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
            # Convert HSV to RGB for each pixel
            for y in range(self.height):
                for x in range(self.width):
                    r, g, b = colorsys.hsv_to_rgb(hues[y, x], 1.0, 1.0)
                    frame[y, x] = [int(r * 255), int(g * 255), int(b * 255)]
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
        
        # Convert to RGB - still need per-pixel for HSV conversion
        for y in range(self.height):
            for x in range(self.width):
                r, g, b = colorsys.hsv_to_rgb(hues[y, x], 1.0, 1.0)
                frame[y, x] = [int(r * 255), int(g * 255), int(b * 255)]
                
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


def _hsv_to_rgb_array(h: np.ndarray, s: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Vectorized HSV->RGB. Inputs in [0,1], any shape. Returns uint8 (..., 3)."""
    h = (h % 1.0) * 6.0
    i = np.floor(h).astype(np.int32) % 6
    f = h - np.floor(h)
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    rgb = np.stack([r, g, b], axis=-1)
    return np.clip(rgb * 255.0, 0, 255).astype(np.uint8)


class Metaballs(ProceduralAnimation):
    """Soft glowing blobs that orbit and merge. Smooth at low resolution."""

    def __init__(self, width: int, height: int, fps: float = 30,
                 num_balls: int = 3, speed: float = 0.7,
                 hue_speed: float = 0.04):
        super().__init__(width, height, fps)
        self.num_balls = max(1, int(num_balls))
        self.speed = speed
        self.hue_speed = hue_speed
        self.xx, self.yy = np.meshgrid(
            np.arange(width, dtype=np.float32),
            np.arange(height, dtype=np.float32),
        )
        # Each ball gets distinct phase + frequency so they don't sync up.
        self.phases = np.linspace(0, 2 * np.pi, self.num_balls, endpoint=False)
        self.freqs_x = 1.0 + 0.3 * np.arange(self.num_balls)
        self.freqs_y = 1.3 + 0.4 * np.arange(self.num_balls)
        self.radius = (width + height) / 6.0

    def generate_frame(self, time: float) -> np.ndarray:
        field = np.zeros((self.height, self.width), dtype=np.float32)
        for i in range(self.num_balls):
            cx = self.width * (0.5 + 0.4 * np.sin(time * self.speed * self.freqs_x[i] + self.phases[i]))
            cy = self.height * (0.5 + 0.4 * np.cos(time * self.speed * self.freqs_y[i] + self.phases[i]))
            d2 = (self.xx - cx) ** 2 + (self.yy - cy) ** 2
            field += (self.radius * self.radius) / (d2 + 0.5)
        v = np.tanh(field / float(self.num_balls))
        h = (field * 0.04 + time * self.hue_speed) % 1.0
        s = np.clip(0.6 + 0.3 * v, 0.0, 1.0)
        return _hsv_to_rgb_array(h, s, v)


class PlasmaFlow(ProceduralAnimation):
    """Sum-of-sines plasma with brightness shading. Replaces the boxy Plasma."""

    def __init__(self, width: int, height: int, fps: float = 30,
                 speed: float = 0.6, hue_speed: float = 0.07):
        super().__init__(width, height, fps)
        self.speed = speed
        self.hue_speed = hue_speed
        x = np.linspace(0.0, 1.0, max(width, 2), dtype=np.float32)
        y = np.linspace(0.0, 1.0, max(height, 2), dtype=np.float32)
        self.xx, self.yy = np.meshgrid(x[:width], y[:height])

    def generate_frame(self, time: float) -> np.ndarray:
        t = time * self.speed
        cx = self.xx - 0.5
        cy = self.yy - 0.5
        v = (
            np.sin(self.xx * 6.0 + t)
            + np.sin(self.yy * 6.0 + t * 1.3)
            + np.sin((self.xx + self.yy) * 5.0 + t * 0.7)
            + np.sin(np.sqrt(cx * cx + cy * cy) * 14.0 - t * 1.1)
        ) * 0.25  # roughly in [-1, 1]
        h = (v * 0.5 + 0.5 + time * self.hue_speed) % 1.0
        s = np.full_like(v, 0.85)
        bright = 0.55 + 0.45 * v  # gives shading, not flat fully-bright
        bright = np.clip(bright, 0.05, 1.0)
        return _hsv_to_rgb_array(h, s, bright)


class Tunnel(ProceduralAnimation):
    """Hypnotic radial tunnel. Twisting bands move toward / away from center."""

    def __init__(self, width: int, height: int, fps: float = 30,
                 zoom_speed: float = 0.6, twist: float = 2.0,
                 hue_speed: float = 0.08):
        super().__init__(width, height, fps)
        self.zoom_speed = zoom_speed
        self.twist = twist
        self.hue_speed = hue_speed
        cx = (width - 1) / 2.0
        cy = (height - 1) / 2.0
        xx, yy = np.meshgrid(
            np.arange(width, dtype=np.float32) - cx,
            np.arange(height, dtype=np.float32) - cy,
        )
        max_r = max(np.hypot(cx, cy), 1.0)
        self.r = np.hypot(xx, yy) / max_r
        self.theta = np.arctan2(yy, xx) / (2.0 * np.pi)

    def generate_frame(self, time: float) -> np.ndarray:
        u = self.twist * self.theta + 1.0 / (self.r + 0.15) + time * self.zoom_speed
        h = (u * 0.15 + time * self.hue_speed) % 1.0
        bands = 0.5 + 0.5 * np.sin(u * 2.0 * np.pi)
        # Vignette: dim toward edges so the tunnel feels deeper.
        vignette = np.clip(1.0 - 0.6 * self.r * self.r, 0.0, 1.0)
        v = np.clip(bands * (0.4 + 0.6 * vignette), 0.0, 1.0)
        s = np.full_like(v, 0.9)
        return _hsv_to_rgb_array(h, s, v)


class Aurora(ProceduralAnimation):
    """Northern-lights ribbons drifting horizontally. Cool palette, soft."""

    def __init__(self, width: int, height: int, fps: float = 30,
                 drift_speed: float = 0.4, ribbon_count: int = 2,
                 hue_center: float = 0.42, hue_range: float = 0.18):
        super().__init__(width, height, fps)
        self.drift_speed = drift_speed
        self.ribbon_count = max(1, int(ribbon_count))
        self.hue_center = hue_center  # 0.42 = teal-green
        self.hue_range = hue_range
        x = np.arange(width, dtype=np.float32)
        y = np.arange(height, dtype=np.float32)
        self.xx, self.yy = np.meshgrid(x, y)
        self.y_norm = self.yy / max(height - 1, 1)

    def generate_frame(self, time: float) -> np.ndarray:
        t = time * self.drift_speed
        # Sum of slow sines per ribbon, each centered at a different Y.
        intensity = np.zeros((self.height, self.width), dtype=np.float32)
        hue_field = np.zeros_like(intensity)
        for i in range(self.ribbon_count):
            y_center = (i + 1) / (self.ribbon_count + 1)
            wob = (
                0.10 * np.sin(self.xx * 0.55 + t * (1.0 + 0.3 * i))
                + 0.06 * np.sin(self.xx * 0.27 + t * 0.7)
            )
            band = np.exp(-((self.y_norm - y_center - wob) ** 2) / 0.012)
            intensity += band
            hue_field += band * (i / max(1, self.ribbon_count - 1))
        v = np.clip(intensity, 0.0, 1.0)
        # Hue centered on aurora green, wandering slightly with the field.
        hue = (
            self.hue_center
            + (hue_field / max(self.ribbon_count, 1) - 0.5) * self.hue_range
            + 0.05 * np.sin(time * 0.2)
        ) % 1.0
        s = np.full_like(v, 0.75)
        return _hsv_to_rgb_array(hue, s, v)


class DarkMatter(ProceduralAnimation):
    """Sparse glowing particles drifting on a black field. Pairs with --fade."""

    def __init__(self, width: int, height: int, fps: float = 30,
                 num_particles: int = 5, speed: float = 0.4,
                 sigma_frac: float = 0.07, hue_drift: float = 0.02,
                 seed: int = 42):
        super().__init__(width, height, fps)
        self.num = max(1, int(num_particles))
        self.speed = speed
        # Scale sigma with grid so particles look the same size whether
        # the animation is rendered at 10x10 or supersampled at 40x40.
        self.sigma = max(0.6, float(sigma_frac) * min(width, height))
        self.hue_drift = hue_drift
        rng = np.random.default_rng(seed)
        self.centers_x = rng.uniform(0.2, 0.8, self.num) * width
        self.centers_y = rng.uniform(0.2, 0.8, self.num) * height
        self.radii = rng.uniform(0.15, 0.4, self.num) * min(width, height)
        self.angular_v = rng.uniform(-1.0, 1.0, self.num)
        # Some particles also drift their orbit center (longer cycles).
        self.drift_v = rng.uniform(-0.15, 0.15, (self.num, 2))
        self.phase0 = rng.uniform(0, 2 * np.pi, self.num)
        self.hues = rng.uniform(0, 1, self.num)
        self.xx, self.yy = np.meshgrid(
            np.arange(width, dtype=np.float32),
            np.arange(height, dtype=np.float32),
        )
        self._two_sigma_sq = 2.0 * self.sigma * self.sigma

    def generate_frame(self, time: float) -> np.ndarray:
        accum = np.zeros((self.height, self.width, 3), dtype=np.float32)
        h_ones = np.empty_like(self.xx)
        s_field = np.full_like(self.xx, 0.85)
        for i in range(self.num):
            angle = self.phase0[i] + time * self.speed * self.angular_v[i]
            cx = self.centers_x[i] + self.radii[i] * np.cos(angle)
            cy = self.centers_y[i] + self.radii[i] * np.sin(angle)
            cx += self.drift_v[i, 0] * time
            cy += self.drift_v[i, 1] * time
            # Wrap-around so particles don't escape the grid.
            cx = cx % self.width
            cy = cy % self.height
            d2 = (self.xx - cx) ** 2 + (self.yy - cy) ** 2
            amp = np.exp(-d2 / self._two_sigma_sq)
            hue = (self.hues[i] + time * self.hue_drift) % 1.0
            h_ones.fill(hue)
            rgb = _hsv_to_rgb_array(h_ones, s_field, amp).astype(np.float32)
            accum += rgb
        return np.clip(accum, 0.0, 255.0).astype(np.uint8)


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
    'metaballs': Metaballs,
    'plasma_flow': PlasmaFlow,
    'tunnel': Tunnel,
    'aurora': Aurora,
    'dark_matter': DarkMatter,
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