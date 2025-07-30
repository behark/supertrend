#!/usr/bin/env python
"""
Auto-Fallback Mode
-----------------
Implements intelligent fallback logic when preferred trading pairs have no valid signals:
1. Identifies alternative tokens under $1 with high-quality setups
2. Ranks alternatives by probability, recent performance, and volatility
3. Maintains a dynamic whitelist of acceptable fallback pairs
"""
import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from collections import defaultdict
import ccxt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AutoFallback:
    """Smart fallback to alternative pairs when preferred symbols lack signals"""
    
    def __init__(self, config=None, data_dir='data'):
        """Initialize auto fallback system
        
        Args:
            config (dict): Configuration parameters
            data_dir (str): Directory for fallback data
        """
        self.config = config or {}
        self.data_dir = data_dir
        self.fallback_file = os.path.join(data_dir, 'fallback_pairs.json')
        
        # Default configuration
        self.config.setdefault('preferred_symbols', ["XRP/USDT", "ADA/USDT", "DOGE/USDT", "TRX/USDT", "XLM/USDT"])
        self.config.setdefault('max_price', 1.0)
        self.config.setdefault('min_probability', 0.9)
        self.config.setdefault('max_fallback_pairs', 10)
        self.config.setdefault('fallback_update_interval', 24)  # hours
        
        # Fallback data
        self.fallback_pairs = {
            'last_update': datetime.now().isoformat(),
            'whitelist': [],
            'blacklist': [],
            'performance': {}
        }
        
        # Load existing data if available
        self._load_fallback_data()
    
    def _load_fallback_data(self):
        """Load fallback data from disk"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Load fallback data
            if os.path.exists(self.fallback_file):
                with open(self.fallback_file, 'r') as f:
                    self.fallback_pairs = json.load(f)
                logger.info(f"Loaded fallback data from {self.fallback_file}")
                
        except Exception as e:
            logger.error(f"Error loading fallback data: {str(e)}")
    
    def _save_fallback_data(self):
        """Save fallback data to disk"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Update timestamp
            self.fallback_pairs['last_update'] = datetime.now().isoformat()
            
            # Save fallback data
            with open(self.fallback_file, 'w') as f:
                json.dump(self.fallback_pairs, f, indent=2)
            
            logger.info(f"Saved fallback data to {self.fallback_file}")
                
        except Exception as e:
            logger.error(f"Error saving fallback data: {str(e)}")
    
    def update_fallback_whitelist(self, exchange_id='bybit'):
        """Update the fallback whitelist with new candidates
        
        Args:
            exchange_id (str): Exchange ID to fetch market data from
        
        Returns:
            list: Updated whitelist of fallback pairs
        """
        try:
            # Check if update is needed
            if self.fallback_pairs.get('last_update'):
                last_update = datetime.fromisoformat(self.fallback_pairs['last_update'])
                update_interval = timedelta(hours=self.config['fallback_update_interval'])
                
                if datetime.now() - last_update < update_interval:
                    logger.info("Fallback whitelist is up-to-date, skipping update")
                    return self.fallback_pairs['whitelist']
            
            logger.info(f"Updating fallback whitelist for {exchange_id}")
            
            # Initialize exchange
            exchange = getattr(ccxt, exchange_id)({
                'enableRateLimit': True
            })
            
            # Get all markets
            markets = exchange.load_markets()
            
            # Filter for linear perpetual futures with USDT
            usdt_linear_pairs = []
            preferred_symbols = self.config['preferred_symbols']
            
            for symbol, market in markets.items():
                # Check if linear perpetual with USDT
                if symbol.endswith(':USDT') and market.get('linear'):
                    base_symbol = symbol.split(':')[0]
                    
                    # Skip if in preferred symbols
                    if f"{base_symbol}/USDT" in preferred_symbols:
                        continue
                    
                    # Skip if in blacklist
                    if symbol in self.fallback_pairs['blacklist']:
                        continue
                    
                    # Add to candidates
                    usdt_linear_pairs.append({
                        'symbol': symbol,
                        'base': base_symbol,
                        'market': market
                    })
            
            logger.info(f"Found {len(usdt_linear_pairs)} potential fallback pairs")
            
            # Filter by price and get additional data
            fallback_candidates = []
            for pair in usdt_linear_pairs:
                try:
                    # Get ticker
                    ticker = exchange.fetch_ticker(pair['symbol'])
                    price = ticker['last']
                    
                    # Skip if price too high
                    if price > self.config['max_price']:
                        continue
                    
                    # Get 24h stats
                    volume_usd = ticker['quoteVolume']
                    change_24h = ticker['percentage']
                    
                    # Calculate volatility score (simple version)
                    volatility = abs(change_24h) / 100
                    
                    # Skip very low volume pairs (may be illiquid)
                    if volume_usd < 100000:  # $100k daily volume minimum
                        continue
                    
                    # Add to candidates with metrics
                    fallback_candidates.append({
                        'symbol': pair['symbol'],
                        'base': pair['base'],
                        'price': price,
                        'volume_usd': volume_usd,
                        'change_24h': change_24h,
                        'volatility': volatility,
                        'score': 0  # Will be calculated next
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing {pair['symbol']}: {str(e)}")
            
            logger.info(f"Found {len(fallback_candidates)} valid fallback candidates")
            
            # Calculate score for each candidate
            for candidate in fallback_candidates:
                # Base score on volume (higher is better)
                volume_score = min(candidate['volume_usd'] / 10000000, 1.0)  # Cap at 10M
                
                # Volatility score (moderate volatility is good)
                volatility_score = 0
                vol = candidate['volatility']
                if 0.01 <= vol <= 0.05:  # 1-5% daily change is ideal
                    volatility_score = 1.0
                elif vol <= 0.1:  # Up to 10% is still good
                    volatility_score = 0.8
                elif vol <= 0.2:  # Up to 20% is acceptable
                    volatility_score = 0.5
                else:  # Too volatile
                    volatility_score = 0.2
                
                # Performance score (if we have data)
                performance_score = 0
                if candidate['symbol'] in self.fallback_pairs['performance']:
                    perf = self.fallback_pairs['performance'][candidate['symbol']]
                    win_rate = perf.get('win_rate', 0)
                    performance_score = win_rate
                
                # Calculate final score (weighted)
                candidate['score'] = (
                    volume_score * 0.4 +
                    volatility_score * 0.4 +
                    performance_score * 0.2
                )
            
            # Sort by score
            fallback_candidates.sort(key=lambda x: x['score'], reverse=True)
            
            # Take top candidates
            top_candidates = fallback_candidates[:self.config['max_fallback_pairs']]
            
            # Update whitelist
            self.fallback_pairs['whitelist'] = [c['symbol'] for c in top_candidates]
            
            # Save to disk
            self._save_fallback_data()
            
            logger.info(f"Updated fallback whitelist with {len(self.fallback_pairs['whitelist'])} pairs")
            return self.fallback_pairs['whitelist']
            
        except Exception as e:
            logger.error(f"Error updating fallback whitelist: {str(e)}")
            return self.fallback_pairs['whitelist']
    
    def update_pair_performance(self, symbol, result):
        """Update performance metrics for a fallback pair
        
        Args:
            symbol (str): Symbol of the pair
            result (bool): Whether the trade was successful
        """
        try:
            # Initialize performance entry if needed
            if symbol not in self.fallback_pairs['performance']:
                self.fallback_pairs['performance'][symbol] = {
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0
                }
            
            # Update metrics
            perf = self.fallback_pairs['performance'][symbol]
            perf['trades'] += 1
            if result:
                perf['wins'] += 1
            else:
                perf['losses'] += 1
            
            # Calculate win rate
            perf['win_rate'] = perf['wins'] / perf['trades'] if perf['trades'] > 0 else 0
            
            # Save to disk
            self._save_fallback_data()
            
            logger.info(f"Updated performance for {symbol}: {perf['win_rate']:.2f} win rate")
            
        except Exception as e:
            logger.error(f"Error updating pair performance: {str(e)}")
    
    def get_fallback_signal(self, signals):
        """Get the best fallback signal from available signals
        
        Args:
            signals (list): List of trading signals
            
        Returns:
            dict: Best fallback signal or None
        """
        try:
            # Check if we need to update the whitelist
            if not self.fallback_pairs['whitelist']:
                self.update_fallback_whitelist()
            
            # Filter signals by whitelist
            whitelist_signals = []
            for signal in signals:
                # Convert signal symbol to linear format if needed
                symbol = signal['symbol']
                if '/' in symbol:
                    base = symbol.split('/')[0]
                    linear_symbol = f"{base}:USDT"
                else:
                    linear_symbol = symbol
                
                # Check if in whitelist
                if linear_symbol in self.fallback_pairs['whitelist']:
                    # Check probability
                    if signal['probability'] >= self.config['min_probability']:
                        whitelist_signals.append(signal)
            
            # No valid signals
            if not whitelist_signals:
                return None
            
            # Sort by probability (highest first)
            whitelist_signals.sort(key=lambda x: x['probability'], reverse=True)
            
            # Get best signal
            best_signal = whitelist_signals[0]
            logger.info(f"Selected fallback signal: {best_signal['symbol']} with {best_signal['probability']:.2f} probability")
            
            return best_signal
            
        except Exception as e:
            logger.error(f"Error getting fallback signal: {str(e)}")
            return None
    
    def add_to_blacklist(self, symbol, reason):
        """Add a symbol to the blacklist
        
        Args:
            symbol (str): Symbol to blacklist
            reason (str): Reason for blacklisting
        """
        try:
            # Add to blacklist if not already there
            if symbol not in self.fallback_pairs['blacklist']:
                self.fallback_pairs['blacklist'].append(symbol)
                logger.info(f"Added {symbol} to blacklist: {reason}")
                
                # Remove from whitelist if present
                if symbol in self.fallback_pairs['whitelist']:
                    self.fallback_pairs['whitelist'].remove(symbol)
                
                # Save to disk
                self._save_fallback_data()
                
        except Exception as e:
            logger.error(f"Error adding to blacklist: {str(e)}")
    
    def remove_from_blacklist(self, symbol):
        """Remove a symbol from the blacklist
        
        Args:
            symbol (str): Symbol to remove from blacklist
        """
        try:
            # Remove from blacklist if present
            if symbol in self.fallback_pairs['blacklist']:
                self.fallback_pairs['blacklist'].remove(symbol)
                logger.info(f"Removed {symbol} from blacklist")
                
                # Save to disk
                self._save_fallback_data()
                
        except Exception as e:
            logger.error(f"Error removing from blacklist: {str(e)}")

# Example usage
if __name__ == "__main__":
    # Initialize auto fallback
    fallback = AutoFallback()
    
    # Update whitelist
    whitelist = fallback.update_fallback_whitelist()
    print(f"Whitelist: {whitelist}")
    
    # Example signals
    example_signals = [
        {
            'symbol': 'XLM:USDT',
            'probability': 0.95,
            'entry_price': 0.12
        },
        {
            'symbol': 'JASMY:USDT',  # Example fallback pair
            'probability': 0.97,
            'entry_price': 0.01
        }
    ]
    
    # Get fallback signal
    fallback_signal = fallback.get_fallback_signal(example_signals)
    if fallback_signal:
        print(f"Best fallback signal: {fallback_signal['symbol']}")
    else:
        print("No fallback signal found")
