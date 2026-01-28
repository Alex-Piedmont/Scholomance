"""Wisconsin Alumni Research Foundation (WARF) scraper using Technology Publisher API."""

from .techpub_base import TechPublisherScraper


class WARFScraper(TechPublisherScraper):
    """
    Scraper for WARF's Express Licensing technology portal.

    WARF manages technology transfer for the University of Wisconsin-Madison,
    with 2,000+ patented technologies available for licensing.
    """

    BASE_URL = "https://expresslicensing.warf.org"
    UNIVERSITY_CODE = "warf"
    UNIVERSITY_NAME = "Wisconsin Alumni Research Foundation"

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(delay_seconds=delay_seconds)
