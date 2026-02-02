#!/bin/bash
# Run script for HPCC simulator
# Usage: ./run.sh <config_file>
# Example: ./run.sh mix/configs/config_two_senders_per_node.txt

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check arguments
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: No config file specified${NC}"
    echo ""
    echo "Usage: $0 <config_file>"
    echo ""
    echo "Examples:"
    echo "  $0 mix/configs/config_two_senders_per_node.txt"
    echo "  $0 mix/configs/config_two_senders.txt"
    exit 1
fi

CONFIG_FILE="$1"

# Detect if running inside container or on host
if [ -d "/workspace/simulation" ]; then
    # Inside container
    BASE_DIR="/workspace/simulation"
else
    # On host - get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    BASE_DIR="$SCRIPT_DIR"
fi

# Resolve to absolute path
if [[ "$CONFIG_FILE" != /* ]]; then
    # Remove 'simulation/' prefix if present (user might include it when running from parent dir)
    CONFIG_FILE="${CONFIG_FILE#simulation/}"
    
    # Try current directory first
    if [ -f "$CONFIG_FILE" ]; then
        CONFIG_FILE="$(realpath "$CONFIG_FILE")"
    # Try relative to base directory
    elif [ -f "$BASE_DIR/$CONFIG_FILE" ]; then
        CONFIG_FILE="$BASE_DIR/$CONFIG_FILE"
    fi
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Config file not found${NC}"
    echo ""
    echo "Searched for: $1"
    echo "Base directory: $BASE_DIR"
    echo ""
    echo "Hint: Run this script from inside the Docker container:"
    echo "  docker compose exec hpcc bash"
    echo "  cd /workspace/simulation"
    echo "  ./run.sh mix/configs/config_two_senders_per_node.txt"
    exit 1
fi

# Check if executable exists
EXECUTABLE="./build/scratch/third"
if [ ! -d "/workspace/simulation" ]; then
    # On host - need to run via Docker
    echo -e "${RED}Error: This script must be run inside the Docker container${NC}"
    echo ""
    echo "To run the simulation:"
    echo "  1. Enter the container:"
    echo "     docker compose exec hpcc bash"
    echo ""
    echo "  2. Navigate to simulation directory:"
    echo "     cd /workspace/simulation"
    echo ""
    echo "  3. Run the script:"
    echo "     ./run.sh mix/configs/config_two_senders_per_node.txt"
    exit 1
fi

if [ ! -f "$EXECUTABLE" ]; then
    echo -e "${RED}Error: Executable not found: $EXECUTABLE${NC}"
    echo -e "${YELLOW}Please build first with: ./build.sh${NC}"
    exit 1
fi

# Set library path
export LD_LIBRARY_PATH=/workspace/simulation/build:$LD_LIBRARY_PATH

echo -e "${BLUE}=== HPCC Simulator Run Script ===${NC}"
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  File: $CONFIG_FILE"
echo ""

# Optional: clear old result files
if [ "$2" == "clean" ]; then
    echo -e "${YELLOW}Clearing old result files...${NC}"
    rm -f /workspace/results/data/*.txt
    echo -e "${GREEN}✓ Old results cleared${NC}"
    echo ""
fi

echo -e "${BLUE}Running simulation...${NC}"
echo ""

# Run the simulator
# Note: ./build/scratch/third is the compiled executable (not a folder)
#       The config file is passed as a command-line argument
./build/scratch/third "$CONFIG_FILE"

echo ""
echo -e "${GREEN}✓ Simulation completed!${NC}"
echo ""
echo "Results saved to: /workspace/results/data/"
echo ""
echo "Next step: Generate plots with:"
echo "  cd /workspace && python3 results/run_all_plots.py"
