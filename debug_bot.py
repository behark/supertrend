#!/usr/bin/env python3
"""
Debug script to identify NoneType has no len() error in Crypto Alert Bot
"""
import os
import sys
import logging
import traceback
from dotenv import load_dotenv
import ccxt

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more verbose logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("debug_script")

# Apply imghdr patch for Python 3.13+
try:
    import imghdr
    logger.info("Native imghdr module found")
except ImportError:
    logger.warning("Native imghdr module not found, applying compatibility patch...")
    sys.path.insert(0, '.')
    import compat_imghdr
    sys.modules['imghdr'] = compat_imghdr
    logger.info("Successfully patched imghdr module")

# Load environment variables
load_dotenv()

def get_exchange_instance(exchange_id):
    """Initialize and return exchange instance."""
    try:
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'apiKey': os.getenv(f'{exchange_id.upper()}_API_KEY', ''),
            'secret': os.getenv(f'{exchange_id.upper()}_SECRET_KEY', ''),
            'enableRateLimit': True,
        })
        return exchange
    except Exception as e:
        logger.error(f"Error initializing exchange {exchange_id}: {str(e)}")
        return None

def check_exchange_markets(exchange_id):
    """Test fetching markets from the exchange."""
    logger.info(f"Testing exchange: {exchange_id}")
    
    exchange = get_exchange_instance(exchange_id)
    if not exchange:
        logger.error(f"Failed to initialize {exchange_id} exchange")
        return False
    
    try:
        logger.info(f"Attempting to load markets for {exchange_id}...")
        exchange.load_markets()
        logger.info(f"Successfully loaded markets for {exchange_id}")
        
        # Try to get USDT symbols
        usdt_symbols = [s for s in exchange.symbols if '/USDT' in s]
        logger.info(f"Found {len(usdt_symbols)} USDT symbols on {exchange_id}")
        if not usdt_symbols:
            logger.warning(f"No USDT trading pairs found on {exchange_id}")
            return False
            
        # Try to fetch OHLCV for a common symbol as a test
        test_symbol = 'BTC/USDT' if 'BTC/USDT' in usdt_symbols else usdt_symbols[0]
        logger.info(f"Testing OHLCV fetch for {test_symbol} on {exchange_id}...")
        
        ohlcv = exchange.fetch_ohlcv(test_symbol, '1h')
        if ohlcv is None:
            logger.error(f"OHLCV fetch returned None for {test_symbol}")
            return False
            
        logger.info(f"OHLCV fetch successful. Got {len(ohlcv)} candles for {test_symbol}")
        return True
        
    except Exception as e:
        logger.error(f"Error checking {exchange_id} exchange: {str(e)}")
        logger.debug(traceback.format_exc())
        return False

def check_bot_dependencies():
    """Test bot configurations and dependencies."""
    try:
        # Check config.py imports
        logger.info("Checking config imports...")
        from config import EXCHANGES, SYMBOLS_TO_SCAN, TIMEFRAMES
        
        logger.info(f"Configured exchanges: {EXCHANGES}")
        logger.info(f"Symbols to scan: {SYMBOLS_TO_SCAN}")
        logger.info(f"Timeframes: {TIMEFRAMES}")
        
        if not SYMBOLS_TO_SCAN:
            logger.info("Empty SYMBOLS_TO_SCAN list - bot will scan all USDT pairs")
            
        # Check Telegram credentials
        logger.info("Checking Telegram credentials...")
        telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not telegram_bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not found in .env")
        else:
            logger.info("TELEGRAM_BOT_TOKEN found")
            
        if not telegram_chat_id:
            logger.warning("TELEGRAM_CHAT_ID not found in .env")
        else:
            logger.info("TELEGRAM_CHAT_ID found")
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False
    except Exception as e:
        logger.error(f"Error checking dependencies: {e}")
        logger.debug(traceback.format_exc())
        return False
        
    return True

def main():
    """Main debug function."""
    logger.info("Starting debug process...")
    
    # Check bot dependencies and config
    logger.info("Checking bot dependencies...")
    if not check_bot_dependencies():
        logger.error("Failed to load bot dependencies")
        return
        
    # Check exchanges
    from config import EXCHANGES
    
    for exchange_id in EXCHANGES:
        logger.info(f"Testing exchange: {exchange_id}")
        if check_exchange_markets(exchange_id):
            logger.info(f"✅ Exchange {exchange_id} passed all tests")
        else:
            logger.error(f"❌ Exchange {exchange_id} failed tests")
    
    logger.info("Debug process completed")

if __name__ == "__main__":
    main()
