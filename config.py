"""
Configuration settings for the Crypto Alert Bot
Edit these settings to customize the bot's behavior
"""

# List of exchanges to scan
EXCHANGES = ['bybit']  # Restricted to Bybit only for USDT Futures

# How often to scan markets (in minutes)
SCAN_INTERVAL = 30

# List of specific symbols to scan - restricted to low-cost pairs under $1
# Format: 'XRP/USDT', 'ADA/USDT', etc.
SYMBOLS_TO_SCAN = ['XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'TRX/USDT', 'XLM/USDT']  # Only trade these low-cost pairs

# Maximum price filter for coins (in USD)
MAX_COIN_PRICE = 1.0  # Only trade coins under $1

# Timeframes to analyze - restricted to 15m to 3h range
# Available: '15m', '30m', '1h', '2h', '3h'
TIMEFRAMES = ['15m', '30m', '1h', '2h', '3h']

# Target profit per trade (in USD)
PROFIT_TARGET = 100.0

# Minimum risk-reward ratio for safe trades
RISK_REWARD_RATIO = 2.0

# Volume + Price Spike settings
VOLUME_THRESHOLD = 2.0  # Volume must be 200% of average
PRICE_CHANGE_THRESHOLD = 1.5  # Price must change by at least 1.5%

# Moving Average (MA) Cross settings
FAST_MA = 9
SLOW_MA = 21

# Breakout strategy settings
BREAKOUT_PERIODS = 20

# Filter settings for safe trades
MAX_DRAWDOWN_PERCENT = 2.0  # Maximum allowed drawdown as percentage of account
MIN_SUCCESS_PROBABILITY = 0.9  # Strict 90% win probability required
MIN_DAILY_VOLUME = 1000000  # Minimum 24h volume in USDT

# Bybit USDT Futures trading settings
LEVERAGE = 20  # Fixed 20x leverage
BALANCE_PERCENTAGE = 0.3  # Use 30% of available balance per trade
FUTURES_ONLY = True  # Only trade USDT perpetual futures, no spot trading
MAX_TELEGRAM_SIGNALS = 30  # Maximum number of filtered signals to send per day

# Daily trading limits
MAX_DAILY_TRADES = 15  # Maximum number of trades to execute per day

# Position sizing settings - overridden by BALANCE_PERCENTAGE for Bybit
MAX_POSITION_SIZE_PERCENT = 30.0  # Use 30% of available balance per trade

# Consolidated settings dictionary for bot.py
SETTINGS = {
    'exchanges': EXCHANGES,
    'scan_interval': SCAN_INTERVAL,
    'symbols_to_scan': SYMBOLS_TO_SCAN,
    'timeframes': TIMEFRAMES,
    'profit_target': PROFIT_TARGET,
    'risk_reward_ratio': RISK_REWARD_RATIO,
    'volume_threshold': VOLUME_THRESHOLD,
    'price_change_threshold': PRICE_CHANGE_THRESHOLD,
    'fast_ma': FAST_MA,
    'slow_ma': SLOW_MA,
    'breakout_periods': BREAKOUT_PERIODS,
    'max_drawdown_percent': MAX_DRAWDOWN_PERCENT,
    'min_success_probability': MIN_SUCCESS_PROBABILITY,
    'min_daily_volume': MIN_DAILY_VOLUME,
    'max_position_size_percent': MAX_POSITION_SIZE_PERCENT,
    'max_daily_trades': MAX_DAILY_TRADES,
    
    # Bidget specific settings
    'max_coin_price': MAX_COIN_PRICE,
    'leverage': LEVERAGE,
    'balance_percentage': BALANCE_PERCENTAGE,
    'futures_only': FUTURES_ONLY,
    'max_telegram_signals': MAX_TELEGRAM_SIGNALS,
}
