#!/usr/bin/env python3
"""
Test to verify the LED animation system structure is complete
"""

import os
import sys

def check_file_exists(path, description):
    """Check if a file exists and report"""
    if os.path.exists(path):
        print(f"✓ {description}: {path}")
        return True
    else:
        print(f"✗ {description}: {path} - MISSING")
        return False

def check_module_structure():
    """Check all required modules exist"""
    print("Checking LED Animation System Structure\n")
    
    base_path = os.path.dirname(os.path.abspath(__file__))
    all_good = True
    
    # Core application files
    print("Core Application:")
    all_good &= check_file_exists(os.path.join(base_path, "app.py"), "Main Flask app")
    all_good &= check_file_exists(os.path.join(base_path, "requirements.txt"), "Dependencies")
    all_good &= check_file_exists(os.path.join(base_path, "config/device.default.yml"), "Configuration")
    
    # Core modules
    print("\nCore Modules:")
    all_good &= check_file_exists(os.path.join(base_path, "core/__init__.py"), "Core package")
    all_good &= check_file_exists(os.path.join(base_path, "core/frames.py"), "Frame processing")
    all_good &= check_file_exists(os.path.join(base_path, "core/gamma.py"), "Gamma correction")
    all_good &= check_file_exists(os.path.join(base_path, "core/playlists.py"), "Playlist management")
    all_good &= check_file_exists(os.path.join(base_path, "core/mapper.py"), "Coordinate mapping")
    
    # Driver modules
    print("\nDriver Modules:")
    all_good &= check_file_exists(os.path.join(base_path, "core/drivers/__init__.py"), "Drivers package")
    all_good &= check_file_exists(os.path.join(base_path, "core/drivers/mock.py"), "Mock driver")
    all_good &= check_file_exists(os.path.join(base_path, "core/drivers/hub75.py"), "HUB75 driver")
    all_good &= check_file_exists(os.path.join(base_path, "core/drivers/ws2811_pi.py"), "WS2811 driver")
    all_good &= check_file_exists(os.path.join(base_path, "core/drivers/wled_udp.py"), "WLED driver")
    
    # Web interface
    print("\nWeb Interface:")
    all_good &= check_file_exists(os.path.join(base_path, "templates/index.html"), "HTML template")
    all_good &= check_file_exists(os.path.join(base_path, "static/main.js"), "JavaScript client")
    all_good &= check_file_exists(os.path.join(base_path, "static/style.css"), "CSS styles")
    
    # Check for key features in app.py
    print("\nKey Features in app.py:")
    with open(os.path.join(base_path, "app.py"), 'r') as f:
        app_content = f.read()
        
    features = [
        ("Command-line args", "--mock" in app_content),
        ("Mock device support", "MOCK" in app_content),
        ("Socket.IO integration", "socketio" in app_content),
        ("File upload", "api_upload" in app_content),
        ("Parameter control", "set_parameter" in app_content),
        ("Device switching", "switch_device" in app_content),
        ("Graceful imports", "try:" in app_content and "import" in app_content)
    ]
    
    for feature, present in features:
        if present:
            print(f"✓ {feature}")
        else:
            print(f"✗ {feature} - MISSING")
            all_good = False
    
    print("\n" + "="*50)
    if all_good:
        print("✅ ALL CHECKS PASSED! The system structure is complete.")
        print("\nTo run the system:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run in mock mode: python app.py --mock")
        print("3. Open browser to http://localhost:5000")
    else:
        print("❌ Some components are missing.")
        
    return all_good

if __name__ == "__main__":
    check_module_structure()