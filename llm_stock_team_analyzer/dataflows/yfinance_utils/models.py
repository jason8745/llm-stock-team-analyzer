"""
Data models for yfinance utilities.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class StockInfo:
    """Model for basic stock information."""

    symbol: str
    short_name: Optional[str] = None
    industry: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None
    website: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None

    @classmethod
    def from_yfinance_info(cls, symbol: str, info: Dict[str, Any]) -> "StockInfo":
        """Create StockInfo from yfinance ticker.info dict."""
        return cls(
            symbol=symbol,
            short_name=info.get("shortName"),
            industry=info.get("industry"),
            sector=info.get("sector"),
            country=info.get("country"),
            website=info.get("website"),
            market_cap=info.get("marketCap"),
            pe_ratio=info.get("trailingPE"),
        )


@dataclass
class AnalystRecommendation:
    """Model for analyst recommendation data."""

    recommendation: Optional[str]
    vote_count: int

    @classmethod
    def create_empty(cls) -> "AnalystRecommendation":
        """Create empty recommendation when no data is available."""
        return cls(recommendation=None, vote_count=0)
