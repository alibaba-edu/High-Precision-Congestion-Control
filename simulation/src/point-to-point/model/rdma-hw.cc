#include <ns3/simulator.h>
#include <ns3/seq-ts-header.h>
#include <ns3/udp-header.h>
#include <ns3/ipv4-header.h>
#include "ns3/ppp-header.h"
#include "ns3/boolean.h"
#include "ns3/uinteger.h"
#include "ns3/double.h"
#include "ns3/data-rate.h"
#include "ns3/pointer.h"
#include "rdma-hw.h"
#include "ppp-header.h"
#include "qbb-header.h"
#include "cn-header.h"
#include "rdma-queue-pair.h"
#include <cstdio>
#include <unordered_map>
#include <cmath>
#include <sstream>
#include <string>
#include <cstdlib>
#include <sstream>
#include <string>

namespace {

  static std::string MakeFlowKey(uint32_t nodeId,
                               const ns3::Ipv4Address& sip, uint16_t sport,
                               const ns3::Ipv4Address& dip, uint16_t dport,
                               uint16_t pg) {
  	std::ostringstream oss;
  	oss << "n" << nodeId
      	<< "_S" << sip << "-" << sport
      	<< "_D" << dip << "-" << dport
      	<< "_pg" << pg;
  	return oss.str();
  }

  // 一个简化的“文件句柄池”：第一次写入时创建文件并写 header
  struct FlowCsvMgr {
  	std::unordered_map<std::string, FILE*> files;

  	~FlowCsvMgr() {
    		for (auto &kv : files) if (kv.second) std::fclose(kv.second);
  	}

  	FILE* get(const std::string& prefix,
            uint32_t nodeId,
            const ns3::Ipv4Address& sip, uint16_t sport,
            const ns3::Ipv4Address& dip, uint16_t dport,
            uint16_t pg,
            const char* header) {
    		std::string key = MakeFlowKey(nodeId, sip, sport, dip, dport, pg);
    		auto it = files.find(prefix + key);
    		if (it != files.end()) return it->second;

    		const std::string base = "mix/log/";
  		// 如果 prefix 里带了子目录（例如 "dcqcn/dcqcn_"），先把目录部分 mkdir -p
  		size_t slash = prefix.find_last_of('/');
  		if (slash != std::string::npos) {
    			std::string dir = base + prefix.substr(0, slash); // e.g. mix/log/dcqcn
    			std::string cmd = "mkdir -p " + dir;
    			(void)std::system(cmd.c_str());
  		} else {
			std::string cmd = "mkdir -p " + base;
			(void)std::system(cmd.c_str());
    			//std::system(std::string("mkdir -p ") + base);
  		}

    		std::string path = base + prefix + key + ".csv";
    		FILE* f = std::fopen(path.c_str(), "w");
    		if (!f) return nullptr;
    		std::fprintf(f, "%s\n", header);
    		files.emplace(prefix + key, f);
    		return f;
  	}
  };

  static FlowCsvMgr g_flowCsv;

  static std::string IpToStr(const ns3::Ipv4Address& a) {
  	std::ostringstream oss;
  	oss << a;          // Ipv4Address 支持 << 打印为 x.x.x.x
  	return oss.str();
  }

  struct RttccFlowLogMgr {
  	std::unordered_map<std::string, FILE*> files;

  	~RttccFlowLogMgr() {
    		for (auto &kv : files) if (kv.second) std::fclose(kv.second);
  	}

  	static std::string IpToStr(const ns3::Ipv4Address& a) {
    		std::ostringstream oss; oss << a; return oss.str(); // 点分十进制
  	}

  	static std::string MakeKey(uint32_t nodeId,
                             const ns3::Ipv4Address& sip, uint16_t sport,
                             const ns3::Ipv4Address& dip, uint16_t dport,
                             uint16_t pg) {
    		std::ostringstream oss;
    		oss << "n" << nodeId
        		<< "_S" << IpToStr(sip) << "-" << sport
        		<< "_D" << IpToStr(dip) << "-" << dport
        		<< "_pg" << pg;
    		return oss.str();
  	}

  	FILE* get(uint32_t nodeId,
            const ns3::Ipv4Address& sip, uint16_t sport,
            const ns3::Ipv4Address& dip, uint16_t dport,
            uint16_t pg) {
    		std::string key = MakeKey(nodeId, sip, sport, dip, dport, pg);
    		auto it = files.find(key);
    		if (it != files.end()) return it->second;

    		// 确保 mix/ 目录存在
    		FILE* probe = std::fopen("mix/log/.probe", "a");
    		if (!probe) std::system("mkdir -p mix/log");  //(void)_mk1;
    		else std::fclose(probe);

		std::string dir  = "mix/log/rttcc";
		std::system(std::string("mkdir -p " + dir).c_str());
		std::string path = dir + "/rttcc_" + key + ".csv";
    		//std::string path = "mix/log/rttcc_" + key + ".csv";
    		FILE* f = std::fopen(path.c_str(), "w");
    		if (!f) return nullptr;

    		std::fprintf(f, "time_s\tnode\tsip\tdip\tsport\tdport\tpg\tphase\trate_Gbps\trtt_ns\tgrad\n");
    		files.emplace(std::move(key), f);
    		return f;
  	}
  };

  static RttccFlowLogMgr g_rttccFlowLogs;
}


namespace ns3{

void RdmaHw::DcqcnMaybeLog(Ptr<RdmaQueuePair> q,
                           const char* phase,
                           uint64_t cur_bps,
                           double alpha,
                           uint64_t tgt_bps,
                           uint32_t stage)
{
  if (!m_dcqcn_log_file) return;

  FILE* f = g_flowCsv.get(
      /*prefix*/ "dcqcn/dcqcn_",
      m_node->GetId(),
      q->sip, q->sport,
      q->dip, q->dport,
      q->m_pg,
      /*header*/ "time_s\tnode\tsip\tdip\tsport\tdport\tpg\tphase\trate_Gbps\talpha\ttarget_Gbps\tstage"
  );
  if (!f) return;

  ns3::Time now = Simulator::Now();
  std::fprintf(f, "%.6f\t%u\t%s\t%s\t%u\t%u\t%u\t%s\t%.3f\t%.6f\t%.3f\t%u\n",
      now.GetSeconds(),
      m_node->GetId(),
      RttccFlowLogMgr::IpToStr(q->sip).c_str(),
      RttccFlowLogMgr::IpToStr(q->dip).c_str(),
      q->sport, q->dport, q->m_pg,
      phase,
      double(cur_bps)/1e9,
      q->mlx.m_alpha,
      double(tgt_bps)/1e9,
      stage
  );
}




void RdmaHw::TimelyMaybeLog(Ptr<RdmaQueuePair> qp,
                            const char* phase,
                            uint64_t cur_bps,
                            uint64_t rtt_ns,
                            double gradient)
{
  // 可选：是否打开日志的开关；若你不想加 Attribute，也可以直接始终记录
  if (!m_timely_log_file) return;

  FILE* f = g_flowCsv.get(
      /*prefix*/ "timely/timely_",
      m_node->GetId(),
      qp->sip, qp->sport,
      qp->dip, qp->dport,
      qp->m_pg,
      /*header*/ "time_s\tnode\tsip\tdip\tsport\tdport\tpg\tphase\trate_Gbps\trtt_ns\tgrad"
  );
  if (!f) return;

  ns3::Time now = Simulator::Now();
  std::fprintf(f, "%.6f\t%u\t%s\t%s\t%u\t%u\t%u\t%s\t%.3f\t%llu\t%.6f\n",
      now.GetSeconds(),
      m_node->GetId(),
      RttccFlowLogMgr::IpToStr(qp->sip).c_str(),
      RttccFlowLogMgr::IpToStr(qp->dip).c_str(),
      qp->sport, qp->dport, qp->m_pg,
      phase,
      double(cur_bps) / 1e9,
      (unsigned long long)rtt_ns,
      gradient
  );
}



void RdmaHw::RttccMaybeLog(Ptr<RdmaQueuePair> qp,
                           const char* phase,
                           uint64_t cur_bps,
                           uint64_t rtt_ns,
                           double gradient)
{
  if (!m_rttcc_log_file) return;

  auto& st = qp->rttcc;
  ns3::Time now = Simulator::Now();

  bool time_ok = st.lastLogTime.IsZero()
              || (uint64_t)(now - st.lastLogTime).GetNanoSeconds() >= m_rttcc_log_every_ns;

  double rel = (st.lastLogBps == 0) ? 1.0
              : std::fabs((double)cur_bps - (double)st.lastLogBps) / (double)st.lastLogBps;

  bool change_ok = (st.lastLogBps == 0) || (rel >= m_rttcc_log_change_pct);
  if (!(time_ok || change_ok)) return;

  FILE* f = g_rttccFlowLogs.get(
      m_node->GetId(),
      qp->sip, qp->sport,
      qp->dip, qp->dport,
      qp->m_pg
  );
  if (f) {
    std::fprintf(f, "%.6f\t%u\t%s\t%s\t%u\t%u\t%u\t%s\t%.3f\t%llu\t%.6f\n",
      now.GetSeconds(),
      m_node->GetId(),
      RttccFlowLogMgr::IpToStr(qp->sip).c_str(),
      RttccFlowLogMgr::IpToStr(qp->dip).c_str(),
      qp->sport, qp->dport, qp->m_pg,
      phase,
      cur_bps / 1e9,
      (unsigned long long)rtt_ns,
      gradient
    );
  }

  st.lastLogTime = now;
  st.lastLogBps  = cur_bps;
}


void RdmaHw::HpccMaybeLog(Ptr<RdmaQueuePair> qp, double rateGbps) {
    static FILE* f = nullptr;
    if (!f) {
        std::system("mkdir -p mix/hpcc_log"); //(void)_mk2;
        f = std::fopen("mix/hpcc_log/hpcc_flows.csv", "w");
        fprintf(f, "time_s,node,sip,dip,sport,dport,pg,rate_Gbps\n");
    }
    ns3::Time now = Simulator::Now();
    fprintf(f, "%.6f,%u,%s,%s,%u,%u,%u,%.3f\n",
        now.GetSeconds(),
        m_node->GetId(),
        IpToStr(qp->sip).c_str(),
        IpToStr(qp->dip).c_str(),
        qp->sport,
        qp->dport,
        qp->m_pg,
        rateGbps);
}





TypeId RdmaHw::GetTypeId (void)
{
	static TypeId tid = TypeId ("ns3::RdmaHw")
		.SetParent<Object> ()
		.AddAttribute("MinRate",
				"Minimum rate of a throttled flow",
				DataRateValue(DataRate("100Mb/s")),
				MakeDataRateAccessor(&RdmaHw::m_minRate),
				MakeDataRateChecker())
		.AddAttribute("Mtu",
				"Mtu.",
				UintegerValue(1000),
				MakeUintegerAccessor(&RdmaHw::m_mtu),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute ("CcMode",
				"which mode of DCQCN is running",
				UintegerValue(0),
				MakeUintegerAccessor(&RdmaHw::m_cc_mode),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("NACK Generation Interval",
				"The NACK Generation interval",
				DoubleValue(500.0),
				MakeDoubleAccessor(&RdmaHw::m_nack_interval),
				MakeDoubleChecker<double>())
		.AddAttribute("L2ChunkSize",
				"Layer 2 chunk size. Disable chunk mode if equals to 0.",
				UintegerValue(0),
				MakeUintegerAccessor(&RdmaHw::m_chunk),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("L2AckInterval",
				"Layer 2 Ack intervals. Disable ack if equals to 0.",
				UintegerValue(0),
				MakeUintegerAccessor(&RdmaHw::m_ack_interval),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("L2BackToZero",
				"Layer 2 go back to zero transmission.",
				BooleanValue(false),
				MakeBooleanAccessor(&RdmaHw::m_backto0),
				MakeBooleanChecker())
		.AddAttribute("EwmaGain",
				"Control gain parameter which determines the level of rate decrease",
				DoubleValue(1.0 / 16),
				MakeDoubleAccessor(&RdmaHw::m_g),
				MakeDoubleChecker<double>())
		.AddAttribute ("RateOnFirstCnp",
				"the fraction of rate on first CNP",
				DoubleValue(1.0),
				MakeDoubleAccessor(&RdmaHw::m_rateOnFirstCNP),
				MakeDoubleChecker<double> ())
		.AddAttribute("ClampTargetRate",
				"Clamp target rate.",
				BooleanValue(false),
				MakeBooleanAccessor(&RdmaHw::m_EcnClampTgtRate),
				MakeBooleanChecker())
		.AddAttribute("RPTimer",
				"The rate increase timer at RP in microseconds",
				DoubleValue(1500.0),
				MakeDoubleAccessor(&RdmaHw::m_rpgTimeReset),
				MakeDoubleChecker<double>())
		.AddAttribute("RateDecreaseInterval",
				"The interval of rate decrease check",
				DoubleValue(4.0),
				MakeDoubleAccessor(&RdmaHw::m_rateDecreaseInterval),
				MakeDoubleChecker<double>())
		.AddAttribute("FastRecoveryTimes",
				"The rate increase timer at RP",
				UintegerValue(5),
				MakeUintegerAccessor(&RdmaHw::m_rpgThreshold),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("AlphaResumInterval",
				"The interval of resuming alpha",
				DoubleValue(55.0),
				MakeDoubleAccessor(&RdmaHw::m_alpha_resume_interval),
				MakeDoubleChecker<double>())
		.AddAttribute("RateAI",
				"Rate increment unit in AI period",
				DataRateValue(DataRate("5Mb/s")),
				MakeDataRateAccessor(&RdmaHw::m_rai),
				MakeDataRateChecker())
		.AddAttribute("RateHAI",
				"Rate increment unit in hyperactive AI period",
				DataRateValue(DataRate("50Mb/s")),
				MakeDataRateAccessor(&RdmaHw::m_rhai),
				MakeDataRateChecker())
		.AddAttribute("VarWin",
				"Use variable window size or not",
				BooleanValue(false),
				MakeBooleanAccessor(&RdmaHw::m_var_win),
				MakeBooleanChecker())
		.AddAttribute("FastReact",
				"Fast React to congestion feedback",
				BooleanValue(true),
				MakeBooleanAccessor(&RdmaHw::m_fast_react),
				MakeBooleanChecker())
		.AddAttribute("MiThresh",
				"Threshold of number of consecutive AI before MI",
				UintegerValue(5),
				MakeUintegerAccessor(&RdmaHw::m_miThresh),
				MakeUintegerChecker<uint32_t>())
		.AddAttribute("TargetUtil",
				"The Target Utilization of the bottleneck bandwidth, by default 95%",
				DoubleValue(0.95),
				MakeDoubleAccessor(&RdmaHw::m_targetUtil),
				MakeDoubleChecker<double>())
		.AddAttribute("UtilHigh",
				"The upper bound of Target Utilization of the bottleneck bandwidth, by default 98%",
				DoubleValue(0.98),
				MakeDoubleAccessor(&RdmaHw::m_utilHigh),
				MakeDoubleChecker<double>())
		.AddAttribute("RateBound",
				"Bound packet sending by rate, for test only",
				BooleanValue(true),
				MakeBooleanAccessor(&RdmaHw::m_rateBound),
				MakeBooleanChecker())
		.AddAttribute("MultiRate",
				"Maintain multiple rates in HPCC",
				BooleanValue(true),
				MakeBooleanAccessor(&RdmaHw::m_multipleRate),
				MakeBooleanChecker())
		.AddAttribute("SampleFeedback",
				"Whether sample feedback or not",
				BooleanValue(false),
				MakeBooleanAccessor(&RdmaHw::m_sampleFeedback),
				MakeBooleanChecker())
		.AddAttribute("TimelyAlpha",
				"Alpha of TIMELY",
				DoubleValue(0.875),
				MakeDoubleAccessor(&RdmaHw::m_tmly_alpha),
				MakeDoubleChecker<double>())
		.AddAttribute("TimelyBeta",
				"Beta of TIMELY",
				DoubleValue(0.8),
				MakeDoubleAccessor(&RdmaHw::m_tmly_beta),
				MakeDoubleChecker<double>())
		.AddAttribute("TimelyTLow",
				"TLow of TIMELY (ns)",
				UintegerValue(50000),
				MakeUintegerAccessor(&RdmaHw::m_tmly_TLow),
				MakeUintegerChecker<uint64_t>())
		.AddAttribute("TimelyTHigh",
				"THigh of TIMELY (ns)",
				UintegerValue(500000),
				MakeUintegerAccessor(&RdmaHw::m_tmly_THigh),
				MakeUintegerChecker<uint64_t>())
		.AddAttribute("TimelyMinRtt",
				"MinRtt of TIMELY (ns)",
				UintegerValue(20000),
				MakeUintegerAccessor(&RdmaHw::m_tmly_minRtt),
				MakeUintegerChecker<uint64_t>())
		.AddAttribute("DctcpRateAI",
				"DCTCP's Rate increment unit in AI period",
				DataRateValue(DataRate("1000Mb/s")),
				MakeDataRateAccessor(&RdmaHw::m_dctcp_rai),
				MakeDataRateChecker())
		.AddAttribute("PintSmplThresh",
				"PINT's sampling threshold in rand()%65536",
				UintegerValue(65536),
				MakeUintegerAccessor(&RdmaHw::pint_smpl_thresh),
				MakeUintegerChecker<uint32_t>())
//========Mycc============
		.AddAttribute("MyccPStar", "Target ECN marking probability", DoubleValue(0.05),
  				MakeDoubleAccessor(&RdmaHw::m_mycc_pStar), MakeDoubleChecker<double>())
		.AddAttribute("MyccKp", "Proportional gain for MYCC PI controller", DoubleValue(0.06),
  				MakeDoubleAccessor(&RdmaHw::m_mycc_Kp), MakeDoubleChecker<double>())
		.AddAttribute("MyccKi", "Integral gain for MYCC PI controller", DoubleValue(0.006),
  				MakeDoubleAccessor(&RdmaHw::m_mycc_Ki), MakeDoubleChecker<double>())
		.AddAttribute("MyccIntegCap", "Integral term absolute cap", DoubleValue(1.0),
  				MakeDoubleAccessor(&RdmaHw::m_mycc_integ_cap), MakeDoubleChecker<double>())
		.AddAttribute("MyccEwma", "EWMA factor for ECN probability estimate", DoubleValue(0.8),
  				MakeDoubleAccessor(&RdmaHw::m_mycc_ewma), MakeDoubleChecker<double>())
		.AddAttribute("MyccWin", "Sliding window size (packets) used for ECN estimation", UintegerValue(16),
  				MakeUintegerAccessor(&RdmaHw::m_mycc_win), MakeUintegerChecker<uint32_t>())
		.AddAttribute("MyccProbeStep", "Additive probe step (bps) when ECN=0", DoubleValue(8e8),   // 0.8 Gbps
  				MakeDoubleAccessor(&RdmaHw::m_mycc_probe_step), MakeDoubleChecker<double>())
		.AddAttribute("MyccSevereTh", "Severe congestion ECN threshold", DoubleValue(0.20),
  				MakeDoubleAccessor(&RdmaHw::m_mycc_severe_th), MakeDoubleChecker<double>())
		.AddAttribute("MyccSevereMul", "Multiplicative decrease factor when severe", DoubleValue(0.70),
  				MakeDoubleAccessor(&RdmaHw::m_mycc_severe_mul), MakeDoubleChecker<double>())
//=========Rttcc==========
		.AddAttribute("RttccAlpha", "EWMA factor for RTT smoothing",
             			DoubleValue(0.5), MakeDoubleAccessor(&RdmaHw::m_rttcc_alpha),
             			MakeDoubleChecker<double>())
		.AddAttribute("RttccRttLow", "RTT low threshold (ns) for fast increase",
             			UintegerValue(9000), MakeUintegerAccessor(&RdmaHw::m_rttcc_rttLow),
             			MakeUintegerChecker<uint64_t>())
		.AddAttribute("RttccRttTarget", "RTT target (ns) for decrease",
             			UintegerValue(25000), MakeUintegerAccessor(&RdmaHw::m_rttcc_rttTarget),
             			MakeUintegerChecker<uint64_t>())
		.AddAttribute("RttccRateLine", "RateLine (bps) used in convergence gradient term",
             			DataRateValue(DataRate("100Gb/s")), MakeDataRateAccessor(&RdmaHw::m_rttcc_rateLine),
             			MakeDataRateChecker())
		.AddAttribute("RttccProbeStep", "Additive probe step (bps) when in very low RTT",
             			DoubleValue(5e8), MakeDoubleAccessor(&RdmaHw::m_rttcc_probe_step),
             			MakeDoubleChecker<double>())
		.AddAttribute("RttccBaseIntervalNs", "Base decision interval (ns)",
             			UintegerValue(15000), MakeUintegerAccessor(&RdmaHw::m_rttcc_baseIntNs),
             			MakeUintegerChecker<uint64_t>())
		.AddAttribute("RttccFastExtraNs", "Extra guard (ns) in fast increase",
             			UintegerValue(20000), MakeUintegerAccessor(&RdmaHw::m_rttcc_fastExtraNs),
             			MakeUintegerChecker<uint64_t>())
		.AddAttribute("RttccDecreaseBaseNs", "Base guard (ns) in decrease",
             			UintegerValue(20000), MakeUintegerAccessor(&RdmaHw::m_rttcc_decBaseNs),
             			MakeUintegerChecker<uint64_t>())
		.AddAttribute("RttccConvergeBaseNs", "Base guard (ns) in convergence",
             			UintegerValue(15000), MakeUintegerAccessor(&RdmaHw::m_rttcc_cvgBaseNs),
             			MakeUintegerChecker<uint64_t>())
		.AddAttribute("RttccLogToFile",
    				"Write Rttcc logs to per-node CSV instead of stdout.",
    				BooleanValue(true),
    				MakeBooleanAccessor(&RdmaHw::m_rttcc_log_file),
    				MakeBooleanChecker())
		.AddAttribute("RttccLogEveryNs",
    				"Minimum interval between two log lines for the same flow (ns).",
    				UintegerValue(20000), // 20us
    				MakeUintegerAccessor(&RdmaHw::m_rttcc_log_every_ns),
    				MakeUintegerChecker<uint64_t>())
		.AddAttribute("RttccLogChangePct",
    				"Minimum relative rate change to trigger a log line (0~1).",
    				DoubleValue(0.02), // 2%
    				MakeDoubleAccessor(&RdmaHw::m_rttcc_log_change_pct),
    				MakeDoubleChecker<double>())
		;
	return tid;
}

RdmaHw::RdmaHw(){
}

void RdmaHw::SetNode(Ptr<Node> node){
	m_node = node;
}
void RdmaHw::Setup(QpCompleteCallback cb){
	for (uint32_t i = 0; i < m_nic.size(); i++){
		Ptr<QbbNetDevice> dev = m_nic[i].dev;
		if (dev == NULL)
			continue;
		// share data with NIC
		dev->m_rdmaEQ->m_qpGrp = m_nic[i].qpGrp;
		// setup callback
		dev->m_rdmaReceiveCb = MakeCallback(&RdmaHw::Receive, this);
		dev->m_rdmaLinkDownCb = MakeCallback(&RdmaHw::SetLinkDown, this);
		dev->m_rdmaPktSent = MakeCallback(&RdmaHw::PktSent, this);
		// config NIC
		dev->m_rdmaEQ->m_rdmaGetNxtPkt = MakeCallback(&RdmaHw::GetNxtPacket, this);
	}
	// setup qp complete callback
	m_qpCompleteCallback = cb;
}

uint32_t RdmaHw::GetNicIdxOfQp(Ptr<RdmaQueuePair> qp){
	auto &v = m_rtTable[qp->dip.Get()];
	if (v.size() > 0){
		return v[qp->GetHash() % v.size()];
	}else{
		NS_ASSERT_MSG(false, "We assume at least one NIC is alive");
	}
}
uint64_t RdmaHw::GetQpKey(uint32_t dip, uint16_t sport, uint16_t pg){
	return ((uint64_t)dip << 32) | ((uint64_t)sport << 16) | (uint64_t)pg;
}
Ptr<RdmaQueuePair> RdmaHw::GetQp(uint32_t dip, uint16_t sport, uint16_t pg){
	uint64_t key = GetQpKey(dip, sport, pg);
	auto it = m_qpMap.find(key);
	if (it != m_qpMap.end())
		return it->second;
	return NULL;
}
void RdmaHw::AddQueuePair(uint64_t size, uint16_t pg, Ipv4Address sip, Ipv4Address dip, uint16_t sport, uint16_t dport, uint32_t win, uint64_t baseRtt, Callback<void> notifyAppFinish){
	// create qp
	Ptr<RdmaQueuePair> qp = CreateObject<RdmaQueuePair>(pg, sip, dip, sport, dport);
	qp->SetSize(size);
	qp->SetWin(win);
	qp->SetBaseRtt(baseRtt);
	qp->SetVarWin(m_var_win);
	qp->SetAppNotifyCallback(notifyAppFinish);

	// add qp
	uint32_t nic_idx = GetNicIdxOfQp(qp);
	m_nic[nic_idx].qpGrp->AddQp(qp);
	uint64_t key = GetQpKey(dip.Get(), sport, pg);
	//std::cout << m_qpMap.count(key) << std::endl;
	m_qpMap[key] = qp;

	//std::cout << "[RdmaHw] QP created, total=" << m_qpMap.size() << "\n";

	// set init variables
	DataRate m_bps = m_nic[nic_idx].dev->GetDataRate();
	qp->m_rate = m_bps;
	qp->m_max_rate = m_bps;
	//std::cout << "init m_bps=" << m_bps.GetBitRate() << " bps\n";
	if (m_cc_mode == 1){
		qp->mlx.m_targetRate = m_bps;
	}else if (m_cc_mode == 3){
		qp->hp.m_curRate = m_bps;
		if (m_multipleRate){
			for (uint32_t i = 0; i < IntHeader::maxHop; i++)
				qp->hp.hopState[i].Rc = m_bps;
		}
	}else if (m_cc_mode == 7){
		qp->tmly.m_curRate = m_bps;
	}else if (m_cc_mode == 10){
		qp->hpccPint.m_curRate = m_bps;
	}else if (m_cc_mode == 11) {          //========= Mycc ============
  		qp->mycc.m_curRate = m_nic[nic_idx].dev->GetDataRate();
  		qp->mycc.win_size = m_mycc_win;
	}else if (m_cc_mode == 12){           // ======== Rttcc ========
  		qp->rttcc.rateCurrent = m_nic[nic_idx].dev->GetDataRate();
  		qp->rttcc.rateTarget  = qp->m_max_rate;          // 目标上限 = 每流最大速率
  		qp->rttcc.recordTimeLast = Simulator::Now();
  		qp->m_rate = qp->rttcc.rateCurrent;              // 与主速率保持一致
	}

	// Notify Nic
	m_nic[nic_idx].dev->NewQp(qp);
}

void RdmaHw::DeleteQueuePair(Ptr<RdmaQueuePair> qp){
	// remove qp from the m_qpMap
	uint64_t key = GetQpKey(qp->dip.Get(), qp->sport, qp->m_pg);
	m_qpMap.erase(key);
}

Ptr<RdmaRxQueuePair> RdmaHw::GetRxQp(uint32_t sip, uint32_t dip, uint16_t sport, uint16_t dport, uint16_t pg, bool create){
	uint64_t key = ((uint64_t)dip << 32) | ((uint64_t)pg << 16) | (uint64_t)dport;
	auto it = m_rxQpMap.find(key);
	if (it != m_rxQpMap.end())
		return it->second;
	if (create){
		// create new rx qp
		Ptr<RdmaRxQueuePair> q = CreateObject<RdmaRxQueuePair>();
		// init the qp
		q->sip = sip;
		q->dip = dip;
		q->sport = sport;
		q->dport = dport;
		q->m_ecn_source.qIndex = pg;
		// store in map
		m_rxQpMap[key] = q;
		return q;
	}
	return NULL;
}
uint32_t RdmaHw::GetNicIdxOfRxQp(Ptr<RdmaRxQueuePair> q){
	auto &v = m_rtTable[q->dip];
	if (v.size() > 0){
		return v[q->GetHash() % v.size()];
	}else{
		NS_ASSERT_MSG(false, "We assume at least one NIC is alive");
	}
}
void RdmaHw::DeleteRxQp(uint32_t dip, uint16_t pg, uint16_t dport){
	uint64_t key = ((uint64_t)dip << 32) | ((uint64_t)pg << 16) | (uint64_t)dport;
	m_rxQpMap.erase(key);
}

int RdmaHw::ReceiveUdp(Ptr<Packet> p, CustomHeader &ch){
	uint8_t ecnbits = ch.GetIpv4EcnBits();

	uint32_t payload_size = p->GetSize() - ch.GetSerializedSize();

	// TODO find corresponding rx queue pair
	Ptr<RdmaRxQueuePair> rxQp = GetRxQp(ch.dip, ch.sip, ch.udp.dport, ch.udp.sport, ch.udp.pg, true);
	if (ecnbits != 0){
		rxQp->m_ecn_source.ecnbits |= ecnbits;
		rxQp->m_ecn_source.qfb++;
	}
	rxQp->m_ecn_source.total++;
	rxQp->m_milestone_rx = m_ack_interval;

	int x = ReceiverCheckSeq(ch.udp.seq, rxQp, payload_size);
	if (x == 1 || x == 2){ //generate ACK or NACK
		qbbHeader seqh;
		seqh.SetSeq(rxQp->ReceiverNextExpectedSeq);
		seqh.SetPG(ch.udp.pg);
		seqh.SetSport(ch.udp.dport);
		seqh.SetDport(ch.udp.sport);
		seqh.SetIntHeader(ch.udp.ih);
		if (ecnbits)
			seqh.SetCnp();

		Ptr<Packet> newp = Create<Packet>(std::max(60-14-20-(int)seqh.GetSerializedSize(), 0));
		newp->AddHeader(seqh);

		Ipv4Header head;	// Prepare IPv4 header
		head.SetDestination(Ipv4Address(ch.sip));
		head.SetSource(Ipv4Address(ch.dip));
		head.SetProtocol(x == 1 ? 0xFC : 0xFD); //ack=0xFC nack=0xFD
		head.SetTtl(64);
		head.SetPayloadSize(newp->GetSize());
		head.SetIdentification(rxQp->m_ipid++);

		newp->AddHeader(head);
		AddHeader(newp, 0x800);	// Attach PPP header
		// send
		uint32_t nic_idx = GetNicIdxOfRxQp(rxQp);
		m_nic[nic_idx].dev->RdmaEnqueueHighPrioQ(newp);
		m_nic[nic_idx].dev->TriggerTransmit();
	}
	return 0;
}

int RdmaHw::ReceiveCnp(Ptr<Packet> p, CustomHeader &ch){
	// QCN on NIC
	// This is a Congestion signal
	// Then, extract data from the congestion packet.
	// We assume, without verify, the packet is destinated to me
	//printf("%u",1);
	uint32_t qIndex = ch.cnp.qIndex;
	if (qIndex == 1){		//DCTCP
		std::cout << "TCP--ignore\n";
		return 0;
	}
	uint16_t udpport = ch.cnp.fid; // corresponds to the sport
	uint8_t ecnbits = ch.cnp.ecnBits;
	uint16_t qfb = ch.cnp.qfb;
	uint16_t total = ch.cnp.total;

	uint32_t i;
	// get qp
	Ptr<RdmaQueuePair> qp = GetQp(ch.sip, udpport, qIndex);
	if (qp == NULL)
		std::cout << "ERROR: QCN NIC cannot find the flow\n";
	// get nic
	uint32_t nic_idx = GetNicIdxOfQp(qp);
	Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;

	if (qp->m_rate == 0)			//lazy initialization	
	{
		qp->m_rate = dev->GetDataRate();
		if (m_cc_mode == 1){
			qp->mlx.m_targetRate = dev->GetDataRate();
		}else if (m_cc_mode == 3){
			qp->hp.m_curRate = dev->GetDataRate();
			if (m_multipleRate){
				for (uint32_t i = 0; i < IntHeader::maxHop; i++)
					qp->hp.hopState[i].Rc = dev->GetDataRate();
			}
		}else if (m_cc_mode == 7){
			qp->tmly.m_curRate = dev->GetDataRate();
		}else if (m_cc_mode == 10){
			qp->hpccPint.m_curRate = dev->GetDataRate();
		}else if (m_cc_mode == 11) {  //============Mycc=============
  			HandleCnpMycc(qp, qfb, total);
		}
	}
	return 0;
}

int RdmaHw::ReceiveAck(Ptr<Packet> p, CustomHeader &ch){
	uint16_t qIndex = ch.ack.pg;
	uint16_t port = ch.ack.dport;
	uint32_t seq = ch.ack.seq;
	uint8_t cnp = (ch.ack.flags >> qbbHeader::FLAG_CNP) & 1;
	int i;
	Ptr<RdmaQueuePair> qp = GetQp(ch.sip, port, qIndex);
	if (qp == NULL){
		std::cout << "ERROR: " << "node:" << m_node->GetId() << ' ' << (ch.l3Prot == 0xFC ? "ACK" : "NACK") << " NIC cannot find the flow\n";
		return 0;
	}

	uint32_t nic_idx = GetNicIdxOfQp(qp);
	Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;
	if (m_ack_interval == 0)
		std::cout << "ERROR: shouldn't receive ack\n";
	else {
		if (!m_backto0){
			qp->Acknowledge(seq);
		}else {
			uint32_t goback_seq = seq / m_chunk * m_chunk;
			qp->Acknowledge(goback_seq);
		}
		if (qp->IsFinished()){
			QpComplete(qp);
		}
	}
	if (ch.l3Prot == 0xFD) // NACK
		RecoverQueue(qp);

	// handle cnp
	if (cnp){
		if (m_cc_mode == 1){ // mlx version
			cnp_received_mlx(qp);
		} 
	}

	if (m_cc_mode == 3){
		HandleAckHp(qp, p, ch);
	}else if (m_cc_mode == 7){
		HandleAckTimely(qp, p, ch);
	}else if (m_cc_mode == 8){
		HandleAckDctcp(qp, p, ch);
	}else if (m_cc_mode == 10){
		HandleAckHpPint(qp, p, ch);
	}else if (m_cc_mode == 11) {  //============Mycc=============
  		HandleAckMycc(qp, p, ch);
	}else if (m_cc_mode == 12){
  		HandleAckRttcc(qp, p, ch);
	}
	// ACK may advance the on-the-fly window, allowing more packets to send
	dev->TriggerTransmit();
	return 0;
}

int RdmaHw::Receive(Ptr<Packet> p, CustomHeader &ch){
	if (ch.l3Prot == 0x11){ // UDP
		ReceiveUdp(p, ch);
	}else if (ch.l3Prot == 0xFF){ // CNP
		ReceiveCnp(p, ch);
	}else if (ch.l3Prot == 0xFD){ // NACK
		ReceiveAck(p, ch);
	}else if (ch.l3Prot == 0xFC){ // ACK
		ReceiveAck(p, ch);
	}
	return 0;
}

int RdmaHw::ReceiverCheckSeq(uint32_t seq, Ptr<RdmaRxQueuePair> q, uint32_t size){
	uint32_t expected = q->ReceiverNextExpectedSeq;
	if (seq == expected){
		q->ReceiverNextExpectedSeq = expected + size;
		if (q->ReceiverNextExpectedSeq >= q->m_milestone_rx){
			q->m_milestone_rx += m_ack_interval;
			return 1; //Generate ACK
		}else if (q->ReceiverNextExpectedSeq % m_chunk == 0){
			return 1;
		}else {
			return 5;
		}
	} else if (seq > expected) {
		// Generate NACK
		if (Simulator::Now() >= q->m_nackTimer || q->m_lastNACK != expected){
			q->m_nackTimer = Simulator::Now() + MicroSeconds(m_nack_interval);
			q->m_lastNACK = expected;
			if (m_backto0){
				q->ReceiverNextExpectedSeq = q->ReceiverNextExpectedSeq / m_chunk*m_chunk;
			}
			return 2;
		}else
			return 4;
	}else {
		// Duplicate. 
		return 3;
	}
}
void RdmaHw::AddHeader (Ptr<Packet> p, uint16_t protocolNumber){
	PppHeader ppp;
	ppp.SetProtocol (EtherToPpp (protocolNumber));
	p->AddHeader (ppp);
}
uint16_t RdmaHw::EtherToPpp (uint16_t proto){
	switch(proto){
		case 0x0800: return 0x0021;   //IPv4
		case 0x86DD: return 0x0057;   //IPv6
		default: NS_ASSERT_MSG (false, "PPP Protocol number not defined!");
	}
	return 0;
}

void RdmaHw::RecoverQueue(Ptr<RdmaQueuePair> qp){
	qp->snd_nxt = qp->snd_una;
}

void RdmaHw::QpComplete(Ptr<RdmaQueuePair> qp){
	NS_ASSERT(!m_qpCompleteCallback.IsNull());
	if (m_cc_mode == 1){
		Simulator::Cancel(qp->mlx.m_eventUpdateAlpha);
		Simulator::Cancel(qp->mlx.m_eventDecreaseRate);
		Simulator::Cancel(qp->mlx.m_rpTimer);
	}

	// This callback will log info
	// It may also delete the rxQp on the receiver
	m_qpCompleteCallback(qp);

	qp->m_notifyAppFinish();

	// delete the qp
	DeleteQueuePair(qp);
}

void RdmaHw::SetLinkDown(Ptr<QbbNetDevice> dev){
	printf("RdmaHw: node:%u a link down\n", m_node->GetId());
}

void RdmaHw::AddTableEntry(Ipv4Address &dstAddr, uint32_t intf_idx){
	uint32_t dip = dstAddr.Get();
	m_rtTable[dip].push_back(intf_idx);
}

void RdmaHw::ClearTable(){
	m_rtTable.clear();
}

void RdmaHw::RedistributeQp(){
	// clear old qpGrp
	for (uint32_t i = 0; i < m_nic.size(); i++){
		if (m_nic[i].dev == NULL)
			continue;
		m_nic[i].qpGrp->Clear();
	}

	// redistribute qp
	for (auto &it : m_qpMap){
		Ptr<RdmaQueuePair> qp = it.second;
		uint32_t nic_idx = GetNicIdxOfQp(qp);
		m_nic[nic_idx].qpGrp->AddQp(qp);
		// Notify Nic
		m_nic[nic_idx].dev->ReassignedQp(qp);
	}
}

Ptr<Packet> RdmaHw::GetNxtPacket(Ptr<RdmaQueuePair> qp){
	uint32_t payload_size = qp->GetBytesLeft();
	if (m_mtu < payload_size)
		payload_size = m_mtu;
	Ptr<Packet> p = Create<Packet> (payload_size);

	uint32_t seq_now = qp->snd_nxt;

	// add SeqTsHeader
	SeqTsHeader seqTs;
	seqTs.SetSeq (qp->snd_nxt);
	seqTs.SetPG (qp->m_pg);
	p->AddHeader (seqTs);
	// add udp header
	UdpHeader udpHeader;
	udpHeader.SetDestinationPort (qp->dport);
	udpHeader.SetSourcePort (qp->sport);
	p->AddHeader (udpHeader);
	// add ipv4 header
	Ipv4Header ipHeader;
	ipHeader.SetSource (qp->sip);
	ipHeader.SetDestination (qp->dip);
	ipHeader.SetProtocol (0x11);
	ipHeader.SetPayloadSize (p->GetSize());
	ipHeader.SetTtl (64);
	ipHeader.SetTos (0);
	ipHeader.SetIdentification (qp->m_ipid);
	p->AddHeader(ipHeader);
	// add ppp header
	PppHeader ppp;
	ppp.SetProtocol (0x0021); // EtherToPpp(0x800), see point-to-point-net-device.cc
	p->AddHeader (ppp);

	// update state
	qp->snd_nxt += payload_size;
	qp->m_ipid++;

	qp->rttcc.tsMap[seq_now] = Simulator::Now();

	// return
	return p;
}

void RdmaHw::PktSent(Ptr<RdmaQueuePair> qp, Ptr<Packet> pkt, Time interframeGap){
	qp->lastPktSize = pkt->GetSize();
	UpdateNextAvail(qp, interframeGap, pkt->GetSize());

	// ==== real throughput (per-QP) windowed logging ====
	const Time win = MicroSeconds(100);                     
	qp->dbg_bytes_win += pkt->GetSize();                    
	if (qp->dbg_win_start.IsZero()) {
    		qp->dbg_win_start = Simulator::Now();
	}
	// 到达窗口末尾就计算吞吐并打印
	Time span = Simulator::Now() - qp->dbg_win_start;
	if (span >= win) {
    		double secs = span.GetSeconds();
    		double bps  = (double)qp->dbg_bytes_win * 8.0 / secs;

    		// 懒加载打开每流日志文件
    		if (!qp->dbg_tp_fp) {
        		// 确保目录存在
        		//(void)std::system("mkdir -p mix/log");

			std::string dir = "mix/log";
			switch (m_cc_mode) {
        			case 1:  dir += "/dcqcn";   break;
        			case 3:  dir += "/hpcc";    break;
        			case 7:  dir += "/timely";  break;
        			case 10: dir += "/hpccpint";break;
        			case 12: dir += "/rttcc";   break;
        			default: dir += "/misc";    break;
      			}
			(void)std::system(std::string("mkdir -p " + dir).c_str());
			//std::system(std::string("mkdir -p " + dir).c_str());
			char fname[256];
			std::snprintf(fname, sizeof(fname),
   				(dir + "/tp_%08x_%08x_%u_%u.pg%u.log").c_str(),
   				qp->sip.Get(), qp->dip.Get(), qp->sport, qp->dport, qp->m_pg);
			qp->dbg_tp_fp = std::fopen(fname, "w");
        		// 为了便于区分流：sip_dip_sport_dport.pg.log
        		//char fname[256];
        		//std::snprintf(fname, sizeof(fname),
                      	//	"mix/log/tp_%08x_%08x_%u_%u.pg%u.log",
                      	//	qp->sip.Get(), qp->dip.Get(),
                      	//	qp->sport, qp->dport, qp->m_pg);
        		//qp->dbg_tp_fp = std::fopen(fname, "w");
        		// 保险起见
        		if (!qp->dbg_tp_fp) {
            			// 打不开就直接返回，不影响仿真
            			qp->dbg_bytes_win = 0;
            			qp->dbg_win_start = Simulator::Now();
            			return;
        		}
        		std::fprintf(qp->dbg_tp_fp,
                     		"# time_ns  throughput_bps  rate_set_bps  bytes_in_window\n");
    		}

    		// 记录当前真实吞吐与控制器设置的速率（方便对比）
    		std::fprintf(qp->dbg_tp_fp, "%lu %.0f %lu %llu\n",
                 	Simulator::Now().GetTimeStep(),        // ns 时间戳
                 	bps,
                 	(unsigned long)qp->m_rate.GetBitRate(),// 目标/设置速率
                 	(unsigned long long)qp->dbg_bytes_win);
    		std::fflush(qp->dbg_tp_fp);

    		// 滑动窗口重置
    		qp->dbg_bytes_win = 0;
    		qp->dbg_win_start = Simulator::Now();
	}

}

void RdmaHw::UpdateNextAvail(Ptr<RdmaQueuePair> qp, Time interframeGap, uint32_t pkt_size){
	Time sendingTime;
	if (m_rateBound)
		sendingTime = interframeGap + Seconds(qp->m_rate.CalculateTxTime(pkt_size));
	else
		sendingTime = interframeGap + Seconds(qp->m_max_rate.CalculateTxTime(pkt_size));
	qp->m_nextAvail = Simulator::Now() + sendingTime;
}

void RdmaHw::ChangeRate(Ptr<RdmaQueuePair> qp, DataRate new_rate){
	#if 1
	Time sendingTime = Seconds(qp->m_rate.CalculateTxTime(qp->lastPktSize));
	Time new_sendintTime = Seconds(new_rate.CalculateTxTime(qp->lastPktSize));
	qp->m_nextAvail = qp->m_nextAvail + new_sendintTime - sendingTime;
	// update nic's next avail event
	uint32_t nic_idx = GetNicIdxOfQp(qp);
	m_nic[nic_idx].dev->UpdateNextAvail(qp->m_nextAvail);
	#endif

	// change to new rate
	qp->m_rate = new_rate;
}



#define PRINT_LOG 0
/******************************
 * Mellanox's version of DCQCN
 *****************************/
void RdmaHw::UpdateAlphaMlx(Ptr<RdmaQueuePair> q){
	#if PRINT_LOG
	//std::cout << Simulator::Now() << " alpha update:" << m_node->GetId() << ' ' << q->mlx.m_alpha << ' ' << (int)q->mlx.m_alpha_cnp_arrived << '\n';
	//printf("%lu alpha update: %08x %08x %u %u %.6lf->", Simulator::Now().GetTimeStep(), q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_alpha);
	#endif
	if (q->mlx.m_alpha_cnp_arrived){
		q->mlx.m_alpha = (1 - m_g)*q->mlx.m_alpha + m_g; 	//binary feedback
	}else {
		q->mlx.m_alpha = (1 - m_g)*q->mlx.m_alpha; 	//binary feedback
	}
	#if PRINT_LOG
	//printf("%.6lf\n", q->mlx.m_alpha);
	#endif
	q->mlx.m_alpha_cnp_arrived = false; // clear the CNP_arrived bit
	ScheduleUpdateAlphaMlx(q);
}
void RdmaHw::ScheduleUpdateAlphaMlx(Ptr<RdmaQueuePair> q){
	q->mlx.m_eventUpdateAlpha = Simulator::Schedule(MicroSeconds(m_alpha_resume_interval), &RdmaHw::UpdateAlphaMlx, this, q);
}

void RdmaHw::cnp_received_mlx(Ptr<RdmaQueuePair> q){
	q->mlx.m_alpha_cnp_arrived = true; // set CNP_arrived bit for alpha update
	q->mlx.m_decrease_cnp_arrived = true; // set CNP_arrived bit for rate decrease
	if (q->mlx.m_first_cnp){
		// init alpha
		q->mlx.m_alpha = 1;
		q->mlx.m_alpha_cnp_arrived = false;
		// schedule alpha update
		ScheduleUpdateAlphaMlx(q);
		// schedule rate decrease
		ScheduleDecreaseRateMlx(q, 1); // add 1 ns to make sure rate decrease is after alpha update
		// set rate on first CNP
		q->mlx.m_targetRate = q->m_rate = m_rateOnFirstCNP * q->m_rate;
		q->mlx.m_first_cnp = false;
		DcqcnMaybeLog(q, "FIRST_CNP",
              		q->m_rate.GetBitRate(),
              		q->mlx.m_alpha,
              		q->mlx.m_targetRate.GetBitRate(),
              		q->mlx.m_rpTimeStage);

	}
}

void RdmaHw::CheckRateDecreaseMlx(Ptr<RdmaQueuePair> q){
	ScheduleDecreaseRateMlx(q, 0);
	if (q->mlx.m_decrease_cnp_arrived){
		#if PRINT_LOG
		printf("%lu rate dec: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(), q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
		#endif
		bool clamp = true;
		if (!m_EcnClampTgtRate){
			if (q->mlx.m_rpTimeStage == 0)
				clamp = false;
		}
		if (clamp)
			q->mlx.m_targetRate = q->m_rate;
		q->m_rate = std::max(m_minRate, q->m_rate * (1 - q->mlx.m_alpha / 2));
		DcqcnMaybeLog(q, "DEC",
              		q->m_rate.GetBitRate(),
              		q->mlx.m_alpha,
              		q->mlx.m_targetRate.GetBitRate(),
              		q->mlx.m_rpTimeStage);

		// reset rate increase related things
		q->mlx.m_rpTimeStage = 0;
		q->mlx.m_decrease_cnp_arrived = false;
		Simulator::Cancel(q->mlx.m_rpTimer);
		q->mlx.m_rpTimer = Simulator::Schedule(MicroSeconds(m_rpgTimeReset), &RdmaHw::RateIncEventTimerMlx, this, q);
		#if PRINT_LOG
		printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
		#endif
	}
}
void RdmaHw::ScheduleDecreaseRateMlx(Ptr<RdmaQueuePair> q, uint32_t delta){
	q->mlx.m_eventDecreaseRate = Simulator::Schedule(MicroSeconds(m_rateDecreaseInterval) + NanoSeconds(delta), &RdmaHw::CheckRateDecreaseMlx, this, q);
}

void RdmaHw::RateIncEventTimerMlx(Ptr<RdmaQueuePair> q){
	q->mlx.m_rpTimer = Simulator::Schedule(MicroSeconds(m_rpgTimeReset), &RdmaHw::RateIncEventTimerMlx, this, q);
	RateIncEventMlx(q);
	q->mlx.m_rpTimeStage++;
}
void RdmaHw::RateIncEventMlx(Ptr<RdmaQueuePair> q){
	// check which increase phase: fast recovery, active increase, hyper increase
	if (q->mlx.m_rpTimeStage < m_rpgThreshold){ // fast recovery
		FastRecoveryMlx(q);
	}else if (q->mlx.m_rpTimeStage == m_rpgThreshold){ // active increase
		ActiveIncreaseMlx(q);
	}else { // hyper increase
		HyperIncreaseMlx(q);
	}
}

void RdmaHw::FastRecoveryMlx(Ptr<RdmaQueuePair> q){
	#if PRINT_LOG
	printf("%lu fast recovery: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(), q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
	q->m_rate = (q->m_rate / 2) + (q->mlx.m_targetRate / 2);
	DcqcnMaybeLog(q, "FAST_REC",
              q->m_rate.GetBitRate(),
              q->mlx.m_alpha,
              q->mlx.m_targetRate.GetBitRate(),
              q->mlx.m_rpTimeStage);
	#if PRINT_LOG
	printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
}
void RdmaHw::ActiveIncreaseMlx(Ptr<RdmaQueuePair> q){
	#if PRINT_LOG
	printf("%lu active inc: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(), q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
	// get NIC
	uint32_t nic_idx = GetNicIdxOfQp(q);
	Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;
	// increate rate
	q->mlx.m_targetRate += m_rai;
	if (q->mlx.m_targetRate > dev->GetDataRate())
		q->mlx.m_targetRate = dev->GetDataRate();
	q->m_rate = (q->m_rate / 2) + (q->mlx.m_targetRate / 2);
	DcqcnMaybeLog(q, "AI",
              q->m_rate.GetBitRate(),
              q->mlx.m_alpha,
              q->mlx.m_targetRate.GetBitRate(),
              q->mlx.m_rpTimeStage);
	#if PRINT_LOG
	printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
}
void RdmaHw::HyperIncreaseMlx(Ptr<RdmaQueuePair> q){
	#if PRINT_LOG
	printf("%lu hyper inc: %08x %08x %u %u (%0.3lf %.3lf)->", Simulator::Now().GetTimeStep(), q->sip.Get(), q->dip.Get(), q->sport, q->dport, q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
	// get NIC
	uint32_t nic_idx = GetNicIdxOfQp(q);
	Ptr<QbbNetDevice> dev = m_nic[nic_idx].dev;
	// increate rate
	q->mlx.m_targetRate += m_rhai;
	if (q->mlx.m_targetRate > dev->GetDataRate())
		q->mlx.m_targetRate = dev->GetDataRate();
	q->m_rate = (q->m_rate / 2) + (q->mlx.m_targetRate / 2);
	DcqcnMaybeLog(q, "HAI",
              q->m_rate.GetBitRate(),
              q->mlx.m_alpha,
              q->mlx.m_targetRate.GetBitRate(),
              q->mlx.m_rpTimeStage);
	#if PRINT_LOG
	printf("(%.3lf %.3lf)\n", q->mlx.m_targetRate.GetBitRate() * 1e-9, q->m_rate.GetBitRate() * 1e-9);
	#endif
}

/***********************
 * High Precision CC
 ***********************/
void RdmaHw::HandleAckHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
	uint32_t ack_seq = ch.ack.seq;
	//std::cout<< "ack:" << ack_seq << std::endl;
	// update rate
	if (ack_seq > qp->hp.m_lastUpdateSeq){ // if full RTT feedback is ready, do full update
		UpdateRateHp(qp, p, ch, false);
		HpccMaybeLog(qp, qp->hp.m_curRate.GetBitRate() * 1e-9);
	}else{ // do fast react
		FastReactHp(qp, p, ch);
	}
}

void RdmaHw::UpdateRateHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool fast_react){
	uint32_t next_seq = qp->snd_nxt;
	bool print = !fast_react || true;
	if (qp->hp.m_lastUpdateSeq == 0){ // first RTT
		qp->hp.m_lastUpdateSeq = next_seq;
		// store INT
		IntHeader &ih = ch.ack.ih;
		NS_ASSERT(ih.nhop <= IntHeader::maxHop);
		for (uint32_t i = 0; i < ih.nhop; i++)
			qp->hp.hop[i] = ih.hop[i];
		#if PRINT_LOG
		if (print){
			printf("%lu %s %08x %08x %u %u [%u,%u,%u]", Simulator::Now().GetTimeStep(), fast_react? "fast" : "update", qp->sip.Get(), qp->dip.Get(), qp->sport, qp->dport, qp->hp.m_lastUpdateSeq, ch.ack.seq, next_seq);
			for (uint32_t i = 0; i < ih.nhop; i++)
				printf(" %u %lu %lu", ih.hop[i].GetQlen(), ih.hop[i].GetBytes(), ih.hop[i].GetTime());
			printf("\n");
		}
		#endif
	}else {
		// check packet INT
		IntHeader &ih = ch.ack.ih;
		if (ih.nhop <= IntHeader::maxHop){
			double max_c = 0;
			bool inStable = false;
			#if PRINT_LOG
			if (print)
				printf("%lu %s %08x %08x %u %u [%u,%u,%u]", Simulator::Now().GetTimeStep(), fast_react? "fast" : "update", qp->sip.Get(), qp->dip.Get(), qp->sport, qp->dport, qp->hp.m_lastUpdateSeq, ch.ack.seq, next_seq);
			#endif
			// check each hop
			double U = 0;
			uint64_t dt = 0;
			bool updated[IntHeader::maxHop] = {false}, updated_any = false;
			NS_ASSERT(ih.nhop <= IntHeader::maxHop);
			for (uint32_t i = 0; i < ih.nhop; i++){
				if (m_sampleFeedback){
					if (ih.hop[i].GetQlen() == 0 && fast_react)
						continue;
				}
				updated[i] = updated_any = true;
				#if PRINT_LOG
				if (print)
					printf(" %u(%u) %lu(%lu) %lu(%lu)", ih.hop[i].GetQlen(), qp->hp.hop[i].GetQlen(), ih.hop[i].GetBytes(), qp->hp.hop[i].GetBytes(), ih.hop[i].GetTime(), qp->hp.hop[i].GetTime());
				#endif
				uint64_t tau = ih.hop[i].GetTimeDelta(qp->hp.hop[i]);;
				double duration = tau * 1e-9;
				double txRate = (ih.hop[i].GetBytesDelta(qp->hp.hop[i])) * 8 / duration;
				double u = txRate / ih.hop[i].GetLineRate() + (double)std::min(ih.hop[i].GetQlen(), qp->hp.hop[i].GetQlen()) * qp->m_max_rate.GetBitRate() / ih.hop[i].GetLineRate() /qp->m_win;
				#if PRINT_LOG
				if (print)
					printf(" %.3lf %.3lf", txRate, u);
				#endif
				if (!m_multipleRate){
					// for aggregate (single R)
					if (u > U){
						U = u;
						dt = tau;
					}
				}else {
					// for per hop (per hop R)
					if (tau > qp->m_baseRtt)
						tau = qp->m_baseRtt;
					qp->hp.hopState[i].u = (qp->hp.hopState[i].u * (qp->m_baseRtt - tau) + u * tau) / double(qp->m_baseRtt);
				}
				qp->hp.hop[i] = ih.hop[i];
			}

			DataRate new_rate;
			int32_t new_incStage;
			DataRate new_rate_per_hop[IntHeader::maxHop];
			int32_t new_incStage_per_hop[IntHeader::maxHop];
			if (!m_multipleRate){
				// for aggregate (single R)
				if (updated_any){
					if (dt > qp->m_baseRtt)
						dt = qp->m_baseRtt;
					qp->hp.u = (qp->hp.u * (qp->m_baseRtt - dt) + U * dt) / double(qp->m_baseRtt);
					max_c = qp->hp.u / m_targetUtil;

					if (max_c >= 1 || qp->hp.m_incStage >= m_miThresh){
						new_rate = qp->hp.m_curRate / max_c + m_rai;
						new_incStage = 0;
					}else{
						new_rate = qp->hp.m_curRate + m_rai;
						new_incStage = qp->hp.m_incStage+1;
					}
					if (new_rate < m_minRate)
						new_rate = m_minRate;
					if (new_rate > qp->m_max_rate)
						new_rate = qp->m_max_rate;
					#if PRINT_LOG
					if (print)
						printf(" u=%.6lf U=%.3lf dt=%u max_c=%.3lf", qp->hp.u, U, dt, max_c);
					#endif
					#if PRINT_LOG
					if (print)
						printf(" rate:%.3lf->%.3lf\n", qp->hp.m_curRate.GetBitRate()*1e-9, new_rate.GetBitRate()*1e-9);
					#endif
				}
			}else{
				// for per hop (per hop R)
				new_rate = qp->m_max_rate;
				for (uint32_t i = 0; i < ih.nhop; i++){
					if (updated[i]){
						double c = qp->hp.hopState[i].u / m_targetUtil;
						if (c >= 1 || qp->hp.hopState[i].incStage >= m_miThresh){
							new_rate_per_hop[i] = qp->hp.hopState[i].Rc / c + m_rai;
							new_incStage_per_hop[i] = 0;
						}else{
							new_rate_per_hop[i] = qp->hp.hopState[i].Rc + m_rai;
							new_incStage_per_hop[i] = qp->hp.hopState[i].incStage+1;
						}
						// bound rate
						if (new_rate_per_hop[i] < m_minRate)
							new_rate_per_hop[i] = m_minRate;
						if (new_rate_per_hop[i] > qp->m_max_rate)
							new_rate_per_hop[i] = qp->m_max_rate;
						// find min new_rate
						if (new_rate_per_hop[i] < new_rate)
							new_rate = new_rate_per_hop[i];
						#if PRINT_LOG
						if (print)
							printf(" [%u]u=%.6lf c=%.3lf", i, qp->hp.hopState[i].u, c);
						#endif
						#if PRINT_LOG
						if (print)
							printf(" %.3lf->%.3lf", qp->hp.hopState[i].Rc.GetBitRate()*1e-9, new_rate.GetBitRate()*1e-9);
						#endif
					}else{
						if (qp->hp.hopState[i].Rc < new_rate)
							new_rate = qp->hp.hopState[i].Rc;
					}
				}
				#if PRINT_LOG
				printf("\n");
				#endif
			}
			if (updated_any)
				ChangeRate(qp, new_rate);
			if (!fast_react){
				if (updated_any){
					qp->hp.m_curRate = new_rate;
					qp->hp.m_incStage = new_incStage;
				}
				if (m_multipleRate){
					// for per hop (per hop R)
					for (uint32_t i = 0; i < ih.nhop; i++){
						if (updated[i]){
							qp->hp.hopState[i].Rc = new_rate_per_hop[i];
							qp->hp.hopState[i].incStage = new_incStage_per_hop[i];
						}
					}
				}
			}
			//HpccMaybeLog(qp, new_rate.GetBitRate() * 1e-9);
		}
		if (!fast_react){
			if (next_seq > qp->hp.m_lastUpdateSeq)
				qp->hp.m_lastUpdateSeq = next_seq; //+ rand() % 2 * m_mtu;
		}
	}
}

void RdmaHw::FastReactHp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
	if (m_fast_react)
		UpdateRateHp(qp, p, ch, true);
	//HpccMaybeLog(qp, new_rate.GetBitRate() * 1e-9);
}

/**********************
 * TIMELY
 *********************/
void RdmaHw::HandleAckTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
	uint32_t ack_seq = ch.ack.seq;
	// update rate
	if (ack_seq > qp->tmly.m_lastUpdateSeq){ // if full RTT feedback is ready, do full update
		UpdateRateTimely(qp, p, ch, false);
	}else{ // do fast react
		FastReactTimely(qp, p, ch);
	}
}
void RdmaHw::UpdateRateTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool us){
	uint32_t next_seq = qp->snd_nxt;
	uint64_t rtt = Simulator::Now().GetTimeStep() - ch.ack.ih.ts;
	bool print = !us;
	if (qp->tmly.m_lastUpdateSeq != 0){ // not first RTT
		int64_t new_rtt_diff = (int64_t)rtt - (int64_t)qp->tmly.lastRtt;
		double rtt_diff = (1 - m_tmly_alpha) * qp->tmly.rttDiff + m_tmly_alpha * new_rtt_diff;
		double gradient = rtt_diff / m_tmly_minRtt;
		bool inc = false;
		double c = 0;
		#if PRINT_LOG
		if (print)
			printf("%lu node:%u rtt:%lu rttDiff:%.0lf gradient:%.3lf rate:%.3lf", Simulator::Now().GetTimeStep(), m_node->GetId(), rtt, rtt_diff, gradient, qp->tmly.m_curRate.GetBitRate() * 1e-9);
		#endif
		if (rtt < m_tmly_TLow){
			inc = true;
		}else if (rtt > m_tmly_THigh){
			c = 1 - m_tmly_beta * (1 - (double)m_tmly_THigh / rtt);
			inc = false;
		}else if (gradient <= 0){
			inc = true;
		}else{
			c = 1 - m_tmly_beta * gradient;
			if (c < 0)
				c = 0;
			inc = false;
		}
		if (inc){
			if (qp->tmly.m_incStage < 5){
				qp->m_rate = qp->tmly.m_curRate + m_rai;
			}else{
				qp->m_rate = qp->tmly.m_curRate + m_rhai;
			}
			if (qp->m_rate > qp->m_max_rate)
				qp->m_rate = qp->m_max_rate;
			if (!us){
				qp->tmly.m_curRate = qp->m_rate;
				qp->tmly.m_incStage++;
				qp->tmly.rttDiff = rtt_diff;
			}
		}else{
			qp->m_rate = std::max(m_minRate, qp->tmly.m_curRate * c); 
			if (!us){
				qp->tmly.m_curRate = qp->m_rate;
				qp->tmly.m_incStage = 0;
				qp->tmly.rttDiff = rtt_diff;
			}
		}
		TimelyMaybeLog(qp, inc ? "INC" : "DEC",
               		qp->m_rate.GetBitRate(),
               		rtt,
               		gradient);
		#if PRINT_LOG
		if (print){
			printf(" %c %.3lf\n", inc? '^':'v', qp->m_rate.GetBitRate() * 1e-9);
		}
		#endif
	}
	if (!us && next_seq > qp->tmly.m_lastUpdateSeq){
		qp->tmly.m_lastUpdateSeq = next_seq;
		// update
		qp->tmly.lastRtt = rtt;
	}
}
void RdmaHw::FastReactTimely(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
}

/**********************
 * DCTCP
 *********************/
void RdmaHw::HandleAckDctcp(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
	uint32_t ack_seq = ch.ack.seq;
	uint8_t cnp = (ch.ack.flags >> qbbHeader::FLAG_CNP) & 1;
	bool new_batch = false;

	// update alpha
	qp->dctcp.m_ecnCnt += (cnp > 0);
	if (ack_seq > qp->dctcp.m_lastUpdateSeq){ // if full RTT feedback is ready, do alpha update
		#if PRINT_LOG
		printf("%lu %s %08x %08x %u %u [%u,%u,%u] %.3lf->", Simulator::Now().GetTimeStep(), "alpha", qp->sip.Get(), qp->dip.Get(), qp->sport, qp->dport, qp->dctcp.m_lastUpdateSeq, ch.ack.seq, qp->snd_nxt, qp->dctcp.m_alpha);
		#endif
		new_batch = true;
		if (qp->dctcp.m_lastUpdateSeq == 0){ // first RTT
			qp->dctcp.m_lastUpdateSeq = qp->snd_nxt;
			qp->dctcp.m_batchSizeOfAlpha = qp->snd_nxt / m_mtu + 1;
		}else {
			double frac = std::min(1.0, double(qp->dctcp.m_ecnCnt) / qp->dctcp.m_batchSizeOfAlpha);
			qp->dctcp.m_alpha = (1 - m_g) * qp->dctcp.m_alpha + m_g * frac;
			qp->dctcp.m_lastUpdateSeq = qp->snd_nxt;
			qp->dctcp.m_ecnCnt = 0;
			qp->dctcp.m_batchSizeOfAlpha = (qp->snd_nxt - ack_seq) / m_mtu + 1;
			#if PRINT_LOG
			printf("%.3lf F:%.3lf", qp->dctcp.m_alpha, frac);
			#endif
		}
		#if PRINT_LOG
		printf("\n");
		#endif
	}

	// check cwr exit
	if (qp->dctcp.m_caState == 1){
		if (ack_seq > qp->dctcp.m_highSeq)
			qp->dctcp.m_caState = 0;
	}

	// check if need to reduce rate: ECN and not in CWR
	if (cnp && qp->dctcp.m_caState == 0){
		#if PRINT_LOG
		printf("%lu %s %08x %08x %u %u %.3lf->", Simulator::Now().GetTimeStep(), "rate", qp->sip.Get(), qp->dip.Get(), qp->sport, qp->dport, qp->m_rate.GetBitRate()*1e-9);
		#endif
		qp->m_rate = std::max(m_minRate, qp->m_rate * (1 - qp->dctcp.m_alpha / 2));
		#if PRINT_LOG
		printf("%.3lf\n", qp->m_rate.GetBitRate() * 1e-9);
		#endif
		qp->dctcp.m_caState = 1;
		qp->dctcp.m_highSeq = qp->snd_nxt;
	}

	// additive inc
	if (qp->dctcp.m_caState == 0 && new_batch)
		qp->m_rate = std::min(qp->m_max_rate, qp->m_rate + m_dctcp_rai);
}

/*********************
 * HPCC-PINT
 ********************/
void RdmaHw::SetPintSmplThresh(double p){
       pint_smpl_thresh = (uint32_t)(65536 * p);
}
void RdmaHw::HandleAckHpPint(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
       uint32_t ack_seq = ch.ack.seq;
       if (rand() % 65536 >= pint_smpl_thresh)
               return;
       // update rate
       if (ack_seq > qp->hpccPint.m_lastUpdateSeq){ // if full RTT feedback is ready, do full update
               UpdateRateHpPint(qp, p, ch, false);
       }else{ // do fast react
               UpdateRateHpPint(qp, p, ch, true);
       }
}

void RdmaHw::UpdateRateHpPint(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch, bool fast_react){
       uint32_t next_seq = qp->snd_nxt;
       if (qp->hpccPint.m_lastUpdateSeq == 0){ // first RTT
               qp->hpccPint.m_lastUpdateSeq = next_seq;
       }else {
               // check packet INT
               IntHeader &ih = ch.ack.ih;
               double U = Pint::decode_u(ih.GetPower());

               DataRate new_rate;
               int32_t new_incStage;
               double max_c = U / m_targetUtil;

               if (max_c >= 1 || qp->hpccPint.m_incStage >= m_miThresh){
                       new_rate = qp->hpccPint.m_curRate / max_c + m_rai;
                       new_incStage = 0;
               }else{
                       new_rate = qp->hpccPint.m_curRate + m_rai;
                       new_incStage = qp->hpccPint.m_incStage+1;
               }
               if (new_rate < m_minRate)
                       new_rate = m_minRate;
               if (new_rate > qp->m_max_rate)
                       new_rate = qp->m_max_rate;
               ChangeRate(qp, new_rate);
               if (!fast_react){
                       qp->hpccPint.m_curRate = new_rate;
                       qp->hpccPint.m_incStage = new_incStage;
               }
               if (!fast_react){
                       if (next_seq > qp->hpccPint.m_lastUpdateSeq)
                               qp->hpccPint.m_lastUpdateSeq = next_seq; //+ rand() % 2 * m_mtu;
               }
       }
}

void RdmaHw::HandleCnpMycc(Ptr<RdmaQueuePair> qp, uint16_t qfb, uint16_t total) {
  	// 累计到发端的窗口计数器
  	qp->mycc.win_cnt += total;
  	qp->mycc.ecn_cnt += qfb;
	printf("%u\n", qfb);
  	// 当累计达到窗口大小（~16包）时，更新 p_est，但不一定立刻改速率
  	while (qp->mycc.win_cnt >= qp->mycc.win_size) {
    		double pHat = (qp->mycc.win_cnt > 0) ? 
                  	(double)qp->mycc.ecn_cnt / (double)qp->mycc.win_cnt : 0.0;
		printf("%.2lf\n", pHat);
    		// EWMA 估计
    		qp->mycc.p_est = m_mycc_ewma * qp->mycc.p_est + (1.0 - m_mycc_ewma) * pHat;
	
    		// 滑窗对齐地“消耗”一窗，保留余量（避免丢精度）
    		qp->mycc.win_cnt -= qp->mycc.win_size;
    		double ratioLeft = (qp->mycc.win_cnt > 0) ? 
                       (double)qp->mycc.win_cnt / (double)(qp->mycc.win_cnt + m_mycc_win) : 0.0;
    		// 这里简单处理：若满窗则清零累计，余量下次继续
    		qp->mycc.ecn_cnt = (qp->mycc.win_cnt == 0) ? 0 : (uint32_t)std::round(qp->mycc.p_est * qp->mycc.win_cnt);
  	}
}

void RdmaHw::HandleAckMycc(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch) {
  	uint32_t ack_seq = ch.ack.seq;
  	// 只有当覆盖到上次发送边界（完整RTT）时做“完整更新”，否则可选快速path
  	bool full = (ack_seq > qp->mycc.m_lastUpdateSeq);
  	UpdateRateMycc(qp, /*fast=*/!full);
}

void RdmaHw::UpdateRateMycc(Ptr<RdmaQueuePair> qp, bool fast) {
  	// 1) 取当前估计的标记率（优先用 p_est；若还没形成估计，可用0作为初始）
  	double p = qp->mycc.p_est;

  	// 2) PI 控制
  	double err = m_mycc_pStar - p;                         // 原逻辑用 pHat；这里用平滑后的 p_est 更稳
	double tmp_integ = qp->mycc.integ + err;
	if (tmp_integ >  m_mycc_integ_cap) tmp_integ =  m_mycc_integ_cap;
	if (tmp_integ < -m_mycc_integ_cap) tmp_integ = -m_mycc_integ_cap;
	qp->mycc.integ = tmp_integ;
  	//qp->mycc.integ = std::clamp(qp->mycc.integ + err, 
        //                      -m_mycc_integ_cap, m_mycc_integ_cap);
  	// 轻微泄放，防积分缠绕
  	qp->mycc.integ *= 0.999;

  	double delta = m_mycc_Kp * err + m_mycc_Ki * qp->mycc.integ; // 无量纲增益
  	double cur_bps = (double)qp->mycc.m_curRate.GetBitRate();
  	double new_bps = cur_bps * (1.0 + delta);

  	// 3) 额外策略：无标记时缓慢探测、重拥塞时快速退
  	if (p <= 1e-9) {
    		new_bps += m_mycc_probe_step;                 // +0.8Gbps
  	} else if (p > m_mycc_severe_th) {
    		new_bps *= m_mycc_severe_mul;                 // *0.70
  	}

  	// 4) 速率边界
  	double min_bps = (double)m_minRate.GetBitRate();
  	double max_bps = (double)qp->m_max_rate.GetBitRate();
  	new_bps = std::min(std::max(new_bps, min_bps), max_bps);
	//std::cout << "init new_bps=" << (new_bps / 1e9) << " bps\n";
  	// 5) 生效（非常重要：用 ChangeRate 同步发送时序）
  	ChangeRate(qp, DataRate((uint64_t)new_bps));

  	// 6) 只在“完整更新”时落盘状态与RTT边界
  	if (!fast) {
    		qp->mycc.m_curRate = DataRate((uint64_t)new_bps);
    		qp->mycc.m_lastUpdateSeq = qp->snd_nxt;
  	}
}


/**********************
 * RTTCC (CcMode = 12)
 *********************/
void RdmaHw::HandleAckRttcc(Ptr<RdmaQueuePair> qp, Ptr<Packet> p, CustomHeader &ch){
  	const uint32_t ack_seq = ch.ack.seq;
  	auto &st = qp->rttcc;
	//std::cout<< "ack:" << ack_seq << std::endl;
  	// RTT 估计：由发送时刻映射回查
  	//auto it = st.tsMap.find(ack_seq);
  	//if (it == st.tsMap.end()) {
    		// 没记录就跳过本次（可能是重传/乱序导致）
    		//return;
  	//}
  	//uint64_t rttNow = (Simulator::Now() - it->second).GetNanoSeconds();
	uint64_t rttNow = Simulator::Now().GetTimeStep() - ch.ack.ih.ts;
  	//st.tsMap.erase(it);
	//std::cout<< "Now:" << Simulator::Now().GetTimeStep() << "     first_time:" << ch.ack.ih.ts << std::endl;

  	st.rttNow = rttNow;
  	if (st.rttLast == 0) st.rttLast = st.rttNow;

  	// EWMA 平滑
  	st.rttNow = (uint64_t)((1.0 - m_rttcc_alpha) * (double)st.rttNow + m_rttcc_alpha * (double)st.rttLast);
  	st.rttDelta = (int64_t)st.rttNow - (int64_t)st.rttLast;
	//std::cout<< "st.rttNow:" << st.rttNow << "      rttLast:" << st.rttLast << std::endl;
  	st.rttLast  = st.rttNow;
  	ns3::Time now = Simulator::Now();
  	int64_t  elapsed_ns = (now - st.recordTimeLast).GetNanoSeconds();
  	if (elapsed_ns <= 0) return;


	uint64_t t_ns = Simulator::Now().GetNanoSeconds();
	st.minRtt.Push(t_ns, rttNow);
	uint64_t baseRtt = st.minRtt.Get();
	//queue delay!!!!!
	uint64_t q = std::max((uint64_t)0, rttNow - baseRtt); //baseRtt
	double alpha = 1.0 - exp(-(double)elapsed_ns / 80000.0); // τ≈80us
	st.qSmooth = (1-alpha)*st.qSmooth + alpha*(double)q;
	if (st.qSmooth > 80000.0) st.qSmooth = 80000.0;
	//double gradient = (st.qSmooth - st.qPrev) / (double)elapsed_ns;
	//if (fabs(gradient) < 0.006) gradient = 0.0;    // 梯度死区
	st.qPrev = st.qSmooth;
	//std::cout<< "st.qSmooth:" << st.qSmooth << std::endl;


  	double gradient = (double)st.rttDelta / (double)elapsed_ns;
	//std::cout<< "st.rttDelta:" << st.rttDelta << "      elapsed_ns:" << elapsed_ns << std::endl;

  	// 总的最小决策间隔
  	if ((uint64_t)elapsed_ns < m_rttcc_baseIntNs) return;

  	// 当前速率（bps）作为整数做运算，最后再包回 DataRate
  	uint64_t cur_bps = st.rateCurrent.GetBitRate();
  	const uint64_t max_bps = qp->m_max_rate.GetBitRate();
  	const uint64_t min_bps = m_minRate.GetBitRate();

	const uint64_t q_low_ns = 300, q_tgt_ns = 5000;
	const uint64_t MAX_UP = 1000000000ULL;     // +1 Gbps/次
	const uint64_t MAX_DOWN_PCT = 20;          // -20%/次

	if (st.qSmooth < q_low_ns && st.cnt < 20 && gradient<=0 && rttNow< m_rttcc_rttLow) {             // FAST
  		if (elapsed_ns < m_rttcc_fastExtraNs && st.cnt > 0) return;
  		uint64_t head = st.rateTarget.GetBitRate() > cur_bps ?
                  	(st.rateTarget.GetBitRate()-cur_bps)/2 : 0;
  		uint64_t step = std::min<uint64_t>(MAX_UP, std::max<uint64_t>(head, 500000000ULL));
  		cur_bps = std::min(max_bps, cur_bps + step);
  		st.cnt++; st.cnt1=st.cnt2=0; st.rateFlag = RdmaQueuePair::RttccState::FAST_INCREASE;
		RttccMaybeLog(qp, "FAST",  cur_bps, st.rttNow, gradient);

	} else if (st.qSmooth > q_tgt_ns || (gradient > 0 && st.rttNow > m_rttcc_rttTarget)) {  // DEC
  		Time guard = NanoSeconds(m_rttcc_decBaseNs + st.cnt1*5000ULL);
  		if ((now - st.recordTimeLast) < guard && st.rateFlag==RdmaQueuePair::RttccState::RTT_DECREASE) return;
  		if (st.rateFlag != RdmaQueuePair::RttccState::RTT_DECREASE) st.rateTarget = st.rateCurrent;

  		//uint64_t cut = std::min<uint64_t>(cur_bps*MAX_DOWN_PCT/100,  // ≤20%
                //    	(uint64_t)(cur_bps*(0.5*((st.qSmooth-q_tgt_ns)/st.qSmooth))));
		uint64_t cut;
		if(st.qSmooth>=q_tgt_ns)  cut = (uint64_t)(cur_bps*(0.5*((st.qSmooth-q_tgt_ns)/st.qSmooth)));
		double frac = 1.0 - 0.5 * ((double)(st.rttNow - m_rttcc_rttTarget) / (double)st.rttNow);
		uint64_t cur_b;
		if(frac>=0) cur_b = (uint64_t)((double)cur_bps * frac);
  		if(st.qSmooth>=q_tgt_ns) cur_bps = std::min(cur_bps-cut,cur_b);
		else if(frac>=0) cur_bps = cur_b;
  		st.cnt=0; st.cnt1++; st.cnt2=0; st.sum=0; st.rateFlag = RdmaQueuePair::RttccState::RTT_DECREASE;
		RttccMaybeLog(qp, "DEC",   cur_bps, st.rttNow, gradient);

	} else {                                                // CONV
  		st.sum++;
  		if (gradient < 0) cur_bps = std::min(max_bps, cur_bps + 100000000UL);
  		else if (gradient > 0) {
    			uint64_t cut = std::min<uint64_t>(cur_bps/10, (uint64_t)(cur_bps*std::min(0.02, gradient*2)));
    			cur_bps -= cut;
  		}
  		st.cnt=0; st.cnt1=0; st.cnt2++; st.rateFlag = RdmaQueuePair::RttccState::CONVERGENCE;
		RttccMaybeLog(qp, "CONV",  cur_bps, st.rttNow, gradient);
	}
	cur_bps = std::max(min_bps, std::min(cur_bps, max_bps));
	ChangeRate(qp, DataRate(cur_bps));
	st.rateCurrent = qp->m_rate;
	st.recordTimeLast = now;
	m_nic[GetNicIdxOfQp(qp)].dev->TriggerTransmit();





/*
  	// ============ 阶段决策 ============
  	if (st.rttNow < m_rttcc_rttLow && st.cnt < 20) {
    		// -------- 快速增长阶段 --------
    		//if ((st.sum % 50) == 0) {               // 你的“每50次一个小步”逻辑
      		//	cur_bps += 500000000ULL;              // +0.5 Gbps
      		//	st.sum = 0;
      			// 限幅
      		//	if (cur_bps > max_bps) cur_bps = max_bps;
    		//} 
		{
      			// 额外护栏（对应 18us）
      			if ((uint64_t)elapsed_ns < m_rttcc_fastExtraNs && st.cnt > 0) {
        			//st.recordTimeLast = now;
        			return;
      			}
      			// 重新拉高目标/重置计数（与原代码等价）
      			if (st.cnt >= 8 || st.rateTarget + 5000000000ULL < st.rateCurrent) {
        			st.rateTarget = qp->m_max_rate;
        			st.cnt = 0;
      			}
      			if (st.cnt == 0) {
        			// 第一次：二分靠近目标
        			uint64_t tgt = st.rateTarget.GetBitRate();
        			cur_bps = cur_bps + (tgt > cur_bps ? (tgt - cur_bps)/2 : 0);
      			} else {
        			cur_bps += 2000000000ULL;           // +2 Gbps
      			}
      			if (cur_bps > max_bps) cur_bps = max_bps;
      			st.cnt++;
    		}
    		st.cnt1 = 0; st.cnt2 = 0; st.sum++;
    		st.rateFlag = RdmaQueuePair::RttccState::FAST_INCREASE;
		RttccMaybeLog(qp, "FAST",  cur_bps, st.rttNow, gradient);

  	} else if (st.rttNow > m_rttcc_rttTarget) {
    		// -------- 拥塞避免（快速降速）--------
    		uint64_t guard_ns = m_rttcc_decBaseNs + (uint64_t)st.cnt1 * 5000ULL;
    		if ((uint64_t)elapsed_ns < guard_ns && st.rateFlag == RdmaQueuePair::RttccState::RTT_DECREASE) {
      			//st.recordTimeLast = now;
      			return;
    		}

    		// 切换到该阶段时冻结目标
    		if (st.rateFlag == RdmaQueuePair::RttccState::FAST_INCREASE || st.rateFlag == RdmaQueuePair::RttccState::CONVERGENCE) {
      			st.rateTarget = st.rateCurrent;
    		}
    		if (st.rateFlag == RdmaQueuePair::RttccState::CONVERGENCE && st.cnt1 > 0) {
      			cur_bps = (uint64_t)((double)cur_bps * 0.9); // 额外 10% 切
    		}

    		// 自适应降速（与原式一致）
    		double factor;
    		if (st.cnt1 < 5) {
      			// max(0.5, 1 - 0.5*(rttNow-rttTarget)/rttNow)
      			double frac = 1.0 - 0.5 * ((double)(st.rttNow - m_rttcc_rttTarget) / (double)st.rttNow);
      			if (frac < 0.5) frac = 0.5;
      			factor = frac;
    		} else {
      			factor = 0.92; // 略缓降
    		}
    		cur_bps = (uint64_t)((double)cur_bps * factor);
		RttccMaybeLog(qp, "DEC",   cur_bps, st.rttNow, gradient);

    		st.cnt = 0; st.cnt1++; st.cnt2 = 0; st.sum = 0;
    		st.rateFlag = RdmaQueuePair::RttccState::RTT_DECREASE;

  	} else {
    		// -------- 收敛阶段（梯度微调）--------
    		uint64_t base = m_rttcc_cvgBaseNs + (uint64_t)st.sum * 50ULL;
    		if ((uint64_t)elapsed_ns < base && st.sum > 12) {
      			//st.recordTimeLast = now;
      			return;
    		}
    		st.sum++;
    		if (gradient < 0) {
      			cur_bps += 100000000ULL; // 负梯度时给一点 +0.1Gbps
    		}
    		st.cnt1 = 0;

    		double rateLine = (double)m_rttcc_rateLine.GetBitRate();
    		if (gradient < 0.025 && gradient > 0) {
      			// 轻微正梯度：温和乘性缩小
      			cur_bps = (uint64_t)((double)cur_bps * (1.0 - gradient*2));
    		} else if (gradient > -0.025 && gradient < 0) {
      			// 轻微负梯度：线性微增（你的公式）
      			double delta = m_rttcc_rateLine.GetBitRate() * (-gradient*2) * (1.0 - (double)cur_bps / rateLine);
      			cur_bps += (uint64_t)delta;
    		}

    		if (cur_bps > max_bps) cur_bps = max_bps;
		RttccMaybeLog(qp, "CONV",  cur_bps, st.rttNow, gradient);
    		st.rateFlag = RdmaQueuePair::RttccState::CONVERGENCE;
    		st.cnt = 0; st.cnt2++;
  	}

  	// 低 RTT 且几乎无排队时的小幅探测步
  	if (st.rttNow < m_rttcc_rttLow && st.cnt == 0) {
   		//cur_bps = std::min(max_bps, cur_bps + (uint64_t)m_rttcc_probe_step);
  	}

  	// 边界并下发
  	if (cur_bps < min_bps) cur_bps = min_bps;
  	ns3::DataRate newR(cur_bps);
  	ChangeRate(qp, newR);
  	st.rateCurrent = qp->m_rate;
	//std::cout << "init new_bps=" << (st.rateCurrent / 1e9) << " Gbps\n";

  	// 推进时间与触发发送
  	st.recordTimeLast = now;
  	uint32_t nic_idx = GetNicIdxOfQp(qp);
  	m_nic[nic_idx].dev->TriggerTransmit();

*/
}




}
