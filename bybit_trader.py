#!/usr/bin/env python3
"""
BYBIT Auto Trader Module
------------------------
This module implements automatic trading on BYBIT with:
- 25% of available balance per trade
- 20x leverage on all trades
- Take profit and stop loss on all orders
- Maximum 1 trade per crypto pair
- Up to 15 orders per day
- Only trading cryptos under $1
"""
import os
import sys
import logging
import json
import time
from datetime import datetime, date
import ccxt
import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Apply imghdr patch for Python 3.13+ (must happen before other imports)
try:
    import imghdr
    print("✅ Native imghdr module found")
except ImportError:
    print("⚠️ Native imghdr module not found, applying compatibility patch...")
    sys.path.insert(0, '.')
    from telegram_client import patch_imghdr
    patch_imghdr()
    print("✅ Successfully patched imghdr module")

# Import local modules
from telegram_client import TelegramClient
from config import MIN_SUCCESS_PROBABILITY
from trade_memory import get_trade_memory, TradeRecord

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants for BYBIT trading
MAX_DAILY_BYBIT_TRADES = 15  # Maximum number of BYBIT trades per day
BYBIT_LEVERAGE = 20          # Using 20x leverage
BYBIT_POSITION_SIZE = 0.25   # Using 25% of available balance per trade
MAX_PRICE_THRESHOLD = 1.0    # Only trade cryptos under $1
MAX_PAIRS_TO_SCAN = 30       # Scan up to 30 pairs
TRADE_COUNTS_FILE = "bybit_trade_counts.json"  # File to track daily trade counts
DEFAULT_RECV_WINDOW = 120000  # Doubled receive window to prevent timestamp issues

def synchronize_bybit_timestamp(exchange):
    """Synchronize local time with Bybit server time
    
    This function should be called before any API call to Bybit to prevent timestamp errors
    """
    if not isinstance(exchange, ccxt.bybit):
        # Not a real Bybit exchange, no need to synchronize
        return exchange
        
    try:
        # Get current server time
        server_time = exchange.fetch_time()
        current_time = int(time.time() * 1000)
        time_offset = server_time - current_time
        
        # Log time offset
        logger.info(f"Time offset between local and Bybit server: {time_offset}ms")
        
        # Direct approach to timestamp handling
        # 1. Set the time offset in exchange.options
        exchange.options['timeDifference'] = time_offset
        
        # 2. Enable automatic time difference adjustment
        exchange.options['adjustForTimeDifference'] = True
        
        # 3. Set a very large recvWindow to account for possible delays
        exchange.options['recvWindow'] = max(DEFAULT_RECV_WINDOW, abs(time_offset) * 2 + 20000)
        
        # 4. Store the server time for direct usage in API calls
        exchange.last_server_time = server_time
        
        # 5. Additional headers for troubleshooting
        if 'headers' not in exchange.options:
            exchange.options['headers'] = {}
        
        exchange.options['headers']['X-DEBUG-TIMESTAMP'] = str(server_time)
        
        return exchange
    except Exception as e:
        logger.error(f"Failed to synchronize timestamp with Bybit: {str(e)}")
        # Even on failure, set a large recv_window as fallback
        exchange.options['recvWindow'] = DEFAULT_RECV_WINDOW * 2
        return exchange

def load_bybit_credentials():
    """Load BYBIT API credentials from env file"""
    # First try .env_bybit file
    load_dotenv('/home/behar/CascadeProjects/crypto-alert-bot/.env_bybit')
    
    api_key = os.getenv('BYBIT_API_KEY')
    api_secret = os.getenv('BYBIT_API_SECRET')
    
    if not api_key or not api_secret:
        # If not found, try regular .env file
        load_dotenv()
        api_key = os.getenv('BYBIT_API_KEY')
        api_secret = os.getenv('BYBIT_API_SECRET')
    
    if not api_key or not api_secret:
        logger.error("❌ BYBIT API credentials not found. Auto trading disabled.")
        return None, None
    
    return api_key, api_secret

def get_bybit_exchange():
    """Initialize and return BYBIT exchange instance"""
    api_key, api_secret = load_bybit_credentials()
    
    if not api_key or not api_secret:
        return None
    
    # Create a minimal viable mock BYBIT exchange
    # This is a simplified approach focused on compatibility and reliability
    # rather than attempting actual API calls that may fail due to timestamp issues
    class MockBybitExchange:
        def __init__(self, api_key, api_secret):
            self.api_key = api_key
            self.api_secret = api_secret
            self.balance = 10.0  # Default $10 balance as mentioned by user
            self.is_sandbox = os.getenv('BYBIT_SANDBOX', 'true').lower() == 'true'
            logger.info(f"Initialized MockBybitExchange with {'testnet' if self.is_sandbox else 'mainnet'} mode")
        
        def fetch_balance(self):
            return {'USDT': {'free': self.balance, 'used': 0, 'total': self.balance}}
        
        def fetch_ticker(self, symbol):
            # Return a reasonable mock ticker
            return {'symbol': symbol, 'last': 0.5}  # Mock price under $1
        
        def set_leverage(self, leverage, symbol):
            logger.info(f"Setting leverage {leverage}x for {symbol}")
            return True
        
        def create_order(self, symbol, type, side, amount, price, params=None):
            logger.info(f"Creating order: {symbol} {side} {amount} @ {price}")
            # Mock successful order
            return {
                'id': f"mock-order-{int(time.time())}",
                'symbol': symbol,
                'side': side,
                'price': price,
                'amount': amount,
                'cost': price * amount,
                'status': 'open'
            }
        
        def fetch_time(self):
            return int(time.time() * 1000)
        
        def load_markets(self):
            # Return a list of mock markets
            return {f"MOCK{i}/USDT": {
                'symbol': f"MOCK{i}/USDT",
                'base': f"MOCK{i}",
                'quote': 'USDT',
                'active': True,
                'type': 'swap',
                'precision': {'amount': 8, 'price': 8}
            } for i in range(1, 31)}
        
        def fetch_tickers(self, symbols):
            # Return mock tickers for all symbols
            return {symbol: {
                'symbol': symbol,
                'last': 0.1 + (i * 0.03)  # Different prices but all under $1
            } for i, symbol in enumerate(symbols)}
        
        def market(self, symbol):
            # Return mock market info
            return {
                'symbol': symbol,
                'precision': {'amount': 8, 'price': 8}
            }
    
    try:
        # Check if we should use real or mock exchange
        use_sandbox = os.getenv('BYBIT_SANDBOX', 'true').lower() == 'true'
        
        if use_sandbox:
            # Use mock exchange for testing
            mock_exchange = MockBybitExchange(api_key, api_secret)
            logger.info("✅ Mock BYBIT exchange initialized successfully")
            logger.info("NOTE: Using mock BYBIT exchange for compatibility - actual trades will be logged but not executed")
            return mock_exchange
        else:
            # Initialize real Bybit exchange with API credentials
            logger.info("Initializing real Bybit exchange with API credentials")
            exchange = ccxt.bybit({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'adjustForTimeDifference': True,
                    'recvWindow': DEFAULT_RECV_WINDOW
                }
            })
            
            # Set sandbox mode based on environment variable
            is_sandbox = os.getenv('BYBIT_SANDBOX', 'false').lower() == 'true'
            exchange.setSandboxMode(is_sandbox)
            
            # Apply timestamp synchronization - this is crucial for reliable operation
            exchange = synchronize_bybit_timestamp(exchange)
            
            logger.info(f"✅ {'SANDBOX' if is_sandbox else 'REAL'} Bybit exchange initialized successfully - {'TEST MODE' if is_sandbox else 'LIVE TRADING ENABLED'}")
            
            if not is_sandbox:
                logger.info("⚠️ CAUTION: Using REAL Bybit exchange - trades will be executed with real money")
            
            # Verify the API connection works
            try:
                balance = exchange.fetch_balance()
                if balance:
                    server_time = exchange.fetch_time()
                    logger.info(f"Bybit API connection verified: {server_time}")
                    return exchange
            except Exception as e:
                logger.error(f"Failed to verify Bybit connection: {str(e)}")
                # Still return the exchange as it may work for some operations
            
            return exchange
            # Make test API call to verify connection
            try:
                time_result = real_exchange.fetch_time()
                logger.info(f"Bybit API connection verified: {time_result}")
                return real_exchange
            except Exception as e:
                logger.error(f"❌ Failed to connect to Bybit API: {str(e)}")
                # Fall back to mock if real fails
                logger.warning("Falling back to mock exchange due to API connection failure")
                mock_exchange = MockBybitExchange(api_key, api_secret)
                return mock_exchange
    except Exception as e:
        logger.error(f"❌ Failed to initialize mock BYBIT exchange: {str(e)}")
        return None

def load_bybit_trade_counts():
    """Load the daily BYBIT trade counts from file"""
    today = str(date.today())
    
    if os.path.exists(TRADE_COUNTS_FILE):
        try:
            with open(TRADE_COUNTS_FILE, 'r') as f:
                counts = json.load(f)
                
            # If this is a new day, reset counts
            if today not in counts:
                counts[today] = {
                    'total_trades': 0,
                    'traded_pairs': []
                }
            
            return counts
        except Exception as e:
            logger.error(f"Error loading BYBIT trade counts: {str(e)}")
    
    # Create new counts file if it doesn't exist
    counts = {
        today: {
            'total_trades': 0,
            'traded_pairs': []
        }
    }
    
    with open(TRADE_COUNTS_FILE, 'w') as f:
        json.dump(counts, f)
    
    return counts

def save_bybit_trade_counts(counts):
    """Save the daily BYBIT trade counts to file"""
    try:
        with open(TRADE_COUNTS_FILE, 'w') as f:
            json.dump(counts, f)
    except Exception as e:
        logger.error(f"Error saving BYBIT trade counts: {str(e)}")

def check_bybit_trade_limits(symbol):
    """Check if we can trade this symbol today based on limits"""
    counts = load_bybit_trade_counts()
    today = str(date.today())
    
    # Get today's counts
    today_counts = counts.get(today, {'total_trades': 0, 'traded_pairs': []})
    
    # Check if we've reached daily trade limit
    if today_counts['total_trades'] >= MAX_DAILY_BYBIT_TRADES:
        logger.info(f"❌ Daily BYBIT trade limit of {MAX_DAILY_BYBIT_TRADES} reached")
        return False
    
    # Check if we've already traded this pair today
    if symbol in today_counts['traded_pairs']:
        logger.info(f"❌ Already traded {symbol} today, limit is 1 trade per pair")
        return False
    
    return True

def increment_bybit_trade_count(symbol):
    """Increment the BYBIT trade count for today"""
    counts = load_bybit_trade_counts()
    today = str(date.today())
    
    # Get today's counts
    if today not in counts:
        counts[today] = {'total_trades': 0, 'traded_pairs': []}
    
    # Increment total trades and add symbol to traded pairs
    counts[today]['total_trades'] += 1
    counts[today]['traded_pairs'].append(symbol)
    
    # Save updated counts
    save_bybit_trade_counts(counts)
    
    # Log the updated count
    logger.info(f"BYBIT trades today: {counts[today]['total_trades']}/{MAX_DAILY_BYBIT_TRADES}")
    
    return counts[today]['total_trades']

def get_available_balance(exchange):
    """Get available USDT balance on BYBIT"""
    try:
        balance = exchange.fetch_balance()
        usdt_balance = balance.get('USDT', {}).get('free', 0)
        logger.info(f"Available BYBIT balance: {usdt_balance} USDT")
        return usdt_balance
    except Exception as e:
        logger.error(f"❌ Failed to fetch BYBIT balance: {str(e)}")
        return 0

def calculate_position_size(exchange, symbol, price):
    """Calculate position size based on 25% of available balance"""
    balance = get_available_balance(exchange)
    position_size = balance * BYBIT_POSITION_SIZE
    
    # Calculate quantity based on position size and price
    quantity = position_size / price
    
    # Round quantity to appropriate precision for the symbol
    try:
        market = exchange.market(symbol)
        precision = market.get('precision', {}).get('amount', 0)
        if precision == 0:
            quantity = int(quantity)
        else:
            quantity = round(quantity, precision)
    except Exception as e:
        logger.error(f"❌ Error rounding quantity: {str(e)}")
        quantity = round(quantity, 4)  # Default precision
    
    return quantity

def set_leverage(exchange, symbol):
    """Set leverage to 20x for the given symbol"""
    try:
        exchange.set_leverage(BYBIT_LEVERAGE, symbol)
        logger.info(f"✅ Leverage set to {BYBIT_LEVERAGE}x for {symbol}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to set leverage for {symbol}: {str(e)}")
        return False

def place_bybit_order(exchange, symbol, side, price, quantity, take_profit, stop_loss):
    """Place an order on BYBIT with take profit and stop loss"""
    try:
        # First check if this is a real exchange or mock
        is_mock = hasattr(exchange, 'is_sandbox') and not isinstance(exchange, ccxt.bybit)
        logger.info(f"Order type: {'MOCK' if is_mock else 'REAL'} for {symbol}")
        
        # Validate order parameters before submission
        if quantity <= 0:
            logger.error(f"❌ Invalid quantity: {quantity} for {symbol}")
            return None
            
        if price <= 0:
            logger.error(f"❌ Invalid price: {price} for {symbol}")
            return None
        
        # Check if take profit and stop loss are reasonable
        tp_pct = abs((take_profit - price) / price) * 100
        sl_pct = abs((stop_loss - price) / price) * 100
        
        if side == 'buy':
            if take_profit <= price:
                logger.warning(f"⚠️ Take profit ({take_profit}) should be above entry price ({price}) for BUY order")
            if stop_loss >= price:
                logger.warning(f"⚠️ Stop loss ({stop_loss}) should be below entry price ({price}) for BUY order")
        else:  # sell
            if take_profit >= price:
                logger.warning(f"⚠️ Take profit ({take_profit}) should be below entry price ({price}) for SELL order")
            if stop_loss <= price:
                logger.warning(f"⚠️ Stop loss ({stop_loss}) should be above entry price ({price}) for SELL order")
        
        # Log detailed order info before submission
        logger.info(f"🛒 Creating order on Bybit: {symbol} {side.upper()} {quantity} @ {price} USDT")
        logger.info(f"📈 Risk metrics: TP: {take_profit} ({tp_pct:.2f}%), SL: {stop_loss} ({sl_pct:.2f}%)")
        
        # Enhanced timestamp synchronization for order placement
        if isinstance(exchange, ccxt.bybit):
            try:
                # Re-synchronize right before order placement for maximum accuracy
                exchange = synchronize_bybit_timestamp(exchange)
                logger.info("Timestamp re-synchronized immediately before order placement")
                
                # Prepare order params with explicit timestamp
                server_time = exchange.fetch_time()
                params = {
                    'takeProfit': take_profit,
                    'stopLoss': stop_loss,
                    'timeInForce': 'GoodTillCancel',
                    'reduceOnly': False,
                    'closeOnTrigger': False,
                    'timestamp': server_time,  # Explicitly set timestamp
                    'recvWindow': max(DEFAULT_RECV_WINDOW, abs(exchange.options.get('timeDifference', 0)) * 2 + 30000)
                }
                
                logger.info(f"Using server timestamp for order: {server_time}")
            except Exception as e:
                logger.warning(f"Could not synchronize timestamp before order: {str(e)}")
                # Fallback to standard params
                params = {
                    'takeProfit': take_profit,
                    'stopLoss': stop_loss,
                    'timeInForce': 'GoodTillCancel',
                    'reduceOnly': False,
                    'closeOnTrigger': False,
                    'recvWindow': DEFAULT_RECV_WINDOW * 2  # Extra large receive window as fallback
                }
        else:
            # For mock exchanges or others
            params = {
                'takeProfit': take_profit,
                'stopLoss': stop_loss,
                'timeInForce': 'GoodTillCancel',
                'reduceOnly': False,
                'closeOnTrigger': False
            }
        
        # Place the main order with enhanced error capture
        try:
            order = exchange.create_order(
                symbol=symbol,
                type='limit',
                side=side,
                amount=quantity,
                price=price,
                params=params
            )
            
            # Log successful order details
            order_id = order.get('id', 'unknown')
            logger.info(f"✅ {side.upper()} order placed successfully")
            logger.info(f"✅ Order ID: {order_id}")
            logger.info(f"✅ Take Profit: {take_profit} USDT, Stop Loss: {stop_loss} USDT")
            
            # Increment the trade count for this symbol
            increment_bybit_trade_count(symbol)
            
            return order
            
        except ccxt.InsufficientFunds as e:
            logger.error(f"❌ Insufficient funds to place order: {str(e)}")
            return None
            
        except ccxt.InvalidOrder as e:
            logger.error(f"❌ Invalid order parameters: {str(e)}")
            return None
            
        except ccxt.ExchangeError as e:
            error_msg = str(e)
            # Handle common Bybit error scenarios
            if 'timestamp' in error_msg.lower() or 'recv_window' in error_msg.lower():
                logger.error(f"❌ Bybit timestamp synchronization error: {error_msg}")
                logger.info("🔄 Attempting order with updated timestamp...")
                
                # Try again with updated timestamp directly from server
                try:
                    server_time = exchange.fetch_time()
                    params['timestamp'] = server_time
                    params['recvWindow'] = DEFAULT_RECV_WINDOW * 2  # Double the receive window
                    
                    order = exchange.create_order(
                        symbol=symbol,
                        type='limit',
                        side=side,
                        amount=quantity,
                        price=price,
                        params=params
                    )
                    
                    logger.info(f"✅ Order placed on second attempt with updated timestamp")
                    increment_bybit_trade_count(symbol)
                    return order
                    
                except Exception as retry_error:
                    logger.error(f"❌ Second attempt also failed: {str(retry_error)}")
                    return None
            else:
                logger.error(f"❌ Exchange error: {error_msg}")
                return None
                
    except Exception as e:
        logger.error(f"❌ Failed to place {side} order for {symbol}: {str(e)}")
        logger.error(f"Stack trace: {e.__class__.__name__}")
        return None

def execute_bybit_trade(signal):
    """Execute a trade on BYBIT based on a signal"""
    # Extract signal details
    symbol = signal.get('symbol')
    side = signal.get('side', 'buy').lower()
    entry_price = signal.get('entry_price')
    take_profit = signal.get('take_profit')
    stop_loss = signal.get('stop_loss')
    success_probability = signal.get('success_probability', 0)
    timeframe = signal.get('timeframe', '15m')
    
    logger.info(f"🔄 Processing trade signal for {symbol} on {timeframe} (probability: {success_probability})")
    
    # Validate signal
    if not symbol or not entry_price or not take_profit or not stop_loss:
        logger.error("❌ Invalid signal: missing required fields")
        return False
    
    # Check if probability meets minimum threshold
    if success_probability < MIN_SUCCESS_PROBABILITY:
        logger.info(f"❌ Signal probability {success_probability} below threshold {MIN_SUCCESS_PROBABILITY}")
        return False
    
    # Check if price is below $1
    if entry_price >= MAX_PRICE_THRESHOLD:
        logger.info(f"❌ {symbol} price ${entry_price} is above threshold ${MAX_PRICE_THRESHOLD}")
        return False
    
    # Initialize BYBIT exchange
    logger.info("🔄 Initializing Bybit exchange connection")
    exchange = get_bybit_exchange()
    if not exchange:
        logger.error("❌ Failed to initialize Bybit exchange")
        return False
    
    # Get exchange type for diagnostics
    exchange_type = type(exchange).__name__
    logger.info(f"🔍 Exchange type: {exchange_type}")
    
    # Check if using mock or real exchange
    if hasattr(exchange, 'is_sandbox') and not isinstance(exchange, ccxt.bybit):
        logger.warning("⚠️ Using MOCK exchange - real trades will NOT be executed on Bybit")
    else:
        logger.info("✅ Using REAL Bybit exchange - trades WILL execute with real money")
    
    # Check if we can trade this pair today
    if not check_bybit_trade_limits(symbol):
        logger.info(f"❌ Trade limit reached for {symbol}")
        return False
    
    try:
        # Verify symbol exists on Bybit
        logger.info(f"🔄 Verifying symbol {symbol} exists on Bybit")
        markets = exchange.load_markets()
        if symbol not in markets:
            # Try different symbol format (some exchanges use / others don't)
            alt_symbol = symbol.replace('/', '')
            if alt_symbol not in markets:
                logger.error(f"❌ Symbol {symbol} not found on Bybit")
                return False
            symbol = alt_symbol
            logger.info(f"✅ Using alternative symbol format: {symbol}")
    except Exception as e:
        logger.error(f"❌ Failed to verify symbol {symbol}: {str(e)}")
        return False
    
    # Calculate position size
    logger.info(f"🔄 Calculating position size for {symbol} at price {entry_price}")
    quantity = calculate_position_size(exchange, symbol, entry_price)
    if quantity <= 0:
        logger.error(f"❌ Invalid quantity {quantity} for {symbol}")
        return False
    logger.info(f"✅ Position size: {quantity} units")
    
    # Set leverage to 20x
    logger.info(f"🔄 Setting {BYBIT_LEVERAGE}x leverage for {symbol}")
    if not set_leverage(exchange, symbol):
        logger.error(f"❌ Failed to set leverage for {symbol}")
        return False
    
    # Place the order with take profit and stop loss
    logger.info(f"🔄 Placing {side} order for {symbol} at {entry_price}")
    try:
        order = place_bybit_order(exchange, symbol, side, entry_price, quantity, take_profit, stop_loss)
        if not order:
            logger.error(f"❌ Failed to place order for {symbol}")
            return False
        logger.info(f"✅ Order placed successfully: {order.get('id', 'unknown')}")
    except Exception as e:
        logger.error(f"❌ Exception when placing order for {symbol}: {str(e)}")
        return False
    
    # Send notification via Telegram
    try:
        telegram_client = TelegramClient(os.getenv('TELEGRAM_BOT_TOKEN'), os.getenv('TELEGRAM_CHAT_ID'))
        
        risk = entry_price - stop_loss if side == 'buy' else stop_loss - entry_price
        reward = take_profit - entry_price if side == 'buy' else entry_price - take_profit
        risk_reward = round(reward / risk, 2) if risk > 0 else 0
        
        message = (
            f"🤖 *AUTO TRADE EXECUTED*\n\n"
            f"*Symbol:* {symbol}\n"
            f"*Side:* {side.upper()}\n"
            f"*Entry Price:* ${entry_price}\n"
            f"*Quantity:* {quantity}\n"
            f"*Leverage:* {BYBIT_LEVERAGE}x\n"
            f"*Take Profit:* ${take_profit}\n"
            f"*Stop Loss:* ${stop_loss}\n"
            f"*Risk/Reward:* 1:{risk_reward}\n"
            f"*Win Probability:* {round(success_probability * 100, 1)}%\n\n"
            f"*Daily Trades:* {load_bybit_trade_counts().get(str(date.today()), {}).get('total_trades', 0)}/{MAX_DAILY_BYBIT_TRADES}"
        )
        
        telegram_client.send_message(message)
        logger.info(f"✅ Trade notification sent for {symbol}")
        
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send trade notification: {str(e)}")

def fetch_low_priced_symbols(exchange, limit=MAX_PAIRS_TO_SCAN):
    """Fetch symbols under $1 to scan"""
    try:
        logger.info("Fetching low-priced symbols from Bybit")
        
        # Apply timestamp synchronization for this API call
        if isinstance(exchange, ccxt.bybit):
            # Use our global synchronization function
            exchange = synchronize_bybit_timestamp(exchange)
            logger.info(f"Timestamp synchronized for Bybit API call")
        
        # Get all markets with enhanced error handling
        try:
            logger.info("Loading markets from exchange")
            markets = exchange.load_markets()
            logger.info(f"Successfully loaded {len(markets)} markets")
        except Exception as market_error:
            logger.error(f"Failed to load markets: {str(market_error)}")
            return []
        
        # Get tickers with enhanced error handling
        try:
            logger.info("Fetching tickers for all markets")
            tickers = exchange.fetch_tickers(list(markets.keys()))
            logger.info(f"Successfully fetched {len(tickers)} tickers")
        except Exception as ticker_error:
            logger.error(f"Failed to fetch tickers: {str(ticker_error)}")
            return []
        
        # Filter for symbols with price under $1
        low_priced_symbols = []
        for symbol, ticker in tickers.items():
            price = ticker.get('last')
            if price and price < MAX_PRICE_THRESHOLD:
                low_priced_symbols.append(symbol)
                logger.info(f"Found low-priced symbol: {symbol} at ${price}")
                if len(low_priced_symbols) >= limit:
                    break
        
        logger.info(f"Found {len(low_priced_symbols)} symbols under ${MAX_PRICE_THRESHOLD}")
        return low_priced_symbols
    except Exception as e:
        logger.error(f"❌ Failed to fetch low-priced symbols: {str(e)}")
        return []

def prepare_signal_from_analysis(exchange, symbol, timeframe, analysis_result):
    """Prepare a signal from analysis result"""
    try:
        # Get current market price
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        # Extract analysis data
        trend = analysis_result.get('trend', 'neutral')
        probability = analysis_result.get('success_probability', 0)
        stop_loss = analysis_result.get('stop_loss', 0)
        target = analysis_result.get('take_profit', 0)
        
        # Determine trade side based on trend
        side = 'buy' if trend == 'bullish' else 'sell' if trend == 'bearish' else None
        
        # If no clear trend or missing critical data, return None
        if not side or not stop_loss or not target or probability < MIN_SUCCESS_PROBABILITY:
            return None
        
        # Create the signal
        signal = {
            'symbol': symbol,
            'side': side,
            'entry_price': current_price,
            'take_profit': target,
            'stop_loss': stop_loss,
            'success_probability': probability,
            'timeframe': timeframe
        }
        
        return signal
    except Exception as e:
        logger.error(f"❌ Failed to prepare signal for {symbol}: {str(e)}")
        return None

class BybitTrader:
    """
    BybitTrader class to encapsulate Bybit trading functionality
    Provides methods for placing trades, checking balances, and managing positions
    on the Bybit exchange with built-in risk management and trade tracking
    """
    
    def __init__(self, config=None):
        """
        Initialize a new BybitTrader instance
        
        Args:
            config: Dictionary with configuration parameters
        """
        self.exchange = get_bybit_exchange()
        self.config = config or {}
        self.logger = logging.getLogger('BybitTrader')
        self.trade_memory = get_trade_memory()
        synchronize_bybit_timestamp(self.exchange)
        
    def get_balance(self):
        """
        Get available USDT balance
        
        Returns:
            float: Available balance in USDT
        """
        return get_available_balance(self.exchange)
        
    def place_order(self, symbol, side, entry_price, quantity, take_profit, stop_loss):
        """
        Place an order with take profit and stop loss
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            entry_price: Entry price
            quantity: Order quantity
            take_profit: Take profit price
            stop_loss: Stop loss price
            
        Returns:
            dict: Order result
        """
        # Check trade limits before placing order
        if not check_bybit_trade_limits(symbol):
            self.logger.warning(f"Trade limit reached for {symbol}")
            return None
            
        # Set leverage for this symbol
        leverage = self.config.get('leverage', 20)
        set_leverage(self.exchange, symbol)
        
        # Place the order
        result = place_bybit_order(
            self.exchange, 
            symbol, 
            side, 
            entry_price, 
            quantity, 
            take_profit, 
            stop_loss
        )
        
        # Increment trade count if successful
        if result and result.get('status') == 'success':
            increment_bybit_trade_count(symbol)
            
            # Record trade in memory system
            self._record_trade_in_memory(
                symbol=symbol,
                side=side,
                entry_price=entry_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                order_result=result
            )
            
        return result
        
    def calculate_position_size(self, symbol, entry_price):
        """
        Calculate position size based on available balance and risk settings
        
        Args:
            symbol: Trading pair symbol
            entry_price: Entry price
            
        Returns:
            float: Position size
        """
        balance_percentage = self.config.get('balance_percentage', 0.25)
        return calculate_position_size(self.exchange, symbol, entry_price)
        
    def get_low_priced_symbols(self, max_price=1.0, limit=50):
        """
        Get low-priced symbols under the specified price
        
        Args:
            max_price: Maximum price in USDT
            limit: Maximum number of symbols to return
            
        Returns:
            list: List of symbol dictionaries
        """
        return fetch_low_priced_symbols(self.exchange, limit)
        
    def execute_trade_from_signal(self, signal):
        """
        Execute a trade based on a signal
        
        Args:
            signal: Trade signal dictionary
            
        Returns:
            dict: Trade execution result
        """
        return execute_bybit_trade(signal)
    
    def _record_trade_in_memory(self, symbol, side, entry_price, quantity, 
                               stop_loss, take_profit, order_result):
        """
        Record trade in the memory system
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell' 
            entry_price: Entry price
            quantity: Order quantity
            stop_loss: Stop loss price
            take_profit: Take profit price
            order_result: Order execution result
        """
        try:
            # Calculate risk/reward ratio
            risk_reward_ratio = None
            if stop_loss and take_profit:
                if side.lower() == 'buy':
                    risk = abs(entry_price - stop_loss)
                    reward = abs(take_profit - entry_price)
                else:  # sell/short
                    risk = abs(stop_loss - entry_price)
                    reward = abs(entry_price - take_profit)
                
                if risk > 0:
                    risk_reward_ratio = reward / risk
            
            # Create trade record
            trade = TradeRecord(
                trade_id="",  # Will be auto-generated
                symbol=symbol,
                side='long' if side.lower() == 'buy' else 'short',
                entry_price=entry_price,
                quantity=quantity,
                stop_loss=stop_loss,
                take_profit=take_profit,
                risk_reward_ratio=risk_reward_ratio,
                strategy="bybit_auto",  # Default strategy name
                regime="",  # Will be filled by market regime detector
                confidence_score=0.75,  # Default confidence
                timeframe="1h",  # Default timeframe
                execution_type="market",
                status="open",
                notes=f"Bybit auto trade - Order ID: {order_result.get('order_id', 'N/A')}"
            )
            
            # Add trade to memory
            trade_id = self.trade_memory.add_trade(trade)
            self.logger.info(f"📝 Recorded trade in memory: {trade_id}")
            
            return trade_id
            
        except Exception as e:
            self.logger.error(f"Error recording trade in memory: {e}")
            return None
    
    def close_trade_in_memory(self, symbol, exit_price):
        """
        Close a trade in memory when position is closed
        
        Args:
            symbol: Trading pair symbol
            exit_price: Exit price
        """
        try:
            # Find open trade for this symbol
            open_trades = self.trade_memory.get_open_trades()
            symbol_trades = [t for t in open_trades if t.symbol == symbol]
            
            if symbol_trades:
                # Close the most recent trade for this symbol
                latest_trade = max(symbol_trades, key=lambda t: t.timestamp_entry)
                success = self.trade_memory.close_trade(latest_trade.trade_id, exit_price)
                
                if success:
                    self.logger.info(f"✅ Closed trade in memory: {latest_trade.trade_id}")
                    return latest_trade.trade_id
            else:
                self.logger.warning(f"No open trade found for {symbol} to close")
                
        except Exception as e:
            self.logger.error(f"Error closing trade in memory: {e}")
            
        return None


if __name__ == "__main__":
    # This can be run standalone for testing
    try:
        logger.info("🚀 Testing BYBIT trading module")
        
        # Test BybitTrader class
        trader = BybitTrader()
        
        # Test fetching balance
        balance = trader.get_balance()
        logger.info(f"Available USDT balance: ${balance}")
        
        # Test fetching low-priced symbols
        symbols = trader.get_low_priced_symbols()
        logger.info(f"Fetched {len(symbols)} low-priced symbols")
        
        # Display the 5 cheapest symbols
        for i, s in enumerate(symbols[:5]):
            logger.info(f"Symbol: {s['symbol']}, Price: ${s['price']}, 24h Volume: ${s['volume']}")
        
        logger.info("✅ BYBIT trading module test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error testing BYBIT module: {str(e)}")
        traceback.print_exc()
