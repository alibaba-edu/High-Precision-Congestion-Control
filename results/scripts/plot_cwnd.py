#!/usr/bin/env python
"""Plot cwnd-like window trace per flow.

Input format (per line):
<time_ns> <src> <dst> <sport> <dport> <rate_bps> <win_bytes>

Includes RTT calculation and annotation:
  Rate (Gbps) = Window (bytes) * 8 / RTT (seconds)
  RTT = Window (bytes) * 8 / Rate (Gbps)
"""
import sys
import matplotlib.pyplot as plt
import statistics

def _pick_unit(max_val):
    if max_val >= 1e9:
        return "GB", 1e9
    if max_val >= 1e6:
        return "MB", 1e6
    if max_val >= 1e3:
        return "KB", 1e3
    return "B", 1


def _calculate_rtt_from_data(filename):
    """Calculate RTT from cwnd data using rate = cwnd * 8 / RTT.
    
    RTT = cwnd * 8 / rate (for steady-state period)
    """
    rtt_samples = []
    
    with open(filename, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 7:
                continue
            try:
                t_ns = int(parts[0])
                rate = int(parts[5])
                win = int(parts[6])
                t_s = t_ns / 1e9
                
                # Use steady-state period (after initial ramp-up, before flow complete)
                if 1.2 <= t_s <= 1.8 and rate > 0 and win > 0:
                    rtt = (win * 8) / rate  # in seconds
                    rtt_samples.append(rtt)
            except (ValueError, IndexError):
                continue
    
    if rtt_samples:
        # Use median to ignore outliers
        rtt_avg = statistics.median(rtt_samples)
        return rtt_avg
    return None


def plot_cwnd(filename):
    flows = {}
    max_win = 0
    rates_by_flow = {}  # Store rates for RTT calculation
    
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 7:
                continue
            try:
                t_ns = int(parts[0])
                src = int(parts[1])
                dst = int(parts[2])
                sport = int(parts[3])
                dport = int(parts[4])
                rate = int(parts[5])
                win = int(parts[6])
            except ValueError:
                continue
            key = (src, dst, sport, dport)
            if key not in flows:
                flows[key] = {"t": [], "win": [], "rate": []}
                rates_by_flow[key] = []
            flows[key]["t"].append(t_ns / 1e9)
            flows[key]["win"].append(win)
            flows[key]["rate"].append(rate)
            rates_by_flow[key].append(rate)
            if win > max_win:
                max_win = win

    if not flows:
        print("No data found in file")
        return

    unit, scale = _pick_unit(max_win)
    
    # Calculate RTT from the data
    rtt = _calculate_rtt_from_data(filename)
    rtt_us = rtt * 1e6 if rtt else None

    plt.figure(figsize=(12, 7))
    ax = plt.gca()
    
    for (src, dst, sport, dport), data in sorted(flows.items()):
        y = [w / scale for w in data["win"]]
        label = f"{src}->{dst} ({sport}->{dport})"
        plt.plot(data["t"], y, label=label, linewidth=1.5)

    plt.xlabel("Time (s)")
    plt.ylabel(f"Window ({unit})")
    plt.title("CWND-like Window Over Time")
    plt.grid(True, alpha=0.3)
    plt.ylim(0, (max_win / scale) * 1.25)
    
    # Add RTT annotation
    if rtt_us is not None:
        textstr = f"RTT ≈ {rtt_us:.2f} μs\n"
        textstr += f"Relationship: Rate (bps) = Window (bytes) × 8 / RTT (s)"
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        print(f"Calculated RTT from data: {rtt_us:.2f} μs ({rtt*1e9:.0f} ns)")
    
    if len(flows) > 1:
        plt.legend()
    plt.tight_layout()

    output_file = filename.replace(".txt", ".png")
    if output_file == filename:
        output_file = filename + ".png"
    plt.savefig(output_file, dpi=150)
    print(f"Plot saved to: {output_file}")
    plt.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        plot_cwnd(sys.argv[1])
    else:
        plot_cwnd("simulation/mix/outputs/cwnd/cwnd.txt")
