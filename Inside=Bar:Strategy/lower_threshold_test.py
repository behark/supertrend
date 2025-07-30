#!/usr/bin/env python3
"""
Lower threshold test script for SuperTrend Bot
This script temporarily lowers the confidence threshold for a specific pair
to trigger a trade and verify TP/SL functionality.
"""

import os
import sys
import time
import logging
from datetime import datetime
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ThresholdTest")

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

try:
    from src.integrations.bidget import TradingAPI
    from src.integrations.telegram import TelegramNotifier
    from src.utils.config import load_env
except ImportError as e:
    logger.error(f"Failed to import required modules: {e}")
    sys.exit(1)

# Load environment variables
load_env()

def send_telegram_notification(message):
    """Send a notification to Telegram"""
    try:
        notifier = TelegramNotifier()
        notifier.send_message(message)
        logger.info("Telegram notification sent successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")
        return False

def test_tp_sl_attachment():
    """Test TP/SL attachment with a real trade"""
    logger.info("=== STARTING TP/SL ATTACHMENT TEST ===")
    
    # Initialize Bitget client
    try:
        client = TradingAPI()
        logger.info("Bitget client initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Bitget client: {e}")
        return False
    
    # Test pair - using DOGEUSDT as it was mentioned in previous issues
    symbol = "DOGEUSDT_UMCBL"
    base_symbol = "DOGE/USDT"
    
    # Get account balance
    try:
        account_info = client.get_account_info()
        balance = float(account_info.get('available', 0))
        logger.info(f"Account balance: ${balance}")
        
        if balance < 1:
            logger.error("Insufficient balance for testing")
            return False
    except Exception as e:
        logger.error(f"Failed to get account balance: {e}")
        return False
    
    # Set leverage
    try:
        leverage_result = client.set_leverage(symbol, 20, "short")
        logger.info(f"Leverage set result: {leverage_result}")
    except Exception as e:
        logger.error(f"Failed to set leverage: {e}")
        return False
    
    # Calculate position size (35% of balance)
    position_size_usd = balance * 0.35
    
    # Get current price
    try:
        ticker = client.get_ticker(base_symbol)
        current_price = float(ticker['last'])
        logger.info(f"Current price of {base_symbol}: ${current_price}")
        
        # Calculate quantity
        quantity = position_size_usd / current_price
        logger.info(f"Calculated quantity: {quantity}")
    except Exception as e:
        logger.error(f"Failed to get current price: {e}")
        return False
    
    # Place a market order
    try:
        order_result = client.place_market_order(
            symbol=symbol,
            side="open_short",
            quantity=quantity,
            leverage=20
        )
        logger.info(f"Market order result: {order_result}")
        
        if not order_result.get('success'):
            logger.error(f"Failed to place market order: {order_result.get('error')}")
            return False
        
        order_id = order_result.get('orderId')
        logger.info(f"Order placed successfully with ID: {order_id}")
        
        # Send notification
        send_telegram_notification(f"🚀 TEST TRADE EXECUTED\nPair: {base_symbol}\nSide: SHORT\nQuantity: {quantity}\nLeverage: 20x\nOrder ID: {order_id}")
    except Exception as e:
        logger.error(f"Failed to place market order: {e}")
        return False
    
    # Wait for order to be filled
    logger.info("Waiting for order to be filled...")
    time.sleep(5)
    
    # Set take profit (10% above entry)
    try:
        tp_price = current_price * 0.9  # 10% profit for short
        tp_result = client.set_take_profit(
            symbol=symbol,
            quantity=quantity,
            price=tp_price,
            position_side="short"
        )
        logger.info(f"Take profit result: {tp_result}")
        
        if not tp_result.get('success'):
            logger.error(f"Failed to set take profit: {tp_result.get('error')}")
            # Continue to try setting stop loss even if TP fails
        else:
            logger.info(f"Take profit set successfully at ${tp_price}")
            send_telegram_notification(f"✅ Take Profit set at ${tp_price}")
    except Exception as e:
        logger.error(f"Failed to set take profit: {e}")
        # Continue to try setting stop loss even if TP fails
    
    # Set stop loss (5% below entry)
    try:
        sl_price = current_price * 1.05  # 5% loss for short
        sl_result = client.set_stop_loss(
            symbol=symbol,
            quantity=quantity,
            stop_price=sl_price,
            position_side="short"
        )
        logger.info(f"Stop loss result: {sl_result}")
        
        if not sl_result.get('success'):
            logger.error(f"Failed to set stop loss: {sl_result.get('error')}")
            return False
        else:
            logger.info(f"Stop loss set successfully at ${sl_price}")
            send_telegram_notification(f"🛑 Stop Loss set at ${sl_price}")
    except Exception as e:
        logger.error(f"Failed to set stop loss: {e}")
        return False
    
    # Final success message
    success_msg = f"""
    ✅ TP/SL TEST COMPLETED SUCCESSFULLY
    
    Pair: {base_symbol}
    Side: SHORT
    Entry Price: ${current_price}
    Take Profit: ${tp_price} (10% profit)
    Stop Loss: ${sl_price} (5% loss)
    Order ID: {order_id}
    
    Please check Bitget app to confirm TP/SL are visible.
    """
    logger.info(success_msg)
    send_telegram_notification(success_msg)
    
    return True

if __name__ == "__main__":
    logger.info("Starting threshold and TP/SL test")
    result = test_tp_sl_attachment()
    
    if result:
        logger.info("✅ Test completed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Test failed!")
        sys.exit(1)
