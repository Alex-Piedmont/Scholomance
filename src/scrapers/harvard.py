"""Harvard Office of Technology Development scraper."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology


class HarvardScraper(BaseScraper):
    """Scraper for Harvard University's Office of Technology Development portal."""

    BASE_URL = "https://otd.harvard.edu"
    RESULTS_URL = f"{BASE_URL}/explore-innovation/technologies/results/"

    # Categories to query (technologies may appear in multiple categories)
    CATEGORIES = [
        "antibodies-protein-therapeutics",
        "artificial-intelligence",
        "cardiovascular-metabolic-disease",
        "cell-interrogation-tissue-engineering",
        "chemistry-biochemistry",
        "cns-neurology",
        "computer-science-bioinformatics",
        "covid-19",
        "dental-medicine",
        "dermatology",
        "diagnostics-biomarkers",
        "drug-discovery-research-tools",
        "electronics-semiconductors",
        "energy-environment",
        "genomics-proteomics",
        "imaging-agents",
        "immunology-autoimmune-diseases",
        "materials-science-interface-science",
        "medical-devices",
        "microbiology-infectious-disease",
        "microbiome",
        "microfluidics",
        "musculoskeletal",
        "nucleic-acid-based-therapies",
        "nutraceuticals-functional-foods-dietary-supplements",
        "oncology",
        "ophthalmology",
        "photonics",
        "quantum-devices-technology",
        "reagents-and-research-materials",
        "robotics-wearable-electronics",
        "sensors-imaging",
        "small-molecule-therapeutics",
        "stem-cells-regenerative-medicine",
        "vaccines",
    ]

    def __init__(self, delay_seconds: float = 0.5):
        super().__init__(
            university_code="harvard",
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None
        self._seen_urls: set[str] = set()

    @property
    def name(self) -> str:
        return "Harvard Office of Technology Development"

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for Harvard")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def _get_technologies_from_category(self, category: str) -> list[dict]:
        """Get technologies from a specific category."""
        await self._init_session()

        url = f"{self.RESULTS_URL}?category={category}"

        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    self.log_error(f"Category {category} returned status {response.status}")
                    return []

                html = await response.text()
                soup = BeautifulSoup(html, "lxml")

                technologies = []

                # Find all technology links
                for link in soup.find_all("a", href=True):
                    href = link.get("href", "")
                    if "/explore-innovation/technologies/" in href and "/results/" not in href:
                        # Get the title from the link text
                        title = link.get_text(strip=True)
                        if title and href not in self._seen_urls:
                            self._seen_urls.add(href)

                            # Get description from parent/sibling elements if available
                            description = None
                            parent = link.find_parent("div")
                            if parent:
                                desc_elem = parent.find("p")
                                if desc_elem:
                                    description = desc_elem.get_text(strip=True)

                            technologies.append({
                                "url": href if href.startswith("http") else f"{self.BASE_URL}{href}",
                                "title": title,
                                "description": description,
                                "category": category,
                            })

                return technologies

        except Exception as e:
            self.log_error(f"Error fetching category {category}", e)
            return []

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from Harvard OTD."""
        try:
            await self._init_session()
            self._seen_urls = set()

            self.log_progress(f"Scraping {len(self.CATEGORIES)} categories")

            for i, category in enumerate(self.CATEGORIES):
                techs = await self._get_technologies_from_category(category)

                for item in techs:
                    tech = self._parse_item(item)
                    if tech:
                        self._tech_count += 1
                        yield tech

                self._page_count += 1
                if (i + 1) % 10 == 0:
                    self.log_progress(
                        f"Processed {i + 1}/{len(self.CATEGORIES)} categories, "
                        f"found {self._tech_count} unique technologies"
                    )

                await self.delay()

            self.log_progress(
                f"Completed scraping: {self._tech_count} unique technologies"
            )

        finally:
            await self._close_session()

    def _parse_item(self, item: dict) -> Optional[Technology]:
        """Parse technology info from scraped item."""
        try:
            title = item.get("title", "").strip()
            if not title:
                return None

            url = item.get("url", "")

            # Extract tech_id from URL slug
            tech_id = ""
            if url:
                slug = url.rstrip("/").split("/")[-1]
                tech_id = slug

            if not tech_id:
                tech_id = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50]

            description = item.get("description")

            raw_data = {
                "url": url,
                "title": title,
                "description": description,
                "category": item.get("category"),
            }

            return Technology(
                university="harvard",
                tech_id=tech_id,
                title=title,
                url=url,
                description=description,
                keywords=[item.get("category")] if item.get("category") else None,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing item: {e}")
            return None

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """
        Scrape technologies - Harvard uses category-based approach.
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
            async with self._session.get(url) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "lxml")

                detail = {"url": url}

                # Get full description
                content = soup.find("div", class_="content")
                if content:
                    detail["full_description"] = content.get_text(strip=True)

                return detail

        except Exception as e:
            logger.debug(f"Error fetching technology detail: {e}")
            return None

    # Backwards compatibility methods
    async def _init_browser(self) -> None:
        """Backwards compatibility - initializes HTTP session instead."""
        await self._init_session()

    async def _close_browser(self) -> None:
        """Backwards compatibility - closes HTTP session instead."""
        await self._close_session()
