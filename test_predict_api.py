#!/usr/bin/env python3
"""
Test script for the /api/regime/predict endpoint
Demonstrates both GET and POST request formats and expected JSON responses
"""

import json
from datetime import datetime

# Mock response structure for demonstration
def mock_api_response(symbol="BTCUSDT", timeframe="1h"):
    """Generate a mock API response showing the expected JSON structure"""
    
    return {
        "success": True,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request": {
            "symbol": symbol,
            "timeframe": timeframe
        },
        "current_regime": {
            "type": "strong_uptrend_low_volatility",
            "confidence": 0.87
        },
        "prediction": {
            "next_regime": "strong_uptrend_low_volatility",
            "confidence": 0.85,
            "rationale": "Strong momentum continuation pattern",
            "expected_duration": "2-4 days"
        },
        "pattern_analysis": {
            "detected_patterns": [
                {
                    "sequence": "volatile_bearish → sideways_high_volatility → strong_uptrend_low_volatility",
                    "occurrences": 23,
                    "performance": 12.4,
                    "label": "Storm to Calm"
                },
                {
                    "sequence": "sideways_high_volatility → strong_uptrend_low_volatility",
                    "occurrences": 45,
                    "performance": 8.7,
                    "label": "Breakout Bull"
                }
            ],
            "historical_performance": {},
            "sequence_analysis": ["volatile_bearish", "sideways_high_volatility"]
        },
        "trading_insights": {
            "recommended_action": "HOLD",
            "strategy": "trend_following",
            "risk_level": "medium",
            "key_levels": []
        },
        "transition_probabilities": {
            "strong_uptrend_low_volatility": 0.65,
            "sideways_high_volatility": 0.25,
            "volatile_bearish": 0.10
        },
        "forecast_text": "🔮 **Pattern Analysis Complete**\n\n**Current Regime:** `strong_uptrend_low_volatility`\n\n**Pattern Detected:** \"Storm to Calm\" 🌪️➡️🌤️\n- **Sequence:** volatile_bearish → sideways_high_volatility → strong_uptrend_low_volatility\n- **Historical Occurrences:** 23 times\n- **Average Performance:** +12.4% ROI\n\n**Next Regime Prediction:** `strong_uptrend_low_volatility` (85% confidence)\n- **Rationale:** Strong momentum continuation pattern\n- **Expected Duration:** 2-4 days\n- **Risk Level:** Medium\n\n**📈 Trading Insights:**\n✅ **Recommended Action:** HOLD/BUY on dips\n✅ **Strategy:** Trend following with tight stops\n✅ **Key Levels:** Watch for breakout above resistance\n\n**⚠️ Risk Factors:**\n- Monitor volume for confirmation\n- Watch for reversal signals at key resistance\n\n**🎯 Confidence Score:** 85/100\n\n*Last updated: 2025-07-30 00:49 UTC*",
        "metadata": {
            "pattern_matcher_version": "1.0",
            "total_patterns_analyzed": 156,
            "transition_matrix_size": 6
        }
    }

def demonstrate_api_usage():
    """Demonstrate the API endpoint usage and expected responses"""
    
    print("🚀 **API Endpoint: /api/regime/predict**\n")
    print("This endpoint provides structured JSON access to advanced pattern matching forecasts.\n")
    
    # Test cases
    test_cases = [
        {
            "method": "GET",
            "url": "/api/regime/predict",
            "description": "Default parameters (BTCUSDT, 1h)",
            "params": None
        },
        {
            "method": "GET", 
            "url": "/api/regime/predict?symbol=ETHUSDT&timeframe=4h",
            "description": "GET with query parameters",
            "params": {"symbol": "ETHUSDT", "timeframe": "4h"}
        },
        {
            "method": "POST",
            "url": "/api/regime/predict",
            "description": "POST with JSON payload",
            "params": {"symbol": "ADAUSDT", "timeframe": "1d"}
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"📋 **Test {i}: {test['description']}**")
        print(f"**Method:** {test['method']}")
        print(f"**URL:** {test['url']}")
        
        if test['method'] == 'POST' and test['params']:
            print(f"**Payload:**")
            print(f"```json")
            print(json.dumps(test['params'], indent=2))
            print(f"```")
        
        print(f"**Expected Response:**")
        print(f"```json")
        
        # Generate mock response
        symbol = test['params']['symbol'] if test['params'] and 'symbol' in test['params'] else 'BTCUSDT'
        timeframe = test['params']['timeframe'] if test['params'] and 'timeframe' in test['params'] else '1h'
        response = mock_api_response(symbol, timeframe)
        
        print(json.dumps(response, indent=2))
        print(f"```")
        print("\n" + "="*80 + "\n")

def show_error_responses():
    """Show expected error response formats"""
    
    print("⚠️ **Error Response Examples**\n")
    
    error_cases = [
        {
            "scenario": "Invalid timeframe",
            "response": {
                "success": False,
                "error": "Invalid timeframe. Supported: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w",
                "code": "INVALID_TIMEFRAME",
                "valid_timeframes": ["1m", "3m", "5m", "15m", "30m", "1h", "2h", "4h", "6h", "8h", "12h", "1d", "3d", "1w"]
            }
        },
        {
            "scenario": "Pattern matcher unavailable",
            "response": {
                "success": False,
                "error": "Pattern matching system not available. Please ensure analytics module is properly installed.",
                "code": "PATTERN_MATCHER_UNAVAILABLE"
            }
        },
        {
            "scenario": "Dependencies missing",
            "response": {
                "success": False,
                "error": "Pattern matching dependencies not available",
                "code": "IMPORT_ERROR",
                "details": "No module named 'numpy'"
            }
        }
    ]
    
    for error in error_cases:
        print(f"**{error['scenario']}:**")
        print("```json")
        print(json.dumps(error['response'], indent=2))
        print("```\n")

if __name__ == "__main__":
    demonstrate_api_usage()
    show_error_responses()
