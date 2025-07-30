"""
Unified AI Command Center
=========================
Core orchestration engine for the Unified AI Command System.
Coordinates multiple trading bots, manages global commands, and 
provides centralized intelligence coordination.
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

# Communication imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from communication.protocol import (
    MessageBuilder, MessageValidator, MessageSerializer, UnifiedMessage,
    CommandType, MessageType, AgentStatus, ResponseHelper
)

logger = logging.getLogger(__name__)

@dataclass
class AgentInfo:
    """Information about a registered agent."""
    agent_id: str
    name: str
    status: AgentStatus
    last_heartbeat: datetime
    capabilities: List[str]
    performance_metrics: Dict[str, Any]
    connection_info: Dict[str, Any]

@dataclass
class CommandExecution:
    """Information about a command execution."""
    command_id: str
    command_type: str
    target_agents: List[str]
    start_time: datetime
    status: str  # 'pending', 'executing', 'completed', 'failed'
    responses: Dict[str, Any]
    timeout: int
    metadata: Dict[str, Any]

class UnifiedCommandCenter:
    """
    Central orchestration engine for the Unified AI Command System.
    Manages multiple trading bots and coordinates global operations.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the command center.
        
        Args:
            config (Dict): System configuration
        """
        self.config = config
        self.agent_registry: Dict[str, AgentInfo] = {}
        self.active_commands: Dict[str, CommandExecution] = {}
        self.message_builder = MessageBuilder("orchestrator", config.get('secret_key'))
        self.message_validator = MessageValidator(config.get('secret_key', ''))
        
        # Performance tracking
        self.system_metrics = {
            'total_commands': 0,
            'successful_commands': 0,
            'failed_commands': 0,
            'average_response_time': 0.0,
            'active_agents': 0,
            'uptime_start': datetime.now()
        }
        
        # Communication handlers
        self.message_handlers = {
            MessageType.RESPONSE: self._handle_response,
            MessageType.HEARTBEAT: self._handle_heartbeat,
            MessageType.TELEMETRY: self._handle_telemetry,
            MessageType.BROADCAST: self._handle_broadcast,
            MessageType.ERROR: self._handle_error
        }
        
        # Thread pool for async operations
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        logger.info("Unified Command Center initialized")
    
    async def register_agent(self, agent_info: AgentInfo) -> bool:
        """Register a new agent with the command center.
        
        Args:
            agent_info (AgentInfo): Agent information
            
        Returns:
            bool: True if registration successful
        """
        try:
            self.agent_registry[agent_info.agent_id] = agent_info
            self.system_metrics['active_agents'] = len(self.agent_registry)
            
            logger.info(f"Agent registered: {agent_info.name} ({agent_info.agent_id})")
            
            # Send welcome message to agent
            welcome_msg = self.message_builder.create_command(
                target_agent=agent_info.agent_id,
                command=CommandType.STATUS,
                data={'action': 'registration_complete'},
                metadata={'welcome': True}
            )
            
            await self._send_message(welcome_msg)
            return True
            
        except Exception as e:
            logger.error(f"Error registering agent {agent_info.name}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the command center.
        
        Args:
            agent_id (str): Agent ID to unregister
            
        Returns:
            bool: True if unregistration successful
        """
        try:
            if agent_id in self.agent_registry:
                agent_name = self.agent_registry[agent_id].name
                del self.agent_registry[agent_id]
                self.system_metrics['active_agents'] = len(self.agent_registry)
                
                logger.info(f"Agent unregistered: {agent_name} ({agent_id})")
                return True
            else:
                logger.warning(f"Attempted to unregister unknown agent: {agent_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error unregistering agent {agent_id}: {e}")
            return False
    
    async def execute_global_command(self, command_type: CommandType, 
                                   data: Dict[str, Any], 
                                   target_agents: Optional[List[str]] = None,
                                   timeout: int = 30) -> Dict[str, Any]:
        """Execute a command across multiple agents.
        
        Args:
            command_type (CommandType): Type of command to execute
            data (Dict): Command data
            target_agents (List[str], optional): Specific agents to target
            timeout (int): Command timeout in seconds
            
        Returns:
            Dict: Aggregated results from all agents
        """
        command_id = str(uuid.uuid4())
        start_time = datetime.now()
        
        # Determine target agents
        if target_agents is None:
            target_agents = list(self.agent_registry.keys())
        else:
            # Filter to only registered agents
            target_agents = [aid for aid in target_agents if aid in self.agent_registry]
        
        if not target_agents:
            return {
                'success': False,
                'error': 'No valid target agents found',
                'results': {}
            }
        
        # Create command execution record
        command_execution = CommandExecution(
            command_id=command_id,
            command_type=command_type.value,
            target_agents=target_agents,
            start_time=start_time,
            status='executing',
            responses={},
            timeout=timeout,
            metadata={'data': data}
        )
        
        self.active_commands[command_id] = command_execution
        self.system_metrics['total_commands'] += 1
        
        try:
            # Send command to all target agents
            tasks = []
            for agent_id in target_agents:
                task = self._send_command_to_agent(agent_id, command_type, data, command_id)
                tasks.append(task)
            
            # Wait for responses with timeout
            responses = await asyncio.wait_for(
                self._collect_responses(command_id, len(target_agents)),
                timeout=timeout
            )
            
            # Update command status
            command_execution.status = 'completed'
            command_execution.responses = responses
            
            # Update metrics
            response_time = (datetime.now() - start_time).total_seconds()
            self._update_response_time_metric(response_time)
            self.system_metrics['successful_commands'] += 1
            
            logger.info(f"Global command {command_type.value} completed in {response_time:.2f}s")
            
            return {
                'success': True,
                'command_id': command_id,
                'execution_time': response_time,
                'results': responses
            }
            
        except asyncio.TimeoutError:
            command_execution.status = 'timeout'
            self.system_metrics['failed_commands'] += 1
            
            logger.warning(f"Global command {command_type.value} timed out after {timeout}s")
            
            return {
                'success': False,
                'error': 'Command timeout',
                'command_id': command_id,
                'partial_results': command_execution.responses
            }
            
        except Exception as e:
            command_execution.status = 'failed'
            self.system_metrics['failed_commands'] += 1
            
            logger.error(f"Error executing global command {command_type.value}: {e}")
            
            return {
                'success': False,
                'error': str(e),
                'command_id': command_id
            }
        
        finally:
            # Clean up command record after delay
            asyncio.create_task(self._cleanup_command(command_id, delay=300))
    
    async def execute_forecast_all(self, symbol: str, timeframe: str = '1h') -> Dict[str, Any]:
        """Execute forecast command across all agents.
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Chart timeframe
            
        Returns:
            Dict: Aggregated forecast results
        """
        return await self.execute_global_command(
            command_type=CommandType.FORECAST,
            data={
                'symbol': symbol,
                'timeframe': timeframe,
                'lookback': 100
            }
        )
    
    async def execute_tune_all(self, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute ML tuning across all agents.
        
        Args:
            parameters (Dict, optional): Tuning parameters
            
        Returns:
            Dict: Aggregated tuning results
        """
        return await self.execute_global_command(
            command_type=CommandType.TUNE,
            data=parameters or {'lookback_days': 30}
        )
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status.
        
        Returns:
            Dict: System status information
        """
        # Calculate uptime
        uptime = datetime.now() - self.system_metrics['uptime_start']
        
        # Get agent statuses
        agent_statuses = {}
        for agent_id, agent_info in self.agent_registry.items():
            time_since_heartbeat = datetime.now() - agent_info.last_heartbeat
            is_responsive = time_since_heartbeat < timedelta(minutes=2)
            
            agent_statuses[agent_id] = {
                'name': agent_info.name,
                'status': agent_info.status.value,
                'responsive': is_responsive,
                'last_heartbeat': agent_info.last_heartbeat.isoformat(),
                'capabilities': agent_info.capabilities,
                'performance': agent_info.performance_metrics
            }
        
        return {
            'system_metrics': {
                **self.system_metrics,
                'uptime_seconds': uptime.total_seconds(),
                'uptime_formatted': str(uptime)
            },
            'agents': agent_statuses,
            'active_commands': len(self.active_commands),
            'timestamp': datetime.now().isoformat()
        }
    
    async def handle_message(self, message: UnifiedMessage) -> Optional[UnifiedMessage]:
        """Handle incoming message from agents.
        
        Args:
            message (UnifiedMessage): Incoming message
            
        Returns:
            UnifiedMessage: Response message if needed
        """
        try:
            # Validate message if security is enabled
            if message.security and not self.message_validator.validate_message(message):
                logger.warning(f"Invalid message signature from {message.source_agent}")
                return ResponseHelper.error_response(
                    self.message_builder,
                    message.source_agent,
                    message.message_id,
                    "Invalid message signature"
                )
            
            # Route message to appropriate handler
            handler = self.message_handlers.get(message.message_type)
            if handler:
                return await handler(message)
            else:
                logger.warning(f"No handler for message type: {message.message_type}")
                return ResponseHelper.error_response(
                    self.message_builder,
                    message.source_agent,
                    message.message_id,
                    f"Unknown message type: {message.message_type}"
                )
                
        except Exception as e:
            logger.error(f"Error handling message from {message.source_agent}: {e}")
            return ResponseHelper.error_response(
                self.message_builder,
                message.source_agent,
                message.message_id,
                f"Internal error: {str(e)}"
            )
    
    async def _send_command_to_agent(self, agent_id: str, command_type: CommandType,
                                   data: Dict[str, Any], command_id: str) -> None:
        """Send command to a specific agent.
        
        Args:
            agent_id (str): Target agent ID
            command_type (CommandType): Command type
            data (Dict): Command data
            command_id (str): Command execution ID
        """
        try:
            command_msg = self.message_builder.create_command(
                target_agent=agent_id,
                command=command_type,
                data=data,
                metadata={'command_id': command_id}
            )
            
            await self._send_message(command_msg)
            
        except Exception as e:
            logger.error(f"Error sending command to agent {agent_id}: {e}")
    
    async def _collect_responses(self, command_id: str, expected_count: int) -> Dict[str, Any]:
        """Collect responses for a command execution.
        
        Args:
            command_id (str): Command execution ID
            expected_count (int): Expected number of responses
            
        Returns:
            Dict: Collected responses
        """
        responses = {}
        
        while len(responses) < expected_count:
            # Check if we have responses for this command
            if command_id in self.active_commands:
                command_execution = self.active_commands[command_id]
                responses.update(command_execution.responses)
                
                if len(responses) >= expected_count:
                    break
            
            # Wait a bit before checking again
            await asyncio.sleep(0.1)
        
        return responses
    
    async def _handle_response(self, message: UnifiedMessage) -> Optional[UnifiedMessage]:
        """Handle response message from agent."""
        try:
            response_data = message.payload.data
            original_message_id = response_data.get('original_message_id')
            
            # Find the command this response belongs to
            for command_id, command_execution in self.active_commands.items():
                if original_message_id in [msg.message_id for msg in getattr(command_execution, 'sent_messages', [])]:
                    command_execution.responses[message.source_agent] = response_data
                    break
            
            logger.debug(f"Received response from {message.source_agent}")
            return None
            
        except Exception as e:
            logger.error(f"Error handling response from {message.source_agent}: {e}")
            return None
    
    async def _handle_heartbeat(self, message: UnifiedMessage) -> Optional[UnifiedMessage]:
        """Handle heartbeat message from agent."""
        try:
            agent_id = message.source_agent
            heartbeat_data = message.payload.data
            
            if agent_id in self.agent_registry:
                agent_info = self.agent_registry[agent_id]
                agent_info.last_heartbeat = datetime.now()
                agent_info.status = AgentStatus(heartbeat_data.get('status', 'online'))
                
                # Update performance metrics if provided
                if 'performance' in heartbeat_data:
                    agent_info.performance_metrics.update(heartbeat_data['performance'])
                
                logger.debug(f"Heartbeat received from {agent_info.name}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling heartbeat from {message.source_agent}: {e}")
            return None
    
    async def _handle_telemetry(self, message: UnifiedMessage) -> Optional[UnifiedMessage]:
        """Handle telemetry message from agent."""
        try:
            agent_id = message.source_agent
            telemetry_data = message.payload.data
            
            if agent_id in self.agent_registry:
                agent_info = self.agent_registry[agent_id]
                agent_info.performance_metrics.update(telemetry_data)
                
                logger.debug(f"Telemetry received from {agent_info.name}")
            
            # Forward telemetry to telemetry system
            # TODO: Implement telemetry forwarding
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling telemetry from {message.source_agent}: {e}")
            return None
    
    async def _handle_broadcast(self, message: UnifiedMessage) -> Optional[UnifiedMessage]:
        """Handle broadcast message from agent."""
        try:
            # Forward broadcast to all other agents
            for agent_id in self.agent_registry:
                if agent_id != message.source_agent:
                    forward_msg = self.message_builder.create_broadcast(
                        action=message.payload.action,
                        data=message.payload.data,
                        metadata={
                            'original_source': message.source_agent,
                            'forwarded_by': 'orchestrator'
                        }
                    )
                    forward_msg.target_agent = agent_id
                    await self._send_message(forward_msg)
            
            logger.info(f"Broadcast forwarded from {message.source_agent}")
            return None
            
        except Exception as e:
            logger.error(f"Error handling broadcast from {message.source_agent}: {e}")
            return None
    
    async def _handle_error(self, message: UnifiedMessage) -> Optional[UnifiedMessage]:
        """Handle error message from agent."""
        try:
            error_data = message.payload.data
            logger.error(f"Error reported by {message.source_agent}: {error_data}")
            
            # TODO: Implement error handling and recovery
            
            return None
            
        except Exception as e:
            logger.error(f"Error handling error message from {message.source_agent}: {e}")
            return None
    
    async def _send_message(self, message: UnifiedMessage) -> None:
        """Send message to target agent.
        
        Args:
            message (UnifiedMessage): Message to send
        """
        # TODO: Implement actual message sending via WebSocket/HTTP
        # For now, just log the message
        logger.debug(f"Sending message to {message.target_agent}: {message.payload.action}")
    
    def _update_response_time_metric(self, response_time: float) -> None:
        """Update average response time metric."""
        current_avg = self.system_metrics['average_response_time']
        total_commands = self.system_metrics['successful_commands']
        
        if total_commands == 1:
            self.system_metrics['average_response_time'] = response_time
        else:
            # Calculate running average
            new_avg = ((current_avg * (total_commands - 1)) + response_time) / total_commands
            self.system_metrics['average_response_time'] = new_avg
    
    async def _cleanup_command(self, command_id: str, delay: int = 300) -> None:
        """Clean up command execution record after delay.
        
        Args:
            command_id (str): Command ID to clean up
            delay (int): Delay in seconds before cleanup
        """
        await asyncio.sleep(delay)
        if command_id in self.active_commands:
            del self.active_commands[command_id]
            logger.debug(f"Cleaned up command record: {command_id}")

# Global command center instance
command_center = None

def get_command_center() -> UnifiedCommandCenter:
    """Get global command center instance."""
    global command_center
    if command_center is None:
        raise RuntimeError("Command center not initialized")
    return command_center

def initialize_command_center(config: Dict[str, Any]) -> UnifiedCommandCenter:
    """Initialize global command center instance."""
    global command_center
    command_center = UnifiedCommandCenter(config)
    return command_center


if __name__ == "__main__":
    # Test the command center
    import asyncio
    
    async def test_command_center():
        # Initialize command center
        config = {
            'secret_key': 'test_secret_key',
            'max_agents': 10,
            'command_timeout': 30
        }
        
        center = initialize_command_center(config)
        
        # Register test agent
        test_agent = AgentInfo(
            agent_id="test_bidget",
            name="Test Bidget",
            status=AgentStatus.ONLINE,
            last_heartbeat=datetime.now(),
            capabilities=["forecast", "tune", "trade"],
            performance_metrics={"win_rate": 0.75, "pnl": 1250.50},
            connection_info={"host": "localhost", "port": 8080}
        )
        
        await center.register_agent(test_agent)
        
        # Get system status
        status = await center.get_system_status()
        print("🧠 System Status:")
        print(json.dumps(status, indent=2, default=str))
        
        print("\n✅ Command Center test completed!")
    
    # Run test
    asyncio.run(test_command_center())
