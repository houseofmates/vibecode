"""
Hermes Web UI -- Advanced structured logging system.
Provides JSON-formatted logs, correlation tracking, and log aggregation.
"""
import json
import logging
import logging.handlers
import os
import sys
import time
import traceback
import threading
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import uuid
import hashlib

logger = logging.getLogger(__name__)

class LogLevel(Enum):
    """Log levels with numeric values."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

class LogCategory(Enum):
    """Log categories for better organization."""
    SYSTEM = "system"
    API = "api"
    AUTH = "auth"
    SESSION = "session"
    SWARM = "swarm"
    TERMINAL = "terminal"
    SEARCH = "search"
    CACHE = "cache"
    MONITORING = "monitoring"
    SECURITY = "security"
    PERFORMANCE = "performance"

@dataclass
class LogContext:
    """Structured log context."""
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    error_type: Optional[str] = None
    component: Optional[str] = None
    version: Optional[str] = None

@dataclass
class LogEvent:
    """Structured log event."""
    timestamp: float
    level: LogLevel
    category: LogCategory
    message: str
    context: LogContext
    extra_data: Dict[str, Any]
    stack_trace: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp,
            'datetime': datetime.fromtimestamp(self.timestamp).isoformat(),
            'level': self.level.name,
            'category': self.category.value,
            'message': self.message,
            'context': asdict(self.context),
            'extra_data': self.extra_data,
            'stack_trace': self.stack_trace,
            'thread_id': threading.get_ident(),
            'process_id': os.getpid()
        }

class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logs."""
    
    def __init__(self, include_stack_trace: bool = True):
        super().__init__()
        self.include_stack_trace = include_stack_trace
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Extract structured data from record
        log_event = self._extract_log_event(record)
        
        # Convert to JSON
        return json.dumps(log_event.to_dict(), default=str, ensure_ascii=False)
    
    def _extract_log_event(self, record: logging.LogRecord) -> LogEvent:
        """Extract log event from log record."""
        # Parse level
        level = LogLevel(record.levelno)
        
        # Parse category
        category = getattr(record, 'category', LogCategory.SYSTEM)
        if isinstance(category, str):
            try:
                category = LogCategory(category)
            except ValueError:
                category = LogCategory.SYSTEM
        
        # Extract context
        context = LogContext(
            correlation_id=getattr(record, 'correlation_id', None),
            user_id=getattr(record, 'user_id', None),
            session_id=getattr(record, 'session_id', None),
            request_id=getattr(record, 'request_id', None),
            client_ip=getattr(record, 'client_ip', None),
            user_agent=getattr(record, 'user_agent', None),
            method=getattr(record, 'method', None),
            path=getattr(record, 'path', None),
            status_code=getattr(record, 'status_code', None),
            duration_ms=getattr(record, 'duration_ms', None),
            error_type=getattr(record, 'error_type', None),
            component=getattr(record, 'component', None),
            version=getattr(record, 'version', None)
        )
        
        # Extract extra data
        extra_data = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info'] + list(context.__dict__.keys()):
                extra_data[key] = value
        
        # Extract stack trace
        stack_trace = None
        if self.include_stack_trace and record.exc_info:
            stack_trace = ''.join(traceback.format_exception(*record.exc_info))
        
        return LogEvent(
            timestamp=record.created,
            level=level,
            category=category,
            message=record.getMessage(),
            context=context,
            extra_data=extra_data,
            stack_trace=stack_trace
        )

class CorrelationFilter(logging.Filter):
    """Filter to add correlation ID to log records."""
    
    def __init__(self):
        super().__init__()
        self._local = threading.local()
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for current thread."""
        self._local.correlation_id = correlation_id
    
    def get_correlation_id(self) -> Optional[str]:
        """Get correlation ID for current thread."""
        return getattr(self._local, 'correlation_id', None)
    
    def filter(self, record: logging.LogRecord) -> logging.LogRecord:
        """Add correlation ID to log record."""
        correlation_id = self.get_correlation_id()
        if correlation_id:
            record.correlation_id = correlation_id
        return record

class StructuredLogger:
    """Enhanced logger with structured logging capabilities."""
    
    def __init__(self, name: str, category: LogCategory = LogCategory.SYSTEM):
        self.logger = logging.getLogger(name)
        self.category = category
        self.correlation_filter = CorrelationFilter()
        
        # Add correlation filter
        self.logger.addFilter(self.correlation_filter)
        
        # Set up handlers if not already configured
        if not self.logger.handlers:
            self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Set up log handlers."""
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler (if configured)
        log_file = os.getenv('HERMES_LOG_FILE')
        if log_file:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=100 * 1024 * 1024,  # 100MB
                backupCount=10
            )
            file_handler.setFormatter(StructuredFormatter())
            self.logger.addHandler(file_handler)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def _log(self, level: LogLevel, message: str, **kwargs) -> None:
        """Internal logging method."""
        # Add category and extra data to record
        extra = {
            'category': self.category.value,
            **kwargs
        }
        
        # Log with appropriate level
        if level == LogLevel.DEBUG:
            self.logger.debug(message, extra=extra)
        elif level == LogLevel.INFO:
            self.logger.info(message, extra=extra)
        elif level == LogLevel.WARNING:
            self.logger.warning(message, extra=extra)
        elif level == LogLevel.ERROR:
            self.logger.error(message, extra=extra, exc_info=kwargs.get('exc_info'))
        elif level == LogLevel.CRITICAL:
            self.logger.critical(message, extra=extra, exc_info=kwargs.get('exc_info'))
    
    def log_api_request(self, method: str, path: str, status_code: int, 
                       duration_ms: float, **kwargs) -> None:
        """Log API request."""
        self.info(
            f"API {method} {path}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_session_event(self, event_type: str, session_id: str, **kwargs) -> None:
        """Log session-related event."""
        self.info(
            f"Session {event_type}",
            category=LogCategory.SESSION,
            session_id=session_id,
            event_type=event_type,
            **kwargs
        )
    
    def log_security_event(self, event_type: str, details: Dict[str, Any], 
                          severity: str = 'warning') -> None:
        """Log security-related event."""
        level = LogLevel.WARNING if severity == 'warning' else LogLevel.ERROR
        self._log(
            level,
            f"Security event: {event_type}",
            category=LogCategory.SECURITY,
            security_event=event_type,
            security_details=details,
            **kwargs
        )
    
    def log_performance_metric(self, metric_name: str, value: float, 
                             unit: str = 'ms', **kwargs) -> None:
        """Log performance metric."""
        self.info(
            f"Performance metric: {metric_name}",
            category=LogCategory.PERFORMANCE,
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            **kwargs
        )
    
    def log_error_with_context(self, error: Exception, context: Dict[str, Any], 
                             **kwargs) -> None:
        """Log error with full context."""
        self.error(
            f"Error: {str(error)}",
            category=LogCategory.SYSTEM,
            error_type=type(error).__name__,
            error_message=str(error),
            context_data=context,
            exc_info=True,
            **kwargs
        )
    
    def set_correlation_id(self, correlation_id: str) -> None:
        """Set correlation ID for current thread."""
        self.correlation_filter.set_correlation_id(correlation_id)
    
    def get_correlation_id(self) -> Optional[str]:
        """Get correlation ID for current thread."""
        return self.correlation_filter.get_correlation_id()

class LogAggregator:
    """Aggregates and analyzes structured logs."""
    
    def __init__(self, log_file: str = None):
        self.log_file = log_file or os.getenv('HERMES_LOG_FILE')
        self.metrics = {
            'total_logs': 0,
            'error_count': 0,
            'warning_count': 0,
            'api_requests': 0,
            'session_events': 0,
            'security_events': 0,
            'performance_metrics': 0,
            'avg_response_time': 0.0,
            'error_rate': 0.0
        }
        self.lock = threading.RLock()
    
    def analyze_logs(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze logs from the specified time period."""
        if not self.log_file or not os.path.exists(self.log_file):
            return {'error': 'Log file not found'}
        
        cutoff_time = time.time() - (hours * 3600)
        analysis = {
            'time_period_hours': hours,
            'total_logs': 0,
            'by_level': {},
            'by_category': {},
            'top_errors': {},
            'performance_summary': {},
            'security_events': [],
            'api_summary': {}
        }
        
        try:
            with open(self.log_file, 'r') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        log_time = log_entry.get('timestamp', 0)
                        
                        if log_time < cutoff_time:
                            continue
                        
                        analysis['total_logs'] += 1
                        
                        # Count by level
                        level = log_entry.get('level', 'UNKNOWN')
                        analysis['by_level'][level] = analysis['by_level'].get(level, 0) + 1
                        
                        # Count by category
                        category = log_entry.get('category', 'system')
                        analysis['by_category'][category] = analysis['by_category'].get(category, 0) + 1
                        
                        # Track errors
                        if level in ['ERROR', 'CRITICAL']:
                            message = log_entry.get('message', '')
                            analysis['top_errors'][message] = analysis['top_errors'].get(message, 0) + 1
                        
                        # Track performance
                        if category == 'performance':
                            metric_name = log_entry.get('extra_data', {}).get('metric_name')
                            metric_value = log_entry.get('extra_data', {}).get('metric_value')
                            if metric_name and metric_value:
                                if metric_name not in analysis['performance_summary']:
                                    analysis['performance_summary'][metric_name] = []
                                analysis['performance_summary'][metric_name].append(metric_value)
                        
                        # Track security events
                        if category == 'security':
                            analysis['security_events'].append({
                                'timestamp': log_time,
                                'event_type': log_entry.get('extra_data', {}).get('security_event'),
                                'message': log_entry.get('message')
                            })
                        
                        # Track API requests
                        if log_entry.get('method') and log_entry.get('path'):
                            duration = log_entry.get('context', {}).get('duration_ms')
                            if duration:
                                if 'response_times' not in analysis['api_summary']:
                                    analysis['api_summary']['response_times'] = []
                                analysis['api_summary']['response_times'].append(duration)
                            
                            status = log_entry.get('context', {}).get('status_code')
                            if status:
                                if 'status_codes' not in analysis['api_summary']:
                                    analysis['api_summary']['status_codes'] = {}
                                analysis['api_summary']['status_codes'][status] = analysis['api_summary']['status_codes'].get(status, 0) + 1
                    
                    except json.JSONDecodeError:
                        continue
                    except Exception:
                        continue
            
            # Calculate summary stats
            if analysis['api_summary'].get('response_times'):
                times = analysis['api_summary']['response_times']
                analysis['api_summary']['avg_response_time'] = sum(times) / len(times)
                analysis['api_summary']['p95_response_time'] = sorted(times)[int(len(times) * 0.95)]
            
            # Calculate error rate
            total_requests = sum(analysis['api_summary'].get('status_codes', {}).values())
            error_requests = sum(count for status, count in analysis['api_summary'].get('status_codes', {}).items() if status >= 400)
            if total_requests > 0:
                analysis['api_summary']['error_rate'] = (error_requests / total_requests) * 100
            
            return analysis
            
        except Exception as e:
            return {'error': f'Analysis failed: {str(e)}'}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        with self.lock:
            return self.metrics.copy()

# Global structured loggers
STRUCTURED_LOGGERS: Dict[str, StructuredLogger] = {}

def get_structured_logger(name: str, category: LogCategory = LogCategory.SYSTEM) -> StructuredLogger:
    """Get or create structured logger."""
    if name not in STRUCTURED_LOGGERS:
        STRUCTURED_LOGGERS[name] = StructuredLogger(name, category)
    return STRUCTURED_LOGGERS[name]

def init_structured_logging(log_level: str = "INFO", log_file: str = None) -> None:
    """Initialize structured logging system."""
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=[]
    )
    
    # Set up file logging if specified
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        os.environ['HERMES_LOG_FILE'] = log_file
    
    # Create default structured logger
    default_logger = get_structured_logger('vibecode', LogCategory.SYSTEM)
    
    logger.info("Structured logging initialized", 
                log_level=log_level, 
                log_file=log_file)

# Decorators for automatic logging
def log_function_calls(logger_name: str = None, category: LogCategory = LogCategory.SYSTEM):
    """Decorator to log function calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_structured_logger(logger_name or func.__module__, category)
            correlation_id = str(uuid.uuid4())
            logger.set_correlation_id(correlation_id)
            
            start_time = time.time()
            try:
                logger.debug(f"Calling {func.__name__}",
                           function=func.__name__,
                           args_count=len(args),
                           kwargs_count=len(kwargs))
                
                result = func(*args, **kwargs)
                
                duration_ms = (time.time() - start_time) * 1000
                logger.debug(f"Completed {func.__name__}",
                           function=func.__name__,
                           duration_ms=duration_ms,
                           success=True)
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.log_error_with_context(e, {
                    'function': func.__name__,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs),
                    'duration_ms': duration_ms
                })
                raise
            finally:
                logger.set_correlation_id(None)
        
        return wrapper
    return decorator

def log_api_calls(logger_name: str = None):
    """Decorator to log API calls."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Extract request info from first argument (usually handler)
            handler = args[0] if args else None
            if handler and hasattr(handler, 'path'):
                logger = get_structured_logger(logger_name or 'api', LogCategory.API)
                correlation_id = str(uuid.uuid4())
                logger.set_correlation_id(correlation_id)
                
                start_time = time.time()
                method = getattr(handler, 'command', 'UNKNOWN')
                path = handler.path
                
                try:
                    result = func(*args, **kwargs)
                    
                    duration_ms = (time.time() - start_time) * 1000
                    status_code = getattr(result, 'status_code', 200) if hasattr(result, 'status_code') else 200
                    
                    logger.log_api_request(method, path, status_code, duration_ms)
                    return result
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    logger.log_error_with_context(e, {
                        'method': method,
                        'path': path,
                        'duration_ms': duration_ms
                    })
                    raise
                finally:
                    logger.set_correlation_id(None)
            else:
                return func(*args, **kwargs)
        
        return wrapper
    return decorator