#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import csv
import argparse
import matplotlib.pyplot as plt


def read_csv(csvfile):
    times = []
    total_gbps = []
    jain_index = []
    perflow_gbps = []
    flow_keys = []

    with open(csvfile, "r") as f:
        reader = csv.reader(f, delimiter="\t")  # 用制表符分隔
        header = next(reader)
        flow_keys = header[3:]  # 前3列是 time, total_Gbps, jain_index

        for row in reader:
            if not row:  # 跳过空行
                continue
            times.append(float(row[0]))
            total_gbps.append(float(row[1]))
            jain_index.append(float(row[2]))
            perflow_gbps.append([float(x) for x in row[3:]])

    return times, total_gbps, jain_index, perflow_gbps, flow_keys


def plot_total_throughput(times, total_gbps, outprefix):
    plt.figure()
    plt.plot(times, total_gbps, label="Total throughput (Gbps)")
    plt.xlabel("Time (s)")
    plt.ylabel("Throughput (Gbps)")
    plt.title("Total Throughput vs Time")
    plt.legend()
    plt.grid(True)
    plt.savefig(outprefix + "_total.png")
    plt.close()


def plot_perflow_throughput(times, perflow_gbps, flow_keys, outprefix):
    #plt.figure()
    plt.figure(figsize=(10, 6))
    for i, key in enumerate(flow_keys):
        flow_data = [row[i] for row in perflow_gbps]
        plt.plot(times, flow_data, label="Flow %s" % key)
    plt.xlabel("Time (s)")
    plt.ylabel("Throughput (Gbps)")
    plt.title("Per-Flow Throughput vs Time")
    plt.ylim(0, 100)
    #plt.legend()
    plt.legend(loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8)
    plt.tight_layout()
    plt.grid(True)
    plt.savefig(outprefix + "_perflow.png")
    plt.close()


def plot_jain_index(times, jain_index, outprefix):
    plt.figure()
    plt.plot(times, jain_index, label="Jain’s fairness index")
    plt.xlabel("Time (s)")
    plt.ylabel("Fairness Index")
    plt.title("Fairness vs Time")
    plt.ylim(0, 1.05)  # Jain 指数范围 0~1
    plt.legend()
    plt.grid(True)
    plt.savefig(outprefix + "_fairness.png")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Plot throughput results from CSV.")
    parser.add_argument("csvfile", help="Input CSV file (throughput_time_series.csv)")
    parser.add_argument("--fairness", action="store_true",
                        help="Plot fairness index if available")
    parser.add_argument("--outprefix", default="throughput",
                        help="Prefix for output image files")
    args = parser.parse_args()

    times, total_gbps, jain_index, perflow_gbps, flow_keys = read_csv(args.csvfile)

    plot_total_throughput(times, total_gbps, args.outprefix)
    plot_perflow_throughput(times, perflow_gbps, flow_keys, args.outprefix)
    if args.fairness and any(jain_index):
        plot_jain_index(times, jain_index, args.outprefix)

    print("Plots saved with prefix:", args.outprefix)


if __name__ == "__main__":
    main()

