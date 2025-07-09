"""
Custom exceptions for yfinance utilities.
"""


class YFinanceError(Exception):
    """Base exception for YFinance related errors."""

    pass


class TickerNotFoundError(YFinanceError):
    """Exception raised when ticker symbol is not found."""

    pass


class DataRetrievalError(YFinanceError):
    """Exception raised when data retrieval fails."""

    pass


class EmptyDataError(YFinanceError):
    """Exception raised when no data is returned."""

    pass
