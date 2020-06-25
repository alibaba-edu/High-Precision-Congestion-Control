all : trace_reader

trace_reader : trace_reader.cpp trace-format.h trace_filter.hpp utils.hpp sim-setting.h
	g++ trace_reader.cpp -o trace_reader -O3 -std=gnu++11

