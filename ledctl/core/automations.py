"""
Procedural animations and automation patterns for LED displays
"""

import numpy as np
import math
import colorsys
import random
from typing import List, Tuple, Dict, Any
from functools import lru_cache
from .frames import ProceduralAnimation


def hsv_to_rgb_np(h, s, v):
    """Vectorized HSV->RGB. h,s,v in [0,1]. Returns uint8 ndarray with last dim 3."""
    h = np.asarray(h, dtype=np.float32)
    s = np.asarray(s, dtype=np.float32)
    v = np.asarray(v, dtype=np.float32)
    h = np.mod(h, 1.0)
    s = np.clip(s, 0.0, 1.0)
    v = np.clip(v, 0.0, 1.0)

    i = np.floor(h * 6.0).astype(np.int32)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i_mod = np.mod(i, 6)

    r = np.choose(i_mod, [v, q, p, p, t, v])
    g = np.choose(i_mod, [t, v, v, q, p, p])
    b = np.choose(i_mod, [p, p, t, v, v, q])
    rgb = np.stack([r, g, b], axis=-1)
    return (rgb * 255.0).astype(np.uint8)


class ColorWave(ProceduralAnimation):
    """Smooth color wave animation - optimized version"""
    
    def __init__(self, width: int, height: int, fps: float = 30, 
                 wave_speed: float = 1.0, color_speed: float = 0.5):
        super().__init__(width, height, fps)
        self.wave_speed = wave_speed
        self.color_speed = color_speed
        # Pre-calculate constants
        self.x_positions = np.linspace(0, 2 * np.pi, width)
        self.x_normalized = np.linspace(0, 1, width)
        
    def generate_frame(self, time: float) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Vectorized wave calculation
        wave = np.sin(self.x_positions + time * self.wave_speed)
        wave = (wave + 1) * 0.5  # Normalize to 0-1
        
        # Vectorized hue calculation
        hues = (time * self.color_speed + self.x_normalized) % 1.0
        
        # Convert HSV to RGB for each column
        for x in range(self.width):
            r, g, b = colorsys.hsv_to_rgb(hues[x], 1.0, wave[x])
            color = np.array([int(r * 255), int(g * 255), int(b * 255)], dtype=np.uint8)
            frame[:, x] = color
                
        return frame


class RainbowCycle(ProceduralAnimation):
    """Classic rainbow cycle animation - optimized version"""
    
    def __init__(self, width: int, height: int, fps: float = 30, 
                 cycle_speed: float = 0.2, diagonal: bool = False):
        super().__init__(width, height, fps)
        self.cycle_speed = cycle_speed
        self.diagonal = diagonal
        # Pre-calculate position arrays
        if diagonal:
            x_grid, y_grid = np.meshgrid(range(width), range(height))
            self.positions = (x_grid + y_grid) / (width + height)
        else:
            self.positions = np.linspace(0, 1, width)
        
    def generate_frame(self, time: float) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Calculate all hues at once
        time_offset = time * self.cycle_speed
        
        if self.diagonal:
            hues = (self.positions + time_offset) % 1.0
            frame = hsv_to_rgb_np(hues, 1.0, 1.0)
        else:
            hues = (self.positions + time_offset) % 1.0
            # Convert HSV to RGB for each column
            for x in range(self.width):
                r, g, b = colorsys.hsv_to_rgb(hues[x], 1.0, 1.0)
                color = np.array([int(r * 255), int(g * 255), int(b * 255)], dtype=np.uint8)
                frame[:, x] = color
                
        return frame


class Plasma(ProceduralAnimation):
    """Plasma effect using sine wave interference - optimized version"""
    
    def __init__(self, width: int, height: int, fps: float = 30,
                 scale: float = 0.1, speed: float = 1.0):
        super().__init__(width, height, fps)
        self.scale = scale
        self.speed = speed
        # Pre-calculate coordinate grids
        x_coords = np.arange(width) * scale
        y_coords = np.arange(height) * scale
        self.cx, self.cy = np.meshgrid(x_coords, y_coords)
        
    def generate_frame(self, time: float) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        t = time * self.speed
        
        # Vectorized plasma calculation
        v1 = np.sin(self.cx + t)
        
        sin_t2 = math.sin(t/2)
        cos_t3 = math.cos(t/3)
        v2 = np.sin(10 * (self.cx * sin_t2 + self.cy * cos_t3) + t)
        
        cx_offset = self.cx + self.scale * math.sin(t/5)
        cy_offset = self.cy + self.scale * cos_t3
        v3 = np.sin(np.sqrt(100 * (cx_offset**2 + cy_offset**2) + 1) + t)
        
        # Combine and normalize
        v = (v1 + v2 + v3) / 3.0
        hues = (v + 1) * 0.5
        
        # Vectorized HSV->RGB conversion
        frame = hsv_to_rgb_np(hues, 1.0, 1.0)
        return frame


class Fire(ProceduralAnimation):
    """Animated fire effect - optimized version"""
    
    def __init__(self, width: int, height: int, fps: float = 30,
                 cooling: float = 55, sparking: float = 120):
        super().__init__(width, height, fps)
        self.cooling = cooling
        self.sparking = sparking
        self.heat = np.zeros((height + 2, width), dtype=float)  # Extra rows for boundary
        
    def generate_frame(self, time: float) -> np.ndarray:
        # Cool down every cell a little (vectorized)
        cooling_map = np.random.uniform(0, self.cooling/255, (self.height, self.width))
        self.heat[:self.height] = np.maximum(self.heat[:self.height] - cooling_map, 0)
        
        # Heat diffusion (vectorized where possible)
        for y in range(self.height - 1, 1, -1):
            self.heat[y] = (self.heat[y-1] + 2 * self.heat[y-2]) / 3.0
            
        # Randomly ignite new sparks at bottom
        spark_prob = self.sparking / 255.0
        spark_mask = np.random.random(self.width) < spark_prob
        self.heat[0, spark_mask] = np.random.uniform(0.7, 1.0, np.sum(spark_mask))
        
        # Convert heat to colors (vectorized)
        heat_clamped = np.clip(self.heat[:self.height], 0, 1)
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Black to red (heat < 0.33)
        mask1 = heat_clamped < 0.33
        frame[mask1, 0] = (heat_clamped[mask1] * 3 * 255).astype(np.uint8)
        
        # Red to yellow (0.33 <= heat < 0.66)
        mask2 = (heat_clamped >= 0.33) & (heat_clamped < 0.66)
        frame[mask2, 0] = 255
        frame[mask2, 1] = ((heat_clamped[mask2] - 0.33) * 3 * 255).astype(np.uint8)
        
        # Yellow to white (heat >= 0.66)
        mask3 = heat_clamped >= 0.66
        frame[mask3, 0] = 255
        frame[mask3, 1] = 255
        frame[mask3, 2] = np.minimum(255, ((heat_clamped[mask3] - 0.66) * 3 * 255).astype(np.uint8))
        
        # Flip vertically
        return frame[::-1]
        
        return frame


class Matrix(ProceduralAnimation):
    """Matrix-style falling text effect - optimized version"""
    
    def __init__(self, width: int, height: int, fps: float = 30,
                 drop_speed: float = 5.0, trail_length: int = 10):
        super().__init__(width, height, fps)
        self.drop_speed = drop_speed
        self.trail_length = trail_length
        self.drops = np.random.uniform(0, height, width)
        self.speeds = np.random.uniform(0.5, 1.5, width)
        # Pre-calculate brightness falloff
        self.brightness_falloff = np.linspace(1.0, 0.0, trail_length) ** 2
        
    def generate_frame(self, time: float) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Update drop positions (vectorized)
        self.drops += self.speeds * self.drop_speed * self.frame_duration
        
        # Reset drops that go off screen (vectorized)
        reset_mask = self.drops > self.height + self.trail_length
        num_reset = np.sum(reset_mask)
        if num_reset > 0:
            self.drops[reset_mask] = np.random.uniform(-self.trail_length, 0, num_reset)
            self.speeds[reset_mask] = np.random.uniform(0.5, 1.5, num_reset)
        
        # Draw drops (partially vectorized)
        for x in range(self.width):
            drop_y = int(self.drops[x])
            
            # Calculate valid y positions for the trail
            y_positions = drop_y - np.arange(self.trail_length)
            valid = (y_positions >= 0) & (y_positions < self.height)
            
            if np.any(valid):
                valid_y = y_positions[valid]
                valid_brightness = self.brightness_falloff[valid]
                
                # Set colors for valid positions
                frame[valid_y, x, 1] = (valid_brightness * 255).astype(np.uint8)  # Green
                frame[valid_y, x, 0] = (valid_brightness * 50).astype(np.uint8)   # Red
                frame[valid_y, x, 2] = (valid_brightness * 20).astype(np.uint8)   # Blue
                    
        return frame


class Sparkle(ProceduralAnimation):
    """Random sparkling/twinkling effect"""
    
    def __init__(self, width: int, height: int, fps: float = 30,
                 density: float = 0.02, fade_speed: float = 2.0,
                 color_mode: str = "white"):
        super().__init__(width, height, fps)
        self.density = density
        self.fade_speed = fade_speed
        self.color_mode = color_mode
        self.sparkles = {}  # Dict of (x,y): (brightness, hue)
        
    def generate_frame(self, time: float) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Add new sparkles
        num_new = int(self.width * self.height * self.density * self.frame_duration)
        for _ in range(num_new):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            if (x, y) not in self.sparkles:
                if self.color_mode == "rainbow":
                    hue = random.random()
                else:
                    hue = 0
                self.sparkles[(x, y)] = (1.0, hue)
                
        # Update and draw existing sparkles
        to_remove = []
        for (x, y), (brightness, hue) in self.sparkles.items():
            # Fade out
            brightness -= self.fade_speed * self.frame_duration
            
            if brightness <= 0:
                to_remove.append((x, y))
            else:
                self.sparkles[(x, y)] = (brightness, hue)
                
                # Draw sparkle
                if self.color_mode == "rainbow":
                    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, brightness)
                    frame[y, x] = [int(r * 255), int(g * 255), int(b * 255)]
                else:
                    val = int(brightness * 255)
                    frame[y, x] = [val, val, val]
                    
        # Remove faded sparkles
        for key in to_remove:
            del self.sparkles[key]
            
        return frame


class Strobe(ProceduralAnimation):
    """Strobe light effect with configurable patterns"""
    
    def __init__(self, width: int, height: int, fps: float = 30,
                 frequency: float = 10.0, duty_cycle: float = 0.5,
                 color: Tuple[int, int, int] = (255, 255, 255)):
        super().__init__(width, height, fps)
        self.frequency = frequency
        self.duty_cycle = duty_cycle
        self.color = np.array(color, dtype=np.uint8)
        
    def generate_frame(self, time: float) -> np.ndarray:
        # Calculate strobe state
        phase = (time * self.frequency) % 1.0
        
        if phase < self.duty_cycle:
            # Strobe on
            frame = np.full((self.height, self.width, 3), self.color, dtype=np.uint8)
        else:
            # Strobe off
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            
        return frame


class Breathe(ProceduralAnimation):
    """Breathing/pulsing effect"""
    
    def __init__(self, width: int, height: int, fps: float = 30,
                 breathe_speed: float = 0.5, min_brightness: float = 0.1,
                 color: Tuple[float, float, float] = (1.0, 1.0, 1.0)):
        super().__init__(width, height, fps)
        self.breathe_speed = breathe_speed
        self.min_brightness = min_brightness
        self.color = np.array(color)
        
    def generate_frame(self, time: float) -> np.ndarray:
        # Sine wave breathing pattern
        brightness = math.sin(time * self.breathe_speed * 2 * math.pi) * 0.5 + 0.5
        brightness = self.min_brightness + brightness * (1.0 - self.min_brightness)
        
        # Apply brightness to color
        color = (self.color * brightness * 255).astype(np.uint8)
        frame = np.full((self.height, self.width, 3), color, dtype=np.uint8)
        
        return frame


class Checkerboard(ProceduralAnimation):
    """Animated checkerboard pattern"""
    
    def __init__(self, width: int, height: int, fps: float = 30,
                 square_size: int = 8, scroll_speed: float = 0.0,
                 color1: Tuple[int, int, int] = (255, 255, 255),
                 color2: Tuple[int, int, int] = (0, 0, 0)):
        super().__init__(width, height, fps)
        self.square_size = square_size
        self.scroll_speed = scroll_speed
        self.color1 = np.array(color1, dtype=np.uint8)
        self.color2 = np.array(color2, dtype=np.uint8)
        
    def generate_frame(self, time: float) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Calculate scroll offset
        offset = int(time * self.scroll_speed * self.square_size) % (self.square_size * 2)
        
        for y in range(self.height):
            for x in range(self.width):
                # Determine which square we're in
                square_x = (x + offset) // self.square_size
                square_y = (y + offset) // self.square_size
                
                # Checkerboard logic
                if (square_x + square_y) % 2 == 0:
                    frame[y, x] = self.color1
                else:
                    frame[y, x] = self.color2
                    
        return frame


# Registry of available automations
AUTOMATION_REGISTRY = {
    'color_wave': ColorWave,
    'rainbow_cycle': RainbowCycle,
    'plasma': Plasma,
    'fire': Fire,
    'matrix': Matrix,
    'sparkle': Sparkle,
    'strobe': Strobe,
    'breathe': Breathe,
    'checkerboard': Checkerboard,
}


def get_automation_info() -> Dict[str, Dict[str, Any]]:
    """Get information about available automations"""
    info = {}
    for name, cls in AUTOMATION_REGISTRY.items():
        # Extract parameters from __init__ signature
        import inspect
        sig = inspect.signature(cls.__init__)
        params = {}
        
        for param_name, param in sig.parameters.items():
            if param_name in ['self', 'width', 'height', 'fps']:
                continue
                
            param_info = {
                'type': param.annotation.__name__ if param.annotation != param.empty else 'any',
                'default': param.default if param.default != param.empty else None
            }
            params[param_name] = param_info
            
        info[name] = {
            'class': cls.__name__,
            'parameters': params,
            'description': cls.__doc__.strip() if cls.__doc__ else ''
        }
        
    return info


def create_automation(name: str, width: int, height: int, 
                     fps: float = 30, **kwargs) -> ProceduralAnimation:
    """Create an automation instance by name"""
    if name not in AUTOMATION_REGISTRY:
        raise ValueError(f"Unknown automation: {name}")
        
    cls = AUTOMATION_REGISTRY[name]
    return cls(width, height, fps, **kwargs)