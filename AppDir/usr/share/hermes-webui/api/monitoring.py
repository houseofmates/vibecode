"""
Hermes Web UI -- Comprehensive monitoring and metrics collection.
Provides performance monitoring, error tracking, and health checks.
"""
import json
import logging
import time
import threading
import traceback
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Performance metrics storage
class MetricsCollector:
    """Thread-safe metrics collection with rolling windows."""
    
    def __init__(self, max_events: int = 10000):
        self.max_events = max_events
        self.lock = threading.RLock()
        
        # Performance metrics
        self.request_times = deque(maxlen=max_events)
        self.error_counts = defaultdict(int)
        self.endpoint_counts = defaultdict(int)
        self.active_connections = 0
        self.peak_connections = 0
        
        # System metrics
        self.memory_usage = deque(maxlen=1000)  # Last 1000 samples
        self.cpu_usage = deque(maxlen=1000)
        
        # Error tracking
        self.recent_errors = deque(maxlen=100)
        self.error_patterns = defaultdict(int)
        
        # Session metrics
        self.session_metrics = {
            'total_sessions': 0,
            'active_sessions': 0,
            'sessions_today': 0,
            'avg_session_duration': 0
        }
        
        # Swarm metrics
        self.swarm_metrics = {
            'total_swarms': 0,
            'active_swarms': 0,
            'total_workers': 0,
            'successful_workers': 0,
            'failed_workers': 0
        }
        
        # Terminal metrics
        self.terminal_metrics = {
            'active_terminals': 0,
            'total_terminals_today': 0,
            'avg_terminal_duration': 0
        }
    
    def record_request(self, endpoint: str, duration: float, status_code: int) -> None:
        """Record API request metrics."""
        with self.lock:
            self.request_times.append(duration)
            self.endpoint_counts[endpoint] += 1
            
            if status_code >= 400:
                self.error_counts[endpoint] += 1
    
    def record_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None) -> None:
        """Record error with context."""
        with self.lock:
            error_entry = {
                'timestamp': time.time(),
                'type': error_type,
                'message': error_message,
                'context': context or {}
            }
            self.recent_errors.append(error_entry)
            self.error_patterns[error_type] += 1
            
            # Log structured error
            logger.error(f"Error recorded: {error_type} - {error_message}", extra=context)
    
    def update_connection_count(self, delta: int) -> None:
        """Update active connection count."""
        with self.lock:
            self.active_connections += delta
            self.peak_connections = max(self.peak_connections, self.active_connections)
    
    def record_memory_usage(self, rss: int, vms: int) -> None:
        """Record memory usage metrics."""
        with self.lock:
            self.memory_usage.append({
                'timestamp': time.time(),
                'rss': rss,
                'vms': vms
            })
    
    def record_cpu_usage(self, percent: float) -> None:
        """Record CPU usage metrics."""
        with self.lock:
            self.cpu_usage.append({
                'timestamp': time.time(),
                'percent': percent
            })
    
    def update_session_metrics(self, metric: str, value: Any) -> None:
        """Update session-related metrics."""
        with self.lock:
            if metric in self.session_metrics:
                self.session_metrics[metric] = value
    
    def update_swarm_metrics(self, metric: str, value: Any) -> None:
        """Update swarm-related metrics."""
        with self.lock:
            if metric in self.swarm_metrics:
                self.swarm_metrics[metric] = value
    
    def update_terminal_metrics(self, metric: str, value: Any) -> None:
        """Update terminal-related metrics."""
        with self.lock:
            if metric in self.terminal_metrics:
                self.terminal_metrics[metric] = value
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        with self.lock:
            # Calculate performance stats
            if self.request_times:
                avg_response_time = sum(self.request_times) / len(self.request_times)
                p95_response_time = sorted(self.request_times)[int(len(self.request_times) * 0.95)]
                p99_response_time = sorted(self.request_times)[int(len(self.request_times) * 0.99)]
            else:
                avg_response_time = p95_response_time = p99_response_time = 0
            
            # Calculate error rate
            total_requests = sum(self.endpoint_counts.values())
            total_errors = sum(self.error_counts.values())
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
            
            # Recent memory usage
            recent_memory = list(self.memory_usage)[-10:] if self.memory_usage else []
            avg_memory = sum(m['rss'] for m in recent_memory) / len(recent_memory) if recent_memory else 0
            
            # Recent CPU usage
            recent_cpu = list(self.cpu_usage)[-10:] if self.cpu_usage else []
            avg_cpu = sum(c['percent'] for c in recent_cpu) / len(recent_cpu) if recent_cpu else 0
            
            return {
                'timestamp': time.time(),
                'performance': {
                    'avg_response_time': round(avg_response_time, 3),
                    'p95_response_time': round(p95_response_time, 3),
                    'p99_response_time': round(p99_response_time, 3),
                    'total_requests': total_requests,
                    'error_rate': round(error_rate, 2),
                    'active_connections': self.active_connections,
                    'peak_connections': self.peak_connections
                },
                'system': {
                    'avg_memory_mb': round(avg_memory / 1024 / 1024, 2),
                    'avg_cpu_percent': round(avg_cpu, 2)
                },
                'sessions': self.session_metrics.copy(),
                'swarms': self.swarm_metrics.copy(),
                'terminals': self.terminal_metrics.copy(),
                'top_errors': dict(sorted(self.error_patterns.items(), key=lambda x: x[1], reverse=True)[:10]),
                'top_endpoints': dict(sorted(self.endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get system health status."""
        with self.lock:
            # Determine health based on various metrics
            health = {
                'status': 'healthy',
                'issues': [],
                'warnings': []
            }
            
            # Check error rate
            total_requests = sum(self.endpoint_counts.values())
            total_errors = sum(self.error_counts.values())
            if total_requests > 0:
                error_rate = total_errors / total_requests * 100
                if error_rate > 10:
                    health['status'] = 'critical'
                    health['issues'].append(f'High error rate: {error_rate:.1f}%')
                elif error_rate > 5:
                    health['status'] = 'degraded'
                    health['warnings'].append(f'Elevated error rate: {error_rate:.1f}%')
            
            # Check response times
            if self.request_times:
                avg_response_time = sum(self.request_times) / len(self.request_times)
                if avg_response_time > 5.0:
                    health['status'] = 'critical'
                    health['issues'].append(f'Slow response times: {avg_response_time:.2f}s')
                elif avg_response_time > 2.0:
                    health['status'] = 'degraded'
                    health['warnings'].append(f'Elevated response times: {avg_response_time:.2f}s')
            
            # Check memory usage
            if self.memory_usage:
                latest_memory = self.memory_usage[-1]['rss']
                memory_mb = latest_memory / 1024 / 1024
                if memory_mb > 2048:  # 2GB
                    health['warnings'].append(f'High memory usage: {memory_mb:.1f}MB')
            
            # Check for recent errors
            recent_time = time.time() - 300  # Last 5 minutes
            recent_error_count = sum(1 for e in self.recent_errors if e['timestamp'] > recent_time)
            if recent_error_count > 20:
                health['status'] = 'critical'
                health['issues'].append(f'High error frequency: {recent_error_count} errors in 5 minutes')
            elif recent_error_count > 10:
                health['status'] = 'degraded'
                health['warnings'].append(f'Elevated error frequency: {recent_error_count} errors in 5 minutes')
            
            return health

# Global metrics collector
METRICS = MetricsCollector()

def record_request_metric(endpoint: str, duration: float, status_code: int) -> None:
    """Convenience function to record request metrics."""
    METRICS.record_request(endpoint, duration, status_code)

def record_error_metric(error_type: str, error_message: str, context: Dict[str, Any] = None) -> None:
    """Convenience function to record error metrics."""
    METRICS.record_error(error_type, error_message, context)

def get_metrics_summary() -> Dict[str, Any]:
    """Get current metrics summary."""
    return METRICS.get_summary()

def get_health_status() -> Dict[str, Any]:
    """Get current health status."""
    return METRICS.get_health_status()

# Background metrics collection
def start_metrics_collection(interval: int = 60) -> None:
    """Start background metrics collection thread."""
    def metrics_loop():
        try:
            import psutil
            import os
        except ImportError:
            logger.warning("psutil not available, system metrics disabled")
            return
        
        while True:
            try:
                # Collect system metrics
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                cpu_percent = process.cpu_percent()
                
                METRICS.record_memory_usage(memory_info.rss, memory_info.vms)
                METRICS.record_cpu_usage(cpu_percent)
                
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                time.sleep(interval)
    
    thread = threading.Thread(target=metrics_loop, daemon=True)
    thread.start()
    logger.info("Metrics collection started")

# Export metrics to file
def export_metrics(filename: str = None) -> str:
    """Export current metrics to JSON file."""
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"metrics_export_{timestamp}.json"
    
    metrics_data = {
        'export_time': datetime.now().isoformat(),
        'summary': METRICS.get_summary(),
        'health': METRICS.get_health_status(),
        'recent_errors': list(METRICS.recent_errors)
    }
    
    try:
        with open(filename, 'w') as f:
            json.dump(metrics_data, f, indent=2, default=str)
        logger.info(f"Metrics exported to {filename}")
        return filename
    except Exception as e:
        logger.error(f"Failed to export metrics: {e}")
        raise