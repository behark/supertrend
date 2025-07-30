#!/usr/bin/env python3
"""
Direct Bybit Market Order Test Script
------------------------------------
A focused script to verify Bybit API connectivity and market order execution
using direct API calls with manual timestamp adjustment.
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
import urllib.parse
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('direct_bybit_test')

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

# Market order constants
SYMBOL = 'BTCUSDT'    # BTC/USDT in Bybit format
SIDE = 'Buy'          # Buy direction
ORDER_TYPE = 'Market' # Market order
TIME_IN_FORCE = 'GoodTillCancel'  # GTC for USDT perpetual

# Order category - try linear (USDT perpetual) instead of spot
# CATEGORY_SPOT = 'spot'
CATEGORY_LINEAR = 'linear'  # USDT perpetual futures

def get_signature(params, secret, timestamp=None):
    """Generate signature for Bybit API request"""
    # For V5 API, use timestamp + HTTP method + request path + query string/request body
    # Reference: https://bybit-exchange.github.io/docs/v5/guide/authentication
    
    # Convert dict params to query string
    if isinstance(params, dict):
        # Sort parameters by key alphabetically
        sorted_params = {k: params[k] for k in sorted(params.keys())}
        if sorted_params:
            query_string = urllib.parse.urlencode(sorted_params)
        else:
            query_string = ''
    else:
        query_string = params if params else ''
    
    # If timestamp provided explicitly, use it in signature
    if timestamp:
        payload = str(timestamp) + query_string
    else:
        payload = query_string
    
    logger.debug(f"Signature payload: {payload}")
    
    signature = hmac.new(
        bytes(secret, 'utf-8'),
        bytes(payload, 'utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    logger.debug(f"Generated signature: {signature}")
    return signature

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

def get_account_balance():
    """Get account balance to verify API connectivity"""
    # Get server time for timestamp
    timestamp = get_server_time()
    recv_window = 120000  # 2 minutes
    
    # Path for V5 API wallet balance
    endpoint = '/v5/account/wallet-balance'
    url = f"{API_URL}{endpoint}"
    
    # Query parameters - EXACTLY as Bybit expects them, no URL encoding
    # Based on error message: origin_string[17537587766582uY6hr6AMsaj3RoukJ120000accountType=UNIFIED]
    params = {'accountType': 'UNIFIED'}
    
    # Construct signature string EXACTLY as Bybit expects
    # Format: timestamp + api_key + recv_window + query parameters (no URL encoding, no path)
    signature_payload = f"{timestamp}{API_KEY}{recv_window}accountType=UNIFIED"
    
    logger.info(f"Signature payload: {signature_payload}")
    
    signature = hmac.new(
        bytes(API_SECRET, 'utf-8'),
        bytes(signature_payload, 'utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Set headers with auth info
    headers = {
        'X-BAPI-API-KEY': API_KEY,
        'X-BAPI-SIGN': signature,
        'X-BAPI-SIGN-TYPE': '2',
        'X-BAPI-TIMESTAMP': str(timestamp),
        'X-BAPI-RECV-WINDOW': str(recv_window)
    }
    
    logger.info(f"Making authenticated request to {url}")
    
    # Make API request
    try:
        response = requests.get(
            url,
            params=params,
            headers=headers
        )
        logger.info(f"Balance API response: {response.status_code}")
        logger.info(f"Response: {response.text[:200]}...")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0:
                logger.info("✅ API authentication successful")
                return True
        
        return False
    except Exception as e:
        logger.error(f"Error checking balance: {e}")
        return False

def get_btc_price():
    """Get current BTC/USDT price from Bybit"""
    try:
        response = requests.get(f"{API_URL}/v5/market/tickers?category=spot&symbol={SYMBOL}")
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0 and 'result' in data and 'list' in data['result']:
                price = float(data['result']['list'][0]['lastPrice'])
                logger.info(f"Current BTC price: ${price:,.2f}")
                return price
    except Exception as e:
        logger.error(f"Error getting BTC price: {e}")
    
    # Fallback price (approximate)
    logger.warning("Could not get current BTC price, using fallback value")
    return 65000.0

def place_market_order(quantity=None):
    """Place a minimal market order on Bybit
    
    Args:
        quantity: BTC amount to buy (if None, calculate minimum valid size)
    """
    # Get current BTC price and calculate minimum order size
    # Bybit minimum notional value is MUCH higher than documented
    btc_price = get_btc_price()
    min_notional = 100.0  # Testing with significantly higher minimum (real minimum appears to be quite high)
    
    if quantity is None:
        # Calculate minimum quantity based on price
        quantity = min_notional / btc_price
        # Round to 5 decimals (Bybit precision) and ensure string format without scientific notation
        quantity = round(quantity, 5)
        
    # Log calculated value
    estimated_value_usd = quantity * btc_price
    logger.info(f"Order size: {quantity:.5f} BTC (approx. ${estimated_value_usd:.2f})")
    # Get server time to avoid timestamp issues
    timestamp = get_server_time()
    recv_window = 120000  # 2 minutes
    
    # Create unique client order ID
    client_order_id = f"test_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    
    # Path for V5 API order creation
    endpoint = '/v5/order/create'
    url = f"{API_URL}{endpoint}"
    
    # Create order parameters for V5 API - using linear (USDT perpetual) instead of spot
    # For linear contracts, we specify quantity in USD, not BTC amount
    # We'll use a fixed quantity of 10 USD for testing
    fixed_usd_qty = 10.0
    
    request_body = {
        'category': CATEGORY_LINEAR,  # Use linear (USDT perpetual) market
        'symbol': SYMBOL,
        'side': SIDE, 
        'orderType': ORDER_TYPE,
        'qty': '10',  # Fixed 10 USD size for linear market
        'timeInForce': TIME_IN_FORCE,
        'orderLinkId': client_order_id,
        'positionIdx': 0,  # 0: one-way mode
        'reduceOnly': False,
        'closeOnTrigger': False
    }
    
    # Convert request body to JSON string with no spaces
    request_body_str = json.dumps(request_body, separators=(',', ':'))
    
    # Construct signature string EXACTLY as Bybit expects
    # For POST requests, we need the timestamp + API key + recv_window + JSON body
    signature_payload = f"{timestamp}{API_KEY}{recv_window}{request_body_str}"
    
    logger.info(f"Signature payload: {signature_payload}")
    
    signature = hmac.new(
        bytes(API_SECRET, 'utf-8'),
        bytes(signature_payload, 'utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    # Set headers with auth info
    headers = {
        'X-BAPI-API-KEY': API_KEY,
        'X-BAPI-SIGN': signature,
        'X-BAPI-SIGN-TYPE': '2',
        'X-BAPI-TIMESTAMP': str(timestamp),
        'X-BAPI-RECV-WINDOW': str(recv_window),
        'Content-Type': 'application/json'
    }
    
    # Log order details
    logger.info(f"Placing {SIDE} market order for {quantity} {SYMBOL}")
    logger.info(f"Order parameters: {json.dumps(request_body)}")
    
    # Make API request
    try:
        response = requests.post(
            url,
            data=request_body_str,
            headers=headers
        )
        
        logger.info(f"Order API response code: {response.status_code}")
        
        # Parse response
        if response.status_code == 200:
            result = response.json()
            logger.info(f"Order API response: {json.dumps(result, indent=2)}")
            
            if result.get('retCode') == 0:
                order_id = result.get('result', {}).get('orderId')
                logger.info(f"✅ Order placed successfully! Order ID: {order_id}")
                return True, order_id
            else:
                error_msg = result.get('retMsg', 'Unknown error')
                logger.error(f"❌ Order placement failed: {error_msg}")
                return False, error_msg
        else:
            logger.error(f"❌ API request failed with status code {response.status_code}")
            logger.error(f"Response: {response.text}")
            return False, f"HTTP {response.status_code}"
            
    except Exception as e:
        logger.error(f"❌ Exception during order placement: {e}")
        return False, str(e)

def main():
    """Main function to test Bybit order placement"""
    logger.info("=" * 60)
    logger.info("DIRECT BYBIT MARKET ORDER TEST")
    logger.info("=" * 60)
    
    # Check if we have API credentials
    if not API_KEY or not API_SECRET:
        logger.error("❌ API credentials not found in environment variables")
        sys.exit(1)
    
    # Log whether we're using testnet or production
    logger.info(f"Using {'TESTNET' if SANDBOX_MODE else 'PRODUCTION'}")
    logger.info(f"API URL: {API_URL}")
    
    # Check API connectivity with account balance endpoint
    logger.info("Checking API connectivity...")
    if not get_account_balance():
        logger.error("❌ Failed to authenticate with Bybit API")
        sys.exit(1)
    
    # Ask for confirmation before placing real order
    if not SANDBOX_MODE:
        confirmation = input("⚠️ You are about to place a REAL market order. Continue? (y/n): ")
        if confirmation.lower() not in ['y', 'yes']:
            logger.info("Order cancelled by user")
            sys.exit(0)
    
    # Place minimal market order with calculated minimum size
    success, result = place_market_order()
    
    if success:
        logger.info("=" * 60)
        logger.info("✅ BYBIT ORDER TEST SUCCESSFUL")
        logger.info("=" * 60)
    else:
        logger.info("=" * 60)
        logger.info("❌ BYBIT ORDER TEST FAILED")
        logger.info("=" * 60)
    
    return success

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Test cancelled by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)
