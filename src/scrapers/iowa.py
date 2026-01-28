"""University of Iowa scraper using Flintbox API."""

from .flintbox_base import FlintboxScraper


class IowaScraper(FlintboxScraper):
    """Scraper for University of Iowa's Flintbox technology portal."""

    BASE_URL = "https://uiowa.flintbox.com"
    UNIVERSITY_CODE = "iowa"
    UNIVERSITY_NAME = "University of Iowa"
    ORGANIZATION_ID = "42"
    ACCESS_KEY = "3fc3085f-bc68-4c36-b0d2-03136e9f46bc"
