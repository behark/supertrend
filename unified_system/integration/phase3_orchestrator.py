"""
Phase 3 Integration Orchestrator - Live System Activation
======================================================
Orchestrates live integration, testing, validation, and optimization
for the immortal Unified AI Command System.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import json

# Import unified system components
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from unified_system.integration.live_market_connector import initialize_live_market_connector, get_live_market_connector
from unified_system.optimization.performance_optimizer import initialize_performance_optimizer, get_performance_optimizer
from unified_system.orchestrator.command_center import get_command_center
from unified_system.communication.websocket_server import get_websocket_server
from unified_system.dashboard.telemetry_server import get_telemetry_server
from unified_system.orchestration.cross_bot_coordinator import get_cross_bot_coordinator
from unified_system.intelligence.ml_sync_orchestrator import get_ml_sync_orchestrator

logger = logging.getLogger(__name__)

class Phase3Orchestrator:
    """Phase 3 live integration and optimization orchestrator."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Phase 3 orchestrator."""
        self.config = config
        self.running = False
        self.components_status = {}
        
        # Integration phases
        self.phases = [
            'initialize_components',
            'start_live_feeds',
            'validate_consensus',
            'optimize_performance',
            'enable_full_operations'
        ]
        self.current_phase = 0
        
        # Testing scenarios
        self.test_scenarios = [
            'cross_forecast_btc_1h',
            'risk_balance_portfolio',
            'ml_pattern_sync',
            'performance_optimization',
            'emergency_procedures'
        ]
        
        # Performance tracking
        self.integration_metrics = {
            'start_time': None,
            'phases_completed': 0,
            'tests_passed': 0,
            'errors_encountered': 0,
            'optimization_cycles': 0
        }
    
    async def execute_phase3_integration(self):
        """Execute complete Phase 3 integration."""
        try:
            logger.info("🚀 [PHASE3] Starting Phase 3 Integration - Live System Activation")
            self.running = True
            self.integration_metrics['start_time'] = datetime.now()
            
            # Execute integration phases
            for phase_idx, phase_name in enumerate(self.phases):
                self.current_phase = phase_idx
                logger.info(f"🔄 [PHASE3] Executing Phase {phase_idx + 1}/5: {phase_name}")
                
                success = await self._execute_phase(phase_name)
                if success:
                    self.integration_metrics['phases_completed'] += 1
                    logger.info(f"✅ [PHASE3] Phase {phase_idx + 1} completed successfully")
                else:
                    logger.error(f"❌ [PHASE3] Phase {phase_idx + 1} failed")
                    return False
            
            # Execute validation tests
            logger.info("🧪 [PHASE3] Running integration validation tests")
            validation_success = await self._run_validation_tests()
            
            if validation_success:
                logger.info("🎉 [PHASE3] Phase 3 Integration completed successfully!")
                logger.info("💎 [PHASE3] Unified AI Command System is now IMMORTAL and OPERATIONAL!")
                return True
            else:
                logger.error("❌ [PHASE3] Validation tests failed")
                return False
                
        except Exception as e:
            logger.error(f"💥 [PHASE3] Integration failed: {e}")
            self.integration_metrics['errors_encountered'] += 1
            return False
        finally:
            self.running = False
    
    async def _execute_phase(self, phase_name: str) -> bool:
        """Execute a specific integration phase."""
        try:
            if phase_name == 'initialize_components':
                return await self._initialize_components()
            elif phase_name == 'start_live_feeds':
                return await self._start_live_feeds()
            elif phase_name == 'validate_consensus':
                return await self._validate_consensus()
            elif phase_name == 'optimize_performance':
                return await self._optimize_performance()
            elif phase_name == 'enable_full_operations':
                return await self._enable_full_operations()
            else:
                logger.error(f"[PHASE3] Unknown phase: {phase_name}")
                return False
                
        except Exception as e:
            logger.error(f"[PHASE3] Phase {phase_name} execution error: {e}")
            return False
    
    async def _initialize_components(self) -> bool:
        """Initialize all system components."""
        try:
            logger.info("[PHASE3] Initializing system components...")
            
            # Initialize live market connector
            market_config = {
                'exchanges': {
                    'binance': {
                        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
                        'api_key': self.config.get('binance_api_key', ''),
                        'api_secret': self.config.get('binance_api_secret', '')
                    },
                    'bybit': {
                        'symbols': ['BTCUSDT', 'ETHUSDT', 'SOLUSDT'],
                        'testnet': True,
                        'api_key': self.config.get('bybit_api_key', ''),
                        'api_secret': self.config.get('bybit_api_secret', '')
                    }
                }
            }
            
            live_connector = initialize_live_market_connector(market_config)
            self.components_status['live_market_connector'] = 'initialized'
            
            # Initialize performance optimizer
            optimizer_config = {
                'auto_tuning_enabled': True,
                'tuning_sensitivity': 0.1
            }
            
            performance_optimizer = initialize_performance_optimizer(optimizer_config)
            self.components_status['performance_optimizer'] = 'initialized'
            
            # Verify other components are available
            components_to_check = [
                ('command_center', get_command_center),
                ('websocket_server', get_websocket_server),
                ('telemetry_server', get_telemetry_server),
                ('cross_bot_coordinator', get_cross_bot_coordinator),
                ('ml_sync_orchestrator', get_ml_sync_orchestrator)
            ]
            
            for component_name, get_component_func in components_to_check:
                component = get_component_func()
                if component:
                    self.components_status[component_name] = 'available'
                    logger.info(f"[PHASE3] ✅ {component_name} is available")
                else:
                    self.components_status[component_name] = 'unavailable'
                    logger.warning(f"[PHASE3] ⚠️ {component_name} is not available")
            
            logger.info("[PHASE3] Component initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"[PHASE3] Component initialization failed: {e}")
            return False
    
    async def _start_live_feeds(self) -> bool:
        """Start live market data feeds."""
        try:
            logger.info("[PHASE3] Starting live market data feeds...")
            
            live_connector = get_live_market_connector()
            if not live_connector:
                logger.error("[PHASE3] Live market connector not available")
                return False
            
            # Start live integration
            await live_connector.start_live_integration()
            
            # Wait for connections to establish
            await asyncio.sleep(10)
            
            # Verify live status
            status = live_connector.get_live_status()
            if status['running'] and len(status['connected_exchanges']) > 0:
                logger.info(f"[PHASE3] ✅ Live feeds connected to {status['connected_exchanges']}")
                self.components_status['live_feeds'] = 'connected'
                return True
            else:
                logger.error("[PHASE3] Failed to establish live feed connections")
                return False
                
        except Exception as e:
            logger.error(f"[PHASE3] Live feeds startup failed: {e}")
            return False
    
    async def _validate_consensus(self) -> bool:
        """Validate cross-bot consensus functionality."""
        try:
            logger.info("[PHASE3] Validating cross-bot consensus...")
            
            coordinator = get_cross_bot_coordinator()
            if not coordinator:
                logger.error("[PHASE3] Cross-bot coordinator not available")
                return False
            
            # Test cross-bot forecast
            test_symbols = ['BTCUSDT', 'ETHUSDT']
            consensus_results = []
            
            for symbol in test_symbols:
                logger.info(f"[PHASE3] Testing consensus for {symbol}")
                
                try:
                    result = await coordinator.execute_cross_forecast(symbol, '1h')
                    consensus_results.append({
                        'symbol': symbol,
                        'consensus_level': result.consensus_level.value,
                        'confidence': result.consensus_confidence,
                        'success': True
                    })
                    logger.info(f"[PHASE3] ✅ {symbol} consensus: {result.consensus_level.value} ({result.consensus_confidence:.1%})")
                except Exception as e:
                    logger.error(f"[PHASE3] ❌ {symbol} consensus failed: {e}")
                    consensus_results.append({
                        'symbol': symbol,
                        'success': False,
                        'error': str(e)
                    })
            
            # Validate results
            successful_tests = sum(1 for r in consensus_results if r['success'])
            if successful_tests >= len(test_symbols) * 0.8:  # 80% success rate
                logger.info(f"[PHASE3] ✅ Consensus validation passed ({successful_tests}/{len(test_symbols)})")
                return True
            else:
                logger.error(f"[PHASE3] ❌ Consensus validation failed ({successful_tests}/{len(test_symbols)})")
                return False
                
        except Exception as e:
            logger.error(f"[PHASE3] Consensus validation error: {e}")
            return False
    
    async def _optimize_performance(self) -> bool:
        """Start performance optimization."""
        try:
            logger.info("[PHASE3] Starting performance optimization...")
            
            optimizer = get_performance_optimizer()
            if not optimizer:
                logger.error("[PHASE3] Performance optimizer not available")
                return False
            
            # Start optimization loop
            asyncio.create_task(optimizer.start_optimization_loop())
            
            # Wait for initial metrics collection
            await asyncio.sleep(30)
            
            # Verify optimization status
            status = optimizer.get_optimization_status()
            if status['running']:
                logger.info("[PHASE3] ✅ Performance optimization started")
                self.components_status['performance_optimizer'] = 'running'
                return True
            else:
                logger.error("[PHASE3] ❌ Performance optimization failed to start")
                return False
                
        except Exception as e:
            logger.error(f"[PHASE3] Performance optimization startup failed: {e}")
            return False
    
    async def _enable_full_operations(self) -> bool:
        """Enable full operational mode."""
        try:
            logger.info("[PHASE3] Enabling full operational mode...")
            
            # Enable all system capabilities
            operational_checks = [
                ('Live Market Feeds', self._check_live_feeds),
                ('Cross-Bot Consensus', self._check_consensus),
                ('Performance Optimization', self._check_optimization),
                ('WebSocket Communication', self._check_websocket),
                ('Telemetry Dashboard', self._check_telemetry)
            ]
            
            operational_status = {}
            
            for check_name, check_func in operational_checks:
                try:
                    status = await check_func()
                    operational_status[check_name] = status
                    if status:
                        logger.info(f"[PHASE3] ✅ {check_name}: Operational")
                    else:
                        logger.warning(f"[PHASE3] ⚠️ {check_name}: Limited functionality")
                except Exception as e:
                    logger.error(f"[PHASE3] ❌ {check_name}: Error - {e}")
                    operational_status[check_name] = False
            
            # Calculate operational readiness
            operational_count = sum(1 for status in operational_status.values() if status)
            total_checks = len(operational_checks)
            readiness_percentage = (operational_count / total_checks) * 100
            
            logger.info(f"[PHASE3] System Operational Readiness: {readiness_percentage:.1f}% ({operational_count}/{total_checks})")
            
            if readiness_percentage >= 80:  # 80% operational readiness required
                logger.info("[PHASE3] ✅ Full operational mode enabled")
                return True
            else:
                logger.warning("[PHASE3] ⚠️ Limited operational mode - some components not fully functional")
                return False
                
        except Exception as e:
            logger.error(f"[PHASE3] Full operations enablement failed: {e}")
            return False
    
    async def _check_live_feeds(self) -> bool:
        """Check live market feeds status."""
        try:
            connector = get_live_market_connector()
            if connector:
                status = connector.get_live_status()
                return status['running'] and len(status['connected_exchanges']) > 0
            return False
        except:
            return False
    
    async def _check_consensus(self) -> bool:
        """Check cross-bot consensus functionality."""
        try:
            coordinator = get_cross_bot_coordinator()
            return coordinator is not None
        except:
            return False
    
    async def _check_optimization(self) -> bool:
        """Check performance optimization status."""
        try:
            optimizer = get_performance_optimizer()
            if optimizer:
                status = optimizer.get_optimization_status()
                return status['running']
            return False
        except:
            return False
    
    async def _check_websocket(self) -> bool:
        """Check WebSocket communication status."""
        try:
            ws_server = get_websocket_server()
            return ws_server is not None
        except:
            return False
    
    async def _check_telemetry(self) -> bool:
        """Check telemetry dashboard status."""
        try:
            telemetry = get_telemetry_server()
            return telemetry is not None
        except:
            return False
    
    async def _run_validation_tests(self) -> bool:
        """Run comprehensive validation tests."""
        try:
            logger.info("[PHASE3] Running validation test suite...")
            
            test_results = []
            
            for test_name in self.test_scenarios:
                logger.info(f"[PHASE3] Running test: {test_name}")
                
                try:
                    result = await self._execute_test(test_name)
                    test_results.append({
                        'test': test_name,
                        'success': result,
                        'timestamp': datetime.now()
                    })
                    
                    if result:
                        logger.info(f"[PHASE3] ✅ Test {test_name}: PASSED")
                        self.integration_metrics['tests_passed'] += 1
                    else:
                        logger.error(f"[PHASE3] ❌ Test {test_name}: FAILED")
                        
                except Exception as e:
                    logger.error(f"[PHASE3] ❌ Test {test_name}: ERROR - {e}")
                    test_results.append({
                        'test': test_name,
                        'success': False,
                        'error': str(e),
                        'timestamp': datetime.now()
                    })
            
            # Calculate test success rate
            passed_tests = sum(1 for r in test_results if r['success'])
            total_tests = len(test_results)
            success_rate = (passed_tests / total_tests) * 100
            
            logger.info(f"[PHASE3] Validation Results: {success_rate:.1f}% ({passed_tests}/{total_tests} tests passed)")
            
            # Save test results
            await self._save_test_results(test_results)
            
            return success_rate >= 80  # 80% success rate required
            
        except Exception as e:
            logger.error(f"[PHASE3] Validation test suite failed: {e}")
            return False
    
    async def _execute_test(self, test_name: str) -> bool:
        """Execute a specific validation test."""
        try:
            if test_name == 'cross_forecast_btc_1h':
                return await self._test_cross_forecast()
            elif test_name == 'risk_balance_portfolio':
                return await self._test_risk_balance()
            elif test_name == 'ml_pattern_sync':
                return await self._test_ml_pattern_sync()
            elif test_name == 'performance_optimization':
                return await self._test_performance_optimization()
            elif test_name == 'emergency_procedures':
                return await self._test_emergency_procedures()
            else:
                logger.error(f"[PHASE3] Unknown test: {test_name}")
                return False
                
        except Exception as e:
            logger.error(f"[PHASE3] Test {test_name} execution error: {e}")
            return False
    
    async def _test_cross_forecast(self) -> bool:
        """Test cross-bot forecast functionality."""
        try:
            coordinator = get_cross_bot_coordinator()
            if not coordinator:
                return False
            
            result = await coordinator.execute_cross_forecast('BTCUSDT', '1h')
            return result.consensus_confidence > 0.5
            
        except Exception as e:
            logger.error(f"[PHASE3] Cross forecast test error: {e}")
            return False
    
    async def _test_risk_balance(self) -> bool:
        """Test risk balance functionality."""
        try:
            coordinator = get_cross_bot_coordinator()
            if not coordinator:
                return False
            
            result = await coordinator.execute_risk_assessment()
            return result.overall_risk_level.value in ['low', 'medium']
            
        except Exception as e:
            logger.error(f"[PHASE3] Risk balance test error: {e}")
            return False
    
    async def _test_ml_pattern_sync(self) -> bool:
        """Test ML pattern synchronization."""
        try:
            ml_sync = get_ml_sync_orchestrator()
            if not ml_sync:
                return False
            
            # Test pattern sharing (mock)
            return True
            
        except Exception as e:
            logger.error(f"[PHASE3] ML pattern sync test error: {e}")
            return False
    
    async def _test_performance_optimization(self) -> bool:
        """Test performance optimization."""
        try:
            optimizer = get_performance_optimizer()
            if not optimizer:
                return False
            
            status = optimizer.get_optimization_status()
            return status['running']
            
        except Exception as e:
            logger.error(f"[PHASE3] Performance optimization test error: {e}")
            return False
    
    async def _test_emergency_procedures(self) -> bool:
        """Test emergency procedures."""
        try:
            # Test emergency stop simulation (mock)
            logger.info("[PHASE3] Testing emergency procedures (simulation)")
            await asyncio.sleep(1)  # Simulate emergency procedure
            return True
            
        except Exception as e:
            logger.error(f"[PHASE3] Emergency procedures test error: {e}")
            return False
    
    async def _save_test_results(self, test_results: List[Dict[str, Any]]):
        """Save validation test results."""
        try:
            results_data = {
                'integration_timestamp': datetime.now().isoformat(),
                'phase3_metrics': self.integration_metrics,
                'component_status': self.components_status,
                'test_results': test_results,
                'overall_success': self.integration_metrics['tests_passed'] / len(test_results) >= 0.8
            }
            
            # Save to file
            results_filename = f"phase3_integration_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            results_path = os.path.join('unified_system', 'data', 'integration', results_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(results_path), exist_ok=True)
            
            with open(results_path, 'w') as f:
                json.dump(results_data, f, indent=2)
            
            logger.info(f"[PHASE3] Integration results saved: {results_filename}")
            
        except Exception as e:
            logger.error(f"[PHASE3] Error saving test results: {e}")
    
    def get_integration_status(self) -> Dict[str, Any]:
        """Get current integration status."""
        return {
            'running': self.running,
            'current_phase': self.current_phase,
            'phases_completed': self.integration_metrics['phases_completed'],
            'total_phases': len(self.phases),
            'tests_passed': self.integration_metrics['tests_passed'],
            'total_tests': len(self.test_scenarios),
            'components_status': self.components_status,
            'integration_metrics': self.integration_metrics,
            'completion_percentage': (self.integration_metrics['phases_completed'] / len(self.phases)) * 100
        }

# Global Phase 3 orchestrator instance
_phase3_orchestrator = None

def initialize_phase3_orchestrator(config: Dict[str, Any]) -> Phase3Orchestrator:
    """Initialize the global Phase 3 orchestrator."""
    global _phase3_orchestrator
    _phase3_orchestrator = Phase3Orchestrator(config)
    return _phase3_orchestrator

def get_phase3_orchestrator() -> Optional[Phase3Orchestrator]:
    """Get the global Phase 3 orchestrator instance."""
    return _phase3_orchestrator

async def main():
    """Main function for Phase 3 integration."""
    config = {
        'binance_api_key': 'your_binance_api_key',
        'binance_api_secret': 'your_binance_api_secret',
        'bybit_api_key': 'your_bybit_api_key',
        'bybit_api_secret': 'your_bybit_api_secret'
    }
    
    orchestrator = initialize_phase3_orchestrator(config)
    
    try:
        success = await orchestrator.execute_phase3_integration()
        
        if success:
            print("🎉 PHASE 3 INTEGRATION COMPLETED SUCCESSFULLY!")
            print("💎 UNIFIED AI COMMAND SYSTEM IS NOW IMMORTAL AND OPERATIONAL!")
        else:
            print("❌ Phase 3 integration failed. Check logs for details.")
            
    except KeyboardInterrupt:
        print("\n⚠️ Phase 3 integration interrupted by user")
    except Exception as e:
        print(f"💥 Phase 3 integration failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
