"""
Technical indicators for cryptocurrency trading signals
Implements:
1. Volume + Price Spike Alert
2. Moving Averages (MA) Cross
3. Breakout Strategy Trigger
"""
import numpy as np
import pandas as pd


def check_volume_price_spike(df, volume_threshold=2.0, price_change_threshold=1.0, periods=5):
    """
    Check for volume and price spikes
    
    Args:
        df (DataFrame): OHLCV dataframe with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        volume_threshold (float): Multiple of average volume to consider as spike (e.g., 2.0 = 200% of avg)
        price_change_threshold (float): Percentage change in price to consider as spike
        periods (int): Number of periods to look back for average calculation
        
    Returns:
        bool: True if both volume and price spike conditions are met, False otherwise
    """
    if len(df) < periods + 1:
        return False
    
    # Calculate average volume over specified periods
    avg_volume = df['volume'].iloc[-(periods+1):-1].mean()
    current_volume = df['volume'].iloc[-1]
    
    # Calculate price change (percentage)
    previous_close = df['close'].iloc[-2]
    current_close = df['close'].iloc[-1]
    price_change_pct = abs(100 * (current_close - previous_close) / previous_close)
    
    # Check for volume spike
    volume_spike = current_volume >= (avg_volume * volume_threshold)
    
    # Check for price spike
    price_spike = price_change_pct >= price_change_threshold
    
    # Both conditions must be true
    if volume_spike and price_spike:
        return True
    
    return False


def check_ma_cross(df, fast_ma=9, slow_ma=21):
    """
    Check for Moving Average crosses
    
    Args:
        df (DataFrame): OHLCV dataframe with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        fast_ma (int): Fast Moving Average period
        slow_ma (int): Slow Moving Average period
        
    Returns:
        bool: True if a bullish cross occurred (fast MA crosses above slow MA), False otherwise
    """
    if len(df) < slow_ma + 2:  # Need at least enough data for slow MA plus 2 points to detect cross
        return False
    
    # Calculate moving averages
    df = df.copy()
    df[f'ma_{fast_ma}'] = df['close'].rolling(window=fast_ma).mean()
    df[f'ma_{slow_ma}'] = df['close'].rolling(window=slow_ma).mean()
    
    # Check for bullish cross (fast MA crosses above slow MA)
    # Current: fast MA > slow MA
    # Previous: fast MA <= slow MA
    current_fast = df[f'ma_{fast_ma}'].iloc[-1]
    current_slow = df[f'ma_{slow_ma}'].iloc[-1]
    previous_fast = df[f'ma_{fast_ma}'].iloc[-2]
    previous_slow = df[f'ma_{slow_ma}'].iloc[-2]
    
    if (current_fast > current_slow) and (previous_fast <= previous_slow):
        # Also check if we're in overall uptrend (current close > slow MA)
        if df['close'].iloc[-1] > current_slow:
            return True
    
    return False


def check_breakout(df, periods=20, confirmation_bars=3, threshold_multiplier=1.0):
    """
    Check for price breakouts from consolidation
    
    Args:
        df (DataFrame): OHLCV dataframe with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        periods (int): Number of periods to look back for consolidation
        confirmation_bars (int): Number of bars to confirm the breakout
        threshold_multiplier (float): Multiplier for ATR to determine breakout threshold
        
    Returns:
        bool: True if a bullish breakout is detected, False otherwise
    """
    if len(df) < periods + confirmation_bars:
        return False
    
    # Get the range excluding the most recent confirmation_bars
    lookback_df = df.iloc[-(periods+confirmation_bars):-confirmation_bars]
    
    # Calculate the resistance (highest high in the lookback period)
    resistance = lookback_df['high'].max()
    
    # Calculate Average True Range (ATR) as a volatility measure
    tr_list = []
    for i in range(1, len(lookback_df)):
        high = lookback_df['high'].iloc[i]
        low = lookback_df['low'].iloc[i]
        prev_close = lookback_df['close'].iloc[i-1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)
    atr = np.mean(tr_list) if tr_list else 0
    
    # Calculate breakout threshold
    breakout_threshold = resistance + (atr * threshold_multiplier)
    
    # Check if price has closed above the resistance level in recent bars
    recent_closes = df['close'].iloc[-confirmation_bars:]
    if (recent_closes > breakout_threshold).any():
        # Also check increasing volume to confirm breakout
        recent_volume = df['volume'].iloc[-confirmation_bars:]
        avg_volume = df['volume'].iloc[-(periods+confirmation_bars):-confirmation_bars].mean()
        if recent_volume.mean() > avg_volume:
            return True
    
    return False


def rsi(df, periods=14):
    """
    Calculate the Relative Strength Index (RSI)
    
    Args:
        df (DataFrame): OHLCV dataframe with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        periods (int): RSI period
        
    Returns:
        Series: RSI values
    """
    close_delta = df['close'].diff()
    
    # Make two series: one for gains, one for losses
    up = close_delta.clip(lower=0)
    down = -1 * close_delta.clip(upper=0)
    
    # Calculate the EWMA (Exponential Weighted Moving Average)
    ma_up = up.ewm(com=periods-1, adjust=True, min_periods=periods).mean()
    ma_down = down.ewm(com=periods-1, adjust=True, min_periods=periods).mean()
    
    # Calculate RSI
    rsi = 100 - (100 / (1 + ma_up / ma_down))
    return rsi


def calculate_risk_metrics(df, entry_price):
    """
    Calculate risk metrics for a potential trade
    
    Args:
        df (DataFrame): OHLCV dataframe
        entry_price (float): Potential entry price
        
    Returns:
        tuple: (stop_loss_price, volatility)
    """
    # Calculate ATR for volatility
    tr_list = []
    for i in range(1, len(df)):
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]
        prev_close = df['close'].iloc[i-1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)
    atr = np.mean(tr_list[-14:]) if len(tr_list) >= 14 else np.mean(tr_list) if tr_list else 0
    
    # Calculate potential stop loss (2 ATR below entry for example)
    stop_loss = entry_price - (2 * atr)
    
    return stop_loss, atr


def calculate_risk_metrics(df, entry_price):
    """
    Calculate risk metrics for a potential trade
    
    Args:
        df (DataFrame): OHLCV dataframe
        entry_price (float): Potential entry price
        
    Returns:
        tuple: (stop_loss_price, volatility)
    """
    # Calculate ATR for volatility
    tr_list = []
    for i in range(1, len(df)):
        high = df['high'].iloc[i]
        low = df['low'].iloc[i]
        prev_close = df['close'].iloc[i-1]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr_list.append(tr)
    atr = np.mean(tr_list[-14:]) if len(tr_list) >= 14 else np.mean(tr_list) if tr_list else 0
    
    # Calculate potential stop loss (2 ATR below entry for example)
    stop_loss = entry_price - (2 * atr)
    
    return stop_loss, atr

def calculate_rsi(df, periods=14):
    """
    Calculate RSI (wrapper function for backward compatibility)
    
    Args:
        df (DataFrame): OHLCV dataframe with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        periods (int): RSI period
        
    Returns:
        Series: RSI values
    """
    return rsi(df, periods)
