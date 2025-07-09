"""
YFinance utilities package.
"""

from .exceptions import (
    DataRetrievalError,
    EmptyDataError,
    TickerNotFoundError,
    YFinanceError,
)
from .models import AnalystRecommendation, StockInfo
from .utils import (
    YFinanceService,
    fetch_kline_data,
    fetch_stock_info,
    get_basic_stock_metrics,
    get_stock_price_history,
    handle_yfinance_errors,
    validate_ticker_symbol,
    yfinance_utils,
)

__all__ = [
    # Main service
    "YFinanceService",
    # Utility functions
    "validate_ticker_symbol",
    "handle_yfinance_errors",
    "fetch_kline_data",
    "fetch_stock_info",
    "get_stock_price_history",
    "get_basic_stock_metrics",
    # Models
    "StockInfo",
    "AnalystRecommendation",
    # Exceptions
    "YFinanceError",
    "TickerNotFoundError",
    "DataRetrievalError",
    "EmptyDataError",
    # Backward compatibility
    "yfinance_utils",
]
