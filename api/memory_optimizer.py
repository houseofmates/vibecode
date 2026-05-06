"""
Hermes Web UI -- Memory optimization utilities.
Provides automatic memory cleanup, caching strategies, and resource monitoring.
"""
import gc
import logging
import threading
import time
import weakref
from typing import Dict, Any, Optional
from collections import OrderedDict

logger = logging.getLogger(__name__)

# LRU Cache for frequently accessed data
class LRUCache:
    """Thread-safe LRU cache with TTL support."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 300):
        self.max_size = max_size
        self.ttl = ttl  # Time to live in seconds
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.lock = threading.RLock()
        self.last_cleanup = time.time()
    
    def get(self, key: str) -> Optional[Any]:
        with self.lock:
            self._cleanup_expired()
            if key in self.cache:
                # Move to end (most recently used)
                value = self.cache.pop(key)
                self.cache[key] = value
                return value['data']
            return None
    
    def set(self, key: str, value: Any) -> None:
        with self.lock:
            self._cleanup_expired()
            if key in self.cache:
                # Update existing
                self.cache.pop(key)
            elif len(self.cache) >= self.max_size:
                # Remove least recently used
                self.cache.popitem(last=False)
            
            self.cache[key] = {
                'data': value,
                'timestamp': time.time()
            }
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        current_time = time.time()
        if current_time - self.last_cleanup < 60:  # Cleanup every minute
            return
        
        expired_keys = []
        for key, entry in self.cache.items():
            if current_time - entry['timestamp'] > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            self.cache.pop(key, None)
        
        self.last_cleanup = current_time
    
    def clear(self) -> None:
        with self.lock:
            self.cache.clear()
    
    def size(self) -> int:
        with self.lock:
            return len(self.cache)

# Global cache instances
_SESSION_CACHE = LRUCache(max_size=500, ttl=600)  # 10 minutes
_WORKSPACE_CACHE = LRUCache(max_size=100, ttl=1800)  # 30 minutes
_MODEL_CACHE = LRUCache(max_size=50, ttl=3600)  # 1 hour

# Weak references for large objects
_WEAK_REFS: Dict[str, weakref.ref] = {}
_WEAK_REF_LOCK = threading.Lock()

def cache_session(session_id: str, session_data: Dict[str, Any]) -> None:
    """Cache session data with automatic cleanup."""
    _SESSION_CACHE.set(session_id, session_data)

def get_cached_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get cached session data."""
    return _SESSION_CACHE.get(session_id)

def cache_workspace(workspace_path: str, workspace_data: Dict[str, Any]) -> None:
    """Cache workspace metadata."""
    _WORKSPACE_CACHE.set(workspace_path, workspace_data)

def get_cached_workspace(workspace_path: str) -> Optional[Dict[str, Any]]:
    """Get cached workspace metadata."""
    return _WORKSPACE_CACHE.get(workspace_path)

def cache_model_info(model_name: str, model_info: Dict[str, Any]) -> None:
    """Cache model information."""
    _MODEL_CACHE.set(model_name, model_info)

def get_cached_model_info(model_name: str) -> Optional[Dict[str, Any]]:
    """Get cached model information."""
    return _MODEL_CACHE.get(model_name)

def store_weak_ref(key: str, obj: Any) -> None:
    """Store a weak reference to a large object."""
    with _WEAK_REF_LOCK:
        _WEAK_REFS[key] = weakref.ref(obj)

def get_weak_ref(key: str) -> Optional[Any]:
    """Get object from weak reference."""
    with _WEAK_REF_LOCK:
        ref = _WEAK_REFS.get(key)
        if ref:
            return ref()
        return None

def cleanup_weak_refs() -> None:
    """Remove dead weak references."""
    with _WEAK_REF_LOCK:
        dead_keys = []
        for key, ref in _WEAK_REFS.items():
            if ref() is None:
                dead_keys.append(key)
        
        for key in dead_keys:
            del _WEAK_REFS[key]

def force_garbage_collection() -> int:
    """Force garbage collection and return number of objects collected."""
    collected = gc.collect()
    logger.debug(f"Garbage collection completed, collected {collected} objects")
    return collected

def get_memory_stats() -> Dict[str, Any]:
    """Get current memory usage statistics."""
    import psutil
    import os
    
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    
    return {
        'rss': memory_info.rss,  # Resident Set Size
        'vms': memory_info.vms,  # Virtual Memory Size
        'percent': process.memory_percent(),
        'cache_sizes': {
            'sessions': _SESSION_CACHE.size(),
            'workspaces': _WORKSPACE_CACHE.size(),
            'models': _MODEL_CACHE.size()
        },
        'weak_refs': len(_WEAK_REFS)
    }

def optimize_memory_usage() -> None:
    """Run memory optimization routines."""
    # Force garbage collection
    force_garbage_collection()
    
    # Cleanup weak references
    cleanup_weak_refs()
    
    # Log memory stats
    stats = get_memory_stats()
    logger.info(f"Memory optimization completed: {stats}")

# Background memory optimization thread
def start_memory_optimizer(interval: int = 300) -> None:
    """Start background memory optimization thread."""
    def optimizer_loop():
        while True:
            try:
                optimize_memory_usage()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Memory optimizer error: {e}")
                time.sleep(60)  # Wait before retrying
    
    thread = threading.Thread(target=optimizer_loop, daemon=True)
    thread.start()
    logger.info("Memory optimizer started")