"""
Telegram Commands Handler for Cryptocurrency Alert Bot
Handles user commands for customizing alerts and getting status updates
"""
import os
import logging
import pandas as pd
from datetime import datetime
import json
import threading

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackContext, 
    MessageHandler, Filters, CallbackQueryHandler
)

from dotenv import load_dotenv

# Local modules
from config import SETTINGS
from trade_memory import get_trade_memory
from auto_recovery import get_recovery_engine
from telegram_forecast_handler import TelegramForecastHandler

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class TelegramCommandHandler:
    """Handles custom commands from Telegram users"""
    
    def __init__(self, config_path='data/user_config.json', bybit_trader=None):
        """Initialize the Telegram command handler.
        
        Args:
            config_path (str): Path to user configuration file
            bybit_trader (BybitTrader): Trading interface for market data
        """
        self.config_path = config_path
        self.user_config = {}
        self.bybit_trader = bybit_trader
        
        # Initialize forecast handler
        self.forecast_handler = TelegramForecastHandler(bybit_trader)
        
        # Create data directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Load user configuration
        self._load_user_config()
        
        # Initialize Telegram updater
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            self.updater = None
        else:
            self.updater = Updater(token=self.bot_token)
            self.dispatcher = self.updater.dispatcher
            
            # Register command handlers
            self._register_handlers()
        
        logger.info("Telegram Command Handler initialized")
    
    def _load_user_config(self):
        """Load user configuration from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.user_config = json.load(f)
                logger.info(f"Loaded user configuration for {len(self.user_config)} users")
            else:
                self.user_config = {}
        except Exception as e:
            logger.error(f"Error loading user configuration: {str(e)}")
            self.user_config = {}
    
    def _save_user_config(self):
        """Save user configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.user_config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving user configuration: {str(e)}")
    
    def _register_handlers(self):
        """Register command handlers with the Telegram dispatcher."""
        if not self.dispatcher:
            return
        
        # Basic commands
        self.dispatcher.add_handler(CommandHandler("start", self._start_command))
        self.dispatcher.add_handler(CommandHandler("help", self._help_command))
        self.dispatcher.add_handler(CommandHandler("status", self._status_command))
        
        # Alert configuration commands
        self.dispatcher.add_handler(CommandHandler("alerts", self._alerts_command))
        self.dispatcher.add_handler(CommandHandler("enable", self._enable_command))
        self.dispatcher.add_handler(CommandHandler("disable", self._disable_command))
        self.dispatcher.add_handler(CommandHandler("set", self._set_command))
        
        # Watchlist commands
        self.dispatcher.add_handler(CommandHandler("watchlist", self._watchlist_command))
        self.dispatcher.add_handler(CommandHandler("add", self._add_command))
        self.dispatcher.add_handler(CommandHandler("remove", self._remove_command))
        
        # Performance commands
        self.dispatcher.add_handler(CommandHandler("performance", self._performance_command))
        
        # Trade Memory commands
        self.dispatcher.add_handler(CommandHandler("history", self._history_command))
        self.dispatcher.add_handler(CommandHandler("last_trade", self._last_trade_command))
        self.dispatcher.add_handler(CommandHandler("trades", self._trades_command))
        
        # Recovery commands
        self.dispatcher.add_handler(CommandHandler("recovery", self._recovery_command))
        
        # Visual Forecast commands
        self.dispatcher.add_handler(CommandHandler("forecast", self._forecast_command))
        self.dispatcher.add_handler(CommandHandler("plan", self._plan_command))
        
        # Callback query handler
        self.dispatcher.add_handler(CallbackQueryHandler(self._button_callback))
        
        # Error handler
        self.dispatcher.add_error_handler(self._error_handler)
    
    def start(self):
        """Start the Telegram updater."""
        if self.updater:
            self.updater.start_polling()
            logger.info("Started Telegram command handler")
    
    def stop(self):
        """Stop the Telegram updater."""
        if self.updater:
            self.updater.stop()
            logger.info("Stopped Telegram command handler")
    
    def send_message(self, chat_id, text, parse_mode=ParseMode.MARKDOWN, reply_markup=None):
        """Send a message to a Telegram chat.
        
        Args:
            chat_id (str): Telegram chat ID
            text (str): Message text
            parse_mode (str): Message parsing mode
            reply_markup: Optional reply markup
            
        Returns:
            bool: True if message was sent successfully
        """
        if not self.updater:
            logger.error("Cannot send message: Telegram updater not initialized")
            return False
        
        try:
            self.updater.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup
            )
            return True
        except Exception as e:
            logger.error(f"Error sending message to {chat_id}: {str(e)}")
            return False
    
    def send_test_message(self, chat_id):
        """Send a test message to a Telegram chat.
        
        Args:
            chat_id (str): Telegram chat ID
            
        Returns:
            bool: True if message was sent successfully
        """
        text = (
            "🔔 *Crypto Alert Bot - Test Message* 🔔\n\n"
            "Your bot is successfully configured and running!\n\n"
            "Use /help to see available commands."
        )
        
        return self.send_message(chat_id, text)
    
    def _get_user_config(self, user_id):
        """Get user configuration.
        
        Args:
            user_id (str): Telegram user ID
            
        Returns:
            dict: User configuration
        """
        user_id = str(user_id)
        
        if user_id not in self.user_config:
            # Default configuration
            self.user_config[user_id] = {
                'alerts': {
                    'volume_spike': True,
                    'ma_cross': True,
                    'breakout': True
                },
                'thresholds': {
                    'volume_threshold': 2.0,
                    'price_change_threshold': 1.5,
                    'risk_reward_ratio': 2.0
                },
                'watchlist': ['BTC/USDT', 'ETH/USDT'],
                'notification_preferences': {
                    'charts': True,
                    'risk_analysis': True,
                    'daily_summary': True
                }
            }
            self._save_user_config()
        
        return self.user_config[user_id]
    
    def _update_user_config(self, user_id, config):
        """Update user configuration.
        
        Args:
            user_id (str): Telegram user ID
            config (dict): User configuration
            
        Returns:
            bool: True if configuration was updated successfully
        """
        user_id = str(user_id)
        
        try:
            self.user_config[user_id] = config
            self._save_user_config()
            return True
        except Exception as e:
            logger.error(f"Error updating user configuration for {user_id}: {str(e)}")
            return False
    
    def _start_command(self, update: Update, context: CallbackContext):
        """Handle the /start command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Get or create user configuration
        config = self._get_user_config(user_id)
        
        welcome_text = (
            "👋 *Welcome to the Crypto Alert Bot!* 👋\n\n"
            "I'll send you alerts for cryptocurrency trading opportunities based on:\n"
            "- Volume + Price Spikes\n"
            "- Moving Average Crossovers\n"
            "- Breakout Patterns\n\n"
            "Use /help to see all available commands."
        )
        
        self.send_message(chat_id, welcome_text)
    
    def _help_command(self, update: Update, context: CallbackContext):
        """Handle the /help command."""
        chat_id = update.effective_chat.id
        
        help_text = (
            "📚 *Available Commands* 📚\n\n"
            "*Basic Commands:*\n"
            "/start - Initialize the bot\n"
            "/help - Show this help message\n"
            "/status - Show bot status\n\n"
            
            "*Alert Configuration:*\n"
            "/alerts - Show current alert settings\n"
            "/enable <strategy> - Enable alerts for a strategy\n"
            "/disable <strategy> - Disable alerts for a strategy\n"
            "/set <param> <value> - Set a parameter value\n\n"
            
            "*Watchlist Management:*\n"
            "/watchlist - Show your watchlist\n"
            "/add <symbol> - Add symbol to watchlist\n"
            "/remove <symbol> - Remove symbol from watchlist\n\n"
            
            "*Performance:*\n"
            "/performance - Show trading performance\n\n"
            
            "*Examples:*\n"
            "/enable volume_spike\n"
            "/disable ma_cross\n"
            "/set volume_threshold 2.5\n"
            "/add SOL/USDT\n"
            "/remove XRP/USDT"
        )
        
        self.send_message(chat_id, help_text)
    
    def _status_command(self, update: Update, context: CallbackContext):
        """Handle the /status command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Get user configuration
        config = self._get_user_config(user_id)
        
        # Format enabled strategies
        enabled_strategies = [s for s, enabled in config['alerts'].items() if enabled]
        
        status_text = (
            "🤖 *Bot Status* 🤖\n\n"
            f"*Enabled Strategies:* {', '.join(enabled_strategies)}\n"
            f"*Watchlist:* {', '.join(config['watchlist'])}\n\n"
            "*Current Thresholds:*\n"
        )
        
        for param, value in config['thresholds'].items():
            status_text += f"- {param}: {value}\n"
        
        status_text += "\nBot is active and scanning for signals!"
        
        self.send_message(chat_id, status_text)
    
    def _alerts_command(self, update: Update, context: CallbackContext):
        """Handle the /alerts command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Get user configuration
        config = self._get_user_config(user_id)
        
        # Create inline keyboard
        keyboard = []
        for strategy, enabled in config['alerts'].items():
            status = "✅" if enabled else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{strategy.capitalize()}: {status}", 
                    callback_data=f"toggle_alert:{strategy}"
                )
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        alert_text = (
            "🔔 *Alert Settings* 🔔\n\n"
            "Click to toggle alerts on/off:"
        )
        
        self.send_message(chat_id, alert_text, reply_markup=reply_markup)
    
    def _enable_command(self, update: Update, context: CallbackContext):
        """Handle the /enable command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Get strategy name from arguments
        if not context.args or len(context.args) < 1:
            self.send_message(
                chat_id, 
                "❌ Please specify a strategy to enable.\n"
                "Example: `/enable volume_spike`"
            )
            return
        
        strategy = context.args[0].lower()
        
        # Get user configuration
        config = self._get_user_config(user_id)
        
        # Check if strategy is valid
        if strategy not in config['alerts']:
            valid_strategies = ", ".join(config['alerts'].keys())
            self.send_message(
                chat_id,
                f"❌ Invalid strategy: {strategy}\n"
                f"Valid strategies: {valid_strategies}"
            )
            return
        
        # Enable strategy
        config['alerts'][strategy] = True
        self._update_user_config(user_id, config)
        
        self.send_message(
            chat_id,
            f"✅ Enabled alerts for {strategy}"
        )
    
    def _disable_command(self, update: Update, context: CallbackContext):
        """Handle the /disable command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Get strategy name from arguments
        if not context.args or len(context.args) < 1:
            self.send_message(
                chat_id, 
                "❌ Please specify a strategy to disable.\n"
                "Example: `/disable volume_spike`"
            )
            return
        
        strategy = context.args[0].lower()
        
        # Get user configuration
        config = self._get_user_config(user_id)
        
        # Check if strategy is valid
        if strategy not in config['alerts']:
            valid_strategies = ", ".join(config['alerts'].keys())
            self.send_message(
                chat_id,
                f"❌ Invalid strategy: {strategy}\n"
                f"Valid strategies: {valid_strategies}"
            )
            return
        
        # Disable strategy
        config['alerts'][strategy] = False
        self._update_user_config(user_id, config)
        
        self.send_message(
            chat_id,
            f"✅ Disabled alerts for {strategy}"
        )
    
    def _set_command(self, update: Update, context: CallbackContext):
        """Handle the /set command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Get parameter and value from arguments
        if not context.args or len(context.args) < 2:
            self.send_message(
                chat_id, 
                "❌ Please specify a parameter and value.\n"
                "Example: `/set volume_threshold 2.5`"
            )
            return
        
        param = context.args[0].lower()
        value_str = context.args[1]
        
        # Get user configuration
        config = self._get_user_config(user_id)
        
        # Check if parameter is valid
        if param not in config['thresholds']:
            valid_params = ", ".join(config['thresholds'].keys())
            self.send_message(
                chat_id,
                f"❌ Invalid parameter: {param}\n"
                f"Valid parameters: {valid_params}"
            )
            return
        
        # Try to convert value to appropriate type
        try:
            current_value = config['thresholds'][param]
            if isinstance(current_value, float):
                value = float(value_str)
            elif isinstance(current_value, int):
                value = int(value_str)
            else:
                value = value_str
        except ValueError:
            self.send_message(
                chat_id,
                f"❌ Invalid value: {value_str}"
            )
            return
        
        # Update parameter value
        config['thresholds'][param] = value
        self._update_user_config(user_id, config)
        
        self.send_message(
            chat_id,
            f"✅ Set {param} = {value}"
        )
    
    def _watchlist_command(self, update: Update, context: CallbackContext):
        """Handle the /watchlist command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Get user configuration
        config = self._get_user_config(user_id)
        
        # Create inline keyboard
        keyboard = []
        for symbol in config['watchlist']:
            keyboard.append([
                InlineKeyboardButton(
                    f"Remove {symbol}", 
                    callback_data=f"remove_symbol:{symbol}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                "Add Symbol", 
                callback_data="add_symbol"
            )
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        watchlist_text = (
            "📋 *Your Watchlist* 📋\n\n"
            f"{', '.join(config['watchlist'])}\n\n"
            "Click on a symbol to remove it from your watchlist."
        )
        
        self.send_message(chat_id, watchlist_text, reply_markup=reply_markup)
    
    def _add_command(self, update: Update, context: CallbackContext):
        """Handle the /add command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Get symbol from arguments
        if not context.args or len(context.args) < 1:
            self.send_message(
                chat_id, 
                "❌ Please specify a symbol to add.\n"
                "Example: `/add SOL/USDT`"
            )
            return
        
        symbol = context.args[0].upper()
        
        # Ensure symbol follows the correct format
        if '/' not in symbol:
            symbol = f"{symbol}/USDT"
        
        # Get user configuration
        config = self._get_user_config(user_id)
        
        # Check if symbol is already in watchlist
        if symbol in config['watchlist']:
            self.send_message(
                chat_id,
                f"ℹ️ {symbol} is already in your watchlist."
            )
            return
        
        # Add symbol to watchlist
        config['watchlist'].append(symbol)
        self._update_user_config(user_id, config)
        
        self.send_message(
            chat_id,
            f"✅ Added {symbol} to your watchlist"
        )
    
    def _remove_command(self, update: Update, context: CallbackContext):
        """Handle the /remove command."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        # Get symbol from arguments
        if not context.args or len(context.args) < 1:
            self.send_message(
                chat_id, 
                "❌ Please specify a symbol to remove.\n"
                "Example: `/remove SOL/USDT`"
            )
            return
        
        symbol = context.args[0].upper()
        
        # Ensure symbol follows the correct format
        if '/' not in symbol:
            symbol = f"{symbol}/USDT"
        
        # Get user configuration
        config = self._get_user_config(user_id)
        
        # Check if symbol is in watchlist
        if symbol not in config['watchlist']:
            self.send_message(
                chat_id,
                f"ℹ️ {symbol} is not in your watchlist."
            )
            return
        
        # Remove symbol from watchlist
        config['watchlist'].remove(symbol)
        self._update_user_config(user_id, config)
        
        self.send_message(
            chat_id,
            f"✅ Removed {symbol} from your watchlist"
        )
    
    def _performance_command(self, update: Update, context: CallbackContext):
        """Handle the /performance command."""
        chat_id = update.effective_chat.id
        
        # TODO: Implement performance reporting
        performance_text = (
            "📈 *Performance Report* 📈\n\n"
            "Performance data will be available once trading history is generated.\n\n"
            "Visit the web dashboard for detailed analytics."
        )
        
        # Create inline keyboard with link to dashboard
        keyboard = [[
            InlineKeyboardButton(
                "Open Dashboard", 
                url="http://localhost:8050"  # This will be replaced with actual dashboard URL
            )
        ]]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        self.send_message(chat_id, performance_text, reply_markup=reply_markup)
    
    async def _button_callback(self, update: Update, context: CallbackContext):
        """Handle callback queries from inline buttons."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        query = update.callback_query
        
        # Get callback data
        callback_data = query.data
        
        # Handle forecast system callbacks
        if callback_data.startswith("forecast_") or callback_data.startswith("plan_"):
            try:
                await self.forecast_handler.handle_forecast_callback(update, context)
                return
            except Exception as e:
                logger.error(f"Error in forecast callback: {e}")
                await query.answer("❌ Error processing request.")
                return
        
        # Get user configuration
        config = self._get_user_config(user_id)
        
        # Handle different callback types
        if callback_data.startswith("toggle_alert:"):
            # Toggle alert for a strategy
            strategy = callback_data.split(":")[1]
            
            if strategy in config['alerts']:
                # Toggle the alert
                config['alerts'][strategy] = not config['alerts'][strategy]
                self._update_user_config(user_id, config)
                
                status = "enabled" if config['alerts'][strategy] else "disabled"
                query.answer(f"{strategy.capitalize()} alerts {status}")
                
                # Update the message with new keyboard
                keyboard = []
                for s, enabled in config['alerts'].items():
                    status_icon = "✅" if enabled else "❌"
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{s.capitalize()}: {status_icon}", 
                            callback_data=f"toggle_alert:{s}"
                        )
                    ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    text="🔔 *Alert Settings* 🔔\n\nClick to toggle alerts on/off:",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
        
        elif callback_data.startswith("remove_symbol:"):
            # Remove symbol from watchlist
            symbol = callback_data.split(":")[1]
            
            if symbol in config['watchlist']:
                config['watchlist'].remove(symbol)
                self._update_user_config(user_id, config)
                
                query.answer(f"Removed {symbol} from your watchlist")
                
                # Update watchlist message
                keyboard = []
                for s in config['watchlist']:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"Remove {s}", 
                            callback_data=f"remove_symbol:{s}"
                        )
                    ])
                
                keyboard.append([
                    InlineKeyboardButton(
                        "Add Symbol", 
                        callback_data="add_symbol"
                    )
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                query.edit_message_text(
                    text=f"📋 *Your Watchlist* 📋\n\n{', '.join(config['watchlist'])}\n\nClick on a symbol to remove it from your watchlist.",
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.MARKDOWN
                )
        
        elif callback_data == "add_symbol":
            query.answer("Send /add <symbol> to add a new symbol")
    
    def _history_command(self, update: Update, context: CallbackContext):
        """Handle the /history command - show trade history."""
        try:
            user_id = str(update.effective_user.id)
            args = context.args
            
            # Parse arguments
            limit = 10  # default
            symbol = None
            days = None
            
            for arg in args:
                if arg.isdigit():
                    limit = min(int(arg), 50)  # max 50 trades
                elif arg.upper().endswith('USDT') or arg.upper().endswith('BTC'):
                    symbol = arg.upper()
                elif arg.endswith('d'):
                    try:
                        days = int(arg[:-1])
                    except ValueError:
                        pass
            
            # Get trade memory
            trade_memory = get_trade_memory()
            trades = trade_memory.get_history(limit=limit, symbol=symbol, days=days)
            
            if not trades:
                update.message.reply_text(
                    "📊 *Trade History* 📊\n\nNo trades found matching your criteria.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Format trade history
            message = f"📊 *Trade History* ({len(trades)} trades) 📊\n\n"
            
            for trade in trades:
                status_emoji = "🟢" if trade.status == "closed" and trade.result == "win" else "🔴" if trade.status == "closed" and trade.result == "loss" else "🟡"
                
                message += f"{status_emoji} *{trade.symbol}* {trade.side.upper()}\n"
                message += f"   Entry: ${trade.entry_price:.4f}"
                
                if trade.exit_price:
                    message += f" → ${trade.exit_price:.4f}"
                
                if trade.pnl_percentage:
                    pnl_sign = "+" if trade.pnl_percentage > 0 else ""
                    message += f" ({pnl_sign}{trade.pnl_percentage:.2f}%)"
                
                message += f"\n   Strategy: {trade.strategy or 'N/A'}"
                message += f"\n   Time: {trade.timestamp_entry.strftime('%m/%d %H:%M')}\n\n"
            
            # Add summary
            summary = trade_memory.get_performance_summary(days=days)
            if summary.get('closed_trades', 0) > 0:
                message += f"📈 *Summary*\n"
                message += f"Win Rate: {summary['win_rate']:.1f}%\n"
                message += f"Total PnL: {summary['total_pnl']:+.2f}%\n"
            
            update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in history command: {e}")
            update.message.reply_text("❌ Error retrieving trade history.")
    
    def _last_trade_command(self, update: Update, context: CallbackContext):
        """Handle the /last_trade command - show most recent trade details."""
        try:
            trade_memory = get_trade_memory()
            last_trade = trade_memory.get_last_trade()
            
            if not last_trade:
                update.message.reply_text(
                    "📊 *Last Trade* 📊\n\nNo trades found.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Format detailed trade info
            status_emoji = "🟢" if last_trade.status == "closed" and last_trade.result == "win" else "🔴" if last_trade.status == "closed" and last_trade.result == "loss" else "🟡"
            
            message = f"📊 *Last Trade Details* 📊\n\n"
            message += f"{status_emoji} *{last_trade.symbol}* {last_trade.side.upper()}\n\n"
            
            message += f"💰 *Prices*\n"
            message += f"Entry: ${last_trade.entry_price:.4f}\n"
            if last_trade.exit_price:
                message += f"Exit: ${last_trade.exit_price:.4f}\n"
            
            message += f"\n🎯 *Risk Management*\n"
            if last_trade.stop_loss:
                message += f"Stop Loss: ${last_trade.stop_loss:.4f}\n"
            if last_trade.take_profit:
                message += f"Take Profit: ${last_trade.take_profit:.4f}\n"
            if last_trade.risk_reward_ratio:
                message += f"R/R Ratio: {last_trade.risk_reward_ratio:.2f}\n"
            
            message += f"\n📊 *Strategy*\n"
            message += f"Strategy: {last_trade.strategy or 'N/A'}\n"
            message += f"Regime: {last_trade.regime or 'N/A'}\n"
            message += f"Confidence: {last_trade.confidence_score:.2f}\n"
            message += f"Timeframe: {last_trade.timeframe}\n"
            
            message += f"\n⏰ *Timing*\n"
            message += f"Entry: {last_trade.timestamp_entry.strftime('%Y-%m-%d %H:%M:%S')}\n"
            if last_trade.timestamp_exit:
                message += f"Exit: {last_trade.timestamp_exit.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            if last_trade.pnl_percentage is not None:
                pnl_sign = "+" if last_trade.pnl_percentage > 0 else ""
                message += f"\n💹 *Result*\n"
                message += f"PnL: {pnl_sign}{last_trade.pnl_percentage:.2f}%\n"
                message += f"Status: {last_trade.result or last_trade.status}\n"
            
            if last_trade.notes:
                message += f"\n📝 *Notes*\n{last_trade.notes}\n"
            
            update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in last_trade command: {e}")
            update.message.reply_text("❌ Error retrieving last trade.")
    
    def _trades_command(self, update: Update, context: CallbackContext):
        """Handle the /trades command - show trade summary and stats."""
        try:
            args = context.args
            days = None
            
            # Parse days argument
            for arg in args:
                if arg.endswith('d'):
                    try:
                        days = int(arg[:-1])
                    except ValueError:
                        pass
                elif arg.isdigit():
                    days = int(arg)
            
            trade_memory = get_trade_memory()
            summary = trade_memory.get_performance_summary(days=days)
            
            period_text = f" ({days} days)" if days else " (All Time)"
            message = f"📊 *Trading Summary*{period_text} 📊\n\n"
            
            if summary.get('total_trades', 0) == 0:
                message += "No trades found for this period."
            else:
                message += f"📈 *Overview*\n"
                message += f"Total Trades: {summary['total_trades']}\n"
                message += f"Closed: {summary['closed_trades']} | Open: {summary['open_trades']}\n\n"
                
                if summary['closed_trades'] > 0:
                    message += f"🎯 *Performance*\n"
                    message += f"Win Rate: {summary['win_rate']:.1f}%\n"
                    message += f"Total PnL: {summary['total_pnl']:+.2f}%\n"
                    message += f"Avg PnL: {summary['avg_pnl']:+.2f}%\n"
                    message += f"Best Trade: +{summary['best_trade']:.2f}%\n"
                    message += f"Worst Trade: {summary['worst_trade']:+.2f}%\n\n"
                    
                    if summary['avg_win'] > 0 and summary['avg_loss'] < 0:
                        message += f"📊 *Risk Metrics*\n"
                        message += f"Avg Win: +{summary['avg_win']:.2f}%\n"
                        message += f"Avg Loss: {summary['avg_loss']:+.2f}%\n"
                        message += f"Profit Factor: {summary['profit_factor']:.2f}\n\n"
                    
                    # Top strategies
                    if summary.get('strategies'):
                        message += f"🎯 *Top Strategies*\n"
                        sorted_strategies = sorted(summary['strategies'].items(), 
                                                 key=lambda x: x[1]['total_pnl'], reverse=True)
                        for strategy, stats in sorted_strategies[:3]:
                            message += f"{strategy}: {stats['total_pnl']:+.2f}% ({stats['trades']} trades)\n"
                        message += "\n"
                    
                    # Top symbols
                    if summary.get('symbols'):
                        message += f"💰 *Top Symbols*\n"
                        sorted_symbols = sorted(summary['symbols'].items(), 
                                              key=lambda x: x[1]['total_pnl'], reverse=True)
                        for symbol, stats in sorted_symbols[:3]:
                            message += f"{symbol}: {stats['total_pnl']:+.2f}% ({stats['trades']} trades)\n"
            
            update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in trades command: {e}")
            update.message.reply_text("❌ Error retrieving trade summary.")
    
    def _recovery_command(self, update: Update, context: CallbackContext):
        """Handle the /recovery command - show recovery engine status."""
        try:
            recovery_engine = get_recovery_engine()
            status = recovery_engine.get_status()
            
            message = f"🔄 *Auto-Recovery Status* 🔄\n\n"
            
            message += f"🟢 Recovery Enabled: {'Yes' if status['recovery_enabled'] else 'No'}\n"
            message += f"🔄 Auto-Save Running: {'Yes' if status['auto_save_running'] else 'No'}\n"
            message += f"⏱️ Save Interval: {status['auto_save_interval']}s\n"
            message += f"💾 Has Saved State: {'Yes' if status['has_saved_state'] else 'No'}\n"
            
            if status['current_state_time']:
                message += f"🕐 Last Save: {status['current_state_time']}\n"
            
            message += f"📁 Backup Count: {status['backup_count']}\n"
            message += f"📂 Data Dir: {status['data_directory']}\n\n"
            
            # Show open trades count
            trade_memory = get_trade_memory()
            open_trades = trade_memory.get_open_trades()
            message += f"📊 Open Trades: {len(open_trades)}\n"
            
            if context.args and 'test' in context.args:
                message += "\n🧪 Running recovery test...\n"
                test_result = recovery_engine.force_recovery_test()
                message += f"Test Result: {'✅ Passed' if test_result['success'] else '❌ Failed'}\n"
            
            update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error in recovery command: {e}")
            update.message.reply_text("❌ Error retrieving recovery status.")
    
    async def _forecast_command(self, update: Update, context: CallbackContext):
        """Handle /forecast command for visual AI forecasting.
        
        Usage: /forecast [symbol] [timeframe] [format]
        Examples:
        - /forecast
        - /forecast ETHUSDT
        - /forecast BTCUSDT 4h
        - /forecast symbol=ADAUSDT timeframe=1h
        """
        try:
            await self.forecast_handler.handle_forecast_command(update, context)
        except Exception as e:
            logger.error(f"Error in forecast command: {e}")
            await update.message.reply_text(
                "❌ Error generating forecast. Please try again later."
            )
    
    async def _plan_command(self, update: Update, context: CallbackContext):
        """Handle /plan command for comprehensive trading plan with visual forecast.
        
        Usage: /plan [symbol]
        Examples:
        - /plan
        - /plan ETHUSDT
        """
        try:
            await self.forecast_handler.handle_plan_command(update, context)
        except Exception as e:
            logger.error(f"Error in plan command: {e}")
            await update.message.reply_text(
                "❌ Error generating trading plan. Please try again later."
            )
    
    def _error_handler(self, update, context):
        """Log errors caused by updates."""
        logger.error(f"Update {update} caused error {context.error}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    handler = TelegramCommandHandler()
    
    # Start the handler
    handler.start()
    
    try:
        # Send test message if chat ID provided
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        if chat_id:
            handler.send_test_message(chat_id)
    except Exception as e:
        logger.error(f"Error sending test message: {str(e)}")
    
    # Run until Ctrl+C
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handler.stop()
