"""
Hermes Web UI -- Advanced JWT-based authentication system.
Provides secure token management, refresh tokens, and role-based access control.
"""
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps

logger = logging.getLogger(__name__)

class TokenType(Enum):
    """JWT token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET = "reset"
    VERIFICATION = "verification"

class UserRole(Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"
    API = "api"

@dataclass
class JWTPayload:
    """JWT token payload."""
    sub: str  # subject (user ID)
    iat: int  # issued at
    exp: int  # expiration
    jti: str  # JWT ID
    type: TokenType
    role: UserRole
    permissions: List[str]
    session_id: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None

@dataclass
class RefreshToken:
    """Refresh token information."""
    token_id: str
    user_id: str
    created_at: float
    expires_at: float
    last_used: Optional[float] = None
    is_revoked: bool = False
    client_info: Dict[str, Any] = None

@dataclass
class User:
    """User information."""
    user_id: str
    username: str
    email: str
    role: UserRole
    permissions: List[str]
    password_hash: str
    created_at: float
    last_login: Optional[float] = None
    is_active: bool = True
    mfa_enabled: bool = False
    mfa_secret: Optional[str] = None

class JWTAuthManager:
    """Manages JWT authentication and authorization."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256",
                 access_token_ttl: int = 3600, refresh_token_ttl: int = 86400 * 30):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_ttl = access_token_ttl
        self.refresh_token_ttl = refresh_token_ttl
        
        # Token storage
        self.refresh_tokens: Dict[str, RefreshToken] = {}
        self.blacklisted_tokens: set = set()
        self.users: Dict[str, User] = {}
        
        # Role permissions
        self.role_permissions = {
            UserRole.ADMIN: [
                "read_all", "write_all", "delete_all", "manage_users",
                "manage_system", "view_logs", "manage_sessions", "manage_swarm",
                "manage_terminal", "manage_search", "view_analytics"
            ],
            UserRole.USER: [
                "read_own", "write_own", "delete_own", "create_sessions",
                "manage_own_sessions", "use_terminal", "use_swarm", "search"
            ],
            UserRole.VIEWER: [
                "read_own", "view_sessions", "search"
            ],
            UserRole.API: [
                "read_all", "write_all", "api_access"
            ]
        }
    
    def create_user(self, username: str, email: str, password: str,
                   role: UserRole = UserRole.USER) -> str:
        """Create a new user."""
        user_id = str(uuid.uuid4())
        password_hash = self._hash_password(password)
        
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=self.role_permissions[role],
            password_hash=password_hash,
            created_at=time.time()
        )
        
        self.users[user_id] = user
        logger.info(f"Created user: {username} ({user_id})")
        return user_id
    
    def authenticate_user(self, username: str, password: str,
                         client_ip: str = None, user_agent: str = None) -> Optional[Dict[str, Any]]:
        """Authenticate user and return tokens."""
        # Find user by username or email
        user = None
        for u in self.users.values():
            if u.username == username or u.email == username:
                user = u
                break
        
        if not user or not user.is_active:
            return None
        
        # Verify password
        if not self._verify_password(password, user.password_hash):
            return None
        
        # Update last login
        user.last_login = time.time()
        
        # Create tokens
        access_token = self._create_access_token(user, client_ip, user_agent)
        refresh_token = self._create_refresh_token(user, client_ip, user_agent)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token['token'],
            'token_type': 'bearer',
            'expires_in': self.access_token_ttl,
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'email': user.email,
                'role': user.role.value,
                'permissions': user.permissions
            }
        }
    
    def _create_access_token(self, user: User, client_ip: str = None,
                          user_agent: str = None) -> str:
        """Create access token."""
        now = int(time.time())
        payload = JWTPayload(
            sub=user.user_id,
            iat=now,
            exp=now + self.access_token_ttl,
            jti=str(uuid.uuid4()),
            type=TokenType.ACCESS,
            role=user.role,
            permissions=user.permissions,
            client_ip=client_ip,
            user_agent=user_agent
        )
        
        return jwt.encode(asdict(payload), self.secret_key, algorithm=self.algorithm)
    
    def _create_refresh_token(self, user: User, client_ip: str = None,
                           user_agent: str = None) -> Dict[str, Any]:
        """Create refresh token."""
        token_id = str(uuid.uuid4())
        now = time.time()
        
        refresh_token = RefreshToken(
            token_id=token_id,
            user_id=user.user_id,
            created_at=now,
            expires_at=now + self.refresh_token_ttl,
            client_info={
                'client_ip': client_ip,
                'user_agent': user_agent
            }
        )
        
        # Store refresh token
        self.refresh_tokens[token_id] = refresh_token
        
        # Create JWT for refresh token
        payload = JWTPayload(
            sub=user.user_id,
            iat=int(now),
            exp=int(now + self.refresh_token_ttl),
            jti=token_id,
            type=TokenType.REFRESH,
            role=user.role,
            permissions=user.permissions
        )
        
        token = jwt.encode(asdict(payload), self.secret_key, algorithm=self.algorithm)
        
        return {
            'token': token,
            'token_id': token_id,
            'expires_at': refresh_token.expires_at
        }
    
    def verify_token(self, token: str) -> Optional[JWTPayload]:
        """Verify JWT token and return payload."""
        try:
            # Check if token is blacklisted
            if token in self.blacklisted_tokens:
                return None
            
            # Decode token
            payload_dict = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Convert to JWTPayload
            payload = JWTPayload(
                sub=payload_dict['sub'],
                iat=payload_dict['iat'],
                exp=payload_dict['exp'],
                jti=payload_dict['jti'],
                type=TokenType(payload_dict['type']),
                role=UserRole(payload_dict['role']),
                permissions=payload_dict['permissions'],
                session_id=payload_dict.get('session_id'),
                client_ip=payload_dict.get('client_ip'),
                user_agent=payload_dict.get('user_agent')
            )
            
            # Additional validation for refresh tokens
            if payload.type == TokenType.REFRESH:
                if payload.jti not in self.refresh_tokens:
                    return None
                
                refresh_token = self.refresh_tokens[payload.jti]
                if refresh_token.is_revoked or refresh_token.expires_at < time.time():
                    return None
                
                # Update last used
                refresh_token.last_used = time.time()
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token."""
        payload = self.verify_token(refresh_token)
        
        if not payload or payload.type != TokenType.REFRESH:
            return None
        
        # Get user
        user = self.users.get(payload.sub)
        if not user or not user.is_active:
            return None
        
        # Create new access token
        access_token = self._create_access_token(
            user, payload.client_ip, payload.user_agent
        )
        
        return {
            'access_token': access_token,
            'token_type': 'bearer',
            'expires_in': self.access_token_ttl
        }
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token."""
        payload = self.verify_token(token)
        
        if not payload:
            return False
        
        if payload.type == TokenType.REFRESH:
            # Revoke refresh token
            if payload.jti in self.refresh_tokens:
                self.refresh_tokens[payload.jti].is_revoked = True
                return True
        else:
            # Blacklist access token
            self.blacklisted_tokens.add(token)
            return True
        
        return False
    
    def revoke_user_tokens(self, user_id: str) -> int:
        """Revoke all tokens for a user."""
        revoked_count = 0
        
        # Revoke refresh tokens
        for token_id, refresh_token in self.refresh_tokens.items():
            if refresh_token.user_id == user_id and not refresh_token.is_revoked:
                refresh_token.is_revoked = True
                revoked_count += 1
        
        logger.info(f"Revoked {revoked_count} tokens for user {user_id}")
        return revoked_count
    
    def check_permission(self, payload: JWTPayload, permission: str) -> bool:
        """Check if user has permission."""
        return permission in payload.permissions
    
    def check_role(self, payload: JWTPayload, role: UserRole) -> bool:
        """Check if user has role."""
        return payload.role == role or (
            payload.role == UserRole.ADMIN and role != UserRole.ADMIN
        )
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        try:
            import bcrypt
            salt = bcrypt.gensalt()
            return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        except ImportError:
            # Fallback to SHA-256
            return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        try:
            import bcrypt
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except ImportError:
            # Fallback to SHA-256
            return hashlib.sha256(password.encode()).hexdigest() == password_hash
    
    def cleanup_expired_tokens(self) -> int:
        """Clean up expired tokens."""
        now = time.time()
        expired_tokens = []
        
        # Clean up refresh tokens
        for token_id, refresh_token in self.refresh_tokens.items():
            if refresh_token.expires_at < now:
                expired_tokens.append(token_id)
        
        for token_id in expired_tokens:
            del self.refresh_tokens[token_id]
        
        # Clean up blacklisted tokens (older than 24 hours)
        old_tokens = []
        for token in self.blacklisted_tokens:
            try:
                payload = jwt.decode(token, options={'verify_signature': False})
                if payload.get('exp', 0) < now - 86400:  # 24 hours ago
                    old_tokens.append(token)
            except Exception:
                old_tokens.append(token)
        
        for token in old_tokens:
            self.blacklisted_tokens.remove(token)
        
        total_cleaned = len(expired_tokens) + len(old_tokens)
        logger.info(f"Cleaned up {total_cleaned} expired tokens")
        return total_cleaned
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information."""
        user = self.users.get(user_id)
        if not user:
            return None
        
        return {
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'permissions': user.permissions,
            'created_at': user.created_at,
            'last_login': user.last_login,
            'is_active': user.is_active,
            'mfa_enabled': user.mfa_enabled
        }
    
    def update_user_role(self, user_id: str, new_role: UserRole) -> bool:
        """Update user role."""
        user = self.users.get(user_id)
        if not user:
            return False
        
        old_role = user.role
        user.role = new_role
        user.permissions = self.role_permissions[new_role]
        
        # Revoke existing tokens
        self.revoke_user_tokens(user_id)
        
        logger.info(f"Updated user {user_id} role from {old_role} to {new_role}")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get authentication statistics."""
        now = time.time()
        active_refresh_tokens = sum(
            1 for t in self.refresh_tokens.values()
            if not t.is_revoked and t.expires_at > now
        )
        
        role_counts = {}
        for user in self.users.values():
            role_counts[user.role.value] = role_counts.get(user.role.value, 0) + 1
        
        return {
            'total_users': len(self.users),
            'active_users': sum(1 for u in self.users.values() if u.is_active),
            'role_distribution': role_counts,
            'active_refresh_tokens': active_refresh_tokens,
            'blacklisted_tokens': len(self.blacklisted_tokens)
        }

# Decorators for authentication and authorization
def require_auth(auth_manager: JWTAuthManager):
    """Decorator to require authentication."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract token from request (first argument should be handler)
            handler = args[0] if args else None
            if not handler:
                raise Exception("No handler provided")
            
            # Get token from Authorization header
            auth_header = getattr(handler, 'headers', {}).get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return {'error': 'Missing or invalid authorization header'}, 401
            
            token = auth_header[7:]  # Remove 'Bearer '
            
            # Verify token
            payload = auth_manager.verify_token(token)
            if not payload:
                return {'error': 'Invalid or expired token'}, 401
            
            # Add payload to kwargs for function
            kwargs['auth_payload'] = payload
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_permission(permission: str, auth_manager: JWTAuthManager):
    """Decorator to require specific permission."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            payload = kwargs.get('auth_payload')
            if not payload:
                return {'error': 'Authentication required'}, 401
            
            if not auth_manager.check_permission(payload, permission):
                return {'error': f'Permission required: {permission}'}, 403
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

def require_role(role: UserRole, auth_manager: JWTAuthManager):
    """Decorator to require specific role."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            payload = kwargs.get('auth_payload')
            if not payload:
                return {'error': 'Authentication required'}, 401
            
            if not auth_manager.check_role(payload, role):
                return {'error': f'Role required: {role.value}'}, 403
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Global JWT auth manager
JWT_AUTH_MANAGER = None

def get_jwt_auth_manager(secret_key: str = None, **kwargs) -> JWTAuthManager:
    """Get global JWT auth manager instance."""
    global JWT_AUTH_MANAGER
    if JWT_AUTH_MANAGER is None:
        if not secret_key:
            secret_key = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
        JWT_AUTH_MANAGER = JWTAuthManager(secret_key, **kwargs)
    return JWT_AUTH_MANAGER

def init_jwt_auth(secret_key: str = None, **kwargs) -> None:
    """Initialize JWT authentication system."""
    manager = get_jwt_auth_manager(secret_key, **kwargs)
    
    # Create default admin user if none exists
    if not manager.users:
        admin_password = secrets.token_urlsafe(16)
        admin_id = manager.create_user(
            username="admin",
            email="admin@vibecode.local",
            password=admin_password,
            role=UserRole.ADMIN
        )
        logger.info(f"Created default admin user. Password: {admin_password}")
    
    logger.info("JWT authentication system initialized")