#include "int-header.h"

namespace ns3 {

const uint64_t IntHop::lineRateValues[8] = {25000000000lu,50000000000lu,100000000000lu,200000000000lu,400000000000lu,0,0,0};
uint32_t IntHop::multi = 1;

uint32_t IntHeader::mode = 0;

IntHeader::IntHeader() : nhop(0) {
	for (uint32_t i = 0; i < maxHop; i++)
		hop[i] = {0};
}

uint32_t IntHeader::GetStaticSize(){
	if (mode == 0){
		return sizeof(hop) + sizeof(nhop);
	}else if (mode == 1){
		return sizeof(ts);
	}else {
		return 0;
	}
}

void IntHeader::PushHop(uint64_t time, uint64_t bytes, uint32_t qlen, uint64_t rate){
	// only do this in INT mode
	if (mode == 0){
		uint32_t idx = nhop % maxHop;
		hop[idx].Set(time, bytes, qlen, rate);
		nhop++;
	}
}

void IntHeader::Serialize (Buffer::Iterator start) const{
	Buffer::Iterator i = start;
	if (mode == 0){
		for (uint32_t j = 0; j < maxHop; j++){
			i.WriteU32(hop[j].buf[0]);
			i.WriteU32(hop[j].buf[1]);
		}
		i.WriteU16(nhop);
	}else if (mode == 1){
		i.WriteU64(ts);
	}
}

uint32_t IntHeader::Deserialize (Buffer::Iterator start){
	Buffer::Iterator i = start;
	if (mode == 0){
		for (uint32_t j = 0; j < maxHop; j++){
			hop[j].buf[0] = i.ReadU32();
			hop[j].buf[1] = i.ReadU32();
		}
		nhop = i.ReadU16();
	}else if (mode == 1){
		ts = i.ReadU64();
	}
	return GetStaticSize();
}

uint64_t IntHeader::GetTs(void){
	if (mode == 1)
		return ts;
	return 0;
}

}
