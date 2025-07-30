#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Telegram Commands Handler for the Trading Bot
Implements debug commands and health check capabilities
"""

import os
import logging
import time
from threading import Thread
import json
import traceback
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Try to import playbook manager
try:
    from src.utils.playbook_manager import playbook_manager
    PLAYBOOK_MANAGER_AVAILABLE = True
except ImportError:
    PLAYBOOK_MANAGER_AVAILABLE = False
    logger.warning("Playbook manager not available - playbook commands will be limited")

class TelegramCommandHandler:
    """Handler for Telegram bot commands"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelegramCommandHandler, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the command handler"""
        self.commands = {
            '/help': self._cmd_help,
            '/status': self._cmd_status,
            '/health': self._cmd_health,
            '/trades': self._cmd_trades,
            '/reset': self._cmd_reset,
            '/set': self._cmd_set,
            '/get': self._cmd_get,
            '/balance': self._cmd_balance,
            '/playbook': self._cmd_playbook,
            '/forecast': self._cmd_forecast
        }
        
        # Map of available parameters that can be set
        self.settable_params = {
            'confidence': {
                'env_var': 'CONFIDENCE_THRESHOLD',
                'type': float,
                'min': 1.0,
                'max': 100.0,
                'default': 95.0,
                'description': 'Signal confidence threshold (%)'
            },
            'max_signals': {
                'env_var': 'MAX_SIGNALS_PER_DAY',
                'type': int,
                'min': 1,
                'max': 100,
                'default': 10,
                'description': 'Maximum signals per day'
            },
            'max_trades': {
                'env_var': 'MAX_TRADES_PER_DAY',
                'type': int,
                'min': 1,
                'max': 50,
                'default': 5,
                'description': 'Maximum trades per day'
            },
            'position_size': {
                'env_var': 'POSITION_SIZE_PERCENT',
                'type': float,
                'min': 1.0,
                'max': 100.0,
                'default': 25.0,
                'description': 'Position size as percentage of available balance'
            }
        }
        
        self.bot_instance = None
        logger.info("Telegram command handler initialized")
    
    def set_bot_instance(self, bot_instance):
        """Set the bot instance reference for command execution"""
        self.bot_instance = bot_instance
        logger.info("Bot instance reference set for command handler")
    
    def process_command(self, message: str) -> Optional[str]:
        """
        Process a potential command message from Telegram
        
        Args:
            message: The message text from Telegram
            
        Returns:
            Optional response message to send back, or None if not a command
        """
        # Check if it's a command (starts with /)
        if not message.startswith('/'):
            return None
        
        # Extract command and arguments
        parts = message.split()
        command = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []
        
        logger.info(f"Processing command: {command} with args: {args}")
        
        # Execute command if it exists
        if command in self.commands:
            try:
                return self.commands[command](args)
            except Exception as e:
                error_msg = f"Error executing command {command}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                return f"⚠️ *Command Error*\n\n{error_msg}\n\n```\n{traceback.format_exc()[:500]}...\n```"
        else:
            return f"❓ Unknown command: {command}\n\nType /help for available commands."
    
    def _cmd_help(self, args: List[str] = None) -> str:
        """Show help message with available commands"""
        help_text = "🤖 *Regime Intelligence Bot Commands:*\n\n"
        help_text += "/status - Show bot status\n"
        help_text += "/health - Run health check\n"
        help_text += "/trades - Show recent trades\n"
        help_text += "/reset - Reset daily counters\n"
        help_text += "/set <param> <value> - Set parameter\n"
        help_text += "/get <param> - Get parameter value\n"
        help_text += "/balance - Show account balance\n"
        help_text += "/playbook <active|list|update> - Manage playbooks\n"
        help_text += "/forecast [symbol] [timeframe] - Generate regime forecast\n"
        
        help_text += "\n*Examples:*\n"
        help_text += "/health api - Run API connectivity health check\n"
        help_text += "/reset BTCUSDT - Reset position tracking for BTC\n"
        help_text += "/set confidence 90 - Set confidence threshold to 90%\n"
        help_text += "/playbook active - Show active playbook configuration\n"
        help_text += "/forecast BTCUSDT 4h - Get forecast for BTC on 4h timeframe\n"
        
        return help_text
    
    def _cmd_status(self, args: List[str]) -> str:
        """Show bot status summary"""
        if not self.bot_instance:
            return "⚠️ Cannot access bot instance"
        
        try:
            # Bot version and runtime info
            uptime = time.time() - getattr(self.bot_instance, 'start_time', time.time())
            hours, remainder = divmod(uptime, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            # Get basic status information
            status = {
                'mode': 'TEST' if getattr(self.bot_instance, 'test_mode', True) else 'LIVE',
                'uptime': f"{int(hours)}h {int(minutes)}m {int(seconds)}s",
                'signals_today': len(getattr(self.bot_instance, 'daily_signals', [])),
                'trades_today': getattr(self.bot_instance, 'daily_trades_count', 0),
                'active_trades': len(getattr(self.bot_instance, 'active_trades', [])),
                'confidence_threshold': getattr(self.bot_instance, 'confidence_threshold', 'N/A'),
                'max_signals': getattr(self.bot_instance, 'max_signals_per_day', 'N/A'),
                'max_trades': getattr(self.bot_instance, 'max_trades_per_day', 'N/A')
            }
            
            # Format the response
            response = f"🤖 *Trading Bot Status*\n\n"
            response += f"*Mode:* {status['mode']}\n"
            response += f"*Uptime:* {status['uptime']}\n"
            response += f"*Signals Today:* {status['signals_today']}\n"
            response += f"*Trades Today:* {status['trades_today']}\n"
            response += f"*Active Trades:* {status['active_trades']}\n"
            response += f"*Confidence Threshold:* {status['confidence_threshold']}%\n"
            
            # Add active trades list if any
            if status['active_trades'] > 0:
                response += "\n*Active Positions:*\n"
                for symbol in getattr(self.bot_instance, 'active_trades', []):
                    response += f"• {symbol}\n"
            
            return response
            
        except Exception as e:
            error_msg = f"Error getting status: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"⚠️ *Status Error*\n\n{error_msg}"
    
    def _cmd_health(self, args: List[str]) -> str:
        """Run health check(s)"""
        try:
            from src.utils.health_check import health_check
            
            # Determine which checks to run
            check_types = None
            if args:
                if args[0].lower() == 'all':
                    check_types = None  # Will run all checks
                else:
                    # Map argument to check type
                    check_map = {
                        'api': 'api_connection',
                        'trading': 'trading_permissions',
                        'signals': 'signal_generation',
                        'trades': 'active_trades',
                        'balance': 'balance',
                        'system': 'system'
                    }
                    
                    check_types = []
                    for arg in args:
                        if arg.lower() in check_map:
                            check_types.append(check_map[arg.lower()])
            
            # Run health check and get results
            results = health_check.run_health_check(check_types=check_types, notify=False)
            
            # Format response
            status_emoji = {
                'ok': '✅',
                'warning': '⚠️',
                'error': '❌'
            }
            
            overall_status = results['overall_status']
            emoji = status_emoji.get(overall_status, '❓')
            
            response = [
                f"{emoji} *Health Check Results*",
                f"Status: {overall_status.upper()}",
                f"Execution Time: {results['duration_ms']}ms",
                ""
            ]
            
            # Add individual check results
            for check_name, check_result in results['checks'].items():
                check_emoji = status_emoji.get(check_result['status'], '❓')
                response.append(f"{check_emoji} {check_name}: {check_result['message']}")
            
            # Include limited details for important checks
            if 'details' in results:
                for check_name, details in results['details'].items():
                    if check_name == 'active_trades' and details:
                        response.append("\n*Active Positions:*")
                        positions = details.get('actual_positions', [])
                        if positions:
                            for pos in positions:
                                response.append(f"• {pos.get('symbol', 'Unknown')}: {pos.get('size', 0)} ({pos.get('side', 'unknown')})")
                        else:
                            response.append("No active positions")
                    
                    if check_name == 'balance' and details:
                        response.append(f"\n*Balance:* {details.get('available', 0)} USDT available, {details.get('frozen', 0)} USDT frozen")
                        
            return "\n".join(response)
            
        except ImportError:
            return "⚠️ Health check module not available"
        except Exception as e:
            error_msg = f"Error running health check: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"⚠️ *Health Check Error*\n\n{error_msg}"
    
    def _cmd_trades(self, args: List[str]) -> str:
        """Show active trades and positions"""
        if not self.bot_instance:
            return "⚠️ Cannot access bot instance"
        
        try:
            # First get locally tracked trades
            active_trades = getattr(self.bot_instance, 'active_trades', [])
            
            response = f"🔄 *Active Trades*\n\n"
            
            # First show locally tracked trades
            response += "*Tracked Positions:*\n"
            if active_trades:
                for symbol in active_trades:
                    response += f"• {symbol}\n"
            else:
                response += "No tracked positions\n"
            
            # Try to get actual API positions
            try:
                from src.integrations.bidget import TradingAPI
                api = TradingAPI()
                
                if api.is_configured:
                    # Get positions from API
                    positions_endpoint = "/api/mix/v1/position/allPosition?productType=umcbl&marginCoin=USDT"
                    positions_response = api._make_request("GET", positions_endpoint, signed=True)
                    
                    if 'error' not in positions_response and 'data' in positions_response:
                        positions_data = positions_response.get('data', [])
                        
                        response += "\n*Actual Positions:*\n"
                        
                        active_positions = []
                        for position in positions_data:
                            if isinstance(position, dict):
                                total = float(position.get('total', 0))
                                if total > 0:
                                    symbol = position.get('symbol', '').replace('_UMCBL', '')
                                    side = position.get('holdSide', 'unknown')
                                    leverage = position.get('leverage', 'N/A')
                                    
                                    active_positions.append({
                                        'symbol': symbol,
                                        'size': total,
                                        'side': side,
                                        'leverage': leverage
                                    })
                        
                        if active_positions:
                            for pos in active_positions:
                                response += f"• {pos['symbol']}: {pos['size']} ({pos['side']}, {pos['leverage']}x)\n"
                        else:
                            response += "No active positions found\n"
                    else:
                        response += "\n⚠️ Failed to retrieve actual positions from API\n"
                else:
                    response += "\n⚠️ API not configured, showing only tracked trades\n"
            except Exception as e:
                response += f"\n⚠️ Error retrieving API positions: {str(e)[:100]}...\n"
                
            # Check for discrepancies
            tracked_set = {s.replace('/', '') for s in active_trades}
            
            try:
                api_set = {p['symbol'] for p in active_positions}
                missing = [s for s in api_set if s not in tracked_set]
                extra = [s for s in tracked_set if s not in api_set]
                
                if missing or extra:
                    response += "\n⚠️ *Tracking Discrepancies:*\n"
                    if missing:
                        response += f"Positions not tracked: {', '.join(missing)}\n"
                    if extra:
                        response += f"Tracked but no position: {', '.join(extra)}\n"
            except:
                pass
                
            return response
            
        except Exception as e:
            error_msg = f"Error getting trades: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"⚠️ *Trades Error*\n\n{error_msg}"
    
    def _cmd_reset(self, args: List[str]) -> str:
        """Reset tracking for a symbol, all symbols, or notification cache"""
        if not args:
            return "⚠️ Missing arguments. Use: /reset all, /reset notifications, or /reset SYMBOL"
        
        try:
            # Reset all active trades tracking
            if args[0].lower() == 'all':
                if self.bot_instance:
                    symbols = list(getattr(self.bot_instance, 'active_trades', []))
                    getattr(self.bot_instance, 'active_trades', set()).clear()
                    return f"✅ Reset tracking for all symbols: {', '.join(symbols) if symbols else 'none'}"
                else:
                    return "⚠️ Cannot access bot instance"
            
            # Reset notification cache
            elif args[0].lower() == 'notifications':
                try:
                    from src.utils.notification_cache import notification_cache
                    notification_cache.reset()
                    return "✅ Notification cache has been reset"
                except ImportError:
                    return "⚠️ Notification cache module not found"
            
            # Reset specific symbol
            else:
                symbol = args[0].upper()
                
                # Format symbol consistently
                if '/' not in symbol and len(symbol) > 3:
                    # Convert BTCUSDT to BTC/USDT format if needed
                    base = symbol[:-4] if symbol.endswith('USDT') else symbol
                    symbol = f"{base}/USDT"
                
                if self.bot_instance:
                    # Use the bot's force reset method
                    if hasattr(self.bot_instance, 'check_and_clean_active_trades'):
                        self.bot_instance.check_and_clean_active_trades(force_reset=True, symbol_to_reset=symbol)
                        return f"✅ Reset tracking for {symbol}"
                    # Fallback to direct manipulation
                    elif symbol in getattr(self.bot_instance, 'active_trades', set()):
                        getattr(self.bot_instance, 'active_trades', set()).remove(symbol)
                        return f"✅ Reset tracking for {symbol}"
                    else:
                        return f"⚠️ {symbol} is not in active trades list"
                else:
                    return "⚠️ Cannot access bot instance"
        except Exception as e:
            error_msg = f"Error during reset: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"⚠️ *Reset Error*\n\n{error_msg}"
    
    def _cmd_set(self, args: List[str]) -> str:
        """Set bot parameters"""
        if len(args) < 2:
            params_list = ", ".join(self.settable_params.keys())
            return f"⚠️ Missing arguments. Use: /set parameter value\n\nAvailable parameters: {params_list}"
        
        param_name = args[0].lower()
        value_str = args[1]
        
        if param_name not in self.settable_params:
            params_list = ", ".join(self.settable_params.keys())
            return f"⚠️ Invalid parameter '{param_name}'. Available parameters: {params_list}"
        
        param_info = self.settable_params[param_name]
        
        try:
            # Convert value to correct type
            value = param_info['type'](value_str)
            
            # Validate range
            if value < param_info['min'] or value > param_info['max']:
                return f"⚠️ Value out of range. {param_name} must be between {param_info['min']} and {param_info['max']}"
            
            # Apply setting to bot instance
            if self.bot_instance:
                # Try direct attribute setting
                param_attr = None
                if param_name == 'confidence':
                    param_attr = 'confidence_threshold'
                elif param_name == 'max_signals':
                    param_attr = 'max_signals_per_day'
                elif param_name == 'max_trades':
                    param_attr = 'max_trades_per_day'
                elif param_name == 'position_size':
                    param_attr = 'position_size_percent'
                
                if param_attr and hasattr(self.bot_instance, param_attr):
                    setattr(self.bot_instance, param_attr, value)
                    
                # For debugging
                logger.info(f"Set parameter {param_name} to {value} via attribute {param_attr}")
                
                # Also set the environment variable so it persists on restart
                env_var = param_info['env_var']
                os.environ[env_var] = str(value)
                
                # For debugging
                logger.info(f"Set environment variable {env_var} to {value}")
                
                return f"✅ Set {param_name} to {value}"
            else:
                # If we can't access bot instance, just set the environment variable
                env_var = param_info['env_var']
                os.environ[env_var] = str(value)
                return f"✅ Set {param_name} to {value} (environment only)"
                
        except ValueError:
            return f"⚠️ Invalid value format. {param_name} must be a {param_info['type'].__name__}"
        except Exception as e:
            error_msg = f"Error setting parameter: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"⚠️ *Parameter Error*\n\n{error_msg}"
    
    def _cmd_get(self, args: List[str]) -> str:
        """Get current parameter values"""
        response = "🔧 *Current Bot Parameters*\n\n"
        
        for param_name, param_info in self.settable_params.items():
            # Get current value - first try bot instance
            current_value = None
            
            if self.bot_instance:
                param_attr = None
                if param_name == 'confidence':
                    param_attr = 'confidence_threshold'
                elif param_name == 'max_signals':
                    param_attr = 'max_signals_per_day'
                elif param_name == 'max_trades':
                    param_attr = 'max_trades_per_day'
                elif param_name == 'position_size':
                    param_attr = 'position_size_percent'
                
                if param_attr and hasattr(self.bot_instance, param_attr):
                    current_value = getattr(self.bot_instance, param_attr)
            
            # Fall back to environment variable
            if current_value is None:
                env_var = param_info['env_var']
                env_value = os.getenv(env_var)
                if env_value:
                    try:
                        current_value = param_info['type'](env_value)
                    except ValueError:
                        current_value = f"Invalid format: {env_value}"
                else:
                    current_value = param_info['default']
            
            # Add to response
            response += f"*{param_name}*: {current_value} ({param_info['description']})\n"
        
        return response
    
    def _cmd_balance(self, args: List[str]) -> str:
        """Show account balance"""
        try:
            from src.integrations.bidget import TradingAPI
            api = TradingAPI()
            
            if not api.is_configured:
                return "⚠️ API not configured"
            
            # Get account balance
            balance_endpoint = "/api/mix/v1/account/accounts?productType=umcbl"
            balance_response = api._make_request("GET", balance_endpoint, signed=True)
            
            if 'error' in balance_response:
                return f"⚠️ Balance API Error: {balance_response.get('error')}"
            
            balance_data = balance_response.get('data', [])
            if not balance_data:
                return "⚠️ No balance data available"
            
            response = "💰 *Account Balance*\n\n"
            
            for currency_data in balance_data:
                if not isinstance(currency_data, dict):
                    continue
                
                currency = currency_data.get('marginCoin', 'Unknown')
                available = float(currency_data.get('available', 0))
                frozen = float(currency_data.get('locked', 0))
                equity = float(currency_data.get('equity', 0))
                
                response += f"*{currency}*\n"
                response += f"Available: {available:.2f}\n"
                response += f"Frozen: {frozen:.2f}\n"
                response += f"Equity: {equity:.2f}\n"
                response += "\n"
            
            return response
            
        except ImportError:
            return "⚠️ API module not available"
        except Exception as e:
            error_msg = f"Error retrieving balance: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"⚠️ *Balance Error*\n\n{error_msg}"

# Singleton instance
    def _cmd_playbook(self, args: List[str] = None) -> str:
        """Manage playbooks and view active playbook configuration"""
        if not PLAYBOOK_MANAGER_AVAILABLE:
            return "⚠️ Playbook system not available"
            
        if not args or len(args) == 0:
            return "📒 *Playbook Commands*:\n\n" + \
                   "/playbook active - Show active playbook\n" + \
                   "/playbook list - List all available playbooks\n" + \
                   "/playbook update <regime> <param> <value> - Update playbook parameter\n" + \
                   "/playbook reset - Reset all playbooks to defaults"
        
        # Handle subcommands
        subcommand = args[0].lower()
        
        if subcommand == "active":
            return self._playbook_show_active()
        elif subcommand == "list":
            return self._playbook_list_all()
        elif subcommand == "update" and len(args) >= 4:
            return self._playbook_update(args[1], args[2], args[3])
        elif subcommand == "reset":
            return self._playbook_reset()
        else:
            return "❌ Invalid playbook command. Use /playbook without arguments to see available options."
    
    def _playbook_show_active(self) -> str:
        """Show active playbook configuration"""
        active = playbook_manager.get_active_playbook()
        
        if not active["active_regime"] or not active["playbook"]:
            return "ℹ️ No active playbook currently"
            
        # Format activation timestamp
        activated_at = active.get("activated_at")
        time_str = "Unknown"
        if activated_at:
            try:
                dt = datetime.fromisoformat(activated_at)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass
        
        # Build response message
        playbook = active["playbook"]
        response = f"📊 *Active Playbook for Regime: {active['active_regime']}*\n"
        response += f"Activated: {time_str}\n\n"
        
        # Add playbook details
        response += f"Strategy: {playbook.get('strategy', 'N/A')}\n"
        response += f"Leverage: {playbook.get('leverage', 'N/A')}\n"
        response += f"Entry Type: {playbook.get('entry_type', 'N/A')}\n"
        response += f"Stop Loss: {playbook.get('stop_loss', 'N/A')}\n"
        
        # Handle take profit targets (may be a list)
        take_profit = playbook.get('take_profit', [])
        if isinstance(take_profit, list) and take_profit:
            response += f"Take Profit: {', '.join(take_profit)}\n"
        elif take_profit:
            response += f"Take Profit: {take_profit}\n"
        else:
            response += "Take Profit: N/A\n"
            
        response += f"Risk Level: {playbook.get('risk_level', 'N/A')}\n"
        
        return response
    
    def _playbook_list_all(self) -> str:
        """List all available playbooks"""
        playbooks = playbook_manager.playbooks
        
        if not playbooks:
            return "ℹ️ No playbooks available"
        
        response = "📒 *Available Playbooks:*\n\n"
        
        # Sort playbooks by name for consistent listing
        for regime in sorted(playbooks.keys()):
            playbook = playbooks[regime]
            strategy = playbook.get('strategy', 'N/A')
            risk_level = playbook.get('risk_level', 'N/A')
            
            response += f"*{regime}*: {strategy} (Risk: {risk_level})\n"
        
        response += "\nUse /playbook active to see the currently active playbook"
        return response
    
    def _playbook_update(self, regime: str, param: str, value: str) -> str:
        """Update playbook parameter for a specific regime"""
        # Validate regime exists
        if regime not in playbook_manager.playbooks:
            return f"❌ Regime '{regime}' not found in playbooks"
        
        # Handle different parameter types
        if param == "leverage":
            try:
                value = int(value)
            except ValueError:
                return f"❌ Leverage must be a number"
                
        elif param == "take_profit":
            # Handle take_profit as a comma-separated list
            value = [item.strip() for item in value.split(',')]
        
        # Update the playbook
        success = playbook_manager.update_playbook_config(regime, {param: value})
        
        if success:
            return f"✅ Updated {param} to {value} for regime '{regime}'"
        else:
            return f"❌ Failed to update playbook parameter"
    
    def _playbook_reset(self) -> str:
        """Reset all playbooks to defaults"""
        success = playbook_manager.reset_to_defaults()
        
        if success:
            return "✅ Reset all playbooks to default values"
        else:
            return "❌ Failed to reset playbooks"
    
    def _cmd_forecast(self, args: List[str]) -> str:
        """
        Generate regime forecast using pattern matching analysis.
        Usage: /forecast [symbol] [timeframe]
        """
        try:
            # Import pattern matcher
            from src.analytics.pattern_matcher import PatternMatcher
            
            # Parse arguments with validation
            symbol = args[0].upper() if len(args) > 0 else "BTCUSDT"
            timeframe = args[1] if len(args) > 1 else "1h"
            
            # Validate timeframe
            valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w']
            if timeframe not in valid_timeframes:
                return f"⚠️ **Invalid Timeframe**\n\nSupported timeframes: {', '.join(valid_timeframes)}\n\n💡 **Usage:** `/forecast [symbol] [timeframe]`"
            
            # Initialize pattern matcher
            pattern_matcher = PatternMatcher()
            
            # Get current regime from bot instance if available
            current_regime = None
            recent_sequence = None
            
            if self.bot_instance:
                # Try to get current regime from bot
                current_regime = getattr(self.bot_instance, 'current_regime', None)
                recent_regimes = getattr(self.bot_instance, 'recent_regimes', [])
                
                if recent_regimes and len(recent_regimes) > 1:
                    recent_sequence = recent_regimes[-3:-1]  # Last 2 regimes before current
            
            # If no current regime from bot, use a default for demo
            if not current_regime:
                # Get the most recent regime from database
                historical_regimes = pattern_matcher.get_historical_regimes(1)
                if historical_regimes:
                    current_regime = historical_regimes[0].regime_type
                else:
                    current_regime = "sideways_high_volatility"  # Default for demo
            
            # Generate forecast
            forecast = pattern_matcher.get_forecast(current_regime, recent_sequence)
            
            # Add header with symbol and timeframe info
            header = f"📊 **Regime Forecast for {symbol.upper()} ({timeframe})**\n\n"
            
            return header + forecast
            
        except ImportError as e:
            logger.error(f"Pattern matcher import error: {str(e)}")
            return "⚠️ **Forecast Unavailable**\n\nPattern matching system not available. Please ensure the analytics module is properly installed."
            
        except Exception as e:
            error_msg = f"Error generating forecast: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return f"⚠️ **Forecast Error**\n\n{error_msg}\n\n💡 **Usage:** `/forecast [symbol] [timeframe]`\n**Example:** `/forecast BTCUSDT 1h`"


# Singleton instance
telegram_commands = TelegramCommandHandler()
