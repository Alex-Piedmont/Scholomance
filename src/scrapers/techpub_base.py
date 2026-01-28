"""Base scraper for Technology Publisher platform sites."""

import re
from typing import AsyncIterator, Optional

import aiohttp
from loguru import logger

from .base import BaseScraper, Technology


class TechPublisherScraper(BaseScraper):
    """
    Base scraper for sites using the Technology Publisher platform.

    Technology Publisher provides a standard API at /autocomplete/products
    that returns all technologies in a simple JSON format.

    Subclasses should set:
    - BASE_URL: The site's base URL
    - UNIVERSITY_CODE: Short code for the university
    - UNIVERSITY_NAME: Human-readable name
    """

    BASE_URL: str = ""
    UNIVERSITY_CODE: str = ""
    UNIVERSITY_NAME: str = ""

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(
            university_code=self.UNIVERSITY_CODE,
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return self.UNIVERSITY_NAME

    @property
    def api_url(self) -> str:
        """URL for the autocomplete API endpoint."""
        return f"{self.BASE_URL}/autocomplete/products"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug(f"HTTP session initialized for {self.UNIVERSITY_CODE}")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from the Technology Publisher API."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology list from API")

            # The autocomplete API returns all products when term is empty
            params = {"term": ""}

            async with self._session.get(self.api_url, params=params) as response:
                if response.status != 200:
                    self.log_error(f"API returned status {response.status}")
                    return

                data = await response.json()
                total = len(data)
                self.log_progress(f"Found {total} technologies")

                for i, item in enumerate(data):
                    tech = self._parse_item(item)
                    if tech:
                        self._tech_count += 1
                        yield tech

                    if (i + 1) % 100 == 0:
                        self.log_progress(f"Processed {i + 1}/{total} technologies")

            self._page_count = 1
            self.log_progress(f"Completed scraping: {self._tech_count} technologies")

        finally:
            await self._close_session()

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """
        Scrape technologies - Technology Publisher uses single API call.
        This method exists for interface compatibility.
        """
        if page_num != 1:
            return []

        technologies = []
        async for tech in self.scrape():
            technologies.append(tech)
        return technologies

    def _parse_item(self, item: dict) -> Optional[Technology]:
        """Parse a technology item from the API response."""
        try:
            name = item.get("name", "").strip()
            if not name:
                return None

            data_attrs = item.get("dataAttributes", {})
            tech_id = str(data_attrs.get("id", ""))
            url_path = data_attrs.get("url", "")

            # Build full URL
            url = f"{self.BASE_URL}/{url_path}" if url_path else ""

            raw_data = {
                "id": tech_id,
                "name": name,
                "url": url,
                "url_path": url_path,
            }

            return Technology(
                university=self.UNIVERSITY_CODE,
                tech_id=tech_id or re.sub(r"[^a-zA-Z0-9]+", "-", name.lower())[:50],
                title=name,
                url=url,
                description=None,  # Basic API doesn't include description
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing item: {e}")
            return None

    async def scrape_technology_detail(self, url: str) -> Optional[dict]:
        """
        Scrape detailed information from a technology's detail page.

        Can be used to get additional information not in the list API.
        """
        await self._init_session()

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None

                # Return basic info - detailed parsing would require BeautifulSoup
                return {"url": url, "status": "fetched"}

        except Exception as e:
            logger.debug(f"Error fetching technology detail: {e}")
            return None

    # Backwards compatibility methods
    async def _init_browser(self) -> None:
        """Backwards compatibility - initializes HTTP session instead."""
        await self._init_session()

    async def _close_browser(self) -> None:
        """Backwards compatibility - closes HTTP session instead."""
        await self._close_session()
