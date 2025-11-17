"""
Application configuration module.
Loads environment variables and provides application-wide settings.
"""
import os
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# Get project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Global flag to indicate test mode (set via --test flag or LIBREFOLIO_TEST_MODE env var)
_test_mode = os.environ.get("LIBREFOLIO_TEST_MODE", "").lower() in ("1", "true", "yes")


def set_test_mode(enabled: bool = True):
    """
    Enable/disable test mode globally.
    When enabled, DATABASE_URL will automatically use TEST_DATABASE_URL.

    Args:
        enabled: True to enable test mode, False to disable
    """
    global _test_mode
    _test_mode = enabled
    os.environ["LIBREFOLIO_TEST_MODE"] = "1" if enabled else "0"


def is_test_mode() -> bool:
    """Check if test mode is enabled."""
    return _test_mode


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    (Note: Environment variables take precedence over .env file)
    """
    # Database
    DATABASE_URL: str = "sqlite:///./backend/data/sqlite/app.db"
    TEST_DATABASE_URL: str = "sqlite:///./backend/data/sqlite/test_app.db"  # Test database (same dir as app.db)

    # API
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "LibreFolio"
    VERSION: str = "0.1.0"

    # Server
    PORT: int = 8000  # Main server port (production/development)
    TEST_PORT: int = 8001  # Test server port (used during automated tests)

    # Logging
    LOG_LEVEL: str = "INFO"

    # Portfolio
    PORTFOLIO_BASE_CURRENCY: str = "EUR"  # ISO 4217 currency code

    # CORS (for frontend development)
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    model_config = ConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        case_sensitive=True,
        env_file_encoding='utf-8'
        )


def get_settings() -> Settings:
    """
    Get settings instance.

    In test mode, DATABASE_URL is automatically overridden with TEST_DATABASE_URL.

    Returns:
        Settings: Application settings
    """
    settings = Settings()

    # Override DATABASE_URL if in test mode
    if is_test_mode():
        settings.DATABASE_URL = settings.TEST_DATABASE_URL

    return settings
