#!/usr/bin/env python3
"""
Test configuration loading to verify fixes
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Testing configuration loading...")

# Test 1: Environment setup
print("\n1. Checking environment...")
if not os.path.exists('.env'):
    print("❌ .env file missing - run ./fix_runtime.sh first")
else:
    print("✓ .env file exists")

# Test 2: Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    secret_key = os.getenv('FLASK_SECRET_KEY')
    if secret_key:
        print("✓ FLASK_SECRET_KEY is set")
    else:
        print("❌ FLASK_SECRET_KEY not found in environment")
except Exception as e:
    print(f"❌ Error loading .env: {e}")

# Test 3: Config class
try:
    from core.config import Config
    config = Config()
    print("✓ Config object created successfully")
    print(f"  Device type: {config.device.get('type') if hasattr(config, 'device') else 'Not set'}")
except Exception as e:
    print(f"❌ Config initialization failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: YAML config loading
try:
    import yaml
    config_path = 'config/device.yml'
    if not os.path.exists(config_path):
        config_path = 'config/device.default.yml'
    
    with open(config_path, 'r') as f:
        yaml_config = yaml.safe_load(f)
    
    device_value = yaml_config.get('device')
    print(f"✓ YAML loaded successfully")
    print(f"  Device value type: {type(device_value)}")
    print(f"  Device value: {device_value}")
except Exception as e:
    print(f"❌ YAML loading failed: {e}")

# Test 5: Device imports
print("\n2. Testing device imports...")
errors = []
try:
    from core.drivers.mock import MockDevice
    print("✓ MockDevice imported")
except Exception as e:
    errors.append(f"MockDevice: {e}")

try:
    from core.automations import get_automation_info
    print("✓ Automations module imported")
    info = get_automation_info()
    print(f"  Found {len(info)} automations")
except Exception as e:
    errors.append(f"Automations: {e}")

if errors:
    print("❌ Import errors:")
    for err in errors:
        print(f"  - {err}")

print("\n" + "="*50)
print("Configuration test complete!")
print("\nIf all tests pass, run: python3 app.py --mock")