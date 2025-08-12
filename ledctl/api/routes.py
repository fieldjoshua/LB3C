"""
REST API routes with proper validation and rate limiting.
"""
import os
import time
from flask import Blueprint, jsonify, request, current_app
from marshmallow import ValidationError

from core.security import (
    limiter, validate_input, require_api_key,
    DeviceConfigSchema, AnimationControlSchema, ParameterUpdateSchema
)
from core.errors import DeviceError, AnimationError

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


@api_bp.route('/status', methods=['GET'])
@limiter.limit("60 per minute")
def get_status():
    """Get current system status."""
    from app import state
    
    status = {
        'device': {
            'connected': state.device is not None,
            'type': state.config.get('device') if state.device else None,
            'dimensions': state.device.get_dimensions() if state.device else None
        },
        'playback': {
            'is_playing': state.is_playing,
            'current_animation': state.current_animation.filename if state.current_animation else None,
            'parameters': state.params
        },
        'system': {
            'uptime': get_uptime(),
            'version': '1.0.0',
            'environment': current_app.config.get('ENV')
        }
    }
    
    return jsonify(status)


@api_bp.route('/device', methods=['GET'])
@limiter.limit("30 per minute")
@require_api_key
def get_device_info():
    """Get current device information."""
    from app import state
    
    if not state.device:
        return jsonify({'error': 'No device connected'}), 404
    
    info = {
        'type': state.config.get('device'),
        'dimensions': state.device.get_dimensions(),
        'brightness': state.params.get('brightness', 1.0),
        'config': state.config.get('devices', {}).get(state.config.get('device'), {})
    }
    
    return jsonify(info)


@api_bp.route('/device', methods=['PUT'])
@limiter.limit(os.getenv('RATE_LIMIT_DEVICE_SWITCH', '30 per hour'))
@require_api_key
@validate_input(DeviceConfigSchema)
def switch_device():
    """Switch to a different LED device."""
    from app import state, initialize_device
    
    data = request.validated_data
    device_type = data['device_type']
    
    try:
        # Update configuration
        state.config['device'] = device_type
        
        # Apply optional parameters
        if 'brightness' in data:
            state.params['brightness'] = data['brightness']
        if 'gamma' in data:
            state.params['gamma'] = data['gamma']
        if 'fps' in data:
            state.config['render']['max_fps'] = data['fps']
        
        # Initialize new device
        if not initialize_device(device_type, state.config):
            raise DeviceError(f"Failed to initialize {device_type}", device_type=device_type)
        
        return jsonify({
            'success': True,
            'device_type': device_type,
            'message': f'Switched to {device_type} device'
        })
        
    except DeviceError:
        raise
    except Exception as e:
        raise DeviceError(f"Device switch failed: {str(e)}", device_type=device_type)


@api_bp.route('/animation', methods=['POST'])
@limiter.limit("30 per minute")
@require_api_key
@validate_input(AnimationControlSchema)
def control_animation():
    """Control animation playback."""
    from app import state, socketio
    
    data = request.validated_data
    action = data['action']
    
    response = {'action': action, 'success': False}
    
    try:
        if action == 'play':
            if 'filename' in data:
                # Play specific file
                filename = data['filename']
                filepath = os.path.join(state.config.get('server', {}).get('upload_folder', 'uploads'), filename)
                
                if not os.path.exists(filepath):
                    raise AnimationError(f"File not found: {filename}", filename=filename)
                
                # Load animation
                from core.frames import MediaAnimation
                state.current_animation = MediaAnimation(filepath, state.frame_processor)
                
            if state.current_animation:
                state.is_playing = True
                if 'loop' in data:
                    state.current_animation.loop = data['loop']
                if 'speed' in data:
                    state.params['speed'] = data['speed']
                    
                socketio.emit('playing', {'filename': state.current_animation.filename})
                response['success'] = True
                response['filename'] = state.current_animation.filename
            else:
                raise AnimationError("No animation loaded")
                
        elif action == 'pause':
            state.is_playing = False
            socketio.emit('paused')
            response['success'] = True
            
        elif action == 'stop':
            state.is_playing = False
            state.current_animation = None
            if state.device:
                state.device.clear()
            socketio.emit('stopped')
            response['success'] = True
            
        elif action in ['next', 'previous']:
            # TODO: Implement playlist navigation
            raise AnimationError(f"Action '{action}' not yet implemented")
            
    except AnimationError:
        raise
    except Exception as e:
        raise AnimationError(f"Animation control failed: {str(e)}")
    
    return jsonify(response)


@api_bp.route('/parameters', methods=['GET'])
@limiter.limit("60 per minute")
def get_parameters():
    """Get current playback parameters."""
    from app import state
    return jsonify(state.params)


@api_bp.route('/parameters', methods=['PUT'])
@limiter.limit("60 per minute")
@require_api_key
@validate_input(ParameterUpdateSchema)
def update_parameter():
    """Update a playback parameter."""
    from app import state, socketio
    
    data = request.validated_data
    param = data['parameter']
    value = data['value']
    
    # Update parameter
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
    
    # Notify clients
    socketio.emit('parameter_updated', {'parameter': param, 'value': value})
    
    return jsonify({
        'success': True,
        'parameter': param,
        'value': value
    })


@api_bp.route('/files/<filename>', methods=['DELETE'])
@limiter.limit("30 per minute")
@require_api_key
def delete_file(filename):
    """Delete an uploaded file."""
    from app import state
    from core.security import sanitize_path
    
    # Sanitize filename
    filename = sanitize_path(filename)
    if not filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    filepath = os.path.join(state.config.get('server', {}).get('upload_folder', 'uploads'), filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    try:
        os.remove(filepath)
        return jsonify({'success': True, 'message': f'File {filename} deleted'})
    except Exception as e:
        return jsonify({'error': f'Failed to delete file: {str(e)}'}), 500


@api_bp.route('/health', methods=['GET'])
@limiter.exempt
def health_check():
    """Health check endpoint for monitoring."""
    from app import state
    
    health = {
        'status': 'healthy',
        'device_connected': state.device is not None,
        'timestamp': int(time.time())
    }
    
    # Check device health
    if state.device:
        try:
            # Try to get device info
            state.device.get_dimensions()
        except Exception:
            health['status'] = 'degraded'
            health['device_error'] = True
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return jsonify(health), status_code


# Error handlers for API blueprint
@api_bp.errorhandler(ValidationError)
def handle_validation_error(e):
    """Handle marshmallow validation errors."""
    return jsonify({
        'error': 'Validation failed',
        'details': e.messages
    }), 400


@api_bp.errorhandler(404)
def handle_not_found(e):
    """Handle 404 errors in API."""
    return jsonify({
        'error': 'Resource not found',
        'code': 'NOT_FOUND'
    }), 404


# Helper functions
def get_uptime():
    """Get system uptime in seconds."""
    import time
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            return int(uptime_seconds)
    except:
        # Fallback for non-Linux systems
        return int(time.time() - current_app.start_time) if hasattr(current_app, 'start_time') else 0