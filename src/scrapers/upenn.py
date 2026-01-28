"""University of Pennsylvania Penn Center for Innovation scraper using RSS feed."""

import asyncio
import re
from typing import AsyncIterator, Optional
from xml.etree import ElementTree
import html

import aiohttp
from loguru import logger

from .base import BaseScraper, Technology


class UPennScraper(BaseScraper):
    """Scraper for University of Pennsylvania's technology publisher portal."""

    BASE_URL = "https://upenn.technologypublisher.com"
    RSS_URL = f"{BASE_URL}/rss.aspx"
    SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

    def __init__(self, delay_seconds: float = 0.2):
        super().__init__(
            university_code="upenn",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "Penn Center for Innovation"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for UPenn")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def _get_technologies_from_rss(self) -> list[dict]:
        """Get all technologies from RSS feed."""
        await self._init_session()

        try:
            async with self._session.get(self.RSS_URL) as response:
                if response.status != 200:
                    self.log_error(f"RSS feed returned status {response.status}")
                    return []

                xml_content = await response.text()
                root = ElementTree.fromstring(xml_content)

                technologies = []
                for item in root.findall(".//item"):
                    tech = {
                        "title": self._get_text(item, "title"),
                        "link": self._get_text(item, "link"),
                        "guid": self._get_text(item, "guid"),
                        "description": self._get_text(item, "description"),
                        "case_id": self._get_text(item, "caseId"),
                        "pub_date": self._get_text(item, "pubDate"),
                    }
                    if tech["title"]:
                        technologies.append(tech)

                return technologies

        except Exception as e:
            self.log_error("Error fetching RSS feed", e)
            return []

    def _get_text(self, element, tag: str) -> str:
        """Get text content from XML element."""
        child = element.find(tag)
        if child is not None and child.text:
            # Unescape HTML entities
            text = html.unescape(child.text)
            # Remove CDATA markers if present
            text = re.sub(r'<!\[CDATA\[|\]\]>', '', text)
            return text.strip()
        return ""

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from UPenn via RSS feed."""
        try:
            await self._init_session()

            self.log_progress("Fetching technologies from RSS feed")
            items = await self._get_technologies_from_rss()
            total = len(items)
            self.log_progress(f"Found {total} technologies in RSS feed")

            for i, item in enumerate(items):
                tech = self._parse_rss_item(item)
                if tech:
                    self._tech_count += 1
                    yield tech

                # Log progress every 100 items
                if (i + 1) % 100 == 0:
                    self.log_progress(f"Processed {i + 1}/{total} technologies")

            self._page_count = 1
            self.log_progress(
                f"Completed scraping: {self._tech_count} technologies"
            )

        finally:
            await self._close_session()

    def _parse_rss_item(self, item: dict) -> Optional[Technology]:
        """Parse technology info from RSS item."""
        try:
            title = item.get("title", "").strip()
            if not title:
                return None

            url = item.get("link") or item.get("guid", "")

            # Extract tech_id from URL (e.g., /technology/59895)
            tech_id = ""
            if url:
                match = re.search(r'/technology/(\d+)', url)
                if match:
                    tech_id = match.group(1)

            # Use case_id if no tech_id from URL
            case_id = item.get("case_id", "")
            if not tech_id:
                tech_id = case_id or re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50]

            # Clean description
            description = item.get("description", "")
            if description:
                # Remove HTML tags
                description = re.sub(r'<[^>]+>', '', description)
                # Clean up whitespace
                description = re.sub(r'\s+', ' ', description).strip()
                # Truncate if too long
                if len(description) > 500:
                    description = description[:497] + "..."

            raw_data = {
                "url": url,
                "tech_id": tech_id,
                "case_id": case_id,
                "title": title,
                "description": description,
                "pub_date": item.get("pub_date", ""),
            }

            return Technology(
                university="upenn",
                tech_id=tech_id,
                title=title,
                url=url,
                description=description if description else None,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing RSS item: {e}")
            return None

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """
        Scrape technologies - UPenn uses RSS feed approach.
        This method exists for interface compatibility.
        """
        if page_num != 1:
            return []

        technologies = []
        async for tech in self.scrape():
            technologies.append(tech)
        return technologies

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

                html_content = await response.text()
                detail = {"url": url}

                # Extract additional details from page if needed
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
