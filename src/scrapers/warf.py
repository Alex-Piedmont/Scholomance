"""Wisconsin Alumni Research Foundation (WARF) scraper using Technology Publisher API."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import Technology
from .techpub_base import TechPublisherScraper

DETAIL_CONCURRENCY = 5


class WARFScraper(TechPublisherScraper):
    """
    Scraper for WARF's Express Licensing technology portal.

    WARF manages technology transfer for the University of Wisconsin-Madison,
    with 2,000+ patented technologies available for licensing.
    """

    BASE_URL = "https://expresslicensing.warf.org"
    UNIVERSITY_CODE = "warf"
    UNIVERSITY_NAME = "Wisconsin Alumni Research Foundation"

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(delay_seconds=delay_seconds)

    async def _fetch_detail(self, tech: Technology, semaphore: asyncio.Semaphore) -> Technology:
        """Fetch detail page for a technology and merge data."""
        async with semaphore:
            try:
                detail = await self.scrape_technology_detail(tech.url)
                if detail:
                    tech.raw_data.update(detail)
                    if detail.get("full_description") and not tech.description:
                        tech.description = detail["full_description"]
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
        """Scrape all technologies with detail page enrichment."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology list from API")

            params = {"term": ""}
            async with self._session.get(self.api_url, params=params) as response:
                if response.status != 200:
                    self.log_error(f"API returned status {response.status}")
                    return

                data = await response.json()
                total = len(data)
                self.log_progress(f"Found {total} technologies")

                all_technologies = []
                for i, item in enumerate(data):
                    tech = self._parse_item(item)
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

    async def scrape_technology_detail(self, url: str) -> Optional[dict]:
        """Scrape detailed information from a technology's detail page."""
        if not url:
            return None
        await self._init_session()

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.debug(f"Detail page returned {resp.status}: {url}")
                    return None
                html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            detail: dict = {}
            text = soup.get_text()

            # WARF ID (e.g., P07254US)
            warf_match = re.search(r'(P\d{5}[A-Z]{2})\s*\(?(PAT|APP)?\)?', text)
            if warf_match:
                detail["warf_id"] = warf_match.group(1)
                if warf_match.group(2) == "PAT":
                    detail["patent_status"] = "Granted"
                elif warf_match.group(2) == "APP":
                    detail["patent_status"] = "Pending"

            # Description - subtitle in h6 or main paragraphs
            h6 = soup.find("h6")
            if h6:
                detail["subtitle"] = h6.get_text(strip=True)

            # Parse the description div for structured sections
            desc_div = soup.select_one(".description.grey-text")
            if desc_div:
                # Known section heading patterns
                section_keywords = {
                    "invention summary", "the invention", "invention",
                    "overview", "applications", "application",
                    "key benefits", "key benefit", "benefits", "advantages",
                    "included ip", "available ip", "intellectual property",
                }

                current_heading = None
                current_parts: list[str] = []
                sections: list[tuple[str | None, list[str]]] = []

                for child in desc_div.children:
                    if not hasattr(child, "name") or not child.name:
                        continue
                    txt = child.get_text(strip=True)
                    if not txt:
                        continue

                    if child.name == "p":
                        # Check if this <p> is a section heading
                        # Headings are typically short and match known patterns
                        txt_clean = txt.rstrip(":").strip()
                        txt_lower = txt_clean.lower()
                        # Also handle "P100054: Title" sub-technology headers
                        is_sub_tech = bool(re.match(r'^P\d{5,}', txt_clean))
                        is_heading = txt_lower in section_keywords or is_sub_tech
                        # Also match "Overview:" or "The Invention:" inline at start
                        if not is_heading and ":" in txt[:40]:
                            prefix = txt.split(":", 1)[0].strip().lower()
                            if prefix in section_keywords or prefix in (
                                "overview", "the invention", "invention summary",
                                "applications", "key benefits",
                            ):
                                is_heading = True
                                # Split: heading is the prefix, first content is the rest
                                rest = txt.split(":", 1)[1].strip()
                                if rest:
                                    current_parts_save = current_parts
                                    if current_parts:
                                        sections.append((current_heading, current_parts))
                                    current_heading = txt_clean.split(":")[0].strip()
                                    current_parts = [rest]
                                    continue

                        if is_heading:
                            if current_parts:
                                sections.append((current_heading, current_parts))
                            current_heading = txt_clean
                            current_parts = []
                        else:
                            current_parts.append(txt)
                    elif child.name == "ul":
                        for li in child.find_all("li"):
                            t = li.get_text(strip=True)
                            if t:
                                current_parts.append(t)

                if current_parts:
                    sections.append((current_heading, current_parts))

                # Map sections to standard field names
                description_parts = []
                abstract_parts: list[str] = []
                all_advantages: list[str] = []
                all_applications: list[str] = []
                ip_items: list[str] = []

                for heading, parts in sections:
                    if heading is None:
                        description_parts.extend(parts)
                        continue
                    h_lower = heading.lower().rstrip(":")
                    text = "\n\n".join(parts)

                    if "invention" in h_lower or "overview" in h_lower:
                        abstract_parts.append(text)
                    elif "benefit" in h_lower or "advantage" in h_lower:
                        all_advantages.extend(parts)
                    elif "application" in h_lower:
                        all_applications.extend(parts)
                    elif "included ip" in h_lower or "available ip" in h_lower or "intellectual" in h_lower:
                        ip_items.extend(parts)
                    elif re.match(r'^P\d{5,}', heading):
                        # Sub-technology header — include in abstract
                        abstract_parts.append(f"**{heading}**\n{text}")
                    else:
                        description_parts.append(text)

                if description_parts:
                    detail["full_description"] = "\n\n".join(description_parts)
                if abstract_parts:
                    detail["abstract"] = "\n\n".join(abstract_parts)
                if all_advantages:
                    detail["advantages"] = all_advantages
                if all_applications:
                    detail["applications"] = all_applications
                if ip_items:
                    detail["ip_text"] = "\n".join(ip_items)

            # Collapsible sections
            for coll in soup.select(".collapsible-header"):
                htxt = coll.get_text(strip=True).lower()
                body = coll.find_next_sibling(class_="collapsible-body")
                if not body:
                    continue
                if "author" in htxt or "inventor" in htxt:
                    inventors = []
                    # Authors are in nested divs
                    for div in body.find_all("div", recursive=False):
                        inner = div.find("div")
                        if inner:
                            n = inner.get_text(strip=True)
                        else:
                            n = div.get_text(strip=True)
                        if n and len(n) > 2 and n not in inventors:
                            inventors.append(n)
                    if not inventors:
                        # Fallback: try a/span or comma-separated
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

            # Categories from breadcrumb or links
            categories = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "searchresults" in href or "category" in href or "lvl0" in href:
                    cat = a.get_text(strip=True)
                    if cat and cat not in categories and len(cat) > 1:
                        categories.append(cat)
            if categories:
                detail["categories"] = categories

            # Licensing terms
            licence_match = re.search(r'\$[\d,]+\.?\d*', text)
            if licence_match:
                detail["license_price"] = licence_match.group(0)
            exp_match = re.search(r'Expir\w+[:\s]*([\d\-/]+)', text)
            if exp_match:
                detail["license_expiration"] = exp_match.group(1)

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

            return detail

        except Exception as e:
            logger.debug(f"Error scraping detail page {url}: {e}")
            return None
