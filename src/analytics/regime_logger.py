"""
Regime Performance Logger
------------------------
This module provides functionality for automatically tracking regime performance,
analyzing patterns, and generating playbook entries.

Key features:
- Performance tracking with enhanced metadata
- Statistical analysis of regime performance
- Pattern recognition for high-performing regimes
- Playbook entry generation based on performance data
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple, Any
from sqlalchemy.orm import Session
from statistics import mean, stdev

from src.database.db import get_db
from src.models.regime_performance import RegimePerformanceEntry, PlaybookEntry
from src.market_analyzer import MarketAnalyzer
from src.utils.logger import setup_logger

logger = setup_logger('regime_logger')


class RegimePerformanceLogger:
    """
    Logs and analyzes regime performance data, identifying high-performing regimes
    and generating insights for playbook entries.
    """

    def __init__(self, db_session: Optional[Session] = None):
        """Initialize the regime performance logger."""
        self.db = db_session or next(get_db())
        self.market_analyzer = MarketAnalyzer()
        self.performance_threshold = 1.5  # ROI multiplier vs average to flag high performers
        self.confidence_threshold = 0.75  # Minimum confidence for reliable entries
        self.min_trades = 5  # Minimum trades needed for statistical significance
        
    def log_regime_performance(self, regime_data: Dict[str, Any], 
                              performance_metrics: Dict[str, Any]) -> RegimePerformanceEntry:
        """
        Log the performance of a completed regime with enriched metadata.
        
        Args:
            regime_data: Data about the regime (type, duration, confidence, etc.)
            performance_metrics: Performance data (win rate, ROI, etc.)
            
        Returns:
            The created RegimePerformanceEntry instance
        """
        try:
            # Extract basic regime info
            entry = RegimePerformanceEntry(
                regime_type=regime_data['regime'],
                start_time=regime_data['start_time'],
                end_time=regime_data['end_time'],
                duration_minutes=regime_data['duration_minutes'],
                confidence=regime_data['confidence'],
                
                # Performance metrics
                win_rate=performance_metrics['win_rate'],
                avg_profit_pct=performance_metrics['avg_profit'],
                roi_pct=performance_metrics['roi'],
                max_drawdown_pct=performance_metrics.get('max_drawdown', 0),
                sharpe_ratio=performance_metrics.get('sharpe_ratio'),
                trade_count=performance_metrics['trade_count'],
                outperformance_vs_default=performance_metrics.get('outperformance', 0),
                
                # Market context
                preceding_regime=regime_data.get('preceding_regime'),
                preceding_duration_minutes=regime_data.get('preceding_duration_minutes'),
                market_volatility=regime_data.get('metrics', {}).get('volatility'),
                adx_value=regime_data.get('metrics', {}).get('adx'),
                rsi_value=regime_data.get('metrics', {}).get('rsi'),
                trend_direction=regime_data.get('metrics', {}).get('trend_direction'),
                
                # Technical levels
                ema_alignment=regime_data.get('metrics', {}).get('ema_alignment')
            )
            
            # Enrich with additional market context (can be expanded later)
            self._enrich_with_market_context(entry, regime_data)
            
            # Calculate statistical significance and outlier status
            self._calculate_statistical_metrics(entry, performance_metrics)
            
            # Save to database
            self.db.add(entry)
            self.db.commit()
            self.db.refresh(entry)
            
            # Log high performers
            if entry.is_high_performer:
                logger.info(f"High-performing regime detected: {entry}")
                
                # Generate playbook entry if confidence is sufficient
                if entry.confidence >= self.confidence_threshold and entry.trade_count >= self.min_trades:
                    self._generate_playbook_entry(entry)
                    
            return entry
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error logging regime performance: {str(e)}")
            raise
    
    def _enrich_with_market_context(self, entry: RegimePerformanceEntry, regime_data: Dict[str, Any]) -> None:
        """
        Enrich a performance entry with broader market context data.
        
        Args:
            entry: The RegimePerformanceEntry to enrich
            regime_data: Raw regime data
        """
        # This can be expanded to fetch external data like VIX, sector rotation, etc.
        # For now, use what's available in the regime data
        metrics = regime_data.get('metrics', {})
        
        # Market phase detection based on available indicators
        if metrics.get('bollinger_width') and metrics.get('rsi') and metrics.get('adx'):
            bb_width = metrics['bollinger_width']
            rsi = metrics['rsi']
            adx = metrics['adx']
            
            # Simple market phase detection logic
            if bb_width < 0.015:  # Narrow bands
                if adx < 20:
                    entry.market_phase = "Consolidation"
                else:
                    entry.market_phase = "Trending Continuation"
            elif bb_width > 0.03:  # Wide bands
                if adx > 25:
                    entry.market_phase = "Momentum"
                else:
                    entry.market_phase = "Distribution"
            else:  # Normal band width
                if rsi > 70:
                    entry.market_phase = "Overbought"
                elif rsi < 30:
                    entry.market_phase = "Oversold"
                else:
                    entry.market_phase = "Normal"
    
    def _calculate_statistical_metrics(self, entry: RegimePerformanceEntry, 
                                      performance_metrics: Dict[str, Any]) -> None:
        """
        Calculate statistical significance and determine if this is an outlier performer.
        
        Args:
            entry: The RegimePerformanceEntry to update
            performance_metrics: Performance data
        """
        # Get historical performance for this regime type
        historical = self._get_historical_performance(entry.regime_type)
        
        if historical and len(historical) >= 3:  # Need at least 3 data points for basic stats
            # Calculate average ROI for this regime type
            roi_values = [h.roi_pct for h in historical if h.roi_pct is not None]
            
            if roi_values:
                avg_roi = mean(roi_values)
                
                # If we have enough data, calculate standard deviation
                if len(roi_values) >= 5:
                    std_dev = stdev(roi_values)
                    z_score = (entry.roi_pct - avg_roi) / std_dev if std_dev > 0 else 0
                    entry.statistical_significance = z_score
                    
                    # Flag as outlier if performance is >2 std deviations above mean
                    entry.is_outlier = z_score > 2.0
                
                # Flag as high performer if ROI is significantly above average
                entry.is_high_performer = entry.roi_pct > (avg_roi * self.performance_threshold)
                
                # Calculate pattern score based on confidence and statistical significance
                entry.pattern_score = (entry.confidence * 0.6) + \
                                    (min(1.0, (entry.roi_pct / (avg_roi * 2))) * 0.4)
        else:
            # Not enough historical data for statistical analysis
            # Flag as high performer based solely on absolute performance
            entry.is_high_performer = entry.roi_pct > 5.0  # 5% ROI as baseline
            entry.pattern_score = entry.confidence * 0.8  # Weighted mostly by confidence
    
    def _get_historical_performance(self, regime_type: str) -> List[RegimePerformanceEntry]:
        """
        Get historical performance entries for a specific regime type.
        
        Args:
            regime_type: The type of regime to get historical data for
            
        Returns:
            List of RegimePerformanceEntry instances
        """
        return self.db.query(RegimePerformanceEntry)\
                    .filter(RegimePerformanceEntry.regime_type == regime_type)\
                    .order_by(RegimePerformanceEntry.timestamp.desc())\
                    .limit(50)\
                    .all()
    
    def _generate_playbook_entry(self, performance_entry: RegimePerformanceEntry) -> PlaybookEntry:
        """
        Generate a playbook entry based on a high-performing regime.
        
        Args:
            performance_entry: The high-performing regime entry
            
        Returns:
            The created PlaybookEntry instance
        """
        try:
            # Create name based on regime type and characteristics
            name = f"{performance_entry.regime_type} Optimizer"
            if performance_entry.market_phase:
                name += f" - {performance_entry.market_phase}"
            
            # Default parameter settings (can be expanded)
            parameter_settings = {
                "confidence_threshold": performance_entry.confidence,
                "recommended_duration": performance_entry.duration_minutes,
                "adx_min": performance_entry.adx_value * 0.9 if performance_entry.adx_value else None,
                "volatility_target": performance_entry.market_volatility
            }
            
            # Create entry conditions based on pattern
            entry_conditions = self._generate_entry_conditions(performance_entry)
            exit_conditions = self._generate_exit_conditions(performance_entry)
            
            # Create the playbook entry
            playbook = PlaybookEntry(
                name=name,
                regime_type=performance_entry.regime_type,
                description=f"Auto-generated playbook for high-performing {performance_entry.regime_type} regime.",
                is_active=True,
                is_auto_generated=True,
                confidence_threshold=max(0.7, performance_entry.confidence * 0.9),  # Slightly lower than original
                
                # Strategy elements
                entry_conditions=entry_conditions,
                exit_conditions=exit_conditions,
                stop_loss_strategy=self._generate_stop_loss_strategy(performance_entry),
                take_profit_strategy=self._generate_take_profit_strategy(performance_entry),
                position_sizing=self._generate_position_sizing(performance_entry),
                parameter_settings=parameter_settings,
                expected_duration=self._format_duration(performance_entry.duration_minutes),
                risk_reward_ratio=self._calculate_risk_reward(performance_entry),
                
                # Link to source performance entry
                performance_entry=performance_entry
            )
            
            # Save to database
            self.db.add(playbook)
            self.db.commit()
            self.db.refresh(playbook)
            
            logger.info(f"Generated new playbook entry: {playbook}")
            return playbook
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error generating playbook entry: {str(e)}")
            raise
    
    def _generate_entry_conditions(self, entry: RegimePerformanceEntry) -> str:
        """Generate entry conditions based on regime characteristics."""
        conditions = [f"1. Wait for {entry.regime_type} regime with confidence > {entry.confidence:.0%}"]
        
        # Add ADX condition if available
        if entry.adx_value:
            conditions.append(f"2. ADX should be > {entry.adx_value:.1f}")
        
        # Add RSI condition if available
        if entry.rsi_value:
            if entry.rsi_value > 70:
                conditions.append(f"3. Wait for RSI to drop below 70 and start rising again")
            elif entry.rsi_value < 30:
                conditions.append(f"3. Wait for RSI to rise above 30 and start falling again")
            else:
                conditions.append(f"3. RSI should be between 40-60 for balanced entries")
        
        # Add trend direction condition if available
        if entry.trend_direction:
            conditions.append(f"4. Confirm trend direction is {entry.trend_direction}")
        
        # Add EMA alignment if available
        if entry.ema_alignment:
            conditions.append(f"5. EMA alignment should be {entry.ema_alignment}")
            
        # Add market phase condition if available
        if entry.market_phase:
            conditions.append(f"6. Optimal during {entry.market_phase} market phase")
            
        return "\n".join(conditions)
    
    def _generate_exit_conditions(self, entry: RegimePerformanceEntry) -> str:
        """Generate exit conditions based on regime characteristics."""
        conditions = [
            f"1. When confidence drops below {(entry.confidence * 0.8):.0%}",
            f"2. When regime changes from {entry.regime_type}",
            f"3. After {self._format_duration(entry.duration_minutes)} (typical regime duration)"
        ]
        
        return "\n".join(conditions)
    
    def _generate_stop_loss_strategy(self, entry: RegimePerformanceEntry) -> str:
        """Generate stop loss strategy based on regime volatility."""
        if entry.market_volatility:
            volatility_factor = min(3.0, max(1.2, entry.market_volatility * 5))
            return f"Use volatility-adjusted stop loss at {volatility_factor:.1f}x ATR"
        else:
            return "Standard stop loss at 2x ATR"
    
    def _generate_take_profit_strategy(self, entry: RegimePerformanceEntry) -> str:
        """Generate take profit strategy based on regime characteristics."""
        if entry.avg_profit_pct:
            return f"Target minimum {entry.avg_profit_pct:.1f}% profit with trailing stop after 50% target reached"
        else:
            return "Use trailing stop loss at 3x ATR once in profit"
    
    def _generate_position_sizing(self, entry: RegimePerformanceEntry) -> str:
        """Generate position sizing recommendations."""
        # Base sizing on confidence and historical performance
        if entry.is_outlier and entry.confidence > 0.85:
            return "100% of standard position size"
        elif entry.is_high_performer and entry.confidence > 0.75:
            return "80% of standard position size"
        else:
            return "50% of standard position size"
    
    def _format_duration(self, minutes: Optional[int]) -> str:
        """Format duration in minutes to human-readable string."""
        if not minutes:
            return "Unknown duration"
            
        if minutes < 60:
            return f"{minutes} minutes"
        elif minutes < 60 * 24:
            hours = minutes / 60
            return f"{hours:.1f} hours"
        else:
            days = minutes / (60 * 24)
            return f"{days:.1f} days"
    
    def _calculate_risk_reward(self, entry: RegimePerformanceEntry) -> float:
        """Calculate risk-reward ratio based on performance metrics."""
        if not entry.avg_profit_pct or not entry.max_drawdown_pct or entry.max_drawdown_pct == 0:
            return 2.0  # Default
            
        risk_reward = abs(entry.avg_profit_pct / entry.max_drawdown_pct)
        return min(5.0, max(1.0, risk_reward))  # Clamp between 1.0 and 5.0
    
    def get_top_performing_regimes(self, limit: int = 10) -> List[RegimePerformanceEntry]:
        """
        Get the top performing regime entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of top performing RegimePerformanceEntry instances
        """
        return self.db.query(RegimePerformanceEntry)\
                    .filter(RegimePerformanceEntry.is_high_performer == True)\
                    .order_by(RegimePerformanceEntry.roi_pct.desc())\
                    .limit(limit)\
                    .all()
    
    def get_active_playbooks(self) -> List[PlaybookEntry]:
        """
        Get all active playbook entries.
        
        Returns:
            List of active PlaybookEntry instances
        """
        return self.db.query(PlaybookEntry)\
                    .filter(PlaybookEntry.is_active == True)\
                    .order_by(PlaybookEntry.created_at.desc())\
                    .all()
    
    def match_current_regime_to_playbooks(self, current_regime: Dict[str, Any]) -> List[PlaybookEntry]:
        """
        Match the current market regime to appropriate playbook entries.
        
        Args:
            current_regime: Data about the current regime
            
        Returns:
            List of matching PlaybookEntry instances
        """
        # Get active playbooks for this regime type
        playbooks = self.db.query(PlaybookEntry)\
                         .filter(PlaybookEntry.regime_type == current_regime['regime'],
                                PlaybookEntry.is_active == True)\
                         .all()
        
        matching_playbooks = []
        
        # Check each playbook for confidence threshold
        for playbook in playbooks:
            if current_regime.get('confidence', 0) >= playbook.confidence_threshold:
                matching_playbooks.append(playbook)
        
        return matching_playbooks


# Singleton instance
regime_logger = RegimePerformanceLogger()
