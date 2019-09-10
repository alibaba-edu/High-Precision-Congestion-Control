/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2007 University of Washington
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation;
 */

// Author: Baltzis Petros<mpaltzis@ceid.upatras.gr>

#ifndef LEAKYBUCKET_H
#define LEAKYBUCKET_H

#include <queue>
#include "ns3/packet.h"
#include "ns3/queue.h"
#include "ns3/data-rate.h"
#include "ns3/address.h"
#include "ns3/ptr.h"
#include "ns3/ipv4-header.h"


namespace ns3 {

class TraceContainer;


/**
 * The Leaky-Bucket is a subclass of Queue. 
 * brief A FIFO packet queue that drops tail-end packets on overflow of leaky bucket
 * 
 */
class LeakyBucket : public Queue {
public:
  static TypeId GetTypeId (void);
  /**
   * LeakyBucket Constructor
   *
   * Creates a LeakyBucket queue with a maximum size of 100 packets by default
   * 
   */
  LeakyBucket ();

  virtual ~LeakyBucket();

  /**
   * Enumeration of the modes supported in the class. 
   *
   */
  enum Mode {
    ILLEGAL,     
    PACKETS,     
    BYTES,        
  };


  /**
   * Set the operating mode of this device.
   *
   * \param mode The operating mode of this device.
   *
   */
  void SetMode (LeakyBucket::Mode mode);

   /**
   * Get the encapsulation mode of this device.
   *
   * \returns The encapsulation mode of this device.
   */
  LeakyBucket::Mode  GetMode (void);

  /**
   * 
   * returns the Ip of the node whose traffic we want to shape
   *
   */
  Ipv4Address GetIpv4Shape(void);

  /**
   * returns the cbr for the transmission of the packets
   * 
   */
  DataRate GetCbrRate(void);

private:
  virtual bool DoEnqueue (Ptr<Packet> p);
  virtual Ptr<Packet> DoDequeue (void);
  virtual Ptr<const Packet> DoPeek (void) const;

  std::queue<Ptr<Packet> > m_packets;
  uint32_t      m_maxPackets;
  uint32_t      m_maxBytes;
  uint32_t      m_bytesInQueue;       
  Mode          m_mode;               
  DataRate      m_cbrRate;            
  uint8_t       m_DSCP;               
  Ipv4Address   m_peer;               
};

}; // namespace ns3

#endif /* DROPTAIL_H */
