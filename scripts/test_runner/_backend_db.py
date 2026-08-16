"""
Database tests: create, validate, populate, fx_rates, brim, referential integrity, etc.
"""

import shutil

from backend.test_scripts.test_db_config import TEST_DATA_DIR
from scripts.cli_base import pipenv_prefix

from . import _common
from ._common import (
    TEST_DB_PATH,
    _build_pytest_cmd,
    _run_test_suite,
    add_test,
    make_category,
    print_error,
    print_info,
    print_section,
    print_success,
    print_warning,
    run_command,
    setup_test_database,
)


def db_create(verbose: bool = False) -> bool:
    """Create fresh database."""
    from ._server import database_file_owned_exclusively

    with database_file_owned_exclusively("creating a clean test database"):
        return _db_create_body(verbose)


def _reset_test_file_store() -> None:
    """Drop the file stores that belong to the database being replaced.

    A broker's uploaded reports live on disk, keyed by the broker's *id* —
    ``broker_reports/uploaded/broker_21/…`` — while the broker row itself lives in
    the database. Recreating the database therefore renumbers the owners of files
    that nobody deleted, and the two halves of one dataset drift apart.

    Measured on this machine before the fix: 28 brokers in the database, 308 broker
    directories on disk, 6490 files, 182 copies of the same ``generic_simple.csv``.
    Every directory numbered 1-28 was a *previous* run's broker silently
    impersonating a current one, so the import wizard listed files whose owner had
    been someone else. Tests that pick "the first file called X" then get a
    different file depending on how many runs preceded them — a shared-state
    landmine that only fires in long runs, which is the hardest kind to diagnose.

    The stores are rebuilt by ``db populate`` (``--with-reports`` / ``--with-static``)
    and the default avatars re-copy themselves at startup, so clearing costs nothing.
    """
    for name in ("broker_reports", "custom-uploads"):
        target = TEST_DATA_DIR / name

        # Never let a path bug reach outside the test data directory.
        if not target.resolve().is_relative_to(TEST_DATA_DIR.resolve()):
            print_error(f"Refusing to clear {target}: outside the test data directory")
            continue

        if not target.exists():
            continue

        file_count = sum(1 for p in target.rglob("*") if p.is_file())
        shutil.rmtree(target)
        print_success(f"Test file store cleared: {name} ({file_count} file(s))")


def _db_create_body(verbose: bool = False) -> bool:
    print_section("Database Creation")

    setup_test_database()

    print_info(f"This test operates on: {TEST_DB_PATH}")
    print_info("The backend server is NOT used in this test")

    # The precondition is checked *before* the destructive step, not by the
    # migration that follows it. `dev.sh db:upgrade` refuses to run while a
    # server holds the test port — correct, but by then the file would already be
    # gone, and the run would continue against a database with no tables.
    # Measured on `all-backend`: 13 failures and 116 `no such table: users`
    # errors, none of which named the cause. The caller now steps the shared
    # backend aside, so this guard should no longer fire — it stays because the
    # order it enforces (check, then destroy) is the point.
    from scripts.cli_base import check_server_running, get_test_server_port

    if not check_server_running("creating a clean test database", port=get_test_server_port()):
        print_error("Test database creation aborted — the database was left untouched")
        return False

    if TEST_DB_PATH.exists():
        print_warning(f"Removing existing test database: {TEST_DB_PATH}")
        TEST_DB_PATH.unlink()
        print_success("Test database removed")
    else:
        print_info("No existing test database found")

    # The files on disk are keyed by database ids, so they are part of the database
    # being replaced — not a separate cache that may outlive it.
    _reset_test_file_store()

    print("\nCreating fresh test database from migrations...")
    success = run_command(
        ["./dev.sh", "db:upgrade", str(TEST_DB_PATH)],
        "Create database via Alembic migrations",
        verbose=verbose
        )

    if success:
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
    """Validate database schema."""
    print_section("Database Schema Validation")
    print_info(f"This test operates on: {TEST_DB_PATH}")
    print_info("The backend server is NOT used in this test")
    print_info("Testing: Tables, Foreign Keys, Constraints, Indexes, Enums")

    cmd = _build_pytest_cmd("backend/test_scripts/test_db/db_schema_validate.py", test_names)
    cmd.insert(cmd.index("-v"), "-s")
    return run_command(cmd, "Schema validation", verbose=verbose)


def db_populate(verbose: bool = False, force: bool = False,
                clean: bool = False, with_static: bool = False,
                with_reports: bool = False) -> bool:
    """Populate database with mock data for testing."""
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

    success = run_command(cmd, "Mock data population", verbose=verbose)

    if not success and not verbose:
        print_warning("\n💡 Hint: Database might already contain data")
        print_info("   Run with -v to see detailed error:")
        print_info(f"     dev.py test -v db populate")
        print_info("   Or use --force to delete and recreate:")
        print_info(f"     dev.py test db populate --force")

    return success


def db_fx_rates(verbose: bool = False, test_names: list = None) -> bool:
    """Test FX rates persistence in database."""
    print_section("DB Test: FX Rates Persistence")
    print_info(f"This test operates on: {TEST_DB_PATH} (test database)")
    print_info("Testing: Fetch rates, Persist to DB, Overwrite, Idempotency, Constraints")

    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_fx_rates_persistence.py", test_names)
    return run_command(cmd, "FX rates persistence tests", verbose=verbose)


def db_brim(verbose: bool = False, test_names: list = None) -> bool:
    """Test BRIM database operations."""
    print_section("DB Test: BRIM Asset Search & Duplicate Detection")
    print_info(f"This test operates on: {TEST_DB_PATH} (test database)")
    print_info("Testing: Asset candidate search, duplicate detection")
    print_info("Tests: ISIN/ticker search, confidence levels, auto-selection")

    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_brim_db.py", test_names)
    return run_command(cmd, "BRIM database tests", verbose=verbose)


def db_brim_bulk(verbose: bool = False, test_names: list = None) -> bool:
    """Test that the bulk candidate search agrees with the per-asset one."""
    print_section("DB Test: BRIM Bulk Candidate Search")
    print_info(f"This test operates on: {TEST_DB_PATH} (test database)")
    print_info("Testing: bulk vs per-asset equivalence, dual-ISIN bonds, '%' in names")

    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_brim_bulk_candidates.py", test_names)
    return run_command(cmd, "BRIM bulk candidate tests", verbose=verbose)


def db_numeric_truncation(verbose: bool = False, test_names: list = None) -> bool:
    """Test Numeric column truncation behavior."""
    print_section("DB Test: Numeric Column Truncation")
    print_info("Testing all Numeric columns in database")
    print_info("Tests: Helper functions, DB truncation, No false updates")

    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_numeric_truncation.py", test_names)
    return run_command(cmd, "Numeric truncation tests", verbose=verbose)


def db_test_referential_integrity(verbose: bool = False, test_names: list = None) -> bool:
    """Test ALL database referential integrity constraints."""
    print_section("DB Test: Referential Integrity (CASCADE, RESTRICT, UNIQUE, CHECK)")
    print_info("Comprehensive test suite for ALL foreign key behaviors and constraints")
    print_info("Tests: CASCADE (7), Transaction↔CashMovement (3), UNIQUE (4), CHECK (4)")

    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_db_referential_integrity.py", test_names)
    cmd.insert(cmd.index("-v"), "-s")
    return run_command(cmd, "Database referential integrity tests", verbose=verbose)


def db_model_validators(verbose: bool = False, test_names: list = None) -> bool:
    """Test Pydantic/SQLModel field validators on DB models."""
    print_section("DB Test: Model Validators")
    print_info("Testing: Currency validation, ISIN/ticker normalization, FxRoute properties")
    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_model_validators.py", test_names)
    return run_command(cmd, "Model validator tests", verbose=verbose)


def db_asset_merge(verbose: bool = False, test_names: list = None) -> bool:
    """Test folding one asset into another (duplicate repair)."""
    print_section("DB Test: Asset Merge")
    print_info("Testing: transaction/price/event migration, identifier union, FK traps (RESTRICT, CASCADE)")
    cmd = _build_pytest_cmd("backend/test_scripts/test_db/test_asset_merge.py", test_names)
    return run_command(cmd, "Asset merge tests", verbose=verbose)


def db_all(verbose: bool = False) -> bool:
    """Run all database tests in sequence."""
    from ._registry import TEST_REGISTRY

    db_order = [
        "create", "validate", "numeric-truncation", "populate",
        "referential-integrity", "fx-rates", "brim", "brim-bulk", "asset-merge", "model-validators"
        ]

    tests = []
    for action in db_order:
        if action in TEST_REGISTRY["db"]:
            info = TEST_REGISTRY["db"][action]
            func = info["func"]
            name = info.get("name", action)
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
            resume=_common._RESUME_MODE,
        )


def populate_registry(registry: dict) -> None:
    """Register all database test entries."""
    cat = make_category(
        help_text="Database layer tests (schema, constraints, persistence)",
        description="""
Database Layer Tests

Tests for the SQLite database layer:
  • Create database from migrations
  • Validate schema (tables, FKs, constraints, indexes)
  • Populate with mock data
  • FX rates persistence
  • BRIM asset search & duplicate detection
  • Asset merge (duplicate repair)
  • Referential integrity (CASCADE, RESTRICT, UNIQUE, CHECK)

Note: No backend server required. Tests operate directly on test DB.
""")
    add_test(cat, "create", db_create, test_names=False, name="Create Database",
             desc="Create fresh test database from migrations", prereq="None")
    add_test(cat, "validate", db_validate, name="Validate Schema",
             desc="Check tables, foreign keys, constraints, indexes", prereq="Database created")
    add_test(cat, "populate", db_populate, test_names=False, name="Populate Mock Data",
             desc="Insert test data (use --force to recreate)", prereq="Database created",
             note="Use --force --clean for fresh state")
    add_test(cat, "fx-rates", db_fx_rates, name="FX Rates Persistence",
             desc="Test rate fetching and DB persistence", prereq="Database created")
    add_test(cat, "brim", db_brim, name="BRIM DB Tests",
             desc="Asset candidate search, duplicate detection", prereq="Database populated")
    add_test(cat, "brim-bulk", db_brim_bulk, name="BRIM Bulk Candidates",
             desc="Bulk candidate search matches the per-asset one", prereq="Database created",
             tests="4 equivalence tests")
    add_test(cat, "asset-merge", db_asset_merge, name="Asset Merge",
             desc="Fold a duplicate asset into another (FK migration policies)", prereq="Database created",
             tests="12 merge tests")
    add_test(cat, "numeric-truncation", db_numeric_truncation, name="Numeric Truncation",
             desc="Test Numeric column precision behavior", prereq="Database created")
    add_test(cat, "referential-integrity", db_test_referential_integrity, name="Referential Integrity",
             desc="CASCADE, RESTRICT, UNIQUE, CHECK constraints", prereq="Database populated",
             tests="17 integrity tests")
    add_test(cat, "model-validators", db_model_validators, name="Model Validators",
             desc="Pydantic/SQLModel field validators", prereq="None")
    add_test(cat, "all", db_all, test_names=False, name="All DB Tests",
             desc="Run all database tests in order")
    registry["db"] = cat

