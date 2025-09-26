
#ifdef NS3_MODULE_COMPILATION
# error "Do not include ns3 module aggregator headers from other modules; these are meant only for end user scripts."
#endif

#ifndef NS3_MODULE_SPECTRUM
    

// Module headers:
#include "adhoc-aloha-noack-ideal-phy-helper.h"
#include "aloha-noack-mac-header.h"
#include "aloha-noack-net-device.h"
#include "constant-spectrum-propagation-loss.h"
#include "friis-spectrum-propagation-loss.h"
#include "half-duplex-ideal-phy-signal-parameters.h"
#include "half-duplex-ideal-phy.h"
#include "microwave-oven-spectrum-value-helper.h"
#include "multi-model-spectrum-channel.h"
#include "non-communicating-net-device.h"
#include "single-model-spectrum-channel.h"
#include "spectrum-analyzer-helper.h"
#include "spectrum-analyzer.h"
#include "spectrum-channel.h"
#include "spectrum-converter.h"
#include "spectrum-error-model.h"
#include "spectrum-helper.h"
#include "spectrum-interference.h"
#include "spectrum-model-300kHz-300GHz-log.h"
#include "spectrum-model-ism2400MHz-res1MHz.h"
#include "spectrum-model.h"
#include "spectrum-phy.h"
#include "spectrum-propagation-loss-model.h"
#include "spectrum-signal-parameters.h"
#include "spectrum-test.h"
#include "spectrum-value.h"
#include "waveform-generator-helper.h"
#include "waveform-generator.h"
#include "wifi-spectrum-value-helper.h"
#endif
