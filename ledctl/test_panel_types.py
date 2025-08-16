#!/usr/bin/env python3
"""
Test different HUB75 panel multiplexing types
"""

import time
import sys
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def test_panel_type(multiplexing, row_addr_type=0, panel_type=""):
    """Test a specific panel configuration"""
    options = RGBMatrixOptions()
    options.rows = 32
    options.cols = 64
    options.chain_length = 1
    options.parallel = 1
    options.hardware_mapping = 'adafruit-hat'
    options.gpio_slowdown = 2
    options.brightness = 50
    options.pwm_bits = 7  # Lower for testing
    
    # Set multiplexing
    options.multiplexing = multiplexing
    
    if row_addr_type > 0:
        options.row_address_type = row_addr_type
        
    if panel_type:
        options.panel_type = panel_type
    
    print(f"\nTesting configuration:")
    print(f"  Multiplexing: {multiplexing}")
    print(f"  Row addr type: {row_addr_type}")
    print(f"  Panel type: {panel_type}")
    
    try:
        matrix = RGBMatrix(options=options)
        
        # Draw test pattern
        # Fill entire display with white
        matrix.Fill(255, 255, 255)
        time.sleep(1)
        
        # Draw grid pattern
        matrix.Clear()
        # Vertical lines every 8 pixels
        for x in range(0, 64, 8):
            for y in range(32):
                matrix.SetPixel(x, y, 255, 0, 0)
        
        # Horizontal lines every 8 pixels
        for y in range(0, 32, 8):
            for x in range(64):
                matrix.SetPixel(x, y, 0, 255, 0)
                
        # Draw corners
        # Top-left
        for i in range(5):
            matrix.SetPixel(i, 0, 0, 0, 255)
            matrix.SetPixel(0, i, 0, 0, 255)
        
        # Top-right
        for i in range(5):
            matrix.SetPixel(63-i, 0, 255, 255, 0)
            matrix.SetPixel(63, i, 255, 255, 0)
            
        print("  Press Enter to continue or 'q' to quit...")
        response = input()
        
        matrix.Clear()
        
        if response.lower() == 'q':
            return False
            
        return True
        
    except Exception as e:
        print(f"  Error: {e}")
        return True

def main():
    print("HUB75 Panel Type Tester")
    print("=" * 40)
    print("This will test different panel configurations")
    print("Look for a pattern where:")
    print("- All pixels are lit properly")
    print("- Red vertical lines every 8 pixels")
    print("- Green horizontal lines every 8 pixels") 
    print("- Blue corners in top-left")
    print("- Yellow corners in top-right")
    
    # Common multiplexing values
    multiplexing_options = [
        0,  # Default
        1,  # Stripe
        2,  # Checkered
        3,  # Spiral
        4,  # ZStripe
        5,  # ZnMirrorZStripe
        6,  # Coreman
        7,  # Kaler2Scan
        8,  # P10Outdoor1R1G
    ]
    
    # Row address types
    row_addr_types = [0, 1, 2, 3]
    
    # Panel types
    panel_types = ["", "FM6126A", "FM6127"]
    
    print("\nTesting standard multiplexing modes...")
    for mult in multiplexing_options:
        if not test_panel_type(mult):
            break
    
    print("\nTesting with different row address types...")
    for row_type in row_addr_types[1:]:
        if not test_panel_type(0, row_type):
            break
    
    print("\nTesting specific panel types...")
    for panel in panel_types[1:]:
        if not test_panel_type(0, 0, panel):
            break
    
    print("\nTest complete!")
    print("\nIf you found a working configuration, update your config with:")
    print("  parameters:")
    print("    multiplexing: <value>")
    print("    row_address_type: <value>")
    print("    panel_type: '<value>'")

if __name__ == "__main__":
    main()