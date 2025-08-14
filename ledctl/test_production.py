#!/usr/bin/env python3
"""
Test production readiness
"""

import sys
import os
import signal
import time
import threading

print("=== Production Readiness Test ===\n")

# Test 1: Signal handling
print("1. Testing signal handling...")
signal_received = False

def test_signal_handler(signum, frame):
    global signal_received
    signal_received = True
    print("  ✓ Signal handler called")

signal.signal(signal.SIGUSR1, test_signal_handler)
os.kill(os.getpid(), signal.SIGUSR1)
time.sleep(0.1)

if signal_received:
    print("  ✓ Signal handling works")
else:
    print("  ✗ Signal handling failed")

# Test 2: Import availability
print("\n2. Testing imports...")
imports_ok = True

try:
    import flask
    print("  ✓ Flask available")
except ImportError:
    print("  ✗ Flask not found")
    imports_ok = False

try:
    import numpy
    print("  ✓ NumPy available")
except ImportError:
    print("  ✗ NumPy not found")
    imports_ok = False

try:
    import cv2
    print("  ✓ OpenCV available")
except ImportError:
    print("  ✗ OpenCV not found")
    imports_ok = False

# Test 3: Hardware libraries (optional)
print("\n3. Testing hardware libraries...")
try:
    import rgbmatrix
    print("  ✓ RGB Matrix library available")
except ImportError:
    print("  ✗ RGB Matrix library not found (OK if not on Pi)")

try:
    import rpi_ws281x
    print("  ✓ WS281x library available")
except ImportError:
    print("  ✗ WS281x library not found (OK if not on Pi)")

# Test 4: File permissions
print("\n4. Testing file permissions...")
can_write_uploads = os.access("uploads", os.W_OK) if os.path.exists("uploads") else False
can_write_logs = os.access(".", os.W_OK)

if can_write_uploads:
    print("  ✓ Can write to uploads directory")
else:
    print("  ✗ Cannot write to uploads directory")

if can_write_logs:
    print("  ✓ Can write logs")
else:
    print("  ✗ Cannot write logs")

# Test 5: GPIO permissions (Pi only)
print("\n5. Testing GPIO permissions...")
if os.path.exists("/dev/gpiomem"):
    if os.access("/dev/gpiomem", os.R_OK | os.W_OK):
        print("  ✓ GPIO accessible without sudo")
    else:
        print("  ✗ GPIO requires sudo")
else:
    print("  - Not on Raspberry Pi")

# Test 6: Thread cleanup
print("\n6. Testing thread cleanup...")
stop_event = threading.Event()
test_thread_stopped = False

def test_thread():
    global test_thread_stopped
    while not stop_event.is_set():
        time.sleep(0.1)
    test_thread_stopped = True

thread = threading.Thread(target=test_thread)
thread.daemon = True
thread.start()
stop_event.set()
thread.join(timeout=1.0)

if test_thread_stopped:
    print("  ✓ Thread cleanup works")
else:
    print("  ✗ Thread cleanup failed")

# Summary
print("\n" + "="*40)
print("Production Readiness Summary:")
print("="*40)

if imports_ok and signal_received and test_thread_stopped:
    print("✓ Basic requirements met")
    print("\nNext steps:")
    print("1. If on Pi and RGB Matrix not found:")
    print("   Run: ./install_hardware_libs.sh")
    print("2. Start the application:")
    print("   Run: ./start_production.sh")
else:
    print("✗ Some requirements not met")
    print("  Please fix the issues above")