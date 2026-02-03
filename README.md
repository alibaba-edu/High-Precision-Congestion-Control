# HPCC simulation
[Project page of HPCC](https://hpcc-group.github.io/) includes latest news of HPCC and extensive evaluation results using this simulator.

This is the simulator for [HPCC: High Precision Congestion Control (SIGCOMM' 2019)](https://rmiao.github.io/publications/hpcc-li.pdf). It also includes the implementation of DCQCN, TIMELY, DCTCP, PFC, ECN and Broadcom shared buffer switch.

We have update this simulator to support HPCC-PINT, which reduces the INT header overhead to 1 to 2 byte. This improves the long flow completion time. See [PINT: Probabilistic In-band Network Telemetry (SIGCOMM' 2020)](https://liyuliang001.github.io/publications/pint.pdf).

## HPCC-Plus Extensions

This is a fork of the original HPCC Alibaba repository that explores improvements to the HPCC congestion control model by addressing end-host congestion. This repository includes implementations of:

1. **End-host Congestion Model** - A model that accounts for congestion at the receiver end-host, complementing the fabric-centric approach of original HPCC.

2. **HPCC_ecwnd** - HPCC variant where end-hosts advertise explicit congestion window (`ecwnd`) based on local receiver congestion. The effective window is `min(ecwnd, fcwnd)` where:
   - `ecwnd` = end-host congestion window (receiver-side)
   - `fcwnd` = fabric congestion window (regular HPCC window based on fabric telemetry)

3. **HPCC_Plus** - Treats end-host congestion as a virtual switch with modifications and applies regular HPCC congestion control principles, providing a unified approach to fabric and end-host congestion.

These extensions aim to improve performance in scenarios where end-host (receiver) congestion is a bottleneck, potentially achieving better flow completion times and overall network utilization.

4. **Dynamic Pulling Rate** - Allows the receiver's pulling rate to be dynamically scheduled during the simulation. This is useful for simulating varying receiver processing capabilities over time.
   - Configured via `RX_PULL_RATE_SCHEDULE` in the simulation configuration file.


## Installation & Setup

### Prerequisites
- Docker (recommended for consistent environment)
- Or manually: Ubuntu 20.04+ with build tools, Python 2, Qt5, and ns-3 dependencies

### Option 1: Using Docker (Recommended)

Choose one of the following (they are alternatives):

- **Use Docker Compose:**
   ```bash
   docker compose build
   docker compose run --rm hpcc
   ```
   To stop a running container started with `docker compose up`:
   ```bash
   docker compose down
   ```

- **Build the Docker container:**
   ```bash
   docker build -t hpcc-simulator:latest .
   ```

- **Run the container with X11 display forwarding (for GUI tools like NetAnim):**
   ```bash
   docker run -it \
     -e DISPLAY=$DISPLAY \
     -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
     -v $(pwd):/workspace \
     hpcc-simulator:latest
   ```

- **Or use VS Code Dev Containers:**
   - Install the "Dev Containers" extension in VS Code
   - Open the workspace folder in VS Code
   - Click the Remote indicator in the bottom left and select "Reopen in Container"

### Option 2: Manual Installation

**Required packages:**
```bash
sudo apt-get update && sudo apt-get install -y \
    python2 \
    python2-dev \
    build-essential \
    gcc \
    g++ \
    gdb \
    gnuplot \
    git \
    tcpdump \
    sqlite3 \
    libsqlite3-dev \
    libxml2 \
    libxml2-dev \
    qtbase5-dev \
    qt5-qmake \
    qtbase5-dev-tools
```

**Install Python dependencies:**
```bash
pip install pybindgen
```

**Build NetAnim (optional, for visualization):**
```bash
hg clone https://code.nsnam.org/netanim/ /opt/netanim
cd /opt/netanim
hg update -r netanim-3.108
qmake NetAnim.pro
make -j$(nproc)
```

## Project Structure

- **`simulation/`** - NS-3 simulation code for congestion control algorithms. See [simulation/README.md](simulation/README.md)
- **`traffic_gen/`** - Traffic generator for workload creation. See [traffic_gen/README.md](traffic_gen/README.md)
- **`analysis/`** - Analysis scripts for packet-level events and FCT analysis. See [analysis/README.md](analysis/README.md)
- **`netanim/`** - NetAnim visualization tool for packet animation playback
- **`pybindgen/`** - Python bindings generator (installed via pip, not committed)
- **`results/`** - Output directory for simulation results, logs, and plots

## Running the Simulation

This section provides a step-by-step guide to build, run, and analyze the HPCC simulator.

### Step 1: Start Docker Container

First, ensure the container is running:

```bash
docker compose up -d hpcc
```

Then enter the container shell:

```bash
docker compose exec hpcc bash
```

**Note:** The container provides a hybrid environment:
*   **Python 2.7**: Used for the NS-3 simulation (`./waf`, `run.py`).
*   **Python 3**: Used for all plotting and analysis scripts (`results/run_all_plots.py`).

### Step 2: Build the Simulation

Navigate to the simulation directory and use the helper script:

```bash
cd /workspace/simulation
./build.sh
```

This script automatically sets up the environment and runs `./waf build`.

### Step 3: Run the Simulation

Run the simulator with a specific configuration file using the helper script:

```bash
# General usage
./run.sh <config_file_path>

# Example: Run the 'two_senders_heavy' scenario
./run.sh mix/configs/config_two_senders_per_node.txt
```

To run and **clear previous results** (optional):
```bash
./run.sh mix/configs/config_two_senders_per_node.txt clean
```

### Step 4: Generate Analysis Plots

Generate all visualization plots using the master plotting script:

```bash
cd /workspace
python3 results/run_all_plots.py
```

This will run a suite of analysis scripts and save the output to `/workspace/results/plots/`.
**Generated Plots include:**
*   `cwnd_rtt_analysis.png`: Congestion Window & RTT Dashboard
*   `cwnd_two_senders_heavy_rtt.png`: RTT over Time (timeline)
*   `switch_throughput.png`: Switch metrics
*   `rxbuf_two_senders_heavy.png`: RX Buffer Occupancy
*   `packet_drops.png`: Packet drop tracking
*   `topology_full.png` / `topology_flows.png`: Network visualization

### Quick Reference: Common Commands

```bash
# 1. Enter container
docker compose exec hpcc bash

# 2. Build (in /workspace/simulation)
cd /workspace/simulation && ./build.sh

# 3. Run Experiment
./run.sh mix/configs/config_two_senders_per_node.txt

# 4. Generate Plots (in /workspace)
cd /workspace && python3 results/run_all_plots.py

# 5. View Results
ls -lh /workspace/results/plots/
```

**Build script details (`./build.sh`):**
- Sets up library paths automatically
- Runs `./waf build` with proper environment
- Checks for errors before completing
- Quick status messages

**Run script details (`./run.sh`):**
- Validates config file exists
- Checks executable is built
- Sets library paths automatically
- Optional `clean` flag to remove old results
- Provides next-steps instructions

## Quick Start

1. **Navigate to simulation directory:**
   ```bash
   cd simulation/
   ```

2. **Review configuration:**
   - See [simulation/README.md](simulation/README.md) for available parameters and scenarios

3. **Run a simulation:**
   ```bash
   # Follow instructions in simulation/README.md
   ```

4. **Analyze results:**
   ```bash
   cd ../analysis/
   # Follow instructions in analysis/README.md
   ```

5. **Visualize with NetAnim:**
   ```bash
   NetAnim results/data/simulation.xml
   ```

## Key Features

- High precision congestion control algorithms (HPCC, DCQCN, TIMELY, DCTCP)
- Programmable packet-level simulation with ns-3
- Support for DCN topologies and workloads
- Comprehensive analysis tools for FCT and packet-level events
- PINT support for reduced INT header overhead

We provide a few analysis scripts under `analysis/` to view the packet-level events, and analyzing the fct in the same way as [HPCC](https://liyuliang001.github.io/publications/hpcc.pdf) Figure 11.
Refer to the README.md under it for more details.

## Questions
For technical questions, please create an issue in this repo, so other people can benefit from your questions. 
You may also check the issue list first to see if people have already asked the questions you have :)

For other questions, please contact Rui Miao (miao.rui@alibaba-inc.com).
