#!/usr/bin/env python
"""
Test script to temporarily lower entry threshold for a specific pair
"""

import os
import sys
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Threshold-Test")

# Add project path
sys.path.append('/home/behar/CascadeProjects/SuperTrend/Inside=Bar:Strategy')

# Import after setting path
try:
    from src.bot import SuperTrendBot
    from src.integrations.telegram import TelegramNotifier
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

def main():
    """Main function to temporarily lower threshold for a specific pair"""
    logger.info("Starting threshold adjustment test")
    
    # Target pair to test (choose a low-priced crypto)
    test_pair = "DOGE/USDT"  # Can be changed to any preferred low-priced crypto
    
    # Initialize the bot
    bot = SuperTrendBot(test_mode=False)
    
    # Store original confidence threshold
    original_threshold = bot.confidence_threshold
    logger.info(f"Original confidence threshold: {original_threshold}%")
    
    # Lower the threshold temporarily
    test_threshold = 50.0  # Lower threshold to increase chance of signal
    bot.confidence_threshold = test_threshold
    bot.original_confidence_threshold = original_threshold
    bot.restore_confidence_after_trade = True
    
    logger.info(f"Temporarily lowered confidence threshold to {test_threshold}% for {test_pair}")
    
    # Send notification about the test
    if bot.telegram and bot.telegram.is_configured:
        message = f"🔍 *Diagnostic Test Started*\n\n"
        message += f"Temporarily lowering confidence threshold from {original_threshold}% to {test_threshold}%\n"
        message += f"Target pair: {test_pair}\n"
        message += f"This is a diagnostic test to verify trade activation logic.\n"
        message += f"The threshold will be automatically restored after a successful trade."
        
        bot.telegram.send_message(message)
    
    # Run a single market scan focused on the test pair
    logger.info(f"Running focused market scan for {test_pair}")
    
    # Override the markets list to focus on the test pair
    bot.market_data.markets = [test_pair]
    
    # Run the scan
    bot.scan_markets()
    
    # Restore the full market list
    bot.market_data.markets = bot.market_data._get_markets_from_config()
    
    logger.info("Test completed. The bot will restore the threshold after a successful trade.")
    logger.info(f"If no trade is executed, the threshold will remain at {test_threshold}% until manually reset.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
