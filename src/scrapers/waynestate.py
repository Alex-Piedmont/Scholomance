"""Wayne State University scraper using Algolia API with Playwright detail fetching.

Uses Algolia search API for technology listings, then Playwright for detail pages
since TechnologyPublisher renders content via JavaScript.
"""

import asyncio
import html as html_mod
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from loguru import logger

from .base import BaseScraper, Technology

DETAIL_CONCURRENCY = 3


class WayneStateScraper(BaseScraper):
    """
    Scraper for Wayne State University Office for Technology Commercialization.

    Uses Algolia search API to retrieve technology listings.
    """

    BASE_URL = "https://wayne.technologypublisher.com"
    ALGOLIA_APP_ID = "4X4GG2YWR0"
    ALGOLIA_API_KEY = "727a0ff1bad4f40749bffb3d67c93e95"
    ALGOLIA_INDEX = "Prod_Inteum_TechnologyPublisher_wayne"
    ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/{ALGOLIA_INDEX}/query"

    def __init__(self, delay_seconds: float = 0.5):
        super().__init__(
            university_code="waynestate",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @property
    def name(self) -> str:
        return "Wayne State University Technology Commercialization"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for Wayne State")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def _init_browser(self) -> None:
        """Initialize Playwright browser for detail page fetching."""
        if self._browser is None:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
            )
            self._context = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            )
            self._page = await self._context.new_page()
            logger.debug("Playwright browser initialized for Wayne State")

    async def _close_browser(self) -> None:
        """Close Playwright browser."""
        if self._page:
            await self._page.close()
            self._page = None
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.debug("Playwright browser closed")

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from Wayne State via Algolia API with Playwright detail fetching."""
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

            all_technologies: list[Technology] = []

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
                        all_technologies.append(tech)

                    if (i + 1) % 100 == 0:
                        self.log_progress(f"Processed {i + 1}/{total} from API")

            # Fetch detail pages using Playwright for full content
            self.log_progress(f"Fetching detail pages for {len(all_technologies)} technologies")
            await self._init_browser()

            for i, tech in enumerate(all_technologies):
                try:
                    detail = await self.scrape_technology_detail(tech.url)
                    if detail:
                        tech.raw_data.update(detail)
                        # Update top-level fields from detail
                        if detail.get("full_description") and (not tech.description or "..." in tech.description):
                            tech.description = detail["full_description"]
                        if detail.get("inventors"):
                            tech.innovators = detail["inventors"]
                    await asyncio.sleep(self.delay_seconds)
                except Exception as e:
                    logger.debug(f"Error fetching detail for {tech.url}: {e}")

                if (i + 1) % 10 == 0:
                    self.log_progress(f"Enriched {i + 1}/{len(all_technologies)} technologies")

            for tech in all_technologies:
                self._tech_count += 1
                yield tech

            self._page_count = 1
            self.log_progress(f"Completed scraping: {self._tech_count} technologies")

        finally:
            await self._close_session()
            await self._close_browser()

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
            # Clean HTML entities
            if description:
                description = html_mod.unescape(description)

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

            # Clean &nbsp; from full_description
            if full_description:
                full_description = full_description.replace("&nbsp;", " ").replace("\xa0", " ")

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
                university="waynestate",
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
        # Clean literal &nbsp; strings and non-breaking spaces
        text = text.replace("&nbsp;", " ").replace("\xa0", " ")

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
                    # Clean whitespace and leading ": ·" prefixes
                    cleaned = re.sub(r"\s+", " ", part).strip()
                    cleaned = re.sub(r"^[:\s·•\-]+", "", cleaned).strip()
                    # Convert inline bullets to newlines for cleaner display
                    cleaned = re.sub(r"\s*[·•]\s*", "\n", cleaned).strip()
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
        """Scrape detailed information from a technology's detail page using Playwright."""
        if not url or not self._page:
            return None

        try:
            await self._page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(1)

            # Get text content
            text = await self._page.inner_text("body")
            detail: dict = {"url": url}

            # Find start of main content (after tech ID)
            tech_id_match = re.search(r"WSU Tech#:\s*[\d-]+", text)
            if tech_id_match:
                text = text[tech_id_match.end():]

            # Section patterns with their field names
            sections = [
                ("tech_description", r"Technology\s+Description:?"),
                ("applications", r"Commercial\s+Applications?:?"),
                ("development_stage", r"Stage\s+of\s+Development:?"),
                ("advantages", r"(?:Benefit\s+Analysis|Competitive\s+Advantages?):?"),
                ("ip_status", r"(?:Patent\s+Status|Intellectual\s+Property\s+Status):?"),
                ("publications", r"(?:References?|Publications?|Related\s+Publications[^:]*):?"),
                ("categories", r"Categories:?"),
                ("inventors_section", r"Inventors?:"),
                ("keywords_section", r"Keywords?:"),
            ]

            # Find full description (text before first section)
            first_section_idx = len(text)
            for _, pattern in sections:
                match = re.search(pattern, text, re.IGNORECASE)
                if match and match.start() < first_section_idx:
                    first_section_idx = match.start()

            if first_section_idx > 50:
                desc_text = text[:first_section_idx].strip()
                # Clean up description
                desc_text = re.sub(r'\s+', ' ', desc_text).strip()
                if desc_text and len(desc_text) > 50:
                    detail["full_description"] = desc_text

            # Parse each section
            for field, pattern in sections:
                match = re.search(pattern, text, re.IGNORECASE)
                if not match:
                    continue

                # Find the end of this section (start of next section or footer)
                start = match.end()
                end = len(text)

                # Find next section
                for _, next_pat in sections:
                    next_match = re.search(next_pat, text[start:], re.IGNORECASE)
                    if next_match:
                        candidate_end = start + next_match.start()
                        if candidate_end < end:
                            end = candidate_end

                # Find footer markers
                for footer in ["Bookmark this page", "Download as PDF", "For Information, Contact", "© 20"]:
                    footer_idx = text.find(footer, start)
                    if footer_idx > 0 and footer_idx < end:
                        end = footer_idx

                content = text[start:end].strip()
                if not content:
                    continue

                # Parse content based on field type
                lines = [line.strip().lstrip("•·-").strip() for line in content.split("\n") if line.strip()]
                lines = [l for l in lines if l and len(l) > 1]

                if field == "tech_description":
                    # Technology Description goes to abstract
                    detail["abstract"] = " ".join(lines)
                elif field in ("applications", "development_stage"):
                    detail[field] = lines if len(lines) > 1 else lines[0] if lines else None
                elif field == "advantages":
                    detail["advantages"] = lines if len(lines) > 1 else [content] if content else None
                elif field == "ip_status":
                    ip_text = " ".join(lines)
                    detail["ip_status"] = ip_text
                    # Extract patent numbers
                    patent_nums = re.findall(r'\b\d{1,2},\d{3},\d{3}\b', ip_text)
                    if patent_nums:
                        detail["patent_numbers"] = patent_nums
                elif field == "publications":
                    pubs = [{"text": l} for l in lines if len(l) > 20 and not l.startswith("http")]
                    if pubs:
                        detail["publications"] = pubs
                elif field == "categories":
                    cats = [c.strip() for c in content.split(",") if c.strip()]
                    if cats:
                        detail["detail_categories"] = cats
                elif field == "inventors_section":
                    inventors = [l for l in lines if len(l) > 2 and not any(x in l.lower() for x in ["keywords", "home", "search"])]
                    if inventors:
                        detail["inventors"] = inventors
                elif field == "keywords_section":
                    kws = [l for l in lines if len(l) > 1 and l.lower() not in ["home", "search"]]
                    if kws:
                        detail["detail_keywords"] = kws

            return detail if len(detail) > 1 else None

        except Exception as e:
            logger.debug(f"Error scraping detail page {url}: {e}")
            return None

