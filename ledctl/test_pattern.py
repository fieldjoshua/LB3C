#!/usr/bin/env python3
"""
HUB75 Test Pattern Generator
Tests various patterns to diagnose display issues
"""

import time
import numpy as np
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import argparse

def create_matrix_options():
    """Create RGBMatrix options with various test configurations"""
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 4
    options.pwm_bits = 11
    options.pwm_lsb_nanoseconds = 130
    options.pwm_dither_bits = 1
    options.brightness = 50
    options.limit_refresh_rate_hz = 120
    options.show_refresh_rate = True  # Show actual refresh rate
    return options

def test_solid_colors(matrix):
    """Test solid colors to check for color accuracy"""
    print("Testing solid colors...")
    colors = [
        ("Red", (255, 0, 0)),
        ("Green", (0, 255, 0)),
        ("Blue", (0, 0, 255)),
        ("White", (255, 255, 255)),
        ("Yellow", (255, 255, 0)),
        ("Cyan", (0, 255, 255)),
        ("Magenta", (255, 0, 255)),
    ]
    
    for name, (r, g, b) in colors:
        print(f"  Showing {name}")
        matrix.Fill(r, g, b)
        time.sleep(2)

def test_gradient(matrix):
    """Test gradient to check for PWM bit depth"""
    print("Testing gradient...")
    width = matrix.width
    height = matrix.height
    
    for y in range(height):
        for x in range(width):
            # Horizontal gradient
            brightness = int((x / width) * 255)
            matrix.SetPixel(x, y, brightness, brightness, brightness)
    
    time.sleep(3)

def test_checkerboard(matrix):
    """Test checkerboard pattern for pixel accuracy"""
    print("Testing checkerboard...")
    for y in range(matrix.height):
        for x in range(matrix.width):
            if (x + y) % 2 == 0:
                matrix.SetPixel(x, y, 255, 255, 255)
            else:
                matrix.SetPixel(x, y, 0, 0, 0)
    
    time.sleep(3)

def test_moving_line(matrix):
    """Test moving line to check for tearing/ghosting"""
    print("Testing moving line...")
    width = matrix.width
    height = matrix.height
    
    # Vertical line moving horizontally
    for frame in range(width * 2):
        matrix.Clear()
        x = frame % width
        for y in range(height):
            matrix.SetPixel(x, y, 255, 255, 255)
        time.sleep(0.05)
    
    # Horizontal line moving vertically
    for frame in range(height * 2):
        matrix.Clear()
        y = frame % height
        for x in range(width):
            matrix.SetPixel(x, y, 255, 255, 255)
        time.sleep(0.05)

def test_frame_timing(matrix):
    """Test frame timing consistency"""
    print("Testing frame timing...")
    width = matrix.width
    height = matrix.height
    
    # Create a simple animation
    frame_times = []
    last_time = time.perf_counter()
    
    for frame in range(100):
        matrix.Clear()
        # Draw a moving box
        box_x = (frame * 2) % (width - 10)
        for y in range(10):
            for x in range(10):
                matrix.SetPixel(box_x + x, y, 255, 0, 0)
        
        current_time = time.perf_counter()
        frame_time = current_time - last_time
        frame_times.append(frame_time)
        last_time = current_time
        
        # Target 30 FPS
        target_frame_time = 1.0 / 30.0
        sleep_time = max(0, target_frame_time - frame_time)
        time.sleep(sleep_time)
    
    # Analyze timing
    avg_frame_time = np.mean(frame_times[1:])  # Skip first frame
    std_frame_time = np.std(frame_times[1:])
    
    print(f"  Average frame time: {avg_frame_time*1000:.2f}ms ({1/avg_frame_time:.1f} FPS)")
    print(f"  Std deviation: {std_frame_time*1000:.2f}ms")
    print(f"  Min frame time: {min(frame_times[1:])*1000:.2f}ms")
    print(f"  Max frame time: {max(frame_times[1:])*1000:.2f}ms")

def test_brightness_levels(matrix):
    """Test different brightness levels"""
    print("Testing brightness levels...")
    
    # Draw a test pattern
    for y in range(matrix.height):
        for x in range(matrix.width):
            if x < matrix.width // 2:
                matrix.SetPixel(x, y, 255, 0, 0)
            else:
                matrix.SetPixel(x, y, 0, 0, 255)
    
    brightness_levels = [10, 25, 50, 75, 100]
    for brightness in brightness_levels:
        print(f"  Brightness: {brightness}%")
        matrix.brightness = brightness
        time.sleep(1.5)

def main():
    parser = argparse.ArgumentParser(description='HUB75 Test Pattern Generator')
    parser.add_argument('--test', choices=['all', 'colors', 'gradient', 'checkerboard', 'motion', 'timing', 'brightness'],
                        default='all', help='Which test to run')
    parser.add_argument('--gpio-slowdown', type=int, default=4, help='GPIO slowdown factor')
    parser.add_argument('--pwm-bits', type=int, default=11, help='PWM bits')
    parser.add_argument('--brightness', type=int, default=50, help='Initial brightness')
    args = parser.parse_args()
    
    # Create matrix with options
    options = create_matrix_options()
    options.gpio_slowdown = args.gpio_slowdown
    options.pwm_bits = args.pwm_bits
    options.brightness = args.brightness
    
    print(f"Initializing matrix with:")
    print(f"  GPIO Slowdown: {options.gpio_slowdown}")
    print(f"  PWM Bits: {options.pwm_bits}")
    print(f"  PWM LSB Nanoseconds: {options.pwm_lsb_nanoseconds}")
    print(f"  Brightness: {options.brightness}%")
    print(f"  Refresh Rate Limit: {options.limit_refresh_rate_hz}Hz")
    
    matrix = RGBMatrix(options=options)
    
    try:
        if args.test == 'all':
            test_solid_colors(matrix)
            test_gradient(matrix)
            test_checkerboard(matrix)
            test_moving_line(matrix)
            test_frame_timing(matrix)
            test_brightness_levels(matrix)
        elif args.test == 'colors':
            test_solid_colors(matrix)
        elif args.test == 'gradient':
            test_gradient(matrix)
        elif args.test == 'checkerboard':
            test_checkerboard(matrix)
        elif args.test == 'motion':
            test_moving_line(matrix)
        elif args.test == 'timing':
            test_frame_timing(matrix)
        elif args.test == 'brightness':
            test_brightness_levels(matrix)
            
        print("\nTest complete!")
        
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        matrix.Clear()

if __name__ == "__main__":
    main()