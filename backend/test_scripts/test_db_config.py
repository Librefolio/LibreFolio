"""
Test Database Configuration

Manages test database setup and teardown.
Tests should use a separate database to avoid corrupting production/development data.

Data Structure:
    backend/data/
    ├── prod/sqlite/app.db    # Production database
    └── test/sqlite/app.db    # Default test database (isolated)

The test database is automatically used when LIBREFOLIO_TEST_MODE=1.
LIBREFOLIO_TEST_DATA_DIR can assign a separate root to one runtime lane.
"""

import os
from pathlib import Path

from backend.app.config import get_settings
from scripts.cli_base import configure_test_runtime

# NOTE: Do NOT import main.py at module level - it has side effects!
# Import ensure_database_exists lazily when needed.


def get_test_database_url() -> str:
    """Return the active test lane's SQLite URL."""
    return f"sqlite:///{get_test_db_path()}"


def setup_test_database():
    """
    Configure environment to use test database.
    Must be called BEFORE importing any app modules that use DATABASE_URL.

    Returns:
        Path: Path to test database
    """
    # Ensure database directory exists
    test_db_path = get_test_db_path()
    test_db_path.parent.mkdir(parents=True, exist_ok=True)

    # Enable explicit test mode for the application BEFORE any app modules are imported.
    # This mirrors the --test flag behavior and ensures get_settings() will return
    # DATABASE_URL pointing at the test database.
    os.environ["LIBREFOLIO_TEST_MODE"] = "1"

    return test_db_path


def get_test_db_path() -> Path:
    """Get the path to test database."""
    return get_test_data_dir() / "sqlite" / "app.db"


def get_test_data_dir() -> Path:
    """Return a validated test root, including direct-script entry points."""
    _, data_dir = configure_test_runtime()
    return data_dir


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

    expected_url = get_test_database_url()
    is_test = is_test_database_configured() and db_url == expected_url
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
        print_func("⚠️  DANGER: Not using test database!")
        print_func(f"Current DATABASE_URL: {db_url}")
        print_func("Expected to contain: test_app.db")
        print_func("Aborting for safety - tests should only modify test database.")
        return False

    # Print confirmation
    print_func(f"✅ Using test database: {db_url}")

    # Ensure database exists and is migrated (lazy import to avoid side effects)
    from backend.app.main import ensure_database_exists  # noqa: PLC0415 — test setup — imports after sys.path/db config

    ensure_database_exists()
    return True
