"""University of Washington CoMotion scraper using Technology Publisher API."""

from .techpub_base import TechPublisherScraper


class UWScraper(TechPublisherScraper):
    """
    Scraper for University of Washington's CoMotion technology portal.

    CoMotion is UW's innovation hub, offering technologies across categories
    including cleantech, software, therapeutics, and research tools.
    """

    BASE_URL = "https://els2.comotion.uw.edu"
    UNIVERSITY_CODE = "uw"
    UNIVERSITY_NAME = "University of Washington CoMotion"

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(delay_seconds=delay_seconds)
