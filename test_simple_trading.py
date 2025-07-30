#!/usr/bin/env python3
"""
Simple test script to verify live trading functionality without recursive initialization
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
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_credentials():
    """Test if API credentials are properly configured"""
    logger.info("🔑 Testing API Credentials...")
    
    api_key = os.getenv('BITGET_API_KEY')
    api_secret = os.getenv('BITGET_API_SECRET')
    api_passphrase = os.getenv('BITGET_API_PASSPHRASE')
    
    if not api_key:
        logger.error("❌ BITGET_API_KEY not found")
        return False
    if not api_secret:
        logger.error("❌ BITGET_API_SECRET not found")
        return False
    if not api_passphrase:
        logger.error("❌ BITGET_API_PASSPHRASE not found")
        return False
        
    logger.info(f"✅ API Key: {api_key[:8]}...")
    logger.info(f"✅ API Secret: {api_secret[:8]}...")
    logger.info(f"✅ API Passphrase: {api_passphrase[:4]}...")
    return True

def test_api_connection():
    """Test basic API connection without health checks"""
    logger.info("🌐 Testing API Connection...")
    
    try:
        from integrations.bidget import TradingAPI
        
        # Create API instance
        api = TradingAPI()
        
        if not api.is_configured:
            logger.error("❌ API not configured")
            return False
            
        logger.info(f"✅ API configured - Test mode: {api.test_mode}")
        
        # Test simple market data call (doesn't require authentication)
        logger.info("📊 Testing market data...")
        market_data = api.get_market_data("BTC/USDT")
        
        if 'error' in market_data:
            logger.warning(f"⚠️  Market data warning: {market_data['error']}")
        else:
            price = market_data.get('price', 0)
            logger.info(f"✅ Market data successful: BTC price = ${price:.2f}")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ API connection test failed: {e}")
        return False

def test_telegram_config():
    """Test Telegram configuration"""
    logger.info("🤖 Testing Telegram Configuration...")
    
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_token:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found")
        return False
    if not telegram_chat_id:
        logger.error("❌ TELEGRAM_CHAT_ID not found")
        return False
        
    logger.info(f"✅ Telegram Token: {telegram_token[:10]}...")
    logger.info(f"✅ Chat ID: {telegram_chat_id}")
    return True

def test_pattern_matcher():
    """Test pattern matching system"""
    logger.info("🎯 Testing Pattern Matcher...")
    
    try:
        from analytics.pattern_matcher import PatternMatcher
        
        pattern_matcher = PatternMatcher()
        
        # Test forecast generation
        logger.info("📈 Generating forecast for BTCUSDT 1h...")
        forecast = pattern_matcher.get_forecast("BTCUSDT", "1h")
        
        if forecast:
            logger.info("✅ Pattern matcher working - forecast generated")
            logger.info(f"   📊 Forecast preview: {forecast[:150]}...")
            return True
        else:
            logger.warning("⚠️  Pattern matcher returned empty forecast")
            return False
            
    except Exception as e:
        logger.error(f"❌ Pattern matcher test failed: {e}")
        return False

def test_trading_parameters():
    """Test trading parameters configuration"""
    logger.info("⚙️  Testing Trading Parameters...")
    
    max_signals = os.getenv('MAX_SIGNALS_PER_DAY', '100')
    max_trades = os.getenv('MAX_TRADES_PER_DAY', '15')
    confidence_threshold = os.getenv('CONFIDENCE_THRESHOLD', '95')
    test_mode = os.getenv('TEST_MODE', 'false')
    
    logger.info(f"✅ Max signals per day: {max_signals}")
    logger.info(f"✅ Max trades per day: {max_trades}")
    logger.info(f"✅ Confidence threshold: {confidence_threshold}%")
    logger.info(f"✅ Test mode: {test_mode}")
    
    # Check if we're in live mode
    if test_mode.lower() == 'false':
        logger.info("💰 CONFIRMED: Running in LIVE MODE")
    else:
        logger.info("🧪 Running in TEST MODE")
        
    return True

def main():
    """Run simplified tests"""
    logger.info("🚀 SuperTrend Live Trading Verification")
    logger.info("=" * 50)
    
    tests = [
        ("API Credentials", test_api_credentials),
        ("API Connection", test_api_connection),
        ("Telegram Config", test_telegram_config),
        ("Pattern Matcher", test_pattern_matcher),
        ("Trading Parameters", test_trading_parameters)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 {test_name}...")
        logger.info("-" * 30)
        
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("🏁 VERIFICATION RESULTS")
    logger.info("=" * 50)
    
    passed = 0
    total = len(tests)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 ALL SYSTEMS GO - SuperTrend bot ready for live trading!")
        logger.info("💎 The consciousness is alive and ready to trade!")
    elif passed >= 3:
        logger.info("⚠️  Most systems operational - minor issues detected")
        logger.info("🌙 Bot can run but may have limited functionality")
    else:
        logger.warning("❌ Critical issues detected - please review configuration")
    
    return passed >= 3

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
