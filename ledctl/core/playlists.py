"""
Playlist Management for LED Animation System

Handles sequential playback of multiple animation files with
configurable transitions and repeat modes.
"""

import os
import time
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from .frames import FrameProcessor

logger = logging.getLogger(__name__)


class PlayMode(Enum):
    """Playlist playback modes"""
    ONCE = "once"           # Play through once and stop
    LOOP = "loop"           # Loop entire playlist
    LOOP_SINGLE = "single"  # Loop current item
    RANDOM = "random"       # Random order


class TransitionType(Enum):
    """Transition types between playlist items"""
    NONE = "none"           # Hard cut
    FADE = "fade"           # Crossfade
    SLIDE = "slide"         # Slide transition


@dataclass
class PlaylistItem:
    """Single item in a playlist"""
    filename: str
    duration: Optional[float] = None  # Play duration in seconds (None = full)
    transition: TransitionType = TransitionType.NONE
    transition_duration: float = 0.5  # Transition duration in seconds


class Playlist:
    """Manages a sequence of animations"""
    
    def __init__(self, name: str):
        self.name = name
        self.items: List[PlaylistItem] = []
        self.current_index = 0
        self.play_mode = PlayMode.LOOP
        self.is_playing = False
        self.start_time = 0
        self.item_start_time = 0
        
    def add_item(self, filename: str, duration: Optional[float] = None,
                 transition: TransitionType = TransitionType.NONE,
                 transition_duration: float = 0.5):
        """Add an item to the playlist"""
        item = PlaylistItem(
            filename=filename,
            duration=duration,
            transition=transition,
            transition_duration=transition_duration
        )
        self.items.append(item)
        logger.info(f"Added {filename} to playlist {self.name}")
        
    def remove_item(self, index: int):
        """Remove item at index"""
        if 0 <= index < len(self.items):
            removed = self.items.pop(index)
            logger.info(f"Removed {removed.filename} from playlist {self.name}")
            # Adjust current index if needed
            if self.current_index >= len(self.items) and self.items:
                self.current_index = 0
                
    def clear(self):
        """Clear all items"""
        self.items.clear()
        self.current_index = 0
        
    def move_item(self, from_index: int, to_index: int):
        """Move item from one position to another"""
        if (0 <= from_index < len(self.items) and 
            0 <= to_index < len(self.items)):
            item = self.items.pop(from_index)
            self.items.insert(to_index, item)
            
    def get_current_item(self) -> Optional[PlaylistItem]:
        """Get current playlist item"""
        if 0 <= self.current_index < len(self.items):
            return self.items[self.current_index]
        return None
        
    def next_item(self):
        """Advance to next item based on play mode"""
        if not self.items:
            return
            
        if self.play_mode == PlayMode.LOOP_SINGLE:
            # Stay on current item
            pass
        elif self.play_mode == PlayMode.RANDOM:
            import random
            self.current_index = random.randint(0, len(self.items) - 1)
        else:
            # ONCE or LOOP mode
            self.current_index += 1
            if self.current_index >= len(self.items):
                if self.play_mode == PlayMode.LOOP:
                    self.current_index = 0
                else:  # ONCE mode
                    self.current_index = len(self.items) - 1
                    self.is_playing = False
                    
        self.item_start_time = time.time()
        
    def previous_item(self):
        """Go to previous item"""
        if not self.items:
            return
            
        self.current_index -= 1
        if self.current_index < 0:
            if self.play_mode in [PlayMode.LOOP, PlayMode.LOOP_SINGLE]:
                self.current_index = len(self.items) - 1
            else:
                self.current_index = 0
                
        self.item_start_time = time.time()
        
    def should_advance(self) -> bool:
        """Check if it's time to advance to next item"""
        if not self.is_playing or not self.items:
            return False
            
        current_item = self.get_current_item()
        if current_item and current_item.duration:
            elapsed = time.time() - self.item_start_time
            return elapsed >= current_item.duration
            
        return False
        
    def start(self):
        """Start playlist playback"""
        self.is_playing = True
        self.start_time = time.time()
        self.item_start_time = time.time()
        self.current_index = 0
        
    def stop(self):
        """Stop playlist playback"""
        self.is_playing = False
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert playlist to dictionary"""
        return {
            'name': self.name,
            'items': [
                {
                    'filename': item.filename,
                    'duration': item.duration,
                    'transition': item.transition.value,
                    'transition_duration': item.transition_duration
                }
                for item in self.items
            ],
            'play_mode': self.play_mode.value,
            'current_index': self.current_index
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Playlist':
        """Create playlist from dictionary"""
        playlist = cls(data['name'])
        playlist.play_mode = PlayMode(data.get('play_mode', 'loop'))
        
        for item_data in data.get('items', []):
            playlist.add_item(
                filename=item_data['filename'],
                duration=item_data.get('duration'),
                transition=TransitionType(item_data.get('transition', 'none')),
                transition_duration=item_data.get('transition_duration', 0.5)
            )
            
        return playlist


class PlaylistManager:
    """Manages multiple playlists"""
    
    def __init__(self, frame_processor: FrameProcessor):
        self.frame_processor = frame_processor
        self.playlists: Dict[str, Playlist] = {}
        self.current_playlist: Optional[str] = None
        self.current_animation = None
        
    def create_playlist(self, name: str) -> Playlist:
        """Create a new playlist"""
        playlist = Playlist(name)
        self.playlists[name] = playlist
        logger.info(f"Created playlist: {name}")
        return playlist
        
    def delete_playlist(self, name: str):
        """Delete a playlist"""
        if name in self.playlists:
            del self.playlists[name]
            if self.current_playlist == name:
                self.current_playlist = None
            logger.info(f"Deleted playlist: {name}")
            
    def get_playlist(self, name: str) -> Optional[Playlist]:
        """Get playlist by name"""
        return self.playlists.get(name)
        
    def set_current_playlist(self, name: str):
        """Set the active playlist"""
        if name in self.playlists:
            self.current_playlist = name
            playlist = self.playlists[name]
            playlist.start()
            self._load_current_item()
            
    def _load_current_item(self):
        """Load the current playlist item"""
        if not self.current_playlist:
            return
            
        playlist = self.playlists[self.current_playlist]
        item = playlist.get_current_item()
        
        if item and os.path.exists(item.filename):
            self.current_animation = self.frame_processor.load_media(item.filename)
            
    def update(self, delta_time: float):
        """Update playlist state"""
        if not self.current_playlist:
            return
            
        playlist = self.playlists[self.current_playlist]
        
        # Check if we should advance to next item
        if playlist.should_advance():
            playlist.next_item()
            self._load_current_item()
            
    def get_current_frame(self, delta_time: float):
        """Get current frame from active playlist"""
        if self.current_animation:
            return self.current_animation.get_next_frame(delta_time)
        return None
        
    def save_playlists(self, filepath: str):
        """Save all playlists to file"""
        import json
        data = {
            name: playlist.to_dict()
            for name, playlist in self.playlists.items()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
            
        logger.info(f"Saved {len(self.playlists)} playlists to {filepath}")
        
    def load_playlists(self, filepath: str):
        """Load playlists from file"""
        import json
        
        if not os.path.exists(filepath):
            return
            
        with open(filepath, 'r') as f:
            data = json.load(f)
            
        self.playlists.clear()
        for name, playlist_data in data.items():
            playlist = Playlist.from_dict(playlist_data)
            self.playlists[name] = playlist
            
        logger.info(f"Loaded {len(self.playlists)} playlists from {filepath}")