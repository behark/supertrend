#!/usr/bin/env python3
"""
Daemon script to run the trading bot 24/7 in the background
"""

import os
import sys
import time
import logging
import signal
import argparse
from datetime import datetime
import subprocess
import platform
from dotenv import load_dotenv

from src.bot import TradingBot
from src.utils.logger import setup_logging
from src.integrations.telegram import TelegramNotifier

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global variables
running = True
bot = None
telegram = None

def signal_handler(sig, frame):
    """Handle termination signals"""
    global running
    logger.info("Received termination signal, shutting down gracefully...")
    if telegram:
        telegram.send_message("🛑 *Bot Shutting Down*\nReceived termination signal, shutting down gracefully...")
    running = False

def daemonize():
    """Daemonize the process (Unix/Linux only)"""
    if platform.system() == 'Windows':
        logger.info("Daemonizing not supported on Windows")
        return
    
    try:
        # First fork
        pid = os.fork()
        if pid > 0:
            # Exit first parent
            sys.exit(0)
    except OSError as e:
        logger.error(f"Fork #1 failed: {e}")
        sys.exit(1)
    
    # Decouple from parent environment
    os.chdir('/')
    os.setsid()
    os.umask(0)
    
    try:
        # Second fork
        pid = os.fork()
        if pid > 0:
            # Exit second parent
            sys.exit(0)
    except OSError as e:
        logger.error(f"Fork #2 failed: {e}")
        sys.exit(1)
    
    # Redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    
    si = open(os.devnull, 'r')
    so = open(os.devnull, 'a+')
    se = open(os.devnull, 'a+')
    
    os.dup2(si.fileno(), sys.stdin.fileno())
    os.dup2(so.fileno(), sys.stdout.fileno())
    os.dup2(se.fileno(), sys.stderr.fileno())

def write_pid_file(pid_file):
    """Write PID to file"""
    with open(pid_file, 'w') as f:
        f.write(str(os.getpid()))
    logger.info(f"PID {os.getpid()} written to {pid_file}")

def run_bot(daemon_mode=False, pid_file=None, max_restarts=3):
    """Run the trading bot with auto-restart capability"""
    global bot, telegram, running
    
    # Load environment variables
    load_dotenv()
    
    # Set environment variable for live trading
    os.environ['USE_FALLBACK_API'] = 'false'
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Initialize Telegram notifier
    telegram = TelegramNotifier()
    
    # Write PID file if specified
    if pid_file:
        write_pid_file(pid_file)
    
    # Daemonize if requested
    if daemon_mode:
        daemonize()
        if telegram.is_configured:
            telegram.send_message("🤖 *Bot Started in Daemon Mode*\nTrading bot is now running in the background.")
    
    # Initialize and start bot
    logger.info("Initializing trading bot in live mode...")
    if telegram.is_configured:
        telegram.send_message("🚀 *Bot Starting*\nInitializing trading bot in live mode...")
    
    restart_count = 0
    last_error_time = None
    
    while running and restart_count <= max_restarts:
        try:
            # Initialize bot in live mode (not test mode)
            bot = TradingBot(test_mode=False)
            
            # Start time
            start_time = datetime.now()
            logger.info(f"Trading bot started at {start_time}")
            
            # Main loop with heartbeat monitoring
            last_heartbeat = datetime.now()
            
            # Let the bot run its own continuous loop instead of manually calling methods
            # This will block until the bot is stopped
            try:
                # Run the bot using its internal loop
                bot.run()
            except Exception as e:
                logger.error(f"Error in bot run method: {e}", exc_info=True)
                # If we get here, the bot has exited its loop unexpectedly
            
        except Exception as e:
            # Get current time for calculating error frequency
            current_time = datetime.now()
            
            # Log the error
            logger.error(f"Critical error running trading bot: {e}", exc_info=True)
            
            if telegram.is_configured:
                telegram.send_message(f"❌ *Bot Critical Error*\n{str(e)}\nAttempting restart {restart_count+1}/{max_restarts+1}")
            
            # Reset error counter if it's been a while since last error
            if last_error_time and (current_time - last_error_time).total_seconds() > 3600:  # 1 hour
                restart_count = 0
                
            last_error_time = current_time
            restart_count += 1
            
            # Wait before restarting to prevent rapid restart loops
            time.sleep(30)
    
    # If we exit the loop, the bot is shutting down
    logger.info("Bot shutting down, cleaning up...")
    if telegram.is_configured:
        telegram.send_message("🛑 *Bot Shutdown*\nTrading bot is shutting down.")
        
    if pid_file and os.path.exists(pid_file):
        os.remove(pid_file)
    
    if restart_count > max_restarts:
        logger.error(f"Bot exceeded maximum restarts ({max_restarts}), shutting down.")
        if telegram.is_configured:
            telegram.send_message(f"⚠️ *Bot Exceeded Maximum Restarts*\nThe bot has been stopped after {restart_count} restart attempts.")
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the trading bot as a daemon")
    parser.add_argument('-d', '--daemon', action='store_true', help='Run as daemon')
    parser.add_argument('-p', '--pid-file', default='/tmp/trading_bot.pid', help='PID file path')
    args = parser.parse_args()
    
    run_bot(args.daemon, args.pid_file)
