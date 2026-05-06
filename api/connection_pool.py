"""
Advanced connection pooling for database and Redis operations.
Optimizes resource usage and reduces connection overhead.
"""
import threading
import time
import queue
import logging
from contextlib import contextmanager
from typing import Dict, Any, Optional
import redis
import sqlite3

logger = logging.getLogger(__name__)

class ConnectionPool:
    """Generic connection pool with thread-safe operations."""
    
    def __init__(self, max_connections: int = 10, connection_factory=None):
        self.max_connections = max_connections
        self.connection_factory = connection_factory
        self.pool = queue.Queue(maxsize=max_connections)
        self.active_connections = 0
        self.lock = threading.Lock()
        self.created_connections = 0
        
        # Pre-warm the pool
        self._warm_pool()
    
    def _warm_pool(self):
        """Pre-create connections to reduce cold start latency."""
        for _ in range(min(3, self.max_connections)):
            try:
                conn = self.connection_factory()
                self.pool.put(conn)
                self.created_connections += 1
            except Exception as e:
                logger.warning(f"Failed to create connection during warm-up: {e}")
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool."""
        conn = None
        try:
            # Try to get from pool first
            try:
                conn = self.pool.get_nowait()
                with self.lock:
                    self.active_connections += 1
            except queue.Empty:
                # Pool empty, create new connection if under limit
                with self.lock:
                    if self.created_connections < self.max_connections:
                        conn = self.connection_factory()
                        self.created_connections += 1
                        with self.lock:
                            self.active_connections += 1
                    else:
                        # Wait for available connection
                        conn = self.pool.get(timeout=5.0)
                        with self.lock:
                            self.active_connections += 1
            
            # Validate connection before returning
            if not self._is_connection_valid(conn):
                conn = self.connection_factory()
            
            yield conn
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            if conn:
                self._close_connection(conn)
            raise
        finally:
            if conn:
                try:
                    # Return connection to pool if valid
                    if self._is_connection_valid(conn):
                        self.pool.put(conn, timeout=1.0)
                    else:
                        self._close_connection(conn)
                except queue.Full:
                    # Pool full, close excess connection
                    self._close_connection(conn)
                finally:
                    with self.lock:
                        self.active_connections -= 1
    
    def _is_connection_valid(self, conn) -> bool:
        """Check if connection is still valid."""
        try:
            if hasattr(conn, 'ping'):
                conn.ping()
            elif hasattr(conn, 'execute'):
                conn.execute('SELECT 1')
            return True
        except:
            return False
    
    def _close_connection(self, conn):
        """Close a connection."""
        try:
            if hasattr(conn, 'close'):
                conn.close()
        except:
            pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pool statistics."""
        with self.lock:
            return {
                'active_connections': self.active_connections,
                'pool_size': self.pool.qsize(),
                'created_connections': self.created_connections,
                'max_connections': self.max_connections
            }

class RedisConnectionPool(ConnectionPool):
    """Redis-specific connection pool with optimized settings."""
    
    def __init__(self, redis_url: str, max_connections: int = 10):
        self.redis_url = redis_url
        
        def create_redis_connection():
            return redis.from_url(
                redis_url,
                max_connections=20,  # Per-connection pool
                retry_on_timeout=True,
                health_check_interval=30,
                socket_keepalive=True,
                socket_keepalive_options={},
                decode_responses=True
            )
        
        super().__init__(max_connections, create_redis_connection)

class SQLiteConnectionPool(ConnectionPool):
    """SQLite-specific connection pool with WAL mode optimization."""
    
    def __init__(self, db_path: str, max_connections: int = 10):
        self.db_path = db_path
        
        def create_sqlite_connection():
            conn = sqlite3.connect(
                db_path,
                check_same_thread=False,
                timeout=30.0,
                isolation_level=None  # Autocommit mode
            )
            # Optimize SQLite settings
            conn.execute('PRAGMA journal_mode=WAL')
            conn.execute('PRAGMA synchronous=NORMAL')
            conn.execute('PRAGMA cache_size=10000')
            conn.execute('PRAGMA temp_store=MEMORY')
            conn.execute('PRAGMA mmap_size=268435456')  # 256MB
            return conn
        
        super().__init__(max_connections, create_sqlite_connection)

# Global connection pools
_redis_pool: Optional[RedisConnectionPool] = None
_sqlite_pool: Optional[SQLiteConnectionPool] = None

def initialize_pools(redis_url: str = None, sqlite_path: str = None):
    """Initialize global connection pools."""
    global _redis_pool, _sqlite_pool
    
    if redis_url:
        _redis_pool = RedisConnectionPool(redis_url)
        logger.info("Redis connection pool initialized")
    
    if sqlite_path:
        _sqlite_pool = SQLiteConnectionPool(sqlite_path)
        logger.info("SQLite connection pool initialized")

@contextmanager
def get_redis_connection():
    """Get a Redis connection from the pool."""
    if not _redis_pool:
        raise RuntimeError("Redis pool not initialized")
    with _redis_pool.get_connection() as conn:
        yield conn

@contextmanager
def get_sqlite_connection():
    """Get a SQLite connection from the pool."""
    if not _sqlite_pool:
        raise RuntimeError("SQLite pool not initialized")
    with _sqlite_pool.get_connection() as conn:
        yield conn

def get_pool_stats() -> Dict[str, Any]:
    """Get statistics for all connection pools."""
    stats = {}
    if _redis_pool:
        stats['redis'] = _redis_pool.get_stats()
    if _sqlite_pool:
        stats['sqlite'] = _sqlite_pool.get_stats()
    return stats

def cleanup_pools():
    """Clean up all connection pools."""
    global _redis_pool, _sqlite_pool
    _redis_pool = None
    _sqlite_pool = None
    logger.info("Connection pools cleaned up")