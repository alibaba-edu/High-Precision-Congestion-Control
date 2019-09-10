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

#include "tcp-option-no-op.h"

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (TcpOptionNoOp);

uint8_t TcpOptionNoOp::NoOpLength = 1;

TcpOptionNoOp::TcpOptionNoOp ()
{
}

TcpOptionNoOp::~TcpOptionNoOp ()
{
}

TypeId
TcpOptionNoOp::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::TcpOptionNoOp")
    .SetParent<TcpOption> ()
  ;
  return tid;
}

TypeId
TcpOptionNoOp::GetInstanceTypeId (void) const
{
  return GetTypeId ();
}

std::string
TcpOptionNoOp::Str (void) const
{
  return "NoOp";
}

uint32_t
TcpOptionNoOp::GetSerializedSize (void) const
{
  return NoOpLength;
}

void
TcpOptionNoOp::Serialize (Buffer::Iterator &start) const
{
  start.WriteU8 (TcpOption::NO_OP);
}

uint32_t
TcpOptionNoOp::DoDeserialize (Buffer::Iterator &start)
{
  return NoOpLength;
}

TcpOption::Kind
TcpOptionNoOp::GetKind (void) const
{
  return TcpOption::NO_OP;
}

} // namespace ns3
