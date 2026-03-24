"""Embedding service for generating vector embeddings via OpenAI API."""

import time
from dataclasses import dataclass, field
from typing import Optional

import tiktoken
from loguru import logger
from openai import OpenAI, APIError, RateLimitError

from .config import settings

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
MAX_TOKENS = 8191
MAX_BATCH_SIZE = 200

# Fields from raw_data to include in the embedding text
EMBEDDING_FIELDS = [
    "applications",
    "advantages",
    "key_points",
    "market_opportunity",
    "development_stage",
]


@dataclass
class EmbeddingStats:
    """Tracks embedding batch statistics."""

    total_embedded: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    total_tokens: int = 0
    elapsed_seconds: float = 0.0


def compose_text(technology) -> Optional[str]:
    """Compose embedding text from a technology's fields.

    Returns labeled concatenation of title, description, and key raw_data fields.
    Returns None if no meaningful text can be composed.
    """
    parts = []

    if technology.title:
        parts.append(f"Title: {technology.title}")
    if technology.description:
        parts.append(f"Description: {technology.description}")

    raw_data = technology.raw_data or {}
    for field_name in EMBEDDING_FIELDS:
        value = raw_data.get(field_name)
        if not value:
            continue
        label = field_name.replace("_", " ").title()
        if isinstance(value, list):
            value = "; ".join(str(v) for v in value if v)
        if value:
            parts.append(f"{label}: {value}")

    if not parts:
        return None

    text = "\n".join(parts)

    # Truncate to MAX_TOKENS using tiktoken
    try:
        enc = tiktoken.encoding_for_model(EMBEDDING_MODEL)
        tokens = enc.encode(text)
        if len(tokens) > MAX_TOKENS:
            text = enc.decode(tokens[:MAX_TOKENS])
    except Exception:
        # If tiktoken fails, do a rough character-based truncation
        if len(text) > MAX_TOKENS * 4:
            text = text[: MAX_TOKENS * 4]

    return text


class Embedder:
    """Embedding service using OpenAI API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = EMBEDDING_MODEL,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.api_key = api_key or settings.openai_api_key
        if not self.api_key:
            raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY.")

        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.total_tokens = 0
        self.total_requests = 0

    def embed_single(self, text: str) -> list[float]:
        """Embed a single text string. Returns a 1536-dim vector."""
        result = self.embed_batch([text])
        return result[0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of 1536-dim vectors.

        Handles batching internally if texts exceeds MAX_BATCH_SIZE.
        Includes retry logic for rate limits and transient errors.
        """
        all_embeddings = []

        for i in range(0, len(texts), MAX_BATCH_SIZE):
            chunk = texts[i : i + MAX_BATCH_SIZE]
            embeddings = self._embed_chunk(chunk)
            all_embeddings.extend(embeddings)

        return all_embeddings

    def _embed_chunk(self, texts: list[str]) -> list[list[float]]:
        """Embed a single chunk of texts with retry logic."""
        for attempt in range(self.max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=texts,
                )
                self.total_tokens += response.usage.total_tokens
                self.total_requests += 1
                return [item.embedding for item in response.data]

            except RateLimitError as e:
                if attempt < self.max_retries - 1:
                    wait = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limited, waiting {wait}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait)
                else:
                    raise

            except APIError as e:
                if attempt < self.max_retries - 1:
                    wait = self.retry_delay * (2 ** attempt)
                    logger.warning(f"API error: {e}, retrying in {wait}s (attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(wait)
                else:
                    raise

    @staticmethod
    def is_configured() -> bool:
        """Check if the OpenAI API key is configured."""
        return bool(settings.openai_api_key)

    @staticmethod
    def embed_if_configured(technology) -> Optional[list[float]]:
        """Embed a technology if OpenAI is configured. Returns None if not configured or on error."""
        if not Embedder.is_configured():
            return None

        text = compose_text(technology)
        if not text:
            return None

        try:
            embedder = Embedder()
            return embedder.embed_single(text)
        except Exception as e:
            logger.warning(f"Failed to embed technology {technology.tech_id}: {e}")
            return None
