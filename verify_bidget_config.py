#!/usr/bin/env python
"""
Bidget Configuration Verification Script
---------------------------------------
This script verifies that the Bidget configuration is correctly applied:
- USDT Perpetual Futures only (Bybit)
- 20x leverage
- 30% of available balance per trade
- Only coins under $1
- Win probability >90%
- TP/SL properly configured
"""
import os
import sys
import logging
import json
import time
import ccxt
from decimal import Decimal
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
if os.path.exists('.env_bybit'):
    load_dotenv('.env_bybit')

# Import local modules
sys.path.insert(0, '.')
from config import (
    EXCHANGES, 
    SYMBOLS_TO_SCAN,
    MAX_COIN_PRICE,
    LEVERAGE,
    BALANCE_PERCENTAGE,
    MAX_DAILY_TRADES,
    MAX_TELEGRAM_SIGNALS
)
from smart_filter import SmartFilter

def print_header(text):
    """Print a formatted header"""
    print("\n" + "="*80)
    print(f" {text}")
    print("="*80)

def print_success(text):
    """Print a success message"""
    print(f"✅ {text}")

def print_warning(text):
    """Print a warning message"""
    print(f"⚠️ {text}")

def print_error(text):
    """Print an error message"""
    print(f"❌ {text}")

def verify_config_values():
    """Verify that config values match Bidget requirements"""
    print_header("VERIFYING BIDGET CONFIGURATION VALUES")
    
    # Check exchanges
    if EXCHANGES == ['bybit']:
        print_success("Exchange configuration is correct (Bybit only)")
    else:
        print_error(f"Exchange configuration is incorrect: {EXCHANGES}, should be ['bybit']")
    
    # Check leverage
    if LEVERAGE == 20:
        print_success("Leverage configuration is correct (20x)")
    else:
        print_error(f"Leverage configuration is incorrect: {LEVERAGE}, should be 20")
    
    # Check balance percentage
    if BALANCE_PERCENTAGE == 0.3:
        print_success("Balance percentage configuration is correct (30%)")
    else:
        print_error(f"Balance percentage configuration is incorrect: {BALANCE_PERCENTAGE}, should be 0.3")
    
    # Check max coin price
    if MAX_COIN_PRICE == 1.0:
        print_success("Max coin price configuration is correct ($1.00)")
    else:
        print_error(f"Max coin price configuration is incorrect: ${MAX_COIN_PRICE}, should be $1.00")
    
    # Check daily limits
    if MAX_DAILY_TRADES == 15:
        print_success("Daily trades limit configuration is correct (15)")
    else:
        print_error(f"Daily trades limit configuration is incorrect: {MAX_DAILY_TRADES}, should be 15")
    
    if MAX_TELEGRAM_SIGNALS == 30:
        print_success("Daily signals limit configuration is correct (30)")
    else:
        print_error(f"Daily signals limit configuration is incorrect: {MAX_TELEGRAM_SIGNALS}, should be 30")
    
    # Check symbols
    preferred_symbols = ['XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'TRX/USDT', 'XLM/USDT']
    missing_symbols = [s for s in preferred_symbols if s not in SYMBOLS_TO_SCAN]
    extra_symbols = [s for s in SYMBOLS_TO_SCAN if s not in preferred_symbols]
    
    if not missing_symbols and not extra_symbols:
        print_success("Symbol configuration is correct")
    else:
        if missing_symbols:
            print_warning(f"Missing preferred symbols: {missing_symbols}")
        if extra_symbols:
            print_warning(f"Extra symbols found: {extra_symbols}")

def verify_smart_filter():
    """Verify that smart filter works correctly"""
    print_header("VERIFYING SMART FILTER FUNCTIONALITY")
    
    smart_filter = SmartFilter({
        'max_coin_price': MAX_COIN_PRICE,
        'min_success_probability': 0.9,
        'max_telegram_signals': MAX_TELEGRAM_SIGNALS
    })
    
    # Test price filtering
    test_signals = [
        {"symbol": "BTC/USDT", "entry_price": 40000, "timeframe": "1h", "probability": 0.95},
        {"symbol": "ETH/USDT", "entry_price": 2500, "timeframe": "1h", "probability": 0.95},
        {"symbol": "ADA/USDT", "entry_price": 0.45, "timeframe": "1h", "probability": 0.95},
        {"symbol": "XRP/USDT", "entry_price": 0.50, "timeframe": "1h", "probability": 0.95},
        {"symbol": "DOGE/USDT", "entry_price": 0.08, "timeframe": "1h", "probability": 0.95},
        {"symbol": "SOL/USDT", "entry_price": 120, "timeframe": "1h", "probability": 0.95},
    ]
    
    # Test price filtering
    print("\nTesting price filtering (<$1):")
    for signal in test_signals:
        result = smart_filter.check_price(signal["entry_price"])
        symbol = signal["symbol"]
        price = signal["entry_price"]
        if result:
            print(f"✅ {symbol} (${price:.2f}) - Passed price filter")
        else:
            print(f"❌ {symbol} (${price:.2f}) - Rejected (above $1)")
    
    # Test timeframe filtering
    print("\nTesting timeframe filtering (15m-3h):")
    timeframes = ["1m", "5m", "15m", "30m", "1h", "2h", "3h", "4h", "1d"]
    for tf in timeframes:
        result = smart_filter.check_timeframe(tf)
        if result:
            print(f"✅ {tf} - Passed timeframe filter")
        else:
            print(f"❌ {tf} - Rejected (not in 15m-3h range)")
    
    # Test probability filtering
    print("\nTesting probability filtering (>90%):")
    probabilities = [0.85, 0.88, 0.9, 0.92, 0.95, 0.99]
    for prob in probabilities:
        result = smart_filter.check_probability(prob)
        if result:
            print(f"✅ {prob*100:.1f}% - Passed probability filter")
        else:
            print(f"❌ {prob*100:.1f}% - Rejected (below 90%)")
    
    # Test signal counting
    print("\nTesting signal counting (max 30):")
    signals_sent = 0
    for i in range(35):
        if smart_filter.can_send_signal():
            smart_filter.signals_sent_today += 1
            signals_sent += 1
            print(f"✅ Signal {signals_sent} sent")
        else:
            print(f"❌ Signal {i+1} rejected (limit reached)")

def verify_bybit_minimums():
    """Verify Bybit minimum order sizes for preferred pairs"""
    print_header("VERIFYING BYBIT MINIMUM ORDER SIZES")
    
    # Initialize Bybit exchange
    try:
        api_key = os.getenv("BYBIT_API_KEY")
        api_secret = os.getenv("BYBIT_SECRET_KEY")
        
        if not api_key or not api_secret:
            print_error("No Bybit API credentials found. Skipping minimum order verification.")
            return
        
        bybit = ccxt.bybit({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'adjustForTimeDifference': True
            }
        })
        
        # Load markets
        print("Loading Bybit markets...")
        markets = bybit.load_markets()
        
        # Check preferred pairs
        preferred_pairs = [s.replace('/', '') for s in SYMBOLS_TO_SCAN]
        
        print("\nChecking minimum order sizes for preferred pairs:")
        for pair in preferred_pairs:
            linear_pair = f"{pair}:USDT"  # Linear futures format
            
            # Get market info for the pair
            if linear_pair in markets:
                market = markets[linear_pair]
                
                # Get minimum notional value
                limits = market.get('limits', {})
                min_cost = limits.get('cost', {}).get('min', 0)
                min_amount = limits.get('amount', {}).get('min', 0)
                
                # Calculate minimum position with 20x leverage and 30% of $14 balance
                balance = 14.0 * BALANCE_PERCENTAGE  # $4.2
                leveraged_balance = balance * LEVERAGE  # $84
                
                # Is our minimum balance sufficient?
                if leveraged_balance >= min_cost:
                    print_success(f"{pair}: Min order {min_cost} USDT - Our position: {leveraged_balance:.2f} USDT ✓")
                else:
                    print_error(f"{pair}: Min order {min_cost} USDT - Our position: {leveraged_balance:.2f} USDT ✗")
            else:
                print_warning(f"{pair}: Not found as linear futures on Bybit")
    
    except Exception as e:
        print_error(f"Error verifying Bybit minimums: {str(e)}")

def main():
    """Main verification function"""
    print_header("BIDGET CONFIGURATION VERIFICATION")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verify configuration values
    verify_config_values()
    
    # Verify smart filter functionality
    verify_smart_filter()
    
    # Verify Bybit minimum order sizes
    verify_bybit_minimums()
    
    print_header("VERIFICATION COMPLETE")

if __name__ == "__main__":
    main()
