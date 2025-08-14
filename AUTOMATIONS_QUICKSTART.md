# LED Automations Quick Start Guide

## Overview

The LED Animation Control System now includes **9 built-in procedural automations** that can generate dynamic patterns without needing any media files. These automations work with all supported hardware (HUB75, WS2811, WLED).

## Available Automations

1. **Color Wave** - Smooth color waves flowing across the display
2. **Rainbow Cycle** - Classic rainbow effect (horizontal or diagonal)
3. **Plasma** - Mesmerizing plasma effect using sine wave interference
4. **Fire** - Realistic fire simulation with sparks and heat diffusion
5. **Matrix** - Matrix-style falling green text effect
6. **Sparkle** - Random twinkling stars (white or rainbow)
7. **Strobe** - Configurable strobe light effect
8. **Breathe** - Gentle pulsing/breathing effect
9. **Checkerboard** - Animated checkerboard pattern

## Quick Start

### 1. Install Dependencies

First, make sure you have the required dependencies:

```bash
cd LB3C/ledctl
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run in Mock Mode (No Hardware Required)

```bash
python3 app.py --mock
```

### 3. Access Web Interface

Open your browser to: http://localhost:5000

### 4. Use Automations

1. Look for the **"Automations"** section in the left panel
2. Select an automation from the dropdown
3. Adjust any parameters that appear
4. Click **"Play Automation"**

## Running on Raspberry Pi with HUB75

```bash
# SSH into your Pi
ssh joshuafield@192.168.0.98

# Navigate to project
cd LB3C/ledctl

# Run with sudo for GPIO access
sudo python3 app.py

# Or use the start script
sudo ./start.sh
```

## Automation Parameters

Each automation has customizable parameters:

- **Color Wave**: wave_speed, color_speed
- **Rainbow Cycle**: cycle_speed, diagonal mode
- **Plasma**: scale, speed
- **Fire**: cooling, sparking intensity
- **Matrix**: drop_speed, trail_length
- **Sparkle**: density, fade_speed, color_mode
- **Strobe**: frequency, duty_cycle, color
- **Breathe**: breathe_speed, min_brightness, color
- **Checkerboard**: square_size, scroll_speed, colors

## API Usage

You can also control automations via the WebSocket API:

```javascript
// Connect to server
const socket = io();

// Play an automation
socket.emit('play', {
    type: 'automation',
    automation: 'plasma',
    params: {
        scale: 0.15,
        speed: 1.5
    }
});
```

## Tips

- Start with **Rainbow Cycle** or **Color Wave** for a gentle introduction
- **Plasma** looks amazing on larger displays
- **Fire** effect works best when display is oriented vertically
- Adjust the main **Speed** slider to control animation playback rate
- Use **Brightness** and **Gamma** controls to fine-tune the look

## Next Steps

- Combine automations with file-based animations in playlists
- Create custom automations by extending the `ProceduralAnimation` class
- Use the scheduling system (coming soon) to automate playback

Enjoy your new LED automations!