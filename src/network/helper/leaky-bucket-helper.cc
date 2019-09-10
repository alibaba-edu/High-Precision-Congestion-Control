/* -*-  Mode: C++; c-file-style: "gnu"; indent-tabs-mode:nil; -*- */
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License version 2 as
// published by the Free Software Foundation;
//
// Author: Baltzis Petros<mpaltzis@ceid.upatras.gr>

#include "leaky-bucket-helper.h"
#include "ns3/leaky-bucket.h"
#include "ns3/node.h"
#include "ns3/inet-socket-address.h"
#include "ns3/packet-socket-address.h"
#include "ns3/net-device.h"


namespace ns3 {

LeakyBucketHelper::LeakyBucketHelper ()
{
  m_factory.SetTypeId ("ns3::LeakyBucket");
}

void 
LeakyBucketHelper::SetAttribute (std::string name, const AttributeValue &value)
{
  m_factory.Set (name, value);
}

//This function is called to install a leay-bucket to a node
void
LeakyBucketHelper::Install (Ptr<NetDevice> ShapedDevice) const
{
  Ptr<Node> ShapedNode = ShapedDevice->GetNode();
  Ptr<LeakyBucket> leaky = m_factory.Create<LeakyBucket> ();
  //ShapedNode->AddShaper (leaky, ShapedDevice);

}

} // namespace ns3
