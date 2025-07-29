#!/usr/bin/env python3
"""
CLI interface for the trading bot daemon
"""

import os
import sys
import argparse
import logging
from dotenv import load_dotenv

from src.bot import TradingBot
from src.utils.daemon import Daemon
from src.utils.logger import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Set up paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PID_FILE = os.path.join(CURRENT_DIR, 'trading_bot.pid')

def run_bot():
    """Function to run the trading bot"""
    load_dotenv()
    bot = TradingBot()
    bot.run()

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='Trading Signal Bot CLI')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status', 'foreground'],
                       help='Action to perform')
    
    args = parser.parse_args()
    
    daemon = Daemon(PID_FILE, CURRENT_DIR)
    
    if args.action == 'start':
        print("Starting trading bot daemon...")
        daemon.start(run_bot)
        
    elif args.action == 'stop':
        print("Stopping trading bot daemon...")
        daemon.stop()
        
    elif args.action == 'restart':
        print("Restarting trading bot daemon...")
        daemon.restart(run_bot)
        
    elif args.action == 'status':
        if daemon.status():
            print("Trading bot is running.")
        else:
            print("Trading bot is not running.")
            
    elif args.action == 'foreground':
        print("Running trading bot in foreground...")
        load_dotenv()
        bot = TradingBot()
        bot.run()
        
if __name__ == "__main__":
    main()
