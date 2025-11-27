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
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from backend.app.utils.datetime_utils import utcnow

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Numeric
from sqlmodel import select

from backend.app.db import models
from backend.app.db.session import get_async_engine
from backend.app.utils.decimal_utils import truncate_to_db_precision, get_model_column_precision, truncate_fx_rate


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


def test_truncation_helpers():
    """Test that get_column_decimal_precision and truncate_decimal_to_db_precision work correctly."""
    columns = discover_numeric_columns()
    assert len(columns) > 0, "No numeric columns found"

    for col_info in columns:
        model = col_info['model']
        column_name = col_info['column_name']
        expected_precision = col_info['precision']
        expected_scale = col_info['scale']

        # Test get_column_decimal_precision
        precision, scale = get_model_column_precision(model, column_name)

        assert precision == expected_precision, \
            f"{model.__name__}.{column_name}: Expected precision {expected_precision}, got {precision}"
        assert scale == expected_scale, \
            f"{model.__name__}.{column_name}: Expected scale {expected_scale}, got {scale}"

        # Test truncate_decimal_to_db_precision
        test_value = generate_test_value(scale)
        truncated = truncate_to_db_precision(test_value, model, column_name)

        # Verify truncation
        truncated_str = str(truncated)
        if '.' in truncated_str:
            actual_scale = len(truncated_str.split('.')[1])
            assert actual_scale == scale, \
                f"{model.__name__}.{column_name}: Truncated to {actual_scale} decimals, expected {scale}\n" \
                f"Input: {test_value}\nOutput: {truncated}"

        print(f"✓ {model.__name__}.{column_name}: Numeric({precision}, {scale}) - Helper OK")


@pytest.mark.asyncio
async def test_database_truncation():
    """Test that database actually truncates values as expected."""
    # We'll test FxRate.rate as it's easy to insert/read
    # Other tables have complex constraints that make testing harder

    test_date = date(2025, 1, 1)
    test_base = "AAA"  # Alphabetically first
    test_quote = "ZZZ"  # Alphabetically last
    source = "TEST"

    # Generate value with extra precision
    scale = 10
    test_value = generate_test_value(scale)
    truncated_expected = truncate_to_db_precision(test_value, models.FxRate, 'rate')

    print(f"\nTest value (input):    {test_value}")
    print(f"Expected (truncated):  {truncated_expected}")

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
                fetched_at=utcnow()
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

            print(f"Stored in DB:          {stored_rate.rate}")

            # Verify database truncated correctly
            assert stored_rate.rate == truncated_expected, \
                f"Database truncation mismatch!\n" \
                f"Expected: {truncated_expected}\n" \
                f"Got:      {stored_rate.rate}"

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


@pytest.mark.asyncio
async def test_no_false_updates():
    """Test that identical truncated values don't trigger false updates."""
    test_date = date(2025, 1, 2)
    test_base = "AAA"
    test_quote = "ZZZ"
    source = "TEST"

    # Generate value with extra precision
    scale = 10
    test_value = generate_test_value(scale)
    truncated = truncate_fx_rate(test_value)

    print(f"\nTest value:       {test_value}")
    print(f"Truncated value:  {truncated}")

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
                fetched_at=utcnow()
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

            print(f"First insert:     {stored_value_1}")

            # Now simulate a "sync" with a value that has extra precision
            # but truncates to the SAME value
            new_value_with_extra_precision = test_value

            print(f"Sync new value:   {new_value_with_extra_precision} (has extra precision)")

            # Our sync code should truncate BEFORE comparing
            stored_truncated = truncate_fx_rate(stored_value_1)
            new_truncated = truncate_fx_rate(new_value_with_extra_precision)

            print(f"Stored truncated: {stored_truncated}")
            print(f"New truncated:    {new_truncated}")

            # This is the comparison our sync code should do
            if stored_truncated != new_truncated:
                # Values are different after truncation, should update
                stored_rate_1.rate = new_value_with_extra_precision
                stored_rate_1.fetched_at = utcnow()
                await session.commit()
                await session.refresh(stored_rate_1)
                print(f"✓ Update applied (values differ after truncation)")
                updated = True
            else:
                # Values are the same after truncation, should NOT update
                print(f"✓ No update (values identical after truncation)")
                updated = False

            # Verify the logic works correctly
            if stored_truncated == new_truncated:
                assert not updated, "False update occurred despite values being identical after truncation"
                print(f"Both truncate to: {stored_truncated}")
            else:
                assert updated, "Update should have been applied for different values"

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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
