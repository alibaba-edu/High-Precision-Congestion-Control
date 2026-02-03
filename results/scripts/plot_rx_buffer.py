#!/usr/bin/env python3
"""Plot NIC RX buffer occupancy over time.

Input format (per line):
<time_ns> <node_id> <if_index> <bytes>
"""
import argparse
import sys
import os
from collections import defaultdict

import matplotlib.pyplot as plt


def parse_config(config_file):
    """Parse config file to extract RX_BUFFER_PER_QUEUE value."""
    if not os.path.exists(config_file):
        return None
    
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('RX_BUFFER_PER_QUEUE'):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        return int(parts[1])
                    except ValueError:
                        pass
    return None


def parse_schedules(config_file):
    """Parse config file to extract RX_PULL_RATE_SCHEDULE."""
    schedules = {}
    if not os.path.exists(config_file):
        return schedules
    
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Handle comments
            if line.startswith('#'):
                continue
            if 'RX_PULL_RATE_SCHEDULE' in line:
                parts = line.split()
                # Format: RX_PULL_RATE_SCHEDULE <node_id> <count> <time1> <rate1> ...
                if len(parts) >= 3 and parts[0] == 'RX_PULL_RATE_SCHEDULE':
                    try:
                        node_id = int(parts[1])
                        count = int(parts[2])
                        schedule = []
                        idx = 3
                        for _ in range(count):
                            if idx + 1 < len(parts):
                                t = float(parts[idx])
                                r = float(parts[idx+1])
                                schedule.append((t, r))
                                idx += 2
                        schedules[node_id] = schedule
                    except ValueError:
                        pass
    return schedules

def plot_rx_buffer(filename, output_file=None, config_file=None):
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

    # Determine best unit for Y-axis
    max_data_val = 0
    for series in data.values():
        if series["bytes"]:
            max_data_val = max(max_data_val, max(series["bytes"]))
            
    # Get max buffer limit
    max_buffer_per_queue = 1048576  # default value (1MB)
    schedules = {}
    if config_file:
        parsed_value = parse_config(config_file)
        if parsed_value is not None:
            max_buffer_per_queue = parsed_value
        schedules = parse_schedules(config_file)

    # Determine scale factor and unit
    # Use the larger of data max or limit to guide scaling, but prefer data readability
    # If usage is tiny (e.g. 6KB) vs Limit (1MB), we might want to scale for Data
    # but still show the limit line context.
    
    reference_val = max(max_data_val, max_buffer_per_queue / 10) # Heuristic
    
    if reference_val >= 1024 * 1024:
        scale = 1024 * 1024
        unit = "MB"
    elif reference_val >= 1024:
        scale = 1024
        unit = "KB"
    else:
        scale = 1
        unit = "Bytes"

    plt.figure(figsize=(12, 6))
    
    # Track max values for annotations
    annotated_series = []
    
    for (node, ifidx), series in sorted(data.items()):
        label = f"node {node} if {ifidx}"
        # Scale data
        scaled_bytes = [b / scale for b in series["bytes"]]
        line, = plt.plot(series["t"], scaled_bytes, label=label, linewidth=1.5)
        
        # Find and annotate maximum value
        if series["bytes"]:
            max_bytes = max(series["bytes"])
            if max_bytes > 0:  # Only annotate if there's actual data
                max_idx = series["bytes"].index(max_bytes)
                max_time = series["t"][max_idx]
                max_val_scaled = max_bytes / scale
                
                plt.annotate(f'{max_val_scaled:.2f} {unit}', 
                            xy=(max_time, max_val_scaled),
                            xytext=(10, 10), textcoords='offset points',
                            fontsize=8, color=line.get_color(),
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                    edgecolor=line.get_color(), alpha=0.8),
                            arrowprops=dict(arrowstyle='->', color=line.get_color(), lw=1))
                annotated_series.append((node, ifidx, max_bytes, max_time))

    # Add reference line for maximum per-queue buffer size
    scaled_limit = max_buffer_per_queue / scale
    plt.axhline(y=scaled_limit, color='red', linestyle='--', linewidth=2, 
                label=f'Max buffer/queue ({scaled_limit:.2f} {unit})', alpha=0.7)

    # Add vertical lines for pulling rate schedule
    colors = ['green', 'purple', 'orange', 'brown'] # Cycle colors for different nodes if needed
    color_idx = 0
    for node_id, schedule in schedules.items():
        # Check if this node is in the plotted data (ignoring interface index)
        if any(d_node == node_id for d_node, _ in data.keys()):
            for time, rate in schedule:
                plt.axvline(x=time, color='gray', linestyle=':', alpha=0.6)
                # Annotate the rate
                plt.text(time, plt.ylim()[1] * 0.95, f' t={time}s\nRate={rate}', rotation=90, verticalalignment='top', fontsize=8, color='black', fontweight='bold')


    plt.xlabel("Time (s)")
    plt.ylabel(f"RX buffer ({unit})")
    plt.title(f"NIC RX Buffer Occupancy Over Time (Max: {max_data_val/scale:.2f} {unit})")
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best', framealpha=0.9)
    plt.tight_layout()

    if output_file is None:
        output_file = filename.replace(".txt", ".png")
        if output_file == filename:
            output_file = filename + ".png"
    plt.savefig(output_file, dpi=150)
    print(f"RX buffer plot saved to: {output_file}")
    plt.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot NIC RX buffer occupancy over time")
    parser.add_argument("input", nargs="?", default="results/data/rxbuf_two_senders_heavy.txt",
                        help="Path to RX buffer trace file")
    parser.add_argument("--out", default=None, help="Output PNG path")
    parser.add_argument("--config", default="simulation/mix/configs/config_two_senders_per_node.txt",
                        help="Path to config file (to read RX_BUFFER_PER_QUEUE)")
    args = parser.parse_args()

    plot_rx_buffer(args.input, args.out, args.config)
