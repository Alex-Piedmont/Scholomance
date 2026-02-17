"""LLM-based technology opportunity assessment service using Claude API."""

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Optional

from anthropic import Anthropic, APIError, RateLimitError
from loguru import logger

from .config import settings


# Fields used to determine data richness for tier assignment
RICHNESS_FIELDS = [
    "applications",
    "advantages",
    "key_points",
    "development_stage",
    "publications",
    "market_opportunity",
]

# Hybrid TRL scale
TRL_TIERS = [
    "Concept",
    "Prototype:Early",
    "Prototype:Demonstrated",
    "Prototype:Advanced",
    "Market-ready",
]

# Pricing per 1M tokens
PRICING = {
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    "claude-3-5-haiku-20241022": {"input": 1.00, "output": 5.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
}

DEFAULT_MODEL = "claude-haiku-4-5-20251001"


@dataclass
class CategoryAssessment:
    """Assessment result for a single category."""

    score: float  # 0.0-1.0
    confidence: float  # 0.0-1.0
    reasoning: str
    details: dict


@dataclass
class AssessmentResult:
    """Result of assessing a technology opportunity."""

    assessment_tier: str  # 'full', 'limited'
    composite_score: float
    trl_gap: Optional[CategoryAssessment] = None
    false_barrier: Optional[CategoryAssessment] = None
    alt_application: Optional[CategoryAssessment] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    model: str = ""
    raw_response: Optional[dict] = None


@dataclass
class AssessmentError:
    """Error during assessment."""

    error_type: str
    message: str
    retryable: bool = False


def determine_assessment_tier(
    title: str,
    description: Optional[str],
    raw_data: Optional[dict],
) -> str:
    """
    Determine the assessment tier based on data availability.

    Returns:
        'full', 'limited', or 'skipped'
    """
    if not description or not description.strip():
        return "skipped"

    raw_data = raw_data or {}
    populated = sum(
        1
        for f in RICHNESS_FIELDS
        if f in raw_data and raw_data[f] and str(raw_data[f]).strip()
    )

    if populated >= 2:
        return "full"
    return "limited"


class Assessor:
    """Technology opportunity assessor using Claude API."""

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
        self.total_assessments = 0
        self.total_cost = 0.0
        self.total_tokens = 0

    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost based on token usage."""
        pricing = PRICING.get(self.model, PRICING[DEFAULT_MODEL])
        input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = (completion_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost

    def _format_raw_data(self, raw_data: Optional[dict]) -> str:
        """Format non-empty raw_data fields for the prompt."""
        if not raw_data:
            return "No additional data available."

        lines = []
        for key, value in raw_data.items():
            if value and str(value).strip():
                lines.append(f"  {key}: {value}")

        return "\n".join(lines) if lines else "No additional data available."

    def _build_prompt(
        self,
        title: str,
        description: str,
        raw_data: Optional[dict],
        tier: str,
    ) -> str:
        """Build the assessment prompt."""
        raw_data_text = self._format_raw_data(raw_data)

        trl_scale = """Hybrid TRL Scale:
- Concept (TRL 1-3): Theory, research question, simulation, initial lab work. No physical validation yet.
- Prototype:Early (TRL 4): Key components validated in a lab setting. Basic proof-of-concept exists.
- Prototype:Demonstrated (TRL 5-6): Tested in a relevant or operational environment. Performance data available.
- Prototype:Advanced (TRL 7): Full system prototype demonstrated in an operational environment.
- Market-ready (TRL 8-9): System qualified through testing, production-ready or already deployed."""

        if tier == "limited":
            return f"""You are a technology commercialization expert. Assess the following university technology listing.

{trl_scale}

Category to assess:

**TRL Gap Analysis**: Compare the maturity level implied by the inventor's language (marketing speak, hedging, etc.) against the actual technical evidence. A high score means there is a significant gap between how mature the technology sounds vs. how mature it actually is.
- inventor_implied_tier: What TRL tier does the inventor's language suggest? (e.g., "ready for licensing" implies Market-ready)
- assessed_tier: What TRL tier does the actual evidence support?
- evidence_fields: Which data fields informed your assessment?

Respond with ONLY a JSON object in this exact format:
{{
  "trl_gap": {{
    "score": 0.0,
    "confidence": 0.0,
    "inventor_implied_tier": "one of: Concept, Prototype:Early, Prototype:Demonstrated, Prototype:Advanced, Market-ready",
    "assessed_tier": "one of: Concept, Prototype:Early, Prototype:Demonstrated, Prototype:Advanced, Market-ready",
    "evidence_fields": ["list of raw_data field names used"],
    "reasoning": "brief explanation"
  }}
}}

Technology to assess:
Title: {title}
Description: {description}

Additional data:
{raw_data_text}

JSON response:"""

        # Full tier prompt
        return f"""You are a technology commercialization expert. Assess the following university technology listing across three categories.

{trl_scale}

Categories to assess:

1. **TRL Gap Analysis**: Compare the maturity level implied by the inventor's language (marketing speak, hedging, etc.) against the actual technical evidence. A high score means there is a significant gap between how mature the technology sounds vs. how mature it actually is.
   - inventor_implied_tier: What TRL tier does the inventor's language suggest? (e.g., "ready for licensing" implies Market-ready)
   - assessed_tier: What TRL tier does the actual evidence support?
   - evidence_fields: Which data fields informed your assessment?
   Example: A listing says "proven technology ready for market" but only has simulation data -> high TRL gap score.

2. **False Barrier Detection**: Infer what barriers to commercialization might exist based on the description and available data (regulatory hurdles, scaling challenges, market adoption concerns, etc.), even if not explicitly stated. Then evaluate whether those barriers are genuine blockers or overstated. A high score means the barriers are likely false or overstated.
   - stated_barrier: The main barrier you identified (inferred or explicit)
   - rebuttal: Why this barrier may be false or overstated
   - barrier_source_field: Which field the barrier was inferred from (e.g., "description", "advantages")
   - market_context: Relevant market context that supports the rebuttal
   Example: A listing implies regulatory barriers for a diagnostic tool, but the technology is software-based and may not require FDA clearance -> high false barrier score.

3. **Alternative Application Discovery**: Identify up to 3 plausible alternative applications for this technology beyond its stated use. Only suggest applications that are genuinely plausible given the underlying mechanism. A high score means strong alternative applications exist.
   - original_application: The primary application stated in the listing
   - suggested_applications: List of up to 3 alternative applications, each with application name, reasoning, and a market_signal (evidence from the data or general market knowledge)
   Example: A novel antimicrobial coating designed for medical devices could also apply to food packaging or HVAC systems.

Respond with ONLY a JSON object in this exact format:
{{
  "trl_gap": {{
    "score": 0.0,
    "confidence": 0.0,
    "inventor_implied_tier": "one of: Concept, Prototype:Early, Prototype:Demonstrated, Prototype:Advanced, Market-ready",
    "assessed_tier": "one of: Concept, Prototype:Early, Prototype:Demonstrated, Prototype:Advanced, Market-ready",
    "evidence_fields": ["list of raw_data field names used"],
    "reasoning": "brief explanation"
  }},
  "false_barrier": {{
    "score": 0.0,
    "confidence": 0.0,
    "stated_barrier": "the main barrier identified",
    "rebuttal": "why the barrier may be false or overstated",
    "barrier_source_field": "description",
    "market_context": "relevant market context",
    "reasoning": "brief explanation"
  }},
  "alt_application": {{
    "score": 0.0,
    "confidence": 0.0,
    "original_application": "stated primary application",
    "suggested_applications": [
      {{"application": "alt use", "reasoning": "why plausible", "market_signal": "supporting evidence"}}
    ],
    "reasoning": "brief explanation"
  }}
}}

Technology to assess:
Title: {title}
Description: {description}

Additional data:
{raw_data_text}

JSON response:"""

    def _parse_response(self, response_text: str) -> dict:
        """Parse the JSON response from Claude."""
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
            raise ValueError(f"Could not parse assessment response: {text[:200]}")

    def _validate_assessment(self, parsed: dict, tier: str) -> dict:
        """Validate and normalize the assessment result."""
        validated = {}

        # Always validate trl_gap
        if "trl_gap" in parsed:
            trl = parsed["trl_gap"]
            trl["score"] = self._clamp_score(trl.get("score", 0.5))
            trl["confidence"] = self._clamp_score(trl.get("confidence", 0.5))

            # Validate TRL tiers
            if trl.get("inventor_implied_tier") not in TRL_TIERS:
                trl["inventor_implied_tier"] = self._match_trl_tier(
                    trl.get("inventor_implied_tier", "")
                )
            if trl.get("assessed_tier") not in TRL_TIERS:
                trl["assessed_tier"] = self._match_trl_tier(
                    trl.get("assessed_tier", "")
                )

            trl.setdefault("evidence_fields", [])
            trl.setdefault("reasoning", "")
            validated["trl_gap"] = trl

        if tier == "full":
            # Validate false_barrier
            if "false_barrier" in parsed:
                fb = parsed["false_barrier"]
                fb["score"] = self._clamp_score(fb.get("score", 0.5))
                fb["confidence"] = self._clamp_score(fb.get("confidence", 0.5))
                fb.setdefault("stated_barrier", "")
                fb.setdefault("rebuttal", "")
                fb.setdefault("barrier_source_field", "description")
                fb.setdefault("market_context", "")
                fb.setdefault("reasoning", "")
                validated["false_barrier"] = fb

            # Validate alt_application
            if "alt_application" in parsed:
                alt = parsed["alt_application"]
                alt["score"] = self._clamp_score(alt.get("score", 0.5))
                alt["confidence"] = self._clamp_score(alt.get("confidence", 0.5))
                alt.setdefault("original_application", "")
                alt.setdefault("suggested_applications", [])
                alt.setdefault("reasoning", "")

                # Validate each suggested application
                valid_apps = []
                for app in alt["suggested_applications"][:3]:
                    if isinstance(app, dict) and app.get("application"):
                        app.setdefault("reasoning", "")
                        app.setdefault("market_signal", "")
                        valid_apps.append(app)
                alt["suggested_applications"] = valid_apps
                validated["alt_application"] = alt

        return validated

    @staticmethod
    def _clamp_score(value) -> float:
        """Clamp a value to 0.0-1.0 range."""
        try:
            v = float(value)
            return max(0.0, min(1.0, v))
        except (TypeError, ValueError):
            return 0.5

    @staticmethod
    def _match_trl_tier(raw: str) -> str:
        """Attempt to match a raw string to a valid TRL tier."""
        if not raw:
            return "Concept"
        raw_lower = raw.strip().lower()
        for tier in TRL_TIERS:
            if tier.lower() == raw_lower:
                return tier
        # Fuzzy matching
        if "market" in raw_lower or "ready" in raw_lower:
            return "Market-ready"
        if "advanced" in raw_lower:
            return "Prototype:Advanced"
        if "demonstrated" in raw_lower:
            return "Prototype:Demonstrated"
        if "early" in raw_lower or "proto" in raw_lower:
            return "Prototype:Early"
        return "Concept"

    def _compute_composite_score(self, validated: dict, tier: str) -> float:
        """Compute a weighted composite score from category scores."""
        if tier == "limited":
            trl = validated.get("trl_gap", {})
            return round(trl.get("score", 0.0), 4)

        categories = ["trl_gap", "false_barrier", "alt_application"]
        scores = []

        for key in categories:
            cat = validated.get(key)
            if cat and "score" in cat:
                scores.append(cat["score"])

        if not scores:
            return 0.0
        return round(sum(scores) / len(scores), 4)

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            await asyncio.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def assess(
        self,
        title: str,
        description: Optional[str] = None,
        raw_data: Optional[dict] = None,
    ) -> AssessmentResult | AssessmentError:
        """
        Assess a single technology opportunity.

        Args:
            title: Technology title
            description: Technology description
            raw_data: Additional structured data (JSONB raw_data column)

        Returns:
            AssessmentResult on success, AssessmentError on failure
        """
        tier = determine_assessment_tier(title, description, raw_data)

        if tier == "skipped":
            return AssessmentResult(
                assessment_tier="skipped",
                composite_score=0.0,
                model=self.model,
            )

        prompt = self._build_prompt(title, description or "", raw_data, tier)

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                )

                # Extract token usage
                prompt_tokens = response.usage.input_tokens
                completion_tokens = response.usage.output_tokens
                cost = self._calculate_cost(prompt_tokens, completion_tokens)

                # Parse response
                response_text = response.content[0].text
                parsed = self._parse_response(response_text)
                validated = self._validate_assessment(parsed, tier)

                # Update stats
                self.total_assessments += 1
                self.total_cost += cost
                self.total_tokens += prompt_tokens + completion_tokens

                # Build category assessments
                trl_gap = None
                if "trl_gap" in validated:
                    t = validated["trl_gap"]
                    trl_gap = CategoryAssessment(
                        score=t["score"],
                        confidence=t["confidence"],
                        reasoning=t["reasoning"],
                        details={
                            "inventor_implied_tier": t["inventor_implied_tier"],
                            "assessed_tier": t["assessed_tier"],
                            "evidence_fields": t["evidence_fields"],
                        },
                    )

                false_barrier = None
                if "false_barrier" in validated:
                    fb = validated["false_barrier"]
                    false_barrier = CategoryAssessment(
                        score=fb["score"],
                        confidence=fb["confidence"],
                        reasoning=fb["reasoning"],
                        details={
                            "stated_barrier": fb["stated_barrier"],
                            "rebuttal": fb["rebuttal"],
                            "barrier_source_field": fb["barrier_source_field"],
                            "market_context": fb["market_context"],
                        },
                    )

                alt_application = None
                if "alt_application" in validated:
                    alt = validated["alt_application"]
                    alt_application = CategoryAssessment(
                        score=alt["score"],
                        confidence=alt["confidence"],
                        reasoning=alt["reasoning"],
                        details={
                            "original_application": alt["original_application"],
                            "suggested_applications": alt["suggested_applications"],
                        },
                    )

                composite = self._compute_composite_score(validated, tier)

                return AssessmentResult(
                    assessment_tier=tier,
                    composite_score=composite,
                    trl_gap=trl_gap,
                    false_barrier=false_barrier,
                    alt_application=alt_application,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_cost=cost,
                    model=self.model,
                    raw_response=parsed,
                )

            except RateLimitError as e:
                logger.warning(
                    f"Rate limited (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))
                else:
                    return AssessmentError(
                        error_type="rate_limit",
                        message=str(e),
                        retryable=True,
                    )

            except APIError as e:
                logger.error(
                    f"API error (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    return AssessmentError(
                        error_type="api_error",
                        message=str(e),
                        retryable=True,
                    )

            except ValueError as e:
                logger.error(f"Parse error: {e}")
                return AssessmentError(
                    error_type="parse_error",
                    message=str(e),
                    retryable=False,
                )

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return AssessmentError(
                    error_type="unknown",
                    message=str(e),
                    retryable=False,
                )

        return AssessmentError(
            error_type="max_retries",
            message="Max retries exceeded",
            retryable=True,
        )

    async def assess_async(
        self,
        title: str,
        description: Optional[str] = None,
        raw_data: Optional[dict] = None,
    ) -> AssessmentResult | AssessmentError:
        """Async version of assess with rate limiting."""
        await self._rate_limit()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.assess, title, description, raw_data)

    async def assess_batch(
        self,
        items: list[tuple[int, str, Optional[str], Optional[dict]]],
        on_progress: Optional[callable] = None,
        max_concurrent: int = 3,
    ) -> list[tuple[int, AssessmentResult | AssessmentError]]:
        """
        Assess multiple technologies with concurrency control.

        Args:
            items: List of (id, title, description, raw_data) tuples
            on_progress: Callback for progress updates (current, total)
            max_concurrent: Maximum concurrent assessments

        Returns:
            List of (id, result) tuples
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def assess_one(
            item: tuple[int, str, Optional[str], Optional[dict]],
        ) -> tuple[int, AssessmentResult | AssessmentError]:
            async with semaphore:
                tech_id, title, description, raw_data = item
                result = await self.assess_async(title, description, raw_data)
                return (tech_id, result)

        total = len(items)
        completed = 0

        for item in items:
            result = await assess_one(item)
            results.append(result)
            completed += 1

            if on_progress:
                on_progress(completed, total)

        return results

    @property
    def stats(self) -> dict:
        """Return assessment statistics."""
        return {
            "total_assessments": self.total_assessments,
            "total_cost": round(self.total_cost, 6),
            "total_tokens": self.total_tokens,
            "average_cost_per_assessment": (
                round(self.total_cost / self.total_assessments, 6)
                if self.total_assessments > 0
                else 0
            ),
        }
