#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Market Analyzer Module

Provides market condition detection capabilities:
- Trend detection (trending up/down, ranging)
- Volatility analysis (low, medium, high)
- Volume analysis
- Market regime classification
- Automated parameter profile selection
"""

import os
import logging
import threading
import json
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from enum import Enum, auto
import time
import warnings

# Suppress pandas warnings that might occur during calculations
warnings.filterwarnings('ignore', category=RuntimeWarning)

# Configure module logger
logger = logging.getLogger(__name__)

# Try to import parameter manager
try:
    from src.utils.parameter_manager import parameter_manager
    PARAMETER_MANAGER_AVAILABLE = True
except ImportError:
    PARAMETER_MANAGER_AVAILABLE = False
    logger.warning("Parameter manager not available - adaptive control disabled")

# Try to import analytics logger for performance tracking
try:
    from src.utils.analytics_logger import analytics_logger
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

# Try to import playbook manager for regime-based strategy configuration
try:
    from src.utils.playbook_manager import playbook_manager
    PLAYBOOK_MANAGER_AVAILABLE = True
except ImportError:
    PLAYBOOK_MANAGER_AVAILABLE = False
    logger.warning("Playbook manager not available - automatic playbook activation disabled")
    
# Try to import regime logger for enhanced regime tracking and analysis
try:
    from src.utils.regime_logger import regime_logger
    REGIME_LOGGER_AVAILABLE = True
except ImportError:
    REGIME_LOGGER_AVAILABLE = False
    logger.warning("Regime logger not available - using basic regime tracking only")

class MarketRegime(Enum):
    """Market regime classification"""
    STRONG_UPTREND = auto()       # Strong trending market with clear bullish momentum
    WEAK_UPTREND = auto()         # Moderate bullish trend with some momentum
    RANGING = auto()              # Sideways or consolidation market
    WEAK_DOWNTREND = auto()       # Moderate bearish trend
    STRONG_DOWNTREND = auto()     # Strong bearish trend with momentum
    HIGH_VOLATILITY = auto()      # Highly volatile market, regardless of direction
    LOW_VOLATILITY = auto()       # Unusually low volatility, potential for breakout
    REVERSAL_LIKELY = auto()      # Technical signals suggest potential reversal
    BREAKOUT_FORMING = auto()     # Consolidation with increasing pressure, likely breakout
    UNKNOWN = auto()              # Unable to classify market conditions
    
    @classmethod
    def to_profile(cls, regime: 'MarketRegime') -> str:
        """
        Convert market regime to parameter profile
        
        Args:
            regime: Market regime enum
            
        Returns:
            Parameter profile name
        """
        profile_map = {
            cls.STRONG_UPTREND: "aggressive",
            cls.WEAK_UPTREND: "default",
            cls.RANGING: "conservative",
            cls.WEAK_DOWNTREND: "conservative",
            cls.STRONG_DOWNTREND: "defensive",
            cls.HIGH_VOLATILITY: "conservative",
            cls.LOW_VOLATILITY: "hyper_aggressive",  # New profile for low volatility conditions
            cls.REVERSAL_LIKELY: "reversal_hunter",  # New profile for potential reversals
            cls.BREAKOUT_FORMING: "aggressive",
            cls.UNKNOWN: "default"
        }
        return profile_map.get(regime, "default")

class MarketAnalyzer:
    """
    Market analyzer for detecting market conditions and regimes
    """
    
    # Singleton implementation
    _instance = None
    _lock = threading.Lock()
    
    # Directory and file paths
    CONFIG_DIR = "config"
    MARKET_DATA_FILE = "market_analysis.json"
    
    # Default configuration
    DEFAULT_CONFIG = {
        # Basic trend detection settings
        "trend_period": 14,                 # Period for ADX calculation
        "volatility_period": 20,            # Period for ATR calculation
        "volume_period": 10,                # Period for volume analysis
        
        # Trend strength thresholds
        "strong_trend_threshold": 30,       # ADX threshold for strong trend
        "weak_trend_threshold": 20,         # ADX threshold for weak trend
        
        # Volatility thresholds
        "high_volatility_threshold": 2.5,    # ATR/price ratio multiplier for high volatility
        "low_volatility_threshold": 0.8,     # ATR/price ratio multiplier for low volatility
        
        # New indicator settings
        "rsi_period": 14,                    # Period for RSI calculation
        "rsi_overbought": 70,               # RSI overbought threshold
        "rsi_oversold": 30,                 # RSI oversold threshold
        "rsi_divergence_lookback": 10,      # Bars to look back for RSI divergence
        "ema_fast_period": 8,               # Fast EMA period
        "ema_medium_period": 21,            # Medium EMA period
        "ema_slow_period": 55,              # Slow EMA period
        "bb_period": 20,                    # Bollinger Bands period
        "bb_std_dev": 2.0,                  # Bollinger Bands standard deviation
        "bb_squeeze_threshold": 0.15,       # BB width threshold for squeeze detection
        
        # Transition sensitivity
        "regime_transition_sensitivity": 0.6, # Higher values (0-1) make transitions more sensitive
        "regime_persistence_threshold": 3,   # Minimum number of consecutive matches for regime change
        "confidence_decay_rate": 0.95,      # Rate at which confidence decays if conditions weaken
        
        # Operational settings
        "regime_check_interval_minutes": 60, # How often to check for regime changes
        "lookback_periods": 3,              # Number of intervals to look back for regime stability
        "adaptive_profile_switch": True,    # Auto switch parameter profiles
        "log_regime_changes": True,         # Log regime changes to analytics
        "notification_on_regime_change": True, # Send notification on regime change
        "auto_backtest_on_regime_change": True, # Run mini-backtest on regime change
        "manual_override_enabled": False     # Allow manual override of auto regime switching
    }
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MarketAnalyzer, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
            
    def __init__(self):
        """Initialize the market analyzer"""
        if getattr(self, '_initialized', False):
            return
            
        # Create config directory if it doesn't exist
        self.base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            self.CONFIG_DIR
        )
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize state
        self.current_regime = MarketRegime.UNKNOWN
        self.regime_history = []
        self.last_regime_check = datetime.now() - timedelta(hours=24)  # Force initial check
        self.market_data_cache = {}  # Symbol -> DataFrame
        self.regime_persistence_count = 0  # Track consecutive matching regime detections
        self.last_detected_regime = None  # Last detected regime before confirmation
        self.regime_confidence = 0.0  # Current confidence in regime detection
        self.manual_override_active = False  # Manual override status
        self.manual_override_profile = None  # Profile used for manual override
        
        # Create required profiles if using parameter manager
        if PARAMETER_MANAGER_AVAILABLE and parameter_manager:
            self._ensure_all_profiles_exist()
        
        # Set initialization flag
        self._initialized = True
        
        logger.info("Market analyzer initialized with enhanced regime detection")
        
    def _load_config(self) -> Dict[str, Any]:
        """
        Load analyzer configuration
        
        Returns:
            Configuration dictionary
        """
        config_file = os.path.join(self.base_dir, "market_analyzer_config.json")
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    logger.info(f"Loaded market analyzer config from {config_file}")
                    
                    # Update with any missing default values
                    for key, value in self.DEFAULT_CONFIG.items():
                        if key not in config:
                            config[key] = value
                            
                    return config
        except Exception as e:
            logger.error(f"Error loading market analyzer config: {e}", exc_info=True)
            
        # Use defaults if file doesn't exist or has errors
        return self.DEFAULT_CONFIG.copy()
        
    def _save_config(self) -> None:
        """Save configuration to file"""
        config_file = os.path.join(self.base_dir, "market_analyzer_config.json")
        
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
                logger.info(f"Saved market analyzer config to {config_file}")
        except Exception as e:
            logger.error(f"Error saving market analyzer config: {e}", exc_info=True)
            
    def _save_regime_history(self) -> None:
        """Save regime history to file"""
        history_file = os.path.join(self.base_dir, self.MARKET_DATA_FILE)
        
        try:
            with open(history_file, 'w') as f:
                json.dump({
                    "current_regime": self.current_regime.name,
                    "last_updated": datetime.now().isoformat(),
                    "confidence": self.regime_confidence,
                    "manual_override": self.manual_override_active,
                    "manual_override_profile": self.manual_override_profile,
                    "history": self.regime_history
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving market regime history: {e}", exc_info=True)
    
    def _send_regime_change_notification(self, prev_regime: MarketRegime, 
                                        new_regime: MarketRegime, confidence: float) -> None:
        """Send notification about regime change"""
        try:
            # Try to import notification module if available
            from src.utils.notification import send_notification
            
            # Format message with details
            message = f"🔄 *Market Regime Change Detected*\n\n"
            message += f"• From: {prev_regime.name}\n"
            message += f"• To: *{new_regime.name}*\n"
            message += f"• Confidence: {confidence:.1%}\n"
            message += f"• Parameter Profile: {MarketRegime.to_profile(new_regime)}\n"
            
            # Add tips based on regime
            if new_regime == MarketRegime.STRONG_UPTREND:
                message += "\n💡 *Tip:* Consider taking full-sized positions in trending pairs."
            elif new_regime == MarketRegime.STRONG_DOWNTREND:
                message += "\n💡 *Tip:* Consider reducing position sizes or sitting out of the market."
            elif new_regime == MarketRegime.REVERSAL_LIKELY:
                message += "\n💡 *Tip:* Watch for counter-trend opportunities and divergences."
            elif new_regime == MarketRegime.HIGH_VOLATILITY:
                message += "\n💡 *Tip:* Consider wider stop losses and taking profits quicker."
            
            # Send the notification
            send_notification(message, priority="medium")
            logger.info(f"Sent regime change notification")
            
        except ImportError:
            logger.warning("Notification module not available - can't send regime change alert")
        except Exception as e:
            logger.error(f"Error sending regime change notification: {e}")
            
    def set_manual_override(self, enable: bool, profile_id: Optional[str] = None) -> Dict[str, Any]:
        """Enable or disable manual override of adaptive parameter switching"""
        if enable and not profile_id:
            raise ValueError("Profile ID must be provided when enabling manual override")
            
        if enable and PARAMETER_MANAGER_AVAILABLE and parameter_manager:
            # Verify profile exists
            profiles = parameter_manager.get_profiles()
            if profile_id not in profiles:
                raise ValueError(f"Profile '{profile_id}' does not exist")
                
            # Enable manual override
            self.manual_override_active = True
            self.manual_override_profile = profile_id
            
            # Activate the profile
            parameter_manager.activate_profile(profile_id)
            
            # Log the action
            logger.info(f"Manual override enabled with profile: {profile_id}")
            
            if ANALYTICS_AVAILABLE and analytics_logger:
                analytics_logger.log_event(
                    event_type="manual_override",
                    metadata={
                        "action": "enabled",
                        "profile": profile_id
                    }
                )
                
            # Update config to persist the setting
            self.config["manual_override_enabled"] = True
            self._save_config()
            
            return {
                "status": "success",
                "message": f"Manual override enabled with profile: {profile_id}",
                "profile": profile_id
            }
        elif not enable:
            # Disable manual override
            self.manual_override_active = False
            self.manual_override_profile = None
            
            # Revert to detected regime profile if available
            if PARAMETER_MANAGER_AVAILABLE and parameter_manager and self.current_regime:
                profile_id = MarketRegime.to_profile(self.current_regime)
                parameter_manager.activate_profile(profile_id)
                
            # Log the action
            logger.info("Manual override disabled, reverting to adaptive regime control")
            
            if ANALYTICS_AVAILABLE and analytics_logger:
                analytics_logger.log_event(
                    event_type="manual_override",
                    metadata={
                        "action": "disabled"
                    }
                )
                
            # Update config to persist the setting
            self.config["manual_override_enabled"] = False
            self._save_config()
            
            return {
                "status": "success",
                "message": "Manual override disabled, reverted to adaptive regime control"
            }
        else:
            logger.error("Cannot enable manual override: parameter manager not available")
            return {
                "status": "error",
                "message": "Cannot enable manual override: parameter manager not available"
            }
    
    def get_regime_status(self) -> Dict[str, Any]:
        """Get current market regime status and configuration"""
        return {
            "current_regime": self.current_regime.name,
            "confidence": self.regime_confidence,
            "manual_override": self.manual_override_active,
            "manual_profile": self.manual_override_profile,
            "active_profile": MarketRegime.to_profile(self.current_regime) 
                if not self.manual_override_active else self.manual_override_profile,
            "config": {
                "adaptive_switching": self.config["adaptive_profile_switch"],
                "persistence_threshold": self.config["regime_persistence_threshold"],
                "transition_sensitivity": self.config["regime_transition_sensitivity"],
                "check_interval_minutes": self.config["regime_check_interval_minutes"],
                "auto_backtest": self.config["auto_backtest_on_regime_change"]
            },
            "history": self.regime_history[-5:] if self.regime_history else []
        }
            
    def _ensure_all_profiles_exist(self) -> None:
        """Ensure all required parameter profiles exist"""
        if not PARAMETER_MANAGER_AVAILABLE or not parameter_manager:
            return
            
        # Check which profiles exist
        profiles = parameter_manager.get_profiles()
        
        # Define required profiles
        required_profiles = {
            "defensive": {
                "name": "Defensive",
                "description": "Minimal trading during strong downtrends or high risk conditions",
                "parameters": {
                    "confidence_threshold": 98.0,
                    "max_signals_per_day": 3,
                    "max_trades_per_day": 2,
                    "position_size_percent": 10.0,
                    "supertrend_adx_weight": 75,
                    "inside_bar_weight": 25
                }
            },
            "hyper_aggressive": {
                "name": "Hyper Aggressive",
                "description": "Maximized trading during low volatility strong trends",
                "parameters": {
                    "confidence_threshold": 80.0,
                    "max_signals_per_day": 30,
                    "max_trades_per_day": 20,
                    "position_size_percent": 20.0,
                    "supertrend_adx_weight": 50,
                    "inside_bar_weight": 50
                }
            },
            "reversal_hunter": {
                "name": "Reversal Hunter",
                "description": "Optimized for catching market reversals with divergence signals",
                "parameters": {
                    "confidence_threshold": 85.0,
                    "max_signals_per_day": 8,
                    "max_trades_per_day": 5,
                    "position_size_percent": 15.0,
                    "supertrend_adx_weight": 40,
                    "inside_bar_weight": 60
                }
            }
        }
        
        # Create missing profiles
        for profile_id, profile_data in required_profiles.items():
            if profile_id not in profiles:
                parameter_manager.create_profile(
                    profile_id=profile_id,
                    name=profile_data["name"],
                    description=profile_data["description"],
                    parameters=profile_data["parameters"]
                )
                logger.info(f"Created {profile_data['name']} parameter profile")
            
    def update_config(self, config_updates: Dict[str, Any]) -> None:
        """
        Update configuration values
        
        Args:
            config_updates: Dictionary of config keys and values to update
        """
        # Update config
        for key, value in config_updates.items():
            if key in self.DEFAULT_CONFIG:
                self.config[key] = value
                logger.info(f"Updated market analyzer config: {key} = {value}")
            else:
                logger.warning(f"Unknown market analyzer config key: {key}")
                
        # Save updated config
        self._save_config()
        
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate Average Directional Index (ADX) for trend detection
        
        Args:
            df: DataFrame with OHLCV data
            period: ADX calculation period
            
        Returns:
            DataFrame with ADX values added
        """
        # Make a copy of the dataframe to avoid modifying the original
        df = df.copy()
        
        # Calculate +DM and -DM
        df['high_diff'] = df['high'] - df['high'].shift(1)
        df['low_diff'] = df['low'].shift(1) - df['low']
        
        # +DM
        df['plus_dm'] = np.where(
            (df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0),
            df['high_diff'],
            0
        )
        
        # -DM
        df['minus_dm'] = np.where(
            (df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0),
            df['low_diff'],
            0
        )
        
        # Calculate True Range
        df['tr0'] = abs(df['high'] - df['low'])
        df['tr1'] = abs(df['high'] - df['close'].shift(1))
        df['tr2'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
        
        # Calculate smoothed values
        df['smoothed_tr'] = df['tr'].rolling(period).sum()
        df['smoothed_plus_dm'] = df['plus_dm'].rolling(period).sum()
        df['smoothed_minus_dm'] = df['minus_dm'].rolling(period).sum()
        
        # Calculate +DI and -DI
        df['plus_di'] = 100 * (df['smoothed_plus_dm'] / df['smoothed_tr'])
        df['minus_di'] = 100 * (df['smoothed_minus_dm'] / df['smoothed_tr'])
        
        # Calculate DX
        df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
        
        # Calculate ADX
        df['adx'] = df['dx'].rolling(period).mean()
        
        return df
    
    def calculate_volatility(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """
        Calculate ATR-based volatility
        
        Args:
            df: DataFrame with OHLCV data
            period: ATR calculation period
            
        Returns:
            DataFrame with volatility metrics added
        """
        # Make a copy of the dataframe to avoid modifying the original
        df = df.copy()
        
        # Calculate True Range if not already done
        if 'tr' not in df.columns:
            df['tr0'] = abs(df['high'] - df['low'])
            df['tr1'] = abs(df['high'] - df['close'].shift(1))
            df['tr2'] = abs(df['low'] - df['close'].shift(1))
            df['tr'] = df[['tr0', 'tr1', 'tr2']].max(axis=1)
        
        # Calculate ATR
        df['atr'] = df['tr'].rolling(period).mean()
        
        # Calculate ATR as percentage of price (normalized volatility)
        df['atr_pct'] = df['atr'] / df['close'] * 100
        
        # Calculate rolling volatility metrics
        df['volatility_ratio'] = df['atr_pct'] / df['atr_pct'].rolling(period*2).mean()
        
        # Calculate rate of change in volatility for breakout detection
        df['volatility_change'] = df['atr_pct'].pct_change(5) * 100
        
        return df
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            df: DataFrame with OHLCV data
            period: RSI calculation period
            
        Returns:
            DataFrame with RSI values added
        """
        # Make a copy of the dataframe to avoid modifying the original
        df = df.copy()
        
        # Calculate price changes
        delta = df['close'].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df
    
    def calculate_ema(self, df: pd.DataFrame, fast_period: int = 8, 
                    medium_period: int = 21, slow_period: int = 55) -> pd.DataFrame:
        """
        Calculate multiple Exponential Moving Averages (EMA)
        
        Args:
            df: DataFrame with OHLCV data
            fast_period: Fast EMA period
            medium_period: Medium EMA period
            slow_period: Slow EMA period
            
        Returns:
            DataFrame with EMA values added
        """
        # Make a copy of the dataframe to avoid modifying the original
        df = df.copy()
        
        # Calculate EMAs
        df['ema_fast'] = df['close'].ewm(span=fast_period, adjust=False).mean()
        df['ema_medium'] = df['close'].ewm(span=medium_period, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow_period, adjust=False).mean()
        
        # Calculate crossover signals (1 for bullish, -1 for bearish, 0 for no crossover)
        df['ema_fast_medium_cross'] = 0
        
        # Fast crossing above medium (bullish)
        bullish_cross = (df['ema_fast'] > df['ema_medium']) & \
                        (df['ema_fast'].shift(1) <= df['ema_medium'].shift(1))
        df.loc[bullish_cross, 'ema_fast_medium_cross'] = 1
        
        # Fast crossing below medium (bearish)
        bearish_cross = (df['ema_fast'] < df['ema_medium']) & \
                        (df['ema_fast'].shift(1) >= df['ema_medium'].shift(1))
        df.loc[bearish_cross, 'ema_fast_medium_cross'] = -1
        
        # Calculate alignment of EMAs (positive when aligned bullish, negative when aligned bearish)
        df['ema_alignment'] = np.where((df['ema_fast'] > df['ema_medium']) & 
                                     (df['ema_medium'] > df['ema_slow']), 1, 
                                     np.where((df['ema_fast'] < df['ema_medium']) & 
                                             (df['ema_medium'] < df['ema_slow']), -1, 0))
        
        return df
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = 20, 
                                std_dev: float = 2.0) -> pd.DataFrame:
        """
        Calculate Bollinger Bands
        
        Args:
            df: DataFrame with OHLCV data
            period: Bollinger Bands calculation period
            std_dev: Number of standard deviations for bands
            
        Returns:
            DataFrame with Bollinger Bands values added
        """
        # Make a copy of the dataframe to avoid modifying the original
        df = df.copy()
        
        # Calculate middle band (SMA)
        df['bb_middle'] = df['close'].rolling(window=period).mean()
        
        # Calculate standard deviation
        df['bb_std'] = df['close'].rolling(window=period).std()
        
        # Calculate upper and lower bands
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * std_dev)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * std_dev)
        
        # Calculate bandwidth and %B
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_pct_b'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Calculate squeeze condition (bandwidth declining)
        df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(window=period).mean()
        
        # Calculate percent from middle band (positive above, negative below)
        df['bb_pct_from_middle'] = (df['close'] - df['bb_middle']) / df['bb_middle'] * 100
        
        return df
        
    def detect_rsi_divergence(self, df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
        """
        Detect RSI divergence signals
        
        Args:
            df: DataFrame with OHLCV and RSI data
            lookback: Number of bars to look back for divergence
            
        Returns:
            DataFrame with divergence signals added
        """
        # Make a copy of the dataframe to avoid modifying the original
        df = df.copy()
        
        # Initialize divergence columns
        df['bullish_divergence'] = False
        df['bearish_divergence'] = False
        
        # Need at least 'lookback' periods to detect divergence
        if len(df) <= lookback:
            return df
        
        # Find local price extremes and corresponding RSI values within lookback window
        for i in range(lookback, len(df)):
            # Get window for analysis
            window = df.iloc[i-lookback:i+1]
            
            # Find local price low and corresponding RSI
            low_idx = window['low'].idxmin()
            price_low = window.loc[low_idx, 'low']
            rsi_at_price_low = window.loc[low_idx, 'rsi']
            
            # Find local price high and corresponding RSI
            high_idx = window['high'].idxmax()
            price_high = window.loc[high_idx, 'high']
            rsi_at_price_high = window.loc[high_idx, 'rsi']
            
            # Current values
            current_idx = window.index[-1]
            current_close = window.loc[current_idx, 'close']
            current_rsi = window.loc[current_idx, 'rsi']
            
            # Detect bullish divergence (price makes lower low but RSI makes higher low)
            if (low_idx != current_idx and 
                current_close < price_low and 
                current_rsi > rsi_at_price_low and
                current_rsi < 40):  # Only valid in oversold region
                df.loc[current_idx, 'bullish_divergence'] = True
                
            # Detect bearish divergence (price makes higher high but RSI makes lower high)
            if (high_idx != current_idx and 
                current_close > price_high and 
                current_rsi < rsi_at_price_high and
                current_rsi > 60):  # Only valid in overbought region
                df.loc[current_idx, 'bearish_divergence'] = True
        
        return df
    
    def analyze_market_data(self, ohlcv_data: Dict[str, pd.DataFrame], 
                           primary_symbol: str = 'BTC/USDT') -> Dict[str, Any]:
        """
        Analyze market data to detect current conditions and regime
        
        Args:
            ohlcv_data: Dictionary of symbol -> OHLCV DataFrame
            primary_symbol: Primary symbol to use for market regime detection
            
        Returns:
            Dictionary with analysis results
        """
        if not ohlcv_data or primary_symbol not in ohlcv_data:
            logger.error(f"Primary symbol {primary_symbol} not found in market data")
            return {
                "regime": MarketRegime.UNKNOWN,
                "confidence": 0.0,
                "details": {}
            }
            
        try:
            # Track performance if analytics available
            start_time = time.time()
            
            # Get data for primary symbol
            df = ohlcv_data[primary_symbol].copy()
            
            # Add technical indicators
            trend_period = self.config['trend_period']
            volatility_period = self.config['volatility_period']
            rsi_period = self.config['rsi_period']
            rsi_divergence_lookback = self.config['rsi_divergence_lookback']
            ema_fast = self.config['ema_fast_period']
            ema_medium = self.config['ema_medium_period']
            ema_slow = self.config['ema_slow_period']
            bb_period = self.config['bb_period']
            bb_std_dev = self.config['bb_std_dev']
            
            # Calculate all needed indicators
            df = self.calculate_adx(df, period=trend_period)
            df = self.calculate_volatility(df, period=volatility_period)
            df = self.calculate_rsi(df, period=rsi_period)
            df = self.calculate_ema(df, fast_period=ema_fast, medium_period=ema_medium, slow_period=ema_slow)
            df = self.calculate_bollinger_bands(df, period=bb_period, std_dev=bb_std_dev)
            df = self.detect_rsi_divergence(df, lookback=rsi_divergence_lookback)
            
            # Get the most recent values
            latest = df.iloc[-1]
            
            # Extract key indicator values
            adx = latest.get('adx', 0)
            plus_di = latest.get('plus_di', 0)
            minus_di = latest.get('minus_di', 0)
            volatility_ratio = latest.get('volatility_ratio', 1.0)
            volatility_change = latest.get('volatility_change', 0)
            rsi = latest.get('rsi', 50)
            ema_alignment = latest.get('ema_alignment', 0)
            ema_cross = latest.get('ema_fast_medium_cross', 0)
            bb_width = latest.get('bb_width', 0)
            bb_squeeze = latest.get('bb_squeeze', False)
            bb_pct_b = latest.get('bb_pct_b', 0.5)
            bb_pct_from_middle = latest.get('bb_pct_from_middle', 0)
            bullish_divergence = latest.get('bullish_divergence', False)
            bearish_divergence = latest.get('bearish_divergence', False)
            
            # Determine trend direction and strength
            trend_direction = 1 if plus_di > minus_di else -1
            
            # Enhanced classification with multiple indicators
            # Initialize scores for different regimes
            regime_scores = {
                MarketRegime.STRONG_UPTREND: 0,
                MarketRegime.WEAK_UPTREND: 0,
                MarketRegime.RANGING: 0,
                MarketRegime.WEAK_DOWNTREND: 0,
                MarketRegime.STRONG_DOWNTREND: 0,
                MarketRegime.HIGH_VOLATILITY: 0,
                MarketRegime.LOW_VOLATILITY: 0,
                MarketRegime.REVERSAL_LIKELY: 0,
                MarketRegime.BREAKOUT_FORMING: 0
            }
            
            # Configuration thresholds
            strong_trend = self.config['strong_trend_threshold']
            weak_trend = self.config['weak_trend_threshold']
            high_vol = self.config['high_volatility_threshold']
            low_vol = self.config['low_volatility_threshold']
            rsi_overbought = self.config['rsi_overbought']
            rsi_oversold = self.config['rsi_oversold']
            bb_squeeze_threshold = self.config['bb_squeeze_threshold']
            transition_sensitivity = self.config['regime_transition_sensitivity']
            
            # ----- Score each regime based on indicator combinations -----
            
            # 1. Volatility regimes
            if volatility_ratio > high_vol:
                regime_scores[MarketRegime.HIGH_VOLATILITY] += min(10, volatility_ratio / high_vol * 7)
            elif volatility_ratio < low_vol:
                regime_scores[MarketRegime.LOW_VOLATILITY] += min(10, (1 - volatility_ratio/low_vol) * 7 + 3)
                
            # 2. Trend strength and direction from ADX and DI
            if adx > strong_trend:
                if trend_direction > 0:
                    regime_scores[MarketRegime.STRONG_UPTREND] += min(10, adx / strong_trend * 6)
                else:
                    regime_scores[MarketRegime.STRONG_DOWNTREND] += min(10, adx / strong_trend * 6)
            elif adx > weak_trend:
                if trend_direction > 0:
                    regime_scores[MarketRegime.WEAK_UPTREND] += min(8, adx / weak_trend * 5)
                else:
                    regime_scores[MarketRegime.WEAK_DOWNTREND] += min(8, adx / weak_trend * 5)
            else:
                regime_scores[MarketRegime.RANGING] += min(8, (weak_trend - adx) / weak_trend * 6 + 2)
                
            # 3. RSI extremes and divergences
            if rsi > rsi_overbought:
                regime_scores[MarketRegime.STRONG_UPTREND] += (rsi - rsi_overbought) / (100 - rsi_overbought) * 3
                # Potential reversal on extreme RSI
                if rsi > 80:
                    regime_scores[MarketRegime.REVERSAL_LIKELY] += (rsi - 80) / 20 * 4
            elif rsi < rsi_oversold:
                regime_scores[MarketRegime.STRONG_DOWNTREND] += (rsi_oversold - rsi) / rsi_oversold * 3
                # Potential reversal on extreme RSI
                if rsi < 20:
                    regime_scores[MarketRegime.REVERSAL_LIKELY] += (20 - rsi) / 20 * 4
                    
            # 4. RSI Divergence signals
            if bullish_divergence:
                regime_scores[MarketRegime.REVERSAL_LIKELY] += 8 # Strong signal for potential reversal
                # Reduce downtrend scores
                regime_scores[MarketRegime.STRONG_DOWNTREND] *= 0.7
                regime_scores[MarketRegime.WEAK_DOWNTREND] *= 0.7
            elif bearish_divergence:
                regime_scores[MarketRegime.REVERSAL_LIKELY] += 8 # Strong signal for potential reversal
                # Reduce uptrend scores
                regime_scores[MarketRegime.STRONG_UPTREND] *= 0.7
                regime_scores[MarketRegime.WEAK_UPTREND] *= 0.7
                
            # 5. EMA alignments and crosses
            if ema_alignment > 0:
                # Bullish alignment
                regime_scores[MarketRegime.STRONG_UPTREND] += 3
                regime_scores[MarketRegime.WEAK_UPTREND] += 2
            elif ema_alignment < 0:
                # Bearish alignment
                regime_scores[MarketRegime.STRONG_DOWNTREND] += 3
                regime_scores[MarketRegime.WEAK_DOWNTREND] += 2
                
            # Recent EMA crosses indicate potential regime changes
            if ema_cross > 0:  # Bullish cross
                regime_scores[MarketRegime.WEAK_UPTREND] += 4
                regime_scores[MarketRegime.REVERSAL_LIKELY] += 3
            elif ema_cross < 0:  # Bearish cross
                regime_scores[MarketRegime.WEAK_DOWNTREND] += 4
                regime_scores[MarketRegime.REVERSAL_LIKELY] += 3
                
            # 6. Bollinger Band signals
            # Narrow bands (squeeze) suggest breakout potential
            if bb_squeeze or bb_width < bb_squeeze_threshold:
                regime_scores[MarketRegime.BREAKOUT_FORMING] += min(8, (bb_squeeze_threshold - bb_width) / bb_squeeze_threshold * 10)
                
            # Position within bands
            if bb_pct_b > 0.95:  # Near upper band
                regime_scores[MarketRegime.STRONG_UPTREND] += 2
            elif bb_pct_b < 0.05:  # Near lower band
                regime_scores[MarketRegime.STRONG_DOWNTREND] += 2
                
            # Distance from middle band indicates trend strength
            if abs(bb_pct_from_middle) > 2.0:
                if bb_pct_from_middle > 0:
                    regime_scores[MarketRegime.STRONG_UPTREND] += min(3, bb_pct_from_middle / 2)
                else:
                    regime_scores[MarketRegime.STRONG_DOWNTREND] += min(3, abs(bb_pct_from_middle) / 2)
            else:
                regime_scores[MarketRegime.RANGING] += (2 - abs(bb_pct_from_middle)) / 2 * 2
                
            # Find the highest scoring regime
            max_score = 0
            detected_regime = MarketRegime.UNKNOWN
            
            for regime_type, score in regime_scores.items():
                if score > max_score:
                    max_score = score
                    detected_regime = regime_type
            
            # Calculate confidence based on score margin
            second_max = 0
            for regime_type, score in regime_scores.items():
                if score > second_max and regime_type != detected_regime:
                    second_max = score
            
            # Confidence based on margin and max possible score
            score_margin = max_score - second_max
            confidence = min(0.95, max_score / 10 * 0.7 + score_margin / 10 * 0.3)
            
            # Apply transition sensitivity - make it easier/harder to change regimes
            if detected_regime != self.current_regime:
                # Boost confidence if sensitivity is high, reduce if low
                confidence = confidence * transition_sensitivity + (1 - confidence) * (1 - transition_sensitivity)
            
            # Create analysis result
            result = {
                "timestamp": datetime.now().isoformat(),
                "regime": detected_regime,
                "previous_regime": self.current_regime,
                "confidence": confidence,
                "details": {
                    "primary_symbol": primary_symbol,
                    "adx": adx,
                    "trend_direction": trend_direction,
                    "volatility_ratio": volatility_ratio,
                    "rsi": rsi,
                    "ema_alignment": ema_alignment,
                    "bb_width": bb_width,
                    "regime_scores": {k.name: round(v, 2) for k, v in regime_scores.items()},
                    "bullish_divergence": bullish_divergence,
                    "bearish_divergence": bearish_divergence
                }
            }
            
            # Log performance metrics
            if ANALYTICS_AVAILABLE and analytics_logger:
                duration_ms = (time.time() - start_time) * 1000
                analytics_logger.log_performance(
                    operation="market_analysis",
                    duration_ms=duration_ms,
                    success=True,
                    metadata={"regime": regime.name, "confidence": confidence}
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing market data: {e}", exc_info=True)
            
            # Log performance failure
            if ANALYTICS_AVAILABLE and analytics_logger:
                duration_ms = (time.time() - start_time) * 1000
                analytics_logger.log_performance(
                    operation="market_analysis",
                    duration_ms=duration_ms,
                    success=False,
                    metadata={"error": str(e)}
                )
            
            return {
                "regime": MarketRegime.UNKNOWN,
                "confidence": 0.0,
                "details": {"error": str(e)}
            }
    
    def should_check_regime(self) -> bool:
        """
        Check if it's time to evaluate market regime
        
        Returns:
            True if regime check is due
        """
        now = datetime.now()
        check_interval = timedelta(minutes=self.config['regime_check_interval_minutes'])
        
        # Check if time since last check exceeds interval
        return (now - self.last_regime_check) >= check_interval
    
    def check_market_regime(self, ohlcv_data: Dict[str, pd.DataFrame],
                             primary_symbol: str = 'BTC/USDT',
                             force_check: bool = False) -> Optional[Dict[str, Any]]:
        """
        Check if market regime has changed and update parameter profile if needed
        
        Args:
            ohlcv_data: Dictionary of symbol -> OHLCV DataFrame
            primary_symbol: Primary symbol to use for market regime detection
            force_check: Force check regardless of time interval
            
        Returns:
            Market regime analysis result if changed, None if no change or check not performed
        """
        current_time = datetime.now()
        check_interval = timedelta(minutes=self.config['regime_check_interval_minutes'])
        
        # Skip check if not forced and not enough time has passed
        if not force_check and current_time - self.last_regime_check < check_interval:
            return None
            
        # Update last check time
        self.last_regime_check = current_time
        
        # Analyze market data
        analysis = self.analyze_market_data(ohlcv_data, primary_symbol)
        detected_regime = analysis['regime']
        confidence = analysis['confidence']
        
        # Apply confidence decay if manual override is not active
        if not self.manual_override_active:
            # Apply confidence decay for existing regime confidence
            if self.regime_confidence > 0:
                self.regime_confidence *= self.config['confidence_decay_rate']
            
            # Check for regime persistence (same regime detected multiple times)
            persistence_threshold = self.config['regime_persistence_threshold']
            
            # If detected regime matches the last detected one
            if detected_regime == self.last_detected_regime:
                self.regime_persistence_count += 1
                
                # Boost confidence based on persistence
                persistence_boost = min(0.1, self.regime_persistence_count / persistence_threshold * 0.1)
                confidence = min(0.95, confidence + persistence_boost)
            else:
                # Reset persistence for new regime
                self.regime_persistence_count = 1
                self.last_detected_regime = detected_regime
            
            # Only update current regime if we've seen it consistently enough times
            # or confidence is very high (for quick transitions on strong signals)
            regime_changed = False
            
            if detected_regime != self.current_regime and (
                (self.regime_persistence_count >= persistence_threshold and confidence >= 0.6) or 
                confidence > 0.85  # Allow quick transitions on very strong signals
            ):
                # Record previous regime
                prev_regime = self.current_regime
                
                # Update current regime
                self.current_regime = detected_regime
                self.regime_confidence = confidence
                regime_changed = True
                
                # Log the regime change
                logger.info(f"Market regime changed: {prev_regime.name} -> {detected_regime.name} (confidence: {confidence:.2f})")
                
                # Update parameter profile if adaptive switching is enabled
                if self.config['adaptive_profile_switch'] and PARAMETER_MANAGER_AVAILABLE and parameter_manager:
                    profile_id = MarketRegime.to_profile(detected_regime)
                    logger.info(f"Switching to parameter profile: {profile_id}")
                    parameter_manager.activate_profile(profile_id)
                    
                    # Run auto-backtest if enabled
                    if self.config['auto_backtest_on_regime_change'] and hasattr(parameter_manager, 'run_backtest'):
                        logger.info(f"Initiating auto-backtest for new regime: {detected_regime.name}")
                        try:
                            backtest_result = parameter_manager.run_backtest(days=14, profile_id=profile_id)
                            logger.info(f"Auto-backtest complete: {backtest_result}")
                        except Exception as e:
                            logger.error(f"Auto-backtest failed: {e}")
                
                # Add result to regime history
                self.regime_history.append({
                    "timestamp": current_time.isoformat(),
                    "regime": detected_regime.name,
                    "confidence": confidence,
                    "profile": MarketRegime.to_profile(detected_regime),
                    "transition_metrics": {
                        "persistence_count": self.regime_persistence_count,
                        "from_regime": prev_regime.name
                    }
                })
                
                # Trim history if it gets too long
                if len(self.regime_history) > 100:
                    self.regime_history = self.regime_history[-100:]
                    
                # Save regime history to file
                self._save_regime_history()
                
                # Log regime detection to dedicated logger for enhanced analysis
                if REGIME_LOGGER_AVAILABLE and regime_logger:
                    try:
                        regime_logger.log_regime_detection(
                            regime=detected_regime.name,
                            confidence=confidence,
                            metrics=analysis['details'],
                            previous_regime=prev_regime.name,
                            metadata={
                                "detected_by": "market_analyzer",
                                "persistence_count": self.regime_persistence_count,
                                "profile": MarketRegime.to_profile(detected_regime)
                            }
                        )
                        logger.info(f"Enhanced regime tracking: logged {detected_regime.name} to regime analysis system")
                    except Exception as e:
                        logger.error(f"Error logging regime to enhanced tracking system: {e}")
                
                # Send notification if enabled
                if self.config['notification_on_regime_change']:
                    self._send_regime_change_notification(prev_regime, detected_regime, confidence)
                    
                # Activate appropriate playbook for the new regime
                if PLAYBOOK_MANAGER_AVAILABLE and playbook_manager:
                    try:
                        # Format regime name for playbook lookup
                        # For example, convert MarketRegime.STRONG_UPTREND to "strong_uptrend"
                        regime_key = detected_regime.name.lower()
                        
                        # Add volatility suffix based on metrics
                        volatility = analysis['details'].get('volatility_ratio', 0)
                        volatility_threshold = self.config.get('high_volatility_threshold', 2.5)
                        
                        if volatility >= volatility_threshold:
                            regime_key = f"{regime_key}_high_volatility"
                        else:
                            regime_key = f"{regime_key}_low_volatility"
                        
                        # Activate playbook for this regime
                        playbook_result = playbook_manager.activate_playbook_for_regime(
                            regime_key, 
                            {
                                "detected_by": "market_analyzer",
                                "confidence": confidence,
                                "persistence_count": self.regime_persistence_count,
                                "metrics": analysis['details']
                            }
                        )
                        
                        # Log playbook activation result
                        if playbook_result["success"]:
                            logger.info(f"Activated playbook for regime '{regime_key}': {playbook_result['playbook']['strategy']}")
                        else:
                            logger.warning(f"Failed to activate playbook for regime '{regime_key}': {playbook_result['message']}")
                    except Exception as e:
                        logger.error(f"Error activating playbook for regime: {e}")
                
                # Log to analytics if available
                if ANALYTICS_AVAILABLE and analytics_logger and self.config['log_regime_changes']:
                    analytics_logger.log_event(
                        event_type="regime_change",
                        metadata={
                            "previous_regime": prev_regime.name,
                            "new_regime": detected_regime.name,
                            "confidence": confidence,
                            "persistence_count": self.regime_persistence_count,
                            "details": analysis['details']
                        }
                    )
                
                return analysis
            else:
                # No change in regime but update our confidence
                if detected_regime == self.current_regime:
                    self.regime_confidence = max(self.regime_confidence, confidence)
        
        # No change in regime or manual override active
        return None
    
    def _apply_regime_parameters(self, regime: MarketRegime, confidence: float) -> bool:
        """
        Apply parameter profile based on market regime
        
        Args:
            regime: Detected market regime
            confidence: Confidence level (0-1)
            
        Returns:
            True if profile applied successfully
        """
        if not PARAMETER_MANAGER_AVAILABLE or not parameter_manager:
            logger.warning("Parameter manager not available - cannot apply regime parameters")
            return False
            
        # Get profile name for regime
        profile_name = MarketRegime.to_profile(regime)
        
        # Only apply if confidence is reasonable
        if confidence < 0.5:
            logger.info(f"Low confidence ({confidence:.2f}) in regime detection - not changing parameters")
            return False
            
        # Apply profile
        reason = f"Market regime change to {regime.name} (confidence: {confidence:.2f})"
        success = parameter_manager.apply_profile(profile_name, reason=reason)
        
        if success:
            logger.info(f"Applied '{profile_name}' parameter profile for {regime.name} market")
            
            # Log to analytics
            if ANALYTICS_AVAILABLE and analytics_logger:
                analytics_logger.log_performance(
                    operation="regime_parameter_change",
                    duration_ms=0,
                    success=True,
                    metadata={
                        "regime": regime.name,
                        "profile": profile_name,
                        "confidence": confidence
                    }
                )
        else:
            logger.error(f"Failed to apply '{profile_name}' parameter profile")
            
        return success
    
    def _save_market_data(self) -> None:
        """Save market data to file"""
        market_data_file = os.path.join(self.base_dir, self.MARKET_DATA_FILE)
        
        try:
            data = {
                "current_regime": self.current_regime.name,
                "last_check": self.last_regime_check.isoformat(),
                "history": self.regime_history[-10:]  # Save last 10 entries
            }
            
            with open(market_data_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving market data: {e}", exc_info=True)
    
    def get_regime_history(self, limit: int = 10) -> List[Dict]:
        """Get recent market regime history
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of regime history entries
        """
        # Use enhanced regime tracking if available (for more detailed data)
        if REGIME_LOGGER_AVAILABLE and regime_logger:
            try:
                return regime_logger.get_recent_history(limit)
            except Exception as e:
                logger.warning(f"Error accessing enhanced regime history: {e}, falling back to basic history")
                
        # Fall back to basic history
        return self.regime_history[-limit:] if self.regime_history else []
    
    def get_current_regime(self) -> Dict:
        """Get current market regime information
        
        Returns:
            Dictionary with current regime information
        """
        return {
            "regime": self.current_regime.name,
            "last_updated": self.last_regime_check.isoformat(),
            "parameter_profile": MarketRegime.to_profile(self.current_regime) if PARAMETER_MANAGER_AVAILABLE else None
        }
    
    def backtest_regimes(self, historical_data: Dict[str, pd.DataFrame], 
                       primary_symbol: str = 'BTC/USDT') -> Dict[str, Any]:
        """
        Backtest market regime detection on historical data
        
        Args:
            historical_data: Dictionary of symbol -> historical OHLCV DataFrame
            primary_symbol: Primary symbol to use for market regime detection
            
        Returns:
            Dictionary with backtest results
        """
        if not historical_data or primary_symbol not in historical_data:
            logger.error(f"Primary symbol {primary_symbol} not found in historical data")
            return {
                "success": False,
                "error": f"Primary symbol {primary_symbol} not found"
            }
            
        try:
            # Get data for primary symbol
            df = historical_data[primary_symbol].copy()
            
            # Add technical indicators
            trend_period = self.config['trend_period']
            volatility_period = self.config['volatility_period']
            
            # Calculate ADX for trend strength
            df = self.calculate_adx(df, period=trend_period)
            
            # Calculate volatility metrics
            df = self.calculate_volatility(df, period=volatility_period)
            
            # Detect regime for each data point
            regimes = []
            for i in range(max(trend_period, volatility_period) * 2, len(df)):
                row = df.iloc[i]
                
                # Get indicator values
                adx = row.get('adx', 0)
                plus_di = row.get('plus_di', 0)
                minus_di = row.get('minus_di', 0)
                volatility_ratio = row.get('volatility_ratio', 1.0)
                
                # Determine trend direction
                trend_direction = 1 if plus_di > minus_di else -1
                
                # Classify market regime
                regime = MarketRegime.UNKNOWN
                confidence = 0.5  # Default confidence
                
                # Strong trend threshold
                strong_trend = self.config['strong_trend_threshold']
                weak_trend = self.config['weak_trend_threshold']
                
                # Volatility thresholds
                high_vol = self.config['high_volatility_threshold']
                low_vol = self.config['low_volatility_threshold']
                
                # Check for high volatility first (overrides trend)
                if volatility_ratio > high_vol:
                    regime = MarketRegime.HIGH_VOLATILITY
                # Check for low volatility
                elif volatility_ratio < low_vol:
                    regime = MarketRegime.LOW_VOLATILITY
                # Strong uptrend
                elif adx > strong_trend and trend_direction > 0:
                    regime = MarketRegime.STRONG_UPTREND
                # Strong downtrend
                elif adx > strong_trend and trend_direction < 0:
                    regime = MarketRegime.STRONG_DOWNTREND
                # Weak uptrend
                elif adx > weak_trend and trend_direction > 0:
                    regime = MarketRegime.WEAK_UPTREND
                # Weak downtrend
                elif adx > weak_trend and trend_direction < 0:
                    regime = MarketRegime.WEAK_DOWNTREND
                # Ranging market
                else:
                    regime = MarketRegime.RANGING
                
                # Add to results
                regimes.append({
                    "timestamp": df.index[i].isoformat(),
                    "regime": regime.name,
                    "adx": adx,
                    "trend_direction": trend_direction,
                    "volatility_ratio": volatility_ratio,
                    "close": row['close']
                })
            
            # Calculate regime statistics
            regime_stats = {}
            for regime in MarketRegime:
                regime_name = regime.name
                regime_count = sum(1 for r in regimes if r["regime"] == regime_name)
                regime_pct = regime_count / len(regimes) * 100 if regimes else 0
                
                regime_stats[regime_name] = {
                    "count": regime_count,
                    "percentage": regime_pct
                }
            
            # Calculate transitions between regimes
            transitions = {}
            prev_regime = None
            for r in regimes:
                curr_regime = r["regime"]
                if prev_regime is not None and prev_regime != curr_regime:
                    key = f"{prev_regime}->{curr_regime}"
                    transitions[key] = transitions.get(key, 0) + 1
                prev_regime = curr_regime
                
            return {
                "success": True,
                "total_periods": len(regimes),
                "regimes": regime_stats,
                "transitions": transitions,
                "regime_timeline": regimes
            }
            
        except Exception as e:
            logger.error(f"Error in backtest_regimes: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

# Singleton instance
market_analyzer = MarketAnalyzer()
