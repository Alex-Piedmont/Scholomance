"""Base scraper for Flintbox platform sites."""

import html as html_mod
import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology
from .flintbox_parsing import (
    clean_html_field,
    clean_html_text,
    is_metadata,
    parse_embedded_sections,
)


class FlintboxScraper(BaseScraper):
    """
    Base scraper for sites using the Flintbox platform.

    Flintbox provides a standard API at /api/v1/technologies that returns
    paginated technology listings.

    Subclasses should set:
    - BASE_URL: The site's base URL (e.g., https://ucf.flintbox.com)
    - UNIVERSITY_CODE: Short code for the university
    - UNIVERSITY_NAME: Human-readable name
    - ORGANIZATION_ID: Flintbox organization ID
    - ACCESS_KEY: Flintbox access key (UUID format)
    """

    BASE_URL: str = ""
    UNIVERSITY_CODE: str = ""
    UNIVERSITY_NAME: str = ""
    ORGANIZATION_ID: str = ""
    ACCESS_KEY: str = ""

    # Set False in a subclass to skip parsing the benefit field as a
    # fallback when the abstract is empty.
    ENABLE_BENEFIT_FALLBACK: bool = True

    def __init__(self, delay_seconds: float = 0.5):
        super().__init__(
            university_code=self.UNIVERSITY_CODE,
            base_url=self.BASE_URL,
            delay_seconds=delay_seconds,
        )
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def name(self) -> str:
        return self.UNIVERSITY_NAME

    @property
    def api_url(self) -> str:
        """URL for the Flintbox API endpoint."""
        return f"{self.BASE_URL}/api/v1/technologies"

    # ── Session management ──────────────────────────────────────────────

    async def _init_session(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug(f"HTTP session initialized for {self.UNIVERSITY_CODE}")

    async def _close_session(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    # ── Scrape orchestration ────────────────────────────────────────────

    async def _get_total_pages(self) -> int:
        await self._init_session()
        params = {
            "organizationId": self.ORGANIZATION_ID,
            "organizationAccessKey": self.ACCESS_KEY,
            "page": 1,
            "query": "",
        }
        try:
            async with self._session.get(self.api_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    total_pages = data.get("meta", {}).get("totalPages", 10)
                    logger.debug(f"{self.UNIVERSITY_CODE} has {total_pages} pages")
                    return total_pages
                else:
                    logger.warning(f"API returned status {response.status}")
                    return 10
        except Exception as e:
            logger.warning(f"Could not determine total pages: {e}")
            return 10

    async def scrape(self) -> AsyncIterator[Technology]:
        """Scrape all technologies from Flintbox."""
        try:
            await self._init_session()
            total_pages = await self._get_total_pages()
            self.log_progress(f"Starting scrape of {total_pages} pages")

            for page_num in range(1, total_pages + 1):
                try:
                    technologies = await self.scrape_page(page_num)
                    if not technologies:
                        self.log_progress(f"No technologies on page {page_num}, stopping")
                        break

                    for tech in technologies:
                        self._tech_count += 1
                        yield tech

                    self._page_count += 1
                    if page_num % 10 == 0:
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
            await self._close_session()

    async def scrape_page(self, page_num: int) -> list[Technology]:
        """Scrape a single page of technologies from the API."""
        await self._init_session()
        params = {
            "organizationId": self.ORGANIZATION_ID,
            "organizationAccessKey": self.ACCESS_KEY,
            "page": page_num,
            "query": "",
        }
        logger.debug(f"Scraping page {page_num}")
        try:
            async with self._session.get(self.api_url, params=params) as response:
                if response.status != 200:
                    self.log_error(f"API returned status {response.status}")
                    return []
                data = await response.json()
                items = data.get("data", [])
                technologies = []
                for item in items:
                    tech = await self._parse_api_item_with_detail(item)
                    if tech:
                        technologies.append(tech)
                return technologies
        except Exception as e:
            self.log_error(f"Error fetching page {page_num}", e)
            return []

    # ── Detail fetching ─────────────────────────────────────────────────

    async def scrape_technology_detail(self, tech_uuid: str) -> Optional[dict]:
        """Fetch detailed information for a specific technology from the API."""
        await self._init_session()
        detail_url = f"{self.BASE_URL}/api/v1/technologies/{tech_uuid}"
        params = {
            "organizationId": self.ORGANIZATION_ID,
            "organizationAccessKey": self.ACCESS_KEY,
        }
        try:
            async with self._session.get(detail_url, params=params) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                attributes = data.get("data", {}).get("attributes", {})

                included = data.get("included", [])
                members, documents, contacts, tags = [], [], [], []
                for item in included:
                    item_type = item.get("type")
                    item_attrs = item.get("attributes", {})
                    if item_type == "member":
                        members.append({
                            "name": item_attrs.get("fullName"),
                            "email": item_attrs.get("email"),
                            "expertise": item_attrs.get("expertise"),
                            "profile": item_attrs.get("profile"),
                        })
                    elif item_type == "document":
                        documents.append({
                            "name": item_attrs.get("name"),
                            "url": item_attrs.get("fileUrl"),
                            "size": item_attrs.get("fileSize"),
                        })
                    elif item_type == "contact":
                        contacts.append({
                            "name": item_attrs.get("fullName"),
                            "email": item_attrs.get("email"),
                            "phone": item_attrs.get("phoneNumber"),
                        })
                    elif item_type == "tag":
                        tag_name = item_attrs.get("name")
                        if tag_name:
                            tags.append(tag_name)

                if members:
                    attributes["_members"] = members
                if documents:
                    attributes["_documents"] = documents
                if contacts:
                    attributes["_contacts"] = contacts
                if tags:
                    attributes["_tags"] = tags
                return attributes

        except Exception as e:
            logger.debug(f"Error fetching technology detail: {e}")
            return None

    # ── Item parsing ────────────────────────────────────────────────────

    def _parse_api_item(self, item: dict) -> Optional[Technology]:
        """Parse a technology item from the API listing (no detail fetch)."""
        try:
            attrs = item.get("attributes", {})
            title = attrs.get("name", "").strip()
            if not title:
                return None

            tech_id = item.get("id", "")
            uuid = attrs.get("uuid", "")
            key_points = [
                attrs[f"keyPoint{i}"].strip()
                for i in range(1, 4)
                if attrs.get(f"keyPoint{i}")
            ]

            return Technology(
                university=self.UNIVERSITY_CODE,
                tech_id=tech_id or uuid or re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50],
                title=title,
                url=f"{self.BASE_URL}/technologies/{uuid}" if uuid else "",
                description=" | ".join(key_points) if key_points else None,
                raw_data={
                    "id": tech_id,
                    "uuid": uuid,
                    "title": title,
                    "key_points": key_points,
                    "published_on": attrs.get("publishedOn"),
                    "featured": attrs.get("featured", False),
                    "image_url": attrs.get("primaryImageSmallUrl"),
                },
            )
        except Exception as e:
            logger.debug(f"Error parsing API item: {e}")
            return None

    async def _parse_api_item_with_detail(self, item: dict) -> Optional[Technology]:
        """Parse a technology item, enriching it with detail-endpoint data."""
        try:
            attrs = item.get("attributes", {})
            uuid = attrs.get("uuid", "")
            if not uuid:
                return self._parse_api_item(item)

            detail = await self.scrape_technology_detail(uuid)

            title = attrs.get("name", "").strip()
            if not title:
                return None

            tech_id = item.get("id", "")
            key_points = [
                html_mod.unescape(attrs[f"keyPoint{i}"].strip())
                for i in range(1, 4)
                if attrs.get(f"keyPoint{i}")
            ]

            # Build base raw_data
            raw_data = {
                "id": tech_id,
                "uuid": uuid,
                "title": title,
                "key_points": key_points,
                "published_on": attrs.get("publishedOn"),
                "featured": attrs.get("featured", False),
                "image_url": attrs.get("primaryImageSmallUrl"),
            }

            parsed = {}
            if detail:
                parsed = self._merge_detail_fields(detail, raw_data)

            description = self._build_description(detail, parsed, key_points)
            innovators, keywords, patent_status = self._extract_top_level_fields(detail, parsed)

            return Technology(
                university=self.UNIVERSITY_CODE,
                tech_id=tech_id or uuid or re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50],
                title=title,
                url=f"{self.BASE_URL}/technologies/{uuid}" if uuid else "",
                description=description,
                innovators=innovators,
                keywords=keywords,
                patent_status=patent_status,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing API item with detail: {e}")
            return self._parse_api_item(item)

    # ── Detail field merging ────────────────────────────────────────────

    def _merge_detail_fields(self, detail: dict, raw_data: dict) -> dict:
        """Merge detail-endpoint data into raw_data. Returns parsed sections dict."""
        # IP fields
        ip_status_val = detail.get("ipStatus")
        ip_date_val = detail.get("ipDate")
        if ip_status_val and ip_date_val:
            raw_data["ip_status"] = f"{ip_status_val} — {ip_date_val}"
        else:
            raw_data["ip_status"] = ip_status_val
        raw_data["ip_number"] = detail.get("ipNumber")
        raw_data["ip_url"] = detail.get("ipUrl")
        raw_data["ip_date"] = ip_date_val
        raw_data["publications"] = detail.get("publications")

        # 'other' field — separate metadata from content
        other_raw = detail.get("other")
        if other_raw and is_metadata(other_raw):
            raw_data["other_metadata"] = other_raw
        else:
            raw_data["other"] = other_raw

        # Parse embedded sections from abstract
        abstract_raw = detail.get("abstract")
        parsed = parse_embedded_sections(abstract_raw)
        raw_data["abstract"] = parsed.get("abstract")
        if parsed.get("background"):
            raw_data["background"] = parsed["background"]
        if parsed.get("market_application") and not detail.get("marketApplication"):
            raw_data["market_application"] = parsed["market_application"]
        else:
            raw_data["market_application"] = detail.get("marketApplication")
        if parsed.get("benefit") and not detail.get("benefit"):
            raw_data["benefit"] = parsed["benefit"]
        else:
            raw_data["benefit"] = detail.get("benefit")
        if parsed.get("solution"):
            raw_data["solution"] = parsed["solution"]
        if parsed.get("reference_number"):
            raw_data["reference_number"] = parsed["reference_number"]
        if parsed.get("patents"):
            raw_data["patents_html"] = parsed["patents"]
        if parsed.get("publications_html"):
            raw_data["publications_html"] = parsed["publications_html"]
            if not raw_data.get("publications"):
                raw_data["publications"] = parsed["publications_html"]
        if parsed.get("ip_text"):
            ip_text_val = parsed["ip_text"]
            if ip_date_val and ip_date_val not in ip_text_val:
                ip_text_val = f"{ip_text_val} — {ip_date_val}"
            raw_data["ip_text"] = ip_text_val
        if parsed.get("development_stage"):
            raw_data["development_stage"] = parsed["development_stage"]
        if parsed.get("researchers_html"):
            raw_data["researchers_html"] = parsed["researchers_html"]
        if parsed.get("keywords_html"):
            raw_data["keywords_html"] = parsed["keywords_html"]

        # Benefit-as-abstract fallback: when the abstract field is empty,
        # some sites embed sections in the benefit field instead.
        if self.ENABLE_BENEFIT_FALLBACK:
            self._apply_benefit_fallback(detail, parsed, raw_data)

        self._extract_publication_links(raw_data)
        self._clean_raw_data_fields(raw_data)

        # Researchers, documents, contacts, tags
        raw_data["researchers"] = detail.get("_members")
        raw_data["documents"] = detail.get("_documents")
        raw_data["contacts"] = detail.get("_contacts")
        raw_data["flintbox_tags"] = detail.get("_tags")

        return parsed

    def _apply_benefit_fallback(self, detail: dict, parsed: dict, raw_data: dict) -> None:
        """When abstract is empty, try parsing embedded sections from the benefit field."""
        if parsed.get("abstract") or not detail.get("benefit"):
            return

        from .flintbox_parsing import _HEADING_STRIP_RE

        benefit_parsed = parse_embedded_sections(detail.get("benefit", ""))
        for key, val in benefit_parsed.items():
            if val and key not in parsed:
                parsed[key] = val

        _FALLBACK_FIELDS = (
            ("abstract", "abstract"), ("background", "background"),
            ("market_application", "market_application"), ("benefit", "benefit"),
            ("publications_html", "publications_html"), ("ip_text", "ip_text"),
            ("development_stage", "development_stage"),
            ("researchers_html", "researchers_html"),
            ("keywords_html", "keywords_html"), ("solution", "solution"),
            ("patents", "patents_html"), ("reference_number", "reference_number"),
        )
        for src_key, dst_key in _FALLBACK_FIELDS:
            val = benefit_parsed.get(src_key)
            if not val or raw_data.get(dst_key):
                continue
            if src_key == "abstract":
                plain = re.sub(r"<[^>]+>", " ", val).strip()
                if _HEADING_STRIP_RE.fullmatch(plain):
                    continue
            raw_data[dst_key] = val

    @staticmethod
    def _extract_publication_links(raw_data: dict) -> None:
        """Extract structured hyperlinks from publication HTML fields."""
        for pub_key in ("publications", "publications_html"):
            pub_raw = raw_data.get(pub_key)
            if pub_raw and isinstance(pub_raw, str) and "<a" in pub_raw.lower():
                pub_soup = BeautifulSoup(pub_raw, "html.parser")
                pub_links = []
                for a_tag in pub_soup.find_all("a", href=True):
                    link_text = a_tag.get_text(strip=True)
                    link_url = a_tag["href"]
                    if link_text or link_url:
                        pub_links.append({"text": link_text or link_url, "url": link_url})
                if pub_links:
                    raw_data["publications"] = pub_links
                    break

    @staticmethod
    def _clean_raw_data_fields(raw_data: dict) -> None:
        """Clean HTML from text fields in raw_data."""
        for key in ("market_application", "benefit", "abstract", "background", "other",
                     "solution", "patents_html", "publications", "publications_html",
                     "ip_text", "development_stage", "researchers_html", "keywords_html"):
            raw = raw_data.get(key)
            if not raw or not isinstance(raw, str):
                continue
            raw_data[key] = clean_html_field(raw)

    # ── Description and top-level field extraction ──────────────────────

    def _build_description(
        self,
        detail: Optional[dict],
        parsed: dict,
        key_points: list[str],
    ) -> Optional[str]:
        """Select the best description from available fields."""
        if detail:
            abstract_raw = detail.get("abstract", "")
            candidates = []
            if parsed.get("abstract"):
                candidates.append(("abstract", parsed["abstract"]))
            elif abstract_raw:
                candidates.append(("abstract", abstract_raw))
            candidates.append(("other", detail.get("other", "")))
            candidates.append(("benefit", detail.get("benefit", "")))

            for field, raw_text in candidates:
                if not raw_text:
                    continue
                if field == "other" and is_metadata(raw_text):
                    continue
                cleaned = clean_html_text(raw_text)
                if cleaned and len(cleaned) > 20:
                    return cleaned[:2000]

        return " | ".join(key_points) if key_points else None

    @staticmethod
    def _extract_top_level_fields(
        detail: Optional[dict],
        parsed: dict,
    ) -> tuple[Optional[list[str]], Optional[list[str]], Optional[str]]:
        """Extract innovators, keywords, and patent_status from detail data."""
        innovators = None
        keywords = None
        patent_status = None

        if detail:
            members = detail.get("_members", [])
            if members:
                innovators = [m["name"] for m in members if m.get("name")] or None
            tags = detail.get("_tags")
            if tags:
                keywords = tags
            if not keywords and parsed.get("keywords_html"):
                keywords = [k.strip() for k in parsed["keywords_html"].split(",") if k.strip()]
            ip_status = detail.get("ipStatus")
            if ip_status:
                patent_status = ip_status

        return innovators, keywords, patent_status
