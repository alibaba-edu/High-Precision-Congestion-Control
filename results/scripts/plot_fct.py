#!/usr/bin/env python3
"""Visualize Flow Completion Time data"""
import argparse
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import math
from matplotlib.ticker import LogLocator, NullFormatter, FuncFormatter
import sys

def plot_fct(filename, output_file=None):
    flow_sizes = []
    fcts = []
    base_fcts = []
    slowdowns = []
    
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 8:
                try:
                    # Format: src dst sport dport base_fct start_time end_time size
                    size = int(parts[7])
                    start_time = int(parts[5])
                    end_time = int(parts[6])
                    
                    # FCT is duration
                    fct = end_time - start_time
                    base_fct = int(parts[4])
                    
                    if fct <= 0:
                         # Fallback if fct is actually duration (unlikely based on data)
                         if end_time < 100 * 1e9: 
                             fct = end_time
                    
                    slowdown = float(fct) / float(base_fct) if base_fct > 0 else 1.0
                    
                    flow_sizes.append(size)
                    fcts.append(fct / 1e6)  # Convert to ms
                    base_fcts.append(base_fct / 1e6)
                    slowdowns.append(slowdown)
                except:
                    continue
    
    if not flow_sizes:
        print("No data found in file")
        return
    
    # Create subplots
    # Create subplots with compact stats panel
    fig = plt.figure(figsize=(14, 8))
    gs = gridspec.GridSpec(2, 3, figure=fig, width_ratios=[1, 1, 0.7])
    ax_fct = fig.add_subplot(gs[0, 0])
    ax_slow = fig.add_subplot(gs[0, 1])
    ax_hist = fig.add_subplot(gs[1, 0:2])
    ax_stats = fig.add_subplot(gs[:, 2])
    
    def _format_bytes(value, _pos=None):
        if value <= 0:
            return "0"
        units = ["B", "KB", "MB", "GB", "TB"]
        idx = 0
        v = float(value)
        while v >= 1024 and idx < len(units) - 1:
            v /= 1024.0
            idx += 1
        return f"{v:.1f}{units[idx]}"

    max_size = max(flow_sizes)
    if max_size >= 1024 ** 3:
        size_scale = 1024 ** 3
        size_unit = "GB"
    elif max_size >= 1024 ** 2:
        size_scale = 1024 ** 2
        size_unit = "MB"
    elif max_size >= 1024:
        size_scale = 1024
        size_unit = "KB"
    else:
        size_scale = 1
        size_unit = "B"
    scaled_sizes = [s / size_scale for s in flow_sizes]

    unique_sizes = sorted(set(scaled_sizes))
    single_size = len(unique_sizes) == 1

    # Plot 1: FCT vs Flow Size
    ax_fct.scatter(scaled_sizes, fcts, alpha=0.35, s=10, rasterized=True)
    ax_fct.set_xlabel(f'Flow Size ({size_unit})')
    ax_fct.set_ylabel('FCT (ms)')
    ax_fct.set_title('FCT vs Flow Size')
    ax_fct.grid(True, alpha=0.3)
    ax_fct.set_xscale('linear' if single_size else 'log')
    ax_fct.set_yscale('log')
    minv, maxv = min(unique_sizes), max(unique_sizes)
    def _plain_num(v, _pos=None):
        if v == 0:
            return "0"
        if abs(v - round(v)) < 1e-6:
            return str(int(round(v)))
        text = f"{v:.3f}"
        return text.rstrip('0').rstrip('.')

    max_ticks = 4
    if single_size:
        v = unique_sizes[0]
        tick_vals = [v * 0.8, v, v * 1.2]
        ax_fct.set_xlim(v * 0.7, v * 1.3)
    elif minv > 0 and maxv > 0 and maxv / minv > 1.5:
        ratio = (maxv / minv) ** (1 / (max_ticks - 1))
        tick_vals = [minv * (ratio ** i) for i in range(max_ticks)]
    else:
        tick_vals = unique_sizes
    ax_fct.set_xticks(tick_vals)
    ax_fct.set_xticklabels([_plain_num(v) for v in tick_vals])
    ax_fct.xaxis.set_minor_formatter(NullFormatter())
    ax_fct.tick_params(axis='x', labelrotation=60, labelsize=9, labelbottom=True)
    ax_fct.xaxis.get_offset_text().set_visible(False)
    for label in ax_fct.get_xticklabels():
        label.set_horizontalalignment('right')
    ax_fct.tick_params(axis='y', labelsize=9)
    
    # Plot 2: Slowdown vs Flow Size
    ax_slow.scatter(scaled_sizes, slowdowns, alpha=0.35, s=10, color='orange', rasterized=True)
    ax_slow.set_xlabel(f'Flow Size ({size_unit})')
    ax_slow.set_ylabel('Slowdown (FCT/Base FCT)')
    ax_slow.set_title('Slowdown vs Flow Size')
    ax_slow.grid(True, alpha=0.3)
    ax_slow.set_xscale('linear' if single_size else 'log')
    if single_size:
        v = unique_sizes[0]
        tick_vals = [v * 0.8, v, v * 1.2]
        ax_slow.set_xlim(v * 0.7, v * 1.3)
    elif minv > 0 and maxv > 0 and maxv / minv > 1.5:
        ratio = (maxv / minv) ** (1 / (max_ticks - 1))
        tick_vals = [minv * (ratio ** i) for i in range(max_ticks)]
    else:
        tick_vals = unique_sizes
    ax_slow.set_xticks(tick_vals)
    ax_slow.set_xticklabels([_plain_num(v) for v in tick_vals])
    ax_slow.xaxis.set_minor_formatter(NullFormatter())
    ax_slow.tick_params(axis='x', labelrotation=60, labelsize=9, labelbottom=True)
    ax_slow.xaxis.get_offset_text().set_visible(False)
    for label in ax_slow.get_xticklabels():
        label.set_horizontalalignment('right')
    ax_slow.tick_params(axis='y', labelsize=9)
    ax_slow.axhline(y=1, color='r', linestyle='--', label='Ideal')
    ax_slow.legend()
    
    # Plot 3: FCT histogram
    ax_hist.hist(fcts, bins=30, alpha=0.7, color='green', edgecolor='black')
    ax_hist.set_xlabel('FCT (ms)')
    ax_hist.set_ylabel('Count')
    ax_hist.set_title('FCT Distribution')
    ax_hist.grid(True, alpha=0.3)
    
    # Plot 4: Statistics summary
    ax_stats.axis('off')
    stats_text = "FCT Stats\n\n"
    stats_text += "Flows: {}\n\n".format(len(fcts))
    stats_text += "FCT (ms):\n"
    stats_text += "  Min: {:.3f}\n".format(min(fcts))
    stats_text += "  Max: {:.3f}\n".format(max(fcts))
    stats_text += "  Mean: {:.3f}\n\n".format(sum(fcts)/len(fcts))
    stats_text += "Slowdown:\n"
    stats_text += "  Min: {:.3f}\n".format(min(slowdowns))
    stats_text += "  Max: {:.3f}\n".format(max(slowdowns))
    stats_text += "  Mean: {:.3f}\n".format(sum(slowdowns)/len(slowdowns))
    ax_stats.text(0.05, 0.95, stats_text, fontsize=10, family='monospace',
                  verticalalignment='top')

    fig.subplots_adjust(left=0.10, right=0.98, bottom=0.12, top=0.92, wspace=0.35, hspace=0.4)
    if output_file is None:
        output_file = filename.replace('.txt', '.png')
    plt.savefig(output_file, dpi=150)
    print("Plot saved to: " + output_file)
    plt.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Plot flow completion time data")
    parser.add_argument("input", nargs="?", default="simulation/mix/outputs/fct/fct.txt",
                        help="Path to FCT data file")
    parser.add_argument("--out", default=None, help="Output PNG path")
    args = parser.parse_args()

    plot_fct(args.input, args.out)
