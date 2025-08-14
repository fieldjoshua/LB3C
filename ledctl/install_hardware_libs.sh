#!/bin/bash
# Install hardware libraries for Raspberry Pi LED control

echo "=== Installing Hardware Libraries for LED Control ==="
echo

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/cpuinfo; then
    echo "Warning: Not running on Raspberry Pi - hardware libraries may not work"
fi

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y python3-dev python3-pillow git build-essential

# Install RGB Matrix library from source
echo "Building RGB Matrix library from source..."
cd /tmp
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix

# Build the library
make build-python PYTHON=$(which python3)
sudo make install-python PYTHON=$(which python3)

# Install WS2811 library
echo "Installing WS2811 library..."
sudo pip3 install rpi_ws281x

# Set up GPIO permissions (alternative to running as root)
echo "Setting up GPIO permissions..."
sudo groupadd -f gpio
sudo usermod -a -G gpio $USER

# Create udev rules for GPIO access
sudo tee /etc/udev/rules.d/99-gpio.rules > /dev/null << EOF
SUBSYSTEM=="bcm2835-gpiomem", KERNEL=="gpiomem", GROUP="gpio", MODE="0660"
SUBSYSTEM=="gpio", KERNEL=="gpiochip*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:gpio /sys/class/gpio/export /sys/class/gpio/unexport ; chmod 220 /sys/class/gpio/export /sys/class/gpio/unexport'"
SUBSYSTEM=="gpio", KERNEL=="gpio*", ACTION=="add", PROGRAM="/bin/sh -c 'chown root:gpio /sys%p/active_low /sys%p/direction /sys%p/edge /sys%p/value ; chmod 660 /sys%p/active_low /sys%p/direction /sys%p/edge /sys%p/value'"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

echo
echo "=== Installation Complete ==="
echo
echo "IMPORTANT: You need to log out and back in for group changes to take effect"
echo
echo "After logging back in, you can run without sudo:"
echo "  python3 app.py"
echo
echo "If you still get permission errors, you may need to run with sudo initially"