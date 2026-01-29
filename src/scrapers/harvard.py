"""Harvard Office of Technology Development scraper."""

import asyncio
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology

DETAIL_CONCURRENCY = 5


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
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug("HTTP session initialized for Harvard")

    async def _close_session(self) -> None:
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
                    if detail.get("investigators"):
                        tech.innovators = detail["investigators"]
                    if detail.get("categories"):
                        if not tech.keywords:
                            tech.keywords = detail["categories"]
                        else:
                            for cat in detail["categories"]:
                                if cat not in tech.keywords:
                                    tech.keywords.append(cat)
                    if detail.get("patent_status"):
                        tech.patent_status = detail["patent_status"]
                await asyncio.sleep(self.delay_seconds)
            except Exception as e:
                logger.debug(f"Error fetching detail for {tech.url}: {e}")
        return tech

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from Harvard OTD with detail enrichment."""
        try:
            await self._init_session()
            self._seen_urls = set()

            self.log_progress(f"Scraping {len(self.CATEGORIES)} categories")

            all_technologies = []

            for i, category in enumerate(self.CATEGORIES):
                techs = await self._get_technologies_from_category(category)

                for item in techs:
                    tech = self._parse_item(item)
                    if tech:
                        all_technologies.append(tech)

                self._page_count += 1
                if (i + 1) % 10 == 0:
                    self.log_progress(
                        f"Processed {i + 1}/{len(self.CATEGORIES)} categories, "
                        f"found {len(all_technologies)} unique technologies"
                    )

                await self.delay()

            self.log_progress(f"Fetching detail pages for {len(all_technologies)} technologies")
            semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)
            tasks = [self._fetch_detail(tech, semaphore) for tech in all_technologies]
            enriched = await asyncio.gather(*tasks)

            for tech in enriched:
                self._tech_count += 1
                yield tech

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
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, "lxml")

                detail: dict = {"url": url}
                text = soup.get_text()

                # Full description from rich-text or content div
                content = soup.select_one(".rich-text, .content, article")
                if content:
                    paragraphs = content.find_all("p")
                    desc_parts = [p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)]
                    if desc_parts:
                        detail["full_description"] = "\n".join(desc_parts)

                # Investigators from h6 or labeled section
                investigators = []
                for h6 in soup.find_all("h6"):
                    h6_text = h6.get_text(strip=True).lower()
                    if "investigator" in h6_text or "inventor" in h6_text or "researcher" in h6_text:
                        # Names might be in the next element
                        nxt = h6.find_next_sibling()
                        if nxt:
                            names = nxt.get_text(strip=True)
                            investigators.extend([n.strip() for n in names.split(",") if n.strip()])
                        break

                # Also look for investigators in text pattern
                if not investigators:
                    inv_match = re.search(r'(?:Investigators?|Inventors?|Researchers?)[:\s]*([^\n]+)', text)
                    if inv_match:
                        names = inv_match.group(1).strip()
                        investigators = [n.strip() for n in names.split(",") if n.strip() and len(n.strip()) > 2]

                if investigators:
                    detail["investigators"] = investigators

                # Case number
                case_match = re.search(r'Case\s*(?:Number|#|No\.?)[:\s]*(\d+)', text)
                if case_match:
                    detail["case_number"] = case_match.group(1)

                # Patent status
                patent_text = text.lower()
                if "patent(s) pending" in patent_text or "patent pending" in patent_text:
                    detail["patent_status"] = "Pending"
                elif "patent granted" in patent_text or "patented" in patent_text:
                    detail["patent_status"] = "Granted"
                elif "patent filed" in patent_text:
                    detail["patent_status"] = "Filed"
                elif "provisional" in patent_text and "patent" in patent_text:
                    detail["patent_status"] = "Provisional"

                # Categories from links
                categories = []
                for a in soup.find_all("a", href=True):
                    href = a.get("href", "")
                    if "category=" in href:
                        cat = a.get_text(strip=True)
                        if cat and cat not in categories:
                            categories.append(cat)
                if categories:
                    detail["categories"] = categories

                # Contact
                contact = {}
                email_link = soup.select_one("a[href^='mailto:']")
                if email_link:
                    contact["email"] = email_link["href"].replace("mailto:", "").split("?")[0]
                    # Try to find name nearby
                    parent = email_link.find_parent()
                    if parent:
                        pt = parent.get_text(strip=True)
                        name = pt.replace(contact["email"], "").replace("[Email]", "").strip().rstrip(",").strip()
                        if name and len(name) > 2:
                            contact["name"] = name
                if contact:
                    detail["contact"] = contact

                # Structured data from JSON-LD
                for script in soup.find_all("script", type="application/ld+json"):
                    try:
                        import json
                        data = json.loads(script.string)
                        if isinstance(data, dict):
                            if data.get("@type") == "CreativeWork":
                                if data.get("author") and not investigators:
                                    authors = data["author"]
                                    if isinstance(authors, list):
                                        detail["investigators"] = [
                                            a.get("name", "") for a in authors if isinstance(a, dict) and a.get("name")
                                        ]
                                    elif isinstance(authors, dict) and authors.get("name"):
                                        detail["investigators"] = [authors["name"]]
                                if data.get("description") and "full_description" not in detail:
                                    detail["full_description"] = data["description"]
                    except (json.JSONDecodeError, AttributeError):
                        pass

                return detail

        except Exception as e:
            logger.debug(f"Error fetching technology detail: {e}")
            return None

    # Backwards compatibility methods
    async def _init_browser(self) -> None:
        await self._init_session()

    async def _close_browser(self) -> None:
        await self._close_session()
