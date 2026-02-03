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



def _parse_schedules(config_file):
    """Parse config file to extract RX_PULL_RATE_SCHEDULE."""
    schedules = {}
    if not config_file or not Path(config_file).exists():
        return schedules
    
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#'): continue
            if 'RX_PULL_RATE_SCHEDULE' in line:
                parts = line.split()
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
                    except ValueError: pass
    return schedules

# helper for plotting lines
def _draw_lines(ax, schedules):
    # determine y-limit to place text
    ylim = ax.get_ylim()
    ymax = ylim[1]
    for node_id, schedule in schedules.items():
            for time, rate in schedule:
                ax.axvline(x=time, color='gray', linestyle=':', alpha=0.8, linewidth=1.5)
                ax.text(time, ymax * 0.98, f' t={time}s\nRate={rate}', rotation=90, 
                        verticalalignment='top', fontsize=8, color='black', alpha=0.7)


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
    
    # Parse schedules
    schedules = _parse_schedules(config_path) if config_path else {}

    # Prepare data
    max_win = max([max(data["win"]) for data in flows.values() if data["win"]])
    
    # Determine units
    if max_win >= 1e6:
        win_unit, win_scale = "KB", 1024
    else:
        win_unit, win_scale = "B", 1
    
    # Get line rate from topology
    line_rate_bps = _parse_topology_min_rate(topo_path) if topo_path else 1e9  # Default 1 Gbps
    
    # Create figure with three plots
    fig = plt.figure(figsize=(12, 14))
    
    # Add spacing at top for title
    fig.suptitle('CWND and Rate Analysis', 
                 fontsize=16, fontweight='bold', y=0.96)
    
    # CWND vs Time (all flows)
    ax1 = plt.subplot(311)
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
    if schedules: _draw_lines(ax1, schedules)
    
    # Rate vs Time (senders only - nodes 0 and 1)
    ax2 = plt.subplot(312)
    
    for idx, (flow_key, data) in enumerate(sorted(flows.items())):
        src, dst, sport, dport = flow_key
        # Only plot senders (src nodes 0 and 1)
        if src not in [0, 1]:
            continue
            
        label = f"Sender {src} (port {sport})"
        
        # Convert rate to Gbps
        y = [r / 1e9 for r in data["rate"]]
        line_style = linestyles[idx % len(linestyles)]
        color = colors[idx % len(colors)]
        
        ax2.plot(data["t"], y, label=label, linewidth=2, 
                linestyle=line_style, color=color)
    
    # Add line rate reference
    if line_rate_bps:
        line_rate_gbps = line_rate_bps / 1e9
        ax2.axhline(y=line_rate_gbps, color='red', linestyle='--', 
                   alpha=0.5, linewidth=2, label=f'Line Rate ({line_rate_gbps:.1f} Gbps)')
    
    ax2.set_xlabel('Time (s)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Sending Rate (Gbps)', fontsize=11, fontweight='bold')
    ax2.set_title('Sender Rates Over Time', fontsize=12, fontweight='bold', pad=10)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='best', fontsize=9)
    
    # Set y-axis limit to 1.1 * line_rate
    if line_rate_bps:
        ax2.set_ylim([0, line_rate_gbps * 1.1])
    if schedules: _draw_lines(ax2, schedules)
    
    # RTT vs Time (all flows)
    ax3 = plt.subplot(313)
    
    for idx, (flow_key, data) in enumerate(sorted(flows.items())):
        src, dst, sport, dport = flow_key
        label = f"Flow {src}→{dst} ({sport})"
        
        # Calculate RTT for this flow dynamically
        # RTT = (Win * 8) / Rate
        rtt_us_series = []
        t_series = []
        for t, w, r in zip(data["t"], data["win"], data["rate"]):
            if r > 0 and w > 0:
                val = (w * 8.0 * 1e6) / r
                # Basic outlier filter (ignore crazy spikes > 1ms for readability if desired, but raw is usually better)
                rtt_us_series.append(val)
                t_series.append(t)

        line_style = linestyles[idx % len(linestyles)]
        color = colors[idx % len(colors)]
        
        if rtt_us_series:
            ax3.plot(t_series, rtt_us_series, label=label, linewidth=1.5,
                    linestyle=line_style, color=color, alpha=0.9)
    
    ax3.set_xlabel('Time (s)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('RTT (µs)', fontsize=11, fontweight='bold')
    ax3.set_title('Round Trip Time Over Time', fontsize=12, fontweight='bold', pad=10)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc='best', fontsize=9)
    if schedules: _draw_lines(ax3, schedules)

    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
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
