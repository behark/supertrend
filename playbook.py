#!/usr/bin/env python3
"""
Playbook System for Bidget Auto Trading Bot
------------------------------------------
Maps market regimes to optimal trading strategies and parameters.
"""
import os
import json
import logging
from typing import Dict, Any, List, Optional, Union

# Configure logging
logger = logging.getLogger(__name__)

class Playbook:
    """
    Playbook system that maps market regimes to optimal trading strategies
    and their respective parameters.
    """
    
    def __init__(self, data_dir: str = 'data'):
        """Initialize the playbook system.
        
        Args:
            data_dir (str): Directory for data files
        """
        self.data_dir = data_dir
        self.playbook_file = os.path.join(data_dir, 'playbooks.json')
        self.playbooks = {}
        
        # Create data directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        # Load existing playbooks or create default
        if os.path.exists(self.playbook_file):
            self._load_playbooks()
        else:
            self._create_default_playbooks()
            self.save_playbooks()
            
        logger.info(f"Playbook system initialized with {len(self.playbooks)} regime playbooks")
    
    def _load_playbooks(self) -> None:
        """Load playbooks from JSON file."""
        try:
            with open(self.playbook_file, 'r') as f:
                self.playbooks = json.load(f)
            logger.info(f"Loaded playbooks from {self.playbook_file}")
        except Exception as e:
            logger.error(f"Error loading playbooks: {e}")
            self._create_default_playbooks()
    
    def _create_default_playbooks(self) -> None:
        """Create default playbooks for various market regimes."""
        self.playbooks = {
            "bullish_trend": {
                "strategy": "supertrend",
                "leverage": 3,
                "stop_loss": "atr_2.0",
                "take_profit": ["r1", "r2"],
                "entry_type": "breakout",
                "risk_level": "moderate",
                "filters": {
                    "min_volume": 1000000,
                    "min_volatility": 0.5
                }
            },
            "bullish_volatile": {
                "strategy": "supertrend",
                "leverage": 2,
                "stop_loss": "atr_2.5",
                "take_profit": ["r1", "r2", "r3"],
                "entry_type": "pullback",
                "risk_level": "moderate-high",
                "filters": {
                    "min_volume": 2000000,
                    "min_volatility": 1.0
                }
            },
            "bearish_trend": {
                "strategy": "supertrend",
                "leverage": 2,
                "stop_loss": "atr_2.0",
                "take_profit": ["s1", "s2"],
                "entry_type": "breakout",
                "risk_level": "moderate",
                "filters": {
                    "min_volume": 1500000,
                    "min_volatility": 0.5
                }
            },
            "bearish_volatile": {
                "strategy": "supertrend",
                "leverage": 1.5,
                "stop_loss": "atr_2.5",
                "take_profit": ["s1", "s2", "s3"],
                "entry_type": "pullback",
                "risk_level": "moderate-high",
                "filters": {
                    "min_volume": 2500000,
                    "min_volatility": 1.2
                }
            },
            "ranging": {
                "strategy": "inside_bar",
                "leverage": 2,
                "stop_loss": "range_boundary",
                "take_profit": ["range_opposite"],
                "entry_type": "range_touch",
                "risk_level": "low",
                "filters": {
                    "min_volume": 800000,
                    "max_volatility": 0.8
                }
            },
            "ranging_breakout": {
                "strategy": "inside_bar",
                "leverage": 3,
                "stop_loss": "range_return",
                "take_profit": ["fib_1.27", "fib_1.62"],
                "entry_type": "breakout",
                "risk_level": "moderate",
                "filters": {
                    "min_volume": 1200000,
                    "min_volatility": 0.4
                }
            },
            "reversal": {
                "strategy": "inside_bar",
                "leverage": 2,
                "stop_loss": "swing_high_low",
                "take_profit": ["fib_0.5", "fib_0.618"],
                "entry_type": "counter_trend",
                "risk_level": "high",
                "filters": {
                    "min_volume": 2000000,
                    "min_volatility": 0.6,
                    "rsi_extreme": True
                }
            },
            "volatile": {
                "strategy": "supertrend",
                "leverage": 1.5,
                "stop_loss": "atr_3.0",
                "take_profit": ["atr_6.0"],
                "entry_type": "momentum",
                "risk_level": "high",
                "filters": {
                    "min_volume": 3000000,
                    "min_volatility": 1.5
                }
            },
            "calm": {
                "strategy": "inside_bar",
                "leverage": 3,
                "stop_loss": "atr_1.5",
                "take_profit": ["atr_4.5"],
                "entry_type": "breakout",
                "risk_level": "low",
                "filters": {
                    "min_volume": 500000,
                    "max_volatility": 0.4
                }
            }
        }
    
    def save_playbooks(self) -> None:
        """Save playbooks to JSON file."""
        try:
            with open(self.playbook_file, 'w') as f:
                json.dump(self.playbooks, f, indent=2)
            logger.info(f"Saved playbooks to {self.playbook_file}")
        except Exception as e:
            logger.error(f"Error saving playbooks: {e}")
    
    def get_playbook(self, regime: str) -> Dict[str, Any]:
        """Get playbook for a specific market regime.
        
        Args:
            regime (str): Market regime name
            
        Returns:
            dict: Playbook parameters for the regime or default playbook
        """
        if regime in self.playbooks:
            logger.debug(f"Found playbook for regime: {regime}")
            return self.playbooks[regime]
        else:
            # If no specific playbook is found, use a default one
            logger.warning(f"No playbook found for regime: {regime}, using default")
            if "ranging" in self.playbooks:  # Using ranging as default as it's moderate
                return self.playbooks["ranging"]
            else:
                # Fallback to first available playbook
                return list(self.playbooks.values())[0] if self.playbooks else {}
    
    def add_playbook(self, regime: str, playbook_params: Dict[str, Any]) -> None:
        """Add or update a playbook for a specific regime.
        
        Args:
            regime (str): Market regime name
            playbook_params (dict): Playbook parameters
        """
        self.playbooks[regime] = playbook_params
        logger.info(f"Added/updated playbook for regime: {regime}")
        self.save_playbooks()
    
    def delete_playbook(self, regime: str) -> bool:
        """Delete a playbook for a specific regime.
        
        Args:
            regime (str): Market regime name
            
        Returns:
            bool: True if playbook was deleted, False otherwise
        """
        if regime in self.playbooks:
            del self.playbooks[regime]
            logger.info(f"Deleted playbook for regime: {regime}")
            self.save_playbooks()
            return True
        return False
    
    def list_playbooks(self) -> Dict[str, Dict[str, Any]]:
        """List all available playbooks.
        
        Returns:
            dict: All playbooks
        """
        return self.playbooks
    
    def get_strategy_params(self, regime: str) -> Dict[str, Any]:
        """Get strategy parameters for a specific regime.
        
        Args:
            regime (str): Market regime name
            
        Returns:
            dict: Strategy parameters for the regime
        """
        playbook = self.get_playbook(regime)
        return {
            "strategy": playbook.get("strategy", "supertrend"),
            "leverage": playbook.get("leverage", 1),
            "entry_type": playbook.get("entry_type", "breakout")
        }
    
    def get_risk_params(self, regime: str) -> Dict[str, Any]:
        """Get risk parameters for a specific regime.
        
        Args:
            regime (str): Market regime name
            
        Returns:
            dict: Risk parameters for the regime
        """
        playbook = self.get_playbook(regime)
        return {
            "stop_loss": playbook.get("stop_loss", "atr_2.0"),
            "take_profit": playbook.get("take_profit", ["r1"]),
            "risk_level": playbook.get("risk_level", "moderate")
        }
    
    def get_filter_params(self, regime: str) -> Dict[str, Any]:
        """Get filter parameters for a specific regime.
        
        Args:
            regime (str): Market regime name
            
        Returns:
            dict: Filter parameters for the regime
        """
        playbook = self.get_playbook(regime)
        return playbook.get("filters", {})


if __name__ == "__main__":
    # Setup basic logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and test playbook system
    playbook_system = Playbook()
    print("Available playbooks:")
    for regime, params in playbook_system.list_playbooks().items():
        print(f"  - {regime}: {params['strategy']} (leverage: {params['leverage']})")
