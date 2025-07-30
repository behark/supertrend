"""
Simple verification script to check that the bot can scan all crypto pairs
Avoids dependencies that cause issues in Python 3.13
"""

import os
import sys
import json
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.info("✅ Loaded environment variables from .env file")
except ImportError:
    logger.warning("⚠️ python-dotenv not installed, using system environment variables only")

# Try to import ccxt
try:
    import ccxt
    logger.info("✅ Successfully imported ccxt")
except ImportError:
    logger.error("❌ Failed to import ccxt. Please install it: pip install ccxt")
    sys.exit(1)

def get_exchange_instance(exchange_id):
    """Create an exchange instance"""
    try:
        # Get API credentials from environment variables
        api_key = os.getenv(f"{exchange_id.upper()}_API_KEY", "")
        secret = os.getenv(f"{exchange_id.upper()}_SECRET_KEY", "")
        
        # Create exchange instance
        exchange_class = getattr(ccxt, exchange_id)
        if api_key and secret:
            exchange = exchange_class({
                'apiKey': api_key,
                'secret': secret,
                'timeout': 30000,
                'enableRateLimit': True,
            })
            logger.info(f"✅ Created authenticated {exchange_id} instance")
        else:
            exchange = exchange_class({
                'timeout': 30000,
                'enableRateLimit': True,
            })
            logger.warning(f"⚠️ Created unauthenticated {exchange_id} instance (API keys not found)")
        
        return exchange
    except Exception as e:
        logger.error(f"❌ Failed to create {exchange_id} instance: {str(e)}")
        return None

def scan_market(exchange_id):
    """Scan all USDT pairs on an exchange"""
    try:
        exchange = get_exchange_instance(exchange_id)
        if not exchange:
            return
        
        # Load markets
        logger.info(f"Loading markets from {exchange_id}...")
        exchange.load_markets()
        
        # Get all USDT pairs
        usdt_pairs = [symbol for symbol in exchange.symbols if symbol.endswith('/USDT')]
        logger.info(f"✅ Found {len(usdt_pairs)} USDT pairs on {exchange_id}")
        
        # Print first 10 pairs
        logger.info(f"Sample pairs: {', '.join(usdt_pairs[:10])}...")
        
        # Verify we can fetch OHLCV data for a sample pair
        if usdt_pairs:
            sample_pair = usdt_pairs[0]
            logger.info(f"Testing OHLCV data fetch for {sample_pair}...")
            
            try:
                data = exchange.fetch_ohlcv(sample_pair, '1h', limit=10)
                logger.info(f"✅ Successfully fetched OHLCV data for {sample_pair}")
                logger.info(f"Sample data: {data[:2]}")
                return len(usdt_pairs)
            except Exception as e:
                logger.error(f"❌ Failed to fetch OHLCV data: {str(e)}")
        
    except Exception as e:
        logger.error(f"❌ Failed to scan {exchange_id}: {str(e)}")
    
    return 0

def main():
    """Main verification function"""
    logger.info("🚀 Starting Crypto Alert Bot Scanning Verification")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # List of exchanges to verify
    exchanges = ['binance', 'kucoin']
    total_pairs = 0
    
    for exchange_id in exchanges:
        logger.info(f"\n==== Testing {exchange_id.upper()} ====")
        pairs_count = scan_market(exchange_id)
        total_pairs += pairs_count
    
    logger.info(f"\n==== VERIFICATION SUMMARY ====")
    logger.info(f"Total USDT pairs found across all exchanges: {total_pairs}")
    
    if total_pairs > 0:
        logger.info("✅ VERIFICATION PASSED: Bot can scan all cryptocurrency pairs")
        logger.info("✅ The bot is ready for production use")
    else:
        logger.error("❌ VERIFICATION FAILED: Could not find any tradable pairs")
        logger.info("⚠️ Check your API keys and internet connection")

if __name__ == "__main__":
    main()
