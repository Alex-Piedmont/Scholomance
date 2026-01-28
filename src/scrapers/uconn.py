"""University of Connecticut scraper using Flintbox API."""

from .flintbox_base import FlintboxScraper


class UConnScraper(FlintboxScraper):
    """Scraper for University of Connecticut's Flintbox technology portal."""

    BASE_URL = "https://uconn.flintbox.com"
    UNIVERSITY_CODE = "uconn"
    UNIVERSITY_NAME = "University of Connecticut"
    ORGANIZATION_ID = "106"
    ACCESS_KEY = "c9a1cb21-6c5e-437c-9662-9492efa1205a"
