set term pngcairo size 1400,600
set output "rate_all.png"
set datafile separator whitespace
#set datafile separator ","
set grid
set xlabel "Time (s)"
set ylabel "Rate (Gbps)"
set key outside top center horizontal box

plot \
  "rttcc_n2_S0.2-10000_D0.1-100_pg3.csv"  using 1:9 with lines lw 2 title "Flow 1", \
  "rttcc_n3_S0.3-10000_D0.1-100_pg3.csv"  using 1:9 with lines lw 2 title "Flow 2", \
  "rttcc_n4_S0.4-10000_D0.1-100_pg3.csv"  using 1:9 with lines lw 2 title "Flow 3", \
  "rttcc_n5_S0.5-10000_D0.1-100_pg3.csv"  using 1:9 with lines lw 2 title "Flow 4", \
  "rttcc_n6_S0.6-10000_D0.1-100_pg3.csv"  using 1:9 with lines lw 2 title "Flow 5", \
  "rttcc_n7_S0.7-10000_D0.1-100_pg3.csv"  using 1:9 with lines lw 2 title "Flow 6", \
  "rttcc_n8_S0.8-10000_D0.1-100_pg3.csv"  using 1:9 with lines lw 2 title "Flow 7", \
  "rttcc_n9_S0.9-10000_D0.1-100_pg3.csv"  using 1:9 with lines lw 2 title "Flow 8", \
  "rttcc_n10_S0.10-10000_D0.1-100_pg3.csv"  using 1:9 with lines lw 2 title "Flow 9", \
  "rttcc_n11_S0.11-10000_D0.1-100_pg3.csv" using 1:9 with lines lw 2 title "Flow 10"

