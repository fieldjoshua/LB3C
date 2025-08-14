"""
HUB75 LED Matrix Driver Implementation

Supports RGB LED matrices using the Adafruit RGB Matrix HAT
and rpi-rgb-led-matrix library.
"""

import logging
from typing import List, Tuple, Dict, Any
from . import OutputDevice, DeviceManager

logger = logging.getLogger(__name__)

try:
    from rgbmatrix import RGBMatrix, RGBMatrixOptions
    HAS_RGBMATRIX = True
except ImportError:
    HAS_RGBMATRIX = False
    logger.warning("rgbmatrix library not available - HUB75 support disabled")


class HUB75Device(OutputDevice):
    """HUB75 LED matrix implementation using rpi-rgb-led-matrix"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.matrix = None
        self.options = None
        
        # Extract HUB75-specific config
        hub75_config = config.get('hub75', {})
        self.rows = hub75_config.get('rows', 64)
        self.cols = hub75_config.get('cols', 64)
        self.chain_length = hub75_config.get('chain_length', 1)
        self.parallel = hub75_config.get('parallel', 1)
        self.hardware_mapping = hub75_config.get('hardware_mapping', 'adafruit-hat')
        self.gpio_slowdown = hub75_config.get('gpio_slowdown', 2)
        self.brightness = hub75_config.get('brightness', 100)
        self.pwm_bits = hub75_config.get('pwm_bits', 11)
        self.pwm_lsb_nanoseconds = hub75_config.get('pwm_lsb_nanoseconds', 130)
        
        # Set dimensions
        self.width = self.cols * self.chain_length
        self.height = self.rows * self.parallel
        
    def open(self) -> None:
        """Initialize HUB75 matrix hardware"""
        if not HAS_RGBMATRIX:
            raise RuntimeError("rgbmatrix library not installed")
            
        if self.is_open:
            return
            
        try:
            # Configure matrix options
            self.options = RGBMatrixOptions()
            self.options.rows = self.rows
            self.options.cols = self.cols
            self.options.chain_length = self.chain_length
            self.options.parallel = self.parallel
            self.options.hardware_mapping = self.hardware_mapping
            self.options.gpio_slowdown = self.gpio_slowdown
            self.options.brightness = self.brightness
            self.options.pwm_bits = self.pwm_bits
            self.options.pwm_lsb_nanoseconds = self.pwm_lsb_nanoseconds
            
            # Additional options that might be needed
            self.options.show_refresh_rate = False
            self.options.disable_hardware_pulsing = False
            
            # Create matrix instance
            self.matrix = RGBMatrix(options=self.options)
            self.offscreen_canvas = self.matrix.CreateFrameCanvas()
            self.is_open = True
            
            logger.info(f"HUB75 matrix opened: {self.width}x{self.height} "
                       f"(chains={self.chain_length}, parallel={self.parallel})")
                       
        except Exception as e:
            logger.error(f"Failed to open HUB75 matrix: {e}")
            raise RuntimeError(f"Cannot initialize HUB75 matrix: {e}")
            
    def close(self) -> None:
        """Clean up matrix resources"""
        if self.matrix and self.is_open:
            try:
                self.matrix.Clear()
                self.matrix = None
                self.is_open = False
                logger.info("HUB75 matrix closed")
            except Exception as e:
                logger.error(f"Error closing HUB75 matrix: {e}")
                
    def set_brightness(self, value: float) -> None:
        """
        Set matrix brightness
        
        Args:
            value: Brightness between 0.0 and 1.0
        """
        if not self.is_open or not self.matrix:
            raise RuntimeError("Device not open")
            
        # Convert to percentage (0-100)
        brightness_percent = max(0, min(100, int(value * 100)))
        self.matrix.brightness = brightness_percent
        logger.debug(f"HUB75 brightness set to {brightness_percent}%")
        
    def draw_rgb_frame(self, width: int, height: int, rgb_data: List[Tuple[int, int, int]]) -> None:
        """
        Draw RGB frame to matrix
        
        Args:
            width: Frame width
            height: Frame height
            rgb_data: Flattened list of RGB tuples
        """
        if not self.is_open or not self.matrix:
            raise RuntimeError("Device not open")
            
        # Validate frame dimensions
        if len(rgb_data) != width * height:
            raise ValueError(f"RGB data size mismatch: expected {width*height}, got {len(rgb_data)}")
            
        # Scale frame if needed
        if width != self.width or height != self.height:
            # For now, we'll do simple nearest-neighbor scaling
            # TODO: Use better scaling from frames.py when implemented
            scaled_data = self._scale_frame(rgb_data, width, height, self.width, self.height)
        else:
            scaled_data = rgb_data
            
        # Draw to matrix
        try:
            # Clear the offscreen canvas
            self.offscreen_canvas.Clear()
            
            for y in range(self.height):
                for x in range(self.width):
                    idx = y * self.width + x
                    if idx < len(scaled_data):
                        r, g, b = scaled_data[idx]
                        # Clamp values to 0-255 to prevent overflow
                        r = max(0, min(255, int(r)))
                        g = max(0, min(255, int(g)))
                        b = max(0, min(255, int(b)))
                        self.offscreen_canvas.SetPixel(x, y, r, g, b)
                        
            self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)
            
        except Exception as e:
            logger.error(f"Error drawing to HUB75 matrix: {e}")
            raise
            
    def _scale_frame(self, rgb_data: List[Tuple[int, int, int]], 
                     src_w: int, src_h: int, 
                     dst_w: int, dst_h: int) -> List[Tuple[int, int, int]]:
        """Simple nearest-neighbor scaling"""
        scaled = []
        x_ratio = src_w / dst_w
        y_ratio = src_h / dst_h
        
        for y in range(dst_h):
            for x in range(dst_w):
                src_x = int(x * x_ratio)
                src_y = int(y * y_ratio)
                src_idx = src_y * src_w + src_x
                
                if src_idx < len(rgb_data):
                    scaled.append(rgb_data[src_idx])
                else:
                    scaled.append((0, 0, 0))
                    
        return scaled


# Register device type
DeviceManager.register_device('HUB75', HUB75Device)