#!/usr/bin/env python3
"""
Plot RTT vs Time for each flow.
Calculates RTT = (Window * 8) / Rate from CWND trace data.
"""

import argparse
import sys
import os
import matplotlib.pyplot as plt
from collections import defaultdict

def parse_cwnd_file(filename):
    """
    Parse CWND file to extract RTT samples.
    Format: time_ns src dst sport dport rate_bps win_bytes
    """
    flows = defaultdict(lambda: {"t": [], "rtt": []})
    
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 7:
                continue
            try:
                t_ns = int(parts[0])
                src = int(parts[1])
                dst = int(parts[2])
                sport = int(parts[3])
                dport = int(parts[4])
                rate_bps = int(parts[5])
                win_bytes = int(parts[6])
                
                if rate_bps > 0 and win_bytes > 0:
                    # Calculate RTT in microseconds
                    # RTT (s) = (win_bytes * 8) / rate_bps
                    rtt_us = (win_bytes * 8.0 * 1e6) / rate_bps
                    
                    # Store data
                    key = (src, dst, sport, dport)
                    flows[key]["t"].append(t_ns / 1e9) # Time in seconds
                    flows[key]["rtt"].append(rtt_us)
                    
            except ValueError:
                continue
                
    return flows

def plot_rtt_time(input_file, output_file):
    flows = parse_cwnd_file(input_file)
    
    if not flows:
        print("No valid flow data found.")
        return

    plt.figure(figsize=(12, 6))
    
    # Use a distinct color cycle
    colors = plt.cm.tab10.colors
    
    for i, (key, data) in enumerate(sorted(flows.items())):
        src, dst, sport, dport = key
        label = f"Flow {src}->{dst} ({sport})"
        color = colors[i % len(colors)]
        
        plt.plot(data["t"], data["rtt"], label=label, linewidth=1.5, alpha=0.9, color=color)

    plt.xlabel("Simulation Time (s)")
    plt.ylabel("RTT (us)")
    plt.title("Round Trip Time (RTT) Over Time")
    plt.grid(True, alpha=0.3)
    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', borderaxespad=0)
    plt.tight_layout()
    
    if output_file is None:
        output_file = input_file.replace(".txt", "_rtt.png")
        if output_file == input_file:
             output_file += "_rtt.png"
             
    plt.savefig(output_file, dpi=150)
    print(f"RTT plot saved to: {output_file}")
    plt.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot RTT over time")
    parser.add_argument("input", help="Path to CWND trace file")
    parser.add_argument("--out", help="Output PNG file path")
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: file {args.input} not found")
        sys.exit(1)
        
    plot_rtt_time(args.input, args.out)
