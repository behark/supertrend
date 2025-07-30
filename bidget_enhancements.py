#!/usr/bin/env python
"""
Bidget Enhancements Integration Module
-------------------------------------
Integrates all Bidget enhancements into the main bot:
1. Auto-Fallback Mode for alternative <$1 pairs
2. Balance-Based Scaling for optimal position sizing
3. Signal Quality Control for filtering and optimizing signals
4. Live Signal Dashboard integration for real-time monitoring
"""
import os
import sys
import time
import logging
import threading
from datetime import datetime, timedelta

# Import enhancement modules
from auto_fallback import AutoFallback
from balance_scaling import BalanceScaling
from signal_quality import SignalQualityControl
from signal_dashboard import SignalDashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BidgetEnhancements:
    """Integration class for Bidget trading enhancements"""
    
    def __init__(self, config=None, data_dir='data'):
        """Initialize Bidget enhancements
        
        Args:
            config (dict): Configuration parameters
            data_dir (str): Directory for data files
        """
        self.config = config or {}
        self.data_dir = data_dir
        
        # Initialize enhancement modules
        logger.info("Initializing Bidget enhancements...")
        
        # Auto-Fallback
        self.fallback = AutoFallback(config=config, data_dir=data_dir)
        logger.info("Auto-Fallback mode initialized")
        
        # Balance Scaling
        self.balance_scaling = BalanceScaling(config=config, data_dir=data_dir)
        logger.info("Balance-Based Scaling initialized")
        
        # Signal Quality Control
        self.quality_control = SignalQualityControl(config=config, data_dir=data_dir)
        logger.info("Signal Quality Control initialized")
        
        # Signal Dashboard
        self.signal_dashboard = SignalDashboard(data_dir=data_dir)
        logger.info("Signal Dashboard initialized")
        
        # Initialize state
        self.current_balance = 0
        self.last_balance_update = datetime.now() - timedelta(hours=1)
        self.signals_processed_today = 0
        self.trades_executed_today = 0
        
        logger.info("Bidget enhancements ready")
    
    def get_config(self):
        """Get current configuration parameters
        
        Returns:
            dict: Current configuration with default values applied
        """
        # Create a copy to avoid modifying the original
        config = self.config.copy() if self.config else {}
        
        # Set defaults for any missing values
        defaults = {
            'preferred_symbols': ['XRPUSDT', 'ADAUSDT', 'DOGEUSDT', 'TRXUSDT', 'XLMUSDT'],
            'max_price': 1.0,
            'balance_percentage': 30.0,
            'leverage': 20,
            'min_probability': 90.0,
            'debug_mode': False,
            'hot_reload': True
        }
        
        # Apply defaults if values missing
        for key, value in defaults.items():
            if key not in config:
                config[key] = value
                
        return config
    
    def get_high_confidence_count(self):
        """Get count of high confidence signals
        
        Returns:
            int: Count of high confidence signals
        """
        if hasattr(self.signal_dashboard, 'get_high_confidence_count'):
            return self.signal_dashboard.get_high_confidence_count()
        return 0
    
    def get_elite_confidence_count(self):
        """Get count of elite confidence signals
        
        Returns:
            int: Count of elite confidence signals
        """
        if hasattr(self.signal_dashboard, 'get_elite_confidence_count'):
            return self.signal_dashboard.get_elite_confidence_count()
        return 0
    
    def get_pending_signals_count(self):
        """Get count of pending signals
        
        Returns:
            int: Count of pending signals
        """
        if hasattr(self.quality_control, 'get_pending_signals_count'):
            return self.quality_control.get_pending_signals_count()
        return 0
        
    def reset_daily_stats(self):
        """Reset daily statistics
        """
        self.signals_processed_today = 0
        self.trades_executed_today = 0
        
        # Reset stats in modules
        if hasattr(self.signal_dashboard, 'reset_daily_stats'):
            self.signal_dashboard.reset_daily_stats()
        
        if hasattr(self.quality_control, 'reset_daily_stats'):
            self.quality_control.reset_daily_stats()
            
        if hasattr(self.fallback, 'reset_daily_stats'):
            self.fallback.reset_daily_stats()
    
    def update_exchange_balance(self, exchange, balance):
        """Update current exchange balance
        
        Args:
            exchange (str): Exchange name
            balance (float): Current balance
            
        Returns:
            float: Scaling multiplier for position sizing
        """
        try:
            logger.info(f"Updating {exchange} balance to {balance} USDT")
            self.current_balance = balance
            self.last_balance_update = datetime.now()
            
            # Update balance scaling
            multiplier = self.balance_scaling.update_balance(balance)
            
            return multiplier
        
        except Exception as e:
            logger.error(f"Error updating exchange balance: {str(e)}")
            return 1.0
    
    def process_signal(self, signal, execute_callback=None):
        """Process a trading signal through all enhancement filters
        
        Args:
            signal (dict): Trading signal
            execute_callback (callable): Callback to execute trade
            
        Returns:
            dict: Processed signal with enhancement data or None if rejected
        """
        try:
            logger.info(f"Processing signal for {signal['symbol']} with probability {signal['probability']:.2f}")
            
            # Ensure signal has required fields
            required_fields = ['symbol', 'timeframe', 'probability', 'entry_price']
            if not all(field in signal for field in required_fields):
                logger.warning(f"Signal missing required fields: {[f for f in required_fields if f not in signal]}")
                return None
            
            # Add to signal dashboard
            self.signal_dashboard.add_signal(signal)
            
            # Use callback for delayed signals
            def execute_signal_callback(processed_signal):
                if execute_callback:
                    # Calculate position size with balance scaling
                    if 'stop_loss' in processed_signal:
                        position_quote, position_base, risk_pct = self.balance_scaling.calculate_position_size(
                            processed_signal['symbol'], 
                            processed_signal['entry_price'],
                            processed_signal['stop_loss'],
                            self.current_balance
                        )
                    else:
                        position_quote, position_base, risk_pct = self.balance_scaling.calculate_position_size(
                            processed_signal['symbol'],
                            processed_signal['entry_price'],
                            None,
                            self.current_balance
                        )
                    
                    # Add position size to signal
                    processed_signal['position_size_quote'] = position_quote
                    processed_signal['position_size_base'] = position_base
                    processed_signal['risk_percentage'] = risk_pct
                    
                    # Execute trade
                    execute_callback(processed_signal)
            
            # Process through signal quality control
            process_now, signal_id = self.quality_control.process_signal(signal, execute_signal_callback)
            
            # Add signal ID to original signal
            signal['id'] = signal_id
            
            # If signal should be processed now
            if process_now:
                # Calculate position size with balance scaling
                if 'stop_loss' in signal:
                    position_quote, position_base, risk_pct = self.balance_scaling.calculate_position_size(
                        signal['symbol'], 
                        signal['entry_price'],
                        signal['stop_loss'],
                        self.current_balance
                    )
                else:
                    position_quote, position_base, risk_pct = self.balance_scaling.calculate_position_size(
                        signal['symbol'],
                        signal['entry_price'],
                        None,
                        self.current_balance
                    )
                
                # Add position size to signal
                signal['position_size_quote'] = position_quote
                signal['position_size_base'] = position_base
                signal['risk_percentage'] = risk_pct
                
                # Return enhanced signal
                return signal
            
            # Signal will be processed later or rejected
            return None
            
        except Exception as e:
            logger.error(f"Error processing signal: {str(e)}")
            return None
    
    def check_for_fallback(self, signals):
        """Check for fallback signals when preferred symbols have no signals
        
        Args:
            signals (list): List of all available signals
            
        Returns:
            dict: Fallback signal or None
        """
        try:
            logger.info(f"Checking for fallback signals among {len(signals)} available signals")
            
            # Get fallback signal
            fallback_signal = self.fallback.get_fallback_signal(signals)
            
            if fallback_signal:
                logger.info(f"Found fallback signal for {fallback_signal['symbol']} with {fallback_signal['probability']:.2f} probability")
            else:
                logger.info("No suitable fallback signals found")
            
            return fallback_signal
            
        except Exception as e:
            logger.error(f"Error checking for fallback signals: {str(e)}")
            return None
    
    def update_trade_result(self, trade_id, symbol, profit, success=None):
        """Update trade result in all enhancement modules
        
        Args:
            trade_id (str): Trade ID
            symbol (str): Trading pair symbol
            profit (float): Profit amount
            success (bool): Whether the trade was successful (if None, determined by profit)
        """
        try:
            # Determine success if not provided
            if success is None:
                success = profit > 0
            
            logger.info(f"Updating trade result for {trade_id}: {'success' if success else 'failure'} with {profit} profit")
            
            # Update balance scaling
            self.balance_scaling.update_trade_result(trade_id, profit, success)
            
            # Update signal quality control
            self.quality_control.update_signal_result(trade_id, success)
            
            # Update signal dashboard
            self.signal_dashboard.update_signal_result(trade_id, success)
            
            # Update auto fallback performance if needed
            if ':' in symbol:  # Linear symbol format for fallback pairs
                self.fallback.update_pair_performance(symbol, success)
            
        except Exception as e:
            logger.error(f"Error updating trade result: {str(e)}")
    
    def get_recommended_parameters(self):
        """Get recommended trading parameters based on current performance
        
        Returns:
            dict: Recommended parameters
        """
        try:
            # Get recommendations from balance scaling
            recommendations = self.balance_scaling.get_recommended_parameters()
            
            # Add signal quality metrics
            signal_metrics = self.quality_control.get_signal_metrics()
            if signal_metrics:
                recommendations['signal_quality'] = {
                    'win_rate': signal_metrics['overall'].get('win_rate', 0),
                    'total_signals': signal_metrics['overall'].get('total_signals', 0),
                    'high_quality': signal_metrics['overall'].get('high_quality', 0),
                    'elite': signal_metrics['overall'].get('elite', 0),
                }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommended parameters: {str(e)}")
            return {}
    
    def get_best_pending_signals(self, top_n=5):
        """Get best pending signals
        
        Args:
            top_n (int): Number of signals to return
            
        Returns:
            list: Best pending signals
        """
        try:
            return self.quality_control.get_best_signals(top_n)
        except Exception as e:
            logger.error(f"Error getting best pending signals: {str(e)}")
            return []
    
    def get_dashboard_metrics(self):
        """Get dashboard metrics for UI
        
        Returns:
            dict: Dashboard metrics
        """
        try:
            metrics = {}
            
            # Signal dashboard metrics
            try:
                dashboard_stats = self.signal_dashboard.get_dashboard_stats()
                if dashboard_stats:
                    metrics['signal_dashboard'] = dashboard_stats
            except:
                pass
            
            # Balance scaling metrics
            try:
                recommendations = self.balance_scaling.get_recommended_parameters()
                if 'metrics' in recommendations:
                    metrics['balance_scaling'] = recommendations['metrics']
            except:
                pass
            
            # Signal quality metrics
            try:
                signal_metrics = self.quality_control.get_signal_metrics()
                if signal_metrics:
                    metrics['signal_quality'] = {
                        'overall': signal_metrics['overall'],
                        'pending_signals': self.quality_control.get_delayed_signals_count()
                    }
            except:
                pass
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting dashboard metrics: {str(e)}")
            return {}
    
    def update_fallback_whitelist(self, exchange_id='bybit'):
        """Update fallback whitelist pairs
        
        Args:
            exchange_id (str): Exchange ID
            
        Returns:
            list: Updated whitelist
        """
        try:
            return self.fallback.update_fallback_whitelist(exchange_id)
        except Exception as e:
            logger.error(f"Error updating fallback whitelist: {str(e)}")
            return []
    
    def get_fallback_whitelist(self):
        """Get current fallback whitelist
        
        Returns:
            list: Current whitelist
        """
        try:
            return self.fallback.fallback_pairs.get('whitelist', [])
        except Exception as e:
            logger.error(f"Error getting fallback whitelist: {str(e)}")
            return []

# Example usage
if __name__ == "__main__":
    # Initialize enhancements
    config = {
        'preferred_symbols': ["XRP/USDT", "ADA/USDT", "DOGE/USDT", "TRX/USDT", "XLM/USDT"],
        'max_price': 1.0,
        'balance_percentage': 0.3,
        'leverage': 20,
        'min_probability': 0.9,
        'high_quality_threshold': 0.95,
        'elite_threshold': 0.98,
        'delay_threshold': 0.92
    }
    
    enhancements = BidgetEnhancements(config=config)
    
    # Update exchange balance
    enhancements.update_exchange_balance('bybit', 100.0)
    
    # Example signal processing
    signal = {
        'symbol': 'ADA/USDT',
        'timeframe': '1h',
        'probability': 0.96,
        'entry_price': 0.5,
        'stop_loss': 0.45,
        'take_profit': 0.6
    }
    
    # Process signal
    enhanced_signal = enhancements.process_signal(signal)
    if enhanced_signal:
        print(f"Enhanced signal: {enhanced_signal}")
    
    # Update trade result
    enhancements.update_trade_result('test_trade', 'ADA/USDT', 5, True)
    
    # Get recommendations
    recommendations = enhancements.get_recommended_parameters()
    print(f"Recommendations: {recommendations}")
    
    # Get dashboard metrics
    metrics = enhancements.get_dashboard_metrics()
    print(f"Dashboard metrics: {metrics}")
    
    # Update fallback whitelist
    whitelist = enhancements.update_fallback_whitelist()
    print(f"Fallback whitelist: {whitelist}")
