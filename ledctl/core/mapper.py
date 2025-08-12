"""
Coordinate Mapping for Complex LED Layouts

Handles transformation of 2D frame coordinates to physical LED positions
for non-standard layouts (serpentine, circular, custom mappings).
"""

import json
import logging
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class MappingType(Enum):
    """Common LED layout mapping types"""
    LINEAR = "linear"           # Standard left-to-right, top-to-bottom
    SERPENTINE = "serpentine"   # Alternating left-right/right-left rows
    SPIRAL = "spiral"           # Spiral from center outward
    CUSTOM = "custom"           # User-defined mapping from file


class PixelMapper:
    """Maps 2D frame coordinates to physical LED positions"""
    
    def __init__(self, width: int, height: int, mapping_type: MappingType = MappingType.LINEAR):
        self.width = width
        self.height = height
        self.mapping_type = mapping_type
        self.pixel_count = width * height
        
        # Mapping from frame position to LED index
        self.forward_map: List[int] = []
        
        # Mapping from LED index to frame position
        self.reverse_map: Dict[int, Tuple[int, int]] = {}
        
        # Initialize mapping
        self._build_mapping()
        
    def _build_mapping(self):
        """Build the coordinate mapping based on type"""
        if self.mapping_type == MappingType.LINEAR:
            self._build_linear_mapping()
        elif self.mapping_type == MappingType.SERPENTINE:
            self._build_serpentine_mapping()
        elif self.mapping_type == MappingType.SPIRAL:
            self._build_spiral_mapping()
        # CUSTOM mapping loaded separately via load_custom_mapping()
            
    def _build_linear_mapping(self):
        """Standard left-to-right, top-to-bottom mapping"""
        self.forward_map = list(range(self.pixel_count))
        
        for y in range(self.height):
            for x in range(self.width):
                index = y * self.width + x
                self.reverse_map[index] = (x, y)
                
    def _build_serpentine_mapping(self):
        """Serpentine (zig-zag) mapping for LED strips"""
        self.forward_map = []
        
        for y in range(self.height):
            if y % 2 == 0:
                # Even rows: left to right
                for x in range(self.width):
                    index = y * self.width + x
                    self.forward_map.append(index)
                    self.reverse_map[index] = (x, y)
            else:
                # Odd rows: right to left
                for x in range(self.width - 1, -1, -1):
                    index = y * self.width + (self.width - 1 - x)
                    self.forward_map.append(index)
                    self.reverse_map[index] = (x, y)
                    
    def _build_spiral_mapping(self):
        """Spiral mapping from center outward"""
        self.forward_map = []
        visited = set()
        
        # Start from center
        cx, cy = self.width // 2, self.height // 2
        x, y = cx, cy
        
        # Directions: right, down, left, up
        dx = [1, 0, -1, 0]
        dy = [0, 1, 0, -1]
        direction = 0
        steps = 1
        step_count = 0
        direction_changes = 0
        
        while len(visited) < self.pixel_count:
            # Add current position if valid
            if 0 <= x < self.width and 0 <= y < self.height:
                pos = (x, y)
                if pos not in visited:
                    visited.add(pos)
                    index = len(self.forward_map)
                    self.forward_map.append(y * self.width + x)
                    self.reverse_map[index] = (x, y)
                    
            # Move to next position
            x += dx[direction]
            y += dy[direction]
            step_count += 1
            
            # Change direction when needed
            if step_count >= steps:
                step_count = 0
                direction = (direction + 1) % 4
                direction_changes += 1
                
                # Increase steps every two direction changes
                if direction_changes % 2 == 0:
                    steps += 1
                    
    def map_pixel(self, x: int, y: int) -> int:
        """Map 2D coordinate to LED index"""
        if 0 <= x < self.width and 0 <= y < self.height:
            frame_index = y * self.width + x
            if frame_index < len(self.forward_map):
                return self.forward_map[frame_index]
        return -1
        
    def map_frame(self, frame_data: List[Tuple[int, int, int]]) -> List[Tuple[int, int, int]]:
        """Remap entire frame data to physical LED order"""
        if len(frame_data) != self.pixel_count:
            logger.error(f"Frame size mismatch: expected {self.pixel_count}, got {len(frame_data)}")
            return frame_data
            
        # Create remapped frame
        remapped = [None] * self.pixel_count
        
        for i, led_index in enumerate(self.forward_map):
            if 0 <= led_index < len(frame_data):
                remapped[i] = frame_data[led_index]
            else:
                remapped[i] = (0, 0, 0)  # Black for invalid indices
                
        # Replace None values with black
        remapped = [(0, 0, 0) if pixel is None else pixel for pixel in remapped]
        
        return remapped
        
    def load_custom_mapping(self, filepath: str):
        """Load custom mapping from JSON file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            if 'mapping' not in data:
                raise ValueError("JSON must contain 'mapping' field")
                
            mapping = data['mapping']
            
            # Validate mapping
            if len(mapping) != self.pixel_count:
                raise ValueError(f"Mapping size mismatch: expected {self.pixel_count}, got {len(mapping)}")
                
            self.forward_map = mapping
            self.mapping_type = MappingType.CUSTOM
            
            # Rebuild reverse map
            self.reverse_map.clear()
            for physical_index, frame_index in enumerate(mapping):
                if 0 <= frame_index < self.pixel_count:
                    y = frame_index // self.width
                    x = frame_index % self.width
                    self.reverse_map[physical_index] = (x, y)
                    
            logger.info(f"Loaded custom mapping from {filepath}")
            
        except Exception as e:
            logger.error(f"Failed to load custom mapping: {e}")
            # Fall back to linear mapping
            self.mapping_type = MappingType.LINEAR
            self._build_linear_mapping()
            
    def save_mapping(self, filepath: str):
        """Save current mapping to JSON file"""
        data = {
            'width': self.width,
            'height': self.height,
            'type': self.mapping_type.value,
            'mapping': self.forward_map,
            'description': 'LED pixel mapping - maps frame indices to physical LED indices'
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Saved mapping to {filepath}")
        
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about the mapping"""
        return {
            'width': self.width,
            'height': self.height,
            'pixel_count': self.pixel_count,
            'mapping_type': self.mapping_type.value,
            'forward_map_sample': self.forward_map[:10] if len(self.forward_map) > 10 else self.forward_map,
            'reverse_map_count': len(self.reverse_map)
        }


class MultiPanelMapper:
    """Maps frames across multiple LED panels with different orientations"""
    
    def __init__(self):
        self.panels: List[Dict[str, Any]] = []
        self.total_width = 0
        self.total_height = 0
        
    def add_panel(self, x: int, y: int, width: int, height: int, 
                  rotation: int = 0, mapper: Optional[PixelMapper] = None):
        """Add a panel to the multi-panel layout"""
        if mapper is None:
            mapper = PixelMapper(width, height)
            
        panel = {
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'rotation': rotation,  # 0, 90, 180, 270 degrees
            'mapper': mapper
        }
        
        self.panels.append(panel)
        
        # Update total dimensions
        self.total_width = max(self.total_width, x + width)
        self.total_height = max(self.total_height, y + height)
        
        logger.info(f"Added panel at ({x},{y}) size {width}x{height} rotation {rotation}")
        
    def map_frame(self, frame: np.ndarray) -> Dict[int, List[Tuple[int, int, int]]]:
        """Map a frame to multiple panels"""
        panel_data = {}
        
        for i, panel in enumerate(self.panels):
            # Extract panel region from frame
            panel_frame = self._extract_panel_region(frame, panel)
            
            # Apply rotation if needed
            if panel['rotation'] != 0:
                panel_frame = self._rotate_frame(panel_frame, panel['rotation'])
                
            # Convert to RGB list and apply panel's pixel mapping
            h, w = panel_frame.shape[:2]
            rgb_list = []
            for y in range(h):
                for x in range(w):
                    pixel = panel_frame[y, x]
                    rgb_list.append((int(pixel[0]), int(pixel[1]), int(pixel[2])))
                    
            # Apply panel's pixel mapping
            mapped_data = panel['mapper'].map_frame(rgb_list)
            panel_data[i] = mapped_data
            
        return panel_data
        
    def _extract_panel_region(self, frame: np.ndarray, panel: Dict[str, Any]) -> np.ndarray:
        """Extract the region of the frame for a specific panel"""
        x, y = panel['x'], panel['y']
        w, h = panel['width'], panel['height']
        
        # Handle out of bounds
        frame_h, frame_w = frame.shape[:2]
        x_end = min(x + w, frame_w)
        y_end = min(y + h, frame_h)
        
        if x >= frame_w or y >= frame_h:
            # Panel is completely outside frame
            return np.zeros((h, w, 3), dtype=np.uint8)
            
        # Extract region
        region = frame[y:y_end, x:x_end]
        
        # Pad if necessary
        if region.shape[0] < h or region.shape[1] < w:
            padded = np.zeros((h, w, 3), dtype=np.uint8)
            padded[:region.shape[0], :region.shape[1]] = region
            region = padded
            
        return region
        
    def _rotate_frame(self, frame: np.ndarray, rotation: int) -> np.ndarray:
        """Rotate frame by specified degrees (0, 90, 180, 270)"""
        if rotation == 90:
            return np.rot90(frame, k=3)  # 270 counter-clockwise = 90 clockwise
        elif rotation == 180:
            return np.rot90(frame, k=2)
        elif rotation == 270:
            return np.rot90(frame, k=1)  # 90 counter-clockwise = 270 clockwise
        else:
            return frame