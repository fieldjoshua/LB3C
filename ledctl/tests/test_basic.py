#!/usr/bin/env python3
"""
Basic test script for LED Animation Control System

This script tests basic functionality without requiring actual hardware.
Run with: python tests/test_basic.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import numpy as np
from core.drivers import DeviceManager, OutputDevice
from core.frames import FrameProcessor
from core.gamma import GammaCorrector

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockDevice(OutputDevice):
    """Mock LED device for testing"""
    
    def __init__(self, config):
        super().__init__(config)
        self.width = 16
        self.height = 16
        self.last_frame = None
        
    def open(self):
        self.is_open = True
        logger.info(f"Mock device opened: {self.width}x{self.height}")
        
    def close(self):
        self.is_open = False
        logger.info("Mock device closed")
        
    def set_brightness(self, value):
        logger.info(f"Mock brightness set to {value}")
        
    def draw_rgb_frame(self, width, height, rgb_data):
        self.last_frame = rgb_data
        logger.info(f"Mock frame drawn: {width}x{height}, {len(rgb_data)} pixels")


def test_device_manager():
    """Test device registration and creation"""
    print("\n=== Testing Device Manager ===")
    
    # Register mock device
    DeviceManager.register_device('MOCK', MockDevice)
    
    # List devices
    devices = DeviceManager.list_devices()
    print(f"Registered devices: {devices}")
    
    # Create mock device
    device = DeviceManager.create_device('MOCK', {})
    print(f"Created device: {type(device).__name__}")
    
    return device


def test_gamma_correction():
    """Test gamma correction"""
    print("\n=== Testing Gamma Correction ===")
    
    # Create corrector
    corrector = GammaCorrector(gamma=2.2)
    corrector.set_rgb_balance([1.2, 1.0, 0.8])
    corrector.set_brightness(0.8)
    
    # Test single RGB value
    r, g, b = corrector.correct_rgb(128, 128, 128)
    print(f"Input RGB(128,128,128) -> Output RGB({r},{g},{b})")
    
    # Test frame correction
    test_frame = np.ones((4, 4, 3), dtype=np.uint8) * 128
    corrected = corrector.correct_frame(test_frame)
    print(f"Frame correction applied: {test_frame[0,0]} -> {corrected[0,0]}")


def test_frame_processor():
    """Test frame processor"""
    print("\n=== Testing Frame Processor ===")
    
    processor = FrameProcessor(16, 16)
    
    # Create test image
    from PIL import Image
    test_img = Image.new('RGB', (32, 32), color='red')
    test_path = 'test_image.png'
    test_img.save(test_path)
    
    # Load image
    animation = processor.load_media(test_path)
    if animation:
        print(f"Loaded animation: {animation.frame_count} frames")
        frame = animation.frames[0]
        print(f"Frame shape: {frame.shape}")
        
        # Get RGB list
        rgb_list = animation.to_rgb_list(frame)
        print(f"RGB list length: {len(rgb_list)}")
    
    # Clean up
    os.remove(test_path)


def test_color_patterns():
    """Test various color patterns on mock device"""
    print("\n=== Testing Color Patterns ===")
    
    device = MockDevice({})
    device.open()
    
    width, height = device.get_dimensions()
    
    # Test solid colors
    colors = [
        ("Red", (255, 0, 0)),
        ("Green", (0, 255, 0)),
        ("Blue", (0, 0, 255)),
        ("White", (255, 255, 255)),
        ("Black", (0, 0, 0))
    ]
    
    for name, color in colors:
        frame = [color] * (width * height)
        device.draw_rgb_frame(width, height, frame)
        print(f"Drew {name} frame")
    
    # Test gradient
    gradient = []
    for y in range(height):
        for x in range(width):
            r = int(255 * x / width)
            g = int(255 * y / height)
            b = 128
            gradient.append((r, g, b))
    
    device.draw_rgb_frame(width, height, gradient)
    print("Drew gradient frame")
    
    device.close()


def main():
    """Run all tests"""
    print("LED Animation Control System - Basic Tests")
    print("=" * 50)
    
    try:
        # Test components
        device = test_device_manager()
        test_gamma_correction()
        test_frame_processor()
        test_color_patterns()
        
        print("\n✅ All basic tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()