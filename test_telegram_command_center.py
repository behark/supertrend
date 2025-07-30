#!/usr/bin/env python3
"""
Test Telegram Command Center
This script tests the Telegram Command Center functionality
"""
import os
import sys
import time
import logging
import threading
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/telegram_test.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('telegram_test')

def setup_environment():
    """Ensure the necessary directories and files exist"""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Create state directory if it doesn't exist
    os.makedirs("state", exist_ok=True)
    
    # Create config directory if it doesn't exist
    os.makedirs("config", exist_ok=True)
    
    # Load environment variables
    load_dotenv()
    load_dotenv('.env_telegram')
    
    # Check for Telegram bot token
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        return False
    
    # Check for authorized users
    authorized_users = os.getenv('TELEGRAM_AUTHORIZED_USERS')
    if not authorized_users:
        logger.warning("TELEGRAM_AUTHORIZED_USERS not found in environment variables")
        logger.warning("Command Center will not authorize any users")
    
    return True

def test_bot_telegram_integration():
    """Test the bot_telegram_integration module"""
    try:
        logger.info("Testing bot_telegram_integration module...")
        
        # Import the module
        import bot_telegram_integration as bti
        
        # Test state functions
        logger.info(f"Current mode: {bti.get_trade_mode()}")
        logger.info(f"Current risk level: {bti.get_risk_level()}")
        logger.info(f"Paused: {bti.get_pause_state()}")
        logger.info(f"Daily trades: {bti.get_daily_trade_count()}")
        logger.info(f"Daily signals: {bti.get_daily_signal_count()}")
        logger.info(f"Bot uptime: {bti.get_bot_uptime()}")
        
        # Test setting values
        logger.info("Testing state modification functions...")
        
        # Save original values
        original_mode = bti.get_trade_mode()
        original_risk = bti.get_risk_level()
        original_paused = bti.get_pause_state()
        
        # Test mode change
        bti.set_trade_mode('debug')
        assert bti.get_trade_mode() == 'debug', "Mode change failed"
        logger.info("Mode change test passed")
        
        # Test risk change
        bti.set_risk_level('low')
        assert bti.get_risk_level() == 'low', "Risk change failed"
        logger.info("Risk change test passed")
        
        # Test pause state
        bti.set_pause_state(True)
        assert bti.get_pause_state() is True, "Pause state change failed"
        logger.info("Pause state change test passed")
        
        # Test counter functions
        original_trades = bti.get_daily_trade_count()
        original_signals = bti.get_daily_signal_count()
        
        bti.increment_daily_trades()
        assert bti.get_daily_trade_count() == original_trades + 1, "Trade increment failed"
        logger.info("Trade increment test passed")
        
        bti.increment_daily_signals(confidence=0.96)  # High confidence signal
        assert bti.get_daily_signal_count() == original_signals + 1, "Signal increment failed"
        assert bti.get_high_confidence_count() == bti.BOT_STATE['high_confidence_signals'], "High confidence count failed"
        logger.info("Signal increment test passed")
        
        # Reset counters
        bti.reset_daily_counters()
        assert bti.get_daily_trade_count() == 0, "Counter reset failed"
        assert bti.get_daily_signal_count() == 0, "Counter reset failed"
        logger.info("Counter reset test passed")
        
        # Restore original values
        bti.set_trade_mode(original_mode)
        bti.set_risk_level(original_risk)
        bti.set_pause_state(original_paused)
        
        logger.info("bot_telegram_integration tests passed")
        return True
    except Exception as e:
        logger.error(f"Error testing bot_telegram_integration: {e}")
        return False

def test_command_integration():
    """Test the telegram_command_integration module"""
    try:
        logger.info("Testing telegram_command_integration module...")
        
        # Import the module
        from telegram_command_integration import integrate_command_center
        
        # Test integration (without starting the bot)
        integration_result = integrate_command_center()
        logger.info(f"Integration result: {integration_result}")
        
        logger.info("telegram_command_integration tests passed")
        return integration_result
    except Exception as e:
        logger.error(f"Error testing telegram_command_integration: {e}")
        return False

def test_full_command_center():
    """Test the full command center with a real Telegram bot"""
    try:
        logger.info("Testing full command center...")
        
        # Import the necessary modules
        import bot_telegram_integration as bti
        
        # Initialize the command center
        if not bti.initialize_telegram_integration():
            logger.error("Failed to initialize Telegram Command Center")
            return False
        
        logger.info("Command center started successfully")
        logger.info("Press Ctrl+C to stop the test")
        
        # Keep the test running
        try:
            while True:
                # Update some values to demonstrate state changes
                current_mode = bti.get_trade_mode()
                new_mode = 'debug' if current_mode == 'scan' else 'scan'
                bti.set_trade_mode(new_mode)
                logger.info(f"Changed mode to {new_mode}")
                
                # Sleep for a while
                time.sleep(60)
                
                # Add a signal and a trade
                bti.increment_daily_signals(confidence=0.99)  # Elite signal
                logger.info("Added an elite signal")
                
                # Sleep again
                time.sleep(60)
        except KeyboardInterrupt:
            # Shutdown the command center
            bti.shutdown_telegram_integration()
            logger.info("Test stopped by user")
        
        return True
    except Exception as e:
        logger.error(f"Error testing full command center: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Telegram Command Center Test")
    print("-------------------------------")
    
    # Setup environment
    if not setup_environment():
        print("❌ Environment setup failed")
        return
    
    print("✅ Environment setup successful")
    
    # Test each component
    print("\n🧪 Testing bot integration module...")
    if test_bot_telegram_integration():
        print("✅ Bot integration module tests passed")
    else:
        print("❌ Bot integration module tests failed")
        return
    
    print("\n🧪 Testing command integration module...")
    if test_command_integration():
        print("✅ Command integration module tests passed")
    else:
        print("❌ Command integration module tests failed")
        return
    
    # Ask if the user wants to run the full test
    response = input("\nDo you want to test the full command center with a live Telegram bot? (y/n): ")
    if response.lower() == 'y':
        print("\n🧪 Starting full command center test...")
        print("Send commands to your bot and observe the responses")
        print("Press Ctrl+C to stop the test")
        
        test_full_command_center()
    else:
        print("\n⏭️ Skipping full command center test")
    
    print("\n✅ All tests completed")

if __name__ == "__main__":
    main()
