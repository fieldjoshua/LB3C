# LB3C Installation Guide for Raspberry Pi

## Quick Install (Recommended)

Run this single command on your Raspberry Pi:

```bash
curl -sSL https://raw.githubusercontent.com/fieldjoshua/LB3C/main/setup.sh | bash
```

This will:
- Install all dependencies
- Set up Python environment
- Configure the service
- Create necessary files
- Enable hardware interfaces

## Manual Installation

### 1. Prerequisites

- Raspberry Pi 3B+ or newer
- Raspberry Pi OS (Bullseye or newer)
- Internet connection
- At least 2GB free space

### 2. System Setup

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install dependencies
sudo apt-get install -y python3-pip python3-venv git redis-server

# Enable hardware interfaces
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0

# Add user to hardware groups
sudo usermod -a -G gpio,spi,i2c $USER
```

### 3. Clone Repository

```bash
cd ~
git clone https://github.com/fieldjoshua/LB3C.git
cd LB3C/ledctl
```

### 4. Python Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 5. Configuration

```bash
# Copy config files
cp config/device.default.yml config/device.yml
cp .env.example .env

# Generate secret key
python generate_secret.py

# Edit .env file
nano .env
```

### 6. Test Installation

```bash
# Test with mock device
./start.sh

# Or run directly
python app.py --mock
```

### 7. Service Setup

```bash
# Install service
sudo cp systemd/ledctl.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ledctl
sudo systemctl start ledctl

# Check status
sudo systemctl status ledctl
```

## Hardware Configuration

### HUB75 LED Matrix

Edit `config/device.yml`:

```yaml
device: HUB75

devices:
  HUB75:
    cols: 64
    rows: 32
    chain: 1
    parallel: 1
    gpio_slowdown: 2
    pwm_bits: 11
```

### WS2811 LED Strip

```yaml
device: WS2811

devices:
  WS2811:
    led_count: 300
    gpio_pin: 18
    strip_type: WS2811_STRIP_GRB
    brightness: 255
```

## Troubleshooting

### Permission Denied

```bash
# Logout and login again for group changes
# Or run with sudo:
sudo ./start.sh
```

### Import Errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Hardware Not Working

1. Check connections
2. Verify SPI/I2C enabled: `ls /dev/spi* /dev/i2c*`
3. Check dmesg for errors: `sudo dmesg | tail -50`
4. Try mock mode first: `python app.py --mock`

### Service Won't Start

```bash
# Check logs
sudo journalctl -u ledctl -n 100

# Check permissions
ls -la /home/pi/LB3C/ledctl/

# Test manually
cd /home/pi/LB3C/ledctl
sudo ./start.sh
```

## Access Web Interface

After installation:

- Direct: `http://<pi-ip>:5000`
- With nginx: `http://<pi-ip>`

Find your Pi's IP:
```bash
hostname -I
```

## Next Steps

1. Upload animations via web interface
2. Configure API keys for security
3. Set up monitoring
4. Join animations in playlists

## Support

- GitHub Issues: https://github.com/fieldjoshua/LB3C/issues
- API Docs: `/ledctl/docs/API.md`
- Development Guide: `/CLAUDE.md`