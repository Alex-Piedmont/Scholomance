"""University of Michigan Innovation Partnerships scraper."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology


class UMichScraper(BaseScraper):
    """Scraper for University of Michigan's available inventions portal."""

    BASE_URL = "https://available-inventions.umich.edu"
    API_URL = f"{BASE_URL}/autocomplete/products"

    def __init__(self, delay_seconds: float = 0.5):
        super().__init__(
            university_code="umich",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "University of Michigan Innovation Partnerships"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for UMich")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from UMich."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology list from API")

            # The autocomplete API returns all technologies with empty term
            params = {"term": ""}

            async with self._session.get(self.API_URL, params=params) as response:
                if response.status != 200:
                    self.log_error(f"API returned status {response.status}")
                    return

                data = await response.json()
                total = len(data)
                self.log_progress(f"Found {total} technologies")

                for i, item in enumerate(data):
                    tech = self._parse_api_item(item)
                    if tech:
                        self._tech_count += 1
                        yield tech

                    # Log progress every 100 items
                    if (i + 1) % 100 == 0:
                        self.log_progress(f"Processed {i + 1}/{total} technologies")

            self._page_count = 1  # Single API call
            self.log_progress(
                f"Completed scraping: {self._tech_count} technologies"
            )

        finally:
            await self._close_session()

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """
        Scrape technologies - UMich uses single API call, not pagination.
        This method exists for interface compatibility.
        """
        if page_num != 1:
            return []

        technologies = []
        async for tech in self.scrape():
            technologies.append(tech)
        return technologies

    def _parse_api_item(self, item: dict) -> Optional[Technology]:
        """Parse a technology item from the API response."""
        try:
            name = item.get("name", "").strip()
            if not name:
                return None

            attrs = item.get("dataAttributes", {})
            tech_id = str(attrs.get("id", ""))
            url_path = attrs.get("url", "")

            # Build full URL
            url = f"{self.BASE_URL}/{url_path}" if url_path else ""

            # Extract slug for tech_id if numeric ID not available
            if not tech_id and url_path:
                tech_id = url_path.replace("product/", "")

            if not tech_id:
                tech_id = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower())[:50]

            raw_data = {
                "id": tech_id,
                "name": name,
                "url": url,
                "url_path": url_path,
            }

            return Technology(
                university="umich",
                tech_id=tech_id,
                title=name,
                url=url,
                description=None,  # Would need to fetch detail page
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing API item: {e}")
            return None

    async def scrape_technology_detail(self, url: str) -> Optional[dict]:
        """
        Scrape detailed information from a technology's detail page.

        Args:
            url: The URL of the technology detail page

        Returns:
            Dictionary with detailed technology information
        """
        await self._init_session()

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "lxml")

                detail = {}

                # Get technology number from meta description
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc:
                    content = meta_desc.get("content", "")
                    if "TECHNOLOGY NUMBER:" in content:
                        detail["technology_number"] = content.replace("TECHNOLOGY NUMBER:", "").strip()

                # Get description
                desc_div = soup.find("div", class_="description")
                if desc_div:
                    detail["description"] = desc_div.get_text(strip=True)

                # Get full product description box
                desc_box = soup.find("div", class_="product-description-box")
                if desc_box:
                    detail["full_description"] = desc_box.get_text(strip=True)

                return detail

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
