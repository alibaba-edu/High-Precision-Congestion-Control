/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
* Copyright (c) 2006 Georgia Tech Research Corporation, INRIA
*
* This program is free software; you can redistribute it and/or modify
* it under the terms of the GNU General Public License version 2 as
* published by the Free Software Foundation;
*
* This program is distributed in the hope that it will be useful,
* but WITHOUT ANY WARRANTY; without even the implied warranty of
* MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License
* along with this program; if not, write to the Free Software
* Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*
* Author: Yibo Zhu <yibzh@microsoft.com>
*/
#ifndef QBB_NET_DEVICE_H
#define QBB_NET_DEVICE_H

#include "ns3/point-to-point-net-device.h"
#include "ns3/broadcom-node.h"
#include "ns3/qbb-channel.h"
//#include "ns3/fivetuple.h"
#include "ns3/event-id.h"
#include "ns3/broadcom-egress-queue.h"
#include "ns3/ipv4.h"
#include "ns3/ipv4-header.h"
#include "ns3/udp-header.h"
#include <vector>
#include<map>

namespace ns3 {

/**
 * \class QbbNetDevice
 * \brief A Device for a IEEE 802.1Qbb Network Link.
 */
class QbbNetDevice : public PointToPointNetDevice 
{
public:
  static const uint32_t qCnt = 8;	// Number of queues/priorities used
  static const uint32_t pCnt = 64;	// Number of ports used
  static const uint32_t fCnt = 128; // Max number of flows on a NIC, for TX and RX respectively. TX+RX=fCnt*2
  static const uint32_t maxHop = 1; // Max hop count in the network. should not exceed 16 

  static TypeId GetTypeId (void);

  QbbNetDevice ();
  virtual ~QbbNetDevice ();

  /**
   * Receive a packet from a connected PointToPointChannel.
   *
   * This is to intercept the same call from the PointToPointNetDevice
   * so that the pause messages are honoured without letting
   * PointToPointNetDevice::Receive(p) know
   *
   * @see PointToPointNetDevice
   * @param p Ptr to the received packet.
   */
  virtual void Receive (Ptr<Packet> p);

  /**
   * Send a packet to the channel by putting it to the queue
   * of the corresponding priority class
   *
   * @param packet Ptr to the packet to send
   * @param dest Unused
   * @param protocolNumber Protocol used in packet
   */
  virtual bool Send(Ptr<Packet> packet, const Address &dest, uint16_t protocolNumber);

  /**
   * Get the size of Tx buffer available in the device
   *
   * @return buffer available in bytes
   */
  //virtual uint32_t GetTxAvailable(unsigned) const;

  /**
   * TracedCallback hooks
   */
  void ConnectWithoutContext(const CallbackBase& callback);
  void DisconnectWithoutContext(const CallbackBase& callback);

  virtual int32_t PrintStatus(std::ostream& os);

  bool Attach (Ptr<QbbChannel> ch);
  
  uint32_t GetPriority(Ptr<Packet> p);
  uint32_t GetSeq(Ptr<Packet> p);
  //uint16_t GetPort(Ptr<Packet> p);
  //uint32_t GetQbbPriority(Ptr<Packet> p);

   void SetBroadcomParams(
	    uint32_t pausetime,
		double qcn_interval,
		double qcn_resume_interval,
		double g,
		DataRate minRate,
		DataRate rai,
		uint32_t m_fastrecover_times
	   );

   virtual Ptr<Channel> GetChannel (void) const;

   virtual uint32_t GetUsedBuffer(uint32_t port, uint32_t qIndex);

   void SetQueue (Ptr<BEgressQueue> q);
   Ptr<BEgressQueue> GetQueue ();

protected:

	//Ptr<Node> m_node;

  bool TransmitStart (Ptr<Packet> p);
  
  Address GetRemote (void) const;
  
  void PointToPointReceive (Ptr<Packet> packet);

  virtual void DoDispose(void);

  /// Reset the channel into READY state and try transmit again
  virtual void TransmitComplete(void);

  /// Look for an available packet and send it using TransmitStart(p)
  virtual void DequeueAndTransmit(void);

  /// Resume a paused queue and call DequeueAndTransmit()
  virtual void Resume(unsigned qIndex);

  /// Wrapper to Resume() as an schedulable function
  void PauseFinish(unsigned qIndex);


  /**
   * Function to generate PAUSE message if necessary
   *
   */
  void CheckQueueFull(uint32_t, uint32_t);

  /// Tell if an address is local to this node
  bool IsLocal(const Ipv4Address& addr) const;

  /**
   * The queues for each priority class.
   * @see class Queue
   * @see class InfiniteQueue
   */
  Ptr<BEgressQueue> m_queue;

  TracedCallback<Ptr<NetDevice>, uint32_t> m_sendCb;	//< Callback chain for notifying Tx buffer available

  Ptr<QbbChannel> m_channel;
  
  //pfc
  bool m_qbbEnabled;	//< PFC behaviour enabled
  bool m_qcnEnabled;
  bool m_dynamicth;
  //uint32_t m_threshold;	//< Threshold for generating Pause
  uint32_t m_pausetime;	//< Time for each Pause
  //uint32_t m_buffersize;//< Total size of Tx buffer
  //uint32_t m_bufferUsage;	//< Occupancy at the buffer
  bool m_paused[qCnt];	//< Whether a queue paused
  EventId m_resumeEvt[qCnt];  //< Keeping the next resume event (PFC)
  EventId m_recheckEvt[pCnt][qCnt]; //< Keeping the next recheck queue full event (PFC)

  //qcn

  //cp
  //uint8_t ShouldSendCN(uint32_t qIndex, uint32_t pktSize);
  bool ShouldSendCN(uint32_t indev, uint32_t ifindex, uint32_t qIndex);
  uint32_t m_qeq;
  uint32_t m_speedup;
  double m_w;
  //int32_t m_qOld[fCnt];
  //int32_t m_timeToMark[fCnt];

  //void AveragingPrinciple(unsigned qIndex);
  
  //void RateIncrease(unsigned qIndex);
  void ResumeAlpha(uint32_t fIndex, uint32_t hop);
  EventId m_resumeAlpha[fCnt][maxHop];

  void AdjustRates(uint32_t fIndex, uint32_t hop, DataRate increase);
  void rpr_adjust_rates(uint32_t fIndex, uint32_t hop);
  void rpr_fast_recovery(uint32_t fIndex, uint32_t hop);
  void rpr_active_increase(uint32_t fIndex, uint32_t hop);
  void rpr_active_byte(uint32_t findex, uint32_t hop);
  void rpr_active_time(uint32_t findex, uint32_t hop);
  void rpr_fast_byte(uint32_t findex, uint32_t hop);
  void rpr_fast_time(uint32_t findex, uint32_t hop);
  void rpr_hyper_byte(uint32_t findex, uint32_t hop);
  void rpr_hyper_time(uint32_t findex, uint32_t hop);
  void rpr_active_select(uint32_t findex, uint32_t hop);
  void rpr_hyper_increase(uint32_t findex, uint32_t hop);
  void rpr_cnm_received(uint32_t findex, uint32_t hop, double fraction);

  void rpr_timer_wrapper(uint32_t fIndex, uint32_t hop);
  EventId m_rptimer[fCnt][maxHop];

  bool m_EcnClampTgtRateAfterTimeInc;
  bool m_EcnClampTgtRate;


  /* RP parameters */
  //double   m_gd;		//< Control gain param for rate decrease
  //double   m_minDec;		//< Min decrease ratio
  DataRate m_minRate;		//< Min sending rate
  uint32_t m_bc;		//< Tx byte counter timeout threshold
  DataRate m_rai;		//< Rate of additive increase
  DataRate m_rhai;		//< Rate of hyper-additive increase
  EventId  m_nextSend;		//< The next send event
  uint32_t m_rpgThreshold;
  /* State variable for rate-limited queues */

  DataRate m_rateAll[fCnt][maxHop];

  DataRate m_targetRate[fCnt][maxHop];	//< Target rate
  //DataRate m_lastRate[fCnt];	//< Target rate
  DataRate m_rate[fCnt];	//< Current rate
  int64_t  m_txBytes[fCnt][maxHop];	//< Tx byte counter
  double  m_rpWhile[fCnt][maxHop];	//< Tx byte counter
  uint32_t m_rpByteStage[fCnt][maxHop];	//< Count of Tx-based rate increments
  uint32_t m_rpTimeStage[fCnt][maxHop];

  uint32_t m_rpStage[fCnt][maxHop]; //1: fr; 2: ai; 3: hi

  //uint32_t m_timeCount[fCnt][maxHop];	//< Count of timer-based rate increments
  //Time     m_timer[qCnt];	//< Time to next self-increment
  Time     m_nextAvail[fCnt];	//< Soonest time of next send
  double   m_credits[fCnt];	//< Credits accumulated
  EventId m_rateIncrease[fCnt]; // rate increase event (QCN)

  //bool m_extraFastRecovery[fCnt][maxHop]; //false means this is the first time receive CNP
  
  double m_qcn_np_sampling_interval;
  double m_qcn_np_sampling;

  //qcn

  struct ECNAccount{
	  Ipv4Address source;
	  uint32_t qIndex;
	  uint32_t port;
	  uint8_t ecnbits;
	  uint16_t qfb;
	  uint16_t total;
  };

  std::vector<ECNAccount> *m_ecn_source;
  //uint32_t m_ecn_count;
  double m_qcn_interval;
  double m_alpha[fCnt][maxHop];
  double m_g; //feedback weight
  double m_rpgTimeReset;
  double m_alpha_resume_interval;
  //uint32_t m_fastrecover_times;

  //Time m_lastpause[qCnt]; //For adding back credits..

  uint32_t m_findex_udpport_map[fCnt];
  uint32_t m_findex_qindex_map[fCnt];

  void CheckandSendQCN(Ipv4Address source, uint32_t qIndex, uint32_t port);


  void ResumeECNState(uint32_t inDev);
  void ResumeECNIngressState(uint32_t inDev);
  void ResumeECNEgressState(uint32_t inDev);

  EventId m_ECNStateEvent[pCnt];
  EventId m_ECNIngressStateEvent[pCnt];
  EventId m_ECNEgressStateEvent[pCnt];

  uint32_t m_ECNState[pCnt]; //0 means no state, 1 means ingress, 2 means egress
  uint32_t m_ECNIngressCount[pCnt];
  uint32_t m_ECNEgressCount[pCnt];


  // Methods and members related to NACK functionality. 

  //void CreateFiveTupleKey(Ptr<Packet> packet, char *fiveTuple);
  //void CreateFiveTupleKey(Ipv4Header iph, UdpHeader udph, char *fiveTuple);

  //int ReceiverCheckSeq(Ipv4Header iph, UdpHeader udph, int seq, std::string &found_key);
  //int ReceiverGetNextSeq(Ptr<Packet> packet);
  //void ReceiverSendNACK(Ptr<Packet> packet);

  //void SenderAddQbbHeader(Ptr<Packet> packet);
  //int SenderGetNextSeq(Ptr<Packet> packet);
 // void ProcessNACK(Ptr<Packet> packet);
  //void SenderAddQbbHeader(Ptr<Packet> p, uint32_t qIndex);
  //void ReceiverRemoveQbbHeader(Ptr<Packet> p);

  //std::map<std::string, int> SenderNextSeq;
  //std::map<std::string, int> ReceiverNextExpectedSeq;
  //nack
  //std::map<std::string, Time> m_nackTimer;
  //std::map<std::string, int32_t> m_lastNACK;
  //uint32_t SenderNextSeq[fCnt];
  //std::map<std::string, int32_t> m_milestone;


  int ReceiverCheckSeq(uint32_t seq, uint32_t key);
  void Retransmit(uint32_t findex);
  double m_nack_interval;
  double m_waitAckTimer;
  Ptr<DropTailQueue> m_sendingBuffer[fCnt];
  uint32_t m_chunk;
  uint32_t m_ack_interval;
  uint32_t ReceiverNextExpectedSeq[fCnt];
  Time m_nackTimer[fCnt];
  uint32_t m_lastNACK[fCnt];
  int32_t m_milestone_rx[fCnt];
  bool m_waitAck;
  bool m_backto0;
  bool m_testRead;
  int32_t m_milestone_tx[fCnt];
  EventId m_retransmit[fCnt];
  bool m_waitingAck[fCnt];

};

} // namespace ns3

#endif // QBB_NET_DEVICE_H

