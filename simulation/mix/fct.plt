set term pngcairo size 1200,600
set output "fct_slowdown.png"
set datafile separator whitespace
set datafile missing "nan"        # 把 'nan' 当作缺失点
set grid
set xlabel "Flow size (bytes)"
set ylabel "FCT slowdown (actual/ideal)"
set key outside top center horizontal box

# 如果你需要对数坐标，保留下一行；否则先注释掉以确认能画出来
#set logscale x 2

# 只有 1 个 CC（列3~5是 P50/P95/P99）
plot \
  "fct_slow.tsv" using ( $2>0 ? $2 : 1/0 ) : 3 with lines lw 2 title "RTTCC P50", \
  ""             using ( $2>0 ? $2 : 1/0 ) : 4 with lines lw 2 title "RTTCC P95", \
  ""             using ( $2>0 ? $2 : 1/0 ) : 5 with lines lw 2 title "RTTCC P99"

