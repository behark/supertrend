# SuperTrend Test Suite

This directory contains comprehensive unit, integration, and end-to-end tests for the SuperTrend trading bot.

## Test Structure

```
tests/
├── __init__.py                 # Package initialization
├── conftest.py                 # Pytest configuration and fixtures
├── run_tests.py               # Test runner script
├── README.md                  # This documentation
├── test_comprehensive_suite.py # Original comprehensive test suite
├── unit/                      # Unit tests
│   ├── test_indicators.py     # Technical indicator tests
│   └── test_strategies.py     # Trading strategy tests
├── integration/               # Integration tests
│   ├── test_exchange_integrations.py  # Exchange API tests
│   └── test_telegram_integration.py   # Telegram notification tests
└── e2e/                      # End-to-end tests (to be added)
```

## Running Tests

### Quick Start
```bash
# Run all tests
python tests/run_tests.py

# Run with verbose output
python tests/run_tests.py --verbose

# Run with coverage report
python tests/run_tests.py --coverage

# Run specific test types
python tests/run_tests.py --type unit
python tests/run_tests.py --type integration
python tests/run_tests.py --type comprehensive
```

### Using pytest directly
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_indicators.py

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run specific test class
pytest tests/unit/test_indicators.py::TestSupertrendIndicator
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Technical Indicators**: Test individual indicator calculations
  - Supertrend indicator
  - ADX (Average Directional Index)
  - ATR (Average True Range)
  - Inside bar pattern detection

- **Trading Strategies**: Test strategy logic in isolation
  - SuperTrend + ADX strategy
  - Inside Bar breakout strategy
  - Signal generation and validation

### Integration Tests (`tests/integration/`)
- **Exchange Integrations**: Test API interactions
  - Bidget exchange API
  - Binance Futures API
  - Order management system
  - Error handling and fallbacks

- **Telegram Notifications**: Test notification system
  - Message sending
  - Signal formatting
  - Command handling
  - Error scenarios

### End-to-End Tests (`tests/e2e/`)
- **Complete Trading Cycles**: Test full workflows
- **Dashboard Integration**: Test web interface
- **Process Management**: Test daemon and watchdog

## Test Coverage

The test suite covers:

### Core Components
- ✅ Technical indicators (Supertrend, ADX, ATR, Inside Bar)
- ✅ Trading strategies (SuperTrend + ADX, Inside Bar)
- ✅ Market data processing
- ✅ Signal generation and validation

### Integrations
- ✅ Exchange APIs (Bidget, Binance Futures)
- ✅ Telegram notifications
- ✅ Order management
- ✅ Configuration management

### Utilities
- ✅ Parameter management
- ✅ Playbook management
- ✅ Notification caching
- ✅ Analytics logging
- ✅ Health monitoring

### Dashboard
- ✅ Web application endpoints
- ✅ API routes
- ✅ Frontend components

## Test Data

### Sample OHLCV Data
Tests use generated sample data that mimics real market conditions:
- Realistic price movements
- Volume patterns
- Trend and volatility variations

### Mock Responses
Integration tests use mocked API responses to test:
- Successful API calls
- Error scenarios
- Network timeouts
- Invalid responses

## Configuration

### Environment Variables
Tests use test-specific environment variables:
- `TEST_MODE=true`
- `TEST_API_KEY=test_key`
- `TEST_API_SECRET=test_secret`

### Fixtures
Common test fixtures are defined in `conftest.py`:
- `test_data_dir`: Temporary directory for test data
- `sample_config`: Sample configuration for testing
- `mock_exchange_response`: Mock exchange API responses
- `mock_telegram_response`: Mock Telegram API responses

## Best Practices

### Writing Tests
1. **Descriptive Names**: Use clear, descriptive test names
2. **Single Responsibility**: Each test should test one thing
3. **Arrange-Act-Assert**: Structure tests with clear sections
4. **Edge Cases**: Test boundary conditions and error scenarios
5. **Mocking**: Use mocks for external dependencies

### Test Organization
1. **Group Related Tests**: Use test classes to group related functionality
2. **Consistent Naming**: Use consistent naming conventions
3. **Documentation**: Add docstrings to test classes and methods
4. **Fixtures**: Use fixtures for common setup and teardown

### Running Tests
1. **Regular Runs**: Run tests before committing changes
2. **Coverage**: Monitor test coverage regularly
3. **CI/CD**: Integrate tests into continuous integration
4. **Performance**: Monitor test execution time

## Troubleshooting

### Common Issues

#### Import Errors
```bash
# Ensure Python path includes project root
export PYTHONPATH="${PYTHONPATH}:/path/to/supertrend"
```

#### Missing Dependencies
```bash
# Install test dependencies
pip install -r requirements.txt
```

#### Test Failures
1. Check if the tested functionality has changed
2. Verify mock responses match actual API responses
3. Ensure test data is realistic and valid
4. Check for environment-specific issues

### Debugging Tests
```bash
# Run with debug output
pytest -v -s tests/

# Run specific failing test
pytest tests/unit/test_indicators.py::TestSupertrendIndicator::test_supertrend_output_format -v -s

# Use pdb for debugging
pytest --pdb tests/
```

## Contributing

When adding new tests:

1. **Follow Structure**: Place tests in appropriate directories
2. **Add Documentation**: Update this README if needed
3. **Update Coverage**: Ensure new code is covered by tests
4. **Test Locally**: Run tests before submitting changes
5. **Follow Patterns**: Use existing test patterns and conventions

## Coverage Goals

- **Unit Tests**: 90%+ coverage of core logic
- **Integration Tests**: 80%+ coverage of external integrations
- **End-to-End Tests**: Critical user workflows covered
- **Overall**: 85%+ total code coverage 