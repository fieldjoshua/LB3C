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
import signal
import atexit
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from logging.handlers import RotatingFileHandler
from marshmallow import ValidationError

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Create a temporary logger for import messages
import_logger = logging.getLogger('imports')
import_logger.setLevel(logging.WARNING)
import_handler = logging.StreamHandler()
import_handler.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
import_logger.addHandler(import_handler)

from core.config import Config, ConfigurationError
from core.drivers import DeviceManager
from core.drivers.mock import MockDevice
from core.errors import (
    register_error_handlers, DeviceError, AnimationError, 
    FileProcessingError, safe_execute, emit_error
)
from core.security import (
    setup_security, limiter, validate_input, require_api_key,
    sanitize_path, validate_file_type, FileUploadSchema,
    DeviceConfigSchema, AnimationControlSchema, ParameterUpdateSchema
)

# Try to import hardware drivers (may fail on non-Pi systems)
try:
    from core.drivers.hub75 import HUB75Device
except ImportError as e:
    import_logger.warning(f"Could not import HUB75 driver: {e}")
    HUB75Device = None

try:
    from core.drivers.ws2811_pi import WS2811Device
except ImportError as e:
    import_logger.warning(f"Could not import WS2811 driver: {e}")
    WS2811Device = None

try:
    from core.drivers.wled_udp import WLEDDevice
except ImportError as e:
    import_logger.warning(f"Could not import WLED driver: {e}")
    WLEDDevice = None
from core.frames import FrameProcessor, MediaAnimation
from core.gamma import GammaCorrector, create_corrector
from core.automations import create_automation, get_automation_info, AUTOMATION_REGISTRY

# Initialize configuration
try:
    config = Config()
    config.validate()
except ConfigurationError as e:
    print(f"Configuration error: {e}")
    print("Please ensure FLASK_SECRET_KEY is set in your environment or .env file")
    sys.exit(1)

# Configure logging with rotation
logger = logging.getLogger(__name__)
logger.setLevel(getattr(logging, config.logging['level']))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(config.logging['format']))
logger.addHandler(console_handler)

# File handler with rotation
if config.logging['file']:
    file_handler = RotatingFileHandler(
        config.logging['file'],
        maxBytes=config.logging['max_size'],
        backupCount=config.logging['backup_count']
    )
    file_handler.setFormatter(logging.Formatter(config.logging['format']))
    logger.addHandler(file_handler)

# Flask app setup
app = Flask(__name__)
app.config.update(config.flask)
app.config['MAX_CONTENT_LENGTH'] = config.upload['max_size']
app.config['SESSION_COOKIE_SECURE'] = config.security['session_cookie_secure']
app.config['SESSION_COOKIE_HTTPONLY'] = config.security['session_cookie_httponly']
app.config['SESSION_COOKIE_SAMESITE'] = config.security['session_cookie_samesite']

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Register error handlers
register_error_handlers(app, socketio)

# Setup security features
setup_security(app, socketio)

# Track app start time for uptime
app.start_time = time.time()

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
            try:
                state.device.close()
            except Exception as e:
                logger.warning(f"Error closing previous device: {e}")
            
        # Get device-specific config
        device_config = config.copy()
        
        # Create device
        try:
            device = DeviceManager.create_device(device_type, device_config)
        except Exception as e:
            raise DeviceError(f"Failed to create {device_type} device: {str(e)}", device_type=device_type)
        
        try:
            device.open()
        except Exception as e:
            raise DeviceError(f"Failed to open {device_type} device: {str(e)}", device_type=device_type)
        
        # Create frame processor
        try:
            width, height = device.get_dimensions()
            state.frame_processor = FrameProcessor(width, height, config)
        except Exception as e:
            device.close()
            raise DeviceError(f"Failed to create frame processor: {str(e)}", device_type=device_type)
        
        # Create gamma corrector
        state.gamma_corrector = create_corrector(config)
        state.gamma_corrector.set_brightness(state.params['brightness'])
        
        state.device = device
        logger.info(f"Initialized {device_type} device: {width}x{height}")
        
        # Emit success to clients
        socketio.emit('device_initialized', {
            'type': device_type,
            'width': width,
            'height': height
        })
        
        return True
        
    except DeviceError:
        raise  # Re-raise device errors
    except Exception as e:
        logger.exception(f"Unexpected error initializing device")
        raise DeviceError(f"Failed to initialize device: {str(e)}", device_type=device_type)


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
                
                # Get next frame based on animation type
                if hasattr(state.current_animation, 'update'):
                    # ProceduralAnimation
                    frame = state.current_animation.update(delta_time)
                else:
                    # MediaAnimation
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
                if hasattr(state.current_animation, 'current_frame'):
                    # MediaAnimation has frame count info
                    socketio.emit('frame_info', {
                        'current_frame': state.current_animation.current_frame,
                        'total_frames': state.current_animation.frame_count
                    })
                else:
                    # ProceduralAnimation - emit time info
                    socketio.emit('frame_info', {
                        'time': state.current_animation.time,
                        'type': 'procedural'
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
    # Get current animation info
    current_animation_info = None
    if state.current_animation:
        if hasattr(state.current_animation, 'source'):
            # File-based animation
            current_animation_info = {'type': 'file', 'source': state.current_animation.source}
        else:
            # Procedural animation
            current_animation_info = {'type': 'automation', 'name': state.current_animation.__class__.__name__}
    
    return jsonify({
        'device_type': state.config.get('device') if state.config else None,
        'device_connected': state.device is not None,
        'is_playing': state.is_playing,
        'current_animation': current_animation_info,
        'parameters': state.params
    })


@app.route('/api/files')
@limiter.limit("100 per minute")
@require_api_key
def api_files():
    """List uploaded files"""
    upload_dir = config.upload['folder']
    
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


@app.route('/api/automations')
@limiter.limit("100 per minute")
def api_automations():
    """Get available automations and their parameters"""
    return jsonify(get_automation_info())


@app.route('/api/upload', methods=['POST'])
@limiter.limit(os.getenv('RATE_LIMIT_UPLOAD', '10 per hour'))
@require_api_key
def api_upload():
    """Handle file upload"""
    try:
        if 'file' not in request.files:
            raise FileProcessingError('No file provided in request')
            
        file = request.files['file']
        if not file or file.filename == '':
            raise FileProcessingError('No file selected')
            
        # Sanitize filename
        original_filename = file.filename
        filename = sanitize_path(original_filename)
        if not filename:
            raise FileProcessingError('Invalid filename', filename=original_filename)
            
        # Additional validation
        if not FileUploadSchema.validate_filename(filename):
            raise FileProcessingError('Invalid filename format', filename=original_filename)
            
        # Check file extension
        ext = os.path.splitext(filename)[1].lower()[1:]  # Remove the dot
        
        if ext not in config.upload['allowed_extensions']:
            raise FileProcessingError(
                f'File type not allowed: {ext}',
                filename=filename,
                reason=f"Allowed types: {', '.join(config.upload['allowed_extensions'])}"
            )
            
        # Ensure upload directory exists
        upload_dir = config.upload['folder']
        os.makedirs(upload_dir, exist_ok=True)
        
        # Check for duplicate filename
        filepath = os.path.join(upload_dir, filename)
        if os.path.exists(filepath):
            # Add timestamp to make unique
            base, ext = os.path.splitext(filename)
            timestamp = int(time.time())
            filename = f"{base}_{timestamp}{ext}"
            filepath = os.path.join(upload_dir, filename)
        
        # Save file
        file.save(filepath)
        logger.info(f"File uploaded: {filename} (original: {original_filename})")
        
        # Verify file was saved correctly
        if not os.path.exists(filepath) or os.path.getsize(filepath) == 0:
            os.remove(filepath) if os.path.exists(filepath) else None
            raise FileProcessingError('File save failed', filename=filename)
            
        return jsonify({
            'success': True,
            'filename': filename,
            'size': os.path.getsize(filepath)
        })
        
    except FileProcessingError:
        raise  # Let error handler handle it
    except Exception as e:
        logger.exception("Unexpected upload error")
        raise FileProcessingError(f"Upload failed: {str(e)}")


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
    """Start playing animation or automation"""
    animation_type = data.get('type', 'file')
    
    if animation_type == 'file':
        # Play file-based animation
        filename = data.get('filename')
        if not filename:
            emit('error', {'message': 'No filename provided'})
            return
            
        upload_dir = config.upload['folder']
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
        
        emit('playing', {'type': 'file', 'filename': filename})
        logger.info(f"Playing file: {filename}")
        
    elif animation_type == 'automation':
        # Play procedural automation
        automation_name = data.get('automation')
        if not automation_name:
            emit('error', {'message': 'No automation name provided'})
            return
            
        if automation_name not in AUTOMATION_REGISTRY:
            emit('error', {'message': f'Unknown automation: {automation_name}'})
            return
            
        # Get device dimensions
        if not state.device:
            emit('error', {'message': 'No device connected'})
            return
            
        width, height = state.device.get_dimensions()
        
        # Get automation parameters
        params = data.get('params', {})
        
        try:
            # Create automation instance
            fps = state.config.get('render', {}).get('fps_cap', 30)
            automation = create_automation(automation_name, width, height, 
                                         fps=fps, **params)
            state.current_animation = automation
            state.is_playing = True
            
            emit('playing', {'type': 'automation', 'automation': automation_name, 'params': params})
            logger.info(f"Playing automation: {automation_name}")
            
        except Exception as e:
            emit('error', {'message': f'Failed to create automation: {str(e)}'})
            logger.error(f"Automation creation error: {e}")
    
    else:
        emit('error', {'message': f'Unknown animation type: {animation_type}'})


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
    # Validate input
    try:
        schema = ParameterUpdateSchema()
        validated = schema.load(data)
        param = validated['parameter']
        value = validated['value']
    except ValidationError as e:
        emit('error', {'message': 'Invalid parameter data', 'details': e.messages})
        return
    
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


@socketio.on('update_hardware_settings')
@limiter.limit("10 per hour")
def handle_update_hardware_settings(data):
    """Update HUB75 hardware settings"""
    if state.config.get('device') != 'HUB75':
        emit('error', {'message': 'Hardware settings only available for HUB75'})
        return
        
    try:
        # Update configuration
        hub75_config = state.config.get('hub75', {})
        
        if 'gpio_slowdown' in data:
            hub75_config['gpio_slowdown'] = max(1, min(4, int(data['gpio_slowdown'])))
        if 'pwm_bits' in data:
            hub75_config['pwm_bits'] = max(8, min(12, int(data['pwm_bits'])))
        if 'pwm_lsb_nanoseconds' in data:
            hub75_config['pwm_lsb_nanoseconds'] = max(50, min(300, int(data['pwm_lsb_nanoseconds'])))
        if 'limit_refresh_rate_hz' in data:
            hub75_config['limit_refresh_rate_hz'] = max(30, min(200, int(data['limit_refresh_rate_hz'])))
        if 'show_refresh_rate' in data:
            hub75_config['show_refresh_rate'] = bool(data['show_refresh_rate'])
            
        state.config['hub75'] = hub75_config
        
        # Reinitialize the device with new settings
        logger.info(f"Updating HUB75 hardware settings: {data}")
        
        # Stop current playback
        old_playing = state.is_playing
        state.is_playing = False
        
        # Reinitialize device
        if initialize_device('HUB75', state.config):
            emit('hardware_settings_updated', hub75_config)
            emit('success', {'message': 'Hardware settings applied successfully'})
            
            # Resume playback if it was playing
            if old_playing and state.current_animation:
                state.is_playing = True
        else:
            emit('error', {'message': 'Failed to apply hardware settings'})
            
    except Exception as e:
        logger.error(f"Hardware settings update error: {e}")
        emit('error', {'message': f'Failed to update settings: {str(e)}'})


@socketio.on('switch_device')
@limiter.limit(os.getenv('RATE_LIMIT_DEVICE_SWITCH', '30 per hour'))
def handle_switch_device(data):
    """Switch to different LED hardware"""
    # Validate input
    try:
        schema = DeviceConfigSchema()
        validated = schema.load(data)
        device_type = validated['device_type']
    except ValidationError as e:
        emit('error', {'message': 'Invalid device configuration', 'details': e.messages})
        return
    
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
    global config
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='LED Animation Control System')
    parser.add_argument('--mock', action='store_true', help='Run in mock mode without hardware')
    parser.add_argument('--config', help='Path to config file')
    parser.add_argument('--env', help='Path to .env file')
    args = parser.parse_args()
    
    # Re-initialize config with command line args if provided
    if args.config or args.env:
        try:
            config = Config(config_path=args.config, env_file=args.env)
            config.validate()
        except ConfigurationError as e:
            logger.error(f"Configuration error: {e}")
            return
    
    # Register device types
    register_devices()
    
    # Register API blueprint
    try:
        from api.routes import api_bp
        app.register_blueprint(api_bp)
        logger.info("API v1 endpoints registered")
    except ImportError as e:
        logger.warning(f"Could not load API routes: {e}")
    
    # Load YAML configuration for device settings
    state.config = load_config(args.config or config.config_path)
    if not state.config:
        logger.error("Failed to load device configuration")
        return
        
    # Override device type if mock mode or env variable
    if args.mock or config.hardware['mock_mode']:
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
    
    # Run Flask app
    logger.info(f"Starting server on {config.server['host']}:{config.server['port']}")
    logger.info(f"Environment: {config.flask['ENV']}")
    socketio.run(app, host=config.server['host'], port=config.server['port'], debug=config.flask['DEBUG'])


def cleanup():
    """Clean shutdown handler"""
    logger.info("Shutting down...")
    state.stop_event.set()
    
    # Wait for playback thread to stop
    if hasattr(state, 'playback_thread') and state.playback_thread and state.playback_thread.is_alive():
        state.playback_thread.join(timeout=5.0)
    
    # Close device
    if state.device:
        try:
            state.device.close()
        except Exception as e:
            logger.error(f"Error closing device: {e}")
    
    logger.info("Shutdown complete")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    cleanup()
    sys.exit(0)


if __name__ == '__main__':
    # Register cleanup handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    atexit.register(cleanup)
    
    try:
        main()
    except KeyboardInterrupt:
        pass  # Handled by signal handler
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        cleanup()
        sys.exit(1)