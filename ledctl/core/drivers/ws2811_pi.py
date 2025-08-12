"""
WS2811 Addressable LED Driver Implementation

Supports WS2811/WS2812/WS2812B LED strips using Raspberry Pi GPIO.
Requires rpi_ws281x library and root privileges.
"""

import json
import logging
from typing import List, Tuple, Dict, Any, Optional
from . import OutputDevice, DeviceManager

logger = logging.getLogger(__name__)

try:
    from rpi_ws281x import PixelStrip, Color
    HAS_WS281X = True
except ImportError:
    HAS_WS281X = False
    logger.warning("rpi_ws281x library not available - WS2811 support disabled")


class WS2811Device(OutputDevice):
    """WS2811 addressable LED implementation"""
    
    # LED strip configuration defaults
    LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA = 10          # DMA channel to use for generating signal
    LED_INVERT = False    # True to invert the signal (when using NPN transistor level shift)
    LED_CHANNEL = 0       # PWM channel (0 or 1)
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.strip = None
        self.pixel_map = None
        
        # Extract WS2811-specific config
        ws2811_config = config.get('ws2811', {})
        self.width = ws2811_config.get('width', 10)
        self.height = ws2811_config.get('height', 10)
        self.count = ws2811_config.get('count', self.width * self.height)
        self.gpio_pin = ws2811_config.get('gpio', 18)
        self.brightness = ws2811_config.get('brightness', 128)
        self.pixel_order = ws2811_config.get('pixel_order', 'GRB')
        self.map_file = ws2811_config.get('map_file', None)
        
        # Advanced settings
        self.freq_hz = ws2811_config.get('freq_hz', self.LED_FREQ_HZ)
        self.dma = ws2811_config.get('dma', self.LED_DMA)
        self.invert = ws2811_config.get('invert', self.LED_INVERT)
        self.channel = ws2811_config.get('channel', self.LED_CHANNEL)
        
        # Load pixel mapping if provided
        if self.map_file:
            self._load_pixel_map(self.map_file)
        else:
            # Generate default linear mapping
            self._generate_default_map()
            
    def _load_pixel_map(self, map_file: str) -> None:
        """Load pixel coordinate mapping from JSON file"""
        try:
            with open(map_file, 'r') as f:
                self.pixel_map = json.load(f)
                
            if len(self.pixel_map) != self.count:
                logger.warning(f"Pixel map size ({len(self.pixel_map)}) doesn't match LED count ({self.count})")
                
            logger.info(f"Loaded pixel map from {map_file}")
            
        except Exception as e:
            logger.error(f"Failed to load pixel map: {e}")
            self._generate_default_map()
            
    def _generate_default_map(self) -> None:
        """Generate default linear pixel mapping"""
        self.pixel_map = []
        for i in range(self.count):
            x = i % self.width
            y = i // self.width
            self.pixel_map.append({"x": x, "y": y})
            
    def _get_pixel_order(self) -> int:
        """Convert pixel order string to rpi_ws281x constant"""
        if not HAS_WS281X:
            return 0
            
        # Import color orders
        from rpi_ws281x import ws
        
        order_map = {
            'RGB': ws.WS2811_STRIP_RGB,
            'RBG': ws.WS2811_STRIP_RBG,
            'GRB': ws.WS2811_STRIP_GRB,
            'GBR': ws.WS2811_STRIP_GBR,
            'BRG': ws.WS2811_STRIP_BRG,
            'BGR': ws.WS2811_STRIP_BGR,
        }
        
        return order_map.get(self.pixel_order.upper(), ws.WS2811_STRIP_GRB)
        
    def open(self) -> None:
        """Initialize WS2811 LED strip"""
        if not HAS_WS281X:
            raise RuntimeError("rpi_ws281x library not installed")
            
        if self.is_open:
            return
            
        try:
            # Create PixelStrip object
            strip_type = self._get_pixel_order()
            self.strip = PixelStrip(
                self.count,
                self.gpio_pin,
                self.freq_hz,
                self.dma,
                self.invert,
                self.brightness,
                self.channel,
                strip_type
            )
            
            # Initialize the strip
            self.strip.begin()
            self.is_open = True
            
            # Clear strip on start
            self._clear_strip()
            
            logger.info(f"WS2811 strip opened: {self.count} LEDs on GPIO {self.gpio_pin}")
            
        except Exception as e:
            logger.error(f"Failed to open WS2811 strip: {e}")
            raise RuntimeError(f"Cannot initialize WS2811 strip: {e}. "
                             "Make sure you're running with sudo privileges.")
                             
    def close(self) -> None:
        """Clean up LED strip resources"""
        if self.strip and self.is_open:
            try:
                self._clear_strip()
                self.strip._cleanup()
                self.strip = None
                self.is_open = False
                logger.info("WS2811 strip closed")
            except Exception as e:
                logger.error(f"Error closing WS2811 strip: {e}")
                
    def _clear_strip(self) -> None:
        """Turn off all LEDs"""
        if self.strip:
            for i in range(self.count):
                self.strip.setPixelColor(i, Color(0, 0, 0))
            self.strip.show()
            
    def set_brightness(self, value: float) -> None:
        """
        Set strip brightness
        
        Args:
            value: Brightness between 0.0 and 1.0
        """
        if not self.is_open or not self.strip:
            raise RuntimeError("Device not open")
            
        # Convert to 0-255 range
        brightness = max(0, min(255, int(value * 255)))
        self.strip.setBrightness(brightness)
        self.strip.show()
        logger.debug(f"WS2811 brightness set to {brightness}")
        
    def draw_rgb_frame(self, width: int, height: int, rgb_data: List[Tuple[int, int, int]]) -> None:
        """
        Draw RGB frame to LED strip
        
        Args:
            width: Frame width
            height: Frame height
            rgb_data: Flattened list of RGB tuples
        """
        if not self.is_open or not self.strip:
            raise RuntimeError("Device not open")
            
        # Validate frame dimensions
        if len(rgb_data) != width * height:
            raise ValueError(f"RGB data size mismatch: expected {width*height}, got {len(rgb_data)}")
            
        # Map frame pixels to physical LEDs
        for led_idx, mapping in enumerate(self.pixel_map):
            if led_idx >= self.count:
                break
                
            # Get mapped coordinates
            x = mapping.get('x', 0)
            y = mapping.get('y', 0)
            
            # Calculate source pixel index with bounds checking
            if 0 <= x < width and 0 <= y < height:
                src_idx = y * width + x
                if src_idx < len(rgb_data):
                    r, g, b = rgb_data[src_idx]
                    # Note: Color() expects order based on strip type
                    # The library handles the conversion internally
                    self.strip.setPixelColor(led_idx, Color(r, g, b))
                else:
                    self.strip.setPixelColor(led_idx, Color(0, 0, 0))
            else:
                # Out of bounds - turn off LED
                self.strip.setPixelColor(led_idx, Color(0, 0, 0))
                
        # Update the strip
        self.strip.show()
        
    def create_serpentine_map(self, width: int, height: int) -> List[Dict[str, int]]:
        """
        Create a serpentine (zigzag) mapping for a grid of LEDs
        
        Args:
            width: Grid width
            height: Grid height
            
        Returns:
            List of coordinate mappings
        """
        mapping = []
        
        for y in range(height):
            if y % 2 == 0:
                # Even rows go left to right
                for x in range(width):
                    mapping.append({"x": x, "y": y})
            else:
                # Odd rows go right to left
                for x in range(width - 1, -1, -1):
                    mapping.append({"x": x, "y": y})
                    
        return mapping


# Register device type
DeviceManager.register_device('WS2811_PI', WS2811Device)