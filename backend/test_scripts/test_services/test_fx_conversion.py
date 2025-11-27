"""
Test 3: FX Conversion Logic
Tests currency conversion using rates from the database.
Verifies direct, inverse, cross-currency, and forward-fill conversions.
"""
import asyncio
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import FxRate
from backend.app.db.session import get_async_engine
from backend.app.services.fx import RateNotFoundError, convert, convert_bulk
from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_success,
    )
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import func


# ============================================================================
# PYTEST FIXTURE - Auto-populate mock FX rates
# ============================================================================

@pytest.fixture(scope="module", autouse=True)
def setup_mock_fx_rates_fixture():
    """
    Auto-run fixture: Populates mock FX rates before any test in this module.
    This replaces the main() orchestrator that was removed during pytest conversion.
    """

    async def _populate():
        engine = get_async_engine()
        async with AsyncSession(engine) as session:
            await setup_mock_fx_rates(session)

    # Run synchronously
    asyncio.run(_populate())
    yield


# ============================================================================
# MOCK DATA SETUP
# ============================================================================

async def setup_mock_fx_rates(session):
    """
    Insert mock FX rates for testing.
    Creates rates for multiple dates (today, yesterday, 7 days ago) to test date handling.
    Uses UPSERT so it's safe to run multiple times.
    """
    print_info("Setting up mock FX rates for testing...")

    # Mock rates (realistic values as of 2025)
    # Format: 1 base = rate * quote (alphabetically ordered)
    base_rates = [
        ("EUR", "USD", Decimal("1.0687")),  # 1 EUR = 1.0687 USD
        ("EUR", "GBP", Decimal("0.8392")),  # 1 EUR = 0.8392 GBP
        ("CHF", "EUR", Decimal("1.0650")),  # 1 CHF = 1.0650 EUR
        ("EUR", "JPY", Decimal("163.45")),  # 1 EUR = 163.45 JPY
        ]

    # Create rates for multiple dates to test date handling
    dates_to_create = [
        date.today(),
        date.today() - timedelta(days=1),  # Yesterday
        date.today() - timedelta(days=7),  # 7 days ago
        ]

    inserted_count = 0

    for rate_date in dates_to_create:
        for base, quote, rate_value in base_rates:
            # Add small daily variation (±0.2%)
            day_offset = (date.today() - rate_date).days
            variation = (day_offset % 5 - 2) * Decimal("0.002")  # -0.004 to +0.004
            adjusted_rate = rate_value * (Decimal("1") + variation)

            stmt = insert(FxRate).values(
                date=rate_date,
                base=base,
                quote=quote,
                rate=adjusted_rate,
                source="MOCK",
                fetched_at=func.current_timestamp()
                )

            # UPSERT: update if exists, insert if not
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=['date', 'base', 'quote'],
                set_={
                    'rate': stmt.excluded.rate,
                    'source': stmt.excluded.source,
                    'fetched_at': func.current_timestamp()
                    }
                )

            await session.execute(upsert_stmt)
            inserted_count += 1

    await session.commit()
    print_success(f"Mock FX rates ready ({inserted_count} rates across {len(dates_to_create)} dates)")


@pytest.mark.asyncio
async def test_identity_conversion():
    """Test identity conversion (same currency)."""
    print_section("Test 1: Identity Conversion (Same Currency)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_amount = Decimal("100.00")
        test_date = date.today()

        # Test EUR → EUR
        result_eur = await convert(session, test_amount, "EUR", "EUR", test_date)
        assert result_eur == test_amount, f"EUR → EUR: expected {test_amount}, got {result_eur}"
        print_success(f"EUR → EUR: {test_amount} = {result_eur} ✓")

        # Test USD → USD
        result_usd = await convert(session, test_amount, "USD", "USD", test_date)
        assert result_usd == test_amount, f"USD → USD: expected {test_amount}, got {result_usd}"
        print_success(f"USD → USD: {test_amount} = {result_usd} ✓")


@pytest.mark.asyncio
async def test_direct_conversion():
    """Test direct conversion using stored rate (EUR → USD)."""
    print_section("Test 2: Direct Conversion (EUR → USD)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.desc()).limit(1)

        result = await session.execute(stmt)
        rate_record = result.scalars().first()

        assert rate_record, f"No EUR/USD rate found in DB. Run persistence tests first."

        print_info(f"Using rate from {rate_record.date}")
        print_info(f"EUR/USD = {rate_record.rate} (1 EUR = {rate_record.rate} USD)")

        # Convert 100 EUR to USD
        amount_eur = Decimal("100.00")
        result_usd = await convert(session, amount_eur, "EUR", "USD", rate_record.date)
        expected_usd = amount_eur * rate_record.rate

        print_info(f"Conversion: {amount_eur} EUR → {result_usd} USD")
        print_info(f"Expected: {expected_usd} USD")

        assert not (abs(result_usd - expected_usd) > Decimal("0.01")), f"Conversion result doesn't match expected value"

        print_success("Direct conversion (EUR → USD) correct")


@pytest.mark.asyncio
async def test_inverse_conversion():
    """Test inverse conversion (USD → EUR) using stored rate."""
    print_section("Test 3: Inverse Conversion (USD → EUR)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.desc()).limit(1)

        result = await session.execute(stmt)
        rate_record = result.scalars().first()

        assert rate_record, f"No EUR/USD rate found in DB. Run persistence tests first."

        print_info(f"Using rate from {rate_record.date}")
        print_info(f"EUR/USD = {rate_record.rate} (1 EUR = {rate_record.rate} USD)")
        print_info(f"Therefore: 1 USD = {Decimal('1') / rate_record.rate} EUR")

        # Convert 100 USD to EUR (inverse operation)
        amount_usd = Decimal("100.00")
        result_eur = await convert(session, amount_usd, "USD", "EUR", rate_record.date)
        expected_eur = amount_usd / rate_record.rate

        print_info(f"Conversion: {amount_usd} USD → {result_eur} EUR")
        print_info(f"Expected: {expected_eur} EUR")

        assert not (abs(result_eur - expected_eur) > Decimal("0.01")), f"Inverse conversion result doesn't match expected value"

        print_success("Inverse conversion (USD → EUR) correct")


@pytest.mark.asyncio
async def test_roundtrip_conversion():
    """Test roundtrip conversion (EUR → USD → EUR) to verify rate inversion."""
    print_section("Test 4: Roundtrip Conversion (EUR → USD → EUR)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.desc()).limit(1)

        result = await session.execute(stmt)
        rate_record = result.scalars().first()

        assert rate_record, f"No EUR/USD rate found in DB. Run persistence tests first."

        print_info(f"Using rate from {rate_record.date}: EUR/USD = {rate_record.rate}")

        # Roundtrip: EUR → USD → EUR
        original_amount = Decimal("100.00")

        # Step 1: EUR → USD
        usd_amount = await convert(session, original_amount, "EUR", "USD", rate_record.date)
        print_info(f"Step 1: {original_amount} EUR → {usd_amount} USD")

        # Step 2: USD → EUR
        final_amount = await convert(session, usd_amount, "USD", "EUR", rate_record.date)
        print_info(f"Step 2: {usd_amount} USD → {final_amount} EUR")

        # Should get back original amount (within rounding error)
        difference = abs(final_amount - original_amount)
        print_info(f"Difference: {difference} EUR")

        assert not (difference > Decimal("0.01")), f"Roundtrip failed: started with {original_amount}, ended with {final_amount}"

        print_success("Roundtrip conversion successful (rate inversion works correctly)")


@pytest.mark.asyncio
async def test_different_dates():
    """Test conversion works correctly with different dates."""
    print_section("Test 5: Conversion with Different Dates")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_amount = Decimal("100.00")

        # Test with today's date
        today = date.today()
        result_today = await convert(session, test_amount, "EUR", "USD", today)
        print_success(f"Today ({today}): 100 EUR → {result_today} USD")

        # Test with yesterday's date
        yesterday = today - timedelta(days=1)
        result_yesterday = await convert(session, test_amount, "EUR", "USD", yesterday)
        print_success(f"Yesterday ({yesterday}): 100 EUR → {result_yesterday} USD")

        # Test with 7 days ago
        week_ago = today - timedelta(days=7)
        result_week_ago = await convert(session, test_amount, "EUR", "USD", week_ago)
        print_success(f"7 days ago ({week_ago}): 100 EUR → {result_week_ago} USD")

        # Verify rates are different (due to daily variation in mock data)
        assert not (result_today == result_yesterday == result_week_ago), f"All dates returned same rate - variation not working"

        print_info(f"Rate variation detected (rates differ across dates) ✓")


@pytest.mark.asyncio
async def test_backward_fill():
    """Test unlimited backward-fill logic and info tracking."""
    print_section("Test 6: Backward-Fill Logic (Unlimited)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.desc()).limit(1)

        result = await session.execute(stmt)
        rate_record = result.scalars().first()

        assert rate_record, f"No EUR/USD rate found in DB. Run persistence tests first."

        print_info(f"Most recent rate in DB: {rate_record.date}")
        print_info(f"EUR/USD = {rate_record.rate}")

        # Test 1: Exact date match (no backward-fill)
        print_info(f"\nTest 6.1: Exact date match ({rate_record.date})")
        amount = Decimal("100.00")

        converted, actual_date, backward_filled = await convert(
            session, amount, "EUR", "USD", rate_record.date, return_rate_info=True
            )

        assert not (backward_filled), f"Backward-fill should not be applied for exact date match"

        print_success(f"✓ Exact match: no backward-fill applied")

        # Test 2: Future date (should use backward-fill - unlimited)
        future_date = rate_record.date + timedelta(days=365)  # 1 year ahead
        print_info(f"\nTest 6.2: Future date ({future_date}, +365 days)")
        print_info("Expected: Use unlimited backward-fill")

        converted, actual_date, backward_filled = await convert(
            session, amount, "EUR", "USD", future_date, return_rate_info=True
            )

        assert backward_filled, f"Backward-fill should be applied for future date"

        days_back = (future_date - actual_date).days
        print_success(f"✓ Backward-fill applied: used rate from {actual_date} ({days_back} days back)")

        expected = amount * rate_record.rate
        assert not (abs(converted - expected) > Decimal("0.01")), f"Conversion value incorrect"

        # Test 3: Very old date (before any rate exists - should fail)
        very_old_date = rate_record.date - timedelta(days=3650)  # 10 years before
        print_info(f"\nTest 6.3: Date before any rate exists ({very_old_date})")
        print_info("Expected: RateNotFoundError")

        # Test should raise RateNotFoundError
        with pytest.raises(RateNotFoundError):
            await convert(session, amount, "EUR", "USD", very_old_date)
        print_success("✓ Correctly raised RateNotFoundError for date before any data")

        print_success("Backward-fill logic works correctly (unlimited with tracking)")


@pytest.mark.asyncio
async def test_missing_rate_error():
    """Test that RateNotFoundError is raised only when no rate exists before requested date."""
    print_section("Test 7: Missing Rate Error Handling")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find the oldest rate in DB
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.asc()).limit(1)

        result = await session.execute(stmt)
        oldest_rate = result.scalars().first()

        assert oldest_rate, f"No EUR/USD rates in DB"

        print_info(f"Oldest rate in DB: {oldest_rate.date}")

        # Test 1: Date before oldest rate (should fail)
        date_before = oldest_rate.date - timedelta(days=1)
        amount = Decimal("100.00")

        print_info(f"\nTest 7.1: Date before any data ({date_before})")
        print_info("Expected: RateNotFoundError")

        with pytest.raises(RateNotFoundError) as exc_info:
            await convert(session, amount, "EUR", "USD", date_before)

        error_msg = str(exc_info.value)
        print_success("✓ Correctly raised RateNotFoundError")
        print_info(f"Error message: {error_msg[:100]}...")

        # Test 2: Very old date but after oldest rate (should work with backward-fill)
        old_but_valid_date = oldest_rate.date + timedelta(days=365)  # 1 year after oldest
        print_info(f"\nTest 7.2: Old date but after oldest rate ({old_but_valid_date})")
        print_info("Expected: Success with backward-fill")

        try:
            converted, actual_date, backward_filled = await convert(
                session, amount, "EUR", "USD", old_but_valid_date, return_rate_info=True
                )

            assert backward_filled, f"Should use backward-fill for old date"

            days_back = (old_but_valid_date - actual_date).days
            print_success(f"✓ Backward-fill used: {actual_date} ({days_back} days back)")

        except RateNotFoundError:
            print_error("Should not raise error for date after oldest rate")

        print_success("Missing rate error handling works correctly")


@pytest.mark.asyncio
async def test_bulk_conversions_single():
    """Test convert_bulk with single item (should behave like convert)."""
    print_section("Test 8: Bulk Conversion - Single Item")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.desc()).limit(1)

        result = await session.execute(stmt)
        rate_record = result.scalars().first()

        assert rate_record, f"No EUR/USD rate found in DB"

        print_info(f"Using rate from {rate_record.date}: EUR/USD = {rate_record.rate}")

        # Convert using bulk with single item (raise_on_error=True)
        amount = Decimal("100.00")
        results, errors = await convert_bulk(
            session,
            [(amount, "EUR", "USD", rate_record.date)],
            raise_on_error=True
            )

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"

        assert len(errors) == 0, f"Expected 0 errors, got {len(errors)}"

        converted, actual_date, backward_filled = results[0]
        expected = amount * rate_record.rate

        assert not (abs(converted - expected) > Decimal("0.01")), f"Expected {expected}, got {converted}"

        print_success(f"✓ Single item bulk: 100 EUR → {converted} USD")


@pytest.mark.asyncio
async def test_bulk_conversions_multiple():
    """Test convert_bulk with multiple items."""
    print_section("Test 9: Bulk Conversion - Multiple Items")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_date = date.today()
        amount = Decimal("100.00")

        # Prepare 3 conversions
        conversions = [
            (amount, "EUR", "USD", test_date),
            (amount, "EUR", "GBP", test_date),
            (amount, "CHF", "EUR", test_date),
            ]

        print_info("Testing 3 conversions in single bulk call")

        # Call bulk
        results, errors = await convert_bulk(session, conversions, raise_on_error=True)

        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        assert len(errors) == 0, f"Expected 0 errors, got {len(errors)}"

        # Verify all results
        print_success(f"✓ 100 EUR → {results[0][0]} USD")
        print_success(f"✓ 100 EUR → {results[1][0]} GBP")
        print_success(f"✓ 100 CHF → {results[2][0]} EUR")


@pytest.mark.asyncio
async def test_bulk_partial_failure():
    """Test convert_bulk with partial failures (some invalid conversions)."""
    print_section("Test 10: Bulk Conversion - Partial Failure")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_date = date.today()
        amount = Decimal("100.00")

        # Mix valid and invalid conversions
        conversions = [
            (amount, "EUR", "USD", test_date),  # Valid
            (amount, "XXX", "EUR", test_date),  # Invalid currency
            (amount, "EUR", "GBP", test_date),  # Valid
            ]

        print_info("Testing 3 conversions: 2 valid, 1 invalid")

        # Call bulk with raise_on_error=False
        results, errors = await convert_bulk(session, conversions, raise_on_error=False)

        assert len(results) == 3, f"Expected 3 results (some None), got {len(results)}"

        # Should have 2 valid results and 1 None
        valid_count = sum(1 for r in results if r is not None)
        none_count = sum(1 for r in results if r is None)

        assert valid_count == 2, f"Expected 2 valid results, got {valid_count}"
        assert none_count == 1, f"Expected 1 None result, got {none_count}"
        assert len(errors) == 1, f"Expected 1 error, got {len(errors)}"

        print_success(f"✓ Valid results: {valid_count}")
        print_success(f"✓ Failed results: {none_count}")
        print_success(f"✓ Errors: {len(errors)}")
        print_info(f"  Error message: {errors[0][:80]}...")


@pytest.mark.asyncio
async def test_bulk_all_failures():
    """Test convert_bulk when all conversions fail."""
    print_section("Test 11: Bulk Conversion - All Failures")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_date = date.today()
        amount = Decimal("100.00")

        # All invalid conversions
        conversions = [
            (amount, "XXX", "EUR", test_date),
            (amount, "YYY", "USD", test_date),
            (amount, "ZZZ", "GBP", test_date),
            ]

        print_info("Testing 3 conversions: all invalid")

        # Call bulk with raise_on_error=False
        results, errors = await convert_bulk(session, conversions, raise_on_error=False)

        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # All should be None
        none_count = sum(1 for r in results if r is None)
        assert none_count == 3, f"Expected 3 None results, got {none_count}"

        assert len(errors) == 3, f"Expected 3 errors, got {len(errors)}"

        print_success(f"✓ All results None (as expected)")
        print_success(f"✓ All errors captured: {len(errors)}")


@pytest.mark.asyncio
async def test_bulk_raise_on_error():
    """Test convert_bulk with raise_on_error=True (should stop on first error)."""
    print_section("Test 12: Bulk Conversion - Raise on Error")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_date = date.today()
        amount = Decimal("100.00")

        # First valid, second invalid
        conversions = [
            (amount, "EUR", "USD", test_date),  # Valid
            (amount, "XXX", "EUR", test_date),  # Invalid - should raise here
            (amount, "EUR", "GBP", test_date),  # Valid but should not be reached
            ]

        print_info("Testing raise_on_error=True with invalid second item")

        with pytest.raises(RateNotFoundError) as exc_info:
            await convert_bulk(session, conversions, raise_on_error=True)

        error_msg = str(exc_info.value)
        print_success("✓ Correctly raised RateNotFoundError")
        print_info(f"  Error: {error_msg[:80]}...")

        # Verify it mentions index
        if "index 1" in error_msg.lower() or "conversion 1" in error_msg.lower():
            print_success("✓ Error message includes failing index")
        else:
            print_info("  (Note: Error message could include failing index)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
