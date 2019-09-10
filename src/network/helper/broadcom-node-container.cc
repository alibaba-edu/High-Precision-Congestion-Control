/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2008 INRIA
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
 * Author: Mathieu Lacage <mathieu.lacage@sophia.inria.fr>
 */
#include "broadcom-node-container.h"
#include "ns3/node-list.h"
#include "ns3/names.h"

namespace ns3 {

BroadcomNodeContainer::BroadcomNodeContainer ()
{
}

BroadcomNodeContainer::BroadcomNodeContainer (Ptr<BroadcomNode> node)
{
  m_nodes.push_back (node);
}
BroadcomNodeContainer::BroadcomNodeContainer (std::string nodeName)
{
  Ptr<BroadcomNode> node = Names::Find<BroadcomNode> (nodeName);
  m_nodes.push_back (node);
}
BroadcomNodeContainer::BroadcomNodeContainer (const BroadcomNodeContainer &a, const BroadcomNodeContainer &b)
{
  Add (a);
  Add (b);
}
BroadcomNodeContainer::BroadcomNodeContainer (const BroadcomNodeContainer &a, const BroadcomNodeContainer &b, 
                              const BroadcomNodeContainer &c)
{
  Add (a);
  Add (b);
  Add (c);
}
BroadcomNodeContainer::BroadcomNodeContainer (const BroadcomNodeContainer &a, const BroadcomNodeContainer &b, 
                              const BroadcomNodeContainer &c, const BroadcomNodeContainer &d)
{
  Add (a);
  Add (b);
  Add (c);
  Add (d);
}

BroadcomNodeContainer::BroadcomNodeContainer (const BroadcomNodeContainer &a, const BroadcomNodeContainer &b, 
                              const BroadcomNodeContainer &c, const BroadcomNodeContainer &d,
                              const BroadcomNodeContainer &e)
{
  Add (a);
  Add (b);
  Add (c);
  Add (d);
  Add (e);
}

BroadcomNodeContainer::Iterator 
BroadcomNodeContainer::Begin (void) const
{
  return m_nodes.begin ();
}
BroadcomNodeContainer::Iterator 
BroadcomNodeContainer::End (void) const
{
  return m_nodes.end ();
}

uint32_t 
BroadcomNodeContainer::GetN (void) const
{
  return m_nodes.size ();
}
Ptr<BroadcomNode> 
BroadcomNodeContainer::Get (uint32_t i) const
{
  return m_nodes[i];
}
void 
BroadcomNodeContainer::Create (uint32_t n)
{
  for (uint32_t i = 0; i < n; i++)
    {
      m_nodes.push_back (CreateObject<BroadcomNode> ());
    }
}
void 
BroadcomNodeContainer::Create (uint32_t n, uint32_t systemId)
{
  for (uint32_t i = 0; i < n; i++)
    {
      m_nodes.push_back (CreateObject<BroadcomNode> (systemId));
    }
}
void 
BroadcomNodeContainer::Add (BroadcomNodeContainer other)
{
  for (Iterator i = other.Begin (); i != other.End (); i++)
    {
      m_nodes.push_back (*i);
    }
}
void 
BroadcomNodeContainer::Add (Ptr<BroadcomNode> node)
{
  m_nodes.push_back (node);
}
void 
BroadcomNodeContainer::Add (std::string nodeName)
{
  Ptr<BroadcomNode> node = Names::Find<BroadcomNode> (nodeName);
  m_nodes.push_back (node);
}

BroadcomNodeContainer 
BroadcomNodeContainer::GetGlobal (void)
{
  BroadcomNodeContainer c;
  for (NodeList::Iterator i = NodeList::Begin (); i != NodeList::End (); ++i)
    {
      c.Add (*((Ptr<BroadcomNode>)i));
    }
  return c;
}

} // namespace ns3
