"""
Portfolio Management Module for Cryptocurrency Trading
Tracks trades, positions, and portfolio performance
"""
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)

class PortfolioManager:
    """Cryptocurrency portfolio manager"""
    
    def __init__(self, initial_capital=10000.0, data_dir='data'):
        """Initialize the portfolio manager.
        
        Args:
            initial_capital (float): Initial capital in USDT
            data_dir (str): Directory to store portfolio data
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.data_dir = data_dir
        
        # Create data directory
        os.makedirs(data_dir, exist_ok=True)
        
        # Positions and trades
        self.positions = {}  # symbol -> position info
        self.trades = []  # list of completed trades
        self.trade_history = []  # detailed trade history with daily snapshots
        
        # Performance metrics
        self.daily_performance = {}  # date -> metrics
        self.monthly_performance = {}  # month -> metrics
        
        # Load existing data if available
        self._load_data()
        
        logger.info(f"Portfolio Manager initialized with {initial_capital} USDT")
    
    def _load_data(self):
        """Load portfolio data from disk."""
        try:
            # Load positions
            positions_file = os.path.join(self.data_dir, 'positions.json')
            if os.path.exists(positions_file):
                with open(positions_file, 'r') as f:
                    self.positions = json.load(f)
                logger.info(f"Loaded {len(self.positions)} positions")
            
            # Load trades
            trades_file = os.path.join(self.data_dir, 'trades.json')
            if os.path.exists(trades_file):
                with open(trades_file, 'r') as f:
                    self.trades = json.load(f)
                logger.info(f"Loaded {len(self.trades)} trades")
            
            # Load trade history
            history_file = os.path.join(self.data_dir, 'trade_history.json')
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.trade_history = json.load(f)
                
            # Load daily performance
            daily_file = os.path.join(self.data_dir, 'daily_performance.json')
            if os.path.exists(daily_file):
                with open(daily_file, 'r') as f:
                    self.daily_performance = json.load(f)
            
            # Load monthly performance
            monthly_file = os.path.join(self.data_dir, 'monthly_performance.json')
            if os.path.exists(monthly_file):
                with open(monthly_file, 'r') as f:
                    self.monthly_performance = json.load(f)
            
            # Update current capital from last daily performance
            if self.daily_performance:
                last_date = max(self.daily_performance.keys())
                self.current_capital = self.daily_performance[last_date]['closing_capital']
            
        except Exception as e:
            logger.error(f"Error loading portfolio data: {str(e)}")
    
    def _save_data(self):
        """Save portfolio data to disk."""
        try:
            # Save positions
            positions_file = os.path.join(self.data_dir, 'positions.json')
            with open(positions_file, 'w') as f:
                json.dump(self.positions, f, indent=2)
            
            # Save trades
            trades_file = os.path.join(self.data_dir, 'trades.json')
            with open(trades_file, 'w') as f:
                json.dump(self.trades, f, indent=2)
            
            # Save trade history
            history_file = os.path.join(self.data_dir, 'trade_history.json')
            with open(history_file, 'w') as f:
                json.dump(self.trade_history, f, indent=2)
            
            # Save daily performance
            daily_file = os.path.join(self.data_dir, 'daily_performance.json')
            with open(daily_file, 'w') as f:
                json.dump(self.daily_performance, f, indent=2)
            
            # Save monthly performance
            monthly_file = os.path.join(self.data_dir, 'monthly_performance.json')
            with open(monthly_file, 'w') as f:
                json.dump(self.monthly_performance, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error saving portfolio data: {str(e)}")
    
    def add_position(self, symbol, entry_price, quantity, stop_loss=None, take_profit=None, strategy=None):
        """Add a new position to the portfolio.
        
        Args:
            symbol (str): Trading pair symbol
            entry_price (float): Entry price
            quantity (float): Position size in base currency
            stop_loss (float): Stop loss price
            take_profit (float): Take profit price
            strategy (str): Strategy used for entry
            
        Returns:
            dict: New position details
        """
        position_id = f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Calculate position cost
        position_cost = entry_price * quantity
        
        # Check if we have enough capital
        if position_cost > self.current_capital:
            logger.warning(f"Insufficient capital for position: {position_cost} > {self.current_capital}")
            return None
        
        # Create position
        position = {
            'id': position_id,
            'symbol': symbol,
            'entry_price': entry_price,
            'quantity': quantity,
            'position_cost': position_cost,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'strategy': strategy,
            'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_price': entry_price,
            'current_value': position_cost,
            'unrealized_pnl': 0.0,
            'unrealized_pnl_percent': 0.0
        }
        
        # Add to positions
        self.positions[position_id] = position
        
        # Update capital
        self.current_capital -= position_cost
        
        # Save data
        self._save_data()
        
        logger.info(f"Added position {position_id}: {quantity} {symbol} at {entry_price}")
        
        return position
    
    def update_position(self, position_id, current_price):
        """Update a position with current market price.
        
        Args:
            position_id (str): Position ID
            current_price (float): Current market price
            
        Returns:
            dict: Updated position details
        """
        if position_id not in self.positions:
            logger.error(f"Position {position_id} not found")
            return None
        
        position = self.positions[position_id]
        
        # Update position values
        position['current_price'] = current_price
        position['current_value'] = position['quantity'] * current_price
        position['unrealized_pnl'] = position['current_value'] - position['position_cost']
        position['unrealized_pnl_percent'] = (position['unrealized_pnl'] / position['position_cost']) * 100
        
        # Check stop loss or take profit
        if position['stop_loss'] and current_price <= position['stop_loss']:
            return self.close_position(position_id, current_price, 'stop_loss')
        
        if position['take_profit'] and current_price >= position['take_profit']:
            return self.close_position(position_id, current_price, 'take_profit')
        
        # Save position
        self.positions[position_id] = position
        self._save_data()
        
        return position
    
    def close_position(self, position_id, exit_price=None, exit_reason='manual'):
        """Close a position and record the trade.
        
        Args:
            position_id (str): Position ID
            exit_price (float): Exit price, or None to use current price
            exit_reason (str): Reason for closing the position
            
        Returns:
            dict: Closed trade details
        """
        if position_id not in self.positions:
            logger.error(f"Position {position_id} not found")
            return None
        
        position = self.positions[position_id]
        
        # Use current price if exit price not provided
        exit_price = exit_price or position['current_price']
        
        # Calculate profit/loss
        exit_value = position['quantity'] * exit_price
        realized_pnl = exit_value - position['position_cost']
        realized_pnl_percent = (realized_pnl / position['position_cost']) * 100
        
        # Create trade record
        trade = {
            'id': position_id,
            'symbol': position['symbol'],
            'strategy': position['strategy'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'quantity': position['quantity'],
            'position_cost': position['position_cost'],
            'exit_value': exit_value,
            'entry_time': position['entry_time'],
            'exit_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'realized_pnl': realized_pnl,
            'realized_pnl_percent': realized_pnl_percent,
            'exit_reason': exit_reason
        }
        
        # Add to trades
        self.trades.append(trade)
        
        # Update capital
        self.current_capital += exit_value
        
        # Remove from positions
        del self.positions[position_id]
        
        # Save data
        self._save_data()
        
        logger.info(f"Closed position {position_id}: {realized_pnl:.2f} USDT ({realized_pnl_percent:.2f}%)")
        
        return trade
    
    def update_all_positions(self, price_dict):
        """Update all positions with current market prices.
        
        Args:
            price_dict (dict): Dictionary of symbol -> price
            
        Returns:
            dict: Updated positions
        """
        updated = {}
        
        for position_id, position in list(self.positions.items()):
            symbol = position['symbol']
            
            if symbol in price_dict:
                updated[position_id] = self.update_position(position_id, price_dict[symbol])
        
        return updated
    
    def get_position_summary(self):
        """Get a summary of current positions.
        
        Returns:
            dict: Position summary
        """
        # Total position value
        total_value = sum(p['current_value'] for p in self.positions.values())
        
        # Total unrealized P&L
        total_pnl = sum(p['unrealized_pnl'] for p in self.positions.values())
        total_pnl_percent = (total_pnl / total_value) * 100 if total_value > 0 else 0
        
        # Group by symbol
        symbols = {}
        for position in self.positions.values():
            symbol = position['symbol']
            if symbol not in symbols:
                symbols[symbol] = {
                    'count': 0,
                    'total_value': 0,
                    'total_pnl': 0
                }
            
            symbols[symbol]['count'] += 1
            symbols[symbol]['total_value'] += position['current_value']
            symbols[symbol]['total_pnl'] += position['unrealized_pnl']
        
        return {
            'total_positions': len(self.positions),
            'total_value': total_value,
            'total_pnl': total_pnl,
            'total_pnl_percent': total_pnl_percent,
            'symbols': symbols
        }
    
    def get_trade_summary(self, days=30):
        """Get a summary of recent trades.
        
        Args:
            days (int): Number of days to include
            
        Returns:
            dict: Trade summary
        """
        # Filter trades by date
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        recent_trades = [t for t in self.trades if t['exit_time'] >= start_date]
        
        # Calculate metrics
        total_trades = len(recent_trades)
        winning_trades = sum(1 for t in recent_trades if t['realized_pnl'] > 0)
        losing_trades = total_trades - winning_trades
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        total_profit = sum(t['realized_pnl'] for t in recent_trades if t['realized_pnl'] > 0)
        total_loss = abs(sum(t['realized_pnl'] for t in recent_trades if t['realized_pnl'] <= 0))
        
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        # Group by strategy
        strategies = {}
        for trade in recent_trades:
            strategy = trade['strategy'] or 'unknown'
            if strategy not in strategies:
                strategies[strategy] = {
                    'count': 0,
                    'winning': 0,
                    'profit': 0
                }
            
            strategies[strategy]['count'] += 1
            if trade['realized_pnl'] > 0:
                strategies[strategy]['winning'] += 1
            strategies[strategy]['profit'] += trade['realized_pnl']
        
        # Calculate win rate per strategy
        for strategy in strategies:
            if strategies[strategy]['count'] > 0:
                strategies[strategy]['win_rate'] = (strategies[strategy]['winning'] / strategies[strategy]['count']) * 100
            else:
                strategies[strategy]['win_rate'] = 0
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'profit_factor': profit_factor,
            'strategies': strategies
        }
    
    def update_daily_performance(self):
        """Update daily performance metrics.
        
        Returns:
            dict: Updated daily performance
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Calculate total portfolio value
        portfolio_value = self.current_capital + sum(p['current_value'] for p in self.positions.values())
        
        # Get yesterday's closing value
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        yesterday_value = self.initial_capital
        
        if yesterday in self.daily_performance:
            yesterday_value = self.daily_performance[yesterday]['closing_value']
        
        # Calculate daily change
        daily_change = portfolio_value - yesterday_value
        daily_change_percent = (daily_change / yesterday_value) * 100 if yesterday_value > 0 else 0
        
        # Get today's trades
        today_trades = [t for t in self.trades if t['exit_time'].startswith(today)]
        
        # Calculate daily metrics
        daily_metrics = {
            'date': today,
            'opening_value': yesterday_value,
            'closing_value': portfolio_value,
            'change': daily_change,
            'change_percent': daily_change_percent,
            'trades': len(today_trades),
            'winning_trades': sum(1 for t in today_trades if t['realized_pnl'] > 0),
            'profit': sum(t['realized_pnl'] for t in today_trades),
            'closing_capital': self.current_capital,
            'positions': len(self.positions)
        }
        
        # Update daily performance
        self.daily_performance[today] = daily_metrics
        
        # Update monthly performance
        month = datetime.now().strftime('%Y-%m')
        if month not in self.monthly_performance:
            self.monthly_performance[month] = {
                'opening_value': yesterday_value,
                'closing_value': portfolio_value,
                'change': daily_change,
                'change_percent': daily_change_percent,
                'trades': len(today_trades),
                'winning_trades': sum(1 for t in today_trades if t['realized_pnl'] > 0),
                'profit': sum(t['realized_pnl'] for t in today_trades)
            }
        else:
            monthly = self.monthly_performance[month]
            monthly['closing_value'] = portfolio_value
            monthly['change'] = portfolio_value - monthly['opening_value']
            monthly['change_percent'] = (monthly['change'] / monthly['opening_value']) * 100
            monthly['trades'] += len(today_trades)
            monthly['winning_trades'] += sum(1 for t in today_trades if t['realized_pnl'] > 0)
            monthly['profit'] += sum(t['realized_pnl'] for t in today_trades)
        
        # Save data
        self._save_data()
        
        return daily_metrics
    
    def generate_performance_charts(self):
        """Generate performance charts.
        
        Returns:
            list: Paths to generated chart files
        """
        chart_files = []
        
        # Create charts directory
        charts_dir = os.path.join(self.data_dir, 'charts')
        os.makedirs(charts_dir, exist_ok=True)
        
        # Convert daily performance to DataFrame
        if not self.daily_performance:
            logger.warning("No daily performance data to generate charts")
            return chart_files
        
        daily_df = pd.DataFrame.from_dict(self.daily_performance, orient='index')
        daily_df.index = pd.to_datetime(daily_df.index)
        daily_df = daily_df.sort_index()
        
        # Equity curve
        plt.figure(figsize=(12, 6))
        plt.plot(daily_df.index, daily_df['closing_value'], 'b-')
        plt.title('Portfolio Equity Curve')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value (USDT)')
        plt.grid(True)
        
        equity_file = os.path.join(charts_dir, 'equity_curve.png')
        plt.savefig(equity_file)
        plt.close()
        chart_files.append(equity_file)
        
        # Daily returns
        plt.figure(figsize=(12, 6))
        plt.bar(daily_df.index, daily_df['change_percent'], color=['g' if x >= 0 else 'r' for x in daily_df['change_percent']])
        plt.title('Daily Returns')
        plt.xlabel('Date')
        plt.ylabel('Daily Return (%)')
        plt.grid(True)
        
        returns_file = os.path.join(charts_dir, 'daily_returns.png')
        plt.savefig(returns_file)
        plt.close()
        chart_files.append(returns_file)
        
        # Profit by strategy
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            strategies = trades_df.groupby('strategy')['realized_pnl'].sum()
            
            plt.figure(figsize=(12, 6))
            strategies.plot(kind='bar', color=['g' if x >= 0 else 'r' for x in strategies])
            plt.title('Profit by Strategy')
            plt.xlabel('Strategy')
            plt.ylabel('Profit (USDT)')
            plt.grid(True)
            
            strategy_file = os.path.join(charts_dir, 'strategy_profit.png')
            plt.savefig(strategy_file)
            plt.close()
            chart_files.append(strategy_file)
            
            # Win rate by strategy
            win_rates = {}
            for strategy in trades_df['strategy'].unique():
                if pd.isna(strategy):
                    continue
                strategy_trades = trades_df[trades_df['strategy'] == strategy]
                wins = sum(1 for _, t in strategy_trades.iterrows() if t['realized_pnl'] > 0)
                win_rates[strategy] = wins / len(strategy_trades) * 100
            
            if win_rates:
                plt.figure(figsize=(12, 6))
                pd.Series(win_rates).plot(kind='bar')
                plt.title('Win Rate by Strategy')
                plt.xlabel('Strategy')
                plt.ylabel('Win Rate (%)')
                plt.grid(True)
                
                win_rate_file = os.path.join(charts_dir, 'strategy_win_rate.png')
                plt.savefig(win_rate_file)
                plt.close()
                chart_files.append(win_rate_file)
        
        logger.info(f"Generated {len(chart_files)} performance charts")
        
        return chart_files
    
    def get_portfolio_stats(self):
        """Get comprehensive portfolio statistics.
        
        Returns:
            dict: Portfolio statistics
        """
        # Current portfolio value
        portfolio_value = self.current_capital + sum(p['current_value'] for p in self.positions.values())
        
        # Calculate overall return
        overall_return = portfolio_value - self.initial_capital
        overall_return_percent = (overall_return / self.initial_capital) * 100
        
        # Calculate drawdown
        if self.daily_performance:
            daily_df = pd.DataFrame.from_dict(self.daily_performance, orient='index')
            daily_df.index = pd.to_datetime(daily_df.index)
            daily_df = daily_df.sort_index()
            
            # Calculate rolling maximum
            daily_df['rolling_max'] = daily_df['closing_value'].cummax()
            daily_df['drawdown'] = (daily_df['closing_value'] - daily_df['rolling_max']) / daily_df['rolling_max'] * 100
            
            max_drawdown = daily_df['drawdown'].min()
        else:
            max_drawdown = 0
        
        # Calculate trade stats
        if self.trades:
            total_trades = len(self.trades)
            winning_trades = sum(1 for t in self.trades if t['realized_pnl'] > 0)
            win_rate = winning_trades / total_trades * 100
            
            avg_win = sum(t['realized_pnl'] for t in self.trades if t['realized_pnl'] > 0) / winning_trades if winning_trades > 0 else 0
            avg_loss = sum(t['realized_pnl'] for t in self.trades if t['realized_pnl'] <= 0) / (total_trades - winning_trades) if (total_trades - winning_trades) > 0 else 0
            
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
        else:
            total_trades = 0
            win_rate = 0
            avg_win = 0
            avg_loss = 0
            profit_factor = 0
        
        # Calculate monthly returns
        monthly_returns = {}
        for month, data in self.monthly_performance.items():
            monthly_returns[month] = data['change_percent']
        
        return {
            'current_value': portfolio_value,
            'current_capital': self.current_capital,
            'initial_capital': self.initial_capital,
            'overall_return': overall_return,
            'overall_return_percent': overall_return_percent,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'open_positions': len(self.positions),
            'monthly_returns': monthly_returns
        }


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    portfolio = PortfolioManager(initial_capital=10000.0)
    
    # Add a position
    position = portfolio.add_position(
        symbol='BTC/USDT',
        entry_price=50000.0,
        quantity=0.1,
        stop_loss=48000.0,
        take_profit=55000.0,
        strategy='breakout'
    )
    
    # Update position
    updated = portfolio.update_position(position['id'], 52000.0)
    
    # Get position summary
    summary = portfolio.get_position_summary()
    print(f"Position summary: {summary}")
    
    # Close position
    trade = portfolio.close_position(position['id'], 53000.0)
    
    # Get trade summary
    trade_summary = portfolio.get_trade_summary()
    print(f"Trade summary: {trade_summary}")
    
    # Update daily performance
    daily = portfolio.update_daily_performance()
    print(f"Daily performance: {daily}")
    
    # Generate charts
    charts = portfolio.generate_performance_charts()
    
    # Get portfolio stats
    stats = portfolio.get_portfolio_stats()
    print(f"Portfolio stats: {stats}")
