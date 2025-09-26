#ifndef RDMA_QUEUE_PAIR_H
#define RDMA_QUEUE_PAIR_H

#include <ns3/object.h>
#include <ns3/packet.h>
#include <ns3/ipv4-address.h>
#include <ns3/data-rate.h>
#include <ns3/event-id.h>
#include <ns3/custom-header.h>
#include <ns3/int-header.h>
#include <vector>
#include <unordered_map>
#include <deque>
#include <utility>

namespace ns3 {

class RdmaQueuePair : public Object {
public:
	Time startTime;
	Ipv4Address sip, dip;
	uint16_t sport, dport;
	uint64_t m_size;
	uint64_t snd_nxt, snd_una; // next seq to send, the highest unacked seq
	uint16_t m_pg;
	uint16_t m_ipid;
	uint32_t m_win; // bound of on-the-fly packets
	uint64_t m_baseRtt; // base RTT of this qp
	DataRate m_max_rate; // max rate
	bool m_var_win; // variable window size
	Time m_nextAvail;	//< Soonest time of next send
	uint32_t wp; // current window of packets
	uint32_t lastPktSize;
	Callback<void> m_notifyAppFinish;

	// ==== debug throughput window ====
	uint64_t dbg_bytes_win = 0;
	ns3::Time dbg_win_start;          // default 0
	FILE*    dbg_tp_fp = nullptr;     

	/******************************
	 * runtime states
	 *****************************/
	DataRate m_rate;	//< Current rate
	struct {
		DataRate m_targetRate;	//< Target rate
		EventId m_eventUpdateAlpha;
		double m_alpha;
		bool m_alpha_cnp_arrived; // indicate if CNP arrived in the last slot
		bool m_first_cnp; // indicate if the current CNP is the first CNP
		EventId m_eventDecreaseRate;
		bool m_decrease_cnp_arrived; // indicate if CNP arrived in the last slot
		uint32_t m_rpTimeStage;
		EventId m_rpTimer;
	} mlx;
	struct {
		uint32_t m_lastUpdateSeq;
		DataRate m_curRate;
		IntHop hop[IntHeader::maxHop];
		uint32_t keep[IntHeader::maxHop];
		uint32_t m_incStage;
		double m_lastGap;
		double u;
		struct {
			double u;
			DataRate Rc;
			uint32_t incStage;
		}hopState[IntHeader::maxHop];
	} hp;
	struct{
		uint32_t m_lastUpdateSeq;
		DataRate m_curRate;
		uint32_t m_incStage;
		uint64_t lastRtt;
		double rttDiff;
	} tmly;
	struct{
		uint32_t m_lastUpdateSeq;
		uint32_t m_caState;
		uint32_t m_highSeq; // when to exit cwr
		double m_alpha;
		uint32_t m_ecnCnt;
		uint32_t m_batchSizeOfAlpha;
	} dctcp;
	struct{
		uint32_t m_lastUpdateSeq;
		DataRate m_curRate;
		uint32_t m_incStage;
	}hpccPint;
	struct {
  		DataRate m_curRate;         // 记录上一次“生效”的速率
  		uint32_t m_lastUpdateSeq{0}; // 上一次完整RTT更新的边界（用 snd_nxt 语义）
  		// ECN滑窗统计
  		uint32_t win_size{16};       // 你的 16 包窗口
  		uint32_t win_cnt{0};         // 已累计总包数
  		uint32_t ecn_cnt{0};         // 已累计ECN标记包数
  		// 估计与PI
  		double p_est{0.0};           // EWMA后的标记率估计
  		double integ{0.0};           // PI积分项
	} mycc;
	struct RttccState {
  		// RTT 估计
  		uint64_t rttNow = 0;      // ns
  		uint64_t rttLast = 0;     // ns
  		int64_t rttDelta = 0;    // ns
  		std::unordered_map<uint32_t, ns3::Time> tsMap; // seq -> send time

		uint64_t qSmooth;
		uint64_t qPrev;

  		// 速率状态
  		ns3::DataRate rateCurrent;   // 当前速率（与 qp->m_rate 保持一致）
  		ns3::DataRate rateTarget;    // 快速增长阶段的目标速率上限（一般 = m_max_rate）

  		// 阶段/计数
  		enum RateState { FAST_INCREASE, RTT_DECREASE, CONVERGENCE } rateFlag = CONVERGENCE;
  		uint32_t cnt  = 0;     // 快增计数 m_cnt
  		uint32_t cnt1 = 0;     // 降速计数 m_cnt1
  		uint32_t cnt2 = 0;     // 收敛计数 m_cnt2
  		uint32_t sum  = 0;     // 你的逻辑里用于节流的计数器

  		// 定时
  		ns3::Time recordTimeLast;    // 上一次决策时刻
		ns3::Time  lastLogTime;   // 上次写日志的时间
		uint64_t   lastLogBps = 0;
		
		
		struct MonotonicMinRtt {
			uint64_t window_ns;  // 滑动窗大小
			std::deque<std::pair<uint64_t,uint64_t> > all;   // (t_ns, rtt_ns)
			std::deque<std::pair<uint64_t,uint64_t> > mono;  // 单调队列(候选最小)

			MonotonicMinRtt(uint64_t w=1000000ULL) : window_ns(w) {} // 默认 5 ms
			void SetWindow(uint64_t w) { window_ns = w; }

			void Push(uint64_t t_ns, uint64_t rtt_ns) {
				uint64_t cutoff = (t_ns > window_ns) ? (t_ns - window_ns) : 0;

				// 过窗清理
				while (!all.empty() && all.front().first < cutoff) {
					if (!mono.empty() && mono.front().first == all.front().first) {
						mono.pop_front();
					}
					all.pop_front();
				}

				// 新样本入队
				all.push_back(std::make_pair(t_ns, rtt_ns));
				while (!mono.empty() && mono.back().second >= rtt_ns) {
					mono.pop_back();
				}
				mono.push_back(std::make_pair(t_ns, rtt_ns));
			}

			uint64_t Get() const {
				return mono.empty() ? 0 : mono.front().second;   // 没有样本时返回 0
			}
		}minRtt;

	}rttcc;

	/***********
	 * methods
	 **********/
	static TypeId GetTypeId (void);
	RdmaQueuePair(uint16_t pg, Ipv4Address _sip, Ipv4Address _dip, uint16_t _sport, uint16_t _dport);
	void SetSize(uint64_t size);
	void SetWin(uint32_t win);
	void SetBaseRtt(uint64_t baseRtt);
	void SetVarWin(bool v);
	void SetAppNotifyCallback(Callback<void> notifyAppFinish);

	uint64_t GetBytesLeft();
	uint32_t GetHash(void);
	void Acknowledge(uint64_t ack);
	uint64_t GetOnTheFly();
	bool IsWinBound();
	uint64_t GetWin(); // window size calculated from m_rate
	bool IsFinished();
	uint64_t HpGetCurWin(); // window size calculated from hp.m_curRate, used by HPCC
};

class RdmaRxQueuePair : public Object { // Rx side queue pair
public:
	struct ECNAccount{
		uint16_t qIndex;
		uint8_t ecnbits;
		uint16_t qfb;
		uint16_t total;

		ECNAccount() { memset(this, 0, sizeof(ECNAccount));}
	};
	ECNAccount m_ecn_source;
	uint32_t sip, dip;
	uint16_t sport, dport;
	uint16_t m_ipid;
	uint32_t ReceiverNextExpectedSeq;
	Time m_nackTimer;
	int32_t m_milestone_rx;
	uint32_t m_lastNACK;
	EventId QcnTimerEvent; // if destroy this rxQp, remember to cancel this timer

	static TypeId GetTypeId (void);
	RdmaRxQueuePair();
	uint32_t GetHash(void);
};

class RdmaQueuePairGroup : public Object {
public:
	std::vector<Ptr<RdmaQueuePair> > m_qps;
	//std::vector<Ptr<RdmaRxQueuePair> > m_rxQps;

	static TypeId GetTypeId (void);
	RdmaQueuePairGroup(void);
	uint32_t GetN(void);
	Ptr<RdmaQueuePair> Get(uint32_t idx);
	Ptr<RdmaQueuePair> operator[](uint32_t idx);
	void AddQp(Ptr<RdmaQueuePair> qp);
	//void AddRxQp(Ptr<RdmaRxQueuePair> rxQp);
	void Clear(void);
};

}

#endif /* RDMA_QUEUE_PAIR_H */
