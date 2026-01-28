"""University of Southern California scraper using Flintbox API."""

from .flintbox_base import FlintboxScraper


class USCScraper(FlintboxScraper):
    """Scraper for University of Southern California's Flintbox technology portal."""

    BASE_URL = "https://usc.flintbox.com"
    UNIVERSITY_CODE = "usc"
    UNIVERSITY_NAME = "University of Southern California"
    ORGANIZATION_ID = "44"
    ACCESS_KEY = "a5abd881-d6b0-4479-872e-7035243d1eb6"
