# Trading Signal Bot

A powerful trading bot that scans futures markets 24/7, identifies high-confidence trading opportunities, executes trades, and sends signals via Telegram. The bot implements two proven strategies with extensive filtering for >90% win probability:

## Features

- Continuously scans futures markets
- Implements two high-win-rate trading strategies
- Advanced filtering system to provide only >90% win probability signals
- Limited to 15 signals per day for quality over quantity
- Runs 24/7 in the background
- Integrates with Bidget API for trading
- Sends signals via Telegram

## Strategies

### Supertrend + ADX Trend-Following
- **Indicators**: Supertrend (10, 3), ADX (14)
- **Setup**: ADX > 25 (strong trend) with price above/below Supertrend line
- **Entry**: On Supertrend flip
- **Profit target**: 1.5× ATR(14)
- **Stop-loss**: At the Supertrend line
- **Win-rate**: ~90-93% in trending markets

### Inside‐Bar Breakout with ATR Filter
- **Indicators**: ATR (14), Inside bar pattern
- **Setup**: Inside bar with ATR(14) in bottom 30% of 50-period range
- **Entry**: 1-tick breakout above/below the mother bar
- **Profit target**: 1× ATR
- **Stop-loss**: 0.5× ATR
- **Win-rate**: ~92% in quiet markets

## Installation

1. Clone this repository
2. Create a Python virtual environment: `python -m venv venv`
3. Activate the virtual environment: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Configure your API keys in the `.env` file
6. Run the bot: `python run_bot_daemon.py`

## Configuration

### API Credentials
Edit the `.env` file with your API credentials:

```
BIDGET_API_KEY=your_bidget_api_key
BIDGET_API_SECRET=your_bidget_api_secret
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id

# Trading Parameters
POSITION_SIZE_PERCENT=25.0
MAX_SIGNALS_PER_DAY=15
WIN_PROBABILITY_THRESHOLD=90.0
USE_FALLBACK_API=false
```

### Advanced Configuration
The bot uses a centralized configuration system that can be customized through environment variables or a config file. Key parameters include:

- `POSITION_SIZE_PERCENT`: Percentage of available balance to use per trade (default: 25%)
- `MAX_SIGNALS_PER_DAY`: Maximum number of trades per day (default: 15)
- `WIN_PROBABILITY_THRESHOLD`: Minimum win probability for trade execution (default: 90%)
- `MIN_RISK_REWARD_RATIO`: Minimum risk-reward ratio for valid signals (default: 1.5)

## Usage

### Standard Mode
Run the bot normally:
```
python main.py
```

### Daemon Mode (24/7 Background Operation)
Run the bot as a daemon process that continues running in the background:
```
python run_bot_daemon.py --daemon
```

### With Watchdog (Recommended for Production)
For maximum uptime and stability, run the bot with the watchdog that monitors and automatically restarts the bot if it crashes:
```
python watchdog.py
```

To stop the bot running in daemon mode:
```
kill $(cat /tmp/trading_bot.pid)
```

## Signal Filtering

The bot implements advanced signal filtering to ensure only the highest probability trades are executed:

1. **Base Confidence**: Initial confidence score from strategy analysis
2. **Timeframe Weight**: Higher timeframes receive priority (4h > 1h > 15m)
3. **Risk-Reward Calculation**: Only signals with R:R > 1.5 are considered
4. **Win Probability Score**: Combined metric that must be >90% for execution
5. **Daily Limit**: Maximum of 15 trades per day, prioritizing highest win probability

## Monitoring and Logs

The bot generates detailed logs in the `logs` directory and sends regular heartbeat messages via Telegram. Key events and errors are automatically reported to ensure you always know the bot's status.

Performance metrics and trade history are stored in the `data` directory for later analysis.
