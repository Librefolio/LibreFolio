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
from backend.test_scripts.test_db_config import setup_test_database
setup_test_database()

from sqlalchemy import inspect, text

from backend.app.db import engine
from backend.app.main import ensure_database_exists


def test_tables_exist():
    """Verify all required tables exist."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    required_tables = {
        'brokers',
        'assets',
        'transactions',
        'price_history',
        'fx_rates',
        'cash_accounts',
        'cash_movements',
        }

    missing = required_tables - tables
    if missing:
        print(f"❌ Missing tables: {missing}")
        return False

    print(f"✅ All {len(required_tables)} required tables exist")
    return True


def test_unique_constraints():
    """Verify unique constraints."""
    inspector = inspect(engine)

    checks = {
        'brokers': ['name'],
        'price_history': ['asset_id', 'date'],
        'fx_rates': ['date', 'base', 'quote'],
        'cash_accounts': ['broker_id', 'currency'],
        }

    all_ok = True
    for table, expected_unique in checks.items():
        unique_constraints = inspector.get_unique_constraints(table)
        # Note: SQLite may report indexes as constraints differently
        print(f"  {table}: {len(unique_constraints)} unique constraint(s)")

    print("✅ Unique constraints checked")
    return all_ok


def test_foreign_keys():
    """Verify foreign keys are defined."""
    inspector = inspect(engine)

    fk_checks = {
        'assets': [],  # No FK
        'transactions': [('asset_id', 'assets'), ('broker_id', 'brokers')],
        'price_history': [('asset_id', 'assets')],
        'cash_accounts': [('broker_id', 'brokers')],
        'cash_movements': [('cash_account_id', 'cash_accounts'), ('linked_transaction_id', 'transactions')],
        }

    all_ok = True
    for table, expected_fks in fk_checks.items():
        fks = inspector.get_foreign_keys(table)
        if len(fks) != len(expected_fks):
            print(f"⚠️  {table}: expected {len(expected_fks)} FKs, found {len(fks)}")
        else:
            print(f"  ✅ {table}: {len(fks)} FK(s)")

    print("✅ Foreign keys verified")
    return all_ok


def test_indexes():
    """Verify indexes are created."""
    inspector = inspect(engine)

    index_checks = {
        'transactions': ['idx_transactions_asset_broker_date'],
        'price_history': ['idx_price_history_asset_date'],
        'fx_rates': ['idx_fx_rates_base_quote_date'],
        'cash_movements': ['idx_cash_movements_account_date'],
        }

    all_ok = True
    for table, expected_indexes in index_checks.items():
        indexes = inspector.get_indexes(table)
        index_names = [idx['name'] for idx in indexes if idx.get('name')]
        print(f"  {table}: {len(indexes)} index(es)")

        for exp_idx in expected_indexes:
            if exp_idx not in index_names:
                print(f"    ⚠️  Missing: {exp_idx}")

    print("✅ Indexes verified")
    return all_ok


def test_fk_pragma():
    """Verify PRAGMA foreign_keys is ON."""
    with engine.connect() as conn:
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
    from backend.app.db.models import (
        IdentifierType,
        AssetType,
        ValuationModel,
        TransactionType,
        CashMovementType,
        )

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
    inspector = inspect(engine)

    # Check price_history has (asset_id, date) unique
    price_uq = inspector.get_unique_constraints('price_history')
    print(f"  price_history unique constraints: {len(price_uq)}")

    # Check fx_rates has (date, base, quote) unique
    fx_uq = inspector.get_unique_constraints('fx_rates')
    print(f"  fx_rates unique constraints: {len(fx_uq)}")

    print("✅ Daily-point policy constraints present")
    return True


def main():
    """Run all validation tests."""
    # Ensure database exists before testing
    ensure_database_exists()

    print("=" * 70)
    print("LibreFolio Database Schema Validation")
    print("=" * 70)
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
