"""
Unified AI Communication Protocol
=================================
Standardized messaging protocol for inter-bot communication in the 
Unified AI Command System. Enables secure, efficient communication
between orchestrator and agents.
"""
import json
import uuid
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Standard message types for inter-bot communication."""
    COMMAND = "command"
    RESPONSE = "response"
    BROADCAST = "broadcast"
    TELEMETRY = "telemetry"
    HEARTBEAT = "heartbeat"
    ERROR = "error"

class CommandType(Enum):
    """Available command types."""
    FORECAST = "forecast"
    TUNE = "tune"
    STATUS = "status"
    CONFIG_UPDATE = "config_update"
    PATTERN_SHARE = "pattern_share"
    ML_SYNC = "ml_sync"
    HEALTH_CHECK = "health_check"
    SHUTDOWN = "shutdown"

class AgentStatus(Enum):
    """Agent status states."""
    ONLINE = "online"
    OFFLINE = "offline"
    BUSY = "busy"
    ERROR = "error"
    MAINTENANCE = "maintenance"

@dataclass
class SecurityInfo:
    """Security information for message authentication."""
    signature: str
    timestamp: str
    nonce: str

@dataclass
class MessagePayload:
    """Standard message payload structure."""
    action: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class UnifiedMessage:
    """Standard message format for all inter-bot communication."""
    message_id: str
    timestamp: str
    source_agent: str
    target_agent: str  # "orchestrator", "all", or specific agent name
    message_type: MessageType
    payload: MessagePayload
    security: Optional[SecurityInfo] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        msg_dict = asdict(self)
        msg_dict['message_type'] = self.message_type.value
        return msg_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UnifiedMessage':
        """Create message from dictionary."""
        # Convert message_type back to enum
        data['message_type'] = MessageType(data['message_type'])
        
        # Convert payload to MessagePayload object
        if isinstance(data['payload'], dict):
            data['payload'] = MessagePayload(**data['payload'])
        
        # Convert security to SecurityInfo object if present
        if data.get('security') and isinstance(data['security'], dict):
            data['security'] = SecurityInfo(**data['security'])
        
        return cls(**data)

class MessageBuilder:
    """Builder class for creating standardized messages."""
    
    def __init__(self, source_agent: str, secret_key: Optional[str] = None):
        """Initialize message builder.
        
        Args:
            source_agent (str): Name of the source agent
            secret_key (str, optional): Secret key for message signing
        """
        self.source_agent = source_agent
        self.secret_key = secret_key
    
    def create_command(self, target_agent: str, command: CommandType, 
                      data: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> UnifiedMessage:
        """Create a command message.
        
        Args:
            target_agent (str): Target agent name
            command (CommandType): Command type
            data (Dict): Command data
            metadata (Dict, optional): Additional metadata
            
        Returns:
            UnifiedMessage: Formatted command message
        """
        return self._create_message(
            target_agent=target_agent,
            message_type=MessageType.COMMAND,
            action=command.value,
            data=data,
            metadata=metadata or {}
        )
    
    def create_response(self, target_agent: str, original_message_id: str,
                       success: bool, data: Dict[str, Any], 
                       error: Optional[str] = None) -> UnifiedMessage:
        """Create a response message.
        
        Args:
            target_agent (str): Target agent name
            original_message_id (str): ID of the original message
            success (bool): Whether the operation was successful
            data (Dict): Response data
            error (str, optional): Error message if failed
            
        Returns:
            UnifiedMessage: Formatted response message
        """
        response_data = {
            'success': success,
            'original_message_id': original_message_id,
            'result': data
        }
        
        if error:
            response_data['error'] = error
        
        return self._create_message(
            target_agent=target_agent,
            message_type=MessageType.RESPONSE,
            action="response",
            data=response_data,
            metadata={}
        )
    
    def create_broadcast(self, action: str, data: Dict[str, Any], 
                        metadata: Optional[Dict[str, Any]] = None) -> UnifiedMessage:
        """Create a broadcast message to all agents.
        
        Args:
            action (str): Broadcast action
            data (Dict): Broadcast data
            metadata (Dict, optional): Additional metadata
            
        Returns:
            UnifiedMessage: Formatted broadcast message
        """
        return self._create_message(
            target_agent="all",
            message_type=MessageType.BROADCAST,
            action=action,
            data=data,
            metadata=metadata or {}
        )
    
    def create_telemetry(self, data: Dict[str, Any]) -> UnifiedMessage:
        """Create a telemetry message.
        
        Args:
            data (Dict): Telemetry data
            
        Returns:
            UnifiedMessage: Formatted telemetry message
        """
        return self._create_message(
            target_agent="orchestrator",
            message_type=MessageType.TELEMETRY,
            action="telemetry_update",
            data=data,
            metadata={}
        )
    
    def create_heartbeat(self, status: AgentStatus, 
                        performance_data: Optional[Dict[str, Any]] = None) -> UnifiedMessage:
        """Create a heartbeat message.
        
        Args:
            status (AgentStatus): Current agent status
            performance_data (Dict, optional): Performance metrics
            
        Returns:
            UnifiedMessage: Formatted heartbeat message
        """
        heartbeat_data = {
            'status': status.value,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        if performance_data:
            heartbeat_data['performance'] = performance_data
        
        return self._create_message(
            target_agent="orchestrator",
            message_type=MessageType.HEARTBEAT,
            action="heartbeat",
            data=heartbeat_data,
            metadata={}
        )
    
    def _create_message(self, target_agent: str, message_type: MessageType,
                       action: str, data: Dict[str, Any], 
                       metadata: Dict[str, Any]) -> UnifiedMessage:
        """Internal method to create a message with security."""
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        
        payload = MessagePayload(
            action=action,
            data=data,
            metadata=metadata
        )
        
        message = UnifiedMessage(
            message_id=message_id,
            timestamp=timestamp,
            source_agent=self.source_agent,
            target_agent=target_agent,
            message_type=message_type,
            payload=payload
        )
        
        # Add security signature if secret key is available
        if self.secret_key:
            message.security = self._create_security_info(message)
        
        return message
    
    def _create_security_info(self, message: UnifiedMessage) -> SecurityInfo:
        """Create security information for message authentication."""
        nonce = str(uuid.uuid4())
        timestamp = message.timestamp
        
        # Create message signature
        message_content = json.dumps({
            'message_id': message.message_id,
            'timestamp': timestamp,
            'source_agent': message.source_agent,
            'target_agent': message.target_agent,
            'message_type': message.message_type.value,
            'payload': message.payload.to_dict()
        }, sort_keys=True)
        
        signature_data = f"{message_content}:{nonce}:{timestamp}"
        signature = hmac.new(
            self.secret_key.encode(),
            signature_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return SecurityInfo(
            signature=signature,
            timestamp=timestamp,
            nonce=nonce
        )

class MessageValidator:
    """Validates message authenticity and integrity."""
    
    def __init__(self, secret_key: str):
        """Initialize message validator.
        
        Args:
            secret_key (str): Secret key for signature verification
        """
        self.secret_key = secret_key
    
    def validate_message(self, message: UnifiedMessage) -> bool:
        """Validate message signature and integrity.
        
        Args:
            message (UnifiedMessage): Message to validate
            
        Returns:
            bool: True if message is valid, False otherwise
        """
        if not message.security:
            logger.warning(f"Message {message.message_id} has no security info")
            return False
        
        try:
            # Recreate signature
            message_content = json.dumps({
                'message_id': message.message_id,
                'timestamp': message.timestamp,
                'source_agent': message.source_agent,
                'target_agent': message.target_agent,
                'message_type': message.message_type.value,
                'payload': message.payload.to_dict()
            }, sort_keys=True)
            
            signature_data = f"{message_content}:{message.security.nonce}:{message.security.timestamp}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                signature_data.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            is_valid = hmac.compare_digest(expected_signature, message.security.signature)
            
            if not is_valid:
                logger.warning(f"Invalid signature for message {message.message_id}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"Error validating message {message.message_id}: {e}")
            return False

class MessageSerializer:
    """Handles message serialization and deserialization."""
    
    @staticmethod
    def serialize(message: UnifiedMessage) -> str:
        """Serialize message to JSON string.
        
        Args:
            message (UnifiedMessage): Message to serialize
            
        Returns:
            str: JSON string representation
        """
        try:
            return json.dumps(message.to_dict(), indent=None, separators=(',', ':'))
        except Exception as e:
            logger.error(f"Error serializing message: {e}")
            raise
    
    @staticmethod
    def deserialize(message_json: str) -> UnifiedMessage:
        """Deserialize JSON string to message.
        
        Args:
            message_json (str): JSON string to deserialize
            
        Returns:
            UnifiedMessage: Deserialized message
        """
        try:
            data = json.loads(message_json)
            return UnifiedMessage.from_dict(data)
        except Exception as e:
            logger.error(f"Error deserializing message: {e}")
            raise

# Standard response helpers
class ResponseHelper:
    """Helper functions for creating standard responses."""
    
    @staticmethod
    def success_response(builder: MessageBuilder, target_agent: str, 
                        original_message_id: str, data: Dict[str, Any]) -> UnifiedMessage:
        """Create a success response."""
        return builder.create_response(
            target_agent=target_agent,
            original_message_id=original_message_id,
            success=True,
            data=data
        )
    
    @staticmethod
    def error_response(builder: MessageBuilder, target_agent: str,
                      original_message_id: str, error_message: str,
                      error_code: Optional[str] = None) -> UnifiedMessage:
        """Create an error response."""
        error_data = {'error_message': error_message}
        if error_code:
            error_data['error_code'] = error_code
        
        return builder.create_response(
            target_agent=target_agent,
            original_message_id=original_message_id,
            success=False,
            data=error_data,
            error=error_message
        )

# Example usage and testing
if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Create message builder
    builder = MessageBuilder("bidget", secret_key="test_secret_key")
    
    # Create a forecast command
    forecast_msg = builder.create_command(
        target_agent="orchestrator",
        command=CommandType.FORECAST,
        data={
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'lookback': 100
        },
        metadata={
            'priority': 'high',
            'timeout': 30
        }
    )
    
    print("🧠 Forecast Command Message:")
    print(MessageSerializer.serialize(forecast_msg))
    
    # Create a broadcast message
    pattern_broadcast = builder.create_broadcast(
        action="pattern_discovery",
        data={
            'pattern_id': 'pattern_123',
            'symbol': 'BTCUSDT',
            'confidence': 0.85,
            'pattern_type': 'bullish_reversal'
        }
    )
    
    print("\n📡 Pattern Broadcast Message:")
    print(MessageSerializer.serialize(pattern_broadcast))
    
    # Create telemetry message
    telemetry_msg = builder.create_telemetry({
        'trades_today': 15,
        'win_rate': 0.73,
        'pnl': 245.67,
        'confidence_avg': 0.78
    })
    
    print("\n📊 Telemetry Message:")
    print(MessageSerializer.serialize(telemetry_msg))
    
    # Test message validation
    validator = MessageValidator("test_secret_key")
    is_valid = validator.validate_message(forecast_msg)
    print(f"\n🔒 Message validation result: {is_valid}")
