#!/usr/bin/env python
"""
Telegram Command Center for Bidget Enhanced Trading Bot
Provides remote control capabilities through Telegram commands
"""
import os
import sys
import logging
import json
import time
import threading
import datetime
from functools import wraps
from typing import List, Dict, Any, Callable, Optional, Union
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/telegram_command_center.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('telegram_command_center')

# Try to import required libraries, with helpful error messages if missing
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
    from telegram.ext import (
        Updater, CommandHandler, CallbackContext, CallbackQueryHandler,
        Filters, MessageHandler, ConversationHandler
    )
except ImportError:
    logger.error("Error: python-telegram-bot package is required.")
    logger.error("Please install it using: pip install python-telegram-bot==13.7")
    sys.exit(1)

# Load environment variables
load_dotenv()  # Load from .env file
load_dotenv('.env_telegram')  # Also try telegram-specific file if it exists

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
AUTHORIZED_USERS = os.getenv('TELEGRAM_AUTHORIZED_USERS', '').split(',')
INSTANCE_NAME = os.getenv('BOT_INSTANCE_NAME', 'Bidget Trading Bot')

# Bot state
BOT_STATE = {
    'mode': 'scan',  # Default mode: scan, live, debug
    'risk_level': 'medium',  # Default risk: low, medium, high
    'paused': False,  # Operational state
    'last_status_update': None,  # Timestamp of last status update
    'daily_trades': 0,  # Current day's trades
    'daily_signals': 0,  # Current day's signals
    'high_confidence_count': 0,  # Current high confidence signals
    'elite_confidence_count': 0,  # Current elite confidence signals
}

# Command access levels
ACCESS_LEVELS = {
    'view': 0,  # Basic status view, no changes (lowest)
    'adjust': 1,  # Adjust parameters, risk levels
    'control': 2,  # Change modes, pause/resume
    'admin': 3,  # Reset, admin functions (highest)
}

# Map users to access levels (default to view-only for authorized users)
USER_ACCESS_LEVELS = {}

# Button callbacks
CALLBACK_PATTERN = {
    'mode': 'mode_{mode}',  # e.g., mode_live
    'risk': 'risk_{level}',  # e.g., risk_high
    'action': 'action_{cmd}',  # e.g., action_pause
    'page': 'page_{view}',  # e.g., page_status2
}

# Function to load user access configuration
def load_user_access_config():
    """Load user access configuration from file"""
    global USER_ACCESS_LEVELS
    
    try:
        config_file = os.path.join('config', 'telegram_access.json')
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                USER_ACCESS_LEVELS = json.load(f)
                logger.info(f"Loaded access config for {len(USER_ACCESS_LEVELS)} users")
        else:
            # Default: authorized users get view access
            for user in AUTHORIZED_USERS:
                USER_ACCESS_LEVELS[user.strip()] = ACCESS_LEVELS['view']
            logger.info(f"Created default access levels for {len(AUTHORIZED_USERS)} users")
            
            # Save default config
            os.makedirs('config', exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(USER_ACCESS_LEVELS, f, indent=2)
    except Exception as e:
        logger.error(f"Error loading user access config: {e}")
        # Fallback to basic access
        for user in AUTHORIZED_USERS:
            USER_ACCESS_LEVELS[user.strip()] = ACCESS_LEVELS['view']

# Authentication decorator
def restricted(min_access_level: str = 'view'):
    """
    Decorator to restrict telegram commands based on user access level
    """
    def decorator(func):
        @wraps(func)
        async def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
            user_id = str(update.effective_user.id)
            
            # Check if user is authorized at all
            if user_id not in USER_ACCESS_LEVELS:
                logger.warning(f"Unauthorized access attempt by user {user_id}")
                await send_unauthorized_message(update)
                return
            
            # Check if user has sufficient access level
            user_level = USER_ACCESS_LEVELS.get(user_id, 0)
            required_level = ACCESS_LEVELS.get(min_access_level, 0)
            
            if user_level < required_level:
                logger.warning(f"Insufficient access level for user {user_id}. Has: {user_level}, Needs: {required_level}")
                await update.message.reply_text(
                    "⚠️ <b>Insufficient permissions</b>\n"
                    f"This command requires <b>{min_access_level}</b> access level.",
                    parse_mode=ParseMode.HTML
                )
                return
            
            # User has sufficient access, proceed with command
            return await func(update, context, *args, **kwargs)
        return wrapped
    return decorator

async def send_unauthorized_message(update: Update):
    """Send an informative message to unauthorized users"""
    await update.message.reply_text(
        "🔒 <b>Access Restricted</b>\n\n"
        f"This {INSTANCE_NAME} instance requires authorization.\n\n"
        "If you should have access, please contact the administrator "
        "with your Telegram ID: <code>" + str(update.effective_user.id) + "</code>",
        parse_mode=ParseMode.HTML
    )

# ---- Command Handlers ----

@restricted(min_access_level='view')
async def command_start(update: Update, context: CallbackContext):
    """Handle /start command"""
    user = update.effective_user
    
    await update.message.reply_html(
        f"👋 Welcome to <b>{INSTANCE_NAME} Command Center</b>, {user.mention_html()}!\n\n"
        "Use /help to see available commands.\n"
        "Use /status to see current system status."
    )

@restricted(min_access_level='view')
async def command_help(update: Update, context: CallbackContext):
    """Handle /help command"""
    user_id = str(update.effective_user.id)
    user_level = USER_ACCESS_LEVELS.get(user_id, 0)
    
    # Basic commands available to all authorized users
    help_text = (
        f"📟 <b>{INSTANCE_NAME} Command Center</b>\n\n"
        "<b>Basic Commands:</b>\n"
        "/status - View bot status and key metrics\n"
        "/logs [today|errors] - Access system logs\n"
    )
    
    # Add commands based on access level
    if user_level >= ACCESS_LEVELS['adjust']:
        help_text += (
            "\n<b>Control Commands:</b>\n"
            "/risk [low|medium|high] - Adjust risk level\n"
        )
    
    if user_level >= ACCESS_LEVELS['control']:
        help_text += (
            "/mode [scan|live|debug] - Change operating mode\n"
            "/pause - Temporarily halt trading\n"
            "/resume - Resume trading operations\n"
        )
        
    if user_level >= ACCESS_LEVELS['admin']:
        help_text += (
            "\n<b>Admin Commands:</b>\n"
            "/reset - Manual system reset\n"
            "/access - Manage user permissions\n"
        )
    
    await update.message.reply_html(help_text)

@restricted(min_access_level='view')
async def command_status(update: Update, context: CallbackContext):
    """Handle /status command"""
    # Update state with latest information (will be implemented when we integrate with the main bot)
    await update_bot_state()
    
    # Create status message
    status_text = (
        f"📊 <b>{INSTANCE_NAME} Status</b>\n\n"
        f"<b>Mode:</b> {BOT_STATE['mode'].upper()}\n"
        f"<b>Risk Level:</b> {BOT_STATE['risk_level'].upper()}\n"
        f"<b>Status:</b> {'PAUSED' if BOT_STATE['paused'] else 'ACTIVE'}\n"
        f"<b>Uptime:</b> {get_uptime_string()}\n\n"
        
        f"<b>Today's Activity:</b>\n"
        f"• Trades: {BOT_STATE['daily_trades']}/{get_daily_trade_limit()}\n"
        f"• Signals: {BOT_STATE['daily_signals']}/{get_daily_signal_limit()}\n"
        f"• High Confidence: {BOT_STATE['high_confidence_count']}\n"
        f"• Elite Signals: {BOT_STATE['elite_confidence_count']}\n"
    )
    
    # Create inline keyboard for quick actions
    keyboard = []
    
    # Add mode buttons if user has control access
    user_id = str(update.effective_user.id)
    user_level = USER_ACCESS_LEVELS.get(user_id, 0)
    
    if user_level >= ACCESS_LEVELS['control']:
        mode_buttons = [
            InlineKeyboardButton("📊 SCAN", callback_data=CALLBACK_PATTERN['mode'].format(mode='scan')),
            InlineKeyboardButton("🔴 LIVE", callback_data=CALLBACK_PATTERN['mode'].format(mode='live')),
            InlineKeyboardButton("🔧 DEBUG", callback_data=CALLBACK_PATTERN['mode'].format(mode='debug'))
        ]
        keyboard.append(mode_buttons)
    
    if user_level >= ACCESS_LEVELS['adjust']:
        risk_buttons = [
            InlineKeyboardButton("🔵 LOW", callback_data=CALLBACK_PATTERN['risk'].format(level='low')),
            InlineKeyboardButton("🟡 MED", callback_data=CALLBACK_PATTERN['risk'].format(level='medium')),
            InlineKeyboardButton("🔴 HIGH", callback_data=CALLBACK_PATTERN['risk'].format(level='high'))
        ]
        keyboard.append(risk_buttons)
    
    if user_level >= ACCESS_LEVELS['control']:
        action_buttons = []
        if BOT_STATE['paused']:
            action_buttons.append(InlineKeyboardButton("▶️ RESUME", callback_data=CALLBACK_PATTERN['action'].format(cmd='resume')))
        else:
            action_buttons.append(InlineKeyboardButton("⏸️ PAUSE", callback_data=CALLBACK_PATTERN['action'].format(cmd='pause')))
        
        if user_level >= ACCESS_LEVELS['admin']:
            action_buttons.append(InlineKeyboardButton("🔄 RESET", callback_data=CALLBACK_PATTERN['action'].format(cmd='reset')))
        
        keyboard.append(action_buttons)
    
    await update.message.reply_html(
        status_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@restricted(min_access_level='adjust')
async def command_risk(update: Update, context: CallbackContext):
    """Handle /risk command to change risk level"""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Please specify a risk level:\n"
            "/risk [low|medium|high]"
        )
        return
    
    risk_level = context.args[0].lower()
    if risk_level not in ['low', 'medium', 'high']:
        await update.message.reply_text("❌ Invalid risk level. Use: low, medium, or high")
        return
    
    # Update risk level (will be implemented when integrated)
    old_level = BOT_STATE['risk_level']
    BOT_STATE['risk_level'] = risk_level
    
    await update.message.reply_html(
        f"✅ Risk level changed from <b>{old_level.upper()}</b> to <b>{risk_level.upper()}</b>\n\n"
        f"This affects position sizing and entry criteria.\n"
        f"Use /status to see updated configuration."
    )

@restricted(min_access_level='control')
async def command_mode(update: Update, context: CallbackContext):
    """Handle /mode command to change operating mode"""
    if not context.args or len(context.args) < 1:
        await update.message.reply_text(
            "⚠️ Please specify a mode:\n"
            "/mode [scan|live|debug]"
        )
        return
    
    mode = context.args[0].lower()
    if mode not in ['scan', 'live', 'debug']:
        await update.message.reply_text("❌ Invalid mode. Use: scan, live, or debug")
        return
    
    # Update mode (will be implemented when integrated)
    old_mode = BOT_STATE['mode']
    BOT_STATE['mode'] = mode
    
    # Create response message based on new mode
    if mode == 'live':
        message = (
            "🔴 <b>LIVE MODE ACTIVATED</b>\n\n"
            "The bot will now execute real trades.\n"
            f"Risk Level: <b>{BOT_STATE['risk_level'].upper()}</b>\n"
            "Monitor closely and use /status to track activity."
        )
    elif mode == 'scan':
        message = (
            "📊 <b>SCAN MODE ACTIVATED</b>\n\n"
            "The bot will analyze markets but not execute trades.\n"
            "Signals will be reported through Telegram alerts."
        )
    else:  # debug
        message = (
            "🔧 <b>DEBUG MODE ACTIVATED</b>\n\n"
            "The bot will provide enhanced logging and output.\n"
            "Check /logs for detailed operation info."
        )
    
    await update.message.reply_html(message)

@restricted(min_access_level='control')
async def command_pause(update: Update, context: CallbackContext):
    """Handle /pause command to temporarily halt trading"""
    if BOT_STATE['paused']:
        await update.message.reply_html(
            "ℹ️ Trading is already paused.\n"
            "Use /resume to restart operations."
        )
        return
    
    # Pause trading (will be implemented when integrated)
    BOT_STATE['paused'] = True
    
    await update.message.reply_html(
        "⏸️ <b>TRADING PAUSED</b>\n\n"
        "All trading operations have been temporarily halted.\n"
        "Market scanning and signal processing will continue.\n\n"
        "Use /resume to restart trading operations."
    )

@restricted(min_access_level='control')
async def command_resume(update: Update, context: CallbackContext):
    """Handle /resume command to restart trading after pause"""
    if not BOT_STATE['paused']:
        await update.message.reply_html(
            "ℹ️ Trading is already active.\n"
            "Use /status to see current activity."
        )
        return
    
    # Resume trading (will be implemented when integrated)
    BOT_STATE['paused'] = False
    
    await update.message.reply_html(
        "▶️ <b>TRADING RESUMED</b>\n\n"
        "Normal trading operations have been restored.\n"
        f"Mode: <b>{BOT_STATE['mode'].upper()}</b>\n"
        f"Risk: <b>{BOT_STATE['risk_level'].upper()}</b>\n"
    )

@restricted(min_access_level='view')
async def command_logs(update: Update, context: CallbackContext):
    """Handle /logs command to view recent logs"""
    log_type = "today"
    if context.args and len(context.args) > 0:
        log_type = context.args[0].lower()
    
    if log_type not in ['today', 'errors']:
        await update.message.reply_text(
            "⚠️ Invalid log type. Use: /logs [today|errors]"
        )
        return
    
    # Get logs based on type (will be implemented when integrated)
    logs = get_logs(log_type)
    
    if not logs:
        await update.message.reply_text(
            f"No {log_type} logs available."
        )
        return
    
    # Format logs for Telegram (truncate if too long)
    if len(logs) > 3900:  # Telegram message limit with some margin
        logs = logs[:3900] + "...\n(truncated, see log files for complete output)"
    
    await update.message.reply_html(
        f"📜 <b>Bot Logs - {log_type.upper()}</b>\n\n"
        f"<pre>{logs}</pre>"
    )

@restricted(min_access_level='admin')
async def command_reset(update: Update, context: CallbackContext):
    """Handle /reset command to manually reset stats and counters"""
    # Confirm reset intention with inline buttons
    keyboard = [
        [
            InlineKeyboardButton("✅ YES", callback_data=CALLBACK_PATTERN['action'].format(cmd='confirm_reset')),
            InlineKeyboardButton("❌ NO", callback_data=CALLBACK_PATTERN['action'].format(cmd='cancel_reset'))
        ]
    ]
    
    await update.message.reply_html(
        "⚠️ <b>Manual Reset Confirmation</b>\n\n"
        "This will reset all daily counters and statistics.\n"
        "Trading positions will NOT be affected.\n\n"
        "Are you sure you want to proceed?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---- Callback Query Handlers ----

async def handle_callback_query(update: Update, context: CallbackContext):
    """Handle button callbacks from inline keyboards"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    
    # Check authorization
    if user_id not in USER_ACCESS_LEVELS:
        await query.answer("Unauthorized action.")
        return
    
    # Extract data
    data = query.data
    
    # Mode change callbacks
    if data.startswith("mode_"):
        mode = data.split("_")[1]
        if mode in ['scan', 'live', 'debug']:
            # Check access level
            if USER_ACCESS_LEVELS[user_id] < ACCESS_LEVELS['control']:
                await query.answer("Insufficient permissions for this action")
                return
            
            # Update mode (will be implemented when integrated)
            BOT_STATE['mode'] = mode
            await query.answer(f"Mode changed to {mode.upper()}")
            
            # Update message with new status
            await update_status_message(query.message)
    
    # Risk change callbacks
    elif data.startswith("risk_"):
        level = data.split("_")[1]
        if level in ['low', 'medium', 'high']:
            # Check access level
            if USER_ACCESS_LEVELS[user_id] < ACCESS_LEVELS['adjust']:
                await query.answer("Insufficient permissions for this action")
                return
            
            # Update risk level (will be implemented when integrated)
            BOT_STATE['risk_level'] = level
            await query.answer(f"Risk level changed to {level.upper()}")
            
            # Update message with new status
            await update_status_message(query.message)
    
    # Action callbacks
    elif data.startswith("action_"):
        action = data.split("_")[1]
        
        # Pause/resume actions
        if action in ['pause', 'resume']:
            # Check access level
            if USER_ACCESS_LEVELS[user_id] < ACCESS_LEVELS['control']:
                await query.answer("Insufficient permissions for this action")
                return
            
            # Update pause state (will be implemented when integrated)
            BOT_STATE['paused'] = (action == 'pause')
            await query.answer(f"Trading {'paused' if action == 'pause' else 'resumed'}")
            
            # Update message with new status
            await update_status_message(query.message)
        
        # Reset confirmation action
        elif action == 'confirm_reset':
            # Check access level
            if USER_ACCESS_LEVELS[user_id] < ACCESS_LEVELS['admin']:
                await query.answer("Insufficient permissions for this action")
                return
            
            # Perform reset (will be implemented when integrated)
            perform_reset()
            await query.answer("Reset completed")
            
            # Update message
            await query.edit_message_text(
                "✅ <b>Reset Completed</b>\n\n"
                "All daily counters and statistics have been reset.\n"
                "Use /status to view updated information.",
                parse_mode=ParseMode.HTML
            )
        
        # Cancel reset action
        elif action == 'cancel_reset':
            await query.edit_message_text(
                "❌ <b>Reset Cancelled</b>\n\n"
                "No changes have been made.",
                parse_mode=ParseMode.HTML
            )

# ---- Helper Functions ----

async def update_status_message(message):
    """Update an existing status message with current state"""
    # Update state with latest information (will be implemented when integrated)
    await update_bot_state()
    
    # Create status message
    status_text = (
        f"📊 <b>{INSTANCE_NAME} Status</b>\n\n"
        f"<b>Mode:</b> {BOT_STATE['mode'].upper()}\n"
        f"<b>Risk Level:</b> {BOT_STATE['risk_level'].upper()}\n"
        f"<b>Status:</b> {'PAUSED' if BOT_STATE['paused'] else 'ACTIVE'}\n"
        f"<b>Uptime:</b> {get_uptime_string()}\n\n"
        
        f"<b>Today's Activity:</b>\n"
        f"• Trades: {BOT_STATE['daily_trades']}/{get_daily_trade_limit()}\n"
        f"• Signals: {BOT_STATE['daily_signals']}/{get_daily_signal_limit()}\n"
        f"• High Confidence: {BOT_STATE['high_confidence_count']}\n"
        f"• Elite Signals: {BOT_STATE['elite_confidence_count']}\n"
    )
    
    # Create inline keyboard for quick actions
    keyboard = []
    
    # Determine user access level from message sender
    user_id = str(message.chat.id)  # This is a simplification, may need refinement
    user_level = USER_ACCESS_LEVELS.get(user_id, 0)
    
    if user_level >= ACCESS_LEVELS['control']:
        mode_buttons = [
            InlineKeyboardButton("📊 SCAN", callback_data=CALLBACK_PATTERN['mode'].format(mode='scan')),
            InlineKeyboardButton("🔴 LIVE", callback_data=CALLBACK_PATTERN['mode'].format(mode='live')),
            InlineKeyboardButton("🔧 DEBUG", callback_data=CALLBACK_PATTERN['mode'].format(mode='debug'))
        ]
        keyboard.append(mode_buttons)
    
    if user_level >= ACCESS_LEVELS['adjust']:
        risk_buttons = [
            InlineKeyboardButton("🔵 LOW", callback_data=CALLBACK_PATTERN['risk'].format(level='low')),
            InlineKeyboardButton("🟡 MED", callback_data=CALLBACK_PATTERN['risk'].format(level='medium')),
            InlineKeyboardButton("🔴 HIGH", callback_data=CALLBACK_PATTERN['risk'].format(level='high'))
        ]
        keyboard.append(risk_buttons)
    
    if user_level >= ACCESS_LEVELS['control']:
        action_buttons = []
        if BOT_STATE['paused']:
            action_buttons.append(InlineKeyboardButton("▶️ RESUME", callback_data=CALLBACK_PATTERN['action'].format(cmd='resume')))
        else:
            action_buttons.append(InlineKeyboardButton("⏸️ PAUSE", callback_data=CALLBACK_PATTERN['action'].format(cmd='pause')))
        
        if user_level >= ACCESS_LEVELS['admin']:
            action_buttons.append(InlineKeyboardButton("🔄 RESET", callback_data=CALLBACK_PATTERN['action'].format(cmd='reset')))
        
        keyboard.append(action_buttons)
    
    await message.edit_text(
        status_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

# Placeholder functions to be implemented when integrating with main bot
async def update_bot_state():
    """Update BOT_STATE with latest information from the main bot"""
    # This will be replaced with actual implementation
    pass

def get_daily_trade_limit():
    """Get the configured daily trade limit"""
    # This will be replaced with actual implementation
    return 15  # Default from Bidget config

def get_daily_signal_limit():
    """Get the configured daily signal limit"""
    # This will be replaced with actual implementation
    return 30  # Default from Bidget config

def get_logs(log_type):
    """Get logs of the specified type"""
    # This will be replaced with actual implementation
    if log_type == "today":
        try:
            with open("logs/bot.log", "r") as f:
                return f.read().strip()
        except:
            return "Error reading logs"
    elif log_type == "errors":
        try:
            # Simplified - would actually filter for error messages
            with open("logs/bot.log", "r") as f:
                lines = f.readlines()
                errors = [line for line in lines if "ERROR" in line]
                return "".join(errors).strip()
        except:
            return "Error reading logs"
    return "No logs available"

def perform_reset():
    """Perform a manual reset of daily stats and counters"""
    # This will be replaced with actual implementation when integrated
    global BOT_STATE
    BOT_STATE['daily_trades'] = 0
    BOT_STATE['daily_signals'] = 0
    BOT_STATE['high_confidence_count'] = 0
    BOT_STATE['elite_confidence_count'] = 0
    
    # In real implementation, this would call the reset functions in the main bot
    logger.info("Manual reset performed via Telegram command")

def get_uptime_string():
    """Get a formatted string representing the bot uptime"""
    # This will be replaced with actual implementation
    # For now, return a placeholder
    return "3h 24m"  # Placeholder

# ---- Main Function ----

def register_command_handlers(dispatcher):
    """Register all command handlers with the dispatcher"""
    dispatcher.add_handler(CommandHandler("start", command_start))
    dispatcher.add_handler(CommandHandler("help", command_help))
    dispatcher.add_handler(CommandHandler("status", command_status))
    dispatcher.add_handler(CommandHandler("risk", command_risk))
    dispatcher.add_handler(CommandHandler("mode", command_mode))
    dispatcher.add_handler(CommandHandler("pause", command_pause))
    dispatcher.add_handler(CommandHandler("resume", command_resume))
    dispatcher.add_handler(CommandHandler("logs", command_logs))
    dispatcher.add_handler(CommandHandler("reset", command_reset))
    
    # Register callback query handler
    dispatcher.add_handler(CallbackQueryHandler(handle_callback_query))
    
    logger.info("Command handlers registered successfully")

def initialize_command_center():
    """Initialize the Telegram Command Center"""
    # Load user access configuration
    load_user_access_config()
    
    logger.info(f"Telegram Command Center initialized with {len(USER_ACCESS_LEVELS)} authorized users")
    return True

# If this file is run directly, print an error (should be imported by the main bot)
if __name__ == "__main__":
    print("Error: This module should be imported by the main bot, not run directly.")
    print("Please use: from telegram_command_center import initialize_command_center, register_command_handlers")
    sys.exit(1)
