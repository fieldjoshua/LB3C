# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LightBox3 LED Animation Control System - A unified web-based controller for multiple LED hardware types (HUB75 matrices, WS2811 strips, WLED/ESP32 devices). The system provides real-time animation playback, parameter control, and a responsive web interface.

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

## Production Deployment

1. Copy systemd service file: `sudo cp ledctl/systemd/ledctl.service /etc/systemd/system/`
2. Enable auto-start: `sudo systemctl enable ledctl`
3. Start service: `sudo systemctl start ledctl`
4. View logs: `sudo journalctl -u ledctl -f`
5. Set up nginx reverse proxy for public access

## WebSocket Events

The server emits/handles these Socket.IO events:
- `frame_info`: Current frame number during playback
- `playing`/`stopped`: Playback state changes
- `parameter_updated`: Confirms parameter changes
- `device_switched`: Device switching confirmation
- `error`: Error messages to client

## Known Limitations

- Maximum frame rate depends on hardware (HUB75: ~60fps, WS2811: ~30fps)
- Large video files may cause memory issues on Pi
- Network latency affects WLED responsiveness
- Flask secret key is hardcoded (TODO: use environment variable)
- Logging configuration in YAML not yet implemented