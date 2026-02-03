"""University of Washington CoMotion scraper using Technology Publisher API."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import Technology
from .techpub_base import TechPublisherScraper

DETAIL_CONCURRENCY = 5


class UWScraper(TechPublisherScraper):
    """
    Scraper for University of Washington's CoMotion technology portal.

    CoMotion is UW's innovation hub, offering technologies across categories
    including cleantech, software, therapeutics, and research tools.
    """

    BASE_URL = "https://els2.comotion.uw.edu"
    UNIVERSITY_CODE = "uw"
    UNIVERSITY_NAME = "University of Washington CoMotion"

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(delay_seconds=delay_seconds)

    async def _fetch_detail(self, tech: Technology, semaphore: asyncio.Semaphore) -> Technology:
        """Fetch detail page for a technology and merge data."""
        async with semaphore:
            try:
                detail = await self.scrape_technology_detail(tech.url)
                if detail:
                    tech.raw_data.update(detail)
                    # Prefer abstract or full_description for top-level description
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
            text = soup.get_text()

            # Reference number (e.g., BDP 8691)
            ref_match = re.search(r'(?:BDP|Ref\.?\s*(?:No\.?|Number)?)[:\s]*([A-Z0-9\s\-]+)', text)
            if ref_match:
                detail["reference_number"] = ref_match.group(1).strip()

            # Description
            desc_box = soup.select_one(".product-description-box, .description, .c_content")
            if desc_box:
                detail["full_description"] = desc_box.get_text(separator="\n", strip=True)
            else:
                h1 = soup.find("h1")
                if h1:
                    parts = []
                    for sib in h1.find_next_siblings():
                        if sib.name in ("h2", "h3", "h4", "strong") and any(
                            kw in sib.get_text().lower()
                            for kw in ["benefit", "feature", "application", "advantage",
                                        "author", "inventor", "problem", "solution", "competitive"]
                        ):
                            break
                        if sib.name in ("p", "div") and sib.get_text(strip=True):
                            parts.append(sib.get_text(strip=True))
                    if parts:
                        detail["full_description"] = "\n".join(parts)

            # Structured sections by headings (UW uses h6 for section headers)
            heading_tags = ["h2", "h3", "h4", "h5", "h6", "strong"]
            for heading in soup.find_all(heading_tags):
                htxt = heading.get_text(strip=True).lower().rstrip(":")
                items = []
                nxt = heading.find_next_sibling()
                while nxt:
                    if nxt.name in heading_tags and nxt.get_text(strip=True):
                        break
                    if nxt.name == "ul":
                        for li in nxt.find_all("li"):
                            t = li.get_text(strip=True)
                            if t:
                                items.append(t)
                    elif nxt.name == "p" and nxt.get_text(strip=True):
                        items.append(nxt.get_text(strip=True))
                    nxt = nxt.find_next_sibling()
                if not items:
                    continue
                if "problem" in htxt:
                    detail["background"] = "\n\n".join(items)
                elif "solution" in htxt:
                    detail["abstract"] = "\n\n".join(items)
                elif "competitive" in htxt or "advantage" in htxt or "benefit" in htxt:
                    detail["advantages"] = items
                elif "application" in htxt:
                    detail["applications"] = items
                elif "development" in htxt or "stage" in htxt or "phase" in htxt:
                    detail["development_stage"] = "\n\n".join(items)
                elif "patent" in htxt:
                    detail["ip_status"] = "\n\n".join(items)

            # Collapsible sections
            for coll in soup.select(".collapsible-header"):
                htxt = coll.get_text(strip=True).lower()
                body = coll.find_next_sibling(class_="collapsible-body")
                if not body:
                    continue
                if "author" in htxt or "inventor" in htxt:
                    inventors = []
                    # Authors are in nested divs (like WARF)
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

            # Categories
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

            return detail

        except Exception as e:
            logger.debug(f"Error scraping detail page {url}: {e}")
            return None
