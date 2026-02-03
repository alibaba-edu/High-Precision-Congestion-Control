#!/usr/bin/env python3
"""
Visualization of network topology from simulation config
Shows node connections and link speeds
Optionally filters to show only nodes involved in specified flows
"""

import matplotlib.pyplot as plt
import networkx as nx
import sys
import os
from matplotlib.patches import FancyBboxPatch
import argparse

def parse_topology(topo_file):
    """Parse topology file (supports both standard and fat-tree formats)."""
    nodes = {}
    links = []
    num_hosts = 0
    num_switches = 0
    switch_ids = set()

    with open(topo_file, 'r') as f:
        lines = f.readlines()

        # First line: node counts
        first = lines[0].strip().split()
        total_nodes = int(first[0])
        num_switches = int(first[1]) if len(first) > 1 else 0
        num_hosts = total_nodes - num_switches

        # Second line: either a switch-id list (fat.txt) or a type indicator (topology.txt)
        if len(lines) > 1:
            second_parts = lines[1].strip().split()
            if len(second_parts) > 1 and len(second_parts) == num_switches:
                try:
                    switch_ids = set(int(x) for x in second_parts)
                except ValueError:
                    switch_ids = set()

        # Create node labels
        if switch_ids:
            for i in range(total_nodes):
                if i in switch_ids:
                    nodes[i] = f'S{i}'
                else:
                    nodes[i] = f'H{i}'
            num_hosts = total_nodes - len(switch_ids)
            num_switches = len(switch_ids)
        else:
            for i in range(total_nodes):
                if i < num_hosts:
                    nodes[i] = f'H{i}'  # Host
                else:
                    nodes[i] = f'S{i-num_hosts}'  # Switch

        # Parse links
        for line_idx in range(2, len(lines)):
            line = lines[line_idx].strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    src = int(parts[0])
                    dst = int(parts[1])
                    speed = parts[2]
                    delay = parts[3] if len(parts) > 3 else "0us"
                    links.append((src, dst, speed, delay))
                except (ValueError, IndexError):
                    continue

    return nodes, links, num_hosts, num_switches

def _extract_topology_from_config(config_file):
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if parts[0] == 'TOPOLOGY_FILE' and len(parts) >= 2:
                        topo_path = parts[1]
                        if not os.path.isabs(topo_path):
                            base_dir = os.path.dirname(os.path.abspath(config_file))
                            if topo_path.startswith('mix/') and os.path.basename(base_dir) == 'mix':
                                topo_path = os.path.normpath(os.path.join(os.path.dirname(base_dir), topo_path))
                            else:
                                topo_path = os.path.normpath(os.path.join(base_dir, topo_path))
                        return topo_path
    except OSError:
        return None
    return None

def parse_flows(flows_file):
    """Parse flows file and return set of involved node IDs.
    
    Format:
    <num_flows>
    <src0> <dst0> <port0> <port0_dst> <size0> <start_time0>
    <src1> <dst1> <port1> <port1_dst> <size1> <start_time1>
    ...
    """
    active_nodes = set()
    try:
        with open(flows_file, 'r') as f:
            lines = f.readlines()
            if len(lines) > 0:
                try:
                    num_flows = int(lines[0].strip())
                except ValueError:
                    return active_nodes
                
                for i in range(1, min(1 + num_flows, len(lines))):
                    parts = lines[i].strip().split()
                    if len(parts) >= 2:
                        try:
                            src = int(parts[0])
                            dst = int(parts[1])
                            active_nodes.add(src)
                            active_nodes.add(dst)
                        except ValueError:
                            continue
    except (OSError, IOError):
        pass
    
    return active_nodes


def parse_flows_details(flows_file):
    """Return list of flow dicts with keys: src, dst, dstport, size, start_time"""
    flows = []
    try:
        with open(flows_file, 'r') as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
            if not lines:
                return flows
            try:
                num_flows = int(lines[0])
            except ValueError:
                num_flows = len(lines)
            for i in range(1, min(1 + num_flows, len(lines))):
                parts = lines[i].split()
                if len(parts) >= 6:
                    try:
                        src = int(parts[0])
                        dst = int(parts[1])
                        # Expected format: src dst <proto> dst_port size start_time
                        dstport = int(parts[3]) if parts[3].isdigit() else None
                        size = int(parts[4]) if parts[4].isdigit() else None
                        start_time = int(parts[5]) if parts[5].isdigit() else None
                    except (ValueError, IndexError):
                        continue
                    flows.append({
                        'src': src,
                        'dst': dst,
                        'dstport': dstport,
                        'size': size,
                        'start_time': start_time,
                    })
    except (OSError, IOError):
        pass
    return flows


def plot_topology(topo_file, output_file='topology.png', flows_file=None):
    """Create network topology visualization
    
    Args:
        topo_file: Path to topology file
        output_file: Output PNG file path
        flows_file: Optional flows file - if provided, only show nodes involved in flows
    """
    nodes, links, num_hosts, num_switches = parse_topology(topo_file)
    
    # Parse flows if provided to filter nodes
    active_nodes_from_flows = None
    if flows_file and os.path.exists(flows_file):
        active_nodes_from_flows = parse_flows(flows_file)
        print(f"Flows file provided: showing only active nodes {sorted(active_nodes_from_flows)}")
    
    # Get all node IDs that actually appear in links
    all_node_ids = set(nodes.keys())
    for src, dst, _, _ in links:
        all_node_ids.add(src)
        all_node_ids.add(dst)
    
    # Update node count if needed
    max_node = max(all_node_ids) if all_node_ids else 0
    for i in range(max_node + 1):
        if i not in nodes:
            nodes[i] = f'Node{i}'
    
    # Filter links and nodes if flows file provided
    if active_nodes_from_flows:
        # Include any link that touches an active flow node, and include both
        # endpoints of those links so switch nodes are shown as well.
        filtered_links = []
        nodes_to_show = set(active_nodes_from_flows)
        for src, dst, speed, delay in links:
            if (src in active_nodes_from_flows) or (dst in active_nodes_from_flows):
                filtered_links.append((src, dst, speed, delay))
                nodes_to_show.add(src)
                nodes_to_show.add(dst)
        links = filtered_links
    else:
        nodes_to_show = all_node_ids
    
    # Create graph
    G = nx.DiGraph()
    G.add_nodes_from(nodes_to_show)
    
    # Add edges
    speeds = {}
    for src, dst, speed, delay in links:
        if src in nodes_to_show and dst in nodes_to_show:
            G.add_edge(src, dst)
            speeds[(src, dst)] = speed
    
    # Layout
    if len(G.nodes()) > 100:
        # Circular layout for dense topologies
        pos = nx.circular_layout(G)
    elif len(G.nodes()) <= 3:
        # Simple layout for very small graphs
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    else:
        # Use a spring layout
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
    
    # Create figure with two subplots side-by-side
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
    fig.suptitle('Network Topology Analysis', fontsize=16, fontweight='bold')
    
    # --- Helper to draw graph on a specific axis ---
    def _draw_subgraph(ax, nodes_subset, title):
        sub_G = nx.DiGraph(G.subgraph(nodes_subset))
        
        # Recalculate layout for subset to look nice
        if len(sub_G.nodes()) > 100:
            pos_sub = nx.circular_layout(sub_G)
        else:
            pos_sub = nx.spring_layout(sub_G, k=2, iterations=50, seed=42)
            
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # Edges
        edge_colors = ['gray'] * len(sub_G.edges())
        nx.draw_networkx_edges(sub_G, pos_sub, ax=ax, edge_color=edge_colors,
                              width=1.5, alpha=0.7, arrows=True, arrowsize=15)
        
        # Edge Labels (Speed + Delay)
        edge_labels = {}
        for u, v in sub_G.edges():
            if (u, v) in link_info:
                spd, dly = link_info[(u, v)]
                edge_labels[(u, v)] = f"{spd}\n{dly}"
        
        nx.draw_networkx_edge_labels(sub_G, pos_sub, edge_labels=edge_labels, ax=ax, font_size=8)
        
        # Nodes
        msg_colors = []
        for n in sub_G.nodes():
            if n < num_hosts:
                if active_nodes_from_flows is not None:
                    msg_colors.append('dodgerblue' if n in active_nodes_from_flows else 'lightblue')
                else:
                    msg_colors.append('lightblue')
            else:
                if active_nodes_from_flows is not None:
                    msg_colors.append('crimson' if n in active_nodes_from_flows else 'lightcoral')
                else:
                    msg_colors.append('lightcoral')
        
        nx.draw_networkx_nodes(sub_G, pos_sub, ax=ax, node_color=msg_colors,
                              node_size=600, edgecolors='black', linewidths=1.5)
        
        # Labels
        sub_labels = {i: nodes[i] for i in sub_G.nodes()}
        nx.draw_networkx_labels(sub_G, pos_sub, sub_labels, ax=ax, font_size=10, font_weight='bold')
        ax.axis('off')

    # Store link info for lookup
    link_info = {}
    for src, dst, speed, delay in links:
        link_info[(src, dst)] = (speed, delay)

    # 1. Full Topology
    _draw_subgraph(ax1, all_node_ids, "Full Network Topology")
    
    # 2. Active Flows Topology (or Stats if no flows provided)
    if active_nodes_from_flows:
        # User wants "Topology Flows". Let's show active endpoints and the switches they touch.
        active_subset = set(active_nodes_from_flows)
        relevant_switches = set()
        for s, d, _, _ in links:
            if s in active_subset or d in active_subset:
                 if s >= num_hosts: relevant_switches.add(s)
                 if d >= num_hosts: relevant_switches.add(d)
        
        _draw_subgraph(ax2, active_subset | relevant_switches, "Active Flows Context")
    else:
        ax2.text(0.5, 0.5, "No Flow Data Provided\n(Use --flows <file>)", 
                ha='center', va='center', fontsize=14)
        ax2.axis('off')

    # Add Legend/Stats Box
    stats_text = f"NODES:\n  • H<n>: Host\n  • S<n>: Switch\n\nLINKS:\n"
    # Summarize unique link types
    link_types = set()
    for _, _, s, d in links:
        link_types.add(f"{s}, {d}")
    for lt in sorted(link_types):
        stats_text += f"  • {lt}\n"
        
    if flows_file and os.path.exists(flows_file):
        flow_details = parse_flows_details(flows_file)
        if flow_details:
            stats_text += f"\nACTIVE FLOWS ({len(flow_details)}):\n"
            for i, f in enumerate(flow_details):
                 # Format: Flow 0: 0->2 (Size: 10000B)
                 size_str = f"{f['size']}B" if f['size'] else "N/A"
                 stats_text += f"  {i+1}. {f['src']} -> {f['dst']} (Size: {size_str})\n"
        
    # Place text box in bottom center or similar
    plt.figtext(0.5, 0.02, stats_text, ha="center", fontsize=9, 
                bbox={"facecolor":"white", "alpha":0.9, "pad":5}, fontfamily='monospace')

    plt.tight_layout(rect=[0, 0.15, 1, 0.95]) # Adjust layout more to make room for larger legend
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"✅ Combined topology visualization saved to: {output_file}")
    plt.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Visualize network topology')
    parser.add_argument('topo_file', nargs='?', default='../data/topology.txt',
                        help='Path to topology file')
    parser.add_argument('--flows', help='Path to flows file (shows only active flow nodes)')
    parser.add_argument('--out', help='Output PNG file path')
    
    args = parser.parse_args()
    
    topo_file = args.topo_file
    if topo_file.endswith('.txt') and 'config' in topo_file:
        topo_file = _extract_topology_from_config(topo_file) or topo_file
    
    output = args.out or topo_file.replace('.txt', '_analysis.png')
    
    # Ensure flows file is absolute or correct relative path if needed
    flows_file = args.flows
    plot_topology(topo_file, output, flows_file=flows_file)
