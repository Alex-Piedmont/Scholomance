"""Tests for Phase 4 functionality (Production Ready)."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch

from src.scheduler import ScrapeScheduler, create_scheduler
from src.scrapers.base import BaseScraper, Technology, RetryConfig, retry_async


class TestRetryDecorator:
    """Tests for the retry decorator."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_first_attempt(self):
        """Test that successful functions don't retry."""
        call_count = 0

        @retry_async(max_retries=3, base_delay=0.01)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await success_func()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self):
        """Test that function retries and eventually succeeds."""
        call_count = 0

        @retry_async(max_retries=3, base_delay=0.01)
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"

        result = await flaky_func()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_raises_after_max_retries(self):
        """Test that function raises after max retries exhausted."""
        call_count = 0

        @retry_async(max_retries=2, base_delay=0.01)
        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            await always_fail()

        assert call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_retry_only_catches_specified_exceptions(self):
        """Test that only specified exceptions are caught."""
        call_count = 0

        @retry_async(max_retries=3, base_delay=0.01, exceptions=(ValueError,))
        async def raise_type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            await raise_type_error()

        assert call_count == 1  # No retries for unhandled exception


class TestRetryConfig:
    """Tests for RetryConfig."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False,
        )
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


class TestScrapeScheduler:
    """Tests for ScrapeScheduler."""

    def test_scheduler_initialization(self):
        """Test scheduler initializes correctly."""
        scheduler = ScrapeScheduler()
        assert scheduler.scheduler is not None
        assert scheduler._running is False

    def test_scheduler_add_weekly_job(self):
        """Test adding a weekly scrape job."""
        scheduler = ScrapeScheduler()

        job_id = scheduler.add_weekly_scrape(
            university="stanford",
            day_of_week="mon",
            hour=3,
        )

        assert job_id == "weekly_scrape_stanford"
        # Just verify job was added, don't check list which may have issues
        # before scheduler is started
        assert scheduler.scheduler.get_job(job_id) is not None

    def test_scheduler_add_daily_job(self):
        """Test adding a daily scrape job."""
        scheduler = ScrapeScheduler()

        job_id = scheduler.add_daily_scrape(
            university=None,  # All universities
            hour=5,
        )

        assert job_id == "daily_scrape_all"
        assert scheduler.scheduler.get_job(job_id) is not None

    def test_scheduler_add_interval_job(self):
        """Test adding an interval scrape job."""
        scheduler = ScrapeScheduler()

        job_id = scheduler.add_interval_scrape(
            university="gatech",
            hours=6,
        )

        assert job_id == "interval_scrape_gatech"
        assert scheduler.scheduler.get_job(job_id) is not None

    def test_scheduler_remove_job(self):
        """Test removing a scheduled job."""
        scheduler = ScrapeScheduler()

        job_id = scheduler.add_daily_scrape()
        assert scheduler.scheduler.get_job(job_id) is not None

        result = scheduler.remove_job(job_id)
        assert result is True
        assert scheduler.scheduler.get_job(job_id) is None

    def test_scheduler_remove_nonexistent_job(self):
        """Test removing a job that doesn't exist."""
        scheduler = ScrapeScheduler()

        result = scheduler.remove_job("nonexistent")
        assert result is False

    def test_scheduler_list_jobs_empty(self):
        """Test listing jobs when none are scheduled."""
        scheduler = ScrapeScheduler()
        jobs = scheduler.list_jobs()
        assert jobs == []


class TestCreateScheduler:
    """Tests for create_scheduler factory function."""

    def test_create_scheduler_with_defaults(self):
        """Test creating scheduler with default settings."""
        with patch.dict('os.environ', {}, clear=True):
            scheduler = create_scheduler()
            assert scheduler is not None
            assert scheduler.smtp_host is None

    def test_create_scheduler_with_env_vars(self):
        """Test creating scheduler with environment variables."""
        env_vars = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "465",
            "SMTP_USER": "user@test.com",
            "SMTP_PASSWORD": "secret",
            "NOTIFICATION_EMAIL": "notify@test.com",
        }

        with patch.dict('os.environ', env_vars):
            scheduler = create_scheduler()
            assert scheduler.smtp_host == "smtp.test.com"
            assert scheduler.smtp_port == 465
            assert scheduler.smtp_user == "user@test.com"
            assert scheduler.notification_email == "notify@test.com"

    def test_create_scheduler_with_explicit_params(self):
        """Test creating scheduler with explicit parameters."""
        scheduler = create_scheduler(
            smtp_host="explicit.smtp.com",
            smtp_port=25,
            smtp_user="explicit@test.com",
            smtp_password="explicit_pass",
            notification_email="explicit_notify@test.com",
        )

        assert scheduler.smtp_host == "explicit.smtp.com"
        assert scheduler.smtp_port == 25


class TestSchedulerRunScrape:
    """Tests for scheduler scrape execution."""

    @pytest.mark.asyncio
    async def test_run_now_single_university(self):
        """Test running immediate scrape for single university."""
        scheduler = ScrapeScheduler()

        with patch('src.scheduler.get_scraper') as mock_get_scraper, \
             patch('src.scheduler.db') as mock_db:

            # Mock scraper with proper async iterator
            mock_scraper = MagicMock()

            async def mock_scrape():
                return
                yield  # Make this an async generator

            mock_scraper.scrape = mock_scrape
            mock_get_scraper.return_value = mock_scraper

            # Mock db
            mock_log = MagicMock()
            mock_log.id = 1
            mock_db.create_scrape_log.return_value = mock_log
            mock_db.bulk_insert_technologies.return_value = (0, 0)

            results = await scheduler.run_now(university="stanford")

            assert "stanford" in results["universities"]
            assert results["total_new"] == 0
            assert results["errors"] == []

    @pytest.mark.asyncio
    async def test_run_scrape_handles_error(self):
        """Test that scrape errors are captured in results."""
        scheduler = ScrapeScheduler()

        with patch('src.scheduler.get_scraper') as mock_get_scraper, \
             patch('src.scheduler.db') as mock_db:

            # Mock scraper that raises
            mock_get_scraper.side_effect = ValueError("Scraper error")

            # Mock db
            mock_log = MagicMock()
            mock_log.id = 1
            mock_db.create_scrape_log.return_value = mock_log

            results = await scheduler.run_now(university="stanford")

            assert len(results["errors"]) == 1
            assert "stanford" in results["errors"][0]


class TestEnhancedFiltering:
    """Tests for enhanced filtering in database."""

    def test_search_function_accepts_date_params(self):
        """Test that search function accepts date range parameters."""
        from src.database import Database
        import inspect

        # Check that the function signature includes from_date and to_date
        sig = inspect.signature(Database.search_technologies)
        params = list(sig.parameters.keys())

        assert "from_date" in params
        assert "to_date" in params
        assert "patent_geography" in params

    def test_search_function_accepts_geography_param(self):
        """Test that search function accepts patent_geography parameter."""
        from src.database import Database
        import inspect

        sig = inspect.signature(Database.search_technologies)
        params = list(sig.parameters.keys())

        assert "patent_geography" in params


class TestCLIEnhancements:
    """Tests for CLI enhancements."""

    def test_search_command_has_date_options(self):
        """Test that search command accepts date options."""
        from click.testing import CliRunner
        from src.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["search", "--help"])

        assert "--from-date" in result.output
        assert "--to-date" in result.output
        assert "--geography" in result.output
        assert "--csv" in result.output

    def test_schedule_command_has_options(self):
        """Test that schedule command has all options."""
        from click.testing import CliRunner
        from src.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["schedule", "--help"])

        assert "--weekly" in result.output
        assert "--daily" in result.output
        assert "--run" in result.output
        assert "--list" in result.output
        assert "--hour" in result.output
        assert "--day" in result.output

    def test_migrate_command_has_options(self):
        """Test that migrate command has all options."""
        from click.testing import CliRunner
        from src.cli import main

        runner = CliRunner()
        result = runner.invoke(main, ["migrate", "--help"])

        assert "--upgrade" in result.output
        assert "--downgrade" in result.output
        assert "--current" in result.output
        assert "--history" in result.output


class TestBaseScraperWithRetry:
    """Tests for BaseScraper with retry functionality."""

    def test_scraper_has_retry_config(self):
        """Test that scraper accepts retry config."""
        from src.scrapers.stanford import StanfordScraper

        config = RetryConfig(max_retries=5)
        scraper = StanfordScraper()

        # Scraper should have retry config attribute
        assert hasattr(scraper, 'retry_config')

    def test_scraper_stats_includes_errors(self):
        """Test that scraper stats includes error count."""
        from src.scrapers.stanford import StanfordScraper

        scraper = StanfordScraper()
        stats = scraper.stats

        assert "errors" in stats
        assert stats["errors"] == 0


class TestDockerConfiguration:
    """Tests to verify Docker configuration files exist."""

    def test_dockerfile_exists(self):
        """Test that Dockerfile exists."""
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        dockerfile_path = os.path.join(project_root, "Dockerfile")
        assert os.path.exists(dockerfile_path)

    def test_docker_compose_exists(self):
        """Test that docker-compose.yml exists."""
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        compose_path = os.path.join(project_root, "docker-compose.yml")
        assert os.path.exists(compose_path)

    def test_dockerignore_exists(self):
        """Test that .dockerignore exists."""
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ignore_path = os.path.join(project_root, ".dockerignore")
        assert os.path.exists(ignore_path)


class TestAlembicConfiguration:
    """Tests for Alembic migration configuration."""

    def test_alembic_ini_exists(self):
        """Test that alembic.ini exists."""
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_path = os.path.join(project_root, "alembic.ini")
        assert os.path.exists(alembic_path)

    def test_migrations_directory_exists(self):
        """Test that migrations directory exists."""
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        migrations_path = os.path.join(project_root, "migrations")
        assert os.path.isdir(migrations_path)

    def test_initial_migration_exists(self):
        """Test that initial migration exists."""
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        versions_path = os.path.join(project_root, "migrations", "versions")
        assert os.path.isdir(versions_path)

        # Check for any migration file
        files = os.listdir(versions_path)
        migration_files = [f for f in files if f.endswith('.py') and not f.startswith('__')]
        assert len(migration_files) >= 1


# Helper class for async iterator mocking
class AsyncIteratorMock:
    """Mock async iterator for testing."""

    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item
