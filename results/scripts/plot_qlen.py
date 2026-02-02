#!/usr/bin/env python
"""Quick visualization of queue length data per link"""
import argparse
import matplotlib.pyplot as plt
import sys

def plot_qlen(filename, output_file=None):
    # Format: First line "time: <nanoseconds>"
    # Then lines of "<sw> <port> <cnt_bin0> <cnt_bin1> ..." (histogram in KB bins)
    qlen_per_link = {}
    current_time = None

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            if line.startswith('time:'):
                current_time = int(line.split(':')[1].strip())
                continue

            parts = line.split()
            if len(parts) >= 3 and current_time is not None:
                try:
                    src = int(parts[0])
                    dest = int(parts[1])
                    counts = [int(x) for x in parts[2:]]
                except:
                    continue

                total_samples = 0
                total_bytes = 0
                for kb, cnt in enumerate(counts):
                    if cnt <= 0:
                        continue
                    total_samples += cnt
                    total_bytes += cnt * kb * 1000

                qlen = (total_bytes / total_samples) if total_samples > 0 else 0.0

                link = (src, dest)
                if link not in qlen_per_link:
                    qlen_per_link[link] = {'times': [], 'qlen': []}

                qlen_per_link[link]['times'].append(current_time / 1e9)  # Convert to seconds
                qlen_per_link[link]['qlen'].append(qlen)
    
    if not qlen_per_link:
        print("No data found in file")
        return
    
    plt.figure(figsize=(12, 6))
    
    # Plot all links (only if they have congestion)
    plotted = 0
    global_min = None
    for data in qlen_per_link.values():
        if data['times']:
            local_min = min(data['times'])
            global_min = local_min if global_min is None else min(global_min, local_min)

    for link, data in sorted(qlen_per_link.items()):
        if data['qlen'] and max(data['qlen']) > 0:
            if global_min is not None:
                shifted = [max(0.0, t - global_min) for t in data['times']]
            else:
                shifted = data['times']
            plt.plot(shifted, data['qlen'], marker='o', label=f'Link {link[0]}->{link[1]}', alpha=0.7)
            plotted += 1
    
    plt.xlabel('Time (s)')
    plt.ylabel('Queue Length (bytes)')
    plt.title('Average Queue Length Over Time (per Link)')
    plt.grid(True, alpha=0.3)
    if plotted > 1:
        plt.legend()
    plt.tight_layout()
    
    if output_file is None:
        output_file = filename.replace('.txt', '.png')
    plt.savefig(output_file, dpi=150)
    print(f"Plot saved to: {output_file} ({plotted} links with congestion)")
    plt.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Plot queue length data per link")
    parser.add_argument("input", nargs="?", default="simulation/mix/outputs/qlen/qlen.txt",
                        help="Path to qlen data file")
    parser.add_argument("--out", default=None, help="Output PNG path")
    args = parser.parse_args()

    plot_qlen(args.input, args.out)
