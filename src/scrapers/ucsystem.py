"""University of California System technology transfer scraper using sitemap."""

import asyncio
import re
from typing import AsyncIterator, Optional
from xml.etree import ElementTree

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology


class UCSystemScraper(BaseScraper):
    """Scraper for University of California System's technology transfer portal.

    This scrapes technologies from all 10 UC campuses via the centralized
    UC tech transfer portal at techtransfer.universityofcalifornia.edu.
    """

    BASE_URL = "https://techtransfer.universityofcalifornia.edu"
    SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

    # Map campus codes to full names
    CAMPUS_NAMES = {
        "berkeley": "UC Berkeley",
        "davis": "UC Davis",
        "irvine": "UC Irvine",
        "los angeles": "UCLA",
        "merced": "UC Merced",
        "riverside": "UC Riverside",
        "san diego": "UC San Diego",
        "san francisco": "UCSF",
        "santa barbara": "UC Santa Barbara",
        "santa cruz": "UC Santa Cruz",
    }

    def __init__(self, delay_seconds: float = 0.3):
        super().__init__(
            university_code="ucsystem",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "University of California System"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for UC System")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def _get_technology_urls(self) -> list[str]:
        """Get all technology URLs from sitemap."""
        await self._init_session()

        try:
            async with self._session.get(self.SITEMAP_URL) as response:
                if response.status != 200:
                    self.log_error(f"Sitemap returned status {response.status}")
                    return []

                xml_content = await response.text()
                root = ElementTree.fromstring(xml_content)

                # Extract URLs from sitemap
                namespace = {"ns": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                urls = []
                for url_elem in root.findall(".//ns:url/ns:loc", namespace):
                    url = url_elem.text
                    # Only get NCD (technology disclosure) pages
                    if url and "/NCD/" in url:
                        urls.append(url)

                return urls

        except Exception as e:
            self.log_error("Error fetching sitemap", e)
            return []

    async def _fetch_technology_detail(self, url: str) -> Optional[dict]:
        """Fetch and parse a technology detail page."""
        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "lxml")

                detail = {"url": url}

                # Extract tech ID from URL (e.g., /NCD/21826.html -> 21826)
                match = re.search(r'/NCD/(\d+)\.html', url)
                if match:
                    detail["tech_id"] = match.group(1)

                # Get title
                title_elem = soup.find("h1")
                if title_elem:
                    detail["title"] = title_elem.get_text(strip=True)

                # Get campus/university — check contact section and page text
                page_text = soup.get_text()
                page_text_lower = page_text.lower()
                for campus_key, campus_name in self.CAMPUS_NAMES.items():
                    if f"university of california, {campus_key}" in page_text_lower:
                        detail["campus"] = campus_name
                        break
                else:
                    # Try matching short campus names directly (e.g. "UCLA", "UCSF")
                    for campus_name in self.CAMPUS_NAMES.values():
                        if campus_name in page_text:
                            detail["campus"] = campus_name
                            break

                # Get short_description from meta tag
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc:
                    detail["short_description"] = meta_desc.get("content", "").strip()

                # Parse h3-delimited sections
                for h3 in soup.find_all("h3"):
                    heading = h3.get_text(strip=True).lower()
                    content_parts = []
                    list_items = []
                    ip_urls = []
                    sibling = h3.find_next_sibling()
                    while sibling and sibling.name != "h3":
                        # Stop at footer-like elements
                        if sibling.name in ("footer", "nav") or (
                            sibling.get("class") and any(
                                c in " ".join(sibling.get("class", []))
                                for c in ("footer", "related", "sidebar")
                            )
                        ):
                            break
                        if sibling.name in ("ul", "ol"):
                            for li in sibling.find_all("li"):
                                list_items.append(li.get_text(separator=" ", strip=True))
                        elif sibling.name == "p":
                            # Extract any hyperlinks for patent/IP sections
                            for a_tag in sibling.find_all("a", href=True):
                                ip_urls.append(a_tag["href"])
                            text = sibling.get_text(strip=True)
                            if text:
                                content_parts.append(text)
                        elif sibling.name == "table":
                            # Parse table into structured format
                            rows = sibling.find_all("tr")
                            table_lines = []
                            for row in rows:
                                cells = row.find_all(["th", "td"])
                                cell_texts = [c.get_text(strip=True) for c in cells]
                                table_lines.append(" | ".join(cell_texts))
                                # Extract links from table cells too
                                for cell in cells:
                                    for a_tag in cell.find_all("a", href=True):
                                        ip_urls.append(a_tag["href"])
                            content_parts.append("\n".join(table_lines))
                        sibling = sibling.find_next_sibling()

                    text_content = "\n\n".join(content_parts)

                    if "abstract" in heading or "brief description" in heading or "overview" in heading or "summary" in heading or heading == "background":
                        detail.setdefault("background", text_content)
                    elif "full description" in heading or heading == "description":
                        detail["full_description"] = text_content
                    elif "application" in heading or "suggested use" in heading:
                        detail["applications"] = list_items if list_items else [t for t in text_content.split("\u2022") if t.strip()] if "\u2022" in text_content else text_content
                    elif "feature" in heading or "benefit" in heading or "advantage" in heading:
                        detail["advantages"] = list_items if list_items else [t.strip() for t in text_content.split("\u2022") if t.strip()] if "\u2022" in text_content else text_content
                    elif "patent" in heading:
                        detail["ip_status"] = text_content
                        if ip_urls:
                            detail["ip_url"] = ip_urls[0] if len(ip_urls) == 1 else ip_urls
                    elif heading == "inventors" or heading == "inventor":
                        # Only match the exact "Inventors" heading, not
                        # "Additional Technologies by these Inventors"
                        filtered = [
                            item for item in list_items
                            if "additional technologies" not in item.lower()
                            and "see more" not in item.lower()
                        ]
                        detail["inventors"] = filtered if filtered else [text_content] if text_content else []

                # Get categories — look for h4 "Categorized As" or div with class
                categories = []
                cat_section = soup.find("div", class_="field-name-field-categories")
                if cat_section:
                    for cat in cat_section.find_all("a"):
                        categories.append(cat.get_text(strip=True))
                else:
                    for h4 in soup.find_all("h4"):
                        if "categorized" in h4.get_text(strip=True).lower():
                            sib = h4.find_next_sibling()
                            while sib and sib.name not in ("h3", "h4"):
                                for a_tag in sib.find_all("a"):
                                    text = a_tag.get_text(strip=True)
                                    if text:
                                        categories.append(text)
                                sib = sib.find_next_sibling()
                            break
                detail["categories"] = categories

                # Get UC Case number if available
                case_match = re.search(r'UC Case[:\s]+([^\s<]+)', html)
                if case_match:
                    detail["case_number"] = case_match.group(1)

                return detail

        except Exception as e:
            logger.debug(f"Error fetching {url}: {e}")
            return None

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from UC System via sitemap."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology URLs from sitemap")
            urls = await self._get_technology_urls()
            total = len(urls)
            self.log_progress(f"Found {total} technology URLs")

            # Process in batches to avoid overwhelming the server
            batch_size = 10
            for i in range(0, total, batch_size):
                batch_urls = urls[i:i + batch_size]

                # Fetch batch concurrently
                tasks = [self._fetch_technology_detail(url) for url in batch_urls]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for url, result in zip(batch_urls, results):
                    if isinstance(result, Exception):
                        logger.debug(f"Error processing {url}: {result}")
                        continue

                    if result:
                        tech = self._parse_detail(result)
                        if tech:
                            self._tech_count += 1
                            yield tech

                # Log progress
                processed = min(i + batch_size, total)
                if processed % 100 == 0 or processed == total:
                    self.log_progress(f"Processed {processed}/{total} technologies")

                await self.delay()

            self._page_count = 1
            self.log_progress(
                f"Completed scraping: {self._tech_count} technologies"
            )

        finally:
            await self._close_session()

    def _parse_detail(self, detail: dict) -> Optional[Technology]:
        """Parse technology info from detail dict."""
        try:
            title = detail.get("title", "").strip()
            if not title:
                return None

            tech_id = detail.get("tech_id", "")
            if not tech_id:
                tech_id = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50]

            url = detail.get("url", "")

            # Use background or full_description as the description (no truncation)
            description = detail.get("background", "") or detail.get("full_description", "") or detail.get("short_description", "")
            if description:
                description = re.sub(r'[ \t]+', ' ', description).strip()

            # De-duplicate: skip fields that repeat description content
            short_desc = detail.get("short_description") or None
            full_desc = detail.get("full_description") or None
            desc_norm = re.sub(r'\s+', ' ', description).strip() if description else ""
            if short_desc and desc_norm:
                sd_norm = re.sub(r'\s+', ' ', short_desc).strip()
                # Drop if either is a substring, or if first 100 chars match (meta tags
                # are near-duplicates with minor whitespace/punctuation differences)
                if sd_norm in desc_norm or desc_norm in sd_norm or sd_norm[:100] == desc_norm[:100]:
                    short_desc = None
            if full_desc and desc_norm:
                fd_norm = re.sub(r'\s+', ' ', full_desc).strip()
                if fd_norm in desc_norm or desc_norm in fd_norm:
                    full_desc = None

            # Get campus info
            campus = detail.get("campus", "")
            categories = detail.get("categories", [])

            raw_data = {
                "url": url,
                "tech_id": tech_id,
                "title": title,
                "description": description,
                "campus": campus,
                "categories": categories,
                "case_number": detail.get("case_number"),
                "short_description": short_desc,
                "background": detail.get("background"),
                "full_description": full_desc,
                "applications": detail.get("applications"),
                "advantages": detail.get("advantages"),
                "ip_status": detail.get("ip_status"),
                "inventors": detail.get("inventors"),
                "ip_url": detail.get("ip_url"),
            }

            keywords = categories.copy() if categories else []

            # Extract inventors for the Technology dataclass field
            innovators = detail.get("inventors")

            return Technology(
                university="ucsystem",
                tech_id=tech_id,
                title=title,
                url=url,
                description=description if description else None,
                innovators=innovators if innovators else None,
                keywords=keywords if keywords else None,
                raw_data=raw_data,
                patent_status=detail.get("ip_status"),
            )

        except Exception as e:
            logger.debug(f"Error parsing detail: {e}")
            return None

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """
        Scrape technologies - UC System uses sitemap approach.
        This method exists for interface compatibility.
        """
        if page_num != 1:
            return []

        technologies = []
        async for tech in self.scrape():
            technologies.append(tech)
        return technologies

    async def scrape_technology_detail(self, url: str) -> Optional[dict]:
        """
        Scrape detailed information from a technology's detail page.

        Args:
            url: The URL of the technology detail page

        Returns:
            Dictionary with detailed technology information
        """
        await self._init_session()
        try:
            return await self._fetch_technology_detail(url)
        finally:
            pass  # Keep session open for potential reuse

    # Backwards compatibility methods
    async def _init_browser(self) -> None:
        """Backwards compatibility - initializes HTTP session instead."""
        await self._init_session()

    async def _close_browser(self) -> None:
        """Backwards compatibility - closes HTTP session instead."""
        await self._close_session()
