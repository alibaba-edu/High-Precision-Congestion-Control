/* -*-  Mode: C++; c-file-style: "gnu"; indent-tabs-mode:nil; -*- */
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License version 2 as
// published by the Free Software Foundation;
//
// Author: Baltzis Petros<mpaltzis@ceid.upatras.gr>

#include "leaky-bucket.h"
#include "ns3/log.h"
#include "ns3/enum.h"
#include "ns3/uinteger.h"
#include "ns3/address.h"
#include "ns3/boolean.h"
#include "ns3/node.h"
#include "ns3/ipv4-header.h"
#include "ns3/attribute.h"
#include "ns3/simulator.h"
#include "ns3/data-rate.h"
#include "ns3/timer.h"
#include "ns3/packet.h"

using namespace std;

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (LeakyBucket);

TypeId
LeakyBucket::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::LeakyBucket")
    .SetParent<Queue> ()
    .AddConstructor<LeakyBucket> ()
    .AddAttribute ("Ipv4Shape", "The address of node to shape",
                   Ipv4AddressValue (),
                   MakeIpv4AddressAccessor (&LeakyBucket::m_peer),
                   MakeIpv4AddressChecker ())
    .AddAttribute ("DataRate", "The data rate of shaper.",
                   DataRateValue (DataRate ("500kb/s")),
                   MakeDataRateAccessor (&LeakyBucket::m_cbrRate),
                   MakeDataRateChecker ())
   .AddAttribute ("Mode", 
                   "Whether to use Bytes (see MaxBytes) or Packets (see MaxPackets) as the maximum queue size metric.",
                   EnumValue (PACKETS),
                   MakeEnumAccessor (&LeakyBucket::SetMode),
                   MakeEnumChecker (BYTES, "Bytes",
                                    PACKETS, "Packets"))
    .AddAttribute ("MaxPackets", 
                   "The maximum number of packets accepted by this Bucket.",
                   UintegerValue (100),
                   MakeUintegerAccessor (&LeakyBucket::m_maxPackets),
                   MakeUintegerChecker<uint32_t> ())
    .AddAttribute ("MaxBytes", 
                   "The maximum number of bytes accepted by this Bucket.",
                   UintegerValue (100 * 65535),
                   MakeUintegerAccessor (&LeakyBucket::m_maxBytes),
                   MakeUintegerChecker<uint32_t> ())
    .AddAttribute ("DSCP", "The value of dscp.",
                   UintegerValue (0),
                   MakeUintegerAccessor (&LeakyBucket::m_DSCP),
                   MakeUintegerChecker<uint8_t> ())
        ;
  return tid;
}

LeakyBucket::LeakyBucket () :
  Queue (),
  m_packets (),
  m_bytesInQueue (0)
{
  //NS_LOG_FUNCTION_NOARGS ();
}

LeakyBucket::~LeakyBucket ()
{
  //NS_LOG_FUNCTION_NOARGS ();
}

void 
LeakyBucket::SetMode (enum Mode mode)
{
  //NS_LOG_FUNCTION (mode);
  m_mode = mode;
}

Ipv4Address
LeakyBucket::GetIpv4Shape(void)
{
  return m_peer;
}


DataRate
LeakyBucket::GetCbrRate(void)
{
  return m_cbrRate;
}

bool 
LeakyBucket::DoEnqueue (Ptr<Packet> p)
{
  //NS_LOG_FUNCTION (this << p);

  if (m_mode == PACKETS && (m_packets.size () >= m_maxPackets))
    {
      //NS_LOG_LOGIC ("Queue full (at max packets) -- droppping pkt");
      Drop (p);
      return false;
    }

  if (m_mode == BYTES && (m_bytesInQueue + p->GetSize () >= m_maxBytes))
    {
      //NS_LOG_LOGIC ("Queue full (packet would exceed max bytes) -- droppping pkt");
      Drop (p);
      return false;
    }

  m_bytesInQueue += p->GetSize ();
  m_packets.push(p);

  //NS_LOG_LOGIC ("Number packets " << m_packets.size ());
  //NS_LOG_LOGIC ("Number bytes " << m_bytesInQueue);

  return true;
}

Ptr<Packet>
LeakyBucket::DoDequeue (void)
{
  //NS_LOG_FUNCTION (this);

  if (m_packets.empty()) 
    {
      //NS_LOG_LOGIC ("Queue empty");
      return 0;
    }

  Ptr<Packet> p = m_packets.front ();
  //NS_LOG_LOGIC ("bits = " << bits);
  m_packets.pop ();
  m_bytesInQueue -= p->GetSize ();

  //NS_LOG_LOGIC ("Popped " << p);

  //NS_LOG_LOGIC ("Number packets " << m_packets.size ());
  //NS_LOG_LOGIC ("Number bytes " << m_bytesInQueue);

return p;
}


Ptr<const Packet>
LeakyBucket::DoPeek (void) const
{
  //NS_LOG_FUNCTION (this);

  if (m_packets.empty()) 
    {
      //NS_LOG_LOGIC ("Queue empty");
      return 0;
    }

  Ptr<Packet> p = m_packets.front ();

  //NS_LOG_LOGIC ("Number packets " << m_packets.size ());
  //NS_LOG_LOGIC ("Number bytes " << m_bytesInQueue);

  return p;
}
}
