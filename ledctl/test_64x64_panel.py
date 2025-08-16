#!/usr/bin/env python3
"""
Test 64x64 HUB75 panel configurations
"""

import time
import sys
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def test_configuration(rows=64, cols=64, multiplexing=0, row_addr_type=0, panel_type="", pixel_mapper=""):
    """Test a specific panel configuration"""
    options = RGBMatrixOptions()
    options.rows = rows
    options.cols = cols
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 2
    options.brightness = 50
    options.pwm_bits = 7  # Lower for testing
    options.show_refresh_rate = True
    
    # Set multiplexing
    options.multiplexing = multiplexing
    
    if row_addr_type > 0:
        options.row_address_type = row_addr_type
        
    if panel_type:
        options.panel_type = panel_type
        
    if pixel_mapper:
        options.pixel_mapper_config = pixel_mapper
    
    print(f"\nTesting configuration:")
    print(f"  Rows: {rows}, Cols: {cols}")
    print(f"  Multiplexing: {multiplexing}")
    print(f"  Row addr type: {row_addr_type}")
    print(f"  Panel type: {panel_type}")
    print(f"  Pixel mapper: {pixel_mapper}")
    
    try:
        matrix = RGBMatrix(options=options)
        
        # Test 1: Fill entire display
        print("  Test 1: Full white (all pixels should be lit)")
        matrix.Fill(255, 255, 255)
        input("  Press Enter to continue...")
        
        # Test 2: Draw corners
        matrix.Clear()
        print("  Test 2: Corner markers")
        print("  - Red: Top-left (0,0)")
        print("  - Green: Top-right (63,0)")  
        print("  - Blue: Bottom-left (0,63)")
        print("  - Yellow: Bottom-right (63,63)")
        
        # Top-left corner - Red
        for i in range(8):
            for j in range(8):
                matrix.SetPixel(i, j, 255, 0, 0)
        
        # Top-right corner - Green
        for i in range(56, 64):
            for j in range(8):
                matrix.SetPixel(i, j, 0, 255, 0)
                
        # Bottom-left corner - Blue
        for i in range(8):
            for j in range(56, 64):
                matrix.SetPixel(i, j, 0, 0, 255)
                
        # Bottom-right corner - Yellow
        for i in range(56, 64):
            for j in range(56, 64):
                matrix.SetPixel(i, j, 255, 255, 0)
        
        input("  Press Enter to continue...")
        
        # Test 3: Row test
        matrix.Clear()
        print("  Test 3: Row test (alternating colors every 8 rows)")
        colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), 
                 (255,0,255), (0,255,255), (255,128,0), (128,0,255)]
        
        for y in range(64):
            color_idx = y // 8
            r, g, b = colors[color_idx]
            for x in range(64):
                matrix.SetPixel(x, y, r, g, b)
        
        input("  Press Enter to continue...")
        
        # Test 4: Column test
        matrix.Clear()
        print("  Test 4: Column test (alternating colors every 8 columns)")
        
        for x in range(64):
            color_idx = x // 8
            r, g, b = colors[color_idx]
            for y in range(64):
                matrix.SetPixel(x, y, r, g, b)
        
        response = input("  Press Enter to continue or 'q' to quit: ")
        
        matrix.Clear()
        
        if response.lower() == 'q':
            return False
            
        return True
        
    except Exception as e:
        print(f"  Error: {e}")
        return True

def main():
    print("64x64 HUB75 Panel Configuration Tester")
    print("=" * 50)
    print("IMPORTANT: Run with sudo for proper operation!")
    print()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        # Quick test of most likely configurations
        configs = [
            # Standard 64x64 configurations
            {"rows": 64, "cols": 64, "multiplexing": 0},
            {"rows": 32, "cols": 64, "multiplexing": 0, "pixel_mapper": "U-mapper"},
            {"rows": 32, "cols": 128, "multiplexing": 0},
            
            # Different multiplexing for 64x64
            {"rows": 64, "cols": 64, "multiplexing": 1},
            {"rows": 64, "cols": 64, "multiplexing": 4},
            
            # Different scan rates
            {"rows": 32, "cols": 64, "multiplexing": 1},
            {"rows": 16, "cols": 64, "multiplexing": 0, "pixel_mapper": "Rotate:90"},
        ]
        
        for config in configs:
            if not test_configuration(**config):
                break
    else:
        # Manual configuration mode
        print("Common 64x64 panel configurations:")
        print("1. Standard 64x64 (1/32 scan)")
        print("2. 32x64 with U-mapper (1/16 scan, folded)")
        print("3. 32x128 mapped to 64x64")
        print("4. 64x64 with different multiplexing")
        print("5. Custom configuration")
        
        choice = input("\nSelect configuration to test (1-5): ")
        
        if choice == '1':
            test_configuration(rows=64, cols=64)
        elif choice == '2':
            test_configuration(rows=32, cols=64, pixel_mapper="U-mapper")
        elif choice == '3':
            test_configuration(rows=32, cols=128)
        elif choice == '4':
            # Test different multiplexing values
            for mult in [0, 1, 4, 5, 6]:
                print(f"\nTrying multiplexing={mult}")
                if not test_configuration(rows=64, cols=64, multiplexing=mult):
                    break
        elif choice == '5':
            rows = int(input("Enter rows (16/32/64): "))
            cols = int(input("Enter cols (32/64/128): "))
            mult = int(input("Enter multiplexing (0-8): "))
            mapper = input("Enter pixel mapper (or leave blank): ")
            test_configuration(rows=rows, cols=cols, multiplexing=mult, pixel_mapper=mapper)
    
    print("\nTest complete!")
    print("\nOnce you find the correct configuration, update device.default.yml:")
    print("  parameters:")
    print("    rows: <value>")
    print("    cols: <value>") 
    print("    multiplexing: <value>")
    print("    pixel_mapper_config: '<value>'  # if needed")

if __name__ == "__main__":
    main()