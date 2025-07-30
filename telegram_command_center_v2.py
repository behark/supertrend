#!/usr/bin/env python3
"""
Telegram Command Center v2 for Bidget Auto Trading Bot
-----------------------------------------------------
Provides full control and monitoring through Telegram commands
Allows users to control the bot without requiring terminal or dashboard access
"""
import os
import sys
import json
import time
import logging
import threading
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union, Tuple

from telegram import Update, ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackContext, MessageHandler,
    Filters, CallbackQueryHandler, Dispatcher
)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Local imports - will be used by command handlers
from config import SETTINGS
from market_regime import MarketRegime
from playbook import Playbook
from trade_planner import SmartTradePlanner

logger = logging.getLogger(__name__)

class TelegramCommandCenterV2:
    """
    Advanced Telegram Command Center for Bidget Auto Trading Bot
    Provides comprehensive control and monitoring through Telegram commands
    """
    
    def __init__(self, 
                 bot_instance=None, 
                 data_dir: str = 'data',
                 config_path: str = 'data/telegram_config.json'):
        """
        Initialize the Telegram Command Center V2
        
        Args:
            bot_instance: Main bot instance for accessing bot functions
            data_dir: Directory for data files
            config_path: Path to Telegram configuration file
        """
        self.bot_instance = bot_instance
        self.data_dir = data_dir
        self.config_path = config_path
        self.config = {}
        self.start_time = datetime.now()
        
        # Status tracking
        self.is_paused = False
        self.alerts_enabled = True
        self.admin_password = os.getenv('TELEGRAM_ADMIN_PASSWORD', 'adminpass')
        
        # Create directories
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Initialize components that can be accessed directly
        self.market_regime = MarketRegime(data_dir=data_dir)
        self.playbook = Playbook(data_dir=data_dir)
        self.trade_planner = SmartTradePlanner(data_dir=data_dir)
        
        # Authorized users
        self.authorized_users = self._get_authorized_users()
        
        # Telegram setup
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            self.updater = None
        else:
            self.updater = Updater(token=self.bot_token, use_context=True)
            self.dispatcher = self.updater.dispatcher
            
            # Register command handlers
            self._register_handlers()
        
        # Load configuration
        self._load_config()
        
        logger.info("🚀 Telegram Command Center V2 initialized")
    
    def _get_authorized_users(self) -> List[str]:
        """Get list of authorized user IDs from environment or config"""
        auth_str = os.getenv('TELEGRAM_AUTHORIZED_USERS', '')
        if auth_str:
            return [user.strip() for user in auth_str.split(',') if user.strip()]
        
        # Default to the main chat ID if no specific authorized users
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        return [chat_id] if chat_id else []
    
    def _load_config(self) -> None:
        """Load Telegram Command Center configuration"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.info(f"Loaded Telegram command center configuration")
            else:
                # Create default configuration
                self.config = {
                    "alerts_enabled": True,
                    "admin_users": self.authorized_users,
                    "command_history": [],
                    "last_updated": datetime.now().isoformat()
                }
                self._save_config()
        except Exception as e:
            logger.error(f"Error loading Telegram configuration: {str(e)}")
            self.config = {
                "alerts_enabled": True,
                "admin_users": self.authorized_users,
                "command_history": [],
                "last_updated": datetime.now().isoformat()
            }
    
    def _save_config(self) -> None:
        """Save Telegram Command Center configuration"""
        try:
            self.config["last_updated"] = datetime.now().isoformat()
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.debug("Saved Telegram command center configuration")
        except Exception as e:
            logger.error(f"Error saving Telegram configuration: {str(e)}")

    def _register_handlers(self) -> None:
        """Register all command handlers with the Telegram dispatcher"""
        if not self.dispatcher:
            logger.error("Cannot register handlers: Telegram dispatcher not initialized")
            return
        
        # Core Commands (from spec)
        self.dispatcher.add_handler(CommandHandler("plan", self._cmd_plan))
        self.dispatcher.add_handler(CommandHandler("regime", self._cmd_regime))
        self.dispatcher.add_handler(CommandHandler("strategy", self._cmd_strategy))
        self.dispatcher.add_handler(CommandHandler("status", self._cmd_status))
        self.dispatcher.add_handler(CommandHandler("config", self._cmd_config))
        self.dispatcher.add_handler(CommandHandler("alerts", self._cmd_alerts))
        self.dispatcher.add_handler(CommandHandler("playbook", self._cmd_playbook))
        self.dispatcher.add_handler(CommandHandler("pause", self._cmd_pause))
        self.dispatcher.add_handler(CommandHandler("resume", self._cmd_resume))
        self.dispatcher.add_handler(CommandHandler("admin", self._cmd_admin))
        
        # Basic commands
        self.dispatcher.add_handler(CommandHandler("start", self._cmd_start))
        self.dispatcher.add_handler(CommandHandler("help", self._cmd_help))
        
        # Callback query handler for buttons
        self.dispatcher.add_handler(CallbackQueryHandler(self._button_callback))
        
        # Error handler
        self.dispatcher.add_error_handler(self._error_handler)
    
    def _is_authorized(self, user_id: str) -> bool:
        """Check if a user is authorized to use bot commands"""
        # Convert to string for consistent comparison
        user_id_str = str(user_id)
        
        # Allow if in authorized users list or if no restrictions are set
        return (not self.authorized_users) or (user_id_str in self.authorized_users)
    
    def _record_command(self, update: Update) -> None:
        """Record command usage for analytics"""
        try:
            if not update.message:
                return
                
            user = update.effective_user
            command = update.message.text
            
            # Store in command history (limited to 100 entries)
            entry = {
                "command": command,
                "user_id": user.id,
                "username": user.username or 'Unknown',
                "timestamp": datetime.now().isoformat()
            }
            
            self.config.setdefault("command_history", [])
            self.config["command_history"].insert(0, entry)
            if len(self.config["command_history"]) > 100:
                self.config["command_history"] = self.config["command_history"][:100]
                
            # Save periodically (not on every command to avoid file I/O overhead)
            if len(self.config["command_history"]) % 10 == 0:
                self._save_config()
        except Exception as e:
            logger.error(f"Error recording command: {str(e)}")
    
    def _error_handler(self, update: Update, context: CallbackContext) -> None:
        """Handle errors in command processing"""
        logger.error(f"Update {update} caused error: {context.error}")
        
        # Log detailed traceback
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = ''.join(tb_list)
        logger.error(f"Exception traceback:\n{tb_string}")
        
        # Send error message to user if possible
        if update and update.effective_message:
            update.effective_message.reply_text(
                "⚠️ An error occurred while processing your command. Please try again later.",
                parse_mode=ParseMode.MARKDOWN
            )
    
    def _button_callback(self, update: Update, context: CallbackContext) -> None:
        """Handle button callbacks from inline keyboards"""
        query = update.callback_query
        query.answer()
        
        # Process callback data
        data = query.data
        if data.startswith('confirm_'):
            action = data.split('_')[1]
            if action == "pause":
                self._do_pause()
                query.edit_message_text("⏸ Bot paused successfully.")
            elif action == "resume":
                self._do_resume()
                query.edit_message_text("▶️ Bot resumed successfully.")
            elif action == "alerts_on":
                self.alerts_enabled = True
                self.config["alerts_enabled"] = True
                self._save_config()
                query.edit_message_text("🔔 Alerts enabled successfully.")
            elif action == "alerts_off":
                self.alerts_enabled = False
                self.config["alerts_enabled"] = False
                self._save_config()
                query.edit_message_text("🔕 Alerts disabled successfully.")
        else:
            query.edit_message_text(f"Acknowledged: {data}")
    
    # Command Handlers
    
    def _cmd_start(self, update: Update, context: CallbackContext) -> None:
        """Handler for /start command"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        welcome_text = (
            f"*Welcome to Bidget Auto Trading Bot Command Center* 🤖\n\n"
            f"This bot provides full control over your trading activities.\n"
            f"Type /help to see available commands.\n\n"
            f"Your User ID: `{user.id}`\n"
        )
        update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)
    
    def _cmd_help(self, update: Update, context: CallbackContext) -> None:
        """Handler for /help command"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        help_text = (
            "*📲 Bidget Command Center Help* 🤖\n\n"
            "*Trading Controls*\n"
            "/plan - View current trade plan with details\n"
            "/regime - Display market regime for active symbols\n"
            "/strategy [name] - Switch strategy (e.g. supertrend, inside_bar)\n"
            "/playbook active - Show current regime-matched playbook\n\n"
            
            "*Bot Controls*\n"
            "/status - Bot health, uptime, signals\n"
            "/config [key]=[value] - Update configuration\n"
            "/alerts on|off - Toggle alert notifications\n"
            "/pause - Pause all trading activity\n"
            "/resume - Resume all trading activity\n\n"
            
            "*Admin*\n"
            "/admin [command] - Admin commands (password required)\n"
        )
        update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
        
    def _cmd_plan(self, update: Update, context: CallbackContext) -> None:
        """Handler for /plan command - Returns the current trade plan"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        try:
            # Load the most recent trade plan
            trade_plans_dir = os.path.join(self.data_dir, 'trade_plans')
            os.makedirs(trade_plans_dir, exist_ok=True)
            
            # Find latest trade plan
            plan_files = [f for f in os.listdir(trade_plans_dir) if f.endswith('_plan.json')]
            if not plan_files:
                update.message.reply_text("ℹ️ No active trade plans found.")
                return
                
            # Sort by modification time (latest first)
            latest_plan_file = sorted(
                plan_files, 
                key=lambda x: os.path.getmtime(os.path.join(trade_plans_dir, x)), 
                reverse=True
            )[0]
            
            with open(os.path.join(trade_plans_dir, latest_plan_file), 'r') as f:
                trade_plan = json.load(f)
                
            # Format the plan details for Telegram
            plan_message = self.trade_planner.format_trade_plan_message(trade_plan)
            update.message.reply_text(plan_message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error retrieving trade plan: {str(e)}")
            update.message.reply_text(f"⚠️ Error retrieving trade plan: {str(e)}")
    
    def _cmd_regime(self, update: Update, context: CallbackContext) -> None:
        """Handler for /regime command - Shows current market regime"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        try:
            # Get active symbols from settings or bot instance
            symbols = SETTINGS.get('SYMBOLS', [])
            if self.bot_instance and hasattr(self.bot_instance, 'symbols'):
                symbols = self.bot_instance.symbols
                
            if not symbols:
                update.message.reply_text("ℹ️ No active symbols configured.")
                return
            
            regimes = {}
            for symbol in symbols:
                # Use direct regime detection if possible
                try:
                    # Use the most recent data from the bot if available
                    if (self.bot_instance and 
                        hasattr(self.bot_instance, 'dataframes') and 
                        symbol in self.bot_instance.dataframes):
                        df = self.bot_instance.dataframes[symbol]
                        timeframe = self.bot_instance.timeframe
                    else:
                        # Placeholder for when we don't have live data
                        df = None
                        timeframe = SETTINGS.get('TIMEFRAME', '1h')
                        
                    if df is not None:
                        regime = self.market_regime.detect_regime(df, symbol, timeframe)
                    else:
                        regime = "unknown (no data)"
                    
                    regimes[symbol] = regime
                except Exception as e:
                    logger.error(f"Error detecting regime for {symbol}: {str(e)}")
                    regimes[symbol] = "error"
            
            # Format response
            response = "*📊 Current Market Regimes*\n\n"
            
            for symbol, regime in regimes.items():
                # Add emoji based on regime
                emoji = "🟢" if "bull" in regime else "🔴" if "bear" in regime else "⚪"
                if regime == "ranging":
                    emoji = "🟠"
                elif regime == "volatile":
                    emoji = "🟣"
                elif regime == "calm":
                    emoji = "🔵"
                    
                response += f"{emoji} *{symbol}*: {regime.upper()}\n"
            
            update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Error processing regime command: {str(e)}")
            update.message.reply_text(f"⚠️ Error processing command: {str(e)}")
            
    def _cmd_strategy(self, update: Update, context: CallbackContext) -> None:
        """Handler for /strategy [name] command - Changes trading strategy"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        # Valid strategies
        valid_strategies = ["supertrend", "inside_bar", "support_resistance", "macd", "auto"]
        
        # Check if strategy is provided
        if not context.args or len(context.args) < 1:
            strategies_list = ", ".join([f"`{s}`" for s in valid_strategies])
            update.message.reply_text(
                f"⚠️ Please specify a strategy name.\n\nAvailable strategies: {strategies_list}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        strategy = context.args[0].lower()
        
        # Validate strategy
        if strategy not in valid_strategies:
            strategies_list = ", ".join([f"`{s}`" for s in valid_strategies])
            update.message.reply_text(
                f"⚠️ Invalid strategy: `{strategy}`\n\nAvailable strategies: {strategies_list}",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        try:
            # Set strategy in configuration or bot
            if self.bot_instance and hasattr(self.bot_instance, 'strategy'):
                self.bot_instance.strategy = strategy
            
            # Save to configuration
            self.config["active_strategy"] = strategy
            self._save_config()
            
            # Confirm to user
            update.message.reply_text(
                f"✅ Strategy changed to: *{strategy}*\n\nNew settings will apply to upcoming signals.",
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error changing strategy: {str(e)}")
            update.message.reply_text(f"⚠️ Error changing strategy: {str(e)}")
    
    def _cmd_status(self, update: Update, context: CallbackContext) -> None:
        """Handler for /status command - Shows bot health and status"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        try:
            # Calculate uptime
            uptime = datetime.now() - self.start_time
            hours, remainder = divmod(uptime.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            
            # Get active strategy
            active_strategy = self.config.get("active_strategy", "auto")
            if self.bot_instance and hasattr(self.bot_instance, 'strategy'):
                active_strategy = self.bot_instance.strategy
            
            # Get signal count
            signal_count = 0
            if self.bot_instance and hasattr(self.bot_instance, 'signal_count'):
                signal_count = self.bot_instance.signal_count
            
            # Get dashboard URL
            dashboard_url = "http://localhost:8050"
            if SETTINGS.get('DASHBOARD_URL'):
                dashboard_url = SETTINGS.get('DASHBOARD_URL')
                
            # Status indicators
            health_status = "✅ Good" if not self.is_paused else "⏸️ Paused"
            alerts_status = "✅ Enabled" if self.alerts_enabled else "🔕 Disabled"
            
            status_text = (
                f"*🤖 Bidget Bot Status*\n\n"
                f"*Health:* {health_status}\n"
                f"*Uptime:* {uptime_str}\n"
                f"*Alerts:* {alerts_status}\n"
                f"*Active Strategy:* `{active_strategy}`\n"
                f"*Signals Generated:* {signal_count}\n\n"
                f"*Dashboard:* [Open Dashboard]({dashboard_url})\n"
                f"*Current Time (UTC):* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
            )
            
            update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN, disable_web_page_preview=True)
            
        except Exception as e:
            logger.error(f"Error getting status: {str(e)}")
            update.message.reply_text(f"⚠️ Error getting status: {str(e)}")
    
    def _cmd_config(self, update: Update, context: CallbackContext) -> None:
        """Handler for /config [key]=[value] command - Update bot configuration"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        # Check for arguments
        if not context.args or not context.args[0]:
            # Display current configuration
            config_text = "*🔧 Current Configuration*\n\n"
            
            # Filter sensitive info
            safe_config = {k: v for k, v in self.config.items() 
                          if k not in ["admin_users", "command_history"]}
            
            for key, value in safe_config.items():
                config_text += f"`{key}`: `{value}`\n"
                
            config_text += "\n*Usage:* /config [key]=[value] to update a setting"
            
            update.message.reply_text(config_text, parse_mode=ParseMode.MARKDOWN)
            return
        
        try:
            # Check for key=value format
            arg_text = " ".join(context.args)
            if "=" not in arg_text:
                update.message.reply_text("⚠️ Invalid format. Use: /config key=value")
                return
                
            key, value = arg_text.split("=", 1)
            key = key.strip()
            value = value.strip()
            
            # Validate key (prevent sensitive settings from being changed)
            protected_keys = ["admin_users", "command_history"]
            if key in protected_keys:
                update.message.reply_text(f"⚠️ Cannot modify protected setting: `{key}`", 
                                        parse_mode=ParseMode.MARKDOWN)
                return
            
            # Special handling for boolean values
            if value.lower() in ["true", "yes", "1", "on"]:
                value = True
            elif value.lower() in ["false", "no", "0", "off"]:
                value = False
            
            # Update the config
            self.config[key] = value
            self._save_config()
            
            # Confirm to user
            update.message.reply_text(
                f"✅ Configuration updated:\n`{key}` = `{value}`", 
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Error updating configuration: {str(e)}")
            update.message.reply_text(f"⚠️ Error updating configuration: {str(e)}")
    
    def _cmd_alerts(self, update: Update, context: CallbackContext) -> None:
        """Handler for /alerts [on|off] command - Toggle alert notifications"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        # Check for arguments
        if not context.args or len(context.args) < 1:
            # Show current state and options
            current = "🔔 ON" if self.alerts_enabled else "🔕 OFF"
            
            # Create inline keyboard
            keyboard = [
                [InlineKeyboardButton("🔔 Enable Alerts", callback_data="confirm_alerts_on")],
                [InlineKeyboardButton("🔕 Disable Alerts", callback_data="confirm_alerts_off")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(
                f"*Alert Status:* {current}\n\nSelect an option to change:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
            return
        
        command = context.args[0].lower()
        
        if command in ["on", "enable", "1", "true"]:
            self.alerts_enabled = True
            self.config["alerts_enabled"] = True
            self._save_config()
            update.message.reply_text("🔔 Alerts have been enabled.")
        elif command in ["off", "disable", "0", "false"]:
            self.alerts_enabled = False
            self.config["alerts_enabled"] = False
            self._save_config()
            update.message.reply_text("🔕 Alerts have been disabled.")
        else:
            update.message.reply_text("⚠️ Invalid option. Use: /alerts on or /alerts off")
    
    def _cmd_playbook(self, update: Update, context: CallbackContext) -> None:
        """Handler for /playbook command - View active playbook for current regime"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        try:
            # Determine which playbook to show
            show_active = False
            playbook_name = None
            if context.args and len(context.args) > 0:
                if context.args[0].lower() == "active":
                    show_active = True
                else:
                    playbook_name = context.args[0].lower()
            
            # Load all available playbooks
            playbooks = self.playbook.load_playbooks()
            
            if not playbooks:
                update.message.reply_text("⚠️ No playbooks found")
                return
            
            if show_active:
                # Get current regime for the first symbol
                symbols = SETTINGS.get('SYMBOLS', [])
                if self.bot_instance and hasattr(self.bot_instance, 'symbols'):
                    symbols = self.bot_instance.symbols
                    
                if not symbols:
                    update.message.reply_text("⚠️ No active symbols to determine regime")
                    return
                    
                # Use first symbol to determine regime
                symbol = symbols[0]
                regime = "unknown"
                
                try:
                    # Use the most recent data from the bot if available
                    if (self.bot_instance and 
                        hasattr(self.bot_instance, 'dataframes') and 
                        symbol in self.bot_instance.dataframes):
                        df = self.bot_instance.dataframes[symbol]
                        timeframe = self.bot_instance.timeframe
                        regime = self.market_regime.detect_regime(df, symbol, timeframe)
                except Exception as e:
                    logger.error(f"Error detecting regime: {str(e)}")
                
                # Get active playbook based on regime
                active_playbook = self.playbook.get_playbook_for_regime(regime)
                
                if not active_playbook:
                    update.message.reply_text(f"⚠️ No playbook found for regime: {regime}")
                    return
                    
                # Format response
                playbook_text = (
                    f"*📖 Active Playbook for {regime.upper()} Regime*\n\n"
                    f"*Strategy:* `{active_playbook.get('strategy', 'Unknown')}`\n"
                    f"*Entry Type:* `{active_playbook.get('entry_type', 'Unknown')}`\n"
                    f"*Stop Loss:* `{active_playbook.get('stop_loss_pct', '?')}%`\n"
                    f"*Take Profit:* `{active_playbook.get('take_profit_pct', '?')}%`\n"
                    f"*Risk Per Trade:* `{active_playbook.get('risk_per_trade', '?')}%`\n"
                    f"*Max Position Size:* `{active_playbook.get('max_position_size', '?')}%`\n"
                    f"*Leverage:* `{active_playbook.get('leverage', '1')}x`\n\n"
                    f"*Symbol:* {symbol}\n"
                    f"*Current Regime:* {regime.upper()}"
                )
                
                update.message.reply_text(playbook_text, parse_mode=ParseMode.MARKDOWN)
                
            elif playbook_name:
                # Show specific playbook by name
                # Find matching playbook
                for pb_name, pb_data in playbooks.items():
                    if playbook_name in pb_name.lower():
                        playbook_text = f"*📖 Playbook: {pb_name}*\n\n"
                        
                        for key, value in pb_data.items():
                            playbook_text += f"*{key}:* `{value}`\n"
                        
                        update.message.reply_text(playbook_text, parse_mode=ParseMode.MARKDOWN)
                        return
                
                # No matching playbook found
                update.message.reply_text(f"⚠️ No playbook found with name: {playbook_name}")
                
            else:
                # List all available playbooks
                playbook_list = "*📚 Available Playbooks*\n\n"
                
                for i, name in enumerate(playbooks.keys(), 1):
                    playbook_list += f"{i}. `{name}`\n"
                    
                playbook_list += "\n*Usage:* /playbook active - Show active playbook\n"
                playbook_list += "*Usage:* /playbook [name] - Show specific playbook"
                
                update.message.reply_text(playbook_list, parse_mode=ParseMode.MARKDOWN)
                
        except Exception as e:
            logger.error(f"Error retrieving playbook: {str(e)}")
            update.message.reply_text(f"⚠️ Error retrieving playbook: {str(e)}")
    
    def _cmd_pause(self, update: Update, context: CallbackContext) -> None:
        """Handler for /pause command - Pause trading activity"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        # Create confirmation keyboard
        keyboard = [
            [InlineKeyboardButton("⏸ Confirm Pause", callback_data="confirm_pause")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_pause")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "⚠️ *Are you sure you want to pause all trading activity?*\n\n"
            "This will prevent any new trades until resumed.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    def _do_pause(self) -> None:
        """Actually pause the bot"""
        self.is_paused = True
        self.config["is_paused"] = True
        self._save_config()
        
        # Signal to bot instance
        if self.bot_instance and hasattr(self.bot_instance, 'set_paused'):
            self.bot_instance.set_paused(True)
        
        logger.info("🔴 Bot trading activity paused via Telegram command")
    
    def _cmd_resume(self, update: Update, context: CallbackContext) -> None:
        """Handler for /resume command - Resume trading activity"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        # Check if bot is actually paused
        if not self.is_paused:
            update.message.reply_text("ℹ️ Bot is already running.")
            return
        
        # Create confirmation keyboard
        keyboard = [
            [InlineKeyboardButton("▶️ Confirm Resume", callback_data="confirm_resume")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_resume")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(
            "⚠️ *Are you sure you want to resume trading activity?*\n\n"
            "This will allow new trades to be executed.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    def _do_resume(self) -> None:
        """Actually resume the bot"""
        self.is_paused = False
        self.config["is_paused"] = False
        self._save_config()
        
        # Signal to bot instance
        if self.bot_instance and hasattr(self.bot_instance, 'set_paused'):
            self.bot_instance.set_paused(False)
        
        logger.info("🟢 Bot trading activity resumed via Telegram command")
    
    def _cmd_admin(self, update: Update, context: CallbackContext) -> None:
        """Handler for /admin command - Advanced admin commands (password protected)"""
        user = update.effective_user
        if not self._is_authorized(user.id):
            update.message.reply_text("⛔ You are not authorized to use this bot.")
            return
            
        self._record_command(update)
        
        # Check if admin password is provided
        if not context.args or len(context.args) < 2:
            update.message.reply_text(
                "⚠️ Admin commands require a password.\n\n"
                "*Usage:* /admin [password] [command]\n\n"
                "Available admin commands:\n"
                "`restart` - Restart the bot\n"
                "`shutdown` - Shutdown the bot\n"
                "`add_user [user_id]` - Authorize a new user\n"
                "`remove_user [user_id]` - Remove an authorized user",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Validate password
        password = context.args[0]
        if password != self.admin_password:
            update.message.reply_text("⛔ Invalid admin password.")
            logger.warning(f"Invalid admin password attempt from user {user.id}")
            return
            
        # Process admin command
        admin_cmd = context.args[1].lower() if len(context.args) > 1 else ""
        
        if admin_cmd == "restart":
            update.message.reply_text("🔄 Restarting bot... This may take a moment.")
            # Signal restart
            if self.bot_instance and hasattr(self.bot_instance, 'restart'):
                self.bot_instance.restart()
            else:
                update.message.reply_text("⚠️ Restart functionality not available in this instance")
                
        elif admin_cmd == "shutdown":
            update.message.reply_text("🛑 Shutting down bot...")
            # Signal shutdown
            if self.bot_instance and hasattr(self.bot_instance, 'shutdown'):
                self.bot_instance.shutdown()
            else:
                update.message.reply_text("⚠️ Shutdown functionality not available in this instance")
                
        elif admin_cmd == "add_user" and len(context.args) > 2:
            new_user_id = context.args[2]
            if new_user_id not in self.authorized_users:
                self.authorized_users.append(new_user_id)
                self.config["admin_users"] = self.authorized_users
                self._save_config()
                update.message.reply_text(f"✅ User `{new_user_id}` authorized successfully.", 
                                         parse_mode=ParseMode.MARKDOWN)
            else:
                update.message.reply_text(f"ℹ️ User `{new_user_id}` is already authorized.", 
                                         parse_mode=ParseMode.MARKDOWN)
                
        elif admin_cmd == "remove_user" and len(context.args) > 2:
            remove_user_id = context.args[2]
            if remove_user_id in self.authorized_users:
                self.authorized_users.remove(remove_user_id)
                self.config["admin_users"] = self.authorized_users
                self._save_config()
                update.message.reply_text(f"✅ User `{remove_user_id}` removed from authorized users.", 
                                         parse_mode=ParseMode.MARKDOWN)
            else:
                update.message.reply_text(f"ℹ️ User `{remove_user_id}` is not in the authorized users list.", 
                                         parse_mode=ParseMode.MARKDOWN)
                
        else:
            update.message.reply_text("⚠️ Invalid admin command. Use /admin for help.")
    
    def start_polling(self) -> bool:
        """Start polling for Telegram updates"""
        if not self.updater:
            logger.error("Updater not initialized. Cannot start polling.")
            return False
            
        try:
            self.updater.start_polling()
            logger.info("🚀 Telegram Command Center V2 started polling successfully")
            return True
        except Exception as e:
            logger.error(f"Error starting Telegram polling: {str(e)}")
            return False
    
    def stop(self) -> None:
        """Stop the Telegram updater"""
        if self.updater:
            try:
                self.updater.stop()
                logger.info("🛑 Stopped Telegram Command Center V2")
            except Exception as e:
                logger.error(f"Error stopping Telegram updater: {str(e)}")
    
    def __del__(self) -> None:
        """Cleanup resources when object is destroyed"""
        self.stop()


# Example usage
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("telegram_command_center.log")
        ]
    )
    
    # Create and start the command center
    try:
        command_center = TelegramCommandCenterV2()
        print(f"🚀 Telegram Command Center v2 initialized with {len(command_center.authorized_users)} authorized users")
        print("Bot is now listening for commands...")
        
        # Start polling for updates
        command_center.start_polling()
        
        # Keep the script running
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⚠️ Keyboard interrupt received. Shutting down...")
            command_center.stop()
            print("✅ Telegram Command Center v2 shutdown complete")
    except Exception as e:
        print(f"❌ Error starting Telegram Command Center: {str(e)}")
        traceback.print_exc()
