"""Princeton University Office of Technology Licensing scraper using RSS feed."""

from .rss_base import RSSBaseScraper


class PrincetonScraper(RSSBaseScraper):
    """Scraper for Princeton University's technology licensing portal."""

    BASE_URL = "https://puotl.technologypublisher.com"
    UNIVERSITY_CODE = "princeton"
    UNIVERSITY_NAME = "Princeton University Office of Technology Licensing"
