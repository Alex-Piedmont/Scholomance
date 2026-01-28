"""Michigan State University scraper using RSS feed."""

from .rss_base import RSSBaseScraper


class MichiganStateScraper(RSSBaseScraper):
    """Scraper for Michigan State University's technology licensing portal."""

    BASE_URL = "https://msut.technologypublisher.com"
    UNIVERSITY_CODE = "michiganstate"
    UNIVERSITY_NAME = "Michigan State University Technologies"
