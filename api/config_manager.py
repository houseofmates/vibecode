"""
Hermes Web UI -- Configuration management and validation.
Provides centralized configuration with validation, environment detection, and hot reloading.
"""
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class Environment(Enum):
    """Application environment types."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class DatabaseConfig:
    """Database configuration."""
    path: str = "sessions.db"
    connection_pool_size: int = 10
    query_timeout: int = 30
    enable_wal_mode: bool = True
    cache_size: int = 10000

@dataclass
class SecurityConfig:
    """Security configuration."""
    enable_auth: bool = True
    session_timeout: int = 3600
    max_login_attempts: int = 5
    lockout_duration: int = 900
    csrf_protection: bool = True
    rate_limiting: bool = True
    allowed_origins: List[str] = None
    
    def __post_init__(self):
        if self.allowed_origins is None:
            self.allowed_origins = ["http://localhost:8786", "http://127.0.0.1:8786"]

@dataclass
class PerformanceConfig:
    """Performance configuration."""
    max_concurrent_sessions: int = 100
    session_cache_ttl: int = 600
    workspace_cache_ttl: int = 1800
    model_cache_ttl: int = 3600
    memory_optimization_interval: int = 300
    garbage_collection_interval: int = 600
    enable_compression: bool = True
    compression_threshold: int = 1024

@dataclass
class MonitoringConfig:
    """Monitoring configuration."""
    enable_metrics: bool = True
    metrics_collection_interval: int = 60
    enable_health_checks: bool = True
    health_check_interval: int = 30
    log_level: str = "INFO"
    log_format: str = "json"
    enable_error_tracking: bool = True
    max_log_size: int = 100 * 1024 * 1024  # 100MB
    log_retention_days: int = 30

@dataclass
class FeatureConfig:
    """Feature flags configuration."""
    enable_swarm: bool = True
    enable_terminal: bool = True
    enable_wiki_memory: bool = True
    enable_file_uploads: bool = True
    enable_remote_sessions: bool = False
    enable_api_keys: bool = True
    enable_profiles: bool = True
    max_upload_size: int = 100 * 1024 * 1024  # 100MB
    allowed_file_types: List[str] = None
    
    def __post_init__(self):
        if self.allowed_file_types is None:
            self.allowed_file_types = [
                ".txt", ".md", ".py", ".js", ".html", ".css",
                ".json", ".yaml", ".yml", ".xml", ".csv",
                ".png", ".jpg", ".jpeg", ".gif", ".svg",
                ".pdf", ".doc", ".docx"
            ]

@dataclass
class AppConfig:
    """Main application configuration."""
    environment: Environment = Environment.DEVELOPMENT
    host: str = "0.0.0.0"
    port: int = 8786
    debug: bool = False
    secret_key: str = None
    database: DatabaseConfig = None
    security: SecurityConfig = None
    performance: PerformanceConfig = None
    monitoring: MonitoringConfig = None
    features: FeatureConfig = None
    
    def __post_init__(self):
        if self.database is None:
            self.database = DatabaseConfig()
        if self.security is None:
            self.security = SecurityConfig()
        if self.performance is None:
            self.performance = PerformanceConfig()
        if self.monitoring is None:
            self.monitoring = MonitoringConfig()
        if self.features is None:
            self.features = FeatureConfig()

class ConfigManager:
    """Configuration manager with validation and hot reloading."""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or "config.json"
        self.config_path = Path(self.config_file)
        self.config = AppConfig()
        self.lock = threading.RLock()
        self.watchers = []
        self.last_modified = 0
        
        # Load configuration
        self.load_config()
        
        # Start file watcher if in development
        if self.config.environment == Environment.DEVELOPMENT:
            self.start_file_watcher()
    
    def load_config(self) -> None:
        """Load configuration from file and environment variables."""
        with self.lock:
            # Load from file
            if self.config_path.exists():
                try:
                    with open(self.config_path, 'r') as f:
                        file_config = json.load(f)
                    self._update_config_from_dict(file_config)
                    logger.info(f"Configuration loaded from {self.config_path}")
                except Exception as e:
                    logger.error(f"Error loading config file: {e}")
            
            # Override with environment variables
            self._load_from_environment()
            
            # Validate configuration
            self._validate_config()
            
            # Apply configuration
            self._apply_config()
    
    def _update_config_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """Update configuration from dictionary."""
        # Update main config
        if 'environment' in config_dict:
            self.config.environment = Environment(config_dict['environment'])
        
        if 'host' in config_dict:
            self.config.host = config_dict['host']
        
        if 'port' in config_dict:
            self.config.port = int(config_dict['port'])
        
        if 'debug' in config_dict:
            self.config.debug = bool(config_dict['debug'])
        
        if 'secret_key' in config_dict:
            self.config.secret_key = config_dict['secret_key']
        
        # Update nested configs
        if 'database' in config_dict:
            self._update_dataclass(self.config.database, config_dict['database'])
        
        if 'security' in config_dict:
            self._update_dataclass(self.config.security, config_dict['security'])
        
        if 'performance' in config_dict:
            self._update_dataclass(self.config.performance, config_dict['performance'])
        
        if 'monitoring' in config_dict:
            self._update_dataclass(self.config.monitoring, config_dict['monitoring'])
        
        if 'features' in config_dict:
            self._update_dataclass(self.config.features, config_dict['features'])
    
    def _update_dataclass(self, obj: Any, data: Dict[str, Any]) -> None:
        """Update dataclass fields from dictionary."""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        env_mappings = {
            'HERMES_WEBUI_HOST': ('host', str),
            'HERMES_WEBUI_PORT': ('port', int),
            'HERMES_WEBUI_DEBUG': ('debug', bool),
            'HERMES_WEBUI_SECRET_KEY': ('secret_key', str),
            'HERMES_WEBUI_ENVIRONMENT': ('environment', str),
            'HERMES_WEBUI_ENABLE_AUTH': ('security.enable_auth', bool),
            'HERMES_WEBUI_SESSION_TIMEOUT': ('security.session_timeout', int),
            'HERMES_WEBUI_MAX_UPLOAD_SIZE': ('features.max_upload_size', int),
            'HERMES_WEBUI_LOG_LEVEL': ('monitoring.log_level', str),
            'HERMES_WEBUI_ENABLE_METRICS': ('monitoring.enable_metrics', bool),
            'HERMES_WEBUI_MAX_CONCURRENT_SESSIONS': ('performance.max_concurrent_sessions', int),
        }
        
        for env_var, (config_path, type_func) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    if type_func == bool:
                        value = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        value = type_func(value)
                    
                    self._set_nested_value(config_path, value)
                    logger.debug(f"Loaded {env_var}={value}")
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid value for {env_var}: {e}")
    
    def _set_nested_value(self, path: str, value: Any) -> None:
        """Set nested configuration value using dot notation."""
        parts = path.split('.')
        obj = self.config
        
        for part in parts[:-1]:
            obj = getattr(obj, part)
        
        setattr(obj, parts[-1], value)
    
    def _validate_config(self) -> None:
        """Validate configuration values."""
        errors = []
        
        # Validate port
        if not (1 <= self.config.port <= 65535):
            errors.append("Port must be between 1 and 65535")
        
        # Validate host
        if not self.config.host:
            errors.append("Host cannot be empty")
        
        # Validate security settings
        if self.config.security.enable_auth and not self.config.secret_key:
            errors.append("Secret key is required when authentication is enabled")
        
        if self.config.security.session_timeout <= 0:
            errors.append("Session timeout must be positive")
        
        # Validate performance settings
        if self.config.performance.max_concurrent_sessions <= 0:
            errors.append("Max concurrent sessions must be positive")
        
        if self.config.features.max_upload_size <= 0:
            errors.append("Max upload size must be positive")
        
        # Validate monitoring settings
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.config.monitoring.log_level not in valid_log_levels:
            errors.append(f"Log level must be one of: {valid_log_levels}")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            raise ValueError(error_msg)
    
    def _apply_config(self) -> None:
        """Apply configuration to the system."""
        # Set logging level
        logging.getLogger().setLevel(getattr(logging, self.config.monitoring.log_level))
        
        # Set environment variables for legacy compatibility
        os.environ['HERMES_WEBUI_PORT'] = str(self.config.port)
        os.environ['HERMES_WEBUI_HOST'] = self.config.host
        
        # Notify watchers
        for watcher in self.watchers:
            try:
                watcher(self.config)
            except Exception as e:
                logger.error(f"Error in config watcher: {e}")
    
    def save_config(self) -> None:
        """Save current configuration to file."""
        with self.lock:
            try:
                config_dict = asdict(self.config)
                
                # Convert enum to string
                config_dict['environment'] = self.config.environment.value
                
                with open(self.config_path, 'w') as f:
                    json.dump(config_dict, f, indent=2, default=str)
                
                logger.info(f"Configuration saved to {self.config_path}")
            except Exception as e:
                logger.error(f"Error saving config: {e}")
    
    def get_config(self) -> AppConfig:
        """Get current configuration."""
        with self.lock:
            return self.config
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values."""
        with self.lock:
            self._update_config_from_dict(updates)
            self._validate_config()
            self._apply_config()
            self.save_config()
    
    def add_watcher(self, callback: Callable[[AppConfig], None]) -> None:
        """Add configuration change watcher."""
        self.watchers.append(callback)
    
    def start_file_watcher(self) -> None:
        """Start file watcher for hot reloading."""
        def watcher_loop():
            while True:
                try:
                    if self.config_path.exists():
                        mtime = self.config_path.stat().st_mtime
                        if mtime > self.last_modified:
                            self.last_modified = mtime
                            logger.info("Configuration file changed, reloading...")
                            self.load_config()
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"File watcher error: {e}")
                    time.sleep(5)
        
        thread = threading.Thread(target=watcher_loop, daemon=True)
        thread.start()
        logger.info("Configuration file watcher started")
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information."""
        return {
            'environment': self.config.environment.value,
            'host': self.config.host,
            'port': self.config.port,
            'debug': self.config.debug,
            'config_file': str(self.config_path),
            'python_version': os.sys.version,
            'platform': os.name,
        }
    
    def export_config(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Export configuration for inspection."""
        config_dict = asdict(self.config)
        
        if not include_sensitive:
            # Remove sensitive information
            sensitive_keys = ['secret_key', 'password', 'token', 'key']
            self._remove_sensitive_keys(config_dict, sensitive_keys)
        
        return config_dict
    
    def _remove_sensitive_keys(self, data: Any, sensitive_keys: List[str]) -> None:
        """Recursively remove sensitive keys from dictionary."""
        if isinstance(data, dict):
            for key in list(data.keys()):
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    data[key] = "***REDACTED***"
                elif isinstance(data[key], (dict, list)):
                    self._remove_sensitive_keys(data[key], sensitive_keys)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._remove_sensitive_keys(item, sensitive_keys)

# Global configuration manager instance
CONFIG_MANAGER = None

def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance."""
    global CONFIG_MANAGER
    if CONFIG_MANAGER is None:
        CONFIG_MANAGER = ConfigManager()
    return CONFIG_MANAGER

def get_config() -> AppConfig:
    """Get current application configuration."""
    return get_config_manager().get_config()

def init_config(config_file: str = None) -> None:
    """Initialize configuration manager."""
    global CONFIG_MANAGER
    CONFIG_MANAGER = ConfigManager(config_file)
    logger.info("Configuration manager initialized")