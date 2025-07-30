"""
Smart Trade Memory System
========================
Comprehensive trade tracking and memory management for the crypto trading bot.
Stores trade history, provides fast lookups, and enables intelligent analysis.

Features:
- Full trade metadata storage (symbol, entry/exit, SL/TP, strategy, etc.)
- Dual JSON/CSV storage with automatic rotation
- Fast lookup capabilities (/history, /last_trade commands)
- Performance analytics and insights
- Session-based indexing
- Backup and recovery support
"""

import os
import json
import csv
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import pandas as pd
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class TradeRecord:
    """Complete trade record with all metadata"""
    # Core trade info
    trade_id: str
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: Optional[float] = None
    quantity: float = 0.0
    
    # Risk management
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    
    # Strategy and context
    strategy: str = ""
    regime: str = ""  # market regime (trending, ranging, volatile, etc.)
    confidence_score: float = 0.0
    timeframe: str = "1h"
    
    # Execution details
    timestamp_entry: datetime = None
    timestamp_exit: Optional[datetime] = None
    execution_type: str = "market"  # market, limit, stop
    
    # Results
    status: str = "open"  # open, closed, cancelled
    result: Optional[str] = None  # win, loss, breakeven
    pnl_absolute: Optional[float] = None
    pnl_percentage: Optional[float] = None
    
    # Additional metadata
    session_id: str = ""
    notes: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.timestamp_entry is None:
            self.timestamp_entry = datetime.now()
        if not self.trade_id:
            self.trade_id = self._generate_trade_id()
    
    def _generate_trade_id(self) -> str:
        """Generate unique trade ID"""
        timestamp = self.timestamp_entry.strftime("%Y%m%d_%H%M%S")
        return f"{self.symbol}_{timestamp}_{self.side}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if data['timestamp_entry']:
            data['timestamp_entry'] = data['timestamp_entry'].isoformat()
        if data['timestamp_exit']:
            data['timestamp_exit'] = data['timestamp_exit'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradeRecord':
        """Create TradeRecord from dictionary"""
        # Convert ISO strings back to datetime
        if data.get('timestamp_entry'):
            data['timestamp_entry'] = datetime.fromisoformat(data['timestamp_entry'])
        if data.get('timestamp_exit'):
            data['timestamp_exit'] = datetime.fromisoformat(data['timestamp_exit'])
        return cls(**data)
    
    def calculate_pnl(self) -> Tuple[Optional[float], Optional[float]]:
        """Calculate PnL if exit price is available"""
        if not self.exit_price or not self.entry_price:
            return None, None
        
        if self.side.lower() == 'long':
            pnl_abs = (self.exit_price - self.entry_price) * self.quantity
            pnl_pct = ((self.exit_price - self.entry_price) / self.entry_price) * 100
        else:  # short
            pnl_abs = (self.entry_price - self.exit_price) * self.quantity
            pnl_pct = ((self.entry_price - self.exit_price) / self.entry_price) * 100
        
        return pnl_abs, pnl_pct
    
    def update_exit(self, exit_price: float, timestamp: Optional[datetime] = None):
        """Update trade with exit information"""
        self.exit_price = exit_price
        self.timestamp_exit = timestamp or datetime.now()
        self.status = "closed"
        
        # Calculate PnL
        pnl_abs, pnl_pct = self.calculate_pnl()
        self.pnl_absolute = pnl_abs
        self.pnl_percentage = pnl_pct
        
        # Determine result
        if pnl_pct and pnl_pct > 0.1:
            self.result = "win"
        elif pnl_pct and pnl_pct < -0.1:
            self.result = "loss"
        else:
            self.result = "breakeven"


class TradeMemory:
    """Smart Trade Memory System"""
    
    def __init__(self, data_dir: str = "data/trades"):
        """Initialize trade memory system"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.json_file = self.data_dir / "trades.json"
        self.csv_file = self.data_dir / "trades.csv"
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # In-memory storage
        self.trades: Dict[str, TradeRecord] = {}
        self.session_id = self._generate_session_id()
        
        # Load existing trades
        self._load_trades()
        
        logger.info(f"Trade Memory initialized. Session: {self.session_id}")
        logger.info(f"Loaded {len(self.trades)} existing trades")
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _load_trades(self):
        """Load trades from JSON file"""
        if self.json_file.exists():
            try:
                with open(self.json_file, 'r') as f:
                    data = json.load(f)
                    for trade_data in data:
                        trade = TradeRecord.from_dict(trade_data)
                        self.trades[trade.trade_id] = trade
                logger.info(f"Loaded {len(self.trades)} trades from {self.json_file}")
            except Exception as e:
                logger.error(f"Error loading trades: {e}")
    
    def _save_trades(self):
        """Save trades to both JSON and CSV"""
        try:
            # Save to JSON
            trades_data = [trade.to_dict() for trade in self.trades.values()]
            with open(self.json_file, 'w') as f:
                json.dump(trades_data, f, indent=2, default=str)
            
            # Save to CSV
            if trades_data:
                df = pd.DataFrame(trades_data)
                df.to_csv(self.csv_file, index=False)
            
            logger.debug(f"Saved {len(self.trades)} trades to storage")
        except Exception as e:
            logger.error(f"Error saving trades: {e}")
    
    def add_trade(self, trade: TradeRecord) -> str:
        """Add new trade to memory"""
        trade.session_id = self.session_id
        self.trades[trade.trade_id] = trade
        self._save_trades()
        
        logger.info(f"Added trade: {trade.trade_id} ({trade.symbol} {trade.side})")
        return trade.trade_id
    
    def update_trade(self, trade_id: str, **updates) -> bool:
        """Update existing trade"""
        if trade_id not in self.trades:
            logger.warning(f"Trade {trade_id} not found for update")
            return False
        
        trade = self.trades[trade_id]
        for key, value in updates.items():
            if hasattr(trade, key):
                setattr(trade, key, value)
        
        self._save_trades()
        logger.info(f"Updated trade: {trade_id}")
        return True
    
    def close_trade(self, trade_id: str, exit_price: float, timestamp: Optional[datetime] = None) -> bool:
        """Close a trade with exit price"""
        if trade_id not in self.trades:
            logger.warning(f"Trade {trade_id} not found for closing")
            return False
        
        trade = self.trades[trade_id]
        trade.update_exit(exit_price, timestamp)
        self._save_trades()
        
        logger.info(f"Closed trade: {trade_id} (PnL: {trade.pnl_percentage:.2f}%)")
        return True
    
    def get_trade(self, trade_id: str) -> Optional[TradeRecord]:
        """Get specific trade by ID"""
        return self.trades.get(trade_id)
    
    def get_last_trade(self) -> Optional[TradeRecord]:
        """Get the most recent trade"""
        if not self.trades:
            return None
        
        return max(self.trades.values(), key=lambda t: t.timestamp_entry)
    
    def get_history(self, limit: int = 10, symbol: Optional[str] = None, 
                   status: Optional[str] = None, days: Optional[int] = None) -> List[TradeRecord]:
        """Get trade history with filters"""
        trades = list(self.trades.values())
        
        # Apply filters
        if symbol:
            trades = [t for t in trades if t.symbol.upper() == symbol.upper()]
        
        if status:
            trades = [t for t in trades if t.status == status]
        
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            trades = [t for t in trades if t.timestamp_entry >= cutoff]
        
        # Sort by timestamp (newest first)
        trades.sort(key=lambda t: t.timestamp_entry, reverse=True)
        
        return trades[:limit]
    
    def get_open_trades(self) -> List[TradeRecord]:
        """Get all open trades"""
        return [trade for trade in self.trades.values() if trade.status == "open"]
    
    def get_performance_summary(self, days: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive performance summary"""
        trades = list(self.trades.values())
        
        if days:
            cutoff = datetime.now() - timedelta(days=days)
            trades = [t for t in trades if t.timestamp_entry >= cutoff]
        
        closed_trades = [t for t in trades if t.status == "closed" and t.pnl_percentage is not None]
        
        if not closed_trades:
            return {"message": "No closed trades found", "total_trades": len(trades)}
        
        # Calculate metrics
        pnl_values = [t.pnl_percentage for t in closed_trades]
        wins = [t for t in closed_trades if t.result == "win"]
        losses = [t for t in closed_trades if t.result == "loss"]
        
        summary = {
            "total_trades": len(trades),
            "closed_trades": len(closed_trades),
            "open_trades": len([t for t in trades if t.status == "open"]),
            "win_rate": (len(wins) / len(closed_trades)) * 100 if closed_trades else 0,
            "total_pnl": sum(pnl_values),
            "avg_pnl": np.mean(pnl_values),
            "best_trade": max(pnl_values),
            "worst_trade": min(pnl_values),
            "avg_win": np.mean([t.pnl_percentage for t in wins]) if wins else 0,
            "avg_loss": np.mean([t.pnl_percentage for t in losses]) if losses else 0,
            "profit_factor": abs(sum([t.pnl_percentage for t in wins]) / sum([t.pnl_percentage for t in losses])) if losses else float('inf'),
            "strategies": self._get_strategy_breakdown(closed_trades),
            "symbols": self._get_symbol_breakdown(closed_trades)
        }
        
        return summary
    
    def _get_strategy_breakdown(self, trades: List[TradeRecord]) -> Dict[str, Dict[str, Any]]:
        """Get performance breakdown by strategy"""
        strategy_stats = defaultdict(list)
        
        for trade in trades:
            if trade.strategy and trade.pnl_percentage is not None:
                strategy_stats[trade.strategy].append(trade.pnl_percentage)
        
        breakdown = {}
        for strategy, pnls in strategy_stats.items():
            breakdown[strategy] = {
                "trades": len(pnls),
                "total_pnl": sum(pnls),
                "avg_pnl": np.mean(pnls),
                "win_rate": (len([p for p in pnls if p > 0]) / len(pnls)) * 100
            }
        
        return breakdown
    
    def _get_symbol_breakdown(self, trades: List[TradeRecord]) -> Dict[str, Dict[str, Any]]:
        """Get performance breakdown by symbol"""
        symbol_stats = defaultdict(list)
        
        for trade in trades:
            if trade.pnl_percentage is not None:
                symbol_stats[trade.symbol].append(trade.pnl_percentage)
        
        breakdown = {}
        for symbol, pnls in symbol_stats.items():
            breakdown[symbol] = {
                "trades": len(pnls),
                "total_pnl": sum(pnls),
                "avg_pnl": np.mean(pnls),
                "win_rate": (len([p for p in pnls if p > 0]) / len(pnls)) * 100
            }
        
        return breakdown
    
    def create_backup(self) -> str:
        """Create backup of current trades"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"trades_backup_{timestamp}.json"
        
        try:
            trades_data = [trade.to_dict() for trade in self.trades.values()]
            with open(backup_file, 'w') as f:
                json.dump(trades_data, f, indent=2, default=str)
            
            logger.info(f"Created backup: {backup_file}")
            return str(backup_file)
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return ""
    
    def cleanup_old_backups(self, keep_days: int = 30):
        """Remove old backup files"""
        cutoff = datetime.now() - timedelta(days=keep_days)
        
        for backup_file in self.backup_dir.glob("trades_backup_*.json"):
            try:
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff:
                    backup_file.unlink()
                    logger.info(f"Removed old backup: {backup_file}")
            except Exception as e:
                logger.warning(f"Error removing backup {backup_file}: {e}")
    
    def export_to_csv(self, filename: Optional[str] = None, days: Optional[int] = None) -> str:
        """Export trades to CSV file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trades_export_{timestamp}.csv"
        
        export_path = self.data_dir / filename
        trades = self.get_history(limit=None, days=days)
        
        if not trades:
            logger.warning("No trades to export")
            return ""
        
        try:
            trades_data = [trade.to_dict() for trade in trades]
            df = pd.DataFrame(trades_data)
            df.to_csv(export_path, index=False)
            
            logger.info(f"Exported {len(trades)} trades to {export_path}")
            return str(export_path)
        except Exception as e:
            logger.error(f"Error exporting trades: {e}")
            return ""
    
    def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """Get summary for specific day"""
        if not date:
            date = datetime.now()
        
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        day_trades = [
            trade for trade in self.trades.values()
            if start_of_day <= trade.timestamp_entry < end_of_day
        ]
        
        closed_trades = [t for t in day_trades if t.status == "closed" and t.pnl_percentage is not None]
        
        summary = {
            "date": date.strftime("%Y-%m-%d"),
            "total_trades": len(day_trades),
            "closed_trades": len(closed_trades),
            "open_trades": len([t for t in day_trades if t.status == "open"]),
            "total_pnl": sum([t.pnl_percentage for t in closed_trades]) if closed_trades else 0,
            "wins": len([t for t in closed_trades if t.result == "win"]),
            "losses": len([t for t in closed_trades if t.result == "loss"]),
            "win_rate": (len([t for t in closed_trades if t.result == "win"]) / len(closed_trades)) * 100 if closed_trades else 0
        }
        
        return summary


# Global trade memory instance
trade_memory = None

def get_trade_memory() -> TradeMemory:
    """Get global trade memory instance"""
    global trade_memory
    if trade_memory is None:
        trade_memory = TradeMemory()
    return trade_memory

def initialize_trade_memory(data_dir: str = "data/trades") -> TradeMemory:
    """Initialize global trade memory"""
    global trade_memory
    trade_memory = TradeMemory(data_dir)
    return trade_memory


if __name__ == "__main__":
    # Test the trade memory system
    logging.basicConfig(level=logging.INFO)
    
    # Initialize
    tm = TradeMemory("test_data/trades")
    
    # Create test trade
    trade = TradeRecord(
        trade_id="",
        symbol="BTCUSDT",
        side="long",
        entry_price=45000.0,
        quantity=0.1,
        stop_loss=44000.0,
        take_profit=47000.0,
        strategy="breakout",
        regime="trending",
        confidence_score=0.85
    )
    
    # Add trade
    trade_id = tm.add_trade(trade)
    print(f"Added trade: {trade_id}")
    
    # Close trade
    tm.close_trade(trade_id, 46500.0)
    
    # Get performance summary
    summary = tm.get_performance_summary()
    print(f"Performance Summary: {json.dumps(summary, indent=2)}")
    
    # Get last trade
    last_trade = tm.get_last_trade()
    print(f"Last trade: {last_trade.trade_id} - PnL: {last_trade.pnl_percentage:.2f}%")
