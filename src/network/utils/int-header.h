#ifndef INT_HEADER_H
#define INT_HEADER_H

#include "ns3/buffer.h"
#include <stdint.h>
#include <cstdio>

namespace ns3 {

class IntHop{
public:
	static const uint32_t timeWidth = 24;
	static const uint32_t bytesWidth = 20;
	static const uint32_t qlenWidth = 17;
	static const uint64_t lineRateValues[8];
	union{
		struct {
			uint64_t lineRate: 64-timeWidth-bytesWidth-qlenWidth,
					 time: timeWidth,
					 bytes: bytesWidth,
					 qlen: qlenWidth;
			#if 0
			uint32_t lineRate:32-timeWidth,
					 time: timeWidth;
			uint32_t bytes: bytesWidth,
					 qlen: 32-bytesWidth;
			#endif
		};
		uint32_t buf[2];
	};

	static const uint32_t byteUnit = 128;
	static const uint32_t qlenUnit = 80;
	static uint32_t multi;

	uint64_t GetLineRate(){
		return lineRateValues[lineRate];
	}
	uint64_t GetBytes(){
		return (uint64_t)bytes * byteUnit * multi;
	}
	uint32_t GetQlen(){
		return (uint32_t)qlen * qlenUnit * multi;
	}
	uint64_t GetTime(){
		return time;
	}
	void Set(uint64_t _time, uint64_t _bytes, uint32_t _qlen, uint64_t _rate){
		time = _time;
		bytes = _bytes / (byteUnit * multi);
		qlen = _qlen / (qlenUnit * multi);
		switch (_rate){
			case 25000000000lu:
				lineRate=0;break;
			case 50000000000lu:
				lineRate=1;break;
			case 100000000000lu:
				lineRate=2;break;
			case 200000000000lu:
				lineRate=3;break;
			case 400000000000lu:
				lineRate=4;break;
			default:
				printf("Error: IntHeader unknown rate: %lu\n", _rate);
				break;
		}
	}
	uint64_t GetBytesDelta(IntHop &b){
		if (bytes >= b.bytes)
			return (bytes - b.bytes) * byteUnit * multi;
		else
			return (bytes + (1<<bytesWidth) - b.bytes) * byteUnit * multi;
	}
	uint64_t GetTimeDelta(IntHop &b){
		if (time >= b.time)
			return time - b.time;
		else
			return time + (1<<timeWidth) - b.time;
	}
};

class IntHeader{
public:
	static const uint32_t maxHop = 5;
	static uint32_t mode; // 0: INT, 1: ts, 5:0

	// Note: the structure of IntHeader must have no internal padding, because we will directly transform the part of packet buffer to IntHeader*
	union{
		struct {
			IntHop hop[maxHop];
			uint16_t nhop;
		};
		uint64_t ts;
	};

	IntHeader();
	static uint32_t GetStaticSize();
	void PushHop(uint64_t time, uint64_t bytes, uint32_t qlen, uint64_t rate);
	void Serialize (Buffer::Iterator start) const;
	uint32_t Deserialize (Buffer::Iterator start);
	uint64_t GetTs(void);
};

}

#endif /* INT_HEADER_H */
