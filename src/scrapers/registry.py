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
        delay_seconds=0.5,
    ),
    UniversityConfig(
        code="mit",
        name="Massachusetts Institute of Technology",
        base_url="https://tlo.mit.edu",
        scraper_class="MITScraper",
        delay_seconds=1.0,
    ),
    UniversityConfig(
        code="umich",
        name="University of Michigan",
        base_url="https://available-inventions.umich.edu",
        scraper_class="UMichScraper",
        delay_seconds=0.5,
    ),
    UniversityConfig(
        code="uf",
        name="University of Florida",
        base_url="https://ufinnovate.technologypublisher.com",
        scraper_class="UFScraper",
        delay_seconds=0.5,
    ),
    UniversityConfig(
        code="jhu",
        name="Johns Hopkins University",
        base_url="https://jhu.technologypublisher.com",
        scraper_class="JHUScraper",
        delay_seconds=0.5,
    ),
    UniversityConfig(
        code="columbia",
        name="Columbia University",
        base_url="https://inventions.techventures.columbia.edu",
        scraper_class="ColumbiaScraper",
        delay_seconds=0.2,
    ),
    UniversityConfig(
        code="upenn",
        name="University of Pennsylvania",
        base_url="https://upenn.technologypublisher.com",
        scraper_class="UPennScraper",
        delay_seconds=0.2,
    ),
    UniversityConfig(
        code="harvard",
        name="Harvard University",
        base_url="https://otd.harvard.edu",
        scraper_class="HarvardScraper",
        delay_seconds=0.5,
    ),
    UniversityConfig(
        code="utaustin",
        name="University of Texas at Austin",
        base_url="https://utotc.technologypublisher.com",
        scraper_class="UTAustinScraper",
        delay_seconds=0.2,
    ),
    UniversityConfig(
        code="ucsystem",
        name="University of California System",
        base_url="https://techtransfer.universityofcalifornia.edu",
        scraper_class="UCSystemScraper",
        delay_seconds=0.3,
    ),
    UniversityConfig(
        code="cornell",
        name="Cornell University",
        base_url="https://cornell.flintbox.com",
        scraper_class="CornellScraper",
        delay_seconds=0.5,
    ),
    UniversityConfig(
        code="cmu",
        name="Carnegie Mellon University",
        base_url="https://cmu.flintbox.com",
        scraper_class="CMUScraper",
        delay_seconds=0.5,
    ),
    UniversityConfig(
        code="uiuc",
        name="University of Illinois Urbana-Champaign",
        base_url="https://illinois.flintbox.com",
        scraper_class="UIUCScraper",
        delay_seconds=0.5,
    ),
    UniversityConfig(
        code="warf",
        name="Wisconsin Alumni Research Foundation",
        base_url="https://expresslicensing.warf.org",
        scraper_class="WARFScraper",
        delay_seconds=0.3,
    ),
    UniversityConfig(
        code="uw",
        name="University of Washington",
        base_url="https://els2.comotion.uw.edu",
        scraper_class="UWScraper",
        delay_seconds=0.3,
    ),
    UniversityConfig(
        code="purdue",
        name="Purdue University",
        base_url="https://licensing.prf.org",
        scraper_class="PurdueScraper",
        delay_seconds=0.3,
    ),
    UniversityConfig(
        code="minnesota",
        name="University of Minnesota",
        base_url="https://license.umn.edu",
        scraper_class="MinnesotaScraper",
        delay_seconds=0.3,
    ),
    UniversityConfig(
        code="northwestern",
        name="Northwestern University",
        base_url="https://inventions.invo.northwestern.edu",
        scraper_class="NorthwesternScraper",
        delay_seconds=0.3,
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
