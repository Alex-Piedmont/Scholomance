"""Tests for FlintboxScraper base class detail field mapping."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.scrapers.flintbox_base import FlintboxScraper


class TestFlintboxScraper(FlintboxScraper):
    """Concrete subclass for testing."""
    BASE_URL = "https://test.flintbox.com"
    UNIVERSITY_CODE = "test"
    UNIVERSITY_NAME = "Test University"
    ORGANIZATION_ID = "1"
    ACCESS_KEY = "test-key"


def make_list_item(tech_id="123", uuid="abc-uuid", name="Test Tech"):
    return {
        "id": tech_id,
        "attributes": {
            "name": name,
            "uuid": uuid,
            "keyPoint1": "Key point 1",
            "keyPoint2": "Key point 2",
            "publishedOn": "2024-01-01",
            "featured": False,
            "primaryImageSmallUrl": None,
        },
    }


def make_detail_response(
    abstract="This is the abstract of the technology.",
    other="<p>Detailed <b>HTML</b> description</p>",
    benefit="Key benefit text here",
    ip_status="Filed",
    ip_number="IP-001",
    members=None,
    tags=None,
    documents=None,
    contacts=None,
):
    data = {
        "data": {
            "attributes": {
                "abstract": abstract,
                "other": other,
                "benefit": benefit,
                "ipStatus": ip_status,
                "ipNumber": ip_number,
                "marketApplication": "Market app text",
                "publications": "Some publication",
            }
        },
        "included": [],
    }
    if members is None:
        members = [
            {"type": "member", "attributes": {"fullName": "Dr. Jane Smith", "email": "jane@test.edu", "expertise": "AI", "profile": "Prof"}},
            {"type": "member", "attributes": {"fullName": "Dr. Bob Jones", "email": "bob@test.edu", "expertise": "ML", "profile": "Asst Prof"}},
        ]
    if tags is None:
        tags = [
            {"type": "tag", "attributes": {"name": "Machine Learning"}},
            {"type": "tag", "attributes": {"name": "Healthcare"}},
        ]
    if documents is None:
        documents = [
            {"type": "document", "attributes": {"name": "Whitepaper.pdf", "fileUrl": "https://test.com/doc.pdf", "fileSize": 1024}},
        ]
    if contacts is None:
        contacts = [
            {"type": "contact", "attributes": {"fullName": "Tech Transfer Office", "email": "tto@test.edu", "phoneNumber": "555-0100"}},
        ]
    data["included"] = members + tags + documents + contacts
    return data


@pytest.mark.asyncio
async def test_parse_api_item_with_detail_maps_innovators():
    scraper = TestFlintboxScraper()
    detail_resp = make_detail_response()

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=detail_resp)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    scraper._session = mock_session

    item = make_list_item()
    tech = await scraper._parse_api_item_with_detail(item)

    assert tech is not None
    assert tech.innovators == ["Dr. Jane Smith", "Dr. Bob Jones"]


@pytest.mark.asyncio
async def test_parse_api_item_with_detail_maps_keywords():
    scraper = TestFlintboxScraper()
    detail_resp = make_detail_response()

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=detail_resp)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    scraper._session = mock_session

    item = make_list_item()
    tech = await scraper._parse_api_item_with_detail(item)

    assert tech is not None
    assert tech.keywords == ["Machine Learning", "Healthcare"]


@pytest.mark.asyncio
async def test_parse_api_item_with_detail_maps_patent_status():
    scraper = TestFlintboxScraper()
    detail_resp = make_detail_response(ip_status="Issued")

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=detail_resp)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    scraper._session = mock_session

    item = make_list_item()
    tech = await scraper._parse_api_item_with_detail(item)

    assert tech is not None
    assert tech.patent_status == "Issued"


@pytest.mark.asyncio
async def test_parse_api_item_with_detail_prefers_abstract_for_description():
    scraper = TestFlintboxScraper()
    detail_resp = make_detail_response(
        abstract="A clear abstract description of the technology that is long enough.",
        other="<p>HTML other field</p>",
    )

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=detail_resp)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    scraper._session = mock_session

    item = make_list_item()
    tech = await scraper._parse_api_item_with_detail(item)

    assert tech is not None
    assert "clear abstract" in tech.description


@pytest.mark.asyncio
async def test_parse_api_item_with_detail_strips_html():
    scraper = TestFlintboxScraper()
    detail_resp = make_detail_response(
        abstract="",
        other="<p>This is a <b>bold</b> description with <a href='#'>links</a> that should be stripped.</p>",
    )

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=detail_resp)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    scraper._session = mock_session

    item = make_list_item()
    tech = await scraper._parse_api_item_with_detail(item)

    assert tech is not None
    assert "<" not in tech.description
    assert "bold" in tech.description


@pytest.mark.asyncio
async def test_parse_api_item_with_detail_falls_back_to_key_points():
    scraper = TestFlintboxScraper()
    detail_resp = make_detail_response(abstract="", other="", benefit="")

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=detail_resp)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    scraper._session = mock_session

    item = make_list_item()
    tech = await scraper._parse_api_item_with_detail(item)

    assert tech is not None
    assert "Key point 1" in tech.description


@pytest.mark.asyncio
async def test_parse_api_item_with_detail_raw_data_has_all_fields():
    scraper = TestFlintboxScraper()
    detail_resp = make_detail_response()

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=detail_resp)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    scraper._session = mock_session

    item = make_list_item()
    tech = await scraper._parse_api_item_with_detail(item)

    assert tech is not None
    rd = tech.raw_data
    assert rd["ip_status"] == "Filed"
    assert rd["ip_number"] == "IP-001"
    assert rd["abstract"] is not None
    assert rd["researchers"] is not None
    assert len(rd["researchers"]) == 2
    assert rd["documents"] is not None
    assert rd["contacts"] is not None
    assert rd["flintbox_tags"] == ["Machine Learning", "Healthcare"]


@pytest.mark.asyncio
async def test_parse_api_item_with_detail_no_members():
    """When no members exist, innovators should be None."""
    scraper = TestFlintboxScraper()
    detail_resp = make_detail_response(members=[], tags=[], documents=[], contacts=[])

    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=detail_resp)
    mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
    mock_resp.__aexit__ = AsyncMock(return_value=False)

    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=mock_resp)
    scraper._session = mock_session

    item = make_list_item()
    tech = await scraper._parse_api_item_with_detail(item)

    assert tech is not None
    assert tech.innovators is None
    assert tech.keywords is None
