#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Trading Bot Dashboard - Flask Backend

Provides a REST API and web interface for monitoring and controlling the trading bot:
- Real-time trade status and history
- Performance metrics and analytics
- Parameter management and profile switching
- System health monitoring
- Market regime visualization
"""

import os
import sys
import json
import logging
import threading
import time
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Any, Optional, Union

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import Flask and extensions
from flask import Flask, request, jsonify, render_template, Response, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Import routes
try:
    from src.dashboard.routes.regime_routes import regime_routes
    REGIME_ROUTES_AVAILABLE = True
except ImportError as e:
    logger.error(f"Error importing regime routes: {e}")
    REGIME_ROUTES_AVAILABLE = False

# Create Flask app
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'supertrend_dashboard_key')
app.config['JSON_SORT_KEYS'] = False
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for development

# Enable CORS
CORS(app)

# Initialize SocketIO for real-time updates
socketio = SocketIO(app, cors_allowed_origins="*")

# Register route blueprints
if 'REGIME_ROUTES_AVAILABLE' in locals() and REGIME_ROUTES_AVAILABLE:
    app.register_blueprint(regime_routes)
    logger.info("Registered enhanced regime routes blueprint")

# Try to import bot components
try:
    from src.bot import TradingBot
    from src.utils.parameter_manager import parameter_manager
    from src.utils.analytics_logger import analytics_logger
    from src.utils.market_analyzer import market_analyzer, MarketRegime
    
    COMPONENTS_AVAILABLE = {
        'bot': True,
        'parameter_manager': parameter_manager is not None,
        'analytics_logger': analytics_logger is not None,
        'market_analyzer': market_analyzer is not None
    }
except ImportError as e:
    logger.error(f"Error importing bot components: {e}")
    COMPONENTS_AVAILABLE = {
        'bot': False,
        'parameter_manager': False,
        'analytics_logger': False,
        'market_analyzer': False
    }

# Bot instance (will be set when dashboard is connected to a running bot)
bot_instance = None

# Dashboard authentication
API_KEY = os.environ.get('DASHBOARD_API_KEY', 'default_api_key')

# Authentication decorator
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        provided_key = request.headers.get('X-API-Key', '')
        if provided_key != API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Dashboard status tracking
dashboard_status = {
    'start_time': datetime.now().isoformat(),
    'connected_to_bot': False,
    'last_update': None,
    'components_available': COMPONENTS_AVAILABLE,
    'active_connections': 0,
    'enhanced_routes': {
        'regime_routes': REGIME_ROUTES_AVAILABLE if 'REGIME_ROUTES_AVAILABLE' in locals() else False
    }
}

# SocketIO connection events
@socketio.on('connect')
def handle_connect():
    dashboard_status['active_connections'] += 1
    emit('status', {'status': 'connected', 'server_time': datetime.now().isoformat()})
    
@socketio.on('disconnect')
def handle_disconnect():
    dashboard_status['active_connections'] -= 1

# Root route - serve dashboard UI
@app.route('/')
def index():
    return render_template('index.html')

# API Routes
@app.route('/api/status')
@require_api_key
def api_status():
    """Get dashboard status and available components"""
    dashboard_status['last_update'] = datetime.now().isoformat()
    
    # Check bot connection
    if bot_instance:
        uptime = None
        if hasattr(bot_instance, 'start_time'):
            uptime = time.time() - bot_instance.start_time
            
        bot_status = {
            'connected': True,
            'uptime': uptime,
            'test_mode': bot_instance.test_mode if hasattr(bot_instance, 'test_mode') else None,
            'market_regime': bot_instance.market_regime if hasattr(bot_instance, 'market_regime') else "UNKNOWN"
        }
    else:
        bot_status = {'connected': False}
        
    return jsonify({
        'dashboard': dashboard_status,
        'bot': bot_status,
        'components': COMPONENTS_AVAILABLE
    })

@app.route('/api/bot/stats')
@require_api_key
def api_bot_stats():
    """Get bot statistics and current state"""
    if not bot_instance:
        return jsonify({'error': 'Bot not connected'}), 503
    
    try:
        # Basic bot statistics
        stats = {
            'market_regime': bot_instance.market_regime if hasattr(bot_instance, 'market_regime') else "UNKNOWN",
            'signals_today': len(bot_instance.daily_signals) if hasattr(bot_instance, 'daily_signals') else 0,
            'trades_today': bot_instance.daily_trades_count if hasattr(bot_instance, 'daily_trades_count') else 0,
            'active_trades': len(bot_instance.active_trades) if hasattr(bot_instance, 'active_trades') else 0
        }
        
        # Get parameters if available
        if COMPONENTS_AVAILABLE['parameter_manager']:
            stats['parameters'] = parameter_manager.get_all_parameters()
            stats['active_profile'] = parameter_manager.active_profile
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting bot stats: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/parameters', methods=['GET'])
@require_api_key
def api_parameters():
    """Get current bot parameters"""
    if not COMPONENTS_AVAILABLE['parameter_manager']:
        return jsonify({'error': 'Parameter manager not available'}), 503
    
    try:
        params = parameter_manager.get_all_parameters()
        constraints = parameter_manager.get_parameter_constraints()
        profiles = parameter_manager.get_profiles()
        active_profile = parameter_manager.active_profile
        
        return jsonify({
            'parameters': params,
            'constraints': constraints,
            'profiles': profiles,
            'active_profile': active_profile
        })
    except Exception as e:
        logger.error(f"Error getting parameters: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/parameters/<param_name>', methods=['PUT'])
@require_api_key
def api_update_parameter(param_name):
    """Update a specific parameter"""
    if not COMPONENTS_AVAILABLE['parameter_manager']:
        return jsonify({'error': 'Parameter manager not available'}), 503
    
    try:
        data = request.get_json()
        value = data.get('value')
        
        if value is None:
            return jsonify({'error': 'Missing parameter value'}), 400
        
        success = parameter_manager.set_parameter(
            parameter=param_name,
            value=value,
            source="dashboard",
            reason=f"Manual update via dashboard by {request.remote_addr}"
        )
        
        if success:
            # Emit update via SocketIO
            socketio.emit('parameter_update', {
                'parameter': param_name,
                'value': value,
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'parameter': param_name,
                'new_value': parameter_manager.get_parameter(param_name)
            })
        else:
            return jsonify({
                'success': False,
                'error': f"Failed to update parameter {param_name}"
            }), 400
    except Exception as e:
        logger.error(f"Error updating parameter {param_name}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/profiles/<profile_id>/apply', methods=['POST'])
@require_api_key
def api_apply_profile(profile_id):
    """Apply a parameter profile"""
    if not COMPONENTS_AVAILABLE['parameter_manager']:
        return jsonify({'error': 'Parameter manager not available'}), 503
    
    try:
        data = request.get_json()
        reason = data.get('reason', f"Profile applied via dashboard by {request.remote_addr}")
        
        success = parameter_manager.apply_profile(profile_id, reason=reason)
        
        if success:
            # Emit update via SocketIO
            socketio.emit('profile_change', {
                'profile': profile_id,
                'timestamp': datetime.now().isoformat()
            })
            
            return jsonify({
                'success': True,
                'profile': profile_id,
                'parameters': parameter_manager.get_all_parameters()
            })
        else:
            return jsonify({
                'success': False,
                'error': f"Failed to apply profile {profile_id}"
            }), 400
    except Exception as e:
        logger.error(f"Error applying profile {profile_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/regime')
@require_api_key
def api_market_regime():
    """Get current market regime information"""
    if not COMPONENTS_AVAILABLE['market_analyzer']:
        return jsonify({'error': 'Market analyzer not available'}), 503
    
    try:
        # Get comprehensive regime status including manual override status
        regime_status = market_analyzer.get_regime_status()
        
        # Get last detected indicators for display
        last_analysis = market_analyzer.get_last_analysis()
        
        # Format response
        response = {
            'current_regime': regime_status['current_regime'],
            'confidence': regime_status['confidence'],
            'manual_override': regime_status['manual_override'],
            'active_profile': regime_status['active_profile'],
            'timestamp': datetime.now().isoformat(),
            'metrics': {}
        }
        
        # Include indicator metrics if available
        if last_analysis and 'details' in last_analysis:
            details = last_analysis['details']
            response['metrics'] = {
                'adx': details.get('adx', 0),
                'volatility': details.get('volatility', 0),
                'trend_direction': details.get('trend_direction', 0),
                'rsi': details.get('rsi', 0),
                'ema_alignment': details.get('ema_alignment', 0),
                'bollinger_width': details.get('bollinger_width', 0),
                'rsi_divergence': details.get('rsi_divergence', 'none')
            }
        
        # Add recent history
        response['history'] = regime_status['history']
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error getting market regime: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/backtest', methods=['POST'])
@require_api_key
def api_market_backtest():
    """Run market regime backtest"""
    if not bot_instance:
        return jsonify({'error': 'Bot not connected'}), 503
    
    if not COMPONENTS_AVAILABLE['market_analyzer']:
        return jsonify({'error': 'Market analyzer not available'}), 503
    
    try:
        data = request.get_json()
        days_back = int(data.get('days_back', 30))
        include_performance = data.get('include_performance', True)
        
        # Run backtest
        results = bot_instance.run_market_backtest(
            days_back=days_back,
            include_performance=include_performance
        )
        
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error running market backtest: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/regime/history')
@require_api_key
def api_regime_history():
    """Get detailed market regime history with analytics"""
    if not COMPONENTS_AVAILABLE['market_analyzer']:
        return jsonify({'error': 'Market analyzer not available'}), 503
    
    try:
        # Parse query parameters
        timeframe = request.args.get('timeframe', '1w')
        limit = int(request.args.get('limit', 100))
        
        # Determine time range based on timeframe
        end_time = datetime.now()
        if timeframe == '1d':
            start_time = end_time - timedelta(days=1)
        elif timeframe == '3d':
            start_time = end_time - timedelta(days=3)
        elif timeframe == '1w':
            start_time = end_time - timedelta(weeks=1)
        elif timeframe == '1m':
            start_time = end_time - timedelta(days=30)
        else:
            start_time = end_time - timedelta(weeks=1)  # Default to 1 week
        
        # Get regime history
        history = market_analyzer.get_regime_history(start_time=start_time, end_time=end_time, limit=limit)
        
        # Get indicator history
        indicators = market_analyzer.get_indicator_history(start_time=start_time, end_time=end_time)
        
        # Calculate regime statistics
        stats = {}
        for entry in history:
            regime = entry.get('regime', 'UNKNOWN')
            if regime not in stats:
                stats[regime] = 0
            stats[regime] += 1
        
        # Get performance metrics if analytics logger is available
        performance = None
        if COMPONENTS_AVAILABLE['analytics_logger']:
            try:
                performance = analytics_logger.get_regime_performance(start_time=start_time, end_time=end_time)
            except Exception as e:
                logger.warning(f"Could not get regime performance: {e}")
        
        return jsonify({
            'history': history,
            'stats': stats,
            'indicators': indicators,
            'performance': performance,
            'timeframe': timeframe
        })
    except Exception as e:
        logger.error(f"Error getting regime history: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/regime/override', methods=['POST'])
@require_api_key
def api_regime_override():
    """Set or clear manual override for market regime"""
    if not COMPONENTS_AVAILABLE['market_analyzer']:
        return jsonify({'error': 'Market analyzer not available'}), 503
    
    try:
        data = request.get_json()
        enable = data.get('enable', False)
        profile_id = data.get('profile_id', None)
        
        result = market_analyzer.set_manual_override(enable=enable, profile_id=profile_id)
        
        # Emit update via SocketIO
        socketio.emit('regime_override', {
            'enabled': enable,
            'profile': profile_id,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error setting regime override: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/market/performance')
@require_api_key
def api_market_performance():
    """Get market regime performance comparison"""
    if not COMPONENTS_AVAILABLE['analytics_logger']:
        return jsonify({'error': 'Analytics logger not available'}), 503
    
    try:
        # Parse query parameters
        days = int(request.args.get('days', 30))
        include_trades = request.args.get('include_trades', 'false').lower() == 'true'
        
        # Get end time and start time
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # Get performance metrics
        performance = analytics_logger.get_regime_performance(
            start_time=start_time,
            end_time=end_time,
            include_trades=include_trades
        )
        
        # Get comparison with default parameters if available
        comparison = None
        if hasattr(analytics_logger, 'get_parameter_comparison'):
            comparison = analytics_logger.get_parameter_comparison(
                start_time=start_time,
                end_time=end_time
            )
        
        return jsonify({
            'performance': performance,
            'comparison': comparison,
            'timeframe': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'days': days
            }
        })
    except Exception as e:
        logger.error(f"Error getting market performance: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/summary')
@require_api_key
def api_analytics_summary():
    """Get analytics summary data"""
    if not COMPONENTS_AVAILABLE['analytics_logger']:
        return jsonify({'error': 'Analytics logger not available'}), 503
    
    try:
        # Generate daily summary
        daily_summary = analytics_logger.generate_daily_summary(force=True)
        
        # Get recent trades
        trades = analytics_logger.get_recent_trades(limit=10)
        
        return jsonify({
            'daily_summary': daily_summary,
            'recent_trades': trades
        })
    except Exception as e:
        logger.error(f"Error getting analytics summary: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/trades', methods=['GET'])
@require_api_key
def api_analytics_trades():
    """Get trade analytics data"""
    if not COMPONENTS_AVAILABLE['analytics_logger']:
        return jsonify({'error': 'Analytics module not available'}), 404
    
    try:
        # Parse query parameters
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Get trade data
        trades = analytics_logger.get_recent_trades(limit=limit, offset=offset)
        
        # Get trade statistics
        stats = analytics_logger.get_trade_statistics()
        
        return jsonify({
            'trades': trades,
            'statistics': stats,
            'pagination': {
                'limit': limit,
                'offset': offset
            }
        })
    except Exception as e:
        logger.error(f"Error getting trade analytics: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Get active signals from bot
@app.route('/api/bot/active_signals', methods=['GET'])
@require_api_key
def api_active_signals():
    """Get active signals from the bot"""
    if not bot_instance or not COMPONENTS_AVAILABLE['bot']:
        # Return mock data for testing if bot not connected
        if app.config.get('DEBUG', False):
            import random
            mock_signals = []
            strategies = ['supertrend_adx', 'inside_bar']
            statuses = ['active', 'executed', 'completed', 'cancelled']
            directions = ['long', 'short']
            symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'ADA/USDT']
            
            # Generate 0-3 random signals
            for _ in range(random.randint(0, 3)):
                mock_signals.append({
                    'symbol': random.choice(symbols),
                    'strategy_name': random.choice(strategies).replace('_', ' ').title(),
                    'strategy_id': random.choice(strategies),
                    'direction': random.choice(directions),
                    'timestamp': datetime.now().isoformat(),
                    'confidence': random.uniform(0.85, 0.99),
                    'status': random.choice(statuses)
                })
                
            return jsonify({'signals': mock_signals})
        return jsonify({'error': 'Bot not available'}), 404
        
    try:
        # Get active signals from bot
        signals = bot_instance.get_active_signals()
        return jsonify({'signals': signals})
    except Exception as e:
        logger.error(f"Error getting active signals: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Get signal counts for today
@app.route('/api/bot/signal_counts', methods=['GET'])
@require_api_key
def api_signal_counts():
    """Get signal count statistics"""
    if not bot_instance or not COMPONENTS_AVAILABLE['bot']:
        # Return mock data for testing
        if app.config.get('DEBUG', False):
            import random
            max_signals = 15
            return jsonify({
                'generated_count': random.randint(0, max_signals),
                'executed_count': random.randint(0, 10),
                'max_signals': max_signals
            })
        return jsonify({'error': 'Bot not available'}), 404
        
    try:
        # Get signal counts from bot
        generated_count = bot_instance.get_signals_today_count()
        executed_count = bot_instance.get_trades_today_count()
        max_signals = bot_instance.max_signals_per_day
        
        return jsonify({
            'generated_count': generated_count,
            'executed_count': executed_count,
            'max_signals': max_signals
        })
    except Exception as e:
        logger.error(f"Error getting signal counts: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Toggle strategy
@app.route('/api/bot/toggle_strategy', methods=['POST'])
@require_api_key
def api_toggle_strategy():
    """Enable or disable a strategy"""
    if not bot_instance or not COMPONENTS_AVAILABLE['bot']:
        return jsonify({'error': 'Bot not available'}), 404
        
    try:
        data = request.json
        if not data or 'strategy_id' not in data or 'enabled' not in data:
            return jsonify({'error': 'Missing required parameters: strategy_id, enabled'}), 400
            
        strategy_id = data['strategy_id']
        enabled = bool(data['enabled'])
        
        # Toggle strategy in bot
        result = bot_instance.toggle_strategy(strategy_id, enabled)
        
        # Emit socket.io event to notify clients
        if socketio:
            socketio.emit('strategy_toggled', {
                'strategy_id': strategy_id,
                'enabled': enabled,
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({
            'success': True,
            'strategy_id': strategy_id,
            'enabled': enabled,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error toggling strategy: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

def connect_to_bot(bot):
    """Connect dashboard to running bot instance"""
    global bot_instance
    bot_instance = bot
    dashboard_status['connected_to_bot'] = True
    dashboard_status['last_update'] = datetime.now().isoformat()
    logger.info(f"Dashboard connected to bot instance")

def run_dashboard(host='0.0.0.0', port=5000, debug=False, bot=None):
    """Run the dashboard web server"""
    if bot:
        connect_to_bot(bot)
    
    logger.info(f"Starting dashboard on {host}:{port}")
    socketio.run(app, host=host, port=port, debug=debug)

# Main entry point for running dashboard standalone
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Trading Bot Dashboard')
    parser.add_argument('--host', default='0.0.0.0', help='Host IP address')
    parser.add_argument('--port', type=int, default=5000, help='Port number')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    
    args = parser.parse_args()
    
    run_dashboard(host=args.host, port=args.port, debug=args.debug)
