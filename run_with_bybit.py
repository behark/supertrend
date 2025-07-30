#!/usr/bin/env python3
"""
Crypto Alert Bot with BYBIT Auto Trading
---------------------------------------
This script runs the main crypto alert bot with additional
BYBIT auto trading functionality.
"""
import os
import sys
import time
import logging
import argparse
import threading
import traceback
from datetime import datetime

# Configure logging first thing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/home/behar/CascadeProjects/crypto-alert-bot/run_with_bybit.log')
    ]
)
logger = logging.getLogger(__name__)

# Apply imghdr patch for Python 3.13+ (must happen before other imports)
try:
    import imghdr
    logger.info("✅ Native imghdr module found")
except ImportError:
    logger.info("⚠️ Native imghdr module not found, applying compatibility patch...")
    
    # Create a simple shim for imghdr
    class ImghdrShim:
        def what(self, *args, **kwargs):
            return None
    
    sys.modules['imghdr'] = ImghdrShim()
    logger.info("✅ Successfully created imghdr shim")

# Now import local modules
try:
    import bot
    from telegram_client import TelegramClient
    from bybit_trader import get_bybit_exchange, execute_bybit_trade, fetch_low_priced_symbols
    from config import SETTINGS, MAX_DAILY_TRADES
    
    logger.info("✅ Successfully imported local modules")
except Exception as e:
    logger.error(f"❌ Error importing modules: {str(e)}")
    logger.error(traceback.format_exc())
    sys.exit(1)

# Flag to enable/disable BYBIT trading
BYBIT_TRADING_ENABLED = True

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Run Crypto Alert Bot with BYBIT integration')
    parser.add_argument('--live', action='store_true', help='Run in live mode (default: False)')
    parser.add_argument('--risk', choices=['low', 'medium', 'high'], default='high', help='Risk level (default: high)')
    args = parser.parse_args()

    live_mode = args.live
    risk_level = args.risk

    # Initialize Telegram client
    try:
        telegram = TelegramClient(
            os.getenv('TELEGRAM_BOT_TOKEN'),
            os.getenv('TELEGRAM_CHAT_ID')
        )
    except Exception as e:
        logger.error(f"Failed to initialize Telegram client: {str(e)}")
        logger.error(traceback.format_exc())
        # Continue without Telegram rather than exiting
        telegram = None

    # Send startup notification
    startup_message = (
        "🚀 *BYBIT CRYPTO ALERT BOT STARTED*\n\n"
        f"*Mode:* {'LIVE' if live_mode else 'Test'}\n"
        f"*Risk Level:* {risk_level.upper()}\n"
        f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"*Auto Trading:* Enabled\n"
        f"*Daily Trade Limit:* {MAX_DAILY_TRADES}\n"
    )
    
    if telegram:
        try:
            telegram.send_message(startup_message)
            logger.info("Startup notification sent")
        except Exception as e:
            logger.error(f"Failed to send startup notification: {str(e)}")
    else:
        logger.warning("Telegram client not initialized - skipping startup notification")

    # Fetch low-priced symbols (under $1)
    try:
        exchange = get_bybit_exchange()
        
        # Fetch low-priced symbols (under $1)
        symbols = fetch_low_priced_symbols(exchange, limit=30)
        logger.info(f"Added {len(symbols)} low-priced symbols to scan list")
        
        # Add these symbols to bot's scan list
        if symbols:
            if not SETTINGS['symbols_to_scan']:
                SETTINGS['symbols_to_scan'] = symbols
            else:
                # Combine existing symbols with low-priced ones
                SETTINGS['symbols_to_scan'] = list(set(SETTINGS['symbols_to_scan'] + symbols))
                
            # Limit to maximum 30 pairs
            if len(SETTINGS['symbols_to_scan']) > 30:
                SETTINGS['symbols_to_scan'] = SETTINGS['symbols_to_scan'][:30]
    except Exception as e:
        logger.error(f"Failed to initialize BYBIT exchange: {str(e)}")
        logger.error(traceback.format_exc())
        # Create empty symbols list to continue without BYBIT
        exchange = None
        logger.warning("Continuing without BYBIT integration")

    # Override the analyze_symbol function to execute BYBIT trades on valid signals
    original_analyze_symbol = bot.analyze_symbol

    def analyze_with_bybit_trading(exchange, symbol, timeframe):
        try:
            # Call the original analysis function
            result = original_analyze_symbol(exchange, symbol, timeframe)
            
            # Early return if original analysis returns None
            if result is None:
                return None
                
            # Extract signal and probability from result
            # Note: In our implementation, we'll assume it returns a tuple of (signal, probability)
            signal = None
            probability = None
            
            # Process analysis results to find signals and probability
            # This is a simplified version - we should adjust based on actual return format
            if isinstance(result, tuple) and len(result) >= 2:
                signal, probability = result
            elif isinstance(result, dict):
                signal = result.get('signal')
                probability = result.get('probability')
            
            # If we have a valid signal with high probability in live mode, execute BYBIT trade
            if signal and probability and live_mode and BYBIT_TRADING_ENABLED and exchange is not None:
                symbol_name = symbol  # Use the symbol directly from function params
                
                # Ensure signal is a dictionary with a type key
                signal_type = 'UNKNOWN'
                if isinstance(signal, dict) and 'type' in signal:
                    signal_type = signal['type'].upper()
                
                # Only execute trades with probability > 90%
                if float(probability) > 0.90:
                    logger.info(f"High probability signal ({probability}) detected for {symbol_name}: {signal_type}")
                    
                    # Execute BYBIT trade
                    try:
                        execute_bybit_trade(
                            exchange,
                            symbol_name, 
                            'buy' if signal_type == 'LONG' else 'sell',
                            probability
                        )
                    except Exception as e:
                        logger.error(f"Failed to execute BYBIT trade for {symbol_name}: {str(e)}")
                        if telegram:
                            error_msg = (
                                f"⚠️ *BYBIT TRADE EXECUTION ERROR*\n\n"
                                f"*Symbol:* {symbol_name}\n"
                                f"*Error:* {str(e)}\n"
                            )
                            telegram.send_message(error_msg)
                else:
                    logger.info(f"Signal for {symbol_name} has probability {probability} below threshold (0.90)")
            
            return signal, probability
        except Exception as e:
            logger.error(f"Error in analysis function: {str(e)}")
            logger.error(traceback.format_exc())
            # Return empty results on error to continue operation
            return None, None

    # Replace the analysis function with our enhanced version
    bot.analyze_symbol = analyze_with_bybit_trading
    
    # Setup signal handling for graceful shutdown
    import signal
    running = True
    
    def signal_handler(sig, frame):
        nonlocal running
        logger.info("Shutdown signal received, stopping bot gracefully...")
        running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Run the main bot with proper arguments (mocking CLI args)
        def run_bot_with_args():
            # Save original args
            orig_argv = sys.argv.copy()
            # Set args to simulate CLI with trading enabled
            if live_mode:
                sys.argv = [sys.argv[0], '--trade']
            else:
                sys.argv = [sys.argv[0]]
            
            try:
                # Run the main bot function
                bot.main()
            finally:
                # Restore original args
                sys.argv = orig_argv
        
        # Start in a thread
        bot_thread = threading.Thread(target=run_bot_with_args)
        bot_thread.daemon = True
        bot_thread.start()
        
        # Heartbeat/watchdog to monitor bot status
        heartbeat_count = 0
        last_heartbeat_time = time.time()
        
        while running:
            time.sleep(60)  # Check every minute
            heartbeat_count += 1
            
            # Log a heartbeat every hour
            if heartbeat_count >= 60:
                current_time = time.time()
                uptime_hours = (current_time - last_heartbeat_time) / 3600
                logger.info(f"Bot heartbeat - Uptime: {uptime_hours:.2f} hours")
                
                # Send heartbeat notification via Telegram every 24 hours
                if heartbeat_count >= 1440 and telegram:  # 24 hours = 1440 minutes
                    try:
                        heartbeat_msg = (
                            f"💓 *BOT HEARTBEAT*\n\n"
                            f"Bot is running smoothly\n"
                            f"*Uptime:* {uptime_hours:.2f} hours\n"
                            f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        )
                        telegram.send_message(heartbeat_msg)
                    except Exception as e:
                        logger.error(f"Failed to send heartbeat: {str(e)}")
                    
                    heartbeat_count = 0
                    last_heartbeat_time = current_time
            
            # Check if bot thread is still alive
            if not bot_thread.is_alive():
                logger.error("Bot thread has died! Attempting restart...")
                bot_thread = threading.Thread(target=run_bot_with_args)
                bot_thread.daemon = True
                bot_thread.start()
                
                if telegram:
                    try:
                        restart_msg = (
                            f"🔄 *BOT RESTARTED*\n\n"
                            f"Bot thread was detected as inactive and has been restarted\n"
                            f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        )
                        telegram.send_message(restart_msg)
                    except Exception as e:
                        logger.error(f"Failed to send restart notification: {str(e)}")
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Attempt to notify of critical error
        if telegram:
            try:
                error_msg = (
                    f"🚨 *CRITICAL ERROR*\n\n"
                    f"The bot has encountered a critical error and may stop functioning\n"
                    f"*Error:* {str(e)}\n"
                    f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"Please check the logs and restart the bot if necessary."
                )
                telegram.send_message(error_msg)
            except Exception as telegram_err:
                logger.error(f"Additionally, failed to send error notification: {str(telegram_err)}")
    
    # Cleanup on exit
    if telegram:
        try:
            shutdown_msg = (
                f"🛑 *BOT SHUTTING DOWN*\n\n"
                f"The bot is performing a controlled shutdown\n"
                f"*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            telegram.send_message(shutdown_msg)
        except Exception as e:
            logger.error(f"Failed to send shutdown notification: {str(e)}")
    
    logger.info("Bot has exited gracefully")

if __name__ == "__main__":
    try:
        logger.info(f"🚀 Starting Crypto Alert Bot - Live Mode: {sys.argv[1] == '--live' if len(sys.argv) > 1 else False}, Risk Level: high")
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️ Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Critical error in main function: {str(e)}")
        logger.error(traceback.format_exc())
        sys.exit(1)
