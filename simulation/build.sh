#!/bin/bash
# Build script for HPCC simulator
# This script compiles the ns-3 simulation with all modules and custom code

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== HPCC Simulator Build Script ===${NC}"
echo ""

# Set library path for runtime
export LD_LIBRARY_PATH=/workspace/simulation/build:$LD_LIBRARY_PATH

# Check if waf exists
if [ ! -f "./waf" ]; then
    echo "Error: waf not found. Please run from simulation/ directory."
    exit 1
fi

echo -e "${BLUE}Building simulation...${NC}"
echo ""

# Run waf build
./waf build

echo ""
echo -e "${GREEN}✓ Build successful!${NC}"
echo ""
echo "Executable location: ./build/scratch/third"
echo "Ready to run with: ./run.sh <config_file>"
