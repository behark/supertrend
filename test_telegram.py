#!/usr/bin/env python
"""
Test script to verify Telegram integration
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
logger = logging.getLogger("Telegram-Test")

# Add project path
sys.path.append('/home/behar/CascadeProjects/SuperTrend/Inside=Bar:Strategy')

# Load environment variables from the correct location
from dotenv import load_dotenv
env_path = '/home/behar/CascadeProjects/SuperTrend/Inside=Bar:Strategy/.env'
load_dotenv(env_path)
logger.info(f"Loading environment variables from {env_path}")

# Import after setting path
try:
    from src.integrations.telegram import TelegramNotifier
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.error("Failed to import TelegramNotifier - check your project path")
    sys.exit(1)

def test_telegram_integration():
    """Test the Telegram integration"""
    logger.info("Starting Telegram integration test")
    
    # Initialize the Telegram notifier
    telegram = TelegramNotifier()
    
    if not telegram.is_configured:
        logger.error("Telegram is not configured. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
        return False
    
    logger.info(f"Telegram configuration: API configured = {telegram.is_configured}")
    
    # Test sending a simple message
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    test_message = f"🧪 *Telegram Test Message*\n\nThis is a test message sent at {current_time} to verify the Telegram integration is working correctly."
    
    logger.info("Sending test message to Telegram...")
    result = telegram.send_message(test_message)
    
    if result and 'error' not in result:
        logger.info("✅ Test message sent successfully!")
        return True
    else:
        error = result.get('error', 'Unknown error')
        logger.error(f"❌ Failed to send test message: {error}")
        return False

def test_signal_notification():
    """Test sending a signal notification"""
    logger.info("Testing signal notification")
    
    # Initialize the Telegram notifier
    telegram = TelegramNotifier()
    
    if not telegram.is_configured:
        logger.error("Telegram is not configured")
        return False
    
    # Create a test signal
    test_signal = {
        'symbol': 'BTC/USDT',
        'direction': 'LONG',
        'timeframe': '1h',
        'strategy': 'supertrend_adx',
        'strategy_name': 'SuperTrend ADX',
        'confidence': 95.0,
        'price': 39000.0,
        'profit_target': 42000.0,
        'stop_loss': 38000.0,
        'atr': 500.0,
        'win_probability': 92.5
    }
    
    logger.info("Sending test signal notification...")
    result = telegram.send_signal_notification(test_signal)
    
    if result and 'error' not in result:
        logger.info("✅ Signal notification sent successfully!")
        return True
    else:
        error = result.get('error', 'Unknown error')
        logger.error(f"❌ Failed to send signal notification: {error}")
        return False

def test_low_price_signal():
    """Test sending a signal for a low price crypto"""
    logger.info("Testing low price crypto signal notification")
    
    # Initialize the Telegram notifier
    telegram = TelegramNotifier()
    
    # Create a test signal for a low price crypto
    test_signal = {
        'symbol': 'DOGE/USDT',
        'direction': 'LONG',
        'timeframe': '1h',
        'strategy': 'supertrend_adx',
        'strategy_name': 'SuperTrend ADX',
        'confidence': 92.0,
        'price': 0.12345,
        'profit_target': 0.15000,
        'stop_loss': 0.11000,
        'atr': 0.005,
        'win_probability': 90.5
    }
    
    logger.info("Sending low price crypto signal notification...")
    result = telegram.send_signal_notification(test_signal)
    
    if result and 'error' not in result:
        logger.info("✅ Low price crypto signal notification sent successfully!")
        return True
    else:
        error = result.get('error', 'Unknown error')
        logger.error(f"❌ Failed to send low price crypto signal notification: {error}")
        return False

def main():
    """Main function"""
    logger.info("Starting Telegram test script")
    
    # Test basic Telegram integration
    basic_test_result = test_telegram_integration()
    
    if basic_test_result:
        # If basic test passes, test signal notification
        signal_test_result = test_signal_notification()
        low_price_test_result = test_low_price_signal()
        
        if signal_test_result and low_price_test_result:
            logger.info("✅ All Telegram tests passed successfully!")
            return 0
        else:
            logger.error("❌ Some signal notification tests failed")
            return 1
    else:
        logger.error("❌ Basic Telegram integration test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
