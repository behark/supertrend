"""
Regime Performance Routes
------------------------
API routes for regime performance logging, playbook generation,
and analytics features.
"""

import json
from typing import Dict, List, Optional, Any
from flask import Blueprint, jsonify, request, current_app
from sqlalchemy import desc

from src.analytics.regime_logger import regime_logger
from src.models.regime_performance import RegimePerformanceEntry, PlaybookEntry
from src.database.db import get_db

# Create blueprint
performance_routes = Blueprint('performance', __name__)


@performance_routes.route('/api/regime/performance-log', methods=['GET'])
def get_regime_performance_log():
    """Get the performance log of regimes."""
    try:
        db = next(get_db())
        
        # Parse query parameters
        limit = int(request.args.get('limit', 50))
        regime_type = request.args.get('regime', None)
        high_performers_only = request.args.get('high_performers', 'false').lower() == 'true'
        
        # Build query
        query = db.query(RegimePerformanceEntry)
        
        if regime_type:
            query = query.filter(RegimePerformanceEntry.regime_type == regime_type)
        
        if high_performers_only:
            query = query.filter(RegimePerformanceEntry.is_high_performer == True)
        
        # Order and limit
        entries = query.order_by(desc(RegimePerformanceEntry.timestamp)).limit(limit).all()
        
        # Convert to dict for JSON response
        result = []
        for entry in entries:
            entry_dict = {
                'id': entry.id,
                'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                'regime_type': entry.regime_type,
                'start_time': entry.start_time.isoformat() if entry.start_time else None,
                'end_time': entry.end_time.isoformat() if entry.end_time else None,
                'duration_minutes': entry.duration_minutes,
                'confidence': entry.confidence,
                
                'performance': {
                    'win_rate': entry.win_rate,
                    'avg_profit_pct': entry.avg_profit_pct,
                    'roi_pct': entry.roi_pct,
                    'max_drawdown_pct': entry.max_drawdown_pct,
                    'trade_count': entry.trade_count,
                    'outperformance': entry.outperformance_vs_default
                },
                
                'market_context': {
                    'preceding_regime': entry.preceding_regime,
                    'volatility': entry.market_volatility,
                    'adx': entry.adx_value,
                    'rsi': entry.rsi_value,
                    'trend_direction': entry.trend_direction,
                    'market_phase': entry.market_phase,
                },
                
                'pattern_analysis': {
                    'is_high_performer': entry.is_high_performer,
                    'is_outlier': entry.is_outlier,
                    'pattern_score': entry.pattern_score,
                    'statistical_significance': entry.statistical_significance
                }
            }
            result.append(entry_dict)
        
        return jsonify({
            'success': True,
            'performance_entries': result,
            'count': len(result)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching regime performance log: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_routes.route('/api/regime/performance-log', methods=['POST'])
def log_regime_performance():
    """Log the performance of a completed regime."""
    try:
        data = request.json
        
        if not data or 'regime_data' not in data or 'performance_metrics' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required data'
            }), 400
        
        # Log performance using regime logger
        entry = regime_logger.log_regime_performance(
            data['regime_data'],
            data['performance_metrics']
        )
        
        return jsonify({
            'success': True,
            'entry_id': entry.id,
            'is_high_performer': entry.is_high_performer,
            'generated_playbook': entry.is_high_performer and entry.confidence >= regime_logger.confidence_threshold
        })
        
    except Exception as e:
        current_app.logger.error(f"Error logging regime performance: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_routes.route('/api/regime/playbooks', methods=['GET'])
def get_playbooks():
    """Get all available playbook entries."""
    try:
        db = next(get_db())
        
        # Parse query parameters
        regime_type = request.args.get('regime', None)
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        # Build query
        query = db.query(PlaybookEntry)
        
        if regime_type:
            query = query.filter(PlaybookEntry.regime_type == regime_type)
        
        if active_only:
            query = query.filter(PlaybookEntry.is_active == True)
        
        # Execute query
        playbooks = query.order_by(desc(PlaybookEntry.updated_at)).all()
        
        # Convert to dict for JSON response
        result = []
        for playbook in playbooks:
            playbook_dict = {
                'id': playbook.id,
                'name': playbook.name,
                'regime_type': playbook.regime_type,
                'description': playbook.description,
                'is_active': playbook.is_active,
                'is_auto_generated': playbook.is_auto_generated,
                'confidence_threshold': playbook.confidence_threshold,
                'user_rating': playbook.user_rating,
                
                'strategy': {
                    'entry_conditions': playbook.entry_conditions,
                    'exit_conditions': playbook.exit_conditions,
                    'stop_loss_strategy': playbook.stop_loss_strategy,
                    'take_profit_strategy': playbook.take_profit_strategy,
                    'position_sizing': playbook.position_sizing,
                    'parameter_settings': playbook.parameter_settings,
                    'expected_duration': playbook.expected_duration,
                    'risk_reward_ratio': playbook.risk_reward_ratio
                },
                
                'performance': {
                    'times_applied': playbook.times_applied,
                    'success_rate': playbook.success_rate,
                    'average_roi': playbook.average_roi
                },
                
                'created_at': playbook.created_at.isoformat() if playbook.created_at else None,
                'updated_at': playbook.updated_at.isoformat() if playbook.updated_at else None
            }
            result.append(playbook_dict)
        
        return jsonify({
            'success': True,
            'playbooks': result,
            'count': len(result)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching playbooks: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_routes.route('/api/regime/playbooks/<playbook_id>', methods=['PUT'])
def update_playbook(playbook_id):
    """Update a playbook entry."""
    try:
        db = next(get_db())
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Missing update data'
            }), 400
        
        # Find playbook
        playbook = db.query(PlaybookEntry).filter(PlaybookEntry.id == playbook_id).first()
        
        if not playbook:
            return jsonify({
                'success': False,
                'error': 'Playbook not found'
            }), 404
        
        # Update fields (only allow specific fields to be updated)
        allowed_fields = [
            'name', 'description', 'is_active', 'confidence_threshold', 'user_rating',
            'entry_conditions', 'exit_conditions', 'stop_loss_strategy', 
            'take_profit_strategy', 'position_sizing'
        ]
        
        for field in allowed_fields:
            if field in data:
                setattr(playbook, field, data[field])
        
        # Handle parameter settings separately (need to merge JSON)
        if 'parameter_settings' in data:
            if playbook.parameter_settings:
                # Merge with existing settings
                current_settings = playbook.parameter_settings.copy()
                current_settings.update(data['parameter_settings'])
                playbook.parameter_settings = current_settings
            else:
                playbook.parameter_settings = data['parameter_settings']
        
        # Save changes
        db.commit()
        
        return jsonify({
            'success': True,
            'playbook_id': playbook.id
        })
        
    except Exception as e:
        db.rollback()
        current_app.logger.error(f"Error updating playbook: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_routes.route('/api/regime/playbooks/match-current', methods=['GET'])
def match_playbooks_to_current_regime():
    """Match playbooks to the current market regime."""
    try:
        # Get current regime from market analyzer
        from src.market_analyzer import market_analyzer
        current_regime = market_analyzer.get_current_market_regime()
        
        if not current_regime:
            return jsonify({
                'success': False,
                'error': 'No current regime available'
            }), 404
        
        # Match to playbooks
        matching_playbooks = regime_logger.match_current_regime_to_playbooks(current_regime)
        
        # Convert to dict for JSON response
        result = []
        for playbook in matching_playbooks:
            playbook_dict = {
                'id': playbook.id,
                'name': playbook.name,
                'regime_type': playbook.regime_type,
                'confidence_threshold': playbook.confidence_threshold,
                
                'strategy': {
                    'entry_conditions': playbook.entry_conditions,
                    'exit_conditions': playbook.exit_conditions,
                    'position_sizing': playbook.position_sizing,
                    'parameter_settings': playbook.parameter_settings,
                }
            }
            result.append(playbook_dict)
        
        return jsonify({
            'success': True,
            'current_regime': {
                'regime': current_regime['regime'],
                'confidence': current_regime['confidence']
            },
            'matching_playbooks': result,
            'count': len(result)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error matching playbooks: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@performance_routes.route('/api/regime/top-performers', methods=['GET'])
def get_top_performers():
    """Get top performing regimes."""
    try:
        # Parse query parameters
        limit = int(request.args.get('limit', 5))
        
        # Get top performers
        top_performers = regime_logger.get_top_performing_regimes(limit)
        
        # Convert to dict for JSON response
        result = []
        for entry in top_performers:
            entry_dict = {
                'id': entry.id,
                'regime_type': entry.regime_type,
                'start_time': entry.start_time.isoformat() if entry.start_time else None,
                'confidence': entry.confidence,
                'roi_pct': entry.roi_pct,
                'win_rate': entry.win_rate,
                'market_phase': entry.market_phase,
                'pattern_score': entry.pattern_score
            }
            result.append(entry_dict)
        
        return jsonify({
            'success': True,
            'top_performers': result
        })
        
    except Exception as e:
        current_app.logger.error(f"Error fetching top performers: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
