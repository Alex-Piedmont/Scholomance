"""Purdue Research Foundation scraper using Technology Publisher API."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import Technology
from .techpub_base import TechPublisherScraper

DETAIL_CONCURRENCY = 5


class PurdueScraper(TechPublisherScraper):
    """
    Scraper for Purdue Research Foundation's technology licensing portal.

    Purdue's Office of Technology Commercialization manages 400+ technologies
    across fields including AI/ML, biotechnology, semiconductors, and aerospace.
    """

    BASE_URL = "https://licensing.prf.org"
    UNIVERSITY_CODE = "purdue"
    UNIVERSITY_NAME = "Purdue Research Foundation"

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

            # Subtitle from h6
            h6 = soup.find("h6")
            if h6:
                detail["subtitle"] = h6.get_text(strip=True)

            # Product ID
            pid = soup.select_one(".product-id")
            if pid:
                m = re.search(r'Technology\s*No\.?\s*([\w\-]+)', pid.get_text())
                if m:
                    detail["technology_number"] = m.group(1).strip()

            # Parse the .description div which contains all content as <p> tags
            # with bold labels like <b>Advantages</b>:, Potential Applications:, etc.
            desc_div = soup.select_one(".description")
            if desc_div:
                self._parse_description_div(desc_div, detail)

            # Collapsible sections (Authors, Documents, Publications)
            for coll in soup.select(".collapsible-header"):
                htxt = coll.get_text(strip=True).lower()
                body = coll.find_next_sibling(class_="collapsible-body")
                if not body:
                    continue
                if "author" in htxt or "inventor" in htxt:
                    inventors = []
                    # Purdue uses nested <div><div>Name</div></div>
                    for div in body.select("div > div"):
                        n = div.get_text(strip=True)
                        if n and len(n) > 2 and n not in inventors:
                            inventors.append(n)
                    if not inventors:
                        for el in body.select("a, span"):
                            n = el.get_text(strip=True)
                            if n and len(n) > 2 and n not in inventors:
                                inventors.append(n)
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
                    for section in body.select(".section"):
                        a = section.find("a", href=True)
                        if not a:
                            continue
                        href = a["href"]
                        if not href.startswith("http"):
                            href = f"{self.BASE_URL}{href}"
                        # Get doc type and filename from the label divs
                        label_col = section.select_one(".col.s12, .col.l9")
                        if label_col:
                            divs = label_col.find_all("div", recursive=False)
                            doc_type = divs[0].get_text(strip=True) if len(divs) > 0 else ""
                            filename = divs[1].get_text(strip=True) if len(divs) > 1 else ""
                            name = f"{doc_type}: {filename}" if doc_type and filename else (filename or doc_type)
                        else:
                            name = a.get_text(strip=True)
                        docs.append({"name": name, "url": href})
                    if not docs:
                        for a in body.find_all("a", href=True):
                            href = a["href"]
                            if not href.startswith("http"):
                                href = f"{self.BASE_URL}{href}"
                            docs.append({"name": a.get_text(strip=True), "url": href})
                    if docs:
                        detail["supporting_documents"] = docs

            # Categories from links
            categories = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "searchresults" in href or "category" in href or "lvl0" in href:
                    cat = a.get_text(strip=True)
                    if cat and cat not in categories and len(cat) > 1:
                        categories.append(cat)
            if categories:
                detail["categories"] = categories

            # Use keywords as categories if no category links found
            if not detail.get("categories") and detail.get("keywords"):
                detail["categories"] = detail["keywords"]

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

            return detail

        except Exception as e:
            logger.debug(f"Error scraping detail page {url}: {e}")
            return None

    @staticmethod
    def _parse_description_div(desc_div, detail: dict) -> None:
        """Parse Purdue's .description div which has all sections as <p> tags with bold labels."""
        description_parts = []
        current_section = "description"

        for el in desc_div.children:
            if not el.name:
                continue

            text = el.get_text(strip=True)
            if not text:
                continue

            # Check for bold-label section headers within <p> tags
            bold = el.find("b")
            label = bold.get_text(strip=True).lower().rstrip(":") if bold else ""

            if "advantage" in label or "benefit" in label or "feature" in label:
                current_section = "advantages"
                # Content after the bold label in same <p>
                after = text.replace(bold.get_text(), "", 1).strip().lstrip(":")
                if after and after != "-":
                    detail.setdefault("advantages", []).append(after.lstrip("- "))
                continue
            elif "application" in label:
                current_section = "applications"
                after = text.replace(bold.get_text(), "", 1).strip().lstrip(":")
                if after and after != "-":
                    detail.setdefault("applications", []).append(after.lstrip("- "))
                continue
            elif "technology validation" in label or "tech validation" in label:
                current_section = "technology_validation"
                after = text.replace(bold.get_text(), "", 1).strip().lstrip(":")
                if after:
                    detail.setdefault("technology_validation", []).append(after.lstrip("- "))
                continue
            elif label.startswith("trl"):
                m = re.search(r'(\d)', text)
                if m:
                    detail["trl"] = m.group(1)
                current_section = "_skip"
                continue
            elif "intellectual" in label or "ip status" in label:
                current_section = "ip"
                after = text.replace(bold.get_text(), "", 1).strip().lstrip(":")
                if after:
                    detail["ip_text"] = after
                    if "utility" in after.lower():
                        detail["patent_status"] = "Filed"
                    elif "provisional" in after.lower():
                        detail["patent_status"] = "Provisional"
                    elif "granted" in after.lower() or "issued" in after.lower():
                        detail["patent_status"] = "Granted"
                continue
            elif "keyword" in label:
                after = text.replace(bold.get_text(), "", 1).strip().lstrip(":")
                kws = [k.strip() for k in after.split(",") if k.strip()]
                if kws:
                    detail["keywords"] = kws
                current_section = "_skip"
                continue
            elif label and ("potential" in text.lower()[:30] and "application" in text.lower()[:30]):
                current_section = "applications"
                after = text.split(":", 1)[1].strip() if ":" in text else ""
                if after:
                    detail.setdefault("applications", []).append(after.lstrip("- "))
                continue

            # Check for non-bold section headers like "Potential Applications:"
            if not bold:
                lower = text.lower()
                if lower.startswith("potential application") or lower.startswith("application"):
                    current_section = "applications"
                    after = text.split(":", 1)[1].strip() if ":" in text else ""
                    if after:
                        detail.setdefault("applications", []).append(after.lstrip("- "))
                    continue

            # Accumulate content into current section
            if current_section == "description":
                description_parts.append(text)
            elif current_section == "advantages":
                detail.setdefault("advantages", []).append(text.lstrip("- "))
            elif current_section == "applications":
                detail.setdefault("applications", []).append(text.lstrip("- "))
            elif current_section == "technology_validation":
                detail.setdefault("technology_validation", []).append(text.lstrip("- "))
            elif current_section == "ip":
                existing = detail.get("ip_text", "")
                detail["ip_text"] = (existing + " " + text).strip() if existing else text
                if "utility" in text.lower():
                    detail["patent_status"] = "Filed"
                elif "provisional" in text.lower():
                    detail["patent_status"] = "Provisional"

        if description_parts:
            detail["full_description"] = "\n".join(description_parts)
