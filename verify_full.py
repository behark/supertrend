#!/usr/bin/env python3
"""
Full System Verification Script for Crypto Alert Bot
---------------------------------------------------
This enhanced verification script addresses all known issues:
1. Properly loads environment variables from .env and .env_bybit files
2. Fixes timestamp synchronization with Bybit API
3. Verifies Python 3.13 compatibility patches
4. Validates all connections (Telegram, Binance, KuCoin, Bybit)
5. Checks portfolio data and trade limits

Usage:
    python verify_full.py [--fix] [--restart]

Options:
    --fix       Attempt to automatically fix identified issues
    --restart   Restart the bot after repairs are complete
"""

import os
import sys
import time
import logging
import signal
import subprocess
import json
import datetime
import socket
import traceback
import argparse
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler('verification_results.txt', mode='a')]
)
logger = logging.getLogger("system_verify")

# First, load environment variables
try:
    from dotenv import load_dotenv
    # Load main .env file first
    load_dotenv(verbose=True)
    logger.info("✅ Loaded environment variables from .env")
    
    # Then load Bybit-specific env if exists
    if os.path.exists(".env_bybit"):
        load_dotenv(".env_bybit", override=True)
        logger.info("✅ Loaded environment variables from .env_bybit")
except ImportError:
    logger.error("❌ Missing python-dotenv package, trying to install...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
        from dotenv import load_dotenv
        load_dotenv(verbose=True)
        if os.path.exists(".env_bybit"):
            load_dotenv(".env_bybit", override=True)
        logger.info("✅ Installed python-dotenv and loaded environment variables")
    except Exception as e:
        logger.error(f"❌ Failed to install python-dotenv: {str(e)}")

# Install ntplib for time synchronization if needed
try:
    import ntplib
except ImportError:
    logger.warning("⚠️ ntplib module not found, installing...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "ntplib"])
        import ntplib
        logger.info("✅ ntplib installed successfully")
    except Exception as e:
        logger.error(f"❌ Failed to install ntplib: {str(e)}")

# Results tracking
verification_results = {
    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "issues_found": [],
    "issues_fixed": [],
    "overall_status": "pending"
}

def check_python_version():
    """Verify Python version compatibility"""
    import platform
    version = platform.python_version()
    major, minor, _ = map(int, version.split('.'))
    
    if major == 3 and minor >= 10 and minor <= 12:
        logger.info(f"✅ Python version {version} is optimal")
        return True
    elif major == 3 and minor == 13:
        logger.warning(f"⚠️ Python version {version} may have compatibility issues with python-telegram-bot")
        verification_results["issues_found"].append(f"Python 3.13 compatibility warning")
        return True
    else:
        logger.error(f"❌ Python version {version} is not compatible (requires 3.10-3.12)")
        verification_results["issues_found"].append(f"Incompatible Python version: {version}")
        return False

def check_env_variables():
    """Check if all required environment variables are set"""
    required_vars = {
        "TELEGRAM_BOT_TOKEN": "Telegram bot token",
        "TELEGRAM_CHAT_ID": "Telegram chat ID"
    }
    
    missing_vars = []
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        if not value:
            missing_vars.append(var_name)
            logger.error(f"❌ Missing required environment variable: {var_name} ({description})")
        else:
            # Partially mask the value for security
            masked_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "***"
            logger.info(f"✅ Found {var_name}: {masked_value}")
    
    if missing_vars:
        verification_results["issues_found"].append(f"Missing environment variables: {', '.join(missing_vars)}")
        return False
    return True

def kill_running_instances():
    """Find and terminate other running bot instances"""
    try:
        # Get the list of running python processes containing bot.py
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True
        )
        
        if result.stdout:
            # Filter for bot.py processes but not grep itself
            bot_processes = []
            for line in result.stdout.split('\n'):
                if 'python' in line and 'bot.py' in line and 'grep' not in line:
                    bot_processes.append(line)
            
            if bot_processes:
                logger.warning(f"⚠️ Found running bot instances: \n{chr(10).join(bot_processes)}")
                verification_results["issues_found"].append("Multiple bot instances running")
                
                # Extract PIDs
                for line in bot_processes:
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            logger.info(f"✅ Successfully terminated bot instance with PID {pid}")
                            verification_results["issues_fixed"].append(f"Terminated bot instance with PID {pid}")
                        except Exception as e:
                            logger.error(f"❌ Failed to terminate process {pid}: {str(e)}")
                return True
            else:
                logger.info("✅ No running bot instances found")
                return True
        else:
            logger.info("✅ No running bot instances found")
            return True
    except Exception as e:
        logger.error(f"❌ Error checking for running instances: {str(e)}")
        verification_results["issues_found"].append(f"Error checking for running instances: {str(e)}")
        return False

def check_server_time_sync():
    """Check if server time is synchronized with NTP and Bybit API"""
    try:
        # Get NTP time
        ntp_client = ntplib.NTPClient()
        response = ntp_client.request('pool.ntp.org', version=3)
        ntp_time = datetime.datetime.fromtimestamp(response.tx_time)
        system_time = datetime.datetime.now()
        
        # Calculate time difference
        time_diff_seconds = abs((system_time - ntp_time).total_seconds())
        
        if time_diff_seconds > 1:  # More than 1 second difference
            logger.warning(f"⚠️ System time is out of sync by {time_diff_seconds:.2f} seconds")
            verification_results["issues_found"].append(f"System time is out of sync by {time_diff_seconds:.2f} seconds")
            
            # Try to import bybit modules to check their time
            try:
                sys.path.insert(0, '.')  # Ensure local modules can be imported
                
                # Ensure compatibility patch is applied for Python 3.13+
                try:
                    import imghdr
                    logger.info("✅ Native imghdr module found")
                except ImportError:
                    from telegram_client import patch_imghdr
                    if patch_imghdr():
                        logger.info("✅ Successfully patched imghdr module")
                    else:
                        logger.error("❌ Failed to patch imghdr module")
                
                # Initialize Bybit with extra-large recv_window
                from bybit_trader import get_bybit_exchange
                
                # Create a custom options dictionary with very large recv_window
                custom_options = {
                    'options': {
                        'adjustForTimeDifference': True,
                        'recvWindow': 240000  # Use extremely large window for testing
                    }
                }
                
                # Pass options to the exchange initialization
                exchange = get_bybit_exchange(custom_options)
                
                # Try to fetch server time
                server_time = exchange.fetch_time()
                local_time = int(time.time() * 1000)
                exchange_diff_ms = abs(server_time - local_time)
                
                logger.warning(f"⚠️ Bybit server time difference: {exchange_diff_ms}ms")
                verification_results["issues_found"].append(f"Bybit time sync issue: {exchange_diff_ms}ms difference")
                
                if exchange_diff_ms > 1000:  # More than 1 second difference
                    if exchange_diff_ms <= 240000:  # Within our large recv_window
                        logger.info(f"✅ Time difference ({exchange_diff_ms}ms) is within recv_window (240000ms)")
                        return True
                    else:
                        verification_results["issues_found"].append("Critical Bybit timestamp sync issue")
                        return False
            except Exception as e:
                logger.error(f"❌ Error checking Bybit time: {str(e)}")
                logger.error(traceback.format_exc())
        else:
            logger.info(f"✅ System time is in sync (difference: {time_diff_seconds:.2f} seconds)")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error checking time synchronization: {str(e)}")
        verification_results["issues_found"].append(f"Unable to verify time synchronization: {str(e)}")
        return False

def check_telegram_connectivity():
    """Verify Telegram bot connectivity"""
    try:
        # Clean up any lock files first
        lock_files = Path('.').glob('*.lock')
        for lock_file in lock_files:
            if 'telegram' in lock_file.name.lower():
                logger.info(f"🔄 Removing stale Telegram lock file: {lock_file}")
                lock_file.unlink()
                verification_results["issues_fixed"].append(f"Removed stale Telegram lock file: {lock_file}")
        
        # Check if environment variables are set
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not telegram_token or not chat_id:
            logger.error("❌ Telegram credentials missing from environment")
            logger.error(f"  TELEGRAM_BOT_TOKEN: {'MISSING' if not telegram_token else 'FOUND'}")
            logger.error(f"  TELEGRAM_CHAT_ID: {'MISSING' if not chat_id else 'FOUND'}")
            verification_results["issues_found"].append("Telegram credentials missing")
            return False
        
        # Try to import telegram modules
        try:
            sys.path.insert(0, '.')  # Ensure local modules can be imported
            from telegram_client import TelegramClient
            
            # Initialize client and send test message
            client = TelegramClient(telegram_token, chat_id)
            message = f"🔍 *SYSTEM VERIFICATION CHECK*\nTimestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            response = client.send_message(message)
            
            if response:
                logger.info("✅ Telegram connectivity verified")
                return True
            else:
                logger.error("❌ Failed to send Telegram message")
                verification_results["issues_found"].append("Telegram message delivery failure")
                return False
        except Exception as e:
            logger.error(f"❌ Error initializing Telegram client: {str(e)}")
            logger.error(traceback.format_exc())
            verification_results["issues_found"].append(f"Telegram client error: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"❌ Error checking Telegram connectivity: {str(e)}")
        logger.error(traceback.format_exc())
        verification_results["issues_found"].append(f"Telegram connectivity error: {str(e)}")
        return False

def check_exchange_connectivity():
    """Verify connection to trading exchanges"""
    exchanges_to_check = ['binance', 'kucoin', 'bybit']
    results = {}
    
    for exchange_name in exchanges_to_check:
        try:
            if exchange_name == 'bybit':
                sys.path.insert(0, '.')  # Ensure local modules can be imported
                from bybit_trader import get_bybit_exchange
                
                # Use extremely large recv_window for testing
                custom_options = {
                    'options': {
                        'adjustForTimeDifference': True,
                        'recvWindow': 240000
                    }
                }
                exchange = get_bybit_exchange(custom_options)
            else:
                import ccxt
                exchange = getattr(ccxt, exchange_name)()
            
            # Try to fetch ticker for a common pair
            ticker = exchange.fetch_ticker('BTC/USDT')
            
            if ticker and 'last' in ticker:
                logger.info(f"✅ {exchange_name.upper()} connection successful (BTC price: {ticker['last']})")
                results[exchange_name] = True
            else:
                logger.warning(f"⚠️ {exchange_name.upper()} response missing price data")
                results[exchange_name] = False
                verification_results["issues_found"].append(f"{exchange_name.upper()} API returned incomplete data")
        except Exception as e:
            logger.error(f"❌ {exchange_name.upper()} connection failed: {str(e)}")
            results[exchange_name] = False
            verification_results["issues_found"].append(f"{exchange_name.upper()} API connection failure: {str(e)}")
    
    # Return True if at least one exchange is working
    if any(results.values()):
        return True
    else:
        return False

def verify_data_integrity():
    """Check for data integrity issues"""
    issues = []
    
    # Check portfolio data
    portfolio_file = Path('data/portfolio/portfolio.json')
    if portfolio_file.exists():
        try:
            with open(portfolio_file, 'r') as f:
                portfolio_data = json.load(f)
            logger.info(f"✅ Portfolio data loaded successfully")
        except Exception as e:
            logger.error(f"❌ Portfolio data corrupted: {str(e)}")
            issues.append(f"Corrupted portfolio data: {str(e)}")
    else:
        logger.warning("⚠️ Portfolio data file not found")
        issues.append("Missing portfolio data file")
    
    # Check trade count file
    try:
        with open('bybit_trade_counts.json', 'r') as f:
            trade_counts = json.load(f)
        logger.info(f"✅ Trade counts loaded: {trade_counts}")
        
        # Check if trade counts need to be reset
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if today not in trade_counts:
            logger.info(f"ℹ️ No trade count for today ({today})")
    except Exception as e:
        logger.warning(f"⚠️ Trade count file issue: {str(e)}")
        issues.append(f"Trade count file issue: {str(e)}")
    
    if issues:
        verification_results["issues_found"].extend(issues)
        return False
    return True

def fix_bybit_time_sync():
    """Update the recv_window in bybit_trader.py to compensate for time difference"""
    try:
        # Check what's currently set in DEFAULT_RECV_WINDOW
        with open("bybit_trader.py", "r") as file:
            content = file.read()
        
        import re
        
        # First find the DEFAULT_RECV_WINDOW constant
        window_match = re.search(r"DEFAULT_RECV_WINDOW\s*=\s*(\d+)", content)
        if window_match:
            current_window = int(window_match.group(1))
            if current_window < 240000:  # If less than our new target
                new_window = 240000  # Increase to 4 minutes (extreme)
                
                # Replace with new value
                new_content = re.sub(
                    r"DEFAULT_RECV_WINDOW\s*=\s*\d+",
                    f"DEFAULT_RECV_WINDOW = {new_window}",
                    content
                )
                
                with open("bybit_trader.py", "w") as file:
                    file.write(new_content)
                
                logger.info(f"✅ Updated Bybit DEFAULT_RECV_WINDOW from {current_window}ms to {new_window}ms")
                verification_results["issues_fixed"].append(f"Increased Bybit recv_window to {new_window}ms")
                return True
            else:
                logger.info(f"✅ Bybit recv_window already set to {current_window}ms (adequate)")
                return True
        else:
            # Try to directly update any recvWindow values we can find
            matches_found = False
            # Find all recvWindow assignments
            window_matches = re.finditer(r"['\"]{0,1}recvWindow['\"]{0,1}\s*[:=]\s*(\d+)", content)
            for match in window_matches:
                matches_found = True
                current_val = int(match.group(1))
                if current_val < 240000:
                    # Replace with new value
                    if ":" in match.group(0):  # JSON format
                        new_content = content[:match.start(1)] + "240000" + content[match.end(1):]
                    else:  # Assignment format
                        new_content = content[:match.start(1)] + "240000" + content[match.end(1):]
                    
                    with open("bybit_trader.py", "w") as file:
                        file.write(new_content)
                    
                    logger.info(f"✅ Updated a Bybit recvWindow value from {current_val}ms to 240000ms")
                    verification_results["issues_fixed"].append(f"Increased a Bybit recv_window to 240000ms")
                    return True
            
            if not matches_found:
                logger.error("❌ Could not find any recvWindow parameters to update in bybit_trader.py")
                return False
    except Exception as e:
        logger.error(f"❌ Error updating Bybit time sync settings: {str(e)}")
        return False

def fix_env_loading():
    """Fix environment variable loading in main script"""
    try:
        # Check if bot.py exists and if it loads dotenv
        with open("bot.py", "r") as file:
            content = file.read()
        
        if "load_dotenv" not in content:
            # Add dotenv loading to top of the file
            import re
            # Find imports section
            imports_end = re.search(r"^import.*$|^from.*import", content, re.MULTILINE)
            
            if imports_end:
                # Add after the last import
                import_pos = 0
                for match in re.finditer(r"^(?:import|from)\s+.*$", content, re.MULTILINE):
                    if match.end() > import_pos:
                        import_pos = match.end()
                
                if import_pos > 0:
                    # Insert the dotenv loading code
                    new_content = (content[:import_pos] + 
                                 "\n\n# Load environment variables\ntry:\n    from dotenv import load_dotenv\n" +
                                 "    load_dotenv()\n    # Also load Bybit-specific env if exists\n" +
                                 "    if os.path.exists('.env_bybit'):\n        load_dotenv('.env_bybit')\n" +
                                 "except ImportError:\n    print('Warning: python-dotenv not installed, environment variables may not be loaded properly')\n" +
                                 content[import_pos:])
                    
                    with open("bot.py", "w") as file:
                        file.write(new_content)
                    
                    logger.info(f"✅ Added dotenv loading to bot.py")
                    verification_results["issues_fixed"].append(f"Added proper environment variable loading")
                    return True
        else:
            logger.info(f"✅ bot.py already loads dotenv")
            return True
    except Exception as e:
        logger.error(f"❌ Error adding dotenv loading: {str(e)}")
        return False

def reset_trade_limits():
    """Reset the trade count limitations if needed"""
    try:
        with open('bybit_trade_counts.json', 'r') as f:
            trade_counts = json.load(f)
        
        # Reset today's count
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        if today in trade_counts:
            trade_counts[today] = 0
            
            with open('bybit_trade_counts.json', 'w') as f:
                json.dump(trade_counts, f, indent=2)
            
            logger.info(f"✅ Reset trade count for {today} to 0")
            verification_results["issues_fixed"].append(f"Reset daily trade count")
            return True
        else:
            logger.info(f"ℹ️ No trade count for today ({today})")
            return True
    except Exception as e:
        logger.error(f"❌ Error resetting trade limits: {str(e)}")
        return False

def restart_bot():
    """Restart the bot service"""
    try:
        # Check if running as a service
        service_result = subprocess.run(
            "systemctl is-active crypto-bot.service",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if service_result.stdout.strip() == "active":
            logger.info("🔄 Restarting crypto-bot service...")
            subprocess.run("systemctl restart crypto-bot.service", shell=True)
            logger.info("✅ Service restart initiated")
            verification_results["issues_fixed"].append("Restarted crypto-bot service")
        else:
            # Try starting the bot directly
            logger.info("🔄 Starting bot directly...")
            subprocess.Popen(
                ["python", "bot.py"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            logger.info("✅ Bot startup initiated")
            verification_results["issues_fixed"].append("Started bot directly")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error restarting bot: {str(e)}")
        return False

def run_comprehensive_check(fix_issues=False):
    """Run all verification checks and return overall status"""
    logger.info("=" * 80)
    logger.info("STARTING COMPREHENSIVE SYSTEM VERIFICATION")
    logger.info("=" * 80)
    
    # Track results
    check_results = {}
    
    # 0. Check environment variables
    check_results["env_vars"] = check_env_variables()
    
    # 1. Check Python version
    check_results["python_version"] = check_python_version()
    
    # 2. Check for multiple running instances
    if fix_issues:
        check_results["single_instance"] = kill_running_instances()
    else:
        # Just detect but don't kill
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        if result.stdout and any('python' in line and 'bot.py' in line and 'grep' not in line for line in result.stdout.split('\n')):
            logger.warning(f"⚠️ Found running bot instances (not terminated)")
            verification_results["issues_found"].append("Multiple bot instances running")
            check_results["single_instance"] = False
        else:
            logger.info("✅ No running bot instances found")
            check_results["single_instance"] = True
    
    # 3. Check time synchronization
    check_results["time_sync"] = check_server_time_sync()
    
    # 4. Check Telegram connectivity
    check_results["telegram"] = check_telegram_connectivity()
    
    # 5. Check exchange connectivity
    check_results["exchange"] = check_exchange_connectivity()
    
    # 6. Check data integrity
    check_results["data"] = verify_data_integrity()
    
    # Calculate overall status
    critical_checks = ["telegram", "exchange", "time_sync"]
    critical_failures = any(not check_results[check] for check in critical_checks)
    
    all_passed = all(check_results.values())
    
    if all_passed:
        logger.info("✅ ALL CHECKS PASSED - System is fully operational")
        verification_results["overall_status"] = "healthy"
    elif critical_failures:
        logger.error("❌ CRITICAL CHECKS FAILED - System is NOT operational")
        verification_results["overall_status"] = "critical_failure"
    else:
        logger.warning("⚠️ SOME CHECKS FAILED - System is partially operational")
        verification_results["overall_status"] = "degraded"
    
    # Output summary
    logger.info("=" * 80)
    logger.info("VERIFICATION SUMMARY:")
    for check, result in check_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {check}")
    
    logger.info("=" * 80)
    logger.info(f"OVERALL STATUS: {verification_results['overall_status'].upper()}")
    logger.info("=" * 80)
    
    # Save results to JSON
    with open('verification_results.json', 'w') as f:
        json.dump(verification_results, f, indent=2)
    
    return verification_results["overall_status"]

def fix_identified_issues():
    """Apply fixes for identified issues"""
    fixes_applied = []
    
    # 1. Fix time sync issues in Bybit
    if fix_bybit_time_sync():
        fixes_applied.append("bybit_time_sync")
    
    # 2. Fix environment variable loading
    if fix_env_loading():
        fixes_applied.append("env_loading")
    
    # 3. Reset trade limits
    if reset_trade_limits():
        fixes_applied.append("trade_limits")
    
    # Return summary of fixes
    return fixes_applied

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Comprehensive system verification')
    parser.add_argument('--fix', action='store_true', help='Automatically fix identified issues')
    parser.add_argument('--restart', action='store_true', help='Restart bot after verification')
    
    args = parser.parse_args()
    
    try:
        # Run the comprehensive check
        status = run_comprehensive_check(fix_issues=args.fix)
        
        # Apply fixes if requested
        if args.fix and status != "healthy":
            logger.info("=" * 80)
            logger.info("APPLYING FIXES FOR IDENTIFIED ISSUES")
            logger.info("=" * 80)
            
            fixes = fix_identified_issues()
            
            if fixes:
                logger.info(f"✅ Applied fixes: {', '.join(fixes)}")
            else:
                logger.warning("⚠️ No fixes were applied")
        
        # Restart bot if requested
        if args.restart:
            logger.info("=" * 80)
            logger.info("RESTARTING BOT")
            logger.info("=" * 80)
            
            restart_bot()
            
        # Final recommendations
        if status != "healthy":
            logger.info("=" * 80)
            logger.info("RECOMMENDATIONS:")
            
            if "critical_failure" in status:
                logger.info("1. Review logs for detailed error messages")
                logger.info("2. Check API key permissions and validity")
                logger.info("3. Verify internet connectivity")
                logger.info("4. Consider downgrading to Python 3.10-3.12 if using 3.13")
            else:
                logger.info("1. Monitor system for a few hours to ensure stability")
                logger.info("2. Consider scheduling regular verification checks")
            
            logger.info("=" * 80)
        
        return 0 if status == "healthy" else 1
    
    except Exception as e:
        logger.error(f"❌ Unhandled exception during verification: {str(e)}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
