#!/usr/bin/env python3
"""
API Server for Smart Trade Planning
----------------------------------
Exposes API endpoints to interact with the Smart Trade Planner
"""
import os
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS

# Local modules
from trade_planner import SmartTradePlanner
from playbook import Playbook
from market_regime import MarketRegime
import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("trade_planner.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all domains

# Initialize trade planner
trade_planner = SmartTradePlanner(data_dir='data')
playbook_system = Playbook(data_dir='data')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'Trade Planner API'
    })

@app.route('/api/playbooks', methods=['GET'])
def get_playbooks():
    """Get all available playbooks."""
    playbooks = playbook_system.list_playbooks()
    return jsonify({
        'status': 'success',
        'playbooks': playbooks
    })

@app.route('/api/playbooks/<regime>', methods=['GET'])
def get_playbook(regime):
    """Get a specific playbook by regime name."""
    playbook = playbook_system.get_playbook(regime)
    return jsonify({
        'status': 'success',
        'regime': regime,
        'playbook': playbook
    })

@app.route('/api/playbooks', methods=['POST'])
def add_playbook():
    """Add or update a playbook."""
    data = request.json
    if not data or 'regime' not in data or 'playbook' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Missing required fields: regime and playbook'
        }), 400
    
    playbook_system.add_playbook(data['regime'], data['playbook'])
    return jsonify({
        'status': 'success',
        'message': f"Playbook for regime '{data['regime']}' saved successfully"
    })

@app.route('/api/playbooks/<regime>', methods=['DELETE'])
def delete_playbook(regime):
    """Delete a playbook."""
    result = playbook_system.delete_playbook(regime)
    if result:
        return jsonify({
            'status': 'success',
            'message': f"Playbook for regime '{regime}' deleted successfully"
        })
    else:
        return jsonify({
            'status': 'error',
            'message': f"Playbook for regime '{regime}' not found"
        }), 404

@app.route('/api/plan', methods=['POST'])
def plan_trade():
    """Plan a trade based on provided OHLCV data and parameters."""
    data = request.json
    
    # Validate required parameters
    if not data:
        return jsonify({
            'status': 'error',
            'message': 'No data provided'
        }), 400
    
    required_fields = ['ohlcv', 'symbol', 'timeframe', 'entry_price']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return jsonify({
            'status': 'error',
            'message': f"Missing required fields: {', '.join(missing_fields)}"
        }), 400
    
    try:
        # Create DataFrame from OHLCV data
        ohlcv_data = data['ohlcv']
        df = pd.DataFrame(ohlcv_data)
        
        # Extract parameters
        symbol = data['symbol']
        timeframe = data['timeframe']
        entry_price = float(data['entry_price'])
        position_type = data.get('position_type', 'long')
        override_regime = data.get('override_regime', None)
        
        # Generate trade plan
        trade_plan = trade_planner.plan_trade(
            df=df,
            entry_price=entry_price,
            symbol=symbol,
            timeframe=timeframe,
            position_type=position_type,
            override_regime=override_regime
        )
        
        # Generate formatted message
        formatted_message = trade_planner.format_trade_plan_message(trade_plan)
        
        # Save trade plan if requested
        save_plan = data.get('save_plan', False)
        plan_path = None
        if save_plan:
            plan_path = trade_planner.save_trade_plan(trade_plan)
        
        return jsonify({
            'status': 'success',
            'trade_plan': trade_plan,
            'formatted_message': formatted_message,
            'saved_path': plan_path
        })
    
    except Exception as e:
        logger.error(f"Error planning trade: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f"Error planning trade: {str(e)}"
        }), 500

@app.route('/api/regimes', methods=['GET'])
def get_regimes():
    """Get available market regimes."""
    market_regime = MarketRegime()
    regime_list = market_regime.get_all_regimes()
    return jsonify({
        'status': 'success',
        'regimes': regime_list
    })

@app.route('/api/sample', methods=['GET'])
def get_sample_data():
    """Get sample OHLCV data for testing."""
    # Generate sample data
    dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=100, freq='1h')
    df = pd.DataFrame({
        'open': np.random.normal(100, 5, 100),
        'high': np.random.normal(105, 5, 100),
        'low': np.random.normal(95, 5, 100),
        'close': np.random.normal(100, 5, 100),
        'volume': np.random.normal(1000000, 200000, 100)
    }, index=dates)
    
    # Convert to dict for JSON response
    sample_data = {
        'ohlcv': df.reset_index().rename(columns={'index': 'timestamp'}).to_dict('records'),
        'symbol': 'BTC/USDT',
        'timeframe': '1h',
        'entry_price': df['close'].iloc[-1]
    }
    
    return jsonify({
        'status': 'success',
        'sample_data': sample_data
    })

def run_server(host='0.0.0.0', port=8060, debug=False):
    """Run the Flask server."""
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    run_server(debug=True)
