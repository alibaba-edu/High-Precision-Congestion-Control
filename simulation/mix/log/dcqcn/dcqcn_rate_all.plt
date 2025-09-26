# dcqcn_rate_all.plt
PG = 3
SPORT = 10000
DIP = "0.1"
DPORT = 100
PREFIX = ""         # 若文件在 mix/log 下，改成 "mix/log/"

set term pngcairo size 1400,600
set output "dcqcn_rate_all.png"
#set datafile separator ","
set grid
set xlabel "Time (s)"
set ylabel "Rate (Gbps)"
set key outside top center horizontal box

plot for [nid=2:4] \
     sprintf("%sdcqcn_n%d_S0.%d-%d_D%s-%d_pg%d.csv", \
             PREFIX, nid, nid, SPORT, DIP, DPORT, PG) \
     using 1:9 with lines lw 2 title sprintf("Flow %d", nid-1)

