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
        # Use the normalized `v` (already 0..1, tanh-clamped) instead of
        # raw `field` whose magnitude scales quadratically with the render
        # resolution. Otherwise supersampling cycles the hue many times
        # within a single LED's area = looks "zoomed in".
        h = (v * 0.4 + time * self.hue_speed) % 1.0
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
        # Normalized x so the ribbon wobble has the same number of waves
        # across the strip regardless of render resolution. Without this
        # supersampling would pack more wobbles per ribbon = looks "zoomed".
        self.x_norm = self.xx / max(width - 1, 1)

    def generate_frame(self, time: float) -> np.ndarray:
        t = time * self.drift_speed
        # Sum of slow sines per ribbon, each centered at a different Y.
        intensity = np.zeros((self.height, self.width), dtype=np.float32)
        hue_field = np.zeros_like(intensity)
        for i in range(self.ribbon_count):
            y_center = (i + 1) / (self.ribbon_count + 1)
            wob = (
                0.10 * np.sin(self.x_norm * 5.5 + t * (1.0 + 0.3 * i))
                + 0.06 * np.sin(self.x_norm * 2.7 + t * 0.7)
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


class SupernovaSampler(ProceduralAnimation):
    """Six supernovas against black space. Each fades in, undulates for ~30s,
    double-flashes its core at peak, then crossfades into the next.

    Designed to be played at >=2x supersampling so shape detail (rings,
    spikes, spirals) is visible on a coarse grid.
    """

    # Six novas, distinct shape + color palette per slot. Hues are in [0,1]:
    #   0.00 red, 0.08 orange, 0.13 gold, 0.30 lime, 0.40 emerald,
    #   0.50 cyan, 0.55 ice blue, 0.70 indigo, 0.75 violet, 0.92 hot pink.
    # Three additive Gaussian layers per nova, all centered:
    #   core (tiny + intense), mid (medium + saturated), halo (large + shaped).
    # Halo radius is bounded so at least the corner LEDs of a 10x10 grid stay
    # genuinely black.
    NOVAS = [
        dict(name='crimson_shock',
             core_hue=0.02, core_sat=1.0,  core_sigma=0.045, core_amp=1.4,
             mid_hue=0.95,  mid_sat=1.0,   mid_sigma=0.10,  mid_amp=0.95,
             halo_hue=0.52, halo_sat=0.95, halo_sigma=0.20, halo_amp=0.55,
             shape='rings', shape_param=2.4,
             undulate_rate=0.21),
        dict(name='violet_thorn',
             core_hue=0.78, core_sat=1.0,  core_sigma=0.045, core_amp=1.4,
             mid_hue=0.85,  mid_sat=1.0,   mid_sigma=0.10,  mid_amp=0.90,
             halo_hue=0.30, halo_sat=1.0,  halo_sigma=0.22, halo_amp=0.50,
             shape='spikes', shape_param=6,
             undulate_rate=0.17),
        dict(name='gold_blossom',
             core_hue=0.13, core_sat=1.0,  core_sigma=0.045, core_amp=1.4,
             mid_hue=0.06,  mid_sat=1.0,   mid_sigma=0.10,  mid_amp=0.95,
             halo_hue=0.92, halo_sat=0.95, halo_sigma=0.22, halo_amp=0.55,
             shape='rings', shape_param=3.2,
             undulate_rate=0.27),
        dict(name='glacier_forge',
             core_hue=0.58, core_sat=1.0,  core_sigma=0.045, core_amp=1.4,
             mid_hue=0.50,  mid_sat=1.0,   mid_sigma=0.10,  mid_amp=0.90,
             halo_hue=0.08, halo_sat=1.0,  halo_sigma=0.20, halo_amp=0.55,
             shape='spiral', shape_param=1.5,
             undulate_rate=0.19),
        dict(name='toxic_rays',
             core_hue=0.40, core_sat=1.0,  core_sigma=0.045, core_amp=1.4,
             mid_hue=0.32,  mid_sat=1.0,   mid_sigma=0.10,  mid_amp=0.95,
             halo_hue=0.92, halo_sat=0.95, halo_sigma=0.22, halo_amp=0.50,
             shape='spikes', shape_param=4,
             undulate_rate=0.23),
        dict(name='white_dwarf',
             core_hue=0.65, core_sat=1.0,  core_sigma=0.045, core_amp=1.4,
             mid_hue=0.72,  mid_sat=1.0,   mid_sigma=0.10,  mid_amp=0.85,
             halo_hue=0.00, halo_sat=0.0,  halo_sigma=0.22, halo_amp=0.65,
             shape='spiral', shape_param=2.5,
             undulate_rate=0.15),
    ]

    def __init__(self, width: int, height: int, fps: float = 30,
                 hold_seconds: float = 30.0,
                 pan_in_seconds: float = 1.2,
                 pan_out_seconds: float = 1.6,
                 black_gap_seconds: float = 0.35,
                 flash_seconds: float = 0.45):
        super().__init__(width, height, fps)
        self.hold = float(hold_seconds)
        self.pan_in = float(pan_in_seconds)
        self.pan_out = float(pan_out_seconds)
        self.black_gap = float(black_gap_seconds)
        self.flash = float(flash_seconds)
        # Each nova: pan in (zoom + brighten) -> double flash at peak ->
        # long hold with subtle undulation -> pan out (shrink + dim) ->
        # brief pure-black beat before the next nova zooms in.
        self.slot = (
            self.pan_in + self.flash + self.hold + self.pan_out + self.black_gap
        )
        x = np.arange(width, dtype=np.float32)
        y = np.arange(height, dtype=np.float32)
        self.xx, self.yy = np.meshgrid(x, y)
        self._scale = float(min(width, height))

    @staticmethod
    def _hue_rgb(hue: float, sat: float) -> Tuple[float, float, float]:
        h = np.array([hue % 1.0])
        s = np.array([sat])
        v = np.array([1.0])
        rgb = _hsv_to_rgb_array(h, s, v)[0]
        return float(rgb[0]) / 255.0, float(rgb[1]) / 255.0, float(rgb[2]) / 255.0

    def _render_nova(self, nova: dict, t_global: float, t_in_slot: float,
                     alpha: float, scale: float = 1.0) -> np.ndarray:
        """Render one centered nova with three additive Gaussian layers.

        alpha     - global brightness multiplier (0..1) for fade-in / pan-out
        scale     - radial scale (1.0 normal, <1 shrunken for pan effect)
        t_in_slot - flash envelope position (negative = no flash this frame)
        """
        # Always centered.
        cx = (self.width - 1) / 2.0
        cy = (self.height - 1) / 2.0

        # Subtle breathing + sub-pixel center wobble.
        breath = 1.0 + 0.05 * np.sin(t_global * nova['undulate_rate'])
        wobble_x = 0.25 * np.sin(t_global * nova['undulate_rate'] * 0.7)
        wobble_y = 0.25 * np.cos(t_global * nova['undulate_rate'] * 0.55)
        dx = self.xx - cx - wobble_x
        dy = self.yy - cy - wobble_y
        r2 = dx * dx + dy * dy
        r = np.sqrt(r2)

        sf = float(scale) * breath
        core_sigma = max(0.35, nova['core_sigma'] * self._scale * sf)
        mid_sigma = max(0.7, nova['mid_sigma'] * self._scale * sf)
        halo_sigma = max(1.2, nova['halo_sigma'] * self._scale * sf)
        core_g = np.exp(-r2 / (2.0 * core_sigma * core_sigma))
        mid_g = np.exp(-r2 / (2.0 * mid_sigma * mid_sigma))
        halo_g = np.exp(-r2 / (2.0 * halo_sigma * halo_sigma))

        # Shape modulates the outer halo only; core and mid stay clean blobs.
        shape = nova['shape']
        if shape == 'rings':
            ringwave = 0.5 + 0.5 * np.sin(r * nova['shape_param'] - t_global * 0.6)
            halo_g = halo_g * (0.35 + 0.65 * ringwave)
        elif shape == 'spikes':
            theta = np.arctan2(dy, dx)
            n = int(nova['shape_param'])
            spike = 0.5 + 0.5 * np.cos(n * theta + t_global * 0.25)
            halo_g = halo_g * (0.30 + 0.70 * spike)
        elif shape == 'spiral':
            theta = np.arctan2(dy, dx)
            spiral = 0.5 + 0.5 * np.sin(theta * 2.0 + r * nova['shape_param'] - t_global * 0.4)
            halo_g = halo_g * (0.30 + 0.70 * spiral)

        # Hard radial cutoff: anything past 2.6 sigma of the halo (with a
        # 1-pixel feather) is forced black so the corners stay genuinely
        # dark even at small grids.
        max_r = halo_sigma * 2.6
        cutoff = np.clip((max_r + 1.0 - r) / 1.5, 0.0, 1.0)
        halo_g *= cutoff
        mid_g *= cutoff

        # Apply layer amplitudes.
        core_amp = core_g * float(nova['core_amp'])
        mid_amp = mid_g * float(nova['mid_amp'])
        halo_amp = halo_g * float(nova['halo_amp'])

        # Double flash: boost the core only.
        if 0.0 <= t_in_slot <= self.flash:
            f1 = np.exp(-((t_in_slot - self.flash * 0.20) / (self.flash * 0.06)) ** 2)
            f2 = np.exp(-((t_in_slot - self.flash * 0.55) / (self.flash * 0.06)) ** 2)
            core_amp = core_amp * (1.0 + 3.5 * (f1 + f2))

        cr, cg, cb = self._hue_rgb(nova['core_hue'], nova['core_sat'])
        mr, mg, mb = self._hue_rgb(nova['mid_hue'], nova['mid_sat'])
        hr, hg, hb = self._hue_rgb(nova['halo_hue'], nova['halo_sat'])

        frame = np.empty((self.height, self.width, 3), dtype=np.float32)
        frame[..., 0] = core_amp * cr + mid_amp * mr + halo_amp * hr
        frame[..., 1] = core_amp * cg + mid_amp * mg + halo_amp * hg
        frame[..., 2] = core_amp * cb + mid_amp * mb + halo_amp * hb
        frame *= 255.0 * float(alpha)
        return frame  # caller clips & casts

    @staticmethod
    def _smoothstep(u: float) -> float:
        u = max(0.0, min(1.0, u))
        return u * u * (3.0 - 2.0 * u)

    def generate_frame(self, time: float) -> np.ndarray:
        n_novas = len(self.NOVAS)
        idx = int(time // self.slot) % n_novas
        t_in = time % self.slot
        cur = self.NOVAS[idx]

        # Phase boundaries (cumulative).
        b1 = self.pan_in
        b2 = b1 + self.flash
        b3 = b2 + self.hold
        b4 = b3 + self.pan_out
        # b4..slot is the black gap.

        if t_in < b1:
            # Pan in: zoom from 30% scale to full while alpha 0 -> 1.
            u = self._smoothstep(t_in / self.pan_in)
            scale = 0.3 + 0.7 * u
            frame = self._render_nova(cur, time, -1.0, alpha=u, scale=scale)
        elif t_in < b2:
            # Double flash at full size.
            flash_t = t_in - b1
            frame = self._render_nova(cur, time, flash_t, alpha=1.0, scale=1.0)
        elif t_in < b3:
            # Long undulation hold.
            frame = self._render_nova(cur, time, -1.0, alpha=1.0, scale=1.0)
        elif t_in < b4:
            # Pan away: shrink from full to ~10% while alpha 1 -> 0.
            u = self._smoothstep((t_in - b3) / self.pan_out)
            scale = 1.0 - 0.9 * u
            frame = self._render_nova(cur, time, -1.0,
                                      alpha=1.0 - u, scale=max(scale, 0.05))
        else:
            # Pure-black beat between novas. One frame's worth of nothing.
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

        return np.clip(frame, 0.0, 255.0).astype(np.uint8)


class SupernovaBlend(ProceduralAnimation):
    """Six supernovas, each crossfading slowly into the next over ~30s.

    Differences vs. supernova_sampler:
      - Long overlapping crossfade (30s default), not a pan-away.
      - Core layer is a hard disc with anti-aliased edge (no blur).
      - Halo shape modulator can be sharpened per-nova so the outer
        rings/spikes/spirals have hard black gaps between bright bands.
    """

    # Concentric layers per nova:
    #   core      - hard disc at center (no blur, super-concentrated)
    #   [GAP]     - genuinely black ring between core and mid
    #   mid       - annular Gaussian ring at mid_peak (color #2)
    #   [GAP]     - genuinely black ring between mid and halo
    #   halo      - annular Gaussian ring at halo_peak, shape-modulated
    #   [black]   - corners stay black via radial cutoff
    # Layered design: hard sharp core + soft Gaussian mid + soft Gaussian halo.
    # Colors blend smoothly outward as a graduated radial gradient (NOT
    # discrete planet-like rings). Shape modulator on halo is intentionally
    # gentle so it suggests motion/structure without splitting into hard bands.
    # Hue: three discrete zones (core / mid / halo), hard 3-way split.
    # Brightness: each zone has its OWN annular Gaussian "bump" so the
    #   outer layers look soft and diffuse (blurred), not like flat color
    #   blocks. The hue itself stays exactly one of three per pixel.
    # Radii pulled back up a bit so the nova has more presence on the strip.
    NOVAS = [
        dict(name='crimson_shock',
             core_hue=0.02, mid_hue=0.95, halo_hue=0.52,
             core_radius=0.10, mid_at=0.20, mid_width=0.06,
             halo_at=0.34,    halo_width=0.08, sat=1.0,
             shape='rings', shape_param=3.0, modulation_depth=0.30,
             undulate_rate=0.21),
        dict(name='violet_thorn',
             core_hue=0.78, mid_hue=0.85, halo_hue=0.30,
             core_radius=0.10, mid_at=0.20, mid_width=0.06,
             halo_at=0.36,    halo_width=0.08, sat=1.0,
             shape='spikes', shape_param=6, modulation_depth=0.25,
             undulate_rate=0.17),
        dict(name='gold_blossom',
             core_hue=0.13, mid_hue=0.06, halo_hue=0.92,
             core_radius=0.10, mid_at=0.20, mid_width=0.06,
             halo_at=0.36,    halo_width=0.08, sat=1.0,
             shape='rings', shape_param=4.0, modulation_depth=0.30,
             undulate_rate=0.27),
        dict(name='glacier_forge',
             core_hue=0.58, mid_hue=0.50, halo_hue=0.08,
             core_radius=0.10, mid_at=0.20, mid_width=0.06,
             halo_at=0.34,    halo_width=0.08, sat=1.0,
             shape='spiral', shape_param=2.0, modulation_depth=0.25,
             undulate_rate=0.19),
        dict(name='toxic_rays',
             core_hue=0.40, mid_hue=0.32, halo_hue=0.92,
             core_radius=0.10, mid_at=0.20, mid_width=0.06,
             halo_at=0.36,    halo_width=0.08, sat=1.0,
             shape='spikes', shape_param=4, modulation_depth=0.30,
             undulate_rate=0.23),
        dict(name='white_dwarf',
             core_hue=0.65, mid_hue=0.72, halo_hue=0.00, halo_sat=0.0,
             core_radius=0.10, mid_at=0.20, mid_width=0.06,
             halo_at=0.36,    halo_width=0.08, sat=1.0,
             shape='spiral', shape_param=3.0, modulation_depth=0.25,
             undulate_rate=0.15),
    ]

    def __init__(self, width: int, height: int, fps: float = 30,
                 hold_seconds: float = 30.0,
                 crossfade_seconds: float = 30.0,
                 flash_seconds: float = 0.45,
                 dark_matter_count: int = 5,
                 dark_matter_seed: int = 17):
        super().__init__(width, height, fps)
        self.hold = float(hold_seconds)
        self.crossfade = float(crossfade_seconds)
        self.flash = float(flash_seconds)
        self.slot = self.crossfade + self.flash + self.hold
        x = np.arange(width, dtype=np.float32)
        y = np.arange(height, dtype=np.float32)
        self.xx, self.yy = np.meshgrid(x, y)
        self._scale = float(min(width, height))

        # Dark-matter "donuts": concentric Gaussian rings of darkness that
        # dim brightness at a given radius from the nova's center. Mix of
        # SKINNY (narrow sigma) and BLURRED (wider sigma) rings. Each ring
        # slowly drifts radially so the pattern isn't static.
        rng = np.random.default_rng(dark_matter_seed)
        n = max(0, int(dark_matter_count))
        self.n_dark = n
        # Ring radii spread across the lit zones, with enough spacing that
        # the rings don't overlap themselves into a wall of black. Sample
        # evenly with a small jitter rather than fully uniform.
        evenly = np.linspace(0.11, 0.40, n) if n > 0 else np.zeros(n)
        jitter = rng.uniform(-0.015, 0.015, n)
        self.dark_r0 = (evenly + jitter).astype(np.float32)
        # Mix of skinny and blurred rings. Skinny rings make fine dark
        # threads; blurred rings make broad soft shadows that feather out.
        skinny = rng.uniform(0.010, 0.025, n).astype(np.float32)
        blurred = rng.uniform(0.045, 0.080, n).astype(np.float32)
        is_skinny = (rng.random(n) < 0.5)
        self.dark_sigma_r = np.where(is_skinny, skinny, blurred)
        # All rings reach pure black at their darkest (radial center of the
        # ring). Gaussian falloff makes the dimming get lighter as you move
        # radially away from each ring's center.
        self.dark_strength = np.full(n, 1.0, dtype=np.float32)
        # Slow radial drift (rings expand/contract very slowly).
        self.dark_drift = rng.uniform(-0.012, 0.012, n).astype(np.float32)

    @staticmethod
    def _hue_rgb(hue: float, sat: float) -> Tuple[float, float, float]:
        h = np.array([hue % 1.0])
        s = np.array([sat])
        v = np.array([1.0])
        rgb = _hsv_to_rgb_array(h, s, v)[0]
        return float(rgb[0]) / 255.0, float(rgb[1]) / 255.0, float(rgb[2]) / 255.0

    @staticmethod
    def _smoothstep(u: float) -> float:
        u = max(0.0, min(1.0, u))
        return u * u * (3.0 - 2.0 * u)

    @staticmethod
    def _lerp_hue(h1: float, h2: float, t: np.ndarray) -> np.ndarray:
        """Lerp between two hues along the SHORT way around the wheel."""
        diff = (h2 - h1) % 1.0
        if diff > 0.5:
            diff -= 1.0
        return (h1 + diff * t) % 1.0

    def _render_nova(self, nova: dict, t_global: float, t_in_slot: float,
                     alpha: float) -> np.ndarray:
        """One-hue-per-pixel renderer.

        Each pixel's color is determined by lerping core_hue -> mid_hue ->
        halo_hue based on its radial position. Brightness is a separate
        radial envelope (hard core + soft halo) plus a soft modulation
        from the shape function. Because each pixel has exactly one hue,
        layers cannot wash each other out at the center.
        """
        cx = (self.width - 1) / 2.0
        cy = (self.height - 1) / 2.0

        breath = 1.0 + 0.05 * np.sin(t_global * nova['undulate_rate'])
        wobble_x = 0.25 * np.sin(t_global * nova['undulate_rate'] * 0.7)
        wobble_y = 0.25 * np.cos(t_global * nova['undulate_rate'] * 0.55)
        dx = self.xx - cx - wobble_x
        dy = self.yy - cy - wobble_y
        r = np.sqrt(dx * dx + dy * dy)

        # Radial bands (in 'pixels' at this resolution).
        scale = self._scale * breath
        core_r = max(0.5, nova['core_radius'] * scale)
        mid_r = nova['mid_at'] * scale
        mid_w = max(0.7, nova['mid_width'] * scale)
        halo_r = nova['halo_at'] * scale
        halo_w = max(1.0, nova['halo_width'] * scale)

        # HUE FIELD: hard 3-way split. Boundaries are at the midpoints
        # between the core/mid and mid/halo radii. Each pixel ends up
        # with EXACTLY ONE of {core_hue, mid_hue, halo_hue}.
        ch = float(nova['core_hue'])
        mh = float(nova['mid_hue'])
        hh = float(nova['halo_hue'])
        b_cm = (core_r + mid_r) / 2.0
        b_mh = (mid_r + halo_r) / 2.0
        hue_field = np.where(r < b_cm, ch,
                     np.where(r < b_mh, mh, hh)).astype(np.float32)

        # Saturation field: per-zone too. Halo_sat lets e.g. white_dwarf's
        # outer ring desaturate to white.
        sat_core = float(nova.get('sat', 1.0))
        sat_halo = float(nova.get('halo_sat', sat_core))
        sat_field = np.where(r < b_mh, sat_core, sat_halo).astype(np.float32)

        # BRIGHTNESS: each zone has its own brightness bump so the outer
        # layers look soft/blurry rather than flat color blocks. Hue stays
        # one of three; only brightness varies smoothly within a zone.
        # Core: hard disc, full 1.0 (no blur on the center).
        # Mid:  annular Gaussian peaking at mid_r, capped at 0.75.
        # Halo: annular Gaussian peaking at halo_r, capped at 0.55.
        core_disc = np.clip(core_r + 0.5 - r, 0.0, 1.0)
        mid_bump = 0.75 * np.exp(-((r - mid_r) ** 2) / (2.0 * mid_w * mid_w))
        halo_bump = 0.55 * np.exp(-((r - halo_r) ** 2) / (2.0 * halo_w * halo_w))
        value_field = np.maximum(np.maximum(core_disc, mid_bump), halo_bump)

        # Soft shape modulation on brightness only (not hue). Clamped so it
        # never cuts to black.
        depth = float(nova.get('modulation_depth', 0.30))
        shape = nova['shape']
        if shape == 'rings':
            raw = 0.5 + 0.5 * np.sin(r * nova['shape_param'] - t_global * 0.6)
        elif shape == 'spikes':
            theta = np.arctan2(dy, dx)
            n = int(nova['shape_param'])
            raw = 0.5 + 0.5 * np.cos(n * theta + t_global * 0.25)
        elif shape == 'spiral':
            theta = np.arctan2(dy, dx)
            raw = 0.5 + 0.5 * np.sin(theta * 2.0 + r * nova['shape_param']
                                     - t_global * 0.4)
        else:
            raw = np.ones_like(value_field)
        modulator = (1.0 - depth) + depth * raw  # [1-depth, 1]
        # Don't modulate inside the core - keep it crisp & full-bright.
        modulator = np.where(core_disc > 0.5, 1.0, modulator)
        value_field = value_field * modulator

        # Hard radial cutoff so corners stay black. Set just past the halo's
        # outer falloff so a generous black margin remains.
        max_r = halo_r + halo_w * 2.0
        cutoff = np.clip((max_r + 1.0 - r) / 1.5, 0.0, 1.0)
        value_field = value_field * cutoff

        # Concentric dark-matter donuts: each is an annular Gaussian
        # darkness at radius ring_r with radial width sigma_r. Skinny
        # rings read as fine dark threads; blurred rings as broad shadows.
        # Rings drift radially over time. Core is spared from dimming.
        if self.n_dark > 0:
            dark_field = np.zeros_like(value_field)
            for i in range(self.n_dark):
                ring_r = (float(self.dark_r0[i])
                          + t_global * float(self.dark_drift[i])) * scale
                sigma_r = max(0.5, float(self.dark_sigma_r[i]) * scale)
                spot = float(self.dark_strength[i]) * np.exp(
                    -((r - ring_r) ** 2) / (2.0 * sigma_r * sigma_r)
                )
                np.maximum(dark_field, spot, out=dark_field)
            dark_field = dark_field * (1.0 - core_disc)
            value_field = value_field * (1.0 - dark_field)

        # Double flash boosts the core's brightness (not hue).
        if 0.0 <= t_in_slot <= self.flash:
            f1 = np.exp(-((t_in_slot - self.flash * 0.20) / (self.flash * 0.06)) ** 2)
            f2 = np.exp(-((t_in_slot - self.flash * 0.55) / (self.flash * 0.06)) ** 2)
            value_field = value_field + core_disc * 2.5 * (f1 + f2)

        rgb = _hsv_to_rgb_array(
            hue_field.astype(np.float32),
            np.clip(sat_field, 0.0, 1.0).astype(np.float32),
            np.clip(value_field, 0.0, 1.0).astype(np.float32),
        )
        return rgb.astype(np.float32) * float(alpha)

    def generate_frame(self, time: float) -> np.ndarray:
        n = len(self.NOVAS)
        cycle_idx = int(time // self.slot)
        idx = cycle_idx % n
        t_in = time % self.slot
        cur = self.NOVAS[idx]

        if t_in < self.crossfade:
            # Long crossfade: this nova fades in on top of the previous
            # nova fading out. On the very first cycle there's no previous.
            u = self._smoothstep(t_in / self.crossfade)
            frame = self._render_nova(cur, time, -1.0, alpha=u)
            if cycle_idx > 0:
                prev = self.NOVAS[(idx - 1) % n]
                frame = frame + self._render_nova(prev, time, -1.0,
                                                  alpha=1.0 - u)
        elif t_in < self.crossfade + self.flash:
            # Now fully visible: double flash from the core.
            flash_t = t_in - self.crossfade
            frame = self._render_nova(cur, time, flash_t, alpha=1.0)
        else:
            # Long stable hold with subtle undulation.
            frame = self._render_nova(cur, time, -1.0, alpha=1.0)

        return np.clip(frame, 0.0, 255.0).astype(np.uint8)


class CosmicDrift(ProceduralAnimation):
    """Layered cosmic scene with parallax depth.

    Five composited layers, each moving at its own speed, scale, and
    color temperature so the eye reads depth (atmospheric perspective +
    motion parallax):

      1. Deep nebula     - sum-of-sines field, slow, cool palette, dim
      2. Mid dust        - drifting warm Gaussian blobs, moderate motion
      3. Far stars       - faint blue-white pinpoints, slow drift, slow twinkle
      4. Near stars      - bright pinpoints, faster drift, fast twinkle
      5. Pulse           - occasional bright shockwave from center

    Composited additively then clipped, so the bright foreground layers
    pop above the dim background layers without washing them out.
    """

    def __init__(self, width: int, height: int, fps: float = 30,
                 num_dust: int = 10,
                 num_far_stars: int = 14,
                 num_near_stars: int = 8,
                 pulse_period: float = 11.0,
                 seed: int = 42):
        super().__init__(width, height, fps)
        self._scale = float(min(width, height))
        x = np.arange(width, dtype=np.float32)
        y = np.arange(height, dtype=np.float32)
        self.xx, self.yy = np.meshgrid(x, y)

        rng = np.random.default_rng(seed)

        # ---- Nebula: 4 plane waves at random angles + low frequencies.
        # The result is a smooth low-contrast field that drifts slowly.
        n_neb = 4
        self.neb_freq = rng.uniform(0.04, 0.10, n_neb).astype(np.float32)
        self.neb_dir = rng.uniform(0, 2 * np.pi, n_neb).astype(np.float32)
        self.neb_speed = rng.uniform(0.05, 0.15, n_neb).astype(np.float32)
        # Blue->violet base; the field's value modulates hue locally so
        # the wisps also drift through indigo / purple / soft pink.
        self.neb_hue_base = float(rng.uniform(0.62, 0.76))

        # ---- Metaballs: orbital blobs that merge softly via inverse-square
        # field accumulation. Far more interesting than linear drift -
        # they smear together as their orbits cross. This is the mid-depth
        # layer between nebula and stars.
        self.num_balls = int(num_dust)
        speed_scale = self._scale / 80.0
        # Each ball orbits its own center with its own frequency / phase
        # so the field never settles into a periodic-looking pattern.
        self.ball_phase = np.linspace(0, 2 * np.pi, self.num_balls,
                                      endpoint=False).astype(np.float32)
        self.ball_freq_x = (1.0 + 0.3 * np.arange(self.num_balls)).astype(np.float32)
        self.ball_freq_y = (1.3 + 0.4 * np.arange(self.num_balls)).astype(np.float32)
        self.ball_speed = 0.5
        # Smaller balls than the standalone metaballs animation since they
        # share the strip with stars + nebula + pulses.
        self.ball_radius = self._scale / 5.5
        # Pink to violet to magenta hues, one per ball.
        self.ball_hue = rng.uniform(0.78, 0.98, self.num_balls).astype(np.float32) % 1.0
        # Slow hue drift so the colors evolve over time.
        self.ball_hue_drift = rng.uniform(0.005, 0.020, self.num_balls).astype(np.float32)

        # ---- Stars (two depth tiers).
        self.num_far = int(num_far_stars)
        self.num_near = int(num_near_stars)
        # Far stars: slow drift, dim, small, pale blue tint, slow twinkle.
        self.far_x0 = rng.uniform(0, width, self.num_far).astype(np.float32)
        self.far_y0 = rng.uniform(0, height, self.num_far).astype(np.float32)
        self.far_vx = rng.uniform(-0.15, 0.15, self.num_far).astype(np.float32) * speed_scale
        self.far_vy = rng.uniform(-0.15, 0.15, self.num_far).astype(np.float32) * speed_scale
        self.far_hue = rng.uniform(0.55, 0.70, self.num_far).astype(np.float32)
        self.far_sat = rng.uniform(0.10, 0.30, self.num_far).astype(np.float32)
        self.far_sigma = rng.uniform(0.012, 0.022, self.num_far).astype(np.float32) * self._scale
        self.far_amp = rng.uniform(0.30, 0.55, self.num_far).astype(np.float32)
        self.far_twink_phase = rng.uniform(0, 2 * np.pi, self.num_far).astype(np.float32)
        self.far_twink_rate = rng.uniform(0.4, 1.0, self.num_far).astype(np.float32)

        # Near stars: faster drift, brighter, larger, warmer/whiter, fast twinkle.
        self.near_x0 = rng.uniform(0, width, self.num_near).astype(np.float32)
        self.near_y0 = rng.uniform(0, height, self.num_near).astype(np.float32)
        self.near_vx = rng.uniform(-0.6, 0.6, self.num_near).astype(np.float32) * speed_scale
        self.near_vy = rng.uniform(-0.6, 0.6, self.num_near).astype(np.float32) * speed_scale
        # Mostly near-white with a slight pink/cyan tint - the saturation
        # is low so they read as bright stars more than colored points,
        # but the hue keeps them in-family with the nebula+dust palette.
        # Half tint pink, half tint cyan - more variety within the theme.
        tint_pink = rng.random(self.num_near) < 0.5
        self.near_hue = np.where(
            tint_pink,
            rng.uniform(0.88, 0.98, self.num_near),  # pink-magenta
            rng.uniform(0.50, 0.62, self.num_near),  # cyan-blue
        ).astype(np.float32)
        self.near_sat = rng.uniform(0.10, 0.30, self.num_near).astype(np.float32)
        self.near_sigma = rng.uniform(0.020, 0.035, self.num_near).astype(np.float32) * self._scale
        self.near_amp = rng.uniform(0.65, 1.00, self.num_near).astype(np.float32)
        self.near_twink_phase = rng.uniform(0, 2 * np.pi, self.num_near).astype(np.float32)
        self.near_twink_rate = rng.uniform(1.5, 3.5, self.num_near).astype(np.float32)

        # ---- Pulse (central shockwave that fires periodically).
        self.pulse_period = float(pulse_period)
        # Pulse alternates through pink/blue/violet/cyan/magenta so the
        # periodic shockwave reads in the same palette as the rest.
        self.pulse_hues = np.array(
            [0.92, 0.62, 0.85, 0.55, 0.78, 0.95], dtype=np.float32
        )

    # ---- Layer renderers --------------------------------------------------

    def _layer_nebula(self, t: float) -> np.ndarray:
        # Build a low-contrast value field from 4 moving plane waves.
        x = self.xx / self._scale
        y = self.yy / self._scale
        v = np.zeros_like(x)
        for i in range(len(self.neb_freq)):
            f = float(self.neb_freq[i]) * 2.0 * np.pi
            d = float(self.neb_dir[i])
            phase = t * float(self.neb_speed[i]) * 2.0 * np.pi
            v = v + np.sin(f * (x * np.cos(d) + y * np.sin(d)) + phase)
        v = v / len(self.neb_freq)  # roughly [-1, 1]
        v = 0.5 + 0.5 * v  # [0, 1]
        # Sparse wisps - most of strip stays black so foreground can pop.
        v = np.clip(v - 0.55, 0.0, 1.0)
        v = v * v
        # Hue drifts blue -> violet -> soft pink across the wisps so the
        # nebula doesn't read as a single flat blue. Bright wisps lean
        # toward the pinker side; dim toward deep blue.
        h = (self.neb_hue_base + 0.18 * v + 0.05 * np.sin(t * 0.05)) % 1.0
        s = np.full_like(v, 0.85, dtype=np.float32)
        v_field = (0.45 * v).astype(np.float32)
        return _hsv_to_rgb_array(h.astype(np.float32),
                                 s, v_field).astype(np.float32)

    def _layer_dust(self, t: float) -> np.ndarray:
        # Metaballs: each ball orbits and contributes 1/r^2 to a scalar field
        # that, when normalized, reads as merging soft blobs. We separately
        # accumulate per-ball-color RGB weighted by that ball's contribution
        # so the field's color blends smoothly where balls overlap.
        accum_field = np.zeros((self.height, self.width), dtype=np.float32)
        accum_rgb = np.zeros((self.height, self.width, 3), dtype=np.float32)
        h_ones = np.empty_like(self.xx)
        s_field = np.full_like(self.xx, 0.85, dtype=np.float32)
        r2_const = self.ball_radius * self.ball_radius
        for i in range(self.num_balls):
            cx = self.width * (
                0.5 + 0.4 * np.sin(t * self.ball_speed * float(self.ball_freq_x[i])
                                    + float(self.ball_phase[i]))
            )
            cy = self.height * (
                0.5 + 0.4 * np.cos(t * self.ball_speed * float(self.ball_freq_y[i])
                                    + float(self.ball_phase[i]))
            )
            d2 = (self.xx - cx) ** 2 + (self.yy - cy) ** 2
            contrib = r2_const / (d2 + 0.5)
            accum_field += contrib
            # Color contribution weighted by this ball's local field strength.
            hue = (float(self.ball_hue[i]) + t * float(self.ball_hue_drift[i])) % 1.0
            h_ones.fill(hue)
            v_field = (contrib / float(self.num_balls)).astype(np.float32)
            accum_rgb += _hsv_to_rgb_array(h_ones, s_field,
                                           np.clip(v_field, 0.0, 1.0)).astype(np.float32)
        # Smooth gating: tanh of the total field gives soft blob shapes.
        # Subtract a threshold first so the field is BLACK in the spaces
        # between balls instead of contributing a low-grade glow.
        gated = np.maximum(0.0, np.tanh(accum_field / float(self.num_balls)) - 0.20)
        # Renormalize and cap so metaballs don't overpower stars/pulse.
        return accum_rgb * (gated[..., None] * 0.40)

    def _layer_stars(self, t: float, near: bool) -> np.ndarray:
        accum = np.zeros((self.height, self.width, 3), dtype=np.float32)
        h_ones = np.empty_like(self.xx)
        s_ones = np.empty_like(self.xx)
        if near:
            n = self.num_near
            x0, y0 = self.near_x0, self.near_y0
            vx, vy = self.near_vx, self.near_vy
            hues, sats = self.near_hue, self.near_sat
            sigs, amps = self.near_sigma, self.near_amp
            tp, tr = self.near_twink_phase, self.near_twink_rate
        else:
            n = self.num_far
            x0, y0 = self.far_x0, self.far_y0
            vx, vy = self.far_vx, self.far_vy
            hues, sats = self.far_hue, self.far_sat
            sigs, amps = self.far_sigma, self.far_amp
            tp, tr = self.far_twink_phase, self.far_twink_rate

        for i in range(n):
            cx = (float(x0[i]) + float(vx[i]) * t) % self.width
            cy = (float(y0[i]) + float(vy[i]) * t) % self.height
            sig = max(0.5, float(sigs[i]))
            # Twinkle: brightness modulated by a sine; near stars twinkle harder.
            base = float(amps[i])
            twink = 0.5 + 0.5 * np.sin(t * float(tr[i]) + float(tp[i]))
            depth_amp = base * (0.35 + 0.65 * twink) if near else base * (0.55 + 0.45 * twink)
            d2 = (self.xx - cx) ** 2 + (self.yy - cy) ** 2
            amp = depth_amp * np.exp(-d2 / (2.0 * sig * sig))
            h_ones.fill(float(hues[i]))
            s_ones.fill(float(sats[i]))
            rgb = _hsv_to_rgb_array(h_ones, s_ones, amp).astype(np.float32)
            accum += rgb
        return accum

    def _layer_pulse(self, t: float) -> np.ndarray:
        # One pulse per pulse_period. Within each, a shockwave expands from
        # the center for ~1.5 seconds, brightening then fading.
        slot = self.pulse_period
        idx = int(t // slot)
        t_in = (t % slot)
        # Pulse only in the first 1.8s of each period (rest is quiet).
        burst_dur = 1.8
        if t_in > burst_dur:
            return np.zeros((self.height, self.width, 3), dtype=np.float32)
        u = t_in / burst_dur  # 0..1
        # Shockwave radius grows linearly; brightness fades as 1-u.
        cx = (self.width - 1) / 2.0
        cy = (self.height - 1) / 2.0
        r = np.sqrt((self.xx - cx) ** 2 + (self.yy - cy) ** 2)
        ring_r = u * (self._scale * 0.55)
        ring_w = max(0.8, self._scale * 0.06)
        amp = (1.0 - u) ** 2 * 1.1 * np.exp(-((r - ring_r) ** 2) / (2.0 * ring_w * ring_w))
        # Hue cycles per pulse; saturated near-white on the leading edge.
        hue = float(self.pulse_hues[idx % len(self.pulse_hues)])
        h_field = np.full_like(amp, hue, dtype=np.float32)
        s_field = np.full_like(amp, 0.45, dtype=np.float32)  # pale, near-white
        return _hsv_to_rgb_array(h_field, s_field, amp.astype(np.float32)).astype(np.float32)

    # ---- Composite --------------------------------------------------------

    def generate_frame(self, time: float) -> np.ndarray:
        nebula = self._layer_nebula(time)
        dust = self._layer_dust(time)
        far = self._layer_stars(time, near=False)
        near = self._layer_stars(time, near=True)
        pulse = self._layer_pulse(time)
        # Additive composite (clip after).
        frame = nebula + dust + far + near + pulse
        return np.clip(frame, 0.0, 255.0).astype(np.uint8)


class FireworksShow(ProceduralAnimation):
    """A complete fireworks show on a black sky.

    Tracers ascend from a horizon at the bottom, decelerate to an apex,
    and burst into one of several effect types. The show progresses
    through four phases over a configurable duration:

        slow start  - sparse single bursts, simple peonies
        variety     - all effect types, occasional doubles
        build       - faster cadence, multi-break shells common
        FINALE      - rapid fire, stacked, the works

    Then loops. Particle physics is fully vectorized; one numpy update
    per frame drives every particle's position, velocity and life.

    Effect types implemented:
        peony          - clean radial sparks, single color
        chrysanthemum  - radial sparks with longer life and trails
        willow         - heavy gravity, drooping streamers
        ring           - particles fired in a ring
        crossette      - sparks that split into mini-bursts mid-flight
        strobe         - rapid bright flashes from a center point
    """

    MAX_PARTICLES = 600

    # Particle 'kind' codes.
    K_TRACER = 0
    K_SPARK = 1        # standard burst spark
    K_HEAVY = 2        # willow - higher gravity, slower
    K_CROSS_SEED = 3   # crossette parent - splits when life expires
    K_STROBE = 4       # strobe spark - flashes via life modulation

    def __init__(self, width: int, height: int, fps: float = 30,
                 show_duration: float = 60.0,
                 horizon_y: float = 0.92,
                 seed: int = 7):
        super().__init__(width, height, fps)
        self._scale = float(min(width, height))
        x = np.arange(width, dtype=np.float32)
        y = np.arange(height, dtype=np.float32)
        self.xx, self.yy = np.meshgrid(x, y)

        self.show_duration = float(show_duration)
        self.horizon_y = float(horizon_y) * (self.height - 1)
        self._rng = np.random.default_rng(seed)

        # Gravity in pixels/sec^2 at this resolution. Tracers get a fraction
        # of this so they slow naturally to an apex; willows get more.
        self.g = 18.0 * self._scale / 80.0

        # Pre-allocated particle arrays (Structure-of-Arrays for speed).
        N = self.MAX_PARTICLES
        self.px = np.zeros(N, dtype=np.float32)
        self.py = np.zeros(N, dtype=np.float32)
        self.pvx = np.zeros(N, dtype=np.float32)
        self.pvy = np.zeros(N, dtype=np.float32)
        self.plife = np.zeros(N, dtype=np.float32)        # remaining (s)
        self.pmaxlife = np.ones(N, dtype=np.float32)
        self.phue = np.zeros(N, dtype=np.float32)
        self.psat = np.ones(N, dtype=np.float32)
        self.psize = np.zeros(N, dtype=np.float32)        # render sigma (px)
        self.pkind = np.zeros(N, dtype=np.int32)
        self.pgravity = np.zeros(N, dtype=np.float32)     # per-particle g mul

        # Per-tracer 'what to spawn when I expire' info.
        self.p_burst_kind = np.zeros(N, dtype='U16')
        self.p_burst_hue = np.zeros(N, dtype=np.float32)
        self.p_burst_size = np.zeros(N, dtype=np.float32)

        self._last_t = 0.0
        self._next_launch_t = 0.6
        self._show_t0 = 0.0

        # Hue palette for fireworks: bright saturated set.
        self._palette = np.array(
            [0.00, 0.06, 0.13, 0.30, 0.45, 0.55, 0.62, 0.78, 0.85, 0.92],
            dtype=np.float32,
        )

    # ---- Slot management -------------------------------------------------

    def _free_slots(self, n: int) -> np.ndarray:
        free = np.where(self.plife <= 0.0)[0]
        return free[:n]

    def _spawn_one(self, x, y, vx, vy, life, hue, sat, size, kind,
                   gmul=1.0, burst_kind='', burst_hue=0.0, burst_size=0.0):
        slot = self._free_slots(1)
        if len(slot) == 0:
            return
        i = int(slot[0])
        self.px[i] = x;    self.py[i] = y
        self.pvx[i] = vx;  self.pvy[i] = vy
        self.plife[i] = life
        self.pmaxlife[i] = life
        self.phue[i] = hue
        self.psat[i] = sat
        self.psize[i] = size
        self.pkind[i] = kind
        self.pgravity[i] = gmul
        self.p_burst_kind[i] = burst_kind
        self.p_burst_hue[i] = burst_hue
        self.p_burst_size[i] = burst_size

    # ---- Spawning helpers -----------------------------------------------

    def _launch_tracer(self, target_x: float, apex_y: float,
                       burst_kind: str, burst_hue: float, burst_size: float):
        """Send a tracer straight up from the horizon to apex_y."""
        # Start at target_x exactly so the tracer goes purely vertical
        # (no left-right drift visible on the strip).
        x0 = target_x
        # Vertical ballistics: vy0 = -sqrt(2 * g * (horizon - apex)) so vy
        # reaches zero exactly at apex_y. Negative = upward.
        dy = max(0.5, self.horizon_y - apex_y)
        vy0 = -np.sqrt(2.0 * self.g * dy)
        t_apex = -vy0 / self.g
        # Tracer is small - target ~half an LED at the output resolution.
        tracer_size = max(0.4, self._scale * 0.025)
        self._spawn_one(
            x=x0, y=self.horizon_y, vx=0.0, vy=vy0, life=t_apex,
            hue=0.13, sat=0.30, size=tracer_size,
            kind=self.K_TRACER, gmul=1.0,
            burst_kind=burst_kind, burst_hue=burst_hue, burst_size=burst_size,
        )

    def _spawn_burst(self, x: float, y: float, kind: str, hue: float,
                     size_mul: float = 1.0):
        """Spawn the spark cloud for a given burst type at (x, y)."""
        s = self._scale / 80.0
        # Particle render sigma. Tuned so a single spark covers about half
        # an LED at the output resolution after supersample averaging.
        size_px = max(0.5, self._scale * 0.045)

        # Speed scale: in pixels/sec at this resolution. Tuned so big bursts
        # cross most of the strip during their lifetime.
        if kind == 'peony':
            n = 24
            speed = self._rng.uniform(18.0, 26.0) * s * size_mul
            for i in range(n):
                ang = (2 * np.pi * i / n) + self._rng.uniform(-0.07, 0.07)
                spd = speed * self._rng.uniform(0.85, 1.15)
                self._spawn_one(
                    x=x, y=y, vx=spd * np.cos(ang), vy=spd * np.sin(ang),
                    life=self._rng.uniform(1.2, 1.8),
                    hue=(hue + self._rng.uniform(-0.02, 0.02)) % 1.0,
                    sat=1.0, size=size_px, kind=self.K_SPARK,
                )
        elif kind == 'chrysanthemum':
            n = 30
            speed = self._rng.uniform(20.0, 32.0) * s * size_mul
            for i in range(n):
                ang = (2 * np.pi * i / n) + self._rng.uniform(-0.05, 0.05)
                spd = speed * self._rng.uniform(0.7, 1.3)
                self._spawn_one(
                    x=x, y=y, vx=spd * np.cos(ang), vy=spd * np.sin(ang),
                    life=self._rng.uniform(1.8, 2.6),
                    hue=(hue + self._rng.uniform(-0.04, 0.04)) % 1.0,
                    sat=1.0, size=size_px, kind=self.K_SPARK,
                )
        elif kind == 'willow':
            n = 22
            speed = self._rng.uniform(15.0, 22.0) * s * size_mul
            for i in range(n):
                ang = (2 * np.pi * i / n) + self._rng.uniform(-0.06, 0.06)
                # Bias velocity slightly upward so droops feel right.
                spd = speed * self._rng.uniform(0.7, 1.2)
                self._spawn_one(
                    x=x, y=y,
                    vx=spd * np.cos(ang) * 0.7,
                    vy=spd * np.sin(ang) - 4.0 * s,
                    life=self._rng.uniform(2.4, 3.5),
                    hue=(hue + self._rng.uniform(-0.02, 0.02)) % 1.0,
                    sat=0.8, size=size_px,
                    kind=self.K_HEAVY, gmul=1.6,
                )
        elif kind == 'ring':
            n = 28
            speed = self._rng.uniform(22.0, 30.0) * s * size_mul
            jit = 0.05
            for i in range(n):
                ang = 2 * np.pi * i / n
                spd = speed * (1.0 + self._rng.uniform(-jit, jit))
                self._spawn_one(
                    x=x, y=y, vx=spd * np.cos(ang), vy=spd * np.sin(ang),
                    life=self._rng.uniform(1.2, 1.6),
                    hue=hue, sat=1.0, size=size_px, kind=self.K_SPARK,
                )
        elif kind == 'crossette':
            # Big slow seeds that split into mini-bursts after ~0.6s.
            n = 8
            speed = self._rng.uniform(16.0, 22.0) * s * size_mul
            seed_life = self._rng.uniform(0.5, 0.8)
            for i in range(n):
                ang = 2 * np.pi * i / n + self._rng.uniform(-0.04, 0.04)
                spd = speed * self._rng.uniform(0.9, 1.1)
                self._spawn_one(
                    x=x, y=y, vx=spd * np.cos(ang), vy=spd * np.sin(ang),
                    life=seed_life,
                    hue=hue, sat=1.0, size=size_px * 1.2,
                    kind=self.K_CROSS_SEED, gmul=0.6,
                    burst_kind='peony', burst_hue=hue, burst_size=0.5,
                )
        elif kind == 'strobe':
            n = 14
            speed = self._rng.uniform(10.0, 16.0) * s * size_mul
            for i in range(n):
                ang = 2 * np.pi * i / n + self._rng.uniform(-0.1, 0.1)
                spd = speed * self._rng.uniform(0.7, 1.3)
                self._spawn_one(
                    x=x, y=y, vx=spd * np.cos(ang), vy=spd * np.sin(ang),
                    life=self._rng.uniform(1.4, 2.0),
                    hue=hue, sat=0.05, size=size_px,
                    kind=self.K_STROBE, gmul=0.9,
                )

    def _random_hue(self) -> float:
        return float(self._palette[self._rng.integers(0, len(self._palette))])

    # ---- Show timeline ---------------------------------------------------

    def _spawn_for_time(self, t_show: float):
        """Time-based launching. t_show is seconds since show start."""
        if t_show < self._next_launch_t:
            return
        # Phase boundaries.
        D = self.show_duration
        finale_start = D * 0.85
        build_start = D * 0.6
        variety_start = D * 0.25

        if t_show >= finale_start:
            # FINALE: rapid fire, big multi-break combos.
            interval = self._rng.uniform(0.18, 0.40)
            count = self._rng.integers(1, 4)
            kinds = ['peony', 'chrysanthemum', 'willow', 'ring',
                     'crossette', 'strobe']
        elif t_show >= build_start:
            interval = self._rng.uniform(0.7, 1.2)
            count = self._rng.integers(1, 3)
            kinds = ['peony', 'chrysanthemum', 'willow', 'ring',
                     'crossette', 'strobe']
        elif t_show >= variety_start:
            interval = self._rng.uniform(1.4, 2.2)
            count = 1 if self._rng.random() < 0.7 else 2
            kinds = ['peony', 'chrysanthemum', 'willow', 'ring', 'strobe']
        else:
            interval = self._rng.uniform(2.4, 3.5)
            count = 1
            kinds = ['peony', 'chrysanthemum']

        self._next_launch_t = t_show + interval
        for _ in range(int(count)):
            kind = kinds[self._rng.integers(0, len(kinds))]
            # Mostly mid-height apexes; occasional very-high big shells.
            apex_y = self._rng.uniform(0.05, 0.40) * (self.height - 1)
            target_x = self._rng.uniform(0.20, 0.80) * (self.width - 1)
            hue = self._random_hue()
            # Most shells normal-size; some big ones that cross the sky.
            # Big-shell probability rises through the show.
            big_prob = (0.10 if t_show < variety_start else
                        0.20 if t_show < build_start else
                        0.35 if t_show < finale_start else
                        0.55)
            if self._rng.random() < big_prob:
                size_mul = self._rng.uniform(1.4, 1.9)
            else:
                size_mul = self._rng.uniform(0.8, 1.15)
            self._launch_tracer(target_x, apex_y, kind, hue, size_mul)

    # ---- Physics ---------------------------------------------------------

    def _update(self, dt: float):
        if dt <= 0:
            return
        alive = self.plife > 0.0
        # Move.
        self.px[alive] += self.pvx[alive] * dt
        self.py[alive] += self.pvy[alive] * dt
        # Gravity (per-particle multiplier so willows sag).
        self.pvy[alive] += self.g * self.pgravity[alive] * dt
        # Mild air drag for sparks so they don't streak forever.
        drag = 0.92 ** dt if dt < 1.0 else 0.5
        self.pvx[alive] *= drag
        # Life.
        prev_life = self.plife.copy()
        self.plife[alive] -= dt

        # Tracers that just expired -> trigger their burst at current pos.
        just_died_tracers = (
            (prev_life > 0.0) & (self.plife <= 0.0) & (self.pkind == self.K_TRACER)
        )
        if np.any(just_died_tracers):
            for idx in np.where(just_died_tracers)[0]:
                self._spawn_burst(
                    float(self.px[idx]), float(self.py[idx]),
                    str(self.p_burst_kind[idx]),
                    float(self.p_burst_hue[idx]),
                    float(self.p_burst_size[idx]),
                )

        # Crossette seeds that just expired -> mini-burst at current pos.
        just_died_seeds = (
            (prev_life > 0.0) & (self.plife <= 0.0) & (self.pkind == self.K_CROSS_SEED)
        )
        if np.any(just_died_seeds):
            for idx in np.where(just_died_seeds)[0]:
                # Smaller secondary burst.
                self._spawn_burst(
                    float(self.px[idx]), float(self.py[idx]),
                    str(self.p_burst_kind[idx]) or 'peony',
                    float(self.p_burst_hue[idx]),
                    0.4,
                )

    # ---- Rendering -------------------------------------------------------

    def _render(self) -> np.ndarray:
        frame = np.zeros((self.height, self.width, 3), dtype=np.float32)

        # Horizon: dim warm glow on the bottom-most row(s). Acts as a
        # "ground line" the tracers launch from. Always visible so the
        # show has a sense of place even between bursts.
        h_row = int(round(self.horizon_y))
        if 0 <= h_row < self.height:
            # Hot-orange glow that's brightest on the horizon row and
            # falls off above it within ~1.5 LEDs.
            band = max(1.0, self._scale * 0.04)
            dy = self.yy - self.horizon_y
            base = np.clip(np.exp(-(dy * dy) / (2.0 * band * band)), 0.0, 1.0)
            # Only on/below the horizon line (don't bleed too far up).
            base = np.where(self.yy >= self.horizon_y - band * 1.2, base, 0.0)
            # Warm dim color: hue ~0.05 (orange), low sat for dusky feel.
            h_field = np.full_like(base, 0.05, dtype=np.float32)
            s_field = np.full_like(base, 0.55, dtype=np.float32)
            v_field = (base * 0.18).astype(np.float32)  # dim
            frame += _hsv_to_rgb_array(
                h_field.astype(np.float32), s_field, v_field
            ).astype(np.float32)

        alive = np.where(self.plife > 0.0)[0]
        if alive.size == 0:
            return np.clip(frame, 0.0, 255.0).astype(np.uint8)

        for i in alive:
            x = float(self.px[i]); y = float(self.py[i])
            if x < -3 or x > self.width + 3 or y < -3 or y > self.height + 3:
                continue
            sigma = max(0.6, float(self.psize[i]))
            kind = int(self.pkind[i])
            life_frac = float(self.plife[i] / max(0.001, self.pmaxlife[i]))
            # Brightness profile per kind:
            if kind == self.K_TRACER:
                # Bright nearly constant; slight fade near apex.
                amp = 0.85 + 0.15 * (1.0 - life_frac)
                hue = float(self.phue[i])
                sat = float(self.psat[i])
            elif kind == self.K_SPARK:
                # Quick bright flash, fades to dim ember.
                amp = life_frac * (0.7 + 0.3 * (1.0 - life_frac))
                hue = float(self.phue[i])
                sat = float(self.psat[i])
            elif kind == self.K_HEAVY:
                # Willow: stays warm, fades slowly to amber.
                amp = life_frac * 0.85
                hue = (float(self.phue[i]) + 0.05 * (1.0 - life_frac)) % 1.0
                sat = float(self.psat[i])
            elif kind == self.K_CROSS_SEED:
                amp = 0.9
                hue = float(self.phue[i])
                sat = 1.0
            elif kind == self.K_STROBE:
                # Rapid on/off flicker via fast sine on remaining life.
                flicker = 0.5 + 0.5 * np.sin(life_frac * 60.0)
                amp = life_frac * flicker
                hue = float(self.phue[i])
                sat = 0.05
            else:
                amp = life_frac
                hue = float(self.phue[i])
                sat = float(self.psat[i])

            if amp < 0.02:
                continue

            # Splat into a small bounding box only.
            r_radius = int(np.ceil(sigma * 3.0))
            x0 = max(0, int(x) - r_radius)
            x1 = min(self.width, int(x) + r_radius + 1)
            y0 = max(0, int(y) - r_radius)
            y1 = min(self.height, int(y) + r_radius + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            sub_xx = self.xx[y0:y1, x0:x1]
            sub_yy = self.yy[y0:y1, x0:x1]
            d2 = (sub_xx - x) ** 2 + (sub_yy - y) ** 2
            g = amp * np.exp(-d2 / (2.0 * sigma * sigma))
            h = np.full_like(g, hue, dtype=np.float32)
            s = np.full_like(g, sat, dtype=np.float32)
            rgb = _hsv_to_rgb_array(h, s, g.astype(np.float32)).astype(np.float32)
            frame[y0:y1, x0:x1] += rgb

        return np.clip(frame, 0.0, 255.0).astype(np.uint8)

    # ---- Frame entry point ----------------------------------------------

    def generate_frame(self, time: float) -> np.ndarray:
        # First call sets the show start; subsequent calls measure dt.
        if self._last_t == 0.0 and time > 0.0:
            self._last_t = time
            self._show_t0 = time
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)

        dt = float(time) - self._last_t
        if dt < 0:
            # Time went backwards - reset.
            self._last_t = float(time)
            self._show_t0 = float(time)
            self._next_launch_t = float(time) - self._show_t0 + 0.6
            return np.zeros((self.height, self.width, 3), dtype=np.uint8)
        # Cap dt to avoid huge jumps after pauses.
        dt = min(dt, 0.1)
        self._last_t = float(time)

        # Loop the show.
        t_show = (float(time) - self._show_t0) % self.show_duration
        # When wrapping, give a half-second of quiet then restart launches.
        if t_show < 0.5 and self._next_launch_t > t_show + 1.5:
            self._next_launch_t = 0.6

        self._update(dt)
        self._spawn_for_time(t_show)
        return self._render()


class FlagMashup(ProceduralAnimation):
    """Cycles between a full Union Jack and a full USA flag, crossfading
    softly between the two. Each flag is rendered with a gentle fabric
    wave + twinkling stars (USA only).

    Cycle (configurable):
        hold Union Jack    (5s default)
        crossfade to USA   (1.5s)
        hold USA flag      (5s)
        crossfade to UK    (1.5s)
        repeat
    """

    BLUE = np.array([12, 35, 130], dtype=np.float32)
    RED = np.array([200, 30, 35], dtype=np.float32)
    WHITE = np.array([235, 235, 235], dtype=np.float32)

    def __init__(self, width: int, height: int, fps: float = 30,
                 hold_seconds: float = 5.0,
                 fade_seconds: float = 1.5,
                 num_stars: int = 12, seed: int = 76):
        super().__init__(width, height, fps)
        self._scale = float(min(width, height))
        x = np.arange(width, dtype=np.float32)
        y = np.arange(height, dtype=np.float32)
        self.xx, self.yy = np.meshgrid(x, y)

        self.hold = float(hold_seconds)
        self.fade = float(fade_seconds)
        # Total cycle: hold UK -> fade -> hold US -> fade -> repeat.
        self.cycle = 2.0 * (self.hold + self.fade)

        # Union Jack diagonal line widths (scaled to resolution).
        self.diag_white_w = max(0.6, self._scale * 0.11)
        self.diag_red_w = max(0.4, self._scale * 0.045)
        # Union Jack horizontal/vertical cross widths.
        self.cross_white_w = max(0.6, self._scale * 0.11)
        self.cross_red_w = max(0.4, self._scale * 0.045)

        # USA canton (top-left) covers ~40% width, ~45% height.
        self.canton_w = width * 0.40
        self.canton_h = height * 0.45

        # USA stripes: 7 visible horizontal bands so the alternation is
        # clearly red/white/red/white/red/white/red on a 10-tall strip.
        self.n_stripes = 7

        rng = np.random.default_rng(seed)
        self.num_stars = int(num_stars)
        # Stars placed inside the canton at fixed positions, twinkling
        # at independent rates.
        self.star_x = rng.uniform(0.5, self.canton_w - 0.5,
                                  self.num_stars).astype(np.float32)
        self.star_y = rng.uniform(0.4, self.canton_h - 0.5,
                                  self.num_stars).astype(np.float32)
        self.star_phase = rng.uniform(0, 2 * np.pi,
                                      self.num_stars).astype(np.float32)
        self.star_rate = rng.uniform(1.4, 3.2,
                                     self.num_stars).astype(np.float32)
        self.star_sigma = (rng.uniform(0.025, 0.040, self.num_stars)
                           * self._scale).astype(np.float32)
        self.star_amp = (rng.uniform(0.7, 1.0, self.num_stars)
                         * 230.0).astype(np.float32)

    @staticmethod
    def _smoothstep(u: float) -> float:
        u = max(0.0, min(1.0, u))
        return u * u * (3.0 - 2.0 * u)

    def _wave_dx(self, time: float) -> np.ndarray:
        wave_amp = self._scale * 0.022
        return wave_amp * np.sin(self.yy * 0.30 + time * 1.2)

    def _render_union_jack(self, time: float) -> np.ndarray:
        H, W = self.height, self.width
        sx = self.xx + self._wave_dx(time)
        sy = self.yy
        cy = (H - 1) * 0.5
        cx = (W - 1) * 0.5
        # Diagonals span corner to corner of the full panel.
        m = (H - 1) / max(1.0, W - 1)
        norm = np.sqrt(1.0 + m * m)
        d1 = np.abs((sy - cy) - m * (sx - cx)) / norm
        d2 = np.abs((sy - cy) + m * (sx - cx)) / norm
        d_diag = np.minimum(d1, d2)
        # Horizontal/vertical cross.
        d_cross = np.minimum(np.abs(sy - cy), np.abs(sx - cx))

        white_diag = d_diag < self.diag_white_w
        red_diag = d_diag < self.diag_red_w
        white_cross = d_cross < self.cross_white_w
        red_cross = d_cross < self.cross_red_w

        frame = np.broadcast_to(self.BLUE, (H, W, 3)).copy()
        # White layers first, then red on top so reds paint over their
        # corresponding white stripes.
        frame[white_diag] = self.WHITE
        frame[white_cross] = self.WHITE
        frame[red_diag] = self.RED
        frame[red_cross] = self.RED
        return frame

    def _render_usa_flag(self, time: float) -> np.ndarray:
        H, W = self.height, self.width
        sx = self.xx + self._wave_dx(time)
        sy = self.yy
        in_canton = (sy < self.canton_h) & (sx < self.canton_w)
        # 7 horizontal stripes so we get red/white/red/.../red on 10 rows.
        idx = np.floor((sy / max(1.0, H)) * self.n_stripes).astype(np.int32)
        idx = np.clip(idx, 0, self.n_stripes - 1)
        is_red = (idx % 2) == 0

        frame = np.zeros((H, W, 3), dtype=np.float32)
        red_mask = is_red & ~in_canton
        white_mask = (~is_red) & (~in_canton)
        frame[red_mask] = self.RED
        frame[white_mask] = self.WHITE
        frame[in_canton] = self.BLUE

        # Twinkling stars, only inside the canton.
        for i in range(self.num_stars):
            phase = float(self.star_phase[i])
            rate = float(self.star_rate[i])
            twink = 0.5 + 0.5 * np.sin(time * rate + phase)
            if twink < 0.30:
                continue
            sx_pos = float(self.star_x[i])
            sy_pos = float(self.star_y[i])
            sigma = max(0.5, float(self.star_sigma[i]))
            amp = float(self.star_amp[i]) * twink
            r2 = (self.xx - sx_pos) ** 2 + (self.yy - sy_pos) ** 2
            g = amp * np.exp(-r2 / (2.0 * sigma * sigma))
            g = np.where(in_canton, g, 0.0)
            frame[..., 0] += g
            frame[..., 1] += g
            frame[..., 2] += g * 0.85
        return frame

    def generate_frame(self, time: float) -> np.ndarray:
        t = float(time) % self.cycle
        # Phase boundaries.
        b1 = self.hold                 # end of UK hold
        b2 = self.hold + self.fade     # end of UK->US fade
        b3 = b2 + self.hold            # end of US hold
        # b3 .. cycle is US->UK fade.

        if t < b1:
            uk_a, us_a = 1.0, 0.0
        elif t < b2:
            u = self._smoothstep((t - b1) / self.fade)
            uk_a, us_a = 1.0 - u, u
        elif t < b3:
            uk_a, us_a = 0.0, 1.0
        else:
            u = self._smoothstep((t - b3) / self.fade)
            uk_a, us_a = u, 1.0 - u

        # Skip rendering whichever flag is at zero alpha.
        if us_a <= 0.0:
            frame = self._render_union_jack(time)
        elif uk_a <= 0.0:
            frame = self._render_usa_flag(time)
        else:
            uk = self._render_union_jack(time).astype(np.float32)
            us = self._render_usa_flag(time).astype(np.float32)
            frame = uk_a * uk + us_a * us
        return np.clip(frame, 0.0, 255.0).astype(np.uint8)


class AmbientField(ProceduralAnimation):
    """Slow flowing color-field engine for a 10x10 strip behind a diffuser.

    Purpose-built for diffused ambient light, NOT pixel-precise imagery:

      - Everything is low spatial frequency (features span several LEDs),
        because the diffuser blurs anything finer into mush anyway.
      - Motion is slow and organic (advection + domain warp).
      - Color carries the piece; the palette is the design.
      - Outputs float32 (sub-8-bit color) so the player's dithering can
        pull smooth gradients out of the panel's 8-bit channels.

    Subclass and set MOOD to pick a palette + motion preset.
    """

    MOOD = 'cosmic'

    # Cyclic palettes: (position 0..1, (r, g, b) 0..255). Designed to look
    # good at any field value and to wrap (last stop blends back to first).
    PALETTES = {
        'cosmic': [
            (0.00, (5, 2, 28)),
            (0.22, (40, 16, 110)),
            (0.42, (130, 30, 155)),
            (0.60, (225, 60, 140)),
            (0.80, (70, 60, 190)),
        ],
        'lava': [
            (0.00, (8, 0, 0)),
            (0.20, (95, 8, 0)),
            (0.42, (205, 30, 0)),
            (0.62, (255, 115, 12)),
            (0.82, (255, 205, 70)),
        ],
        'aurora': [
            (0.00, (0, 18, 42)),
            (0.25, (0, 85, 95)),
            (0.46, (20, 165, 115)),
            (0.66, (125, 225, 155)),
            (0.84, (205, 120, 175)),
        ],
        'color_field': [
            (0.00, (170, 55, 70)),
            (0.28, (200, 130, 60)),
            (0.52, (70, 85, 150)),
            (0.76, (150, 80, 145)),
        ],
    }

    # Per-mood motion: spatial frequencies (low = big features), domain-warp
    # amount, time-speed, flow bias (vx, vy in field-units/sec), and a
    # brightness floor so the field never goes fully dark.
    MOODS = {
        'cosmic':      dict(fx=1.6, fy=1.8, fd=1.2, warp=0.22, speed=1.0,
                            flow=(0.02, -0.015), vfloor=0.45),
        'lava':        dict(fx=1.4, fy=1.7, fd=1.3, warp=0.30, speed=0.8,
                            flow=(0.0, -0.06), vfloor=0.35),
        'aurora':      dict(fx=1.3, fy=1.0, fd=1.1, warp=0.18, speed=0.9,
                            flow=(0.05, 0.0), vfloor=0.40),
        'color_field': dict(fx=0.8, fy=0.9, fd=0.6, warp=0.10, speed=0.45,
                            flow=(0.01, 0.008), vfloor=0.55),
    }

    def __init__(self, width, height, fps=30, mood=None, speed=1.0, lut_n=512):
        super().__init__(width, height, fps)
        self.mood = mood or self.MOOD
        m = self.MOODS[self.mood]
        self.fx, self.fy, self.fd = m['fx'], m['fy'], m['fd']
        self.warp = m['warp']
        self.base_speed = m['speed'] * speed
        self.flow = m['flow']
        self.vfloor = m['vfloor']
        xn = np.linspace(0.0, 1.0, width, dtype=np.float32)
        yn = np.linspace(0.0, 1.0, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.lut_n = lut_n
        self.lut = self._build_lut(self.PALETTES[self.mood], lut_n)

    @staticmethod
    def _build_lut(stops, n):
        stops = sorted(stops)
        pos = np.array([p for p, _ in stops] + [1.0 + stops[0][0]],
                       dtype=np.float64)
        lut = np.zeros((n, 3), dtype=np.float32)
        q = np.linspace(0.0, 1.0, n, endpoint=False)
        for ch in range(3):
            vals = np.array([c[ch] for _, c in stops] + [stops[0][1][ch]],
                            dtype=np.float64)
            lut[:, ch] = np.interp(q, pos, vals).astype(np.float32)
        return lut

    def _fields(self, t):
        s = self.base_speed
        fx_, fy_ = self.flow
        # Advect (slow flow) + domain-warp for organic, non-repeating motion.
        x = self.xn + fx_ * t
        y = self.yn + fy_ * t
        wx = self.warp * np.sin(2 * np.pi * (self.yn * 0.9) + t * 0.13 * s)
        wy = self.warp * np.cos(2 * np.pi * (self.xn * 0.9) + t * 0.11 * s)
        xx = x + wx
        yy = y + wy
        # Color field: 3 low-frequency waves -> 0..1.
        a = np.sin(2 * np.pi * (xx * self.fx) + t * 0.05 * s)
        b = np.sin(2 * np.pi * (yy * self.fy) - t * 0.043 * s)
        c = np.sin(2 * np.pi * ((xx + yy) * self.fd) + t * 0.031 * s)
        color_f = (a + b + c) / 3.0
        # The sum-of-sines clusters near the middle; expand its contrast with
        # tanh so the field actually travels to the vivid ends of the palette
        # instead of hovering in the washed-out midtones.
        color_f = 0.5 + 0.5 * np.tanh(color_f * 2.4)
        # Brightness field: different slow combo -> vfloor..1 (gives depth).
        d = np.sin(2 * np.pi * (xx * 0.7) - t * 0.027 * s)
        e = np.sin(2 * np.pi * (yy * 0.6) + t * 0.019 * s)
        bright_f = 0.5 + 0.5 * (0.5 * (d + e))
        bright_f = self.vfloor + (1.0 - self.vfloor) * bright_f
        return color_f.astype(np.float32), bright_f.astype(np.float32)

    def generate_frame(self, time):
        t = float(time)
        color_f, bright_f = self._fields(t)
        breathe = 0.88 + 0.12 * np.sin(t * 0.08 * self.base_speed)
        # Map color field through the palette LUT with linear interpolation
        # (continuous color = no stepping before dithering even gets a turn).
        fp = color_f * self.lut_n
        i0 = np.floor(fp).astype(np.int32) % self.lut_n
        frac = (fp - np.floor(fp)).astype(np.float32)[..., None]
        i1 = (i0 + 1) % self.lut_n
        col = self.lut[i0] * (1.0 - frac) + self.lut[i1] * frac
        # Saturation boost: push each pixel away from its own gray level to
        # counteract the dulling that linear RGB interpolation introduces
        # between hue stops. Keeps the colors vivid, not pastel/washed.
        gray = col.mean(axis=2, keepdims=True)
        col = gray + (col - gray) * 1.35
        col = np.clip(col, 0.0, 255.0)
        out = col * (bright_f[..., None] * breathe)
        # Return float32 (0..255) so the player can dither for smoothness.
        return out.astype(np.float32)


class AmbientCosmic(AmbientField):
    """Ambient cosmic nebula - slow indigo/violet/magenta/cyan flow."""
    MOOD = 'cosmic'


class AmbientLava(AmbientField):
    """Ambient liquid lava - warm molten amber/crimson/gold morphing."""
    MOOD = 'lava'


class AmbientAurora(AmbientField):
    """Ambient aurora/tides - flowing teal/green/blue with pink edges."""
    MOOD = 'aurora'


class AmbientColorField(AmbientField):
    """Ambient color-field - Rothko-style slow breathing color washes."""
    MOOD = 'color_field'


# --- Shared helpers for the structured ambient set -------------------------

def _build_palette_lut(stops, n=512):
    """Cyclic palette -> (n, 3) float32 LUT. stops: [(pos0..1, (r,g,b)), ...]."""
    stops = sorted(stops)
    pos = np.array([p for p, _ in stops] + [1.0 + stops[0][0]], dtype=np.float64)
    lut = np.zeros((n, 3), dtype=np.float32)
    q = np.linspace(0.0, 1.0, n, endpoint=False)
    for ch in range(3):
        vals = np.array([c[ch] for _, c in stops] + [stops[0][1][ch]],
                        dtype=np.float64)
        lut[:, ch] = np.interp(q, pos, vals).astype(np.float32)
    return lut


def _map_lut(lut, field):
    """Map a (H, W) field in 0..1 through a cyclic LUT with linear interp."""
    n = lut.shape[0]
    fp = field * n
    i0 = np.floor(fp).astype(np.int32) % n
    frac = (fp - np.floor(fp)).astype(np.float32)[..., None]
    i1 = (i0 + 1) % n
    return lut[i0] * (1.0 - frac) + lut[i1] * frac


def _sat_boost(col, amt=1.3):
    """Push each pixel away from its own gray for vividness."""
    gray = col.mean(axis=2, keepdims=True)
    return np.clip(gray + (col - gray) * amt, 0.0, 255.0)


# Named cyclic palettes - any noise field can be run through any of these
# via the player's --palette flag.
NAMED_PALETTES = {
    'cosmic':     [(0.00, (5, 2, 28)), (0.22, (40, 16, 110)), (0.42, (130, 30, 155)),
                   (0.60, (225, 60, 140)), (0.80, (70, 60, 190))],
    'lava':       [(0.00, (8, 0, 0)), (0.20, (95, 8, 0)), (0.42, (205, 30, 0)),
                   (0.62, (255, 115, 12)), (0.82, (255, 205, 70))],
    'aurora':     [(0.00, (0, 18, 42)), (0.25, (0, 85, 95)), (0.46, (20, 165, 115)),
                   (0.66, (125, 225, 155)), (0.84, (205, 120, 175))],
    'colorfield': [(0.00, (170, 55, 70)), (0.28, (200, 130, 60)),
                   (0.52, (70, 85, 150)), (0.76, (150, 80, 145))],
    'sky':        [(0.00, (10, 15, 50)), (0.40, (60, 40, 120)),
                   (0.70, (200, 90, 140)), (0.90, (255, 180, 120))],
    'caustic':    [(0.00, (0, 10, 30)), (0.50, (0, 90, 120)),
                   (0.80, (40, 190, 200)), (1.00, (220, 255, 255))],
    'ink':        [(0.00, (4, 2, 16)), (0.40, (50, 10, 90)), (0.65, (150, 25, 140)),
                   (0.85, (70, 90, 210)), (0.95, (235, 220, 255))],
    'smoke':      [(0.00, (8, 8, 14)), (0.45, (60, 55, 80)),
                   (0.70, (130, 120, 155)), (0.90, (215, 205, 230))],
    'fire':       [(0.00, (2, 0, 0)), (0.30, (120, 10, 0)), (0.60, (240, 60, 0)),
                   (0.80, (255, 170, 30)), (0.95, (255, 240, 180))],
    'forest':     [(0.00, (2, 15, 8)), (0.40, (20, 80, 30)), (0.70, (120, 180, 60)),
                   (0.90, (220, 230, 140))],
    'sunset':     [(0.00, (20, 10, 60)), (0.35, (180, 40, 90)),
                   (0.60, (255, 110, 60)), (0.85, (255, 200, 110))],
    'ice':        [(0.00, (4, 10, 30)), (0.40, (20, 90, 140)),
                   (0.70, (120, 200, 230)), (0.95, (235, 250, 255))],
    'mono':       [(0.00, (5, 5, 8)), (0.50, (185, 190, 205))],
}


def _resolve_palette(name, default):
    """Return the named palette's stops, or `default` if name is unknown/None."""
    if name and name in NAMED_PALETTES:
        return NAMED_PALETTES[name]
    return default


class AmbientRipples(ProceduralAnimation):
    """Concentric color rings expanding from center - calm, ordered, pond-like."""

    PALETTE = [(0.00, (4, 6, 32)), (0.30, (0, 80, 150)), (0.55, (0, 185, 205)),
               (0.78, (190, 245, 255)), (0.90, (180, 55, 165))]

    def __init__(self, width, height, fps=30, speed=1.0, rings=2.4):
        super().__init__(width, height, fps)
        cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
        xx, yy = np.meshgrid(np.arange(width, dtype=np.float32),
                             np.arange(height, dtype=np.float32))
        self.r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(
            1.0, np.sqrt(cx * cx + cy * cy))
        self.rings = rings
        self.speed = speed
        self.lut = _build_palette_lut(self.PALETTE)

    def generate_frame(self, time):
        t = float(time)
        phase = self.r * self.rings - t * 0.18 * self.speed
        col = _map_lut(self.lut, phase % 1.0)
        ringv = 0.55 + 0.45 * np.sin(2 * np.pi * phase)
        col = _sat_boost(col, 1.3)
        return (col * ringv[..., None]).astype(np.float32)


class AmbientSpiral(ProceduralAnimation):
    """Slow rotating spiral arms, hue varying along the arm. Ordered, hypnotic."""

    PALETTE = [(0.00, (8, 2, 35)), (0.25, (60, 18, 140)), (0.50, (180, 40, 170)),
               (0.72, (235, 80, 130)), (0.88, (60, 80, 200))]

    def __init__(self, width, height, fps=30, speed=1.0, arms=2.0, twist=2.5):
        super().__init__(width, height, fps)
        cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
        xx, yy = np.meshgrid(np.arange(width, dtype=np.float32),
                             np.arange(height, dtype=np.float32))
        self.theta = np.arctan2(yy - cy, xx - cx) / (2.0 * np.pi)  # -0.5..0.5
        self.r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(
            1.0, np.sqrt(cx * cx + cy * cy))
        self.arms = arms
        self.twist = twist
        self.speed = speed
        self.lut = _build_palette_lut(self.PALETTE)

    def generate_frame(self, time):
        t = float(time)
        phase = self.arms * self.theta + self.r * self.twist - t * 0.20 * self.speed
        col = _map_lut(self.lut, phase % 1.0)
        # Soft radial vignette so the center reads as the spiral's hub.
        vign = np.clip(1.0 - 0.5 * self.r * self.r, 0.25, 1.0)
        col = _sat_boost(col, 1.3)
        return (col * vign[..., None]).astype(np.float32)


class AmbientSweep(ProceduralAnimation):
    """A color gradient that slowly rotates across the panel. Minimal, ordered."""

    PALETTE = [(0.00, (10, 40, 90)), (0.25, (20, 140, 150)),
               (0.50, (120, 60, 180)), (0.72, (230, 70, 140)),
               (0.88, (240, 150, 60))]

    def __init__(self, width, height, fps=30, speed=1.0):
        super().__init__(width, height, fps)
        xn = np.linspace(-0.5, 0.5, width, dtype=np.float32)
        yn = np.linspace(-0.5, 0.5, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.speed = speed
        self.lut = _build_palette_lut(self.PALETTE)

    def generate_frame(self, time):
        t = float(time)
        angle = t * 0.10 * self.speed
        proj = self.xn * np.cos(angle) + self.yn * np.sin(angle)  # ~ -0.7..0.7
        field = (proj * 1.3 + t * 0.07 * self.speed) % 1.0
        col = _map_lut(self.lut, field)
        breathe = 0.85 + 0.15 * np.sin(t * 0.12 * self.speed)
        col = _sat_boost(col, 1.25)
        return (col * breathe).astype(np.float32)


class AmbientBloom(ProceduralAnimation):
    """A glowing center that breathes outward and shifts hue. Symmetric, calm."""

    PALETTE = [(0.00, (40, 4, 30)), (0.30, (180, 30, 40)), (0.55, (240, 120, 30)),
               (0.78, (250, 210, 120)), (0.92, (230, 120, 160))]

    def __init__(self, width, height, fps=30, speed=1.0):
        super().__init__(width, height, fps)
        cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
        xx, yy = np.meshgrid(np.arange(width, dtype=np.float32),
                             np.arange(height, dtype=np.float32))
        self.r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(
            1.0, np.sqrt(cx * cx + cy * cy))
        self.speed = speed
        self.lut = _build_palette_lut(self.PALETTE)

    def generate_frame(self, time):
        t = float(time)
        breathe = 0.5 + 0.5 * np.sin(t * 0.30 * self.speed)
        # Bloom radius grows/shrinks with the breath.
        radius = 0.35 + 0.5 * breathe
        bright = np.clip(1.15 - self.r / radius, 0.0, 1.0)
        field = (self.r * 0.8 - t * 0.05 * self.speed) % 1.0
        col = _map_lut(self.lut, field)
        col = _sat_boost(col, 1.3)
        return (col * bright[..., None]).astype(np.float32)


class AmbientLavaLamp(ProceduralAnimation):
    """Rising, merging soft blobs - classic lava lamp. Organic but not noisy."""

    PALETTE = [(0.00, (6, 2, 22)), (0.42, (70, 12, 50)), (0.66, (205, 40, 30)),
               (0.84, (255, 120, 24)), (0.96, (255, 205, 90))]

    def __init__(self, width, height, fps=30, speed=1.0, num_blobs=5):
        super().__init__(width, height, fps)
        xn = np.linspace(0.0, 1.0, width, dtype=np.float32)
        yn = np.linspace(0.0, 1.0, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.n = int(num_blobs)
        self.speed = speed
        # Deterministic (not random) blob parameters: evenly spread phases.
        i = np.arange(self.n)
        self.sway_phase = (i / self.n) * 2.0 * np.pi
        self.sway_freq = 0.15 + 0.05 * i
        self.rise = 0.035 + 0.012 * ((i % 3))
        self.y0 = i / self.n
        self.r2 = (0.17 ** 2)
        self.lut = _build_palette_lut(self.PALETTE)

    def generate_frame(self, time):
        t = float(time)
        field = np.zeros_like(self.xn)
        for i in range(self.n):
            cx = 0.5 + 0.32 * np.sin(t * self.sway_freq[i] * self.speed
                                     + self.sway_phase[i])
            cy = (self.y0[i] - t * self.rise[i] * self.speed) % 1.0
            d2 = (self.xn - cx) ** 2 + (self.yn - cy) ** 2
            field += self.r2 / (d2 + 0.004)
        v = np.tanh(field / self.n * 1.6)  # 0..1 smooth blob coverage
        col = _map_lut(self.lut, v)
        col = _sat_boost(col, 1.3)
        return col.astype(np.float32)


# --- Noise-based ambient set ----------------------------------------------

class _ValueNoise3D:
    """Tileable 3D value noise. Sampling the 3rd axis with time gives smooth,
    seamless animation; the lattice wraps mod L so there are no seams."""

    def __init__(self, L=16, seed=0):
        self.L = int(L)
        rng = np.random.default_rng(seed)
        self.G = rng.random((self.L, self.L, self.L)).astype(np.float32)

    def sample(self, x, y, z):
        L = self.L
        xi = np.floor(x); yi = np.floor(y); zi = np.floor(z)
        xf = (x - xi).astype(np.float32)
        yf = (y - yi).astype(np.float32)
        zf = (z - zi).astype(np.float32)
        u = xf * xf * (3.0 - 2.0 * xf)
        v = yf * yf * (3.0 - 2.0 * yf)
        w = zf * zf * (3.0 - 2.0 * zf)
        x0 = xi.astype(np.int64) % L; x1 = (x0 + 1) % L
        y0 = yi.astype(np.int64) % L; y1 = (y0 + 1) % L
        z0 = zi.astype(np.int64) % L; z1 = (z0 + 1) % L
        G = self.G
        c000 = G[x0, y0, z0]; c100 = G[x1, y0, z0]
        c010 = G[x0, y1, z0]; c110 = G[x1, y1, z0]
        c001 = G[x0, y0, z1]; c101 = G[x1, y0, z1]
        c011 = G[x0, y1, z1]; c111 = G[x1, y1, z1]
        x00 = c000 * (1 - u) + c100 * u
        x10 = c010 * (1 - u) + c110 * u
        x01 = c001 * (1 - u) + c101 * u
        x11 = c011 * (1 - u) + c111 * u
        y0_ = x00 * (1 - v) + x10 * v
        y1_ = x01 * (1 - v) + x11 * v
        return (y0_ * (1 - w) + y1_ * w).astype(np.float32)


def _fbm(noise, x, y, z, octaves=4, lac=2.0, gain=0.5):
    """Fractal Brownian motion: sum noise octaves -> organic 0..1 field."""
    amp, freq, total, norm = 1.0, 1.0, np.zeros_like(x), 0.0
    for _ in range(octaves):
        total = total + amp * noise.sample(x * freq, y * freq, z * freq)
        norm += amp
        amp *= gain
        freq *= lac
    return total / norm


class AmbientClouds(ProceduralAnimation):
    """Soft fractal clouds drifting - dreamy, low-contrast, dusk palette."""

    PALETTE = [(0.00, (10, 15, 50)), (0.40, (60, 40, 120)),
               (0.70, (200, 90, 140)), (0.90, (255, 180, 120))]

    def __init__(self, width, height, fps=30, speed=1.0, scale=2.0, seed=11,
                 palette=None):
        super().__init__(width, height, fps)
        xn = np.linspace(0.0, 1.0, width, dtype=np.float32)
        yn = np.linspace(0.0, 1.0, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.scale = scale
        self.speed = speed
        self.noise = _ValueNoise3D(16, seed)
        self.lut = _build_palette_lut(_resolve_palette(palette, self.PALETTE))

    def generate_frame(self, time):
        t = float(time)
        z = t * 0.06 * self.speed
        x = self.xn * self.scale + t * 0.02 * self.speed
        y = self.yn * self.scale
        f = _fbm(self.noise, x, y, z, octaves=4)
        f = np.clip((f - 0.5) * 1.5 + 0.5, 0.0, 1.0)
        col = _map_lut(self.lut, f)
        col = _sat_boost(col, 1.25)
        return (col * (0.55 + 0.45 * f)[..., None]).astype(np.float32)


class AmbientCaustics(ProceduralAnimation):
    """Underwater light caustics - bright shifting veins on deep water."""

    PALETTE = [(0.00, (0, 10, 30)), (0.50, (0, 90, 120)),
               (0.80, (40, 190, 200)), (1.00, (220, 255, 255))]

    def __init__(self, width, height, fps=30, speed=1.0, scale=2.2, seed=23,
                 palette=None, warp=1.0):
        super().__init__(width, height, fps)
        xn = np.linspace(0.0, 1.0, width, dtype=np.float32)
        yn = np.linspace(0.0, 1.0, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.scale = scale
        self.speed = speed
        self.warp = warp
        self.noise = _ValueNoise3D(16, seed)
        self.lut = _build_palette_lut(_resolve_palette(palette, self.PALETTE))

    def generate_frame(self, time):
        t = float(time)
        z = t * 0.08 * self.speed
        # Warp the sample coords with noise so the veins ripple organically.
        wa = 0.6 * self.warp
        wx = (_fbm(self.noise, self.xn * 1.3, self.yn * 1.3, z, 2) - 0.5) * wa
        wy = (_fbm(self.noise, self.xn * 1.3 + 5, self.yn * 1.3 + 5, z, 2) - 0.5) * wa
        n = _fbm(self.noise, self.xn * self.scale + wx + t * 0.03,
                 self.yn * self.scale + wy, z, octaves=3)
        # Bright thin network where the field crosses its midline.
        caustic = (1.0 - np.abs(2.0 * n - 1.0)) ** 3
        col = _map_lut(self.lut, np.clip(caustic, 0.0, 1.0))
        col = _sat_boost(col, 1.2)
        return col.astype(np.float32)


class AmbientInk(ProceduralAnimation):
    """Ink diffusing in water - domain-warped tendrils, slow and organic."""

    PALETTE = [(0.00, (4, 2, 16)), (0.40, (50, 10, 90)), (0.65, (150, 25, 140)),
               (0.85, (70, 90, 210)), (0.95, (235, 220, 255))]

    def __init__(self, width, height, fps=30, speed=1.0, scale=1.8, seed=37,
                 palette=None, warp=1.0):
        super().__init__(width, height, fps)
        xn = np.linspace(0.0, 1.0, width, dtype=np.float32)
        yn = np.linspace(0.0, 1.0, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.scale = scale
        self.speed = speed
        self.warp = warp
        self.noise = _ValueNoise3D(16, seed)
        self.lut = _build_palette_lut(_resolve_palette(palette, self.PALETTE))

    def generate_frame(self, time):
        t = float(time)
        z = t * 0.05 * self.speed
        s = self.scale
        wa = 3.5 * self.warp
        # Classic domain-warp fBm (warp the input of a warp) -> inky tendrils.
        q = _fbm(self.noise, self.xn * s, self.yn * s, z, 2)
        r = _fbm(self.noise, self.xn * s + wa * q + t * 0.02,
                 self.yn * s + wa * q, z + 0.3, 2)
        f = _fbm(self.noise, self.xn * s + wa * r, self.yn * s + wa * r, z, 3)
        # Normalize across the frame so the tendrils use the full range
        # (domain-warp fBm clusters tightly otherwise -> looked too dim).
        lo, hi = float(f.min()), float(f.max())
        f = (f - lo) / max(1e-3, hi - lo)
        col = _map_lut(self.lut, (f + t * 0.02) % 1.0)
        col = _sat_boost(col, 1.3)
        return (col * (0.45 + 0.55 * f)[..., None]).astype(np.float32)


class AmbientSmoke(ProceduralAnimation):
    """Drifting smoke rising and dissipating - cool gray-violet, soft."""

    PALETTE = [(0.00, (8, 8, 14)), (0.45, (60, 55, 80)),
               (0.70, (130, 120, 155)), (0.90, (215, 205, 230))]

    def __init__(self, width, height, fps=30, speed=1.0, scale=1.6, seed=51,
                 palette=None):
        super().__init__(width, height, fps)
        xn = np.linspace(0.0, 1.0, width, dtype=np.float32)
        yn = np.linspace(0.0, 1.0, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.scale = scale
        self.speed = speed
        self.noise = _ValueNoise3D(16, seed)
        self.lut = _build_palette_lut(_resolve_palette(palette, self.PALETTE))

    def generate_frame(self, time):
        t = float(time)
        z = t * 0.07 * self.speed
        # Upward drift (smoke rises) + a gentle domain warp.
        wx = (_fbm(self.noise, self.xn + 9, self.yn + 9, z, 2) - 0.5) * 0.5
        x = self.xn * self.scale + wx
        y = self.yn * self.scale + t * 0.14 * self.speed
        f = _fbm(self.noise, x, y, z, octaves=4)
        f = np.clip((f - 0.45) * 1.5 + 0.45, 0.0, 1.0)
        col = _map_lut(self.lut, f)
        col = _sat_boost(col, 1.15)
        return (col * (0.45 + 0.55 * f)[..., None]).astype(np.float32)


class AmbientMarble(ProceduralAnimation):
    """Marble veining - noise folded through a sine so it reads as stone veins."""

    PALETTE = NAMED_PALETTES['ink']

    def __init__(self, width, height, fps=30, speed=1.0, scale=1.6, seed=61,
                 palette=None, warp=1.0, veins=4.0):
        super().__init__(width, height, fps)
        xn = np.linspace(0.0, 1.0, width, dtype=np.float32)
        yn = np.linspace(0.0, 1.0, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.scale = scale
        self.speed = speed
        self.warp = warp
        self.veins = veins
        self.noise = _ValueNoise3D(16, seed)
        self.lut = _build_palette_lut(_resolve_palette(palette, self.PALETTE))

    def generate_frame(self, time):
        t = float(time)
        z = t * 0.05 * self.speed
        turb = _fbm(self.noise, self.xn * self.scale, self.yn * self.scale, z, 4)
        # Fold: position + turbulence through a sine -> sharp marble veins.
        f = 0.5 + 0.5 * np.sin(2 * np.pi * (
            self.xn * self.veins + (turb - 0.5) * 4.0 * self.warp))
        col = _map_lut(self.lut, f)
        col = _sat_boost(col, 1.25)
        return (col * (0.4 + 0.6 * f)[..., None]).astype(np.float32)


class AmbientPlasmaNoise(ProceduralAnimation):
    """High-contrast fractal plasma - vivid, energetic, full-field."""

    PALETTE = NAMED_PALETTES['cosmic']

    def __init__(self, width, height, fps=30, speed=1.0, scale=2.6, seed=71,
                 palette=None):
        super().__init__(width, height, fps)
        xn = np.linspace(0.0, 1.0, width, dtype=np.float32)
        yn = np.linspace(0.0, 1.0, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.scale = scale
        self.speed = speed
        self.noise = _ValueNoise3D(16, seed)
        self.lut = _build_palette_lut(_resolve_palette(palette, self.PALETTE))

    def generate_frame(self, time):
        t = float(time)
        z = t * 0.10 * self.speed
        f = _fbm(self.noise, self.xn * self.scale + t * 0.03,
                 self.yn * self.scale, z, octaves=5)
        # Cycle the palette with the field so colors churn -> plasma energy.
        col = _map_lut(self.lut, (f * 1.6 + t * 0.04) % 1.0)
        col = _sat_boost(col, 1.35)
        return (col * (0.55 + 0.45 * f)[..., None]).astype(np.float32)


class AmbientFlowingLava(ProceduralAnimation):
    """Molten flow - bright cracks of lava between dark crust, rising slowly."""

    PALETTE = NAMED_PALETTES['lava']

    def __init__(self, width, height, fps=30, speed=1.0, scale=2.0, seed=83,
                 palette=None, warp=1.0):
        super().__init__(width, height, fps)
        xn = np.linspace(0.0, 1.0, width, dtype=np.float32)
        yn = np.linspace(0.0, 1.0, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.scale = scale
        self.speed = speed
        self.warp = warp
        self.noise = _ValueNoise3D(16, seed)
        self.lut = _build_palette_lut(_resolve_palette(palette, self.PALETTE))

    def generate_frame(self, time):
        t = float(time)
        z = t * 0.05 * self.speed
        wx = (_fbm(self.noise, self.xn + 3, self.yn + 3, z, 2) - 0.5) * 0.5 * self.warp
        n = _fbm(self.noise, self.xn * self.scale + wx,
                 self.yn * self.scale + t * 0.10 * self.speed, z, octaves=3)
        # Ridged: bright thin cracks where the field crosses its midline.
        crust = np.abs(2.0 * n - 1.0)
        glow = (1.0 - crust) ** 2  # bright in the cracks
        # Map base noise to lava color, then push brightness into the cracks.
        col = _map_lut(self.lut, np.clip(n * 0.7 + glow * 0.5, 0.0, 1.0))
        col = _sat_boost(col, 1.25)
        return (col * (0.25 + 0.75 * glow)[..., None]).astype(np.float32)


class AmbientNebula(ProceduralAnimation):
    """Fractal nebula clouds with a scatter of slow-twinkling stars."""

    PALETTE = NAMED_PALETTES['cosmic']

    def __init__(self, width, height, fps=30, speed=1.0, scale=2.2, seed=97,
                 palette=None, num_stars=10):
        super().__init__(width, height, fps)
        xn = np.linspace(0.0, 1.0, width, dtype=np.float32)
        yn = np.linspace(0.0, 1.0, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.iyy, self.ixx = np.meshgrid(np.arange(width, dtype=np.float32),
                                         np.arange(height, dtype=np.float32),
                                         indexing='ij')
        self.scale = scale
        self.speed = speed
        self.noise = _ValueNoise3D(16, seed)
        self.lut = _build_palette_lut(_resolve_palette(palette, self.PALETTE))
        # Deterministic star field (coherent positions, not re-rolled).
        rng = np.random.default_rng(seed)
        self.n_stars = int(num_stars)
        self.sx = rng.uniform(0, width, self.n_stars).astype(np.float32)
        self.sy = rng.uniform(0, height, self.n_stars).astype(np.float32)
        self.sphase = rng.uniform(0, 2 * np.pi, self.n_stars).astype(np.float32)
        self.srate = rng.uniform(0.6, 1.8, self.n_stars).astype(np.float32)
        xx, yy = np.meshgrid(np.arange(width, dtype=np.float32),
                             np.arange(height, dtype=np.float32))
        self.xx, self.yy = xx, yy

    def generate_frame(self, time):
        t = float(time)
        z = t * 0.05 * self.speed
        f = _fbm(self.noise, self.xn * self.scale + t * 0.015,
                 self.yn * self.scale, z, octaves=4)
        f = np.clip((f - 0.5) * 1.4 + 0.5, 0.0, 1.0)
        col = _map_lut(self.lut, f)
        col = _sat_boost(col, 1.3)
        out = col * (0.45 + 0.55 * f)[..., None]
        # Add slow-twinkling stars on top.
        for i in range(self.n_stars):
            tw = 0.5 + 0.5 * np.sin(t * self.srate[i] + self.sphase[i])
            if tw < 0.35:
                continue
            d2 = (self.xx - self.sx[i]) ** 2 + (self.yy - self.sy[i]) ** 2
            g = (200.0 * tw) * np.exp(-d2 / (2.0 * 0.55 ** 2))
            out[..., 0] += g
            out[..., 1] += g
            out[..., 2] += g * 0.95
        return np.clip(out, 0.0, 255.0).astype(np.float32)


class AmbientWood(ProceduralAnimation):
    """Wood-grain rings - concentric grain distorted by noise. Warm, organic."""

    PALETTE = [(0.00, (40, 18, 6)), (0.45, (110, 55, 20)),
               (0.72, (170, 100, 45)), (0.92, (210, 150, 90))]

    def __init__(self, width, height, fps=30, speed=1.0, rings=5.0, seed=103,
                 palette=None, warp=1.0):
        super().__init__(width, height, fps)
        xn = np.linspace(-0.5, 0.5, width, dtype=np.float32)
        yn = np.linspace(-0.5, 0.5, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.r = np.sqrt(self.xn ** 2 + (self.yn * 1.6) ** 2)
        self.rings = rings
        self.speed = speed
        self.warp = warp
        self.noise = _ValueNoise3D(16, seed)
        self.lut = _build_palette_lut(_resolve_palette(palette, self.PALETTE))

    def generate_frame(self, time):
        t = float(time)
        z = t * 0.03 * self.speed
        n = _fbm(self.noise, (self.xn + 0.5) * 2.0, (self.yn + 0.5) * 2.0, z, 3)
        grain = (self.r * self.rings + (n - 0.5) * 1.2 * self.warp) % 1.0
        f = 0.5 + 0.5 * np.sin(2 * np.pi * grain)
        col = _map_lut(self.lut, f)
        col = _sat_boost(col, 1.15)
        return (col * (0.5 + 0.5 * f)[..., None]).astype(np.float32)


class SkyCycle(ProceduralAnimation):
    """Day -> sunset -> night -> storm -> dawn, ~150s loop.

    Design rules (per the user):
      - Sky is plain dark blue and just DARKENS through the cycle; it goes
        full BLACK at night. The sky never takes on sunset color.
      - The CLOUDS carry all the color: bright-white in day, warm sunset
        oranges/pinks at sunset, dim violet at dusk, dark gray at night,
        nearly black during the storm.
      - The moon is SMALL but bright, only visible at night.
      - Clouds get illuminated by moonlight when they're close to the moon
        and stay dark when far from it. So as a cloud drifts across the
        moon you watch its near-moon edges glow, then dim as it moves on.
        Clouds that cover the moon also occlude it (the cloud opacity
        blends over the moon disc).
      - Storm window: cloud coverage ramps up, clouds darken, deterministic
        lightning flashes punctuate the dark.
    """

    # Sky color per phase. Sky-only luminance, no warm colors -
    # any "sunset" color appears on the clouds, not on this gradient.
    SKY_KEYS = [
        (0.00, (12, 28, 75)),   # dark blue day
        (0.30, (10, 24, 65)),   # day, very slight dim
        (0.45, (6, 14, 38)),    # dusk: sky just gets darker
        (0.58, (2, 5, 18)),     # almost black
        (0.66, (0, 0, 0)),      # BLACK night
        (0.86, (0, 0, 0)),      # still black going into storm
        (0.94, (3, 4, 12)),     # pre-dawn shadow
        (1.00, (12, 28, 75)),   # back to day
    ]

    def __init__(self, width, height, fps=30, duration=150.0, seed=7):
        super().__init__(width, height, fps)
        self.duration = float(duration)
        xn = np.linspace(0.0, 1.0, width, dtype=np.float32)
        yn = np.linspace(0.0, 1.0, height, dtype=np.float32)
        self.xn, self.yn = np.meshgrid(xn, yn)
        self.xx, self.yy = np.meshgrid(np.arange(width, dtype=np.float32),
                                       np.arange(height, dtype=np.float32))
        self.clouds = _ValueNoise3D(16, seed)
        # Small moon up and slightly left of center.
        self.moon_x = (width - 1) * 0.45
        self.moon_y = (height - 1) * 0.30
        # Moon size: smaller-but-bright. Sigma ~0.55 LED -> ~1 bright LED
        # with a hint of glow on its immediate neighbors.
        self.moon_sigma = max(0.45, min(width, height) * 0.05)
        # Moonlight reach: how far moonlight illuminates clouds (in LEDs).
        self.moon_reach = max(2.0, min(width, height) * 0.30)
        # Deterministic lightning schedule (phase positions in the storm).
        rng = np.random.default_rng(seed + 1)
        n_flash = 7
        self.flash_t = np.sort(rng.uniform(0.86, 0.99, n_flash)).astype(np.float32)
        self.flash_x = rng.uniform(0.2, 0.8, n_flash).astype(np.float32)

    @staticmethod
    def _interp_color(keys, x):
        """Cyclic interp through (phase, rgb) keypoints."""
        for i in range(len(keys) - 1):
            p0, c0 = keys[i]
            p1, c1 = keys[i + 1]
            if p0 <= x <= p1:
                f = (x - p0) / max(1e-6, p1 - p0)
                return np.array(c0, np.float32) * (1 - f) + \
                       np.array(c1, np.float32) * f
        return np.array(keys[-1][1], np.float32)

    def _base_cloud_color(self, ph):
        """Cloud base color per phase. Cloud color is where the sunset lives."""
        # Anchor colors.
        day = np.array([240, 245, 255], np.float32)     # bright white day cloud
        sunset = np.array([255, 130, 75], np.float32)   # warm orange/pink sunset
        dusk = np.array([90, 50, 110], np.float32)      # dim violet
        night = np.array([10, 12, 22], np.float32)      # dark gray-black
        storm = np.array([6, 6, 12], np.float32)        # near-black storm cloud
        # Phase blends.
        if ph < 0.28:
            return day
        if ph < 0.42:
            f = (ph - 0.28) / 0.14
            return day * (1 - f) + sunset * f
        if ph < 0.52:
            f = (ph - 0.42) / 0.10
            return sunset * (1 - f) + dusk * f
        if ph < 0.62:
            f = (ph - 0.52) / 0.10
            return dusk * (1 - f) + night * f
        if ph < 0.84:
            return night
        if ph < 0.96:
            f = (ph - 0.84) / 0.12
            return night * (1 - f) + storm * f
        # 0.96..1.0 -> rapidly back to day
        f = (ph - 0.96) / 0.04
        return storm * (1 - f) + day * f

    def generate_frame(self, time):
        t = float(time)
        ph = (t / self.duration) % 1.0

        # --- 1. Sky (uniform, no gradient; just darkens with phase) ---
        sky_rgb = self._interp_color(self.SKY_KEYS, ph)
        frame = np.broadcast_to(sky_rgb, (self.height, self.width, 3)).astype(np.float32).copy()

        # --- 2. Phase factors ---
        moon_vis = float(np.clip((ph - 0.56) / 0.06, 0.0, 1.0)) * \
            float(np.clip((0.92 - ph) / 0.04, 0.0, 1.0))
        storm = float(np.clip((ph - 0.84) / 0.04, 0.0, 1.0)) * \
            float(np.clip((0.99 - ph) / 0.03, 0.0, 1.0))

        # --- 3. Clouds: drifting fractal field + opacity ---
        z = t * 0.04
        cfield = _fbm(self.clouds, self.xn * 2.2 + t * 0.05,
                      self.yn * 2.0, z, octaves=4)
        # Coverage threshold: storm makes the sky cloudier.
        cov = 0.55 - 0.32 * storm
        op = np.clip((cfield - cov) / 0.20, 0.0, 1.0)

        # --- 4. Moon (small, bright). Drawn on the sky BEFORE clouds so
        #         opaque clouds occlude it.
        if moon_vis > 0.01:
            d2_m = (self.xx - self.moon_x) ** 2 + (self.yy - self.moon_y) ** 2
            disc = np.exp(-d2_m / (2.0 * self.moon_sigma ** 2))
            tiny_halo = np.exp(-d2_m / (2.0 * (self.moon_sigma * 2.0) ** 2)) * 0.25
            moon_lum = (disc + tiny_halo) * (255.0 * moon_vis)
            frame[..., 0] += moon_lum
            frame[..., 1] += moon_lum
            frame[..., 2] += moon_lum * 0.97
        else:
            d2_m = None

        # --- 5. Cloud color, with moonlight illumination by proximity ---
        base = self._base_cloud_color(ph)
        cloud_col = np.broadcast_to(base, (self.height, self.width, 3)).astype(np.float32).copy()
        if moon_vis > 0.01:
            # Smooth moonlight falloff with distance to the moon.
            if d2_m is None:
                d2_m = (self.xx - self.moon_x) ** 2 + (self.yy - self.moon_y) ** 2
            ill = np.exp(-d2_m / (2.0 * self.moon_reach ** 2)) * moon_vis
            moonlight = np.array([225, 235, 255], np.float32)
            # Mix the cloud's base color toward bright moonlight as you
            # approach the moon. ill=1 at the moon, ~0 far away.
            ill3 = ill[..., None]
            cloud_col = cloud_col * (1.0 - 0.85 * ill3) + moonlight * (0.85 * ill3)

        # --- 6. Composite clouds OVER everything (occludes moon where dense) ---
        op3 = op[..., None]
        frame = frame * (1.0 - op3) + cloud_col * op3

        # --- 7. Lightning during the storm ---
        if storm > 0.05:
            flash = 0.0
            bolt_x = 0.5
            for ft, fx in zip(self.flash_t, self.flash_x):
                dt = ph - ft
                if 0.0 <= dt < 0.02:
                    env = np.exp(-dt / 0.004) * (0.6 + 0.4 * np.sin(dt * 1800))
                    if env > flash:
                        flash = env
                        bolt_x = fx
            if flash > 0.01:
                amount = flash * storm
                # Whole-scene cloud-lit flash...
                frame += np.array([170, 190, 255], np.float32) * (amount * 0.65)
                # ...plus a brighter vertical column where the bolt strikes.
                col_x = bolt_x * (self.width - 1)
                colmask = np.exp(-((self.xx - col_x) ** 2) / (2.0 * 0.9 ** 2))
                frame += np.array([220, 235, 255], np.float32) * \
                    (colmask[..., None] * amount * 1.4)

        return np.clip(frame, 0.0, 255.0).astype(np.float32)


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
    'supernova_sampler': SupernovaSampler,
    'supernova_blend': SupernovaBlend,
    'cosmic_drift': CosmicDrift,
    'fireworks_show': FireworksShow,
    'flag_mashup': FlagMashup,
    'ambient_cosmic': AmbientCosmic,
    'ambient_lava': AmbientLava,
    'ambient_aurora': AmbientAurora,
    'ambient_field': AmbientColorField,
    'ambient_ripples': AmbientRipples,
    'ambient_spiral': AmbientSpiral,
    'ambient_sweep': AmbientSweep,
    'ambient_bloom': AmbientBloom,
    'ambient_lavalamp': AmbientLavaLamp,
    'ambient_clouds': AmbientClouds,
    'ambient_caustics': AmbientCaustics,
    'ambient_ink': AmbientInk,
    'ambient_smoke': AmbientSmoke,
    'ambient_marble': AmbientMarble,
    'ambient_plasma_noise': AmbientPlasmaNoise,
    'ambient_flowing_lava': AmbientFlowingLava,
    'ambient_nebula': AmbientNebula,
    'ambient_wood': AmbientWood,
    'sky_cycle': SkyCycle,
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