#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os, re, sys, argparse

RRTCC_RE = re.compile(r'rttcc_n(\d+)_S([0-9\.]+)-(\d+)_D([0-9\.]+)-(\d+)_pg(\d+)\.csv$')

def ip_to_hex(ip):
    parts = [int(x) for x in ip.split('.')]
    val = (parts[0]<<24) | (parts[1]<<16) | (parts[2]<<8) | parts[3]
    return "%08x" % val  # 小写十六进制，和 C 里的 %08x 对齐

def parse_tp_file(tp_path):
    """
    读取 mix/log/tp_*.log
    每行: time_ns throughput_bps rate_set_bps bytes_in_window
    返回 (sum_bytes, sum_time_seconds) —— 由窗口逐行累加
    """
    sum_bytes = 0L
    sum_time = 0.0
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
                thr_bps = float(parts[1])
                bytes_win = float(parts[3])
            except:
                continue
            # thr_bps = bytes*8 / dt  =>  dt = bytes*8 / thr_bps
            if thr_bps > 0.0 and bytes_win >= 0.0:
                dt = (bytes_win * 8.0) / thr_bps
                sum_time += dt
                sum_bytes += bytes_win
    return (sum_bytes, sum_time)

def parse_rttcc_rate_avg(csv_path):
    """
    读取 rttcc_*.csv 作为兜底近似：按时间加权平均 rate_Gbps
    列: time_s,node,sip,dip,sport,dport,pg,phase,rate_Gbps,rtt_ns,grad
    返回 近似平均吞吐 (Gbps)；若不足两行则返回 None
    """
    ts = []
    rs = []
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
                t = float(parts[0])
                r = float(parts[8])  # rate_Gbps
            except:
                continue
            ts.append(t); rs.append(r)
    if len(ts) < 2:
        return None
    # 时间加权平均
    num = 0.0
    den = 0.0
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
    ap.add_argument('--logdir', default='', help='日志目录，包含 rttcc_*.csv 和 tp_*.log')
    ap.add_argument('--out', default='rttcc_avg_throughput.tsv', help='输出汇总 TSV 文件名')
    args = ap.parse_args()

    logdir = args.logdir
    rttcc_files = [os.path.join(logdir, f) for f in os.listdir(logdir) if f.startswith('rttcc_') and f.endswith('.csv')]
    if not rttcc_files:
        print("没有找到 %s 下的 rttcc_*.csv，确认已开启 RttccLogToFile 并已跑过 RTTCC。" % logdir)
        sys.exit(1)

    rows = []  # (flow_key, avg_gbps, method, tp_path)
    total_bytes = 0L
    total_time = 0.0
    sum_flow_avg = 0.0
    flow_cnt = 0

    for csv_path in rttcc_files:
        fn = os.path.basename(csv_path)
        m = RRTCC_RE.match(fn)
        if not m:
            continue
        node, sip, sport, dip, dport, pg = m.groups()
        sip_hex = ip_to_hex(sip)
        dip_hex = ip_to_hex(dip)
        tp_fn = "tp_%s_%s_%s_%s.pg%s.log" % (sip_hex, dip_hex, sport, dport, pg)
        tp_path = os.path.join(logdir, tp_fn)

        # 先用 tp_*.log 计算真实平均吞吐
        sum_b, sum_t = parse_tp_file(tp_path)
        if sum_b is not None and sum_t and sum_t > 0.0:
            avg_bps = (float(sum_b) * 8.0) / sum_t
            avg_gbps = avg_bps / 1e9
            rows.append(("%s:%s-%s->%s-%s.pg%s" % (node, sip, sport, dip, dport, pg),
                         avg_gbps, 'tp', tp_fn))
            total_bytes += long(sum_b)
            total_time  += sum_t
            sum_flow_avg += avg_gbps
            flow_cnt += 1
        else:
            # 兜底：用 rttcc 控制日志的 rate_Gbps 时间加权平均
            approx = parse_rttcc_rate_avg(csv_path)
            if approx is not None:
                rows.append(("%s:%s-%s->%s-%s.pg%s" % (node, sip, sport, dip, dport, pg),
                             approx, 'rate', '(fallback)'))
                sum_flow_avg += approx
                flow_cnt += 1

    if not rows:
        print("没有成功解析到任何吞吐记录。确认是否存在 tp_*.log 或 rttcc_*.csv 有足够多的行。")
        sys.exit(2)

    # 输出 TSV
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
    # 终端也简单回显一下关键汇总
    if total_time > 0.0:
        print("overall(time-weighted) = %.6f Gbps" % ((float(total_bytes) * 8.0 / total_time) / 1e9))
    if flow_cnt > 0:
        print("mean(of %d flows)     = %.6f Gbps" % (flow_cnt, (sum_flow_avg / float(flow_cnt))))

if __name__ == '__main__':
    main()

