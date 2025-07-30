#!/usr/bin/env python3
"""
Bot Telegram Integration Module
Contains functions to interface between bot.py and the Telegram Command Center
"""
import os
import time
import logging
import json
from datetime import datetime
import threading
from typing import Dict, Any, Optional, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/bot_telegram_integration.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('bot_telegram_integration')

# Global state variables (shared with main bot)
BOT_START_TIME = time.time()
BOT_STATE = {
    'mode': 'scan',       # Current operating mode: 'scan', 'live', 'debug'
    'risk_level': 'medium',  # Current risk level: 'low', 'medium', 'high'
    'is_paused': False,   # Whether trading is paused
    'daily_trades': 0,    # Number of trades executed today
    'daily_signals': 0,   # Number of signals generated today
    'high_confidence_signals': 0,  # Signals with >95% confidence
    'elite_signals': 0,   # Signals with >98% confidence
    'last_trade_time': None,  # Timestamp of last trade
    'last_signal_time': None,  # Timestamp of last signal
    'active_pairs': []    # Currently active trading pairs
}

# State file paths
STATE_DIR = 'state'
STATE_FILE = os.path.join(STATE_DIR, 'bot_state.json')

# Risk level mapping
RISK_LEVELS = {
    'low': 0.1,      # 10% of available balance
    'medium': 0.3,   # 30% of available balance (Bidget default)
    'high': 0.5      # 50% of available balance
}

# Functions to get bot state
def get_trade_mode() -> str:
    """Get the current trading mode"""
    return BOT_STATE['mode']

def get_risk_level() -> str:
    """Get the current risk level"""
    return BOT_STATE['risk_level']

def get_pause_state() -> bool:
    """Get whether trading is paused"""
    return BOT_STATE['is_paused']

def get_daily_trade_count() -> int:
    """Get the number of trades executed today"""
    return BOT_STATE['daily_trades']

def get_daily_signal_count() -> int:
    """Get the number of signals generated today"""
    return BOT_STATE['daily_signals']

def get_high_confidence_count() -> int:
    """Get the number of high confidence signals today"""
    return BOT_STATE['high_confidence_signals']

def get_elite_confidence_count() -> int:
    """Get the number of elite confidence signals today"""
    return BOT_STATE['elite_signals']

def get_bot_uptime() -> str:
    """Get the bot's uptime as a formatted string"""
    uptime_seconds = time.time() - BOT_START_TIME
    hours, remainder = divmod(int(uptime_seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"

def get_active_pairs() -> list:
    """Get the currently active trading pairs"""
    return BOT_STATE['active_pairs']

# Functions to modify bot state
def set_trade_mode(mode: str) -> bool:
    """
    Set the trading mode
    Args:
        mode: 'scan', 'live', or 'debug'
    Returns:
        bool: Success or failure
    """
    if mode not in ['scan', 'live', 'debug']:
        logger.error(f"Invalid mode: {mode}")
        return False
    
    old_mode = BOT_STATE['mode']
    BOT_STATE['mode'] = mode
    
    logger.info(f"Trading mode changed from {old_mode} to {mode}")
    save_bot_state()
    
    # Additional logic to handle mode change can be added here
    # For example, if switching to live mode, we might want to do additional checks
    
    return True

def set_risk_level(level: str) -> bool:
    """
    Set the risk level
    Args:
        level: 'low', 'medium', or 'high'
    Returns:
        bool: Success or failure
    """
    if level not in ['low', 'medium', 'high']:
        logger.error(f"Invalid risk level: {level}")
        return False
    
    old_level = BOT_STATE['risk_level']
    BOT_STATE['risk_level'] = level
    
    logger.info(f"Risk level changed from {old_level} to {level}")
    save_bot_state()
    
    return True

def set_pause_state(paused: bool) -> bool:
    """
    Set whether trading is paused
    Args:
        paused: True to pause, False to resume
    Returns:
        bool: Success or failure
    """
    old_state = BOT_STATE['is_paused']
    BOT_STATE['is_paused'] = paused
    
    action = "paused" if paused else "resumed"
    logger.info(f"Trading {action}")
    save_bot_state()
    
    return True

def increment_daily_trades() -> None:
    """Increment the daily trade counter"""
    BOT_STATE['daily_trades'] += 1
    BOT_STATE['last_trade_time'] = datetime.now().isoformat()
    save_bot_state()

def increment_daily_signals(confidence: float = 0.0) -> None:
    """
    Increment the daily signal counter
    Args:
        confidence: Signal confidence level (0.0 to 1.0)
    """
    BOT_STATE['daily_signals'] += 1
    BOT_STATE['last_signal_time'] = datetime.now().isoformat()
    
    # Track high confidence and elite signals
    if confidence >= 0.98:
        BOT_STATE['elite_signals'] += 1
    elif confidence >= 0.95:
        BOT_STATE['high_confidence_signals'] += 1
    
    save_bot_state()

def reset_daily_counters() -> None:
    """Reset all daily counters"""
    BOT_STATE['daily_trades'] = 0
    BOT_STATE['daily_signals'] = 0
    BOT_STATE['high_confidence_signals'] = 0
    BOT_STATE['elite_signals'] = 0
    save_bot_state()
    logger.info("Daily counters reset")

def add_active_pair(pair: str) -> None:
    """Add a pair to the active pairs list"""
    if pair not in BOT_STATE['active_pairs']:
        BOT_STATE['active_pairs'].append(pair)
        save_bot_state()

def remove_active_pair(pair: str) -> None:
    """Remove a pair from the active pairs list"""
    if pair in BOT_STATE['active_pairs']:
        BOT_STATE['active_pairs'].remove(pair)
        save_bot_state()

# State persistence functions
def load_bot_state() -> None:
    """Load the bot state from disk"""
    global BOT_STATE
    
    try:
        # Ensure the state directory exists
        os.makedirs(STATE_DIR, exist_ok=True)
        
        # If the state file exists, load it
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                loaded_state = json.load(f)
                
                # Update BOT_STATE with the loaded values
                for key, value in loaded_state.items():
                    if key in BOT_STATE:
                        BOT_STATE[key] = value
                
                logger.info("Bot state loaded from disk")
        else:
            # If the state file doesn't exist, save the current state
            save_bot_state()
            logger.info("No state file found, created default state")
    except Exception as e:
        logger.error(f"Error loading bot state: {e}")

def save_bot_state() -> None:
    """Save the bot state to disk"""
    try:
        # Ensure the state directory exists
        os.makedirs(STATE_DIR, exist_ok=True)
        
        # Save the state
        with open(STATE_FILE, 'w') as f:
            json.dump(BOT_STATE, f, indent=2)
        
        logger.debug("Bot state saved to disk")
    except Exception as e:
        logger.error(f"Error saving bot state: {e}")

# Integration functions for bot.py
def initialize_telegram_integration() -> bool:
    """
    Initialize the Telegram integration
    Returns:
        bool: Success or failure
    """
    try:
        # Load the bot state
        load_bot_state()
        
        # Import and start the command center
        from telegram_command_integration import integrate_command_center, start_command_center
        
        # Integrate the command center
        if not integrate_command_center():
            logger.error("Failed to integrate Telegram Command Center")
            return False
        
        # Start the command center
        if not start_command_center():
            logger.error("Failed to start Telegram Command Center")
            return False
        
        logger.info("Telegram Command Center initialized and started")
        return True
    except Exception as e:
        logger.error(f"Error initializing Telegram integration: {e}")
        return False

def shutdown_telegram_integration() -> bool:
    """
    Shutdown the Telegram integration
    Returns:
        bool: Success or failure
    """
    try:
        # Import and stop the command center
        from telegram_command_integration import stop_command_center
        
        # Stop the command center
        if not stop_command_center():
            logger.error("Failed to stop Telegram Command Center")
            return False
        
        logger.info("Telegram Command Center stopped")
        return True
    except Exception as e:
        logger.error(f"Error shutting down Telegram integration: {e}")
        return False

# Initialize when this module is imported
if __name__ != "__main__":
    # Load the bot state when imported
    load_bot_state()

# For testing
if __name__ == "__main__":
    print("Bot Telegram Integration Module")
    print("This module should be imported by bot.py, not run directly.")
    print("For testing, you can manually check the state functions:")
    
    # Test state functions
    print(f"Current mode: {get_trade_mode()}")
    print(f"Current risk level: {get_risk_level()}")
    print(f"Paused: {get_pause_state()}")
    print(f"Daily trades: {get_daily_trade_count()}")
    print(f"Daily signals: {get_daily_signal_count()}")
    print(f"Bot uptime: {get_bot_uptime()}")
