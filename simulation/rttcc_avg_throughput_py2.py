#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os, re, sys, argparse

# rttcc 文件名示例：rttcc_n2_S0.2-10000_D0.1-100_pg3.csv
RRTCC_RE = re.compile(r'^rttcc_n(\d+)_S([^_-]+)-(\d+)_D([^_-]+)-(\d+)_pg(\d+)\.csv$')
# tp 文件名示例：tp_0b000101_0b000201_10000_100.pg3.log
TP_RE    = re.compile(r'^tp_([0-9a-fA-F]{8})_([0-9a-fA-F]{8})_(\d+)_(\d+)\.pg(\d+)\.log$')

def parse_tp_file(tp_path):
    """读取 mix/log/tp_*.log，按窗口做时间加权平均"""
    sum_bytes = 0L
    sum_time  = 0.0
    if not os.path.exists(tp_path):
        return (None, None)
    with open(tp_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            try:
                thr_bps   = float(parts[1])  # throughput_bps
                bytes_win = float(parts[3])  # bytes_in_window
            except:
                continue
            if thr_bps > 0.0 and bytes_win >= 0.0:
                # thr_bps = bytes*8 / dt  =>  dt = bytes*8 / thr_bps
                dt = (bytes_win * 8.0) / thr_bps
                sum_time  += dt
                sum_bytes += long(bytes_win)
    return (sum_bytes, sum_time)

def parse_rttcc_rate_avg(csv_path):
    """兜底：用 rttcc 控制日志的 rate_Gbps 做时间加权平均"""
    ts, rs = [], []
    try:
        with open(csv_path, 'r') as f:
            header = True
            for line in f:
                if header:
                    header = False
                    continue
                line = line.strip()
                if not line:
                    continue
                parts = line.split(',')
                if len(parts) < 10:
                    continue
                try:
                    t = float(parts[0])   # time_s
                    r = float(parts[8])   # rate_Gbps
                except:
                    continue
                ts.append(t); rs.append(r)
    except:
        return None
    if len(ts) < 2:
        return None
    num, den = 0.0, 0.0
    for i in range(len(ts)-1):
        dt = ts[i+1] - ts[i]
        if dt <= 0: 
            continue
        num += rs[i] * dt
        den += dt
    if den == 0.0:
        return None
    return num / den

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--logdir', default='mix/log', help='日志目录（含 rttcc_*.csv / tp_*.log）')
    ap.add_argument('--out',    default='rttcc_avg_throughput.tsv', help='输出 TSV 文件')
    args = ap.parse_args()

    if not os.path.isdir(args.logdir):
        print("目录不存在：%s" % args.logdir); sys.exit(1)

    # 1) 索引 tp_*.log：按 (sport, dport, pg) 聚合
    tp_index = {}  # key=(sport,dport,pg) -> [fullpath,...]
    for fn in os.listdir(args.logdir):
        m = TP_RE.match(fn)
        if not m:
            continue
        sport = int(m.group(3))
        dport = int(m.group(4))
        pg    = int(m.group(5))
        tp_index.setdefault((sport, dport, pg), []).append(os.path.join(args.logdir, fn))

    # 2) 扫描 rttcc_*.csv
    rows = []  # (flow_key, avg_gbps, method, source)
    total_bytes = 0L
    total_time  = 0.0
    sum_flow_avg = 0.0
    flow_cnt = 0

    rttcc_files = [fn for fn in os.listdir(args.logdir) if fn.startswith('rttcc_') and fn.endswith('.csv')]
    if not rttcc_files:
        print("没有找到 rttcc_*.csv，请确认已开启 RttccLogToFile 并且有输出。")
        sys.exit(2)

    for fn in rttcc_files:
        m = RRTCC_RE.match(fn)
        if not m:
            # 文件名不符合预期，跳过
            continue
        node  = m.group(1)
        sip_s = m.group(2)  # 原样保留（不再做点分转换）
        sport = int(m.group(3))
        dip_s = m.group(4)
        dport = int(m.group(5))
        pg    = int(m.group(6))

        csv_path = os.path.join(args.logdir, fn)
        flow_key = "%s:%s-%d->%s-%d.pg%d" % (node, sip_s, sport, dip_s, dport, pg)

        # 先按 (sport,dport,pg) 找 tp 候选
        cands = tp_index.get((sport, dport, pg), [])

        if cands:
            # 多个候选时，简单取第一个；如需更精确可在此加更多判别规则
            tp_path = cands[0]
            sum_b, sum_t = parse_tp_file(tp_path)
            if sum_b is not None and sum_t and sum_t > 0.0:
                avg_bps  = (float(sum_b) * 8.0) / sum_t
                avg_gbps = avg_bps / 1e9
                rows.append((flow_key, avg_gbps, 'tp', os.path.basename(tp_path)))
                total_bytes += long(sum_b)
                total_time  += sum_t
                sum_flow_avg += avg_gbps
                flow_cnt += 1
                continue  # 下一个 flow

        # 没有匹配到 tp_*.log，或 tp 解析失败：兜底用 rttcc 的 rate_Gbps
        approx = parse_rttcc_rate_avg(csv_path)
        if approx is not None:
            rows.append((flow_key, approx, 'rate', '(fallback)'))
            sum_flow_avg += approx
            flow_cnt += 1

    if not rows:
        print("没有成功解析到任何吞吐记录（tp 或 rate）。")
        sys.exit(3)

    # 3) 输出 TSV
    with open(args.out, 'w') as out:
        out.write("flow\tavg_throughput_Gbps\tmethod\tsource\n")
        for (k, v, mtd, src) in rows:
            out.write("%s\t%.6f\t%s\t%s\n" % (k, v, mtd, src))
        out.write("\n# 汇总\n")
        if total_time > 0.0:
            overall_gbps_time_weighted = (float(total_bytes) * 8.0 / total_time) / 1e9
            out.write("# overall_time_weighted_Gbps\t%.6f\n" % overall_gbps_time_weighted)
        if flow_cnt > 0:
            out.write("# mean_of_flows_Gbps\t%.6f\n" % (sum_flow_avg / float(flow_cnt)))

    print("已写出：%s" % args.out)
    if total_time > 0.0:
        print("overall(time-weighted) = %.6f Gbps" % ((float(total_bytes) * 8.0 / total_time) / 1e9))
    if flow_cnt > 0:
        print("mean(of %d flows)     = %.6f Gbps" % (flow_cnt, (sum_flow_avg / float(flow_cnt))))

if __name__ == '__main__':
    main()

