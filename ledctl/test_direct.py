#!/usr/bin/env python3
"""Direct test of HUB75 animations"""

import sys
import time
import numpy as np
sys.path.insert(0, '.')

from core.drivers.hub75 import HUB75Device
from core.automations import ColorWave, RainbowCycle, Fire

# Test configuration
config = {
    'hub75': {
        'gpio_slowdown': 2,
        'pwm_bits': 10,
        'pwm_lsb_nanoseconds': 130,
        'show_refresh_rate': True
    }
}

print("Testing HUB75 directly...")

# Create and open device
device = HUB75Device(config)
device.open()

# Test ColorWave
print("\nTesting ColorWave for 5 seconds...")
anim = ColorWave(64, 64, 30)
start = time.time()
frames = 0

while time.time() - start < 5:
    frame = anim.generate_frame(time.time())
    rgb_list = anim.to_rgb_list(frame)
    device.draw_rgb_frame(64, 64, rgb_list)
    frames += 1

fps = frames / 5
print(f"ColorWave: {fps:.1f} FPS")

# Test RainbowCycle
print("\nTesting RainbowCycle for 5 seconds...")
anim = RainbowCycle(64, 64, 30)
start = time.time()
frames = 0

while time.time() - start < 5:
    frame = anim.generate_frame(time.time())
    rgb_list = anim.to_rgb_list(frame)
    device.draw_rgb_frame(64, 64, rgb_list)
    frames += 1

fps = frames / 5
print(f"RainbowCycle: {fps:.1f} FPS")

# Clean up
device.close()
print("\nTest complete!")