#!/usr/bin/env python
"""
Live Trade Verification Script
This script checks for existing positions on Bitget and attaches TP/SL orders
to verify the fixes to the TP/SL attachment logic without placing new trades.
"""

import os
import sys
import logging
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("LiveTradeVerify")

# Load environment variables from .env file
load_dotenv()

# Import the trading API
from src.integrations.bidget import TradingAPI
from src.integrations.telegram import TelegramNotifier

def verify_live_trade():
    """Check for existing positions and attach TP/SL to verify fixes"""
    logger.info("=== STARTING TP/SL ATTACHMENT VERIFICATION ===")
    
    # Initialize API client
    api = TradingAPI()
    telegram = TelegramNotifier()
    
    # Check if API is configured
    if not api.is_configured:
        logger.error("Bitget API not configured. Please check your .env file.")
        telegram.send_message("⚠️ VERIFICATION FAILED: Bitget API not configured. Please check your .env file.")
        return False
        
    # Send notification that we're starting verification
    telegram.send_message("🔍 VERIFICATION: Checking existing positions to verify TP/SL attachment...")
    
    # Fetch symbol information from Bitget API to get price tick sizes
    try:
        endpoint = "/api/mix/v1/market/contracts"
        params = {"productType": "umcbl"}
        contracts_data = api._make_request("GET", endpoint, params=params)
        
        if not contracts_data or 'data' not in contracts_data:
            logger.error("Failed to retrieve contracts data")
            telegram.send_message("❌ VERIFICATION FAILED: Could not retrieve contracts data")
            return False
            
        # Create a dictionary of price tick sizes for each symbol
        tick_sizes = {}
        for contract in contracts_data.get('data', []):
            symbol = contract.get('symbol')
            # Log the full contract data to see all available fields
            logger.info(f"Contract data for {symbol}: {contract}")
            
            # The correct field is 'pricePlace' which indicates decimal places
            if 'pricePlace' in contract:
                # Convert decimal places to tick size
                price_place = int(contract.get('pricePlace', 4))
                tick_size = 10 ** (-price_place)
            else:
                # Default to 4 decimal places (0.0001) if not specified
                tick_size = 0.0001
            
            tick_sizes[symbol] = tick_size
            logger.info(f"Symbol {symbol} has price tick size {tick_size}")
    except Exception as e:
        logger.exception(f"Error fetching symbol information: {str(e)}")
        telegram.send_message(f"❌ VERIFICATION FAILED: Error fetching symbol information: {str(e)}")
        return False
    
    # Get all open positions
    try:
        # Direct API call to get positions
        endpoint = "/api/mix/v1/position/allPosition"
        params = {"productType": "umcbl"}
        positions_data = api._make_request("GET", endpoint, params=params)
        
        if not positions_data or 'data' not in positions_data:
            logger.error("Failed to retrieve positions data")
            telegram.send_message("❌ VERIFICATION FAILED: Could not retrieve positions data")
            return False
            
        positions = positions_data.get('data', [])
        
        if not positions:
            logger.warning("No open positions found to attach TP/SL orders")
            telegram.send_message("⚠️ VERIFICATION SKIPPED: No open positions found to attach TP/SL orders")
            return False
            
        logger.info(f"Found {len(positions)} open positions")
        
        # Process each position
        success_count = 0
        for position in positions:
            symbol = position.get('symbol')
            size = float(position.get('total', 0))
            margin_mode = position.get('marginMode')
            hold_side = position.get('holdSide')
            entry_price = float(position.get('averageOpenPrice', 0))
            
            if size <= 0 or not symbol or not hold_side or entry_price <= 0:
                logger.warning(f"Skipping invalid position: {position}")
                continue
                
            # Get current market price
            market_data = api.get_market_data(symbol)
            current_price = float(market_data.get('last_price', 0))
            
            if current_price <= 0:
                logger.warning(f"Could not get valid price for {symbol}, skipping")
                continue
                
            # Calculate TP/SL levels based on position side
            is_long = hold_side.lower() == 'long'
            
            # Get the minimum price limit (use 1% of current price as safe minimum)
            min_price_limit = current_price * 0.01
            
            # Get the tick size for this symbol from our fetched data
            tick_size = tick_sizes.get(symbol, 0.0001)  # Default to 0.0001 if not found
            logger.info(f"Using price tick size {tick_size} for {symbol}")
            
            # Helper function to round to specific tick size with exact precision
            def round_to_tick_size(value, tick_size):
                # Calculate how many decimal places we need for this tick size
                decimal_places = 0
                temp = tick_size
                while temp < 1:
                    temp *= 10
                    decimal_places += 1
                    
                # Round to the nearest tick
                rounded = round(value / tick_size) * tick_size
                
                # Format to exact decimal places to avoid floating point precision issues
                return float(f"{rounded:.{decimal_places}f}")
            
            if is_long:
                # For long positions
                take_profit_raw = current_price * 1.15  # 15% profit
                take_profit = round_to_tick_size(take_profit_raw, tick_size)
                
                calculated_sl = current_price * 0.95  # 5% loss
                stop_loss_min = max(calculated_sl, min_price_limit * 1.01)  # Ensure above min limit
                stop_loss = round_to_tick_size(stop_loss_min, tick_size)
            else:
                # For short positions
                tp_price = round_to_tick_size(current_price * 0.85, tick_size)  # 15% profit
                sl_price = round_to_tick_size(current_price * 1.05, tick_size)  # 5% loss
                logger.info(f"Setting TP: {tp_price}, SL: {sl_price}")
                
                # Split the position between TP and SL
                # Use 50% for TP and 50% for SL
                tp_size = round(size * 0.5)
                sl_size = size - tp_size
                
                logger.info(f"Splitting position: TP size = {tp_size}, SL size = {sl_size}")
                
                # Use set_take_profit and set_stop_loss methods directly
                # Place TP order
                tp_result = api.set_take_profit(
                    symbol=symbol,
                    quantity=tp_size,  # Use half the position size
                    price=tp_price,
                    position_side="short"  # Position side
                )
                
                # Place SL order
                sl_result = api.set_stop_loss(
                    symbol=symbol,
                    quantity=sl_size,  # Use the other half of the position size
                    stop_price=sl_price,
                    position_side="short"  # Position side
                )
                
            # Check results
            tp_result = tp_result.get('take_profit', {})
            sl_result = sl_result.get('stop_loss', {})
            
            tp_success = tp_result and 'success' in tp_result and tp_result['success'] is True
            sl_success = sl_result and 'success' in sl_result and sl_result['success'] is True
            
            if tp_success and sl_success:
                logger.info(f"✅ Successfully attached TP/SL to {symbol} {hold_side} position")
                success_count += 1
            else:
                logger.error(f"Failed to attach TP/SL to {symbol} {hold_side} position")
                logger.error(f"TP result: {tp_result}")
                logger.error(f"SL result: {sl_result}")
                
        # Final verification result
        if success_count > 0:
            logger.info(f"✅ VERIFICATION SUCCESSFUL: Attached TP/SL to {success_count} positions")
            telegram.send_message(f"""
✅ VERIFICATION SUCCESSFUL!
Attached TP/SL orders to {success_count} existing positions
Full automation verified!
""")
            return True
        else:
            logger.error("Failed to attach TP/SL to any positions")
            telegram.send_message("❌ VERIFICATION FAILED: Could not attach TP/SL to any positions")
            return False
            
    except Exception as e:
        logger.exception(f"Error during verification: {str(e)}")
        telegram.send_message(f"❌ VERIFICATION FAILED: Error during verification: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        success = verify_live_trade()
        if success:
            logger.info("Verification completed successfully")
            sys.exit(0)
        else:
            logger.error("Verification failed")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"Verification script error: {str(e)}")
        sys.exit(1)
