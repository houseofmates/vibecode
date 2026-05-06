"""
HTTP/2 optimization with server push, multiplexing, and header compression.
Implements modern HTTP/2 features for better performance.
"""
import asyncio
import time
import logging
import json
import hashlib
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict, deque
from dataclasses import dataclass
import base64

logger = logging.getLogger(__name__)

@dataclass
class PushPromise:
    """HTTP/2 server push promise."""
    url: str
    method: str = 'GET'
    headers: Dict[str, str] = None
    priority: int = 0
    weight: int = 16
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

@dataclass
class HTTP2Stream:
    """HTTP/2 stream information."""
    stream_id: int
    parent_stream_id: Optional[int] = None
    weight: int = 16
    dependency: Optional[int] = None
    exclusive: bool = False
    state: str = 'idle'  # idle, reserved, open, closed
    window_size: int = 65535
    headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}

class HTTP2Optimizer:
    """Advanced HTTP/2 optimization with intelligent push strategies."""
    
    def __init__(self):
        # Stream management
        self.streams: Dict[int, HTTP2Stream] = {}
        self.next_stream_id = 1
        self.stream_lock = asyncio.Lock()
        
        # Push cache and strategies
        self.push_cache: Dict[str, bytes] = {}
        self.push_promises: List[PushPromise] = []
        self.push_stats = defaultdict(lambda: {
            'pushed': 0,
            'hit': 0,
            'miss': 0,
            'bytes_saved': 0
        })
        
        # Header compression (HPACK)
        self.header_table: List[Dict[str, str]] = []
        self.max_header_table_size = 4096
        self.dynamic_table_size = 0
        
        # Priority scheduling
        self.priority_queue = deque()
        self.active_streams: Set[int] = set()
        
        # Configuration
        self.max_concurrent_streams = 100
        self.max_push_size = 1024 * 1024  # 1MB
        self.push_threshold = 0.8  # Push if confidence > 80%
        
        # Learning patterns
        self.request_patterns: Dict[str, int] = defaultdict(int)
        self.correlation_patterns: Dict[str, List[str]] = defaultdict(list)
        
        logger.info("HTTP/2 optimizer initialized")
    
    async def create_stream(self, headers: Dict[str, str], weight: int = 16, 
                         dependency: Optional[int] = None, exclusive: bool = False) -> int:
        """Create new HTTP/2 stream."""
        async with self.stream_lock:
            if len(self.streams) >= self.max_concurrent_streams:
                raise Exception("Maximum streams exceeded")
            
            stream_id = self.next_stream_id
            self.next_stream_id += 2  # Client-initiated streams are odd
            
            # Compress headers using HPACK
            compressed_headers = self._compress_headers(headers)
            
            stream = HTTP2Stream(
                stream_id=stream_id,
                weight=weight,
                dependency=dependency,
                exclusive=exclusive,
                state='idle',
                headers=compressed_headers
            )
            
            self.streams[stream_id] = stream
            logger.debug(f"Created HTTP/2 stream {stream_id}")
            
            return stream_id
    
    async def send_headers(self, stream_id: int, headers: Dict[str, str], 
                         end_stream: bool = False):
        """Send headers on HTTP/2 stream."""
        async with self.stream_lock:
            stream = self.streams.get(stream_id)
            if not stream or stream.state == 'closed':
                return
            
            # Compress headers
            compressed_headers = self._compress_headers(headers)
            
            # Update stream state
            if stream.state == 'idle':
                stream.state = 'open'
                self.active_streams.add(stream_id)
            
            if end_stream:
                stream.state = 'closed'
                self.active_streams.discard(stream_id)
            
            # In real implementation, this would send HEADERS frame
            logger.debug(f"Sent headers on stream {stream_id}, end_stream={end_stream}")
    
    async def send_data(self, stream_id: int, data: bytes, 
                      end_stream: bool = False):
        """Send data on HTTP/2 stream."""
        async with self.stream_lock:
            stream = self.streams.get(stream_id)
            if not stream or stream.state != 'open':
                return
            
            # Check flow control
            if len(data) > stream.window_size:
                # Would need to handle flow control
                data = data[:stream.window_size]
                stream.window_size -= len(data)
            
            if end_stream:
                stream.state = 'closed'
                self.active_streams.discard(stream_id)
            
            # In real implementation, this would send DATA frame
            logger.debug(f"Sent {len(data)} bytes on stream {stream_id}")
    
    def _compress_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Compress headers using HPACK-like algorithm."""
        compressed = {}
        
        for name, value in headers.items():
            # Check if header is in static table
            static_match = self._find_in_static_table(name, value)
            if static_match:
                compressed[name] = static_match
                continue
            
            # Check dynamic table
            dynamic_match = self._find_in_dynamic_table(name, value)
            if dynamic_match:
                compressed[name] = dynamic_match
                continue
            
            # Add to dynamic table
            if self.dynamic_table_size < self.max_header_table_size:
                self.header_table.append({'name': name, 'value': value})
                self.dynamic_table_size += len(name) + len(value) + 32
                
                # Use index reference
                index = len(self.header_table) - 1
                compressed[name] = str(index)
            else:
                # Evict oldest entry and add new
                if self.header_table:
                    evicted = self.header_table.pop(0)
                    self.dynamic_table_size -= len(evicted['name']) + len(evicted['value']) + 32
                
                self.header_table.append({'name': name, 'value': value})
                compressed[name] = str(len(self.header_table) - 1)
        
        return compressed
    
    def _find_in_static_table(self, name: str, value: str) -> Optional[str]:
        """Find header in static table (simplified)."""
        # Common static headers
        static_headers = {
            ':method': ['GET', 'POST', 'PUT', 'DELETE'],
            ':path': None,  # Dynamic
            ':scheme': ['http', 'https'],
            ':status': ['200', '201', '301', '404', '500'],
            'content-type': ['text/html', 'application/json', 'text/css', 'application/javascript'],
            'content-length': None,
            'cache-control': ['public', 'private', 'no-cache', 'max-age'],
            'etag': None
        }
        
        if name in static_headers:
            values = static_headers[name]
            if values and value in values:
                return str(values.index(value))
        
        return None
    
    def _find_in_dynamic_table(self, name: str, value: str) -> Optional[str]:
        """Find header in dynamic table."""
        for i, entry in enumerate(self.header_table):
            if entry['name'] == name and entry['value'] == value:
                return str(i)
        return None
    
    def analyze_request_patterns(self, url: str, referer: str = None):
        """Analyze request patterns for intelligent push."""
        # Extract resource type
        resource_type = self._get_resource_type(url)
        
        # Update pattern counts
        self.request_patterns[url] += 1
        self.request_patterns[resource_type] += 1
        
        # Analyze correlations
        if referer:
            self.correlation_patterns[referer].append(url)
    
    def _get_resource_type(self, url: str) -> str:
        """Extract resource type from URL."""
        if url.endswith('.css'):
            return 'css'
        elif url.endswith('.js'):
            return 'javascript'
        elif url.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
            return 'image'
        elif url.endswith(('.woff', '.woff2', '.ttf', '.eot')):
            return 'font'
        elif '/api/' in url:
            return 'api'
        else:
            return 'document'
    
    def should_push_resource(self, url: str, referer: str = None) -> bool:
        """Determine if resource should be pushed."""
        # Don't push API calls
        if self._get_resource_type(url) == 'api':
            return False
        
        # Check request frequency
        request_count = self.request_patterns[url]
        if request_count < 2:  # Need at least 2 requests to consider pushing
            return False
        
        # Check correlation strength
        if referer:
            correlation_count = self.correlation_patterns[referer].count(url)
            total_referer_requests = len(self.correlation_patterns[referer])
            if total_referer_requests > 0:
                correlation_rate = correlation_count / total_referer_requests
                if correlation_rate < self.push_threshold:
                    return False
        
        # Check resource size and type
        if url in self.push_cache:
            resource_size = len(self.push_cache[url])
            if resource_size > self.max_push_size:
                return False
        
        return True
    
    def create_push_promise(self, url: str, referer: str = None, 
                          priority: int = 0) -> Optional[PushPromise]:
        """Create push promise for resource."""
        if not self.should_push_resource(url, referer):
            return None
        
        # Determine priority based on resource type and request patterns
        resource_type = self._get_resource_type(url)
        request_count = self.request_patterns[url]
        
        # Priority calculation
        if resource_type == 'css':
            priority = 1  # Highest priority for CSS
            weight = 32
        elif resource_type == 'javascript':
            priority = 2  # High priority for JS
            weight = 24
        elif resource_type == 'font':
            priority = 3  # Medium-high for fonts
            weight = 20
        elif resource_type == 'image':
            priority = 4  # Medium for images
            weight = 16
        else:
            priority = 5  # Lower for documents
            weight = 8
        
        # Adjust based on request frequency
        if request_count > 5:
            priority = max(1, priority - 1)
            weight = min(32, weight + 8)
        
        promise = PushPromise(
            url=url,
            priority=priority,
            weight=weight
        )
        
        self.push_promises.append(promise)
        return promise
    
    def get_push_promises(self, referer: str = None, limit: int = 5) -> List[PushPromise]:
        """Get prioritized push promises for a request."""
        # Filter and sort promises
        valid_promises = []
        
        for promise in self.push_promises:
            if self.should_push_resource(promise.url, referer):
                valid_promises.append(promise)
        
        # Sort by priority (lower number = higher priority)
        valid_promises.sort(key=lambda p: (p.priority, -p.weight))
        
        # Clear used promises
        used_promises = valid_promises[:limit]
        for promise in used_promises:
            self.push_promises.remove(promise)
        
        return used_promises
    
    def cache_push_resource(self, url: str, content: bytes):
        """Cache resource for pushing."""
        if len(content) <= self.max_push_size:
            self.push_cache[url] = content
            
            # Update stats
            resource_type = self._get_resource_type(url)
            self.push_stats[resource_type]['pushed'] += 1
    
    def get_push_resource(self, url: str) -> Optional[bytes]:
        """Get cached push resource."""
        content = self.push_cache.get(url)
        if content is not None:
            # Update stats
            resource_type = self._get_resource_type(url)
            self.push_stats[resource_type]['hit'] += 1
        else:
            # Update miss stats
            resource_type = self._get_resource_type(url)
            self.push_stats[resource_type]['miss'] += 1
        
        return content
    
    def get_multiplexed_streams(self) -> Dict[int, HTTP2Stream]:
        """Get all active streams for multiplexing."""
        return {sid: stream for sid, stream in self.streams.items() 
                if stream.state == 'open'}
    
    def update_stream_priority(self, stream_id: int, weight: int = None, 
                           dependency: Optional[int] = None):
        """Update stream priority for multiplexing."""
        async with self.stream_lock:
            stream = self.streams.get(stream_id)
            if stream and stream.state == 'open':
                if weight is not None:
                    stream.weight = weight
                if dependency is not None:
                    stream.dependency = dependency
                
                # Rebuild priority queue
                self._rebuild_priority_queue()
    
    def _rebuild_priority_queue(self):
        """Rebuild priority queue based on stream dependencies."""
        # Simple priority implementation - in real HTTP/2 this is more complex
        open_streams = [s for s in self.streams.values() if s.state == 'open']
        
        # Sort by weight and dependency
        open_streams.sort(key=lambda s: (s.dependency or 0, -s.weight))
        
        self.priority_queue = deque(open_streams)
    
    def get_next_frame(self) -> Optional[Dict[str, Any]]:
        """Get next frame to send based on priority."""
        if not self.priority_queue:
            return None
        
        # Get highest priority stream
        stream = self.priority_queue[0]
        
        # In real implementation, this would determine frame type
        # For now, return stream info
        return {
            'stream_id': stream.stream_id,
            'weight': stream.weight,
            'dependency': stream.dependency,
            'state': stream.state
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get HTTP/2 performance statistics."""
        total_pushes = sum(stats['pushed'] for stats in self.push_stats.values())
        total_hits = sum(stats['hit'] for stats in self.push_stats.values())
        total_misses = sum(stats['miss'] for stats in self.push_stats.values())
        
        hit_rate = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0
        
        return {
            'active_streams': len(self.active_streams),
            'total_streams': len(self.streams),
            'header_table_size': len(self.header_table),
            'dynamic_table_size': self.dynamic_table_size,
            'push_cache_size': len(self.push_cache),
            'total_pushes': total_pushes,
            'push_hit_rate': hit_rate,
            'push_stats_by_type': dict(self.push_stats),
            'request_patterns': dict(self.request_patterns),
            'correlation_patterns': {
                url: len(correlations) 
                for url, correlations in self.correlation_patterns.items()
            }
        }
    
    def clear_cache(self):
        """Clear push cache and reset patterns."""
        self.push_cache.clear()
        self.push_promises.clear()
        self.request_patterns.clear()
        self.correlation_patterns.clear()
        logger.info("HTTP/2 cache cleared")

# Global HTTP/2 optimizer
_http2_optimizer: Optional[HTTP2Optimizer] = None

def initialize_http2_optimizer():
    """Initialize global HTTP/2 optimizer."""
    global _http2_optimizer
    _http2_optimizer = HTTP2Optimizer()
    logger.info("Global HTTP/2 optimizer initialized")

def create_http2_stream(headers: Dict[str, str], weight: int = 16, 
                       dependency: Optional[int] = None) -> int:
    """Create HTTP/2 stream through global optimizer."""
    if not _http2_optimizer:
        raise RuntimeError("HTTP/2 optimizer not initialized")
    return await _http2_optimizer.create_stream(headers, weight, dependency)

def get_push_promises(referer: str = None, limit: int = 5) -> List[PushPromise]:
    """Get push promises through global optimizer."""
    if _http2_optimizer:
        return _http2_optimizer.get_push_promises(referer, limit)
    return []

def cache_push_resource(url: str, content: bytes):
    """Cache push resource through global optimizer."""
    if _http2_optimizer:
        _http2_optimizer.cache_push_resource(url, content)

def get_http2_stats() -> Dict[str, Any]:
    """Get HTTP/2 performance statistics."""
    if _http2_optimizer:
        return _http2_optimizer.get_performance_stats()
    return {}