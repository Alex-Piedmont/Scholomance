"""Johns Hopkins University Technology Ventures scraper using Algolia API."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
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

        JHU detail pages contain structured patent information including:
        - Patent number
        - Serial number
        - Issue Date
        - Status (Granted/Pending/etc.)

        Args:
            url: The URL of the technology detail page

        Returns:
            Dictionary with detailed technology information including patent info
        """
        await self._init_session()

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "lxml")

                detail = {"url": url}

                # Get full description
                desc_div = soup.find("div", class_="technology-description")
                if desc_div:
                    detail["full_description"] = desc_div.get_text(strip=True)

                # Extract patent information from structured HTML
                patent_info = self._extract_patent_info_from_html(soup, html)
                if patent_info:
                    detail.update(patent_info)

                return detail

        except Exception as e:
            logger.debug(f"Error fetching technology detail: {e}")
            return None

    def _extract_patent_info_from_html(self, soup, html: str) -> dict:
        """Extract structured patent information from JHU HTML page."""
        patent_info = {}
        patent_numbers = []
        serial_numbers = []

        # JHU displays patent info in structured format
        # Look for patent number patterns
        us_patent_matches = re.findall(
            r'(?:Patent|Patent\s*#?|Patent\s*Number)[:\s]*(\d{1,3}(?:,\d{3})+|\d{7,10})',
            html,
            re.IGNORECASE
        )
        for match in us_patent_matches:
            clean_num = match.replace(",", "")
            if len(clean_num) >= 7:
                patent_numbers.append(match)

        # Look for serial numbers (application numbers)
        serial_matches = re.findall(
            r'(?:Serial|Serial\s*#?|Application\s*#?)[:\s]*(\d{2}/\d{3},?\d{3})',
            html,
            re.IGNORECASE
        )
        serial_numbers.extend(serial_matches)

        if patent_numbers:
            patent_info["patent_numbers"] = list(set(patent_numbers))
            patent_info["ip_status"] = "Granted"

        if serial_numbers:
            patent_info["serial_numbers"] = list(set(serial_numbers))

        # Look for explicit Status field
        status_match = re.search(
            r'Status[:\s]*([A-Za-z]+)',
            html,
            re.IGNORECASE
        )
        if status_match:
            status_text = status_match.group(1).lower()
            if "granted" in status_text or "issued" in status_text:
                patent_info["ip_status"] = "Granted"
            elif "pending" in status_text:
                if "ip_status" not in patent_info:
                    patent_info["ip_status"] = "Pending"
            elif "filed" in status_text:
                if "ip_status" not in patent_info:
                    patent_info["ip_status"] = "Filed"
            elif "provisional" in status_text:
                if "ip_status" not in patent_info:
                    patent_info["ip_status"] = "Provisional"

        # Look for Issue Date
        date_match = re.search(
            r'Issue\s*Date[:\s]*(\d{1,2}/\d{1,2}/\d{4})',
            html,
            re.IGNORECASE
        )
        if date_match:
            patent_info["issue_date"] = date_match.group(1)

        html_lower = html.lower()

        # Fallback: check for patent pending keywords
        if "patent pending" in html_lower or "patent-pending" in html_lower:
            if "ip_status" not in patent_info:
                patent_info["ip_status"] = "Pending"

        # Check for PCT/international applications
        if re.search(r'\bpct\b', html_lower) or "international application" in html_lower:
            if "ip_status" not in patent_info:
                patent_info["ip_status"] = "Filed"

        return patent_info

    # Backwards compatibility methods
    async def _init_browser(self) -> None:
        """Backwards compatibility - initializes HTTP session instead."""
        await self._init_session()

    async def _close_browser(self) -> None:
        """Backwards compatibility - closes HTTP session instead."""
        await self._close_session()
