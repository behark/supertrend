# Channel Setup Guide

## Problem
Your bot is currently sending messages directly to you instead of to your "Trading Signals" channel.

## Solution

### Step 1: Get Your Channel ID

1. **Add your bot to the channel**:
   - Go to your "Trading Signals" channel
   - Click on the channel name to open channel info
   - Click "Add Admin" or "Add Member"
   - Search for your bot "@Tradingsallleeertssbot" and add it
   - Give it admin rights (as shown in your screenshots)

2. **Get the channel ID**:
   - Send any message to your "Trading Signals" channel
   - Forward that message to @userinfobot
   - The bot will show you the channel ID (e.g., `-1002675685695`)

### Step 2: Create/Update .env File

Create a `.env` file in your project root with:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=8084043323:AAE5oJYBKjVdkV-W9AFJ-8XtiL9egpoAmu8

# Channel ID (replace with your actual channel ID)
TELEGRAM_CHAT_ID=-1002675685695

# Optional settings
SCAN_INTERVAL=30
PROFIT_TARGET=100.0
```

### Step 3: Verify Bot Permissions

Make sure your bot has these permissions in the channel:
- ✅ Send Messages
- ✅ Send Media
- ✅ Post Messages

### Step 4: Test the Configuration

Run this command to test if the bot can send messages to the channel:

```bash
python test_telegram_only.py
```

### Step 5: Restart Your Bot

After updating the `.env` file, restart your bot:

```bash
python bot.py
```

## Troubleshooting

### If messages still go to personal chat:
1. Check that `TELEGRAM_CHAT_ID` is set to the channel ID (not your personal chat ID)
2. Verify the bot is added to the channel as an admin
3. Make sure the channel ID is correct (should start with `-100`)

### If bot can't send to channel:
1. Ensure the bot has admin rights in the channel
2. Check that the bot token is correct
3. Verify the channel ID is correct

### To get your personal chat ID (for reference):
1. Send a message to @userinfobot
2. It will show your personal chat ID (different from channel ID)

## Channel ID Format
- Personal chat ID: `123456789` (positive number)
- Channel ID: `-1002675685695` (negative number starting with -100)
- Group ID: `-987654321` (negative number not starting with -100) 