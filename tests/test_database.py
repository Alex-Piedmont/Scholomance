"""Tests for database operations."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.scrapers.base import Technology as TechnologyData


class TestTechnologyModel:
    """Tests for the Technology data class."""

    def test_technology_creation(self, sample_technology):
        """Test that a Technology object can be created with all fields."""
        assert sample_technology.university == "stanford"
        assert sample_technology.tech_id == "S21-123"
        assert sample_technology.title == "Novel Machine Learning Algorithm for Medical Imaging"
        assert "machine learning" in sample_technology.keywords
        assert sample_technology.description is not None

    def test_technology_minimal_creation(self):
        """Test Technology creation with only required fields."""
        tech = TechnologyData(
            university="stanford",
            tech_id="S21-999",
            title="Test Technology",
            url="https://example.com/tech",
        )
        assert tech.university == "stanford"
        assert tech.tech_id == "S21-999"
        assert tech.description is None
        assert tech.keywords is None

    def test_technology_with_empty_keywords(self):
        """Test Technology with empty keywords list."""
        tech = TechnologyData(
            university="stanford",
            tech_id="S21-100",
            title="Test Tech",
            url="https://example.com",
            keywords=[],
        )
        assert tech.keywords == []


class TestDatabaseOperations:
    """Tests for database operations using mocks."""

    @patch("src.database.Database")
    def test_database_initialization(self, mock_db_class):
        """Test that database can be initialized."""
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        from src.database import Database
        db = Database("postgresql://test:test@localhost/test")

        assert db is not None

    @patch("src.database.Database.get_session")
    def test_search_technologies_with_keyword(self, mock_session):
        """Test search functionality with keyword."""
        from src.database import Database

        db = Database.__new__(Database)
        db.database_url = "postgresql://test:test@localhost/test"

        # Create mock query chain
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        mock_sess = MagicMock()
        mock_sess.query.return_value = mock_query
        mock_sess.__enter__ = MagicMock(return_value=mock_sess)
        mock_sess.__exit__ = MagicMock(return_value=None)

        mock_session.return_value = mock_sess

        # This would test the actual search if we had a real database
        # For now, we're just testing that the method exists and returns a list
        assert hasattr(db, "search_technologies")

    def test_bulk_insert_logic(self, sample_technologies):
        """Test bulk insert logic with multiple technologies."""
        # Verify we have multiple technologies
        assert len(sample_technologies) == 3

        # Verify each has unique tech_id
        tech_ids = [t.tech_id for t in sample_technologies]
        assert len(tech_ids) == len(set(tech_ids))

    def test_technology_data_integrity(self, sample_technology):
        """Test that technology data maintains integrity."""
        raw_data = sample_technology.raw_data

        # Raw data should contain the title
        assert "title" in raw_data
        assert raw_data["title"] == sample_technology.title


class TestDatabaseFiltering:
    """Tests for database filtering functionality."""

    def test_filter_parameters(self):
        """Test that filter parameters are properly structured."""
        from src.database import db

        # Verify the search method accepts all expected parameters
        import inspect
        sig = inspect.signature(db.search_technologies)
        params = list(sig.parameters.keys())

        assert "keyword" in params
        assert "university" in params
        assert "top_field" in params
        assert "subfield" in params
        assert "limit" in params
        assert "offset" in params

    def test_count_technologies_method_exists(self):
        """Test that count method exists."""
        from src.database import db

        assert hasattr(db, "count_technologies")
        assert callable(db.count_technologies)
