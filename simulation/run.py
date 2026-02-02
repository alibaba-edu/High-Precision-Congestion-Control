import argparse
import sys
import os

config_template="""ENABLE_QCN 1 {{0: disable, 1: enable}}
USE_DYNAMIC_PFC_THRESHOLD 1 {{0: disable, 1: enable}}

PACKET_PAYLOAD_SIZE 1000 {{packet size (bytes)}}

TOPOLOGY_FILE mix/topologies/{topo}.txt {{input file: topology}}
FLOW_FILE mix/flows/{trace}.txt {{input file: flow to generate}}
TRACE_FILE mix/inputs/trace.txt {{input file: nodes to monitor packet-level events}}
TRACE_OUTPUT_FILE mix/outputs/trace/mix_{topo}_{trace}_{cc}{failure}.tr {{output file: packet-level events}}
FCT_OUTPUT_FILE mix/outputs/fct/fct_{topo}_{trace}_{cc}{failure}.txt {{output file: flow completion time}}
PFC_OUTPUT_FILE mix/outputs/pfc/pfc_{topo}_{trace}_{cc}{failure}.txt {{output file: PFC}}
CWND_OUTPUT_FILE mix/outputs/cwnd/cwnd_{topo}_{trace}_{cc}{failure}.txt {{output file: qp rate/window trace}}

SIMULATOR_STOP_TIME 4.00 {{simulation stop time}}

CC_MODE {mode} {{1: DCQCN, 3: HPCC, 7: TIMELY, 8: DCTCP, 10: HPCC-PINT}}
ALPHA_RESUME_INTERVAL {t_alpha} {{for DCQCN: interval of update alpha}}
RATE_DECREASE_INTERVAL {t_dec} {{for DCQCN: interval of rate decrease}}
CLAMP_TARGET_RATE 0 {{for DCQCN: reduce target rate on consecutive decrease}}
RP_TIMER {t_inc} {{for DCQCN: interval of rate increase}}
EWMA_GAIN {g} {{for DCQCN/DCTCP: EWMA gain}}
FAST_RECOVERY_TIMES 1 {{for DCQCN: number of fast recovery increases}}
RATE_AI {ai}Mb/s {{additive increase (not for DCTCP)}}
RATE_HAI {hai}Mb/s {{hyper additive increase}}
MIN_RATE 1000Mb/s {{minimum rate}}
DCTCP_RATE_AI {dctcp_ai}Mb/s {{additive increase for DCTCP}}

ERROR_RATE_PER_LINK 0.0000 {{error rate of each link}}
L2_CHUNK_SIZE 4000 {{for DCQCN: chunk size}}
L2_ACK_INTERVAL 1 {{packets between ACK generation, 1 means per packet}}
L2_BACK_TO_ZERO 0 {{0: go-back-0, 1: go-back-N}}

HAS_WIN {has_win} {{0: no window, 1: has a window}}
GLOBAL_T 1 {{0: per-pair RTT, 1: global max RTT}}
VAR_WIN {vwin} {{0: fixed window, 1: variable window}}
FAST_REACT {us} {{0: react per RTT, 1: react per ACK}}
U_TARGET {u_tgt} {{for HPCC: target utilization}}
MI_THRESH {mi} {{for HPCC: maxStage}}
INT_MULTI {int_multi} {{for HPCC: INT scaling}}
MULTI_RATE 0 {{for HPCC: 0: single rate, 1: per hop}}
SAMPLE_FEEDBACK 0 {{for HPCC: 0: per packet, 1: per RTT or qlen>0}}
PINT_LOG_BASE {pint_log_base} {{for HPCC-PINT: log base}}
PINT_PROB {pint_prob} {{for HPCC-PINT: sampling probability}}

RATE_BOUND 1 {{0: no rate limiter, 1: use rate limiter}}

ACK_HIGH_PRIO {ack_prio} {{0: same priority as data, 1: prioritize ACK}}

LINK_DOWN {link_down} {{a b c: take down link between b and c at time a}}

ENABLE_TRACE {enable_tr} {{dump packet-level events or not}}
ENABLE_CWND_TRACE 1 {{dump qp rate/window trace or not}}

KMAX_MAP {kmax_map} {{bandwidth->kmax map}}
KMIN_MAP {kmin_map} {{bandwidth->kmin map}}
PMAX_MAP {pmax_map} {{bandwidth->pmax map}}
BUFFER_SIZE {buffer_size} {{buffer size per switch (MB)}}
QLEN_MON_FILE mix/outputs/qlen/qlen_{topo}_{trace}_{cc}{failure}.txt {{output file: queue length}}
QLEN_MON_START 2000000000 {{start time of dumping qlen}}
QLEN_MON_END 3000000000 {{end time of dumping qlen}}
"""
if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='run simulation')
	parser.add_argument('--cc', dest='cc', action='store', default='hp', help="hp/dcqcn/timely/dctcp/hpccPint")
	parser.add_argument('--trace', dest='trace', action='store', default='flow', help="the name of the flow file")
	parser.add_argument('--bw', dest="bw", action='store', default='50', help="the NIC bandwidth")
	parser.add_argument('--down', dest='down', action='store', default='0 0 0', help="link down event")
	parser.add_argument('--topo', dest='topo', action='store', default='fat', help="the name of the topology file")
	parser.add_argument('--utgt', dest='utgt', action='store', type=int, default=95, help="eta of HPCC")
	parser.add_argument('--mi', dest='mi', action='store', type=int, default=0, help="MI_THRESH")
	parser.add_argument('--hpai', dest='hpai', action='store', type=int, default=0, help="AI for HPCC")
	parser.add_argument('--pint_log_base', dest='pint_log_base', action = 'store', type=float, default=1.01, help="PINT's log_base")
	parser.add_argument('--pint_prob', dest='pint_prob', action = 'store', type=float, default=1.0, help="PINT's sampling probability")
	parser.add_argument('--enable_tr', dest='enable_tr', action = 'store', type=int, default=0, help="enable packet-level events dump")
	args = parser.parse_args()

	topo=args.topo
	bw = int(args.bw)
	trace = args.trace
	#bfsz = 16 if bw==50 else 32
	bfsz = 16 * bw / 50
	u_tgt=args.utgt/100.
	mi=args.mi
	pint_log_base=args.pint_log_base
	pint_prob = args.pint_prob
	enable_tr = args.enable_tr

	failure = ''
	if args.down != '0 0 0':
		failure = '_down'

	config_name = "mix/configs/config_%s_%s_%s%s.txt"%(topo, trace, args.cc, failure)

	kmax_map = "3 %d %d %d %d %d %d"%(10000000000, 400*10/25, bw*1000000000, 400*bw/25, bw*4*1000000000, 400*bw*4/25)
	kmin_map = "3 %d %d %d %d %d %d"%(10000000000, 100*10/25, bw*1000000000, 100*bw/25, bw*4*1000000000, 100*bw*4/25)
	pmax_map = "3 %d %.2f %d %.2f %d %.2f"%(10000000000, 0.2, bw*1000000000, 0.2, bw*4*1000000000, 0.2)
	if (args.cc.startswith("dcqcn")):
		ai = 5 * bw / 25
		hai = 50 * bw /25

		if args.cc == "dcqcn":
			config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=1, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=0, vwin=0, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=1, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr)
		elif args.cc == "dcqcn_paper":
			config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=1, t_alpha=50, t_dec=50, t_inc=55, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=0, vwin=0, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=1, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr)
		elif args.cc == "dcqcn_vwin":
			config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=1, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=1, vwin=1, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr)
		elif args.cc == "dcqcn_paper_vwin":
			config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=1, t_alpha=50, t_dec=50, t_inc=55, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=1, vwin=1, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr)
	elif args.cc == "hp":
		ai = 10 * bw / 25;
		if args.hpai > 0:
			ai = args.hpai
		hai = ai # useless
		int_multi = bw / 25;
		cc = "%s%d"%(args.cc, args.utgt)
		if (mi > 0):
			cc += "mi%d"%mi
		if args.hpai > 0:
			cc += "ai%d"%ai
		config_name = "mix/config_%s_%s_%s%s.txt"%(topo, trace, cc, failure)
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=cc, mode=3, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=1, vwin=1, us=1, u_tgt=u_tgt, mi=mi, int_multi=int_multi, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr)
	elif args.cc == "dctcp":
		ai = 10 # ai is useless for dctcp
		hai = ai  # also useless
		dctcp_ai=615 # calculated from RTT=13us and MTU=1KB, because DCTCP add 1 MTU per RTT.
		kmax_map = "2 %d %d %d %d"%(bw*1000000000, 30*bw/10, bw*4*1000000000, 30*bw*4/10)
		kmin_map = "2 %d %d %d %d"%(bw*1000000000, 30*bw/10, bw*4*1000000000, 30*bw*4/10)
		pmax_map = "2 %d %.2f %d %.2f"%(bw*1000000000, 1.0, bw*4*1000000000, 1.0)
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=8, t_alpha=1, t_dec=4, t_inc=300, g=0.0625, ai=ai, hai=hai, dctcp_ai=dctcp_ai, has_win=1, vwin=1, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr)
	elif args.cc == "timely":
		ai = 10 * bw / 10;
		hai = 50 * bw / 10;
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=7, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=0, vwin=0, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=1, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr)
	elif args.cc == "timely_vwin":
		ai = 10 * bw / 10;
		hai = 50 * bw / 10;
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=7, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=1, vwin=1, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=1, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr)
	elif args.cc == "hpccPint":
		ai = 10 * bw / 25;
		if args.hpai > 0:
			ai = args.hpai
		hai = ai # useless
		int_multi = bw / 25;
		cc = "%s%d"%(args.cc, args.utgt)
		if (mi > 0):
			cc += "mi%d"%mi
		if args.hpai > 0:
			cc += "ai%d"%ai
		cc += "log%.3f"%pint_log_base
		cc += "p%.3f"%pint_prob
		config_name = "mix/config_%s_%s_%s%s.txt"%(topo, trace, cc, failure)
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=cc, mode=10, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=1, vwin=1, us=1, u_tgt=u_tgt, mi=mi, int_multi=int_multi, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr)
	else:
		print "unknown cc:", args.cc
		sys.exit(1)

	with open(config_name, "w") as file:
		file.write(config)
	
	os.system("./waf --run 'scratch/third %s'"%(config_name))
