#!/usr/bin/env python3
"""
Test column lighting to diagnose multiplexing issues
"""

import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def main():
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 2
    options.brightness = 50
    options.pwm_bits = 7
    
    matrix = RGBMatrix(options=options)
    
    print("Column test - each column will light up in sequence")
    print("Watch for pattern...")
    
    # Test 1: Light each column individually
    for x in range(64):
        matrix.Clear()
        for y in range(32):
            matrix.SetPixel(x, y, 255, 255, 255)
        time.sleep(0.1)
    
    # Test 2: Show column numbers
    matrix.Clear()
    print("\nShowing column pattern:")
    print("Red = columns 0,4,8,12...")
    print("Green = columns 1,5,9,13...")
    print("Blue = columns 2,6,10,14...")
    print("White = columns 3,7,11,15...")
    
    for x in range(64):
        color_index = x % 4
        colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,255)]
        r, g, b = colors[color_index]
        
        for y in range(32):
            matrix.SetPixel(x, y, r, g, b)
    
    input("Press Enter to continue...")
    
    # Test 3: Draw quadrants
    matrix.Clear()
    print("\nDrawing quadrants (should be 4 equal sections):")
    
    # Top-left - Red
    for x in range(0, 16):
        for y in range(0, 16):
            matrix.SetPixel(x, y, 255, 0, 0)
    
    # Top-right - Green  
    for x in range(16, 32):
        for y in range(0, 16):
            matrix.SetPixel(x, y, 0, 255, 0)
            
    # Bottom-left - Blue
    for x in range(0, 16):
        for y in range(16, 32):
            matrix.SetPixel(x, y, 0, 0, 255)
            
    # Bottom-right - White
    for x in range(16, 32):
        for y in range(16, 32):
            matrix.SetPixel(x, y, 255, 255, 255)
    
    input("Press Enter to exit...")
    matrix.Clear()

if __name__ == "__main__":
    main()