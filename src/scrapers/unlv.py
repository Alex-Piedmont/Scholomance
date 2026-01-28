"""University of Nevada Las Vegas scraper using Algolia API."""

import re
from typing import AsyncIterator, Optional

import aiohttp
from loguru import logger

from .base import BaseScraper, Technology


class UNLVScraper(BaseScraper):
    """
    Scraper for University of Nevada Las Vegas technology portal.

    Uses Algolia search API to retrieve technology listings.
    """

    BASE_URL = "https://unlvecondev.technologypublisher.com"
    ALGOLIA_APP_ID = "0YSWDGMOHF"
    ALGOLIA_API_KEY = "f63aa4b7c74379f3e547101e65f07b21"
    ALGOLIA_INDEX = "Prod_Inteum_TechnologyPublisher_unlvecondev"
    ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(
            university_code="unlv",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "University of Nevada Las Vegas"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for UNLV")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from UNLV via Algolia API."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology list from Algolia API")

            headers = {
                "X-Algolia-Application-Id": self.ALGOLIA_APP_ID,
                "X-Algolia-API-Key": self.ALGOLIA_API_KEY,
                "Content-Type": "application/json",
            }

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

                    if (i + 1) % 100 == 0:
                        self.log_progress(f"Processed {i + 1}/{total} technologies")

            self._page_count = 1
            self.log_progress(f"Completed scraping: {self._tech_count} technologies")

        finally:
            await self._close_session()

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """Scrape technologies - uses single API call."""
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

            description = item.get("descriptionTruncated", "")
            if description:
                description = description.strip()

            categories = []
            final_path = item.get("finalPathCategories", "")
            if final_path:
                for path in final_path.split(", "):
                    parts = path.split(" > ")
                    if len(parts) > 1:
                        categories.append(parts[-1].strip())

            inventors = []
            inventors_str = item.get("finalPathInventors", "")
            if inventors_str:
                inventors = [inv.strip() for inv in inventors_str.split(",") if inv.strip()]

            keywords_raw = item.get("keywords")
            keywords = []
            if keywords_raw and keywords_raw != "None":
                if isinstance(keywords_raw, list):
                    keywords = keywords_raw
                elif isinstance(keywords_raw, str):
                    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]

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
                university="unlv",
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
        """Scrape detailed information from a technology's detail page."""
        await self._init_session()
        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None
                return {"url": url}
        except Exception as e:
            logger.debug(f"Error fetching technology detail: {e}")
            return None

    async def _init_browser(self) -> None:
        await self._init_session()

    async def _close_browser(self) -> None:
        await self._close_session()
