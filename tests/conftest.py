"""Pytest configuration and fixtures."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock

from src.scrapers.base import Technology


@pytest.fixture
def sample_technology():
    """Create a sample Technology object for testing."""
    return Technology(
        university="stanford",
        tech_id="S21-123",
        title="Novel Machine Learning Algorithm for Medical Imaging",
        url="https://techfinder.stanford.edu/technologies/S21-123",
        description="A breakthrough machine learning algorithm that improves diagnostic accuracy in medical imaging by 40%.",
        keywords=["machine learning", "medical imaging", "diagnostics"],
        innovators=["Dr. Jane Smith", "Dr. John Doe"],
        raw_data={
            "title": "Novel Machine Learning Algorithm for Medical Imaging",
            "description": "A breakthrough machine learning algorithm...",
            "keywords": ["machine learning", "medical imaging"],
        },
        scraped_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_technologies():
    """Create multiple sample Technology objects for testing."""
    return [
        Technology(
            university="stanford",
            tech_id="S21-001",
            title="Robotics Control System",
            url="https://techfinder.stanford.edu/technologies/S21-001",
            description="Advanced robotics control system for industrial applications.",
            keywords=["robotics", "automation"],
        ),
        Technology(
            university="stanford",
            tech_id="S21-002",
            title="Solar Cell Efficiency Improvement",
            url="https://techfinder.stanford.edu/technologies/S21-002",
            description="Novel approach to improving solar cell efficiency.",
            keywords=["solar", "energy", "renewable"],
        ),
        Technology(
            university="stanford",
            tech_id="S21-003",
            title="Drug Delivery Nanoparticles",
            url="https://techfinder.stanford.edu/technologies/S21-003",
            description="Targeted drug delivery using engineered nanoparticles.",
            keywords=["pharmaceuticals", "nanotechnology", "drug delivery"],
        ),
    ]


@pytest.fixture
def mock_browser():
    """Create a mock Playwright browser."""
    mock = MagicMock()
    mock.close = AsyncMock()
    return mock


@pytest.fixture
def mock_page():
    """Create a mock Playwright page."""
    mock = MagicMock()
    mock.goto = AsyncMock()
    mock.wait_for_selector = AsyncMock()
    mock.query_selector = AsyncMock()
    mock.query_selector_all = AsyncMock(return_value=[])
    mock.close = AsyncMock()
    mock.set_viewport_size = AsyncMock()
    mock.url = "https://techfinder.stanford.edu/technologies"
    return mock
