#!/bin/bash
#
# LB3C LED Control System - Raspberry Pi Setup Script
# This script automates the installation process on Raspberry Pi
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/fieldjoshua/LB3C.git"
INSTALL_DIR="/home/pi/LB3C"
SERVICE_NAME="ledctl"

# Print banner
echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════╗"
echo "║       LB3C LED Control System Installer       ║"
echo "║          For Raspberry Pi OS (Bullseye+)      ║"
echo "╚═══════════════════════════════════════════════╝"
echo -e "${NC}"

# Check if running on Raspberry Pi
check_raspberry_pi() {
    echo -e "${YELLOW}Checking system...${NC}"
    if [ ! -f /proc/device-tree/model ]; then
        echo -e "${RED}Warning: This doesn't appear to be a Raspberry Pi${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        MODEL=$(cat /proc/device-tree/model)
        echo -e "${GREEN}✓ Detected: $MODEL${NC}"
    fi
}

# Check if running as pi user
check_user() {
    if [ "$USER" != "pi" ]; then
        echo -e "${YELLOW}Warning: Not running as 'pi' user${NC}"
        echo "Installation directory will be: /home/$USER/LB3C"
        INSTALL_DIR="/home/$USER/LB3C"
        read -p "Continue? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# Update system packages
update_system() {
    echo -e "\n${YELLOW}Updating system packages...${NC}"
    sudo apt-get update
    sudo apt-get upgrade -y
}

# Install system dependencies
install_dependencies() {
    echo -e "\n${YELLOW}Installing system dependencies...${NC}"
    
    # Core dependencies
    sudo apt-get install -y \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        build-essential \
        cmake \
        pkg-config \
        libjpeg-dev \
        libtiff5-dev \
        libpng-dev \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev \
        libv4l-dev \
        libxvidcore-dev \
        libx264-dev \
        libatlas-base-dev \
        gfortran \
        redis-server
    
    # Enable hardware interfaces
    echo -e "\n${YELLOW}Enabling hardware interfaces...${NC}"
    sudo raspi-config nonint do_spi 0  # Enable SPI
    sudo raspi-config nonint do_i2c 0  # Enable I2C
    
    # Add user to gpio group
    sudo usermod -a -G gpio,spi,i2c $USER
    echo -e "${GREEN}✓ Added $USER to gpio, spi, and i2c groups${NC}"
}

# Clone or update repository
setup_repository() {
    echo -e "\n${YELLOW}Setting up repository...${NC}"
    
    if [ -d "$INSTALL_DIR" ]; then
        echo "Found existing installation at $INSTALL_DIR"
        read -p "Update existing installation? (Y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            echo "Using existing installation"
        else
            cd "$INSTALL_DIR"
            git pull origin main
            echo -e "${GREEN}✓ Repository updated${NC}"
        fi
    else
        echo "Cloning repository..."
        git clone "$REPO_URL" "$INSTALL_DIR"
        cd "$INSTALL_DIR"
        echo -e "${GREEN}✓ Repository cloned${NC}"
    fi
}

# Setup Python virtual environment
setup_python_env() {
    echo -e "\n${YELLOW}Setting up Python environment...${NC}"
    cd "$INSTALL_DIR/ledctl"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip wheel setuptools
    
    # Install Python dependencies
    echo -e "\n${YELLOW}Installing Python packages...${NC}"
    
    # Install packages that don't require hardware first
    pip install flask flask-socketio python-socketio[client] eventlet
    pip install Pillow pyyaml numpy requests werkzeug python-dotenv
    pip install flask-limiter flask-cors marshmallow redis
    
    # Try to install hardware libraries (may fail on non-Pi systems)
    echo -e "\n${YELLOW}Installing hardware libraries...${NC}"
    
    # OpenCV (this can take a while on Pi)
    pip install opencv-python || {
        echo -e "${YELLOW}OpenCV installation failed, trying alternative...${NC}"
        sudo apt-get install -y python3-opencv
    }
    
    # RGB Matrix library
    pip install rpi-rgb-led-matrix || {
        echo -e "${YELLOW}RGB Matrix library failed, building from source...${NC}"
        install_rgb_matrix_from_source
    }
    
    # WS281x library
    pip install rpi_ws281x || {
        echo -e "${YELLOW}WS281x library failed, you may need to install manually${NC}"
    }
    
    echo -e "${GREEN}✓ Python packages installed${NC}"
}

# Build RGB Matrix library from source if pip fails
install_rgb_matrix_from_source() {
    cd /tmp
    git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
    cd rpi-rgb-led-matrix
    make build-python PYTHON=$(which python3)
    sudo make install-python PYTHON=$(which python3)
    cd "$INSTALL_DIR/ledctl"
}

# Setup configuration files
setup_config() {
    echo -e "\n${YELLOW}Setting up configuration...${NC}"
    cd "$INSTALL_DIR/ledctl"
    
    # Copy default config if needed
    if [ ! -f "config/device.yml" ]; then
        cp config/device.default.yml config/device.yml
        echo -e "${GREEN}✓ Created device.yml from default${NC}"
    fi
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        cp .env.example .env
        
        # Generate secret key
        SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')
        sed -i "s/your-secret-key-here-generate-with-python-secrets/$SECRET_KEY/" .env
        echo -e "${GREEN}✓ Generated secure secret key${NC}"
        
        # Set production environment
        sed -i "s/FLASK_ENV=development/FLASK_ENV=production/" .env
        sed -i "s/FLASK_DEBUG=False/FLASK_DEBUG=False/" .env
        
        echo -e "${GREEN}✓ Created .env file${NC}"
        echo -e "${YELLOW}Note: Edit .env to customize settings${NC}"
    fi
    
    # Create uploads directory
    mkdir -p uploads
    chmod 755 uploads
}

# Setup systemd service
setup_systemd() {
    echo -e "\n${YELLOW}Setting up systemd service...${NC}"
    
    # Update service file with correct paths
    sudo sed -i "s|/home/pi/ledctl|$INSTALL_DIR/ledctl|g" "$INSTALL_DIR/ledctl/systemd/ledctl.service"
    sudo sed -i "s|User=pi|User=$USER|g" "$INSTALL_DIR/ledctl/systemd/ledctl.service"
    
    # Copy service file
    sudo cp "$INSTALL_DIR/ledctl/systemd/ledctl.service" /etc/systemd/system/
    
    # Reload systemd
    sudo systemctl daemon-reload
    
    echo -e "${GREEN}✓ Systemd service installed${NC}"
    
    # Ask about enabling service
    read -p "Enable LED control service to start on boot? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        sudo systemctl enable $SERVICE_NAME
        echo -e "${GREEN}✓ Service enabled${NC}"
    fi
}

# Configure Redis (optional)
setup_redis() {
    echo -e "\n${YELLOW}Configuring Redis for rate limiting...${NC}"
    
    # Enable and start Redis
    sudo systemctl enable redis-server
    sudo systemctl start redis-server
    
    # Test Redis connection
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Redis is running${NC}"
        
        # Update .env to use Redis
        sed -i "s|REDIS_URL=redis://localhost:6379|REDIS_URL=redis://localhost:6379|g" "$INSTALL_DIR/ledctl/.env"
    else
        echo -e "${YELLOW}Redis not available, will use memory-based rate limiting${NC}"
    fi
}

# Setup nginx (optional)
setup_nginx() {
    read -p "Install and configure nginx reverse proxy? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "\n${YELLOW}Installing nginx...${NC}"
        sudo apt-get install -y nginx
        
        # Create nginx config
        cat > /tmp/ledctl.nginx << EOF
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /socket.io {
        proxy_pass http://localhost:5000/socket.io;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
    }
}
EOF
        
        sudo mv /tmp/ledctl.nginx /etc/nginx/sites-available/ledctl
        sudo ln -sf /etc/nginx/sites-available/ledctl /etc/nginx/sites-enabled/
        sudo rm -f /etc/nginx/sites-enabled/default
        
        sudo systemctl restart nginx
        echo -e "${GREEN}✓ Nginx configured${NC}"
    fi
}

# Test installation
test_installation() {
    echo -e "\n${YELLOW}Testing installation...${NC}"
    cd "$INSTALL_DIR/ledctl"
    
    # Test Python imports
    source venv/bin/activate
    python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from core.config import Config
    from core.drivers import DeviceManager
    print('✓ Core modules OK')
except Exception as e:
    print(f'✗ Import error: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Installation test passed${NC}"
    else
        echo -e "${RED}✗ Installation test failed${NC}"
        return 1
    fi
}

# Final setup steps
final_steps() {
    echo -e "\n${BLUE}════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Installation Complete!${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════${NC}"
    
    echo -e "\n${YELLOW}Next steps:${NC}"
    echo "1. Configure your LED hardware in: $INSTALL_DIR/ledctl/config/device.yml"
    echo "2. Edit environment settings in: $INSTALL_DIR/ledctl/.env"
    echo "3. Test with mock device: cd $INSTALL_DIR/ledctl && ./start.sh"
    echo "4. Start the service: sudo systemctl start $SERVICE_NAME"
    echo "5. View logs: sudo journalctl -u $SERVICE_NAME -f"
    
    IP=$(hostname -I | cut -d' ' -f1)
    echo -e "\n${GREEN}Web interface will be available at:${NC}"
    echo "  http://$IP:5000 (direct)"
    if systemctl is-active --quiet nginx; then
        echo "  http://$IP (via nginx)"
    fi
    
    echo -e "\n${YELLOW}Important:${NC}"
    echo "- You may need to logout and login again for GPIO permissions"
    echo "- Use 'sudo' when running with hardware access"
    echo "- Check the docs at: $INSTALL_DIR/ledctl/docs/"
}

# Main installation flow
main() {
    check_raspberry_pi
    check_user
    
    echo -e "\n${YELLOW}This will install LB3C LED Control System${NC}"
    echo "Installation directory: $INSTALL_DIR"
    read -p "Continue? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        exit 0
    fi
    
    update_system
    install_dependencies
    setup_repository
    setup_python_env
    setup_config
    setup_systemd
    setup_redis
    setup_nginx
    
    if test_installation; then
        final_steps
    else
        echo -e "${RED}Installation completed with errors${NC}"
        echo "Check the logs and try running manually"
        exit 1
    fi
}

# Run main function
main