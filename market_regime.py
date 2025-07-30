#!/usr/bin/env python
"""
Market Regime Detection Module
-----------------------------
Detects different market regimes and provides optimized risk parameters:
1. Trending Market (Bullish/Bearish)
2. Ranging/Sideways Market
3. Volatile Market
4. Calm Market
5. Reversal/Transition Market

Adjusts risk parameters based on detected regime to maximize performance
across different market conditions.
"""
import logging
import numpy as np
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from scipy import stats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketRegime:
    """Market regime detection and risk parameter optimization"""
    
    # Define market regimes
    REGIME_BULLISH_TREND = "bullish_trend"
    REGIME_BEARISH_TREND = "bearish_trend"
    REGIME_RANGING = "ranging"
    REGIME_VOLATILE = "volatile"
    REGIME_CALM = "calm"
    REGIME_REVERSAL = "reversal"
    
    def __init__(self, config=None, data_dir='data'):
        """Initialize market regime detector
        
        Args:
            config (dict): Configuration parameters
            data_dir (str): Directory for data files
        """
        self.config = config or {}
        self.data_dir = data_dir
        self.regime_history_file = os.path.join(data_dir, 'regime_history.json')
        self.performance_file = os.path.join(data_dir, 'regime_performance.json')
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        # Default configuration
        self.default_config = {
            # Lookback periods for regime detection
            'trend_lookback': 20,
            'volatility_lookback': 14,
            'atr_lookback': 14,
            
            # Thresholds
            'trend_threshold': 30,  # ADX threshold for trend
            'volatility_threshold': 1.5,  # Multiplier of average volatility
            'range_threshold': 0.3,  # Max price change for ranging markets
            
            # Risk parameters by regime
            'risk_params': {
                self.REGIME_BULLISH_TREND: {
                    'risk_reward_ratio': 2.5,
                    'max_drawdown_percent': 2.0,
                    'position_size_factor': 1.2,
                    'stop_loss_factor': 1.0
                },
                self.REGIME_BEARISH_TREND: {
                    'risk_reward_ratio': 3.0,
                    'max_drawdown_percent': 1.5,
                    'position_size_factor': 0.8,
                    'stop_loss_factor': 0.8
                },
                self.REGIME_RANGING: {
                    'risk_reward_ratio': 2.0,
                    'max_drawdown_percent': 1.5,
                    'position_size_factor': 1.0,
                    'stop_loss_factor': 0.9
                },
                self.REGIME_VOLATILE: {
                    'risk_reward_ratio': 3.5,
                    'max_drawdown_percent': 1.2,
                    'position_size_factor': 0.7,
                    'stop_loss_factor': 0.7
                },
                self.REGIME_CALM: {
                    'risk_reward_ratio': 1.8,
                    'max_drawdown_percent': 2.0,
                    'position_size_factor': 1.3,
                    'stop_loss_factor': 1.1
                },
                self.REGIME_REVERSAL: {
                    'risk_reward_ratio': 2.8,
                    'max_drawdown_percent': 1.3,
                    'position_size_factor': 0.8,
                    'stop_loss_factor': 0.8
                }
            }
        }
        
        # Apply default configuration if values are missing
        for key, value in self.default_config.items():
            if key not in self.config:
                self.config[key] = value
            elif key == 'risk_params' and isinstance(value, dict):
                if key not in self.config:
                    self.config[key] = {}
                # Merge risk params
                for regime, params in value.items():
                    if regime not in self.config[key]:
                        self.config[key][regime] = params
                    else:
                        for param_key, param_value in params.items():
                            if param_key not in self.config[key][regime]:
                                self.config[key][regime][param_key] = param_value
        
        # Load historical regimes and performance data
        self.regime_history = self._load_regime_history()
        self.regime_performance = self._load_regime_performance()
        
        logger.info(f"Market Regime Detector initialized with {len(self.regime_history)} historical records")

    def _load_regime_history(self):
        """Load regime history from file
        
        Returns:
            dict: Regime history by symbol and timeframe
        """
        try:
            if os.path.exists(self.regime_history_file):
                with open(self.regime_history_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading regime history: {str(e)}")
            return {}
    
    def _save_regime_history(self):
        """Save regime history to file"""
        try:
            with open(self.regime_history_file, 'w') as f:
                json.dump(self.regime_history, f)
        except Exception as e:
            logger.error(f"Error saving regime history: {str(e)}")
    
    def _load_regime_performance(self):
        """Load regime performance from file
        
        Returns:
            dict: Regime performance metrics
        """
        try:
            if os.path.exists(self.performance_file):
                with open(self.performance_file, 'r') as f:
                    return json.load(f)
            return {
                regime: {
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0.0,
                    'profit': 0.0,
                    'loss': 0.0,
                    'avg_profit': 0.0,
                    'avg_loss': 0.0
                } for regime in [
                    self.REGIME_BULLISH_TREND,
                    self.REGIME_BEARISH_TREND,
                    self.REGIME_RANGING,
                    self.REGIME_VOLATILE,
                    self.REGIME_CALM,
                    self.REGIME_REVERSAL
                ]
            }
        except Exception as e:
            logger.error(f"Error loading regime performance: {str(e)}")
            return {}
    
    def _save_regime_performance(self):
        """Save regime performance to file"""
        try:
            with open(self.performance_file, 'w') as f:
                json.dump(self.regime_performance, f)
        except Exception as e:
            logger.error(f"Error saving regime performance: {str(e)}")
    
    def _calculate_atr(self, df, period=14):
        """Calculate Average True Range (ATR)
        
        Args:
            df (DataFrame): OHLCV data
            period (int): ATR period
            
        Returns:
            float: Current ATR value
        """
        high = df['high'].values
        low = df['low'].values
        close = np.roll(df['close'].values, 1)
        close[0] = high[0]
        
        tr1 = high - low
        tr2 = np.abs(high - close)
        tr3 = np.abs(low - close)
        
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        atr = np.mean(tr[-period:])
        
        return atr
    
    def _calculate_adx(self, df, period=14):
        """Calculate Average Directional Index (ADX)
        
        Args:
            df (DataFrame): OHLCV data
            period (int): ADX period
            
        Returns:
            tuple: (ADX, +DI, -DI)
        """
        # Simple ADX calculation
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # Smoothing factor
        alpha = 1.0 / period
        
        # True range
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        # Directional movement
        up_move = high[1:] - high[:-1]
        down_move = low[:-1] - low[1:]
        
        pos_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        neg_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        # Smooth true range and directional movement
        tr_smooth = np.zeros(len(tr))
        pos_dm_smooth = np.zeros(len(pos_dm))
        neg_dm_smooth = np.zeros(len(neg_dm))
        
        tr_smooth[0] = np.mean(tr[:period])
        pos_dm_smooth[0] = np.mean(pos_dm[:period])
        neg_dm_smooth[0] = np.mean(neg_dm[:period])
        
        for i in range(1, len(tr)):
            tr_smooth[i] = (1 - alpha) * tr_smooth[i-1] + alpha * tr[i]
            if i < len(pos_dm):
                pos_dm_smooth[i] = (1 - alpha) * pos_dm_smooth[i-1] + alpha * pos_dm[i]
                neg_dm_smooth[i] = (1 - alpha) * neg_dm_smooth[i-1] + alpha * neg_dm[i]
        
        # Directional indicators
        pdi = 100.0 * pos_dm_smooth / tr_smooth
        ndi = 100.0 * neg_dm_smooth / tr_smooth
        
        # Directional index
        dx = 100.0 * np.abs(pdi - ndi) / (pdi + ndi)
        
        # Average directional index
        adx = np.zeros(len(dx))
        adx[period-1] = np.mean(dx[:period])
        for i in range(period, len(dx)):
            adx[i] = (adx[i-1] * (period-1) + dx[i]) / period
        
        # Return last values
        if len(adx) > 0:
            return adx[-1], pdi[-1], ndi[-1]
        else:
            return 0, 0, 0
    
    def _calculate_volatility(self, df, period=14):
        """Calculate volatility as standard deviation of returns
        
        Args:
            df (DataFrame): OHLCV data
            period (int): Volatility period
            
        Returns:
            float: Current volatility value
        """
        if len(df) < period + 1:
            return 0
            
        # Calculate daily returns
        returns = np.diff(np.log(df['close'].values))
        
        # Standard deviation of returns (volatility)
        volatility = np.std(returns[-period:])
        
        return volatility
    
    def _is_ranging_market(self, df, threshold=0.03, period=20):
        """Detect ranging market
        
        Args:
            df (DataFrame): OHLCV data
            threshold (float): Maximum price change for ranging market
            period (int): Lookback period
            
        Returns:
            bool: True if market is ranging
        """
        if len(df) < period:
            return False
            
        # Get recent close prices
        closes = df['close'].values[-period:]
        
        # Calculate max percentage change
        max_close = np.max(closes)
        min_close = np.min(closes)
        
        price_change = (max_close - min_close) / min_close
        
        # Check linear regression slope
        x = np.arange(len(closes))
        slope, _, r_value, _, _ = stats.linregress(x, closes)
        
        # Ranging market has small price change and low r-squared
        is_ranging = price_change < threshold and r_value**2 < 0.25
        
        return is_ranging
    
    def _is_reversal_market(self, df, lookback=10):
        """Detect potential market reversal
        
        Args:
            df (DataFrame): OHLCV data
            lookback (int): Lookback period
            
        Returns:
            bool: True if market shows reversal patterns
        """
        if len(df) < lookback + 10:
            return False
            
        # Get recent close prices
        closes = df['close'].values
        
        # Calculate short-term and longer-term trend
        short_slope = np.polyfit(np.arange(lookback), closes[-lookback:], 1)[0]
        long_slope = np.polyfit(np.arange(lookback*2), closes[-(lookback*2):], 1)[0]
        
        # Check for trend direction change
        is_reversal = (short_slope * long_slope < 0) and abs(short_slope) > abs(long_slope) * 0.5
        
        return is_reversal
    
    def detect_regime(self, df, symbol=None, timeframe=None):
        """Detect market regime based on technical indicators
        
        Args:
            df (DataFrame): OHLCV data
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            str: Detected market regime
        """
        try:
            if len(df) < 50:  # Need sufficient data for analysis
                logger.warning(f"Insufficient data for regime detection ({len(df)} points)")
                return self.REGIME_RANGING  # Default to ranging if not enough data
                
            # Calculate key metrics
            adx, pdi, ndi = self._calculate_adx(df, period=self.config['trend_lookback'])
            volatility = self._calculate_volatility(df, period=self.config['volatility_lookback'])
            atr = self._calculate_atr(df, period=self.config['atr_lookback'])
            
            # Get historical volatility for comparison
            historical_vol = np.mean([self._calculate_volatility(df.iloc[:-i], 
                                    period=self.config['volatility_lookback']) 
                                    for i in range(5, 15)])
            
            is_ranging = self._is_ranging_market(df, 
                                              threshold=self.config['range_threshold'],
                                              period=self.config['trend_lookback'])
            
            is_reversal = self._is_reversal_market(df, lookback=self.config['trend_lookback']//2)
            
            # Determine regime based on indicators
            regime = self.REGIME_RANGING  # Default regime
            
            if is_reversal:
                regime = self.REGIME_REVERSAL
            elif adx > self.config['trend_threshold']:
                # Strong trend exists
                if pdi > ndi:
                    regime = self.REGIME_BULLISH_TREND
                else:
                    regime = self.REGIME_BEARISH_TREND
            elif is_ranging:
                regime = self.REGIME_RANGING
            elif volatility > historical_vol * self.config['volatility_threshold']:
                regime = self.REGIME_VOLATILE
            else:
                regime = self.REGIME_CALM
            
            # Log detection
            logger.info(f"Detected {regime} regime for {symbol or 'unknown'} {timeframe or ''}")
            logger.debug(f"Metrics: ADX={adx:.2f}, +DI={pdi:.2f}, -DI={ndi:.2f}, " +
                        f"Volatility={volatility:.4f}, Historical Vol={historical_vol:.4f}")
            
            # Store regime history
            if symbol and timeframe:
                key = f"{symbol}_{timeframe}"
                if key not in self.regime_history:
                    self.regime_history[key] = []
                
                # Add to history with timestamp
                self.regime_history[key].append({
                    'timestamp': datetime.now().isoformat(),
                    'regime': regime,
                    'adx': float(adx),
                    'pdi': float(pdi),
                    'ndi': float(ndi),
                    'volatility': float(volatility),
                    'is_ranging': is_ranging,
                    'is_reversal': is_reversal
                })
                
                # Keep only recent history (last 100 entries)
                if len(self.regime_history[key]) > 100:
                    self.regime_history[key] = self.regime_history[key][-100:]
                
                # Save history periodically (every 10 updates)
                if len(self.regime_history[key]) % 10 == 0:
                    self._save_regime_history()
            
            return regime
            
        except Exception as e:
            logger.error(f"Error detecting market regime: {str(e)}")
            return self.REGIME_RANGING  # Default to ranging on error
    
    def get_risk_parameters(self, regime):
        """Get optimized risk parameters for a specific market regime
        
        Args:
            regime (str): Market regime
            
        Returns:
            dict: Risk parameters
        """
        # Check if regime exists in config
        if regime in self.config['risk_params']:
            return self.config['risk_params'][regime]
        else:
            # Return default parameters
            logger.warning(f"Unknown regime: {regime}, using default parameters")
            return self.config['risk_params'][self.REGIME_RANGING]
    
    def get_regime_performance(self):
        """Get performance metrics for each regime
        
        Returns:
            dict: Performance metrics by regime
        """
        return self.regime_performance
    
    def update_trade_result(self, regime, profit, success):
        """Update performance metrics for a regime
        
        Args:
            regime (str): Market regime
            profit (float): Profit amount
            success (bool): Whether the trade was successful
        """
        try:
            if regime not in self.regime_performance:
                self.regime_performance[regime] = {
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0.0,
                    'profit': 0.0,
                    'loss': 0.0,
                    'avg_profit': 0.0,
                    'avg_loss': 0.0
                }
            
            # Update metrics
            metrics = self.regime_performance[regime]
            metrics['trades'] += 1
            
            if success:
                metrics['wins'] += 1
                metrics['profit'] += profit
                if metrics['wins'] > 0:
                    metrics['avg_profit'] = metrics['profit'] / metrics['wins']
            else:
                metrics['losses'] += 1
                metrics['loss'] += abs(profit)  # Store losses as positive values
                if metrics['losses'] > 0:
                    metrics['avg_loss'] = metrics['loss'] / metrics['losses']
            
            # Calculate win rate
            if metrics['trades'] > 0:
                metrics['win_rate'] = metrics['wins'] / metrics['trades']
            
            # Save updated performance
            self._save_regime_performance()
            
            logger.info(f"Updated {regime} performance: {metrics['win_rate']:.2f} win rate over {metrics['trades']} trades")
            
        except Exception as e:
            logger.error(f"Error updating regime performance: {str(e)}")
    
    def optimize_parameters(self):
        """Optimize risk parameters based on historical performance
        
        Returns:
            dict: Updated risk parameters
        """
        try:
            # Check if we have sufficient performance data
            min_trades = 10
            has_sufficient_data = any(
                self.regime_performance.get(regime, {}).get('trades', 0) >= min_trades
                for regime in self.regime_performance
            )
            
            if not has_sufficient_data:
                logger.info("Insufficient trade data for optimization")
                return self.config['risk_params']
            
            # Optimize parameters based on performance
            optimized_params = {}
            
            for regime, metrics in self.regime_performance.items():
                if metrics['trades'] < min_trades:
                    # Not enough data, keep default parameters
                    optimized_params[regime] = self.config['risk_params'].get(regime, 
                                            self.config['risk_params'][self.REGIME_RANGING])
                    continue
                
                # Start with current parameters
                params = self.config['risk_params'].get(regime, 
                                                    self.config['risk_params'][self.REGIME_RANGING]).copy()
                
                # Adjust parameters based on performance
                win_rate = metrics['win_rate']
                
                if win_rate > 0.6:
                    # High win rate - can be more aggressive
                    params['position_size_factor'] *= 1.1
                    params['stop_loss_factor'] *= 1.05
                elif win_rate < 0.4:
                    # Low win rate - be more conservative
                    params['position_size_factor'] *= 0.9
                    params['risk_reward_ratio'] *= 1.1
                    params['max_drawdown_percent'] *= 0.9
                
                # Check profit vs loss ratio
                if metrics['wins'] > 0 and metrics['losses'] > 0:
                    profit_loss_ratio = metrics['avg_profit'] / max(metrics['avg_loss'], 0.0001)
                    
                    if profit_loss_ratio > 1.5:
                        # Good profit/loss ratio - can reduce risk-reward requirement
                        params['risk_reward_ratio'] *= 0.95
                    elif profit_loss_ratio < 0.8:
                        # Poor profit/loss ratio - increase risk-reward requirement
                        params['risk_reward_ratio'] *= 1.1
                
                # Cap parameters to reasonable values
                params['risk_reward_ratio'] = max(1.5, min(4.0, params['risk_reward_ratio']))
                params['max_drawdown_percent'] = max(1.0, min(3.0, params['max_drawdown_percent']))
                params['position_size_factor'] = max(0.5, min(1.5, params['position_size_factor']))
                params['stop_loss_factor'] = max(0.5, min(1.5, params['stop_loss_factor']))
                
                optimized_params[regime] = params
            
            # Add default parameters for any missing regimes
            for regime in [
                self.REGIME_BULLISH_TREND,
                self.REGIME_BEARISH_TREND,
                self.REGIME_RANGING,
                self.REGIME_VOLATILE,
                self.REGIME_CALM,
                self.REGIME_REVERSAL
            ]:
                if regime not in optimized_params:
                    optimized_params[regime] = self.config['risk_params'].get(
                        regime, self.config['risk_params'][self.REGIME_RANGING])
            
            # Update configuration
            self.config['risk_params'] = optimized_params
            
            logger.info("Optimized risk parameters based on performance")
            
            return optimized_params
            
        except Exception as e:
            logger.error(f"Error optimizing parameters: {str(e)}")
            return self.config['risk_params']
    
    def get_all_regimes(self):
        """Get list of all possible market regimes
        
        Returns:
            list: Market regimes
        """
        return [
            self.REGIME_BULLISH_TREND,
            self.REGIME_BEARISH_TREND,
            self.REGIME_RANGING,
            self.REGIME_VOLATILE,
            self.REGIME_CALM,
            self.REGIME_REVERSAL
        ]
    
    def get_symbol_regimes(self, symbol=None, timeframe=None, limit=10):
        """Get recent regimes for a symbol
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            limit (int): Maximum number of entries
            
        Returns:
            list: Recent regimes
        """
        if not symbol or not timeframe:
            return []
            
        key = f"{symbol}_{timeframe}"
        if key not in self.regime_history:
            return []
        
        # Return recent regimes
        recent_regimes = self.regime_history[key][-limit:]
        return recent_regimes
    
    def reset_daily_stats(self):
        """Reset daily statistics"""
        # Currently nothing to reset daily
        pass


# Example usage if run directly
if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    
    # Create sample data
    dates = pd.date_range(start="2023-01-01", periods=100)
    
    # Trending market
    trend_prices = np.linspace(100, 150, 100) + np.random.normal(0, 3, 100)
    trend_df = pd.DataFrame({
        'timestamp': dates,
        'open': trend_prices,
        'high': trend_prices + np.random.uniform(1, 5, 100),
        'low': trend_prices - np.random.uniform(1, 5, 100),
        'close': trend_prices,
        'volume': np.random.uniform(1000, 5000, 100)
    })
    
    # Ranging market
    range_prices = 100 + np.random.normal(0, 5, 100)
    range_df = pd.DataFrame({
        'timestamp': dates,
        'open': range_prices,
        'high': range_prices + np.random.uniform(1, 5, 100),
        'low': range_prices - np.random.uniform(1, 5, 100),
        'close': range_prices,
        'volume': np.random.uniform(1000, 5000, 100)
    })
    
    # Volatile market
    volatile_prices = 100 + np.cumsum(np.random.normal(0, 3, 100))
    volatile_df = pd.DataFrame({
        'timestamp': dates,
        'open': volatile_prices,
        'high': volatile_prices + np.random.uniform(3, 10, 100),
        'low': volatile_prices - np.random.uniform(3, 10, 100),
        'close': volatile_prices,
        'volume': np.random.uniform(2000, 10000, 100)
    })
    
    # Initialize market regime detector
    regime_detector = MarketRegime(data_dir='data')
    
    # Detect regimes
    trend_regime = regime_detector.detect_regime(trend_df, symbol="SAMPLE/TREND", timeframe="1d")
    range_regime = regime_detector.detect_regime(range_df, symbol="SAMPLE/RANGE", timeframe="1d")
    volatile_regime = regime_detector.detect_regime(volatile_df, symbol="SAMPLE/VOLATILE", timeframe="1d")
    
    print(f"Trend sample regime: {trend_regime}")
    print(f"Range sample regime: {range_regime}")
    print(f"Volatile sample regime: {volatile_regime}")
    
    # Get risk parameters
    trend_params = regime_detector.get_risk_parameters(trend_regime)
    range_params = regime_detector.get_risk_parameters(range_regime)
    volatile_params = regime_detector.get_risk_parameters(volatile_regime)
    
    print(f"\nRisk parameters for {trend_regime}: {trend_params}")
    print(f"Risk parameters for {range_regime}: {range_params}")
    print(f"Risk parameters for {volatile_regime}: {volatile_params}")
