"""
Google News scraping utilities package.
"""

from .exceptions import (
    GoogleNewsError,
    InvalidDateFormatError,
    ParseError,
    RateLimitError,
    ScrapingError,
)
from .models import (
    NewsArticle,
    NewsSearchResult,
    ScrapingConfig,
)
from .utils import (
    GoogleNewsClient,
    GoogleNewsHTMLParser,
    getNewsData,  # For backward compatibility
    search_google_news,
    validate_date_format,
)

__all__ = [
    # Main classes
    "GoogleNewsClient",
    "GoogleNewsHTMLParser",
    # Utility functions
    "search_google_news",
    "validate_date_format",
    # Models
    "NewsArticle",
    "NewsSearchResult",
    "ScrapingConfig",
    # Exceptions
    "GoogleNewsError",
    "RateLimitError",
    "ScrapingError",
    "ParseError",
    "InvalidDateFormatError",
    # Backward compatibility
    "getNewsData",
]
