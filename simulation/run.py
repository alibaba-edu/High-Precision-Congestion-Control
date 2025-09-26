import argparse
import sys
import os

config_template="""ENABLE_QCN 1
USE_DYNAMIC_PFC_THRESHOLD 1

PACKET_PAYLOAD_SIZE 1000

TOPOLOGY_FILE mix/{topo}.txt
FLOW_FILE mix/{trace}.txt
TRACE_FILE mix/trace.txt
TRACE_OUTPUT_FILE mix/mix_{topo}_{trace}_{cc}{failure}.tr
FCT_OUTPUT_FILE mix/fct_{topo}_{trace}_{cc}{failure}.txt
PFC_OUTPUT_FILE mix/pfc_{topo}_{trace}_{cc}{failure}.txt

SIMULATOR_STOP_TIME 4.00

CC_MODE {mode}
ALPHA_RESUME_INTERVAL {t_alpha}
RATE_DECREASE_INTERVAL {t_dec}
CLAMP_TARGET_RATE 0
RP_TIMER {t_inc}
EWMA_GAIN {g}
FAST_RECOVERY_TIMES 1
RATE_AI {ai}Mb/s
RATE_HAI {hai}Mb/s
MIN_RATE 1000Mb/s
DCTCP_RATE_AI {dctcp_ai}Mb/s

ERROR_RATE_PER_LINK 0.0000
L2_CHUNK_SIZE 4000
L2_ACK_INTERVAL 1
L2_BACK_TO_ZERO 0

HAS_WIN {has_win}
GLOBAL_T 1
VAR_WIN {vwin}
FAST_REACT {us}
U_TARGET {u_tgt}
MI_THRESH {mi}
INT_MULTI {int_multi}
MULTI_RATE 0
SAMPLE_FEEDBACK 0
PINT_LOG_BASE {pint_log_base}
PINT_PROB {pint_prob}

RATE_BOUND 1

ACK_HIGH_PRIO {ack_prio}

LINK_DOWN {link_down}

ENABLE_TRACE {enable_tr}

KMAX_MAP {kmax_map}
KMIN_MAP {kmin_map}
PMAX_MAP {pmax_map}
BUFFER_SIZE {buffer_size}
QLEN_MON_FILE mix/qlen_{topo}_{trace}_{cc}{failure}.txt
QLEN_MON_START 2000000000
QLEN_MON_END 3000000000


MYCC_PSTAR {mycc_pstar}
MYCC_KP {mycc_kp}
MYCC_KI {mycc_ki}
MYCC_INTEG_CAP {mycc_integ_cap}
MYCC_EWMA {mycc_ewma}
MYCC_WIN {mycc_win}
MYCC_PROBE_STEP {mycc_probe_step}
MYCC_SEVERE_TH {mycc_severe_th}
MYCC_SEVERE_MUL {mycc_severe_mul}

# ===== Rttcc (CcMode=12) =====
RTTCC_ALPHA {rttcc_alpha}
RTTCC_RTT_LOW {rttcc_rtt_low}
RTTCC_RTT_TARGET {rttcc_rtt_target}
RTTCC_RATE_LINE {rttcc_rate_line}Mb/s
RTTCC_BASE_INTERVAL_NS {rttcc_base_ns}
RTTCC_FAST_EXTRA_NS {rttcc_fast_extra_ns}
RTTCC_DECREASE_BASE_NS {rttcc_dec_base_ns}
RTTCC_CONVERGE_BASE_NS {rttcc_cvg_base_ns}
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
	parser.add_argument('--mycc', dest='mycc', action='store_true', help="use MYCC (mode 11)")#==========Mycc============
	parser.add_argument('--mycc_pstar', type=float, default=0.05)
	parser.add_argument('--mycc_kp',    type=float, default=0.06)
	parser.add_argument('--mycc_ki',    type=float, default=0.006)
	parser.add_argument('--mycc_integ_cap', type=float, default=1.0)
	parser.add_argument('--mycc_ewma',  type=float, default=0.8)
	parser.add_argument('--mycc_win',   type=int,   default=16)
	parser.add_argument('--mycc_probe_step', type=float, default=8e8)   # 0.8Gbps
	parser.add_argument('--mycc_severe_th',  type=float, default=0.20)
	parser.add_argument('--mycc_severe_mul', type=float, default=0.70)
	# ---------- Rttcc options ----------
	parser.add_argument('--rttcc', dest='rttcc', action='store_true', help="use Rttcc (mode 12)")
	parser.add_argument('--rttcc_alpha', type=float, default=0.5)
	parser.add_argument('--rttcc_rtt_low', type=int, default=9000, help="ns")
	parser.add_argument('--rttcc_rtt_target', type=int, default=16000, help="ns")
	parser.add_argument('--rttcc_rate_line', type=int, default=None, help="Mb/s; default = NIC bw (Gbps)*1000")
	parser.add_argument('--rttcc_base_ns', type=int, default=9000)
	parser.add_argument('--rttcc_fast_extra_ns', type=int, default=18000)
	parser.add_argument('--rttcc_dec_base_ns', type=int, default=20000)
	parser.add_argument('--rttcc_cvg_base_ns', type=int, default=80000)
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

	config_name = "mix/config_%s_%s_%s%s.txt"%(topo, trace, args.cc, failure)

	kmax_map = "2 %d %d %d %d"%(bw*1000000000, 400*bw/25, bw*4*1000000000, 400*bw*4/25)
	kmin_map = "2 %d %d %d %d"%(bw*1000000000, 100*bw/25, bw*4*1000000000, 100*bw*4/25)
	pmax_map = "2 %d %.2f %d %.2f"%(bw*1000000000, 0.2, bw*4*1000000000, 0.2)
	if (args.cc.startswith("dcqcn")):
		ai = 5 * bw / 25
		hai = 50 * bw /25

		if args.cc == "dcqcn":
			config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=1, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=0, vwin=0, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=1, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr,mycc_pstar=0.05,#add mycc
    mycc_kp=0.06,
    mycc_ki=0.006,
    mycc_integ_cap=1.0,
    mycc_ewma=0.8,
    mycc_win=16,
    mycc_probe_step=8e8,
    mycc_severe_th=0.20,
    mycc_severe_mul=0.70,
	rttcc_alpha=0.5,rttcc_rtt_low=9000,rttcc_rtt_target=16000,rttcc_rate_line=100000000000,rttcc_base_ns=9000,rttcc_fast_extra_ns=18000,rttcc_dec_base_ns=20000,rttcc_cvg_base_ns=80000)
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
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=cc, mode=3, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=1, vwin=1, us=1, u_tgt=u_tgt, mi=mi, int_multi=int_multi, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=0, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr,mycc_pstar=0.05,#add mycc
    mycc_kp=0.06,
    mycc_ki=0.006,
    mycc_integ_cap=1.0,
    mycc_ewma=0.8,
    mycc_win=16,
    mycc_probe_step=8e8,
    mycc_severe_th=0.20,
    mycc_severe_mul=0.70,
	rttcc_alpha=0.5,rttcc_rtt_low=9000,rttcc_rtt_target=16000,rttcc_rate_line=100000000000,rttcc_base_ns=9000,rttcc_fast_extra_ns=18000,rttcc_dec_base_ns=20000,rttcc_cvg_base_ns=80000)
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
		config = config_template.format(bw=bw, trace=trace, topo=topo, cc=args.cc, mode=7, t_alpha=1, t_dec=4, t_inc=300, g=0.00390625, ai=ai, hai=hai, dctcp_ai=1000, has_win=0, vwin=0, us=0, u_tgt=u_tgt, mi=mi, int_multi=1, pint_log_base=pint_log_base, pint_prob=pint_prob, ack_prio=1, link_down=args.down, failure=failure, kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map, buffer_size=bfsz, enable_tr=enable_tr,mycc_pstar=0.05,#add mycc
    mycc_kp=0.06,
    mycc_ki=0.006,
    mycc_integ_cap=1.0,
    mycc_ewma=0.8,
    mycc_win=16,
    mycc_probe_step=8e8,
    mycc_severe_th=0.20,
    mycc_severe_mul=0.70,
	rttcc_alpha=0.5,rttcc_rtt_low=9000,rttcc_rtt_target=16000,rttcc_rate_line=100000000000,rttcc_base_ns=9000,rttcc_fast_extra_ns=18000,rttcc_dec_base_ns=20000,rttcc_cvg_base_ns=80000)
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
	elif args.cc == "mycc":
    		ai  = 10 * bw / 25
    		hai = ai
    		cc  = "mycc"
    		config = config_template.format(
        		bw=bw, trace=trace, topo=topo, cc=cc, mode=11,
        		t_alpha=1, t_dec=4, t_inc=300, g=0.00390625,
        		ai=ai, hai=hai, dctcp_ai=1000,
        		has_win=1, vwin=1, us=1, u_tgt=u_tgt, mi=mi, int_multi=1,
        		pint_log_base=pint_log_base, pint_prob=pint_prob,
        		ack_prio=0, link_down=args.down, failure=failure,
        		kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map,
        		buffer_size=bfsz, enable_tr=enable_tr,
        		# adding mycc
        		mycc_pstar=args.mycc_pstar,
        		mycc_kp=args.mycc_kp,
        		mycc_ki=args.mycc_ki,
        		mycc_integ_cap=args.mycc_integ_cap,
        		mycc_ewma=args.mycc_ewma,
        		mycc_win=args.mycc_win,
        		mycc_probe_step=args.mycc_probe_step,
        		mycc_severe_th=args.mycc_severe_th,
        		mycc_severe_mul=args.mycc_severe_mul
    		)
	elif args.cc == "rttcc":
    		ai  = 10 * bw / 25     
    		hai = ai
    		cc  = "rttcc"

    		rttcc_rate_line = args.rttcc_rate_line if args.rttcc_rate_line is not None else (bw * 1000)

    		config = config_template.format(
        		bw=bw, trace=trace, topo=topo, cc=cc, mode=12,       
        		t_alpha=1, t_dec=4, t_inc=300, g=0.00390625,         
        		ai=ai, hai=hai, dctcp_ai=1000,
        		has_win=0, vwin=0, us=1, u_tgt=u_tgt, mi=mi, int_multi=1,
        		pint_log_base=pint_log_base, pint_prob=pint_prob,
        		ack_prio=1,                                         
        		link_down=args.down, failure=failure,
        		kmax_map=kmax_map, kmin_map=kmin_map, pmax_map=pmax_map,
        		buffer_size=bfsz, enable_tr=enable_tr,

        		mycc_pstar=0.05, mycc_kp=0.06, mycc_ki=0.006, mycc_integ_cap=1.0,
        		mycc_ewma=0.8, mycc_win=16, mycc_probe_step=8e8, mycc_severe_th=0.20, mycc_severe_mul=0.70,

        		rttcc_alpha=args.rttcc_alpha,
        		rttcc_rtt_low=args.rttcc_rtt_low,
        		rttcc_rtt_target=args.rttcc_rtt_target,
        		rttcc_rate_line=rttcc_rate_line,             # Mb/s
        		rttcc_base_ns=args.rttcc_base_ns,
        		rttcc_fast_extra_ns=args.rttcc_fast_extra_ns,
        		rttcc_dec_base_ns=args.rttcc_dec_base_ns,
        		rttcc_cvg_base_ns=args.rttcc_cvg_base_ns
    		)
	else:
		print "unknown cc:", args.cc
		sys.exit(1)

	with open(config_name, "w") as file:
		file.write(config)
	
	os.system("./waf --run 'scratch/third %s'"%(config_name))
