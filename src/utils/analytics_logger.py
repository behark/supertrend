#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Analytics Logger Module

Provides enhanced structured logging capabilities for trading bot analytics:
- JSON-formatted logs for automated processing
- Performance metrics collection
- Trade analytics and summary reports
- Strategy effectiveness tracking
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import threading
from functools import wraps
import time
import statistics
from datetime import datetime, timedelta

# Configure module logger
logger = logging.getLogger(__name__)

class AnalyticsLogger:
    """
    Enhanced analytics logger with structured data output and performance tracking
    """
    
    # Singleton implementation
    _instance = None
    _lock = threading.Lock()
    
    # Directory for analytics data
    ANALYTICS_DIR = "analytics"
    
    # File paths
    TRADES_LOG = "trades.jsonl"
    SIGNALS_LOG = "signals.jsonl"
    PERFORMANCE_LOG = "performance.jsonl"
    ERRORS_LOG = "errors.jsonl"
    STRATEGY_METRICS_LOG = "strategy_metrics.jsonl"
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AnalyticsLogger, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
            
    def __init__(self):
        """Initialize the analytics logger"""
        if getattr(self, '_initialized', False):
            return
            
        # Create analytics directory if it doesn't exist
        self.base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            self.ANALYTICS_DIR
        )
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Performance tracking
        self._performance_data = {
            'api_calls': [],
            'strategy_execution': [],
            'signal_processing': []
        }
        
        # Trade performance metrics
        self._trade_metrics = {
            'total_trades': 0,
            'profitable_trades': 0,
            'total_profit': 0.0,
            'total_loss': 0.0,
            'win_rate': 0.0,
            'avg_profit_percent': 0.0,
            'avg_loss_percent': 0.0,
            'max_drawdown': 0.0,
            'longest_winning_streak': 0,
            'longest_losing_streak': 0
        }
        
        # Strategy performance metrics
        self._strategy_metrics = {}
        
        # Signal metrics
        self._signal_metrics = {
            'total_signals': 0,
            'executed_signals': 0,
            'signal_accuracy': 0.0,
            'signals_by_strategy': {}
        }
        
        # Daily summary data
        self._daily_summary = {}
        
        # Flags and locks
        self._last_summary_date = datetime.now().date()
        self._initialized = True
        
        logger.info(f"Analytics logger initialized. Data directory: {self.base_dir}")
    
    def _write_jsonl(self, filename: str, data: Dict) -> None:
        """
        Write JSON line to file
        
        Args:
            filename: Target filename
            data: Data dictionary to write
        """
        filepath = os.path.join(self.base_dir, filename)
        try:
            # Add timestamp if not present
            if 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()
                
            # Append to file
            with open(filepath, 'a') as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            logger.error(f"Failed to write analytics data to {filepath}: {e}", exc_info=True)
    
    def log_trade(self, 
                  symbol: str, 
                  trade_type: str,
                  entry_price: float,
                  exit_price: Optional[float] = None,
                  position_size: float = 0.0,
                  profit_loss: Optional[float] = None,
                  profit_loss_percent: Optional[float] = None,
                  take_profit: Optional[float] = None,
                  stop_loss: Optional[float] = None,
                  trade_id: Optional[str] = None,
                  strategy: Optional[str] = None,
                  status: str = "open",
                  metadata: Optional[Dict] = None) -> None:
        """
        Log trade data for analytics
        
        Args:
            symbol: Trading pair symbol
            trade_type: Type of trade ('long' or 'short')
            entry_price: Entry price of the trade
            exit_price: Exit price (if trade is closed)
            position_size: Size of position in base currency
            profit_loss: Absolute profit/loss (if trade is closed)
            profit_loss_percent: Percentage profit/loss (if trade is closed)
            take_profit: Take profit level
            stop_loss: Stop loss level
            trade_id: Unique trade identifier
            strategy: Strategy that generated the trade signal
            status: Trade status ('open', 'closed', 'canceled')
            metadata: Additional trade metadata
        """
        # Create trade data dictionary
        trade_data = {
            'symbol': symbol,
            'trade_type': trade_type,
            'entry_price': entry_price,
            'position_size': position_size,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'trade_id': trade_id,
            'strategy': strategy,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add optional fields if present
        if exit_price is not None:
            trade_data['exit_price'] = exit_price
        if profit_loss is not None:
            trade_data['profit_loss'] = profit_loss
        if profit_loss_percent is not None:
            trade_data['profit_loss_percent'] = profit_loss_percent
        if metadata:
            trade_data['metadata'] = metadata
            
        # Write to trade log
        self._write_jsonl(self.TRADES_LOG, trade_data)
        
        # Update trade metrics if trade is closed
        if status == 'closed' and profit_loss is not None:
            self._update_trade_metrics(trade_data)
    
    def log_signal(self,
                   symbol: str,
                   signal_type: str,
                   confidence: float,
                   strategy: str,
                   timeframe: str,
                   executed: bool = False,
                   reason_rejected: Optional[str] = None,
                   metadata: Optional[Dict] = None) -> None:
        """
        Log trade signal data for analytics
        
        Args:
            symbol: Trading pair symbol
            signal_type: Type of signal ('long', 'short', 'exit')
            confidence: Signal confidence percentage
            strategy: Strategy that generated the signal
            timeframe: Timeframe of the signal
            executed: Whether signal was executed as a trade
            reason_rejected: Reason signal was rejected (if applicable)
            metadata: Additional signal metadata
        """
        # Create signal data dictionary
        signal_data = {
            'symbol': symbol,
            'signal_type': signal_type,
            'confidence': confidence,
            'strategy': strategy,
            'timeframe': timeframe,
            'executed': executed,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add optional fields if present
        if reason_rejected:
            signal_data['reason_rejected'] = reason_rejected
        if metadata:
            signal_data['metadata'] = metadata
            
        # Write to signal log
        self._write_jsonl(self.SIGNALS_LOG, signal_data)
        
        # Update signal metrics
        self._update_signal_metrics(signal_data)
    
    def log_error(self,
                  error_type: str,
                  message: str,
                  severity: str = "medium",
                  context: Optional[Dict] = None,
                  traceback: Optional[str] = None) -> None:
        """
        Log error data for analytics
        
        Args:
            error_type: Type of error (e.g. 'api', 'strategy', 'connection')
            message: Error message
            severity: Error severity ('low', 'medium', 'high', 'critical')
            context: Additional context information
            traceback: Exception traceback if available
        """
        # Create error data dictionary
        error_data = {
            'error_type': error_type,
            'message': message,
            'severity': severity,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add optional fields if present
        if context:
            error_data['context'] = context
        if traceback:
            error_data['traceback'] = traceback
            
        # Write to error log
        self._write_jsonl(self.ERRORS_LOG, error_data)
    
    def log_performance(self,
                        operation: str,
                        duration_ms: float,
                        success: bool = True,
                        metadata: Optional[Dict] = None) -> None:
        """
        Log performance data for analytics
        
        Args:
            operation: Operation being measured
            duration_ms: Duration in milliseconds
            success: Whether operation was successful
            metadata: Additional performance metadata
        """
        # Create performance data dictionary
        perf_data = {
            'operation': operation,
            'duration_ms': duration_ms,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add optional fields if present
        if metadata:
            perf_data['metadata'] = metadata
            
        # Write to performance log
        self._write_jsonl(self.PERFORMANCE_LOG, perf_data)
        
        # Track in memory for aggregation
        category = metadata.get('category', 'other') if metadata else 'other'
        if category in self._performance_data:
            self._performance_data[category].append({
                'operation': operation,
                'duration_ms': duration_ms,
                'success': success,
                'timestamp': datetime.now().isoformat()
            })
    
    def log_strategy_metrics(self,
                             strategy_name: str,
                             signal_count: int,
                             success_rate: float,
                             avg_gain: float,
                             metadata: Optional[Dict] = None) -> None:
        """
        Log strategy performance metrics
        
        Args:
            strategy_name: Name of the trading strategy
            signal_count: Number of signals generated
            success_rate: Success rate of signals (0.0-1.0)
            avg_gain: Average gain from successful signals
            metadata: Additional strategy metrics
        """
        # Create strategy metrics data dictionary
        metrics_data = {
            'strategy': strategy_name,
            'signal_count': signal_count,
            'success_rate': success_rate,
            'avg_gain': avg_gain,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add optional fields if present
        if metadata:
            metrics_data['metadata'] = metadata
            
        # Write to strategy metrics log
        self._write_jsonl(self.STRATEGY_METRICS_LOG, metrics_data)
        
        # Update in-memory metrics
        if strategy_name not in self._strategy_metrics:
            self._strategy_metrics[strategy_name] = {
                'total_signals': 0,
                'successful_signals': 0,
                'failed_signals': 0,
                'total_gain': 0.0,
                'accuracy': 0.0
            }
            
        # Update strategy metrics
        metrics = self._strategy_metrics[strategy_name]
        metrics['total_signals'] += signal_count
        metrics['successful_signals'] += int(signal_count * success_rate)
        metrics['failed_signals'] += int(signal_count * (1 - success_rate))
        metrics['total_gain'] += avg_gain * int(signal_count * success_rate)
        if metrics['total_signals'] > 0:
            metrics['accuracy'] = metrics['successful_signals'] / metrics['total_signals']
    
    def _update_trade_metrics(self, trade_data: Dict) -> None:
        """Update trade metrics based on completed trade"""
        self._trade_metrics['total_trades'] += 1
        
        profit_loss = trade_data.get('profit_loss', 0.0)
        if profit_loss > 0:
            self._trade_metrics['profitable_trades'] += 1
            self._trade_metrics['total_profit'] += profit_loss
        else:
            self._trade_metrics['total_loss'] += abs(profit_loss)
            
        # Update win rate
        if self._trade_metrics['total_trades'] > 0:
            self._trade_metrics['win_rate'] = (
                self._trade_metrics['profitable_trades'] / self._trade_metrics['total_trades']
            )
    
    def _update_signal_metrics(self, signal_data: Dict) -> None:
        """Update signal metrics based on new signal"""
        self._signal_metrics['total_signals'] += 1
        
        if signal_data['executed']:
            self._signal_metrics['executed_signals'] += 1
            
        # Update signal accuracy
        if self._signal_metrics['total_signals'] > 0:
            self._signal_metrics['signal_accuracy'] = (
                self._signal_metrics['executed_signals'] / self._signal_metrics['total_signals']
            )
            
        # Track by strategy
        strategy = signal_data['strategy']
        if strategy not in self._signal_metrics['signals_by_strategy']:
            self._signal_metrics['signals_by_strategy'][strategy] = {
                'total': 0,
                'executed': 0
            }
            
        self._signal_metrics['signals_by_strategy'][strategy]['total'] += 1
        if signal_data['executed']:
            self._signal_metrics['signals_by_strategy'][strategy]['executed'] += 1
    
    def generate_daily_summary(self, force: bool = False) -> Optional[Dict]:
        """
        Generate daily performance summary
        
        Args:
            force: Force generation even if already generated today
            
        Returns:
            Summary data dictionary or None if no summary generated
        """
        today = datetime.now().date()
        
        # Check if we already generated a summary today unless forced
        if not force and today == self._last_summary_date:
            return None
            
        # Update last summary date
        self._last_summary_date = today
        
        # Calculate yesterday's date for the report
        yesterday = today - timedelta(days=1)
        yesterday_str = yesterday.isoformat()
        
        # Prepare summary data
        summary = {
            'date': yesterday_str,
            'trades': {
                'total': self._trade_metrics['total_trades'],
                'profitable': self._trade_metrics['profitable_trades'],
                'win_rate': self._trade_metrics['win_rate'],
                'total_profit': self._trade_metrics['total_profit'],
                'total_loss': self._trade_metrics['total_loss'],
                'net_pnl': self._trade_metrics['total_profit'] - self._trade_metrics['total_loss']
            },
            'signals': {
                'total': self._signal_metrics['total_signals'],
                'executed': self._signal_metrics['executed_signals'],
                'execution_rate': self._signal_metrics['signal_accuracy'],
                'by_strategy': self._signal_metrics['signals_by_strategy']
            },
            'strategies': {},
            'performance': {}
        }
        
        # Add strategy metrics
        for strategy, metrics in self._strategy_metrics.items():
            summary['strategies'][strategy] = {
                'signals': metrics['total_signals'],
                'accuracy': metrics['accuracy'],
                'total_gain': metrics['total_gain']
            }
            
        # Add performance metrics
        for category, data in self._performance_data.items():
            if not data:
                continue
                
            durations = [item['duration_ms'] for item in data]
            success_count = sum(1 for item in data if item['success'])
            success_rate = success_count / len(data) if data else 0
            
            summary['performance'][category] = {
                'count': len(data),
                'avg_duration_ms': sum(durations) / len(durations) if durations else 0,
                'min_duration_ms': min(durations) if durations else 0,
                'max_duration_ms': max(durations) if durations else 0,
                'success_rate': success_rate
            }
            
        # Write summary to file
        summary_file = f"summary_{yesterday_str}.json"
        try:
            with open(os.path.join(self.base_dir, summary_file), 'w') as f:
                json.dump(summary, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write summary to {summary_file}: {e}", exc_info=True)
            
        # Store in daily summaries
        self._daily_summary[yesterday_str] = summary
        
        return summary
    
    def generate_weekly_summary(self) -> Optional[Dict]:
        """
        Generate weekly performance summary
        
        Returns:
            Weekly summary data dictionary or None if not enough data
        """
        today = datetime.now().date()
        
        # Only generate on Mondays
        if today.weekday() != 0:  # Monday is 0
            return None
        
        # Calculate the date range for the previous week
        end_date = today - timedelta(days=1)  # Sunday
        start_date = end_date - timedelta(days=6)  # Previous Monday
        
        week_str = f"{start_date.isoformat()}_to_{end_date.isoformat()}"
        
        # Aggregate daily summaries for the week
        weekly_data = {
            'period': week_str,
            'trades': {
                'total': 0,
                'profitable': 0,
                'win_rate': 0.0,
                'total_profit': 0.0,
                'total_loss': 0.0,
                'net_pnl': 0.0
            },
            'signals': {
                'total': 0,
                'executed': 0,
                'execution_rate': 0.0
            },
            'strategies': {},
            'daily_breakdown': {}
        }
        
        # Find relevant daily summaries
        for date_str, summary in self._daily_summary.items():
            try:
                date = datetime.fromisoformat(date_str).date()
                if start_date <= date <= end_date:
                    # Add to weekly totals
                    weekly_data['trades']['total'] += summary['trades']['total']
                    weekly_data['trades']['profitable'] += summary['trades']['profitable']
                    weekly_data['trades']['total_profit'] += summary['trades']['total_profit']
                    weekly_data['trades']['total_loss'] += summary['trades']['total_loss']
                    weekly_data['signals']['total'] += summary['signals']['total']
                    weekly_data['signals']['executed'] += summary['signals']['executed']
                    
                    # Store daily breakdown
                    weekly_data['daily_breakdown'][date_str] = {
                        'trades': summary['trades']['total'],
                        'net_pnl': summary['trades']['net_pnl']
                    }
                    
                    # Aggregate strategy data
                    for strategy, metrics in summary.get('strategies', {}).items():
                        if strategy not in weekly_data['strategies']:
                            weekly_data['strategies'][strategy] = {
                                'signals': 0,
                                'total_gain': 0.0
                            }
                        weekly_data['strategies'][strategy]['signals'] += metrics['signals']
                        weekly_data['strategies'][strategy]['total_gain'] += metrics['total_gain']
            except Exception as e:
                logger.error(f"Error processing daily summary {date_str}: {e}", exc_info=True)
                
        # Calculate derived metrics
        if weekly_data['trades']['total'] > 0:
            weekly_data['trades']['win_rate'] = (
                weekly_data['trades']['profitable'] / weekly_data['trades']['total']
            )
            weekly_data['trades']['net_pnl'] = (
                weekly_data['trades']['total_profit'] - weekly_data['trades']['total_loss']
            )
            
        if weekly_data['signals']['total'] > 0:
            weekly_data['signals']['execution_rate'] = (
                weekly_data['signals']['executed'] / weekly_data['signals']['total']
            )
            
        # Add success rates for strategies
        for strategy, data in weekly_data['strategies'].items():
            if data['signals'] > 0 and data['total_gain'] > 0:
                # Rough estimate of success rate
                data['estimated_success_rate'] = data['total_gain'] / (data['signals'] * 2)
                
        # Write weekly summary to file
        weekly_file = f"weekly_summary_{week_str}.json"
        try:
            with open(os.path.join(self.base_dir, weekly_file), 'w') as f:
                json.dump(weekly_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write weekly summary to {weekly_file}: {e}", exc_info=True)
            
        return weekly_data
    
    def get_trade_metrics(self) -> Dict:
        """Get current trade metrics"""
        return self._trade_metrics.copy()
    
    def get_signal_metrics(self) -> Dict:
        """Get current signal metrics"""
        return self._signal_metrics.copy()
    
    def get_strategy_metrics(self) -> Dict:
        """Get current strategy metrics"""
        return self._strategy_metrics.copy()
    
    def get_performance_metrics(self) -> Dict:
        """Get current performance metrics"""
        metrics = {}
        for category, data in self._performance_data.items():
            if not data:
                continue
                
            durations = [item['duration_ms'] for item in data]
            success_count = sum(1 for item in data if item['success'])
            success_rate = success_count / len(data) if data else 0
            
            metrics[category] = {
                'count': len(data),
                'avg_duration_ms': sum(durations) / len(durations) if durations else 0,
                'min_duration_ms': min(durations) if durations else 0,
                'max_duration_ms': max(durations) if durations else 0,
                'success_rate': success_rate
            }
        
        return metrics
    
    def measure_execution_time(self, category: str = 'other'):
        """
        Decorator to measure execution time of functions
        
        Args:
            category: Performance data category
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                success = True
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    raise e
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    self.log_performance(
                        operation=func.__name__,
                        duration_ms=duration_ms,
                        success=success,
                        metadata={'category': category}
                    )
            return wrapper
        return decorator

# Singleton instance
analytics_logger = AnalyticsLogger()
