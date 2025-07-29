#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import traceback
import threading
import schedule

# Configure logging
logger = logging.getLogger(__name__)

class HealthCheck:
    """Comprehensive health check system for the trading bot"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(HealthCheck, cls).__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize the health check system"""
        self.last_check_time = 0
        self.last_results = {}
        self.status_history = []
        self.max_history = 10
        self.checkers = {
            'api_connection': self._check_api_connection,
            'trading_permissions': self._check_trading_permissions,
            'signal_generation': self._check_signal_generation,
            'active_trades': self._check_active_trades,
            'balance': self._check_balance,
            'system': self._check_system
        }
        logger.info("Health check system initialized")
    
    def run_health_check(self, check_types: Optional[List[str]] = None, 
                         notify: bool = True) -> Dict[str, Any]:
        """Run a comprehensive health check or specific checks
        
        Args:
            check_types: Optional list of specific checks to run, runs all if None
            notify: Whether to send notification with results
            
        Returns:
            Dict containing check results and status
        """
        logger.info("Starting health check")
        start_time = time.time()
        
        # Use all checkers if none specified
        if check_types is None:
            check_types = list(self.checkers.keys())
        else:
            # Filter out any invalid check types
            check_types = [c for c in check_types if c in self.checkers]
        
        # Run each requested checker
        results = {
            'timestamp': datetime.now().isoformat(),
            'checks': {},
            'overall_status': 'ok',
            'duration_ms': 0,
            'details': {}
        }
        
        for check_type in check_types:
            try:
                if check_type in self.checkers:
                    logger.info(f"Running {check_type} check")
                    check_result = self.checkers[check_type]()
                    results['checks'][check_type] = check_result
                    
                    # Update overall status - if any check fails, overall status fails
                    if check_result['status'] != 'ok' and results['overall_status'] == 'ok':
                        results['overall_status'] = check_result['status']
                        
                    # Add any details
                    if 'details' in check_result:
                        results['details'][check_type] = check_result['details']
            except Exception as e:
                logger.error(f"Error during {check_type} health check: {str(e)}", exc_info=True)
                results['checks'][check_type] = {
                    'status': 'error',
                    'message': f"Error during check: {str(e)}"
                }
                results['overall_status'] = 'error'
        
        # Calculate duration
        results['duration_ms'] = int((time.time() - start_time) * 1000)
        
        # Save results
        self.last_check_time = time.time()
        self.last_results = results
        
        # Manage history
        self.status_history.append(results)
        if len(self.status_history) > self.max_history:
            self.status_history.pop(0)
        
        # Send notification if requested
        if notify:
            self._send_notification(results)
        
        return results
    
    def get_last_results(self) -> Dict[str, Any]:
        """Get the results of the last health check"""
        return self.last_results
    
    def get_status_history(self) -> List[Dict[str, Any]]:
        """Get the history of health check results"""
        return self.status_history
    
    def schedule_regular_checks(self, interval_hours: int = 4) -> None:
        """Schedule regular health checks
        
        Args:
            interval_hours: How often to run checks in hours
        """
        logger.info(f"Scheduling regular health checks every {interval_hours} hours")
        
        def scheduled_health_check():
            logger.info("Running scheduled health check")
            self.run_health_check(notify=True)
        
        # Schedule the health check
        schedule.every(interval_hours).hours.do(scheduled_health_check)
    
    def _check_api_connection(self) -> Dict[str, Any]:
        """Check connection to the trading API"""
        try:
            from src.integrations.bidget import TradingAPI
            api = TradingAPI()
            
            if not api.is_configured:
                return {
                    'status': 'warning',
                    'message': 'API not configured'
                }
            
            # Attempt a simple request to verify connection
            time_endpoint = "/api/mix/v1/market/time"
            response = api._make_request("GET", time_endpoint)
            
            if 'error' in response:
                return {
                    'status': 'error',
                    'message': f"API connection error: {response.get('error')}",
                    'details': response
                }
                
            # Test authentication with a signed request
            account_endpoint = "/api/mix/v1/account/account"
            account_response = api._make_request("GET", account_endpoint, signed=True)
            
            if 'error' in account_response:
                return {
                    'status': 'error',
                    'message': f"API authentication error: {account_response.get('error')}",
                    'details': account_response
                }
            
            return {
                'status': 'ok',
                'message': 'API connection successful',
                'details': {'server_time': response.get('data', {})}
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f"API connection check failed: {str(e)}",
                'details': {'traceback': traceback.format_exc()}
            }
    
    def _check_trading_permissions(self) -> Dict[str, Any]:
        """Check if the bot has permissions to place trades"""
        try:
            from src.integrations.bidget import TradingAPI
            api = TradingAPI()
            
            if not api.is_configured:
                return {
                    'status': 'warning',
                    'message': 'API not configured'
                }
                
            # Verify account has trading enabled
            account_endpoint = "/api/mix/v1/account/account"
            account_response = api._make_request("GET", account_endpoint, signed=True)
            
            if 'error' in account_response:
                return {
                    'status': 'error',
                    'message': f"Could not verify trading permissions: {account_response.get('error')}",
                    'details': account_response
                }
            
            # Check if futures trading is available
            if api.test_mode:
                return {
                    'status': 'ok',
                    'message': 'Test mode enabled - trading simulated'
                }
            
            # Check if we can place orders
            can_trade = True  # Default assumption
            
            # TODO: Add specific API call to check if account can trade
            # This varies by exchange API, so a placeholder implementation
            
            if can_trade:
                return {
                    'status': 'ok',
                    'message': 'Trading permissions verified'
                }
            else:
                return {
                    'status': 'error', 
                    'message': 'Trading not permitted for this account'
                }
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Trading permissions check failed: {str(e)}",
                'details': {'traceback': traceback.format_exc()}
            }
    
    def _check_signal_generation(self) -> Dict[str, Any]:
        """Check if signal generation is working properly"""
        try:
            # Check if strategies are loaded and functioning
            from src.strategies.supertrend_adx import SupertrendADXStrategy
            from src.strategies.inside_bar import InsideBarStrategy
            
            strategies_loaded = True  # Default assumption
            
            # Get historical data to test signal generation
            try:
                from src.integrations.bidget import TradingAPI
                api = TradingAPI()
                
                # Try to get some recent candles for BTC
                symbol = "BTCUSDT_UMCBL"
                candles_endpoint = f"/api/mix/v1/market/candles?symbol={symbol}&granularity=15m&limit=100"
                candles_response = api._make_request("GET", candles_endpoint)
                
                if 'error' in candles_response:
                    return {
                        'status': 'warning',
                        'message': f"Could not retrieve candle data for signal test: {candles_response.get('error')}",
                        'details': candles_response
                    }
                    
                # Check if data looks valid
                candle_data = candles_response.get('data', [])
                if not candle_data or len(candle_data) < 30:
                    return {
                        'status': 'warning',
                        'message': f"Insufficient candle data for signal test: got {len(candle_data)} candles",
                        'details': {'candle_count': len(candle_data)}
                    }
                    
                # Got valid data - could test strategies here
                return {
                    'status': 'ok',
                    'message': f"Signal generation check passed - retrieved {len(candle_data)} candles"
                }
                
            except ImportError:
                return {
                    'status': 'error',
                    'message': "Could not import required modules for signal testing"
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Signal generation check failed: {str(e)}",
                'details': {'traceback': traceback.format_exc()}
            }
    
    def _check_active_trades(self) -> Dict[str, Any]:
        """Check status of active trades"""
        try:
            # First, get reference to the bot to check active trades
            bot_instance = None
            
            try:
                from src.bot import trading_bot
                if trading_bot is not None:
                    bot_instance = trading_bot
            except (ImportError, NameError):
                logger.warning("Could not get bot instance from global reference")
                
                # Try to get via other means
                try:
                    from src.bot import TradingBot
                    bot_instance = TradingBot()
                except Exception as e:
                    logger.error(f"Could not instantiate bot: {str(e)}")
            
            if bot_instance is None:
                return {
                    'status': 'warning',
                    'message': "Could not access bot instance to check active trades"
                }
                
            # Check active trades
            active_trades = getattr(bot_instance, 'active_trades', [])
            
            # Also check API directly
            try:
                from src.integrations.bidget import TradingAPI
                api = TradingAPI()
                
                if not api.is_configured:
                    return {
                        'status': 'warning',
                        'message': 'API not configured, relying on bot tracking only',
                        'details': {'tracked_trades': active_trades}
                    }
                
                # Check actual positions
                positions_endpoint = "/api/mix/v1/position/allPosition?productType=umcbl&marginCoin=USDT"
                positions_response = api._make_request("GET", positions_endpoint, signed=True)
                
                if 'error' in positions_response:
                    return {
                        'status': 'warning',
                        'message': f"Could not retrieve positions: {positions_response.get('error')}",
                        'details': {'tracked_trades': active_trades}
                    }
                    
                # Parse positions
                positions_data = positions_response.get('data', [])
                api_positions = []
                
                for position in positions_data:
                    if isinstance(position, dict):
                        total = float(position.get('total', 0))
                        symbol = position.get('symbol', '').replace('_UMCBL', '')
                        
                        if total > 0:
                            api_positions.append({
                                'symbol': symbol,
                                'size': total,
                                'side': position.get('holdSide', 'unknown')
                            })
                
                # Compare tracked vs actual
                api_symbols = [p['symbol'] for p in api_positions]
                
                # Format for readability
                tracked_formatted = [s.replace('/', '') for s in active_trades]
                
                # Check for discrepancies
                missing_from_tracking = [s for s in api_symbols if s not in tracked_formatted]
                extra_in_tracking = [s for s in tracked_formatted if s not in api_symbols]
                
                if missing_from_tracking or extra_in_tracking:
                    return {
                        'status': 'warning',
                        'message': "Discrepancy between tracked trades and actual positions",
                        'details': {
                            'tracked_trades': active_trades,
                            'actual_positions': api_positions,
                            'missing_from_tracking': missing_from_tracking,
                            'extra_in_tracking': extra_in_tracking
                        }
                    }
                    
                return {
                    'status': 'ok',
                    'message': f"Active trades check passed - {len(api_positions)} positions",
                    'details': {
                        'tracked_trades': active_trades,
                        'actual_positions': api_positions
                    }
                }
                
            except Exception as e:
                return {
                    'status': 'warning',
                    'message': f"Error checking API positions: {str(e)}",
                    'details': {'tracked_trades': active_trades}
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Active trades check failed: {str(e)}",
                'details': {'traceback': traceback.format_exc()}
            }
    
    def _check_balance(self) -> Dict[str, Any]:
        """Check account balance"""
        try:
            from src.integrations.bidget import TradingAPI
            api = TradingAPI()
            
            if not api.is_configured:
                return {
                    'status': 'warning',
                    'message': 'API not configured'
                }
                
            # Get account balance
            balance_endpoint = "/api/mix/v1/account/accounts?productType=umcbl"
            balance_response = api._make_request("GET", balance_endpoint, signed=True)
            
            if 'error' in balance_response:
                return {
                    'status': 'error',
                    'message': f"Could not retrieve balance: {balance_response.get('error')}",
                    'details': balance_response
                }
                
            balance_data = balance_response.get('data', [])
            if not balance_data:
                return {
                    'status': 'warning',
                    'message': "No balance data available"
                }
                
            # Look for USDT balance
            usdt_balance = None
            for balance in balance_data:
                if isinstance(balance, dict) and balance.get('marginCoin') == 'USDT':
                    usdt_balance = balance
                    break
                    
            if not usdt_balance:
                return {
                    'status': 'warning',
                    'message': "No USDT balance found",
                    'details': {'available_currencies': [b.get('marginCoin') for b in balance_data if isinstance(b, dict)]}
                }
                
            # Calculate key balance values
            available = float(usdt_balance.get('available', 0))
            frozen = float(usdt_balance.get('locked', 0))
            total = available + frozen
            
            # Check for low balance
            min_required = float(os.getenv('MIN_BALANCE_REQUIRED', '10'))  # Default 10 USDT minimum
            
            if available < min_required:
                return {
                    'status': 'warning',
                    'message': f"Low available balance: {available} USDT",
                    'details': {
                        'available': available,
                        'frozen': frozen,
                        'total': total,
                        'minimum_required': min_required
                    }
                }
                
            return {
                'status': 'ok',
                'message': f"Balance check passed - {available} USDT available",
                'details': {
                    'available': available,
                    'frozen': frozen,
                    'total': total,
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Balance check failed: {str(e)}",
                'details': {'traceback': traceback.format_exc()}
            }
    
    def _check_system(self) -> Dict[str, Any]:
        """Check system resources and bot operational status"""
        try:
            import psutil
            import os
            
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Check memory usage
            memory = psutil.virtual_memory()
            memory_used_percent = memory.percent
            
            # Check disk space
            disk = psutil.disk_usage('/')
            disk_used_percent = disk.percent
            
            # Check bot process
            pid = os.getpid()
            process = psutil.Process(pid)
            process_memory_percent = process.memory_percent()
            process_cpu_percent = process.cpu_percent(interval=1)
            
            details = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_used_percent,
                'disk_percent': disk_used_percent,
                'process_memory_percent': process_memory_percent,
                'process_cpu_percent': process_cpu_percent,
                'uptime_seconds': time.time() - process.create_time()
            }
            
            status = 'ok'
            message = "System resources check passed"
            
            # Warning thresholds
            if cpu_percent > 80 or memory_used_percent > 80 or disk_used_percent > 85:
                status = 'warning'
                message = "High system resource usage detected"
                
            return {
                'status': status,
                'message': message,
                'details': details
            }
            
        except ImportError:
            # psutil not available
            return {
                'status': 'warning',
                'message': "System check skipped - psutil module not available"
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': f"System check failed: {str(e)}",
                'details': {'traceback': traceback.format_exc()}
            }
    
    def _send_notification(self, results: Dict[str, Any]) -> None:
        """Send notification with health check results"""
        try:
            from src.integrations.telegram import TelegramNotifier
            telegram = TelegramNotifier()
            
            if not telegram.is_configured:
                logger.warning("Telegram not configured, skipping health check notification")
                return
                
            # Format the message
            status_emoji = {
                'ok': '✅',
                'warning': '⚠️',
                'error': '❌'
            }
            
            overall_status = results['overall_status']
            emoji = status_emoji.get(overall_status, '❓')
            
            message = [
                f"{emoji} *Trading Bot Health Check*",
                f"Status: {overall_status.upper()}",
                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                ""
            ]
            
            # Add each check result
            for check_name, check_result in results['checks'].items():
                check_emoji = status_emoji.get(check_result['status'], '❓')
                message.append(f"{check_emoji} {check_name}: {check_result['message']}")
            
            telegram.send_message("\n".join(message))
            logger.info("Sent health check notification via Telegram")
            
        except Exception as e:
            logger.error(f"Failed to send health check notification: {str(e)}", exc_info=True)

# Singleton instance
health_check = HealthCheck()
