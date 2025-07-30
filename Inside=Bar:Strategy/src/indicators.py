"""
Technical indicators module
"""

import numpy as np
import pandas as pd
from typing import Tuple


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range (ATR)
    
    Args:
        df: DataFrame with OHLC data
        period: ATR period
        
    Returns:
        pd.Series: ATR values
    """
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    
    # Calculate the three components of TR
    tr1 = high - low  # Current high - current low
    tr2 = abs(high - close)  # Current high - previous close
    tr3 = abs(low - close)  # Current low - previous close
    
    # True Range is the maximum of the three
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    
    # Calculate ATR using exponential moving average
    atr = tr.ewm(span=period, adjust=False).mean()
    
    return atr


def calculate_supertrend(df: pd.DataFrame, atr_period: int = 10, multiplier: float = 3.0) -> Tuple[pd.Series, pd.Series]:
    """
    Calculate Supertrend indicator
    
    Args:
        df: DataFrame with OHLC data
        atr_period: Period for ATR calculation
        multiplier: ATR multiplier for band calculation
        
    Returns:
        Tuple[pd.Series, pd.Series]: Supertrend values and direction (1 for bullish, -1 for bearish)
    """
    # Calculate ATR
    atr = calculate_atr(df, atr_period)
    
    # Calculate basic upper and lower bands
    hl2 = (df['high'] + df['low']) / 2
    basic_upper_band = hl2 + (multiplier * atr)
    basic_lower_band = hl2 - (multiplier * atr)
    
    # Initialize final bands and supertrend series
    final_upper_band = basic_upper_band.copy()
    final_lower_band = basic_lower_band.copy()
    supertrend = pd.Series(0.0, index=df.index)
    direction = pd.Series(1, index=df.index)  # 1 for bullish, -1 for bearish
    
    # Calculate final bands and supertrend values
    for i in range(1, len(df)):
        if basic_upper_band.iloc[i] < final_upper_band.iloc[i-1] or df['close'].iloc[i-1] > final_upper_band.iloc[i-1]:
            final_upper_band.iloc[i] = basic_upper_band.iloc[i]
        else:
            final_upper_band.iloc[i] = final_upper_band.iloc[i-1]
            
        if basic_lower_band.iloc[i] > final_lower_band.iloc[i-1] or df['close'].iloc[i-1] < final_lower_band.iloc[i-1]:
            final_lower_band.iloc[i] = basic_lower_band.iloc[i]
        else:
            final_lower_band.iloc[i] = final_lower_band.iloc[i-1]
            
        # Determine direction and supertrend value
        if supertrend.iloc[i-1] == final_upper_band.iloc[i-1] and df['close'].iloc[i] <= final_upper_band.iloc[i]:
            supertrend.iloc[i] = final_upper_band.iloc[i]
            direction.iloc[i] = -1
        elif supertrend.iloc[i-1] == final_upper_band.iloc[i-1] and df['close'].iloc[i] > final_upper_band.iloc[i]:
            supertrend.iloc[i] = final_lower_band.iloc[i]
            direction.iloc[i] = 1
        elif supertrend.iloc[i-1] == final_lower_band.iloc[i-1] and df['close'].iloc[i] >= final_lower_band.iloc[i]:
            supertrend.iloc[i] = final_lower_band.iloc[i]
            direction.iloc[i] = 1
        elif supertrend.iloc[i-1] == final_lower_band.iloc[i-1] and df['close'].iloc[i] < final_lower_band.iloc[i]:
            supertrend.iloc[i] = final_upper_band.iloc[i]
            direction.iloc[i] = -1
    
    return supertrend, direction


def calculate_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Average Directional Index (ADX)
    
    Args:
        df: DataFrame with OHLC data
        period: ADX calculation period
        
    Returns:
        pd.DataFrame: DataFrame with ADX, +DI, and -DI values
    """
    # Calculate True Range
    tr = calculate_atr(df, 1)  # Use ATR with period=1 to get TR
    
    # Calculate +DM and -DM
    high_diff = df['high'].diff()
    low_diff = df['low'].diff() * -1
    
    # Calculate +DM
    plus_dm = pd.Series(0.0, index=df.index)
    plus_dm.loc[(high_diff > low_diff) & (high_diff > 0)] = high_diff.loc[(high_diff > low_diff) & (high_diff > 0)]
    
    # Calculate -DM
    minus_dm = pd.Series(0.0, index=df.index)
    minus_dm.loc[(low_diff > high_diff) & (low_diff > 0)] = low_diff.loc[(low_diff > high_diff) & (low_diff > 0)]
    
    # Smooth +DM, -DM, and TR using Wilder's smoothing
    plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / tr.ewm(alpha=1/period, adjust=False).mean())
    minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / tr.ewm(alpha=1/period, adjust=False).mean())
    
    # Calculate DX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    
    # Calculate ADX
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    
    # Create output DataFrame
    result = pd.DataFrame({
        'plus_di': plus_di,
        'minus_di': minus_di,
        'adx': adx
    })
    
    return result


def detect_inside_bar(df: pd.DataFrame) -> pd.Series:
    """
    Detect Inside Bar pattern
    
    Args:
        df: DataFrame with OHLC data
        
    Returns:
        pd.Series: Boolean series indicating inside bars
    """
    # An inside bar occurs when today's high is lower than yesterday's high
    # and today's low is higher than yesterday's low
    high_condition = df['high'] < df['high'].shift(1)
    low_condition = df['low'] > df['low'].shift(1)
    
    # Combine conditions
    inside_bar = high_condition & low_condition
    
    return inside_bar


def is_atr_in_bottom_percentile(df: pd.DataFrame, atr_period: int = 14, lookback: int = 50, percentile: float = 30) -> pd.Series:
    """
    Check if current ATR is in the bottom percentile of its range
    
    Args:
        df: DataFrame with OHLC data
        atr_period: Period for ATR calculation
        lookback: Period for percentile calculation
        percentile: Percentile threshold (0-100)
        
    Returns:
        pd.Series: Boolean series indicating if ATR is in bottom percentile
    """
    # Calculate ATR
    atr = calculate_atr(df, atr_period)
    
    # Calculate rolling percentile rank of ATR
    def rolling_percentile_rank(x):
        return pd.Series(x).rank(pct=True).iloc[-1] * 100
    
    atr_rank = atr.rolling(window=lookback).apply(rolling_percentile_rank, raw=False)
    
    # Check if ATR is in bottom percentile
    is_low_volatility = atr_rank <= percentile
    
    return is_low_volatility
