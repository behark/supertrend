"""
Multi-Agent Feedback Loop System
================================
Enables Bidget and Bybit bots to share memory traits and perform
cross-agent reinforcement learning with consensus tuning.
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import hashlib

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.smart_trade_memory import get_smart_trade_memory
from live_ops.live_ops_manager import get_live_ops_manager
from scaling.multi_agent_scaler import get_multi_agent_scaler

logger = logging.getLogger(__name__)

class MultiAgentFeedback:
    """Multi-agent feedback loop for shared learning and consensus tuning."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize multi-agent feedback system."""
        self.config = config
        self.feedback_active = False
        
        # Feedback intervals
        self.memory_sync_interval = config.get('memory_sync_interval', 600)  # 10 minutes
        self.consensus_tuning_interval = config.get('consensus_tuning_interval', 1800)  # 30 minutes
        self.trait_sharing_interval = config.get('trait_sharing_interval', 300)  # 5 minutes
        
        # System components
        self.smart_memory = None
        self.live_ops = None
        self.multi_scaler = None
        
        # Agent tracking
        self.agents = ['bidget', 'bybit']
        self.shared_memory_pool = {}
        self.consensus_history = []
        self.trait_exchanges = 0
        
        # Learning parameters
        self.reinforcement_threshold = config.get('reinforcement_threshold', 0.7)
        self.consensus_weight = config.get('consensus_weight', 0.6)
        
    async def initialize_feedback_loop(self):
        """Initialize the multi-agent feedback system."""
        try:
            logger.info("🤝 [FEEDBACK] Initializing Multi-Agent Feedback Loop")
            
            # Get system components
            self.smart_memory = get_smart_trade_memory()
            self.live_ops = get_live_ops_manager()
            self.multi_scaler = get_multi_agent_scaler()
            
            if not all([self.smart_memory, self.live_ops, self.multi_scaler]):
                raise Exception("Required system components not available")
            
            self.feedback_active = True
            
            # Initialize shared memory pool
            await self._initialize_shared_memory_pool()
            
            # Start feedback loops
            asyncio.create_task(self._memory_sync_loop())
            asyncio.create_task(self._consensus_tuning_loop())
            asyncio.create_task(self._trait_sharing_loop())
            
            logger.info("✅ [FEEDBACK] Multi-agent feedback loop initialized")
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Initialization failed: {e}")
            raise
    
    async def _initialize_shared_memory_pool(self):
        """Initialize the shared memory pool for cross-agent learning."""
        try:
            logger.info("🧠 [FEEDBACK] Initializing shared memory pool")
            
            # Create shared memory structure
            self.shared_memory_pool = {
                'patterns': {},
                'strategies': {},
                'performance_metrics': {},
                'risk_profiles': {},
                'consensus_decisions': [],
                'trait_library': {}
            }
            
            # Load existing patterns from each agent
            for agent in self.agents:
                agent_patterns = await self._extract_agent_patterns(agent)
                if agent_patterns:
                    self.shared_memory_pool['patterns'][agent] = agent_patterns
                    logger.info(f"📊 [FEEDBACK] Loaded {len(agent_patterns)} patterns from {agent}")
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Shared memory pool initialization failed: {e}")
    
    async def _memory_sync_loop(self):
        """Synchronize memory between agents."""
        logger.info("🔄 [FEEDBACK] Memory sync loop started")
        
        while self.feedback_active:
            try:
                # Sync patterns between agents
                sync_result = await self._sync_agent_memories()
                
                if sync_result['patterns_synced'] > 0:
                    logger.info(f"🔄 [MEMORY_SYNC] Synced {sync_result['patterns_synced']} patterns "
                              f"across {len(self.agents)} agents")
                
                # Update shared memory pool
                await self._update_shared_memory_pool()
                
                await asyncio.sleep(self.memory_sync_interval)
                
            except Exception as e:
                logger.error(f"❌ [MEMORY_SYNC] Error in memory sync loop: {e}")
                await asyncio.sleep(self.memory_sync_interval * 2)
    
    async def _consensus_tuning_loop(self):
        """Perform consensus-based parameter tuning."""
        logger.info("⚖️ [FEEDBACK] Consensus tuning loop started")
        
        while self.feedback_active:
            try:
                # Gather performance data from all agents
                performance_data = await self._gather_agent_performance()
                
                # Calculate consensus parameters
                consensus_params = await self._calculate_consensus_parameters(performance_data)
                
                if consensus_params:
                    # Apply consensus tuning
                    tuning_result = await self._apply_consensus_tuning(consensus_params)
                    
                    if tuning_result['success']:
                        logger.info(f"⚖️ [CONSENSUS] Applied consensus tuning: "
                                  f"{tuning_result['parameters_tuned']} parameters updated")
                        
                        # Log consensus decision
                        self.consensus_history.append({
                            'timestamp': datetime.now().isoformat(),
                            'parameters': consensus_params,
                            'confidence': tuning_result.get('confidence', 0.0)
                        })
                
                await asyncio.sleep(self.consensus_tuning_interval)
                
            except Exception as e:
                logger.error(f"❌ [CONSENSUS] Error in consensus tuning loop: {e}")
                await asyncio.sleep(self.consensus_tuning_interval * 2)
    
    async def _trait_sharing_loop(self):
        """Share successful traits between agents."""
        logger.info("🧬 [FEEDBACK] Trait sharing loop started")
        
        while self.feedback_active:
            try:
                # Identify successful traits from each agent
                successful_traits = await self._identify_successful_traits()
                
                # Share traits between agents
                if successful_traits:
                    sharing_result = await self._share_traits_between_agents(successful_traits)
                    
                    if sharing_result['traits_shared'] > 0:
                        self.trait_exchanges += sharing_result['traits_shared']
                        
                        logger.info(f"🧬 [TRAIT_SHARE] Shared {sharing_result['traits_shared']} "
                                  f"successful traits between agents")
                
                await asyncio.sleep(self.trait_sharing_interval)
                
            except Exception as e:
                logger.error(f"❌ [TRAIT_SHARE] Error in trait sharing loop: {e}")
                await asyncio.sleep(self.trait_sharing_interval * 2)
    
    async def _extract_agent_patterns(self, agent: str) -> List[Dict[str, Any]]:
        """Extract patterns from specific agent."""
        try:
            # Get agent-specific patterns from memory
            patterns_result = await self.smart_memory.execute_memory_command(
                'memory_get_patterns', {
                    'agent_filter': agent,
                    'min_confidence': 0.5
                }
            )
            
            if patterns_result.get('success', False):
                return patterns_result.get('patterns', [])
            
            return []
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Error extracting patterns from {agent}: {e}")
            return []
    
    async def _sync_agent_memories(self) -> Dict[str, Any]:
        """Synchronize memory patterns between agents."""
        try:
            patterns_synced = 0
            
            # Cross-pollinate patterns between agents
            for source_agent in self.agents:
                for target_agent in self.agents:
                    if source_agent != target_agent:
                        # Get high-performing patterns from source
                        source_patterns = await self._extract_agent_patterns(source_agent)
                        
                        # Filter for high-confidence patterns
                        high_confidence_patterns = [
                            p for p in source_patterns 
                            if p.get('confidence', 0) >= self.reinforcement_threshold
                        ]
                        
                        # Share with target agent
                        if high_confidence_patterns:
                            sync_result = await self._transfer_patterns_to_agent(
                                target_agent, high_confidence_patterns, source_agent
                            )
                            patterns_synced += sync_result.get('patterns_transferred', 0)
            
            return {
                'success': True,
                'patterns_synced': patterns_synced,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Memory sync failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _transfer_patterns_to_agent(self, target_agent: str, patterns: List[Dict[str, Any]], 
                                        source_agent: str) -> Dict[str, Any]:
        """Transfer patterns to target agent."""
        try:
            patterns_transferred = 0
            
            for pattern in patterns:
                # Create cross-agent pattern record
                cross_pattern = {
                    **pattern,
                    'source_agent': source_agent,
                    'target_agent': target_agent,
                    'transfer_timestamp': datetime.now().isoformat(),
                    'cross_agent_confidence': pattern.get('confidence', 0) * self.consensus_weight
                }
                
                # Store in memory system
                transfer_result = await self.smart_memory.execute_memory_command(
                    'memory_store_cross_pattern', {
                        'pattern': cross_pattern,
                        'agent': target_agent
                    }
                )
                
                if transfer_result.get('success', False):
                    patterns_transferred += 1
            
            return {
                'success': True,
                'patterns_transferred': patterns_transferred
            }
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Pattern transfer failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _gather_agent_performance(self) -> Dict[str, Any]:
        """Gather performance data from all agents."""
        try:
            performance_data = {}
            
            for agent in self.agents:
                # Get agent performance metrics
                agent_stats = await self.smart_memory.execute_memory_command(
                    'memory_agent_stats', {
                        'agent': agent,
                        'lookback_hours': 24
                    }
                )
                
                if agent_stats.get('success', False):
                    performance_data[agent] = agent_stats.get('stats', {})
            
            return performance_data
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Performance gathering failed: {e}")
            return {}
    
    async def _calculate_consensus_parameters(self, performance_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Calculate consensus parameters based on agent performance."""
        try:
            if not performance_data:
                return None
            
            # Calculate weighted averages for key parameters
            consensus_params = {}
            
            # Risk parameters
            risk_ratios = []
            leverage_values = []
            confidence_thresholds = []
            
            for agent, stats in performance_data.items():
                if stats.get('win_rate', 0) >= 0.6:  # Only consider successful agents
                    risk_ratios.append(stats.get('avg_risk_ratio', 2.0))
                    leverage_values.append(stats.get('avg_leverage', 1.0))
                    confidence_thresholds.append(stats.get('avg_confidence_threshold', 0.7))
            
            if risk_ratios:
                consensus_params['risk_ratio'] = sum(risk_ratios) / len(risk_ratios)
                consensus_params['leverage'] = sum(leverage_values) / len(leverage_values)
                consensus_params['confidence_threshold'] = sum(confidence_thresholds) / len(confidence_thresholds)
                
                # Calculate consensus confidence
                consensus_params['consensus_confidence'] = min(len(risk_ratios) / len(self.agents), 1.0)
                
                return consensus_params
            
            return None
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Consensus calculation failed: {e}")
            return None
    
    async def _apply_consensus_tuning(self, consensus_params: Dict[str, Any]) -> Dict[str, Any]:
        """Apply consensus parameters to all agents."""
        try:
            parameters_tuned = 0
            
            for agent in self.agents:
                # Apply consensus parameters to agent
                tuning_result = await self.smart_memory.execute_memory_command(
                    'memory_apply_consensus_tuning', {
                        'agent': agent,
                        'parameters': consensus_params
                    }
                )
                
                if tuning_result.get('success', False):
                    parameters_tuned += tuning_result.get('parameters_updated', 0)
            
            return {
                'success': True,
                'parameters_tuned': parameters_tuned,
                'confidence': consensus_params.get('consensus_confidence', 0.0)
            }
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Consensus tuning application failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _identify_successful_traits(self) -> Dict[str, List[Dict[str, Any]]]:
        """Identify successful traits from each agent."""
        try:
            successful_traits = {}
            
            for agent in self.agents:
                # Get high-performing patterns
                traits_result = await self.smart_memory.execute_memory_command(
                    'memory_get_successful_traits', {
                        'agent': agent,
                        'min_win_rate': 0.7,
                        'min_trades': 5
                    }
                )
                
                if traits_result.get('success', False):
                    traits = traits_result.get('traits', [])
                    if traits:
                        successful_traits[agent] = traits
            
            return successful_traits
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Trait identification failed: {e}")
            return {}
    
    async def _share_traits_between_agents(self, successful_traits: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Share successful traits between agents."""
        try:
            traits_shared = 0
            
            for source_agent, traits in successful_traits.items():
                for target_agent in self.agents:
                    if source_agent != target_agent:
                        # Share top traits with target agent
                        top_traits = sorted(traits, key=lambda x: x.get('performance_score', 0), reverse=True)[:3]
                        
                        for trait in top_traits:
                            # Create shared trait record
                            shared_trait = {
                                **trait,
                                'source_agent': source_agent,
                                'target_agent': target_agent,
                                'share_timestamp': datetime.now().isoformat(),
                                'trait_id': hashlib.md5(f"{source_agent}_{target_agent}_{trait.get('trait_type', 'unknown')}_{datetime.now()}".encode()).hexdigest()[:8]
                            }
                            
                            # Store shared trait
                            share_result = await self.smart_memory.execute_memory_command(
                                'memory_store_shared_trait', {
                                    'trait': shared_trait,
                                    'target_agent': target_agent
                                }
                            )
                            
                            if share_result.get('success', False):
                                traits_shared += 1
            
            return {
                'success': True,
                'traits_shared': traits_shared
            }
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Trait sharing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _update_shared_memory_pool(self):
        """Update the shared memory pool with latest data."""
        try:
            # Update patterns
            for agent in self.agents:
                agent_patterns = await self._extract_agent_patterns(agent)
                if agent_patterns:
                    self.shared_memory_pool['patterns'][agent] = agent_patterns
            
            # Update performance metrics
            performance_data = await self._gather_agent_performance()
            self.shared_memory_pool['performance_metrics'] = performance_data
            
            # Trim old consensus decisions
            if len(self.consensus_history) > 100:
                self.consensus_history = self.consensus_history[-50:]
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Shared memory pool update failed: {e}")
    
    async def execute_feedback_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute feedback system command."""
        try:
            params = params or {}
            
            if command == 'feedback_status':
                return await self._handle_feedback_status(params)
            elif command == 'force_memory_sync':
                return await self._handle_force_memory_sync(params)
            elif command == 'consensus_tune':
                return await self._handle_consensus_tune(params)
            elif command == 'trait_share':
                return await self._handle_trait_share(params)
            else:
                return {'success': False, 'error': f'Unknown feedback command: {command}'}
                
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Command execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_feedback_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle feedback status command."""
        try:
            return {
                'success': True,
                'message': 'Multi-agent feedback status',
                'feedback_active': self.feedback_active,
                'agents': self.agents,
                'trait_exchanges': self.trait_exchanges,
                'consensus_decisions': len(self.consensus_history),
                'shared_patterns': sum(len(patterns) for patterns in self.shared_memory_pool['patterns'].values()),
                'last_consensus': self.consensus_history[-1] if self.consensus_history else None,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Status command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_force_memory_sync(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle force memory sync command."""
        try:
            logger.info("🔄 [FEEDBACK] Forcing memory sync between agents")
            
            sync_result = await self._sync_agent_memories()
            
            return {
                'success': True,
                'message': 'Memory sync forced successfully',
                'sync_result': sync_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Force memory sync failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_consensus_tune(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle consensus tuning command."""
        try:
            logger.info("⚖️ [FEEDBACK] Forcing consensus tuning")
            
            performance_data = await self._gather_agent_performance()
            consensus_params = await self._calculate_consensus_parameters(performance_data)
            
            if consensus_params:
                tuning_result = await self._apply_consensus_tuning(consensus_params)
                
                return {
                    'success': True,
                    'message': 'Consensus tuning completed',
                    'consensus_params': consensus_params,
                    'tuning_result': tuning_result,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'Insufficient performance data for consensus tuning'
                }
                
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Consensus tuning failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_trait_share(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle trait sharing command."""
        try:
            logger.info("🧬 [FEEDBACK] Forcing trait sharing between agents")
            
            successful_traits = await self._identify_successful_traits()
            
            if successful_traits:
                sharing_result = await self._share_traits_between_agents(successful_traits)
                
                return {
                    'success': True,
                    'message': 'Trait sharing completed',
                    'successful_traits': {k: len(v) for k, v in successful_traits.items()},
                    'sharing_result': sharing_result,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'No successful traits identified for sharing'
                }
                
        except Exception as e:
            logger.error(f"❌ [FEEDBACK] Trait sharing failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_feedback_status(self) -> Dict[str, Any]:
        """Get current feedback system status."""
        return {
            'feedback_active': self.feedback_active,
            'agents': self.agents,
            'trait_exchanges': self.trait_exchanges,
            'consensus_decisions': len(self.consensus_history),
            'shared_patterns': sum(len(patterns) for patterns in self.shared_memory_pool['patterns'].values()),
            'memory_sync_interval': self.memory_sync_interval,
            'consensus_tuning_interval': self.consensus_tuning_interval,
            'trait_sharing_interval': self.trait_sharing_interval,
            'timestamp': datetime.now().isoformat()
        }

# Global multi-agent feedback instance
_multi_agent_feedback = None

def initialize_multi_agent_feedback(config: Dict[str, Any]) -> MultiAgentFeedback:
    """Initialize the global multi-agent feedback system."""
    global _multi_agent_feedback
    _multi_agent_feedback = MultiAgentFeedback(config)
    return _multi_agent_feedback

def get_multi_agent_feedback() -> Optional[MultiAgentFeedback]:
    """Get the global multi-agent feedback instance."""
    return _multi_agent_feedback

async def main():
    """Main function for multi-agent feedback system."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🤝 MULTI-AGENT FEEDBACK LOOP SYSTEM")
    print("=" * 50)
    print("Enabling Bidget and Bybit cross-agent learning...")
    print()
    
    # Initialize multi-agent feedback
    config = {
        'memory_sync_interval': 600,  # 10 minutes
        'consensus_tuning_interval': 1800,  # 30 minutes
        'trait_sharing_interval': 300,  # 5 minutes
        'reinforcement_threshold': 0.7,
        'consensus_weight': 0.6
    }
    
    feedback = initialize_multi_agent_feedback(config)
    await feedback.initialize_feedback_loop()
    
    print("🔄 [MEMORY_SYNC] Cross-agent memory synchronization active")
    print("⚖️ [CONSENSUS] Consensus-based parameter tuning enabled")
    print("🧬 [TRAIT_SHARE] Successful trait sharing between agents")
    print()
    print("Available commands:")
    print("  - /feedback status")
    print("  - /feedback force_memory_sync")
    print("  - /feedback consensus_tune")
    print("  - /feedback trait_share")
    
    try:
        while True:
            await asyncio.sleep(60)
            status = feedback.get_feedback_status()
            print(f"[STATUS] {datetime.now().strftime('%H:%M:%S')} - "
                  f"Traits: {status['trait_exchanges']} | "
                  f"Consensus: {status['consensus_decisions']} | "
                  f"Patterns: {status['shared_patterns']}")
    except KeyboardInterrupt:
        print("\n🛑 [SHUTDOWN] Multi-agent feedback system shutting down...")
        feedback.feedback_active = False

if __name__ == "__main__":
    asyncio.run(main())
