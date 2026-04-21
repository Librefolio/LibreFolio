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
import inspect
import os
import re
import shutil
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Callable

import argcomplete

# Ensure project root is in path (file is in scripts/)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Change to project root so relative paths work
os.chdir(PROJECT_ROOT)

from scripts.cli_base import auto_build_frontend, pipenv_prefix
from scripts.coverage_analysis import register_subparser as register_cov_parser, run_analysis as run_coverage_analysis

# Setup test database configuration and get test database path
from backend.test_scripts.test_db_config import setup_test_database, TEST_DB_PATH, TEST_DATABASE_URL
# Import test utilities (avoid code duplication)
from backend.test_scripts.test_utils import Colors, print_header, print_section, print_success, print_error, print_warning, print_info

# Global flag for coverage mode (set by main())
_COVERAGE_MODE = False
# Coverage source: "backend", "frontend", or None (auto-detect)
_COVERAGE_SOURCE = None


def _run_test_suite(
    suite_name: str,
    tests: list[tuple[str, Callable]],
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
                ["coverage", "combine", "--keep"],
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
    cmd = [*pipenv_prefix(), "python", "-m", "pytest", test_path, "-v"]
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
                # Use source-specific HTML directory
                html_dir = "htmlcov-backend" if _COVERAGE_SOURCE != "frontend" else "htmlcov-frontend"
                flags_to_add.extend([
                    '--cov=backend/app',
                    '--cov-append',  # Append to existing coverage data
                    f'--cov-report=html:{html_dir}',
                    '--cov-report=term-missing:skip-covered',
                    ])
            # Insert after pytest command
            if flags_to_add:
                cmd = cmd[:pytest_idx + 1] + flags_to_add + cmd[pytest_idx + 1:]
                if use_coverage:
                    print(f"{Colors.YELLOW}📊 Coverage tracking enabled (appending to .coverage){Colors.NC}")
    print(f"\n{Colors.BLUE}Running: {description}{Colors.NC}")
    print(f"Command:\n└─▶ $ {' '.join(cmd)}")

    # --- Coverage isolation: swap-in the correct accumulated DB ---
    # Persistent DBs live in .coverage_data/ (safe from pytest-cov's combine).
    # Before pytest: copy the right DB → .coverage (so --cov-append appends to it).
    # After pytest: copy .coverage back → .coverage_data/ (accumulate).
    if use_coverage:
        cwd_p = Path(os.getcwd())
        data_dir = cwd_p / ".coverage_data"
        data_dir.mkdir(exist_ok=True)
        source = _COVERAGE_SOURCE or "backend"  # default to backend for non-meta categories
        accumulated_db = data_dir / source
        main_cov = cwd_p / ".coverage"
        # Swap-in: restore accumulated DB so pytest-cov appends to it
        if accumulated_db.exists():
            shutil.copy2(str(accumulated_db), str(main_cov))

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

    finally:
        # --- Swap-out: save .coverage back to .coverage_data/ ---
        # No archiving here — archive happens once at session end in _finalize_coverage
        if use_coverage:
            cwd_p = Path(os.getcwd())
            main_cov = cwd_p / ".coverage"
            if main_cov.exists():
                data_dir = cwd_p / ".coverage_data"
                source = _COVERAGE_SOURCE or "backend"
                shutil.copy2(str(main_cov), str(data_dir / source))


# ============================================================================
# EXTERNAL SERVICES TESTS
# ============================================================================

# ── Provider discovery for dynamic CLI help & filtering ─────────────────

# Regex to extract provider_code from property definitions like:
#   @property
#   def provider_code(self) -> str:
#       return "yfinance"
_PROVIDER_CODE_RE = re.compile(
    r'def\s+provider_code\s*\(self\).*?\n\s+(?:"""[^"]*"""\n\s+)?return\s+["\']([^"\']+)["\']',
    re.MULTILINE,
)

# Fallback regex for FX providers where provider_code delegates to code property:
#   def code(self) -> str:
#       return "ECB"
_CODE_RE = re.compile(
    r'def\s+code\s*\(self\).*?\n\s+return\s+["\']([^"\']+)["\']',
    re.MULTILINE,
)

# Provider folder mapping (relative to PROJECT_ROOT/backend/app/services/)
_PROVIDER_FOLDERS = {
    "asset": "asset_source_providers",
    "fx":    "fx_providers",
    "brim":  "brim_providers",
}


def _discover_provider_codes(registry_type: str) -> list[str]:
    """
    Discover provider codes by scanning source files with regex.

    This avoids importing provider modules (which would trigger heavy side-effects
    like TTL cache creation, logging, and network client initialisation).

    Uses two patterns:
      1. ``def provider_code(self): return "literal"``
      2. ``def code(self): return "literal"`` (FX providers delegate provider_code → code)

    Args:
        registry_type: "asset", "fx", or "brim"

    Returns:
        Sorted list of provider code strings (e.g. ['css_scraper', 'justetf', 'yfinance'])
    """
    folder_name = _PROVIDER_FOLDERS.get(registry_type)
    if not folder_name:
        return []

    target_dir = PROJECT_ROOT / "backend" / "app" / "services" / folder_name
    if not target_dir.exists():
        return []

    codes: list[str] = []
    for py in target_dir.glob("*.py"):
        if py.name == "__init__.py":
            continue
        try:
            text = py.read_text(encoding="utf-8")
            match = _PROVIDER_CODE_RE.search(text)
            if not match:
                # Fallback: try the `def code(self)` pattern (used by FX providers)
                match = _CODE_RE.search(text)
            if match:
                codes.append(match.group(1))
        except Exception:
            continue
    return sorted(codes)


# Cache at module level (discovered once per run)
_ASSET_PROVIDER_CODES: list[str] | None = None
_FX_PROVIDER_CODES: list[str] | None = None
_BRIM_PROVIDER_CODES: list[str] | None = None


def get_asset_provider_codes() -> list[str]:
    """Get available asset provider codes (cached)."""
    global _ASSET_PROVIDER_CODES
    if _ASSET_PROVIDER_CODES is None:
        _ASSET_PROVIDER_CODES = _discover_provider_codes("asset")
    return _ASSET_PROVIDER_CODES


def get_fx_provider_codes() -> list[str]:
    """Get available FX provider codes (cached)."""
    global _FX_PROVIDER_CODES
    if _FX_PROVIDER_CODES is None:
        _FX_PROVIDER_CODES = _discover_provider_codes("fx")
    return _FX_PROVIDER_CODES


def get_brim_provider_codes() -> list[str]:
    """Get available BRIM provider codes (cached)."""
    global _BRIM_PROVIDER_CODES
    if _BRIM_PROVIDER_CODES is None:
        _BRIM_PROVIDER_CODES = _discover_provider_codes("brim")
    return _BRIM_PROVIDER_CODES


def _build_provider_filter_expr(providers: list[str] | None, exclude_providers: list[str] | None) -> str | None:
    """
    Build a pytest -k expression to include/exclude providers.

    Args:
        providers: If set, ONLY these providers will be tested
        exclude_providers: If set, these providers will be EXCLUDED

    Returns:
        A pytest -k expression string, or None if no filtering
    """
    if providers:
        return " or ".join(providers)
    elif exclude_providers:
        return " and ".join(f"not {p}" for p in exclude_providers)
    return None

def external_fx_providers(verbose: bool = False, test_names: list = None,
                          providers: list = None, exclude_providers: list = None) -> bool:
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

    if providers:
        print_info(f"🔍 Filter: ONLY providers → {', '.join(providers)}")
    if exclude_providers:
        print_info(f"🚫 Filter: EXCLUDING providers → {', '.join(exclude_providers)}")

    # Merge provider filter into test_names (both use pytest -k)
    effective_names = list(test_names) if test_names else []
    provider_expr = _build_provider_filter_expr(providers, exclude_providers)
    if provider_expr:
        effective_names.append(provider_expr)

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_fx_providers.py",
                            effective_names or None)
    return run_command(cmd, "FX providers external tests", verbose=verbose)


def external_asset_providers(verbose: bool = False, test_names: list = None,
                             providers: list = None, exclude_providers: list = None) -> bool:
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

    if providers:
        print_info(f"🔍 Filter: ONLY providers → {', '.join(providers)}")
    if exclude_providers:
        print_info(f"🚫 Filter: EXCLUDING providers → {', '.join(exclude_providers)}")

    # Merge provider filter into test_names (both use pytest -k)
    effective_names = list(test_names) if test_names else []
    provider_expr = _build_provider_filter_expr(providers, exclude_providers)
    if provider_expr:
        effective_names.append(provider_expr)

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_asset_providers.py",
                            effective_names or None)
    return run_command(cmd, "Asset providers tests", verbose=verbose)


def external_brim_providers(verbose: bool = False, test_names: list = None,
                            providers: list = None, exclude_providers: list = None) -> bool:
    """
    Test BRIM (Broker Report Import Manager) providers.

    Tests plugin discovery, file parsing, auto-detection, and sample file coverage.
    Does NOT require network - tests are based on local sample files.
    """
    print_section("External: BRIM Providers Tests")
    print_info("Testing: Broker Report Import Manager (BRIM) plugins")
    print_info("Tests: Plugin discovery, file parsing, auto-detection, sample coverage")
    print_info("Brokers: Directa, DEGIRO, Trading212, IBKR, eToro, Revolut, Schwab, etc.")

    if providers:
        print_info(f"🔍 Filter: ONLY providers → {', '.join(providers)}")
    if exclude_providers:
        print_info(f"🚫 Filter: EXCLUDING providers → {', '.join(exclude_providers)}")

    # Merge provider filter into test_names (both use pytest -k)
    effective_names = list(test_names) if test_names else []
    provider_expr = _build_provider_filter_expr(providers, exclude_providers)
    if provider_expr:
        effective_names.append(provider_expr)

    cmd = _build_pytest_cmd("backend/test_scripts/test_external/test_brim_providers.py",
                            effective_names or None)
    return run_command(cmd, "BRIM providers tests", verbose=verbose)


def external_all(verbose: bool = False,
                 providers: list = None, exclude_providers: list = None) -> bool:
    """Run all external tests (network-dependent)."""
    # Build test list, forwarding provider filters to functions that accept them
    tests = []
    for action, info in TEST_REGISTRY.get("external", {}).items():
        if action in ("_meta", "all"):
            continue
        func = info["func"]
        name = info.get("name", action)
        func_params = inspect.signature(func).parameters
        if "providers" in func_params:
            tests.append((name, lambda f=func, v=verbose, p=providers, ep=exclude_providers:
                          f(verbose=v, providers=p, exclude_providers=ep)))
        else:
            tests.append((name, lambda f=func, v=verbose: f(verbose=v)))

    return _run_test_suite(
        suite_name="External Tests",
        tests=tests,
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


def db_populate(verbose: bool = False, force: bool = False,
                clean: bool = False, with_static: bool = False,
                with_reports: bool = False) -> bool:
    """
    Populate database with mock data for testing.
    Inserts comprehensive sample data (useful for frontend development).

    Args:
        verbose: Show verbose output
        force: Delete existing database and recreate from scratch
        clean: Clean data dirs (custom-uploads, broker_reports) before populating
        with_static: Upload static resources (avatars, broker icons)
        with_reports: Upload sample broker report files
    """
    print_section("Database Mock Data Population")

    print_info(f"This test operates on: {TEST_DB_PATH}")
    print_info("The backend server is NOT used in this test")
    print_info("⚠️  Populating MOCK DATA for testing purposes")

    if force:
        print_warning("--force flag detected: Will DELETE existing data")
    cmd = [*pipenv_prefix(), "python", "-m", "backend.test_scripts.test_db.populate_mock_data"]
    if force:
        cmd.append("--force")
    if clean:
        cmd.append("--clean")
    if with_static:
        cmd.append("--with-static")
    if with_reports:
        cmd.append("--with-reports")

    success = run_command(
        cmd,
        "Mock data population",
        verbose=verbose
        )

    # If failed and not verbose, provide helpful hint
    if not success and not verbose:
        print_warning("\n💡 Hint: Database might already contain data")
        print_info("   Run with -v to see detailed error:")
        print_info(f"     dev.py test -v db populate")
        print_info("   Or use --force to delete and recreate:")
        print_info(f"     dev.py test db populate --force")

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


def db_model_validators(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test Pydantic/SQLModel field validators on DB models.
    Validates currency, ISIN, ticker normalization and rejection of invalid data.
    """
    print_section("DB Test: Model Validators")
    print_info("Testing: Currency validation, ISIN/ticker normalization, FxRoute properties")
    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_model_validators.py", test_names)
    return run_command(cmd, "Model validator tests", verbose=verbose)


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
        "referential-integrity", "fx-rates", "brim", "model-validators"
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


def services_provider_contracts(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test provider interface contracts (FX, Asset, BRIM).
    Offline parametrized tests that validate ABC compliance for ALL registered providers.
    """
    print_section("Services: Provider Contract Tests")
    print_info("Testing: Interface compliance for ALL registered providers (offline, no HTTP)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_provider_contracts.py", test_names)
    return run_command(cmd, "Provider contract tests", verbose=verbose)


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

    cmd = [*pipenv_prefix(), "python", "-m", "pytest", "backend/test_scripts/test_services/test_transaction_service.py", "-v"]
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

    cmd = [*pipenv_prefix(), "python", "-m", "pytest", "backend/test_scripts/test_services/test_broker_service.py", "-v"]
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


def services_global_settings(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test GlobalSettingsService: _convert_value, get_setting_value, typed getters.
    """
    print_section("Services: Global Settings Service")
    print_info("Testing: backend/app/services/global_settings_service.py")
    print_info("Tests: Type conversion, DB reads with defaults, TTL/upload/registration getters")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_global_settings_service.py", test_names)
    return run_command(cmd, "Global settings service tests", verbose=verbose)


def services_fx_core(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test FX core helpers: normalize_rate_for_storage, upsert/delete bulk, count changes.
    """
    print_section("Services: FX Core Helpers")
    print_info("Testing: backend/app/services/fx.py (core functions not covered by fx-conversion)")
    print_info("Tests: normalize_rate, upsert_rates_bulk, delete_rates_bulk, _count_actual_changes")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_fx_core.py", test_names)
    return run_command(cmd, "FX core helpers tests", verbose=verbose)


def services_static_uploads(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test static uploads service: save, list, get, delete, security validation.
    """
    print_section("Services: Static Uploads")
    print_info("Testing: backend/app/services/static_uploads.py")
    print_info("Tests: File save/list/get/delete, security validation, user filtering")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_static_uploads.py", test_names)
    return run_command(cmd, "Static uploads service tests", verbose=verbose)


def services_brim_parse_error(verbose: bool = False, test_names: list = None) -> bool:
    """
    Test BRIMParseError exception class: message, details, inheritance.
    """
    print_section("Services: BRIM Parse Error")
    print_info("Testing: backend/app/services/brim_provider.py (BRIMParseError)")
    print_info("Tests: Constructor, message/details attributes, exception hierarchy")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_brim_parse_error.py", test_names)
    return run_command(cmd, "BRIM parse error tests", verbose=verbose)



def services_settings(verbose: bool = False, test_names: list = None) -> bool:
    """Test settings service: get_session_ttl_sync."""
    print_section("Services: Settings Service")
    print_info("Testing: backend/app/services/settings_service.py")

    cmd = _build_pytest_cmd("backend/test_scripts/test_services/test_settings_service.py", test_names)
    return run_command(cmd, "Settings service tests", verbose=verbose)


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



def utils_day_count(verbose: bool = False, test_names: list = None) -> bool:
    """Test day count conventions."""
    print_section("Utils: Day Count Conventions")
    print_info("Testing: backend/app/services/asset_source_providers/scheduled_investment.py (day count functions)")
    print_info("Tests: ACT/365, ACT/360, ACT/ACT, 30/360 conventions")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_day_count_conventions.py", test_names)
    return run_command(cmd, "Day count convention tests", verbose=verbose)



def utils_geo_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test geographic area normalization utilities (country codes, weight validation)."""
    print_section("Utils: Geographic Area Normalization")
    print_info("Testing: backend/app/utils/geo_utils.py")
    print_info("Tests: ISO-3166-A3 normalization, weight parsing, validation pipeline")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_geo_utils.py", test_names)
    return run_command(cmd, "Geographic area normalization tests", verbose=verbose)


def utils_version(verbose: bool = False, test_names: list = None) -> bool:
    """Test version utilities: get_git_version, get_version_info."""
    print_section("Utils: Version")
    print_info("Testing: backend/app/utils/version.py")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_version.py", test_names)
    return run_command(cmd, "Version utility tests", verbose=verbose)


def utils_sector_normalization(verbose: bool = False, test_names: list = None) -> bool:
    """Test FinancialSector enum and sector normalization."""
    print_section("Utils: Sector Normalization")
    print_info("Testing: backend/app/utils/sector_fin_utils.py")
    print_info("Tests: FinancialSector enum, aliases, normalization, validation")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_sector_normalization.py", test_names)
    return run_command(cmd, "Sector normalization tests", verbose=verbose)


def utils_currency_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test currency listing, flag mapping, and validation consistency."""
    print_section("Utils: Currency Utils")
    print_info("Testing: backend/app/utils/currency_utils.py")
    print_info("Tests: list_currencies (pycountry), flag_emoji mapping, crypto, validation consistency")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_currency_utils.py", test_names)
    return run_command(cmd, "Currency utils tests", verbose=verbose)


def utils_cache_utils(verbose: bool = False, test_names: list = None) -> bool:
    """Test NamedCache wrapper, TTL expiration, and global cache registry."""
    print_section("Utils: Cache Utils")
    print_info("Testing: backend/app/utils/cache_utils.py")
    print_info("Tests: NamedCache set/get/delete/clear, TTL, registry, stats")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_cache_utils.py", test_names)
    return run_command(cmd, "Cache utils tests", verbose=verbose)


def utils_provider_core_cache(verbose: bool = False, test_names: list = None) -> bool:
    """Test provider core cache & thread isolation infrastructure."""
    print_section("Utils: Provider Core Cache & Thread Isolation")
    print_info("Testing: backend/app/services/asset_source.py (core cache + _run_provider_in_thread)")
    print_info("Tests: Thread isolation, timeout, caches (history/current/metadata/search), probe bypass")
    cmd = _build_pytest_cmd("backend/test_scripts/test_utilities/test_provider_core_cache.py", test_names)
    return run_command(cmd, "Provider core cache tests", verbose=verbose)


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

def schemas_computed_fields(verbose: bool = False, test_names: list = None) -> bool:
    """Test computed properties across all schemas (BRSummary, FAPricePoint, etc.)."""
    print_section("Schemas: Computed Fields")
    print_info("Testing: computed properties at 0% across brokers, common, fx, prices, transactions schemas")

    cmd = _build_pytest_cmd("backend/test_scripts/test_schemas/test_schema_computed_fields.py", test_names)
    return run_command(cmd, "Schema computed fields tests", verbose=verbose)


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

    cmd = [*pipenv_prefix(), "python", "-m", "pytest", "backend/test_scripts/test_schemas/test_transaction_schemas.py", "-v"]
    if test_names:
        cmd.extend(["-k", " or ".join(test_names)])

    return run_command(cmd, "Transaction schemas tests", verbose=verbose)


def schemas_brokers(verbose: bool = False, test_names: list = None) -> bool:
    """Test broker Pydantic schemas (BRCreateItem, BRReadItem, etc.)."""
    print_section("Schemas: Brokers (BRCreateItem, BRReadItem, etc.)")
    print_info("Testing: backend/app/schemas/brokers.py")

    cmd = [*pipenv_prefix(), "python", "-m", "pytest", "backend/test_scripts/test_schemas/test_broker_schemas.py", "-v"]
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


def api_fx_compress_errors(verbose: bool = False, test_names: list = None) -> bool:
    """Run tests for _compress_convert_errors utility in FX API."""
    print_section("FX Compress Errors Tests")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_fx_compress_errors.py", test_names)
    return run_command(cmd, "FX compress errors tests", verbose=verbose)


def api_preview_cache(verbose: bool = False, test_names: list = None) -> bool:
    """Run tests for PreviewCache in uploads API."""
    print_section("Preview Cache Tests")
    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_preview_cache.py", test_names)
    return run_command(cmd, "Preview cache tests", verbose=verbose)


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
    print_info("Tests: POST /assets/prices/query (bulk read from DB)")
    print_info("Tests: POST /assets/prices/sync (from providers)")
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


def api_assets_events(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run Assets Events API endpoint tests.
    """
    print_section("Assets Events API Endpoint Tests")
    print_info("Testing REST API endpoints for asset event management")
    print_info("Tests: POST /assets/events (bulk upsert manual)")
    print_info("Tests: DELETE /assets/events/{id} (delete by PK)")
    print_info("Tests: POST /assets/events/query (bulk query)")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_assets_events.py", test_names)
    return run_command(cmd, "Assets Events API tests", verbose=verbose)


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


def api_system(verbose: bool = False, test_names: list = None) -> bool:
    """Test system API: parse_pipfile, get_backend_deps, get_frontend_deps, get_display_name."""
    print_section("System API Tests")
    print_info("Testing: system.py utility functions (parse_pipfile, deps)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_system_api.py", test_names)
    return run_command(cmd, "System API tests", verbose=verbose)


def api_backup(verbose: bool = False, test_names: list = None) -> bool:
    """Test backup API: formats, status, export (501), restore (501)."""
    print_section("Backup API Tests")
    print_info("Testing: backup.py placeholder endpoints")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_backup_api.py", test_names)
    return run_command(cmd, "Backup API tests", verbose=verbose)


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


def api_transfer_promotion(verbose: bool = False, test_names: list = None) -> bool:
    """
    Run Transfer Promotion API tests (Block H.4).
    """
    print_section("Transfer Promotion API Tests")
    print_info("Testing POST /transactions/transfers/promote (Block H.4)")
    print_info("Tests: DEPOSIT/WITHDRAWAL → TRANSFER / FX_CONVERSION atomic promotion")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_transfer_promotion.py", test_names)
    return run_command(cmd, "Transfer Promotion API tests", verbose=verbose)


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


def api_users_search(verbose: bool = False, test_names: list[str] | None = None) -> bool:
    """
    Run user search API tests.

    Tests: user search endpoint and share_percentage validation
    """
    print_section("User Search & Share Validation API Tests")
    print_info("Testing REST API endpoints for user search")
    print_info("Tests: GET /users/search, share_percentage sum validation")
    print_info("Note: Server will be automatically started and stopped by test")

    cmd = _build_pytest_cmd("backend/test_scripts/test_api/test_users_search.py", test_names)
    return run_command(cmd, "User Search API tests", verbose=verbose)


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

    result = auto_build_frontend(debug=False)

    # auto_build_frontend returns None if no build needed, 0 if success, non-zero if failed
    if result is None or result == 0:
        return True
    else:
        print_error("Frontend build failed!")
        return False

    print_success("Frontend build completed")
    return True


def _ensure_db_populated() -> bool:
    """Ensure test database has been populated with mock data (brokers, assets, etc.).

    Always runs populate --force to guarantee a clean, known state.
    Required by tests that expect pre-existing data (e.g., broker-sharing).
    """
    print_info("Populating test DB with mock data...")
    return db_populate(verbose=False, force=True)


def _ensure_test_users() -> bool:
    """Ensure E2E test users exist in test database."""
    print_info("Ensuring E2E test users exist...")

    users = [
        ("e2e_test_user", "e2e@test.example.com", "E2eTestPass123!"),
        ("e2e_test_admin", "e2eadmin@test.example.com", "E2eAdminPass123!"),
        ("e2e_test_user2", "e2e2@test.example.com", "E2eTestPass456!"),
        ("e2e_user_alice", "alice@test.example.com", "AlicePass123!"),
        ("e2e_user_bob", "bob@test.example.com", "BobPass123!"),
        ("e2e_user_carol", "carol@test.example.com", "CarolPass123!"),
        ("e2e_user_dave", "dave@test.example.com", "DavePass123!"),
        ("e2e_user_eve", "eve@test.example.com", "EvePass123!"),
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
    test_names: list = None,
    coverage: bool = False,
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
        coverage: If True, enable backend code coverage tracking
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
    if coverage:
        print(f"{Colors.YELLOW}📊 Backend coverage tracking enabled (COVERAGE_BACKEND=1){Colors.NC}")
    print(f"Command:\n└─▶ $ cd frontend && {' '.join(cmd)}")

    try:
        env = os.environ.copy() if coverage else None
        if coverage:
            env["COVERAGE_BACKEND"] = "1"
        result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", text=True, env=env)
        if result.returncode == 0:
            print_success(f"Playwright {spec_file or 'all'} - PASSED")
            return True
        else:
            print_error(f"Playwright {spec_file or 'all'} - FAILED (exit code: {result.returncode})")
            return False
    except Exception as e:
        print_error(f"Playwright error: {e}")
        return False


def front_auth(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run auth E2E tests."""
    print_section("Frontend Auth Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("auth.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_settings(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run settings E2E tests."""
    print_section("Frontend Settings Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("settings.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_files(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run files E2E tests."""
    print_section("Frontend Files Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("files.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_brokers(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run brokers E2E tests."""
    print_section("Frontend Brokers Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("brokers/brokers.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_multi_user(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run multi-user isolation tests."""
    print_section("Frontend Multi-User Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("brokers/multi-user.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_select(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run select components E2E tests."""
    print_section("Frontend Select Components Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("select-components.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_image_crop(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run image crop & media components E2E tests."""
    print_section("Frontend Image Crop & Media Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("image-crop.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_utilities(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run utilities API E2E tests (currencies, countries, sectors)."""
    print_section("Frontend Utilities API Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("utilities.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_broker_sharing(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run broker sharing E2E tests (requires populated DB with brokers)."""
    print_section("Frontend Broker Sharing Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("brokers/broker-sharing.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_unit(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX unit tests (Vitest)."""
    print_section("Frontend FX Unit Tests (Vitest)")
    cmd = ["npm", "run", "test:unit"]
    print(f"\n{Colors.BLUE}Running: Vitest unit tests{Colors.NC}")
    print(f"Command:\n└─▶ $ cd frontend && {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", text=True)
        if result.returncode == 0:
            print_success("Vitest unit tests - PASSED")
            return True
        else:
            print_error(f"Vitest unit tests - FAILED (exit code: {result.returncode})")
            return False
    except Exception as e:
        print_error(f"Vitest error: {e}")
        return False


def front_fx_list(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX list page E2E tests."""
    print_section("Frontend FX List Page Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("fx/fx-list.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_detail(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX detail page E2E tests."""
    print_section("Frontend FX Detail Page Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("fx/fx-detail.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_add_pair(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX add pair modal E2E tests."""
    print_section("Frontend FX Add Pair Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("fx/fx-add-pair.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_editor(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX data editor E2E tests."""
    print_section("Frontend FX Data Editor Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("fx/fx-data-editor.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_csv_import(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX CSV import modal E2E tests."""
    print_section("Frontend FX CSV Import Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("fx/fx-csv-import.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_sync(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX sync modal E2E tests."""
    print_section("Frontend FX Sync Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("fx/fx-sync.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_api(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX API route E2E tests."""
    print_section("Frontend FX API Route Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("fx/fx-api.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx_settings(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run FX chart settings E2E tests."""
    print_section("Frontend FX Chart Settings Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("fx/fx-chart-settings.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_fx(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all FX tests (unit + E2E)."""
    return _run_test_suite(
        suite_name="All FX Tests (Unit + E2E)",
        tests=[
            ("FX Unit (Vitest)", lambda: front_fx_unit(verbose=verbose)),
            ("FX List Page", lambda: front_fx_list(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX Add Pair Modal", lambda: front_fx_add_pair(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX Detail Page", lambda: front_fx_detail(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX Data Editor", lambda: front_fx_editor(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX Sync Modal", lambda: front_fx_sync(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX API Routes", lambda: front_fx_api(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("FX Chart Settings", lambda: front_fx_settings(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
        ],
        verbose=verbose,
        header_msg="All FX Tests (Unit + E2E)",
        summary_title="FX Test Summary",
        success_msg="All FX tests passed! 🎉",
    )


# =============================================================================
# Frontend Asset Tests (Playwright E2E)
# =============================================================================

def front_asset_list(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset list page E2E tests."""
    print_section("Frontend Asset List Page Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("assets/asset-list.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_detail(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset detail page E2E tests."""
    print_section("Frontend Asset Detail Page Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("assets/asset-detail.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_modal(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset modal E2E tests."""
    print_section("Frontend Asset Modal Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("assets/asset-modal.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_data_editor(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run Asset data editor E2E tests."""
    print_section("Frontend Asset Data Editor Tests")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    return _run_playwright("assets/asset-data-editor.spec.ts", ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)


def front_asset_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, test_names: list = None, coverage: bool = False) -> bool:
    """Run all Asset E2E tests."""
    return _run_test_suite(
        suite_name="All Asset Tests (E2E)",
        tests=[
            ("Asset List Page", lambda: front_asset_list(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("Asset Detail Page", lambda: front_asset_detail(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("Asset Modal", lambda: front_asset_modal(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
            ("Asset Data Editor", lambda: front_asset_data_editor(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)),
        ],
        verbose=verbose,
        header_msg="All Asset Tests (E2E)",
        summary_title="Asset Test Summary",
        success_msg="All Asset tests passed! 🎉",
    )


def front_utility_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, coverage: bool = False) -> bool:
    """Run all frontend utility/component E2E tests."""
    print_header("Frontend Utility Tests (Playwright)")
    if not _ensure_frontend_build():
        return False
    if not _ensure_test_users():
        return False
    specs = ["auth.spec.ts", "settings.spec.ts", "files.spec.ts", "select-components.spec.ts", "image-crop.spec.ts"]
    return _run_test_suite(
        suite_name="Frontend Utility Tests",
        tests=[(spec.replace('.spec.ts', '').title(), lambda s=spec: _run_playwright(s, ui=ui, headed=headed, debug=debug, coverage=coverage)) for spec in specs],
        verbose=verbose,
        header_msg=None,
        summary_title="Frontend Utility Test Summary",
        success_msg="All frontend utility tests passed! 🎉",
    )


def front_user_all(verbose: bool = False, ui: bool = False, headed: bool = False, debug: bool = False, coverage: bool = False) -> bool:
    """Run all frontend user/broker E2E tests."""
    print_header("Frontend User Tests (Playwright)")
    if not _ensure_frontend_build():
        return False
    if not _ensure_db_populated():
        return False
    if not _ensure_test_users():
        return False
    specs = ["brokers/brokers.spec.ts", "brokers/multi-user.spec.ts", "brokers/broker-sharing.spec.ts"]
    return _run_test_suite(
        suite_name="Frontend User Tests",
        tests=[(spec.replace('.spec.ts', '').title(), lambda s=spec: _run_playwright(s, ui=ui, headed=headed, debug=debug, coverage=coverage)) for spec in specs],
        verbose=verbose,
        header_msg=None,
        summary_title="Frontend User Test Summary",
        success_msg="All frontend user tests passed! 🎉",
    )


def _list_front_tests(category: str, action: str = None) -> bool:
    """
    List available test names from spec files for a front-* category.
    Parses .spec.ts files looking for test.describe() and test() calls.
    If action is specified, lists only that spec; otherwise lists all specs in the category.

    Returns True always (listing is not a failure).
    """

    # Map category actions to spec files
    spec_map = {}
    if category in TEST_REGISTRY:
        for act, info in TEST_REGISTRY[category].items():
            if act == "_meta" or act == "all":
                continue
            tests_file = info.get("tests", "")
            if tests_file.endswith(".spec.ts"):
                spec_map[act] = tests_file

    # If action specified (and not "all"), filter to just that spec
    if action and action != "all" and action in spec_map:
        spec_map = {action: spec_map[action]}
    elif action and action == "fx-unit":
        # Special: vitest unit tests
        print(f"\n{Colors.CYAN}🧪 Vitest Unit Tests:{Colors.NC}")
        try:
            result = subprocess.run(
                ["npm", "run", "test:unit:list"],
                cwd=PROJECT_ROOT / "frontend",
                capture_output=True, text=True
            )
            if result.stdout:
                for line in result.stdout.strip().splitlines():
                    if line.strip():
                        print(f"  {line.strip()}")
        except Exception as e:
            print_error(f"Could not list Vitest tests: {e}")
        print()
        return True

    if not spec_map:
        print_error(f"No spec files found for category '{category}' action '{action}'")
        return True

    e2e_dir = PROJECT_ROOT / "frontend" / "e2e"

    print(f"\n{Colors.CYAN}🧪 Available Tests ({category}):{Colors.NC}")
    print(f"  Use {Colors.YELLOW}./dev.py test {category} <action> \"<test name>\"{Colors.NC} to run a specific test\n")

    for act, spec_path in spec_map.items():
        spec_file = e2e_dir / spec_path
        if not spec_file.exists():
            print(f"  {Colors.RED}✗ {spec_path} — not found{Colors.NC}")
            continue

        content = spec_file.read_text()
        current_describe = ""
        test_count = 0

        print(f"  {Colors.GREEN}▸ {act}{Colors.NC} ({spec_path})")
        for line in content.splitlines():
            dm = re.search(r"test\.describe\(['\"](.+?)['\"]", line)
            if dm:
                current_describe = dm.group(1)
                print(f"    {Colors.BLUE}▸ {current_describe}{Colors.NC}")
            tm = re.search(r"test\(['\"](.+?)['\"]", line)
            if tm:
                test_name = tm.group(1)
                print(f"      • {test_name}")
                test_count += 1

        if test_count == 0:
            print(f"    {Colors.YELLOW}(no tests found){Colors.NC}")
        print()

    return True


# Mapping of backend test categories to their test directories/files
BACKEND_TEST_PATHS = {
    "external": "backend/test_scripts/test_external/",
    "db": "backend/test_scripts/test_db/",
    "services": "backend/test_scripts/test_services/",
    "utils": "backend/test_scripts/test_utilities/",
    "schemas": "backend/test_scripts/test_schemas/",
    "api": "backend/test_scripts/test_api/",
    "e2e": "backend/test_scripts/test_e2e/",
}


def _list_pytest_tests(category: str, action: str = None) -> bool:
    """
    List available pytest test names for a backend category.
    Uses `pytest --collect-only -q` to enumerate tests.

    Args:
        category: Backend test category (external, db, services, etc.)
        action: Specific action or "all" to list all tests in category.

    Returns True always (listing is not a failure).
    """
    # Determine path: if action maps to a specific file, use that; otherwise use category directory
    test_path = None

    if action and action != "all" and category in TEST_REGISTRY:
        info = TEST_REGISTRY[category].get(action, {})
        # Try to extract path from the "tests" field or known patterns
        tests_field = info.get("tests", "")
        # Check if the function has a known pytest path
        func = info.get("func")
        if func:
            # Inspect function source to find _build_pytest_cmd path
            try:
                source = inspect.getsource(func)
                match = re.search(r'_build_pytest_cmd\(["\']([^"\']+)["\']', source)
                if match:
                    test_path = match.group(1)
                else:
                    # Try direct pytest path
                    match = re.search(r'pytest.*?["\']([^"\']*test_scripts[^"\']+\.py)["\']', source)
                    if match:
                        test_path = match.group(1)
            except (TypeError, OSError):
                pass

    if not test_path:
        # Fall back to category directory
        test_path = BACKEND_TEST_PATHS.get(category)

    if not test_path:
        print_error(f"No test path found for category '{category}' action '{action}'")
        return True

    full_path = PROJECT_ROOT / test_path
    if not full_path.exists():
        print_error(f"Test path not found: {test_path}")
        return True

    print(f"\n{Colors.CYAN}🧪 Available Tests ({category}{' / ' + action if action and action != 'all' else ''}):{Colors.NC}")
    print(f"  Use {Colors.YELLOW}./dev.py test {category} <action> \"<test name>\"{Colors.NC} to run a specific test\n")

    try:
        cmd = [*pipenv_prefix(), "python", "-m", "pytest", str(test_path), "--collect-only", "-q"]
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = result.stdout.strip()
        if not output:
            print(f"  {Colors.YELLOW}(no tests collected){Colors.NC}")
            if result.stderr:
                # Show only the last few lines of stderr (skip warnings)
                err_lines = [l for l in result.stderr.strip().splitlines() if 'ERROR' in l or 'error' in l.lower()]
                for l in err_lines[:5]:
                    print(f"  {Colors.RED}{l}{Colors.NC}")
            print()
            return True

        # Parse pytest --collect-only -q output
        # Format: "backend/test_scripts/test_api/test_fx_api.py::TestFxApi::test_get_providers"
        # or: "backend/test_scripts/.../test_file.py::test_function"
        current_file = ""
        current_class = ""
        test_count = 0

        for line in output.splitlines():
            line = line.strip()
            if not line or line.startswith("=") or line.startswith("-") or "selected" in line or "no tests" in line:
                continue
            if "::" not in line:
                continue

            parts = line.split("::")
            file_part = parts[0] if len(parts) > 0 else ""
            # Extract filename from path
            file_name = Path(file_part).name if file_part else ""

            if len(parts) == 3:
                # file::Class::test
                cls = parts[1]
                test = parts[2]
                if file_name != current_file:
                    current_file = file_name
                    current_class = ""
                    print(f"  {Colors.GREEN}▸ {file_name}{Colors.NC}")
                if cls != current_class:
                    current_class = cls
                    print(f"    {Colors.BLUE}▸ {cls}{Colors.NC}")
                print(f"      • {test}")
            elif len(parts) == 2:
                # file::test (no class)
                test = parts[1]
                if file_name != current_file:
                    current_file = file_name
                    current_class = ""
                    print(f"  {Colors.GREEN}▸ {file_name}{Colors.NC}")
                print(f"    • {test}")
            test_count += 1

        # Print summary line from pytest (e.g., "42 tests collected")
        for line in output.splitlines():
            if "selected" in line or "test" in line.lower() and not "::" in line:
                stripped = line.strip()
                if stripped and not stripped.startswith("="):
                    print(f"\n  {Colors.CYAN}{stripped}{Colors.NC}")

    except subprocess.TimeoutExpired:
        print_error("Timeout collecting tests (30s)")
    except Exception as e:
        print_error(f"Could not list tests: {e}")

    print()
    return True


# ============================================================================
# COVERAGE CLEAN HELPERS
# ============================================================================

_BACKEND_CATEGORIES = ("external", "db", "services", "utils", "schemas", "api", "e2e")
_FRONTEND_CATEGORIES = ("front-utility", "front-user", "front-fx", "front-asset")


def _clean_coverage_dirs(clean_backend: bool, clean_frontend: bool) -> None:
    """Remove coverage data directories selectively, archiving DBs first."""
    cwd = Path(os.getcwd())
    data_dir = cwd / ".coverage_data"

    def _archive_and_remove(db_path: Path, label: str):
        """Archive a coverage DB before removing it."""
        if db_path.exists():
            archive_dir = data_dir / "archive"
            archive_dir.mkdir(parents=True, exist_ok=True)
            from datetime import datetime as _dt
            ts = _dt.now().strftime("%Y%m%d_%H%M")
            archive_name = f"{label}_{ts}_clean"
            shutil.move(str(db_path), str(archive_dir / archive_name))
            print(f"{Colors.GREEN}📦 Archived .coverage_data/{label} → archive/{archive_name}{Colors.NC}")

    if clean_backend:
        be_dir = cwd / "htmlcov-backend"
        if be_dir.exists():
            shutil.rmtree(be_dir)
            print(f"{Colors.GREEN}🗑️  Removed htmlcov-backend/{Colors.NC}")
        _archive_and_remove(data_dir / "backend", "backend")

    if clean_frontend:
        fe_dir = cwd / "htmlcov-frontend"
        if fe_dir.exists():
            shutil.rmtree(fe_dir)
            print(f"{Colors.GREEN}🗑️  Removed htmlcov-frontend/{Colors.NC}")
        _archive_and_remove(data_dir / "frontend", "frontend")

    if clean_backend or clean_frontend:
        # Also erase .coverage database in root
        result = subprocess.run(
            [*pipenv_prefix(), "coverage", "erase"],
            cwd=os.getcwd(),
            capture_output=True,
            text=True
            )
        if result.returncode == 0:
            print(f"{Colors.GREEN}✅ Coverage database reset{Colors.NC}\n")
        else:
            print(f"{Colors.RED}❌ Failed to reset coverage database{Colors.NC}")
            print(f"{Colors.RED}   Error: {result.stderr}{Colors.NC}\n")
        # Clean up legacy files if they exist
        for legacy in (".coverage.backend", ".coverage.frontend"):
            lf = cwd / legacy
            if lf.exists():
                lf.unlink()


# ============================================================================
# GLOBAL ALL TESTS
# ============================================================================

def run_all_tests(verbose: bool = False,
                  providers: list = None, exclude_providers: list = None) -> bool:
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
            func_params = inspect.signature(func).parameters
            # Front-* categories accept coverage kwarg; pass it when --coverage is active
            if category.startswith("front-") and 'coverage' in func_params:
                tests.append((name, lambda f=func, v=verbose, c=_COVERAGE_MODE: f(verbose=v, coverage=c)))
            # External category: forward provider filter flags
            elif "providers" in func_params:
                tests.append((name, lambda f=func, v=verbose, p=providers, ep=exclude_providers:
                              f(verbose=v, providers=p, exclude_providers=ep)))
            else:
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


def run_all_backend_tests(verbose: bool = False,
                          providers: list = None, exclude_providers: list = None) -> bool:
    """Run all backend tests (external, db, services, utils, schemas, api, e2e)."""
    tests = []
    for category in _BACKEND_CATEGORIES:
        if category not in TEST_REGISTRY:
            continue
        all_info = TEST_REGISTRY[category].get("all", {})
        func = all_info.get("func")
        name = all_info.get("name", f"{category.title()} Tests")
        if func:
            func_params = inspect.signature(func).parameters
            # External category: forward provider filter flags
            if "providers" in func_params:
                tests.append((name, lambda f=func, v=verbose, p=providers, ep=exclude_providers:
                              f(verbose=v, providers=p, exclude_providers=ep)))
            else:
                tests.append((name, lambda f=func, v=verbose: f(verbose=v)))

    return _run_test_suite(
        suite_name="Backend Test Suite",
        tests=tests,
        verbose=verbose,
        info_msgs=[
            "Running all backend test categories",
            "This may take a few minutes...\n",
            ],
        success_msg="\n🎉 ALL BACKEND TESTS PASSED! 🎉",
        )


def run_all_frontend_tests(verbose: bool = False) -> bool:
    """Run all frontend tests (front-utility, front-user, front-fx, front-asset)."""
    tests = []
    for category in _FRONTEND_CATEGORIES:
        if category not in TEST_REGISTRY:
            continue
        all_info = TEST_REGISTRY[category].get("all", {})
        func = all_info.get("func")
        name = all_info.get("name", f"{category.title()} Tests")
        if func:
            if 'coverage' in inspect.signature(func).parameters:
                tests.append((name, lambda f=func, v=verbose, c=_COVERAGE_MODE: f(verbose=v, coverage=c)))
            else:
                tests.append((name, lambda f=func, v=verbose: f(verbose=v)))

    return _run_test_suite(
        suite_name="Frontend Test Suite",
        tests=tests,
        verbose=verbose,
        info_msgs=[
            "Running all frontend test categories",
            "This may take a few minutes...\n",
            ],
        success_msg="\n🎉 ALL FRONTEND TESTS PASSED! 🎉",
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
        "model-validators": {
            "func": db_model_validators,
            "test_names": True,
            "name": "Model Validators",
            "desc": "Test Pydantic field validators on DB models",
            "prereq": "None",
            "tests": "Currency, ISIN, ticker validation",
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
        "provider-contracts": {
            "func": services_provider_contracts,
            "test_names": True,
            "name": "Provider Contracts",
            "desc": "Test ABC interface compliance for ALL providers (offline)",
            "prereq": "None",
            "tests": "Metadata, static URLs, test_cases, params_schema",
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
        "global-settings": {
            "func": services_global_settings,
            "test_names": True,
            "name": "Global Settings Service",
            "desc": "Test global settings service",
            "prereq": "Database created",
            "tests": "Type conversion, DB reads, typed getters",
            },
        "fx-core": {
            "func": services_fx_core,
            "test_names": True,
            "name": "FX Core Helpers",
            "desc": "Test FX core helpers (normalize, upsert, delete, count)",
            "prereq": "Database created",
            "tests": "Rate normalization, bulk upsert/delete, change counting",
            },
        "static-uploads": {
            "func": services_static_uploads,
            "test_names": True,
            "name": "Static Uploads Service",
            "desc": "Test static uploads service",
            "prereq": "None",
            "tests": "Save, list, get, delete, security validation",
            },
        "brim-parse-error": {
            "func": services_brim_parse_error,
            "test_names": True,
            "name": "BRIM Parse Error",
            "desc": "Test BRIMParseError exception class",
            "prereq": "None",
            "tests": "Constructor, attributes, exception hierarchy",
            },
        "settings": {
            "func": services_settings,
            "test_names": True,
            "name": "Settings Service",
            "desc": "Test settings service (session TTL)",
            "prereq": "None",
            "tests": "get_session_ttl_sync",
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
        "day-count": {
            "func": utils_day_count,
            "test_names": True,
            "name": "Day Count",
            "desc": "Test day count conventions",
            "prereq": "None",
            "tests": "ACT/365, ACT/360, ACT/ACT, 30/360",
            },
        "geo-normalization": {
            "func": utils_geo_utils,
            "test_names": True,
            "name": "Geo Normalization",
            "desc": "Test geographic area normalization",
            "prereq": "pycountry installed",
            "tests": "ISO-3166-A3 conversion, weight validation, expand_region",
            },
        "version": {
            "func": utils_version,
            "test_names": True,
            "name": "Version Utils",
            "desc": "Test version utilities (git version, version info)",
            "prereq": "git installed",
            "tests": "get_git_version, get_version_info",
            },
        "sector-normalization": {
            "func": utils_sector_normalization,
            "test_names": True,
            "name": "Sector Normalization",
            "desc": "Test FinancialSector enum and normalization",
            "prereq": "None",
            "tests": "Sector enum values, aliases",
            },
        "currency-utils": {
            "func": utils_currency_utils,
            "test_names": True,
            "name": "Currency Utils",
            "desc": "Test currency listing, flag mapping, validation consistency",
            "prereq": "pycountry, babel installed",
            "tests": "list_currencies (pycountry), flag_emoji, crypto, no historic currencies",
            },
        "cache-utils": {
            "func": utils_cache_utils,
            "test_names": True,
            "name": "Cache Utils",
            "desc": "Test NamedCache, TTL expiration, global registry, stats",
            "prereq": "theine installed",
            "tests": "set/get/delete/clear, TTL expiration, registry, stats, list_caches",
            },
        "provider-core-cache": {
            "func": utils_provider_core_cache,
            "test_names": True,
            "name": "Provider Core Cache",
            "desc": "Test core cache + thread isolation for asset providers",
            "prereq": "theine installed",
            "tests": "Thread isolation, timeout, history/current/metadata/search caches, probe bypass",
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
        "computed-fields": {
            "func": schemas_computed_fields,
            "test_names": True,
            "name": "Schema Computed Fields",
            "desc": "Test computed properties across schemas (BRSummary, FAPricePoint, etc.)",
            "prereq": "None",
            "tests": "Computed properties, tag helpers, date formatters",
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
        "fx-compress-errors": {
            "func": api_fx_compress_errors,
            "test_names": True,
            "name": "FX Compress Errors",
            "desc": "Test _compress_convert_errors utility",
            "prereq": "None",
            "tests": "Error compression logic",
            },
        "preview-cache": {
            "func": api_preview_cache,
            "test_names": True,
            "name": "Preview Cache",
            "desc": "Test PreviewCache LRU cache",
            "prereq": "None",
            "tests": "Cache get/put/evict/invalidate",
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
        "assets-events": {
            "func": api_assets_events,
            "test_names": True,
            "name": "Assets Events API",
            "desc": "Test asset event CRUD endpoints",
            "prereq": "Database created",
            "tests": "POST /events, DELETE /events/{id}, POST /events/query",
            },
        "utilities": {
            "func": api_utilities,
            "test_names": True,
            "name": "Utilities API",
            "desc": "Test utility endpoints",
            "prereq": "None",
            "tests": "GET /utilities/sectors, /countries/normalize",
            },
        "system": {
            "func": api_system,
            "test_names": True,
            "name": "System API",
            "desc": "Test system info endpoints (parse_pipfile, deps)",
            "prereq": "None",
            "tests": "parse_pipfile, get_backend_deps, get_frontend_deps",
            },
        "backup": {
            "func": api_backup,
            "test_names": True,
            "name": "Backup API",
            "desc": "Test backup placeholder endpoints",
            "prereq": "Database created",
            "tests": "GET /formats, /status, POST /export (501), /restore (501)",
            },
        "transactions": {
            "func": api_transactions,
            "test_names": True,
            "name": "Transactions API",
            "desc": "Test transaction endpoints",
            "prereq": "Database created",
            "tests": "CRUD, validation, balance checks",
            },
        "transfer-promotion": {
            "func": api_transfer_promotion,
            "test_names": True,
            "name": "Transfer Promotion API",
            "desc": "Promote DEPOSIT/WITHDRAWAL pair to TRANSFER/FX_CONVERSION (H.4)",
            "prereq": "Database created",
            "tests": "Atomic promotion, same-broker rejection, query filters",
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
        "users-search": {
            "func": api_users_search,
            "test_names": True,
            "name": "User Search API",
            "desc": "Test user search and share validation",
            "prereq": "Database created",
            "tests": "Search, exclude broker, share % validation",
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
    "front-utility": {
        "_meta": {
            "help": "Frontend utility & component E2E tests (auth, settings, files, select, image-crop)",
            "description": """
Frontend Utility & Component Tests

Browser-based tests for core UI components and utility pages:
  • Auth (login, register, logout, language)
  • Settings (user preferences, global settings)
  • Files (upload, tabs, filters)
  • Select components (keyboard navigation, search)
  • Image crop & media (ImageEditModal, AssetPicker, avatar)

Options: --ui, --headed, --debug
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
        "select": {
            "func": front_select,
            "test_names": True,
            "name": "Select Components Tests",
            "desc": "SimpleSelect, SearchSelect, keyboard navigation",
            "prereq": "Login working",
            "tests": "select-components.spec.ts",
            },
        "image-crop": {
            "func": front_image_crop,
            "test_names": True,
            "name": "Image Crop & Media Tests",
            "desc": "ImageEditModal, AssetPicker, FileGrid, avatar (42 tests)",
            "prereq": "Login working, uploaded files",
            "tests": "image-crop.spec.ts",
            },
        "utilities": {
            "func": front_utilities,
            "test_names": True,
            "name": "Utilities API E2E",
            "desc": "Test currencies, countries, sectors API via Playwright",
            "prereq": "Login working",
            "tests": "utilities.spec.ts",
            },
        "all": {
            "func": front_utility_all,
            "test_names": False,
            "name": "All Frontend Utility Tests",
            "desc": "Run all utility/component E2E tests",
            },
        },
    "front-user": {
        "_meta": {
            "help": "Frontend user & broker E2E tests (brokers, multi-user, sharing)",
            "description": """
Frontend User & Broker Tests

Browser-based tests for broker management and multi-user scenarios:
  • Brokers (CRUD, import files)
  • Multi-user (data isolation)
  • Broker sharing (roles, ownership chart)

Options: --ui, --headed, --debug
""",
            },
        "brokers": {
            "func": front_brokers,
            "test_names": True,
            "name": "Brokers Tests",
            "desc": "CRUD broker, import files modal",
            "prereq": "Login working",
            "tests": "brokers/brokers.spec.ts",
            },
        "multi-user": {
            "func": front_multi_user,
            "test_names": True,
            "name": "Multi-User Tests",
            "desc": "Data isolation between users",
            "prereq": "Multiple test users",
            "tests": "brokers/multi-user.spec.ts",
            },
        "broker-sharing": {
            "func": front_broker_sharing,
            "test_names": True,
            "name": "Broker Sharing Tests",
            "desc": "BrokerSharingModal, ownership chart, add/remove users",
            "prereq": "Login working, brokers exist",
            "tests": "brokers/broker-sharing.spec.ts",
            },
        "all": {
            "func": front_user_all,
            "test_names": False,
            "name": "All User Tests",
            "desc": "Run all user/broker E2E tests",
            },
        },
    "front-fx": {
        "_meta": {
            "help": "Frontend FX E2E & unit tests (list, detail, add-pair, editor, sync, API, settings)",
            "description": """
Frontend FX Tests

Tests for the FX (foreign exchange) subsystem:
  • Unit tests: TimeSeriesStore, EditBuffer (Vitest)
  • E2E: FX list page, detail page, add pair modal
  • E2E: Data editor, sync modal, API routes, chart settings

Options: --ui, --headed, --debug
""",
            },
        "fx-unit": {
            "func": front_fx_unit,
            "test_names": False,
            "name": "FX Unit Tests",
            "desc": "Vitest unit tests for TimeSeriesStore, EditBuffer",
            "prereq": "None",
            "tests": "vitest (stores/__tests__/)",
            },
        "fx-list": {
            "func": front_fx_list,
            "test_names": True,
            "name": "FX List Page",
            "desc": "FX list page navigation, cards, filters",
            "prereq": "Login working, DB populated",
            "tests": "fx/fx-list.spec.ts",
            },
        "fx-detail": {
            "func": front_fx_detail,
            "test_names": True,
            "name": "FX Detail Page",
            "desc": "FX detail page chart, panels, swap, sync",
            "prereq": "Login working, DB populated",
            "tests": "fx/fx-detail.spec.ts",
            },
        "fx-add-pair": {
            "func": front_fx_add_pair,
            "test_names": True,
            "name": "FX Add Pair",
            "desc": "Add pair modal, currency select, route discovery",
            "prereq": "Login working, DB populated",
            "tests": "fx/fx-add-pair.spec.ts",
            },
        "fx-editor": {
            "func": front_fx_editor,
            "test_names": True,
            "name": "FX Data Editor",
            "desc": "Data editor table, edit, CSV import",
            "prereq": "Login working, DB populated",
            "tests": "fx/fx-data-editor.spec.ts",
            },
        "fx-csv-import": {
            "func": front_fx_csv_import,
            "test_names": True,
            "name": "FX CSV Import",
            "desc": "CSV import modal, swap direction, validation",
            "prereq": "Login working, DB populated",
            "tests": "fx/fx-csv-import.spec.ts",
            },
        "fx-sync": {
            "func": front_fx_sync,
            "test_names": True,
            "name": "FX Sync Modal",
            "desc": "Sync all modal, sync from detail",
            "prereq": "Login working, DB populated",
            "tests": "fx/fx-sync.spec.ts",
            },
        "fx-api": {
            "func": front_fx_api,
            "test_names": True,
            "name": "FX API Routes",
            "desc": "FX API endpoint contract tests",
            "prereq": "Login working, DB populated",
            "tests": "fx/fx-api.spec.ts",
            },
        "fx-settings": {
            "func": front_fx_settings,
            "test_names": True,
            "name": "FX Chart Settings",
            "desc": "Chart settings modal, aesthetics, signals",
            "prereq": "Login working, DB populated",
            "tests": "fx/fx-chart-settings.spec.ts",
            },
        "all": {
            "func": front_fx,
            "test_names": False,
            "name": "All FX Tests",
            "desc": "Run all FX tests (unit + E2E)",
            },
        },
    "front-asset": {
        "_meta": {
            "help": "Frontend Asset E2E tests (list, detail, modal)",
            "description": """
Frontend Asset Tests

Browser-based tests for the Asset Management subsystem:
  • Asset list page (cards/table, filters, navigation)
  • Asset detail page (chart, signals, measures, classification)
  • Asset modal (create, edit, provider, distributions)

Options: --ui, --headed, --debug
""",
            },
        "asset-list": {
            "func": front_asset_list,
            "test_names": True,
            "name": "Asset List Page",
            "desc": "Asset list page navigation, cards/table, filters",
            "prereq": "Login working, DB populated",
            "tests": "assets/asset-list.spec.ts",
            },
        "asset-detail": {
            "func": front_asset_detail,
            "test_names": True,
            "name": "Asset Detail Page",
            "desc": "Asset detail page chart, panels, sync, edit",
            "prereq": "Login working, DB populated",
            "tests": "assets/asset-detail.spec.ts",
            },
        "asset-modal": {
            "func": front_asset_modal,
            "test_names": True,
            "name": "Asset Modal",
            "desc": "Create/edit asset modal, provider, distributions",
            "prereq": "Login working, DB populated",
            "tests": "assets/asset-modal.spec.ts",
            },
        "asset-data-editor": {
            "func": front_asset_data_editor,
            "test_names": True,
            "name": "Asset Data Editor",
            "desc": "Prices/Events tabs, CSV import, save/cancel",
            "prereq": "Login working, DB populated",
            "tests": "assets/asset-data-editor.spec.ts",
            },
        "all": {
            "func": front_asset_all,
            "test_names": False,
            "name": "All Asset Tests",
            "desc": "Run all Asset E2E tests",
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

    # Special case for db populate (has force, clean, with-static, with-reports flags)
    if category == "db" and action == "populate":
        force = kwargs.get("force", False)
        clean = kwargs.get("clean", False)
        with_static = kwargs.get("with_static", False)
        with_reports = kwargs.get("with_reports", False)
        return test_func(verbose=verbose, force=force, clean=clean,
                         with_static=with_static, with_reports=with_reports)

    # Handle --list for any category
    list_tests = kwargs.get("list_tests", False)
    if list_tests:
        if category in ("front-utility", "front-user", "front-fx", "front-asset"):
            return _list_front_tests(category, action)
        elif category in BACKEND_TEST_PATHS:
            return _list_pytest_tests(category, action)
        else:
            print_error(f"--list not supported for category '{category}'")
            return True

    # Special case for front category (has ui, headed, debug flags + test_names)
    if category in ("front-utility", "front-user", "front-fx", "front-asset"):

        ui = kwargs.get("ui", False)
        headed = kwargs.get("headed", False)
        debug = kwargs.get("debug", False)
        coverage = kwargs.get("coverage", False) or _COVERAGE_MODE
        if accepts_test_names and test_names:
            return test_func(verbose=verbose, ui=ui, headed=headed, debug=debug, test_names=test_names, coverage=coverage)
        return test_func(verbose=verbose, ui=ui, headed=headed, debug=debug, coverage=coverage)

    # Special case for external category (has --providers / --exclude-providers)
    if category == "external":
        providers = kwargs.get("providers", None)
        exclude_providers = kwargs.get("exclude_providers", None)
        # Only pass provider filters to functions that accept them (fx-providers, asset-providers)
        func_params = inspect.signature(test_func).parameters
        extra_kw = {}
        if "providers" in func_params:
            extra_kw["providers"] = providers
        if "exclude_providers" in func_params:
            extra_kw["exclude_providers"] = exclude_providers
        if accepts_test_names and test_names:
            return test_func(verbose=verbose, test_names=test_names, **extra_kw)
        return test_func(verbose=verbose, **extra_kw)

    # Build arguments
    if accepts_test_names and test_names:
        return test_func(verbose=verbose, test_names=test_names)
    else:
        return test_func(verbose=verbose)


def _get_external_extra_args() -> list[tuple]:
    """
    Generate --providers / --exclude-providers argparse arguments for the external category.

    Dynamic help text lists all currently registered provider codes,
    so users see available choices directly in --help output.

    Provider codes are discovered via lightweight filesystem regex parsing
    (no module imports, no side-effects).

    Shared between create_parser() and register_subparser() to avoid duplication.
    """
    asset_codes = get_asset_provider_codes()
    fx_codes = get_fx_provider_codes()
    brim_codes = get_brim_provider_codes()
    provider_help = (
        "Only test these provider(s). "
        f"Asset: {', '.join(asset_codes) or '(none)'}. "
        f"FX: {', '.join(fx_codes) or '(none)'}. "
        f"BRIM: {', '.join(brim_codes) or '(none)'}. "
        "If omitted, ALL providers are tested."
    )
    exclude_help = (
        "Exclude these provider(s) from testing. "
        f"Asset: {', '.join(asset_codes) or '(none)'}. "
        f"FX: {', '.join(fx_codes) or '(none)'}. "
        f"BRIM: {', '.join(brim_codes) or '(none)'}."
    )
    return [
        (
            "--providers", {
            "nargs": "+",
            "dest": "providers",
            "metavar": "CODE",
            "help": provider_help,
            "default": None,
            }
            ),
        (
            "--exclude-providers", {
            "nargs": "+",
            "dest": "exclude_providers",
            "metavar": "CODE",
            "help": exclude_help,
            "default": None,
            }
            ),
    ]


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
    lines.append(f"  {'coverage-report':8} - Analyse coverage: find uncovered function bodies")
    lines.append("")
    lines.append("Examples:")
    lines.append("  dev.py test all                 # All tests (optimal order)")
    lines.append("  dev.py test -v all              # All tests with verbose output")
    lines.append("  dev.py test api auth            # Only auth API tests")
    lines.append("  dev.py testpython test_runner.py db create           # Create database")
    lines.append("")
    lines.append("  # Via dev.sh")
    lines.append("  dev.sh test all                         # Complete test suite")
    lines.append("  dev.sh test api all                     # All API tests")
    lines.append("")
    lines.append("Coverage:")
    lines.append("  dev.py test --coverage api all          # Run with coverage tracking")
    lines.append("  dev.py test --coverage --cov-clean-backend api all   # Clean backend coverage + run")
    lines.append("  dev.py test --coverage --cov-clean-frontend front-fx all  # Clean frontend coverage + run")
    lines.append("")
    lines.append("  # Backend coverage during frontend E2E tests:")
    lines.append("  dev.py test --coverage front-fx all     # Playwright + backend coverage")
    lines.append("")
    lines.append("  # After running tests with --coverage:")
    lines.append("  coverage combine                        # Merge .coverage.<pid> files")
    lines.append("  coverage report                         # Terminal summary")
    lines.append("  coverage html && open htmlcov/index.html  # HTML report in browser")
    lines.append("")
    lines.append("  # View differentiated reports:")
    lines.append("  dev.py test coverage show backend       # Backend test coverage")
    lines.append("  dev.py test coverage show frontend      # Frontend E2E → backend coverage")
    lines.append("  dev.py test coverage show combined      # Merge all + open")

    return "\n".join(lines)


def _register_coverage_subparser(subparsers):
    """Register the 'coverage' sub-command for viewing/combining coverage reports."""
    cov_parser = subparsers.add_parser(
        "coverage",
        help="📊 View or combine coverage reports (backend/frontend/combined)",
        description="""
Coverage Report Management

View differentiated coverage reports:
  show backend     Open backend test coverage (htmlcov-backend/)
  show frontend    Open frontend E2E → backend coverage (htmlcov-frontend/)
  show combined    Combine all data + open merged report (htmlcov/)
  combine          Combine .coverage.* files without opening browser
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cov_sub = cov_parser.add_subparsers(dest="cov_action", metavar="action")

    show_parser = cov_sub.add_parser("show", help="Open coverage HTML report in browser")
    show_parser.add_argument(
        "target",
        choices=["backend", "frontend", "combined"],
        help="Which coverage report to show",
    )

    cov_sub.add_parser("combine", help="Combine .coverage.* files into single .coverage")

    return cov_parser


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
        "--cov-clean-backend",
        action="store_true",
        help="Clean backend coverage data (htmlcov-backend/ + .coverage files)",
        default=False
        )

    parser.add_argument(
        "--cov-clean-frontend",
        action="store_true",
        help="Clean frontend coverage data (htmlcov-frontend/ + .coverage files)",
        default=False
        )


    subparsers = parser.add_subparsers(
        dest="category",
        help="Test category to run",
        required=False
        )

    # Auto-generate subparsers from TEST_REGISTRY
    for category in TEST_REGISTRY.keys():
        extra_args = []
        # --list for all categories (list tests without running)
        extra_args.append((
            "--list", {
            "action": "store_true",
            "dest": "list_tests",
            "help": "List available test names without running them",
            "default": False,
            }
            ))
        if category == "db":
            extra_args.append((
                "--force", {
                "action": "store_true",
                "help": "[populate only] Recreate from scratch",
                "default": False,
                }
                ))
            extra_args.append((
                "--clean", {
                "action": "store_true",
                "help": "[populate only] Clean custom-uploads and broker_reports dirs",
                "default": False,
                }
                ))
            extra_args.append((
                "--with-static", {
                "action": "store_true",
                "dest": "with_static",
                "help": "[populate only] Upload static resources (avatars, broker icons)",
                "default": False,
                }
                ))
            extra_args.append((
                "--with-reports", {
                "action": "store_true",
                "dest": "with_reports",
                "help": "[populate only] Upload sample broker report files",
                "default": False,
                }
                ))
        elif category == "external":
            extra_args.extend(_get_external_extra_args())
        elif category in ("front-utility", "front-user", "front-fx", "front-asset"):
            extra_args.extend([
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
                ])
        create_subparser_from_registry(subparsers, category, extra_args)

    # Special "all" category – also accepts provider filter flags
    all_parser = subparsers.add_parser(
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
    for arg_name, arg_kwargs in _get_external_extra_args():
        all_parser.add_argument(arg_name, **arg_kwargs)

    # "all-backend" category – also accepts provider filter flags
    all_be_parser = subparsers.add_parser(
        "all-backend",
        help="Run all backend tests (external, db, schemas, utils, services, api, e2e)",
        description="""
Backend Test Suite

Runs all backend test categories:
  1. External Services
  2. Database Layer
  3. Schema Validation
  4. Utility Modules
  5. Services Layer
  6. API Endpoints
  7. E2E Tests
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )
    for arg_name, arg_kwargs in _get_external_extra_args():
        all_be_parser.add_argument(arg_name, **arg_kwargs)

    # "all-frontend" category
    subparsers.add_parser(
        "all-frontend",
        help="Run all frontend tests (front-utility, front-user, front-fx, front-asset)",
        description="""
Frontend Test Suite

Runs all frontend test categories:
  1. Front-utility (Vitest unit tests)
  2. Front-user (Playwright E2E)
  3. Front-fx (Playwright E2E)
  4. Front-asset (Playwright E2E)
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
        )

    # Coverage analysis command
    register_cov_parser(subparsers)

    # Coverage management command (show, combine)
    _register_coverage_subparser(subparsers)

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
        help="Run tests (api, db, external, schemas, services, utils, e2e, front-utility, front-user, front-fx, all, all-backend, all-frontend)",
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
        "--cov-clean-backend",
        action="store_true",
        help="Clean backend coverage data (htmlcov-backend/ + .coverage files)",
        default=False
        )

    test_parser.add_argument(
        "--cov-clean-frontend",
        action="store_true",
        help="Clean frontend coverage data (htmlcov-frontend/ + .coverage files)",
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
        extra_args = []
        # --list for all categories
        extra_args.append((
            "--list", {
            "action": "store_true",
            "dest": "list_tests",
            "help": "List available test names without running them",
            "default": False,
            }
            ))
        if category == "db":
            extra_args.append((
                "--force", {
                "action": "store_true",
                "help": "[populate only] Recreate from scratch",
                "default": False,
                }
                ))
            extra_args.append((
                "--clean", {
                "action": "store_true",
                "help": "[populate only] Clean custom-uploads and broker_reports dirs",
                "default": False,
                }
                ))
            extra_args.append((
                "--with-static", {
                "action": "store_true",
                "dest": "with_static",
                "help": "[populate only] Upload static resources (avatars, broker icons)",
                "default": False,
                }
                ))
            extra_args.append((
                "--with-reports", {
                "action": "store_true",
                "dest": "with_reports",
                "help": "[populate only] Upload sample broker report files",
                "default": False,
                }
                ))
        elif category == "external":
            extra_args.extend(_get_external_extra_args())
        elif category in ("front-utility", "front-user", "front-fx", "front-asset"):
            extra_args.extend([
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
                ])
        create_subparser_from_registry(test_subparsers, category, extra_args)

    # "all" category – also accepts provider filter flags
    all_parser = test_subparsers.add_parser(
        "all",
        help="Run ALL tests in optimal order"
        )
    for arg_name, arg_kwargs in _get_external_extra_args():
        all_parser.add_argument(arg_name, **arg_kwargs)

    # "all-backend" category – also accepts provider filter flags
    all_be_parser = test_subparsers.add_parser(
        "all-backend",
        help="Run all backend tests (external, db, schemas, utils, services, api, e2e)"
        )
    for arg_name, arg_kwargs in _get_external_extra_args():
        all_be_parser.add_argument(arg_name, **arg_kwargs)

    # "all-frontend" category
    test_subparsers.add_parser(
        "all-frontend",
        help="Run all frontend tests (front-utility, front-user, front-fx, front-asset)"
        )

    # Coverage analysis command
    register_cov_parser(test_subparsers)

    # Coverage management command (show, combine)
    _register_coverage_subparser(test_subparsers)

    # Set the dispatch function
    test_parser.set_defaults(func=_dispatch_test_command)

    return test_parser


def _dispatch_test_command(args):
    """Dispatch test command from dev.py."""
    global _COVERAGE_MODE, _COVERAGE_SOURCE

    if not args.category:
        print("Error: test category required. Use: ./dev.py test --help")
        return 1

    verbose = getattr(args, 'verbose', False)
    test_names = getattr(args, 'test_names', None)
    coverage = getattr(args, 'coverage', False)
    cov_clean_be = getattr(args, 'cov_clean_backend', False)
    cov_clean_fe = getattr(args, 'cov_clean_frontend', False)

    _COVERAGE_MODE = coverage
    # Auto-detect coverage source from category
    if args.category and args.category.startswith("front-"):
        _COVERAGE_SOURCE = "frontend"
    elif args.category == "all-frontend":
        _COVERAGE_SOURCE = "frontend"
    elif args.category and args.category not in ("all", "all-backend", "coverage-report", "coverage"):
        _COVERAGE_SOURCE = "backend"
    else:
        _COVERAGE_SOURCE = None

    # If coverage mode, handle cov-clean and show message
    if coverage:
        print_header("LibreFolio Test Suite - Coverage Mode")
        print(f"{Colors.YELLOW}📊 Running tests with code coverage tracking{Colors.NC}")
        print(f"{Colors.BLUE}Coverage will accumulate across all test runs{Colors.NC}")
        print(f"{Colors.BLUE}Final report: htmlcov/index.html{Colors.NC}")
        print()

        _clean_coverage_dirs(cov_clean_be, cov_clean_fe)

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

        is_front = _COVERAGE_SOURCE == "frontend"
        is_all = _COVERAGE_SOURCE is None  # category "all"

        print()
        print(f"{Colors.GREEN}📊 Generating final coverage report...{Colors.NC}")
        print()

        _finalize_coverage(is_front, is_all)

    # Exit with appropriate code
    return 0 if success else 1


def _finalize_coverage(is_front: bool, is_all: bool) -> str:
    """
    Finalize coverage data after test runs.

    Coverage DBs are persisted in ``.coverage_data/backend`` and
    ``.coverage_data/frontend``.  The active ``.coverage`` in root is
    a working copy that pytest-cov writes to; it is swapped in/out by
    ``run_command`` before/after each pytest invocation.

    Flow:
      - Backend-only: ``.coverage`` already saved by run_command's finally block.
        Generate ``htmlcov-backend/`` from it.
      - Frontend-only: combine server PID files → ``.coverage``, save to
        ``.coverage_data/frontend``, generate ``htmlcov-frontend/``.
      - All: backend DB already saved.  Combine PID files for frontend.
        Then merge both for ``htmlcov/`` combined report.

    Returns the html_dir used for the final report.
    """
    cwd = Path(os.getcwd())
    main_cov = cwd / ".coverage"
    data_dir = cwd / ".coverage_data"
    data_dir.mkdir(exist_ok=True)
    backend_db = data_dir / "backend"
    frontend_db = data_dir / "frontend"
    html_dir = "htmlcov-frontend" if is_front else "htmlcov-backend"

    def _archive_db(db_path: Path, label: str):
        """Archive previous version of a coverage DB before overwriting."""
        if db_path.exists():
            archive_dir = data_dir / "archive"
            archive_dir.mkdir(exist_ok=True)
            from datetime import datetime as _dt
            ts = _dt.now().strftime("%Y%m%d_%H%M")
            shutil.copy2(str(db_path), str(archive_dir / f"{label}_{ts}"))
            print(f"   {Colors.GREEN}📦 Archived {label} → archive/{label}_{ts}{Colors.NC}")

    if is_front or is_all:
        # --- Save backend DB (run_command already saved it, but for "all"
        #     the backend tests wrote to .coverage which was saved as
        #     .coverage_data/backend by run_command's finally block) ---
        # Remove .coverage so frontend combine creates a clean file
        if main_cov.exists():
            # Ensure backend DB is up-to-date (run_command already did this,
            # but in "all" mode _COVERAGE_SOURCE is None so it may not have)
            if is_all and not backend_db.exists():
                shutil.copy2(str(main_cov), str(backend_db))
            main_cov.unlink()

        # --- Collect only server PID files ---
        SAVED_NAMES = frozenset({".coveragerc"})
        pid_files = [f for f in cwd.glob(".coverage.*") if f.name not in SAVED_NAMES]

        print(f"{Colors.YELLOW}📊 Combining coverage data from server subprocess(es)...{Colors.NC}")
        if pid_files:
            print(f"   Found {len(pid_files)} coverage data file(s): "
                  f"{', '.join(f.name for f in pid_files[:5])}"
                  f"{'...' if len(pid_files) > 5 else ''}")
            r_combine = subprocess.run(
                [*pipenv_prefix(), "coverage", "combine"] + [str(f) for f in pid_files],
                cwd=os.getcwd(), capture_output=True, text=True
            )
            if r_combine.returncode != 0:
                err_lines = [l for l in r_combine.stderr.strip().splitlines()
                             if "Loading .env" not in l and l.strip()]
                if err_lines:
                    print_warning(f"   coverage combine: {' '.join(err_lines)}")

            # Save frontend coverage
            if main_cov.exists():
                _archive_db(frontend_db, "frontend")
                shutil.copy2(str(main_cov), str(frontend_db))
                print(f"   {Colors.GREEN}💾 Saved frontend coverage → .coverage_data/frontend{Colors.NC}")
        else:
            print_warning("   No .coverage.* files found! Server may not have written coverage data.")
            print(f"   {Colors.YELLOW}Hint: check that './dev.py server --coverage' starts the server "
                  f"with 'coverage run'{Colors.NC}")

    if is_all:
        # --- Generate htmlcov-backend/ from backend DB ---
        if backend_db.exists():
            shutil.copy2(str(backend_db), str(main_cov))
            subprocess.run(
                [*pipenv_prefix(), "coverage", "html", "-d", "htmlcov-backend",
                 "--title", "LibreFolio Backend Coverage", "--ignore-errors"],
                cwd=os.getcwd(), capture_output=True, text=True
            )
            print(f"   {Colors.GREEN}📊 Generated htmlcov-backend/{Colors.NC}")

        # --- Generate htmlcov-frontend/ from frontend DB ---
        if frontend_db.exists():
            shutil.copy2(str(frontend_db), str(main_cov))
            r_fe = subprocess.run(
                [*pipenv_prefix(), "coverage", "html", "-d", "htmlcov-frontend",
                 "--title", "LibreFolio Frontend E2E → Backend Coverage",
                 "--ignore-errors"],
                cwd=os.getcwd(), capture_output=True, text=True
            )
            if r_fe.returncode != 0:
                print_warning(f"coverage html (frontend) failed: {r_fe.stderr.strip()}")
            else:
                print(f"   {Colors.GREEN}📊 Generated htmlcov-frontend/{Colors.NC}")

        # --- Merge backend + frontend for combined report ---
        combine_srcs = [str(f) for f in (backend_db, frontend_db) if f.exists()]
        if combine_srcs:
            if main_cov.exists():
                main_cov.unlink()
            print(f"{Colors.YELLOW}📊 Merging backend + frontend for combined report...{Colors.NC}")
            r_merge = subprocess.run(
                [*pipenv_prefix(), "coverage", "combine", "--keep"] + combine_srcs,
                cwd=os.getcwd(), capture_output=True, text=True
            )
            if r_merge.returncode != 0:
                err_lines = [l for l in r_merge.stderr.strip().splitlines()
                             if "Loading .env" not in l and l.strip()]
                if err_lines:
                    print_warning(f"   coverage combine: {' '.join(err_lines)}")

        # Generate combined report in htmlcov/
        r = subprocess.run(
            [*pipenv_prefix(), "coverage", "html", "-d", "htmlcov",
             "--title", "LibreFolio Combined Coverage", "--ignore-errors"],
            cwd=os.getcwd(), capture_output=True, text=True
        )
        if r.returncode != 0:
            print_warning(f"coverage html failed: {r.stderr.strip()}")
        html_dir = "htmlcov"
    elif is_front:
        r = subprocess.run(
            [*pipenv_prefix(), "coverage", "html", "-d", html_dir,
             "--title", "LibreFolio Frontend E2E → Backend Coverage",
             "--ignore-errors"],
            cwd=os.getcwd(), capture_output=True, text=True
        )
        if r.returncode != 0:
            print_warning(f"coverage html failed: {r.stderr.strip()}")
    else:
        # Backend — report already generated by pytest-cov
        # Archive previous DB, then save new one
        if main_cov.exists():
            _archive_db(backend_db, "backend")
            shutil.copy2(str(main_cov), str(backend_db))
            print(f"   {Colors.GREEN}💾 Saved backend coverage → .coverage_data/backend{Colors.NC}")

    # Generate terminal summary
    subprocess.run(
        [*pipenv_prefix(), "coverage", "report", "--skip-covered", "--ignore-errors"],
        cwd=os.getcwd(), capture_output=False, text=True
    )

    # Print hints
    print()
    print(f"{Colors.GREEN}📊 Detailed reports:{Colors.NC}")
    print(f"   HTML: {Colors.BLUE}{html_dir}/index.html{Colors.NC}")
    print(f"   Data: {Colors.BLUE}.coverage{Colors.NC}")
    if backend_db.exists():
        print(f"   Backend DB: {Colors.BLUE}.coverage_data/backend{Colors.NC}")
    if frontend_db.exists():
        print(f"   Frontend DB: {Colors.BLUE}.coverage_data/frontend{Colors.NC}")
    print()
    print(f"{Colors.YELLOW}💡 View HTML report:{Colors.NC}")
    if is_all:
        print(f"└─▶ $ ./dev.py test coverage show combined")
    else:
        print(f"└─▶ $ ./dev.py test coverage show {'frontend' if is_front else 'backend'}")
        print(f"└─▶ $ ./dev.py test coverage show combined   # merge backend + frontend")
    print()

    return html_dir


def _handle_coverage_command(args) -> int:
    """Handle ./dev.py test coverage show [backend|frontend|combined]."""
    action = getattr(args, 'cov_action', None)
    if not action:
        print_error("Usage: ./dev.py test coverage show [backend|frontend|combined]")
        return 1

    if action == "show":
        target = getattr(args, 'target', 'combined')
        return _coverage_show(target)
    elif action == "combine":
        return _coverage_combine()
    else:
        print_error(f"Unknown coverage action: {action}")
        return 1


def _coverage_show(target: str) -> int:
    """Open coverage HTML report for the given target."""
    dir_map = {
        "backend": "htmlcov-backend",
        "frontend": "htmlcov-frontend",
        "combined": "htmlcov",
    }
    title_map = {
        "backend": "LibreFolio Backend Test Coverage",
        "frontend": "LibreFolio Frontend E2E → Backend Coverage",
        "combined": "LibreFolio Combined Coverage (Backend + Frontend)",
    }

    html_dir = PROJECT_ROOT / dir_map[target]
    index_file = html_dir / "index.html"

    if target == "combined":
        # Combine all coverage data first
        print(f"{Colors.YELLOW}📊 Combining all coverage data...{Colors.NC}")
        _coverage_combine_internal(html_dir=str(html_dir), title=title_map[target])
    elif not index_file.exists():
        print_error(f"No {target} coverage report found at {html_dir}/")
        print_info(f"Run tests with --coverage first:")
        if target == "backend":
            print_info(f"  ./dev.py test --coverage api all")
        else:
            print_info(f"  ./dev.py test --coverage front-fx all")
        return 1

    if index_file.exists():
        print_success(f"Opening {target} coverage report: {html_dir}/index.html")
        subprocess.run(["open", str(index_file)])
        return 0
    else:
        print_error(f"Failed to generate {target} coverage report")
        return 1


def _coverage_combine() -> int:
    """Combine all .coverage.* files and generate combined HTML report."""
    return _coverage_combine_internal(
        html_dir="htmlcov",
        title="LibreFolio Combined Coverage (Backend + Frontend)"
    )


def _coverage_combine_internal(html_dir: str = "htmlcov", title: str = "LibreFolio Coverage") -> int:
    """Internal: combine coverage data and generate HTML report.

    Prefers saved snapshots (.coverage.backend, .coverage.frontend) over raw
    PID files to avoid double-counting. Falls back to all .coverage.* files
    if no snapshots exist.
    """
    cwd = Path(os.getcwd())
    backend_cov = cwd / ".coverage.backend"
    frontend_cov = cwd / ".coverage.frontend"

    # Step 1: Determine which files to combine
    # Prefer saved snapshots; fall back to all .coverage.* files
    combine_files = []
    if backend_cov.exists() or frontend_cov.exists():
        if backend_cov.exists():
            combine_files.append(str(backend_cov))
        if frontend_cov.exists():
            combine_files.append(str(frontend_cov))
        print(f"   Using saved snapshots: {', '.join(f.name for f in [backend_cov, frontend_cov] if f.exists())}")
    else:
        # Fallback: use all .coverage.* files
        combine_files = [str(f) for f in cwd.glob(".coverage.*") if f.name != ".coveragerc"]
        if combine_files:
            print(f"   Using {len(combine_files)} parallel data file(s)")

    if not combine_files:
        # Nothing to combine, just use existing .coverage if it exists
        main_cov = cwd / ".coverage"
        if not main_cov.exists():
            print_warning("No coverage data found to combine")
            return 1
    else:
        # Remove existing .coverage before combine to avoid stale data
        main_cov = cwd / ".coverage"
        if main_cov.exists():
            main_cov.unlink()

        result = subprocess.run(
            [*pipenv_prefix(), "coverage", "combine", "--keep"] + combine_files,
            cwd=os.getcwd(), capture_output=True, text=True
        )
        if result.returncode != 0 and "No data to combine" not in result.stderr:
            print_warning(f"coverage combine: {result.stderr.strip()}")

    # Step 2: Generate HTML report
    result = subprocess.run(
        [*pipenv_prefix(), "coverage", "html", "-d", html_dir, "--title", title],
        cwd=os.getcwd(), capture_output=True, text=True
    )
    if result.returncode == 0:
        print_success(f"Coverage report generated: {html_dir}/index.html")
    else:
        print_error(f"Failed to generate report: {result.stderr.strip()}")
        return 1

    # Step 3: Show terminal summary
    subprocess.run(
        [*pipenv_prefix(), "coverage", "report", "--skip-covered"],
        cwd=os.getcwd(), capture_output=False, text=True
    )
    return 0


def dispatch_to_category(category: str, test_names, verbose: bool, args) -> int:
    """Dispatch to the appropriate test handler. Returns 0 on success, 1 on failure."""
    success = False

    if category == "all":
        providers = getattr(args, 'providers', None)
        exclude_providers = getattr(args, 'exclude_providers', None)
        success = run_all_tests(verbose=verbose, providers=providers, exclude_providers=exclude_providers)
    elif category == "all-backend":
        providers = getattr(args, 'providers', None)
        exclude_providers = getattr(args, 'exclude_providers', None)
        success = run_all_backend_tests(verbose=verbose, providers=providers, exclude_providers=exclude_providers)
    elif category == "all-frontend":
        success = run_all_frontend_tests(verbose=verbose)
    elif category == "coverage-report":
        # Build a namespace with the right attributes
        cov_args = argparse.Namespace(
            input=getattr(args, 'input', '/tmp/cov_report.json'),
            priority=getattr(args, 'priority', None),
            category=getattr(args, 'category', None),
            threshold=getattr(args, 'threshold', 0.0),
            json=getattr(args, 'json_output', False),
            summary=getattr(args, 'summary', False),
        )
        return run_coverage_analysis(cov_args)
    elif category == "coverage":
        return _handle_coverage_command(args)
    elif category in TEST_REGISTRY:
        action = getattr(args, 'action', None)
        if action:
            # Build kwargs based on category
            kwargs = {}
            # --list available for all categories
            kwargs['list_tests'] = getattr(args, 'list_tests', False)
            if category == "db":
                kwargs['force'] = getattr(args, 'force', False)
                kwargs['clean'] = getattr(args, 'clean', False)
                kwargs['with_static'] = getattr(args, 'with_static', False)
                kwargs['with_reports'] = getattr(args, 'with_reports', False)
            elif category == "external":
                kwargs['providers'] = getattr(args, 'providers', None)
                kwargs['exclude_providers'] = getattr(args, 'exclude_providers', None)
            elif category in ("front-utility", "front-user", "front-fx", "front-asset"):
                kwargs['ui'] = getattr(args, 'ui', False)
                kwargs['headed'] = getattr(args, 'headed', False)
                kwargs['debug'] = getattr(args, 'debug', False)
                kwargs['coverage'] = getattr(args, 'coverage', False) or _COVERAGE_MODE

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

    return 0


def main():
    """Main entry point."""
    global _COVERAGE_MODE, _COVERAGE_SOURCE

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
    cov_clean_be = getattr(args, 'cov_clean_backend', False)
    cov_clean_fe = getattr(args, 'cov_clean_frontend', False)

    # Set global coverage flag
    _COVERAGE_MODE = coverage
    # Auto-detect coverage source from category
    if args.category and args.category.startswith("front-"):
        _COVERAGE_SOURCE = "frontend"
    elif args.category == "all-frontend":
        _COVERAGE_SOURCE = "frontend"
    elif args.category and args.category not in ("all", "all-backend", "coverage-report", "coverage"):
        _COVERAGE_SOURCE = "backend"
    else:
        _COVERAGE_SOURCE = None

    # If coverage mode, handle cov-clean and show message
    if coverage:
        print_header("LibreFolio Test Suite - Coverage Mode")
        print(f"{Colors.YELLOW}📊 Running tests with code coverage tracking{Colors.NC}")
        print(f"{Colors.BLUE}Coverage will accumulate across all test runs{Colors.NC}")
        print(f"{Colors.BLUE}Final report: htmlcov/index.html{Colors.NC}")
        print()

        _clean_coverage_dirs(cov_clean_be, cov_clean_fe)

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

        is_front = _COVERAGE_SOURCE == "frontend"
        is_all = _COVERAGE_SOURCE is None  # category "all"

        print()
        print(f"{Colors.GREEN}📊 Generating final coverage report...{Colors.NC}")
        print()

        _finalize_coverage(is_front, is_all)

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
