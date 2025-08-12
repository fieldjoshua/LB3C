"""
Mock LED Output Device for Testing

Simulates LED hardware without requiring physical devices.
Useful for development and testing on non-Raspberry Pi systems.
"""

import logging
import numpy as np
from typing import List, Tuple

from . import OutputDevice

logger = logging.getLogger(__name__)


class MockDevice(OutputDevice):
    """Mock LED device for testing without hardware"""
    
    def __init__(self, config):
        super().__init__(config)
        self.width = config.get('mock', {}).get('width', 64)
        self.height = config.get('mock', {}).get('height', 32)
        self.brightness = 1.0
        self.is_open = False
        self.frame_count = 0
        self.last_frame = None
        logger.info(f"MockDevice initialized: {self.width}x{self.height}")
    
    def open(self):
        """Initialize mock device"""
        self.is_open = True
        logger.info("MockDevice opened successfully")
        return True
    
    def close(self):
        """Close mock device"""
        self.is_open = False
        logger.info(f"MockDevice closed. Total frames rendered: {self.frame_count}")
    
    def is_connected(self) -> bool:
        """Check if mock device is connected"""
        return self.is_open
    
    def get_dimensions(self) -> Tuple[int, int]:
        """Get mock display dimensions"""
        return (self.width, self.height)
    
    def set_brightness(self, brightness: float):
        """Set mock brightness (0.0 to 1.0)"""
        self.brightness = max(0.0, min(1.0, brightness))
        logger.debug(f"MockDevice brightness set to {self.brightness}")
    
    def draw_rgb_frame(self, width: int, height: int, data: List[Tuple[int, int, int]]):
        """Simulate drawing a frame"""
        if not self.is_open:
            raise RuntimeError("MockDevice is not open")
        
        # Validate data
        expected_pixels = width * height
        if len(data) != expected_pixels:
            raise ValueError(f"Expected {expected_pixels} pixels, got {len(data)}")
        
        # Store frame for debugging
        self.last_frame = data
        self.frame_count += 1
        
        # Log every 30th frame to avoid spam
        if self.frame_count % 30 == 0:
            # Calculate average brightness of frame
            total_brightness = sum(sum(pixel) for pixel in data)
            avg_brightness = total_brightness / (len(data) * 3 * 255)
            logger.debug(f"MockDevice frame {self.frame_count}: {width}x{height}, "
                        f"avg brightness: {avg_brightness:.2%}")
    
    def clear(self):
        """Clear the mock display"""
        if self.is_open:
            black_frame = [(0, 0, 0)] * (self.width * self.height)
            self.draw_rgb_frame(self.width, self.height, black_frame)
            logger.debug("MockDevice cleared")