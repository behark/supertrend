#!/usr/bin/env python3
"""
Bybit Balance Check Script
--------------------------
A simple script to check available balances across all account types in Bybit
"""

import os
import sys
import time
import json
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
logger = logging.getLogger('bybit_balance_check')

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

def check_account_balances():
    """Check account balances for all account types"""
    # Get server time for timestamp
    timestamp = get_server_time()
    recv_window = 120000  # 2 minutes
    
    # Account types to check
    account_types = ['UNIFIED', 'CONTRACT', 'SPOT', 'OPTION', 'FUND']
    
    all_balances = {}
    
    for account_type in account_types:
        # Path for V5 API wallet balance
        endpoint = '/v5/account/wallet-balance'
        url = f"{API_URL}{endpoint}"
        
        # Query parameters
        params = {'accountType': account_type}
        query_string = f"accountType={account_type}"
        
        # Construct signature string
        signature_payload = f"{timestamp}{API_KEY}{recv_window}{query_string}"
        
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
        
        logger.info(f"Checking {account_type} account balance...")
        
        # Make API request
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Pretty print the response with indentation
                formatted_json = json.dumps(data, indent=2)
                logger.info(f"{account_type} balance response:\n{formatted_json}")
                
                # Store in balances dict for summary
                if data.get('retCode') == 0 and 'result' in data:
                    all_balances[account_type] = data['result']
            else:
                logger.error(f"Failed to get {account_type} balance: HTTP {response.status_code}")
                logger.error(response.text)
        except Exception as e:
            logger.error(f"Error checking {account_type} balance: {e}")
    
    return all_balances

def check_spot_trading_rules():
    """Check trading rules for spot markets"""
    try:
        logger.info("Checking spot trading rules for BTC/USDT...")
        response = requests.get(f"{API_URL}/v5/market/instruments-info?category=spot&symbol=BTCUSDT")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('retCode') == 0 and 'result' in data and 'list' in data['result']:
                # Format the output more clearly
                rules = data['result']['list'][0]
                
                logger.info("=== BTC/USDT Spot Trading Rules ===")
                logger.info(f"Minimum order size: {rules.get('minOrderAmt')} BTC")
                logger.info(f"Maximum order size: {rules.get('maxOrderAmt')} BTC")
                logger.info(f"Tick size (price increment): {rules.get('tickSize')}")
                logger.info(f"Min price: {rules.get('minPrice')}")
                logger.info(f"Max price: {rules.get('maxPrice')}")
                logger.info(f"Min notional value: {rules.get('minNotional', 'Not specified')}")
                logger.info("================================")
                
                return rules
        
        logger.error("Failed to get trading rules")
        logger.error(response.text)
        return None
    
    except Exception as e:
        logger.error(f"Error checking trading rules: {e}")
        return None

def main():
    """Main function to check Bybit account balances"""
    logger.info("=" * 60)
    logger.info("BYBIT BALANCE CHECK")
    logger.info("=" * 60)
    
    # Check if we have API credentials
    if not API_KEY or not API_SECRET:
        logger.error("❌ API credentials not found in environment variables")
        sys.exit(1)
    
    # Log whether we're using testnet or production
    logger.info(f"Using {'TESTNET' if SANDBOX_MODE else 'PRODUCTION'}")
    
    # Check account balances
    check_account_balances()
    
    # Check spot trading rules
    check_spot_trading_rules()

if __name__ == "__main__":
    main()
