"""
Risk Management Module for Cryptocurrency Trading
Responsible for filtering signals and ensuring only the safest trades are alerted
with support for regime-based risk parameter adaptation
"""
import logging
import numpy as np
import pandas as pd
from datetime import datetime
import os
import json

# Import market regime detector if available
try:
    from market_regime import MarketRegime
except ImportError:
    MarketRegime = None

logger = logging.getLogger(__name__)

class RiskManager:
    """Risk management class to filter trading signals with regime awareness"""
    
    def __init__(self, risk_reward_ratio=2.0, max_drawdown_percent=2.0, 
                 min_daily_volume=1000000, min_success_probability=0.6,
                 data_dir='data', enable_regimes=True):
        """Initialize the risk manager.
        
        Args:
            risk_reward_ratio (float): Minimum risk/reward ratio required
            max_drawdown_percent (float): Maximum drawdown percentage allowed
            min_daily_volume (int): Minimum 24-hour volume in USDT
            min_success_probability (float): Minimum probability of success required
            data_dir (str): Directory for data files
            enable_regimes (bool): Whether to enable regime-based risk parameters
        """
        self.risk_reward_ratio = risk_reward_ratio
        self.max_drawdown_percent = max_drawdown_percent
        self.min_daily_volume = min_daily_volume
        self.min_success_probability = min_success_probability
        self.data_dir = data_dir
        self.enable_regimes = enable_regimes
        
        # Store recent alerts to prevent duplicates
        self.recent_alerts = {}
        # Store last price for each symbol to detect significant changes
        self.last_prices = {}
        # Minimum price change percentage required for a new alert (3%)
        self.min_price_change_pct = 3.0
        # Time window for duplicate prevention (in hours)
        self.alert_window_hours = 4
        
        # Store current market regime for each symbol
        self.current_regimes = {}
        
        # Initialize market regime detector if available
        self.market_regime = MarketRegime(data_dir=data_dir) if MarketRegime and enable_regimes else None
        
        logger.info(f"Risk manager initialized with risk/reward ratio: {risk_reward_ratio}, max drawdown: {max_drawdown_percent}%")
        if self.market_regime:
            logger.info("Regime-based risk management enabled")

    
    def is_safe_trade(self, df, entry_price, stop_loss, take_profit, volume_24h, symbol=None, timeframe=None):
        """Determine if a trade meets safety criteria.
        
        Args:
            df (DataFrame): Historical OHLCV data
            entry_price (float): Potential entry price
            stop_loss (float): Stop loss price level
            take_profit (float): Take profit price level
            volume_24h (float): 24-hour trading volume in USDT
            symbol (str): Trading symbol (e.g. 'BTC/USDT')
            timeframe (str): Timeframe (e.g. '15m', '1h')
            
        Returns:
            tuple: (is_safe, reasons) where is_safe is a boolean and reasons is a list
                  of strings explaining the decision
        """
        reasons = []
        
        # Detect market regime if enabled
        current_regime = None
        if self.market_regime and symbol and timeframe and self.enable_regimes:
            try:
                current_regime = self.market_regime.detect_regime(df, symbol=symbol, timeframe=timeframe)
                self.current_regimes[f"{symbol}_{timeframe}"] = current_regime
                reasons.append(f"Market regime: {current_regime}")
                
                # Get optimized parameters for the current regime
                regime_params = self.market_regime.get_risk_parameters(current_regime)
                
                # Apply regime-specific risk parameters
                self.risk_reward_ratio = regime_params.get('risk_reward_ratio', self.risk_reward_ratio)
                self.max_drawdown_percent = regime_params.get('max_drawdown_percent', self.max_drawdown_percent)
                
                # Adjust stop loss based on regime (optional)
                if 'stop_loss_factor' in regime_params and stop_loss:
                    factor = regime_params['stop_loss_factor']
                    if factor != 1.0:
                        risk_amount = abs(entry_price - stop_loss)
                        adjusted_risk = risk_amount * factor
                        
                        # Adjust stop loss while preserving direction
                        if stop_loss < entry_price:  # Long position
                            stop_loss = entry_price - adjusted_risk
                        else:  # Short position
                            stop_loss = entry_price + adjusted_risk
                            
                        reasons.append(f"Adjusted stop loss for {current_regime} (factor: {factor:.2f})")
                
            except Exception as e:
                logger.error(f"Error detecting market regime: {str(e)}")
        
        # Skip duplicate alerts for the same symbol/timeframe within the alert window
        if symbol and timeframe:
            alert_key = f"{symbol}_{timeframe}"
            current_time = datetime.now()
            
            # Check if we've sent an alert for this symbol/timeframe recently
            if alert_key in self.recent_alerts:
                last_alert_time, last_price = self.recent_alerts[alert_key]
                hours_since_last_alert = (current_time - last_alert_time).total_seconds() / 3600
                
                # Check if within time window
                if hours_since_last_alert < self.alert_window_hours:
                    # Calculate price change since last alert
                    price_change_pct = abs(100 * (entry_price - last_price) / last_price)
                    
                    # If price hasn't changed significantly, reject the alert
                    if price_change_pct < self.min_price_change_pct:
                        return False, [f"Duplicate alert: {symbol} on {timeframe} sent {hours_since_last_alert:.1f}h ago with only {price_change_pct:.2f}% price change"]
        
        # Check risk/reward ratio
        risk = entry_price - stop_loss if entry_price > stop_loss else stop_loss - entry_price
        reward = take_profit - entry_price if take_profit > entry_price else entry_price - take_profit
        
        if risk <= 0:
            reasons.append(f"Invalid risk: Entry {entry_price:.8f}, Stop {stop_loss:.8f}")
            return False, reasons
            
        current_ratio = reward / risk
        if current_ratio < self.risk_reward_ratio:
            reasons.append(f"Risk/reward ratio too low: {current_ratio:.2f} < {self.risk_reward_ratio:.2f}")
            return False, reasons
        else:
            reasons.append(f"Risk/reward ratio good: {current_ratio:.2f} > {self.risk_reward_ratio:.2f}")
        
        # Check trading volume
        if volume_24h < self.min_daily_volume:
            reasons.append(f"24h volume too low: ${volume_24h:.2f} < ${self.min_daily_volume:.2f}")
            return False, reasons
        else:
            reasons.append(f"24h volume sufficient: ${volume_24h:.2f}")
        
        # Calculate historical success probability based on similar setups
        success_prob = self._calculate_success_probability(df, entry_price, stop_loss, take_profit)
        if success_prob < self.min_success_probability:
            reasons.append(f"Success probability too low: {success_prob:.2f} < {self.min_success_probability:.2f}")
            return False, reasons
        else:
            reasons.append(f"Success probability good: {success_prob:.2f}")
        
        # Calculate potential drawdown
        max_drawdown = self._calculate_potential_drawdown(df, entry_price)
        if max_drawdown > self.max_drawdown_percent:
            reasons.append(f"Potential drawdown too high: {max_drawdown:.2f}% > {self.max_drawdown_percent:.2f}%")
            return False, reasons
        else:
            reasons.append(f"Acceptable drawdown: {max_drawdown:.2f}%")
        
        # Check if price is near major support/resistance
        near_sr = self._is_near_support_resistance(df, entry_price)
        if near_sr:
            reasons.append(f"Price near major support/resistance: increased risk")
            
        # Store this alert to prevent duplicates
        if symbol and timeframe:
            self.recent_alerts[f"{symbol}_{timeframe}"] = (datetime.now(), entry_price)
        
        # All criteria met, trade is considered safe
        return True, reasons
    
    def predict_success_probability(self, df):
        """Calculate probability of success for reporting purposes
        
        Args:
            df (DataFrame): Historical OHLCV data
            
        Returns:
            float: Probability value between 0 and 1
        """
        # This is a simplified version of _calculate_success_probability for external use
        return self._calculate_success_probability(df, df['close'].iloc[-1], df['close'].iloc[-1] * 0.95, df['close'].iloc[-1] * 1.05)
        
    def _calculate_success_probability(self, df, entry_price, stop_loss, take_profit):
        """Calculate probability of success based on historical data.
        
        This is a simplified implementation. In a real system, this would use more
        sophisticated analysis of historical patterns.
        
        Args:
            df (DataFrame): Historical OHLCV data
            entry_price (float): Potential entry price
            stop_loss (float): Stop loss price level
            take_profit (float): Take profit price level
        
        Returns:
            float: Estimated probability of success (0.0 to 1.0)
        """
        if len(df) < 30:
            # Not enough historical data
            return 0.5
            
        # Get recent price action
        recent_df = df.tail(30)
        
        # Calculate average volatility
        volatility = (recent_df['high'] - recent_df['low']).mean() / recent_df['close'].mean() * 100
        
        # Analyze trend strength (simple version - using closing prices)
        closes = recent_df['close'].values
        trend_strength = np.corrcoef(np.arange(len(closes)), closes)[0, 1]
        
        # Adjust for distance to stop loss and take profit
        risk = abs(entry_price - stop_loss) / entry_price
        reward = abs(take_profit - entry_price) / entry_price
        
        # Basic success probability calculation
        # This is simplified - real implementation would be more complex
        base_probability = 0.5
        
        # Adjust for trend (stronger trend = higher probability)
        trend_factor = 0.1 * trend_strength
        
        # Adjust for volatility (higher volatility = lower probability)
        volatility_factor = -0.005 * volatility
        
        # Adjust for risk/reward (better risk/reward = higher probability)
        rr_factor = 0.05 * (reward / risk) if risk > 0 else 0
        
        # Combine factors (capped between 0.1 and 0.9)
        probability = max(0.1, min(0.9, base_probability + trend_factor + volatility_factor + rr_factor))
        
        return probability
    
    def _calculate_potential_drawdown(self, df, entry_price):
        """Calculate potential drawdown based on recent volatility.
        
        Args:
            df (DataFrame): Historical OHLCV data
            entry_price (float): Potential entry price
        
        Returns:
            float: Estimated maximum drawdown percentage
        """
        if len(df) < 14:
            return 5.0  # Default value if not enough data
            
        # Calculate Average True Range (ATR) as volatility measure
        tr_list = []
        for i in range(1, len(df)):
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            prev_close = df['close'].iloc[i-1]
            tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
            tr_list.append(tr)
        
        atr = np.mean(tr_list[-14:])
        
        # Potential drawdown is estimated as 2x ATR as percentage of entry price
        potential_drawdown = (2 * atr / entry_price) * 100
        
        return potential_drawdown
    
    def get_current_regime(self, symbol, timeframe):
        """Get the current detected market regime for a symbol/timeframe
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            str: Current market regime or None
        """
        key = f"{symbol}_{timeframe}"
        return self.current_regimes.get(key, None)
    
    def update_trade_result(self, symbol, timeframe, profit, success):
        """Update trade result for regime performance tracking
        
        Args:
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            profit (float): Profit amount
            success (bool): Whether the trade was successful
        """
        if not self.market_regime:
            return
            
        key = f"{symbol}_{timeframe}"
        if key in self.current_regimes:
            regime = self.current_regimes[key]
            self.market_regime.update_trade_result(regime, profit, success)
            logger.info(f"Updated trade result for {regime} regime: {'success' if success else 'failure'} with {profit:.2f} profit")
    
    def optimize_parameters(self):
        """Optimize risk parameters based on historical performance
        
        Returns:
            dict: Updated risk parameters
        """
        if self.market_regime:
            updated_params = self.market_regime.optimize_parameters()
            logger.info("Optimized risk parameters based on performance")
            return updated_params
        return None
    
    def get_regime_performance(self):
        """Get performance metrics for each market regime
        
        Returns:
            dict: Performance metrics by regime
        """
        if self.market_regime:
            return self.market_regime.get_regime_performance()
        return {}
    
    def reset_daily_stats(self):
        """Reset daily statistics"""
        if self.market_regime:
            self.market_regime.reset_daily_stats()
    
    def _is_near_support_resistance(self, df, entry_price):
        """Check if price is near major support/resistance levels.
        
        Args:
            df (DataFrame): Historical OHLCV data
            entry_price (float): Potential entry price
        
        Returns:
            bool: True if price is near major support/resistance
        """
        if len(df) < 50:
            return False
            
        # Find recent highs and lows
        recent_df = df.tail(50)
        highs = recent_df['high'].values
        lows = recent_df['low'].values
        
        # Simple support/resistance detection
        # Find local maxima and minima
        resistance_levels = []
        support_levels = []
        
        for i in range(2, len(highs) - 2):
            # Resistance: local high with 2 lower highs on each side
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                resistance_levels.append(highs[i])
            
            # Support: local low with 2 higher lows on each side
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                support_levels.append(lows[i])
        
        # Check if entry price is near any support/resistance level
        threshold = 0.01  # 1% threshold
        
        for level in resistance_levels + support_levels:
            if abs(entry_price - level) / entry_price < threshold:
                return True
                
        return False

    def calculate_position_size(self, entry_price, stop_loss, target_profit, max_risk_percent=1.0, symbol=None, timeframe=None):
        """Calculate position size based on risk parameters.
        
        Args:
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            target_profit (float): Target profit amount in USD
            max_risk_percent (float): Maximum percentage of capital to risk
            symbol (str, optional): Trading symbol (e.g. 'BTC/USDT')
            timeframe (str, optional): Timeframe (e.g. '15m', '1h')
                
        Returns:
            float: Position size in base currency units
        """
        # Apply regime-specific position sizing if applicable
        position_size_factor = 1.0
        
        if self.market_regime and symbol and timeframe and self.enable_regimes:
            regime_key = f"{symbol}_{timeframe}"
            if regime_key in self.current_regimes:
                current_regime = self.current_regimes[regime_key]
                regime_params = self.market_regime.get_risk_parameters(current_regime)
                position_size_factor = regime_params.get('position_size_factor', 1.0)
                logger.debug(f"Applied position size factor of {position_size_factor} for {current_regime} regime")
        
        # Risk per unit
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit <= 0:
            return 0
            
        # Position size based on target profit
        price_move_for_target = target_profit / risk_per_unit * abs(entry_price - stop_loss)
        base_position_size = target_profit / price_move_for_target
        
        # Apply regime-specific adjustment
        adjusted_position_size = base_position_size * position_size_factor
        
        # Safety check - we don't have account balance info in this example
        # so we're skipping the max risk check for now
        
        return adjusted_position_size
