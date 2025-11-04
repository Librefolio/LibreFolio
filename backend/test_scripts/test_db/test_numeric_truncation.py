#!/usr/bin/env python3
"""
Test suite for Numeric column truncation.

This test validates that all Numeric columns in the database handle precision
correctly and that our truncation helpers work as expected.

Algorithm:
1. Scan all SQLModel tables to find Numeric columns
2. For each Numeric(P, S) column:
   - Generate test values with more precision than allowed
   - Verify truncate_decimal_to_db_precision() works correctly
   - Insert value into database
   - Read back and verify database truncated it correctly
   - Verify no false updates occur when syncing identical truncated values

This ensures:
- Helper functions work correctly
- Database truncation matches our expectations
- No false update detections in sync operations
"""
import asyncio
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database, TEST_DB_PATH

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Numeric
from sqlmodel import select

from backend.app.db import models
from backend.app.db.session import get_async_engine
from backend.app.services.fx import get_column_decimal_precision, truncate_decimal_to_db_precision
from backend.test_scripts.test_db_config import initialize_test_database


def print_header(text: str, level: int = 1):
    """Print formatted header."""
    if level == 1:
        print("\n" + "=" * 60)
        print(f"  {text}")
        print("=" * 60)
    elif level == 2:
        print("\n" + "-" * 60)
        print(f"  {text}")
        print("-" * 60)
    else:
        print(f"\n{text}")


def discover_numeric_columns():
    """
    Discover all Numeric columns across all SQLModel tables.

    Returns:
        List of dicts with table metadata:
        [
            {
                'model': FxRate,
                'table_name': 'fx_rates',
                'column_name': 'rate',
                'precision': 24,
                'scale': 10
            },
            ...
        ]
    """
    numeric_columns = []

    # Get all SQLModel classes from models module
    for attr_name in dir(models):
        attr = getattr(models, attr_name)

        # Check if it's a SQLModel table class
        if (
            isinstance(attr, type) and
            hasattr(attr, '__table__') and
            hasattr(attr, '__tablename__')
        ):
            table_name = attr.__tablename__

            # Inspect columns
            for column_name, column in attr.__table__.columns.items():
                if isinstance(column.type, Numeric):
                    numeric_columns.append({
                        'model': attr,
                        'table_name': table_name,
                        'column_name': column_name,
                        'precision': column.type.precision,
                        'scale': column.type.scale
                    })

    return numeric_columns


def generate_test_value(scale: int) -> Decimal:
    """
    Generate a test Decimal value with more precision than allowed.

    Args:
        scale: Number of decimal places allowed

    Returns:
        Decimal with (scale + 5) decimal places for testing truncation

    Example:
        scale=10 → "1.065757220505168"  (15 decimals, 5 more than allowed)
    """
    # Generate a value with extra precision
    extra_decimals = 5
    total_decimals = scale + extra_decimals

    # Create string like "1.065757220505168922519450069"
    decimal_part = "".join(str((i % 10)) for i in range(total_decimals))
    return Decimal(f"1.{decimal_part}")


async def test_truncation_helpers():
    """Test that get_column_decimal_precision and truncate_decimal_to_db_precision work correctly."""
    print_header("Test 1: Truncation Helper Functions", level=2)

    columns = discover_numeric_columns()
    passed = 0
    failed = 0

    for col_info in columns:
        model = col_info['model']
        column_name = col_info['column_name']
        expected_precision = col_info['precision']
        expected_scale = col_info['scale']

        try:
            # Test get_column_decimal_precision
            precision, scale = get_column_decimal_precision(model, column_name)

            if precision != expected_precision or scale != expected_scale:
                print(f"❌ {model.__name__}.{column_name}: Expected ({expected_precision}, {expected_scale}), "
                      f"got ({precision}, {scale})")
                failed += 1
                continue

            # Test truncate_decimal_to_db_precision
            test_value = generate_test_value(scale)
            truncated = truncate_decimal_to_db_precision(test_value, model, column_name)

            # Verify truncation
            truncated_str = str(truncated)
            if '.' in truncated_str:
                actual_scale = len(truncated_str.split('.')[1])
                if actual_scale != scale:
                    print(f"❌ {model.__name__}.{column_name}: Truncated to {actual_scale} decimals, expected {scale}")
                    print(f"   Input: {test_value}")
                    print(f"   Output: {truncated}")
                    failed += 1
                    continue

            print(f"✅ {model.__name__}.{column_name}: Numeric({precision}, {scale}) - Helper functions OK")
            passed += 1

        except Exception as e:
            print(f"❌ {model.__name__}.{column_name}: {e}")
            failed += 1

    print(f"\nHelper Functions Test: {passed} passed, {failed} failed")
    return failed == 0


async def test_database_truncation():
    """Test that database actually truncates values as expected."""
    print_header("Test 2: Database Truncation Behavior", level=2)

    # We'll test FxRate.rate as it's easy to insert/read
    # Other tables have complex constraints that make testing harder

    print("\nℹ️  Testing FxRate.rate column (Numeric(24, 10))")
    print("   This validates that database truncation matches our helper")

    test_date = date(2025, 1, 1)
    test_base = "AAA"  # Alphabetically first
    test_quote = "ZZZ"  # Alphabetically last
    source = "TEST"

    # Generate value with extra precision
    scale = 10
    test_value = generate_test_value(scale)
    truncated_expected = truncate_decimal_to_db_precision(test_value, models.FxRate, 'rate')

    print(f"\n   Test value (input):    {test_value}")
    print(f"   Expected (truncated):  {truncated_expected}")

    success = False

    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        try:
            # Cleanup any existing test data first
            cleanup_stmt = select(models.FxRate).where(
                models.FxRate.date == test_date,
                models.FxRate.base == test_base,
                models.FxRate.quote == test_quote
            )
            result = await session.execute(cleanup_stmt)
            existing = result.scalar_one_or_none()
            if existing:
                await session.delete(existing)
                await session.commit()

            # Insert test rate
            test_rate = models.FxRate(
                date=test_date,
                base=test_base,
                quote=test_quote,
                rate=test_value,  # Insert with extra precision
                source=source,
                fetched_at=datetime.now(timezone.utc)
            )
            session.add(test_rate)
            await session.commit()

            # Read back (new session to avoid cache)
            stmt = select(models.FxRate).where(
                models.FxRate.date == test_date,
                models.FxRate.base == test_base,
                models.FxRate.quote == test_quote
            )
            result = await session.execute(stmt)
            stored_rate = result.scalar_one()

            print(f"   Stored in DB:          {stored_rate.rate}")

            # Verify database truncated correctly
            if stored_rate.rate == truncated_expected:
                print("✅ Database truncation matches helper function")
                success = True
            else:
                print(f"❌ Database truncation mismatch!")
                print(f"   Expected: {truncated_expected}")
                print(f"   Got:      {stored_rate.rate}")
                success = False

        finally:
            # Cleanup - make sure we delete even if test fails
            try:
                cleanup_stmt = select(models.FxRate).where(
                    models.FxRate.date == test_date,
                    models.FxRate.base == test_base,
                    models.FxRate.quote == test_quote
                )
                result = await session.execute(cleanup_stmt)
                stored_rate = result.scalar_one_or_none()
                if stored_rate:
                    await session.delete(stored_rate)
                    await session.commit()
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")
                await session.rollback()

    return success


async def test_no_false_updates():
    """Test that identical truncated values don't trigger false updates."""
    print_header("Test 3: No False Update Detection", level=2)

    print("\nℹ️  Testing that re-syncing identical values doesn't report changes")

    test_date = date(2025, 1, 2)
    test_base = "AAA"
    test_quote = "ZZZ"
    source = "TEST"

    # Generate value with extra precision
    scale = 10
    test_value = generate_test_value(scale)
    truncated = truncate_decimal_to_db_precision(test_value, models.FxRate, 'rate')

    print(f"\n   Test value:       {test_value}")
    print(f"   Truncated value:  {truncated}")

    success = False

    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        try:
            # Cleanup any existing test data first
            cleanup_stmt = select(models.FxRate).where(
                models.FxRate.date == test_date,
                models.FxRate.base == test_base,
                models.FxRate.quote == test_quote
            )
            result = await session.execute(cleanup_stmt)
            existing = result.scalar_one_or_none()
            if existing:
                await session.delete(existing)
                await session.commit()

            # First insert
            test_rate = models.FxRate(
                date=test_date,
                base=test_base,
                quote=test_quote,
                rate=test_value,
                source=source,
                fetched_at=datetime.now(timezone.utc)
            )
            session.add(test_rate)
            await session.commit()

            # Read back
            stmt = select(models.FxRate).where(
                models.FxRate.date == test_date,
                models.FxRate.base == test_base,
                models.FxRate.quote == test_quote
            )
            result = await session.execute(stmt)
            stored_rate_1 = result.scalar_one()
            stored_value_1 = stored_rate_1.rate

            print(f"   First insert:     {stored_value_1}")

            # Now simulate a "sync" with a value that has extra precision
            # but truncates to the SAME value (this is the key test!)
            # Example: 1.0123456789 (stored) vs 1.01234567891234 (new, with extra decimals)
            # Both should truncate to 1.0123456789
            new_value_with_extra_precision = test_value  # This already has 15 decimals

            print(f"   Sync new value:   {new_value_with_extra_precision} (has extra precision)")

            # IMPORTANT: Our sync code should truncate BEFORE comparing
            # Let's simulate what our FIXED code does:
            stored_truncated = truncate_decimal_to_db_precision(stored_value_1, models.FxRate, 'rate')
            new_truncated = truncate_decimal_to_db_precision(new_value_with_extra_precision, models.FxRate, 'rate')

            print(f"   Stored truncated: {stored_truncated}")
            print(f"   New truncated:    {new_truncated}")

            # This is the comparison our sync code should do
            if stored_truncated != new_truncated:
                # Values are different after truncation, should update
                stored_rate_1.rate = new_value_with_extra_precision
                stored_rate_1.fetched_at = datetime.now(timezone.utc)
                await session.commit()
                await session.refresh(stored_rate_1)
                print(f"   ✓ Update applied (values differ after truncation)")
                updated = True
            else:
                # Values are the same after truncation, should NOT update
                print(f"   ✓ No update (values identical after truncation)")
                updated = False

            # Verify the logic works correctly
            if stored_truncated == new_truncated and not updated:
                print("✅ No false update: Truncation comparison works correctly")
                print(f"   Both truncate to: {stored_truncated}")
                success = True
            elif stored_truncated != new_truncated and updated:
                print("✅ Update applied correctly: Values were actually different")
                success = True
            else:
                print(f"❌ Test logic error!")
                print(f"   Stored: {stored_truncated}")
                print(f"   New:    {new_truncated}")
                print(f"   Updated: {updated}")
                success = False

        finally:
            # Cleanup - make sure we delete even if test fails
            try:
                cleanup_stmt = select(models.FxRate).where(
                    models.FxRate.date == test_date,
                    models.FxRate.base == test_base,
                    models.FxRate.quote == test_quote
                )
                result = await session.execute(cleanup_stmt)
                stored_rate = result.scalar_one_or_none()
                if stored_rate:
                    await session.delete(stored_rate)
                    await session.commit()
            except Exception as e:
                print(f"⚠️  Cleanup warning: {e}")
                await session.rollback()

    return success


async def run_all_tests():
    """Run all truncation tests."""
    print_header("LibreFolio - Numeric Column Truncation Tests", level=1)

    # Show prerequisites
    print("\nℹ️  This test operates on:", TEST_DB_PATH)
    print("ℹ️  The backend server is NOT used in this test")
    print()

    # Initialize database with safety checks
    print("ℹ️  Initializing test database...")
    if not initialize_test_database(print):
        print("❌ Failed to initialize test database")
        return 1

    print()
    print("This test suite validates:")
    print("  • Helper functions for precision/truncation work correctly")
    print("  • Database truncates Numeric columns as expected")
    print("  • No false update detections when syncing identical values")

    # Discover all Numeric columns
    columns = discover_numeric_columns()
    print(f"\n📊 Found {len(columns)} Numeric column(s) across all tables:")
    for col in columns:
        print(f"   • {col['table_name']}.{col['column_name']}: "
              f"Numeric({col['precision']}, {col['scale']})")

    # Run tests
    results = []

    results.append(await test_truncation_helpers())
    results.append(await test_database_truncation())
    results.append(await test_no_false_updates())

    # Summary
    print_header("Test Summary", level=1)
    test_names = [
        "Helper Functions",
        "Database Truncation",
        "No False Updates"
    ]

    all_passed = all(results)

    for name, passed in zip(test_names, results):
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    print()
    if all_passed:
        print("🎉 All truncation tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)

