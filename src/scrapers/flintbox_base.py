"""Base scraper for Flintbox platform sites."""

import re
from typing import AsyncIterator, Optional

import aiohttp
from bs4 import BeautifulSoup
from loguru import logger

from .base import BaseScraper, Technology


_METADATA_PATTERNS = re.compile(
    r"(Contact\s*:|Inventors?\s*:|Technology Category|Case Manager|"
    r"Contact Information|Case Number|Case #|USU Ref\.|USU Department)",
    re.IGNORECASE,
)

_SECTION_MARKERS = re.compile(
    r"(?:Market\s+Applications?\s*:?|Features,?\s+Benefits?\s*(?:&|and)\s*Advantages?\s*:?|"
    r"Benefits?\s*:?|Reference\s+Number\s*:?|"
    r"Technology\s+(?:Overview|Applications?|Advantages?)\s*:?|"
    r"Potential\s+Applications?\s*:?|Advantages?\s*:?|"
    r"Background\s*(?:&amp;|&)\s*Unmet\s+Need\s*:?|"
    r"Publications?\s*:?|Patents?\s*:?)",
    re.IGNORECASE,
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

    async def _init_session(self) -> None:
        """Initialize aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            logger.debug(f"HTTP session initialized for {self.UNIVERSITY_CODE}")

    async def _close_session(self) -> None:
        """Close aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.debug("HTTP session closed")

    async def _get_total_pages(self) -> int:
        """Get total number of pages from API."""
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
                    meta = data.get("meta", {})
                    total_pages = meta.get("totalPages", 10)
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

    @staticmethod
    def _clean_html_text(raw_text: str) -> str:
        """Strip HTML tags and decode common HTML entities."""
        cleaned = re.sub(r"<[^>]+>", " ", raw_text)
        cleaned = cleaned.replace("&nbsp;", " ").replace("&amp;", "&")
        cleaned = cleaned.replace("&lt;", "<").replace("&gt;", ">")
        cleaned = cleaned.replace("&quot;", '"')
        # Convert middle-dot bullets to dashes
        cleaned = re.sub(r"[·•]\s*", "- ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def _is_metadata(text: str) -> bool:
        """Check if text is internal metadata rather than narrative content."""
        if not text:
            return False
        cleaned = re.sub(r"<[^>]+>", " ", text).strip()
        return bool(_METADATA_PATTERNS.search(cleaned))

    @staticmethod
    def _parse_embedded_sections(abstract_html: str) -> dict:
        """Parse TTU-style abstracts that contain embedded section markers.

        Returns a dict with keys: abstract, market_application, benefit.
        Only populated if markers are found; otherwise returns {"abstract": abstract_html}.
        """
        if not abstract_html:
            return {"abstract": abstract_html}

        # Check for section markers in the text (ignoring HTML tags)
        plain = re.sub(r"<[^>]+>", " ", abstract_html)
        if not _SECTION_MARKERS.search(plain):
            return {"abstract": abstract_html}

        # Split on section headers that may be wrapped in HTML tags like
        # <p><strong>Market Applications:</strong></p> or <p>Market Applications:</p>
        tag = r"(?:</?(?:p|strong|b|br|em|h[1-6])\s*/?>[\s\n]*)*"
        section_re = re.compile(
            tag
            + r"(?:"
            + r"(?P<abstract>Abstract\s*:\s*)"
            + r"|(?P<market>(?:Market|Technology|Potential)\s+Applications?\s*:?\s*)"
            + r"|(?P<benefit>"
            +   r"Features,?\s+Benefits?\s*(?:&amp;|&|and)\s*Advantages?\s*:?\s*"
            +   r"|Technology\s+Advantages?\s*:?\s*"
            +   r"|Advantages?\s*:?\s*"
            + r")"
            + r"|(?P<background>Background\s*(?:&amp;|&)\s*Unmet\s+Need\s*:?\s*)"
            + r"|(?P<overview>Technology\s+Overview\s*:?\s*)"
            + r"|(?P<ip>Intellectual\s+Property\s*:?\s*)"
            + r"|(?P<patents>(?<=\>)Patents?\s*:?\s*)"
            + r"|(?P<pubs>Publications?\s*:?\s*)"
            + r"|(?P<dev>Development(?:al)?\s+Stage\s*:?\s*)"
            + r"|(?P<researcher>Researchers?\s*\(?\s*s?\s*\)?\s*:?\s*)"
            + r"|(?P<keywords>Key\s*[Ww]ords?\s*:?\s*)"
            + r"|(?P<refnum>Reference\s+Number\s*:?\s*)"
            + r")"
            + tag,
            re.IGNORECASE,
        )

        # Use finditer to get sections with positions
        sections: list[tuple[str, int, int]] = []  # (name, content_start, next_start)
        for m in section_re.finditer(abstract_html):
            # Determine which group matched
            name = next((k for k, v in m.groupdict().items() if v), "unknown")
            sections.append((name, m.end(), m.start()))

        result: dict = {}

        if not sections:
            result["abstract"] = abstract_html
            return result

        # Text before the first section marker
        before = abstract_html[:sections[0][2]].strip()
        before = re.sub(r"(?:</?(?:p|strong|b|br|em)\s*/?>[\s\n]*)+$", "", before).strip()
        if before:
            result["abstract"] = before

        # Extract content for each section
        for idx, (name, content_start, _) in enumerate(sections):
            content_end = sections[idx + 1][2] if idx + 1 < len(sections) else len(abstract_html)
            content = abstract_html[content_start:content_end].strip()
            content = re.sub(r"(?:</?(?:p|strong|b|br|em)\s*/?>[\s\n]*)+$", "", content).strip()
            if not content:
                continue

            if name == "abstract":
                result.setdefault("abstract", content)
            elif name == "background":
                result["background"] = content
            elif name == "overview":
                result["abstract"] = content
            elif name == "market":
                result["market_application"] = content
            elif name == "benefit":
                result["benefit"] = content
            elif name == "patents":
                result["patents"] = content
                # Also extract as ip_text if no separate IP section
                if "ip_text" not in result:
                    result["ip_text"] = content
            elif name == "pubs":
                result["publications_html"] = content
            elif name == "refnum":
                result["reference_number"] = content
            elif name == "ip":
                result["ip_text"] = content
            elif name == "dev":
                result["development_stage"] = content
            elif name == "researcher":
                result["researchers_html"] = content
            elif name == "keywords":
                result["keywords_html"] = content

        # Clean HTML from list-style fields: extract text items from <li> tags
        for key in ("market_application", "benefit", "background", "ip_text", "development_stage",
                     "researchers_html", "keywords_html"):
            raw = result.get(key)
            if not raw:
                continue
            soup = BeautifulSoup(raw, "html.parser")
            items = [li.get_text(strip=True) for li in soup.find_all("li") if li.get_text(strip=True)]
            if items:
                result[key] = "\n".join(items)
            else:
                result[key] = soup.get_text(separator=" ", strip=True)
            # Clean non-breaking spaces
            result[key] = result[key].replace('\xa0', ' ').replace('&nbsp;', ' ')

        return result

    def _parse_api_item(self, item: dict) -> Optional[Technology]:
        """Parse a technology item from the API response."""
        try:
            attrs = item.get("attributes", {})

            title = attrs.get("name", "").strip()
            if not title:
                return None

            tech_id = item.get("id", "")
            uuid = attrs.get("uuid", "")

            # Build description from key points
            key_points = []
            for i in range(1, 4):
                kp = attrs.get(f"keyPoint{i}")
                if kp:
                    key_points.append(kp.strip())

            description = " | ".join(key_points) if key_points else None

            # Build URL
            url = f"{self.BASE_URL}/technologies/{uuid}" if uuid else ""

            # Get published date
            published_on = attrs.get("publishedOn")

            raw_data = {
                "id": tech_id,
                "uuid": uuid,
                "title": title,
                "key_points": key_points,
                "published_on": published_on,
                "featured": attrs.get("featured", False),
                "image_url": attrs.get("primaryImageSmallUrl"),
            }

            return Technology(
                university=self.UNIVERSITY_CODE,
                tech_id=tech_id or uuid or re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50],
                title=title,
                url=url,
                description=description,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing API item: {e}")
            return None

    async def _parse_api_item_with_detail(self, item: dict) -> Optional[Technology]:
        """Parse a technology item and fetch additional detail data."""
        try:
            attrs = item.get("attributes", {})
            uuid = attrs.get("uuid", "")

            if not uuid:
                return self._parse_api_item(item)

            # Fetch detail data for IP status and publications
            detail = await self.scrape_technology_detail(uuid)

            title = attrs.get("name", "").strip()
            if not title:
                return None

            tech_id = item.get("id", "")

            # Build description from key points
            key_points = []
            for i in range(1, 4):
                kp = attrs.get(f"keyPoint{i}")
                if kp:
                    key_points.append(kp.strip())

            # Use detail description if available, otherwise key points
            description = None
            if detail:
                # Parse embedded sections from abstract (TTU pattern)
                abstract_raw = detail.get("abstract", "")
                parsed_sections = self._parse_embedded_sections(abstract_raw)

                # Try parsed abstract first, then full abstract, other, benefit
                candidates = []
                if parsed_sections.get("abstract"):
                    candidates.append(("abstract", parsed_sections["abstract"]))
                elif abstract_raw:
                    candidates.append(("abstract", abstract_raw))
                candidates.append(("other", detail.get("other", "")))
                candidates.append(("benefit", detail.get("benefit", "")))

                for field, raw_text in candidates:
                    if not raw_text:
                        continue
                    if field == "other" and self._is_metadata(raw_text):
                        continue
                    cleaned = self._clean_html_text(raw_text)
                    if cleaned and len(cleaned) > 20:
                        description = cleaned[:2000]
                        break

            if not description:
                description = " | ".join(key_points) if key_points else None

            # Build URL
            url = f"{self.BASE_URL}/technologies/{uuid}" if uuid else ""

            # Get published date
            published_on = attrs.get("publishedOn")

            # Build raw_data with detail fields
            raw_data = {
                "id": tech_id,
                "uuid": uuid,
                "title": title,
                "key_points": key_points,
                "published_on": published_on,
                "featured": attrs.get("featured", False),
                "image_url": attrs.get("primaryImageSmallUrl"),
            }

            # Add detail fields if available
            if detail:
                raw_data["ip_status"] = detail.get("ipStatus")
                raw_data["ip_number"] = detail.get("ipNumber")
                raw_data["ip_url"] = detail.get("ipUrl")
                raw_data["ip_date"] = detail.get("ipDate")
                raw_data["publications"] = detail.get("publications")

                # Handle 'other' — store metadata separately
                other_raw = detail.get("other")
                if other_raw and self._is_metadata(other_raw):
                    raw_data["other_metadata"] = other_raw
                else:
                    raw_data["other"] = other_raw

                # Handle abstract with embedded sections (TTU pattern)
                abstract_raw = detail.get("abstract")
                parsed = self._parse_embedded_sections(abstract_raw)
                raw_data["abstract"] = parsed.get("abstract")
                if parsed.get("background"):
                    raw_data["background"] = parsed["background"]
                # Only override if detail didn't already provide these fields
                if parsed.get("market_application") and not detail.get("marketApplication"):
                    raw_data["market_application"] = parsed["market_application"]
                else:
                    raw_data["market_application"] = detail.get("marketApplication")
                if parsed.get("benefit") and not detail.get("benefit"):
                    raw_data["benefit"] = parsed["benefit"]
                else:
                    raw_data["benefit"] = detail.get("benefit")
                if parsed.get("reference_number"):
                    raw_data["reference_number"] = parsed["reference_number"]
                if parsed.get("patents"):
                    raw_data["patents_html"] = parsed["patents"]
                if parsed.get("publications_html"):
                    raw_data["publications_html"] = parsed["publications_html"]
                    if not raw_data.get("publications"):
                        raw_data["publications"] = parsed["publications_html"]
                if parsed.get("ip_text"):
                    raw_data["ip_text"] = parsed["ip_text"]
                if parsed.get("development_stage"):
                    raw_data["development_stage"] = parsed["development_stage"]
                if parsed.get("researchers_html"):
                    raw_data["researchers_html"] = parsed["researchers_html"]
                if parsed.get("keywords_html"):
                    raw_data["keywords_html"] = parsed["keywords_html"]
                # Clean HTML and formatting from text fields
                for key in ("market_application", "benefit", "abstract", "background", "other",
                             "patents_html", "publications_html", "ip_text",
                             "development_stage", "researchers_html", "keywords_html"):
                    raw = raw_data.get(key)
                    if not raw or not isinstance(raw, str):
                        continue
                    # Strip HTML tags if present
                    if "<" in raw:
                        soup = BeautifulSoup(raw, "html.parser")
                        items = [li.get_text(strip=True) for li in soup.find_all("li") if li.get_text(strip=True)]
                        if items:
                            raw = "\n".join(items)
                        else:
                            raw = soup.get_text(separator="\n", strip=True)
                    # Clean non-breaking spaces and bullet markers
                    raw = raw.replace('\xa0', ' ').replace('&nbsp;', ' ')
                    raw = re.sub(r'[·•]\s*', '', raw)
                    raw = re.sub(r'[ \t]+', ' ', raw)
                    # Clean up lines
                    lines = [line.strip() for line in raw.split('\n')]
                    raw_data[key] = '\n'.join(line for line in lines if line)

                # Store researchers, documents, contacts, and tags
                raw_data["researchers"] = detail.get("_members")
                raw_data["documents"] = detail.get("_documents")
                raw_data["contacts"] = detail.get("_contacts")
                raw_data["flintbox_tags"] = detail.get("_tags")

            # Extract top-level fields from detail
            innovators = None
            keywords = None
            patent_status = None
            if detail:
                members = detail.get("_members", [])
                if members:
                    innovators = [m["name"] for m in members if m.get("name")]
                    innovators = innovators or None
                tags = detail.get("_tags")
                if tags:
                    keywords = tags
                # Use embedded keywords if no tags available
                if not keywords and parsed.get("keywords_html"):
                    keywords = [k.strip() for k in parsed["keywords_html"].split(",") if k.strip()]
                ip_status = detail.get("ipStatus")
                if ip_status:
                    patent_status = ip_status

            return Technology(
                university=self.UNIVERSITY_CODE,
                tech_id=tech_id or uuid or re.sub(r"[^a-zA-Z0-9]+", "-", title.lower())[:50],
                title=title,
                url=url,
                description=description,
                innovators=innovators,
                keywords=keywords,
                patent_status=patent_status,
                raw_data=raw_data,
            )

        except Exception as e:
            logger.debug(f"Error parsing API item with detail: {e}")
            return self._parse_api_item(item)

    async def scrape_technology_detail(self, tech_uuid: str) -> Optional[dict]:
        """Scrape detailed information for a specific technology."""
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

                # Extract members (researchers) from included data
                included = data.get("included", [])
                members = []
                documents = []
                contacts = []
                tags = []

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

                # Add extracted data to attributes
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

    # Backwards compatibility methods
    async def _init_browser(self) -> None:
        """Backwards compatibility - initializes HTTP session instead."""
        await self._init_session()

    async def _close_browser(self) -> None:
        """Backwards compatibility - closes HTTP session instead."""
        await self._close_session()
