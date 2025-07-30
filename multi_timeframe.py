"""
Multi-Timeframe Analysis Module for Cryptocurrency Trading
Analyzes signals across multiple timeframes to confirm trade entries
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime

from indicators import (
    check_volume_price_spike,
    check_ma_cross,
    check_breakout,
    calculate_rsi
)

logger = logging.getLogger(__name__)

class MultiTimeframeAnalyzer:
    """Analyzes trading signals across multiple timeframes"""
    
    def __init__(self, config=None):
        """Initialize the multi-timeframe analyzer.
        
        Args:
            config (dict): Configuration parameters
        """
        self.config = config or {}
        
        # Default configuration
        self.config.setdefault('timeframes', ['5m', '15m', '1h', '4h', '1d'])
        self.config.setdefault('primary_timeframe', '1h')
        self.config.setdefault('confirmation_timeframes', ['4h', '1d'])
        self.config.setdefault('min_confirmations', 2)
        
        logger.info("Multi-Timeframe Analyzer initialized")
    
    def analyze_trend_alignment(self, timeframe_data):
        """Analyze if trends are aligned across timeframes.
        
        Args:
            timeframe_data (dict): Dictionary of timeframe -> OHLCV dataframe
            
        Returns:
            dict: Trend alignment analysis
        """
        # Get available timeframes
        available_timeframes = list(timeframe_data.keys())
        
        # Initialize result
        result = {
            'trend_aligned': False,
            'alignment_score': 0,
            'aligned_timeframes': [],
            'bullish_timeframes': [],
            'bearish_timeframes': [],
            'price_action': {},
            'ma_analysis': {}
        }
        
        # Price action analysis for each timeframe
        for tf in available_timeframes:
            df = timeframe_data[tf]
            if len(df) < 10:
                continue
                
            # Check higher highs and higher lows for bullish trend
            price_action_bullish = (
                df['high'].iloc[-1] > df['high'].iloc[-2] and
                df['low'].iloc[-1] > df['low'].iloc[-2]
            )
            
            # Check moving averages
            ma_20 = df['close'].rolling(20).mean()
            ma_50 = df['close'].rolling(50).mean()
            ma_200 = df['close'].rolling(200).mean() if len(df) >= 200 else None
            
            current_price = df['close'].iloc[-1]
            
            # Check price above key moving averages
            above_ma20 = current_price > ma_20.iloc[-1]
            above_ma50 = current_price > ma_50.iloc[-1]
            above_ma200 = current_price > ma_200.iloc[-1] if ma_200 is not None else None
            
            # MA alignment (20 > 50 > 200) for bullish trend
            ma_aligned_bullish = (
                above_ma20 and above_ma50 and
                ma_20.iloc[-1] > ma_50.iloc[-1] and
                (ma_50.iloc[-1] > ma_200.iloc[-1] if ma_200 is not None else True)
            )
            
            # Store price action and MA analysis
            result['price_action'][tf] = {
                'bullish': price_action_bullish,
                'last_candle': {
                    'open': df['open'].iloc[-1],
                    'high': df['high'].iloc[-1],
                    'low': df['low'].iloc[-1],
                    'close': df['close'].iloc[-1],
                    'volume': df['volume'].iloc[-1]
                }
            }
            
            result['ma_analysis'][tf] = {
                'above_ma20': above_ma20,
                'above_ma50': above_ma50,
                'above_ma200': above_ma200,
                'ma_aligned_bullish': ma_aligned_bullish
            }
            
            # Determine if timeframe is bullish
            timeframe_bullish = price_action_bullish and ma_aligned_bullish
            
            if timeframe_bullish:
                result['bullish_timeframes'].append(tf)
            else:
                result['bearish_timeframes'].append(tf)
        
        # Count aligned bullish timeframes
        aligned_count = len(result['bullish_timeframes'])
        total_timeframes = len(available_timeframes)
        
        # Calculate alignment score
        alignment_score = aligned_count / total_timeframes if total_timeframes > 0 else 0
        result['alignment_score'] = alignment_score
        
        # Check if primary and confirmation timeframes are aligned
        primary_aligned = self.config['primary_timeframe'] in result['bullish_timeframes']
        confirmation_aligned = sum(1 for tf in self.config['confirmation_timeframes'] 
                                  if tf in result['bullish_timeframes'])
        
        # Trend is aligned if primary and enough confirmation timeframes are bullish
        result['trend_aligned'] = (
            primary_aligned and 
            confirmation_aligned >= self.config['min_confirmations']
        )
        
        result['aligned_timeframes'] = result['bullish_timeframes']
        
        return result
    
    def confirm_signal(self, signal, timeframe_data):
        """Confirm a trading signal using multiple timeframes.
        
        Args:
            signal (dict): Trading signal
            timeframe_data (dict): Dictionary of timeframe -> OHLCV dataframe
            
        Returns:
            dict: Enhanced signal with multi-timeframe confirmation
        """
        # Analyze trend alignment
        alignment = self.analyze_trend_alignment(timeframe_data)
        
        # Enhanced signal with multi-timeframe analysis
        enhanced_signal = signal.copy()
        enhanced_signal['multi_timeframe'] = {
            'trend_aligned': alignment['trend_aligned'],
            'alignment_score': alignment['alignment_score'],
            'aligned_timeframes': alignment['aligned_timeframes'],
            'bullish_timeframes': alignment['bullish_timeframes'],
            'bearish_timeframes': alignment['bearish_timeframes']
        }
        
        # Check if signal is confirmed
        signal_confirmed = alignment['trend_aligned']
        
        # If signal is from a specific strategy, check for confirmation in that strategy
        strategy = signal.get('strategy')
        if strategy:
            strategy_confirmations = self._check_strategy_confirmations(strategy, timeframe_data)
            enhanced_signal['multi_timeframe']['strategy_confirmations'] = strategy_confirmations
            
            # Signal is confirmed if trend is aligned and strategy confirmations are sufficient
            min_strategy_confirmations = self.config.get('min_strategy_confirmations', 1)
            strategy_confirmed = len(strategy_confirmations) >= min_strategy_confirmations
            
            signal_confirmed = signal_confirmed and strategy_confirmed
        
        enhanced_signal['confirmed'] = signal_confirmed
        enhanced_signal['confidence'] = self._calculate_confidence(enhanced_signal)
        
        return enhanced_signal
    
    def _check_strategy_confirmations(self, strategy, timeframe_data):
        """Check for strategy-specific confirmations across timeframes.
        
        Args:
            strategy (str): Strategy name
            timeframe_data (dict): Dictionary of timeframe -> OHLCV dataframe
            
        Returns:
            list: Timeframes that confirm the strategy
        """
        confirmations = []
        
        for tf, df in timeframe_data.items():
            if len(df) < 50:  # Skip timeframes with insufficient data
                continue
            
            if strategy == 'volume_spike':
                # Check for volume spike in this timeframe
                if check_volume_price_spike(
                    df,
                    volume_threshold=2.0,
                    price_change_threshold=1.0
                ):
                    confirmations.append(tf)
            
            elif strategy == 'ma_cross':
                # Check for MA cross in this timeframe
                if check_ma_cross(
                    df,
                    fast_ma=9,
                    slow_ma=21
                ):
                    confirmations.append(tf)
            
            elif strategy == 'breakout':
                # Check for breakout in this timeframe
                if check_breakout(
                    df,
                    periods=20
                ):
                    confirmations.append(tf)
        
        return confirmations
    
    def _calculate_confidence(self, enhanced_signal):
        """Calculate confidence score for a signal based on multi-timeframe analysis.
        
        Args:
            enhanced_signal (dict): Enhanced signal with multi-timeframe data
            
        Returns:
            float: Confidence score (0-1)
        """
        # Start with base confidence
        confidence = 0.5
        
        multi_tf = enhanced_signal.get('multi_timeframe', {})
        
        # Add confidence based on trend alignment
        if multi_tf.get('trend_aligned', False):
            confidence += 0.2
        
        # Add confidence based on alignment score
        alignment_score = multi_tf.get('alignment_score', 0)
        confidence += alignment_score * 0.2
        
        # Add confidence based on strategy confirmations
        strategy_confirmations = multi_tf.get('strategy_confirmations', [])
        if strategy_confirmations:
            confirmation_ratio = len(strategy_confirmations) / len(self.config['timeframes'])
            confidence += confirmation_ratio * 0.1
        
        # Cap confidence at 1.0
        return min(confidence, 1.0)
    
    def analyze_timeframes(self, data_dict, strategy=None):
        """Analyze multiple timeframes for trading opportunities.
        
        Args:
            data_dict (dict): Dictionary of timeframe -> OHLCV dataframe
            strategy (str): Optional strategy to filter signals
            
        Returns:
            list: List of confirmed signals
        """
        signals = []
        
        # First, check primary timeframe for signals
        primary_tf = self.config['primary_timeframe']
        if primary_tf not in data_dict:
            logger.warning(f"Primary timeframe {primary_tf} not in data")
            return []
        
        primary_df = data_dict[primary_tf]
        
        # Check for volume + price spike signals
        if not strategy or strategy == 'volume_spike':
            if check_volume_price_spike(primary_df):
                signal = {
                    'timestamp': datetime.now(),
                    'strategy': 'volume_spike',
                    'timeframe': primary_tf,
                    'price': primary_df['close'].iloc[-1]
                }
                
                # Confirm with other timeframes
                confirmed_signal = self.confirm_signal(signal, data_dict)
                if confirmed_signal['confirmed']:
                    signals.append(confirmed_signal)
        
        # Check for MA cross signals
        if not strategy or strategy == 'ma_cross':
            if check_ma_cross(primary_df):
                signal = {
                    'timestamp': datetime.now(),
                    'strategy': 'ma_cross',
                    'timeframe': primary_tf,
                    'price': primary_df['close'].iloc[-1]
                }
                
                # Confirm with other timeframes
                confirmed_signal = self.confirm_signal(signal, data_dict)
                if confirmed_signal['confirmed']:
                    signals.append(confirmed_signal)
        
        # Check for breakout signals
        if not strategy or strategy == 'breakout':
            if check_breakout(primary_df):
                signal = {
                    'timestamp': datetime.now(),
                    'strategy': 'breakout',
                    'timeframe': primary_tf,
                    'price': primary_df['close'].iloc[-1]
                }
                
                # Confirm with other timeframes
                confirmed_signal = self.confirm_signal(signal, data_dict)
                if confirmed_signal['confirmed']:
                    signals.append(confirmed_signal)
        
        return signals
    
    def get_best_signal(self, signals):
        """Get the best signal from a list of confirmed signals.
        
        Args:
            signals (list): List of confirmed signals
            
        Returns:
            dict: Best signal or None
        """
        if not signals:
            return None
        
        # Sort signals by confidence
        sorted_signals = sorted(signals, key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Return signal with highest confidence
        return sorted_signals[0]


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    import ccxt
    
    # Initialize exchange
    exchange = ccxt.binance()
    
    # Fetch data for multiple timeframes
    symbol = 'BTC/USDT'
    timeframes = ['5m', '15m', '1h', '4h', '1d']
    
    data_dict = {}
    for tf in timeframes:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, tf, limit=100)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            data_dict[tf] = df
            print(f"Fetched {len(df)} candles for {symbol} {tf}")
        except Exception as e:
            print(f"Error fetching {symbol} {tf}: {str(e)}")
    
    # Initialize multi-timeframe analyzer
    mta = MultiTimeframeAnalyzer()
    
    # Analyze trend alignment
    alignment = mta.analyze_trend_alignment(data_dict)
    print(f"Trend alignment: {alignment['trend_aligned']}")
    print(f"Alignment score: {alignment['alignment_score']:.2f}")
    print(f"Bullish timeframes: {alignment['bullish_timeframes']}")
    print(f"Bearish timeframes: {alignment['bearish_timeframes']}")
    
    # Analyze timeframes for signals
    signals = mta.analyze_timeframes(data_dict)
    print(f"Found {len(signals)} confirmed signals")
    
    # Get best signal
    best_signal = mta.get_best_signal(signals)
    if best_signal:
        print(f"Best signal: {best_signal['strategy']} on {best_signal['timeframe']} with confidence {best_signal['confidence']:.2f}")
    else:
        print("No confirmed signals found")
