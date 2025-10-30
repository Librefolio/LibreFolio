"""
Test Database Configuration

Manages test database setup and teardown.
Tests should use a separate database to avoid corrupting production/development data.

The test database URL is configured in config.py (TEST_DATABASE_URL).
Can be customized via environment variable.
"""
import os
from pathlib import Path

# Import settings to get TEST_DATABASE_URL
from backend.app.config import Settings

# Get settings
_settings = Settings()

# Test database URL (from config, e.g., "sqlite:///./backend/data/sqlite/test_app.db")
TEST_DATABASE_URL = _settings.TEST_DATABASE_URL

# Extract path from URL for file operations
# sqlite:///./backend/data/sqlite/test_app.db -> backend/data/sqlite/test_app.db
TEST_DB_PATH = Path(_settings.TEST_DATABASE_URL.replace("sqlite:///./", "").replace("sqlite:///", "/"))

# Project root and database directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_DIR = TEST_DB_PATH.parent


def setup_test_database():
    """
    Configure environment to use test database.
    Must be called BEFORE importing any app modules that use DATABASE_URL.

    Returns:
        Path: Path to test database
    """
    # Ensure database directory exists
    DB_DIR.mkdir(parents=True, exist_ok=True)

    # Set environment variable for test database (use URL from config)
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    return TEST_DB_PATH


def cleanup_test_database():
    """
    Remove test database after tests complete.
    """
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


def get_test_db_path() -> Path:
    """Get the path to test database."""
    return TEST_DB_PATH


def is_test_database_configured() -> bool:
    """Check if test database is configured."""
    db_url = os.environ.get("DATABASE_URL", "")
    return db_url == TEST_DATABASE_URL

