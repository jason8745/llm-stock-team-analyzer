"""
Custom exceptions for Google News scraping utilities.
"""


class GoogleNewsError(Exception):
    """Base exception for Google News related errors."""

    pass


class RateLimitError(GoogleNewsError):
    """Exception raised when rate limited by Google."""

    pass


class ScrapingError(GoogleNewsError):
    """Exception raised when scraping fails."""

    pass


class ParseError(GoogleNewsError):
    """Exception raised when parsing HTML fails."""

    pass


class InvalidDateFormatError(GoogleNewsError):
    """Exception raised when date format is invalid."""

    pass
