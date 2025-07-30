#!/usr/bin/env python3
"""
Emergency Test Trade Script
---------------------------
This script forces a trade by directly calling the execute_bybit_trade function
with a manually crafted signal that bypasses all filters.
"""
import os
import sys
import logging
from dotenv import load_dotenv
from datetime import datetime

# Apply imghdr patch for Python 3.13+ (must happen before other imports)
try:
    import imghdr
    print("✅ Native imghdr module found")
except ImportError:
    print("⚠️ Native imghdr module not found, applying compatibility patch...")
    # Create minimal imghdr shim
    sys.modules['imghdr'] = type('imghdr', (), {'what': lambda f, h: None})
    print("✅ Successfully patched imghdr module")

# Load environment variables
load_dotenv()
load_dotenv('.env_bybit')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import required modules
try:
    from bybit_trader import execute_bybit_trade
    from telegram_client import TelegramClient
    logger.info("✅ Successfully imported modules")
except Exception as e:
    logger.error(f"❌ Error importing modules: {str(e)}")
    sys.exit(1)

def main():
    """Force an emergency test trade that bypasses all normal filters"""
    logger.info("🚨 CREATING EMERGENCY TEST TRADE 🚨")
    
    # Create a guaranteed high-probability signal
    test_signal = {
        'symbol': 'BTC/USDT',
        'side': 'buy',
        'entry_price': 0.5,  # Mock price for testing
        'take_profit': 0.525,  # 5% profit target
        'stop_loss': 0.49,    # 2% stop loss
        'success_probability': 0.99,  # 99% probability to bypass all filters
        'timeframe': '1h',
        'exchange': 'binance',
        'volume': 5000000,    # High volume
        'risk_reward_ratio': 2.5,  # Good risk/reward
        # Add any other required fields
        'strategy': 'EMERGENCY_TEST',
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # Send notification about test
    try:
        telegram = TelegramClient(
            os.getenv('TELEGRAM_BOT_TOKEN'),
            os.getenv('TELEGRAM_CHAT_ID')
        )
        telegram.send_message("🚨 *EMERGENCY TEST TRADE INCOMING*\nThis is a test of the trading system.")
        logger.info("✅ Test notification sent")
    except Exception as e:
        logger.error(f"❌ Error sending notification: {str(e)}")
    
    # Force the trade
    try:
        result = execute_bybit_trade(test_signal)
        if result:
            logger.info("✅ EMERGENCY TEST TRADE EXECUTED SUCCESSFULLY")
        else:
            logger.error("❌ EMERGENCY TEST TRADE FAILED")
    except Exception as e:
        logger.error(f"❌ Error executing test trade: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        logger.error(f"Exception args: {e.args}")
        
        # Try to send notification about failure
        try:
            telegram.send_message(f"❌ *TEST TRADE ERROR*\n{str(e)}")
        except:
            pass
        return False
        
    return True

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ TEST COMPLETED SUCCESSFULLY")
            sys.exit(0)
        else:
            print("\n❌ TEST FAILED")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unhandled exception: {str(e)}")
        sys.exit(1)
