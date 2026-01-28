"""Utah State University scraper using Flintbox API."""

from .flintbox_base import FlintboxScraper


class USUScraper(FlintboxScraper):
    """Scraper for Utah State University's Flintbox technology portal."""

    BASE_URL = "https://usu.flintbox.com"
    UNIVERSITY_CODE = "usu"
    UNIVERSITY_NAME = "Utah State University"
    ORGANIZATION_ID = "198"
    ACCESS_KEY = "6af4c512-15e2-4213-bb3f-3b7e904a0e43"
