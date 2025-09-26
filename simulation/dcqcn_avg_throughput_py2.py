#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import re
import argparse

# ---------- utils ----------

def ip_from_u32str(s):
    """
    s: '0a000101' -> '10.0.1.1'
    """
    s = s.strip()
    v = int(s, 16)
    return "%d.%d.%d.%d" % (
        (v >> 24) & 0xff,
        (v >> 16) & 0xff,
        (v >> 8)  & 0xff,
        v & 0xff
    )

def parse_tp_filename(fname):
    """
    fname like: tp_0a000101_0b000201_1234_5678.pg3.log
    return (sip, dip, sport, dport, pg) in dotted-decimal + ints
    """
    m = re.match(r'^tp_([0-9a-fA-F]{8})_([0-9a-fA-F]{8})_(\d+)_(\d+)\.pg(\d+)\.log$', fname)
    if not m:
        return None
    sip_hex, dip_hex, sport, dport, pg = m.groups()
    return (ip_from_u32str(sip_hex), ip_from_u32str(dip_hex),
            int(sport), int(dport), int(pg))

def flow_key(sip, dip, sport, dport, pg):
    return "%s|%s|%d|%d|%d" % (sip, dip, sport, dport, pg)

# ---------- readers ----------

def read_tp_logs(logdir):
    """
    读取 mix/log/tp_*.log
    文件每行：time_ns throughput_bps rate_set_bps bytes_in_window
    用 bytes_in_window 和 throughput_bps 反推出窗口时长，再累加字节与时长
    返回: dict[key] = {'bits': total_bits, 'secs': total_secs, 'windows': n}
    """
    agg = {}
    for fname in os.listdir(logdir):
        if not fname.startswith("tp_") or not fname.endswith(".log"):
            continue
        flow = parse_tp_filename(fname)
        if not flow:
            continue
        sip, dip, sport, dport, pg = flow
        key = flow_key(sip, dip, sport, dport, pg)

        bits_sum = 0.0
        secs_sum = 0.0
        windows   = 0

        path = os.path.join(logdir, fname)
        try:
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split()
                    if len(parts) < 4:
                        continue
                    # time_ns  throughput_bps  rate_set_bps  bytes_in_window
                    try:
                        bps   = float(parts[1])
                        bytes_in_win = float(parts[3])
                    except Exception:
                        continue
                    if bps <= 0.0 or bytes_in_win < 0.0:
                        continue
                    # duration = bytes*8 / bps
                    dur = (bytes_in_win * 8.0) / bps
                    secs_sum += dur
                    bits_sum += bytes_in_win * 8.0
                    windows  += 1
        except IOError:
            continue

        if secs_sum > 0.0:
            agg[key] = {'bits': bits_sum, 'secs': secs_sum, 'windows': windows, 'method': 'tp'}
    return agg

def read_dcqcn_csv(logdir):
    """
    读取 mix/log/dcqcn_*.csv
    header: time_s,node,sip,dip,sport,dport,pg,phase,rate_Gbps,alpha,target_Gbps,stage
    用相邻两行的 time_s 做片段时长，对 rate_Gbps 做时间加权
    返回: dict[key] = {'bits': total_bits_equiv, 'secs': total_secs, 'rows': n}
    """
    agg = {}

    for fname in os.listdir(logdir):
        if not fname.startswith("dcqcn_") or not fname.endswith(".csv"):
            continue
        path = os.path.join(logdir, fname)
        rows = []
        try:
            with open(path, 'r') as f:
                header = f.readline()
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    parts = line.split(',')
                    if len(parts) < 12:
                        continue
                    try:
                        t_s   = float(parts[0])
                        sip   = parts[2].strip()
                        dip   = parts[3].strip()
                        sport = int(parts[4])
                        dport = int(parts[5])
                        pg    = int(parts[6])
                        rate_g = float(parts[8])  # rate_Gbps
                    except Exception:
                        continue
                    rows.append((t_s, sip, dip, sport, dport, pg, rate_g))
        except IOError:
            continue

        if not rows:
            continue

        # 按时间排序并累加 (丢弃最后一个点的未知片段)
        rows.sort(key=lambda x: x[0])
        # key 固定自第一行（文件是每流一个文件，保险起见用第一行）
        _, sip, dip, sport, dport, pg, _ = rows[0]
        key = flow_key(sip, dip, sport, dport, pg)

        secs_sum = 0.0
        bits_sum = 0.0
        for i in range(len(rows)-1):
            t0, _, _, _, _, _, r0 = rows[i]
            t1 = rows[i+1][0]
            dt = t1 - t0
            if dt <= 0:
                continue
            bps = r0 * 1e9
            secs_sum += dt
            bits_sum += bps * dt

        if secs_sum > 0.0:
            # 只在该 key 还没有 tp 统计时记录（后面汇总时会以 tp 优先）
            if key not in agg:
                agg[key] = {'bits': bits_sum, 'secs': secs_sum, 'rows': len(rows), 'method': 'rate'}

    return agg

# ---------- main ----------

def main():
    parser = argparse.ArgumentParser(description="Compute DCQCN per-flow average throughput (Python2)")
    parser.add_argument('--logdir', default='mix/log', help='directory containing tp_*.log and dcqcn_*.csv')
    parser.add_argument('--out', default='dcqcn_avg.tsv', help='output TSV filename')
    args = parser.parse_args()

    logdir = args.logdir

    # 先读 tp（真实吞吐优先）
    tp_map = read_tp_logs(logdir)

    # 再读 dcqcn csv（只填补没有 tp 的流）
    rate_map = read_dcqcn_csv(logdir)

    # 合并
    all_keys = {}
    for k, v in tp_map.items():
        all_keys[k] = v
    for k, v in rate_map.items():
        if k not in all_keys:
            all_keys[k] = v

    # 输出每流平均吞吐
    out_lines = []
    out_lines.append("# sip\tdip\tsport\tdport\tpg\tmethod\tavg_Gbps\tweight_secs\twindows_or_rows")
    overall_bits = 0.0
    overall_secs = 0.0
    perflow_gbps = []

    for k, v in sorted(all_keys.items()):
        sip, dip, sport, dport, pg = k.split('|')
        sport = int(sport); dport = int(dport); pg = int(pg)

        bits = v['bits']
        secs = v['secs']
        method = v['method']
        n = v.get('windows', v.get('rows', 0))
        if secs > 0.0:
            gbps = (bits / secs) / 1e9
        else:
            gbps = 0.0

        out_lines.append("%s\t%s\t%d\t%d\t%d\t%s\t%.6f\t%.6f\t%d" %
                         (sip, dip, sport, dport, pg, method, gbps, secs, n))

        # 用所有流（无论 tp 还是 rate）共同统计一个“整体时间加权平均”
        overall_bits += bits
        overall_secs += secs
        perflow_gbps.append(gbps)

    # 写文件
    with open(args.out, 'w') as f:
        f.write("\n".join(out_lines) + "\n")

    # 汇总打印
    if overall_secs > 0.0 and perflow_gbps:
        overall_gbps = (overall_bits / overall_secs) / 1e9
        mean_gbps = sum(perflow_gbps) / float(len(perflow_gbps))
        print("已写出：%s" % args.out)
        print("overall(time-weighted) = %.6f Gbps" % overall_gbps)
        print("mean(of %d flows)     = %.6f Gbps" % (len(perflow_gbps), mean_gbps))
    else:
        print("没有有效数据可统计（检查 %s 是否包含 dcqcn_*.csv 或 tp_*.log）" % logdir)

if __name__ == '__main__':
    main()

