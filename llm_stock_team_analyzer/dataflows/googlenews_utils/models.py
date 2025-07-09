"""
Data models for Google News utilities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class NewsArticle:
    """Model for a single news article."""

    title: str
    link: str
    snippet: str
    date: str
    source: str

    def __post_init__(self):
        """Validate and clean data after initialization."""
        self.title = self.title.strip() if self.title else ""
        self.snippet = self.snippet.strip() if self.snippet else ""
        self.source = self.source.strip() if self.source else ""
        self.date = self.date.strip() if self.date else ""


@dataclass
class NewsSearchResult:
    """Model for search results."""

    query: str
    start_date: str
    end_date: str
    articles: List[NewsArticle]
    total_results: int
    pages_scraped: int

    @classmethod
    def create_empty(
        cls, query: str, start_date: str, end_date: str
    ) -> "NewsSearchResult":
        """Create empty search result."""
        return cls(
            query=query,
            start_date=start_date,
            end_date=end_date,
            articles=[],
            total_results=0,
            pages_scraped=0,
        )


@dataclass
class ScrapingConfig:
    """Configuration for scraping behavior."""

    max_pages: int = 1
    max_articles: int = 3
    delay_min: float = 2.0
    delay_max: float = 6.0
    max_retries: int = 5
    timeout: int = 30
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/101.0.4951.54 Safari/537.36"
    )
