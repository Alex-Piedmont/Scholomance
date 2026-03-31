"""University of Illinois Urbana-Champaign OTM scraper using Flintbox API."""

from .flintbox_base import FlintboxScraper


class UIUCScraper(FlintboxScraper):
    """Scraper for UIUC's Flintbox technology portal."""

    BASE_URL = "https://illinois.flintbox.com"
    UNIVERSITY_CODE = "uiuc"
    UNIVERSITY_NAME = "UIUC Office of Technology Management"
    ORGANIZATION_ID = "31"
    ACCESS_KEY = "f80b8917-1613-4c29-8925-ca33c89e7e08"
