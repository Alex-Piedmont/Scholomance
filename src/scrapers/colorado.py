"""University of Colorado scraper using Flintbox API."""

from .flintbox_base import FlintboxScraper


class ColoradoScraper(FlintboxScraper):
    """Scraper for University of Colorado's Flintbox technology portal."""

    BASE_URL = "https://colorado.flintbox.com"
    UNIVERSITY_CODE = "colorado"
    UNIVERSITY_NAME = "University of Colorado"
    ORGANIZATION_ID = "178"
    ACCESS_KEY = "28ee410e-269a-4878-a58d-9c3b211860cf"
