# Analysis
This folder includes code and scripts for analysis.

## FCT analysis
`fct_analysis.py` is used to analyze fct. It reads multiple fct files (simulation's output), and prints data that can produce figures like Figure 11 (a) and (c) in [HPCC paper](https://liyuliang001.github.io/publications/hpcc.pdf).

Usage: please check `python fct_analysis.py -h` and read line 20-26 in `fct_analysis.py`

## Trace reader
`trace_reader` is used to parse the .tr files output by the simulation.

Usage: 

1. `make trace_reader`

2. `./trace_reader <.tr file> [filter_expr]`. The filter_expr is used to filter events. For example, `time > 2000010000` will display only events after 2000010000, `sip=0x0b000101&dip=0x0b000201` will display only events with sip=0x0b000101 and dip=0x0b000201. Feel free to play with it.
