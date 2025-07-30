"""
Integration tests for Telegram notifications
"""
import pytest
import responses
from unittest.mock import Mock, patch

# Import Telegram integrations to test
try:
    from src.integrations.telegram import TelegramNotifier
    from src.integrations.telegram_commands import TelegramCommands
except ImportError:
    # Fallback for different project structure
    from Inside.Bar.Strategy.src.integrations.telegram import TelegramNotifier
    from Inside.Bar.Strategy.src.integrations.telegram_commands import TelegramCommands


class TestTelegramNotifier:
    """Test Telegram notification system"""
    
    @pytest.fixture
    def telegram_notifier(self):
        """Create a Telegram notifier for testing"""
        return TelegramNotifier('test_bot_token', 'test_chat_id')
    
    @responses.activate
    def test_send_message(self, telegram_notifier):
        """Test sending a simple message"""
        mock_response = {
            'ok': True,
            'result': {
                'message_id': 123,
                'chat': {'id': 456},
                'text': 'Test message'
            }
        }
        
        responses.add(
            responses.POST,
            f'https://api.telegram.org/bot{telegram_notifier.bot_token}/sendMessage',
            json=mock_response,
            status=200
        )
        
        result = telegram_notifier.send_message('Test message')
        
        assert result['ok'] is True
        assert result['result']['message_id'] == 123
    
    @responses.activate
    def test_send_signal_notification(self, telegram_notifier):
        """Test sending a trading signal notification"""
        mock_response = {
            'ok': True,
            'result': {
                'message_id': 124,
                'chat': {'id': 456},
                'text': 'Signal notification'
            }
        }
        
        responses.add(
            responses.POST,
            f'https://api.telegram.org/bot{telegram_notifier.bot_token}/sendMessage',
            json=mock_response,
            status=200
        )
        
        test_signal = {
            'symbol': 'BTC/USDT',
            'direction': 'LONG',
            'timeframe': '1h',
            'strategy': 'supertrend_adx',
            'strategy_name': 'SuperTrend ADX',
            'confidence': 95.0,
            'price': 39000.0,
            'profit_target': 42000.0,
            'stop_loss': 38000.0,
            'atr': 500.0,
            'win_probability': 92.5
        }
        
        result = telegram_notifier.send_signal_notification(test_signal)
        
        assert result['ok'] is True
        assert 'error' not in result
    
    @responses.activate
    def test_send_low_price_signal(self, telegram_notifier):
        """Test sending a signal for low price crypto"""
        mock_response = {
            'ok': True,
            'result': {
                'message_id': 125,
                'chat': {'id': 456},
                'text': 'Low price signal'
            }
        }
        
        responses.add(
            responses.POST,
            f'https://api.telegram.org/bot{telegram_notifier.bot_token}/sendMessage',
            json=mock_response,
            status=200
        )
        
        test_signal = {
            'symbol': 'DOGE/USDT',
            'direction': 'LONG',
            'timeframe': '1h',
            'strategy': 'supertrend_adx',
            'strategy_name': 'SuperTrend ADX',
            'confidence': 92.0,
            'price': 0.12345,
            'profit_target': 0.15000,
            'stop_loss': 0.11000,
            'atr': 0.005,
            'win_probability': 90.5
        }
        
        result = telegram_notifier.send_signal_notification(test_signal)
        
        assert result['ok'] is True
        assert 'error' not in result
    
    @responses.activate
    def test_telegram_error_handling(self, telegram_notifier):
        """Test error handling in Telegram API calls"""
        mock_response = {
            'ok': False,
            'error_code': 400,
            'description': 'Bad Request'
        }
        
        responses.add(
            responses.POST,
            f'https://api.telegram.org/bot{telegram_notifier.bot_token}/sendMessage',
            json=mock_response,
            status=400
        )
        
        result = telegram_notifier.send_message('Test message')
        
        assert result['ok'] is False
        assert 'error_code' in result
    
    def test_telegram_configuration(self, telegram_notifier):
        """Test Telegram configuration validation"""
        assert telegram_notifier.bot_token == 'test_bot_token'
        assert telegram_notifier.chat_id == 'test_chat_id'
        assert telegram_notifier.is_configured is True
    
    def test_telegram_unconfigured(self):
        """Test Telegram notifier when not configured"""
        notifier = TelegramNotifier(None, None)
        assert notifier.is_configured is False


class TestTelegramCommands:
    """Test Telegram bot commands"""
    
    @pytest.fixture
    def telegram_commands(self):
        """Create Telegram commands handler for testing"""
        return TelegramCommands('test_bot_token', 'test_chat_id')
    
    def test_commands_initialization(self, telegram_commands):
        """Test Telegram commands initialization"""
        assert hasattr(telegram_commands, 'start')
        assert hasattr(telegram_commands, 'stop')
        assert hasattr(telegram_commands, 'status')
    
    def test_available_commands(self, telegram_commands):
        """Test that all expected commands are available"""
        methods = [m for m in dir(telegram_commands) if not m.startswith('_')]
        
        expected_commands = ['start', 'stop', 'status', 'help']
        for cmd in expected_commands:
            assert cmd in methods
    
    @responses.activate
    def test_start_command(self, telegram_commands):
        """Test start command execution"""
        mock_response = {
            'ok': True,
            'result': {
                'message_id': 126,
                'chat': {'id': 456},
                'text': 'Bot started'
            }
        }
        
        responses.add(
            responses.POST,
            f'https://api.telegram.org/bot{telegram_commands.bot_token}/sendMessage',
            json=mock_response,
            status=200
        )
        
        result = telegram_commands.start()
        
        assert result['ok'] is True
    
    @responses.activate
    def test_status_command(self, telegram_commands):
        """Test status command execution"""
        mock_response = {
            'ok': True,
            'result': {
                'message_id': 127,
                'chat': {'id': 456},
                'text': 'Bot status'
            }
        }
        
        responses.add(
            responses.POST,
            f'https://api.telegram.org/bot{telegram_commands.bot_token}/sendMessage',
            json=mock_response,
            status=200
        )
        
        result = telegram_commands.status()
        
        assert result['ok'] is True


class TestTelegramIntegrationEndToEnd:
    """End-to-end tests for Telegram integration"""
    
    @responses.activate
    def test_complete_notification_flow(self):
        """Test complete notification flow from signal to message"""
        # Mock Telegram API responses
        mock_response = {
            'ok': True,
            'result': {
                'message_id': 128,
                'chat': {'id': 456},
                'text': 'Complete notification flow'
            }
        }
        
        responses.add(
            responses.POST,
            'https://api.telegram.org/bottest_token/sendMessage',
            json=mock_response,
            status=200
        )
        
        # Create notifier and send notification
        notifier = TelegramNotifier('test_token', 'test_chat_id')
        
        test_signal = {
            'symbol': 'BTC/USDT',
            'direction': 'LONG',
            'timeframe': '1h',
            'strategy': 'supertrend_adx',
            'confidence': 95.0,
            'price': 39000.0,
            'profit_target': 42000.0,
            'stop_loss': 38000.0,
            'win_probability': 92.5
        }
        
        result = notifier.send_signal_notification(test_signal)
        
        assert result['ok'] is True
        assert result['result']['message_id'] == 128
    
    def test_notification_formatting(self):
        """Test that notifications are properly formatted"""
        notifier = TelegramNotifier('test_token', 'test_chat_id')
        
        test_signal = {
            'symbol': 'BTC/USDT',
            'direction': 'LONG',
            'strategy_name': 'SuperTrend ADX',
            'confidence': 95.0,
            'price': 39000.0,
            'profit_target': 42000.0,
            'stop_loss': 38000.0,
            'win_probability': 92.5
        }
        
        # Test message formatting (this would test the internal formatting logic)
        formatted_message = notifier._format_signal_message(test_signal)
        
        assert 'BTC/USDT' in formatted_message
        assert 'LONG' in formatted_message
        assert '95.0' in formatted_message
        assert 'SuperTrend ADX' in formatted_message
    
    def test_notification_caching(self):
        """Test notification caching to prevent spam"""
        # This would test that duplicate notifications are cached
        # and not sent repeatedly
        pass 