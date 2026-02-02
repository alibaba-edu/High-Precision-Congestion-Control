# How RX Pulling Rate Controls Sender's Transmission Rate

## The Complete Feedback Loop

You've observed that the algorithm adapts to the end-host pulling rate. Here's exactly **how** this happens through an elegant window-based flow control mechanism:

---

## The Mechanism (Step by Step)

### 1. **Sender is Window-Bound**

**File**: [qbb-net-device.cc#L106](simulation/src/point-to-point/model/qbb-net-device.cc#L106)

```cpp
if (!paused[qp->m_pg] && qp->GetBytesLeft() > 0 && !qp->IsWinBound()){
    // Can send packet
}
```

The sender can only transmit when **NOT** window-bound. Let's see what this means:

**File**: [rdma-queue-pair.cc#L120-L122](simulation/src/point-to-point/model/rdma-queue-pair.cc#L120-L122)

```cpp
bool RdmaQueuePair::IsWinBound(){
    uint64_t w = GetWin();
    return w != 0 && GetOnTheFly() >= w;
}
```

Where:
- `GetOnTheFly() = snd_nxt - snd_una` (bytes sent but not yet acknowledged)
- `GetWin()` = the window size (either static or scaled by rate)

**Translation**: Sender stops sending when unacknowledged bytes reach the window limit.

---

### 2. **Receiver Pulls Packets at Limited Rate**

**File**: [rdma-hw.cc#L531-L539](simulation/src/point-to-point/model/rdma-hw.cc#L531-L539)

```cpp
uint64_t line_rate = dev->GetDataRate().GetBitRate();
double rate = line_rate * m_rxPullRate;  // e.g., 1 Gbps * 0.1 = 100 Mbps
double seconds = (p->GetSize() * 8.0) / rate;  // Service time per packet

m_rxPullEvents[nic_idx] = Simulator::Schedule(
    Seconds(seconds), 
    &RdmaHw::ProcessRxBuffer, 
    this, 
    nic_idx
);
```

**Example Calculation** (RX_PULL_RATE = 0.1):
- Line rate: 1 Gbps
- Pull rate: 100 Mbps (10% of line rate)
- Packet size: 1000 bytes
- **Service time**: (1000 × 8) / (100 × 10⁶) = **80 μs per packet**

**Key Point**: Packets are pulled from RX buffer one at a time, with 80 μs between pulls.

---

### 3. **ACKs Generated When Packets Are Pulled**

**File**: [rdma-hw.cc#L489-L495](simulation/src/point-to-point/model/rdma-hw.cc#L489-L495)

```cpp
int RdmaHw::ReceiveFromRxBuffer(Ptr<Packet> p){
    CustomHeader ch(...);
    p->PeekHeader(ch);
    p->RemoveHeader(ch);
    return Receive(p, ch);  // Routes to ReceiveUdp
}
```

**File**: [rdma-hw.cc#L335-L377](simulation/src/point-to-point/model/rdma-hw.cc#L335-L377)

```cpp
int RdmaHw::ReceiveUdp(Ptr<Packet> p, CustomHeader &ch){
    // ... process packet ...
    
    int x = ReceiverCheckSeq(ch.udp.seq, rxQp, payload_size);
    if (x == 1 || x == 2){ // Generate ACK or NACK
        qbbHeader seqh;
        seqh.SetSeq(rxQp->ReceiverNextExpectedSeq);  // ACK sequence number
        // ... build ACK packet ...
        m_nic[nic_idx].dev->RdmaEnqueueHighPrioQ(newp);  // Send ACK
        m_nic[nic_idx].dev->TriggerTransmit();
    }
    return 0;
}
```

**Critical Insight**: ACK generation happens **inside** `ReceiveFromRxBuffer`, which is called **after** pulling a packet from the RX buffer.

**Timeline**:
```
t=0 μs:   Packet arrives in RX buffer
t=0 μs:   ProcessRxBuffer scheduled (NotifyRxEnqueue)
t=0 μs:   Packet pulled → ReceiveFromRxBuffer → ReceiveUdp → ACK generated
t=80 μs:  Next packet pulled → ACK generated
t=160 μs: Next packet pulled → ACK generated
...
```

**Result**: ACKs are generated at the **pulling rate** (100 Mbps), not the arrival rate (1 Gbps).

---

### 4. **ACKs Advance the Sender's Window**

**File**: [rdma-hw.cc#L440-L450](simulation/src/point-to-point/model/rdma-hw.cc#L440-L450)

```cpp
int RdmaHw::ReceiveAck(Ptr<Packet> p, CustomHeader &ch){
    uint32_t seq = ch.ack.seq;  // ACK sequence number
    Ptr<RdmaQueuePair> qp = GetQp(...);
    
    if (!m_backto0){
        qp->Acknowledge(seq);  // Advance snd_una
    }
    // ... handle CNP, HPCC updates ...
    
    dev->TriggerTransmit();  // Try to send more packets
    return 0;
}
```

**File**: [rdma-queue-pair.cc#L110-L113](simulation/src/point-to-point/model/rdma-queue-pair.cc#L110-L113)

```cpp
void RdmaQueuePair::Acknowledge(uint64_t ack){
    if (ack > snd_una){
        snd_una = ack;  // Advance unacknowledged sequence number
    }
}
```

**Effect**:
- `snd_una` increases → `GetOnTheFly() = snd_nxt - snd_una` decreases
- Window space freed → `!IsWinBound()` becomes true again
- Sender can transmit more packets

---

## The Complete Flow Control Loop

```
┌─────────────────────────────────────────────────────────────┐
│  SENDER (Node 0 or 1)                                        │
│                                                              │
│  1. Check: !IsWinBound()  (snd_nxt - snd_una < window)     │
│  2. If true: Send packet, snd_nxt += packet_size            │
│  3. Wait for ACK...                                          │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │ Packet @ 1 Gbps
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  NETWORK (Switches)                                          │
│  - Links run at 1 Gbps                                       │
│  - Low utilization (<<100% because receiver can't keep up)   │
│  - INT headers show low qlen, low utilization                │
└──────────────────────┬───────────────────────────────────────┘
                       │ Packet arrives
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  RECEIVER (Node 2)                                           │
│                                                              │
│  1. Packet enqueued in RX buffer (RdmaIngressQueue)         │
│  2. NotifyRxEnqueue → Schedule ProcessRxBuffer              │
│  3. Pull packet at 100 Mbps rate (80 μs per 1KB packet)    │
│     ┌──────────────────────────────────────────┐            │
│     │ ProcessRxBuffer:                         │            │
│     │   - Dequeue one packet                   │            │
│     │   - ReceiveFromRxBuffer → ReceiveUdp    │            │
│     │   - Generate ACK                         │            │
│     │   - Schedule next pull in 80 μs         │            │
│     └──────────────────────────────────────────┘            │
│                                                              │
└──────────────────────┬───────────────────────────────────────┘
                       │ ACK @ high priority
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  SENDER                                                      │
│                                                              │
│  4. Receive ACK: Acknowledge(seq) → snd_una += packet_size  │
│  5. Window freed: GetOnTheFly() decreases                   │
│  6. TriggerTransmit() → Can send next packet                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Why Sender Rate Matches Receiver Pull Rate

### The Math

**Given**:
- Window size: `W` bytes
- Receiver pull rate: `R_pull` bps
- RTT: `T` seconds

**Steady-State Analysis**:

At steady state, the sender's effective rate is limited by how fast ACKs return:

```
Effective_Rate = W / RTT
```

But ACKs are generated at the receiver's pull rate `R_pull`. The ACK rate determines how fast the window "slides":

```
ACK_Rate = R_pull  (one ACK per pulled packet)
Window_Advance_Rate = R_pull
Sender_Effective_Rate = R_pull
```

**Example** (your configuration):
- RX_PULL_RATE = 0.1 → R_pull = 100 Mbps
- Even if HPCC sets rate to 1 Gbps, sender is window-bound
- Actual throughput ≈ 100 Mbps (two flows share this, so ~50 Mbps each)

---

## How HPCC Algorithm Sees This

### What HPCC Measures
**File**: [rdma-hw.cc#L835-L920](simulation/src/point-to-point/model/rdma-hw.cc#L835-L920) (HandleAckHp)

From INT headers in ACKs:
- `txBytes`: Bytes transmitted at each switch port
- `qlen`: Queue length at each switch
- `linkCapacity`: Line rate (1 Gbps)

Calculate utilization:
```cpp
u = (txBytes / time) / linkCapacity
```

### What It Observes
- Network links: **Low utilization** (<<100%) because receiver only pulls at 100 Mbps
- Queue lengths: **Near zero** (no congestion)
- INT telemetry: `max_c < 1` (no oversubscription)

### Algorithm Response
From [rdma-hw.cc#L922-L927](simulation/src/point-to-point/model/rdma-hw.cc#L922-L927):

```cpp
if (max_c >= 1 || qp->hp.m_incStage >= m_miThresh){
    // Network congestion OR MI threshold reached
    // Apply Multiplicative Decrease/Increase
} else {
    // No congestion: Apply Additive Increase
    hp.m_curRate += m_dctcp_rai;
}
```

Since `max_c < 1` always (network underutilized), HPCC keeps increasing rate via AI until it hits `m_rate_bound` (1 Gbps).

**But**: Even though HPCC sets rate to 1 Gbps, the **window mechanism** prevents sender from actually transmitting faster than receiver can ACK (100 Mbps).

---

## Why You See Constant 1 Gbps in Rate Trace

### Rate vs. Throughput

**Important Distinction**:
- **m_rate / hp.m_curRate**: The algorithm's *calculated* sending rate (what HPCC sets)
- **Actual throughput**: Limited by min(m_rate, window/RTT, receiver_pull_rate)

### Your Trace Shows
```
cwnd_two_senders_heavy.txt shows: m_rate = 1 Gbps (constant)
```

This is **correct** from HPCC's perspective:
- Network says "no congestion"
- Algorithm says "increase rate"
- Rate reaches 1 Gbps and stays there

### Actual Behavior
```
Effective throughput ≈ 100 Mbps (limited by receiver pull rate)
Window keeps sender throttled despite high rate setting
```

---

## Verification: Check Window Occupancy

You can verify this by checking:

### 1. Window Usage Trace
Look for packets in flight:
```cpp
GetOnTheFly() = snd_nxt - snd_una
```

**Prediction**: Should stay at or near window limit `W` for most of the time.

### 2. RX Buffer Occupancy
Check `m_traceTotalBytes` in RdmaIngressQueue.

**Prediction**: Should oscillate in sawtooth pattern:
- Packets arrive faster than pulling → buffer grows
- Pulling drains → buffer shrinks
- Repeat

### 3. ACK Timing
Measure time between ACKs at sender.

**Prediction**: ACK inter-arrival ≈ 80 μs (matching pull rate)

---

## Summary: The Elegant Self-Regulating System

### The Beauty of This Design

1. **Network-based congestion control** (HPCC):
   - Monitors switch queue lengths and link utilization
   - Adjusts rate to prevent network congestion
   - Works at network timescale (microseconds)

2. **End-host flow control** (Window mechanism):
   - Prevents receiver buffer overflow
   - Automatically throttles sender to match receiver capacity
   - Works at end-host timescale (packet service time)

3. **Decoupled but complementary**:
   - HPCC sets the target rate based on network conditions
   - Window enforcement ensures sender never exceeds receiver capacity
   - Actual throughput = min(HPCC_rate, window/RTT, receiver_pull_rate)

### In Your Configuration

```
HPCC target rate:     1 Gbps (no network congestion detected)
Window limit:         Effective ~100 Mbps (due to ACK rate)
Receiver pull rate:   100 Mbps (explicit limit)

Actual throughput:    ~100 Mbps (bottleneck: receiver)
```

**Result**: The algorithm correctly adapts to end-host limitations through standard TCP-like window flow control, while HPCC independently manages network-layer congestion!

---

## References

**Key Code Sections**:
1. Window bound check: [qbb-net-device.cc#L106](simulation/src/point-to-point/model/qbb-net-device.cc#L106)
2. Pull rate limiting: [rdma-hw.cc#L531-L539](simulation/src/point-to-point/model/rdma-hw.cc#L531-L539)
3. ACK generation: [rdma-hw.cc#L350-L377](simulation/src/point-to-point/model/rdma-hw.cc#L350-L377)
4. Window advancement: [rdma-hw.cc#L440-L450](simulation/src/point-to-point/model/rdma-hw.cc#L440-L450)
5. IsWinBound: [rdma-queue-pair.cc#L120-L122](simulation/src/point-to-point/model/rdma-queue-pair.cc#L120-L122)
