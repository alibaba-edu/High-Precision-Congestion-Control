#include "rdma-ingress-queue.h"
#include "ns3/uinteger.h"

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED(RdmaIngressQueue);

TypeId RdmaIngressQueue::GetTypeId (void)
{
	static TypeId tid = TypeId("ns3::RdmaIngressQueue")
		.SetParent<Object>()
		.AddAttribute("MaxBytes",
			"Maximum bytes allowed in the NIC RX buffer (total).",
			UintegerValue(8 * 1024 * 1024),
			MakeUintegerAccessor(&RdmaIngressQueue::m_maxBytes),
			MakeUintegerChecker<uint64_t>())
		.AddAttribute("MaxBytesPerQueue",
			"Maximum bytes allowed per priority queue (0 means no per-queue cap).",
			UintegerValue(0),
			MakeUintegerAccessor(&RdmaIngressQueue::m_maxBytesPerQueue),
			MakeUintegerChecker<uint64_t>())
		.AddTraceSource("RdmaIngressBytes",
			"Total bytes in NIC RX buffer.",
			MakeTraceSourceAccessor(&RdmaIngressQueue::m_traceTotalBytes))
		;
	return tid;
}

RdmaIngressQueue::RdmaIngressQueue()
	: m_totalBytes(0),
	  m_maxBytes(8 * 1024 * 1024),
	  m_maxBytesPerQueue(0),
	  m_rrLast(0)
{
	for (uint32_t i = 0; i < qCnt; i++){
		m_q[i] = CreateObject<DropTailQueue>();
		m_q[i]->SetAttribute("MaxBytes", UintegerValue(0xffffffff));
		m_qBytes[i] = 0;
	}
	m_traceTotalBytes = 0;
}

bool RdmaIngressQueue::Enqueue(Ptr<Packet> p, uint32_t qIndex)
{
	if (qIndex >= qCnt || p == 0)
		return false;

	uint32_t size = p->GetSize();
	if (m_maxBytes > 0 && m_totalBytes + size > m_maxBytes)
		return false;
	if (m_maxBytesPerQueue > 0 && m_qBytes[qIndex] + size > m_maxBytesPerQueue)
		return false;

	m_q[qIndex]->Enqueue(p);
	m_qBytes[qIndex] += size;
	m_totalBytes += size;
	m_traceTotalBytes = m_totalBytes;
	return true;
}

Ptr<Packet> RdmaIngressQueue::Dequeue(uint32_t &qIndex)
{
	for (uint32_t i = 0; i < qCnt; i++){
		uint32_t idx = (m_rrLast + i + 1) % qCnt;
		if (m_q[idx]->GetNPackets() > 0){
			Ptr<Packet> p = m_q[idx]->Dequeue();
			if (p != 0){
				uint32_t size = p->GetSize();
				m_qBytes[idx] -= size;
				m_totalBytes -= size;
				m_traceTotalBytes = m_totalBytes;
				m_rrLast = idx;
				qIndex = idx;
				return p;
			}
		}
	}
	return 0;
}

bool RdmaIngressQueue::IsEmpty() const
{
	return m_totalBytes == 0;
}

uint64_t RdmaIngressQueue::GetNBytesTotal() const
{
	return m_totalBytes;
}

uint64_t RdmaIngressQueue::GetNBytes(uint32_t qIndex) const
{
	if (qIndex >= qCnt)
		return 0;
	return m_qBytes[qIndex];
}

uint64_t RdmaIngressQueue::GetMaxBytes() const
{
	return m_maxBytes;
}

uint64_t RdmaIngressQueue::GetMaxBytesPerQueue() const
{
	return m_maxBytesPerQueue;
}

void RdmaIngressQueue::SetMaxBytes(uint64_t bytes)
{
	m_maxBytes = bytes;
}

void RdmaIngressQueue::SetMaxBytesPerQueue(uint64_t bytes)
{
	m_maxBytesPerQueue = bytes;
}

} // namespace ns3
