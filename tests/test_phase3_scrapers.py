"""Tests for Phase 3 scrapers (Georgia Tech and UGA)."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.scrapers.gatech import GatechScraper
from src.scrapers.uga import UGAScraper
from src.scrapers import SCRAPERS, get_scraper, list_scrapers
from src.scrapers.registry import (
    UniversityConfig,
    UNIVERSITY_CONFIGS,
    get_university_config,
    get_enabled_universities,
    get_registry_info,
)


class TestGatechScraper:
    """Tests for Georgia Tech scraper."""

    def test_scraper_initialization(self):
        """Test Georgia Tech scraper can be initialized."""
        scraper = GatechScraper()
        assert scraper.university_code == "gatech"
        assert scraper.name == "Georgia Tech Flintbox"

    def test_scraper_urls(self):
        """Test Georgia Tech scraper URLs."""
        scraper = GatechScraper()
        assert "gatech.flintbox.com" in scraper.BASE_URL
        assert "gatech.flintbox.com" in scraper.API_URL

    def test_scraper_delay_configuration(self):
        """Test scraper delay can be configured."""
        scraper = GatechScraper(delay_seconds=2.0)
        assert scraper.delay_seconds == 2.0

    def test_scraper_stats_initialization(self):
        """Test scraper stats start at zero."""
        scraper = GatechScraper()
        stats = scraper.stats
        assert stats["pages_scraped"] == 0
        assert stats["technologies_found"] == 0

    @pytest.mark.asyncio
    async def test_delay_method(self):
        """Test the delay method works."""
        scraper = GatechScraper(delay_seconds=0.01)
        await scraper.delay()
        assert True

    @pytest.mark.asyncio
    async def test_close_session_when_none(self):
        """Test close_session handles None gracefully."""
        scraper = GatechScraper()
        scraper._session = None
        await scraper._close_session()
        assert scraper._session is None

    @pytest.mark.asyncio
    async def test_scrape_page_error_handling(self):
        """Test scrape_page handles errors gracefully."""
        scraper = GatechScraper()
        # Mock the session to raise an error
        mock_session = AsyncMock()
        mock_session.get = AsyncMock(side_effect=Exception("Network error"))
        scraper._session = mock_session

        techs = await scraper.scrape_page(1)
        assert techs == []

    def test_log_progress(self):
        """Test log_progress doesn't raise."""
        scraper = GatechScraper()
        scraper.log_progress("Test message")

    def test_log_error(self):
        """Test log_error doesn't raise."""
        scraper = GatechScraper()
        scraper.log_error("Test error", Exception("test"))


class TestUGAScraper:
    """Tests for UGA Flintbox scraper."""

    def test_scraper_initialization(self):
        """Test UGA scraper can be initialized."""
        scraper = UGAScraper()
        assert scraper.university_code == "uga"
        assert scraper.name == "UGA Flintbox"

    def test_scraper_urls(self):
        """Test UGA scraper URLs."""
        scraper = UGAScraper()
        assert "uga.flintbox.com" in scraper.BASE_URL
        assert "/technologies" in scraper.TECHNOLOGIES_URL

    def test_scraper_delay_configuration(self):
        """Test scraper delay can be configured."""
        scraper = UGAScraper(delay_seconds=2.5)
        assert scraper.delay_seconds == 2.5

    def test_scraper_default_delay_higher(self):
        """Test UGA scraper has higher default delay for React app."""
        scraper = UGAScraper()
        assert scraper.delay_seconds >= 1.0

    def test_api_data_initialized(self):
        """Test API data list is initialized."""
        scraper = UGAScraper()
        assert scraper._api_data == []

    @pytest.mark.asyncio
    async def test_close_browser_when_none(self):
        """Test close_browser handles None gracefully."""
        scraper = UGAScraper()
        scraper._browser = None
        scraper._page = None
        await scraper._close_browser()
        assert scraper._browser is None

    def test_parse_api_item_valid(self):
        """Test parsing valid API item."""
        scraper = UGAScraper()
        item = {
            "id": "123",
            "title": "Test Technology",
            "description": "A test description",
            "url": "https://uga.flintbox.com/technologies/123",
        }

        tech = scraper._parse_api_item(item)

        assert tech is not None
        assert tech.title == "Test Technology"
        assert tech.university == "uga"
        assert tech.tech_id == "123"

    def test_parse_api_item_minimal(self):
        """Test parsing API item with minimal data."""
        scraper = UGAScraper()
        item = {
            "title": "Minimal Tech",
        }

        tech = scraper._parse_api_item(item)

        assert tech is not None
        assert tech.title == "Minimal Tech"

    def test_parse_api_item_empty_title(self):
        """Test parsing API item with empty title returns None."""
        scraper = UGAScraper()
        item = {
            "id": "123",
            "title": "",
        }

        tech = scraper._parse_api_item(item)
        assert tech is None

    def test_parse_api_item_with_html_description(self):
        """Test parsing API item strips HTML from description."""
        scraper = UGAScraper()
        item = {
            "title": "Test",
            "description": "<p>This is a <strong>test</strong></p>",
        }

        tech = scraper._parse_api_item(item)

        assert tech is not None
        assert "<" not in tech.description
        assert ">" not in tech.description

    def test_parse_api_item_keywords_string(self):
        """Test parsing API item with keywords as string."""
        scraper = UGAScraper()
        item = {
            "title": "Test",
            "keywords": "keyword1, keyword2, keyword3",
        }

        tech = scraper._parse_api_item(item)

        assert tech is not None
        assert tech.keywords is not None
        assert len(tech.keywords) == 3

    def test_parse_api_item_keywords_list(self):
        """Test parsing API item with keywords as list."""
        scraper = UGAScraper()
        item = {
            "title": "Test",
            "keywords": ["keyword1", "keyword2"],
        }

        tech = scraper._parse_api_item(item)

        assert tech is not None
        assert tech.keywords == ["keyword1", "keyword2"]


class TestScraperRegistry:
    """Tests for scraper registry."""

    def test_all_scrapers_registered(self):
        """Test all three scrapers are registered."""
        assert "stanford" in SCRAPERS
        assert "gatech" in SCRAPERS
        assert "uga" in SCRAPERS

    def test_get_scraper_stanford(self):
        """Test getting Stanford scraper."""
        scraper = get_scraper("stanford")
        assert scraper.university_code == "stanford"

    def test_get_scraper_gatech(self):
        """Test getting Georgia Tech scraper."""
        scraper = get_scraper("gatech")
        assert scraper.university_code == "gatech"

    def test_get_scraper_uga(self):
        """Test getting UGA scraper."""
        scraper = get_scraper("uga")
        assert scraper.university_code == "uga"

    def test_get_scraper_unknown(self):
        """Test getting unknown scraper raises error."""
        with pytest.raises(ValueError) as exc_info:
            get_scraper("unknown")
        assert "Unknown university" in str(exc_info.value)

    def test_list_scrapers(self):
        """Test listing all scrapers."""
        scrapers = list_scrapers()

        assert len(scrapers) >= 3
        codes = [s["code"] for s in scrapers]
        assert "stanford" in codes
        assert "gatech" in codes
        assert "uga" in codes

    def test_list_scrapers_has_required_fields(self):
        """Test list_scrapers returns required fields."""
        scrapers = list_scrapers()

        for scraper in scrapers:
            assert "code" in scraper
            assert "name" in scraper
            assert "base_url" in scraper


class TestUniversityConfig:
    """Tests for university configuration."""

    def test_university_config_creation(self):
        """Test creating UniversityConfig."""
        config = UniversityConfig(
            code="test",
            name="Test University",
            base_url="https://test.edu",
            scraper_class="TestScraper",
        )

        assert config.code == "test"
        assert config.name == "Test University"
        assert config.enabled is True  # Default

    def test_get_university_config_stanford(self):
        """Test getting Stanford config."""
        config = get_university_config("stanford")

        assert config is not None
        assert config.code == "stanford"
        assert config.name == "Stanford University"

    def test_get_university_config_gatech(self):
        """Test getting Georgia Tech config."""
        config = get_university_config("gatech")

        assert config is not None
        assert config.code == "gatech"

    def test_get_university_config_uga(self):
        """Test getting UGA config."""
        config = get_university_config("uga")

        assert config is not None
        assert config.code == "uga"

    def test_get_university_config_unknown(self):
        """Test getting unknown config returns None."""
        config = get_university_config("unknown")
        assert config is None

    def test_get_enabled_universities(self):
        """Test getting enabled universities."""
        enabled = get_enabled_universities()

        assert len(enabled) >= 3
        for config in enabled:
            assert config.enabled is True

    def test_get_registry_info(self):
        """Test getting registry info."""
        info = get_registry_info()

        assert "total_universities" in info
        assert "enabled_universities" in info
        assert "universities" in info
        assert info["total_universities"] >= 3


class TestAllScrapersInterface:
    """Tests to verify all scrapers implement the same interface."""

    @pytest.mark.parametrize("university_code", ["stanford", "gatech", "uga"])
    def test_scraper_has_name(self, university_code):
        """Test all scrapers have name property."""
        scraper = get_scraper(university_code)
        assert hasattr(scraper, "name")
        assert isinstance(scraper.name, str)
        assert len(scraper.name) > 0

    @pytest.mark.parametrize("university_code", ["stanford", "gatech", "uga"])
    def test_scraper_has_base_url(self, university_code):
        """Test all scrapers have base_url."""
        scraper = get_scraper(university_code)
        assert hasattr(scraper, "base_url")
        assert scraper.base_url.startswith("http")

    @pytest.mark.parametrize("university_code", ["stanford", "gatech", "uga"])
    def test_scraper_has_scrape_method(self, university_code):
        """Test all scrapers have scrape method."""
        scraper = get_scraper(university_code)
        assert hasattr(scraper, "scrape")
        assert callable(scraper.scrape)

    @pytest.mark.parametrize("university_code", ["stanford", "gatech", "uga"])
    def test_scraper_has_scrape_page_method(self, university_code):
        """Test all scrapers have scrape_page method."""
        scraper = get_scraper(university_code)
        assert hasattr(scraper, "scrape_page")
        assert callable(scraper.scrape_page)

    @pytest.mark.parametrize("university_code", ["stanford", "gatech", "uga"])
    def test_scraper_has_stats(self, university_code):
        """Test all scrapers have stats property."""
        scraper = get_scraper(university_code)
        stats = scraper.stats
        assert "pages_scraped" in stats
        assert "technologies_found" in stats
