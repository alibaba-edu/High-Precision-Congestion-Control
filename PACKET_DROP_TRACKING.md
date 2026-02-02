# Packet Drop Tracking and Visualization

## Overview

The simulator now tracks and visualizes packet drops at the NIC RX buffer level. When the RX buffer overflows (exceeds `RX_BUFFER_SIZE` or `RX_BUFFER_PER_QUEUE` limits), packets are dropped using tail-drop behavior.

## What Gets Tracked

**Drop Events**: Each packet drop is logged with:
- **Timestamp** (nanoseconds)
- **Node ID** (which node experienced the drop)
- **Interface Index** (which NIC interface)
- **Queue Index** (which priority queue, 0-7)
- **Packet Size** (bytes dropped)

## Output Files

### `drop.txt`
Plain text file with one drop event per line:
```
<time_ns> <node_id> <if_index> <queue_index> <packet_size>
```

Example:
```
1500000000 2 1 0 1040
1500080000 2 1 0 1040
1500160000 2 1 1 1040
```

## Visualization

### Running the Plot Script

```bash
# From results/ directory
python3 scripts/plot_packet_drops.py data/drop_two_senders_heavy.txt

# Or specify output location
python3 scripts/plot_packet_drops.py data/drop_two_senders_heavy.txt -o plots/drops.png
```

### What the Plot Shows

The visualization includes **4 subplots**:

1. **Top-Left: Histogram of Total Packet Drops per Node**
   - Bar chart showing how many packets each node dropped
   - Annotated with exact counts

2. **Top-Right: Histogram of Bytes Dropped per Node**
   - Shows total bytes (in KB) dropped at each node
   - Helps identify which nodes are experiencing buffer pressure

3. **Bottom-Left: Cumulative Drops Timeline**
   - Line graph showing how drops accumulate over time
   - One line per node that experienced drops
   - Useful for identifying when congestion occurs

4. **Bottom-Right: Drops by Queue Index (Stacked Bar)**
   - Shows which priority queues are experiencing drops
   - Stacked bars for each node
   - Helps diagnose priority-level issues

### Zero Drops Case

If no packets are dropped, the script generates a simple plot with:
```
No Packet Drops Detected ✓
```

## Integration with Plotting Pipeline

The packet drop plot is automatically included when running:

```bash
cd results
python3 run_all_plots.py
```

This will:
1. Look for `data/drop_two_senders_heavy.txt`
2. Generate `plots/packet_drops.png` if drop data exists
3. Skip gracefully if no drop file is found

## Understanding Drop Behavior

### When Drops Occur

Packets are dropped when:

1. **Total RX buffer full**: `total_bytes + packet_size > RX_BUFFER_SIZE`
2. **Per-queue limit exceeded**: `queue_bytes[idx] + packet_size > RX_BUFFER_PER_QUEUE`

See [rdma-ingress-queue.cc](simulation/src/point-to-point/model/rdma-ingress-queue.cc) lines 49-51.

### What Happens After Drop

1. Packet is **silently dropped** (tail-drop)
2. **No ACK generated** (receiver never sees the packet)
3. Sender detects via:
   - **Missing ACK** (timeout or gap detection)
   - **NACK** if receiver gets out-of-order packet
4. Sender **retransmits** the lost packet

### Configuration Parameters

Control RX buffer size in config files:

```bash
# Global settings
RX_BUFFER_SIZE 8388608          # Total buffer: 8 MB
RX_BUFFER_PER_QUEUE 2179        # Per-queue limit
RX_PULL_MODE 1                  # 0=immediate, 1=fixed-rate
RX_PULL_RATE 1.0                # Fraction of line rate

# Per-node overrides
RX_BUFFER_SIZE_NODE 2 4194304   # Node 2: 4 MB buffer
RX_PULL_RATE_NODE 2 0.1         # Node 2: Pull at 10% rate
```

## Example Use Cases

### 1. Diagnosing RX Buffer Overflow

If you see drops at a specific node:
```
Node 2: 15,234 packets dropped (15.6 MB)
```

**Check**:
- Is `RX_PULL_RATE` too low?
- Is buffer size adequate for traffic?
- Are multiple flows overwhelming receiver?

### 2. Identifying Bottleneck Queues

If drops are concentrated in queue 0:
```
Queue 0: 90% of drops
Queue 1: 10% of drops
```

**Indicates**: High-priority traffic overwhelming queue 0

### 3. Temporal Analysis

If drops occur in bursts at specific times:
```
t=0-1s:    No drops
t=1-2s:    5000 drops (burst!)
t=2-3s:    Few drops
```

**Indicates**: Traffic pattern has incast or synchronized bursts

## Code Implementation

### C++ Trace Callback

File: `simulation/scratch/third.cc`

```cpp
void trace_drop(FILE* fout, Ptr<QbbNetDevice> dev, Ptr<const Packet> p, uint32_t qIndex){
    fprintf(fout, "%lu %u %u %u %u\n", 
        Simulator::Now().GetTimeStep(), 
        dev->GetNode()->GetId(), 
        dev->GetIfIndex(), 
        qIndex, 
        p->GetSize());
    fflush(fout);
}
```

Connected to device:
```cpp
dev->TraceConnectWithoutContext("Drop", 
    MakeBoundCallback(&trace_drop, drop_output, dev));
```

### Python Plotting Script

File: `results/scripts/plot_packet_drops.py`

Key features:
- Handles empty files (no drops)
- Aggregates by node, queue, and time
- Generates comprehensive 4-subplot visualization
- Annotated with statistics

## Related Documentation

- [HOW_PULLING_RATE_AFFECTS_SENDING.md](HOW_PULLING_RATE_AFFECTS_SENDING.md) - Explains how RX pulling creates backpressure
- [RESULTS_ORGANIZATION.md](RESULTS_ORGANIZATION.md) - How results are organized
- [VISUALIZATION_GUIDE.md](VISUALIZATION_GUIDE.md) - Other available plots

## Troubleshooting

**Q: No drop.txt file generated?**
- Check that simulation compiled with updated third.cc
- Verify `drop_output` file is opened (line ~900 in third.cc)
- Ensure trace connection is established for devices

**Q: Plot shows zero drops but I expect some?**
- Check if `RX_BUFFER_SIZE` is very large
- Verify `RX_PULL_RATE` allows buffer to drain
- Confirm traffic is actually reaching receivers

**Q: Too many drops - how to reduce?**
- Increase `RX_BUFFER_SIZE`
- Increase `RX_PULL_RATE` (closer to 1.0)
- Use `RX_PULL_MODE 0` (immediate) for testing
- Reduce sending rate or number of flows
