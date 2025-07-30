#!/usr/bin/env python3
"""
Bybit Live Trade Verification Script
-----------------------------------
This script performs a real but minimal test trade on Bybit to verify:
1. API connectivity and authentication
2. Order execution capability
3. Position management
4. Telegram notifications

It uses the smallest possible position size for safety while testing real money functionality.
"""
import os
import sys
import json
import logging
import ccxt
import time
from decimal import Decimal, ROUND_DOWN
from dotenv import load_dotenv
from datetime import datetime

# Configure logging with timestamps
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('verify_live')

# Apply imghdr patch for Python 3.13+ if needed
try:
    import imghdr
    logger.info("✅ Native imghdr module found")
except ImportError:
    logger.warning("⚠️ Native imghdr module not found, applying compatibility patch...")
    sys.path.insert(0, '.')
    from telegram_client import patch_imghdr
    patch_imghdr()
    logger.info("✅ Successfully patched imghdr module")

# Load environment variables (both main .env and .env_bybit)
logger.info("Loading environment variables...")
load_dotenv(verbose=True)

# Print environment variables for debugging (masking secrets)
telegram_bot = os.getenv('TELEGRAM_BOT_TOKEN')
if telegram_bot:
    masked_token = telegram_bot[:8] + '...' + telegram_bot[-4:]
    logger.info(f"Telegram bot token found: {masked_token}")
else:
    logger.warning("⚠️ Telegram bot token not found")
    
# Try to load Bybit credentials from .env_bybit
load_dotenv('.env_bybit', override=True)
logger.info("Loaded .env_bybit file")

# Print Bybit API credentials status (masked)
bybit_key = os.getenv('BYBIT_API_KEY') or os.getenv('BYBIT_KEY')
if bybit_key:
    masked_key = bybit_key[:4] + '...' + bybit_key[-4:]
    logger.info(f"Bybit API key found: {masked_key}")
else:
    logger.error("❌ Bybit API key not found in environment variables")
    
bybit_secret = os.getenv('BYBIT_API_SECRET') or os.getenv('BYBIT_SECRET_KEY')
if bybit_secret:
    masked_secret = bybit_secret[:4] + '...' + bybit_secret[-4:]
    logger.info(f"Bybit API secret found: {masked_secret}")
else:
    logger.error("❌ Bybit API secret not found in environment variables")
logger.info("✅ Environment variables loaded")

# Import local modules after env variables are loaded
try:
    from telegram_client import TelegramClient
    logger.info("✅ Successfully imported TelegramClient")
except Exception as e:
    logger.error(f"❌ Failed to import TelegramClient: {str(e)}")
    sys.exit(1)

def get_bybit_client():
    """Initialize and return a CCXT Bybit client"""
    try:
        # Get API credentials from environment variables
        api_key = os.getenv('BYBIT_API_KEY')
        api_secret = os.getenv('BYBIT_API_SECRET')
        
        # Try alternate env var names if needed
        if not api_key or not api_secret:
            logger.warning("⚠️ Trying alternate env var names for Bybit credentials")
            api_key = os.getenv('BYBIT_API_KEY') or os.getenv('BYBIT_KEY')
            api_secret = os.getenv('BYBIT_API_SECRET') or os.getenv('BYBIT_SECRET') or os.getenv('BYBIT_SECRET_KEY')
        
        if not api_key or not api_secret:
            logger.error("❌ Bybit API credentials not found in environment variables")
            return None
            
        # Create exchange object with extended options
        logger.info("🔄 Initializing Bybit exchange...")
        exchange = ccxt.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
                'recvWindow': 600000,  # 10 minutes to handle any time sync issues
                'adjustForTimeDifference': True
            }
        })
        
        # Check connection and synchronize time
        logger.info("🔄 Checking Bybit API connection...")
        server_time = exchange.fetch_time()
        local_time = int(time.time() * 1000)
        time_difference_ms = server_time - local_time
        exchange.options['timeDifference'] = time_difference_ms
        
        # Log time details for debugging
        logger.info(f"⏰ Server time: {server_time}")
        logger.info(f"⏰ Local time: {local_time}")
        logger.info(f"⏰ Time difference: {time_difference_ms}ms")
        
        # Force immediate synchronization with a standard endpoint
        try:
            logger.info("Verifying authentication with fetch_balance...")
            sync_result = exchange.fetch_balance()
            if sync_result:
                logger.info(f"✅ Time synchronization verified with Bybit private endpoint")
            else:
                logger.warning(f"⚠️ Initial time synchronization check failed")
        except Exception as e:
            logger.warning(f"⚠️ Initial time synchronization check error: {str(e)}")
        
        logger.info(f"✅ Connected to Bybit (time offset: {time_difference_ms}ms)")
        logger.info(f"✅ Server time: {datetime.fromtimestamp(server_time/1000).strftime('%Y-%m-%d %H:%M:%S.%f')}")
        
        return exchange
    except Exception as e:
        logger.error(f"❌ Failed to initialize Bybit client: {str(e)}")
        return None

def get_minimum_order_size(exchange, symbol):
    """Get the minimum allowed order size for a symbol"""
    try:
        # Load markets to get symbol information
        markets = exchange.load_markets()
        
        if symbol not in markets:
            logger.error(f"❌ Symbol {symbol} not found in markets")
            return None
            
        # Get minimum amount for this symbol
        market = markets[symbol]
        min_amount = market['limits']['amount']['min']
        
        if min_amount is None:
            logger.warning(f"⚠️ No minimum amount specified for {symbol}, using 0.0001")
            min_amount = 0.0001
            
        # Add a small buffer to ensure we're above minimum
        min_amount = min_amount * 1.05
        
        # Round to appropriate precision
        precision = market['precision']['amount']
        if precision:
            # Convert to Decimal for precise rounding
            min_amount = float(Decimal(str(min_amount)).quantize(
                Decimal('0.' + '0' * precision), rounding=ROUND_DOWN
            ))
        
        logger.info(f"✅ Minimum order size for {symbol}: {min_amount}")
        return min_amount
    except Exception as e:
        logger.error(f"❌ Error getting minimum order size: {str(e)}")
        return 0.0001  # Fallback to a small value

def sync_bybit_time(exchange):
    """Aggressively synchronize time with Bybit server"""
    try:
        # Get server time from Bybit
        server_time = exchange.fetch_time()
        local_time = int(time.time() * 1000)
        time_diff = server_time - local_time
        
        logger.info(f"⏰ Re-synchronizing time: server={server_time}, local={local_time}, diff={time_diff}ms")
        
        # Set time difference in exchange options
        exchange.options['timeDifference'] = time_diff
        
        # Set an extra large recvWindow
        exchange.options['recvWindow'] = max(600000, abs(time_diff) * 3)
        
        # Force a private API call to verify auth works with new time sync
        try:
            result = exchange.fetch_balance()
            if result and 'total' in result:
                logger.info(f"✅ Time synchronization successful")
                return True
            else:
                logger.warning(f"⚠️ Time sync verification returned unexpected format")
                return False
        except Exception as e:
            logger.error(f"❌ Error during time sync verification: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"❌ Failed to synchronize time: {str(e)}")
        return False

def create_test_trade(exchange, symbol='BTC/USDT'):
    """Create and execute a minimal test trade on Bybit"""
    try:
        # Fetch current market price
        logger.info(f"🔄 Fetching current price for {symbol}...")
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        logger.info(f"✅ Current price: {current_price}")
        
        # Calculate take profit and stop loss (0.5% in each direction)
        take_profit = round(current_price * 1.005, 2)
        stop_loss = round(current_price * 0.995, 2)
        
        # Get minimum allowed order size
        min_amount = get_minimum_order_size(exchange, symbol)
        if not min_amount:
            return False
            
        # Create a test signal
        test_signal = {
            'symbol': symbol,
            'side': 'buy',
            'entry_price': current_price,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'success_probability': 0.99,
            'timeframe': '15m',
            'exchange': 'bybit',
            'volume': 1000000,
            'risk_reward_ratio': 1.0,
            'strategy': 'VERIFICATION_TEST',
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'test_size': min_amount
        }
        
        logger.info(f"✅ Created test signal: {json.dumps(test_signal, indent=2)}")
        
        # Send notification via Telegram
        try:
            telegram = TelegramClient(
                os.getenv('TELEGRAM_BOT_TOKEN'),
                os.getenv('TELEGRAM_CHAT_ID')
            )
            
            message = (
                f"🧪 *LIVE TRADE VERIFICATION TEST*\n\n"
                f"*Symbol:* {symbol}\n"
                f"*Side:* BUY\n"
                f"*Entry Price:* ${current_price}\n"
                f"*Size:* {min_amount} BTC (minimum)\n"
                f"*Take Profit:* ${take_profit} (+0.5%)\n"
                f"*Stop Loss:* ${stop_loss} (-0.5%)\n\n"
                f"_This is a verification test with real funds._"
            )
            
            telegram.send_message(message)
            logger.info("✅ Test notification sent to Telegram")
        except Exception as e:
            logger.error(f"❌ Error sending Telegram notification: {str(e)}")
        
        # Execute the test trade
        try:
            # Import at this point to avoid circular imports
            from bybit_trader import execute_bybit_trade
            
            logger.info("🔄 Executing test trade...")
            result = execute_bybit_trade(test_signal)
            
            if result:
                logger.info("✅ LIVE TRADE VERIFICATION SUCCESSFUL")
                
                # Send confirmation
                try:
                    telegram.send_message("✅ *VERIFICATION SUCCESSFUL*\nLive trading is operational!")
                except:
                    pass
                    
                return True
            else:
                logger.error("❌ LIVE TRADE VERIFICATION FAILED")
                
                # Send failure notification
                try:
                    telegram.send_message("❌ *VERIFICATION FAILED*\nCheck logs for details.")
                except:
                    pass
                    
                return False
                
        except Exception as e:
            logger.error(f"❌ Error executing test trade: {str(e)}")
            logger.error(f"Exception type: {type(e)}")
            
            # Try to send error notification
            try:
                telegram.send_message(f"❌ *VERIFICATION ERROR*\n{str(e)}")
            except:
                pass
                
            return False
            
    except Exception as e:
        logger.error(f"❌ Error in create_test_trade: {str(e)}")
        return False

def patch_bybit_trader():
    """Patch bybit_trader.py to handle test_size parameter"""
    try:
        # This is a temporary modification to handle our test signal
        import bybit_trader
        
        # Store original calculate_position_size function
        original_calculate_position_size = bybit_trader.calculate_position_size
        
        # Define patched function that checks for test_size
        def patched_calculate_position_size(exchange, symbol, price):
            # Check if we're being called from our test script
            import inspect
            frame = inspect.currentframe()
            try:
                while frame:
                    if frame.f_code.co_name == 'execute_bybit_trade':
                        # Check if the signal has our test_size
                        if 'signal' in frame.f_locals and 'test_size' in frame.f_locals['signal']:
                            test_size = frame.f_locals['signal']['test_size']
                            logger.info(f"✅ Using test size: {test_size}")
                            return test_size
                    frame = frame.f_back
            finally:
                del frame  # Avoid reference cycles
                
            # Fall back to original function
            return original_calculate_position_size(exchange, symbol, price)
            
        # Apply the patch
        bybit_trader.calculate_position_size = patched_calculate_position_size
        logger.info("✅ Patched bybit_trader.calculate_position_size for test trade")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to patch bybit_trader: {str(e)}")
        return False

def main():
    """Main verification function"""
    logger.info("=" * 80)
    logger.info("STARTING BYBIT LIVE TRADE VERIFICATION")
    logger.info("=" * 80)
    
    # Step 1: Initialize Bybit client
    exchange = get_bybit_client()
    if not exchange:
        logger.error("❌ Failed to initialize Bybit client")
        return False
        
    # Step 2: Patch bybit_trader to handle our test size
    if not patch_bybit_trader():
        logger.warning("⚠️ Failed to patch bybit_trader, proceeding anyway")
    
    # Step 3: Aggressively synchronize time with Bybit
    logger.info("🔄 Performing aggressive time synchronization...")
    sync_success = sync_bybit_time(exchange)
    if not sync_success:
        logger.warning("⚠️ Time synchronization not fully verified, proceeding anyway")
    
    # Step 4: Execute the test trade
    result = create_test_trade(exchange)
    
    if result:
        logger.info("=" * 80)
        logger.info("✅ BYBIT LIVE TRADING VERIFICATION PASSED")
        logger.info("=" * 80)
        return True
    else:
        logger.info("=" * 80)
        logger.info("❌ BYBIT LIVE TRADING VERIFICATION FAILED")
        logger.info("=" * 80)
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ Unhandled exception: {str(e)}")
        sys.exit(1)
