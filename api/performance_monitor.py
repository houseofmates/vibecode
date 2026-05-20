"""
Comprehensive performance monitoring and metrics collection.
Tracks response times, memory usage, database queries, and system health.
"""
import time
import threading
import psutil
import logging
import json
import traceback
from typing import Dict, List, Any, Optional, Callable
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from functools import wraps
import asyncio

logger = logging.getLogger(__name__)

@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    method: str
    path: str
    status_code: int
    response_time: float
    memory_delta: int
    cpu_delta: float
    timestamp: float
    user_id: Optional[str] = None
    session_id: Optional[str] = None

@dataclass
class SystemMetrics:
    """System-level metrics snapshot."""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    active_connections: int
    process_count: int

@dataclass
class DatabaseMetrics:
    """Database performance metrics."""
    timestamp: float
    query_count: int
    total_query_time: float
    slow_queries: int
    connection_pool_size: int
    cache_hit_rate: float

class PerformanceMonitor:
    """Advanced performance monitoring with real-time metrics."""
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        self.lock = threading.RLock()
        
        # Metrics storage
        self.request_history: deque = deque(maxlen=max_history)
        self.system_history: deque = deque(maxlen=1000)  # Less frequent
        self.database_history: deque = deque(maxlen=1000)
        
        # Aggregated stats
        self.request_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0.0,
            'min_time': float('inf'),
            'max_time': 0.0,
            'error_count': 0,
            'status_codes': defaultdict(int)
        })
        
        # Performance thresholds
        self.thresholds = {
            'response_time_slow': 1.0,  # 1 second
            'response_time_critical': 5.0,  # 5 seconds
            'memory_usage_high': 80.0,  # 80%
            'cpu_usage_high': 80.0,  # 80%
            'error_rate_high': 0.05  # 5%
        }
        
        # Monitoring state
        self.start_time = time.time()
        self.last_system_check = 0
        self.system_check_interval = 30.0  # 30 seconds
        
        # Alert callbacks
        self.alert_callbacks: List[Callable] = []
        
        # Background monitoring
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitoring_worker, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Performance monitor initialized")
    
    def record_request(self, method: str, path: str, status_code: int, 
                    response_time: float, memory_delta: int = 0, 
                    cpu_delta: float = 0.0, user_id: str = None, 
                    session_id: str = None):
        """Record metrics for a request."""
        with self.lock:
            metrics = RequestMetrics(
                method=method,
                path=path,
                status_code=status_code,
                response_time=response_time,
                memory_delta=memory_delta,
                cpu_delta=cpu_delta,
                timestamp=time.time(),
                user_id=user_id,
                session_id=session_id
            )
            
            self.request_history.append(metrics)
            
            # Update aggregated stats
            key = f"{method}:{path}"
            stats = self.request_stats[key]
            stats['count'] += 1
            stats['total_time'] += response_time
            stats['min_time'] = min(stats['min_time'], response_time)
            stats['max_time'] = max(stats['max_time'], response_time)
            stats['status_codes'][status_code] += 1
            
            if status_code >= 400:
                stats['error_count'] += 1
            
            # Check for alerts
            self._check_request_alerts(metrics)
    
    def record_database_metrics(self, query_count: int, total_time: float, 
                           slow_queries: int = 0, connection_pool_size: int = 0,
                           cache_hit_rate: float = 0.0):
        """Record database performance metrics."""
        with self.lock:
            metrics = DatabaseMetrics(
                timestamp=time.time(),
                query_count=query_count,
                total_query_time=total_time,
                slow_queries=slow_queries,
                connection_pool_size=connection_pool_size,
                cache_hit_rate=cache_hit_rate
            )
            
            self.database_history.append(metrics)
    
    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used_mb = memory.used / (1024 * 1024)
            memory_available_mb = memory.available / (1024 * 1024)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = disk.percent
            
            # Process info
            process_count = len(psutil.pids())
            
            # Network connections (estimate)
            try:
                active_connections = len(psutil.net_connections())
            except (psutil.AccessDenied, psutil.NoSuchProcess, OSError):
                active_connections = 0
            
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_used_mb=memory_used_mb,
                memory_available_mb=memory_available_mb,
                disk_usage_percent=disk_usage_percent,
                active_connections=active_connections,
                process_count=process_count
            )
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return None
    
    def _monitoring_worker(self):
        """Background worker for system monitoring."""
        while self.monitoring:
            try:
                current_time = time.time()
                
                # Check if it's time for system metrics
                if current_time - self.last_system_check >= self.system_check_interval:
                    metrics = self.get_current_metrics()
                    if metrics:
                        with self.lock:
                            self.system_history.append(metrics)
                        self.last_system_check = current_time
                        self._check_system_alerts(metrics)
                
                time.sleep(5.0)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Monitoring worker error: {e}")
                time.sleep(10.0)
    
    def _check_request_alerts(self, metrics: RequestMetrics):
        """Check for request-level alerts."""
        # Slow request alert
        if metrics.response_time > self.thresholds['response_time_critical']:
            self._trigger_alert('critical_slow_request', {
                'path': metrics.path,
                'method': metrics.method,
                'response_time': metrics.response_time,
                'status_code': metrics.status_code
            })
        elif metrics.response_time > self.thresholds['response_time_slow']:
            self._trigger_alert('slow_request', {
                'path': metrics.path,
                'method': metrics.method,
                'response_time': metrics.response_time
            })
        
        # Error alert
        if metrics.status_code >= 500:
            self._trigger_alert('server_error', {
                'path': metrics.path,
                'method': metrics.method,
                'status_code': metrics.status_code
            })
    
    def _check_system_alerts(self, metrics: SystemMetrics):
        """Check for system-level alerts."""
        # High memory usage
        if metrics.memory_percent > self.thresholds['memory_usage_high']:
            self._trigger_alert('high_memory_usage', {
                'memory_percent': metrics.memory_percent,
                'memory_used_mb': metrics.memory_used_mb
            })
        
        # High CPU usage
        if metrics.cpu_percent > self.thresholds['cpu_usage_high']:
            self._trigger_alert('high_cpu_usage', {
                'cpu_percent': metrics.cpu_percent
            })
    
    def _trigger_alert(self, alert_type: str, data: Dict[str, Any]):
        """Trigger an alert to all registered callbacks."""
        alert = {
            'type': alert_type,
            'timestamp': time.time(),
            'data': data
        }
        
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")
    
    def register_alert_callback(self, callback: Callable):
        """Register a callback for alerts."""
        self.alert_callbacks.append(callback)
    
    def get_summary_stats(self, time_window: float = 300.0) -> Dict[str, Any]:
        """Get summary statistics for the last time window."""
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        with self.lock:
            # Filter recent requests
            recent_requests = [
                r for r in self.request_history 
                if r.timestamp >= cutoff_time
            ]
            
            if not recent_requests:
                return {
                    'time_window': time_window,
                    'total_requests': 0,
                    'requests_per_second': 0,
                    'average_response_time': 0,
                    'error_rate': 0,
                    'status_distribution': {},
                    'slowest_requests': [],
                    'busiest_endpoints': {}
                }
            
            # Calculate stats
            total_requests = len(recent_requests)
            total_response_time = sum(r.response_time for r in recent_requests)
            average_response_time = total_response_time / total_requests
            requests_per_second = total_requests / time_window
            
            # Error rate
            error_count = sum(1 for r in recent_requests if r.status_code >= 400)
            error_rate = error_count / total_requests
            
            # Status code distribution
            status_distribution = defaultdict(int)
            for r in recent_requests:
                status_distribution[r.status_code] += 1
            
            # Slowest requests
            slowest_requests = sorted(recent_requests, key=lambda r: r.response_time, reverse=True)[:10]
            
            # Busiest endpoints
            endpoint_counts = defaultdict(int)
            endpoint_times = defaultdict(list)
            for r in recent_requests:
                endpoint = f"{r.method} {r.path}"
                endpoint_counts[endpoint] += 1
                endpoint_times[endpoint].append(r.response_time)
            
            busiest_endpoints = {}
            for endpoint, count in sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
                avg_time = sum(endpoint_times[endpoint]) / len(endpoint_times[endpoint])
                busiest_endpoints[endpoint] = {
                    'count': count,
                    'average_response_time': avg_time
                }
            
            return {
                'time_window': time_window,
                'total_requests': total_requests,
                'requests_per_second': requests_per_second,
                'average_response_time': average_response_time,
                'error_rate': error_rate,
                'status_distribution': dict(status_distribution),
                'slowest_requests': [
                    {
                        'method': r.method,
                        'path': r.path,
                        'response_time': r.response_time,
                        'timestamp': r.timestamp
                    } for r in slowest_requests
                ],
                'busiest_endpoints': busiest_endpoints
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall system health status."""
        current_metrics = self.get_current_metrics()
        if not current_metrics:
            return {'status': 'unknown', 'message': 'Unable to get metrics'}
        
        # Determine health status
        issues = []
        
        if current_metrics.memory_percent > self.thresholds['memory_usage_high']:
            issues.append(f"High memory usage: {current_metrics.memory_percent:.1f}%")
        
        if current_metrics.cpu_percent > self.thresholds['cpu_usage_high']:
            issues.append(f"High CPU usage: {current_metrics.cpu_percent:.1f}%")
        
        if current_metrics.disk_usage_percent > 90:
            issues.append(f"High disk usage: {current_metrics.disk_usage_percent:.1f}%")
        
        # Get recent error rate
        with self.lock:
            recent_requests = [
                r for r in self.request_history 
                if time.time() - r.timestamp <= 300  # Last 5 minutes
            ]
            
            if recent_requests:
                error_rate = sum(1 for r in recent_requests if r.status_code >= 400) / len(recent_requests)
                if error_rate > self.thresholds['error_rate_high']:
                    issues.append(f"High error rate: {error_rate:.1%}")
        
        # Determine overall status
        if not issues:
            status = 'healthy'
            message = 'All systems operating normally'
        elif len(issues) <= 2:
            status = 'warning'
            message = '; '.join(issues)
        else:
            status = 'critical'
            message = '; '.join(issues)
        
        return {
            'status': status,
            'message': message,
            'timestamp': current_metrics.timestamp,
            'metrics': asdict(current_metrics),
            'uptime': time.time() - self.start_time
        }
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        with self.lock:
            return {
                'uptime': time.time() - self.start_time,
                'total_requests': len(self.request_history),
                'system_checks': len(self.system_history),
                'database_metrics': len(self.database_history),
                'request_stats': dict(self.request_stats),
                'thresholds': self.thresholds,
                'summary_5min': self.get_summary_stats(300),
                'summary_1hour': self.get_summary_stats(3600),
                'health': self.get_health_status()
            }
    
    def shutdown(self):
        """Gracefully shutdown monitoring."""
        self.monitoring = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5.0)
        logger.info("Performance monitor shutdown")

# Global monitor instance
_monitor: Optional[PerformanceMonitor] = None

def initialize_monitor(max_history: int = 10000):
    """Initialize global performance monitor."""
    global _monitor
    _monitor = PerformanceMonitor(max_history)
    logger.info("Global performance monitor initialized")

def record_request(*args, **kwargs):
    """Record request metrics through global monitor."""
    if _monitor:
        _monitor.record_request(*args, **kwargs)

def record_database_metrics(*args, **kwargs):
    """Record database metrics through global monitor."""
    if _monitor:
        _monitor.record_database_metrics(*args, **kwargs)

def get_performance_stats() -> Dict[str, Any]:
    """Get performance statistics."""
    if _monitor:
        return _monitor.get_detailed_stats()
    return {}

def get_health_status() -> Dict[str, Any]:
    """Get system health status."""
    if _monitor:
        return _monitor.get_health_status()
    return {'status': 'unknown', 'message': 'Monitor not initialized'}

def register_alert_callback(callback: Callable):
    """Register alert callback."""
    if _monitor:
        _monitor.register_alert_callback(callback)

def performance_monitor(middleware_func: Callable = None):
    """Decorator for monitoring request performance."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not _monitor:
                return func(*args, **kwargs)
            
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            try:
                result = func(*args, **kwargs)
                status_code = getattr(result, 'status_code', 200)
                success = True
            except Exception as e:
                status_code = 500
                success = False
                raise
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss
                
                response_time = end_time - start_time
                memory_delta = end_memory - start_memory
                
                # Extract request info if available
                method = 'UNKNOWN'
                path = 'UNKNOWN'
                user_id = None
                session_id = None
                
                if args and hasattr(args[0], 'method'):
                    method = args[0].method
                    path = getattr(args[0], 'path', 'UNKNOWN')
                    user_id = getattr(args[0], 'user_id', None)
                    session_id = getattr(args[0], 'session_id', None)
                
                record_request(
                    method=method,
                    path=path,
                    status_code=status_code,
                    response_time=response_time,
                    memory_delta=memory_delta,
                    user_id=user_id,
                    session_id=session_id
                )
            
            return result
        return wrapper
    return decorator

def shutdown_monitor():
    """Shutdown performance monitor."""
    if _monitor:
        _monitor.shutdown()