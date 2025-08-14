#!/bin/bash
# LED Animation Control System - Startup Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}LED Animation Control System${NC}"
echo "================================"

# Check if running on Raspberry Pi
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    echo -e "Hardware: ${YELLOW}$MODEL${NC}"
else
    echo -e "${YELLOW}Warning: Not running on Raspberry Pi${NC}"
fi

# Check for virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check for .env file and secret key
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Please copy .env.example to .env and configure it:"
    echo "  cp .env.example .env"
    echo "  python3 generate_secret.py"
    exit 1
fi

# Check if FLASK_SECRET_KEY is set
if ! grep -q "FLASK_SECRET_KEY=" .env || grep -q "FLASK_SECRET_KEY=your-secret-key-here" .env; then
    echo -e "${RED}ERROR: FLASK_SECRET_KEY not configured!${NC}"
    echo "Generate a secret key with:"
    echo "  python3 generate_secret.py"
    echo "Then add it to your .env file"
    exit 1
fi

# Check if running as root/sudo
if [ "$EUID" -ne 0 ]; then 
    echo -e "${YELLOW}Note: Not running as root. Hardware access may fail.${NC}"
    echo "For hardware access, run: sudo ./start.sh"
    echo ""
    read -p "Continue without hardware access? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
    # Run without sudo (mock mode)
    python3 app.py --mock
else
    # Run with hardware access
    echo -e "${GREEN}Starting with hardware access...${NC}"
    python3 app.py
fi