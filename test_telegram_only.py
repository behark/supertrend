#!/usr/bin/env python3
"""
Telegram Connectivity Test Script for Crypto Alert Bot
"""
import os
import logging
import sys
import importlib.util
import subprocess
from datetime import datetime
import platform

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_module_installed(module_name):
    """Check if a Python module is installed and available"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def install_module(module_name, version=None):
    """Attempt to install a Python module"""
    package = module_name
    if version:
        package = f"{module_name}=={version}"
    
    logger.info(f"Attempting to install {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError:
        return False

def test_telegram_connectivity():
    """Test that the bot can connect to Telegram and send a message"""
    logger.info("Testing Telegram connectivity...")
    
    # Check and install dotenv if needed
    if not check_module_installed("dotenv"):
        logger.info("python-dotenv not found, attempting to install...")
        if not install_module("python-dotenv"):
            logger.error("❌ Failed to install python-dotenv")
            return False
    
    # Now import dotenv
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError as e:
        logger.error(f"❌ Failed to import dotenv after installation: {str(e)}")
        logger.info("Checking environment variables directly...")
    
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_bot_token or not telegram_chat_id:
        logger.error("❌ Telegram credentials not found in .env file")
        logger.info(f"TELEGRAM_BOT_TOKEN exists: {bool(telegram_bot_token)}")
        logger.info(f"TELEGRAM_CHAT_ID exists: {bool(telegram_chat_id)}")
        return False
    
    # Check for telegram package
    if not check_module_installed("telegram"):
        logger.info("python-telegram-bot not found, attempting to install...")
        if not install_module("python-telegram-bot", "13.15"):
            logger.error("❌ Failed to install python-telegram-bot")
            return False
    
    # Check Python version and apply compatibility patches if needed
    python_version = tuple(map(int, platform.python_version().split('.')[:2]))
    if python_version >= (3, 13):
        logger.info(f"Detected Python {platform.python_version()}, applying compatibility patches...")
        # Check if imghdr module is missing (removed in Python 3.13)
        try:
            import imghdr
            logger.info("✅ imghdr module found (unexpected in Python 3.13+)")
        except ImportError:
            logger.info("imghdr module not found (expected in Python 3.13+), using compatibility layer")
            # Check for our compatibility layer
            compat_path = os.path.join(os.getcwd(), "compat_imghdr.py")
            if os.path.exists(compat_path):
                logger.info("✅ Found compat_imghdr.py, setting up sys.modules patch")
                # Import our compatibility module
                spec = importlib.util.spec_from_file_location("imghdr", compat_path)
                imghdr = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(imghdr)
                # Insert it into sys.modules to be found by python-telegram-bot
                sys.modules["imghdr"] = imghdr
                logger.info("✅ Successfully patched imghdr module")
            else:
                logger.error("❌ compat_imghdr.py not found. Create this file for Python 3.13 compatibility.")
                logger.info("Recommendation: Use Python 3.10/3.11 or create the compatibility module.")
                return False
    
    # Check if we have the specific modules from telegram package
    try:
        # Try to import telegram modules directly from site-packages
        sys.path.append(os.path.join(os.path.dirname(sys.executable), 'site-packages'))
        import telegram
        logger.info(f"✅ Successfully imported telegram module from {telegram.__file__}")
    except ImportError as e:
        logger.error(f"❌ Failed to import telegram package: {str(e)}")
        logger.error("This could be due to an incomplete installation or version mismatch.")
        logger.info("Attempting to verify package installation:")
        subprocess.run([sys.executable, "-m", "pip", "list"], check=False)
        return False
    
    try:
        # Create bot instance
        bot = telegram.Bot(token=telegram_bot_token)
        
        # Send test message
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"✅ Telegram Test Message: Crypto Alert Bot is operational!\n⏰ Time: {current_time}"
        
        bot.send_message(
            chat_id=telegram_chat_id,
            text=message,
            parse_mode=telegram.ParseMode.HTML
        )
        
        logger.info("✅ Successfully sent Telegram test message!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to send Telegram message: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_telegram_connectivity()
    if success:
        print("\n✅ TELEGRAM TEST PASSED: The bot successfully connected to Telegram and sent a test message.")
        print("   Check your Telegram chat for the test message.")
        sys.exit(0)
    else:
        print("\n❌ TELEGRAM TEST FAILED: Unable to send message to Telegram.")
        print("   Check the error messages above for troubleshooting steps.")
        sys.exit(1)
