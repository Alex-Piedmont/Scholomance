"""Columbia Technology Ventures scraper using sitemap."""

import asyncio
import re
from typing import AsyncIterator, Optional
from xml.etree import ElementTree

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology


class ColumbiaScraper(BaseScraper):
    """Scraper for Columbia University's technology ventures portal."""

    BASE_URL = "https://inventions.techventures.columbia.edu"
    SITEMAP_URL = f"{BASE_URL}/sitemap.xml"

    def __init__(self, delay_seconds: float = 0.2):
        super().__init__(
            university_code="columbia",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "Columbia Technology Ventures"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for Columbia")

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
                    if url and "/technologies/" in url:
                        urls.append(url)

                return urls

        except Exception as e:
            self.log_error("Error fetching sitemap", e)
            return []

    async def _fetch_detail(self, tech: Technology, semaphore: asyncio.Semaphore) -> Technology:
        """Fetch detail page for a technology and merge data."""
        async with semaphore:
            try:
                detail = await self.scrape_technology_detail(tech.url)
                if detail:
                    tech.raw_data.update(detail)
                    if detail.get("description"):
                        tech.description = detail["description"]
                    elif detail.get("meta_description"):
                        tech.description = detail["meta_description"]
                await asyncio.sleep(self.delay_seconds)
            except Exception as e:
                logger.debug(f"Error fetching detail for {tech.url}: {e}")
        return tech

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from Columbia via sitemap."""
        try:
            await self._init_session()

            self.log_progress("Fetching technology URLs from sitemap")
            urls = await self._get_technology_urls()
            total = len(urls)
            self.log_progress(f"Found {total} technology URLs")

            all_technologies = []
            for i, url in enumerate(urls):
                tech = self._parse_url(url)
                if tech:
                    all_technologies.append(tech)

                # Log progress every 200 items
                if (i + 1) % 200 == 0:
                    self.log_progress(f"Parsed {i + 1}/{total} URLs")

            self.log_progress(f"Fetching detail pages for {len(all_technologies)} technologies")
            semaphore = asyncio.Semaphore(5)
            tasks = [self._fetch_detail(tech, semaphore) for tech in all_technologies]
            enriched = await asyncio.gather(*tasks)

            for tech in enriched:
                self._tech_count += 1
                yield tech

            self._page_count = 1
            self.log_progress(
                f"Completed scraping: {self._tech_count} technologies"
            )

        finally:
            await self._close_session()

    def _parse_url(self, url: str) -> Optional[Technology]:
        """Parse technology info from URL."""
        try:
            # URL format: /technologies/title-slug--CU12345
            path = url.split("/technologies/")[-1]

            # Extract tech ID (CU number at end)
            tech_id_match = re.search(r'--?(CU\d+|\d+)$', path)
            if tech_id_match:
                tech_id = tech_id_match.group(1)
                # Title is everything before the ID
                title_slug = path[:tech_id_match.start()]
            else:
                tech_id = path
                title_slug = path

            # Convert slug to title
            title = title_slug.replace("-", " ").strip()
            # Capitalize first letter of each word
            title = " ".join(word.capitalize() for word in title.split())

            if not title:
                return None

            raw_data = {
                "url": url,
                "tech_id": tech_id,
                "title_slug": title_slug,
            }

            return Technology(
                university="columbia",
                tech_id=tech_id,
                title=title,
                url=url,
                description=None,  # Would need to fetch detail page
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing URL {url}: {e}")
            return None

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """
        Scrape technologies - Columbia uses sitemap approach.
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
            Dictionary with detailed technology information including patent info
        """
        await self._init_session()

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "lxml")

                detail = {"url": url}

                # Try to extract description from meta tag
                meta_desc = soup.find("meta", attrs={"name": "description"})
                if meta_desc:
                    detail["meta_description"] = meta_desc.get("content", "")

                # Parse structured sections from detail body
                # Find the container that directly holds h2 elements
                first_h2 = soup.find("h2")
                body_div = first_h2.parent if first_h2 else None

                if body_div:
                    # Collect sections: list of (heading_text|None, [parts])
                    raw_sections: list[tuple[Optional[str], list[str]]] = []
                    current_heading: Optional[str] = None
                    current_parts: list[str] = []

                    for child in body_div.children:
                        if not hasattr(child, "name") or not child.name:
                            continue
                        if child.name == "h2":
                            if current_parts:
                                raw_sections.append((current_heading, current_parts))
                            current_heading = child.get_text(strip=True)
                            current_parts = []
                        elif child.name == "ul":
                            for li in child.find_all("li"):
                                t = li.get_text(strip=True)
                                if t:
                                    current_parts.append(t)
                        elif child.name in ("p", "div"):
                            t = child.get_text(strip=True)
                            if t:
                                current_parts.append(t)

                    if current_parts:
                        raw_sections.append((current_heading, current_parts))

                    # Map sections to standard raw_data field names
                    for heading, parts in raw_sections:
                        if heading is None:
                            # Intro paragraph before any heading
                            detail["description"] = "\n\n".join(parts)
                            continue
                        h_lower = heading.lower().rstrip(":")
                        text = "\n\n".join(parts)
                        items = parts  # list form

                        if "application" in h_lower:
                            detail["applications"] = items
                        elif "advantage" in h_lower:
                            detail["advantages"] = items
                        elif "benefit" in h_lower:
                            detail["benefit"] = text
                        elif "unmet need" in h_lower or "background" in h_lower:
                            detail["background"] = text
                        elif "technology" in h_lower and ("overview" in h_lower or ":" in heading):
                            detail["abstract"] = text
                        elif "market" in h_lower:
                            detail["market_application"] = text
                        elif "inventor" in h_lower:
                            detail["inventors"] = items
                        elif "patent" in h_lower:
                            detail["ip_status"] = text
                        elif "publication" in h_lower:
                            detail["publications"] = text
                        elif "reference" in h_lower:
                            detail["reference_number"] = text
                        elif "development" in h_lower or "stage" in h_lower:
                            detail["development_stage"] = text
                        else:
                            # Unknown section — store as 'other'
                            existing = detail.get("other", "")
                            section_text = f"**{heading}**\n\n{text}"
                            detail["other"] = f"{existing}\n\n{section_text}".strip() if existing else section_text

                # Extract patent information
                patent_info = self._extract_patent_info(html)
                if patent_info:
                    detail.update(patent_info)

                return detail

        except Exception as e:
            logger.debug(f"Error fetching technology detail: {e}")
            return None

    def _extract_patent_info(self, html: str) -> dict:
        """Extract patent information from HTML content."""
        patent_info = {}
        patent_numbers = []

        # Look for US patent numbers (granted patents: 7-10 digits)
        us_patent_matches = re.findall(
            r'(?:US|U\.?S\.?\s*Patent(?:\s*No\.?)?\s*)(\d{1,3}(?:,\d{3})+|\d{7,10})',
            html,
            re.IGNORECASE
        )
        for match in us_patent_matches:
            clean_num = match.replace(",", "")
            if len(clean_num) >= 7 and not clean_num.startswith("202"):
                patent_numbers.append(f"US{match}")

        # Look for patent application numbers
        app_matches = re.findall(
            r'(?:US|Application)\s*(202\d{7,})',
            html,
            re.IGNORECASE
        )
        if app_matches:
            patent_info["patent_applications"] = list(set(app_matches))

        if patent_numbers:
            patent_info["patent_numbers"] = list(set(patent_numbers))
            patent_info["ip_status"] = "Granted"

        html_lower = html.lower()

        # Check for "Patent Status" section with specific status
        status_match = re.search(
            r'patent\s*status[:\s]*([a-zA-Z\s]+)',
            html_lower
        )
        if status_match:
            status_text = status_match.group(1).strip()
            if "pending" in status_text:
                if "ip_status" not in patent_info:
                    patent_info["ip_status"] = "Pending"
            elif "granted" in status_text or "issued" in status_text:
                patent_info["ip_status"] = "Granted"
            elif "filed" in status_text:
                if "ip_status" not in patent_info:
                    patent_info["ip_status"] = "Filed"

        # Check for patent pending keywords
        if "patent pending" in html_lower or "patent-pending" in html_lower:
            if "ip_status" not in patent_info:
                patent_info["ip_status"] = "Pending"

        # Check for provisional
        if "provisional" in html_lower and "patent" in html_lower:
            if "ip_status" not in patent_info:
                patent_info["ip_status"] = "Provisional"

        return patent_info

    # Backwards compatibility methods
    async def _init_browser(self) -> None:
        """Backwards compatibility - initializes HTTP session instead."""
        await self._init_session()

    async def _close_browser(self) -> None:
        """Backwards compatibility - closes HTTP session instead."""
        await self._close_session()
