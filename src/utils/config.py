#!/usr/bin/env python3
"""
Configuration module for trading bot - centralizes all configurable parameters
"""

import os
import logging
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class BotConfig:
    """Central configuration management for the trading bot"""
    
    # Default configuration values
    DEFAULT_CONFIG = {
        # API Configuration
        "use_bidget_api": True,
        "use_fallback_api": False,
        
        # Trading Parameters
        "position_size_percent": 25.0,
        "max_signals_per_day": 15,
        "confidence_threshold": 95.0,
        "win_probability_threshold": 90.0,
        "min_risk_reward_ratio": 1.5,
        
        # Strategy Weights
        "supertrend_adx_weight": 50,
        "inside_bar_weight": 50,
        
        # Market Parameters
        "symbols": [
            "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT", 
            "ADA/USDT", "AVAX/USDT", "DOT/USDT", "DOGE/USDT", "MATIC/USDT"
        ],
        "timeframes": ["15m", "1h", "4h"],
        
        # Indicator Parameters
        "supertrend_period": 10,
        "supertrend_multiplier": 3,
        "adx_period": 14,
        "atr_period": 14,
        "adx_threshold": 25,
        
        # Technical Analysis Settings
        "ta_lookback_periods": 100,
        
        # Operation Parameters
        "scan_interval_seconds": 60,
        "daemon_check_interval": 60,
        "max_restart_failures": 3,
        
        # Paths
        "pid_file": "/tmp/trading_bot.pid",
        "log_level": "INFO",
        
        # Notification Settings
        "telegram_notification_enabled": True,
        "heartbeat_interval_hours": 1
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration with values from:
        1. Default config
        2. Environment variables
        3. Config file (if provided)
        """
        # Start with default config
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load environment variables
        load_dotenv()
        
        # Load config from file if provided
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                self.config.update(file_config)
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.error(f"Error loading config from {config_path}: {e}")
        
        # Override with environment variables if they exist
        self._load_from_env()
        
        # Log the final configuration (excluding sensitive values)
        self._log_config()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # API Configuration
        if os.getenv('USE_BIDGET_API'):
            self.config['use_bidget_api'] = os.getenv('USE_BIDGET_API').lower() == 'true'
        if os.getenv('USE_FALLBACK_API'):
            self.config['use_fallback_api'] = os.getenv('USE_FALLBACK_API').lower() == 'true'
            
        # Trading Parameters
        if os.getenv('POSITION_SIZE_PERCENT'):
            self.config['position_size_percent'] = float(os.getenv('POSITION_SIZE_PERCENT'))
        if os.getenv('MAX_SIGNALS_PER_DAY'):
            self.config['max_signals_per_day'] = int(os.getenv('MAX_SIGNALS_PER_DAY'))
        if os.getenv('CONFIDENCE_THRESHOLD'):
            self.config['confidence_threshold'] = float(os.getenv('CONFIDENCE_THRESHOLD'))
        if os.getenv('WIN_PROBABILITY_THRESHOLD'):
            self.config['win_probability_threshold'] = float(os.getenv('WIN_PROBABILITY_THRESHOLD'))
        if os.getenv('MIN_RISK_REWARD_RATIO'):
            self.config['min_risk_reward_ratio'] = float(os.getenv('MIN_RISK_REWARD_RATIO'))
            
        # Strategy Weights
        if os.getenv('SUPERTREND_ADX_WEIGHT'):
            self.config['supertrend_adx_weight'] = int(os.getenv('SUPERTREND_ADX_WEIGHT'))
        if os.getenv('INSIDE_BAR_WEIGHT'):
            self.config['inside_bar_weight'] = int(os.getenv('INSIDE_BAR_WEIGHT'))
        
    def _log_config(self):
        """Log the configuration (excluding sensitive values)"""
        safe_config = {k: v for k, v in self.config.items() if not k.lower().endswith(('key', 'secret', 'password', 'token'))}
        logger.info(f"Trading bot configuration: {json.dumps(safe_config, indent=2)}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value"""
        self.config[key] = value
    
    def save(self, config_path: str) -> bool:
        """Save the current configuration to a file"""
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Configuration saved to {config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config to {config_path}: {e}")
            return False
    
    @property
    def as_dict(self) -> Dict[str, Any]:
        """Return the entire configuration as a dictionary"""
        return self.config.copy()
    
# Global configuration instance
config = BotConfig()

def load_config(config_path: Optional[str] = None) -> BotConfig:
    """Load configuration from the given path"""
    global config
    config = BotConfig(config_path)
    return config
