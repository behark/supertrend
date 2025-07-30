#!/usr/bin/env python3
"""
Crypto Alert Bot - Feature Testing Script
----------------------------------------
This script tests all the advanced features of the Crypto Alert Bot to ensure they're working correctly.
"""
import os
import sys
import time
import logging
import json
import argparse
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create directories for tests
os.makedirs('test_results', exist_ok=True)
os.makedirs('models', exist_ok=True)
os.makedirs('charts/test', exist_ok=True)


def test_imports():
    """Test that all required modules are importable"""
    logger.info("Testing imports...")
    try:
        # Core dependencies
        import pandas as pd
        import numpy as np
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        import matplotlib.pyplot as plt
        import ccxt
        from dotenv import load_dotenv
        import telegram
        
        # Dashboard dependencies
        import dash
        import dash_bootstrap_components as dbc
        import plotly.graph_objects as go
        
        # ML dependencies
        from sklearn.ensemble import RandomForestClassifier
        import joblib
        
        # Local modules
        try:
            from telegram_client import TelegramClient
            from telegram_commands import TelegramCommandHandler
            from indicators import (
                check_volume_price_spike, 
                check_ma_cross, 
                check_breakout,
                rsi,
                calculate_risk_metrics
            )
            from risk_manager import RiskManager
            from chart_generator import ChartGenerator
            from backtester import Backtester
            from ml_predictor import MLPredictor
            from trader import Trader
            from multi_timeframe import MultiTimeframeAnalyzer
            from portfolio_manager import PortfolioManager
            from dashboard import Dashboard
            from config import (
                EXCHANGES,
                SCAN_INTERVAL,
                SYMBOLS_TO_SCAN,
                PROFIT_TARGET
            )
            
        except ImportError as e:
            logger.error(f"Failed to import local modules: {e}")
            return False
            
        logger.info("✅ All imports successful")
        return True
    
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return False


def test_telegram():
    """Test Telegram connectivity"""
    logger.info("Testing Telegram connectivity...")
    
    from telegram_client import TelegramClient
    from dotenv import load_dotenv
    
    load_dotenv()
    
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_bot_token or not chat_id:
        logger.error("Telegram credentials not found in environment variables")
        return False
    
    try:
        client = TelegramClient(telegram_bot_token, chat_id)
        
        test_message = (
            "🧪 TESTING: Basic Telegram functionality\n\n"
            "This is a test message from the Crypto Alert Bot testing suite.\n"
            f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        result = client.send_message(test_message)
        logger.info(f"Telegram send_message result: {result}")
        
        # Create a simple test chart
        import matplotlib.pyplot as plt
        import numpy as np
        
        plt.figure(figsize=(10, 6))
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        plt.plot(x, y)
        plt.title("Test Chart")
        plt.xlabel("X")
        plt.ylabel("Y")
        
        test_chart_path = "charts/test/telegram_test_chart.png"
        plt.savefig(test_chart_path)
        plt.close()
        
        chart_result = client.send_chart(test_chart_path, caption="Test Chart")
        logger.info(f"Telegram send_chart result: {chart_result}")
        
        logger.info("✅ Telegram connectivity test successful")
        return True
    
    except Exception as e:
        logger.error(f"Telegram connectivity test failed: {e}")
        return False


def test_backtester():
    """Test backtesting functionality"""
    logger.info("Testing backtesting...")
    
    try:
        from backtester import Backtester
        from config import SYMBOLS_TO_SCAN
        
        backtester = Backtester()
        
        # Test with one symbol and a short time period
        symbol = SYMBOLS_TO_SCAN[0] if SYMBOLS_TO_SCAN else "BTC/USDT"
        
        results = backtester.run_backtest(
            symbol=symbol,
            timeframe='1h',
            strategy_name='ma_cross',
            days=7  # Use a short period for the test
        )
        
        # Check if results contain expected keys
        required_keys = ['summary', 'trades', 'equity_curve', 'win_rate', 'profit_factor']
        
        for key in required_keys:
            if key not in results:
                logger.error(f"Backtest results missing key: {key}")
                return False
        
        # Save results to test_results directory
        with open('test_results/backtest_results.json', 'w') as f:
            # Convert to serializable format
            serializable_results = {
                k: v for k, v in results.items() 
                if k not in ['equity_curve']  # Skip non-serializable items
            }
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Backtest results: Win rate: {results['win_rate']:.2f}%, Profit factor: {results['profit_factor']:.2f}")
        logger.info("✅ Backtester test successful")
        return True
    
    except Exception as e:
        logger.error(f"Backtester test failed: {e}")
        return False


def test_ml_predictor():
    """Test ML predictor functionality"""
    logger.info("Testing ML predictor...")
    
    try:
        from ml_predictor import MLPredictor
        import pandas as pd
        import numpy as np
        from config import SYMBOLS_TO_SCAN
        import ccxt
        
        ml_predictor = MLPredictor(model_dir='models')
        
        # Create a dummy model for testing if not exists
        dummy_model_path = 'models/test_dummy_model.joblib'
        
        if not os.path.exists(dummy_model_path):
            from sklearn.ensemble import RandomForestClassifier
            import joblib
            
            # Create a simple dummy model
            dummy_model = RandomForestClassifier(n_estimators=10, random_state=42)
            X = np.random.rand(100, 5)  # 5 features
            y = np.random.randint(0, 2, 100)  # Binary classification
            dummy_model.fit(X, y)
            
            # Save the model
            joblib.dump(dummy_model, dummy_model_path)
            logger.info("Created dummy ML model for testing")
        
        # Fetch some actual data for prediction
        exchange = ccxt.binance()
        symbol = SYMBOLS_TO_SCAN[0] if SYMBOLS_TO_SCAN else "BTC/USDT"
        
        # Fetch recent data
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Test the prediction functionality
        try:
            # Try with the dummy model
            ml_predictor.model_dir = 'models'
            ml_predictor.default_model = 'test_dummy_model.joblib'
            
            prediction, confidence = ml_predictor.predict_signal_quality(
                df, 
                signal_type='test'
            )
            
            logger.info(f"ML prediction result: {prediction}, confidence: {confidence:.2f}%")
            
            # Also test the training function (with minimal data)
            ml_predictor.train_model(
                symbols=[symbol],
                timeframe='1h',
                strategy='test',
                days=3,  # Minimal training period
                save_model=False  # Don't save the test model
            )
            
            logger.info("✅ ML predictor test successful")
            return True
            
        except Exception as e:
            logger.error(f"ML prediction failed: {e}")
            return False
            
    except Exception as e:
        logger.error(f"ML predictor test failed: {e}")
        return False


def test_trader():
    """Test trading functionality (in dry-run mode)"""
    logger.info("Testing trader functionality (dry-run)...")
    
    try:
        from trader import Trader
        from config import SYMBOLS_TO_SCAN
        
        # Initialize trader in dry-run mode
        trader = Trader(dry_run=True)
        
        # Check if trader is enabled and in dry-run mode
        if not trader.is_enabled():
            logger.error("Trader should be enabled in dry-run mode")
            return False
            
        if not trader.dry_run:
            logger.error("Trader should be in dry-run mode for testing")
            return False
        
        # Test executing a trade in dry-run mode
        symbol = SYMBOLS_TO_SCAN[0] if SYMBOLS_TO_SCAN else "BTC/USDT"
        
        trade_result = trader.execute_trade(
            symbol=symbol,
            order_type='market',
            side='buy',
            amount=0.01,  # Small amount for testing
            price=50000,  # Sample price
            stop_loss=49000,
            take_profit=52000,
            strategy='test'
        )
        
        # Check if we got a simulated trade result
        if not trade_result or not isinstance(trade_result, dict):
            logger.error("Trader did not return a valid trade result")
            return False
            
        if 'id' not in trade_result:
            logger.error("Trade result missing order ID")
            return False
        
        logger.info(f"Trade execution result: {trade_result}")
        logger.info("✅ Trader test successful")
        return True
        
    except Exception as e:
        logger.error(f"Trader test failed: {e}")
        return False


def test_multi_timeframe():
    """Test multi-timeframe analysis"""
    logger.info("Testing multi-timeframe analysis...")
    
    try:
        from multi_timeframe import MultiTimeframeAnalyzer
        import ccxt
        from config import SYMBOLS_TO_SCAN
        
        # Initialize exchange and analyzer
        exchange = ccxt.binance()
        mtf_analyzer = MultiTimeframeAnalyzer(exchange)
        
        # Test confirmation across timeframes
        symbol = SYMBOLS_TO_SCAN[0] if SYMBOLS_TO_SCAN else "BTC/USDT"
        
        confidence, confirmed = mtf_analyzer.confirm_signal(
            symbol=symbol,
            base_timeframe='1h',
            signal_type='test',
            current_price=50000  # Sample price
        )
        
        logger.info(f"Multi-timeframe analysis: Confidence: {confidence:.2f}%, Confirmed: {confirmed}")
        logger.info("✅ Multi-timeframe analysis test successful")
        return True
        
    except Exception as e:
        logger.error(f"Multi-timeframe analysis test failed: {e}")
        return False


def test_portfolio_manager():
    """Test portfolio management functionality"""
    logger.info("Testing portfolio management...")
    
    try:
        from portfolio_manager import PortfolioManager
        
        # Initialize with test data
        portfolio_manager = PortfolioManager(
            initial_capital=10000,
            data_dir='test_results'
        )
        
        # Test adding a position
        position = portfolio_manager.add_position(
            symbol="BTC/USDT",
            entry_price=50000,
            quantity=0.1,
            stop_loss=48000,
            take_profit=55000,
            strategy="test"
        )
        
        # Test updating a position
        updated_position = portfolio_manager.update_position(
            position_id=position['id'],
            current_price=52000
        )
        
        # Test closing a position with profit
        closed_position = portfolio_manager.close_position(
            position_id=position['id'],
            exit_price=53000,
            exit_reason="test_take_profit"
        )
        
        # Test updating daily performance
        portfolio_manager.update_daily_performance()
        
        # Test getting portfolio statistics
        stats = portfolio_manager.get_portfolio_statistics()
        
        # Check if stats contain expected keys
        required_keys = ['total_return', 'win_rate', 'profit_factor', 'max_drawdown']
        
        for key in required_keys:
            if key not in stats:
                logger.error(f"Portfolio statistics missing key: {key}")
                return False
        
        # Test generating performance charts
        chart_path = portfolio_manager.generate_equity_curve_chart()
        
        logger.info(f"Portfolio statistics: {stats}")
        logger.info("✅ Portfolio manager test successful")
        return True
        
    except Exception as e:
        logger.error(f"Portfolio manager test failed: {e}")
        return False


def test_telegram_commands():
    """Test Telegram command handler"""
    logger.info("Testing Telegram command handler...")
    
    try:
        from telegram_commands import TelegramCommandHandler
        from dotenv import load_dotenv
        
        load_dotenv()
        
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not chat_id:
            logger.error("Telegram chat ID not found in environment variables")
            return False
        
        # Initialize handler but don't start it
        handler = TelegramCommandHandler()
        
        # Test handling various commands without actually sending them
        commands = [
            "/help",
            "/status",
            "/alerts",
            "/enable volume_spike",
            "/disable breakout",
            "/set volume_threshold 3",
            "/watchlist",
            "/performance",
        ]
        
        for command in commands:
            # Just check if the methods exist and are callable
            if command.startswith("/help"):
                handler.handle_help_command(chat_id)
            elif command.startswith("/status"):
                handler.handle_status_command(chat_id)
            elif command.startswith("/alerts"):
                handler.handle_alerts_command(chat_id)
            elif command.startswith("/enable"):
                strategy = command.split(" ")[1] if len(command.split(" ")) > 1 else "volume_spike"
                handler.handle_enable_command(chat_id, strategy)
            elif command.startswith("/disable"):
                strategy = command.split(" ")[1] if len(command.split(" ")) > 1 else "breakout"
                handler.handle_disable_command(chat_id, strategy)
            elif command.startswith("/set"):
                param = command.split(" ")[1] if len(command.split(" ")) > 1 else "volume_threshold"
                value = command.split(" ")[2] if len(command.split(" ")) > 2 else "3"
                handler.handle_set_command(chat_id, param, value)
            elif command.startswith("/watchlist"):
                handler.handle_watchlist_command(chat_id)
            elif command.startswith("/performance"):
                handler.handle_performance_command(chat_id)
        
        # Test the test message function
        handler.send_test_message(chat_id)
        
        logger.info("✅ Telegram command handler test successful")
        return True
        
    except Exception as e:
        logger.error(f"Telegram command handler test failed: {e}")
        return False


def test_dashboard():
    """Test dashboard functionality"""
    logger.info("Testing dashboard...")
    
    try:
        from dashboard import Dashboard
        import threading
        import requests
        import time
        
        # Initialize dashboard but don't start it
        dashboard = Dashboard(port=8051)  # Use different port for testing
        
        # Start the dashboard in a separate thread
        dashboard_thread = threading.Thread(target=dashboard.run)
        dashboard_thread.daemon = True
        dashboard_thread.start()
        
        # Wait for the dashboard to start
        time.sleep(5)
        
        # Try to access the dashboard
        try:
            response = requests.get("http://localhost:8051")
            if response.status_code != 200:
                logger.error(f"Dashboard returned status code {response.status_code}")
                return False
                
            logger.info("Dashboard is running and accessible")
        except Exception as e:
            logger.error(f"Failed to access dashboard: {e}")
            return False
        
        logger.info("✅ Dashboard test successful")
        return True
        
    except Exception as e:
        logger.error(f"Dashboard test failed: {e}")
        return False


def run_all_tests():
    """Run all tests and return the results"""
    results = {}
    
    test_functions = [
        test_imports,
        test_telegram,
        test_backtester,
        test_ml_predictor,
        test_trader,
        test_multi_timeframe,
        test_portfolio_manager,
        test_telegram_commands,
        test_dashboard
    ]
    
    all_passed = True
    
    for test_func in test_functions:
        test_name = test_func.__name__
        logger.info(f"\n{'='*50}\nRunning {test_name}\n{'='*50}")
        
        try:
            result = test_func()
            results[test_name] = result
            
            if not result:
                all_passed = False
                
        except Exception as e:
            logger.error(f"Error running {test_name}: {e}")
            results[test_name] = False
            all_passed = False
    
    return results, all_passed


def main():
    """Main function to run tests"""
    parser = argparse.ArgumentParser(description="Test Crypto Alert Bot Features")
    parser.add_argument("--test", help="Run specific test (imports, telegram, backtester, ml, trader, mtf, portfolio, commands, dashboard)")
    args = parser.parse_args()
    
    logger.info("Starting Crypto Alert Bot feature tests")
    
    if args.test:
        # Run specific test
        test_map = {
            "imports": test_imports,
            "telegram": test_telegram,
            "backtester": test_backtester,
            "ml": test_ml_predictor,
            "trader": test_trader,
            "mtf": test_multi_timeframe,
            "portfolio": test_portfolio_manager,
            "commands": test_telegram_commands,
            "dashboard": test_dashboard
        }
        
        if args.test in test_map:
            result = test_map[args.test]()
            logger.info(f"Test {args.test}: {'PASSED' if result else 'FAILED'}")
        else:
            logger.error(f"Unknown test: {args.test}")
            logger.info(f"Available tests: {', '.join(test_map.keys())}")
    else:
        # Run all tests
        results, all_passed = run_all_tests()
        
        # Print summary
        logger.info("\n" + "="*50)
        logger.info("TEST SUMMARY")
        logger.info("="*50)
        
        for test_name, passed in results.items():
            logger.info(f"{test_name}: {'✅ PASSED' if passed else '❌ FAILED'}")
        
        logger.info("="*50)
        logger.info(f"Overall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
        logger.info("="*50)
        
        # Save results to file
        with open('test_results/test_summary.json', 'w') as f:
            json.dump({k: "PASSED" if v else "FAILED" for k, v in results.items()}, f, indent=2)
        
        return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
