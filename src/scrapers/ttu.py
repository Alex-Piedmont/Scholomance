"""Texas Tech University scraper using Flintbox API."""

from .flintbox_base import FlintboxScraper


class TTUScraper(FlintboxScraper):
    """Scraper for Texas Tech University's Flintbox technology portal."""

    BASE_URL = "https://ttu.flintbox.com"
    UNIVERSITY_CODE = "ttu"
    UNIVERSITY_NAME = "Texas Tech University"
    ORGANIZATION_ID = "23"
    ACCESS_KEY = "391d483e-dc4f-4be7-913d-1a63f683a47b"
