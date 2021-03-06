# Traffic Generator
This folder includes the scripts for generating traffic.

## Usage

`python traffic_gen.py -h` for help.

Example:
`python traffic_gen.py -c WebSearch_distribution.txt -n 320 -l 0.3 -b 100G -t 0.1` generates traffic according to the web search flow size distribution, for 320 hosts, at 30% network load with 100Gbps host bandwidth for 0.1 seconds.

The generate traffic can be directly used by the simulation.

## Traffic format
The first line is the number of flows.

Each line after that is a flow: `<source host> <dest host> 3 <dest port number> <flow size (bytes)> <start time (seconds)>`

## Flow size distributions
We provide 4 distributions. `WebSearch_distribution.txt` and `FbHdp_distribution.txt` are the ones used in the HPCC paper. `AliStorage2019.txt` are collected from Alibaba's production distributed storage system in 2019. `GoogleRPC2008.txt` are Google's RPC size distribution before 2008.
