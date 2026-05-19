"""
Hermes Web UI -- Main server entry point.
Thin routing shell: imports Handler, delegates to api/routes.py, runs server.
All business logic lives in api/*.
"""
import logging
import os
import socket
import sys
import time
import traceback
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Set up JSON logging for the root logger
try:
    from pythonjsonlogger import JsonFormatter
except ImportError:
    from pythonjsonlogger.json import JsonFormatter

logHandler = logging.StreamHandler(sys.stdout)
formatter = JsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
logHandler.setFormatter(formatter)
# Clear any existing handlers and set our own
logging.root.handlers.clear()
logging.root.addHandler(logHandler)
logging.root.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

from api.auth import check_auth
from api.config import HOST, PORT, STATE_DIR, SESSION_DIR, DEFAULT_WORKSPACE
from api.helpers import j
from api.routes import handle_get, handle_post
from api.startup import auto_install_agent_deps, fix_credential_permissions

# Import optimization modules (temporarily disabled for testing)
# from api.optimization_manager import initialize_optimizations, get_optimization_stats, shutdown_optimizations
# from api.performance_monitor import performance_monitor, record_request, register_alert_callback
# from api.connection_manager import add_connection, remove_connection, broadcast_to_topic
# from api.static_optimizer import get_optimized_asset, get_preload_links
# from api.batch_processor import batch_request
# from api.query_optimizer import execute_optimized_query
# from api.memory_leak_detector import track_object_creation, stop_memory_monitoring


async def _initialize_optimizations():
    """Initialize all optimization systems."""
    try:
        print('[*] Initializing optimization systems...', flush=True)
        
        # Optimization configuration
        optimization_config = {
            'database': {
                'path': str(SESSION_DIR / 'sessions.db') if SESSION_DIR else None,
                'redis_url': None  # Add Redis URL if available
            },
            'cache': {
                'redis_url': None,  # Add Redis URL if available
                'l1_size': 2000,  # Larger L1 cache for better performance
                'default_ttl': 600  # 10 minutes default TTL
            },
            'static': {
                'dir': 'static',
                'cache_dir': None,  # Use default cache directory
                'compression_enabled': True,
                'minify_enabled': True
            },
            'batch': {
                'max_batch_size': 100,  # Larger batches for better throughput
                'max_wait_time': 0.05,  # 50ms batch window
                'max_queue_size': 2000
            },
            'monitoring': {
                'max_history': 50000,  # Larger history for better analytics
                'alert_thresholds': {
                    'response_time_slow': 0.5,  # Stricter thresholds
                    'response_time_critical': 2.0,
                    'memory_usage_high': 75.0,
                    'cpu_usage_high': 75.0,
                    'error_rate_high': 0.02
                }
            },
            'connections': {
                'max_connections': 20000,  # Higher connection limit
                'heartbeat_interval': 15.0  # More frequent heartbeats
            },
            'memory': {
                'check_interval': 30.0,  # More frequent memory checks
                'history_size': 200,
                'leak_thresholds': {
                    'memory_growth_rate': 5.0,  # Stricter leak detection
                    'object_growth_rate': 500,
                    'memory_leak_threshold': 50.0,
                    'object_leak_threshold': 5000
                }
            }
        }
        
        await initialize_optimizations(optimization_config)
        
        # Setup performance alerting
        def performance_alert(alert):
            alert_type = alert.get('type', 'unknown')
            severity = alert.get('data', {}).get('severity', 'info')
            print(f'[ALERT] {alert_type.upper()} [{severity.upper()}]: {alert.get("data", {}).get("description", "No description")}', flush=True)
        
        register_alert_callback(performance_alert)
        
        print('[ok] All optimization systems initialized.', flush=True)
        
    except Exception as e:
        print(f'[!!] Optimization initialization failed: {e}', flush=True)
        import traceback
        traceback.print_exc()

def _warmup_session_cache():
    """Pre-build session index at startup for instant page loads."""
    try:
        from api.models import _rebuild_session_index
        _rebuild_session_index()
        print('[ok] Session index warmed up.', flush=True)
    except Exception as e:
        print(f'[!!] Session index warmup failed: {e}', flush=True)


class OptimizedHTTPServer(ThreadingHTTPServer):
    """High-performance HTTP server with optimization integration."""
    request_queue_size = 256  # Allow more pending connections
    allow_reuse_address = True  # Allow socket reuse
    allow_reuse_port = True  # Allow port reuse
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
=======
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
>>>>>>> Stashed changes
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connections = set()
        self.start_time = time.time()
    
    def process_request(self, handler, *args, **kwargs):
        """Process request with performance monitoring."""
        start_time = time.time()
        
        # Track connection
        client_ip = handler.client_address[0] if hasattr(handler, 'client_address') else 'unknown'
        connection_id = None
        
        try:
            # Add connection to manager
            connection_id = add_connection(
                client_ip=client_ip,
                user_agent=handler.headers.get('User-Agent', 'unknown') if hasattr(handler, 'headers') else 'unknown'
            )
            
            # Process request with monitoring
            with performance_monitor():
                result = super().process_request(handler, *args, **kwargs)
            
            # Record request metrics
            response_time = time.time() - start_time
            status_code = getattr(result, 'status_code', 200)
            
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=status_code,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            
            return result
            
        except Exception as e:
            # Record error metrics
            response_time = time.time() - start_time
            record_request(
                method=getattr(handler, 'command', 'GET'),
                path=getattr(handler, 'path', '/'),
                status_code=500,
                response_time=response_time,
                user_id=getattr(handler, 'user_id', None),
                session_id=getattr(handler, 'session_id', None)
            )
            raise
        
        finally:
            # Clean up connection
            if connection_id:
                remove_connection(connection_id)
    
    def server_bind(self):
        """Override server bind for optimization."""
        # Set socket options for better performance
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        
        # Enable TCP_NODELAY for better latency
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        
        # Set socket buffer sizes
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        super().server_bind()
    
    def get_performance_stats(self):
        """Get server performance statistics."""
        uptime = time.time() - self.start_time
        return {
            'uptime_seconds': uptime,
            'active_connections': len(self.connections),
            'total_connections_processed': len(self.connections),
            'server_type': 'OptimizedHTTPServer'
        }
    
    allow_reuse_address = True  # Avoid Address already in use after restarts
    allow_reuse_port = True  # Same for port reuse

    def handle_error(self, request, client_address):
        """Override to suppress logging for common client disconnect errors."""
        exc_type, exc_value, _ = sys.exc_info()
        
        # Silently ignore common connection errors caused by client disconnects
        if exc_type in (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
            return
        
        # Also handle socket errors that indicate client disconnect
        if exc_type is socket.error:
            # errno 54 is Connection reset by peer on macOS/BSD
            # errno 104 is Connection reset by peer on Linux
            if exc_value.errno in (54, 104, 32):  # ECONNRESET, EPIPE
                return
        
        # For other errors, use default logging
        super().handle_error(request, client_address)


class Handler(BaseHTTPRequestHandler):
    timeout = 0  # disabled — SSE streams must stay open indefinitely; OS handles dead connections
    server_version = 'HermesWebUI/0.50.38'
    def log_message(self, fmt, *args): pass  # suppress default Apache-style log

    def log_request(self, code: str='-', size: str='-') -> None:
        """Structured JSON logs for each request."""
        import json as _json
        duration_ms = round((time.time() - getattr(self, '_req_t0', time.time())) * 1000, 1)
        record = _json.dumps({
            'ts': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'method': self.command or '-',
            'path': self.path or '-',
            'status': int(code) if str(code).isdigit() else code,
            'ms': duration_ms,
        })
        print(f'[webui] {record}', flush=True)

    def do_GET(self) -> None:
        self._req_t0 = time.time()
        try:
            parsed = urlparse(self.path)
            if not check_auth(self, parsed): return
            result = handle_get(self, parsed)
            if result is False:
                return j(self, {'error': 'not found'}, status=404)
        except Exception as e:
            print(f'[webui] ERROR {self.command} {self.path}\n' + traceback.format_exc(), flush=True)
            return j(self, {'error': 'Internal server error'}, status=500)

    def do_OPTIONS(self) -> None:
        """Handle CORS preflight requests."""
        self.send_response(204)
        origin = self.headers.get('Origin', '')
        if origin:
            self.send_header('Access-Control-Allow-Origin', origin)
        else:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Access-Control-Allow-Credentials', 'true')
        self.end_headers()

    def do_POST(self) -> None:
        self._req_t0 = time.time()
        try:
            parsed = urlparse(self.path)
            if not check_auth(self, parsed): return
            # Pre-read POST body to prevent rfile.read() hang
            try:
                _cl = int(self.headers.get('Content-Length', 0))
                self._post_body = self.rfile.read(_cl) if _cl else b'{}'
            except Exception:
                self._post_body = b'{}'
            result = handle_post(self, parsed)
            if result is False:
                return j(self, {'error': 'not found'}, status=404)
        except Exception as e:
            print(f'[webui] ERROR {self.command} {self.path}\n' + traceback.format_exc(), flush=True)
            return j(self, {'error': 'Internal server error'}, status=500)


async def main() -> None:
    from api.config import print_startup_config, verify_hermes_imports, _HERMES_FOUND

    # Initialize optimizations first (temporarily disabled)
    # await _initialize_optimizations()

    print_startup_config()

    # Fix sensitive file permissions before doing anything else
    fix_credential_permissions()

    within_container = False
    # Check for the "/.within_container" file to determine if we're running inside a container; this file is created in the Dockerfile
    try:
        with open('/.within_container', 'r') as f:
            within_container = True
    except FileNotFoundError:
        pass

    if within_container:
        print('[ok] Running within container.', flush=True)

    # Security: warn if binding non-loopback without authentication
    from api.auth import is_auth_enabled
    if HOST not in ('127.0.0.1', '::1', 'localhost') and not is_auth_enabled():
        print(f'[!!] WARNING: Binding to {HOST} with NO PASSWORD SET.', flush=True)
        print(f' Anyone on the network can access your filesystem and agent.', flush=True)
        print(f' Set a password via Settings or HERMES_WEBUI_PASSWORD env var.', flush=True)
        print(f' To suppress: bind to 127.0.0.1 or set a password.', flush=True)
        if within_container:
            print(f' Note: You are running within a container, must bind to 0.0.0.0 to publish the port.', flush=True)
    elif not is_auth_enabled():
        print(f' [tip] No password set. Any process on this machine can read sessions', flush=True)
        print(f' and memory via the local API. Set HERMES_WEBUI_PASSWORD to', flush=True)
        print(f' enable authentication.', flush=True)

    # Remote-client override: if restricted to localhost but no auth is set,
    # override to 0.0.0.0 so AppImage and other remote clients can connect.
    # This preserves explicit localhost binding when auth IS enabled (secure).
    if HOST in ('127.0.0.1', '::1', 'localhost') and not os.getenv('HERMES_WEBUI_FORCE_LOCALHOST'):
        if not is_auth_enabled():
            import api.config
            print('[!!] Overriding localhost binding to 0.0.0.0 — remote clients (AppImage, other machines) cannot reach 127.0.0.1.', flush=True)
            print('[!!] Set HERMES_WEBUI_FORCE_LOCALHOST=1 to keep localhost binding, or set a password.', flush=True)
            api.config.HOST = '0.0.0.0'

    ok, missing, errors = verify_hermes_imports()
    if not ok and _HERMES_FOUND:
        print(f'[!!] Warning: Hermes agent found but missing modules: {missing}', flush=True)
        for mod, err in errors.items():
            print(f'    {mod}: {err}', flush=True)
        print('  Attempting to install missing dependencies from agent requirements.txt...', flush=True)
        auto_install_agent_deps()
        ok, missing, errors = verify_hermes_imports()
        if not ok:
            print(f'[!!] Still missing after install attempt: {missing}', flush=True)
            for mod, err in errors.items():
                print(f'    {mod}: {err}', flush=True)
            print('  Agent features may not work correctly.', flush=True)
        else:
            print('[ok] Agent dependencies installed successfully.', flush=True)

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    DEFAULT_WORKSPACE.mkdir(parents=True, exist_ok=True)

    # Warm up session cache for instant page loads
    _warmup_session_cache()

    # Start the gateway session watcher for real-time SSE updates
    try:
        from api.gateway_watcher import start_watcher
        start_watcher()
    except Exception as e:
        print(f'[!!] WARNING: Gateway watcher failed to start: {e}', flush=True)

    # Start background cron session cleanup (every hour)
    def cleanup_cron_sessions():
        """Background cleanup of cron sessions only"""
        import time
        from api.config import SESSION_DIR, LOCK
        from api.models import Session
        
        while True:
            try:
                time.sleep(3600)  # Run every hour
                
                cleaned = 0
                for p in SESSION_DIR.glob("*.json"):
                    # Only clean sessions that start with cron or _cron
                    if not (p.stem.startswith('cron') or p.stem.startswith('_cron')):
                        continue
                        
                    try:
                        s = Session.load(p.stem)
                        if not s:
                            continue
                            
                        # Always delete cron/_cron sessions regardless of content
                        with LOCK:
                            SESSIONS.pop(p.stem, None)
                        p.unlink(missing_ok=True)
                        cleaned += 1
                    except Exception:
                        # Skip problematic files
                        continue
                        
                # Rebuild index to remove cleaned sessions
                try:
                    from api.models import _rebuild_session_index
                    _rebuild_session_index()
                except Exception:
                    pass
                    
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} cron/_cron sessions")
                    print(f'[ok] Cleaned up {cleaned} cron/_cron sessions', flush=True)
                    
            except Exception as e:
                logger.error(f"Error in cron session cleanup: {e}")
                # Continue the loop even if there's an error
                continue

    # Start cleanup thread as daemon so it doesn't block shutdown
    cleanup_thread = threading.Thread(target=cleanup_cron_sessions, daemon=True)
    cleanup_thread.start()
    logger.info("Started cron session cleanup background thread")

<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    # ── Multiplex SSE queue cleanup ─────────────────────────────────────────
    def cleanup_multiplex_queues():
        """Remove empty multiplex queues that haven't been active for 2 minutes."""
        while True:
            time.sleep(60)
            try:
                from api.config import MULTIPLEX_QUEUES, MULTIPLEX_LOCK
                now = time.time()
                with MULTIPLEX_LOCK:
                    stale = []
                    for cid, q in list(MULTIPLEX_QUEUES.items()):
                        last_activity = max(
                            getattr(q, '_last_get', 0),
                            getattr(q, '_last_put', 0),
                        )
                        if q.empty() and now - last_activity > 120:
                            stale.append(cid)
                    for cid in stale:
                        del MULTIPLEX_QUEUES[cid]
                        print(f'[webui] Cleaned up stale multiplex queue for client_id={cid}', flush=True)
            except Exception as e:
                logger.debug(f"Multiplex queue cleanup error: {e}")

    mq_cleanup_thread = threading.Thread(target=cleanup_multiplex_queues, daemon=True)
    mq_cleanup_thread.start()
    logger.info("Started multiplex queue cleanup background thread")

    httpd = QuietHTTPServer((HOST, PORT), Handler)
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes
=======
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
>>>>>>> Stashed changes

    # ── TLS/HTTPS setup (optional) ─────────────────────────────────────────
    from api.config import TLS_ENABLED, TLS_CERT, TLS_KEY
    scheme = 'https' if TLS_ENABLED else 'http'
    if TLS_ENABLED:
        try:
            import ssl
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.minimum_version = ssl.TLSVersion.TLSv1_2
            ctx.load_cert_chain(TLS_CERT, TLS_KEY)
            httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
            print(f'  TLS enabled: cert={TLS_CERT}, key={TLS_KEY}', flush=True)
        except Exception as e:
            print(f'[!!] WARNING: TLS setup failed ({e}), falling back to HTTP', flush=True)
            scheme = 'http'

    print(f'  Hermes Web UI listening on {scheme}://{HOST}:{PORT}', flush=True)
    if HOST == '127.0.0.1' or within_container:
        print(f'  Remote access: ssh -N -L {PORT}:127.0.0.1:{PORT} <user>@<your-server>', flush=True)
        print(f'               Then open: {scheme}://localhost:{PORT}', flush=True)
    print('', flush=True)
    try:
        httpd.serve_forever()
    finally:
        # Shutdown optimization systems
        try:
            import asyncio
            asyncio.create_task(shutdown_optimizations())
        except Exception:
            logger.debug("Failed to shutdown optimization systems")
        
        # Stop the gateway watcher on shutdown
        try:
            from api.gateway_watcher import stop_watcher
            stop_watcher()
        except Exception:
            logger.debug("Failed to stop gateway watcher during shutdown")

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
