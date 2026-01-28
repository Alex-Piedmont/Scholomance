"""Johns Hopkins University Technology Ventures scraper using Algolia API."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from loguru import logger

from .base import BaseScraper, Technology


class JHUScraper(BaseScraper):
    """Scraper for Johns Hopkins University's technology publisher portal."""

    BASE_URL = "https://jhu.technologypublisher.com"
    ALGOLIA_APP_ID = "X7MZ45KXED"
    ALGOLIA_API_KEY = "6d2eb86acf644cc476844fa15c2a04ef"
    ALGOLIA_INDEX = "Prod_Inteum_TechnologyPublisher_jhu"
    ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

    # Categories to query separately (Algolia limits to 1000 results per query)
    CATEGORIES = [
        "Research Tools",
        "Therapeutic Modalities",
        "Computers, Electronics & Software",
        "Medical Devices",
        "Diagnostics",
        "Engineering Tech",
        "Industrial Tech",
    ]

    def __init__(self, delay_seconds: float = 0.5):
        super().__init__(
            university_code="jhu",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None
        self._seen_ids: set[str] = set()  # Track seen IDs to avoid duplicates

    @property
    def name(self) -> str:
        return "Johns Hopkins Technology Ventures"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for JHU")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from JHU via Algolia API."""
        try:
            await self._init_session()
            self._seen_ids = set()

            self.log_progress("Fetching technology list from Algolia API")

            headers = {
                "X-Algolia-Application-Id": self.ALGOLIA_APP_ID,
                "X-Algolia-API-Key": self.ALGOLIA_API_KEY,
                "Content-Type": "application/json",
            }

            # Query each category separately to work around 1000 result limit
            for category in self.CATEGORIES:
                payload = {
                    "query": "",
                    "hitsPerPage": 1000,
                    "filters": f'"Technology Classifications.lvl0":"{category}"',
                }

                try:
                    async with self._session.post(
                        self.ALGOLIA_URL, headers=headers, json=payload
                    ) as response:
                        if response.status != 200:
                            self.log_error(f"Algolia API returned status {response.status} for {category}")
                            continue

                        data = await response.json()
                        hits = data.get("hits", [])

                        new_count = 0
                        for item in hits:
                            tech = self._parse_algolia_hit(item)
                            if tech and tech.tech_id not in self._seen_ids:
                                self._seen_ids.add(tech.tech_id)
                                self._tech_count += 1
                                new_count += 1
                                yield tech

                        self.log_progress(f"Category '{category}': {len(hits)} hits, {new_count} new")

                except Exception as e:
                    self.log_error(f"Error querying category {category}", e)
                    continue

                self._page_count += 1
                await self.delay()

            self.log_progress(
                f"Completed scraping: {self._tech_count} unique technologies"
            )

        finally:
            await self._close_session()

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """
        Scrape technologies - JHU uses category-based queries.
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
                for path in final_path.split(", "):
                    parts = path.split(" > ")
                    if len(parts) > 1:
                        categories.append(parts[-1].strip())

            # Parse inventors
            inventors = []
            inventors_str = item.get("finalPathInventors", "")
            if inventors_str:
                inventors = [inv.strip() for inv in inventors_str.split(",") if inv.strip()]

            # Get patent status
            patent_statuses = item.get("patentStatuses", [])

            raw_data = {
                "tech_id": tech_id,
                "object_id": item.get("objectID"),
                "title": title,
                "url": url,
                "description": description,
                "disclosure_date": item.get("disclosureDate"),
                "categories": categories,
                "inventors": inventors,
                "patent_statuses": patent_statuses,
            }

            return Technology(
                university="jhu",
                tech_id=tech_id or re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50],
                title=title,
                url=url,
                description=description if description else None,
                keywords=categories if categories else None,
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
                detail = {"url": url}
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
