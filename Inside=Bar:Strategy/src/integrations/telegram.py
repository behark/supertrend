"""
Telegram Integration Module
"""

import os
import logging
import requests
from typing import Dict, Optional, Union, List, Any, Callable
from dotenv import load_dotenv
import time
from urllib.parse import quote
import re
import json
import threading
from datetime import datetime
from functools import wraps

# Import the notification cache - use try/except for backward compatibility
try:
    from src.utils.notification_cache import notification_cache
    NOTIFICATION_CACHE_AVAILABLE = True
except ImportError:
    NOTIFICATION_CACHE_AVAILABLE = False

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Telegram notification integration with command processing
    """
    
    # Singleton instance
    _instance = None
    _lock = threading.Lock()
    
    # Update polling variables
    _polling_thread = None
    _last_update_id = 0
    _should_stop = False
    _polling_interval = 5  # Seconds between polls
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TelegramNotifier, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """
        Initialize the Telegram notifier
        """
        # Skip initialization if already done (singleton pattern)
        if getattr(self, '_initialized', False):
            return
            
        self.token = os.getenv('TELEGRAM_BOT_TOKEN', '')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', '')
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.is_configured = bool(self.token and self.chat_id)
        self.bot_instance = None
        self._command_handler = None
        self._initialized = True
        
        if self.is_configured:
            logger.info("Telegram notifier initialized")
            # Try to load the command handler if available
            try:
                from src.integrations.telegram_commands import telegram_commands
                self._command_handler = telegram_commands
                logger.info("Telegram command handler loaded")
            except ImportError:
                logger.warning("Telegram command handler not available")
        else:
            logger.warning("Telegram notifier not configured. Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
    
    # Class-level cache for tracking GLOBAL insufficient balance notifications
    # This is needed because we're getting multiple bot instances running
    _last_insufficient_balance_time = 0
    _insufficient_balance_cooldown = 14400  # 4 hours
    
    def send_message(self, message: str, parse_mode: str = "Markdown") -> Dict:
        """
        Send a message via Telegram
        
        Args:
            message: Message to send
            parse_mode: Message formatting mode (Markdown or HTML)
            
        Returns:
            Dict: API response
        """
        if not self.is_configured:
            logger.error("Telegram not configured")
            return {"error": "Telegram not configured"}
        
        # EXTREMELY AGGRESSIVE GLOBAL NOTIFICATION FILTER FOR INSUFFICIENT BALANCE
        # This is a hard block on all insufficient balance messages with a class-level time tracker
        if "Insufficient balance" in message or "Trade Execution Failed" in message:
            current_time = time.time()
            time_since_last = current_time - TelegramNotifier._last_insufficient_balance_time
            
            # Only allow one insufficient balance notification every 4 hours
            # This is global across ALL instances and ALL symbols
            if time_since_last < TelegramNotifier._insufficient_balance_cooldown:
                time_remaining = TelegramNotifier._insufficient_balance_cooldown - time_since_last
                logger.info(f"🔇 HARD BLOCK: Suppressing ALL insufficient balance messages for {time_remaining/60:.1f} more minutes")
                return {"filtered": True, "reason": "Global insufficient balance rate limit"}
            
            # Update the class-level timestamp
            TelegramNotifier._last_insufficient_balance_time = current_time
            logger.info("⚠️ ALLOWED: Sending one insufficient balance notification (next allowed in 4 hours)")
        
        # Continue with normal message processing if we pass the filters
        
        # IMPROVED MARKDOWN HANDLING
        # Switch to HTML mode if message contains complex formatting that might break Markdown
        if parse_mode == "Markdown" and (
            message.count('*') > 10 or 
            message.count('_') > 10 or 
            message.count('`') > 4 or
            '[' in message and '](' in message
        ):
            # Convert basic Markdown to HTML for more reliable formatting
            message = self._convert_markdown_to_html(message)
            parse_mode = "HTML"
            logger.info("Switched to HTML parse mode for complex message")
        elif parse_mode == "Markdown":
            # Fix common Markdown formatting issues
            # Ensure all formatting markers are properly paired
            for marker in ['*', '_', '`']:
                if message.count(marker) % 2 != 0:
                    # Add missing closing marker at the end if needed
                    message += marker
                    logger.info(f"Fixed unpaired {marker} in Markdown message")
            
            # Escape special characters that break Markdown
            # But preserve intentional formatting
            message = re.sub(r'(?<![\\*_`])([\.\-\+\!\(\)\[\]\#])', r'\\\1', message)
        
        # Limit message length to prevent API errors
        if len(message) > 4000:
            message = message[:3997] + "..."
        
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=data)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Telegram message: {e}")
            # Try sending without parse_mode if we get a formatting error
            if "can't parse entities" in str(e).lower() or "bad request" in str(e).lower():
                logger.warning("Retrying without Markdown parsing")
                # Try again with plain text (no formatting)
                data["parse_mode"] = ""
                # Also strip any potential formatting characters
                data["text"] = re.sub(r'[\*_`\[\]\(\)\#]', '', message)
                try:
                    response = requests.post(url, json=data)
                    response.raise_for_status()
                    logger.info("Successfully sent message without formatting")
                    return response.json()
                except requests.exceptions.RequestException as e2:
                    logger.error(f"Failed to send Telegram message without formatting: {e2}")
                    return {"error": str(e2)}
            return {"error": str(e)}
    
    def send_signal_notification(self, signal: Dict) -> Dict:
        """
        Send a formatted signal notification with safe Markdown formatting
        
        Args:
            signal: Signal data dictionary
            
        Returns:
            Dict: API response
        """
        try:
            # Format signal message with safe formatting to prevent Telegram API errors
            direction_emoji = "🟢" if signal.get('direction', '').upper() == 'LONG' else "🔴"
            
            # Safely extract and clean values to prevent Markdown parsing errors
            strategy_name = str(signal.get('strategy_name', 'Unknown')).replace('*', '').replace('_', '')
            direction = str(signal.get('direction', 'UNKNOWN')).replace('*', '').replace('_', '')
            symbol = str(signal.get('symbol', 'UNKNOWN')).replace('*', '').replace('_', '')
            timeframe = str(signal.get('timeframe', '1h')).replace('*', '').replace('_', '')
            
            message = f"{direction_emoji} *{strategy_name} SIGNAL*\n"
            message += f"*{direction}* {symbol} ({timeframe})\n\n"
            
            # Format numbers safely with proper precision
            confidence = float(signal.get('confidence', 0))
            price = float(signal.get('price', 0))
            profit_target = float(signal.get('profit_target', 0))
            stop_loss = float(signal.get('stop_loss', 0))
            
            message += f"*Confidence:* {confidence:.1f}%\n"
            message += f"*Entry Price:* {price:.6f}\n"
            message += f"*Profit Target:* {profit_target:.6f}\n"
            message += f"*Stop Loss:* {stop_loss:.6f}\n\n"
            
            # Calculate risk-reward ratio safely
            try:
                risk = abs(price - stop_loss)
                reward = abs(profit_target - price)
                
                if risk > 0:
                    risk_reward = reward / risk
                    message += f"*Risk-Reward Ratio:* {risk_reward:.2f}\n"
            except (ValueError, ZeroDivisionError):
                pass
                
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error formatting signal notification: {e}", exc_info=True)
            # Send a simple fallback message
            fallback_msg = f"🚨 SIGNAL: {signal.get('symbol', 'UNKNOWN')} {signal.get('direction', 'UNKNOWN')}"
            return self.send_message(fallback_msg)
        
    def send_error_notification(self, error_message: str) -> Dict:
        """
        Send an error notification
        
        Args:
            error_message: Error message to send
            
        Returns:
            Dict: API response
        """
        message = f"⚠️ *ERROR ALERT*\n\n{error_message}"
        return self.send_message(message)
        
    def send_status_update(self, title: str, details: str) -> Dict:
        """
        Send a status update notification
        
        Args:
            title: Status update title
            details: Status update details
            
        Returns:
            Dict: API response
        """
        message = f"📊 *{title}*\n\n{details}"
        return self.send_message(message)
        
    def test_notification(self) -> Dict:
        """
        Send a test notification to verify the configuration
        
        Returns:
            Dict: API response
        """
        message = (
            "🔔 *Trading Signal Bot Test*\n\n"
            "This is a test notification to verify that your Telegram bot is correctly configured. "
            "If you received this message, the bot is working correctly!\n\n"
            "*Command Support:* " + ("Enabled ✅" if self._command_handler else "Disabled ❌") + "\n"
            "Type /help for available commands."
        )
        return self.send_message(message)
        
    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """
        Convert basic Markdown formatting to HTML for more reliable message delivery
        
        Args:
            markdown_text: Text with Markdown formatting
            
        Returns:
            Text with HTML formatting
        """
        # Replace bold: *text* -> <b>text</b>
        html_text = re.sub(r'\*(.*?)\*', r'<b>\1</b>', markdown_text)
        
        # Replace italic: _text_ -> <i>text</i>
        html_text = re.sub(r'_(.*?)_', r'<i>\1</i>', html_text)
        
        # Replace code: `text` -> <code>text</code>
        html_text = re.sub(r'`(.*?)`', r'<code>\1</code>', html_text)
        
        # Replace links: [text](url) -> <a href="url">text</a>
        html_text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', html_text)
        
        return html_text
        
    def set_bot_instance(self, bot_instance) -> None:
        """
        Set reference to the bot instance for commands
        
        Args:
            bot_instance: Reference to the TradingBot instance
        """
        self.bot_instance = bot_instance
        
        # Also pass to command handler if available
        if self._command_handler:
            self._command_handler.set_bot_instance(bot_instance)
            logger.info("Bot instance set for command handler")
            
    def start_update_polling(self) -> None:
        """
        Start a background thread to poll for Telegram updates
        This allows processing commands sent by the user
        """
        if not self.is_configured:
            logger.warning("Cannot start Telegram polling - not configured")
            return
            
        # Don't start if already running
        if TelegramNotifier._polling_thread and TelegramNotifier._polling_thread.is_alive():
            logger.warning("Telegram polling already running")
            return
            
        # Reset stop flag
        TelegramNotifier._should_stop = False
        
        # Start polling in a separate thread
        TelegramNotifier._polling_thread = threading.Thread(
            target=self._polling_worker,
            daemon=True,
            name="TelegramPoller"
        )
        TelegramNotifier._polling_thread.start()
        logger.info("Started Telegram update polling thread")
        
        # Send an initial notification
        try:
            self.send_message("🤖 *Bot Started*\n\nTelegram command interface is active. Type /help for available commands.")
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    def stop_update_polling(self) -> None:
        """
        Stop the Telegram update polling thread
        """
        TelegramNotifier._should_stop = True
        if TelegramNotifier._polling_thread and TelegramNotifier._polling_thread.is_alive():
            TelegramNotifier._polling_thread.join(timeout=2.0)
            logger.info("Stopped Telegram update polling")
    
    def _polling_worker(self) -> None:
        """
        Worker thread function to poll for updates
        """
        logger.info("Telegram polling worker started")
        
        while not TelegramNotifier._should_stop:
            try:
                # Get updates with timeout (long polling)
                updates = self._get_updates(offset=TelegramNotifier._last_update_id + 1, timeout=30)
                
                if updates and isinstance(updates, list) and updates:
                    # Process each update
                    for update in updates:
                        if 'update_id' in update:
                            # Update the last seen update ID
                            TelegramNotifier._last_update_id = max(TelegramNotifier._last_update_id, update['update_id'])
                            
                            # Process the update
                            self._process_update(update)
                            
            except Exception as e:
                logger.error(f"Error in Telegram polling: {e}")
                
            # Sleep a bit to avoid hammering the API
            time.sleep(TelegramNotifier._polling_interval)
            
        logger.info("Telegram polling worker stopped")
    
    def _get_updates(self, offset: int = 0, timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Get updates from Telegram API
        
        Args:
            offset: Update ID to start from
            timeout: Long polling timeout in seconds
            
        Returns:
            List of update objects
        """
        url = f"{self.base_url}/getUpdates"
        params = {
            "offset": offset,
            "timeout": timeout
        }
        
        try:
            response = requests.get(url, params=params, timeout=timeout+5)
            if response.status_code == 200:
                result = response.json()
                if result.get('ok', False):
                    return result.get('result', [])
                else:
                    logger.error(f"Telegram API error: {result.get('description', 'Unknown error')}")
            else:
                logger.error(f"Telegram API HTTP error: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"Request error getting Telegram updates: {e}")
        except Exception as e:
            logger.error(f"Error getting Telegram updates: {e}")
            
        return []
    
    def _process_update(self, update: Dict[str, Any]) -> None:
        """
        Process a single update from Telegram
        
        Args:
            update: Update object from Telegram
        """
        try:
            # Check if it's a message update
            if 'message' in update:
                message = update['message']
                chat_id = message.get('chat', {}).get('id')
                
                # Only process messages from the configured chat
                if str(chat_id) != str(self.chat_id):
                    logger.warning(f"Ignored message from unauthorized chat: {chat_id}")
                    return
                
                # Check if it's a text message
                if 'text' in message:
                    text = message['text']
                    
                    # Log incoming message
                    user = message.get('from', {}).get('username', 'unknown')
                    logger.info(f"Telegram message from {user}: {text}")
                    
                    # Check if it's a command and we have a command handler
                    if text.startswith('/') and self._command_handler:
                        # Process the command
                        response = self._command_handler.process_command(text)
                        
                        # Send response if we got one
                        if response:
                            self.send_message(response)
        except Exception as e:
            logger.error(f"Error processing Telegram update: {e}", exc_info=True)
