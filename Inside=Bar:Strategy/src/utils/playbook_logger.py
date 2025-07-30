#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Playbook Logger Module

Provides dedicated logging for playbook activations, transitions, and outcomes.
Maintains a historical record of which trading configurations were used for different
market regimes and their performance metrics.
"""

import os
import logging
import json
import csv
from typing import Dict, List, Any, Optional
from datetime import datetime
import threading

# Configure module logger
logger = logging.getLogger(__name__)

class PlaybookLogger:
    """
    Dedicated logger for playbook activations and outcomes
    """
    
    _instance = None
    _lock = threading.Lock()
    
    DATA_DIR = "data/playbooks"
    ACTIVATIONS_FILE = "playbook_activations.json"
    PERFORMANCE_FILE = "playbook_performance.csv"
    
    def __new__(cls):
        """Singleton implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(PlaybookLogger, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        """Initialize the playbook logger"""
        # Skip initialization if already done
        if getattr(self, '_initialized', False):
            return
            
        # Create data directory if it doesn't exist
        self.base_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            self.DATA_DIR
        )
        os.makedirs(self.base_dir, exist_ok=True)
        
        # Initialize state
        self.activations = self._load_activations()
        self.activation_count = len(self.activations)
        
        # Set initialization flag
        self._initialized = True
        logger.info("Playbook logger initialized with %d historical activations", 
                   self.activation_count)
    
    def _load_activations(self) -> List[Dict]:
        """
        Load playbook activations from file
        
        Returns:
            List of playbook activation records
        """
        activations_path = os.path.join(self.base_dir, self.ACTIVATIONS_FILE)
        
        # If file doesn't exist, start with empty list
        if not os.path.exists(activations_path):
            return []
            
        # Try to load existing file
        try:
            with open(activations_path, 'r') as f:
                activations = json.load(f)
                return activations if isinstance(activations, list) else []
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading playbook activations: {str(e)}")
            return []
    
    def _save_activations(self) -> bool:
        """
        Save playbook activations to file
        
        Returns:
            True if successful, False otherwise
        """
        activations_path = os.path.join(self.base_dir, self.ACTIVATIONS_FILE)
        
        try:
            with open(activations_path, 'w') as f:
                json.dump(self.activations, f, indent=2)
            return True
        except IOError as e:
            logger.error(f"Error saving playbook activations: {str(e)}")
            return False
    
    def log_activation(self, regime: str, playbook: Dict, metadata: Optional[Dict] = None) -> Dict:
        """
        Log a playbook activation
        
        Args:
            regime: Market regime name
            playbook: Playbook configuration
            metadata: Additional metadata about the activation
            
        Returns:
            Dict with activation record information
        """
        # Create activation record
        timestamp = datetime.now()
        activation_id = f"{timestamp.strftime('%Y%m%d%H%M%S')}-{self.activation_count + 1}"
        
        activation = {
            "id": activation_id,
            "timestamp": timestamp.isoformat(),
            "regime": regime,
            "playbook": playbook.copy() if playbook else {},
            "metadata": metadata or {}
        }
        
        # Add to activations list
        self.activations.append(activation)
        self.activation_count += 1
        
        # Keep list at reasonable size
        if len(self.activations) > 1000:
            self.activations = self.activations[-1000:]
            
        # Save to file
        self._save_activations()
        
        # Log the activation
        strategy = playbook.get('strategy', 'unknown') if playbook else 'none'
        logger.info(f"Logged playbook activation #{self.activation_count}: {regime} → {strategy}")
        
        return activation
    
    def log_trade_result(self, activation_id: str, trade_result: Dict) -> bool:
        """
        Log trade result for a specific playbook activation
        
        Args:
            activation_id: ID of the playbook activation
            trade_result: Trade result data
            
        Returns:
            True if successful, False otherwise
        """
        # Find the activation by ID
        for activation in self.activations:
            if activation["id"] == activation_id:
                # Add trade result to activation
                if "trade_results" not in activation:
                    activation["trade_results"] = []
                    
                trade_result["timestamp"] = datetime.now().isoformat()
                activation["trade_results"].append(trade_result)
                
                # Save updated activations
                self._save_activations()
                
                # Also log to CSV for easy analysis
                self._log_performance_to_csv(activation, trade_result)
                
                logger.info(f"Logged trade result for activation {activation_id}: {trade_result.get('outcome', 'unknown')}")
                return True
                
        logger.warning(f"Could not find activation with ID {activation_id} to log trade result")
        return False
    
    def _log_performance_to_csv(self, activation: Dict, trade_result: Dict) -> bool:
        """
        Log performance data to CSV file
        
        Args:
            activation: Playbook activation record
            trade_result: Trade result data
            
        Returns:
            True if successful, False otherwise
        """
        csv_path = os.path.join(self.base_dir, self.PERFORMANCE_FILE)
        file_exists = os.path.exists(csv_path)
        
        try:
            with open(csv_path, mode='a', newline='') as f:
                # Extract fields for CSV
                regime = activation.get("regime", "unknown")
                strategy = activation.get("playbook", {}).get("strategy", "unknown")
                risk_level = activation.get("playbook", {}).get("risk_level", "unknown")
                trade_type = trade_result.get("type", "unknown")
                outcome = trade_result.get("outcome", "unknown")
                profit_loss = trade_result.get("profit_loss", 0.0)
                leverage = activation.get("playbook", {}).get("leverage", 1)
                entry_type = activation.get("playbook", {}).get("entry_type", "unknown")
                symbol = trade_result.get("symbol", "unknown")
                
                # Create CSV writer
                fieldnames = ["timestamp", "activation_id", "regime", "strategy", 
                             "risk_level", "trade_type", "outcome", "profit_loss", 
                             "leverage", "entry_type", "symbol"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                    
                # Write record
                writer.writerow({
                    "timestamp": datetime.now().isoformat(),
                    "activation_id": activation.get("id", "unknown"),
                    "regime": regime,
                    "strategy": strategy,
                    "risk_level": risk_level,
                    "trade_type": trade_type,
                    "outcome": outcome,
                    "profit_loss": profit_loss,
                    "leverage": leverage,
                    "entry_type": entry_type,
                    "symbol": symbol
                })
                
            return True
        except (IOError, ValueError) as e:
            logger.error(f"Error logging to performance CSV: {str(e)}")
            return False
    
    def get_activation_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent playbook activations
        
        Args:
            limit: Maximum number of activations to return
            
        Returns:
            List of recent activation records
        """
        return self.activations[-limit:] if self.activations else []
    
    def get_performance_by_regime(self) -> Dict[str, Dict]:
        """
        Get performance statistics grouped by regime
        
        Returns:
            Dict of regime -> performance metrics
        """
        performance = {}
        
        # Process all activations with trade results
        for activation in self.activations:
            regime = activation.get("regime")
            if not regime or "trade_results" not in activation:
                continue
                
            # Initialize regime stats if needed
            if regime not in performance:
                performance[regime] = {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "total_profit_loss": 0.0,
                    "win_rate": 0.0,
                    "avg_profit_loss": 0.0
                }
                
            # Update stats with trade results
            for trade in activation["trade_results"]:
                performance[regime]["total_trades"] += 1
                profit_loss = trade.get("profit_loss", 0.0)
                performance[regime]["total_profit_loss"] += profit_loss
                
                if profit_loss > 0:
                    performance[regime]["winning_trades"] += 1
                elif profit_loss < 0:
                    performance[regime]["losing_trades"] += 1
                    
        # Calculate derived metrics
        for regime, stats in performance.items():
            if stats["total_trades"] > 0:
                stats["win_rate"] = stats["winning_trades"] / stats["total_trades"] * 100
                stats["avg_profit_loss"] = stats["total_profit_loss"] / stats["total_trades"]
                
        return performance
    
    def generate_performance_report(self) -> Dict:
        """
        Generate a comprehensive performance report for playbooks
        
        Returns:
            Dict with performance report data
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_activations": self.activation_count,
            "regime_performance": self.get_performance_by_regime(),
            "strategy_performance": {},
            "recent_activations": self.get_activation_history(5)
        }
        
        # Add strategy-specific performance
        strategy_performance = {}
        
        for activation in self.activations:
            if "trade_results" not in activation:
                continue
                
            strategy = activation.get("playbook", {}).get("strategy")
            if not strategy:
                continue
                
            # Initialize strategy stats if needed
            if strategy not in strategy_performance:
                strategy_performance[strategy] = {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "total_profit_loss": 0.0
                }
                
            # Update stats with trade results
            for trade in activation["trade_results"]:
                strategy_performance[strategy]["total_trades"] += 1
                profit_loss = trade.get("profit_loss", 0.0)
                strategy_performance[strategy]["total_profit_loss"] += profit_loss
                
                if profit_loss > 0:
                    strategy_performance[strategy]["winning_trades"] += 1
                elif profit_loss < 0:
                    strategy_performance[strategy]["losing_trades"] += 1
                    
        # Calculate derived metrics for strategies
        for strategy, stats in strategy_performance.items():
            if stats["total_trades"] > 0:
                stats["win_rate"] = stats["winning_trades"] / stats["total_trades"] * 100
                stats["avg_profit_loss"] = stats["total_profit_loss"] / stats["total_trades"]
                
        report["strategy_performance"] = strategy_performance
        
        return report


# Singleton instance
playbook_logger = PlaybookLogger()
