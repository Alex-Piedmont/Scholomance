"""LLM-based technology classification service using Claude API."""

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from anthropic import Anthropic, APIError, RateLimitError
from loguru import logger

from .config import settings
from .taxonomy import TAXONOMY, format_taxonomy_for_prompt, get_top_fields


@dataclass
class ClassificationResult:
    """Result of classifying a technology."""

    top_field: str
    subfield: str
    confidence: float
    reasoning: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    model: str = ""


@dataclass
class ClassificationError:
    """Error during classification."""

    error_type: str
    message: str
    retryable: bool = False


# Pricing per 1M tokens (Claude 3 Haiku for cost-effective classification)
PRICING = {
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-5-haiku-20241022": {"input": 1.00, "output": 5.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
}

# Default model for classification (Haiku for cost efficiency)
DEFAULT_MODEL = "claude-3-5-haiku-20241022"


class Classifier:
    """Technology classifier using Claude API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.api_key = api_key or settings.anthropic_api_key
        if not self.api_key:
            raise ValueError("Anthropic API key not configured. Set ANTHROPIC_API_KEY.")

        self.client = Anthropic(api_key=self.api_key)
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Rate limiting
        self._last_request_time = 0.0
        self._min_request_interval = 0.1  # 100ms between requests

        # Stats
        self.total_classifications = 0
        self.total_cost = 0.0
        self.total_tokens = 0

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on token usage."""
        pricing = PRICING.get(self.model, PRICING[DEFAULT_MODEL])
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def _build_prompt(self, title: str, description: str) -> str:
        """Build the classification prompt."""
        taxonomy_text = format_taxonomy_for_prompt()

        return f"""You are a technology classification expert. Your task is to classify university technology transfer listings into appropriate fields and subfields.

{taxonomy_text}

Instructions:
1. Read the technology title and description carefully
2. Identify the PRIMARY field this technology belongs to
3. Select the most specific subfield that applies
4. Provide a confidence score from 0.0 to 1.0
5. If the technology spans multiple fields, choose the most dominant one

Respond with ONLY a JSON object in this exact format:
{{
    "top_field": "field name from the list above",
    "subfield": "subfield name from the list above",
    "confidence": 0.85,
    "reasoning": "brief explanation of classification"
}}

Technology to classify:
Title: {title}
Description: {description or "No description provided."}

JSON response:"""

    def _parse_response(self, response_text: str) -> dict:
        """Parse the JSON response from Claude."""
        # Try to extract JSON from the response
        text = response_text.strip()

        # Handle potential markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {e}")
            # Try to find JSON object in the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                try:
                    return json.loads(text[start:end])
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Could not parse classification response: {text[:200]}")

    def _validate_classification(self, result: dict) -> dict:
        """Validate and normalize the classification result."""
        top_field = result.get("top_field", "").strip()
        subfield = result.get("subfield", "").strip()
        confidence = result.get("confidence", 0.5)

        # Validate top_field
        valid_fields = get_top_fields()
        if top_field not in valid_fields:
            # Try case-insensitive match
            for field in valid_fields:
                if field.lower() == top_field.lower():
                    top_field = field
                    break
            else:
                logger.warning(f"Unknown top_field '{top_field}', defaulting to 'Other'")
                top_field = "Other"

        # Validate subfield
        valid_subfields = TAXONOMY[top_field].subfields
        if subfield not in valid_subfields:
            # Try case-insensitive match
            for sf in valid_subfields:
                if sf.lower() == subfield.lower():
                    subfield = sf
                    break
            else:
                # Use first subfield as default
                subfield = valid_subfields[0] if valid_subfields else "Other"
                logger.debug(f"Unknown subfield, defaulting to '{subfield}'")

        # Validate confidence
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = 0.5

        return {
            "top_field": top_field,
            "subfield": subfield,
            "confidence": confidence,
            "reasoning": result.get("reasoning", ""),
        }

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def classify(
        self,
        title: str,
        description: Optional[str] = None,
    ) -> ClassificationResult | ClassificationError:
        """
        Classify a single technology.

        Args:
            title: Technology title
            description: Technology description (optional)

        Returns:
            ClassificationResult on success, ClassificationError on failure
        """
        prompt = self._build_prompt(title, description or "")

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=256,
                    messages=[{"role": "user", "content": prompt}],
                )

                # Extract token usage
                prompt_tokens = response.usage.input_tokens
                completion_tokens = response.usage.output_tokens
                cost = self._calculate_cost(prompt_tokens, completion_tokens)

                # Parse response
                response_text = response.content[0].text
                parsed = self._parse_response(response_text)
                validated = self._validate_classification(parsed)

                # Update stats
                self.total_classifications += 1
                self.total_cost += cost
                self.total_tokens += prompt_tokens + completion_tokens

                return ClassificationResult(
                    top_field=validated["top_field"],
                    subfield=validated["subfield"],
                    confidence=validated["confidence"],
                    reasoning=validated["reasoning"],
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_cost=cost,
                    model=self.model,
                )

            except RateLimitError as e:
                logger.warning(f"Rate limited (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return ClassificationError(
                        error_type="rate_limit",
                        message=str(e),
                        retryable=True,
                    )

            except APIError as e:
                logger.error(f"API error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return ClassificationError(
                        error_type="api_error",
                        message=str(e),
                        retryable=True,
                    )

            except ValueError as e:
                logger.error(f"Parse error: {e}")
                return ClassificationError(
                    error_type="parse_error",
                    message=str(e),
                    retryable=False,
                )

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return ClassificationError(
                    error_type="unknown",
                    message=str(e),
                    retryable=False,
                )

        return ClassificationError(
            error_type="max_retries",
            message="Max retries exceeded",
            retryable=True,
        )

    async def classify_async(
        self,
        title: str,
        description: Optional[str] = None,
    ) -> ClassificationResult | ClassificationError:
        """Async version of classify with rate limiting."""
        await self._rate_limit()
        # Run sync classify in executor to not block
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.classify, title, description)

    async def classify_batch(
        self,
        items: list[tuple[int, str, Optional[str]]],
        on_progress: Optional[callable] = None,
        max_concurrent: int = 3,
    ) -> list[tuple[int, ClassificationResult | ClassificationError]]:
        """
        Classify multiple technologies with concurrency control.

        Args:
            items: List of (id, title, description) tuples
            on_progress: Callback for progress updates (current, total)
            max_concurrent: Maximum concurrent classifications

        Returns:
            List of (id, result) tuples
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def classify_one(item: tuple[int, str, Optional[str]]) -> tuple[int, ClassificationResult | ClassificationError]:
            async with semaphore:
                tech_id, title, description = item
                result = await self.classify_async(title, description)
                return (tech_id, result)

        total = len(items)
        completed = 0

        for item in items:
            result = await classify_one(item)
            results.append(result)
            completed += 1

            if on_progress:
                on_progress(completed, total)

        return results

    @property
    def stats(self) -> dict:
        """Return classification statistics."""
        return {
            "total_classifications": self.total_classifications,
            "total_cost": round(self.total_cost, 6),
            "total_tokens": self.total_tokens,
            "average_cost_per_classification": (
                round(self.total_cost / self.total_classifications, 6)
                if self.total_classifications > 0
                else 0
            ),
        }
