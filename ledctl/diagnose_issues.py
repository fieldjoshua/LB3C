#!/usr/bin/env python3
"""
Diagnose configuration and runtime issues in the LB3C codebase
"""

import os
import sys
import traceback

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_env_file():
    """Check for .env file and required environment variables"""
    print("\n=== Checking Environment Configuration ===")
    
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    env_example_path = os.path.join(os.path.dirname(__file__), '.env.example')
    
    if not os.path.exists(env_path):
        print(f"❌ ERROR: .env file not found at {env_path}")
        print(f"   Copy {env_example_path} to {env_path} and configure it")
        return False
    else:
        print(f"✓ .env file exists")
        
    # Check if FLASK_SECRET_KEY is set
    from dotenv import load_dotenv
    load_dotenv(env_path)
    
    if not os.getenv('FLASK_SECRET_KEY') or os.getenv('FLASK_SECRET_KEY') == 'your-secret-key-here':
        print("❌ ERROR: FLASK_SECRET_KEY not properly configured in .env")
        print("   Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'")
        return False
    else:
        print("✓ FLASK_SECRET_KEY is configured")
        
    return True

def check_yaml_config():
    """Check YAML configuration file structure"""
    print("\n=== Checking YAML Configuration ===")
    
    config_path = 'config/device.yml'
    default_config_path = 'config/device.default.yml'
    
    # Check which config exists
    if os.path.exists(config_path):
        active_config = config_path
    elif os.path.exists(default_config_path):
        active_config = default_config_path
        print(f"ℹ Using default config: {default_config_path}")
    else:
        print(f"❌ ERROR: No configuration file found")
        return False
        
    # Load and validate YAML
    try:
        with open(active_config, 'r') as f:
            config = yaml.safe_load(f)
        print(f"✓ YAML config loaded successfully from {active_config}")
    except Exception as e:
        print(f"❌ ERROR loading YAML: {e}")
        return False
        
    # Check required sections
    required_sections = ['device', 'render', 'server']
    for section in required_sections:
        if section not in config:
            print(f"❌ ERROR: Missing required section '{section}' in config")
            return False
        else:
            print(f"✓ Config section '{section}' exists")
            
    # Check device type configuration
    device_type = config.get('device')
    if not device_type:
        print("❌ ERROR: No device type specified in config")
        return False
    
    print(f"✓ Device type: {device_type}")
    
    # Map device types to their config sections
    device_config_map = {
        'HUB75': 'hub75',
        'WS2811_PI': 'ws2811',
        'WLED': 'wled',
        'MOCK': 'mock'
    }
    
    if device_type in device_config_map:
        config_section = device_config_map[device_type]
        if config_section not in config:
            print(f"❌ ERROR: Device type '{device_type}' specified but '{config_section}' config section missing")
            return False
        else:
            print(f"✓ Device config section '{config_section}' exists")
    
    return True

def check_config_module():
    """Check the Config class implementation"""
    print("\n=== Checking Config Module ===")
    
    try:
        from core.config import Config, ConfigurationError
        print("✓ Config module imports successfully")
    except Exception as e:
        print(f"❌ ERROR importing Config module: {e}")
        traceback.print_exc()
        return False
        
    # Try to instantiate Config
    try:
        config = Config()
        print("✓ Config instance created")
    except ConfigurationError as e:
        print(f"❌ Configuration error: {e}")
        return False
    except Exception as e:
        print(f"❌ ERROR creating Config instance: {e}")
        traceback.print_exc()
        return False
        
    # Check validate method
    try:
        config.validate()
        print("✓ Config validation passed")
    except AttributeError as e:
        print(f"❌ AttributeError in config.validate(): {e}")
        print("   This is likely the issue at line 163")
        
        # Debug the config structure
        print("\n   Debugging config structure:")
        print(f"   - config.device type: {type(config.device)}")
        print(f"   - config.device value: {config.device}")
        
        if hasattr(config, 'yaml_config'):
            print(f"   - config.yaml_config type: {type(config.yaml_config)}")
            print(f"   - config.yaml_config keys: {list(config.yaml_config.keys()) if isinstance(config.yaml_config, dict) else 'Not a dict'}")
            
        return False
    except Exception as e:
        print(f"❌ ERROR in config.validate(): {e}")
        traceback.print_exc()
        return False
        
    return True

def check_imports():
    """Check all critical imports"""
    print("\n=== Checking Module Imports ===")
    
    modules_to_check = [
        ('flask', 'Flask'),
        ('flask_socketio', 'Flask-SocketIO'),
        ('eventlet', 'eventlet'),
        ('PIL', 'Pillow'),
        ('cv2', 'opencv-python'),
        ('yaml', 'pyyaml'),
        ('numpy', 'numpy'),
        ('dotenv', 'python-dotenv'),
        ('flask_limiter', 'flask-limiter'),
        ('flask_cors', 'flask-cors'),
        ('marshmallow', 'marshmallow'),
        ('redis', 'redis')
    ]
    
    all_good = True
    for module, package in modules_to_check:
        try:
            __import__(module)
            print(f"✓ {module} ({package})")
        except ImportError:
            print(f"❌ Missing: {module} - install with: pip install {package}")
            all_good = False
            
    return all_good

def check_project_structure():
    """Check required directories and files"""
    print("\n=== Checking Project Structure ===")
    
    required_paths = [
        ('uploads/', 'Upload directory'),
        ('config/', 'Config directory'),
        ('static/', 'Static files directory'),
        ('templates/', 'Templates directory'),
        ('core/', 'Core module directory'),
        ('core/drivers/', 'Drivers directory'),
        ('api/', 'API directory'),
    ]
    
    all_good = True
    for path, description in required_paths:
        full_path = os.path.join(os.path.dirname(__file__), path)
        if os.path.exists(full_path):
            print(f"✓ {description}: {path}")
        else:
            print(f"❌ Missing: {description} at {path}")
            all_good = False
            
    return all_good

def main():
    """Run all diagnostic checks"""
    print("LB3C Diagnostic Tool")
    print("===================")
    
    results = []
    
    # Run all checks
    results.append(("Environment", check_env_file()))
    results.append(("YAML Config", check_yaml_config()))
    results.append(("Config Module", check_config_module()))
    results.append(("Dependencies", check_imports()))
    results.append(("Project Structure", check_project_structure()))
    
    # Summary
    print("\n=== SUMMARY ===")
    all_passed = True
    for check_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{check_name}: {status}")
        if not passed:
            all_passed = False
            
    if all_passed:
        print("\n✅ All checks passed! The application should run.")
    else:
        print("\n❌ Some checks failed. Fix the issues above before running the application.")
        
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())