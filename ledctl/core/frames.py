"""
Frame Loading and Processing Module

Handles loading and processing of various media formats (GIF, PNG, JPG, MP4)
into RGB frame data for LED output.
"""

import os
import logging
from typing import List, Tuple, Optional, Iterator, Any, Dict
from PIL import Image, ImageSequence
import numpy as np
import cv2
from threading import Lock
from collections import deque

logger = logging.getLogger(__name__)


class FrameProcessor:
    """Processes various media formats into RGB frames"""
    
    SUPPORTED_IMAGE_FORMATS = {'.gif', '.png', '.jpg', '.jpeg', '.bmp', '.webp'}
    SUPPORTED_VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.webm', '.mkv'}
    
    def __init__(self, target_width: int, target_height: int, config: Dict[str, Any] = None):
        """
        Initialize frame processor
        
        Args:
            target_width: Target frame width
            target_height: Target frame height
            config: Rendering configuration
        """
        self.target_width = target_width
        self.target_height = target_height
        self.config = config or {}
        
        # Get render settings
        render_config = self.config.get('render', {})
        self.scale_method = render_config.get('scale', 'LANCZOS')
        self.fps_cap = render_config.get('fps_cap', 60)
        
        # Cache for loaded frames
        self.frame_cache = {}
        self.cache_lock = Lock()
        self.max_cache_size = 100  # Maximum cached animations
        
    def load_media(self, file_path: str) -> Optional['MediaAnimation']:
        """
        Load media file and return animation object
        
        Args:
            file_path: Path to media file
            
        Returns:
            MediaAnimation object or None if failed
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None
            
        # Check cache first
        with self.cache_lock:
            if file_path in self.frame_cache:
                logger.debug(f"Loading from cache: {file_path}")
                return self.frame_cache[file_path]
                
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext in self.SUPPORTED_IMAGE_FORMATS:
                if ext == '.gif':
                    animation = self._load_gif(file_path)
                else:
                    animation = self._load_static_image(file_path)
            elif ext in self.SUPPORTED_VIDEO_FORMATS:
                animation = self._load_video(file_path)
            else:
                logger.error(f"Unsupported file format: {ext}")
                return None
                
            # Add to cache
            with self.cache_lock:
                self.frame_cache[file_path] = animation
                
                # Evict oldest if cache full
                if len(self.frame_cache) > self.max_cache_size:
                    oldest = next(iter(self.frame_cache))
                    del self.frame_cache[oldest]
                    
            return animation
            
        except Exception as e:
            logger.error(f"Error loading media {file_path}: {e}")
            return None
            
    def _load_gif(self, file_path: str) -> 'MediaAnimation':
        """Load animated GIF file"""
        frames = []
        durations = []
        
        with Image.open(file_path) as img:
            for frame in ImageSequence.Iterator(img):
                # Convert to RGB
                rgb_frame = frame.convert('RGB')
                
                # Resize to target dimensions
                rgb_frame = self._resize_image(rgb_frame)
                
                # Convert to numpy array
                frame_array = np.array(rgb_frame)
                frames.append(frame_array)
                
                # Get frame duration (default 100ms if not specified)
                duration = frame.info.get('duration', 100) / 1000.0
                durations.append(duration)
                
        return MediaAnimation(frames, durations, file_path)
        
    def _load_static_image(self, file_path: str) -> 'MediaAnimation':
        """Load static image file"""
        with Image.open(file_path) as img:
            # Convert to RGB
            rgb_img = img.convert('RGB')
            
            # Resize to target dimensions
            rgb_img = self._resize_image(rgb_img)
            
            # Convert to numpy array
            frame_array = np.array(rgb_img)
            
        # Single frame with 1 second duration
        return MediaAnimation([frame_array], [1.0], file_path)
        
    def _load_video(self, file_path: str) -> 'MediaAnimation':
        """Load video file"""
        frames = []
        durations = []
        
        cap = cv2.VideoCapture(file_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {file_path}")
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30  # Default fallback
            
        frame_duration = 1.0 / min(fps, self.fps_cap)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Convert BGR to RGB
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize to target dimensions
            rgb_frame = self._resize_frame(rgb_frame)
            
            frames.append(rgb_frame)
            durations.append(frame_duration)
            
        cap.release()
        
        if not frames:
            raise ValueError(f"No frames extracted from video: {file_path}")
            
        return MediaAnimation(frames, durations, file_path)
        
    def _resize_image(self, img: Image.Image) -> Image.Image:
        """Resize PIL Image to target dimensions"""
        if img.size == (self.target_width, self.target_height):
            return img
            
        # Map scale method to PIL constants
        resample_map = {
            'NEAREST': Image.Resampling.NEAREST,
            'LINEAR': Image.Resampling.BILINEAR,
            'CUBIC': Image.Resampling.BICUBIC,
            'LANCZOS': Image.Resampling.LANCZOS,
        }
        
        resample = resample_map.get(self.scale_method, Image.Resampling.LANCZOS)
        
        return img.resize((self.target_width, self.target_height), resample)
        
    def _resize_frame(self, frame: np.ndarray) -> np.ndarray:
        """Resize numpy array frame to target dimensions"""
        if frame.shape[:2] == (self.target_height, self.target_width):
            return frame
            
        # Map scale method to OpenCV constants
        interpolation_map = {
            'NEAREST': cv2.INTER_NEAREST,
            'LINEAR': cv2.INTER_LINEAR,
            'CUBIC': cv2.INTER_CUBIC,
            'LANCZOS': cv2.INTER_LANCZOS4,
        }
        
        interpolation = interpolation_map.get(self.scale_method, cv2.INTER_LANCZOS4)
        
        return cv2.resize(frame, (self.target_width, self.target_height), 
                         interpolation=interpolation)
        
    def clear_cache(self) -> None:
        """Clear frame cache"""
        with self.cache_lock:
            self.frame_cache.clear()
            logger.info("Frame cache cleared")


class MediaAnimation:
    """Container for loaded animation frames"""
    
    def __init__(self, frames: List[np.ndarray], durations: List[float], source: str):
        """
        Initialize animation
        
        Args:
            frames: List of numpy arrays (H, W, 3)
            durations: List of frame durations in seconds
            source: Source file path
        """
        self.frames = frames
        self.durations = durations
        self.source = source
        self.total_duration = sum(durations)
        self.frame_count = len(frames)
        
        # Current playback state
        self.current_frame = 0
        self.frame_time = 0.0
        self.loop = True
        
    def get_frame_at_time(self, time: float) -> Tuple[np.ndarray, int]:
        """
        Get frame at specific time
        
        Args:
            time: Time in seconds
            
        Returns:
            (frame, frame_index)
        """
        if not self.frames:
            return None, -1
            
        if self.loop:
            time = time % self.total_duration
            
        accumulated_time = 0.0
        
        for i, duration in enumerate(self.durations):
            if accumulated_time <= time < accumulated_time + duration:
                return self.frames[i], i
            accumulated_time += duration
            
        # Return last frame if beyond duration
        return self.frames[-1], len(self.frames) - 1
        
    def get_next_frame(self, delta_time: float) -> np.ndarray:
        """
        Get next frame based on time delta
        
        Args:
            delta_time: Time elapsed since last frame
            
        Returns:
            Current frame
        """
        self.frame_time += delta_time
        
        # Check if we need to advance frame
        while self.frame_time >= self.durations[self.current_frame]:
            self.frame_time -= self.durations[self.current_frame]
            self.current_frame += 1
            
            if self.current_frame >= self.frame_count:
                if self.loop:
                    self.current_frame = 0
                else:
                    self.current_frame = self.frame_count - 1
                    break
                    
        return self.frames[self.current_frame]
        
    def reset(self) -> None:
        """Reset animation to beginning"""
        self.current_frame = 0
        self.frame_time = 0.0
        
    def to_rgb_list(self, frame: np.ndarray) -> List[Tuple[int, int, int]]:
        """
        Convert numpy frame to flat RGB tuple list
        
        Args:
            frame: Numpy array (H, W, 3)
            
        Returns:
            Flat list of RGB tuples
        """
        # Ensure frame is uint8
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)
            
        # Flatten and convert to tuples
        flat = frame.reshape(-1, 3)
        return [tuple(pixel) for pixel in flat]


class ProceduralAnimation:
    """Base class for procedural animations"""
    
    def __init__(self, width: int, height: int, fps: float = 30):
        self.width = width
        self.height = height
        self.fps = fps
        self.frame_duration = 1.0 / fps
        self.time = 0.0
        
    def update(self, delta_time: float) -> np.ndarray:
        """Update animation and return current frame"""
        self.time += delta_time
        return self.generate_frame(self.time)
        
    def generate_frame(self, time: float) -> np.ndarray:
        """Generate frame at given time - override in subclasses"""
        raise NotImplementedError
        
    def to_rgb_list(self, frame: np.ndarray) -> List[Tuple[int, int, int]]:
        """Convert frame to RGB tuple list"""
        if frame.dtype != np.uint8:
            frame = np.clip(frame, 0, 255).astype(np.uint8)
        flat = frame.reshape(-1, 3)
        return [tuple(pixel) for pixel in flat]