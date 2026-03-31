"""MIT Technology Licensing Office scraper."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology


class MITScraper(BaseScraper):
    """Scraper for MIT's Technology Licensing Office portal."""

    BASE_URL = "https://tlo.mit.edu"
    TECHNOLOGIES_URL = f"{BASE_URL}/industry-entrepreneurs/available-technologies"

    def __init__(self, delay_seconds: float = 1.0):
        super().__init__(
            university_code="mit",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "MIT Technology Licensing Office"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for MIT")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def _get_total_pages(self) -> int:
        """Estimate total number of pages."""
        # MIT has ~2834 technologies, 20 per page = ~142 pages (0-indexed)
        # We'll discover actual count while scraping
        return 143

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from MIT TLO."""
        try:
            await self._init_session()

            total_pages = await self._get_total_pages()
            self.log_progress(f"Starting scrape of approximately {total_pages} pages")

            for page_num in range(total_pages):
                try:
                    technologies = await self.scrape_page(page_num)

                    if not technologies:
                        self.log_progress(f"No technologies on page {page_num}, stopping")
                        break

                    for tech in technologies:
                        # Fetch detail page for each technology
                        if tech.url:
                            try:
                                detail = await self.scrape_technology_detail(tech.url)
                                if detail:
                                    tech.raw_data.update(detail)
                                    # Also update top-level description if background available
                                    if "background" in detail and not tech.description:
                                        tech.description = detail["background"]
                                    # Clear redundant description when background+solution exist
                                    if tech.raw_data.get("background") and tech.raw_data.get("solution"):
                                        tech.raw_data["description"] = None
                                await asyncio.sleep(1)  # Rate limiting between detail requests
                            except Exception as e:
                                logger.debug(f"Error fetching detail for {tech.url}: {e}")

                        self._tech_count += 1
                        yield tech

                    self._page_count += 1
                    if (page_num + 1) % 10 == 0:
                        self.log_progress(
                            f"Scraped page {page_num + 1}/{total_pages}, "
                            f"found {self._tech_count} technologies"
                        )

                    await self.delay()

                except Exception as e:
                    self.log_error(f"Error scraping page {page_num}", e)
                    continue

            self.log_progress(
                f"Completed scraping: {self._tech_count} technologies "
                f"from {self._page_count} pages"
            )

        finally:
            await self._close_session()

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """Scrape a single page of technologies."""
        await self._init_session()

        url = f"{self.TECHNOLOGIES_URL}?page={page_num}"
        logger.debug(f"Scraping page {page_num}: {url}")

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    self.log_error(f"HTTP {response.status} for page {page_num}")
                    return []

                html = await response.text()
                return self._parse_page(html)

        except Exception as e:
            self.log_error(f"Error fetching page {page_num}", e)
            return []

    def _parse_page(self, html: str) -> list[Technology]:
        """Parse technologies from HTML page."""
        soup = BeautifulSoup(html, "lxml")
        technologies = []

        # Find all technology teasers
        teasers = soup.find_all("div", class_="tech-brief-teaser")

        for teaser in teasers:
            tech = self._parse_teaser(teaser)
            if tech:
                technologies.append(tech)

        return technologies

    def _parse_teaser(self, teaser) -> Optional[Technology]:
        """Parse a single technology teaser element."""
        try:
            # Get title and URL from heading link
            heading = teaser.find("h3", class_="tech-brief-teaser__heading")
            if not heading:
                return None

            link = heading.find("a", class_="tech-brief-teaser__link")
            if not link:
                return None

            # Remove SVG elements and use space separator to fix title spacing
            for svg in link.find_all("svg"):
                svg.decompose()
            title = link.get_text(" ", strip=True)
            if not title:
                return None

            href = link.get("href", "")
            url = f"{self.BASE_URL}{href}" if href.startswith("/") else href

            # Extract tech_id from URL (the slug)
            tech_id = href.rstrip("/").split("/")[-1] if href else ""
            if not tech_id:
                tech_id = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50]

            # Get case number if present
            case_number = None
            details = teaser.find("span", class_="tech-brief-teaser__details-text")
            if details:
                case_match = re.search(r"#(\w+)", details.get_text())
                if case_match:
                    case_number = case_match.group(1)

            # Get description/details
            description = None
            if details:
                description = details.get_text(strip=True)
                # Remove case number from description
                if case_number:
                    description = re.sub(rf"\s*Case #{case_number}\s*", "", description).strip()

            # Get technology areas/categories
            categories = []
            tech_areas = teaser.find("div", class_="tech-brief-teaser__categories--tech-areas")
            if tech_areas:
                text = tech_areas.get_text(strip=True)
                text = re.sub(r"^Technology Areas:\s*", "", text)
                categories = [c.strip() for c in text.split("/") if c.strip()]

            # Get impact areas
            impact_areas = []
            impact_div = teaser.find("div", class_="tech-brief-teaser__categories--impact-areas")
            if impact_div:
                for impact in impact_div.find_all("a"):
                    impact_text = impact.get_text(strip=True)
                    if impact_text:
                        impact_areas.append(impact_text)

            # Get researchers
            researchers = []
            researchers_div = teaser.find("div", class_="tech-brief-teaser__reseachers")
            if researchers_div:
                researchers_text = researchers_div.get_text(strip=True)
                if researchers_text:
                    # Parse researcher names (separated by " / ")
                    researchers = [{"name": r.strip()} for r in researchers_text.split(" / ") if r.strip()]

            # Check if licensed
            is_licensed = teaser.find("span", class_="tech-brief-teaser__license-label--licensed") is not None

            raw_data = {
                "title": title,
                "url": url,
                "case_number": case_number,
                "description": description,
                "technology_areas": categories,
                "impact_areas": impact_areas,
                "researchers": researchers,
                "is_licensed": is_licensed,
            }

            return Technology(
                university="mit",
                tech_id=tech_id,
                title=title,
                url=url,
                description=description,
                keywords=categories if categories else None,
                innovators=[r["name"] for r in researchers] if researchers else None,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing teaser: {e}")
            return None

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

                detail = {}

                # Get background from intro section
                intro = soup.find("div", class_="tech-brief-details__intro")
                if intro:
                    detail["background"] = intro.get_text(strip=True)

                # Parse body sections by h2 headings
                body = soup.find("div", class_="tech-brief-body__inner")
                if body:
                    headings = body.find_all("h2")
                    for heading in headings:
                        heading_text = heading.get_text(strip=True).lower()

                        # Collect content between this heading and the next
                        content_parts = []
                        sibling = heading.find_next_sibling()
                        while sibling and sibling.name != "h2":
                            content_parts.append(sibling)
                            sibling = sibling.find_next_sibling()

                        if "technology" in heading_text and "problem" not in heading_text:
                            text = " ".join(p.get_text(strip=True) for p in content_parts if p.get_text(strip=True))
                            if text:
                                detail["solution"] = text
                        elif "problem" in heading_text:
                            text = " ".join(p.get_text(strip=True) for p in content_parts if p.get_text(strip=True))
                            if text:
                                detail["technical_problem"] = text
                        elif "advantage" in heading_text:
                            # Advantages are typically in ul > li items
                            advantages = []
                            for part in content_parts:
                                for li in part.find_all("li"):
                                    li_text = li.get_text(strip=True)
                                    if li_text:
                                        advantages.append(li_text)
                            # If no list items found, try plain text
                            if not advantages:
                                text = " ".join(p.get_text(strip=True) for p in content_parts if p.get_text(strip=True))
                                if text:
                                    advantages = [text]
                            if advantages:
                                detail["advantages"] = advantages

                # Get IP status from IP section
                ip_section = soup.find("div", class_="tech-brief-details__ip")
                if ip_section:
                    ip_items = ip_section.find_all("li", class_="tech-brief-ip__item")
                    if ip_items:
                        ip_texts = []
                        for li in ip_items:
                            strong = li.find("strong")
                            # Extract patent title from <strong> before decomposing
                            patent_title = strong.get_text(strip=True) if strong else ""
                            if strong:
                                strong.decompose()
                            # Remove patent link element
                            for a_tag in li.find_all("a"):
                                a_tag.decompose()
                            # Normalize whitespace and clean pipe separators
                            raw_text = " ".join(li.get_text().split())
                            country_status = raw_text.strip(" |")
                            # Format as "Country | Status"
                            country_status = re.sub(r"\s*\|\s*", " | ", country_status).strip(" |")
                            parts = []
                            if patent_title:
                                parts.append(patent_title)
                            if country_status:
                                parts.append(country_status)
                            if parts:
                                ip_texts.append("\n".join(parts))
                        if ip_texts:
                            detail["ip_status"] = "\n".join(ip_texts)

                # Extract patent information from page content
                patent_info = self._extract_patent_info(html)
                if patent_info:
                    # Don't overwrite structured ip_status from IP section
                    if "ip_status" in detail and "ip_status" in patent_info:
                        del patent_info["ip_status"]
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
        # Format: US10,059,990 or US 10059990 or Patent US10059990
        us_patent_matches = re.findall(
            r'(?:US|U\.?S\.?\s*Patent(?:\s*No\.?)?\s*)(\d{1,3}(?:,\d{3})+|\d{7,10})',
            html,
            re.IGNORECASE
        )
        for match in us_patent_matches:
            clean_num = match.replace(",", "")
            # Granted patents are 7-8 digits not starting with 202x
            if len(clean_num) >= 7 and not clean_num.startswith("202"):
                patent_numbers.append(f"US{match}")

        # Look for patent application numbers (pending: starts with 202x)
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

        # Check for patent pending keywords
        html_lower = html.lower()
        if "patent pending" in html_lower or "patent-pending" in html_lower:
            if "ip_status" not in patent_info:
                patent_info["ip_status"] = "Pending"

        # Check for patent filed
        if re.search(r'patent\s+(?:application\s+)?filed', html_lower):
            if "ip_status" not in patent_info:
                patent_info["ip_status"] = "Filed"

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
