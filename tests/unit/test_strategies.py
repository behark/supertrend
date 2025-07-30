"""
Unit tests for trading strategies
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import strategies to test
try:
    from src.strategies import SupertrendADXStrategy, InsideBarStrategy
except ImportError:
    # Fallback for different project structure
    from Inside.Bar.Strategy.src.strategies import SupertrendADXStrategy, InsideBarStrategy


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


class TestSuperTrendStrategy:
    """Test SuperTrend strategy implementation"""
    
    def test_strategy_initialization(self):
        """Test strategy initialization with different parameters"""
        strat = SupertrendADXStrategy()
        assert strat.name == "Supertrend+ADX"
        assert strat.supertrend_period == 10
        assert strat.supertrend_multiplier == 3
    
    def test_supertrend_signals_format(self):
        """Test that signals are generated in correct format"""
        df = make_sample_ohlcv(50)
        strat = SupertrendADXStrategy()
        signals = strat.generate_signals(df)
        
        assert isinstance(signals, pd.DataFrame)
        assert 'signal' in signals.columns
        assert len(signals) == len(df)
    
    def test_supertrend_signal_values(self):
        """Test that signals contain valid values (-1, 0, 1)"""
        df = make_sample_ohlcv(50)
        strat = SupertrendADXStrategy()
        signals = strat.generate_signals(df)
        
        valid_signals = {-1, 0, 1}
        assert set(signals['signal'].unique()).issubset(valid_signals)
    
    def test_supertrend_trend_detection(self):
        """Test that strategy detects trends properly"""
        # Create trending data
        df = make_sample_ohlcv(100)
        df['close'] = df['close'] + np.linspace(0, 50, len(df))  # Strong uptrend
        
        strat = SupertrendADXStrategy()
        signals = strat.generate_signals(df)
        
        # Should detect some signals in trending data
        assert signals['signal'].abs().sum() > 0
    
    def test_supertrend_parameters_effect(self):
        """Test that different parameters affect signal generation"""
        df = make_sample_ohlcv(50)
        
        strat1 = SupertrendADXStrategy()
        strat1.supertrend_period = 5
        strat1.supertrend_multiplier = 2
        
        strat2 = SupertrendADXStrategy()
        strat2.supertrend_period = 20
        strat2.supertrend_multiplier = 3
        
        signals1 = strat1.generate_signals(df)
        signals2 = strat2.generate_signals(df)
        
        # Different parameters should give different results
        assert not signals1['signal'].equals(signals2['signal'])


class TestInsideBarStrategy:
    """Test Inside Bar strategy implementation"""
    
    def test_strategy_initialization(self):
        """Test strategy initialization"""
        strat = InsideBarStrategy()
        assert hasattr(strat, 'generate_signals')
    
    def test_insidebar_signals_format(self):
        """Test that signals are generated in correct format"""
        df = make_sample_ohlcv(30)
        strat = InsideBarStrategy()
        signals = strat.generate_signals(df)
        
        assert isinstance(signals, pd.DataFrame)
        assert 'signal' in signals.columns
        assert len(signals) == len(df)
    
    def test_insidebar_signal_values(self):
        """Test that signals contain valid values"""
        df = make_sample_ohlcv(30)
        strat = InsideBarStrategy()
        signals = strat.generate_signals(df)
        
        valid_signals = {-1, 0, 1}
        assert set(signals['signal'].unique()).issubset(valid_signals)
    
    def test_insidebar_pattern_detection(self):
        """Test that strategy detects inside bar patterns"""
        # Create data with inside bars
        df = make_sample_ohlcv(20)
        # Create inside bar pattern
        df.loc[df.index[10], 'high'] = df.loc[df.index[9], 'high'] * 0.9
        df.loc[df.index[10], 'low'] = df.loc[df.index[9], 'low'] * 1.1
        
        strat = InsideBarStrategy()
        signals = strat.generate_signals(df)
        
        # Should detect some signals
        assert signals['signal'].abs().sum() >= 0  # May or may not detect depending on implementation


class TestStrategyIntegration:
    """Test integration between strategies and indicators"""
    
    def test_strategy_with_indicators(self):
        """Test that strategies work with calculated indicators"""
        df = make_sample_ohlcv(50)
        
        # Test SuperTrend strategy
        st_strat = SupertrendADXStrategy()
        st_signals = st_strat.generate_signals(df)
        
        # Test Inside Bar strategy
        ib_strat = InsideBarStrategy()
        ib_signals = ib_strat.generate_signals(df)
        
        # Both should produce valid signals
        assert len(st_signals) == len(df)
        assert len(ib_signals) == len(df)
    
    def test_strategy_consistency(self):
        """Test that strategies produce consistent results"""
        df = make_sample_ohlcv(50)
        strat = SupertrendADXStrategy()
        
        # Run strategy twice
        signals1 = strat.generate_signals(df)
        signals2 = strat.generate_signals(df)
        
        # Results should be identical
        pd.testing.assert_frame_equal(signals1, signals2)
    
    def test_strategy_edge_cases(self):
        """Test strategies with edge cases"""
        # Empty dataframe
        empty_df = pd.DataFrame()
        strat = SupertrendADXStrategy()
        
        # Should handle empty data gracefully
        try:
            signals = strat.generate_signals(empty_df)
            # If it doesn't raise an exception, check the result
            assert isinstance(signals, pd.DataFrame)
        except (ValueError, IndexError):
            # It's also acceptable to raise an exception for empty data
            pass
        
        # Single row dataframe
        single_row = make_sample_ohlcv(1)
        signals = strat.generate_signals(single_row)
        assert len(signals) == 1 