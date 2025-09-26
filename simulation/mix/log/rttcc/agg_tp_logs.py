#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
按时间窗口把 mix/log 下的 tp_*.log 重采样并聚合成统一 CSV：
输出列: time_s,total_Gbps,jain_index,<flow cols...>

假设 tp_.log 每行格式（没有 header）:
  time_ns  throughput_bps  rate_set_bps  bytes_in_window

我们把每行视作区间 [time_ns, time_ns + dt_ns) 其中 dt = bytes*8 / thr_bps (秒 -> 转为 ns)
然后基于全局等宽 bin（以秒为单位，参数 --bin）对区间与 bin 做重叠加权平均。
"""
from __future__ import print_function
import os, glob, math, argparse, csv

def parse_tp_logs(logdir):
    """
    读取所有 tp_*.log，解析为 flow -> list of (t_ns, thr_bps, bytes_in_window)
    """
    flows = {}
    for path in glob.glob(os.path.join(logdir, "tp_*.log")):
        key = os.path.basename(path).replace(".log", "")
        rows = []
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    if len(parts) < 4:
                        continue
                    try:
                        t_ns = float(parts[0])            # 原始文件用 Simulator::Now().GetTimeStep() -> ns
                        thr_bps = float(parts[1])
                        bytes_win = float(parts[3])
                    except:
                        continue
                    if thr_bps <= 0.0 or bytes_win < 0.0:
                        continue
                    rows.append((t_ns, thr_bps, bytes_win))
        except Exception as e:
            print("WARN: cannot read", path, e)
            continue
        if rows:
            # 保证按时间排序
            rows.sort(key=lambda x: x[0])
            flows[key] = rows
    return flows

def make_intervals_for_flow(rows):
    """
    把每行变为区间 (start_ns, end_ns, thr_bps)
    dt_seconds = bytes_win*8 / thr_bps
    dt_ns = dt_seconds * 1e9
    返回 list of (start_ns, end_ns, thr_bps)
    """
    intervals = []
    for (t_ns, thr_bps, bytes_win) in rows:
        # 防止除零
        if thr_bps <= 0.0:
            continue
        dt_s = (bytes_win * 8.0) / thr_bps   # 秒
        dt_ns = dt_s * 1e9
        if dt_ns <= 0:
            # 退化为微小窗口
            dt_ns = 1.0
        intervals.append((t_ns, t_ns + dt_ns, thr_bps))
    return intervals

def aggregate(flows_intervals, bin_s):
    """
    flows_intervals: dict flow -> list of (s_ns, e_ns, thr_bps)
    bin_s: bin 宽度（秒）
    返回：sorted list of bin_time_s, 和每 bin 的总吞吐、jain、以及每流吞吐
    """
    # 找时间范围（单位：ns）
    min_ns = None
    max_ns = None
    for fl, iv in flows_intervals.items():
        if not iv:
            continue
        if min_ns is None or iv[0][0] < min_ns:
            min_ns = iv[0][0]
        if max_ns is None or iv[-1][1] > max_ns:
            max_ns = iv[-1][1]
    if min_ns is None:
        return [], []

    bin_ns = bin_s * 1e9
    # 构造 bin edges: left inclusive. 我们用左边界时间作为时间点输出 (秒).
    first_bin_idx = int(math.floor(min_ns / bin_ns))
    last_bin_idx  = int(math.floor(max_ns / bin_ns))
    bins = [ (i * bin_ns, (i+1) * bin_ns) for i in range(first_bin_idx, last_bin_idx+1) ]
    bin_count = len(bins)

    # 准备结果矩阵：每个 bin 对每个 flow 的累计 bytes-time（即 thr_bps * overlap_dt），但我们使用 bps*time (bit-seconds) 更稳妥
    flow_keys = sorted(flows_intervals.keys())
    # result[bin_idx][flow_idx] = time-weighted average throughput in bps for that bin
    # We'll compute numerator = sum(thr_bps * overlap_dt_s) and denominator = bin_s -> avg_bps = numerator / bin_s
    numerators = [ [0.0]*len(flow_keys) for _ in range(bin_count) ]  # units: bps * s = bits
    # For each flow, walk its intervals and add overlaps
    for fi, fl in enumerate(flow_keys):
        ivs = flows_intervals[fl]
        for (s_ns, e_ns, thr_bps) in ivs:
            if e_ns <= s_ns:
                continue
            # find overlapping bins indices
            start_idx = int(math.floor(s_ns / bin_ns)) - first_bin_idx
            end_idx   = int(math.floor((e_ns-1) / bin_ns)) - first_bin_idx
            # clamp
            if end_idx < 0 or start_idx >= bin_count:
                continue
            if start_idx < 0: start_idx = 0
            if end_idx >= bin_count: end_idx = bin_count-1
            # for each overlapping bin compute overlap time
            for b in range(start_idx, end_idx+1):
                b_s_ns, b_e_ns = bins[b]
                overlap_s = max(s_ns, b_s_ns)
                overlap_e = min(e_ns, b_e_ns)
                if overlap_e > overlap_s:
                    overlap_dt_s = (overlap_e - overlap_s) / 1e9
                    numerators[b][fi] += thr_bps * overlap_dt_s  # bps * s

    # compute averages per bin
    rows = []
    for b_idx, (b_s_ns,b_e_ns) in enumerate(bins):
        time_s = b_s_ns / 1e9
        perflow_avg_bps = []
        for fi in range(len(flow_keys)):
            num = numerators[b_idx][fi]
            avg_bps = num / bin_s if bin_s > 0 else 0.0
            perflow_avg_bps.append(avg_bps)
        total_bps = sum(perflow_avg_bps)
        # Jain 指数
        n = float(len(perflow_avg_bps))
        sum_sq = sum(x*x for x in perflow_avg_bps)
        if total_bps > 0 and sum_sq > 0:
            jain = (total_bps*total_bps) / (n * sum_sq)
        else:
            jain = 0.0
        rows.append( (time_s, total_bps, jain, perflow_avg_bps) )
    return flow_keys, rows

def write_csv(outpath, flow_keys, rows):
    with open(outpath, "wb") as f:
        writer = csv.writer(f, delimiter='\t')
        header = ["time", "total_Gbps", "jain_index"] + flow_keys
        writer.writerow(header)
        for (t_s, total_bps, jain, perflow_bps) in rows:
            line = [ "%.6f" % t_s, "%.6f" % (total_bps/1e9), "%.6f" % jain ]
            line += [ "%.6f" % (x/1e9) for x in perflow_bps ]
            writer.writerow(line)
    print("Wrote", outpath, "rows:", len(rows), "flows:", len(flow_keys))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--logdir", default="", help="dir containing tp_*.log")
    ap.add_argument("--out", default="throughput_time_series.csv", help="output CSV path")
    ap.add_argument("--bin", type=float, default=0.001, help="bin size in seconds (default 1ms)")
    args = ap.parse_args()

    flows = parse_tp_logs(args.logdir)
    if not flows:
        print("No tp_*.log under", args.logdir)
        return
    # make intervals
    flows_intervals = {}
    for k, rows in flows.items():
        flows_intervals[k] = make_intervals_for_flow(rows)

    flow_keys, rows = aggregate(flows_intervals, args.bin)
    write_csv(args.out, flow_keys, rows)

if __name__ == "__main__":
    main()

