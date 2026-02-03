"""University of Michigan Innovation Partnerships scraper."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology

DETAIL_CONCURRENCY = 5


class UMichScraper(BaseScraper):
    """Scraper for University of Michigan's available inventions portal."""

    BASE_URL = "https://available-inventions.umich.edu"
    API_URL = f"{BASE_URL}/autocomplete/products"

    def __init__(self, delay_seconds: float = 0.5):
        super().__init__(
            university_code="umich",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "University of Michigan Innovation Partnerships"

    async def _init_session(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for UMich")

    async def _close_session(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def _fetch_detail(self, tech: Technology, semaphore: asyncio.Semaphore) -> Technology:
        """Fetch detail page for a technology and merge data."""
        async with semaphore:
            try:
                detail = await self.scrape_technology_detail(tech.url)
                if detail:
                    tech.raw_data.update(detail)
                    if detail.get("abstract"):
                        tech.description = detail["abstract"]
                    elif detail.get("subtitle"):
                        tech.description = detail["subtitle"]
                    if detail.get("inventors"):
                        tech.innovators = detail["inventors"]
                    if detail.get("categories"):
                        tech.keywords = detail["categories"]
                    if detail.get("patent_status"):
                        tech.patent_status = detail["patent_status"]
                await asyncio.sleep(self.delay_seconds)
            except Exception as e:
                logger.debug(f"Error fetching detail for {tech.url}: {e}")
        return tech

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from UMich with detail page enrichment."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology list from API")

            params = {"term": ""}
            async with self._session.get(self.API_URL, params=params) as response:
                if response.status != 200:
                    self.log_error(f"API returned status {response.status}")
                    return

                data = await response.json()
                total = len(data)
                self.log_progress(f"Found {total} technologies")

                all_technologies = []
                for i, item in enumerate(data):
                    tech = self._parse_api_item(item)
                    if tech:
                        all_technologies.append(tech)
                    if (i + 1) % 100 == 0:
                        self.log_progress(f"Processed {i + 1}/{total} technologies")

            self.log_progress(f"Fetching detail pages for {len(all_technologies)} technologies")
            semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)
            tasks = [self._fetch_detail(tech, semaphore) for tech in all_technologies]
            enriched = await asyncio.gather(*tasks)

            for tech in enriched:
                self._tech_count += 1
                yield tech

            self._page_count = 1
            self.log_progress(f"Completed scraping: {self._tech_count} technologies")

        finally:
            await self._close_session()

    async def scrape_page(self, page_num: int) -> list[Technology]:
        if page_num != 1:
            return []
        technologies = []
        async for tech in self.scrape():
            technologies.append(tech)
        return technologies

    def _parse_api_item(self, item: dict) -> Optional[Technology]:
        """Parse a technology item from the API response."""
        try:
            name = item.get("name", "").strip()
            if not name:
                return None

            attrs = item.get("dataAttributes", {})
            tech_id = str(attrs.get("id", ""))
            url_path = attrs.get("url", "")

            url = f"{self.BASE_URL}/{url_path}" if url_path else ""

            if not tech_id and url_path:
                tech_id = url_path.replace("product/", "")

            if not tech_id:
                tech_id = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower())[:50]

            raw_data = {
                "id": tech_id,
                "name": name,
                "url": url,
                "url_path": url_path,
            }

            return Technology(
                university="umich",
                tech_id=tech_id,
                title=name,
                url=url,
                description=None,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing API item: {e}")
            return None

    async def scrape_technology_detail(self, url: str) -> Optional[dict]:
        """Scrape detailed information from a technology's detail page."""
        if not url:
            return None
        await self._init_session()

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            detail: dict = {}
            text = soup.get_text()

            # Technology number from meta description
            meta_desc = soup.find("meta", attrs={"name": "description"})
            if meta_desc:
                content = meta_desc.get("content", "")
                if "TECHNOLOGY NUMBER:" in content:
                    detail["technology_number"] = content.replace("TECHNOLOGY NUMBER:", "").strip()

            # Parse the description div for structured sections
            # UMich pages have malformed HTML with h2 tags nested inside <p> tags,
            # so we walk all descendants and segment by h2 headings.
            desc_div = soup.select_one(".description.grey-text")
            if desc_div:
                from bs4 import NavigableString
                sections: list[tuple[str | None, list[str]]] = []
                current_heading = None
                current_parts: list[str] = []

                for el in desc_div.descendants:
                    if hasattr(el, "name") and el.name == "h2":
                        if current_heading is not None or current_parts:
                            sections.append((current_heading, current_parts))
                        current_heading = el.get_text(strip=True)
                        current_parts = []
                    elif isinstance(el, NavigableString):
                        t = el.strip()
                        if t and not (hasattr(el.parent, "name") and el.parent.name == "h2"):
                            current_parts.append(t)

                if current_heading is not None or current_parts:
                    sections.append((current_heading, current_parts))

                # Map sections to standard field names
                for heading, parts in sections:
                    if heading is None:
                        continue
                    h_lower = heading.lower()
                    text = " ".join(parts)

                    if "overview" in h_lower:
                        detail["subtitle"] = "\n\n".join(parts)
                    elif "background" in h_lower:
                        detail["background"] = text
                    elif "innovation" in h_lower or "solution" in h_lower:
                        detail["abstract"] = text
                    elif "problem" in h_lower:
                        if not detail.get("background"):
                            detail["background"] = text
                    elif "benefit" in h_lower or "feature" in h_lower or "advantage" in h_lower or "competitive" in h_lower:
                        detail["advantages"] = parts
                    elif h_lower in ("application", "applications") or ("application" in h_lower and "patent" not in h_lower):
                        detail["applications"] = parts
                    elif "intellectual property" in h_lower or "patent" in h_lower:
                        detail["ip_status"] = text
                    elif "publication" in h_lower:
                        detail["publications"] = text
                    elif "development" in h_lower or "stage" in h_lower or "phase" in h_lower:
                        detail["development_stage"] = text
                    elif "indication" in h_lower:
                        detail["market_application"] = text

            # Collapsible sections (Authors, References, Documents)
            for coll in soup.select(".collapsible-header"):
                htxt = coll.get_text(strip=True).lower()
                body = coll.find_next_sibling(class_="collapsible-body")
                if not body:
                    continue
                if "author" in htxt or "inventor" in htxt:
                    inventors = []
                    for div in body.find_all("div", recursive=False):
                        inner = div.find("div")
                        if inner:
                            n = inner.get_text(strip=True)
                        else:
                            n = div.get_text(strip=True)
                        if n and len(n) > 2 and n not in inventors:
                            inventors.append(n)
                    if not inventors:
                        for el in body.select("a, span"):
                            n = el.get_text(strip=True)
                            if n and len(n) > 2 and n not in inventors:
                                inventors.append(n)
                    if not inventors:
                        inventors = [n.strip() for n in body.get_text().split(",") if len(n.strip()) > 2]
                    if inventors:
                        detail["inventors"] = inventors
                elif "reference" in htxt or "publication" in htxt:
                    refs = []
                    for el in body.find_all(["a", "li", "p"]):
                        t = el.get_text(strip=True)
                        if t:
                            entry = {"text": t}
                            if el.name == "a" and el.get("href"):
                                entry["url"] = el["href"]
                            refs.append(entry)
                    if refs:
                        detail["publications"] = refs
                elif "document" in htxt:
                    docs = []
                    for a in body.find_all("a", href=True):
                        docs.append({"name": a.get_text(strip=True), "url": a["href"]})
                    if docs:
                        detail["supporting_documents"] = docs

            # Categories/Tags
            categories = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "searchresults" in href or "category" in href or "lvl0" in href:
                    cat = a.get_text(strip=True)
                    if cat and cat not in categories and len(cat) > 1:
                        categories.append(cat)
            if categories:
                detail["categories"] = categories

            # Contact
            contact = {}
            email_link = soup.select_one("a[href^='mailto:']")
            if email_link:
                contact["email"] = email_link["href"].replace("mailto:", "").split("?")[0]
                parent = email_link.find_parent()
                if parent:
                    pt = parent.get_text(strip=True)
                    if pt != contact["email"]:
                        contact["name"] = pt.replace(contact["email"], "").strip().rstrip(",").strip()
            if contact:
                detail["contact"] = contact

            # Patent table
            patent_table = soup.find("table")
            if patent_table:
                rows = patent_table.find_all("tr")
                if len(rows) > 1:
                    headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
                    patents = []
                    for row in rows[1:]:
                        cells = [td.get_text(strip=True) for td in row.find_all("td")]
                        if cells:
                            patents.append(dict(zip(headers, cells)))
                    if patents:
                        detail["patent_table"] = patents
                        if not detail.get("patent_status"):
                            for p in patents:
                                if p.get("patent no.") or p.get("patent number"):
                                    detail["patent_status"] = "Granted"
                                    break

            # Patent numbers from links
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "patents.google" in href or "patft.uspto" in href:
                    pn = a.get_text(strip=True)
                    if pn:
                        detail.setdefault("patent_numbers", []).append(pn)
                        detail["patent_status"] = "Granted"

            # Licensing info
            licence_el = soup.select_one(".modal-licence, .license-info")
            if licence_el:
                detail["licensing_info"] = licence_el.get_text(strip=True)

            return detail

        except Exception as e:
            logger.debug(f"Error fetching technology detail: {e}")
            return None

    # Backwards compatibility methods
    async def _init_browser(self) -> None:
        await self._init_session()

    async def _close_browser(self) -> None:
        await self._close_session()
