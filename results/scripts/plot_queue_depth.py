
import matplotlib.pyplot as plt
import sys
import os
import csv
from collections import defaultdict

import argparse

# Parse arguments
parser = argparse.ArgumentParser(description="Plot queue depth")
parser.add_argument("input", nargs="?", default="simulation/queue_depth.csv", help="Input CSV file")
args = parser.parse_args()

csv_file = args.input

if not os.path.exists(csv_file):
    # Try alternative location relative to script if run from root
    alt_file = os.path.join(os.path.dirname(__file__), '../../simulation/queue_depth.csv')
    if os.path.os.path.exists(alt_file):
        csv_file = alt_file
    else:
        print(f"Error: {csv_file} not found")
        sys.exit(1)

# Usage: Time,QpId,Hop,Qlen
data = defaultdict(lambda: {"t": [], "qlen": []})

try:
    with open(csv_file, 'r') as f:
        reader = csv.reader(f)
        header = next(reader, None) # Skip header if present
        if header and header[0] == 'Time':
             pass # Header consumed
        else:
             # If no header (unlikely given my code), treat matching row as data
             if header:
                 f.seek(0)
                 reader = csv.reader(f)

        for row in reader:
            if not row: continue
            try:
                t = float(row[0])
                qpid = int(row[1])
                hop = int(row[2])
                qlen = int(row[3])
                
                key = (qpid, hop)
                data[key]["t"].append(t)
                data[key]["qlen"].append(qlen)
            except ValueError:
                continue
except Exception as e:
    print(f"Error reading {csv_file}: {e}")
    sys.exit(1)

if not data:
    print("Error: CSV file is empty or invalid")
    sys.exit(1)

plt.figure(figsize=(10,6))

# Sort keys to have consistent legend
sorted_keys = sorted(data.keys())

for key in sorted_keys:
    series = data[key]
    qpid, hop = key
    if len(series["t"]) > 0:
        plt.plot(series["t"], series["qlen"], label=f"QP {qpid} Hop {hop}", marker='.', markersize=2, linestyle='None')

plt.xlabel("Time (s)")
plt.ylabel("Queue Length (bytes)")
plt.title("Instantaneous Switch Queue Depth (INT)")
plt.legend()
plt.grid(True)

output_file = 'results/plots/instantaneous_queue_depth.png'
# If running from scripts dir
if not os.path.exists('results/plots'):
    if os.path.exists('../plots'):
        output_file = '../plots/instantaneous_queue_depth.png'
    else:
        # Fallback create
        os.makedirs('results/plots', exist_ok=True)

plt.savefig(output_file)
print(f"Saved plot to {output_file}")
