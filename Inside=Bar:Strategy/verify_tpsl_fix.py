#!/usr/bin/env python3
"""
TP/SL Fix Verification Script for SuperTrend Bot
This script directly tests the fixed TP/SL methods to verify they work properly.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TPSLVerify")

# Load environment variables
load_dotenv()

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.integrations.bidget import TradingAPI
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

def test_tp_sl_methods():
    """Test TP/SL methods with holdSide parameter"""
    logger.info("=== STARTING TP/SL METHOD VERIFICATION TEST ===")
    
    # Initialize Bitget client
    try:
        client = TradingAPI()
        logger.info("Bitget client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Bitget client: {e}")
        return False
    
    # Test pair - using DOGEUSDT as it was mentioned in previous issues
    symbol = "DOGEUSDT_UMCBL"
    quantity = 100  # Test quantity
    
    # Test both long and short positions
    for position_side in ["long", "short"]:
        logger.info(f"Testing {position_side.upper()} position TP/SL methods")
        
        # Test price values
        if position_side == "long":
            tp_price = 0.15  # Example take profit price for long
            sl_price = 0.10  # Example stop loss price for long
        else:
            tp_price = 0.10  # Example take profit price for short
            sl_price = 0.15  # Example stop loss price for short
        
        # Test set_take_profit
        logger.info(f"Testing set_take_profit with holdSide={position_side}")
        try:
            # Call the main method directly
            tp_result = client.set_take_profit(symbol, quantity, tp_price, position_side)
            logger.info(f"Main set_take_profit result: {tp_result}")
            
            # Call the legacy method (should redirect to main)
            tp_legacy_result = client.set_take_profit_bitget(symbol, quantity, tp_price, position_side)
            logger.info(f"Legacy set_take_profit_bitget result: {tp_legacy_result}")
            
            # Verify redirection is working
            if str(tp_result) == str(tp_legacy_result):
                logger.info("✅ Legacy method successfully redirected to main implementation")
            else:
                logger.error("❌ Legacy method not redirecting properly")
                return False
        except Exception as e:
            logger.error(f"Error testing take profit methods: {e}")
            return False
        
        # Test set_stop_loss
        logger.info(f"Testing set_stop_loss with holdSide={position_side}")
        try:
            # Call the main method directly
            sl_result = client.set_stop_loss(symbol, quantity, sl_price, position_side)
            logger.info(f"Main set_stop_loss result: {sl_result}")
            
            # Call the legacy method (should redirect to main)
            sl_legacy_result = client.set_stop_loss_bitget(symbol, quantity, sl_price, position_side)
            logger.info(f"Legacy set_stop_loss_bitget result: {sl_legacy_result}")
            
            # Verify redirection is working
            if str(sl_result) == str(sl_legacy_result):
                logger.info("✅ Legacy method successfully redirected to main implementation")
            else:
                logger.error("❌ Legacy method not redirecting properly")
                return False
        except Exception as e:
            logger.error(f"Error testing stop loss methods: {e}")
            return False
    
    logger.info("=== TP/SL METHOD VERIFICATION TEST COMPLETED SUCCESSFULLY ===")
    return True

if __name__ == "__main__":
    logger.info("Starting TP/SL method verification test")
    result = test_tp_sl_methods()
    
    if result:
        logger.info("✅ All tests passed! The TP/SL fix is working correctly.")
        sys.exit(0)
    else:
        logger.error("❌ Test failed! The TP/SL fix is not working correctly.")
        sys.exit(1)
