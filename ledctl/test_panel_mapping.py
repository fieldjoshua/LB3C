#!/usr/bin/env python3
"""
Test different panel mappings for 64x64 display with quarter sections
"""

import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def test_mapping(rows, cols, mapper, description):
    """Test a specific mapping configuration"""
    options = RGBMatrixOptions()
    options.rows = rows
    options.cols = cols
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 2
    options.brightness = 50
    options.pwm_bits = 7
    
    if mapper:
        options.pixel_mapper_config = mapper
    
    print(f"\n{description}")
    print(f"Config: rows={rows}, cols={cols}, mapper='{mapper}'")
    
    try:
        matrix = RGBMatrix(options=options)
        
        # Draw numbered quadrants
        matrix.Clear()
        
        # Quadrant 1 (top-left) - Red with "1"
        for x in range(0, 32):
            for y in range(0, 32):
                matrix.SetPixel(x, y, 255, 0, 0)
        
        # Quadrant 2 (top-right) - Green with "2"
        for x in range(32, 64):
            for y in range(0, 32):
                matrix.SetPixel(x, y, 0, 255, 0)
        
        # Quadrant 3 (bottom-left) - Blue with "3"
        for x in range(0, 32):
            for y in range(32, 64):
                matrix.SetPixel(x, y, 0, 0, 255)
        
        # Quadrant 4 (bottom-right) - Yellow with "4"
        for x in range(32, 64):
            for y in range(32, 64):
                matrix.SetPixel(x, y, 255, 255, 0)
        
        # Draw white borders between quadrants
        for i in range(64):
            matrix.SetPixel(31, i, 255, 255, 255)
            matrix.SetPixel(32, i, 255, 255, 255)
            matrix.SetPixel(i, 31, 255, 255, 255)
            matrix.SetPixel(i, 32, 255, 255, 255)
        
        response = input("Check quadrant layout (should see 4 colored squares). Type 'y' if correct, Enter to skip: ")
        matrix.Clear()
        
        return response.lower() in ['y', 'yes']
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("64x64 Panel Mapping Tester")
    print("=" * 50)
    print("Testing for panels with alternating quarter sections")
    
    mappings = [
        # Most common 64x64 configurations
        (32, 64, "U-mapper", "32x64 with U-mapper (2 vertical sections)"),
        (16, 128, "U-mapper", "16x128 with U-mapper (4 sections in line)"),
        (32, 128, "", "32x128 direct (2 panels side by side)"),
        (16, 64, "U-mapper;Rotate:90", "16x64 U-mapper rotated"),
        (64, 64, "", "64x64 direct (1:32 scan)"),
        (32, 64, "V-mapper", "32x64 with V-mapper (zigzag)"),
        (16, 64, "U-mapper:2", "16x64 with double U-mapper"),
        
        # Try with multiplexing
        (32, 64, "", "32x64 direct (may need multiplexing=1)"),
    ]
    
    found = False
    for rows, cols, mapper, desc in mappings:
        if test_mapping(rows, cols, mapper, desc):
            print(f"\n✓ Found working configuration!")
            print(f"  rows: {rows}")
            print(f"  cols: {cols}")
            print(f"  pixel_mapper_config: \"{mapper}\"")
            found = True
            break
    
    if not found:
        print("\nNo automatic match found. Let's try custom configuration.")
        print("\nYour panel shows alternating quarters, which suggests:")
        print("1. Four 32x32 panels arranged in 2x2")
        print("2. Two 32x64 panels stacked with alternating scan")
        print("3. Special multiplexing pattern")
        
        # Test with different multiplexing values
        print("\nTesting with different multiplexing values...")
        for mult in [1, 2, 4, 5, 6, 7]:
            options = RGBMatrixOptions()
            options.rows = 64
            options.cols = 64
            options.chain_length = 1
            options.parallel = 1
            options.hardware_mapping = 'adafruit-hat'
            options.gpio_slowdown = 2
            options.brightness = 50
            options.pwm_bits = 7
            options.multiplexing = mult
            
            try:
                print(f"\nTesting multiplexing={mult}")
                matrix = RGBMatrix(options=options)
                matrix.Fill(255, 255, 255)
                response = input("Are all pixels lit? (y/n): ")
                matrix.Clear()
                
                if response.lower() == 'y':
                    print(f"\n✓ Found working configuration with multiplexing={mult}")
                    found = True
                    break
                    
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    main()