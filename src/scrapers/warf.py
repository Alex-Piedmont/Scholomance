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

            # Subtitle from first h6
            h6 = soup.find("h6")
            if h6:
                detail["subtitle"] = h6.get_text(strip=True)

            # Parse structured sections from description div
            # WARF uses <b> tags inside <p> elements as section headers:
            #   <p><b>Overview: </b>text...</p>
            #   <p><b>Applications</b></p><ul>...</ul>
            desc_div = soup.select_one(".description.grey-text") or soup.select_one(".product-description-box, .description, .c_content")
            if desc_div:
                current_section = None
                current_items = []

                def _flush_section(section_name, items):
                    if not items:
                        return
                    sn = section_name.lower().rstrip(":").strip()
                    if "overview" in sn:
                        detail["full_description"] = "\n".join(items)
                    elif "invention" in sn:
                        detail["invention"] = "\n".join(items)
                    elif "key benefit" in sn or "benefit" in sn or "advantage" in sn:
                        detail["advantages"] = items
                    elif "application" in sn:
                        detail["applications"] = items
                    elif "available ip" in sn or "intellectual" in sn or "included ip" in sn:
                        detail["available_ip"] = items
                    elif "licensing" in sn:
                        detail["licensing_info"] = "\n".join(items)

                for el in desc_div.children:
                    if not hasattr(el, 'name') or not el.name:
                        continue
                    if el.name == "p":
                        bold = el.find("b")
                        if bold:
                            label = bold.get_text(strip=True)
                            # Flush previous section
                            if current_section:
                                _flush_section(current_section, current_items)
                            current_section = label
                            current_items = []
                            # Text after the bold tag in the same <p>
                            rest = el.get_text(strip=True).replace(label, "", 1).strip()
                            if rest:
                                current_items.append(rest)
                        elif current_section and el.get_text(strip=True):
                            current_items.append(el.get_text(strip=True))
                    elif el.name == "ul" and current_section:
                        for li in el.find_all("li"):
                            t = li.get_text(strip=True)
                            if t:
                                current_items.append(t)

                # Flush last section
                if current_section:
                    _flush_section(current_section, current_items)

                # Fallback: use full text if no structured sections found
                if "full_description" not in detail and "invention" not in detail:
                    detail["full_description"] = desc_div.get_text(separator="\n", strip=True)

            # Collapsible sections
            for coll in soup.select(".collapsible-header"):
                htxt = coll.get_text(strip=True).lower()
                body = coll.find_next_sibling(class_="collapsible-body")
                if not body:
                    continue
                if "author" in htxt or "inventor" in htxt:
                    inventors = []
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
