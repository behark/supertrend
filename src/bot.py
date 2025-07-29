"""
Trading bot main module
"""

import logging
import time
import os
import logging
import time
import schedule
import datetime
from datetime import datetime, timedelta
import threading
import traceback
from typing import Dict, List, Set, Optional, Union, Any
from collections import defaultdict
import random

# Import Telegram module if needed
try:
    from src.integrations.telegram import telegram_notifier
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    
# Import health check module if available
try:
    from src.utils.health_check import health_check
    HEALTH_CHECK_AVAILABLE = True
except ImportError:
    HEALTH_CHECK_AVAILABLE = False
    
# Import analytics logger if available
try:
    from src.utils.analytics_logger import analytics_logger
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    logger.warning("Analytics logger not available - analytics features disabled")
    
# Import parameter manager if available
try:
    from src.utils.parameter_manager import parameter_manager
    PARAMETER_MANAGER_AVAILABLE = True
except ImportError:
    PARAMETER_MANAGER_AVAILABLE = False
    logger.warning("Parameter manager not available - advanced parameter controls disabled")
    
# Import market analyzer if available
try:
    from src.utils.market_analyzer import market_analyzer, MarketRegime
    MARKET_ANALYZER_AVAILABLE = True
except ImportError:
    MARKET_ANALYZER_AVAILABLE = False
    logger.warning("Market analyzer not available - adaptive market regime detection disabled")
    
from src.market_data import MarketData
from src.strategies import SupertrendADXStrategy, InsideBarStrategy
from src.integrations.order_manager import OrderManager

logger = logging.getLogger(__name__)

class TradingBot:
    """
    Main trading bot class that coordinates market scanning, signal generation,
    and notifications
    """
    
    def __init__(self, test_mode: bool = False):
        """
        Initialize the trading bot
        
        Args:
            test_mode: If True, operate in test mode
        """
        # Initialize bot settings
        logger.info("Initializing Trading Bot")
        
        # Record start time
        self.start_time = time.time()
        
        # Test mode flag
        self.test_mode = test_mode or os.getenv('TEST_MODE', '').lower() in ['true', '1', 'yes']
        if self.test_mode:
            logger.info("🧪 RUNNING IN TEST MODE 🧪")
        else:
            logger.info("💰 RUNNING IN LIVE MODE 💰")
        
        # Load strategies
        self.strategies = {
            "supertrend_adx": SupertrendADXStrategy(),
            "inside_bar": InsideBarStrategy()
        }
        
        # Load confidence threshold from environment variable
        self.confidence_threshold = float(os.getenv('CONFIDENCE_THRESHOLD', '95'))
        logger.info(f"Signal confidence threshold set to: {self.confidence_threshold}%")
        
        # Maximum number of signals and trades per day
        self.max_signals_per_day = int(os.getenv('MAX_SIGNALS_PER_DAY', '10'))
        
        # Active signals tracking
        self.active_signals = []
        self.signals_today = 0
        self.trades_today = 0
        self.signals_enabled = {strategy_id: True for strategy_id in self.strategies.keys()}
        
        # Reset daily counters at midnight
        schedule.every().day.at("00:00").do(self.reset_daily_counters)
        self.max_trades_per_day = int(os.getenv('MAX_TRADES_PER_DAY', '5'))
        
        # Position sizing
        self.position_size_percent = float(os.getenv('POSITION_SIZE_PERCENT', '25'))
        
        # Track signals, trades and active positions
        self.daily_signals = []
        self.daily_trades_count = 0
        self.last_signals_reset = datetime.now().date()
        self.active_trades = set()  # Set of symbols with active trades
        
        # Initialize Telegram (if available)
        self.telegram = None
        if TELEGRAM_AVAILABLE:
            self.telegram = telegram_notifier
            if self.telegram.is_configured:
                logger.info("Telegram notifications enabled")
                
                # Send startup notification
                mode_str = "TEST MODE" if self.test_mode else "LIVE MODE"
                self.telegram.send_message(f"🚀 *Trading Bot Started* ({mode_str})\n\nSignal confidence threshold: {self.confidence_threshold}%\nMax signals per day: {self.max_signals_per_day}\nMax trades per day: {self.max_trades_per_day}")
                
                # Link the bot instance to the telegram notifier for commands
                self.telegram.set_bot_instance(self)
                logger.info("Bot instance linked to Telegram for commands")
            else:
                logger.warning("Telegram not configured - notifications disabled")
                
        # Initialize health check if available
        if HEALTH_CHECK_AVAILABLE:
            # Schedule regular health checks every 4 hours
            health_check.schedule_regular_checks(interval_hours=4)
            logger.info("Scheduled regular health checks every 4 hours")
            
            # Run an initial health check
            try:
                logger.info("Running initial health check")
                health_results = health_check.run_health_check(notify=False)
                status = health_results.get('overall_status', 'unknown')
                logger.info(f"Initial health check complete - status: {status}")
            except Exception as e:
                logger.error(f"Failed to run initial health check: {e}", exc_info=True)
                
        # Initialize analytics logger if available
        if ANALYTICS_AVAILABLE:
            # Schedule daily summary generation at 00:05 AM
            schedule.every().day.at("00:05").do(self._generate_analytics_summary)
            logger.info("Scheduled daily analytics summary generation at 00:05")
            
            # Log initial bot configuration
            try:
                analytics_logger.log_performance(
                    operation="bot_startup",
                    duration_ms=0,
                    success=True,
                    metadata={
                        "category": "system",
                        "test_mode": self.test_mode,
                        "confidence_threshold": self.confidence_threshold,
                        "max_signals_per_day": self.max_signals_per_day,
                        "max_trades_per_day": self.max_trades_per_day,
                        "position_size_percent": self.position_size_percent
                    }
                )
                logger.info("Analytics logging initialized")
            except Exception as e:
                logger.error(f"Failed to initialize analytics logging: {e}", exc_info=True)
                
        # Initialize market analyzer if available
        self.market_regime = "UNKNOWN"
        self.last_regime_check = datetime.now() - timedelta(hours=24)  # Force initial check
        
        if MARKET_ANALYZER_AVAILABLE:
            # Schedule market regime detection every hour
            schedule.every(1).hours.do(self._check_market_regime)
            logger.info("Scheduled market regime detection every hour")
            
            # Run initial market regime detection
            try:
                # Schedule initial check after bot startup (2 minutes delay)
                schedule.every(2).minutes.do(self._initial_market_regime_check).tag('startup')
                logger.info("Scheduled initial market regime check in 2 minutes")
            except Exception as e:
                logger.error(f"Failed to schedule market regime check: {e}", exc_info=True)
        
        # Initialize trading API reference (will be instantiated when needed)
        self.trading_api = None
        # Initialize order manager for OCO functionality (will be instantiated when needed)
        self.order_manager = None
        
        # Initialize market data
        self.market_data = MarketData(test_mode=test_mode)
        
        logger.info("Trading bot initialized with %d strategies", len(self.strategies))
        logger.info("Signal configuration: max %d signals/day, max %d trades/day, confidence threshold: %.1f%%", 
                    self.max_signals_per_day, self.max_trades_per_day, self.confidence_threshold)
                   
    def run(self):
        """Run the trading bot continuously"""
        logger.info("Starting trading bot main loop")
        
        # Set up scheduled jobs with explicit logging
        logger.info("Setting up scheduled jobs...")
        
        # Schedule market scanning every 4 hours
        schedule.every(4).hours.do(self.scan_markets)
        logger.info("Scheduled market scanning every 4 hours")
        
        # Schedule daily signal count reset
        schedule.every().day.at("00:00").do(self.reset_daily_signal_count)
        logger.info("Scheduled daily signal count reset at midnight")
        
        # Schedule active trade cleanup every 10 minutes (reduced from 30)
        schedule.every(10).minutes.do(self.check_and_clean_active_trades)
        logger.info("Scheduled active trade cleanup every 10 minutes")
        
        # Initial scan
        logger.info("Running initial market scan...")
        self.scan_markets()
        
        # Initial cleanup of active trades - Force cleanup now for immediate effect
        logger.info("Running initial active trade cleanup...")
        self.check_and_clean_active_trades()
        
        # Forcefully clear TRX/USDT from active trades if it exists (one-time fix)
        if 'TRX/USDT' in self.active_trades:
            logger.info("EMERGENCY FIX: Forcefully removing TRX/USDT from active trades")
            self.active_trades.remove('TRX/USDT')
            close_msg = f"🔔 *Position Reset* - TRX/USDT\n\nManually removed from active trades tracking to fix stuck state."
            self._send_telegram_message(close_msg)
        
        logger.info(f"Active trades after startup: {self.active_trades}")
        
        # Main loop
        try:
            next_schedule_run = time.time() + 60
            next_cleanup_check = time.time() + 300  # Force cleanup every 5 minutes regardless of schedule
            
            while True:
                current_time = time.time()
                
                # Run scheduled jobs
                if current_time >= next_schedule_run:
                    logger.info("Running pending scheduled jobs")
                    schedule.run_pending()
                    next_schedule_run = current_time + 60
                
                # Force trade cleanup check periodically regardless of schedule
                if current_time >= next_cleanup_check:
                    logger.info("Forcing active trade cleanup check")
                    self.check_and_clean_active_trades()
                    next_cleanup_check = current_time + 300  # Every 5 minutes
                
                # Process signals with rate limiting
                # Only process signals every 60 seconds instead of every 5 seconds
                if not hasattr(self, 'last_signal_process_time') or current_time - getattr(self, 'last_signal_process_time', 0) >= 60:
                    self.process_pending_signals()
                    self.last_signal_process_time = current_time
                
                # Sleep briefly to avoid CPU hogging
                time.sleep(5)
                
        except KeyboardInterrupt:
            logger.info("Trading bot stopped by user")
        except Exception as e:
            logger.error("Error in main loop: %s", str(e), exc_info=True)
            
    def scan_markets(self):
        """Scan all markets for trading signals"""
        logger.info("Starting market scan")
        
        try:
            # Get market data
            all_market_data = self.market_data.scan_all_markets()
            signals = []
            
            # Process each market and timeframe
            for symbol, timeframe_data in all_market_data.items():
                for timeframe, df in timeframe_data.items():
                    if df.empty:
                        continue
                        
                    # Run each strategy on the data
                    for strategy_name, strategy in self.strategies.items():
                        try:
                            # Generate signals
                            signal_df = strategy.generate_signals(df)
                            
                            # Extract triggered signals
                            triggered_signals = signal_df[signal_df['signal_triggered']]
                            
                            # Add signals to the list with metadata
                            for idx, row in triggered_signals.iterrows():
                                signal = {
                                    'timestamp': idx,
                                    'symbol': symbol,
                                    'timeframe': timeframe,
                                    'strategy': strategy_name,
                                    'strategy_name': strategy.name,
                                    'direction': 'LONG' if row['signal'] == 1 else 'SHORT',
                                    'confidence': row['confidence'],
                                    'price': row['close'],
                                    'profit_target': row['profit_target'],
                                    'stop_loss': row['stop_loss'],
                                    'atr': row['atr']
                                }
                                signals.append(signal)
                                
                        except Exception as e:
                            logger.error(f"Error applying {strategy_name} to {symbol} {timeframe}: {e}", exc_info=True)
            
            # Filter signals by confidence threshold
            high_confidence_signals = [s for s in signals if s['confidence'] >= self.confidence_threshold]
            logger.info(f"Found {len(high_confidence_signals)} high-confidence signals out of {len(signals)} total")
            
            # Add to pending signals with timestamp
            current_time = time.time()
            for signal in high_confidence_signals:
                # Add timestamp if not present
                if 'scan_time' not in signal:
                    signal['scan_time'] = current_time
                    
            # Add new signals to pending list
            self.pending_signals.extend(high_confidence_signals)
            
            # Clean up old pending signals (older than 8 hours)
            # This prevents signal accumulation over time
            if hasattr(self, 'pending_signals') and self.pending_signals:
                self.pending_signals = [s for s in self.pending_signals if current_time - s.get('scan_time', current_time) < 28800]  # 8 hours
                logger.info(f"Cleaned pending signals queue, {len(self.pending_signals)} signals remaining")
            
        except Exception as e:
            logger.error(f"Error during market scan: {e}", exc_info=True)
            
    def process_pending_signals(self):
        """Process pending signals and send notifications"""
        if not self.pending_signals:
            return
            
        # Reset daily signal count if it's a new day
        current_date = datetime.now().date()
        if current_date != self.last_signals_reset:
            self.reset_daily_signal_count()
            
        # Initialize signal history tracker if it doesn't exist
        if not hasattr(self, 'recent_signal_keys') or not isinstance(self.recent_signal_keys, dict):
            self.recent_signal_keys = {}
            
        # Remove old signal keys (older than 24 hours)
        current_time = time.time()
        self.recent_signal_keys = {k: v for k, v in self.recent_signal_keys.items() if current_time - v < 86400}
            
        # Check if we've reached the daily limit
        if self.signals_sent_today >= self.max_signals_per_day:
            logger.info(f"Daily signal limit reached ({self.max_signals_per_day}). No more signals until tomorrow.")
            return
            
        # First sort by confidence (highest first)
        self.pending_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Then apply additional win probability filters
        high_probability_signals = self.filter_by_win_probability(self.pending_signals)
        logger.info(f"Filtered {len(high_probability_signals)} high win-rate signals from {len(self.pending_signals)} pending signals")
        
        # Use these high probability signals instead of all pending signals
        signals_to_process = high_probability_signals
        
        # Clear original pending signals and replace with filtered ones
        self.pending_signals = signals_to_process
        
        # Apply strategy weights
        weighted_signals = self.apply_strategy_weights()
        
        # Take top signals up to daily limit
        signals_to_send = []
        remaining_slots = self.max_signals_per_day - self.signals_sent_today
        
        for signal in weighted_signals[:remaining_slots]:
            signals_to_send.append(signal)
            
        # Send signals
        for signal in signals_to_send:
            success = self.send_signal(signal)
            if success:
                self.signals_sent_today += 1
                self.signal_history.append(signal)
                self.pending_signals.remove(signal)
                
        # Save remaining signals for next time
        if self.pending_signals:
            logger.info(f"{len(self.pending_signals)} signals remaining in queue")
            
    def filter_by_win_probability(self, signals):
        """
        Apply advanced filtering to select signals with highest win probability
        
        Args:
            signals: List of trading signals
            
        Returns:
            List[Dict]: Filtered signals with highest win probability (>90%)
        """
        # Already sorted by confidence, now add additional filters
        high_probability_signals = []
        
        # Minimum win probability threshold (90%)
        WIN_PROBABILITY_THRESHOLD = 0.9  # 90%
        
        for signal in signals:
            # Add additional filters based on strategy-specific criteria
            strategy = signal['strategy']
            timeframe = signal['timeframe']
            symbol = signal['symbol']
            direction = signal['direction']
            atr = signal.get('atr', 0)
            
            # Skip signals without proper risk management parameters
            if not signal.get('profit_target') or not signal.get('stop_loss'):
                continue
                
            # Calculate risk-reward ratio
            entry_price = signal['price']
            profit_target = signal['profit_target']
            stop_loss = signal['stop_loss']
            
            # Fix DOGE/USDT price scaling issue - ensure price formatting is consistent
            if symbol == 'DOGE/USDT':
                # DOGE price should typically be below 1 USD
                if entry_price > 10:  # If price is abnormally high
                    entry_price = entry_price / 100.0
                    profit_target = profit_target / 100.0
                    stop_loss = stop_loss / 100.0
                    
                    # Update the signal values
                    signal['price'] = entry_price
                    signal['profit_target'] = profit_target
                    signal['stop_loss'] = stop_loss
                    logger.info(f"Corrected DOGE/USDT price scaling: {entry_price:.6f}")
            
            if direction == 'LONG':
                risk = entry_price - stop_loss
                reward = profit_target - entry_price
            else:  # SHORT
                risk = stop_loss - entry_price
                reward = entry_price - profit_target
                
            # Skip invalid risk/reward setups
            if risk <= 0 or reward <= 0:
                continue
                
            risk_reward_ratio = reward / risk
            
            # Only consider signals with good risk-reward ratio (at least 1.5:1)
            if risk_reward_ratio < 1.5:
                continue
                
            # Prefer signals from higher timeframes for reliability
            timeframe_weight = 1.0
            if timeframe == '4h':
                timeframe_weight = 1.5
            elif timeframe == '1h':
                timeframe_weight = 1.3
            elif timeframe == '15m':
                timeframe_weight = 1.0
                
            # Calculate final win probability score - properly scaled between 0-100%
            # Base win probability from confidence (0-100)
            base_probability = min(float(signal['confidence']), 90.0)  # Cap base confidence at 90%
            
            # Apply modifiers (cap each to prevent multiplication from exceeding realistic values)
            timeframe_factor = min(timeframe_weight, 1.1)  # Slight boost for higher timeframes
            risk_reward_factor = min(0.1 * risk_reward_ratio, 1.1)  # Slight boost for good risk/reward
            
            # Calculate final probability with controlled factors
            adjusted_probability = base_probability * (1.0 + ((timeframe_factor - 1.0) * 0.1) + ((risk_reward_factor - 1.0) * 0.1))
            
            # Final cap to ensure realistic values (0-99.9%)
            win_probability = min(adjusted_probability, 99.9)
            
            # Add win probability to signal (stored as a percentage value)
            signal['win_probability'] = round(win_probability, 1)
            
            # Only include signals with win probability > 90%
            if win_probability > WIN_PROBABILITY_THRESHOLD:
                high_probability_signals.append(signal)
                logger.info(f"High win probability signal ({win_probability:.2f}%) for {symbol} {direction}")
            else:
                logger.info(f"Filtered out low probability signal ({win_probability:.2f}%) for {symbol} {direction}")
            
        # Sort by win probability
        high_probability_signals.sort(key=lambda x: x['win_probability'], reverse=True)
        
        # Return only the top signals, respecting daily limit
        available_slots = self.max_signals_per_day - self.signals_sent_today
        return high_probability_signals[:available_slots]
        
    def check_daily_trade_limit(self) -> bool:
        """
        Check if daily trade limit has been reached (15 trades per day)
        
        Returns:
            bool: True if limit reached, False otherwise
        """
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        trades_today = self.trade_log.get(today, [])
        max_trades = self.max_trades_per_day
        
        # Log current trade count vs limit
        if len(trades_today) >= max_trades:
            logger.warning(f"Daily trade limit reached: {len(trades_today)}/{max_trades} trades executed today")
            return True
        else:
            logger.info(f"Daily trade count: {len(trades_today)}/{max_trades} trades executed today")
            return False

    def apply_strategy_weights(self):
        """
        Apply strategy weights to balance signals between strategies
        
        Returns:
            List[Dict]: Weighted and sorted list of signals
        """
        # Group signals by strategy
        strategy_signals = {}
        for signal in self.pending_signals:
            strategy = signal['strategy']
            if strategy not in strategy_signals:
                strategy_signals[strategy] = []
            strategy_signals[strategy].append(signal)
            
        # Apply weights
        weighted_signals = []
        for strategy, signals in strategy_signals.items():
            if strategy == 'supertrend_adx':
                weight = self.supertrend_adx_weight / 100.0
            elif strategy == 'inside_bar':
                weight = self.inside_bar_weight / 100.0
            else:
                weight = 0.5  # Default weight
                
            # Calculate how many signals to take based on weight
            available_slots = self.max_signals_per_day - self.signals_sent_today
            slots_for_strategy = int(available_slots * weight)
            
            # Sort by win probability and take top N
            signals.sort(key=lambda x: x.get('win_probability', x['confidence']/100.0), reverse=True)
            selected_signals = signals[:slots_for_strategy]
            weighted_signals.extend(selected_signals)
            
        # Sort again by win probability
        weighted_signals.sort(key=lambda x: x.get('win_probability', x['confidence']/100.0), reverse=True)
        
        return weighted_signals
        
    def send_signal(self, signal: Dict) -> bool:
        """
        Send a trading signal via Telegram and execute trade if in live mode
        
        Args:
            signal: Signal data dictionary
            
        Returns:
            bool: Success status
        """
        if not self.telegram_token or not self.telegram_chat_id:
            logger.warning("Telegram not configured, skipping signal notification")
            return False
            
        # Create a unique key for this signal to prevent duplicates
        symbol = signal['symbol']
        direction = signal['direction']
        strategy = signal['strategy']
        timeframe = signal['timeframe']
        price = signal.get('price', 0)
        
        # Create a signal fingerprint
        signal_key = f"{symbol}-{direction}-{strategy}-{timeframe}-{price:.6f}"
        
        # Check if we've sent this signal recently (within 24 hours)
        current_time = time.time()
        if signal_key in self.recent_signal_keys:
            last_sent = self.recent_signal_keys[signal_key]
            hours_since_last = (current_time - last_sent) / 3600
            
            # If the same signal was sent in the last 4 hours, skip it
            if hours_since_last < 4:
                logger.info(f"Skipping duplicate signal: {signal_key} (last sent {hours_since_last:.1f} hours ago)")
                return False
                
        # Record this signal as sent
        self.recent_signal_keys[signal_key] = current_time
            
        try:
            # Format signal message
            message = self._format_signal_message(signal)
            
            # Execute the trade if we're not in test mode
            if not self.test_mode:
                from src.integrations.bidget import TradingAPI
                api = TradingAPI()
                
                if api.is_configured:
                    symbol = signal['symbol']
                    
                    # Skip if we already have an active trade for this symbol
                    if symbol in self.active_trades:
                        logger.info(f"Skipping signal for {symbol} as there's already an active trade")
                        return False
                    
                    # Store API reference for reuse
                    self.trading_api = api
                    
                    # Initialize order manager if not already done
                    if self.order_manager is None:
                        self.order_manager = OrderManager(api)
                        logger.info("OrderManager initialized for OCO order handling")
                    
                    logger.info(f"Executing trade for signal: {symbol} {signal['direction']}")
                    
                    # Use OrderManager for trade execution with OCO orders
                    try:
                        # Extract trade details
                        direction = signal['direction']
                        price = signal['price']
                        profit_target = signal['profit_target']
                        stop_loss = signal['stop_loss']
                        
                        # Calculate position size (this is normally done in the API's execute_signal)
                        account_info = api.get_account_info()
                        if 'error' in account_info:
                            logger.error(f"Failed to get account balance: {account_info['error']}")
                            
                            # Use notification cache for error notifications
                            error_key = f"account_info:{symbol.replace('/', '_')}"
                            
                            if notification_cache.should_send('error', key=error_key):
                                message += f"\n\n⚠️ *Trade Execution Failed*: Could not get account balance"
                                return self._send_telegram_message(message)
                            else:
                                logger.info(f"Suppressing duplicate account error notification for {symbol}")
                                return False
                            
                        available_balance = float(account_info.get('available_balance', 0))
                        position_value = available_balance * 0.25  # Use 25% of balance per trade
                        
                        # Ensure minimum position value of $20 to meet Bitget requirements
                        MIN_POSITION_VALUE = 20.0  # $20 USD minimum
                        if position_value < MIN_POSITION_VALUE:
                            if available_balance >= MIN_POSITION_VALUE:
                                logger.warning(f"Increasing position value from ${position_value:.2f} to ${MIN_POSITION_VALUE:.2f} to meet Bitget minimum order value")
                                position_value = MIN_POSITION_VALUE
                            else:
                                logger.error(f"Insufficient balance: ${available_balance:.2f} < ${MIN_POSITION_VALUE:.2f} required")
                                
                                # Use the notification cache to check if we should send this alert
                                symbol_key = symbol.replace('/', '_')  # Create a cache key from the symbol
                                
                                if notification_cache.should_send('insufficient_balance', key=symbol_key):
                                    # We are allowed to send this notification
                                    logger.info(f"Sending insufficient balance notification for {symbol} (${available_balance:.2f})")
                                    message += f"\n\n⚠️ *Trade Execution Failed*: Insufficient balance (${available_balance:.2f})"
                                    return self._send_telegram_message(message)
                                else:
                                    # Skip notification but still log the error
                                    logger.info(f"Suppressing duplicate insufficient balance notification for {symbol}")
                                    return False  # Return without sending notification
                        
                        # Get current market price if needed
                        current_price = api.get_current_price(symbol)
                        if 'error' in current_price:
                            logger.warning(f"Could not get current price for {symbol}, using signal price")
                            current_price = price
                        else:
                            current_price = float(current_price.get('price', price))
                            
                        # Calculate quantity based on position value and current price
                        quantity = position_value / current_price
                        
                        # Place the order with OCO
                        result = self.order_manager.place_main_order_with_tpsl(
                            symbol=symbol,
                            direction=direction,
                            quantity=quantity,
                            entry_price=None,  # Use market order
                            take_profit=profit_target,
                            stop_loss=stop_loss
                        )
                        
                        if 'main_order' in result and 'error' not in result['main_order']:
                            logger.info(f"Trade executed successfully with OCO orders: {result}")
                            message += f"\n\n✅ *Trade Executed Successfully with OCO Orders*"
                            
                            # Track this symbol as having an active trade
                            self.active_trades.add(symbol)
                            
                            # Add TP/SL details to message
                            message += f"\n\n📊 *Order Details:*"
                            message += f"\n• Main order: {result['main_order'].get('orderId', 'N/A')}"
                            
                            if result['take_profit_order'] and 'error' not in result['take_profit_order']:
                                message += f"\n• Take-profit set: ✓"
                            else:
                                tp_error = result.get('take_profit_order', {}).get('error', 'Failed to set')
                                message += f"\n• Take-profit: ❌ ({tp_error})"
                                
                            if result['stop_loss_order'] and 'error' not in result['stop_loss_order']:
                                message += f"\n• Stop-loss set: ✓"
                            else:
                                sl_error = result.get('stop_loss_order', {}).get('error', 'Failed to set')
                                message += f"\n• Stop-loss: ❌ ({sl_error})"
                            
                            # If confidence threshold was temporarily lowered, restore it after successful trade
                            if hasattr(self, 'restore_confidence_after_trade') and self.restore_confidence_after_trade:
                                logger.info(f"DIAGNOSTIC: Restoring confidence threshold from {self.confidence_threshold}% to {self.original_confidence_threshold}%")
                                self.confidence_threshold = self.original_confidence_threshold
                                self.restore_confidence_after_trade = False
                                # Send Telegram notification about the diagnostic test
                                self._send_telegram_message(f"🔍 *Diagnostic Test Complete*\n\nConfidence threshold has been restored to {self.confidence_threshold}%\n\nTemporary 50% threshold was used for testing purposes.")
                        else:
                            error_msg = result.get('main_order', {}).get('error', 'Unknown error during order placement')
                            logger.error(f"Trade execution failed: {error_msg}")
                            message += f"\n\n⚠️ *Trade Execution Failed*: {error_msg}"
                            
                    except Exception as e:
                        logger.error(f"Exception during OCO order placement: {str(e)}", exc_info=True)
                        message += f"\n\n⚠️ *Trade Execution Error*: {str(e)}"
                else:
                    logger.warning("Trading API not configured, skipping trade execution")
            
            # Send Telegram message
            success = self._send_telegram_message(message)
            
            if success:
                self.signals_sent_today += 1
                self.signal_history.append(signal)
                logger.info(f"Signal sent successfully ({self.signals_sent_today}/{self.max_signals_per_day} today)")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending signal: {e}", exc_info=True)
            return False
            
    def _format_signal_message(self, signal: Dict) -> str:
        """
        Format a signal as a message for notification
        
        Args:
            signal: Signal data dictionary
            
        Returns:
            str: Formatted message
        """
        symbol = signal['symbol']
        direction = signal['direction']
        timeframe = signal['timeframe']
        strategy_name = signal['strategy_name']
        confidence = signal['confidence']
        price = signal['price']
        profit_target = signal['profit_target']
        stop_loss = signal['stop_loss']
        win_probability = signal.get('win_probability', confidence)  # Already a percentage value
        
        # Calculate risk-reward ratio
        if direction == "LONG":
            risk = price - stop_loss
            reward = profit_target - price
        else:  # SHORT
            risk = stop_loss - price
            reward = price - profit_target
            
        risk_reward_ratio = reward / max(risk, 0.0001)  # Avoid division by zero
        
        # Determine appropriate decimal places based on asset and price
        # Small value assets like DOGE need more decimals
        if 'DOGE' in symbol or price < 1.0:
            price_decimals = 6
        elif price < 10.0:
            price_decimals = 5
        elif price < 100.0:
            price_decimals = 4
        elif price < 1000.0:
            price_decimals = 3
        else:
            price_decimals = 2
            
        emoji = "🟢" if direction == "LONG" else "🔴"
        
        # Format the message with appropriate decimals
        message = f"{emoji} *{direction} Signal: {symbol}*\n"
        message += f"*Strategy:* {strategy_name}\n"
        message += f"*Timeframe:* {timeframe}\n"
        message += f"*Confidence:* {confidence:.1f}%\n"
        message += f"*Win Probability:* {win_probability:.1f}%\n"
        message += f"*Risk/Reward:* 1:{risk_reward_ratio:.2f}\n"
        message += f"*Entry Price:* {price:.{price_decimals}f}\n"
        message += f"*Take Profit:* {profit_target:.{price_decimals}f}\n"
        message += f"*Stop Loss:* {stop_loss:.{price_decimals}f}\n"
        message += f"*Date/Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return message
        
    def _send_telegram_message(self, message: str):
        """Send a message via Telegram"""
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = {
            "chat_id": self.telegram_chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=data)
        if response.status_code != 200:
            logger.error(f"Telegram API error: {response.text}")
            
    def reset_daily_counts(self):
        """Reset daily signal and trade counts"""
        self.daily_signals = []
        self.daily_trades_count = 0
        self.last_signals_reset = datetime.now().date()
        logger.info("Reset daily signal and trade counts")
        
        # Generate analytics summary when daily counts are reset
        if ANALYTICS_AVAILABLE:
            try:
                self._generate_analytics_summary()
            except Exception as e:
                logger.error(f"Failed to generate analytics summary on daily reset: {e}", exc_info=True)
                
    def _generate_analytics_summary(self) -> None:
        """
        Generate daily and weekly analytics summaries
        """
        if not ANALYTICS_AVAILABLE:
            return
            
        try:
            # Generate daily summary
            daily_summary = analytics_logger.generate_daily_summary(force=False)
            if daily_summary:
                logger.info("Generated daily analytics summary")
                
                # Send summary notification via Telegram if available
                if TELEGRAM_AVAILABLE and self.telegram and self.telegram.is_configured:
                    summary_msg = self._format_daily_summary_message(daily_summary)
                    self.telegram.send_message(summary_msg)
            
            # Check if we should generate a weekly summary (Mondays)
            today = datetime.now().date()
            if today.weekday() == 0:  # Monday
                weekly_summary = analytics_logger.generate_weekly_summary()
                if weekly_summary:
                    logger.info("Generated weekly analytics summary")
                    
                    # Send weekly summary via Telegram if available
                    if TELEGRAM_AVAILABLE and self.telegram and self.telegram.is_configured:
                        weekly_msg = self._format_weekly_summary_message(weekly_summary)
                        self.telegram.send_message(weekly_msg)
        except Exception as e:
            logger.error(f"Error generating analytics summary: {e}", exc_info=True)
            
    def _format_daily_summary_message(self, summary: Dict) -> str:
        """
        Format daily summary for Telegram notification
        
        Args:
            summary: Daily summary data
            
        Returns:
            Formatted message string
        """
        date_str = summary.get('date', 'Unknown')
        
        # Extract key metrics
        trades = summary.get('trades', {})
        signals = summary.get('signals', {})
        strategies = summary.get('strategies', {})
        performance = summary.get('performance', {})
        
        # Format message
        msg = f"📊 *Daily Summary for {date_str}*\n\n"
        
        # Add trade stats
        msg += "*Trading Performance*\n"
        msg += f"Total Trades: {trades.get('total', 0)}\n"
        msg += f"Win Rate: {trades.get('win_rate', 0) * 100:.1f}%\n"
        msg += f"Net P&L: {trades.get('net_pnl', 0):.2f} USDT\n\n"
        
        # Add signal stats
        msg += "*Signal Performance*\n"
        msg += f"Total Signals: {signals.get('total', 0)}\n"
        msg += f"Execution Rate: {signals.get('execution_rate', 0) * 100:.1f}%\n\n"
        
        # Add strategy performance
        msg += "*Strategy Performance*\n"
        for strategy_name, metrics in strategies.items():
            accuracy = metrics.get('accuracy', 0) * 100
            msg += f"{strategy_name}: {metrics.get('signals', 0)} signals, {accuracy:.1f}% accuracy\n"
        
        # Add system performance
        if 'api_calls' in performance:
            api_perf = performance.get('api_calls', {})
            msg += "\n*System Performance*\n"
            msg += f"API Success Rate: {api_perf.get('success_rate', 0) * 100:.1f}%\n"
            msg += f"Avg API Response: {api_perf.get('avg_duration_ms', 0):.1f} ms\n"
        
        return msg
        
    def _format_weekly_summary_message(self, summary: Dict) -> str:
        """
        Format weekly summary for Telegram notification
        
        Args:
            summary: Weekly summary data
            
        Returns:
            Formatted message string
        """
        period = summary.get('period', 'Unknown')
        
        # Extract key metrics
        trades = summary.get('trades', {})
        signals = summary.get('signals', {})
        strategies = summary.get('strategies', {})
        daily_breakdown = summary.get('daily_breakdown', {})
        
        # Format message
        msg = f"📈 *Weekly Trading Summary*\n{period}\n\n"
        
        # Add trade stats
        msg += "*Weekly Performance*\n"
        msg += f"Total Trades: {trades.get('total', 0)}\n"
        msg += f"Win Rate: {trades.get('win_rate', 0) * 100:.1f}%\n"
        msg += f"Net P&L: {trades.get('net_pnl', 0):.2f} USDT\n\n"
        
        # Add signal stats
        msg += "*Signal Analytics*\n"
        msg += f"Total Signals: {signals.get('total', 0)}\n"
        msg += f"Execution Rate: {signals.get('execution_rate', 0) * 100:.1f}%\n\n"
        
        # Add strategy performance
        msg += "*Top Strategies*\n"
        for strategy_name, metrics in strategies.items():
            success_rate = metrics.get('estimated_success_rate', 0) * 100
            msg += f"{strategy_name}: {success_rate:.1f}% est. success rate\n"
        
        # Add daily breakdown
        if daily_breakdown:
            msg += "\n*Daily Breakdown*\n"
            for date, metrics in sorted(daily_breakdown.items()):
                trades_count = metrics.get('trades', 0)
                pnl = metrics.get('net_pnl', 0)
                msg += f"{date}: {trades_count} trades, {pnl:.2f} USDT\n"
        
        return msg
        
    def _initial_market_regime_check(self) -> bool:
        """
        Initial market regime check after bot startup
        
        Returns:
            True if check was successful
        """
        result = self._check_market_regime()
        
        # Clear the startup schedule tag
        schedule.clear('startup')
        
        return result
        
    def _check_market_regime(self) -> bool:
        """
        Check market regime and apply appropriate parameter profile
        
        Returns:
            True if check was successful
        """
        if not MARKET_ANALYZER_AVAILABLE:
            return False
            
        try:
            # Get latest market data for analysis
            primary_symbol = 'BTC/USDT'  # Use BTC as primary indicator
            timeframes = ['1h', '4h']    # Use multiple timeframes for better analysis
            ohlcv_data = {}
            
            # Get OHLCV data for analysis
            for tf in timeframes:
                try:
                    if not hasattr(self, 'market_data') or self.market_data is None:
                        logger.error("Market data module not initialized")
                        return False
                        
                    # Get data for primary symbol
                    ohlcv = self.market_data.get_market_data(primary_symbol, tf)
                    if ohlcv is not None and len(ohlcv) > 0:
                        ohlcv_data[f"{primary_symbol}_{tf}"] = ohlcv
                except Exception as e:
                    logger.error(f"Error getting {tf} data for {primary_symbol}: {e}")
            
            if not ohlcv_data:
                logger.error("No market data available for regime detection")
                return False
                
            # Update market regime
            regime, confidence = market_analyzer.update_market_regime(ohlcv_data, primary_symbol)
            
            # Store current regime
            self.market_regime = regime.name if hasattr(regime, 'name') else str(regime)
            self.last_regime_check = datetime.now()
            
            # Log regime change
            logger.info(f"Market regime detected: {self.market_regime} (confidence: {confidence:.2f})")
            
            # Send notification on significant regime changes
            if TELEGRAM_AVAILABLE and self.telegram and self.telegram.is_configured:
                # Only notify on high confidence regime changes
                if confidence >= 0.7:
                    msg = f"📉 *Market Regime Update*\n\n"
                    msg += f"Current Regime: *{self.market_regime}*\n"
                    msg += f"Confidence: {confidence*100:.1f}%\n\n"
                    
                    # Add strategy recommendation based on regime
                    if self.market_regime == "STRONG_UPTREND":
                        msg += "🔥 Strong bullish trend detected - aggressive trading profile active\n"
                    elif self.market_regime == "WEAK_UPTREND":
                        msg += "📈 Bullish trend detected - standard trading profile active\n"
                    elif self.market_regime == "RANGING":
                        msg += "⚖️ Sideways market detected - conservative approach recommended\n"
                    elif self.market_regime == "WEAK_DOWNTREND":
                        msg += "📉 Bearish trend detected - conservative profile active\n"
                    elif self.market_regime == "STRONG_DOWNTREND":
                        msg += "⚠️ Strong bearish trend detected - defensive profile active\n"
                    elif self.market_regime == "HIGH_VOLATILITY":
                        msg += "🔄 High volatility detected - conservative approach active\n"
                    
                    # Send notification
                    self.telegram.send_message(msg)
                    
            return True
            
        except Exception as e:
            logger.error(f"Error checking market regime: {e}", exc_info=True)
            return False
            
    def run_market_backtest(self, days_back: int = 30) -> Dict[str, Any]:
        """
        Run market regime detection backtest on historical data
        
        Args:
            days_back: Number of days to backtest
            
        Returns:
            Backtest results dictionary
        """
        if not MARKET_ANALYZER_AVAILABLE:
            return {
                "success": False,
                "error": "Market analyzer not available"
            }
            
        try:
            # Get historical market data
            primary_symbol = 'BTC/USDT'  # Use BTC as primary indicator
            timeframes = ['1h', '4h']    # Use multiple timeframes
            
            # Calculate start time
            end_time = int(time.time() * 1000)  # Current time in milliseconds
            start_time = end_time - (days_back * 24 * 60 * 60 * 1000)  # days_back days ago
            
            # Get historical data
            historical_data = {}
            
            for tf in timeframes:
                try:
                    if not hasattr(self, 'market_data') or self.market_data is None:
                        return {
                            "success": False,
                            "error": "Market data module not initialized"
                        }
                        
                    # Get historical data
                    ohlcv = self.market_data.get_historical_data(
                        symbol=primary_symbol,
                        timeframe=tf,
                        since=start_time
                    )
                    
                    if ohlcv is not None and len(ohlcv) > 0:
                        historical_data[f"{primary_symbol}_{tf}"] = ohlcv
                        
                except Exception as e:
                    logger.error(f"Error getting historical {tf} data for {primary_symbol}: {e}")
            
            if not historical_data:
                return {
                    "success": False,
                    "error": "No historical data available for backtest"
                }
                
            # Run backtest
            backtest_results = market_analyzer.backtest_regimes(historical_data, primary_symbol)
            
            # Log backtest completion
            if backtest_results.get('success', False):
                logger.info(f"Market regime backtest completed: {len(backtest_results.get('regime_timeline', []))} data points analyzed")
            else:
                logger.error(f"Market regime backtest failed: {backtest_results.get('error', 'Unknown error')}")
                
            return backtest_results
            
        except Exception as e:
            logger.error(f"Error in market backtest: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
        
    def check_and_clean_active_trades(self, force_reset=False, symbol_to_reset=None):
        """Check active trades and remove closed ones from the tracking list
        
        Args:
            force_reset (bool): If True, force reset tracking for all positions or specific symbol
            symbol_to_reset (str): Optional specific symbol to reset tracking for
        """
        logger.info("Starting active trade cleanup check - scheduled task")
        if self.test_mode:
            logger.info("Test mode: Skipping active trade check")
            return
            
        # Handle forced reset cases first
        if force_reset:
            if symbol_to_reset:
                if symbol_to_reset in self.active_trades:
                    logger.info(f"FORCED RESET: Removing {symbol_to_reset} from active trades tracking")
                    self.active_trades.remove(symbol_to_reset)
                    close_msg = f"🔄 *Tracking Reset* - {symbol_to_reset}\n\nForced removal from active trades tracking. The bot will now consider new signals for this pair."
                    self._send_telegram_message(close_msg)
                else:
                    logger.info(f"FORCED RESET: {symbol_to_reset} was not in active trades list")
                return
            else:
                # Reset all active trades
                logger.info(f"FORCED RESET: Clearing all active trades tracking ({len(self.active_trades)} positions)")
                symbol_list = list(self.active_trades)  # Create a copy for the message
                self.active_trades.clear()
                close_msg = f"🔄 *All Tracking Reset*\n\nForced removal of all positions from active trades tracking.\nCleared positions: {', '.join(symbol_list) if symbol_list else 'none'}\n\nThe bot will now consider new signals for all pairs."
                self._send_telegram_message(close_msg)
                return
            
        try:
            from src.integrations.bidget import TradingAPI
            api = TradingAPI()
            
            if not api.is_configured:
                logger.warning("Trading API not configured, skipping active trade check")
                return
                
            # Make a copy of active_trades to avoid modifying during iteration
            symbols_to_check = list(self.active_trades)
            
            if not symbols_to_check:
                logger.info("No active trades to check")
                return
                
            logger.info(f"Checking {len(symbols_to_check)} active trades for closure: {symbols_to_check}")
            
            # Track symbols that couldn't be verified due to API errors
            failed_checks = []
            
            for symbol in symbols_to_check:
                retry_count = 0
                max_retries = 2  # Try up to 3 times (initial + 2 retries)
                
                while retry_count <= max_retries:
                    try:
                        # Convert symbol format if needed (e.g., 'BTC/USDT' to 'BTCUSDT_UMCBL')
                        formatted_symbol = symbol.replace('/', '') + '_UMCBL'
                        
                        # Check if there's still an active position
                        position_endpoint = f"/api/mix/v1/position/singlePosition?symbol={formatted_symbol}&marginCoin=USDT"
                        position_info = api._make_request("GET", position_endpoint, signed=True)
                        
                        active_position = False
                        position_size = 0
                        
                        if 'error' not in position_info and 'data' in position_info:
                            position_data = position_info.get('data', {})
                            logger.info(f"Position data for {symbol}: {position_data}")
                            
                            # Handle if position_data is a list (some Bitget endpoints return list)
                            if isinstance(position_data, list):
                                for pos in position_data:
                                    position_size = float(pos.get('total', 0)) if isinstance(pos, dict) else 0
                                    if position_size > 0:
                                        active_position = True
                                        break
                            elif isinstance(position_data, dict):
                                position_size = float(position_data.get('total', 0))
                                if position_size > 0:
                                    active_position = True
                            
                            # Successfully checked the position, break retry loop
                            break
                        else:
                            logger.warning(f"Failed to get position info for {symbol}: {position_info}")
                            # Only retry on API errors, not on "no position" responses
                            if retry_count < max_retries:
                                retry_count += 1
                                logger.info(f"Retrying position check for {symbol} (attempt {retry_count+1}/{max_retries+1})")
                                time.sleep(2)  # Brief delay before retry
                            else:
                                failed_checks.append(symbol)
                                break
                    except Exception as e:
                        if retry_count < max_retries:
                            retry_count += 1
                            logger.warning(f"Error checking position for {symbol}, retrying (attempt {retry_count+1}/{max_retries+1}): {str(e)}")
                            time.sleep(2)  # Brief delay before retry
                        else:
                            logger.error(f"Final error checking position for {symbol}: {str(e)}", exc_info=True)
                            failed_checks.append(symbol)
                            break
                
                # Only process position if we didn't add it to failed_checks
                if symbol not in failed_checks:
                    logger.info(f"Position check for {symbol}: active={active_position}, size={position_size}")
                    
                    # If no active position, remove from tracking list
                    if not active_position:
                        self.active_trades.remove(symbol)
                        logger.info(f"Removed {symbol} from active trades - position closed")
                        
                        # Notify via Telegram
                        close_msg = f"🔔 *Position Closed* - {symbol}\n\nThe bot will now consider new signals for this pair."
                        self._send_telegram_message(close_msg)
            
            # Report on failed checks but don't remove them from tracking
            if failed_checks:
                logger.warning(f"Could not verify status for {len(failed_checks)} positions due to API errors: {failed_checks}")
            
            logger.info(f"Active trades after cleanup: {self.active_trades}")
        except Exception as e:
            logger.error(f"Error during active trade cleanup: {str(e)}", exc_info=True)
        
    def prepare_bidget_integration(self):
        """
        Placeholder for Bidget API integration
        """
        # This method will be implemented when Bidget API details are provided
        logger.info("Bidget API integration ready for configuration")
        
    def get_active_signals(self):
        """
        Get currently active signals for the dashboard
        
        Returns:
            List[Dict]: List of active signals with their status
        """
        try:
            # Return a copy of active signals to avoid modifications
            # Format timestamps and ensure consistent structure
            formatted_signals = []
            for signal in self.active_signals:
                formatted_signal = signal.copy()
                
                # Ensure timestamp is ISO format string
                if isinstance(formatted_signal.get('timestamp'), datetime):
                    formatted_signal['timestamp'] = formatted_signal['timestamp'].isoformat()
                    
                # Ensure strategy name is formatted
                if 'strategy_id' in formatted_signal and 'strategy_name' not in formatted_signal:
                    strategy_id = formatted_signal['strategy_id']
                    formatted_signal['strategy_name'] = strategy_id.replace('_', ' ').title()
                    
                formatted_signals.append(formatted_signal)
                
            return formatted_signals
        except Exception as e:
            logger.error(f"Error getting active signals: {str(e)}", exc_info=True)
            return []
    
    def get_signals_today_count(self):
        """
        Get count of signals generated today
        
        Returns:
            int: Number of signals generated today
        """
        # Check if we need to reset daily counters
        current_date = datetime.now().date()
        if current_date != self.last_signals_reset:
            self.reset_daily_counters()
            
        return self.signals_today
    
    def get_trades_today_count(self):
        """
        Get count of trades executed today
        
        Returns:
            int: Number of trades executed today
        """
        # Check if we need to reset daily counters
        current_date = datetime.now().date()
        if current_date != self.last_signals_reset:
            self.reset_daily_counters()
            
        return self.trades_today
    
    def toggle_strategy(self, strategy_id, enabled):
        """
        Enable or disable a strategy
        
        Args:
            strategy_id (str): ID of the strategy to toggle
            enabled (bool): Whether to enable or disable the strategy
            
        Returns:
            Dict: Status and info about the operation
        """
        try:
            # Validate strategy_id
            if strategy_id not in self.strategies:
                return {
                    "success": False,
                    "message": f"Invalid strategy ID: {strategy_id}"
                }
                
            # Set enabled status
            self.signals_enabled[strategy_id] = enabled
            status = "enabled" if enabled else "disabled"
            
            # Log the change
            logger.info(f"Strategy '{strategy_id}' {status}")
            
            # Send notification via Telegram
            if self.telegram and self.telegram.is_configured:
                strategy_name = strategy_id.replace('_', ' ').title()
                message = f"🔧 *Strategy {status.title()}*: {strategy_name}\n\n"
                message += "This change was made from the dashboard."
                self._send_telegram_message(message)
                
            # Log to analytics if available
            if ANALYTICS_AVAILABLE:
                try:
                    analytics_logger.log_event(
                        event_type="strategy_toggle",
                        metadata={
                            "category": "configuration",
                            "strategy_id": strategy_id,
                            "enabled": enabled
                        }
                    )
                except Exception as e:
                    logger.error(f"Error logging strategy toggle to analytics: {str(e)}")
                    
            return {
                "success": True,
                "strategy_id": strategy_id,
                "enabled": enabled,
                "message": f"Strategy '{strategy_id}' {status}"
            }
        except Exception as e:
            logger.error(f"Error toggling strategy {strategy_id}: {str(e)}", exc_info=True)
            return {
                "success": False,
                "strategy_id": strategy_id,
                "message": f"Error: {str(e)}"
            }
    
    def reset_daily_counters(self):
        """
        Reset daily signal and trade counters
        """
        try:
            # Reset counters
            self.signals_today = 0
            self.trades_today = 0
            self.last_signals_reset = datetime.now().date()
            
            logger.info("Daily signal and trade counters reset")
            
            return True
        except Exception as e:
            logger.error(f"Error resetting daily counters: {str(e)}", exc_info=True)
            return False
            
    def track_signal(self, signal):
        """
        Track a new signal for dashboard monitoring
        
        Args:
            signal (Dict): Signal data
            
        Returns:
            bool: Success status
        """
        try:
            # Add timestamp if not present
            if 'timestamp' not in signal:
                signal['timestamp'] = datetime.now()
                
            # Add to active signals
            self.active_signals.append(signal)
            
            # Increment signals today counter
            self.signals_today += 1
            
            # Keep max 100 signals in memory
            if len(self.active_signals) > 100:
                self.active_signals = self.active_signals[-100:]
                
            return True
        except Exception as e:
            logger.error(f"Error tracking signal: {str(e)}", exc_info=True)
            return False
            
    def track_trade(self, trade):
        """
        Track a new executed trade
        
        Args:
            trade (Dict): Trade data
            
        Returns:
            bool: Success status
        """
        try:
            # Increment trades today counter
            self.trades_today += 1
            
            # Update signal status if present
            signal_id = trade.get('signal_id')
            if signal_id:
                for signal in self.active_signals:
                    if signal.get('id') == signal_id:
                        signal['status'] = 'executed'
                        break
                        
            return True
        except Exception as e:
            logger.error(f"Error tracking trade: {str(e)}", exc_info=True)
            return False
