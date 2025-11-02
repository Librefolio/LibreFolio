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

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database, initialize_test_database

setup_test_database()

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import FxRate
from backend.app.db.session import get_async_engine
from backend.app.services.fx import RateNotFoundError, convert
from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_success,
    print_test_header,
    print_test_summary,
    exit_with_result,
    )


async def setup_mock_fx_rates(session):
    """
    Insert mock FX rates for testing.
    Creates rates for multiple dates (today, yesterday, 7 days ago) to test date handling.
    Uses UPSERT so it's safe to run multiple times.
    """
    from sqlalchemy.dialects.sqlite import insert
    from sqlalchemy import func

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


async def test_identity_conversion():
    """Test identity conversion (same currency)."""
    print_section("Test 1: Identity Conversion (Same Currency)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_amount = Decimal("100.00")
        test_date = date.today()

        # Test EUR → EUR
        result_eur = await convert(session, test_amount, "EUR", "EUR", test_date)
        if result_eur != test_amount:
            print_error(f"EUR → EUR: expected {test_amount}, got {result_eur}")
            return False
        print_success(f"EUR → EUR: {test_amount} = {result_eur} ✓")

        # Test USD → USD
        result_usd = await convert(session, test_amount, "USD", "USD", test_date)
        if result_usd != test_amount:
            print_error(f"USD → USD: expected {test_amount}, got {result_usd}")
            return False
        print_success(f"USD → USD: {test_amount} = {result_usd} ✓")

        return True


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

        if not rate_record:
            print_error("No EUR/USD rate found in DB. Run persistence tests first.")
            return False

        print_info(f"Using rate from {rate_record.date}")
        print_info(f"EUR/USD = {rate_record.rate} (1 EUR = {rate_record.rate} USD)")

        # Convert 100 EUR to USD
        amount_eur = Decimal("100.00")
        result_usd = await convert(session, amount_eur, "EUR", "USD", rate_record.date)
        expected_usd = amount_eur * rate_record.rate

        print_info(f"Conversion: {amount_eur} EUR → {result_usd} USD")
        print_info(f"Expected: {expected_usd} USD")

        if abs(result_usd - expected_usd) > Decimal("0.01"):
            print_error("Conversion result doesn't match expected value")
            return False

        print_success("Direct conversion (EUR → USD) correct")
        return True


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

        if not rate_record:
            print_error("No EUR/USD rate found in DB. Run persistence tests first.")
            return False

        print_info(f"Using rate from {rate_record.date}")
        print_info(f"EUR/USD = {rate_record.rate} (1 EUR = {rate_record.rate} USD)")
        print_info(f"Therefore: 1 USD = {Decimal('1') / rate_record.rate} EUR")

        # Convert 100 USD to EUR (inverse operation)
        amount_usd = Decimal("100.00")
        result_eur = await convert(session, amount_usd, "USD", "EUR", rate_record.date)
        expected_eur = amount_usd / rate_record.rate

        print_info(f"Conversion: {amount_usd} USD → {result_eur} EUR")
        print_info(f"Expected: {expected_eur} EUR")

        if abs(result_eur - expected_eur) > Decimal("0.01"):
            print_error("Inverse conversion result doesn't match expected value")
            return False

        print_success("Inverse conversion (USD → EUR) correct")
        return True


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

        if not rate_record:
            print_error("No EUR/USD rate found in DB. Run persistence tests first.")
            return False

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

        if difference > Decimal("0.01"):
            print_error(f"Roundtrip failed: started with {original_amount}, ended with {final_amount}")
            return False

        print_success("Roundtrip conversion successful (rate inversion works correctly)")
        return True


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
        if result_today == result_yesterday == result_week_ago:
            print_error("All dates returned same rate - variation not working")
            return False

        print_info(f"Rate variation detected (rates differ across dates) ✓")
        return True


async def test_forward_fill():
    """Test forward-fill logic (use most recent rate when exact date not available)."""
    print_section("Test 6: Forward-Fill Logic")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.desc()).limit(1)

        result = await session.execute(stmt)
        rate_record = result.scalars().first()

        if not rate_record:
            print_error("No EUR/USD rate found in DB. Run persistence tests first.")
            return False

        print_info(f"Most recent rate in DB: {rate_record.date}")
        print_info(f"EUR/USD = {rate_record.rate}")

        # Request conversion for a future date (30 days ahead)
        future_date = date.today() + timedelta(days=30)
        print_info(f"\nRequesting conversion for future date: {future_date}")
        print_info("Expected behavior: use most recent available rate (forward-fill)")

        amount = Decimal("100.00")
        result = await convert(session, amount, "EUR", "USD", future_date)
        expected = amount * rate_record.rate

        print_info(f"Conversion: {amount} EUR → {result} USD")
        print_info(f"Expected (using rate from {rate_record.date}): {expected} USD")

        if abs(result - expected) > Decimal("0.01"):
            print_error("Forward-fill conversion failed")
            return False

        print_success("Forward-fill logic works correctly")
        print_info("Check logs above for forward-fill warning message")
        return True


async def test_missing_rate_error():
    """Test that RateNotFoundError is raised when no rate exists."""
    print_section("Test 7: Missing Rate Error Handling")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Use a very old date (no rate should exist)
        old_date = date(2000, 1, 1)
        amount = Decimal("100.00")

        print_info(f"Attempting conversion for very old date: {old_date}")
        print_info("Expected behavior: RateNotFoundError")

        try:
            result = await convert(session, amount, "USD", "EUR", old_date)
            print_error(f"Expected RateNotFoundError but got result: {result}")
            return False
        except RateNotFoundError as e:
            print_success(f"Correctly raised RateNotFoundError")
            print_info(f"Error message: {e}")
            return True
        except Exception as e:
            print_error(f"Unexpected error type: {type(e).__name__}: {e}")
            return False


async def run_all_tests():
    """Run all FX conversion tests."""
    print_test_header(
        "LibreFolio - FX Service: Conversion Logic Tests",
        description="""These tests verify:
  • Identity conversion (same currency)
  • Direct conversion (stored rate)
  • Inverse conversion (1/rate)
  • Roundtrip conversion (verify precision)
  • Forward-fill logic (missing dates)
  • Error handling (missing rates)
  
Note: Mock FX rates are automatically inserted for testing.""",
        prerequisites=[
            "Test database configured",
            "Mock FX rates will be inserted automatically"
            ]
        )

    # Initialize database with safety checks
    print_info("Initializing test database...")
    if not initialize_test_database(print_info):
        return False


    # Setup mock FX rates
    engine = get_async_engine()
    async with AsyncSession(engine) as session:
        await setup_mock_fx_rates(session)

    results = {
        "Identity Conversion": await test_identity_conversion(),
        "Direct Conversion (EUR→USD)": await test_direct_conversion(),
        "Inverse Conversion (USD→EUR)": await test_inverse_conversion(),
        "Roundtrip Conversion": await test_roundtrip_conversion(),
        "Different Dates": await test_different_dates(),
        "Forward-Fill Logic": await test_forward_fill(),
        "Missing Rate Error": await test_missing_rate_error(),
        }

    # Summary
    success = print_test_summary(results, "FX Conversion Logic Tests")
    return success


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit_with_result(success)
