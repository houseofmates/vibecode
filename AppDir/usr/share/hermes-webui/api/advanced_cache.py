"""
Hermes Web UI -- Advanced caching with Redis/Memcached support.
Provides distributed caching, cache warming, and intelligent invalidation.
"""
import json
import logging
import pickle
import time
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class CacheConfig:
    """Cache configuration."""
    backend: str = "memory"  # memory, redis, memcached
    host: str = "localhost"
    port: int = 6379
    password: Optional[str] = None
    db: int = 0
    max_connections: int = 10
    default_ttl: int = 300  # 5 minutes
    key_prefix: str = "vibecode:"
    compression: bool = True
    serialization: str = "pickle"  # pickle, json

class CacheBackend(ABC):
    """Abstract cache backend."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass
    
    @abstractmethod
    def clear(self, pattern: str = None) -> int:
        """Clear cache entries."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass

class MemoryCache(CacheBackend):
    """In-memory cache backend with LRU eviction."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
        self.lock = threading.RLock()
    
    def _evict_if_needed(self) -> None:
        """Evict oldest entries if at capacity."""
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times.items(), key=lambda x: x[1])[0]
            del self.cache[oldest_key]
            del self.access_times[oldest_key]
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            if key in self.cache:
                value, timestamp, ttl = self.cache[key]
                if ttl is None or time.time() - timestamp < ttl:
                    self.access_times[key] = time.time()
                    return value
                else:
                    # Expired
                    del self.cache[key]
                    del self.access_times[key]
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        with self.lock:
            self._evict_if_needed()
            self.cache[key] = (value, time.time(), ttl)
            self.access_times[key] = time.time()
            return True
    
    def delete(self, key: str) -> bool:
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.access_times[key]
                return True
            return False
    
    def exists(self, key: str) -> bool:
        with self.lock:
            return key in self.cache
    
    def clear(self, pattern: str = None) -> int:
        with self.lock:
            if pattern is None:
                count = len(self.cache)
                self.cache.clear()
                self.access_times.clear()
                return count
            else:
                to_remove = [k for k in self.cache.keys() if pattern in k]
                for k in to_remove:
                    del self.cache[k]
                    del self.access_times[k]
                return len(to_remove)
    
    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            return {
                'type': 'memory',
                'size': len(self.cache),
                'max_size': self.max_size,
                'memory_usage': sum(len(str(v[0])) for v in self.cache.values())
            }

class RedisCache(CacheBackend):
    """Redis cache backend."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.redis = None
        self._connect()
    
    def _connect(self) -> None:
        """Connect to Redis."""
        try:
            import redis
            self.redis = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                decode_responses=False,  # Handle binary data
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.redis.ping()
            logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")
        except ImportError:
            logger.error("Redis library not available")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        if self.config.serialization == 'json':
            data = json.dumps(value, default=str).encode('utf-8')
        else:
            data = pickle.dumps(value)
        
        if self.config.compression:
            import zlib
            data = zlib.compress(data)
        
        return data
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        if self.config.compression:
            import zlib
            data = zlib.decompress(data)
        
        if self.config.serialization == 'json':
            return json.loads(data.decode('utf-8'))
        else:
            return pickle.loads(data)
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.config.key_prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        try:
            data = self.redis.get(self._make_key(key))
            if data is None:
                return None
            return self._deserialize(data)
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        try:
            data = self._serialize(value)
            redis_key = self._make_key(key)
            ttl = ttl or self.config.default_ttl
            
            return self.redis.setex(redis_key, ttl, data)
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        try:
            return bool(self.redis.delete(self._make_key(key)))
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        try:
            return bool(self.redis.exists(self._make_key(key)))
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False
    
    def clear(self, pattern: str = None) -> int:
        try:
            if pattern is None:
                pattern = f"{self.config.key_prefix}*"
            else:
                pattern = f"{self.config.key_prefix}{pattern}"
            
            keys = self.redis.keys(pattern)
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis clear error: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, Any]:
        try:
            info = self.redis.info()
            return {
                'type': 'redis',
                'used_memory': info.get('used_memory', 0),
                'used_memory_human': info.get('used_memory_human', '0B'),
                'connected_clients': info.get('connected_clients', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
            }
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {'type': 'redis', 'error': str(e)}

class MemcachedCache(CacheBackend):
    """Memcached cache backend."""
    
    def __init__(self, config: CacheConfig):
        self.config = config
        self.client = None
        self._connect()
    
    def _connect(self) -> None:
        """Connect to Memcached."""
        try:
            import pymemcache
            servers = [f"{self.config.host}:{self.config.port}"]
            self.client = pymemcache.Client(servers, connect_timeout=5, timeout=5)
            logger.info(f"Connected to Memcached at {self.config.host}:{self.config.port}")
        except ImportError:
            logger.error("pymemcache library not available")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Memcached: {e}")
            raise
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        if self.config.serialization == 'json':
            return json.dumps(value, default=str).encode('utf-8')
        else:
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        if self.config.serialization == 'json':
            return json.loads(data.decode('utf-8'))
        else:
            return pickle.loads(data)
    
    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.config.key_prefix}{key}"
    
    def get(self, key: str) -> Optional[Any]:
        try:
            data = self.client.get(self._make_key(key))
            if data is None:
                return None
            return self._deserialize(data)
        except Exception as e:
            logger.error(f"Memcached get error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        try:
            data = self._serialize(value)
            ttl = ttl or self.config.default_ttl
            return self.client.set(self._make_key(key), data, expire=ttl)
        except Exception as e:
            logger.error(f"Memcached set error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        try:
            return self.client.delete(self._make_key(key))
        except Exception as e:
            logger.error(f"Memcached delete error: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        try:
            return self.client.get(self._make_key(key)) is not None
        except Exception as e:
            logger.error(f"Memcached exists error: {e}")
            return False
    
    def clear(self, pattern: str = None) -> int:
        # Memcached doesn't support pattern-based deletion
        # This would require tracking keys separately
        logger.warning("Memcached doesn't support pattern-based clearing")
        return 0
    
    def get_stats(self) -> Dict[str, Any]:
        try:
            stats = self.client.stats()
            server_stats = list(stats.values())[0] if stats else {}
            return {
                'type': 'memcached',
                'bytes': server_stats.get('bytes', 0),
                'curr_connections': server_stats.get('curr_connections', 0),
                'get_hits': server_stats.get('get_hits', 0),
                'get_misses': server_stats.get('get_misses', 0),
                'limit_maxbytes': server_stats.get('limit_maxbytes', 0),
            }
        except Exception as e:
            logger.error(f"Memcached stats error: {e}")
            return {'type': 'memcached', 'error': str(e)}

class AdvancedCache:
    """Advanced cache manager with multiple backends and features."""
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        self.backend = self._create_backend()
        self.local_cache = MemoryCache(max_size=1000)  # L1 cache
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
        }
        self.lock = threading.RLock()
    
    def _create_backend(self) -> CacheBackend:
        """Create cache backend based on configuration."""
        if self.config.backend == "redis":
            return RedisCache(self.config)
        elif self.config.backend == "memcached":
            return MemcachedCache(self.config)
        else:
            return MemoryCache()
    
    def get(self, key: str, use_l1: bool = True) -> Optional[Any]:
        """Get value with L1 cache fallback."""
        with self.lock:
            # Try L1 cache first
            if use_l1:
                value = self.local_cache.get(key)
                if value is not None:
                    self.stats['hits'] += 1
                    return value
            
            # Try backend cache
            value = self.backend.get(key)
            if value is not None:
                self.stats['hits'] += 1
                # Store in L1 cache
                if use_l1:
                    self.local_cache.set(key, value, ttl=60)  # Short TTL for L1
            else:
                self.stats['misses'] += 1
            
            return value
    
    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set value in both caches."""
        with self.lock:
            self.stats['sets'] += 1
            
            # Set in backend
            backend_success = self.backend.set(key, value, ttl)
            
            # Set in L1 cache
            l1_success = self.local_cache.set(key, value, ttl=min(ttl or 300, 60))
            
            return backend_success and l1_success
    
    def delete(self, key: str) -> bool:
        """Delete from both caches."""
        with self.lock:
            self.stats['deletes'] += 1
            backend_success = self.backend.delete(key)
            l1_success = self.local_cache.delete(key)
            return backend_success or l1_success
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        # Check L1 first
        if self.local_cache.exists(key):
            return True
        return self.backend.exists(key)
    
    def clear(self, pattern: str = None) -> int:
        """Clear from both caches."""
        with self.lock:
            backend_count = self.backend.clear(pattern)
            l1_count = self.local_cache.clear(pattern)
            return backend_count + l1_count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        with self.lock:
            hit_rate = (self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) * 100) if (self.stats['hits'] + self.stats['misses']) > 0 else 0
            
            return {
                'operations': self.stats.copy(),
                'hit_rate': round(hit_rate, 2),
                'backend': self.backend.get_stats(),
                'l1_cache': self.local_cache.get_stats(),
            }
    
    def warm_cache(self, data: Dict[str, Any], ttl: int = None) -> None:
        """Warm cache with initial data."""
        logger.info(f"Warming cache with {len(data)} items")
        for key, value in data.items():
            self.set(key, value, ttl)
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern."""
        count = self.clear(pattern)
        logger.info(f"Invalidated {count} cache entries matching '{pattern}'")
        return count

# Decorators for easy caching
def cached(ttl: int = 300, key_prefix: str = "", use_l1: bool = True):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}{func.__name__}:{_generate_key(args, kwargs)}"
            
            # Try to get from cache
            result = ADVANCED_CACHE.get(cache_key, use_l1)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            ADVANCED_CACHE.set(cache_key, result, ttl)
            return result
        
        return wrapper
    return decorator

def cache_invalidate(pattern: str):
    """Decorator to invalidate cache after function execution."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            ADVANCED_CACHE.invalidate_pattern(pattern)
            return result
        return wrapper
    return decorator

def _generate_key(args: tuple, kwargs: dict) -> str:
    """Generate cache key from arguments."""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    key_str = json.dumps(key_data, sort_keys=True, default=str)
    return hashlib.md5(key_str.encode()).hexdigest()

# Global cache instance
ADVANCED_CACHE = None

def get_advanced_cache(config: CacheConfig = None) -> AdvancedCache:
    """Get global advanced cache instance."""
    global ADVANCED_CACHE
    if ADVANCED_CACHE is None:
        ADVANCED_CACHE = AdvancedCache(config)
    return ADVANCED_CACHE

def init_advanced_cache(config: CacheConfig = None) -> None:
    """Initialize advanced cache."""
    global ADVANCED_CACHE
    ADVANCED_CACHE = AdvancedCache(config)
    logger.info(f"Advanced cache initialized with backend: {ADVANCED_CACHE.config.backend}")