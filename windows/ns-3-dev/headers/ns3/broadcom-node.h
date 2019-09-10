/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Copyright (c) 2006 Georgia Tech Research Corporation, INRIA
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
 * Author: Yibo Zhu <yibzh@microsoft.com>
 */
#ifndef BROADCOM_NODE_H
#define BROADCOM_NODE_H

#include <vector>

#include "ns3/object.h"
#include "ns3/callback.h"
#include "ns3/ptr.h"
#include "ns3/net-device.h"

namespace ns3 {

	class Application;
	class Packet;
	class Address;


	/**
	 * \ingroup network
	 *
	 * \brief A network Node.
	 *
	 * This class holds together:
	 *   - a list of NetDevice objects which represent the network interfaces
	 *     of this node which are connected to other Node instances through
	 *     Channel instances.
	 *   - a list of Application objects which represent the userspace
	 *     traffic generation applications which interact with the Node
	 *     through the Socket API.
	 *   - a node Id: a unique per-node identifier.
	 *   - a system Id: a unique Id used for parallel simulations.
	 *
	 * Every Node created is added to the NodeList automatically.
	 */
	class BroadcomNode : public Object
	{
	public:

		static const unsigned qCnt = 8;	// Number of queues/priorities used
		static const unsigned pCnt = 64;	// Number of ports used

		static TypeId GetTypeId(void);

		BroadcomNode();
		/**
		 * \param systemId a unique integer used for parallel simulations.
		 */
		 //BroadcomNode(uint32_t systemId);

		virtual ~BroadcomNode();


		//yibo
		bool CheckIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
		bool CheckEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
		void UpdateIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
		void UpdateEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
		void RemoveFromIngressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);
		void RemoveFromEgressAdmission(uint32_t port, uint32_t qIndex, uint32_t psize);

		void GetPauseClasses(uint32_t port, uint32_t qIndex, bool pClasses[]);
		bool GetResumeClasses(uint32_t port, uint32_t qIndex);

		void SetBroadcomParams(
			uint32_t buffer_cell_limit_sp, //ingress sp buffer threshold p.120
			uint32_t buffer_cell_limit_sp_shared, //ingress sp buffer shared threshold, nonshare -> share
			uint32_t pg_min_cell, //ingress pg guarantee
			uint32_t port_min_cell, //ingress port guarantee
			uint32_t pg_shared_limit_cell, //max buffer for an ingress pg
			uint32_t port_max_shared_cell, //max buffer for an ingress port
			uint32_t pg_hdrm_limit, //ingress pg headroom
			uint32_t port_max_pkt_size, //ingress global headroom
			uint32_t q_min_cell,	//egress queue guaranteed buffer
			uint32_t op_uc_port_config1_cell, //egress queue threshold
			uint32_t op_uc_port_config_cell, //egress port threshold
			uint32_t op_buffer_shared_limit_cell, //egress sp threshold
			uint32_t q_shared_alpha_cell,
			uint32_t port_share_alpha_cell,
			uint32_t pg_qcn_threshold);


		void SetMarkingThreshold(uint32_t kmin, uint32_t kmax, double pmax);
		void SetTCPMarkingThreshold(uint32_t kmin, uint32_t kmax);

		bool m_pause_remote[pCnt][qCnt];

		bool ShouldSendCN(uint32_t indev, uint32_t ifindex, uint32_t qIndex);

		uint32_t GetUsedBufferTotal();

		void SetDynamicThreshold();

	protected:
		uint32_t GetIngressSP(uint32_t port, uint32_t pgIndex);
		uint32_t GetEgressSP(uint32_t port, uint32_t qIndex);

	private:

		uint32_t m_maxBufferBytes;
		uint32_t m_usedTotalBytes;


		uint32_t m_usedIngressPGBytes[pCnt][qCnt];
		uint32_t m_usedIngressPortBytes[pCnt];
		uint32_t m_usedIngressSPBytes[4];
		uint32_t m_usedIngressPGHeadroomBytes[pCnt][qCnt];


		uint32_t m_usedEgressQMinBytes[pCnt][qCnt];
		uint32_t m_usedEgressQSharedBytes[pCnt][qCnt];
		uint32_t m_usedEgressPortBytes[pCnt];
		uint32_t m_usedEgressSPBytes[4];

		//ingress params
		uint32_t m_buffer_cell_limit_sp; //ingress sp buffer threshold p.120
		uint32_t m_buffer_cell_limit_sp_shared; //ingress sp buffer shared threshold, nonshare -> share
		uint32_t m_pg_min_cell; //ingress pg guarantee
		uint32_t m_port_min_cell; //ingress port guarantee
		uint32_t m_pg_shared_limit_cell; //max buffer for an ingress pg
		uint32_t m_port_max_shared_cell; //max buffer for an ingress port
		uint32_t m_pg_hdrm_limit; //ingress pg headroom
		uint32_t m_port_max_pkt_size; //ingress global headroom
		//still needs reset limits..
		uint32_t m_port_min_cell_off; // PAUSE off threshold
		uint32_t m_pg_shared_limit_cell_off;
		uint32_t m_global_hdrm_limit;


		//egress params
		uint32_t m_q_min_cell;	//egress queue guaranteed buffer
		uint32_t m_op_uc_port_config1_cell; //egress queue threshold
		uint32_t m_op_uc_port_config_cell; //egress port threshold
		uint32_t m_op_buffer_shared_limit_cell; //egress sp threshold

		//dynamic threshold
		double m_pg_shared_alpha_cell;
		double m_pg_shared_alpha_cell_off_diff;
		double m_port_shared_alpha_cell;
		double m_port_shared_alpha_cell_off_diff;
		bool m_dynamicth;

		//QCN threshold
		uint32_t m_pg_qcn_threshold;
		uint32_t m_pg_qcn_threshold_max;
		double m_pg_qcn_maxp;

		double m_log_start;
		double m_log_end;
		double m_log_step;

		//dctcp
		uint32_t m_dctcp_threshold;
		uint32_t m_dctcp_threshold_max;
		bool m_enable_pfc_on_dctcp;
	};

} // namespace ns3

#endif /* BROADCOM_NODE_H */
