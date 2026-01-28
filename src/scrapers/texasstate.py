"""Texas State University scraper using RSS feed."""

from .rss_base import RSSBaseScraper


class TexasStateScraper(RSSBaseScraper):
    """Scraper for Texas State University's technology licensing portal."""

    BASE_URL = "https://txstate.technologypublisher.com"
    UNIVERSITY_CODE = "texasstate"
    UNIVERSITY_NAME = "Texas State University"
