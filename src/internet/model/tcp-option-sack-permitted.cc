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

#include "tcp-option-sack-permitted.h"

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (TcpOptionSackPermitted);

uint8_t TcpOptionSackPermitted::SackPermLength = 2;

TcpOptionSackPermitted::TcpOptionSackPermitted ()
{
}

TcpOptionSackPermitted::~TcpOptionSackPermitted ()
{
}

TypeId
TcpOptionSackPermitted::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::TcpOptionSackPermitted")
    .SetParent<TcpOption> ()
  ;
  return tid;
}

TypeId
TcpOptionSackPermitted::GetInstanceTypeId (void) const
{
  return GetTypeId ();
}

std::string
TcpOptionSackPermitted::Str (void) const
{
  return "SACK Permitted";
}

uint32_t
TcpOptionSackPermitted::GetSerializedSize (void) const
{
  return SackPermLength;
}

void
TcpOptionSackPermitted::Serialize (Buffer::Iterator &start) const
{
  start.WriteU8 (TcpOption::SACK_PERMITED); // Kind

  start.WriteU8 (SackPermLength); // Length
}

uint32_t
TcpOptionSackPermitted::DoDeserialize (Buffer::Iterator &start)
{
  uint8_t size = start.ReadU8 ();
  NS_ASSERT (size == SackPermLength);
  return SackPermLength;
}

TcpOption::Kind
TcpOptionSackPermitted::GetKind (void) const
{
  return TcpOption::SACK_PERMITED;
}

} // namespace ns3
