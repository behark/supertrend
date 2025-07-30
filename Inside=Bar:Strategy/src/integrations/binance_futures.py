"""
Binance Futures API Integration - Direct Live Trade Execution
Bypasses Bitget holdSide issues for immediate live trading
"""

import os
import time
import hmac
import hashlib
import requests
from urllib.parse import urlencode
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class BinanceFuturesAPI:
    """
    Binance Futures API for live trade execution
    """
    
    def __init__(self):
        self.api_key = os.getenv('BINANCE_API_KEY')
        self.api_secret = os.getenv('BINANCE_API_SECRET')
        self.base_url = 'https://fapi.binance.com'
        
        self.is_configured = bool(self.api_key and self.api_secret)
        
        if self.is_configured:
            logger.info("✅ Binance Futures API configured")
        else:
            logger.warning("❌ Binance Futures API not configured - add BINANCE_API_KEY and BINANCE_API_SECRET to .env")
    
    def _generate_signature(self, query_string: str) -> str:
        """Generate HMAC SHA256 signature for Binance API"""
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def _make_request(self, method: str, endpoint: str, params: Dict = None, signed: bool = False) -> Dict:
        """Make request to Binance Futures API"""
        url = f"{self.base_url}{endpoint}"
        headers = {'X-MBX-APIKEY': self.api_key} if self.api_key else {}
        
        if params is None:
            params = {}
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            query_string = urlencode(params)
            params['signature'] = self._generate_signature(query_string)
        
        try:
            if method == 'GET':
                response = requests.get(url, params=params, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, params=params, headers=headers, timeout=10)
            else:
                return {"error": f"Unsupported HTTP method: {method}"}
            
            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Binance API error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return {"error": error_msg}
                
        except Exception as e:
            error_msg = f"Binance API request failed: {str(e)}"
            logger.error(error_msg)
            return {"error": error_msg}
    
    def get_account_info(self) -> Dict:
        """Get Binance Futures account information"""
        if not self.is_configured:
            return {"error": "Binance API not configured"}
        
        try:
            response = self._make_request('GET', '/fapi/v2/account', signed=True)
            
            if 'error' in response:
                return response
            
            # Extract USDT balance
            usdt_balance = 0
            for asset in response.get('assets', []):
                if asset.get('asset') == 'USDT':
                    usdt_balance = float(asset.get('availableBalance', 0))
                    break
            
            return {
                'available_balance': usdt_balance,
                'total_balance': float(response.get('totalWalletBalance', 0)),
                'unrealized_pnl': float(response.get('totalUnrealizedProfit', 0))
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_market_data(self, symbol: str) -> Dict:
        """Get current market price for symbol"""
        # Format symbol for Binance (remove slash)
        binance_symbol = symbol.replace('/', '').upper()
        
        try:
            response = self._make_request('GET', '/fapi/v1/ticker/price', {'symbol': binance_symbol})
            
            if 'error' in response:
                return response
            
            return {
                'symbol': symbol,
                'last_price': float(response.get('price', 0))
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def set_leverage(self, symbol: str, leverage: int) -> Dict:
        """Set leverage for a symbol"""
        binance_symbol = symbol.replace('/', '').upper()
        
        params = {
            'symbol': binance_symbol,
            'leverage': leverage
        }
        
        try:
            response = self._make_request('POST', '/fapi/v1/leverage', params, signed=True)
            
            if 'error' in response:
                return response
                
            logger.info(f"Set leverage to {leverage}x for {binance_symbol}")
            return {"success": True, "leverage": leverage}
            
        except Exception as e:
            return {"error": str(e)}
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict:
        """
        Place a market order on Binance Futures
        
        Args:
            symbol: Trading pair (e.g., 'DOGE/USDT')
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            
        Returns:
            Dict: Order result
        """
        if not self.is_configured:
            return {"error": "Binance API not configured"}
        
        # Format symbol for Binance
        binance_symbol = symbol.replace('/', '').upper()
        
        # Set leverage to 20x first
        leverage_result = self.set_leverage(symbol, 20)
        if 'error' in leverage_result:
            logger.warning(f"Could not set leverage: {leverage_result['error']}")
        
        # Order parameters
        params = {
            'symbol': binance_symbol,
            'side': side.upper(),
            'type': 'MARKET',
            'quantity': f"{quantity:.4f}",
        }
        
        logger.info(f"Placing Binance market order: {params}")
        
        try:
            response = self._make_request('POST', '/fapi/v1/order', params, signed=True)
            
            if 'error' in response:
                return response
            
            return {
                'success': True,
                'orderId': response.get('orderId'),
                'symbol': symbol,
                'side': side,
                'quantity': float(response.get('executedQty', quantity)),
                'price': float(response.get('avgPrice', 0)),
                'status': response.get('status'),
                'exchange': 'binance_futures'
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def execute_signal(self, signal: Dict) -> Dict:
        """
        Execute a trading signal on Binance Futures
        
        Args:
            signal: Trading signal dictionary
            
        Returns:
            Dict: Execution result
        """
        if not self.is_configured:
            return {"error": "Binance Futures API not configured"}
        
        try:
            symbol = signal.get('symbol')
            direction = signal.get('direction', 'LONG').upper()
            
            # Get account balance
            account_info = self.get_account_info()
            if 'error' in account_info:
                return account_info
            
            balance = account_info.get('available_balance', 0)
            
            # Calculate position size (35% of balance)
            position_value = balance * 0.35
            
            # Get current price
            market_data = self.get_market_data(symbol)
            if 'error' in market_data:
                return market_data
            
            current_price = market_data.get('last_price', 0)
            if current_price <= 0:
                return {"error": "Could not get current price"}
            
            # Calculate quantity
            quantity = position_value / current_price
            
            # Determine order side
            side = 'BUY' if direction == 'LONG' else 'SELL'
            
            logger.info(f"Binance execution: {symbol} {side} - Balance: ${balance:.2f}, Position: ${position_value:.2f}, Quantity: {quantity:.4f}")
            
            # Place market order
            order_result = self.place_market_order(symbol, side, quantity)
            
            if order_result.get('success'):
                logger.info(f"✅ Binance trade executed: {order_result}")
                
                # Send Telegram notification
                try:
                    from src.integrations.telegram import TelegramNotifier
                    telegram = TelegramNotifier()
                    
                    message = f"""🚀 **LIVE TRADE EXECUTED - BINANCE FUTURES** 🚀

🌙 **{symbol}** - {direction} Position
💰 **Quantity:** {quantity:.4f}
📊 **Price:** ${current_price:.4f}
💎 **Position Value:** ${position_value:.2f}
🔥 **Order ID:** {order_result.get('orderId')}

✅ **THE IMMORTAL CONSCIOUSNESS LIVES AND TRADES!**
🎉 **Real capital deployed on Binance Futures**"""
                    
                    telegram.send_message(message)
                    
                except Exception as e:
                    logger.warning(f"Could not send Telegram notification: {e}")
                
                return order_result
            else:
                return order_result
                
        except Exception as e:
            logger.error(f"Binance execution error: {e}")
            return {"error": str(e)}
