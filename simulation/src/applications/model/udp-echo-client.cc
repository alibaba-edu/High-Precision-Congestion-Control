/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright 2007 University of Washington
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
 */
#include "ns3/log.h"
#include "ns3/ipv4-address.h"
#include "ns3/ipv6-address.h"
#include "ns3/nstime.h"
#include "ns3/inet-socket-address.h"
#include "ns3/inet6-socket-address.h"
#include "ns3/socket.h"
#include "ns3/simulator.h"
#include "ns3/socket-factory.h"
#include "ns3/packet.h"
#include "ns3/uinteger.h"
#include "ns3/trace-source-accessor.h"
#include "ns3/random-variable.h"
#include "ns3/qbb-net-device.h"
#include "ns3/ipv4-end-point.h"
#include "udp-echo-client.h"
#include "ns3/seq-ts-header.h"

namespace ns3 {

	NS_LOG_COMPONENT_DEFINE("UdpEchoClientApplication");
	NS_OBJECT_ENSURE_REGISTERED(UdpEchoClient);

	TypeId
		UdpEchoClient::GetTypeId(void)
	{
		static TypeId tid = TypeId("ns3::UdpEchoClient")
			.SetParent<Application>()
			.AddConstructor<UdpEchoClient>()
			.AddAttribute("MaxPackets",
				"The maximum number of packets the application will send",
				UintegerValue(100),
				MakeUintegerAccessor(&UdpEchoClient::m_count),
				MakeUintegerChecker<uint32_t>())
			.AddAttribute("ChunkSize",
				"The chunk size can be sent before getting an ack",
				UintegerValue(4000000),
				MakeUintegerAccessor(&UdpEchoClient::m_chunk),
				MakeUintegerChecker<uint32_t>())
			.AddAttribute("Interval",
				"The time to wait between packets",
				TimeValue(Seconds(1.0)),
				MakeTimeAccessor(&UdpEchoClient::m_interval),
				MakeTimeChecker())
			.AddAttribute("RemoteAddress",
				"The destination Address of the outbound packets",
				AddressValue(),
				MakeAddressAccessor(&UdpEchoClient::m_peerAddress),
				MakeAddressChecker())
			.AddAttribute("RemotePort",
				"The destination port of the outbound packets",
				UintegerValue(0),
				MakeUintegerAccessor(&UdpEchoClient::m_peerPort),
				MakeUintegerChecker<uint16_t>())
			.AddAttribute("PriorityGroup", "The priority group of this flow",
				UintegerValue(0),
				MakeUintegerAccessor(&UdpEchoClient::m_pg),
				MakeUintegerChecker<uint16_t>())
			.AddAttribute("PacketSize", "Size of echo data in outbound packets",
				UintegerValue(1024),
				MakeUintegerAccessor(&UdpEchoClient::SetDataSize,
					&UdpEchoClient::GetDataSize),
				MakeUintegerChecker<uint32_t>())
			.AddTraceSource("Tx", "A new packet is created and is sent",
				MakeTraceSourceAccessor(&UdpEchoClient::m_txTrace))
			;
		return tid;
	}

	UdpEchoClient::UdpEchoClient()
	{
		NS_LOG_FUNCTION_NOARGS();
		m_sent = 0;
		m_sentBytes = 0;
		m_socket = 0;
		m_sendEvent = EventId();
		m_data = 0;
		m_dataSize = 0;
	}

	UdpEchoClient::~UdpEchoClient()
	{
		NS_LOG_FUNCTION_NOARGS();
		m_socket = 0;

		delete[] m_data;
		m_data = 0;
		m_dataSize = 0;
	}

	void
		UdpEchoClient::SetRemote(Address ip, uint16_t port)
	{
		m_peerAddress = ip;
		m_peerPort = port;
	}

	void
		UdpEchoClient::SetRemote(Ipv4Address ip, uint16_t port)
	{
		m_peerAddress = Address(ip);
		m_peerPort = port;
	}

	void
		UdpEchoClient::SetRemote(Ipv6Address ip, uint16_t port)
	{
		m_peerAddress = Address(ip);
		m_peerPort = port;
	}

	void
		UdpEchoClient::DoDispose(void)
	{
		NS_LOG_FUNCTION_NOARGS();
		Application::DoDispose();
	}

	void
		UdpEchoClient::StartApplication(void)
	{
		NS_LOG_FUNCTION_NOARGS();

		if (m_socket == 0)
		{
			TypeId tid = TypeId::LookupByName("ns3::UdpSocketFactory");
			m_socket = Socket::CreateSocket(GetNode(), tid);
			if (Ipv4Address::IsMatchingType(m_peerAddress) == true)
			{
				m_socket->Bind();
				m_socket->Connect(InetSocketAddress(Ipv4Address::ConvertFrom(m_peerAddress), m_peerPort));
			}
			else if (Ipv6Address::IsMatchingType(m_peerAddress) == true)
			{
				m_socket->Bind6();
				m_socket->Connect(Inet6SocketAddress(Ipv6Address::ConvertFrom(m_peerAddress), m_peerPort));
			}
		}

		m_socket->SetRecvCallback(MakeCallback(&UdpEchoClient::HandleRead, this));
		m_allowed = m_chunk;
		ScheduleTransmit(Seconds(0.));
	}

	void
		UdpEchoClient::StopApplication()
	{
		NS_LOG_FUNCTION_NOARGS();

		if (m_socket != 0)
		{
			m_socket->Close();
			m_socket->SetRecvCallback(MakeNullCallback<void, Ptr<Socket> >());
			m_socket = 0;
		}

		Simulator::Cancel(m_sendEvent);
	}

	void
		UdpEchoClient::SetDataSize(uint32_t dataSize)
	{
		NS_LOG_FUNCTION(dataSize);

		//
		// If the client is setting the echo packet data size this way, we infer
		// that she doesn't care about the contents of the packet at all, so 
		// neither will we.
		//
		delete[] m_data;
		m_data = 0;
		m_dataSize = 0;
		m_size = dataSize;
	}

	uint32_t
		UdpEchoClient::GetDataSize(void) const
	{
		NS_LOG_FUNCTION_NOARGS();
		return m_size;
	}

	void
		UdpEchoClient::SetFill(std::string fill)
	{
		NS_LOG_FUNCTION(fill);

		uint32_t dataSize = fill.size() + 1;

		if (dataSize != m_dataSize)
		{
			delete[] m_data;
			m_data = new uint8_t[dataSize];
			m_dataSize = dataSize;
		}

		memcpy(m_data, fill.c_str(), dataSize);

		//
		// Overwrite packet size attribute.
		//
		m_size = dataSize;
	}

	void
		UdpEchoClient::SetFill(uint8_t fill, uint32_t dataSize)
	{
		if (dataSize != m_dataSize)
		{
			delete[] m_data;
			m_data = new uint8_t[dataSize];
			m_dataSize = dataSize;
		}

		memset(m_data, fill, dataSize);

		//
		// Overwrite packet size attribute.
		//
		m_size = dataSize;
	}

	void
		UdpEchoClient::SetFill(uint8_t *fill, uint32_t fillSize, uint32_t dataSize)
	{
		if (dataSize != m_dataSize)
		{
			delete[] m_data;
			m_data = new uint8_t[dataSize];
			m_dataSize = dataSize;
		}

		if (fillSize >= dataSize)
		{
			memcpy(m_data, fill, dataSize);
			m_size = dataSize;
			return;
		}

		//
		// Do all but the final fill.
		//
		uint32_t filled = 0;
		while (filled + fillSize < dataSize)
		{
			memcpy(&m_data[filled], fill, fillSize);
			filled += fillSize;
		}

		//
		// Last fill may be partial
		//
		memcpy(&m_data[filled], fill, dataSize - filled);

		//
		// Overwrite packet size attribute.
		//
		m_size = dataSize;
	}

	void
		UdpEchoClient::ScheduleTransmit(Time dt)
	{
		NS_LOG_FUNCTION_NOARGS();
		m_sendEvent = Simulator::Schedule(dt, &UdpEchoClient::Send, this);
	}

	void
		UdpEchoClient::Send(void)
	{

		NS_LOG_FUNCTION_NOARGS();
		NS_ASSERT(m_sendEvent.IsExpired());

		//below we need to make sure the UDP client is also pushed back when the host gets PFC
		//otherwise UDP client will build infinite queues on the host
		Ptr<Node> node = GetNode();
		uint32_t dn = node->GetNDevices();
		double next_avail = 10;
		bool found = false;

		for (uint32_t i = 0; i < dn; i++)
		{
			Ptr<NetDevice> d = node->GetDevice(i);
			uint32_t localp = m_socket->GetLocalPort();

			uint32_t buffer = d->GetUsedBuffer(localp, m_pg);
			double tmp = (buffer*8.0 - 1500 * 8.0) / 40 / 1000000000 * 0.95; //0.95 is for conservative. assuming 40Gbps link.
			if (tmp < next_avail && tmp>0)
			{
				next_avail = tmp;
				found = true;
			}
		}
		if (!found)
		{
			next_avail = 0;
		}

		next_avail = next_avail > m_interval.GetSeconds() ? next_avail : m_interval.GetSeconds();

		if (next_avail < 0.000005)
		{
			SeqTsHeader seqTs;
			seqTs.SetSeq(m_sent);
			seqTs.SetPG(m_pg);
			Ptr<Packet> p = Create<Packet>(m_size - 14); // 14 : the size of the seqTs header
			p->AddHeader(seqTs);

			std::stringstream peerAddressStringStream;
			if (Ipv4Address::IsMatchingType(m_peerAddress))
			{
				peerAddressStringStream << Ipv4Address::ConvertFrom(m_peerAddress);
			}
			else if (Ipv6Address::IsMatchingType(m_peerAddress))
			{
				peerAddressStringStream << Ipv6Address::ConvertFrom(m_peerAddress);
			}

			if (m_sentBytes < m_allowed && m_sentBytes / m_size < m_count)
			{
				if ((m_socket->Send(p)) >= 0)
				{
					++m_sent;
					m_sentBytes += p->GetSize();
					NS_LOG_INFO("TraceDelay TX " << m_size << " bytes to "
						<< peerAddressStringStream.str() << " Uid: "
						<< p->GetUid() << " Time: "
						<< (Simulator::Now()).GetSeconds());

				}
				else
				{
					NS_LOG_INFO("Error while sending " << m_size << " bytes to "
						<< peerAddressStringStream.str());
				}
			}
		}

		//add jitter here to avoid unfairness across different flows
		if (m_sentBytes < m_allowed && m_sentBytes / m_size < m_count)
		{
			m_sendEvent = Simulator::Schedule(Seconds(next_avail * UniformVariable(0.45, 0.55).GetValue()), &UdpEchoClient::Send, this);
		}
	}

	void
		UdpEchoClient::HandleRead(Ptr<Socket> socket)
	{
		NS_LOG_FUNCTION(this << socket);
		Ptr<Packet> packet;
		Address from;
		while ((packet = socket->RecvFrom(from)))
		{
			if (InetSocketAddress::IsMatchingType(from))
			{
				NS_LOG_INFO("At time " << Simulator::Now().GetSeconds() << "s client received " << packet->GetSize() << " bytes from " <<
					InetSocketAddress::ConvertFrom(from).GetIpv4() << " port " <<
					InetSocketAddress::ConvertFrom(from).GetPort());
				m_allowed += m_chunk;
				m_sendEvent = Simulator::Schedule(Seconds(0), &UdpEchoClient::Send, this);
			}
			else if (Inet6SocketAddress::IsMatchingType(from))
			{
				NS_LOG_INFO("At time " << Simulator::Now().GetSeconds() << "s client received " << packet->GetSize() << " bytes from " <<
					Inet6SocketAddress::ConvertFrom(from).GetIpv6() << " port " <<
					Inet6SocketAddress::ConvertFrom(from).GetPort());
				m_allowed += m_chunk;
				//for quiescence flows
				m_sendEvent = Simulator::Schedule(Seconds(0), &UdpEchoClient::Send, this);
			}
		}

	}

} // Namespace ns3
