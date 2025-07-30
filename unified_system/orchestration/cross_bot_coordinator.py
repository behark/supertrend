"""
Cross-Bot Coordinator - Multi-Agent Intelligence Orchestration
============================================================
Enables cross-bot consensus, risk management, and collaborative intelligence
between Bidget and Bybit bots with advanced coordination features.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import json
import numpy as np
from enum import Enum

# Import unified system components
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from unified_system.communication.protocol import UnifiedMessage, MessageType, CommandType
from unified_system.intelligence.ml_sync_orchestrator import get_ml_sync_orchestrator

logger = logging.getLogger(__name__)

class ConsensusLevel(Enum):
    """Consensus agreement levels."""
    STRONG_AGREEMENT = "strong_agreement"      # >80% confidence alignment
    MODERATE_AGREEMENT = "moderate_agreement"  # 60-80% confidence alignment
    WEAK_AGREEMENT = "weak_agreement"          # 40-60% confidence alignment
    DISAGREEMENT = "disagreement"              # <40% confidence alignment

class RiskLevel(Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class CrossBotForecast:
    """Cross-bot forecast comparison and consensus."""
    symbol: str
    timeframe: str
    timestamp: datetime
    forecasts: Dict[str, Dict[str, Any]]  # agent_id -> forecast_data
    consensus_level: ConsensusLevel
    consensus_signal: str  # BUY, SELL, HOLD
    consensus_confidence: float
    risk_assessment: RiskLevel
    recommended_action: Dict[str, Any]

@dataclass
class RiskMetrics:
    """Cross-bot risk assessment metrics."""
    portfolio_correlation: float
    position_concentration: float
    drawdown_risk: float
    volatility_exposure: float
    leverage_risk: float
    overall_risk_score: float
    risk_level: RiskLevel
    recommendations: List[str]

class CrossBotCoordinator:
    """Coordinates intelligence and risk management across multiple bots."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize cross-bot coordinator."""
        self.config = config
        self.registered_bots: Dict[str, Dict[str, Any]] = {}
        
        # Consensus thresholds
        self.consensus_thresholds = {
            'strong': 0.8,
            'moderate': 0.6,
            'weak': 0.4
        }
        
        # Risk management settings
        self.risk_limits = {
            'max_portfolio_correlation': 0.7,
            'max_position_concentration': 0.3,
            'max_drawdown_threshold': 0.15,
            'max_leverage_exposure': 3.0
        }
        
        # Cross-bot state tracking
        self.active_forecasts: Dict[str, CrossBotForecast] = {}
        self.risk_assessments: Dict[str, RiskMetrics] = {}
        self.coordination_history: List[Dict[str, Any]] = []
        
        # Performance tracking
        self.consensus_performance = {
            'total_consensus_calls': 0,
            'successful_consensus': 0,
            'consensus_accuracy': 0.0,
            'risk_warnings_issued': 0,
            'risk_actions_taken': 0
        }
    
    def register_bot(self, bot_id: str, bot_config: Dict[str, Any]) -> bool:
        """Register a bot for cross-coordination."""
        try:
            self.registered_bots[bot_id] = {
                'bot_id': bot_id,
                'name': bot_config.get('name', bot_id),
                'capabilities': bot_config.get('capabilities', []),
                'risk_profile': bot_config.get('risk_profile', 'medium'),
                'registered_at': datetime.now(),
                'last_active': datetime.now(),
                'performance_metrics': bot_config.get('performance_metrics', {}),
                'status': 'active'
            }
            
            logger.info(f"[CROSS_BOT] Registered bot {bot_id} for coordination")
            return True
            
        except Exception as e:
            logger.error(f"[CROSS_BOT] Failed to register bot {bot_id}: {e}")
            return False
    
    async def execute_cross_forecast(self, symbol: str, timeframe: str, 
                                   target_bots: List[str] = None) -> CrossBotForecast:
        """Execute cross-bot forecast and generate consensus."""
        try:
            if target_bots is None:
                target_bots = list(self.registered_bots.keys())
            
            logger.info(f"[CROSS_BOT] Executing cross-forecast for {symbol} {timeframe}")
            
            # Collect forecasts from all target bots
            forecasts = {}
            for bot_id in target_bots:
                if bot_id in self.registered_bots:
                    try:
                        # Simulate forecast collection (integrate with actual bot APIs)
                        forecast_data = await self._get_bot_forecast(bot_id, symbol, timeframe)
                        if forecast_data:
                            forecasts[bot_id] = forecast_data
                    except Exception as e:
                        logger.error(f"[CROSS_BOT] Failed to get forecast from {bot_id}: {e}")
            
            # Generate consensus analysis
            consensus_result = self._analyze_forecast_consensus(forecasts, symbol, timeframe)
            
            # Store active forecast
            forecast_key = f"{symbol}_{timeframe}"
            self.active_forecasts[forecast_key] = consensus_result
            
            # Update performance tracking
            self.consensus_performance['total_consensus_calls'] += 1
            
            logger.info(f"[CROSS_BOT] Cross-forecast completed: {consensus_result.consensus_level.value}")
            return consensus_result
            
        except Exception as e:
            logger.error(f"[CROSS_BOT] Cross-forecast execution failed: {e}")
            raise
    
    async def _get_bot_forecast(self, bot_id: str, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Get forecast from a specific bot."""
        try:
            # Mock forecast data - integrate with actual bot APIs
            mock_forecasts = {
                'bidget': {
                    'signal': 'BUY',
                    'confidence': 0.75,
                    'regime': 'trending_up',
                    'entry_price': 43250.0,
                    'stop_loss': 42800.0,
                    'take_profit': 44100.0,
                    'risk_ratio': 2.5,
                    'position_size': 0.1
                },
                'bybit': {
                    'signal': 'BUY',
                    'confidence': 0.68,
                    'regime': 'consolidation',
                    'entry_price': 43200.0,
                    'stop_loss': 42750.0,
                    'take_profit': 44000.0,
                    'risk_ratio': 2.8,
                    'position_size': 0.08
                }
            }
            
            return mock_forecasts.get(bot_id)
            
        except Exception as e:
            logger.error(f"[CROSS_BOT] Error getting forecast from {bot_id}: {e}")
            return None
    
    def _analyze_forecast_consensus(self, forecasts: Dict[str, Dict[str, Any]], 
                                  symbol: str, timeframe: str) -> CrossBotForecast:
        """Analyze forecasts and generate consensus."""
        try:
            if not forecasts:
                raise ValueError("No forecasts available for consensus analysis")
            
            # Extract signals and confidences
            signals = [f['signal'] for f in forecasts.values()]
            confidences = [f['confidence'] for f in forecasts.values()]
            
            # Calculate signal consensus
            signal_counts = {}
            for signal in signals:
                signal_counts[signal] = signal_counts.get(signal, 0) + 1
            
            # Determine consensus signal
            consensus_signal = max(signal_counts, key=signal_counts.get)
            signal_agreement = signal_counts[consensus_signal] / len(signals)
            
            # Calculate confidence consensus
            consensus_confidence = np.mean(confidences)
            confidence_std = np.std(confidences)
            
            # Determine consensus level
            if signal_agreement >= self.consensus_thresholds['strong'] and confidence_std < 0.1:
                consensus_level = ConsensusLevel.STRONG_AGREEMENT
            elif signal_agreement >= self.consensus_thresholds['moderate'] and confidence_std < 0.15:
                consensus_level = ConsensusLevel.MODERATE_AGREEMENT
            elif signal_agreement >= self.consensus_thresholds['weak']:
                consensus_level = ConsensusLevel.WEAK_AGREEMENT
            else:
                consensus_level = ConsensusLevel.DISAGREEMENT
            
            # Risk assessment
            risk_level = self._assess_consensus_risk(forecasts, consensus_level)
            
            # Generate recommended action
            recommended_action = self._generate_recommended_action(
                forecasts, consensus_signal, consensus_confidence, risk_level
            )
            
            return CrossBotForecast(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.now(),
                forecasts=forecasts,
                consensus_level=consensus_level,
                consensus_signal=consensus_signal,
                consensus_confidence=consensus_confidence,
                risk_assessment=risk_level,
                recommended_action=recommended_action
            )
            
        except Exception as e:
            logger.error(f"[CROSS_BOT] Consensus analysis failed: {e}")
            raise
    
    def _assess_consensus_risk(self, forecasts: Dict[str, Dict[str, Any]], 
                             consensus_level: ConsensusLevel) -> RiskLevel:
        """Assess risk level of the consensus."""
        try:
            risk_factors = []
            
            # Confidence spread risk
            confidences = [f['confidence'] for f in forecasts.values()]
            confidence_spread = max(confidences) - min(confidences)
            if confidence_spread > 0.3:
                risk_factors.append('high_confidence_spread')
            
            # Position size risk
            position_sizes = [f.get('position_size', 0.1) for f in forecasts.values()]
            total_exposure = sum(position_sizes)
            if total_exposure > 0.3:
                risk_factors.append('high_position_exposure')
            
            # Risk ratio analysis
            risk_ratios = [f.get('risk_ratio', 2.0) for f in forecasts.values()]
            avg_risk_ratio = np.mean(risk_ratios)
            if avg_risk_ratio < 1.5:
                risk_factors.append('poor_risk_ratio')
            
            # Consensus level risk
            if consensus_level == ConsensusLevel.DISAGREEMENT:
                risk_factors.append('consensus_disagreement')
            elif consensus_level == ConsensusLevel.WEAK_AGREEMENT:
                risk_factors.append('weak_consensus')
            
            # Determine overall risk level
            if len(risk_factors) >= 3:
                return RiskLevel.CRITICAL
            elif len(risk_factors) == 2:
                return RiskLevel.HIGH
            elif len(risk_factors) == 1:
                return RiskLevel.MEDIUM
            else:
                return RiskLevel.LOW
                
        except Exception as e:
            logger.error(f"[CROSS_BOT] Risk assessment failed: {e}")
            return RiskLevel.HIGH
    
    def _generate_recommended_action(self, forecasts: Dict[str, Dict[str, Any]], 
                                   consensus_signal: str, consensus_confidence: float,
                                   risk_level: RiskLevel) -> Dict[str, Any]:
        """Generate recommended action based on consensus and risk."""
        try:
            # Calculate weighted averages for trade parameters
            total_weight = sum(f['confidence'] for f in forecasts.values())
            
            weighted_entry = sum(f['entry_price'] * f['confidence'] for f in forecasts.values()) / total_weight
            weighted_stop = sum(f['stop_loss'] * f['confidence'] for f in forecasts.values()) / total_weight
            weighted_target = sum(f['take_profit'] * f['confidence'] for f in forecasts.values()) / total_weight
            
            # Adjust position size based on risk
            base_position_size = np.mean([f.get('position_size', 0.1) for f in forecasts.values()])
            
            risk_multipliers = {
                RiskLevel.LOW: 1.0,
                RiskLevel.MEDIUM: 0.8,
                RiskLevel.HIGH: 0.5,
                RiskLevel.CRITICAL: 0.2
            }
            
            adjusted_position_size = base_position_size * risk_multipliers[risk_level]
            
            # Generate action recommendation
            if risk_level == RiskLevel.CRITICAL:
                action_type = "AVOID"
                reasoning = "Critical risk level detected - avoid trade"
            elif consensus_confidence < 0.5:
                action_type = "WAIT"
                reasoning = "Low consensus confidence - wait for better setup"
            else:
                action_type = consensus_signal
                reasoning = f"Consensus {consensus_signal} with {consensus_confidence:.1%} confidence"
            
            return {
                'action': action_type,
                'reasoning': reasoning,
                'entry_price': weighted_entry,
                'stop_loss': weighted_stop,
                'take_profit': weighted_target,
                'position_size': adjusted_position_size,
                'risk_level': risk_level.value,
                'consensus_confidence': consensus_confidence,
                'risk_adjusted': True if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] else False
            }
            
        except Exception as e:
            logger.error(f"[CROSS_BOT] Action generation failed: {e}")
            return {'action': 'WAIT', 'reasoning': 'Error in consensus analysis'}
    
    async def execute_risk_assessment(self, target_bots: List[str] = None) -> RiskMetrics:
        """Execute comprehensive risk assessment across bots."""
        try:
            if target_bots is None:
                target_bots = list(self.registered_bots.keys())
            
            logger.info("[CROSS_BOT] Executing cross-bot risk assessment")
            
            # Collect portfolio data from all bots
            portfolio_data = {}
            for bot_id in target_bots:
                if bot_id in self.registered_bots:
                    try:
                        bot_portfolio = await self._get_bot_portfolio(bot_id)
                        if bot_portfolio:
                            portfolio_data[bot_id] = bot_portfolio
                    except Exception as e:
                        logger.error(f"[CROSS_BOT] Failed to get portfolio from {bot_id}: {e}")
            
            # Calculate risk metrics
            risk_metrics = self._calculate_risk_metrics(portfolio_data)
            
            # Store risk assessment
            self.risk_assessments['current'] = risk_metrics
            
            # Issue warnings if necessary
            if risk_metrics.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                await self._issue_risk_warning(risk_metrics)
                self.consensus_performance['risk_warnings_issued'] += 1
            
            logger.info(f"[CROSS_BOT] Risk assessment completed: {risk_metrics.risk_level.value}")
            return risk_metrics
            
        except Exception as e:
            logger.error(f"[CROSS_BOT] Risk assessment failed: {e}")
            raise
    
    async def _get_bot_portfolio(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get portfolio data from a specific bot."""
        try:
            # Mock portfolio data - integrate with actual bot APIs
            mock_portfolios = {
                'bidget': {
                    'total_value': 10000.0,
                    'positions': {
                        'BTCUSDT': {'size': 0.1, 'value': 4325.0, 'pnl': 125.0},
                        'ETHUSDT': {'size': 2.0, 'value': 5000.0, 'pnl': -50.0}
                    },
                    'leverage': 2.0,
                    'margin_used': 0.6,
                    'daily_pnl': 75.0,
                    'max_drawdown': 0.08
                },
                'bybit': {
                    'total_value': 8000.0,
                    'positions': {
                        'BTCUSDT': {'size': 0.08, 'value': 3460.0, 'pnl': 80.0},
                        'SOLUSDT': {'size': 50.0, 'value': 3500.0, 'pnl': 25.0}
                    },
                    'leverage': 1.5,
                    'margin_used': 0.4,
                    'daily_pnl': 105.0,
                    'max_drawdown': 0.05
                }
            }
            
            return mock_portfolios.get(bot_id)
            
        except Exception as e:
            logger.error(f"[CROSS_BOT] Error getting portfolio from {bot_id}: {e}")
            return None
    
    def _calculate_risk_metrics(self, portfolio_data: Dict[str, Dict[str, Any]]) -> RiskMetrics:
        """Calculate comprehensive risk metrics."""
        try:
            if not portfolio_data:
                raise ValueError("No portfolio data available for risk calculation")
            
            # Portfolio correlation analysis
            symbols_exposure = {}
            total_portfolio_value = 0
            
            for bot_id, portfolio in portfolio_data.items():
                total_portfolio_value += portfolio['total_value']
                
                for symbol, position in portfolio['positions'].items():
                    if symbol not in symbols_exposure:
                        symbols_exposure[symbol] = 0
                    symbols_exposure[symbol] += position['value']
            
            # Calculate concentration risk
            max_symbol_exposure = max(symbols_exposure.values()) if symbols_exposure else 0
            position_concentration = max_symbol_exposure / total_portfolio_value if total_portfolio_value > 0 else 0
            
            # Calculate correlation (simplified - same symbols across bots)
            common_symbols = set()
            for portfolio in portfolio_data.values():
                if common_symbols:
                    common_symbols &= set(portfolio['positions'].keys())
                else:
                    common_symbols = set(portfolio['positions'].keys())
            
            portfolio_correlation = len(common_symbols) / max(len(symbols_exposure), 1)
            
            # Drawdown risk
            drawdowns = [p['max_drawdown'] for p in portfolio_data.values()]
            max_drawdown = max(drawdowns) if drawdowns else 0
            
            # Volatility exposure (leverage-weighted)
            leverages = [p['leverage'] for p in portfolio_data.values()]
            avg_leverage = np.mean(leverages) if leverages else 1.0
            volatility_exposure = avg_leverage * portfolio_correlation
            
            # Leverage risk
            max_leverage = max(leverages) if leverages else 1.0
            leverage_risk = min(max_leverage / 3.0, 1.0)  # Normalize to 3x as high risk
            
            # Overall risk score (weighted combination)
            risk_components = {
                'correlation': portfolio_correlation * 0.25,
                'concentration': position_concentration * 0.25,
                'drawdown': max_drawdown * 0.2,
                'volatility': min(volatility_exposure / 2.0, 1.0) * 0.15,
                'leverage': leverage_risk * 0.15
            }
            
            overall_risk_score = sum(risk_components.values())
            
            # Determine risk level
            if overall_risk_score >= 0.8:
                risk_level = RiskLevel.CRITICAL
            elif overall_risk_score >= 0.6:
                risk_level = RiskLevel.HIGH
            elif overall_risk_score >= 0.4:
                risk_level = RiskLevel.MEDIUM
            else:
                risk_level = RiskLevel.LOW
            
            # Generate recommendations
            recommendations = self._generate_risk_recommendations(risk_components, risk_level)
            
            return RiskMetrics(
                portfolio_correlation=portfolio_correlation,
                position_concentration=position_concentration,
                drawdown_risk=max_drawdown,
                volatility_exposure=volatility_exposure,
                leverage_risk=leverage_risk,
                overall_risk_score=overall_risk_score,
                risk_level=risk_level,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"[CROSS_BOT] Risk metrics calculation failed: {e}")
            raise
    
    def _generate_risk_recommendations(self, risk_components: Dict[str, float], 
                                     risk_level: RiskLevel) -> List[str]:
        """Generate risk management recommendations."""
        recommendations = []
        
        try:
            if risk_components['correlation'] > 0.7:
                recommendations.append("Reduce portfolio correlation by diversifying across different symbols")
            
            if risk_components['concentration'] > 0.3:
                recommendations.append("Reduce position concentration - maximum 30% in any single symbol")
            
            if risk_components['drawdown'] > 0.15:
                recommendations.append("Implement stricter stop-loss management to limit drawdowns")
            
            if risk_components['leverage'] > 0.5:
                recommendations.append("Consider reducing leverage exposure across bots")
            
            if risk_level == RiskLevel.CRITICAL:
                recommendations.append("CRITICAL: Consider halting new positions until risk is reduced")
            elif risk_level == RiskLevel.HIGH:
                recommendations.append("HIGH RISK: Implement immediate risk reduction measures")
            
            if not recommendations:
                recommendations.append("Risk levels are within acceptable parameters")
                
        except Exception as e:
            logger.error(f"[CROSS_BOT] Risk recommendations generation failed: {e}")
            recommendations.append("Error generating recommendations - manual review required")
        
        return recommendations
    
    async def _issue_risk_warning(self, risk_metrics: RiskMetrics):
        """Issue risk warning to all registered bots."""
        try:
            warning_message = {
                'type': 'risk_warning',
                'risk_level': risk_metrics.risk_level.value,
                'overall_risk_score': risk_metrics.overall_risk_score,
                'recommendations': risk_metrics.recommendations,
                'timestamp': datetime.now().isoformat(),
                'action_required': risk_metrics.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
            }
            
            # Send warning to all registered bots
            for bot_id in self.registered_bots.keys():
                logger.warning(f"[CROSS_BOT] Issuing {risk_metrics.risk_level.value} risk warning to {bot_id}")
                # In production, this would send actual messages to bots
            
        except Exception as e:
            logger.error(f"[CROSS_BOT] Failed to issue risk warning: {e}")
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """Get current coordination status."""
        return {
            'registered_bots': len(self.registered_bots),
            'active_forecasts': len(self.active_forecasts),
            'current_risk_level': self.risk_assessments.get('current', {}).get('risk_level', 'unknown'),
            'performance_metrics': self.consensus_performance,
            'last_coordination': max([f.timestamp for f in self.active_forecasts.values()]) if self.active_forecasts else None
        }

# Global coordinator instance
_cross_bot_coordinator = None

def initialize_cross_bot_coordinator(config: Dict[str, Any]) -> CrossBotCoordinator:
    """Initialize the global cross-bot coordinator."""
    global _cross_bot_coordinator
    _cross_bot_coordinator = CrossBotCoordinator(config)
    return _cross_bot_coordinator

def get_cross_bot_coordinator() -> Optional[CrossBotCoordinator]:
    """Get the global cross-bot coordinator instance."""
    return _cross_bot_coordinator
