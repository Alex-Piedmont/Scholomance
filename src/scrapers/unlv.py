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
                "attributesToRetrieve": ["*"],
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

            # Get full description (preferred) or truncated
            full_description = item.get("descriptionFull", "")
            truncated_description = item.get("descriptionTruncated", "")

            # Parse structured sections from full description
            sections = self._parse_description_sections(full_description) if full_description else {}

            # Use short description from sections, or truncated, or full text
            description = (
                sections.get("short_description")
                or sections.get("abstract")
                or truncated_description.strip()
                or full_description[:2000].strip()
            )

            # Parse categories from finalPathCategories
            categories = []
            final_path = item.get("finalPathCategories", "")
            if final_path:
                for path in final_path.split(", "):
                    parts = path.split(" > ")
                    if len(parts) > 1:
                        categories.append(parts[-1].strip())

            # Parse inventors from structured field or path string
            inventors = []
            inventors_list = item.get("inventors")
            if isinstance(inventors_list, list):
                inventors = [inv.strip() for inv in inventors_list if isinstance(inv, str) and inv.strip()]
            if not inventors:
                inventors_str = item.get("finalPathInventors", "")
                if inventors_str:
                    inventors = [inv.strip() for inv in inventors_str.split(",") if inv.strip()]
            if not inventors and sections.get("inventors"):
                inventors = sections["inventors"]

            # Get keywords
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
                "full_description": full_description if full_description else None,
                "disclosure_date": item.get("disclosureDate"),
                "categories": categories,
                "inventors": inventors,
                "keywords": keywords,
                "client_departments": item.get("clientDepartments"),
            }

            # Add parsed sections
            for key in ("abstract", "background", "short_description", "advantages",
                        "applications", "publications", "ip_status", "market_opportunity",
                        "development_stage", "benefit"):
                if sections.get(key):
                    raw_data[key] = sections[key]

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

    @staticmethod
    def _parse_description_sections(text: str) -> dict:
        """Parse structured sections from Algolia descriptionFull text."""
        import html as html_mod

        text = html_mod.unescape(text)

        section_patterns = [
            ("short_description", r"SHORT\s+DESCRIPTION"),
            ("abstract", r"ABSTRACT"),
            ("background", r"BACKGROUND"),
            ("market_opportunity", r"MARKET\s+OPPORTUNITY"),
            ("development_stage", r"DEVELOPMENT\s+STAGE"),
            ("applications", r"APPLICATIONS"),
            ("advantages", r"ADVANTAGES"),
            ("publications", r"PUBLICATIONS"),
            ("ip_status", r"IP\s+STATUS"),
            ("benefit", r"BENEFITS?"),
            ("inventors_section", r"INVENTORS?"),
            ("technical_problem", r"TECHNICAL\s+PROBLEM"),
            ("solution", r"(?:TECHNICAL\s+)?SOLUTION"),
        ]

        all_headers = "|".join(f"(?P<s{i}>{pat})" for i, (_, pat) in enumerate(section_patterns))
        header_re = re.compile(rf"\s*(?:{all_headers})\s*", re.IGNORECASE)

        sections = {}
        parts = header_re.split(text)

        current_key = None
        for part in parts:
            if part is None:
                continue
            part = part.strip()
            if not part:
                continue

            matched_key = None
            for key, pat in section_patterns:
                if re.fullmatch(pat, part, re.IGNORECASE):
                    matched_key = key
                    break

            if matched_key:
                current_key = matched_key
            elif current_key:
                if current_key == "inventors_section":
                    sections[current_key] = part
                else:
                    cleaned = re.sub(r"\s+", " ", part).strip()
                    if cleaned:
                        sections[current_key] = cleaned

        inv_text = sections.pop("inventors_section", "")
        if inv_text:
            inv_list = re.split(r"\s{2,}|\t|\n|•|;", inv_text)
            inventors = [
                re.sub(r"\*$", "", inv.strip().rstrip(",")).strip()
                for inv in inv_list
                if inv.strip() and len(inv.strip()) > 1
                and not re.match(r"^[\d\W]+$", inv.strip())
            ]
            if inventors:
                sections["inventors"] = inventors

        return sections

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
