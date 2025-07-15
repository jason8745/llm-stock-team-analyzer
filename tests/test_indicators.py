"""
Unit tests for technical indicators.
Focus on core functionality and edge cases.
"""

import pandas as pd

from llm_stock_team_analyzer.dataflows.indicators import (
    calculate_bollinger_bands,
    calculate_macd,
    calculate_moving_averages,
    calculate_rsi,
)


class TestMovingAverages:
    """Test moving average calculations."""

    def test_basic_moving_averages(self, sample_stock_data):
        """Test that moving averages are calculated correctly."""
        df = sample_stock_data.copy()
        df.columns = df.columns.str.lower()  # Convert to lowercase

        result = calculate_moving_averages(df)

        # Check new columns exist
        assert "5ma" in result.columns
        assert "10ma" in result.columns
        assert "20ma" in result.columns

        # Check values are calculated (no NaN after warmup period)
        assert not result["5ma"].iloc[4:].isna().any()
        assert not result["10ma"].iloc[9:].isna().any()
        assert not result["20ma"].iloc[19:].isna().any()

    def test_moving_averages_simple_data(self):
        """Test with simple known data."""
        df = pd.DataFrame({"close": [10, 12, 14, 16, 18]})

        result = calculate_moving_averages(df)

        # 5-day MA at last position should be mean of all values
        expected = (10 + 12 + 14 + 16 + 18) / 5
        assert abs(result["5ma"].iloc[-1] - expected) < 0.001


class TestBollingerBands:
    """Test Bollinger Bands calculations."""

    def test_bollinger_bands_structure(self, sample_stock_data):
        """Test that Bollinger bands have correct structure."""
        df = sample_stock_data.copy()
        df.columns = df.columns.str.lower()

        result = calculate_bollinger_bands(df)

        # Check columns exist
        assert "bollinger_middle" in result.columns
        assert "bollinger_upper" in result.columns
        assert "bollinger_lower" in result.columns

        # Check logical relationship: upper >= middle >= lower
        valid_data = result.iloc[19:]  # After 20-day window
        assert (valid_data["bollinger_upper"] >= valid_data["bollinger_middle"]).all()
        assert (valid_data["bollinger_middle"] >= valid_data["bollinger_lower"]).all()


class TestRSI:
    """Test RSI calculations."""

    def test_rsi_range(self, sample_stock_data):
        """Test that RSI values are within valid range."""
        df = sample_stock_data.copy()
        df.columns = df.columns.str.lower()

        result = calculate_rsi(df)

        assert "rsi" in result.columns

        # RSI should be between 0 and 100
        valid_rsi = result["rsi"].dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_uptrend(self):
        """Test RSI behavior in uptrend."""
        # Create strong uptrend
        df = pd.DataFrame(
            {
                "close": list(range(100, 130))  # Consistent uptrend
            }
        )

        result = calculate_rsi(df)

        # In uptrend, RSI should trend higher
        final_rsi = result["rsi"].iloc[-1]
        assert final_rsi > 50


class TestMACD:
    """Test MACD calculations."""

    def test_macd_components(self, sample_stock_data):
        """Test MACD calculation components."""
        df = sample_stock_data.copy()
        df.columns = df.columns.str.lower()

        result = calculate_macd(df)

        # Check all components exist
        assert "ema_short" in result.columns
        assert "ema_long" in result.columns
        assert "macd" in result.columns
        assert "signal_line" in result.columns

        # MACD should equal short EMA - long EMA
        expected_macd = result["ema_short"] - result["ema_long"]
        pd.testing.assert_series_equal(result["macd"], expected_macd, check_names=False)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_dataframe(self):
        """Test with empty dataframe."""
        df = pd.DataFrame({"close": []})
        result = calculate_moving_averages(df)
        assert len(result) == 0
        assert "5ma" in result.columns

    def test_single_value(self):
        """Test with single value."""
        df = pd.DataFrame({"close": [100]})
        result = calculate_moving_averages(df)
        assert len(result) == 1
        # Single value should give NaN for most indicators
        assert pd.isna(result["5ma"].iloc[0])

    def test_constant_values(self):
        """Test with constant prices."""
        df = pd.DataFrame({"close": [100] * 30, "high": [100] * 30, "low": [100] * 30})

        result = calculate_bollinger_bands(df)

        # With constant prices, bands should converge
        valid_data = result.iloc[19:]
        assert (valid_data["bollinger_upper"] == valid_data["bollinger_middle"]).all()
        assert (valid_data["bollinger_lower"] == valid_data["bollinger_middle"]).all()
