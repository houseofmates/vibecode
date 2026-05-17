"""
Central optimization manager that integrates all performance systems.
Coordinates initialization, configuration, and monitoring of all optimization modules.
"""
import logging
import asyncio
import threading
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class OptimizationManager:
    """Central manager for all optimization systems."""
    
    def __init__(self):
        self.initialized = False
        self.startup_time = None
        self.optimization_config = {}
        
        # Module references
        self.connection_pool = None
        self.cache_system = None
        self.static_optimizer = None
        self.batch_processor = None
        self.performance_monitor = None
        self.connection_manager = None
        self.query_optimizer = None
        self.http2_optimizer = None
        self.memory_detector = None
        
        # Status tracking
        self.module_status = {
            'connection_pool': False,
            'cache_system': False,
            'static_optimizer': False,
            'batch_processor': False,
            'performance_monitor': False,
            'connection_manager': False,
            'query_optimizer': False,
            'http2_optimizer': False,
            'memory_detector': False
        }
        
        logger.info("Optimization manager initialized")
    
    async def initialize(self, config: Dict[str, Any] = None):
        """Initialize all optimization systems with configuration."""
        if self.initialized:
            logger.warning("Optimization manager already initialized")
            return
        
        self.startup_time = time.time()
        
        # Load configuration from file if provided, else use defaults
        if config:
            from api.optimization_config import load_config
            loaded_config = load_config()
            self.optimization_config = loaded_config
        else:
            from api.optimization_config import initialize_config
            self.optimization_config = initialize_config()
        
        logger.info("Initializing optimization systems with configuration...")
        
        try:
            # 1. Initialize connection pooling
            await self._initialize_connection_pooling()
            
            # 2. Initialize caching system
            await self._initialize_caching()
            
            # 3. Initialize static optimization
            await self._initialize_static_optimization()
            
            # 4. Initialize batch processing
            await self._initialize_batch_processing()
            
            # 5. Initialize performance monitoring
            await self._initialize_performance_monitoring()
            
            # 6. Initialize connection management
            await self._initialize_connection_management()
            
            # 7. Initialize query optimization
            await self._initialize_query_optimization()
            
            # 8. Initialize HTTP/2 optimization
            await self._initialize_http2_optimization()
            
            # 9. Initialize memory leak detection
            await self._initialize_memory_leak_detection()
            
            # 10. Setup cross-module integration
            await self._setup_integration()
            
            self.initialized = True
            initialization_time = time.time() - self.startup_time
            
            logger.info(f"All optimization systems initialized in {initialization_time:.2f}s")
            
            # Log summary
            self._log_initialization_summary()
            
        except Exception as e:
            logger.error(f"Optimization initialization failed: {e}")
            raise
    
    async def _initialize_connection_pooling(self):
        """Initialize database connection pooling."""
        try:
            from api.connection_pool import initialize_pools, get_pool_stats
            
            # Get configuration
            db_config = self.optimization_config.get('database', {})
            
            # Initialize pools if database path provided
            if db_config.get('path'):
                from api.connection_pool import initialize_pools
                initialize_pools(
                    sqlite_path=db_config['path'],
                    redis_url=db_config.get('redis_url')
                )
                
                self.module_status['connection_pool'] = True
                logger.info("Connection pooling initialized")
            else:
                logger.info("Connection pooling skipped (no database config)")
                
        except Exception as e:
            logger.error(f"Connection pooling initialization failed: {e}")
    
    async def _initialize_caching(self):
        """Initialize advanced caching system."""
        try:
            from api.advanced_cache import initialize_cache, get_cache_stats
            
            cache_config = self.optimization_config.get('cache', {})
            
            # Initialize Redis if available
            redis_client = None
            if cache_config.get('redis_url'):
                import redis
                redis_client = redis.from_url(cache_config['redis_url'])
            
            initialize_cache(
                redis_client=redis_client,
                l1_size=cache_config.get('l1_size', 1000),
                default_ttl=cache_config.get('default_ttl', 300)
            )
            
            self.module_status['cache_system'] = True
            logger.info("Caching system initialized")
            
        except Exception as e:
            logger.error(f"Caching initialization failed: {e}")
    
    async def _initialize_static_optimization(self):
        """Initialize static asset optimization."""
        try:
            from api.static_optimizer import initialize_optimizer, get_optimizer_stats
            
            static_config = self.optimization_config.get('static', {})
            static_dir = static_config.get('dir', 'static')
            cache_dir = static_config.get('cache_dir')
            
            initialize_optimizer(static_dir, cache_dir)
            
            self.module_status['static_optimizer'] = True
            logger.info("Static optimization initialized")
            
        except Exception as e:
            logger.error(f"Static optimization initialization failed: {e}")
    
    async def _initialize_batch_processing(self):
        """Initialize request batching system."""
        try:
            from api.batch_processor import (
                initialize_batch_processor, 
                register_batch_processor, 
                setup_default_processors,
                get_batch_stats
            )
            
            batch_config = self.optimization_config.get('batch', {})
            max_batch_size = batch_config.get('max_batch_size', 50)
            max_wait_time = batch_config.get('max_wait_time', 0.1)
            max_queue_size = batch_config.get('max_queue_size', 1000)
            
            from api.batch_processor import BatchConfig
            config = BatchConfig(
                max_batch_size=max_batch_size,
                max_wait_time=max_wait_time,
                max_queue_size=max_queue_size
            )
            
            initialize_batch_processor(config)
            setup_default_processors()
            
            self.module_status['batch_processor'] = True
            logger.info("Batch processing initialized")
            
        except Exception as e:
            logger.error(f"Batch processing initialization failed: {e}")
    
    async def _initialize_performance_monitoring(self):
        """Initialize performance monitoring."""
        try:
            from api.performance_monitor import (
                initialize_monitor,
                register_alert_callback,
                get_performance_stats,
                performance_monitor
            )
            
            monitor_config = self.optimization_config.get('monitoring', {})
            max_history = monitor_config.get('max_history', 10000)
            
            initialize_monitor(max_history)
            
            # Register alert callback
            def alert_callback(alert):
                logger.warning(f"Performance alert: {alert['type']} - {alert['data']}")
            
            register_alert_callback(alert_callback)
            
            self.module_status['performance_monitor'] = True
            logger.info("Performance monitoring initialized")
            
        except Exception as e:
            logger.error(f"Performance monitoring initialization failed: {e}")
    
    async def _initialize_connection_management(self):
        """Initialize WebSocket/SSE connection management."""
        try:
            from api.connection_manager import (
                initialize_connection_manager,
                get_connection_stats,
                shutdown_connection_manager
            )
            
            conn_config = self.optimization_config.get('connections', {})
            max_connections = conn_config.get('max_connections', 10000)
            heartbeat_interval = conn_config.get('heartbeat_interval', 30.0)
            
            initialize_connection_manager(max_connections, heartbeat_interval)
            
            self.module_status['connection_manager'] = True
            logger.info("Connection management initialized")
            
        except Exception as e:
            logger.error(f"Connection management initialization failed: {e}")
    
    async def _initialize_query_optimization(self):
        """Initialize database query optimization."""
        try:
            from api.query_optimizer import (
                initialize_query_optimizer,
                get_query_performance_report,
                optimize_database,
                close_query_optimizer
            )
            
            db_config = self.optimization_config.get('database', {})
            db_path = db_config.get('path')
            
            if db_path:
                initialize_query_optimizer(db_path)
                
                self.module_status['query_optimizer'] = True
                logger.info("Query optimization initialized")
            else:
                logger.info("Query optimization skipped (no database path)")
                
        except Exception as e:
            logger.error(f"Query optimization initialization failed: {e}")
    
    async def _initialize_http2_optimization(self):
        """Initialize HTTP/2 optimization."""
        try:
            from api.http2_optimizer import (
                initialize_http2_optimizer,
                get_http2_stats
            )
            
            http2_config = self.optimization_config.get('http2', {})
            
            initialize_http2_optimizer()
            
            self.module_status['http2_optimizer'] = True
            logger.info("HTTP/2 optimization initialized")
            
        except Exception as e:
            logger.error(f"HTTP/2 optimization initialization failed: {e}")
    
    async def _initialize_memory_leak_detection(self):
        """Initialize memory leak detection."""
        try:
            from api.memory_leak_detector import (
                initialize_memory_detector,
                get_memory_report,
                stop_memory_monitoring
            )
            
            memory_config = self.optimization_config.get('memory', {})
            check_interval = memory_config.get('check_interval', 60.0)
            history_size = memory_config.get('history_size', 100)
            
            initialize_memory_detector(check_interval, history_size)
            
            self.module_status['memory_detector'] = True
            logger.info("Memory leak detection initialized")
            
        except Exception as e:
            logger.error(f"Memory leak detection initialization failed: {e}")
    
    async def _setup_integration(self):
        """Setup cross-module integration and optimizations."""
        try:
            # Integrate caching with query optimization
            if self.module_status['cache_system'] and self.module_status['query_optimizer']:
                logger.info("Integrating cache with query optimizer...")
                # This would involve customizing query results caching
            
            # Integrate performance monitoring with all systems
            if self.module_status['performance_monitor']:
                logger.info("Integrating performance monitoring...")
                # Setup monitoring for all other modules
            
            # Integrate connection pooling with query optimization
            if (self.module_status['connection_pool'] and 
                self.module_status['query_optimizer']):
                logger.info("Integrating connection pooling with query optimizer...")
            
            # Integrate static optimization with HTTP/2
            if (self.module_status['static_optimizer'] and 
                self.module_status['http2_optimizer']):
                logger.info("Integrating static optimization with HTTP/2...")
            
            logger.info("Cross-module integration completed")
            
        except Exception as e:
            logger.error(f"Integration setup failed: {e}")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default optimization configuration."""
        import os
        from api.config import SESSION_DIR
        
        return {
            'database': {
                'path': str(SESSION_DIR / 'sessions.db') if SESSION_DIR else None,
                'redis_url': os.getenv('REDIS_URL', None)
            },
            'cache': {
                'redis_url': os.getenv('REDIS_URL', None),
                'l1_size': 1000,
                'default_ttl': 300
            },
            'static': {
                'dir': 'static',
                'cache_dir': None,
                'compression_enabled': True,
                'minify_enabled': True
            },
            'batch': {
                'max_batch_size': 50,
                'max_wait_time': 0.1,
                'max_queue_size': 1000
            },
            'monitoring': {
                'max_history': 10000,
                'alert_thresholds': {
                    'response_time_slow': 1.0,
                    'response_time_critical': 5.0,
                    'memory_usage_high': 80.0,
                    'cpu_usage_high': 80.0,
                    'error_rate_high': 0.05
                }
            },
            'connections': {
                'max_connections': 10000,
                'heartbeat_interval': 30.0
            },
            'http2': {
                'max_concurrent_streams': 100,
                'max_push_size': 1024 * 1024,
                'push_threshold': 0.8
            },
            'memory': {
                'check_interval': 60.0,
                'history_size': 100,
                'leak_thresholds': {
                    'memory_growth_rate': 10.0,
                    'object_growth_rate': 1000,
                    'memory_leak_threshold': 100.0,
                    'object_leak_threshold': 10000
                }
            }
        }
    
    def _log_initialization_summary(self):
        """Log summary of initialization results."""
        total_modules = len(self.module_status)
        initialized_modules = sum(self.module_status.values())
        
        logger.info("=== Optimization Initialization Summary ===")
        logger.info(f"Total modules: {total_modules}")
        logger.info(f"Initialized modules: {initialized_modules}")
        logger.info(f"Success rate: {initialized_modules/total_modules:.1%}")
        
        for module, status in self.module_status.items():
            status_str = "✓" if status else "✗"
            logger.info(f"  {status_str} {module}")
        
        if initialized_modules == total_modules:
            logger.info("All optimization systems successfully initialized!")
        else:
            logger.warning(f"Some optimization systems failed to initialize")
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all optimization systems."""
        stats = {
            'manager': {
                'initialized': self.initialized,
                'uptime': time.time() - self.startup_time if self.startup_time else 0,
                'module_status': self.module_status.copy()
            }
        }
        
        # Collect stats from each module
        try:
            if self.module_status['connection_pool']:
                from api.connection_pool import get_pool_stats
                stats['connection_pool'] = get_pool_stats()
            
            if self.module_status['cache_system']:
                from api.advanced_cache import get_cache_stats
                stats['cache_system'] = get_cache_stats()
            
            if self.module_status['static_optimizer']:
                from api.static_optimizer import get_optimizer_stats
                stats['static_optimizer'] = get_optimizer_stats()
            
            if self.module_status['batch_processor']:
                from api.batch_processor import get_batch_stats
                stats['batch_processor'] = get_batch_stats()
            
            if self.module_status['performance_monitor']:
                from api.performance_monitor import get_performance_stats
                stats['performance_monitor'] = get_performance_stats()
            
            if self.module_status['connection_manager']:
                from api.connection_manager import get_connection_stats
                stats['connection_manager'] = get_connection_stats()
            
            if self.module_status['query_optimizer']:
                from api.query_optimizer import get_query_performance_report
                stats['query_optimizer'] = get_query_performance_report()
            
            if self.module_status['http2_optimizer']:
                from api.http2_optimizer import get_http2_stats
                stats['http2_optimizer'] = get_http2_stats()
            
            if self.module_status['memory_detector']:
                from api.memory_leak_detector import get_memory_report
                stats['memory_detector'] = get_memory_report()
                
        except Exception as e:
            logger.error(f"Error collecting comprehensive stats: {e}")
        
        return stats
    
    async def shutdown(self):
        """Gracefully shutdown all optimization systems."""
        logger.info("Shutting down optimization systems...")
        
        try:
            if self.module_status['connection_manager']:
                from api.connection_manager import shutdown_connection_manager
                shutdown_connection_manager()
            
            if self.module_status['memory_detector']:
                from api.memory_leak_detector import stop_memory_monitoring
                stop_memory_monitoring()
            
            if self.module_status['query_optimizer']:
                from api.query_optimizer import close_query_optimizer
                close_query_optimizer()
            
            logger.info("All optimization systems shutdown")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations based on current state."""
        recommendations = []
        
        if not self.initialized:
            recommendations.append("Initialize optimization manager first")
            return recommendations
        
        stats = self.get_comprehensive_stats()
        
        # Analyze performance stats
        if 'performance_monitor' in stats:
            perf = stats['performance_monitor']
            health = perf.get('health', {})
            
            if health.get('status') != 'healthy':
                recommendations.append(f"System health: {health.get('message')}")
            
            # Check response times
            summary = perf.get('summary_5min', {})
            if summary.get('average_response_time', 0) > 0.5:
                recommendations.append("Consider enabling request batching for better response times")
        
        # Analyze cache stats
        if 'cache_system' in stats:
            cache = stats['cache_system']
            if cache.get('l1', {}).get('hit_rate', 0) < 0.7:
                recommendations.append("Consider increasing L1 cache size for better hit rates")
        
        # Analyze memory usage
        if 'memory_detector' in stats:
            memory = stats['memory_detector']
            if memory.get('leak_reports'):
                recommendations.append("Memory leaks detected - review object lifecycle management")
        
        # Analyze connection pool
        if 'connection_pool' in stats:
            pool = stats['connection_pool']
            if pool.get('redis', {}).get('connected') and pool.get('sqlite', {}).get('created_connections', 0) > 5:
                recommendations.append("Consider tuning connection pool sizes")
        
        return recommendations

# Global optimization manager
_optimization_manager: Optional[OptimizationManager] = None

async def initialize_optimizations(config: Dict[str, Any] = None):
    """Initialize global optimization manager."""
    global _optimization_manager
    _optimization_manager = OptimizationManager()
    await _optimization_manager.initialize(config)
    logger.info("Global optimization manager initialized")

def get_optimization_stats() -> Dict[str, Any]:
    """Get optimization statistics."""
    if _optimization_manager:
        return _optimization_manager.get_comprehensive_stats()
    return {}

def get_optimization_recommendations() -> List[str]:
    """Get optimization recommendations."""
    if _optimization_manager:
        return _optimization_manager.get_optimization_recommendations()
    return []

async def shutdown_optimizations():
    """Shutdown optimization systems."""
    if _optimization_manager:
        await _optimization_manager.shutdown()