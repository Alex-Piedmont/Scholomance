"""University of Louisville scraper using Flintbox API."""

from .flintbox_base import FlintboxScraper


class LouisvilleScraper(FlintboxScraper):
    """Scraper for University of Louisville's Flintbox technology portal."""

    BASE_URL = "https://louisville.flintbox.com"
    UNIVERSITY_CODE = "louisville"
    UNIVERSITY_NAME = "University of Louisville"
    ORGANIZATION_ID = "28"
    ACCESS_KEY = "a4d8f8a8-6e05-4f69-aeb3-a41213e75405"
