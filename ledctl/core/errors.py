"""
Error handling and custom exceptions for the LED Control System.
"""
import logging
import traceback
from typing import Optional, Dict, Any
from flask import jsonify, render_template, request
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)


class LEDControlError(Exception):
    """Base exception for LED Control System errors."""
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.code = code or 'LED_ERROR'
        self.details = details or {}


class DeviceError(LEDControlError):
    """Hardware device related errors."""
    def __init__(self, message: str, device_type: Optional[str] = None):
        super().__init__(message, code='DEVICE_ERROR', details={'device_type': device_type})


class AnimationError(LEDControlError):
    """Animation processing errors."""
    def __init__(self, message: str, filename: Optional[str] = None):
        super().__init__(message, code='ANIMATION_ERROR', details={'filename': filename})


class ConfigurationError(LEDControlError):
    """Configuration related errors."""
    def __init__(self, message: str, config_key: Optional[str] = None):
        super().__init__(message, code='CONFIG_ERROR', details={'config_key': config_key})


class FileProcessingError(LEDControlError):
    """File upload/processing errors."""
    def __init__(self, message: str, filename: Optional[str] = None, reason: Optional[str] = None):
        super().__init__(message, code='FILE_ERROR', details={'filename': filename, 'reason': reason})


def register_error_handlers(app, socketio):
    """Register error handlers with Flask app."""
    
    @app.errorhandler(LEDControlError)
    def handle_led_error(error):
        """Handle custom LED control errors."""
        logger.error(f"{error.code}: {error.message}", extra=error.details)
        
        response = {
            'error': error.message,
            'code': error.code,
            'details': error.details
        }
        
        # Emit error to websocket clients
        socketio.emit('error', response)
        
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify(response), 400
        
        return render_template('error.html', error=error), 400
    
    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        """Handle HTTP errors."""
        logger.warning(f"HTTP {error.code}: {error.description}")
        
        response = {
            'error': error.description,
            'code': f'HTTP_{error.code}'
        }
        
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify(response), error.code
            
        return render_template('error.html', 
                             error_code=error.code,
                             error_message=error.description), error.code
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handle unexpected errors."""
        logger.exception("Unexpected error occurred")
        
        # Get traceback for logging
        tb = traceback.format_exc()
        logger.error(f"Traceback:\n{tb}")
        
        # Don't expose internal errors in production
        if app.config.get('ENV') == 'production':
            message = "An unexpected error occurred. Please try again later."
            details = {}
        else:
            message = str(error)
            details = {'traceback': tb.split('\n')}
        
        response = {
            'error': message,
            'code': 'INTERNAL_ERROR',
            'details': details
        }
        
        # Emit critical error to websocket clients
        socketio.emit('error', {'error': 'System error occurred', 'code': 'CRITICAL'})
        
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify(response), 500
            
        return render_template('error.html',
                             error_code=500,
                             error_message=message,
                             show_details=(app.config.get('ENV') != 'production'),
                             details=details), 500
    
    @app.errorhandler(413)
    def handle_file_too_large(error):
        """Handle file too large errors."""
        max_size = app.config.get('MAX_CONTENT_LENGTH', 0) / 1024 / 1024  # Convert to MB
        message = f"File too large. Maximum size is {max_size:.0f}MB"
        
        logger.warning(message)
        
        response = {
            'error': message,
            'code': 'FILE_TOO_LARGE',
            'details': {'max_size_mb': max_size}
        }
        
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return jsonify(response), 413
            
        return render_template('error.html',
                             error_code=413,
                             error_message=message), 413


def safe_execute(func, *args, error_message="Operation failed", **kwargs):
    """
    Safely execute a function and handle errors.
    
    Args:
        func: Function to execute
        *args: Arguments for the function
        error_message: Error message to use if function fails
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of function or None if error occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"{error_message}: {str(e)}")
        return None


def emit_error(socketio, error_type: str, message: str, details: Optional[Dict[str, Any]] = None):
    """Emit an error message to all websocket clients."""
    socketio.emit('error', {
        'type': error_type,
        'message': message,
        'details': details or {}
    })