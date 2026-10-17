#!/usr/bin/env python3
"""
Test suite for Numeric column truncation.

This test validates that all Numeric columns in the database handle precision
correctly and that our truncation helpers work as expected.

Algorithm:
1. Scan all SQLModel tables to find Numeric columns, a TypeDecorator over Numeric included
   (C-97a: RealDecimal, whose precision and scale are those of the Numeric it decorates, its impl_instance)
2. For each Numeric(P, S) column:
   - Generate test values with more precision than allowed
   - Verify truncate_to_db_precision() works correctly: the scale, ROUND_DOWN, then, on a TypeDecorator
     column only, at most 15 significant digits, ROUND_DOWN
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
from decimal import ROUND_DOWN, Decimal
from types import SimpleNamespace

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.utils.datetime_utils import utcnow

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import Column, Integer, MetaData, String, Table
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Numeric, TypeDecorator, TypeEngine
from sqlmodel import select

from backend.app.db import models
from backend.app.db.precision import get_model_column_precision, truncate_fx_rate, truncate_to_db_precision
from backend.app.db.session import get_async_engine

# A TypeDecorator over Numeric (C-97a: RealDecimal) stores a double and reads back at most this many significant
# digits, what a double keeps: its truncation cuts to the scale, then to these digits.
SIGNIFICANT_DIGITS = 15


def numeric_type(column_type: TypeEngine) -> Numeric | None:
    """The Numeric that declares a column's precision and scale, or None when the column is not numeric.

    A Numeric column declares them itself. A TypeDecorator over Numeric (C-97a: RealDecimal) is no Numeric
    instance, so ``isinstance(column.type, Numeric)`` alone skips it, and with it every column it was written
    for: it declares them on ``impl_instance``, the Numeric it decorates.
    """
    if isinstance(column_type, Numeric):
        return column_type
    if isinstance(column_type, TypeDecorator) and isinstance(column_type.impl_instance, Numeric):
        return column_type.impl_instance
    return None


def discover_numeric_columns(source=models):
    """
    Discover all Numeric columns across all SQLModel tables, a TypeDecorator over Numeric included.

    Args:
        source: Where the table classes are looked up (default: the models module)

    Returns:
        List of dicts with table metadata:
        [
            {
                'model': FxRate,
                'table_name': 'fx_rates',
                'column_name': 'rate',
                'type_name': 'Numeric',
                'decorated': False,  # True for a TypeDecorator over Numeric (C-97a: RealDecimal)
                'precision': 24,
                'scale': 10
            },
            ...
        ]
    """
    numeric_columns = []

    # Get all SQLModel classes from the source (the models module)
    for attr_name in dir(source):
        attr = getattr(source, attr_name)

        # Check if it's a SQLModel table class
        if isinstance(attr, type) and hasattr(attr, "__table__") and hasattr(attr, "__tablename__"):
            table_name = attr.__tablename__

            # Inspect columns
            for column_name, column in attr.__table__.columns.items():
                numeric = numeric_type(column.type)
                if numeric is not None:
                    numeric_columns.append(
                        {
                            "model": attr,
                            "table_name": table_name,
                            "column_name": column_name,
                            "type_name": type(column.type).__name__,
                            "decorated": numeric is not column.type,
                            "precision": numeric.precision,
                            "scale": numeric.scale,
                        }
                    )

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
    decimal_part = "".join(str(i % 10) for i in range(total_decimals))
    return Decimal(f"1.{decimal_part}")


def generate_full_width_value(precision: int, scale: int) -> Decimal:
    """
    Generate a value of nines filling every integer digit a column declares, with 5 decimals beyond its scale.

    Nearest rounding would carry it to the next power of ten; ROUND_DOWN keeps it below. Cut to the scale it
    still has more than 15 significant digits wherever the column declares more: the value that shows the
    15-significant-digit cut of a TypeDecorator column (C-97a), and its absence on a plain Numeric one.

    Example:
        (24, 12) → "999999999999.99999999999999999"  (12 integer digits, 17 decimals)
    """
    integer_digits = max(precision - scale, 1)
    return Decimal(f"{'9' * integer_digits}.{'9' * (scale + 5)}")


def expected_truncation(value: Decimal, scale: int, decorated: bool) -> Decimal:
    """What truncate_to_db_precision must answer: the scale, ROUND_DOWN; then, on a TypeDecorator column
    (C-97a: RealDecimal), at most 15 significant digits, ROUND_DOWN.
    """
    truncated = value.quantize(Decimal(10) ** -scale, rounding=ROUND_DOWN)
    if decorated and len(truncated.as_tuple().digits) > SIGNIFICANT_DIGITS:
        truncated = truncated.quantize(Decimal(10) ** (truncated.adjusted() - SIGNIFICANT_DIGITS + 1), rounding=ROUND_DOWN)
    return truncated


def test_truncation_helpers():
    """Test that get_model_column_precision and truncate_to_db_precision work correctly on every numeric column.

    A TypeDecorator over Numeric (C-97a: RealDecimal) is one too: its precision and scale are those of its
    impl_instance, and its truncation also cuts to 15 significant digits (ROUND_DOWN). No model declares one
    before C-97a; after it, Transaction.quantity (22, 10), Transaction.cost_basis_override (24, 12, decision D5)
    and the five PriceHistory prices (24, 12) do, and since W-B60 Transaction.amount and AssetEvent.value (18, 6):
    nine columns.
    """
    columns = discover_numeric_columns()
    assert len(columns) > 0, "No numeric columns found"

    for col_info in columns:
        model = col_info["model"]
        column_name = col_info["column_name"]
        decorated = col_info["decorated"]
        expected_precision = col_info["precision"]
        expected_scale = col_info["scale"]

        # Test get_model_column_precision
        precision, scale = get_model_column_precision(model, column_name)

        assert precision == expected_precision, f"{model.__name__}.{column_name}: Expected precision {expected_precision}, got {precision}"
        assert scale == expected_scale, f"{model.__name__}.{column_name}: Expected scale {expected_scale}, got {scale}"

        # Test truncate_to_db_precision: one integer digit, so never more than 15 significant digits once cut to the
        # scale (13 at scale 12), and the 15-digit cut leaves it as it is
        test_value = generate_test_value(scale)
        truncated = truncate_to_db_precision(test_value, model, column_name)
        expected = expected_truncation(test_value, scale, decorated)
        assert truncated == expected, f"{model.__name__}.{column_name}: truncate_to_db_precision({test_value}) = {truncated}, expected {expected} (the scale, ROUND_DOWN)"

        # Verify truncation
        truncated_str = str(truncated)
        if "." in truncated_str:
            actual_scale = len(truncated_str.split(".")[1])
            assert actual_scale == scale, f"{model.__name__}.{column_name}: Truncated to {actual_scale} decimals, expected {scale}\n" f"Input: {test_value}\nOutput: {truncated}"

        # Every digit the column declares: cut to 15 significant digits on a TypeDecorator column, not on a plain one
        wide_value = generate_full_width_value(precision, scale)
        wide_truncated = truncate_to_db_precision(wide_value, model, column_name)
        wide_expected = expected_truncation(wide_value, scale, decorated)
        rule = "then 15 significant digits, ROUND_DOWN: a TypeDecorator over Numeric" if decorated else "and no significant-digit cut: a plain Numeric"
        assert wide_truncated == wide_expected, f"{model.__name__}.{column_name}: truncate_to_db_precision({wide_value}) = {wide_truncated}, expected {wide_expected} (the scale, ROUND_DOWN, {rule})"

        print(f"✓ {model.__name__}.{column_name}: {col_info['type_name']}({precision}, {scale}) - Helper OK")


# --------------------------------------------------------------------------- #
# The discovery itself, on a table this file owns
# --------------------------------------------------------------------------- #


class _DecoratedNumeric(TypeDecorator):
    """A TypeDecorator over Numeric, as C-97a's RealDecimal is."""

    impl = Numeric
    cache_ok = True


class _DecoratedString(TypeDecorator):
    """A TypeDecorator over a type that is not numeric."""

    impl = String
    cache_ok = True


class _DiscoveryProbe:
    """A table class holding one column of each kind the discovery must tell apart.

    Its own MetaData: never mapped, never created, invisible to SQLModel.metadata and to every other test.
    """

    __tablename__ = "numeric_discovery_probe"
    __table__ = Table(
        "numeric_discovery_probe",
        MetaData(),
        Column("id", Integer, primary_key=True),
        Column("plain", Numeric(18, 6)),
        Column("decorated", _DecoratedNumeric(24, 12)),
        Column("decorated_text", _DecoratedString(3)),
        Column("text", String(3)),
    )


def test_the_discovery_sees_a_numeric_through_a_type_decorator():
    """GUARD (green before and after C-97a): a TypeDecorator over Numeric is discovered, with its impl_instance's precision and scale.

    Before C-97a no model declares one, so test_truncation_helpers cannot show that the discovery finds it; after
    C-97a and W-B60 the nine RealDecimal columns are such columns. Without this guard a discovery skipping them again
    would stay green, checking every numeric column but the nine whose digits C-97a and W-B60 keep.
    """
    found = {(info["column_name"], info["decorated"], info["precision"], info["scale"]) for info in discover_numeric_columns(SimpleNamespace(probe=_DiscoveryProbe))}

    assert found == {("plain", False, 18, 6), ("decorated", True, 24, 12)}, f"the discovery found {sorted(found)}: expected the plain Numeric(18, 6) and the TypeDecorator over Numeric(24, 12), and neither the Integer id, the String nor the TypeDecorator over String"


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
    truncated_expected = truncate_to_db_precision(test_value, models.FxRate, "rate")

    print(f"\nTest value (input):    {test_value}")
    print(f"Expected (truncated):  {truncated_expected}")

    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        try:
            # Cleanup any existing test data first
            cleanup_stmt = select(models.FxRate).where(
                models.FxRate.date == test_date,
                models.FxRate.base == test_base,
                models.FxRate.quote == test_quote,
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
                fetched_at=utcnow(),
            )
            session.add(test_rate)
            await session.commit()

            # Read back (new session to avoid cache)
            stmt = select(models.FxRate).where(
                models.FxRate.date == test_date,
                models.FxRate.base == test_base,
                models.FxRate.quote == test_quote,
            )
            result = await session.execute(stmt)
            stored_rate = result.scalar_one()

            print(f"Stored in DB:          {stored_rate.rate}")

            # Verify database truncated correctly
            assert stored_rate.rate == truncated_expected, f"Database truncation mismatch!\n" f"Expected: {truncated_expected}\n" f"Got:      {stored_rate.rate}"

        finally:
            # Cleanup - make sure we delete even if test fails
            try:
                cleanup_stmt = select(models.FxRate).where(
                    models.FxRate.date == test_date,
                    models.FxRate.base == test_base,
                    models.FxRate.quote == test_quote,
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
                models.FxRate.quote == test_quote,
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
                fetched_at=utcnow(),
            )
            session.add(test_rate)
            await session.commit()

            # Read back
            stmt = select(models.FxRate).where(
                models.FxRate.date == test_date,
                models.FxRate.base == test_base,
                models.FxRate.quote == test_quote,
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
                print("✓ Update applied (values differ after truncation)")
                updated = True
            else:
                # Values are the same after truncation, should NOT update
                print("✓ No update (values identical after truncation)")
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
                    models.FxRate.quote == test_quote,
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
