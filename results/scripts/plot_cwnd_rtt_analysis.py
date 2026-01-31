#!/usr/bin/env python3
"""
Generate comprehensive CWND/Rate/RTT analysis dashboard.
Dynamically adapts to any simulation data - robust for different topologies/flows.

Input:
  - cwnd_data_file: CWND trace file (time_ns, src, dst, sport, dport, rate_bps, win_bytes)
  - output_file: Output PNG path

Features:
  - Plots all flows in Window over Time panel
  - Extracts RTT from steady-state data
  - Rate vs CWND mathematical relationship
  - Per-flow throughput distribution
  - RTT component breakdown
"""
import sys
import statistics
from pathlib import Path
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np


def _extract_steady_state_period(data):
    """Find the steady-state period where transmission is active."""
    times = [t for t, _, _, _, _ in data]
    if not times:
        return None, None
    
    # Steady state is roughly in the middle 50% of active transmission
    t_min, t_max = min(times), max(times)
    duration = t_max - t_min
    steady_start = t_min + duration * 0.2  # Skip first 20%
    steady_end = t_min + duration * 0.9    # Use up to 90%
    
    return steady_start, steady_end


def _calculate_rtt_from_cwnd_data(cwnd_file):
    """Extract RTT from steady-state CWND data using rate = cwnd * 8 / RTT."""
    rtt_samples = []
    
    with open(cwnd_file, 'r') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 7:
                continue
            try:
                t_ns = int(parts[0])
                rate = int(parts[5])
                win = int(parts[6])
                t_s = t_ns / 1e9
                
                # Use steady-state period (middle 70% of transmission)
                if rate > 0 and win > 0:
                    rtt = (win * 8) / rate
                    rtt_samples.append(rtt)
            except (ValueError, IndexError):
                continue
    
    if rtt_samples:
        # Use median to avoid outliers
        return statistics.median(rtt_samples)
    return None


def _parse_cwnd_file(cwnd_file):
    """Parse CWND file and return flows with their data."""
    flows = defaultdict(lambda: {"t": [], "win": [], "rate": []})
    
    with open(cwnd_file, 'r') as f:
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
                rate = int(parts[5])
                win = int(parts[6])
                
                key = (src, dst, sport, dport)
                flows[key]["t"].append(t_ns / 1e9)
                flows[key]["win"].append(win)
                flows[key]["rate"].append(rate)
            except (ValueError, IndexError):
                continue
    
    return flows


def _parse_fct_file(fct_file_path):
    """Parse FCT file to get actual throughput per flow."""
    throughput_map = {}
    try:
        with open(fct_file_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 8:
                    # Format: src_ip dst_ip sport dport size start_time complete_time base_rtt
                    sport = int(parts[2])
                    dport = int(parts[3])
                    size_bytes = int(parts[4])
                    start_ns = int(parts[5])
                    complete_ns = int(parts[6])
                    
                    # Extract src/dst from IP (0b000X01 format)
                    src_ip = parts[0]
                    dst_ip = parts[1]
                    src = int(src_ip[5], 16) if len(src_ip) >= 6 else 0
                    dst = int(dst_ip[5], 16) if len(dst_ip) >= 6 else 0
                    
                    duration_s = (complete_ns - start_ns) / 1e9
                    if duration_s > 0:
                        throughput_bps = (size_bytes * 8) / duration_s
                        throughput_map[(src, dst, sport, dport)] = throughput_bps
    except FileNotFoundError:
        pass
    return throughput_map


def _get_steady_state_stats(flows, fct_throughput_map=None):
    """Calculate steady-state CWND and rate for each flow."""
    stats = {}
    
    for flow_key, data in flows.items():
        times = data["t"]
        wins = data["win"]
        rates = data["rate"]
        
        if not times:
            continue
        
        # Find steady state (middle 70% of transmission)
        t_min, t_max = min(times), max(times)
        duration = t_max - t_min
        steady_start = t_min + duration * 0.15
        steady_end = t_max - duration * 0.1
        
        # Extract steady-state samples
        steady_wins = [w for t, w in zip(times, wins) if steady_start <= t <= steady_end and w > 0]
        steady_rates = [r for t, r in zip(times, rates) if steady_start <= t <= steady_end and r > 0]
        
        if steady_wins and steady_rates:
            stats[flow_key] = {
                "cwnd_avg": statistics.mean(steady_wins),
                "rate_avg": statistics.mean(steady_rates),  # HPCC target rate
                "fct": t_max  # Flow completion time
            }
            
            # Add actual throughput if available from FCT
            if fct_throughput_map and flow_key in fct_throughput_map:
                stats[flow_key]["actual_throughput"] = fct_throughput_map[flow_key]
    
    return stats


def _parse_rate_to_bps(rate_str):
    if rate_str is None:
        return None
    s = str(rate_str).strip()
    try:
        return float(s)
    except ValueError:
        pass
    s = s.lower()
    if s.endswith("gbps"):
        return float(s[:-4]) * 1e9
    if s.endswith("mbps"):
        return float(s[:-4]) * 1e6
    if s.endswith("kbps"):
        return float(s[:-4]) * 1e3
    if s.endswith("bps"):
        return float(s[:-3])
    return None


def _parse_config(config_path):
    cfg = {}
    if not config_path or not Path(config_path).exists():
        return cfg
    with open(config_path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("{") or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            key = parts[0]
            value = parts[1]
            cfg[key] = value
    return cfg


def _parse_topology_min_rate(topo_path):
    if not topo_path or not Path(topo_path).exists():
        return None
    rates = []
    with open(topo_path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 5:
                rate_bps = _parse_rate_to_bps(parts[2])
                if rate_bps:
                    rates.append(rate_bps)
    return min(rates) if rates else None


def _compute_host_delay_us(pkt_size_bytes, line_rate_bps, rx_pull_rate):
    if not pkt_size_bytes or not line_rate_bps or rx_pull_rate is None:
        return 0.0
    if rx_pull_rate >= 1.0:
        return 0.0
    base_time = (pkt_size_bytes * 8.0) / line_rate_bps
    pull_time = (pkt_size_bytes * 8.0) / (line_rate_bps * rx_pull_rate)
    extra = pull_time - base_time
    return max(extra * 1e6, 0.0)


def plot_cwnd_rtt_analysis(cwnd_file, output_file, config_path=None, topo_path=None):
    """Generate comprehensive CWND/Rate/RTT analysis dashboard."""
    
    # Parse data
    flows = _parse_cwnd_file(cwnd_file)
    if not flows:
        print("ERROR: No flows found in CWND file")
        return
    
    # Try to load FCT data for actual throughput
    fct_file = cwnd_file.replace('cwnd_', 'fct_')
    fct_throughput_map = _parse_fct_file(fct_file)
    
    # Get statistics
    stats = _get_steady_state_stats(flows, fct_throughput_map)
    rtt = _calculate_rtt_from_cwnd_data(cwnd_file)
    rtt_us = rtt * 1e6 if rtt else None
    
    # Prepare data
    max_win = max([max(data["win"]) for data in flows.values() if data["win"]])
    
    # Determine units
    if max_win >= 1e6:
        win_unit, win_scale = "KB", 1024
    else:
        win_unit, win_scale = "B", 1
    
    # Create figure with single plot
    fig = plt.figure(figsize=(12, 6))
    
    # Add spacing at top for title
    fig.suptitle('CWND Analysis', 
                 fontsize=16, fontweight='bold', y=0.96)
    
    # CWND vs Time (all flows)
    ax1 = plt.subplot(111)
    colors = ['blue', 'red', 'green', 'orange', 'purple', 'brown']
    linestyles = ['-', '--', '-.', ':', '-', '--']
    
    for idx, (flow_key, data) in enumerate(sorted(flows.items())):
        src, dst, sport, dport = flow_key
        label = f"Flow {src}→{dst} ({sport}→{dport})"
        
        y = [w / win_scale for w in data["win"]]
        line_style = linestyles[idx % len(linestyles)]
        color = colors[idx % len(colors)]
        
        ax1.plot(data["t"], y, label=label, linewidth=2, 
                linestyle=line_style, color=color)
    
    # Mark FCT for primary flow
    if flows:
        first_flow = list(flows.values())[0]
        fct = max(first_flow["t"])
        ax1.axvline(x=fct, color='green', linestyle='--', alpha=0.6, linewidth=1.5, label='FCT')
    
    ax1.set_xlabel('Time (s)', fontsize=11, fontweight='bold')
    ax1.set_ylabel(f'CWND ({win_unit})', fontsize=11, fontweight='bold')
    ax1.set_title('Window Size Over Time', fontsize=12, fontweight='bold', pad=10)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best', fontsize=9)
    ax1.set_ylim([0, max_win / win_scale * 1.25])
    
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✓ Analysis dashboard saved to: {output_file}")
    
    if config_path:
        print(f"  Config: {config_path}")
    if topo_path:
        print(f"  Topology: {topo_path}")
    print(f"  Flows: {len(flows)}")
    for idx, (flow_key, stat) in enumerate(sorted(stats.items())):
        src, dst = flow_key[0], flow_key[1]
        if "actual_throughput" in stat:
            throughput_str = f"{stat['actual_throughput']/1e9:.3f} Gbps (actual)"
        else:
            throughput_str = f"{stat['rate_avg']/1e9:.3f} Gbps (target)"
        print(f"    Flow {src}→{dst}: {throughput_str}, "
              f"CWND: {stat['cwnd_avg']/1024:.2f} KB")
    
    plt.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cwnd_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else cwnd_file.replace('.txt', '_analysis.png')
        config_path = sys.argv[3] if len(sys.argv) > 3 else None
        topo_path = sys.argv[4] if len(sys.argv) > 4 else None
    else:
        base = Path(__file__).resolve().parents[1]
        cwnd_file = str(base / "data" / "cwnd_two_senders_heavy.txt")
        output_file = str(base / "plots" / "cwnd_rtt_analysis.png")
        config_path = str(base.parent / "simulation" / "mix" / "configs" / "config_two_senders.txt")
        topo_path = str(base.parent / "simulation" / "mix" / "topologies" / "topology_two_senders.txt")

    plot_cwnd_rtt_analysis(cwnd_file, output_file, config_path=config_path, topo_path=topo_path)
