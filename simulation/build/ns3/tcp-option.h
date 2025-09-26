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

#ifndef TCP_OPTION_H
#define TCP_OPTION_H

#include <stdint.h>
#include "ns3/object.h"
#include "ns3/buffer.h"

namespace ns3 {

/**
 * Base class for all kinds of TCP options
 */

class TcpOption : public Object
{
public:
  TcpOption ();
  virtual ~TcpOption ();

  static TypeId GetTypeId (void);
  virtual TypeId GetInstanceTypeId (void) const;

  enum Kind {
    END_OF_OPTION_LIST          = 0x0,
    NO_OP,
    MAX_SEGMENT_SIZE,
    WINDOW_SCALE,
    SACK_PERMITED,
    SACK,
    TIME_STAMP                  = 0x8,
    SKEETER                     = 0x10,
    BUBBA,
    TRAILER_CHECKSUM,
    SCPS_CAPABILITY             = 0x14,
    SELECTIVE_NACK,
    RECORD_BOUNDRIES,
    CORRUPTION_EXPERIENCED,
    SNAP,
    TCP_COMPRESSION_FILTER      = 0x1A,
    QUICK_START_RESPONSE,
    USER_TIMEOUT,
    TCP_AUTHENTICATION,
    MULTIPATH_TCP,
    EXPERIMENTAL1               = 0xFD,
    EXPERIMENTAL2
  };

  virtual std::string Str (void) const = 0;
  virtual void Serialize (Buffer::Iterator &start) const = 0;
  static Ptr<TcpOption> Deserialize (Buffer::Iterator &start, uint32_t &optionLen); // Factory method for all options

  virtual Kind GetKind (void) const = 0; // Get the `kind' (as in RFC793) of this option
  virtual uint32_t GetSerializedSize (void) const = 0; // Get the total length of this option, >= 1
private:
  /*
   * DoDesearialize must also calculate the first byte that was stripped down,
   * so the TCP Option type could be deducted
   */
  virtual uint32_t DoDeserialize (Buffer::Iterator &start) = 0;
};

} // namespace ns3

#endif /* TCP_OPTION */
