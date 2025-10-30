"""
Application configuration module.
Loads environment variables and provides application-wide settings.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings

# Get project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent


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

    class Config:
        env_file = str(PROJECT_ROOT / ".env")
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Returns:
        Settings: Application settings
    """
    return Settings()
