#!/usr/bin/env python3
"""
Demonstration of LED automations
Run with: python3 demo_automations.py
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.automations import get_automation_info, AUTOMATION_REGISTRY

def main():
    print("LED Automation System - Available Automations")
    print("=" * 60)
    
    info = get_automation_info()
    
    print("\nAvailable automations:")
    for i, (name, details) in enumerate(info.items(), 1):
        print(f"\n{i}. {name}")
        print(f"   Description: {details['description']}")
        if details['parameters']:
            print("   Parameters:")
            for param, param_info in details['parameters'].items():
                print(f"     - {param}: {param_info['type']} (default: {param_info['default']})")
    
    print("\n" + "=" * 60)
    print("\nTo use these automations:")
    print("1. Run the server: python3 app.py --mock")
    print("2. Open http://localhost:5000 in your browser")
    print("3. Go to the 'Automations' section")
    print("4. Select an automation and adjust parameters")
    print("5. Click 'Play Automation' to see it in action")
    
    print("\nFor hardware testing on Raspberry Pi:")
    print("1. Run: sudo python3 app.py")
    print("2. The automations will render on your connected LED display")

if __name__ == '__main__':
    main()