"""
Test 3: FX Conversion Logic
Tests currency conversion using rates from the database.
Verifies direct, inverse, cross-currency, and forward-fill conversions.

X-R38 (the FX side of W-B58): a stored rate no column can keep reads as a missing rate, and compute_chain_rate answers
None for a date whose leg is unusable (see the X-R38 block below).
"""

import asyncio
import re
import sys
from datetime import date, timedelta
from decimal import Decimal

import pytest

from backend.app.config import PROJECT_ROOT

# Add project root to path
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import func, text
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.app.db.models import FxRate
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.services.fx.base import RateNotFoundError
from backend.app.services.fx.conversion import compute_chain_rate, convert_bulk
from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_success,
)

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
                fetched_at=func.current_timestamp(),
            )

            # UPSERT: update if exists, insert if not
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["date", "base", "quote"],
                set_={
                    "rate": stmt.excluded.rate,
                    "source": stmt.excluded.source,
                    "fetched_at": func.current_timestamp(),
                },
            )

            await session.execute(upsert_stmt)
            inserted_count += 1

    await session.commit()
    print_success(f"Mock FX rates ready ({inserted_count} rates across {len(dates_to_create)} dates)")


async def _convert_single(session, amount, to_currency, as_of_date, return_rate_info=False):
    """Helper: single-item wrapper around convert_bulk (replaces removed convert())."""
    results, errors = await convert_bulk(session, [(amount, to_currency, as_of_date)], raise_on_error=True)
    converted, rate_date, backward_filled = results[0]
    if return_rate_info:
        return converted, rate_date, backward_filled
    return converted


@pytest.mark.asyncio
async def test_identity_conversion():
    """Test identity conversion (same currency)."""
    print_section("Test 1: Identity Conversion (Same Currency)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_amount = Decimal("100.00")
        test_date = date.today()

        # Test EUR → EUR (using Currency objects)
        amount_eur = Currency(code="EUR", amount=test_amount)
        result_eur = await _convert_single(session, amount_eur, "EUR", test_date)
        assert result_eur.amount == test_amount, f"EUR → EUR: expected {test_amount}, got {result_eur.amount}"
        assert result_eur.code == "EUR", f"EUR → EUR: expected code EUR, got {result_eur.code}"
        print_success(f"EUR → EUR: {test_amount} = {result_eur} ✓")

        # Test USD → USD
        amount_usd = Currency(code="USD", amount=test_amount)
        result_usd = await _convert_single(session, amount_usd, "USD", test_date)
        assert result_usd.amount == test_amount, f"USD → USD: expected {test_amount}, got {result_usd.amount}"
        assert result_usd.code == "USD", f"USD → USD: expected code USD, got {result_usd.code}"
        print_success(f"USD → USD: {test_amount} = {result_usd} ✓")


@pytest.mark.asyncio
async def test_direct_conversion():
    """Test direct conversion using stored rate (EUR → USD)."""
    print_section("Test 2: Direct Conversion (EUR → USD)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(FxRate.base == "EUR", FxRate.quote == "USD").order_by(FxRate.date.desc()).limit(1)

        result = await session.execute(stmt)
        rate_record = result.scalars().first()

        assert rate_record, "No EUR/USD rate found in DB. Run persistence tests first."

        print_info(f"Using rate from {rate_record.date}")
        print_info(f"EUR/USD = {rate_record.rate} (1 EUR = {rate_record.rate} USD)")

        # Convert 100 EUR to USD (using Currency)
        amount_eur = Currency(code="EUR", amount=Decimal("100.00"))
        result_usd = await _convert_single(session, amount_eur, "USD", rate_record.date)
        expected_usd = amount_eur.amount * rate_record.rate

        print_info(f"Conversion: {amount_eur} → {result_usd}")
        print_info(f"Expected: {expected_usd} USD")

        assert result_usd.code == "USD", f"Expected currency USD, got {result_usd.code}"
        assert not (abs(result_usd.amount - expected_usd) > Decimal("0.01")), "Conversion result doesn't match expected value"

        print_success("Direct conversion (EUR → USD) correct")


@pytest.mark.asyncio
async def test_inverse_conversion():
    """Test inverse conversion (USD → EUR) using stored rate."""
    print_section("Test 3: Inverse Conversion (USD → EUR)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(FxRate.base == "EUR", FxRate.quote == "USD").order_by(FxRate.date.desc()).limit(1)

        result = await session.execute(stmt)
        rate_record = result.scalars().first()

        assert rate_record, "No EUR/USD rate found in DB. Run persistence tests first."

        print_info(f"Using rate from {rate_record.date}")
        print_info(f"EUR/USD = {rate_record.rate} (1 EUR = {rate_record.rate} USD)")
        print_info(f"Therefore: 1 USD = {Decimal('1') / rate_record.rate} EUR")

        # Convert 100 USD to EUR (inverse operation, using Currency)
        amount_usd = Currency(code="USD", amount=Decimal("100.00"))
        result_eur = await _convert_single(session, amount_usd, "EUR", rate_record.date)
        expected_eur = amount_usd.amount / rate_record.rate

        print_info(f"Conversion: {amount_usd} → {result_eur}")
        print_info(f"Expected: {expected_eur} EUR")

        assert result_eur.code == "EUR", f"Expected currency EUR, got {result_eur.code}"
        assert not (abs(result_eur.amount - expected_eur) > Decimal("0.01")), "Inverse conversion result doesn't match expected value"

        print_success("Inverse conversion (USD → EUR) correct")


@pytest.mark.asyncio
async def test_roundtrip_conversion():
    """Test roundtrip conversion (EUR → USD → EUR) to verify rate inversion."""
    print_section("Test 4: Roundtrip Conversion (EUR → USD → EUR)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(FxRate.base == "EUR", FxRate.quote == "USD").order_by(FxRate.date.desc()).limit(1)

        result = await session.execute(stmt)
        rate_record = result.scalars().first()

        assert rate_record, "No EUR/USD rate found in DB. Run persistence tests first."

        print_info(f"Using rate from {rate_record.date}: EUR/USD = {rate_record.rate}")

        # Roundtrip: EUR → USD → EUR (using Currency)
        original_amount = Decimal("100.00")

        # Step 1: EUR → USD
        eur_currency = Currency(code="EUR", amount=original_amount)
        usd_result = await _convert_single(session, eur_currency, "USD", rate_record.date)
        print_info(f"Step 1: {eur_currency} → {usd_result}")

        # Step 2: USD → EUR
        final_result = await _convert_single(session, usd_result, "EUR", rate_record.date)
        print_info(f"Step 2: {usd_result} → {final_result}")

        # Should get back original amount (within rounding error)
        difference = abs(final_result.amount - original_amount)
        print_info(f"Difference: {difference} EUR")

        assert final_result.code == "EUR", f"Expected EUR, got {final_result.code}"
        assert not (difference > Decimal("0.01")), f"Roundtrip failed: started with {original_amount}, ended with {final_result.amount}"

        print_success("Roundtrip conversion successful (rate inversion works correctly)")


@pytest.mark.asyncio
async def test_different_dates():
    """Test conversion works correctly with different dates."""
    print_section("Test 5: Conversion with Different Dates")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_amount = Currency(code="EUR", amount=Decimal("100.00"))

        # Test with today's date
        today = date.today()
        result_today = await _convert_single(session, test_amount, "USD", today)
        print_success(f"Today ({today}): {test_amount} → {result_today}")

        # Test with yesterday's date
        yesterday = today - timedelta(days=1)
        result_yesterday = await _convert_single(session, test_amount, "USD", yesterday)
        print_success(f"Yesterday ({yesterday}): {test_amount} → {result_yesterday}")

        # Test with 7 days ago
        week_ago = today - timedelta(days=7)
        result_week_ago = await _convert_single(session, test_amount, "USD", week_ago)
        print_success(f"7 days ago ({week_ago}): {test_amount} → {result_week_ago}")

        # Verify rates are different (due to daily variation in mock data)
        assert not (result_today.amount == result_yesterday.amount == result_week_ago.amount), "All dates returned same rate - variation not working"

        print_info("Rate variation detected (rates differ across dates) ✓")


@pytest.mark.asyncio
async def test_backward_fill():
    """Test unlimited backward-fill logic and info tracking."""
    print_section("Test 6: Backward-Fill Logic (Unlimited)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(FxRate.base == "EUR", FxRate.quote == "USD").order_by(FxRate.date.desc()).limit(1)

        result = await session.execute(stmt)
        rate_record = result.scalars().first()

        assert rate_record, "No EUR/USD rate found in DB. Run persistence tests first."

        print_info(f"Most recent rate in DB: {rate_record.date}")
        print_info(f"EUR/USD = {rate_record.rate}")

        # Test 1: Exact date match (no backward-fill)
        print_info(f"\nTest 6.1: Exact date match ({rate_record.date})")
        amount = Currency(code="EUR", amount=Decimal("100.00"))

        converted, actual_date, backward_filled = await _convert_single(session, amount, "USD", rate_record.date, return_rate_info=True)

        assert not (backward_filled), "Backward-fill should not be applied for exact date match"

        print_success("✓ Exact match: no backward-fill applied")

        # Test 2: Future date (should use backward-fill - unlimited)
        future_date = rate_record.date + timedelta(days=365)  # 1 year ahead
        print_info(f"\nTest 6.2: Future date ({future_date}, +365 days)")
        print_info("Expected: Use unlimited backward-fill")

        converted, actual_date, backward_filled = await _convert_single(session, amount, "USD", future_date, return_rate_info=True)

        assert backward_filled, "Backward-fill should be applied for future date"

        days_back = (future_date - actual_date).days
        print_success(f"✓ Backward-fill applied: used rate from {actual_date} ({days_back} days back)")

        expected = amount.amount * rate_record.rate
        assert not (abs(converted.amount - expected) > Decimal("0.01")), "Conversion value incorrect"

        # Test 3: Very old date (before any rate exists - should fail)
        very_old_date = rate_record.date - timedelta(days=3650)  # 10 years before
        print_info(f"\nTest 6.3: Date before any rate exists ({very_old_date})")
        print_info("Expected: RateNotFoundError")

        # Test should raise RateNotFoundError
        with pytest.raises(RateNotFoundError):
            await _convert_single(session, amount, "USD", very_old_date)
        print_success("✓ Correctly raised RateNotFoundError for date before any data")

        print_success("Backward-fill logic works correctly (unlimited with tracking)")


@pytest.mark.asyncio
async def test_missing_rate_error():
    """Test that RateNotFoundError is raised only when no rate exists before requested date.

    The test creates the gap it measures: two EUR/XTS rates (XTS is the ISO 4217 code
    reserved for testing; no seed writes the pair) on fixed dates far from any seeded
    history, flushed in this session and never committed. Deriving the dates from the
    oldest EUR/USD row of the shared table made the verdict depend on the database
    contents and on today's date: on a seeded database "oldest + 365 days" is a weekday
    with a rate of its own, so nothing was backward-filled.
    """
    print_section("Test 7: Missing Rate Error Handling")

    # Stored as EUR/XTS: base < quote, as fx_rates requires. The later rate is a trap with a
    # different value: backward-fill for gap_date must use the rate before it, never the one after.
    oldest_rate_date = date(2001, 1, 8)
    gap_date = date(2001, 1, 10)  # no rate of its own: only backward-fill can answer
    later_rate_date = date(2001, 1, 12)
    oldest_rate = Decimal("1.25")
    later_rate = Decimal("1.40")
    amount = Currency(code="EUR", amount=Decimal("100.00"))

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Precondition, checked not assumed: no EUR/XTS rate on or before the last date written here
        leftover_stmt = select(FxRate.date).where(FxRate.base == "EUR", FxRate.quote == "XTS", FxRate.date <= later_rate_date).order_by(FxRate.date)
        leftover_dates = (await session.execute(leftover_stmt)).scalars().all()
        if leftover_dates:
            leftovers = ", ".join(str(d) for d in leftover_dates)
            print_error(f"EUR/XTS already has rates on or before {later_rate_date}: {leftovers}")
            pytest.fail(f"Precondition failed: this test needs EUR/XTS without rates on or before {later_rate_date}, found {leftovers}")

        try:
            # Flushed, never committed: only this session sees them, and the rollback removes them
            session.add_all(
                [
                    FxRate(date=oldest_rate_date, base="EUR", quote="XTS", rate=oldest_rate, source="TEST"),
                    FxRate(date=later_rate_date, base="EUR", quote="XTS", rate=later_rate, source="TEST"),
                ]
            )
            await session.flush()

            print_info(f"Oldest EUR/XTS rate: {oldest_rate_date} = {oldest_rate} (next: {later_rate_date} = {later_rate})")

            # Test 1: Date before oldest rate (should fail)
            date_before = oldest_rate_date - timedelta(days=1)

            print_info(f"\nTest 7.1: Date before any data ({date_before})")
            print_info("Expected: RateNotFoundError")

            with pytest.raises(RateNotFoundError) as exc_info:
                await _convert_single(session, amount, "XTS", date_before)

            error_msg = str(exc_info.value)
            print_success("✓ Correctly raised RateNotFoundError")
            print_info(f"Error message: {error_msg[:100]}...")

            # Test 2: Date after oldest rate, without a rate of its own (should work with backward-fill)
            print_info(f"\nTest 7.2: Date after oldest rate, without its own rate ({gap_date})")
            print_info(f"Expected: Success with backward-fill from {oldest_rate_date}")

            converted, actual_date, backward_filled = await _convert_single(session, amount, "XTS", gap_date, return_rate_info=True)
            expected = amount.amount * oldest_rate

            assert backward_filled is True, f"Should use backward-fill for {gap_date}, got backward_filled={backward_filled}"
            assert actual_date == oldest_rate_date, f"Backward-fill should use the latest rate on or before {gap_date} ({oldest_rate_date}), used {actual_date}"
            assert converted.code == "XTS", f"Expected XTS, got {converted.code}"
            assert not (abs(converted.amount - expected) > Decimal("0.01")), f"Expected {expected}, got {converted.amount}"

            days_back = (gap_date - actual_date).days
            print_success(f"✓ Backward-fill used: {actual_date} ({days_back} days back)")

            # Test 3: Exact date of the oldest rate (control: backward-fill is not always reported)
            print_info(f"\nTest 7.3: Exact date of oldest rate ({oldest_rate_date})")
            print_info("Expected: Success without backward-fill")

            converted, actual_date, backward_filled = await _convert_single(session, amount, "XTS", oldest_rate_date, return_rate_info=True)

            assert backward_filled is False, f"Backward-fill should not be applied for exact date match, got backward_filled={backward_filled}"
            assert actual_date == oldest_rate_date, f"Expected rate date {oldest_rate_date}, got {actual_date}"
            assert not (abs(converted.amount - expected) > Decimal("0.01")), f"Expected {expected}, got {converted.amount}"

            print_success("✓ Exact match: no backward-fill applied")
        finally:
            await session.rollback()

        print_success("Missing rate error handling works correctly")


@pytest.mark.asyncio
async def test_bulk_conversions_single():
    """Test convert_bulk with single item (should behave like convert)."""
    print_section("Test 8: Bulk Conversion - Single Item")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(FxRate.base == "EUR", FxRate.quote == "USD").order_by(FxRate.date.desc()).limit(1)

        result = await session.execute(stmt)
        rate_record = result.scalars().first()

        assert rate_record, "No EUR/USD rate found in DB"

        print_info(f"Using rate from {rate_record.date}: EUR/USD = {rate_record.rate}")

        # Convert using bulk with single item (raise_on_error=True)
        # New signature: (Currency, to_currency, date)
        amount = Currency(code="EUR", amount=Decimal("100.00"))
        results, errors = await convert_bulk(session, [(amount, "USD", rate_record.date)], raise_on_error=True)

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"

        assert len(errors) == 0, f"Expected 0 errors, got {len(errors)}"

        converted, actual_date, backward_filled = results[0]
        expected = amount.amount * rate_record.rate

        assert converted.code == "USD", f"Expected USD, got {converted.code}"
        assert not (abs(converted.amount - expected) > Decimal("0.01")), f"Expected {expected}, got {converted.amount}"

        print_success(f"✓ Single item bulk: {amount} → {converted}")


@pytest.mark.asyncio
async def test_bulk_conversions_multiple():
    """Test convert_bulk with multiple items."""
    print_section("Test 9: Bulk Conversion - Multiple Items")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_date = date.today()

        # Prepare 3 conversions using Currency objects
        # New signature: (Currency, to_currency, date)
        conversions = [
            (Currency(code="EUR", amount=Decimal("100.00")), "USD", test_date),
            (Currency(code="EUR", amount=Decimal("100.00")), "GBP", test_date),
            (Currency(code="CHF", amount=Decimal("100.00")), "EUR", test_date),
        ]

        print_info("Testing 3 conversions in single bulk call")

        # Call bulk
        results, errors = await convert_bulk(session, conversions, raise_on_error=True)

        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        assert len(errors) == 0, f"Expected 0 errors, got {len(errors)}"

        # Verify all results
        print_success(f"✓ 100 EUR → {results[0][0]}")
        print_success(f"✓ 100 EUR → {results[1][0]}")
        print_success(f"✓ 100 CHF → {results[2][0]}")


@pytest.mark.asyncio
async def test_bulk_partial_failure():
    """Test convert_bulk with partial failures (some invalid conversions).

    Note: Currency validates codes at creation, so we test failure by using
    a date where no rates exist for some pairs.
    """
    print_section("Test 10: Bulk Conversion - Partial Failure")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_date = date.today()
        very_old_date = date(1900, 1, 1)  # No rates exist for this date

        # Mix valid and failing conversions using Currency objects
        # New signature: (Currency, to_currency, date)
        conversions = [
            (Currency(code="EUR", amount=Decimal("100.00")), "USD", test_date),  # Valid
            (
                Currency(code="EUR", amount=Decimal("100.00")),
                "USD",
                very_old_date,
            ),  # Fails - no rate for date
            (Currency(code="EUR", amount=Decimal("100.00")), "GBP", test_date),  # Valid
        ]

        print_info("Testing 3 conversions: 2 valid, 1 failing (no rate for 1900)")

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
    """Test convert_bulk when all conversions fail.

    Note: Currency validates codes at creation, so we use valid but unusual
    currency codes that won't have rates in our test DB.
    """
    print_section("Test 11: Bulk Conversion - All Failures")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Use a very old date where no rates exist
        very_old_date = date(1900, 1, 1)

        # All conversions will fail because no rates exist for this date
        # New signature: (Currency, to_currency, date)
        conversions = [
            (Currency(code="EUR", amount=Decimal("100.00")), "USD", very_old_date),
            (Currency(code="USD", amount=Decimal("100.00")), "GBP", very_old_date),
            (Currency(code="GBP", amount=Decimal("100.00")), "CHF", very_old_date),
        ]

        print_info("Testing 3 conversions: all will fail (no rates for date 1900-01-01)")

        # Call bulk with raise_on_error=False
        results, errors = await convert_bulk(session, conversions, raise_on_error=False)

        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        # All should be None
        none_count = sum(1 for r in results if r is None)
        assert none_count == 3, f"Expected 3 None results, got {none_count}"

        assert len(errors) == 3, f"Expected 3 errors, got {len(errors)}"

        print_success("✓ All results None (as expected)")
        print_success(f"✓ All errors captured: {len(errors)}")


@pytest.mark.asyncio
async def test_bulk_raise_on_error():
    """Test convert_bulk with raise_on_error=True (should stop on first error).

    Note: Currency validates codes at creation, so we test failure by using
    a date where no rates exist.
    """
    print_section("Test 12: Bulk Conversion - Raise on Error")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_date = date.today()
        very_old_date = date(1900, 1, 1)  # No rates exist for this date

        # First valid, second fails due to missing rate
        # New signature: (Currency, to_currency, date)
        conversions = [
            (Currency(code="EUR", amount=Decimal("100.00")), "USD", test_date),  # Valid
            (
                Currency(code="EUR", amount=Decimal("100.00")),
                "USD",
                very_old_date,
            ),  # Fails - no rate
            (
                Currency(code="EUR", amount=Decimal("100.00")),
                "GBP",
                test_date,
            ),  # Valid but should not be reached
        ]

        print_info("Testing raise_on_error=True with failing second item (no rate for 1900)")

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


# ============================================================================
# X-R38 (the FX side of W-B58): a stored rate no column can keep reads as missing
# ============================================================================
#
# Measured before the cure: convert_bulk multiplies or divides by the stored rate as it reads it. A legacy 0 converts
# GNF → IRR to 0, and IRR → GNF raises DivisionByZero ("Conversion 0 failed: …"); a legacy inf converts GNF → IRR to an
# infinite amount, which Currency refuses ("Conversion 0 failed: … finite number"), and IRR → GNF to 0; a legacy rate of
# 20 digits before the decimal point converts to absurd amounts. compute_chain_rate divides by a leg of 0
# (DivisionByZero) and multiplies through an infinite one.
#
# Contract (X-R38): reads never raise. A stored rate storable_fx_rate refuses is a missing rate for its date, with the
# missing-rate behaviour that exists: backward-filled from the latest usable rate before it, else "No FX rate found for
# GNF/IRR on or before <date>" (a RateNotFoundError with raise_on_error, a None and that error without). Never a
# division by zero, never an infinite amount. compute_chain_rate answers None for a date whose leg is unusable.
#
# GNF/IRR is this block's own: no seed and no other test uses the pair. The rates are planted with raw SQL, past the
# model, in the test's session and never committed: the session rolls them back.

XR38_EARLIER = date(1987, 6, 8)
XR38_DAY = date(1987, 6, 10)
XR38_LATER = date(1987, 6, 11)
_XR38_UNUSABLE = [
    pytest.param(float("inf"), id="inf"),
    pytest.param(0.0, id="0"),
    pytest.param(1e19, id="1e19-20-integer-digits"),
]
_XR38_DIRECTIONS = [
    pytest.param("GNF", "IRR", id="direct-multiplies"),
    pytest.param("IRR", "GNF", id="inverse-divides"),
]


async def _xr38_plant(session, day: date, rate: float) -> None:
    """A GNF/IRR rate written with raw SQL, past the model, in ``session`` and not committed: what an older release could leave."""
    await session.execute(text("INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES (:day, 'GNF', 'IRR', :rate, 'X-R38', CURRENT_TIMESTAMP)"), {"day": day.isoformat(), "rate": rate})


async def _xr38_check_the_pair_is_free(session) -> None:
    """Precondition, checked not assumed: no committed GNF/IRR rate on or before the last date of this block, which a
    backward fill could reach."""
    leftover = (await session.execute(select(FxRate.date).where(FxRate.base == "GNF", FxRate.quote == "IRR", FxRate.date <= XR38_LATER))).scalars().all()
    if leftover:
        pytest.fail(f"Precondition failed: X-R38 needs GNF/IRR without rates on or before {XR38_LATER}, found {', '.join(str(day) for day in leftover)}")


async def _xr38_convert(session, conversions: list, raise_on_error: bool, story: str):
    """``convert_bulk``: ``((results, errors), None)``, or ``(None, the RateNotFoundError)``. Any other exception fails the
    test, naming it."""
    try:
        return await convert_bulk(session, conversions, raise_on_error=raise_on_error), None
    except RateNotFoundError as missing:
        return None, missing
    except Exception as exc:  # noqa: BLE001 — any other exception is the defect under test
        pytest.fail(f"{story}: convert_bulk raised {exc!r} (X-R38: reads never raise)")


def _xr38_missing() -> re.Pattern:
    """The missing-rate error of GNF/IRR on ``XR38_DAY`` as convert_bulk words it (``POST /fx/currencies/convert``
    compresses its errors by that wording)."""
    return re.compile(rf"No FX rate found for GNF/IRR on or before {XR38_DAY.isoformat()}\. ")


@pytest.mark.asyncio
@pytest.mark.parametrize(("from_code", "to_code"), _XR38_DIRECTIONS)
@pytest.mark.parametrize("planted", _XR38_UNUSABLE)
async def test_xr38_a_stored_rate_no_column_can_keep_raises_the_missing_rate_error(planted, from_code, to_code):
    """Red today: 0 converts GNF → IRR to 0 and makes IRR → GNF raise ``DivisionByZero``; inf converts IRR → GNF to 0 and
    GNF → IRR to an infinite amount Currency refuses; 1e19 converts to absurd amounts. What raises is wrapped into a
    RateNotFoundError "Conversion 0 failed: …", never the missing-rate one.

    Contract (X-R38): with ``raise_on_error`` and no usable rate on or before the date, the RateNotFoundError of a missing
    rate, "No FX rate found for GNF/IRR on or before 1987-06-10".
    """
    story = f"converting 100 {from_code} to {to_code} on {XR38_DAY}, the only GNF/IRR rate a legacy {planted!r}"
    async with AsyncSession(get_async_engine()) as session:
        await _xr38_check_the_pair_is_free(session)
        try:
            await _xr38_plant(session, XR38_DAY, planted)
            converted, missing = await _xr38_convert(session, [(Currency(code=from_code, amount=Decimal("100")), to_code, XR38_DAY)], True, story)
        finally:
            await session.rollback()

    assert missing is not None, f"{story} converted as {converted}: expected the missing-rate RateNotFoundError (X-R38)"
    assert _xr38_missing().search(str(missing)), f"{story} raised {missing!r}: expected the missing-rate error, 'No FX rate found for GNF/IRR on or before {XR38_DAY}' (X-R38)"


@pytest.mark.asyncio
@pytest.mark.parametrize(("from_code", "to_code"), _XR38_DIRECTIONS)
@pytest.mark.parametrize("planted", _XR38_UNUSABLE)
async def test_xr38_a_stored_rate_no_column_can_keep_is_collected_as_a_missing_rate(planted, from_code, to_code):
    """Red today: as with ``raise_on_error``, an amount of 0 or an absurd one, or the error "Conversion 0 failed: …".

    Contract (X-R38): without ``raise_on_error``, None for the conversion and its missing-rate error, "Conversion 0: No FX
    rate found for GNF/IRR on or before 1987-06-10. …", the wording ``POST /fx/currencies/convert`` compresses.
    """
    story = f"converting 100 {from_code} to {to_code} on {XR38_DAY} without raise_on_error, the only GNF/IRR rate a legacy {planted!r}"
    async with AsyncSession(get_async_engine()) as session:
        await _xr38_check_the_pair_is_free(session)
        try:
            await _xr38_plant(session, XR38_DAY, planted)
            converted, missing = await _xr38_convert(session, [(Currency(code=from_code, amount=Decimal("100")), to_code, XR38_DAY)], False, story)
        finally:
            await session.rollback()

    assert missing is None, f"{story} raised {missing!r}: without raise_on_error nothing raises"
    results, errors = converted
    assert results == [None], f"{story} converted as {results}: expected None, a missing rate (X-R38)"
    assert len(errors) == 1 and errors[0].startswith("Conversion 0: ") and _xr38_missing().search(errors[0]), f"{story} reports {errors}: expected 'Conversion 0: No FX rate found for GNF/IRR on or before {XR38_DAY}. …' (X-R38)"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("from_code", "to_code", "on_the_day", "the_day_after"),
    [
        pytest.param("GNF", "IRR", "250", "400", id="direct-multiplies"),
        pytest.param("IRR", "GNF", "40", "25", id="inverse-divides"),
    ],
)
@pytest.mark.parametrize("planted", _XR38_UNUSABLE)
async def test_xr38_a_stored_rate_no_column_can_keep_is_backward_filled_over(planted, from_code, to_code, on_the_day, the_day_after):
    """Red today: the legacy rate of 1987-06-10 is used as it is (an amount of 0, an absurd one, or a refusal) instead of
    the usable rate of two days before.

    Contract (X-R38): a missing rate for its date, with the missing-rate behaviour that exists: 1987-06-10 is
    backward-filled from the usable 2.5 of 1987-06-08 (``backward_fill_applied``), as a date without a row would be, and
    1987-06-11 keeps its own 4. Derived from "treat it as a missing rate for that date": the backward fill must see past
    the unusable row, which today also anchors the window convert_bulk loads.
    """
    story = f"converting 100 {from_code} to {to_code} on {XR38_DAY} and {XR38_LATER}, GNF/IRR 2.5 on {XR38_EARLIER}, a legacy {planted!r} on {XR38_DAY}, 4 on {XR38_LATER}"
    amount = Currency(code=from_code, amount=Decimal("100"))
    async with AsyncSession(get_async_engine()) as session:
        await _xr38_check_the_pair_is_free(session)
        try:
            await _xr38_plant(session, XR38_EARLIER, 2.5)
            await _xr38_plant(session, XR38_DAY, planted)
            await _xr38_plant(session, XR38_LATER, 4.0)
            converted, missing = await _xr38_convert(session, [(amount, to_code, XR38_DAY), (amount, to_code, XR38_LATER)], True, story)
        finally:
            await session.rollback()

    assert missing is None, f"{story} raised {missing!r}: expected {on_the_day} {to_code} on {XR38_DAY}, backward-filled from the rate of {XR38_EARLIER} (X-R38)"
    results, _errors = converted
    found = [(item[0].code, item[0].amount, item[1], item[2]) for item in results]
    expected = [(to_code, Decimal(on_the_day), XR38_EARLIER, True), (to_code, Decimal(the_day_after), XR38_LATER, False)]
    assert found == expected, f"{story} converted as {found}: expected {expected}, the legacy rate missing for its date (X-R38)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])


# ============================================================================
# COMPUTE CHAIN RATE TESTS (C13b — pure function, no DB)
# ============================================================================


class TestComputeChainRate:
    """Tests for compute_chain_rate() — pure computation, no DB needed."""

    def test_single_step_direct(self):
        """Single step GBP→EUR (direct order: GBP < EUR alphabetically is False, EUR < GBP is True)."""
        # EUR < GBP alphabetically, so norm is (EUR, GBP)
        # Step from=EUR to=GBP: EUR < GBP → direct → multiply by rate
        steps = [{"from": "EUR", "to": "GBP"}]
        leg_rates = {("EUR", "GBP", date(2025, 1, 1)): Decimal("0.84")}
        result = compute_chain_rate(steps, leg_rates, date(2025, 1, 1))
        assert result == Decimal("0.84")

    def test_single_step_inverse(self):
        """Single step GBP→EUR (inverse order: GBP > EUR alphabetically)."""
        # Stored as (EUR, GBP). Step from=GBP to=EUR: GBP > EUR → inverse → 1/rate
        steps = [{"from": "GBP", "to": "EUR"}]
        leg_rates = {("EUR", "GBP", date(2025, 1, 1)): Decimal("0.84")}
        result = compute_chain_rate(steps, leg_rates, date(2025, 1, 1))
        expected = Decimal("1") / Decimal("0.84")
        assert abs(result - expected) < Decimal("0.0001")

    def test_two_step_chain(self):
        """Two-step chain: GBP→EUR→USD = (1/EUR_GBP) * EUR_USD."""
        steps = [
            {"from": "GBP", "to": "EUR"},  # inverse: 1/0.84
            {"from": "EUR", "to": "USD"},  # direct: 1.07
        ]
        d = date(2025, 1, 1)
        leg_rates = {
            ("EUR", "GBP", d): Decimal("0.84"),
            ("EUR", "USD", d): Decimal("1.07"),
        }
        result = compute_chain_rate(steps, leg_rates, d)
        expected = (Decimal("1") / Decimal("0.84")) * Decimal("1.07")
        assert abs(result - expected) < Decimal("0.0001")

    def test_missing_leg_returns_none(self):
        """If any leg is missing for the target date, returns None."""
        steps = [
            {"from": "EUR", "to": "GBP"},
            {"from": "GBP", "to": "USD"},
        ]
        # Only one leg present
        leg_rates = {("EUR", "GBP", date(2025, 1, 1)): Decimal("0.84")}
        result = compute_chain_rate(steps, leg_rates, date(2025, 1, 1))
        assert result is None

    def test_wrong_date_returns_none(self):
        """Rates exist for a different date → returns None (strict date matching)."""
        steps = [{"from": "EUR", "to": "USD"}]
        leg_rates = {("EUR", "USD", date(2025, 1, 1)): Decimal("1.07")}
        result = compute_chain_rate(steps, leg_rates, date(2025, 1, 2))
        assert result is None

    def test_empty_steps(self):
        """Empty steps list → composite rate = 1 (identity)."""
        result = compute_chain_rate([], {}, date(2025, 1, 1))
        assert result == Decimal("1")

    @pytest.mark.parametrize("position", [pytest.param("EUR-GBP", id="inverse-leg"), pytest.param("EUR-USD", id="direct-leg")])
    @pytest.mark.parametrize(
        "unusable",
        [
            pytest.param(Decimal("0"), id="0"),
            pytest.param(Decimal("Infinity"), id="Infinity"),
            pytest.param(Decimal("1E+19"), id="20-integer-digits"),
            pytest.param(Decimal("NaN"), id="derived-NaN"),
        ],
    )
    def test_xr38_a_date_whose_leg_is_unusable_gives_none(self, unusable, position):
        """Red today: a leg of 0 in inverse order raises ``DivisionByZero`` (the sync of the pair fails), in direct order
        gives 0; an infinite leg gives 0 or Infinity; a leg of 20 digits before the decimal point an absurd rate; NaN, NaN.

        Contract (X-R38): None for the date whose leg is unusable (no column can keep it), as for a date whose leg is
        missing; the other date, whose legs are usable, computes as before.
        """
        steps = [{"from": "GBP", "to": "EUR"}, {"from": "EUR", "to": "USD"}]
        bad, good = date(2025, 1, 1), date(2025, 1, 2)
        leg_rates = {
            ("EUR", "GBP", bad): unusable if position == "EUR-GBP" else Decimal("0.84"),
            ("EUR", "USD", bad): unusable if position == "EUR-USD" else Decimal("1.07"),
            ("EUR", "GBP", good): Decimal("0.84"),
            ("EUR", "USD", good): Decimal("1.07"),
        }
        try:
            found = compute_chain_rate(steps, leg_rates, bad)
        except Exception as exc:  # noqa: BLE001 — any exception is the defect under test
            pytest.fail(f"compute_chain_rate with the {position} leg at {unusable!r} raised {exc!r}: the sync of the pair fails (X-R38: None for that date)")

        assert found is None, f"compute_chain_rate with the {position} leg at {unusable!r} = {found!r}: expected None, a date without a usable leg (X-R38)"
        other = compute_chain_rate(steps, leg_rates, good)
        expected = (Decimal("1") / Decimal("0.84")) * Decimal("1.07")
        assert other is not None and abs(other - expected) < Decimal("0.0001"), f"the other date, whose legs are usable, computes {other!r}: expected {expected}"
