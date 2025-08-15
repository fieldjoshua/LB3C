# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LightBox3 LED Animation Control System - A unified web-based controller for multiple LED hardware types (HUB75 matrices, WS2811 strips, WLED/ESP32 devices). The system provides real-time animation playback, parameter control, and a responsive web interface.

### Roadmap Features
- User authentication system
- Mobile app for remote control
- Cloud synchronization
- MQTT sync for multi-display setups
- Advanced effects and transitions

## Memories

- PI Details: joshuafield@192.168.0.98 
- Working Directory: LB3C

## Key Commands

### Development
```bash
# Install dependencies (optionally in virtual environment)
python -m venv venv
source venv/bin/activate  # On Linux/Mac
pip install -r ledctl/requirements.txt

# Run using the start script (recommended)
./ledctl/start.sh

# Run directly with sudo for GPIO access
sudo python ledctl/app.py

# Run without hardware (mock mode)
python ledctl/app.py --mock

# Run with alternate config
python ledctl/app.py --config path/to/config.yml
```

### Testing
```bash
# Run structure validation test
python ledctl/test_structure.py

# Run mock device test
python ledctl/test_mock.py

# Run comprehensive unit tests
python ledctl/tests/test_basic.py

# Note: pytest not currently configured - use direct python execution
```

### Production Setup
```bash
# Quick install on Raspberry Pi (RECOMMENDED - handles all dependencies)
curl -sSL https://raw.githubusercontent.com/fieldjoshua/LB3C/main/setup.sh | bash

# The setup.sh script automatically:
# - Detects Raspberry Pi model
# - Installs system dependencies and OpenCV
# - Sets up Python virtual environment
# - Configures Redis for rate limiting
# - Generates security keys
# - Optionally configures nginx reverse proxy
# - Enables required hardware interfaces (SPI, I2C)

# Manual systemd service setup
sudo cp ledctl/systemd/ledctl.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ledctl
sudo systemctl start ledctl

# View service logs
sudo journalctl -u ledctl -f
```

## Architecture Overview

### Core Components

1. **Driver Abstraction Layer** (`core/drivers/`)
   - Base `OutputDevice` class defines interface for all hardware
   - Hardware-specific implementations: `hub75.py`, `ws2811_pi.py`, `wled_udp.py`
   - `DeviceManager` handles driver registration and switching

2. **Animation Pipeline** (`core/`)
   - `frames.py`: Loads and processes GIF/PNG/MP4 files
   - `gamma.py`: Color correction and RGB balance
   - `playlists.py`: Sequential animation playback
   - `mapper.py`: Coordinate transformation for complex LED layouts

3. **Web Interface**
   - Flask + Socket.IO server (`app.py`)
   - Real-time parameter updates via WebSocket
   - File upload and playlist management
   - Responsive Bootstrap UI

### Configuration System

All hardware and rendering settings in `config/device.default.yml`:
- Device selection and hardware-specific parameters
- Rendering options (scaling, FPS, gamma, transforms)
- Server settings (host, port, upload limits)

### Hardware Support

- **HUB75**: Uses `rpi-rgb-led-matrix` library, requires Adafruit HAT
- **WS2811**: Uses `rpi_ws281x` library, requires root/sudo
- **WLED**: Network control via UDP packets

## Important Implementation Details

1. **GPIO Access**: WS2811 and HUB75 drivers require sudo privileges on Raspberry Pi

2. **Frame Processing**: All animations go through unified pipeline in `frames.py` before hardware output

3. **Real-time Updates**: Parameter changes (brightness, speed, etc.) apply immediately without restart

4. **Error Handling**: Hardware failures gracefully degrade - server continues running if device disconnects

5. **File Uploads**: Media files stored in `uploads/` directory, validated by extension

## Common Tasks

### Adding New Hardware Support
1. Create new driver class inheriting from `OutputDevice` in `core/drivers/`
2. Implement required methods: `open()`, `close()`, `set_brightness()`, `draw_rgb_frame()`
3. Register with `DeviceManager.register_device()`
4. Add configuration section to `device.default.yml`

### Adding New Animation Effects
1. Create procedural animation class inheriting from `ProceduralAnimation` in `core/frames.py`
2. Implement `generate_frame()` method
3. Add to animation selection in web interface

### Debugging Hardware Issues
- Check logs for driver initialization errors
- Verify GPIO permissions (run with sudo)
- Test with `--mock` flag to isolate hardware problems
- Hardware libraries fail gracefully on non-Pi systems

### Troubleshooting Common Issues

**Permission Denied**
```bash
# Logout and login for group changes to take effect
# Or run with sudo:
sudo ./start.sh
```

**Import Errors**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

**Hardware Not Working**
1. Check connections
2. Verify SPI/I2C enabled: `ls /dev/spi* /dev/i2c*`
3. Check dmesg for errors: `sudo dmesg | tail -50`
4. Try mock mode first: `python app.py --mock`

**Service Won't Start**
```bash
# Check logs
sudo journalctl -u ledctl -n 100
# Test manually
cd /home/pi/LB3C/ledctl
sudo ./start.sh
```

**RGB Matrix Library Build Issues**
If pip installation fails for rpi-rgb-led-matrix:
```bash
# Build from source
git clone https://github.com/hzeller/rpi-rgb-led-matrix.git
cd rpi-rgb-led-matrix
make build-python PYTHON=$(which python3)
sudo make install-python PYTHON=$(which python3)
```

## Security Configuration

The system includes production-grade security features configured via environment variables:

1. **Initial Setup**:
   ```bash
   # Copy environment template
   cp ledctl/.env.example ledctl/.env
   
   # Generate secret key
   python ledctl/generate_secret.py
   
   # Generate API key
   python ledctl/generate_api_key.py
   ```

2. **API Authentication**: Configure `API_KEYS` in `.env` for protected endpoints
3. **Rate Limiting**: Automatic rate limiting per IP (configurable in `core/security.py`)

## REST API Reference

Key API endpoints (`/api/v1/`):
- **System Control**: `/status`, `/config`, `/logs`
- **Device Management**: `/device/list`, `/device/switch`, `/device/brightness`
- **Animation Control**: `/play`, `/stop`, `/next`, `/playlist`
- **File Management**: `/upload`, `/files`, `/delete`

All endpoints support API key authentication via `X-API-Key` header. Rate limits:
- Public endpoints: 60 requests/minute
- Authenticated: 300 requests/minute
- Upload endpoints: 10 requests/minute

See `docs/API.md` for complete API documentation.

## WebSocket Events

The server emits/handles these Socket.IO events:
- `frame_info`: Current frame number during playback
- `playing`/`stopped`: Playback state changes
- `parameter_updated`: Confirms parameter changes
- `device_switched`: Device switching confirmation
- `error`: Error messages to client

## Production Deployment

### Environment Variables (.env)
```bash
FLASK_ENV=production  # or development
FLASK_SECRET_KEY=your-generated-secret-key
API_AUTH_ENABLED=True
API_KEYS=comma,separated,api,keys
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
```

### Nginx Reverse Proxy (optional)
```nginx
location / {
    proxy_pass http://localhost:5000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

### Security Headers
Automatically applied in production mode:
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security (when HTTPS)

## Known Limitations

- Maximum frame rate depends on hardware (HUB75: ~60fps, WS2811: ~30fps)
- Large video files may cause memory issues on Pi
- Network latency affects WLED responsiveness
- Redis required for distributed rate limiting (falls back to memory)
- Hardware libraries only work on Raspberry Pi (mock mode available)