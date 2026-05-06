"""
Advanced request batching system for API optimization.
Batches similar requests to reduce database load and improve throughput.
"""
import asyncio
import time
import threading
import logging
from typing import Dict, List, Any, Callable, Optional, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class BatchRequest:
    """Individual request within a batch."""
    request_id: str
    method: str
    params: Dict[str, Any]
    timestamp: float
    future: asyncio.Future
    
@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    max_batch_size: int = 50
    max_wait_time: float = 0.1  # 100ms
    max_queue_size: int = 1000
    cleanup_interval: float = 60.0  # 1 minute

class BatchProcessor:
    """Advanced batch processor with intelligent grouping."""
    
    def __init__(self, config: BatchConfig = None):
        self.config = config or BatchConfig()
        self.queues: Dict[str, deque] = defaultdict(deque)
        self.processors: Dict[str, Callable] = {}
        self.locks: Dict[str, threading.Lock] = defaultdict(threading.Lock)
        self.stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
            'batches_processed': 0,
            'requests_processed': 0,
            'total_wait_time': 0,
            'errors': 0
        })
        
        # Background processing
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("Batch processor initialized")
    
    def register_processor(self, batch_type: str, processor: Callable):
        """Register a processor for a specific batch type."""
        self.processors[batch_type] = processor
        logger.info(f"Registered batch processor for {batch_type}")
    
    async def add_request(self, batch_type: str, method: str, params: Dict[str, Any]) -> Any:
        """Add a request to batch and wait for result."""
        if batch_type not in self.processors:
            raise ValueError(f"No processor registered for {batch_type}")
        
        # Create request and future
        request_id = f"{batch_type}_{int(time.time() * 1000000)}_{id(params)}"
        future = asyncio.Future()
        
        batch_request = BatchRequest(
            request_id=request_id,
            method=method,
            params=params,
            timestamp=time.time(),
            future=future
        )
        
        # Add to queue
        with self.locks[batch_type]:
            queue = self.queues[batch_type]
            
            # Check queue size limit
            if len(queue) >= self.config.max_queue_size:
                future.set_exception(Exception("Batch queue full"))
                return await future
            
            queue.append(batch_request)
            
            # Trigger processing if needed
            if (len(queue) >= self.config.max_batch_size or
                (queue and time.time() - queue[0].timestamp >= self.config.max_wait_time)):
                self._process_batch_async(batch_type)
        
        return await future
    
    def _process_batch_async(self, batch_type: str):
        """Process batch asynchronously."""
        asyncio.create_task(self._process_batch(batch_type))
    
    async def _process_batch(self, batch_type: str):
        """Process a batch of requests."""
        with self.locks[batch_type]:
            queue = self.queues[batch_type]
            if not queue:
                return
            
            # Extract batch
            batch_size = min(len(queue), self.config.max_batch_size)
            batch_requests = [queue.popleft() for _ in range(batch_size)]
            
            if not batch_requests:
                return
        
        try:
            # Calculate wait time
            current_time = time.time()
            total_wait = sum(current_time - req.timestamp for req in batch_requests)
            
            # Process batch
            processor = self.processors[batch_type]
            results = await processor([req.params for req in batch_requests])
            
            # Update stats
            stats = self.stats[batch_type]
            stats['batches_processed'] += 1
            stats['requests_processed'] += len(batch_requests)
            stats['total_wait_time'] += total_wait
            
            # Set results
            for i, request in enumerate(batch_requests):
                if i < len(results):
                    request.future.set_result(results[i])
                else:
                    request.future.set_exception(Exception("Batch processing result mismatch"))
                    
        except Exception as e:
            logger.error(f"Batch processing error for {batch_type}: {e}")
            
            # Set exception for all requests
            for request in batch_requests:
                request.future.set_exception(e)
            
            # Update error stats
            self.stats[batch_type]['errors'] += 1
    
    def _cleanup_worker(self):
        """Background worker for cleanup tasks."""
        while self.running:
            try:
                time.sleep(self.config.cleanup_interval)
                self._cleanup_expired_requests()
            except Exception as e:
                logger.error(f"Batch cleanup error: {e}")
    
    def _cleanup_expired_requests(self):
        """Remove expired requests from queues."""
        current_time = time.time()
        max_age = 30.0  # 30 seconds max wait
        
        for batch_type, queue in self.queues.items():
            with self.locks[batch_type]:
                # Remove expired requests
                expired_requests = []
                remaining_requests = deque()
                
                while queue:
                    request = queue.popleft()
                    if current_time - request.timestamp > max_age:
                        expired_requests.append(request)
                    else:
                        remaining_requests.append(request)
                
                self.queues[batch_type] = remaining_requests
                
                # Fail expired requests
                for request in expired_requests:
                    if not request.future.done():
                        request.future.set_exception(Exception("Request expired"))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get batch processing statistics."""
        total_stats = {
            'total_batches': 0,
            'total_requests': 0,
            'total_errors': 0,
            'average_wait_time': 0.0,
            'queue_sizes': {},
            'per_type': {}
        }
        
        for batch_type, stats in self.stats.items():
            total_stats['total_batches'] += stats['batches_processed']
            total_stats['total_requests'] += stats['requests_processed']
            total_stats['total_errors'] += stats['errors']
            total_stats['per_type'][batch_type] = stats.copy()
            
            # Queue sizes
            with self.locks[batch_type]:
                total_stats['queue_sizes'][batch_type] = len(self.queues[batch_type])
        
        # Calculate average wait time
        if total_stats['total_requests'] > 0:
            total_wait = sum(stats['total_wait_time'] for stats in self.stats.values())
            total_stats['average_wait_time'] = total_wait / total_stats['total_requests']
        
        return total_stats
    
    def shutdown(self):
        """Gracefully shutdown batch processor."""
        self.running = False
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5.0)
        
        # Fail remaining requests
        for batch_type, queue in self.queues.items():
            with self.locks[batch_type]:
                for request in queue:
                    if not request.future.done():
                        request.future.set_exception(Exception("Batch processor shutdown"))

# Global batch processor
_batch_processor: Optional[BatchProcessor] = None

def initialize_batch_processor(config: BatchConfig = None):
    """Initialize global batch processor."""
    global _batch_processor
    _batch_processor = BatchProcessor(config)
    logger.info("Global batch processor initialized")

async def batch_request(batch_type: str, method: str, params: Dict[str, Any]) -> Any:
    """Submit a batched request."""
    if not _batch_processor:
        raise RuntimeError("Batch processor not initialized")
    return await _batch_processor.add_request(batch_type, method, params)

def register_batch_processor(batch_type: str, processor: Callable):
    """Register a batch processor."""
    if _batch_processor:
        _batch_processor.register_processor(batch_type, processor)

def get_batch_stats() -> Dict[str, Any]:
    """Get batch processing statistics."""
    if _batch_processor:
        return _batch_processor.get_stats()
    return {}

def shutdown_batch_processor():
    """Shutdown batch processor."""
    if _batch_processor:
        _batch_processor.shutdown()

# Predefined batch processors
async def session_list_batch_processor(requests: List[Dict[str, Any]]) -> List[Any]:
    """Batch processor for session list requests."""
    try:
        from api.models import get_sessions_list_cached
        # All session list requests return the same data
        result = get_sessions_list_cached()
        return [result for _ in requests]
    except Exception as e:
        logger.error(f"Session list batch error: {e}")
        raise

async def workspace_files_batch_processor(requests: List[Dict[str, Any]]) -> List[Any]:
    """Batch processor for workspace file requests."""
    try:
        from api.workspace import list_workspace_files
        results = []
        
        for request in requests:
            workspace = request.get('workspace')
            path = request.get('path', '.')
            result = list_workspace_files(workspace, path)
            results.append(result)
        
        return results
    except Exception as e:
        logger.error(f"Workspace files batch error: {e}")
        raise

async def api_keys_batch_processor(requests: List[Dict[str, Any]]) -> List[Any]:
    """Batch processor for API keys requests."""
    try:
        from api.api_keys_routes import list_api_keys_cached
        # All API key requests return the same data
        result = list_api_keys_cached()
        return [result for _ in requests]
    except Exception as e:
        logger.error(f"API keys batch error: {e}")
        raise

def setup_default_processors():
    """Setup default batch processors."""
    register_batch_processor('session_list', session_list_batch_processor)
    register_batch_processor('workspace_files', workspace_files_batch_processor)
    register_batch_processor('api_keys', api_keys_batch_processor)
    logger.info("Default batch processors registered")