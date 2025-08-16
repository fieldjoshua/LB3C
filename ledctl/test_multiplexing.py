#!/usr/bin/env python3
"""
Test different multiplexing values for 64x64 panel
"""

import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def test_multiplexing(mult_value):
    """Test a specific multiplexing value"""
    options = RGBMatrixOptions()
    options.rows = 64
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 2
    options.brightness = 50
    options.pwm_bits = 7
    options.multiplexing = mult_value
    options.show_refresh_rate = True
    
    print(f"\nTesting multiplexing = {mult_value}")
    
    try:
        matrix = RGBMatrix(options=options)
        
        # Test 1: Fill entire display
        print("Test 1: Full white fill")
        matrix.Fill(255, 255, 255)
        response = input("Are ALL pixels lit evenly? (y/n): ")
        
        if response.lower() != 'y':
            matrix.Clear()
            return False
        
        # Test 2: Draw test pattern
        matrix.Clear()
        print("\nTest 2: Quadrant test")
        
        # Draw 4 different colored quadrants
        # Top-left - Red
        for x in range(32):
            for y in range(32):
                matrix.SetPixel(x, y, 255, 0, 0)
        
        # Top-right - Green
        for x in range(32, 64):
            for y in range(32):
                matrix.SetPixel(x, y, 0, 255, 0)
        
        # Bottom-left - Blue
        for x in range(32):
            for y in range(32, 64):
                matrix.SetPixel(x, y, 0, 0, 255)
        
        # Bottom-right - Yellow
        for x in range(32, 64):
            for y in range(32, 64):
                matrix.SetPixel(x, y, 255, 255, 0)
        
        print("Should see: Red (top-left), Green (top-right), Blue (bottom-left), Yellow (bottom-right)")
        response = input("Are the quadrants in correct positions? (y/n): ")
        
        if response.lower() != 'y':
            matrix.Clear()
            return False
            
        # Test 3: Animation test
        matrix.Clear()
        print("\nTest 3: Animation smoothness")
        
        for frame in range(64):
            matrix.Clear()
            # Draw moving vertical line
            for y in range(64):
                matrix.SetPixel(frame, y, 255, 255, 255)
            time.sleep(0.05)
        
        response = input("Was the animation smooth without gaps? (y/n): ")
        matrix.Clear()
        
        return response.lower() == 'y'
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("64x64 Panel Multiplexing Tester")
    print("=" * 50)
    print("Testing different multiplexing values for alternating quarter issues")
    
    # Test multiplexing values
    mult_values = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    
    found = False
    for mult in mult_values:
        if test_multiplexing(mult):
            print(f"\n✓ SUCCESS! Multiplexing = {mult} works correctly")
            print("\nUpdate your config/device.default.yml:")
            print("  multiplexing: " + str(mult))
            found = True
            break
    
    if not found:
        print("\n❌ No standard multiplexing value worked.")
        print("\nYour panel might need:")
        print("1. Different row_address_type (try 1, 2, or 3)")
        print("2. Special panel_type (FM6126A or FM6127)")
        print("3. Custom pixel mapping")
        print("\nTry running: sudo python3 test_64x64_panel.py")

if __name__ == "__main__":
    main()