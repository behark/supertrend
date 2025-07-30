"""
Regime Performance Logger Model
-------------------------------
This module defines database models for tracking regime performance metrics,
creating performance journals, and supporting playbook generation.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from src.database.db import Base


class RegimePerformanceEntry(Base):
    """Model for storing regime performance data with enriched metadata."""
    __tablename__ = "regime_performance_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Regime basic info
    regime_type = Column(String(50), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_minutes = Column(Integer)
    confidence = Column(Float)
    
    # Performance metrics
    win_rate = Column(Float)
    avg_profit_pct = Column(Float)
    roi_pct = Column(Float)
    max_drawdown_pct = Column(Float)
    sharpe_ratio = Column(Float)
    trade_count = Column(Integer)
    outperformance_vs_default = Column(Float)  # How much better than default profile
    
    # Market context
    preceding_regime = Column(String(50))
    preceding_duration_minutes = Column(Integer)
    market_volatility = Column(Float)
    adx_value = Column(Float)
    rsi_value = Column(Float)
    trend_direction = Column(String(20))
    market_phase = Column(String(30))  # Accumulation, Distribution, etc.
    
    # External factors
    vix_level = Column(Float)
    market_wide_trend = Column(String(30))  # Bull, Bear, Sideways
    sector_rotation = Column(Boolean)
    significant_news = Column(Text)
    
    # Technical levels at regime start/end
    key_support_level = Column(Float)
    key_resistance_level = Column(Float)
    ema_alignment = Column(String(30))  # e.g., "Bullish", "Bearish", "Mixed"
    
    # Pattern detection and scoring
    pattern_score = Column(Float)  # Higher = more reliable pattern
    pattern_name = Column(String(100))
    statistical_significance = Column(Float)  # p-value or similar
    is_outlier = Column(Boolean, default=False)  # Statistical outlier in performance
    is_high_performer = Column(Boolean, default=False)  # Top performer by defined metrics
    
    # Tradable pattern characteristics
    entry_signal_description = Column(Text)
    exit_signal_description = Column(Text)
    optimal_parameters = Column(JSON)  # Stores JSON with optimal settings
    position_sizing_recommendation = Column(Float)  # % of max position size
    
    # Relationship to playbook entries
    playbook_entries = relationship("PlaybookEntry", back_populates="performance_entry")
    
    def __repr__(self):
        return (f"<RegimePerformanceEntry(regime={self.regime_type}, "
                f"start={self.start_time}, confidence={self.confidence:.2f}, "
                f"roi={self.roi_pct:.2f}%, is_high_performer={self.is_high_performer})>")


class PlaybookEntry(Base):
    """Model for storing generated trading playbook entries."""
    __tablename__ = "regime_playbook_entries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Playbook metadata
    name = Column(String(100), nullable=False)
    regime_type = Column(String(50), nullable=False, index=True)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    is_auto_generated = Column(Boolean, default=False)
    confidence_threshold = Column(Float, default=0.7)  # Minimum confidence to apply
    user_rating = Column(Integer)  # User's rating of this playbook (1-5)
    
    # Trading strategy elements
    entry_conditions = Column(Text, nullable=False)
    exit_conditions = Column(Text, nullable=False)
    stop_loss_strategy = Column(Text)
    take_profit_strategy = Column(Text)
    position_sizing = Column(Text)
    parameter_settings = Column(JSON)
    expected_duration = Column(String(50))  # e.g., "2-5 days"
    risk_reward_ratio = Column(Float)
    
    # Visual pattern templates
    pattern_image_url = Column(String(255))
    pattern_description = Column(Text)
    
    # Performance tracking
    times_applied = Column(Integer, default=0)
    success_rate = Column(Float)
    average_roi = Column(Float)
    
    # Relationships
    performance_entry_id = Column(String(36), ForeignKey("regime_performance_entries.id"))
    performance_entry = relationship("RegimePerformanceEntry", back_populates="playbook_entries")
    
    def __repr__(self):
        return (f"<PlaybookEntry(name='{self.name}', regime={self.regime_type}, "
                f"active={self.is_active}, auto_generated={self.is_auto_generated})>")
