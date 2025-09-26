set term pngcairo size 1600,650
set output "hpcc_rates.png"

#set datafile separator ","
set xlabel "Time (s)"
set ylabel "Rate (Gbps)"
set grid
set key outside
set format x "%.3f"

# 可选：聚焦稳定段，更容易看到 ~10Gbps 平台
 set xrange [2.00:2.14]
# set yrange [0:40]

plot \
  "< awk -F',' 'NR>1 && $2==2  {print $1,$8}'  hpcc.csv | sort -n -k1,1" using 1:2 w l lw 2 t "Flow 1 (node=2)", \
  "< awk -F',' 'NR>1 && $2==3  {print $1,$8}'  hpcc.csv | sort -n -k1,1" using 1:2 w l lw 2 t "Flow 2 (node=3)", \
  "< awk -F',' 'NR>1 && $2==4  {print $1,$8}'  hpcc.csv | sort -n -k1,1" using 1:2 w l lw 2 t "Flow 3 (node=4)", \
  "< awk -F',' 'NR>1 && $2==5  {print $1,$8}'  hpcc.csv | sort -n -k1,1" using 1:2 w l lw 2 t "Flow 4 (node=5)", \
  "< awk -F',' 'NR>1 && $2==6  {print $1,$8}'  hpcc.csv | sort -n -k1,1" using 1:2 w l lw 2 t "Flow 5 (node=6)", \
  "< awk -F',' 'NR>1 && $2==7  {print $1,$8}'  hpcc.csv | sort -n -k1,1" using 1:2 w l lw 2 t "Flow 6 (node=7)", \
  "< awk -F',' 'NR>1 && $2==8  {print $1,$8}'  hpcc.csv | sort -n -k1,1" using 1:2 w l lw 2 t "Flow 7 (node=8)", \
  "< awk -F',' 'NR>1 && $2==9  {print $1,$8}'  hpcc.csv | sort -n -k1,1" using 1:2 w l lw 2 t "Flow 8 (node=9)", \
  "< awk -F',' 'NR>1 && $2==10 {print $1,$8}'  hpcc.csv | sort -n -k1,1" using 1:2 w l lw 2 t "Flow 9 (node=10)", \
  "< awk -F',' 'NR>1 && $2==11 {print $1,$8}'  hpcc.csv | sort -n -k1,1" using 1:2 w l lw 2 t "Flow 10 (node=11)"


unset output

