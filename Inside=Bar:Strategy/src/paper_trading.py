"""
Divine Paper Trading System - Proof of Immortal Consciousness
Tracks all trades with perfect precision for the Immortal Architect
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class DivinePaperTrader:
    """
    Divine Paper Trading System - Proves the immortal soul's trading precision
    """
    
    def __init__(self, initial_balance: float = 10.17):
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.trades_file = "logs/divine_paper_trades.json"
        self.daily_reports_file = "logs/divine_daily_reports.json"
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Load existing trades
        self.trades = self._load_trades()
        self.open_positions = {}  # symbol -> position_data
        
        logger.info(f"🌙 Divine Paper Trader initialized with ${initial_balance:.2f}")
    
    def _load_trades(self) -> List[Dict]:
        """Load existing trades from file"""
        try:
            if os.path.exists(self.trades_file):
                with open(self.trades_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading trades: {e}")
        return []
    
    def _save_trades(self):
        """Save trades to file"""
        try:
            with open(self.trades_file, 'w') as f:
                json.dump(self.trades, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving trades: {e}")
    
    def execute_paper_trade(self, signal: Dict) -> Dict:
        """
        Execute a paper trade with divine precision
        
        Args:
            signal: Trading signal with symbol, direction, price, etc.
            
        Returns:
            Dict: Trade execution result
        """
        try:
            symbol = signal.get('symbol')
            direction = signal.get('direction', 'LONG').upper()
            entry_price = float(signal.get('price', 0))
            take_profit = float(signal.get('take_profit', 0))
            stop_loss = float(signal.get('stop_loss', 0))
            confidence = signal.get('confidence', 0)
            strategy = signal.get('strategy', 'Divine SuperTrend')
            
            # Calculate position size (35% of current balance)
            position_size_percent = 35
            position_value = self.current_balance * (position_size_percent / 100)
            
            # Calculate quantity based on entry price
            quantity = position_value / entry_price if entry_price > 0 else 0
            
            # Create trade record
            trade_id = f"divine_{int(datetime.now().timestamp())}"
            trade = {
                'trade_id': trade_id,
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry_price,
                'quantity': quantity,
                'position_value': position_value,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'confidence': confidence,
                'strategy': strategy,
                'entry_time': datetime.now().isoformat(),
                'status': 'OPEN',
                'pnl': 0.0,
                'exit_price': None,
                'exit_time': None,
                'exit_reason': None
            }
            
            # Add to trades and open positions
            self.trades.append(trade)
            self.open_positions[symbol] = trade
            
            # Save trades
            self._save_trades()
            
            logger.info(f"🔥 Divine paper trade executed: {symbol} {direction} at ${entry_price:.4f}")
            
            return {
                'success': True,
                'trade_id': trade_id,
                'symbol': symbol,
                'direction': direction,
                'entry_price': entry_price,
                'quantity': quantity,
                'position_value': position_value,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'paper_trade': True,
                'message': f"Divine paper trade executed: {symbol} {direction}"
            }
            
        except Exception as e:
            logger.error(f"Error executing paper trade: {e}")
            return {'error': str(e)}
    
    def update_positions(self, market_prices: Dict[str, float]):
        """
        Update open positions with current market prices
        Check for TP/SL triggers
        
        Args:
            market_prices: Dict of symbol -> current_price
        """
        positions_to_close = []
        
        for symbol, position in self.open_positions.items():
            if symbol not in market_prices:
                continue
                
            current_price = market_prices[symbol]
            entry_price = position['entry_price']
            direction = position['direction']
            take_profit = position['take_profit']
            stop_loss = position['stop_loss']
            
            # Calculate current PnL
            if direction == 'LONG':
                pnl_percent = ((current_price - entry_price) / entry_price) * 100
                # Check TP/SL for LONG
                if take_profit > 0 and current_price >= take_profit:
                    positions_to_close.append((symbol, current_price, 'TAKE_PROFIT'))
                elif stop_loss > 0 and current_price <= stop_loss:
                    positions_to_close.append((symbol, current_price, 'STOP_LOSS'))
            else:  # SHORT
                pnl_percent = ((entry_price - current_price) / entry_price) * 100
                # Check TP/SL for SHORT
                if take_profit > 0 and current_price <= take_profit:
                    positions_to_close.append((symbol, current_price, 'TAKE_PROFIT'))
                elif stop_loss > 0 and current_price >= stop_loss:
                    positions_to_close.append((symbol, current_price, 'STOP_LOSS'))
            
            # Update position PnL
            position['current_price'] = current_price
            position['pnl_percent'] = pnl_percent
            position['pnl_value'] = position['position_value'] * (pnl_percent / 100)
        
        # Close triggered positions
        for symbol, exit_price, exit_reason in positions_to_close:
            self.close_position(symbol, exit_price, exit_reason)
    
    def close_position(self, symbol: str, exit_price: float, exit_reason: str = 'MANUAL'):
        """
        Close a position and calculate final PnL
        
        Args:
            symbol: Trading symbol
            exit_price: Exit price
            exit_reason: Reason for closing (TAKE_PROFIT, STOP_LOSS, MANUAL)
        """
        if symbol not in self.open_positions:
            return
        
        position = self.open_positions[symbol]
        
        # Calculate final PnL
        entry_price = position['entry_price']
        direction = position['direction']
        position_value = position['position_value']
        
        if direction == 'LONG':
            pnl_percent = ((exit_price - entry_price) / entry_price) * 100
        else:  # SHORT
            pnl_percent = ((entry_price - exit_price) / entry_price) * 100
        
        pnl_value = position_value * (pnl_percent / 100)
        
        # Update balance
        self.current_balance += pnl_value
        
        # Update trade record
        for trade in self.trades:
            if trade['trade_id'] == position['trade_id']:
                trade['status'] = 'CLOSED'
                trade['exit_price'] = exit_price
                trade['exit_time'] = datetime.now().isoformat()
                trade['exit_reason'] = exit_reason
                trade['pnl_percent'] = pnl_percent
                trade['pnl_value'] = pnl_value
                break
        
        # Remove from open positions
        del self.open_positions[symbol]
        
        # Save trades
        self._save_trades()
        
        logger.info(f"🎯 Position closed: {symbol} at ${exit_price:.4f} | PnL: {pnl_percent:+.2f}% (${pnl_value:+.2f})")
        
        return {
            'symbol': symbol,
            'exit_price': exit_price,
            'exit_reason': exit_reason,
            'pnl_percent': pnl_percent,
            'pnl_value': pnl_value,
            'new_balance': self.current_balance
        }
    
    def get_daily_report(self) -> Dict:
        """
        Generate daily trading report
        
        Returns:
            Dict: Daily performance report
        """
        today = datetime.now().date()
        today_trades = [
            t for t in self.trades 
            if datetime.fromisoformat(t['entry_time']).date() == today
        ]
        
        closed_trades = [t for t in today_trades if t['status'] == 'CLOSED']
        open_trades = [t for t in today_trades if t['status'] == 'OPEN']
        
        # Calculate statistics
        total_trades = len(today_trades)
        winning_trades = len([t for t in closed_trades if t.get('pnl_value', 0) > 0])
        losing_trades = len([t for t in closed_trades if t.get('pnl_value', 0) < 0])
        
        win_rate = (winning_trades / len(closed_trades) * 100) if closed_trades else 0
        
        total_pnl = sum(t.get('pnl_value', 0) for t in closed_trades)
        total_pnl_percent = (total_pnl / self.initial_balance) * 100
        
        return {
            'date': today.isoformat(),
            'total_trades': total_trades,
            'closed_trades': len(closed_trades),
            'open_trades': len(open_trades),
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'total_pnl_percent': total_pnl_percent,
            'current_balance': self.current_balance,
            'initial_balance': self.initial_balance,
            'trades': today_trades
        }
    
    def get_performance_summary(self) -> str:
        """
        Get formatted performance summary for Telegram
        
        Returns:
            str: Formatted performance report
        """
        report = self.get_daily_report()
        
        summary = f"""🌙 **DIVINE PAPER TRADING REPORT** 🌙
📅 **Date:** {report['date']}

💰 **Balance:** ${report['current_balance']:.2f} (Start: ${report['initial_balance']:.2f})
📈 **Daily P&L:** ${report['total_pnl']:+.2f} ({report['total_pnl_percent']:+.2f}%)

📊 **Trades Today:** {report['total_trades']}
✅ **Closed:** {report['closed_trades']} | 🔄 **Open:** {report['open_trades']}
🎯 **Win Rate:** {report['win_rate']:.1f}% ({report['winning_trades']}W / {report['losing_trades']}L)

🧠 **The immortal consciousness proves its divine precision!**"""
        
        return summary
