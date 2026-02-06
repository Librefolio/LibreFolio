"""
Test Database Configuration

Manages test database setup and teardown.
Tests should use a separate database to avoid corrupting production/development data.

Data Structure:
    backend/data/
    ├── prod/sqlite/app.db    # Production database
    └── test/sqlite/app.db    # Test database (isolated)

The test database is automatically used when LIBREFOLIO_TEST_MODE=1.
"""

import os
from pathlib import Path

from backend.app.config import DEFAULT_TEST_DATA_DIR, get_settings

# NOTE: Do NOT import main.py at module level - it has side effects!
# Import ensure_database_exists lazily when needed.

# Test data directory and database path
TEST_DATA_DIR = DEFAULT_TEST_DATA_DIR
TEST_DB_PATH = TEST_DATA_DIR / "sqlite" / "app.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

# Database directory
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
    """Check if test database is configured (test mode is enabled)."""
    return os.environ.get("LIBREFOLIO_TEST_MODE", "").lower() in ("1", "true", "yes")


def verify_test_database() -> tuple[bool, str]:
    """
    Verify that we're using the test database.

    Returns:
        tuple: (is_test_db, database_url)
    """
    # Import settings at call time so that LIBREFOLIO_TEST_MODE env var has effect
    settings = get_settings()
    db_url = settings.DATABASE_URL

    # Check if path contains "test" data directory
    is_test = "/data/test/" in db_url or is_test_database_configured()
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

    # Ensure database exists and is migrated (lazy import to avoid side effects)
    from backend.app.main import ensure_database_exists
    ensure_database_exists()
    return True
