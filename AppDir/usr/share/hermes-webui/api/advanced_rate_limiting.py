"""
Hermes Web UI -- Advanced rate limiting with Redis backend.
Provides distributed rate limiting, sliding windows, and adaptive throttling.
"""
import json
import logging
import time
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import asyncio
from collections import defaultdict

logger = logging.getLogger(__name__)

class RateLimitStrategy(Enum):
    """Rate limiting strategies."""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, identifier: str, limit: int, window: int, 
                 retry_after: int, strategy: str):
        self.identifier = identifier
        self.limit = limit
        self.window = window
        self.retry_after = retry_after
        self.strategy = strategy
        super().__init__(f"Rate limit exceeded for {identifier}: {limit}/{window}s")

@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    limit: int = 100  # requests
    window: int = 60   # seconds
    burst: int = 10    # burst capacity
    penalty_multiplier: float = 1.0  # penalty for exceeding limits
    adaptive_threshold: float = 0.8   # threshold for adaptive throttling
    
    def __post_init__(self):
        if isinstance(self.strategy, str):
            self.strategy = RateLimitStrategy(self.strategy)

@dataclass
class RateLimitResult:
    """Rate limit check result."""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: int
    current_usage: int
    strategy: str
    identifier: str

class RedisRateLimiter:
    """Redis-based rate limiter with multiple strategies."""
    
    def __init__(self, redis_client: redis.Redis, prefix: str = "rate_limit:"):
        self.redis = redis_client
        self.prefix = prefix
        self.lock = threading.RLock()
        
        # Lua scripts for atomic operations
        self._load_lua_scripts()
    
    def _load_lua_scripts(self) -> None:
        """Load Lua scripts for atomic rate limiting."""
        
        # Sliding window script
        self.sliding_window_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        
        -- Remove old entries
        redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
        
        -- Count current requests
        local current = redis.call('ZCARD', key)
        
        if current < limit then
            -- Add new request
            redis.call('ZADD', key, now, now)
            redis.call('EXPIRE', key, window)
            return {1, limit - current - 1, now + window}
        else
            -- Rate limited
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            local retry_after = oldest[1] and oldest[2] - now or window
            return {0, 0, now + window, math.ceil(retry_after)}
        end
        """
        
        # Token bucket script
        self.token_bucket_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local capacity = tonumber(ARGV[2])
        local refill_rate = tonumber(ARGV[3])
        local tokens = tonumber(ARGV[4])
        
        local bucket = redis.call('HMGET', key, 'tokens', 'last_refill')
        local current_tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now
        
        -- Refill tokens
        local time_passed = now - last_refill
        local tokens_to_add = math.floor(time_passed * refill_rate)
        current_tokens = math.min(capacity, current_tokens + tokens_to_add)
        
        if current_tokens >= tokens then
            -- Consume tokens
            current_tokens = current_tokens - tokens
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
            redis.call('EXPIRE', key, math.ceil(capacity / refill_rate) + 1)
            return {1, current_tokens, 0}
        else
            -- Rate limited
            redis.call('HMSET', key, 'tokens', current_tokens, 'last_refill', now)
            local retry_after = math.ceil((tokens - current_tokens) / refill_rate)
            return {0, current_tokens, retry_after}
        end
        """
        
        # Fixed window script
        self.fixed_window_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window = tonumber(ARGV[2])
        local limit = tonumber(ARGV[3])
        
        local current = redis.call('GET', key)
        if not current then
            current = 0
        end
        
        current = tonumber(current)
        
        if current < limit then
            redis.call('INCR', key)
            redis.call('EXPIRE', key, window)
            return {1, limit - current - 1, now + window}
        else
            local ttl = redis.call('TTL', key)
            local retry_after = ttl > 0 and ttl or window
            return {0, 0, now + window, retry_after}
        end
        """
        
        # Compile scripts
        self.sliding_window_sha = self.redis.script_load(self.sliding_window_script)
        self.token_bucket_sha = self.redis.script_load(self.token_bucket_script)
        self.fixed_window_sha = self.redis.script_load(self.fixed_window_script)
    
    def check_rate_limit(self, identifier: str, config: RateLimitConfig) -> RateLimitResult:
        """Check rate limit for identifier."""
        key = f"{self.prefix}{identifier}"
        
        try:
            if config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                return self._check_sliding_window(key, config)
            elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
                return self._check_token_bucket(key, config)
            elif config.strategy == RateLimitStrategy.FIXED_WINDOW:
                return self._check_fixed_window(key, config)
            else:
                raise ValueError(f"Unsupported strategy: {config.strategy}")
        
        except redis.RedisError as e:
            logger.error(f"Redis rate limit error: {e}")
            # Fail open - allow request if Redis is down
            return RateLimitResult(
                allowed=True,
                remaining=config.limit,
                reset_time=int(time.time()) + config.window,
                retry_after=0,
                current_usage=0,
                strategy=config.strategy.value,
                identifier=identifier
            )
    
    def _check_sliding_window(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Check sliding window rate limit."""
        now = time.time()
        
        result = self.redis.evalsha(
            self.sliding_window_sha,
            1, key,
            now, config.window, config.limit
        )
        
        allowed = bool(result[0])
        remaining = int(result[1])
        reset_time = int(result[2])
        retry_after = int(result[3]) if len(result) > 3 else 0
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after,
            current_usage=config.limit - remaining,
            strategy=config.strategy.value,
            identifier=key.replace(self.prefix, "")
        )
    
    def _check_token_bucket(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Check token bucket rate limit."""
        now = time.time()
        refill_rate = config.limit / config.window  # tokens per second
        
        result = self.redis.evalsha(
            self.token_bucket_sha,
            1, key,
            now, config.burst or config.limit, refill_rate, 1
        )
        
        allowed = bool(result[0])
        remaining_tokens = int(result[1])
        retry_after = int(result[2]) if len(result) > 2 else 0
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining_tokens,
            reset_time=int(time.time()) + config.window,
            retry_after=retry_after,
            current_usage=(config.burst or config.limit) - remaining_tokens,
            strategy=config.strategy.value,
            identifier=key.replace(self.prefix, "")
        )
    
    def _check_fixed_window(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Check fixed window rate limit."""
        now = time.time()
        
        result = self.redis.evalsha(
            self.fixed_window_sha,
            1, key,
            now, config.window, config.limit
        )
        
        allowed = bool(result[0])
        remaining = int(result[1])
        reset_time = int(result[2])
        retry_after = int(result[3]) if len(result) > 3 else 0
        
        return RateLimitResult(
            allowed=allowed,
            remaining=remaining,
            reset_time=reset_time,
            retry_after=retry_after,
            current_usage=config.limit - remaining,
            strategy=config.strategy.value,
            identifier=key.replace(self.prefix, "")
        )
    
    def reset_rate_limit(self, identifier: str) -> bool:
        """Reset rate limit for identifier."""
        key = f"{self.prefix}{identifier}"
        try:
            return bool(self.redis.delete(key))
        except redis.RedisError as e:
            logger.error(f"Error resetting rate limit: {e}")
            return False
    
    def get_usage_stats(self, identifier: str) -> Dict[str, Any]:
        """Get usage statistics for identifier."""
        key = f"{self.prefix}{identifier}"
        try:
            # Get basic info
            ttl = self.redis.ttl(key)
            
            # For sliding window, get current count
            now = time.time()
            window = 60  # Default window
            count = self.redis.zcount(key, now - window, now)
            
            return {
                'identifier': identifier,
                'current_usage': count,
                'ttl': ttl,
                'window_remaining': max(0, ttl)
            }
        except redis.RedisError as e:
            logger.error(f"Error getting usage stats: {e}")
            return {'error': str(e)}

class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on system load."""
    
    def __init__(self, redis_client: redis.Redis):
        self.base_limiter = RedisRateLimiter(redis_client)
        self.system_metrics = defaultdict(list)
        self.adaptive_configs: Dict[str, RateLimitConfig] = {}
        self.lock = threading.RLock()
    
    def check_rate_limit(self, identifier: str, base_config: RateLimitConfig) -> RateLimitResult:
        """Check rate limit with adaptive adjustments."""
        # Get adaptive config
        config = self._get_adaptive_config(identifier, base_config)
        
        # Check rate limit
        result = self.base_limiter.check_rate_limit(identifier, config)
        
        # Update system metrics
        self._update_metrics(identifier, result)
        
        # Adjust config if needed
        self._adjust_config(identifier, result)
        
        return result
    
    def _get_adaptive_config(self, identifier: str, 
                           base_config: RateLimitConfig) -> RateLimitConfig:
        """Get adaptive configuration for identifier."""
        with self.lock:
            if identifier not in self.adaptive_configs:
                self.adaptive_configs[identifier] = RateLimitConfig(
                    strategy=base_config.strategy,
                    limit=base_config.limit,
                    window=base_config.window,
                    burst=base_config.burst
                )
            return self.adaptive_configs[identifier]
    
    def _update_metrics(self, identifier: str, result: RateLimitResult) -> None:
        """Update system metrics."""
        with self.lock:
            self.system_metrics[identifier].append({
                'timestamp': time.time(),
                'allowed': result.allowed,
                'current_usage': result.current_usage,
                'remaining': result.remaining
            })
            
            # Keep only last 100 entries
            if len(self.system_metrics[identifier]) > 100:
                self.system_metrics[identifier] = self.system_metrics[identifier][-100:]
    
    def _adjust_config(self, identifier: str, result: RateLimitResult) -> None:
        """Adjust configuration based on usage patterns."""
        with self.lock:
            if identifier not in self.system_metrics:
                return
            
            metrics = self.system_metrics[identifier]
            if len(metrics) < 10:
                return  # Need enough data points
            
            # Calculate recent usage
            recent_metrics = metrics[-20:]  # Last 20 requests
            allowed_count = sum(1 for m in recent_metrics if m['allowed'])
            usage_ratio = allowed_count / len(recent_metrics)
            
            config = self.adaptive_configs[identifier]
            
            # Adaptive adjustment
            if usage_ratio < config.adaptive_threshold:
                # Reduce limit if usage is low
                new_limit = max(10, int(config.limit * 0.8))
                if new_limit != config.limit:
                    config.limit = new_limit
                    logger.info(f"Reduced rate limit for {identifier} to {new_limit}")
            
            elif not result.allowed and result.retry_after > 10:
                # Increase limit if being throttled heavily
                new_limit = int(config.limit * 1.2)
                if new_limit <= config.limit * 2:  # Don't increase too much
                    config.limit = new_limit
                    logger.info(f"Increased rate limit for {identifier} to {new_limit}")

class RateLimitManager:
    """Manages multiple rate limiters with different configurations."""
    
    def __init__(self, redis_url: str = None):
        self.redis_client = None
        self.limiter = None
        self.adaptive_limiter = None
        self.configs: Dict[str, RateLimitConfig] = {}
        self.lock = threading.RLock()
        
        if redis_url:
            self._connect_redis(redis_url)
    
    def _connect_redis(self, redis_url: str) -> None:
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=False)
            self.limiter = RedisRateLimiter(self.redis_client)
            self.adaptive_limiter = AdaptiveRateLimiter(self.redis_client)
            logger.info(f"Connected to Redis for rate limiting: {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    def add_rate_limit_config(self, name: str, config: RateLimitConfig) -> None:
        """Add rate limit configuration."""
        with self.lock:
            self.configs[name] = config
    
    def check_rate_limit(self, identifier: str, config_name: str = "default",
                        adaptive: bool = False) -> RateLimitResult:
        """Check rate limit for identifier."""
        config = self.configs.get(config_name, RateLimitConfig())
        
        if not self.limiter:
            # Fallback to in-memory limiting
            return self._memory_rate_limit(identifier, config)
        
        if adaptive and self.adaptive_limiter:
            return self.adaptive_limiter.check_rate_limit(identifier, config)
        else:
            return self.limiter.check_rate_limit(identifier, config)
    
    def _memory_rate_limit(self, identifier: str, config: RateLimitConfig) -> RateLimitResult:
        """Fallback in-memory rate limiting."""
        # Simple in-memory implementation
        with self.lock:
            key = f"memory:{identifier}"
            now = time.time()
            
            if not hasattr(self, '_memory_store'):
                self._memory_store = {}
            
            if key not in self._memory_store:
                self._memory_store[key] = []
            
            # Clean old entries
            self._memory_store[key] = [
                t for t in self._memory_store[key] 
                if now - t < config.window
            ]
            
            if len(self._memory_store[key]) < config.limit:
                self._memory_store[key].append(now)
                return RateLimitResult(
                    allowed=True,
                    remaining=config.limit - len(self._memory_store[key]),
                    reset_time=int(now + config.window),
                    retry_after=0,
                    current_usage=len(self._memory_store[key]),
                    strategy="memory",
                    identifier=identifier
                )
            else:
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_time=int(now + config.window),
                    retry_after=config.window,
                    current_usage=len(self._memory_store[key]),
                    strategy="memory",
                    identifier=identifier
                )
    
    def get_rate_limit_headers(self, result: RateLimitResult) -> Dict[str, str]:
        """Get rate limit headers for HTTP response."""
        headers = {
            'X-RateLimit-Limit': str(result.current_usage + result.remaining),
            'X-RateLimit-Remaining': str(result.remaining),
            'X-RateLimit-Reset': str(result.reset_time),
            'X-RateLimit-Strategy': result.strategy
        }
        
        if not result.allowed:
            headers['Retry-After'] = str(result.retry_after)
        
        return headers
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        stats = {
            'configs': {name: asdict(config) for name, config in self.configs.items()},
            'redis_connected': bool(self.redis_client),
            'adaptive_enabled': bool(self.adaptive_limiter)
        }
        
        if self.redis_client:
            try:
                info = self.redis_client.info()
                stats['redis'] = {
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory': info.get('used_memory_human', '0B'),
                    'total_commands': info.get('total_commands_processed', 0)
                }
            except Exception as e:
                stats['redis_error'] = str(e)
        
        return stats

# Global rate limit manager
RATE_LIMIT_MANAGER = None

def get_rate_limit_manager(redis_url: str = None) -> RateLimitManager:
    """Get global rate limit manager instance."""
    global RATE_LIMIT_MANAGER
    if RATE_LIMIT_MANAGER is None:
        RATE_LIMIT_MANAGER = RateLimitManager(redis_url)
    return RATE_LIMIT_MANAGER

def init_rate_limiting(redis_url: str = None) -> None:
    """Initialize rate limiting system."""
    manager = get_rate_limit_manager(redis_url)
    
    # Add default configurations
    manager.add_rate_limit_config("api", RateLimitConfig(
        strategy=RateLimitStrategy.SLIDING_WINDOW,
        limit=1000,
        window=60
    ))
    
    manager.add_rate_limit_config("auth", RateLimitConfig(
        strategy=RateLimitStrategy.SLIDING_WINDOW,
        limit=10,
        window=60
    ))
    
    manager.add_rate_limit_config("upload", RateLimitConfig(
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        limit=20,
        window=60,
        burst=5
    ))
    
    manager.add_rate_limit_config("terminal", RateLimitConfig(
        strategy=RateLimitStrategy.LEAKY_BUCKET,
        limit=50,
        window=60
    ))
    
    logger.info("Rate limiting system initialized")

# Decorator for automatic rate limiting
def rate_limit(config_name: str = "default", identifier_func: callable = None,
              adaptive: bool = False):
    """Decorator for automatic rate limiting."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            manager = get_rate_limit_manager()
            
            # Extract identifier
            if identifier_func:
                identifier = identifier_func(*args, **kwargs)
            else:
                # Default: use IP address from first argument if it's a handler
                handler = args[0] if args else None
                if handler and hasattr(handler, 'client_address'):
                    identifier = handler.client_address[0]
                else:
                    identifier = 'unknown'
            
            # Check rate limit
            result = manager.check_rate_limit(identifier, config_name, adaptive)
            
            if not result.allowed:
                raise RateLimitExceeded(
                    identifier, result.current_usage + result.remaining,
                    60, result.retry_after, result.strategy
                )
            
            # Call function
            return func(*args, **kwargs)
        
        return wrapper
    return decorator