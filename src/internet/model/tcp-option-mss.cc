/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2011 Adrian Sai-wah Tam
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
 * Author: Adrian Sai-wah Tam <adrian.sw.tam@gmail.com>
 */

#include "tcp-option-mss.h"

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (TcpOptionMSS);

uint8_t TcpOptionMSS::MSSLength = 4;

TcpOptionMSS::TcpOptionMSS ()
  : m_mss (1460)
{
}

TcpOptionMSS::~TcpOptionMSS ()
{
}

TypeId
TcpOptionMSS::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::TcpOptionMSS")
    .SetParent<TcpOption> ()
  ;
  return tid;
}

TypeId
TcpOptionMSS::GetInstanceTypeId (void) const
{
  return GetTypeId ();
}

std::string
TcpOptionMSS::Str (void) const
{
  std::ostringstream os;
  os << "MSS " << m_mss;
  return os.str();
}

uint32_t
TcpOptionMSS::GetSerializedSize (void) const
{
  return MSSLength;
}

void
TcpOptionMSS::Serialize (Buffer::Iterator &start) const
{
  start.WriteU8 (TcpOption::MAX_SEGMENT_SIZE); // Kind
  start.WriteU8 (MSSLength); // Length
  start.WriteHtonU16 (m_mss); // Max segment size
}

uint32_t
TcpOptionMSS::DoDeserialize (Buffer::Iterator &start)
{
  uint8_t size = start.ReadU8 ();
  NS_ASSERT (size == MSSLength);
  m_mss = start.ReadNtohU16 ();
  return MSSLength;
}

TcpOption::Kind
TcpOptionMSS::GetKind (void) const
{
  return TcpOption::MAX_SEGMENT_SIZE;
}

uint16_t
TcpOptionMSS::GetMSS (void) const
{
  return m_mss;
}

void
TcpOptionMSS::SetMSS (uint16_t mss)
{
  m_mss = mss;
}

} // namespace ns3
