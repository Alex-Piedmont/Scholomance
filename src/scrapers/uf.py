"""University of Florida Tech Licensing scraper using Algolia API."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from loguru import logger

from .base import BaseScraper, Technology


class UFScraper(BaseScraper):
    """Scraper for University of Florida's technology publisher portal."""

    BASE_URL = "https://ufinnovate.technologypublisher.com"
    ALGOLIA_APP_ID = "K848S43IM3"
    ALGOLIA_API_KEY = "c562a719fe42837070634da98b0cd472"
    ALGOLIA_INDEX = "Prod_Inteum_TechnologyPublisher_ufinnovate"
    ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

    def __init__(self, delay_seconds: float = 0.5):
        super().__init__(
            university_code="uf",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "University of Florida Tech Licensing"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for UF")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from UF via Algolia API."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology list from Algolia API")

            headers = {
                "X-Algolia-Application-Id": self.ALGOLIA_APP_ID,
                "X-Algolia-API-Key": self.ALGOLIA_API_KEY,
                "Content-Type": "application/json",
            }

            # Request all hits in one query
            payload = {
                "query": "",
                "hitsPerPage": 1000,
            }

            async with self._session.post(
                self.ALGOLIA_URL, headers=headers, json=payload
            ) as response:
                if response.status != 200:
                    self.log_error(f"Algolia API returned status {response.status}")
                    return

                data = await response.json()
                hits = data.get("hits", [])
                total = data.get("nbHits", len(hits))
                self.log_progress(f"Found {total} technologies")

                for i, item in enumerate(hits):
                    tech = self._parse_algolia_hit(item)
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
        Scrape technologies - UF uses single API call, not pagination.
        This method exists for interface compatibility.
        """
        if page_num != 1:
            return []

        technologies = []
        async for tech in self.scrape():
            technologies.append(tech)
        return technologies

    def _parse_algolia_hit(self, item: dict) -> Optional[Technology]:
        """Parse a technology item from Algolia search hit."""
        try:
            title = item.get("title", "").strip()
            if not title:
                return None

            tech_id = item.get("techID", "") or str(item.get("objectID", ""))
            url = item.get("Url", "")

            # Get description
            description = item.get("descriptionTruncated", "")
            if description:
                description = description.strip()

            # Parse categories from finalPathCategories
            categories = []
            final_path = item.get("finalPathCategories", "")
            if final_path:
                # Format: "Technology Classifications > Engineering > Computer Science, ..."
                for path in final_path.split(", "):
                    parts = path.split(" > ")
                    if len(parts) > 1:
                        # Get the most specific category (last part)
                        categories.append(parts[-1].strip())

            # Parse inventors
            inventors = []
            inventors_str = item.get("finalPathInventors", "")
            if inventors_str:
                inventors = [inv.strip() for inv in inventors_str.split(",") if inv.strip()]

            # Get keywords
            keywords_raw = item.get("keywords")
            keywords = []
            if keywords_raw and keywords_raw != "None":
                if isinstance(keywords_raw, list):
                    keywords = keywords_raw
                elif isinstance(keywords_raw, str):
                    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

            # Combine categories and keywords
            all_keywords = list(set(categories + keywords)) if (categories or keywords) else None

            raw_data = {
                "tech_id": tech_id,
                "object_id": item.get("objectID"),
                "title": title,
                "url": url,
                "description": description,
                "disclosure_date": item.get("disclosureDate"),
                "categories": categories,
                "inventors": inventors,
                "keywords": keywords,
            }

            return Technology(
                university="uf",
                tech_id=tech_id or re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50],
                title=title,
                url=url,
                description=description if description else None,
                keywords=all_keywords,
                innovators=inventors if inventors else None,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing Algolia hit: {e}")
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
                # Basic extraction - could be enhanced with BeautifulSoup
                detail = {"url": url}

                # The detail page likely has more info, but for now
                # we rely on Algolia data which is comprehensive
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
