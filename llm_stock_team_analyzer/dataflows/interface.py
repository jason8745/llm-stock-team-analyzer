"""
Interface module for stock market data retrieval and analysis.

This module provides clean, stateless functions for:
- Google News scraping
- Stock data retrieval via yfinance
- Technical indicator calculations

All functions are designed to be robust, testable, and suitable for offline operation.
"""

from datetime import datetime
from typing import Annotated

import pandas as pd
from dateutil.relativedelta import relativedelta

# Import our local modules
from .googlenews_utils import getNewsData
from .indicators import (
    calculate_atr,
    calculate_bollinger_bands,
    calculate_macd,
    calculate_rsi,
)
from .yfinance_utils import YFinanceService


def get_google_news(
    query: Annotated[
        str,
        "Search query for Google News (e.g., 'AAPL Apple stock'). Use company ticker and name for best results. ONE CALL retrieves ALL relevant news for the query and date range.",
    ],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[
        int,
        "Number of days to look back from curr_date (typically 7-14 days is sufficient for comprehensive news coverage)",
    ],
) -> str:
    """
    Retrieve comprehensive Google News data for a specific query and date range.

    IMPORTANT: This function returns ALL available news articles for the given query and date range
    in a SINGLE CALL. Do NOT call this function multiple times with the same parameters as it will
    return the same results. If you need different news topics, use different search queries.

    Args:
        query: Search query string. For stock analysis, use format like "AAPL Apple stock" or "company_name earnings"
        curr_date: End date for news search in YYYY-MM-DD format
        look_back_days: Days to look back (7-14 days typically provides comprehensive coverage)

    Returns:
        Formatted string containing ALL news articles found for the query and date range.
        Returns empty string if no news found. Each article includes title, source, and snippet.

    Usage Tips:
        - ONE call per unique query/date combination is sufficient
        - Use specific, relevant search terms for better results
        - 7-14 days lookback typically provides comprehensive news coverage
        - Do NOT make multiple calls with identical parameters
    """
    query = query.replace(" ", "+")

    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    news_results = getNewsData(query, before, curr_date)

    news_str = ""

    for news in news_results:
        news_str += (
            f"### {news['title']} (source: {news['source']}) \n\n{news['snippet']}\n\n"
        )

    if len(news_results) == 0:
        return ""

    return f"## {query} Google News, from {before} to {curr_date}:\n\n{news_str}"


def get_stock_stats_indicators_window(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[
        str, "The current trading date you are trading on, YYYY-mm-dd"
    ],
    look_back_days: Annotated[int, "how many days to look back"],
    online: Annotated[bool, "to fetch data online or offline (both use yfinance)"],
) -> str:
    """
    Calculate and return technical indicators for a stock over a specified time window.

    Args:
        symbol: Stock ticker symbol
        indicator: Technical indicator name (see supported indicators below)
        curr_date: Current date in YYYY-mm-dd format
        look_back_days: Number of days to look back
        online: Whether to use online mode (both modes use yfinance for robustness)

    Returns:
        Formatted string with indicator values and description
    """

    # Supported indicators with descriptions
    supported_indicators = {
        # Moving Averages
        "close_50_sma": (
            "50 SMA: A medium-term trend indicator. "
            "Usage: Identify trend direction and serve as dynamic support/resistance. "
            "Tips: It lags price; combine with faster indicators for timely signals."
        ),
        "close_200_sma": (
            "200 SMA: A long-term trend benchmark. "
            "Usage: Confirm overall market trend and identify golden/death cross setups. "
            "Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries."
        ),
        "close_10_ema": (
            "10 EMA: A responsive short-term average. "
            "Usage: Capture quick shifts in momentum and potential entry points. "
            "Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals."
        ),
        # MACD Related
        "macd": (
            "MACD: Computes momentum via differences of EMAs. "
            "Usage: Look for crossovers and divergence as signals of trend changes. "
            "Tips: Confirm with other indicators in low-volatility or sideways markets."
        ),
        "macds": (
            "MACD Signal: An EMA smoothing of the MACD line. "
            "Usage: Use crossovers with the MACD line to trigger trades. "
            "Tips: Should be part of a broader strategy to avoid false positives."
        ),
        "macdh": (
            "MACD Histogram: Shows the gap between the MACD line and its signal. "
            "Usage: Visualize momentum strength and spot divergence early. "
            "Tips: Can be volatile; complement with additional filters in fast-moving markets."
        ),
        # Momentum Indicators
        "rsi": (
            "RSI: Measures momentum to flag overbought/oversold conditions. "
            "Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. "
            "Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis."
        ),
        # Volatility Indicators
        "boll": (
            "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. "
            "Usage: Acts as a dynamic benchmark for price movement. "
            "Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals."
        ),
        "boll_ub": (
            "Bollinger Upper Band: Typically 2 standard deviations above the middle line. "
            "Usage: Signals potential overbought conditions and breakout zones. "
            "Tips: Confirm signals with other tools; prices may ride the band in strong trends."
        ),
        "boll_lb": (
            "Bollinger Lower Band: Typically 2 standard deviations below the middle line. "
            "Usage: Indicates potential oversold conditions. "
            "Tips: Use additional analysis to avoid false reversal signals."
        ),
        "atr": (
            "ATR: Averages true range to measure volatility. "
            "Usage: Set stop-loss levels and adjust position sizes based on current market volatility. "
            "Tips: It's a reactive measure, so use it as part of a broader risk management strategy."
        ),
        # Volume-Based Indicators
        "vwma": (
            "VWMA: A moving average weighted by volume. "
            "Usage: Confirm trends by integrating price action with volume data. "
            "Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses."
        ),
        "mfi": (
            "MFI: The Money Flow Index is a momentum indicator that uses both price and volume to measure buying and selling pressure. "
            "Usage: Identify overbought (>80) or oversold (<20) conditions and confirm the strength of trends or reversals. "
            "Tips: Use alongside RSI or MACD to confirm signals; divergence between price and MFI can indicate potential reversals."
        ),
    }

    if indicator not in supported_indicators:
        raise ValueError(
            f"Indicator {indicator} is not supported. Please choose from: {list(supported_indicators.keys())}"
        )

    try:
        # Calculate the start date based on look_back_days (add extra days for indicator calculation)
        end_date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date_obj = end_date_obj - relativedelta(days=look_back_days + 60)
        start_date = start_date_obj.strftime("%Y-%m-%d")

        # Get stock data using our yfinance utilities
        stock_data = YFinanceService.get_stock_data(symbol, start_date, curr_date)

        if stock_data is None or stock_data.empty:
            return f"No data available for {symbol} in the specified date range."

        # Standardize column names to lowercase for consistent access
        stock_data.columns = stock_data.columns.str.lower()

        # Remove timezone info from index for cleaner datetime operations
        if stock_data.index.tz is not None:
            stock_data.index = stock_data.index.tz_localize(None)

        # Calculate the technical indicator
        data_with_indicator = _calculate_indicator(stock_data.copy(), indicator)

        if data_with_indicator is None:
            return f"Failed to calculate indicator {indicator}"

        # Filter to the requested date range for display
        display_start = end_date_obj - relativedelta(days=look_back_days)
        display_data = data_with_indicator[data_with_indicator.index >= display_start]

        # Format the results
        result_lines = []
        for date, row in display_data.iterrows():
            date_str = date.strftime("%Y-%m-%d")
            indicator_values = _get_indicator_values(row, indicator)
            result_lines.append(f"{date_str}: {indicator_values}")

        result_str = (
            f"## {indicator} values from {display_start.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
            + "\n".join(result_lines)
            + "\n\n"
            + supported_indicators.get(indicator, "No description available.")
        )

        return result_str

    except Exception as e:
        return f"Error calculating indicator {indicator} for {symbol}: {str(e)}"


def _calculate_indicator(data: pd.DataFrame, indicator: str) -> pd.DataFrame:
    """Calculate the specified technical indicator using our indicators.py functions"""
    try:
        if indicator == "close_50_sma":
            data["close_50_sma"] = data["close"].rolling(window=50).mean()

        elif indicator == "close_200_sma":
            data["close_200_sma"] = data["close"].rolling(window=200).mean()

        elif indicator == "close_10_ema":
            data["close_10_ema"] = data["close"].ewm(span=10, adjust=False).mean()

        elif indicator in ["macd", "macds", "macdh"]:
            data = calculate_macd(data)
            if indicator == "macdh":
                data["macdh"] = data["macd"] - data["signal_line"]

        elif indicator == "rsi":
            data = calculate_rsi(data)

        elif indicator in ["boll", "boll_ub", "boll_lb"]:
            data = calculate_bollinger_bands(data)

        elif indicator == "atr":
            data = calculate_atr(data)

        elif indicator == "vwma":
            # Calculate VWMA (Volume Weighted Moving Average)
            window = 20
            data["vwma"] = (data["close"] * data["volume"]).rolling(
                window=window
            ).sum() / data["volume"].rolling(window=window).sum()

        elif indicator == "mfi":
            # Calculate Money Flow Index (basic implementation)
            typical_price = (data["high"] + data["low"] + data["close"]) / 3
            money_flow = typical_price * data["volume"]

            # Positive and negative money flow
            positive_flow = (
                money_flow.where(typical_price > typical_price.shift(1), 0)
                .rolling(window=14)
                .sum()
            )
            negative_flow = (
                money_flow.where(typical_price < typical_price.shift(1), 0)
                .rolling(window=14)
                .sum()
            )

            money_ratio = positive_flow / negative_flow
            data["mfi"] = 100 - (100 / (1 + money_ratio))

        return data

    except Exception as e:
        print(f"Error calculating indicator {indicator}: {e}")
        return None


def _get_indicator_values(row: pd.Series, indicator: str) -> str:
    """Extract and format the indicator values from a data row"""
    try:
        if indicator == "close_50_sma":
            value = row.get("close_50_sma", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "close_200_sma":
            value = row.get("close_200_sma", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "close_10_ema":
            value = row.get("close_10_ema", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "macd":
            macd_val = row.get("macd", "N/A")
            return f"{macd_val:.4f}" if pd.notna(macd_val) else "N/A"

        elif indicator == "macds":
            signal_val = row.get("signal_line", "N/A")
            return f"{signal_val:.4f}" if pd.notna(signal_val) else "N/A"

        elif indicator == "macdh":
            macdh_val = row.get("macdh", "N/A")
            return f"{macdh_val:.4f}" if pd.notna(macdh_val) else "N/A"

        elif indicator == "rsi":
            rsi_val = row.get("rsi", "N/A")
            return f"{rsi_val:.2f}" if pd.notna(rsi_val) else "N/A"

        elif indicator == "boll":
            value = row.get("bollinger_middle", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "boll_ub":
            value = row.get("bollinger_upper", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "boll_lb":
            value = row.get("bollinger_lower", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "atr":
            value = row.get("atr", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "vwma":
            value = row.get("vwma", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "mfi":
            value = row.get("mfi", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        return "N/A"

    except Exception:
        return "N/A"


def get_stock_price_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Get stock price data for the specified symbol and date range.

    Args:
        symbol: Stock ticker symbol
        start_date: Start date in YYYY-mm-dd format
        end_date: End date in YYYY-mm-dd format

    Returns:
        Formatted string with stock price data
    """
    try:
        # Validate date formats
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")

        # Get stock data using our yfinance utilities
        data = YFinanceService.get_stock_data(symbol, start_date, end_date)

        # Check if data is empty
        if data is None or data.empty:
            return f"No data found for symbol '{symbol}' between {start_date} and {end_date}"

        # Standardize column names to lowercase for consistent access
        data.columns = data.columns.str.lower()

        # Remove timezone info from index for cleaner output
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)

        # Round numerical values to 2 decimal places for cleaner display
        numeric_columns = ["open", "high", "low", "close", "adj_close"]
        for col in numeric_columns:
            if col in data.columns:
                data[col] = data[col].round(2)

        # Convert DataFrame to CSV string
        csv_string = data.to_csv()

        # Add header information
        header = f"# Stock data for {symbol.upper()} from {start_date} to {end_date}\n"
        header += f"# Total records: {len(data)}\n"
        header += (
            f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        return header + csv_string

    except Exception as e:
        return f"Error retrieving data for {symbol}: {str(e)}"
