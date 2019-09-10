/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2007,2008,2009 INRIA, UDCAST
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
 * Author: Amine Ismail <amine.ismail@sophia.inria.fr>
 *                      <amine.ismail@udcast.com>
 */
#include "ns3/log.h"
#include "ns3/ipv4-address.h"
#include "ns3/nstime.h"
#include "ns3/inet-socket-address.h"
#include "ns3/inet6-socket-address.h"
#include "ns3/socket.h"
#include "ns3/simulator.h"
#include "ns3/socket-factory.h"
#include "ns3/packet.h"
#include "ns3/uinteger.h"
#include "ns3/random-variable.h"
#include "ns3/qbb-net-device.h"
#include "ns3/ipv4-end-point.h"
#include "udp-client.h"
#include "ns3/seq-ts-header.h"
#include <stdlib.h>
#include <stdio.h>

namespace ns3 {

NS_LOG_COMPONENT_DEFINE ("UdpClient");
NS_OBJECT_ENSURE_REGISTERED (UdpClient);

TypeId
UdpClient::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::UdpClient")
    .SetParent<Application> ()
    .AddConstructor<UdpClient> ()
    .AddAttribute ("MaxPackets",
                   "The maximum number of packets the application will send",
                   UintegerValue (100),
                   MakeUintegerAccessor (&UdpClient::m_count),
                   MakeUintegerChecker<uint32_t> ())
    .AddAttribute ("Interval",
                   "The time to wait between packets", TimeValue (Seconds (1.0)),
                   MakeTimeAccessor (&UdpClient::m_interval),
                   MakeTimeChecker ())
    .AddAttribute ("RemoteAddress",
					"The destination Address of the outbound packets",
					AddressValue (),
					MakeAddressAccessor (&UdpClient::m_peerAddress),
					MakeAddressChecker ())
    .AddAttribute ("RemotePort", "The destination port of the outbound packets",
                   UintegerValue (100),
                   MakeUintegerAccessor (&UdpClient::m_peerPort),
                   MakeUintegerChecker<uint16_t> ())
	.AddAttribute ("PriorityGroup", "The priority group of this flow",
				   UintegerValue (0),
				   MakeUintegerAccessor (&UdpClient::m_pg),
				   MakeUintegerChecker<uint16_t> ())
    .AddAttribute ("PacketSize",
                   "Size of packets generated. The minimum packet size is 14 bytes which is the size of the header carrying the sequence number and the time stamp.",
                   UintegerValue (1024),
                   MakeUintegerAccessor (&UdpClient::m_size),
                   MakeUintegerChecker<uint32_t> (14,1500))
  ;
  return tid;
}

UdpClient::UdpClient ()
{
  NS_LOG_FUNCTION_NOARGS ();
  m_sent = 0;
  m_socket = 0;
  m_sendEvent = EventId ();
}

UdpClient::~UdpClient ()
{
  NS_LOG_FUNCTION_NOARGS ();
}

void
UdpClient::SetRemote (Ipv4Address ip, uint16_t port)
{
  m_peerAddress = Address(ip);
  m_peerPort = port;
}

void
UdpClient::SetRemote (Ipv6Address ip, uint16_t port)
{
  m_peerAddress = Address(ip);
  m_peerPort = port;
}

void
UdpClient::SetRemote (Address ip, uint16_t port)
{
  m_peerAddress = ip;
  m_peerPort = port;
}

void
UdpClient::DoDispose (void)
{
  NS_LOG_FUNCTION_NOARGS ();
  Application::DoDispose ();
}

void
UdpClient::StartApplication (void)
{
  NS_LOG_FUNCTION_NOARGS ();

  if (m_socket == 0)
    {
      TypeId tid = TypeId::LookupByName ("ns3::UdpSocketFactory");
      m_socket = Socket::CreateSocket (GetNode (), tid);
      if (Ipv4Address::IsMatchingType(m_peerAddress) == true)
        {
          m_socket->Bind ();
          m_socket->Connect (InetSocketAddress (Ipv4Address::ConvertFrom(m_peerAddress), m_peerPort));
        }
      else if (Ipv6Address::IsMatchingType(m_peerAddress) == true)
        {
          m_socket->Bind6 ();
          m_socket->Connect (Inet6SocketAddress (Ipv6Address::ConvertFrom(m_peerAddress), m_peerPort));
        }
    }

  m_socket->SetRecvCallback (MakeCallback (&UdpClient::Reset, this));
  m_sendEvent = Simulator::Schedule (Seconds (0.0), &UdpClient::Send, this);
  m_allowed = m_count;
}

void
UdpClient::StopApplication ()
{
  NS_LOG_FUNCTION_NOARGS ();
  Simulator::Cancel (m_sendEvent);
}

void
UdpClient::Send (void)
{
  NS_LOG_FUNCTION_NOARGS ();
  NS_ASSERT (m_sendEvent.IsExpired ());

  //Yibo: optimize!!!
  Ptr<Node> node = GetNode();
  uint32_t dn = node->GetNDevices();
  double next_avail=10;
  bool found=false;

  for (uint32_t i=0;i<dn;i++)
  {
	  Ptr<NetDevice> d = node->GetDevice(i);
	  uint32_t localp=m_socket->GetLocalPort();
	  
	  //std::cout<<localp<<"\n";
	  uint32_t buffer = d->GetUsedBuffer(localp,m_pg);
	  double tmp = (buffer*8.0-1500*8.0)/40/1000000000*0.95; //0.95 is for conservative. assuming 40Gbps link.
	  if (tmp<next_avail && tmp>0)
	  {
		  next_avail = tmp;
		  found = true;
	  }
	      //std::cout<<tmp<<"\n";
  }
  if (!found)
  {
	  next_avail=0;
  }
  
  next_avail = next_avail>m_interval.GetSeconds()?next_avail:m_interval.GetSeconds();
  //next_avail = m_interval.GetSeconds();

  if (next_avail < 0.000005)
  {
	  SeqTsHeader seqTs;
	  seqTs.SetSeq (m_sent);
	  seqTs.SetPG (m_pg);
	  //Ptr<Packet> p = Create<Packet> (m_size-14-10); // 14 : the size of the seqTs header, 10: the size of qbb header
	  Ptr<Packet> p = Create<Packet> (m_size);
	  p->AddHeader (seqTs);

	  std::stringstream peerAddressStringStream;
	  if (Ipv4Address::IsMatchingType (m_peerAddress))
	  {
		  peerAddressStringStream << Ipv4Address::ConvertFrom (m_peerAddress);
	  }
	  else if (Ipv6Address::IsMatchingType (m_peerAddress))
	  {
		  peerAddressStringStream << Ipv6Address::ConvertFrom (m_peerAddress);
	  }

	  if ((m_socket->Send (p)) >= 0)
	  {
		  ++m_sent;
		  NS_LOG_INFO ("TraceDelay TX " << m_size << " bytes to "
			  << peerAddressStringStream.str () << " Uid: "
			  << p->GetUid () << " Time: "
			  << (Simulator::Now ()).GetSeconds ());

	  }
	  else
	  {
		  NS_LOG_INFO ("Error while sending " << m_size << " bytes to "
			  << peerAddressStringStream.str ());
	  }
  }

  //Yibo: add jitter here to avoid unfairness!!!!!
  if (m_sent < m_allowed)
    {
      m_sendEvent = Simulator::Schedule (Seconds(next_avail * UniformVariable(0.45,0.55).GetValue()), &UdpClient::Send, this);
    }

}

void 
UdpClient::SetPG (uint16_t pg)
{
	m_pg = pg;
	return;
}

void
UdpClient::Reset(Ptr<Socket> socket)
{
	m_allowed += m_count;
	Send();
}

} // Namespace ns3
