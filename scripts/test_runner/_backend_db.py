"""
Database tests: create, validate, populate, fx_rates, brim, referential integrity, etc.
"""

from scripts.cli_base import pipenv_prefix

from ._common import (
    _RESUME_MODE,
    _run_test_suite, _build_pytest_cmd, run_command,
    setup_test_database, TEST_DB_PATH,
    print_section, print_info, print_success, print_error, print_warning,
    make_category, add_test,
)


def db_create(verbose: bool = False) -> bool:
    """Create fresh database."""
    print_section("Database Creation")

    setup_test_database()

    print_info(f"This test operates on: {TEST_DB_PATH}")
    print_info("The backend server is NOT used in this test")

    if TEST_DB_PATH.exists():
        print_warning(f"Removing existing test database: {TEST_DB_PATH}")
        TEST_DB_PATH.unlink()
        print_success("Test database removed")
    else:
        print_info("No existing test database found")

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


def db_all(verbose: bool = False) -> bool:
    """Run all database tests in sequence."""
    from ._registry import TEST_REGISTRY

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
            resume=_RESUME_MODE,
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
             desc="Asset search, duplicate detection", prereq="Database populated")
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

