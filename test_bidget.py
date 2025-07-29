#!/usr/bin/env python3
"""
Test script to verify Trading API integration (Bidget API with Binance fallback)
"""

import os
import logging
import json
from dotenv import load_dotenv
from src.integrations.bidget import TradingAPI
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def main():
    """Test Trading API integration"""
    # Load environment variables
    load_dotenv()
    
    logger.info("Testing Trading API integration...")
    
    # Initialize Trading API client
    api = TradingAPI()
    
    if not api.is_configured:
        logger.error("Trading API is not properly configured. Check your .env file.")
        return
    
    try:
        # Get market data for BTC/USDT
        logger.info("Fetching market data for BTC/USDT...")
        market_data = api.get_market_data("BTC/USDT")
        
        if "error" in market_data:
            logger.warning(f"Error getting market data: {market_data['error']}")
        else:
            logger.info("Market data retrieved successfully!")
            # Pretty print a subset of the data to avoid flooding logs
            if isinstance(market_data, list) and len(market_data) > 0:
                # For Binance which returns a list of tickers
                market_item = next((item for item in market_data if item.get('symbol') == 'BTCUSDT'), market_data[0])
                logger.info(f"BTC/USDT price: ${float(market_item.get('lastPrice', 0)):,.2f}")
            elif isinstance(market_data, dict):
                # For single ticker response
                logger.info(f"BTC/USDT data: {json.dumps(market_data, indent=2)[:500]}...")
        
        # Try to get account info (this will likely fail with demo keys)
        logger.info("Attempting to fetch account information...")
        try:
            account_info = api.get_account_info()
            if "error" in account_info:
                logger.warning(f"Could not get account info (expected with demo keys): {account_info['error']}")
            else:
                logger.info(f"Account info: {json.dumps(account_info, indent=2)[:500]}...")
        except Exception as e:
            logger.warning(f"Expected error getting account info with demo keys: {e}")
        
        logger.info("Trading API test completed!")
        
    except Exception as e:
        logger.error(f"Error testing Trading API: {e}", exc_info=True)

if __name__ == "__main__":
    main()
