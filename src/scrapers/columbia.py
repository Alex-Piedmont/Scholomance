"""Columbia Technology Ventures scraper using sitemap."""

import asyncio
import re
from typing import AsyncIterator, Optional
from xml.etree import ElementTree

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology


class ColumbiaScraper(BaseScraper):
    """Scraper for Columbia University's technology ventures portal."""

    BASE_URL = "https://inventions.techventures.columbia.edu"
    SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

    def __init__(self, delay_seconds: float = 0.2):
        super().__init__(
            university_code="columbia",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "Columbia Technology Ventures"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for Columbia")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def _get_technology_urls(self) -> list[str]:
        """Get all technology URLs from sitemap."""
        await self._init_session()

        try:
            async with self._session.get(self.SITEMAP_URL) as response:
                if response.status != 200:
                    self.log_error(f"Sitemap returned status {response.status}")
                    return []

                xml_content = await response.text()
                root = ElementTree.fromstring(xml_content)

                # Extract URLs from sitemap
                namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                urls = []
                for url_elem in root.findall(".//ns:url/ns:loc", namespace):
                    url = url_elem.text
                    if url and "/technologies/" in url:
                        urls.append(url)

                return urls

        except Exception as e:
            self.log_error("Error fetching sitemap", e)
            return []

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from Columbia via sitemap."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology URLs from sitemap")
            urls = await self._get_technology_urls()
            total = len(urls)
            self.log_progress(f"Found {total} technology URLs")

            for i, url in enumerate(urls):
                tech = self._parse_url(url)
                if tech:
                    self._tech_count += 1
                    yield tech

                # Log progress every 200 items
                if (i + 1) % 200 == 0:
                    self.log_progress(f"Processed {i + 1}/{total} technologies")

            self._page_count = 1
            self.log_progress(
                f"Completed scraping: {self._tech_count} technologies"
            )

        finally:
            await self._close_session()

    def _parse_url(self, url: str) -> Optional[Technology]:
        """Parse technology info from URL."""
        try:
            # URL format: /technologies/title-slug--CU12345
            path = url.split("/technologies/")[-1]

            # Extract tech ID (CU number at end)
            tech_id_match = re.search(r'--?(CU\d+|\d+)$', path)
            if tech_id_match:
                tech_id = tech_id_match.group(1)
                # Title is everything before the ID
                title_slug = path[:tech_id_match.start()]
            else:
                tech_id = path
                title_slug = path

            # Convert slug to title
            title = title_slug.replace("-", " ").strip()
            # Capitalize first letter of each word
            title = " ".join(word.capitalize() for word in title.split())

            if not title:
                return None

            raw_data = {
                "url": url,
                "tech_id": tech_id,
                "title_slug": title_slug,
            }

            return Technology(
                university="columbia",
                tech_id=tech_id,
                title=title,
                url=url,
                description=None,  # Would need to fetch detail page
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing URL {url}: {e}")
            return None

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """
        Scrape technologies - Columbia uses sitemap approach.
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

                html = await response.text()
                soup = BeautifulSoup(html, "lxml")

                detail = {"url": url}

                # Try to extract description and other details
                # The actual structure would need to be determined from the page
                desc = soup.find("meta", attrs={"name": "description"})
                if desc:
                    detail["description"] = desc.get("content", "")

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
