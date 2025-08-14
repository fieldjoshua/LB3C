#!/bin/bash
# Quick setup script for Raspberry Pi

echo "=== LED Control System Quick Setup ==="
echo

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "ERROR: Please run this script from the ledctl directory"
    exit 1
fi

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-dev python3-yaml

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies (ignore hardware library errors on first pass)
echo "Installing Python dependencies..."
pip install flask flask-socketio python-socketio eventlet Pillow opencv-python pyyaml numpy requests werkzeug python-dotenv flask-limiter flask-cors marshmallow redis

# Try to install hardware libraries (may fail on non-Pi)
echo "Attempting to install hardware libraries..."
pip install rpi-rgb-led-matrix rpi_ws281x || echo "Hardware libraries failed (normal on non-Pi systems)"

# Setup configuration
if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env
    
    # Generate secret key
    echo "Generating secret key..."
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
    sed -i "s/your-secret-key-here/$SECRET_KEY/g" .env
fi

# Create device.yml if it doesn't exist
if [ ! -f "config/device.yml" ]; then
    echo "Creating device.yml..."
    cp config/device.default.yml config/device.yml
fi

# Create uploads directory
mkdir -p uploads

echo
echo "=== Setup Complete! ==="
echo
echo "To run the LED controller:"
echo "  With hardware:  sudo ./start.sh"
echo "  Mock mode:      python3 app.py --mock"
echo
echo "Access the web interface at http://$(hostname -I | awk '{print $1}'):5000"