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

#ifndef TCP_OPTION_NOP_H
#define TCP_OPTION_NOP_H

#include "tcp-option.h"

namespace ns3 {

/**
 * Defines the TCP option of kind 1 (no operation) as in RFC793
 */

class TcpOptionNoOp : public TcpOption
{
public:
  TcpOptionNoOp ();
  virtual ~TcpOptionNoOp ();

  static TypeId GetTypeId (void);
  virtual TypeId GetInstanceTypeId (void) const;

  virtual std::string Str (void) const;
  virtual void Serialize (Buffer::Iterator &start) const;

  virtual TcpOption::Kind GetKind (void) const;
  virtual uint32_t GetSerializedSize (void) const;
protected:
  static uint8_t NoOpLength;
private:
  virtual uint32_t DoDeserialize (Buffer::Iterator &start);
};

} // namespace ns3

#endif /* TCP_OPTION_NOP_H */
