"""
WebSocket Communication Server - Real-Time Agent Coordination
==========================================================
Ultra-low latency communication backbone for the Unified AI Command System
enabling real-time regime broadcasts, alert coordination, and mesh networking.
"""
import asyncio
import websockets
import json
import logging
from datetime import datetime
from typing import Dict, Set, Any, Optional, List
from dataclasses import dataclass, asdict
import uuid
import ssl
import hashlib
import hmac

# Import unified system components
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from unified_system.communication.protocol import UnifiedMessage, MessageType, CommandType

logger = logging.getLogger(__name__)

@dataclass
class WebSocketClient:
    """Represents a connected WebSocket client."""
    client_id: str
    agent_id: str
    websocket: websockets.WebSocketServerProtocol
    connected_at: datetime
    last_heartbeat: datetime
    subscriptions: Set[str]
    metadata: Dict[str, Any]

@dataclass
class RealtimeMessage:
    """Real-time message for WebSocket communication."""
    message_id: str
    message_type: str  # 'regime_change', 'alert', 'heartbeat', 'command', 'broadcast'
    source_agent: str
    target_agents: List[str]  # Empty list means broadcast to all
    data: Dict[str, Any]
    priority: str  # 'low', 'normal', 'high', 'critical'
    timestamp: datetime
    expires_at: Optional[datetime] = None

class WebSocketServer:
    """WebSocket server for real-time agent communication."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize WebSocket server."""
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 8765)
        self.secret_key = config.get('secret_key', 'unified_ai_secret_2024')
        
        # Client management
        self.clients: Dict[str, WebSocketClient] = {}
        self.agent_to_client: Dict[str, str] = {}  # agent_id -> client_id mapping
        
        # Message routing
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.subscription_channels: Dict[str, Set[str]] = {}  # channel -> set of client_ids
        
        # Statistics
        self.stats = {
            'connections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'broadcasts': 0,
            'errors': 0,
            'uptime_start': datetime.now()
        }
        
        # Server state
        self.server = None
        self.running = False
        self.message_processor_task = None
    
    async def start_server(self) -> None:
        """Start the WebSocket server."""
        try:
            logger.info(f"[WEBSOCKET] Starting server on {self.host}:{self.port}")
            
            # Start message processor
            self.message_processor_task = asyncio.create_task(self._process_message_queue())
            
            # Start WebSocket server
            self.server = await websockets.serve(
                self._handle_client_connection,
                self.host,
                self.port,
                ping_interval=30,
                ping_timeout=10,
                close_timeout=10
            )
            
            self.running = True
            logger.info("[WEBSOCKET] Server started successfully")
            
            # Start periodic tasks
            asyncio.create_task(self._heartbeat_monitor())
            asyncio.create_task(self._cleanup_expired_messages())
            
        except Exception as e:
            logger.error(f"[WEBSOCKET] Failed to start server: {e}")
            raise
    
    async def stop_server(self) -> None:
        """Stop the WebSocket server."""
        try:
            self.running = False
            
            # Close all client connections
            if self.clients:
                await asyncio.gather(
                    *[self._disconnect_client(client_id) for client_id in list(self.clients.keys())],
                    return_exceptions=True
                )
            
            # Stop message processor
            if self.message_processor_task:
                self.message_processor_task.cancel()
                try:
                    await self.message_processor_task
                except asyncio.CancelledError:
                    pass
            
            # Stop server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            logger.info("[WEBSOCKET] Server stopped")
            
        except Exception as e:
            logger.error(f"[WEBSOCKET] Error stopping server: {e}")
    
    async def _handle_client_connection(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """Handle new client connection."""
        client_id = str(uuid.uuid4())
        client = None
        
        try:
            # Wait for authentication message
            auth_message = await asyncio.wait_for(websocket.recv(), timeout=30)
            auth_data = json.loads(auth_message)
            
            # Validate authentication
            if not self._validate_auth(auth_data):
                await websocket.send(json.dumps({
                    'type': 'auth_error',
                    'message': 'Authentication failed'
                }))
                return
            
            # Create client record
            agent_id = auth_data['agent_id']
            client = WebSocketClient(
                client_id=client_id,
                agent_id=agent_id,
                websocket=websocket,
                connected_at=datetime.now(),
                last_heartbeat=datetime.now(),
                subscriptions=set(auth_data.get('subscriptions', [])),
                metadata=auth_data.get('metadata', {})
            )
            
            # Register client
            self.clients[client_id] = client
            self.agent_to_client[agent_id] = client_id
            self.stats['connections'] += 1
            
            # Send authentication success
            await websocket.send(json.dumps({
                'type': 'auth_success',
                'client_id': client_id,
                'server_time': datetime.now().isoformat()
            }))
            
            logger.info(f"[WEBSOCKET] Agent {agent_id} connected as {client_id}")
            
            # Handle client messages
            async for message in websocket:
                try:
                    await self._handle_client_message(client, message)
                except Exception as e:
                    logger.error(f"[WEBSOCKET] Error handling message from {client_id}: {e}")
                    self.stats['errors'] += 1
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[WEBSOCKET] Client {client_id} disconnected")
        except asyncio.TimeoutError:
            logger.warning(f"[WEBSOCKET] Client {client_id} authentication timeout")
        except Exception as e:
            logger.error(f"[WEBSOCKET] Connection error for {client_id}: {e}")
            self.stats['errors'] += 1
        finally:
            # Clean up client
            if client:
                await self._disconnect_client(client_id)
    
    def _validate_auth(self, auth_data: Dict[str, Any]) -> bool:
        """Validate client authentication."""
        try:
            required_fields = ['agent_id', 'timestamp', 'signature']
            if not all(field in auth_data for field in required_fields):
                return False
            
            # Verify signature
            message = f"{auth_data['agent_id']}:{auth_data['timestamp']}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(auth_data['signature'], expected_signature)
            
        except Exception as e:
            logger.error(f"[WEBSOCKET] Auth validation error: {e}")
            return False
    
    async def _handle_client_message(self, client: WebSocketClient, message: str):
        """Handle message from client."""
        try:
            data = json.loads(message)
            message_type = data.get('type')
            
            if message_type == 'heartbeat':
                await self._handle_heartbeat(client, data)
            elif message_type == 'subscribe':
                await self._handle_subscription(client, data)
            elif message_type == 'unsubscribe':
                await self._handle_unsubscription(client, data)
            elif message_type == 'broadcast':
                await self._handle_broadcast(client, data)
            elif message_type == 'direct_message':
                await self._handle_direct_message(client, data)
            elif message_type == 'regime_change':
                await self._handle_regime_change(client, data)
            elif message_type == 'alert':
                await self._handle_alert(client, data)
            else:
                logger.warning(f"[WEBSOCKET] Unknown message type from {client.client_id}: {message_type}")
            
            self.stats['messages_received'] += 1
            
        except json.JSONDecodeError:
            logger.error(f"[WEBSOCKET] Invalid JSON from {client.client_id}")
        except Exception as e:
            logger.error(f"[WEBSOCKET] Error handling message from {client.client_id}: {e}")
    
    async def _handle_heartbeat(self, client: WebSocketClient, data: Dict[str, Any]):
        """Handle heartbeat message."""
        client.last_heartbeat = datetime.now()
        
        # Send heartbeat response
        response = {
            'type': 'heartbeat_ack',
            'server_time': datetime.now().isoformat(),
            'client_id': client.client_id
        }
        
        await client.websocket.send(json.dumps(response))
    
    async def _handle_subscription(self, client: WebSocketClient, data: Dict[str, Any]):
        """Handle channel subscription."""
        channels = data.get('channels', [])
        
        for channel in channels:
            client.subscriptions.add(channel)
            
            if channel not in self.subscription_channels:
                self.subscription_channels[channel] = set()
            self.subscription_channels[channel].add(client.client_id)
        
        logger.info(f"[WEBSOCKET] {client.agent_id} subscribed to {channels}")
        
        # Send subscription confirmation
        response = {
            'type': 'subscription_ack',
            'channels': channels,
            'total_subscriptions': len(client.subscriptions)
        }
        
        await client.websocket.send(json.dumps(response))
    
    async def _handle_unsubscription(self, client: WebSocketClient, data: Dict[str, Any]):
        """Handle channel unsubscription."""
        channels = data.get('channels', [])
        
        for channel in channels:
            client.subscriptions.discard(channel)
            
            if channel in self.subscription_channels:
                self.subscription_channels[channel].discard(client.client_id)
                
                # Clean up empty channels
                if not self.subscription_channels[channel]:
                    del self.subscription_channels[channel]
        
        logger.info(f"[WEBSOCKET] {client.agent_id} unsubscribed from {channels}")
    
    async def _handle_broadcast(self, client: WebSocketClient, data: Dict[str, Any]):
        """Handle broadcast message."""
        broadcast_message = RealtimeMessage(
            message_id=str(uuid.uuid4()),
            message_type='broadcast',
            source_agent=client.agent_id,
            target_agents=[],  # Broadcast to all
            data=data.get('data', {}),
            priority=data.get('priority', 'normal'),
            timestamp=datetime.now(),
            expires_at=None
        )
        
        await self.message_queue.put(broadcast_message)
        self.stats['broadcasts'] += 1
    
    async def _handle_direct_message(self, client: WebSocketClient, data: Dict[str, Any]):
        """Handle direct message to specific agent."""
        target_agents = data.get('target_agents', [])
        
        direct_message = RealtimeMessage(
            message_id=str(uuid.uuid4()),
            message_type='direct_message',
            source_agent=client.agent_id,
            target_agents=target_agents,
            data=data.get('data', {}),
            priority=data.get('priority', 'normal'),
            timestamp=datetime.now(),
            expires_at=None
        )
        
        await self.message_queue.put(direct_message)
    
    async def _handle_regime_change(self, client: WebSocketClient, data: Dict[str, Any]):
        """Handle regime change broadcast."""
        regime_message = RealtimeMessage(
            message_id=str(uuid.uuid4()),
            message_type='regime_change',
            source_agent=client.agent_id,
            target_agents=[],  # Broadcast to all
            data={
                'symbol': data.get('symbol'),
                'timeframe': data.get('timeframe'),
                'old_regime': data.get('old_regime'),
                'new_regime': data.get('new_regime'),
                'confidence': data.get('confidence'),
                'timestamp': datetime.now().isoformat()
            },
            priority='high',
            timestamp=datetime.now(),
            expires_at=None
        )
        
        await self.message_queue.put(regime_message)
        logger.info(f"[WEBSOCKET] Regime change broadcast from {client.agent_id}: {data.get('symbol')} {data.get('old_regime')} -> {data.get('new_regime')}")
    
    async def _handle_alert(self, client: WebSocketClient, data: Dict[str, Any]):
        """Handle alert message."""
        alert_message = RealtimeMessage(
            message_id=str(uuid.uuid4()),
            message_type='alert',
            source_agent=client.agent_id,
            target_agents=data.get('target_agents', []),
            data={
                'alert_type': data.get('alert_type'),
                'symbol': data.get('symbol'),
                'message': data.get('message'),
                'severity': data.get('severity', 'medium'),
                'action_required': data.get('action_required', False),
                'timestamp': datetime.now().isoformat()
            },
            priority=data.get('priority', 'normal'),
            timestamp=datetime.now(),
            expires_at=None
        )
        
        await self.message_queue.put(alert_message)
        logger.info(f"[WEBSOCKET] Alert from {client.agent_id}: {data.get('alert_type')} - {data.get('message')}")
    
    async def _process_message_queue(self):
        """Process messages from the queue."""
        while self.running:
            try:
                # Get message from queue
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                # Route message to appropriate clients
                await self._route_message(message)
                
                # Mark task as done
                self.message_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"[WEBSOCKET] Message processing error: {e}")
    
    async def _route_message(self, message: RealtimeMessage):
        """Route message to appropriate clients."""
        try:
            target_clients = []
            
            if not message.target_agents:
                # Broadcast to all clients
                target_clients = list(self.clients.values())
            else:
                # Send to specific agents
                for agent_id in message.target_agents:
                    if agent_id in self.agent_to_client:
                        client_id = self.agent_to_client[agent_id]
                        if client_id in self.clients:
                            target_clients.append(self.clients[client_id])
            
            # Send message to target clients
            message_data = {
                'type': message.message_type,
                'message_id': message.message_id,
                'source_agent': message.source_agent,
                'data': message.data,
                'priority': message.priority,
                'timestamp': message.timestamp.isoformat()
            }
            
            message_json = json.dumps(message_data)
            
            # Send to all target clients
            send_tasks = []
            for client in target_clients:
                if client.websocket.open:
                    send_tasks.append(client.websocket.send(message_json))
            
            if send_tasks:
                await asyncio.gather(*send_tasks, return_exceptions=True)
                self.stats['messages_sent'] += len(send_tasks)
            
        except Exception as e:
            logger.error(f"[WEBSOCKET] Message routing error: {e}")
    
    async def _disconnect_client(self, client_id: str):
        """Disconnect and clean up client."""
        try:
            if client_id in self.clients:
                client = self.clients[client_id]
                
                # Remove from agent mapping
                if client.agent_id in self.agent_to_client:
                    del self.agent_to_client[client.agent_id]
                
                # Remove from subscriptions
                for channel in client.subscriptions:
                    if channel in self.subscription_channels:
                        self.subscription_channels[channel].discard(client_id)
                        if not self.subscription_channels[channel]:
                            del self.subscription_channels[channel]
                
                # Close WebSocket connection
                if not client.websocket.closed:
                    await client.websocket.close()
                
                # Remove client record
                del self.clients[client_id]
                
                logger.info(f"[WEBSOCKET] Client {client_id} ({client.agent_id}) disconnected")
                
        except Exception as e:
            logger.error(f"[WEBSOCKET] Error disconnecting client {client_id}: {e}")
    
    async def _heartbeat_monitor(self):
        """Monitor client heartbeats and disconnect stale connections."""
        while self.running:
            try:
                current_time = datetime.now()
                stale_clients = []
                
                for client_id, client in self.clients.items():
                    # Check if client hasn't sent heartbeat in 60 seconds
                    if (current_time - client.last_heartbeat).total_seconds() > 60:
                        stale_clients.append(client_id)
                
                # Disconnect stale clients
                for client_id in stale_clients:
                    logger.warning(f"[WEBSOCKET] Disconnecting stale client {client_id}")
                    await self._disconnect_client(client_id)
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"[WEBSOCKET] Heartbeat monitor error: {e}")
    
    async def _cleanup_expired_messages(self):
        """Clean up expired messages (placeholder for future implementation)."""
        while self.running:
            try:
                # Future: Clean up expired messages from persistent storage
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"[WEBSOCKET] Message cleanup error: {e}")
    
    async def broadcast_regime_change(self, agent_id: str, symbol: str, timeframe: str, 
                                    old_regime: str, new_regime: str, confidence: float):
        """Broadcast regime change to all connected agents."""
        message = RealtimeMessage(
            message_id=str(uuid.uuid4()),
            message_type='regime_change',
            source_agent=agent_id,
            target_agents=[],
            data={
                'symbol': symbol,
                'timeframe': timeframe,
                'old_regime': old_regime,
                'new_regime': new_regime,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat()
            },
            priority='high',
            timestamp=datetime.now()
        )
        
        await self.message_queue.put(message)
    
    async def send_alert(self, source_agent: str, target_agents: List[str], 
                        alert_type: str, symbol: str, message: str, 
                        severity: str = 'medium', priority: str = 'normal'):
        """Send alert to specific agents."""
        alert_message = RealtimeMessage(
            message_id=str(uuid.uuid4()),
            message_type='alert',
            source_agent=source_agent,
            target_agents=target_agents,
            data={
                'alert_type': alert_type,
                'symbol': symbol,
                'message': message,
                'severity': severity,
                'timestamp': datetime.now().isoformat()
            },
            priority=priority,
            timestamp=datetime.now()
        )
        
        await self.message_queue.put(alert_message)
    
    def get_server_status(self) -> Dict[str, Any]:
        """Get current server status."""
        uptime = datetime.now() - self.stats['uptime_start']
        
        return {
            'running': self.running,
            'host': self.host,
            'port': self.port,
            'connected_clients': len(self.clients),
            'active_agents': list(self.agent_to_client.keys()),
            'subscription_channels': list(self.subscription_channels.keys()),
            'stats': {
                **self.stats,
                'uptime_seconds': uptime.total_seconds(),
                'uptime_formatted': str(uptime).split('.')[0]
            },
            'message_queue_size': self.message_queue.qsize()
        }

# Global WebSocket server instance
_websocket_server = None

def initialize_websocket_server(config: Dict[str, Any]) -> WebSocketServer:
    """Initialize the global WebSocket server."""
    global _websocket_server
    _websocket_server = WebSocketServer(config)
    return _websocket_server

def get_websocket_server() -> Optional[WebSocketServer]:
    """Get the global WebSocket server instance."""
    return _websocket_server

async def main():
    """Main function for testing WebSocket server."""
    config = {
        'host': 'localhost',
        'port': 8765,
        'secret_key': 'unified_ai_secret_2024'
    }
    
    server = initialize_websocket_server(config)
    
    try:
        await server.start_server()
        print(f"[WEBSOCKET] Server running on ws://{server.host}:{server.port}")
        print("[WEBSOCKET] Press Ctrl+C to stop")
        
        # Keep server running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[WEBSOCKET] Shutting down server...")
        await server.stop_server()
        print("[WEBSOCKET] Server stopped")

if __name__ == "__main__":
    asyncio.run(main())
