"""
YFinance data retrieval service for stock OHLCV and info.
Refactored for better maintainability and error handling.
"""

from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional, Union

import pandas as pd
import yfinance as yf

from llm_stock_team_analyzer.utils.logger import log

from .exceptions import (
    DataRetrievalError,
    EmptyDataError,
    TickerNotFoundError,
    YFinanceError,
)
from .models import AnalystRecommendation, StockInfo


def validate_ticker_symbol(symbol: str) -> str:
    """Validate and clean ticker symbol."""
    if not symbol or not isinstance(symbol, str):
        raise ValueError("Ticker symbol must be a non-empty string")
    return symbol.strip().upper()


def handle_yfinance_errors(func):
    """Decorator to handle common yfinance errors."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except (YFinanceError, TickerNotFoundError, DataRetrievalError, EmptyDataError):
            # Re-raise our custom exceptions without wrapping
            raise
        except Exception as e:
            log.error(f"Error in {func.__name__}: {str(e)}")
            if "No data found" in str(e) or "Invalid ticker" in str(e):
                raise TickerNotFoundError(f"Ticker not found: {str(e)}")
            elif "Failed to download" in str(e) or "Connection" in str(e):
                raise DataRetrievalError(f"Failed to retrieve data: {str(e)}")
            else:
                raise YFinanceError(f"YFinance operation failed: {str(e)}")

    return wrapper


class YFinanceService:
    """Service class for Yahoo Finance data operations."""

    @staticmethod
    @handle_yfinance_errors
    def get_stock_data(
        symbol: str, start_date: str, end_date: str, period: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Retrieve stock price data for designated ticker symbol.

        Args:
            symbol: Ticker symbol (e.g., 'AAPL', '2330.TW')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            period: Alternative to start_date/end_date (e.g., '1y', '6mo')

        Returns:
            DataFrame with OHLCV data

        Raises:
            TickerNotFoundError: If ticker is not found
            DataRetrievalError: If data retrieval fails
        """
        symbol = validate_ticker_symbol(symbol)
        ticker = yf.Ticker(symbol)

        try:
            if period:
                data = ticker.history(period=period)
            else:
                # Add one day to end_date to make the range inclusive
                end_date_inclusive = (
                    pd.to_datetime(end_date) + pd.DateOffset(days=1)
                ).strftime("%Y-%m-%d")
                data = ticker.history(start=start_date, end=end_date_inclusive)

            if data.empty:
                raise EmptyDataError(f"No data available for {symbol}")

            return data

        except Exception as e:
            log.error(f"Failed to retrieve stock data for {symbol}: {e}")
            raise DataRetrievalError(f"Failed to retrieve stock data: {e}")

    @staticmethod
    @handle_yfinance_errors
    def get_stock_info(symbol: str) -> StockInfo:
        """
        Fetch basic stock information.

        Args:
            symbol: Ticker symbol

        Returns:
            StockInfo object with company details
        """
        symbol = validate_ticker_symbol(symbol)
        ticker = yf.Ticker(symbol)

        try:
            info = ticker.info
            if not info:
                raise EmptyDataError(f"No info available for {symbol}")
            return StockInfo.from_yfinance_info(symbol, info)
        except Exception as e:
            log.error(f"Failed to retrieve stock info for {symbol}: {e}")
            raise DataRetrievalError(f"Failed to retrieve stock info: {e}")

    @staticmethod
    @handle_yfinance_errors
    def get_company_info(symbol: str) -> pd.DataFrame:
        """
        Fetch company information as a DataFrame.

        Args:
            symbol: Ticker symbol

        Returns:
            DataFrame with company information
        """
        stock_info = YFinanceService.get_stock_info(symbol)

        company_data = {
            "Symbol": stock_info.symbol,
            "Company Name": stock_info.short_name or "N/A",
            "Industry": stock_info.industry or "N/A",
            "Sector": stock_info.sector or "N/A",
            "Country": stock_info.country or "N/A",
            "Website": stock_info.website or "N/A",
            "Market Cap": stock_info.market_cap,
            "P/E Ratio": stock_info.pe_ratio,
        }

        return pd.DataFrame([company_data])

    @staticmethod
    @handle_yfinance_errors
    def get_dividends(symbol: str) -> pd.DataFrame:
        """
        Fetch dividend history.

        Args:
            symbol: Ticker symbol

        Returns:
            DataFrame with dividend data
        """
        symbol = validate_ticker_symbol(symbol)
        ticker = yf.Ticker(symbol)

        try:
            dividends = ticker.dividends
            if dividends.empty:
                log.warning(f"No dividend data available for {symbol}")
            return dividends
        except Exception as e:
            log.error(f"Failed to retrieve dividends for {symbol}: {e}")
            raise DataRetrievalError(f"Failed to retrieve dividends: {e}")

    @staticmethod
    @handle_yfinance_errors
    def get_financials(symbol: str) -> Dict[str, pd.DataFrame]:
        """
        Fetch all financial statements.

        Args:
            symbol: Ticker symbol

        Returns:
            Dictionary containing income statement, balance sheet, and cash flow
        """
        symbol = validate_ticker_symbol(symbol)
        ticker = yf.Ticker(symbol)

        try:
            return {
                "income_statement": ticker.financials,
                "balance_sheet": ticker.balance_sheet,
                "cash_flow": ticker.cashflow,
            }
        except Exception as e:
            log.error(f"Failed to retrieve financials for {symbol}: {e}")
            raise DataRetrievalError(f"Failed to retrieve financials: {e}")

    @staticmethod
    @handle_yfinance_errors
    def get_analyst_recommendations(symbol: str) -> AnalystRecommendation:
        """
        Fetch analyst recommendations and return the most common one.

        Args:
            symbol: Ticker symbol

        Returns:
            AnalystRecommendation object with most common recommendation
        """
        symbol = validate_ticker_symbol(symbol)
        ticker = yf.Ticker(symbol)

        try:
            recommendations = ticker.recommendations

            if recommendations is None or recommendations.empty:
                log.warning(f"No analyst recommendations available for {symbol}")
                return AnalystRecommendation.create_empty()

            # Get the most recent recommendations (first row, excluding period column)
            latest_rec = recommendations.iloc[0, 1:]  # Skip period column

            if latest_rec.empty:
                return AnalystRecommendation.create_empty()

            # Find the recommendation with the highest count
            max_votes = latest_rec.max()
            majority_recommendations = latest_rec[
                latest_rec == max_votes
            ].index.tolist()

            return AnalystRecommendation(
                recommendation=majority_recommendations[0]
                if majority_recommendations
                else None,
                vote_count=int(max_votes) if pd.notna(max_votes) else 0,
            )

        except Exception as e:
            log.error(f"Failed to retrieve analyst recommendations for {symbol}: {e}")
            return AnalystRecommendation.create_empty()


# Standalone utility functions for backward compatibility and specific use cases


@handle_yfinance_errors
def fetch_kline_data(
    symbol: str,
    period: str = "3mo",
    interval: str = "1d",
    normalize_volume: bool = True,
) -> pd.DataFrame:
    """
    Fetch K-line (OHLCV) data from yfinance with improved error handling.

    Args:
        symbol: Ticker symbol (e.g., '2330.TW')
        period: Data period (e.g., '1d', '5d', '1mo', '3mo', '6mo', '1y')
        interval: Data interval (e.g., '1m', '5m', '1h', '1d')
        normalize_volume: Whether to normalize volume by dividing by 1000

    Returns:
        DataFrame with columns [open, high, low, close, volume] and timestamp index

    Raises:
        TickerNotFoundError: If ticker is not found
        DataRetrievalError: If data retrieval fails
        EmptyDataError: If no data is returned
    """
    symbol = validate_ticker_symbol(symbol)

    try:
        # Download data using yfinance
        data = yf.download(
            tickers=symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,  # Suppress progress bar
        )

        if data is None or data.empty:
            raise EmptyDataError(f"No data returned for {symbol}")

        # Handle MultiIndex columns (when downloading multiple tickers)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)

        # Standardize column names
        column_mapping = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        }

        # Check for missing expected columns
        expected_columns = list(column_mapping.keys())
        missing_columns = [col for col in expected_columns if col not in data.columns]

        if missing_columns:
            raise DataRetrievalError(
                f"Missing expected columns {missing_columns} in data for {symbol}"
            )

        # Rename columns to lowercase
        data = data.rename(columns=column_mapping)

        # Set index name
        data.index.name = "timestamp"

        # Select only required columns in specific order
        data = data[["open", "high", "low", "close", "volume"]]

        # Convert Series to DataFrame if necessary
        if isinstance(data, pd.Series):
            data = data.to_frame().T

        # Normalize data if requested
        if normalize_volume and "volume" in data.columns:
            data["volume"] = data["volume"] // 1000

        # Convert price columns to integers (removing decimals)
        price_columns = ["open", "high", "low", "close"]
        for col in price_columns:
            if col in data.columns:
                data[col] = data[col] // 1

        return data

    except Exception as e:
        if isinstance(e, (EmptyDataError, DataRetrievalError)):
            raise
        log.error(f"Error fetching K-line data for {symbol}: {e}")
        raise DataRetrievalError(f"Failed to fetch K-line data: {e}")


@handle_yfinance_errors
def fetch_stock_info(symbol: str) -> Dict[str, str]:
    """
    Fetch sector and industry info for a stock with improved error handling.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Dictionary with sector and industry information

    Raises:
        TickerNotFoundError: If ticker is not found
        DataRetrievalError: If data retrieval fails
    """
    symbol = validate_ticker_symbol(symbol)

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info:
            raise EmptyDataError(f"No info available for {symbol}")

        return {
            "sector": info.get("sector", "Unknown Sector"),
            "industry": info.get("industry", "Unknown Industry"),
        }

    except Exception as e:
        if isinstance(e, (EmptyDataError, DataRetrievalError)):
            raise
        log.error(f"Failed to get basic info for {symbol}: {e}")
        # Return default values instead of raising error for backward compatibility
        return {"sector": "Unknown Sector", "industry": "Unknown Industry"}


# Convenience functions for common operations
def get_stock_price_history(symbol: str, days: int = 30) -> pd.DataFrame:
    """Get stock price history for the last N days."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    return YFinanceService.get_stock_data(
        symbol=symbol,
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
    )


def get_basic_stock_metrics(symbol: str) -> Dict[str, Union[str, float, None]]:
    """Get basic stock metrics in a single call."""
    try:
        stock_info = YFinanceService.get_stock_info(symbol)
        return {
            "symbol": stock_info.symbol,
            "name": stock_info.short_name,
            "sector": stock_info.sector,
            "industry": stock_info.industry,
            "market_cap": stock_info.market_cap,
            "pe_ratio": stock_info.pe_ratio,
        }
    except Exception as e:
        log.error(f"Failed to get basic metrics for {symbol}: {e}")
        return {"symbol": symbol, "error": str(e)}


# Backward compatibility - create instance for legacy code
yfinance_utils = YFinanceService()
