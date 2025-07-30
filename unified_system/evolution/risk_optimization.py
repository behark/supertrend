"""
Risk Optimization Warm-Up System
================================
Activates periodic risk balancing in testnet mode and monitors behavior
under multiple market regimes for optimal risk management.
"""
import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import numpy as np

# Add project root to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.smart_trade_memory import get_smart_trade_memory
from guardian.live_guardian import get_live_guardian

logger = logging.getLogger(__name__)

class RiskOptimization:
    """Risk optimization and regime monitoring for immortal consciousness."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize risk optimization system."""
        self.config = config
        self.optimization_active = False
        
        # Optimization intervals
        self.risk_balance_interval = config.get('risk_balance_interval', 900)  # 15 minutes
        self.regime_monitor_interval = config.get('regime_monitor_interval', 300)  # 5 minutes
        self.performance_check_interval = config.get('performance_check_interval', 1800)  # 30 minutes
        
        # System components
        self.smart_memory = None
        self.guardian = None
        
        # Risk tracking
        self.current_regime = 'unknown'
        self.regime_history = []
        self.risk_adjustments = 0
        self.optimization_cycles = 0
        
        # Risk parameters
        self.base_risk_ratio = config.get('base_risk_ratio', 2.0)
        self.max_risk_ratio = config.get('max_risk_ratio', 5.0)
        self.min_risk_ratio = config.get('min_risk_ratio', 1.2)
        self.regime_multipliers = {
            'trending': 1.2,
            'volatile': 0.8,
            'sideways': 1.0,
            'breakout': 1.5,
            'reversal': 0.6
        }
        
    async def initialize_risk_optimization(self):
        """Initialize the risk optimization system."""
        try:
            logger.info("⚖️ [RISK_OPT] Initializing Risk Optimization System")
            
            # Get system components
            self.smart_memory = get_smart_trade_memory()
            self.guardian = get_live_guardian()
            
            if not all([self.smart_memory, self.guardian]):
                raise Exception("Required system components not available")
            
            self.optimization_active = True
            
            # Start optimization loops
            asyncio.create_task(self._risk_balance_loop())
            asyncio.create_task(self._regime_monitor_loop())
            asyncio.create_task(self._performance_check_loop())
            
            logger.info("✅ [RISK_OPT] Risk optimization system initialized")
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Initialization failed: {e}")
            raise
    
    async def _risk_balance_loop(self):
        """Periodic risk balancing in testnet mode."""
        logger.info("⚖️ [RISK_OPT] Risk balance loop started")
        
        while self.optimization_active:
            try:
                # Execute risk balance cycle
                balance_result = await self._execute_risk_balance()
                
                if balance_result['success']:
                    self.optimization_cycles += 1
                    
                    if balance_result.get('adjustments_made', 0) > 0:
                        self.risk_adjustments += balance_result['adjustments_made']
                        
                        logger.info(f"⚖️ [RISK_BALANCE] Cycle {self.optimization_cycles}: "
                                  f"{balance_result['adjustments_made']} risk adjustments made")
                
                await asyncio.sleep(self.risk_balance_interval)
                
            except Exception as e:
                logger.error(f"❌ [RISK_BALANCE] Error in risk balance loop: {e}")
                await asyncio.sleep(self.risk_balance_interval * 2)
    
    async def _regime_monitor_loop(self):
        """Monitor market regime changes and adapt risk accordingly."""
        logger.info("📊 [RISK_OPT] Regime monitor loop started")
        
        while self.optimization_active:
            try:
                # Detect current market regime
                regime_result = await self._detect_market_regime()
                
                if regime_result['success']:
                    new_regime = regime_result['regime']
                    
                    if new_regime != self.current_regime:
                        logger.info(f"📊 [REGIME_CHANGE] Market regime changed: "
                                  f"{self.current_regime} → {new_regime}")
                        
                        # Update regime and adjust risk parameters
                        await self._handle_regime_change(self.current_regime, new_regime)
                        self.current_regime = new_regime
                        
                        # Log regime change
                        self.regime_history.append({
                            'timestamp': datetime.now().isoformat(),
                            'old_regime': self.current_regime,
                            'new_regime': new_regime,
                            'confidence': regime_result.get('confidence', 0.0)
                        })
                
                await asyncio.sleep(self.regime_monitor_interval)
                
            except Exception as e:
                logger.error(f"❌ [REGIME_MONITOR] Error in regime monitor loop: {e}")
                await asyncio.sleep(self.regime_monitor_interval * 2)
    
    async def _performance_check_loop(self):
        """Monitor performance under different regimes."""
        logger.info("📈 [RISK_OPT] Performance check loop started")
        
        while self.optimization_active:
            try:
                # Analyze performance by regime
                performance_analysis = await self._analyze_regime_performance()
                
                if performance_analysis['success']:
                    # Log performance insights
                    insights = performance_analysis.get('insights', [])
                    
                    for insight in insights:
                        logger.info(f"📈 [PERFORMANCE] {insight['regime']}: "
                                  f"Win Rate {insight['win_rate']:.1%}, "
                                  f"Avg Return {insight['avg_return']:.2%}")
                    
                    # Adjust risk parameters based on performance
                    await self._optimize_risk_from_performance(performance_analysis)
                
                await asyncio.sleep(self.performance_check_interval)
                
            except Exception as e:
                logger.error(f"❌ [PERFORMANCE_CHECK] Error in performance check loop: {e}")
                await asyncio.sleep(self.performance_check_interval * 2)
    
    async def _execute_risk_balance(self) -> Dict[str, Any]:
        """Execute risk balancing cycle."""
        try:
            # Get current risk metrics
            risk_metrics = await self._get_current_risk_metrics()
            
            adjustments_made = 0
            adjustments = []
            
            # Check if risk adjustments are needed
            if risk_metrics['portfolio_risk'] > 0.8:  # High risk
                # Reduce position sizes
                adjustment = await self._adjust_position_sizes('reduce', 0.2)
                if adjustment['success']:
                    adjustments_made += 1
                    adjustments.append('reduced_position_sizes')
            
            elif risk_metrics['portfolio_risk'] < 0.3:  # Low risk, can increase
                # Increase position sizes (if regime allows)
                if self.current_regime in ['trending', 'breakout']:
                    adjustment = await self._adjust_position_sizes('increase', 0.15)
                    if adjustment['success']:
                        adjustments_made += 1
                        adjustments.append('increased_position_sizes')
            
            # Check risk ratios
            if risk_metrics['avg_risk_ratio'] > self.max_risk_ratio:
                adjustment = await self._adjust_risk_ratios('reduce')
                if adjustment['success']:
                    adjustments_made += 1
                    adjustments.append('reduced_risk_ratios')
            
            elif risk_metrics['avg_risk_ratio'] < self.min_risk_ratio:
                adjustment = await self._adjust_risk_ratios('increase')
                if adjustment['success']:
                    adjustments_made += 1
                    adjustments.append('increased_risk_ratios')
            
            # Log risk balance to memory
            await self._log_risk_balance_cycle({
                'risk_metrics': risk_metrics,
                'adjustments_made': adjustments_made,
                'adjustments': adjustments,
                'regime': self.current_regime
            })
            
            return {
                'success': True,
                'adjustments_made': adjustments_made,
                'adjustments': adjustments,
                'risk_metrics': risk_metrics,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Risk balance execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _detect_market_regime(self) -> Dict[str, Any]:
        """Detect current market regime."""
        try:
            # Get recent market data and patterns
            market_data = await self.smart_memory.execute_memory_command(
                'memory_get_market_patterns', {
                    'lookback_hours': 24,
                    'pattern_types': ['volatility', 'trend', 'momentum']
                }
            )
            
            if not market_data.get('success', False):
                return {'success': False, 'error': 'Failed to get market data'}
            
            patterns = market_data.get('patterns', [])
            
            # Analyze patterns to determine regime
            regime_scores = {
                'trending': 0.0,
                'volatile': 0.0,
                'sideways': 0.0,
                'breakout': 0.0,
                'reversal': 0.0
            }
            
            for pattern in patterns:
                pattern_type = pattern.get('type', '')
                confidence = pattern.get('confidence', 0.0)
                
                if 'trend' in pattern_type.lower():
                    regime_scores['trending'] += confidence
                elif 'volatile' in pattern_type.lower() or 'volatility' in pattern_type.lower():
                    regime_scores['volatile'] += confidence
                elif 'sideways' in pattern_type.lower() or 'range' in pattern_type.lower():
                    regime_scores['sideways'] += confidence
                elif 'breakout' in pattern_type.lower():
                    regime_scores['breakout'] += confidence
                elif 'reversal' in pattern_type.lower():
                    regime_scores['reversal'] += confidence
            
            # Determine dominant regime
            if regime_scores:
                dominant_regime = max(regime_scores, key=regime_scores.get)
                confidence = regime_scores[dominant_regime] / max(sum(regime_scores.values()), 1.0)
                
                return {
                    'success': True,
                    'regime': dominant_regime,
                    'confidence': confidence,
                    'regime_scores': regime_scores,
                    'timestamp': datetime.now().isoformat()
                }
            
            return {
                'success': True,
                'regime': 'sideways',  # Default regime
                'confidence': 0.5,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Regime detection failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_regime_change(self, old_regime: str, new_regime: str):
        """Handle market regime change and adjust risk parameters."""
        try:
            # Get regime-specific multiplier
            multiplier = self.regime_multipliers.get(new_regime, 1.0)
            
            # Adjust base risk parameters
            new_risk_ratio = self.base_risk_ratio * multiplier
            new_risk_ratio = max(self.min_risk_ratio, min(self.max_risk_ratio, new_risk_ratio))
            
            # Apply regime-based risk adjustment
            adjustment_result = await self.smart_memory.execute_memory_command(
                'memory_apply_regime_risk_adjustment', {
                    'regime': new_regime,
                    'risk_ratio': new_risk_ratio,
                    'multiplier': multiplier,
                    'old_regime': old_regime
                }
            )
            
            if adjustment_result.get('success', False):
                logger.info(f"⚖️ [REGIME_ADJUST] Risk adjusted for {new_regime}: "
                          f"ratio {new_risk_ratio:.2f} (multiplier: {multiplier:.2f})")
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Regime change handling failed: {e}")
    
    async def _get_current_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics."""
        try:
            # Get risk metrics from memory system
            metrics_result = await self.smart_memory.execute_memory_command(
                'memory_get_risk_metrics', {
                    'lookback_hours': 24
                }
            )
            
            if metrics_result.get('success', False):
                return metrics_result.get('metrics', {})
            
            # Return default metrics if not available
            return {
                'portfolio_risk': 0.5,
                'avg_risk_ratio': self.base_risk_ratio,
                'position_count': 0,
                'max_drawdown': 0.0,
                'volatility': 0.0
            }
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Risk metrics retrieval failed: {e}")
            return {}
    
    async def _adjust_position_sizes(self, direction: str, magnitude: float) -> Dict[str, Any]:
        """Adjust position sizes."""
        try:
            adjustment_result = await self.smart_memory.execute_memory_command(
                'memory_adjust_position_sizes', {
                    'direction': direction,
                    'magnitude': magnitude,
                    'regime': self.current_regime
                }
            )
            
            return adjustment_result
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Position size adjustment failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _adjust_risk_ratios(self, direction: str) -> Dict[str, Any]:
        """Adjust risk ratios."""
        try:
            adjustment_result = await self.smart_memory.execute_memory_command(
                'memory_adjust_risk_ratios', {
                    'direction': direction,
                    'regime': self.current_regime,
                    'base_ratio': self.base_risk_ratio
                }
            )
            
            return adjustment_result
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Risk ratio adjustment failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _analyze_regime_performance(self) -> Dict[str, Any]:
        """Analyze performance under different market regimes."""
        try:
            performance_result = await self.smart_memory.execute_memory_command(
                'memory_analyze_regime_performance', {
                    'lookback_days': 7,
                    'regimes': list(self.regime_multipliers.keys())
                }
            )
            
            return performance_result
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Regime performance analysis failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _optimize_risk_from_performance(self, performance_analysis: Dict[str, Any]):
        """Optimize risk parameters based on performance analysis."""
        try:
            insights = performance_analysis.get('insights', [])
            
            for insight in insights:
                regime = insight['regime']
                win_rate = insight.get('win_rate', 0.0)
                avg_return = insight.get('avg_return', 0.0)
                
                # Adjust regime multiplier based on performance
                if win_rate > 0.7 and avg_return > 0.02:  # Strong performance
                    self.regime_multipliers[regime] = min(1.5, self.regime_multipliers[regime] * 1.1)
                elif win_rate < 0.4 or avg_return < -0.01:  # Poor performance
                    self.regime_multipliers[regime] = max(0.5, self.regime_multipliers[regime] * 0.9)
                
                logger.info(f"📊 [RISK_OPT] Updated {regime} multiplier to {self.regime_multipliers[regime]:.2f}")
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Risk optimization from performance failed: {e}")
    
    async def _log_risk_balance_cycle(self, cycle_data: Dict[str, Any]):
        """Log risk balance cycle to memory."""
        try:
            await self.smart_memory.execute_memory_command(
                'memory_log_risk_balance_cycle', {
                    'cycle_data': {
                        **cycle_data,
                        'timestamp': datetime.now().isoformat(),
                        'optimization_cycle': self.optimization_cycles
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Risk balance cycle logging failed: {e}")
    
    async def execute_risk_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute risk optimization command."""
        try:
            params = params or {}
            
            if command == 'risk_status':
                return await self._handle_risk_status(params)
            elif command == 'risk_balance':
                return await self._handle_risk_balance(params)
            elif command == 'regime_detect':
                return await self._handle_regime_detect(params)
            elif command == 'performance_analyze':
                return await self._handle_performance_analyze(params)
            else:
                return {'success': False, 'error': f'Unknown risk command: {command}'}
                
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Command execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_risk_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle risk status command."""
        try:
            risk_metrics = await self._get_current_risk_metrics()
            
            return {
                'success': True,
                'message': 'Risk optimization status',
                'optimization_active': self.optimization_active,
                'current_regime': self.current_regime,
                'optimization_cycles': self.optimization_cycles,
                'risk_adjustments': self.risk_adjustments,
                'regime_changes': len(self.regime_history),
                'risk_metrics': risk_metrics,
                'regime_multipliers': self.regime_multipliers,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Status command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_risk_balance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle risk balance command."""
        try:
            logger.info("⚖️ [RISK_OPT] Forcing risk balance cycle")
            
            balance_result = await self._execute_risk_balance()
            
            return {
                'success': True,
                'message': 'Risk balance executed',
                'balance_result': balance_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Risk balance command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_regime_detect(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle regime detection command."""
        try:
            logger.info("📊 [RISK_OPT] Forcing regime detection")
            
            regime_result = await self._detect_market_regime()
            
            return {
                'success': True,
                'message': 'Market regime detected',
                'regime_result': regime_result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Regime detection command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_performance_analyze(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle performance analysis command."""
        try:
            logger.info("📈 [RISK_OPT] Forcing performance analysis")
            
            performance_analysis = await self._analyze_regime_performance()
            
            return {
                'success': True,
                'message': 'Performance analysis completed',
                'performance_analysis': performance_analysis,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ [RISK_OPT] Performance analysis command failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk optimization status."""
        return {
            'optimization_active': self.optimization_active,
            'current_regime': self.current_regime,
            'optimization_cycles': self.optimization_cycles,
            'risk_adjustments': self.risk_adjustments,
            'regime_changes': len(self.regime_history),
            'regime_multipliers': self.regime_multipliers,
            'risk_balance_interval': self.risk_balance_interval,
            'regime_monitor_interval': self.regime_monitor_interval,
            'timestamp': datetime.now().isoformat()
        }

# Global risk optimization instance
_risk_optimization = None

def initialize_risk_optimization(config: Dict[str, Any]) -> RiskOptimization:
    """Initialize the global risk optimization system."""
    global _risk_optimization
    _risk_optimization = RiskOptimization(config)
    return _risk_optimization

def get_risk_optimization() -> Optional[RiskOptimization]:
    """Get the global risk optimization instance."""
    return _risk_optimization

async def main():
    """Main function for risk optimization system."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("⚖️ RISK OPTIMIZATION WARM-UP SYSTEM")
    print("=" * 45)
    print("Activating periodic risk balancing in testnet mode...")
    print()
    
    # Initialize risk optimization
    config = {
        'risk_balance_interval': 900,  # 15 minutes
        'regime_monitor_interval': 300,  # 5 minutes
        'performance_check_interval': 1800,  # 30 minutes
        'base_risk_ratio': 2.0,
        'max_risk_ratio': 5.0,
        'min_risk_ratio': 1.2
    }
    
    risk_opt = initialize_risk_optimization(config)
    await risk_opt.initialize_risk_optimization()
    
    print("⚖️ [RISK_BALANCE] Periodic risk balancing active")
    print("📊 [REGIME_MONITOR] Market regime monitoring enabled")
    print("📈 [PERFORMANCE] Multi-regime performance analysis running")
    print()
    print("Available commands:")
    print("  - /risk status")
    print("  - /risk balance")
    print("  - /risk regime_detect")
    print("  - /risk performance_analyze")
    
    try:
        while True:
            await asyncio.sleep(60)
            status = risk_opt.get_risk_status()
            print(f"[STATUS] {datetime.now().strftime('%H:%M:%S')} - "
                  f"Regime: {status['current_regime']} | "
                  f"Cycles: {status['optimization_cycles']} | "
                  f"Adjustments: {status['risk_adjustments']}")
    except KeyboardInterrupt:
        print("\n🛑 [SHUTDOWN] Risk optimization system shutting down...")
        risk_opt.optimization_active = False

if __name__ == "__main__":
    asyncio.run(main())
