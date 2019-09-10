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

#include "tcp-option-end.h"

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (TcpOptionEnd);

uint8_t TcpOptionEnd::EOPLength = 1;

TcpOptionEnd::TcpOptionEnd ()
{
}

TcpOptionEnd::~TcpOptionEnd ()
{
}

TypeId
TcpOptionEnd::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::TcpOptionEnd")
    .SetParent<TcpOption> ()
  ;
  return tid;
}

TypeId
TcpOptionEnd::GetInstanceTypeId (void) const
{
  return GetTypeId ();
}

std::string
TcpOptionEnd::Str (void) const
{
  return "End Of Options";
}

uint32_t
TcpOptionEnd::GetSerializedSize (void) const
{
  return EOPLength;
}

void
TcpOptionEnd::Serialize (Buffer::Iterator &start) const
{
  start.WriteU8 (TcpOption::END_OF_OPTION_LIST);
}

uint32_t
TcpOptionEnd::DoDeserialize (Buffer::Iterator &start)
{
  return EOPLength;
}

TcpOption::Kind
TcpOptionEnd::GetKind (void) const
{
  return TcpOption::END_OF_OPTION_LIST;
}

} // namespace ns3
