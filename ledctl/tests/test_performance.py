#!/usr/bin/env python3
"""
Performance and stability test for LB3C enhancements
"""

import sys
import os
import time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.automations import (
    ColorWave, RainbowCycle, Plasma, Fire, Matrix, Sparkle,
    Strobe, Breathe, Checkerboard
)
from core.drivers.mock import MockDevice


def test_animation_performance(animation_class, name, **kwargs):
    """Test performance of a single animation"""
    print(f"\nTesting {name}...")
    
    # Create 64x64 animation
    width, height = 64, 64
    fps = 30
    
    try:
        animation = animation_class(width, height, fps, **kwargs)
    except Exception as e:
        print(f"  ✗ Failed to create: {e}")
        return False
    
    # Test frame generation
    frame_times = []
    errors = 0
    
    print("  Generating 100 frames...")
    for i in range(100):
        try:
            start = time.time()
            frame = animation.update(1.0 / fps)
            elapsed = time.time() - start
            frame_times.append(elapsed)
            
            # Verify frame shape and type
            assert frame.shape == (height, width, 3), f"Wrong shape: {frame.shape}"
            assert frame.dtype == np.uint8, f"Wrong dtype: {frame.dtype}"
            assert np.all(frame >= 0) and np.all(frame <= 255), "Values out of range"
            
        except Exception as e:
            print(f"  ✗ Frame {i} error: {e}")
            errors += 1
    
    if errors > 0:
        print(f"  ✗ {errors} errors during generation")
        return False
    
    # Calculate statistics
    avg_time = np.mean(frame_times) * 1000  # Convert to ms
    max_time = np.max(frame_times) * 1000
    min_time = np.min(frame_times) * 1000
    
    print(f"  ✓ Frame generation: avg={avg_time:.2f}ms, min={min_time:.2f}ms, max={max_time:.2f}ms")
    
    # Check if fast enough for target FPS
    target_ms = 1000.0 / fps
    if avg_time < target_ms:
        print(f"  ✓ Performance OK for {fps} FPS (need <{target_ms:.1f}ms)")
    else:
        print(f"  ⚠ Too slow for {fps} FPS (need <{target_ms:.1f}ms)")
    
    return True


def test_rgb_conversion():
    """Test RGB list conversion performance"""
    print("\nTesting RGB conversion...")
    
    # Create test animation
    animation = ColorWave(64, 64, 30)
    frame = animation.generate_frame(0)
    
    # Test conversion
    times = []
    for _ in range(10):
        start = time.time()
        rgb_list = animation.to_rgb_list(frame)
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = np.mean(times) * 1000
    print(f"  ✓ RGB conversion: avg={avg_time:.2f}ms")
    
    # Verify output
    assert len(rgb_list) == 64 * 64, f"Wrong length: {len(rgb_list)}"
    assert all(isinstance(pixel, tuple) and len(pixel) == 3 for pixel in rgb_list[:10]), "Invalid format"
    print("  ✓ Output format correct")


def test_hardware_settings():
    """Test new hardware settings"""
    print("\nTesting hardware settings...")
    
    config = {
        'hub75': {
            'rows': 64,
            'cols': 64,
            'gpio_slowdown': 2,
            'pwm_bits': 11,
            'dithering': 1,
            'scan_mode': 0,
            'disable_hardware_pulsing': True
        }
    }
    
    # Test with mock device (HUB75Device requires hardware)
    device = MockDevice(config)
    device.open()
    
    # Test brightness control
    device.set_brightness(0.5)
    print("  ✓ Brightness control works")
    
    # Test frame drawing
    width, height = device.get_dimensions()
    test_frame = [(255, 0, 0)] * (width * height)  # All red
    device.draw_rgb_frame(width, height, test_frame)
    print("  ✓ Frame drawing works")
    
    device.close()
    print("  ✓ Device cleanup works")


def run_all_tests():
    """Run all performance tests"""
    print("=" * 60)
    print("LB3C Performance Test Suite")
    print("=" * 60)
    
    # Test each animation
    animations = [
        (ColorWave, "ColorWave", {'wave_speed': 2.0, 'color_speed': 1.0}),
        (RainbowCycle, "RainbowCycle", {'cycle_speed': 0.5, 'diagonal': True}),
        (Plasma, "Plasma", {'scale': 0.1, 'speed': 1.0}),
        (Fire, "Fire", {'cooling': 55, 'sparking': 120}),
        (Matrix, "Matrix", {'drop_speed': 5.0, 'trail_length': 10}),
        (Sparkle, "Sparkle", {'density': 0.02, 'fade_speed': 2.0}),
        (Strobe, "Strobe", {'frequency': 10.0, 'duty_cycle': 0.5}),
        (Breathe, "Breathe", {'breathe_speed': 0.5, 'min_brightness': 0.1}),
        (Checkerboard, "Checkerboard", {'square_size': 8, 'scroll_speed': 1.0}),
    ]
    
    passed = 0
    failed = 0
    
    for anim_class, name, kwargs in animations:
        if test_animation_performance(anim_class, name, **kwargs):
            passed += 1
        else:
            failed += 1
    
    # Test other components
    test_rgb_conversion()
    test_hardware_settings()
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Tests completed: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)