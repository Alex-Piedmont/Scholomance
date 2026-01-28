"""University of Central Florida scraper using Flintbox API."""

from .flintbox_base import FlintboxScraper


class UCFScraper(FlintboxScraper):
    """Scraper for University of Central Florida's Flintbox technology portal."""

    BASE_URL = "https://ucf.flintbox.com"
    UNIVERSITY_CODE = "ucf"
    UNIVERSITY_NAME = "University of Central Florida"
    ORGANIZATION_ID = "82"
    ACCESS_KEY = "735da6c7-5d27-4015-bb46-60b45f80225d"
