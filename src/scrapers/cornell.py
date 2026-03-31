"""Cornell University Center for Technology Licensing scraper using Flintbox API."""

from .flintbox_base import FlintboxScraper


class CornellScraper(FlintboxScraper):
    """Scraper for Cornell University's Flintbox technology portal."""

    BASE_URL = "https://cornell.flintbox.com"
    UNIVERSITY_CODE = "cornell"
    UNIVERSITY_NAME = "Cornell Center for Technology Licensing"
    ORGANIZATION_ID = "25"
    ACCESS_KEY = "09e7e6cd-845f-4bab-b079-58afbc2d2094"
