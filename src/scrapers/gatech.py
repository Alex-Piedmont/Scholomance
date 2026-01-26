"""Georgia Tech technology licensing scraper using Playwright."""

import asyncio
import re
from typing import AsyncIterator, Optional
from urllib.parse import urljoin, urlparse, parse_qs

from playwright.async_api import async_playwright, Page, Browser
from loguru import logger

from .base import BaseScraper, Technology


class GatechScraper(BaseScraper):
    """Scraper for Georgia Tech's technology licensing site."""

    BASE_URL = "https://licensing.research.gatech.edu"
    TECHNOLOGIES_URL = f"{BASE_URL}/technology-licensing"

    def __init__(self, delay_seconds: float = 1.0):
        super().__init__(
            university_code="gatech",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    @property
    def name(self) -> str:
        return "Georgia Tech Technology Licensing"

    async def _init_browser(self) -> None:
        """Initialize Playwright browser."""
        if self._browser is None:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(headless=True)
            self._page = await self._browser.new_page()
            await self._page.set_viewport_size({"width": 1920, "height": 1080})
            logger.debug("Browser initialized for Georgia Tech")

    async def _close_browser(self) -> None:
        """Close Playwright browser."""
        if self._page:
            await self._page.close()
            self._page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.debug("Browser closed")

    async def _get_total_pages(self) -> int:
        """Get the total number of pages from pagination."""
        if not self._page:
            await self._init_browser()

        await self._page.goto(self.TECHNOLOGIES_URL, wait_until="networkidle")

        try:
            # Look for pagination links
            pagination = await self._page.query_selector_all(
                ".pager a, .pagination a, nav.pager a, [class*='pager'] a"
            )

            if pagination:
                page_numbers = []
                for link in pagination:
                    text = await link.inner_text()
                    text = text.strip()
                    if text.isdigit():
                        page_numbers.append(int(text))
                    # Also check href for page numbers
                    href = await link.get_attribute("href")
                    if href:
                        match = re.search(r"page=(\d+)", href)
                        if match:
                            page_numbers.append(int(match.group(1)) + 1)  # 0-indexed to 1-indexed

                if page_numbers:
                    return max(page_numbers)

            # Look for "last" link
            last_link = await self._page.query_selector(
                ".pager-last a, .pagination .last a, [class*='last'] a"
            )
            if last_link:
                href = await last_link.get_attribute("href")
                if href:
                    match = re.search(r"page=(\d+)", href)
                    if match:
                        return int(match.group(1)) + 1

            # Default fallback
            return 20

        except Exception as e:
            logger.warning(f"Could not determine total pages: {e}")
            return 20

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from Georgia Tech."""
        try:
            await self._init_browser()

            total_pages = await self._get_total_pages()
            self.log_progress(f"Starting scrape of approximately {total_pages} pages")

            for page_num in range(1, total_pages + 1):
                try:
                    technologies = await self.scrape_page(page_num)
                    for tech in technologies:
                        self._tech_count += 1
                        yield tech

                    self._page_count += 1
                    if page_num % 5 == 0:
                        self.log_progress(
                            f"Scraped page {page_num}/{total_pages}, "
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
            await self._close_browser()

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """Scrape a single page of technologies."""
        if not self._page:
            await self._init_browser()

        # Georgia Tech uses 0-indexed pages in URL
        url = f"{self.TECHNOLOGIES_URL}?page={page_num - 1}" if page_num > 1 else self.TECHNOLOGIES_URL
        logger.debug(f"Scraping page {page_num}: {url}")

        try:
            await self._page.goto(url, wait_until="networkidle", timeout=30000)

            # Wait for content to load
            await self._page.wait_for_selector(
                ".view-content, .views-row, article, .node, .technology-item",
                timeout=15000,
            )

            await asyncio.sleep(0.5)

            technologies = []

            # Try different selectors for technology items
            items = await self._page.query_selector_all(
                ".views-row, .node--type-technology, article.node, "
                ".technology-item, .view-content > div"
            )

            if not items:
                # Fallback to more generic selectors
                items = await self._page.query_selector_all(
                    ".view-content article, .view-content .node"
                )

            for item in items:
                try:
                    tech = await self._parse_item(item)
                    if tech:
                        technologies.append(tech)
                except Exception as e:
                    logger.debug(f"Error parsing item: {e}")
                    continue

            return technologies

        except Exception as e:
            self.log_error(f"Error loading page {page_num}", e)
            return []

    async def _parse_item(self, item) -> Optional[Technology]:
        """Parse a technology item element into a Technology object."""
        try:
            # Get title and link
            title_elem = await item.query_selector(
                "h2 a, h3 a, .field--name-title a, .node-title a, a[href*='/technologies/']"
            )

            if not title_elem:
                title_elem = await item.query_selector("h2, h3, .field--name-title, .node-title")

            if not title_elem:
                return None

            title = await title_elem.inner_text()
            title = title.strip()

            if not title:
                return None

            # Get URL
            link = await item.query_selector("a[href*='/technologies/'], h2 a, h3 a")
            url = ""
            if link:
                href = await link.get_attribute("href")
                url = urljoin(self.BASE_URL, href) if href else ""

            # Extract tech_id from URL or generate one
            tech_id = ""
            if url:
                # URL might be like /technologies/machine-learning-system or /node/123
                path = urlparse(url).path
                tech_id = path.rstrip("/").split("/")[-1]

            if not tech_id:
                tech_id = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50]

            # Get description/summary
            desc_elem = await item.query_selector(
                ".field--name-body, .field--name-field-summary, "
                ".summary, .description, .teaser, p"
            )
            description = ""
            if desc_elem:
                description = await desc_elem.inner_text()
                description = description.strip()

            # Get categories/tags
            keywords = []
            tag_elems = await item.query_selector_all(
                ".field--name-field-category a, .field--name-field-tags a, "
                ".taxonomy-term, .tag, [class*='category']"
            )
            for tag_elem in tag_elems:
                tag_text = await tag_elem.inner_text()
                tag_text = tag_text.strip()
                if tag_text:
                    keywords.append(tag_text)

            # Get inventors if available
            innovators = []
            inventor_elem = await item.query_selector(
                ".field--name-field-inventors, .field--name-field-researchers, "
                "[class*='inventor'], [class*='researcher']"
            )
            if inventor_elem:
                inventor_text = await inventor_elem.inner_text()
                innovators = [i.strip() for i in re.split(r"[,;]", inventor_text) if i.strip()]

            raw_data = {
                "title": title,
                "description": description,
                "url": url,
                "keywords": keywords,
                "innovators": innovators,
                "source_page": self._page.url if self._page else "",
            }

            return Technology(
                university="gatech",
                tech_id=tech_id,
                title=title,
                url=url,
                description=description,
                keywords=keywords if keywords else None,
                innovators=innovators if innovators else None,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing item element: {e}")
            return None

    async def scrape_technology_detail(self, url: str) -> Optional[dict]:
        """Scrape detailed information from a technology's detail page."""
        if not self._page:
            await self._init_browser()

        try:
            await self._page.goto(url, wait_until="networkidle", timeout=30000)

            detail = {}

            # Get full description
            desc_elem = await self._page.query_selector(
                ".field--name-body, .node__content, article .content"
            )
            if desc_elem:
                detail["full_description"] = await desc_elem.inner_text()

            # Get inventors
            inventors_elem = await self._page.query_selector(
                ".field--name-field-inventors, [class*='inventor']"
            )
            if inventors_elem:
                text = await inventors_elem.inner_text()
                detail["inventors"] = [i.strip() for i in re.split(r"[,;]", text) if i.strip()]

            # Get patent info
            patent_elem = await self._page.query_selector(
                ".field--name-field-patent, [class*='patent']"
            )
            if patent_elem:
                detail["patent_info"] = await patent_elem.inner_text()

            # Get categories
            cat_elems = await self._page.query_selector_all(
                ".field--name-field-category a, .taxonomy-term"
            )
            if cat_elems:
                detail["categories"] = []
                for elem in cat_elems:
                    detail["categories"].append(await elem.inner_text())

            return detail

        except Exception as e:
            logger.debug(f"Error scraping detail page {url}: {e}")
            return None
