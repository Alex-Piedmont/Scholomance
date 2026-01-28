"""Tests for patent status detection."""

import pytest

from src.patent_detector import (
    PatentDetector,
    PatentDetectionResult,
    PatentStatus,
    patent_detector,
)


class TestPatentDetector:
    """Tests for PatentDetector class."""

    def test_detect_from_jhu_style_raw_data(self):
        """Test detection from JHU-style patentStatuses array."""
        raw_data = {
            "patentStatuses": [
                {"name": "Patent Issued"},
                {"name": "Patent Pending"},
            ]
        }

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.GRANTED
        assert result.confidence >= 0.9
        assert result.source == "api_data"
        assert "Patent Issued" in result.details

    def test_detect_from_raw_data_pending(self):
        """Test detection of pending status from raw data."""
        raw_data = {
            "patentStatuses": [{"name": "Patent Pending"}]
        }

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.PENDING
        assert result.source == "api_data"

    def test_detect_from_raw_data_patent_status_field(self):
        """Test detection from direct patent_status field."""
        raw_data = {"patent_status": "granted"}

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.GRANTED
        assert result.source == "api_data"

    def test_detect_from_raw_data_patent_numbers(self):
        """Test detection from patent_numbers field."""
        raw_data = {"patent_numbers": ["US12345678", "EP987654"]}

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.GRANTED
        assert result.source == "api_data"

    def test_detect_from_raw_data_has_patent_bool(self):
        """Test detection from has_patent boolean field."""
        raw_data = {"has_patent": True}

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.GRANTED
        assert result.source == "api_data"

    def test_detect_us_patent_number_in_url(self):
        """Test detection of US patent number in URL."""
        url = "https://example.com/tech/US12345678"

        result = patent_detector.detect(url=url)

        assert result.status == PatentStatus.GRANTED
        assert result.confidence >= 0.85
        assert result.source == "url_patent_number"
        assert "US12345678" in result.details

    def test_detect_wipo_patent_in_url(self):
        """Test detection of WIPO patent number in URL."""
        url = "https://example.com/tech/WO2023/123456"

        result = patent_detector.detect(url=url)

        assert result.status == PatentStatus.GRANTED
        assert "WO" in result.details

    def test_detect_ep_patent_in_url(self):
        """Test detection of European patent number in URL."""
        url = "https://example.com/tech/EP1234567"

        result = patent_detector.detect(url=url)

        assert result.status == PatentStatus.GRANTED
        assert "EP" in result.details

    def test_detect_from_title_patent_issued(self):
        """Test detection from 'patent issued' in title."""
        title = "Novel Drug Delivery System (Patent Issued)"

        result = patent_detector.detect(title=title)

        assert result.status == PatentStatus.GRANTED
        assert result.source == "text_explicit"

    def test_detect_from_description_patented(self):
        """Test detection from 'patented' in description."""
        description = "This technology has been patented and is available for licensing."

        result = patent_detector.detect(description=description)

        assert result.status == PatentStatus.GRANTED

    def test_detect_from_title_patent_pending(self):
        """Test detection from 'patent pending' in title."""
        title = "New Sensor Technology - Patent Pending"

        result = patent_detector.detect(title=title)

        assert result.status == PatentStatus.PENDING
        assert result.source == "text_explicit"

    def test_detect_from_description_application_filed(self):
        """Test detection from 'application filed' in description."""
        description = "Patent application filed in 2023."

        result = patent_detector.detect(description=description)

        # "application filed" is more specific than "pending"
        assert result.status == PatentStatus.FILED

    def test_detect_provisional_patent(self):
        """Test detection of provisional patent status."""
        description = "A provisional patent application has been filed."

        result = patent_detector.detect(description=description)

        assert result.status == PatentStatus.PROVISIONAL

    def test_detect_pct_filed(self):
        """Test detection of PCT filed status."""
        description = "PCT application filed internationally."

        result = patent_detector.detect(description=description)

        assert result.status == PatentStatus.FILED

    def test_detect_expired_patent(self):
        """Test detection of expired patent status."""
        description = "The patent expired in 2020 and is now in the public domain."

        result = patent_detector.detect(description=description)

        assert result.status == PatentStatus.EXPIRED

    def test_detect_from_url_path(self):
        """Test detection from /patent/ in URL path."""
        url = "https://tech.university.edu/patent/12345"

        result = patent_detector.detect(url=url)

        assert result.status == PatentStatus.GRANTED
        assert result.source == "url_path"
        assert result.confidence < 0.85  # Lower confidence than patent number

    def test_no_patent_info_returns_unknown(self):
        """Test that no patent info returns unknown status."""
        result = patent_detector.detect(
            title="New Software Algorithm",
            description="An innovative approach to data processing.",
            url="https://tech.university.edu/technology/12345",
        )

        assert result.status == PatentStatus.UNKNOWN
        assert result.confidence == 0.0
        assert result.source == "none"

    def test_empty_inputs_returns_unknown(self):
        """Test that empty inputs return unknown status."""
        result = patent_detector.detect()

        assert result.status == PatentStatus.UNKNOWN

    def test_priority_granted_over_pending(self):
        """Test that granted status takes priority over pending when both present."""
        raw_data = {
            "patentStatuses": [
                {"name": "Patent Pending"},
                {"name": "Patent Issued"},  # This should take priority
            ]
        }

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.GRANTED

    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        title = "PATENT PENDING Technology"

        result = patent_detector.detect(title=title)

        assert result.status == PatentStatus.PENDING

    def test_combined_sources_api_data_wins(self):
        """Test that API data takes precedence over text detection."""
        raw_data = {"patent_status": "pending"}
        title = "This is patented technology"  # Would indicate granted

        result = patent_detector.detect(raw_data=raw_data, title=title)

        # API data should win
        assert result.status == PatentStatus.PENDING
        assert result.source == "api_data"

    def test_patent_statuses_as_string_list(self):
        """Test patentStatuses as a simple string list."""
        raw_data = {
            "patentStatuses": ["Granted", "Pending"]
        }

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.GRANTED

    def test_us_patent_number_in_text_indicates_granted(self):
        """Test that US patent number in text indicates granted status."""
        description = "Licensed under US12345678."

        result = patent_detector.detect(description=description)

        assert result.status == PatentStatus.GRANTED


class TestFlintboxPatentDetection:
    """Tests for Flintbox-specific patent detection."""

    def test_detect_from_ip_status_granted(self):
        """Test detection from Flintbox ip_status field."""
        raw_data = {"ip_status": "Granted"}

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.GRANTED
        assert result.source == "api_data"

    def test_detect_from_ip_status_filed(self):
        """Test detection of Filed status from ip_status."""
        raw_data = {"ip_status": "Filed"}

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.FILED
        assert result.source == "api_data"

    def test_detect_from_publications_issued_patent(self):
        """Test detection from 'Issued US patent' in publications HTML."""
        raw_data = {
            "publications": '<ul><li>Issued US patent <a href="https://patents.google.com/patent/US9389413B2/en">9,389,413</a></li></ul>'
        }

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.GRANTED
        assert "9389413" in result.details or "9,389,413" in result.details

    def test_detect_from_publications_us_patent_number(self):
        """Test detection of granted patent from US patent number in publications."""
        raw_data = {
            "publications": '<p>US Patent 10,410,380</p>'
        }

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.GRANTED

    def test_detect_from_publications_pending_application(self):
        """Test detection of pending status from US application number (202x)."""
        raw_data = {
            "publications": '<p>US 20240030400</p>'
        }

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.PENDING

    def test_detect_from_publications_patent_pending_text(self):
        """Test detection of patent pending text in publications."""
        raw_data = {
            "publications": '<p>This technology is patent pending.</p>'
        }

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.PENDING

    def test_detect_from_ip_number(self):
        """Test detection from ip_number field."""
        raw_data = {"ip_number": "US10410380"}

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.GRANTED
        assert result.source == "api_data"

    def test_ip_status_takes_precedence(self):
        """Test that ip_status takes precedence over publications."""
        raw_data = {
            "ip_status": "Filed",
            "publications": '<p>US Patent 10,410,380</p>'  # Would indicate granted
        }

        result = patent_detector.detect(raw_data=raw_data)

        # ip_status should win
        assert result.status == PatentStatus.FILED

    def test_detect_provisional_application_in_publications(self):
        """Test detection of provisional patent application in publications."""
        raw_data = {
            "publications": '<li>Provisional Patent Application No. 63/417,605</li>'
        }

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.PROVISIONAL

    def test_detect_pct_in_publications(self):
        """Test detection of PCT filing in publications."""
        raw_data = {
            "publications": '<li>Patent filed (<a href="url">PCT</a>)</li>'
        }

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.FILED

    def test_detect_patent_filed_in_publications(self):
        """Test detection of 'patent filed' in publications."""
        raw_data = {
            "publications": '<p>A patent filed for this technology.</p>'
        }

        result = patent_detector.detect(raw_data=raw_data)

        assert result.status == PatentStatus.FILED


class TestPatentStatusEnum:
    """Tests for PatentStatus enum."""

    def test_enum_values(self):
        """Test that enum has expected values."""
        assert PatentStatus.UNKNOWN.value == "unknown"
        assert PatentStatus.PENDING.value == "pending"
        assert PatentStatus.PROVISIONAL.value == "provisional"
        assert PatentStatus.FILED.value == "filed"
        assert PatentStatus.GRANTED.value == "granted"
        assert PatentStatus.EXPIRED.value == "expired"

    def test_enum_is_string(self):
        """Test that enum values are strings."""
        assert isinstance(PatentStatus.GRANTED.value, str)
        assert PatentStatus.GRANTED == "granted"


class TestPatentDetectionResult:
    """Tests for PatentDetectionResult dataclass."""

    def test_result_creation(self):
        """Test creating a detection result."""
        result = PatentDetectionResult(
            status=PatentStatus.GRANTED,
            confidence=0.95,
            source="api_data",
            details="From patentStatuses",
        )

        assert result.status == PatentStatus.GRANTED
        assert result.confidence == 0.95
        assert result.source == "api_data"
        assert result.details == "From patentStatuses"

    def test_result_optional_details(self):
        """Test that details is optional."""
        result = PatentDetectionResult(
            status=PatentStatus.UNKNOWN,
            confidence=0.0,
            source="none",
        )

        assert result.details is None
