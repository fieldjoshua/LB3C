"""
Gamma Correction and RGB Balance Module

Provides color correction functionality for LED displays including:
- Gamma correction for perceptual linearity
- RGB channel balance adjustment
- Color temperature correction
- Brightness scaling
"""

import numpy as np
from typing import List, Tuple, Union, Optional
import logging

logger = logging.getLogger(__name__)


class GammaCorrector:
    """Handles gamma correction and color adjustments for LED output"""
    
    def __init__(self, gamma: float = 2.2):
        """
        Initialize gamma corrector
        
        Args:
            gamma: Gamma correction value (typically 1.8-2.5)
        """
        self.gamma = gamma
        self.rgb_balance = [1.0, 1.0, 1.0]
        self.brightness = 1.0
        
        # Pre-calculate lookup table for performance
        self._lut = None
        self._lut_gamma = None
        self._update_lut()
        
    def set_gamma(self, gamma: float) -> None:
        """Update gamma correction value"""
        self.gamma = max(0.1, min(5.0, gamma))  # Clamp to reasonable range
        self._update_lut()
        logger.debug(f"Gamma set to {self.gamma}")
        
    def set_rgb_balance(self, rgb: List[float]) -> None:
        """
        Set RGB channel balance multipliers
        
        Args:
            rgb: List of three multipliers [R, G, B], typically 0.0-2.0
        """
        self.rgb_balance = [
            max(0.0, min(2.0, rgb[0])),
            max(0.0, min(2.0, rgb[1])),
            max(0.0, min(2.0, rgb[2]))
        ]
        self._update_lut()
        logger.debug(f"RGB balance set to {self.rgb_balance}")
        
    def set_brightness(self, brightness: float) -> None:
        """
        Set global brightness multiplier
        
        Args:
            brightness: Brightness value 0.0-1.0
        """
        self.brightness = max(0.0, min(1.0, brightness))
        self._update_lut()
        logger.debug(f"Brightness set to {self.brightness}")
        
    def _update_lut(self) -> None:
        """Update lookup table for fast gamma correction"""
        # Create separate LUTs for each channel
        self._lut = []
        
        for channel in range(3):
            lut = np.zeros(256, dtype=np.uint8)
            
            for i in range(256):
                # Normalize to 0-1
                normalized = i / 255.0
                
                # Apply gamma correction
                corrected = np.power(normalized, self.gamma)
                
                # Apply RGB balance
                corrected *= self.rgb_balance[channel]
                
                # Apply brightness
                corrected *= self.brightness
                
                # Convert back to 0-255 and clamp
                lut[i] = int(np.clip(corrected * 255, 0, 255))
                
            self._lut.append(lut)
            
        self._lut_gamma = self.gamma
        
    def correct_frame(self, frame: np.ndarray, in_place: bool = False) -> np.ndarray:
        """
        Apply gamma correction and color adjustments to a frame
        
        Args:
            frame: Input frame as numpy array (H, W, 3) with values 0-255
            in_place: Modify the input frame directly if True
            
        Returns:
            Corrected frame
        """
        if not in_place:
            frame = frame.copy()
            
        # Ensure frame is uint8
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)
            
        # Apply lookup table to each channel
        for c in range(3):
            frame[:, :, c] = self._lut[c][frame[:, :, c]]
            
        return frame
        
    def correct_rgb_list(self, rgb_list: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
        """
        Apply corrections to a flat list of RGB values
        
        Args:
            rgb_list: List of RGB tuples
            
        Returns:
            Corrected RGB list
        """
        corrected = []
        
        for r, g, b in rgb_list:
            r = self._lut[0][r]
            g = self._lut[1][g]
            b = self._lut[2][b]
            corrected.append((r, g, b))
            
        return corrected
        
    def correct_rgb(self, r: int, g: int, b: int) -> Tuple[int, int, int]:
        """
        Apply corrections to a single RGB value
        
        Args:
            r, g, b: Input color values 0-255
            
        Returns:
            Corrected (r, g, b) tuple
        """
        return (
            self._lut[0][r],
            self._lut[1][g],
            self._lut[2][b]
        )


class ColorTemperature:
    """Adjust color temperature of LED output"""
    
    # Predefined color temperatures (Kelvin -> RGB multipliers)
    TEMPERATURES = {
        2000: (1.00, 0.56, 0.20),  # Candle
        2700: (1.00, 0.73, 0.42),  # Incandescent
        3000: (1.00, 0.78, 0.55),  # Warm white
        4000: (1.00, 0.87, 0.70),  # Cool white
        5000: (1.00, 0.93, 0.84),  # Daylight
        6500: (1.00, 1.00, 1.00),  # Neutral
        8000: (0.86, 0.90, 1.00),  # Cool daylight
        10000: (0.78, 0.85, 1.00), # Blue sky
    }
    
    @classmethod
    def get_rgb_multipliers(cls, kelvin: int) -> Tuple[float, float, float]:
        """
        Get RGB multipliers for a given color temperature
        
        Args:
            kelvin: Color temperature in Kelvin (2000-10000)
            
        Returns:
            (r, g, b) multipliers
        """
        # Clamp to valid range
        kelvin = max(2000, min(10000, kelvin))
        
        # Find surrounding temperatures for interpolation
        temps = sorted(cls.TEMPERATURES.keys())
        
        # Exact match
        if kelvin in cls.TEMPERATURES:
            return cls.TEMPERATURES[kelvin]
            
        # Find surrounding values
        lower_temp = None
        upper_temp = None
        
        for i, temp in enumerate(temps):
            if temp < kelvin:
                lower_temp = temp
            elif temp > kelvin:
                upper_temp = temp
                break
                
        # Edge cases
        if lower_temp is None:
            return cls.TEMPERATURES[temps[0]]
        if upper_temp is None:
            return cls.TEMPERATURES[temps[-1]]
            
        # Linear interpolation
        t = (kelvin - lower_temp) / (upper_temp - lower_temp)
        
        lower_rgb = cls.TEMPERATURES[lower_temp]
        upper_rgb = cls.TEMPERATURES[upper_temp]
        
        return tuple(
            lower_rgb[i] + t * (upper_rgb[i] - lower_rgb[i])
            for i in range(3)
        )
        
    @classmethod
    def apply_temperature(cls, gamma_corrector: GammaCorrector, kelvin: int) -> None:
        """
        Apply color temperature to a gamma corrector
        
        Args:
            gamma_corrector: GammaCorrector instance to modify
            kelvin: Target color temperature
        """
        multipliers = cls.get_rgb_multipliers(kelvin)
        
        # Combine with existing RGB balance
        combined = [
            gamma_corrector.rgb_balance[i] * multipliers[i]
            for i in range(3)
        ]
        
        gamma_corrector.set_rgb_balance(combined)


class AutoWhiteBalance:
    """Automatic white balance based on frame content"""
    
    @staticmethod
    def calculate_balance(frame: np.ndarray, 
                         percentile: float = 95) -> Tuple[float, float, float]:
        """
        Calculate RGB balance multipliers from a frame
        
        Args:
            frame: Input frame (H, W, 3)
            percentile: Percentile to use for white point detection
            
        Returns:
            (r, g, b) balance multipliers
        """
        # Find bright pixels (potential white points)
        brightness = np.mean(frame, axis=2)
        threshold = np.percentile(brightness, percentile)
        
        # Get pixels above threshold
        bright_mask = brightness > threshold
        bright_pixels = frame[bright_mask]
        
        if len(bright_pixels) == 0:
            return (1.0, 1.0, 1.0)
            
        # Calculate average of bright pixels
        avg_bright = np.mean(bright_pixels, axis=0)
        
        # Calculate multipliers to balance to neutral gray
        max_val = np.max(avg_bright)
        if max_val == 0:
            return (1.0, 1.0, 1.0)
            
        multipliers = max_val / avg_bright
        
        # Normalize so no channel exceeds 1.0
        max_mult = np.max(multipliers)
        if max_mult > 1.0:
            multipliers = multipliers / max_mult
            
        return tuple(multipliers)


# Convenience function for creating pre-configured correctors
def create_corrector(config: dict) -> GammaCorrector:
    """
    Create a GammaCorrector from configuration dict
    
    Args:
        config: Configuration dictionary with render settings
        
    Returns:
        Configured GammaCorrector instance
    """
    render_config = config.get('render', {})
    
    corrector = GammaCorrector(
        gamma=render_config.get('gamma', 2.2)
    )
    
    corrector.set_rgb_balance(
        render_config.get('rgb_balance', [1.0, 1.0, 1.0])
    )
    
    return corrector