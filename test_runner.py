#!/usr/bin/env python3
"""
LibreFolio Test Runner

Central test orchestrator for running backend and frontend tests.
Organized into test categories with specific sub-commands.

Test Categories:
  - db:  Database layer tests (SQLite file only, no backend server)
  - api: API endpoint tests (requires running backend server)

Author: LibreFolio Contributors
"""

import argparse
import subprocess
import sys
from pathlib import Path


# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'  # No Color


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.CYAN}{'=' * 70}{Colors.NC}")
    print(f"{Colors.CYAN}{text:^70}{Colors.NC}")
    print(f"{Colors.CYAN}{'=' * 70}{Colors.NC}\n")


def print_section(text: str):
    """Print a section title."""
    print(f"\n{Colors.BLUE}{'▶' * 3} {text}{Colors.NC}")
    print(f"{Colors.BLUE}{'-' * 70}{Colors.NC}")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.NC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.NC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.NC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.MAGENTA}ℹ️  {text}{Colors.NC}")


def run_command(cmd: list[str], description: str) -> bool:
    """
    Run a command and return True if successful.

    Args:
        cmd: Command to run as list
        description: Description for logging

    Returns:
        bool: True if command succeeded
    """
    print(f"\n{Colors.BLUE}Running: {description}{Colors.NC}")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=False,
            text=True,
        )

        if result.returncode == 0:
            print_success(f"{description} - PASSED")
            return True
        else:
            print_error(f"{description} - FAILED (exit code: {result.returncode})")
            return False

    except Exception as e:
        print_error(f"{description} - ERROR: {e}")
        return False


# ============================================================================
# DATABASE TESTS
# ============================================================================

def db_create() -> bool:
    """
    Create fresh database.
    Removes existing database and creates a new one from migrations.
    """
    print_section("Database Creation")
    print_info("This test operates on: backend/data/sqlite/app.db")
    print_info("The backend server is NOT used in this test")

    db_path = Path(__file__).parent / "backend" / "data" / "sqlite" / "app.db"

    # Remove existing database
    if db_path.exists():
        print_warning(f"Removing existing database: {db_path}")
        db_path.unlink()
        print_success("Database removed")
    else:
        print_info("No existing database found")

    # Create fresh database
    print("\nCreating fresh database from migrations...")
    success = run_command(
        ["./dev.sh", "db:upgrade"],
        "Create database via Alembic migrations"
    )

    if success:
        print_success("Database created successfully")
    else:
        print_error("Database creation failed")

    return success


def db_validate() -> bool:
    """
    Validate database schema.
    Checks that all expected tables, constraints, indexes exist.
    """
    print_section("Database Schema Validation")
    print_info("This test operates on: backend/data/sqlite/app.db")
    print_info("The backend server is NOT used in this test")
    print_info("Testing: Tables, Foreign Keys, Constraints, Indexes, Enums")

    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_db.db_schema_validate"],
        "Schema validation"
    )


def db_populate() -> bool:
    """
    Populate database with test data and verify.
    Inserts sample data and runs queries to verify integrity.
    """
    print_section("Database Population & Query Verification")
    print_info("This test operates on: backend/data/sqlite/app.db")
    print_info("The backend server is NOT used in this test")
    print_info("Testing: Data insertion, Queries, Relationships, Constraints")

    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_db.populate_db"],
        "Database population and query verification"
    )


def db_all() -> bool:
    """
    Run all database tests in sequence.
    """
    print_header("LibreFolio Database Tests")
    print_info("Testing the database layer (SQLite file)")
    print_info("Backend server is NOT required for these tests")
    print_info("Target: backend/data/sqlite/app.db")

    # Test order matters!
    tests = [
        ("Create Fresh Database", db_create),
        ("Validate Schema", db_validate),
        ("Populate & Query Verification", db_populate),
    ]

    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))

        if not success:
            print_error(f"Test failed: {test_name}")
            print_warning("Stopping test execution")
            break

    # Summary
    print_section("Database Test Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if success else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print_success("All database tests passed! 🎉")
        return True
    else:
        print_error(f"{total - passed} test(s) failed")
        return False


# ============================================================================
# API TESTS
# ============================================================================

def api_test() -> bool:
    """
    Run API tests (placeholder for now).
    """
    print_section("API Tests")
    print_info("Testing REST API endpoints")
    print_info("Requires: Running backend server on http://localhost:8000")
    print_warning("API tests are not implemented yet")
    print()
    print("These tests will verify:")
    print("  • HTTP endpoints respond correctly")
    print("  • Request/response validation")
    print("  • Authentication/authorization")
    print("  • Error handling")
    print("  • Data integrity through API")
    print()
    print_info("Coming soon in the next development phase!")

    return True  # Return True for now (not implemented)


# ============================================================================
# MAIN ARGUMENT PARSER
# ============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="LibreFolio Test Runner - Organized test execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Categories:
  
  db   - Database Layer Tests
         Tests the SQLite database file directly without backend server.
         Verifies: schema, constraints, data integrity, queries.
         Target: backend/data/sqlite/app.db
  
  api  - API Endpoint Tests  
         Tests REST API endpoints (requires running backend server).
         Verifies: HTTP endpoints, validation, authentication, errors.
         Target: http://localhost:8000

Examples:
  # Database tests (no backend server needed)
  python test_runner.py db create       # Create fresh database
  python test_runner.py db validate     # Validate schema
  python test_runner.py db populate     # Populate and verify queries
  python test_runner.py db all          # Run all DB tests
  
  # API tests (requires backend server running)
  python test_runner.py api test        # Run API tests (not implemented yet)
  
  # Quick shortcuts
  ./dev.sh test db all                  # Via dev.sh wrapper
  ./dev.sh test api test                # Via dev.sh wrapper
        """
    )

    subparsers = parser.add_subparsers(
        dest="category",
        help="Test category to run",
        required=True
    )

    # ========================================================================
    # DATABASE TESTS SUBPARSER
    # ========================================================================
    db_parser = subparsers.add_parser(
        "db",
        help="Database layer tests (SQLite file, no backend)",
        description="""
Database Layer Tests

These tests operate directly on the SQLite database file:
  • Target: backend/data/sqlite/app.db
  • No backend server required
  • Tests Python database functions that will be used by the backend

Test commands:
  create   - Delete existing DB and create fresh from migrations
  validate - Verify all tables, constraints, indexes, foreign keys
  populate - Insert test data and verify with queries
  all      - Run all tests in sequence (create → validate → populate)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    db_parser.add_argument(
        "action",
        choices=["create", "validate", "populate", "all"],
        help="Database test to run"
    )

    # ========================================================================
    # API TESTS SUBPARSER
    # ========================================================================
    api_parser = subparsers.add_parser(
        "api",
        help="API endpoint tests (requires backend server)",
        description="""
API Endpoint Tests

These tests verify REST API endpoints:
  • Target: http://localhost:8000
  • Requires backend server running (./dev.sh server)
  • Tests HTTP requests/responses, validation, authentication

Test commands:
  test - Run API endpoint tests (NOT IMPLEMENTED YET)
  
Note: Start the backend server first with './dev.sh server'
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    api_parser.add_argument(
        "action",
        choices=["test"],
        help="API test to run"
    )

    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Route to appropriate test handler
    success = False

    if args.category == "db":
        # Database tests
        if args.action == "create":
            success = db_create()
        elif args.action == "validate":
            success = db_validate()
        elif args.action == "populate":
            success = db_populate()
        elif args.action == "all":
            success = db_all()

    elif args.category == "api":
        # API tests
        if args.action == "test":
            success = api_test()

    # Exit with appropriate code
    return 0 if success else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}⚠️  Test execution interrupted by user{Colors.NC}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

