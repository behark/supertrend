#!/usr/bin/env python3
"""
Trading Signal Bot - Main Entry Point
Scans futures markets for high-confidence signals using Supertrend+ADX and Inside Bar strategies.
"""

import os
import time
import logging
import argparse
from dotenv import load_dotenv
from src.bot import TradingBot
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the trading bot"""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Trading Signal Bot')
        parser.add_argument('--test', action='store_true', help='Run in test mode (no real trades)')
        args = parser.parse_args()
        
        # Load environment variables
        load_dotenv()
        
        # Configure test mode
        if args.test:
            os.environ['TEST_MODE'] = 'true'
            logger.info("Starting Trading Signal Bot in TEST MODE - no real trades will be executed")
        else:
            os.environ['TEST_MODE'] = 'false'
            logger.info("Starting Trading Signal Bot in LIVE MODE")
        
        # Initialize the trading bot
        bot = TradingBot()
        
        # Run the bot (this will block and run continuously)
        bot.run()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        
if __name__ == "__main__":
    main()
