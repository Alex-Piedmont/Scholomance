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

            # Main description - look for product description content
            # TechPublisher uses a product-description-box or description div
            desc_box = soup.select_one(".product-description-box, .description, .c_content")
            if desc_box:
                detail["full_description"] = desc_box.get_text(separator="\n", strip=True)
                detail["description_html"] = str(desc_box)

            # If no description box found, try the main content area
            if "full_description" not in detail:
                # Look for the main text content after h1
                h1 = soup.find("h1")
                if h1:
                    content_parts = []
                    for sibling in h1.find_next_siblings():
                        if sibling.name in ("h2", "h3", "h4") and any(
                            kw in sibling.get_text().lower()
                            for kw in ["benefit", "feature", "application", "advantage", "author", "inventor"]
                        ):
                            break
                        if sibling.name == "p":
                            t = sibling.get_text(strip=True)
                            if t:
                                content_parts.append(t)
                    if content_parts:
                        detail["full_description"] = "\n".join(content_parts)

            # Parse sections by headings (h2, h3, strong)
            sections = {}
            for heading in soup.find_all(["h2", "h3", "strong"]):
                heading_text = heading.get_text(strip=True).lower()
                items = []

                # Collect list items after this heading
                next_el = heading.find_next_sibling()
                while next_el:
                    if next_el.name in ("h2", "h3", "strong") and next_el.get_text(strip=True):
                        break
                    if next_el.name == "ul":
                        for li in next_el.find_all("li"):
                            t = li.get_text(strip=True)
                            if t:
                                items.append(t)
                    elif next_el.name == "p":
                        t = next_el.get_text(strip=True)
                        if t:
                            items.append(t)
                    next_el = next_el.find_next_sibling()

                if items:
                    sections[heading_text] = items

            # Map sections to standard fields
            for key, items in sections.items():
                if "benefit" in key or "feature" in key:
                    detail["advantages"] = items
                elif "application" in key:
                    detail["applications"] = items
                elif "phase" in key or "development" in key or "stage" in key:
                    detail["development_stage"] = " ".join(items)

            # Collapsible sections (Authors, References, Supporting documents)
            for collapsible in soup.select(".collapsible-header"):
                header_text = collapsible.get_text(strip=True).lower()
                body = collapsible.find_next_sibling(class_="collapsible-body")
                if not body:
                    continue

                if "author" in header_text or "inventor" in header_text:
                    inventors = []
                    for item in body.select("a, .inventor-name, span"):
                        name = item.get_text(strip=True)
                        if name and len(name) > 2 and name not in inventors:
                            inventors.append(name)
                    if not inventors:
                        # Try plain text
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
