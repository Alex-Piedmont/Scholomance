"""Carnegie Mellon University CTTEC scraper using Flintbox API."""

from .flintbox_base import FlintboxScraper


class CMUScraper(FlintboxScraper):
    """Scraper for Carnegie Mellon University's Flintbox technology portal."""

    BASE_URL = "https://cmu.flintbox.com"
    UNIVERSITY_CODE = "cmu"
    UNIVERSITY_NAME = "Carnegie Mellon CTTEC"
    ORGANIZATION_ID = "18"
    ACCESS_KEY = "c6a38f07-02cb-4ecb-88b2-a4cbb1b10702"
