"""
Auto-Recovery Engine
===================
Intelligent state persistence and recovery system for the crypto trading bot.
Saves critical runtime state and enables seamless recovery after restarts.

Features:
- Save/restore open trades and positions
- Persist active regime and strategy state
- Store current playbook and parameters
- Track last price data and trading plans
- Automatic recovery on startup
- Admin notifications with memory snapshots
- Configurable recovery modes
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import pickle
import threading
import time

from trade_memory import TradeMemory, TradeRecord, get_trade_memory

logger = logging.getLogger(__name__)

@dataclass
class BotState:
    """Complete bot state for recovery"""
    # Timestamp
    timestamp: datetime
    session_id: str
    
    # Trading state
    open_trades: List[Dict[str, Any]]
    active_positions: Dict[str, Any]
    
    # Market analysis state
    current_regime: str
    active_strategy: str
    regime_confidence: float
    
    # Playbook state
    current_playbook: Dict[str, Any]
    playbook_parameters: Dict[str, Any]
    
    # Market data
    last_prices: Dict[str, float]
    market_conditions: Dict[str, Any]
    
    # Trading plan
    pending_signals: List[Dict[str, Any]]
    risk_metrics: Dict[str, Any]
    
    # Configuration
    trading_enabled: bool
    daily_stats: Dict[str, Any]
    
    def __post_init__(self):
        if not self.session_id:
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with datetime serialization"""
        data = asdict(self)
        data['timestamp'] = data['timestamp'].isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BotState':
        """Create BotState from dictionary"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class AutoRecoveryEngine:
    """Auto-Recovery Engine for bot state management"""
    
    def __init__(self, data_dir: str = "data/recovery", config: Optional[Dict[str, Any]] = None):
        """Initialize auto-recovery engine"""
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.config = config or {}
        self.config.setdefault('recovery_enabled', True)
        self.config.setdefault('auto_save_interval', 300)  # 5 minutes
        self.config.setdefault('max_recovery_age_hours', 24)
        self.config.setdefault('backup_retention_days', 7)
        self.config.setdefault('notify_admin_on_recovery', True)
        
        # File paths
        self.state_file = self.data_dir / "bot_state.json"
        self.backup_dir = self.data_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)
        
        # Runtime state
        self.current_state: Optional[BotState] = None
        self.auto_save_thread: Optional[threading.Thread] = None
        self.running = False
        
        # Trade memory integration
        self.trade_memory = get_trade_memory()
        
        logger.info(f"Auto-Recovery Engine initialized. Recovery enabled: {self.config['recovery_enabled']}")
    
    def save_state(self, 
                   open_trades: Optional[List[TradeRecord]] = None,
                   regime: str = "",
                   strategy: str = "",
                   regime_confidence: float = 0.0,
                   playbook: Optional[Dict[str, Any]] = None,
                   playbook_params: Optional[Dict[str, Any]] = None,
                   last_prices: Optional[Dict[str, float]] = None,
                   market_conditions: Optional[Dict[str, Any]] = None,
                   pending_signals: Optional[List[Dict[str, Any]]] = None,
                   risk_metrics: Optional[Dict[str, Any]] = None,
                   trading_enabled: bool = True,
                   daily_stats: Optional[Dict[str, Any]] = None) -> bool:
        """Save current bot state"""
        
        try:
            # Get open trades from trade memory if not provided
            if open_trades is None:
                open_trades = self.trade_memory.get_open_trades()
            
            # Convert trades to dict format
            open_trades_data = [trade.to_dict() for trade in open_trades]
            
            # Create state object
            state = BotState(
                timestamp=datetime.now(),
                session_id=self.trade_memory.session_id,
                open_trades=open_trades_data,
                active_positions=self._get_active_positions(),
                current_regime=regime,
                active_strategy=strategy,
                regime_confidence=regime_confidence,
                current_playbook=playbook or {},
                playbook_parameters=playbook_params or {},
                last_prices=last_prices or {},
                market_conditions=market_conditions or {},
                pending_signals=pending_signals or [],
                risk_metrics=risk_metrics or {},
                trading_enabled=trading_enabled,
                daily_stats=daily_stats or {}
            )
            
            # Save to file
            with open(self.state_file, 'w') as f:
                json.dump(state.to_dict(), f, indent=2, default=str)
            
            self.current_state = state
            
            logger.debug(f"Saved bot state with {len(open_trades_data)} open trades")
            return True
            
        except Exception as e:
            logger.error(f"Error saving bot state: {e}")
            return False
    
    def load_state(self) -> Optional[BotState]:
        """Load saved bot state"""
        if not self.state_file.exists():
            logger.info("No saved state found")
            return None
        
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
            
            state = BotState.from_dict(data)
            
            # Check if state is too old
            age_hours = (datetime.now() - state.timestamp).total_seconds() / 3600
            if age_hours > self.config['max_recovery_age_hours']:
                logger.warning(f"Saved state is {age_hours:.1f} hours old, skipping recovery")
                return None
            
            self.current_state = state
            logger.info(f"Loaded bot state from {state.timestamp} ({age_hours:.1f} hours ago)")
            return state
            
        except Exception as e:
            logger.error(f"Error loading bot state: {e}")
            return None
    
    def recover_state(self) -> Tuple[bool, Dict[str, Any]]:
        """Attempt to recover bot state and return recovery info"""
        if not self.config['recovery_enabled']:
            return False, {"message": "Recovery disabled in configuration"}
        
        state = self.load_state()
        if not state:
            return False, {"message": "No valid state found for recovery"}
        
        recovery_info = {
            "recovered": True,
            "timestamp": state.timestamp.isoformat(),
            "session_id": state.session_id,
            "open_trades_count": len(state.open_trades),
            "regime": state.current_regime,
            "strategy": state.active_strategy,
            "trading_enabled": state.trading_enabled,
            "recovery_actions": []
        }
        
        try:
            # Restore open trades to trade memory
            if state.open_trades:
                for trade_data in state.open_trades:
                    trade = TradeRecord.from_dict(trade_data)
                    # Only add if not already in memory
                    if trade.trade_id not in self.trade_memory.trades:
                        self.trade_memory.trades[trade.trade_id] = trade
                        recovery_info["recovery_actions"].append(f"Restored trade: {trade.trade_id}")
            
            # Create recovery summary
            recovery_info["summary"] = self._create_recovery_summary(state)
            
            logger.info(f"Successfully recovered bot state: {len(state.open_trades)} open trades")
            
            # Notify admin if configured
            if self.config['notify_admin_on_recovery']:
                self._notify_admin_recovery(recovery_info)
            
            return True, recovery_info
            
        except Exception as e:
            logger.error(f"Error during state recovery: {e}")
            return False, {"message": f"Recovery failed: {str(e)}"}
    
    def _get_active_positions(self) -> Dict[str, Any]:
        """Get current active positions (placeholder for exchange integration)"""
        # This would integrate with the actual trading system
        # For now, return empty dict
        return {}
    
    def _create_recovery_summary(self, state: BotState) -> Dict[str, Any]:
        """Create comprehensive recovery summary"""
        return {
            "recovery_time": datetime.now().isoformat(),
            "original_session": state.session_id,
            "state_age_hours": (datetime.now() - state.timestamp).total_seconds() / 3600,
            "open_trades": len(state.open_trades),
            "market_regime": state.current_regime,
            "active_strategy": state.active_strategy,
            "regime_confidence": state.regime_confidence,
            "trading_status": "enabled" if state.trading_enabled else "disabled",
            "last_prices_count": len(state.last_prices),
            "pending_signals": len(state.pending_signals),
            "playbook_active": bool(state.current_playbook)
        }
    
    def _notify_admin_recovery(self, recovery_info: Dict[str, Any]):
        """Send recovery notification to admin (placeholder)"""
        # This would integrate with the Telegram notification system
        logger.info(f"Recovery notification: {recovery_info['summary']}")
    
    def start_auto_save(self):
        """Start automatic state saving thread"""
        if self.auto_save_thread and self.auto_save_thread.is_alive():
            logger.warning("Auto-save thread already running")
            return
        
        self.running = True
        self.auto_save_thread = threading.Thread(target=self._auto_save_loop, daemon=True)
        self.auto_save_thread.start()
        
        logger.info(f"Started auto-save thread (interval: {self.config['auto_save_interval']}s)")
    
    def stop_auto_save(self):
        """Stop automatic state saving"""
        self.running = False
        if self.auto_save_thread:
            self.auto_save_thread.join(timeout=5)
        
        logger.info("Stopped auto-save thread")
    
    def _auto_save_loop(self):
        """Auto-save loop running in background thread"""
        while self.running:
            try:
                # Save current state (basic version for auto-save)
                self.save_state()
                
                # Sleep for configured interval
                time.sleep(self.config['auto_save_interval'])
                
            except Exception as e:
                logger.error(f"Error in auto-save loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def create_backup(self) -> str:
        """Create backup of current state"""
        if not self.current_state:
            logger.warning("No current state to backup")
            return ""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"state_backup_{timestamp}.json"
        
        try:
            with open(backup_file, 'w') as f:
                json.dump(self.current_state.to_dict(), f, indent=2, default=str)
            
            logger.info(f"Created state backup: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return ""
    
    def cleanup_old_backups(self):
        """Remove old backup files"""
        cutoff = datetime.now() - timedelta(days=self.config['backup_retention_days'])
        
        for backup_file in self.backup_dir.glob("state_backup_*.json"):
            try:
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff:
                    backup_file.unlink()
                    logger.info(f"Removed old backup: {backup_file}")
            except Exception as e:
                logger.warning(f"Error removing backup {backup_file}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get recovery engine status"""
        return {
            "recovery_enabled": self.config['recovery_enabled'],
            "auto_save_running": self.auto_save_thread and self.auto_save_thread.is_alive(),
            "auto_save_interval": self.config['auto_save_interval'],
            "has_saved_state": self.state_file.exists(),
            "current_state_time": self.current_state.timestamp.isoformat() if self.current_state else None,
            "backup_count": len(list(self.backup_dir.glob("state_backup_*.json"))),
            "data_directory": str(self.data_dir)
        }
    
    def force_recovery_test(self) -> Dict[str, Any]:
        """Test recovery functionality (for debugging)"""
        logger.info("Running recovery test...")
        
        # Save current state
        save_success = self.save_state(
            regime="test_regime",
            strategy="test_strategy",
            regime_confidence=0.75,
            trading_enabled=True
        )
        
        if not save_success:
            return {"success": False, "message": "Failed to save test state"}
        
        # Try to recover
        recovery_success, recovery_info = self.recover_state()
        
        return {
            "success": recovery_success,
            "save_success": save_success,
            "recovery_info": recovery_info
        }


# Global recovery engine instance
recovery_engine = None

def get_recovery_engine() -> AutoRecoveryEngine:
    """Get global recovery engine instance"""
    global recovery_engine
    if recovery_engine is None:
        recovery_engine = AutoRecoveryEngine()
    return recovery_engine

def initialize_recovery_engine(data_dir: str = "data/recovery", 
                             config: Optional[Dict[str, Any]] = None) -> AutoRecoveryEngine:
    """Initialize global recovery engine"""
    global recovery_engine
    recovery_engine = AutoRecoveryEngine(data_dir, config)
    return recovery_engine


if __name__ == "__main__":
    # Test the auto-recovery system
    logging.basicConfig(level=logging.INFO)
    
    # Initialize
    engine = AutoRecoveryEngine("test_data/recovery")
    
    # Test save and recovery
    test_result = engine.force_recovery_test()
    print(f"Recovery test result: {json.dumps(test_result, indent=2)}")
    
    # Get status
    status = engine.get_status()
    print(f"Recovery engine status: {json.dumps(status, indent=2)}")
