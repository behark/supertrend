"""
Market data module for fetching and processing trading data
"""

import os
import logging
import pandas as pd
import numpy as np
import ccxt
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class MarketData:
    """
    Handles all market data fetching and processing
    """
    
    def __init__(self, exchange_id: str = 'binance', test_mode: bool = False):
        """
        Initialize the market data handler
        
        Args:
            exchange_id: The exchange ID to use (default: binance)
            test_mode: If True, use test data instead of real API (default: False)
        """
        self.exchange_id = exchange_id
        self.test_mode = test_mode
        self.exchange = self._initialize_exchange()
        self.markets = self._get_markets_from_config()
        self.timeframes = self._get_timeframes_from_config()
        logger.info(f"Initialized market data handler with {len(self.markets)} markets and {len(self.timeframes)} timeframes in {'test mode' if test_mode else 'live mode'}")

    def _initialize_exchange(self) -> Optional[ccxt.Exchange]:
        """
        Initialize the exchange API client
        
        Returns:
            ccxt.Exchange: The exchange API client or None in test mode
        """
        if self.test_mode:
            logger.info(f"Running in test mode, using simulated exchange data")
            return None
            
        try:
            # Create exchange instance
            exchange_class = getattr(ccxt, self.exchange_id)
            exchange = exchange_class({
                'apiKey': os.getenv('BIDGET_API_KEY', ''),
                'secret': os.getenv('BIDGET_API_SECRET', ''),
                'timeout': 30000,
                'enableRateLimit': True,
            })
            
            # Load markets
            exchange.load_markets()
            logger.info(f"Successfully connected to {self.exchange_id} exchange")
            return exchange
            
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            if os.getenv('ALLOW_TEST_FALLBACK', 'true').lower() == 'true':
                logger.warning("Falling back to test mode due to exchange initialization failure")
                return None
            else:
                raise
    
    def _get_markets_from_config(self) -> List[str]:
        """
        Get the list of markets to scan from the configuration
        
        Returns:
            List[str]: List of market symbols
        """
        markets_str = os.getenv('FUTURES_MARKETS', 'BTC/USDT,ETH/USDT')
        return markets_str.split(',')
    
    def _get_timeframes_from_config(self) -> List[str]:
        """
        Get the list of timeframes to scan from the configuration
        
        Returns:
            List[str]: List of timeframe strings
        """
        timeframes_str = os.getenv('TIMEFRAMES', '15m,1h,4h')
        return timeframes_str.split(',')
    
    def fetch_ohlcv_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Fetch OHLCV (Open, High, Low, Close, Volume) data for a symbol
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for the data (e.g., '1h', '4h', '1d')
            limit: Number of candles to fetch
            
        Returns:
            pd.DataFrame: DataFrame with OHLCV data
        """
        if self.test_mode or self.exchange is None:
            # Generate synthetic data for testing
            return self._generate_test_ohlcv(symbol, timeframe, limit)
            
        try:
            # Fetch OHLCV data
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            
            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching {timeframe} data for {symbol}: {e}")
            return pd.DataFrame()
            
    def _generate_test_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Generate synthetic OHLCV data for testing
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe for the data (e.g., '1h', '4h', '1d')
            limit: Number of candles to generate
            
        Returns:
            pd.DataFrame: DataFrame with synthetic OHLCV data
        """
        logger.info(f"Generating synthetic data for {symbol} ({timeframe})")
        
        # Map timeframe to minutes
        tf_map = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        minutes = tf_map.get(timeframe, 60)  # Default to 1h if timeframe not recognized
        
        # Set base price based on symbol
        if 'BTC' in symbol:
            base_price = 50000
            volatility = 0.05
        elif 'ETH' in symbol:
            base_price = 3000
            volatility = 0.06
        else:
            base_price = 100
            volatility = 0.08
        
        # Generate timestamps
        end_time = pd.Timestamp.now()
        timestamps = [end_time - pd.Timedelta(minutes=minutes*i) for i in range(limit)][::-1]
        
        # Generate prices with random walk
        prices = []
        current_price = base_price
        
        for i in range(limit):
            # Random price change with some trend and volatility
            change_percent = np.random.normal(0, volatility)
            current_price = current_price * (1 + change_percent/100)
            
            # Add some cyclical patterns
            cycle_component = np.sin(i/20) * base_price * 0.02
            current_price += cycle_component
            
            # Generate OHLC values around the current price
            candle_volatility = current_price * volatility * 0.1
            open_price = current_price
            close_price = current_price * (1 + np.random.normal(0, 0.01))
            high_price = max(open_price, close_price) + abs(np.random.normal(0, candle_volatility))
            low_price = min(open_price, close_price) - abs(np.random.normal(0, candle_volatility))
            
            # Generate volume
            volume = abs(np.random.normal(base_price * 10, base_price * 5))
            
            prices.append([timestamps[i], open_price, high_price, low_price, close_price, volume])
        
        # Create DataFrame
        df = pd.DataFrame(prices, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        return df
    
    def scan_all_markets(self) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Scan all configured markets and timeframes
        
        Returns:
            Dict[str, Dict[str, pd.DataFrame]]: Nested dict of market data by symbol and timeframe
        """
        all_data = {}
        max_price = 1.0
        if os.getenv('LOW_PRICE_FILTER', 'true').lower() == 'true':
            logger.info(f"Filtering for cryptos under ${max_price}")
            
            # Get current prices
            markets = self.markets[:]
            for market in markets[:]:
                try:
                    ticker = self.exchange.fetch_ticker(market)
                    price = ticker.get('last')
                    
                    if price is not None and price > max_price:
                        markets.remove(market)
                        logger.info(f"Filtered out high-priced crypto: {market} (${price:.3f})")
                    elif price is None:
                        logger.warning(f"Could not get price for {market}, keeping it in the scan list")
                except Exception as e:
                    logger.error(f"Error checking price for {market}: {e}")
                    # Keep the market in the list, we'll handle errors during data fetching
        else:
            markets = self.markets
        
        for symbol in markets:
            all_data[symbol] = {}
            
            for timeframe in self.timeframes:
                try:
                    df = self.fetch_ohlcv_data(symbol, timeframe)
                    
                    if not df.empty:
                        all_data[symbol][timeframe] = df
                        logger.debug(f"Successfully fetched {timeframe} data for {symbol}")
                    else:
                        logger.warning(f"Empty data returned for {symbol} on {timeframe}")
                        
                except Exception as e:
                    logger.error(f"Error scanning {symbol} on {timeframe}: {e}")
        
        return all_data
