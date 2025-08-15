#!/usr/bin/env python3
"""
Test script for LED automations
"""

import sys
import os
import time

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.automations import (
    ColorWave, RainbowCycle, Plasma, Fire, Matrix, 
    Sparkle, Strobe, Breathe, Checkerboard,
    get_automation_info, create_automation
)
from core.drivers.mock import MockDevice
from core.gamma import create_corrector

def test_automation_info():
    """Test getting automation information"""
    print("Testing automation info...")
    info = get_automation_info()
    
    for name, details in info.items():
        print(f"\n{name}:")
        print(f"  Description: {details['description']}")
        print(f"  Parameters:")
        for param, param_info in details['parameters'].items():
            print(f"    - {param}: {param_info}")

def test_automation_rendering():
    """Test rendering a few frames from each automation"""
    print("\nTesting automation rendering...")
    
    # Create mock device
    device = MockDevice()
    device.open(64, 32)
    
    # Create gamma corrector
    gamma_corrector = create_corrector(gamma=2.2, brightness=0.8)
    
    # Test each automation
    automations = [
        ('color_wave', ColorWave(64, 32)),
        ('rainbow_cycle', RainbowCycle(64, 32)),
        ('plasma', Plasma(64, 32, scale=0.2)),
        ('fire', Fire(64, 32)),
        ('matrix', Matrix(64, 32)),
        ('sparkle', Sparkle(64, 32, density=0.05)),
        ('strobe', Strobe(64, 32, frequency=5)),
        ('breathe', Breathe(64, 32, breathe_speed=1.0)),
        ('checkerboard', Checkerboard(64, 32, square_size=4))
    ]
    
    for name, automation in automations:
        print(f"\nTesting {name}...")
        
        # Render a few frames
        for i in range(30):  # 1 second at 30fps
            frame = automation.update(1/30)  # 33ms per frame
            
            # Apply gamma correction
            corrected = gamma_corrector.correct_frame(frame)
            
            # Convert to RGB list
            rgb_data = automation.to_rgb_list(corrected)
            
            # Send to device
            device.draw_rgb_frame(64, 32, rgb_data)
            
        print(f"  ✓ Rendered 30 frames successfully")
        print(f"  Final time: {automation.time:.2f}s")

def test_automation_creation():
    """Test creating automations with parameters"""
    print("\nTesting automation creation with parameters...")
    
    # Test with various parameters
    tests = [
        ('color_wave', {'wave_speed': 2.0, 'color_speed': 1.0}),
        ('rainbow_cycle', {'cycle_speed': 0.5, 'diagonal': True}),
        ('plasma', {'scale': 0.1, 'speed': 2.0}),
        ('fire', {'cooling': 80, 'sparking': 200}),
        ('sparkle', {'density': 0.1, 'fade_speed': 1.0, 'color_mode': 'rainbow'}),
    ]
    
    for name, params in tests:
        try:
            automation = create_automation(name, 64, 32, 30, **params)
            print(f"  ✓ Created {name} with params: {params}")
        except Exception as e:
            print(f"  ✗ Failed to create {name}: {e}")

def test_animation_performance():
    """Test performance of animations"""
    print("\nTesting animation performance...")
    
    automation = Plasma(64, 32, scale=0.15)
    
    # Time 100 frames
    start_time = time.time()
    for _ in range(100):
        frame = automation.update(1/30)
        rgb_data = automation.to_rgb_list(frame)
    
    elapsed = time.time() - start_time
    fps = 100 / elapsed
    
    print(f"  Rendered 100 frames in {elapsed:.2f}s")
    print(f"  Performance: {fps:.1f} FPS")
    print(f"  Target: 30 FPS")
    
    if fps >= 30:
        print("  ✓ Performance is sufficient")
    else:
        print("  ✗ Performance may be too slow")

if __name__ == '__main__':
    print("LED Automation Test Suite")
    print("=" * 50)
    
    test_automation_info()
    test_automation_rendering()
    test_automation_creation()
    test_animation_performance()
    
    print("\n" + "=" * 50)
    print("All tests completed!")
    print("\nTo test in the web interface:")
    print("1. Run: python app.py --mock")
    print("2. Open http://localhost:5000")
    print("3. Select an automation from the dropdown")
    print("4. Adjust parameters and click 'Play Automation'")