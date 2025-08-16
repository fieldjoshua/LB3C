#!/usr/bin/env python3
"""
Test configurations based on Adafruit's RGB Matrix examples
"""

import time
import sys
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def test_config(name, options_dict):
    """Test a specific configuration"""
    options = RGBMatrixOptions()
    
    # Set all options from dict
    for key, value in options_dict.items():
        setattr(options, key, value)
    
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Config: {options_dict}")
    
    try:
        matrix = RGBMatrix(options=options)
        
        # Simple test - draw diagonal line
        matrix.Clear()
        for i in range(min(64, matrix.width, matrix.height)):
            matrix.SetPixel(i, i, 255, 255, 255)
        
        # Draw borders
        for x in range(matrix.width):
            matrix.SetPixel(x, 0, 255, 0, 0)  # Top - red
            matrix.SetPixel(x, matrix.height-1, 0, 255, 0)  # Bottom - green
        
        for y in range(matrix.height):
            matrix.SetPixel(0, y, 0, 0, 255)  # Left - blue
            matrix.SetPixel(matrix.width-1, y, 255, 255, 0)  # Right - yellow
        
        response = input("Does the display show correct borders and diagonal? (y/n/q): ")
        matrix.Clear()
        
        if response.lower() == 'q':
            return 'quit'
        return response.lower() == 'y'
        
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to continue...")
        return False

def main():
    print("Adafruit RGB Matrix Configuration Tester")
    print("Based on Adafruit's documentation and examples")
    print("=" * 60)
    
    # Common Adafruit configurations for 64x64 panels
    configs = [
        # Standard 64x64 P3 indoor panel
        ("64x64 P3 Standard", {
            "rows": 64,
            "cols": 64,
            "chain_length": 1,
            "parallel": 1,
            "hardware_mapping": "adafruit-hat",
            "gpio_slowdown": 4,  # Higher for Pi 4
            "pwm_bits": 11,
            "brightness": 50,
            "pwm_lsb_nanoseconds": 130,
            "led_rgb_sequence": "RGB"
        }),
        
        # 64x64 with row address type 2 (common for some panels)
        ("64x64 with row_address_type=2", {
            "rows": 64,
            "cols": 64,
            "chain_length": 1,
            "parallel": 1,
            "hardware_mapping": "adafruit-hat",
            "gpio_slowdown": 4,
            "row_address_type": 2,
            "brightness": 50
        }),
        
        # 64x64 as 2 chained 32x64 panels
        ("2x 32x64 chained", {
            "rows": 32,
            "cols": 64,
            "chain_length": 2,
            "parallel": 1,
            "hardware_mapping": "adafruit-hat",
            "gpio_slowdown": 4,
            "brightness": 50
        }),
        
        # 64x64 with AB addressing
        ("64x64 AB addressing", {
            "rows": 64,
            "cols": 64,
            "chain_length": 1,
            "parallel": 1,
            "hardware_mapping": "adafruit-hat",
            "gpio_slowdown": 4,
            "row_address_type": 1,
            "brightness": 50
        }),
        
        # 64x64 with direct addressing
        ("64x64 Direct addressing", {
            "rows": 64,
            "cols": 64,
            "chain_length": 1,
            "parallel": 1,
            "hardware_mapping": "adafruit-hat",
            "gpio_slowdown": 4,
            "row_address_type": 3,
            "brightness": 50
        }),
        
        # FM6126A panel (common driver chip)
        ("64x64 FM6126A panel", {
            "rows": 64,
            "cols": 64,
            "chain_length": 1,
            "parallel": 1,
            "hardware_mapping": "adafruit-hat",
            "gpio_slowdown": 4,
            "panel_type": "FM6126A",
            "brightness": 50
        }),
        
        # Sometimes 64x64 is actually 64x32 in parallel
        ("64x32 in parallel", {
            "rows": 32,
            "cols": 64,
            "chain_length": 1,
            "parallel": 2,
            "hardware_mapping": "adafruit-hat",
            "gpio_slowdown": 4,
            "brightness": 50
        }),
    ]
    
    # Test each configuration
    for name, config in configs:
        result = test_config(name, config)
        if result == 'quit':
            break
        elif result:
            print(f"\n✓ SUCCESS with: {name}")
            print("\nAdd these to your config/device.default.yml under hub75:")
            for key, value in config.items():
                if key != "hardware_mapping" and key != "brightness":  # Skip defaults
                    if isinstance(value, str):
                        print(f"  {key}: \"{value}\"")
                    else:
                        print(f"  {key}: {value}")
            break
    
    # If nothing worked, show diagnostic info
    else:
        print("\n❌ No configuration worked correctly.")
        print("\nPlease check:")
        print("1. Your exact panel model/part number")
        print("2. Look for markings on the PCB (like 'P3', '1/32', 'AB')")
        print("3. Check where you purchased it - the listing often has specs")
        print("\nYou can also try:")
        print("- The Adafruit forums: forums.adafruit.com")
        print("- Post panel photos to r/FastLED or Adafruit forums")
        print("- Check if panel needs 5V (not 3.3V) logic levels")

if __name__ == "__main__":
    main()