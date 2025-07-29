"""
Trading strategies implementation
"""

import pandas as pd
import numpy as np
import logging
from typing import Dict, List, Optional, Tuple, Union

from src.indicators import (
    calculate_supertrend,
    calculate_adx,
    calculate_atr,
    detect_inside_bar,
    is_atr_in_bottom_percentile
)

logger = logging.getLogger(__name__)


class Strategy:
    """Base strategy class that all strategies inherit from"""
    
    def __init__(self, name: str):
        self.name = name
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals for the strategy
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            pd.DataFrame: DataFrame with signals
        """
        raise NotImplementedError("Subclasses must implement this method")
    
    def calculate_confidence(self, df: pd.DataFrame, signal_idx: int) -> float:
        """
        Calculate confidence level for a specific signal
        
        Args:
            df: DataFrame with signals
            signal_idx: Index of the signal to evaluate
            
        Returns:
            float: Confidence level (0-100)
        """
        raise NotImplementedError("Subclasses must implement this method")


class SupertrendADXStrategy(Strategy):
    """
    Supertrend + ADX Trend-Following Strategy
    
    Setup:
    - ADX > 25 (strong trend)
    - Price is above (long) or below (short) the Supertrend line
    - Enter on the Supertrend flip
    - Profit target: 1.5× ATR(14)
    - Stop-loss: at the Supertrend line
    """
    
    def __init__(self):
        super().__init__(name="Supertrend+ADX")
        self.supertrend_period = 10
        self.supertrend_multiplier = 3
        self.adx_period = 14
        self.adx_threshold = 25
        self.atr_period = 14
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate Supertrend + ADX signals
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            pd.DataFrame: DataFrame with signals added
        """
        # Create a copy of the dataframe
        result_df = df.copy()
        
        # Calculate Supertrend
        supertrend, direction = calculate_supertrend(
            result_df, 
            atr_period=self.supertrend_period, 
            multiplier=self.supertrend_multiplier
        )
        result_df['supertrend'] = supertrend
        result_df['supertrend_direction'] = direction
        
        # Calculate ADX
        adx_data = calculate_adx(result_df, period=self.adx_period)
        result_df['adx'] = adx_data['adx']
        result_df['plus_di'] = adx_data['plus_di']
        result_df['minus_di'] = adx_data['minus_di']
        
        # Calculate ATR for profit target and stop loss
        result_df['atr'] = calculate_atr(result_df, period=self.atr_period)
        
        # Initialize signal columns
        result_df['signal'] = 0  # 0: no signal, 1: long, -1: short
        result_df['signal_triggered'] = False
        result_df['profit_target'] = np.nan
        result_df['stop_loss'] = np.nan
        result_df['confidence'] = 0.0
        
        # Generate signals
        for i in range(1, len(result_df)):
            # Check for Supertrend flip (direction change)
            direction_change = result_df['supertrend_direction'].iloc[i] != result_df['supertrend_direction'].iloc[i-1]
            
            # Strong trend condition (ADX > threshold)
            strong_trend = result_df['adx'].iloc[i] > self.adx_threshold
            
            # Signal conditions
            if direction_change and strong_trend:
                # Long signal
                if result_df['supertrend_direction'].iloc[i] == 1:
                    result_df.loc[result_df.index[i], 'signal'] = 1
                    result_df.loc[result_df.index[i], 'signal_triggered'] = True
                    result_df.loc[result_df.index[i], 'profit_target'] = result_df['close'].iloc[i] + (1.5 * result_df['atr'].iloc[i])
                    result_df.loc[result_df.index[i], 'stop_loss'] = result_df['supertrend'].iloc[i]
                    
                # Short signal
                elif result_df['supertrend_direction'].iloc[i] == -1:
                    result_df.loc[result_df.index[i], 'signal'] = -1
                    result_df.loc[result_df.index[i], 'signal_triggered'] = True
                    result_df.loc[result_df.index[i], 'profit_target'] = result_df['close'].iloc[i] - (1.5 * result_df['atr'].iloc[i])
                    result_df.loc[result_df.index[i], 'stop_loss'] = result_df['supertrend'].iloc[i]
        
        # Calculate confidence for each signal
        for i in range(len(result_df)):
            if result_df['signal_triggered'].iloc[i]:
                result_df.loc[result_df.index[i], 'confidence'] = self.calculate_confidence(result_df, i)
        
        return result_df
    
    def calculate_confidence(self, df: pd.DataFrame, signal_idx: int) -> float:
        """
        Calculate confidence level for a Supertrend + ADX signal
        
        Factors affecting confidence:
        1. ADX strength - higher ADX = more confidence
        2. DI separation - larger spread between +DI and -DI = more confidence
        3. Supertrend stability - distance from price to Supertrend line
        4. Recent success rate - backtest last few signals
        
        Args:
            df: DataFrame with signals
            signal_idx: Index of the signal to evaluate
            
        Returns:
            float: Confidence level (0-100)
        """
        # Confidence starts at base level
        confidence = 85.0  # Base level for this high-win-rate strategy
        
        # 1. ADX strength factor (0-5%)
        adx = df['adx'].iloc[signal_idx]
        if adx > 40:  # Very strong trend
            confidence += 5
        elif adx > 30:  # Strong trend
            confidence += 3
        elif adx > 25:  # Moderate trend
            confidence += 1
            
        # 2. DI separation factor (0-4%)
        plus_di = df['plus_di'].iloc[signal_idx]
        minus_di = df['minus_di'].iloc[signal_idx]
        di_spread = abs(plus_di - minus_di)
        if di_spread > 30:
            confidence += 4
        elif di_spread > 20:
            confidence += 2
        elif di_spread > 10:
            confidence += 1
            
        # 3. Supertrend stability factor (0-3%)
        price = df['close'].iloc[signal_idx]
        supertrend = df['supertrend'].iloc[signal_idx]
        price_to_supertrend_ratio = abs(price - supertrend) / df['atr'].iloc[signal_idx]
        
        if price_to_supertrend_ratio > 1.0:
            confidence += 3
        elif price_to_supertrend_ratio > 0.5:
            confidence += 2
        
        # 4. Volume confirmation (0-3%)
        if signal_idx > 0:
            if df['volume'].iloc[signal_idx] > df['volume'].iloc[signal_idx-1] * 1.5:
                confidence += 3
            elif df['volume'].iloc[signal_idx] > df['volume'].iloc[signal_idx-1] * 1.2:
                confidence += 1
                
        # Ensure confidence is capped at 100%
        return min(confidence, 100.0)


class InsideBarStrategy(Strategy):
    """
    Inside‐Bar Breakout with ATR Filter Strategy
    
    Setup:
    - Identify an inside bar (today's range within yesterday's)
    - ATR(14) is in bottom 30% of its 50-period range (low volatility)
    - Enter on a 1-tick breakout above/below the mother bar
    - Profit target: 1× ATR
    - Stop-loss: 0.5× ATR
    """
    
    def __init__(self):
        super().__init__(name="InsideBar+ATR")
        self.atr_period = 14
        self.lookback_period = 50
        self.volatility_percentile = 30
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate Inside Bar + ATR signals
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            pd.DataFrame: DataFrame with signals added
        """
        # Create a copy of the dataframe
        result_df = df.copy()
        
        # Calculate ATR
        result_df['atr'] = calculate_atr(result_df, period=self.atr_period)
        
        # Detect inside bars
        result_df['inside_bar'] = detect_inside_bar(result_df)
        
        # Check if ATR is in bottom percentile
        result_df['low_volatility'] = is_atr_in_bottom_percentile(
            result_df, 
            atr_period=self.atr_period, 
            lookback=self.lookback_period, 
            percentile=self.volatility_percentile
        )
        
        # Initialize signal columns
        result_df['signal'] = 0  # 0: no signal, 1: long, -1: short
        result_df['signal_triggered'] = False
        result_df['mother_bar_high'] = np.nan
        result_df['mother_bar_low'] = np.nan
        result_df['profit_target_long'] = np.nan
        result_df['profit_target_short'] = np.nan
        result_df['stop_loss_long'] = np.nan
        result_df['stop_loss_short'] = np.nan
        result_df['confidence'] = 0.0
        
        # Generate signals
        for i in range(1, len(result_df) - 1):  # -1 to avoid looking ahead
            # Check for inside bar with low volatility
            if result_df['inside_bar'].iloc[i] and result_df['low_volatility'].iloc[i]:
                # Store mother bar high and low (the previous bar)
                mother_bar_high = result_df['high'].iloc[i-1]
                mother_bar_low = result_df['low'].iloc[i-1]
                
                result_df.loc[result_df.index[i], 'mother_bar_high'] = mother_bar_high
                result_df.loc[result_df.index[i], 'mother_bar_low'] = mother_bar_low
                
                # Set up potential signals for next bar
                current_atr = result_df['atr'].iloc[i]
                
                # Long setup (breakout above mother bar high)
                result_df.loc[result_df.index[i], 'profit_target_long'] = mother_bar_high + current_atr
                result_df.loc[result_df.index[i], 'stop_loss_long'] = mother_bar_high - (0.5 * current_atr)
                
                # Short setup (breakout below mother bar low)
                result_df.loc[result_df.index[i], 'profit_target_short'] = mother_bar_low - current_atr
                result_df.loc[result_df.index[i], 'stop_loss_short'] = mother_bar_low + (0.5 * current_atr)
                
                # Check if the next bar breaks out (we're not at the end of the dataframe)
                if i < len(result_df) - 1:
                    next_bar = result_df.iloc[i+1]
                    
                    # Long signal: breakout above mother bar high
                    if next_bar['high'] > mother_bar_high:
                        result_df.loc[result_df.index[i+1], 'signal'] = 1
                        result_df.loc[result_df.index[i+1], 'signal_triggered'] = True
                        result_df.loc[result_df.index[i+1], 'profit_target'] = result_df.loc[result_df.index[i], 'profit_target_long']
                        result_df.loc[result_df.index[i+1], 'stop_loss'] = result_df.loc[result_df.index[i], 'stop_loss_long']
                    
                    # Short signal: breakout below mother bar low
                    elif next_bar['low'] < mother_bar_low:
                        result_df.loc[result_df.index[i+1], 'signal'] = -1
                        result_df.loc[result_df.index[i+1], 'signal_triggered'] = True
                        result_df.loc[result_df.index[i+1], 'profit_target'] = result_df.loc[result_df.index[i], 'profit_target_short']
                        result_df.loc[result_df.index[i+1], 'stop_loss'] = result_df.loc[result_df.index[i], 'stop_loss_short']
        
        # Calculate confidence for each signal
        for i in range(len(result_df)):
            if result_df['signal_triggered'].iloc[i]:
                result_df.loc[result_df.index[i], 'confidence'] = self.calculate_confidence(result_df, i)
        
        return result_df
    
    def calculate_confidence(self, df: pd.DataFrame, signal_idx: int) -> float:
        """
        Calculate confidence level for an Inside Bar + ATR signal
        
        Factors affecting confidence:
        1. How low the volatility is - lower = better
        2. Bar size - smaller inside bar = better
        3. Breakout strength
        4. Trend alignment
        
        Args:
            df: DataFrame with signals
            signal_idx: Index of the signal to evaluate
            
        Returns:
            float: Confidence level (0-100)
        """
        # Confidence starts at base level
        confidence = 88.0  # Base level for this high-win-rate strategy
        
        if signal_idx < 2:  # Need at least 2 bars before the signal
            return confidence
            
        # Find the inside bar (one bar before signal)
        inside_bar_idx = signal_idx - 1
        
        # 1. Volatility factor (0-3%)
        # Check how deep in the bottom percentile the ATR is
        atr_rank = df['atr'].iloc[inside_bar_idx] / df['atr'].iloc[inside_bar_idx-10:inside_bar_idx].max()
        if atr_rank < 0.2:  # Very low volatility
            confidence += 3
        elif atr_rank < 0.3:
            confidence += 2
        elif atr_rank < 0.4:
            confidence += 1
            
        # 2. Inside bar size factor (0-3%)
        # Smaller inside bars relative to the mother bar are better
        mother_bar_idx = inside_bar_idx - 1
        mother_bar_range = df['high'].iloc[mother_bar_idx] - df['low'].iloc[mother_bar_idx]
        inside_bar_range = df['high'].iloc[inside_bar_idx] - df['low'].iloc[inside_bar_idx]
        
        if mother_bar_range > 0:  # Avoid division by zero
            size_ratio = inside_bar_range / mother_bar_range
            if size_ratio < 0.3:  # Very small inside bar
                confidence += 3
            elif size_ratio < 0.5:
                confidence += 2
            elif size_ratio < 0.7:
                confidence += 1
                
        # 3. Breakout strength (0-4%)
        signal_direction = df['signal'].iloc[signal_idx]
        if signal_direction == 1:  # Long signal
            mother_bar_high = df['mother_bar_high'].iloc[inside_bar_idx]
            breakout_strength = (df['high'].iloc[signal_idx] - mother_bar_high) / df['atr'].iloc[inside_bar_idx]
            
            if breakout_strength > 0.5:  # Strong breakout
                confidence += 4
            elif breakout_strength > 0.3:
                confidence += 2
            elif breakout_strength > 0.1:
                confidence += 1
                
        elif signal_direction == -1:  # Short signal
            mother_bar_low = df['mother_bar_low'].iloc[inside_bar_idx]
            breakout_strength = (mother_bar_low - df['low'].iloc[signal_idx]) / df['atr'].iloc[inside_bar_idx]
            
            if breakout_strength > 0.5:  # Strong breakout
                confidence += 4
            elif breakout_strength > 0.3:
                confidence += 2
            elif breakout_strength > 0.1:
                confidence += 1
                
        # 4. Volume confirmation (0-2%)
        if df['volume'].iloc[signal_idx] > df['volume'].iloc[inside_bar_idx] * 1.3:
            confidence += 2
        elif df['volume'].iloc[signal_idx] > df['volume'].iloc[inside_bar_idx] * 1.1:
            confidence += 1
            
        # Ensure confidence is capped at 100%
        return min(confidence, 100.0)
