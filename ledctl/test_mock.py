#!/usr/bin/env python3
"""
Test script to verify the LED animation system works in mock mode
"""

import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Test basic imports
print("Testing imports...")

try:
    from core.drivers import DeviceManager
    from core.drivers.mock import MockDevice
    print("✓ Mock device driver imported successfully")
except ImportError as e:
    print(f"✗ Failed to import mock device: {e}")
    sys.exit(1)

try:
    # Create a simple mock device
    config = {
        'mock': {
            'width': 16,
            'height': 8
        }
    }
    
    # Register and create device
    DeviceManager.register_device('MOCK', MockDevice)
    device = DeviceManager.create_device('MOCK', config)
    
    print("✓ Mock device created successfully")
    
    # Test opening device
    device.open()
    print("✓ Mock device opened successfully")
    
    # Test drawing frames
    width, height = device.get_dimensions()
    print(f"✓ Device dimensions: {width}x{height}")
    
    # Create a simple test pattern
    print("\nTesting frame rendering...")
    
    # Red frame
    red_frame = [(255, 0, 0)] * (width * height)
    device.draw_rgb_frame(width, height, red_frame)
    print("✓ Drew red frame")
    
    # Green frame
    green_frame = [(0, 255, 0)] * (width * height)
    device.draw_rgb_frame(width, height, green_frame)
    print("✓ Drew green frame")
    
    # Blue frame
    blue_frame = [(0, 0, 255)] * (width * height)
    device.draw_rgb_frame(width, height, blue_frame)
    print("✓ Drew blue frame")
    
    # Test brightness
    device.set_brightness(0.5)
    print("✓ Set brightness to 50%")
    
    # Close device
    device.close()
    print("✓ Mock device closed successfully")
    
    print("\n✅ All tests passed! The mock device is working correctly.")
    
except Exception as e:
    print(f"\n✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)