"""
Unit tests for utility functions.
Tests basic validation and error handling without external dependencies.
"""
import pytest
from llm_stock_team_analyzer.dataflows.yfinance_utils.utils import validate_ticker_symbol


class TestTickerValidation:
    """Test ticker symbol validation."""
    
    def test_valid_ticker_symbols(self):
        """Test valid ticker symbols."""
        assert validate_ticker_symbol("AAPL") == "AAPL"
        assert validate_ticker_symbol("aapl") == "AAPL"  # Should uppercase
        assert validate_ticker_symbol(" MSFT ") == "MSFT"  # Should strip
        assert validate_ticker_symbol("tsla") == "TSLA"
    
    def test_invalid_ticker_symbols(self):
        """Test invalid ticker symbols."""
        with pytest.raises(ValueError):
            validate_ticker_symbol("")
        
        with pytest.raises(ValueError):
            validate_ticker_symbol(None)
        
        with pytest.raises(ValueError):
            validate_ticker_symbol(123)  # Not a string


class TestUtilityFunctions:
    """Test other utility functions that don't require external calls."""
    
    def test_basic_functionality(self):
        """Basic smoke test to ensure imports work."""
        # Just test that we can import the module without errors
        from llm_stock_team_analyzer.dataflows.yfinance_utils import utils
        assert hasattr(utils, 'validate_ticker_symbol')
        assert hasattr(utils, 'handle_yfinance_errors')
