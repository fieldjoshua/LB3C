"""
WLED UDP Driver Implementation

Supports WLED/ESP32 devices via network UDP protocols.
Compatible with WARLS, DRGB, and DNRGB protocols.
"""

import socket
import struct
import logging
from typing import List, Tuple, Dict, Any
import time
from . import OutputDevice, DeviceManager

logger = logging.getLogger(__name__)


class WLEDDevice(OutputDevice):
    """WLED network LED controller implementation"""
    
    # Protocol constants
    WARLS_PROTOCOL = 1
    DRGB_PROTOCOL = 2
    DNRGB_PROTOCOL = 3
    
    # WARLS packet structure
    WARLS_HEADER_SIZE = 10
    WARLS_MAX_LEDS = 490  # Max LEDs per packet
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.socket = None
        
        # Extract WLED-specific config
        wled_config = config.get('wled', {})
        self.host = wled_config.get('host', '192.168.1.50')
        self.port = wled_config.get('port', 21324)
        self.timeout = wled_config.get('timeout', 2.0)
        self.protocol = wled_config.get('protocol', 'WARLS').upper()
        
        # Get dimensions from config or try to detect
        self.width = wled_config.get('width', 16)
        self.height = wled_config.get('height', 16)
        self.led_count = self.width * self.height
        
        # Network state
        self.last_packet_time = 0
        self.packet_interval = 1.0 / 60  # 60 FPS max
        
        # Brightness (0-255 for WLED)
        self.brightness = 255
        
    def open(self) -> None:
        """Initialize UDP socket for WLED communication"""
        if self.is_open:
            return
            
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.settimeout(self.timeout)
            
            # Test connection by sending a blank frame
            self._send_test_packet()
            
            self.is_open = True
            logger.info(f"WLED device opened: {self.host}:{self.port} "
                       f"({self.width}x{self.height}, protocol={self.protocol})")
                       
        except Exception as e:
            logger.error(f"Failed to open WLED device: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            raise RuntimeError(f"Cannot connect to WLED at {self.host}:{self.port}: {e}")
            
    def close(self) -> None:
        """Close UDP socket"""
        if self.socket and self.is_open:
            try:
                # Send black frame before closing
                self._send_black_frame()
                self.socket.close()
                self.socket = None
                self.is_open = False
                logger.info("WLED device closed")
            except Exception as e:
                logger.error(f"Error closing WLED device: {e}")
                
    def set_brightness(self, value: float) -> None:
        """
        Set global brightness
        
        Args:
            value: Brightness between 0.0 and 1.0
        """
        if not self.is_open:
            raise RuntimeError("Device not open")
            
        # Convert to 0-255 range
        self.brightness = max(0, min(255, int(value * 255)))
        logger.debug(f"WLED brightness set to {self.brightness}")
        
    def draw_rgb_frame(self, width: int, height: int, rgb_data: List[Tuple[int, int, int]]) -> None:
        """
        Send RGB frame to WLED device
        
        Args:
            width: Frame width
            height: Frame height
            rgb_data: Flattened list of RGB tuples
        """
        if not self.is_open or not self.socket:
            raise RuntimeError("Device not open")
            
        # Validate frame dimensions
        if len(rgb_data) != width * height:
            raise ValueError(f"RGB data size mismatch: expected {width*height}, got {len(rgb_data)}")
            
        # Rate limiting
        current_time = time.time()
        elapsed = current_time - self.last_packet_time
        if elapsed < self.packet_interval:
            time.sleep(self.packet_interval - elapsed)
            
        # Send based on protocol
        if self.protocol == 'WARLS':
            self._send_warls_frame(rgb_data)
        elif self.protocol == 'DRGB':
            self._send_drgb_frame(rgb_data)
        elif self.protocol == 'DNRGB':
            self._send_dnrgb_frame(rgb_data)
        else:
            raise ValueError(f"Unknown protocol: {self.protocol}")
            
        self.last_packet_time = time.time()
        
    def _send_warls_frame(self, rgb_data: List[Tuple[int, int, int]]) -> None:
        """Send frame using WARLS protocol"""
        # WARLS supports up to 490 LEDs per packet
        # Header: [protocol, timeout_hi, timeout_lo, led_count_hi, led_count_lo, 
        #          channel, sequence, physical_start_hi, physical_start_lo]
        
        led_count = min(len(rgb_data), self.led_count)
        packets_needed = (led_count + self.WARLS_MAX_LEDS - 1) // self.WARLS_MAX_LEDS
        
        sequence = 0
        for packet_idx in range(packets_needed):
            start_idx = packet_idx * self.WARLS_MAX_LEDS
            end_idx = min(start_idx + self.WARLS_MAX_LEDS, led_count)
            packet_led_count = end_idx - start_idx
            
            # Build header
            header = struct.pack(
                '!BBHBBBHB',
                self.WARLS_PROTOCOL,  # Protocol version
                0,  # Timeout high byte
                25,  # Timeout low byte (25 * 10ms = 250ms)
                packet_led_count >> 8,  # LED count high byte
                packet_led_count & 0xFF,  # LED count low byte
                0,  # Channel
                sequence,  # Sequence number
                start_idx >> 8,  # Physical start high byte
                start_idx & 0xFF  # Physical start low byte
            )
            
            # Build data
            data = bytearray()
            for i in range(start_idx, end_idx):
                if i < len(rgb_data):
                    r, g, b = rgb_data[i]
                    # Apply brightness
                    r = (r * self.brightness) // 255
                    g = (g * self.brightness) // 255
                    b = (b * self.brightness) // 255
                    data.extend([r, g, b])
                else:
                    data.extend([0, 0, 0])
                    
            # Send packet
            packet = header + data
            self.socket.sendto(packet, (self.host, self.port))
            
            sequence = (sequence + 1) % 256
            
    def _send_drgb_frame(self, rgb_data: List[Tuple[int, int, int]]) -> None:
        """Send frame using DRGB protocol"""
        # DRGB: Simple RGB data, max 490 LEDs
        led_count = min(len(rgb_data), self.led_count, 490)
        
        data = bytearray()
        data.append(2)  # Protocol identifier for DRGB
        
        for i in range(led_count):
            if i < len(rgb_data):
                r, g, b = rgb_data[i]
                # Apply brightness
                r = (r * self.brightness) // 255
                g = (g * self.brightness) // 255
                b = (b * self.brightness) // 255
                data.extend([r, g, b])
            else:
                data.extend([0, 0, 0])
                
        self.socket.sendto(data, (self.host, self.port))
        
    def _send_dnrgb_frame(self, rgb_data: List[Tuple[int, int, int]]) -> None:
        """Send frame using DNRGB protocol"""
        # DNRGB: [protocol, start_high, start_low, r, g, b, ...]
        led_count = min(len(rgb_data), self.led_count, 489)  # 489 due to 3-byte header
        
        data = bytearray()
        data.append(3)  # Protocol identifier for DNRGB
        data.append(0)  # Start index high byte
        data.append(0)  # Start index low byte
        
        for i in range(led_count):
            if i < len(rgb_data):
                r, g, b = rgb_data[i]
                # Apply brightness
                r = (r * self.brightness) // 255
                g = (g * self.brightness) // 255
                b = (b * self.brightness) // 255
                data.extend([r, g, b])
            else:
                data.extend([0, 0, 0])
                
        self.socket.sendto(data, (self.host, self.port))
        
    def _send_test_packet(self) -> None:
        """Send a test packet to verify connection"""
        try:
            # Send a single black pixel
            if self.protocol == 'WARLS':
                header = struct.pack(
                    '!BBHBBBHB',
                    self.WARLS_PROTOCOL, 0, 25, 0, 1, 0, 0, 0, 0
                )
                data = bytearray([0, 0, 0])
                self.socket.sendto(header + data, (self.host, self.port))
            elif self.protocol == 'DRGB':
                data = bytearray([2, 0, 0, 0])
                self.socket.sendto(data, (self.host, self.port))
            elif self.protocol == 'DNRGB':
                data = bytearray([3, 0, 0, 0, 0, 0])
                self.socket.sendto(data, (self.host, self.port))
                
        except Exception as e:
            raise RuntimeError(f"Failed to send test packet: {e}")
            
    def _send_black_frame(self) -> None:
        """Send all black frame to clear display"""
        try:
            black_data = [(0, 0, 0)] * self.led_count
            self.draw_rgb_frame(self.width, self.height, black_data)
        except:
            pass
            
    def get_info(self) -> Dict[str, Any]:
        """Get device information"""
        return {
            'host': self.host,
            'port': self.port,
            'protocol': self.protocol,
            'width': self.width,
            'height': self.height,
            'led_count': self.led_count,
            'connected': self.is_open
        }


# Register device type
DeviceManager.register_device('WLED', WLEDDevice)