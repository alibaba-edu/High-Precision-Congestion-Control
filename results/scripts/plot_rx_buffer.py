#!/usr/bin/env python3
"""Plot NIC RX buffer occupancy over time.

Input format (per line):
<time_ns> <node_id> <if_index> <bytes>
"""
import sys
from collections import defaultdict

import matplotlib.pyplot as plt


def plot_rx_buffer(filename):
    data = defaultdict(lambda: {"t": [], "bytes": []})
    with open(filename, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 4:
                continue
            try:
                t_ns = int(parts[0])
                node = int(parts[1])
                ifidx = int(parts[2])
                b = int(parts[3])
            except ValueError:
                continue
            key = (node, ifidx)
            data[key]["t"].append(t_ns / 1e9)
            data[key]["bytes"].append(b)

    if not data:
        print("No data found in file")
        return

    plt.figure(figsize=(12, 6))
    for (node, ifidx), series in sorted(data.items()):
        label = f"node {node} if {ifidx}"
        plt.plot(series["t"], series["bytes"], label=label, linewidth=1.5)

    plt.xlabel("Time (s)")
    plt.ylabel("RX buffer bytes")
    plt.title("NIC RX Buffer Occupancy Over Time")
    plt.grid(True, alpha=0.3)
    if len(data) > 1:
        plt.legend()
    plt.tight_layout()

    output_file = filename.replace(".txt", ".png")
    if output_file == filename:
        output_file = filename + ".png"
    plt.savefig(output_file, dpi=150)
    print(f"RX buffer plot saved to: {output_file}")
    plt.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        plot_rx_buffer(sys.argv[1])
    else:
        plot_rx_buffer("results/data/rxbuf_two_senders_heavy.txt")
