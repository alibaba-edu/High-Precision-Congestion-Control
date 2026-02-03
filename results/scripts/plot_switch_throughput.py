#!/usr/bin/env python3
"""Plot average switch throughput and utilization over time from binary trace."""
import argparse
import struct
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import ctypes


class _Data(ctypes.LittleEndianStructure):
    _fields_ = [
        ("sport", ctypes.c_uint16),
        ("dport", ctypes.c_uint16),
        ("seq", ctypes.c_uint32),
        ("ts", ctypes.c_uint64),
        ("pg", ctypes.c_uint16),
        ("payload", ctypes.c_uint16),
    ]


class _Cnp(ctypes.LittleEndianStructure):
    _fields_ = [
        ("fid", ctypes.c_uint16),
        ("qIndex", ctypes.c_uint8),
        ("ecnBits", ctypes.c_uint8),
        ("qfb_or_seq", ctypes.c_uint32),
    ]


class _Ack(ctypes.LittleEndianStructure):
    _fields_ = [
        ("sport", ctypes.c_uint16),
        ("dport", ctypes.c_uint16),
        ("flags", ctypes.c_uint16),
        ("pg", ctypes.c_uint16),
        ("seq", ctypes.c_uint32),
        ("ts", ctypes.c_uint64),
    ]


class _Pfc(ctypes.LittleEndianStructure):
    _fields_ = [
        ("time", ctypes.c_uint32),
        ("qlen", ctypes.c_uint32),
        ("qIndex", ctypes.c_uint8),
    ]


class _Qp(ctypes.LittleEndianStructure):
    _fields_ = [
        ("sport", ctypes.c_uint16),
        ("dport", ctypes.c_uint16),
    ]


class _Union(ctypes.Union):
    _fields_ = [
        ("data", _Data),
        ("cnp", _Cnp),
        ("ack", _Ack),
        ("pfc", _Pfc),
        ("qp", _Qp),
    ]


class Trace(ctypes.LittleEndianStructure):
    _fields_ = [
        ("time", ctypes.c_uint64),
        ("node", ctypes.c_uint16),
        ("intf", ctypes.c_uint8),
        ("qidx", ctypes.c_uint8),
        ("qlen", ctypes.c_uint32),
        ("sip", ctypes.c_uint32),
        ("dip", ctypes.c_uint32),
        ("size", ctypes.c_uint16),
        ("l3Prot", ctypes.c_uint8),
        ("event", ctypes.c_uint8),
        ("ecn", ctypes.c_uint8),
        ("nodeType", ctypes.c_uint8),
        ("u", _Union),
    ]


def _read_sim_setting(f):
    raw = f.read(4)
    if len(raw) < 4:
        raise ValueError("Trace file missing SimSetting header")
    (count,) = struct.unpack("<I", raw)
    port_speed = defaultdict(dict)
    for _ in range(count):
        entry = f.read(2 + 1 + 8)
        if len(entry) < 11:
            raise ValueError("Trace file truncated while reading SimSetting")
        node, intf, bps = struct.unpack("<HBQ", entry)
        port_speed[node][intf] = bps
    win_raw = f.read(4)
    if len(win_raw) < 4:
        raise ValueError("Trace file truncated while reading SimSetting.win")
    return port_speed


def _iter_traces(trace_path):
    with trace_path.open("rb") as f:
        port_speed = _read_sim_setting(f)
        record_size = ctypes.sizeof(Trace)
        while True:
            buf = f.read(record_size)
            if len(buf) < record_size:
                break
            yield port_speed, Trace.from_buffer_copy(buf)


def _parse_topology_links(topo_path):
    links = []
    with open(topo_path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 5:
                try:
                    a = int(parts[0])
                    b = int(parts[1])
                except ValueError:
                    continue
                links.append((a, b))
    return links


def _build_port_map(links):
    """Build neighbor map AND interface map from topology links.
    
    Returns:
        port_map: dict mapping node -> list of neighbors
        intf_map: dict mapping (node, neighbor) -> interface_index
    """
    port_map = defaultdict(list)
    intf_map = {}
    intf_counter = defaultdict(lambda: 1)  # ns-3 starts interface numbering at 1
    
    for a, b in links:
        port_map[a].append(b)
        port_map[b].append(a)
        # Assign interface indices in link creation order (1-indexed)
        intf_map[(a, b)] = intf_counter[a]
        intf_counter[a] += 1
        intf_map[(b, a)] = intf_counter[b]
        intf_counter[b] += 1
    
    return port_map, intf_map


def _infer_receiver_from_flows(flow_path):
    with open(flow_path, "r") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                return int(parts[1])
    return None


def _infer_switch_for_receiver(port_map, dst_node):
    if dst_node is None or port_map is None:
        return None
    candidates = []
    for node, neighs in port_map.items():
        if dst_node in neighs:
            candidates.append(node)
    if not candidates:
        return None
    # Prefer nodes with degree > 1 (likely switch)
    for node in candidates:
        if len(port_map.get(node, [])) > 1:
            return node
    return candidates[0]


def _parse_schedules(config_file):
    """Parse config file to extract RX_PULL_RATE_SCHEDULE."""
    schedules = {}
    if not config_file or not Path(config_file).exists():
        return schedules
    
    with open(config_file, 'r') as f:
        for line in f:
            line = line.strip()
            # Handle comments
            if line.startswith('#'):
                continue
            if 'RX_PULL_RATE_SCHEDULE' in line:
                parts = line.split()
                # Format: RX_PULL_RATE_SCHEDULE <node_id> <count> <time1> <rate1> ...
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
                    except ValueError:
                        pass
    return schedules


def plot_switch_throughput(trace_path, out_path, bin_ms, topo_path=None, flow_path=None,
                           sw_node=None, dst_node=None, config_path=None):
    trace_path = Path(trace_path)
    if not trace_path.exists():
        raise FileNotFoundError(trace_path)

    bin_ns = int(bin_ms * 1e6)
    switch_nodes = set()
    port_speed = None
    bytes_per_bin_switch = defaultdict(lambda: defaultdict(int))
    bytes_per_bin_port = defaultdict(int)
    t0 = None

    port_map = None
    intf_map = None
    if topo_path:
        links = _parse_topology_links(topo_path)
        port_map, intf_map = _build_port_map(links)
    if dst_node is None and flow_path:
        dst_node = _infer_receiver_from_flows(flow_path)
    if sw_node is None and dst_node is not None and port_map is not None:
        sw_node = _infer_switch_for_receiver(port_map, dst_node)

    for ps, tr in _iter_traces(trace_path):
        if port_speed is None:
            port_speed = ps
        if tr.nodeType != 1:
            continue
        switch_nodes.add(tr.node)
        if tr.event != 2:  # Dequ
            continue
        # Use absolute time for binning (no t0 shift)
        idx = tr.time // bin_ns
        bytes_per_bin_switch[idx][tr.node] += int(tr.size)

        if sw_node is not None and dst_node is not None and intf_map is not None:
            dst_intf = intf_map.get((sw_node, dst_node))
            if dst_intf is not None and tr.node == sw_node and tr.intf == dst_intf:
                bytes_per_bin_port[idx] += int(tr.size)

    
    # helper for plotting lines
    def _draw_lines(ax, schedules):
        # determine y-limit to place text
        ylim = ax.get_ylim()
        ymax = ylim[1]
        for node_id, schedule in schedules.items():
             for time, rate in schedule:
                 ax.axvline(x=time, color='gray', linestyle=':', alpha=0.8, linewidth=1.5)
                 ax.text(time, ymax * 0.98, f' t={time}s\nRate={rate}', rotation=90, width=100,
                         verticalalignment='top', fontsize=8, color='black', alpha=0.7)

    schedules = {}
    if config_path:
        schedules = _parse_schedules(config_path)

    if sw_node is not None and dst_node is not None and port_map is not None and intf_map is not None:
        if dst_node not in port_map.get(sw_node, []):
            raise RuntimeError("Destination node not connected to the switch in topology")
        dst_port = intf_map.get((sw_node, dst_node))
        if dst_port is None:
            raise RuntimeError(f"Interface mapping not found for switch {sw_node} -> node {dst_node}")
        if port_speed is None or sw_node not in port_speed or dst_port not in port_speed[sw_node]:
            raise RuntimeError("Port speed for selected switch/port not found in trace header")

        if not bytes_per_bin_port:
            raise RuntimeError("No dequeue events found for selected switch port")

        max_bin = max(bytes_per_bin_port.keys())
        times = []
        thr_bps = []
        util = []
        cap = port_speed[sw_node][dst_port]
        for b in range(max_bin + 1):
            bytes_sw = bytes_per_bin_port.get(b, 0)
            bps = (bytes_sw * 8.0) / (bin_ms / 1000.0)
            thr_bps.append(bps)
            util.append((bps / cap) * 100.0 if cap > 0 else 0.0)
            times.append((b * bin_ns) / 1e9)

        plt.figure(figsize=(10, 6))
        ax1 = plt.subplot(2, 1, 1)
        ax1.plot(times, [v / 1e9 for v in thr_bps], linewidth=1.3)
        ax1.set_ylabel("Throughput (Gbps)")
        ax1.set_title(f"Switch {sw_node} -> Node {dst_node} Throughput")
        ax1.grid(True, alpha=0.3)
        if schedules: _draw_lines(ax1, schedules)

        ax2 = plt.subplot(2, 1, 2)
        ax2.plot(times, util, linewidth=1.3, color="orange")
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("Utilization (%)")
        ax2.set_title(f"Switch {sw_node} -> Node {dst_node} Utilization")
        ax2.grid(True, alpha=0.3)
        if schedules: _draw_lines(ax2, schedules)

        plt.tight_layout()
        plt.savefig(out_path, dpi=150)
        plt.close()
        return

    if not bytes_per_bin_switch:
        raise RuntimeError("No switch dequeue events found in trace")

    switches = sorted(switch_nodes)
    if not switches:
        raise RuntimeError("No switch nodes found in trace")

    cap_per_switch = {}
    for sw in switches:
        cap_per_switch[sw] = sum(port_speed.get(sw, {}).values())

    max_bin = max(bytes_per_bin_switch.keys())
    times = []
    avg_throughput_bps = []
    avg_util = []

    for b in range(max_bin + 1):
        per_sw_bytes = bytes_per_bin_switch.get(b, {})
        sum_bps = 0.0
        util_sum = 0.0
        for sw in switches:
            bytes_sw = per_sw_bytes.get(sw, 0)
            bps = (bytes_sw * 8.0) / (bin_ms / 1000.0)
            sum_bps += bps
            cap = cap_per_switch.get(sw, 0)
            util_sum += (bps / cap) if cap > 0 else 0.0
        avg_bps = sum_bps / len(switches)
        avg_throughput_bps.append(avg_bps)
        avg_util.append((util_sum / len(switches)) * 100.0)
        times.append((b * bin_ns) / 1e9)

    plt.figure(figsize=(10, 6))
    ax1 = plt.subplot(2, 1, 1)
    ax1.plot(times, [v / 1e9 for v in avg_throughput_bps], linewidth=1.3)
    ax1.set_ylabel("Avg throughput (Gbps)")
    ax1.set_title("Average Switch Throughput Over Time")
    ax1.grid(True, alpha=0.3)
    if schedules: _draw_lines(ax1, schedules)

    ax2 = plt.subplot(2, 1, 2)
    ax2.plot(times, avg_util, linewidth=1.3, color="orange")
    ax2.set_xlabel("Time (s)")
    ax2.set_ylabel("Avg utilization (%)")
    ax2.set_title("Average Switch Utilization Over Time")
    ax2.grid(True, alpha=0.3)
    if schedules: _draw_lines(ax2, schedules)

    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser(description="Plot average switch throughput/utilization over time")
    parser.add_argument("--trace", default="results/data/mix_two_senders_heavy.tr", help="Path to binary trace file")
    parser.add_argument("--topo", default="simulation/mix/topologies/topology_two_senders.txt", help="Path to topology file")
    parser.add_argument("--flows", default="simulation/mix/flows/flow_two_senders_heavy.txt", help="Path to flow file")
    parser.add_argument("--sw-node", type=int, help="Switch node id to focus on")
    parser.add_argument("--dst-node", type=int, help="Receiver node id (port target)")
    parser.add_argument("--bin-ms", type=float, default=1.0, help="Time bin size in ms")
    parser.add_argument("--out", default="results/plots/avg_switch_throughput_util.png", help="Output plot path")
    parser.add_argument("--config", default=None, help="Path to config file (for schedule)")
    args = parser.parse_args()

    plot_switch_throughput(
        args.trace,
        args.out,
        args.bin_ms,
        topo_path=args.topo,
        flow_path=args.flows,
        sw_node=args.sw_node,
        dst_node=args.dst_node,
        config_path=args.config
    )


if __name__ == "__main__":
    main()
