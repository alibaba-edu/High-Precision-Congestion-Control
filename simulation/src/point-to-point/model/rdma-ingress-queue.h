#ifndef RDMA_INGRESS_QUEUE_H
#define RDMA_INGRESS_QUEUE_H

#include "ns3/object.h"
#include "ns3/ptr.h"
#include "ns3/packet.h"
#include "ns3/drop-tail-queue.h"
#include "ns3/traced-value.h"

namespace ns3 {

class RdmaIngressQueue : public Object {
public:
	static const uint32_t qCnt = 8;
	static TypeId GetTypeId (void);

	RdmaIngressQueue();

	bool Enqueue(Ptr<Packet> p, uint32_t qIndex);
	Ptr<Packet> Dequeue(uint32_t &qIndex);
	bool IsEmpty() const;

	uint64_t GetNBytesTotal() const;
	uint64_t GetNBytes(uint32_t qIndex) const;
	uint64_t GetMaxBytes() const;
	uint64_t GetMaxBytesPerQueue() const;

	void SetMaxBytes(uint64_t bytes);
	void SetMaxBytesPerQueue(uint64_t bytes);

private:
	Ptr<DropTailQueue> m_q[qCnt];
	uint64_t m_qBytes[qCnt];
	uint64_t m_totalBytes;
	uint64_t m_maxBytes;
	uint64_t m_maxBytesPerQueue;
	uint32_t m_rrLast;

	TracedValue<uint64_t> m_traceTotalBytes;
};

} // namespace ns3

#endif // RDMA_INGRESS_QUEUE_H
