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
        # Cool palette: hue in 0.55..0.80 (cyan -> indigo -> violet).
        self.neb_hue_base = float(rng.uniform(0.58, 0.78))

        # ---- Dust: warm Gaussian blobs drifting linearly with wrap-around.
        self.num_dust = int(num_dust)
        self.dust_x0 = rng.uniform(0, width, self.num_dust).astype(np.float32)
        self.dust_y0 = rng.uniform(0, height, self.num_dust).astype(np.float32)
        # Slow drift, in pixels per second at this resolution.
        speed_scale = self._scale / 80.0
        self.dust_vx = rng.uniform(-0.6, 0.6, self.num_dust).astype(np.float32) * speed_scale
        self.dust_vy = rng.uniform(-0.6, 0.6, self.num_dust).astype(np.float32) * speed_scale
        self.dust_sigma = rng.uniform(0.06, 0.12, self.num_dust).astype(np.float32) * self._scale
        # Warm hues: amber / orange / pink, varied by particle.
        self.dust_hue = rng.uniform(-0.04, 0.10, self.num_dust).astype(np.float32) % 1.0
        self.dust_amp = rng.uniform(0.30, 0.55, self.num_dust).astype(np.float32)

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
        # Mostly white-yellow with a few pinks.
        self.near_hue = rng.uniform(0.05, 0.18, self.num_near).astype(np.float32)
        self.near_sat = rng.uniform(0.05, 0.25, self.num_near).astype(np.float32)
        self.near_sigma = rng.uniform(0.020, 0.035, self.num_near).astype(np.float32) * self._scale
        self.near_amp = rng.uniform(0.65, 1.00, self.num_near).astype(np.float32)
        self.near_twink_phase = rng.uniform(0, 2 * np.pi, self.num_near).astype(np.float32)
        self.near_twink_rate = rng.uniform(1.5, 3.5, self.num_near).astype(np.float32)

        # ---- Pulse (central shockwave that fires periodically).
        self.pulse_period = float(pulse_period)
        # Pulse hue cycles through a few warm colors per beat.
        self.pulse_hues = np.array([0.02, 0.10, 0.92, 0.55, 0.78], dtype=np.float32)

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
        # Hue drifts slowly around the cool palette center.
        h = (self.neb_hue_base + 0.05 * np.sin(t * 0.05)
             + 0.04 * v) % 1.0
        s = np.full_like(v, 0.85, dtype=np.float32)
        # Keep nebula DIM so foreground reads above it.
        v_field = (0.20 + 0.18 * v).astype(np.float32)
        return _hsv_to_rgb_array(h.astype(np.float32),
                                 s, v_field).astype(np.float32)

    def _layer_dust(self, t: float) -> np.ndarray:
        accum = np.zeros((self.height, self.width, 3), dtype=np.float32)
        h_ones = np.empty_like(self.xx)
        s_field = np.full_like(self.xx, 0.85, dtype=np.float32)
        for i in range(self.num_dust):
            cx = (float(self.dust_x0[i]) + float(self.dust_vx[i]) * t) % self.width
            cy = (float(self.dust_y0[i]) + float(self.dust_vy[i]) * t) % self.height
            sig = max(1.0, float(self.dust_sigma[i]))
            d2 = (self.xx - cx) ** 2 + (self.yy - cy) ** 2
            amp = float(self.dust_amp[i]) * np.exp(-d2 / (2.0 * sig * sig))
            h_ones.fill(float(self.dust_hue[i]))
            rgb = _hsv_to_rgb_array(h_ones, s_field, amp).astype(np.float32)
            accum += rgb
        return accum

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