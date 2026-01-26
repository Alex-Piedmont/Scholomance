"""Tests for scrapers."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio

from src.scrapers.base import BaseScraper, Technology
from src.scrapers.stanford import StanfordScraper
from src.scrapers import SCRAPERS, get_scraper


class TestBaseScraper:
    """Tests for the BaseScraper abstract class."""

    def test_technology_dataclass(self):
        """Test Technology dataclass creation."""
        tech = Technology(
            university="test",
            tech_id="T-001",
            title="Test Technology",
            url="https://example.com",
        )
        assert tech.university == "test"
        assert tech.tech_id == "T-001"
        assert tech.title == "Test Technology"
        assert tech.url == "https://example.com"
        assert tech.description is None
        assert tech.raw_data == {}

    def test_technology_with_all_fields(self, sample_technology):
        """Test Technology with all fields populated."""
        assert sample_technology.university == "stanford"
        assert sample_technology.keywords is not None
        assert len(sample_technology.keywords) > 0
        assert sample_technology.raw_data is not None


class TestStanfordScraper:
    """Tests for the Stanford scraper."""

    def test_scraper_initialization(self):
        """Test Stanford scraper can be initialized."""
        scraper = StanfordScraper()
        assert scraper.university_code == "stanford"
        assert scraper.name == "Stanford TechFinder"
        assert "techfinder.stanford.edu" in scraper.base_url

    def test_scraper_urls(self):
        """Test Stanford scraper URLs are correct."""
        scraper = StanfordScraper()
        assert scraper.BASE_URL == "https://techfinder.stanford.edu"
        assert "/technology" in scraper.TECHNOLOGIES_URL

    def test_scraper_delay_configuration(self):
        """Test scraper delay can be configured."""
        scraper = StanfordScraper(delay_seconds=2.0)
        assert scraper.delay_seconds == 2.0

    def test_scraper_stats_initialization(self):
        """Test scraper stats start at zero."""
        scraper = StanfordScraper()
        stats = scraper.stats
        assert stats["pages_scraped"] == 0
        assert stats["technologies_found"] == 0

    @pytest.mark.asyncio
    async def test_delay_method(self):
        """Test the delay method works."""
        scraper = StanfordScraper(delay_seconds=0.01)  # Short delay for testing
        await scraper.delay()
        # If we get here, delay worked
        assert True

    @pytest.mark.asyncio
    async def test_scraper_with_mock_browser(self, mock_browser, mock_page):
        """Test scraper with mocked browser."""
        scraper = StanfordScraper()

        # Mock the browser initialization
        scraper._browser = mock_browser
        scraper._page = mock_page

        # Mock query_selector_all to return empty list
        mock_page.query_selector_all.return_value = []

        # Test scrape_page with mocked page
        technologies = await scraper.scrape_page(1)

        # Should return empty list when no cards found
        assert isinstance(technologies, list)


class TestScraperRegistry:
    """Tests for the scraper registry."""

    def test_scrapers_registry_exists(self):
        """Test that SCRAPERS registry exists and has entries."""
        assert SCRAPERS is not None
        assert isinstance(SCRAPERS, dict)
        assert "stanford" in SCRAPERS

    def test_get_scraper_stanford(self):
        """Test getting Stanford scraper."""
        scraper = get_scraper("stanford")
        assert isinstance(scraper, StanfordScraper)

    def test_get_scraper_unknown(self):
        """Test getting unknown scraper raises error."""
        with pytest.raises(ValueError) as exc_info:
            get_scraper("unknown_university")
        assert "Unknown university" in str(exc_info.value)

    def test_all_registered_scrapers_instantiate(self):
        """Test that all registered scrapers can be instantiated."""
        for code, scraper_class in SCRAPERS.items():
            scraper = scraper_class()
            assert isinstance(scraper, BaseScraper)
            assert scraper.university_code == code


class TestTechnologyParsing:
    """Tests for technology parsing logic."""

    def test_technology_url_parsing(self):
        """Test that URLs are properly formed."""
        tech = Technology(
            university="stanford",
            tech_id="S21-123",
            title="Test",
            url="https://techfinder.stanford.edu/technologies/S21-123",
        )
        assert "techfinder.stanford.edu" in tech.url
        assert tech.tech_id in tech.url

    def test_technology_raw_data_storage(self):
        """Test that raw data is properly stored."""
        raw_data = {
            "original_title": "Original Title",
            "extra_field": "Extra Value",
            "nested": {"key": "value"},
        }
        tech = Technology(
            university="stanford",
            tech_id="S21-100",
            title="Test",
            url="https://example.com",
            raw_data=raw_data,
        )
        assert tech.raw_data == raw_data
        assert tech.raw_data["nested"]["key"] == "value"
