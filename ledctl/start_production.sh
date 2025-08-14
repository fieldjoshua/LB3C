#!/bin/bash
# Production startup script with proper error handling

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== LED Control System - Production Start ===${NC}"
echo

# Check if running on Raspberry Pi
if grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo -e "${GREEN}✓ Running on Raspberry Pi${NC}"
    IS_PI=true
else
    echo -e "${YELLOW}! Not running on Raspberry Pi - using mock mode${NC}"
    IS_PI=false
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Python version: $PYTHON_VERSION"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if rgbmatrix is available
if $IS_PI; then
    python3 -c "import rgbmatrix" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo -e "${RED}✗ RGB Matrix library not found${NC}"
        echo "Please run: ./install_hardware_libs.sh"
        echo "Falling back to mock mode..."
        python3 app.py --mock
        exit 0
    else
        echo -e "${GREEN}✓ RGB Matrix library found${NC}"
    fi
fi

# Check if we need sudo for GPIO
if $IS_PI && [ ! -w /dev/gpiomem ]; then
    echo -e "${YELLOW}! GPIO access requires elevated permissions${NC}"
    echo "Running with sudo..."
    exec sudo -E $(which python3) app.py "$@"
else
    echo -e "${GREEN}✓ GPIO permissions OK${NC}"
    python3 app.py "$@"
fi