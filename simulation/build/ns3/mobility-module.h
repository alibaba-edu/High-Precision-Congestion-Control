
#ifdef NS3_MODULE_COMPILATION
# error "Do not include ns3 module aggregator headers from other modules; these are meant only for end user scripts."
#endif

#ifndef NS3_MODULE_MOBILITY
    

// Module headers:
#include "box.h"
#include "constant-acceleration-mobility-model.h"
#include "constant-position-mobility-model.h"
#include "constant-velocity-helper.h"
#include "constant-velocity-mobility-model.h"
#include "gauss-markov-mobility-model.h"
#include "hierarchical-mobility-model.h"
#include "mobility-helper.h"
#include "mobility-model.h"
#include "ns2-mobility-helper.h"
#include "position-allocator.h"
#include "random-direction-2d-mobility-model.h"
#include "random-walk-2d-mobility-model.h"
#include "random-waypoint-mobility-model.h"
#include "rectangle.h"
#include "steady-state-random-waypoint-mobility-model.h"
#include "waypoint-mobility-model.h"
#include "waypoint.h"
#endif
