"""Base scraper class for university tech transfer sites."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import wraps
from typing import Any, AsyncIterator, Callable, Optional, TypeVar
import asyncio
import random

from loguru import logger

T = TypeVar("T")


def retry_async(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: tuple = (Exception,),
):
    """
    Decorator for retrying async functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        jitter: Add random jitter to prevent thundering herd
        exceptions: Tuple of exceptions to retry on
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {e}")
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)

                    # Add jitter
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )

                    await asyncio.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


@dataclass
class Technology:
    """Data class representing a scraped technology."""

    university: str
    tech_id: str
    title: str
    url: str
    description: Optional[str] = None
    innovators: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    raw_data: dict[str, Any] = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=_utc_now)


class BaseScraper(ABC):
    """Abstract base class for all university scrapers."""

    def __init__(
        self,
        university_code: str,
        base_url: str,
        delay_seconds: float = 1.0,
        retry_config: Optional[RetryConfig] = None,
    ):
        self.university_code = university_code
        self.base_url = base_url
        self.delay_seconds = delay_seconds
        self.retry_config = retry_config or RetryConfig()
        self._page_count = 0
        self._tech_count = 0
        self._error_count = 0

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this scraper."""
        pass

    @abstractmethod
    async def scrape(self) -> AsyncIterator[Technology]:
        """
        Scrape all technologies from the university site.

        Yields Technology objects as they are scraped.
        """
        pass

    @abstractmethod
    async def scrape_page(self, page_num: int) -> list[Technology]:
        """
        Scrape a single page of technologies.

        Args:
            page_num: The page number to scrape (1-indexed).

        Returns:
            List of Technology objects from that page.
        """
        pass

    async def delay(self) -> None:
        """Wait between requests to be respectful to the server."""
        if self.delay_seconds > 0:
            await asyncio.sleep(self.delay_seconds)

    def log_progress(self, message: str) -> None:
        """Log scraping progress."""
        logger.info(f"[{self.university_code}] {message}")

    def log_error(self, message: str, error: Optional[Exception] = None) -> None:
        """Log scraping errors."""
        if error:
            logger.error(f"[{self.university_code}] {message}: {error}")
        else:
            logger.error(f"[{self.university_code}] {message}")

    @property
    def stats(self) -> dict[str, int]:
        """Return scraping statistics."""
        return {
            "pages_scraped": self._page_count,
            "technologies_found": self._tech_count,
            "errors": self._error_count,
        }

    async def with_retry(self, coro):
        """
        Execute a coroutine with retry logic.

        Args:
            coro: Coroutine to execute

        Returns:
            Result of the coroutine
        """
        last_exception = None
        config = self.retry_config

        for attempt in range(config.max_retries + 1):
            try:
                return await coro
            except Exception as e:
                last_exception = e
                self._error_count += 1

                if attempt == config.max_retries:
                    self.log_error(f"Max retries ({config.max_retries}) exceeded", e)
                    raise

                delay = min(
                    config.base_delay * (config.exponential_base ** attempt),
                    config.max_delay,
                )

                if config.jitter:
                    delay = delay * (0.5 + random.random())

                self.log_error(
                    f"Attempt {attempt + 1}/{config.max_retries + 1} failed. Retrying in {delay:.2f}s",
                    e,
                )

                await asyncio.sleep(delay)

        raise last_exception
