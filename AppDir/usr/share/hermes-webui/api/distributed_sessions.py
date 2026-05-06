"""
Hermes Web UI -- Distributed session management.
Provides session replication, synchronization, and high availability.
"""
import json
import logging
import time
import threading
import uuid
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import asyncio
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class SessionState(Enum):
    """Session synchronization states."""
    ACTIVE = "active"
    SYNCING = "syncing"
    CONFLICT = "conflict"
    LOCKED = "locked"

@dataclass
class SessionNode:
    """Information about a session node."""
    node_id: str
    host: str
    port: int
    last_seen: float
    is_primary: bool = False
    capabilities: List[str] = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = ["read", "write", "sync"]

@dataclass
class SessionSync:
    """Session synchronization event."""
    session_id: str
    node_id: str
    event_type: str
    timestamp: float
    data: Dict[str, Any]
    checksum: str
    version: int

class SessionLock:
    """Distributed session lock."""
    
    def __init__(self, session_id: str, node_id: str, ttl: int = 30):
        self.session_id = session_id
        self.node_id = node_id
        self.ttl = ttl
        self.acquired_at = None
        self.expires_at = None
    
    def is_expired(self) -> bool:
        """Check if lock has expired."""
        return self.expires_at and time.time() > self.expires_at
    
    def acquire(self) -> bool:
        """Acquire the lock."""
        if self.acquired_at and not self.is_expired():
            return False
        
        self.acquired_at = time.time()
        self.expires_at = self.acquired_at + self.ttl
        return True
    
    def release(self) -> bool:
        """Release the lock."""
        if not self.acquired_at:
            return False
        
        self.acquired_at = None
        self.expires_at = None
        return True

class DistributedSessionManager:
    """Manages distributed sessions across multiple nodes."""
    
    def __init__(self, node_id: str = None, host: str = "localhost", 
                 port: int = 8787, redis_url: str = None):
        self.node_id = node_id or str(uuid.uuid4())
        self.host = host
        self.port = port
        self.redis_url = redis_url
        
        # Session storage
        self.local_sessions: Dict[str, Dict[str, Any]] = {}
        self.session_locks: Dict[str, SessionLock] = {}
        self.session_states: Dict[str, SessionState] = {}
        
        # Node management
        self.nodes: Dict[str, SessionNode] = {}
        self.is_primary = False
        self.last_heartbeat = time.time()
        
        # Sync management
        self.sync_queue = asyncio.Queue()
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.sync_interval = 30  # seconds
        self.conflict_resolution = "last_writer_wins"
        
        # Threading
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Initialize
        self._init_storage()
        self._register_handlers()
    
    def _init_storage(self) -> None:
        """Initialize distributed storage backend."""
        try:
            if self.redis_url:
                import redis
                self.redis_client = redis.from_url(self.redis_url)
                self.storage_type = "redis"
                logger.info(f"Using Redis storage: {self.redis_url}")
            else:
                self.redis_client = None
                self.storage_type = "memory"
                logger.info("Using in-memory storage")
        except ImportError:
            logger.warning("Redis not available, falling back to memory storage")
            self.redis_client = None
            self.storage_type = "memory"
    
    def _register_handlers(self) -> None:
        """Register sync event handlers."""
        self.event_handlers.update({
            "session_created": [self._handle_session_created],
            "session_updated": [self._handle_session_updated],
            "session_deleted": [self._handle_session_deleted],
            "node_joined": [self._handle_node_joined],
            "node_left": [self._handle_node_left],
            "conflict_detected": [self._handle_conflict_detected],
        })
    
    async def start(self) -> None:
        """Start distributed session manager."""
        logger.info(f"Starting distributed session manager: {self.node_id}")
        
        # Register this node
        await self._register_node()
        
        # Start background tasks
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._sync_loop())
        asyncio.create_task(self._cleanup_loop())
        
        # Try to become primary if no primary exists
        await self._elect_primary()
    
    async def _register_node(self) -> None:
        """Register this node in the cluster."""
        node_info = SessionNode(
            node_id=self.node_id,
            host=self.host,
            port=self.port,
            last_seen=time.time(),
            capabilities=["read", "write", "sync", "primary"]
        )
        
        if self.redis_client:
            # Store in Redis
            await self._store_node_redis(node_info)
        else:
            # Store in memory
            with self.lock:
                self.nodes[self.node_id] = node_info
    
    async def _store_node_redis(self, node_info: SessionNode) -> None:
        """Store node information in Redis."""
        key = f"session_nodes:{node_info.node_id}"
        data = json.dumps(asdict(node_info))
        
        await asyncio.get_event_loop().run_in_executor(
            self.executor,
            lambda: self.redis_client.setex(key, 120, data)  # 2 minutes TTL
        )
    
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to maintain cluster membership."""
        while True:
            try:
                await self._send_heartbeat()
                await self._check_node_health()
                await asyncio.sleep(30)  # 30 seconds
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    async def _send_heartbeat(self) -> None:
        """Send heartbeat to cluster."""
        heartbeat_data = {
            'node_id': self.node_id,
            'timestamp': time.time(),
            'is_primary': self.is_primary,
            'session_count': len(self.local_sessions)
        }
        
        if self.redis_client:
            # Publish heartbeat
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.redis_client.publish('session_heartbeats', json.dumps(heartbeat_data))
            )
        
        self.last_heartbeat = time.time()
    
    async def _check_node_health(self) -> None:
        """Check health of other nodes and remove dead ones."""
        current_time = time.time()
        dead_nodes = []
        
        if self.redis_client:
            # Get all nodes from Redis
            pattern = "session_nodes:*"
            keys = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.redis_client.keys(pattern)
            )
            
            for key in keys:
                data = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: self.redis_client.get(key)
                )
                
                if data:
                    node_info = json.loads(data)
                    if current_time - node_info['last_seen'] > 120:  # 2 minutes
                        dead_nodes.append(node_info['node_id'])
                        
                        # Remove from Redis
                        await asyncio.get_event_loop().run_in_executor(
                            self.executor,
                            lambda: self.redis_client.delete(key)
                        )
        else:
            # Check in-memory nodes
            with self.lock:
                for node_id, node_info in self.nodes.items():
                    if current_time - node_info.last_seen > 120:
                        dead_nodes.append(node_id)
        
        # Remove dead nodes
        for node_id in dead_nodes:
            await self._handle_node_left(node_id)
    
    async def _sync_loop(self) -> None:
        """Periodic session synchronization."""
        while True:
            try:
                await self._sync_sessions()
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"Sync error: {e}")
                await asyncio.sleep(10)
    
    async def _sync_sessions(self) -> None:
        """Synchronize sessions with cluster."""
        if not self.is_primary:
            return  # Only primary syncs
        
        with self.lock:
            for session_id, session_data in self.local_sessions.items():
                if self.session_states.get(session_id) == SessionState.SYNCING:
                    continue
                
                # Mark as syncing
                self.session_states[session_id] = SessionState.SYNCING
                
                # Create sync event
                sync_event = SessionSync(
                    session_id=session_id,
                    node_id=self.node_id,
                    event_type="session_sync",
                    timestamp=time.time(),
                    data=session_data,
                    checksum=self._calculate_checksum(session_data),
                    version=int(time.time())
                )
                
                # Broadcast sync event
                await self._broadcast_sync_event(sync_event)
                
                # Mark as active
                self.session_states[session_id] = SessionState.ACTIVE
    
    async def _broadcast_sync_event(self, event: SessionSync) -> None:
        """Broadcast sync event to all nodes."""
        event_data = json.dumps(asdict(event))
        
        if self.redis_client:
            # Publish to Redis
            await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.redis_client.publish('session_sync', event_data)
            )
        else:
            # In-memory broadcasting (simplified)
            logger.debug(f"Broadcasting sync event: {event.session_id}")
    
    async def _cleanup_loop(self) -> None:
        """Cleanup expired locks and old data."""
        while True:
            try:
                await self._cleanup_expired_locks()
                await asyncio.sleep(60)  # 1 minute
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                await asyncio.sleep(10)
    
    async def _cleanup_expired_locks(self) -> None:
        """Remove expired session locks."""
        current_time = time.time()
        expired_locks = []
        
        with self.lock:
            for session_id, lock in self.session_locks.items():
                if lock.is_expired():
                    expired_locks.append(session_id)
            
            for session_id in expired_locks:
                del self.session_locks[session_id]
                logger.info(f"Expired lock removed: {session_id}")
    
    async def _elect_primary(self) -> None:
        """Elect primary node in the cluster."""
        if self.redis_client:
            # Use Redis distributed lock for election
            lock_key = "session_primary_lock"
            lock_value = f"{self.node_id}:{time.time()}"
            
            # Try to acquire lock
            acquired = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.redis_client.set(lock_key, lock_value, nx=True, ex=60)
            )
            
            if acquired:
                self.is_primary = True
                logger.info(f"Node {self.node_id} elected as primary")
                
                # Maintain primary status
                while True:
                    await asyncio.sleep(30)
                    # Refresh lock
                    await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        lambda: self.redis_client.expire(lock_key, 60)
                    )
    
    def _calculate_checksum(self, data: Dict[str, Any]) -> str:
        """Calculate checksum for session data."""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    async def create_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Create new session in distributed storage."""
        # Acquire lock
        lock = SessionLock(session_id, self.node_id)
        if not lock.acquire():
            return False
        
        try:
            with self.lock:
                self.local_sessions[session_id] = session_data
                self.session_states[session_id] = SessionState.ACTIVE
                self.session_locks[session_id] = lock
            
            # Create sync event
            sync_event = SessionSync(
                session_id=session_id,
                node_id=self.node_id,
                event_type="session_created",
                timestamp=time.time(),
                data=session_data,
                checksum=self._calculate_checksum(session_data),
                version=1
            )
            
            await self._broadcast_sync_event(sync_event)
            await self._trigger_handlers("session_created", session_id, session_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating session {session_id}: {e}")
            return False
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session in distributed storage."""
        # Acquire lock
        lock = SessionLock(session_id, self.node_id)
        if not lock.acquire():
            return False
        
        try:
            with self.lock:
                if session_id not in self.local_sessions:
                    return False
                
                # Apply updates
                self.local_sessions[session_id].update(updates)
                self.session_locks[session_id] = lock
            
            # Create sync event
            sync_event = SessionSync(
                session_id=session_id,
                node_id=self.node_id,
                event_type="session_updated",
                timestamp=time.time(),
                data=updates,
                checksum=self._calculate_checksum(self.local_sessions[session_id]),
                version=int(time.time())
            )
            
            await self._broadcast_sync_event(sync_event)
            await self._trigger_handlers("session_updated", session_id, updates)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from distributed storage."""
        # Acquire lock
        lock = SessionLock(session_id, self.node_id)
        if not lock.acquire():
            return False
        
        try:
            with self.lock:
                if session_id in self.local_sessions:
                    del self.local_sessions[session_id]
                
                if session_id in self.session_states:
                    del self.session_states[session_id]
                
                if session_id in self.session_locks:
                    del self.session_locks[session_id]
            
            # Create sync event
            sync_event = SessionSync(
                session_id=session_id,
                node_id=self.node_id,
                event_type="session_deleted",
                timestamp=time.time(),
                data={},
                checksum="",
                version=int(time.time())
            )
            
            await self._broadcast_sync_event(sync_event)
            await self._trigger_handlers("session_deleted", session_id, {})
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session from distributed storage."""
        with self.lock:
            return self.local_sessions.get(session_id)
    
    async def handle_sync_event(self, event_data: str) -> None:
        """Handle incoming sync event."""
        try:
            event = json.loads(event_data)
            sync_event = SessionSync(**event)
            
            # Ignore events from self
            if sync_event.node_id == self.node_id:
                return
            
            # Process based on event type
            if sync_event.event_type in self.event_handlers:
                for handler in self.event_handlers[sync_event.event_type]:
                    await handler(sync_event)
            
        except Exception as e:
            logger.error(f"Error handling sync event: {e}")
    
    async def _trigger_handlers(self, event_type: str, *args) -> None:
        """Trigger event handlers."""
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(*args)
                    else:
                        handler(*args)
                except Exception as e:
                    logger.error(f"Handler error for {event_type}: {e}")
    
    # Event handlers
    async def _handle_session_created(self, event: SessionSync) -> None:
        """Handle session creation event."""
        with self.lock:
            if event.session_id not in self.local_sessions:
                self.local_sessions[event.session_id] = event.data
                self.session_states[event.session_id] = SessionState.ACTIVE
                logger.info(f"Replicated session {event.session_id} from {event.node_id}")
    
    async def _handle_session_updated(self, event: SessionSync) -> None:
        """Handle session update event."""
        with self.lock:
            if event.session_id in self.local_sessions:
                # Check for conflicts
                local_checksum = self._calculate_checksum(self.local_sessions[event.session_id])
                
                if local_checksum != event.checksum:
                    # Conflict detected
                    await self._resolve_conflict(event.session_id, event)
                else:
                    # Apply updates
                    self.local_sessions[event.session_id].update(event.data)
                    logger.info(f"Updated session {event.session_id} from {event.node_id}")
    
    async def _handle_session_deleted(self, event: SessionSync) -> None:
        """Handle session deletion event."""
        with self.lock:
            if event.session_id in self.local_sessions:
                del self.local_sessions[event.session_id]
                if event.session_id in self.session_states:
                    del self.session_states[event.session_id]
                logger.info(f"Deleted session {event.session_id} from {event.node_id}")
    
    async def _handle_node_joined(self, node_id: str) -> None:
        """Handle node joining event."""
        logger.info(f"Node {node_id} joined cluster")
    
    async def _handle_node_left(self, node_id: str) -> None:
        """Handle node leaving event."""
        with self.lock:
            if node_id in self.nodes:
                del self.nodes[node_id]
                logger.info(f"Node {node_id} left cluster")
    
    async def _handle_conflict_detected(self, session_id: str, event: SessionSync) -> None:
        """Handle session conflict."""
        logger.warning(f"Conflict detected for session {session_id}")
        self.session_states[session_id] = SessionState.CONFLICT
        
        # Apply conflict resolution strategy
        if self.conflict_resolution == "last_writer_wins":
            # Keep the most recent version
            if event.version > self._get_session_version(session_id):
                with self.lock:
                    self.local_sessions[session_id] = event.data
                    self.session_states[session_id] = SessionState.ACTIVE
    
    def _get_session_version(self, session_id: str) -> int:
        """Get current session version."""
        # This would be stored with the session data
        # For now, use timestamp
        session = self.local_sessions.get(session_id)
        return int(session.get('updated_at', 0)) if session else 0
    
    async def _resolve_conflict(self, session_id: str, event: SessionSync) -> None:
        """Resolve session conflict based on strategy."""
        # Implementation depends on conflict resolution strategy
        await self._handle_conflict_detected(session_id, event)
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get cluster status information."""
        with self.lock:
            return {
                'node_id': self.node_id,
                'is_primary': self.is_primary,
                'total_nodes': len(self.nodes),
                'total_sessions': len(self.local_sessions),
                'session_states': {
                    state.value: sum(1 for s in self.session_states.values() if s == state)
                    for state in SessionState
                },
                'last_heartbeat': self.last_heartbeat,
                'storage_type': self.storage_type
            }

# Global distributed session manager
DISTRIBUTED_SESSIONS = None

def get_distributed_session_manager(**kwargs) -> DistributedSessionManager:
    """Get global distributed session manager instance."""
    global DISTRIBUTED_SESSIONS
    if DISTRIBUTED_SESSIONS is None:
        DISTRIBUTED_SESSIONS = DistributedSessionManager(**kwargs)
    return DISTRIBUTED_SESSIONS

async def init_distributed_sessions(**kwargs) -> None:
    """Initialize distributed session manager."""
    manager = get_distributed_session_manager(**kwargs)
    await manager.start()
    logger.info("Distributed session manager initialized")