"""
Hermes Web UI -- API versioning and backward compatibility.
Provides version management, deprecation warnings, and API migration.
"""
import json
import logging
import time
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from functools import wraps
import re

logger = logging.getLogger(__name__)

class Version(Enum):
    """API version enumeration."""
    V1_0 = "1.0"
    V1_1 = "1.1"
    V1_2 = "1.2"
    V2_0 = "2.0"
    LATEST = "2.0"

class DeprecationStatus(Enum):
    """Deprecation status for features."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    REMOVED = "removed"

@dataclass
class EndpointInfo:
    """Endpoint version information."""
    path: str
    method: str
    min_version: Version
    max_version: Optional[Version]
    deprecation_status: DeprecationStatus
    deprecation_message: Optional[str]
    migration_path: Optional[str]
    parameters: Dict[str, Dict[str, Any]]
    response_schema: Dict[str, Any]

@dataclass
class APIVersion:
    """API version definition."""
    version: Version
    release_date: str
    status: str  # stable, beta, deprecated
    breaking_changes: List[str]
    new_features: List[str]
    security_changes: List[str]
    endpoints: List[EndpointInfo]

class VersionManager:
    """Manages API versions and compatibility."""
    
    def __init__(self):
        self.versions: Dict[str, APIVersion] = {}
        self.endpoints: Dict[str, EndpointInfo] = {}
        self.current_version = Version.V2_0
        self.default_version = Version.V1_0
        self.load_version_definitions()
    
    def load_version_definitions(self) -> None:
        """Load API version definitions."""
        # Version 1.0
        v1_0 = APIVersion(
            version=Version.V1_0,
            release_date="2024-01-01",
            status="stable",
            breaking_changes=[],
            new_features=[
                "Basic session management",
                "Message streaming",
                "File uploads"
            ],
            security_changes=[
                "Basic authentication"
            ],
            endpoints=[]
        )
        
        # Version 1.1
        v1_1 = APIVersion(
            version=Version.V1_1,
            release_date="2024-03-01",
            status="stable",
            breaking_changes=[],
            new_features=[
                "Swarm orchestration",
                "Terminal integration",
                "Wiki memory browser"
            ],
            security_changes=[
                "Enhanced rate limiting"
            ],
            endpoints=[]
        )
        
        # Version 1.2
        v1_2 = APIVersion(
            version=Version.V1_2,
            release_date="2024-06-01",
            status="stable",
            breaking_changes=[
                "Changed response format for /api/sessions"
            ],
            new_features=[
                "Advanced caching",
                "Performance metrics"
            ],
            security_changes=[
                "CSRF protection"
            ],
            endpoints=[]
        )
        
        # Version 2.0
        v2_0 = APIVersion(
            version=Version.V2_0,
            release_date="2024-09-01",
            status="stable",
            breaking_changes=[
                "Removed deprecated endpoints",
                "New authentication system",
                "WebSocket-based real-time updates"
            ],
            new_features=[
                "WebSocket support",
                "Advanced search",
                "Distributed sessions"
            ],
            security_changes=[
                "JWT authentication",
                "Enhanced input validation"
            ],
            endpoints=[]
        )
        
        self.versions = {
            Version.V1_0.value: v1_0,
            Version.V1_1.value: v1_1,
            Version.V1_2.value: v1_2,
            Version.V2_0.value: v2_0
        }
        
        # Define endpoints
        self._define_endpoints()
    
    def _define_endpoints(self) -> None:
        """Define endpoint version mappings."""
        endpoint_definitions = [
            # Session endpoints
            EndpointInfo(
                path="/api/sessions",
                method="GET",
                min_version=Version.V1_0,
                max_version=Version.V1_2,
                deprecation_status=DeprecationStatus.DEPRECATED,
                deprecation_message="Use /api/v2/sessions instead",
                migration_path="/api/v2/sessions",
                parameters={},
                response_schema={}
            ),
            EndpointInfo(
                path="/api/v2/sessions",
                method="GET",
                min_version=Version.V2_0,
                max_version=None,
                deprecation_status=DeprecationStatus.ACTIVE,
                deprecation_message=None,
                migration_path=None,
                parameters={},
                response_schema={}
            ),
            
            # Authentication endpoints
            EndpointInfo(
                path="/api/auth/login",
                method="POST",
                min_version=Version.V1_0,
                max_version=Version.V1_2,
                deprecation_status=DeprecationStatus.DEPRECATED,
                deprecation_message="Use /api/v2/auth/token instead",
                migration_path="/api/v2/auth/token",
                parameters={},
                response_schema={}
            ),
            EndpointInfo(
                path="/api/v2/auth/token",
                method="POST",
                min_version=Version.V2_0,
                max_version=None,
                deprecation_status=DeprecationStatus.ACTIVE,
                deprecation_message=None,
                migration_path=None,
                parameters={},
                response_schema={}
            ),
        ]
        
        for endpoint in endpoint_definitions:
            key = f"{endpoint.method}:{endpoint.path}"
            self.endpoints[key] = endpoint
    
    def get_version_from_request(self, headers: Dict[str, str], 
                              path: str) -> Version:
        """Extract API version from request."""
        # Check Accept header
        accept_header = headers.get('Accept', '')
        version_match = re.search(r'application/vnd\.vibecode\.v(\d+\.\d+)', accept_header)
        if version_match:
            version_str = version_match.group(1)
            if version_str in [v.value for v in Version]:
                return Version(version_str)
        
        # Check URL path
        path_match = re.search(r'/api/v(\d+\.\d+)/', path)
        if path_match:
            version_str = path_match.group(1)
            if version_str in [v.value for v in Version]:
                return Version(version_str)
        
        # Check custom header
        api_version = headers.get('X-API-Version')
        if api_version and api_version in [v.value for v in Version]:
            return Version(api_version)
        
        # Return default version
        return self.default_version
    
    def validate_endpoint(self, path: str, method: str, 
                       version: Version) -> Tuple[bool, Optional[str]]:
        """Validate endpoint for given version."""
        key = f"{method}:{path}"
        
        # Check exact match
        if key in self.endpoints:
            endpoint = self.endpoints[key]
            if self._is_version_supported(endpoint, version):
                return True, None
            else:
                return False, f"Endpoint {path} not available in version {version.value}"
        
        # Check pattern match
        for endpoint_key, endpoint in self.endpoints.items():
            if self._path_matches(path, endpoint.path):
                if self._is_version_supported(endpoint, version):
                    return True, None
                else:
                    return False, f"Endpoint {path} not available in version {version.value}"
        
        return False, f"Endpoint {path} not found"
    
    def _is_version_supported(self, endpoint: EndpointInfo, 
                           version: Version) -> bool:
        """Check if endpoint supports given version."""
        if version.value < endpoint.min_version.value:
            return False
        
        if endpoint.max_version and version.value > endpoint.max_version.value:
            return False
        
        return True
    
    def _path_matches(self, requested_path: str, endpoint_path: str) -> bool:
        """Check if requested path matches endpoint pattern."""
        # Simple pattern matching - could be enhanced with regex
        if '*' in endpoint_path:
            base_path = endpoint_path.replace('*', '')
            return requested_path.startswith(base_path)
        
        return requested_path == endpoint_path
    
    def get_deprecation_warnings(self, version: Version) -> List[Dict[str, Any]]:
        """Get deprecation warnings for version."""
        warnings = []
        
        for endpoint_key, endpoint in self.endpoints.items():
            if (endpoint.deprecation_status == DeprecationStatus.DEPRECATED and
                self._is_version_supported(endpoint, version)):
                
                warnings.append({
                    'endpoint': f"{endpoint.method} {endpoint.path}",
                    'message': endpoint.deprecation_message,
                    'migration_path': endpoint.migration_path,
                    'removal_date': self._get_removal_date(endpoint)
                })
        
        return warnings
    
    def _get_removal_date(self, endpoint: EndpointInfo) -> Optional[str]:
        """Get removal date for deprecated endpoint."""
        # This could be configured per endpoint
        # For now, assume 6 months after deprecation
        if endpoint.deprecation_status == DeprecationStatus.DEPRECATED:
            return "2025-03-01"  # Example date
        return None
    
    def get_version_info(self, version: Version = None) -> Dict[str, Any]:
        """Get version information."""
        if version is None:
            version = self.current_version
        
        version_obj = self.versions.get(version.value)
        if not version_obj:
            return {'error': f'Version {version.value} not found'}
        
        return asdict(version_obj)
    
    def get_all_versions(self) -> List[Dict[str, Any]]:
        """Get all available versions."""
        return [asdict(v) for v in self.versions.values()]
    
    def upgrade_path(self, from_version: Version, 
                   to_version: Version) -> List[str]:
        """Get upgrade path between versions."""
        path = []
        
        # Define upgrade steps
        upgrade_steps = {
            (Version.V1_0, Version.V1_1): [
                "Add swarm support",
                "Update authentication headers"
            ],
            (Version.V1_1, Version.V1_2): [
                "Update session response format",
                "Add CSRF tokens"
            ],
            (Version.V1_2, Version.V2_0): [
                "Migrate to JWT authentication",
                "Update WebSocket endpoints",
                "Remove deprecated API calls"
            ]
        }
        
        current = from_version
        while current.value < to_version.value:
            # Find next version
            next_versions = [v for v in Version if float(v.value) > float(current.value)]
            if not next_versions:
                break
            
            next_version = min(next_versions, key=lambda v: float(v.value))
            step_key = (current, next_version)
            
            if step_key in upgrade_steps:
                path.extend(upgrade_steps[step_key])
            
            current = next_version
        
        return path

def versioned(min_version: Version = Version.V1_0, 
              max_version: Optional[Version] = None,
              deprecation_message: str = None):
    """Decorator for versioned endpoints."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get version from request (first arg should be handler)
            if args and hasattr(args[0], 'headers'):
                request_version = VERSION_MANAGER.get_version_from_request(
                    args[0].headers, 
                    getattr(args[0], 'path', '')
                )
            else:
                request_version = VERSION_MANAGER.default_version
            
            # Check version compatibility
            if float(request_version.value) < float(min_version.value):
                return {
                    'error': 'Endpoint not available in this version',
                    'min_version': min_version.value,
                    'current_version': request_version.value
                }, 415
            
            if max_version and float(request_version.value) > float(max_version.value):
                return {
                    'error': 'Endpoint deprecated in this version',
                    'max_version': max_version.value,
                    'current_version': request_version.value,
                    'message': deprecation_message or 'Use newer API version'
                }, 410
            
            # Call original function
            return func(*args, **kwargs)
        
        # Store version info
        wrapper._version_info = {
            'min_version': min_version,
            'max_version': max_version,
            'deprecation_message': deprecation_message
        }
        
        return wrapper
    return decorator

def deprecated(new_endpoint: str, removal_date: str = None):
    """Decorator for deprecated endpoints."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Add deprecation headers
            if args and hasattr(args[0], 'send_header'):
                args[0].send_header('Deprecation', 'true')
                args[0].send_header('Sunset', removal_date or 'TBD')
                args[0].send_header('Link', f'<{new_endpoint}>; rel="successor-version"')
            
            # Log deprecation warning
            logger.warning(f"Deprecated endpoint called: {func.__name__}")
            
            return func(*args, **kwargs)
        
        wrapper._deprecated = True
        wrapper._new_endpoint = new_endpoint
        wrapper._removal_date = removal_date
        
        return wrapper
    return decorator

def migrate_response_format(old_response: Dict[str, Any], 
                         from_version: Version,
                         to_version: Version) -> Dict[str, Any]:
    """Migrate response format between versions."""
    if from_version == Version.V1_0 and to_version == Version.V1_2:
        # Example: wrap session data
        if 'sessions' in old_response:
            return {
                'data': {
                    'sessions': old_response['sessions'],
                    'total': len(old_response['sessions'])
                },
                'version': to_version.value
            }
    
    # Add more migration logic as needed
    return old_response

# Global version manager
VERSION_MANAGER = VersionManager()

def get_version_manager() -> VersionManager:
    """Get global version manager instance."""
    return VERSION_MANAGER

def init_version_manager() -> None:
    """Initialize version manager."""
    logger.info(f"Version manager initialized, current version: {VERSION_MANAGER.current_version.value}")