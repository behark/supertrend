#!/usr/bin/env python
"""
Telegram Command Center Integration Module
Connects the Telegram Command Center to the main trading bot
"""
import os
import sys
import logging
import json
import threading
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/telegram_integration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('telegram_integration')

# Try to import required modules
try:
    from telegram.ext import Updater
    from telegram_command_center import (
        initialize_command_center, register_command_handlers,
        BOT_STATE, update_bot_state, get_daily_trade_limit, get_daily_signal_limit,
        get_logs, perform_reset
    )
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    logger.error("Make sure telegram_command_center.py exists and python-telegram-bot is installed")
    sys.exit(1)

# Global state
telegram_updater = None
telegram_thread = None
is_running = False

# Main Bot State Interface
# These functions will be monkey-patched into the command center module
# to provide access to the main bot's state and functionality

async def update_bot_state_impl():
    """
    Implementation of update_bot_state that reads from the main bot
    This replaces the placeholder in telegram_command_center.py
    """
    try:
        # Import here to avoid circular imports
        from bot import (
            get_trade_mode, get_risk_level, get_pause_state,
            get_daily_trade_count, get_daily_signal_count,
            get_high_confidence_count, get_elite_confidence_count,
            get_bot_uptime
        )
        
        # Update the command center's BOT_STATE with real values
        BOT_STATE['mode'] = get_trade_mode()
        BOT_STATE['risk_level'] = get_risk_level()
        BOT_STATE['paused'] = get_pause_state()
        BOT_STATE['daily_trades'] = get_daily_trade_count()
        BOT_STATE['daily_signals'] = get_daily_signal_count()
        BOT_STATE['high_confidence_count'] = get_high_confidence_count()
        BOT_STATE['elite_confidence_count'] = get_elite_confidence_count()
        BOT_STATE['last_status_update'] = get_bot_uptime()
        
        logger.debug("Bot state updated from main bot")
    except Exception as e:
        logger.error(f"Error updating bot state: {e}")

def get_daily_trade_limit_impl():
    """Implementation of get_daily_trade_limit that reads from config"""
    try:
        # Import here to avoid circular imports
        from config import MAX_DAILY_TRADES
        return MAX_DAILY_TRADES
    except Exception:
        # Default from Bidget config
        return 15

def get_daily_signal_limit_impl():
    """Implementation of get_daily_signal_limit that reads from config"""
    try:
        # Import here to avoid circular imports
        from config import MAX_DAILY_SIGNALS
        return MAX_DAILY_SIGNALS
    except Exception:
        # Default from Bidget config
        return 30

def get_logs_impl(log_type):
    """Implementation of get_logs that reads actual log files"""
    try:
        if log_type == "today":
            # Read today's logs from main log file
            with open("logs/bot.log", "r") as f:
                lines = f.readlines()
                # Get today's date
                from datetime import datetime
                today = datetime.now().strftime("%Y-%m-%d")
                # Filter for today's entries
                today_logs = [line for line in lines if today in line]
                return "".join(today_logs[-100:])  # Last 100 lines for today
        elif log_type == "errors":
            # Read error logs
            with open("logs/bot.log", "r") as f:
                lines = f.readlines()
                # Filter for errors
                error_logs = [line for line in lines if "ERROR" in line]
                return "".join(error_logs[-50:])  # Last 50 error lines
        return "No logs available for the specified type"
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return f"Error reading logs: {e}"

def perform_reset_impl():
    """Implementation of perform_reset that calls the main bot's reset function"""
    try:
        # Import here to avoid circular imports
        from bot import reset_all_daily_stats
        
        # Call the actual reset function
        reset_all_daily_stats()
        logger.info("Manual reset performed via Telegram command")
        
        # Also run the update_bot_state to refresh all values
        import asyncio
        asyncio.run(update_bot_state_impl())
        
        return True
    except Exception as e:
        logger.error(f"Error performing reset: {e}")
        return False

# Command Implementation Functions
# These functions implement the actual commands by calling the main bot

def set_trade_mode(mode):
    """Set the trading mode in the main bot"""
    try:
        # Import here to avoid circular imports
        from bot import set_trade_mode as bot_set_mode
        
        # Call the actual function
        success = bot_set_mode(mode)
        if success:
            logger.info(f"Trading mode changed to {mode} via Telegram command")
            BOT_STATE['mode'] = mode
        else:
            logger.error(f"Failed to change trading mode to {mode}")
        return success
    except Exception as e:
        logger.error(f"Error setting trade mode: {e}")
        return False

def set_risk_level(level):
    """Set the risk level in the main bot"""
    try:
        # Import here to avoid circular imports
        from bot import set_risk_level as bot_set_risk
        
        # Call the actual function
        success = bot_set_risk(level)
        if success:
            logger.info(f"Risk level changed to {level} via Telegram command")
            BOT_STATE['risk_level'] = level
        else:
            logger.error(f"Failed to change risk level to {level}")
        return success
    except Exception as e:
        logger.error(f"Error setting risk level: {e}")
        return False

def set_pause_state(paused):
    """Set the pause state in the main bot"""
    try:
        # Import here to avoid circular imports
        from bot import set_pause_state as bot_set_pause
        
        # Call the actual function
        success = bot_set_pause(paused)
        if success:
            logger.info(f"Pause state set to {paused} via Telegram command")
            BOT_STATE['paused'] = paused
        else:
            logger.error(f"Failed to set pause state to {paused}")
        return success
    except Exception as e:
        logger.error(f"Error setting pause state: {e}")
        return False

# Main Integration Function

def integrate_command_center():
    """Integrate the Telegram Command Center with the main bot"""
    # Monkey patch the command center functions with our implementations
    import telegram_command_center
    telegram_command_center.update_bot_state = update_bot_state_impl
    telegram_command_center.get_daily_trade_limit = get_daily_trade_limit_impl
    telegram_command_center.get_daily_signal_limit = get_daily_signal_limit_impl
    telegram_command_center.get_logs = get_logs_impl
    telegram_command_center.perform_reset = perform_reset_impl
    
    # Initialize the command center
    success = initialize_command_center()
    if not success:
        logger.error("Failed to initialize Telegram Command Center")
        return False
    
    logger.info("Telegram Command Center integrated with main bot")
    return True

def start_command_center():
    """Start the Telegram Command Center in a separate thread"""
    global telegram_updater, telegram_thread, is_running
    
    if is_running:
        logger.warning("Telegram Command Center is already running")
        return False
    
    try:
        # Get the bot token from environment
        from dotenv import load_dotenv
        load_dotenv()
        load_dotenv('.env_telegram')
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
            return False
        
        # Create the updater
        telegram_updater = Updater(token=bot_token, use_context=True)
        
        # Register command handlers
        register_command_handlers(telegram_updater.dispatcher)
        
        # Start the bot in a separate thread
        telegram_thread = threading.Thread(target=telegram_updater.start_polling)
        telegram_thread.daemon = True
        telegram_thread.start()
        
        is_running = True
        logger.info("Telegram Command Center started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting Telegram Command Center: {e}")
        return False

def stop_command_center():
    """Stop the Telegram Command Center"""
    global telegram_updater, is_running
    
    if not is_running:
        logger.warning("Telegram Command Center is not running")
        return False
    
    try:
        # Stop the updater
        if telegram_updater:
            telegram_updater.stop()
            is_running = False
            logger.info("Telegram Command Center stopped successfully")
            return True
    except Exception as e:
        logger.error(f"Error stopping Telegram Command Center: {e}")
    
    return False

# Main entry point for testing
if __name__ == "__main__":
    print("Telegram Command Center Integration Module")
    print("This module should be imported by the main bot, not run directly.")
    print("For testing, you can uncomment and run the following:")
    """
    # Test integration
    if integrate_command_center():
        print("Integration successful")
        
        # Test starting the command center
        if start_command_center():
            print("Command center started successfully")
            
            # Keep the main thread alive
            import time
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Stopping command center...")
                stop_command_center()
        else:
            print("Failed to start command center")
    else:
        print("Integration failed")
    """
