#!/usr/bin/env python3
"""
Final verification script for Bitget TP/SL fix
Tests the updated place_tp_sl_orders method with plan orders
"""

import os
import sys
import time
import logging
import dotenv
from typing import Dict, Optional
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('verify_tpsl')

# Load environment variables from the correct location
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Inside=Bar:Strategy/.env')
if os.path.exists(dotenv_path):
    logger.info(f"Loading environment from {dotenv_path}")
    dotenv.load_dotenv(dotenv_path)
else:
    logger.warning(f"No .env file found at {dotenv_path}")

# Add the src directory to the Python path
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Inside=Bar:Strategy/src')
logger.info(f"Adding to Python path: {src_path}")
sys.path.append(src_path)

# Import the Bitget integration
from integrations.bidget import TradingAPI

def verify_tpsl_fix():
    """
    Verify the TP/SL fix by:
    1. Placing a small test trade
    2. Attaching TP/SL orders using the updated place_tp_sl_orders method
    3. Verifying both orders are successfully placed
    """
    logger.info("Starting TP/SL fix verification")
    
    # Initialize the Bitget API
    api = TradingAPI()
    
    # Check if API is configured
    if not api.is_configured:
        logger.error("Bitget API not configured. Please check your .env file.")
        return False
    
    # Get account info
    account_info = api.get_account_info()
    balance = float(account_info.get('available_balance', 0))
    logger.info(f"Available balance: ${balance:.2f} USDT")
    
    if balance < 1:
        logger.error(f"Insufficient balance (${balance:.2f}) for testing. Need at least $1 USDT.")
        return False
    
    # Use a low-price coin to maximize quantity with minimal balance
    # SHIB/USDT is ideal as it has a very low price per unit
    symbol = "SHIB/USDT"
    formatted_symbol = api._format_symbol_for_bitget(symbol)
    
    # Get current market price
    market_data = api.get_market_data(symbol)
    current_price = float(market_data.get('last_price', 0))
    
    if current_price <= 0:
        logger.error(f"Could not get current price for {symbol}")
        return False
    
    logger.info(f"Current price of {symbol}: ${current_price:.8f}")
    
    # Use fixed notional value of $5.5 USDT (slightly above minimum) for test trade
    notional_value = 5.5  # Slightly above Bitget's minimum of $5
    leverage = 20
    margin_value = notional_value / leverage
    
    # Calculate quantity
    quantity = notional_value / current_price
    
    # Log the values
    logger.info(f"Using fixed notional value: ${notional_value:.2f} USDT")
    logger.info(f"Required margin: ${margin_value:.4f} USDT")
    
    # Verify we have enough balance
    if margin_value > balance * 0.9:  # Use at most 90% of available balance
        logger.error(f"Insufficient balance (${balance:.2f}) for test trade margin (${margin_value:.4f})")
        return False
    
    # Round quantity to whole number for SHIB (Bitget requires integer quantities for SHIB)
    quantity = int(quantity)  # Use integer for SHIB as per Bitget's requirement
    logger.info(f"Rounded quantity to integer: {quantity} SHIB")
    
    logger.info(f"Test trade parameters:")
    logger.info(f"Symbol: {symbol}")
    logger.info(f"Side: buy (long)")
    logger.info(f"Quantity: {quantity}")
    logger.info(f"Leverage: {leverage}x")
    logger.info(f"Notional value: ${notional_value:.2f}")
    
    # Calculate TP/SL prices (using 5% for both to ensure they're valid)
    take_profit = current_price * 1.05  # 5% above current price
    stop_loss = current_price * 0.95    # 5% below current price
    
    logger.info(f"Take profit: ${take_profit:.8f} (5% above current price)")
    logger.info(f"Stop loss: ${stop_loss:.8f} (5% below current price)")
    
    # Place the test order
    logger.info(f"Placing test order...")
    order_result = api.place_order_direct(symbol, "buy", quantity)
    
    if 'error' in order_result:
        logger.error(f"Failed to place test order: {order_result.get('error')}")
        return False
    
    logger.info(f"Test order placed successfully: {order_result}")
    time.sleep(2)  # Wait for order to be processed
    
    # Now attach TP/SL orders using the updated method
    logger.info(f"Attaching TP/SL orders...")
    tp_sl_result = api.place_tp_sl_orders(symbol, "buy", quantity, current_price, take_profit, stop_loss)
    
    # Check TP result
    tp_result = tp_sl_result.get('take_profit', {})
    if tp_result and tp_result.get('success'):
        logger.info(f"✅ Take profit order placed successfully: {tp_result}")
    else:
        logger.error(f"❌ Take profit order failed: {tp_result}")
    
    # Check SL result
    sl_result = tp_sl_result.get('stop_loss', {})
    if sl_result and sl_result.get('success'):
        logger.info(f"✅ Stop loss order placed successfully: {sl_result}")
    else:
        logger.error(f"❌ Stop loss order failed: {sl_result}")
    
    # Final verification result
    if (tp_result and tp_result.get('success')) and (sl_result and sl_result.get('success')):
        logger.info("🎉 VERIFICATION SUCCESSFUL: Both TP and SL orders were placed correctly!")
        return True
    else:
        logger.error("❌ VERIFICATION FAILED: One or both TP/SL orders failed.")
        return False

if __name__ == "__main__":
    try:
        success = verify_tpsl_fix()
        if success:
            print("\n✅ TP/SL FIX VERIFIED SUCCESSFULLY!")
            print("The fix has been implemented and tested successfully.")
            print("Both take profit and stop loss orders are now properly attached to positions.")
        else:
            print("\n❌ TP/SL FIX VERIFICATION FAILED")
            print("Please check the logs above for details on what went wrong.")
    except Exception as e:
        logger.exception(f"Verification script encountered an error: {e}")
        print("\n❌ VERIFICATION SCRIPT ERROR")
        print(f"Error: {str(e)}")
