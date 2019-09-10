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

#ifndef TCP_OPTION_TS_H
#define TCP_OPTION_TS_H

#include "tcp-option.h"

namespace ns3 {

/**
 * Defines the TCP option of kind 8 (timestamp option) as in RFC1323
 */

class TcpOptionTS : public TcpOption
{
public:
  TcpOptionTS ();
  virtual ~TcpOptionTS ();

  static TypeId GetTypeId (void);
  virtual TypeId GetInstanceTypeId (void) const;

  virtual std::string Str (void) const;
  virtual void Serialize (Buffer::Iterator &start) const;

  virtual TcpOption::Kind GetKind (void) const;
  virtual uint32_t GetSerializedSize (void) const;

  uint32_t GetTimestamp (void) const;
  uint32_t GetEcho (void) const;
  void SetTimestamp (uint32_t ts);
  void SetEcho (uint32_t ts);
protected:
  uint32_t m_timestamp; // local timestamp
  uint32_t m_echo;      // echo timestamp
  static uint8_t TimeStampLength;
private:
  virtual uint32_t DoDeserialize (Buffer::Iterator &start);
};

} // namespace ns3

#endif /* TCP_OPTION_TS */
