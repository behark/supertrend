#!/usr/bin/env python3
"""
Test script to verify Telegram integration
"""

import os
import logging
from dotenv import load_dotenv
from src.integrations.telegram import TelegramNotifier
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def main():
    """Test Telegram integration"""
    # Load environment variables
    load_dotenv()
    
    logger.info("Testing Telegram integration...")
    
    # Initialize Telegram notifier
    telegram = TelegramNotifier()
    
    if not telegram.is_configured:
        logger.error("Telegram is not properly configured. Check your .env file.")
        return
    
    # Send test message
    logger.info("Sending test message to Telegram...")
    result = telegram.test_notification()
    
    if "error" in result:
        logger.error(f"Failed to send test message: {result['error']}")
    else:
        logger.info(f"Test message sent successfully!")
        logger.info(f"Message ID: {result.get('result', {}).get('message_id')}")

if __name__ == "__main__":
    main()
