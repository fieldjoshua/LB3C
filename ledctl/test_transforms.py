#!/usr/bin/env python3
"""
Test script to verify transform functionality
"""

import time
import numpy as np
from rgbmatrix import RGBMatrix, RGBMatrixOptions
import sys

def create_test_pattern(width, height):
    """Create a test pattern that shows orientation clearly"""
    pattern = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Red arrow pointing right at top
    for x in range(width//4, 3*width//4):
        pattern[height//4, x] = [255, 0, 0]
    # Arrow head
    for i in range(5):
        if height//4-i >= 0 and 3*width//4+i < width:
            pattern[height//4-i, 3*width//4+i] = [255, 0, 0]
        if height//4+i < height and 3*width//4+i < width:
            pattern[height//4+i, 3*width//4+i] = [255, 0, 0]
    
    # Green "L" in top-left corner
    for y in range(5, 15):
        pattern[y, 5] = [0, 255, 0]
    for x in range(5, 15):
        pattern[14, x] = [0, 255, 0]
    
    # Blue square in bottom-right
    for y in range(height-15, height-5):
        for x in range(width-15, width-5):
            pattern[y, x] = [0, 0, 255]
    
    # Yellow center cross
    cy, cx = height//2, width//2
    for i in range(-10, 11):
        if 0 <= cy+i < height:
            pattern[cy+i, cx] = [255, 255, 0]
        if 0 <= cx+i < width:
            pattern[cy, cx+i] = [255, 255, 0]
    
    # White border
    pattern[0, :] = [255, 255, 255]
    pattern[-1, :] = [255, 255, 255]
    pattern[:, 0] = [255, 255, 255]
    pattern[:, -1] = [255, 255, 255]
    
    return pattern

def apply_transforms(frame, params):
    """Apply mirror and rotation transforms to frame"""
    # Apply mirroring
    if params.get('mirror_x', False):
        frame = np.fliplr(frame)
    if params.get('mirror_y', False):
        frame = np.flipud(frame)
    
    # Apply rotation
    rotation = params.get('rotation', 0)
    if rotation == 90:
        frame = np.rot90(frame, k=1)
    elif rotation == 180:
        frame = np.rot90(frame, k=2)
    elif rotation == 270:
        frame = np.rot90(frame, k=3)
    
    return frame

def test_transform(matrix, pattern, transform_name, params):
    """Test a specific transform"""
    print(f"\nTesting: {transform_name}")
    print(f"Parameters: {params}")
    
    # Apply transforms
    transformed = apply_transforms(pattern.copy(), params)
    
    # Display on matrix
    height, width = transformed.shape[:2]
    rgb_data = []
    for y in range(height):
        for x in range(width):
            r, g, b = transformed[y, x]
            rgb_data.append((int(r), int(g), int(b)))
    
    matrix.Clear()
    for y in range(min(height, matrix.height)):
        for x in range(min(width, matrix.width)):
            if y * width + x < len(rgb_data):
                r, g, b = rgb_data[y * width + x]
                matrix.SetPixel(x, y, r, g, b)
    
    input("Press Enter to continue...")

def main():
    # Matrix configuration
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 4
    options.brightness = 50
    options.pwm_bits = 7
    options.pixel_mapper_config = "U-mapper"
    options.row_address_type = 1
    
    print("Transform Test Script")
    print("=" * 50)
    print("\nThis will test the transform functionality")
    print("\nPattern legend:")
    print("- Red arrow pointing right")
    print("- Green 'L' in top-left")
    print("- Blue square in bottom-right")
    print("- Yellow center cross")
    print("- White border")
    
    matrix = RGBMatrix(options=options)
    
    # Create test pattern
    pattern = create_test_pattern(64, 64)
    
    # Test cases
    tests = [
        ("Original (no transform)", {}),
        ("Mirror X (horizontal flip)", {'mirror_x': True}),
        ("Mirror Y (vertical flip)", {'mirror_y': True}),
        ("Mirror X+Y", {'mirror_x': True, 'mirror_y': True}),
        ("Rotate 90°", {'rotation': 90}),
        ("Rotate 180°", {'rotation': 180}),
        ("Rotate 270°", {'rotation': 270}),
        ("Mirror X + Rotate 90°", {'mirror_x': True, 'rotation': 90}),
        ("Mirror Y + Rotate 90°", {'mirror_y': True, 'rotation': 90}),
    ]
    
    try:
        for name, params in tests:
            test_transform(matrix, pattern, name, params)
    
        print("\nTest complete!")
        
        # Interactive mode
        print("\nEntering interactive mode...")
        print("Commands: mx (mirror x), my (mirror y), r0/r90/r180/r270 (rotation), q (quit)")
        
        current_params = {}
        
        while True:
            cmd = input("\nCommand: ").strip().lower()
            
            if cmd == 'q':
                break
            elif cmd == 'mx':
                current_params['mirror_x'] = not current_params.get('mirror_x', False)
            elif cmd == 'my':
                current_params['mirror_y'] = not current_params.get('mirror_y', False)
            elif cmd == 'r0':
                current_params['rotation'] = 0
            elif cmd == 'r90':
                current_params['rotation'] = 90
            elif cmd == 'r180':
                current_params['rotation'] = 180
            elif cmd == 'r270':
                current_params['rotation'] = 270
            else:
                print("Unknown command")
                continue
            
            test_transform(matrix, pattern, "Current", current_params)
    
    except KeyboardInterrupt:
        print("\nTest interrupted")
    finally:
        matrix.Clear()

if __name__ == "__main__":
    main()