"""University of California System technology transfer scraper using sitemap."""

import asyncio
import re
from typing import AsyncIterator, Optional
from xml.etree import ElementTree

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology


class UCSystemScraper(BaseScraper):
    """Scraper for University of California System's technology transfer portal.

    This scrapes technologies from all 10 UC campuses via the centralized
    UC tech transfer portal at techtransfer.universityofcalifornia.edu.
    """

    BASE_URL = "https://techtransfer.universityofcalifornia.edu"
    SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

    # Map campus codes to full names
    CAMPUS_NAMES = {
        "berkeley": "UC Berkeley",
        "davis": "UC Davis",
        "irvine": "UC Irvine",
        "los angeles": "UCLA",
        "merced": "UC Merced",
        "riverside": "UC Riverside",
        "san diego": "UC San Diego",
        "san francisco": "UCSF",
        "santa barbara": "UC Santa Barbara",
        "santa cruz": "UC Santa Cruz",
    }

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(
            university_code="ucsystem",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "University of California System"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for UC System")

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
                    # Only get NCD (technology disclosure) pages
                    if url and "/NCD/" in url:
                        urls.append(url)

                return urls

        except Exception as e:
            self.log_error("Error fetching sitemap", e)
            return []

    async def _fetch_technology_detail(self, url: str) -> Optional[dict]:
        """Fetch and parse a technology detail page."""
        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "lxml")

                detail = {"url": url}

                # Extract tech ID from URL (e.g., /NCD/21826.html -> 21826)
                match = re.search(r'/NCD/(\d+)\.html', url)
                if match:
                    detail["tech_id"] = match.group(1)

                # Get title
                title_elem = soup.find("h1")
                if title_elem:
                    detail["title"] = title_elem.get_text(strip=True)

                # Get campus/university from breadcrumb or content
                campus_elem = soup.find("a", href=re.compile(r"\?campus="))
                if campus_elem:
                    detail["campus"] = campus_elem.get_text(strip=True)
                else:
                    # Try to find in page text
                    page_text = soup.get_text()
                    for campus_key, campus_name in self.CAMPUS_NAMES.items():
                        if f"university of california, {campus_key}" in page_text.lower():
                            detail["campus"] = campus_name
                            break

                # Get description from meta tag or content
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc:
                    detail["description"] = meta_desc.get("content", "")

                # Try to get fuller description from page content
                content_div = soup.find("div", class_="field-item")
                if content_div:
                    desc_text = content_div.get_text(strip=True)
                    if desc_text and len(desc_text) > len(detail.get("description", "")):
                        detail["description"] = desc_text

                # Get categories
                categories = []
                cat_section = soup.find("div", class_="field-name-field-categories")
                if cat_section:
                    for cat in cat_section.find_all("a"):
                        categories.append(cat.get_text(strip=True))
                detail["categories"] = categories

                # Get UC Case number if available
                case_match = re.search(r'UC Case[:\s]+([^\s<]+)', html)
                if case_match:
                    detail["case_number"] = case_match.group(1)

                return detail

        except Exception as e:
            logger.debug(f"Error fetching {url}: {e}")
            return None

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from UC System via sitemap."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology URLs from sitemap")
            urls = await self._get_technology_urls()
            total = len(urls)
            self.log_progress(f"Found {total} technology URLs")

            # Process in batches to avoid overwhelming the server
            batch_size = 10
            for i in range(0, total, batch_size):
                batch_urls = urls[i:i + batch_size]

                # Fetch batch concurrently
                tasks = [self._fetch_technology_detail(url) for url in batch_urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for url, result in zip(batch_urls, results):
                    if isinstance(result, Exception):
                        logger.debug(f"Error processing {url}: {result}")
                        continue

                    if result:
                        tech = self._parse_detail(result)
                        if tech:
                            self._tech_count += 1
                            yield tech

                # Log progress
                processed = min(i + batch_size, total)
                if processed % 100 == 0 or processed == total:
                    self.log_progress(f"Processed {processed}/{total} technologies")

                await self.delay()

            self._page_count = 1
            self.log_progress(
                f"Completed scraping: {self._tech_count} technologies"
            )

        finally:
            await self._close_session()

    def _parse_detail(self, detail: dict) -> Optional[Technology]:
        """Parse technology info from detail dict."""
        try:
            title = detail.get("title", "").strip()
            if not title:
                return None

            tech_id = detail.get("tech_id", "")
            if not tech_id:
                tech_id = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50]

            url = detail.get("url", "")
            description = detail.get("description", "")

            # Clean description
            if description:
                description = re.sub(r'\s+', ' ', description).strip()
                if len(description) > 500:
                    description = description[:497] + "..."

            # Get campus info
            campus = detail.get("campus", "")
            categories = detail.get("categories", [])

            raw_data = {
                "url": url,
                "tech_id": tech_id,
                "title": title,
                "description": description,
                "campus": campus,
                "categories": categories,
                "case_number": detail.get("case_number"),
            }

            # Add campus to keywords if available
            keywords = categories.copy() if categories else []
            if campus:
                keywords.insert(0, campus)

            return Technology(
                university="ucsystem",
                tech_id=tech_id,
                title=title,
                url=url,
                description=description if description else None,
                keywords=keywords if keywords else None,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing detail: {e}")
            return None

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """
        Scrape technologies - UC System uses sitemap approach.
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
            return await self._fetch_technology_detail(url)
        finally:
            pass  # Keep session open for potential reuse

    # Backwards compatibility methods
    async def _init_browser(self) -> None:
        """Backwards compatibility - initializes HTTP session instead."""
        await self._init_session()

    async def _close_browser(self) -> None:
        """Backwards compatibility - closes HTTP session instead."""
        await self._close_session()
