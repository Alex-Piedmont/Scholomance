"""Purdue Research Foundation scraper using Technology Publisher API."""

from .techpub_base import TechPublisherScraper


class PurdueScraper(TechPublisherScraper):
    """
    Scraper for Purdue Research Foundation's technology licensing portal.

    Purdue's Office of Technology Commercialization manages 400+ technologies
    across fields including AI/ML, biotechnology, semiconductors, and aerospace.
    """

    BASE_URL = "https://licensing.prf.org"
    UNIVERSITY_CODE = "purdue"
    UNIVERSITY_NAME = "Purdue Research Foundation"

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(delay_seconds=delay_seconds)
