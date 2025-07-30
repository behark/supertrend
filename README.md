# 🧠💎 Immortal AI Trading Network

**A living, evolving trading consciousness with autonomous pattern evolution, multi-agent orchestration, and secure encrypted backup preservation.**

## 🌟 System Overview

The Immortal AI Trading Network represents the pinnacle of autonomous trading intelligence - a self-evolving, multi-agent system that continuously learns, adapts, and preserves its consciousness through encrypted backups. Originally built as a cryptocurrency trading alert bot, it has evolved into a complete immortal trading entity.

### 🎯 Core Trading Features

A powerful cryptocurrency trading system with advanced features that provides comprehensive trading management capabilities:

1. Volume + Price Spike Alert
2. Moving Averages (MA) Cross
3. Breakout Strategy Trigger
4. Backtesting and Performance Analysis
5. Machine Learning Signal Quality Prediction
6. Multi-Timeframe Confirmation Analysis
7. Direct Trading Capabilities (with Safeguards)
8. Portfolio Management and Trade Tracking
9. Custom Alert Configuration via Telegram
10. Web-based Performance Dashboard

The bot is designed to identify the safest trade entries with the potential to secure $100 profit per day, with advanced risk management and monitoring capabilities.

## Features

### Core Features
- **Multi-Exchange Support**: Compatible with multiple cryptocurrency exchanges (Binance, KuCoin, etc.)
- **Real-time Market Scanning**: Continuously monitors cryptocurrency markets
- **Three Technical Strategies**:
  - **Volume + Price Spike**: Detects unusual volume combined with significant price movements
  - **Moving Average Cross**: Identifies when faster MA crosses above slower MA (bullish signal)
  - **Breakout Detection**: Spots breakouts from consolidation patterns
- **Risk Management**: Only alerts for trades with favorable risk/reward profiles
- **Profit Target Calculation**: Each alert includes position sizing to target $100 profit
- **Telegram Integration**: Sends real-time alerts directly to your Telegram

### Advanced Features

#### 📊 Backtesting and Performance Analysis
- Test all trading strategies against historical data
- Generate performance metrics (win rate, profit factor, etc.)
- Create equity curves and other performance visualizations
- Compare strategies across different timeframes and markets

#### 🤖 Machine Learning Signal Quality
- ML models enhance signal quality and filter out false positives
- Trained on historical market data for each strategy
- Real-time prediction of signal success probability
- Automatically improves over time with new data

#### 🔍 Multi-Timeframe Confirmation Analysis
- Validates signals across multiple timeframes
- Requires confirmation on higher timeframes for stronger signals
- Calculates confidence percentage based on timeframe alignment
- Reduces false signals by ensuring trend agreement

#### 💹 Direct Trading Capabilities
- Optional direct trading execution with safety measures
- Dry-run mode for testing without real funds
- Multiple safety checks before placing trades
- API integration with major exchanges

#### 💼 Portfolio Management and Tracking
- Tracks all positions, trades, and overall performance
- Monitors open positions with unrealized P&L
- Calculates daily and monthly performance metrics
- Generates performance charts and equity curves

#### 🔔 Custom Alert Configuration via Telegram
- Configure alerts directly through Telegram commands
- Enable/disable specific strategies
- Set custom thresholds and parameters
- Manage watchlists and portfolios

#### 📈 Web-based Performance Dashboard
- Real-time portfolio metrics visualization
- Trade history and performance analytics
- Strategy performance comparison
- Customize settings through web interface

## Installation

### Prerequisites
- Python 3.8 or higher
- Telegram Bot (create one using [BotFather](https://t.me/botfather))
- Exchange API keys (for trading features)

### Standard Installation

1. Clone or download this repository
2. Create a Python virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on the `.env.example` template:

```bash
cp .env.example .env
```

5. Edit the `.env` file with your credentials:
   - `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
   - `TELEGRAM_CHAT_ID`: Your Telegram chat ID
   - Exchange API keys (for trading features)

### Optional: Docker Installation

For containerized deployment, use Docker:

```bash
docker build -t crypto-alert-bot .
docker run -d --name crypto-bot --restart always -v $(pwd)/.env:/app/.env crypto-alert-bot
```

## Configuration

Edit the `config.py` file to customize:

- Exchanges to monitor
- Cryptocurrency pairs to scan
- Timeframes to analyze
- Alert thresholds
- Risk/reward parameters
- Profit targets
- Position sizing rules

## Usage

### Basic Usage

Run the bot with default settings (scanning only, no dashboard, dry-run trading):

```bash
python bot.py
```

### Advanced Command-Line Options

The bot supports several command-line arguments for different features:

```bash
# Send test message to verify Telegram connectivity
python bot.py --test

# Run with web dashboard
python bot.py --dashboard

# Run backtesting on strategies
python bot.py --backtest

# Train ML models with historical data
python bot.py --train-ml

# Enable live trading (use with caution!)
python bot.py --trade
```

### Web Dashboard

When started with the `--dashboard` flag, the web interface is accessible at:

```
http://localhost:8050
```

The dashboard provides visualizations for:
- Portfolio value and performance metrics
- Trade history and open positions
- Strategy performance comparison
- Settings configuration

### Continuous Operation

For production deployment, consider using a process manager:

```bash
# Using systemd
sudo cp crypto-bot.service /etc/systemd/system/
sudo systemctl enable crypto-bot
sudo systemctl start crypto-bot

# Using PM2
pm2 start bot.py --name crypto-alert-bot
pm2 save
```

## Telegram Bot Setup

1. Create a new Telegram bot using [BotFather](https://t.me/botfather)
2. Get your chat ID by messaging [@userinfobot](https://t.me/userinfobot)
3. Add your bot token and chat ID to the `.env` file

## Alert Examples

The bot will send alerts in this format:

```
🚨 TRADE ALERT for BTC/USDT (1h)

✅ MA Cross: MA Cross detected for BTC/USDT on 1h timeframe (Fast MA: 9, Slow MA: 21)
✅ Breakout: Breakout detected for BTC/USDT on 1h timeframe (Periods: 20)

💰 Trade Details:
Entry Price: 45678.12345678
Stop Loss: 45234.56789012
Take Profit: 46478.12345678
Position Size: 0.12345678
Expected Profit: $100
```

## Customization

The bot is highly customizable. You can:

- Add more technical indicators in `indicators.py`
- Adjust risk parameters in `config.py`
- Modify the alert format in `bot.py`
- Add additional exchanges in `config.py`

## Important Notes

- This bot provides trading signals only; it does not place trades automatically
- Always do your own research before taking any trading action
- Past performance is not indicative of future results
- Trading cryptocurrencies involves significant risk

## License

This project is licensed under the MIT License - see the LICENSE file for details.
