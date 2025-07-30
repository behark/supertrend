#!/usr/bin/env python3
"""
Debug script for crypto-alert-bot service
This script helps diagnose any issues with the bot startup
"""
import os
import sys
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/behar/CascadeProjects/crypto-alert-bot/debug.log')
    ]
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    optional_vars = [
        'BYBIT_API_KEY',
        'BYBIT_API_SECRET',
        'BYBIT_SANDBOX'
    ]
    
    logger.info("=== Environment Variables Check ===")
    all_required_present = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var} is set")
        else:
            logger.error(f"❌ {var} is NOT set")
            all_required_present = False
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var} is set")
        else:
            logger.info(f"ℹ️ {var} is not set (optional)")
    
    return all_required_present

def check_telegram():
    """Test Telegram messaging"""
    try:
        sys.path.insert(0, '.')
        from telegram_client import TelegramClient
        
        # Apply imghdr patch if needed
        try:
            import imghdr
            logger.info("✅ Native imghdr module found")
        except ImportError:
            logger.warning("⚠️ Native imghdr module not found, applying compatibility patch...")
            class ImghdrShim:
                def what(self, *args, **kwargs):
                    return None
            sys.modules['imghdr'] = ImghdrShim()
            logger.info("✅ Successfully patched imghdr module")
        
        telegram_client = TelegramClient(
            os.getenv('TELEGRAM_BOT_TOKEN'),
            os.getenv('TELEGRAM_CHAT_ID')
        )
        
        message = (
            "🔍 *SERVICE DEBUG TEST*\n\n"
            "This is a test message to verify that the bot can send Telegram alerts\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"User: {os.getenv('USER')}"
        )
        
        telegram_client.send_message(message)
        logger.info("✅ Telegram test message sent successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Telegram test failed: {str(e)}")
        return False

def check_bybit():
    """Test BYBIT API connection"""
    try:
        sys.path.insert(0, '.')
        from bybit_trader import get_bybit_exchange
        
        exchange = get_bybit_exchange()
        if exchange:
            logger.info("✅ BYBIT connection successful")
            return True
        else:
            logger.error("❌ BYBIT connection failed")
            return False
    except Exception as e:
        logger.error(f"❌ BYBIT test failed: {str(e)}")
        return False

def check_files():
    """Check if all required files exist"""
    required_files = [
        '/home/behar/CascadeProjects/crypto-alert-bot/run_with_bybit.py',
        '/home/behar/CascadeProjects/crypto-alert-bot/bot.py',
        '/home/behar/CascadeProjects/crypto-alert-bot/bybit_trader.py',
        '/home/behar/CascadeProjects/crypto-alert-bot/config.py',
        '/home/behar/CascadeProjects/crypto-alert-bot/telegram_client.py',
        '/home/behar/CascadeProjects/crypto-alert-bot/.env',
        '/home/behar/CascadeProjects/crypto-alert-bot/.env_bybit'
    ]
    
    logger.info("=== Required Files Check ===")
    all_files_present = True
    
    for file_path in required_files:
        if os.path.exists(file_path):
            logger.info(f"✅ {file_path} exists")
        else:
            logger.error(f"❌ {file_path} does NOT exist")
            all_files_present = False
    
    return all_files_present

def main():
    """Run all diagnostic checks"""
    logger.info("Starting crypto-alert-bot service diagnostics")
    logger.info(f"Current directory: {os.getcwd()}")
    logger.info(f"Python version: {sys.version}")
    
    # Check environment variables
    env_ok = check_environment()
    
    # Check required files
    files_ok = check_files()
    
    # Check Telegram
    telegram_ok = check_telegram()
    
    # Check BYBIT
    bybit_ok = check_bybit()
    
    # Summary
    logger.info("\n=== Diagnostic Summary ===")
    logger.info(f"Environment variables: {'✅ OK' if env_ok else '❌ FAILED'}")
    logger.info(f"Required files: {'✅ OK' if files_ok else '❌ FAILED'}")
    logger.info(f"Telegram connection: {'✅ OK' if telegram_ok else '❌ FAILED'}")
    logger.info(f"BYBIT connection: {'✅ OK' if bybit_ok else '❌ FAILED'}")
    
    if all([env_ok, files_ok, telegram_ok, bybit_ok]):
        logger.info("\n✅ All diagnostics PASSED. Service should work correctly.")
    else:
        logger.error("\n❌ Some diagnostics FAILED. Please fix the issues above.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Error in diagnostics: {str(e)}")
        sys.exit(1)
