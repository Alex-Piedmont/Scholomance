"""Integration-style tests with comprehensive mocking."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from src.scrapers.stanford import StanfordScraper
from src.scrapers.base import Technology


class TestStanfordScraperMocked:
    """Tests for Stanford scraper with mocked Playwright."""

    def test_scraper_name(self):
        """Test scraper name property."""
        scraper = StanfordScraper()
        assert scraper.name == "Stanford TechFinder"

    def test_scraper_base_url(self):
        """Test scraper base URL."""
        scraper = StanfordScraper()
        assert scraper.BASE_URL == "https://techfinder.stanford.edu"

    def test_scraper_technologies_url(self):
        """Test scraper technologies URL."""
        scraper = StanfordScraper()
        assert "/technology" in scraper.TECHNOLOGIES_URL

    def test_scraper_default_delay(self):
        """Test default delay setting."""
        scraper = StanfordScraper()
        assert scraper.delay_seconds == 1.0

    def test_scraper_custom_delay(self):
        """Test custom delay setting."""
        scraper = StanfordScraper(delay_seconds=2.5)
        assert scraper.delay_seconds == 2.5

    def test_scraper_initial_counts(self):
        """Test initial page and tech counts."""
        scraper = StanfordScraper()
        assert scraper._page_count == 0
        assert scraper._tech_count == 0

    @pytest.mark.asyncio
    async def test_init_browser_creates_browser(self):
        """Test browser initialization."""
        scraper = StanfordScraper()

        with patch("src.scrapers.stanford.async_playwright") as mock_playwright:
            mock_pw_instance = AsyncMock()
            mock_browser = AsyncMock()
            mock_page = AsyncMock()

            mock_playwright.return_value.start = AsyncMock(return_value=mock_pw_instance)
            mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_page = AsyncMock(return_value=mock_page)

            await scraper._init_browser()

            assert scraper._browser is not None

    @pytest.mark.asyncio
    async def test_close_browser(self):
        """Test browser closing."""
        scraper = StanfordScraper()
        mock_browser = AsyncMock()
        mock_page = AsyncMock()
        scraper._browser = mock_browser
        scraper._page = mock_page

        await scraper._close_browser()

        mock_page.close.assert_called_once()
        mock_browser.close.assert_called_once()
        assert scraper._browser is None
        assert scraper._page is None

    @pytest.mark.asyncio
    async def test_scrape_page_empty_result(self):
        """Test scrape_page returns empty when no cards found."""
        scraper = StanfordScraper()
        scraper._page = AsyncMock()
        scraper._page.goto = AsyncMock()
        scraper._page.wait_for_selector = AsyncMock()
        scraper._page.query_selector_all = AsyncMock(return_value=[])

        techs = await scraper.scrape_page(1)

        assert techs == []

    @pytest.mark.asyncio
    async def test_delay_respects_setting(self):
        """Test delay method respects delay_seconds setting."""
        scraper = StanfordScraper(delay_seconds=0.01)

        import time
        start = time.time()
        await scraper.delay()
        elapsed = time.time() - start

        assert elapsed >= 0.01

    @pytest.mark.asyncio
    async def test_delay_zero_returns_immediately(self):
        """Test delay with zero seconds returns immediately."""
        scraper = StanfordScraper(delay_seconds=0)

        import time
        start = time.time()
        await scraper.delay()
        elapsed = time.time() - start

        assert elapsed < 0.01


class TestStanfordScraperParsing:
    """Tests for Stanford scraper parsing logic."""

    @pytest.mark.asyncio
    async def test_scrape_page_returns_list(self):
        """Test that scrape_page returns a list."""
        scraper = StanfordScraper()
        scraper._page = AsyncMock()
        scraper._page.goto = AsyncMock()
        scraper._page.wait_for_selector = AsyncMock()
        scraper._page.query_selector_all = AsyncMock(return_value=[])

        # Sleep mock
        with patch("asyncio.sleep", new_callable=AsyncMock):
            techs = await scraper.scrape_page(1)

        assert isinstance(techs, list)

    def test_stats_property(self):
        """Test stats property returns correct structure."""
        scraper = StanfordScraper()
        scraper._page_count = 5
        scraper._tech_count = 75

        stats = scraper.stats

        assert stats["pages_scraped"] == 5
        assert stats["technologies_found"] == 75

    def test_log_progress_method_exists(self):
        """Test log_progress method exists and is callable."""
        scraper = StanfordScraper()
        assert hasattr(scraper, "log_progress")
        assert callable(scraper.log_progress)

    def test_log_error_method_exists(self):
        """Test log_error method exists and is callable."""
        scraper = StanfordScraper()
        assert hasattr(scraper, "log_error")
        assert callable(scraper.log_error)


class TestDatabaseOperationsMocked:
    """Tests for database operations with session mocking."""

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_search_with_all_filters(self, mock_sessionmaker, mock_create_engine):
        """Test search with all filter parameters."""
        from src.database import Database

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")

        results = db.search_technologies(
            keyword="robot",
            university="stanford",
            top_field="Robotics",
            subfield="Industrial Robotics",
            limit=50,
            offset=10,
        )

        assert results == []
        # Verify filter was called multiple times
        assert mock_query.filter.called

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_count_technologies_with_university(self, mock_sessionmaker, mock_create_engine):
        """Test count_technologies with university filter."""
        from src.database import Database

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 42
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")

        count = db.count_technologies(university="stanford")

        assert count == 42

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_count_technologies_no_filter(self, mock_sessionmaker, mock_create_engine):
        """Test count_technologies without filter."""
        from src.database import Database

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.scalar.return_value = 100
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")

        count = db.count_technologies()

        assert count == 100


class TestConfigSettings:
    """Tests for configuration settings."""

    def test_settings_import(self):
        """Test settings can be imported."""
        from src.config import settings
        assert settings is not None

    def test_settings_has_database_url_method(self):
        """Test settings has get_database_url method."""
        from src.config import Settings
        s = Settings()
        assert hasattr(s, "get_database_url")

    def test_settings_defaults(self):
        """Test settings have reasonable defaults."""
        from src.config import Settings
        s = Settings()

        assert s.postgres_port == 5432
        assert s.scrape_delay_seconds >= 0
        assert s.request_timeout > 0


class TestTechnologyDataClass:
    """Additional tests for Technology data class."""

    def test_technology_core_fields(self):
        """Test Technology objects have correct core fields."""
        from src.scrapers.base import Technology

        tech = Technology(
            university="stanford",
            tech_id="S21-001",
            title="Test",
            url="https://example.com",
        )

        assert tech.university == "stanford"
        assert tech.tech_id == "S21-001"
        assert tech.title == "Test"
        assert tech.url == "https://example.com"

    def test_technology_scraped_at_default(self):
        """Test Technology has scraped_at timestamp by default."""
        from src.scrapers.base import Technology

        tech = Technology(
            university="stanford",
            tech_id="S21-001",
            title="Test",
            url="https://example.com",
        )

        assert tech.scraped_at is not None
        assert isinstance(tech.scraped_at, datetime)

    def test_technology_raw_data_default(self):
        """Test Technology has empty dict as default raw_data."""
        from src.scrapers.base import Technology

        tech = Technology(
            university="stanford",
            tech_id="S21-001",
            title="Test",
            url="https://example.com",
        )

        assert tech.raw_data == {}
