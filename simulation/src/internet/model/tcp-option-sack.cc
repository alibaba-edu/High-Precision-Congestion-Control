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

#include "tcp-option-sack.h"

namespace ns3 {

NS_OBJECT_ENSURE_REGISTERED (TcpOptionSack);

uint8_t TcpOptionSack::SACKLength = 10;

TcpOptionSack::TcpOptionSack ()
{
}

TcpOptionSack::~TcpOptionSack ()
{
}

TypeId
TcpOptionSack::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::TcpOptionSack")
    .SetParent<TcpOption> ()
  ;
  return tid;
}

TypeId
TcpOptionSack::GetInstanceTypeId (void) const
{
  return GetTypeId ();
}

std::string
TcpOptionSack::Str (void) const
{
  std::ostringstream os;
  os << " SACK:" << std::endl;
  for (ScoreBoard::const_iterator l_i = m_sb.begin (); l_i != m_sb.end (); ++l_i)
    {
      os << "  left SACK " << l_i->first.GetValue (); // left
      os << " right SACK " << l_i->second.GetValue (); // right
      os << ";" << std::endl;
    }
  return os.str();
}

uint32_t
TcpOptionSack::GetSerializedSize (void) const
{
  return m_sb.size () * 2 * sizeof(uint32_t) + 2 * sizeof(uint8_t);
}

void
TcpOptionSack::Serialize (Buffer::Iterator &start) const
{
  start.WriteU8 (TcpOption::SACK); // Kind
  start.WriteU8 (m_sb.size () * 2 * sizeof(uint32_t) + 2 * sizeof(uint8_t)); // Length
  for (ScoreBoard::const_iterator l_i = m_sb.begin (); l_i != m_sb.end (); ++l_i)
    {
      start.WriteHtonU32 (l_i->first.GetValue ()); // left
      start.WriteHtonU32 (l_i->second.GetValue ()); // right
    }
}

uint32_t
TcpOptionSack::DoDeserialize (Buffer::Iterator &start)
{
  uint8_t size = start.ReadU8 ();
  NS_ASSERT (size >=  SACKLength && ((size - 2) % 8 == 0));
  uint8_t length = size - 2;
  m_sb.clear ();
  while (length > 0)
    {
      SequenceNumber32 left = SequenceNumber32(start.ReadNtohU32 ());
      SequenceNumber32 right = SequenceNumber32(start.ReadNtohU32 ());
      SackBlock s = SackBlock(left, right);
      m_sb.push_back (s);
      length -= 8;
    }
  return size;
}

TcpOption::Kind
TcpOptionSack::GetKind (void) const
{
  return TcpOption::SACK;
}

void
TcpOptionSack::AddSack (SackBlock s)
{
  // Assumed s has no overlap with any SACK block in m_sb
  for (ScoreBoard::iterator i = m_sb.begin (); i != m_sb.end (); ++i)
    {
      if (s.first < i->first)
        {
          m_sb.insert(i,s);
          break;
        }
    }
}

uint32_t
TcpOptionSack::SackCount (void) const
{
  return m_sb.size ();
}

void
TcpOptionSack::ClearSackList (void)
{
  m_sb.clear ();
}

ScoreBoard
TcpOptionSack::GetSackList (void) const
{
  return m_sb;
}

} // namespace ns3
