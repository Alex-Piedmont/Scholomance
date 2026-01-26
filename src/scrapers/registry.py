"""Scraper registry configuration.

This module provides a centralized configuration for all university scrapers,
making it easy to add new universities or modify existing configurations.
"""

from dataclasses import dataclass, field
from typing import Optional, Type
import importlib

from .base import BaseScraper


@dataclass
class UniversityConfig:
    """Configuration for a university scraper."""

    code: str
    name: str
    base_url: str
    scraper_class: str  # Fully qualified class name or short name
    enabled: bool = True
    delay_seconds: float = 1.0
    max_pages: Optional[int] = None
    extra_config: dict = field(default_factory=dict)


# Default university configurations
UNIVERSITY_CONFIGS: list[UniversityConfig] = [
    UniversityConfig(
        code="stanford",
        name="Stanford University",
        base_url="https://techfinder.stanford.edu",
        scraper_class="StanfordScraper",
        delay_seconds=1.0,
    ),
    UniversityConfig(
        code="gatech",
        name="Georgia Institute of Technology",
        base_url="https://gatech.flintbox.com",
        scraper_class="GatechScraper",
        delay_seconds=0.5,
    ),
    UniversityConfig(
        code="uga",
        name="University of Georgia",
        base_url="https://uga.flintbox.com",
        scraper_class="UGAScraper",
        delay_seconds=1.5,  # Slightly slower for React app
    ),
]


def get_university_config(code: str) -> Optional[UniversityConfig]:
    """Get configuration for a specific university."""
    for config in UNIVERSITY_CONFIGS:
        if config.code == code:
            return config
    return None


def get_enabled_universities() -> list[UniversityConfig]:
    """Get all enabled university configurations."""
    return [config for config in UNIVERSITY_CONFIGS if config.enabled]


def get_scraper_for_config(config: UniversityConfig) -> BaseScraper:
    """
    Create a scraper instance from a university configuration.

    Args:
        config: University configuration

    Returns:
        Configured scraper instance
    """
    # Import the scraper class
    from . import SCRAPERS

    if config.code not in SCRAPERS:
        raise ValueError(f"No scraper registered for university: {config.code}")

    scraper_class = SCRAPERS[config.code]
    return scraper_class(delay_seconds=config.delay_seconds)


def add_university(config: UniversityConfig) -> None:
    """
    Add a new university configuration.

    Args:
        config: University configuration to add
    """
    # Check for duplicates
    for existing in UNIVERSITY_CONFIGS:
        if existing.code == config.code:
            raise ValueError(f"University with code '{config.code}' already exists")

    UNIVERSITY_CONFIGS.append(config)


def update_university(code: str, **kwargs) -> bool:
    """
    Update an existing university configuration.

    Args:
        code: University code to update
        **kwargs: Fields to update

    Returns:
        True if updated, False if not found
    """
    for config in UNIVERSITY_CONFIGS:
        if config.code == code:
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            return True
    return False


def disable_university(code: str) -> bool:
    """
    Disable a university (it won't be scraped with --all).

    Args:
        code: University code to disable

    Returns:
        True if disabled, False if not found
    """
    return update_university(code, enabled=False)


def enable_university(code: str) -> bool:
    """
    Enable a university.

    Args:
        code: University code to enable

    Returns:
        True if enabled, False if not found
    """
    return update_university(code, enabled=True)


def get_registry_info() -> dict:
    """Get summary information about the scraper registry."""
    enabled = get_enabled_universities()
    return {
        "total_universities": len(UNIVERSITY_CONFIGS),
        "enabled_universities": len(enabled),
        "universities": [
            {
                "code": c.code,
                "name": c.name,
                "base_url": c.base_url,
                "enabled": c.enabled,
            }
            for c in UNIVERSITY_CONFIGS
        ],
    }
