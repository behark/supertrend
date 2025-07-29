#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Playbook Manager Module

Manages strategy playbooks that map market regimes to specific trading configurations.
Each playbook contains regime-specific settings for strategy selection, leverage, 
entry types, stop loss, take profit targets, and risk levels.
"""

import os
import json
import logging
import threading
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from enum import Enum, auto

# Configure module logger
logger = logging.getLogger(__name__)

# Try to import market analyzer for regime detection integration
try:
    from src.utils.market_analyzer import market_analyzer, MarketRegime
    MARKET_ANALYZER_AVAILABLE = True
except ImportError:
    MARKET_ANALYZER_AVAILABLE = False
    logger.warning("Market analyzer not available - automatic regime detection disabled")

# Try to import analytics logger for performance tracking
try:
    from src.utils.analytics_logger import analytics_logger
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    logger.warning("Analytics logger not available - playbook logging features limited")

# Try to import playbook logger for activation tracking and performance analysis
try:
    from src.utils.playbook_logger import playbook_logger
    PLAYBOOK_LOGGER_AVAILABLE = True
except ImportError:
    PLAYBOOK_LOGGER_AVAILABLE = False
    logger.warning("Playbook logger not available - activation history will be limited")


class PlaybookManager:
    """
    Manages strategy playbooks that map market regimes to trading configurations
    """
    
    _instance = None
    _lock = threading.Lock()
    
    CONFIG_DIR = "config"
    PLAYBOOK_FILE = "playbooks.json"
    
    DEFAULT_PLAYBOOK = {
        # Strong uptrend with low volatility
        "strong_uptrend_low_volatility": {
            "strategy": "supertrend_adx",
            "leverage": 3,
            "entry_type": "breakout",
            "stop_loss": "atr_1.5",
            "take_profit": ["r1", "r2"],
            "risk_level": "medium"
        },
        # Strong uptrend with high volatility
        "strong_uptrend_high_volatility": {
            "strategy": "supertrend_adx",
            "leverage": 2,
            "entry_type": "pullback",
            "stop_loss": "atr_2.0",
            "take_profit": ["r1"],
            "risk_level": "medium"
        },
        # Weak uptrend with low volatility
        "weak_uptrend_low_volatility": {
            "strategy": "inside_bar",
            "leverage": 2,
            "entry_type": "breakout",
            "stop_loss": "atr_1.0",
            "take_profit": ["r1", "r2", "r3"],
            "risk_level": "low"
        },
        # Weak uptrend with high volatility
        "weak_uptrend_high_volatility": {
            "strategy": "inside_bar",
            "leverage": 1,
            "entry_type": "pullback",
            "stop_loss": "atr_1.5",
            "take_profit": ["r1"],
            "risk_level": "low"
        },
        # Range-bound with low volatility
        "sideways_low_volatility": {
            "strategy": "inside_bar",
            "leverage": 1,
            "entry_type": "range_bound",
            "stop_loss": "atr_1.0",
            "take_profit": ["range_top"],
            "risk_level": "low"
        },
        # Range-bound with high volatility
        "sideways_high_volatility": {
            "strategy": "inside_bar",
            "leverage": 1,
            "entry_type": "range_bound",
            "stop_loss": "atr_1.0",
            "take_profit": ["range_top"],
            "risk_level": "low"
        },
        # Strong downtrend with low volatility
        "strong_downtrend_low_volatility": {
            "strategy": "supertrend_adx",
            "leverage": 3,
            "entry_type": "breakout",
            "stop_loss": "atr_1.5",
            "take_profit": ["r1", "r2"],
            "risk_level": "medium"
        },
        # Strong downtrend with high volatility
        "strong_downtrend_high_volatility": {
            "strategy": "supertrend_adx",
            "leverage": 2,
            "entry_type": "pullback",
            "stop_loss": "atr_2.0",
            "take_profit": ["r1"],
            "risk_level": "high"
        },
        # Weak downtrend with low volatility
        "weak_downtrend_low_volatility": {
            "strategy": "inside_bar",
            "leverage": 2,
            "entry_type": "breakout",
            "stop_loss": "atr_1.0",
            "take_profit": ["r1", "r2"],
            "risk_level": "low"
        },
        # Weak downtrend with high volatility
        "weak_downtrend_high_volatility": {
            "strategy": "inside_bar",
            "leverage": 1,
            "entry_type": "pullback",
            "stop_loss": "atr_1.5",
            "take_profit": ["r1"],
            "risk_level": "medium"
        },
        # Unknown or transitioning market (fallback/default)
        "unknown": {
            "strategy": "inside_bar",
            "leverage": 1,
            "entry_type": "confirmation",
            "stop_loss": "atr_1.0",
            "take_profit": ["r1"],
            "risk_level": "low"
        }
    }
    
    def __new__(cls):
        """Singleton implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(PlaybookManager, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        """Initialize the playbook manager"""
        # Skip initialization if already done
        if getattr(self, '_initialized', False):
            return
            
        # Create config directory if it doesn't exist
        self.base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            self.CONFIG_DIR
        )
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Initialize state
        self.playbooks = self._load_playbooks()
        self.active_playbook = None
        self.active_regime = None
        self.activation_history = []
        
        # Set initialization flag
        self._initialized = True
        logger.info("Playbook manager initialized with %d regime configurations", 
                    len(self.playbooks))
    
    def _load_playbooks(self) -> Dict[str, Dict]:
        """
        Load playbook configurations from file
        
        Returns:
            Dictionary of playbook configurations
        """
        playbook_path = os.path.join(self.base_dir, self.PLAYBOOK_FILE)
        
        # If playbook file doesn't exist, create with default values
        if not os.path.exists(playbook_path):
            logger.info("Creating default playbook configuration")
            playbooks = self.DEFAULT_PLAYBOOK
            self._save_playbooks(playbooks)
            return playbooks
            
        # Try to load existing playbook file
        try:
            with open(playbook_path, 'r') as f:
                playbooks = json.load(f)
                logger.info("Loaded playbook configuration with %d regimes", len(playbooks))
                return playbooks
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading playbooks from {playbook_path}: {str(e)}")
            logger.info("Falling back to default playbook configuration")
            return self.DEFAULT_PLAYBOOK.copy()
    
    def _save_playbooks(self, playbooks: Dict[str, Dict]) -> bool:
        """
        Save playbook configurations to file
        
        Args:
            playbooks: Dictionary of playbook configurations
            
        Returns:
            True if successful, False otherwise
        """
        playbook_path = os.path.join(self.base_dir, self.PLAYBOOK_FILE)
        
        try:
            with open(playbook_path, 'w') as f:
                json.dump(playbooks, f, indent=4)
            logger.info("Saved playbook configuration to %s", playbook_path)
            return True
        except IOError as e:
            logger.error(f"Error saving playbooks to {playbook_path}: {str(e)}")
            return False
    
    def get_playbook_for_regime(self, regime_name: str) -> Optional[Dict]:
        """
        Get playbook configuration for a specific regime
        
        Args:
            regime_name: Name of the market regime
            
        Returns:
            Playbook configuration dictionary or None if not found
        """
        # Normalize regime name for lookup
        regime_key = regime_name.lower().replace(' ', '_')
        
        # Return playbook if found, otherwise return default/unknown
        if regime_key in self.playbooks:
            return self.playbooks[regime_key]
        elif "unknown" in self.playbooks:
            logger.warning(f"No playbook found for regime '{regime_name}', using default")
            return self.playbooks["unknown"]
        else:
            logger.error(f"No playbook found for regime '{regime_name}' and no default available")
            return None
    
    def activate_playbook_for_regime(self, regime_name: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Activate playbook for a specific market regime
        
        Args:
            regime_name: Name of the market regime
            metadata: Additional metadata about the regime activation
            
        Returns:
            Dictionary with activation result
        """
        playbook = self.get_playbook_for_regime(regime_name)
        
        if not playbook:
            logger.error(f"Failed to activate playbook for regime '{regime_name}'")
            return {
                "success": False,
                "message": f"No playbook found for regime '{regime_name}'"
            }
            
        # Update active state
        self.active_playbook = playbook
        self.active_regime = regime_name
        
        # Record activation in history
        activation_record = {
            "timestamp": datetime.now().isoformat(),
            "regime": regime_name,
            "playbook": playbook.copy(),
            "metadata": metadata or {}
        }
        self.activation_history.append(activation_record)
        
        # Keep history at reasonable size
        if len(self.activation_history) > 100:
            self.activation_history = self.activation_history[-100:]
        
        # Log activation
        logger.info(f"Activated playbook for regime '{regime_name}' with strategy '{playbook['strategy']}'")
        
        # Log to playbook logger for detailed tracking and performance analysis
        if PLAYBOOK_LOGGER_AVAILABLE and playbook_logger:
            try:
                log_result = playbook_logger.log_activation(
                    regime=regime_name,
                    playbook=playbook,
                    metadata={
                        **(metadata or {}),
                        "activation_source": "playbook_manager",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                activation_record["log_id"] = log_result.get("id")
                logger.info(f"Logged playbook activation with ID: {log_result.get('id')}")
            except Exception as e:
                logger.error(f"Error logging to playbook logger: {str(e)}")
        
        # Log to analytics if available
        if ANALYTICS_AVAILABLE and analytics_logger:
            try:
                analytics_logger.log_event(
                    event_type="playbook_activated",
                    metadata={
                        "category": "playbook",
                        "regime": regime_name,
                        "strategy": playbook.get("strategy"),
                        "risk_level": playbook.get("risk_level")
                    }
                )
            except Exception as e:
                logger.error(f"Error logging playbook activation to analytics: {str(e)}")
        
        return {
            "success": True,
            "regime": regime_name,
            "playbook": playbook,
            "message": f"Playbook activated for regime '{regime_name}'"
        }
    
    def get_active_playbook(self) -> Dict:
        """
        Get currently active playbook
        
        Returns:
            Dictionary with active playbook information
        """
        return {
            "active_regime": self.active_regime,
            "playbook": self.active_playbook,
            "activated_at": self.activation_history[-1]["timestamp"] if self.activation_history else None
        }
    
    def update_playbook_config(self, regime_name: str, config_updates: Dict) -> bool:
        """
        Update playbook configuration for a specific regime
        
        Args:
            regime_name: Name of the market regime
            config_updates: Dictionary of configuration updates
            
        Returns:
            True if successful, False otherwise
        """
        # Normalize regime name for lookup
        regime_key = regime_name.lower().replace(' ', '_')
        
        # Create new regime if it doesn't exist
        if regime_key not in self.playbooks:
            self.playbooks[regime_key] = {}
            
        # Update configuration
        for key, value in config_updates.items():
            self.playbooks[regime_key][key] = value
            
        # Save updated playbooks
        success = self._save_playbooks(self.playbooks)
        
        if success:
            logger.info(f"Updated playbook configuration for regime '{regime_name}'")
            
            # If this regime is currently active, update active playbook
            if self.active_regime == regime_name:
                self.active_playbook = self.playbooks[regime_key]
                logger.info(f"Updated active playbook for regime '{regime_name}'")
        
        return success
    
    def delete_playbook_config(self, regime_name: str) -> bool:
        """
        Delete playbook configuration for a specific regime
        
        Args:
            regime_name: Name of the market regime
            
        Returns:
            True if successful, False otherwise
        """
        # Normalize regime name for lookup
        regime_key = regime_name.lower().replace(' ', '_')
        
        # Check if regime exists
        if regime_key not in self.playbooks:
            logger.warning(f"Cannot delete non-existent playbook for regime '{regime_name}'")
            return False
            
        # Prevent deletion of the default/unknown playbook
        if regime_key == "unknown":
            logger.warning("Cannot delete the default playbook")
            return False
            
        # Delete playbook
        del self.playbooks[regime_key]
        
        # Save updated playbooks
        success = self._save_playbooks(self.playbooks)
        
        if success:
            logger.info(f"Deleted playbook configuration for regime '{regime_name}'")
            
            # If this regime is currently active, reset active playbook
            if self.active_regime == regime_name:
                self.active_playbook = None
                self.active_regime = None
                logger.info("Reset active playbook after deletion")
        
        return success
    
    def reset_to_defaults(self) -> bool:
        """
        Reset all playbooks to default values
        
        Returns:
            True if successful, False otherwise
        """
        self.playbooks = self.DEFAULT_PLAYBOOK.copy()
        success = self._save_playbooks(self.playbooks)
        
        if success:
            logger.info("Reset all playbooks to default values")
            
            # Reset active playbook if set
            if self.active_regime:
                self.active_playbook = self.get_playbook_for_regime(self.active_regime)
        
        return success
    
    def get_recent_activations(self, limit: int = 5) -> List[Dict]:
        """
        Get recent playbook activations
        
        Args:
            limit: Maximum number of recent activations to return
            
        Returns:
            List of activation records
        """
        return self.activation_history[-limit:] if self.activation_history else []
    
    def sync_with_market_analyzer(self) -> Dict:
        """
        Synchronize playbooks with current market regime from analyzer
        
        Returns:
            Result of synchronization attempt
        """
        if not MARKET_ANALYZER_AVAILABLE or not market_analyzer:
            return {
                "success": False,
                "message": "Market analyzer not available"
            }
            
        try:
            # Get current regime from market analyzer
            regime_data = market_analyzer.get_current_regime()
            regime_name = regime_data.get("regime")
            
            if not regime_name:
                return {
                    "success": False,
                    "message": "No current regime available from market analyzer"
                }
                
            # Convert regime enum to string if needed
            if not isinstance(regime_name, str):
                regime_name = str(regime_name).replace("MarketRegime.", "").lower()
                
            # Add volatility suffix based on metrics
            metrics = regime_data.get("metrics", {})
            volatility = metrics.get("volatility", 0)
            volatility_threshold = market_analyzer.config.get("high_volatility_threshold", 2.5)
            
            if volatility >= volatility_threshold:
                regime_name = f"{regime_name}_high_volatility"
            else:
                regime_name = f"{regime_name}_low_volatility"
                
            # Activate playbook for detected regime
            result = self.activate_playbook_for_regime(regime_name, {
                "detected_by": "market_analyzer",
                "confidence": regime_data.get("confidence", 0),
                "metrics": metrics
            })
            
            return result
        except Exception as e:
            logger.error(f"Error synchronizing with market analyzer: {str(e)}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }


# Singleton instance
playbook_manager = PlaybookManager()
