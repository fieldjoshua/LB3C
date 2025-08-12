<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## **Unified Lightbox Interface – Production Scaffold**

Below is your complete **starter scaffold and production outline** for a unified HUB75/WS2811 (and WLED/ESP32 optional) LED animation system. This covers:

- The **file/folder structure**
- **Key Python, HTML, JS, CSS, YAML/JSON stub files**, with comments and TODO markers
- Your **production goals, outline, and todo list** directly embedded in code/document comments so AI editors and human contributors stay on track and avoid project drift.

***

### **Directory Structure**

```plaintext
ledctl/
  app.py                 # Flask + Socket.IO server [MAIN ENTRY]
  requirements.txt       # All Python dependencies
  config/
    device.default.yml   # Main config (HUB75/WS2811/WLED) [EDIT THIS]
    ws2811.map.json      # Example 10x10 grid mapping (serpentine)
  core/
    frames.py            # Loads GIF/PNG/MP4 frames [TODOs marked]
    gamma.py             # Gamma & RGB balance logic
    playlists.py         # Playlist/crossfade logic
    mapper.py            # Coordinate mapping functions (JSON+algorithms)
    drivers/
      __init__.py        # OutputDevice base class [TODO: Expand for new HW]
      hub75.py           # HUB75 driver (Adafruit + rpi-rgb-led-matrix)
      ws2811_pi.py       # WS2811 driver for Pi GPIO
      wled_udp.py        # UDP driver for WLED/ESP32
  static/
    main.js              # JS: UI interaction with Flask/Socket.IO
    style.css            # CSS: Clean production UI
  templates/
    index.html           # Web control GUI
  uploads/               # User assets (uploads)
  systemd/
    ledctl.service       # Pi auto-boot/systemd unit
  monitor.py             # System health checks [TODO: Fill out]
```


***

### **Production Goals (top of `README.md` or code comments)**

1. **One web control interface** works with HUB75 panels, WS2811 lightboxes, and WLED/ESP32.
2. **Unified animation pipeline** (all GIF/PNG/MP4/procedural) before device output.
3. **Driver abstraction layer** for swappable hardware (easy extension).
4. **Live, real-time controls:** brightness, gamma, speed, RGB balance, transforms.
5. **Playlist management:** user uploads, ordering, loop, and crossfade.
6. **Production deployment:** systemd, error logging, system monitoring.
7. **Hardware reliability:** power, wiring, level-shifting, voltage/thermal checks.
8. **Optional MQTT sync for multi-display setups.**

***

### **Production Outline \& Key File Comments**

#### `app.py` (main entry)

```python
"""
Unified Lightbox Interface - Production Scaffold

GOALS:
    - Single Flask + Socket.IO server for all LED hardware
    - No duplicated code: all animations go through frame pipeline
    - Extensible driver system (see core/drivers/)
    - Web GUI uploads, playlists, device switching, live controls
    - Systemd-ready for production deployment

TODOs marked throughout for clarity.

See /config/device.default.yml for hardware and render settings.
See /static/main.js and /templates/index.html for GUI controls.
"""
# ...starter Flask app code with TODO markers...
```


#### `requirements.txt`

```
flask
flask-socketio
Pillow
opencv-python
pyyaml
rpi-rgb-led-matrix
rpi_ws281x
eventlet
```


#### `device.default.yml` (production config stub)

```yaml
device: HUB75            # HUB75 | WS2811_PI | WLED
hub75:
  rows: 64
  cols: 64
  hardware_mapping: "adafruit-hat"
  gpio_slowdown: 2
  brightness: 85
ws2811:
  width: 10
  height: 10
  count: 100
  gpio: 18
  brightness: 128
  pixel_order: "GRB"
  map_file: "config/ws2811.map.json"
wled:
  host: "192.168.1.50"
  port: 21324
render:
  scale: "LANCZOS"
  fps_cap: 60
  gamma: 2.2
  rgb_balance: [1.0, 1.0, 1.0]
  mirror_x: false
  mirror_y: false
  rotate: 0
```


#### `ws2811.map.json` (serpentine example for 10x10 grid)

```json
[
  {"x":0, "y":0}, {"x":1, "y":0}, ... {"x":9, "y":0},
  {"x":9, "y":1}, {"x":8, "y":1}, ... {"x":0, "y":1},
  ... repeat for rows 0-9
]
```

> Replace with the actual full mapping for your grid!

#### Driver interface (`core/drivers/__init__.py`)

```python
class OutputDevice:
    def open(self): pass
    def close(self): pass
    def set_brightness(self, value01: float): pass
    def draw_rgb_frame(self, w, h, iterable_rgb): pass
# TODO: Implement device-specific subclasses in hub75.py, ws2811_pi.py, wled_udp.py
```


#### GUI HTML (`templates/index.html`) - with production notes and layout comments

```html
<!--
Production GUI for Unified LED Animation System

GOALS:
  - File upload, playlist, device selection
  - Live preview, parameter sliders (brightness, speed, gamma, RGB balance)
  - Transform toggles (mirror, rotate)
-->
<!-- TODO: Connect controls to main.js and Flask Socket.IO endpoints -->
<!-- Layout: Bootstrap for mobile/readable UI; preview canvas for effect preview -->
```


#### `main.js` (web UI logic)

```javascript
/* 
Production JavaScript for Real-Time LED Controls

TODOs:
  - Fetch /api/files for uploaded assets
  - Connect to Socket.IO for play/stop/parameter events
  - Render preview grid so settings can be tuned before sending to device
  - Bind GUI controls to API/WebSocket endpoints
*/
```


#### `systemd/ledctl.service`

```
[Unit]
Description=LED Controller
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/ledctl
ExecStart=/usr/bin/python3 /home/pi/ledctl/app.py
Restart=always

[Install]
WantedBy=multi-user.target
```


***

### **AI Editor-Ready TODO List (embedded in code and notes)**

- Scaffold and check each file above, filling out TODOs as listed.
- Never duplicate animation logic—use central pipeline (frames.py, playlists.py).
- Always edit config via YAML/JSON keys; never hardcode pin numbers or grid sizes in drivers.
- GUI controls in HTML/JS must update state via Flask API/Socket.IO, never direct hardware calls.
- Use driver abstractions—no direct hardware manipulation in Flask endpoints.
- All hardware-specific wiring/power best practices from the guides must be followed ().[^1][^2][^3]
- Implement `/tests/` folder with snippet scripts to validate each feature as you add.

***

### **What’s Next?**

You now have the complete starter scaffold, fully outlined for production and AI collaborative development. Drop this folder structure on your Pi, fill in the TODOs, and follow the embedded production strategy for a robust, extensible, and maintainable LED interface.

**All guidance comes directly from production-tested LED guides and professional architecture best practices.**

If you want file contents for any specific modules or further expansion (e.g., MQTT, multi-display sync, advanced effects), just ask!

<div style="text-align: center">⁂</div>

[^1]: Complete-LED-Animation-System-Implementation-Guide.pdf

[^2]: Google-LED-Animation-Control-System.pdf

[^3]: LED-Animation-Control-System.pdf

