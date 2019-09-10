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

#include "tcp-option.h"
#include "tcp-option-end.h"
#include "tcp-option-no-op.h"
#include "tcp-option-mss.h"
#include "tcp-option-winscale.h"
#include "tcp-option-sack-permitted.h"
#include "tcp-option-sack.h"
#include "tcp-option-ts.h"

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (TcpOption);

TcpOption::TcpOption ()
{
}

TcpOption::~TcpOption ()
{
}

TypeId
TcpOption::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::TcpOption")
    .SetParent<Object> ()
  ;
  return tid;
}

TypeId
TcpOption::GetInstanceTypeId (void) const
{
  return GetTypeId ();
}

Ptr<TcpOption>
TcpOption::Deserialize (Buffer::Iterator &start, uint32_t &optionLen)
{
  TcpOption::Kind kind = (TcpOption::Kind)start.ReadU8 ();
  Ptr<TcpOption> op;
  switch (kind)
    {
      case END_OF_OPTION_LIST:
        op = CreateObject<TcpOptionEnd> ();
        break;
      case NO_OP:
        op = CreateObject<TcpOptionNoOp> ();
        break;
      case MAX_SEGMENT_SIZE:
        op = CreateObject<TcpOptionMSS> ();
        break;
      case WINDOW_SCALE:
        op = CreateObject<TcpOptionWinScale> ();
        break;
      case SACK_PERMITED:
        op = CreateObject<TcpOptionSackPermitted> ();
        break;
      case SACK:
        op = CreateObject<TcpOptionSack> ();
        break;
      case TIME_STAMP:
        op = CreateObject<TcpOptionTS> ();
        break;
      default:
        return 0;
    }
  optionLen -= op->DoDeserialize (start);
  return op;
}

} // namespace ns3
