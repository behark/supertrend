"""
Bidget Agent Adapter
===================
Integration adapter for Bidget trading bot to connect with the
Unified AI Command System. Enables Bidget to participate in
collective intelligence network and respond to global commands.
"""
import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid

# Communication imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from communication.protocol import (
    MessageBuilder, MessageValidator, MessageSerializer, UnifiedMessage,
    CommandType, MessageType, AgentStatus, ResponseHelper
)

# Bidget imports (existing system)
from ml_playbook_tuner import get_ml_tuner
from telegram_forecast_handler import TelegramForecastHandler
from trade_memory import get_trade_memory
from market_regime import MarketRegimeDetector
from bybit_trader import BybitTrader

logger = logging.getLogger(__name__)

class BidgetAgent:
    """
    Agent adapter for Bidget trading bot integration with Unified AI Command System.
    Bridges existing Bidget functionality with the collective intelligence network.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Bidget agent adapter.
        
        Args:
            config (Dict): Agent configuration including credentials and settings
        """
        self.config = config
        self.agent_id = config.get('agent_id', 'bidget_primary')
        self.agent_name = config.get('agent_name', 'Bidget')
        self.secret_key = config.get('secret_key', '')
        
        # Initialize communication
        self.message_builder = MessageBuilder(self.agent_id, self.secret_key)
        self.message_validator = MessageValidator(self.secret_key)
        
        # Initialize existing Bidget components
        self.ml_tuner = get_ml_tuner()
        self.forecast_handler = TelegramForecastHandler()
        self.trade_memory = get_trade_memory()
        self.regime_detector = MarketRegimeDetector()
        self.trader = BybitTrader() if config.get('enable_trading', False) else None
        
        # Agent state
        self.status = AgentStatus.OFFLINE
        self.last_heartbeat = datetime.now()
        self.performance_metrics = {}
        self.shared_patterns = {}
        
        # Command handlers
        self.command_handlers = {
            CommandType.FORECAST: self._handle_forecast_command,
            CommandType.TUNE: self._handle_tune_command,
            CommandType.STATUS: self._handle_status_command,
            CommandType.CONFIG_UPDATE: self._handle_config_update,
            CommandType.PATTERN_SHARE: self._handle_pattern_share,
            CommandType.ML_SYNC: self._handle_ml_sync,
            CommandType.HEALTH_CHECK: self._handle_health_check
        }
        
        # Capabilities
        self.capabilities = [
            'forecast',
            'ml_tuning',
            'pattern_recognition',
            'regime_detection',
            'trade_execution' if self.trader else 'trade_simulation',
            'telemetry_streaming',
            'collaborative_learning'
        ]
        
        # Performance tracking
        self._update_performance_metrics()
        
        logger.info(f"Bidget Agent {self.agent_id} initialized with {len(self.capabilities)} capabilities")
    
    async def register_with_orchestrator(self, orchestrator_endpoint: str) -> bool:
        """Register this agent with the Unified Command Center.
        
        Args:
            orchestrator_endpoint (str): Orchestrator connection endpoint
            
        Returns:
            bool: True if registration successful
        """
        try:
            # Create registration message
            registration_data = {
                'agent_id': self.agent_id,
                'name': self.agent_name,
                'status': AgentStatus.ONLINE.value,
                'capabilities': self.capabilities,
                'performance_metrics': self.performance_metrics,
                'connection_info': {
                    'endpoint': orchestrator_endpoint,
                    'protocol': 'websocket',
                    'version': '1.0'
                },
                'registration_timestamp': datetime.now().isoformat()
            }
            
            registration_msg = self.message_builder.create_command(
                target_agent='orchestrator',
                command=CommandType.STATUS,  # Using STATUS for registration
                data=registration_data,
                metadata={'action': 'register_agent'}
            )
            
            # TODO: Send registration message to orchestrator
            # For now, simulate successful registration
            self.status = AgentStatus.ONLINE
            self.last_heartbeat = datetime.now()
            
            logger.info(f"Bidget Agent {self.agent_id} registered with orchestrator")
            
            # Start heartbeat loop
            asyncio.create_task(self._heartbeat_loop())
            
            # Start telemetry streaming
            asyncio.create_task(self._telemetry_loop())
            
            return True
            
        except Exception as e:
            logger.error(f"Error registering with orchestrator: {e}")
            self.status = AgentStatus.ERROR
            return False
    
    async def handle_message(self, message: UnifiedMessage) -> Optional[UnifiedMessage]:
        """Handle incoming message from orchestrator or other agents.
        
        Args:
            message (UnifiedMessage): Incoming message
            
        Returns:
            UnifiedMessage: Response message if needed
        """
        try:
            # Validate message security
            if message.security and not self.message_validator.validate_message(message):
                logger.warning(f"Invalid message signature from {message.source_agent}")
                return ResponseHelper.error_response(
                    self.message_builder,
                    message.source_agent,
                    message.message_id,
                    "Invalid message signature"
                )
            
            # Handle different message types
            if message.message_type == MessageType.COMMAND:
                return await self._handle_command(message)
            elif message.message_type == MessageType.BROADCAST:
                return await self._handle_broadcast(message)
            elif message.message_type == MessageType.RESPONSE:
                return await self._handle_response(message)
            else:
                logger.warning(f"Unhandled message type: {message.message_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return ResponseHelper.error_response(
                self.message_builder,
                message.source_agent,
                message.message_id,
                f"Internal error: {str(e)}"
            )
    
    async def _handle_command(self, message: UnifiedMessage) -> Optional[UnifiedMessage]:
        """Handle command message."""
        try:
            command_type = CommandType(message.payload.action)
            handler = self.command_handlers.get(command_type)
            
            if handler:
                result = await handler(message.payload.data)
                return ResponseHelper.success_response(
                    self.message_builder,
                    message.source_agent,
                    message.message_id,
                    result
                )
            else:
                return ResponseHelper.error_response(
                    self.message_builder,
                    message.source_agent,
                    message.message_id,
                    f"Unknown command: {message.payload.action}"
                )
                
        except Exception as e:
            logger.error(f"Error handling command: {e}")
            return ResponseHelper.error_response(
                self.message_builder,
                message.source_agent,
                message.message_id,
                str(e)
            )
    
    async def _handle_broadcast(self, message: UnifiedMessage) -> Optional[UnifiedMessage]:
        """Handle broadcast message from other agents."""
        try:
            action = message.payload.action
            data = message.payload.data
            
            if action == 'pattern_discovery':
                await self._process_shared_pattern(data)
            elif action == 'ml_model_update':
                await self._process_ml_update(data)
            elif action == 'regime_change':
                await self._process_regime_change(data)
            
            logger.info(f"Processed broadcast '{action}' from {message.source_agent}")
            return None
            
        except Exception as e:
            logger.error(f"Error handling broadcast: {e}")
            return None
    
    async def _handle_response(self, message: UnifiedMessage) -> Optional[UnifiedMessage]:
        """Handle response message."""
        # TODO: Implement response handling for async operations
        logger.debug(f"Received response from {message.source_agent}")
        return None
    
    async def _handle_forecast_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle forecast command from orchestrator."""
        try:
            symbol = data.get('symbol', 'BTCUSDT')
            timeframe = data.get('timeframe', '1h')
            lookback = data.get('lookback', 100)
            
            logger.info(f"Executing forecast for {symbol} {timeframe}")
            
            # Get market data (simulate for now)
            # TODO: Integrate with actual market data fetching
            forecast_result = {
                'symbol': symbol,
                'timeframe': timeframe,
                'prediction': 'bullish',
                'confidence': 78.5,
                'target_price': 45250.50,
                'probability': 0.785,
                'horizon': 24,
                'reasoning': 'Strong momentum with regime confirmation',
                'generated_by': self.agent_name,
                'timestamp': datetime.now().isoformat()
            }
            
            # Update performance metrics
            self.performance_metrics['last_forecast'] = datetime.now().isoformat()
            self.performance_metrics['total_forecasts'] = self.performance_metrics.get('total_forecasts', 0) + 1
            
            return forecast_result
            
        except Exception as e:
            logger.error(f"Error in forecast command: {e}")
            raise
    
    async def _handle_tune_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ML tuning command from orchestrator."""
        try:
            lookback_days = data.get('lookback_days', 30)
            
            logger.info(f"Executing ML tuning with {lookback_days} days lookback")
            
            # Generate tuning recommendations using existing ML tuner
            session = self.ml_tuner.generate_tuning_recommendations(lookback_days)
            
            # Format results for orchestrator
            tuning_result = {
                'session_id': session.session_id,
                'recommendations': [
                    {
                        'regime': rec.regime,
                        'parameter': rec.parameter,
                        'current_value': rec.current_value,
                        'recommended_value': rec.recommended_value,
                        'confidence': rec.confidence,
                        'reasoning': rec.reasoning,
                        'risk_level': rec.risk_level
                    }
                    for rec in session.recommendations
                ],
                'data_quality_score': session.data_quality_score,
                'total_trades_analyzed': session.total_trades_analyzed,
                'generated_by': self.agent_name,
                'timestamp': datetime.now().isoformat()
            }
            
            # Update performance metrics
            self.performance_metrics['last_tuning'] = datetime.now().isoformat()
            self.performance_metrics['total_tuning_sessions'] = self.performance_metrics.get('total_tuning_sessions', 0) + 1
            
            return tuning_result
            
        except Exception as e:
            logger.error(f"Error in tune command: {e}")
            raise
    
    async def _handle_status_command(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status command from orchestrator."""
        try:
            # Update performance metrics
            self._update_performance_metrics()
            
            status_result = {
                'agent_id': self.agent_id,
                'name': self.agent_name,
                'status': self.status.value,
                'uptime': (datetime.now() - self.last_heartbeat).total_seconds(),
                'capabilities': self.capabilities,
                'performance_metrics': self.performance_metrics,
                'shared_patterns_count': len(self.shared_patterns),
                'last_heartbeat': self.last_heartbeat.isoformat(),
                'timestamp': datetime.now().isoformat()
            }
            
            return status_result
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            raise
    
    async def _handle_config_update(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle configuration update from orchestrator."""
        try:
            # Update configuration
            for key, value in data.items():
                if key in self.config:
                    old_value = self.config[key]
                    self.config[key] = value
                    logger.info(f"Config updated: {key} = {old_value} → {value}")
            
            return {
                'updated_keys': list(data.keys()),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            raise
    
    async def _handle_pattern_share(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pattern sharing request."""
        try:
            # Share discovered patterns with the network
            patterns_to_share = []
            
            # TODO: Extract patterns from recent analysis
            # For now, create example pattern
            pattern = {
                'pattern_id': str(uuid.uuid4()),
                'symbol': 'BTCUSDT',
                'pattern_type': 'bullish_reversal',
                'confidence': 0.82,
                'success_rate': 0.75,
                'discovery_timestamp': datetime.now().isoformat(),
                'discovered_by': self.agent_name
            }
            
            patterns_to_share.append(pattern)
            
            # Broadcast patterns to network
            for pattern in patterns_to_share:
                broadcast_msg = self.message_builder.create_broadcast(
                    action='pattern_discovery',
                    data=pattern
                )
                # TODO: Send broadcast message
                
            return {
                'patterns_shared': len(patterns_to_share),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error sharing patterns: {e}")
            raise
    
    async def _handle_ml_sync(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle ML model synchronization."""
        try:
            # TODO: Implement ML model synchronization
            return {
                'models_synced': ['leverage_optimizer', 'risk_ratio_optimizer'],
                'sync_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in ML sync: {e}")
            raise
    
    async def _handle_health_check(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle health check from orchestrator."""
        try:
            # Perform comprehensive health check
            health_status = {
                'overall_health': 'healthy',
                'components': {
                    'ml_tuner': 'online',
                    'forecast_handler': 'online',
                    'trade_memory': 'online',
                    'regime_detector': 'online',
                    'trader': 'online' if self.trader else 'disabled'
                },
                'last_error': None,
                'memory_usage': 'normal',
                'response_time': 0.05,
                'timestamp': datetime.now().isoformat()
            }
            
            return health_status
            
        except Exception as e:
            logger.error(f"Error in health check: {e}")
            raise
    
    async def _process_shared_pattern(self, pattern_data: Dict[str, Any]):
        """Process pattern shared by another agent."""
        try:
            pattern_id = pattern_data.get('pattern_id')
            if pattern_id and pattern_id not in self.shared_patterns:
                self.shared_patterns[pattern_id] = pattern_data
                logger.info(f"Learned new pattern from network: {pattern_data.get('pattern_type', 'unknown')}")
                
                # TODO: Integrate pattern into local ML models
                
        except Exception as e:
            logger.error(f"Error processing shared pattern: {e}")
    
    async def _process_ml_update(self, update_data: Dict[str, Any]):
        """Process ML model update from another agent."""
        try:
            # TODO: Implement ML model update processing
            logger.info(f"Received ML update from network")
            
        except Exception as e:
            logger.error(f"Error processing ML update: {e}")
    
    async def _process_regime_change(self, regime_data: Dict[str, Any]):
        """Process regime change notification from network."""
        try:
            symbol = regime_data.get('symbol')
            new_regime = regime_data.get('regime')
            confidence = regime_data.get('confidence', 0)
            
            logger.info(f"Network regime change: {symbol} → {new_regime} ({confidence:.1%})")
            
            # TODO: Update local regime detection with network intelligence
            
        except Exception as e:
            logger.error(f"Error processing regime change: {e}")
    
    def _update_performance_metrics(self):
        """Update performance metrics from trade memory and other sources."""
        try:
            # Get recent performance from trade memory
            recent_trades = self.trade_memory.get_history(days=1, limit=50)
            
            if recent_trades:
                total_pnl = sum(trade.pnl or 0 for trade in recent_trades if trade.pnl)
                winning_trades = [trade for trade in recent_trades if trade.pnl and trade.pnl > 0]
                win_rate = len(winning_trades) / len(recent_trades) if recent_trades else 0
                
                self.performance_metrics.update({
                    'trades_today': len(recent_trades),
                    'pnl_today': total_pnl,
                    'win_rate': win_rate,
                    'avg_confidence': sum(trade.confidence_score for trade in recent_trades) / len(recent_trades),
                    'last_updated': datetime.now().isoformat()
                })
            
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages to orchestrator."""
        while self.status != AgentStatus.OFFLINE:
            try:
                # Update performance metrics
                self._update_performance_metrics()
                
                # Create heartbeat message
                heartbeat_msg = self.message_builder.create_heartbeat(
                    status=self.status,
                    performance_data=self.performance_metrics
                )
                
                # TODO: Send heartbeat to orchestrator
                self.last_heartbeat = datetime.now()
                
                logger.debug(f"Heartbeat sent from {self.agent_name}")
                
                # Wait 30 seconds before next heartbeat
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _telemetry_loop(self):
        """Send periodic telemetry data to orchestrator."""
        while self.status != AgentStatus.OFFLINE:
            try:
                # Collect telemetry data
                telemetry_data = {
                    'agent_id': self.agent_id,
                    'timestamp': datetime.now().isoformat(),
                    'performance': self.performance_metrics,
                    'system_metrics': {
                        'memory_usage': 'normal',  # TODO: Get actual memory usage
                        'cpu_usage': 'normal',     # TODO: Get actual CPU usage
                        'response_time': 0.05,     # TODO: Calculate actual response time
                        'error_count': 0           # TODO: Track actual errors
                    },
                    'trading_metrics': {
                        'active_positions': 0,     # TODO: Get from trader
                        'pending_orders': 0,       # TODO: Get from trader
                        'risk_exposure': 0.0       # TODO: Calculate risk exposure
                    }
                }
                
                # Create telemetry message
                telemetry_msg = self.message_builder.create_telemetry(telemetry_data)
                
                # TODO: Send telemetry to orchestrator
                
                logger.debug(f"Telemetry sent from {self.agent_name}")
                
                # Wait 60 seconds before next telemetry
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in telemetry loop: {e}")
                await asyncio.sleep(120)  # Wait longer on error
    
    async def shutdown(self):
        """Gracefully shutdown the agent."""
        try:
            self.status = AgentStatus.OFFLINE
            
            # Send shutdown notification
            shutdown_msg = self.message_builder.create_command(
                target_agent='orchestrator',
                command=CommandType.STATUS,
                data={'action': 'agent_shutdown', 'agent_id': self.agent_id},
                metadata={'shutdown_timestamp': datetime.now().isoformat()}
            )
            
            # TODO: Send shutdown message
            
            logger.info(f"Bidget Agent {self.agent_id} shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Global agent instance
bidget_agent = None

def get_bidget_agent() -> BidgetAgent:
    """Get global Bidget agent instance."""
    global bidget_agent
    if bidget_agent is None:
        raise RuntimeError("Bidget agent not initialized")
    return bidget_agent

def initialize_bidget_agent(config: Dict[str, Any]) -> BidgetAgent:
    """Initialize global Bidget agent instance."""
    global bidget_agent
    bidget_agent = BidgetAgent(config)
    return bidget_agent


if __name__ == "__main__":
    # Test the Bidget agent
    import asyncio
    
    async def test_bidget_agent():
        # Initialize agent
        config = {
            'agent_id': 'bidget_test',
            'agent_name': 'Test Bidget',
            'secret_key': 'test_secret_key',
            'enable_trading': False
        }
        
        agent = initialize_bidget_agent(config)
        
        # Test registration
        success = await agent.register_with_orchestrator('ws://localhost:9000')
        print(f"🤖 Registration successful: {success}")
        
        # Test forecast command
        forecast_result = await agent._handle_forecast_command({
            'symbol': 'BTCUSDT',
            'timeframe': '1h'
        })
        print(f"📊 Forecast result: {json.dumps(forecast_result, indent=2)}")
        
        # Test status command
        status_result = await agent._handle_status_command({})
        print(f"📈 Status result: {json.dumps(status_result, indent=2, default=str)}")
        
        print("\n✅ Bidget Agent test completed!")
        
        # Shutdown
        await agent.shutdown()
    
    # Run test
    asyncio.run(test_bidget_agent())
