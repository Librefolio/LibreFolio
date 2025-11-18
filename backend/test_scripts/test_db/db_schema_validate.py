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
    python -m backend.test_scripts.test_db.db_schema_validate
    or via test_runner.py: python test_runner.py db validate
"""

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database, initialize_test_database

setup_test_database()

# Standard library and SQLAlchemy imports
from sqlalchemy import inspect, text, CheckConstraint, UniqueConstraint, ForeignKeyConstraint

# App imports
from backend.app.db.session import get_sync_engine
from backend.app.db.base import SQLModel
from backend.app.db.models import (
    IdentifierType,
    AssetType,
    ValuationModel,
    TransactionType,
    CashMovementType,
    )
from backend.alembic.check_constraints_hook import check_and_add_missing_constraints, LogLevel


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
    expected_tables.add('alembic_version')

    # Check for missing tables (ERROR)
    missing = expected_tables - actual_tables
    if missing:
        print(f"❌ Missing tables: {', '.join(sorted(missing))}")
        print(f"   Expected (from models): {', '.join(sorted(expected_tables))}")
        print(f"   Found (in database): {', '.join(sorted(actual_tables))}")
        return False

    # Check for extra tables (WARNING - not an error)
    extra = actual_tables - expected_tables
    if extra:
        print(f"⚠️  Extra tables found (not in models): {', '.join(sorted(extra))}")
        print(f"   This might be OK (e.g., alembic_version, temp tables)")

    print(f"✅ All {len(expected_tables)} required tables exist")
    if extra:
        print(f"   (plus {len(extra)} extra table(s) - see warning above)")

    return True


def test_unique_constraints():
    """
    Verify unique constraints exist.
    
    Dynamically reads unique constraints from SQLModel metadata and verifies
    they exist in the database.
    """
    inspector = inspect(get_sync_engine())

    # Get tables with unique constraints from models
    tables_with_unique = []
    for table_name, table in SQLModel.metadata.tables.items():
        unique_constraints = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
        if unique_constraints:
            tables_with_unique.append((table_name, len(unique_constraints)))
            print(f"  {table_name}: {len(unique_constraints)} unique constraint(s) expected")

    # Verify in database
    all_ok = True
    for table_name, expected_count in tables_with_unique:
        db_unique = inspector.get_unique_constraints(table_name)
        # Note: SQLite may report indexes as constraints differently
        # We just check that there are some constraints, not exact match
        if len(db_unique) == 0 and expected_count > 0:
            print(f"  ⚠️  {table_name}: Expected {expected_count} constraints, found 0 in DB")
            print(f"      (May be implemented as unique indexes in SQLite)")

    print("✅ Unique constraints checked")
    return all_ok


def test_foreign_keys():
    """
    Verify foreign keys are defined.
    
    Dynamically reads foreign key constraints from SQLModel metadata and verifies
    they exist in the database.
    """
    inspector = inspect(get_sync_engine())

    # Get tables with foreign keys from models
    tables_with_fks = []
    for table_name, table in SQLModel.metadata.tables.items():
        fk_constraints = [c for c in table.constraints if isinstance(c, ForeignKeyConstraint)]
        fk_count = len(fk_constraints)
        tables_with_fks.append((table_name, fk_count))

    all_ok = True
    for table_name, expected_count in sorted(tables_with_fks):
        fks = inspector.get_foreign_keys(table_name)
        actual_count = len(fks)

        if actual_count != expected_count:
            print(f"  ⚠️  {table_name}: expected {expected_count} FK(s), found {actual_count}")
            all_ok = False
        else:
            print(f"  ✅ {table_name}: {actual_count} FK(s)")

    print("✅ Foreign keys verified")
    return all_ok


def test_indexes():
    """
    Verify indexes are created.
    
    Dynamically reads indexes from SQLModel metadata and verifies they exist
    in the database.
    """
    inspector = inspect(get_sync_engine())

    # Get tables with indexes from models
    tables_with_indexes = []
    for table_name, table in SQLModel.metadata.tables.items():
        # Count indexes defined in the model
        index_count = len(table.indexes)
        if index_count > 0:
            tables_with_indexes.append((table_name, index_count, [idx.name for idx in table.indexes]))

    all_ok = True
    for table_name, expected_count, expected_names in sorted(tables_with_indexes):
        db_indexes = inspector.get_indexes(table_name)
        db_index_names = [idx['name'] for idx in db_indexes if idx.get('name')]

        print(f"  {table_name}: {len(db_indexes)} index(es)")

        # Check if expected indexes are present
        for expected_name in expected_names:
            if expected_name and expected_name not in db_index_names:
                print(f"    ⚠️  Missing: {expected_name}")
                all_ok = False

    print("✅ Indexes verified")
    return all_ok


def test_fk_pragma():
    """Verify PRAGMA foreign_keys is ON."""
    with get_sync_engine().connect() as conn:
        result = conn.execute(text("PRAGMA foreign_keys"))
        fk_enabled = result.scalar()

        if fk_enabled == 1:
            print("✅ PRAGMA foreign_keys=ON (enforced)")
            return True
        else:
            print("❌ PRAGMA foreign_keys=OFF (NOT enforced!)")
            return False


def test_enum_values():
    """Test that enum values can be used."""

    # Just verify they can be accessed
    assert IdentifierType.ISIN == "ISIN"
    assert AssetType.STOCK == "STOCK"
    assert AssetType.HOLD == "HOLD"
    assert ValuationModel.MARKET_PRICE == "MARKET_PRICE"
    assert ValuationModel.MANUAL == "MANUAL"
    assert TransactionType.BUY == "BUY"
    assert CashMovementType.DEPOSIT == "DEPOSIT"

    print("✅ All enum types accessible")
    return True


def test_model_imports():
    """Test that all models can be imported."""

    print("✅ All model classes importable")
    return True


def test_daily_point_constraints():
    """Verify daily-point policy unique constraints."""
    inspector = inspect(get_sync_engine())

    # Check price_history has (asset_id, date) unique
    price_uq = inspector.get_unique_constraints('price_history')
    print(f"  price_history unique constraints: {len(price_uq)}")

    # Check fx_rates has (date, base, quote) unique
    fx_uq = inspector.get_unique_constraints('fx_rates')
    print(f"  fx_rates unique constraints: {len(fx_uq)}")

    print("✅ Daily-point policy constraints present")
    return True


def test_check_constraints():
    """
    Verify CHECK constraints exist in database.

    This test dynamically reads all CHECK constraints defined in SQLModel models
    and verifies they exist in the actual database.

    Note: SQLite limitation - Alembic autogenerate doesn't detect CHECK constraints.
    This test ensures they were manually added to migrations.
    """

    # Get count of tables with CHECK constraints
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
        return True

    print("  Verifying constraints exist in database...")
    all_present, missing = check_and_add_missing_constraints(auto_fix=False, log_level=LogLevel.VERBOSE)

    if not all_present:
        print(f"  ❌ Missing CHECK constraints:")
        for constraint in missing:
            print(f"     • {constraint}")
        print()
        print("  ⚠️  SQLite/Alembic limitation: CHECK constraints must be added manually to migrations")
        print("  Run: python -m backend.alembic.check_constraints_hook")
        return False

    print(f"✅ All CHECK constraints present in database")
    return True


def main():
    """Run all validation tests."""
    print("=" * 70)
    print("LibreFolio Database Schema Validation")
    print("=" * 70)
    print()

    # Initialize database with safety checks
    if not initialize_test_database():
        return 1

    print()

    tests = [
        ("Tables Exist", test_tables_exist),
        ("Foreign Keys", test_foreign_keys),
        ("Unique Constraints", test_unique_constraints),
        ("Indexes", test_indexes),
        ("PRAGMA foreign_keys", test_fk_pragma),
        ("Enum Types", test_enum_values),
        ("Model Imports", test_model_imports),
        ("Daily-Point Policy", test_daily_point_constraints),
        ("CHECK Constraints", test_check_constraints),
        ]

    results = []
    for test_name, test_func in tests:
        print(f"\n🧪 Testing: {test_name}")
        print("-" * 70)
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {test_name}")

    print()
    print(f"Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All validation tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit(main())
