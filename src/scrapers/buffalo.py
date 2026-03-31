"""University at Buffalo scraper using Algolia API."""

import re
from typing import AsyncIterator, Optional

import aiohttp
from loguru import logger

from .base import BaseScraper, Technology


class BuffaloScraper(BaseScraper):
    """
    Scraper for University at Buffalo Innovation portal.

    Uses Algolia search API to retrieve technology listings.
    """

    BASE_URL = "https://buffalo.technologypublisher.com"
    ALGOLIA_APP_ID = "8J63AVPT8D"
    ALGOLIA_API_KEY = "9670d8d8d18703772307cfb709976528"
    ALGOLIA_INDEX = "Prod_Inteum_TechnologyPublisher_buffalo"
    ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(
            university_code="buffalo",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "University at Buffalo Innovation"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for Buffalo")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from Buffalo via Algolia API."""
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
            # Filter out campus names and top-level groupings
            skip_categories = {"University at Buffalo", "Technology Classifications"}
            categories = []
            final_path = item.get("finalPathCategories", "")
            if final_path:
                for path in final_path.split(", "):
                    parts = path.split(" > ")
                    leaf = parts[-1].strip() if len(parts) > 1 else ""
                    if leaf and leaf not in skip_categories:
                        categories.append(leaf)

            # Parse inventors from structured field or path string
            inventors = []
            inventors_list = item.get("inventors")
            if isinstance(inventors_list, list):
                inventors = [inv.strip() for inv in inventors_list if isinstance(inv, str) and inv.strip()]
            if not inventors:
                inventors_str = item.get("finalPathInventors", "")
                if inventors_str:
                    inventors = [inv.strip() for inv in inventors_str.split(",") if inv.strip()]
            # Also try from parsed sections
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
                "short_description": description,
                "disclosure_date": item.get("disclosureDate"),
                "categories": categories,
                "inventors": inventors,
                "keywords": keywords,
                "client_departments": item.get("clientDepartments"),
            }

            # Add parsed sections (short_description already set above)
            for key in ("abstract", "background", "advantages",
                        "applications", "publications", "ip_status", "market_opportunity",
                        "development_stage", "benefit", "solution", "technical_problem",
                        "trl"):
                if sections.get(key):
                    raw_data[key] = sections[key]

            # If no structured sections found but full description is substantial,
            # store as cleaned plain text in description
            if not sections and full_description:
                cleaned = re.sub(r"<[^>]+>", " ", full_description)
                cleaned = re.sub(r"&nbsp;", " ", cleaned)
                cleaned = re.sub(r"\s+", " ", cleaned).strip()
                if len(cleaned) > 100:
                    raw_data["description"] = cleaned

            return Technology(
                university="buffalo",
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
        """Parse structured sections from Algolia descriptionFull RSS XML tags."""
        import html as html_mod
        import warnings
        from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

        warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

        text = html_mod.unescape(text)

        tag_mapping = {
            "AlgoliaSummary": "short_description",
            "Background": "background",
            "Technology": "solution",
            "Advantages": "advantages",
            "Application": "applications",
            "Applications": "applications",
            "Publication": "publications",
            "Publications": "publications",
            "PatentStatus": "ip_status",
            "StageOfDevelopment": "development_stage",
        }

        sections = {}
        for rss_tag, field_name in tag_mapping.items():
            pattern = rf"<RSS\.{rss_tag}>(.*?)</RSS\.{rss_tag}>"
            match = re.search(pattern, text, re.DOTALL)
            if not match:
                continue
            raw_html = match.group(1).strip()
            if not raw_html:
                continue

            # Publications: extract <a> tags with links
            if field_name == "publications":
                soup = BeautifulSoup(raw_html, "html.parser")
                links = soup.find_all("a", href=True)
                if links:
                    pubs = []
                    for a in links:
                        link_text = a.get_text(strip=True)
                        link_url = a["href"]
                        if link_text or link_url:
                            pubs.append({"text": link_text or link_url, "url": link_url})
                    if pubs:
                        sections["publications"] = pubs
                        continue
                # No links found — store as plain text
                plain = re.sub(r"<[^>]+>", " ", raw_html)
                plain = re.sub(r"&nbsp;", " ", plain)
                plain = re.sub(r"\s+", " ", plain).strip()
                if plain:
                    sections["publications"] = plain
                continue

            # Advantages/applications: try <li> extraction first
            if field_name in ("advantages", "applications"):
                soup = BeautifulSoup(raw_html, "html.parser")
                li_items = soup.find_all("li")
                if li_items:
                    items = [li.get_text(strip=True) for li in li_items if li.get_text(strip=True)]
                    if items:
                        sections[field_name] = items
                        continue
                # Fall back: strip HTML but preserve tabs/newlines as delimiters
                content = re.sub(r"<[^>]+>", "\n", raw_html)
                content = re.sub(r"&nbsp;", " ", content)
                # Split on tabs, newlines, or bullet characters BEFORE collapsing whitespace
                items = re.split(r"\t+|\n+|•|►|■", content)
                items = [re.sub(r"\s+", " ", item).strip() for item in items if item.strip()]
                if items:
                    sections[field_name] = items
                continue

            # Default: strip HTML tags
            content = re.sub(r"<[^>]+>", " ", raw_html)
            content = re.sub(r"&nbsp;", " ", content)
            content = re.sub(r"\s+", " ", content).strip()
            if not content:
                continue
            sections[field_name] = content

        # Extract TRL from development_stage
        if sections.get("development_stage"):
            trl_match = re.search(r"TRL\s*(\d+(?:\s*[-–]\s*\d+)?)", sections["development_stage"], re.IGNORECASE)
            if trl_match:
                sections["trl"] = trl_match.group(1).strip()

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
