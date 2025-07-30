#!/usr/bin/env python3
"""
Bybit USDT Futures Test Trade Script for Low-Cost Pairs
-------------------------------------------------------
Tests trading capabilities on Bybit USDT Futures for low-cost cryptocurrency pairs
using 20x leverage and a percentage of available balance.
"""

import os
import sys
import time
import json
import uuid
import hmac
import hashlib
import logging
import requests
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bybit_futures_test')

# Load environment variables
load_dotenv()
load_dotenv('.env_bybit', override=True)

# Get API credentials
API_KEY = os.getenv('BYBIT_API_KEY')
API_SECRET = os.getenv('BYBIT_API_SECRET') or os.getenv('BYBIT_SECRET_KEY')

# Bybit API endpoints
BASE_URL = 'https://api.bybit.com'  # Production
TESTNET_URL = 'https://api-testnet.bybit.com'  # Testnet

# Check if sandbox mode is enabled
SANDBOX_MODE = os.getenv('BYBIT_SANDBOX', 'false').lower() == 'true'
API_URL = TESTNET_URL if SANDBOX_MODE else BASE_URL

# Trading parameters (from user configuration)
LEVERAGE = 20  # 20x leverage
BALANCE_PERCENTAGE = 0.3  # 30% of available balance
PREFERRED_PAIRS = ['XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'TRXUSDT', 'XLMUSDT']
CATEGORY = 'linear'  # USDT Perpetual Futures

def get_server_time():
    """Get Bybit server time"""
    try:
        response = requests.get(f"{API_URL}/v3/public/time")
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'timeNano' in data['result']:
                server_time = int(int(data['result']['timeNano']) / 1000000)
                local_time = int(time.time() * 1000)
                logger.info(f"Bybit server time: {server_time}")
                logger.info(f"Local time: {local_time}")
                logger.info(f"Time difference: {server_time - local_time}ms")
                return server_time
    except Exception as e:
        logger.error(f"Error getting server time: {e}")
    
    # Fallback to local time
    return int(time.time() * 1000)

def get_signature(params, secret, timestamp=None):
    """Generate signature for Bybit API request"""
    if timestamp is None:
        timestamp = get_server_time()
    
    if isinstance(params, dict):
        # For GET requests with query params
        sorted_params = sorted(params.items())
        signature_payload = '&'.join([f"{key}={value}" for key, value in sorted_params])
        payload = f"{timestamp}{API_KEY}120000{signature_payload}"
    else:
        # For POST requests with JSON body
        payload = f"{timestamp}{API_KEY}120000{params}"
    
    logger.info(f"Signature payload: {payload}")
    
    return hmac.new(
        bytes(secret, 'utf-8'),
        bytes(payload, 'utf-8'), 
        hashlib.sha256
    ).hexdigest()

def get_account_balance():
    """Get available USDT balance from unified account"""
    timestamp = get_server_time()
    recv_window = 120000  # 2 minutes
    
    # Path for V5 API wallet balance
    endpoint = '/v5/account/wallet-balance'
    url = f"{API_URL}{endpoint}"
    
    # Query parameters
    params = {'accountType': 'UNIFIED'}
    query_string = "accountType=UNIFIED"
    
    # Construct signature
    signature = get_signature(params, API_SECRET, timestamp)
    
    # Set headers with auth info
    headers = {
        'X-BAPI-API-KEY': API_KEY,
        'X-BAPI-SIGN': signature,
        'X-BAPI-SIGN-TYPE': '2',
        'X-BAPI-TIMESTAMP': str(timestamp),
        'X-BAPI-RECV-WINDOW': str(recv_window)
    }
    
    # Make API request
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('retCode') == 0 and 'result' in data and 'list' in data['result']:
                account_data = data['result']['list'][0]
                
                # Find USDT balance
                usdt_balance = None
                for coin in account_data.get('coin', []):
                    if coin.get('coin') == 'USDT':
                        usdt_balance = float(coin.get('availableToWithdraw', 0) or coin.get('walletBalance', 0))
                        logger.info(f"Available USDT balance: {usdt_balance}")
                        return usdt_balance
                
                if usdt_balance is None:
                    logger.error("No USDT balance found in account")
                    return 0
            else:
                logger.error(f"Failed to get account balance: {data.get('retMsg')}")
                return 0
        else:
            logger.error(f"Failed to get account balance: HTTP {response.status_code}")
            logger.error(response.text)
            return 0
    except Exception as e:
        logger.error(f"Error getting account balance: {e}")
        return 0

def get_market_price(symbol):
    """Get current market price for the symbol"""
    try:
        # Use the Bybit V5 API to get the latest price
        url = f"{API_URL}/v5/market/tickers"
        params = {
            'category': CATEGORY,
            'symbol': symbol
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('retCode') == 0 and 'result' in data and 'list' in data['result']:
                ticker_list = data['result']['list']
                if ticker_list:
                    price = float(ticker_list[0].get('lastPrice', 0))
                    logger.info(f"Current {symbol} price: ${price}")
                    return price
            
            logger.error(f"Failed to get {symbol} price: {data.get('retMsg')}")
            return None
        else:
            logger.error(f"Failed to get {symbol} price: HTTP {response.status_code}")
            logger.error(response.text)
            return None
    except Exception as e:
        logger.error(f"Error getting {symbol} price: {e}")
        return None

def set_leverage(symbol, leverage=20):
    """Set leverage for the symbol"""
    timestamp = get_server_time()
    recv_window = 120000  # 2 minutes
    
    # Path for V5 API set leverage
    endpoint = '/v5/position/set-leverage'
    url = f"{API_URL}{endpoint}"
    
    # Request body
    request_body = {
        'category': CATEGORY,
        'symbol': symbol,
        'buyLeverage': str(leverage),
        'sellLeverage': str(leverage)
    }
    
    request_body_str = json.dumps(request_body)
    
    # Construct signature
    signature = get_signature(request_body_str, API_SECRET, timestamp)
    
    # Set headers with auth info
    headers = {
        'X-BAPI-API-KEY': API_KEY,
        'X-BAPI-SIGN': signature,
        'X-BAPI-SIGN-TYPE': '2',
        'X-BAPI-TIMESTAMP': str(timestamp),
        'X-BAPI-RECV-WINDOW': str(recv_window),
        'Content-Type': 'application/json'
    }
    
    # Make API request
    try:
        response = requests.post(
            url,
            data=request_body_str,
            headers=headers
        )
        
        logger.info(f"Leverage API response code: {response.status_code}")
        logger.info(f"Leverage API response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('retCode') == 0:
                logger.info(f"✅ Successfully set {leverage}x leverage for {symbol}")
                return True
            else:
                logger.error(f"Failed to set leverage: {data.get('retMsg')}")
                return False
        else:
            logger.error(f"Failed to set leverage: HTTP {response.status_code}")
            logger.error(response.text)
            return False
    except Exception as e:
        logger.error(f"Error setting leverage: {e}")
        return False

def place_futures_order(symbol, side, quantity, price=None, take_profit=None, stop_loss=None):
    """Place a futures order on Bybit"""
    timestamp = get_server_time()
    recv_window = 120000  # 2 minutes
    
    # Generate a unique client order ID
    client_order_id = f"test_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    # Path for V5 API order creation
    endpoint = '/v5/order/create'
    url = f"{API_URL}{endpoint}"
    
    # Order type: Market or Limit
    order_type = 'Market' if price is None else 'Limit'
    
    # Create order parameters
    request_body = {
        'category': CATEGORY,
        'symbol': symbol,
        'side': side,
        'orderType': order_type,
        'qty': str(quantity),
        'timeInForce': 'GoodTillCancel',
        'orderLinkId': client_order_id,
        'positionIdx': 0,  # 0: one-way mode
        'reduceOnly': False,
        'closeOnTrigger': False
    }
    
    # Add price for limit orders
    if price is not None:
        request_body['price'] = str(price)
    
    # Add take profit and stop loss if provided
    if take_profit is not None:
        request_body['takeProfit'] = str(take_profit)
    
    if stop_loss is not None:
        request_body['stopLoss'] = str(stop_loss)
    
    request_body_str = json.dumps(request_body)
    
    # Construct signature
    signature = get_signature(request_body_str, API_SECRET, timestamp)
    
    # Set headers with auth info
    headers = {
        'X-BAPI-API-KEY': API_KEY,
        'X-BAPI-SIGN': signature,
        'X-BAPI-SIGN-TYPE': '2',
        'X-BAPI-TIMESTAMP': str(timestamp),
        'X-BAPI-RECV-WINDOW': str(recv_window),
        'Content-Type': 'application/json'
    }
    
    logger.info(f"Placing {side} {order_type.lower()} order for {quantity} {symbol}")
    logger.info(f"Order parameters: {json.dumps(request_body, indent=2)}")
    
    # Make API request
    try:
        response = requests.post(
            url,
            data=request_body_str,
            headers=headers
        )
        
        logger.info(f"Order API response code: {response.status_code}")
        logger.info(f"Order API response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('retCode') == 0:
                logger.info(f"✅ Order placed successfully: {data.get('result', {})}")
                return True, data.get('result', {})
            else:
                logger.error(f"❌ Order placement failed: {data.get('retMsg')}")
                return False, data.get('retMsg')
        else:
            logger.error(f"❌ Order placement failed: HTTP {response.status_code}")
            logger.error(response.text)
            return False, f"HTTP {response.status_code}: {response.text}"
    except Exception as e:
        logger.error(f"❌ Error placing order: {e}")
        return False, str(e)

def check_trading_rules(symbol):
    """Check trading rules and minimum requirements for a symbol"""
    try:
        logger.info(f"Checking trading rules for {symbol}...")
        url = f"{API_URL}/v5/market/instruments-info"
        params = {
            'category': CATEGORY,
            'symbol': symbol
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('retCode') == 0 and 'result' in data and 'list' in data['result']:
                rules = data['result']['list'][0]
                
                logger.info(f"=== {symbol} Trading Rules ===")
                logger.info(f"Lot size filter: min {rules.get('lotSizeFilter', {}).get('minOrderQty')}, max {rules.get('lotSizeFilter', {}).get('maxOrderQty')}, step {rules.get('lotSizeFilter', {}).get('qtyStep')}")
                logger.info(f"Price filter: min {rules.get('priceFilter', {}).get('minPrice')}, max {rules.get('priceFilter', {}).get('maxPrice')}, tick {rules.get('priceFilter', {}).get('tickSize')}")
                
                if 'leverageFilter' in rules:
                    logger.info(f"Leverage: min {rules['leverageFilter'].get('minLeverage')}, max {rules['leverageFilter'].get('maxLeverage')}")
                
                return rules
        
        logger.error(f"Failed to get trading rules for {symbol}")
        return None
    except Exception as e:
        logger.error(f"Error checking trading rules: {e}")
        return None

def calculate_position_size(symbol, available_balance, percentage=0.3, leverage=20):
    """Calculate position size based on available balance and leverage"""
    # Get current price
    price = get_market_price(symbol)
    if not price:
        return None
    
    # Calculate position size in USD
    position_size_usd = available_balance * percentage * leverage
    
    # Convert to token quantity
    quantity = position_size_usd / price
    
    # Get trading rules
    rules = check_trading_rules(symbol)
    if not rules or 'lotSizeFilter' not in rules:
        return None
    
    # Adjust for minimum order quantity
    min_qty = float(rules['lotSizeFilter'].get('minOrderQty', 0))
    qty_step = float(rules['lotSizeFilter'].get('qtyStep', 0.001))
    
    # Make sure quantity is at least minimum
    if quantity < min_qty:
        quantity = min_qty
    
    # Round to the correct step size
    if qty_step > 0:
        # Round down to the nearest step
        quantity = int(quantity / qty_step) * qty_step
        # Format to avoid scientific notation and respect step precision
        decimals = len(str(qty_step).split('.')[-1]) if '.' in str(qty_step) else 0
        quantity = round(quantity, decimals)
    
    logger.info(f"Calculated position size: {quantity} {symbol} (${position_size_usd:.2f} with {leverage}x leverage)")
    
    return quantity

def test_futures_trade(symbol='XRPUSDT'):
    """Test placing a futures trade for the specified symbol"""
    logger.info(f"Testing futures trade for {symbol}...")
    
    # Get available balance
    available_balance = get_account_balance()
    if not available_balance or available_balance <= 0:
        logger.error(f"❌ No available balance for trading")
        return False
    
    # Calculate position size (30% of balance with 20x leverage)
    quantity = calculate_position_size(symbol, available_balance, BALANCE_PERCENTAGE, LEVERAGE)
    if not quantity:
        logger.error(f"❌ Failed to calculate position size")
        return False
    
    # Set leverage
    if not set_leverage(symbol, LEVERAGE):
        logger.error(f"❌ Failed to set leverage to {LEVERAGE}x")
        # Continue anyway as the account may already have the correct leverage
    
    # Get current price for setting TP/SL
    price = get_market_price(symbol)
    if not price:
        logger.error(f"❌ Failed to get current price")
        return False
    
    # Calculate take profit (3% above entry) and stop loss (2% below entry) for a buy order
    take_profit = round(price * 1.03, 6)
    stop_loss = round(price * 0.98, 6)
    
    # Place a market order
    success, result = place_futures_order(
        symbol=symbol,
        side='Buy',
        quantity=quantity,
        take_profit=take_profit,
        stop_loss=stop_loss
    )
    
    if success:
        logger.info(f"✅ FUTURES TEST TRADE SUCCESSFUL")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Quantity: {quantity}")
        logger.info(f"Entry Price: ~${price}")
        logger.info(f"Take Profit: ${take_profit}")
        logger.info(f"Stop Loss: ${stop_loss}")
        logger.info(f"Leverage: {LEVERAGE}x")
        return True
    else:
        logger.error(f"❌ FUTURES TEST TRADE FAILED")
        return False

def main():
    """Main function to test futures trading"""
    logger.info("=" * 60)
    logger.info("BYBIT FUTURES TEST TRADE")
    logger.info("=" * 60)
    
    # Check if we have API credentials
    if not API_KEY or not API_SECRET:
        logger.error("❌ API credentials not found in environment variables")
        sys.exit(1)
    
    # Log whether we're using testnet or production
    logger.info(f"Using {'TESTNET' if SANDBOX_MODE else 'PRODUCTION'}")
    
    # Test trade mode (interactive prompt)
    print("\n--- Available Pairs ---")
    for idx, pair in enumerate(PREFERRED_PAIRS, 1):
        print(f"{idx}. {pair}")
    
    print("\nSelect a pair to test trade (1-5) or 'all' to test all pairs:")
    choice = input("> ").strip().lower()
    
    # Get confirmation for real order
    print("\n⚠️ This will place a REAL futures order using 30% of your balance with 20x leverage.")
    print("Are you sure you want to continue? (y/n)")
    confirm = input("> ").strip().lower()
    
    if confirm != 'y':
        print("Test cancelled by user.")
        return
    
    if choice == 'all':
        results = {}
        for pair in PREFERRED_PAIRS:
            print(f"\nTesting {pair}...")
            success = test_futures_trade(pair)
            results[pair] = success
            # Wait between API calls to avoid rate limits
            time.sleep(1)
        
        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("=" * 60)
        
        for pair, success in results.items():
            logger.info(f"{pair}: {'✅ SUCCESS' if success else '❌ FAILED'}")
    elif choice.isdigit() and 1 <= int(choice) <= len(PREFERRED_PAIRS):
        pair = PREFERRED_PAIRS[int(choice) - 1]
        test_futures_trade(pair)
    else:
        logger.error("Invalid choice. Please select a number from 1-5 or 'all'.")

if __name__ == "__main__":
    main()
