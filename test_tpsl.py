#!/usr/bin/env python
"""
Test script to verify TP/SL order placement fixes
"""

import os
import sys
import logging
import time
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TPSL-Test")

# Add project path
sys.path.append('/home/behar/CascadeProjects/SuperTrend/Inside=Bar:Strategy')

# Set environment variables for testing
os.environ['TEST_MODE'] = 'true'  # Use test mode
os.environ['BITGET_API_KEY'] = 'test_key'
os.environ['BITGET_API_SECRET'] = 'test_secret'
os.environ['BITGET_API_PASSPHRASE'] = 'test_passphrase'

# Import after setting environment variables
from src.integrations.bidget import TradingAPI
from src.integrations.order_manager import OrderManager

class TPSLTester:
    """Test class for TP/SL functionality"""
    
    def __init__(self):
        """Initialize the tester"""
        self.api = TradingAPI()
        self.order_manager = OrderManager(self.api)
        logger.info(f"API Configured: {self.api.is_configured}")
        logger.info(f"Test Mode: {self.api.test_mode}")
        
    def test_place_order_with_tpsl(self):
        """Test placing an order with TP/SL"""
        symbol = "BTC/USDT"
        direction = "LONG"
        quantity = 0.001
        take_profit = 40000.0  # Example TP price
        stop_loss = 38000.0    # Example SL price
        
        logger.info(f"Testing order placement with TP/SL for {symbol}")
        
        # Mock the API responses for testing
        self._mock_api_responses()
        
        # Place the order with TP/SL
        result = self.order_manager.place_main_order_with_tpsl(
            symbol=symbol,
            direction=direction,
            quantity=quantity,
            entry_price=None,  # Market order
            take_profit=take_profit,
            stop_loss=stop_loss
        )
        
        # Verify the results
        logger.info("Order Result:")
        logger.info(f"Main Order: {result.get('main_order', {}).get('orderId', 'N/A')}")
        logger.info(f"TP Order: {result.get('take_profit_order', {}).get('orderId', 'N/A')}")
        logger.info(f"SL Order: {result.get('stop_loss_order', {}).get('orderId', 'N/A')}")
        
        # Check if TP/SL orders were placed successfully
        tp_success = 'error' not in result.get('take_profit_order', {'error': 'Not placed'})
        sl_success = 'error' not in result.get('stop_loss_order', {'error': 'Not placed'})
        
        logger.info(f"TP Order Success: {tp_success}")
        logger.info(f"SL Order Success: {sl_success}")
        
        return tp_success and sl_success
    
    def _mock_api_responses(self):
        """Mock API responses for testing"""
        # Override the API methods with mock implementations
        
        # Mock place_order
        def mock_place_order(*args, **kwargs):
            logger.info(f"Mock place_order called with: {kwargs}")
            return {
                "orderId": "mock_order_123",
                "status": "placed",
                "price": kwargs.get('price', 0)
            }
        self.api.place_order = mock_place_order
        
        # Mock get_position
        def mock_get_position(*args, **kwargs):
            logger.info(f"Mock get_position called with: {args}")
            return {
                "size": 0.001,
                "holdSide": "long",
                "entryPrice": 39000.0,
                "unrealizedPL": 0,
                "margin": 0.001 * 39000.0 / 20  # Assuming 20x leverage
            }
        self.api.get_position = mock_get_position
        
        # Mock set_take_profit
        def mock_set_take_profit(*args, **kwargs):
            logger.info(f"Mock set_take_profit called with: {kwargs}")
            # Verify the holdSide parameter is present
            if 'position_side' in kwargs:
                logger.info(f"✅ holdSide parameter correctly passed: {kwargs['position_side']}")
                return {
                    "orderId": "mock_tp_123",
                    "status": "placed",
                    "type": "take_profit",
                    "price": kwargs.get('price', 0)
                }
            else:
                logger.error("❌ holdSide parameter missing!")
                return {"error": "holdSide parameter missing"}
        self.api.set_take_profit = mock_set_take_profit
        
        # Mock set_stop_loss
        def mock_set_stop_loss(*args, **kwargs):
            logger.info(f"Mock set_stop_loss called with: {kwargs}")
            # Verify the holdSide parameter is present
            if 'position_side' in kwargs:
                logger.info(f"✅ holdSide parameter correctly passed: {kwargs['position_side']}")
                return {
                    "orderId": "mock_sl_123",
                    "status": "placed",
                    "type": "stop_loss",
                    "price": kwargs.get('stop_price', 0)
                }
            else:
                logger.error("❌ holdSide parameter missing!")
                return {"error": "holdSide parameter missing"}
        self.api.set_stop_loss = mock_set_stop_loss

def main():
    """Main function"""
    logger.info("Starting TP/SL test")
    tester = TPSLTester()
    success = tester.test_place_order_with_tpsl()
    
    if success:
        logger.info("✅ TEST PASSED: TP/SL orders placed successfully with correct holdSide parameter")
    else:
        logger.error("❌ TEST FAILED: TP/SL orders not placed correctly")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
