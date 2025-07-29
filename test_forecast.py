#!/usr/bin/env python3
"""
Test script for the /forecast Telegram command
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.integrations.telegram_commands import telegram_commands

def test_forecast_command():
    """Test the forecast command with various inputs"""
    
    print("🧪 Testing /forecast command implementation...\n")
    
    # Test cases
    test_cases = [
        # (args, description)
        ([], "Default parameters (BTCUSDT, 1h)"),
        (["ETHUSDT"], "Custom symbol, default timeframe"),
        (["BTCUSDT", "4h"], "Custom symbol and timeframe"),
        (["ADAUSDT", "1d"], "Different symbol and daily timeframe"),
        (["BTCUSDT", "invalid"], "Invalid timeframe test"),
    ]
    
    for args, description in test_cases:
        print(f"📋 Test: {description}")
        print(f"Command: /forecast {' '.join(args)}")
        print("Response:")
        print("-" * 50)
        
        try:
            response = telegram_commands._cmd_forecast(args)
            print(response)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    test_forecast_command()
