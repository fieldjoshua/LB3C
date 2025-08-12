"""
Unified Lightbox Interface - Main Flask Application

GOALS:
    - Single Flask + Socket.IO server for all LED hardware
    - No duplicated code: all animations go through frame pipeline
    - Extensible driver system (see core/drivers/)
    - Web GUI uploads, playlists, device switching, live controls
    - Systemd-ready for production deployment

See /config/device.default.yml for hardware and render settings.
See /static/main.js and /templates/index.html for GUI controls.
"""

import os
import sys
import logging
import yaml
import time
import threading
import argparse
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.drivers import DeviceManager
from core.drivers.mock import MockDevice

# Try to import hardware drivers (may fail on non-Pi systems)
try:
    from core.drivers.hub75 import HUB75Device
except ImportError as e:
    logger.warning(f"Could not import HUB75 driver: {e}")
    HUB75Device = None

try:
    from core.drivers.ws2811_pi import WS2811Device
except ImportError as e:
    logger.warning(f"Could not import WS2811 driver: {e}")
    WS2811Device = None

try:
    from core.drivers.wled_udp import WLEDDevice
except ImportError as e:
    logger.warning(f"Could not import WLED driver: {e}")
    WLEDDevice = None
from core.frames import FrameProcessor, MediaAnimation
from core.gamma import GammaCorrector, create_corrector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'  # TODO: Use environment variable
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Global state
class AppState:
    def __init__(self):
        self.config = None
        self.device = None
        self.frame_processor = None
        self.gamma_corrector = None
        self.current_animation = None
        self.is_playing = False
        self.playback_thread = None
        self.stop_event = threading.Event()
        self.params = {
            'brightness': 1.0,
            'speed': 1.0,
            'gamma': 2.2,
            'rgb_balance': [1.0, 1.0, 1.0]
        }
        
state = AppState()


def load_config(config_path='config/device.default.yml'):
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return None


def initialize_device(device_type, config):
    """Initialize LED output device"""
    try:
        # Close existing device if any
        if state.device:
            state.device.close()
            
        # Get device-specific config
        device_config = config.copy()
        
        # Create device
        device = DeviceManager.create_device(device_type, device_config)
        device.open()
        
        # Create frame processor
        width, height = device.get_dimensions()
        state.frame_processor = FrameProcessor(width, height, config)
        
        # Create gamma corrector
        state.gamma_corrector = create_corrector(config)
        state.gamma_corrector.set_brightness(state.params['brightness'])
        
        state.device = device
        logger.info(f"Initialized {device_type} device: {width}x{height}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize device: {e}")
        return False


def playback_worker():
    """Background thread for animation playback"""
    last_time = time.time()
    
    while not state.stop_event.is_set():
        if state.is_playing and state.current_animation and state.device:
            try:
                # Calculate delta time
                current_time = time.time()
                delta_time = current_time - last_time
                last_time = current_time
                
                # Adjust for speed parameter
                delta_time *= state.params['speed']
                
                # Get next frame
                frame = state.current_animation.get_next_frame(delta_time)
                
                # Apply gamma correction and RGB balance
                if state.gamma_corrector:
                    frame = state.gamma_corrector.correct_frame(frame)
                
                # Convert to RGB list
                rgb_data = state.current_animation.to_rgb_list(frame)
                
                # Send to device
                h, w = frame.shape[:2]
                state.device.draw_rgb_frame(w, h, rgb_data)
                
                # Emit frame info to clients
                socketio.emit('frame_info', {
                    'current_frame': state.current_animation.current_frame,
                    'total_frames': state.current_animation.frame_count
                })
                
            except Exception as e:
                logger.error(f"Playback error: {e}")
                state.is_playing = False
                
        else:
            last_time = time.time()
            
        # Small sleep to prevent CPU spinning
        time.sleep(0.001)


# Routes
@app.route('/')
def index():
    """Main web interface"""
    return render_template('index.html')


@app.route('/api/status')
def api_status():
    """Get system status"""
    return jsonify({
        'device_type': state.config.get('device') if state.config else None,
        'device_connected': state.device is not None,
        'is_playing': state.is_playing,
        'current_file': state.current_animation.source if state.current_animation else None,
        'parameters': state.params
    })


@app.route('/api/files')
def api_files():
    """List uploaded files"""
    upload_dir = state.config.get('server', {}).get('upload_folder', 'uploads')
    
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    files = []
    for filename in os.listdir(upload_dir):
        filepath = os.path.join(upload_dir, filename)
        if os.path.isfile(filepath):
            files.append({
                'name': filename,
                'size': os.path.getsize(filepath),
                'modified': os.path.getmtime(filepath)
            })
            
    return jsonify({'files': files})


@app.route('/api/upload', methods=['POST'])
def api_upload():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
        
    # Check file extension
    allowed_extensions = state.config.get('server', {}).get('allowed_extensions', [])
    ext = os.path.splitext(file.filename)[1].lower()[1:]  # Remove the dot
    
    if ext not in allowed_extensions:
        return jsonify({'error': f'File type not allowed: {ext}'}), 400
        
    # Save file
    upload_dir = state.config.get('server', {}).get('upload_folder', 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
        
    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_dir, filename)
    
    try:
        file.save(filepath)
        logger.info(f"File uploaded: {filename}")
        return jsonify({'success': True, 'filename': filename})
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return jsonify({'error': str(e)}), 500


# Socket.IO events
@socketio.on('connect')
def handle_connect():
    """Client connected"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'status': 'Connected to LED controller'})


@socketio.on('disconnect')
def handle_disconnect():
    """Client disconnected"""
    logger.info(f"Client disconnected: {request.sid}")


@socketio.on('play')
def handle_play(data):
    """Start playing animation"""
    filename = data.get('filename')
    if not filename:
        emit('error', {'message': 'No filename provided'})
        return
        
    upload_dir = state.config.get('server', {}).get('upload_folder', 'uploads')
    filepath = os.path.join(upload_dir, filename)
    
    if not os.path.exists(filepath):
        emit('error', {'message': 'File not found'})
        return
        
    # Load animation
    animation = state.frame_processor.load_media(filepath)
    if not animation:
        emit('error', {'message': 'Failed to load animation'})
        return
        
    state.current_animation = animation
    state.is_playing = True
    
    emit('playing', {'filename': filename})
    logger.info(f"Playing: {filename}")


@socketio.on('stop')
def handle_stop():
    """Stop playing animation"""
    state.is_playing = False
    if state.device:
        # Clear display
        try:
            width, height = state.device.get_dimensions()
            black_frame = [(0, 0, 0)] * (width * height)
            state.device.draw_rgb_frame(width, height, black_frame)
        except:
            pass
            
    emit('stopped', {})
    logger.info("Playback stopped")


@socketio.on('set_parameter')
def handle_set_parameter(data):
    """Update playback parameter"""
    param = data.get('parameter')
    value = data.get('value')
    
    if param in state.params:
        state.params[param] = value
        
        # Apply parameter updates
        if state.gamma_corrector:
            if param == 'brightness':
                state.gamma_corrector.set_brightness(value)
                if state.device:
                    state.device.set_brightness(value)
            elif param == 'gamma':
                state.gamma_corrector.set_gamma(value)
            elif param == 'rgb_balance':
                state.gamma_corrector.set_rgb_balance(value)
            
        emit('parameter_updated', {'parameter': param, 'value': value})
        logger.info(f"Parameter updated: {param} = {value}")
    else:
        emit('error', {'message': f'Unknown parameter: {param}'})


@socketio.on('switch_device')
def handle_switch_device(data):
    """Switch to different LED hardware"""
    device_type = data.get('device_type')
    
    if device_type not in ['HUB75', 'WS2811_PI', 'WLED', 'MOCK']:
        emit('error', {'message': f'Unknown device type: {device_type}'})
        return
        
    # Update config
    state.config['device'] = device_type
    
    # Reinitialize device
    if initialize_device(device_type, state.config):
        emit('device_switched', {'device_type': device_type})
        logger.info(f"Switched to device: {device_type}")
    else:
        emit('error', {'message': 'Failed to switch device'})


def register_devices():
    """Register all available device types"""
    # Always register mock device
    DeviceManager.register_device('MOCK', MockDevice)
    
    # Register hardware devices if available
    if HUB75Device:
        try:
            DeviceManager.register_device('HUB75', HUB75Device)
        except Exception as e:
            logger.warning(f"Could not register HUB75 device: {e}")
            
    if WS2811Device:
        try:
            DeviceManager.register_device('WS2811_PI', WS2811Device)
        except Exception as e:
            logger.warning(f"Could not register WS2811 device: {e}")
            
    if WLEDDevice:
        try:
            DeviceManager.register_device('WLED', WLEDDevice)
        except Exception as e:
            logger.warning(f"Could not register WLED device: {e}")


def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='LED Animation Control System')
    parser.add_argument('--mock', action='store_true', help='Run in mock mode without hardware')
    parser.add_argument('--config', default='config/device.default.yml', help='Path to config file')
    args = parser.parse_args()
    
    # Register device types
    register_devices()
    
    # Load configuration
    state.config = load_config(args.config)
    if not state.config:
        logger.error("Failed to load configuration")
        return
        
    # Override device type if mock mode
    if args.mock:
        state.config['device'] = 'MOCK'
        logger.info("Running in mock mode")
        
    # Initialize device
    device_type = state.config.get('device', 'HUB75')
    if not initialize_device(device_type, state.config):
        logger.error("Failed to initialize device")
        return
        
    # Start playback thread
    state.playback_thread = threading.Thread(target=playback_worker)
    state.playback_thread.daemon = True
    state.playback_thread.start()
    
    # Get server config
    server_config = state.config.get('server', {})
    host = server_config.get('host', '0.0.0.0')
    port = server_config.get('port', 5000)
    debug = server_config.get('debug', False)
    
    # Run Flask app
    logger.info(f"Starting server on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        state.stop_event.set()
        if state.device:
            state.device.close()