"""UGA Flintbox scraper using their API."""

from .flintbox_base import FlintboxScraper


class UGAScraper(FlintboxScraper):
    """Scraper for UGA's Flintbox technology portal."""

    BASE_URL = "https://uga.flintbox.com"
    UNIVERSITY_CODE = "uga"
    UNIVERSITY_NAME = "UGA Flintbox"
    ORGANIZATION_ID = "11"
    ACCESS_KEY = "28c03bda-3676-41d6-bf18-22101ac1dbc5"
