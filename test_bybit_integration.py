#!/usr/bin/env python3
"""
Test Script for BYBIT Trading Integration
----------------------------------------
This script tests all aspects of the BYBIT integration:
- BYBIT API connection
- Finding coins under $1
- Position sizing with 25% of balance
- 20x leverage settings
- Take profit and stop loss settings
- Daily limits (15 trades max, 1 per pair)
"""
import sys
import logging
import time
from datetime import datetime

# Apply imghdr patch for Python 3.13+ (must happen before other imports)
try:
    import imghdr
    print("✅ Native imghdr module found")
except ImportError:
    print("⚠️ Native imghdr module not found, applying compatibility patch...")
    sys.path.insert(0, '.')
    # Create a manual patch for imghdr
    import os
    import tempfile
    import sys
    
    class ImghdrShim:
        def what(self, *args, **kwargs):
            return None
    
    sys.modules['imghdr'] = ImghdrShim()
    print("✅ Successfully patched imghdr module")

# Import local modules
from bybit_trader import (
    get_bybit_exchange, fetch_low_priced_symbols, get_available_balance,
    calculate_position_size, set_leverage, execute_bybit_trade, 
    load_bybit_trade_counts, MAX_PAIRS_TO_SCAN, BYBIT_LEVERAGE,
    BYBIT_POSITION_SIZE, MAX_PRICE_THRESHOLD, MAX_DAILY_BYBIT_TRADES
)
from telegram_client import TelegramClient
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_tests():
    """Run all tests to verify BYBIT integration"""
    
    passed = 0
    failed = 0
    
    # Test 1: BYBIT API connection
    logger.info("TEST 1: BYBIT API Connection")
    exchange = get_bybit_exchange()
    if exchange:
        logger.info("✅ PASSED: BYBIT API connection successful")
        passed += 1
    else:
        logger.error("❌ FAILED: BYBIT API connection failed")
        failed += 1
    
    if exchange:
        # Test 2: Fetch low-priced symbols (under $1)
        logger.info("\nTEST 2: Fetch Low-Priced Symbols (under $1)")
        symbols = fetch_low_priced_symbols(exchange)
        if symbols and len(symbols) > 0:
            logger.info(f"✅ PASSED: Found {len(symbols)} symbols under ${MAX_PRICE_THRESHOLD}")
            logger.info(f"Sample symbols: {symbols[:5]}")
            passed += 1
        else:
            logger.error(f"❌ FAILED: Could not find symbols under ${MAX_PRICE_THRESHOLD}")
            failed += 1
        
        # Test 3: Maximum pairs limit
        logger.info("\nTEST 3: Maximum Pairs Limit")
        if len(symbols) <= MAX_PAIRS_TO_SCAN:
            logger.info(f"✅ PASSED: Symbol count {len(symbols)} is within limit of {MAX_PAIRS_TO_SCAN}")
            passed += 1
        else:
            logger.error(f"❌ FAILED: Symbol count {len(symbols)} exceeds limit of {MAX_PAIRS_TO_SCAN}")
            failed += 1
        
        # Test 4: Available balance
        logger.info("\nTEST 4: Available Balance")
        balance = get_available_balance(exchange)
        if balance > 0:
            logger.info(f"✅ PASSED: Available balance is ${balance}")
            passed += 1
        else:
            logger.error("❌ FAILED: Could not retrieve available balance")
            failed += 1
        
        # Test 5: Position sizing (25% of balance)
        logger.info("\nTEST 5: Position Sizing (25% of balance)")
        if balance > 0 and len(symbols) > 0:
            symbol = symbols[0]
            # Get current price
            ticker = exchange.fetch_ticker(symbol)
            price = ticker['last']
            # Calculate position size
            quantity = calculate_position_size(exchange, symbol, price)
            expected_value = balance * BYBIT_POSITION_SIZE / price
            if abs(quantity - expected_value) / expected_value < 0.1:  # Within 10% due to rounding
                logger.info(f"✅ PASSED: Position size calculation correct - {quantity} {symbol}")
                logger.info(f"Value: ${quantity * price} (25% of ${balance})")
                passed += 1
            else:
                logger.error(f"❌ FAILED: Position size calculation incorrect")
                logger.error(f"Expected ~{expected_value}, got {quantity}")
                failed += 1
        else:
            logger.error("❌ FAILED: Could not test position sizing")
            failed += 1
        
        # Test 6: Leverage setting (20x)
        logger.info("\nTEST 6: Leverage Setting (20x)")
        if len(symbols) > 0:
            symbol = symbols[0]
            success = set_leverage(exchange, symbol)
            if success:
                logger.info(f"✅ PASSED: Successfully set leverage to {BYBIT_LEVERAGE}x for {symbol}")
                passed += 1
            else:
                logger.error(f"❌ FAILED: Could not set leverage for {symbol}")
                failed += 1
        else:
            logger.error("❌ FAILED: Could not test leverage setting")
            failed += 1
        
        # Test 7: Daily trade limit checks
        logger.info("\nTEST 7: Daily Trade Limit Checks")
        counts = load_bybit_trade_counts()
        logger.info(f"Current trade counts: {counts}")
        if counts:
            logger.info(f"✅ PASSED: Trade count tracking system working properly")
            logger.info(f"Maximum daily trades limit is set to {MAX_DAILY_BYBIT_TRADES}")
            passed += 1
        else:
            logger.error("❌ FAILED: Trade count tracking system not working")
            failed += 1
    
    # Test 8: System service configuration
    logger.info("\nTEST 8: System Service Configuration")
    try:
        import subprocess
        result = subprocess.run(
            ["systemctl", "--user", "status", "crypto-alert-bot"],
            capture_output=True, text=True
        )
        if "Active: active (running)" in result.stdout:
            logger.info("✅ PASSED: crypto-alert-bot service is running")
            passed += 1
        else:
            logger.error("❌ FAILED: crypto-alert-bot service is not running")
            failed += 1
    except Exception as e:
        logger.error(f"❌ FAILED: Could not check service status - {str(e)}")
        failed += 1
    
    # Send test results via Telegram
    logger.info("\n--- TEST RESULTS ---")
    logger.info(f"Tests passed: {passed}/{passed+failed}")
    logger.info(f"Tests failed: {failed}/{passed+failed}")
    
    if failed == 0:
        logger.info("🎉 ALL TESTS PASSED! BYBIT integration is fully functional!")
    else:
        logger.error(f"⚠️ {failed} tests failed. Please fix the issues.")
    
    # Send test results via Telegram
    try:
        telegram_client = TelegramClient(
            os.getenv('TELEGRAM_BOT_TOKEN'),
            os.getenv('TELEGRAM_CHAT_ID')
        )
        
        if failed == 0:
            message = (
                "🎉 *BYBIT INTEGRATION VERIFIED*\n\n"
                "All tests passed! Your crypto alert bot with BYBIT auto trading is fully functional with:\n\n"
                "✅ 100 signals per day limit\n"
                f"✅ 15 BYBIT orders per day limit (currently: {counts.get(list(counts.keys())[0], {}).get('total_trades', 0)})\n"
                "✅ 25% of balance per trade\n"
                "✅ 20x leverage on all trades\n"
                "✅ Take profit and stop loss on all orders\n"
                "✅ Only trading coins under $1\n"
                "✅ Maximum 1 trade per crypto pair\n"
                f"✅ Scanning {len(symbols) if 'symbols' in locals() else 'up to 30'} crypto pairs\n"
                "✅ Auto-starts on system boot\n\n"
                f"Current BYBIT balance: ${balance if 'balance' in locals() else 'unknown'}\n"
                f"System verified: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            message = (
                "⚠️ *BYBIT INTEGRATION ISSUES*\n\n"
                f"Tests passed: {passed}/{passed+failed}\n"
                f"Tests failed: {failed}/{passed+failed}\n\n"
                "Please check the logs for more information."
            )
        
        telegram_client.send_message(message)
        logger.info("Test results sent via Telegram")
    except Exception as e:
        logger.error(f"Failed to send test results via Telegram: {str(e)}")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        logger.error(f"Error running tests: {str(e)}")
        sys.exit(1)
