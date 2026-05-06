"""
Advanced multi-tier caching system with Redis, L1 memory cache, and smart invalidation.
Optimizes frequently accessed data with intelligent cache warming.
"""
import json
import time
import threading
import logging
import hashlib
import pickle
from typing import Any, Optional, Dict, List, Callable
from functools import wraps
from collections import OrderedDict
import redis

logger = logging.getLogger(__name__)

class L1Cache:
    """Thread-safe L1 in-memory cache with LRU eviction."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = OrderedDict()
        self.timestamps = {}
        self.lock = threading.RLock()
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from L1 cache."""
        with self.lock:
            if key not in self.cache:
                self.misses += 1
                return None
            
            # Check TTL
            if time.time() - self.timestamps[key] > self.ttl:
                del self.cache[key]
                del self.timestamps[key]
                self.misses += 1
                return None
            
            # Move to end (LRU)
            value = self.cache.pop(key)
            self.cache[key] = value
            self.hits += 1
            return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in L1 cache."""
        with self.lock:
            # Evict if necessary
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def invalidate(self, key: str):
        """Invalidate specific key."""
        with self.lock:
            self.cache.pop(key, None)
            self.timestamps.pop(key, None)
    
    def clear(self):
        """Clear all cache."""
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.lock:
            total = self.hits + self.misses
            hit_rate = self.hits / total if total > 0 else 0
            return {
                'hits': self.hits,
                'misses': self.misses,
                'hit_rate': hit_rate,
                'size': len(self.cache),
                'max_size': self.max_size
            }

class AdvancedCache:
    """Multi-tier cache with L1 memory + L2 Redis."""
    
    def __init__(self, redis_client=None, l1_size: int = 1000, default_ttl: int = 300):
        self.redis = redis_client
        self.l1 = L1Cache(max_size=l1_size, ttl=default_ttl)
        self.default_ttl = default_ttl
        self.key_prefix = "vibecode:"
        self.lock = threading.RLock()
        
        # Cache warming patterns
        self.warm_patterns = {}
        self.warm_lock = threading.Lock()
    
    def _make_key(self, key: str) -> str:
        """Create namespaced cache key."""
        return f"{self.key_prefix}{key}"
    
    def _hash_key(self, key: str) -> str:
        """Create short hash for long keys."""
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L1 first, then L2)."""
        # Try L1 first
        value = self.l1.get(key)
        if value is not None:
            return value
        
        # Try L2 Redis
        if self.redis:
            try:
                redis_key = self._make_key(self._hash_key(key))
                data = self.redis.get(redis_key)
                if data:
                    value = pickle.loads(data)
                    # Promote to L1
                    self.l1.set(key, value)
                    return value
            except Exception as e:
                logger.warning(f"Redis cache get error: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in both L1 and L2."""
        ttl = ttl or self.default_ttl
        
        # Set in L1
        self.l1.set(key, value, ttl)
        
        # Set in L2 Redis
        if self.redis:
            try:
                redis_key = self._make_key(self._hash_key(key))
                data = pickle.dumps(value)
                self.redis.setex(redis_key, ttl, data)
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
    
    def invalidate(self, key: str):
        """Invalidate from both tiers."""
        self.l1.invalidate(key)
        
        if self.redis:
            try:
                redis_key = self._make_key(self._hash_key(key))
                self.redis.delete(redis_key)
            except Exception as e:
                logger.warning(f"Redis cache invalidate error: {e}")
    
    def invalidate_pattern(self, pattern: str):
        """Invalidate keys matching pattern."""
        # Clear L1 matching keys
        with self.l1.lock:
            keys_to_remove = [k for k in self.l1.cache.keys() if pattern in k]
            for key in keys_to_remove:
                self.l1.invalidate(key)
        
        # Clear L2 Redis matching keys
        if self.redis:
            try:
                redis_pattern = self._make_key(f"*{pattern}*")
                keys = self.redis.keys(redis_pattern)
                if keys:
                    self.redis.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis pattern invalidate error: {e}")
    
    def warm_cache(self, data_loader: Callable[[str], Any], keys: List[str]):
        """Warm cache with frequently accessed data."""
        with self.warm_lock:
            for key in keys:
                if self.get(key) is None:
                    try:
                        value = data_loader(key)
                        if value is not None:
                            self.set(key, value, ttl=self.default_ttl * 2)  # Longer TTL for warmed data
                    except Exception as e:
                        logger.warning(f"Cache warm error for {key}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        stats = {
            'l1': self.l1.get_stats(),
            'redis_connected': bool(self.redis)
        }
        
        if self.redis:
            try:
                info = self.redis.info()
                stats['redis_memory'] = info.get('used_memory_human', 'N/A')
                stats['redis_keys'] = info.get('db0', {}).get('keys', 0)
            except:
                pass
        
        return stats

# Global cache instance
_cache: Optional[AdvancedCache] = None

def initialize_cache(redis_client=None, l1_size: int = 1000, default_ttl: int = 300):
    """Initialize global cache instance."""
    global _cache
    _cache = AdvancedCache(redis_client, l1_size, default_ttl)
    logger.info("Advanced cache initialized")

def cached(ttl: int = 300, key_prefix: str = "", warm_keys: List[str] = None):
    """Decorator for caching function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not _cache:
                return func(*args, **kwargs)
            
            # Create cache key
            cache_key = f"{key_prefix}{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try cache first
            result = _cache.get(cache_key)
            if result is not None:
                return result
            
            # Compute and cache result
            result = func(*args, **kwargs)
            _cache.set(cache_key, result, ttl)
            
            return result
        return wrapper
    return decorator

def invalidate_cache_pattern(pattern: str):
    """Invalidate cache keys matching pattern."""
    if _cache:
        _cache.invalidate_pattern(pattern)

def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    if _cache:
        return _cache.get_stats()
    return {}

def cache_warm_data(data_loader: Callable[[str], Any], keys: List[str]):
    """Warm cache with specified data."""
    if _cache:
        _cache.warm_cache(data_loader, keys)

# Predefined cache keys for common operations
CACHE_KEYS = {
    'sessions_list': 'sessions:list',
    'workspace_files': 'workspace:files:',
    'user_settings': 'user:settings:',
    'api_keys': 'api:keys:',
    'swarm_status': 'swarm:status:',
    'terminal_sessions': 'terminal:sessions:',
    'wiki_memory': 'wiki:memory:',
    'config_data': 'config:data',
    'metrics_data': 'metrics:data'
}

def get_cache_key(key_type: str, identifier: str = "") -> str:
    """Get standardized cache key."""
    base = CACHE_KEYS.get(key_type, key_type)
    return f"{base}{identifier}" if identifier else base