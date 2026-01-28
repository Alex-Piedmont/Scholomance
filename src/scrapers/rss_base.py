"""Base scraper for Technology Publisher sites with RSS feeds."""

import re
import xml.etree.ElementTree as ET
from typing import AsyncIterator, Optional

import aiohttp
from loguru import logger

from .base import BaseScraper, Technology


class RSSBaseScraper(BaseScraper):
    """
    Base scraper for Technology Publisher sites that provide RSS feeds.

    These older Technology Publisher sites don't have Algolia but provide
    RSS feeds at /rss.aspx with technology listings.

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
    def rss_url(self) -> str:
        """URL for the RSS feed."""
        return f"{self.BASE_URL}/rss.aspx"

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
        """Scrape all technologies from the RSS feed."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology list from RSS feed")

            async with self._session.get(self.rss_url) as response:
                if response.status != 200:
                    self.log_error(f"RSS feed returned status {response.status}")
                    return

                content = await response.text()

                # Parse RSS XML
                try:
                    root = ET.fromstring(content)
                except ET.ParseError as e:
                    self.log_error(f"Failed to parse RSS feed: {e}")
                    return

                # Find all items in the RSS feed
                # RSS 2.0 structure: rss > channel > item
                channel = root.find("channel")
                if channel is None:
                    self.log_error("No channel found in RSS feed")
                    return

                items = channel.findall("item")
                total = len(items)
                self.log_progress(f"Found {total} technologies in RSS feed")

                for i, item in enumerate(items):
                    tech = self._parse_rss_item(item)
                    if tech:
                        self._tech_count += 1
                        yield tech

                    if (i + 1) % 50 == 0:
                        self.log_progress(f"Processed {i + 1}/{total} technologies")

            self._page_count = 1
            self.log_progress(f"Completed scraping: {self._tech_count} technologies")

        finally:
            await self._close_session()

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """Scrape technologies - RSS uses single feed, not pagination."""
        if page_num != 1:
            return []

        technologies = []
        async for tech in self.scrape():
            technologies.append(tech)
        return technologies

    def _parse_rss_item(self, item: ET.Element) -> Optional[Technology]:
        """Parse a technology item from RSS feed."""
        try:
            title = item.findtext("title", "").strip()
            if not title:
                return None

            # Get case ID (tech ID)
            case_id = item.findtext("caseId", "")
            if not case_id:
                # Try to extract from guid
                guid = item.findtext("guid", "")
                if guid:
                    case_id = guid.split("/")[-1] if "/" in guid else guid

            url = item.findtext("link", "")
            description = item.findtext("description", "")
            if description:
                # Clean up HTML entities and tags
                description = re.sub(r'<[^>]+>', '', description)
                description = description.strip()

            pub_date = item.findtext("pubDate", "")
            author = item.findtext("author", "")

            raw_data = {
                "case_id": case_id,
                "title": title,
                "url": url,
                "description": description,
                "pub_date": pub_date,
                "author": author,
                "guid": item.findtext("guid", ""),
            }

            return Technology(
                university=self.UNIVERSITY_CODE,
                tech_id=case_id or re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50],
                title=title,
                url=url,
                description=description if description else None,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing RSS item: {e}")
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
