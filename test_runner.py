#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
"""
LibreFolio Test Runner

Central test orchestrator for running backend and frontend tests.
Organized into logical test categories with specific sub-commands.

⚠️  NOTE: This is NOT a pytest module!
    This is a standalone test orchestrator that runs test scripts.
    Run it directly: python test_runner.py [category] [action]
    Do NOT run with pytest.

Test Categories:
  - external: External service integrations (ECB, yfinance, etc.)
  - db:       Database layer tests (schema, constraints, persistence)
  - services: Backend service logic (conversions, calculations)
  - api:      REST API endpoint tests (requires running server)

Author: LibreFolio Contributors
"""

import argparse
import argcomplete
import subprocess
import sys
import traceback
from pathlib import Path

# Setup test database configuration and get test database path
from backend.test_scripts.test_db_config import setup_test_database, TEST_DB_PATH, TEST_DATABASE_URL
# Import test utilities (avoid code duplication)
from backend.test_scripts.test_utils import (Colors, print_header, print_section, print_success, print_error, print_warning, print_info)


def run_command(cmd: list[str], description: str, verbose: bool = False) -> bool:
    """
    Run a command and return True if successful.

    Args:
        cmd: Command to run as list
        description: Description for logging
        verbose: If True, show full command output (like calling script directly)

    Returns:
        bool: True if command succeeded
    """
    print(f"\n{Colors.BLUE}Running: {description}{Colors.NC}")
    print(f"Command: {' '.join(cmd)}")

    try:
        # Ensure test subprocesses run in test mode when invoking test scripts
        env = None
        try:
            # If the command invokes our test scripts via pipenv/python module, force test env
            if any('backend.test_scripts' in c or c.endswith('.py') and 'backend/test_scripts' in c for c in cmd):
                env = os.environ.copy()
                env['LIBREFOLIO_TEST_MODE'] = '1'
                env['DATABASE_URL'] = TEST_DATABASE_URL
        except Exception:
            env = None

        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent,
            capture_output=not verbose,  # Capture only if not verbose
            text=True,
            env=env,
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
# EXTERNAL SERVICES TESTS
# ============================================================================

def external_fx_source(verbose: bool = False) -> bool:
    """
    Test all registered FX providers (ECB, FED, BOE, etc.).
    Tests external integration with central bank APIs.
    """
    print_section("External: FX Providers")
    print_info("Testing all registered FX rate providers")
    print_info("Tests: Metadata, API connection, rate fetching, normalization")

    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_external.test_fx_providers"],
        "FX providers tests",
        verbose=verbose
        )


def external_fx_multi_unit(verbose: bool = False) -> bool:
    """
    Test multi-unit currency handling (JPY, SEK, NOK, DKK).
    Validates correct 100x inversion logic.
    """
    print_section("External: Multi-Unit Currencies")
    print_info("Testing multi-unit currency handling (JPY, SEK, NOK, DKK)")
    print_info("Tests: Identification, rate reasonableness, calculation consistency")

    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_external.test_fx_multi_unit"],
        "Multi-unit currency tests",
        verbose=verbose
        )


def external_asset_providers(verbose: bool = False) -> bool:
    """
    Test all registered asset pricing providers (yfinance, cssscraper, etc.).
    Tests external integration with data sources.
    """
    print_section("External: Asset Providers")
    print_info("Testing all registered asset pricing providers")
    print_info("Tests: Metadata, API connection, current/historical data fetching, search")

    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_external.test_asset_providers"],
        "Asset providers tests",
        verbose=verbose
        )


def external_all(verbose: bool = False) -> bool:
    """
    Run all external service tests.
    """
    print_header("LibreFolio External Services Tests")
    print_info("Testing external API integrations")
    print_info("No backend server required")

    tests = [
        ("External Forex data import API", lambda: external_fx_source(verbose)),
        ("Multi-Unit Currency Handling", lambda: external_fx_multi_unit(verbose)),
        ("Asset Pricing Providers", lambda: external_asset_providers(verbose)),
        # Future: yfinance, other data sources
        ]

    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))

        if not success:
            print_error(f"Test failed: {test_name}")
            print_warning("Stopping external tests execution")
            break

    # Summary
    print_section("External Services Test Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if success else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print_success("All external services tests passed! 🎉")
        return True
    else:
        print_error(f"{total - passed} test(s) failed")
        return False


# ============================================================================
# DATABASE TESTS
# ============================================================================

def db_create(verbose: bool = False) -> bool:
    """
    Create fresh database.
    Removes existing database and creates a new one from migrations.
    """
    print_section("Database Creation")

    setup_test_database()

    print_info(f"This test operates on: {TEST_DB_PATH}")
    print_info("The backend server is NOT used in this test")

    # Remove existing test database
    if TEST_DB_PATH.exists():
        print_warning(f"Removing existing test database: {TEST_DB_PATH}")
        TEST_DB_PATH.unlink()
        print_success("Test database removed")
    else:
        print_info("No existing test database found")

    # Create fresh test database
    print("\nCreating fresh test database from migrations...")

    # Pass database path directly to dev.sh (it will convert to URL internally)
    success = run_command(
        ["./dev.sh", "db:upgrade", str(TEST_DB_PATH)],
        "Create database via Alembic migrations",
        verbose=verbose
        )

    if success:
        # Verify database file exists
        if TEST_DB_PATH.exists():
            print_success(f"Test database created successfully: {TEST_DB_PATH}")
            print_info(f"Database file size: {TEST_DB_PATH.stat().st_size} bytes")
        else:
            print_error(f"Test database file not found at: {TEST_DB_PATH}")
            print_error("Migration succeeded but database file was not created")
            success = False
    else:
        print_error("Test database creation failed")

    return success


def db_validate(verbose: bool = False) -> bool:
    """
    Validate database schema.
    Checks that all expected tables, constraints, indexes exist.
    """
    print_section("Database Schema Validation")

    print_info(f"This test operates on: {TEST_DB_PATH}")
    print_info("The backend server is NOT used in this test")
    print_info("Testing: Tables, Foreign Keys, Constraints, Indexes, Enums")

    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_db.db_schema_validate"],
        "Schema validation",
        verbose=verbose
        )


def db_populate(verbose: bool = False, force: bool = False) -> bool:
    """
    Populate database with mock data for testing.
    Inserts comprehensive sample data (useful for frontend development).

    Args:
        verbose: Show verbose output
        force: Delete existing database and recreate from scratch
    """
    print_section("Database Mock Data Population")

    print_info(f"This test operates on: {TEST_DB_PATH}")
    print_info("The backend server is NOT used in this test")
    print_info("⚠️  Populating MOCK DATA for testing purposes")

    if force:
        print_warning("--force flag detected: Will DELETE existing data")

    cmd = ["pipenv", "run", "python", "-m", "backend.test_scripts.test_db.populate_mock_data"]
    if force:
        cmd.append("--force")

    success = run_command(
        cmd,
        "Mock data population",
        verbose=verbose
        )

    # If failed and not verbose, provide helpful hint
    if not success and not verbose:
        print_warning("\n💡 Hint: Database might already contain data")
        print_info("   Run with -v to see detailed error:")
        print_info(f"     python test_runner.py -v db populate")
        print_info("   Or use --force to delete and recreate:")
        print_info(f"     python test_runner.py db populate --force")

    return success


def db_fx_rates(verbose: bool = False) -> bool:
    """
    Test FX rates persistence in database.
    Tests fetching rates from ECB and persisting to database.
    """
    print_section("DB Test: FX Rates Persistence")

    print_info(f"This test operates on: {TEST_DB_PATH} (test database)")
    print_info("Testing: Fetch rates, Persist to DB, Overwrite, Idempotency, Constraints")

    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_db.test_fx_rates_persistence"],
        "FX rates persistence tests",
        verbose=verbose
        )


def db_numeric_truncation(verbose: bool = False) -> bool:
    """
    Test Numeric column truncation behavior across all tables.
    Validates helper functions and database precision handling.
    """
    print_section("DB Test: Numeric Column Truncation")
    print_info("Testing all Numeric columns in database")
    print_info("Tests: Helper functions, DB truncation, No false updates")

    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_db.test_numeric_truncation"],
        "Numeric truncation tests",
        verbose=verbose
        )


def db_all(verbose: bool = False) -> bool:
    """
    Run all database tests in sequence.
    """
    print_header("LibreFolio Database Tests")
    print_info("Testing the database layer (SQLite file)")
    print_info("Backend server is NOT required for these tests")
    print_info("Target: backend/data/sqlite/test_app.db")

    # Test order matters!
    # Note: populate comes before fx-rates because:
    #   - populate requires empty DB (or --force to delete)
    #   - fx-rates can run on DB with existing data (uses UPSERT)
    tests = [
        ("Create Fresh Database", lambda: db_create(verbose)),
        ("Validate Schema", lambda: db_validate(verbose)),
        ("Numeric Truncation", lambda: db_numeric_truncation(verbose)),
        ("Populate Mock Data", lambda: db_populate(verbose, force=True)),  # Use force in 'all' mode
        ("FX Rates Persistence", lambda: db_fx_rates(verbose)),
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
# SERVICES TESTS
# ============================================================================

def services_fx_conversion(verbose: bool = False) -> bool:
    """
    Test FX conversion service logic.
    Tests currency conversion algorithms (direct, inverse, roundtrip, different dates, forward-fill).
    Mock FX rates are automatically inserted across multiple dates.
    """
    print_section("Services: FX Conversion Logic")
    print_info("Testing: backend/app/services/fx.py convert() function")
    print_info("Scenarios: Identity, Direct, Inverse, Roundtrip, Different Dates, Forward-fill")
    print_info("Safety: Verifies test database usage before modifying data")
    print_info("Note: Mock FX rates automatically inserted for 3 dates")

    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_services.test_fx_conversion"],
        "FX conversion service tests",
        verbose=verbose
        )


def services_asset_source(verbose: bool = False) -> bool:
    """
    Test Asset Source service logic.
    Tests provider assignment (bulk/single), helper functions, and synthetic yield calculation.
    """
    print_section("Services: Asset Source Logic")
    print_info("Testing: backend/app/services/asset_source.py")
    print_info("Tests: Helper functions, Provider assignment, Synthetic yield")
    print_info("Note: Test assets automatically created and cleaned up")

    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_services.test_asset_source"],
        "Asset source service tests",
        verbose=verbose
        )


def services_asset_source_refresh(verbose: bool = False) -> bool:
    """
    Smoke test: Asset Source refresh orchestration.
    Runs the lightweight refresh orchestration smoke test which uses a mock provider.
    """
    print_section("Services: Asset Source Refresh (smoke)")
    print_info("Testing: backend/app/services/asset_source bulk refresh orchestration (smoke)")
    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_services.test_asset_source_refresh"],
        "Asset source refresh smoke test",
        verbose=verbose
        )


def services_synthetic_yield(verbose: bool = False) -> bool:
    """
    Test synthetic yield calculation for SCHEDULED_YIELD assets.
    Tests runtime valuation for crowdfunding loans, bonds, etc.
    """
    print_section("Services: Synthetic Yield Calculation")
    print_info("Testing: SCHEDULED_YIELD asset valuation (ACT/365 SIMPLE interest)")
    print_info("Covers: Rate lookup, accrued interest, full valuation, DB integration")
    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_services.test_synthetic_yield"],
        "Synthetic yield tests",
        verbose=verbose
        )


def services_all(verbose: bool = False) -> bool:
    """
    Run all backend service tests.
    """
    print_header("LibreFolio Backend Services Tests")
    print_info("Testing business logic and service layer")
    print_info("No backend server required")

    tests = [
        ("FX Conversion Logic", lambda: services_fx_conversion(verbose)),
        ("Asset Source Logic", lambda: services_asset_source(verbose)),
        ("Synthetic Yield Calculation", lambda: services_synthetic_yield(verbose)),
        # Future: FIFO calculations, portfolio aggregations, etc.
        ]

    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))

        if not success:
            print_error(f"Test failed: {test_name}")
            print_warning("Stopping services tests execution")
            break

    # Summary
    print_section("Backend Services Test Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if success else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print_success("All backend services tests passed! 🎉")
        return True
    else:
        print_error(f"{total - passed} test(s) failed")
        return False


# ============================================================================
# API TESTS
# ============================================================================

def api_fx(verbose: bool = False) -> bool:
    """
    Run FX API endpoint tests.
    """
    print_section("FX API Endpoint Tests")
    print_info("Testing REST API endpoints for FX functionality")
    print_info("Note: Server will be automatically started and stopped by test")

    return run_command(
        ["pipenv", "run", "python", "-m", "backend.test_scripts.test_api.test_fx_api"],
        "FX API tests",
        verbose=verbose
        )


def api_test(verbose: bool = False) -> bool:
    """
    Run all API tests.
    """
    print_header("LibreFolio API Tests")
    print_info("Testing REST API endpoints")
    print_info("Requires: Running backend server on http://localhost:8000")
    print_warning("⚠️  Start server before running: ./dev.sh server\n")

    # For now, only FX API tests exist
    return api_fx(verbose=verbose)


# ============================================================================
# GLOBAL ALL TESTS
# ============================================================================

def run_all_tests(verbose: bool = False) -> bool:
    """
    Run ALL tests in the optimal order.

    Order:
      1. External services (ECB API, etc.)
      2. Database (schema, persistence)
      3. Backend services (conversion logic, calculations)
      4. API endpoints (REST API - auto-starts test server on port 8001)

    Note: API tests will automatically start and stop the test server.
          If port 8001 is occupied, tests will fail with helpful instructions.
    """
    print_header("LibreFolio Complete Test Suite")
    print_info("Running all test categories in optimal order")
    print_info("This will take a few minutes...\n")

    # Define test categories in order
    test_categories = [
        ("External Services", lambda: external_all(verbose)),
        ("Database Layer", lambda: db_all(verbose)),
        ("Backend Services", lambda: services_all(verbose)),
        ("API Endpoints", lambda: api_test(verbose)),  # Auto-starts server via TestServerManager
        ]

    results = []
    for category_name, test_func in test_categories:
        print(f"\n{'=' * 70}")
        print(f"Starting: {category_name}")
        print('=' * 70)

        success = test_func()
        results.append((category_name, success))

        if not success:
            print_error(f"\nCategory failed: {category_name}")
            print_warning("Stopping complete test suite execution")
            print_info("Fix the failing tests before continuing")
            break

    # Global Summary
    print_section("Complete Test Suite Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for category_name, success in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if success else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status} - {category_name}")

    print(f"\nResults: {passed}/{total} categories passed")

    if passed == total:
        print_success("\n🎉 ALL TESTS PASSED! 🎉")
        print_info("Your LibreFolio instance is working correctly!")
        return True
    else:
        print_error(f"\n{total - passed} category(ies) failed")
        return False


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
  
  external - External Services Tests
             Tests external API integrations (no backend server needed).
             Verifies: External Forex API, yfinance, other data sources.
  
  db       - Database Layer Tests
             Tests the SQLite database file directly (no backend server needed).
             Verifies: schema, constraints, data integrity, persistence.
             Target: backend/data/sqlite/app.db
  
  services - Backend Services Tests
             Tests business logic and service layer (no backend server needed).
             Verifies: conversions, calculations, algorithms.
  
  api      - API Endpoint Tests  
             Tests REST API endpoints (requires running backend server).
             Verifies: HTTP endpoints, validation, error handling.
             Target: http://localhost:8000
  
  all      - Run ALL tests in optimal order

Examples:
  # Run everything
  python test_runner.py all                 # All tests (optimal order)
  python test_runner.py -v all              # All tests with all log
  
  # Quick shortcuts via dev.sh
  ./dev.sh test all                         # Run complete test suite
  ./dev.sh test db all                      # All database tests
        """
        )

    # Global flags
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show full test output (like calling test scripts directly)",
        default=False
        )

    subparsers = parser.add_subparsers(
        dest="category",
        help="Test category to run",
        required=False  # Allow 'all' without category
        )

    # ========================================================================
    # EXTERNAL SERVICES TESTS SUBPARSER
    # ========================================================================
    external_parser = subparsers.add_parser(
        "external",
        help="External service integration tests (no backend server)",
        description="""
External Services Tests

These tests verify external API integrations:
  • No backend server required
  • Tests connections for Forex data source like ECB, FED, BOE, SNB and other
  • Tests connections for Asset data source like YahooFinance, CssScraper and other
  • Verifies data availability and format

Test commands:
  fx-source      - Test all FX providers (ECB, FED, BOE, SNB)
                   Tests: Metadata, API connection, rate fetching, normalization
                   📋 Prerequisites: Internet connection
         
  fx-multi-unit  - Test multi-unit currency handling (JPY, SEK, NOK, DKK)
                   Tests: Identification, rate reasonableness, 100x logic
                   📋 Prerequisites: Internet connection
         
  asset-providers - Test all asset pricing providers (yfinance, cssscraper)
                    Tests: Metadata, API connection, current/historical data fetching, search
                    📋 Prerequisites: Internet connection
         
  all            - Run all external service tests
  
Future: yfinance, other data sources will be added here
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    external_parser.add_argument(
        "action",
        choices=["fx-source", "fx-multi-unit", "asset-providers", "all"],
        help="External service test to run"
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
  • Tests schema, constraints, data persistence

Test commands:
  create            - Delete existing DB and create fresh from migrations
                      📋 Prerequisites: None - this is the first test to run
              
  validate          - Verify all tables, constraints, indexes, foreign keys
                      📋 Prerequisites: Database created (run: db create)
              
  numeric-truncation - Test Numeric column truncation for ALL tables
                      📋 Prerequisites: Database created (run: db create)
                      💡 Tests helper functions and database precision handling
              
  populate          - Populate database with MOCK DATA for testing/frontend dev
                      📋 Prerequisites: Database created (run: db create)
                      💡 Use --force to delete existing data and recreate
              
  fx-rates          - Test FX rates persistence (fetch from ECB & persist)
                      📋 Prerequisites: External ECB API working (run: external ecb)
                      💡 Can run on database with existing data (uses UPSERT)
              
  all               - Run all DB tests (create → validate → numeric-truncation → populate → fx-rates)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    db_parser.add_argument(
        "action",
        choices=["create", "validate", "numeric-truncation", "fx-rates", "populate", "all"],
        help="Database test to run"
        )

    db_parser.add_argument(
        "--force",
        action="store_true",
        help="[populate only] Delete existing database and recreate from scratch"
        )

    # ========================================================================
    # SERVICES TESTS SUBPARSER
    # ========================================================================
    services_parser = subparsers.add_parser(
        "services",
        help="Backend service logic tests (no backend server)",
        description="""
Backend Services Tests

These tests verify business logic and service layer:
  • No backend server required
  • Tests conversions, calculations, algorithms
  • Uses data from database

Test commands:
  fx                   - Test FX conversion service logic (identity, direct, inverse, cross-currency, forward-fill)
                         📋 Prerequisites: DB FX rates subsystem (run: db fx-rates)

  asset-source         - Test Asset Source service logic (provider assignment, helpers, synthetic yield)
                         📋 Prerequisites: Database created (run: db create)
                         💡 Tests: Helper functions (truncation, ACT/365), Provider assignment (bulk/single), Synthetic yield
  
  asset-source-refresh - Smoke test: Asset Source refresh orchestration
                         📋 Prerequisites: Database created (run: db create)
                         💡 Runs lightweight refresh orchestration smoke test using a mock provider
  
  synthetic-yield      - Test synthetic yield calculation for SCHEDULED_YIELD assets
                         📋 Prerequisites: Database created (run: db create)
                         💡 Tests: ACT/365 day count, rate lookup, accrued interest, full valuation
  
  all                   - Run all backend service tests
  
Future: FIFO calculations, portfolio aggregations, loan schedules will be added here
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    services_parser.add_argument(
        "action",
        choices=["fx", "asset-source", "asset-source-refresh", "synthetic-yield", "all"],
        help="Service test to run"
        )

    # ========================================================================
    # API TESTS SUBPARSER
    # ========================================================================
    api_parser = subparsers.add_parser(
        "api",
        help="API endpoint tests (auto-starts server if needed)",
        description="""
API Endpoint Tests

These tests verify REST API endpoints:
  • Target: http://localhost:8000
  • Backend server auto-started if not running
  • Tests HTTP requests/responses, validation, error handling

Test commands:
  fx   - Test FX endpoints (GET /currencies, POST /sync, GET /convert)
         📋 Prerequisites: Services FX conversion subsystem (run: db fx-rates)
         Note: Server will be automatically started and stopped by test
         
  all  - Run all API tests (currently only FX)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    api_parser.add_argument(
        "action",
        choices=["fx", "all"],
        help="API test to run"
        )

    # ========================================================================
    # ALL TESTS CATEGORY
    # ========================================================================
    all_parser = subparsers.add_parser(
        "all",
        help="Run ALL tests in optimal order",
        description="""
Complete Test Suite

Runs all test categories in the optimal order:
  1. External Services (ECB API, etc.)
  2. Database Layer (schema, persistence)
  3. Backend Services (conversion logic, calculations)
  4. API Endpoints (REST API - auto-starts test server on port 8001)

This is the recommended way to verify your LibreFolio installation.

Expected time: 3-7 minutes (depending on network speed for ECB API)

✅ API tests now INCLUDED with automatic server start/stop
   Test server runs on port 8001 (configurable via TEST_PORT env var)
   If port 8001 is occupied, you'll see helpful troubleshooting instructions
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    return parser


def main():
    """Main entry point."""
    parser = create_parser()

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # If no category provided, show help
    if not args.category:
        parser.print_help()
        return 1

    # Route to appropriate test handler
    success = False
    verbose = getattr(args, 'verbose', False)

    if args.category == "all":
        # Run complete test suite
        success = run_all_tests(verbose=verbose)

    elif args.category == "external":
        # External services tests
        if args.action == "fx-source":
            success = external_fx_source(verbose=verbose)
        elif args.action == "fx-multi-unit":
            success = external_fx_multi_unit(verbose=verbose)
        elif args.action == "asset-providers":
            success = external_asset_providers(verbose=verbose)
        elif args.action == "all":
            success = external_all(verbose=verbose)

    elif args.category == "db":
        # Database tests
        if args.action == "create":
            success = db_create(verbose=verbose)
        elif args.action == "validate":
            success = db_validate(verbose=verbose)
        elif args.action == "numeric-truncation":
            success = db_numeric_truncation(verbose=verbose)
        elif args.action == "fx-rates":
            success = db_fx_rates(verbose=verbose)
        elif args.action == "populate":
            force = getattr(args, 'force', False)
            success = db_populate(verbose=verbose, force=force)
        elif args.action == "all":
            success = db_all(verbose=verbose)

    elif args.category == "services":
        # Backend services tests
        if args.action == "fx":
            success = services_fx_conversion(verbose=verbose)
        elif args.action == "asset-source":
            success = services_asset_source(verbose=verbose)
        elif args.action == "asset-source-refresh":
            success = services_asset_source_refresh(verbose=verbose)
        elif args.action == "synthetic-yield":
            success = services_synthetic_yield(verbose=verbose)
        elif args.action == "all":
            success = services_all(verbose=verbose)

    elif args.category == "api":
        # API tests
        if args.action == "fx":
            success = api_fx(verbose=verbose)
        elif args.action == "all":
            success = api_test(verbose=verbose)

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

        traceback.print_exc()
        sys.exit(1)
