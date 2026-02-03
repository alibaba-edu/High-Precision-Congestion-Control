#!/usr/bin/env python3
"""Comprehensive simulation results dashboard"""
import argparse
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import sys
import os

def parse_config(config_file):
    """Parse simulation configuration"""
    config = {}
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 2:
                        config[parts[0]] = ' '.join(parts[1:])
    except:
        pass
    return config

def _select_file(base_dir, preferred, fallback):
    preferred_path = os.path.join(base_dir, preferred)
    if os.path.exists(preferred_path):
        return preferred_path
    fallback_path = os.path.join(base_dir, fallback)
    if os.path.exists(fallback_path):
        return fallback_path
    return None


def _select_file_in(base_dir, subdir, preferred, fallback):
    return _select_file(os.path.join(base_dir, subdir), preferred, fallback)


def _parse_qlen_time_blocks(qlen_file):
    """Parse qlen file with 'time:' blocks and per-link queue lengths."""
    times = []
    max_values = []

    current_time = None
    current_max = None

    with open(qlen_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('time:'):
                if current_time is not None and current_max is not None:
                    times.append(current_time / 1e9)
                    max_values.append(current_max)
                current_time = int(line.split(':')[1].strip())
                current_max = 0
                continue
            parts = line.split()
            if len(parts) >= 3 and current_time is not None:
                try:
                    qlen = int(parts[2])
                    if current_max is None:
                        current_max = qlen
                    else:
                        current_max = max(current_max, qlen)
                except ValueError:
                    continue

    if current_time is not None and current_max is not None:
        times.append(current_time / 1e9)
        max_values.append(current_max)

    return times, max_values



def plot_dashboard(base_dir='simulation/mix', output_file=None, **kwargs):
    """Create a comprehensive dashboard of simulation results"""
    
    # Read data
    qlen_times, qlen_values = [], []
    fct_data = []
    
    # Qlen logic
    qlen_file = None
    if kwargs.get('qlen_file'):
        qlen_file = kwargs['qlen_file']
    else:
        qlen_file = _select_file_in(base_dir, os.path.join('outputs', 'qlen'), 'qlen_fat_k4.txt', 'qlen.txt')
        
    if qlen_file and os.path.exists(qlen_file):
        qlen_times, qlen_values = _parse_qlen_time_blocks(qlen_file)
        if qlen_times:
            t0 = qlen_times[0]
            qlen_times = [max(0.0, t - t0) for t in qlen_times]
    
    # FCT logic
    fct_file = None
    if kwargs.get('fct_file'):
        fct_file = kwargs['fct_file']
    else:
        fct_file = _select_file_in(base_dir, os.path.join('outputs', 'fct'), 'fct_fat_k4.txt', 'fct.txt')
        
    if fct_file and os.path.exists(fct_file):
        with open(fct_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 8:
                    try:
                        fct_data.append({
                            'size': int(parts[7]),
                            'fct': int(parts[6]) / 1e6,  # ms
                            'base_fct': int(parts[4]) / 1e6,
                            'start': int(parts[5]) / 1e9  # s
                        })
                    except ValueError:
                        pass
    
    # Config Logic
    config_path = _select_file_in(base_dir, 'configs', 'config_fat_k4.txt', 'config.txt')
    # Try to deduce config from FCT filename if provided
    if fct_file and not config_path:
        # heuristic...
        pass 
    
    config = parse_config(config_path) if config_path else {}
    
    # ... rest of plotting code ...
    
    # Create dashboard
    fig = plt.figure(figsize=(16, 10))
    gs = gridspec.GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)
    
    # Title
    cc_mode = config.get('CC_MODE', 'Unknown')
    cc_names = {
        '1': 'DCQCN',
        '3': 'HPCC',
        '7': 'TIMELY',
        '8': 'DCTCP'
    }
    cc_name = cc_names.get(cc_mode, 'CC_MODE=' + cc_mode)
    
    fig.suptitle('HPCC Simulation Results Dashboard - ' + cc_name, 
                 fontsize=16, fontweight='bold')
    
    # Configuration info (top-left)
    ax_config = fig.add_subplot(gs[0, 0])
    ax_config.axis('off')
    config_text = "Configuration:\\n"
    key_params = ['CC_MODE', 'TOPOLOGY_FILE', 'FLOW_FILE', 
                  'RATE_AI', 'RATE_HAI', 'U_TARGET', 'ALPHA_RESUME_INTERVAL']
    for key in key_params:
        if key in config:
            val = config[key]
            if len(val) > 30:
                val = val[:27] + '...'
            config_text += "{}:\\n  {}\\n".format(key.replace('_', ' '), val)
    ax_config.text(0.05, 0.95, config_text, fontsize=9, family='monospace',
                   verticalalignment='top', transform=ax_config.transAxes)
    
    # Queue length over time (top-middle and top-right)
    if qlen_times:
        ax_qlen = fig.add_subplot(gs[0, 1:])
        ax_qlen.plot(qlen_times, qlen_values, linewidth=0.8, color='blue', alpha=0.7)
        ax_qlen.set_xlabel('Time (s)')
        ax_qlen.set_ylabel('Max Queue Length (bytes)')
        ax_qlen.set_title('Max Queue Length Over Time')
        ax_qlen.grid(True, alpha=0.3)
        ax_qlen.fill_between(qlen_times, qlen_values, alpha=0.2)
    
    if fct_data:
        # FCT vs Flow Size (middle-left)
        ax_fct_size = fig.add_subplot(gs[1, 0])
        sizes = [d['size'] for d in fct_data]
        fcts = [d['fct'] for d in fct_data]
        ax_fct_size.scatter(sizes, fcts, alpha=0.7, s=100, c='green', edgecolors='black')
        ax_fct_size.set_xlabel('Flow Size (bytes)')
        ax_fct_size.set_ylabel('FCT (ms)')
        ax_fct_size.set_title('Flow Completion Time')
        ax_fct_size.grid(True, alpha=0.3)
        if len(sizes) > 1:
            ax_fct_size.set_xscale('log')
            ax_fct_size.set_yscale('log')
        
        # Slowdown (middle-middle)
        ax_slowdown = fig.add_subplot(gs[1, 1])
        slowdowns = [d['fct']/d['base_fct'] if d['base_fct'] > 0 else 1 for d in fct_data]
        ax_slowdown.scatter(sizes, slowdowns, alpha=0.7, s=100, c='orange', edgecolors='black')
        ax_slowdown.set_xlabel('Flow Size (bytes)')
        ax_slowdown.set_ylabel('Slowdown (FCT/Base FCT)')
        ax_slowdown.set_title('Slowdown vs Flow Size')
        ax_slowdown.grid(True, alpha=0.3)
        ax_slowdown.axhline(y=1, color='red', linestyle='--', linewidth=2, label='Ideal')
        ax_slowdown.legend()
        if len(sizes) > 1:
            ax_slowdown.set_xscale('log')
        
        # Flow timeline (middle-right)
        ax_timeline = fig.add_subplot(gs[1, 2])
        starts = [d['start'] for d in fct_data]
        ends = [d['start'] + d['fct']/1000 for d in fct_data]  # Convert ms to s
        for i, (start, end) in enumerate(zip(starts, ends)):
            ax_timeline.barh(i, end-start, left=start, height=0.8, 
                            color='purple', alpha=0.6, edgecolor='black')
        ax_timeline.set_xlabel('Time (s)')
        ax_timeline.set_ylabel('Flow ID')
        ax_timeline.set_title('Flow Timeline')
        ax_timeline.grid(True, alpha=0.3, axis='x')
        
        # Statistics (bottom-left)
        ax_stats = fig.add_subplot(gs[2, 0])
        ax_stats.axis('off')
        stats_text = "Flow Statistics:\\n\\n"
        stats_text += "Total Flows: {}\\n\\n".format(len(fct_data))
        stats_text += "FCT (ms):\\n"
        stats_text += "  Min: {:.3f}\\n".format(min(fcts))
        stats_text += "  Max: {:.3f}\\n".format(max(fcts))
        stats_text += "  Mean: {:.3f}\\n\\n".format(sum(fcts)/len(fcts))
        stats_text += "Slowdown:\\n"
        stats_text += "  Min: {:.3f}\\n".format(min(slowdowns))
        stats_text += "  Max: {:.3f}\\n".format(max(slowdowns))
        stats_text += "  Mean: {:.3f}\\n".format(sum(slowdowns)/len(slowdowns))
        ax_stats.text(0.1, 0.95, stats_text, fontsize=10, family='monospace',
                     verticalalignment='top', transform=ax_stats.transAxes)
        
        # FCT Distribution (bottom-middle)
        ax_hist = fig.add_subplot(gs[2, 1])
        ax_hist.hist(fcts, bins=max(5, len(fcts)//2), alpha=0.7, color='teal', 
                     edgecolor='black')
        ax_hist.set_xlabel('FCT (ms)')
        ax_hist.set_ylabel('Count')
        ax_hist.set_title('FCT Distribution')
        ax_hist.grid(True, alpha=0.3, axis='y')
        
        # Slowdown Distribution (bottom-right)
        ax_slow_hist = fig.add_subplot(gs[2, 2])
        ax_slow_hist.hist(slowdowns, bins=max(5, len(slowdowns)//2), alpha=0.7, 
                         color='coral', edgecolor='black')
        ax_slow_hist.set_xlabel('Slowdown')
        ax_slow_hist.set_ylabel('Count')
        ax_slow_hist.set_title('Slowdown Distribution')
        ax_slow_hist.grid(True, alpha=0.3, axis='y')
    
    # Save
    if output_file is None:
        output_file = os.path.join(base_dir, 'outputs', 'dashboard.png')
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print("Dashboard saved to: " + output_file)
    plt.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create a comprehensive simulation results dashboard")
    parser.add_argument("--base-dir", default="simulation/mix", help="Base directory for simulation data")
    parser.add_argument("--out", default=None, help="Output PNG path")
    parser.add_argument("--fct", default=None, help="Explicit path to FCT file")
    parser.add_argument("--qlen", default=None, help="Explicit path to qlen file")
    args = parser.parse_args()

    # Pass args to main func using kwargs since signature is positional
    plot_dashboard(args.base_dir, args.out, fct_file=args.fct, qlen_file=args.qlen)
