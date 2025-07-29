#!/usr/bin/env python3
"""
Watchdog script to ensure the trading bot daemon stays running 24/7
"""

import os
import sys
import time
import logging
import subprocess
import signal
import argparse
from datetime import datetime
import psutil
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('watchdog.log')
    ]
)
logger = logging.getLogger('watchdog')

class BotWatchdog:
    def __init__(self, pid_file='/tmp/trading_bot.pid', check_interval=60, max_failures=3):
        """
        Initialize the watchdog
        
        Args:
            pid_file: Path to the bot's PID file
            check_interval: How often to check if the bot is running (seconds)
            max_failures: Maximum number of restart failures before giving up
        """
        self.pid_file = pid_file
        self.check_interval = check_interval
        self.max_failures = max_failures
        self.failure_count = 0
        self.running = True
        self.last_restart = None
        
    def get_bot_pid(self):
        """Get the bot's PID from the PID file"""
        try:
            if os.path.exists(self.pid_file):
                with open(self.pid_file, 'r') as f:
                    return int(f.read().strip())
            return None
        except Exception as e:
            logger.error(f"Error reading PID file: {e}")
            return None
    
    def is_bot_running(self):
        """Check if the bot process is running"""
        pid = self.get_bot_pid()
        if not pid:
            return False
            
        try:
            process = psutil.Process(pid)
            if process.is_running() and 'python' in process.name().lower():
                return True
            return False
        except Exception:
            return False
    
    def start_bot(self):
        """Start the trading bot daemon"""
        try:
            logger.info("Starting trading bot daemon...")
            cmd = [sys.executable, 'run_bot_daemon.py', '--daemon']
            
            # Change to the correct directory
            os.chdir(os.path.dirname(os.path.abspath(__file__)))
            
            # Activate virtual environment if needed
            venv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv/bin/activate')
            if os.path.exists(venv_path):
                # Use subprocess to source the activate script and then run the daemon
                subprocess.run(f"source {venv_path} && python run_bot_daemon.py --daemon", 
                               shell=True, executable='/bin/bash')
            else:
                # Run directly if no venv
                subprocess.run(cmd)
                
            # Allow time for daemon to start
            time.sleep(5)
            
            # Check if it started successfully
            if self.is_bot_running():
                logger.info(f"Bot started successfully with PID: {self.get_bot_pid()}")
                self.last_restart = datetime.now()
                self.failure_count = 0  # Reset failure count on successful start
                return True
            else:
                logger.error("Bot failed to start")
                self.failure_count += 1
                return False
                
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            self.failure_count += 1
            return False
    
    def stop_bot(self):
        """Stop the trading bot daemon"""
        pid = self.get_bot_pid()
        if not pid:
            logger.warning("No PID file found, can't stop bot")
            return
            
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info(f"Sent SIGTERM to bot process {pid}")
            
            # Wait for process to terminate
            for _ in range(10):  # Wait up to 10 seconds
                if not self.is_bot_running():
                    logger.info("Bot stopped successfully")
                    return
                time.sleep(1)
                
            # Force kill if still running
            if self.is_bot_running():
                os.kill(pid, signal.SIGKILL)
                logger.warning(f"Forced SIGKILL on bot process {pid}")
                
        except ProcessLookupError:
            logger.info(f"Process {pid} already terminated")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")
    
    def run(self):
        """Run the watchdog loop"""
        logger.info("Watchdog started")
        
        signal.signal(signal.SIGTERM, lambda sig, frame: self.handle_shutdown())
        signal.signal(signal.SIGINT, lambda sig, frame: self.handle_shutdown())
        
        try:
            while self.running:
                if not self.is_bot_running():
                    logger.warning("Trading bot is not running, attempting to restart...")
                    
                    # Check if we've exceeded max failures
                    if self.failure_count >= self.max_failures:
                        # If it's been at least 6 hours since last restart, reset counter
                        if self.last_restart and (datetime.now() - self.last_restart).total_seconds() > 6*3600:
                            logger.info("Resetting failure count after 6 hours")
                            self.failure_count = 0
                        else:
                            logger.error(f"Maximum restart failures ({self.max_failures}) reached, giving up")
                            break
                    
                    self.start_bot()
                
                # Sleep for the check interval, but break into smaller sleeps to check for shutdown signal
                for _ in range(self.check_interval):
                    if not self.running:
                        break
                    time.sleep(1)
                
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
        
        logger.info("Watchdog shutting down")
    
    def handle_shutdown(self):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal, stopping watchdog")
        self.running = False

def main():
    parser = argparse.ArgumentParser(description="Watchdog for trading bot daemon")
    parser.add_argument('-i', '--interval', type=int, default=60, help='Check interval in seconds')
    parser.add_argument('-p', '--pid-file', default='/tmp/trading_bot.pid', help='Path to PID file')
    parser.add_argument('-m', '--max-failures', type=int, default=3, help='Maximum restart failures before giving up')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Create and run watchdog
    watchdog = BotWatchdog(
        pid_file=args.pid_file,
        check_interval=args.interval,
        max_failures=args.max_failures
    )
    watchdog.run()

if __name__ == "__main__":
    main()
