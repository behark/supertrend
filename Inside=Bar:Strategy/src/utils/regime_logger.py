#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Regime Logger Module

Provides dedicated logging for market regime detection, transitions, and metrics.
Maintains a historical record of detected regimes with detailed metrics and
transition patterns for analysis and visualization.
"""

import os
import logging
import json
import csv
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
import threading
import pandas as pd
import numpy as np
from enum import Enum

# Configure module logger
logger = logging.getLogger(__name__)

class RegimeLogger:
    """
    Dedicated logger for market regime detection and analysis
    """
    
    _instance = None
    _lock = threading.Lock()
    
    DATA_DIR = "data/regimes"
    REGIMES_FILE = "regime_history.json"
    METRICS_FILE = "regime_metrics.csv"
    TRANSITIONS_FILE = "regime_transitions.csv"
    
    def __new__(cls):
        """Singleton implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(RegimeLogger, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        """Initialize the regime logger"""
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
        self.regime_history = self._load_regime_history()
        self.regime_count = len(self.regime_history)
        
        # Generate statistics on initialization
        self._update_statistics()
        
        # Set initialization flag
        self._initialized = True
        logger.info("Regime logger initialized with %d historical regime records", 
                   self.regime_count)
    
    def _load_regime_history(self) -> List[Dict]:
        """
        Load regime history from file
        
        Returns:
            List of regime records
        """
        history_path = os.path.join(self.base_dir, self.REGIMES_FILE)
        
        # If file doesn't exist, start with empty list
        if not os.path.exists(history_path):
            return []
            
        # Try to load existing file
        try:
            with open(history_path, 'r') as f:
                history = json.load(f)
                return history if isinstance(history, list) else []
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading regime history: {str(e)}")
            return []
    
    def _save_regime_history(self) -> bool:
        """
        Save regime history to file
        
        Returns:
            True if successful, False otherwise
        """
        history_path = os.path.join(self.base_dir, self.REGIMES_FILE)
        
        try:
            with open(history_path, 'w') as f:
                json.dump(self.regime_history, f, indent=2)
            return True
        except IOError as e:
            logger.error(f"Error saving regime history: {str(e)}")
            return False
    
    def log_regime_detection(self, regime: str, confidence: float, metrics: Dict, 
                           previous_regime: Optional[str] = None,
                           metadata: Optional[Dict] = None) -> Dict:
        """
        Log a regime detection event
        
        Args:
            regime: Detected market regime name
            confidence: Confidence level (0-1)
            metrics: Regime detection metrics (adx, volatility, etc.)
            previous_regime: Previous regime if this is a transition
            metadata: Additional metadata about the detection
            
        Returns:
            Dict with detection record information
        """
        # Create detection record
        timestamp = datetime.now()
        detection_id = f"{timestamp.strftime('%Y%m%d%H%M%S')}-{self.regime_count + 1}"
        
        detection = {
            "id": detection_id,
            "timestamp": timestamp.isoformat(),
            "regime": regime,
            "confidence": confidence,
            "previous_regime": previous_regime,
            "metrics": metrics.copy() if metrics else {},
            "metadata": metadata or {}
        }
        
        # Add to history list
        self.regime_history.append(detection)
        self.regime_count += 1
        
        # Keep list at reasonable size
        if len(self.regime_history) > 1000:
            self.regime_history = self.regime_history[-1000:]
            
        # Save to file
        self._save_regime_history()
        
        # Log the detection
        if previous_regime:
            logger.info(f"Logged regime transition: {previous_regime} → {regime} (confidence: {confidence:.2f})")
            # Also log to transitions CSV for analysis
            self._log_transition_to_csv(previous_regime, regime, confidence, timestamp)
        else:
            logger.info(f"Logged regime detection: {regime} (confidence: {confidence:.2f})")
            
        # Log metrics to CSV for time-series analysis
        self._log_metrics_to_csv(regime, confidence, metrics, timestamp)
        
        # Update statistics
        self._update_statistics()
        
        return detection
    
    def _log_metrics_to_csv(self, regime: str, confidence: float, metrics: Dict, 
                           timestamp: datetime) -> bool:
        """
        Log regime metrics to CSV file for time-series analysis
        
        Args:
            regime: Detected regime name
            confidence: Confidence level
            metrics: Regime detection metrics
            timestamp: Detection timestamp
            
        Returns:
            True if successful, False otherwise
        """
        csv_path = os.path.join(self.base_dir, self.METRICS_FILE)
        file_exists = os.path.exists(csv_path)
        
        try:
            with open(csv_path, mode='a', newline='') as f:
                # Flatten metrics for CSV
                flat_metrics = {}
                for k, v in metrics.items():
                    if isinstance(v, dict):
                        for sub_k, sub_v in v.items():
                            flat_metrics[f"{k}_{sub_k}"] = sub_v
                    else:
                        flat_metrics[k] = v
                
                # Extract standard fields that we always want
                standard_fields = {
                    "timestamp": timestamp.isoformat(),
                    "regime": regime,
                    "confidence": confidence,
                    "adx": flat_metrics.get("adx", 0),
                    "volatility": flat_metrics.get("volatility_ratio", 0),
                    "trend_direction": flat_metrics.get("trend_direction", 0),
                    "rsi": flat_metrics.get("rsi", 50),
                }
                
                # Determine all fields for header
                all_fields = list(standard_fields.keys())
                for k in flat_metrics.keys():
                    if k not in all_fields:
                        all_fields.append(k)
                        
                writer = csv.DictWriter(f, fieldnames=all_fields)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                    
                # Combine standard fields with any additional metrics
                row_data = {**standard_fields, **flat_metrics}
                
                # Write record
                writer.writerow(row_data)
                
            return True
        except (IOError, ValueError) as e:
            logger.error(f"Error logging to metrics CSV: {str(e)}")
            return False
    
    def _log_transition_to_csv(self, from_regime: str, to_regime: str, 
                              confidence: float, timestamp: datetime) -> bool:
        """
        Log regime transition to CSV file for pattern analysis
        
        Args:
            from_regime: Previous regime name
            to_regime: New regime name
            confidence: Confidence level
            timestamp: Transition timestamp
            
        Returns:
            True if successful, False otherwise
        """
        csv_path = os.path.join(self.base_dir, self.TRANSITIONS_FILE)
        file_exists = os.path.exists(csv_path)
        
        try:
            with open(csv_path, mode='a', newline='') as f:
                fieldnames = ["timestamp", "from_regime", "to_regime", "confidence", 
                             "duration_hours", "transition_type"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                
                # Write header if file is new
                if not file_exists:
                    writer.writeheader()
                
                # Calculate duration if we have previous records
                duration_hours = 0
                transition_type = "unknown"
                
                # Find last occurrence of from_regime
                for i in range(len(self.regime_history) - 2, -1, -1):
                    if self.regime_history[i]["regime"] == from_regime:
                        # Calculate duration
                        prev_time = datetime.fromisoformat(self.regime_history[i]["timestamp"])
                        duration_hours = (timestamp - prev_time).total_seconds() / 3600
                        
                        # Classify transition type
                        if "strong_uptrend" in to_regime and "weak" in from_regime:
                            transition_type = "strengthening_uptrend"
                        elif "strong_downtrend" in to_regime and "weak" in from_regime:
                            transition_type = "strengthening_downtrend"
                        elif "weak_uptrend" in to_regime and "strong" in from_regime:
                            transition_type = "weakening_uptrend"
                        elif "weak_downtrend" in to_regime and "strong" in from_regime:
                            transition_type = "weakening_downtrend"
                        elif "reversal" in to_regime:
                            transition_type = "reversal"
                        elif "ranging" in to_regime:
                            transition_type = "consolidation"
                        elif "breakout" in to_regime:
                            transition_type = "breakout"
                        break
                
                # Write record
                writer.writerow({
                    "timestamp": timestamp.isoformat(),
                    "from_regime": from_regime,
                    "to_regime": to_regime,
                    "confidence": confidence,
                    "duration_hours": duration_hours,
                    "transition_type": transition_type
                })
                
            return True
        except (IOError, ValueError) as e:
            logger.error(f"Error logging to transitions CSV: {str(e)}")
            return False
    
    def _update_statistics(self) -> None:
        """Update regime statistics"""
        # Skip if no history
        if not self.regime_history:
            self.statistics = {}
            return
            
        # Initialize statistics
        stats = {
            "last_updated": datetime.now().isoformat(),
            "total_regimes_detected": self.regime_count,
            "regime_distribution": {},
            "avg_regime_confidence": 0,
            "avg_regime_duration_hours": 0,
            "common_transitions": {},
            "volatility_by_regime": {}
        }
        
        # Calculate regime distribution
        regime_counts = {}
        total_confidence = 0
        
        for record in self.regime_history:
            regime = record["regime"]
            confidence = record.get("confidence", 0)
            
            # Update counts
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
            total_confidence += confidence
            
            # Track volatility by regime
            volatility = record.get("metrics", {}).get("volatility_ratio", 0)
            if regime not in stats["volatility_by_regime"]:
                stats["volatility_by_regime"][regime] = []
            stats["volatility_by_regime"][regime].append(volatility)
        
        # Calculate percentages
        for regime, count in regime_counts.items():
            stats["regime_distribution"][regime] = {
                "count": count,
                "percentage": count / self.regime_count * 100
            }
            
        # Calculate average confidence
        stats["avg_regime_confidence"] = total_confidence / self.regime_count if self.regime_count > 0 else 0
        
        # Calculate regime durations and transitions
        transitions = {}
        durations = []
        
        for i in range(1, len(self.regime_history)):
            current = self.regime_history[i]
            previous = self.regime_history[i-1]
            
            # Only count if different regimes (transitions)
            if current["regime"] != previous["regime"]:
                transition_key = f"{previous['regime']} → {current['regime']}"
                transitions[transition_key] = transitions.get(transition_key, 0) + 1
                
                # Calculate duration
                current_time = datetime.fromisoformat(current["timestamp"])
                previous_time = datetime.fromisoformat(previous["timestamp"])
                duration_hours = (current_time - previous_time).total_seconds() / 3600
                durations.append(duration_hours)
        
        # Set average duration
        stats["avg_regime_duration_hours"] = np.mean(durations) if durations else 0
        
        # Find most common transitions
        if transitions:
            sorted_transitions = sorted(transitions.items(), key=lambda x: x[1], reverse=True)
            stats["common_transitions"] = dict(sorted_transitions[:5])
        
        # Calculate average volatility by regime
        for regime, volatilities in stats["volatility_by_regime"].items():
            if volatilities:
                stats["volatility_by_regime"][regime] = np.mean(volatilities)
            else:
                stats["volatility_by_regime"][regime] = 0
        
        # Save statistics
        self.statistics = stats
    
    def get_recent_history(self, limit: int = 10) -> List[Dict]:
        """
        Get recent regime history
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of recent regime records
        """
        return self.regime_history[-limit:] if self.regime_history else []
    
    def get_regimes_for_period(self, days: int = 7) -> List[Dict]:
        """
        Get regime history for a specific period
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of regime records within the period
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_time.isoformat()
        
        return [r for r in self.regime_history if r["timestamp"] > cutoff_str]
    
    def get_regime_distribution(self) -> Dict:
        """
        Get distribution of regimes
        
        Returns:
            Dict of regime counts and percentages
        """
        return self.statistics.get("regime_distribution", {})
    
    def get_transition_matrix(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate regime transition probability matrix
        
        Returns:
            Dict of {from_regime: {to_regime: probability}}
        """
        transitions = {}
        
        # Count transitions
        for i in range(1, len(self.regime_history)):
            current = self.regime_history[i]
            previous = self.regime_history[i-1]
            
            from_regime = previous["regime"]
            to_regime = current["regime"]
            
            if from_regime not in transitions:
                transitions[from_regime] = {}
                
            transitions[from_regime][to_regime] = transitions[from_regime].get(to_regime, 0) + 1
        
        # Calculate probabilities
        transition_probs = {}
        
        for from_regime, destinations in transitions.items():
            total = sum(destinations.values())
            
            transition_probs[from_regime] = {
                to_regime: count / total
                for to_regime, count in destinations.items()
            }
            
        return transition_probs
    
    def get_statistics(self) -> Dict:
        """
        Get overall regime statistics
        
        Returns:
            Dict with statistics
        """
        return self.statistics
    
    def generate_regime_report(self, days: Optional[int] = 30) -> Dict:
        """
        Generate a comprehensive regime analysis report
        
        Args:
            days: Number of days to analyze (None for all history)
            
        Returns:
            Dict with report data
        """
        # Get relevant history
        if days is not None:
            history = self.get_regimes_for_period(days)
        else:
            history = self.regime_history
            
        if not history:
            return {"error": "No regime history available"}
            
        # Create DataFrame for analysis
        try:
            df = pd.DataFrame([
                {
                    "timestamp": datetime.fromisoformat(r["timestamp"]),
                    "regime": r["regime"],
                    "confidence": r.get("confidence", 0),
                    "volatility": r.get("metrics", {}).get("volatility_ratio", 0),
                    "adx": r.get("metrics", {}).get("adx", 0),
                    "rsi": r.get("metrics", {}).get("rsi", 50)
                }
                for r in history
            ])
            
            # Daily regime counts
            df["date"] = df["timestamp"].dt.date
            daily_regimes = df.groupby(["date", "regime"]).size().unstack(fill_value=0)
            
            # Calculate average metrics by regime
            regime_metrics = df.groupby("regime").agg({
                "confidence": "mean",
                "volatility": "mean",
                "adx": "mean",
                "rsi": "mean"
            }).to_dict()
            
            # Calculate transition matrix
            transition_matrix = self.get_transition_matrix()
            
            # Compile report
            report = {
                "timestamp": datetime.now().isoformat(),
                "period_days": days,
                "total_regimes": len(history),
                "regime_distribution": self.get_regime_distribution(),
                "transition_matrix": transition_matrix,
                "regime_metrics": regime_metrics,
                "latest_regime": history[-1] if history else None,
                "daily_breakdown": daily_regimes.to_dict() if not daily_regimes.empty else {},
                "statistics": self.statistics
            }
            
            return report
        except Exception as e:
            logger.error(f"Error generating regime report: {e}")
            return {"error": f"Failed to generate report: {str(e)}"}


# Singleton instance
regime_logger = RegimeLogger()
