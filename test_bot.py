#!/usr/bin/env python3
"""
Test script for the trading bot
"""

import os
import logging
import time
from dotenv import load_dotenv
from src.bot import TradingBot
from src.utils.logger import setup_logging
from src.integrations.telegram import TelegramNotifier

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def main():
    """Run the trading bot in test mode"""
    # Load environment variables
    load_dotenv()
    
    # Set fallback API flag if not already set
    if os.getenv('USE_FALLBACK_API') is None:
        os.environ['USE_FALLBACK_API'] = 'true'
    
    # Initialize Telegram notifier
    telegram = TelegramNotifier()
    if telegram.is_configured:
        telegram.send_message("🔄 *Bot Test Started*\nRunning trading bot in test mode...")
    
    logger.info("Initializing trading bot...")
    
    # Initialize trading bot in test mode
    bot = TradingBot(test_mode=True)
    
    # Run market scan for signals
    logger.info("Scanning markets for signals...")
    try:
        # scan_markets updates bot.pending_signals internally
        bot.scan_markets()
        
        logger.info(f"Found {len(bot.pending_signals)} potential signals")
        
        # The bot's process_pending_signals method handles filtering and selecting signals
        signals_to_notify = bot.pending_signals[:5]  # Just take the top 5 for testing
        
        logger.info(f"Selected {len(signals_to_notify)} signals for notification")
        
        # Send signals to Telegram
        if telegram.is_configured:
            for signal in signals_to_notify:
                message = bot._format_signal_message(signal)
                telegram.send_message(message)
            
            if not signals_to_notify:
                telegram.send_message("No signals found in this scan")
        
        logger.info("Bot test completed successfully!")
        if telegram.is_configured:
            telegram.send_message("✅ *Bot Test Completed*\nTest run finished successfully!")
            
    except Exception as e:
        logger.error(f"Error during bot test: {e}", exc_info=True)
        if telegram.is_configured:
            telegram.send_message(f"❌ *Bot Test Error*\nAn error occurred: {str(e)}")

if __name__ == "__main__":
    main()
