"""
Advanced WebSocket/SSE connection management with pooling, heartbeat, and auto-recovery.
Optimizes real-time connection handling for better performance and reliability.
"""
import asyncio
import time
import threading
import logging
import json
import weakref
from typing import Dict, Set, Optional, Callable, Any, List
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import uuid

logger = logging.getLogger(__name__)

@dataclass
class ConnectionInfo:
    """Information about a connected client."""
    connection_id: str
    client_ip: str
    user_agent: str
    connected_at: float
    last_activity: float
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    subscriptions: Set[str] = None
    message_count: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    
    def __post_init__(self):
        if self.subscriptions is None:
            self.subscriptions = set()

@dataclass
class ConnectionStats:
    """Connection pool statistics."""
    total_connections: int = 0
    active_connections: int = 0
    peak_connections: int = 0
    total_messages_sent: int = 0
    total_bytes_sent: int = 0
    total_bytes_received: int = 0
    average_connection_duration: float = 0.0
    connection_errors: int = 0
    reconnect_count: int = 0

class ConnectionManager:
    """Advanced connection manager with pooling and optimization."""
    
    def __init__(self, max_connections: int = 10000, heartbeat_interval: float = 30.0):
        self.max_connections = max_connections
        self.heartbeat_interval = heartbeat_interval
        
        # Connection storage
        self.connections: Dict[str, ConnectionInfo] = {}
        self.session_connections: Dict[str, Set[str]] = defaultdict(set)  # session_id -> connection_ids
        self.user_connections: Dict[str, Set[str]] = defaultdict(set)  # user_id -> connection_ids
        self.subscriptions: Dict[str, Set[str]] = defaultdict(set)  # topic -> connection_ids
        
        # Message queues for broadcasting
        self.message_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Connection management
        self.connection_lock = threading.RLock()
        self.stats = ConnectionStats()
        self.start_time = time.time()
        
        # Background tasks
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.broadcast_thread = threading.Thread(target=self._broadcast_worker, daemon=True)
        
        # Start background workers
        self.heartbeat_thread.start()
        self.cleanup_thread.start()
        self.broadcast_thread.start()
        
        logger.info(f"Connection manager initialized (max: {max_connections})")
    
    def add_connection(self, connection_id: str = None, client_ip: str = None, 
                    user_agent: str = None, session_id: str = None, 
                    user_id: str = None) -> str:
        """Add a new connection to the pool."""
        if connection_id is None:
            connection_id = str(uuid.uuid4())
        
        with self.connection_lock:
            # Check connection limit
            if len(self.connections) >= self.max_connections:
                logger.warning(f"Connection limit reached: {self.max_connections}")
                raise Exception("Connection limit reached")
            
            # Create connection info
            current_time = time.time()
            connection_info = ConnectionInfo(
                connection_id=connection_id,
                client_ip=client_ip or 'unknown',
                user_agent=user_agent or 'unknown',
                connected_at=current_time,
                last_activity=current_time,
                session_id=session_id,
                user_id=user_id
            )
            
            # Add to pools
            self.connections[connection_id] = connection_info
            
            if session_id:
                self.session_connections[session_id].add(connection_id)
            
            if user_id:
                self.user_connections[user_id].add(connection_id)
            
            # Update stats
            self.stats.total_connections += 1
            self.stats.active_connections = len(self.connections)
            self.stats.peak_connections = max(self.stats.peak_connections, self.stats.active_connections)
            
            logger.info(f"Connection added: {connection_id} from {client_ip}")
            return connection_id
    
    def remove_connection(self, connection_id: str):
        """Remove a connection from the pool."""
        with self.connection_lock:
            connection_info = self.connections.pop(connection_id, None)
            if not connection_info:
                return
            
            # Remove from session/user mappings
            if connection_info.session_id:
                self.session_connections[connection_info.session_id].discard(connection_id)
                if not self.session_connections[connection_info.session_id]:
                    del self.session_connections[connection_info.session_id]
            
            if connection_info.user_id:
                self.user_connections[connection_info.user_id].discard(connection_id)
                if not self.user_connections[connection_info.user_id]:
                    del self.user_connections[connection_info.user_id]
            
            # Remove from subscriptions
            for topic in connection_info.subscriptions:
                self.subscriptions[topic].discard(connection_id)
                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]
            
            # Update stats
            self.stats.active_connections = len(self.connections)
            connection_duration = time.time() - connection_info.connected_at
            
            # Update average connection duration
            total_duration = self.stats.average_connection_duration * (self.stats.total_connections - 1)
            self.stats.average_connection_duration = (total_duration + connection_duration) / self.stats.total_connections
            
            # Add connection stats to totals
            self.stats.total_messages_sent += connection_info.message_count
            self.stats.total_bytes_sent += connection_info.bytes_sent
            self.stats.total_bytes_received += connection_info.bytes_received
            
            logger.info(f"Connection removed: {connection_id} (duration: {connection_duration:.1f}s)")
    
    def update_activity(self, connection_id: str, message_size: int = 0):
        """Update connection activity timestamp."""
        with self.connection_lock:
            connection_info = self.connections.get(connection_id)
            if connection_info:
                connection_info.last_activity = time.time()
                connection_info.message_count += 1
                connection_info.bytes_received += message_size
    
    def subscribe(self, connection_id: str, topic: str):
        """Subscribe connection to a topic."""
        with self.connection_lock:
            connection_info = self.connections.get(connection_id)
            if connection_info:
                connection_info.subscriptions.add(topic)
                self.subscriptions[topic].add(connection_id)
                logger.debug(f"Connection {connection_id} subscribed to {topic}")
    
    def unsubscribe(self, connection_id: str, topic: str):
        """Unsubscribe connection from a topic."""
        with self.connection_lock:
            connection_info = self.connections.get(connection_id)
            if connection_info:
                connection_info.subscriptions.discard(topic)
                self.subscriptions[topic].discard(connection_id)
                
                if not self.subscriptions[topic]:
                    del self.subscriptions[topic]
                
                logger.debug(f"Connection {connection_id} unsubscribed from {topic}")
    
    def broadcast_to_topic(self, topic: str, message: Any, exclude_connections: Set[str] = None):
        """Broadcast message to all subscribers of a topic."""
        with self.connection_lock:
            subscribers = self.subscriptions.get(topic, set()).copy()
            
            if exclude_connections:
                subscribers -= exclude_connections
            
            # Queue message for broadcasting
            self.message_queues[topic].append({
                'message': message,
                'subscribers': subscribers,
                'timestamp': time.time()
            })
    
    def broadcast_to_session(self, session_id: str, message: Any, exclude_connection: str = None):
        """Broadcast message to all connections in a session."""
        with self.connection_lock:
            connection_ids = self.session_connections.get(session_id, set()).copy()
            
            if exclude_connection:
                connection_ids.discard(exclude_connection)
            
            # Queue message for each connection
            for connection_id in connection_ids:
                self.message_queues[f"connection:{connection_id}"].append({
                    'message': message,
                    'connection_id': connection_id,
                    'timestamp': time.time()
                })
    
    def broadcast_to_user(self, user_id: str, message: Any, exclude_connection: str = None):
        """Broadcast message to all connections for a user."""
        with self.connection_lock:
            connection_ids = self.user_connections.get(user_id, set()).copy()
            
            if exclude_connection:
                connection_ids.discard(exclude_connection)
            
            # Queue message for each connection
            for connection_id in connection_ids:
                self.message_queues[f"connection:{connection_id}"].append({
                    'message': message,
                    'connection_id': connection_id,
                    'timestamp': time.time()
                })
    
    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get information about a connection."""
        with self.connection_lock:
            return self.connections.get(connection_id)
    
    def get_session_connections(self, session_id: str) -> List[str]:
        """Get all connection IDs for a session."""
        with self.connection_lock:
            return list(self.session_connections.get(session_id, set()))
    
    def get_user_connections(self, user_id: str) -> List[str]:
        """Get all connection IDs for a user."""
        with self.connection_lock:
            return list(self.user_connections.get(user_id, set()))
    
    def get_connection_stats(self) -> ConnectionStats:
        """Get current connection statistics."""
        with self.connection_lock:
            stats = ConnectionStats(
                total_connections=self.stats.total_connections,
                active_connections=self.stats.active_connections,
                peak_connections=self.stats.peak_connections,
                total_messages_sent=self.stats.total_messages_sent,
                total_bytes_sent=self.stats.total_bytes_sent,
                total_bytes_received=self.stats.total_bytes_received,
                average_connection_duration=self.stats.average_connection_duration,
                connection_errors=self.stats.connection_errors,
                reconnect_count=self.stats.reconnect_count
            )
            
            # Add real-time stats
            stats.uptime = time.time() - self.start_time
            stats.subscriptions_by_topic = {
                topic: len(connections) 
                for topic, connections in self.subscriptions.items()
            }
            stats.connections_by_session = {
                session_id: len(connections)
                for session_id, connections in self.session_connections.items()
            }
            
            return stats
    
    def _heartbeat_worker(self):
        """Background worker for connection heartbeat."""
        while self.running:
            try:
                current_time = time.time()
                stale_connections = []
                
                with self.connection_lock:
                    for connection_id, connection_info in self.connections.items():
                        # Check if connection is stale
                        if current_time - connection_info.last_activity > self.heartbeat_interval * 2:
                            stale_connections.append(connection_id)
                
                # Remove stale connections
                for connection_id in stale_connections:
                    self.remove_connection(connection_id)
                    logger.info(f"Removed stale connection: {connection_id}")
                
                # Send heartbeat to active connections
                heartbeat_msg = {
                    'type': 'heartbeat',
                    'timestamp': current_time
                }
                
                self.broadcast_to_topic('system', heartbeat_msg)
                
                time.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Heartbeat worker error: {e}")
                time.sleep(10.0)
    
    def _cleanup_worker(self):
        """Background worker for cleanup tasks."""
        while self.running:
            try:
                time.sleep(60.0)  # Run every minute
                
                current_time = time.time()
                
                with self.connection_lock:
                    # Clean empty message queues
                    empty_topics = [
                        topic for topic, queue in self.message_queues.items()
                        if not queue
                    ]
                    for topic in empty_topics:
                        del self.message_queues[topic]
                    
                    # Clean old connection data (optional - for very long running servers)
                    # This would require additional logic to track connection history
                    
            except Exception as e:
                logger.error(f"Cleanup worker error: {e}")
    
    def _broadcast_worker(self):
        """Background worker for message broadcasting."""
        while self.running:
            try:
                # Process all message queues
                all_topics = list(self.message_queues.keys())
                
                for topic in all_topics:
                    queue = self.message_queues[topic]
                    
                    while queue:
                        message_data = queue.popleft()
                        
                        try:
                            if topic.startswith('connection:'):
                                # Direct connection message
                                connection_id = message_data['connection_id']
                                self._send_to_connection(connection_id, message_data['message'])
                            else:
                                # Topic broadcast
                                subscribers = message_data['subscribers']
                                message = message_data['message']
                                
                                for subscriber_id in subscribers:
                                    self._send_to_connection(subscriber_id, message)
                        
                        except Exception as e:
                            logger.error(f"Error broadcasting message: {e}")
                
                time.sleep(0.01)  # 10ms between batches
                
            except Exception as e:
                logger.error(f"Broadcast worker error: {e}")
                time.sleep(1.0)
    
    def _send_to_connection(self, connection_id: str, message: Any):
        """Send message to specific connection (to be implemented by subclasses)."""
        # This would be implemented by the actual server handler
        # For now, just update stats
        with self.connection_lock:
            connection_info = self.connections.get(connection_id)
            if connection_info:
                message_size = len(json.dumps(message).encode('utf-8'))
                connection_info.bytes_sent += message_size
    
    def shutdown(self):
        """Gracefully shutdown connection manager."""
        logger.info("Shutting down connection manager...")
        
        self.running = False
        
        # Wait for background threads
        for thread in [self.heartbeat_thread, self.cleanup_thread, self.broadcast_thread]:
            if thread.is_alive():
                thread.join(timeout=5.0)
        
        # Close all connections
        with self.connection_lock:
            connection_ids = list(self.connections.keys())
            for connection_id in connection_ids:
                self.remove_connection(connection_id)
        
        logger.info("Connection manager shutdown complete")

# Global connection manager
_connection_manager: Optional[ConnectionManager] = None

def initialize_connection_manager(max_connections: int = 10000, heartbeat_interval: float = 30.0):
    """Initialize global connection manager."""
    global _connection_manager
    _connection_manager = ConnectionManager(max_connections, heartbeat_interval)
    logger.info("Global connection manager initialized")

def add_connection(**kwargs) -> str:
    """Add connection through global manager."""
    if not _connection_manager:
        raise RuntimeError("Connection manager not initialized")
    return _connection_manager.add_connection(**kwargs)

def remove_connection(connection_id: str):
    """Remove connection through global manager."""
    if _connection_manager:
        _connection_manager.remove_connection(connection_id)

def subscribe(connection_id: str, topic: str):
    """Subscribe through global manager."""
    if _connection_manager:
        _connection_manager.subscribe(connection_id, topic)

def unsubscribe(connection_id: str, topic: str):
    """Unsubscribe through global manager."""
    if _connection_manager:
        _connection_manager.unsubscribe(connection_id, topic)

def broadcast_to_topic(topic: str, message: Any, exclude_connections: Set[str] = None):
    """Broadcast through global manager."""
    if _connection_manager:
        _connection_manager.broadcast_to_topic(topic, message, exclude_connections)

def broadcast_to_session(session_id: str, message: Any, exclude_connection: str = None):
    """Broadcast to session through global manager."""
    if _connection_manager:
        _connection_manager.broadcast_to_session(session_id, message, exclude_connection)

def get_connection_stats() -> ConnectionStats:
    """Get connection statistics."""
    if _connection_manager:
        return _connection_manager.get_connection_stats()
    return ConnectionStats()

def shutdown_connection_manager():
    """Shutdown connection manager."""
    if _connection_manager:
        _connection_manager.shutdown()