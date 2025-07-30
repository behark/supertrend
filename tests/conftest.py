"""
Pytest configuration and common fixtures for SuperTrend tests
"""
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Add src directory to path for imports
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Add Inside=Bar:Strategy/src to path
strategy_src_path = project_root / "Inside=Bar:Strategy" / "src"
if strategy_src_path.exists():
    sys.path.insert(0, str(strategy_src_path))

@pytest.fixture(scope="session")
def test_data_dir():
    """Create a temporary directory for test data"""
    temp_dir = tempfile.mkdtemp(prefix="supertrend_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture(scope="session")
def sample_config():
    """Sample configuration for testing"""
    return {
        "symbols": ["BTC/USDT", "ETH/USDT"],
        "strategy": "supertrend_adx",
        "position_size_percent": 25.0,
        "max_signals_per_day": 15,
        "win_probability_threshold": 90.0,
        "use_fallback_api": False
    }

@pytest.fixture(scope="session")
def mock_exchange_response():
    """Mock exchange API response"""
    return {
        "orderId": "test_order_123",
        "status": "FILLED",
        "executedQty": "1.0",
        "price": "50000.0"
    }

@pytest.fixture(scope="session")
def mock_telegram_response():
    """Mock Telegram API response"""
    return {
        "ok": True,
        "result": {
            "message_id": 123,
            "chat": {"id": 456},
            "text": "Test message"
        }
    } 