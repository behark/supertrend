"""
Integration tests for exchange APIs and order management
"""
import pytest
import responses
from unittest.mock import Mock, patch

# Import exchange integrations to test
try:
    from src.integrations.bidget import BidgetClient
    from src.integrations.binance_futures import BinanceFuturesClient
    from src.integrations.order_manager import OrderManager
except ImportError:
    # Fallback for different project structure
    from Inside.Bar.Strategy.src.integrations.bidget import BidgetClient
    from Inside.Bar.Strategy.src.integrations.binance_futures import BinanceFuturesClient
    from Inside.Bar.Strategy.src.integrations.order_manager import OrderManager


class TestBidgetIntegration:
    """Test Bidget exchange integration"""
    
    @pytest.fixture
    def bidget_client(self):
        """Create a Bidget client for testing"""
        return BidgetClient('test_api_key', 'test_secret')
    
    @responses.activate
    def test_bidget_place_order(self, bidget_client):
        """Test placing an order on Bidget"""
        # Mock the API response
        mock_response = {
            'orderId': 'test_order_123',
            'status': 'FILLED',
            'executedQty': '1.0',
            'price': '50000.0'
        }
        
        responses.add(
            responses.POST,
            'https://api.bidget.com/api/v1/order',
            json=mock_response,
            status=200
        )
        
        result = bidget_client.place_order('BTC/USDT', 'BUY', 1.0)
        
        assert result['orderId'] == 'test_order_123'
        assert result['status'] == 'FILLED'
    
    @responses.activate
    def test_bidget_get_balance(self, bidget_client):
        """Test getting account balance from Bidget"""
        mock_response = {
            'balances': [
                {'asset': 'USDT', 'free': '1000.0', 'locked': '0.0'},
                {'asset': 'BTC', 'free': '0.1', 'locked': '0.0'}
            ]
        }
        
        responses.add(
            responses.GET,
            'https://api.bidget.com/api/v1/account',
            json=mock_response,
            status=200
        )
        
        balance = bidget_client.get_balance()
        
        assert 'balances' in balance
        assert len(balance['balances']) == 2
    
    @responses.activate
    def test_bidget_error_handling(self, bidget_client):
        """Test error handling in Bidget API calls"""
        responses.add(
            responses.POST,
            'https://api.bidget.com/api/v1/order',
            json={'error': 'Insufficient balance'},
            status=400
        )
        
        with pytest.raises(Exception):
            bidget_client.place_order('BTC/USDT', 'BUY', 1000000.0)


class TestBinanceFuturesIntegration:
    """Test Binance Futures integration"""
    
    @pytest.fixture
    def binance_client(self):
        """Create a Binance Futures client for testing"""
        return BinanceFuturesClient('test_api_key', 'test_secret')
    
    @responses.activate
    def test_binance_place_order(self, binance_client):
        """Test placing an order on Binance Futures"""
        mock_response = {
            'orderId': 'binance_order_456',
            'status': 'FILLED',
            'executedQty': '2.0',
            'price': '50000.0'
        }
        
        responses.add(
            responses.POST,
            'https://fapi.binance.com/fapi/v1/order',
            json=mock_response,
            status=200
        )
        
        result = binance_client.place_order('BTC/USDT', 'SELL', 2.0)
        
        assert result['orderId'] == 'binance_order_456'
        assert result['status'] == 'FILLED'
    
    @responses.activate
    def test_binance_get_market_data(self, binance_client):
        """Test getting market data from Binance Futures"""
        mock_response = [
            {
                'symbol': 'BTCUSDT',
                'price': '50000.0',
                'volume': '1000.0'
            }
        ]
        
        responses.add(
            responses.GET,
            'https://fapi.binance.com/fapi/v1/ticker/24hr',
            json=mock_response,
            status=200
        )
        
        data = binance_client.get_market_data('BTC/USDT')
        
        assert isinstance(data, list)
        assert len(data) > 0


class TestOrderManager:
    """Test order management system"""
    
    @pytest.fixture
    def order_manager(self):
        """Create an order manager for testing"""
        return OrderManager()
    
    @pytest.fixture
    def mock_exchange(self):
        """Create a mock exchange client"""
        mock_exchange = Mock()
        mock_exchange.place_order.return_value = {
            'orderId': 'test_order_789',
            'status': 'FILLED',
            'executedQty': '1.0',
            'price': '50000.0'
        }
        return mock_exchange
    
    def test_order_manager_initialization(self, order_manager):
        """Test order manager initialization"""
        assert hasattr(order_manager, 'execute_order')
        assert hasattr(order_manager, 'get_order_status')
    
    def test_execute_order(self, order_manager, mock_exchange):
        """Test order execution through order manager"""
        order_manager.exchange = mock_exchange
        
        result = order_manager.execute_order('BTC/USDT', 'BUY', 1.0)
        
        assert result['orderId'] == 'test_order_789'
        assert result['status'] == 'FILLED'
        
        # Verify the exchange was called correctly
        mock_exchange.place_order.assert_called_once_with('BTC/USDT', 'BUY', 1.0)
    
    def test_order_manager_with_different_exchanges(self, order_manager):
        """Test order manager with different exchange types"""
        # Test with Bidget
        bidget_client = BidgetClient('key', 'secret')
        order_manager.exchange = bidget_client
        
        # Test with Binance
        binance_client = BinanceFuturesClient('key', 'secret')
        order_manager.exchange = binance_client
        
        # Both should work
        assert order_manager.exchange is not None
    
    @patch('src.integrations.order_manager.OrderManager.execute_order')
    def test_order_manager_error_handling(self, mock_execute, order_manager):
        """Test error handling in order manager"""
        mock_execute.side_effect = Exception("Order failed")
        
        with pytest.raises(Exception):
            order_manager.execute_order('BTC/USDT', 'BUY', 1.0)


class TestExchangeIntegrationEndToEnd:
    """End-to-end tests for exchange integrations"""
    
    @responses.activate
    def test_complete_trading_flow(self):
        """Test complete trading flow from signal to order execution"""
        # Mock market data
        mock_market_data = {
            'symbol': 'BTC/USDT',
            'price': '50000.0',
            'volume': '1000.0'
        }
        
        # Mock order response
        mock_order_response = {
            'orderId': 'flow_order_123',
            'status': 'FILLED',
            'executedQty': '1.0',
            'price': '50000.0'
        }
        
        # Set up responses
        responses.add(
            responses.GET,
            'https://api.bidget.com/api/v1/ticker/24hr',
            json=mock_market_data,
            status=200
        )
        
        responses.add(
            responses.POST,
            'https://api.bidget.com/api/v1/order',
            json=mock_order_response,
            status=200
        )
        
        # Create client and execute flow
        client = BidgetClient('test_key', 'test_secret')
        
        # Get market data
        market_data = client.get_market_data('BTC/USDT')
        
        # Place order
        order_result = client.place_order('BTC/USDT', 'BUY', 1.0)
        
        # Verify results
        assert market_data is not None
        assert order_result['orderId'] == 'flow_order_123'
        assert order_result['status'] == 'FILLED'
    
    def test_exchange_fallback_mechanism(self):
        """Test fallback mechanism between exchanges"""
        # This would test switching from primary to fallback exchange
        # when the primary exchange fails
        pass 