#!/usr/bin/env python
"""
UTC-based daily stats reset monitor for Bidget Enhancements
Ensures all daily counters and statistics are reset precisely at UTC midnight
"""
import time
import logging
import json
import os
import sys
import signal
import requests
import threading
import traceback
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/daily_reset_monitor.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('daily_reset_monitor')

# Constants
STATE_FILE = 'data/reset_state.json'
SLEEP_INTERVAL = 60  # Check every minute
PID_FILE = 'daily_reset_monitor.pid'

# Load environment variables
load_dotenv()  # Load from .env file
load_dotenv('.env_telegram')  # Also try telegram-specific file if it exists

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

def get_last_reset_date():
    """Get the last reset date from persistent storage"""
    if not os.path.exists(STATE_FILE):
        return None
    
    try:
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            return state.get('last_reset')
    except Exception as e:
        logger.error(f"Error reading state file: {e}")
        return None

def save_reset_date(date_str):
    """Save reset date to persistent storage"""
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({'last_reset': date_str}, f)
        logger.info(f"Saved reset date: {date_str}")
    except Exception as e:
        logger.error(f"Error saving state file: {e}")

def trigger_reset():
    """Reset all daily stats across the system"""
    try:
        # Import the bot module to access its functions
        sys.path.insert(0, '.')
        from bot import reset_all_daily_stats
        
        # Capture start time to measure how long the reset takes
        start_time = time.time()
        
        # Perform the reset
        result = reset_all_daily_stats()
        
        # Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        if result:
            reset_date = datetime.utcnow().strftime('%Y-%m-%d')
            logger.info(f"✅ Successfully triggered UTC boundary reset for {reset_date} (took {elapsed_time:.2f}s)")
            
            # Send Telegram notification about successful reset
            notification = (
                f"🔄 <b>Bidget Daily Stats Reset @ {datetime.utcnow().strftime('%H:%M')} UTC</b>\n\n"
                f"📅 <b>Date:</b> {reset_date}\n"
                f"⏱️ <b>Process Time:</b> {elapsed_time:.2f}s\n\n"
                f"✅ Trades, Signals, Confidence Levels Cleared\n"
                f"🚀 System Ready for New Trading Day"
            )
            send_telegram_notification_async(notification)
            
            return True
        else:
            logger.error("❌ Reset operation reported failure")
            
            # Send Telegram notification about failed reset
            error_notification = (
                f"⚠️ <b>Bidget Daily Stats Reset FAILED</b>\n\n"
                f"📅 <b>Date:</b> {datetime.utcnow().strftime('%Y-%m-%d')}\n"
                f"⚠️ <b>Status:</b> Reset operation returned failure flag\n"
                f"👉 <b>Action:</b> Please check system logs"
            )
            send_telegram_notification_async(error_notification)
            
            return False
            
    except Exception as e:
        error_message = str(e)
        error_trace = traceback.format_exc()
        logger.error(f"❌ Failed to trigger reset: {error_message}\n{error_trace}")
        
        # Send Telegram notification about exception during reset
        error_notification = (
            f"🚨 <b>Bidget Daily Stats Reset ERROR</b>\n\n"
            f"📅 <b>Date:</b> {datetime.utcnow().strftime('%Y-%m-%d')}\n"
            f"❌ <b>Error:</b> {error_message[:200] if len(error_message) > 200 else error_message}\n"
            f"👉 <b>Action:</b> Check logs for full traceback"
        )
        send_telegram_notification_async(error_notification)
        
        return False

def save_pid():
    """Save the current process ID to file"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logger.error(f"Failed to write PID file: {e}")

def cleanup_pid():
    """Remove the PID file on exit"""
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except Exception as e:
        logger.error(f"Failed to remove PID file: {e}")

def signal_handler(sig, frame):
    """Handle termination signals"""
    logger.info("Received signal to terminate, shutting down...")
    cleanup_pid()
    sys.exit(0)

def send_telegram_message(message, retry_count=3):
    """Send a message to the configured Telegram chat"""
    if not TELEGRAM_ENABLED:
        logger.warning("Telegram notifications not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    # Retry mechanism for network issues
    for attempt in range(retry_count):
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("Telegram notification sent successfully")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.status_code} {response.text}")
        except Exception as e:
            logger.error(f"Error sending Telegram message (attempt {attempt+1}/{retry_count}): {str(e)}")
            if attempt < retry_count - 1:  # Don't sleep on the last attempt
                time.sleep(2)  # Wait before retry
    
    return False

def send_telegram_notification_async(message):
    """Send Telegram notification in a separate thread to avoid blocking"""
    if not TELEGRAM_ENABLED:
        return
    
    # Create and start thread for non-blocking notification
    notification_thread = threading.Thread(
        target=send_telegram_message,
        args=(message,),
        daemon=True
    )
    notification_thread.start()
    
def calculate_seconds_until_midnight_utc():
    """Calculate seconds until next UTC midnight"""
    now = datetime.utcnow()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_remaining = (tomorrow - now).total_seconds()
    return seconds_remaining

def main():
    """Main monitor loop"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Save PID for service management
    save_pid()
    
    logger.info("🕒 Starting UTC daily reset monitor")
    logger.info(f"Current UTC time: {datetime.utcnow()}")
    
    # Calculate time until next UTC midnight
    seconds_to_midnight = calculate_seconds_until_midnight_utc()
    hours = int(seconds_to_midnight // 3600)
    minutes = int((seconds_to_midnight % 3600) // 60)
    logger.info(f"Next UTC reset in: {hours} hours, {minutes} minutes")
    
    while True:
        try:
            # Get current UTC date as string
            utc_today = datetime.utcnow().date().isoformat()
            last_reset = get_last_reset_date()
            
            if last_reset != utc_today:
                logger.info(f"🔄 UTC boundary detected: {utc_today} vs {last_reset or 'None'}")
                if trigger_reset():
                    save_reset_date(utc_today)
                    
                    # Recalculate time until next UTC midnight
                    seconds_to_midnight = calculate_seconds_until_midnight_utc()
                    hours = int(seconds_to_midnight // 3600)
                    minutes = int((seconds_to_midnight % 3600) // 60)
                    logger.info(f"Next UTC reset in: {hours} hours, {minutes} minutes")
            
            # Sleep until next check
            time.sleep(SLEEP_INTERVAL)
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            time.sleep(SLEEP_INTERVAL)

if __name__ == "__main__":
    # Ensure the logs directory exists
    os.makedirs("logs", exist_ok=True)
    main()
