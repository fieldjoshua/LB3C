"""
Procedural animations and automation patterns for LED displays
"""

import numpy as np
import math
import colorsys
import random
from typing import List, Tuple, Dict, Any
from .frames import ProceduralAnimation


class ColorWave(ProceduralAnimation):
    """Smooth color wave animation"""
    
    def __init__(self, width: int, height: int, fps: float = 30, 
                 wave_speed: float = 1.0, color_speed: float = 0.5):
        super().__init__(width, height, fps)
        self.wave_speed = wave_speed
        self.color_speed = color_speed
        
    def generate_frame(self, time: float) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        for y in range(self.height):
            for x in range(self.width):
                # Create wave pattern
                wave = math.sin((x / self.width) * 2 * math.pi + time * self.wave_speed)
                wave = (wave + 1) / 2  # Normalize to 0-1
                
                # Color cycling
                hue = (time * self.color_speed + (x / self.width)) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, wave)
                
                frame[y, x] = [int(r * 255), int(g * 255), int(b * 255)]
                
        return frame


class RainbowCycle(ProceduralAnimation):
    """Classic rainbow cycle animation"""
    
    def __init__(self, width: int, height: int, fps: float = 30, 
                 cycle_speed: float = 0.2, diagonal: bool = False):
        super().__init__(width, height, fps)
        self.cycle_speed = cycle_speed
        self.diagonal = diagonal
        
    def generate_frame(self, time: float) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        for y in range(self.height):
            for x in range(self.width):
                if self.diagonal:
                    # Diagonal rainbow
                    position = (x + y) / (self.width + self.height)
                else:
                    # Horizontal rainbow
                    position = x / self.width
                    
                hue = (position + time * self.cycle_speed) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                
                frame[y, x] = [int(r * 255), int(g * 255), int(b * 255)]
                
        return frame


class Plasma(ProceduralAnimation):
    """Plasma effect using sine wave interference"""
    
    def __init__(self, width: int, height: int, fps: float = 30,
                 scale: float = 0.1, speed: float = 1.0):
        super().__init__(width, height, fps)
        self.scale = scale
        self.speed = speed
        
    def generate_frame(self, time: float) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        t = time * self.speed
        
        for y in range(self.height):
            for x in range(self.width):
                # Create plasma pattern using multiple sine waves
                cx = x * self.scale
                cy = y * self.scale
                
                v1 = math.sin(cx + t)
                v2 = math.sin(10 * (cx * math.sin(t/2) + cy * math.cos(t/3)) + t)
                cx += self.scale * math.sin(t/5)
                cy += self.scale * math.cos(t/3)
                v3 = math.sin(math.sqrt(100 * (cx*cx + cy*cy) + 1) + t)
                
                v = (v1 + v2 + v3) / 3.0
                
                # Convert to color
                hue = (v + 1) * 0.5  # Normalize to 0-1
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                
                frame[y, x] = [int(r * 255), int(g * 255), int(b * 255)]
                
        return frame


class Fire(ProceduralAnimation):
    """Animated fire effect"""
    
    def __init__(self, width: int, height: int, fps: float = 30,
                 cooling: float = 55, sparking: float = 120):
        super().__init__(width, height, fps)
        self.cooling = cooling
        self.sparking = sparking
        self.heat = np.zeros((height, width), dtype=float)
        
    def generate_frame(self, time: float) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Cool down every cell a little
        self.heat = np.maximum(self.heat - np.random.uniform(0, self.cooling/255, 
                                                            (self.height, self.width)), 0)
        
        # Heat diffusion
        for y in range(self.height - 1, 1, -1):
            self.heat[y] = (self.heat[y-1] + 2 * self.heat[y-2]) / 3.0
            
        # Randomly ignite new sparks at bottom
        if random.randint(0, 255) < self.sparking:
            spark_x = random.randint(0, self.width - 1)
            self.heat[0, spark_x] = random.uniform(0.7, 1.0)
            
        # Convert heat to colors
        for y in range(self.height):
            for x in range(self.width):
                heat_val = self.heat[y, x]
                
                # Heat color mapping
                if heat_val < 0.33:
                    # Black to red
                    r = int(heat_val * 3 * 255)
                    g = 0
                    b = 0
                elif heat_val < 0.66:
                    # Red to yellow
                    r = 255
                    g = int((heat_val - 0.33) * 3 * 255)
                    b = 0
                else:
                    # Yellow to white
                    r = 255
                    g = 255
                    b = int((heat_val - 0.66) * 3 * 255)
                    
                frame[self.height - 1 - y, x] = [r, g, b]  # Flip vertically
                
        return frame


class Matrix(ProceduralAnimation):
    """Matrix-style falling text effect"""
    
    def __init__(self, width: int, height: int, fps: float = 30,
                 drop_speed: float = 5.0, trail_length: int = 10):
        super().__init__(width, height, fps)
        self.drop_speed = drop_speed
        self.trail_length = trail_length
        self.drops = np.random.uniform(0, height, width)
        self.speeds = np.random.uniform(0.5, 1.5, width)
        
    def generate_frame(self, time: float) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Update drop positions
        self.drops += self.speeds * self.drop_speed * self.frame_duration
        
        # Reset drops that go off screen
        reset_mask = self.drops > self.height + self.trail_length
        self.drops[reset_mask] = np.random.uniform(-self.trail_length, 0, 
                                                   np.sum(reset_mask))
        self.speeds[reset_mask] = np.random.uniform(0.5, 1.5, np.sum(reset_mask))
        
        # Draw drops
        for x in range(self.width):
            drop_y = int(self.drops[x])
            
            for i in range(self.trail_length):
                y = drop_y - i
                if 0 <= y < self.height:
                    brightness = 1.0 - (i / self.trail_length)
                    brightness *= brightness  # Exponential falloff
                    
                    # Green color with slight variation
                    g = int(brightness * 255)
                    r = int(brightness * 50)
                    b = int(brightness * 20)
                    
                    frame[y, x] = [r, g, b]
                    
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