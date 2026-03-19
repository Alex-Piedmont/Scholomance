"""Johns Hopkins University Technology Ventures scraper using Algolia API with Playwright detail fetching.

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
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

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
            logger.debug("Playwright browser initialized for JHU")

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
        """Scrape all technologies from JHU via Algolia API with Playwright detail fetching."""
        try:
            await self._init_session()
            self._seen_ids = set()

            self.log_progress("Fetching technology list from Algolia API")

            headers = {
                "X-Algolia-Application-Id": self.ALGOLIA_APP_ID,
                "X-Algolia-API-Key": self.ALGOLIA_API_KEY,
                "Content-Type": "application/json",
            }

            all_technologies: list[Technology] = []

            # Query each category separately to work around 1000 result limit
            for category in self.CATEGORIES:
                payload = {
                    "query": "",
                    "hitsPerPage": 1000,
                    "filters": f'"Technology Classifications.lvl0":"{category}"',
                    "attributesToRetrieve": ["*"],
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
                                new_count += 1
                                all_technologies.append(tech)

                        self.log_progress(f"Category '{category}': {len(hits)} hits, {new_count} new")

                except Exception as e:
                    self.log_error(f"Error querying category {category}", e)
                    continue

                self._page_count += 1
                await self.delay()

            # Fetch detail pages using Playwright for full content
            self.log_progress(f"Fetching detail pages for {len(all_technologies)} technologies")
            await self._init_browser()

            for i, tech in enumerate(all_technologies):
                try:
                    detail = await self.scrape_technology_detail(tech.url)
                    if detail:
                        tech.raw_data.update(detail)
                        # Update top-level fields from detail
                        if detail.get("abstract") and (not tech.description or "..." in tech.description):
                            tech.description = detail["abstract"]
                        if detail.get("inventors"):
                            tech.innovators = detail["inventors"]
                        if detail.get("detail_keywords"):
                            tech.keywords = detail["detail_keywords"]
                    await asyncio.sleep(self.delay_seconds)
                except Exception as e:
                    logger.debug(f"Error fetching detail for {tech.url}: {e}")

                if (i + 1) % 50 == 0:
                    self.log_progress(f"Enriched {i + 1}/{len(all_technologies)} technologies")

            for tech in all_technologies:
                self._tech_count += 1
                yield tech

            self.log_progress(
                f"Completed scraping: {self._tech_count} unique technologies"
            )

        finally:
            await self._close_session()
            await self._close_browser()

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

            # Get full description (preferred) or truncated
            full_description = item.get("descriptionFull", "")
            truncated_description = item.get("descriptionTruncated", "")

            # Parse structured sections from full description
            sections = self._parse_description_sections(full_description) if full_description else {}

            # Use short description from sections, or truncated, or full text
            description = (
                sections.get("short_description")
                or sections.get("abstract")
                or sections.get("background")
                or html_mod.unescape(truncated_description).strip()
                or html_mod.unescape(full_description[:2000]).strip()
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

            # Get patent status
            patent_statuses = item.get("patentStatuses", [])

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
                "patent_statuses": patent_statuses,
                "client_departments": item.get("clientDepartments"),
            }

            # Add parsed sections
            for key in ("abstract", "background", "short_description", "advantages",
                        "applications", "publications", "ip_status", "market_opportunity",
                        "development_stage", "benefit", "technical_problem", "solution"):
                if sections.get(key):
                    raw_data[key] = sections[key]

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

    @staticmethod
    def _parse_description_sections(text: str) -> dict:
        """Parse structured sections from Algolia descriptionFull text."""
        import html as html_mod

        text = html_mod.unescape(text)

        section_patterns = [
            ("short_description", r"(?:SHORT\s+DESCRIPTION|NOVELTY):?"),
            ("abstract", r"ABSTRACT:?"),
            ("background", r"(?:BACKGROUND|UNMET\s+NEED):?"),
            ("market_opportunity", r"MARKET\s+(?:OPPORTUNITY|APPLICATIONS?):?"),
            ("development_stage", r"(?:DEVELOPMENT\s+STAGE|STAGE\s+OF\s+DEVELOPMENT):?"),
            ("applications", r"APPLICATIONS:?"),
            ("advantages", r"(?:ADVANTAGES|VALUE\s+PROPOSITION):?"),
            ("publications", r"PUBLICATION(?:\(S\)|S)?:?"),
            ("ip_status", r"(?:IP\s+STATUS|PATENT\s+(?:STATUS|INFORMATION|DETAILS)):?"),
            ("benefit", r"BENEFITS?:?"),
            ("inventors_section", r"INVENTORS?:?"),
            ("technical_problem", r"(?:TECHNICAL\s+PROBLEM|PROBLEM\s+STATEMENT):?"),
            ("solution", r"(?:TECHNICAL\s+)?(?:SOLUTION|TECHNOLOGY\s+(?:OVERVIEW|SOLUTION)):?"),
        ]

        all_headers = "|".join(f"(?P<s{i}>{pat})" for i, (_, pat) in enumerate(section_patterns))
        # Require 2+ whitespace chars (or start of text) before a header to avoid
        # matching mid-sentence words like "research applications"
        header_re = re.compile(rf"(?:^|\s{{2,}})(?:{all_headers})\s*", re.IGNORECASE)

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
        """Scrape detailed information from a technology's detail page using Playwright.

        Playwright-rendered pages show: Case ID, Unmet Need, Technology Overview,
        Stage of Development, Patent Information (tab-separated table), Publications,
        Inventors, Category(s).

        User-visible pages show: Case ID, Problem Statement, Technology Solution,
        Development Level, Patent Details, Publication Details, Keywords.

        We match both sets of headings with alternation patterns.
        """
        if not url or not self._page:
            return None

        try:
            await self._page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(1)

            # Get text content
            text = await self._page.inner_text("body")
            detail: dict = {"url": url}

            # Section patterns — covers three known template variants:
            #   Newer: Unmet Need, Technology Overview, Stage of Development
            #   User-visible: Problem Statement, Technology Solution, Development Level
            #   Older: Novelty, Value Proposition, Technical Details, Looking for Partners
            sections = [
                ("case_id", r"Case\s+ID:?"),
                ("short_description", r"Novelty:?"),
                ("technical_problem", r"(?:Problem\s+Statement|Unmet\s+Need|Value\s+Proposition):?"),
                ("solution", r"(?:Technology\s+Solution|Technology\s+Overview|Technical\s+Details):?"),
                ("development_stage", r"(?:Development\s+Level|Stage\s+of\s+Development|Looking\s+for\s+Partners):?"),
                ("data_availability", r"Data\s+Availability:?"),
                ("patent_info", r"(?:Patent\s+Details|Patent\s+Information):?"),
                ("ip_status_inline", r"Patent\s+Status:"),
                ("publications", r"(?:Publication\s+Details|(?:Select\s+)?Publications?(?:/Associated\s+Cases)?):?"),
                ("keywords", r"(?:Keywords|Category\(s\)):?"),
                ("inventors_section", r"Inventors?:"),
            ]

            # Parse each section by finding boundaries
            for field, pattern in sections:
                match = re.search(pattern, text, re.IGNORECASE)
                if not match:
                    continue

                start = match.end()
                end = len(text)

                # Find next section start
                for _, next_pat in sections:
                    next_match = re.search(next_pat, text[start:], re.IGNORECASE)
                    if next_match:
                        candidate_end = start + next_match.start()
                        if candidate_end < end:
                            end = candidate_end

                # Find footer markers
                for footer in ["Direct Link:", "Subscribe for", "For Information, Contact",
                               "Get custom alerts", "© 20"]:
                    footer_idx = text.find(footer, start)
                    if 0 < footer_idx < end:
                        end = footer_idx

                content = text[start:end].strip()
                if not content:
                    continue

                # Clean lines (strip bullets/dashes)
                lines = [line.strip().lstrip("·•-").strip() for line in content.split("\n") if line.strip()]
                lines = [l for l in lines if l and len(l) > 1]

                if field == "case_id":
                    detail["case_id"] = lines[0] if lines else content.strip()
                elif field == "short_description":
                    detail["short_description"] = " ".join(lines)
                elif field == "data_availability":
                    detail["data_availability"] = " ".join(lines)
                elif field == "technical_problem":
                    detail["technical_problem"] = " ".join(lines)
                    detail["background"] = detail["technical_problem"]
                elif field == "solution":
                    detail["solution"] = " ".join(lines)
                    detail["abstract"] = detail["solution"]
                elif field == "development_stage":
                    detail["development_stage"] = " ".join(lines)
                elif field == "patent_info":
                    # Tab-separated table (Patent Information format)
                    patents = self._parse_patent_text(content)
                    if patents:
                        detail["patent_details"] = patents
                        statuses = []
                        for pat in patents:
                            status = pat.get("patent_status", "")
                            patent_no = pat.get("patent_no", "")
                            title = pat.get("title", "")
                            if status:
                                entry = status
                                if patent_no:
                                    entry += f" — {patent_no}"
                                if title:
                                    entry = f"{title}: {entry}"
                                statuses.append(entry)
                        if statuses:
                            detail["ip_status"] = "; ".join(statuses)
                elif field == "ip_status_inline":
                    # Inline format: "18/286,185 (Status: Pending)"
                    # Don't overwrite table-derived ip_status
                    if "ip_status" not in detail:
                        ip_text = " ".join(lines)
                        if ip_text:
                            detail["ip_status"] = ip_text
                elif field == "publications":
                    # Filter out "N/A" and noise
                    pubs = [l for l in lines if len(l) > 10 and l.lower() != "n/a"]
                    if pubs:
                        detail["publications"] = [{"text": p} for p in pubs]
                elif field == "keywords":
                    # Each line is a keyword (don't split on commas —
                    # category names like "Computers, Electronics & Software" contain commas)
                    kw = [l for l in lines if len(l) > 1]
                    if kw:
                        detail["detail_keywords"] = kw
                elif field == "inventors_section":
                    inventors = [l for l in lines
                                 if len(l) > 2
                                 and not any(x in l.lower() for x in
                                             ["category", "subscribe", "get custom", "save this"])]
                    if inventors:
                        detail["inventors"] = inventors

            # Parse publication links from <a> tags
            pub_links = await self._parse_publication_links()
            if pub_links:
                existing = detail.get("publications", [])
                for link in pub_links:
                    if not any(p.get("url") == link["url"] for p in existing):
                        existing.append(link)
                if existing:
                    detail["publications"] = existing

            return detail if len(detail) > 1 else None

        except Exception as e:
            logger.debug(f"Error scraping detail page {url}: {e}")
            return None

    @staticmethod
    def _parse_patent_text(content: str) -> list[dict]:
        """Parse tab-separated patent table from inner_text content.

        The patent info section in inner_text looks like:
        Title\\tApp Type\\tCountry\\tSerial No.\\tPatent No.\\tFile Date\\tIssued Date\\tExpire Date\\tPatent Status
        SOME TITLE\\tPCT: ...\\tUnited States\\t17/309,268\\t12,276,590\\t5/13/2021\\t...\\tGranted
        """
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        if not lines:
            return []

        # Find header line (contains tab-separated column names)
        header_idx = None
        for i, line in enumerate(lines):
            if "\t" in line and ("patent" in line.lower() or "serial" in line.lower()):
                header_idx = i
                break

        if header_idx is None:
            return []

        headers = [h.strip().lower() for h in lines[header_idx].split("\t")]
        header_map = {
            "title": "title",
            "app type": "app_type",
            "country": "country",
            "serial no.": "serial_no",
            "patent no.": "patent_no",
            "file date": "file_date",
            "issued date": "issued_date",
            "expire date": "expire_date",
            "patent status": "patent_status",
        }

        col_map = {}
        for i, h in enumerate(headers):
            for key, field in header_map.items():
                if key in h:
                    col_map[i] = field
                    break

        patents = []
        for line in lines[header_idx + 1:]:
            if "\t" not in line:
                continue
            cells = line.split("\t")
            if len(cells) < 3:
                continue
            patent = {}
            for i, cell in enumerate(cells):
                field = col_map.get(i)
                if field:
                    patent[field] = cell.strip()
            # Validate: must have at least a title or patent number
            if patent.get("title") or patent.get("patent_no") or patent.get("serial_no"):
                patents.append(patent)

        return patents

    async def _parse_publication_links(self) -> list[dict]:
        """Extract publication links from the detail page."""
        if not self._page:
            return []
        try:
            links = await self._page.evaluate("""() => {
                const allLinks = Array.from(document.querySelectorAll('a[href]'));
                const results = [];
                for (const a of allLinks) {
                    const href = a.href;
                    if (href && (href.includes('pubmed') || href.includes('doi.org') || href.includes('ncbi.nlm.nih.gov'))) {
                        results.push({text: a.innerText.trim() || href, url: href});
                    }
                }
                return results;
            }""")
            return links or []
        except Exception as e:
            logger.debug(f"Error parsing publication links: {e}")
            return []
