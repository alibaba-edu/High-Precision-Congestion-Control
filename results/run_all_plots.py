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
    # ("plot_qlen.py", "Queue Length Analysis"), # Unified into queue metrics
    ("plot_fct.py", "Flow Completion Time Analysis"),
    ("plot_rx_buffer.py", "RX Buffer Occupancy"),
    ("plot_packet_drops.py", "Packet Drop Analysis"),
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
                # Unified Topology Analysis (Full + Flows side-by-side)
                flows_file = (RESULTS_DIR / ".." / "simulation" / "mix" / "flows" / "flow_two_senders_heavy.txt").resolve()
                
                cmd = [sys.executable, str(script_path), 
                       str(topo_file),
                       "--out", str(PLOTS_DIR / "topology_analysis.png")]
                
                if flows_file.exists():
                    cmd.extend(["--flows", str(flows_file)])
                    print(f"Generating unified topology analysis (Full + Flows)...")
                else:
                    print(f"Generating topology analysis (Full view only)...")

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    if result.stdout:
                        print(result.stdout)
                    print(f"✓ {description} completed successfully")
                    return True
                else:
                    print(f"✗ {description} failed")
                    if result.stderr:
                        print(result.stderr)
                    return False
            else:
                print(f"⚠️  Skipping {description}: Topology file not found")
                return False
        
        elif "switch_throughput" in script_name:
            # This script needs --trace, --topo, and --flows flags
            # Find all trace files (excluding pcap or other types if necessary)
            trace_files = list(DATA_DIR.glob("*.tr"))
            
            if trace_files:
                for trace_file in trace_files:
                    # mix_dynamic_pull.tr -> config_dynamic_pull.txt
                    exp_name = trace_file.stem
                    # Try to deduce config components from experiment name
                    # Fallback to standard locations if dynamic deduction fails
                    
                    topo_file = RESULTS_DIR.parent / "simulation" / "mix" / "topologies" / "topology_two_senders.txt"
                    # Try to find a specific topology? For now default is safe or we can try to find config
                    
                    flows_file = (RESULTS_DIR / ".." / "simulation" / "mix" / "flows" / "flow_two_senders_long.txt").resolve()
                    if not flows_file.exists():
                         flows_file = (RESULTS_DIR / ".." / "simulation" / "mix" / "flows" / "flow_two_senders_heavy.txt").resolve()

                    if trace_file.exists():
                        cmd = [sys.executable, str(script_path), 
                               "--trace", str(trace_file),
                               "--out", str(PLOTS_DIR / f"switch_throughput_{exp_name}.png")]
                        
                        # Infer config file
                        config_name = f"config_{exp_name}.txt"
                        config_file = RESULTS_DIR.parent / "simulation" / "mix" / "configs" / config_name
                        if config_file.exists():
                            cmd.extend(["--config", str(config_file)])
                        
                        if topo_file.exists():
                             cmd.extend(["--topo", str(topo_file)])
                        if flows_file.exists():
                             cmd.extend(["--flows", str(flows_file)])
                        
                        print(f"Command: {' '.join(cmd)}")
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300) # Increased timeout for big traces
                        
                        if result.returncode == 0:
                            print(f"✓ {description} ({trace_file.name}) completed successfully")
                            if result.stdout:
                                print(result.stdout)
                        else:
                            print(f"✗ {description} ({trace_file.name}) failed")
                            if result.stderr:
                                print(f"Error: {result.stderr[:300]}")
                            return False
                return True
            else:
                print(f"⚠️  Skipping {description}: No trace files found")
                return False

        elif "cwnd_rtt_analysis" in script_name:
            # This script generates CWND/RTT analysis dashboard
            # Find all cwnd files
            cwnd_files = list(DATA_DIR.glob("cwnd_*.txt"))
            
            if cwnd_files:
                for cwnd_file in cwnd_files:
                    exp_name = cwnd_file.stem.replace("cwnd_", "")
                    
                    config_name = f"config_{exp_name}.txt"
                    config_file = RESULTS_DIR.parent / "simulation" / "mix" / "configs" / config_name
                    # Default topo
                    topo_file = RESULTS_DIR.parent / "simulation" / "mix" / "topologies" / "topology_two_senders.txt"
                    
                    if not config_file.exists():
                         # Fallback for dynamic pull naming convention if different
                         config_file = RESULTS_DIR.parent / "simulation" / "mix" / "configs" / "config_two_senders_per_node.txt"

                    cmd = [sys.executable, str(script_path), 
                               str(cwnd_file),
                               str(PLOTS_DIR / f"cwnd_rtt_analysis_{exp_name}.png")]
                    
                    if config_file.exists():
                        cmd.append(str(config_file))
                    if topo_file.exists():
                        cmd.append(str(topo_file))
                    
                    print(f"Command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        print(f"✓ {description} ({cwnd_file.name}) completed successfully")
                        if result.stdout:
                            print(result.stdout)
                    else:
                        print(f"✗ {description} ({cwnd_file.name}) failed")
                        if result.stderr:
                            print(f"Error: {result.stderr[:300]}")
                        return False
                return True
            else:
                print(f"⚠️  Skipping {description}: No CWND data file found")
                return False

        elif "queue_metrics" in script_name:
            # This script needs --qlen, optional --pfc, and --out-dir
            # Find all qlen files
            qlen_files = list(DATA_DIR.glob("qlen_*.txt"))
            
            if qlen_files:
                for qlen_file in qlen_files:
                    exp_name = qlen_file.stem.replace("qlen_", "")
                    pfc_file = DATA_DIR / f"pfc_{exp_name}.txt"
                    
                    # Infer config file
                    config_name = f"config_{exp_name}.txt"
                    config_file = RESULTS_DIR.parent / "simulation" / "mix" / "configs" / config_name

                    cmd = [sys.executable, str(script_path), 
                           "--qlen", str(qlen_file),
                           "--out-dir", str(PLOTS_DIR)]
                    
                    if pfc_file.exists():
                        cmd.extend(["--pfc", str(pfc_file)])

                    if config_file.exists():
                        cmd.extend(["--config", str(config_file)])
                        
                    print(f"Command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        print(f"✓ {description} ({qlen_file.name}) completed successfully")
                        if result.stdout:
                            print(result.stdout)
                    else:
                        print(f"✗ {description} ({qlen_file.name}) failed")
                        if result.stderr:
                             print(f"Error: {result.stderr[:300]}")
                             return False
                return True
            else:
                 print(f"⚠️  Skipping {description}: No qlen files found")
                 return False
        
        elif "plot_rx_buffer" in script_name or "rx_buffer" in script_name:
            # This script needs RX buffer trace
            # Find all rxbuf files
            rxbuf_files = list(DATA_DIR.glob("rxbuf_*.txt"))
            
            if rxbuf_files:
                for rxbuf_file in rxbuf_files:
                    # Infer config file
                    # rxbuf_dynamic_pull.txt -> config_dynamic_pull.txt
                    exp_name = rxbuf_file.stem.replace("rxbuf_", "")
                    config_name = f"config_{exp_name}.txt"
                    config_file = RESULTS_DIR.parent / "simulation" / "mix" / "configs" / config_name
                    
                    cmd = [sys.executable, str(script_path), str(rxbuf_file),
                           "--out", str(PLOTS_DIR / f"rx_buffer_{exp_name}.png")]
                    
                    if config_file.exists():
                        cmd.extend(["--config", str(config_file)])
                        
                    print(f"Command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        print(f"✓ {description} ({rxbuf_file.name}) completed successfully")
                        if result.stdout:
                            print(result.stdout)
                    else:
                        print(f"✗ {description} ({rxbuf_file.name}) failed")
                        if result.stderr:
                            print(f"Error: {result.stderr[:300]}")
                        return False
                return True
            else:
                print(f"⚠️  Skipping {description}: No RX buffer file found")
                return False

        elif "plot_fct" in script_name:
             # FCT Plot
             # Find all fct files
             fct_files = list(DATA_DIR.glob("fct_*.txt"))
             if fct_files:
                 for fct_file in fct_files:
                     exp_name = fct_file.stem.replace("fct_", "")
                     cmd = [sys.executable, str(script_path), str(fct_file),
                            "--out", str(PLOTS_DIR / f"fct_{exp_name}.png")]
                     print(f"Command: {' '.join(cmd)}")
                     result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                     if result.returncode == 0:
                         print(f"✓ {description} ({fct_file.name}) completed successfully")
                         if result.stdout:
                             print(result.stdout)
                     else:
                         print(f"✗ {description} ({fct_file.name}) failed")
                         if result.stderr:
                             print(f"Error: {result.stderr[:300]}")
                 return True
             else:
                 print(f"⚠️  Skipping {description}: No FCT file found")
                 return False

        elif "packet_drops" in script_name or "drop" in script_name:
            # This script needs packet drop trace AND pfc trace for unified plot
            # Find all drop files
            drop_files = list(DATA_DIR.glob("drop_*.txt"))
            
            if drop_files:
                for drop_file in drop_files:
                    exp_name = drop_file.stem.replace("drop_", "")
                    pfc_file = DATA_DIR / f"pfc_{exp_name}.txt"
                    
                    cmd = [sys.executable, str(script_path), 
                           "-o", str(PLOTS_DIR / f"reliability_analysis_{exp_name}.png")]
                    
                    cmd.extend(["--drops", str(drop_file)])
                    
                    if pfc_file.exists():
                        cmd.extend(["--pfc", str(pfc_file)])
                        
                    print(f"Command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        print(f"✓ {description} ({drop_file.name}) completed successfully")
                        if result.stdout:
                            print(result.stdout)
                    else:
                        print(f"✗ {description} ({drop_file.name}) failed")
                        if result.stderr:
                            print(f"Error: {result.stderr[:300]}")
                return True
            else:
                print(f"✓ {description}: No drop files found (Clean Run)")
                return True 

        elif "dashboard" in script_name:
             # Comprehensive Dashboard
             # Needs FCT and Qlen files
             fct_files = list(DATA_DIR.glob("fct_*.txt"))
             
             if fct_files:
                 for fct_file in fct_files:
                     exp_name = fct_file.stem.replace("fct_", "")
                     qlen_file = DATA_DIR / f"qlen_{exp_name}.txt"
                     
                     cmd = [sys.executable, str(script_path), 
                            "--out", str(PLOTS_DIR / f"dashboard_{exp_name}.png"),
                            "--fct", str(fct_file)]
                     
                     if qlen_file.exists():
                         cmd.extend(["--qlen", str(qlen_file)])
                         
                     print(f"Command: {' '.join(cmd)}")
                     result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                     
                     if result.returncode == 0:
                         print(f"✓ {description} ({exp_name}) completed successfully")
                         if result.stdout:
                             print(result.stdout)
                     else:
                         print(f"✗ {description} ({exp_name}) failed")
                         if result.stderr:
                             print(f"Error: {result.stderr[:300]}")
                             return False
                 return True
             else:
                 print(f"⚠️  Skipping {description}: No FCT files found for dashboard")
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
