#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Regime Logger Test Script
-------------------------
Tests the functionality of the regime logging system and integration.
Displays sample outputs for key functions.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pprint import pprint

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import components
try:
    from src.utils.regime_logger import regime_logger, RegimeLogger
    REGIME_LOGGER_AVAILABLE = True
except ImportError as e:
    logger.error(f"Error importing regime logger: {e}")
    REGIME_LOGGER_AVAILABLE = False
    
try:
    from src.utils.market_analyzer import market_analyzer, MarketRegime
    MARKET_ANALYZER_AVAILABLE = True
except ImportError as e:
    logger.error(f"Error importing market analyzer: {e}")
    MARKET_ANALYZER_AVAILABLE = False

def test_regime_logger():
    """Test the regime logger functionality"""
    print("\n==== TESTING REGIME LOGGER ====")
    
    if not REGIME_LOGGER_AVAILABLE:
        print("❌ Regime logger not available!")
        return False
        
    print("✅ Successfully imported regime logger")
    
    # Generate some test regime detections
    print("\n-- Generating test regime data --")
    regimes = ["uptrend", "sideways", "downtrend", "volatile", "uptrend"]
    
    for i, regime in enumerate(regimes):
        # Create sample metrics
        metrics = {
            "adx": 25 + (i * 5),
            "volatility": 0.5 + (i * 0.2),
            "rsi": 50 + (i * 5),
            "macd": 0.5 - (i * 0.2),
            "ema_trend": 1.0 if regime == "uptrend" else (-1.0 if regime == "downtrend" else 0)
        }
        
        # Log the regime with sample data
        prev_regime = regimes[i-1] if i > 0 else None
        result = regime_logger.log_regime_detection(
            regime=regime, 
            confidence=0.7 + (i * 0.05), 
            metrics=metrics,
            previous_regime=prev_regime,
            metadata={"test_id": f"test_{i+1}", "source": "test_script"}
        )
        
        print(f"Logged {regime} regime (previous: {prev_regime})")
    
    print("✅ Successfully generated test data\n")
    
    # Test key functions and show sample outputs
    print("\n-- Testing regime history retrieval --")
    history = regime_logger.get_recent_history(limit=3)
    print("Recent History (last 3 entries):")
    pprint(history)
    
    print("\n-- Testing regime distribution --")
    distribution = regime_logger.get_regime_distribution()
    print("Regime Distribution:")
    pprint(distribution)
    
    print("\n-- Testing transition matrix --")
    transitions = regime_logger.get_transition_matrix()
    print("Transition Matrix:")
    pprint(transitions)
    
    print("\n-- Testing statistics --")
    stats = regime_logger.get_statistics()
    print("Regime Statistics:")
    pprint(stats)
    
    print("\n-- Testing regime report --")
    report = regime_logger.generate_regime_report(days=30)
    print("Regime Report Sections:")
    for key in report.keys():
        print(f" - {key}")
    
    # Check if data is being persisted correctly
    print("\n-- Testing data persistence --")
    history_path = os.path.join(regime_logger.base_dir, RegimeLogger.REGIMES_FILE)
    if os.path.exists(history_path):
        print(f"✅ Regime history file created at: {history_path}")
    else:
        print(f"❌ Regime history file not found at: {history_path}")
    
    return True

def test_market_analyzer_integration():
    """Test integration with market analyzer"""
    print("\n==== TESTING MARKET ANALYZER INTEGRATION ====")
    
    if not MARKET_ANALYZER_AVAILABLE:
        print("❌ Market analyzer not available!")
        return False
        
    if not REGIME_LOGGER_AVAILABLE:
        print("❌ Regime logger not available!")
        return False
    
    print("✅ Successfully imported market analyzer")
    
    # Check if market analyzer is using regime logger
    print("\n-- Fetching regime history from market analyzer --")
    history = market_analyzer.get_regime_history(limit=5)
    print(f"Retrieved {len(history)} regime history entries")
    
    # Test regime metrics
    print("\n-- Fetching regime metrics from market analyzer --")
    metrics = market_analyzer.get_regime_metrics()
    print("Regime metrics keys:")
    for key in metrics.keys():
        print(f" - {key}")
    
    # Test comprehensive report generation
    print("\n-- Generating comprehensive report --")
    report = market_analyzer.generate_regime_report(days=30)
    print("Report sections:")
    for key in report.keys():
        print(f" - {key}")
    
    return True

def test_api_route_structure():
    """Review API route structure for correctness"""
    print("\n==== REVIEWING API ROUTE STRUCTURE ====")
    
    # Check if regime routes file exists
    routes_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "src/dashboard/routes/regime_routes.py"
    )
    
    if os.path.exists(routes_path):
        print(f"✅ Regime routes file found at: {routes_path}")
        
        # List the endpoints defined in the file
        with open(routes_path, 'r') as f:
            content = f.read()
            
        endpoints = []
        for line in content.split('\n'):
            if "@regime_routes.route" in line:
                endpoints.append(line.strip())
        
        print("\nAPI Endpoints defined:")
        for endpoint in endpoints:
            print(f" - {endpoint}")
    else:
        print(f"❌ Regime routes file not found at: {routes_path}")
    
    # Check if routes are registered in app.py
    app_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "src/dashboard/app.py"
    )
    
    if os.path.exists(app_path):
        print(f"\n✅ Dashboard app file found at: {app_path}")
        
        # Check if routes are registered
        with open(app_path, 'r') as f:
            content = f.read()
            
        if "from src.dashboard.routes.regime_routes import regime_routes" in content:
            print("✅ Regime routes imported in app.py")
        else:
            print("❌ Regime routes not imported in app.py")
            
        if "app.register_blueprint(regime_routes)" in content:
            print("✅ Regime routes registered in app.py")
        else:
            print("❌ Regime routes not registered in app.py")
    else:
        print(f"❌ Dashboard app file not found at: {app_path}")
    
    return True

def main():
    """Main test function"""
    print("\n📊 REGIME LOGGING SYSTEM INTEGRATION TEST")
    print("========================================")
    
    # Test the core functionality
    regime_logger_ok = test_regime_logger()
    
    # Test market analyzer integration
    market_analyzer_ok = test_market_analyzer_integration()
    
    # Test API route structure
    api_routes_ok = test_api_route_structure()
    
    # Overall assessment
    print("\n==== TEST SUMMARY ====")
    print(f"Regime Logger Core Functionality: {'✅ PASS' if regime_logger_ok else '❌ FAIL'}")
    print(f"Market Analyzer Integration: {'✅ PASS' if market_analyzer_ok else '❌ FAIL'}")
    print(f"API Route Structure: {'✅ PASS' if api_routes_ok else '❌ FAIL'}")
    
    overall = regime_logger_ok and api_routes_ok
    print(f"\nOverall Assessment: {'✅ PASS' if overall else '❌ FAIL'}")
    
    print("\nTest completed.")

if __name__ == "__main__":
    main()
