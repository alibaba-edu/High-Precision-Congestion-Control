# TODO: High-Precision Congestion Control Plus

## Immediate Tasks

### 1. Test the full pulling rate of senders
- Verify that senders (nodes 0 and 1) with RX_PULL_MODE 0 (immediate) have zero RX buffer occupancy
- Run simulation with current config and check rxbuf output
- Confirm pull rate setting is properly applied: `RX_PULL_MODE_NODE 0 0` and `RX_PULL_MODE_NODE 1 0`
- Compare RX buffer traces before and after immediate mode fix
- Expected outcome: Senders should show 0 bytes occupancy in rxbuf trace

### 2. Understand NIC Rx Buffer Occupancy oscillation at receiver
- **Issue**: Receiver (node 2) RX buffer occupancy oscillates around a certain value instead of increasing monotonically
- **Root cause investigation needed**:
  - Check if oscillation is due to fixed-rate pulling (RX_PULL_MODE 1, RX_PULL_RATE 0.88)
  - Analyze pull interval: `seconds = packet_size * 8 / (line_rate * rx_pull_rate)`
  - For 0.88 pull rate on 1Gbps: pull interval ≈ 9μs per 1KB packet
  - Determine if packet arrival rate > pull rate causing buildup then drain cycle
  - Check queueing theory: if arrival > service rate, queue grows; if arrival < service rate, queue drains
- **Analysis steps**:
  - Plot RX buffer occupancy vs time (high resolution)
  - Calculate avg arrival rate vs avg pull rate
  - Check if burstiness in packet arrivals causes oscillation
  - Consider per-queue vs total buffer occupancy
- **Solution options**:
  - Increase RX_PULL_RATE (e.g., 0.95 or 1.0)
  - Switch to immediate mode (RX_PULL_MODE 0) for receiver
  - Investigate if oscillation is actually correct behavior (queue dynamics)

## Feature Implementation Tasks

### 3. Implement HPCC_ecwnd (End-host Congestion Window)
- **Description**: Advertise end-host congestion window (ecwnd) in ACK packets; sender uses `min(ecwnd, fcwnd)`
- **Motivation**: Allow receiver-side congestion visibility (RX buffer backpressure) to affect sender window
- **Implementation steps**:
  - Add ecwnd field to ACK packet header
  - Calculate ecwnd based on receiver RX buffer availability: `ecwnd = (max_buffer - current_occupancy) / base_rtt`
  - Modify sender to track received ecwnd value
  - Modify window calculation: `W = min(fcwnd, ecwnd)` instead of just `W = fcwnd`
  - Update CWND trace to show both fcwnd and ecwnd
  - Test with RX_PULL_RATE < 1.0 to create receiver-side bottleneck
- **Files to modify**:
  - `rdma-header.h`: Add ecwnd field to ACK header
  - `rdma-hw.cc`: Calculate and embed ecwnd in ACK generation
  - `rdma-qp.h/cc`: Track ecwnd, update window calculation
  - `cwnd trace output`: Add ecwnd column
  - `plot_cwnd_rtt_analysis.py`: Visualize fcwnd vs ecwnd

### 4. Implement HPCC_Plus
- **Description**: Enhanced HPCC protocol with receiver-side congestion signaling
- **Key features**:
  - Combine HPCC feedback (network INT) with ecwnd (receiver RX buffer)
  - Implement aggressive RX buffer draining when ecwnd signals congestion
  - Add receiver-side rate limiting based on buffer occupancy
  - Integrate with per-node pull rate configuration
- **Implementation steps**:
  - Build on HPCC_ecwnd implementation
  - Add RX buffer occupancy-based feedback mechanism
  - Implement adaptive pull rate: adjust RX_PULL_RATE based on buffer level
  - Create HPCC_Plus config file with tuning parameters
  - Compare performance: HPCC vs HPCC_ecwnd vs HPCC_Plus
- **Metrics to track**:
  - Flow completion time (FCT)
  - RX buffer occupancy (mean, max, std dev)
  - Packet loss rate (if any)
  - Link utilization
  - CWND stability

## Testing Plan

- Config file: `config_two_senders.txt` with per-node settings
- Topology: `topology_two_senders.txt` (2 senders → 1 receiver)
- Flow: `flow_two_senders_heavy.txt` (100 MB per flow)
- Measurement output: `fct.txt`, `cwnd.txt`, `rxbuf.txt`
- Visualization: CWND analysis dashboard with fcwnd/ecwnd comparison

## Notes

- HPCC uses fixed base_RTT for window calculation: `W = R × base_RTT`
- Base RTT does not include RX buffer delays (network-only)
- RX buffer delay invisible to HPCC control loop (uses only INT feedback)
- Pull rate = 0.88 means NIC pulls packets at 88% of line rate (12% slower than arrive rate)
- Receiver-side congestion needs explicit signaling mechanism (ecwnd) to affect sender
