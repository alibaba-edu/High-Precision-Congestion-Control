set term pngcairo size 1400,600
set output "rate_all.png"
set datafile separator whitespace
set datafile separator ","
set grid
set xlabel "Time (s)"
set ylabel "Rate (Gbps)"
set key outside top center horizontal box

plot \
  "flow1.csv"  using 1:9 with lines lw 2 title "Flow 1", \
  "flow2.csv"  using 1:9 with lines lw 2 title "Flow 2", \
  "flow3.csv"  using 1:9 with lines lw 2 title "Flow 3", \
  "flow4.csv"  using 1:9 with lines lw 2 title "Flow 4", \
  "flow5.csv"  using 1:9 with lines lw 2 title "Flow 5", \
  "flow6.csv"  using 1:9 with lines lw 2 title "Flow 6", \
  "flow7.csv"  using 1:9 with lines lw 2 title "Flow 7", \
  "flow8.csv"  using 1:9 with lines lw 2 title "Flow 8", \
  "flow9.csv"  using 1:9 with lines lw 2 title "Flow 9", \
  "flow10.csv" using 1:9 with lines lw 2 title "Flow 10"

