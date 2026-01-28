"""Stanford TechFinder scraper using Playwright."""

import asyncio
import re
from typing import AsyncIterator, Optional
from urllib.parse import urljoin, urlparse, parse_qs

import aiohttp
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser
from loguru import logger

from .base import BaseScraper, Technology

DETAIL_CONCURRENCY = 5


class StanfordScraper(BaseScraper):
    """Scraper for Stanford's TechFinder (techfinder.stanford.edu)."""

    BASE_URL = "https://techfinder.stanford.edu"
    TECHNOLOGIES_URL = f"{BASE_URL}/technology"  # Note: /technology not /technologies

    def __init__(self, delay_seconds: float = 1.0):
        super().__init__(
            university_code="stanford",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return "Stanford TechFinder"

    async def _init_browser(self) -> None:
        """Initialize Playwright browser and aiohttp session."""
        if self._browser is None:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(headless=True)
            self._page = await self._browser.new_page()
            await self._page.set_viewport_size({"width": 1920, "height": 1080})
            logger.debug("Browser initialized")
        if self._session is None:
            self._session = aiohttp.ClientSession()

    async def _close_browser(self) -> None:
        """Close Playwright browser and aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
        if self._page:
            await self._page.close()
            self._page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.debug("Browser closed")

    async def _get_total_pages(self) -> int:
        """Get the total number of pages from the pagination."""
        if not self._page:
            await self._init_browser()

        await self._page.goto(self.TECHNOLOGIES_URL, wait_until="networkidle")

        try:
            # Wait for content to load
            await self._page.wait_for_selector("a[href*='/technology/']", timeout=10000)

            # Look for pagination - Stanford uses pager links
            pager_items = await self._page.query_selector_all(".pager__item a, .pager a, nav.pager a")

            if pager_items:
                page_numbers = []
                for link in pager_items:
                    href = await link.get_attribute("href")
                    if href:
                        # Look for page parameter in URL
                        match = re.search(r"page=(\d+)", href)
                        if match:
                            page_numbers.append(int(match.group(1)) + 1)  # 0-indexed to 1-indexed

                if page_numbers:
                    return max(page_numbers)

            # Look for last page link
            last_link = await self._page.query_selector(".pager__item--last a, .pager-last a")
            if last_link:
                href = await last_link.get_attribute("href")
                if href:
                    match = re.search(r"page=(\d+)", href)
                    if match:
                        return int(match.group(1)) + 1

            # Default fallback - estimate based on total count if shown
            return 100  # Conservative estimate

        except Exception as e:
            logger.warning(f"Could not determine total pages: {e}")
            return 100

    async def _fetch_detail(self, tech: Technology, semaphore: asyncio.Semaphore) -> Technology:
        """Fetch detail page for a technology using aiohttp and merge data."""
        async with semaphore:
            try:
                detail = await self.scrape_technology_detail(tech.url)
                if detail:
                    tech.raw_data.update(detail)
                    if detail.get("full_description") and not tech.description:
                        tech.description = detail["full_description"]
                    if detail.get("inventors"):
                        tech.raw_data["inventors"] = detail["inventors"]
                    if detail.get("applications"):
                        tech.raw_data["applications"] = detail["applications"]
                    if detail.get("advantages"):
                        tech.raw_data["advantages"] = detail["advantages"]
                await asyncio.sleep(self.delay_seconds)
            except Exception as e:
                logger.debug(f"Error fetching detail for {tech.url}: {e}")
        return tech

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from Stanford TechFinder."""
        try:
            await self._init_browser()

            total_pages = await self._get_total_pages()
            self.log_progress(f"Starting scrape of approximately {total_pages} pages")

            all_technologies: list[Technology] = []

            for page_num in range(1, total_pages + 1):
                try:
                    technologies = await self.scrape_page(page_num)

                    if not technologies:
                        self.log_progress(f"No technologies on page {page_num}, stopping")
                        break

                    all_technologies.extend(technologies)

                    self._page_count += 1
                    if page_num % 10 == 0:
                        self.log_progress(f"Scraped page {page_num}/{total_pages}, found {len(all_technologies)} technologies")

                    await self.delay()

                except Exception as e:
                    self.log_error(f"Error scraping page {page_num}", e)
                    continue

            self.log_progress(f"Fetching detail pages for {len(all_technologies)} technologies")

            semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)
            tasks = [self._fetch_detail(tech, semaphore) for tech in all_technologies]
            enriched = await asyncio.gather(*tasks)

            for tech in enriched:
                self._tech_count += 1
                yield tech

            self.log_progress(f"Completed scraping: {self._tech_count} technologies from {self._page_count} pages")

        finally:
            await self._close_browser()

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """Scrape a single page of technologies."""
        if not self._page:
            await self._init_browser()

        # Stanford uses 0-indexed pages
        url = f"{self.TECHNOLOGIES_URL}?page={page_num - 1}" if page_num > 1 else self.TECHNOLOGIES_URL
        logger.debug(f"Scraping page {page_num}: {url}")

        try:
            await self._page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for technology links to appear
            await self._page.wait_for_selector("a[href*='/technology/']", timeout=15000)

            # Give page time to fully render
            await asyncio.sleep(1)

            technologies = []

            # Find all technology links - they follow pattern /technology/slug-name
            links = await self._page.query_selector_all("a[href*='/technology/']")

            seen_urls = set()
            for link in links:
                try:
                    href = await link.get_attribute("href")
                    if not href:
                        continue

                    # Skip if it's a facet/filter link
                    if "facet" in href or "innovator" in href:
                        continue

                    full_url = urljoin(self.BASE_URL, href)

                    # Skip duplicates
                    if full_url in seen_urls:
                        continue
                    seen_urls.add(full_url)

                    # Get title from link text
                    title = await link.inner_text()
                    title = title.strip()

                    if not title or len(title) < 5:
                        continue

                    # Extract tech_id from URL
                    path = urlparse(full_url).path
                    tech_id = path.rstrip("/").split("/")[-1]

                    if not tech_id or tech_id == "technology":
                        continue

                    # Try to get parent element for more context
                    parent = await link.evaluate_handle("el => el.closest('article, .card, .views-row, div')")
                    description = ""
                    keywords = []

                    if parent:
                        # Try to get description from sibling/child elements
                        desc_elem = await parent.query_selector("p, .description, .summary, .field--name-body")
                        if desc_elem:
                            description = await desc_elem.inner_text()
                            description = description.strip()

                        # Try to get tags/keywords
                        tag_elems = await parent.query_selector_all(".tag, .keyword, [class*='category']")
                        for tag_elem in tag_elems:
                            tag_text = await tag_elem.inner_text()
                            if tag_text.strip():
                                keywords.append(tag_text.strip())

                    raw_data = {
                        "title": title,
                        "description": description,
                        "url": full_url,
                        "keywords": keywords,
                        "source_page": url,
                    }

                    tech = Technology(
                        university="stanford",
                        tech_id=tech_id,
                        title=title,
                        url=full_url,
                        description=description if description else None,
                        keywords=keywords if keywords else None,
                        raw_data=raw_data,
                    )
                    technologies.append(tech)

                except Exception as e:
                    logger.debug(f"Error parsing link: {e}")
                    continue

            return technologies

        except Exception as e:
            self.log_error(f"Error loading page {page_num}", e)
            return []

    async def scrape_technology_detail(self, url: str) -> Optional[dict]:
        """Scrape detailed information from a technology's detail page using aiohttp."""
        if self._session is None:
            self._session = aiohttp.ClientSession()

        try:
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status != 200:
                    logger.debug(f"Detail page returned {resp.status}: {url}")
                    return None
                html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")
            detail: dict = {}

            # Docket number from eyebrow
            eyebrow = soup.select_one("div.docket__eyebrow")
            if eyebrow:
                text = eyebrow.get_text(strip=True)
                match = re.search(r"S\d{2}-\d{3}", text)
                if match:
                    detail["docket_number"] = match.group(0)

            # Description from docket__text
            desc_div = soup.select_one("div.docket__text")
            if desc_div:
                detail["full_description"] = desc_div.get_text(separator="\n", strip=True)
                detail["description_html"] = str(desc_div)

                # Related portfolio: links to other /technology/ pages within description
                related = []
                for a in desc_div.select("a[href*='/technology/']"):
                    href = a.get("href", "")
                    full = urljoin(self.BASE_URL, href)
                    if full != url:
                        related.append({"title": a.get_text(strip=True), "url": full})
                if related:
                    detail["related_portfolio"] = related

            # Parse docket__section divs by h2 heading
            for section in soup.select("div.docket__section"):
                h2 = section.select_one("h2")
                if not h2:
                    continue
                heading = h2.get_text(strip=True).lower()

                items = [li.get_text(strip=True) for li in section.select("li") if li.get_text(strip=True)]

                if "application" in heading:
                    detail["applications"] = items
                elif "advantage" in heading:
                    detail["advantages"] = items
                elif "publication" in heading:
                    # Preserve links for publications
                    pub_items = []
                    for li in section.select("li"):
                        a = li.select_one("a")
                        if a and a.get("href"):
                            pub_items.append({"text": li.get_text(strip=True), "url": a["href"]})
                        elif li.get_text(strip=True):
                            pub_items.append({"text": li.get_text(strip=True)})
                    detail["publications"] = pub_items
                elif "innovator" in heading:
                    detail["inventors"] = items
                elif "licensing contact" in heading:
                    contact: dict = {}
                    name_el = section.select_one(".people__name")
                    if name_el:
                        contact["name"] = name_el.get_text(strip=True)
                    title_el = section.select_one(".people__title")
                    if title_el:
                        contact["title"] = title_el.get_text(strip=True)
                    mailto = section.select_one("a[href^='mailto:']")
                    if mailto:
                        contact["email"] = mailto["href"].replace("mailto:", "")
                    if contact:
                        detail["licensing_contact"] = contact

            # PDF link
            pdf_link = soup.select_one("a[href*='/print/pdf/']")
            if pdf_link:
                detail["pdf_url"] = urljoin(self.BASE_URL, pdf_link["href"])

            return detail

        except Exception as e:
            logger.debug(f"Error scraping detail page {url}: {e}")
            return None
