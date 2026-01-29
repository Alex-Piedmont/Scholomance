"""University of Texas at Austin Office of Technology Commercialization scraper using RSS feed."""

import asyncio
import re
from typing import AsyncIterator, Optional
from xml.etree import ElementTree
import html

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology

DETAIL_CONCURRENCY = 5


class UTAustinScraper(BaseScraper):
    """Scraper for University of Texas at Austin's technology publisher portal."""

    BASE_URL = "https://utotc.technologypublisher.com"
    RSS_URL = f"{BASE_URL}/rss.aspx"
    SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

    def __init__(self, delay_seconds: float = 0.2):
        super().__init__(
            university_code="utaustin",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "UT Austin Office of Technology Commercialization"

    async def _init_session(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for UT Austin")

    async def _close_session(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def _get_technologies_from_rss(self) -> list[dict]:
        """Get all technologies from RSS feed."""
        await self._init_session()

        try:
            async with self._session.get(self.RSS_URL) as response:
                if response.status != 200:
                    self.log_error(f"RSS feed returned status {response.status}")
                    return []

                xml_content = await response.text()
                root = ElementTree.fromstring(xml_content)

                technologies = []
                for item in root.findall(".//item"):
                    tech = {
                        "title": self._get_text(item, "title"),
                        "link": self._get_text(item, "link"),
                        "guid": self._get_text(item, "guid"),
                        "description": self._get_text(item, "description"),
                        "case_id": self._get_text(item, "caseId"),
                        "pub_date": self._get_text(item, "pubDate"),
                    }
                    if tech["title"]:
                        technologies.append(tech)

                return technologies

        except Exception as e:
            self.log_error("Error fetching RSS feed", e)
            return []

    def _get_text(self, element, tag: str) -> str:
        child = element.find(tag)
        if child is not None and child.text:
            text = html.unescape(child.text)
            text = re.sub(r'<!\[CDATA\[|\]\]>', '', text)
            return text.strip()
        return ""

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
        """Scrape all technologies from UT Austin via RSS feed with detail enrichment."""
        try:
            await self._init_session()

            self.log_progress("Fetching technologies from RSS feed")
            items = await self._get_technologies_from_rss()
            total = len(items)
            self.log_progress(f"Found {total} technologies in RSS feed")

            all_technologies = []
            for i, item in enumerate(items):
                tech = self._parse_rss_item(item)
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

    def _parse_rss_item(self, item: dict) -> Optional[Technology]:
        try:
            title = item.get("title", "").strip()
            if not title:
                return None

            url = item.get("link") or item.get("guid", "")

            tech_id = ""
            if url:
                match = re.search(r'/technology/(\d+)', url)
                if match:
                    tech_id = match.group(1)

            case_id = item.get("case_id", "")
            if not tech_id:
                tech_id = case_id or re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50]

            description = item.get("description", "")
            if description:
                description = re.sub(r'<[^>]+>', '', description)
                description = re.sub(r'\s+', ' ', description).strip()
                if len(description) > 500:
                    description = description[:497] + "..."

            raw_data = {
                "url": url,
                "tech_id": tech_id,
                "case_id": case_id,
                "title": title,
                "description": description,
                "pub_date": item.get("pub_date", ""),
            }

            return Technology(
                university="utaustin",
                tech_id=tech_id,
                title=title,
                url=url,
                description=description if description else None,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing RSS item: {e}")
            return None

    async def scrape_page(self, page_num: int) -> list[Technology]:
        if page_num != 1:
            return []
        technologies = []
        async for tech in self.scrape():
            technologies.append(tech)
        return technologies

    async def scrape_technology_detail(self, url: str) -> Optional[dict]:
        """Scrape detailed information from a technology's detail page."""
        if not url:
            return None
        await self._init_session()

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    return None
                html_content = await resp.text()

            soup = BeautifulSoup(html_content, "html.parser")
            detail: dict = {}
            text = soup.get_text()

            # Description
            desc_div = soup.select_one(".c_content, .js-text, .description, .product-description-box")
            if desc_div:
                detail["full_description"] = desc_div.get_text(separator="\n", strip=True)

            # Parse sections by headings
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
                    elif nxt.name in ("p", "div") and nxt.get_text(strip=True):
                        items.append(nxt.get_text(strip=True))
                    nxt = nxt.find_next_sibling()
                if not items:
                    continue
                if "background" in htxt:
                    detail["background"] = "\n".join(items)
                elif "benefit" in htxt or "advantage" in htxt:
                    detail["advantages"] = items
                elif "application" in htxt:
                    detail["applications"] = items
                elif "opportunity" in htxt:
                    detail["opportunity"] = " ".join(items)
                elif "development" in htxt or "stage" in htxt:
                    detail["development_stage"] = " ".join(items)
                elif "intellectual" in htxt or "ip" in htxt:
                    detail["ip_info"] = " ".join(items)

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
                if ("searchresults" in href or "category" in href) and "type=i" not in href:
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

            # Patent info from table
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

            if not detail.get("patent_status"):
                if "patent pending" in text.lower():
                    detail["patent_status"] = "Pending"
                elif "provisional" in text.lower() and "patent" in text.lower():
                    detail["patent_status"] = "Provisional"

            # Publications / DOIs
            refs = []
            for a in soup.find_all("a", href=True):
                href = a.get("href", "")
                if "doi.org" in href or "pubmed" in href:
                    refs.append({"text": a.get_text(strip=True), "url": href})
            if refs:
                detail["publications"] = refs

            return detail

        except Exception as e:
            logger.debug(f"Error fetching technology detail: {e}")
            return None

    async def _init_browser(self) -> None:
        await self._init_session()

    async def _close_browser(self) -> None:
        await self._close_session()
