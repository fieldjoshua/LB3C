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
        self.offscreen_canvas = None
        
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
        self.limit_refresh_rate_hz = hub75_config.get('limit_refresh_rate_hz', 0)
        self.show_refresh_rate = hub75_config.get('show_refresh_rate', False)
        self.drop_privileges = hub75_config.get('drop_privileges', False)
        self.disable_hardware_pulsing = hub75_config.get('disable_hardware_pulsing', True)
        self.scan_mode = hub75_config.get('scan_mode', 0)  # 0=progressive, 1=interlaced
        self.dithering = hub75_config.get('dithering', 0)  # 0=off, 1=on
        
        # Set dimensions
        self.width = self.cols * self.chain_length
        self.height = self.rows * self.parallel
        
        # Performance optimizations
        self._last_frame_data = None
        self._frame_buffer = None
        
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
            
            # Additional options for performance
            self.options.show_refresh_rate = self.show_refresh_rate
            self.options.disable_hardware_pulsing = self.disable_hardware_pulsing
            self.options.drop_privileges = self.drop_privileges
            
            # Advanced options
            if hasattr(self.options, 'scan_mode'):
                self.options.scan_mode = self.scan_mode
            if hasattr(self.options, 'dithering'):
                self.options.dithering = self.dithering
                
            if self.limit_refresh_rate_hz > 0:
                self.options.limit_refresh_rate_hz = self.limit_refresh_rate_hz
            
            # Create matrix instance
            self.matrix = RGBMatrix(options=self.options)
            self.offscreen_canvas = self.matrix.CreateFrameCanvas()
            
            # Pre-allocate frame buffer for performance
            self._frame_buffer = [(0, 0, 0)] * (self.width * self.height)
            
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
            
        # Draw to matrix with optimizations
        try:
            # Skip identical frames
            if self._last_frame_data is not None and scaled_data == self._last_frame_data:
                return
            
            # Use faster bulk pixel setting if available
            if hasattr(self.offscreen_canvas, 'SetPixels'):
                # scaled_data is already a list of (r,g,b) tuples
                self.offscreen_canvas.SetPixels(0, 0, self.width, self.height, scaled_data)
            else:
                # Fall back to individual pixel setting
                for y in range(self.height):
                    row_offset = y * self.width
                    for x in range(self.width):
                        idx = row_offset + x
                        if idx < len(scaled_data):
                            r, g, b = scaled_data[idx]
                            # Inline clamping for performance
                            self.offscreen_canvas.SetPixel(x, y, 
                                                         min(255, max(0, int(r))),
                                                         min(255, max(0, int(g))),
                                                         min(255, max(0, int(b))))
                        
            self.offscreen_canvas = self.matrix.SwapOnVSync(self.offscreen_canvas)
            self._last_frame_data = scaled_data
            
        except Exception as e:
            logger.error(f"Error drawing to HUB75 matrix: {e}")
            raise
            
    def _scale_frame(self, rgb_data: List[Tuple[int, int, int]], 
                     src_w: int, src_h: int, 
                     dst_w: int, dst_h: int) -> List[Tuple[int, int, int]]:
        """Optimized nearest-neighbor scaling with caching"""
        # Check if we can skip scaling
        if src_w == dst_w and src_h == dst_h:
            return rgb_data
            
        # Use pre-allocated buffer if possible
        if self._frame_buffer and len(self._frame_buffer) == dst_w * dst_h:
            scaled = self._frame_buffer
        else:
            scaled = [(0, 0, 0)] * (dst_w * dst_h)
            
        x_ratio = src_w / dst_w
        y_ratio = src_h / dst_h
        
        # Pre-calculate source indices for each row
        src_x_indices = [min(src_w - 1, int(x * x_ratio)) for x in range(dst_w)]
        
        dst_idx = 0
        for y in range(dst_h):
            src_y = min(src_h - 1, int(y * y_ratio))
            src_row_offset = src_y * src_w
            
            for src_x in src_x_indices:
                src_idx = src_row_offset + src_x
                if src_idx < len(rgb_data):
                    scaled[dst_idx] = rgb_data[src_idx]
                else:
                    scaled[dst_idx] = (0, 0, 0)
                dst_idx += 1
                    
        return scaled


# Register device type
DeviceManager.register_device('HUB75', HUB75Device)