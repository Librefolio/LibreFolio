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
import subprocess
import traceback
# Ensure project root is in path (file is in scripts/)
from pathlib import Path

import argcomplete

PROJECT_ROOT = Path(__file__).parent.parent
import sys
import os

sys.path.insert(0, str(PROJECT_ROOT))

# Change to project root so relative paths work
os.chdir(PROJECT_ROOT)

# Setup test database configuration and get test database path
from backend.test_scripts.test_db_config import setup_test_database, TEST_DB_PATH, TEST_DATABASE_URL
# Import test utilities (avoid code duplication)
from backend.test_scripts.test_utils import (Colors, print_header, print_section, print_success, print_error, print_warning, print_info)

# Global flag for coverage mode (set by main())
_COVERAGE_MODE = False


def _run_test_suite(
    suite_name: str,
    tests: list[tuple[str, callable]],
    verbose: bool = False,
    header_msg: str = None,
    info_msgs: list[str] = None,
    summary_title: str = None,
    success_msg: str = None,
    combine_coverage: bool = False,
    ) -> bool:
    """
    Generic function to run a suite of tests with consistent output format.

    Args:
        suite_name: Name of the test suite (e.g., "API Tests", "Database Tests")
        tests: List of (test_name, test_function) tuples
        verbose: Pass to test functions
        header_msg: Optional custom header message (default: "LibreFolio {suite_name}")
        info_msgs: Optional list of info messages to print before tests
        summary_title: Optional custom summary section title (default: "{suite_name} Summary")
        success_msg: Optional custom success message (default: "All {suite_name.lower()} passed! 🎉")
        combine_coverage: If True, combine coverage data after tests (for API/E2E tests)

    Returns:
        bool: True if all tests passed
    """
    # Print header (unless None to skip)
    if header_msg is not None or header_msg != "":
        print_header(header_msg or f"LibreFolio {suite_name}")

    # Print info messages
    if info_msgs:
        for msg in info_msgs:
            print_info(msg)

    total_tests = len(tests)
    results = {}

    # Initialize all as pending
    for test_name, _ in tests:
        results[test_name] = None

    # Run tests
    for test_name, test_func in tests:
        success = test_func()
        results[test_name] = success

        if not success:
            print_error(f"Test failed: {test_name}")
            print_warning(f"Stopping {suite_name.lower()} execution")
            break

    # Summary
    print_section(summary_title or f"{suite_name} Summary")
    passed = sum(1 for success in results.values() if success is True)
    failed = sum(1 for success in results.values() if success is False)
    pending = sum(1 for success in results.values() if success is None)

    for test_name, _ in tests:
        success = results[test_name]
        if success is True:
            status = f"{Colors.GREEN}✅ PASS{Colors.NC}"
        elif success is False:
            status = f"{Colors.RED}❌ FAIL{Colors.NC}"
        else:
            status = f"{Colors.YELLOW}⏳ PENDING{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total_tests} tests passed")
    if pending > 0:
        print(f"{Colors.YELLOW}⏳ {pending} test(s) not run (stopped early){Colors.NC}")

    # Combine coverage if requested
    if combine_coverage and _COVERAGE_MODE:
        print_section("Combining Coverage Data")
        print_info("Merging coverage from test server subprocess...")
        try:
            result = subprocess.run(
                ["coverage", "combine"],
                capture_output=True,
                text=True,
                cwd=Path(__file__).parent
                )
            if result.returncode == 0:
                print_success("Coverage data combined successfully")
            else:
                print_warning(f"Coverage combine had warnings: {result.stderr}")
        except Exception as e:
            print_warning(f"Could not combine coverage: {e}")

    if passed == total_tests:
        print_success(success_msg or f"All {suite_name.lower()} passed! 🎉")
        return True
    else:
        if failed > 0:
            print_error(f"{failed} test(s) failed")
        return False


def _get_category_tests_for_all(category: str, verbose: bool) -> list:
    """
    Generate list of (name, lambda) tuples for a category's all test.

    Automatically excludes the 'all' action itself and uses registry
    as single source of truth.

    Args:
        category: Category key in TEST_REGISTRY
        verbose: Verbose flag to pass to test functions

    Returns:
        List of (test_name, test_lambda) tuples for _run_test_suite
    """
    if category not in TEST_REGISTRY:
        return []

    tests = []
    for action, info in TEST_REGISTRY[category].items():
        if action == "_meta" or action == "all":
            continue
        func = info["func"]
        name = info.get("name", action)
        tests.append((name, lambda f=func, v=verbose: f(verbose=v)))
    return tests


def _build_pytest_cmd(test_path: str, test_names: list = None) -> list:
    """
    Build pytest command with optional test name filter.

    Args:
        test_path: Path to test file or directory
        test_names: Optional list of test names to filter (uses -k flag)

    Returns:
        List of command parts for run_command
    """
    cmd = ["pipenv", "run", "python", "-m", "pytest", test_path, "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])
    return cmd


# TODO: riscrivere in maniera sensata questa funzione affinchè per i test si prenda solo il path e aggiunga tutto lei
def run_command(cmd: list[str], description: str, verbose: bool = False) -> bool:
    """
    Run a command and return True if successful.

    If _COVERAGE_MODE is True and the command is a pytest test, automatically
    adds coverage tracking flags and updates the cumulative coverage database.

    Args:
        cmd: Command to run as list
        description: Description for logging
        verbose: If True, show full command output (like calling script directly)

    Returns:
        bool: True if command succeeded
    """
    # Check if this is a pytest command and coverage is enabled
    is_pytest = 'pytest' in ' '.join(cmd)
    use_coverage = _COVERAGE_MODE and is_pytest

    # If coverage mode, enhance pytest command
    # If coverage mode or verbose, enhance pytest command
    if is_pytest:
        # Find pytest in command
        pytest_idx = next((i for i, c in enumerate(cmd) if 'pytest' in c), None)
        if pytest_idx is not None:
            # Prepare flags to add after pytest
            flags_to_add = []
            if verbose:
                flags_to_add.append('-s')
            if use_coverage:
                flags_to_add.extend([
                    '--cov=backend/app',
                    '--cov-append',  # Append to existing coverage data
                    '--cov-report=html',
                    '--cov-report=term-missing:skip-covered',
                    ])
            # Insert after pytest command
            if flags_to_add:
                cmd = cmd[:pytest_idx + 1] + flags_to_add + cmd[pytest_idx + 1:]
                if use_coverage:
                    print(f"{Colors.YELLOW}📊 Coverage tracking enabled (appending to .coverage){Colors.NC}")
    print(f"\n{Colors.BLUE}Running: {description}{Colors.NC}")
    print(f"Command:\n└─▶ $ {' '.join(cmd)}")

    try:
        # Ensure test subprocesses run in test mode when invoking test scripts
        env = None
        try:
            # If the command invokes our test scripts via pipenv/python module, force test env
            if any('backend.test_scripts' in c or c.endswith('.py') and 'backend/test_scripts' in c for c in cmd):
                env = os.environ.copy()
                env['LIBREFOLIO_TEST_MODE'] = '1'
                env['DATABASE_URL'] = TEST_DATABASE_URL

                # Signal to test server that coverage is enabled
                if use_coverage:
                    env['COVERAGE_RUN'] = '1'
        except Exception:
            env = None
        # Capture only if not verbose
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=not verbose, text=True, env=env)

        if result.returncode == 0:
            print_success(f"{description} - PASSED")
            if use_coverage:
                print(f"{Colors.GREEN}✅ Coverage data appended to .coverage database{Colors.NC}")
            return True
        else:
            print_error(f"{description} - FAILED (exit code: {result.returncode})")
            if use_coverage:
                print(f"{Colors.YELLOW}⚠️  Coverage data still appended despite test failure{Colors.NC}")
            return False

    except Exception as e:
        print_error(f"{description} - ERROR: {e}")
        return False


# ============================================================================
# EXTERNAL SERVICES TESTS
# ============================================================================

def external_fx_providers(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run FX providers external tests (network-dependent).

    Tests all registered FX providers (ECB, FED, BOE, etc.) with live API calls.
    Includes multi-unit currency tests (automatically skipped for providers without multi-unit support).

    WARNING: Requires internet connection and may be slow due to rate limiting.
    """
    print_section("External: FX Providers Tests (including multi-unit)")
    print_info("Testing: All registered FX providers (ECB, FED, BOE, etc.)")
    print_info("Tests: Metadata, currencies, rate fetching, normalization, multi-unit handling")
    print_info("Note: Multi-unit tests auto-skip for providers without multi-unit support")
    print_info("⚠️  WARNING: Requires internet connection")
    print_info("⚠️  WARNING: May be slow due to API rate limiting")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_fx_providers.py", test_names)
    return run_command(cmd, "FX providers external tests", verbose=verbose)


def external_asset_providers(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test all registered asset pricing providers (yfinance, cssscraper, etc.).

    Tests external integration with asset data sources.
    Includes tests for metadata, current value, historical data, search, error handling.
    """
    print_section("External: Asset Providers Tests")
    print_info("Testing: All registered asset pricing providers")
    print_info("Tests: Metadata, current value, historical data, search, error handling")
    print_info("⚠️  WARNING: Requires internet connection")
    print_info("⚠️  WARNING: May be slow due to API rate limiting")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_asset_providers.py", test_names)
    return run_command(cmd, "Asset providers tests", verbose=verbose)


def external_brim_providers(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test BRIM (Broker Report Import Manager) providers.

    Tests plugin discovery, file parsing, auto-detection, and sample file coverage.
    Does NOT require network - tests are based on local sample files.
    """
    print_section("External: BRIM Providers Tests")
    print_info("Testing: Broker Report Import Manager (BRIM) plugins")
    print_info("Tests: Plugin discovery, file parsing, auto-detection, sample coverage")
    print_info("Brokers: Directa, DEGIRO, Trading212, IBKR, eToro, Revolut, Schwab, etc.")

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_providers.py", test_names)
    return run_command(cmd, "BRIM providers tests", verbose=verbose)


def external_all(verbose: bool = False) -> bool:
    """Run all external tests (network-dependent)."""
    return _run_test_suite(
        suite_name="External Tests",
        tests=_get_category_tests_for_all("external", verbose),
        verbose=verbose,
        info_msgs=[
            "Testing external provider integrations",
            "⚠️  WARNING: Requires internet connection for FX/Asset providers",
            "⚠️  WARNING: May be slow",
            ],
        )


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
    # TODO: aggiungere le variabili di ambiente per fargli capire che siamo in modalitá test e quindi deve guardare l'altra porta
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


def db_validate(verbose: bool = False, test_names: list = None) -> bool:
    """
    Validate database schema.
    Checks that all expected tables, constraints, indexes exist.
    """
    print_section("Database Schema Validation")

    print_info(f"This test operates on: {TEST_DB_PATH}")
    print_info("The backend server is NOT used in this test")
    print_info("Testing: Tables, Foreign Keys, Constraints, Indexes, Enums")

    cmd = _build_pytest_cmd("backend/test_scripts/test_db/db_schema_validate.py", test_names)
    # Add -s flag for this specific test
    cmd.insert(cmd.index("-v"), "-s")
    return run_command(cmd, "Schema validation", verbose=verbose)


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


def db_fx_rates(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test FX rates persistence in database.
    Tests fetching rates from ECB and persisting to database.
    """
    print_section("DB Test: FX Rates Persistence")

    print_info(f"This test operates on: {TEST_DB_PATH} (test database)")
    print_info("Testing: Fetch rates, Persist to DB, Overwrite, Idempotency, Constraints")

    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_fx_rates_persistence.py", test_names)
    return run_command(cmd, "FX rates persistence tests", verbose=verbose)


def db_brim(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test BRIM (Broker Report Import Manager) database operations.

    Tests asset candidate search and duplicate transaction detection.
    Requires database with test data.
    """
    print_section("DB Test: BRIM Asset Search & Duplicate Detection")

    print_info(f"This test operates on: {TEST_DB_PATH} (test database)")
    print_info("Testing: Asset candidate search, duplicate detection")
    print_info("Tests: ISIN/ticker search, confidence levels, auto-selection")

    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_brim_db.py", test_names)
    return run_command(cmd, "BRIM database tests", verbose=verbose)


def db_numeric_truncation(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test Numeric column truncation behavior across all tables.
    Validates helper functions and database precision handling.
    """
    print_section("DB Test: Numeric Column Truncation")
    print_info("Testing all Numeric columns in database")
    print_info("Tests: Helper functions, DB truncation, No false updates")

    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_numeric_truncation.py", test_names)
    return run_command(cmd, "Numeric truncation tests", verbose=verbose)


def db_test_referential_integrity(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test ALL database referential integrity constraints.

    Comprehensive test suite covering:
    - CASCADE delete behaviors (Asset→PriceHistory, Asset→AssetProviderAssignment,
      CashAccount→CashMovements, CashMovement→Transaction)
    - RESTRICT behaviors (Asset/Broker deletion blocked by Transactions/CashAccounts)
    - Transaction ↔ CashMovement unidirectional relationship with CASCADE
    - All UNIQUE constraints (daily-point policy, one provider per asset,
      one account per broker/currency)
    - All CHECK constraints (transaction types require cash_movement_id,
      FX alphabetical ordering)

    Total: 17 comprehensive integrity tests
    """
    print_section("DB Test: Referential Integrity (CASCADE, RESTRICT, UNIQUE, CHECK)")
    print_info("Comprehensive test suite for ALL foreign key behaviors and constraints")
    print_info("Tests: CASCADE (7), Transaction↔CashMovement (3), UNIQUE (4), CHECK (4)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_db_referential_integrity.py", test_names)
    cmd.insert(cmd.index("-v"), "-s")
    return run_command(cmd, "Database referential integrity tests", verbose=verbose)


def db_all(verbose: bool = False) -> bool:
    """
    Run all database tests in sequence.

    Order is critical:
    1. create - Must be first (creates empty DB)
    2. validate - Schema must exist
    3. numeric-truncation - DB must exist
    4. populate - Adds test data (force=True to recreate)
    5. referential-integrity - Needs data
    6. fx-rates - Uses UPSERT (can run with existing data)
    7. brim - Needs populated data
    """
    # DB tests have critical ordering - define explicitly
    db_order = [
        "create", "validate", "numeric-truncation", "populate",
        "referential-integrity", "fx-rates", "brim"
        ]

    tests = []
    for action in db_order:
        if action in TEST_REGISTRY["db"]:
            info = TEST_REGISTRY["db"][action]
            func = info["func"]
            name = info.get("name", action)
            # Special case: populate needs force=True in all
            if action == "populate":
                tests.append((name, lambda v=verbose: db_populate(verbose=v, force=True)))
            else:
                tests.append((name, lambda f=func, v=verbose: f(verbose=v)))

    return _run_test_suite(
        suite_name="Database Tests",
        tests=tests,
        verbose=verbose,
        info_msgs=[
            "Testing the database layer (SQLite file)",
            "Backend server is NOT required for these tests",
            f"Target: {TEST_DB_PATH}",
            ],
        summary_title="Database Test Summary",
        )


# ============================================================================
# SERVICES TESTS
# ============================================================================

def services_fx_conversion(verbose: bool = False, test_names: list = None) -> bool:
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

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_fx_conversion.py", test_names)
    return run_command(cmd, "FX conversion service tests", verbose=verbose)


def services_asset_metadata(verbose: bool = False, test_names: list = None) -> bool:
    """Test AssetMetadataService static utility behavior."""
    print_section("Services: Asset Metadata Service")
    print_info("Testing: backend/app/services/asset_metadata.py")
    print_info("Tests: parse/serialize, diff, patch semantics")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_metadata.py", test_names)
    return run_command(cmd, "Asset metadata service tests", verbose=verbose)


def services_asset_source(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test Asset Source service logic.
    Tests provider assignment (bulk/single), helper functions, and synthetic yield calculation.
    """
    print_section("Services: Asset Source Logic")
    print_info("Testing: backend/app/services/asset_source.py")
    print_info("Tests: Helper functions, Provider assignment, Synthetic yield")
    print_info("Note: Test assets automatically created and cleaned up")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_source.py", test_names)
    return run_command(cmd, "Asset source service tests", verbose=verbose)


def services_asset_source_refresh(verbose: bool = False, test_names: list = None) -> bool:
    """
    Smoke test: Asset Source refresh orchestration.
    Runs the lightweight refresh orchestration smoke test which uses a mock provider.
    """
    print_section("Services: Asset Source Refresh (smoke)")
    print_info("Testing: backend/app/services/asset_source bulk refresh orchestration (smoke)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_asset_source_refresh.py", test_names)
    return run_command(cmd, "Asset source refresh smoke test", verbose=verbose)


def services_provider_registry(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test registry dei provider (asset & fx).
    Verifica registrazione, lookup, priorità e fallback.
    """
    print_section("Services: Provider Registry")
    print_info("Testing: backend/app/services/provider_registry.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_provider_registry.py", test_names)
    return run_command(cmd, "Provider registry tests", verbose=verbose)


def services_synthetic_yield(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test synthetic yield calculation for SCHEDULED_YIELD assets.
    Tests runtime valuation for crowdfunding loans, bonds, etc.
    """
    print_section("Services: Synthetic Yield Calculation")
    print_info("Testing: SCHEDULED_YIELD asset valuation (ACT/365 SIMPLE interest)")
    print_info("Covers: Rate lookup, accrued interest, full valuation, DB integration")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_synthetic_yield.py", test_names)
    return run_command(cmd, "Synthetic yield tests", verbose=verbose)


def services_synthetic_yield_integration(verbose: bool = False, test_names: list = None) -> bool:
    """Test E2E synthetic yield integration scenarios (P2P loan, bond, mixed schedule)."""
    print_section("Services: Synthetic Yield Integration E2E")
    print_info("Testing: ScheduledInvestmentProvider end-to-end scenarios")
    print_info("Scenarios: P2P loan (grace + late), bond compound quarterly, mixed SIMPLE/COMPOUND")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_synthetic_yield_integration.py", test_names)
    return run_command(cmd, "Synthetic yield integration E2E tests", verbose=verbose)


def services_transaction(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test TransactionService CRUD operations, balance validation, and link resolution.
    """
    print_section("Services: Transaction Service")
    print_info("Testing: backend/app/services/transaction_service.py")
    print_info("Tests: CRUD, balance validation, link resolution, balance queries")

    cmd = ["pipenv", "run", "python", "-m", "pytest", "backend/test_scripts/test_services/test_transaction_service.py", "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])

    return run_command(cmd, "Transaction service tests", verbose=verbose)


def services_broker(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test BrokerService CRUD operations, initial balances, and flag validation.
    """
    print_section("Services: Broker Service")
    print_info("Testing: backend/app/services/broker_service.py")
    print_info("Tests: CRUD, initial deposits, get_summary, flag validation")

    cmd = ["pipenv", "run", "python", "-m", "pytest", "backend/test_scripts/test_services/test_broker_service.py", "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])

    return run_command(cmd, "Broker service tests", verbose=verbose)


def services_user_profile(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test user profile update service (username/email modification).
    """
    print_section("Services: User Profile")
    print_info("Testing: backend/app/services/user_service.py (update_profile)")
    print_info("Tests: Update username/email, uniqueness validation, error handling")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_user_profile.py", test_names)
    return run_command(cmd, "User profile service tests", verbose=verbose)


def services_edge_cases(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test edge cases and regression scenarios for transactions.
    """
    print_section("Services: Transaction Edge Cases")
    print_info("Testing: Edge cases, boundary conditions, regression scenarios")
    print_info("Tests: Decimal precision, currency validation, date edge cases, null handling")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_transaction_edge_cases.py", test_names)
    return run_command(cmd, "Transaction edge cases tests", verbose=verbose)


# ============================================================================
# UTILS TESTS
# ============================================================================

def utils_decimal_precision(verbose: bool = False, test_names: list = None) -> bool:
    """Test decimal precision utilities (Phase 2 task 3.2)."""
    print_section("Utils: Decimal Precision")
    print_info("Testing: backend/app/utils/decimal_utils.py")
    print_info("Tests: Model precision extraction, Truncation, Edge cases")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_decimal_utils.py", test_names)
    return run_command(cmd, "Decimal precision tests", verbose=verbose)


def utils_datetime(verbose: bool = False, test_names: list = None) -> bool:
    """Test datetime utilities (Phase 1 task 3.1)."""
    print_section("Utils: Datetime")
    print_info("Testing: backend/app/utils/datetime_utils.py")
    print_info("Tests: Timezone-aware datetime helpers")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_datetime_utils.py", test_names)
    return run_command(cmd, "Datetime utils tests", verbose=verbose)


def utils_financial_math(verbose: bool = False, test_names: list = None) -> bool:
    """Test financial math utilities."""
    print_section("Utils: Financial Math")
    print_info("Testing: backend/app/utils/financial_math.py")
    print_info("Tests: Day count conventions, Interest calculations, Rate finding")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_financial_math.py", test_names)
    return run_command(cmd, "Financial math tests", verbose=verbose)


def utils_day_count(verbose: bool = False, test_names: list = None) -> bool:
    """Test day count conventions."""
    print_section("Utils: Day Count Conventions")
    print_info("Testing: backend/app/utils/financial_math.py (day count functions)")
    print_info("Tests: ACT/365, ACT/360, ACT/ACT, 30/360 conventions")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_day_count_conventions.py", test_names)
    return run_command(cmd, "Day count convention tests", verbose=verbose)


def utils_compound_interest(verbose: bool = False, test_names: list = None) -> bool:
    """Test compound interest calculations."""
    print_section("Utils: Compound Interest")
    print_info("Testing: backend/app/utils/financial_math.py (interest calculations)")
    print_info("Tests: Simple, Compound (annual, semiannual, quarterly, monthly, daily, continuous)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_compound_interest.py", test_names)
    return run_command(cmd, "Compound interest tests", verbose=verbose)


def utils_geo_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test geographic area normalization utilities (country codes, weight validation)."""
    print_section("Utils: Geographic Area Normalization")
    print_info("Testing: backend/app/utils/geo_utils.py")
    print_info("Tests: ISO-3166-A3 normalization, weight parsing, validation pipeline")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_geo_utils.py", test_names)
    return run_command(cmd, "Geographic area normalization tests", verbose=verbose)


def utils_sector_normalization(verbose: bool = False, test_names: list = None) -> bool:
    """Test FinancialSector enum and sector normalization."""
    print_section("Utils: Sector Normalization")
    print_info("Testing: backend/app/utils/sector_fin_utils.py")
    print_info("Tests: FinancialSector enum, aliases, normalization, validation")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_sector_normalization.py", test_names)
    return run_command(cmd, "Sector normalization tests", verbose=verbose)


def utils_all(verbose: bool = False) -> bool:
    """Run all utility tests."""
    return _run_test_suite(
        suite_name="Utility Tests",
        tests=_get_category_tests_for_all("utils", verbose),
        verbose=verbose,
        info_msgs=["Testing utility modules and helper functions"],
        )


# ============================================================================
# SCHEMAS TESTS
# ============================================================================

def schemas_common(verbose: bool = False, test_names: list = None) -> bool:
    """Test common Pydantic schemas (Currency, DateRangeModel, OldNew)."""
    print_section("Schemas: Common (Currency, DateRangeModel, OldNew)")
    print_info("Testing: backend/app/schemas/common.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_common_schemas.py", test_names)
    return run_command(cmd, "Common schemas tests", verbose=verbose)


def schemas_assets(verbose: bool = False, test_names: list = None) -> bool:
    """Test asset-related Pydantic schemas (FAGeographicArea, FAInterestRatePeriod, etc.)."""
    print_section("Schemas: Assets (FAGeographicArea, FAInterestRatePeriod, etc.)")
    print_info("Testing: backend/app/schemas/assets.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_asset_schemas.py", test_names)
    return run_command(cmd, "Asset schemas tests", verbose=verbose)


def schemas_transactions(verbose: bool = False, test_names: list = None) -> bool:
    """Test transaction Pydantic schemas (TXCreateItem, TXReadItem, etc.)."""
    print_section("Schemas: Transactions (TXCreateItem, TXReadItem, etc.)")
    print_info("Testing: backend/app/schemas/transactions.py")

    cmd = ["pipenv", "run", "python", "-m", "pytest", "backend/test_scripts/test_schemas/test_transaction_schemas.py", "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])

    return run_command(cmd, "Transaction schemas tests", verbose=verbose)


def schemas_brokers(verbose: bool = False, test_names: list = None) -> bool:
    """Test broker Pydantic schemas (BRCreateItem, BRReadItem, etc.)."""
    print_section("Schemas: Brokers (BRCreateItem, BRReadItem, etc.)")
    print_info("Testing: backend/app/schemas/brokers.py")

    cmd = ["pipenv", "run", "python", "-m", "pytest", "backend/test_scripts/test_schemas/test_broker_schemas.py", "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])

    return run_command(cmd, "Broker schemas tests", verbose=verbose)


def schemas_all(verbose: bool = False) -> bool:
    """Run all schema validation tests."""
    return _run_test_suite(
        suite_name="Schema Validation Tests",
        tests=_get_category_tests_for_all("schemas", verbose),
        verbose=verbose,
        info_msgs=["Testing Pydantic schema validation rules"],
        summary_title="Schema Tests Summary",
        success_msg="All schema tests passed! 🎉",
        )


def services_all(verbose: bool = False) -> bool:
    """Run all backend service tests."""
    print_header("LibreFolio Backend Services Tests")
    print_info("Testing business logic and service layer")
    print_info("No backend server required")

    # Ensure clean test database before running services tests
    print_info("\n⚙️  Creating clean test database for services tests...")
    if not db_create(verbose=False):
        print_error("Failed to create clean test database")
        print_warning("Services tests may fail due to dirty database state")
    else:
        print_success("Clean test database created\n")

    return _run_test_suite(
        suite_name="Backend Services Tests",
        tests=_get_category_tests_for_all("services", verbose),
        verbose=verbose,
        header_msg=None,  # Already printed above
        summary_title="Backend Services Test Summary",
        success_msg="All backend services tests passed! 🎉",
        )


# ============================================================================
# API TESTS
# ============================================================================

def api_fx(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run FX API endpoint tests (conversion, providers, pair sources).
    """
    print_section("FX API Endpoint Tests")
    print_info("Testing REST API endpoints for FX functionality")
    print_info("Tests: Currency conversion, providers, pair sources CRUD")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_fx_api.py", test_names)
    return run_command(cmd, "FX API tests", verbose=verbose)


def api_fx_sync(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run FX Sync API endpoint tests.
    """
    print_section("FX Sync API Endpoint Tests")
    print_info("Testing FX rate synchronization endpoints")
    print_info("Tests: GET /fx/currencies/sync with all scenarios")
    print_info("Tests: Error handling (FXServiceError), auto-config mode, provider validation")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_fx_sync.py", test_names)
    return run_command(cmd, "FX Sync API tests", verbose=verbose)


def api_assets_price(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run Assets Price API endpoint tests.
    """
    print_section("Assets Price API Endpoint Tests")
    print_info("Testing asset price management endpoints")
    print_info("Tests: POST /assets/prices (bulk upsert)")
    print_info("Tests: DELETE /assets/prices (bulk delete)")
    print_info("Tests: GET /assets/prices/{asset_id}")
    print_info("Tests: POST /assets/prices/refresh (from providers)")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_assets_prices.py", test_names)
    return run_command(cmd, "Assets Price API tests", verbose=verbose)


def api_assets_provider(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run Assets Provider API endpoint tests.
    """
    print_section("Assets Provider API Endpoint Tests")
    print_info("Testing provider assignment endpoints")
    print_info("Tests: GET /assets/provider/assignments")
    print_info("Tests: POST /assets/provider (edge cases)")
    print_info("Tests: DELETE /assets/provider (edge cases)")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_assets_provider.py", test_names)
    return run_command(cmd, "Assets Provider API tests", verbose=verbose)


def api_assets_metadata(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run Assets Metadata API endpoint tests.
    """
    print_section("Assets Metadata API Endpoint Tests")
    print_info("Testing REST API endpoints for asset metadata management")
    print_info("Tests: PATCH metadata, bulk read, refresh endpoints")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_assets_metadata.py", test_names)
    return run_command(cmd, "Assets Metadata API tests", verbose=verbose)


def api_assets_crud(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run Assets CRUD API endpoint tests.
    """
    print_section("Assets CRUD API Endpoint Tests")
    print_info("Testing REST API endpoints for asset CRUD operations")
    print_info("Tests: Create assets, list/filter assets, delete assets")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_assets_crud.py", test_names)
    return run_command(cmd, "Assets CRUD API tests", verbose=verbose)


def api_utilities(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run Utilities API endpoint tests.
    """
    print_section("Utilities API Endpoint Tests")
    print_info("Testing REST API endpoints for frontend utilities")
    print_info("Tests: GET /utilities/sectors, GET /utilities/countries/normalize")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_utilities.py", test_names)
    return run_command(cmd, "Utilities API tests", verbose=verbose)


def api_transactions(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run Transactions API endpoint tests.
    """
    print_section("Transactions API Endpoint Tests")
    print_info("Testing REST API endpoints for transaction management")
    print_info("Tests: POST /transactions (bulk create), GET /transactions (query)")
    print_info("Tests: GET /transactions/{id}, PATCH /transactions, DELETE /transactions")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_transactions_api.py", test_names)
    return run_command(cmd, "Transactions API tests", verbose=verbose)


def api_brokers(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run Brokers API endpoint tests.
    """
    print_section("Brokers API Endpoint Tests")
    print_info("Testing REST API endpoints for broker management")
    print_info("Tests: POST /brokers (create), GET /brokers (list)")
    print_info("Tests: GET /brokers/{id}, PATCH /brokers, DELETE /brokers")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_brokers_api.py", test_names)
    return run_command(cmd, "Brokers API tests", verbose=verbose)


def api_brim(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run BRIM (Broker Report Import Manager) API endpoint tests.
    """
    print_section("BRIM API Endpoint Tests")
    print_info("Testing REST API endpoints for broker report import")
    print_info("Tests: POST /import/upload, GET /import/files, POST /import/files/{id}/parse")
    print_info("Tests: File storage, parse response, duplicate detection, E2E import flow")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_brim_api.py", test_names)
    return run_command(cmd, "BRIM API tests", verbose=verbose)


def search2prices_test(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run E2E (End-to-End) API tests.

    Tests complete flow: Search → Create → Assign → Metadata → Prices
    """
    print_section("E2E API Test search-to-prices")
    print_info("Testing complete end-to-end flow via API")
    print_info("Tests: Search → Create Asset → Assign Provider → Refresh Metadata → Refresh Prices")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_e2e/test_search_to_prices.py", test_names)
    return run_command(cmd, "E2E API tests", verbose=verbose)


def api_auth(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run Authentication API endpoint tests.

    Tests: register, login, logout, me, session management
    """
    print_section("Authentication API Tests")
    print_info("Testing REST API endpoints for authentication")
    print_info("Tests: POST /auth/register, POST /auth/login, POST /auth/logout, GET /auth/me")
    print_info("Tests: Session cookies, password validation, duplicate detection")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_auth_api.py", test_names)
    return run_command(cmd, "Auth API tests", verbose=verbose)


def api_profile(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run Profile Update API endpoint tests.

    Tests: PUT /auth/profile (username/email update)
    """
    print_section("Profile Update API Tests")
    print_info("Testing REST API endpoints for profile updates")
    print_info("Tests: PUT /auth/profile")
    print_info("Tests: Username update, email update, validation, uniqueness")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_profile_api.py", test_names)
    return run_command(cmd, "Profile API tests", verbose=verbose)


def api_settings(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """
    Run settings API tests.

    Tests: user settings, global settings CRUD, admin permissions
    """
    print_section("Settings API Tests")
    print_info("Testing REST API endpoints for user and global settings")
    print_info("Tests: GET/PUT /settings/user, GET/PUT /settings/global")
    print_info("Tests: Admin permissions, setting validation")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_settings_api.py", test_names)
    return run_command(cmd, "Settings API tests", verbose=verbose)


def api_uploads(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """
    Run uploads API tests.

    Tests: file upload, list, download, delete, plugin static assets
    """
    print_section("Uploads API Tests")
    print_info("Testing REST API endpoints for file uploads")
    print_info("Tests: POST /uploads, GET /uploads, DELETE /uploads/{id}")
    print_info("Tests: Download, plugin static assets")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_uploads_api.py", test_names)
    return run_command(cmd, "Uploads API tests", verbose=verbose)


def api_broker_access(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """
    Run broker access API tests.

    Tests: broker access management (add, update, remove access)
    Tests role permissions: OWNER, EDITOR, VIEWER
    """
    print_section("Broker Access API Tests")
    print_info("Testing REST API endpoints for broker access management")
    print_info("Tests: GET/POST/PATCH/DELETE /brokers/{id}/access")
    print_info("Tests: Role hierarchy (OWNER > EDITOR > VIEWER)")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_broker_access_api.py", test_names)
    return run_command(cmd, "Broker Access API tests", verbose=verbose)


def api_broker_multiuser(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """
    Run broker multi-user role tests.

    Tests: role-based permissions on broker operations
    OWNER can do everything, EDITOR can modify, VIEWER read-only
    """
    print_section("Broker Multi-User Role Tests")
    print_info("Testing role-based permissions on broker operations")
    print_info("Tests: OWNER permissions, EDITOR permissions, VIEWER permissions")
    print_info("Tests: User isolation between different users")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_broker_multiuser_api.py", test_names)
    return run_command(cmd, "Broker Multi-User API tests", verbose=verbose)


def api_test(verbose: bool = False) -> bool:
    """Run all API tests."""
    return _run_test_suite(
        suite_name="API Tests",
        tests=_get_category_tests_for_all("api", verbose),
        verbose=verbose,
        info_msgs=[
            "Testing REST API endpoints",
            "Note: Server will be automatically started/stopped by tests",
            ],
        combine_coverage=True,
        )


def e2e_brim(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run BRIM E2E tests.

    Tests complete import flow: Upload → Parse → Import transactions.
    """
    print_section("E2E Test: BRIM Import Flow")
    print_info("Testing complete broker report import workflow")
    print_info("Tests: Upload → Parse → Asset Mapping → Duplicate Detection → Import")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_e2e/test_brim_e2e.py", test_names)
    return run_command(cmd, "BRIM E2E tests", verbose=verbose)


def e2e_test(verbose: bool = False) -> bool:
    """Run all E2E tests."""
    return _run_test_suite(
        suite_name="E2E Tests",
        tests=_get_category_tests_for_all("e2e", verbose),
        verbose=verbose,
        header_msg="LibreFolio E2E Tests with API interaction",
        info_msgs=[
            "Testing E2E workflow using REST API endpoints",
            "Note: Server will be automatically started/stopped by tests",
            ],
        combine_coverage=True,
        )


# ============================================================================
# FRONTEND E2E TESTS (Playwright)
# ============================================================================

def _ensure_frontend_build() -> bool:
    """
    Ensure frontend is built and up to date.
    Uses shared logic from cli_base.

    Returns:
        True if build is ready, False if build failed.
    """
    from scripts.cli_base import auto_build_frontend

    result = auto_build_frontend(debug=False)

    # auto_build_frontend returns None if no build needed, 0 if success, non-zero if failed
    if result is None or result == 0:
        return True
    else:
        print_error("Frontend build failed!")
        return False

    print_success("Frontend build completed")
    return True


def _ensure_test_users() -> bool:
    """Ensure E2E test users exist in test database."""
    print_info("Ensuring E2E test users exist...")

    users = [
        ("e2e_test_user", "e2e@test.example.com", "E2eTestPass123!"),
        ("e2e_test_admin", "e2eadmin@test.example.com", "E2eAdminPass123!"),
        ("e2e_test_user2", "e2e2@test.example.com", "E2eTestPass456!"),
    ]

    for username, email, password in users:
        result = subprocess.run(
            ["python", "scripts/user_cli.py", "--test-db", "create-superuser",
             username, email, password],
            capture_output=True,
            text=True
        )
        # Ignore "already exists" errors
        if result.returncode != 0 and "already exists" not in result.stderr.lower():
            print_error(f"Failed to create user {username}: {result.stderr}")
            return False

    # Promote admin
    subprocess.run(
        ["python", "scripts/user_cli.py", "--test-db", "promote", "e2e_test_admin"],
        capture_output=True
    )

    print_success("Test users ready")
    return True


def _run_playwright(
    spec_file: str = None,
    ui: bool = False,
    headed: bool = False,
    debug: bool = False,
    project: str = "desktop",
    test_names: list = None
) -> bool:
    """
    Run Playwright tests with given options.

    Args:
        spec_file: Specific spec file to run (e.g., "auth.spec.ts")
        ui: Open Playwright interactive UI
        headed: Run with visible browser
        debug: Run with PWDEBUG=1 for step-by-step debugging
        project: Playwright project (desktop/mobile)
        test_names: List of test name patterns to filter (uses -g/--grep)
    """
    cmd = ["npm", "run"]

    if ui:
        cmd.append("test:e2e:ui")
    elif debug:
        cmd.append("test:e2e:debug")  # Includes --headed
    elif headed:
        cmd.append("test:e2e:headed")
    else:
        cmd.append("test:e2e")

    # Add extra args after --
    extra_args = []
    if spec_file:
        extra_args.append(spec_file)
    if project and not ui:  # UI mode ignores project
        extra_args.extend(["--project", project])

    # Add grep filter for test names (matches test description)
    if test_names:
        # Join multiple patterns with |
        pattern = "|".join(test_names)
        extra_args.extend(["--grep", pattern])

    if extra_args:
        cmd.extend(["--"] + extra_args)

    print(f"\n{Colors.BLUE}Running: Playwright {spec_file or 'all tests'}{Colors.NC}")
    if test_names:
        print(f"{Colors.YELLOW}Filter: {' | '.join(test_names)}{Colors.NC}")
    print(f"Command:\n└─▶ $ cd frontend && {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", text=True)
        if result.returncode == 0:
            print_success(f"Playwright {spec_file or 'all'} - PASSED")
            return True
        else:
            print_error(f"Playwright {spec_file or 'all'} - FAILED (exit code: {result.returncode})")
            return False
    except Exception as e:
        print_error(f"Playwright error: {e}")
        return False


def front_auth(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None) -> bool:
    """Run auth E2E tests."""
    print_section("Frontend Auth Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("auth.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names)


def front_settings(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None) -> bool:
    """Run settings E2E tests."""
    print_section("Frontend Settings Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("settings.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names)


def front_files(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None) -> bool:
    """Run files E2E tests."""
    print_section("Frontend Files Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("files.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names)


def front_brokers(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None) -> bool:
    """Run brokers E2E tests."""
    print_section("Frontend Brokers Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("brokers.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names)


def front_multi_user(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None) -> bool:
    """Run multi-user isolation tests."""
    print_section("Frontend Multi-User Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("multi-user.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names)


def front_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False) -> bool:
    """Run all frontend tests (excludes gallery)."""
    print_header("Frontend E2E Tests (Playwright)")
    print_info("Running browser-based E2E tests")
    print_info("Server will be started automatically by Playwright")

    # Ensure frontend is built before running tests
    if not _ensure_frontend_build():
        return False

    if not _ensure_test_users():
        return False

    # Run all specs except gallery
    specs = ["auth.spec.ts", "settings.spec.ts", "files.spec.ts", "brokers.spec.ts", "multi-user.spec.ts"]

    return _run_test_suite(
        suite_name="Frontend E2E Tests",
        tests=[(spec.replace('.spec.ts', '').title(), lambda s=spec: _run_playwright(s, ui=ui, headed=headed, debug=debug)) for spec in specs],
        verbose=verbose,
        header_msg=None,  # Already printed above
        summary_title="Frontend E2E Test Summary",
        success_msg="All frontend E2E tests passed! 🎉",
    )


# ============================================================================
# GLOBAL ALL TESTS
# ============================================================================

def run_all_tests(verbose: bool = False) -> bool:
    """
    Run ALL tests in the optimal order.

    Order is determined by the order of categories in TEST_REGISTRY
    (Python 3.7+ guarantees dict ordering):
      1. External services - No dependencies, tests external APIs
      2. Database - Creates/validates DB structure
      3. Schemas - Tests validation rules (pure unit tests)
      4. Utils - Tests helper functions (pure unit tests)
      5. Services - Tests business logic (needs DB)
      6. API endpoints - Tests HTTP layer (needs server)
      7. E2E - Complete workflows (needs everything)

    Note: API tests will automatically start and stop the test server.
          If port 8001 is occupied, tests will fail with helpful instructions.
    """
    # Generate tests from registry - order comes from dict key order
    tests = []
    for category in TEST_REGISTRY.keys():
        # Get the 'all' function for each category
        all_info = TEST_REGISTRY[category].get("all", {})
        func = all_info.get("func")
        name = all_info.get("name", f"{category.title()} Tests")
        if func:
            tests.append((name, lambda f=func, v=verbose: f(verbose=v)))

    return _run_test_suite(
        suite_name="Complete Test Suite",
        tests=tests,
        verbose=verbose,
        info_msgs=[
            "Running all test categories in optimal order",
            "This will take a few minutes...\n",
            ],
        success_msg="\n🎉 ALL TESTS PASSED! 🎉\nYour LibreFolio instance is working correctly!",
        )


# ============================================================================
# TEST REGISTRY - Single source of truth for all tests
# ============================================================================
# Structure:
#   category -> {
#       "_meta": { parser metadata: description, help },
#       action: {
#           "func": test_function,
#           "test_names": bool - whether accepts test_names parameter,
#           "name": display name for help,
#           "desc": description for epilog,
#           "prereq": prerequisites (optional),
#           "tests": what it tests (optional),
#           "note": additional notes (optional),
#       }
#   }
#
# The "all" action in each category runs all tests in that category.
# accepts_test_names=True means you can pass specific test names to run.

TEST_REGISTRY = {
    "external": {
        "_meta": {
            "help": "External service integration tests (no backend server)",
            "description": """
External Services Tests

These tests verify external API integrations:
  • No backend server required
  • Tests network calls to external APIs
  • May be slow or fail if external services are down
""",
            },
        "fx-providers": {
            "func": external_fx_providers,
            "test_names": True,
            "name": "FX Providers",
            "desc": "Test FX rate providers (ECB, FED, BOE, SNB)",
            "prereq": "Internet connection",
            "tests": "ECB, FED, BOE, SNB API calls",
            },
        "asset-providers": {
            "func": external_asset_providers,
            "test_names": True,
            "name": "Asset Providers",
            "desc": "Test asset data providers (yfinance, JustETF)",
            "prereq": "Internet connection",
            "tests": "yfinance, JustETF scraping",
            },
        "brim-providers": {
            "func": external_brim_providers,
            "test_names": True,
            "name": "BRIM Providers",
            "desc": "Test broker import plugins",
            "prereq": "Sample files in samples/",
            "tests": "CSV parsing, transaction mapping",
            },
        "all": {
            "func": external_all,
            "test_names": False,
            "name": "All External Tests",
            "desc": "Run all external service tests",
            },
        },
    "db": {
        "_meta": {
            "help": "Database layer tests (SQLite file, no backend)",
            "description": """
Database Layer Tests

These tests verify SQLite database operations:
  • No backend server required
  • Tests schema, constraints, data integrity
  • Uses test_app.db (separate from production)
""",
            },
        "create": {
            "func": db_create,
            "test_names": False,
            "name": "Create Database",
            "desc": "Create database via Alembic migrations",
            "prereq": "None",
            "tests": "Migration execution",
            },
        "validate": {
            "func": db_validate,
            "test_names": True,
            "name": "Validate Schema",
            "desc": "Validate database schema (tables, columns, indexes)",
            "prereq": "Database created (run: db create)",
            "tests": "Schema validation, constraints",
            },
        "numeric-truncation": {
            "func": db_numeric_truncation,
            "test_names": True,
            "name": "Numeric Truncation",
            "desc": "Test numeric precision handling",
            "prereq": "Database created",
            "tests": "Decimal precision, truncation",
            },
        "fx-rates": {
            "func": db_fx_rates,
            "test_names": True,
            "name": "FX Rates",
            "desc": "Test FX rates persistence and queries",
            "prereq": "Database created",
            "tests": "FX rate CRUD, date queries",
            },
        "brim": {
            "func": db_brim,
            "test_names": True,
            "name": "BRIM Database",
            "desc": "Test BRIM file storage and metadata",
            "prereq": "Database created",
            "tests": "File upload, metadata persistence",
            },
        "populate": {
            "func": db_populate,
            "test_names": False,
            "name": "Populate Database",
            "desc": "Populate database with test data",
            "prereq": "Database created",
            "tests": "Test data insertion",
            "note": "Use --force to recreate from scratch",
            },
        "referential-integrity": {
            "func": db_test_referential_integrity,
            "test_names": True,
            "name": "Referential Integrity",
            "desc": "Test foreign key constraints",
            "prereq": "Database created",
            "tests": "FK constraints, cascades",
            },
        "all": {
            "func": db_all,
            "test_names": False,
            "name": "All Database Tests",
            "desc": "Run all database tests",
            },
        },
    "services": {
        "_meta": {
            "help": "Backend service logic tests (no backend server)",
            "description": """
Backend Services Tests

These tests verify business logic in service layer:
  • No backend server required
  • Tests calculations, conversions, algorithms
  • Uses in-memory or test database
""",
            },
        "fx-conversion": {
            "func": services_fx_conversion,
            "test_names": True,
            "name": "FX Conversion",
            "desc": "Test currency conversion service",
            "prereq": "Database with FX rates",
            "tests": "Direct/triangulated conversion, date handling",
            },
        "asset-source": {
            "func": services_asset_source,
            "test_names": True,
            "name": "Asset Source",
            "desc": "Test asset data source service",
            "prereq": "Database created",
            "tests": "Provider selection, data fetching",
            },
        "asset-metadata": {
            "func": services_asset_metadata,
            "test_names": True,
            "name": "Asset Metadata",
            "desc": "Test asset metadata service",
            "prereq": "Database created",
            "tests": "Metadata refresh, caching",
            },
        "asset-source-refresh": {
            "func": services_asset_source_refresh,
            "test_names": True,
            "name": "Asset Source Refresh",
            "desc": "Test asset price refresh service",
            "prereq": "Database with assets",
            "tests": "Price history updates",
            },
        "provider-registry": {
            "func": services_provider_registry,
            "test_names": True,
            "name": "Provider Registry",
            "desc": "Test provider auto-discovery",
            "prereq": "None",
            "tests": "Registry pattern, plugin loading",
            },
        "synthetic-yield": {
            "func": services_synthetic_yield,
            "test_names": True,
            "name": "Synthetic Yield",
            "desc": "Test scheduled investment calculations",
            "prereq": "None",
            "tests": "Interest calculations, schedules",
            },
        "synthetic-yield-integration": {
            "func": services_synthetic_yield_integration,
            "test_names": True,
            "name": "Synthetic Yield Integration",
            "desc": "Test E2E synthetic yield scenarios",
            "prereq": "Database created",
            "tests": "P2P loan, bond, mixed schedules",
            },
        "transaction": {
            "func": services_transaction,
            "test_names": True,
            "name": "Transaction Service",
            "desc": "Test transaction service",
            "prereq": "Database created",
            "tests": "CRUD, validation, balances",
            },
        "broker": {
            "func": services_broker,
            "test_names": True,
            "name": "Broker Service",
            "desc": "Test broker service",
            "prereq": "Database created",
            "tests": "CRUD, access control, summary",
            },
        "user-profile": {
            "func": services_user_profile,
            "test_names": True,
            "name": "User Profile Service",
            "desc": "Test user profile update service",
            "prereq": "Database created",
            "tests": "Username/email update, validation",
            },
        "edge-cases": {
            "func": services_edge_cases,
            "test_names": True,
            "name": "Edge Cases",
            "desc": "Test edge cases and error handling",
            "prereq": "Database created",
            "tests": "Error paths, boundary conditions",
            },
        "all": {
            "func": services_all,
            "test_names": False,
            "name": "All Service Tests",
            "desc": "Run all service tests",
            },
        },
    "utils": {
        "_meta": {
            "help": "Utility module tests (helper functions)",
            "description": """
Utility Module Tests

These tests verify utility modules and helper functions:
  • No backend server required
  • Tests pure functions and helpers
  • Foundational code used across the application
""",
            },
        "decimal-precision": {
            "func": utils_decimal_precision,
            "test_names": True,
            "name": "Decimal Precision",
            "desc": "Test decimal precision utilities",
            "prereq": "None",
            "tests": "get_model_column_precision(), truncate_to_db_precision()",
            },
        "datetime": {
            "func": utils_datetime,
            "test_names": True,
            "name": "Datetime",
            "desc": "Test datetime utilities",
            "prereq": "None",
            "tests": "utcnow() timezone-aware helper",
            },
        "financial-math": {
            "func": utils_financial_math,
            "test_names": True,
            "name": "Financial Math",
            "desc": "Test financial math utilities",
            "prereq": "None",
            "tests": "Day count, interest calculations",
            },
        "day-count": {
            "func": utils_day_count,
            "test_names": True,
            "name": "Day Count",
            "desc": "Test day count conventions",
            "prereq": "None",
            "tests": "ACT/365, ACT/360, ACT/ACT, 30/360",
            },
        "compound-interest": {
            "func": utils_compound_interest,
            "test_names": True,
            "name": "Compound Interest",
            "desc": "Test compound interest calculations",
            "prereq": "None",
            "tests": "Simple, compound (annual, monthly, daily, continuous)",
            },
        "geo-normalization": {
            "func": utils_geo_utils,
            "test_names": True,
            "name": "Geo Normalization",
            "desc": "Test geographic area normalization",
            "prereq": "pycountry installed",
            "tests": "ISO-3166-A3 conversion, weight validation",
            },
        "sector-normalization": {
            "func": utils_sector_normalization,
            "test_names": True,
            "name": "Sector Normalization",
            "desc": "Test FinancialSector enum and normalization",
            "prereq": "None",
            "tests": "Sector enum values, aliases",
            },
        "all": {
            "func": utils_all,
            "test_names": False,
            "name": "All Utility Tests",
            "desc": "Run all utility tests",
            },
        },
    "schemas": {
        "_meta": {
            "help": "Pydantic schema validation tests",
            "description": """
Schema Validation Tests

These tests verify Pydantic schema validation rules:
  • No backend server required
  • Tests DTO validation, business rules, serialization
  • Pure unit tests (no database needed)
""",
            },
        "common": {
            "func": schemas_common,
            "test_names": True,
            "name": "Common Schemas",
            "desc": "Test common schemas (Currency, DateRangeModel)",
            "prereq": "None",
            "tests": "Creation, validation, arithmetic, serialization",
            },
        "assets": {
            "func": schemas_assets,
            "test_names": True,
            "name": "Asset Schemas",
            "desc": "Test asset-related schemas",
            "prereq": "None",
            "tests": "Distribution validation, interest periods",
            },
        "transactions": {
            "func": schemas_transactions,
            "test_names": True,
            "name": "Transaction Schemas",
            "desc": "Test transaction schemas",
            "prereq": "None",
            "tests": "Type rules, link_uuid, sign validation",
            },
        "brokers": {
            "func": schemas_brokers,
            "test_names": True,
            "name": "Broker Schemas",
            "desc": "Test broker schemas",
            "prereq": "None",
            "tests": "Name validation, initial_balances",
            },
        "all": {
            "func": schemas_all,
            "test_names": False,
            "name": "All Schema Tests",
            "desc": "Run all schema tests",
            },
        },
    "api": {
        "_meta": {
            "help": "API endpoint tests (auto-starts server if needed)",
            "description": """
API Endpoint Tests

These tests verify REST API endpoints:
  • Target: http://localhost:8001 (test server)
  • Backend server auto-started if not running
  • Tests HTTP requests/responses, validation, error handling
""",
            },
        "auth": {
            "func": api_auth,
            "test_names": True,
            "name": "Auth API",
            "desc": "Test Authentication endpoints",
            "prereq": "Database created",
            "tests": "POST /auth/register, /login, /logout, GET /auth/me",
            "note": "Server auto-started",
            },
        "profile": {
            "func": api_profile,
            "test_names": True,
            "name": "Profile API",
            "desc": "Test Profile update endpoints",
            "prereq": "Database created",
            "tests": "PUT /auth/profile",
            "note": "Server auto-started",
            },
        "settings": {
            "func": api_settings,
            "test_names": True,
            "name": "Settings API",
            "desc": "Test Settings endpoints",
            "prereq": "Database created",
            "tests": "GET/PUT /settings/user, /settings/global",
            },
        "uploads": {
            "func": api_uploads,
            "test_names": True,
            "name": "Uploads API",
            "desc": "Test file upload endpoints",
            "prereq": "Database created",
            "tests": "POST /uploads, GET /uploads, DELETE",
            },
        "fx": {
            "func": api_fx,
            "test_names": True,
            "name": "FX API",
            "desc": "Test FX endpoints",
            "prereq": "FX rates populated",
            "tests": "GET /currencies, POST /sync, GET /convert",
            },
        "fx-sync": {
            "func": api_fx_sync,
            "test_names": True,
            "name": "FX Sync API",
            "desc": "Test FX sync endpoints",
            "prereq": "External FX API working",
            "tests": "GET /currencies/sync",
            },
        "assets-metadata": {
            "func": api_assets_metadata,
            "test_names": True,
            "name": "Assets Metadata API",
            "desc": "Test asset metadata endpoints",
            "prereq": "Database created",
            "tests": "PATCH metadata, bulk read, refresh",
            },
        "assets-crud": {
            "func": api_assets_crud,
            "test_names": True,
            "name": "Assets CRUD API",
            "desc": "Test asset CRUD endpoints",
            "prereq": "Database created",
            "tests": "POST /bulk, GET /list, DELETE /bulk",
            },
        "assets-price": {
            "func": api_assets_price,
            "test_names": True,
            "name": "Assets Price API",
            "desc": "Test asset price endpoints",
            "prereq": "Database with assets",
            "tests": "Price history queries",
            },
        "assets-provider": {
            "func": api_assets_provider,
            "test_names": True,
            "name": "Assets Provider API",
            "desc": "Test asset provider assignment",
            "prereq": "Database created",
            "tests": "Provider assignment, validation",
            },
        "utilities": {
            "func": api_utilities,
            "test_names": True,
            "name": "Utilities API",
            "desc": "Test utility endpoints",
            "prereq": "None",
            "tests": "GET /utilities/sectors, /countries/normalize",
            },
        "transactions": {
            "func": api_transactions,
            "test_names": True,
            "name": "Transactions API",
            "desc": "Test transaction endpoints",
            "prereq": "Database created",
            "tests": "CRUD, validation, balance checks",
            },
        "brokers": {
            "func": api_brokers,
            "test_names": True,
            "name": "Brokers API",
            "desc": "Test broker endpoints",
            "prereq": "Database created",
            "tests": "CRUD, summary, access control",
            },
        "broker-access": {
            "func": api_broker_access,
            "test_names": True,
            "name": "Broker Access API",
            "desc": "Test broker access management",
            "prereq": "Database created",
            "tests": "Access grants, role validation",
            },
        "broker-multiuser": {
            "func": api_broker_multiuser,
            "test_names": True,
            "name": "Broker Multi-User API",
            "desc": "Test multi-user broker scenarios",
            "prereq": "Database created",
            "tests": "Sharing, permissions, isolation",
            },
        "brim": {
            "func": api_brim,
            "test_names": True,
            "name": "BRIM API",
            "desc": "Test BRIM endpoints",
            "prereq": "Database created",
            "tests": "File upload, parse, import",
            },
        "all": {
            "func": api_test,
            "test_names": False,
            "name": "All API Tests",
            "desc": "Run all API tests",
            },
        },
    "e2e": {
        "_meta": {
            "help": "E2E Tests with API Interaction",
            "description": """
E2E Tests with API Interaction

These tests verify complete end-to-end workflows via REST API:
  • Target: http://localhost:8001 (test server)
  • Backend server auto-started if not running
  • Tests complete user journeys
""",
            },
        "search-to-prices": {
            "func": search2prices_test,
            "test_names": True,
            "name": "Search to Prices E2E",
            "desc": "Test complete asset flow",
            "prereq": "Database created, providers configured",
            "tests": "Search → Create → Assign → Metadata → Prices",
            },
        "brim": {
            "func": e2e_brim,
            "test_names": True,
            "name": "BRIM E2E",
            "desc": "Test complete BRIM import flow",
            "prereq": "Database created",
            "tests": "Upload → Parse → Asset Mapping → Import",
            },
        "all": {
            "func": e2e_test,
            "test_names": False,
            "name": "All E2E Tests",
            "desc": "Run all E2E tests",
            },
        },
    "front": {
        "_meta": {
            "help": "Frontend E2E tests (Playwright on Chromium)",
            "description": """
Frontend E2E Tests

Browser-based tests using Playwright:
  • Backend server started automatically in test mode
  • Tests run on Chromium (headless by default)
  • Use --ui for interactive Playwright UI
  • Use --headed to see browser
  • Screenshots saved on failure

Note: gallery.spec.ts is NOT included in 'all' - use ./dev.py mkdocs gallery
""",
            },
        "auth": {
            "func": front_auth,
            "test_names": True,
            "name": "Auth Tests",
            "desc": "Login, register, logout, language change",
            "prereq": "Test users created",
            "tests": "auth.spec.ts",
            },
        "settings": {
            "func": front_settings,
            "test_names": True,
            "name": "Settings Tests",
            "desc": "User preferences, global settings (admin)",
            "prereq": "Login working",
            "tests": "settings.spec.ts",
            },
        "files": {
            "func": front_files,
            "test_names": True,
            "name": "Files Tests",
            "desc": "Files page, tabs, URL filters",
            "prereq": "Login working",
            "tests": "files.spec.ts",
            },
        "brokers": {
            "func": front_brokers,
            "test_names": True,
            "name": "Brokers Tests",
            "desc": "CRUD broker, import files modal",
            "prereq": "Login working",
            "tests": "brokers.spec.ts",
            },
        "multi-user": {
            "func": front_multi_user,
            "test_names": True,
            "name": "Multi-User Tests",
            "desc": "Data isolation between users",
            "prereq": "Multiple test users",
            "tests": "multi-user.spec.ts",
            },
        "all": {
            "func": front_all,
            "test_names": False,
            "name": "All Frontend Tests",
            "desc": "Run all E2E tests (excludes gallery)",
            },
        },
    }


def get_category_choices(category: str) -> list[str]:
    """Get list of valid actions for a category from TEST_REGISTRY (excluding _meta)."""
    if category not in TEST_REGISTRY:
        return []
    return [k for k in TEST_REGISTRY[category].keys() if k != "_meta"]


def generate_epilog(category: str) -> str:
    """Generate epilog text for a category parser from TEST_REGISTRY."""
    if category not in TEST_REGISTRY:
        return ""

    cat_data = TEST_REGISTRY[category]
    lines = []

    # Add category description from _meta
    if "_meta" in cat_data:
        lines.append(cat_data["_meta"].get("description", ""))
        lines.append("\nTest commands:")

    # Add each action
    for action, info in cat_data.items():
        if action == "_meta":
            continue

        desc = info.get("desc", "")
        prereq = info.get("prereq", "")
        tests = info.get("tests", "")
        note = info.get("note", "")

        lines.append(f"  {action:20} - {desc}")
        if prereq:
            lines.append(f"                       📋 Prerequisites: {prereq}")
        if tests:
            lines.append(f"                       💡 Tests: {tests}")
        if note:
            lines.append(f"                       Note: {note}")
        lines.append("")

    return "\n".join(lines)


def run_test_from_registry(category: str, action: str, verbose: bool = False,
                           test_names: list = None, **kwargs) -> bool:
    """
    Run a test from the registry.

    Args:
        category: Test category (e.g., "api", "db")
        action: Test action (e.g., "auth", "all")
        verbose: Verbose output
        test_names: Optional specific test names
        **kwargs: Additional args (e.g., force for db populate)

    Returns:
        bool: True if test passed
    """
    if category not in TEST_REGISTRY:
        print_error(f"Unknown category: {category}")
        return False

    if action not in TEST_REGISTRY[category] or action == "_meta":
        print_error(f"Unknown action '{action}' for category '{category}'")
        return False

    test_info = TEST_REGISTRY[category][action]
    test_func = test_info["func"]
    accepts_test_names = test_info.get("test_names", False)

    # Special case for db populate (has force flag)
    if category == "db" and action == "populate":
        force = kwargs.get("force", False)
        return test_func(verbose=verbose, force=force)

    # Special case for front category (has ui, headed, debug flags + test_names)
    if category == "front":
        ui = kwargs.get("ui", False)
        headed = kwargs.get("headed", False)
        debug = kwargs.get("debug", False)
        if accepts_test_names and test_names:
            return test_func(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names)
        return test_func(verbose=verbose, ui=ui, headed=headed, debug=debug)

    # Build arguments
    if accepts_test_names and test_names:
        return test_func(verbose=verbose, test_names=test_names)
    else:
        return test_func(verbose=verbose)


def create_subparser_from_registry(subparsers, category: str, extra_args: list = None):
    """
    Create a subparser for a category from TEST_REGISTRY.

    Args:
        subparsers: argparse subparsers object
        category: Category key in TEST_REGISTRY
        extra_args: Optional list of tuples (arg_name, arg_kwargs) for extra arguments

    Returns:
        Created subparser
    """
    if category not in TEST_REGISTRY:
        raise ValueError(f"Unknown category: {category}")

    meta = TEST_REGISTRY[category].get("_meta", {})

    parser = subparsers.add_parser(
        category,
        help=meta.get("help", f"{category} tests"),
        description=generate_epilog(category),
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    parser.add_argument(
        "action",
        choices=get_category_choices(category),
        help=f"{category.capitalize()} test to run"
        )

    parser.add_argument(
        "test_names",
        nargs="*",
        help="Optional: specific test names to run"
        )

    # Add any extra arguments
    if extra_args:
        for arg_name, arg_kwargs in extra_args:
            parser.add_argument(arg_name, **arg_kwargs)

    return parser


# ============================================================================
# MAIN ARGUMENT PARSER
# ============================================================================

def _generate_main_epilog() -> str:
    """Generate main parser epilog from TEST_REGISTRY."""
    lines = ["\nTest Categories:\n"]

    for category in TEST_REGISTRY.keys():
        meta = TEST_REGISTRY[category].get("_meta", {})
        help_text = meta.get("help", f"{category} tests")
        lines.append(f"  {category:8} - {help_text}")

    lines.append(f"  {'all':8} - Run ALL tests in optimal order")
    lines.append("")
    lines.append("Examples:")
    lines.append("  python test_runner.py all                 # All tests (optimal order)")
    lines.append("  python test_runner.py -v all              # All tests with verbose output")
    lines.append("  python test_runner.py api auth            # Only auth API tests")
    lines.append("  python test_runner.py db create           # Create database")
    lines.append("")
    lines.append("  # Via dev.sh")
    lines.append("  ./dev.sh test all                         # Complete test suite")
    lines.append("  ./dev.sh test api all                     # All API tests")

    return "\n".join(lines)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser using TEST_REGISTRY."""
    parser = argparse.ArgumentParser(
        description="LibreFolio Test Runner - Organized test execution",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_generate_main_epilog()
        )

    # Global flags
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show full test output",
        default=False
        )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with code coverage tracking",
        default=False
        )

    parser.add_argument(
        "--cov-clean",
        action="store_true",
        help="Clean coverage database before running tests",
        default=False
        )

    parser.add_argument(
        "--db-reset",
        action="store_true",
        help="Reset test database before running db tests",
        default=False
        )

    subparsers = parser.add_subparsers(
        dest="category",
        help="Test category to run",
        required=False
        )

    # Auto-generate subparsers from TEST_REGISTRY
    for category in TEST_REGISTRY.keys():
        extra_args = None
        if category == "db":
            extra_args = [
                (
                    "--force", {
                    "action": "store_true",
                    "help": "[populate only] Recreate from scratch",
                    "default": False,
                    }
                    ),
                ]
        elif category == "front":
            extra_args = [
                (
                    "--ui", {
                    "action": "store_true",
                    "help": "Run with Playwright interactive UI",
                    "default": False,
                    }
                    ),
                (
                    "--headed", {
                    "action": "store_true",
                    "help": "Run with visible browser window",
                    "default": False,
                    }
                    ),
                (
                    "--debug", {
                    "action": "store_true",
                    "help": "Run with step-by-step debugging (includes --headed)",
                    "default": False,
                    }
                    ),
                ]
        create_subparser_from_registry(subparsers, category, extra_args)

    # Special "all" category
    subparsers.add_parser(
        "all",
        help="Run ALL tests in optimal order",
        description="""
Complete Test Suite

Runs all test categories in optimal order:
  1. External Services
  2. Database Layer
  3. Schema Validation
  4. Utility Modules
  5. Services Layer
  6. API Endpoints
  7. E2E Tests

Expected time: 3-7 minutes
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    return parser


def register_subparser(parent_subparsers):
    """
    Register test commands as a subparser of dev.py.

    This allows dev.py to import and integrate test_runner's full parser,
    so `./dev.py test api auth` has full autocompletion support.
    """
    # Create the "test" subparser under dev.py
    test_parser = parent_subparsers.add_parser(
        "test",
        help="Run tests (api, db, external, schemas, services, utils, e2e, all)",
        description="LibreFolio Test Runner"
        )

    # Add the same global options
    test_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show full test output",
        default=False
        )

    test_parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with code coverage tracking",
        default=False
        )

    test_parser.add_argument(
        "--cov-clean",
        action="store_true",
        help="Clean coverage database before running tests",
        default=False
        )

    test_parser.add_argument(
        "--db-reset",
        action="store_true",
        help="Reset test database before running db tests",
        default=False
        )

    # Create subparsers for test categories
    test_subparsers = test_parser.add_subparsers(
        dest="category",
        title="Test categories",
        metavar=""
        )

    # Auto-generate from registry
    for category in TEST_REGISTRY.keys():
        extra_args = None
        if category == "db":
            extra_args = [
                (
                    "--force", {
                    "action": "store_true",
                    "help": "[populate only] Recreate from scratch",
                    "default": False,
                    }
                    ),
                ]
        elif category == "front":
            extra_args = [
                (
                    "--ui", {
                    "action": "store_true",
                    "help": "Run with Playwright interactive UI",
                    "default": False,
                    }
                    ),
                (
                    "--headed", {
                    "action": "store_true",
                    "help": "Run with visible browser window",
                    "default": False,
                    }
                    ),
                (
                    "--debug", {
                    "action": "store_true",
                    "help": "Run with step-by-step debugging (includes --headed)",
                    "default": False,
                    }
                    ),
                ]
        create_subparser_from_registry(test_subparsers, category, extra_args)

    # "all" category
    test_subparsers.add_parser(
        "all",
        help="Run ALL tests in optimal order"
        )

    # Set the dispatch function
    test_parser.set_defaults(func=_dispatch_test_command)

    return test_parser


def _dispatch_test_command(args):
    """Dispatch test command from dev.py."""
    global _COVERAGE_MODE

    if not args.category:
        print("Error: test category required. Use: ./dev.py test --help")
        return 1

    verbose = getattr(args, 'verbose', False)
    test_names = getattr(args, 'test_names', None)
    coverage = getattr(args, 'coverage', False)
    cov_clean = getattr(args, 'cov_clean', False)

    _COVERAGE_MODE = coverage

    if coverage:
        print_header("LibreFolio Test Suite - Coverage Mode")
        print(f"{Colors.YELLOW}📊 Running tests with code coverage tracking{Colors.NC}")
        print()

        if cov_clean:
            import subprocess
            result = subprocess.run(
                ["pipenv", "run", "coverage", "erase"],
                cwd=os.getcwd(),
                capture_output=True,
                text=True
                )
            if result.returncode == 0:
                print(f"{Colors.GREEN}✅ Coverage database reset{Colors.NC}\n")

    # Dispatch to appropriate handler
    return dispatch_to_category(args.category, test_names, verbose, args)


def dispatch_to_category(category: str, test_names, verbose: bool, args) -> int:
    """Dispatch to the appropriate test handler. Returns 0 on success, 1 on failure."""
    success = False

    if category == "all":
        success = run_all_tests(verbose=verbose)
    elif category in TEST_REGISTRY:
        action = getattr(args, 'action', None)
        if action:
            # Build kwargs based on category
            kwargs = {}
            if category == "db":
                kwargs['force'] = getattr(args, 'force', False)
            elif category == "front":
                kwargs['ui'] = getattr(args, 'ui', False)
                kwargs['headed'] = getattr(args, 'headed', False)
                kwargs['debug'] = getattr(args, 'debug', False)

            success = run_test_from_registry(
                category=category,
                action=action,
                verbose=verbose,
                test_names=test_names,
                **kwargs
                )
        else:
            print_error(f"No action specified for category '{category}'")
            return 1
    else:
        print_error(f"Unknown category: {category}")
        return 1

    return 0 if success else 1


def main():
    """Main entry point."""
    global _COVERAGE_MODE

    parser = create_parser()

    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # If no category provided, show help
    if not args.category:
        parser.print_help()
        return 1

    # Extract flags
    verbose = getattr(args, 'verbose', False)
    test_names = getattr(args, 'test_names', None)
    coverage = getattr(args, 'coverage', False)
    cov_clean = getattr(args, 'cov_clean', False)

    # Set global coverage flag
    _COVERAGE_MODE = coverage

    # If coverage mode, handle cov-clean and show message
    if coverage:
        print_header("LibreFolio Test Suite - Coverage Mode")
        print(f"{Colors.YELLOW}📊 Running tests with code coverage tracking{Colors.NC}")
        print(f"{Colors.BLUE}Coverage will accumulate across all test runs{Colors.NC}")
        print(f"{Colors.BLUE}Final report: htmlcov/index.html{Colors.NC}")
        print()

        # If --cov-clean flag, erase coverage database
        if cov_clean:
            print(f"{Colors.YELLOW}🗑️  Resetting coverage database...{Colors.NC}")
            result = subprocess.run(
                ["pipenv", "run", "coverage", "erase"],
                cwd=os.getcwd(),
                capture_output=True,
                text=True
                )
            if result.returncode == 0:
                print(f"{Colors.GREEN}✅ Coverage database reset{Colors.NC}\n")
            else:
                print(f"{Colors.RED}❌ Failed to reset coverage database{Colors.NC}")
                print(f"{Colors.RED}   Error: {result.stderr}{Colors.NC}\n")
        else:
            # Just clear old .coverage file (legacy behavior)
            coverage_file = Path(__file__).parent / '.coverage'
            if coverage_file.exists():
                coverage_file.unlink()
                print(f"{Colors.YELLOW}🗑️  Cleared previous coverage data{Colors.NC}\n")

    # Run tests
    result = dispatch_to_category(args.category, test_names, verbose, args)
    success = result == 0

    # If coverage mode, show final summary
    if _COVERAGE_MODE:
        print()
        print_header("Coverage Report Summary")
        if success:
            print_success("✅ All tests passed with coverage tracking!")
        else:
            print_warning("⚠️  Some tests failed, but coverage was still tracked")

        print()
        print(f"{Colors.GREEN}📊 Generating final coverage report...{Colors.NC}")
        print()

        # Generate final coverage report with table
        result = subprocess.run(
            ["pipenv", "run", "coverage", "report", "--skip-covered"],
            cwd=os.getcwd(),
            capture_output=False,  # Show output directly
            text=True
            )

        print()
        print(f"{Colors.GREEN}📊 Detailed reports:{Colors.NC}")
        print(f"   HTML: {Colors.BLUE}htmlcov/index.html{Colors.NC}")
        print(f"   Data: {Colors.BLUE}.coverage{Colors.NC}")
        print()
        print(f"{Colors.YELLOW}💡 View HTML report with:{Colors.NC}")
        print(f"└─▶ $ open htmlcov/index.html")
        print()
        print(f"{Colors.BLUE}ℹ️  The HTML report shows:{Colors.NC}")
        print(f"   • Line-by-line coverage (green = covered, red = not covered)")
        print(f"   • Coverage % for each file")
        print(f"   • Missing line numbers")
        print(f"   • Branch coverage")
        print()

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
