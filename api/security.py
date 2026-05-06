"""
Hermes Web UI -- Security hardening and validation utilities.
Provides input validation, rate limiting, CSRF protection, and security headers.
"""
import hashlib
import hmac
import ipaddress
import json
import logging
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Rate limiting storage
class RateLimiter:
    """Thread-safe rate limiter with multiple strategies."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(lambda: deque())
        self.lock = threading.RLock()
    
    def is_allowed(self, identifier: str) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed, return (allowed, info)."""
        with self.lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            # Clean old requests
            requests = self.requests[identifier]
            while requests and requests[0] < cutoff:
                requests.popleft()
            
            # Check limit
            if len(requests) >= self.max_requests:
                return False, {
                    'allowed': False,
                    'remaining': 0,
                    'reset_time': requests[0] + self.window_seconds,
                    'retry_after': int(requests[0] + self.window_seconds - now)
                }
            
            # Add current request
            requests.append(now)
            return True, {
                'allowed': True,
                'remaining': self.max_requests - len(requests),
                'reset_time': now + self.window_seconds
            }

# Global rate limiters for different endpoints
RATE_LIMITERS = {
    'api': RateLimiter(max_requests=1000, window_seconds=60),  # General API
    'auth': RateLimiter(max_requests=10, window_seconds=60),    # Auth endpoints
    'upload': RateLimiter(max_requests=20, window_seconds=60),  # File uploads
    'terminal': RateLimiter(max_requests=50, window_seconds=60), # Terminal operations
    'swarm': RateLimiter(max_requests=30, window_seconds=60),    # Swarm operations
}

# Input validation patterns
VALIDATION_PATTERNS = {
    'session_id': re.compile(r'^[a-zA-Z0-9_-]+$'),
    'workspace_path': re.compile(r'^[a-zA-Z0-9_/-]+$'),
    'model_name': re.compile(r'^[a-zA-Z0-9_/.-]+$'),
    'filename': re.compile(r'^[a-zA-Z0-9._-]+$'),
    'terminal_command': re.compile(r'^[a-zA-Z0-9\s._/\\|&;()<>\'"\[\]{}$@#!%^*+=~-]+$'),
}

# Security headers
SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: blob:; "
        "font-src 'self'; "
        "connect-src 'self' ws: wss:; "
        "frame-ancestors 'none';"
    ),
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': (
        'geolocation=(), microphone=(), camera=(), '
        'payment=(), usb=(), magnetometer=(), gyroscope=(), '
        'accelerometer=(), ambient-light-sensor=()'
    )
}

def validate_input(value: str, input_type: str, max_length: int = 1000) -> Tuple[bool, str]:
    """Validate input against patterns and length."""
    if not isinstance(value, str):
        return False, "Input must be a string"
    
    if len(value) > max_length:
        return False, f"Input too long (max {max_length} characters)"
    
    pattern = VALIDATION_PATTERNS.get(input_type)
    if pattern and not pattern.match(value):
        return False, f"Invalid {input_type} format"
    
    # Check for common attack patterns
    dangerous_patterns = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',                # JavaScript URLs
        r'on\w+\s*=',                # Event handlers
        r'\.\./',                     # Path traversal
        r'\0',                        # Null bytes
    ]
    
    for dangerous_pattern in dangerous_patterns:
        if re.search(dangerous_pattern, value, re.IGNORECASE):
            return False, "Potentially dangerous input detected"
    
    return True, ""

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal."""
    # Remove path separators and dangerous characters
    filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', filename)
    filename = filename.replace('..', '')
    filename = filename.strip('. ')
    
    # Limit length
    if len(filename) > 255:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        filename = name[:255-len(ext)-1] + '.' + ext if ext else name[:255]
    
    return filename or 'unnamed'

def validate_ip_address(ip: str) -> bool:
    """Validate IP address and check for private ranges if needed."""
    try:
        ip_obj = ipaddress.ip_address(ip)
        # Allow all IPs except documented malicious ranges
        return not any(
            ip_obj in ipaddress.ip_network(block)
            for block in [
                '0.0.0.0/8',           # Null network
                '169.254.0.0/16',      # Link-local
                '224.0.0.0/4',         # Multicast
            ]
        )
    except ValueError:
        return False

def generate_csrf_token() -> str:
    """Generate CSRF token."""
    return hashlib.sha256(
        f"{time.time()}{os.urandom(32)}".encode()
    ).hexdigest()

def verify_csrf_token(token: str, session_token: str) -> bool:
    """Verify CSRF token against session token."""
    if not token or not session_token:
        return False
    
    # Use constant-time comparison
    return hmac.compare_digest(token, session_token)

def check_rate_limit(identifier: str, endpoint_type: str = 'api') -> Tuple[bool, Dict[str, Any]]:
    """Check rate limit for given identifier and endpoint type."""
    limiter = RATE_LIMITERS.get(endpoint_type, RATE_LIMITERS['api'])
    return limiter.is_allowed(identifier)

def get_client_ip(handler) -> str:
    """Extract real client IP from request."""
    # Check for forwarded headers
    forwarded_for = handler.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Take the first IP in the chain
        return forwarded_for.split(',')[0].strip()
    
    real_ip = handler.headers.get('X-Real-IP')
    if real_ip:
        return real_ip.strip()
    
    # Fall back to client address
    return handler.client_address[0] if handler.client_address else 'unknown'

def add_security_headers(handler) -> None:
    """Add security headers to response."""
    for header, value in SECURITY_HEADERS.items():
        handler.send_header(header, value)

def validate_json_payload(payload: str, max_size: int = 1024 * 1024) -> Tuple[bool, Any, str]:
    """Validate JSON payload size and structure."""
    if len(payload) > max_size:
        return False, None, f"Payload too large (max {max_size} bytes)"
    
    try:
        data = json.loads(payload)
        return True, data, ""
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON: {str(e)}"

def log_security_event(event_type: str, details: Dict[str, Any], severity: str = 'warning') -> None:
    """Log security-related events."""
    security_log = {
        'timestamp': datetime.now().isoformat(),
        'event_type': event_type,
        'severity': severity,
        'details': details
    }
    
    if severity == 'critical':
        logger.critical(f"Security event: {event_type}", extra=details)
    elif severity == 'warning':
        logger.warning(f"Security event: {event_type}", extra=details)
    else:
        logger.info(f"Security event: {event_type}", extra=details)

def check_suspicious_patterns(value: str) -> List[str]:
    """Check for suspicious patterns in input."""
    suspicious = []
    
    # SQL injection patterns
    sql_patterns = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
        r"(--|#|/\*|\*/)",
        r"(\bOR\b.*=.*\bOR\b)",
        r"(\bAND\b.*=.*\bAND\b)",
    ]
    
    for pattern in sql_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            suspicious.append("SQL injection attempt")
    
    # Command injection patterns
    cmd_patterns = [
        r"[;&|`$(){}[\]]",
        r"\b(curl|wget|nc|netcat|ssh|ftp|telnet)\b",
        r"\b(rm|mv|cp|cat|ls|ps|kill)\s",
    ]
    
    for pattern in cmd_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            suspicious.append("Command injection attempt")
    
    # XSS patterns
    xss_patterns = [
        r"<script[^>]*>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
    ]
    
    for pattern in xss_patterns:
        if re.search(pattern, value, re.IGNORECASE):
            suspicious.append("XSS attempt")
    
    return suspicious

def sanitize_html(html: str) -> str:
    """Basic HTML sanitization."""
    # Remove dangerous tags and attributes
    dangerous_tags = ['script', 'iframe', 'object', 'embed', 'form', 'input']
    dangerous_attrs = ['onload', 'onerror', 'onclick', 'onmouseover', 'javascript:']
    
    for tag in dangerous_tags:
        html = re.sub(f'<{tag}[^>]*>.*?</{tag}>', '', html, flags=re.IGNORECASE | re.DOTALL)
        html = re.sub(f'<{tag}[^>]*/?>', '', html, flags=re.IGNORECASE)
    
    for attr in dangerous_attrs:
        html = re.sub(f'{attr}\s*=\s*["\'][^"\']*["\']', '', html, flags=re.IGNORECASE)
    
    return html

# Security middleware for routes
def security_middleware(handler, endpoint_type: str = 'api'):
    """Apply security checks to request."""
    client_ip = get_client_ip(handler)
    
    # Rate limiting
    allowed, rate_info = check_rate_limit(client_ip, endpoint_type)
    if not allowed:
        log_security_event('rate_limit_exceeded', {
            'ip': client_ip,
            'endpoint_type': endpoint_type,
            'retry_after': rate_info['retry_after']
        }, 'warning')
        return False, rate_info
    
    # Add security headers
    add_security_headers(handler)
    
    return True, {'rate_limit': rate_info}

# Initialize security monitoring
def init_security_monitoring():
    """Initialize security monitoring and logging."""
    logger.info("Security monitoring initialized")
    
    # Log security configuration
    security_config = {
        'rate_limiters': {k: v.max_requests for k, v in RATE_LIMITERS.items()},
        'security_headers': list(SECURITY_HEADERS.keys()),
        'validation_patterns': list(VALIDATION_PATTERNS.keys())
    }
    logger.info(f"Security config: {security_config}")