/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
//
// Copyright (c) 2006 Georgia Tech Research Corporation
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License version 2 as
// published by the Free Software Foundation;
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the Free Software
// Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
//
// Author: Rajib Bhattacharjea<raj.b@gatech.edu>
//

// Georgia Tech Network Simulator - Round Trip Time Estimation Class
// George F. Riley.  Georgia Tech, Spring 2002


#ifndef RTT_ESTIMATOR_H
#define RTT_ESTIMATOR_H

#include <deque>
#include "ns3/sequence-number.h"
#include "ns3/nstime.h"
#include "ns3/object.h"

namespace ns3 {

/**
 * \ingroup tcp
 *
 * \brief Helper class to store RTT measurements
 */
class RttHistory {
public:
  RttHistory (SequenceNumber32 s, uint64_t c, Time t, uint64_t marked, uint64_t unmarked);
  RttHistory (const RttHistory& h); // Copy constructor
public:
  SequenceNumber32  seq;  // First sequence number in packet sent
  uint64_t        count;  // Number of bytes sent
  Time            time;   // Time this one was sent
  uint64_t        nonMarked; // Number of unmarked packets (needed for DCTCP)
  uint64_t        marked;   // Number of marked packets (needed for DCTCP)
  bool            retx;   // True if this has been retransmitted
};

typedef std::deque<RttHistory> RttHistory_t;

/**
 * \ingroup tcp
 *
 * \brief Base class for all RTT Estimators
 */
class RttEstimator : public Object {
public:
  static TypeId GetTypeId (void);

  RttEstimator();
  RttEstimator (const RttEstimator&);

  virtual ~RttEstimator();

  /**
   * \brief Note that a particular sequence has been sent
   * \param seq the packet sequence number.
   * \param size the packet size.
   * \param number of unmarked packet so far (needed for DCTCP)
   * \param number of marked packets so far (needed for DCTCP)
   */
  virtual void SentSeq (SequenceNumber32 seq, uint32_t size);

  /**
   * \brief Note that a particular ack sequence has been received
   * \param ackSeq the ack sequence number.
   * \param flag is the packet was marked (needed for DCTCP)
   * \param reference to number of unmarked packets so far (needed for DCTCP)
   * \param reference to number of marked packets so far (needed for DCTCP)
   * \param g parameter (needed for DCTCP)
   * \param calculated alpha parameter (needed for DCTCP)
   * \return The measured RTT for this ack.
   */
  virtual Time AckSeq (SequenceNumber32 ackSeq, bool markedFlag);

  /**
   * \brief Clear all history entries
   */
  virtual void ClearSent ();

  /**
   * \brief Add a new measurement to the estimator. Pure virtual function.
   * \param t the new RTT measure.
   */
  virtual void  Measurement (Time t) = 0;

  /**
   * \brief Returns the estimated RTO. Pure virtual function.
   * \return the estimated RTO.
   */
  virtual Time RetransmitTimeout () = 0;

  virtual Ptr<RttEstimator> Copy () const = 0;

  /**
   * \brief Increase the estimation multiplier up to MaxMultiplier.
   */
  virtual void IncreaseMultiplier ();

  /**
   * \brief Resets the estimation multiplier to 1.
   */
  virtual void ResetMultiplier ();

  /**
   * \brief Resets the estimation to its initial state.
   */
  virtual void Reset (SequenceNumber32 seq);

  /**
   * \brief Sets the Minimum RTO.
   * \param minRto The minimum RTO returned by the estimator.
   */
  void SetMinRto (Time minRto);

  /**
   * \brief Get the Minimum RTO.
   * \return The minimum RTO returned by the estimator.
   */
  Time GetMinRto (void) const;

  /**
   * \brief Sets the current RTT estimate (forcefully).
   * \param estimate The current RTT estimate.
   */
  void SetCurrentEstimate (Time estimate);

  /**
   * \brief gets the current RTT estimate.
   * \return The current RTT estimate.
   */
  Time GetCurrentEstimate (void) const;

  /**
   * \brief gets the current Alpha value.
   * \return The current Alpha value.
   */
  double GetAlpha (void) const;

  /**
   * \brief gets the current DCTCP weight value.
   * \return The current parameter g value.
   */
  double GetG (void) const;

  /**
   * \brief sets the current DCTCP weight value.
   * \return The current parameter g value.
   */
  void SetG (double g);

  /**
   * \brief get the number of bytes sent so far
   * \return number of bytes sent
   */
  uint64_t GetBytesSent (void) const;

  void SetExpectedNextSeq(SequenceNumber32 seq)
  {
    m_next = seq;
  }

private:
  SequenceNumber32 m_next;    // Next expected sequence to be sent
  RttHistory_t m_history;     // List of sent packet
  uint16_t m_maxMultiplier;
  Time m_initialEstimatedRtt;

protected:
  Time         m_currentEstimatedRtt;     // Current estimate
  Time         m_minRto;                  // minimum value of the timeout
  uint32_t     m_nSamples;                // Number of samples
  uint16_t     m_multiplier;              // RTO Multiplier
  uint64_t     m_sentBytes;               // Number of bytes sent
  // Parameters needed for DCTCP
  double      m_g;
  uint64_t     m_marked;
  uint64_t     m_nonMarked;
  double      m_alpha;
};

/**
 * \ingroup tcp
 *
 * \brief The "Mean--Deviation" RTT estimator, as discussed by Van Jacobson
 *
 * This class implements the "Mean--Deviation" RTT estimator, as discussed
 * by Van Jacobson and Michael J. Karels, in
 * "Congestion Avoidance and Control", SIGCOMM 88, Appendix A
 *
 */
class RttMeanDeviation : public RttEstimator {
public:
  static TypeId GetTypeId (void);

  RttMeanDeviation ();

  RttMeanDeviation (const RttMeanDeviation&);

  /**
   * \brief Add a new measurement to the estimator.
   * \param measure the new RTT measure.
   */
  void Measurement (Time measure);

  /**
   * \brief Returns the estimated RTO.
   * \return the estimated RTO.
   */
  Time RetransmitTimeout ();

  Ptr<RttEstimator> Copy () const;

  /**
   * \brief Resets sthe estimator.
   */
  virtual void Reset (SequenceNumber32 seq);

  /**
   * \brief Sets the estimator Gain.
   * \param g the gain, where 0 < g < 1.
   */
  void Gain (double g);

private:
  double       m_gain;       // Filter gain
  Time         m_variance;   // Current variance
};
} // namespace ns3

#endif /* RTT_ESTIMATOR_H */
