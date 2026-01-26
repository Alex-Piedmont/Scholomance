"""Configuration settings for the university tech scraper."""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/tech_transfer",
        alias="DATABASE_URL",
    )
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="tech_transfer", alias="POSTGRES_DB")
    postgres_user: str = Field(default="user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="password", alias="POSTGRES_PASSWORD")

    # Anthropic API
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Scraper settings
    scrape_delay_seconds: float = Field(default=1.0, alias="SCRAPE_DELAY_SECONDS")
    max_concurrent_requests: int = Field(default=3, alias="MAX_CONCURRENT_REQUESTS")
    request_timeout: int = Field(default=30, alias="REQUEST_TIMEOUT")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, alias="LOG_FILE")

    # Email notifications (for scheduler)
    smtp_host: Optional[str] = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, alias="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, alias="SMTP_PASSWORD")
    notification_email: Optional[str] = Field(default=None, alias="NOTIFICATION_EMAIL")

    # Retry settings
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    retry_delay: float = Field(default=5.0, alias="RETRY_DELAY")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def get_database_url(self) -> str:
        """Get the database URL, building from components if not set."""
        if self.database_url and "postgresql://" in self.database_url:
            return self.database_url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# Global settings instance
settings = Settings()
