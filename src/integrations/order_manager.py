"""
Order Manager Module for OCO (One-Cancels-Other) Order Management
"""

import os
import time
import logging
from typing import Dict, List, Optional, Tuple, Union
import threading

logger = logging.getLogger(__name__)

class OrderManager:
    """
    Manages OCO (One-Cancels-Other) orders and position tracking
    """
    
    def __init__(self, trading_api):
        """
        Initialize the order manager
        
        Args:
            trading_api: Trading API client
        """
        self.trading_api = trading_api
        self.open_orders = {}  # Maps symbol to list of {orderId, type, position_side}
        self.open_positions = {}  # Maps symbol to position details
        self.order_lock = threading.RLock()  # Thread-safe operations
        logger.info("Order manager initialized")
    
    def place_main_order_with_tpsl(self, symbol: str, direction: str, quantity: float, 
                                   entry_price: Optional[float] = None, 
                                   take_profit: Optional[float] = None,
                                   stop_loss: Optional[float] = None) -> Dict:
        """
        Place a main order with take-profit and stop-loss orders
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            direction: Trade direction ('LONG' or 'SHORT')
            quantity: Order quantity
            entry_price: Entry price (None for market order)
            take_profit: Take-profit price
            stop_loss: Stop-loss price
            
        Returns:
            Dict: Order result with all order IDs
        """
        # Standardize direction format for Bitget API
        position_side = "long" if direction.upper() == "LONG" else "short"
        
        # Validate symbol first to avoid wasting resources on invalid symbols
        # Use trading_api to check if the symbol exists on Bitget
        symbol_check = self.trading_api.get_current_price(symbol)
        if 'error' in symbol_check:
            logger.warning(f"Symbol {symbol} is not available on Bitget: {symbol_check.get('error')}")
            return {'main_order': {'error': f"Symbol {symbol} is not available: {symbol_check.get('error')}"}}
        
        # Place the main order
        order_type = "limit" if entry_price is not None else "market"
        main_order = self.trading_api.place_order(
            symbol=symbol,
            side=direction.lower(),
            quantity=quantity,
            price=entry_price,
            order_type=order_type,
            position_side=position_side  # Explicitly pass position side
        )
        
        if 'error' in main_order:
            logger.error(f"Failed to place main order: {main_order.get('error')}")
            return main_order
            
        # Get the order ID
        main_order_id = main_order.get('orderId', '')
        logger.info(f"Placed main {direction} order {main_order_id} for {symbol}")
        
        # Add main order to tracked orders
        with self.order_lock:
            if symbol not in self.open_orders:
                self.open_orders[symbol] = []
            
            self.open_orders[symbol].append({
                'orderId': main_order_id,
                'type': 'main',
                'position_side': position_side
            })
        
        # Wait for the position to be established before setting TP/SL
        # This ensures we have accurate position data
        max_wait = 10  # Maximum wait time in seconds
        position_established = False
        start_time = time.time()
        
        while not position_established and time.time() - start_time < max_wait:
            # Check if the position is established
            position = self.trading_api.get_position(symbol)
            if position and not position.get('error') and float(position.get('size', 0)) > 0:
                position_established = True
                logger.info(f"Position established for {symbol}: {position}")
                # Store position details
                with self.order_lock:
                    self.open_positions[symbol] = {
                        'size': float(position.get('size', 0)),
                        'position_side': position.get('holdSide', position_side),
                        'entry_price': float(position.get('entryPrice', 0))
                    }
                break
            time.sleep(1)  # Wait a second before checking again
        
        result = {
            'main_order': main_order,
            'take_profit_order': None,
            'stop_loss_order': None
        }
        
        # Place take-profit order if specified
        if take_profit is not None and position_established:
            # Use the actual position size for TP
            position_size = self.open_positions[symbol]['size']
            
            tp_order = self.trading_api.set_take_profit(
                symbol=symbol,
                quantity=position_size,
                price=take_profit,
                position_side=position_side
            )
            
            if 'error' in tp_order:
                logger.error(f"Failed to place take-profit order: {tp_order.get('error')}")
            else:
                tp_order_id = tp_order.get('orderId', '')
                logger.info(f"Placed take-profit order {tp_order_id} at {take_profit} for {symbol}")
                
                # Add TP order to tracked orders
                with self.order_lock:
                    self.open_orders[symbol].append({
                        'orderId': tp_order_id,
                        'type': 'take_profit',
                        'position_side': position_side
                    })
                
                result['take_profit_order'] = tp_order
        
        # Place stop-loss order if specified
        if stop_loss is not None and position_established:
            # Use the actual position size for SL
            position_size = self.open_positions[symbol]['size']
            
            sl_order = self.trading_api.set_stop_loss(
                symbol=symbol,
                quantity=position_size,
                stop_price=stop_loss,
                position_side=position_side
            )
            
            if 'error' in sl_order:
                logger.error(f"Failed to place stop-loss order: {sl_order.get('error')}")
            else:
                sl_order_id = sl_order.get('orderId', '')
                logger.info(f"Placed stop-loss order {sl_order_id} at {stop_loss} for {symbol}")
                
                # Add SL order to tracked orders
                with self.order_lock:
                    self.open_orders[symbol].append({
                        'orderId': sl_order_id,
                        'type': 'stop_loss',
                        'position_side': position_side
                    })
                
                result['stop_loss_order'] = sl_order
        
        return result
    
    def handle_order_filled(self, symbol: str, order_id: str, order_type: str) -> None:
        """
        Handle an order fill event - implement OCO logic
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            order_id: Order ID of the filled order
            order_type: Type of the filled order ('take_profit', 'stop_loss')
        """
        if order_type not in ['take_profit', 'stop_loss']:
            logger.warning(f"Unrecognized order type for OCO handling: {order_type}")
            return
            
        logger.info(f"Handling {order_type} fill for {symbol}, order ID: {order_id}")
        
        with self.order_lock:
            if symbol not in self.open_orders:
                logger.warning(f"No open orders found for {symbol}")
                return
                
            # Find the opposite order type to cancel
            opposite_type = "stop_loss" if order_type == "take_profit" else "take_profit"
            
            # Find orders to cancel
            orders_to_cancel = []
            position_side = None
            
            for order in self.open_orders[symbol]:
                if order['type'] == opposite_type:
                    orders_to_cancel.append(order['orderId'])
                    position_side = order.get('position_side')
            
            # Cancel the opposite orders
            for cancel_order_id in orders_to_cancel:
                try:
                    logger.info(f"OCO Logic: Cancelling {opposite_type} order {cancel_order_id} for {symbol}")
                    self.trading_api.cancel_order(symbol, cancel_order_id, position_side)
                except Exception as e:
                    logger.error(f"Failed to cancel {opposite_type} order {cancel_order_id}: {str(e)}")
            
            # Clean up the filled order and any cancelled orders from our tracking
            self.open_orders[symbol] = [order for order in self.open_orders[symbol] 
                                     if order['orderId'] != order_id and order['orderId'] not in orders_to_cancel]
            
            # If no orders left, clean up the position data too
            if not self.open_orders[symbol]:
                if symbol in self.open_positions:
                    del self.open_positions[symbol]
                del self.open_orders[symbol]
    
    def update_position_status(self) -> None:
        """
        Update the status of all open positions and handle closed positions
        Should be called periodically to keep position tracking accurate
        """
        with self.order_lock:
            for symbol in list(self.open_positions.keys()):
                try:
                    position = self.trading_api.get_position(symbol)
                    
                    # If position no longer exists or size is 0, handle position close
                    if position.get('error') or float(position.get('size', 0)) <= 0:
                        logger.info(f"Position closed for {symbol}")
                        
                        # Cancel any remaining orders
                        if symbol in self.open_orders:
                            for order in self.open_orders[symbol]:
                                try:
                                    self.trading_api.cancel_order(
                                        symbol, 
                                        order['orderId'], 
                                        order.get('position_side')
                                    )
                                    logger.info(f"Cancelled order {order['orderId']} after position close")
                                except Exception as e:
                                    logger.warning(f"Failed to cancel order {order['orderId']}: {str(e)}")
                            
                            # Clean up tracking data
                            del self.open_orders[symbol]
                        
                        # Remove from open positions
                        del self.open_positions[symbol]
                    
                except Exception as e:
                    logger.warning(f"Failed to update position for {symbol}: {str(e)}")
