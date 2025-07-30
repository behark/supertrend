"""
ML Sync Orchestrator - Collective Intelligence Layer
=================================================
Connects individual ML systems into a unified learning network
enabling cross-agent pattern sharing, performance broadcasting,
and adaptive intelligence evolution.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import numpy as np
from dataclasses import dataclass, asdict
import pickle
import hashlib

# Import existing ML components
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from ml_playbook_tuner import MLPlaybookTuner
from unified_system.communication.protocol import UnifiedMessage, MessageType, CommandType

logger = logging.getLogger(__name__)

@dataclass
class MLPattern:
    """Represents a learned pattern that can be shared across agents."""
    pattern_id: str
    agent_id: str
    symbol: str
    timeframe: str
    pattern_type: str  # 'regime_transition', 'entry_signal', 'risk_adjustment'
    features: Dict[str, float]
    confidence: float
    success_rate: float
    trade_count: int
    created_at: datetime
    last_updated: datetime
    performance_metrics: Dict[str, float]

@dataclass
class MLInsight:
    """Represents actionable intelligence derived from collective learning."""
    insight_id: str
    insight_type: str  # 'parameter_optimization', 'regime_detection', 'risk_warning'
    source_agents: List[str]
    target_agents: List[str]
    data: Dict[str, Any]
    confidence: float
    priority: str  # 'low', 'medium', 'high', 'critical'
    expires_at: Optional[datetime]
    created_at: datetime

class CollectiveMemory:
    """Shared memory system for cross-agent learning."""
    
    def __init__(self, memory_path: str = "unified_system/data/collective_memory"):
        """Initialize collective memory system."""
        self.memory_path = memory_path
        self.patterns: Dict[str, MLPattern] = {}
        self.insights: Dict[str, MLInsight] = {}
        self.performance_history: Dict[str, List[Dict]] = {}
        
        # Ensure memory directory exists
        os.makedirs(memory_path, exist_ok=True)
        
        # Load existing memory
        self._load_memory()
    
    def store_pattern(self, pattern: MLPattern) -> bool:
        """Store a learned pattern in collective memory."""
        try:
            self.patterns[pattern.pattern_id] = pattern
            self._save_patterns()
            logger.info(f"[MEMORY] Stored pattern {pattern.pattern_id} from {pattern.agent_id}")
            return True
        except Exception as e:
            logger.error(f"[MEMORY] Failed to store pattern: {e}")
            return False
    
    def get_relevant_patterns(self, agent_id: str, symbol: str, 
                            timeframe: str, pattern_type: str = None) -> List[MLPattern]:
        """Retrieve patterns relevant to current context."""
        relevant = []
        
        for pattern in self.patterns.values():
            # Skip own patterns
            if pattern.agent_id == agent_id:
                continue
                
            # Match symbol and timeframe
            if pattern.symbol == symbol and pattern.timeframe == timeframe:
                if pattern_type is None or pattern.pattern_type == pattern_type:
                    # Only include high-confidence patterns
                    if pattern.confidence > 0.6 and pattern.success_rate > 0.55:
                        relevant.append(pattern)
        
        # Sort by confidence and success rate
        relevant.sort(key=lambda p: (p.confidence * p.success_rate), reverse=True)
        return relevant[:10]  # Top 10 most relevant
    
    def store_insight(self, insight: MLInsight) -> bool:
        """Store actionable intelligence in collective memory."""
        try:
            self.insights[insight.insight_id] = insight
            self._save_insights()
            logger.info(f"[MEMORY] Stored insight {insight.insight_id} for {insight.target_agents}")
            return True
        except Exception as e:
            logger.error(f"[MEMORY] Failed to store insight: {e}")
            return False
    
    def get_pending_insights(self, agent_id: str) -> List[MLInsight]:
        """Get pending insights for a specific agent."""
        pending = []
        current_time = datetime.now()
        
        for insight in self.insights.values():
            # Check if insight is for this agent and not expired
            if agent_id in insight.target_agents:
                if insight.expires_at is None or insight.expires_at > current_time:
                    pending.append(insight)
        
        # Sort by priority and creation time
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        pending.sort(key=lambda i: (priority_order.get(i.priority, 3), i.created_at))
        return pending
    
    def record_performance(self, agent_id: str, performance_data: Dict) -> None:
        """Record agent performance for collective analysis."""
        if agent_id not in self.performance_history:
            self.performance_history[agent_id] = []
        
        performance_entry = {
            'timestamp': datetime.now().isoformat(),
            'data': performance_data
        }
        
        self.performance_history[agent_id].append(performance_entry)
        
        # Keep only last 1000 entries per agent
        if len(self.performance_history[agent_id]) > 1000:
            self.performance_history[agent_id] = self.performance_history[agent_id][-1000:]
        
        self._save_performance_history()
    
    def _load_memory(self) -> None:
        """Load existing memory from disk."""
        try:
            # Load patterns
            patterns_file = os.path.join(self.memory_path, "patterns.pkl")
            if os.path.exists(patterns_file):
                with open(patterns_file, 'rb') as f:
                    self.patterns = pickle.load(f)
            
            # Load insights
            insights_file = os.path.join(self.memory_path, "insights.pkl")
            if os.path.exists(insights_file):
                with open(insights_file, 'rb') as f:
                    self.insights = pickle.load(f)
            
            # Load performance history
            perf_file = os.path.join(self.memory_path, "performance.json")
            if os.path.exists(perf_file):
                with open(perf_file, 'r') as f:
                    self.performance_history = json.load(f)
                    
            logger.info(f"[MEMORY] Loaded {len(self.patterns)} patterns, {len(self.insights)} insights")
            
        except Exception as e:
            logger.error(f"[MEMORY] Failed to load memory: {e}")
    
    def _save_patterns(self) -> None:
        """Save patterns to disk."""
        try:
            patterns_file = os.path.join(self.memory_path, "patterns.pkl")
            with open(patterns_file, 'wb') as f:
                pickle.dump(self.patterns, f)
        except Exception as e:
            logger.error(f"[MEMORY] Failed to save patterns: {e}")
    
    def _save_insights(self) -> None:
        """Save insights to disk."""
        try:
            insights_file = os.path.join(self.memory_path, "insights.pkl")
            with open(insights_file, 'wb') as f:
                pickle.dump(self.insights, f)
        except Exception as e:
            logger.error(f"[MEMORY] Failed to save insights: {e}")
    
    def _save_performance_history(self) -> None:
        """Save performance history to disk."""
        try:
            perf_file = os.path.join(self.memory_path, "performance.json")
            with open(perf_file, 'w') as f:
                json.dump(self.performance_history, f, indent=2)
        except Exception as e:
            logger.error(f"[MEMORY] Failed to save performance history: {e}")

class MLSyncOrchestrator:
    """Orchestrates ML learning and pattern sharing across agents."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize ML sync orchestrator."""
        self.config = config
        self.collective_memory = CollectiveMemory()
        self.agent_ml_tuners: Dict[str, MLPlaybookTuner] = {}
        self.sync_interval = config.get('sync_interval', 300)  # 5 minutes
        self.running = False
        
        # Performance tracking
        self.sync_stats = {
            'patterns_shared': 0,
            'insights_generated': 0,
            'optimizations_applied': 0,
            'last_sync': None
        }
    
    def register_agent_ml_tuner(self, agent_id: str, ml_tuner: MLPlaybookTuner) -> bool:
        """Register an agent's ML tuner for collective learning."""
        try:
            self.agent_ml_tuners[agent_id] = ml_tuner
            logger.info(f"[ML_SYNC] Registered ML tuner for agent {agent_id}")
            return True
        except Exception as e:
            logger.error(f"[ML_SYNC] Failed to register ML tuner for {agent_id}: {e}")
            return False
    
    async def start_sync_loop(self) -> None:
        """Start the continuous ML synchronization loop."""
        self.running = True
        logger.info("[ML_SYNC] Starting collective intelligence sync loop")
        
        while self.running:
            try:
                await self._perform_sync_cycle()
                await asyncio.sleep(self.sync_interval)
            except Exception as e:
                logger.error(f"[ML_SYNC] Sync cycle error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    async def stop_sync_loop(self) -> None:
        """Stop the ML synchronization loop."""
        self.running = False
        logger.info("[ML_SYNC] Stopping collective intelligence sync loop")
    
    async def _perform_sync_cycle(self) -> None:
        """Perform one complete synchronization cycle."""
        logger.info("[ML_SYNC] Starting sync cycle")
        
        # Step 1: Collect patterns from all agents
        await self._collect_agent_patterns()
        
        # Step 2: Generate cross-agent insights
        await self._generate_collective_insights()
        
        # Step 3: Distribute insights to agents
        await self._distribute_insights()
        
        # Step 4: Update performance metrics
        await self._update_performance_metrics()
        
        self.sync_stats['last_sync'] = datetime.now()
        logger.info("[ML_SYNC] Sync cycle completed")
    
    async def _collect_agent_patterns(self) -> None:
        """Collect learned patterns from all registered agents."""
        for agent_id, ml_tuner in self.agent_ml_tuners.items():
            try:
                # Get recent patterns from agent's ML tuner
                patterns = await self._extract_agent_patterns(agent_id, ml_tuner)
                
                for pattern in patterns:
                    if self.collective_memory.store_pattern(pattern):
                        self.sync_stats['patterns_shared'] += 1
                        
            except Exception as e:
                logger.error(f"[ML_SYNC] Failed to collect patterns from {agent_id}: {e}")
    
    async def _extract_agent_patterns(self, agent_id: str, ml_tuner: MLPlaybookTuner) -> List[MLPattern]:
        """Extract learnable patterns from an agent's ML tuner."""
        patterns = []
        
        try:
            # Get recent training data and model performance
            recent_data = ml_tuner.prepare_training_data(lookback_days=7)
            
            if recent_data.empty:
                return patterns
            
            # Extract regime transition patterns
            regime_patterns = self._extract_regime_patterns(agent_id, recent_data)
            patterns.extend(regime_patterns)
            
            # Extract entry signal patterns
            entry_patterns = self._extract_entry_patterns(agent_id, recent_data)
            patterns.extend(entry_patterns)
            
            # Extract risk adjustment patterns
            risk_patterns = self._extract_risk_patterns(agent_id, recent_data)
            patterns.extend(risk_patterns)
            
        except Exception as e:
            logger.error(f"[ML_SYNC] Failed to extract patterns from {agent_id}: {e}")
        
        return patterns
    
    def _extract_regime_patterns(self, agent_id: str, data) -> List[MLPattern]:
        """Extract regime transition patterns from agent data."""
        patterns = []
        
        # Group by symbol and timeframe
        for (symbol, timeframe), group in data.groupby(['symbol', 'timeframe']):
            if len(group) < 10:  # Need sufficient data
                continue
            
            # Analyze regime transitions
            regime_changes = group[group['regime'] != group['regime'].shift(1)]
            
            if len(regime_changes) > 3:
                # Calculate pattern features
                features = {
                    'avg_confidence_before_change': float(group['confidence'].rolling(5).mean().iloc[-1]),
                    'volatility_increase': float(group['volatility'].pct_change().mean()),
                    'volume_spike': float(group['volume'].pct_change().mean()),
                    'rsi_divergence': float(abs(group['rsi'].diff()).mean())
                }
                
                # Calculate success metrics
                successful_transitions = regime_changes[regime_changes['pnl'] > 0]
                success_rate = len(successful_transitions) / len(regime_changes)
                avg_confidence = float(regime_changes['confidence'].mean())
                
                pattern = MLPattern(
                    pattern_id=self._generate_pattern_id(agent_id, symbol, timeframe, 'regime_transition'),
                    agent_id=agent_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    pattern_type='regime_transition',
                    features=features,
                    confidence=avg_confidence,
                    success_rate=success_rate,
                    trade_count=len(regime_changes),
                    created_at=datetime.now(),
                    last_updated=datetime.now(),
                    performance_metrics={
                        'avg_pnl': float(regime_changes['pnl'].mean()),
                        'max_drawdown': float(regime_changes['pnl'].min()),
                        'win_rate': success_rate
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _extract_entry_patterns(self, agent_id: str, data) -> List[MLPattern]:
        """Extract entry signal patterns from agent data."""
        patterns = []
        
        # Similar logic for entry patterns
        for (symbol, timeframe), group in data.groupby(['symbol', 'timeframe']):
            if len(group) < 10:
                continue
            
            entry_signals = group[group['action'].isin(['BUY', 'SELL'])]
            
            if len(entry_signals) > 5:
                features = {
                    'avg_entry_confidence': float(entry_signals['confidence'].mean()),
                    'rsi_at_entry': float(entry_signals['rsi'].mean()),
                    'macd_signal_strength': float(entry_signals['macd'].abs().mean()),
                    'volume_confirmation': float(entry_signals['volume'].mean())
                }
                
                successful_entries = entry_signals[entry_signals['pnl'] > 0]
                success_rate = len(successful_entries) / len(entry_signals)
                
                pattern = MLPattern(
                    pattern_id=self._generate_pattern_id(agent_id, symbol, timeframe, 'entry_signal'),
                    agent_id=agent_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    pattern_type='entry_signal',
                    features=features,
                    confidence=float(entry_signals['confidence'].mean()),
                    success_rate=success_rate,
                    trade_count=len(entry_signals),
                    created_at=datetime.now(),
                    last_updated=datetime.now(),
                    performance_metrics={
                        'avg_pnl': float(entry_signals['pnl'].mean()),
                        'avg_hold_time': float(entry_signals['hold_time'].mean()) if 'hold_time' in entry_signals else 0,
                        'win_rate': success_rate
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    def _extract_risk_patterns(self, agent_id: str, data) -> List[MLPattern]:
        """Extract risk adjustment patterns from agent data."""
        patterns = []
        
        # Analyze risk management effectiveness
        for (symbol, timeframe), group in data.groupby(['symbol', 'timeframe']):
            if len(group) < 10:
                continue
            
            # Focus on trades with stop losses
            risk_trades = group[group['stop_loss'].notna()]
            
            if len(risk_trades) > 5:
                features = {
                    'avg_risk_ratio': float(risk_trades['risk_ratio'].mean()) if 'risk_ratio' in risk_trades else 2.0,
                    'stop_loss_effectiveness': float((risk_trades['pnl'] > risk_trades['stop_loss']).mean()),
                    'position_size_correlation': float(risk_trades['position_size'].corr(risk_trades['confidence'])),
                    'volatility_adjustment': float(risk_trades['leverage'].corr(risk_trades['volatility']))
                }
                
                effective_risk_mgmt = risk_trades[risk_trades['pnl'] > risk_trades['stop_loss']]
                success_rate = len(effective_risk_mgmt) / len(risk_trades)
                
                pattern = MLPattern(
                    pattern_id=self._generate_pattern_id(agent_id, symbol, timeframe, 'risk_adjustment'),
                    agent_id=agent_id,
                    symbol=symbol,
                    timeframe=timeframe,
                    pattern_type='risk_adjustment',
                    features=features,
                    confidence=float(risk_trades['confidence'].mean()),
                    success_rate=success_rate,
                    trade_count=len(risk_trades),
                    created_at=datetime.now(),
                    last_updated=datetime.now(),
                    performance_metrics={
                        'risk_adjusted_return': float(risk_trades['pnl'].mean() / risk_trades['pnl'].std()) if risk_trades['pnl'].std() > 0 else 0,
                        'max_loss_prevented': float(risk_trades['stop_loss'].min()),
                        'avg_drawdown': float(risk_trades['pnl'].min())
                    }
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _generate_collective_insights(self) -> None:
        """Generate actionable insights from collective patterns."""
        try:
            # Cross-agent performance comparison
            await self._generate_performance_insights()
            
            # Pattern consensus analysis
            await self._generate_consensus_insights()
            
            # Risk correlation warnings
            await self._generate_risk_insights()
            
        except Exception as e:
            logger.error(f"[ML_SYNC] Failed to generate insights: {e}")
    
    async def _generate_performance_insights(self) -> None:
        """Generate insights from cross-agent performance comparison."""
        for agent_id in self.agent_ml_tuners.keys():
            try:
                # Find top-performing patterns from other agents
                top_patterns = []
                for pattern in self.collective_memory.patterns.values():
                    if (pattern.agent_id != agent_id and 
                        pattern.success_rate > 0.7 and 
                        pattern.confidence > 0.8):
                        top_patterns.append(pattern)
                
                if top_patterns:
                    # Group by pattern type
                    pattern_groups = {}
                    for pattern in top_patterns:
                        if pattern.pattern_type not in pattern_groups:
                            pattern_groups[pattern.pattern_type] = []
                        pattern_groups[pattern.pattern_type].append(pattern)
                    
                    # Generate optimization recommendations
                    for pattern_type, patterns in pattern_groups.items():
                        if len(patterns) >= 2:  # Need multiple examples
                            insight = MLInsight(
                                insight_id=self._generate_insight_id(agent_id, pattern_type),
                                insight_type='parameter_optimization',
                                source_agents=[p.agent_id for p in patterns],
                                target_agents=[agent_id],
                                data={
                                    'pattern_type': pattern_type,
                                    'recommended_features': self._aggregate_pattern_features(patterns),
                                    'expected_improvement': self._calculate_improvement_potential(patterns),
                                    'confidence_threshold': max(p.confidence for p in patterns),
                                    'success_rate_target': max(p.success_rate for p in patterns)
                                },
                                confidence=min(p.confidence for p in patterns),
                                priority='high' if pattern_type == 'risk_adjustment' else 'medium',
                                expires_at=datetime.now() + timedelta(hours=24),
                                created_at=datetime.now()
                            )
                            
                            if self.collective_memory.store_insight(insight):
                                self.sync_stats['insights_generated'] += 1
                                
            except Exception as e:
                logger.error(f"[ML_SYNC] Failed to generate performance insights for {agent_id}: {e}")
    
    async def _distribute_insights(self) -> None:
        """Distribute insights to target agents."""
        for agent_id, ml_tuner in self.agent_ml_tuners.items():
            try:
                pending_insights = self.collective_memory.get_pending_insights(agent_id)
                
                for insight in pending_insights:
                    # Apply insight to agent's ML system
                    if await self._apply_insight_to_agent(agent_id, ml_tuner, insight):
                        self.sync_stats['optimizations_applied'] += 1
                        logger.info(f"[ML_SYNC] Applied insight {insight.insight_id} to {agent_id}")
                        
            except Exception as e:
                logger.error(f"[ML_SYNC] Failed to distribute insights to {agent_id}: {e}")
    
    async def _apply_insight_to_agent(self, agent_id: str, ml_tuner: MLPlaybookTuner, 
                                    insight: MLInsight) -> bool:
        """Apply a collective insight to an agent's ML system."""
        try:
            if insight.insight_type == 'parameter_optimization':
                # Apply parameter optimizations
                data = insight.data
                pattern_type = data['pattern_type']
                recommended_features = data['recommended_features']
                
                # Update ML tuner with collective intelligence
                # This would integrate with the existing ML tuner's optimization logic
                logger.info(f"[ML_SYNC] Applying {pattern_type} optimization to {agent_id}")
                
                # Mark insight as processed
                insight.expires_at = datetime.now()
                return True
                
        except Exception as e:
            logger.error(f"[ML_SYNC] Failed to apply insight to {agent_id}: {e}")
            
        return False
    
    def _generate_pattern_id(self, agent_id: str, symbol: str, timeframe: str, pattern_type: str) -> str:
        """Generate unique pattern ID."""
        data = f"{agent_id}_{symbol}_{timeframe}_{pattern_type}_{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def _generate_insight_id(self, agent_id: str, insight_type: str) -> str:
        """Generate unique insight ID."""
        data = f"{agent_id}_{insight_type}_{datetime.now().isoformat()}"
        return hashlib.md5(data.encode()).hexdigest()[:16]
    
    def _aggregate_pattern_features(self, patterns: List[MLPattern]) -> Dict[str, float]:
        """Aggregate features from multiple patterns."""
        aggregated = {}
        
        # Collect all feature keys
        all_keys = set()
        for pattern in patterns:
            all_keys.update(pattern.features.keys())
        
        # Calculate weighted averages
        for key in all_keys:
            values = []
            weights = []
            
            for pattern in patterns:
                if key in pattern.features:
                    values.append(pattern.features[key])
                    weights.append(pattern.confidence * pattern.success_rate)
            
            if values:
                weighted_avg = np.average(values, weights=weights)
                aggregated[key] = float(weighted_avg)
        
        return aggregated
    
    def _calculate_improvement_potential(self, patterns: List[MLPattern]) -> float:
        """Calculate potential improvement from adopting collective patterns."""
        if not patterns:
            return 0.0
        
        avg_success_rate = np.mean([p.success_rate for p in patterns])
        avg_confidence = np.mean([p.confidence for p in patterns])
        
        # Estimate improvement potential
        improvement = (avg_success_rate * avg_confidence) - 0.5  # Baseline 50%
        return max(0.0, min(1.0, improvement))
    
    async def _update_performance_metrics(self) -> None:
        """Update collective performance metrics."""
        try:
            # Record current sync statistics
            for agent_id in self.agent_ml_tuners.keys():
                performance_data = {
                    'sync_cycle': self.sync_stats['last_sync'].isoformat() if self.sync_stats['last_sync'] else None,
                    'patterns_available': len([p for p in self.collective_memory.patterns.values() if p.agent_id != agent_id]),
                    'pending_insights': len(self.collective_memory.get_pending_insights(agent_id)),
                    'collective_intelligence_score': self._calculate_ci_score(agent_id)
                }
                
                self.collective_memory.record_performance(agent_id, performance_data)
                
        except Exception as e:
            logger.error(f"[ML_SYNC] Failed to update performance metrics: {e}")
    
    def _calculate_ci_score(self, agent_id: str) -> float:
        """Calculate collective intelligence score for an agent."""
        try:
            # Factors: pattern sharing, insight adoption, performance improvement
            patterns_shared = len([p for p in self.collective_memory.patterns.values() if p.agent_id == agent_id])
            insights_received = len(self.collective_memory.get_pending_insights(agent_id))
            
            # Normalize and combine factors
            pattern_score = min(1.0, patterns_shared / 10.0)  # Max 10 patterns
            insight_score = min(1.0, insights_received / 5.0)  # Max 5 insights
            
            ci_score = (pattern_score + insight_score) / 2.0
            return ci_score
            
        except Exception as e:
            logger.error(f"[ML_SYNC] Failed to calculate CI score for {agent_id}: {e}")
            return 0.0
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current synchronization status."""
        return {
            'running': self.running,
            'registered_agents': list(self.agent_ml_tuners.keys()),
            'patterns_in_memory': len(self.collective_memory.patterns),
            'active_insights': len(self.collective_memory.insights),
            'sync_stats': self.sync_stats.copy(),
            'next_sync_in': self.sync_interval if self.running else None
        }

# Global ML sync orchestrator instance
_ml_sync_orchestrator = None

def initialize_ml_sync_orchestrator(config: Dict[str, Any]) -> MLSyncOrchestrator:
    """Initialize the global ML sync orchestrator."""
    global _ml_sync_orchestrator
    _ml_sync_orchestrator = MLSyncOrchestrator(config)
    return _ml_sync_orchestrator

def get_ml_sync_orchestrator() -> Optional[MLSyncOrchestrator]:
    """Get the global ML sync orchestrator instance."""
    return _ml_sync_orchestrator
