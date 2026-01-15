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
import os
import subprocess
import sys
import traceback
from pathlib import Path

import argcomplete

# Setup test database configuration and get test database path
from backend.test_scripts.test_db_config import setup_test_database, TEST_DB_PATH, TEST_DATABASE_URL
# Import test utilities (avoid code duplication)
from backend.test_scripts.test_utils import (Colors, print_header, print_section, print_success, print_error, print_warning, print_info)

# Global flag for coverage mode (set by main())
_COVERAGE_MODE = False


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
        result = subprocess.run(cmd, cwd=Path(__file__).parent, capture_output=not verbose, text=True, env=env)

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
    """
    Run all external tests (network-dependent).
    """
    print_header("LibreFolio External Tests")
    print_info("Testing external provider integrations")
    print_info("⚠️  WARNING: Requires internet connection for FX/Asset providers")
    print_info("⚠️  WARNING: May be slow")

    tests = [
        ("FX Providers (including multi-unit)", lambda: external_fx_providers(verbose)),
        ("Asset Providers", lambda: external_asset_providers(verbose)),
        ("BRIM Providers", lambda: external_brim_providers(verbose)),
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
    print_section("External Tests Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if success else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print_success("All external tests passed! 🎉")
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
        ("Referential Integrity (CASCADE/RESTRICT/UNIQUE/CHECK)", lambda: db_test_referential_integrity(verbose)),
        ("FX Rates Persistence", lambda: db_fx_rates(verbose)),
        ("BRIM Asset Search & Duplicates", lambda: db_brim(verbose)),
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
    print_header("LibreFolio Utility Tests")
    print_info("Testing utility modules and helper functions")

    tests = [
        ("Decimal Precision", lambda: utils_decimal_precision(verbose)),
        ("Datetime Utils", lambda: utils_datetime(verbose)),
        ("Financial Math", lambda: utils_financial_math(verbose)),
        ("Day Count Conventions", lambda: utils_day_count(verbose)),
        ("Compound Interest", lambda: utils_compound_interest(verbose)),
        ("Geographic Area Normalization", lambda: utils_geo_utils(verbose)),
        ("Sector Normalization", lambda: utils_sector_normalization(verbose)),
        # Note: Currency, Distribution Models, Scheduled Investment Schemas, and
        # FAGeographicArea Integration have been moved to schemas category
        ]

    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))

        if not success:
            print_error(f"Test failed: {test_name}")
            print_warning("Stopping utils tests execution")
            break

    # Summary
    print_section("Utility Tests Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if success else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print_success("All utility tests passed! 🎉")
        return True
    else:
        print_error(f"{total - passed} test(s) failed")
        return False


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
    print_header("LibreFolio Schema Validation Tests")
    print_info("Testing Pydantic schema validation rules")

    tests = [
        ("Common Schemas", lambda: schemas_common(verbose)),
        ("Asset Schemas", lambda: schemas_assets(verbose)),
        ("Transaction Schemas", lambda: schemas_transactions(verbose)),
        ("Broker Schemas", lambda: schemas_brokers(verbose)),
    ]

    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))
        if not success:
            print_error(f"Test failed: {test_name}")
            print_warning("Stopping schema tests execution")
            break

    # Summary
    print_section("Schema Tests Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if success else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    if passed == total:
        print_success("All schema tests passed! 🎉")
        return True
    else:
        print_error(f"{total - passed} test(s) failed")
        return False


def services_all(verbose: bool = False) -> bool:
    """
    Run all backend service tests.
    """
    print_header("LibreFolio Backend Services Tests")
    print_info("Testing business logic and service layer")
    print_info("No backend server required")

    # Ensure clean test database before running services tests
    print_info("\n⚙️  Creating clean test database for services tests...")
    if not db_create(verbose=False):
        print_error("Failed to create clean test database")
        print_warning("Services tests may fail due to dirty database state")
        # Continue anyway, don't block tests
    else:
        print_success("Clean test database created\n")

    tests = [
        ("FX Conversion Logic", lambda: services_fx_conversion(verbose)),
        ("Asset Source Logic", lambda: services_asset_source(verbose)),
        ("Asset Metadata Service", lambda: services_asset_metadata(verbose)),
        ("Asset Source Refresh (smoke)", lambda: services_asset_source_refresh(verbose)),
        ("Provider Registry", lambda: services_provider_registry(verbose)),
        ("Synthetic Yield Calculation", lambda: services_synthetic_yield(verbose)),
        ("Synthetic Yield Integration E2E", lambda: services_synthetic_yield_integration(verbose)),
        ("Transaction Service", lambda: services_transaction(verbose)),
        ("Broker Service", lambda: services_broker(verbose)),
        ("Transaction Edge Cases", lambda: services_edge_cases(verbose)),
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
    """
    Run all API tests.
    """
    print_header("LibreFolio API Tests")
    print_info("Testing REST API endpoints")
    print_info("Note: Server will be automatically started/stopped by tests")

    tests = [
        ("Auth API", lambda: api_auth(verbose)),
        ("Settings API", lambda: api_settings(verbose)),
        ("Uploads API", lambda: api_uploads(verbose)),
        ("FX API", lambda: api_fx(verbose)),
        ("FX Sync API", lambda: api_fx_sync(verbose)),
        ("Assets Metadata API", lambda: api_assets_metadata(verbose)),
        ("Assets CRUD API", lambda: api_assets_crud(verbose)),
        ("Assets Price API", lambda: api_assets_price(verbose)),
        ("Assets Provider API", lambda: api_assets_provider(verbose)),
        ("Utilities API", lambda: api_utilities(verbose)),
        ("Transactions API", lambda: api_transactions(verbose)),
        ("Brokers API", lambda: api_brokers(verbose)),
        ("Broker Access API", lambda: api_broker_access(verbose)),
        ("Broker Multi-User API", lambda: api_broker_multiuser(verbose)),
        ("BRIM API", lambda: api_brim(verbose)),
        ]

    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))

        if not success:
            print_error(f"Test failed: {test_name}")
            print_warning("Stopping API tests execution")
            break

    # Summary
    print_section("API Tests Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if success else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    # If coverage mode, combine coverage from all processes
    if _COVERAGE_MODE:
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

    if passed == total:
        print_success("All API tests passed! 🎉")
        return True
    else:
        print_error(f"{total - passed} test(s) failed")
        return False


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
    """
    Run all E2E tests.
    """
    print_header("LibreFolio E2E Tests with API interaction")
    print_info("Testing E2E workflow using REST API endpoints")
    print_info("Note: Server will be automatically started/stopped by tests")

    tests = [
        ("E2E search-to-prices Flow", lambda: search2prices_test(verbose)),
        ("E2E BRIM Import Flow", lambda: e2e_brim(verbose)),
        ]

    results = []
    for test_name, test_func in tests:
        success = test_func()
        results.append((test_name, success))

        if not success:
            print_error(f"Test failed: {test_name}")
            print_warning("Stopping E2E tests execution")
            break

    # Summary
    print_section("E2E Tests Summary")
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.NC}" if success else f"{Colors.RED}❌ FAIL{Colors.NC}"
        print(f"{status} - {test_name}")

    print(f"\nResults: {passed}/{total} tests passed")

    # If coverage mode, combine coverage from all processes
    if _COVERAGE_MODE:
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

    if passed == total:
        print_success("All API tests passed! 🎉")
        return True
    else:
        print_error(f"{total - passed} test(s) failed")
        return False



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
        ("Schema Validation", lambda: schemas_all(verbose)),
        ("Utility Modules", lambda: utils_all(verbose)),
        ("Services layers", lambda: services_all(verbose)),
        ("API Endpoints", lambda: api_test(verbose)),  # Auto-starts server via TestServerManager
        ("E2E Tests", lambda: e2e_test(verbose)), # Auto-starts server via TestServerManager
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

  utils    - Utility Module Tests
             Tests utility modules and helper functions (no backend server needed).
             Verifies: Decimal precision, datetime utils, financial math, ...

  schemas  - Schema Validation Tests
             Tests Pydantic schema validation rules (no backend server needed).
  
  api      - API Endpoint Tests  
             Tests REST API endpoints (requires running backend server).
             Verifies: HTTP endpoints, validation, error handling.
             Target: http://localhost:8000
  
  e2e      - E2E Tests with API interaction
  
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

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run tests with code coverage tracking (generates htmlcov/index.html report)",
        default=False
        )

    parser.add_argument(
        "--cov-clean",
        action="store_true",
        help="Clean coverage database before running tests (use with --coverage)",
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
  • Tests connections to live external APIs (requires internet)
  • Verifies data availability and format

Test commands:
  fx-providers    - Test all FX providers (ECB, FED, BOE, etc.)
                    Tests: Metadata, API connection, rate fetching, normalization
                    📋 Prerequisites: Internet connection
                    💡 Repeats tests for all configured FX providers
  
  asset-providers - Test all asset providers (yfinance, cssscraper, etc.)
                    Tests: Metadata, current value, historical data, search, error handling
                    Note: Tests auto-skip if provider doesn't support feature (e.g., search)
                    📋 Prerequisites: Internet connection

  brim-providers  - Test BRIM (Broker Report Import Manager) plugins
                    Tests: Plugin discovery, file parsing, auto-detection, sample coverage
                    Brokers: Directa, DEGIRO, Trading212, IBKR, eToro, Revolut, etc.
                    📋 Prerequisites: None (uses local sample files)
         
  all             - Run all external service tests
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    external_parser.add_argument(
        "action",
        choices=["fx-providers", "asset-providers", "brim-providers", "all"],
        help="External service test to run"
        )

    external_parser.add_argument(
        "test_names",
        nargs="*",
        help="Optional: specific test names to run (e.g., test_ecb_provider)"
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
  create                - Delete existing DB and create fresh from migrations
                        📋 Prerequisites: None - this is the first test to run
    
  validate              - Verify all tables, constraints, indexes, foreign keys
                          📋 Prerequisites: Database created (run: db create)
    
  numeric-truncation     - Test Numeric column truncation for ALL tables
                         📋 Prerequisites: Database created (run: db create)
                         💡 Tests helper functions and database precision handling
    
  populate              - Populate database with MOCK DATA for testing/frontend dev
                          📋 Prerequisites: Database created (run: db create)
                          💡 Use --force to delete existing data and recreate
                
  fx-rates              - Test FX rates persistence (fetch from ECB & persist)
                          📋 Prerequisites: External ECB API working (run: external ecb)
                          💡 Can run on database with existing data (uses UPSERT)

  brim                  - Test BRIM asset search & duplicate detection
                          📋 Prerequisites: Database created (run: db create)
                          💡 Tests: Asset candidate search, duplicate transaction detection
    
  referential-integrity - Test unidirectional relationship between Transaction and CashMovement
                          📋 Prerequisites: Database created (run: db create)
                          💡 Validates referential integrity, CASCADE delete, CHECK constraints between the tables
                                enum mapping, logical constraints, CashMovement consistency, etc.
                            
  all               - Run all DB tests (create → validate → numeric-truncation → populate → fx-rates → brim)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    db_parser.add_argument(
        "action",
        choices=["create", "validate", "numeric-truncation", "fx-rates", "brim", "populate", "referential-integrity", "all"],
        help="Database test to run"
        )

    db_parser.add_argument(
        "test_names",
        nargs="*",
        help="Optional: specific test names to run (e.g., test_tables_exist)"
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
  fx-conversion        - Test FX conversion service logic (identity, direct, inverse, cross-currency, forward-fill)
                         📋 Prerequisites: DB FX rates subsystem (run: db fx-rates)

  asset-source         - Test Asset Source service logic (provider assignment, helpers, synthetic yield)
                         📋 Prerequisites: Database created (run: db create)
                         💡 Tests: Helper functions (truncation, ACT/365), Provider assignment (bulk/single), Synthetic yield
  
  asset-source-refresh - Smoke test: Asset Source refresh orchestration
                         📋 Prerequisites: Database created (run: db create)
                         💡 Runs lightweight refresh orchestration smoke test using a mock provider

  asset-metadata      - Test AssetMetadataService static utility behavior
                        📋 Prerequisites: Database created (run: db create)
                        💡 Tests: parse/serialize, diff, patch semantics
  
  provider-registry   - Test provider registry (asset & fx)
                        📋 Prerequisites: Database created (run: db create)
                        💡 Tests: Registration, lookup, priority, fallback
  
  synthetic-yield      - Test synthetic yield calculation for SCHEDULED_YIELD assets
                         📋 Prerequisites: Database created (run: db create)
                         💡 Tests: ACT/365 day count, rate lookup, accrued interest, full valuation
  
  synthetic-yield-integration - Test E2E synthetic yield integration scenarios (P2P loan, bond, mixed schedule)
                              📋 Prerequisites: Database created (run: db create)
                              💡 Scenarios: P2P loan (grace + late), bond compound quarterly, mixed SIMPLE/COMPOUND
  
  all                   - Run all backend service tests
  
Future: FIFO calculations, portfolio aggregations, loan schedules will be added here
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    services_parser.add_argument(
        "action",
        choices=["fx-conversion", "asset-source", "asset-metadata", "asset-source-refresh", "provider-registry", "synthetic-yield", "synthetic-yield-integration", "transaction", "broker", "edge-cases", "all"],
        help="Service test to run"
        )

    services_parser.add_argument(
        "test_names",
        nargs="*",
        help="Optional: specific test names to run (e.g., test_direct_conversion)"
        )

    # ========================================================================
    # UTILS TESTS SUBPARSER
    # ========================================================================
    utils_parser = subparsers.add_parser(
        "utils",
        help="Utility module tests (helper functions)",
        description="""
Utility Module Tests

These tests verify utility modules and helper functions:
  • No backend server required
  • Tests pure functions and helpers
  • Foundational code used across the application

Test commands:
  decimal-precision - Test decimal precision utilities (Phase 2 task 3.2)
                      📋 Prerequisites: None
                      💡 Tests: get_model_column_precision(), truncate_to_db_precision()
                      
  datetime         - Test datetime utilities (Phase 1 task 3.1)
                     📋 Prerequisites: None
                     💡 Tests: utcnow() timezone-aware datetime helper
                     
  financial-math   - Test financial math utilities
                     📋 Prerequisites: None
                     💡 Tests: Day count conventions (ACT/365), Interest calculations, Rate finding
  
  day-count        - Test day count conventions (Phase 4 task 2.1)
                     📋 Prerequisites: None
                     💡 Tests: ACT/365, ACT/360, ACT/ACT, 30/360 conventions with exact comparisons
  
  compound-interest - Test compound interest calculations (Phase 4 task 2.1)
                      📋 Prerequisites: None
                      💡 Tests: Simple, Compound (annual, semiannual, quarterly, monthly, daily, continuous)
  
  geo-normalization - Test geographic area normalization utilities (Phase 5.1)
                      📋 Prerequisites: pycountry installed
                      💡 Tests: ISO-3166-A3 conversion, weight validation, sum normalization
  
  sector-normalization - Test FinancialSector enum and sector normalization
                         📋 Prerequisites: None
                         💡 Tests: Sector enum values, aliases, normalization to standard names
  
  all              - Run all utility tests

Note: Currency, Distribution Models, Scheduled Investment Schemas and Geographic Area 
      Integration tests have been migrated to the 'schemas' category.
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    utils_parser.add_argument(
        "action",
        choices=[
            "decimal-precision",
            "datetime",
            "financial-math",
            "day-count",
            "compound-interest",
            "geo-normalization",
            "sector-normalization",
            "all",
            ],
        help="Utility test to run",
        )

    utils_parser.add_argument(
        "test_names",
        nargs="*",
        help="Optional: specific test names to run (e.g., test_utcnow)"
        )

    # ========================================================================
    # SCHEMAS TESTS SUBPARSER
    # ========================================================================
    schemas_parser = subparsers.add_parser(
        "schemas",
        help="Pydantic schema validation tests",
        description="""
Schema Validation Tests

These tests verify Pydantic schema validation rules:
  • No backend server required
  • Tests DTO validation, business rules, serialization
  • Pure unit tests (no database needed)

Test commands:
  common           - Test common schemas (Currency, DateRangeModel, OldNew)
                     📋 Prerequisites: None
                     💡 Tests: Creation, validation, arithmetic, serialization
  
  assets           - Test asset-related schemas (FAGeographicArea, FAInterestRatePeriod, etc.)
                     📋 Prerequisites: None
                     💡 Tests: Distribution validation, interest periods, schedule continuity
  
  transactions     - Test transaction schemas (TXCreateItem, TXReadItem, TXUpdateItem)
                     📋 Prerequisites: None
                     💡 Tests: Type rules, link_uuid, cash/asset requirements, sign validation
  
  brokers          - Test broker schemas (BRCreateItem, BRReadItem, BRUpdateItem)
                     📋 Prerequisites: None
                     💡 Tests: Name validation, initial_balances, delete force flag
  
  all              - Run all schema tests
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    schemas_parser.add_argument(
        "action",
        choices=["common", "assets", "transactions", "brokers", "all"],
        help="Schema test to run"
        )

    schemas_parser.add_argument(
        "test_names",
        nargs="*",
        help="Optional: specific test names to run (e.g., test_transfer_requires_link_uuid)"
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
  • Target: http://localhost:8001 (test server)
  • Backend server auto-started if not running
  • Tests HTTP requests/responses, validation, error handling

Test commands:
  auth            - Test Authentication endpoints (register, login, logout, me)
                    📋 Prerequisites: Database created (run: db create)
                    💡 Tests: POST /auth/register, POST /auth/login, POST /auth/logout, GET /auth/me
                    Note: Server will be automatically started and stopped by test

  settings        - Test Settings endpoints (GET /settings/user, PUT /settings/user,
                    GET /settings/global, PUT /settings/global)
                    📋 Prerequisites: Database created (run: db create)

  fx              - Test FX endpoints (GET /currencies, POST /sync, GET /convert)
                    📋 Prerequisites: Services FX conversion subsystem (run: db fx-rates)
                    Note: Server will be automatically started and stopped by test

  fx-sync         - Test FX sync endpoints (GET /currencies/sync)
                    📋 Prerequisite: External FX API working (run: external all)
                    Note: Server will be automatically started and stopped by test
  
  assets-metadata - Test Assets Metadata endpoints (PATCH, bulk read, refresh)
                    📋 Prerequisites: Database created (run: db create)
                    💡 Tests: PATCH metadata, bulk read, single/bulk refresh, provider assignments
                    Note: Server will be automatically started and stopped by test
  
  assets-crud     - Test Assets CRUD endpoints (create, list, delete)
                    📋 Prerequisites: Database created (run: db create)
                    💡 Tests: POST /bulk (create), GET /list (filter), DELETE /bulk
                    Note: Server will be automatically started and stopped by test

  assets-provider - Test Asset provider assignment enpoint
                    Note: Server will be automatically started and stopped by test
                    
  assets-price    - Test Asset price data endpoint
                    Note: Server will be automatically started and stopped by test
  
  utilities       - Test Utilities endpoints (sectors list, country normalization)
                    📋 Prerequisites: None
                    💡 Tests: GET /utilities/sectors, GET /utilities/countries/normalize
                    Note: Server will be automatically started and stopped by test

  brim            - Test BRIM (Broker Report Import Manager) endpoints
                    📋 Prerequisites: Database created (run: db create)
                    💡 Tests: File upload/list/delete, parse, E2E import flow
                    Note: Server will be automatically started and stopped by test
  
  e2e             - Test complete End-to-End flow
                    📋 Prerequisites: Database created, providers configured
                    💡 Tests: Search → Create → Assign Provider → Metadata → Prices
                    Note: Server will be automatically started and stopped by test
                    
  all             - Run all API tests (FX + Assets Metadata + Assets CRUD + ...)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    api_parser.add_argument(
        "action",
        choices=["auth", "settings", "uploads", "fx", "fx-sync", "assets-metadata", "assets-crud", "assets-provider", "assets-price", "utilities", "transactions", "brokers", "broker-access", "broker-multiuser", "brim", "all"],
        help="API test to run"
        )

    api_parser.add_argument(
        "test_names",
        nargs="*",
        help="Optional: specific test names to run (e.g., test_get_currencies)"
        )

    # ========================================================================
    # E2E TESTS SUBPARSER
    # ========================================================================
    e2e_parser = subparsers.add_parser(
        "e2e",
        help="E2E Tests with API Interaction",
        description="""
E2E Tests with API Interaction
These tests verify complete end-to-end workflows via REST API:
  • Target: http://localhost:8001 (test server)
  • Backend server auto-started if not running

  search-to-prices  - Test complete flow: Search → Create → Assign → Metadata → Prices
                      📋 Prerequisites: Database created, providers configured
                      💡 Tests: Search asset, create asset, assign provider, refresh metadata, refresh prices
                      Note: Server will be automatically started and stopped by test

  brim              - Test complete BRIM import flow: Upload → Parse → Import
                      📋 Prerequisites: Database created
                      💡 Tests: Upload file, parse with plugin, asset mapping, duplicate detection, import
                      Note: Server will be automatically started and stopped by test
                      
  all               - Run all E2E tests with API interaction

        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    e2e_parser.add_argument(
        "action",
        choices=["search-to-prices", "brim", "all"],
        help="End-to-End tests with API interaction (auto-starts server if needed)"
        )

    e2e_parser.add_argument(
        "test_names",
        nargs="*",
        help="Optional: specific test names to run"
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

    # Route to appropriate test handler (normal mode - coverage handled by run_command)
    success = False

    if args.category == "all":
        # Run complete test suite
        success = run_all_tests(verbose=verbose)

    elif args.category == "external":
        # External services tests
        if args.action == "fx-providers":
            success = external_fx_providers(verbose=verbose, test_names=test_names)
        elif args.action == "asset-providers":
            success = external_asset_providers(verbose=verbose, test_names=test_names)
        elif args.action == "brim-providers":
            success = external_brim_providers(verbose=verbose, test_names=test_names)
        elif args.action == "all":
            success = external_all(verbose=verbose)

    elif args.category == "db":
        # Database tests
        if args.action == "create":
            success = db_create(verbose=verbose)
        elif args.action == "validate":
            success = db_validate(verbose=verbose, test_names=test_names)
        elif args.action == "numeric-truncation":
            success = db_numeric_truncation(verbose=verbose, test_names=test_names)
        elif args.action == "fx-rates":
            success = db_fx_rates(verbose=verbose, test_names=test_names)
        elif args.action == "brim":
            success = db_brim(verbose=verbose, test_names=test_names)
        elif args.action == "populate":
            force = getattr(args, 'force', False)
            success = db_populate(verbose=verbose, force=force)
        elif args.action == "referential-integrity":
            success = db_test_referential_integrity(verbose=verbose, test_names=test_names)
        elif args.action == "all":
            success = db_all(verbose=verbose)

    elif args.category == "services":
        # Backend services tests
        if args.action == "fx-conversion":
            success = services_fx_conversion(verbose=verbose, test_names=test_names)
        elif args.action == "asset-source":
            success = services_asset_source(verbose=verbose, test_names=test_names)
        elif args.action == "asset-metadata":
            success = services_asset_metadata(verbose=verbose, test_names=test_names)
        elif args.action == "asset-source-refresh":
            success = services_asset_source_refresh(verbose=verbose, test_names=test_names)
        elif args.action == "provider-registry":
            success = services_provider_registry(verbose=verbose, test_names=test_names)
        elif args.action == "synthetic-yield":
            success = services_synthetic_yield(verbose=verbose, test_names=test_names)
        elif args.action == "synthetic-yield-integration":
            success = services_synthetic_yield_integration(verbose=verbose, test_names=test_names)
        elif args.action == "transaction":
            success = services_transaction(verbose=verbose, test_names=test_names)
        elif args.action == "broker":
            success = services_broker(verbose=verbose, test_names=test_names)
        elif args.action == "edge-cases":
            success = services_edge_cases(verbose=verbose, test_names=test_names)
        elif args.action == "all":
            success = services_all(verbose=verbose)

    elif args.category == "utils":
        # Utility module tests
        if args.action == "decimal-precision":
            success = utils_decimal_precision(verbose=verbose, test_names=test_names)
        elif args.action == "datetime":
            success = utils_datetime(verbose=verbose, test_names=test_names)
        elif args.action == "financial-math":
            success = utils_financial_math(verbose=verbose, test_names=test_names)
        elif args.action == "day-count":
            success = utils_day_count(verbose=verbose, test_names=test_names)
        elif args.action == "compound-interest":
            success = utils_compound_interest(verbose=verbose, test_names=test_names)
        elif args.action == "geo-normalization":
            success = utils_geo_utils(verbose=verbose, test_names=test_names)
        elif args.action == "sector-normalization":
            success = utils_sector_normalization(verbose=verbose, test_names=test_names)
        elif args.action == "all":
            success = utils_all(verbose=verbose)

    elif args.category == "schemas":
        # Schema validation tests
        if args.action == "common":
            success = schemas_common(verbose=verbose, test_names=test_names)
        elif args.action == "assets":
            success = schemas_assets(verbose=verbose, test_names=test_names)
        elif args.action == "transactions":
            success = schemas_transactions(verbose=verbose, test_names=test_names)
        elif args.action == "brokers":
            success = schemas_brokers(verbose=verbose, test_names=test_names)
        elif args.action == "all":
            success = schemas_all(verbose=verbose)

    elif args.category == "api":
        # API tests
        if args.action == "fx":
            success = api_fx(verbose=verbose, test_names=test_names)
        elif args.action == "fx-sync":
            success = api_fx_sync(verbose=verbose, test_names=test_names)
        elif args.action == "assets-metadata":
            success = api_assets_metadata(verbose=verbose, test_names=test_names)
        elif args.action == "assets-crud":
            success = api_assets_crud(verbose=verbose, test_names=test_names)
        elif args.action == "assets-price":
            success = api_assets_price(verbose=verbose, test_names=test_names)
        elif args.action == "assets-provider":
            success = api_assets_provider(verbose=verbose, test_names=test_names)
        elif args.action == "utilities":
            success = api_utilities(verbose=verbose, test_names=test_names)
        elif args.action == "transactions":
            success = api_transactions(verbose=verbose, test_names=test_names)
        elif args.action == "brokers":
            success = api_brokers(verbose=verbose, test_names=test_names)
        elif args.action == "broker-access":
            success = api_broker_access(verbose=verbose, test_names=test_names)
        elif args.action == "broker-multiuser":
            success = api_broker_multiuser(verbose=verbose, test_names=test_names)
        elif args.action == "brim":
            success = api_brim(verbose=verbose, test_names=test_names)
        elif args.action == "auth":
            success = api_auth(verbose=verbose, test_names=test_names)
        elif args.action == "settings":
            success = api_settings(verbose=verbose, test_names=test_names)
        elif args.action == "uploads":
            success = api_uploads(verbose=verbose, test_names=test_names)
        elif args.action == "all":
            success = api_test(verbose=verbose)
    
    elif args.category == "e2e":
        # E2E tests
        if args.action == "search-to-prices":
            success = search2prices_test(verbose=verbose, test_names=test_names)
        elif args.action == "brim":
            success = e2e_brim(verbose=verbose, test_names=test_names)
        elif args.action == "all":
            success = e2e_test(verbose=verbose)

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
