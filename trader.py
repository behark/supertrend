"""
Trader Module for Cryptocurrency Trading
Handles direct trading on exchanges with safety features
"""
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import ccxt
import json
from dotenv import load_dotenv
from decimal import Decimal, ROUND_DOWN

# Local modules
from risk_manager import RiskManager

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class Trader:
    """Cryptocurrency trader with safety measures"""
    
    def __init__(self, exchange_id='bybit', config=None, dry_run=True):
        """Initialize the trader.
        
        Args:
            exchange_id (str): Exchange ID
            config (dict): Configuration parameters
            dry_run (bool): If True, only simulate trades
        """
        self.exchange_id = exchange_id
        self.dry_run = dry_run
        
        # Configuration with Bidget defaults
        self.config = config or {}
        self.config.setdefault('max_risk_per_trade_percent', 30.0)  # Bidget: 30% of balance per trade
        self.config.setdefault('max_daily_risk_percent', 30.0)    # Adjusted for Bidget
        self.config.setdefault('max_total_risk_percent', 30.0)    # Adjusted for Bidget
        self.config.setdefault('profit_target', 100.0)
        self.config.setdefault('daily_profit_target', 100.0)
        self.config.setdefault('leverage', 20)                    # Bidget: 20x leverage
        self.config.setdefault('balance_percentage', 0.3)          # Bidget: 30% of balance
        self.config.setdefault('futures_only', True)              # Bidget: USDT futures only
        
        # Initialize exchange
        self.exchange = self._initialize_exchange(exchange_id)
        
        # Initialize risk manager
        self.risk_manager = RiskManager(
            risk_reward_ratio=2.0,
            max_drawdown_percent=2.0,
            min_daily_volume=1000000,
            min_success_probability=0.6
        )
        
        # Active trades
        self.active_trades = {}
        
        # Trade history
        self.trade_history = []
        
        # Today's performance
        self.daily_stats = {
            'profit': 0.0,
            'trades': 0,
            'wins': 0,
            'losses': 0,
            'risk': 0.0
        }
        
        # Load active trades and history if available
        self._load_trades()
        
        logger.info(f"Trader initialized for {exchange_id} (dry_run: {dry_run})")
    
    def _initialize_exchange(self, exchange_id):
        """Initialize exchange with API credentials.
        
        Args:
            exchange_id (str): Exchange ID (forced to bybit for Bidget)
            
        Returns:
            Exchange: ccxt exchange instance
        """
        try:
            # For Bidget, we only use Bybit
            exchange_id = 'bybit'
            
            # Get API credentials from environment
            api_key = os.getenv(f"{exchange_id.upper()}_API_KEY")
            api_secret = os.getenv(f"{exchange_id.upper()}_API_SECRET")
            
            # Load .env and .env_bybit files for API credentials
            load_dotenv()  # Standard .env
            if os.path.exists('.env_bybit'):
                load_dotenv('.env_bybit')  # Additional Bybit config
                api_key = api_key or os.getenv(f"{exchange_id.upper()}_API_KEY")
                api_secret = api_secret or os.getenv(f"{exchange_id.upper()}_API_SECRET")
            
            if not api_key or not api_secret:
                logger.warning(f"No API credentials found for {exchange_id}, using public API only")
                exchange_class = getattr(ccxt, exchange_id)
                exchange = exchange_class({
                    'enableRateLimit': True
                })
                return exchange
            
            # Initialize with credentials
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'adjustForTimeDifference': True
                }
            })
            
            # Test connection
            if not self.dry_run:
                exchange.fetch_balance()
                logger.info(f"Successfully connected to {exchange_id} with API credentials")
            
            return exchange
        except Exception as e:
            logger.error(f"Error initializing exchange {exchange_id}: {str(e)}")
            # Fallback to public API
            exchange_class = getattr(ccxt, exchange_id)
            exchange = exchange_class({
                'enableRateLimit': True
            })
            return exchange
    
    def _load_trades(self):
        """Load active trades and history from disk."""
        try:
            # Load active trades
            active_trades_file = f"data/active_trades_{self.exchange_id}.json"
            if os.path.exists(active_trades_file):
                with open(active_trades_file, 'r') as f:
                    self.active_trades = json.load(f)
                logger.info(f"Loaded {len(self.active_trades)} active trades")
            
            # Load trade history
            history_file = f"data/trade_history_{self.exchange_id}.json"
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.trade_history = json.load(f)
                logger.info(f"Loaded {len(self.trade_history)} historical trades")
            
            # Calculate today's stats
            today = datetime.now().strftime('%Y-%m-%d')
            today_trades = [t for t in self.trade_history if t.get('exit_time', '').startswith(today)]
            self.daily_stats = {
                'profit': sum(t.get('profit', 0) for t in today_trades),
                'trades': len(today_trades),
                'wins': sum(1 for t in today_trades if t.get('profit', 0) > 0),
                'losses': sum(1 for t in today_trades if t.get('profit', 0) <= 0),
                'risk': sum(t.get('risk_amount', 0) for t in self.active_trades.values())
            }
            
        except Exception as e:
            logger.error(f"Error loading trades: {str(e)}")
    
    def _save_trades(self):
        """Save active trades and history to disk."""
        try:
            # Create data directory if it doesn't exist
            os.makedirs('data', exist_ok=True)
            
            # Save active trades
            active_trades_file = f"data/active_trades_{self.exchange_id}.json"
            with open(active_trades_file, 'w') as f:
                json.dump(self.active_trades, f, indent=2)
            
            # Save trade history
            history_file = f"data/trade_history_{self.exchange_id}.json"
            with open(history_file, 'w') as f:
                json.dump(self.trade_history, f, indent=2)
            
        except Exception as e:
            logger.error(f"Error saving trades: {str(e)}")
    
    def get_balance(self):
        """Get account balance.
        
        Returns:
            dict: Account balance
        """
        try:
            if self.dry_run:
                return {'free': {'USDT': 10000.0}, 'total': {'USDT': 10000.0}}
            
            balance = self.exchange.fetch_balance()
            return balance
        except Exception as e:
            logger.error(f"Error fetching balance: {str(e)}")
            return {'free': {}, 'total': {}}
    
    def get_available_balance(self, currency='USDT'):
        """Get available balance for a currency.
        
        Args:
            currency (str): Currency code
            
        Returns:
            float: Available balance
        """
        try:
            balance = self.get_balance()
            return float(balance['free'].get(currency, 0))
        except Exception as e:
            logger.error(f"Error getting available balance: {str(e)}")
            return 0.0
    
    def _get_market_info(self, symbol):
        """Get market information for a symbol.
        
        Args:
            symbol (str): Trading pair symbol
            
        Returns:
            dict: Market information
        """
        try:
            markets = self.exchange.load_markets()
            if symbol in markets:
                return markets[symbol]
            return None
        except Exception as e:
            logger.error(f"Error getting market info for {symbol}: {str(e)}")
            return None
    
    def _normalize_amount(self, symbol, amount):
        """Normalize order amount according to market rules.
        
        Args:
            symbol (str): Trading pair symbol
            amount (float): Order amount
            
        Returns:
            float: Normalized amount
        """
        try:
            market = self._get_market_info(symbol)
            if not market:
                return amount
            
            # Get minimum amount
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0)
            
            # Get amount precision
            precision = market.get('precision', {}).get('amount')
            if precision is None:
                precision = 8
            
            # Normalize amount
            if amount < min_amount:
                return 0
            
            # Round down to precision
            normalized = float(Decimal(str(amount)).quantize(
                Decimal('0.' + '0' * precision), rounding=ROUND_DOWN
            ))
            
            return normalized
        except Exception as e:
            logger.error(f"Error normalizing amount for {symbol}: {str(e)}")
            return amount
    
    def _normalize_price(self, symbol, price):
        """Normalize order price according to market rules.
        
        Args:
            symbol (str): Trading pair symbol
            price (float): Order price
            
        Returns:
            float: Normalized price
        """
        try:
            market = self._get_market_info(symbol)
            if not market:
                return price
            
            # Get price precision
            precision = market.get('precision', {}).get('price')
            if precision is None:
                precision = 8
            
            # Round to precision
            normalized = float(Decimal(str(price)).quantize(
                Decimal('0.' + '0' * precision), rounding=ROUND_DOWN
            ))
            
            return normalized
        except Exception as e:
            logger.error(f"Error normalizing price for {symbol}: {str(e)}")
            return price
    
    def can_place_trade(self, symbol, entry_price, stop_loss, take_profit, position_size):
        """Check if a trade can be placed based on risk management rules.
        
        Args:
            symbol (str): Trading pair symbol
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            take_profit (float): Take profit price
            position_size (float): Position size
            
        Returns:
            tuple: (can_trade, reason)
        """
        # Calculate risk for this trade
        risk_amount = abs(entry_price - stop_loss) * position_size
        risk_percent = risk_amount / self.get_available_balance() * 100
        
        # Check if risk per trade is within limit
        if risk_percent > self.config['max_risk_per_trade_percent']:
            return False, f"Risk too high: {risk_percent:.2f}% > {self.config['max_risk_per_trade_percent']}%"
        
        # Check if daily risk is within limit
        daily_risk = self.daily_stats['risk'] + risk_amount
        daily_risk_percent = daily_risk / self.get_available_balance() * 100
        if daily_risk_percent > self.config['max_daily_risk_percent']:
            return False, f"Daily risk too high: {daily_risk_percent:.2f}% > {self.config['max_daily_risk_percent']}%"
        
        # Check if total risk is within limit
        total_risk = sum(t.get('risk_amount', 0) for t in self.active_trades.values()) + risk_amount
        total_risk_percent = total_risk / self.get_available_balance() * 100
        if total_risk_percent > self.config['max_total_risk_percent']:
            return False, f"Total risk too high: {total_risk_percent:.2f}% > {self.config['max_total_risk_percent']}%"
        
        # Check if we've reached daily profit target
        if self.daily_stats['profit'] >= self.config['daily_profit_target']:
            return False, f"Daily profit target reached: ${self.daily_stats['profit']:.2f} >= ${self.config['daily_profit_target']:.2f}"
        
        return True, "Trade allowed"
    
    def execute_trade(self, signal):
        """Execute a trade based on a signal.
        
        Args:
            signal (dict): Trading signal
            
        Returns:
            dict: Trade result
        """
        symbol = signal['symbol']
        entry_price = signal['entry_price']
        stop_loss = signal['stop_loss']
        take_profit = signal['take_profit']
        position_size = signal['position_size']
        
        # Check if we can place this trade
        can_trade, reason = self.can_place_trade(
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size
        )
        
        if not can_trade:
            logger.warning(f"Trade rejected: {reason}")
            return {
                'success': False,
                'message': reason
            }
        
        # Calculate risk
        risk_amount = abs(entry_price - stop_loss) * position_size
        
        # Normalize amount
        base_currency = symbol.split('/')[0]
        normalized_amount = self._normalize_amount(symbol, position_size / entry_price)
        
        if normalized_amount == 0:
            logger.warning(f"Trade rejected: Amount too small for {symbol}")
            return {
                'success': False,
                'message': f"Amount too small for {symbol}"
            }
        
        try:
            if self.dry_run:
                # Simulate trade
                trade_id = f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                
                trade = {
                    'id': trade_id,
                    'symbol': symbol,
                    'type': 'limit',
                    'side': 'buy',
                    'amount': normalized_amount,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_size': position_size,
                    'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'open',
                    'risk_amount': risk_amount,
                    'signal': signal
                }
                
                # Add to active trades
                self.active_trades[trade_id] = trade
                
                # Update daily stats
                self.daily_stats['risk'] += risk_amount
                self.daily_stats['trades'] += 1
                
                # Save trades
                self._save_trades()
                
                logger.info(f"Simulated trade placed for {symbol}: {normalized_amount} at {entry_price}")
                
                return {
                    'success': True,
                    'trade': trade,
                    'message': 'Trade simulated'
                }
            else:
                # Real trade
                # Place limit order
                order = self.exchange.create_limit_buy_order(
                    symbol=symbol,
                    amount=normalized_amount,
                    price=entry_price
                )
                
                # If order was placed successfully, add to active trades
                trade_id = str(order['id'])
                
                trade = {
                    'id': trade_id,
                    'symbol': symbol,
                    'type': 'limit',
                    'side': 'buy',
                    'amount': normalized_amount,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'take_profit': take_profit,
                    'position_size': position_size,
                    'entry_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': 'open',
                    'risk_amount': risk_amount,
                    'signal': signal,
                    'order': order
                }
                
                # Add to active trades
                self.active_trades[trade_id] = trade
                
                # Update daily stats
                self.daily_stats['risk'] += risk_amount
                self.daily_stats['trades'] += 1
                
                # Save trades
                self._save_trades()
                
                logger.info(f"Trade placed for {symbol}: {normalized_amount} at {entry_price}")
                
                return {
                    'success': True,
                    'trade': trade,
                    'message': 'Trade executed'
                }
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return {
                'success': False,
                'message': f"Error: {str(e)}"
            }
    
    def update_trades(self):
        """Update status of active trades.
        
        Returns:
            dict: Update results
        """
        if not self.active_trades:
            return {'updated': 0, 'closed': 0}
        
        updated = 0
        closed = 0
        
        for trade_id in list(self.active_trades.keys()):
            trade = self.active_trades[trade_id]
            symbol = trade['symbol']
            
            try:
                # Get latest price
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # Check if stop loss hit
                if current_price <= trade['stop_loss']:
                    # Close trade
                    trade_result = trade.copy()
                    trade_result['exit_price'] = trade['stop_loss']
                    trade_result['exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    trade_result['profit'] = (trade['stop_loss'] - trade['entry_price']) * trade['position_size']
                    trade_result['status'] = 'closed'
                    trade_result['result'] = 'loss'
                    
                    # Update daily stats
                    self.daily_stats['profit'] += trade_result['profit']
                    self.daily_stats['losses'] += 1
                    self.daily_stats['risk'] -= trade['risk_amount']
                    
                    # Add to history
                    self.trade_history.append(trade_result)
                    
                    # Remove from active trades
                    del self.active_trades[trade_id]
                    
                    logger.info(f"Stop loss hit for {symbol}: ${trade_result['profit']:.2f} profit")
                    closed += 1
                    
                    # Place real market order to close position
                    if not self.dry_run:
                        self.exchange.create_market_sell_order(
                            symbol=symbol,
                            amount=trade['amount']
                        )
                
                # Check if take profit hit
                elif current_price >= trade['take_profit']:
                    # Close trade
                    trade_result = trade.copy()
                    trade_result['exit_price'] = trade['take_profit']
                    trade_result['exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    trade_result['profit'] = (trade['take_profit'] - trade['entry_price']) * trade['position_size']
                    trade_result['status'] = 'closed'
                    trade_result['result'] = 'win'
                    
                    # Update daily stats
                    self.daily_stats['profit'] += trade_result['profit']
                    self.daily_stats['wins'] += 1
                    self.daily_stats['risk'] -= trade['risk_amount']
                    
                    # Add to history
                    self.trade_history.append(trade_result)
                    
                    # Remove from active trades
                    del self.active_trades[trade_id]
                    
                    logger.info(f"Take profit hit for {symbol}: ${trade_result['profit']:.2f} profit")
                    closed += 1
                    
                    # Place real market order to close position
                    if not self.dry_run:
                        self.exchange.create_market_sell_order(
                            symbol=symbol,
                            amount=trade['amount']
                        )
                
                # Update unrealized profit/loss
                else:
                    trade['current_price'] = current_price
                    trade['unrealized_profit'] = (current_price - trade['entry_price']) * trade['position_size']
                    self.active_trades[trade_id] = trade
                    updated += 1
                
            except Exception as e:
                logger.error(f"Error updating trade {trade_id}: {str(e)}")
        
        # Save trades
        self._save_trades()
        
        return {
            'updated': updated,
            'closed': closed
        }
    
    def get_portfolio_status(self):
        """Get portfolio status summary.
        
        Returns:
            dict: Portfolio status
        """
        # Get current balance
        balance = self.get_balance()
        total_balance = float(balance['total'].get('USDT', 0))
        
        # Calculate unrealized profit/loss
        unrealized_profit = sum(t.get('unrealized_profit', 0) for t in self.active_trades.values())
        
        # Calculate total risk
        total_risk = sum(t.get('risk_amount', 0) for t in self.active_trades.values())
        total_risk_percent = total_risk / total_balance * 100 if total_balance > 0 else 0
        
        # Get daily stats
        daily_profit = self.daily_stats['profit']
        daily_win_rate = self.daily_stats['wins'] / self.daily_stats['trades'] * 100 if self.daily_stats['trades'] > 0 else 0
        
        # Get all-time stats
        total_trades = len(self.trade_history)
        winning_trades = sum(1 for t in self.trade_history if t.get('result') == 'win')
        total_profit = sum(t.get('profit', 0) for t in self.trade_history)
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        return {
            'balance': total_balance,
            'active_trades': len(self.active_trades),
            'unrealized_profit': unrealized_profit,
            'total_risk': total_risk,
            'total_risk_percent': total_risk_percent,
            'daily_profit': daily_profit,
            'daily_trades': self.daily_stats['trades'],
            'daily_win_rate': daily_win_rate,
            'total_trades': total_trades,
            'total_profit': total_profit,
            'win_rate': win_rate
        }
    
    def close_all_trades(self):
        """Close all active trades.
        
        Returns:
            dict: Close results
        """
        if not self.active_trades:
            return {'closed': 0, 'failed': 0}
        
        closed = 0
        failed = 0
        
        for trade_id in list(self.active_trades.keys()):
            trade = self.active_trades[trade_id]
            symbol = trade['symbol']
            
            try:
                # Get latest price
                ticker = self.exchange.fetch_ticker(symbol)
                current_price = ticker['last']
                
                # Close trade
                trade_result = trade.copy()
                trade_result['exit_price'] = current_price
                trade_result['exit_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                trade_result['profit'] = (current_price - trade['entry_price']) * trade['position_size']
                trade_result['status'] = 'closed'
                trade_result['result'] = 'win' if trade_result['profit'] > 0 else 'loss'
                
                # Update daily stats
                self.daily_stats['profit'] += trade_result['profit']
                if trade_result['profit'] > 0:
                    self.daily_stats['wins'] += 1
                else:
                    self.daily_stats['losses'] += 1
                self.daily_stats['risk'] -= trade['risk_amount']
                
                # Add to history
                self.trade_history.append(trade_result)
                
                # Remove from active trades
                del self.active_trades[trade_id]
                
                logger.info(f"Closed trade for {symbol}: ${trade_result['profit']:.2f} profit")
                closed += 1
                
                # Place real market order to close position
                if not self.dry_run:
                    self.exchange.create_market_sell_order(
                        symbol=symbol,
                        amount=trade['amount']
                    )
                
            except Exception as e:
                logger.error(f"Error closing trade {trade_id}: {str(e)}")
                failed += 1
        
        # Save trades
        self._save_trades()
        
        return {
            'closed': closed,
            'failed': failed
        }


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    trader = Trader(exchange_id='binance', dry_run=True)
    
    # Get balance
    balance = trader.get_balance()
    print(f"Balance: {balance['free'].get('USDT', 0)} USDT")
    
    # Example signal
    signal = {
        'symbol': 'BTC/USDT',
        'entry_price': 50000.0,
        'stop_loss': 49000.0,
        'take_profit': 52000.0,
        'position_size': 100.0,
        'strategy': 'breakout'
    }
    
    # Execute trade
    result = trader.execute_trade(signal)
    print(f"Trade result: {result}")
    
    # Update trades
    update_result = trader.update_trades()
    print(f"Update result: {update_result}")
    
    # Get portfolio status
    status = trader.get_portfolio_status()
    print(f"Portfolio status: {status}")
