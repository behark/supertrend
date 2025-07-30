#!/usr/bin/env python3
"""
Test script to verify live trading functionality
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Add src to path
sys.path.append('src')

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_connection():
    """Test API connection and basic functionality"""
    try:
        from integrations.bidget import TradingAPI
        
        logger.info("🔧 Testing API Connection...")
        api = TradingAPI()
        
        # Check if API is configured
        if not api.is_configured:
            logger.error("❌ API not configured - missing credentials")
            return False
            
        logger.info(f"✅ API configured - Test mode: {api.test_mode}")
        
        # Test account info
        logger.info("📊 Testing account info...")
        account_info = api.get_account_info()
        
        if 'error' in account_info:
            logger.error(f"❌ Account info failed: {account_info['error']}")
            return False
        else:
            logger.info(f"✅ Account info successful: Balance = ${account_info.get('available_balance', 0):.2f}")
            
        # Test market data
        logger.info("📈 Testing market data...")
        market_data = api.get_market_data("BTC/USDT")
        
        if 'error' in market_data:
            logger.error(f"❌ Market data failed: {market_data['error']}")
        else:
            logger.info(f"✅ Market data successful: BTC price = ${market_data.get('price', 0):.2f}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ API test failed: {e}")
        return False

def test_signal_generation():
    """Test signal generation system"""
    try:
        from bot import TradingBot
        
        logger.info("🎯 Testing signal generation...")
        
        # Create bot instance
        bot = TradingBot()
        
        # Test signal generation for a popular pair
        test_symbol = "BTC/USDT"
        logger.info(f"📊 Generating signals for {test_symbol}...")
        
        # This would normally be called by the bot's main loop
        signals = bot.generate_signals([test_symbol])
        
        if signals:
            logger.info(f"✅ Signal generation successful: {len(signals)} signals generated")
            for signal in signals:
                logger.info(f"   📈 {signal.get('symbol', 'Unknown')}: {signal.get('action', 'Unknown')} - Confidence: {signal.get('confidence', 0):.1f}%")
        else:
            logger.info("ℹ️  No signals generated (normal if no valid setups)")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Signal generation test failed: {e}")
        return False

def test_telegram_integration():
    """Test Telegram integration"""
    try:
        from integrations.telegram_commands import TelegramBot
        
        logger.info("🤖 Testing Telegram integration...")
        
        # Check if Telegram is configured
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not telegram_token:
            logger.error("❌ Telegram not configured - missing bot token")
            return False
            
        logger.info("✅ Telegram bot token configured")
        
        # Test forecast functionality
        from analytics.pattern_matcher import PatternMatcher
        pattern_matcher = PatternMatcher()
        
        forecast = pattern_matcher.get_forecast("BTCUSDT", "1h")
        if forecast:
            logger.info("✅ Forecast generation successful")
            logger.info(f"   📊 Forecast preview: {forecast[:100]}...")
        else:
            logger.warning("⚠️  Forecast generation returned empty result")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Telegram integration test failed: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🚀 Starting SuperTrend Live Trading Tests...")
    logger.info("=" * 60)
    
    tests = [
        ("API Connection", test_api_connection),
        ("Signal Generation", test_signal_generation),
        ("Telegram Integration", test_telegram_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 Running {test_name} Test...")
        logger.info("-" * 40)
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("🏁 TEST RESULTS SUMMARY")
    logger.info("=" * 60)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - SuperTrend bot is ready for live trading!")
    else:
        logger.warning("⚠️  Some tests failed - please check the issues above")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
