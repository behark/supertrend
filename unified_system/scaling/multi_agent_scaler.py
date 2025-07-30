"""
Multi-Agent Scaling System - Phase 4 Component 3
==============================================
Architecture for onboarding new agents, smart routing, load balancing,
and horizontal scaling for the immortal trading network.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import uuid

logger = logging.getLogger(__name__)

class AgentStatus(Enum):
    """Agent operational status."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    IDLE = "idle"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"

class LoadBalanceStrategy(Enum):
    """Load balancing strategies."""
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    PERFORMANCE_BASED = "performance_based"

@dataclass
class AgentCapability:
    """Agent capability definition."""
    capability_id: str
    name: str
    description: str
    specializations: List[str]

@dataclass
class AgentProfile:
    """Complete agent profile for scaling system."""
    agent_id: str
    agent_name: str
    agent_type: str
    capabilities: List[AgentCapability]
    current_load: float
    max_capacity: float
    performance_score: float
    status: AgentStatus
    last_heartbeat: datetime
    specializations: List[str]
    metadata: Dict[str, Any]

@dataclass
class ScalingRule:
    """Auto-scaling rule definition."""
    rule_id: str
    name: str
    trigger_condition: str
    action: str
    parameters: Dict[str, Any]
    cooldown_seconds: int
    enabled: bool
    last_triggered: Optional[datetime]

class MultiAgentScaler:
    """Multi-agent scaling and orchestration system."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Multi-Agent Scaler."""
        self.config = config
        self.max_agents = config.get('max_agents', 50)
        self.load_threshold_scale_up = config.get('load_threshold_scale_up', 0.8)
        self.load_threshold_scale_down = config.get('load_threshold_scale_down', 0.3)
        self.heartbeat_timeout_seconds = config.get('heartbeat_timeout_seconds', 60)
        self.default_strategy = LoadBalanceStrategy(config.get('default_strategy', 'least_loaded'))
        
        # Agent registry
        self.registered_agents: Dict[str, AgentProfile] = {}
        self.routing_table: Dict[str, List[str]] = {}  # capability -> agent_ids
        self.load_balancer_state: Dict[str, Any] = {}
        self.scaling_rules: Dict[str, ScalingRule] = {}
        
        # System state
        self.scaler_active = False
        self.auto_scaling_enabled = config.get('auto_scaling_enabled', True)
        
    async def initialize_scaler(self):
        """Initialize the multi-agent scaling system."""
        try:
            logger.info("[SCALER] Initializing Multi-Agent Scaling System")
            await self._initialize_default_scaling_rules()
            await self._start_background_tasks()
            self.scaler_active = True
            logger.info("[SCALER] Multi-Agent Scaling System initialized successfully")
        except Exception as e:
            logger.error(f"[SCALER] Initialization failed: {e}")
            raise
    
    async def _initialize_default_scaling_rules(self):
        """Initialize default auto-scaling rules."""
        scale_up_rule = ScalingRule(
            rule_id="scale_up_load",
            name="Scale Up on High Load",
            trigger_condition="average_load > 0.8",
            action="scale_up",
            parameters={"min_agents": 1, "max_agents": 3},
            cooldown_seconds=300,
            enabled=True,
            last_triggered=None
        )
        
        scale_down_rule = ScalingRule(
            rule_id="scale_down_load",
            name="Scale Down on Low Load",
            trigger_condition="average_load < 0.3",
            action="scale_down",
            parameters={"min_agents": 1},
            cooldown_seconds=600,
            enabled=True,
            last_triggered=None
        )
        
        self.scaling_rules = {
            scale_up_rule.rule_id: scale_up_rule,
            scale_down_rule.rule_id: scale_down_rule
        }
        
        logger.info(f"[SCALER] Initialized {len(self.scaling_rules)} default scaling rules")
    
    async def _start_background_tasks(self):
        """Start background scaling and monitoring tasks."""
        asyncio.create_task(self._agent_health_monitor())
        asyncio.create_task(self._auto_scaling_loop())
        logger.info("[SCALER] Background scaling tasks started")
    
    async def register_agent(self, agent_profile: AgentProfile) -> bool:
        """Register a new agent with the scaling system."""
        try:
            logger.info(f"[SCALER] Registering agent: {agent_profile.agent_id}")
            
            if len(self.registered_agents) >= self.max_agents:
                logger.warning(f"[SCALER] Maximum agent capacity reached ({self.max_agents})")
                return False
            
            # Register agent
            self.registered_agents[agent_profile.agent_id] = agent_profile
            
            # Update capability routing
            await self._update_capability_routing(agent_profile)
            
            # Initialize load balancer state
            self.load_balancer_state[agent_profile.agent_id] = {
                'last_assigned': datetime.now(),
                'assignment_count': 0
            }
            
            logger.info(f"[SCALER] Agent {agent_profile.agent_id} registered successfully")
            return True
        except Exception as e:
            logger.error(f"[SCALER] Agent registration failed: {e}")
            return False
    
    async def _update_capability_routing(self, agent_profile: AgentProfile):
        """Update routing table with agent capabilities."""
        for capability in agent_profile.capabilities:
            capability_id = capability.capability_id
            
            if capability_id not in self.routing_table:
                self.routing_table[capability_id] = []
            
            if agent_profile.agent_id not in self.routing_table[capability_id]:
                self.routing_table[capability_id].append(agent_profile.agent_id)
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the scaling system."""
        try:
            logger.info(f"[SCALER] Unregistering agent: {agent_id}")
            
            if agent_id not in self.registered_agents:
                return False
            
            # Remove from routing table
            for capability_id, agent_list in self.routing_table.items():
                if agent_id in agent_list:
                    agent_list.remove(agent_id)
            
            # Clean up
            self.routing_table = {k: v for k, v in self.routing_table.items() if v}
            del self.registered_agents[agent_id]
            
            if agent_id in self.load_balancer_state:
                del self.load_balancer_state[agent_id]
            
            logger.info(f"[SCALER] Agent {agent_id} unregistered successfully")
            return True
        except Exception as e:
            logger.error(f"[SCALER] Agent unregistration failed: {e}")
            return False
    
    async def route_request(self, capability_required: str, request_data: Dict[str, Any], 
                          strategy: Optional[LoadBalanceStrategy] = None) -> Optional[str]:
        """Route request to best available agent."""
        try:
            strategy = strategy or self.default_strategy
            
            # Get agents with required capability
            candidate_agents = self.routing_table.get(capability_required, [])
            
            if not candidate_agents:
                logger.warning(f"[SCALER] No agents available for capability: {capability_required}")
                return None
            
            # Filter active agents
            active_agents = [
                agent_id for agent_id in candidate_agents
                if (agent_id in self.registered_agents and 
                    self.registered_agents[agent_id].status == AgentStatus.ACTIVE)
            ]
            
            if not active_agents:
                return None
            
            # Select agent based on strategy
            selected_agent = await self._select_agent_by_strategy(active_agents, strategy)
            
            if selected_agent:
                # Update load balancer state
                self.load_balancer_state[selected_agent]['last_assigned'] = datetime.now()
                self.load_balancer_state[selected_agent]['assignment_count'] += 1
                
                # Update agent load
                if selected_agent in self.registered_agents:
                    self.registered_agents[selected_agent].current_load += 0.1
            
            return selected_agent
        except Exception as e:
            logger.error(f"[SCALER] Request routing failed: {e}")
            return None
    
    async def _select_agent_by_strategy(self, candidate_agents: List[str], 
                                      strategy: LoadBalanceStrategy) -> Optional[str]:
        """Select agent based on load balancing strategy."""
        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return await self._round_robin_selection(candidate_agents)
        elif strategy == LoadBalanceStrategy.LEAST_LOADED:
            return await self._least_loaded_selection(candidate_agents)
        elif strategy == LoadBalanceStrategy.PERFORMANCE_BASED:
            return await self._performance_based_selection(candidate_agents)
        else:
            return await self._least_loaded_selection(candidate_agents)
    
    async def _round_robin_selection(self, candidates: List[str]) -> str:
        """Round-robin agent selection."""
        if not hasattr(self, '_round_robin_index'):
            self._round_robin_index = 0
        
        selected = candidates[self._round_robin_index % len(candidates)]
        self._round_robin_index += 1
        return selected
    
    async def _least_loaded_selection(self, candidates: List[str]) -> str:
        """Select agent with lowest current load."""
        min_load = float('inf')
        selected_agent = candidates[0]
        
        for agent_id in candidates:
            if agent_id in self.registered_agents:
                current_load = self.registered_agents[agent_id].current_load
                if current_load < min_load:
                    min_load = current_load
                    selected_agent = agent_id
        
        return selected_agent
    
    async def _performance_based_selection(self, candidates: List[str]) -> str:
        """Select agent with highest performance score."""
        max_performance = 0.0
        selected_agent = candidates[0]
        
        for agent_id in candidates:
            if agent_id in self.registered_agents:
                performance = self.registered_agents[agent_id].performance_score
                if performance > max_performance:
                    max_performance = performance
                    selected_agent = agent_id
        
        return selected_agent
    
    async def execute_scaling_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute scaling system command."""
        try:
            params = params or {}
            
            if command == 'scale_status':
                return await self._handle_scale_status(params)
            elif command == 'scale_up':
                return await self._handle_scale_up(params)
            elif command == 'scale_down':
                return await self._handle_scale_down(params)
            elif command == 'agent_list':
                return await self._handle_agent_list(params)
            else:
                return {'success': False, 'error': f'Unknown scaling command: {command}'}
        except Exception as e:
            logger.error(f"[SCALER] Command execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_scale_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scaling status command."""
        total_agents = len(self.registered_agents)
        active_agents = len([a for a in self.registered_agents.values() if a.status == AgentStatus.ACTIVE])
        
        average_load = 0.0
        average_performance = 0.0
        
        if self.registered_agents:
            average_load = sum(a.current_load for a in self.registered_agents.values()) / total_agents
            average_performance = sum(a.performance_score for a in self.registered_agents.values()) / total_agents
        
        return {
            'success': True,
            'scaling_status': {
                'total_agents': total_agents,
                'active_agents': active_agents,
                'max_agents': self.max_agents,
                'average_load': average_load,
                'average_performance': average_performance,
                'auto_scaling_enabled': self.auto_scaling_enabled,
                'capabilities_available': len(self.routing_table)
            },
            'timestamp': datetime.now().isoformat()
        }
    
    async def _handle_scale_up(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scale up command."""
        target_agents = params.get('target_agents', 1)
        capability_type = params.get('capability_type', 'general')
        
        logger.info(f"[SCALER] Scaling up {target_agents} agents")
        
        current_count = len(self.registered_agents)
        if current_count + target_agents > self.max_agents:
            return {
                'success': False,
                'error': f'Would exceed maximum agents limit ({self.max_agents})',
                'current_agents': current_count
            }
        
        # Mock scaling up
        scaled_agents = []
        for i in range(target_agents):
            new_agent_id = f"scaled_agent_{uuid.uuid4().hex[:8]}"
            
            mock_profile = AgentProfile(
                agent_id=new_agent_id,
                agent_name=f"Scaled Agent {i+1}",
                agent_type="trading_bot",
                capabilities=[
                    AgentCapability(
                        capability_id=capability_type,
                        name=f"{capability_type.title()} Trading",
                        description=f"Automated {capability_type} trading capability",
                        specializations=[capability_type]
                    )
                ],
                current_load=0.0,
                max_capacity=1.0,
                performance_score=0.75,
                status=AgentStatus.ACTIVE,
                last_heartbeat=datetime.now(),
                specializations=[capability_type],
                metadata={'scaled_up': True, 'created_at': datetime.now().isoformat()}
            )
            
            if await self.register_agent(mock_profile):
                scaled_agents.append(new_agent_id)
        
        return {
            'success': True,
            'message': f'Successfully scaled up {len(scaled_agents)} agents',
            'scaled_agents': scaled_agents,
            'total_agents': len(self.registered_agents),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _handle_scale_down(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scale down command."""
        target_agents = params.get('target_agents', 1)
        
        logger.info(f"[SCALER] Scaling down {target_agents} agents")
        
        # Get candidates for removal (scaled agents only)
        candidates = []
        for agent_id, agent in self.registered_agents.items():
            if agent.metadata.get('scaled_up', False):
                candidates.append((agent_id, agent.current_load))
        
        if not candidates:
            return {
                'success': False,
                'error': 'No scalable agents available for removal',
                'total_agents': len(self.registered_agents)
            }
        
        # Sort by load (ascending) to remove least loaded first
        candidates.sort(key=lambda x: x[1])
        
        # Remove agents
        removed_agents = []
        for i in range(min(target_agents, len(candidates))):
            agent_id = candidates[i][0]
            if await self.unregister_agent(agent_id):
                removed_agents.append(agent_id)
        
        return {
            'success': True,
            'message': f'Successfully scaled down {len(removed_agents)} agents',
            'removed_agents': removed_agents,
            'total_agents': len(self.registered_agents),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _handle_agent_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent list command."""
        status_filter = params.get('status')
        
        # Filter agents
        filtered_agents = []
        for agent_id, agent in self.registered_agents.items():
            if status_filter and agent.status.value != status_filter:
                continue
            
            agent_summary = {
                'agent_id': agent.agent_id,
                'agent_name': agent.agent_name,
                'agent_type': agent.agent_type,
                'status': agent.status.value,
                'current_load': agent.current_load,
                'performance_score': agent.performance_score,
                'capabilities': [c.capability_id for c in agent.capabilities],
                'last_heartbeat': agent.last_heartbeat.isoformat()
            }
            
            filtered_agents.append(agent_summary)
        
        return {
            'success': True,
            'message': f'Found {len(filtered_agents)} agents',
            'agents': filtered_agents,
            'total_registered': len(self.registered_agents),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _agent_health_monitor(self):
        """Background agent health monitoring."""
        while self.scaler_active:
            try:
                current_time = datetime.now()
                
                for agent_id, agent in self.registered_agents.items():
                    time_since_heartbeat = (current_time - agent.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > self.heartbeat_timeout_seconds:
                        if agent.status != AgentStatus.OFFLINE:
                            logger.warning(f"[SCALER] Agent {agent_id} heartbeat timeout")
                            agent.status = AgentStatus.OFFLINE
                
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                logger.error(f"[SCALER] Health monitor error: {e}")
                await asyncio.sleep(60)
    
    async def _auto_scaling_loop(self):
        """Background auto-scaling loop."""
        while self.scaler_active and self.auto_scaling_enabled:
            try:
                # Check scaling rules
                for rule_id, rule in self.scaling_rules.items():
                    if not rule.enabled:
                        continue
                    
                    # Check cooldown
                    if rule.last_triggered:
                        time_since_trigger = (datetime.now() - rule.last_triggered).total_seconds()
                        if time_since_trigger < rule.cooldown_seconds:
                            continue
                    
                    # Evaluate trigger condition
                    if await self._evaluate_scaling_condition(rule):
                        await self._execute_scaling_action(rule)
                        rule.last_triggered = datetime.now()
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"[SCALER] Auto-scaling loop error: {e}")
                await asyncio.sleep(300)
    
    async def _evaluate_scaling_condition(self, rule: ScalingRule) -> bool:
        """Evaluate if scaling rule condition is met."""
        if not self.registered_agents:
            return False
        
        total_agents = len(self.registered_agents)
        average_load = sum(a.current_load for a in self.registered_agents.values()) / total_agents
        
        condition = rule.trigger_condition
        
        if "average_load > 0.8" in condition:
            return average_load > 0.8
        elif "average_load < 0.3" in condition:
            return average_load < 0.3
        
        return False
    
    async def _execute_scaling_action(self, rule: ScalingRule):
        """Execute scaling action based on rule."""
        action = rule.action
        params = rule.parameters
        
        logger.info(f"[SCALER] Executing scaling action: {action}")
        
        if action == "scale_up":
            target = params.get('min_agents', 1)
            await self._handle_scale_up({'target_agents': target})
        elif action == "scale_down":
            target = 1
            await self._handle_scale_down({'target_agents': target})
    
    def get_scaler_status(self) -> Dict[str, Any]:
        """Get current scaler system status."""
        return {
            'scaler_active': self.scaler_active,
            'total_agents': len(self.registered_agents),
            'auto_scaling_enabled': self.auto_scaling_enabled,
            'max_agents': self.max_agents,
            'active_rules': len([r for r in self.scaling_rules.values() if r.enabled]),
            'timestamp': datetime.now().isoformat()
        }

# Global multi-agent scaler instance
_multi_agent_scaler = None

def initialize_multi_agent_scaler(config: Dict[str, Any]) -> MultiAgentScaler:
    """Initialize the global multi-agent scaler."""
    global _multi_agent_scaler
    _multi_agent_scaler = MultiAgentScaler(config)
    return _multi_agent_scaler

def get_multi_agent_scaler() -> Optional[MultiAgentScaler]:
    """Get the global multi-agent scaler instance."""
    return _multi_agent_scaler

async def main():
    """Main function for testing multi-agent scaler."""
    config = {
        'max_agents': 50,
        'load_threshold_scale_up': 0.8,
        'load_threshold_scale_down': 0.3,
        'heartbeat_timeout_seconds': 60,
        'default_strategy': 'least_loaded',
        'auto_scaling_enabled': True
    }
    
    scaler = initialize_multi_agent_scaler(config)
    await scaler.initialize_scaler()
    
    print("[SCALER] Multi-Agent Scaling System is running...")
    print("[SCALER] Available commands:")
    print("  - /scale status")
    print("  - /scale up")
    print("  - /scale down")
    print("  - /agent list")
    
    try:
        while True:
            await asyncio.sleep(60)
            status = scaler.get_scaler_status()
            print(f"[HEARTBEAT] {datetime.now().strftime('%H:%M:%S')} - Scaler Status: {status['total_agents']} agents")
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Multi-Agent Scaling System shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
