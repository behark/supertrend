# Troubleshooting Guide

This document provides solutions for common issues you might encounter when setting up and running the Crypto Alert Bot.

## Installation Issues

### Dependency Installation Problems

**Issue**: `pip install -r requirements.txt` fails with build errors.

**Solution**:
1. Make sure you have the necessary build tools:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install build-essential python3-dev
   
   # Fedora/RHEL
   sudo dnf install gcc python3-devel
   ```

2. Try installing dependencies one by one:
   ```bash
   pip install python-telegram-bot==13.15
   pip install ccxt==3.0.16
   # etc.
   ```

3. Create a clean virtual environment:
   ```bash
   python -m venv fresh_venv
   source fresh_venv/bin/activate
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

### Python Version Compatibility

**Issue**: Incompatible Python version errors.

**Solution**:
- This bot requires Python 3.8 or higher. Check your version with `python --version`
- If you're using an older version, consider using pyenv or conda to manage Python versions

## Connection Issues

### Telegram Connection Problems

**Issue**: Bot can't connect to Telegram or doesn't send messages.

**Solution**:
1. Verify your internet connection
2. Confirm `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` are correct
3. Test with the dedicated test option: `python bot.py --test`
4. Check if your bot is active in Telegram by messaging it directly
5. Ensure you've started a conversation with your bot in Telegram

### Exchange API Connection Issues

**Issue**: Can't connect to cryptocurrency exchange APIs.

**Solution**:
1. Verify your API keys are correct in the `.env` file
2. Check if API keys have the necessary permissions (read-only for scanning, trading permissions for direct trading)
3. Some exchanges have IP restrictions - check your API settings
4. Use `ccxt` test commands to verify connectivity:
   ```python
   import ccxt
   exchange = ccxt.binance({'apiKey': 'YOUR_API_KEY', 'secret': 'YOUR_SECRET'})
   print(exchange.fetch_ticker('BTC/USDT'))
   ```

## Feature-Specific Issues

### Backtesting Issues

**Issue**: Backtesting fails or produces unexpected results.

**Solution**:
1. Check that historical data is being correctly downloaded
2. Verify date ranges are valid
3. Try with a smaller subset of symbols
4. Increase logging level for detailed debugging: `python bot.py --backtest --debug`

### ML Model Issues

**Issue**: ML training fails or predictions aren't working.

**Solution**:
1. Ensure you have enough historical data for training
2. Check model directory permissions
3. Try with a simpler model configuration
4. Force model retraining: `python bot.py --train-ml --force`

### Dashboard Not Working

**Issue**: Web dashboard doesn't load or displays errors.

**Solution**:
1. Check if dashboard is running (http://localhost:8050)
2. Verify port 8050 isn't used by another application
3. Check for error messages in the console output
4. Try running with explicit host and port: `python bot.py --dashboard --host 127.0.0.1 --port 8051`

### Trading Issues

**Issue**: Trading doesn't execute or fails.

**Solution**:
1. Remember trading is in dry-run mode by default
2. Check exchange API permissions
3. Verify sufficient funds in the account
4. Look for specific error messages in logs
5. Try with a smaller trade amount to test

## Data and Performance Issues

### High Memory/CPU Usage

**Issue**: Bot consumes too much system resources.

**Solution**:
1. Reduce the number of symbols being monitored
2. Increase the scan interval in settings
3. Disable unused features (e.g., run without dashboard)
4. Use monitoring tools to identify bottlenecks

### Data Storage Problems

**Issue**: Data files corrupt or performance degradation over time.

**Solution**:
1. Back up and reset portfolio data: `cp data/portfolio/portfolio.json data/portfolio/portfolio.json.bak`
2. Check disk space availability
3. Set up periodic maintenance tasks to archive old data

## Advanced Issues

### Custom Strategy Implementation

**Issue**: Need to add a custom strategy.

**Solution**:
1. Add new strategy functions in `indicators.py`
2. Register the strategy in the main scanning loop
3. Update the risk management logic if needed
4. Add backtesting capability for the new strategy

### Multi-timeframe Analysis Problems

**Issue**: Multi-timeframe confirmation not working correctly.

**Solution**:
1. Check timeframe configuration in settings
2. Verify data is being downloaded for all required timeframes
3. Test the confirmation logic with known historical patterns

## Getting Additional Help

If you continue experiencing issues:

1. Check the logs for detailed error messages
2. Search for similar issues in the project repository
3. Enable debug mode for more verbose output: `python bot.py --debug`
4. Gather logs and configuration files for troubleshooting
5. When reporting issues, include:
   - Full error message
   - Bot version
   - Python version
   - OS details
   - Steps to reproduce the issue
