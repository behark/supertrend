#!/usr/bin/env python
"""
Balance-Based Scaling
-------------------
Dynamically adjusts position sizes based on account balance fluctuations:
1. Scales lot sizes within the 30% balance cap
2. Adapts to growing/shrinking balance for optimal capital efficiency 
3. Implements progressive sizing for winning/losing streaks
"""
import os
import sys
import json
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BalanceScaling:
    """Dynamic position sizing based on balance fluctuations"""
    
    def __init__(self, config=None, data_dir='data'):
        """Initialize the balance scaling system
        
        Args:
            config (dict): Configuration parameters
            data_dir (str): Directory for balance data
        """
        self.config = config or {}
        self.data_dir = data_dir
        self.balance_file = os.path.join(data_dir, 'balance_scaling.json')
        
        # Default configuration
        self.config.setdefault('balance_percentage', 0.3)  # 30% of balance
        self.config.setdefault('leverage', 20)  # 20x leverage
        self.config.setdefault('min_balance_multiplier', 0.8)  # 80% of normal size on drawdown
        self.config.setdefault('max_balance_multiplier', 1.2)  # 120% of normal size on winning streak
        self.config.setdefault('winning_streak_bonus', 0.05)  # +5% per win in a streak
        self.config.setdefault('losing_streak_reduction', 0.05)  # -5% per loss in a streak
        self.config.setdefault('max_streak_adjustment', 0.2)  # Cap adjustment at ±20%
        self.config.setdefault('risk_adjustment_threshold', 0.1)  # 10% balance change triggers adjustment
        
        # Balance data
        self.balance_data = {
            'last_update': datetime.now().isoformat(),
            'initial_balance': 0,
            'current_balance': 0,
            'highest_balance': 0,
            'lowest_balance': float('inf'),
            'balance_history': [],
            'winning_streak': 0,
            'losing_streak': 0,
            'current_multiplier': 1.0,
            'trades_history': []
        }
        
        # Load existing data if available
        self._load_balance_data()
    
    def _load_balance_data(self):
        """Load balance data from disk"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Load balance data
            if os.path.exists(self.balance_file):
                with open(self.balance_file, 'r') as f:
                    self.balance_data = json.load(f)
                logger.info(f"Loaded balance data from {self.balance_file}")
                
        except Exception as e:
            logger.error(f"Error loading balance data: {str(e)}")
    
    def _save_balance_data(self):
        """Save balance data to disk"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Update timestamp
            self.balance_data['last_update'] = datetime.now().isoformat()
            
            # Save balance data
            with open(self.balance_file, 'w') as f:
                json.dump(self.balance_data, f, indent=2)
            
            logger.info(f"Saved balance data to {self.balance_file}")
                
        except Exception as e:
            logger.error(f"Error saving balance data: {str(e)}")
    
    def update_balance(self, balance):
        """Update the current balance
        
        Args:
            balance (float): Current account balance
        
        Returns:
            float: Current multiplier for position sizing
        """
        try:
            # Set initial balance if this is the first update
            if self.balance_data['initial_balance'] == 0:
                self.balance_data['initial_balance'] = balance
            
            # Update balance data
            self.balance_data['current_balance'] = balance
            
            # Update highest/lowest
            if balance > self.balance_data['highest_balance']:
                self.balance_data['highest_balance'] = balance
            
            if balance < self.balance_data['lowest_balance']:
                self.balance_data['lowest_balance'] = balance
            
            # Add to balance history
            self.balance_data['balance_history'].append({
                'timestamp': datetime.now().isoformat(),
                'balance': balance
            })
            
            # Trim history if too long
            if len(self.balance_data['balance_history']) > 100:
                self.balance_data['balance_history'] = self.balance_data['balance_history'][-100:]
            
            # Recalculate current multiplier based on balance trend
            self._recalculate_multiplier()
            
            # Save data
            self._save_balance_data()
            
            logger.info(f"Updated balance to {balance} USDT (multiplier: {self.balance_data['current_multiplier']:.2f})")
            return self.balance_data['current_multiplier']
            
        except Exception as e:
            logger.error(f"Error updating balance: {str(e)}")
            return 1.0
    
    def _recalculate_multiplier(self):
        """Recalculate position sizing multiplier based on balance trends"""
        try:
            # Skip if not enough data
            if len(self.balance_data['balance_history']) < 5:
                return
            
            # Calculate balance change percentage
            initial = self.balance_data['initial_balance']
            current = self.balance_data['current_balance']
            highest = self.balance_data['highest_balance']
            
            if initial == 0:
                return
            
            # Get percent from all-time high
            percent_from_ath = (current / highest) if highest > 0 else 1.0
            
            # Calculate balance trend
            if current > initial:
                # Account growing, potentially increase size
                growth_percent = current / initial - 1
                
                # Scale multiplier based on growth (cap at max_balance_multiplier)
                trend_multiplier = min(
                    1.0 + (growth_percent / 2),  # Half of growth percentage as bonus
                    self.config['max_balance_multiplier']
                )
                
                # Adjust based on how close we are to ATH
                if percent_from_ath < 0.9:  # More than 10% down from ATH
                    trend_multiplier *= 0.9  # Reduce sizing
            else:
                # Account shrinking, potentially decrease size
                decline_percent = 1 - current / initial
                
                # Scale multiplier based on decline (floor at min_balance_multiplier)
                trend_multiplier = max(
                    1.0 - decline_percent,
                    self.config['min_balance_multiplier']
                )
            
            # Combine trend multiplier with streak multiplier
            streak_multiplier = self._calculate_streak_multiplier()
            
            # Calculate final multiplier (trend * streak)
            final_multiplier = trend_multiplier * streak_multiplier
            
            # Clamp to limits
            final_multiplier = max(
                min(final_multiplier, self.config['max_balance_multiplier']),
                self.config['min_balance_multiplier']
            )
            
            # Set multiplier
            self.balance_data['current_multiplier'] = final_multiplier
            
        except Exception as e:
            logger.error(f"Error recalculating multiplier: {str(e)}")
    
    def _calculate_streak_multiplier(self):
        """Calculate multiplier adjustment based on winning/losing streaks"""
        try:
            # Get current streaks
            winning_streak = self.balance_data['winning_streak']
            losing_streak = self.balance_data['losing_streak']
            
            # Calculate streak effects
            if winning_streak > 0:
                # Increase size for winning streaks
                streak_adjustment = min(
                    winning_streak * self.config['winning_streak_bonus'],
                    self.config['max_streak_adjustment']
                )
                return 1.0 + streak_adjustment
            elif losing_streak > 0:
                # Decrease size for losing streaks
                streak_adjustment = min(
                    losing_streak * self.config['losing_streak_reduction'],
                    self.config['max_streak_adjustment']
                )
                return 1.0 - streak_adjustment
            else:
                return 1.0
                
        except Exception as e:
            logger.error(f"Error calculating streak multiplier: {str(e)}")
            return 1.0
    
    def update_trade_result(self, trade_id, profit, success=None):
        """Update trade result and adjust streaks
        
        Args:
            trade_id (str): Trade ID
            profit (float): Profit amount (positive or negative)
            success (bool): Whether the trade was successful (if None, determined by profit)
            
        Returns:
            float: Current multiplier for position sizing
        """
        try:
            # Determine success if not provided
            if success is None:
                success = profit > 0
            
            # Update streaks
            if success:
                self.balance_data['winning_streak'] += 1
                self.balance_data['losing_streak'] = 0
            else:
                self.balance_data['losing_streak'] += 1
                self.balance_data['winning_streak'] = 0
            
            # Add to trade history
            self.balance_data['trades_history'].append({
                'trade_id': trade_id,
                'timestamp': datetime.now().isoformat(),
                'profit': profit,
                'success': success
            })
            
            # Trim history if too long
            if len(self.balance_data['trades_history']) > 100:
                self.balance_data['trades_history'] = self.balance_data['trades_history'][-100:]
            
            # Recalculate multiplier
            self._recalculate_multiplier()
            
            # Save data
            self._save_balance_data()
            
            logger.info(f"Updated trade {trade_id} result: {'success' if success else 'failure'} with {profit} profit")
            logger.info(f"Current streaks - Win: {self.balance_data['winning_streak']}, Loss: {self.balance_data['losing_streak']}")
            logger.info(f"Current multiplier: {self.balance_data['current_multiplier']:.2f}")
            
            return self.balance_data['current_multiplier']
            
        except Exception as e:
            logger.error(f"Error updating trade result: {str(e)}")
            return 1.0
    
    def calculate_position_size(self, symbol, entry_price, stop_loss=None, balance=None):
        """Calculate position size based on current scaling factors
        
        Args:
            symbol (str): Trading symbol
            entry_price (float): Entry price
            stop_loss (float): Stop loss price (optional)
            balance (float): Account balance (if None, uses current_balance)
            
        Returns:
            tuple: (position_size_in_quote, position_size_in_base, actual_risk_percentage)
        """
        try:
            # Get current balance
            if balance is None:
                balance = self.balance_data['current_balance']
            
            # If no balance, return zeros
            if balance <= 0:
                return 0, 0, 0
            
            # Calculate base percentage with scaling
            base_percentage = self.config['balance_percentage']
            scaled_percentage = base_percentage * self.balance_data['current_multiplier']
            
            # Cap at maximum percentage
            actual_percentage = min(scaled_percentage, 0.4)  # Hard cap at 40%
            
            # Calculate position size in quote currency (USDT)
            position_size_quote = balance * actual_percentage
            
            # Apply leverage
            leveraged_position = position_size_quote * self.config['leverage']
            
            # Calculate position size in base currency
            position_size_base = leveraged_position / entry_price
            
            # Calculate actual risk percentage
            risk_pct = actual_percentage
            
            # If stop loss provided, calculate risk more precisely
            if stop_loss:
                price_risk = abs(entry_price - stop_loss) / entry_price
                if price_risk > 0:
                    # Adjust position size to respect risk
                    adjusted_position = position_size_base * (actual_percentage / price_risk / self.config['leverage'])
                    
                    # Use smaller of the two calculations to be safe
                    position_size_base = min(position_size_base, adjusted_position)
                    
                    # Recalculate position size in quote currency
                    position_size_quote = position_size_base * entry_price / self.config['leverage']
                    risk_pct = position_size_quote / balance
            
            logger.info(f"Calculated position size for {symbol}: {position_size_base} units ({position_size_quote} USDT)")
            logger.info(f"Risk percentage: {risk_pct*100:.2f}% (multiplier: {self.balance_data['current_multiplier']:.2f})")
            
            return position_size_quote, position_size_base, risk_pct
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0, 0, 0
    
    def get_recommended_parameters(self):
        """Get recommended trading parameters based on current balance trend
        
        Returns:
            dict: Recommended parameters
        """
        try:
            # Get balance trend
            current = self.balance_data['current_balance']
            highest = self.balance_data['highest_balance']
            initial = self.balance_data['initial_balance']
            
            # Skip if not enough data
            if current == 0 or initial == 0:
                return {}
            
            # Calculate balance trend metrics
            growth_pct = (current / initial - 1) * 100 if initial > 0 else 0
            drawdown_pct = (1 - current / highest) * 100 if highest > 0 else 0
            
            # Get streak information
            winning_streak = self.balance_data['winning_streak']
            losing_streak = self.balance_data['losing_streak']
            
            # Base recommendations on current state
            recommendations = {}
            
            # Adjust based on growth
            if growth_pct > 20:  # Strong growth
                recommendations['leverage'] = min(self.config['leverage'] + 2, 25)  # Increase leverage slightly
                recommendations['min_probability'] = 0.88  # Can take slightly more risk
            elif growth_pct < -10:  # Significant decline
                recommendations['leverage'] = max(self.config['leverage'] - 2, 5)  # Reduce leverage
                recommendations['min_probability'] = 0.92  # Be more conservative
            
            # Adjust based on streaks
            if winning_streak >= 5:
                recommendations['max_daily_trades'] = min(20, self.config.get('max_daily_trades', 15) + 5)  # More trades
            elif losing_streak >= 3:
                recommendations['max_daily_trades'] = max(10, self.config.get('max_daily_trades', 15) - 5)  # Fewer trades
                recommendations['min_probability'] = 0.94  # Higher probability threshold
            
            # Add metrics for reference
            recommendations['metrics'] = {
                'growth_pct': growth_pct,
                'drawdown_pct': drawdown_pct,
                'winning_streak': winning_streak,
                'losing_streak': losing_streak,
                'current_multiplier': self.balance_data['current_multiplier']
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommended parameters: {str(e)}")
            return {}

# Example usage
if __name__ == "__main__":
    # Initialize balance scaling
    scaling = BalanceScaling()
    
    # Example balance updates
    print("Starting with 100 USDT")
    scaling.update_balance(100)
    
    print("\nSimulating a winning streak")
    scaling.update_trade_result("trade1", 5, True)
    scaling.update_trade_result("trade2", 7, True)
    scaling.update_trade_result("trade3", 3, True)
    scaling.update_balance(115)
    
    print("\nCalculating position size")
    position_quote, position_base, risk = scaling.calculate_position_size("ADA/USDT", 0.5, 0.45, 115)
    print(f"Position size: {position_base} ADA ({position_quote} USDT)")
    print(f"Risk: {risk*100:.2f}%")
    
    print("\nSimulating a losing streak")
    scaling.update_trade_result("trade4", -10, False)
    scaling.update_trade_result("trade5", -8, False)
    scaling.update_balance(97)
    
    print("\nRecalculating position size")
    position_quote, position_base, risk = scaling.calculate_position_size("ADA/USDT", 0.5, 0.45, 97)
    print(f"Position size: {position_base} ADA ({position_quote} USDT)")
    print(f"Risk: {risk*100:.2f}%")
    
    print("\nGetting recommendations")
    recommendations = scaling.get_recommended_parameters()
    print(f"Recommendations: {recommendations}")
