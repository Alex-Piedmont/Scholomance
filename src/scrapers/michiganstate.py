"""Michigan State University scraper using RSS feed."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import Technology
from .rss_base import RSSBaseScraper

DETAIL_CONCURRENCY = 5


class MichiganStateScraper(RSSBaseScraper):
    """Scraper for Michigan State University's technology licensing portal."""

    BASE_URL = "https://msut.technologypublisher.com"
    UNIVERSITY_CODE = "michiganstate"
    UNIVERSITY_NAME = "Michigan State University Technologies"

    async def _fetch_detail(self, tech: Technology, semaphore: asyncio.Semaphore) -> Technology:
        """Fetch detail page for a technology and merge data."""
        async with semaphore:
            try:
                detail = await self.scrape_technology_detail(tech.url)
                if detail:
                    tech.raw_data.update(detail)
                    if detail.get("full_description") and not tech.description:
                        tech.description = detail["full_description"]
                    elif detail.get("full_description") and tech.description and len(detail["full_description"]) > len(tech.description):
                        tech.description = detail["full_description"]
                    # Clean non-breaking spaces and HTML entities
                    if tech.description:
                        tech.description = tech.description.replace('\xa0', ' ').replace('&nbsp;', ' ').strip()
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
        """Scrape all technologies from RSS feed with detail page enrichment."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology list from RSS feed")

            async with self._session.get(self.rss_url) as response:
                if response.status != 200:
                    self.log_error(f"RSS feed returned status {response.status}")
                    return

                import xml.etree.ElementTree as ET
                content = await response.text()
                try:
                    root = ET.fromstring(content)
                except ET.ParseError as e:
                    self.log_error(f"Failed to parse RSS feed: {e}")
                    return

                channel = root.find("channel")
                if channel is None:
                    self.log_error("No channel found in RSS feed")
                    return

                items = channel.findall("item")
                total = len(items)
                self.log_progress(f"Found {total} technologies in RSS feed")

                all_technologies = []
                for i, item in enumerate(items):
                    tech = self._parse_rss_item(item)
                    if tech:
                        all_technologies.append(tech)
                    if (i + 1) % 50 == 0:
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

            # Case ID
            case_match = re.search(r'Case\s*(?:ID|#)[:\s]*([A-Z0-9\-]+)', text)
            if case_match:
                detail["case_id"] = case_match.group(1).strip()

            pub_match = re.search(r'Web\s*Published[:\s]*([\d/]+)', text)
            if pub_match:
                detail["web_published"] = pub_match.group(1).strip()

            # Main description
            desc_div = soup.select_one(".c_content, .description, .product-description-box")
            if desc_div:
                detail["full_description"] = desc_div.get_text(separator="\n", strip=True)

            # Parse sections
            for heading in soup.find_all(["h2", "h3", "strong"]):
                htxt = heading.get_text(strip=True).lower()
                items = []
                nxt = heading.find_next_sibling()
                if not nxt and heading.parent:
                    nxt = heading.parent.find_next_sibling()
                while nxt:
                    if nxt.name in ("h2", "h3", "strong") and nxt.get_text(strip=True):
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
                if "executive summary" in htxt or "description" in htxt:
                    if "full_description" not in detail:
                        detail["full_description"] = "\n".join(items)
                elif "benefit" in htxt or "advantage" in htxt:
                    detail["advantages"] = items
                elif "application" in htxt:
                    detail["applications"] = items
                elif "development" in htxt or "stage" in htxt:
                    detail["development_stage"] = " ".join(items)
                elif "patent" in htxt and "status" in htxt:
                    detail["patent_info"] = " ".join(items)

            # Inventors
            inventors = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "searchresults" in href and "type=i" in href:
                    name = a.get_text(strip=True)
                    if name and name not in inventors:
                        inventors.append(name)
            if inventors:
                detail["inventors"] = inventors

            # Categories
            categories = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if ("searchresults" in href or "idx=" in href or "lvl0" in href) and "type=i" not in href:
                    cat = a.get_text(strip=True)
                    if cat and cat not in categories and len(cat) > 1 and cat not in (inventors or []):
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
                        for p in patents:
                            if p.get("patent no.") or p.get("patent number"):
                                detail["patent_status"] = "Granted"
                                break
                            elif any("pending" in v.lower() for v in p.values() if isinstance(v, str)):
                                detail["patent_status"] = "Pending"

            # Patent numbers from links
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "patents.google" in href or "patft.uspto" in href:
                    pn = a.get_text(strip=True)
                    if pn:
                        detail.setdefault("patent_numbers", []).append(pn)
                        detail["patent_status"] = "Granted"

            if not detail.get("patent_status"):
                if "patent pending" in text.lower():
                    detail["patent_status"] = "Pending"

            return detail

        except Exception as e:
            logger.debug(f"Error scraping detail page {url}: {e}")
            return None
