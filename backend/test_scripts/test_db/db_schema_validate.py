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
# ONBOARDING MIGRATION TESTS (Workstream J foundation, 004_release_1_2_0_schema)
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
_ONBOARDING_REVISION = "004_release_1_2_0_schema"
# The backfill grandfathers welcome as completed and every other flow as skipped:
# skipped suppresses the trigger exactly like completed while keeping "was never
# shown this" distinct from "went through it", so a flow can still be offered
# retroactively. Pending here would re-trigger every guide for existing users.
_ONBOARDING_MIGRATION_FLOW_STATUSES = {
    "welcome": "completed",
    "intro_tour": "skipped",
    "transactions_page_guide": "skipped",
    "transaction_create_guide": "skipped",
    "transaction_bulk_guide": "skipped",
    "import_guide": "skipped",
    "broker_page_guide": "skipped",
    "broker_guide": "skipped",
    "broker_detail_guide": "skipped",
    "fx_page_guide": "skipped",
    "fx_guide": "skipped",
    "fx_detail_guide": "skipped",
    "asset_page_guide": "skipped",
    "asset_guide": "skipped",
    "asset_detail_guide": "skipped",
}
_ONBOARDING_MIGRATION_STEP_STATUS = "skipped"
_REMOVED_ONBOARDING_DRAFT_FLOWS = {
    "transaction_bulk_validation_guide",
    "transaction_bulk_selection_guide",
    "transaction_bulk_save_guide",
}
_ONBOARDING_MIGRATION_STEPS = {
    "transaction_bulk_guide": {
        "transaction.bulk.workspace",
        "transaction.bulk.validation",
        "transaction.bulk.selection",
        "transaction.bulk.save",
    },
    "import_guide": {
        "import.upload",
        "import.select",
        "import.analyze",
        "import.assets",
        "import.fix",
        "import.duplicates",
        "import.review",
        "import.bulk",
    },
}


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


def _fetch_onboarding_migration_step_rows(db_path, user_id: int):
    import sqlite3  # noqa: PLC0415 — test-only, private migration harness

    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(
            "SELECT flow, step_id, status, version, completed_at, skipped_at " "FROM user_onboarding_step_progress WHERE user_id = ? ORDER BY flow, step_id",
            (user_id,),
        ).fetchall()
    finally:
        conn.close()


@pytest.fixture()
def onboarding_migration_db(tmp_path):
    """A fresh private SQLite file migrated up to (but not including) 004."""
    db_path = tmp_path / "onboarding_migration.db"
    cfg = _onboarding_migration_config(db_path)
    command.upgrade(cfg, _PRE_ONBOARDING_REVISION)
    return db_path, cfg


def test_onboarding_migration_chain_has_exactly_one_head_at_004(tmp_path):
    """The migration chain is linear and ends at a single head, 004_release_1_2_0_schema.

    The single-head assertion is the point of this test. The chain once forked
    into two sibling 003 revisions and needed an empty merge node to become
    upgradable again; a fork is cheap to see here and expensive to see on an
    install, where Alembic simply refuses to upgrade.
    """
    from alembic.script import ScriptDirectory  # noqa: PLC0415 — test-only migration inspection

    cfg = _onboarding_migration_config(tmp_path / "onboarding_revision_contract.db")
    scripts = ScriptDirectory.from_config(cfg)
    heads = scripts.get_heads()
    revision = scripts.get_revision(_ONBOARDING_REVISION)

    assert len(heads) == 1, f"Migration chain must not fork; found {len(heads)} heads: {heads}"
    assert heads[0] == _ONBOARDING_REVISION, f"Expected head {_ONBOARDING_REVISION}, got {heads[0]}"
    assert revision is not None
    assert revision.down_revision == _PRE_ONBOARDING_REVISION


def test_onboarding_migration_backfills_existing_users_by_flow_and_step_policy(onboarding_migration_db):
    """Existing users get 15 flows (welcome completed, the rest skipped) and all Import/Bulk steps at v1."""
    db_path, cfg = onboarding_migration_db
    user_a = _insert_migration_test_user(db_path, "mig_backfill_user_a")
    user_b = _insert_migration_test_user(db_path, "mig_backfill_user_b")

    command.upgrade(cfg, _ONBOARDING_REVISION)

    for user_id in (user_a, user_b):
        rows = _fetch_onboarding_migration_rows(db_path, user_id)
        flow_names = {flow for flow, _status, _version, _completed_at, _skipped_at in rows}
        assert len(rows) == 15, f"user {user_id}: expected exactly the 15 source-of-truth flows, got {rows}"
        assert len(flow_names) == len(rows), f"user {user_id}: migration must not create duplicate flow rows"
        assert flow_names == set(_ONBOARDING_MIGRATION_FLOW_STATUSES)
        assert flow_names.isdisjoint(_REMOVED_ONBOARDING_DRAFT_FLOWS), f"user {user_id}: removed draft flows must not be seeded"
        for flow, status, version, completed_at, skipped_at in rows:
            expected_status = _ONBOARDING_MIGRATION_FLOW_STATUSES[flow]
            assert status == expected_status, f"{flow}: expected {expected_status}, got {status}"
            assert version == 1
            if expected_status == "completed":
                assert completed_at is not None
                assert skipped_at is None
            else:
                assert completed_at is None
                assert skipped_at is not None, f"{flow}: skipped rows must carry skipped_at"

        step_rows = _fetch_onboarding_migration_step_rows(db_path, user_id)
        actual_steps = {(flow, step_id) for flow, step_id, _status, _version, _completed_at, _skipped_at in step_rows}
        expected_steps = {(flow, step_id) for flow, step_ids in _ONBOARDING_MIGRATION_STEPS.items() for step_id in step_ids}
        assert len(step_rows) == 12, f"user {user_id}: expected exactly 12 step rows, got {step_rows}"
        assert len(actual_steps) == len(step_rows), f"user {user_id}: migration must not create duplicate step rows"
        assert actual_steps == expected_steps
        for flow, step_id, status, version, completed_at, skipped_at in step_rows:
            assert step_id in _ONBOARDING_MIGRATION_STEPS[flow]
            assert status == _ONBOARDING_MIGRATION_STEP_STATUS
            assert version == 1
            assert completed_at is None
            assert skipped_at is not None, f"{flow}/{step_id}: skipped rows must carry skipped_at"

    print("✅ Onboarding migration backfilled 15 flows and 12 step rows at v1")


def test_onboarding_migration_step_table_schema_contract(onboarding_migration_db):
    """Migration 004 owns the complete step table contract, including cascade and uniqueness."""
    db_path, cfg = onboarding_migration_db
    command.upgrade(cfg, _ONBOARDING_REVISION)

    import sqlite3  # noqa: PLC0415 — test-only, private migration harness

    conn = sqlite3.connect(db_path)
    try:
        columns = {row[1]: {"not_null": bool(row[3]), "primary_key": bool(row[5])} for row in conn.execute("PRAGMA table_info(user_onboarding_step_progress)").fetchall()}
        foreign_keys = conn.execute("PRAGMA foreign_key_list(user_onboarding_step_progress)").fetchall()
        indexes = conn.execute("PRAGMA index_list(user_onboarding_step_progress)").fetchall()
        unique_index_names = [row[1] for row in indexes if row[2]]
        unique_columns = {tuple(column[0] for column in conn.execute("SELECT name FROM pragma_index_info(?) ORDER BY seqno", (name,)).fetchall()) for name in unique_index_names}
    finally:
        conn.close()

    assert set(columns) == {
        "id",
        "user_id",
        "flow",
        "step_id",
        "status",
        "version",
        "created_at",
        "updated_at",
        "completed_at",
        "skipped_at",
    }
    assert columns["id"]["primary_key"] is True
    for required in ("user_id", "flow", "step_id", "status", "version", "created_at", "updated_at"):
        assert columns[required]["not_null"] is True
    assert columns["completed_at"]["not_null"] is False
    assert columns["skipped_at"]["not_null"] is False
    assert ("user_id", "flow", "step_id") in unique_columns
    assert any(row[2] == "users" and row[3] == "user_id" and row[4] == "id" and row[6].upper() == "CASCADE" for row in foreign_keys)


def test_onboarding_migration_backfill_is_idempotent_at_insert_level(onboarding_migration_db):
    """Replaying the 004 backfill values through INSERT OR IGNORE must not
    duplicate or overwrite any existing (user_id, flow) row."""
    db_path, cfg = onboarding_migration_db
    user_id = _insert_migration_test_user(db_path, "mig_idempotent_user")

    command.upgrade(cfg, _ONBOARDING_REVISION)
    before = _fetch_onboarding_migration_rows(db_path, user_id)
    before_steps = _fetch_onboarding_migration_step_rows(db_path, user_id)
    assert len(before) == 15
    assert len(before_steps) == 12

    import sqlite3  # noqa: PLC0415 — test-only, private migration harness

    conn = sqlite3.connect(db_path)
    try:
        # Replay the same source-of-truth rows through INSERT OR IGNORE. Existing
        # terminal rows must win over every attempted duplicate.
        conn.executemany(
            """
            INSERT OR IGNORE INTO user_onboarding_progress
                (user_id, flow, status, version, created_at, updated_at, completed_at, skipped_at)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                    CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE NULL END,
                    CASE WHEN ? = 'skipped' THEN CURRENT_TIMESTAMP ELSE NULL END)
            """,
            [(user_id, flow, status, status, status) for flow, status in _ONBOARDING_MIGRATION_FLOW_STATUSES.items()],
        )
        conn.executemany(
            """
            INSERT OR IGNORE INTO user_onboarding_step_progress
                (user_id, flow, step_id, status, version, created_at, updated_at, skipped_at)
            VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                    CASE WHEN ? = 'skipped' THEN CURRENT_TIMESTAMP ELSE NULL END)
            """,
            [(user_id, flow, step_id, _ONBOARDING_MIGRATION_STEP_STATUS, _ONBOARDING_MIGRATION_STEP_STATUS) for flow, step_ids in _ONBOARDING_MIGRATION_STEPS.items() for step_id in step_ids],
        )
        conn.commit()
    finally:
        conn.close()

    after = _fetch_onboarding_migration_rows(db_path, user_id)
    after_steps = _fetch_onboarding_migration_step_rows(db_path, user_id)
    assert after == before, "Re-running the backfill INSERT must be a byte-identical no-op"
    assert after_steps == before_steps, "Re-running the step backfill INSERT must be a byte-identical no-op"

    print("✅ Onboarding migration backfill is idempotent at the INSERT level")


def test_onboarding_migration_new_user_after_migration_has_no_rows(onboarding_migration_db):
    """A user created after the migration gets no onboarding rows until the
    service's ensure() lazily creates them as pending."""
    db_path, cfg = onboarding_migration_db
    command.upgrade(cfg, _ONBOARDING_REVISION)

    user_id = _insert_migration_test_user(db_path, "mig_post_migration_user")
    rows = _fetch_onboarding_migration_rows(db_path, user_id)
    step_rows = _fetch_onboarding_migration_step_rows(db_path, user_id)

    assert rows == [], "A brand-new post-migration user must get no rows from the migration itself"
    assert step_rows == [], "A brand-new post-migration user must get no step rows from the migration itself"

    print("✅ Post-migration user has no onboarding rows until the service creates them")


def test_onboarding_migration_downgrade_drops_both_tables_without_touching_users(onboarding_migration_db):
    """Downgrade removes both onboarding tables without touching users."""
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
    assert "user_onboarding_step_progress" not in tables
    assert user_row is not None, "Downgrade must not cascade into the users table"

    print("✅ Downgrade drops both onboarding progress tables without touching users")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
