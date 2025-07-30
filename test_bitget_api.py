#!/usr/bin/env python3
"""
Bitget API Integration Test Script
This script tests the core functionality of the Bitget API integration:
1. API connectivity and authentication
2. Market data retrieval and price accuracy
3. Order placement simulation
"""

import os
import sys
import logging
import time
from typing import Dict, List
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("bitget_test")

# Import the TradingAPI class from our module
from src.integrations.bidget import TradingAPI
from src.integrations.telegram import TelegramNotifier

def test_account_info(integration: TradingAPI) -> bool:
    """Test retrieving account information"""
    logger.info("Testing account information retrieval...")
    try:
        account_info = integration.get_account_info()
        if 'error' in account_info:
            logger.error(f"Failed to get account info: {account_info['error']}")
            return False
        
        logger.info(f"Account info: {account_info}")
        return True
    except Exception as e:
        logger.error(f"Exception during account info test: {e}")
        return False

def test_market_data(integration: TradingAPI, symbols: List[str]) -> bool:
    """Test market data retrieval for multiple symbols"""
    logger.info("Testing market data retrieval...")
    success = True
    
    for symbol in symbols:
        try:
            logger.info(f"Getting market data for {symbol}")
            market_data = integration.get_market_data(symbol)
            
            if 'error' in market_data:
                logger.error(f"Failed to get market data for {symbol}: {market_data['error']}")
                success = False
                continue
            
            last_price = market_data.get('last_price')
            if not last_price:
                logger.error(f"No price returned for {symbol}")
                success = False
                continue
                
            logger.info(f"{symbol} last price: {last_price}")
        except Exception as e:
            logger.error(f"Exception during market data test for {symbol}: {e}")
            success = False
            
    return success

def test_order_placement_simulation(integration: TradingAPI, symbol: str) -> bool:
    """Test order placement in test mode"""
    logger.info(f"Testing order placement simulation for {symbol}...")
    try:
        # Force test mode
        integration.test_mode = True
        
        # Test a buy order with automatic position sizing
        buy_result = integration.place_order(symbol, 'buy')
        if 'error' in buy_result:
            logger.error(f"Error in buy order simulation: {buy_result['error']}")
            return False
            
        logger.info(f"Buy order simulation result: {buy_result}")
        
        # Test a sell order with specific quantity
        sell_result = integration.place_order(symbol, 'sell', 0.01)
        if 'error' in sell_result:
            logger.error(f"Error in sell order simulation: {sell_result['error']}")
            return False
            
        logger.info(f"Sell order simulation result: {sell_result}")
        
        return True
    except Exception as e:
        logger.error(f"Exception during order placement test: {e}")
        return False

def test_signal_execution_simulation(integration: TradingAPI, symbol: str) -> bool:
    """Test signal execution in test mode"""
    logger.info(f"Testing signal execution simulation for {symbol}...")
    try:
        # Create a test signal
        signal = {
            'symbol': symbol,
            'direction': 'LONG',
            'price': None,  # Market order
            'stop_loss': 25000.0,  # Example stop loss
            'take_profit': 35000.0,  # Example take profit
            'win_probability': 95.5
        }
        
        # Force test mode
        integration.test_mode = True
        
        # Execute the signal
        result = integration.execute_signal(signal)
        
        logger.info(f"Signal execution result: {result}")
        
        if result.get('success') is not True:
            logger.error(f"Signal execution simulation failed: {result.get('error', 'Unknown error')}")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Exception during signal execution test: {e}")
        return False

def run_tests():
    """Run all API tests"""
    logger.info("Starting Bitget API integration tests...")
    
    # Load environment variables
    load_dotenv()
    
    # Test symbols
    symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    
    # Create integration instance
    bitget = TradingAPI()
    
    # Initialize Telegram notifier for notifications
    telegram = TelegramNotifier()
    
    # Track test results
    all_tests_passed = True
    
    # Test 1: API connectivity via account info
    if not test_account_info(bitget):
        logger.error("❌ Account info test FAILED")
        all_tests_passed = False
    else:
        logger.info("✅ Account info test PASSED")
    
    # Test 2: Market data retrieval
    if not test_market_data(bitget, symbols):
        logger.error("❌ Market data test FAILED")
        all_tests_passed = False
    else:
        logger.info("✅ Market data test PASSED")
    
    # Test 3: Order placement simulation
    if not test_order_placement_simulation(bitget, symbols[0]):
        logger.error("❌ Order placement simulation test FAILED")
        all_tests_passed = False
    else:
        logger.info("✅ Order placement simulation test PASSED")
    
    # Test 4: Signal execution simulation
    if not test_signal_execution_simulation(bitget, symbols[0]):
        logger.error("❌ Signal execution simulation test FAILED")
        all_tests_passed = False
    else:
        logger.info("✅ Signal execution simulation test PASSED")
    
    # Final results
    if all_tests_passed:
        message = "🎉 All Bitget API integration tests PASSED! Ready for 24/7 operation."
        logger.info(message)
        telegram.send_message(message)
    else:
        message = "⚠️ Some Bitget API integration tests FAILED. Please check logs."
        logger.error(message)
        telegram.send_message(message)
    
    return all_tests_passed

if __name__ == "__main__":
    run_tests()
