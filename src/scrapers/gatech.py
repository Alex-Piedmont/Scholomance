"""Georgia Tech Flintbox scraper using their API."""

from .flintbox_base import FlintboxScraper


class GatechScraper(FlintboxScraper):
    """Scraper for Georgia Tech's Flintbox technology portal."""

    BASE_URL = "https://gatech.flintbox.com"
    UNIVERSITY_CODE = "gatech"
    UNIVERSITY_NAME = "Georgia Tech Flintbox"
    ORGANIZATION_ID = "186"
    ACCESS_KEY = "803ec38e-0986-4610-af3c-fbb9084a1a43"
