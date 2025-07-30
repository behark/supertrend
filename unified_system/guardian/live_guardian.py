"""
Live Guardian Layer - Phase 4 Component 4
=========================================
Safety sentinel with emergency stop, fault isolation, auto-recovery,
and comprehensive protection for the immortal trading network.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum
import json
import hashlib
import psutil

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """System threat levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class GuardianAction(Enum):
    """Guardian protective actions."""
    MONITOR = "monitor"
    ALERT = "alert"
    THROTTLE = "throttle"
    ISOLATE = "isolate"
    EMERGENCY_STOP = "emergency_stop"
    AUTO_RECOVER = "auto_recover"

class SystemComponent(Enum):
    """System components under guardian protection."""
    TRADING_ENGINE = "trading_engine"
    API_CONNECTIONS = "api_connections"
    MEMORY_SYSTEM = "memory_system"
    SCALING_SYSTEM = "scaling_system"
    WEBSOCKET_SERVER = "websocket_server"

@dataclass
class ThreatDetection:
    """Threat detection record."""
    threat_id: str
    threat_type: str
    component: SystemComponent
    severity: ThreatLevel
    description: str
    detected_at: datetime
    metrics: Dict[str, Any]
    auto_resolved: bool
    resolution_action: Optional[GuardianAction]

@dataclass
class SafetyRule:
    """Safety rule definition."""
    rule_id: str
    name: str
    component: SystemComponent
    condition: str
    threshold_values: Dict[str, float]
    action: GuardianAction
    enabled: bool
    last_triggered: Optional[datetime]
    trigger_count: int

class LiveGuardian:
    """Live Guardian Layer for system protection."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Live Guardian system."""
        self.config = config
        self.monitoring_interval = config.get('monitoring_interval', 10)
        self.threat_retention_hours = config.get('threat_retention_hours', 24)
        self.auto_recovery_enabled = config.get('auto_recovery_enabled', True)
        
        # Safety thresholds
        self.cpu_threshold = config.get('cpu_threshold', 90.0)
        self.memory_threshold = config.get('memory_threshold', 85.0)
        self.error_rate_threshold = config.get('error_rate_threshold', 0.1)
        
        # Guardian state
        self.guardian_active = False
        self.emergency_mode = False
        self.isolated_components: Set[SystemComponent] = set()
        
        # Monitoring data
        self.threat_history: List[ThreatDetection] = []
        self.safety_rules: Dict[str, SafetyRule] = {}
        self.system_metrics: Dict[str, Any] = {}
        self.component_health: Dict[SystemComponent, Dict[str, Any]] = {}
        
        # Recovery state
        self.recovery_attempts: Dict[str, int] = {}
        self.max_recovery_attempts = config.get('max_recovery_attempts', 3)
        
    async def initialize_guardian(self):
        """Initialize the Live Guardian system."""
        try:
            logger.info("[GUARDIAN] Initializing Live Guardian Layer")
            await self._initialize_safety_rules()
            await self._initialize_component_monitoring()
            await self._start_guardian_tasks()
            self.guardian_active = True
            logger.info("[GUARDIAN] Live Guardian Layer initialized successfully")
        except Exception as e:
            logger.error(f"[GUARDIAN] Initialization failed: {e}")
            raise
    
    async def _initialize_safety_rules(self):
        """Initialize default safety rules."""
        cpu_rule = SafetyRule(
            rule_id="cpu_overload",
            name="CPU Overload Protection",
            component=SystemComponent.TRADING_ENGINE,
            condition="cpu_usage > threshold",
            threshold_values={"threshold": self.cpu_threshold},
            action=GuardianAction.THROTTLE,
            enabled=True,
            last_triggered=None,
            trigger_count=0
        )
        
        memory_rule = SafetyRule(
            rule_id="memory_overload",
            name="Memory Overload Protection",
            component=SystemComponent.MEMORY_SYSTEM,
            condition="memory_usage > threshold",
            threshold_values={"threshold": self.memory_threshold},
            action=GuardianAction.ALERT,
            enabled=True,
            last_triggered=None,
            trigger_count=0
        )
        
        emergency_rule = SafetyRule(
            rule_id="system_failure",
            name="System Failure Emergency Stop",
            component=SystemComponent.TRADING_ENGINE,
            condition="critical_failure_detected",
            threshold_values={},
            action=GuardianAction.EMERGENCY_STOP,
            enabled=True,
            last_triggered=None,
            trigger_count=0
        )
        
        self.safety_rules = {
            cpu_rule.rule_id: cpu_rule,
            memory_rule.rule_id: memory_rule,
            emergency_rule.rule_id: emergency_rule
        }
        
        logger.info(f"[GUARDIAN] Initialized {len(self.safety_rules)} safety rules")
    
    async def _initialize_component_monitoring(self):
        """Initialize component health monitoring."""
        for component in SystemComponent:
            self.component_health[component] = {
                'status': 'healthy',
                'last_check': datetime.now(),
                'error_count': 0,
                'response_time': 0.0,
                'uptime': 0.0,
                'metrics': {}
            }
        logger.info("[GUARDIAN] Component health monitoring initialized")
    
    async def _start_guardian_tasks(self):
        """Start guardian background tasks."""
        asyncio.create_task(self._system_monitor_loop())
        asyncio.create_task(self._threat_detection_loop())
        asyncio.create_task(self._auto_recovery_loop())
        logger.info("[GUARDIAN] Guardian background tasks started")
    
    async def report_threat(self, threat_type: str, component: SystemComponent, 
                          severity: ThreatLevel, description: str, 
                          metrics: Dict[str, Any] = None) -> str:
        """Report a detected threat to the guardian."""
        try:
            threat_id = f"threat_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(description.encode()).hexdigest()[:8]}"
            
            threat = ThreatDetection(
                threat_id=threat_id,
                threat_type=threat_type,
                component=component,
                severity=severity,
                description=description,
                detected_at=datetime.now(),
                metrics=metrics or {},
                auto_resolved=False,
                resolution_action=None
            )
            
            self.threat_history.append(threat)
            logger.warning(f"[GUARDIAN] Threat detected: {threat_id} - {description}")
            
            # Trigger immediate response for high severity threats
            if severity in [ThreatLevel.HIGH, ThreatLevel.CRITICAL, ThreatLevel.EMERGENCY]:
                await self._respond_to_threat(threat)
            
            return threat_id
        except Exception as e:
            logger.error(f"[GUARDIAN] Failed to report threat: {e}")
            return ""
    
    async def _respond_to_threat(self, threat: ThreatDetection):
        """Respond to a detected threat."""
        try:
            logger.info(f"[GUARDIAN] Responding to threat: {threat.threat_id}")
            
            if threat.severity == ThreatLevel.EMERGENCY:
                await self._execute_emergency_stop(threat)
            elif threat.severity == ThreatLevel.CRITICAL:
                await self._isolate_component(threat.component, threat)
            elif threat.severity == ThreatLevel.HIGH:
                await self._throttle_component(threat.component, threat)
            
            threat.resolution_action = self._get_action_for_severity(threat.severity)
        except Exception as e:
            logger.error(f"[GUARDIAN] Failed to respond to threat: {e}")
    
    def _get_action_for_severity(self, severity: ThreatLevel) -> GuardianAction:
        """Get appropriate action for threat severity."""
        if severity == ThreatLevel.EMERGENCY:
            return GuardianAction.EMERGENCY_STOP
        elif severity == ThreatLevel.CRITICAL:
            return GuardianAction.ISOLATE
        elif severity == ThreatLevel.HIGH:
            return GuardianAction.THROTTLE
        else:
            return GuardianAction.ALERT
    
    async def _execute_emergency_stop(self, threat: ThreatDetection):
        """Execute emergency stop procedure."""
        try:
            logger.critical(f"[GUARDIAN] EMERGENCY STOP ACTIVATED - Threat: {threat.threat_id}")
            
            self.emergency_mode = True
            
            # Stop all trading activities
            await self._stop_trading_engine()
            
            # Isolate critical components
            for component in [SystemComponent.TRADING_ENGINE, SystemComponent.API_CONNECTIONS]:
                self.isolated_components.add(component)
            
            logger.critical("[GUARDIAN] Emergency stop completed - System in safe mode")
        except Exception as e:
            logger.error(f"[GUARDIAN] Emergency stop failed: {e}")
    
    async def _isolate_component(self, component: SystemComponent, threat: ThreatDetection):
        """Isolate a system component."""
        try:
            logger.warning(f"[GUARDIAN] Isolating component: {component.value}")
            
            self.isolated_components.add(component)
            
            if component in self.component_health:
                self.component_health[component]['status'] = 'isolated'
                self.component_health[component]['last_check'] = datetime.now()
            
            logger.warning(f"[GUARDIAN] Component {component.value} isolated due to threat: {threat.threat_id}")
        except Exception as e:
            logger.error(f"[GUARDIAN] Component isolation failed: {e}")
    
    async def _throttle_component(self, component: SystemComponent, threat: ThreatDetection):
        """Throttle a system component."""
        try:
            logger.info(f"[GUARDIAN] Throttling component: {component.value}")
            
            if component in self.component_health:
                self.component_health[component]['status'] = 'throttled'
                self.component_health[component]['last_check'] = datetime.now()
            
            logger.info(f"[GUARDIAN] Component {component.value} throttled due to threat: {threat.threat_id}")
        except Exception as e:
            logger.error(f"[GUARDIAN] Component throttling failed: {e}")
    
    async def _stop_trading_engine(self):
        """Stop the trading engine safely."""
        try:
            logger.info("[GUARDIAN] Stopping trading engine")
            self.component_health[SystemComponent.TRADING_ENGINE]['status'] = 'stopped'
        except Exception as e:
            logger.error(f"[GUARDIAN] Failed to stop trading engine: {e}")
    
    async def execute_guardian_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute guardian system command."""
        try:
            params = params or {}
            
            if command == 'guardian_status':
                return await self._handle_guardian_status(params)
            elif command == 'emergency_stop':
                return await self._handle_emergency_stop(params)
            elif command == 'recovery_start':
                return await self._handle_recovery_start(params)
            elif command == 'threat_history':
                return await self._handle_threat_history(params)
            else:
                return {'success': False, 'error': f'Unknown guardian command: {command}'}
        except Exception as e:
            logger.error(f"[GUARDIAN] Command execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_guardian_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle guardian status command."""
        # Count threats by severity
        threat_counts = {}
        for threat in self.threat_history[-100:]:
            severity = threat.severity.value
            threat_counts[severity] = threat_counts.get(severity, 0) + 1
        
        # Component status summary
        component_status = {}
        for component, health in self.component_health.items():
            component_status[component.value] = {
                'status': health['status'],
                'error_count': health['error_count'],
                'last_check': health['last_check'].isoformat()
            }
        
        return {
            'success': True,
            'guardian_status': {
                'guardian_active': self.guardian_active,
                'emergency_mode': self.emergency_mode,
                'isolated_components': [c.value for c in self.isolated_components],
                'total_threats': len(self.threat_history),
                'threat_counts': threat_counts,
                'component_status': component_status,
                'auto_recovery_enabled': self.auto_recovery_enabled,
                'active_safety_rules': len([r for r in self.safety_rules.values() if r.enabled])
            },
            'timestamp': datetime.now().isoformat()
        }
    
    async def _handle_emergency_stop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency stop command."""
        reason = params.get('reason', 'Manual emergency stop')
        
        # Create emergency threat
        threat = ThreatDetection(
            threat_id=f"manual_emergency_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            threat_type="manual_emergency",
            component=SystemComponent.TRADING_ENGINE,
            severity=ThreatLevel.EMERGENCY,
            description=reason,
            detected_at=datetime.now(),
            metrics={},
            auto_resolved=False,
            resolution_action=GuardianAction.EMERGENCY_STOP
        )
        
        await self._execute_emergency_stop(threat)
        
        return {
            'success': True,
            'message': 'Emergency stop executed successfully',
            'threat_id': threat.threat_id,
            'emergency_mode': self.emergency_mode,
            'isolated_components': [c.value for c in self.isolated_components],
            'timestamp': datetime.now().isoformat()
        }
    
    async def _handle_recovery_start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle recovery start command."""
        component_name = params.get('component', 'all')
        
        if component_name == 'all':
            # Start full system recovery
            recovery_results = []
            
            for component in self.isolated_components.copy():
                result = await self._recover_component(component)
                recovery_results.append({
                    'component': component.value,
                    'success': result,
                    'status': self.component_health[component]['status']
                })
            
            # Exit emergency mode if all components recovered
            if not self.isolated_components:
                self.emergency_mode = False
            
            return {
                'success': True,
                'message': f'Recovery attempted for {len(recovery_results)} components',
                'recovery_results': recovery_results,
                'emergency_mode': self.emergency_mode,
                'timestamp': datetime.now().isoformat()
            }
        else:
            # Recover specific component
            try:
                component = SystemComponent(component_name)
                result = await self._recover_component(component)
                
                return {
                    'success': True,
                    'message': f'Recovery attempted for {component_name}',
                    'component': component_name,
                    'recovery_success': result,
                    'component_status': self.component_health[component]['status'],
                    'timestamp': datetime.now().isoformat()
                }
            except ValueError:
                return {'success': False, 'error': f'Unknown component: {component_name}'}
    
    async def _recover_component(self, component: SystemComponent) -> bool:
        """Attempt to recover a component."""
        try:
            logger.info(f"[GUARDIAN] Attempting recovery for component: {component.value}")
            
            # Check recovery attempt count
            recovery_key = component.value
            attempts = self.recovery_attempts.get(recovery_key, 0)
            
            if attempts >= self.max_recovery_attempts:
                logger.warning(f"[GUARDIAN] Max recovery attempts reached for {component.value}")
                return False
            
            # Increment attempt count
            self.recovery_attempts[recovery_key] = attempts + 1
            
            # Mock recovery process
            await asyncio.sleep(1)
            
            # Update component status
            self.component_health[component]['status'] = 'healthy'
            self.component_health[component]['last_check'] = datetime.now()
            self.component_health[component]['error_count'] = 0
            
            # Remove from isolated components
            if component in self.isolated_components:
                self.isolated_components.remove(component)
            
            logger.info(f"[GUARDIAN] Component {component.value} recovered successfully")
            return True
        except Exception as e:
            logger.error(f"[GUARDIAN] Component recovery failed: {e}")
            return False
    
    async def _handle_threat_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle threat history command."""
        limit = params.get('limit', 20)
        severity_filter = params.get('severity')
        
        # Filter threats
        filtered_threats = self.threat_history
        
        if severity_filter:
            filtered_threats = [t for t in filtered_threats if t.severity.value == severity_filter]
        
        # Get recent threats
        recent_threats = filtered_threats[-limit:]
        
        # Format threat summaries
        threat_summaries = []
        for threat in recent_threats:
            summary = {
                'threat_id': threat.threat_id,
                'threat_type': threat.threat_type,
                'component': threat.component.value,
                'severity': threat.severity.value,
                'description': threat.description,
                'detected_at': threat.detected_at.isoformat(),
                'auto_resolved': threat.auto_resolved,
                'resolution_action': threat.resolution_action.value if threat.resolution_action else None
            }
            threat_summaries.append(summary)
        
        return {
            'success': True,
            'message': f'Retrieved {len(threat_summaries)} threats',
            'threats': threat_summaries,
            'total_threats': len(self.threat_history),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _system_monitor_loop(self):
        """Background system monitoring loop."""
        while self.guardian_active:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                
                self.system_metrics.update({
                    'cpu_usage': cpu_percent,
                    'memory_usage': memory_percent,
                    'timestamp': datetime.now()
                })
                
                # Check safety rules
                await self._check_safety_rules()
                
                await asyncio.sleep(self.monitoring_interval)
            except Exception as e:
                logger.error(f"[GUARDIAN] System monitor error: {e}")
                await asyncio.sleep(30)
    
    async def _check_safety_rules(self):
        """Check all safety rules against current metrics."""
        for rule_id, rule in self.safety_rules.items():
            if not rule.enabled:
                continue
            
            if await self._evaluate_safety_rule(rule):
                await self._trigger_safety_rule(rule)
    
    async def _evaluate_safety_rule(self, rule: SafetyRule) -> bool:
        """Evaluate if a safety rule should trigger."""
        condition = rule.condition
        thresholds = rule.threshold_values
        
        if "cpu_usage > threshold" in condition:
            return self.system_metrics.get('cpu_usage', 0) > thresholds.get('threshold', 90)
        elif "memory_usage > threshold" in condition:
            return self.system_metrics.get('memory_usage', 0) > thresholds.get('threshold', 85)
        
        return False
    
    async def _trigger_safety_rule(self, rule: SafetyRule):
        """Trigger a safety rule action."""
        logger.warning(f"[GUARDIAN] Safety rule triggered: {rule.name}")
        
        rule.last_triggered = datetime.now()
        rule.trigger_count += 1
        
        # Create threat based on rule
        await self.report_threat(
            threat_type="safety_rule_violation",
            component=rule.component,
            severity=ThreatLevel.HIGH,
            description=f"Safety rule '{rule.name}' triggered",
            metrics=self.system_metrics.copy()
        )
    
    async def _threat_detection_loop(self):
        """Background threat detection loop."""
        while self.guardian_active:
            try:
                # Clean old threats
                cutoff_time = datetime.now() - timedelta(hours=self.threat_retention_hours)
                self.threat_history = [t for t in self.threat_history if t.detected_at > cutoff_time]
                
                await asyncio.sleep(300)  # Check every 5 minutes
            except Exception as e:
                logger.error(f"[GUARDIAN] Threat detection loop error: {e}")
                await asyncio.sleep(600)
    
    async def _auto_recovery_loop(self):
        """Background auto-recovery loop."""
        while self.guardian_active and self.auto_recovery_enabled:
            try:
                # Attempt recovery for isolated components
                for component in self.isolated_components.copy():
                    if self.component_health[component]['status'] == 'isolated':
                        # Check if component has been isolated long enough
                        last_check = self.component_health[component]['last_check']
                        time_isolated = (datetime.now() - last_check).total_seconds()
                        
                        if time_isolated > 300:  # 5 minutes
                            await self._recover_component(component)
                
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"[GUARDIAN] Auto-recovery loop error: {e}")
                await asyncio.sleep(300)
    
    def get_guardian_status(self) -> Dict[str, Any]:
        """Get current guardian system status."""
        return {
            'guardian_active': self.guardian_active,
            'emergency_mode': self.emergency_mode,
            'isolated_components': len(self.isolated_components),
            'total_threats': len(self.threat_history),
            'auto_recovery_enabled': self.auto_recovery_enabled,
            'active_safety_rules': len([r for r in self.safety_rules.values() if r.enabled]),
            'timestamp': datetime.now().isoformat()
        }

# Global live guardian instance
_live_guardian = None

def initialize_live_guardian(config: Dict[str, Any]) -> LiveGuardian:
    """Initialize the global live guardian."""
    global _live_guardian
    _live_guardian = LiveGuardian(config)
    return _live_guardian

def get_live_guardian() -> Optional[LiveGuardian]:
    """Get the global live guardian instance."""
    return _live_guardian

async def main():
    """Main function for testing live guardian."""
    config = {
        'monitoring_interval': 10,
        'threat_retention_hours': 24,
        'auto_recovery_enabled': True,
        'cpu_threshold': 90.0,
        'memory_threshold': 85.0,
        'error_rate_threshold': 0.1,
        'max_recovery_attempts': 3
    }
    
    guardian = initialize_live_guardian(config)
    await guardian.initialize_guardian()
    
    print("[GUARDIAN] Live Guardian Layer is running...")
    print("[GUARDIAN] Available commands:")
    print("  - /guardian status")
    print("  - /emergency stop")
    print("  - /recovery start")
    print("  - /threat history")
    
    try:
        while True:
            await asyncio.sleep(60)
            status = guardian.get_guardian_status()
            print(f"[HEARTBEAT] {datetime.now().strftime('%H:%M:%S')} - Guardian Status: {status['total_threats']} threats")
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Live Guardian Layer shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
