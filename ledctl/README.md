# LED Animation Control System (LightBox3)

A unified web-based control system for multiple LED hardware types including HUB75 matrices, WS2811 strips, and WLED/ESP32 devices.

## Features

- **Multiple Hardware Support**: HUB75 LED matrices, WS2811 addressable strips, WLED network devices
- **Web Interface**: Real-time control via browser with responsive design
- **Animation Support**: GIF, PNG, JPG, MP4 playback with smooth transitions
- **Live Parameter Control**: Brightness, speed, gamma correction, RGB balance
- **File Management**: Upload and organize animations via web interface
- **Production Ready**: systemd service, error handling, logging

## Quick Start

### Installation

1. Clone the repository:
```bash
cd /home/pi
git clone <repository-url> ledctl
cd ledctl
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Configure your hardware:
```bash
cp config/device.default.yml config/device.yml
# Edit config/device.yml with your hardware settings
```

### Running

```bash
# Run with sudo for GPIO access
sudo python3 app.py

# Or run without hardware (mock mode)
python3 app.py --mock
```

Access the web interface at `http://<raspberry-pi-ip>:5000`

### Auto-start on Boot

```bash
# Copy systemd service
sudo cp systemd/ledctl.service /etc/systemd/system/

# Enable and start service
sudo systemctl enable ledctl
sudo systemctl start ledctl
```

## Hardware Setup

### HUB75 LED Matrix
- Requires Adafruit RGB Matrix HAT or compatible
- Connect to Pi GPIO headers
- Configure dimensions in `config/device.yml`

### WS2811 LED Strip
- Connect data to GPIO 18 (default)
- Requires 5V level shifter for reliable operation
- Configure LED count and mapping in config

### WLED/ESP32
- Configure network IP and port
- Supports WARLS, DRGB, DNRGB protocols
- No physical connection required

## Configuration

Edit `config/device.yml` to set:
- Active device type
- Hardware-specific parameters
- Rendering options (gamma, scaling, FPS)
- Server settings

## Testing

Run basic tests without hardware:
```bash
python3 tests/test_basic.py
```

## Troubleshooting

- **Permission Denied**: Run with `sudo` for GPIO access
- **Import Errors**: Ensure you're in the correct directory
- **Connection Failed**: Check network settings for WLED
- **No Output**: Verify GPIO connections and power supply

## Development

See [CLAUDE.md](../CLAUDE.md) for detailed development guidance.

## License

[Your License Here]