"""
Trading API Integration Module for Bitget
"""

import os
import logging
import requests
import json
import time
import hmac
import hashlib
import base64
from urllib.parse import urlencode
from typing import Dict, List, Optional, Union
from functools import wraps

logger = logging.getLogger(__name__)

# Global flag to track method calls and prevent duplicate orders
_in_progress_orders = {}
_last_tp_order = None
_last_sl_order = None

def prevent_duplicate_orders(func):
    """Decorator to prevent duplicate TP/SL orders by tracking method calls"""
    @wraps(func)
    def wrapper(self, symbol, *args, **kwargs):
        global _last_tp_order, _last_sl_order
        
        # Determine if this is a TP or SL order
        is_tp = 'take_profit' in func.__name__
        is_sl = 'stop_loss' in func.__name__
        
        # For legacy methods, return the last order of the same type
        if 'bitget' in func.__name__:
            if is_tp and _last_tp_order is not None:
                logger.warning(f"Legacy {func.__name__} called - returning cached TP order")
                return _last_tp_order
            elif is_sl and _last_sl_order is not None:
                logger.warning(f"Legacy {func.__name__} called - returning cached SL order")
                return _last_sl_order
        
        # Generate a unique key for this order
        key = f"{func.__name__}_{symbol}_{time.time()}"
        
        # Check if we're already processing this order
        if key in _in_progress_orders:
            logger.warning(f"Preventing duplicate order for {symbol} in {func.__name__}")
            return _in_progress_orders[key]
            
        try:
            # Mark this order as in progress
            _in_progress_orders[key] = None
            
            # Execute the original function
            result = func(self, symbol, *args, **kwargs)
            
            # Store the result
            _in_progress_orders[key] = result
            
            # For main methods, cache the result
            if 'bitget' not in func.__name__:
                if is_tp:
                    _last_tp_order = result
                elif is_sl:
                    _last_sl_order = result
                    
            return result
        finally:
            # Clean up after a reasonable delay to prevent memory leaks
            # while still protecting against rapid duplicate calls
            def cleanup():
                if key in _in_progress_orders:
                    del _in_progress_orders[key]
            # Schedule cleanup after 5 seconds
            import threading
            threading.Timer(5.0, cleanup).start()
    
    return wrapper


class TradingAPI:
    """
    Trading API client for Bitget exchange
    """

    def _format_symbol_for_bitget(self, symbol: str) -> str:
        """
        BULLETPROOF symbol formatting for Bitget API
        Handles ALL special cases consistently across ALL API calls
        """
        logger.info(f"🔧 SYMBOL FORMATTING: Input symbol: '{symbol}'")
        
        if not symbol:
            logger.info(f"🔧 SYMBOL FORMATTING: Empty symbol, returning as-is")
            return symbol
            
        # Handle already formatted symbols
        if symbol.endswith('_UMCBL'):
            logger.info(f"🔧 SYMBOL FORMATTING: Already formatted, returning: '{symbol}'")
            return symbol
            
        # Extract base currency from trading pair
        if '/' in symbol:
            base_currency = symbol.split('/')[0]
            logger.info(f"🔧 SYMBOL FORMATTING: Extracted base currency from '/': '{base_currency}'")
        else:
            base_currency = symbol.replace('USDT', '').replace('_UMCBL', '')
            logger.info(f"🔧 SYMBOL FORMATTING: Extracted base currency from string: '{base_currency}'")
            
        # Apply ALL special symbol mappings for Bitget
        symbol_mappings = {
            '1000LUNC': 'LUNC',
            '1000SHIB': 'SHIB', 
            '1000PEPE': 'PEPE',
            '1000FLOKI': 'FLOKI',
            '1000BONK': 'BONK',
            '1000XEC': 'XEC',
            '1000SATS': 'SATS',
            'MATIC': 'MATIC',  # Ensure MATIC is properly mapped
            'SC': None  # SC is not supported on Bitget, mark as None
        }
        
        # List of valid symbols on Bitget
        self.valid_bitget_symbols = [
            'BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT', 'SOLUSDT', 'MATICUSDT',
            'DOTUSDT', 'LTCUSDT', 'AVAXUSDT', 'LINKUSDT', 'UNIUSDT', 'ATOMUSDT', 'ETCUSDT',
            'TRXUSDT', 'EOSUSDT', 'FILUSDT', 'XLMUSDT', 'NEARUSDT', 'APEUSDT', 'SANDUSDT',
            'MANAUSDT', 'AAVEUSDT', 'FTMUSDT', 'LUNCUSDT', 'SHIBUSDT', 'PEPEUSDT', 'FLOKIUSDT',
            'BONKUSDT', 'XECUSDT', 'SATSUSDT', 'OPUSDT', 'ARBUSDT', 'SUIUSDT', 'APTUSDT',
            'INJUSDT', 'GMTUSDT', 'AXSUSDT', 'GALAUSDT', 'ICPUSDT', 'LDOUSDT', 'RUNEUSDT',
            'SNXUSDT', 'CHZUSDT', 'GRTUSDT', 'ENJUSDT', 'STXUSDT', 'IMXUSDT', 'CFXUSDT',
            'FETUSDT', 'FLOWUSDT', 'MINAUSDT', 'BNBUSDT', 'BCHUSDT', 'DASHUSDT', 'ZECUSDT'
        ]
        
        # Apply mapping if exists
        if base_currency in symbol_mappings:
            old_base = base_currency
            base_currency = symbol_mappings[base_currency]
            logger.info(f"🔧 SYMBOL FORMATTING: Mapped '{old_base}' -> '{base_currency}'")
        else:
            logger.info(f"🔧 SYMBOL FORMATTING: No mapping needed for '{base_currency}'")
            
        # Check if base currency is explicitly marked as unsupported
        if base_currency is None:
            logger.error(f"🔴 SYMBOL VALIDATION FAILED: '{symbol}' is not supported on Bitget")
            return None
            
        # Return properly formatted Bitget futures symbol
        formatted = f"{base_currency}USDT_UMCBL"
        logger.info(f"🔧 SYMBOL FORMATTING: Final result: '{symbol}' -> '{formatted}'")
        return formatted
        
    def is_valid_symbol(self, symbol: str) -> bool:
        """
        Validate if a symbol is supported on Bitget
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            bool: True if symbol is valid, False otherwise
        """
        # Format the symbol first
        formatted_symbol = self._format_symbol_for_bitget(symbol)
        
        # If formatting returned None, symbol is explicitly unsupported
        if formatted_symbol is None:
            logger.error(f"🔴 SYMBOL VALIDATION: '{symbol}' is explicitly marked as unsupported")
            return False
            
        # Extract the base currency for validation
        base_currency = formatted_symbol.replace('USDT_UMCBL', '')
        check_symbol = f"{base_currency}USDT"
        
        # Check if the symbol is in our valid symbols list
        is_valid = check_symbol in self.valid_bitget_symbols
        
        if not is_valid:
            logger.error(f"🔴 SYMBOL VALIDATION: '{symbol}' (formatted as '{formatted_symbol}') is not in the list of valid Bitget symbols")
        else:
            logger.info(f"👍 SYMBOL VALIDATION: '{symbol}' is valid on Bitget")
            
        return is_valid

    def __init__(self):
        """Initialize the Bitget API client"""
        self.api_key = os.getenv('BITGET_API_KEY', '')
        self.api_secret = os.getenv('BITGET_API_SECRET', '')
        self.api_passphrase = os.getenv('BITGET_API_PASSPHRASE', '')
        self.base_url = "https://api.bitget.com"
        self.is_configured = bool(self.api_key and self.api_secret and self.api_passphrase)
        
        # Determine whether to use test mode or not
        self.test_mode = os.getenv('TEST_MODE', 'false').lower() == 'true'
        
        # Set position sizing percentage (25% of available balance)
        self.position_size_percent = float(os.getenv('POSITION_SIZE_PERCENT', '25.0'))

        # Bitget API endpoints
        self.futures_base_url = "https://api.bitget.com/api/mix/v1"
        
        if self.is_configured:
            logger.info("Trading API client initialized with Bitget API")
        else:
            logger.warning("Bitget API not configured - API key, secret, or passphrase missing")
            logger.warning("No API credentials provided - running in test mode only")
            self.test_mode = True  # Force test mode if no credentials are available

    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """
        Generate Bitget API signature

        Args:
            timestamp: Current timestamp in ISO format
            method: HTTP method
            request_path: API endpoint path
            body: Request body as JSON string

        Returns:
            str: Base64 encoded HMAC signature
        """
        message = timestamp + method + request_path + (body if body else '')
        signature = hmac.new(self.api_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
        return base64.b64encode(signature).decode()

    def _make_bitget_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        """
        Make a request to the Bitget API with proper authentication
        """
        if not self.is_configured:
            logger.error("Bitget API not configured")
            return {"error": "API not configured"}

        url = f"{self.base_url}{endpoint}"
        
        # For POST requests, use data in body; for GET requests, use params in URL
        if method.upper() == 'POST' and data:
            # POST request with JSON body
            request_path = endpoint
            body = json.dumps(data, separators=(',', ':'))  # Compact JSON
            query_string = ''
        elif method.upper() == 'GET' and params:
            # GET request with query parameters
            query_string = urlencode(sorted(params.items()))  # Sort for consistency
            url = f"{url}?{query_string}"
            request_path = f"{endpoint}?{query_string}"
            body = ''
        else:
            # No parameters
            request_path = endpoint
            body = ''
            query_string = ''

        # Generate timestamp and signature
        timestamp = str(int(time.time() * 1000))
        signature = self._generate_signature(timestamp, method.upper(), request_path, body)

        # Prepare headers
        headers = {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.api_passphrase,
            "Content-Type": "application/json"
        }

        logger.info(f"Bitget API call: {method} {request_path}")
        logger.debug(f"Headers: {headers}")
        logger.debug(f"Body: {body}")

        try:
            if method.upper() == 'POST':
                response = requests.post(url, headers=headers, data=body, timeout=10)
            else:
                response = requests.get(url, headers=headers, timeout=10)

            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response text: {response.text}")
            
            response_data = response.json()
            
            # Check for API errors
            if response.status_code != 200:
                error_msg = f"Bitget HTTP error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
                
            if response_data.get('code') != '00000':
                error_msg = f"Bitget API error: {response_data.get('msg', 'Unknown error')} (code: {response_data.get('code')})"
                logger.error(error_msg)
                return {"error": error_msg}
                
            return response_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Bitget API request failed: {e}")
            return {"error": str(e)}
        except json.JSONDecodeError as e:
            logger.error(f"Bitget API response not valid JSON: {e}")
            return {"error": f"Invalid JSON response: {e}"}

    # Removed Binance integration code as we're using Bidget API exclusively

    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None, signed: bool = False) -> Dict:
        """
        Make a request to the Bitget API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            params: Query parameters
            data: Request body data
            signed: Whether the request needs signature (always true for Bitget authenticated endpoints)

        Returns:
            Dict: API response
        """
        logger.info(f"LIVE MODE: Making {method} request to {endpoint}")
        
        # Always use Bitget API
        try:
            return self._make_bitget_request(method, endpoint, params, data)
        except Exception as e:
            error_msg = f"Bitget API request failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    # Removed Binance-related parameter mapping as we're using Bidget API exclusively

    def get_account_info(self) -> Dict:
        """
        Get account information

        Returns:
            Dict: Account information
        """
        endpoint = "/api/mix/v1/account/account"
        params = {
            "symbol": "BTCUSDT_UMCBL",  # Any valid symbol works for account info
            "marginCoin": "USDT"  # We're using USDT margin
        }
        
        try:
            response = self._make_request("GET", endpoint, params=params, signed=True)
            
            if 'error' in response:
                return response
                
            # Format response for consistency with our internal API
            account_data = response.get('data', {})
            
            if not account_data:
                logger.error("Error parsing account data: no data returned")
                return {"error": "No account data returned"}
                
            # Extract available balance
            try:
                # Bitget returns available as a string, so convert to float
                available_balance = float(account_data.get('available', 0))
                equity = float(account_data.get('equity', available_balance))
                unrealized_pnl = float(account_data.get('unrealizedPL', 0))
                margin_ratio = float(account_data.get('marginRatio', 0))
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing account data: {e}")
                return {"error": f"Failed to parse account data: {e}"}
                
            return {
                "available_balance": available_balance,
                "equity": equity,
                "margin_ratio": margin_ratio,
                "unrealized_pnl": unrealized_pnl
            }
            
        except Exception as e:
            logger.error(f"Error getting account info: {str(e)}")
            return {"error": str(e)}

    def place_order_direct(self, symbol: str, side: str, quantity: float, price: Optional[float] = None) -> Dict:
        """
        Direct Bitget order placement bypassing holdSide issues
        """
        # Use bulletproof symbol formatting
        formatted_symbol = self._format_symbol_for_bitget(symbol)
        
        # Determine order side and holdSide - ensure holdSide is never empty
        if side.lower() in ['buy', 'long']:
            order_side = "open_long"
            hold_side = "long"
        elif side.lower() in ['sell', 'short']:
            order_side = "open_short" 
            hold_side = "short"
        else:
            # Default to long if unclear
            order_side = "open_long"
            hold_side = "long"
            logger.warning(f"Unclear side '{side}', defaulting to long")
        
        # Order parameters
        params = {
            "symbol": formatted_symbol,
            "marginCoin": "USDT",
            "side": order_side,
            "orderType": "market" if price is None else "limit",
            "size": str(quantity),
            "holdSide": hold_side
        }
        
        if price is not None:
            params["price"] = str(round(price, 5))
        
        logger.info(f"Direct order: {params}")
        
        try:
            response = self._make_request("POST", "/api/mix/v1/order/placeOrder", data=params, signed=True)
            
            if 'error' in response:
                return response
                
            order_data = response.get('data', {})
            return {
                "success": True,
                "orderId": order_data.get('orderId', ''),
                "status": order_data.get('state', ''),
                "filled_qty": float(order_data.get('size', 0)),
                "entry_price": float(order_data.get('price', price if price else 0)),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def place_tp_sl_orders(self, symbol: str, side: str, quantity: float, entry_price: float, take_profit: float, stop_loss: float) -> Dict:
        """
        Place Take Profit and Stop Loss orders for a position
        This creates visible TP/SL orders in Bitget that the user can see
        Uses plan orders (conditional orders) for both TP and SL to ensure proper execution
        """
        formatted_symbol = self._format_symbol_for_bitget(symbol)
        
        # Determine position side for TP/SL orders
        if side.lower() in ['buy', 'long']:
            close_side = "close_long"
            hold_side = "long"
        else:
            close_side = "close_short"
            hold_side = "short"
        
        results = {"take_profit": None, "stop_loss": None}
        
        try:
            # Round prices to 5 decimal places to comply with Bitget requirements
            rounded_tp = round(take_profit, 5)
            rounded_sl = round(stop_loss, 5)
            
            # Get symbol info to ensure price complies with tick size
            try:
                endpoint = f"/api/mix/v1/market/contracts?productType=umcbl"
                contracts_info = self._make_request("GET", endpoint)
                
                if 'error' not in contracts_info and 'data' in contracts_info:
                    # Find the contract info for our symbol
                    for contract in contracts_info.get('data', []):
                        if contract.get('symbol') == formatted_symbol:
                            # Extract tick size from pricePlace field
                            price_place = int(contract.get('pricePlace', 4))
                            tick_size = 10 ** -price_place
                            
                            # Ensure prices are multiples of tick size
                            rounded_tp = round(rounded_tp / tick_size) * tick_size
                            rounded_sl = round(rounded_sl / tick_size) * tick_size
                            
                            logger.info(f"Adjusted prices to tick size {tick_size}: TP={rounded_tp}, SL={rounded_sl}")
                            break
            except Exception as e:
                logger.warning(f"Could not adjust prices to tick size: {str(e)}")
            
            # Place Take Profit Order using plan order (conditional order)
            tp_params = {
                "symbol": formatted_symbol,
                "marginCoin": "USDT",
                "orderType": "market",
                "side": close_side,
                "size": str(round(quantity, 4)),
                "triggerType": "market_price",
                "triggerPrice": str(rounded_tp),
                "planType": "profit",
                "reduceOnly": "true",
                "holdSide": hold_side  # Critical: Specify the position side being held
            }
            
            logger.info(f"Setting take-profit with {close_side} at {rounded_tp} for {formatted_symbol}")
            
            tp_response = self._make_request("POST", "/api/mix/v1/plan/placePlan", data=tp_params, signed=True)
            if 'error' not in tp_response:
                results["take_profit"] = {
                    "success": True,
                    "orderId": tp_response.get('data', {}).get('orderId', ''),
                    "price": rounded_tp
                }
                logger.info(f"✅ Take Profit plan order placed: {rounded_tp} for {symbol}")
            else:
                results["take_profit"] = {"error": tp_response.get('error')}
                logger.error(f"❌ Take Profit plan order failed: {tp_response.get('error')}")
            
            # Place Stop Loss Order using plan order (conditional order)
            sl_params = {
                "symbol": formatted_symbol,
                "marginCoin": "USDT",
                "orderType": "market",
                "side": close_side,
                "size": str(round(quantity, 4)),
                "triggerType": "market_price",
                "triggerPrice": str(rounded_sl),
                "planType": "stop",
                "reduceOnly": "true",
                "holdSide": hold_side  # Critical: Specify the position side being held
            }
            
            logger.info(f"Setting stop-loss with {close_side} at {rounded_sl} for {formatted_symbol}")
            
            sl_response = self._make_request("POST", "/api/mix/v1/plan/placePlan", data=sl_params, signed=True)
            if 'error' not in sl_response:
                results["stop_loss"] = {
                    "success": True,
                    "orderId": sl_response.get('data', {}).get('orderId', ''),
                    "price": rounded_sl
                }
                logger.info(f"✅ Stop Loss plan order placed: {rounded_sl} for {symbol}")
            else:
                results["stop_loss"] = {"error": sl_response.get('error')}
                logger.error(f"❌ Stop Loss plan order failed: {sl_response.get('error')}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error placing TP/SL orders: {str(e)}")
            return {"error": str(e)}
    
    def _set_leverage(self, symbol: str, leverage: int) -> Dict:
        """
        Set leverage for a trading pair on Bitget
        """
        # Use bulletproof symbol formatting
        formatted_symbol = self._format_symbol_for_bitget(symbol)
        
        endpoint = "/api/mix/v1/account/setLeverage"
        data = {
            "symbol": formatted_symbol,
            "marginCoin": "USDT",
            "leverage": str(leverage),
            "holdSide": "long"  # Default to long, will be overridden by actual trades
        }
        
        try:
            response = self._make_request("POST", endpoint, data=data, signed=True)
            if 'error' in response:
                logger.error(f"Failed to set leverage for {formatted_symbol}: {response.get('error')}")
                return response
            
            logger.info(f"Successfully set leverage to {leverage}x for {formatted_symbol}")
            return {"success": True, "leverage": leverage, "symbol": formatted_symbol}
            
        except Exception as e:
            error_msg = f"Error setting leverage for {formatted_symbol}: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def get_position(self, symbol: str) -> Dict:
        """
        Get position information for a symbol
        """
        formatted_symbol = self._format_symbol_for_bitget(symbol)
        
        endpoint = "/api/mix/v1/position/singlePosition"
        params = {
            "symbol": formatted_symbol,
            "marginCoin": "USDT"
        }
        
        try:
            response = self._make_request("GET", endpoint, params=params, signed=True)
            if 'error' in response:
                return response
            
            position_data = response.get('data', {})
            if position_data:
                return {
                    "symbol": formatted_symbol,
                    "size": position_data.get('size', '0'),
                    "side": position_data.get('holdSide', ''),
                    "entry_price": position_data.get('averageOpenPrice', '0'),
                    "unrealized_pnl": position_data.get('unrealizedPL', '0'),
                    "margin": position_data.get('margin', '0')
                }
            else:
                return {"symbol": formatted_symbol, "size": "0", "side": "", "entry_price": "0"}
                
        except Exception as e:
            error_msg = f"Error getting position for {formatted_symbol}: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def place_order(self, symbol: str, side: str, quantity: Optional[float] = None, price: Optional[float] = None, order_type: str = None, position_side: str = None) -> Dict:
        """
        Place an order on the exchange
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            side: Order side ('buy'/'long' or 'sell'/'short')
            quantity: Order quantity (will be calculated automatically if None)
            price: Limit price (if None, a market order will be placed)
            order_type: Optional order type override ('market' or 'limit')
            position_side: Optional explicit position side ('long' or 'short') for hedging mode
            
        Returns:
            Dict: Order execution result
        """
        # Use bulletproof symbol formatting - CRITICAL FIX for 1000LUNCUSDT_UMCBL errors
        formatted_symbol = self._format_symbol_for_bitget(symbol)
        logger.info(f"🔧 PLACE_ORDER: Using formatted symbol: {formatted_symbol}")
        
        # Validate the symbol before proceeding
        if not self.is_valid_symbol(symbol):
            error_msg = f"⚠️ ERROR: Symbol {symbol} is not valid or not supported on Bitget"
            logger.error(error_msg)
            
            # Send Telegram notification for invalid symbol
            try:
                from src.integrations.telegram import TelegramNotifier
                telegram = TelegramNotifier()
                telegram_message = f"⚠️ Trading Error: {symbol}\n\nThis symbol is not available on Bitget. Trade skipped to protect your capital."
                telegram.send_message(telegram_message)
            except Exception as e:
                logger.error(f"Failed to send Telegram notification: {str(e)}")
                
            return {"error": error_msg, "code": "INVALID_SYMBOL"}
            
        # Set leverage to 15x for all trades as per user requirements
        try:
            self._set_leverage(formatted_symbol, 15)
            logger.info(f"Set leverage to 15x for {formatted_symbol}")
        except Exception as e:
            logger.warning(f"Could not set 15x leverage for {formatted_symbol}: {e}")
        
        # Get account information for position
        # If quantity is not specified, calculate it based on position sizing
        if quantity is None:
            account_info = self.get_account_info()
            if 'error' in account_info:
                logger.error(f"Error getting account info for position sizing: {account_info.get('error')}")
                return account_info
                
            available_balance = account_info.get('available_balance', 0)
            if available_balance <= 0:
                logger.error(f"Insufficient available balance: {available_balance}")
                return {"error": "Insufficient available balance"}
                
            # Get market data for price
            market_data = self.get_market_data(symbol)
            if 'error' in market_data:
                logger.error(f"Error getting market data for position sizing: {market_data.get('error')}")
                return market_data
                
            last_price = market_data.get('last_price')
            if not last_price:
                logger.error("Could not get current price for position sizing")
                return {"error": "Could not get current price for position sizing"}
                
            # Calculate position size (25% of available balance by default)
            position_size_percent = self.position_size_percent
            position_value = available_balance * (position_size_percent / 100)
            
            # CRITICAL: Force minimum order value (not position value) to exactly $20 for Bitget
            # Bitget documentation says $5, but clearly requires more in practice
            # Using $20 to ensure we exceed their actual requirements
            min_order_value = 20.0
            
            # Calculate what the order value would be with current position value
            order_value = position_value / last_price * last_price  # Simplify to position_value for clarity
            
            if order_value < min_order_value:
                # Increase position value to ensure order value meets minimum
                new_position_value = min_order_value
                logger.warning(f"Increasing position value from ${position_value:.2f} to ${new_position_value:.2f} to meet Bitget minimum order value of ${min_order_value}")
                position_value = new_position_value
            
            # Calculate quantity based on last price
            if last_price and last_price > 0:
                # Calculate quantity based on position size percentage and last price
                quantity = position_value / last_price
            
            # Define minimum position sizes for different assets
            min_sizes = {
                'BTC': 0.001,    # Minimum BTC position: 0.001
                'ETH': 0.01,     # Minimum ETH position: 0.01
                'SOL': 0.1,      # Minimum SOL position: 0.1
                'DOGE': 100,     # Minimum DOGE position: 100
                'XRP': 10,       # Minimum XRP position: 10
                'DEFAULT': 0.01  # Default minimum for other assets
            }
            
            # Determine minimum size for this asset
            min_size = 0.01  # Default minimum
            
            # Calculate effective notional value with leverage
            leverage = 20  # Using 20x leverage as per user requirements
            
            # Bitget minimum base value (margin) appears to be $5 directly
            # This is different from what we expected (which would be $5/15 = $0.33)
            min_margin = 5.0
            min_notional = min_margin
            
            # Force position value to be at least the minimum required by Bitget
            if position_value < min_margin:
                logger.warning(f"Increasing position value from ${position_value:.2f} to ${min_margin:.2f} to meet Bitget minimum")
                position_value = min_margin
                quantity = position_value / last_price
            
            notional_value = quantity * last_price * leverage
            logger.info(f"Effective notional value with {leverage}x leverage: ${notional_value:.2f}")
            
            # Set minimum size requirements based on asset (physical units)
            min_size = 0.01  # Default minimum size
            if 'BTC' in symbol:
                min_size = 0.001  # BTC minimum
            elif 'ETH' in symbol:
                min_size = 0.01   # ETH minimum
            elif 'SOL' in symbol:
                min_size = 0.1    # SOL minimum
            elif 'DOGE' in symbol:
                min_size = 10.0  # DOGE minimum - lowered from 100 since we're using leverage
            elif 'XRP' in symbol:
                min_size = 1.0   # XRP minimum - lowered from 10 since we're using leverage
                
            # Check both minimum size and minimum notional value with leverage
            if quantity <= 0 or (quantity < min_size and notional_value < min_notional):
                logger.warning(f"Skipping trade due to insufficient position: {quantity} {symbol} (notional value: ${notional_value:.2f} with {leverage}x leverage)")
                # Send Telegram notification for skipped trade
                from src.integrations.telegram import TelegramNotifier
                telegram = TelegramNotifier()
                telegram_message = f"⚠️ Skipped trade: {symbol} at {last_price}\n\nInsufficient position size: {quantity} {symbol}\nNotional value: ${notional_value:.2f} with {leverage}x leverage\n\nBitget requires min. notional value of ${min_notional}\n\nYour balance: ${available_balance:.2f}\nUsing: {self.position_size_percent}% per trade"
                telegram.send_message(telegram_message)
                return {"error": f"Insufficient position size: notional value ${notional_value:.2f} < ${min_notional} minimum"}
            
            logger.info(f"Auto-calculated position size: {quantity} {symbol} at {last_price} (${notional_value:.2f} notional with {leverage}x leverage)")
            
            # Log the position sizing calculation
            logger.info(f"Position sizing: {self.position_size_percent}% of ${available_balance:.2f} = ${position_value:.2f}")
            price_str = f"${price:.2f}" if price is not None else "market"
            logger.info(f"Order quantity for {symbol} at {price_str}: {quantity:.6f}")
        
        # Normalize parameters for Bitget API
        # Bitget requires specific formatting for the side parameter
        side_lower = side.lower()
        
        # Map the side parameter according to Bitget API requirements
        if side_lower == "buy" or side_lower == "long":
            order_side = "open_long"
        elif side_lower == "sell" or side_lower == "short":
            order_side = "open_short"
        else:
            logger.error(f"Invalid side parameter: {side}")
            return {"error": f"Invalid side parameter: {side}. Must be 'buy'/'long' or 'sell'/'short'"}
        
        # Use the provided order_type or determine it from the price
        if order_type is None:
            order_type = "market" if price is None else "limit"
        logger.info(f"Using order type: {order_type}")

        
        # Set leverage to 20x as per user requirements
        leverage = 20
        
        # First check account balance to ensure there are sufficient funds
        try:
            account_info = self.get_account_info()
            if 'error' in account_info:
                error_msg = f"Could not retrieve account balance: {account_info.get('error')}"
                logger.error(error_msg)
                return {"error": error_msg}
                
            available_balance = float(account_info.get('available_balance', 0))
            logger.info(f"Current available balance: ${available_balance:.2f}")
            
            if available_balance < position_value:
                error_msg = f"Insufficient balance: ${available_balance:.2f} < ${position_value:.2f} required"
                logger.error(error_msg)
                # Return error without sending direct Telegram notification
                # The bot.py layer will handle notifications with proper rate limiting
                return {"error": error_msg, "available_balance": available_balance, "required": position_value}
        except Exception as e:
            logger.warning(f"Could not check account balance: {str(e)}")
        
        # Check if the symbol exists on Bitget and get price limits
        try:
            # Check if the symbol exists by getting its ticker info
            ticker_endpoint = f"/api/mix/v1/market/ticker?symbol={formatted_symbol}"
            ticker_info = self._make_request("GET", ticker_endpoint, signed=False)
            
            if 'error' in ticker_info or 'data' not in ticker_info or not ticker_info.get('data'):
                error_msg = f"Symbol {formatted_symbol} does not exist on Bitget or has been removed"
                logger.error(error_msg)
                # Send Telegram notification for invalid symbol
                from src.integrations.telegram import TelegramNotifier
                telegram = TelegramNotifier()
                telegram_message = f"⚠️ Trading Error: {symbol}\n\nThis symbol is not available on Bitget. Skipping trade."
                telegram.send_message(telegram_message)
                return {"error": error_msg}
            
            # Get price limits from ticker data
            ticker_data = ticker_info.get('data', {})
            if not isinstance(ticker_data, list):
                ticker_data = [ticker_data]
                
            if ticker_data:
                current_ticker = ticker_data[0]
                # Extract price information
                market_price = float(current_ticker.get('last', price if price else 0))
                high_24h = float(current_ticker.get('high24h', 0))
                low_24h = float(current_ticker.get('low24h', 0))
                
                # Calculate safe price limits (within 5% of market price)
                max_price = min(market_price * 1.05, high_24h * 1.02)
                min_price = max(market_price * 0.95, low_24h * 0.98)
                
                logger.info(f"Symbol {formatted_symbol} verified to exist on Bitget")
                logger.info(f"Market price: {market_price}, Safe price range: {min_price:.8f} - {max_price:.8f}")
                
                # If we have a price specified, ensure it's within limits
                if price is not None:
                    if price > max_price:
                        logger.warning(f"Order price {price} exceeds maximum safe price {max_price} for {formatted_symbol}, adjusting to {max_price}")
                        price = max_price
                    elif price < min_price:
                        logger.warning(f"Order price {price} below minimum safe price {min_price} for {formatted_symbol}, adjusting to {min_price}")
                        price = min_price
            else:
                logger.warning(f"No ticker data available for {formatted_symbol}, proceeding with caution")
        except Exception as e:
            logger.warning(f"Could not verify symbol {formatted_symbol}: {str(e)}")
        
        # Determine the holdSide parameter - must be lowercase 'long' or 'short'
        # Map from the original side parameter to holdSide
        if position_side is not None:
            hold_side = position_side.lower()  # Ensure lowercase
            logger.info(f"Using explicitly provided position side: {hold_side}")
        else:
            # Map directly from the original side parameter
            if side_lower in ["buy", "long"]:
                hold_side = "long"
            elif side_lower in ["sell", "short"]:
                hold_side = "short"
            else:
                logger.error(f"Cannot determine holdSide from side: {side}")
                return {"error": f"Invalid side parameter for holdSide: {side}"}
            logger.info(f"Using derived position side: {hold_side} from side: {side}")
        
        # Ensure the symbol has proper leverage set first - we need to do this before order placement
        try:
            leverage_endpoint = "/api/mix/v1/account/setLeverage"
            leverage_params = {
                "symbol": formatted_symbol,
                "marginCoin": "USDT",
                "leverage": str(leverage),
                "holdSide": hold_side  # Must be lowercase 'long' or 'short'
            }
            leverage_response = self._make_request("POST", leverage_endpoint, data=leverage_params, signed=True)
            
            if 'error' in leverage_response:
                logger.error(f"Error setting leverage: {leverage_response.get('error')}")
                # If we can't set leverage, we can't place the order
                return {"error": f"Failed to set leverage: {leverage_response.get('error')}"}
            else:
                logger.info(f"Successfully set leverage for {formatted_symbol} to {leverage}x with holdSide={hold_side}")
        except Exception as e:
            logger.warning(f"Could not set leverage: {str(e)}")
            return {"error": f"Failed to set leverage: {str(e)}"}
        
        # Order parameters for Bitget futures API
        params = {
            "symbol": formatted_symbol,
            "marginCoin": "USDT",  # USDT-margined contract
            "side": order_side,
            "orderType": order_type,
            "size": str(quantity),  # Don't round - let the API handle precision
            "holdSide": hold_side  # Must match the holdSide used for setting leverage
        }
        
        if order_type == "limit" and price is not None:
            # Round price to 5 decimal places to ensure it's a multiple of 0.00001
            rounded_price = round(price, 5)
            params["price"] = str(rounded_price)
            if rounded_price != price:
                logger.info(f"Rounded order price from {price} to {rounded_price} to comply with Bitget tick size requirements")
        
        # Place the order using Bitget's futures API
        endpoint = "/api/mix/v1/order/placeOrder"
        
        # For logging, show rounded price if it's a limit order
        log_price = rounded_price if order_type == "limit" and price is not None else "market price"
        logger.info(f"Placing {order_side} {order_type} order for {formatted_symbol}: {quantity} at {log_price}")
        
        try:
            response = self._make_request("POST", endpoint, data=params, signed=True)
            
            if 'error' in response:
                return response
                
            # Format response for consistency with our internal API
            order_data = response.get('data', {})
            return {
                "orderId": order_data.get('orderId', ''),
                "status": order_data.get('state', ''),
                "filled_qty": float(order_data.get('size', 0)),
                "entry_price": float(order_data.get('price', price if price else 0)),
            }
        except Exception as e:
            error_msg = f"Error placing order: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    @prevent_duplicate_orders
    def set_stop_loss_bitget(self, symbol: str, quantity: float, stop_price: float, position_side: str) -> Dict:
        """
        Legacy method - DIRECT IMPLEMENTATION to ensure consistent behavior with main method
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            quantity: Order quantity
            stop_price: Stop price
            position_side: The side of the position ('long' or 'short')
            
        Returns:
            Dict: Order result
        """
        logger.warning("Legacy set_stop_loss_bitget called - using direct implementation with holdSide")
        
        # Format symbol for Bitget futures API
        if '/' in symbol:
            base_currency = symbol.split('/')[0]
            formatted_symbol = f"{base_currency}USDT_UMCBL"
        else:
            formatted_symbol = f"{symbol}_UMCBL" if not symbol.endswith('_UMCBL') else symbol
        
        # Determine close side based on position side
        hold_side = position_side.lower()
        close_side = "close_long" if hold_side == "long" else "close_short"
        
        # Round stop_price to 5 decimal places
        rounded_stop_price = round(stop_price, 5)
        
        data = {
            "symbol": formatted_symbol,
            "marginCoin": "USDT",
            "orderType": "market",
            "side": close_side,
            "size": str(round(quantity, 4)),
            "triggerType": "market_price",
            "triggerPrice": str(rounded_stop_price),
            "planType": "stop",
            "reduceOnly": "true",
            "holdSide": hold_side  # Critical: Specify the position side being held
        }
        
        logger.info(f"Setting stop-loss with {close_side} at {rounded_stop_price} for {formatted_symbol}")
        
        endpoint = "/api/mix/v1/plan/placePlan"
        
        try:
            response = self._make_request("POST", endpoint, data=data, signed=True)
            
            if 'error' in response:
                logger.error(f"Failed to set stop-loss: {response.get('error')}")
                return response
                
            # Format response for consistency with our internal API
            order_data = response.get('data', {})
            return {
                "orderId": order_data.get('orderId', ''),
                "status": "placed",
                "type": "stop_loss",
                "price": stop_price
            }
        except Exception as e:
            error_msg = f"Error setting stop-loss: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}
    
    @prevent_duplicate_orders
    def set_take_profit_bitget(self, symbol: str, quantity: float, price: float, position_side: str) -> Dict:
        """
        Legacy method - DIRECT IMPLEMENTATION to ensure consistent behavior with main method
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            quantity: Order quantity
            price: Take-profit price
            position_side: The side of the position ('long' or 'short')
            
        Returns:
            Dict: Order result
        """
        logger.warning("Legacy set_take_profit_bitget called - using direct implementation with holdSide")
        
        # Format symbol for Bitget futures API
        if '/' in symbol:
            base_currency = symbol.split('/')[0]
            formatted_symbol = f"{base_currency}USDT_UMCBL"
        else:
            formatted_symbol = f"{symbol}_UMCBL" if not symbol.endswith('_UMCBL') else symbol
        
        # Determine close side based on position side
        hold_side = position_side.lower()
        close_side = "close_long" if hold_side == "long" else "close_short"
        
        # Round price to 5 decimal places
        rounded_price = round(price, 5)
        
        data = {
            "symbol": formatted_symbol,
            "marginCoin": "USDT",
            "orderType": "market",
            "side": close_side,
            "size": str(round(quantity, 4)),
            "triggerType": "market_price",
            "triggerPrice": str(rounded_price),
            "planType": "profit",
            "reduceOnly": "true",
            "holdSide": hold_side  # Critical: Specify the position side being held
        }
        
        logger.info(f"Setting take-profit with {close_side} at {rounded_price} (rounded from {price}) for {formatted_symbol}")
        
        endpoint = "/api/mix/v1/plan/placePlan"
        
        try:
            response = self._make_request("POST", endpoint, data=data, signed=True)
            
            if 'error' in response:
                logger.error(f"Failed to set take-profit: {response.get('error')}")
                return response
                
            # Format response for consistency with our internal API
            order_data = response.get('data', {})
            return {
                "orderId": order_data.get('orderId', ''),
                "status": "placed",
                "type": "take_profit",
                "price": price
            }
        except Exception as e:
            error_msg = f"Error setting take-profit: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    @prevent_duplicate_orders
    def set_stop_loss(self, symbol: str, quantity: float, stop_price: float, position_side: str = None) -> Dict:
        """
        Set a stop-loss order using Bitget API

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            quantity: Order quantity
            stop_price: Stop price
            position_side: The side of the position ('long' or 'short'). If None, it will be determined

        Returns:
            Dict: Order result
        """
        # Format symbol for Bitget futures API
        if '/' in symbol:
            base_currency = symbol.split('/')[0]
            formatted_symbol = f"{base_currency}USDT_UMCBL"
        else:
            formatted_symbol = f"{symbol}_UMCBL" if not symbol.endswith('_UMCBL') else symbol
            
        # Determine position side from parameter or lookup
        if position_side:
            # Use the provided position side (enforced tagging for hedging mode)
            hold_side = position_side.lower()
            close_side = "close_long" if hold_side == "long" else "close_short"
            logger.info(f"Using explicitly provided position side: {hold_side} for stop-loss")
        else:
            # Try to determine the position side from the actual position
            try:
                # Get position info for this symbol to determine if long or short
                endpoint = f"/api/mix/v1/position/singlePosition?symbol={formatted_symbol}&marginCoin=USDT"
                position_info = self._make_request("GET", endpoint, signed=True)
                
                if 'error' not in position_info and 'data' in position_info:
                    position_data = position_info.get('data', {})
                    hold_side = position_data.get('holdSide')
                    if hold_side == "long":
                        close_side = "close_long"
                    elif hold_side == "short":
                        close_side = "close_short"
                    else:
                        # No position found, log warning and exit
                        logger.warning(f"No active position found for {formatted_symbol} to set stop-loss")
                        return {"error": f"No active position found for {formatted_symbol} to set stop-loss"}
                else:
                    # No position info available, log warning and exit
                    logger.warning(f"Could not retrieve position info for {formatted_symbol} to set stop-loss")
                    return {"error": f"Could not retrieve position info for {formatted_symbol} to set stop-loss"}
            except Exception as e:
                logger.error(f"Error determining position side for stop-loss: {str(e)}")
                return {"error": f"Could not determine position side: {str(e)}"}
            
        # For Bitget, we need to place a conditional order with trigger price
        # Round stop_price to 5 decimal places to comply with Bitget requirements
        rounded_stop_price = round(stop_price, 5)
        
        data = {
            "symbol": formatted_symbol,
            "marginCoin": "USDT",
            "orderType": "market",  # Market order for immediate execution when triggered
            "side": close_side,  # Close the correct position side
            "size": str(round(quantity, 4)),
            "triggerType": "market_price",
            "triggerPrice": str(rounded_stop_price),
            "planType": "stop",
            "reduceOnly": "true",  # Ensure this order only reduces positions, doesn't open new ones
            "holdSide": hold_side  # Critical: Specify the position side being held
        }
        
        logger.info(f"Setting stop-loss with {close_side} at {rounded_stop_price} (rounded from {stop_price}) for {formatted_symbol}")

        endpoint = "/api/mix/v1/plan/placePlan"
        
        try:
            response = self._make_request("POST", endpoint, data=data, signed=True)
            
            if 'error' in response:
                logger.error(f"Failed to set stop-loss: {response.get('error')}")
                return response
                
            # Format response for consistency with our internal API
            order_data = response.get('data', {})
            return {
                "orderId": order_data.get('orderId', ''),
                "status": "placed",
                "type": "stop_loss",
                "price": stop_price
            }
        except Exception as e:
            error_msg = f"Error setting stop-loss: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    @prevent_duplicate_orders
    def set_take_profit(self, symbol: str, quantity: float, price: float, position_side: str = None) -> Dict:
        """
        Set a take-profit order using Bitget API

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            quantity: Order quantity
            price: Take-profit price
            position_side: The side of the position ('long' or 'short'). If None, it will be determined

        Returns:
            Dict: Order result
        """
        # Format symbol for Bitget futures API
        if '/' in symbol:
            base_currency = symbol.split('/')[0]
            formatted_symbol = f"{base_currency}USDT_UMCBL"
        else:
            formatted_symbol = f"{symbol}_UMCBL" if not symbol.endswith('_UMCBL') else symbol
            
        # Determine position side from parameter or lookup
        if position_side:
            # Use the provided position side (enforced tagging for hedging mode)
            hold_side = position_side.lower()
            close_side = "close_long" if hold_side == "long" else "close_short"
            logger.info(f"Using explicitly provided position side: {hold_side} for take-profit")
        else:
            # Try to determine the position side from the actual position
            try:
                # Get position info for this symbol to determine if long or short
                endpoint = f"/api/mix/v1/position/singlePosition?symbol={formatted_symbol}&marginCoin=USDT"
                position_info = self._make_request("GET", endpoint, signed=True)
                
                if 'error' not in position_info and 'data' in position_info:
                    position_data = position_info.get('data', {})
                    hold_side = position_data.get('holdSide')
                    if hold_side == "long":
                        close_side = "close_long"
                    elif hold_side == "short":
                        close_side = "close_short"
                    else:
                        # No position found, log warning and exit
                        logger.warning(f"No active position found for {formatted_symbol} to set take-profit")
                        return {"error": f"No active position found for {formatted_symbol} to set take-profit"}
                else:
                    # No position info available, log warning and exit
                    logger.warning(f"Could not retrieve position info for {formatted_symbol} to set take-profit")
                    return {"error": f"Could not retrieve position info for {formatted_symbol} to set take-profit"}
            except Exception as e:
                logger.error(f"Error determining position side for take-profit: {str(e)}")
                return {"error": f"Could not determine position side: {str(e)}"}
            
        # For Bitget, we need to place a conditional order with trigger price
        # Round take profit price to 5 decimal places to comply with Bitget requirements
        rounded_price = round(price, 5)
        
        data = {
            "symbol": formatted_symbol,
            "marginCoin": "USDT",
            "orderType": "market",  # Market order for immediate execution when triggered
            "side": close_side,  # Close the correct position side
            "size": str(round(quantity, 4)),
            "triggerType": "market_price",
            "triggerPrice": str(rounded_price),
            "planType": "profit_plan",  # Take-profit plan
            "reduceOnly": "true",  # Ensure this order only reduces positions, doesn't open new ones
            "holdSide": hold_side  # Critical: Specify the position side being held
        }
        
        logger.info(f"Setting take-profit with {close_side} at {rounded_price} (rounded from {price}) for {formatted_symbol}")

        endpoint = "/api/mix/v1/plan/placePlan"
        
        try:
            response = self._make_request("POST", endpoint, data=data, signed=True)
            
            if 'error' in response:
                logger.error(f"Failed to set take-profit: {response.get('error')}")
                return response
                
            # Format response for consistency with our internal API
            order_data = response.get('data', {})
            return {
                "orderId": order_data.get('orderId', ''),
                "status": "placed",
                "type": "take_profit",
                "price": price
            }
        except Exception as e:
            error_msg = f"Error setting take-profit: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        """
        Get all open orders using Bitget API

        Args:
            symbol: Optional symbol to filter by

        Returns:
            List[Dict]: List of open orders
        """
        # Format symbol for Bitget futures API if provided
        formatted_symbol = None
        if symbol:
            if '/' in symbol:
                base_currency = symbol.split('/')[0]
                formatted_symbol = f"{base_currency}USDT_UMCBL"
            else:
                formatted_symbol = f"{symbol}_UMCBL" if not symbol.endswith('_UMCBL') else symbol
        
        # Set up parameters for the request
        params = {
            "marginCoin": "USDT"  # USDT-margined contracts
        }
        
        if formatted_symbol:
            params["symbol"] = formatted_symbol
            
        # Use Bitget's futures API endpoint for active orders
        endpoint = "/api/mix/v1/order/current"
        
        try:
            response = self._make_request("GET", endpoint, params=params, signed=True)
            
            if 'error' in response:
                logger.error(f"Failed to get open orders: {response.get('error')}")
                return []
                
            # Format response for consistency with our internal API
            orders_data = response.get('data', [])
            formatted_orders = []
            
            for order in orders_data:
                formatted_orders.append({
                    "orderId": order.get('orderId', ''),
                    "symbol": order.get('symbol', '').replace('_UMCBL', '/USDT'),
                    "price": float(order.get('price', 0)),
                    "origQty": float(order.get('size', 0)),
                    "executedQty": float(order.get('filledQty', 0)),
                    "status": order.get('status', ''),
                    "type": order.get('orderType', ''),
                    "side": "buy" if order.get('side', '') == "long" else "sell"
                })
                
            return formatted_orders
        except Exception as e:
            error_msg = f"Error getting open orders: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return []

    def cancel_order(self, order_id: str, symbol: str) -> Dict:
        """
        Cancel an order using Bitget API

        Args:
            order_id: Order ID to cancel
            symbol: Trading pair symbol

        Returns:
            Dict: Cancellation result
        """
        # Format symbol for Bitget futures API
        if '/' in symbol:
            base_currency = symbol.split('/')[0]
            formatted_symbol = f"{base_currency}USDT_UMCBL"
        else:
            formatted_symbol = f"{symbol}_UMCBL" if not symbol.endswith('_UMCBL') else symbol
            
        # Set up parameters for the request
        params = {
            "symbol": formatted_symbol,
            "marginCoin": "USDT",
            "orderId": order_id
        }
            
        # Use Bitget's futures API endpoint for canceling orders
        endpoint = "/api/mix/v1/order/cancel-order"
        
        try:
            response = self._make_request("POST", endpoint, data=params, signed=True)
            
            if 'error' in response:
                logger.error(f"Failed to cancel order: {response.get('error')}")
                return {"error": response.get('error')}
                
            # Format response for consistency with our internal API
            cancel_data = response.get('data', {})
            return {
                "orderId": cancel_data.get('orderId', ''),
                "status": "canceled" if response.get('code') == '00000' else "failed",
                "message": response.get('msg', '')
            }
        except Exception as e:
            error_msg = f"Error canceling order: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    def get_market_data(self, symbol: str) -> Dict:
        """
        Get current market data for a symbol from Bitget API

        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')

        Returns:
            Dict: Market data including last price, 24h high/low, and volume
        """
        # Use bulletproof symbol formatting
        formatted_symbol = self._format_symbol_for_bitget(symbol)
            
        # Use Bitget's market ticker endpoint
        endpoint = f"/api/mix/v1/market/ticker?symbol={formatted_symbol}"
        
        try:
            response = self._make_request("GET", endpoint)
            
            if 'error' in response:
                logger.error(f"Failed to get market data: {response.get('error')}")
                return response
                
            # Extract and format the relevant market data
            ticker_data = response.get('data', {})
            
            # Log raw response for debugging price issues
            logger.debug(f"Raw ticker response for {symbol}: {ticker_data}")
            
            # Format response for consistency with our internal API
            last_price = float(ticker_data.get('last', 0))
            
            return {
                "symbol": symbol,
                "last_price": last_price,
                "bid_price": float(ticker_data.get('bidPr', last_price)),
                "ask_price": float(ticker_data.get('askPr', last_price)),
                "high_price": float(ticker_data.get('high24h', 0)),
                "low_price": float(ticker_data.get('low24h', 0)),
                "volume": float(ticker_data.get('baseVolume', 0)),
                "timestamp": int(time.time() * 1000)
            }
        except Exception as e:
            error_msg = f"Error getting market data for {symbol}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}

    def execute_signal(self, signal: Dict) -> Dict:
        """
        Execute a trading signal with automatic position sizing and risk management
        
        Args:
            signal: Trading signal dict with symbol, direction, stop_loss, take_profit, etc.
        
        Returns:
            Dict: Result of signal execution with order details or error
        """
        # Import here to avoid circular imports
        from src.integrations.telegram import TelegramNotifier
        # Initialize telegram notifier
        telegram = TelegramNotifier()
        
        try:
            logger.info(f"Executing signal: {signal}")
            
            # Ensure stop loss and take profit are available
            stop_loss = signal.get('stop_loss')
            take_profit = signal.get('profit_target')
            
            # If stop loss or take profit are missing, calculate them using ATR
            if not stop_loss or not take_profit:
                logger.warning("Stop loss or take profit missing, calculating based on current price and ATR")
                atr = signal.get('atr', 0.01)  # Default ATR if not provided
                
                # Get current price if not provided in signal
                price = signal.get('price')
                if price is None:
                    # Get current market price for the symbol
                    try:
                        market_data = self.get_market_data(signal['symbol'])
                        price = float(market_data.get('last_price', 0))
                        if price <= 0:
                            logger.error(f"Could not get valid price for {signal['symbol']}")
                            return {"error": f"Could not calculate TP/SL: invalid price for {signal['symbol']}"}
                    except Exception as e:
                        logger.error(f"Error getting market data for TP/SL calculation: {str(e)}")
                        return {"error": f"Could not calculate TP/SL: {str(e)}"}
                
                # Now calculate TP/SL with valid price
                if signal['direction'].upper() in ['LONG', 'BUY']:
                    if not stop_loss:
                        # For LONG positions, stop loss must be at least 5% below current price to comply with Bitget limits
                        # but not more than 15% to protect capital
                        min_sl_price = price * 0.95  # Maximum 5% below current price
                        atr_sl_price = price - (2 * atr)  # 2 ATR below entry for long stop loss
                        stop_loss = max(atr_sl_price, min_sl_price)  # Use the higher of the two (closer to price)
                    if not take_profit:
                        take_profit = price + (3 * atr)  # 3 ATR above entry for long take profit
                else:  # SHORT
                    if not stop_loss:
                        # For SHORT positions, stop loss must be at least 5% above current price to comply with Bitget limits
                        # but not more than 15% to protect capital
                        min_sl_price = price * 1.05  # Minimum 5% above current price
                        atr_sl_price = price + (2 * atr)  # 2 ATR above entry for short stop loss
                        stop_loss = min(atr_sl_price, min_sl_price)  # Use the lower of the two (closer to price)
                    if not take_profit:
                        take_profit = price - (3 * atr)  # 3 ATR below entry for short take profit
                        
                logger.info(f"Calculated TP/SL based on price {price}: SL={stop_loss}, TP={take_profit}")
                
                # Ensure values are properly formatted
                stop_loss = float("{:.8f}".format(stop_loss))
                take_profit = float("{:.8f}".format(take_profit))
                
                logger.info(f"Calculated stop_loss: {stop_loss}, take_profit: {take_profit}")
            
            # Extract signal details
            symbol = signal.get('symbol')
            direction = signal.get('direction')
            price = signal.get('price')  # Optional limit price
            
            if not symbol or not direction:
                error_msg = "Invalid signal: missing symbol or direction"
                logger.error(error_msg)
                return {"error": error_msg}
            
            # Map direction to order side for Bitget API format
            if direction.upper() in ["LONG", "BUY"]:
                side = "buy"  # Will be mapped to open_long in place_order
                # For stop loss and take profit, we'll need to close a long position
                position_side = "long"
                close_side = "close_long"
            elif direction.upper() in ["SHORT", "SELL"]:
                side = "sell"  # Will be mapped to open_short in place_order
                # For stop loss and take profit, we'll need to close a short position
                position_side = "short"
                close_side = "close_short"
            else:
                error_msg = f"Invalid direction: {direction}. Must be LONG/BUY or SHORT/SELL."
                logger.error(error_msg)
                return {"error": error_msg}
            
            logger.info(f"Direction: {direction} -> side: {side}, position_side: {position_side}")
            
            # Check if we're in test mode - don't actually execute orders in test mode
            if os.getenv('TEST_MODE', 'false').lower() == 'true' or getattr(self, 'test_mode', False):
                logger.info(f"TEST MODE: Would execute signal for {symbol} {direction}")
                return {
                    "success": True, 
                    "test_mode": True, 
                    "message": f"Signal execution simulated in test mode: {symbol} {direction} at {price if price else 'market'}",
                    "symbol": symbol,
                    "direction": direction,
                    "entry_price": price if price else "market",
                    "win_probability": signal.get('win_probability', 0.0)
                }
                
            # Check if API is properly configured
            if not self.is_configured:
                error_msg = "❌ *API ERROR*: Bitget API not configured correctly.\n\nPlease check your API keys in the .env file."
                telegram.send_message(error_msg)
                return {"success": False, "error": "Bitget API not configured"}
            
            # Use bulletproof symbol formatting
            formatted_symbol = self._format_symbol_for_bitget(symbol)
                
            # Set leverage to 20x before placing any orders
            try:
                self._set_leverage(formatted_symbol, 20)  # Always use 20x leverage as per requirement
                logger.info(f"Set leverage to 20x for {formatted_symbol}")
            except Exception as e:
                logger.warning(f"Could not set leverage for {formatted_symbol}: {e}")
            
            # DIRECT LIVE TRADE EXECUTION - NO MORE HOLDSIDE ISSUES
            # Calculate position size directly
            account_info = self.get_account_info()
            balance = float(account_info.get('available_balance', 0))
            
            # Check if a fixed notional value is specified for testing/verification
            fixed_notional = signal.get('fixed_notional', None)
            leverage = 20  # Always use 20x leverage as per user requirements
            
            if fixed_notional is not None:
                # Use the fixed notional value directly, but ensure it doesn't exceed available balance
                notional_value = fixed_notional
                margin_value = notional_value / leverage
                
                # Make sure margin doesn't exceed 90% of available balance
                if margin_value > balance * 0.9:
                    logger.warning(f"Required margin ${margin_value:.2f} exceeds 90% of available balance ${balance:.2f}, adjusting")
                    margin_value = balance * 0.9  # Use 90% of available balance
                    notional_value = margin_value * leverage
                    
                logger.info(f"Using fixed notional value: ${notional_value:.2f} (margin: ${margin_value:.2f})")
            else:
                # Use position_size from signal if provided, otherwise default to 35% of balance
                position_percentage = signal.get('position_size', 0.35)
                margin_value = balance * position_percentage
                notional_value = margin_value * leverage
            
            # Bitget requires minimum notional value of $5 USDT
            MIN_NOTIONAL_VALUE = 5.0  # $5 USD minimum
            
            # Always ensure we meet the minimum notional value for test trades
            if notional_value < MIN_NOTIONAL_VALUE:
                logger.warning(f"Increasing notional value from ${notional_value:.2f} to ${MIN_NOTIONAL_VALUE:.2f} to meet Bitget minimum")
                notional_value = MIN_NOTIONAL_VALUE
                margin_value = notional_value / leverage
                
                # Double-check if we have enough balance
                if margin_value > balance:
                    logger.warning(f"Required margin ${margin_value:.2f} exceeds available balance ${balance:.2f}, adjusting to use 90% of balance")
                    margin_value = balance * 0.9  # Use 90% of available balance
                    notional_value = margin_value * leverage
                    
            logger.info(f"Order sizing: Balance=${balance:.2f}, Margin=${margin_value:.2f}, Notional=${notional_value:.2f} (with {leverage}x leverage)")
            
            # Get current price for quantity calculation
            market_data = self.get_market_data(symbol)
            current_price = float(market_data.get('last_price', price if price else 0))
            
            if current_price <= 0:
                return {"error": "Could not get current price"}
            
            # Calculate quantity based on notional value (not margin value)
            quantity = notional_value / current_price
            
            # Ensure quantity is sufficient for minimum notional value
            min_quantity = MIN_NOTIONAL_VALUE / current_price
            if quantity < min_quantity:
                logger.warning(f"Increasing quantity from {quantity:.4f} to {min_quantity:.4f} to meet minimum notional value")
                quantity = min_quantity
            
            logger.info(f"DIRECT EXECUTION: {symbol} {side} - Balance: ${balance:.2f}, Margin: ${margin_value:.2f}, Notional: ${notional_value:.2f}, Quantity: {quantity:.4f}")
            
            # Use direct order placement method
            order_result = self.place_order_direct(symbol, side, quantity, price)
            
            if 'error' in order_result:
                error_msg = f"❌ *ORDER ERROR*: Failed to place {direction} order for {symbol}.\n\nError: {order_result.get('error', 'Unknown error')}"
                telegram.send_message(error_msg)
                return order_result
            
            # If order was successful, set stop loss and take profit using bulletproof system
            logger.info(f"✅ Order executed successfully: {order_result}")
            
            # Get entry price from order result
            entry_price = float(order_result.get('entry_price', current_price))
            
            # Place TP/SL orders using the new bulletproof system
            tp_sl_result = None
            if stop_loss and take_profit:
                logger.info(f"🎯 Placing TP/SL orders for {symbol} - Entry: {entry_price}, TP: {take_profit}, SL: {stop_loss}")
                tp_sl_result = self.place_tp_sl_orders(symbol, side, quantity, entry_price, take_profit, stop_loss)
                
                if tp_sl_result.get('take_profit', {}).get('success') and tp_sl_result.get('stop_loss', {}).get('success'):
                    logger.info(f"✅ TP/SL orders successfully placed for {symbol}")
                else:
                    logger.error(f"❌ TP/SL order placement failed: {tp_sl_result}")
                    error_msg = f"⚠️ *WARNING*: Order placed but TP/SL failed: {tp_sl_result}"
                    telegram.send_message(error_msg)
            else:
                logger.warning(f"⚠️ No TP/SL values provided for {symbol}")
            
            # Confirm successful execution via Telegram
            success_msg = f"Trade executed: {symbol} {direction} at {price if price else 'market'}"
            
            # Extract TP/SL results from the tp_sl_result dictionary
            sl_result = tp_sl_result.get('stop_loss', {}) if tp_sl_result else {}
            tp_result = tp_sl_result.get('take_profit', {}) if tp_sl_result else {}
            
            if sl_result and 'error' not in sl_result:
                success_msg += f"\nStop-loss: {stop_loss}"
            if tp_result and 'error' not in tp_result:
                success_msg += f"\nTake-profit: {take_profit}"
                
            telegram.send_message(success_msg)
            
            return {
                "success": True,
                "order_id": order_result.get('orderId'),
                "symbol": symbol,
                "direction": direction,
                "filled_quantity": order_result.get('filled_qty', 0),
                "stop_loss": sl_result,
                "take_profit": tp_result
            }
                
        except Exception as e:
            error_msg = f"⚠️ ERROR: Exception while executing {signal.get('symbol', 'unknown')} signal: {str(e)}"
            logger.error(error_msg, exc_info=True)
            telegram.send_message(error_msg)
            return {"error": str(e)}

    def _set_leverage(self, symbol: str, leverage: int) -> Dict:
        """
        Set leverage for a specific symbol
        
        Args:
            symbol: Trading pair symbol (formatted for Bitget)
            leverage: Leverage value to set (1-125)
            
        Returns:
            Dict: Response from API
        """
        if not self.is_configured or self.test_mode:
            logger.info(f"TEST MODE: Would set {leverage}x leverage for {symbol}")
            return {"success": True, "test_mode": True}
            
        # Endpoint for setting leverage in Bitget API
        endpoint = "/api/mix/v1/account/setLeverage"
        
        # Parameters for the leverage setting request
        params = {
            "symbol": symbol,
            "marginCoin": "USDT",
            "leverage": str(leverage),
            "holdSide": "long_short"  # Set for both long and short positions
        }
        
        try:
            response = self._make_request("POST", endpoint, data=params, signed=True)
            return response
        except Exception as e:
            logger.error(f"Error setting leverage: {str(e)}")
            return {"error": str(e)}

# For backward compatibility, alias the class
BitgetIntegration = TradingAPI
BidgetAPI = TradingAPI  # Keep both aliases for compatibility
