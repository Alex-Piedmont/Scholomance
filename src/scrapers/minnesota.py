"""University of Minnesota Technology Commercialization scraper using Technology Publisher API."""

from .techpub_base import TechPublisherScraper


class MinnesotaScraper(TechPublisherScraper):
    """
    Scraper for University of Minnesota's Technology Commercialization portal.

    UMN is a leader in technology transfer with 3,200+ current licenses,
    offering technologies in agriculture, engineering, life sciences, and software.
    """

    BASE_URL = "https://license.umn.edu"
    UNIVERSITY_CODE = "minnesota"
    UNIVERSITY_NAME = "University of Minnesota Technology Commercialization"

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(delay_seconds=delay_seconds)
