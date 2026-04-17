"""
Application configuration module.
Loads environment variables and provides application-wide settings.

Data Directory Structure:
    backend/data/
    ├── prod/                    # Production data
    │   ├── sqlite/app.db
    │   ├── custom-uploads/
    │   ├── broker_reports/{uploaded,parsed,failed}/
    │   └── logs/
    └── test/                    # Test data (isolated)
        ├── sqlite/app.db
        ├── custom-uploads/
        ├── broker_reports/{uploaded,parsed,failed}/
        └── logs/

Environment Variables (see .env):
    LIBREFOLIO_DATA_DIR: Override production data directory (default: ./backend/data/prod)
    LIBREFOLIO_TEST_MODE: When "1", use test data directory (backend/data/test/)
    PORT: Production server port (default: 8000)
    TEST_PORT: Test server port (default: 8001)
    LOG_LEVEL: Logging level (default: INFO)
    PORTFOLIO_BASE_CURRENCY: Base currency ISO 4217 (default: EUR)
    PREVIEW_CACHE_MAX_MB: Image preview cache size in MB (default: 50)
    BACKEND_CORS_ORIGINS: CORS origins for frontend dev (default: localhost:3000, localhost:5173)
"""

import os
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# =============================================================================
# Constants (not configurable via .env — change here if needed)
# =============================================================================
PROJECT_NAME: str = "LibreFolio"
API_V1_PREFIX: str = "/api/v1"

# Get project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Default data directories (relative to project root)
DEFAULT_PROD_DATA_DIR = PROJECT_ROOT / "backend" / "data" / "prod"
DEFAULT_TEST_DATA_DIR = PROJECT_ROOT / "backend" / "data" / "test"


# =============================================================================
# Test mode management
# =============================================================================


def set_test_mode(enabled: bool = True):
    """
    Enable/disable test mode globally.
    When enabled, data directory switches to backend/data/test/.
    """
    os.environ["LIBREFOLIO_TEST_MODE"] = "1" if enabled else "0"
    _reset_engine_singletons()


def _reset_engine_singletons():
    """Reset engine singletons to allow recreation with new settings."""
    from backend.app.db import session as session_module

    session_module.sync_engine = None
    session_module.async_engine = None


def is_test_mode() -> bool:
    """
    Check if test mode is enabled.
    Checks env var directly to support dynamic switching.
    """
    return os.environ.get("LIBREFOLIO_TEST_MODE", "").lower() in ("1", "true", "yes")


# =============================================================================
# Settings model (loaded from .env)
# =============================================================================


class Settings(BaseSettings):
    """
    Application settings loaded from .env file.
    Environment variables take precedence over .env values.

    NOTE: DATABASE_URL is computed dynamically by get_settings(),
    it is NOT read from .env.
    """

    # Database URL — computed dynamically, do NOT set in .env
    DATABASE_URL: str = ""

    # Server
    PORT: int = 8000
    TEST_PORT: int = 8001

    # Logging
    LOG_LEVEL: str = "INFO"

    # Portfolio
    PORTFOLIO_BASE_CURRENCY: str = "EUR"

    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Image Preview Cache
    PREVIEW_CACHE_MAX_MB: int = 50

    model_config = ConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        case_sensitive=True,
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore env vars not defined as fields (e.g. LIBREFOLIO_DATA_DIR)
    )


# =============================================================================
# Data directory resolution
# =============================================================================


def get_data_dir() -> Path:
    """
    Get the current data directory based on environment and test mode.

    Priority:
    1. Test mode → ALWAYS backend/data/test/ (no override)
    2. LIBREFOLIO_DATA_DIR env var → custom path
    3. Default → backend/data/prod/
    """
    if is_test_mode():
        return DEFAULT_TEST_DATA_DIR

    env_data_dir = os.environ.get("LIBREFOLIO_DATA_DIR")
    if env_data_dir:
        path = Path(env_data_dir)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    return DEFAULT_PROD_DATA_DIR


def get_database_url() -> str:
    """Get the SQLite database URL based on current data directory."""
    db_path = get_data_dir() / "sqlite" / "app.db"
    return f"sqlite:///{db_path}"


def get_version() -> str:
    """
    Get application version from git tags.
    Same logic as ./dev.py info version and frontend APP_VERSION.
    """
    from backend.app.utils.version import get_git_version

    return get_git_version()


def get_settings() -> Settings:
    """
    Get settings instance with computed fields.

    DATABASE_URL is computed dynamically based on test mode and data directory.
    LOG_LEVEL can be overridden by LIBREFOLIO_LOG_LEVEL env var.
    """
    settings = Settings()
    settings.DATABASE_URL = get_database_url()

    log_level_override = os.environ.get("LIBREFOLIO_LOG_LEVEL")
    if log_level_override:
        settings.LOG_LEVEL = log_level_override.upper()

    return settings


def ensure_data_dirs() -> None:
    """
    Ensure all data directories exist.
    Called at application startup.
    """
    data_dir = get_data_dir()
    for subdir in [
        "sqlite",
        "custom-uploads",
        "broker_reports/uploaded",
        "broker_reports/parsed",
        "broker_reports/failed",
        "logs",
    ]:
        (data_dir / subdir).mkdir(parents=True, exist_ok=True)
