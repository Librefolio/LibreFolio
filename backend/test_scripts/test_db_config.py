"""
Test Database Configuration

Manages test database setup and teardown.
Tests should use a separate database to avoid corrupting production/development data.

The test database URL is configured in config.py (TEST_DATABASE_URL).
Can be customized via environment variable.
"""
import os
from pathlib import Path

from backend.app.config import get_settings
from backend.app.main import ensure_database_exists

# Avoid importing app config at module import time to prevent early evaluation
# of settings (which can pick up production DATABASE_URL). Instead read TEST
# database URL from environment if provided, otherwise fall back to the default.

# Default test database URL (relative to project root)
DEFAULT_TEST_DATABASE_URL = "sqlite:///./backend/data/sqlite/test_app.db"

# Use environment override if present (allows CI or user to change path)
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)

# Extract path from URL for file operations
# Handle both sqlite:///./path and sqlite:////absolute/path
if TEST_DATABASE_URL.startswith("sqlite:///"):
    db_path_str = TEST_DATABASE_URL.replace("sqlite:///./", "").replace("sqlite:///", "/")
else:
    db_path_str = TEST_DATABASE_URL

TEST_DB_PATH = Path(db_path_str)

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

    # Enable explicit test mode for the application BEFORE any app modules are imported.
    # This mirrors the --test flag behavior and ensures get_settings() will return
    # DATABASE_URL pointing at the test database.
    os.environ["LIBREFOLIO_TEST_MODE"] = "1"

    # Set environment variable for database to the test database URL
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


def verify_test_database() -> tuple[bool, str]:
    """
    Verify that we're using the test database.

    Returns:
        tuple: (is_test_db, database_url)
    """
    # Import settings at call time so that LIBREFOLIO_TEST_MODE env var has effect
    settings = get_settings()
    db_url = settings.DATABASE_URL

    is_test = "test_app.db" in db_url or "test_app" in db_url
    return is_test, db_url


def initialize_test_database(print_func=None):
    """
    Initialize test database with safety checks.

    This function:
    1. Ensures database directory exists
    2. Verifies we're using test database (not production)
    3. Creates database schema if needed (via ensure_database_exists)
    4. Prints confirmation message

    Args:
        print_func: Optional print function (e.g., print_info from test_utils)
                   If None, uses standard print

    Returns:
        bool: True if initialization successful and using test DB, False otherwise

    Example:
        from backend.test_scripts.test_db_config import initialize_test_database
        from backend.test_scripts.test_utils import print_info

        if not initialize_test_database(print_info):
            sys.exit(1)
    """
    if print_func is None:
        print_func = print

    # Verify we're using test database
    is_test, db_url = verify_test_database()

    if not is_test:
        print_func(f"⚠️  DANGER: Not using test database!")
        print_func(f"Current DATABASE_URL: {db_url}")
        print_func(f"Expected to contain: test_app.db")
        print_func(f"Aborting for safety - tests should only modify test database.")
        return False

    # Print confirmation
    print_func(f"✅ Using test database: {db_url}")

    # Ensure database exists and is migrated
    ensure_database_exists()
    return True
