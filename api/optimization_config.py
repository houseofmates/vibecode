"""
Comprehensive optimization configuration for Vibecode.
Centralizes all optimization settings with validation and defaults.
"""
import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database optimization configuration."""
    path: Optional[str] = None
    redis_url: Optional[str] = None
    connection_pool_size: int = 10
    connection_timeout: float = 30.0
    query_timeout: float = 10.0
    enable_query_optimization: bool = True
    enable_connection_pooling: bool = True

@dataclass
class CacheConfig:
    """Caching system configuration."""
    redis_url: Optional[str] = None
    l1_cache_size: int = 2000
    l2_cache_ttl: int = 600  # 10 minutes
    default_ttl: int = 300  # 5 minutes
    enable_compression: bool = True
    cache_warming_enabled: bool = True
    max_cache_size_mb: int = 100

@dataclass
class StaticConfig:
    """Static asset optimization configuration."""
    static_dir: str = "static"
    cache_dir: Optional[str] = None
    enable_compression: bool = True
    enable_minification: bool = True
    enable_brotli: bool = True
    gzip_level: int = 6
    brotli_level: int = 6
    max_asset_size_mb: int = 10
    preload_critical_assets: bool = True

@dataclass
class BatchConfig:
    """Request batching configuration."""
    max_batch_size: int = 100
    max_wait_time: float = 0.05  # 50ms
    max_queue_size: int = 2000
    enable_batching: bool = True
    batch_timeout: float = 5.0
    retry_attempts: int = 3

@dataclass
class MonitoringConfig:
    """Performance monitoring configuration."""
    enable_monitoring: bool = True
    max_history_size: int = 50000
    alert_thresholds: Dict[str, float] = None
    enable_real_time_alerts: bool = True
    metrics_retention_days: int = 7
    enable_profiling: bool = False
    slow_query_threshold: float = 0.1  # 100ms
    slow_request_threshold: float = 1.0  # 1 second

@dataclass
class ConnectionConfig:
    """Connection management configuration."""
    max_connections: int = 20000
    heartbeat_interval: float = 15.0
    enable_heartbeat: bool = True
    connection_timeout: float = 300.0  # 5 minutes
    enable_multiplexing: bool = True
    max_concurrent_streams: int = 100

@dataclass
class HTTP2Config:
    """HTTP/2 optimization configuration."""
    enable_http2: bool = True
    max_concurrent_streams: int = 100
    enable_server_push: bool = True
    push_threshold: float = 0.8
    max_push_size_mb: int = 1
    enable_header_compression: bool = True
    max_header_table_size: int = 4096

@dataclass
class MemoryConfig:
    """Memory leak detection configuration."""
    enable_monitoring: bool = True
    check_interval: float = 30.0
    history_size: int = 200
    enable_tracemalloc: bool = True
    leak_thresholds: Dict[str, float] = None
    auto_cleanup_threshold_mb: float = 500.0
    gc_optimization_enabled: bool = True

@dataclass
class OptimizationConfig:
    """Main optimization configuration container."""
    database: DatabaseConfig = DatabaseConfig()
    cache: CacheConfig = CacheConfig()
    static: StaticConfig = StaticConfig()
    batch: BatchConfig = BatchConfig()
    monitoring: MonitoringConfig = MonitoringConfig()
    connections: ConnectionConfig = ConnectionConfig()
    http2: HTTP2Config = HTTP2Config()
    memory: MemoryConfig = MemoryConfig()
    
    # Global settings
    enable_all_optimizations: bool = True
    debug_mode: bool = False
    performance_mode: str = "balanced"  # minimal, balanced, maximum
    
    def __post_init__(self):
        """Initialize default values and load from environment."""
        self._load_from_environment()
        self._validate_configuration()
    
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        # Database settings
        self.database.path = os.getenv('VIBECODE_DB_PATH', self.database.path)
        self.database.redis_url = os.getenv('VIBECODE_REDIS_URL', self.database.redis_url)
        self.database.connection_pool_size = int(os.getenv('VIBECODE_DB_POOL_SIZE', str(self.database.connection_pool_size)))
        self.database.enable_query_optimization = os.getenv('VIBECODE_ENABLE_QUERY_OPT', 'true').lower() == 'true'
        
        # Cache settings
        self.cache.redis_url = os.getenv('VIBECODE_CACHE_REDIS_URL', self.cache.redis_url)
        self.cache.l1_cache_size = int(os.getenv('VIBECODE_L1_CACHE_SIZE', str(self.cache.l1_cache_size)))
        self.cache.default_ttl = int(os.getenv('VIBECODE_CACHE_TTL', str(self.cache.default_ttl)))
        self.cache.enable_compression = os.getenv('VIBECODE_ENABLE_COMPRESSION', 'true').lower() == 'true'
        
        # Static settings
        self.static.cache_dir = os.getenv('VIBECODE_STATIC_CACHE_DIR', self.static.cache_dir)
        self.static.enable_compression = os.getenv('VIBECODE_ENABLE_STATIC_COMP', 'true').lower() == 'true'
        self.static.enable_minification = os.getenv('VIBECODE_ENABLE_MINIFICATION', 'true').lower() == 'true'
        
        # Monitoring settings
        self.monitoring.enable_monitoring = os.getenv('VIBECODE_ENABLE_MONITORING', 'true').lower() == 'true'
        self.monitoring.slow_query_threshold = float(os.getenv('VIBECODE_SLOW_QUERY_THRESHOLD', str(self.monitoring.slow_query_threshold)))
        self.monitoring.slow_request_threshold = float(os.getenv('VIBECODE_SLOW_REQUEST_THRESHOLD', str(self.monitoring.slow_request_threshold)))
        
        # Performance mode
        self.performance_mode = os.getenv('VIBECODE_PERFORMANCE_MODE', self.performance_mode)
        self.debug_mode = os.getenv('VIBECODE_DEBUG', 'false').lower() == 'true'
        
        # Initialize alert thresholds with defaults
        if self.monitoring.alert_thresholds is None:
            self.monitoring.alert_thresholds = {
                'response_time_slow': self.monitoring.slow_request_threshold,
                'response_time_critical': self.monitoring.slow_request_threshold * 5,
                'memory_usage_high': 80.0,
                'cpu_usage_high': 80.0,
                'error_rate_high': 0.05
            }
        
        # Initialize memory leak thresholds with defaults
        if self.memory.leak_thresholds is None:
            self.memory.leak_thresholds = {
                'memory_growth_rate': 10.0,
                'object_growth_rate': 1000,
                'memory_leak_threshold': 100.0,
                'object_leak_threshold': 10000
            }
    
    def _validate_configuration(self):
        """Validate configuration values."""
        errors = []
        
        # Validate database config
        if self.database.connection_pool_size < 1 or self.database.connection_pool_size > 100:
            errors.append("Database connection pool size must be between 1 and 100")
        
        if self.database.query_timeout < 1.0 or self.database.query_timeout > 60.0:
            errors.append("Database query timeout must be between 1 and 60 seconds")
        
        # Validate cache config
        if self.cache.l1_cache_size < 100 or self.cache.l1_cache_size > 10000:
            errors.append("L1 cache size must be between 100 and 10000")
        
        if self.cache.default_ttl < 10 or self.cache.default_ttl > 3600:
            errors.append("Cache TTL must be between 10 and 3600 seconds")
        
        # Validate static config
        if self.static.max_asset_size_mb < 1 or self.static.max_asset_size_mb > 100:
            errors.append("Max asset size must be between 1 and 100 MB")
        
        # Validate batch config
        if self.batch.max_batch_size < 1 or self.batch.max_batch_size > 1000:
            errors.append("Batch size must be between 1 and 1000")
        
        if self.batch.max_wait_time < 0.001 or self.batch.max_wait_time > 1.0:
            errors.append("Batch wait time must be between 1ms and 1s")
        
        # Validate monitoring config
        if self.monitoring.max_history_size < 1000 or self.monitoring.max_history_size > 100000:
            errors.append("Monitoring history size must be between 1000 and 100000")
        
        # Validate connection config
        if self.connections.max_connections < 100 or self.connections.max_connections > 100000:
            errors.append("Max connections must be between 100 and 100000")
        
        if self.connections.heartbeat_interval < 1.0 or self.connections.heartbeat_interval > 300.0:
            errors.append("Heartbeat interval must be between 1 and 300 seconds")
        
        # Validate memory config
        if self.memory.check_interval < 1.0 or self.memory.check_interval > 300.0:
            errors.append("Memory check interval must be between 1 and 300 seconds")
        
        if errors:
            error_msg = "Configuration validation errors:\n" + "\n".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration as dictionary."""
        return asdict(self.database)
    
    def get_cache_config(self) -> Dict[str, Any]:
        """Get cache configuration as dictionary."""
        return asdict(self.cache)
    
    def get_static_config(self) -> Dict[str, Any]:
        """Get static configuration as dictionary."""
        return asdict(self.static)
    
    def get_batch_config(self) -> Dict[str, Any]:
        """Get batch configuration as dictionary."""
        return asdict(self.batch)
    
    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration as dictionary."""
        return asdict(self.monitoring)
    
    def get_connection_config(self) -> Dict[str, Any]:
        """Get connection configuration as dictionary."""
        return asdict(self.connections)
    
    def get_http2_config(self) -> Dict[str, Any]:
        """Get HTTP/2 configuration as dictionary."""
        return asdict(self.http2)
    
    def get_memory_config(self) -> Dict[str, Any]:
        """Get memory configuration as dictionary."""
        return asdict(self.memory)
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as dictionary."""
        return {
            'database': self.get_database_config(),
            'cache': self.get_cache_config(),
            'static': self.get_static_config(),
            'batch': self.get_batch_config(),
            'monitoring': self.get_monitoring_config(),
            'connections': self.get_connection_config(),
            'http2': self.get_http2_config(),
            'memory': self.get_memory_config(),
            'global': {
                'enable_all_optimizations': self.enable_all_optimizations,
                'debug_mode': self.debug_mode,
                'performance_mode': self.performance_mode
            }
        }
    
    def get_environment_overrides(self) -> Dict[str, str]:
        """Get environment variable overrides for documentation."""
        return {
            'VIBECODE_DB_PATH': 'Database file path',
            'VIBECODE_REDIS_URL': 'Redis connection URL',
            'VIBECODE_CACHE_REDIS_URL': 'Cache Redis connection URL',
            'VIBECODE_L1_CACHE_SIZE': 'L1 cache size (entries)',
            'VIBECODE_CACHE_TTL': 'Default cache TTL (seconds)',
            'VIBECODE_ENABLE_COMPRESSION': 'Enable compression (true/false)',
            'VIBECODE_ENABLE_STATIC_COMP': 'Enable static compression (true/false)',
            'VIBECODE_ENABLE_MINIFICATION': 'Enable static minification (true/false)',
            'VIBECODE_STATIC_CACHE_DIR': 'Static cache directory path',
            'VIBECODE_ENABLE_MONITORING': 'Enable performance monitoring (true/false)',
            'VIBECODE_SLOW_QUERY_THRESHOLD': 'Slow query threshold (seconds)',
            'VIBECODE_SLOW_REQUEST_THRESHOLD': 'Slow request threshold (seconds)',
            'VIBECODE_PERFORMANCE_MODE': 'Performance mode (minimal/balanced/maximum)',
            'VIBECODE_DEBUG': 'Debug mode (true/false)'
        }
    
    def save_config(self, file_path: str = None):
        """Save configuration to file."""
        if file_path is None:
            file_path = 'optimization_config.json'
        
        config_path = Path(file_path)
        
        try:
            with open(config_path, 'w') as f:
                json.dump(self.get_all_config(), f, indent=2)
            
            logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def load_config(self, file_path: str = None):
        """Load configuration from file."""
        if file_path is None:
            file_path = 'optimization_config.json'
        
        config_path = Path(file_path)
        
        if not config_path.exists():
            logger.warning(f"Configuration file {config_path} not found, using defaults")
            return
        
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            # Update configuration with loaded values
            self._update_from_dict(config_data)
            self._validate_configuration()
            
            logger.info(f"Configuration loaded from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _update_from_dict(self, config_data: Dict[str, Any]):
        """Update configuration from dictionary."""
        if 'database' in config_data:
            for key, value in config_data['database'].items():
                if hasattr(self.database, key):
                    setattr(self.database, key, value)
        
        if 'cache' in config_data:
            for key, value in config_data['cache'].items():
                if hasattr(self.cache, key):
                    setattr(self.cache, key, value)
        
        if 'static' in config_data:
            for key, value in config_data['static'].items():
                if hasattr(self.static, key):
                    setattr(self.static, key, value)
        
        if 'batch' in config_data:
            for key, value in config_data['batch'].items():
                if hasattr(self.batch, key):
                    setattr(self.batch, key, value)
        
        if 'monitoring' in config_data:
            for key, value in config_data['monitoring'].items():
                if hasattr(self.monitoring, key):
                    setattr(self.monitoring, key, value)
        
        if 'connections' in config_data:
            for key, value in config_data['connections'].items():
                if hasattr(self.connections, key):
                    setattr(self.connections, key, value)
        
        if 'http2' in config_data:
            for key, value in config_data['http2'].items():
                if hasattr(self.http2, key):
                    setattr(self.http2, key, value)
        
        if 'memory' in config_data:
            for key, value in config_data['memory'].items():
                if hasattr(self.memory, key):
                    setattr(self.memory, key, value)
        
        if 'global' in config_data:
            for key, value in config_data['global'].items():
                if hasattr(self, key):
                    setattr(self, key, value)

# Global configuration instance
_config: Optional[OptimizationConfig] = None

def initialize_config(config_file: str = None, auto_save: bool = True) -> OptimizationConfig:
    """Initialize global optimization configuration."""
    global _config
    _config = OptimizationConfig()
    
    try:
        if config_file:
            _config.load_config(config_file)
        
        logger.info("Optimization configuration initialized")
        
        if auto_save and not config_file:
            _config.save_config()
        
        return _config
        
    except Exception as e:
        logger.error(f"Failed to initialize optimization configuration: {e}")
        raise

def get_config() -> OptimizationConfig:
    """Get global optimization configuration."""
    global _config
    if _config is None:
        _config = initialize_config()
    return _config

def save_config(file_path: str = None):
    """Save current configuration."""
    global _config
    if _config:
        _config.save_config(file_path)

def get_config_summary() -> Dict[str, Any]:
    """Get configuration summary for display."""
    global _config
    if not _config:
        return {"error": "Configuration not initialized"}
    
    return {
        "database": {
            "connection_pooling": _config.database.enable_connection_pooling,
            "query_optimization": _config.database.enable_query_optimization,
            "pool_size": _config.database.connection_pool_size
        },
        "cache": {
            "l1_cache_size": _config.cache.l1_cache_size,
            "compression_enabled": _config.cache.enable_compression,
            "ttl": _config.cache.default_ttl
        },
        "static": {
            "compression_enabled": _config.static.enable_compression,
            "minification_enabled": _config.static.enable_minification,
            "brotli_enabled": _config.static.enable_brotli
        },
        "monitoring": {
            "enabled": _config.monitoring.enable_monitoring,
            "slow_query_threshold": _config.monitoring.slow_query_threshold,
            "slow_request_threshold": _config.monitoring.slow_request_threshold
        },
        "connections": {
            "max_connections": _config.connections.max_connections,
            "heartbeat_interval": _config.connections.heartbeat_interval,
            "multiplexing_enabled": _config.connections.enable_multiplexing
        },
        "http2": {
            "enabled": _config.http2.enable_http2,
            "server_push_enabled": _config.http2.enable_server_push
        },
        "memory": {
            "monitoring_enabled": _config.memory.enable_monitoring,
            "leak_detection_enabled": _config.memory.enable_monitoring
        },
        "global": {
            "all_optimizations_enabled": _config.enable_all_optimizations,
            "performance_mode": _config.performance_mode,
            "debug_mode": _config.debug_mode
        }
    }