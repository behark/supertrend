"""
Smart Signal Filter for Bidget Trading Bot
------------------------------------------
This module provides filtering capabilities for the Bidget trading bot:
1. Price filter (<$1)
2. Timeframe filter (15m-3h)
3. Win probability filter (>90%)
4. Risk-reward optimization
"""
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

logger = logging.getLogger(__name__)

class SmartFilter:
    """Smart filter for Bidget trading signals"""
    
    def __init__(self, config=None):
        """Initialize the smart filter with configuration."""
        self.config = config or {}
        self.max_coin_price = self.config.get('max_coin_price', 1.0)
        self.min_success_probability = self.config.get('min_success_probability', 0.9)
        self.max_daily_signals = self.config.get('max_telegram_signals', 30)
        self.signals_sent_today = 0
        self.last_reset_day = datetime.now().date()
        
        # Track filtered signals
        self.filtered_signals = []
        
    def reset_daily_counters(self):
        """Reset daily counters if it's a new day."""
        today = datetime.now().date()
        if today != self.last_reset_day:
            self.signals_sent_today = 0
            self.last_reset_day = today
            self.filtered_signals = []
            logger.info(f"Reset daily signal counters for {today}")
    
    def check_price(self, price: float) -> bool:
        """Check if price is below the maximum allowed price."""
        return price <= self.max_coin_price
    
    def check_timeframe(self, timeframe: str) -> bool:
        """Check if timeframe is in the allowed range (15m-3h)."""
        allowed_timeframes = ['15m', '30m', '1h', '2h', '3h']
        return timeframe in allowed_timeframes
    
    def check_probability(self, probability: float) -> bool:
        """Check if success probability meets minimum threshold."""
        return probability >= self.min_success_probability
    
    def calculate_signal_score(self, signal: Dict[str, Any]) -> float:
        """Calculate a score for the signal based on risk/reward and probability.
        
        Higher score = better signal.
        """
        # Extract key metrics
        probability = signal.get('probability', 0)
        risk_pct = signal.get('risk_percentage', 0)
        reward_pct = signal.get('profit_percentage', 0)
        
        # Avoid division by zero
        if risk_pct <= 0:
            risk_pct = 0.1
            
        # Calculate risk-reward ratio
        risk_reward = reward_pct / risk_pct
        
        # Penalize signals with low probability or poor risk-reward
        if probability < self.min_success_probability:
            return 0
            
        # Final score calculation - weight probability higher
        score = (probability * 0.7) + (risk_reward * 0.3)
        return score
        
    def can_send_signal(self) -> bool:
        """Check if we can send more signals today."""
        self.reset_daily_counters()
        return self.signals_sent_today < self.max_daily_signals
        
    def filter_signal(self, signal: Dict[str, Any]) -> Tuple[bool, str]:
        """Filter a signal based on Bidget criteria.
        
        Returns:
            (is_accepted, reason): Whether signal passed filter and why
        """
        self.reset_daily_counters()
        
        # If we've hit the daily signal limit, reject
        if not self.can_send_signal():
            return False, f"Daily signal limit ({self.max_daily_signals}) reached"
        
        # Check price
        price = signal.get('entry_price', 0)
        if not self.check_price(price):
            return False, f"Price too high: ${price:.4f} > ${self.max_coin_price:.4f}"
        
        # Check timeframe
        timeframe = signal.get('timeframe', '')
        if not self.check_timeframe(timeframe):
            return False, f"Timeframe not in range: {timeframe}"
        
        # Check probability
        probability = signal.get('probability', 0)
        if not self.check_probability(probability):
            return False, f"Win probability too low: {probability*100:.1f}% < {self.min_success_probability*100:.1f}%"
        
        # Calculate score for sorting/ranking
        score = self.calculate_signal_score(signal)
        signal['score'] = score
        
        # If signal passes all filters, increment counter
        self.signals_sent_today += 1
        
        # Add to filtered signals list
        self.filtered_signals.append(signal)
        
        # Sort signals by score (best first)
        self.filtered_signals.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return True, f"Signal accepted (score: {score:.2f})"

    def get_top_signals(self, max_count: int = None) -> List[Dict[str, Any]]:
        """Get the top N signals sorted by score."""
        if max_count is None:
            max_count = self.max_daily_signals
            
        return self.filtered_signals[:max_count]
