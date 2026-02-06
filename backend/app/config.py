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

Environment Variables:
    LIBREFOLIO_DATA_DIR: Override data directory (default: ./backend/data/prod)
    LIBREFOLIO_TEST_MODE: When "1", use test data directory
"""

import os
from pathlib import Path

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

# Get project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Default data directories (relative to project root)
DEFAULT_PROD_DATA_DIR = PROJECT_ROOT / "backend" / "data" / "prod"
DEFAULT_TEST_DATA_DIR = PROJECT_ROOT / "backend" / "data" / "test"


# Global flag to indicate test mode (set via --test flag or LIBREFOLIO_TEST_MODE env var)
# NOTE: This is updated by set_test_mode() but is_test_mode() also checks env var


def set_test_mode(enabled: bool = True):
    """
    Enable/disable test mode globally.
    When enabled, DATABASE_URL will automatically use TEST_DATABASE_URL.

    Args:
        enabled: True to enable test mode, False to disable
    """
    os.environ["LIBREFOLIO_TEST_MODE"] = "1" if enabled else "0"

    # Reset engine singletons so they get recreated with new settings
    _reset_engine_singletons()


def _reset_engine_singletons():
    """Reset engine singletons to allow recreation with new settings."""
    # Import here to avoid circular imports
    from backend.app.db import session as session_module

    session_module.sync_engine = None
    session_module.async_engine = None


def is_test_mode() -> bool:
    """
    Check if test mode is enabled.

    Checks the environment variable directly to support dynamic switching
    (e.g., when --test-db flag is passed after module import).
    """
    return os.environ.get("LIBREFOLIO_TEST_MODE", "").lower() in ("1", "true", "yes")


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    (Note: Environment variables take precedence over .env file)
    """

    # Data directory (set dynamically based on test mode)
    # This is NOT configurable via env file - it's computed from LIBREFOLIO_DATA_DIR or test mode
    _data_dir: Path | None = None

    # Database - These are DEPRECATED, use get_database_url() instead
    # Kept for backward compatibility with alembic.ini and direct env overrides
    DATABASE_URL: str = ""  # Will be computed dynamically
    TEST_DATABASE_URL: str = ""  # DEPRECATED

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
        env_file=str(PROJECT_ROOT / ".env"), case_sensitive=True, env_file_encoding="utf-8"
    )


def get_data_dir() -> Path:
    """
    Get the current data directory based on environment and test mode.

    Priority:
    1. LIBREFOLIO_DATA_DIR env var (if set, overrides everything except test mode)
    2. Test mode: DEFAULT_TEST_DATA_DIR
    3. Production: DEFAULT_PROD_DATA_DIR

    Returns:
        Path: Absolute path to data directory
    """
    # Check for explicit override (only in prod mode)
    env_data_dir = os.environ.get("LIBREFOLIO_DATA_DIR")

    if is_test_mode():
        # Test mode ALWAYS uses test data dir (no override possible)
        return DEFAULT_TEST_DATA_DIR
    elif env_data_dir:
        # Custom data dir specified via env var
        path = Path(env_data_dir)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path
    else:
        # Default production data dir
        return DEFAULT_PROD_DATA_DIR


def get_database_url() -> str:
    """
    Get the database URL based on current data directory.

    Returns:
        str: SQLite database URL
    """
    data_dir = get_data_dir()
    db_path = data_dir / "sqlite" / "app.db"
    return f"sqlite:///{db_path}"


def get_settings() -> Settings:
    """
    Get settings instance.

    DATABASE_URL is computed dynamically based on test mode and data directory.
    LIBREFOLIO_LOG_LEVEL env var overrides LOG_LEVEL setting.

    Returns:
        Settings: Application settings
    """
    settings = Settings()

    # Compute DATABASE_URL dynamically
    settings.DATABASE_URL = get_database_url()

    # Override LOG_LEVEL from LIBREFOLIO_LOG_LEVEL env var (for dev.py --debug)
    log_level_override = os.environ.get("LIBREFOLIO_LOG_LEVEL")
    if log_level_override:
        settings.LOG_LEVEL = log_level_override.upper()

    return settings


def ensure_data_dirs() -> None:
    """
    Ensure all data directories exist.
    Called at application startup to create directories if needed.
    """
    data_dir = get_data_dir()

    dirs_to_create = [
        data_dir / "sqlite",
        data_dir / "custom-uploads",
        data_dir / "broker_reports" / "uploaded",
        data_dir / "broker_reports" / "parsed",
        data_dir / "broker_reports" / "failed",
        data_dir / "logs",
    ]

    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)

