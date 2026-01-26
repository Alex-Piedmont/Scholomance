"""UGA Flintbox technology scraper using Playwright."""

import asyncio
import json
import re
from typing import AsyncIterator, Optional
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page, Browser, Route
from loguru import logger

from .base import BaseScraper, Technology


class UGAScraper(BaseScraper):
    """Scraper for UGA's Flintbox technology listings.

    Flintbox is a React-based platform that loads data via API calls.
    This scraper intercepts those API calls when possible, falling back
    to DOM scraping when needed.
    """

    BASE_URL = "https://uga.flintbox.com"
    TECHNOLOGIES_URL = f"{BASE_URL}/technologies"
    API_URL = f"{BASE_URL}/api"

    def __init__(self, delay_seconds: float = 1.5):
        super().__init__(
            university_code="uga",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._api_data: list[dict] = []

    @property
    def name(self) -> str:
        return "UGA Flintbox"

    async def _init_browser(self) -> None:
        """Initialize Playwright browser."""
        if self._browser is None:
            playwright = await async_playwright().start()
            self._browser = await playwright.chromium.launch(headless=True)
            self._page = await self._browser.new_page()
            await self._page.set_viewport_size({"width": 1920, "height": 1080})

            # Set up request interception to capture API responses
            await self._page.route("**/api/**", self._handle_api_route)

            logger.debug("Browser initialized for UGA Flintbox")

    async def _handle_api_route(self, route: Route) -> None:
        """Intercept API requests to capture technology data."""
        response = await route.fetch()
        try:
            if "technologies" in route.request.url or "listings" in route.request.url:
                body = await response.text()
                try:
                    data = json.loads(body)
                    if isinstance(data, list):
                        self._api_data.extend(data)
                    elif isinstance(data, dict) and "data" in data:
                        self._api_data.extend(data["data"])
                    elif isinstance(data, dict) and "technologies" in data:
                        self._api_data.extend(data["technologies"])
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logger.debug(f"Error handling API route: {e}")

        await route.fulfill(response=response)

    async def _close_browser(self) -> None:
        """Close Playwright browser."""
        if self._page:
            await self._page.close()
            self._page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.debug("Browser closed")

    async def _scroll_to_load_all(self) -> None:
        """Scroll the page to trigger lazy loading of all items."""
        if not self._page:
            return

        try:
            # Get initial height
            last_height = await self._page.evaluate("document.body.scrollHeight")

            while True:
                # Scroll to bottom
                await self._page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await asyncio.sleep(1)

                # Calculate new height
                new_height = await self._page.evaluate("document.body.scrollHeight")

                if new_height == last_height:
                    break

                last_height = new_height

                # Safety limit
                if self._tech_count > 500:
                    break

        except Exception as e:
            logger.debug(f"Error during scroll: {e}")

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from UGA Flintbox."""
        try:
            await self._init_browser()
            self._api_data = []

            self.log_progress("Loading UGA Flintbox technologies page")

            await self._page.goto(self.TECHNOLOGIES_URL, wait_until="networkidle", timeout=60000)

            # Wait for React to render
            await asyncio.sleep(2)

            # Try to find and click "Load More" or scroll to load all
            await self._load_all_technologies()

            # First try to use intercepted API data
            if self._api_data:
                self.log_progress(f"Found {len(self._api_data)} technologies via API")
                for item in self._api_data:
                    tech = self._parse_api_item(item)
                    if tech:
                        self._tech_count += 1
                        yield tech
            else:
                # Fall back to DOM scraping
                self.log_progress("Falling back to DOM scraping")
                async for tech in self._scrape_from_dom():
                    yield tech

            self.log_progress(f"Completed scraping: {self._tech_count} technologies")

        finally:
            await self._close_browser()

    async def _load_all_technologies(self) -> None:
        """Load all technologies by clicking load more or scrolling."""
        if not self._page:
            return

        try:
            # Look for "Load More" button
            load_more_attempts = 0
            max_attempts = 50

            while load_more_attempts < max_attempts:
                load_more = await self._page.query_selector(
                    "button:has-text('Load More'), "
                    "button:has-text('Show More'), "
                    "a:has-text('Load More'), "
                    "[class*='load-more'], "
                    "[class*='show-more']"
                )

                if load_more:
                    try:
                        await load_more.click()
                        await asyncio.sleep(1)
                        load_more_attempts += 1
                    except Exception:
                        break
                else:
                    break

            # Also try scrolling
            await self._scroll_to_load_all()

        except Exception as e:
            logger.debug(f"Error loading all technologies: {e}")

    def _parse_api_item(self, item: dict) -> Optional[Technology]:
        """Parse a technology item from API response."""
        try:
            tech_id = str(item.get("id", item.get("slug", "")))
            title = item.get("title", item.get("name", ""))

            if not title:
                return None

            url = item.get("url", "")
            if not url and tech_id:
                url = f"{self.BASE_URL}/technologies/{tech_id}"

            description = item.get("description", item.get("summary", item.get("abstract", "")))

            # Clean HTML from description if present
            if description:
                description = re.sub(r"<[^>]+>", "", description)
                description = description.strip()

            keywords = item.get("keywords", item.get("tags", []))
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.split(",") if k.strip()]

            innovators = item.get("inventors", item.get("researchers", item.get("contacts", [])))
            if isinstance(innovators, str):
                innovators = [i.strip() for i in innovators.split(",") if i.strip()]
            elif isinstance(innovators, list):
                # Handle list of dicts with name field
                if innovators and isinstance(innovators[0], dict):
                    innovators = [i.get("name", str(i)) for i in innovators]

            raw_data = {
                "original": item,
                "title": title,
                "description": description,
                "url": url,
            }

            return Technology(
                university="uga",
                tech_id=tech_id,
                title=title,
                url=url,
                description=description,
                keywords=keywords if keywords else None,
                innovators=innovators if innovators else None,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing API item: {e}")
            return None

    async def _scrape_from_dom(self) -> AsyncIterator[Technology]:
        """Scrape technologies from the DOM when API interception fails."""
        if not self._page:
            return

        # Wait for items to load
        await self._page.wait_for_selector(
            ".technology-card, .listing-card, [class*='technology'], "
            "[class*='listing'], article, .card",
            timeout=15000,
        )

        items = await self._page.query_selector_all(
            ".technology-card, .listing-card, [class*='technology-item'], "
            "[class*='listing-item'], article.card, .card"
        )

        for item in items:
            tech = await self._parse_dom_item(item)
            if tech:
                self._tech_count += 1
                yield tech

    async def _parse_dom_item(self, item) -> Optional[Technology]:
        """Parse a technology item from DOM element."""
        try:
            # Get title and link
            title_elem = await item.query_selector(
                "h2 a, h3 a, .title a, [class*='title'] a, a[href*='/technologies/']"
            )

            if not title_elem:
                title_elem = await item.query_selector("h2, h3, .title, [class*='title']")

            if not title_elem:
                return None

            title = await title_elem.inner_text()
            title = title.strip()

            if not title:
                return None

            # Get URL
            link = await item.query_selector("a[href*='/technologies/']")
            url = ""
            if link:
                href = await link.get_attribute("href")
                url = urljoin(self.BASE_URL, href) if href else ""

            # Extract tech_id from URL
            tech_id = ""
            if url:
                match = re.search(r"/technologies/([^/?]+)", url)
                if match:
                    tech_id = match.group(1)

            if not tech_id:
                tech_id = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50]

            # Get description
            desc_elem = await item.query_selector(
                ".description, .summary, .abstract, p, [class*='description']"
            )
            description = ""
            if desc_elem:
                description = await desc_elem.inner_text()
                description = description.strip()

            # Get tags/keywords
            keywords = []
            tag_elems = await item.query_selector_all(
                ".tag, .keyword, [class*='tag'], [class*='category']"
            )
            for tag_elem in tag_elems:
                tag_text = await tag_elem.inner_text()
                if tag_text.strip():
                    keywords.append(tag_text.strip())

            raw_data = {
                "title": title,
                "description": description,
                "url": url,
                "keywords": keywords,
                "source_page": self._page.url if self._page else "",
            }

            return Technology(
                university="uga",
                tech_id=tech_id,
                title=title,
                url=url,
                description=description,
                keywords=keywords if keywords else None,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing DOM item: {e}")
            return None

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """
        Scrape a single page - for Flintbox this is less meaningful
        since it uses infinite scroll, but implemented for interface compatibility.
        """
        # Flintbox doesn't have traditional pagination
        # This method exists for interface compatibility
        if page_num == 1:
            technologies = []
            async for tech in self.scrape():
                technologies.append(tech)
            return technologies
        return []

    async def scrape_technology_detail(self, url: str) -> Optional[dict]:
        """Scrape detailed information from a technology's detail page."""
        if not self._page:
            await self._init_browser()

        try:
            await self._page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(1)  # Wait for React

            detail = {}

            # Get full description
            desc_elem = await self._page.query_selector(
                ".description, .content, [class*='description'], article"
            )
            if desc_elem:
                detail["full_description"] = await desc_elem.inner_text()

            # Get contact info
            contact_elem = await self._page.query_selector(
                ".contact, [class*='contact'], .inventor"
            )
            if contact_elem:
                detail["contact"] = await contact_elem.inner_text()

            # Get categories
            cat_elems = await self._page.query_selector_all(
                ".category, .tag, [class*='category']"
            )
            if cat_elems:
                detail["categories"] = []
                for elem in cat_elems:
                    text = await elem.inner_text()
                    if text.strip():
                        detail["categories"].append(text.strip())

            return detail

        except Exception as e:
            logger.debug(f"Error scraping detail page {url}: {e}")
            return None
