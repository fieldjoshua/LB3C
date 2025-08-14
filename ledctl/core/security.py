"""
API Security: Rate limiting, input validation, and authentication.
"""
import os
import re
import hashlib
import hmac
import time
import logging
from functools import wraps
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta

from flask import request, jsonify, current_app
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from marshmallow import Schema, fields, validate, ValidationError
from redis import Redis

logger = logging.getLogger(__name__)


# Rate limiter storage backend
def get_redis_connection():
    """Get Redis connection for rate limiting, fallback to memory if not available."""
    try:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        r = Redis.from_url(redis_url)
        r.ping()
        logger.info("Using Redis for rate limiting")
        return r
    except Exception as e:
        logger.warning(f"Redis not available, using memory storage: {e}")
        return None


# Initialize rate limiter
redis_conn = get_redis_connection()
if redis_conn:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri=f"redis://localhost:6379",
        swallow_errors=True  # Don't fail if rate limiting backend is down
    )
else:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per hour", "50 per minute"],
        storage_uri="memory://",
        swallow_errors=True  # Don't fail if rate limiting backend is down
    )


# Input validation schemas
class FileUploadSchema(Schema):
    """Validation schema for file uploads."""
    filename = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    size = fields.Int(validate=validate.Range(min=1, max=104857600))  # 100MB max
    
    @staticmethod
    def validate_filename(filename: str) -> bool:
        """Validate filename for security."""
        # Allow only alphanumeric, dash, underscore, and dot
        pattern = r'^[a-zA-Z0-9_\-\.]+$'
        return bool(re.match(pattern, filename))


class DeviceConfigSchema(Schema):
    """Validation schema for device configuration."""
    device_type = fields.Str(
        required=True, 
        validate=validate.OneOf(['HUB75', 'WS2811', 'WLED', 'MOCK'])
    )
    brightness = fields.Float(validate=validate.Range(min=0.0, max=1.0))
    gamma = fields.Float(validate=validate.Range(min=0.1, max=5.0))
    fps = fields.Int(validate=validate.Range(min=1, max=120))


class AnimationControlSchema(Schema):
    """Validation schema for animation controls."""
    action = fields.Str(
        required=True,
        validate=validate.OneOf(['play', 'pause', 'stop', 'next', 'previous'])
    )
    filename = fields.Str(validate=validate.Length(max=255))
    loop = fields.Bool()
    speed = fields.Float(validate=validate.Range(min=0.1, max=10.0))


class ParameterUpdateSchema(Schema):
    """Validation schema for parameter updates."""
    parameter = fields.Str(
        required=True,
        validate=validate.OneOf(['brightness', 'speed', 'gamma', 'rgb_balance'])
    )
    value = fields.Raw(required=True)  # Validated based on parameter type
    
    def validate_value(self, data):
        """Custom validation based on parameter type."""
        param = data.get('parameter')
        value = data.get('value')
        
        if param == 'brightness':
            if not isinstance(value, (int, float)) or value < 0 or value > 1:
                raise ValidationError('Brightness must be between 0 and 1')
        elif param == 'speed':
            if not isinstance(value, (int, float)) or value < 0.1 or value > 10:
                raise ValidationError('Speed must be between 0.1 and 10')
        elif param == 'gamma':
            if not isinstance(value, (int, float)) or value < 0.1 or value > 5:
                raise ValidationError('Gamma must be between 0.1 and 5')
        elif param == 'rgb_balance':
            if not isinstance(value, list) or len(value) != 3:
                raise ValidationError('RGB balance must be a list of 3 values')
            for v in value:
                if not isinstance(v, (int, float)) or v < 0 or v > 2:
                    raise ValidationError('RGB balance values must be between 0 and 2')


# API Key Management
class APIKeyManager:
    """Manages API keys for authentication."""
    
    def __init__(self):
        self.keys = {}
        self._load_keys()
    
    def _load_keys(self):
        """Load API keys from environment or config."""
        # Load from environment variable (comma-separated)
        api_keys = os.getenv('API_KEYS', '').split(',')
        for key in api_keys:
            if key:
                # Store hashed version
                key_hash = hashlib.sha256(key.encode()).hexdigest()
                self.keys[key_hash] = {
                    'created': datetime.now(),
                    'last_used': None,
                    'usage_count': 0
                }
    
    def validate_key(self, key: str) -> bool:
        """Validate an API key."""
        if not key:
            return False
            
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        if key_hash in self.keys:
            # Update usage stats
            self.keys[key_hash]['last_used'] = datetime.now()
            self.keys[key_hash]['usage_count'] += 1
            return True
        return False
    
    def generate_key(self) -> str:
        """Generate a new API key."""
        import secrets
        return secrets.token_urlsafe(32)


# Initialize API key manager
api_key_manager = APIKeyManager()


# Decorators
def validate_input(schema_class: Schema):
    """Decorator to validate request input."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get data from request
            if request.method == 'GET':
                data = request.args.to_dict()
            else:
                data = request.get_json() or {}
            
            # Validate
            schema = schema_class()
            try:
                validated_data = schema.load(data)
                request.validated_data = validated_data
            except ValidationError as e:
                logger.warning(f"Validation error: {e.messages}")
                return jsonify({
                    'error': 'Invalid input',
                    'details': e.messages
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if API key authentication is enabled
        if not os.getenv('API_AUTH_ENABLED', 'False').lower() == 'true':
            return f(*args, **kwargs)
        
        # Get API key from header or query parameter
        api_key = request.headers.get('X-API-Key') or request.args.get('api_key')
        
        if not api_key_manager.validate_key(api_key):
            logger.warning(f"Invalid API key attempt from {request.remote_addr}")
            return jsonify({
                'error': 'Invalid or missing API key',
                'code': 'AUTH_REQUIRED'
            }), 401
        
        return f(*args, **kwargs)
    return decorated_function


def sanitize_path(path: str) -> Optional[str]:
    """Sanitize file paths to prevent directory traversal."""
    if not path:
        return None
    
    # Remove any directory traversal attempts
    path = os.path.basename(path)
    
    # Remove any non-alphanumeric characters except dash, underscore, and dot
    path = re.sub(r'[^a-zA-Z0-9_\-\.]', '', path)
    
    return path if path else None


def validate_file_type(filename: str, allowed_extensions: List[str]) -> bool:
    """Validate file type against allowed extensions."""
    if not filename:
        return False
    
    ext = os.path.splitext(filename)[1].lower()[1:]  # Remove dot
    return ext in allowed_extensions


def setup_security(app, socketio):
    """Setup security features for the Flask app."""
    # Initialize CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": os.getenv('CORS_ORIGINS', '*').split(','),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "X-API-Key"],
            "supports_credentials": True
        }
    })
    
    # Initialize rate limiter
    limiter.init_app(app)
    
    # Add security headers
    @app.after_request
    def add_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Add CSP header for production
        if app.config.get('ENV') == 'production':
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.socket.io; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "img-src 'self' data: blob:; "
                "connect-src 'self' ws: wss:;"
            )
            response.headers['Content-Security-Policy'] = csp
        
        return response
    
    # Request logging
    @app.before_request
    def log_request():
        """Log incoming requests for monitoring."""
        logger.info(f"{request.method} {request.path} from {request.remote_addr}")
        
        # Log request body for debugging (be careful with sensitive data)
        if app.config.get('ENV') == 'development' and request.is_json:
            logger.debug(f"Request body: {request.get_json()}")
    
    # Rate limit error handler
    @app.errorhandler(429)
    def handle_rate_limit(e):
        logger.warning(f"Rate limit exceeded for {request.remote_addr}")
        return jsonify({
            'error': 'Rate limit exceeded',
            'code': 'RATE_LIMIT',
            'retry_after': e.retry_after
        }), 429
    
    logger.info("Security features initialized")


# Utility functions for use in routes
def get_client_ip() -> str:
    """Get the real client IP address."""
    # Check for proxy headers
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr


def is_safe_url(target):
    """Check if a URL is safe for redirection."""
    from urllib.parse import urlparse, urljoin
    
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    
    return (test_url.scheme in ('http', 'https') and 
            ref_url.netloc == test_url.netloc)