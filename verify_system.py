#!/usr/bin/env python3
"""
Verification Script for Crypto Alert Bot with BYBIT Trading
----------------------------------------------------------
This script forces a test signal and trade to verify the system is working correctly.
"""
import os
import sys
import logging
from datetime import datetime
import traceback
from dotenv import load_dotenv

# Load environment variables from .env files
load_dotenv()
load_dotenv('.env_bybit')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Import local modules with error handling
try:
    from telegram_client import TelegramClient
    from bybit_trader import get_bybit_exchange, execute_bybit_trade
    logger.info("✅ Successfully imported local modules")
except Exception as e:
    logger.error(f"❌ Error importing modules: {str(e)}")
    logger.error(traceback.format_exc())
    sys.exit(1)

def main():
    """Run verification test"""
    # 1. Initialize Telegram client
    try:
        telegram = TelegramClient(
            os.getenv('TELEGRAM_BOT_TOKEN'),
            os.getenv('TELEGRAM_CHAT_ID')
        )
        logger.info("✅ Telegram client initialized")
    except Exception as e:
        logger.error(f"❌ Error initializing Telegram: {str(e)}")
        return False
        
    # 2. Send verification start message
    try:
        telegram.send_message("🔍 *SYSTEM VERIFICATION STARTED*\nTesting signal and trade flow...")
        logger.info("✅ Sent start notification")
    except Exception as e:
        logger.error(f"❌ Error sending Telegram message: {str(e)}")
        return False
        
    # 3. Initialize Bybit exchange
    try:
        exchange = get_bybit_exchange()
        logger.info("✅ BYBIT exchange initialized")
    except Exception as e:
        logger.error(f"❌ Error initializing BYBIT exchange: {str(e)}")
        telegram.send_message(f"⚠️ *VERIFICATION ERROR*: BYBIT initialization failed: {str(e)}")
        return False
        
    # 4. Create a test signal
    test_symbol = "BTC/USDT"
    test_probability = 0.95  # 95% probability
    
    # 5. Execute test trade
    try:
        # Create a properly formatted signal dictionary
        current_price = 0.5  # Mock price for test
        test_signal = {
            'symbol': test_symbol,
            'side': 'buy',
            'entry_price': current_price,
            'take_profit': round(current_price * 1.05, 8),  # 5% profit target
            'stop_loss': round(current_price * 0.98, 8),    # 2% stop loss
            'success_probability': test_probability,
            'timeframe': '1h'
        }
        
        # Execute the trade with our signal
        result = execute_bybit_trade(test_signal)
        
        if result:
            logger.info(f"✅ Test trade executed for {test_symbol}")
        else:
            logger.error("❌ Trade execution returned False")
            telegram.send_message("⚠️ *VERIFICATION ERROR*: Trade execution returned False")
            return False
    except Exception as e:
        logger.error(f"❌ Error executing test trade: {str(e)}")
        telegram.send_message(f"⚠️ *VERIFICATION ERROR*: Trade execution failed: {str(e)}")
        return False
        
    # 6. Send success message
    success_msg = (
        "✅ *SYSTEM VERIFICATION SUCCESSFUL*\n\n"
        f"Verified at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Test Symbol: {test_symbol}\n"
        f"Signal Type: BUY\n"
        f"Probability: {test_probability*100}%\n\n"
        "All systems operational. Bot is monitoring for real trading opportunities."
    )
    telegram.send_message(success_msg)
    logger.info("✅ Verification completed successfully")
    return True

if __name__ == "__main__":
    try:
        logger.info("🚀 Starting system verification")
        result = main()
        if result:
            logger.info("✅ Verification PASSED")
            sys.exit(0)
        else:
            logger.info("❌ Verification FAILED")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
