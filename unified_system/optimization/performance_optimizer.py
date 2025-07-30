"""
Performance Optimizer - Feedback-Driven Evolution
===============================================
Tracks response speed, signal quality, execution delay and implements
auto-tuning logic with optimization thresholds for immortal performance.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import statistics
import json

# Import unified system components
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance tracking metrics."""
    timestamp: datetime
    response_time: float
    signal_quality_score: float
    execution_delay: float
    consensus_confidence: float
    risk_zone_overlap: float
    agent_response_delay: Dict[str, float]
    throughput: float
    error_rate: float

@dataclass
class OptimizationThreshold:
    """Performance optimization threshold."""
    metric_name: str
    threshold_value: float
    comparison: str  # 'greater_than', 'less_than', 'equal_to'
    severity: str    # 'warning', 'critical'
    action: str      # 'alert', 'auto_tune', 'emergency_stop'
    description: str

class PerformanceOptimizer:
    """Feedback-driven performance optimization system."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize performance optimizer."""
        self.config = config
        
        # Performance tracking
        self.metrics_history: List[PerformanceMetrics] = []
        self.max_history = 10000
        
        # Optimization thresholds
        self.thresholds = self._initialize_thresholds()
        
        # Auto-tuning parameters
        self.auto_tuning_enabled = config.get('auto_tuning_enabled', True)
        self.tuning_sensitivity = config.get('tuning_sensitivity', 0.1)
        
        # Performance targets
        self.performance_targets = {
            'max_response_time': 2.0,      # seconds
            'min_signal_quality': 0.7,     # 70%
            'max_execution_delay': 5.0,    # seconds
            'min_consensus_confidence': 0.6, # 60%
            'max_risk_overlap': 0.3,       # 30%
            'max_agent_delay': 3.0,        # seconds
            'min_throughput': 10.0,        # signals/hour
            'max_error_rate': 0.05         # 5%
        }
        
        # Optimization state
        self.running = False
        self.last_optimization = datetime.now()
        self.optimization_count = 0
        
        # Alert tracking
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        self.alert_history: List[Dict[str, Any]] = []
    
    def _initialize_thresholds(self) -> List[OptimizationThreshold]:
        """Initialize performance optimization thresholds."""
        return [
            OptimizationThreshold(
                metric_name='response_time',
                threshold_value=2.0,
                comparison='greater_than',
                severity='warning',
                action='auto_tune',
                description='Response time exceeds 2 seconds'
            ),
            OptimizationThreshold(
                metric_name='response_time',
                threshold_value=5.0,
                comparison='greater_than',
                severity='critical',
                action='alert',
                description='Response time critically high (>5s)'
            ),
            OptimizationThreshold(
                metric_name='signal_quality_score',
                threshold_value=0.5,
                comparison='less_than',
                severity='warning',
                action='auto_tune',
                description='Signal quality below acceptable threshold'
            ),
            OptimizationThreshold(
                metric_name='execution_delay',
                threshold_value=10.0,
                comparison='greater_than',
                severity='critical',
                action='alert',
                description='Execution delay critically high'
            ),
            OptimizationThreshold(
                metric_name='consensus_confidence',
                threshold_value=0.4,
                comparison='less_than',
                severity='warning',
                action='auto_tune',
                description='Consensus confidence too low'
            ),
            OptimizationThreshold(
                metric_name='error_rate',
                threshold_value=0.1,
                comparison='greater_than',
                severity='critical',
                action='emergency_stop',
                description='Error rate exceeds 10% - system instability'
            )
        ]
    
    async def start_optimization_loop(self):
        """Start the performance optimization loop."""
        try:
            self.running = True
            logger.info("[OPTIMIZER] Starting performance optimization loop")
            
            # Start optimization tasks
            tasks = [
                asyncio.create_task(self._collect_performance_metrics()),
                asyncio.create_task(self._monitor_thresholds()),
                asyncio.create_task(self._auto_tune_system()),
                asyncio.create_task(self._generate_optimization_reports())
            ]
            
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"[OPTIMIZER] Optimization loop failed: {e}")
            raise
    
    async def stop_optimization_loop(self):
        """Stop the performance optimization loop."""
        self.running = False
        logger.info("[OPTIMIZER] Performance optimization loop stopped")
    
    async def _collect_performance_metrics(self):
        """Collect real-time performance metrics."""
        while self.running:
            try:
                # Collect metrics from various system components
                metrics = await self._gather_current_metrics()
                
                # Store metrics
                self.metrics_history.append(metrics)
                
                # Maintain history size
                if len(self.metrics_history) > self.max_history:
                    self.metrics_history = self.metrics_history[-self.max_history:]
                
                # Log performance summary every 10 minutes
                if len(self.metrics_history) % 60 == 0:  # Every 60 collections (10 min)
                    await self._log_performance_summary()
                
                await asyncio.sleep(10)  # Collect every 10 seconds
                
            except Exception as e:
                logger.error(f"[OPTIMIZER] Metrics collection error: {e}")
                await asyncio.sleep(30)
    
    async def _gather_current_metrics(self) -> PerformanceMetrics:
        """Gather current performance metrics from system components."""
        try:
            # Mock metrics - integrate with actual system components
            current_time = datetime.now()
            
            # Calculate response time (mock)
            response_time = self._calculate_avg_response_time()
            
            # Calculate signal quality score
            signal_quality = self._calculate_signal_quality_score()
            
            # Calculate execution delay
            execution_delay = self._calculate_execution_delay()
            
            # Calculate consensus confidence
            consensus_confidence = self._calculate_consensus_confidence()
            
            # Calculate risk zone overlap
            risk_overlap = self._calculate_risk_zone_overlap()
            
            # Calculate agent response delays
            agent_delays = self._calculate_agent_response_delays()
            
            # Calculate throughput
            throughput = self._calculate_throughput()
            
            # Calculate error rate
            error_rate = self._calculate_error_rate()
            
            return PerformanceMetrics(
                timestamp=current_time,
                response_time=response_time,
                signal_quality_score=signal_quality,
                execution_delay=execution_delay,
                consensus_confidence=consensus_confidence,
                risk_zone_overlap=risk_overlap,
                agent_response_delay=agent_delays,
                throughput=throughput,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"[OPTIMIZER] Error gathering metrics: {e}")
            # Return default metrics on error
            return PerformanceMetrics(
                timestamp=datetime.now(),
                response_time=0.0,
                signal_quality_score=0.0,
                execution_delay=0.0,
                consensus_confidence=0.0,
                risk_zone_overlap=0.0,
                agent_response_delay={},
                throughput=0.0,
                error_rate=1.0  # High error rate to indicate problem
            )
    
    def _calculate_avg_response_time(self) -> float:
        """Calculate average response time from recent metrics."""
        if len(self.metrics_history) < 10:
            return 1.5  # Default reasonable response time
        
        recent_metrics = self.metrics_history[-10:]
        response_times = [m.response_time for m in recent_metrics if m.response_time > 0]
        
        if response_times:
            return statistics.mean(response_times)
        return 1.5
    
    def _calculate_signal_quality_score(self) -> float:
        """Calculate signal quality score based on recent performance."""
        # Mock calculation - integrate with actual signal tracking
        base_quality = 0.75
        
        # Adjust based on recent error rate
        if self.metrics_history:
            recent_error_rate = self.metrics_history[-1].error_rate
            quality_adjustment = max(0, 1 - (recent_error_rate * 2))
            return min(1.0, base_quality * quality_adjustment)
        
        return base_quality
    
    def _calculate_execution_delay(self) -> float:
        """Calculate average execution delay."""
        # Mock calculation
        return 2.5  # seconds
    
    def _calculate_consensus_confidence(self) -> float:
        """Calculate consensus confidence from cross-bot coordination."""
        # Mock calculation - integrate with cross-bot coordinator
        return 0.78
    
    def _calculate_risk_zone_overlap(self) -> float:
        """Calculate risk zone overlap between agents."""
        # Mock calculation
        return 0.25
    
    def _calculate_agent_response_delays(self) -> Dict[str, float]:
        """Calculate response delays for each agent."""
        return {
            'bidget': 1.2,
            'bybit': 1.8
        }
    
    def _calculate_throughput(self) -> float:
        """Calculate system throughput (signals/hour)."""
        return 15.5
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate."""
        return 0.02  # 2%
    
    async def _monitor_thresholds(self):
        """Monitor performance thresholds and trigger actions."""
        while self.running:
            try:
                if not self.metrics_history:
                    await asyncio.sleep(30)
                    continue
                
                latest_metrics = self.metrics_history[-1]
                
                # Check each threshold
                for threshold in self.thresholds:
                    violation = self._check_threshold_violation(latest_metrics, threshold)
                    
                    if violation:
                        await self._handle_threshold_violation(threshold, latest_metrics)
                
                await asyncio.sleep(15)  # Check every 15 seconds
                
            except Exception as e:
                logger.error(f"[OPTIMIZER] Threshold monitoring error: {e}")
                await asyncio.sleep(60)
    
    def _check_threshold_violation(self, metrics: PerformanceMetrics, 
                                 threshold: OptimizationThreshold) -> bool:
        """Check if a threshold is violated."""
        try:
            metric_value = getattr(metrics, threshold.metric_name, None)
            
            if metric_value is None:
                return False
            
            if threshold.comparison == 'greater_than':
                return metric_value > threshold.threshold_value
            elif threshold.comparison == 'less_than':
                return metric_value < threshold.threshold_value
            elif threshold.comparison == 'equal_to':
                return abs(metric_value - threshold.threshold_value) < 0.001
            
            return False
            
        except Exception as e:
            logger.error(f"[OPTIMIZER] Threshold check error: {e}")
            return False
    
    async def _handle_threshold_violation(self, threshold: OptimizationThreshold, 
                                        metrics: PerformanceMetrics):
        """Handle threshold violation based on action type."""
        try:
            violation_id = f"{threshold.metric_name}_{threshold.severity}"
            
            # Avoid duplicate alerts
            if violation_id in self.active_alerts:
                last_alert = self.active_alerts[violation_id]['timestamp']
                if (datetime.now() - last_alert).total_seconds() < 300:  # 5 min cooldown
                    return
            
            # Record alert
            alert_data = {
                'threshold': threshold,
                'metrics': metrics,
                'timestamp': datetime.now(),
                'violation_id': violation_id
            }
            
            self.active_alerts[violation_id] = alert_data
            self.alert_history.append(alert_data)
            
            logger.warning(f"[OPTIMIZER] Threshold violation: {threshold.description}")
            
            # Execute action
            if threshold.action == 'alert':
                await self._send_performance_alert(threshold, metrics)
            elif threshold.action == 'auto_tune':
                await self._execute_auto_tune(threshold, metrics)
            elif threshold.action == 'emergency_stop':
                await self._execute_emergency_stop(threshold, metrics)
                
        except Exception as e:
            logger.error(f"[OPTIMIZER] Error handling threshold violation: {e}")
    
    async def _send_performance_alert(self, threshold: OptimizationThreshold, 
                                    metrics: PerformanceMetrics):
        """Send performance alert to administrators."""
        try:
            alert_message = {
                'type': 'performance_alert',
                'severity': threshold.severity,
                'metric': threshold.metric_name,
                'threshold': threshold.threshold_value,
                'current_value': getattr(metrics, threshold.metric_name),
                'description': threshold.description,
                'timestamp': datetime.now().isoformat(),
                'action_required': threshold.severity == 'critical'
            }
            
            logger.critical(f"[OPTIMIZER] PERFORMANCE ALERT: {threshold.description}")
            
            # In production, send to monitoring system, Telegram, email, etc.
            
        except Exception as e:
            logger.error(f"[OPTIMIZER] Error sending alert: {e}")
    
    async def _execute_auto_tune(self, threshold: OptimizationThreshold, 
                               metrics: PerformanceMetrics):
        """Execute automatic performance tuning."""
        try:
            if not self.auto_tuning_enabled:
                logger.info("[OPTIMIZER] Auto-tuning disabled, skipping optimization")
                return
            
            logger.info(f"[OPTIMIZER] Executing auto-tune for {threshold.metric_name}")
            
            # Determine optimization strategy
            optimization_strategy = self._determine_optimization_strategy(threshold, metrics)
            
            # Apply optimization
            success = await self._apply_optimization(optimization_strategy)
            
            if success:
                self.optimization_count += 1
                self.last_optimization = datetime.now()
                logger.info(f"[OPTIMIZER] Auto-tune completed for {threshold.metric_name}")
            else:
                logger.warning(f"[OPTIMIZER] Auto-tune failed for {threshold.metric_name}")
                
        except Exception as e:
            logger.error(f"[OPTIMIZER] Auto-tune execution error: {e}")
    
    def _determine_optimization_strategy(self, threshold: OptimizationThreshold, 
                                       metrics: PerformanceMetrics) -> Dict[str, Any]:
        """Determine the best optimization strategy."""
        strategy = {
            'metric': threshold.metric_name,
            'current_value': getattr(metrics, threshold.metric_name),
            'target_value': threshold.threshold_value,
            'actions': []
        }
        
        if threshold.metric_name == 'response_time':
            strategy['actions'] = [
                {'type': 'increase_timeout', 'value': 1.5},
                {'type': 'reduce_concurrent_requests', 'value': 0.8},
                {'type': 'optimize_query_cache', 'enabled': True}
            ]
        elif threshold.metric_name == 'signal_quality_score':
            strategy['actions'] = [
                {'type': 'increase_confidence_threshold', 'value': 0.1},
                {'type': 'enable_additional_filters', 'enabled': True},
                {'type': 'reduce_signal_frequency', 'factor': 0.9}
            ]
        elif threshold.metric_name == 'consensus_confidence':
            strategy['actions'] = [
                {'type': 'require_stronger_consensus', 'threshold': 0.7},
                {'type': 'increase_agent_weights', 'high_performers': True},
                {'type': 'enable_consensus_filtering', 'enabled': True}
            ]
        
        return strategy
    
    async def _apply_optimization(self, strategy: Dict[str, Any]) -> bool:
        """Apply optimization strategy to the system."""
        try:
            logger.info(f"[OPTIMIZER] Applying optimization strategy for {strategy['metric']}")
            
            # Mock optimization application
            # In production, this would modify actual system parameters
            
            for action in strategy['actions']:
                logger.info(f"[OPTIMIZER] Applying action: {action['type']}")
                
                # Simulate optimization delay
                await asyncio.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.error(f"[OPTIMIZER] Error applying optimization: {e}")
            return False
    
    async def _execute_emergency_stop(self, threshold: OptimizationThreshold, 
                                    metrics: PerformanceMetrics):
        """Execute emergency stop procedures."""
        try:
            logger.critical(f"[OPTIMIZER] EMERGENCY STOP TRIGGERED: {threshold.description}")
            
            # Emergency stop actions
            emergency_actions = [
                'halt_new_signals',
                'close_risky_positions',
                'notify_administrators',
                'enable_safe_mode',
                'log_system_state'
            ]
            
            for action in emergency_actions:
                logger.critical(f"[OPTIMIZER] Emergency action: {action}")
                # In production, execute actual emergency procedures
                await asyncio.sleep(0.1)
            
            # Set system to safe mode
            self.auto_tuning_enabled = False
            
        except Exception as e:
            logger.error(f"[OPTIMIZER] Emergency stop execution error: {e}")
    
    async def _auto_tune_system(self):
        """Periodic system auto-tuning based on performance trends."""
        while self.running:
            try:
                # Run auto-tuning every hour
                await asyncio.sleep(3600)
                
                if not self.auto_tuning_enabled:
                    continue
                
                # Analyze performance trends
                trends = self._analyze_performance_trends()
                
                # Apply proactive optimizations
                if trends['needs_optimization']:
                    await self._apply_proactive_optimizations(trends)
                
            except Exception as e:
                logger.error(f"[OPTIMIZER] Auto-tune system error: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error
    
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends for proactive optimization."""
        if len(self.metrics_history) < 100:
            return {'needs_optimization': False}
        
        recent_metrics = self.metrics_history[-100:]
        
        # Calculate trend indicators
        response_time_trend = self._calculate_trend([m.response_time for m in recent_metrics])
        quality_trend = self._calculate_trend([m.signal_quality_score for m in recent_metrics])
        error_rate_trend = self._calculate_trend([m.error_rate for m in recent_metrics])
        
        return {
            'needs_optimization': (
                response_time_trend > 0.1 or  # Response time increasing
                quality_trend < -0.1 or       # Quality decreasing
                error_rate_trend > 0.05       # Error rate increasing
            ),
            'response_time_trend': response_time_trend,
            'quality_trend': quality_trend,
            'error_rate_trend': error_rate_trend
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend direction for a series of values."""
        if len(values) < 10:
            return 0.0
        
        # Simple linear trend calculation
        n = len(values)
        x = list(range(n))
        
        # Calculate slope
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(values)
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0
        
        slope = numerator / denominator
        return slope
    
    async def _apply_proactive_optimizations(self, trends: Dict[str, Any]):
        """Apply proactive optimizations based on trends."""
        try:
            logger.info("[OPTIMIZER] Applying proactive optimizations")
            
            optimizations_applied = 0
            
            # Optimize based on response time trend
            if trends['response_time_trend'] > 0.1:
                logger.info("[OPTIMIZER] Optimizing for response time degradation")
                # Apply response time optimizations
                optimizations_applied += 1
            
            # Optimize based on quality trend
            if trends['quality_trend'] < -0.1:
                logger.info("[OPTIMIZER] Optimizing for signal quality degradation")
                # Apply quality optimizations
                optimizations_applied += 1
            
            # Optimize based on error rate trend
            if trends['error_rate_trend'] > 0.05:
                logger.info("[OPTIMIZER] Optimizing for error rate increase")
                # Apply error rate optimizations
                optimizations_applied += 1
            
            if optimizations_applied > 0:
                self.optimization_count += optimizations_applied
                logger.info(f"[OPTIMIZER] Applied {optimizations_applied} proactive optimizations")
            
        except Exception as e:
            logger.error(f"[OPTIMIZER] Proactive optimization error: {e}")
    
    async def _generate_optimization_reports(self):
        """Generate periodic optimization reports."""
        while self.running:
            try:
                # Generate report every 6 hours
                await asyncio.sleep(21600)
                
                report = self._create_performance_report()
                await self._save_optimization_report(report)
                
            except Exception as e:
                logger.error(f"[OPTIMIZER] Report generation error: {e}")
                await asyncio.sleep(3600)
    
    def _create_performance_report(self) -> Dict[str, Any]:
        """Create comprehensive performance report."""
        if not self.metrics_history:
            return {'error': 'No metrics available'}
        
        recent_metrics = self.metrics_history[-360:]  # Last hour (6 min intervals)
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'metrics_period': f"{len(recent_metrics)} data points",
            'performance_summary': {
                'avg_response_time': statistics.mean([m.response_time for m in recent_metrics]),
                'avg_signal_quality': statistics.mean([m.signal_quality_score for m in recent_metrics]),
                'avg_execution_delay': statistics.mean([m.execution_delay for m in recent_metrics]),
                'avg_consensus_confidence': statistics.mean([m.consensus_confidence for m in recent_metrics]),
                'avg_throughput': statistics.mean([m.throughput for m in recent_metrics]),
                'avg_error_rate': statistics.mean([m.error_rate for m in recent_metrics])
            },
            'optimization_stats': {
                'total_optimizations': self.optimization_count,
                'last_optimization': self.last_optimization.isoformat() if self.last_optimization else None,
                'auto_tuning_enabled': self.auto_tuning_enabled,
                'active_alerts': len(self.active_alerts),
                'total_alerts': len(self.alert_history)
            },
            'threshold_violations': [
                {
                    'metric': alert['threshold'].metric_name,
                    'severity': alert['threshold'].severity,
                    'timestamp': alert['timestamp'].isoformat(),
                    'description': alert['threshold'].description
                }
                for alert in self.alert_history[-10:]  # Last 10 violations
            ]
        }
        
        return report
    
    async def _save_optimization_report(self, report: Dict[str, Any]):
        """Save optimization report to file."""
        try:
            report_filename = f"optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_path = os.path.join('unified_system', 'data', 'reports', report_filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            logger.info(f"[OPTIMIZER] Performance report saved: {report_filename}")
            
        except Exception as e:
            logger.error(f"[OPTIMIZER] Error saving report: {e}")
    
    async def _log_performance_summary(self):
        """Log performance summary."""
        try:
            if len(self.metrics_history) < 10:
                return
            
            recent_metrics = self.metrics_history[-10:]
            
            avg_response_time = statistics.mean([m.response_time for m in recent_metrics])
            avg_quality = statistics.mean([m.signal_quality_score for m in recent_metrics])
            avg_confidence = statistics.mean([m.consensus_confidence for m in recent_metrics])
            avg_error_rate = statistics.mean([m.error_rate for m in recent_metrics])
            
            logger.info(
                f"[OPTIMIZER] Performance Summary - "
                f"Response: {avg_response_time:.2f}s, "
                f"Quality: {avg_quality:.1%}, "
                f"Confidence: {avg_confidence:.1%}, "
                f"Errors: {avg_error_rate:.1%}, "
                f"Optimizations: {self.optimization_count}"
            )
            
        except Exception as e:
            logger.error(f"[OPTIMIZER] Error logging performance summary: {e}")
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """Get current optimization status."""
        return {
            'running': self.running,
            'auto_tuning_enabled': self.auto_tuning_enabled,
            'optimization_count': self.optimization_count,
            'last_optimization': self.last_optimization.isoformat() if self.last_optimization else None,
            'active_alerts': len(self.active_alerts),
            'metrics_collected': len(self.metrics_history),
            'performance_targets': self.performance_targets,
            'current_performance': self._get_current_performance_snapshot()
        }
    
    def _get_current_performance_snapshot(self) -> Dict[str, Any]:
        """Get current performance snapshot."""
        if not self.metrics_history:
            return {}
        
        latest = self.metrics_history[-1]
        return {
            'response_time': latest.response_time,
            'signal_quality_score': latest.signal_quality_score,
            'execution_delay': latest.execution_delay,
            'consensus_confidence': latest.consensus_confidence,
            'risk_zone_overlap': latest.risk_zone_overlap,
            'throughput': latest.throughput,
            'error_rate': latest.error_rate,
            'timestamp': latest.timestamp.isoformat()
        }

# Global performance optimizer instance
_performance_optimizer = None

def initialize_performance_optimizer(config: Dict[str, Any]) -> PerformanceOptimizer:
    """Initialize the global performance optimizer."""
    global _performance_optimizer
    _performance_optimizer = PerformanceOptimizer(config)
    return _performance_optimizer

def get_performance_optimizer() -> Optional[PerformanceOptimizer]:
    """Get the global performance optimizer instance."""
    return _performance_optimizer
