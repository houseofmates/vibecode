"""
Hermes Web UI -- WebSocket real-time communication manager.
Provides bidirectional real-time communication with authentication and room management.
"""
import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Set, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.exceptions import ConnectionClosed

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """WebSocket message types."""
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    HEARTBEAT = "heartbeat"
    SESSION_UPDATE = "session_update"
    TERMINAL_OUTPUT = "terminal_output"
    TERMINAL_INPUT = "terminal_input"
    SWARM_UPDATE = "swarm_update"
    CHAT_MESSAGE = "chat_message"
    NOTIFICATION = "notification"
    ERROR = "error"
    AUTH = "auth"
    ROOM_JOIN = "room_join"
    ROOM_LEAVE = "room_leave"
    ROOM_MESSAGE = "room_message"

@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    type: MessageType
    data: Dict[str, Any]
    timestamp: float = None
    message_id: str = None
    room: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())

@dataclass
class ClientConnection:
    """Client connection information."""
    websocket: WebSocketServerProtocol
    client_id: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    rooms: Set[str] = None
    last_heartbeat: float = None
    authenticated: bool = False
    permissions: List[str] = None
    
    def __post_init__(self):
        if self.rooms is None:
            self.rooms = set()
        if self.permissions is None:
            self.permissions = []
        if self.last_heartbeat is None:
            self.last_heartbeat = time.time()

class Room:
    """WebSocket room for group communication."""
    
    def __init__(self, name: str, max_clients: int = 100):
        self.name = name
        self.max_clients = max_clients
        self.clients: Set[str] = set()
        self.created_at = time.time()
        self.metadata: Dict[str, Any] = {}
    
    def add_client(self, client_id: str) -> bool:
        """Add client to room."""
        if len(self.clients) >= self.max_clients:
            return False
        self.clients.add(client_id)
        return True
    
    def remove_client(self, client_id: str) -> bool:
        """Remove client from room."""
        if client_id in self.clients:
            self.clients.remove(client_id)
            return True
        return False
    
    def get_client_count(self) -> int:
        """Get number of clients in room."""
        return len(self.clients)

class WebSocketManager:
    """Manages WebSocket connections and rooms."""
    
    def __init__(self):
        self.clients: Dict[str, ClientConnection] = {}
        self.rooms: Dict[str, Room] = {}
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        self.auth_handler: Optional[Callable] = None
        self.lock = asyncio.Lock()
        
        # Register default handlers
        self.register_handler(MessageType.HEARTBEAT, self._handle_heartbeat)
        self.register_handler(MessageType.ROOM_JOIN, self._handle_room_join)
        self.register_handler(MessageType.ROOM_LEAVE, self._handle_room_leave)
        self.register_handler(MessageType.AUTH, self._handle_auth)
    
    async def register_client(self, websocket: WebSocketServerProtocol, path: str) -> str:
        """Register new WebSocket client."""
        client_id = str(uuid.uuid4())
        client = ClientConnection(
            websocket=websocket,
            client_id=client_id
        )
        
        async with self.lock:
            self.clients[client_id] = client
        
        logger.info(f"Client {client_id} connected from {websocket.remote_address}")
        
        # Send welcome message
        await self.send_to_client(client_id, WebSocketMessage(
            type=MessageType.CONNECT,
            data={'client_id': client_id, 'server_time': time.time()}
        ))
        
        return client_id
    
    async def unregister_client(self, client_id: str) -> None:
        """Unregister WebSocket client."""
        async with self.lock:
            if client_id in self.clients:
                client = self.clients[client_id]
                
                # Remove from all rooms
                for room_name in list(client.rooms):
                    await self.leave_room(client_id, room_name)
                
                # Remove client
                del self.clients[client_id]
                
                logger.info(f"Client {client_id} disconnected")
    
    async def send_to_client(self, client_id: str, message: WebSocketMessage) -> bool:
        """Send message to specific client."""
        if client_id not in self.clients:
            return False
        
        client = self.clients[client_id]
        try:
            await client.websocket.send(json.dumps(asdict(message)))
            return True
        except ConnectionClosed:
            await self.unregister_client(client_id)
            return False
        except Exception as e:
            logger.error(f"Error sending to client {client_id}: {e}")
            return False
    
    async def send_to_room(self, room_name: str, message: WebSocketMessage, 
                          exclude_client: str = None) -> int:
        """Send message to all clients in room."""
        if room_name not in self.rooms:
            return 0
        
        room = self.rooms[room_name]
        sent_count = 0
        
        for client_id in room.clients:
            if exclude_client and client_id == exclude_client:
                continue
            
            if await self.send_to_client(client_id, message):
                sent_count += 1
        
        return sent_count
    
    async def broadcast(self, message: WebSocketMessage, 
                      authenticated_only: bool = False) -> int:
        """Broadcast message to all clients."""
        sent_count = 0
        
        for client_id, client in self.clients.items():
            if authenticated_only and not client.authenticated:
                continue
            
            if await self.send_to_client(client_id, message):
                sent_count += 1
        
        return sent_count
    
    async def join_room(self, client_id: str, room_name: str, 
                      password: str = None) -> bool:
        """Join client to room."""
        async with self.lock:
            if client_id not in self.clients:
                return False
            
            client = self.clients[client_id]
            
            # Create room if doesn't exist
            if room_name not in self.rooms:
                self.rooms[room_name] = Room(room_name)
            
            room = self.rooms[room_name]
            
            # Add client to room
            if room.add_client(client_id):
                client.rooms.add(room_name)
                
                # Notify room
                await self.send_to_room(room_name, WebSocketMessage(
                    type=MessageType.ROOM_MESSAGE,
                    data={
                        'event': 'user_joined',
                        'client_id': client_id,
                        'user_id': client.user_id,
                        'room_size': room.get_client_count()
                    }
                ))
                
                logger.info(f"Client {client_id} joined room {room_name}")
                return True
            else:
                await self.send_to_client(client_id, WebSocketMessage(
                    type=MessageType.ERROR,
                    data={'message': f'Room {room_name} is full'}
                ))
                return False
    
    async def leave_room(self, client_id: str, room_name: str) -> bool:
        """Remove client from room."""
        async with self.lock:
            if client_id not in self.clients:
                return False
            
            client = self.clients[client_id]
            
            if room_name not in self.rooms:
                return False
            
            room = self.rooms[room_name]
            
            if room.remove_client(client_id):
                client.rooms.discard(room_name)
                
                # Notify room
                await self.send_to_room(room_name, WebSocketMessage(
                    type=MessageType.ROOM_MESSAGE,
                    data={
                        'event': 'user_left',
                        'client_id': client_id,
                        'user_id': client.user_id,
                        'room_size': room.get_client_count()
                    }
                ), exclude_client=client_id)
                
                # Clean up empty rooms
                if room.get_client_count() == 0:
                    del self.rooms[room_name]
                    logger.info(f"Room {room_name} deleted (empty)")
                
                logger.info(f"Client {client_id} left room {room_name}")
                return True
            
            return False
    
    def register_handler(self, message_type: MessageType, 
                       handler: Callable) -> None:
        """Register message handler."""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        self.message_handlers[message_type].append(handler)
    
    def set_auth_handler(self, handler: Callable) -> None:
        """Set authentication handler."""
        self.auth_handler = handler
    
    async def handle_message(self, client_id: str, raw_message: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            data = json.loads(raw_message)
            message_type = MessageType(data.get('type'))
            message_data = data.get('data', {})
            
            # Create message object
            message = WebSocketMessage(
                type=message_type,
                data=message_data,
                message_id=data.get('message_id'),
                room=data.get('room')
            )
            
            # Check if handler exists
            if message_type in self.message_handlers:
                for handler in self.message_handlers[message_type]:
                    try:
                        await handler(client_id, message)
                    except Exception as e:
                        logger.error(f"Handler error for {message_type}: {e}")
            else:
                logger.warning(f"No handler for message type: {message_type}")
        
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON from client {client_id}: {raw_message}")
        except Exception as e:
            logger.error(f"Error handling message from {client_id}: {e}")
    
    async def _handle_heartbeat(self, client_id: str, message: WebSocketMessage) -> None:
        """Handle heartbeat message."""
        async with self.lock:
            if client_id in self.clients:
                self.clients[client_id].last_heartbeat = time.time()
        
        # Send heartbeat response
        await self.send_to_client(client_id, WebSocketMessage(
            type=MessageType.HEARTBEAT,
            data={'timestamp': time.time()}
        ))
    
    async def _handle_room_join(self, client_id: str, message: WebSocketMessage) -> None:
        """Handle room join request."""
        room_name = message.data.get('room')
        password = message.data.get('password')
        
        if room_name:
            await self.join_room(client_id, room_name, password)
    
    async def _handle_room_leave(self, client_id: str, message: WebSocketMessage) -> None:
        """Handle room leave request."""
        room_name = message.data.get('room')
        
        if room_name:
            await self.leave_room(client_id, room_name)
    
    async def _handle_auth(self, client_id: str, message: WebSocketMessage) -> None:
        """Handle authentication request."""
        if not self.auth_handler:
            return
        
        try:
            auth_result = await self.auth_handler(
                client_id, 
                message.data.get('token'),
                message.data.get('credentials')
            )
            
            async with self.lock:
                if client_id in self.clients:
                    client = self.clients[client_id]
                    client.authenticated = auth_result.get('success', False)
                    client.user_id = auth_result.get('user_id')
                    client.permissions = auth_result.get('permissions', [])
            
            # Send auth response
            await self.send_to_client(client_id, WebSocketMessage(
                type=MessageType.AUTH,
                data=auth_result
            ))
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            await self.send_to_client(client_id, WebSocketMessage(
                type=MessageType.ERROR,
                data={'message': 'Authentication failed'}
            ))
    
    async def start_heartbeat_monitor(self, interval: int = 30) -> None:
        """Monitor client heartbeats and disconnect inactive clients."""
        while True:
            try:
                current_time = time.time()
                inactive_clients = []
                
                async with self.lock:
                    for client_id, client in self.clients.items():
                        if current_time - client.last_heartbeat > interval * 2:
                            inactive_clients.append(client_id)
                
                # Disconnect inactive clients
                for client_id in inactive_clients:
                    logger.info(f"Disconnecting inactive client: {client_id}")
                    await self.unregister_client(client_id)
                
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Heartbeat monitor error: {e}")
                await asyncio.sleep(5)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket manager statistics."""
        async with self.lock:
            return {
                'total_clients': len(self.clients),
                'authenticated_clients': sum(1 for c in self.clients.values() if c.authenticated),
                'total_rooms': len(self.rooms),
                'room_details': {
                    name: {
                        'client_count': room.get_client_count(),
                        'max_clients': room.max_clients,
                        'created_at': room.created_at
                    }
                    for name, room in self.rooms.items()
                }
            }

# Global WebSocket manager
WEBSOCKET_MANAGER = WebSocketManager()

def get_websocket_manager() -> WebSocketManager:
    """Get global WebSocket manager instance."""
    return WEBSOCKET_MANAGER

async def websocket_handler(websocket: WebSocketServerProtocol, path: str) -> None:
    """Main WebSocket handler."""
    manager = get_websocket_manager()
    client_id = await manager.register_client(websocket, path)
    
    try:
        async for message in websocket:
            await manager.handle_message(client_id, message)
    except ConnectionClosed:
        logger.info(f"Client {client_id} connection closed")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        await manager.unregister_client(client_id)

# Helper functions for common operations
async def notify_session_update(session_id: str, update_data: Dict[str, Any]) -> None:
    """Notify clients about session update."""
    manager = get_websocket_manager()
    await manager.send_to_room(f"session_{session_id}", WebSocketMessage(
        type=MessageType.SESSION_UPDATE,
        data=update_data
    ))

async def notify_terminal_output(terminal_id: str, output: str) -> None:
    """Send terminal output to subscribed clients."""
    manager = get_websocket_manager()
    await manager.send_to_room(f"terminal_{terminal_id}", WebSocketMessage(
        type=MessageType.TERMINAL_OUTPUT,
        data={'terminal_id': terminal_id, 'output': output}
    ))

async def notify_swarm_update(swarm_id: str, update_data: Dict[str, Any]) -> None:
    """Notify clients about swarm update."""
    manager = get_websocket_manager()
    await manager.send_to_room(f"swarm_{swarm_id}", WebSocketMessage(
        type=MessageType.SWARM_UPDATE,
        data={'swarm_id': swarm_id, **update_data}
    ))

async def send_notification(user_id: str, title: str, message: str, 
                          notification_type: str = "info") -> None:
    """Send notification to specific user."""
    manager = get_websocket_manager()
    
    # Find all clients for this user
    for client_id, client in manager.clients.items():
        if client.user_id == user_id:
            await manager.send_to_client(client_id, WebSocketMessage(
                type=MessageType.NOTIFICATION,
                data={
                    'title': title,
                    'message': message,
                    'type': notification_type,
                    'timestamp': time.time()
                }
            ))