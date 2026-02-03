"""University of Minnesota Technology Commercialization scraper using Technology Publisher API."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import Technology
from .techpub_base import TechPublisherScraper

DETAIL_CONCURRENCY = 5


class MinnesotaScraper(TechPublisherScraper):
    """
    Scraper for University of Minnesota's Technology Commercialization portal.

    UMN is a leader in technology transfer with 3,200+ current licenses,
    offering technologies in agriculture, engineering, life sciences, and software.
    """

    BASE_URL = "https://license.umn.edu"
    UNIVERSITY_CODE = "minnesota"
    UNIVERSITY_NAME = "University of Minnesota Technology Commercialization"

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(delay_seconds=delay_seconds)

    async def _fetch_detail(self, tech: Technology, semaphore: asyncio.Semaphore) -> Technology:
        """Fetch detail page for a technology and merge data."""
        async with semaphore:
            try:
                detail = await self.scrape_technology_detail(tech.url)
                if detail:
                    # Clean HTML from text fields
                    for key in ("abstract", "full_description", "development_stage", "publications"):
                        raw = detail.get(key)
                        if raw and isinstance(raw, str) and "<" in raw:
                            from bs4 import BeautifulSoup as BS
                            s = BS(raw, "html.parser")
                            raw = s.get_text(separator=" ", strip=True)
                            raw = raw.replace('\xa0', ' ').replace('&nbsp;', ' ')
                            raw = re.sub(r'[ \t]+', ' ', raw)
                            detail[key] = raw.strip()

                    tech.raw_data.update(detail)
                    if detail.get("abstract"):
                        tech.description = detail["abstract"]
                    elif detail.get("full_description") and not tech.description:
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

            # Technology number from page content
            text = soup.get_text()
            tech_num_match = re.search(r'(?:Technology\s*#?|Tech\s*(?:No\.?|Number):?\s*)(\d{6,})', text)
            if tech_num_match:
                detail["technology_number"] = tech_num_match.group(1)

            # IP Status
            ip_match = re.search(r'IP\s*Status[:\s]*([^\n<]+)', text)
            if ip_match:
                detail["ip_status"] = ip_match.group(1).strip()
                detail["patent_status"] = detail["ip_status"]

            # Application/Patent number
            app_match = re.search(r'Application\s*#?[:\s]*([^\n<]+)', text)
            if app_match:
                detail["application_number"] = app_match.group(1).strip()

            # Parse the description div for structured sections
            desc_div = soup.select_one(".description.grey-text")
            if desc_div:
                section_keywords = {
                    "benefits and features", "benefits", "features", "advantages",
                    "applications", "application",
                    "phase of development", "development stage", "stage of development",
                    "researchers", "publications", "references", "citations",
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
                        # Check if this <p> is a section heading (contains <b> with known keyword)
                        b_tag = child.find("b") or child.find("strong")
                        is_heading = False
                        if b_tag:
                            b_text = b_tag.get_text(strip=True).rstrip(":").strip().lower()
                            if b_text in section_keywords:
                                is_heading = True

                        if is_heading:
                            if current_parts:
                                sections.append((current_heading, current_parts))
                            current_heading = txt.rstrip(":")
                            current_parts = []
                        else:
                            current_parts.append(txt)
                    elif child.name == "ul":
                        for li in child.find_all("li"):
                            t = li.get_text(strip=True)
                            if t:
                                current_parts.append(t)
                    elif child.name in ("h2", "h3"):
                        if current_parts:
                            sections.append((current_heading, current_parts))
                        current_heading = txt
                        current_parts = []
                        # Collect inline content after h2/h3 (e.g. <b>TRL: 8-9</b><br/>text)
                        nxt = child.next_sibling
                        while nxt:
                            if hasattr(nxt, "name") and nxt.name in ("p", "ul", "h2", "h3", "div"):
                                break
                            t = nxt.get_text(strip=True) if hasattr(nxt, "get_text") else str(nxt).strip()
                            if t:
                                current_parts.append(t)
                            nxt = nxt.next_sibling

                if current_parts:
                    sections.append((current_heading, current_parts))

                # Map sections to standard field names
                description_parts = []
                abstract_parts: list[str] = []

                for heading, parts in sections:
                    if heading is None:
                        description_parts.extend(parts)
                        continue
                    h_lower = heading.lower().rstrip(":")
                    text = "\n\n".join(parts)

                    if "benefit" in h_lower or "feature" in h_lower or "advantage" in h_lower:
                        detail["advantages"] = parts
                    elif "application" in h_lower:
                        detail["applications"] = parts
                    elif "development" in h_lower or "stage" in h_lower or "phase" in h_lower:
                        detail["development_stage"] = text
                    elif "researcher" in h_lower:
                        # Parse researcher names from the h2's sibling <ul> in the soup
                        researchers_heading = desc_div.find("h2", string=re.compile(r"Researcher", re.I))
                        if researchers_heading:
                            ul = researchers_heading.find_next_sibling("ul")
                            if ul:
                                names = []
                                for li in ul.find_all("li"):
                                    b = li.find("b") or li.find("strong")
                                    if b:
                                        # Name is in the bold tag, strip degree suffixes
                                        raw_name = b.get_text(strip=True)
                                        # Remove trailing degree like ", PhD" or ", MD"
                                        raw_name = re.sub(r',?\s*(?:PhD|MD|MS|PharmD|DVM|DO|JD|DrPH)$', '', raw_name).strip()
                                        if raw_name:
                                            names.append(raw_name)
                                if names:
                                    detail["inventors"] = names
                        if not detail.get("inventors") and parts:
                            detail["researchers"] = parts
                    elif "publication" in h_lower or "reference" in h_lower or "citation" in h_lower:
                        detail["publications"] = text
                    else:
                        # Sub-technology heading — add to abstract
                        abstract_parts.append(text)

                if description_parts:
                    detail["full_description"] = "\n\n".join(description_parts)
                if abstract_parts:
                    detail["abstract"] = "\n\n".join(abstract_parts)

            # Collapsible sections (Authors, References, Supporting documents)
            for collapsible in soup.select(".collapsible-header"):
                header_text = collapsible.get_text(strip=True).lower()
                body = collapsible.find_next_sibling(class_="collapsible-body")
                if not body:
                    continue

                if "author" in header_text or "inventor" in header_text:
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
                        for item in body.select("a, .inventor-name, span"):
                            name = item.get_text(strip=True)
                            if name and len(name) > 2 and name not in inventors:
                                inventors.append(name)
                    if not inventors:
                        names = [n.strip() for n in body.get_text().split(",") if n.strip()]
                        inventors = [n for n in names if len(n) > 2]
                    if inventors:
                        detail["inventors"] = inventors

                elif "reference" in header_text or "publication" in header_text:
                    refs = []
                    for item in body.find_all(["a", "li", "p"]):
                        t = item.get_text(strip=True)
                        href = item.get("href", "") if item.name == "a" else ""
                        if t:
                            entry = {"text": t}
                            if href:
                                entry["url"] = href
                            refs.append(entry)
                    if refs:
                        detail["publications"] = refs

                elif "document" in header_text:
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

            # Contact information
            contact = {}
            email_link = soup.select_one("a[href^='mailto:']")
            if email_link:
                contact["email"] = email_link["href"].replace("mailto:", "").split("?")[0]
                # Try to get name from nearby text
                parent = email_link.find_parent()
                if parent:
                    parent_text = parent.get_text(strip=True)
                    if parent_text and parent_text != contact["email"]:
                        contact["name"] = parent_text.replace(contact["email"], "").strip().rstrip(",").strip()
            if contact:
                detail["contact"] = contact

            # Licensing info
            licence_el = soup.select_one(".modal-licence, .license-info")
            if licence_el:
                detail["licensing_info"] = licence_el.get_text(strip=True)

            # Patent info from tables
            patent_table = soup.find("table")
            if patent_table:
                rows = patent_table.find_all("tr")
                if len(rows) > 1:
                    headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
                    patents = []
                    for row in rows[1:]:
                        cells = [td.get_text(strip=True) for td in row.find_all("td")]
                        if cells:
                            patent_entry = dict(zip(headers, cells))
                            patents.append(patent_entry)
                    if patents:
                        detail["patent_table"] = patents
                        if not detail.get("patent_status"):
                            for p in patents:
                                if p.get("patent no.") or p.get("patent number"):
                                    detail["patent_status"] = "Granted"
                                    break
                                elif p.get("patent status", "").lower() == "pending":
                                    detail["patent_status"] = "Pending"

            return detail

        except Exception as e:
            logger.debug(f"Error scraping detail page {url}: {e}")
            return None
