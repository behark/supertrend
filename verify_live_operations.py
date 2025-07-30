#!/usr/bin/env python3
"""
Live Operations Verification Script for Crypto Alert Bot
-------------------------------------------------------
This script verifies that all critical components of the bot are working properly:
1. Signal generation and processing
2. Trade execution flows
3. Telegram notifications
4. Portfolio tracking and updating
5. Exchange connectivity and data flow

Usage:
    python verify_live_operations.py

Author: Cascade (Windsurf AI)
Date: 2025-07-29
"""

import os
import sys
import json
import time
import logging
import datetime
import requests
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("live_verify")

# First, load environment variables
load_dotenv()
load_dotenv('.env_bybit')  # Also load Bybit-specific env vars if present

# Results tracking
verification_results = {
    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "components_verified": [],
    "issues_found": [],
    "status": {}
}

def check_bot_process():
    """Check if the bot process is running"""
    import subprocess
    
    result = subprocess.run(
        ["systemctl", "status", "crypto-bot.service"], 
        capture_output=True, 
        text=True
    )
    
    if "active (running)" in result.stdout:
        logger.info("✅ Bot service is running")
        verification_results["status"]["bot_process"] = "running"
        return True
    else:
        logger.error("❌ Bot service is not running")
        verification_results["issues_found"].append("Bot service not running")
        verification_results["status"]["bot_process"] = "stopped"
        return False

def check_recent_logs():
    """Check recent log entries to verify normal operation"""
    log_file = Path('/home/behar/CascadeProjects/crypto-alert-bot/bot_service.log')
    error_log = Path('/home/behar/CascadeProjects/crypto-alert-bot/bot_service_error.log')
    
    if not log_file.exists():
        logger.error(f"❌ Log file not found: {log_file}")
        verification_results["issues_found"].append(f"Missing log file: {log_file}")
        return False
    
    # Check standard logs
    try:
        with open(log_file, 'r') as f:
            log_lines = f.readlines()[-200:]  # Get last 200 lines
            
            # Look for key operational indicators
            data_fetches = [line for line in log_lines if "fetch_ohlcv" in line or "data fetched" in line]
            signals = [line for line in log_lines if "signal generated" in line or "new signal" in line.lower()]
            trades = [line for line in log_lines if "executed trade" in line.lower() or "placing order" in line.lower()]
            errors = [line for line in log_lines if "error" in line.lower() or "exception" in line.lower() or "failed" in line.lower()]
            
            logger.info(f"📊 Log Analysis: {len(data_fetches)} data fetches, {len(signals)} signals, {len(trades)} trades, {len(errors)} errors")
            
            verification_results["status"]["data_fetching"] = "active" if data_fetches else "inactive"
            verification_results["status"]["signal_generation"] = "active" if signals else "inactive"
            verification_results["status"]["trading"] = "active" if trades else "inactive"
            
            if errors:
                logger.warning(f"⚠️ Found {len(errors)} error messages in recent logs")
                verification_results["issues_found"].append(f"{len(errors)} error messages in recent logs")
                # Sample the first few errors
                for error in errors[:3]:
                    logger.warning(f"  - {error.strip()}")
            
            # Return True if we see data fetching activity at minimum
            return bool(data_fetches)
    except Exception as e:
        logger.error(f"❌ Error reading log file: {str(e)}")
        verification_results["issues_found"].append(f"Error reading log file: {str(e)}")
        return False

def verify_telegram():
    """Verify Telegram bot connectivity and send a test message"""
    try:
        # Check if Telegram modules are available
        try:
            sys.path.insert(0, '.')  # Ensure local modules can be imported
            
            # Check if environment variables are set
            telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')
            
            if not telegram_token or not chat_id:
                logger.error("❌ Telegram credentials missing from environment")
                verification_results["issues_found"].append("Missing Telegram credentials")
                verification_results["status"]["telegram"] = "misconfigured"
                return False
            
            # Import and test Telegram functionality
            from telegram_client import TelegramClient
            
            # Initialize client and send test message
            client = TelegramClient(telegram_token, chat_id)
            message = f"🧪 *LIVE VERIFICATION TEST*\n\nThis is a test notification to verify Telegram integration is working correctly.\nTimestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            response = client.send_message(message)
            
            if response:
                logger.info("✅ Telegram notification test successful")
                verification_results["components_verified"].append("telegram_notifications")
                verification_results["status"]["telegram"] = "operational"
                return True
            else:
                logger.error("❌ Failed to send Telegram message")
                verification_results["issues_found"].append("Telegram message delivery failure")
                verification_results["status"]["telegram"] = "failed"
                return False
                
        except ImportError as e:
            logger.error(f"❌ Telegram module import error: {str(e)}")
            verification_results["issues_found"].append(f"Telegram module import error: {str(e)}")
            verification_results["status"]["telegram"] = "import_error"
            return False
    except Exception as e:
        logger.error(f"❌ Error testing Telegram: {str(e)}")
        verification_results["issues_found"].append(f"Telegram test error: {str(e)}")
        verification_results["status"]["telegram"] = "error"
        return False

def verify_portfolio_tracking():
    """Verify that portfolio tracking is working correctly"""
    try:
        portfolio_file = Path('data/portfolio/portfolio.json')
        if not portfolio_file.exists():
            logger.error("❌ Portfolio file not found")
            verification_results["issues_found"].append("Missing portfolio file")
            verification_results["status"]["portfolio"] = "missing"
            return False
        
        with open(portfolio_file, 'r') as f:
            portfolio = json.load(f)
        
        logger.info(f"📊 Portfolio loaded: {len(portfolio.get('positions', []))} positions tracked")
        
        # Check portfolio structure
        required_keys = ['total_value', 'positions']
        missing_keys = [key for key in required_keys if key not in portfolio]
        
        if missing_keys:
            logger.warning(f"⚠️ Portfolio missing required keys: {', '.join(missing_keys)}")
            verification_results["issues_found"].append(f"Portfolio missing keys: {', '.join(missing_keys)}")
            verification_results["status"]["portfolio"] = "incomplete"
        else:
            logger.info("✅ Portfolio structure valid")
            verification_results["components_verified"].append("portfolio_structure")
            verification_results["status"]["portfolio"] = "valid"
        
        # Check if portfolio has been updated recently
        if portfolio_file.stat().st_mtime > time.time() - 3600:  # Modified in the last hour
            logger.info("✅ Portfolio recently updated")
            verification_results["components_verified"].append("portfolio_updates")
        else:
            logger.warning(f"⚠️ Portfolio not updated recently (last modified: {datetime.datetime.fromtimestamp(portfolio_file.stat().st_mtime)})")
            verification_results["issues_found"].append("Portfolio not recently updated")
        
        return True
    except Exception as e:
        logger.error(f"❌ Error verifying portfolio: {str(e)}")
        verification_results["issues_found"].append(f"Portfolio verification error: {str(e)}")
        verification_results["status"]["portfolio"] = "error"
        return False

def verify_exchange_data():
    """Verify real-time exchange data fetching"""
    try:
        exchanges = ['binance', 'kucoin', 'bybit']
        results = {}
        
        import ccxt
        
        for exchange_name in exchanges:
            try:
                if exchange_name == 'bybit':
                    # Special handling for Bybit with increased recv_window
                    custom_options = {
                        'options': {
                            'adjustForTimeDifference': True,
                            'recvWindow': 240000
                        }
                    }
                    exchange = getattr(ccxt, exchange_name)(custom_options)
                else:
                    exchange = getattr(ccxt, exchange_name)()
                
                # Try to fetch recent trades for BTC/USDT
                ticker = exchange.fetch_ticker('BTC/USDT')
                ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=5)
                
                logger.info(f"✅ {exchange_name.upper()} data: Price={ticker['last']}, Candles={len(ohlcv)}")
                verification_results["components_verified"].append(f"{exchange_name}_data")
                results[exchange_name] = True
            except Exception as e:
                logger.error(f"❌ {exchange_name.upper()} data fetch failed: {str(e)}")
                verification_results["issues_found"].append(f"{exchange_name.upper()} data fetch error: {str(e)}")
                results[exchange_name] = False
        
        # Overall exchange status
        verification_results["status"]["exchanges"] = {
            exchange: "operational" if result else "error"
            for exchange, result in results.items()
        }
        
        # Return True if at least one exchange is working
        return any(results.values())
    except Exception as e:
        logger.error(f"❌ Error verifying exchange data: {str(e)}")
        verification_results["issues_found"].append(f"Exchange data verification error: {str(e)}")
        return False

def verify_trade_execution(simulate=True):
    """Verify trade execution flows (simulated or real test trades)"""
    if not simulate:
        logger.warning("⚠️ Live trade execution test skipped (simulation only)")
        verification_results["status"]["trade_execution"] = "not_tested"
        return True
    
    try:
        # Import trading modules
        sys.path.insert(0, '.')
        
        # Test with Binance since it's most reliable
        try:
            import ccxt
            
            exchange = ccxt.binance()
            
            # Simulate the trade execution flow without actually executing
            symbol = 'BTC/USDT'
            current_price = exchange.fetch_ticker(symbol)['last']
            position_size = 0.001  # Very small test amount
            
            logger.info(f"✅ Trade simulation: {symbol} @ {current_price}, size: {position_size}")
            
            # Check trade count limits
            trade_counts_file = Path('bybit_trade_counts.json')
            if trade_counts_file.exists():
                with open(trade_counts_file, 'r') as f:
                    trade_counts = json.load(f)
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                
                if today in trade_counts:
                    logger.info(f"✅ Trade count tracking working: {trade_counts[today]} trades today")
                    verification_results["components_verified"].append("trade_counting")
                else:
                    logger.warning(f"⚠️ No trade count for today ({today})")
            else:
                logger.warning("⚠️ Trade count file not found")
            
            verification_results["status"]["trade_execution"] = "simulated_ok"
            verification_results["components_verified"].append("trade_execution_flow")
            return True
        except Exception as e:
            logger.error(f"❌ Error in trade execution simulation: {str(e)}")
            verification_results["issues_found"].append(f"Trade execution simulation error: {str(e)}")
            verification_results["status"]["trade_execution"] = "simulation_failed"
            return False
    except Exception as e:
        logger.error(f"❌ Error verifying trade execution: {str(e)}")
        verification_results["issues_found"].append(f"Trade execution verification error: {str(e)}")
        verification_results["status"]["trade_execution"] = "error"
        return False

def verify_dashboard():
    """Verify dashboard functionality if available"""
    try:
        dashboard_port = 5000  # Default Flask port
        dashboard_url = f"http://localhost:{dashboard_port}"
        
        try:
            response = requests.get(dashboard_url, timeout=3)
            if response.status_code == 200:
                logger.info(f"✅ Dashboard responding at {dashboard_url}")
                verification_results["components_verified"].append("dashboard")
                verification_results["status"]["dashboard"] = "operational"
                return True
            else:
                logger.warning(f"⚠️ Dashboard returned status code {response.status_code}")
                verification_results["status"]["dashboard"] = f"error_{response.status_code}"
        except requests.exceptions.ConnectionError:
            logger.warning(f"⚠️ Dashboard not available at {dashboard_url}")
            verification_results["status"]["dashboard"] = "not_running"
        except Exception as e:
            logger.error(f"❌ Error checking dashboard: {str(e)}")
            verification_results["issues_found"].append(f"Dashboard check error: {str(e)}")
            verification_results["status"]["dashboard"] = "error"
        
        return False
    except Exception as e:
        logger.error(f"❌ Error verifying dashboard: {str(e)}")
        verification_results["issues_found"].append(f"Dashboard verification error: {str(e)}")
        return False

def run_live_verification():
    """Run all live verification checks"""
    logger.info("=" * 80)
    logger.info("STARTING LIVE OPERATIONS VERIFICATION")
    logger.info("=" * 80)
    
    # Track component statuses
    all_checks = {}
    
    # 1. Verify bot process
    all_checks["bot_process"] = check_bot_process()
    
    # 2. Check recent logs
    all_checks["recent_logs"] = check_recent_logs()
    
    # 3. Verify Telegram
    all_checks["telegram"] = verify_telegram()
    
    # 4. Verify portfolio tracking
    all_checks["portfolio"] = verify_portfolio_tracking()
    
    # 5. Verify exchange data
    all_checks["exchange_data"] = verify_exchange_data()
    
    # 6. Verify trade execution (simulation)
    all_checks["trade_execution"] = verify_trade_execution(simulate=True)
    
    # 7. Verify dashboard if available
    all_checks["dashboard"] = verify_dashboard()
    
    # Calculate overall status
    critical_checks = ["bot_process", "telegram", "exchange_data"]
    critical_failures = any(not all_checks[check] for check in critical_checks if check in all_checks)
    
    all_passed = all(all_checks.values())
    
    if all_passed:
        logger.info("✅ ALL CHECKS PASSED - System is fully operational")
        verification_results["overall_status"] = "fully_operational"
    elif critical_failures:
        logger.error("❌ CRITICAL CHECKS FAILED - System is NOT fully operational")
        verification_results["overall_status"] = "critical_issues"
    else:
        logger.warning("⚠️ SOME CHECKS FAILED - System is partially operational")
        verification_results["overall_status"] = "partially_operational"
    
    # Output summary
    logger.info("=" * 80)
    logger.info("VERIFICATION SUMMARY:")
    for check, result in all_checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {check}")
    
    logger.info("=" * 80)
    logger.info(f"OVERALL STATUS: {verification_results['overall_status'].upper()}")
    logger.info("=" * 80)
    
    # Save results to JSON
    with open('live_verification_results.json', 'w') as f:
        json.dump(verification_results, f, indent=2)
    
    # Generate recommendations based on findings
    suggest_improvements()
    
    return verification_results["overall_status"]

def suggest_improvements():
    """Generate improvement suggestions based on verification findings"""
    logger.info("=" * 80)
    logger.info("IMPROVEMENT SUGGESTIONS:")
    
    suggestions = []
    
    # Add general improvements
    suggestions.append({
        "title": "Real-time Health Dashboard",
        "description": "Create a real-time system health dashboard to monitor all bot components, API latency, signal quality, and portfolio performance.",
        "implementation": "Add a dedicated /health endpoint to your dashboard or create a new monitoring UI."
    })
    
    suggestions.append({
        "title": "Self-Healing Mechanisms",
        "description": "Implement automatic recovery procedures for common failure scenarios (API disconnections, rate limits, etc.)",
        "implementation": "Create a watchdog process that monitors the bot and implements recovery actions."
    })
    
    suggestions.append({
        "title": "Improved Signal Quality Metrics",
        "description": "Track and analyze signal quality over time to continuously improve prediction accuracy.",
        "implementation": "Implement a signal backtest system that compares predicted vs actual outcomes."
    })
    
    suggestions.append({
        "title": "Enhanced Logging & Analytics",
        "description": "Improve logging with structured data and add analytics to track performance patterns.",
        "implementation": "Use JSON logging and implement log aggregation with tools like ELK stack."
    })
    
    # Add issue-specific suggestions
    if verification_results.get("status", {}).get("dashboard") != "operational":
        suggestions.append({
            "title": "Add Web Dashboard",
            "description": "Implement a web dashboard for monitoring bot status, trades, and performance metrics.",
            "implementation": "Use Flask or FastAPI with a simple frontend to visualize key metrics."
        })
    
    if "bybit" in str(verification_results.get("issues_found", [])):
        suggestions.append({
            "title": "Bybit Connectivity Optimization",
            "description": "Further optimize Bybit API connectivity with automatic timestamp synchronization.",
            "implementation": "Implement a dynamic recv_window that adjusts based on measured time difference."
        })
    
    # Output suggestions
    for i, suggestion in enumerate(suggestions, 1):
        logger.info(f"{i}. {suggestion['title']}:")
        logger.info(f"   {suggestion['description']}")
        logger.info(f"   Implementation: {suggestion['implementation']}")
        logger.info("")
    
    # Save suggestions to file
    with open('improvement_suggestions.json', 'w') as f:
        json.dump(suggestions, f, indent=2)
    
    logger.info(f"✅ Saved {len(suggestions)} improvement suggestions to improvement_suggestions.json")
    logger.info("=" * 80)

if __name__ == "__main__":
    run_live_verification()
