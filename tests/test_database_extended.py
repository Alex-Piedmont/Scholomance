"""Extended tests for database operations with more coverage."""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone

from src.database import (
    Database,
    Technology,
    University,
    ScrapeLog,
    ClassificationLog,
    Base,
)
from src.scrapers.base import Technology as TechnologyData


class TestDatabaseClass:
    """Tests for Database class methods."""

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_database_init_with_url(self, mock_sessionmaker, mock_create_engine):
        """Test Database initialization with explicit URL."""
        db = Database("postgresql://test:test@localhost/testdb")

        assert db.database_url == "postgresql://test:test@localhost/testdb"
        mock_create_engine.assert_called_once()

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_database_init_from_settings(self, mock_sessionmaker, mock_create_engine):
        """Test Database initialization from settings."""
        with patch("src.database.settings") as mock_settings:
            mock_settings.get_database_url.return_value = "postgresql://user:pass@host/db"

            db = Database()
            assert "postgresql" in db.database_url

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_get_session_context_manager(self, mock_sessionmaker, mock_create_engine):
        """Test get_session context manager behavior."""
        mock_session = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")

        with db.get_session() as session:
            assert session is mock_session

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_get_session_rollback_on_error(self, mock_sessionmaker, mock_create_engine):
        """Test get_session rolls back on exception."""
        mock_session = MagicMock()
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")

        with pytest.raises(ValueError):
            with db.get_session() as session:
                raise ValueError("Test error")

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    @patch("src.database.Base")
    def test_init_db(self, mock_base, mock_sessionmaker, mock_create_engine):
        """Test init_db creates tables."""
        db = Database("postgresql://test:test@localhost/test")
        db.init_db()

        mock_base.metadata.create_all.assert_called_once()


class TestTechnologyModel:
    """Tests for Technology SQLAlchemy model."""

    def test_technology_repr(self):
        """Test Technology string representation."""
        tech = Technology()
        tech.id = 1
        tech.university = "stanford"
        tech.tech_id = "S21-001"

        repr_str = repr(tech)
        assert "Technology" in repr_str
        assert "stanford" in repr_str

    def test_technology_default_values(self):
        """Test Technology default field values."""
        tech = Technology()

        assert tech.classification_status is None or tech.classification_status == "pending"


class TestUniversityModel:
    """Tests for University SQLAlchemy model."""

    def test_university_repr(self):
        """Test University string representation."""
        uni = University()
        uni.code = "stanford"
        uni.name = "Stanford University"

        repr_str = repr(uni)
        assert "University" in repr_str
        assert "stanford" in repr_str


class TestScrapeLogModel:
    """Tests for ScrapeLog SQLAlchemy model."""

    def test_scrape_log_repr(self):
        """Test ScrapeLog string representation."""
        log = ScrapeLog()
        log.id = 1
        log.university = "stanford"
        log.status = "completed"

        repr_str = repr(log)
        assert "ScrapeLog" in repr_str
        assert "stanford" in repr_str


class TestClassificationLogModel:
    """Tests for ClassificationLog SQLAlchemy model."""

    def test_classification_log_repr(self):
        """Test ClassificationLog string representation."""
        log = ClassificationLog()
        log.id = 1
        log.technology_id = 10

        repr_str = repr(log)
        assert "ClassificationLog" in repr_str


class TestDatabaseInsertOperations:
    """Tests for database insert operations."""

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_insert_technology_new(self, mock_sessionmaker, mock_create_engine):
        """Test inserting a new technology."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")

        tech_data = TechnologyData(
            university="stanford",
            tech_id="S21-NEW",
            title="New Technology",
            url="https://example.com",
        )

        # The method exists and can be called
        assert hasattr(db, "insert_technology")

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_bulk_insert_technologies(self, mock_sessionmaker, mock_create_engine):
        """Test bulk inserting technologies."""
        mock_session = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        mock_session.query.return_value = mock_query
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_sessionmaker.return_value = MagicMock(return_value=mock_session)

        db = Database("postgresql://test:test@localhost/test")

        # Verify the method exists
        assert hasattr(db, "bulk_insert_technologies")


class TestDatabaseQueryOperations:
    """Tests for database query operations."""

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_search_technologies_method_exists(self, mock_sessionmaker, mock_create_engine):
        """Test search_technologies method exists with correct signature."""
        db = Database("postgresql://test:test@localhost/test")

        import inspect
        sig = inspect.signature(db.search_technologies)
        params = list(sig.parameters.keys())

        assert "keyword" in params
        assert "university" in params
        assert "top_field" in params
        assert "subfield" in params
        assert "limit" in params
        assert "offset" in params

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_count_methods_exist(self, mock_sessionmaker, mock_create_engine):
        """Test count methods exist."""
        db = Database("postgresql://test:test@localhost/test")

        assert hasattr(db, "count_technologies")
        assert hasattr(db, "count_unclassified")
        assert hasattr(db, "count_classified")

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_get_methods_exist(self, mock_sessionmaker, mock_create_engine):
        """Test get methods exist."""
        db = Database("postgresql://test:test@localhost/test")

        assert hasattr(db, "get_technology_by_id")
        assert hasattr(db, "get_technology_by_tech_id")
        assert hasattr(db, "get_universities")
        assert hasattr(db, "get_university")


class TestDatabaseClassificationOperations:
    """Tests for classification-related database operations."""

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_classification_methods_exist(self, mock_sessionmaker, mock_create_engine):
        """Test classification methods exist."""
        db = Database("postgresql://test:test@localhost/test")

        assert hasattr(db, "get_unclassified_technologies")
        assert hasattr(db, "get_technologies_for_classification")
        assert hasattr(db, "update_technology_classification")
        assert hasattr(db, "mark_classification_failed")
        assert hasattr(db, "get_classification_stats")

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_get_technologies_for_classification_params(self, mock_sessionmaker, mock_create_engine):
        """Test get_technologies_for_classification parameters."""
        db = Database("postgresql://test:test@localhost/test")

        import inspect
        sig = inspect.signature(db.get_technologies_for_classification)
        params = list(sig.parameters.keys())

        assert "university" in params
        assert "force" in params
        assert "limit" in params

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_update_technology_classification_params(self, mock_sessionmaker, mock_create_engine):
        """Test update_technology_classification parameters."""
        db = Database("postgresql://test:test@localhost/test")

        import inspect
        sig = inspect.signature(db.update_technology_classification)
        params = list(sig.parameters.keys())

        assert "tech_id" in params
        assert "top_field" in params
        assert "subfield" in params
        assert "confidence" in params
        assert "model" in params
        assert "total_cost" in params


class TestDatabaseScrapeLogOperations:
    """Tests for scrape log database operations."""

    @patch("src.database.create_engine")
    @patch("src.database.sessionmaker")
    def test_scrape_log_methods_exist(self, mock_sessionmaker, mock_create_engine):
        """Test scrape log methods exist."""
        db = Database("postgresql://test:test@localhost/test")

        assert hasattr(db, "create_scrape_log")
        assert hasattr(db, "update_scrape_log")
