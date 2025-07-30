"""
Backtesting Module for Cryptocurrency Trading Strategies
Tests trading strategies against historical data to evaluate performance
"""
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import ccxt
import json

from indicators import (
    check_volume_price_spike,
    check_ma_cross,
    check_breakout,
    calculate_risk_metrics
)
from risk_manager import RiskManager
from chart_generator import ChartGenerator

logger = logging.getLogger(__name__)

class Backtester:
    """Backtester for cryptocurrency trading strategies"""
    
    def __init__(self, exchange_id='binance', symbols=None, timeframes=None, 
                 start_date=None, end_date=None, config=None, output_dir='backtest_results'):
        """Initialize the backtester.
        
        Args:
            exchange_id (str): Exchange ID to fetch historical data from
            symbols (list): List of symbols to backtest
            timeframes (list): List of timeframes to backtest
            start_date (str): Start date for backtesting in YYYY-MM-DD format
            end_date (str): End date for backtesting in YYYY-MM-DD format
            config (dict): Configuration parameters
            output_dir (str): Directory to save backtest results
        """
        self.exchange_id = exchange_id
        self.symbols = symbols or ['BTC/USDT', 'ETH/USDT']
        self.timeframes = timeframes or ['1h', '4h']
        
        # Set default date range if not provided (last 90 days)
        end_date = end_date or datetime.now().strftime('%Y-%m-%d')
        start_date = start_date or (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
        
        self.start_date = pd.Timestamp(start_date)
        self.end_date = pd.Timestamp(end_date)
        
        # Convert to milliseconds for CCXT
        self.start_timestamp = int(self.start_date.timestamp() * 1000)
        self.end_timestamp = int(self.end_date.timestamp() * 1000)
        
        # Configuration for strategies
        self.config = config or {}
        
        # Default configuration if not provided
        self.config.setdefault('volume_threshold', 2.0)
        self.config.setdefault('price_change_threshold', 1.5)
        self.config.setdefault('fast_ma', 9)
        self.config.setdefault('slow_ma', 21)
        self.config.setdefault('breakout_periods', 20)
        self.config.setdefault('risk_reward_ratio', 2.0)
        self.config.setdefault('profit_target', 100.0)
        self.config.setdefault('max_risk_percent', 1.0)
        self.config.setdefault('initial_capital', 10000.0)
        
        # Output directory
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize exchange
        self.exchange = self._initialize_exchange(exchange_id)
        
        # Initialize risk manager
        self.risk_manager = RiskManager(
            risk_reward_ratio=self.config['risk_reward_ratio'],
            max_drawdown_percent=2.0,
            min_daily_volume=1000000,
            min_success_probability=0.6
        )
        
        # Initialize chart generator
        self.chart_generator = ChartGenerator(output_dir=os.path.join(output_dir, 'charts'))
        
        # Safely log initialization, using self.symbols and self.timeframes which have default values
        logger.info(f"Backtester initialized with {len(self.symbols)} symbols, {len(self.timeframes)} timeframes")
        logger.info(f"Backtesting period: {start_date} to {end_date}")
        
    def _initialize_exchange(self, exchange_id):
        """Initialize exchange instance for historical data fetching."""
        try:
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({
                'enableRateLimit': True,
                'options': {
                    'adjustForTimeDifference': True
                }
            })
            return exchange
        except Exception as e:
            logger.error(f"Error initializing exchange {exchange_id}: {str(e)}")
            return None
    
    def fetch_historical_data(self, symbol, timeframe):
        """Fetch historical OHLCV data for backtesting."""
        try:
            all_candles = []
            since = self.start_timestamp
            
            # Fetch data in chunks due to exchange limits
            while since < self.end_timestamp:
                logger.debug(f"Fetching {symbol} {timeframe} data since {pd.Timestamp(since, unit='ms')}")
                candles = self.exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
                if not candles:
                    break
                
                all_candles.extend(candles)
                since = candles[-1][0] + 1  # Next candle timestamp
                
                # Sleep to avoid rate limits
                import time
                time.sleep(self.exchange.rateLimit / 1000)
            
            # Convert to DataFrame
            df = pd.DataFrame(all_candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # Filter by date range
            df = df[(df['timestamp'] >= self.start_date) & (df['timestamp'] <= self.end_date)]
            
            return df
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol} {timeframe}: {str(e)}")
            return pd.DataFrame()
    
    def backtest_strategy(self, strategy, symbol, timeframe):
        """Backtest a strategy on historical data.
        
        Args:
            strategy (str): Strategy name ('volume_spike', 'ma_cross', 'breakout', 'combined')
            symbol (str): Symbol to backtest
            timeframe (str): Timeframe to backtest
            
        Returns:
            dict: Backtest results
        """
        # Fetch historical data
        df = self.fetch_historical_data(symbol, timeframe)
        if df.empty:
            logger.error(f"No historical data for {symbol} {timeframe}")
            return {
                'strategy': strategy,
                'symbol': symbol,
                'timeframe': timeframe,
                'trades': [],
                'metrics': {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'profit_factor': 0,
                    'total_return': 0,
                    'max_drawdown': 0,
                    'sharpe_ratio': 0,
                    'annual_return': 0
                }
            }
        
        # Initialize results
        trades = []
        positions = {}  # Currently open positions
        
        # Simulate trading day by day
        for i in range(max(self.config['slow_ma'], self.config['breakout_periods']), len(df)):
            current_date = df.iloc[i]['timestamp']
            
            # Get historical data up to current date (avoid lookahead bias)
            historical_df = df.iloc[:i+1]
            
            # Check for signals based on strategy
            signal = False
            
            if strategy == 'volume_spike' or strategy == 'combined':
                signal = check_volume_price_spike(
                    historical_df,
                    volume_threshold=self.config['volume_threshold'],
                    price_change_threshold=self.config['price_change_threshold']
                )
            
            if (strategy == 'ma_cross' or strategy == 'combined') and not signal:
                signal = check_ma_cross(
                    historical_df,
                    fast_ma=self.config['fast_ma'],
                    slow_ma=self.config['slow_ma']
                )
            
            if (strategy == 'breakout' or strategy == 'combined') and not signal:
                signal = check_breakout(
                    historical_df,
                    periods=self.config['breakout_periods']
                )
            
            # Check for exit signals on open positions
            for position_id in list(positions.keys()):
                position = positions[position_id]
                current_price = df.iloc[i]['close']
                
                # Check if stop loss hit
                if current_price <= position['stop_loss']:
                    # Close position at stop loss
                    trade = position.copy()
                    trade['exit_date'] = current_date
                    trade['exit_price'] = position['stop_loss']
                    trade['profit'] = (position['stop_loss'] - position['entry_price']) * position['position_size']
                    trade['return'] = (position['stop_loss'] / position['entry_price'] - 1) * 100
                    trade['result'] = 'loss'
                    trades.append(trade)
                    del positions[position_id]
                    continue
                
                # Check if take profit hit
                if current_price >= position['take_profit']:
                    # Close position at take profit
                    trade = position.copy()
                    trade['exit_date'] = current_date
                    trade['exit_price'] = position['take_profit']
                    trade['profit'] = (position['take_profit'] - position['entry_price']) * position['position_size']
                    trade['return'] = (position['take_profit'] / position['entry_price'] - 1) * 100
                    trade['result'] = 'win'
                    trades.append(trade)
                    del positions[position_id]
                    continue
                
                # Close position if held for max holding period (e.g. 14 days)
                max_holding_days = 14
                if (current_date - position['entry_date']).days >= max_holding_days:
                    trade = position.copy()
                    trade['exit_date'] = current_date
                    trade['exit_price'] = current_price
                    trade['profit'] = (current_price - position['entry_price']) * position['position_size']
                    trade['return'] = (current_price / position['entry_price'] - 1) * 100
                    trade['result'] = 'win' if trade['profit'] > 0 else 'loss'
                    trades.append(trade)
                    del positions[position_id]
            
            # If signal detected, open new position
            if signal:
                entry_price = df.iloc[i]['close']
                
                # Calculate stop loss and take profit
                stop_loss, volatility = calculate_risk_metrics(historical_df, entry_price)
                
                # Calculate position size
                position_size = self.risk_manager.calculate_position_size(
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    target_profit=self.config['profit_target'],
                    max_risk_percent=self.config['max_risk_percent']
                )
                
                # Calculate take profit
                price_move_needed = self.config['profit_target'] / position_size if position_size > 0 else 0
                take_profit = entry_price + price_move_needed
                
                # Check if trade is safe
                is_safe, safety_reasons = self.risk_manager.is_safe_trade(
                    df=historical_df,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    volume_24h=df.iloc[i]['volume'] * entry_price  # Estimate 24h volume
                )
                
                if is_safe:
                    # Open position
                    position_id = f"{symbol}_{current_date.strftime('%Y%m%d%H%M%S')}"
                    positions[position_id] = {
                        'id': position_id,
                        'symbol': symbol,
                        'strategy': strategy,
                        'timeframe': timeframe,
                        'entry_date': current_date,
                        'entry_price': entry_price,
                        'stop_loss': stop_loss,
                        'take_profit': take_profit,
                        'position_size': position_size,
                        'risk': entry_price - stop_loss,
                        'reward': take_profit - entry_price
                    }
        
        # Close any remaining open positions at the end of the backtest period
        last_price = df.iloc[-1]['close']
        for position_id, position in positions.items():
            trade = position.copy()
            trade['exit_date'] = df.iloc[-1]['timestamp']
            trade['exit_price'] = last_price
            trade['profit'] = (last_price - position['entry_price']) * position['position_size']
            trade['return'] = (last_price / position['entry_price'] - 1) * 100
            trade['result'] = 'win' if trade['profit'] > 0 else 'loss'
            trades.append(trade)
        
        # Calculate performance metrics
        metrics = self.calculate_performance_metrics(trades, self.config['initial_capital'])
        
        # Generate backtest report
        report = {
            'strategy': strategy,
            'symbol': symbol,
            'timeframe': timeframe,
            'trades': trades,
            'metrics': metrics
        }
        
        # Generate equity curve chart
        if trades:
            self.generate_equity_curve(trades, symbol, strategy, timeframe)
        
        return report
    
    def calculate_performance_metrics(self, trades, initial_capital):
        """Calculate trading performance metrics.
        
        Args:
            trades (list): List of trades
            initial_capital (float): Initial capital
            
        Returns:
            dict: Performance metrics
        """
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'annual_return': 0
            }
        
        # Basic metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['result'] == 'win')
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # Profit metrics
        total_profit = sum(t['profit'] for t in trades if t['result'] == 'win')
        total_loss = abs(sum(t['profit'] for t in trades if t['result'] == 'loss'))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Calculate equity curve and drawdowns
        equity = [initial_capital]
        for trade in sorted(trades, key=lambda x: x['exit_date']):
            equity.append(equity[-1] + trade['profit'])
        
        max_equity = initial_capital
        max_drawdown = 0
        
        for e in equity:
            max_equity = max(max_equity, e)
            drawdown = (max_equity - e) / max_equity * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate returns
        total_return = (equity[-1] / initial_capital - 1) * 100
        
        # Calculate annualized return and Sharpe ratio
        if len(trades) >= 2:
            start_date = min(t['entry_date'] for t in trades)
            end_date = max(t['exit_date'] for t in trades)
            days = (end_date - start_date).days
            
            if days > 0:
                annual_return = total_return / days * 365
                
                # Calculate daily returns for Sharpe ratio
                daily_returns = []
                daily_equity = {}
                
                # Group trades by exit date
                for trade in trades:
                    exit_date = trade['exit_date'].date()
                    if exit_date not in daily_equity:
                        daily_equity[exit_date] = 0
                    daily_equity[exit_date] += trade['profit']
                
                # Calculate daily returns
                prev_equity = initial_capital
                for date in sorted(daily_equity.keys()):
                    curr_equity = prev_equity + daily_equity[date]
                    daily_return = (curr_equity / prev_equity - 1) * 100
                    daily_returns.append(daily_return)
                    prev_equity = curr_equity
                
                # Calculate Sharpe ratio
                if daily_returns:
                    avg_return = np.mean(daily_returns)
                    std_return = np.std(daily_returns)
                    sharpe_ratio = np.sqrt(252) * (avg_return / std_return) if std_return > 0 else 0
                else:
                    sharpe_ratio = 0
            else:
                annual_return = 0
                sharpe_ratio = 0
        else:
            annual_return = 0
            sharpe_ratio = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_return': total_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'annual_return': annual_return
        }
    
    def generate_equity_curve(self, trades, symbol, strategy, timeframe):
        """Generate equity curve chart for backtest results.
        
        Args:
            trades (list): List of trades
            symbol (str): Symbol
            strategy (str): Strategy name
            timeframe (str): Timeframe
        """
        if not trades:
            return
        
        # Sort trades by exit date
        sorted_trades = sorted(trades, key=lambda x: x['exit_date'])
        
        # Calculate equity curve
        dates = [sorted_trades[0]['entry_date']]
        equity = [self.config['initial_capital']]
        
        for trade in sorted_trades:
            dates.append(trade['exit_date'])
            equity.append(equity[-1] + trade['profit'])
        
        # Plot equity curve
        plt.figure(figsize=(12, 6))
        plt.plot(dates, equity, 'b-')
        plt.title(f'Equity Curve - {symbol} {strategy} ({timeframe})')
        plt.xlabel('Date')
        plt.ylabel('Equity')
        plt.grid(True)
        
        # Mark trades on the curve
        for trade in sorted_trades:
            marker = 'go' if trade['result'] == 'win' else 'ro'
            plt.plot([trade['exit_date']], [equity[dates.index(trade['exit_date'])]], marker)
        
        # Save chart
        filename = f"{self.output_dir}/equity_curve_{symbol.replace('/', '_')}_{strategy}_{timeframe}.png"
        plt.savefig(filename)
        plt.close()
        
        logger.info(f"Equity curve saved to {filename}")
    
    def run_backtest(self, strategies=None):
        """Run backtest for all strategies, symbols, and timeframes.
        
        Args:
            strategies (list): List of strategies to backtest, default is all
            
        Returns:
            dict: Aggregated backtest results
        """
        strategies = strategies or ['volume_spike', 'ma_cross', 'breakout', 'combined']
        
        results = {}
        for strategy in strategies:
            strategy_results = {
                'symbol_results': {}
            }
            
            for symbol in self.symbols:
                symbol_results = {
                    'timeframe_results': {}
                }
                
                for timeframe in self.timeframes:
                    logger.info(f"Backtesting {strategy} strategy on {symbol} {timeframe}")
                    result = self.backtest_strategy(strategy, symbol, timeframe)
                    symbol_results['timeframe_results'][timeframe] = result
                
                # Aggregate symbol metrics across timeframes
                all_trades = []
                for tf_result in symbol_results['timeframe_results'].values():
                    all_trades.extend(tf_result['trades'])
                
                symbol_metrics = self.calculate_performance_metrics(all_trades, self.config['initial_capital'])
                symbol_results['metrics'] = symbol_metrics
                strategy_results['symbol_results'][symbol] = symbol_results
            
            # Aggregate strategy metrics across symbols
            all_trades = []
            for symbol_result in strategy_results['symbol_results'].values():
                for tf_result in symbol_result['timeframe_results'].values():
                    all_trades.extend(tf_result['trades'])
            
            strategy_metrics = self.calculate_performance_metrics(all_trades, self.config['initial_capital'])
            strategy_results['metrics'] = strategy_metrics
            results[strategy] = strategy_results
        
        # Save results to file
        self._save_results(results)
        
        return results
    
    def _save_results(self, results):
        """Save backtest results to file."""
        # Convert datetime objects to strings for JSON serialization
        results_copy = self._convert_dates_to_str(results)
        
        # Save as JSON
        filename = os.path.join(self.output_dir, f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(filename, 'w') as f:
            json.dump(results_copy, f, indent=2)
        
        logger.info(f"Backtest results saved to {filename}")
        
        # Generate summary report
        self._generate_summary_report(results, filename)
    
    def _convert_dates_to_str(self, obj):
        """Convert datetime objects to strings for JSON serialization."""
        if isinstance(obj, dict):
            return {k: self._convert_dates_to_str(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_dates_to_str(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return obj
    
    def _generate_summary_report(self, results, json_file):
        """Generate summary report from backtest results."""
        report = "# Cryptocurrency Strategy Backtesting Report\n\n"
        report += f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Backtest period: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}\n\n"
        
        # Overall summary
        report += "## Overall Summary\n\n"
        report += "| Strategy | Win Rate | Profit Factor | Total Return | Max Drawdown | Sharpe Ratio |\n"
        report += "|----------|----------|--------------|--------------|--------------|-------------|\n"
        
        for strategy, strategy_result in results.items():
            metrics = strategy_result['metrics']
            report += f"| {strategy} | {metrics['win_rate']:.2%} | {metrics['profit_factor']:.2f} | "
            report += f"{metrics['total_return']:.2f}% | {metrics['max_drawdown']:.2f}% | {metrics['sharpe_ratio']:.2f} |\n"
        
        # Strategy details
        for strategy, strategy_result in results.items():
            report += f"\n## {strategy.capitalize()} Strategy\n\n"
            
            # Symbol results
            for symbol, symbol_result in strategy_result['symbol_results'].items():
                metrics = symbol_result['metrics']
                report += f"### {symbol}\n\n"
                report += f"Total Trades: {metrics['total_trades']}\n"
                report += f"Win Rate: {metrics['win_rate']:.2%}\n"
                report += f"Profit Factor: {metrics['profit_factor']:.2f}\n"
                report += f"Total Return: {metrics['total_return']:.2f}%\n"
                report += f"Max Drawdown: {metrics['max_drawdown']:.2f}%\n\n"
                
                # Timeframe results
                for timeframe, tf_result in symbol_result['timeframe_results'].items():
                    metrics = tf_result['metrics']
                    report += f"#### {timeframe} Timeframe\n\n"
                    report += f"Total Trades: {metrics['total_trades']}\n"
                    report += f"Win Rate: {metrics['win_rate']:.2%}\n"
                    report += f"Profit Factor: {metrics['profit_factor']:.2f}\n"
                    report += f"Total Return: {metrics['total_return']:.2f}%\n\n"
        
        # Save report
        report_file = os.path.join(self.output_dir, f"backtest_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Summary report saved to {report_file}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    symbols = ['BTC/USDT', 'ETH/USDT']
    timeframes = ['1h', '4h']
    
    backtester = Backtester(
        exchange_id='binance',
        symbols=symbols,
        timeframes=timeframes,
        start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
        end_date=datetime.now().strftime('%Y-%m-%d'),
        config={
            'volume_threshold': 2.0,
            'price_change_threshold': 1.5,
            'fast_ma': 9,
            'slow_ma': 21,
            'breakout_periods': 20,
            'risk_reward_ratio': 2.0,
            'profit_target': 100.0,
            'max_risk_percent': 1.0,
            'initial_capital': 10000.0
        }
    )
    
    results = backtester.run_backtest()
    print("Backtest completed!")
