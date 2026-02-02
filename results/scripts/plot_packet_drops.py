#!/usr/bin/env python3
"""Plot packet drop statistics per node.

Input format (per line in drop.txt):
<time_ns> <node_id> <if_index> <queue_index> <packet_size>
"""
import argparse
import sys
import os
from collections import defaultdict

import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec


def _parse_pfc(pfc_file, bin_us):
    bin_ns = bin_us * 1000
    bins = {}
    min_time = None
    with open(pfc_file, "r") as f:
        for raw in f:
            parts = raw.strip().split()
            if len(parts) < 5:
                continue
            try:
                t_ns = int(parts[0])
                event_type = int(parts[4])
            except ValueError:
                continue
            if event_type != 1:
                continue  # pause only
            if min_time is None or t_ns < min_time:
                min_time = t_ns
            b = t_ns // bin_ns
            bins[b] = bins.get(b, 0) + 1
            
    if not bins:
        return [], []

    xs = sorted(bins.keys())
    ys = [bins[x] for x in xs]
    base = 0 if min_time is None else (min_time // bin_ns)
    times = [max(0.0, (x - base) * bin_ns / 1e9) for x in xs]
    return times, ys


def plot_packet_drops(filename, output_file=None, pfc_file=None, pfc_bin_us=1000):
    """Create comprehensive packet drop and PFC visualization."""
    
    # Data structures for Drops
    drops_per_node = defaultdict(int)
    drops_per_node_bytes = defaultdict(int)
    drops_timeline = defaultdict(list)
    drops_per_queue = defaultdict(lambda: defaultdict(int))
    
    total_drops = 0
    total_bytes_dropped = 0
    
    if filename and os.path.exists(filename):
        with open(filename, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                try:
                    t_ns = int(parts[0])
                    node = int(parts[1])
                    ifidx = int(parts[2])
                    qidx = int(parts[3])
                    pkt_size = int(parts[4])
                except ValueError:
                    continue
                
                drops_per_node[node] += 1
                drops_per_node_bytes[node] += pkt_size
                drops_per_queue[node][qidx] += 1
                total_drops += 1
                total_bytes_dropped += pkt_size
                drops_timeline[node].append((t_ns / 1e9, drops_per_node[node]))
    
    # Parse PFC if provided
    pfc_times, pfc_counts = [], []
    if pfc_file and os.path.exists(pfc_file):
        pfc_times, pfc_counts = _parse_pfc(pfc_file, pfc_bin_us)
        
    has_drops = total_drops > 0
    has_pfc = len(pfc_times) > 0
    
    if not has_drops and not has_pfc:
        print("No drops or PFC events found.")
        fig = plt.figure(figsize=(12, 6))
        plt.text(0.5, 0.5, 'No Congestion Events (Drops/PFC) Detected ✓', 
                ha='center', va='center', fontsize=20, color='green')
        plt.axis('off')
        if output_file is None:
            output_file = "reliability_analysis.png"
        plt.savefig(output_file, dpi=150)
        plt.close()
        return

    # Create figure with 3 rows if PFC exists, else 2
    rows = 3 if has_pfc else 2
    fig = plt.figure(figsize=(16, 5 * rows))
    gs = gridspec.GridSpec(rows, 2, figure=fig, hspace=0.3, wspace=0.3)
    
    # Row 1 & 2: Drop Stats (only if drops exist)
    if has_drops:
        # 1. Histogram: Total drops per node
        ax1 = fig.add_subplot(gs[0, 0])
        nodes = sorted(drops_per_node.keys())
        drop_counts = [drops_per_node[n] for n in nodes]
        bars = ax1.bar(nodes, drop_counts, color='#e74c3c', alpha=0.7, edgecolor='black')
        ax1.set_xlabel('Node ID', fontsize=12)
        ax1.set_ylabel('Total Packet Drops', fontsize=12)
        ax1.set_title(f'Packet Drops per Node (Total: {total_drops:,})', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # 2. Histogram: Bytes dropped
        ax2 = fig.add_subplot(gs[0, 1])
        bytes_counts = [drops_per_node_bytes[n] / 1024 for n in nodes]
        ax2.bar(nodes, bytes_counts, color='#3498db', alpha=0.7, edgecolor='black')
        ax2.set_ylabel('Total Bytes Dropped (KB)', fontsize=12)
        ax2.set_title('Bytes Dropped per Node', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # 3. Timeline
        ax3 = fig.add_subplot(gs[1, 0])
        colors = plt.cm.tab10(range(len(nodes)))
        for idx, node in enumerate(nodes):
            if node in drops_timeline:
                times, cumulative = zip(*drops_timeline[node])
                ax3.plot(times, cumulative, label=f'Node {node}', 
                        linewidth=2, marker='o', markersize=4, 
                        color=colors[idx % len(colors)])
        ax3.set_ylabel('Cumulative Drops', fontsize=12)
        ax3.set_title('Drop Timeline', fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='best')
        
        # 4. Stacked Queue
        ax4 = fig.add_subplot(gs[1, 1])
        all_queues = sorted(set(q for n in nodes for q in drops_per_queue[n]))
        queue_data = {q: [drops_per_queue[n].get(q, 0) for n in nodes] for q in all_queues}
        bottom = [0] * len(nodes)
        queue_colors = plt.cm.Set3(range(len(all_queues)))
        for idx, qidx in enumerate(all_queues):
            ax4.bar(nodes, queue_data[qidx], bottom=bottom, label=f'Q{qidx}', 
                   alpha=0.8, color=queue_colors[idx % len(queue_colors)], edgecolor='black')
            bottom = [b + d for b, d in zip(bottom, queue_data[qidx])]
        ax4.set_title('Drops by Queue Index', fontsize=14, fontweight='bold')
        ax4.legend(loc='upper right', ncol=2)
    else:
        # Placeholder if no drops but PFC exists
        ax1 = fig.add_subplot(gs[0, :])
        ax1.text(0.5, 0.5, "No Packet Drops Detected", ha='center', va='center', fontsize=16)
        ax1.axis('off')
        
    # Row 3: PFC Stats
    if has_pfc:
        ax5 = fig.add_subplot(gs[2 if has_drops else 1, :])
        ax5.step(pfc_times, pfc_counts, where="post", color='purple', linewidth=2)
        ax5.set_xlabel("Time (s)", fontsize=12)
        ax5.set_ylabel(f"Pause Events / {pfc_bin_us}µs", fontsize=12)
        ax5.set_title("PFC Pause Events Over Time (Flow Control)", fontsize=14, fontweight='bold')
        ax5.grid(True, alpha=0.3)
        ax5.fill_between(pfc_times, pfc_counts, step="post", alpha=0.2, color='purple')

    fig.suptitle('Network Reliability & Flow Control Analysis', fontsize=16, fontweight='bold', y=0.98)
    
    if output_file is None:
        output_file = filename.replace(".txt", "_reliability.png") if filename else "reliability.png"
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Saved reliability analysis: {output_file}")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Plot packet drops and PFC events')
    parser.add_argument('--drops', help='Input drop trace file', default=None)
    parser.add_argument('--pfc', help='Input PFC trace file', default=None)
    parser.add_argument('-o', '--output', help='Output PNG file')
    
    args = parser.parse_args()
    
    # Support positional arg for backward compatibility
    if not args.drops and len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        args.drops = sys.argv[1]
        
    plot_packet_drops(args.drops, args.output, args.pfc)


if __name__ == "__main__":
    main()
