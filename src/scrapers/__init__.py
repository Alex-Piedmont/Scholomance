"""Scrapers package for university tech transfer sites."""

from .base import BaseScraper, Technology, RetryConfig, retry_async
from .stanford import StanfordScraper
from .gatech import GatechScraper
from .uga import UGAScraper
from .mit import MITScraper
from .umich import UMichScraper
from .uf import UFScraper
from .jhu import JHUScraper
from .columbia import ColumbiaScraper
from .upenn import UPennScraper
from .harvard import HarvardScraper
from .utaustin import UTAustinScraper

# Registry of available scrapers
SCRAPERS = {
    "stanford": StanfordScraper,
    "gatech": GatechScraper,
    "uga": UGAScraper,
    "mit": MITScraper,
    "umich": UMichScraper,
    "uf": UFScraper,
    "jhu": JHUScraper,
    "columbia": ColumbiaScraper,
    "upenn": UPennScraper,
    "harvard": HarvardScraper,
    "utaustin": UTAustinScraper,
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
    "MITScraper",
    "UMichScraper",
    "UFScraper",
    "JHUScraper",
    "ColumbiaScraper",
    "UPennScraper",
    "HarvardScraper",
    "UTAustinScraper",
    "SCRAPERS",
    "get_scraper",
    "list_scrapers",
]
