"""
Smart Trade Memory System - Phase 4 Component 2
==============================================
Secure local trade log and knowledge bank with ML pattern evolution
and reinforcement learning capabilities for the immortal trading network.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import json
import sqlite3
import hashlib
import os

logger = logging.getLogger(__name__)

class TradeOutcome(Enum):
    """Trade execution outcomes."""
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class PatternType(Enum):
    """ML pattern types for evolution."""
    ENTRY_SIGNAL = "entry_signal"
    EXIT_SIGNAL = "exit_signal"
    RISK_MANAGEMENT = "risk_management"
    REGIME_TRANSITION = "regime_transition"

@dataclass
class TradeRecord:
    """Comprehensive trade record for memory system."""
    trade_id: str
    agent_id: str
    symbol: str
    timeframe: str
    trade_type: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    confidence_score: float
    execution_conditions: Dict[str, Any]
    market_regime: str
    consensus_data: Dict[str, Any]
    outcome: TradeOutcome
    pnl: Optional[float]
    execution_time: datetime
    close_time: Optional[datetime]
    metadata: Dict[str, Any]

@dataclass
class PatternEvolution:
    """ML pattern evolution tracking."""
    pattern_id: str
    pattern_type: PatternType
    symbol: str
    timeframe: str
    initial_accuracy: float
    current_accuracy: float
    trade_count: int
    success_count: int
    failure_count: int
    last_evolution: datetime
    reinforcement_score: float

class SmartTradeMemory:
    """Secure trade memory and ML evolution system."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize Smart Trade Memory system."""
        self.config = config
        self.db_path = config.get('db_path', 'unified_system/data/trade_memory.db')
        self.max_trade_records = config.get('max_trade_records', 100000)
        self.retention_days = config.get('retention_days', 365)
        self.min_trades_for_evolution = config.get('min_trades_for_evolution', 20)
        
        # In-memory caches
        self.recent_trades_cache: List[TradeRecord] = []
        self.pattern_cache: Dict[str, PatternEvolution] = {}
        
        # System state
        self.memory_active = False
        
    async def initialize_memory_system(self):
        """Initialize the trade memory system."""
        try:
            logger.info("[TRADE_MEMORY] Initializing Smart Trade Memory System")
            await self._initialize_database()
            await self._load_caches()
            await self._start_background_tasks()
            self.memory_active = True
            logger.info("[TRADE_MEMORY] Smart Trade Memory System initialized successfully")
        except Exception as e:
            logger.error(f"[TRADE_MEMORY] Initialization failed: {e}")
            raise
    
    async def _initialize_database(self):
        """Initialize SQLite database with required tables."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    trade_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trade_type TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    quantity REAL NOT NULL,
                    confidence_score REAL NOT NULL,
                    execution_conditions TEXT,
                    market_regime TEXT,
                    consensus_data TEXT,
                    outcome TEXT NOT NULL,
                    pnl REAL,
                    execution_time TEXT NOT NULL,
                    close_time TEXT,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create patterns table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_type TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    initial_accuracy REAL NOT NULL,
                    current_accuracy REAL NOT NULL,
                    trade_count INTEGER NOT NULL,
                    success_count INTEGER NOT NULL,
                    failure_count INTEGER NOT NULL,
                    last_evolution TEXT NOT NULL,
                    reinforcement_score REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol_time ON trades(symbol, execution_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_agent ON trades(agent_id)')
            
            conn.commit()
            conn.close()
            
            logger.info("[TRADE_MEMORY] Database initialized successfully")
        except Exception as e:
            logger.error(f"[TRADE_MEMORY] Database initialization failed: {e}")
            raise
    
    async def _load_caches(self):
        """Load recent data into memory caches."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Load recent trades
            cursor.execute('SELECT * FROM trades ORDER BY execution_time DESC LIMIT 1000')
            trade_rows = cursor.fetchall()
            self.recent_trades_cache = []
            
            for row in trade_rows:
                trade_record = self._row_to_trade_record(row)
                self.recent_trades_cache.append(trade_record)
            
            # Load active patterns
            cursor.execute('SELECT * FROM patterns WHERE current_accuracy > 0.5')
            pattern_rows = cursor.fetchall()
            
            self.pattern_cache = {}
            for row in pattern_rows:
                pattern = self._row_to_pattern_evolution(row)
                self.pattern_cache[pattern.pattern_id] = pattern
            
            conn.close()
            
            logger.info(f"[TRADE_MEMORY] Loaded {len(self.recent_trades_cache)} trades and {len(self.pattern_cache)} patterns")
        except Exception as e:
            logger.error(f"[TRADE_MEMORY] Cache loading failed: {e}")
    
    def _row_to_trade_record(self, row) -> TradeRecord:
        """Convert database row to TradeRecord."""
        return TradeRecord(
            trade_id=row[0],
            agent_id=row[1],
            symbol=row[2],
            timeframe=row[3],
            trade_type=row[4],
            entry_price=row[5],
            exit_price=row[6],
            quantity=row[7],
            confidence_score=row[8],
            execution_conditions=json.loads(row[9]) if row[9] else {},
            market_regime=row[10] or "unknown",
            consensus_data=json.loads(row[11]) if row[11] else {},
            outcome=TradeOutcome(row[12]),
            pnl=row[13],
            execution_time=datetime.fromisoformat(row[14]),
            close_time=datetime.fromisoformat(row[15]) if row[15] else None,
            metadata=json.loads(row[16]) if row[16] else {}
        )
    
    def _row_to_pattern_evolution(self, row) -> PatternEvolution:
        """Convert database row to PatternEvolution."""
        return PatternEvolution(
            pattern_id=row[0],
            pattern_type=PatternType(row[1]),
            symbol=row[2],
            timeframe=row[3],
            initial_accuracy=row[4],
            current_accuracy=row[5],
            trade_count=row[6],
            success_count=row[7],
            failure_count=row[8],
            last_evolution=datetime.fromisoformat(row[9]),
            reinforcement_score=row[10]
        )
    
    async def _start_background_tasks(self):
        """Start background maintenance and evolution tasks."""
        asyncio.create_task(self._pattern_evolution_loop())
        asyncio.create_task(self._memory_maintenance_loop())
        logger.info("[TRADE_MEMORY] Background tasks started")
    
    async def record_trade(self, trade_record: TradeRecord) -> bool:
        """Record a new trade in the memory system."""
        try:
            logger.info(f"[TRADE_MEMORY] Recording trade: {trade_record.trade_id}")
            
            # Add to cache
            self.recent_trades_cache.insert(0, trade_record)
            if len(self.recent_trades_cache) > 1000:
                self.recent_trades_cache = self.recent_trades_cache[:1000]
            
            # Store in database
            await self._store_trade_in_db(trade_record)
            
            # Update pattern performance
            if trade_record.outcome in [TradeOutcome.EXECUTED, TradeOutcome.CANCELLED]:
                await self._update_pattern_performance(trade_record)
            
            return True
        except Exception as e:
            logger.error(f"[TRADE_MEMORY] Failed to record trade: {e}")
            return False
    
    async def _store_trade_in_db(self, trade_record: TradeRecord):
        """Store trade record in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trades (
                trade_id, agent_id, symbol, timeframe, trade_type,
                entry_price, exit_price, quantity, confidence_score,
                execution_conditions, market_regime, consensus_data,
                outcome, pnl, execution_time, close_time, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_record.trade_id, trade_record.agent_id, trade_record.symbol,
            trade_record.timeframe, trade_record.trade_type, trade_record.entry_price,
            trade_record.exit_price, trade_record.quantity, trade_record.confidence_score,
            json.dumps(trade_record.execution_conditions), trade_record.market_regime,
            json.dumps(trade_record.consensus_data), trade_record.outcome.value,
            trade_record.pnl, trade_record.execution_time.isoformat(),
            trade_record.close_time.isoformat() if trade_record.close_time else None,
            json.dumps(trade_record.metadata)
        ))
        
        conn.commit()
        conn.close()
    
    async def execute_memory_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute memory system command."""
        try:
            params = params or {}
            
            if command == 'memory_last':
                return await self._handle_memory_last(params)
            elif command == 'memory_pattern_evolve':
                return await self._handle_pattern_evolve(params)
            elif command == 'memory_stats':
                return await self._handle_memory_stats(params)
            else:
                return {'success': False, 'error': f'Unknown memory command: {command}'}
        except Exception as e:
            logger.error(f"[TRADE_MEMORY] Command execution failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _handle_memory_last(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle /memory last command."""
        count = params.get('count', 5)
        agent_id = params.get('agent_id')
        symbol = params.get('symbol')
        
        # Filter recent trades
        filtered_trades = self.recent_trades_cache
        
        if agent_id:
            filtered_trades = [t for t in filtered_trades if t.agent_id == agent_id]
        if symbol:
            filtered_trades = [t for t in filtered_trades if t.symbol == symbol]
        
        # Get last N trades
        last_trades = filtered_trades[:count]
        
        # Format trade summaries
        trade_summaries = []
        for trade in last_trades:
            summary = {
                'trade_id': trade.trade_id,
                'agent_id': trade.agent_id,
                'symbol': trade.symbol,
                'trade_type': trade.trade_type,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'confidence_score': trade.confidence_score,
                'outcome': trade.outcome.value,
                'pnl': trade.pnl,
                'execution_time': trade.execution_time.isoformat(),
                'market_regime': trade.market_regime
            }
            trade_summaries.append(summary)
        
        return {
            'success': True,
            'message': f'Retrieved {len(trade_summaries)} recent trades',
            'trades': trade_summaries,
            'total_in_memory': len(self.recent_trades_cache),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _handle_pattern_evolve(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle /memory pattern evolve command."""
        logger.info("[TRADE_MEMORY] Executing pattern evolution cycle")
        
        evolution_results = []
        for pattern_id, pattern in self.pattern_cache.items():
            old_accuracy = pattern.current_accuracy
            await self._evolve_pattern(pattern)
            
            evolution_results.append({
                'pattern_id': pattern_id,
                'pattern_type': pattern.pattern_type.value,
                'symbol': pattern.symbol,
                'old_accuracy': old_accuracy,
                'new_accuracy': pattern.current_accuracy,
                'improvement': pattern.current_accuracy - old_accuracy,
                'trade_count': pattern.trade_count,
                'reinforcement_score': pattern.reinforcement_score
            })
        
        return {
            'success': True,
            'message': f'Pattern evolution completed for {len(evolution_results)} patterns',
            'evolution_results': evolution_results,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _handle_memory_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle memory statistics command."""
        total_trades = len(self.recent_trades_cache)
        
        if total_trades == 0:
            return {'success': True, 'message': 'No trades in memory', 'stats': {'total_trades': 0}}
        
        # Calculate statistics
        total_pnl = sum(trade.pnl for trade in self.recent_trades_cache if trade.pnl)
        avg_confidence = sum(trade.confidence_score for trade in self.recent_trades_cache) / total_trades
        
        successful_trades = len([t for t in self.recent_trades_cache 
                               if t.outcome == TradeOutcome.EXECUTED and (t.pnl or 0) > 0])
        success_rate = (successful_trades / total_trades) * 100
        
        return {
            'success': True,
            'stats': {
                'total_trades': total_trades,
                'total_pnl': total_pnl,
                'average_confidence': avg_confidence,
                'success_rate': success_rate,
                'active_patterns': len(self.pattern_cache)
            },
            'timestamp': datetime.now().isoformat()
        }
    
    async def _update_pattern_performance(self, trade_record: TradeRecord):
        """Update pattern performance based on trade outcome."""
        try:
            pattern_id = self._generate_pattern_id(trade_record)
            
            if pattern_id not in self.pattern_cache:
                pattern = PatternEvolution(
                    pattern_id=pattern_id,
                    pattern_type=PatternType.ENTRY_SIGNAL,
                    symbol=trade_record.symbol,
                    timeframe=trade_record.timeframe,
                    initial_accuracy=0.5,
                    current_accuracy=0.5,
                    trade_count=0,
                    success_count=0,
                    failure_count=0,
                    last_evolution=datetime.now(),
                    reinforcement_score=0.0
                )
                self.pattern_cache[pattern_id] = pattern
            else:
                pattern = self.pattern_cache[pattern_id]
            
            # Update pattern with trade result
            pattern.trade_count += 1
            
            if trade_record.outcome == TradeOutcome.EXECUTED and (trade_record.pnl or 0) > 0:
                pattern.success_count += 1
            else:
                pattern.failure_count += 1
            
            # Recalculate accuracy
            if pattern.trade_count > 0:
                pattern.current_accuracy = pattern.success_count / pattern.trade_count
            
            # Update reinforcement score
            pattern.reinforcement_score = self._calculate_reinforcement_score(pattern)
            
            # Store updated pattern
            await self._store_pattern_in_db(pattern)
        except Exception as e:
            logger.error(f"[TRADE_MEMORY] Pattern update failed: {e}")
    
    def _generate_pattern_id(self, trade_record: TradeRecord) -> str:
        """Generate unique pattern ID based on trade characteristics."""
        pattern_string = f"{trade_record.symbol}_{trade_record.timeframe}_{trade_record.market_regime}_{trade_record.trade_type}"
        return hashlib.md5(pattern_string.encode()).hexdigest()[:16]
    
    def _calculate_reinforcement_score(self, pattern: PatternEvolution) -> float:
        """Calculate reinforcement learning score for pattern."""
        if pattern.trade_count == 0:
            return 0.0
        
        accuracy_score = pattern.current_accuracy * 100
        volume_bonus = min(20, pattern.trade_count * 0.5)
        total_score = accuracy_score + volume_bonus
        
        return min(100.0, max(0.0, total_score))
    
    async def _store_pattern_in_db(self, pattern: PatternEvolution):
        """Store pattern evolution in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO patterns (
                pattern_id, pattern_type, symbol, timeframe,
                initial_accuracy, current_accuracy, trade_count,
                success_count, failure_count, last_evolution,
                reinforcement_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern.pattern_id, pattern.pattern_type.value, pattern.symbol,
            pattern.timeframe, pattern.initial_accuracy, pattern.current_accuracy,
            pattern.trade_count, pattern.success_count, pattern.failure_count,
            pattern.last_evolution.isoformat(), pattern.reinforcement_score
        ))
        
        conn.commit()
        conn.close()
    
    async def _pattern_evolution_loop(self):
        """Background pattern evolution loop."""
        while self.memory_active:
            try:
                patterns_to_evolve = [
                    pattern for pattern in self.pattern_cache.values()
                    if pattern.trade_count >= self.min_trades_for_evolution
                ]
                
                for pattern in patterns_to_evolve:
                    await self._evolve_pattern(pattern)
                
                if patterns_to_evolve:
                    logger.info(f"[TRADE_MEMORY] Evolved {len(patterns_to_evolve)} patterns")
                
                await asyncio.sleep(3600)  # Check every hour
            except Exception as e:
                logger.error(f"[TRADE_MEMORY] Pattern evolution loop error: {e}")
                await asyncio.sleep(1800)
    
    async def _evolve_pattern(self, pattern: PatternEvolution):
        """Evolve a specific pattern using reinforcement learning."""
        if pattern.trade_count >= 10:
            recent_success_rate = pattern.success_count / pattern.trade_count
            adjustment_factor = 0.1
            
            pattern.current_accuracy = (
                pattern.current_accuracy * (1 - adjustment_factor) +
                recent_success_rate * adjustment_factor
            )
        
        pattern.last_evolution = datetime.now()
        pattern.reinforcement_score = self._calculate_reinforcement_score(pattern)
        await self._store_pattern_in_db(pattern)
    
    async def _memory_maintenance_loop(self):
        """Background memory maintenance loop."""
        while self.memory_active:
            try:
                # Clean old trades beyond retention period
                cutoff_date = datetime.now() - timedelta(days=self.retention_days)
                
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM trades WHERE execution_time < ?', (cutoff_date.isoformat(),))
                cursor.execute('DELETE FROM patterns WHERE last_evolution < ?', (cutoff_date.isoformat(),))
                conn.commit()
                conn.close()
                
                # Refresh caches
                await self._load_caches()
                
                await asyncio.sleep(86400)  # Daily maintenance
            except Exception as e:
                logger.error(f"[TRADE_MEMORY] Maintenance error: {e}")
                await asyncio.sleep(3600)
    
    def get_memory_status(self) -> Dict[str, Any]:
        """Get current memory system status."""
        return {
            'memory_active': self.memory_active,
            'total_trades_cached': len(self.recent_trades_cache),
            'active_patterns': len(self.pattern_cache),
            'retention_days': self.retention_days,
            'timestamp': datetime.now().isoformat()
        }

# Global smart trade memory instance
_smart_trade_memory = None

def initialize_smart_trade_memory(config: Dict[str, Any]) -> SmartTradeMemory:
    """Initialize the global smart trade memory."""
    global _smart_trade_memory
    _smart_trade_memory = SmartTradeMemory(config)
    return _smart_trade_memory

def get_smart_trade_memory() -> Optional[SmartTradeMemory]:
    """Get the global smart trade memory instance."""
    return _smart_trade_memory

async def main():
    """Main function for testing smart trade memory."""
    config = {
        'db_path': 'unified_system/data/trade_memory.db',
        'max_trade_records': 100000,
        'retention_days': 365,
        'min_trades_for_evolution': 20
    }
    
    memory = initialize_smart_trade_memory(config)
    await memory.initialize_memory_system()
    
    print("[TRADE_MEMORY] Smart Trade Memory System is running...")
    print("[TRADE_MEMORY] Available commands:")
    print("  - /memory last")
    print("  - /memory pattern evolve")
    print("  - /memory stats")
    
    try:
        while True:
            await asyncio.sleep(60)
            status = memory.get_memory_status()
            print(f"[HEARTBEAT] {datetime.now().strftime('%H:%M:%S')} - Memory Status: {status['total_trades_cached']} trades, {status['active_patterns']} patterns")
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Smart Trade Memory System shutting down...")

if __name__ == "__main__":
    asyncio.run(main())
