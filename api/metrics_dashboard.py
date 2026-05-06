"""
Hermes Web UI -- Metrics dashboard API.
Provides real-time metrics and performance data for monitoring.
"""
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from api.monitoring import METRICS, get_metrics_summary, get_health_status
from api.memory_optimizer import get_memory_stats, optimize_memory_usage
from api.config_manager import get_config

logger = logging.getLogger(__name__)

def get_dashboard_data() -> Dict[str, Any]:
    """Get comprehensive dashboard data."""
    try:
        # Get current metrics
        metrics_summary = get_metrics_summary()
        health_status = get_health_status()
        memory_stats = get_memory_stats()
        config = get_config()
        
        # Calculate uptime
        uptime = time.time() - getattr(METRICS, 'start_time', time.time())
        
        # Get system info
        system_info = get_system_info()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'uptime_seconds': uptime,
            'uptime_formatted': format_uptime(uptime),
            'health': health_status,
            'metrics': metrics_summary,
            'memory': memory_stats,
            'system': system_info,
            'config': {
                'environment': config.environment.value,
                'version': getattr(config, 'version', 'unknown'),
                'features': {
                    'swarm': config.features.enable_swarm,
                    'terminal': config.features.enable_terminal,
                    'wiki_memory': config.features.enable_wiki_memory,
                    'file_uploads': config.features.enable_file_uploads,
                }
            },
            'alerts': get_active_alerts(metrics_summary, health_status),
        }
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        return {
            'error': str(e),
            'timestamp': datetime.now().isoformat(),
        }

def get_system_info() -> Dict[str, Any]:
    """Get system information."""
    try:
        import psutil
        import platform
        
        # CPU info
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        
        # Memory info
        memory = psutil.virtual_memory()
        
        # Disk info
        disk = psutil.disk_usage('/')
        
        # Network info
        network = psutil.net_io_counters()
        
        # System info
        system = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'architecture': platform.architecture()[0],
        }
        
        return {
            'cpu': {
                'count': cpu_count,
                'percent': cpu_percent,
                'frequency_mhz': cpu_freq.current if cpu_freq else None,
            },
            'memory': {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'percent': memory.percent,
                'used_gb': round(memory.used / (1024**3), 2),
            },
            'disk': {
                'total_gb': round(disk.total / (1024**3), 2),
                'free_gb': round(disk.free / (1024**3), 2),
                'percent': round((disk.used / disk.total) * 100, 2),
                'used_gb': round(disk.used / (1024**3), 2),
            },
            'network': {
                'bytes_sent': network.bytes_sent,
                'bytes_recv': network.bytes_recv,
                'packets_sent': network.packets_sent,
                'packets_recv': network.packets_recv,
            } if network else {},
            'system': system,
        }
    except ImportError:
        logger.warning("psutil not available, system info limited")
        return {'error': 'psutil not available'}
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return {'error': str(e)}

def get_active_alerts(metrics: Dict[str, Any], health: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate active alerts based on metrics and health."""
    alerts = []
    
    # Health-based alerts
    if health['status'] == 'critical':
        alerts.append({
            'severity': 'critical',
            'title': 'System Critical',
            'message': '; '.join(health['issues']),
            'timestamp': datetime.now().isoformat(),
        })
    elif health['status'] == 'degraded':
        alerts.append({
            'severity': 'warning',
            'title': 'System Degraded',
            'message': '; '.join(health['warnings']),
            'timestamp': datetime.now().isoformat(),
        })
    
    # Performance-based alerts
    perf = metrics.get('performance', {})
    if perf.get('avg_response_time', 0) > 2.0:
        alerts.append({
            'severity': 'warning',
            'title': 'High Response Time',
            'message': f"Average response time: {perf['avg_response_time']:.2f}s",
            'timestamp': datetime.now().isoformat(),
        })
    
    if perf.get('error_rate', 0) > 5.0:
        alerts.append({
            'severity': 'critical',
            'title': 'High Error Rate',
            'message': f"Error rate: {perf['error_rate']:.1f}%",
            'timestamp': datetime.now().isoformat(),
        })
    
    # Memory-based alerts
    memory = metrics.get('memory', {})
    if memory.get('avg_memory_mb', 0) > 1024:  # 1GB
        alerts.append({
            'severity': 'warning',
            'title': 'High Memory Usage',
            'message': f"Memory usage: {memory['avg_memory_mb']:.1f}MB",
            'timestamp': datetime.now().isoformat(),
        })
    
    # Session-based alerts
    sessions = metrics.get('sessions', {})
    if sessions.get('active_sessions', 0) > sessions.get('total_sessions', 0) * 0.9:
        alerts.append({
            'severity': 'info',
            'title': 'High Session Usage',
            'message': f"Active sessions: {sessions['active_sessions']}",
            'timestamp': datetime.now().isoformat(),
        })
    
    return alerts

def format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def get_historical_metrics(hours: int = 24) -> Dict[str, Any]:
    """Get historical metrics for the specified time period."""
    try:
        # This would typically read from a time-series database
        # For now, return current metrics with timestamp ranges
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        return {
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'hours': hours,
            'data_points': [],  # Would contain historical data points
            'summary': get_metrics_summary(),
        }
    except Exception as e:
        logger.error(f"Error getting historical metrics: {e}")
        return {'error': str(e)}

def optimize_system() -> Dict[str, Any]:
    """Run system optimization routines."""
    try:
        # Memory optimization
        memory_before = get_memory_stats()
        optimize_memory_usage()
        memory_after = get_memory_stats()
        
        # Force garbage collection
        import gc
        collected = gc.collect()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'memory_optimization': {
                'before': memory_before,
                'after': memory_after,
                'improvement': memory_before.get('rss', 0) - memory_after.get('rss', 0),
            },
            'garbage_collection': {
                'objects_collected': collected,
            },
            'status': 'success',
        }
    except Exception as e:
        logger.error(f"Error during system optimization: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'status': 'error',
        }

def export_metrics_report(format: str = 'json') -> str:
    """Export comprehensive metrics report."""
    try:
        dashboard_data = get_dashboard_data()
        historical_data = get_historical_metrics(24)
        
        report = {
            'report_generated': datetime.now().isoformat(),
            'dashboard': dashboard_data,
            'historical': historical_data,
            'recommendations': generate_recommendations(dashboard_data),
        }
        
        if format.lower() == 'json':
            filename = f"metrics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            return filename
        elif format.lower() == 'html':
            filename = f"metrics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            html_content = generate_html_report(report)
            with open(filename, 'w') as f:
                f.write(html_content)
            return filename
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    except Exception as e:
        logger.error(f"Error exporting metrics report: {e}")
        raise

def generate_recommendations(data: Dict[str, Any]) -> List[str]:
    """Generate performance recommendations based on metrics."""
    recommendations = []
    
    # Performance recommendations
    perf = data.get('metrics', {}).get('performance', {})
    if perf.get('avg_response_time', 0) > 1.0:
        recommendations.append("Consider optimizing slow endpoints or adding caching")
    
    if perf.get('error_rate', 0) > 2.0:
        recommendations.append("Investigate and fix error-prone endpoints")
    
    # Memory recommendations
    memory = data.get('memory', {})
    if memory.get('rss', 0) > 1024 * 1024 * 1024:  # 1GB
        recommendations.append("Memory usage is high, consider implementing memory optimization")
    
    # System recommendations
    system = data.get('system', {})
    if system.get('memory', {}).get('percent', 0) > 80:
        recommendations.append("System memory usage is high, consider adding more RAM")
    
    if system.get('cpu', {}).get('percent', 0) > 80:
        recommendations.append("CPU usage is high, consider scaling or optimizing")
    
    # Session recommendations
    sessions = data.get('metrics', {}).get('sessions', {})
    if sessions.get('active_sessions', 0) > 50:
        recommendations.append("Consider implementing session cleanup or connection pooling")
    
    return recommendations

def generate_html_report(data: Dict[str, Any]) -> str:
    """Generate HTML metrics report."""
    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>vibecode Metrics Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .header { background: #f5f5f5; padding: 20px; border-radius: 5px; }
            .section { margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }
            .metric { display: inline-block; margin: 10px; padding: 10px; background: #e9ecef; border-radius: 3px; }
            .alert { padding: 10px; margin: 5px 0; border-radius: 3px; }
            .critical { background: #f8d7da; border: 1px solid #f5c6cb; }
            .warning { background: #fff3cd; border: 1px solid #ffeaa7; }
            .info { background: #d1ecf1; border: 1px solid #bee5eb; }
            table { width: 100%; border-collapse: collapse; margin: 10px 0; }
            th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f2f2f2f; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>vibecode Metrics Report</h1>
            <p>Generated: {report_time}</p>
        </div>
        
        <div class="section">
            <h2>System Health</h2>
            <p><strong>Status:</strong> {health_status}</p>
            <p><strong>Uptime:</strong> {uptime}</p>
        </div>
        
        <div class="section">
            <h2>Performance Metrics</h2>
            <div class="metric">Avg Response Time: {avg_response_time}s</div>
            <div class="metric">Error Rate: {error_rate}%</div>
            <div class="metric">Total Requests: {total_requests}</div>
        </div>
        
        <div class="section">
            <h2>Active Alerts</h2>
            {alerts_html}
        </div>
        
        <div class="section">
            <h2>Recommendations</h2>
            <ul>
                {recommendations_html}
            </ul>
        </div>
    </body>
    </html>
    """
    
    # Extract data for template
    dashboard = data.get('dashboard', {})
    health = dashboard.get('health', {})
    metrics = dashboard.get('metrics', {}).get('performance', {})
    alerts = dashboard.get('alerts', [])
    
    # Generate alerts HTML
    alerts_html = ""
    for alert in alerts:
        alerts_html += f'<div class="alert {alert["severity"]}">{alert["title"]}: {alert["message"]}</div>'
    
    # Generate recommendations HTML
    recommendations = data.get('recommendations', [])
    recommendations_html = "".join(f"<li>{rec}</li>" for rec in recommendations)
    
    return html_template.format(
        report_time=data.get('report_generated', 'Unknown'),
        health_status=health.get('status', 'Unknown'),
        uptime=dashboard.get('uptime_formatted', 'Unknown'),
        avg_response_time=metrics.get('avg_response_time', 0),
        error_rate=metrics.get('error_rate', 0),
        total_requests=metrics.get('total_requests', 0),
        alerts_html=alerts_html,
        recommendations_html=recommendations_html,
    )