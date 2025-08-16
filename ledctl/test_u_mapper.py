#!/usr/bin/env python3
"""
Test U-mapper configuration for 64x64 panel
"""

import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def main():
    options = RGBMatrixOptions()
    options.rows = 32  # Physical rows
    options.cols = 64  # Physical columns
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 2
    options.brightness = 50
    options.pwm_bits = 7
    options.pixel_mapper_config = "U-mapper"  # Maps 32x64 to 64x64
    
    print("Testing U-mapper configuration for 64x64 panel")
    print("This maps a 32x64 physical panel to 64x64 logical display")
    
    matrix = RGBMatrix(options=options)
    
    # Test 1: Draw actual corners of 64x64
    matrix.Clear()
    print("\nTest 1: Drawing true corners (8x8 blocks)")
    
    # Top-left (0,0) - Red
    for x in range(8):
        for y in range(8):
            matrix.SetPixel(x, y, 255, 0, 0)
    
    # Top-right (56-63, 0-7) - Green
    for x in range(56, 64):
        for y in range(8):
            matrix.SetPixel(x, y, 0, 255, 0)
    
    # Bottom-left (0-7, 56-63) - Blue
    for x in range(8):
        for y in range(56, 64):
            matrix.SetPixel(x, y, 0, 0, 255)
    
    # Bottom-right (56-63, 56-63) - Yellow
    for x in range(56, 64):
        for y in range(56, 64):
            matrix.SetPixel(x, y, 255, 255, 0)
    
    # Middle markers to verify mapping
    # Center cross - White
    for i in range(30, 34):
        matrix.SetPixel(i, 32, 255, 255, 255)
        matrix.SetPixel(32, i, 255, 255, 255)
    
    input("Should see corners only at edges, white cross in center. Press Enter...")
    
    # Test 2: Draw grid
    matrix.Clear()
    print("\nTest 2: Drawing 8x8 grid")
    
    # Vertical lines every 8 pixels
    for x in range(0, 64, 8):
        for y in range(64):
            matrix.SetPixel(x, y, 255, 0, 0)
    
    # Horizontal lines every 8 pixels
    for y in range(0, 64, 8):
        for x in range(64):
            matrix.SetPixel(x, y, 0, 255, 0)
    
    input("Should see even 8x8 grid. Press Enter...")
    
    # Test 3: Test numbering
    matrix.Clear()
    print("\nTest 3: Row numbers (different color per 8 rows)")
    
    colors = [
        (255, 0, 0),    # Red 0-7
        (255, 128, 0),  # Orange 8-15
        (255, 255, 0),  # Yellow 16-23
        (0, 255, 0),    # Green 24-31
        (0, 255, 255),  # Cyan 32-39
        (0, 0, 255),    # Blue 40-47
        (128, 0, 255),  # Purple 48-55
        (255, 0, 255),  # Magenta 56-63
    ]
    
    for y in range(64):
        color_idx = y // 8
        r, g, b = colors[color_idx]
        for x in range(64):
            matrix.SetPixel(x, y, r, g, b)
    
    input("Should see 8 horizontal color bands. Press Enter...")
    
    matrix.Clear()
    print("\nIf all tests passed, update your config with:")
    print("  rows: 32")
    print("  cols: 64")
    print("  pixel_mapper_config: \"U-mapper\"")

if __name__ == "__main__":
    main()