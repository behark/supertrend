#!/usr/bin/env python
"""
Bybit Minimum Order Size Verification
-------------------------------------
This script verifies Bybit minimum order sizes for all preferred pairs
and confirms that Bidget's trading setup can execute orders with the
available balance and 20x leverage.
"""
import os
import sys
import json
import time
import logging
import ccxt
from decimal import Decimal, ROUND_DOWN
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
if os.path.exists('.env_bybit'):
    load_dotenv('.env_bybit')

# Import local modules
sys.path.insert(0, '.')
try:
    from config import (
        SYMBOLS_TO_SCAN,
        LEVERAGE,
        BALANCE_PERCENTAGE,
        MAX_COIN_PRICE
    )
except ImportError:
    # Default values if import fails
    SYMBOLS_TO_SCAN = ["XRP/USDT", "ADA/USDT", "DOGE/USDT", "TRX/USDT", "XLM/USDT"]
    LEVERAGE = 20
    BALANCE_PERCENTAGE = 0.3
    MAX_COIN_PRICE = 1.0

class BybitMinimumVerifier:
    """Verify Bybit minimums for Bidget configuration"""
    
    def __init__(self):
        """Initialize the verifier"""
        self.bybit = self._initialize_bybit()
        self.current_prices = {}
        self.success_count = 0
        self.fail_count = 0
        self.verification_results = {}
        
    def _initialize_bybit(self):
        """Initialize Bybit exchange with API credentials"""
        try:
            # Get API credentials
            api_key = os.getenv("BYBIT_API_KEY")
            api_secret = os.getenv("BYBIT_SECRET_KEY")
            
            if not api_key or not api_secret:
                logger.error("Missing Bybit API credentials. Please check .env or .env_bybit")
                sys.exit(1)
            
            # Initialize exchange
            bybit = ccxt.bybit({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'adjustForTimeDifference': True,
                    'recvWindow': 60000
                },
                'timeout': 30000
            })
            
            # Synchronize time
            bybit.nonce = lambda: int(time.time() * 1000) - 1000
            return bybit
            
        except Exception as e:
            logger.error(f"Failed to initialize Bybit: {e}")
            sys.exit(1)
    
    def _get_account_balance(self):
        """Get account balance from Bybit"""
        try:
            # Fetch balance
            balance = self.bybit.fetch_balance()
            usdt_balance = float(balance.get('USDT', {}).get('free', 0))
            
            if not usdt_balance:
                # Try to get from unified wallet
                total_equity = float(balance.get('total', {}).get('USDT', 0))
                if total_equity:
                    usdt_balance = total_equity
            
            logger.info(f"Available USDT balance: {usdt_balance}")
            return usdt_balance
            
        except Exception as e:
            logger.error(f"Failed to fetch balance: {e}")
            return 0.0
    
    def _fetch_current_prices(self):
        """Fetch current prices for all symbols"""
        symbols = [s.replace('/', '') for s in SYMBOLS_TO_SCAN]
        
        for symbol in symbols:
            try:
                # Fetch ticker for linear perpetual
                ticker = self.bybit.fetch_ticker(f"{symbol}:USDT")
                price = ticker['last']
                self.current_prices[symbol] = price
                logger.info(f"Current price for {symbol}: ${price}")
            except Exception as e:
                logger.warning(f"Failed to fetch price for {symbol}: {e}")
    
    def _get_market_info(self, symbol):
        """Get market info for a symbol"""
        try:
            markets = self.bybit.load_markets()
            linear_symbol = f"{symbol}:USDT"  # Format for USDT perpetual
            
            if linear_symbol in markets:
                return markets[linear_symbol]
            else:
                logger.warning(f"Market {linear_symbol} not found")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get market info: {e}")
            return None
    
    def _calculate_minimum_order(self, market, balance):
        """Calculate minimum order information"""
        try:
            # Extract market limits
            limits = market.get('limits', {})
            min_amount = float(limits.get('amount', {}).get('min', 0))
            min_cost = float(limits.get('cost', {}).get('min', 0))
            
            # Get precisions
            precision = market.get('precision', {})
            amount_precision = precision.get('amount', 8)
            price_precision = precision.get('price', 8)
            
            # Calculate order amount with leverage
            available_amount = balance * BALANCE_PERCENTAGE
            leveraged_amount = available_amount * LEVERAGE
            
            # Calculate minimum notional
            if min_cost <= 0:
                min_cost = 5.0  # Default minimum for Bybit
            
            return {
                'min_amount': min_amount,
                'min_cost': min_cost,
                'amount_precision': amount_precision,
                'price_precision': price_precision,
                'available_amount': available_amount,
                'leveraged_amount': leveraged_amount
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate minimum order: {e}")
            return {
                'min_amount': 0,
                'min_cost': 0,
                'amount_precision': 8,
                'price_precision': 8,
                'available_amount': 0,
                'leveraged_amount': 0
            }
    
    def verify_symbol(self, symbol, balance):
        """Verify if a symbol can be traded with current settings"""
        # Get market info
        market = self._get_market_info(symbol)
        if not market:
            return False, f"Market {symbol}:USDT not found on Bybit"
        
        # Get symbol price
        price = self.current_prices.get(symbol, 0)
        if not price:
            return False, f"Price for {symbol} could not be fetched"
        
        # Check if price is below threshold
        if price > MAX_COIN_PRICE:
            return False, f"{symbol} price (${price}) exceeds maximum threshold (${MAX_COIN_PRICE})"
        
        # Get minimum order details
        min_details = self._calculate_minimum_order(market, balance)
        
        # Calculate required position size in units of the base currency
        position_size_in_usdt = min_details['available_amount']
        position_size_leveraged = min_details['leveraged_amount']
        position_size_in_units = position_size_leveraged / price
        
        # Round down to precision
        position_size_in_units = float(Decimal(str(position_size_in_units)).quantize(
            Decimal('0.' + '0' * min_details['amount_precision']), rounding=ROUND_DOWN
        ))
        
        # Calculate order value
        order_value = position_size_in_units * price
        
        # Check if order meets minimums
        meets_min_amount = position_size_in_units >= min_details['min_amount']
        meets_min_cost = order_value >= min_details['min_cost']
        
        # Store results for reporting
        self.verification_results[symbol] = {
            'price': price,
            'position_size_in_usdt': position_size_in_usdt,
            'position_size_leveraged': position_size_leveraged,
            'position_size_in_units': position_size_in_units,
            'order_value': order_value,
            'min_amount': min_details['min_amount'],
            'min_cost': min_details['min_cost'],
            'meets_min_amount': meets_min_amount,
            'meets_min_cost': meets_min_cost,
            'can_trade': meets_min_amount and meets_min_cost
        }
        
        # Determine if tradable
        if meets_min_amount and meets_min_cost:
            return True, f"{symbol} can be traded with current settings"
        else:
            if not meets_min_amount:
                return False, f"{symbol} order size ({position_size_in_units}) below minimum ({min_details['min_amount']})"
            else:
                return False, f"{symbol} order value (${order_value}) below minimum (${min_details['min_cost']})"
    
    def run_verification(self):
        """Run verification for all symbols"""
        print("\n" + "="*80)
        print(" BYBIT MINIMUM ORDER SIZE VERIFICATION")
        print("="*80)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Configuration: {LEVERAGE}x leverage, {int(BALANCE_PERCENTAGE*100)}% balance per trade")
        print("="*80)
        
        # Get account balance
        balance = self._get_account_balance()
        if balance <= 0:
            print("❌ No balance available. Please check your Bybit account.")
            return
        
        print(f"Available balance: {balance} USDT")
        print(f"Amount per trade: {balance * BALANCE_PERCENTAGE:.2f} USDT")
        print(f"Leveraged amount: {balance * BALANCE_PERCENTAGE * LEVERAGE:.2f} USDT")
        
        # Fetch current prices
        self._fetch_current_prices()
        
        print("\nVerifying minimum order sizes for preferred pairs:")
        print("-" * 80)
        print(f"{'Symbol':<10} | {'Price':>10} | {'Min Cost':>10} | {'Order Value':>12} | {'Status':<10}")
        print("-" * 80)
        
        # Verify each symbol
        for symbol_with_slash in SYMBOLS_TO_SCAN:
            symbol = symbol_with_slash.replace('/', '')
            success, message = self.verify_symbol(symbol, balance)
            
            if success:
                self.success_count += 1
            else:
                self.fail_count += 1
            
            # Get data for display
            if symbol in self.verification_results:
                data = self.verification_results[symbol]
                status = "✅ VALID" if data['can_trade'] else "❌ INVALID"
                print(f"{symbol:<10} | ${data['price']:<9.4f} | ${data['min_cost']:<9.2f} | ${data['order_value']:<11.2f} | {status}")
        
        # Print summary
        print("\n" + "="*80)
        print(f"VERIFICATION SUMMARY: {self.success_count} valid, {self.fail_count} invalid")
        print("="*80)
        
        # Print detailed results
        print("\nDetailed Results:")
        for symbol, data in self.verification_results.items():
            print(f"\n{symbol}:")
            print(f"  Price: ${data['price']:.4f}")
            print(f"  Position Size (USDT): {data['position_size_in_usdt']:.2f} USDT")
            print(f"  Position Size (Leveraged): {data['position_size_leveraged']:.2f} USDT")
            print(f"  Position Size (Units): {data['position_size_in_units']}")
            print(f"  Order Value: ${data['order_value']:.2f}")
            print(f"  Minimum Amount: {data['min_amount']}")
            print(f"  Minimum Cost: ${data['min_cost']:.2f}")
            print(f"  Can Trade: {'Yes' if data['can_trade'] else 'No'}")
            if not data['can_trade']:
                if not data['meets_min_amount']:
                    print(f"  Reason: Order size too small")
                elif not data['meets_min_cost']:
                    print(f"  Reason: Order value too small")
        
        # Generate recommendations if needed
        if self.fail_count > 0:
            print("\n" + "="*80)
            print(" RECOMMENDATIONS")
            print("="*80)
            
            for symbol, data in self.verification_results.items():
                if not data['can_trade']:
                    min_balance_needed = 0
                    
                    if not data['meets_min_cost']:
                        # Calculate minimum balance needed
                        min_balance_needed = (data['min_cost'] / LEVERAGE) / BALANCE_PERCENTAGE
                        print(f"For {symbol}: Need minimum balance of {min_balance_needed:.2f} USDT")
                        
                        # Suggest leverage adjustment
                        adjusted_leverage = min(100, int(LEVERAGE * 1.5))  # Increase leverage but cap at 100x
                        adjusted_balance = (data['min_cost'] / adjusted_leverage) / BALANCE_PERCENTAGE
                        if adjusted_balance < balance:
                            print(f"  Option: Increase leverage to {adjusted_leverage}x")
                    
                    # Suggest alternative pairs
                    if data['price'] < MAX_COIN_PRICE * 0.5:  # If price is quite low
                        print(f"  Option: Increase allocation to {int(BALANCE_PERCENTAGE*100*1.5)}% for {symbol}")

if __name__ == "__main__":
    try:
        verifier = BybitMinimumVerifier()
        verifier.run_verification()
    except KeyboardInterrupt:
        print("\nVerification interrupted by user")
    except Exception as e:
        print(f"\nError: {e}")
