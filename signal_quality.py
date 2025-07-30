#!/usr/bin/env python
"""
Signal Quality Control
---------------------
Optimizes signal delivery and trade execution:
1. Delays signals with <92% confidence to check for higher quality alternatives
2. Maintains a buffer of pending signals to find optimal execution timing
3. Tracks signal quality metrics by pair, timeframe and other factors
4. Adapts thresholds based on historical performance
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SignalQualityControl:
    """Signal quality control and optimization system"""
    
    def __init__(self, config=None, data_dir='data'):
        """Initialize signal quality control
        
        Args:
            config (dict): Configuration parameters
            data_dir (str): Directory for signal data
        """
        self.config = config or {}
        self.data_dir = data_dir
        self.signal_file = os.path.join(data_dir, 'signal_quality.json')
        
        # Default configuration
        self.config.setdefault('min_probability', 0.9)  # Minimum probability for any signal
        self.config.setdefault('high_quality_threshold', 0.95)  # High quality signals
        self.config.setdefault('elite_threshold', 0.98)  # Elite signals
        self.config.setdefault('delay_threshold', 0.92)  # Delay signals below this threshold
        self.config.setdefault('delay_duration', 300)  # 5 minutes delay for borderline signals
        self.config.setdefault('max_pending_signals', 10)  # Maximum pending signals per pair
        
        # Signal quality data
        self.signal_data = {
            'last_update': datetime.now().isoformat(),
            'metrics': {
                'pairs': {},
                'timeframes': {},
                'overall': {
                    'total_signals': 0,
                    'high_quality': 0,
                    'elite': 0,
                    'successful': 0,
                    'failed': 0,
                    'win_rate': 0
                }
            },
            'threshold_adjustments': [],
            'current_thresholds': {
                'min_probability': self.config['min_probability'],
                'high_quality': self.config['high_quality_threshold'],
                'elite': self.config['elite_threshold'],
                'delay': self.config['delay_threshold']
            }
        }
        
        # Pending signals queue
        self.pending_signals = defaultdict(list)  # symbol -> list of signals
        self.signal_queue = queue.PriorityQueue()  # Priority queue for delayed signals
        self.processing_thread = None
        self.stop_event = threading.Event()
        
        # Load existing data if available
        self._load_signal_data()
        
        # Start signal processing thread
        self._start_processing_thread()
    
    def _load_signal_data(self):
        """Load signal data from disk"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Load signal data
            if os.path.exists(self.signal_file):
                with open(self.signal_file, 'r') as f:
                    self.signal_data = json.load(f)
                logger.info(f"Loaded signal data from {self.signal_file}")
                
                # Update current thresholds from loaded data
                if 'current_thresholds' in self.signal_data:
                    for key, value in self.signal_data['current_thresholds'].items():
                        if key in self.config:
                            self.config[key] = value
                
        except Exception as e:
            logger.error(f"Error loading signal data: {str(e)}")
    
    def _save_signal_data(self):
        """Save signal data to disk"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Update timestamp and current thresholds
            self.signal_data['last_update'] = datetime.now().isoformat()
            self.signal_data['current_thresholds'] = {
                'min_probability': self.config['min_probability'],
                'high_quality': self.config['high_quality_threshold'],
                'elite': self.config['elite_threshold'],
                'delay': self.config['delay_threshold']
            }
            
            # Save signal data
            with open(self.signal_file, 'w') as f:
                json.dump(self.signal_data, f, indent=2)
            
            logger.info(f"Saved signal data to {self.signal_file}")
                
        except Exception as e:
            logger.error(f"Error saving signal data: {str(e)}")
    
    def _start_processing_thread(self):
        """Start the signal processing thread"""
        if self.processing_thread is None or not self.processing_thread.is_alive():
            self.stop_event.clear()
            self.processing_thread = threading.Thread(target=self._process_pending_signals)
            self.processing_thread.daemon = True
            self.processing_thread.start()
            logger.info("Started signal processing thread")
    
    def stop_processing(self):
        """Stop the signal processing thread"""
        if self.processing_thread and self.processing_thread.is_alive():
            self.stop_event.set()
            self.processing_thread.join(timeout=2.0)
            logger.info("Stopped signal processing thread")
    
    def _process_pending_signals(self):
        """Process pending signals in background thread"""
        while not self.stop_event.is_set():
            try:
                # Check for due signals
                if not self.signal_queue.empty():
                    # Get next signal if it's due
                    due_time, _, signal = self.signal_queue.queue[0]
                    
                    if datetime.now() >= due_time:
                        # Remove from queue
                        self.signal_queue.get_nowait()
                        
                        # Process signal
                        symbol = signal['symbol']
                        
                        # Check if we should still process this signal
                        if self._should_process_delayed_signal(symbol, signal):
                            # Call the callback
                            if signal.get('callback'):
                                try:
                                    signal['callback'](signal)
                                except Exception as e:
                                    logger.error(f"Error in signal callback: {str(e)}")
                
                # Sleep to avoid busy waiting
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error processing pending signals: {str(e)}")
                time.sleep(5.0)  # Back off on error
    
    def _should_process_delayed_signal(self, symbol, signal):
        """Determine if a delayed signal should still be processed
        
        Args:
            symbol (str): Symbol of the signal
            signal (dict): Signal data
            
        Returns:
            bool: Whether to process the signal
        """
        try:
            # Get current pending signals for this symbol
            pending = self.pending_signals.get(symbol, [])
            
            # If no other signals for this symbol, process it
            if not pending:
                return True
            
            # Find best signal for this symbol
            best_signal = max(pending, key=lambda s: s['probability'])
            
            # If this signal is the best, process it
            if signal['id'] == best_signal['id']:
                return True
            
            # If there's a much better signal (>3% higher probability), skip this one
            if best_signal['probability'] - signal['probability'] > 0.03:
                logger.info(f"Skipping {symbol} signal with {signal['probability']:.2f} probability in favor of better signal with {best_signal['probability']:.2f}")
                return False
            
            # Otherwise process it
            return True
            
        except Exception as e:
            logger.error(f"Error determining whether to process delayed signal: {str(e)}")
            return True  # Process on error to be safe
    
    def process_signal(self, signal, callback=None):
        """Process a new trading signal
        
        Args:
            signal (dict): Trading signal
            callback (callable): Callback function to call when signal is ready
            
        Returns:
            tuple: (process_now, signal_id) - whether to process immediately and signal ID
        """
        try:
            # Generate signal ID if not present
            if 'id' not in signal:
                signal['id'] = f"{signal['symbol']}_{int(time.time())}_{signal['probability']:.4f}"
            
            # Get symbol and probability
            symbol = signal['symbol']
            probability = signal['probability']
            
            # Add callback
            if callback:
                signal['callback'] = callback
            
            # Check if signal meets minimum probability
            if probability < self.config['min_probability']:
                logger.info(f"Rejecting {symbol} signal with {probability:.2f} probability (below minimum {self.config['min_probability']:.2f})")
                return False, signal['id']
            
            # Update metrics
            self._update_signal_metrics(signal)
            
            # Add to pending signals
            self.pending_signals[symbol].append(signal)
            
            # Trim pending signals if too many
            if len(self.pending_signals[symbol]) > self.config['max_pending_signals']:
                # Sort by probability (highest first)
                self.pending_signals[symbol].sort(key=lambda s: s['probability'], reverse=True)
                
                # Keep only the best signals
                self.pending_signals[symbol] = self.pending_signals[symbol][:self.config['max_pending_signals']]
            
            # Check if we should delay this signal
            if probability < self.config['delay_threshold']:
                # Calculate due time
                due_time = datetime.now() + timedelta(seconds=self.config['delay_duration'])
                
                # Add to queue with priority based on due time and probability
                priority = (due_time, -probability)  # Negative probability to prioritize higher probabilities
                self.signal_queue.put((due_time, priority, signal))
                
                logger.info(f"Delaying {symbol} signal with {probability:.2f} probability for {self.config['delay_duration']} seconds")
                return False, signal['id']
            
            # Process immediately
            logger.info(f"Processing {symbol} signal with {probability:.2f} probability immediately")
            return True, signal['id']
            
        except Exception as e:
            logger.error(f"Error processing signal: {str(e)}")
            return False, None
    
    def _update_signal_metrics(self, signal):
        """Update signal quality metrics
        
        Args:
            signal (dict): Trading signal
        """
        try:
            # Get symbol and timeframe
            symbol = signal['symbol']
            timeframe = signal.get('timeframe', 'unknown')
            probability = signal['probability']
            
            # Initialize pair metrics if needed
            if symbol not in self.signal_data['metrics']['pairs']:
                self.signal_data['metrics']['pairs'][symbol] = {
                    'total_signals': 0,
                    'high_quality': 0,
                    'elite': 0,
                    'successful': 0,
                    'failed': 0,
                    'win_rate': 0
                }
            
            # Initialize timeframe metrics if needed
            if timeframe not in self.signal_data['metrics']['timeframes']:
                self.signal_data['metrics']['timeframes'][timeframe] = {
                    'total_signals': 0,
                    'high_quality': 0,
                    'elite': 0,
                    'successful': 0,
                    'failed': 0,
                    'win_rate': 0
                }
            
            # Update total signals count
            self.signal_data['metrics']['overall']['total_signals'] += 1
            self.signal_data['metrics']['pairs'][symbol]['total_signals'] += 1
            self.signal_data['metrics']['timeframes'][timeframe]['total_signals'] += 1
            
            # Update quality metrics
            if probability >= self.config['elite_threshold']:
                self.signal_data['metrics']['overall']['elite'] += 1
                self.signal_data['metrics']['pairs'][symbol]['elite'] += 1
                self.signal_data['metrics']['timeframes'][timeframe]['elite'] += 1
            
            elif probability >= self.config['high_quality_threshold']:
                self.signal_data['metrics']['overall']['high_quality'] += 1
                self.signal_data['metrics']['pairs'][symbol]['high_quality'] += 1
                self.signal_data['metrics']['timeframes'][timeframe]['high_quality'] += 1
            
            # Save metrics
            self._save_signal_data()
            
        except Exception as e:
            logger.error(f"Error updating signal metrics: {str(e)}")
    
    def update_signal_result(self, signal_id, success):
        """Update the result of a processed signal
        
        Args:
            signal_id (str): Signal ID
            success (bool): Whether the trade was successful
        """
        try:
            # Find signal in pending signals
            found = False
            symbol = None
            timeframe = None
            
            for sym, signals in self.pending_signals.items():
                for i, signal in enumerate(signals):
                    if signal['id'] == signal_id:
                        found = True
                        symbol = sym
                        timeframe = signal.get('timeframe', 'unknown')
                        
                        # Remove from pending signals
                        self.pending_signals[sym].pop(i)
                        break
                
                if found:
                    break
            
            if not found:
                logger.warning(f"Signal {signal_id} not found in pending signals")
                # Try to extract symbol from signal_id
                if '_' in signal_id:
                    symbol = signal_id.split('_')[0]
                    timeframe = 'unknown'
            
            if symbol:
                # Update success/failure counts
                if success:
                    self.signal_data['metrics']['overall']['successful'] += 1
                    
                    if symbol in self.signal_data['metrics']['pairs']:
                        self.signal_data['metrics']['pairs'][symbol]['successful'] += 1
                    
                    if timeframe in self.signal_data['metrics']['timeframes']:
                        self.signal_data['metrics']['timeframes'][timeframe]['successful'] += 1
                else:
                    self.signal_data['metrics']['overall']['failed'] += 1
                    
                    if symbol in self.signal_data['metrics']['pairs']:
                        self.signal_data['metrics']['pairs'][symbol]['failed'] += 1
                    
                    if timeframe in self.signal_data['metrics']['timeframes']:
                        self.signal_data['metrics']['timeframes'][timeframe]['failed'] += 1
                
                # Update win rates
                self._update_win_rates()
                
                # Adapt thresholds based on performance
                self._adapt_thresholds()
                
                # Save data
                self._save_signal_data()
                
                logger.info(f"Updated signal {signal_id} result: {'success' if success else 'failure'}")
            
        except Exception as e:
            logger.error(f"Error updating signal result: {str(e)}")
    
    def _update_win_rates(self):
        """Update win rates for all metrics"""
        try:
            # Update overall win rate
            total = self.signal_data['metrics']['overall']['successful'] + self.signal_data['metrics']['overall']['failed']
            if total > 0:
                self.signal_data['metrics']['overall']['win_rate'] = self.signal_data['metrics']['overall']['successful'] / total
            
            # Update pair win rates
            for symbol, metrics in self.signal_data['metrics']['pairs'].items():
                total = metrics['successful'] + metrics['failed']
                if total > 0:
                    metrics['win_rate'] = metrics['successful'] / total
            
            # Update timeframe win rates
            for timeframe, metrics in self.signal_data['metrics']['timeframes'].items():
                total = metrics['successful'] + metrics['failed']
                if total > 0:
                    metrics['win_rate'] = metrics['successful'] / total
            
        except Exception as e:
            logger.error(f"Error updating win rates: {str(e)}")
    
    def _adapt_thresholds(self):
        """Adapt thresholds based on performance"""
        try:
            # Skip if not enough data
            total_signals = self.signal_data['metrics']['overall']['total_signals']
            if total_signals < 20:
                return
            
            # Get overall win rate
            win_rate = self.signal_data['metrics']['overall']['win_rate']
            
            # Adjust thresholds based on win rate
            if win_rate < 0.7 and total_signals >= 50:
                # Poor performance, increase thresholds
                self.config['min_probability'] = min(self.config['min_probability'] + 0.01, 0.95)
                self.config['delay_threshold'] = min(self.config['delay_threshold'] + 0.01, 0.96)
                
                # Record adjustment
                self.signal_data['threshold_adjustments'].append({
                    'timestamp': datetime.now().isoformat(),
                    'reason': 'poor_performance',
                    'win_rate': win_rate,
                    'min_probability': self.config['min_probability'],
                    'delay_threshold': self.config['delay_threshold']
                })
                
                logger.info(f"Increased thresholds due to poor performance (win rate: {win_rate:.2f})")
                
            elif win_rate > 0.9 and total_signals >= 100:
                # Excellent performance, could slightly decrease thresholds
                self.config['min_probability'] = max(self.config['min_probability'] - 0.005, 0.88)
                
                # Record adjustment
                self.signal_data['threshold_adjustments'].append({
                    'timestamp': datetime.now().isoformat(),
                    'reason': 'excellent_performance',
                    'win_rate': win_rate,
                    'min_probability': self.config['min_probability'],
                    'delay_threshold': self.config['delay_threshold']
                })
                
                logger.info(f"Decreased thresholds due to excellent performance (win rate: {win_rate:.2f})")
                
            # Trim adjustment history if too long
            if len(self.signal_data['threshold_adjustments']) > 100:
                self.signal_data['threshold_adjustments'] = self.signal_data['threshold_adjustments'][-100:]
            
        except Exception as e:
            logger.error(f"Error adapting thresholds: {str(e)}")
    
    def get_signal_metrics(self):
        """Get signal quality metrics
        
        Returns:
            dict: Signal quality metrics
        """
        return self.signal_data['metrics']
    
    def get_pending_signals(self):
        """Get all pending signals
        
        Returns:
            dict: Pending signals by symbol
        """
        return {k: v for k, v in self.pending_signals.items()}
    
    def get_delayed_signals_count(self):
        """Get count of delayed signals
        
        Returns:
            int: Number of delayed signals
        """
        return self.signal_queue.qsize()
    
    def get_best_signals(self, top_n=5):
        """Get best pending signals
        
        Args:
            top_n (int): Number of signals to return
            
        Returns:
            list: Best pending signals
        """
        try:
            # Collect all signals
            all_signals = []
            for symbol, signals in self.pending_signals.items():
                all_signals.extend(signals)
            
            # Sort by probability (highest first)
            all_signals.sort(key=lambda s: s['probability'], reverse=True)
            
            # Return top signals
            return all_signals[:top_n]
            
        except Exception as e:
            logger.error(f"Error getting best signals: {str(e)}")
            return []

# Example usage
if __name__ == "__main__":
    # Initialize signal quality control
    quality_control = SignalQualityControl()
    
    # Example callback
    def signal_callback(signal):
        print(f"Processing signal: {signal['symbol']} with {signal['probability']:.2f} probability")
    
    # Example signals
    signals = [
        {
            'symbol': 'ADA/USDT',
            'timeframe': '1h',
            'probability': 0.96,
            'entry_price': 0.5
        },
        {
            'symbol': 'ADA/USDT',
            'timeframe': '15m',
            'probability': 0.91,
            'entry_price': 0.51
        },
        {
            'symbol': 'XRP/USDT',
            'timeframe': '4h',
            'probability': 0.98,
            'entry_price': 0.6
        }
    ]
    
    # Process signals
    for signal in signals:
        process_now, signal_id = quality_control.process_signal(signal, signal_callback)
        print(f"Signal {signal_id} for {signal['symbol']}: {'process now' if process_now else 'delayed'}")
    
    print("\nPending signals:")
    pending = quality_control.get_pending_signals()
    for symbol, signals in pending.items():
        print(f"{symbol}: {len(signals)} signals")
    
    print("\nDelayed signals count:", quality_control.get_delayed_signals_count())
    
    print("\nBest signals:")
    best_signals = quality_control.get_best_signals(2)
    for signal in best_signals:
        print(f"{signal['symbol']} ({signal['timeframe']}): {signal['probability']:.2f}")
    
    print("\nSimulating trade results")
    quality_control.update_signal_result(best_signals[0]['id'], True)
    
    print("\nSignal metrics:")
    metrics = quality_control.get_signal_metrics()
    print(f"Overall: {metrics['overall']['total_signals']} signals, {metrics['overall']['win_rate']:.2f} win rate")
    
    # Stop processing thread
    quality_control.stop_processing()
