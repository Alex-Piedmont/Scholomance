"""Additional tests to boost code coverage."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone


class TestDatabaseSearchOperations:
    """Tests for database search operations."""

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_search_keyword_only(self, mock_sessionmaker, mock_create_engine):
        """Test search with only keyword filter."""
        from src.database import Database, Technology

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
        results = db.search_technologies(keyword="robot")

        assert isinstance(results, list)

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_get_technology_by_id(self, mock_sessionmaker, mock_create_engine):
        """Test getting technology by ID."""
        from src.database import Database

        mock_tech = MagicMock()
        mock_tech.id = 1

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_tech
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")
        result = db.get_technology_by_id(1)

        assert result.id == 1

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_get_technology_by_tech_id(self, mock_sessionmaker, mock_create_engine):
        """Test getting technology by university and tech_id."""
        from src.database import Database

        mock_tech = MagicMock()
        mock_tech.tech_id = "S21-001"

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_tech
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")
        result = db.get_technology_by_tech_id("stanford", "S21-001")

        assert result.tech_id == "S21-001"


class TestDatabaseClassificationOps:
    """Tests for classification database operations."""

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_get_unclassified_technologies(self, mock_sessionmaker, mock_create_engine):
        """Test getting unclassified technologies."""
        from src.database import Database

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")
        results = db.get_unclassified_technologies(limit=50)

        assert isinstance(results, list)

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_count_unclassified(self, mock_sessionmaker, mock_create_engine):
        """Test counting unclassified technologies."""
        from src.database import Database

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 25
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")
        count = db.count_unclassified()

        assert count == 25

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_count_classified(self, mock_sessionmaker, mock_create_engine):
        """Test counting classified technologies."""
        from src.database import Database

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.scalar.return_value = 75
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")
        count = db.count_classified()

        assert count == 75


class TestStanfordScraperExtended:
    """Extended tests for Stanford scraper."""

    @pytest.mark.asyncio
    async def test_get_total_pages_default(self):
        """Test _get_total_pages returns default when can't determine."""
        from src.scrapers.stanford import StanfordScraper

        scraper = StanfordScraper()
        scraper._page = AsyncMock()
        scraper._page.goto = AsyncMock()
        scraper._page.wait_for_selector = AsyncMock(side_effect=Exception("timeout"))
        scraper._page.query_selector_all = AsyncMock(return_value=[])

        # Should return default (100) on error
        pages = await scraper._get_total_pages()
        assert pages == 100

    @pytest.mark.asyncio
    async def test_scrape_page_handles_error(self):
        """Test scrape_page handles errors gracefully."""
        from src.scrapers.stanford import StanfordScraper

        scraper = StanfordScraper()
        scraper._page = AsyncMock()
        scraper._page.goto = AsyncMock(side_effect=Exception("Network error"))

        techs = await scraper.scrape_page(1)

        assert techs == []

    def test_log_progress(self):
        """Test log_progress doesn't raise."""
        from src.scrapers.stanford import StanfordScraper

        scraper = StanfordScraper()
        # Should not raise
        scraper.log_progress("Test message")

    def test_log_error_without_exception(self):
        """Test log_error without exception."""
        from src.scrapers.stanford import StanfordScraper

        scraper = StanfordScraper()
        # Should not raise
        scraper.log_error("Test error")

    def test_log_error_with_exception(self):
        """Test log_error with exception."""
        from src.scrapers.stanford import StanfordScraper

        scraper = StanfordScraper()
        # Should not raise
        scraper.log_error("Test error", Exception("test"))


class TestClassifierExtended:
    """Extended tests for classifier."""

    @patch("src.classifier.Anthropic")
    def test_classify_parse_error(self, mock_anthropic):
        """Test classify handles parse errors."""
        from src.classifier import Classifier, ClassificationError

        mock_response = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.content = [MagicMock(text="not json at all {{{")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        classifier = Classifier(api_key="test-key")
        result = classifier.classify("Test", "Test description")

        assert isinstance(result, ClassificationError)
        assert result.error_type == "parse_error"

    @patch("src.classifier.Anthropic")
    def test_min_request_interval(self, mock_anthropic):
        """Test minimum request interval is set."""
        from src.classifier import Classifier

        classifier = Classifier(api_key="test-key")
        assert classifier._min_request_interval > 0

    @patch("src.classifier.Anthropic")
    def test_last_request_time_initialized(self, mock_anthropic):
        """Test last request time is initialized."""
        from src.classifier import Classifier

        classifier = Classifier(api_key="test-key")
        assert classifier._last_request_time == 0.0


class TestCLIExtended:
    """Extended CLI tests."""

    def test_setup_logging_verbose(self):
        """Test setup_logging with verbose mode."""
        from src.cli import setup_logging

        # Should not raise
        setup_logging(verbose=True)

    def test_setup_logging_normal(self):
        """Test setup_logging with normal mode."""
        from src.cli import setup_logging

        # Should not raise
        setup_logging(verbose=False)


class TestBaseScraperExtended:
    """Extended base scraper tests."""

    def test_base_scraper_log_progress(self):
        """Test base scraper log_progress method."""
        from src.scrapers.stanford import StanfordScraper

        scraper = StanfordScraper()
        # Should execute without error
        scraper.log_progress("Testing progress")

    def test_base_scraper_log_error_no_exception(self):
        """Test base scraper log_error without exception."""
        from src.scrapers.stanford import StanfordScraper

        scraper = StanfordScraper()
        # Should execute without error
        scraper.log_error("Testing error")

    def test_base_scraper_log_error_with_exception(self):
        """Test base scraper log_error with exception."""
        from src.scrapers.stanford import StanfordScraper

        scraper = StanfordScraper()
        # Should execute without error
        scraper.log_error("Testing error", ValueError("test"))


class TestDatabaseUniversityOps:
    """Tests for university database operations."""

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_get_universities(self, mock_sessionmaker, mock_create_engine):
        """Test getting all universities."""
        from src.database import Database

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.all.return_value = []
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")
        results = db.get_universities()

        assert isinstance(results, list)

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_get_university(self, mock_sessionmaker, mock_create_engine):
        """Test getting a university by code."""
        from src.database import Database

        mock_uni = MagicMock()
        mock_uni.code = "stanford"

        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = mock_uni
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")
        result = db.get_university("stanford")

        assert result.code == "stanford"


class TestDatabaseClassificationStats:
    """Tests for classification stats."""

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_get_classification_stats(self, mock_sessionmaker, mock_create_engine):
        """Test getting classification statistics."""
        from src.database import Database

        mock_session = MagicMock()
        mock_session.query.return_value.scalar.return_value = 0.5
        mock_session.query.return_value.filter.return_value.group_by.return_value.all.return_value = []
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")
        stats = db.get_classification_stats()

        assert "total_cost" in stats
        assert "total_classifications" in stats


class TestStanfordScraperInit:
    """Tests for Stanford scraper initialization."""

    @pytest.mark.asyncio
    async def test_init_browser_sets_viewport(self):
        """Test browser init sets viewport."""
        from src.scrapers.stanford import StanfordScraper

        scraper = StanfordScraper()

        with patch("src.scrapers.stanford.async_playwright") as mock_pw:
            mock_instance = AsyncMock()
            mock_browser = AsyncMock()
            mock_page = AsyncMock()

            mock_pw.return_value.start = AsyncMock(return_value=mock_instance)
            mock_instance.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_browser.new_page = AsyncMock(return_value=mock_page)

            await scraper._init_browser()

            mock_page.set_viewport_size.assert_called_once()


class TestConfigGetDatabaseUrl:
    """Tests for config get_database_url method."""

    def test_get_database_url_from_url(self):
        """Test get_database_url returns configured URL."""
        from src.config import Settings

        s = Settings()
        s.database_url = "postgresql://user:pass@host:5432/db"

        url = s.get_database_url()
        assert "postgresql://" in url

    def test_get_database_url_builds_from_components(self):
        """Test get_database_url builds URL from components."""
        from src.config import Settings

        s = Settings()
        s.database_url = ""
        s.postgres_user = "testuser"
        s.postgres_password = "testpass"
        s.postgres_host = "localhost"
        s.postgres_port = 5432
        s.postgres_db = "testdb"

        url = s.get_database_url()
        assert "testuser" in url
        assert "localhost" in url
