#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import subprocess
import argparse
import math

def pct(sorted_vals, p):
    """返回分位（p∈(0,1]），使用上取整索引，空数组返回 NaN。"""
    if not sorted_vals:
        return float('nan')
    idx = int(math.ceil(p * len(sorted_vals))) - 1
    if idx < 0: idx = 0
    if idx >= len(sorted_vals): idx = len(sorted_vals) - 1
    return sorted_vals[idx]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize FCT slowdown by flow-size buckets.')
    parser.add_argument('-p', dest='prefix', default='fct_topology_flow1',
                        help="fct 文件前缀（不含 CC 名），默认 fct_fat（会去找 ../simulation/mix/fct_fat_<CC>.txt）")
    parser.add_argument('-s', dest='step', default='5',
                        help="按流大小分位的步长(%%)，默认 5")
    parser.add_argument('-t', dest='type', type=int, default=0,
                        help="0: normal ($4==100), 1: incast ($4==200), 2: all")
    parser.add_argument('-T', dest='time_limit', type=int, default=3000000000,
                        help="只统计在 T(纳秒) 前完成的流，默认 3e9 ns")
    parser.add_argument('-b', dest='bw', type=int, default=25,
                        help="边链带宽(Gbps)（本脚本未使用，仅保留参数位）")
    args = parser.parse_args()

    # TODO: 把这个列表改成你实际的 CC 名（即 fct_<prefix>_<这里>.txt 的后缀）
    CCs = [
        #'hpccPint95ai50log1.050p1.000',
        #'hp95ai50',
	#'dcqcn',
	#'timely',
	'rttcc'
    ]

    step = int(args.step)
    # 初始化每个分桶的行：第1列是“分位起点”（0.00, 0.05, ...），第2列稍后填 size
    res = [[i/100.0] for i in xrange(0, 100, step)]

    for cc in CCs:
        #file_path = "../simulation/mix/%s_%s.txt" % (args.prefix, cc)
	file_path = "./%s_%s.txt" % (args.prefix, cc)
        if args.type == 0:
            cond = '$4==100 && $6+$7<%d' % args.time_limit
        elif args.type == 1:
            cond = '$4==200 && $6+$7<%d' % args.time_limit
        else:
            cond = '$6+$7<%d' % args.time_limit

        # 输出两列：slowdown 和 size；按 size 排序
        # slowdown = max(1, $7/$8)，与原始脚本一致
        cmd = ("awk '{if (%s) {slow=$7/$8; if (slow<1) slow=1; print slow, $5}}' %s | sort -n -k 2"
               % (cond, file_path))

        output = subprocess.check_output(cmd, shell=True)
        lines = output.strip().splitlines()
        n = len(lines)

        for i in xrange(0, 100, step):
            l = (i       * n) / 100   # 整数下取整
            r = ((i+step) * n) / 100
            idx = i // step
            if r <= l:
                # 空桶：保持 size（若还未填则填 0），并写入 NaN
                if len(res[idx]) == 1:
                    res[idx].append(0)
                res[idx] += [float('nan'), float('nan'), float('nan')]
                continue

            pair = [ (float(s.split()[0]), int(s.split()[1])) for s in lines[l:r] ]
            fcts = sorted([x for (x, _) in pair])
            size = pair[-1][1]

            # 仅第一次 CC 时把 size 写到第2列，保持与原脚本输出格式一致
            if len(res[idx]) == 1:
                res[idx].append(size)

            res[idx] += [ pct(fcts, 0.50), pct(fcts, 0.95), pct(fcts, 0.99) ]

    # 打印：col1=分位起点, col2=size, 之后每个CC给出三列(P50/P95/P99)
    for row in res:
        size_val = int(row[1]) if len(row) > 1 else 0
        line = "%.3f %d" % (row[0], size_val)
        base = 2
        for _ in CCs:
            if len(row) >= base + 3:
                p50, p95, p99 = row[base:base+3]
            else:
                p50 = p95 = p99 = float('nan')
            line += "\t%.3f %.3f %.3f" % (p50, p95, p99)
            base += 3
        print line

