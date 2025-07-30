#!/usr/bin/env python
"""
Launch script for Crypto Alert Bot - handles Python 3.13+ compatibility
"""
import os
import sys
import argparse
import importlib

# Apply imghdr patch for Python 3.13+
try:
    import imghdr
    print("✅ Native imghdr module found")
except ImportError:
    print("⚠️ Native imghdr module not found, applying compatibility patch...")
    sys.path.insert(0, '.')
    import compat_imghdr
    sys.modules['imghdr'] = compat_imghdr
    print("✅ Successfully patched imghdr module")

# Parse command line arguments
parser = argparse.ArgumentParser(description='Crypto Alert Bot')
parser.add_argument('--live', action='store_true', help='Run in live mode')
parser.add_argument('--scan', action='store_true', help='Run a full market scan cycle')
parser.add_argument('--test', action='store_true', help='Send a test message and exit')
parser.add_argument('--risk-level', choices=['low', 'medium', 'high'], default='high', 
                    help='Risk level for alerts (high = most secure/safe alerts only)')
args = parser.parse_args()

# Set risk level in environment variables based on command line arguments
if args.risk_level == 'high':
    # High risk level = most secure alerts only
    os.environ['MIN_SUCCESS_PROBABILITY'] = '0.6'  # 60% probability of success
    os.environ['RISK_REWARD_RATIO'] = '2.0'        # Risk-reward ratio of 2.0 or better
elif args.risk_level == 'medium':
    os.environ['MIN_SUCCESS_PROBABILITY'] = '0.5'  # 50% probability of success  
    os.environ['RISK_REWARD_RATIO'] = '1.5'        # Risk-reward ratio of 1.5 or better
else:  # low
    os.environ['MIN_SUCCESS_PROBABILITY'] = '0.4'  # 40% probability of success
    os.environ['RISK_REWARD_RATIO'] = '1.0'        # Risk-reward ratio of 1.0 or better

# Import the bot module (after imghdr patch is applied)
try:
    # For live mode, just run the normal bot without any special flags
    # The risk level is handled through environment variables
    print(f"🚀 Starting Crypto Alert Bot - Live Mode: {args.live}, Risk Level: {args.risk_level}")
    
    # Import and run the bot with appropriate command line arguments
    sys_argv_backup = sys.argv
    sys.argv = [sys.argv[0]]
    
    # Handle specific command flags
    if args.scan:
        # Run a full market scan
        sys.argv.append('--scan')
        print("🔍 Running full market scan with Bidget enhancements")
    elif args.test:
        # Send test message and exit
        sys.argv.append('--test')
        print("🧪 Sending test message and exiting")
    elif not args.live:
        # Default behavior if no specific flag is provided (non-live mode)
        sys.argv.append('--test')
        print("ℹ️ Default: Sending test message and exiting")
    
    # Add live mode if specified
    if args.live:
        sys.argv.append('--live')
        print("⚡ Running in LIVE trading mode - real orders will be executed")

    
    # Import and run the bot's main function
    from bot import main
    main()
    
    # Restore original sys.argv
    sys.argv = sys_argv_backup
    
except Exception as e:
    print(f"❌ Error running bot: {e}")
    sys.exit(1)
