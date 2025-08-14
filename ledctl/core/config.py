"""
Configuration management with environment variable support and validation.
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing required values."""
    pass


class Config:
    """Manages application configuration with environment override support."""
    
    def __init__(self, config_path: Optional[str] = None, env_file: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to YAML config file
            env_file: Path to .env file (defaults to .env in current directory)
        """
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()  # Looks for .env in current directory
            
        # Load YAML config
        self.config_path = config_path or os.getenv('CONFIG_PATH', 'config/device.yml')
        self.yaml_config = self._load_yaml_config()
        
        # Flask configuration
        self.flask = self._get_flask_config()
        
        # Server configuration
        self.server = self._get_server_config()
        
        # Security configuration
        self.security = self._get_security_config()
        
        # Logging configuration
        self.logging = self._get_logging_config()
        
        # Upload configuration
        self.upload = self._get_upload_config()
        
        # Hardware configuration
        self.hardware = self._get_hardware_config()
        
        # Device-specific configuration from YAML
        device_config = self.yaml_config.get('device', 'MOCK')
        # Handle device as string or dict
        if isinstance(device_config, str):
            self.device = {'type': device_config}
        elif isinstance(device_config, dict):
            self.device = device_config
        else:
            self.device = {'type': 'MOCK'}
        self.render = self.yaml_config.get('render', {})
        
    def _load_yaml_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            # First try the specified path
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    return yaml.safe_load(f) or {}
            
            # Fall back to default config
            default_path = self.config_path.replace('.yml', '.default.yml')
            if os.path.exists(default_path):
                logger.info(f"Using default config from {default_path}")
                with open(default_path, 'r') as f:
                    return yaml.safe_load(f) or {}
                    
            logger.warning(f"No config file found at {self.config_path}")
            return {}
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def _get_flask_config(self) -> Dict[str, Any]:
        """Get Flask configuration with environment overrides."""
        secret_key = os.getenv('FLASK_SECRET_KEY')
        if not secret_key:
            raise ConfigurationError(
                "FLASK_SECRET_KEY must be set in environment variables. "
                "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )
            
        return {
            'SECRET_KEY': secret_key,
            'ENV': os.getenv('FLASK_ENV', 'production'),
            'DEBUG': os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
            'TESTING': os.getenv('FLASK_TESTING', 'False').lower() == 'true',
        }
    
    def _get_server_config(self) -> Dict[str, Any]:
        """Get server configuration."""
        yaml_server = self.yaml_config.get('server', {})
        return {
            'host': os.getenv('SERVER_HOST', yaml_server.get('host', '0.0.0.0')),
            'port': int(os.getenv('SERVER_PORT', yaml_server.get('port', 5000))),
        }
    
    def _get_security_config(self) -> Dict[str, Any]:
        """Get security configuration."""
        return {
            'session_cookie_secure': os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true',
            'session_cookie_httponly': os.getenv('SESSION_COOKIE_HTTPONLY', 'True').lower() == 'true',
            'session_cookie_samesite': os.getenv('SESSION_COOKIE_SAMESITE', 'Lax'),
        }
    
    def _get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        yaml_logging = self.yaml_config.get('logging', {})
        return {
            'level': os.getenv('LOG_LEVEL', yaml_logging.get('level', 'INFO')),
            'file': os.getenv('LOG_FILE', yaml_logging.get('file', 'ledctl.log')),
            'max_size': int(os.getenv('LOG_MAX_SIZE', yaml_logging.get('max_size', 10485760))),
            'backup_count': int(os.getenv('LOG_BACKUP_COUNT', yaml_logging.get('backup_count', 5))),
            'format': yaml_logging.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
        }
    
    def _get_upload_config(self) -> Dict[str, Any]:
        """Get upload configuration."""
        yaml_server = self.yaml_config.get('server', {})
        return {
            'max_size': int(os.getenv('MAX_UPLOAD_SIZE', yaml_server.get('upload_max_size', 104857600))),
            'allowed_extensions': os.getenv(
                'ALLOWED_EXTENSIONS',
                yaml_server.get('allowed_extensions', 'gif,png,jpg,jpeg,mp4,avi,mov')
            ).split(','),
            'folder': yaml_server.get('upload_folder', 'uploads'),
        }
    
    def _get_hardware_config(self) -> Dict[str, Any]:
        """Get hardware configuration."""
        return {
            'mock_mode': os.getenv('HARDWARE_MOCK_MODE', 'False').lower() == 'true',
            'gpio_warnings': os.getenv('GPIO_WARNINGS', 'False').lower() == 'true',
        }
    
    def get_device_config(self, device_type: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration for a specific device type."""
        device_type = device_type or self.device.get('type', 'mock')
        return self.yaml_config.get('devices', {}).get(device_type, {})
    
    def validate(self) -> None:
        """Validate configuration and raise errors if invalid."""
        # Check required Flask configuration
        if not self.flask.get('SECRET_KEY'):
            raise ConfigurationError("Flask SECRET_KEY is required")
            
        # Check upload folder exists
        upload_folder = Path(self.upload['folder'])
        if not upload_folder.exists():
            upload_folder.mkdir(parents=True, exist_ok=True)
            
        # Validate device configuration
        if not self.device or not self.device.get('type'):
            raise ConfigurationError("Device type must be specified in configuration")
            
    def __repr__(self) -> str:
        device_type = self.device.get('type', 'unknown') if isinstance(self.device, dict) else 'unknown'
        return f"<Config env={self.flask['ENV']} device={device_type}>"