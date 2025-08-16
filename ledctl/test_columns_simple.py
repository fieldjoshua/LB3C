#!/usr/bin/env python3
"""
Simple column test to identify the pattern
"""

import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def main():
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 3
    options.pwm_bits = 11
    options.pwm_lsb_nanoseconds = 120
    options.limit_refresh_rate_hz = 200
    options.brightness = 50
    options.row_address_type = 1  # Your working setting
    
    matrix = RGBMatrix(options=options)
    
    print("Column Pattern Test")
    print("=" * 50)
    
    # Test 1: Light each column individually
    print("\nTest 1: Lighting columns 0-7 individually")
    for col in range(8):
        matrix.Clear()
        for y in range(64):
            matrix.SetPixel(col, y, 255, 255, 255)
        print(f"Column {col} lit - ", end='', flush=True)
        response = input("Visible? (y/n): ")
    
    # Test 2: Pattern test
    print("\nTest 2: Column groups")
    patterns = [
        ("Columns 0,2,4,6", [0, 2, 4, 6]),
        ("Columns 1,3,5,7", [1, 3, 5, 7]),
        ("Columns 0,1,2,3", [0, 1, 2, 3]),
        ("Columns 4,5,6,7", [4, 5, 6, 7]),
    ]
    
    for name, cols in patterns:
        matrix.Clear()
        for col in cols:
            for y in range(64):
                matrix.SetPixel(col, y, 255, 0, 0)
        print(f"{name} - ", end='', flush=True)
        response = input("How many lines visible?: ")
    
    # Test 3: Full width test
    print("\nTest 3: Drawing at different X positions")
    test_positions = [0, 15, 16, 31, 32, 47, 48, 63]
    
    matrix.Clear()
    for x in test_positions:
        for y in range(64):
            matrix.SetPixel(x, y, 255, 255, 0)
        print(f"Drew line at X={x}")
    
    visible = input("Which X positions are visible? (comma separated): ")
    
    print("\nBased on this pattern, your panel likely needs:")
    if "0,16,32,48" in visible or "15,31,47,63" in visible:
        print("- Multiplexing adjustment (every 16 columns)")
    elif "0,32" in visible or "15,47" in visible:
        print("- Panel is likely 32-wide internally, mapped to 64")
    else:
        print("- Custom mapping needed")
    
    matrix.Clear()

if __name__ == "__main__":
    main()