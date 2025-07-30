#!/usr/bin/env python3
"""
Smart Trade Planner for Bidget Auto Trading Bot
----------------------------------------------
Dynamically plans trades based on market regime and selected playbook.
"""
import os
import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime

from playbook import Playbook
from market_regime import MarketRegime

# Configure logging
logger = logging.getLogger(__name__)

class SmartTradePlanner:
    """
    Smart Trade Planner that dynamically plans trades based on market regime
    and selected playbook parameters.
    """
    
    def __init__(self, data_dir: str = 'data', enable_playbooks: bool = True):
        """Initialize the smart trade planner.
        
        Args:
            data_dir (str): Directory for data files
            enable_playbooks (bool): Whether to enable playbook-based planning
        """
        self.data_dir = data_dir
        self.enable_playbooks = enable_playbooks
        
        # Initialize playbook system
        self.playbook = Playbook(data_dir=data_dir)
        
        # Initialize market regime detector
        self.market_regime = MarketRegime(data_dir=data_dir)
        
        # Create data directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        logger.info("Smart Trade Planner initialized")
        if self.enable_playbooks:
            logger.info("Playbook-based trade planning enabled")
    
    def detect_regime_and_get_playbook(self, df: pd.DataFrame, symbol: str, 
                                       timeframe: str) -> Tuple[str, Dict[str, Any]]:
        """Detect the current market regime and get corresponding playbook.
        
        Args:
            df (pd.DataFrame): OHLCV data
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            
        Returns:
            tuple: (regime_name, playbook_params)
        """
        # Detect market regime
        regime = self.market_regime.detect_regime(df, symbol, timeframe)
        
        # Get playbook for the detected regime
        playbook_params = self.playbook.get_playbook(regime)
        
        logger.info(f"Detected {regime} regime for {symbol} on {timeframe}, using corresponding playbook")
        return regime, playbook_params
    
    def calculate_stop_loss(self, df: pd.DataFrame, entry_price: float, 
                            playbook_params: Dict[str, Any], 
                            position_type: str = 'long') -> float:
        """Calculate stop loss based on playbook parameters.
        
        Args:
            df (pd.DataFrame): OHLCV data
            entry_price (float): Entry price
            playbook_params (dict): Playbook parameters
            position_type (str): Position type ('long' or 'short')
            
        Returns:
            float: Stop loss price
        """
        stop_loss_type = playbook_params.get('stop_loss', 'atr_2.0')
        
        if 'atr' in stop_loss_type:
            # Extract the multiplier from the string (e.g., "atr_2.0" -> 2.0)
            try:
                multiplier = float(stop_loss_type.split('_')[1])
            except (IndexError, ValueError):
                multiplier = 2.0  # Default if parsing fails
            
            # Calculate ATR
            high = df['high'].values
            low = df['low'].values
            close = pd.Series(df['close'].values)
            
            tr1 = pd.Series(high - low)
            tr2 = pd.Series(abs(high - close.shift()))
            tr3 = pd.Series(abs(low - close.shift()))
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean().iloc[-1]
            
            # Calculate stop loss based on ATR
            if position_type.lower() == 'long':
                stop_loss = entry_price - (atr * multiplier)
            else:
                stop_loss = entry_price + (atr * multiplier)
        
        elif stop_loss_type == 'range_boundary':
            # Calculate range boundaries
            recent_high = df['high'].rolling(20).max().iloc[-1]
            recent_low = df['low'].rolling(20).min().iloc[-1]
            
            if position_type.lower() == 'long':
                stop_loss = recent_low
            else:
                stop_loss = recent_high
        
        elif stop_loss_type == 'swing_high_low':
            # Find swing highs and lows
            highs = df['high'].rolling(5, center=True).max()
            lows = df['low'].rolling(5, center=True).min()
            
            if position_type.lower() == 'long':
                # Find the most recent swing low
                recent_lows = lows.iloc[-10:]
                swing_low = recent_lows.min()
                stop_loss = swing_low
            else:
                # Find the most recent swing high
                recent_highs = highs.iloc[-10:]
                swing_high = recent_highs.max()
                stop_loss = swing_high
        
        else:
            # Default to 2% below/above entry price
            if position_type.lower() == 'long':
                stop_loss = entry_price * 0.98
            else:
                stop_loss = entry_price * 1.02
        
        return stop_loss
    
    def calculate_take_profit_levels(self, df: pd.DataFrame, entry_price: float, 
                                    stop_loss: float, playbook_params: Dict[str, Any],
                                    position_type: str = 'long') -> List[float]:
        """Calculate take profit levels based on playbook parameters.
        
        Args:
            df (pd.DataFrame): OHLCV data
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            playbook_params (dict): Playbook parameters
            position_type (str): Position type ('long' or 'short')
            
        Returns:
            list: Take profit price levels
        """
        take_profit_types = playbook_params.get('take_profit', ['r1'])
        take_profit_levels = []
        
        # Calculate risk (distance from entry to stop loss)
        risk = abs(entry_price - stop_loss)
        
        for tp_type in take_profit_types:
            if tp_type == 'r1':
                # R1 = 1x the risk
                if position_type.lower() == 'long':
                    tp = entry_price + risk
                else:
                    tp = entry_price - risk
                take_profit_levels.append(tp)
            
            elif tp_type == 'r2':
                # R2 = 2x the risk
                if position_type.lower() == 'long':
                    tp = entry_price + (risk * 2)
                else:
                    tp = entry_price - (risk * 2)
                take_profit_levels.append(tp)
            
            elif tp_type == 'r3':
                # R3 = 3x the risk
                if position_type.lower() == 'long':
                    tp = entry_price + (risk * 3)
                else:
                    tp = entry_price - (risk * 3)
                take_profit_levels.append(tp)
            
            elif tp_type == 's1':
                # Support level 1 (for shorts)
                lows = df['low'].rolling(20).min().iloc[-20:]
                s1 = lows.nsmallest(2).iloc[-1]
                take_profit_levels.append(s1)
            
            elif tp_type == 's2':
                # Support level 2 (for shorts)
                lows = df['low'].rolling(30).min().iloc[-30:]
                s2 = lows.nsmallest(3).iloc[-1]
                take_profit_levels.append(s2)
            
            elif tp_type == 's3':
                # Support level 3 (for shorts)
                lows = df['low'].rolling(50).min().iloc[-50:]
                s3 = lows.nsmallest(5).iloc[-1]
                take_profit_levels.append(s3)
            
            elif tp_type == 'range_opposite':
                # Opposite side of the range
                recent_high = df['high'].rolling(20).max().iloc[-1]
                recent_low = df['low'].rolling(20).min().iloc[-1]
                
                if position_type.lower() == 'long':
                    tp = recent_high
                else:
                    tp = recent_low
                take_profit_levels.append(tp)
            
            elif tp_type.startswith('fib_'):
                # Fibonacci extension
                try:
                    fib_level = float(tp_type.split('_')[1])
                except (IndexError, ValueError):
                    fib_level = 1.618  # Default if parsing fails
                
                # Calculate the Fibonacci extension
                if position_type.lower() == 'long':
                    tp = entry_price + (risk * fib_level)
                else:
                    tp = entry_price - (risk * fib_level)
                take_profit_levels.append(tp)
            
            elif tp_type.startswith('atr_'):
                # ATR multiple
                try:
                    atr_multiple = float(tp_type.split('_')[1])
                except (IndexError, ValueError):
                    atr_multiple = 3.0  # Default if parsing fails
                
                # Calculate ATR
                high = df['high'].values
                low = df['low'].values
                close = pd.Series(df['close'].values)
                
                tr1 = pd.Series(high - low)
                tr2 = pd.Series(abs(high - close.shift()))
                tr3 = pd.Series(abs(low - close.shift()))
                
                tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
                atr = tr.rolling(14).mean().iloc[-1]
                
                # Calculate take profit based on ATR multiple
                if position_type.lower() == 'long':
                    tp = entry_price + (atr * atr_multiple)
                else:
                    tp = entry_price - (atr * atr_multiple)
                take_profit_levels.append(tp)
        
        # If no take profit levels were calculated, use a default 2:1 reward-to-risk ratio
        if not take_profit_levels:
            if position_type.lower() == 'long':
                tp = entry_price + (risk * 2)
            else:
                tp = entry_price - (risk * 2)
            take_profit_levels.append(tp)
        
        return take_profit_levels
    
    def get_leverage(self, playbook_params: Dict[str, Any]) -> float:
        """Get leverage based on playbook parameters.
        
        Args:
            playbook_params (dict): Playbook parameters
            
        Returns:
            float: Leverage value
        """
        return float(playbook_params.get('leverage', 1.0))
    
    def plan_trade(self, df: pd.DataFrame, entry_price: float, symbol: str, 
                   timeframe: str, position_type: str = 'long',
                   override_regime: str = None) -> Dict[str, Any]:
        """Plan a trade based on market data, regime, and playbook.
        
        Args:
            df (pd.DataFrame): OHLCV data
            entry_price (float): Entry price
            symbol (str): Trading symbol
            timeframe (str): Timeframe
            position_type (str): Position type ('long' or 'short')
            override_regime (str): Override detected regime with this value
            
        Returns:
            dict: Complete trade plan with entry, exit, and risk parameters
        """
        # Detect regime and get playbook
        if override_regime:
            regime = override_regime
            playbook_params = self.playbook.get_playbook(regime)
            logger.info(f"Using overridden regime: {regime}")
        else:
            regime, playbook_params = self.detect_regime_and_get_playbook(df, symbol, timeframe)
        
        # Calculate stop loss
        stop_loss = self.calculate_stop_loss(df, entry_price, playbook_params, position_type)
        
        # Calculate take profit levels
        take_profit_levels = self.calculate_take_profit_levels(
            df, entry_price, stop_loss, playbook_params, position_type
        )
        
        # Get leverage
        leverage = self.get_leverage(playbook_params)
        
        # Get strategy
        strategy = playbook_params.get('strategy', 'supertrend')
        entry_type = playbook_params.get('entry_type', 'breakout')
        risk_level = playbook_params.get('risk_level', 'moderate')
        filters = playbook_params.get('filters', {})
        
        # Calculate risk-reward ratio
        risk = abs(entry_price - stop_loss)
        reward = abs(entry_price - take_profit_levels[0])
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        # Create the complete trade plan
        trade_plan = {
            'symbol': symbol,
            'timeframe': timeframe,
            'regime': regime,
            'strategy': strategy,
            'entry_type': entry_type,
            'position_type': position_type,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit_levels': take_profit_levels,
            'leverage': leverage,
            'risk_level': risk_level,
            'risk_reward_ratio': risk_reward_ratio,
            'timestamp': datetime.utcnow().isoformat(),
            'filters': filters
        }
        
        logger.info(f"Generated trade plan for {symbol} on {timeframe} in {regime} regime")
        return trade_plan
    
    def format_trade_plan_message(self, trade_plan: Dict[str, Any]) -> str:
        """Format a trade plan as a readable message for Telegram or console.
        
        Args:
            trade_plan (dict): Trade plan
            
        Returns:
            str: Formatted message
        """
        symbol = trade_plan['symbol']
        timeframe = trade_plan['timeframe']
        regime = trade_plan['regime']
        position_type = trade_plan['position_type'].upper()
        entry = trade_plan['entry_price']
        stop = trade_plan['stop_loss']
        tp_levels = trade_plan['take_profit_levels']
        rr = trade_plan['risk_reward_ratio']
        leverage = trade_plan['leverage']
        strategy = trade_plan['strategy']
        entry_type = trade_plan['entry_type']
        
        # Emoji based on position type
        emoji = "🟢" if position_type == "LONG" else "🔴"
        
        # Format take profit levels
        tp_formatted = []
        for i, tp in enumerate(tp_levels):
            tp_formatted.append(f"TP{i+1}: {tp:.6f}")
        
        tp_text = " | ".join(tp_formatted)
        
        # Calculate potential profit percentages
        profit_percentages = []
        for tp in tp_levels:
            if position_type == "LONG":
                pct = ((tp - entry) / entry) * 100 * leverage
            else:
                pct = ((entry - tp) / entry) * 100 * leverage
            profit_percentages.append(f"{pct:.2f}%")
        
        profit_text = " | ".join(profit_percentages)
        
        # Calculate potential loss percentage
        if position_type == "LONG":
            loss_pct = ((entry - stop) / entry) * 100 * leverage
        else:
            loss_pct = ((stop - entry) / entry) * 100 * leverage
        
        message = (
            f"📊 TRADE PLAN: {emoji} {position_type} {symbol} ({timeframe})\n\n"
            f"🔍 Market Regime: {regime.upper()}\n"
            f"📈 Strategy: {strategy.upper()} ({entry_type})\n\n"
            f"📍 Entry: {entry:.6f}\n"
            f"🛑 Stop Loss: {stop:.6f} (-{loss_pct:.2f}%)\n"
            f"🎯 Take Profit: {tp_text}\n"
            f"💰 Potential Profits: {profit_text}\n\n"
            f"📊 Risk/Reward: {rr:.2f}\n"
            f"⚡ Leverage: {leverage}x\n"
        )
        
        return message
    
    def save_trade_plan(self, trade_plan: Dict[str, Any]) -> str:
        """Save a trade plan to the data directory.
        
        Args:
            trade_plan (dict): Trade plan
            
        Returns:
            str: Path to the saved trade plan
        """
        # Create a unique filename
        symbol = trade_plan['symbol'].replace('/', '_')
        timeframe = trade_plan['timeframe']
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{symbol}_{timeframe}_{timestamp}_plan.json"
        
        # Save the trade plan
        plan_path = os.path.join(self.data_dir, 'trade_plans', filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(plan_path), exist_ok=True)
        
        # Save as JSON
        with open(plan_path, 'w') as f:
            json.dump(trade_plan, f, indent=2)
        
        logger.info(f"Trade plan saved to {plan_path}")
        return plan_path


if __name__ == "__main__":
    # Setup basic logging for standalone testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and test Smart Trade Planner with dummy data
    planner = SmartTradePlanner()
    
    # Create dummy OHLCV data
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
    df = pd.DataFrame({
        'open': np.random.normal(100, 5, 100),
        'high': np.random.normal(105, 5, 100),
        'low': np.random.normal(95, 5, 100),
        'close': np.random.normal(100, 5, 100),
        'volume': np.random.normal(1000000, 200000, 100)
    }, index=dates)
    
    # Plan a trade
    trade_plan = planner.plan_trade(
        df=df,
        entry_price=100.0,
        symbol='BTC/USDT',
        timeframe='1h',
        position_type='long'
    )
    
    # Print formatted trade plan
    print(planner.format_trade_plan_message(trade_plan))
