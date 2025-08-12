"""
LED Output Device Base Class and Driver Management

Provides unified interface for different LED hardware types.
All hardware-specific implementations must inherit from OutputDevice.
"""

from abc import ABC, abstractmethod
from typing import Tuple, List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class OutputDevice(ABC):
    """Abstract base class for LED output devices"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize output device with configuration
        
        Args:
            config: Device-specific configuration dictionary
        """
        self.config = config
        self.width = 0
        self.height = 0
        self.is_open = False
        
    @abstractmethod
    def open(self) -> None:
        """
        Initialize hardware connection
        Raises:
            RuntimeError: If device cannot be opened
        """
        pass
        
    @abstractmethod
    def close(self) -> None:
        """Clean up hardware resources"""
        pass
        
    @abstractmethod
    def set_brightness(self, value: float) -> None:
        """
        Set global brightness
        
        Args:
            value: Brightness value between 0.0 and 1.0
        """
        pass
        
    @abstractmethod
    def draw_rgb_frame(self, width: int, height: int, rgb_data: List[Tuple[int, int, int]]) -> None:
        """
        Send RGB frame to hardware
        
        Args:
            width: Frame width
            height: Frame height
            rgb_data: Flattened list of RGB tuples (R, G, B values 0-255)
        """
        pass
    
    def get_dimensions(self) -> Tuple[int, int]:
        """Return device dimensions (width, height)"""
        return self.width, self.height
    
    def __enter__(self):
        """Context manager entry"""
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class DeviceManager:
    """Manages loading and switching between output devices"""
    
    _devices = {}
    _current_device: Optional[OutputDevice] = None
    
    @classmethod
    def register_device(cls, name: str, device_class: type):
        """Register a device type"""
        cls._devices[name] = device_class
        logger.info(f"Registered device type: {name}")
    
    @classmethod
    def create_device(cls, device_type: str, config: Dict[str, Any]) -> OutputDevice:
        """
        Create a device instance
        
        Args:
            device_type: Registered device type name
            config: Device configuration
            
        Returns:
            OutputDevice instance
            
        Raises:
            ValueError: If device type not registered
        """
        if device_type not in cls._devices:
            raise ValueError(f"Unknown device type: {device_type}")
            
        device_class = cls._devices[device_type]
        return device_class(config)
    
    @classmethod
    def get_current_device(cls) -> Optional[OutputDevice]:
        """Get currently active device"""
        return cls._current_device
    
    @classmethod
    def set_current_device(cls, device: OutputDevice):
        """Set the active device"""
        if cls._current_device and cls._current_device.is_open:
            cls._current_device.close()
        cls._current_device = device
        
    @classmethod
    def list_devices(cls) -> List[str]:
        """List all registered device types"""
        return list(cls._devices.keys())