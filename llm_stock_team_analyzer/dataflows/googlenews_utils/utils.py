"""
Google News scraping utilities - Refactored for better maintainability and error handling.
"""

import json
import random
import time
from datetime import datetime
from functools import wraps
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
)

from llm_stock_team_analyzer.utils.logger import log

from .exceptions import (
    GoogleNewsError,
    InvalidDateFormatError,
    ParseError,
    RateLimitError,
    ScrapingError,
)
from .models import NewsArticle, NewsSearchResult, ScrapingConfig


def validate_date_format(date_str: str) -> str:
    """
    Validate and convert date format to MM/DD/YYYY.

    Args:
        date_str: Date string in YYYY-MM-DD or MM/DD/YYYY format

    Returns:
        Date string in MM/DD/YYYY format

    Raises:
        InvalidDateFormatError: If date format is invalid
    """
    try:
        if "-" in date_str:
            # Convert YYYY-MM-DD to MM/DD/YYYY
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%m/%d/%Y")
        elif "/" in date_str:
            # Validate MM/DD/YYYY format
            datetime.strptime(date_str, "%m/%d/%Y")
            return date_str
        else:
            raise InvalidDateFormatError(f"Invalid date format: {date_str}")
    except ValueError as e:
        raise InvalidDateFormatError(f"Invalid date format: {date_str}. Error: {e}")


def handle_scraping_errors(func):
    """Decorator to handle common scraping errors."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            log.error(f"Request error in {func.__name__}: {e}")
            raise ScrapingError(f"Network error: {e}")
        except Exception as e:
            if isinstance(
                e, (GoogleNewsError, RateLimitError, ScrapingError, ParseError)
            ):
                raise
            log.error(f"Unexpected error in {func.__name__}: {e}")
            raise GoogleNewsError(f"Unexpected error: {e}")

    return wrapper


class GoogleNewsHTMLParser:
    """Parser for Google News HTML content."""

    @staticmethod
    def parse_article_element(element) -> Optional[NewsArticle]:
        """
        Parse a single article element from Google News HTML.

        Args:
            element: BeautifulSoup element containing article data

        Returns:
            NewsArticle object or None if parsing fails
        """
        try:
            # Extract article information with fallbacks
            link_elem = element.find("a")
            title_elem = element.select_one("div.MBeuO")
            snippet_elem = element.select_one(".GI74Re")
            date_elem = element.select_one(".LfVVr")
            source_elem = element.select_one(".NUnG9d span")

            # Check if all required elements are present
            if not all([link_elem, title_elem]):
                log.warning("Missing required elements in article")
                return None

            # Truncate snippet to save tokens (limit to ~50 chars)
            snippet_text = snippet_elem.get_text(strip=True) if snippet_elem else ""
            if len(snippet_text) > 50:
                snippet_text = snippet_text[:50] + "..."

            # Truncate title to save tokens (limit to ~80 chars)
            title_text = title_elem.get_text(strip=True) if title_elem else ""
            if len(title_text) > 80:
                title_text = title_text[:80] + "..."

            return NewsArticle(
                link=link_elem.get("href", ""),
                title=title_text,
                snippet=snippet_text,
                date=date_elem.get_text(strip=True) if date_elem else "",
                source=source_elem.get_text(strip=True) if source_elem else "",
            )

        except Exception as e:
            log.warning(f"Error parsing article element: {e}")
            return None

    @staticmethod
    def extract_articles_from_page(soup: BeautifulSoup) -> List[NewsArticle]:
        """
        Extract all articles from a Google News search results page.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            List of NewsArticle objects
        """
        articles = []
        results_elements = soup.select("div.SoaBEf")

        if not results_elements:
            log.warning("No article elements found on page")
            return articles

        for element in results_elements:
            article = GoogleNewsHTMLParser.parse_article_element(element)
            if article:
                articles.append(article)

        return articles

    @staticmethod
    def has_next_page(soup: BeautifulSoup) -> bool:
        """Check if there's a next page available."""
        next_link = soup.find("a", id="pnnext")
        return next_link is not None


class GoogleNewsClient:
    """Client for scraping Google News with improved error handling and rate limiting."""

    def __init__(self, config: Optional[ScrapingConfig] = None):
        """
        Initialize the Google News client.

        Args:
            config: Scraping configuration, uses default if None
        """
        self.config = config or ScrapingConfig()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config.user_agent})

    def _is_rate_limited(self, response: requests.Response) -> bool:
        """Check if the response indicates rate limiting."""
        return response.status_code == 429

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        stop=stop_after_attempt(5),
    )
    @handle_scraping_errors
    def _make_request(self, url: str) -> requests.Response:
        """
        Make a request with retry logic for rate limiting.

        Args:
            url: URL to request

        Returns:
            Response object

        Raises:
            RateLimitError: If rate limited
            ScrapingError: If request fails
        """
        # Random delay to avoid detection
        delay = random.uniform(self.config.delay_min, self.config.delay_max)
        time.sleep(delay)

        try:
            response = self.session.get(url, timeout=self.config.timeout)

            if self._is_rate_limited(response):
                raise RateLimitError("Rate limited by Google")

            response.raise_for_status()
            return response

        except requests.exceptions.Timeout:
            raise ScrapingError("Request timeout")
        except requests.exceptions.RequestException as e:
            raise ScrapingError(f"Request failed: {e}")

    def _build_search_url(
        self, query: str, start_date: str, end_date: str, page: int = 0
    ) -> str:
        """
        Build Google News search URL.

        Args:
            query: Search query
            start_date: Start date in MM/DD/YYYY format
            end_date: End date in MM/DD/YYYY format
            page: Page number (0-based)

        Returns:
            Complete search URL
        """
        offset = page * 10
        encoded_query = quote_plus(query)

        return (
            f"https://www.google.com/search?q={encoded_query}"
            f"&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}"
            f"&tbm=nws&start={offset}"
        )

    @handle_scraping_errors
    def search_news(
        self,
        query: str,
        start_date: str,
        end_date: str,
        max_pages: Optional[int] = None,
    ) -> NewsSearchResult:
        """
        Search Google News for articles matching the query and date range.

        Args:
            query: Search query string
            start_date: Start date (YYYY-MM-DD or MM/DD/YYYY)
            end_date: End date (YYYY-MM-DD or MM/DD/YYYY)
            max_pages: Maximum pages to scrape (uses config default if None)

        Returns:
            NewsSearchResult object containing all found articles

        Raises:
            InvalidDateFormatError: If date format is invalid
            ScrapingError: If scraping fails
            GoogleNewsError: For other errors
        """
        # Validate and convert dates
        try:
            start_date_formatted = validate_date_format(start_date)
            end_date_formatted = validate_date_format(end_date)
        except InvalidDateFormatError:
            raise

        max_pages = max_pages or self.config.max_pages
        result = NewsSearchResult.create_empty(query, start_date, end_date)
        page = 0

        log.info(
            f"Starting Google News search for query: '{query}' from {start_date} to {end_date}"
        )

        while page < max_pages:
            try:
                url = self._build_search_url(
                    query, start_date_formatted, end_date_formatted, page
                )
                log.debug(f"Scraping page {page + 1}: {url}")

                response = self._make_request(url)
                soup = BeautifulSoup(response.content, "html.parser")

                # Extract articles from current page
                articles = GoogleNewsHTMLParser.extract_articles_from_page(soup)

                if not articles:
                    log.info(f"No articles found on page {page + 1}, stopping search")
                    break

                # Check if adding these articles would exceed max_articles limit
                current_total = len(result.articles)
                if current_total + len(articles) > self.config.max_articles:
                    # Only add articles up to the limit
                    remaining_slots = self.config.max_articles - current_total
                    articles = articles[:remaining_slots]
                    result.articles.extend(articles)
                    result.pages_scraped = page + 1
                    log.info(
                        f"Reached max articles limit ({self.config.max_articles}), stopping search"
                    )
                    break

                result.articles.extend(articles)
                result.pages_scraped = page + 1

                log.info(f"Found {len(articles)} articles on page {page + 1}")

                # Check if there's a next page
                if not GoogleNewsHTMLParser.has_next_page(soup):
                    log.info("No more pages available")
                    break

                page += 1

            except RateLimitError:
                log.warning(f"Rate limited on page {page + 1}, stopping search")
                break
            except ScrapingError as e:
                log.error(f"Scraping error on page {page + 1}: {e}")
                break
            except Exception as e:
                log.error(f"Unexpected error on page {page + 1}: {e}")
                break

        result.total_results = len(result.articles)
        log.info(
            f"Search completed. Found {result.total_results} articles across {result.pages_scraped} pages"
        )

        return result

    def close(self):
        """Close the session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Backward compatibility function
def getNewsData(query: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Legacy function for backward compatibility.

    Args:
        query: Search query
        start_date: Start date (YYYY-MM-DD or MM/DD/YYYY)
        end_date: End date (YYYY-MM-DD or MM/DD/YYYY)

    Returns:
        List of dictionaries containing article data
    """
    try:
        with GoogleNewsClient() as client:
            result = client.search_news(query, start_date, end_date)

            # Convert NewsArticle objects to dictionaries for backward compatibility
            return [
                {
                    "link": article.link,
                    "title": article.title,
                    "snippet": article.snippet,
                    "date": article.date,
                    "source": article.source,
                }
                for article in result.articles
            ]
    except Exception as e:
        log.error(f"Error in getNewsData: {e}")
        return []


# Convenience functions
def search_google_news(
    query: str,
    start_date: str,
    end_date: str,
    max_pages: int = 2,
    max_articles: int = 8,
) -> NewsSearchResult:
    """
    Convenient function to search Google News.

    Args:
        query: Search query
        start_date: Start date (YYYY-MM-DD or MM/DD/YYYY)
        end_date: End date (YYYY-MM-DD or MM/DD/YYYY)
        max_pages: Maximum pages to scrape (default: 2 for token conservation)
        max_articles: Maximum articles to return (default: 8 for token conservation)

    Returns:
        NewsSearchResult object
    """
    config = ScrapingConfig(max_pages=max_pages, max_articles=max_articles)
    with GoogleNewsClient(config) as client:
        return client.search_news(query, start_date, end_date)
