# LB3C - LED Animation Control System

A unified web-based control system for multiple LED hardware types including HUB75 matrices, WS2811 strips, and WLED/ESP32 devices.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Raspberry%20Pi-red.svg)

## Features

- **Multi-Hardware Support**: Control HUB75 LED matrices, WS2811 addressable strips, and WLED network devices
- **Web Interface**: Real-time control via responsive web browser interface
- **Animation Playback**: Support for GIF, PNG, JPG, and MP4 files with smooth transitions
- **Live Control**: Adjust brightness, speed, gamma correction, and RGB balance in real-time
- **Playlist Management**: Create and manage animation playlists
- **Production Ready**: Includes systemd service, error handling, and logging

## Quick Start

### Prerequisites

- Raspberry Pi (3B+ or newer recommended)
- Python 3.8+
- LED hardware (HUB75 matrix, WS2811 strips, or WLED device)

### Installation

```bash
# Clone the repository
git clone https://github.com/fieldjoshua/LB3C.git
cd LB3C

# Install dependencies
cd ledctl
pip3 install -r requirements.txt

# Copy and configure settings
cp config/device.default.yml config/device.yml
# Edit config/device.yml with your hardware settings
```

### Running

```bash
# Run with hardware (requires sudo)
sudo python3 ledctl/app.py

# Run without hardware (mock mode)
python3 ledctl/app.py --mock
```

Access the web interface at `http://<raspberry-pi-ip>:5000`

## Hardware Setup

### HUB75 LED Matrix
- Requires [Adafruit RGB Matrix HAT](https://www.adafruit.com/product/2345)
- Connect matrix to HAT following Adafruit's guide
- Configure matrix dimensions in `config/device.yml`

### WS2811 LED Strip
- Connect data line to GPIO 18 (configurable)
- Use 5V level shifter for reliable operation
- Configure LED count and mapping in config

### WLED/ESP32
- No physical connection required
- Configure device IP address and port
- Supports WARLS, DRGB, and DNRGB protocols

## Documentation

- [Development Guide](CLAUDE.md) - Architecture and development instructions
- [API Reference](docs/api.md) - WebSocket and REST API documentation
- [Hardware Guide](docs/hardware.md) - Detailed hardware setup instructions

## Project Structure

```
LB3C/
├── ledctl/                # Main application
│   ├── app.py            # Flask server
│   ├── core/             # Core modules
│   │   ├── drivers/      # Hardware drivers
│   │   ├── frames.py     # Animation processing
│   │   └── playlists.py  # Playlist management
│   ├── static/           # Frontend assets
│   ├── templates/        # HTML templates
│   └── config/           # Configuration files
├── CLAUDE.md             # Development instructions
└── README.md             # This file
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature-name`)
3. Commit your changes (`git commit -am 'Add feature'`)
4. Push to the branch (`git push origin feature-name`)
5. Create a Pull Request

## Roadmap

- [ ] User authentication system
- [ ] Mobile app for remote control
- [ ] Support for more LED types
- [ ] Cloud synchronization
- [ ] Advanced effects and transitions

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [rpi-rgb-led-matrix](https://github.com/hzeller/rpi-rgb-led-matrix) for HUB75 support
- [rpi_ws281x](https://github.com/jgarff/rpi_ws281x) for WS2811 support
- [WLED](https://github.com/Aircoookie/WLED) for protocol compatibility