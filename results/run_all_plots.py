#!/usr/bin/env python3
"""
Master plotting script - generates all simulation analysis plots
Runs all major visualization scripts in sequence
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Get results directory
RESULTS_DIR = Path(__file__).parent.resolve()
DATA_DIR = RESULTS_DIR / "data"
PLOTS_DIR = RESULTS_DIR / "plots"
SCRIPTS_DIR = RESULTS_DIR / "scripts"

# Ensure plots directory exists
PLOTS_DIR.mkdir(exist_ok=True)

# List of all plot scripts to run (order matters for dependencies)
PLOT_SCRIPTS = [
    ("plot_topology.py", "Network Topology Visualization"),
    ("plot_qlen.py", "Queue Length Analysis"),
    ("plot_fct.py", "Flow Completion Time Analysis"),
    ("plot_cwnd.py", "Congestion Window Analysis"),
    ("plot_rx_buffer.py", "RX Buffer Occupancy"),
    ("plot_cwnd_rtt_analysis.py", "CWND Analysis Dashboard"),
    ("plot_queue_metrics.py", "Queue Metrics"),
    ("plot_switch_throughput.py", "Switch Throughput"),
    ("plot_dashboard.py", "Comprehensive Dashboard"),
]

def find_data_files():
    """Find all relevant data files in the data directory"""
    data_files = {}
    
    # Look for key data files
    for file in DATA_DIR.glob("*.txt"):
        if "fat" in file.name or "topology" in file.name:
            continue
        data_files[file.name] = file
    
    return data_files

def run_plot_script(script_name, description, data_files):
    """Run a single plot script with available data files"""
    script_path = SCRIPTS_DIR / script_name
    
    if not script_path.exists():
        print(f"⚠️  Skipping {description}: Script not found")
        return False
    
    print(f"\n{'='*70}")
    print(f"Running: {description}")
    print(f"Script: {script_name}")
    print(f"{'='*70}")
    
    try:
        # Special handling for scripts with specific requirements
        if "topology" in script_name:
            # This script visualizes the network topology
            # Use the topology that matches the flows being tested
            topo_file = (RESULTS_DIR.parent / "simulation" / "mix" / "topologies" / "topology_two_senders.txt").resolve()
            
            if not topo_file.exists():
                # Fallback to data folder topology if primary doesn't exist
                topo_file = DATA_DIR / "topology.txt"
            
            if topo_file.exists():
                # First: Full topology
                cmd = [sys.executable, str(script_path), 
                       str(topo_file),
                       "--out", str(PLOTS_DIR / "topology_full.png")]
                
                print(f"Generating full topology from: {topo_file.name}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    if result.stdout:
                        print(result.stdout)
                
                # Second: Flow-specific topology
                flows_file = (RESULTS_DIR / ".." / "simulation" / "mix" / "flows" / "flow_two_senders_heavy.txt").resolve()
                if flows_file.exists():
                    cmd = [sys.executable, str(script_path), 
                           str(topo_file),
                           "--flows", str(flows_file),
                           "--out", str(PLOTS_DIR / "topology_flows.png")]
                    
                    print(f"Generating flow-specific topology...")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        if result.stdout:
                            print(result.stdout)
                        print(f"✓ {description} completed successfully (both full and flow topologies)")
                        return True
                
                print(f"✓ {description} completed successfully (full topology generated)")
                return True
            else:
                print(f"⚠️  Skipping {description}: Topology file not found")
                return False
        
        elif "queue_metrics" in script_name:
            # This script needs --qlen and optionally --pfc flags
            qlen_file = DATA_DIR / "qlen_two_senders_heavy.txt"
            pfc_file = DATA_DIR / "pfc_two_senders_heavy.txt"
            
            if qlen_file.exists():
                cmd = [sys.executable, str(script_path), "--qlen", str(qlen_file)]
                if pfc_file.exists():
                    cmd.extend(["--pfc", str(pfc_file)])
                print(f"Command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print(f"✓ {description} completed successfully")
                    if result.stdout:
                        print(result.stdout)
                    return True
        
        elif "switch_throughput" in script_name:
            # This script needs --trace, --topo, and --flows flags
            trace_file = DATA_DIR / "mix_two_senders_heavy.tr"
            topo_file = RESULTS_DIR.parent / "simulation" / "mix" / "topologies" / "topology_two_senders.txt"
            flows_file = (RESULTS_DIR / ".." / "simulation" / "mix" / "flows" / "flow_two_senders_heavy.txt").resolve()
            
            if trace_file.exists() and topo_file.exists() and flows_file.exists():
                cmd = [sys.executable, str(script_path), 
                       "--trace", str(trace_file),
                       "--topo", str(topo_file),
                       "--flows", str(flows_file),
                       "--out", str(PLOTS_DIR / "switch_throughput.png")]
                
                print(f"Command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    print(f"✓ {description} completed successfully")
                    if result.stdout:
                        print(result.stdout)
                    return True
                else:
                    print(f"✗ {description} failed")
                    if result.stderr:
                        print(f"Error: {result.stderr[:300]}")
                    return False
            else:
                missing = []
                if not trace_file.exists():
                    missing.append("trace")
                if not topo_file.exists():
                    missing.append("topology")
                if not flows_file.exists():
                    missing.append(f"flows ({flows_file})")
                print(f"⚠️  Skipping {description}: Missing files: {', '.join(missing)}")
                return False
        
        elif "cwnd_rtt_analysis" in script_name:
            # This script generates CWND/RTT analysis dashboard
            cwnd_file = DATA_DIR / "cwnd_two_senders_heavy.txt"
            config_file = RESULTS_DIR.parent / "simulation" / "mix" / "configs" / "config_two_senders.txt"
            topo_file = RESULTS_DIR.parent / "simulation" / "mix" / "topologies" / "topology_two_senders.txt"
            
            if cwnd_file.exists():
                cmd = [sys.executable, str(script_path), 
                           str(cwnd_file),
                           str(PLOTS_DIR / "cwnd_rtt_analysis.png"),
                           str(config_file),
                           str(topo_file)]
                
                print(f"Command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    print(f"✓ {description} completed successfully")
                    if result.stdout:
                        print(result.stdout)
                    return True
                else:
                    print(f"✗ {description} failed")
                    if result.stderr:
                        print(f"Error: {result.stderr[:300]}")
                    return False
            else:
                print(f"⚠️  Skipping {description}: CWND data file not found ({cwnd_file})")
                return False

        elif "plot_rx_buffer" in script_name or "rx_buffer" in script_name:
            # This script needs RX buffer trace
            rxbuf_file = DATA_DIR / "rxbuf_two_senders_heavy.txt"
            if rxbuf_file.exists():
                cmd = [sys.executable, str(script_path), str(rxbuf_file)]
                print(f"Command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    print(f"✓ {description} completed successfully")
                    if result.stdout:
                        print(result.stdout)
                    return True
                else:
                    print(f"✗ {description} failed")
                    if result.stderr:
                        print(f"Error: {result.stderr[:300]}")
                    return False
            else:
                print(f"⚠️  Skipping {description}: RX buffer file not found ({rxbuf_file})")
                return False
        
        # Default behavior: try to find matching data file
        for data_file in sorted(data_files):
            cmd = [sys.executable, str(script_path), str(DATA_DIR / data_file)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(f"✓ {description} completed successfully")
                if result.stdout:
                    print(result.stdout)
                return True
        
        # If no data files worked, try running without arguments
        print("Attempting to run without arguments...")
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✓ {description} completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"✗ {description} failed")
            if result.stderr:
                print(f"Error: {result.stderr[:300]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"✗ {description} timed out")
        return False
    except Exception as e:
        print(f"✗ {description} encountered error: {e}")
        return False

def main():
    """Main function to run all plots"""
    print("\n" + "="*70)
    print("HPCC Simulation - Master Plotting Script")
    print("="*70)
    
    # Check if data directory exists
    if not DATA_DIR.exists():
        print(f"❌ Data directory not found: {DATA_DIR}")
        sys.exit(1)
    
    # Find available data files
    data_files = find_data_files()
    
    if not data_files:
        print("⚠️  No data files found in data directory")
    else:
        print(f"\n📊 Found {len(data_files)} data file(s):")
        for fname in sorted(data_files.keys()):
            print(f"   - {fname}")
    
    # Run all plot scripts
    results = {}
    for script_name, description in PLOT_SCRIPTS:
        results[description] = run_plot_script(script_name, description, data_files.keys())
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    
    for description, success in results.items():
        status = "✓" if success else "✗"
        print(f"{status} {description}")
    
    print(f"\nCompleted: {successful}/{total} scripts")
    
    # Move generated plots to plots directory
    print(f"\n{'='*70}")
    print("Organizing plots...")
    print(f"{'='*70}")
    
    png_files_moved = 0
    
    # Search for PNG files in multiple locations
    search_paths = [
        DATA_DIR,
        RESULTS_DIR / "simulation" / "mix" / "outputs",
        RESULTS_DIR / "plots",
    ]
    
    for search_path in search_paths:
        if search_path.exists():
            for png_file in search_path.glob("*.png"):
                # Skip if already in plots folder
                if png_file.parent == PLOTS_DIR:
                    continue
                
                dest = PLOTS_DIR / png_file.name
                try:
                    shutil.move(str(png_file), str(dest))
                    print(f"✓ Moved: {png_file.name}")
                    png_files_moved += 1
                except Exception as e:
                    print(f"✗ Failed to move {png_file.name}: {e}")
    
    print(f"\nMoved {png_files_moved} plot file(s) to plots/ directory")
    
    if successful == total:
        print("\n✓ All plotting scripts completed successfully!")
        print(f"✓ Plots organized in: {PLOTS_DIR}")
        return 0
    else:
        print(f"\n⚠️  {total - successful} script(s) failed or were skipped")
        print(f"✓ Generated plots available in: {PLOTS_DIR}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
