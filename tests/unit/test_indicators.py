"""
Unit tests for technical indicators
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import indicators to test
try:
    from src.indicators import calculate_supertrend, calculate_adx, calculate_atr, detect_inside_bar
except ImportError:
    # Fallback for different project structure
    from Inside.Bar.Strategy.src.indicators import calculate_supertrend, calculate_adx, calculate_atr, detect_inside_bar


def make_sample_ohlcv(n=100):
    """Create sample OHLCV data for testing"""
    now = datetime.utcnow()
    times = [now + timedelta(minutes=i) for i in range(n)]
    price = np.linspace(100, 200, n) + np.random.randn(n)
    df = pd.DataFrame({
        'timestamp': times,
        'open': price,
        'high': price + np.abs(np.random.randn(n)),
        'low': price - np.abs(np.random.randn(n)),
        'close': price + np.random.randn(n),
        'volume': np.random.rand(n) * 1000
    })
    df.set_index('timestamp', inplace=True)
    return df


class TestSupertrendIndicator:
    """Test Supertrend indicator calculations"""
    
    def test_supertrend_output_format(self):
        """Test that supertrend returns correct format"""
        df = make_sample_ohlcv(50)
        st, direction = calculate_supertrend(df, atr_period=10, multiplier=3)
        
        assert isinstance(st, pd.Series)
        assert isinstance(direction, pd.Series)
        assert len(st) == len(df)
        assert len(direction) == len(df)
        assert st.dropna().dtype == float
    
    def test_supertrend_values_range(self):
        """Test that supertrend values are reasonable"""
        df = make_sample_ohlcv(50)
        st, direction = calculate_supertrend(df, atr_period=10, multiplier=3)
        
        # Supertrend should be close to price levels
        assert st.dropna().min() > 0
        assert st.dropna().max() < df['high'].max() * 1.5
    
    def test_supertrend_parameters(self):
        """Test different parameter combinations"""
        df = make_sample_ohlcv(50)
        
        # Test different periods
        st1, dir1 = calculate_supertrend(df, atr_period=5, multiplier=2)
        st2, dir2 = calculate_supertrend(df, atr_period=20, multiplier=3)
        
        assert len(st1) == len(st2)
        assert not st1.equals(st2)  # Different parameters should give different results


class TestADXIndicator:
    """Test ADX indicator calculations"""
    
    def test_adx_bounds(self):
        """Test that ADX values are within expected bounds (0-100)"""
        df = make_sample_ohlcv(200)
        adx_data = calculate_adx(df, period=14)
        
        assert adx_data['adx'].between(0, 100).all()
    
    def test_adx_trend_detection(self):
        """Test that ADX detects trends properly"""
        # Create trending data
        df = make_sample_ohlcv(100)
        # Add strong trend
        df['close'] = df['close'] + np.linspace(0, 50, len(df))
        df['high'] = df['high'] + np.linspace(0, 50, len(df))
        df['low'] = df['low'] + np.linspace(0, 50, len(df))
        
        adx_data = calculate_adx(df, period=14)
        
        # ADX should be higher in trending periods
        assert adx_data['adx'].dropna().mean() > 20  # Should detect some trend strength


class TestATRIndicator:
    """Test ATR indicator calculations"""
    
    def test_atr_positive_values(self):
        """Test that ATR values are always positive"""
        df = make_sample_ohlcv(50)
        atr = calculate_atr(df, period=14)
        
        assert (atr >= 0).all()
    
    def test_atr_volatility_sensitivity(self):
        """Test that ATR responds to volatility changes"""
        df = make_sample_ohlcv(100)
        
        # Add volatility spike
        df.loc[df.index[50], 'high'] *= 1.1
        df.loc[df.index[50], 'low'] *= 0.9
        
        atr = calculate_atr(df, period=14)
        
        # ATR should spike around the volatility increase
        assert atr.iloc[50:60].max() > atr.iloc[40:50].mean()


class TestInsideBarDetection:
    """Test inside bar pattern detection"""
    
    def test_inside_bar_flag(self):
        """Test basic inside bar detection"""
        data = pd.DataFrame({
            'high': [5, 6, 5.5],
            'low': [1, 2, 1.8],
            'open': [2, 3, 2.5],
            'close': [4, 5, 4.5]
        })
        flags = detect_inside_bar(data)
        
        # Second bar should be inside the first
        assert flags.tolist() == [False, True, False]
    
    def test_no_inside_bars(self):
        """Test when no inside bars exist"""
        data = pd.DataFrame({
            'high': [5, 6, 7],
            'low': [1, 2, 3],
            'open': [2, 3, 4],
            'close': [4, 5, 6]
        })
        flags = detect_inside_bar(data)
        
        assert all(not flag for flag in flags)
    
    def test_multiple_inside_bars(self):
        """Test multiple inside bars in sequence"""
        data = pd.DataFrame({
            'high': [10, 8, 7, 9],
            'low': [1, 2, 3, 1],
            'open': [5, 4, 5, 5],
            'close': [6, 5, 6, 6]
        })
        flags = detect_inside_bar(data)
        
        # Should detect inside bars at positions 1 and 2
        assert flags.tolist() == [False, True, True, False] 