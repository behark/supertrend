"""
Telegram Client module for the Crypto Alert Bot
Handles sending messages to Telegram channels/chats
"""
import os
import uuid
import atexit
import logging
import sys
import time
from datetime import datetime

# Apply imghdr patch for Python 3.13+ (must happen before telegram import)
def patch_imghdr():
    """Patch the imghdr module for Python 3.13+ compatibility"""
    try:
        import imghdr
        return True  # Native module exists, no patch needed
    except ImportError:
        sys.path.insert(0, '.')
        import compat_imghdr
        sys.modules['imghdr'] = compat_imghdr
        return True

# Apply the patch immediately
try:
    import imghdr
except ImportError:
    patch_imghdr()

from telegram import Bot, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

class TelegramClient:
    """Client for sending messages to Telegram."""
    
    # Class-level lock file path
    LOCK_FILE = "/tmp/crypto_alert_bot_telegram.lock"
    
    @staticmethod
    def is_another_instance_running():
        """Check if another instance is already running by testing the lock file"""
        try:
            if os.path.exists(TelegramClient.LOCK_FILE):
                with open(TelegramClient.LOCK_FILE, 'r') as f:
                    pid = f.read().strip()
                    if pid and os.path.exists(f"/proc/{pid}"):
                        logger.warning(f"Another Telegram bot instance is running with PID {pid}")
                        return True
            return False
        except Exception as e:
            logger.error(f"Error checking for running instance: {str(e)}")
            return False
    
    @staticmethod
    def create_lock_file():
        """Create a lock file with current PID"""
        # First check if another instance is running
        if TelegramClient.is_another_instance_running():
            logger.warning(f"Cannot create lock file, another instance is already running")
            return False
            
        try:
            with open(TelegramClient.LOCK_FILE, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(f"Created lock file for PID {os.getpid()}")
            return True
        except Exception as e:
            logger.error(f"Error creating lock file: {str(e)}")
            return False
    
    @staticmethod
    def remove_lock_file():
        """Remove the lock file"""
        try:
            if os.path.exists(TelegramClient.LOCK_FILE):
                os.remove(TelegramClient.LOCK_FILE)
                logger.info("Removed Telegram lock file")
            return True
        except Exception as e:
            logger.error(f"Error removing lock file: {str(e)}")
            return False

    def __init__(self, token=None, chat_id=None, admin_chat_ids=None):
        """Initialize the Telegram client.
        
        Args:
            token (str): The Telegram bot token.
            chat_id (str): The chat ID to send messages to.
            admin_chat_ids (list): List of admin chat IDs for admin commands.
        """
        self.token = token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        self.admin_chat_ids = admin_chat_ids or []
        self.bot = None
        self.updater = None
        self.send_only_mode = False
        
        # Generate a unique instance ID to track this particular client instance
        self.instance_id = str(uuid.uuid4())[:8]
        logger.info(f"Initializing TelegramClient with instance ID: {self.instance_id}")
        
        # Check if another instance is running
        if TelegramClient.is_another_instance_running():
            # Force send-only mode to avoid conflicts
            self.send_only_mode = True
            logger.warning("Another Telegram bot instance is already running. This instance will only send messages.")
            try:
                # Initialize the bot for sending messages only
                if self.token and self.chat_id:
                    self.bot = Bot(self.token)
                    logger.info(f"Telegram client initialized for sending messages only (instance {self.instance_id})")
            except Exception as e:
                logger.error(f"Error initializing Telegram client for sending messages: {str(e)}")
                self.bot = None
            return  # Don't proceed with updater initialization
            
        self.initialize()

    def initialize(self):
        """Initialize the Telegram client fully with updater."""
        if self.send_only_mode:
            logger.info("Running in send-only mode due to another active instance. Skipping full initialization.")
            return False
        
        if not self.token or not self.chat_id:
            logger.error("Telegram bot token or chat ID not set. Unable to initialize.")
            return False
            
        try:
            # Create a lock file to indicate this instance is running
            if not TelegramClient.create_lock_file():
                logger.error("Failed to create lock file. Setting to send-only mode.")
                self.send_only_mode = True
                self.bot = Bot(self.token)
                return False
            
            # Register cleanup on exit
            atexit.register(TelegramClient.remove_lock_file)
            
            # Initialize the bot
            self.bot = Bot(self.token)
            self.updater = Updater(self.token, use_context=True)
            
            # Test if we can send a message
            # self.bot.send_message(chat_id=self.chat_id, text="🤖 Telegram client initialized")
            
            logger.info(f"Telegram client initialized (instance {self.instance_id})")
            return True
        except TelegramError as te:
            if "Conflict" in str(te):
                logger.error(f"Telegram conflict detected. Setting to send-only mode: {str(te)}")
                self.send_only_mode = True
                if not self.bot:
                    self.bot = Bot(self.token)
                TelegramClient.remove_lock_file()  # Release the lock since we're not using updater
                return False
            else:
                logger.error(f"Telegram error: {str(te)}")
                return False
        except Exception as e:
            logger.error(f"Error initializing Telegram client: {str(e)}")
            return False

    def error_handler(self, update, context):
        """Handle errors in the telegram bot"""
        logger.error(f"Update {update} caused error {context.error}")
        if "Conflict" in str(context.error):
            logger.critical("Telegram conflict detected! Another bot instance may be running.")
            if self.updater:
                try:
                    self.updater.stop()
                    logger.info("Stopped updater due to conflict")
                    time.sleep(5)  # Wait before trying to restart
                    self.updater.start_polling()
                    logger.info("Restarted polling after conflict")
                except Exception as e:
                    logger.error(f"Failed to restart polling: {str(e)}")

    
    def cleanup(self):
        """Clean up Telegram resources to avoid conflicts"""
        if self.updater:
            try:
                logger.info(f"Cleaning up Telegram updater (instance {self.instance_id})")
                self.updater.stop()
                self.send_message("🔌 Bot disconnecting...")
            except Exception as e:
                logger.error(f"Error during Telegram cleanup: {str(e)}")
                
    def help_command(self, update, context):
        """Send a message when the command /help is issued."""
        help_text = (
            "💬 *Available Commands:*\n\n"
            "/help - Show this help message\n"
            "/status - Check bot status and active trades"
        )
        update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    def status_command(self, update, context):
        """Send a message when the command /status is issued."""
        status_text = (
            "✅ *Bot Status:* Active\n"
            "🕒 *Time:* " + str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + "\n"
            "🤖 *Instance ID:* " + self.instance_id + "\n"
        )
        update.message.reply_text(status_text, parse_mode=ParseMode.MARKDOWN)

    def echo(self, update, context):
        """Echo the user message."""
        update.message.reply_text("I received your message. Use /help for available commands.")
        
    def start_polling(self):
        """Start polling for Telegram updates."""
        if self.send_only_mode:
            logger.warning("In send-only mode. Polling not started.")
            return False
            
        if not self.updater:
            logger.error("Updater not initialized. Cannot start polling.")
            return False
            
        try:
            self.updater.start_polling()
            logger.info("Telegram polling started")
            return True
        except TelegramError as te:
            if "Conflict" in str(te):
                logger.critical("Telegram conflict detected! Another bot instance may be running.")
                self.send_only_mode = True
                if self.updater:
                    self.updater.stop()
                    self.updater = None
                return False
            else:
                logger.error(f"Telegram error: {str(te)}")
                return False
        except Exception as e:
            logger.error(f"Error starting Telegram polling: {str(e)}")
            return False

    def stop(self):
        """Stop the Telegram updater"""
        if self.updater:
            try:
                self.updater.stop()
                logger.info(f"Stopped Telegram updater (instance {self.instance_id})")
            except Exception as e:
                logger.error(f"Error stopping Telegram updater: {str(e)}")
                
    def __del__(self):
        """Destructor to ensure cleanup"""
        self.cleanup()
    
    def send_message(self, message):
        """Send a message to the Telegram chat.
        
        Args:
            message (str): Message to send
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=ParseMode.HTML
            )
            return True
        except TelegramError as e:
            logger.error(f"Error sending Telegram message: {str(e)}")
            return False
    
    def send_chart(self, chart_path, caption=None):
        """Send a chart image to the Telegram chat.
        
        Args:
            chart_path (str): Path to chart image file
            caption (str, optional): Caption for the chart
            
        Returns:
            bool: True if chart was sent successfully, False otherwise
        """
        try:
            with open(chart_path, 'rb') as chart:
                self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=chart,
                    caption=caption
                )
            return True
        except (TelegramError, FileNotFoundError) as e:
            logger.error(f"Error sending chart to Telegram: {str(e)}")
            return False
