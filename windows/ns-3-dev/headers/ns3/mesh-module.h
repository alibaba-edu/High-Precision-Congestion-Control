
#ifdef NS3_MODULE_COMPILATION
# error "Do not include ns3 module aggregator headers from other modules; these are meant only for end user scripts."
#endif

#ifndef NS3_MODULE_MESH
    

// Module headers:
#include "dot11s-installer.h"
#include "dot11s-mac-header.h"
#include "flame-header.h"
#include "flame-installer.h"
#include "flame-protocol-mac.h"
#include "flame-protocol.h"
#include "flame-rtable.h"
#include "hwmp-protocol.h"
#include "hwmp-rtable.h"
#include "ie-dot11s-beacon-timing.h"
#include "ie-dot11s-configuration.h"
#include "ie-dot11s-id.h"
#include "ie-dot11s-metric-report.h"
#include "ie-dot11s-peer-management.h"
#include "ie-dot11s-peering-protocol.h"
#include "ie-dot11s-perr.h"
#include "ie-dot11s-prep.h"
#include "ie-dot11s-preq.h"
#include "ie-dot11s-rann.h"
#include "mesh-helper.h"
#include "mesh-information-element-vector.h"
#include "mesh-information-element.h"
#include "mesh-l2-routing-protocol.h"
#include "mesh-point-device.h"
#include "mesh-stack-installer.h"
#include "mesh-wifi-beacon.h"
#include "mesh-wifi-interface-mac-plugin.h"
#include "mesh-wifi-interface-mac.h"
#include "peer-link-frame.h"
#include "peer-link.h"
#include "peer-management-protocol.h"
#endif
