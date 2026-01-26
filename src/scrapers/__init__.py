"""Scrapers package for university tech transfer sites."""

from .base import BaseScraper, Technology, RetryConfig, retry_async
from .stanford import StanfordScraper
from .gatech import GatechScraper
from .uga import UGAScraper

# Registry of available scrapers
SCRAPERS = {
    "stanford": StanfordScraper,
    "gatech": GatechScraper,
    "uga": UGAScraper,
}


def get_scraper(university_code: str) -> BaseScraper:
    """Get a scraper instance for the given university code."""
    if university_code not in SCRAPERS:
        raise ValueError(f"Unknown university: {university_code}. Available: {list(SCRAPERS.keys())}")
    return SCRAPERS[university_code]()


def list_scrapers() -> list[dict]:
    """List all available scrapers with their details."""
    result = []
    for code, scraper_class in SCRAPERS.items():
        scraper = scraper_class()
        result.append({
            "code": code,
            "name": scraper.name,
            "base_url": scraper.base_url,
        })
    return result


__all__ = [
    "BaseScraper",
    "Technology",
    "RetryConfig",
    "retry_async",
    "StanfordScraper",
    "GatechScraper",
    "UGAScraper",
    "SCRAPERS",
    "get_scraper",
    "list_scrapers",
]
