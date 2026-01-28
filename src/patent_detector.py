"""Patent status detection service.

Detects patent status from multiple sources:
- API-provided data (like JHU's patentStatuses)
- URL patterns (patent numbers, /patent/ paths)
- Text content (keywords like "Patent Issued", "Patent Pending")
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class PatentStatus(str, Enum):
    """Patent status values."""

    UNKNOWN = "unknown"
    PENDING = "pending"
    PROVISIONAL = "provisional"
    FILED = "filed"
    GRANTED = "granted"
    EXPIRED = "expired"


# Confidence levels for different detection sources
SOURCE_CONFIDENCE = {
    "api_data": 0.95,  # Most reliable - explicit from source
    "url_patent_number": 0.90,  # Patent number in URL is strong signal
    "text_explicit": 0.85,  # Explicit text like "Patent Issued"
    "text_implicit": 0.70,  # Implicit text like mentions of patents
    "url_path": 0.60,  # /patent/ in path is weaker signal
}


@dataclass
class PatentDetectionResult:
    """Result of patent status detection."""

    status: PatentStatus
    confidence: float
    source: str  # Where the detection came from
    details: Optional[str] = None  # Additional info like patent number


class PatentDetector:
    """Detects patent status from various sources."""

    # Patent number patterns
    PATENT_NUMBER_PATTERNS = [
        # US patents: US followed by 7-10 digits
        (r"US\s*(\d{7,10})", "US"),
        # US application numbers: US20XX/XXXXXXX
        (r"US\s*20\d{2}/\d{6,7}", "US_APP"),
        # WIPO/PCT: WO followed by year/number
        (r"WO\s*(\d{4})/(\d+)", "WIPO"),
        # European patents: EP followed by digits
        (r"EP\s*(\d+)", "EP"),
        # Japanese patents: JP followed by digits
        (r"JP\s*(\d+)", "JP"),
        # Chinese patents: CN followed by digits
        (r"CN\s*(\d+)", "CN"),
        # Generic patent number in URL
        (r"/patent/(\d{7,10})", "URL"),
    ]

    # Keywords indicating granted patents (case-insensitive)
    GRANTED_KEYWORDS = [
        r"\bpatent\s+issued\b",
        r"\bpatent\s+granted\b",
        r"\bgranted\s+patent\b",
        r"\bissued\s+patent\b",
        r"\bpatented\b",
        r"\bUS\s*\d{7,10}\b",  # US patent numbers indicate granted
    ]

    # Keywords indicating pending patents (more general - checked after provisional/filed)
    PENDING_KEYWORDS = [
        r"\bpatent\s+pending\b",
        r"\bpending\s+patent\b",
        r"\bawaiting\s+patent\b",
    ]

    # Keywords indicating provisional patents
    PROVISIONAL_KEYWORDS = [
        r"\bprovisional\s+patent\b",
        r"\bprovisional\s+application\b",
        r"\bprovisionall?y\s+patented\b",
    ]

    # Keywords indicating filed status
    FILED_KEYWORDS = [
        r"\bpct\s+filed\b",
        r"\bfiled\s+pct\b",
        r"\bpct\s+application\b",
        r"\binternational\s+application\b",
        r"\bpatent\s+application\s+filed\b",
        r"\bapplication\s+filed\b",
    ]

    # Keywords indicating expired patents
    EXPIRED_KEYWORDS = [
        r"\bpatent\s+expired\b",
        r"\bexpired\s+patent\b",
    ]

    def detect(
        self,
        raw_data: Optional[dict[str, Any]] = None,
        url: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
    ) -> PatentDetectionResult:
        """
        Detect patent status from available data sources.

        Checks sources in order of reliability:
        1. API-provided data (raw_data with patentStatuses, patent_status, etc.)
        2. Patent numbers in URL
        3. Keywords in title/description
        4. URL path patterns

        Args:
            raw_data: Raw data from scraper (may contain patent info)
            url: Technology URL
            title: Technology title
            description: Technology description

        Returns:
            PatentDetectionResult with status, confidence, and source
        """
        # Try detection sources in order of reliability
        result = self._detect_from_raw_data(raw_data)
        if result and result.status != PatentStatus.UNKNOWN:
            return result

        result = self._detect_from_url_patent_number(url)
        if result and result.status != PatentStatus.UNKNOWN:
            return result

        result = self._detect_from_text(title, description)
        if result and result.status != PatentStatus.UNKNOWN:
            return result

        result = self._detect_from_url_path(url)
        if result and result.status != PatentStatus.UNKNOWN:
            return result

        # No patent info found
        return PatentDetectionResult(
            status=PatentStatus.UNKNOWN,
            confidence=0.0,
            source="none",
            details="No patent information detected",
        )

    def _detect_from_raw_data(
        self, raw_data: Optional[dict[str, Any]]
    ) -> Optional[PatentDetectionResult]:
        """Detect patent status from raw API data."""
        if not raw_data:
            return None

        # Check for JHU-style patentStatuses array
        patent_statuses = raw_data.get("patentStatuses") or raw_data.get(
            "patent_statuses"
        )
        if patent_statuses:
            return self._parse_patent_statuses(patent_statuses)

        # Check for Flintbox-style ip_status field
        ip_status = raw_data.get("ip_status") or raw_data.get("ipStatus")
        if ip_status:
            status = self._normalize_status(ip_status)
            if status != PatentStatus.UNKNOWN:
                return PatentDetectionResult(
                    status=status,
                    confidence=SOURCE_CONFIDENCE["api_data"],
                    source="api_data",
                    details=f"From ip_status: {ip_status}",
                )

        # Check for Flintbox publications field (HTML with patent info)
        publications = raw_data.get("publications")
        if publications:
            result = self._parse_publications_html(publications)
            if result:
                return result

        # Check for direct patent_status field
        patent_status = raw_data.get("patent_status") or raw_data.get("patentStatus")
        if patent_status:
            status = self._normalize_status(patent_status)
            if status != PatentStatus.UNKNOWN:
                return PatentDetectionResult(
                    status=status,
                    confidence=SOURCE_CONFIDENCE["api_data"],
                    source="api_data",
                    details=f"From API: {patent_status}",
                )

        # Check for patent numbers in raw data
        patent_numbers = raw_data.get("patent_numbers") or raw_data.get("patentNumbers")
        if patent_numbers:
            return PatentDetectionResult(
                status=PatentStatus.GRANTED,
                confidence=SOURCE_CONFIDENCE["api_data"],
                source="api_data",
                details=f"Patent numbers: {patent_numbers}",
            )

        # Check for ip_number field (Flintbox)
        ip_number = raw_data.get("ip_number") or raw_data.get("ipNumber")
        if ip_number:
            return PatentDetectionResult(
                status=PatentStatus.GRANTED,
                confidence=SOURCE_CONFIDENCE["api_data"],
                source="api_data",
                details=f"IP number: {ip_number}",
            )

        # Check for patent field (boolean or string)
        has_patent = raw_data.get("patent") or raw_data.get("has_patent")
        if has_patent:
            if isinstance(has_patent, bool) and has_patent:
                return PatentDetectionResult(
                    status=PatentStatus.GRANTED,
                    confidence=SOURCE_CONFIDENCE["api_data"],
                    source="api_data",
                    details="Patent flag is true",
                )
            elif isinstance(has_patent, str):
                status = self._normalize_status(has_patent)
                if status != PatentStatus.UNKNOWN:
                    return PatentDetectionResult(
                        status=status,
                        confidence=SOURCE_CONFIDENCE["api_data"],
                        source="api_data",
                        details=f"From patent field: {has_patent}",
                    )

        return None

    def _parse_publications_html(self, html: str) -> Optional[PatentDetectionResult]:
        """Parse Flintbox publications HTML for patent information."""
        if not html:
            return None

        html_lower = html.lower()

        # Check for "Issued US patent" pattern (granted)
        issued_match = re.search(
            r"issued\s+(?:us\s+)?patent\s+[\d,]+",
            html_lower
        )
        if issued_match:
            # Extract patent number
            num_match = re.search(r"(\d{1,3}(?:,\d{3})+|\d{7,})", html)
            patent_num = num_match.group(1) if num_match else "unknown"
            return PatentDetectionResult(
                status=PatentStatus.GRANTED,
                confidence=SOURCE_CONFIDENCE["api_data"],
                source="api_data",
                details=f"Issued patent in publications: {patent_num}",
            )

        # Check for US patent numbers in publications
        # Granted patents: 7-8 digit numbers NOT starting with 202x
        # Published applications: numbers starting with 202x (pending)
        patent_nums = re.findall(
            r"US\s*(?:Patent\s*)?(?:No\.?\s*)?(\d{1,3}(?:,\d{3})+|\d{7,})",
            html,
            re.IGNORECASE
        )

        granted_patents = []
        pending_applications = []

        for num in patent_nums:
            # Remove commas for analysis
            clean_num = num.replace(",", "")
            # Published applications start with year (202x)
            if clean_num.startswith("202") and len(clean_num) >= 10:
                pending_applications.append(num)
            elif len(clean_num) >= 7:
                granted_patents.append(num)

        if granted_patents:
            return PatentDetectionResult(
                status=PatentStatus.GRANTED,
                confidence=SOURCE_CONFIDENCE["api_data"],
                source="api_data",
                details=f"US patent(s) in publications: {', '.join(granted_patents[:3])}",
            )

        if pending_applications:
            return PatentDetectionResult(
                status=PatentStatus.PENDING,
                confidence=SOURCE_CONFIDENCE["api_data"],
                source="api_data",
                details=f"US application(s) in publications: {', '.join(pending_applications[:3])}",
            )

        # Check for "patent pending" in publications
        if "patent pending" in html_lower:
            return PatentDetectionResult(
                status=PatentStatus.PENDING,
                confidence=SOURCE_CONFIDENCE["api_data"],
                source="api_data",
                details="Patent pending mentioned in publications",
            )

        # Check for provisional patent applications
        if re.search(r"provisional\s+patent\s+application", html_lower):
            return PatentDetectionResult(
                status=PatentStatus.PROVISIONAL,
                confidence=SOURCE_CONFIDENCE["api_data"],
                source="api_data",
                details="Provisional patent application in publications",
            )

        # Check for "patent filed" or PCT applications
        if re.search(r"patent\s+filed", html_lower) or re.search(r"\bpct\b", html_lower):
            return PatentDetectionResult(
                status=PatentStatus.FILED,
                confidence=SOURCE_CONFIDENCE["api_data"],
                source="api_data",
                details="Patent filed/PCT in publications",
            )

        return None

    def _parse_patent_statuses(
        self, patent_statuses: list[Any]
    ) -> Optional[PatentDetectionResult]:
        """Parse JHU-style patentStatuses array."""
        if not patent_statuses:
            return None

        # JHU format: [{"name": "Patent Issued"}, {"name": "Patent Pending"}]
        # Take the "best" status (granted > pending > provisional > filed)
        best_status = PatentStatus.UNKNOWN
        details = []

        for ps in patent_statuses:
            if isinstance(ps, dict):
                name = ps.get("name", "")
            elif isinstance(ps, str):
                name = ps
            else:
                continue

            details.append(name)
            status = self._normalize_status(name)

            # Update if this is a "better" status
            if self._status_priority(status) > self._status_priority(best_status):
                best_status = status

        if best_status != PatentStatus.UNKNOWN:
            return PatentDetectionResult(
                status=best_status,
                confidence=SOURCE_CONFIDENCE["api_data"],
                source="api_data",
                details=f"From patentStatuses: {', '.join(details)}",
            )

        return None

    def _status_priority(self, status: PatentStatus) -> int:
        """Return priority of status (higher = more definitive)."""
        priorities = {
            PatentStatus.UNKNOWN: 0,
            PatentStatus.FILED: 1,
            PatentStatus.PROVISIONAL: 2,
            PatentStatus.PENDING: 3,
            PatentStatus.EXPIRED: 4,
            PatentStatus.GRANTED: 5,
        }
        return priorities.get(status, 0)

    def _normalize_status(self, status_str: str) -> PatentStatus:
        """Normalize a status string to a PatentStatus enum."""
        status_lower = status_str.lower().strip()

        # Direct mappings
        if status_lower in ("granted", "issued", "patented"):
            return PatentStatus.GRANTED
        if status_lower in ("pending", "patent pending"):
            return PatentStatus.PENDING
        if status_lower in ("provisional", "provisional patent"):
            return PatentStatus.PROVISIONAL
        if status_lower in ("filed", "application filed"):
            return PatentStatus.FILED
        if status_lower in ("expired",):
            return PatentStatus.EXPIRED

        # Pattern matching for more complex strings
        if re.search(r"\b(issued|granted|patented)\b", status_lower):
            return PatentStatus.GRANTED
        if re.search(r"\bpending\b", status_lower):
            return PatentStatus.PENDING
        if re.search(r"\bprovisional\b", status_lower):
            return PatentStatus.PROVISIONAL
        if re.search(r"\bfiled\b", status_lower):
            return PatentStatus.FILED
        if re.search(r"\bexpired\b", status_lower):
            return PatentStatus.EXPIRED

        return PatentStatus.UNKNOWN

    def _detect_from_url_patent_number(
        self, url: Optional[str]
    ) -> Optional[PatentDetectionResult]:
        """Detect patent status from patent numbers in URL."""
        if not url:
            return None

        for pattern, patent_type in self.PATENT_NUMBER_PATTERNS:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                patent_num = match.group(0)
                return PatentDetectionResult(
                    status=PatentStatus.GRANTED,
                    confidence=SOURCE_CONFIDENCE["url_patent_number"],
                    source="url_patent_number",
                    details=f"Patent number in URL: {patent_num} ({patent_type})",
                )

        return None

    def _detect_from_text(
        self, title: Optional[str], description: Optional[str]
    ) -> Optional[PatentDetectionResult]:
        """Detect patent status from keywords in title/description."""
        text = ""
        if title:
            text += title + " "
        if description:
            text += description

        if not text.strip():
            return None

        text_lower = text.lower()

        # Check for granted keywords first (highest priority)
        for pattern in self.GRANTED_KEYWORDS:
            if re.search(pattern, text_lower):
                return PatentDetectionResult(
                    status=PatentStatus.GRANTED,
                    confidence=SOURCE_CONFIDENCE["text_explicit"],
                    source="text_explicit",
                    details=f"Matched pattern: {pattern}",
                )

        # Check for US patent numbers in text (indicates granted)
        us_patent_match = re.search(r"\bUS\s*(\d{7,10})\b", text, re.IGNORECASE)
        if us_patent_match:
            return PatentDetectionResult(
                status=PatentStatus.GRANTED,
                confidence=SOURCE_CONFIDENCE["text_explicit"],
                source="text_explicit",
                details=f"US patent number in text: {us_patent_match.group(0)}",
            )

        # Check for expired (before pending, as it's more specific)
        for pattern in self.EXPIRED_KEYWORDS:
            if re.search(pattern, text_lower):
                return PatentDetectionResult(
                    status=PatentStatus.EXPIRED,
                    confidence=SOURCE_CONFIDENCE["text_explicit"],
                    source="text_explicit",
                    details=f"Matched pattern: {pattern}",
                )

        # Check for provisional keywords (before pending, more specific)
        for pattern in self.PROVISIONAL_KEYWORDS:
            if re.search(pattern, text_lower):
                return PatentDetectionResult(
                    status=PatentStatus.PROVISIONAL,
                    confidence=SOURCE_CONFIDENCE["text_explicit"],
                    source="text_explicit",
                    details=f"Matched pattern: {pattern}",
                )

        # Check for filed keywords (before pending, more specific)
        for pattern in self.FILED_KEYWORDS:
            if re.search(pattern, text_lower):
                return PatentDetectionResult(
                    status=PatentStatus.FILED,
                    confidence=SOURCE_CONFIDENCE["text_explicit"],
                    source="text_explicit",
                    details=f"Matched pattern: {pattern}",
                )

        # Check for pending keywords (most general)
        for pattern in self.PENDING_KEYWORDS:
            if re.search(pattern, text_lower):
                return PatentDetectionResult(
                    status=PatentStatus.PENDING,
                    confidence=SOURCE_CONFIDENCE["text_explicit"],
                    source="text_explicit",
                    details=f"Matched pattern: {pattern}",
                )

        return None

    def _detect_from_url_path(
        self, url: Optional[str]
    ) -> Optional[PatentDetectionResult]:
        """Detect patent status from URL path patterns."""
        if not url:
            return None

        url_lower = url.lower()

        # Check for /patent/ or /patents/ in path
        if "/patent/" in url_lower or "/patents/" in url_lower:
            return PatentDetectionResult(
                status=PatentStatus.GRANTED,
                confidence=SOURCE_CONFIDENCE["url_path"],
                source="url_path",
                details="URL contains /patent/ path",
            )

        return None


# Singleton instance for convenience
patent_detector = PatentDetector()
