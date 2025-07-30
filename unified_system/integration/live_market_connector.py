"""
Live Market Connector - Real-Time Exchange Integration
===================================================
Connects Bidget and Bybit agents to live market feeds with full command execution,
forecast generation, and coordinated trading signals for immortal performance.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
import json
import websockets
import aiohttp
from dataclasses import dataclass, asdict
import hmac
import hashlib
import time

# Import unified system components
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from unified_system.orchestrator.command_center import get_command_center
from unified_system.communication.websocket_server import get_websocket_server
from unified_system.orchestration.cross_bot_coordinator import get_cross_bot_coordinator

logger = logging.getLogger(__name__)

@dataclass
class LiveMarketData:
    """Real-time market data structure."""
    symbol: str
    timestamp: datetime
    price: float
    volume: float
    high_24h: float
    low_24h: float
    change_24h: float
    bid: float
    ask: float
    funding_rate: Optional[float] = None
    open_interest: Optional[float] = None

@dataclass
class TradingSignal:
    """Live trading signal from collective intelligence."""
    signal_id: str
    symbol: str
    timeframe: str
    signal_type: str  # BUY, SELL, HOLD
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    risk_level: str
    consensus_level: str
    source_agents: List[str]
    timestamp: datetime
    expires_at: datetime

class LiveMarketConnector:
    """Connects the unified system to live market feeds."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize live market connector."""
        self.config = config
        self.exchanges = config.get('exchanges', {})
        
        # Market data streams
        self.market_streams: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.market_data_cache: Dict[str, LiveMarketData] = {}
        
        # Trading connections
        self.trading_sessions: Dict[str, aiohttp.ClientSession] = {}
        
        # Signal tracking
        self.active_signals: Dict[str, TradingSignal] = {}
        self.signal_performance: Dict[str, Dict[str, Any]] = {}
        
        # Performance metrics
        self.performance_metrics = {
            'signals_generated': 0,
            'signals_executed': 0,
            'successful_trades': 0,
            'total_pnl': 0.0,
            'consensus_accuracy': 0.0,
            'avg_response_time': 0.0,
            'last_update': datetime.now()
        }
        
        # Connection status
        self.running = False
        self.connected_exchanges = set()
        
    async def start_live_integration(self):
        """Start live market integration."""
        try:
            logger.info("[LIVE] Starting live market integration")
            self.running = True
            
            # Initialize trading sessions
            await self._initialize_trading_sessions()
            
            # Connect to market data streams
            await self._connect_market_streams()
            
            # Start signal processing
            asyncio.create_task(self._process_live_signals())
            
            # Start performance monitoring
            asyncio.create_task(self._monitor_performance())
            
            logger.info("[LIVE] Live market integration started successfully")
            
        except Exception as e:
            logger.error(f"[LIVE] Failed to start live integration: {e}")
            raise
    
    async def stop_live_integration(self):
        """Stop live market integration."""
        try:
            self.running = False
            
            # Close market streams
            for exchange, ws in self.market_streams.items():
                if not ws.closed:
                    await ws.close()
            
            # Close trading sessions
            for session in self.trading_sessions.values():
                await session.close()
            
            logger.info("[LIVE] Live market integration stopped")
            
        except Exception as e:
            logger.error(f"[LIVE] Error stopping live integration: {e}")
    
    async def _initialize_trading_sessions(self):
        """Initialize HTTP sessions for trading APIs."""
        try:
            for exchange_name, exchange_config in self.exchanges.items():
                session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=30),
                    headers={
                        'User-Agent': 'UnifiedAI-TradingSystem/1.0',
                        'Content-Type': 'application/json'
                    }
                )
                self.trading_sessions[exchange_name] = session
                logger.info(f"[LIVE] Initialized trading session for {exchange_name}")
                
        except Exception as e:
            logger.error(f"[LIVE] Failed to initialize trading sessions: {e}")
            raise
    
    async def _connect_market_streams(self):
        """Connect to live market data streams."""
        try:
            # Binance WebSocket connection
            if 'binance' in self.exchanges:
                await self._connect_binance_stream()
            
            # Bybit WebSocket connection
            if 'bybit' in self.exchanges:
                await self._connect_bybit_stream()
            
            logger.info(f"[LIVE] Connected to {len(self.market_streams)} market streams")
            
        except Exception as e:
            logger.error(f"[LIVE] Failed to connect market streams: {e}")
            raise
    
    async def _connect_binance_stream(self):
        """Connect to Binance WebSocket stream."""
        try:
            symbols = self.exchanges['binance'].get('symbols', ['btcusdt', 'ethusdt'])
            streams = [f"{symbol.lower()}@ticker" for symbol in symbols]
            stream_url = f"wss://stream.binance.com:9443/ws/{'/'.join(streams)}"
            
            ws = await websockets.connect(stream_url)
            self.market_streams['binance'] = ws
            self.connected_exchanges.add('binance')
            
            # Start processing Binance data
            asyncio.create_task(self._process_binance_data(ws))
            
            logger.info("[LIVE] Connected to Binance market stream")
            
        except Exception as e:
            logger.error(f"[LIVE] Failed to connect Binance stream: {e}")
    
    async def _connect_bybit_stream(self):
        """Connect to Bybit WebSocket stream."""
        try:
            # Bybit testnet or mainnet
            is_testnet = self.exchanges['bybit'].get('testnet', True)
            base_url = "wss://stream-testnet.bybit.com/v5/public/linear" if is_testnet else "wss://stream.bybit.com/v5/public/linear"
            
            ws = await websockets.connect(base_url)
            self.market_streams['bybit'] = ws
            self.connected_exchanges.add('bybit')
            
            # Subscribe to tickers
            symbols = self.exchanges['bybit'].get('symbols', ['BTCUSDT', 'ETHUSDT'])
            subscribe_msg = {
                "op": "subscribe",
                "args": [f"tickers.{symbol}" for symbol in symbols]
            }
            
            await ws.send(json.dumps(subscribe_msg))
            
            # Start processing Bybit data
            asyncio.create_task(self._process_bybit_data(ws))
            
            logger.info("[LIVE] Connected to Bybit market stream")
            
        except Exception as e:
            logger.error(f"[LIVE] Failed to connect Bybit stream: {e}")
    
    async def _process_binance_data(self, ws: websockets.WebSocketClientProtocol):
        """Process Binance market data."""
        try:
            async for message in ws:
                try:
                    data = json.loads(message)
                    
                    if 'data' in data:
                        ticker_data = data['data']
                        symbol = ticker_data['s']
                        
                        market_data = LiveMarketData(
                            symbol=symbol,
                            timestamp=datetime.now(),
                            price=float(ticker_data['c']),
                            volume=float(ticker_data['v']),
                            high_24h=float(ticker_data['h']),
                            low_24h=float(ticker_data['l']),
                            change_24h=float(ticker_data['P']),
                            bid=float(ticker_data['b']),
                            ask=float(ticker_data['a'])
                        )
                        
                        self.market_data_cache[f"binance_{symbol}"] = market_data
                        
                        # Trigger signal generation if significant price movement
                        if abs(market_data.change_24h) > 2.0:  # >2% change
                            await self._trigger_signal_generation(symbol, '1h', 'binance')
                            
                except json.JSONDecodeError:
                    logger.warning("[LIVE] Invalid JSON from Binance stream")
                except Exception as e:
                    logger.error(f"[LIVE] Error processing Binance data: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("[LIVE] Binance WebSocket connection closed")
            self.connected_exchanges.discard('binance')
        except Exception as e:
            logger.error(f"[LIVE] Binance data processing error: {e}")
    
    async def _process_bybit_data(self, ws: websockets.WebSocketClientProtocol):
        """Process Bybit market data."""
        try:
            async for message in ws:
                try:
                    data = json.loads(message)
                    
                    if 'data' in data and data.get('topic', '').startswith('tickers'):
                        ticker_data = data['data']
                        symbol = ticker_data['symbol']
                        
                        market_data = LiveMarketData(
                            symbol=symbol,
                            timestamp=datetime.now(),
                            price=float(ticker_data['lastPrice']),
                            volume=float(ticker_data['volume24h']),
                            high_24h=float(ticker_data['highPrice24h']),
                            low_24h=float(ticker_data['lowPrice24h']),
                            change_24h=float(ticker_data['price24hPcnt']) * 100,
                            bid=float(ticker_data['bid1Price']),
                            ask=float(ticker_data['ask1Price']),
                            funding_rate=float(ticker_data.get('fundingRate', 0)),
                            open_interest=float(ticker_data.get('openInterest', 0))
                        )
                        
                        self.market_data_cache[f"bybit_{symbol}"] = market_data
                        
                        # Trigger signal generation for significant moves
                        if abs(market_data.change_24h) > 2.0:
                            await self._trigger_signal_generation(symbol, '1h', 'bybit')
                            
                except json.JSONDecodeError:
                    logger.warning("[LIVE] Invalid JSON from Bybit stream")
                except Exception as e:
                    logger.error(f"[LIVE] Error processing Bybit data: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning("[LIVE] Bybit WebSocket connection closed")
            self.connected_exchanges.discard('bybit')
        except Exception as e:
            logger.error(f"[LIVE] Bybit data processing error: {e}")
    
    async def _trigger_signal_generation(self, symbol: str, timeframe: str, exchange: str):
        """Trigger collective intelligence signal generation."""
        try:
            # Get cross-bot coordinator
            coordinator = get_cross_bot_coordinator()
            if not coordinator:
                logger.warning("[LIVE] Cross-bot coordinator not available")
                return
            
            # Execute cross-bot forecast
            cross_forecast = await coordinator.execute_cross_forecast(symbol, timeframe)
            
            # Generate trading signal if consensus is strong enough
            if cross_forecast.consensus_level.value in ['strong_agreement', 'moderate_agreement']:
                signal = TradingSignal(
                    signal_id=f"{symbol}_{timeframe}_{int(time.time())}",
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type=cross_forecast.consensus_signal,
                    confidence=cross_forecast.consensus_confidence,
                    entry_price=cross_forecast.recommended_action.get('entry_price', 0),
                    stop_loss=cross_forecast.recommended_action.get('stop_loss', 0),
                    take_profit=cross_forecast.recommended_action.get('take_profit', 0),
                    position_size=cross_forecast.recommended_action.get('position_size', 0.1),
                    risk_level=cross_forecast.risk_assessment.value,
                    consensus_level=cross_forecast.consensus_level.value,
                    source_agents=list(cross_forecast.forecasts.keys()),
                    timestamp=datetime.now(),
                    expires_at=datetime.now() + timedelta(hours=1)
                )
                
                # Store active signal
                self.active_signals[signal.signal_id] = signal
                
                # Broadcast signal to network
                await self._broadcast_trading_signal(signal)
                
                self.performance_metrics['signals_generated'] += 1
                
                logger.info(f"[LIVE] Generated {signal.signal_type} signal for {symbol} with {signal.confidence:.1%} confidence")
                
        except Exception as e:
            logger.error(f"[LIVE] Signal generation failed for {symbol}: {e}")
    
    async def _broadcast_trading_signal(self, signal: TradingSignal):
        """Broadcast trading signal to all connected agents."""
        try:
            # Get WebSocket server
            ws_server = get_websocket_server()
            if not ws_server:
                logger.warning("[LIVE] WebSocket server not available")
                return
            
            # Broadcast signal to all agents
            signal_data = {
                'signal_id': signal.signal_id,
                'symbol': signal.symbol,
                'signal_type': signal.signal_type,
                'confidence': signal.confidence,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'position_size': signal.position_size,
                'risk_level': signal.risk_level,
                'consensus_level': signal.consensus_level,
                'expires_at': signal.expires_at.isoformat()
            }
            
            # Send to all connected agents
            for agent_id in signal.source_agents:
                await ws_server.send_alert(
                    source_agent='live_market_connector',
                    target_agents=[agent_id],
                    alert_type='trading_signal',
                    symbol=signal.symbol,
                    message=f"{signal.signal_type} signal generated with {signal.confidence:.1%} confidence",
                    severity='high' if signal.confidence > 0.8 else 'medium',
                    priority='high'
                )
            
            logger.info(f"[LIVE] Broadcasted signal {signal.signal_id} to {len(signal.source_agents)} agents")
            
        except Exception as e:
            logger.error(f"[LIVE] Failed to broadcast signal: {e}")
    
    async def _process_live_signals(self):
        """Process and manage live trading signals."""
        while self.running:
            try:
                current_time = datetime.now()
                expired_signals = []
                
                # Check for expired signals
                for signal_id, signal in self.active_signals.items():
                    if current_time > signal.expires_at:
                        expired_signals.append(signal_id)
                
                # Remove expired signals
                for signal_id in expired_signals:
                    expired_signal = self.active_signals.pop(signal_id)
                    logger.info(f"[LIVE] Signal {signal_id} expired")
                
                # Process active signals (placeholder for execution logic)
                for signal in self.active_signals.values():
                    await self._process_signal_execution(signal)
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"[LIVE] Signal processing error: {e}")
                await asyncio.sleep(30)
    
    async def _process_signal_execution(self, signal: TradingSignal):
        """Process signal execution (placeholder for actual trading)."""
        try:
            # In production, this would execute actual trades
            # For now, we'll simulate execution and track performance
            
            current_price = self._get_current_price(signal.symbol)
            if not current_price:
                return
            
            # Simulate execution logic
            if signal.signal_type == 'BUY' and current_price <= signal.entry_price * 1.001:  # 0.1% slippage
                logger.info(f"[LIVE] Simulated BUY execution for {signal.symbol} at {current_price}")
                self.performance_metrics['signals_executed'] += 1
                
                # Track signal for performance analysis
                self.signal_performance[signal.signal_id] = {
                    'executed_at': datetime.now(),
                    'execution_price': current_price,
                    'signal': signal
                }
            
        except Exception as e:
            logger.error(f"[LIVE] Signal execution error: {e}")
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        try:
            # Check both exchanges for the symbol
            for exchange in ['binance', 'bybit']:
                key = f"{exchange}_{symbol}"
                if key in self.market_data_cache:
                    return self.market_data_cache[key].price
            return None
        except Exception as e:
            logger.error(f"[LIVE] Error getting current price for {symbol}: {e}")
            return None
    
    async def _monitor_performance(self):
        """Monitor live performance metrics."""
        while self.running:
            try:
                # Update performance metrics
                self.performance_metrics['last_update'] = datetime.now()
                
                # Calculate consensus accuracy
                if self.performance_metrics['signals_generated'] > 0:
                    self.performance_metrics['consensus_accuracy'] = (
                        self.performance_metrics['successful_trades'] / 
                        self.performance_metrics['signals_generated']
                    )
                
                # Log performance summary
                if self.performance_metrics['signals_generated'] > 0:
                    logger.info(
                        f"[LIVE] Performance: {self.performance_metrics['signals_generated']} signals, "
                        f"{self.performance_metrics['consensus_accuracy']:.1%} accuracy, "
                        f"${self.performance_metrics['total_pnl']:.2f} PnL"
                    )
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"[LIVE] Performance monitoring error: {e}")
                await asyncio.sleep(60)
    
    def get_live_status(self) -> Dict[str, Any]:
        """Get current live integration status."""
        return {
            'running': self.running,
            'connected_exchanges': list(self.connected_exchanges),
            'active_signals': len(self.active_signals),
            'market_data_feeds': len(self.market_data_cache),
            'performance_metrics': self.performance_metrics.copy(),
            'last_signal': max([s.timestamp for s in self.active_signals.values()]) if self.active_signals else None
        }
    
    async def execute_live_command(self, command: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute live trading command."""
        try:
            if command == 'cross_forecast':
                symbol = params.get('symbol', 'BTCUSDT')
                timeframe = params.get('timeframe', '1h')
                
                coordinator = get_cross_bot_coordinator()
                if coordinator:
                    result = await coordinator.execute_cross_forecast(symbol, timeframe)
                    return {'success': True, 'data': asdict(result)}
                else:
                    return {'success': False, 'error': 'Cross-bot coordinator not available'}
            
            elif command == 'risk_status':
                coordinator = get_cross_bot_coordinator()
                if coordinator:
                    result = await coordinator.execute_risk_assessment()
                    return {'success': True, 'data': asdict(result)}
                else:
                    return {'success': False, 'error': 'Cross-bot coordinator not available'}
            
            elif command == 'live_status':
                return {'success': True, 'data': self.get_live_status()}
            
            else:
                return {'success': False, 'error': f'Unknown command: {command}'}
                
        except Exception as e:
            logger.error(f"[LIVE] Command execution failed: {e}")
            return {'success': False, 'error': str(e)}

# Global live market connector instance
_live_market_connector = None

def initialize_live_market_connector(config: Dict[str, Any]) -> LiveMarketConnector:
    """Initialize the global live market connector."""
    global _live_market_connector
    _live_market_connector = LiveMarketConnector(config)
    return _live_market_connector

def get_live_market_connector() -> Optional[LiveMarketConnector]:
    """Get the global live market connector instance."""
    return _live_market_connector

async def main():
    """Main function for testing live market connector."""
    config = {
        'exchanges': {
            'binance': {
                'symbols': ['BTCUSDT', 'ETHUSDT'],
                'api_key': 'your_binance_api_key',
                'api_secret': 'your_binance_api_secret'
            },
            'bybit': {
                'symbols': ['BTCUSDT', 'ETHUSDT'],
                'testnet': True,
                'api_key': 'your_bybit_api_key',
                'api_secret': 'your_bybit_api_secret'
            }
        }
    }
    
    connector = initialize_live_market_connector(config)
    
    try:
        await connector.start_live_integration()
        print("[LIVE] Live market integration started")
        print("[LIVE] Press Ctrl+C to stop")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n[LIVE] Shutting down live integration...")
        await connector.stop_live_integration()
        print("[LIVE] Live integration stopped")

if __name__ == "__main__":
    asyncio.run(main())
