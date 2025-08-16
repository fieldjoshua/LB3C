#!/usr/bin/env python3
"""
Diagnose 64x64 panel column issues
"""

import time
from rgbmatrix import RGBMatrix, RGBMatrixOptions

def test_config(name, **kwargs):
    """Test a specific configuration"""
    options = RGBMatrixOptions()
    
    # Base config from user
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
    
    # Apply test-specific options
    for key, value in kwargs.items():
        setattr(options, key, value)
    
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    for key, value in kwargs.items():
        print(f"  {key}: {value}")
    
    try:
        matrix = RGBMatrix(options=options)
        
        # Test 1: Column test
        print("\nTest 1: Drawing vertical lines every 4 pixels")
        matrix.Clear()
        for x in range(0, 64, 4):
            for y in range(64):
                matrix.SetPixel(x, y, 255, 255, 255)
        
        response = input("How many vertical lines do you see? (should be 16): ")
        
        # Test 2: Fill columns sequentially
        print("\nTest 2: Filling columns sequentially")
        for col_group in range(4):
            matrix.Clear()
            # Fill every 4th column starting at col_group
            for x in range(col_group, 64, 4):
                for y in range(64):
                    matrix.SetPixel(x, y, 255, 0, 0)
            print(f"  Showing columns {col_group}, {col_group+4}, {col_group+8}...")
            time.sleep(1)
        
        # Test 3: Checkerboard
        print("\nTest 3: 2x2 checkerboard pattern")
        matrix.Clear()
        for y in range(64):
            for x in range(64):
                if ((x//2) + (y//2)) % 2 == 0:
                    matrix.SetPixel(x, y, 255, 255, 255)
        
        response = input("Does the checkerboard look correct? (y/n): ")
        
        matrix.Clear()
        return response.lower() == 'y'
        
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("64x64 Panel Column Diagnostic")
    print("=" * 60)
    print("Issue: Only 2/4 columns displaying")
    
    configs = [
        # Try actual 32x64 configurations
        ("32x64 with chain_length=2", {
            'rows': 32,
            'cols': 64,
            'chain_length': 2,
            'pixel_mapper_config': ''
        }),
        
        # Try 64x64 with different multiplexing
        ("64x64 with multiplexing=1", {
            'rows': 64,
            'cols': 64,
            'multiplexing': 1
        }),
        
        ("64x64 with multiplexing=8", {
            'rows': 64,
            'cols': 64,
            'multiplexing': 8
        }),
        
        # Try different row address types
        ("64x64 with row_address_type=2", {
            'rows': 64,
            'cols': 64,
            'row_address_type': 2
        }),
        
        ("64x64 with row_address_type=3", {
            'rows': 64,
            'cols': 64,
            'row_address_type': 3
        }),
        
        # Try panel types
        ("64x64 with panel_type=FM6126A", {
            'rows': 64,
            'cols': 64,
            'panel_type': 'FM6126A'
        }),
        
        # Try 16x64 with multiplexing
        ("16x64 with chain=4 + U-mapper", {
            'rows': 16,
            'cols': 64,
            'chain_length': 4,
            'pixel_mapper_config': 'U-mapper'
        }),
        
        # Custom column mapper
        ("64x64 with Rotate:180", {
            'rows': 64,
            'cols': 64,
            'pixel_mapper_config': 'Rotate:180'
        }),
        
        # Try interlaced mode
        ("32x64 interlaced with multiplexing=2", {
            'rows': 32,
            'cols': 64,
            'multiplexing': 2,
            'pixel_mapper_config': 'U-mapper'
        }),
    ]
    
    for name, config in configs:
        if test_config(name, **config):
            print(f"\n✓ Configuration '{name}' seems to work!")
            print("\nUpdate your device.default.yml with:")
            print("hub75:")
            print(f"  rows: {config.get('rows', 64)}")
            print(f"  cols: {config.get('cols', 64)}")
            if 'chain_length' in config:
                print(f"  chain_length: {config['chain_length']}")
            if 'multiplexing' in config:
                print(f"  multiplexing: {config['multiplexing']}")
            if 'row_address_type' in config:
                print(f"  row_address_type: {config['row_address_type']}")
            if 'panel_type' in config:
                print(f"  panel_type: \"{config['panel_type']}\"")
            if 'pixel_mapper_config' in config and config['pixel_mapper_config']:
                print(f"  pixel_mapper_config: \"{config['pixel_mapper_config']}\"")
            break
        
        cont = input("\nContinue testing? (y/n): ")
        if cont.lower() != 'y':
            break
    
    print("\nIf none worked, your panel might need a custom pixel mapper.")
    print("Can you share:")
    print("1. Exact product link or model number")
    print("2. Any markings on the back (like '1/16 scan', 'ABCDE')")
    print("3. Photos of the back showing the chips and connectors")

if __name__ == "__main__":
    main()