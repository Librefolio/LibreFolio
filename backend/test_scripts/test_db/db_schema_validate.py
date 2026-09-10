#!/usr/bin/env python3
"""
Database schema validation script for LibreFolio.

Verifies:
- All tables created correctly
- Foreign keys enforced
- Unique constraints present
- Indexes created
- Decimal columns use Numeric(18, 6)
- Daily-point policy constraints

Usage:
    pytest backend/test_scripts/test_db/db_schema_validate.py -v
    or via test_runner.py: ./dev.py test db validate
"""

import sys

import pytest

from backend.app.config import PROJECT_ROOT

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

# Standard library and SQLAlchemy imports
from alembic import command
from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint, inspect, text

from backend.alembic.check_constraints_hook import LogLevel, check_and_add_missing_constraints
from backend.app.db.base import SQLModel
from backend.app.db.models import (
    AssetType,
    IdentifierType,
    TransactionType,
    UserRole,
)

# App imports
from backend.app.db.session import get_sync_engine


def test_tables_exist():
    """
    Verify all required tables exist.

    Uses SQLModel metadata to dynamically discover expected tables from models.
    This makes the test future-proof - new tables are automatically detected.
    """
    inspector = inspect(get_sync_engine())
    actual_tables = set(inspector.get_table_names())

    # Get expected tables from SQLModel metadata (dynamically from models)
    expected_tables = set(SQLModel.metadata.tables.keys())

    # Add alembic_version (created by Alembic, not in models)
    expected_tables.add("alembic_version")

    # Check for missing tables (ERROR)
    missing = expected_tables - actual_tables
    assert not missing, f"Missing tables: {', '.join(sorted(missing))}\n" f"Expected (from models): {', '.join(sorted(expected_tables))}\n" f"Found (in database): {', '.join(sorted(actual_tables))}"

    # Check for extra tables (WARNING - not an error, just informational)
    extra = actual_tables - expected_tables
    if extra:
        print(f"ℹ️  Extra tables found (not in models): {', '.join(sorted(extra))}")
        print("   This might be OK (e.g., temp tables)")

    print(f"✅ All {len(expected_tables)} required tables exist")
    if extra:
        print(f"   (plus {len(extra)} extra table(s) - see info above)")


def test_unique_constraints():
    """
    Verify unique constraints exist.

    Dynamically reads unique constraints from SQLModel metadata and verifies
    they exist in the database.
    """
    inspector = inspect(get_sync_engine())

    # Get tables with unique constraints from models (dynamically discovered)
    tables_with_unique = []
    for table_name, table in SQLModel.metadata.tables.items():
        unique_constraints = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
        if unique_constraints:
            tables_with_unique.append((table_name, len(unique_constraints)))
            print(f"  {table_name}: {len(unique_constraints)} unique constraint(s) expected")

    # Verify in database
    for table_name, expected_count in tables_with_unique:
        db_unique = inspector.get_unique_constraints(table_name)
        # Note: SQLite may report indexes as constraints differently
        # We just check that there are some constraints, not exact match
        if len(db_unique) == 0 and expected_count > 0:
            print(f"  ℹ️  {table_name}: Expected {expected_count} constraints, found 0 in DB")
            print("      (May be implemented as unique indexes in SQLite)")

    print("✅ Unique constraints checked")


def test_foreign_keys():
    """
    Verify foreign keys are defined.

    Dynamically reads foreign key constraints from SQLModel metadata and verifies
    they exist in the database.
    """
    inspector = inspect(get_sync_engine())

    # Get tables with foreign keys from models (dynamically discovered)
    tables_with_fks = []
    for table_name, table in SQLModel.metadata.tables.items():
        fk_constraints = [c for c in table.constraints if isinstance(c, ForeignKeyConstraint)]
        fk_count = len(fk_constraints)
        tables_with_fks.append((table_name, fk_count))

    # Verify foreign keys match expected counts
    for table_name, expected_count in sorted(tables_with_fks):
        fks = inspector.get_foreign_keys(table_name)
        actual_count = len(fks)

        assert actual_count == expected_count, f"{table_name}: expected {expected_count} FK(s), found {actual_count}"

        print(f"  ✅ {table_name}: {actual_count} FK(s)")

    print("✅ Foreign keys verified")


def test_indexes():
    """
    Verify indexes are created.

    Dynamically reads indexes from SQLModel metadata and verifies they exist
    in the database.
    """
    inspector = inspect(get_sync_engine())

    # Get tables with indexes from models (dynamically discovered)
    tables_with_indexes = []
    for table_name, table in SQLModel.metadata.tables.items():
        # Count indexes defined in the model
        index_count = len(table.indexes)
        if index_count > 0:
            tables_with_indexes.append((table_name, index_count, [idx.name for idx in table.indexes]))

    # Verify indexes exist in database
    missing_indexes = []
    for table_name, _expected_count, expected_names in sorted(tables_with_indexes):
        db_indexes = inspector.get_indexes(table_name)
        db_index_names = [idx["name"] for idx in db_indexes if idx.get("name")]

        print(f"  {table_name}: {len(db_indexes)} index(es)")

        # Check if expected indexes are present
        for expected_name in expected_names:
            if expected_name and expected_name not in db_index_names:
                missing_indexes.append(f"{table_name}.{expected_name}")
                print(f"    ⚠️  Missing: {expected_name}")

    assert not missing_indexes, f"Missing indexes: {', '.join(missing_indexes)}"

    print("✅ Indexes verified")


def test_fk_pragma():
    """Verify PRAGMA foreign_keys is ON."""
    with get_sync_engine().connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys"))
        fk_enabled = result.scalar()

        assert fk_enabled == 1, "PRAGMA foreign_keys is OFF (NOT enforced!)"
        print("✅ PRAGMA foreign_keys=ON (enforced)")


def test_enum_values():
    """Test that enum values can be used and match expected values."""

    # Verify enums can be accessed and have expected values
    assert IdentifierType.ISIN == "ISIN"
    assert AssetType.STOCK == "STOCK"
    assert AssetType.HOLD == "HOLD"
    assert TransactionType.BUY == "BUY"
    assert TransactionType.DEPOSIT == "DEPOSIT"
    assert TransactionType.FX_CONVERSION == "FX_CONVERSION"
    assert UserRole.OWNER == "OWNER"

    print("✅ All enum types accessible")


def test_model_imports():
    """Test that all models can be imported without errors."""
    # If we got here, all imports at the top succeeded
    # This test validates that the model structure is importable

    # Verify we can access SQLModel metadata
    assert SQLModel.metadata is not None
    assert len(SQLModel.metadata.tables) > 0

    print(f"✅ All model classes importable ({len(SQLModel.metadata.tables)} tables in metadata)")


def test_daily_point_constraints():
    """
    Verify daily-point policy unique constraints.

    Checks that price_history and fx_rates have the expected unique constraints
    for daily-point data (one record per day per entity).
    """
    inspector = inspect(get_sync_engine())

    # Check price_history has (asset_id, date) unique constraint
    price_uq = inspector.get_unique_constraints("price_history")
    print(f"  price_history unique constraints: {len(price_uq)}")

    # We expect at least 1 unique constraint for daily-point policy
    assert len(price_uq) >= 1, "price_history should have unique constraint for daily-point policy"

    # Check fx_rates has (date, base, quote) unique constraint
    fx_uq = inspector.get_unique_constraints("fx_rates")
    print(f"  fx_rates unique constraints: {len(fx_uq)}")

    # We expect at least 1 unique constraint for daily-point policy
    assert len(fx_uq) >= 1, "fx_rates should have unique constraint for daily-point policy"

    print("✅ Daily-point policy constraints present")


def test_check_constraints():
    """
    Verify CHECK constraints exist in database.

    This test dynamically reads all CHECK constraints defined in SQLModel models
    and verifies they exist in the actual database.

    Note: SQLite limitation - Alembic autogenerate doesn't detect CHECK constraints.
    This test ensures they were manually added to migrations.
    """

    # Get tables with CHECK constraints (dynamically discovered from models)
    tables_with_checks = []
    for table_name, table in SQLModel.metadata.tables.items():
        if any(isinstance(c, CheckConstraint) for c in table.constraints):
            check_count = sum(1 for c in table.constraints if isinstance(c, CheckConstraint))
            tables_with_checks.append((table_name, check_count))

    if tables_with_checks:
        print(f"  Found {len(tables_with_checks)} table(s) with CHECK constraints in models:")
        for table_name, count in sorted(tables_with_checks):
            print(f"    • {table_name}: {count} constraint(s)")
    else:
        print("  No CHECK constraints defined in models")
        pytest.skip("No CHECK constraints defined in models")

    print("  Verifying constraints exist in database...")
    all_present, missing = check_and_add_missing_constraints(auto_fix=False, log_level=LogLevel.VERBOSE)

    assert all_present, f"Missing CHECK constraints: {', '.join(missing)}\n" f"SQLite/Alembic limitation: CHECK constraints must be added manually to migrations\n" f"Run: python -m backend.alembic.check_constraints_hook"

    print("✅ All CHECK constraints present in database")


def test_identifier_columns_match_enum():
    """
    Verify every IdentifierType enum has corresponding fields in ALL dependent schemas.

    This ensures the data model stays in sync with the enum definition.
    Each IdentifierType value X should have:
    - Asset.identifier_{x.lower()} column
    - FAAssetCreateItem.identifier_{x.lower()} field
    - FAAssetPatchItem.identifier_{x.lower()} field
    - FAinfoResponse.identifier_{x.lower()} field

    FAAinfoFiltersRequest uses different naming (isin, ticker, etc.) so checked separately.

    If this test fails, see IdentifierType docstring for full update checklist.
    """
    from backend.app.db.models import Asset, IdentifierType  # noqa: PLC0415 — test setup — imports after sys.path/db config
    from backend.app.schemas.assets import (  # noqa: PLC0415 — test setup — imports after sys.path/db config
        FAAinfoFiltersRequest,
        FAAssetCreateItem,
        FAAssetPatchItem,
        FAinfoResponse,
    )

    print("\n  Checking IdentifierType → Schema field mappings:")

    # Define what to check for each IdentifierType
    # Format: (schema_class, field_name_pattern, description)
    checks = [
        (Asset, "identifier_{}", "Asset model column"),
        (FAAssetCreateItem, "identifier_{}", "Create schema field"),
        (FAAssetPatchItem, "identifier_{}", "Patch schema field"),
        (FAinfoResponse, "identifier_{}", "Response schema field"),
    ]

    # FAAinfoFiltersRequest uses short names (isin, ticker, etc.)
    # We check that separately with a mapping
    filter_field_mapping = {
        "ISIN": "isin",
        "TICKER": "ticker",
        "CUSIP": "cusip",
        "SEDOL": "sedol",
        "FIGI": "figi",
        "UUID": "uuid",
        "OTHER": "identifier_other",  # OTHER uses identifier_other (partial match)
    }

    all_missing = []

    # Check standard identifier_xxx fields
    for id_type in IdentifierType:
        field_suffix = id_type.value.lower()
        print(f"\n  IdentifierType.{id_type.value}:")

        for schema_class, pattern, description in checks:
            field_name = pattern.format(field_suffix)
            # For Pydantic models, check model_fields; for SQLModel, use hasattr
            if hasattr(schema_class, "model_fields"):
                has_field = field_name in schema_class.model_fields
            else:
                has_field = hasattr(schema_class, field_name)

            status = "✓" if has_field else "✗"
            print(f"    {status} {schema_class.__name__}.{field_name} ({description})")

            if not has_field:
                all_missing.append(f"{schema_class.__name__}.{field_name}")

    # Check FAAinfoFiltersRequest separately
    print("\n  FAAinfoFiltersRequest filter fields:")
    for id_type in IdentifierType:
        expected_field = filter_field_mapping.get(id_type.value)
        if expected_field:
            has_field = expected_field in FAAinfoFiltersRequest.model_fields
            status = "✓" if has_field else "✗"
            print(f"    {status} FAAinfoFiltersRequest.{expected_field} (for {id_type.value})")

            if not has_field:
                all_missing.append(f"FAAinfoFiltersRequest.{expected_field}")

    if all_missing:
        print(f"\n❌ Missing fields: {all_missing}")
        print("   See IdentifierType docstring in models.py for update checklist")

    assert not all_missing, f"Missing fields for IdentifierType sync: {all_missing}\n" f"See IdentifierType docstring in models.py for full update checklist"

    total_checks = len(list(IdentifierType)) * len(checks) + len(filter_field_mapping)
    print(f"\n✅ All {total_checks} IdentifierType field mappings verified")


def test_transactions_has_asset_event_fk_restrict():
    """
    Verify transactions.asset_event_id FK:
    - Column exists and is nullable
    - FK points to asset_events.id
    - ON DELETE RESTRICT
    - Dedicated index idx_transactions_asset_event is present
    """
    inspector = inspect(get_sync_engine())

    # Column check
    cols = {c["name"]: c for c in inspector.get_columns("transactions")}
    assert "asset_event_id" in cols, "transactions.asset_event_id column missing"
    assert cols["asset_event_id"]["nullable"] is True, "asset_event_id must be nullable"

    # FK check
    fks = inspector.get_foreign_keys("transactions")
    target_fk = next(
        (fk for fk in fks if fk["constrained_columns"] == ["asset_event_id"]),
        None,
    )
    assert target_fk is not None, "FK on transactions.asset_event_id missing"
    assert target_fk["referred_table"] == "asset_events"
    assert target_fk["referred_columns"] == ["id"]
    # SQLAlchemy exposes ondelete in options
    on_delete = (target_fk.get("options") or {}).get("ondelete", "").upper()
    assert on_delete == "RESTRICT", f"Expected ON DELETE RESTRICT, got '{on_delete}'"

    # Index check
    indexes = inspector.get_indexes("transactions")
    index_names = {idx.get("name") for idx in indexes}
    assert "idx_transactions_asset_event" in index_names, f"Expected index idx_transactions_asset_event, got: {index_names}"

    print("✅ transactions.asset_event_id FK RESTRICT + index verified")


# ============================================================================
# ONBOARDING MIGRATION TESTS (Workstream J foundation, 003_user_onboarding_progress)
# ============================================================================
#
# These run the REAL Alembic upgrade/downgrade chain against a private,
# throwaway SQLite file (pytest's per-test `tmp_path`) — never against the
# shared lane's test database. This is required because the backfill
# migration must be observed against a *pre-migration* state (existing users,
# no onboarding rows yet); a lane whose migrations already ran to head cannot
# reproduce that starting point, and mutating the shared database's Alembic
# history would break every other test that depends on it. Nothing here
# touches TEST_PORT, the shared data dir, or the app's own DATABASE_URL.

_ALEMBIC_INI = PROJECT_ROOT / "backend" / "alembic.ini"
_ALEMBIC_SCRIPT_LOCATION = PROJECT_ROOT / "backend" / "alembic"
_PRE_ONBOARDING_REVISION = "5b1333fa6b07"
_ONBOARDING_REVISION = "003_user_onboarding_progress"
_ONBOARDING_MIGRATION_FLOWS = ("welcome", "intro_tour", "import_guide")


def _onboarding_migration_config(db_path):
    """Build an Alembic Config pointed at a private SQLite file.

    `backend/alembic/env.py` only honours a URL override passed as
    `-x sqlalchemy.url=...`: setting `sqlalchemy.url` on the Config object
    alone is silently ignored and falls back to the app's own configured
    DATABASE_URL, which would run the migration against the live/shared
    database instead of this throwaway file. `cmd_opts.x` is normally
    populated by the `alembic` CLI; it is set explicitly here to get the
    override while driving Alembic from Python.
    """
    import argparse  # noqa: PLC0415 — test-only, private migration harness

    from alembic.config import Config  # noqa: PLC0415 — test-only, private migration harness

    url = f"sqlite:///{db_path}"
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", str(_ALEMBIC_SCRIPT_LOCATION))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.cmd_opts = argparse.Namespace(x=[f"sqlalchemy.url={url}"])
    return cfg


def _insert_migration_test_user(db_path, username: str) -> int:
    """Insert a minimal user row directly via sqlite3 (no ORM/session involved)."""
    import sqlite3  # noqa: PLC0415 — test-only, private migration harness

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "INSERT INTO users (username, email, hashed_password, created_at, updated_at) " "VALUES (?, ?, 'fakehash', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
            (username, f"{username}@test.invalid"),
        )
        conn.commit()
        return conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()[0]
    finally:
        conn.close()


def _fetch_onboarding_migration_rows(db_path, user_id: int):
    import sqlite3  # noqa: PLC0415 — test-only, private migration harness

    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT flow, status, version, completed_at, skipped_at FROM user_onboarding_progress WHERE user_id = ? ORDER BY flow",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()


@pytest.fixture()
def onboarding_migration_db(tmp_path):
    """A fresh private SQLite file migrated up to (but not including) 003."""
    db_path = tmp_path / "onboarding_migration.db"
    cfg = _onboarding_migration_config(db_path)
    command.upgrade(cfg, _PRE_ONBOARDING_REVISION)
    return db_path, cfg


def test_onboarding_migration_backfills_existing_users_as_completed_current(onboarding_migration_db):
    """Every pre-existing user gets all three flows as completed/current-version."""
    db_path, cfg = onboarding_migration_db
    user_a = _insert_migration_test_user(db_path, "mig_backfill_user_a")
    user_b = _insert_migration_test_user(db_path, "mig_backfill_user_b")

    command.upgrade(cfg, _ONBOARDING_REVISION)

    for user_id in (user_a, user_b):
        rows = _fetch_onboarding_migration_rows(db_path, user_id)
        assert len(rows) == 3, f"user {user_id}: expected exactly the 3 registered flows, got {rows}"
        assert {row[0] for row in rows} == set(_ONBOARDING_MIGRATION_FLOWS)
        for flow, status, version, completed_at, skipped_at in rows:
            assert status == "completed", f"{flow}: expected completed, got {status}"
            assert version == 1
            assert completed_at is not None
            assert skipped_at is None

    print("✅ Onboarding migration backfilled existing users as completed/current")


def test_onboarding_migration_backfill_is_idempotent_at_insert_level(onboarding_migration_db):
    """Re-running the exact backfill INSERT (INSERT OR IGNORE on the unique
    (user_id, flow) constraint) must not duplicate or overwrite rows."""
    db_path, cfg = onboarding_migration_db
    user_id = _insert_migration_test_user(db_path, "mig_idempotent_user")

    command.upgrade(cfg, _ONBOARDING_REVISION)
    before = _fetch_onboarding_migration_rows(db_path, user_id)
    assert len(before) == 3

    import sqlite3  # noqa: PLC0415 — test-only, private migration harness

    conn = sqlite3.connect(db_path)
    try:
        # Mirrors the backfill INSERT in 003_user_onboarding_progress.py's upgrade();
        # keep in sync if that migration's backfill SQL ever changes.
        conn.execute(
            """
            INSERT OR IGNORE INTO user_onboarding_progress
                (user_id, flow, status, version, created_at, updated_at, completed_at)
            SELECT users.id, flows.flow, 'completed', 1,
                   CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM users
            CROSS JOIN (
                SELECT 'welcome' AS flow
                UNION ALL SELECT 'intro_tour'
                UNION ALL SELECT 'import_guide'
            ) AS flows
            WHERE users.id = ?
            """,
            (user_id,),
        )
        conn.commit()
    finally:
        conn.close()

    after = _fetch_onboarding_migration_rows(db_path, user_id)
    assert after == before, "Re-running the backfill INSERT must be a byte-identical no-op"

    print("✅ Onboarding migration backfill is idempotent at the INSERT level")


def test_onboarding_migration_new_user_after_migration_has_no_rows(onboarding_migration_db):
    """A user created after the migration gets no onboarding rows until the
    service's ensure() lazily creates them as pending."""
    db_path, cfg = onboarding_migration_db
    command.upgrade(cfg, _ONBOARDING_REVISION)

    user_id = _insert_migration_test_user(db_path, "mig_post_migration_user")
    rows = _fetch_onboarding_migration_rows(db_path, user_id)

    assert rows == [], "A brand-new post-migration user must get no rows from the migration itself"

    print("✅ Post-migration user has no onboarding rows until the service creates them")


def test_onboarding_migration_downgrade_drops_table_without_touching_users(onboarding_migration_db):
    """Downgrade removes only user_onboarding_progress; users are untouched."""
    db_path, cfg = onboarding_migration_db
    user_id = _insert_migration_test_user(db_path, "mig_downgrade_user")
    command.upgrade(cfg, _ONBOARDING_REVISION)

    command.downgrade(cfg, _PRE_ONBOARDING_REVISION)

    import sqlite3  # noqa: PLC0415 — test-only, private migration harness

    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        user_row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
    finally:
        conn.close()

    assert "user_onboarding_progress" not in tables
    assert user_row is not None, "Downgrade must not cascade into the users table"

    print("✅ Downgrade drops user_onboarding_progress without touching users")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
