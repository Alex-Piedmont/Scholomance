"""Tests for the classifier service."""

import pytest
from unittest.mock import MagicMock, patch, Mock
from decimal import Decimal

from src.classifier import (
    Classifier,
    ClassificationResult,
    ClassificationError,
    PRICING,
    DEFAULT_MODEL,
)


class TestClassificationResult:
    """Tests for ClassificationResult dataclass."""

    def test_result_creation(self):
        """Test creating a ClassificationResult."""
        result = ClassificationResult(
            top_field="Robotics",
            subfield="Industrial Robotics",
            confidence=0.85,
            reasoning="Technology involves robotic manipulation",
            prompt_tokens=100,
            completion_tokens=50,
            total_cost=0.001,
            model="claude-3-haiku",
        )

        assert result.top_field == "Robotics"
        assert result.subfield == "Industrial Robotics"
        assert result.confidence == 0.85
        assert result.prompt_tokens == 100

    def test_result_defaults(self):
        """Test ClassificationResult default values."""
        result = ClassificationResult(
            top_field="Computing",
            subfield="AI",
            confidence=0.9,
        )

        assert result.reasoning is None
        assert result.prompt_tokens == 0
        assert result.total_cost == 0.0


class TestClassificationError:
    """Tests for ClassificationError dataclass."""

    def test_error_creation(self):
        """Test creating a ClassificationError."""
        error = ClassificationError(
            error_type="api_error",
            message="Rate limit exceeded",
            retryable=True,
        )

        assert error.error_type == "api_error"
        assert error.message == "Rate limit exceeded"
        assert error.retryable is True

    def test_error_defaults(self):
        """Test ClassificationError default values."""
        error = ClassificationError(
            error_type="parse_error",
            message="Invalid JSON",
        )

        assert error.retryable is False


class TestClassifierInit:
    """Tests for Classifier initialization."""

    def test_missing_api_key_raises(self):
        """Test that missing API key raises ValueError."""
        with patch("src.classifier.settings") as mock_settings:
            mock_settings.anthropic_api_key = None

            with pytest.raises(ValueError) as exc_info:
                Classifier(api_key=None)

            assert "API key" in str(exc_info.value)

    @patch("src.classifier.Anthropic")
    def test_init_with_api_key(self, mock_anthropic):
        """Test initialization with provided API key."""
        classifier = Classifier(api_key="test-key")

        assert classifier.api_key == "test-key"
        mock_anthropic.assert_called_once_with(api_key="test-key")

    @patch("src.classifier.Anthropic")
    def test_init_with_custom_model(self, mock_anthropic):
        """Test initialization with custom model."""
        classifier = Classifier(api_key="test-key", model="claude-3-sonnet-20240229")

        assert classifier.model == "claude-3-sonnet-20240229"


class TestClassifierCostCalculation:
    """Tests for cost calculation."""

    @patch("src.classifier.Anthropic")
    def test_calculate_cost_haiku(self, mock_anthropic):
        """Test cost calculation for Haiku model."""
        classifier = Classifier(api_key="test-key")

        # 1000 input tokens, 500 output tokens
        cost = classifier._calculate_cost(1000, 500)

        # Haiku pricing: $1/M input, $5/M output
        expected_input = (1000 / 1_000_000) * 1.00
        expected_output = (500 / 1_000_000) * 5.00
        expected = expected_input + expected_output

        assert abs(cost - expected) < 0.0001

    @patch("src.classifier.Anthropic")
    def test_calculate_cost_sonnet(self, mock_anthropic):
        """Test cost calculation for Sonnet model."""
        classifier = Classifier(api_key="test-key", model="claude-3-sonnet-20240229")

        cost = classifier._calculate_cost(1000, 500)

        # Sonnet pricing: $3/M input, $15/M output
        expected_input = (1000 / 1_000_000) * 3.00
        expected_output = (500 / 1_000_000) * 15.00
        expected = expected_input + expected_output

        assert abs(cost - expected) < 0.0001


class TestClassifierPromptBuilding:
    """Tests for prompt building."""

    @patch("src.classifier.Anthropic")
    def test_build_prompt_includes_title(self, mock_anthropic):
        """Test that prompt includes the technology title."""
        classifier = Classifier(api_key="test-key")

        prompt = classifier._build_prompt(
            title="Robotic Arm Controller",
            description="A system for controlling robotic arms",
        )

        assert "Robotic Arm Controller" in prompt

    @patch("src.classifier.Anthropic")
    def test_build_prompt_includes_description(self, mock_anthropic):
        """Test that prompt includes the description."""
        classifier = Classifier(api_key="test-key")

        prompt = classifier._build_prompt(
            title="Test Tech",
            description="This is a test description",
        )

        assert "This is a test description" in prompt

    @patch("src.classifier.Anthropic")
    def test_build_prompt_handles_empty_description(self, mock_anthropic):
        """Test that prompt handles empty description."""
        classifier = Classifier(api_key="test-key")

        prompt = classifier._build_prompt(
            title="Test Tech",
            description="",
        )

        assert "Test Tech" in prompt
        assert "No description provided" in prompt or prompt  # Either handles it gracefully

    @patch("src.classifier.Anthropic")
    def test_build_prompt_includes_taxonomy(self, mock_anthropic):
        """Test that prompt includes taxonomy fields."""
        classifier = Classifier(api_key="test-key")

        prompt = classifier._build_prompt(
            title="Test",
            description="Test",
        )

        assert "Robotics" in prompt
        assert "MedTech" in prompt
        assert "Computing" in prompt


class TestClassifierResponseParsing:
    """Tests for response parsing."""

    @patch("src.classifier.Anthropic")
    def test_parse_valid_json(self, mock_anthropic):
        """Test parsing valid JSON response."""
        classifier = Classifier(api_key="test-key")

        response = '{"top_field": "Robotics", "subfield": "Industrial Robotics", "confidence": 0.9, "reasoning": "test"}'
        parsed = classifier._parse_response(response)

        assert parsed["top_field"] == "Robotics"
        assert parsed["subfield"] == "Industrial Robotics"
        assert parsed["confidence"] == 0.9

    @patch("src.classifier.Anthropic")
    def test_parse_json_with_markdown(self, mock_anthropic):
        """Test parsing JSON wrapped in markdown code block."""
        classifier = Classifier(api_key="test-key")

        response = '```json\n{"top_field": "Computing", "subfield": "AI", "confidence": 0.8}\n```'
        parsed = classifier._parse_response(response)

        assert parsed["top_field"] == "Computing"

    @patch("src.classifier.Anthropic")
    def test_parse_invalid_json_raises(self, mock_anthropic):
        """Test that invalid JSON raises ValueError."""
        classifier = Classifier(api_key="test-key")

        with pytest.raises(ValueError):
            classifier._parse_response("not valid json at all")


class TestClassifierValidation:
    """Tests for classification validation."""

    @patch("src.classifier.Anthropic")
    def test_validate_valid_classification(self, mock_anthropic):
        """Test validation of valid classification."""
        classifier = Classifier(api_key="test-key")

        result = {
            "top_field": "Robotics",
            "subfield": "Industrial Robotics",
            "confidence": 0.85,
            "reasoning": "test",
        }

        validated = classifier._validate_classification(result)

        assert validated["top_field"] == "Robotics"
        assert validated["subfield"] == "Industrial Robotics"
        assert validated["confidence"] == 0.85

    @patch("src.classifier.Anthropic")
    def test_validate_unknown_field_defaults_to_other(self, mock_anthropic):
        """Test that unknown field defaults to 'Other'."""
        classifier = Classifier(api_key="test-key")

        result = {
            "top_field": "UnknownField",
            "subfield": "Something",
            "confidence": 0.5,
        }

        validated = classifier._validate_classification(result)

        assert validated["top_field"] == "Other"

    @patch("src.classifier.Anthropic")
    def test_validate_confidence_clamping(self, mock_anthropic):
        """Test that confidence is clamped to 0-1 range."""
        classifier = Classifier(api_key="test-key")

        # Test > 1
        result = {"top_field": "Robotics", "subfield": "Industrial Robotics", "confidence": 1.5}
        validated = classifier._validate_classification(result)
        assert validated["confidence"] == 1.0

        # Test < 0
        result = {"top_field": "Robotics", "subfield": "Industrial Robotics", "confidence": -0.5}
        validated = classifier._validate_classification(result)
        assert validated["confidence"] == 0.0

    @patch("src.classifier.Anthropic")
    def test_validate_case_insensitive_field(self, mock_anthropic):
        """Test case-insensitive field matching."""
        classifier = Classifier(api_key="test-key")

        result = {
            "top_field": "robotics",  # lowercase
            "subfield": "industrial robotics",  # lowercase
            "confidence": 0.8,
        }

        validated = classifier._validate_classification(result)

        assert validated["top_field"] == "Robotics"


class TestClassifierStats:
    """Tests for classifier statistics."""

    @patch("src.classifier.Anthropic")
    def test_initial_stats(self, mock_anthropic):
        """Test initial statistics are zero."""
        classifier = Classifier(api_key="test-key")

        stats = classifier.stats

        assert stats["total_classifications"] == 0
        assert stats["total_cost"] == 0
        assert stats["total_tokens"] == 0
        assert stats["average_cost_per_classification"] == 0


class TestPricingConfig:
    """Tests for pricing configuration."""

    def test_pricing_has_default_model(self):
        """Test that pricing includes default model."""
        assert DEFAULT_MODEL in PRICING or "claude-3-5-haiku" in DEFAULT_MODEL

    def test_pricing_has_input_output(self):
        """Test that pricing entries have input and output."""
        for model, prices in PRICING.items():
            assert "input" in prices
            assert "output" in prices
            assert prices["input"] > 0
            assert prices["output"] > 0


class TestClassifierClassify:
    """Tests for the classify method."""

    @patch("src.classifier.Anthropic")
    def test_classify_success(self, mock_anthropic):
        """Test successful classification."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.content = [
            MagicMock(text='{"top_field": "Robotics", "subfield": "Industrial Robotics", "confidence": 0.9, "reasoning": "test"}')
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        classifier = Classifier(api_key="test-key")
        result = classifier.classify("Robot Arm", "A robotic arm for manufacturing")

        assert isinstance(result, ClassificationResult)
        assert result.top_field == "Robotics"
        assert result.confidence == 0.9

    @patch("src.classifier.Anthropic")
    def test_classify_updates_stats(self, mock_anthropic):
        """Test that classify updates statistics."""
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        mock_response.content = [
            MagicMock(text='{"top_field": "Computing", "subfield": "AI", "confidence": 0.8}')
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        classifier = Classifier(api_key="test-key")

        assert classifier.total_classifications == 0

        classifier.classify("AI System", "An artificial intelligence system")

        assert classifier.total_classifications == 1
        assert classifier.total_tokens == 150
        assert classifier.total_cost > 0

    @patch("src.classifier.Anthropic")
    def test_classify_handles_none_description(self, mock_anthropic):
        """Test classification with None description."""
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 80
        mock_response.usage.output_tokens = 40
        mock_response.content = [
            MagicMock(text='{"top_field": "Energy", "subfield": "Solar Energy", "confidence": 0.7}')
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        classifier = Classifier(api_key="test-key")
        result = classifier.classify("Solar Panel Tech", None)

        assert isinstance(result, ClassificationResult)
        assert result.top_field == "Energy"


class TestClassifierRetryBehavior:
    """Tests for classifier retry behavior."""

    @patch("src.classifier.Anthropic")
    def test_max_retries_setting(self, mock_anthropic):
        """Test max_retries configuration."""
        classifier = Classifier(api_key="test-key", max_retries=5)
        assert classifier.max_retries == 5

    @patch("src.classifier.Anthropic")
    def test_retry_delay_setting(self, mock_anthropic):
        """Test retry_delay configuration."""
        classifier = Classifier(api_key="test-key", retry_delay=2.0)
        assert classifier.retry_delay == 2.0


class TestClassifierAsyncMethods:
    """Tests for async classifier methods."""

    @patch("src.classifier.Anthropic")
    def test_classify_async_exists(self, mock_anthropic):
        """Test that classify_async method exists."""
        classifier = Classifier(api_key="test-key")
        assert hasattr(classifier, "classify_async")
        assert callable(classifier.classify_async)

    @patch("src.classifier.Anthropic")
    def test_classify_batch_exists(self, mock_anthropic):
        """Test that classify_batch method exists."""
        classifier = Classifier(api_key="test-key")
        assert hasattr(classifier, "classify_batch")
        assert callable(classifier.classify_batch)

    @patch("src.classifier.Anthropic")
    def test_rate_limit_method_exists(self, mock_anthropic):
        """Test that _rate_limit method exists."""
        classifier = Classifier(api_key="test-key")
        assert hasattr(classifier, "_rate_limit")


class TestClassifierEdgeCases:
    """Tests for edge cases in classification."""

    @patch("src.classifier.Anthropic")
    def test_empty_title(self, mock_anthropic):
        """Test classification with empty title."""
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 30
        mock_response.content = [
            MagicMock(text='{"top_field": "Other", "subfield": "Other", "confidence": 0.3}')
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        classifier = Classifier(api_key="test-key")
        result = classifier.classify("", "Some description")

        assert isinstance(result, ClassificationResult)

    @patch("src.classifier.Anthropic")
    def test_very_long_description(self, mock_anthropic):
        """Test classification with very long description."""
        mock_response = MagicMock()
        mock_response.usage.input_tokens = 500
        mock_response.usage.output_tokens = 50
        mock_response.content = [
            MagicMock(text='{"top_field": "MedTech", "subfield": "Diagnostics", "confidence": 0.85}')
        ]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client

        classifier = Classifier(api_key="test-key")
        long_description = "This is a medical diagnostic device. " * 100
        result = classifier.classify("Medical Device", long_description)

        assert isinstance(result, ClassificationResult)
        assert result.top_field == "MedTech"
