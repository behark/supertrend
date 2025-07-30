#!/usr/bin/env python3
"""
Cryptocurrency Telegram Alert Bot
--------------------------------
This bot scans cryptocurrency markets and sends alerts to Telegram
based on technical indicators, with advanced features:
1. Volume + Price Spike Alert
2. Moving Averages (MA) Cross
3. Breakout Strategy Trigger
4. Backtesting and Performance Analysis
5. Machine Learning Signal Quality Prediction
6. Multi-Timeframe Confirmation
7. Direct Trading Capabilities (with Safeguards)
8. Portfolio Management and Tracking
9. Custom Telegram Alert Configuration
10. Performance Dashboard
"""
import os
import time
import logging

# Import configuration settings
from config import MAX_DAILY_TRADES, MIN_SUCCESS_PROBABILITY, SETTINGS
import schedule
import threading
import argparse
from datetime import datetime, date
from dotenv import load_dotenv
import ccxt
import pandas as pd
import numpy as np
import json

# Local modules
from telegram_client import TelegramClient
from telegram_commands import TelegramCommandHandler
from indicators import (
    check_volume_price_spike, 
    check_ma_cross, 
    check_breakout,
    rsi,
    calculate_risk_metrics
)
from smart_filter import SmartFilter
from risk_manager import RiskManager
from chart_generator import ChartGenerator
from backtester import Backtester
from ml_predictor import MLPredictor
from trader import Trader
from bybit_trader import BybitTrader
from market_regime import MarketRegime
from trade_planner import SmartTradePlanner
from playbook import Playbook
from trade_memory import initialize_trade_memory, get_trade_memory
from auto_recovery import initialize_recovery_engine, get_recovery_engine
from multi_timeframe import MultiTimeframeAnalyzer
from portfolio_manager import PortfolioManager
from dashboard import Dashboard
from bidget_enhancements import BidgetEnhancements
from config import (
    EXCHANGES,
    SCAN_INTERVAL,
    SYMBOLS_TO_SCAN,
    PROFIT_TARGET,
    RISK_REWARD_RATIO,
    TIMEFRAMES,
    VOLUME_THRESHOLD,
    PRICE_CHANGE_THRESHOLD,
    FAST_MA,
    SLOW_MA,
    BREAKOUT_PERIODS,
    MAX_DRAWDOWN_PERCENT,
    MIN_DAILY_VOLUME,
    MIN_SUCCESS_PROBABILITY,
    MAX_POSITION_SIZE_PERCENT,
    MAX_COIN_PRICE,
    LEVERAGE,
    BALANCE_PERCENTAGE,
    FUTURES_ONLY,
    MAX_TELEGRAM_SIGNALS
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crypto_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Global instances
telegram_client = None
telegram_commands = None
trader = None
portfolio_manager = None
dashboard_thread = None
backtester = None
ml_predictor = None
smart_filter = None
bidget_enhancements = None

# Daily trade counter
daily_trade_count = 0
today_date = date.today().isoformat()

# File to store daily trade counts
TRADE_COUNT_FILE = 'data/trade_counts.json'

# Create output directories
os.makedirs('charts', exist_ok=True)
os.makedirs('data', exist_ok=True)

def get_exchange_instance(exchange_id):
    """Initialize and return exchange instance."""
    try:
        # For Bidget, we only use Bybit
        main_exchange = 'bybit'
        exchange_class = getattr(ccxt, main_exchange)
        exchange = exchange_class({
            'apiKey': os.getenv(f'{main_exchange.upper()}_API_KEY', ''),
            'secret': os.getenv(f'{main_exchange.upper()}_SECRET_KEY', ''),
            'enableRateLimit': True,
        })
        return exchange
    except Exception as e:
        logger.error(f"Error initializing exchange {exchange_id}: {str(e)}")
        return None

def fetch_ohlcv(exchange, symbol, timeframe):
    """Fetch OHLCV data for a specific symbol and timeframe."""
    try:
        logger.debug(f"Fetching OHLCV for {symbol} on {exchange.id} with timeframe {timeframe}")
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe)
        if ohlcv is None:
            logger.warning(f"OHLCV data is None for {symbol} on {exchange.id}")
            return None
            
        if len(ohlcv) == 0:
            logger.warning(f"OHLCV data is empty for {symbol} on {exchange.id}")
            return None
            
        logger.debug(f"Got {len(ohlcv)} candles for {symbol}")
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        logger.error(f"Error fetching OHLCV for {symbol} on {exchange.id}: {str(e)}")
        return None

def analyze_symbol(exchange, symbol, timeframe):
    """Analyze a symbol using all technical indicators and send alerts if conditions are met."""
    global smart_filter, bidget_enhancements
    
    # Skip symbols that don't match our Bidget criteria
    if not smart_filter.check_timeframe(timeframe):
        logger.debug(f"Skipping {symbol} on {timeframe} - timeframe not in allowed range")
        return
    
    logger.debug(f"Analyzing {symbol} on {timeframe}")
    df = fetch_ohlcv(exchange, symbol, timeframe)
    
    if df is None:
        logger.debug(f"Skipping {symbol} analysis - OHLCV data is None")
        return
        
    try:
        min_data_points = max(SLOW_MA, BREAKOUT_PERIODS)
        logger.debug(f"Data points required: {min_data_points}, available: {len(df)}")
        
        if len(df) < min_data_points:
            logger.debug(f"Skipping {symbol} analysis - insufficient data points")
            return
    except Exception as e:
        logger.error(f"Error checking data length for {symbol}: {str(e)}")
        return
    
    # Get market info for position sizing
    try:
        ticker = exchange.fetch_ticker(symbol)
        volume_24h = ticker['quoteVolume'] if 'quoteVolume' in ticker else ticker['volume']
        
        # Get current price for Bidget price filter
        current_price = ticker['last']
        
        # Skip if price is too high (above $1 for Bidget)
        if not smart_filter.check_price(current_price):
            logger.debug(f"Skipping {symbol} - price ${current_price:.4f} > ${MAX_COIN_PRICE:.2f}")
            return
    except Exception as e:
        logger.error(f"Error fetching ticker for {symbol}: {str(e)}")
        volume_24h = 0
    
    # Calculate estimated position size needed for $100 profit target
    current_price = df.iloc[-1]['close']
    
    alerts = []
    primary_alert_type = None
    
    # Check volume and price spike
    volume_spike = check_volume_price_spike(
        df, 
        volume_threshold=VOLUME_THRESHOLD, 
        price_change_threshold=PRICE_CHANGE_THRESHOLD
    )
    if volume_spike:
        alerts.append({
            'type': 'Volume + Price Spike',
            'message': f"Volume + Price spike detected for {symbol} on {timeframe} timeframe"
        })
        if not primary_alert_type:
            primary_alert_type = 'Volume + Price Spike'
    
    # Check MA cross
    ma_cross = check_ma_cross(df, fast_ma=FAST_MA, slow_ma=SLOW_MA)
    if ma_cross:
        alerts.append({
            'type': 'MA Cross',
            'message': f"MA Cross detected for {symbol} on {timeframe} timeframe (Fast MA: {FAST_MA}, Slow MA: {SLOW_MA})"
        })
        if not primary_alert_type:
            primary_alert_type = 'MA Cross'
    
    # Check breakout
    breakout = check_breakout(df, periods=BREAKOUT_PERIODS)
    if breakout:
        alerts.append({
            'type': 'Breakout',
            'message': f"Breakout detected for {symbol} on {timeframe} timeframe (Periods: {BREAKOUT_PERIODS})"
        })
        if not primary_alert_type:
            primary_alert_type = 'Breakout'
    
    # Send alerts
    if alerts:
        # Calculate entry, stop loss, and take profit
        entry_price = current_price
        
        # Use risk metrics to determine stop loss
        stop_loss, volatility = calculate_risk_metrics(df, entry_price)
        
        # Use risk manager to calculate position size and check if trade is safe
        risk_manager = RiskManager(
            risk_reward_ratio=RISK_REWARD_RATIO,
            max_drawdown_percent=MAX_DRAWDOWN_PERCENT,
            min_daily_volume=MIN_DAILY_VOLUME,
            min_success_probability=MIN_SUCCESS_PROBABILITY
        )
        
        # Calculate position size based on risk parameters
        trader = Trader(
            exchange_id='bybit', 
            config={
                'max_risk_per_trade_percent': MAX_POSITION_SIZE_PERCENT,
                'profit_target': PROFIT_TARGET,
                'leverage': LEVERAGE,
                'balance_percentage': BALANCE_PERCENTAGE,
                'futures_only': FUTURES_ONLY
            },
            dry_run=False
        )
        position_size = risk_manager.calculate_position_size(
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_profit=PROFIT_TARGET,
            max_risk_percent=MAX_POSITION_SIZE_PERCENT,
            symbol=symbol,
            timeframe=timeframe
        )
        
        # Calculate reasonable take profit based on price and risk-reward ratio
        # Use a percentage-based approach instead of absolute dollar values
        price_diff = abs(entry_price - stop_loss)
        take_profit = entry_price + (price_diff * RISK_REWARD_RATIO)
        
        # Check if trade is safe - pass symbol and timeframe to prevent duplicates
        is_safe, safety_reasons = risk_manager.is_safe_trade(
            df=df,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            volume_24h=volume_24h,
            symbol=symbol,
            timeframe=timeframe
        )
        
        if is_safe:
            # Use Smart Trade Planner to generate comprehensive trade plan
            trade_planner = SmartTradePlanner(data_dir='data')
            position_type = 'long' if entry_price < take_profit else 'short'
            
            # Generate trade plan based on market regime and playbook
            trade_plan = trade_planner.plan_trade(
                df=df,
                entry_price=entry_price,
                symbol=symbol,
                timeframe=timeframe,
                position_type=position_type
            )
            
            # Use trade plan's optimized parameters
            stop_loss = trade_plan['stop_loss']
            take_profit_levels = trade_plan['take_profit_levels']
            take_profit = take_profit_levels[0]  # Primary take profit level
            leverage = trade_plan['leverage']
            regime = trade_plan['regime']
            strategy = trade_plan['strategy']
            entry_type = trade_plan['entry_type']
            risk_level = trade_plan['risk_level']
            risk_reward_ratio = trade_plan['risk_reward_ratio']
            
            # Generate chart for the alert
            chart_generator = ChartGenerator(output_dir='charts')
            chart_path = chart_generator.generate_alert_chart(
                df=df,
                symbol=symbol,
                timeframe=timeframe,
                alert_type=primary_alert_type,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            
            # Get the formatted trade plan message
            alert_message = trade_planner.format_trade_plan_message(trade_plan)
            
            # Add signal information to the alert message
            signal_info = "🔔 SIGNALS DETECTED:\n"
            for alert in alerts:
                signal_info += f"✅ {alert['type']}: {alert['message']}\n"
            
            # Add risk analysis
            risk_analysis = "\n🔍 RISK ANALYSIS:\n"
            for reason in safety_reasons:
                risk_analysis += f"✓ {reason}\n"
            
            # Combine all information
            alert_message = alert_message + "\n" + signal_info + "\n" + risk_analysis
            
            # Save the trade plan
            trade_planner.save_trade_plan(trade_plan)
            
            # Build signal data for smart filter
            signal = {
                'symbol': symbol,
                'timeframe': timeframe,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'risk_percentage': risk_percentage,
                'profit_percentage': profit_percentage,
                'position_size': position_size,
                'probability': risk_manager.predict_success_probability(df),
                'volume_24h': volume_24h,
                'alert_types': [alert['type'] for alert in alerts],
                'chart_path': chart_path,
                'message': alert_message
            }
            
            # Apply smart filter for Bidget criteria
            passed_filter, filter_reason = smart_filter.filter_signal(signal)
            
            # Enhanced signal processing with BidgetEnhancements module
            if passed_filter:
                # Process through Bidget enhancements if available
                if bidget_enhancements:
                    try:
                        # Apply signal quality control and enhancement
                        enhanced_signal = bidget_enhancements.process_signal(signal)
                        
                        if enhanced_signal:
                            # Log enhancement details
                            logger.info(f"Signal enhanced: {symbol} {timeframe}")
                            
                            # Update signal parameters with enhanced values
                            if 'position_size' in enhanced_signal:
                                signal['position_size'] = enhanced_signal['position_size']
                                alert_message = alert_message.replace(
                                    f"Position Size: {position_size:.8f}", 
                                    f"Position Size: {enhanced_signal['position_size']:.8f} (Scaled)"
                                )
                            
                            if 'stop_loss' in enhanced_signal:
                                signal['stop_loss'] = enhanced_signal['stop_loss']
                                alert_message = alert_message.replace(
                                    f"Stop Loss: {stop_loss:.8f}",
                                    f"Stop Loss: {enhanced_signal['stop_loss']:.8f} (Enhanced)"
                                )
                            
                            if 'take_profit' in enhanced_signal:
                                signal['take_profit'] = enhanced_signal['take_profit']
                                alert_message = alert_message.replace(
                                    f"Take Profit: {take_profit:.8f}",
                                    f"Take Profit: {enhanced_signal['take_profit']:.8f} (Enhanced)"
                                )
                                
                            if 'confidence_score' in enhanced_signal:
                                signal['confidence_score'] = enhanced_signal['confidence_score']
                                alert_message += f"\n🧮 Confidence Score: {enhanced_signal['confidence_score']:.2f}\n"
                                
                            # Add enhancement info to message
                            alert_message += f"\n🔧 Bidget Enhancements Applied\n"
                            
                            # Check if signal should be delayed for quality control
                            if enhanced_signal.get('delay_signal', False):
                                logger.info(f"Signal delayed for quality control: {symbol} {timeframe}")
                                bidget_enhancements.add_pending_signal(signal)
                                return
                    except Exception as e:
                        logger.error(f"Error in signal enhancement: {str(e)}")
                
                # Add filter reason to message
                # Add confidence scoring and enhancement details
                confidence_score = signal.get('probability', 0) * 100
                alert_message += f"\n🧠 Bidget Smart Filter: {filter_reason}\n"
                alert_message += f"🎯 Confidence Score: {confidence_score:.2f}%\n"
                
                # Add decision rationale
                if 'decision_factors' in signal:
                    alert_message += f"\n📊 Decision Factors:\n"
                    for factor, value in signal['decision_factors'].items():
                        alert_message += f"• {factor}: {value}\n"
                
                # Send message with chart
                telegram_client.send_message(alert_message)
                telegram_client.send_chart(chart_path, caption=f"{symbol} {timeframe} Analysis - {confidence_score:.2f}% Confidence")
                
                # Increment trade count
                increment_trade_count()
                
                # Update confidence dashboard with signal
                if bidget_enhancements:
                    try:
                        bidget_enhancements.add_signal_to_dashboard(signal)
                    except Exception as e:
                        logger.error(f"Error updating confidence dashboard: {str(e)}")
                
                # Log signal acceptance
                logger.info(f"BIDGET ACCEPTED: {symbol} {timeframe} - {filter_reason}")
            else:
                # Log filter rejection
                logger.info(f"BIDGET REJECTED: {symbol} {timeframe} - {filter_reason}")
            
            logger.info(f"Alert sent for {symbol} on {timeframe} (Daily trade {daily_trade_count}/{MAX_DAILY_TRADES})")



def load_trade_counts():
    """Load the daily trade counts from file."""
    global daily_trade_count, today_date
    
    try:
        if os.path.exists(TRADE_COUNT_FILE):
            with open(TRADE_COUNT_FILE, 'r') as file:
                data = json.load(file)
                if today_date in data:
                    daily_trade_count = data[today_date]
                    logger.info(f"Loaded daily trade count: {daily_trade_count} for {today_date}")
                else:
                    # New day, reset counter
                    daily_trade_count = 0
                    logger.info(f"New day detected. Resetting trade count to 0")
        else:
            # File doesn't exist yet
            daily_trade_count = 0
            logger.info("No trade count file found. Starting with 0 trades.")
    except Exception as e:
        logger.error(f"Error loading trade counts: {str(e)}")
        daily_trade_count = 0
    
    # Always save to ensure the file exists with today's date
    save_trade_counts()

def save_trade_counts():
    """Save the daily trade counts to file."""
    try:
        # Load existing data if file exists
        data = {}
        if os.path.exists(TRADE_COUNT_FILE):
            with open(TRADE_COUNT_FILE, 'r') as file:
                data = json.load(file)
        
        # Update with today's count
        data[today_date] = daily_trade_count
        
        # Save back to file
        with open(TRADE_COUNT_FILE, 'w') as file:
            json.dump(data, file)
            
        logger.debug(f"Saved trade count: {daily_trade_count} for {today_date}")
    except Exception as e:
        logger.error(f"Error saving trade counts: {str(e)}")

def increment_trade_count():
    """Increment the daily trade count and save."""
    global daily_trade_count
    daily_trade_count += 1
    logger.info(f"Incremented daily trade count to {daily_trade_count}")
    save_trade_counts()

def check_daily_trade_limit(max_limit):
    """Check if we've reached the daily trade limit."""
    # Refresh from file in case multiple processes are running
    load_trade_counts()
    
    # Check if under limit
    return daily_trade_count < max_limit

def scan_markets():
    """Scan all markets for trading opportunities with Bidget enhancement support."""
    # Update daily trade tracking - handle day changes
    global today_date, bidget_enhancements
    current_date = date.today().isoformat()
    
    # Reset counter if it's a new day
    if current_date != today_date:
        today_date = current_date
        load_trade_counts()  # This will reset the counter for the new day
        
        # Also reset daily stats in enhancements
        if bidget_enhancements:
            bidget_enhancements.reset_daily_stats()
            logger.info("Reset Bidget enhancement daily statistics")
        
    # Get maximum daily trades from config
    try:
        from config import SETTINGS, MAX_DAILY_TRADES, MAX_TELEGRAM_SIGNALS
        max_trades = MAX_DAILY_TRADES
        max_signals = MAX_TELEGRAM_SIGNALS
        
        # Log Bidget limits
        logger.info(f"Bidget daily limits: {max_trades} trades, {max_signals} signals")
    except ImportError:
        # Default fallback for Bidget config
        max_trades = 15
        max_signals = 30
    
    # Check if we've hit the daily limit
    daily_limit_reached = not check_daily_trade_limit(max_trades)
    if daily_limit_reached:
        warning_msg = f"⚠️ Daily trade limit of {max_trades} reached. No more alerts will be sent today."
        logger.warning(warning_msg)
        telegram_client.send_message(warning_msg)
        # Return empty results instead of None
        return {
            "signals_processed": 0,
            "signals_found": 0,
            "preferred_signals": 0,
            "fallback_signals": 0,
            "daily_limit_reached": True,
            "scan_time_seconds": 0
        }
        
    logger.info("Starting enhanced market scan...")
    start_time = time.time()
    
    # Track all signals found in this scan for potential fallback
    all_signals = []
    signal_count = 0
    preferred_symbol_count = 0
    fallback_symbols_found = False
    
    # Get list of exchanges to scan (prioritize Bybit for Bidget)
    exchanges_to_scan = EXCHANGES.get('enabled', ['bybit'])
    logger.info(f"Scanning exchanges: {exchanges_to_scan}")
    
    # Count total symbols to scan for progress tracking
    total_symbols = 0
    for exchange_id in exchanges_to_scan:
        symbols = SYMBOLS_TO_SCAN.get(exchange_id, [])
        if symbols:
            total_symbols += len(symbols) * len(TIMEFRAMES)
        else:
            # Rough estimate if using all exchange pairs
            total_symbols += 50 * len(TIMEFRAMES)
    
    logger.info(f"Total pairs to scan: ~{total_symbols}")
    completed = 0  # Track completed items for progress
    
    for exchange_id in exchanges_to_scan:
        logger.info(f"Processing exchange: {exchange_id}")
        exchange = get_exchange_instance(exchange_id)
        if not exchange:
            logger.error(f"Failed to get exchange instance for {exchange_id}")
            continue
        
        # Load exchange markets
        try:
            logger.info(f"Loading markets for {exchange_id}")
            exchange.load_markets()
        except Exception as e:
            logger.error(f"Error loading markets for {exchange_id}: {str(e)}")
            continue
        
        # Update fallback whitelist if we have the enhancement module
        if bidget_enhancements and exchange_id == 'bybit':
            try:
                bidget_enhancements.update_fallback_whitelist(exchange)
                whitelist = bidget_enhancements.get_fallback_whitelist()
                if whitelist:
                    logger.info(f"Auto-Fallback whitelist updated: {len(whitelist)} pairs available")
                    fallback_symbols_found = True
            except Exception as e:
                logger.error(f"Error updating fallback whitelist: {str(e)}")
        
        # Get balance for position sizing
        if bidget_enhancements and exchange_id == 'bybit':
            try:
                balance = trader.get_balance()
                logger.info(f"{exchange_id} balance: {balance} USDT")
                
                # Update balance in enhancement module for scaling calculations
                if balance > 0:
                    bidget_enhancements.update_balance(balance)
                    logger.info(f"Updated balance for position scaling: {balance} USDT")
            except Exception as e:
                logger.error(f"Error fetching {exchange_id} balance: {str(e)}")
        
        # Get symbols to scan - either from config or all USDT pairs
        symbols = SYMBOLS_TO_SCAN.get(exchange_id, [])
        if not symbols:
            try:
                logger.info(f"No specific symbols for {exchange_id}, using all USDT pairs")
                markets = exchange.load_markets()
                symbols = [s for s in markets.keys() if '/USDT' in s or s.endswith(':USDT')]
                
                # Cap at 50 symbols if none specified to avoid excessive API calls
                if len(symbols) > 50:
                    logger.info(f"Limiting to top 50 USDT pairs for {exchange_id}")
                    symbols = symbols[:50]
            except Exception as e:
                logger.error(f"Error getting USDT symbols from {exchange_id}: {str(e)}")
                continue
        
        logger.info(f"Scanning {len(symbols)} pairs on {exchange_id}")
        
        # Analyze each symbol
        try:
            for symbol in symbols:
                # Check if this is a preferred symbol for tracking
                is_preferred = False
                if bidget_enhancements:
                    is_preferred = bidget_enhancements.is_preferred_symbol(symbol)
                    if is_preferred:
                        preferred_symbol_count += 1
                
                # Process each timeframe
                for timeframe in TIMEFRAMES:
                    try:
                        # This will trigger signal processing in analyze_symbol
                        analyze_symbol(exchange, symbol, timeframe)
                        signal_count += 1
                    except Exception as e:
                        logger.error(f"Error analyzing {symbol} on {timeframe}: {str(e)}")
                    
                    # Update progress tracking
                    completed += 1
                    if completed % 10 == 0:
                        progress = (completed / total_symbols) * 100
                        logger.info(f"Scan progress: {completed}/{total_symbols} ({progress:.1f}%)")
                        
                        # Hot reload check for configuration updates
                        if bidget_enhancements and bidget_enhancements.should_reload_config():
                            bidget_enhancements.reload_config()
                            logger.info("Hot reloaded Bidget enhancement parameters")
                
                # Sleep briefly to avoid hitting rate limits
                time.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error during symbol scanning on {exchange_id}: {str(e)}")
    
    # Check for fallback signals if we have the enhancement module
    if bidget_enhancements:
        try:
            # Process any pending signals from quality control
            pending_signals = bidget_enhancements.process_pending_signals()
            if pending_signals:
                logger.info(f"Processed {len(pending_signals)} pending signals after quality control delay")
            
            # Check if we should use fallback
            fallback_signal = bidget_enhancements.get_best_fallback_signal()
            if fallback_signal:
                logger.info(f"Using auto-fallback signal: {fallback_signal['symbol']} with {fallback_signal['probability']:.2f}% probability")
                
                # Create fallback alert message with detailed reasoning
                alert_message = f"🔄 AUTO-FALLBACK SIGNAL for {fallback_signal['symbol']}\n\n"
                
                # Add fallback reason with clear explanation
                fallback_reason = fallback_signal.get('fallback_reason', 'No signals found for preferred pairs')
                alert_message += f"{fallback_reason}. Using next-best alternative.\n\n"
                
                # Add standard trade parameters
                alert_message += f"Entry: {fallback_signal['entry_price']:.8f}\n"
                alert_message += f"Stop Loss: {fallback_signal['stop_loss']:.8f}\n"
                alert_message += f"Take Profit: {fallback_signal['take_profit']:.8f}\n"
                alert_message += f"Probability: {fallback_signal['probability']:.2f}%\n"
                alert_message += f"Timeframe: {fallback_signal['timeframe']}\n"
                
                # Add confidence details and selection criteria
                if 'confidence_details' in fallback_signal:
                    alert_message += f"\n📈 Selection Criteria:\n"
                    for detail, value in fallback_signal['confidence_details'].items():
                        alert_message += f"• {detail}: {value}\n"
                        
                # Add any recent performance metrics if available
                if 'recent_performance' in fallback_signal:
                    perf = fallback_signal['recent_performance']
                    alert_message += f"\n📊 Recent Performance:\n"
                    alert_message += f"• Win Rate: {perf.get('win_rate', 'N/A')}%\n"
                    alert_message += f"• Avg Profit: {perf.get('avg_profit', 'N/A')}%\n"
                
                # Send fallback alert
                telegram_client.send_message(alert_message)
                if 'chart_path' in fallback_signal and fallback_signal['chart_path']:
                    telegram_client.send_chart(fallback_signal['chart_path'], caption=f"Auto-Fallback: {fallback_signal['symbol']}")
                
                # Update dashboard with fallback signal
                bidget_enhancements.add_signal_to_dashboard(fallback_signal, is_fallback=True)
                
                # Increment trade count for the fallback signal
                increment_trade_count()
        except Exception as e:
            logger.error(f"Error processing fallback signals: {str(e)}")
    
    # Calculate and log scan statistics
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Market scan completed in {duration:.2f} seconds")
    logger.info(f"Scanned {signal_count} possible signals, {preferred_symbol_count} preferred symbols")
    
    # Update dashboard with scan statistics if available
    if bidget_enhancements:
        try:
            bidget_enhancements.update_scan_stats({
                'duration': duration,
                'signals_checked': signal_count,
                'preferred_symbols': preferred_symbol_count,
                'fallback_available': fallback_symbols_found
            })
        except Exception as e:
            logger.error(f"Error updating dashboard scan stats: {str(e)}")
    
    # Return scan statistics for potential use elsewhere
    return {
        'duration': duration,
        'signals_checked': signal_count,
        'preferred_symbols': preferred_symbol_count,
        'exchanges': len(exchanges_to_scan),
        'fallback_available': fallback_symbols_found
    }

def start_dashboard():
    """Start the web dashboard in a separate thread with Bidget enhancements."""
    global dashboard_thread, bidget_enhancements
    
    try:
        # Set up standard dashboard
        dashboard = Dashboard(port=8050)
        
        # If we have bidget enhancements, integrate the signal confidence dashboard
        if bidget_enhancements:
            # Pass the enhancement module to the dashboard
            logger.info("Initializing enhanced dashboard with Bidget features")
            dashboard.set_enhancements(bidget_enhancements)
            
            # Enable live signal confidence metrics
            dashboard.enable_signal_confidence_dashboard()
            
            # Enable real-time trading statistics for balance-based scaling
            dashboard.enable_balance_scaling_visualization()
            
            # Add signal quality visualization
            dashboard.enable_quality_control_visualization()
            
            logger.info("Enhanced dashboard initialized with all Bidget features")
        
        # Create and start dashboard thread
        dashboard_thread = threading.Thread(target=dashboard.run_server)
        dashboard_thread.daemon = True
        dashboard_thread.start()
        
        logger.info("Dashboard started successfully")
        
    except Exception as e:
        logger.error(f"Error starting dashboard: {str(e)}")

def start_trade_planner_api(port=8060, host='0.0.0.0', debug=False):
    """Start the Trade Planner API server in a separate thread."""
    global trade_planner_api_thread
    
    try:
        # Import the run_server function from trade_planner_api
        from trade_planner_api import run_server
        
        # Create and start API server thread
        trade_planner_api_thread = threading.Thread(
            target=run_server,
            args=(host, port, debug)
        )
        trade_planner_api_thread.daemon = True
        trade_planner_api_thread.start()
        
        logger.info(f"Trade Planner API started at http://{host}:{port}")
        logger.info(f"Access trade planning endpoint at http://{host}:{port}/api/plan")
        
    except Exception as e:
        logger.error(f"Error starting Trade Planner API: {str(e)}")
        return None

def send_test_message():
    """Send a test message via Telegram to verify the bot is working."""
    global telegram_client, telegram_commands
    
    try:
        # Send a test message with standard client
        if telegram_client:
            test_message = (
                "🧪 *TEST MESSAGE* 🧪\n\n"
                "Your Crypto Alert Bot is correctly configured and operational!\n\n"
                "✅ Telegram connection: ACTIVE\n"
                "✅ Data retrieval: ACTIVE\n"
                "✅ Signal analysis: READY\n"
                "✅ All modules loaded successfully\n\n"
                "The bot is now monitoring markets and will send alerts when profitable opportunities are detected.\n"
                "Use the command /help to see available options.\n"
            )
            telegram_client.send_message(test_message)
            logger.info("Test message sent successfully via primary client")
        
        # Also send a test message with command handler
        if telegram_commands:
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            if chat_id:
                telegram_commands.send_test_message(chat_id)
                logger.info("Test message sent successfully via command handler")
    
    except Exception as e:
        logger.error(f"Failed to send test message: {str(e)}")
        return False
    
    return True

def reset_all_daily_stats():
    """Reset all daily statistics, counters and limits across the system
    Called by daily_reset_monitor at UTC midnight
    """
    global bidget_enhancements
    
    try:
        logger.info("🔄 Resetting all daily statistics and counters...")
        
        # Reset Bidget enhancement stats if initialized
        if bidget_enhancements:
            bidget_enhancements.reset_daily_stats()
            logger.info("✅ Reset Bidget enhancement daily statistics")
        
        # Reset trade count
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'daily_trades.json')
        today = datetime.now().strftime('%Y-%m-%d')
        
        try:
            # Create an empty trades record for today
            data = {today: 0}
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            # Write new empty count
            with open(config_file, 'w') as f:
                json.dump(data, f)
                
            logger.info(f"✅ Reset daily trade count for {today}")
        except Exception as e:
            logger.error(f"Failed to reset daily trade count: {e}")
        
        # Reset signal count
        if hasattr(config, 'MAX_DAILY_SIGNALS'):
            signal_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'daily_signals.json')
            
            try:
                # Create an empty signals record for today
                data = {today: 0}
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(signal_file), exist_ok=True)
                
                # Write new empty count
                with open(signal_file, 'w') as f:
                    json.dump(data, f)
                    
                logger.info(f"✅ Reset daily signal count for {today}")
            except Exception as e:
                logger.error(f"Failed to reset daily signal count: {e}")
        
        # Additional resets as needed for other components
        
        logger.info("🎉 All daily stats and counters reset successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Error during daily stats reset: {e}")
        return False

def main():
    """Main function to run the crypto alert bot."""
    global telegram_client, telegram_commands, trader, portfolio_manager, dashboard_thread, backtester, ml_predictor, smart_filter, bidget_enhancements
    
    # Load daily trade counts
    load_trade_counts()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Cryptocurrency Alert Bot')
    parser.add_argument('--test', action='store_true', help='Send test message and exit')
    parser.add_argument('--scan', action='store_true', help='Run full market scan with Bidget enhancements')
    parser.add_argument('--backtest', action='store_true', help='Run backtesting')
    parser.add_argument('--dashboard', action='store_true', help='Start web dashboard')
    parser.add_argument('--trade', action='store_true', help='Enable auto trading (use with caution)')
    parser.add_argument('--train-ml', action='store_true', help='Train ML models')
    parser.add_argument('--live', action='store_true', help='Run in live trading mode with real orders')
    args = parser.parse_args()
    
    # Initialize Telegram client
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_bot_token or not chat_id:
        logger.error("Telegram credentials not found in environment variables")
        return
    
    telegram_client = TelegramClient(telegram_bot_token, chat_id)
    
    # Initialize Telegram command handler for custom alerts
    telegram_commands = TelegramCommandHandler(bybit_trader=bybit_trader)
    
    # Initialize Trade Memory System
    logger.info("🧠 Initializing Smart Trade Memory System...")
    trade_memory = initialize_trade_memory()
    
    # Initialize Auto-Recovery Engine
    logger.info("🔄 Initializing Auto-Recovery Engine...")
    recovery_config = {
        'recovery_enabled': True,
        'auto_save_interval': 300,  # 5 minutes
        'notify_admin_on_recovery': True
    }
    recovery_engine = initialize_recovery_engine(config=recovery_config)
    
    # Attempt recovery on startup
    logger.info("🔍 Checking for previous state to recover...")
    recovery_success, recovery_info = recovery_engine.recover_state()
    if recovery_success:
        logger.info(f"✅ Successfully recovered previous state: {recovery_info['open_trades_count']} open trades")
        # Send recovery notification via Telegram
        recovery_message = f"🔄 *Bot Recovery Complete* 🔄\n\n"
        recovery_message += f"📊 Recovered {recovery_info['open_trades_count']} open trades\n"
        recovery_message += f"📈 Market Regime: {recovery_info.get('regime', 'Unknown')}\n"
        recovery_message += f"🎯 Strategy: {recovery_info.get('strategy', 'Unknown')}\n"
        recovery_message += f"⏰ State Age: {recovery_info['summary']['state_age_hours']:.1f} hours\n"
        telegram_client.send_message(recovery_message)
    else:
        logger.info("ℹ️ No previous state found or recovery disabled")
    
    # Start auto-save for future state persistence
    recovery_engine.start_auto_save()
    
    # Initialize portfolio manager
    portfolio_manager = PortfolioManager(initial_capital=10000.0)
    
    # Initialize trader in dry-run mode by default
    trader = Trader(dry_run=not args.trade)
    
    # Initialize backtester
    backtester = Backtester()
    
    # Initialize ML predictor
    try:
        ml_predictor = MLPredictor(model_dir="models")
        logger.info("ML predictor initialized")
    except Exception as e:
        logger.error(f"Failed to initialize ML predictor: {str(e)}")
        ml_predictor = None
        
    # Initialize smart filter for Bidget
    try:
        smart_filter = SmartFilter({
            'max_coin_price': MAX_COIN_PRICE,
            'min_success_probability': MIN_SUCCESS_PROBABILITY,
            'max_telegram_signals': MAX_TELEGRAM_SIGNALS
        })
        logger.info("Bidget Smart Filter initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Smart Filter: {str(e)}")
        smart_filter = SmartFilter()  # Use defaults if config fails
        
    # Initialize Bidget enhancements with debug toggle
    try:
        # Check if SYMBOLS_TO_SCAN is a dictionary or list
        if isinstance(SYMBOLS_TO_SCAN, dict):
            preferred_symbols = SYMBOLS_TO_SCAN.get('bybit', [])
        else:
            # If it's not a dict, use directly or create a list of preferred pairs
            preferred_symbols = ['XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'TRXUSDT', 'XLMUSDT']
            logger.info(f"Using default preferred symbols: {preferred_symbols}")
        
        bidget_enhancements = BidgetEnhancements(
            config={
                'preferred_symbols': preferred_symbols,
                'max_price': MAX_COIN_PRICE,
                'balance_percentage': BALANCE_PERCENTAGE,
                'leverage': LEVERAGE,
                'min_probability': MIN_SUCCESS_PROBABILITY,
                'debug_mode': os.getenv('BIDGET_DEBUG', 'false').lower() == 'true',
                'hot_reload': True  # Enable hot reloading of enhancement parameters
            },
            data_dir='data'
        )
        logger.info("Bidget enhancements initialized with advanced features")
        
        # Log key enhancement parameters for visibility
        enhancement_params = bidget_enhancements.get_config()
        logger.info(f"Bidget enhancement parameters: {enhancement_params}")
    except Exception as e:
        logger.error(f"Failed to initialize Bidget enhancements: {str(e)}")
        bidget_enhancements = None
    
    # If test message flag is set, send test and exit
    if args.test:
        logger.info("Sending test message and exiting")
        if send_test_message():
            logger.info("Test message sent successfully. Exiting.")
            return
        else:
            logger.error("Failed to send test message")
            return
            
    # If scan flag is set, run a full market scan with Bidget enhancements
    if args.scan:
        logger.info("🔍 Starting full market scan with Bidget enhancements...")
        # Initialize dashboard for visualization
        if not args.live:
            try:
                start_dashboard()
                logger.info("Dashboard started for scan visualization")
            except Exception as e:
                logger.warning(f"Could not start dashboard: {e}")
        
        # Run the full market scan
        try:
            scan_results = scan_markets()
            
            # Check if daily limit was reached
            if scan_results.get('daily_limit_reached', False):
                logger.info("⚠️ Market scan skipped due to daily trade limit")
            else:
                signals_processed = scan_results.get('signals_processed', 0)
                signals_found = scan_results.get('signals_found', 0)
                scan_time = scan_results.get('scan_time_seconds', 0)
                logger.info(f"✅ Market scan complete! Processed {signals_processed} signals in {scan_time:.2f} seconds")
                logger.info(f"Found {signals_found} valid trading signals")
            
            # Log Bidget enhancement stats if available
            if bidget_enhancements:
                high_conf = bidget_enhancements.get_high_confidence_count()
                elite_conf = bidget_enhancements.get_elite_confidence_count()
                pending = bidget_enhancements.get_pending_signals_count()
                logger.info(f"Bidget Enhancement Stats: {high_conf} high confidence, {elite_conf} elite signals, {pending} pending signals")
                
            # Keep running to allow viewing dashboard
            if not args.live and dashboard_thread is not None and not dashboard_thread.is_alive():
                logger.info("Scan complete. Press Ctrl+C to exit.")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("User interrupted. Exiting.")
            
            return scan_results
        except Exception as e:
            logger.error(f"Error during market scan: {str(e)}")
            return None
    
    # If backtest flag is set, run backtesting
    if args.backtest:
        logger.info("Running backtesting")
        try:
            # Run backtesting for all strategies
            for symbol in SYMBOLS_TO_SCAN[:5]:  # Limit to first 5 symbols for testing
                results = backtester.run_backtest(
                    symbol=symbol,
                    timeframe='1h',
                    strategy_name='combined',
                    days=30
                )
                
                # Log results
                logger.info(f"Backtest results for {symbol}: {results['summary']}")
                
                # Save equity curve chart
                if 'equity_curve' in results:
                    chart_path = results['equity_curve']
                    telegram_client.send_chart(chart_path, caption=f"{symbol} {timeframe} Analysis")
        except Exception as e:
            logger.error(f"Error during backtesting: {str(e)}")
    
    # If ML training flag is set, train models
    if args.train_ml:
        logger.info("Training ML models")
        try:
            # Train models for all strategies
            for strategy in ['volume_spike', 'ma_cross', 'breakout', 'combined']:
                ml_predictor.train_model(
                    symbols=SYMBOLS_TO_SCAN[:5],  # Limit to first 5 symbols for testing
                    timeframe='1h',
                    strategy=strategy,
                    days=60
                )
                logger.info(f"Trained ML model for {strategy} strategy")
        except Exception as e:
            logger.error(f"Error during ML model training: {str(e)}")
    
    # Start dashboard in separate thread if enabled
    if args.dashboard:
        logger.info("Starting dashboard on port 8050")
        start_dashboard()
        
    # Start Trade Planner API server
    logger.info("Starting Trade Planner API server on port 8060")
    start_trade_planner_api(port=8060, host='0.0.0.0', debug=False)
    
    # Start Telegram command handler
    telegram_commands.start()
    
    # Send startup message with bot information
    startup_message = (
        "🤖 *Crypto Alert Bot is now running!*\n\n"
        "This bot scans cryptocurrency markets for safe trading opportunities\n"
        "and aims to help you secure $100 profit per day.\n\n"
        "*Features:*\n"
        "✅ Volume + Price Spike Alerts\n"
        "✅ Moving Averages (MA) Cross\n"
        "✅ Breakout Strategy Trigger\n"
        "✅ Multi-Timeframe Confirmation\n"
        "✅ Machine Learning Signal Quality\n"
        f"✅ {'LIVE Trading' if args.trade else 'Simulated Trading (Dry Run)'}\n"
        "✅ Portfolio Management\n"
        f"✅ {'Web Dashboard ACTIVE' if args.dashboard else 'Web Dashboard (disabled)'}\n\n"
        f"Scanning {len(SYMBOLS_TO_SCAN)} cryptocurrencies every {SCAN_INTERVAL} minutes.\n"
        f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "Use /help for available commands."
    )
    telegram_client.send_message(startup_message)
    
    # Schedule regular market scans
    schedule.every(SCAN_INTERVAL).minutes.do(scan_markets)
    
    # Schedule daily portfolio update
    schedule.every().day.at("00:01").do(portfolio_manager.update_daily_performance)
    
    # Run once immediately
    scan_markets()
    
    # Keep the script running
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        if telegram_commands:
            telegram_commands.stop()
        if args.dashboard and dashboard_thread:
            logger.info("Stopping dashboard thread")
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
        telegram_client.send_message(f"⚠️ Bot error: {str(e)}")
        if telegram_commands:
            telegram_commands.stop()

if __name__ == "__main__":
    main()
