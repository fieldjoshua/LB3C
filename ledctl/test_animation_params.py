#!/usr/bin/env python3
"""
Test animation parameter changes including renamed speed parameters
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:5000"

def test_api_connection():
    """Test basic API connection"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/status")
        if response.status_code == 200:
            print("✓ API connection successful")
            return True
        else:
            print(f"✗ API returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to API: {e}")
        return False

def test_automations():
    """Test automation listing and parameters"""
    try:
        response = requests.get(f"{BASE_URL}/api/v1/automations")
        automations = response.json()
        
        print("\n=== Testing Automation Parameters ===")
        
        # Check Plasma specifically
        if 'plasma' in automations:
            plasma = automations['plasma']
            print(f"\nPlasma automation:")
            print(f"  Parameters: {list(plasma['parameters'].keys())}")
            
            # Check for renamed parameter
            if 'plasma_speed' in plasma['parameters']:
                print("  ✓ plasma_speed parameter found (renamed from speed)")
            else:
                print("  ✗ plasma_speed parameter NOT found")
                
            if 'speed' in plasma['parameters']:
                print("  ✗ WARNING: old 'speed' parameter still exists!")
        
        # Check color parameters
        print("\nChecking color parameters:")
        for name, info in automations.items():
            for param, details in info['parameters'].items():
                if details.get('type') == 'color':
                    print(f"  ✓ {name}.{param} has color type")
                    if 'default' in details:
                        print(f"    Default: RGB{details['default']}")
        
        # Check select parameters
        print("\nChecking select parameters:")
        for name, info in automations.items():
            for param, details in info['parameters'].items():
                if details.get('type') == 'select':
                    print(f"  ✓ {name}.{param} has select type")
                    if 'options' in details:
                        print(f"    Options: {details['options']}")
        
        # Check parameter ranges
        print("\nChecking parameter ranges:")
        params_with_ranges = []
        for name, info in automations.items():
            for param, details in info['parameters'].items():
                if 'min' in details or 'max' in details:
                    params_with_ranges.append(f"{name}.{param}")
                    print(f"  ✓ {name}.{param}: min={details.get('min', 'N/A')}, max={details.get('max', 'N/A')}")
        
        print(f"\nTotal parameters with ranges: {len(params_with_ranges)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing automations: {e}")
        return False

def test_parameter_validation():
    """Test parameter validation"""
    print("\n=== Testing Parameter Validation ===")
    
    test_cases = [
        # Valid transform parameters
        {
            'parameter': 'mirror_x',
            'value': True,
            'expected': 'success'
        },
        {
            'parameter': 'rotation',
            'value': 90,
            'expected': 'success'
        },
        # Invalid rotation
        {
            'parameter': 'rotation',
            'value': 45,
            'expected': 'error'
        },
        # Valid brightness
        {
            'parameter': 'brightness',
            'value': 0.5,
            'expected': 'success'
        },
        # Invalid brightness
        {
            'parameter': 'brightness',
            'value': 2.0,
            'expected': 'error'
        }
    ]
    
    headers = {'Content-Type': 'application/json'}
    
    for test in test_cases:
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/parameter",
                json=test,
                headers=headers
            )
            
            if test['expected'] == 'success' and response.status_code == 200:
                print(f"✓ {test['parameter']}={test['value']} accepted")
            elif test['expected'] == 'error' and response.status_code >= 400:
                print(f"✓ {test['parameter']}={test['value']} rejected (expected)")
            else:
                print(f"✗ {test['parameter']}={test['value']} unexpected result: {response.status_code}")
                
        except Exception as e:
            print(f"✗ Error testing {test['parameter']}: {e}")

def test_plasma_animation():
    """Test playing Plasma animation with new parameter name"""
    print("\n=== Testing Plasma Animation ===")
    
    try:
        # Stop any current playback
        requests.post(f"{BASE_URL}/api/v1/stop")
        time.sleep(0.5)
        
        # Play Plasma with plasma_speed parameter
        play_data = {
            'type': 'automation',
            'automation': 'plasma',
            'params': {
                'plasma_speed': 2.0,
                'scale': 0.2
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        response = requests.post(
            f"{BASE_URL}/api/v1/play",
            json=play_data,
            headers=headers
        )
        
        if response.status_code == 200:
            print("✓ Plasma animation started with plasma_speed parameter")
            print("  Let it run for 3 seconds...")
            time.sleep(3)
            
            # Stop playback
            requests.post(f"{BASE_URL}/api/v1/stop")
            print("✓ Animation stopped")
            return True
        else:
            print(f"✗ Failed to start animation: {response.status_code}")
            print(f"  Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing Plasma: {e}")
        return False

def main():
    print("LED Controller Parameter Test")
    print("=" * 50)
    
    if not test_api_connection():
        print("\nMake sure the LED controller is running:")
        print("  cd ~/LB3C/ledctl")
        print("  sudo ./start.sh")
        sys.exit(1)
    
    test_automations()
    test_parameter_validation()
    test_plasma_animation()
    
    print("\n" + "=" * 50)
    print("Test complete!")
    print("\nNext steps:")
    print("1. Open the web interface at http://[pi-ip]:5000")
    print("2. Test the transform controls (mirror/rotation)")
    print("3. Test color pickers in Strobe/Checkerboard animations")
    print("4. Verify Plasma shows 'plasma speed' not 'speed'")

if __name__ == "__main__":
    main()