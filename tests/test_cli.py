"""Tests for CLI commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from src.cli import main, scrape, search, stats, init_db


@pytest.fixture
def cli_runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestCLIMain:
    """Tests for the main CLI group."""

    def test_main_help(self, cli_runner):
        """Test main help command."""
        result = cli_runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "University Tech Transfer Scraper" in result.output

    def test_main_verbose_flag(self, cli_runner):
        """Test verbose flag is accepted."""
        result = cli_runner.invoke(main, ["--verbose", "--help"])
        assert result.exit_code == 0


class TestScrapeCommand:
    """Tests for the scrape command."""

    def test_scrape_help(self, cli_runner):
        """Test scrape help."""
        result = cli_runner.invoke(main, ["scrape", "--help"])
        assert result.exit_code == 0
        assert "--university" in result.output
        assert "--all" in result.output

    def test_scrape_no_args_error(self, cli_runner):
        """Test scrape without arguments shows error."""
        result = cli_runner.invoke(main, ["scrape"])
        assert result.exit_code == 1
        assert "Please specify" in result.output

    def test_scrape_university_choice(self, cli_runner):
        """Test scrape accepts valid university."""
        result = cli_runner.invoke(main, ["scrape", "--help"])
        assert "stanford" in result.output


class TestSearchCommand:
    """Tests for the search command."""

    def test_search_help(self, cli_runner):
        """Test search help."""
        result = cli_runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "--keyword" in result.output
        assert "--university" in result.output
        assert "--json" in result.output

    @patch("src.cli.db")
    def test_search_no_results(self, mock_db, cli_runner):
        """Test search with no results."""
        mock_db.search_technologies.return_value = []

        result = cli_runner.invoke(main, ["search", "--keyword", "nonexistent"])
        assert result.exit_code == 0
        assert "No technologies found" in result.output

    @patch("src.cli.db")
    def test_search_with_results(self, mock_db, cli_runner):
        """Test search with results."""
        # Create mock technology objects
        mock_tech = MagicMock()
        mock_tech.id = 1
        mock_tech.university = "stanford"
        mock_tech.tech_id = "S21-001"
        mock_tech.title = "Test Technology"
        mock_tech.description = "A test description"
        mock_tech.url = "https://example.com"
        mock_tech.top_field = "Robotics"
        mock_tech.subfield = None
        mock_tech.scraped_at = None

        mock_db.search_technologies.return_value = [mock_tech]

        result = cli_runner.invoke(main, ["search", "--keyword", "test"])
        assert result.exit_code == 0

    @patch("src.cli.db")
    def test_search_json_output(self, mock_db, cli_runner):
        """Test search with JSON output."""
        mock_tech = MagicMock()
        mock_tech.id = 1
        mock_tech.university = "stanford"
        mock_tech.tech_id = "S21-001"
        mock_tech.title = "Test Technology"
        mock_tech.description = "A test description"
        mock_tech.url = "https://example.com"
        mock_tech.top_field = "Robotics"
        mock_tech.subfield = None
        mock_tech.keywords = ["test", "keyword"]
        mock_tech.patent_geography = ["US"]
        mock_tech.scraped_at = None

        mock_db.search_technologies.return_value = [mock_tech]

        result = cli_runner.invoke(main, ["search", "--keyword", "test", "--json"])
        assert result.exit_code == 0
        # JSON output should contain these strings
        assert '"university":' in result.output or '"university"' in result.output


class TestStatsCommand:
    """Tests for the stats command."""

    def test_stats_help(self, cli_runner):
        """Test stats help."""
        result = cli_runner.invoke(main, ["stats", "--help"])
        assert result.exit_code == 0
        assert "--university" in result.output

    @patch("src.cli.db")
    def test_stats_total(self, mock_db, cli_runner):
        """Test stats shows total count."""
        mock_db.count_technologies.return_value = 100

        result = cli_runner.invoke(main, ["stats"])
        assert result.exit_code == 0
        assert "100" in result.output

    @patch("src.cli.db")
    def test_stats_by_university(self, mock_db, cli_runner):
        """Test stats for specific university."""
        mock_db.count_technologies.return_value = 50

        result = cli_runner.invoke(main, ["stats", "--university", "stanford"])
        assert result.exit_code == 0
        assert "stanford" in result.output
        assert "50" in result.output


class TestInitDbCommand:
    """Tests for the init-db command."""

    def test_init_db_help(self, cli_runner):
        """Test init-db help."""
        result = cli_runner.invoke(main, ["init-db", "--help"])
        assert result.exit_code == 0

    @patch("src.cli.db")
    def test_init_db_success(self, mock_db, cli_runner):
        """Test successful database initialization."""
        mock_db.init_db.return_value = None

        result = cli_runner.invoke(main, ["init-db"])
        assert result.exit_code == 0
        assert "successfully" in result.output


class TestScheduleCommand:
    """Tests for the schedule command."""

    def test_schedule_help(self, cli_runner):
        """Test schedule help."""
        result = cli_runner.invoke(main, ["schedule", "--help"])
        assert result.exit_code == 0
        assert "--weekly" in result.output
        assert "--daily" in result.output

    def test_schedule_no_args_error(self, cli_runner):
        """Test schedule without arguments shows error."""
        result = cli_runner.invoke(main, ["schedule"])
        assert result.exit_code == 1
        assert "Please specify" in result.output

    def test_schedule_weekly(self, cli_runner):
        """Test schedule with weekly flag."""
        result = cli_runner.invoke(main, ["schedule", "--weekly"])
        assert result.exit_code == 0
        # Should mention Phase 4 since not implemented yet
        assert "Phase 4" in result.output or "weekly" in result.output


class TestShowCommand:
    """Tests for the show command."""

    def test_show_help(self, cli_runner):
        """Test show help."""
        result = cli_runner.invoke(main, ["show", "--help"])
        assert result.exit_code == 0

    @patch("src.cli.db")
    def test_show_not_found(self, mock_db, cli_runner):
        """Test show with non-existent ID."""
        mock_db.get_technology_by_id.return_value = None

        result = cli_runner.invoke(main, ["show", "999"])
        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("src.cli.db")
    def test_show_success(self, mock_db, cli_runner):
        """Test show with existing technology."""
        mock_tech = MagicMock()
        mock_tech.id = 1
        mock_tech.university = "stanford"
        mock_tech.tech_id = "S21-001"
        mock_tech.title = "Amazing Technology"
        mock_tech.description = "This is a great technology."
        mock_tech.url = "https://example.com"
        mock_tech.top_field = "Robotics"
        mock_tech.subfield = None
        mock_tech.keywords = ["robotics", "ai"]

        mock_db.get_technology_by_id.return_value = mock_tech

        result = cli_runner.invoke(main, ["show", "1"])
        assert result.exit_code == 0
        assert "Amazing Technology" in result.output


class TestClassifyCommand:
    """Tests for the classify command."""

    def test_classify_help(self, cli_runner):
        """Test classify help."""
        result = cli_runner.invoke(main, ["classify", "--help"])
        assert result.exit_code == 0
        assert "--batch" in result.output
        assert "--university" in result.output
        assert "--force" in result.output
        assert "--dry-run" in result.output

    @patch("src.cli.db")
    def test_classify_no_technologies(self, mock_db, cli_runner):
        """Test classify with no technologies to classify."""
        mock_db.get_technologies_for_classification.return_value = []

        result = cli_runner.invoke(main, ["classify"])
        assert result.exit_code == 0
        assert "No technologies to classify" in result.output

    @patch("src.cli.db")
    def test_classify_dry_run(self, mock_db, cli_runner):
        """Test classify in dry-run mode."""
        mock_tech = MagicMock()
        mock_tech.id = 1
        mock_tech.university = "stanford"
        mock_tech.title = "Test Technology"
        mock_tech.top_field = None

        mock_db.get_technologies_for_classification.return_value = [mock_tech]

        result = cli_runner.invoke(main, ["classify", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output

    @patch("src.cli.Classifier")
    @patch("src.cli.db")
    def test_classify_missing_api_key(self, mock_db, mock_classifier_class, cli_runner):
        """Test classify with missing API key."""
        mock_tech = MagicMock()
        mock_tech.id = 1
        mock_tech.title = "Test"
        mock_tech.description = "Test desc"

        mock_db.get_technologies_for_classification.return_value = [mock_tech]
        mock_classifier_class.side_effect = ValueError("API key not configured")

        result = cli_runner.invoke(main, ["classify"])
        assert result.exit_code == 1
        assert "ANTHROPIC_API_KEY" in result.output or "Error" in result.output


class TestClassificationStatsCommand:
    """Tests for the classification-stats command."""

    def test_classification_stats_help(self, cli_runner):
        """Test classification-stats help."""
        result = cli_runner.invoke(main, ["classification-stats", "--help"])
        assert result.exit_code == 0
        assert "--university" in result.output

    @patch("src.cli.db")
    def test_classification_stats_basic(self, mock_db, cli_runner):
        """Test basic classification stats."""
        mock_db.count_unclassified.return_value = 50
        mock_db.count_classified.return_value = 100
        mock_db.get_classification_stats.return_value = {
            "total_cost": 0.05,
            "total_classifications": 100,
            "by_field": {"Robotics": 30, "MedTech": 25},
        }

        result = cli_runner.invoke(main, ["classification-stats"])
        assert result.exit_code == 0
        assert "150" in result.output or "Total" in result.output

    @patch("src.cli.db")
    def test_classification_stats_by_university(self, mock_db, cli_runner):
        """Test classification stats for specific university."""
        mock_db.count_unclassified.return_value = 10
        mock_db.count_classified.return_value = 40
        mock_db.get_classification_stats.return_value = {
            "total_cost": 0.02,
            "total_classifications": 40,
            "by_field": {},
        }

        result = cli_runner.invoke(main, ["classification-stats", "-u", "stanford"])
        assert result.exit_code == 0


class TestListFieldsCommand:
    """Tests for the list-fields command."""

    def test_list_fields_help(self, cli_runner):
        """Test list-fields help."""
        result = cli_runner.invoke(main, ["list-fields", "--help"])
        assert result.exit_code == 0

    def test_list_fields_output(self, cli_runner):
        """Test list-fields shows fields and subfields."""
        result = cli_runner.invoke(main, ["list-fields"])
        assert result.exit_code == 0
        assert "Robotics" in result.output
        assert "MedTech" in result.output
        assert "Subfields" in result.output
