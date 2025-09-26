/* -*-  Mode: C++; c-file-style: "gnu"; indent-tabs-mode:nil; -*- */
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License version 2 as
// published by the Free Software Foundation;

// Author: Baltzis Petros<mpaltzis@ceid.upatras.gr>

#ifndef LEAKY_BUCKET_HELPER_H
#define LEAKY_BUCKET_HELPER_H

#include "ns3/object-factory.h"
#include "ns3/address.h"
#include "ns3/attribute.h"
#include "ns3/node.h"

namespace ns3 {

/**
 * \brief A helper to make it easier to instantiate an ns3::LeakyBucket 
 * on a set of nodes.
 */

class LeakyBucketHelper
{
public:
 
  LeakyBucketHelper ();

  /**
   * Helper function used to set the underlying attributes of leaky-bucket.
   *
   * \param name the name of the leaky-bucket attribute to set
   * \param value the value of the leaky-bucket attribute to set
   */
  void SetAttribute (std::string name, const AttributeValue &value);

  void Install (Ptr<NetDevice> ShapedDevice) const;
 
private:
  ObjectFactory m_factory;
  
};

} // namespace ns3

#endif /* ON_OFF_HELPER_H */

