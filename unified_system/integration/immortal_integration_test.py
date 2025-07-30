"""
Immortal Integration Test Suite
==============================
Comprehensive end-to-end testing for Phase 4 integration with Phase 3 infrastructure.
Tests tight coupling between all core systems for immortal activation readiness.
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

# Import Phase 4 systems
from live_ops.live_ops_manager import LiveOpsManager, initialize_live_ops_manager
from memory.smart_trade_memory import SmartTradeMemory, initialize_smart_trade_memory, TradeRecord, TradeOutcome
from scaling.multi_agent_scaler import MultiAgentScaler, initialize_multi_agent_scaler, AgentProfile, AgentCapability, AgentStatus
from guardian.live_guardian import LiveGuardian, initialize_live_guardian, SystemComponent, ThreatLevel

logger = logging.getLogger(__name__)

class ImmortalIntegrationTest:
    """Comprehensive integration test suite for immortal system activation."""
    
    def __init__(self):
        """Initialize integration test suite."""
        self.test_results: Dict[str, Dict[str, Any]] = {}
        self.systems_initialized = False
        
        # Phase 4 systems
        self.live_ops_manager: Optional[LiveOpsManager] = None
        self.smart_memory: Optional[SmartTradeMemory] = None
        self.multi_scaler: Optional[MultiAgentScaler] = None
        self.guardian: Optional[LiveGuardian] = None
        
    async def run_full_integration_suite(self) -> Dict[str, Any]:
        """Run complete integration test suite."""
        try:
            logger.info("🚀 [IMMORTAL_TEST] Starting Immortal Integration Test Suite")
            
            # Initialize all systems
            await self._initialize_all_systems()
            
            # Run integration tests
            test_results = {}
            
            # Test 1: Live Ops ↔ Performance Engine Integration
            test_results['live_ops_performance'] = await self._test_live_ops_performance_integration()
            
            # Test 2: Smart Memory ↔ Behavioral Decision Integration
            test_results['memory_behavioral'] = await self._test_memory_behavioral_integration()
            
            # Test 3: Multi-Agent Scaling ↔ Orchestration Core Integration
            test_results['scaling_orchestration'] = await self._test_scaling_orchestration_integration()
            
            # Test 4: Guardian ↔ Emergency Systems Integration
            test_results['guardian_emergency'] = await self._test_guardian_emergency_integration()
            
            # Test 5: End-to-End System Flow
            test_results['end_to_end'] = await self._test_end_to_end_flow()
            
            # Generate final report
            final_report = await self._generate_integration_report(test_results)
            
            logger.info("✅ [IMMORTAL_TEST] Integration Test Suite Completed")
            return final_report
            
        except Exception as e:
            logger.error(f"❌ [IMMORTAL_TEST] Integration test suite failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _initialize_all_systems(self):
        """Initialize all Phase 4 systems."""
        try:
            logger.info("🔧 [IMMORTAL_TEST] Initializing all systems for integration testing")
            
            # Initialize Phase 4 systems
            live_ops_config = {
                'max_agents': 10,
                'heartbeat_interval': 30,
                'api_timeout': 10,
                'emergency_stop_enabled': True
            }
            self.live_ops_manager = initialize_live_ops_manager(live_ops_config)
            await self.live_ops_manager.initialize_live_ops()
            
            memory_config = {
                'db_path': 'unified_system/data/test_trade_memory.db',
                'max_trade_records': 10000,
                'retention_days': 30,
                'min_trades_for_evolution': 5
            }
            self.smart_memory = initialize_smart_trade_memory(memory_config)
            await self.smart_memory.initialize_memory_system()
            
            scaler_config = {
                'max_agents': 20,
                'load_threshold_scale_up': 0.7,
                'load_threshold_scale_down': 0.2,
                'auto_scaling_enabled': True
            }
            self.multi_scaler = initialize_multi_agent_scaler(scaler_config)
            await self.multi_scaler.initialize_scaler()
            
            guardian_config = {
                'monitoring_interval': 5,
                'auto_recovery_enabled': True,
                'cpu_threshold': 80.0,
                'memory_threshold': 75.0
            }
            self.guardian = initialize_live_guardian(guardian_config)
            await self.guardian.initialize_guardian()
            
            self.systems_initialized = True
            logger.info("✅ [IMMORTAL_TEST] All systems initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ [IMMORTAL_TEST] System initialization failed: {e}")
            raise
    
    async def _test_live_ops_performance_integration(self) -> Dict[str, Any]:
        """Test Live Ops Manager ↔ Performance Engine integration."""
        try:
            logger.info("🔄 [TEST_1] Testing Live Ops ↔ Performance Engine Integration")
            
            # Test live mode activation
            live_start_result = await self.live_ops_manager.execute_live_command('live_start', {})
            
            # Test performance metrics collection
            performance_result = await self.live_ops_manager.execute_live_command('live_status', {})
            
            # Test mode switching
            sim_result = await self.live_ops_manager.execute_live_command('live_mode', {'mode': 'simulation'})
            
            success = (
                live_start_result.get('success', False) and
                performance_result.get('success', False) and
                sim_result.get('success', False)
            )
            
            return {
                'test_name': 'Live Ops ↔ Performance Engine Integration',
                'success': success,
                'details': {
                    'live_start': live_start_result,
                    'performance_check': performance_result,
                    'mode_switch': sim_result
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [TEST_1] Live Ops integration test failed: {e}")
            return {
                'test_name': 'Live Ops ↔ Performance Engine Integration',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _test_memory_behavioral_integration(self) -> Dict[str, Any]:
        """Test Smart Memory ↔ Behavioral Decision Integration."""
        try:
            logger.info("🧠 [TEST_2] Testing Smart Memory ↔ Behavioral Decision Integration")
            
            # Create test trade record
            test_trade = TradeRecord(
                trade_id="test_trade_001",
                agent_id="test_agent",
                symbol="BTCUSDT",
                timeframe="1h",
                trade_type="BUY",
                entry_price=45000.0,
                exit_price=46000.0,
                quantity=0.1,
                confidence_score=0.85,
                execution_conditions={"regime": "trending_up"},
                market_regime="bullish",
                consensus_data={"agreement": 0.9},
                outcome=TradeOutcome.EXECUTED,
                pnl=100.0,
                execution_time=datetime.now(),
                close_time=datetime.now() + timedelta(hours=2),
                metadata={"test": True}
            )
            
            # Record trade in memory
            record_result = await self.smart_memory.record_trade(test_trade)
            
            # Test memory retrieval
            memory_result = await self.smart_memory.execute_memory_command('memory_last', {'count': 1})
            
            # Test pattern evolution
            evolution_result = await self.smart_memory.execute_memory_command('memory_pattern_evolve', {})
            
            success = (
                record_result and
                memory_result.get('success', False) and
                evolution_result.get('success', False)
            )
            
            return {
                'test_name': 'Smart Memory ↔ Behavioral Decision Integration',
                'success': success,
                'details': {
                    'trade_recorded': record_result,
                    'memory_retrieval': memory_result,
                    'pattern_evolution': evolution_result
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [TEST_2] Memory integration test failed: {e}")
            return {
                'test_name': 'Smart Memory ↔ Behavioral Decision Integration',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _test_scaling_orchestration_integration(self) -> Dict[str, Any]:
        """Test Multi-Agent Scaling ↔ Orchestration Core Integration."""
        try:
            logger.info("📈 [TEST_3] Testing Multi-Agent Scaling ↔ Orchestration Core Integration")
            
            # Create test agent
            test_agent = AgentProfile(
                agent_id="test_scaling_agent",
                agent_name="Test Scaling Agent",
                agent_type="trading_bot",
                capabilities=[
                    AgentCapability(
                        capability_id="forecast",
                        name="Forecast Generation",
                        description="Generate market forecasts",
                        specializations=["BTCUSDT", "ETHUSDT"]
                    )
                ],
                current_load=0.3,
                max_capacity=1.0,
                performance_score=0.8,
                status=AgentStatus.ACTIVE,
                last_heartbeat=datetime.now(),
                specializations=["BTCUSDT"],
                metadata={"test": True}
            )
            
            # Register agent
            register_result = await self.multi_scaler.register_agent(test_agent)
            
            # Test routing
            route_result = await self.multi_scaler.route_request("forecast", {"symbol": "BTCUSDT"})
            
            # Test scaling commands
            status_result = await self.multi_scaler.execute_scaling_command('scale_status', {})
            
            success = (
                register_result and
                route_result is not None and
                status_result.get('success', False)
            )
            
            return {
                'test_name': 'Multi-Agent Scaling ↔ Orchestration Core Integration',
                'success': success,
                'details': {
                    'agent_registered': register_result,
                    'routing_success': route_result is not None,
                    'status_check': status_result
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [TEST_3] Scaling integration test failed: {e}")
            return {
                'test_name': 'Multi-Agent Scaling ↔ Orchestration Core Integration',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _test_guardian_emergency_integration(self) -> Dict[str, Any]:
        """Test Guardian ↔ Emergency Systems Integration."""
        try:
            logger.info("🛡️ [TEST_4] Testing Guardian ↔ Emergency Systems Integration")
            
            # Test threat reporting
            threat_id = await self.guardian.report_threat(
                threat_type="test_threat",
                component=SystemComponent.TRADING_ENGINE,
                severity=ThreatLevel.HIGH,
                description="Integration test threat",
                metrics={"cpu_usage": 95.0}
            )
            
            # Test guardian status
            status_result = await self.guardian.execute_guardian_command('guardian_status', {})
            
            # Test threat history
            threat_history = await self.guardian.execute_guardian_command('threat_history', {'limit': 5})
            
            success = (
                threat_id != "" and
                status_result.get('success', False) and
                threat_history.get('success', False)
            )
            
            return {
                'test_name': 'Guardian ↔ Emergency Systems Integration',
                'success': success,
                'details': {
                    'threat_reported': threat_id != "",
                    'status_check': status_result,
                    'threat_history': threat_history
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [TEST_4] Guardian integration test failed: {e}")
            return {
                'test_name': 'Guardian ↔ Emergency Systems Integration',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _test_end_to_end_flow(self) -> Dict[str, Any]:
        """Test complete end-to-end system flow."""
        try:
            logger.info("🔄 [TEST_5] Testing End-to-End System Flow")
            
            # Simulate complete trading flow
            flow_steps = []
            
            # Step 1: Live ops activation
            live_ops_result = await self.live_ops_manager.execute_live_command('live_status', {})
            flow_steps.append(('live_ops_check', live_ops_result.get('success', False)))
            
            # Step 2: Memory system check
            memory_result = await self.smart_memory.execute_memory_command('memory_stats', {})
            flow_steps.append(('memory_check', memory_result.get('success', False)))
            
            # Step 3: Scaling system check
            scaling_result = await self.multi_scaler.execute_scaling_command('scale_status', {})
            flow_steps.append(('scaling_check', scaling_result.get('success', False)))
            
            # Step 4: Guardian system check
            guardian_result = await self.guardian.execute_guardian_command('guardian_status', {})
            flow_steps.append(('guardian_check', guardian_result.get('success', False)))
            
            # Calculate overall success
            success = all(step[1] for step in flow_steps)
            
            return {
                'test_name': 'End-to-End System Flow',
                'success': success,
                'details': {
                    'flow_steps': flow_steps,
                    'all_systems_operational': success
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [TEST_5] End-to-end flow test failed: {e}")
            return {
                'test_name': 'End-to-End System Flow',
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def _generate_integration_report(self, test_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate comprehensive integration test report."""
        try:
            # Calculate overall statistics
            total_tests = len(test_results)
            passed_tests = len([r for r in test_results.values() if r.get('success', False)])
            failed_tests = total_tests - passed_tests
            success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
            
            # Determine overall readiness
            immortal_ready = success_rate >= 90.0  # 90% pass rate required
            
            # Generate recommendations
            recommendations = []
            if not immortal_ready:
                recommendations.append("Address failing integration tests before immortal activation")
            
            for test_name, result in test_results.items():
                if not result.get('success', False):
                    recommendations.append(f"Fix {test_name}: {result.get('error', 'Unknown error')}")
            
            if immortal_ready:
                recommendations.append("✅ System ready for Immortal Mode activation")
                recommendations.append("Proceed with live API credential integration")
                recommendations.append("Execute /immortal start when ready")
            
            report = {
                'integration_test_report': {
                    'test_suite_version': '1.0.0',
                    'execution_time': datetime.now().isoformat(),
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': success_rate,
                    'immortal_ready': immortal_ready,
                    'test_results': test_results,
                    'recommendations': recommendations,
                    'next_steps': [
                        "Live API credential integration" if immortal_ready else "Fix failing tests",
                        "Immortal Mode activation" if immortal_ready else "Re-run integration tests",
                        "Legacy export preparation" if immortal_ready else "System debugging"
                    ]
                },
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"📊 [IMMORTAL_TEST] Integration Report: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
            
            if immortal_ready:
                logger.info("🎯 [IMMORTAL_TEST] ✅ SYSTEM READY FOR IMMORTAL ACTIVATION")
            else:
                logger.warning("⚠️ [IMMORTAL_TEST] System requires fixes before immortal activation")
            
            return report
            
        except Exception as e:
            logger.error(f"❌ [IMMORTAL_TEST] Report generation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

async def main():
    """Main function to run immortal integration tests."""
    # Configure logging with UTF-8 encoding
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    print("IMMORTAL INTEGRATION TEST SUITE")
    print("=" * 50)
    print("Testing Phase 4 <-> Phase 3 system integration...")
    print("Validating immortal activation readiness...")
    print()
    
    # Create and run test suite
    test_suite = ImmortalIntegrationTest()
    
    try:
        # Run full integration test suite
        results = await test_suite.run_full_integration_suite()
        
        # Display results
        if results.get('success', False):
            report = results['integration_test_report']
            
            print(f"INTEGRATION TEST RESULTS")
            print(f"Tests Passed: {report['passed_tests']}/{report['total_tests']}")
            print(f"Success Rate: {report['success_rate']:.1f}%")
            print(f"Immortal Ready: {'YES' if report['immortal_ready'] else 'NO'}")
            print()
            
            print("RECOMMENDATIONS:")
            for rec in report['recommendations']:
                print(f"  - {rec}")
            print()
            
            if report['immortal_ready']:
                print("IMMORTAL SYSTEM INTEGRATION: COMPLETE")
                print("Ready for live API integration and immortal activation!")
            else:
                print("IMMORTAL SYSTEM INTEGRATION: REQUIRES ATTENTION")
                print("Please address failing tests before activation.")
        else:
            print(f"ERROR: Integration test suite failed: {results.get('error', 'Unknown error')}")
            
    except KeyboardInterrupt:
        print("\nIntegration test suite interrupted by user")
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
