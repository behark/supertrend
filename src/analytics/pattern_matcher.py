"""
Pattern Matcher for Market Regimes
---------------------------------
This module identifies, analyzes, and predicts sequences of market regimes
to forecast future market behavior based on historical patterns.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Tuple, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from collections import defaultdict, Counter

from src.database.db import get_db
from src.models.regime_performance import RegimePerformanceEntry
from src.analytics.regime_logger import RegimePerformanceLogger
from src.utils.logger import setup_logger

logger = setup_logger('pattern_matcher')


class PatternMatcher:
    """
    Identifies patterns in regime sequences and forecasts likely regime transitions.
    """
    
    def __init__(self, db_session: Optional[Session] = None):
        """Initialize the pattern matcher."""
        self.db = db_session or next(get_db())
        self.regime_logger = RegimePerformanceLogger(self.db)
        self.min_sequence_length = 2
        self.max_sequence_length = 5
        self.min_pattern_occurrences = 3
        self.transition_threshold = 0.6  # Minimum probability to consider a transition likely
        self.patterns = {}
        self.transitions = {}
        self.labeled_patterns = {}
        
    def get_historical_regimes(self, limit: int = 200) -> List[RegimePerformanceEntry]:
        """
        Retrieve historical regime data from the database.
        
        Args:
            limit: Maximum number of regimes to retrieve
            
        Returns:
            List of RegimePerformanceEntry instances ordered by start time
        """
        try:
            regimes = self.db.query(RegimePerformanceEntry)\
                           .order_by(RegimePerformanceEntry.start_time.asc())\
                           .limit(limit)\
                           .all()
            
            logger.info(f"Retrieved {len(regimes)} historical regimes for pattern analysis")
            return regimes
            
        except Exception as e:
            logger.error(f"Error retrieving historical regimes: {str(e)}")
            return []
            
    def identify_patterns(self, min_occurrences: Optional[int] = None) -> Dict[str, Dict]:
        """
        Identify recurring patterns in historical regime sequences.
        
        Args:
            min_occurrences: Minimum number of times a pattern must occur to be considered
            
        Returns:
            Dictionary of identified patterns with metadata
        """
        min_occurrences = min_occurrences or self.min_pattern_occurrences
        regimes = self.get_historical_regimes(200)
        
        if len(regimes) < self.min_sequence_length:
            logger.warning("Insufficient historical data for pattern analysis")
            return {}
        
        # Extract regime sequence
        regime_sequence = [r.regime_type for r in regimes]
        patterns = {}
        
        # Look for patterns of different lengths
        for length in range(self.min_sequence_length, min(self.max_sequence_length + 1, len(regime_sequence))):
            for i in range(len(regime_sequence) - length + 1):
                pattern = tuple(regime_sequence[i:i+length])
                pattern_str = " → ".join(pattern)
                
                if pattern_str not in patterns:
                    patterns[pattern_str] = {
                        'sequence': pattern,
                        'occurrences': 0,
                        'positions': [],
                        'length': length,
                        'first_seen': regimes[i].start_time,
                        'performance_data': [],
                        'avg_duration': 0
                    }
                
                patterns[pattern_str]['occurrences'] += 1
                patterns[pattern_str]['positions'].append(i)
                
                # Collect performance and duration data for this pattern instance
                pattern_regimes = regimes[i:i+length]
                total_roi = sum([r.roi_pct for r in pattern_regimes if r.roi_pct is not None])
                total_duration = sum([r.duration_minutes for r in pattern_regimes if r.duration_minutes is not None])
                
                patterns[pattern_str]['performance_data'].append({
                    'total_roi': total_roi,
                    'total_duration': total_duration,
                    'start_time': regimes[i].start_time,
                    'confidence_avg': sum([r.confidence for r in pattern_regimes if r.confidence is not None]) / length
                })
        
        # Filter patterns by minimum occurrences and calculate statistics
        filtered_patterns = {}
        for pattern_str, data in patterns.items():
            if data['occurrences'] >= min_occurrences:
                # Calculate average performance metrics
                perf_data = data['performance_data']
                if perf_data:
                    data['avg_performance'] = sum([p['total_roi'] for p in perf_data]) / len(perf_data)
                    data['avg_duration'] = sum([p['total_duration'] for p in perf_data]) / len(perf_data)
                    data['avg_confidence'] = sum([p['confidence_avg'] for p in perf_data]) / len(perf_data)
                    data['reliability_score'] = (data['avg_confidence'] * 0.6) + (min(1.0, data['occurrences'] / 10) * 0.4)
                else:
                    data['avg_performance'] = 0
                    data['avg_duration'] = 0
                    data['avg_confidence'] = 0
                    data['reliability_score'] = 0
                    
                filtered_patterns[pattern_str] = data
        
        # Store results and log findings
        self.patterns = filtered_patterns
        logger.info(f"Identified {len(filtered_patterns)} recurring patterns from {len(regimes)} historical regimes")
        
        # Log top patterns by reliability
        top_patterns = sorted(filtered_patterns.items(), key=lambda x: x[1]['reliability_score'], reverse=True)[:5]
        for pattern_str, data in top_patterns:
            logger.info(f"Pattern: {pattern_str} | Occurrences: {data['occurrences']} | Reliability: {data['reliability_score']:.2f}")
        
        return filtered_patterns
        
    def calculate_transition_probabilities(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate transition probabilities between different regime types.
        
        Returns:
            Dictionary mapping regime types to their transition probabilities
        """
        regimes = self.get_historical_regimes(200)
        
        if len(regimes) < 2:
            logger.warning("Insufficient data for transition probability calculation")
            return {}
        
        # Count transitions
        transition_counts = defaultdict(lambda: defaultdict(int))
        regime_counts = defaultdict(int)
        
        for i in range(len(regimes) - 1):
            current_regime = regimes[i].regime_type
            next_regime = regimes[i + 1].regime_type
            
            transition_counts[current_regime][next_regime] += 1
            regime_counts[current_regime] += 1
        
        # Calculate probabilities
        transition_probabilities = {}
        for current_regime, transitions in transition_counts.items():
            total_transitions = regime_counts[current_regime]
            if total_transitions > 0:
                transition_probabilities[current_regime] = {
                    next_regime: count / total_transitions
                    for next_regime, count in transitions.items()
                }
        
        # Store results
        self.transitions = transition_probabilities
        
        # Log transition insights
        logger.info(f"Calculated transition probabilities for {len(transition_probabilities)} regime types")
        for regime, transitions in transition_probabilities.items():
            most_likely = max(transitions.items(), key=lambda x: x[1])
            logger.info(f"{regime} → {most_likely[0]}: {most_likely[1]:.2%} probability")
        
        return transition_probabilities
        
    def label_patterns(self) -> Dict[str, str]:
        """
        Assign meaningful labels to identified patterns based on regime characteristics.
        
        Returns:
            Dictionary mapping pattern strings to human-readable labels
        """
        if not self.patterns:
            self.identify_patterns()
        
        labeled_patterns = {}
        
        # Define pattern recognition rules
        pattern_rules = {
            # Breakout patterns
            ('sideways_high_volatility', 'strong_uptrend_low_volatility'): 'Volatility Breakout Bull',
            ('sideways_high_volatility', 'strong_downtrend_low_volatility'): 'Volatility Breakout Bear',
            ('consolidation', 'strong_uptrend_low_volatility'): 'Consolidation Breakout Bull',
            ('consolidation', 'strong_downtrend_low_volatility'): 'Consolidation Breakout Bear',
            
            # Reversal patterns
            ('strong_uptrend_low_volatility', 'sideways_high_volatility', 'strong_downtrend_low_volatility'): 'Bull to Bear Reversal',
            ('strong_downtrend_low_volatility', 'sideways_high_volatility', 'strong_uptrend_low_volatility'): 'Bear to Bull Reversal',
            
            # Continuation patterns
            ('strong_uptrend_low_volatility', 'consolidation', 'strong_uptrend_low_volatility'): 'Bull Trend Continuation',
            ('strong_downtrend_low_volatility', 'consolidation', 'strong_downtrend_low_volatility'): 'Bear Trend Continuation',
            
            # Volatility patterns
            ('sideways_high_volatility', 'sideways_high_volatility'): 'Persistent Volatility',
            ('consolidation', 'sideways_high_volatility'): 'Calm to Storm',
            ('sideways_high_volatility', 'consolidation'): 'Storm to Calm',
            
            # Trend exhaustion
            ('strong_uptrend_low_volatility', 'weak_uptrend_high_volatility'): 'Bull Trend Weakening',
            ('strong_downtrend_low_volatility', 'weak_downtrend_high_volatility'): 'Bear Trend Weakening'
        }
        
        # Apply pattern rules
        for pattern_str, pattern_data in self.patterns.items():
            sequence = pattern_data['sequence']
            
            # Check for exact matches first
            if sequence in pattern_rules:
                labeled_patterns[pattern_str] = pattern_rules[sequence]
            else:
                # Generate descriptive labels based on pattern characteristics
                label = self._generate_descriptive_label(sequence, pattern_data)
                labeled_patterns[pattern_str] = label
        
        # Store results
        self.labeled_patterns = labeled_patterns
        
        # Log labeled patterns
        logger.info(f"Labeled {len(labeled_patterns)} patterns with descriptive names")
        for pattern_str, label in labeled_patterns.items():
            occurrences = self.patterns[pattern_str]['occurrences']
            reliability = self.patterns[pattern_str]['reliability_score']
            logger.info(f"'{label}': {pattern_str} ({occurrences}x, {reliability:.2f} reliability)")
        
        return labeled_patterns
        
    def _generate_descriptive_label(self, sequence: Tuple[str, ...], pattern_data: Dict) -> str:
        """
        Generate a descriptive label for a pattern based on its characteristics.
        
        Args:
            sequence: The regime sequence tuple
            pattern_data: Pattern metadata
            
        Returns:
            Descriptive label string
        """
        # Analyze sequence characteristics
        has_uptrend = any('uptrend' in regime for regime in sequence)
        has_downtrend = any('downtrend' in regime for regime in sequence)
        has_volatility = any('high_volatility' in regime for regime in sequence)
        has_consolidation = any('consolidation' in regime or 'sideways' in regime for regime in sequence)
        
        # Performance-based descriptors
        performance = pattern_data.get('avg_performance', 0)
        reliability = pattern_data.get('reliability_score', 0)
        
        # Build label components
        label_parts = []
        
        # Direction component
        if has_uptrend and has_downtrend:
            label_parts.append('Reversal')
        elif has_uptrend:
            label_parts.append('Bullish')
        elif has_downtrend:
            label_parts.append('Bearish')
        else:
            label_parts.append('Neutral')
        
        # Volatility component
        if has_volatility:
            label_parts.append('Volatile')
        
        # Structure component
        if has_consolidation:
            label_parts.append('Consolidation')
        
        # Performance qualifier
        if performance > 3:
            label_parts.append('High-Profit')
        elif performance < -2:
            label_parts.append('Loss-Risk')
        
        # Reliability qualifier
        if reliability > 0.8:
            label_parts.append('Reliable')
        elif reliability < 0.4:
            label_parts.append('Uncertain')
        
        # Combine parts or use generic label
        if label_parts:
            return ' '.join(label_parts) + ' Pattern'
        else:
            return f'{len(sequence)}-Stage Pattern'
            
    def predict_next_regime(self, current_regime: str, recent_sequence: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Predict the most likely next regime based on current state and historical patterns.
        
        Args:
            current_regime: The current regime type
            recent_sequence: Optional list of recent regime types for context
            
        Returns:
            Dictionary containing prediction details and confidence levels
        """
        # Ensure we have transition probabilities calculated
        if not self.transitions:
            self.calculate_transition_probabilities()
        
        # Ensure we have patterns identified
        if not self.patterns:
            self.identify_patterns()
        
        predictions = []
        
        # Method 1: Direct transition probabilities
        if current_regime in self.transitions:
            for next_regime, probability in self.transitions[current_regime].items():
                if probability >= self.transition_threshold:
                    predictions.append({
                        'regime': next_regime,
                        'probability': probability,
                        'method': 'direct_transition',
                        'confidence': probability
                    })
        
        # Method 2: Pattern-based prediction
        if recent_sequence:
            # Look for patterns that match the recent sequence
            sequence_str = " → ".join(recent_sequence + [current_regime])
            
            for pattern_str, pattern_data in self.patterns.items():
                pattern_sequence = pattern_data['sequence']
                
                # Check if current sequence matches the beginning of a known pattern
                if len(pattern_sequence) > len(recent_sequence) + 1:
                    pattern_start = pattern_sequence[:len(recent_sequence) + 1]
                    current_sequence = tuple(recent_sequence + [current_regime])
                    
                    if pattern_start == current_sequence:
                        next_regime = pattern_sequence[len(recent_sequence) + 1]
                        confidence = pattern_data['reliability_score'] * (pattern_data['occurrences'] / 10)
                        
                        predictions.append({
                            'regime': next_regime,
                            'probability': min(0.95, confidence),
                            'method': 'pattern_matching',
                            'pattern': pattern_str,
                            'pattern_label': self.labeled_patterns.get(pattern_str, 'Unknown Pattern'),
                            'confidence': confidence,
                            'occurrences': pattern_data['occurrences']
                        })
        
        # Combine and rank predictions
        if predictions:
            # Remove duplicates and combine probabilities for same regime
            regime_predictions = {}
            for pred in predictions:
                regime = pred['regime']
                if regime not in regime_predictions:
                    regime_predictions[regime] = pred
                else:
                    # Combine probabilities (weighted average)
                    existing = regime_predictions[regime]
                    combined_prob = (existing['probability'] + pred['probability']) / 2
                    combined_conf = (existing['confidence'] + pred['confidence']) / 2
                    
                    regime_predictions[regime].update({
                        'probability': min(0.95, combined_prob),
                        'confidence': combined_conf,
                        'method': f"{existing['method']}, {pred['method']}"
                    })
            
            # Sort by probability
            sorted_predictions = sorted(regime_predictions.values(), 
                                      key=lambda x: x['probability'], reverse=True)
            
            return {
                'current_regime': current_regime,
                'predictions': sorted_predictions[:3],  # Top 3 predictions
                'most_likely': sorted_predictions[0],
                'prediction_confidence': sorted_predictions[0]['confidence'],
                'timestamp': datetime.utcnow()
            }
        else:
            # No strong predictions available
            return {
                'current_regime': current_regime,
                'predictions': [],
                'most_likely': None,
                'prediction_confidence': 0.0,
                'message': 'Insufficient historical data for reliable prediction',
                'timestamp': datetime.utcnow()
            }
            
    def get_forecast(self, current_regime: str, recent_sequence: Optional[List[str]] = None) -> str:
        """
        Generate a human-readable forecast based on pattern analysis.
        
        Args:
            current_regime: The current regime type
            recent_sequence: Optional list of recent regime types for context
            
        Returns:
            Human-readable forecast string
        """
        prediction = self.predict_next_regime(current_regime, recent_sequence)
        
        # Build forecast message
        forecast_lines = []
        forecast_lines.append(f"🔮 **Regime Forecast Analysis**")
        forecast_lines.append(f"📊 Current Regime: `{current_regime}`")
        
        if recent_sequence:
            sequence_str = " → ".join(recent_sequence + [current_regime])
            forecast_lines.append(f"📈 Recent Sequence: `{sequence_str}`")
        
        forecast_lines.append("")
        
        if prediction['most_likely']:
            most_likely = prediction['most_likely']
            confidence = most_likely['confidence']
            
            # Confidence level description
            if confidence >= 0.8:
                confidence_desc = "Very High 🟢"
            elif confidence >= 0.6:
                confidence_desc = "High 🟡"
            elif confidence >= 0.4:
                confidence_desc = "Medium 🟠"
            else:
                confidence_desc = "Low 🔴"
            
            forecast_lines.append(f"🎯 **Most Likely Next Regime:** `{most_likely['regime']}`")
            forecast_lines.append(f"📈 Probability: {most_likely['probability']:.1%}")
            forecast_lines.append(f"🎲 Confidence: {confidence_desc} ({confidence:.2f})")
            forecast_lines.append(f"🔍 Method: {most_likely['method'].replace('_', ' ').title()}")
            
            # Add pattern information if available
            if 'pattern_label' in most_likely:
                forecast_lines.append(f"🧩 Pattern: {most_likely['pattern_label']}")
                if 'occurrences' in most_likely:
                    forecast_lines.append(f"📊 Historical Occurrences: {most_likely['occurrences']}x")
            
            forecast_lines.append("")
            
            # Alternative predictions
            if len(prediction['predictions']) > 1:
                forecast_lines.append("🔄 **Alternative Scenarios:**")
                for i, alt_pred in enumerate(prediction['predictions'][1:3], 1):
                    forecast_lines.append(f"{i+1}. `{alt_pred['regime']}` ({alt_pred['probability']:.1%} probability)")
                forecast_lines.append("")
            
            # Generate actionable insights
            insights = self._generate_forecast_insights(prediction, current_regime)
            if insights:
                forecast_lines.append("💡 **Actionable Insights:**")
                for insight in insights:
                    forecast_lines.append(f"• {insight}")
                    
        else:
            forecast_lines.append("⚠️ **No Strong Predictions Available**")
            forecast_lines.append(f"📝 {prediction.get('message', 'Insufficient historical data')}")
            forecast_lines.append("")
            forecast_lines.append("💡 **Recommendation:** Continue monitoring current regime for pattern development")
        
        forecast_lines.append("")
        forecast_lines.append(f"⏰ Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        
        return "\n".join(forecast_lines)
        
    def _generate_forecast_insights(self, prediction: Dict[str, Any], current_regime: str) -> List[str]:
        """
        Generate actionable insights based on the forecast.
        
        Args:
            prediction: The prediction dictionary
            current_regime: Current regime type
            
        Returns:
            List of insight strings
        """
        insights = []
        most_likely = prediction.get('most_likely')
        
        if not most_likely:
            return insights
        
        next_regime = most_likely['regime']
        confidence = most_likely['confidence']
        
        # Regime-specific insights
        if 'uptrend' in next_regime:
            if confidence > 0.7:
                insights.append("Consider increasing long positions as bullish momentum may strengthen")
            insights.append("Monitor for breakout confirmation signals")
            
        elif 'downtrend' in next_regime:
            if confidence > 0.7:
                insights.append("Consider reducing long exposure or adding short positions")
            insights.append("Watch for breakdown confirmation and support levels")
            
        elif 'sideways' in next_regime or 'consolidation' in next_regime:
            insights.append("Range-bound trading strategies may be more effective")
            insights.append("Look for support/resistance levels to define trading ranges")
            
        elif 'high_volatility' in next_regime:
            insights.append("Expect increased market volatility - adjust position sizes accordingly")
            insights.append("Consider volatility-based strategies and wider stop losses")
        
        # Confidence-based insights
        if confidence > 0.8:
            insights.append("High confidence prediction - consider acting on this forecast")
        elif confidence < 0.5:
            insights.append("Low confidence prediction - wait for more confirmation")
        
        # Pattern-based insights
        if 'pattern_label' in most_likely:
            pattern_label = most_likely['pattern_label']
            if 'Breakout' in pattern_label:
                insights.append("Breakout pattern detected - prepare for directional move")
            elif 'Reversal' in pattern_label:
                insights.append("Potential reversal pattern - consider contrarian positions")
            elif 'Continuation' in pattern_label:
                insights.append("Trend continuation likely - stay with current direction")
        
        return insights
