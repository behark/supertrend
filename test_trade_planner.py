#!/usr/bin/env python3
"""
Test script for the Smart Trade Planner integration
This script tests the core functionality of the trade planner without requiring all bot dependencies
"""
import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('TradeplannerTest')

# Ensure data directories exist
os.makedirs('data/playbooks', exist_ok=True)
os.makedirs('data/trade_plans', exist_ok=True)

# Import required modules
try:
    from market_regime import MarketRegime
    from playbook import Playbook
    from trade_planner import SmartTradePlanner
    logger.info("✅ Successfully imported required modules")
except ImportError as e:
    logger.error(f"❌ Failed to import required modules: {str(e)}")
    sys.exit(1)

def generate_sample_ohlcv_data(symbol='BTC/USDT', timeframe='1h', periods=100):
    """Generate sample OHLCV data for testing"""
    logger.info(f"Generating sample OHLCV data for {symbol} on {timeframe} timeframe")
    
    # Start with a base price and generate random walks
    base_price = 28000.0
    volatility = 0.02
    
    # Generate timestamps
    now = datetime.now()
    timestamps = pd.date_range(end=now, periods=periods, freq='1H')
    
    # Generate OHLCV data
    data = []
    price = base_price
    for i in range(periods):
        # Random walk with drift
        price_change = price * np.random.normal(0, volatility)
        open_price = price
        close_price = price + price_change
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility/2)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility/2)))
        volume = abs(np.random.normal(1000, 500)) * (1 + abs(price_change/price))
        
        # Create a row
        data.append([
            timestamps[i].timestamp() * 1000,  # Timestamp in milliseconds
            open_price,
            high_price,
            low_price,
            close_price,
            volume
        ])
        
        # Update price for next iteration
        price = close_price
    
    # Create DataFrame with proper column names
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df

def test_market_regime_detection():
    """Test market regime detection functionality"""
    logger.info("Testing market regime detection...")
    
    # Generate sample data
    df = generate_sample_ohlcv_data()
    
    # Create MarketRegime instance
    regime_detector = MarketRegime()
    
    # Detect regime
    regime = regime_detector.detect_regime(df)
    
    logger.info(f"Detected market regime: {regime}")
    return regime, df

def test_playbook_system():
    """Test the playbook system functionality"""
    logger.info("Testing playbook system...")
    
    # Create Playbook instance
    playbook_manager = Playbook(data_dir='data')
    
    # List available playbooks
    playbooks = playbook_manager.list_playbooks()
    logger.info(f"Available playbooks: {playbooks}")
    
    # If no playbooks exist, create default ones
    if not playbooks:
        logger.info("Creating default playbooks...")
        
        # Define a default playbook
        default_playbook = {
            "bullish_trend": {
                "strategy": "supertrend",
                "leverage": 20,
                "stop_loss": {
                    "type": "atr",
                    "multiplier": 2.5
                },
                "take_profit_levels": [
                    {
                        "type": "fixed_r",
                        "multiplier": 1.5
                    },
                    {
                        "type": "fixed_r",
                        "multiplier": 3.0
                    }
                ],
                "entry_type": "breakout",
                "risk_level": "moderate",
                "filters": {
                    "min_volume": 1000000,
                    "min_volatility": 1.5
                }
            }
        }
        
        # Add the default playbook
        playbook_manager.save_playbook('default_playbooks', default_playbook)
        playbooks = playbook_manager.list_playbooks()
        logger.info(f"Created default playbook. Available playbooks: {playbooks}")
    
    # Get a playbook by name
    if playbooks:
        # Get the first playbook name from the dictionary keys
        first_playbook_name = next(iter(playbooks))
        logger.info(f"Getting playbook details for: {first_playbook_name}")
        playbook = playbooks[first_playbook_name]
        logger.info(f"Playbook contents: {json.dumps(playbook, indent=2)}")
    
    return playbook_manager

def test_trade_planner(regime=None, df=None):
    """Test the Smart Trade Planner functionality"""
    logger.info("Testing Smart Trade Planner...")
    
    # Generate data if not provided
    if df is None:
        df = generate_sample_ohlcv_data()
    
    # Create trade planner
    trade_planner = SmartTradePlanner(data_dir='data')
    
    # Plan a trade
    position_type = 'long'
    entry_price = df['close'].iloc[-1]
    symbol = 'BTC/USDT'
    timeframe = '1h'
    
    logger.info(f"Planning a {position_type} trade for {symbol} at price {entry_price:.2f}")
    
    # Plan trade with optional regime override
    trade_plan = trade_planner.plan_trade(
        df=df,
        entry_price=entry_price,
        symbol=symbol,
        timeframe=timeframe,
        position_type=position_type,
        override_regime=regime
    )
    
    # Display the trade plan
    logger.info("Generated trade plan:")
    logger.info(json.dumps(trade_plan, indent=2))
    
    # Format the trade plan as a message
    message = trade_planner.format_trade_plan_message(trade_plan)
    logger.info("\nFormatted trade plan message:")
    logger.info(message)
    
    # Save the trade plan
    saved_path = trade_planner.save_trade_plan(trade_plan)
    logger.info(f"Saved trade plan to: {saved_path}")
    
    return trade_planner, trade_plan

def main():
    """Main test function"""
    logger.info("Starting Smart Trade Planner integration test")
    
    try:
        # Test market regime detection
        regime, df = test_market_regime_detection()
        
        # Test playbook system
        playbook_manager = test_playbook_system()
        
        # Test trade planner with detected regime
        trade_planner, trade_plan = test_trade_planner(regime, df)
        
        logger.info("✅ All tests completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
