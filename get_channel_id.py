#!/usr/bin/env python3
"""
Helper script to get Telegram channel ID from a forwarded message
"""

import os
import sys

def load_dotenv():
    """
    Simple .env file loader
    """
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

def get_channel_id_from_forwarded_message():
    """
    Instructions to get channel ID from a forwarded message
    """
    print("🔍 How to get your Channel ID:")
    print("=" * 50)
    print()
    print("1. Go to your 'Trading Signals' channel")
    print("2. Send any message to the channel")
    print("3. Forward that message to @userinfobot")
    print("4. The bot will show you the channel ID")
    print()
    print("Example output from @userinfobot:")
    print("   Forwarded from")
    print("   Trading Signals (F)")
    print("   Id: -1002675685695  ← This is your channel ID")
    print()
    print("5. Use this ID in your .env file:")
    print("   TELEGRAM_CHAT_ID=-1002675685695")
    print()
    print("Note: Channel IDs start with -100 and are negative numbers")
    print("Personal chat IDs are positive numbers")

def check_current_config():
    """
    Check current Telegram configuration
    """
    load_dotenv()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    print("📋 Current Configuration:")
    print("=" * 30)
    
    if bot_token:
        print(f"✅ Bot Token: {bot_token[:20]}...")
    else:
        print("❌ Bot Token: Not found")
    
    if chat_id:
        print(f"✅ Chat ID: {chat_id}")
        if chat_id.startswith('-100'):
            print("   → This looks like a channel ID")
        elif chat_id.startswith('-'):
            print("   → This looks like a group ID")
        else:
            print("   → This looks like a personal chat ID")
    else:
        print("❌ Chat ID: Not found")
    
    print()

if __name__ == "__main__":
    print("🤖 Telegram Channel ID Helper")
    print("=" * 40)
    print()
    
    check_current_config()
    get_channel_id_from_forwarded_message()
    
    print("=" * 40)
    print("After getting your channel ID, update your .env file and restart the bot!") 