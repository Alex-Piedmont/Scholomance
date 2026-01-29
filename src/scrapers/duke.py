"""Duke University Office for Translation & Commercialization scraper using Playwright."""

import asyncio
import re
from typing import AsyncIterator, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from loguru import logger

from .base import BaseScraper, Technology

DETAIL_CONCURRENCY = 3


class DukeScraper(BaseScraper):
    """
    Scraper for Duke's Office for Translation & Commercialization (OTC).

    Uses Playwright with anti-bot-detection measures since Duke's site
    blocks standard automated requests.
    """

    BASE_URL = "https://otc.duke.edu"
    TECHNOLOGIES_URL = f"{BASE_URL}/technologies/"

    def __init__(self, delay_seconds: float = 1.0):
        super().__init__(
            university_code="duke",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    @property
    def name(self) -> str:
        return "Duke Office for Translation & Commercialization"

    async def _init_browser(self) -> None:
        """Initialize Playwright browser with anti-detection settings."""
        if self._browser is None:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                ]
            )
            self._context = await self._browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                locale='en-US',
                timezone_id='America/New_York',
            )
            self._page = await self._context.new_page()

            # Remove webdriver property to avoid detection
            await self._page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            logger.debug("Browser initialized with anti-detection settings")

    async def _close_browser(self) -> None:
        """Close Playwright browser."""
        if self._page:
            await self._page.close()
            self._page = None
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.debug("Browser closed")

    async def _get_total_pages(self) -> int:
        """Get the total number of pages from the pagination."""
        if not self._page:
            await self._init_browser()

        await self._page.goto(self.TECHNOLOGIES_URL, wait_until="networkidle", timeout=60000)
        await asyncio.sleep(2)

        try:
            # Find pagination links
            page_links = await self._page.query_selector_all("a[href*='pg=']")
            max_page = 1

            for link in page_links:
                href = await link.get_attribute("href") or ""
                match = re.search(r'pg=(\d+)', href)
                if match:
                    max_page = max(max_page, int(match.group(1)))

            return max_page

        except Exception as e:
            logger.warning(f"Could not determine total pages: {e}")
            return 50  # Conservative estimate

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from Duke OTC with detail page enrichment."""
        try:
            await self._init_browser()

            total_pages = await self._get_total_pages()
            self.log_progress(f"Starting scrape of {total_pages} pages")

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
                        self.log_progress(
                            f"Scraped page {page_num}/{total_pages}, "
                            f"found {len(all_technologies)} technologies"
                        )

                    await self.delay()

                except Exception as e:
                    self.log_error(f"Error scraping page {page_num}", e)
                    continue

            # Fetch detail pages concurrently using Playwright
            self.log_progress(f"Fetching detail pages for {len(all_technologies)} technologies")
            semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)

            # Duke blocks aiohttp, so we use Playwright sequentially for details
            for i, tech in enumerate(all_technologies):
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

                if (i + 1) % 20 == 0:
                    self.log_progress(f"Enriched {i + 1}/{len(all_technologies)} technologies")

            for tech in all_technologies:
                self._tech_count += 1
                yield tech

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

        # Build URL with pagination
        url = f"{self.TECHNOLOGIES_URL}?pg={page_num}" if page_num > 1 else self.TECHNOLOGIES_URL
        logger.debug(f"Scraping page {page_num}: {url}")

        try:
            await self._page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(2)

            # Check if we got blocked
            title = await self._page.title()
            if "bot" in title.lower():
                self.log_error("Blocked by bot detection")
                return []

            technologies = []

            # Find all technology links
            all_links = await self._page.query_selector_all("a")

            # First pass: collect all technology URLs and their best titles
            url_titles = {}  # url -> best title

            for link in all_links:
                try:
                    href = await link.get_attribute("href") or ""

                    # Match technology URLs but not categories or base page
                    if "/technologies/" not in href:
                        continue
                    if "/c/" in href or href.endswith("/technologies/"):
                        continue

                    # Normalize URL
                    if not href.startswith("http"):
                        href = urljoin(self.BASE_URL, href)

                    # Check it's a valid technology URL
                    if not re.match(r'https://otc\.duke\.edu/technologies/[a-z0-9-]+/?$', href):
                        continue

                    # Get title from link text
                    title = await link.inner_text()
                    title = ' '.join(title.split()).strip()

                    # Skip empty, "READ MORE", or very short titles
                    if not title or len(title) < 10 or title.upper() == "READ MORE":
                        continue

                    # Keep the longest/best title for each URL
                    if href not in url_titles or len(title) > len(url_titles[href]):
                        url_titles[href] = title

                except Exception as e:
                    logger.debug(f"Error parsing link: {e}")
                    continue

            # Second pass: create Technology objects
            for href, title in url_titles.items():
                tech_id = href.rstrip('/').split('/')[-1]

                raw_data = {
                    "title": title,
                    "url": href,
                    "source_page": url,
                }

                tech = Technology(
                    university="duke",
                    tech_id=tech_id,
                    title=title,
                    url=href,
                    description=None,
                    raw_data=raw_data,
                )
                technologies.append(tech)

            return technologies

        except Exception as e:
            self.log_error(f"Error loading page {page_num}", e)
            return []

    async def scrape_technology_detail(self, url: str) -> Optional[dict]:
        """Scrape detailed information from a technology's detail page using Playwright."""
        if not self._page:
            await self._init_browser()

        try:
            await self._page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(1)

            # Check for bot detection
            title = await self._page.title()
            if "bot" in title.lower():
                logger.debug(f"Bot detection on detail page: {url}")
                return None

            html_content = await self._page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            detail: dict = {"url": url}

            # Get main content from article or main element
            main = soup.select_one("article, main, .entry-content, .content")
            if main:
                # Full description from all paragraphs
                paragraphs = main.find_all("p")
                desc_parts = []
                for p in paragraphs:
                    t = p.get_text(strip=True)
                    if t and len(t) > 20:
                        desc_parts.append(t)
                if desc_parts:
                    detail["full_description"] = "\n".join(desc_parts)

                # Look for structured sections with headings
                for heading in main.find_all(["h2", "h3", "h4", "strong"]):
                    htxt = heading.get_text(strip=True).lower()
                    items = []
                    nxt = heading.find_next_sibling()
                    while nxt:
                        if nxt.name in ("h2", "h3", "h4", "strong") and nxt.get_text(strip=True):
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
                    if "advantage" in htxt or "benefit" in htxt:
                        detail["advantages"] = items
                    elif "application" in htxt or "use" in htxt:
                        detail["applications"] = items
                    elif "inventor" in htxt or "researcher" in htxt:
                        detail["inventors"] = items
                    elif "patent" in htxt or "ip" in htxt:
                        detail["patent_info"] = " ".join(items)
                    elif "publication" in htxt or "reference" in htxt:
                        detail["publications"] = [{"text": t} for t in items]
                    elif "status" in htxt or "stage" in htxt or "development" in htxt:
                        detail["development_stage"] = " ".join(items)

                # Categories from tags/categories
                categories = []
                for a in main.find_all("a", href=True):
                    href = a.get("href", "")
                    if "/technologies/c/" in href or "category" in href:
                        cat = a.get_text(strip=True)
                        if cat and cat not in categories:
                            categories.append(cat)
                if categories:
                    detail["categories"] = categories

            # Contact from footer or sidebar
            contact = {}
            email_link = soup.select_one("a[href^='mailto:']")
            if email_link:
                contact["email"] = email_link["href"].replace("mailto:", "").split("?")[0]
            if contact:
                detail["contact"] = contact

            # Patent status from text
            text = soup.get_text().lower()
            if "patent pending" in text or "patent-pending" in text:
                detail["patent_status"] = "Pending"
            elif "patent filed" in text:
                detail["patent_status"] = "Filed"
            elif "patented" in text or "patent granted" in text:
                detail["patent_status"] = "Granted"

            return detail

        except Exception as e:
            logger.debug(f"Error scraping detail page {url}: {e}")
            return None
