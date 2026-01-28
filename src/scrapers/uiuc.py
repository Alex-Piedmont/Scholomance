"""University of Illinois Urbana-Champaign OTM scraper using Flintbox API."""

import re
from typing import AsyncIterator, Optional

import aiohttp
from loguru import logger

from .base import BaseScraper, Technology


class UIUCScraper(BaseScraper):
    """Scraper for UIUC's Flintbox technology portal."""

    BASE_URL = "https://illinois.flintbox.com"
    API_URL = "https://illinois.flintbox.com/api/v1/technologies"
    ORGANIZATION_ID = "31"
    ACCESS_KEY = "f80b8917-1613-4c29-8925-ca33c89e7e08"

    def __init__(self, delay_seconds: float = 0.5):
        super().__init__(
            university_code="uiuc",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "UIUC Office of Technology Management"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for UIUC")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def _get_total_pages(self) -> int:
        """Get total number of pages from API."""
        await self._init_session()

        params = {
            "organizationId": self.ORGANIZATION_ID,
            "organizationAccessKey": self.ACCESS_KEY,
            "page": 1,
            "query": "",
        }

        try:
            async with self._session.get(self.API_URL, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    meta = data.get("meta", {})
                    total_pages = meta.get("totalPages", 33)
                    logger.debug(f"UIUC has {total_pages} pages")
                    return total_pages
                else:
                    logger.warning(f"API returned status {response.status}")
                    return 33
        except Exception as e:
            logger.warning(f"Could not determine total pages: {e}")
            return 33

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from UIUC Flintbox."""
        try:
            await self._init_session()

            total_pages = await self._get_total_pages()
            self.log_progress(f"Starting scrape of {total_pages} pages")

            for page_num in range(1, total_pages + 1):
                try:
                    technologies = await self.scrape_page(page_num)

                    if not technologies:
                        self.log_progress(f"No technologies on page {page_num}, stopping")
                        break

                    for tech in technologies:
                        self._tech_count += 1
                        yield tech

                    self._page_count += 1
                    if page_num % 10 == 0:
                        self.log_progress(
                            f"Scraped page {page_num}/{total_pages}, "
                            f"found {self._tech_count} technologies"
                        )

                    await self.delay()

                except Exception as e:
                    self.log_error(f"Error scraping page {page_num}", e)
                    continue

            self.log_progress(
                f"Completed scraping: {self._tech_count} technologies "
                f"from {self._page_count} pages"
            )

        finally:
            await self._close_session()

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """Scrape a single page of technologies from the API."""
        await self._init_session()

        params = {
            "organizationId": self.ORGANIZATION_ID,
            "organizationAccessKey": self.ACCESS_KEY,
            "page": page_num,
            "query": "",
        }

        logger.debug(f"Scraping page {page_num}")

        try:
            async with self._session.get(self.API_URL, params=params) as response:
                if response.status != 200:
                    self.log_error(f"API returned status {response.status}")
                    return []

                data = await response.json()
                items = data.get("data", [])

                technologies = []
                for item in items:
                    tech = await self._parse_api_item_with_detail(item)
                    if tech:
                        technologies.append(tech)

                return technologies

        except Exception as e:
            self.log_error(f"Error fetching page {page_num}", e)
            return []

    async def _parse_api_item_with_detail(self, item: dict) -> Optional[Technology]:
        """Parse a technology item and fetch additional detail data."""
        try:
            attrs = item.get("attributes", {})
            uuid = attrs.get("uuid", "")

            if not uuid:
                return self._parse_api_item(item)

            # Fetch detail data for IP status and publications
            detail = await self.scrape_technology_detail(uuid)

            title = attrs.get("name", "").strip()
            if not title:
                return None

            tech_id = item.get("id", "")

            # Build description from key points
            key_points = []
            for i in range(1, 4):
                kp = attrs.get(f"keyPoint{i}")
                if kp:
                    key_points.append(kp.strip())

            # Use detail description if available, otherwise key points
            description = None
            if detail:
                other = detail.get("other", "")
                if other:
                    description = re.sub(r"<[^>]+>", " ", other)
                    description = re.sub(r"\s+", " ", description).strip()[:2000]

            if not description:
                description = " | ".join(key_points) if key_points else None

            # Build URL
            url = f"{self.BASE_URL}/technologies/{uuid}" if uuid else ""

            # Get published date
            published_on = attrs.get("publishedOn")

            # Build raw_data with detail fields
            raw_data = {
                "id": tech_id,
                "uuid": uuid,
                "title": title,
                "key_points": key_points,
                "published_on": published_on,
                "featured": attrs.get("featured", False),
                "image_url": attrs.get("primaryImageSmallUrl"),
            }

            # Add detail fields if available
            if detail:
                raw_data["ip_status"] = detail.get("ipStatus")
                raw_data["ip_number"] = detail.get("ipNumber")
                raw_data["ip_url"] = detail.get("ipUrl")
                raw_data["ip_date"] = detail.get("ipDate")
                raw_data["publications"] = detail.get("publications")

            return Technology(
                university="uiuc",
                tech_id=tech_id or uuid or re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50],
                title=title,
                url=url,
                description=description,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing API item with detail: {e}")
            return self._parse_api_item(item)

    def _parse_api_item(self, item: dict) -> Optional[Technology]:
        """Parse a technology item from the API response."""
        try:
            attrs = item.get("attributes", {})

            title = attrs.get("name", "").strip()
            if not title:
                return None

            tech_id = item.get("id", "")
            uuid = attrs.get("uuid", "")

            # Build description from key points
            key_points = []
            for i in range(1, 4):
                kp = attrs.get(f"keyPoint{i}")
                if kp:
                    key_points.append(kp.strip())

            description = " | ".join(key_points) if key_points else None

            # Build URL
            url = f"{self.BASE_URL}/technologies/{uuid}" if uuid else ""

            # Get published date
            published_on = attrs.get("publishedOn")

            raw_data = {
                "id": tech_id,
                "uuid": uuid,
                "title": title,
                "key_points": key_points,
                "published_on": published_on,
                "featured": attrs.get("featured", False),
                "image_url": attrs.get("primaryImageSmallUrl"),
            }

            return Technology(
                university="uiuc",
                tech_id=tech_id or uuid or re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50],
                title=title,
                url=url,
                description=description,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing API item: {e}")
            return None

    async def scrape_technology_detail(self, tech_uuid: str) -> Optional[dict]:
        """Scrape detailed information for a specific technology."""
        await self._init_session()

        detail_url = f"{self.BASE_URL}/api/v1/technologies/{tech_uuid}"
        params = {
            "organizationId": self.ORGANIZATION_ID,
            "organizationAccessKey": self.ACCESS_KEY,
        }

        try:
            async with self._session.get(detail_url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()
                return data.get("data", {}).get("attributes", {})

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
