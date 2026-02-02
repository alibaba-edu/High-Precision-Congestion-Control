#!/usr/bin/env python3
"""
Organize simulation results with timestamps
Creates timestamped result directories for multiple runs
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime

def organize_results(sim_dir='simulation/mix', results_base='results'):
    """
    Organize results from a simulation run into timestamped directory
    
    Args:
        sim_dir: Directory containing simulation output files
        results_base: Base results directory
    """
    
    # Create timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Create timestamped results directory
    run_dir = os.path.join(results_base, 'runs', timestamp)
    os.makedirs(os.path.join(run_dir, 'plots'), exist_ok=True)
    os.makedirs(os.path.join(run_dir, 'data'), exist_ok=True)
    
    print("Organizing results for run: {}".format(timestamp))
    print("Output directory: {}".format(run_dir))
    
    # Copy data files
    data_files = ['fct.txt', 'qlen.txt', 'pfc.txt', 'config.txt', 'cwnd.txt', 'rxbuf.txt', 'drop.txt']
    for fname in data_files:
        src = os.path.join(sim_dir, fname)
        if os.path.exists(src):
            dst = os.path.join(run_dir, 'data', fname)
            shutil.copy2(src, dst)
            print("  Copied: {}".format(fname))
    
    # Copy trace file if it exists
    trace_src = os.path.join(sim_dir, 'mix.tr')
    if os.path.exists(trace_src):
        trace_dst = os.path.join(run_dir, 'data', 'mix.tr')
        shutil.copy2(trace_src, trace_dst)
        print("  Copied: mix.tr")
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    
    # Get the script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Generate plots
    if os.path.exists(os.path.join(run_dir, 'data', 'qlen.txt')):
        qlen_file = os.path.join(run_dir, 'data', 'qlen.txt')
        output = os.path.join(run_dir, 'plots', 'qlen.png')
        try:
            subprocess.run(['python3', 'scripts/plot_qlen.py', qlen_file], 
                         cwd=results_base, check=True, capture_output=True)
            # Move to run directory
            if os.path.exists(os.path.join(results_base, 'plots', 'qlen.png')):
                shutil.move(os.path.join(results_base, 'plots', 'qlen.png'), 
                           output)
            print("  Generated: qlen.png")
        except Exception as e:
            print("  Error generating qlen plot: {}".format(str(e)))
    
    if os.path.exists(os.path.join(run_dir, 'data', 'fct.txt')):
        fct_file = os.path.join(run_dir, 'data', 'fct.txt')
        output = os.path.join(run_dir, 'plots', 'fct.png')
        try:
            subprocess.run(['python3', 'scripts/plot_fct.py', fct_file],
                         cwd=results_base, check=True, capture_output=True)
            # Move to run directory
            if os.path.exists(os.path.join(results_base, 'plots', 'fct.png')):
                shutil.move(os.path.join(results_base, 'plots', 'fct.png'),
                           output)
            print("  Generated: fct.png")
        except Exception as e:
            print("  Error generating fct plot: {}".format(str(e)))
    
    # Generate dashboard
    try:
        subprocess.run(['python3', 'scripts/plot_dashboard.py'],
                     cwd=run_dir, check=True, capture_output=True)
        dashboard_src = os.path.join(run_dir, 'plots', 'dashboard.png')
        if os.path.exists(dashboard_src):
            print("  Generated: dashboard.png")
        else:
            # Try alternate location
            alt_src = os.path.join(run_dir, 'data', 'dashboard.png')
            if os.path.exists(alt_src):
                shutil.move(alt_src, dashboard_src)
                print("  Generated: dashboard.png")
    except Exception as e:
        print("  Error generating dashboard: {}".format(str(e)))
    
    # Create index file
    index_content = """# Results for Run: {}

## Quick Links
- [Full Dashboard](plots/dashboard.png)
- [FCT Analysis](plots/fct.png)
- [Queue Length](plots/qlen.png)

## Data Files
- [fct.txt](data/fct.txt) - Flow completion times
- [qlen.txt](data/qlen.txt) - Queue length samples
- [config.txt](data/config.txt) - Simulation configuration

## Command
```
./waf --run 'scratch/third mix/config.txt'
```

## Results Generated
{}
""".format(timestamp, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    index_file = os.path.join(run_dir, 'INDEX.md')
    with open(index_file, 'w') as f:
        f.write(index_content)
    
    print("\nOrganization complete!")
    print("Results saved to: {}".format(run_dir))
    print("View plots: {}".format(os.path.join(run_dir, 'plots')))
    
    return run_dir

def list_runs(results_base='results'):
    """List all organized runs"""
    runs_dir = os.path.join(results_base, 'runs')
    if not os.path.exists(runs_dir):
        print("No runs directory found")
        return
    
    runs = sorted(os.listdir(runs_dir), reverse=True)
    print("Organized simulation runs:")
    print("-" * 60)
    for i, run in enumerate(runs[:10], 1):  # Show last 10
        run_path = os.path.join(runs_dir, run)
        plot_dir = os.path.join(run_path, 'plots')
        plots = len([f for f in os.listdir(plot_dir) if f.endswith('.png')]) if os.path.exists(plot_dir) else 0
        print("{}. {} ({} plots)".format(i, run, plots))

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--list':
        list_runs()
    else:
        sim_dir = sys.argv[1] if len(sys.argv) > 1 else 'simulation/mix'
        organize_results(sim_dir)
