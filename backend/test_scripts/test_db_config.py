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
from backend.app.main import ensure_database_exists

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


def verify_test_database() -> tuple[bool, str]:
    """
    Verify that we're using the test database.

    Returns:
        tuple: (is_test_db, database_url)
    """
    from backend.app.config import get_settings
    settings = get_settings()
    db_url = settings.DATABASE_URL

    is_test = "test_app.db" in db_url
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
