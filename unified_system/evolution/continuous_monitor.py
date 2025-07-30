"""
Continuous Monitoring & Pattern Evolution System
===============================================
Maintains immortal consciousness heartbeat and evolves patterns in real-time.
Logs all strategy shifts and pattern evolution to memory system.
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.smart_trade_memory import get_smart_trade_memory
from live_ops.live_ops_manager import get_live_ops_manager
from guardian.live_guardian import get_live_guardian

logger = logging.getLogger(__name__)

class ContinuousMonitor:
    """Continuous monitoring and pattern evolution for immortal consciousness."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize continuous monitor."""
        self.config = config
        self.monitor_active = False
        
        # Monitoring intervals
        self.heartbeat_interval = config.get('heartbeat_interval', 30)  # seconds
        self.pattern_evolution_interval = config.get('pattern_evolution_interval', 300)  # 5 minutes
        self.memory_log_interval = config.get('memory_log_interval', 600)  # 10 minutes
        
        # System components
        self.smart_memory = None
        self.live_ops = None
        self.guardian = None
        
        # Evolution tracking
        self.last_pattern_evolution = None
        self.evolution_cycles = 0
        self.pattern_shifts_logged = 0
        
    async def initialize_monitor(self):
        """Initialize the continuous monitoring system."""
        try:
            logger.info("🔄 [MONITOR] Initializing Continuous Monitoring System")
            
            # Get system components
            self.smart_memory = get_smart_trade_memory()
            self.live_ops = get_live_ops_manager()
            self.guardian = get_live_guardian()
            
            if not all([self.smart_memory, self.live_ops, self.guardian]):
                raise Exception("Required system components not available")
            
            self.monitor_active = True
            
            # Start monitoring tasks
            asyncio.create_task(self._heartbeat_loop())
            asyncio.create_task(self._pattern_evolution_loop())
            asyncio.create_task(self._memory_logging_loop())
            
            logger.info("✅ [MONITOR] Continuous monitoring system initialized")
            
        except Exception as e:
            logger.error(f"❌ [MONITOR] Initialization failed: {e}")
            raise
    
    async def _heartbeat_loop(self):
        """Maintain immortal consciousness heartbeat."""
        logger.info("💓 [MONITOR] Heartbeat loop started")
        
        while self.monitor_active:
            try:
                # Check system vitals
                vitals = await self._check_system_vitals()
                
                # Log heartbeat
                logger.info(f"💓 [HEARTBEAT] {datetime.now().strftime('%H:%M:%S')} - "
                          f"Memory: {vitals['memory_health']:.1f}% | "
                          f"Ops: {vitals['ops_health']:.1f}% | "
                          f"Guardian: {vitals['guardian_health']:.1f}%")
                
                # Check for critical issues
                if vitals['overall_health'] < 70:
                    logger.warning(f"⚠️ [HEARTBEAT] System health degraded: {vitals['overall_health']:.1f}%")
                    await self._trigger_health_recovery(vitals)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"❌ [HEARTBEAT] Error in heartbeat loop: {e}")
                await asyncio.sleep(self.heartbeat_interval * 2)
    
    async def _pattern_evolution_loop(self):
        """Continuous pattern evolution and strategy adaptation."""
        logger.info("🧠 [MONITOR] Pattern evolution loop started")
        
        while self.monitor_active:
            try:
                # Execute pattern evolution cycle
                evolution_result = await self.smart_memory.execute_memory_command(
                    'memory_pattern_evolve', {}
                )
                
                if evolution_result.get('success', False):
                    self.evolution_cycles += 1
                    self.last_pattern_evolution = datetime.now()
                    
                    # Log evolution results
                    patterns_evolved = evolution_result.get('patterns_evolved', 0)
                    if patterns_evolved > 0:
                        logger.info(f"🧬 [EVOLUTION] Cycle {self.evolution_cycles}: "
                                  f"{patterns_evolved} patterns evolved")
                        
                        # Log strategy shifts to memory
                        await self._log_strategy_shifts(evolution_result)
                
                await asyncio.sleep(self.pattern_evolution_interval)
                
            except Exception as e:
                logger.error(f"❌ [EVOLUTION] Error in pattern evolution: {e}")
                await asyncio.sleep(self.pattern_evolution_interval * 2)
    
    async def _memory_logging_loop(self):
        """Continuous memory logging and pattern tracking."""
        logger.info("📝 [MONITOR] Memory logging loop started")
        
        while self.monitor_active:
            try:
                # Get memory statistics
                memory_stats = await self.smart_memory.execute_memory_command(
                    'memory_stats', {}
                )
                
                if memory_stats.get('success', False):
                    stats = memory_stats.get('stats', {})
                    
                    # Log memory state
                    logger.info(f"📊 [MEMORY] Trades: {stats.get('total_trades', 0)} | "
                              f"Patterns: {stats.get('total_patterns', 0)} | "
                              f"Evolution Score: {stats.get('evolution_score', 0):.2f}")
                    
                    # Check for significant pattern changes
                    await self._detect_pattern_shifts(stats)
                
                await asyncio.sleep(self.memory_log_interval)
                
            except Exception as e:
                logger.error(f"❌ [MEMORY_LOG] Error in memory logging: {e}")
                await asyncio.sleep(self.memory_log_interval * 2)
    
    async def _check_system_vitals(self) -> Dict[str, Any]:
        """Check overall system health vitals."""
        try:
            vitals = {}
            
            # Check memory system health
            if self.smart_memory:
                memory_status = self.smart_memory.get_memory_status()
                vitals['memory_health'] = memory_status.get('system_health', 0)
            else:
                vitals['memory_health'] = 0
            
            # Check live ops health
            if self.live_ops:
                ops_status = self.live_ops.get_live_ops_status()
                vitals['ops_health'] = 95.0 if ops_status.get('live_ops_active', False) else 50.0
            else:
                vitals['ops_health'] = 0
            
            # Check guardian health
            if self.guardian:
                guardian_status = self.guardian.get_guardian_status()
                vitals['guardian_health'] = guardian_status.get('system_health', 0)
            else:
                vitals['guardian_health'] = 0
            
            # Calculate overall health
            health_values = [vitals['memory_health'], vitals['ops_health'], vitals['guardian_health']]
            vitals['overall_health'] = sum(health_values) / len(health_values) if health_values else 0
            
            return vitals
            
        except Exception as e:
            logger.error(f"❌ [VITALS] Error checking system vitals: {e}")
            return {
                'memory_health': 0,
                'ops_health': 0,
                'guardian_health': 0,
                'overall_health': 0
            }
    
    async def _trigger_health_recovery(self, vitals: Dict[str, Any]):
        """Trigger health recovery procedures."""
        try:
            logger.info("🔧 [RECOVERY] Triggering health recovery procedures")
            
            # Identify failing systems
            failing_systems = []
            if vitals['memory_health'] < 70:
                failing_systems.append('memory')
            if vitals['ops_health'] < 70:
                failing_systems.append('ops')
            if vitals['guardian_health'] < 70:
                failing_systems.append('guardian')
            
            # Attempt recovery through guardian
            if self.guardian:
                recovery_result = await self.guardian.execute_guardian_command(
                    'component_recovery', {
                        'failing_systems': failing_systems,
                        'recovery_level': 'moderate'
                    }
                )
                
                if recovery_result.get('success', False):
                    logger.info("✅ [RECOVERY] Health recovery initiated")
                else:
                    logger.error("❌ [RECOVERY] Health recovery failed")
            
        except Exception as e:
            logger.error(f"❌ [RECOVERY] Error in health recovery: {e}")
    
    async def _log_strategy_shifts(self, evolution_result: Dict[str, Any]):
        """Log strategy shifts to memory system."""
        try:
            strategy_shifts = evolution_result.get('strategy_shifts', [])
            
            for shift in strategy_shifts:
                # Create detailed shift log
                shift_log = {
                    'timestamp': datetime.now().isoformat(),
                    'shift_type': shift.get('type', 'unknown'),
                    'regime': shift.get('regime', 'general'),
                    'old_value': shift.get('old_value'),
                    'new_value': shift.get('new_value'),
                    'confidence': shift.get('confidence', 0.0),
                    'reason': shift.get('reason', 'pattern_evolution')
                }
                
                # Log to memory system
                await self.smart_memory.execute_memory_command(
                    'memory_log_pattern_shift', {
                        'shift_data': shift_log
                    }
                )
                
                self.pattern_shifts_logged += 1
                
                logger.info(f"📈 [SHIFT] {shift['type']} in {shift['regime']}: "
                          f"{shift.get('old_value')} → {shift.get('new_value')} "
                          f"(confidence: {shift.get('confidence', 0):.2f})")
            
        except Exception as e:
            logger.error(f"❌ [SHIFT_LOG] Error logging strategy shifts: {e}")
    
    async def _detect_pattern_shifts(self, stats: Dict[str, Any]):
        """Detect significant pattern shifts in memory data."""
        try:
            # Check for significant changes in pattern distribution
            current_patterns = stats.get('total_patterns', 0)
            evolution_score = stats.get('evolution_score', 0)
            
            # Log significant pattern evolution
            if evolution_score > 0.1:  # Significant evolution threshold
                logger.info(f"🔄 [PATTERN_SHIFT] Significant pattern evolution detected: "
                          f"Score {evolution_score:.3f}, Patterns: {current_patterns}")
                
                # Log to memory for future analysis
                await self.smart_memory.execute_memory_command(
                    'memory_log_evolution_event', {
                        'event_type': 'significant_pattern_shift',
                        'evolution_score': evolution_score,
                        'pattern_count': current_patterns,
                        'timestamp': datetime.now().isoformat()
                    }
                )
            
        except Exception as e:
            logger.error(f"❌ [PATTERN_DETECT] Error detecting pattern shifts: {e}")
    
    async def execute_monitor_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute monitoring system command."""
        try:
            params = params or {}
            
            if command == 'monitor_status':
                return await self._handle_monitor_status(params)
            elif command == 'force_evolution':
                return await self._handle_force_evolution(params)
            elif command == 'heartbeat_check':
                return await self._handle_heartbeat_check(params)
            else:
                return {'success': False, 'error': f'Unknown monitor command: {command}'}
                
        except Exception as e:
            logger.error(f"❌ [MONITOR] Command execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_monitor_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle monitor status command."""
        try:
            vitals = await self._check_system_vitals()
            
            return {
                'success': True,
                'message': 'Continuous monitoring status',
                'monitor_active': self.monitor_active,
                'evolution_cycles': self.evolution_cycles,
                'pattern_shifts_logged': self.pattern_shifts_logged,
                'last_pattern_evolution': self.last_pattern_evolution.isoformat() if self.last_pattern_evolution else None,
                'system_vitals': vitals,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [MONITOR] Status command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_force_evolution(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle force evolution command."""
        try:
            logger.info("🧬 [MONITOR] Forcing pattern evolution cycle")
            
            evolution_result = await self.smart_memory.execute_memory_command(
                'memory_pattern_evolve', params
            )
            
            if evolution_result.get('success', False):
                self.evolution_cycles += 1
                self.last_pattern_evolution = datetime.now()
                
                # Log strategy shifts
                await self._log_strategy_shifts(evolution_result)
                
                return {
                    'success': True,
                    'message': 'Pattern evolution forced successfully',
                    'evolution_result': evolution_result,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'error': 'Pattern evolution failed',
                    'details': evolution_result
                }
                
        except Exception as e:
            logger.error(f"❌ [MONITOR] Force evolution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_heartbeat_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle heartbeat check command."""
        try:
            vitals = await self._check_system_vitals()
            
            return {
                'success': True,
                'message': 'Heartbeat check completed',
                'vitals': vitals,
                'heartbeat_healthy': vitals['overall_health'] >= 70,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [MONITOR] Heartbeat check failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_monitor_status(self) -> Dict[str, Any]:
        """Get current monitoring system status."""
        return {
            'monitor_active': self.monitor_active,
            'evolution_cycles': self.evolution_cycles,
            'pattern_shifts_logged': self.pattern_shifts_logged,
            'last_pattern_evolution': self.last_pattern_evolution.isoformat() if self.last_pattern_evolution else None,
            'heartbeat_interval': self.heartbeat_interval,
            'pattern_evolution_interval': self.pattern_evolution_interval,
            'timestamp': datetime.now().isoformat()
        }

# Global continuous monitor instance
_continuous_monitor = None

def initialize_continuous_monitor(config: Dict[str, Any]) -> ContinuousMonitor:
    """Initialize the global continuous monitor."""
    global _continuous_monitor
    _continuous_monitor = ContinuousMonitor(config)
    return _continuous_monitor

def get_continuous_monitor() -> Optional[ContinuousMonitor]:
    """Get the global continuous monitor instance."""
    return _continuous_monitor

async def main():
    """Main function for continuous monitoring system."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🔄 CONTINUOUS MONITORING & PATTERN EVOLUTION SYSTEM")
    print("=" * 60)
    print("Maintaining immortal consciousness heartbeat...")
    print()
    
    # Initialize continuous monitor
    config = {
        'heartbeat_interval': 30,
        'pattern_evolution_interval': 300,  # 5 minutes
        'memory_log_interval': 600  # 10 minutes
    }
    
    monitor = initialize_continuous_monitor(config)
    await monitor.initialize_monitor()
    
    print("💓 [HEARTBEAT] Immortal consciousness pulse active")
    print("🧬 [EVOLUTION] Pattern evolution loops running")
    print("📝 [MEMORY] Strategy shift logging enabled")
    print()
    print("Available commands:")
    print("  - /monitor status")
    print("  - /monitor force_evolution")
    print("  - /monitor heartbeat_check")
    
    try:
        while True:
            await asyncio.sleep(60)
            status = monitor.get_monitor_status()
            print(f"[STATUS] {datetime.now().strftime('%H:%M:%S')} - "
                  f"Cycles: {status['evolution_cycles']} | "
                  f"Shifts: {status['pattern_shifts_logged']}")
    except KeyboardInterrupt:
        print("\n🛑 [SHUTDOWN] Continuous monitoring system shutting down...")
        monitor.monitor_active = False

if __name__ == "__main__":
    asyncio.run(main())
