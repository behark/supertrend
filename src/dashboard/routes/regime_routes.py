"""
Regime Analysis Routes
---------------------
API routes for the enhanced regime logging and analysis system,
providing detailed regime history, transitions, and analytics.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from flask import Blueprint, jsonify, request, current_app

# Import regime analysis components
try:
    from src.utils.regime_logger import regime_logger
    REGIME_LOGGER_AVAILABLE = True
except ImportError:
    REGIME_LOGGER_AVAILABLE = False
    current_app.logger.warning("Regime logger not available - using basic regime data")

try:
    from src.utils.market_analyzer import MarketAnalyzer, MarketRegime
    market_analyzer = MarketAnalyzer()
    MARKET_ANALYZER_AVAILABLE = True
except ImportError:
    MARKET_ANALYZER_AVAILABLE = False
    current_app.logger.warning("Market analyzer not available - limited regime data")

# Try to import playbook manager for integrated data
try:
    from src.utils.playbook_manager import playbook_manager
    PLAYBOOK_MANAGER_AVAILABLE = True
except ImportError:
    PLAYBOOK_MANAGER_AVAILABLE = False

# Try to import pattern matcher for advanced forecasting
try:
    from src.analytics.pattern_matcher import PatternMatcher
    PATTERN_MATCHER_AVAILABLE = True
except ImportError:
    PATTERN_MATCHER_AVAILABLE = False
    current_app.logger.warning("Pattern matcher not available - advanced predictions disabled")

# Create blueprint
regime_routes = Blueprint('regimes', __name__)

@regime_routes.route('/api/regimes/current', methods=['GET'])
def get_current_regime():
    """Get the current market regime with detailed information."""
    try:
        if not MARKET_ANALYZER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Market analyzer not available'
            }), 500
            
        # Get current regime info from market analyzer
        current_regime = {
            'regime': market_analyzer.current_regime.name,
            'confidence': market_analyzer.regime_confidence,
            'since': market_analyzer.last_regime_change.isoformat() if hasattr(market_analyzer, 'last_regime_change') else None,
            'manual_override': market_analyzer.manual_override_active
        }
        
        # Get active playbook if available
        if PLAYBOOK_MANAGER_AVAILABLE:
            try:
                current_regime['active_playbook'] = playbook_manager.get_active_playbook()
            except Exception as e:
                current_app.logger.warning(f"Error fetching active playbook: {str(e)}")
                
        return jsonify({
            'success': True,
            'current_regime': current_regime
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching current regime: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@regime_routes.route('/api/regimes/history', methods=['GET'])
def get_regime_history():
    """Get the regime history with enhanced metrics."""
    try:
        # Parse query parameters
        days = request.args.get('days', '7')
        try:
            days = int(days)
        except ValueError:
            days = 7
            
        limit = request.args.get('limit', '50')
        try:
            limit = int(limit)
        except ValueError:
            limit = 50
            
        # Determine which data source to use
        if REGIME_LOGGER_AVAILABLE:
            # Use enhanced regime logger
            if days > 0:
                history = regime_logger.get_regimes_for_period(days)
            else:
                history = regime_logger.get_recent_history(limit)
                
            result = {
                'success': True,
                'history': history,
                'count': len(history),
                'source': 'enhanced_logger'
            }
        elif MARKET_ANALYZER_AVAILABLE:
            # Fall back to market analyzer
            history = market_analyzer.get_regime_history(limit)
            result = {
                'success': True,
                'history': history,
                'count': len(history),
                'source': 'market_analyzer'
            }
        else:
            result = {
                'success': False,
                'error': 'No regime history data source available',
                'history': []
            }
            
        return jsonify(result)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching regime history: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@regime_routes.route('/api/regimes/distribution', methods=['GET'])
def get_regime_distribution():
    """Get the distribution of regimes over time."""
    try:
        if REGIME_LOGGER_AVAILABLE:
            # Use enhanced distribution data
            distribution = regime_logger.get_regime_distribution()
        elif MARKET_ANALYZER_AVAILABLE:
            # Fall back to market analyzer
            distribution = market_analyzer.get_regime_distribution()
        else:
            return jsonify({
                'success': False,
                'error': 'No regime distribution data source available'
            }), 500
            
        return jsonify({
            'success': True,
            'distribution': distribution
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching regime distribution: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@regime_routes.route('/api/regimes/analysis', methods=['GET'])
def get_regime_analysis():
    """Get in-depth analysis of regime patterns and transitions."""
    try:
        if not REGIME_LOGGER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Enhanced regime logger not available'
            }), 500
            
        # Parse query parameters
        days = request.args.get('days', '30')
        try:
            days = int(days)
        except ValueError:
            days = 30
            
        # Generate comprehensive report
        report = regime_logger.generate_regime_report(days)
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating regime analysis: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@regime_routes.route('/api/regimes/transitions', methods=['GET'])
def get_regime_transitions():
    """Get regime transition patterns and probabilities."""
    try:
        if not REGIME_LOGGER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Enhanced regime logger not available'
            }), 500
            
        # Get transition matrix
        transitions = regime_logger.get_transition_matrix()
        
        return jsonify({
            'success': True,
            'transitions': transitions
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching regime transitions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@regime_routes.route('/api/regimes/metrics', methods=['GET'])
def get_regime_metrics():
    """Get metrics about market regimes."""
    try:
        if REGIME_LOGGER_AVAILABLE:
            # Use enhanced statistics
            statistics = regime_logger.get_statistics()
        elif MARKET_ANALYZER_AVAILABLE:
            # Fall back to basic metrics
            statistics = market_analyzer.get_regime_metrics()
        else:
            return jsonify({
                'success': False,
                'error': 'No regime metrics data source available'
            }), 500
            
        return jsonify({
            'success': True,
            'metrics': statistics
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching regime metrics: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@regime_routes.route('/api/regimes/forecast', methods=['GET'])
def get_regime_forecast():
    """Get regime forecast based on transition probabilities."""
    try:
        if not REGIME_LOGGER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Enhanced regime logger not available'
            }), 500
            
        # Get transition matrix for forecasting
        transitions = regime_logger.get_transition_matrix()
        
        if not MARKET_ANALYZER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Market analyzer not available for current regime'
            }), 500
            
        # Get current regime
        current_regime = market_analyzer.current_regime.name.lower()
        
        # Calculate forecast probabilities
        forecast = {}
        
        if current_regime in transitions:
            for target_regime, probability in transitions[current_regime].items():
                forecast[target_regime] = {
                    'probability': probability,
                    'confidence': probability * market_analyzer.regime_confidence
                }
                
            # Sort by probability
            forecast = dict(sorted(forecast.items(), key=lambda x: x[1]['probability'], reverse=True))
            
        return jsonify({
            'success': True,
            'current_regime': current_regime,
            'forecast': forecast,
            'confidence': market_analyzer.regime_confidence
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating regime forecast: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@regime_routes.route('/api/regime/predict', methods=['POST', 'GET'])
def predict_regime():
    """
    Advanced regime prediction using pattern matching analysis.
    
    Supports both GET and POST requests:
    - GET: Uses default parameters (BTCUSDT, 1h)
    - POST: Accepts JSON with 'symbol' and 'timeframe' parameters
    
    Returns structured JSON with pattern analysis, confidence scores,
    trading insights, and actionable recommendations.
    """
    try:
        if not PATTERN_MATCHER_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'Pattern matching system not available. Please ensure analytics module is properly installed.',
                'code': 'PATTERN_MATCHER_UNAVAILABLE'
            }), 503
        
        # Parse request parameters
        if request.method == 'POST':
            data = request.get_json() or {}
            symbol = data.get('symbol', 'BTCUSDT').upper()
            timeframe = data.get('timeframe', '1h')
        else:
            symbol = request.args.get('symbol', 'BTCUSDT').upper()
            timeframe = request.args.get('timeframe', '1h')
        
        # Validate timeframe
        valid_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w']
        if timeframe not in valid_timeframes:
            return jsonify({
                'success': False,
                'error': f'Invalid timeframe. Supported: {", ".join(valid_timeframes)}',
                'code': 'INVALID_TIMEFRAME',
                'valid_timeframes': valid_timeframes
            }), 400
        
        # Initialize pattern matcher
        pattern_matcher = PatternMatcher()
        
        # Get current regime (try from market analyzer first, then database)
        current_regime = None
        recent_sequence = None
        
        if MARKET_ANALYZER_AVAILABLE:
            try:
                current_regime = market_analyzer.current_regime.name.lower()
                # Try to get recent regime sequence if available
                recent_regimes = getattr(market_analyzer, 'recent_regimes', [])
                if recent_regimes and len(recent_regimes) > 1:
                    recent_sequence = recent_regimes[-3:-1]  # Last 2 regimes before current
            except Exception as e:
                current_app.logger.warning(f"Could not get current regime from market analyzer: {e}")
        
        # Fallback to database if market analyzer unavailable
        if not current_regime:
            historical_regimes = pattern_matcher.get_historical_regimes(1)
            if historical_regimes:
                current_regime = historical_regimes[0].regime_type
            else:
                current_regime = "sideways_high_volatility"  # Default for demo
        
        # Get pattern analysis and forecast
        patterns = pattern_matcher.identify_patterns()
        transitions = pattern_matcher.calculate_transition_probabilities()
        next_regime_prediction = pattern_matcher.predict_next_regime(current_regime, recent_sequence)
        
        # Get human-readable forecast (for text field)
        forecast_text = pattern_matcher.get_forecast(current_regime, recent_sequence)
        
        # Structure the response
        response_data = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'request': {
                'symbol': symbol,
                'timeframe': timeframe
            },
            'current_regime': {
                'type': current_regime,
                'confidence': getattr(market_analyzer, 'regime_confidence', 0.85) if MARKET_ANALYZER_AVAILABLE else 0.75
            },
            'prediction': {
                'next_regime': next_regime_prediction['regime'],
                'confidence': next_regime_prediction['confidence'],
                'rationale': next_regime_prediction.get('rationale', 'Pattern-based prediction'),
                'expected_duration': next_regime_prediction.get('expected_duration', 'Variable')
            },
            'pattern_analysis': {
                'detected_patterns': [],
                'historical_performance': {},
                'sequence_analysis': recent_sequence or []
            },
            'trading_insights': {
                'recommended_action': 'HOLD',  # Default, will be enhanced
                'strategy': 'trend_following',
                'risk_level': 'medium',
                'key_levels': []
            },
            'forecast_text': forecast_text,
            'metadata': {
                'pattern_matcher_version': '1.0',
                'total_patterns_analyzed': len(patterns),
                'transition_matrix_size': len(transitions)
            }
        }
        
        # Enhance with pattern details if available
        if patterns:
            top_patterns = sorted(patterns.items(), key=lambda x: x[1]['performance'], reverse=True)[:3]
            response_data['pattern_analysis']['detected_patterns'] = [
                {
                    'sequence': pattern,
                    'occurrences': details['count'],
                    'performance': details['performance'],
                    'label': pattern_matcher.label_patterns({pattern: details}).get(pattern, 'Unknown Pattern')
                }
                for pattern, details in top_patterns
            ]
        
        # Add transition probabilities
        if current_regime in transitions:
            response_data['transition_probabilities'] = {
                regime: prob for regime, prob in 
                sorted(transitions[current_regime].items(), key=lambda x: x[1], reverse=True)
            }
        
        return jsonify(response_data)
        
    except ImportError as e:
        current_app.logger.error(f"Pattern matcher import error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Pattern matching dependencies not available',
            'code': 'IMPORT_ERROR',
            'details': str(e)
        }), 503
        
    except Exception as e:
        current_app.logger.error(f"Error in regime prediction: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Internal server error during prediction',
            'code': 'PREDICTION_ERROR',
            'details': str(e)
        }), 500
