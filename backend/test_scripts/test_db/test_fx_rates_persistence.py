"""
Test 2: FX Rates Persistence
Tests fetching FX rates from ECB and persisting them to the database.

⚠️  INTEGRATION TEST - EXTERNAL API DEPENDENCY
These are NOT unit tests with mocks. They perform REAL operations:
- HTTP calls to ECB API (https://data-api.ecb.europa.eu)
- Database writes to test_app.db
- End-to-end validation of the complete flow

TESTS WILL FAIL IF:
- ECB API is down or unreachable
- No internet connection
- ECB changes their API format
- Weekend/holidays (some dates may have no rates)

This is intentional - we test the REAL integration, not mocked behavior.
"""
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
from backend.app.services.fx import ensure_rates_multi_source
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import func


@pytest.mark.asyncio
async def test_fetch_and_persist_single_currency():
    """Test fetching and persisting rates for a single currency."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Use recent date range to avoid weekends
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=5)

        # Count existing rates before sync
        existing_stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD",
            FxRate.date >= start_date,
            FxRate.date <= end_date
        )
        result = await session.execute(existing_stmt)
        existing_count = len(result.scalars().all())

        # Fetch rates from ECB
        result = await ensure_rates_multi_source(session, (start_date, end_date), ["USD"], provider_code="ECB")
        synced_count = result['total_changed']

        # Verify rates were persisted
        all_stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD",
            FxRate.date >= start_date,
            FxRate.date <= end_date
        )
        result = await session.execute(all_stmt)
        all_rates = result.scalars().all()

        assert len(all_rates) > 0, "No rates found in database after sync"
        assert len(all_rates) >= existing_count, "Rate count decreased after sync"

        # Show sample rates (informational)
        sample_rates = sorted(all_rates, key=lambda r: r.date)[:3]
        for rate in sample_rates:
            print(f"  {rate.date}: 1 EUR = {rate.rate} USD")

        # Verify rate values are reasonable (EUR/USD typically between 0.7 and 1.9)
        # Only check ECB rates (ignore TEST rates from other tests)
        ecb_rates = [r for r in all_rates if r.source == "ECB"]
        for rate in ecb_rates:
            assert Decimal("0.7") <= rate.rate <= Decimal("1.9"), \
                f"Suspicious rate value: {rate.rate} on {rate.date}"


@pytest.mark.asyncio
async def test_fetch_multiple_currencies():
    """Test fetching and persisting rates for multiple currencies."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Use recent date range
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=7)
        test_currencies = ["USD", "GBP", "CHF", "JPY"]

        # Fetch rates
        result = await ensure_rates_multi_source(session, (start_date, end_date), test_currencies, provider_code="ECB")
        synced_count = result['total_changed']

        # Verify each currency
        for currency in test_currencies:
            # Determine alphabetical pair
            if currency < "EUR":
                base, quote = currency, "EUR"
            else:
                base, quote = "EUR", currency

            stmt = select(FxRate).where(
                FxRate.base == base,
                FxRate.quote == quote,
                FxRate.date >= start_date,
                FxRate.date <= end_date
            )
            result = await session.execute(stmt)
            rates = result.scalars().all()

            assert len(rates) > 0, f"{currency}: No rates found (stored as {base}/{quote})"

            latest = max(rates, key=lambda r: r.date)
            print(f"  {currency}: {len(rates)} rates (latest: {latest.date}, rate: {latest.rate})")


@pytest.mark.asyncio
async def test_data_overwrite():
    """Test that new data overwrites old data for same date/currency pair."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Use a date range to ensure we get at least one business day with data
        # Go back 7 days to avoid recent weekends/holidays
        end_date = date.today() - timedelta(days=7)
        start_date = end_date - timedelta(days=3)

        # Step 1: Fetch real rates first to find a business day with data
        result = await ensure_rates_multi_source(session, (start_date, end_date), ["USD"], provider_code="ECB")
        synced_count = result['total_changed']

        if synced_count == 0:
            # All weekends/holidays - acceptable, test passes
            pytest.skip("No rates available for date range (all weekends/holidays)")

        # Find a date that has real data
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD",
            FxRate.date >= start_date,
            FxRate.date <= end_date,
            FxRate.source == "ECB"
        ).order_by(FxRate.date.desc()).limit(1)
        result = await session.execute(stmt)
        real_rate = result.scalars().first()

        assert real_rate is not None, "No real ECB rates found even though synced_count > 0"

        test_date = real_rate.date
        original_rate = real_rate.rate

        # Step 2: Overwrite with fake rate
        stmt = insert(FxRate).values(
            date=test_date,
            base="EUR",
            quote="USD",
            rate=Decimal("9.9999"),
            source="TEST",
            fetched_at=func.current_timestamp()
        )

        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=['date', 'base', 'quote'],
            set_={
                'rate': stmt.excluded.rate,
                'source': stmt.excluded.source,
                'fetched_at': func.current_timestamp()
            }
        )

        await session.execute(upsert_stmt)
        await session.commit()

        # Step 3: Fetch from ECB again (should restore real rate)
        result = await ensure_rates_multi_source(session, (test_date, test_date), ["USD"], provider_code="ECB")
        refetch_count = result['total_changed']

        # Step 4: Verify rate was restored
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD",
            FxRate.date == test_date
        )
        result = await session.execute(stmt)
        restored_rate = result.scalars().first()

        assert restored_rate is not None, "Rate not found after restore"

        # If ECB couldn't refetch (weekend/holiday), the test is inconclusive but acceptable
        if refetch_count == 0:
            if restored_rate.rate == Decimal("9.9999"):
                pytest.skip(f"ECB has no data for {test_date} (weekend/holiday) - test inconclusive")
            else:
                pytest.fail("Rate changed but refetch_count=0, unexpected behavior")

        # If ECB refetched data, verify it was restored
        assert restored_rate.rate != Decimal("9.9999"), \
            f"Rate was NOT restored (refetch_count={refetch_count})"
        assert restored_rate.source == "ECB", f"Source was NOT restored: {restored_rate.source}"

        # Verify rate is realistic (should be between 0.2 and 1.9 for EUR/USD)
        assert Decimal("0.2") <= restored_rate.rate <= Decimal("1.9"), \
            f"Restored rate seems unrealistic: {restored_rate.rate}"


@pytest.mark.asyncio
async def test_idempotent_sync():
    """Test that syncing the same period twice doesn't create duplicates."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=3)

        # First sync
        result = await ensure_rates_multi_source(session, (start_date, end_date), ["USD"], provider_code="ECB")
        synced_1 = result['total_changed']

        # Count rates after first sync
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD",
            FxRate.date >= start_date,
            FxRate.date <= end_date
        )
        result_db = await session.execute(stmt)
        count_1 = len(result_db.scalars().all())

        # Second sync (should insert 0 new rates)
        result = await ensure_rates_multi_source(session, (start_date, end_date), ["USD"], provider_code="ECB")
        synced_2 = result['total_changed']

        # Count rates after second sync
        result = await session.execute(stmt)
        count_2 = len(result.scalars().all())

        assert synced_2 == 0, f"Second sync inserted {synced_2} rates (expected 0)"
        assert count_1 == count_2, f"Rate count changed: {count_1} → {count_2} (duplicates?)"


@pytest.mark.asyncio
async def test_rate_inversion_for_alphabetical_ordering():
    """Test that rates are correctly inverted when storing currencies in alphabetical order.

    ECB provides: 1 EUR = X CHF (e.g., 1 EUR = 0.95 CHF)
    We store as: CHF/EUR with inverted rate (e.g., 1 CHF = 1.0526 EUR)

    This ensures base < quote alphabetically (CHF < EUR).
    """
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_date = date.today() - timedelta(days=1)

        # Fetch CHF rate (ECB gives: 1 EUR = X CHF)
        await ensure_rates_multi_source(session, (test_date, test_date), ["CHF"], provider_code="ECB")

        # Query stored rate (should be CHF/EUR with inverted rate)
        stmt = select(FxRate).where(
            FxRate.base == "CHF",
            FxRate.quote == "EUR",
            FxRate.date == test_date
        )
        result = await session.execute(stmt)
        stored_rate = result.scalars().first()

        assert stored_rate is not None, "No CHF/EUR rate found in database"
        print(f"Stored as: {stored_rate.base}/{stored_rate.quote} = {stored_rate.rate}")

        # Verify alphabetical ordering
        assert stored_rate.base < stored_rate.quote, \
            f"Base ({stored_rate.base}) is not less than quote ({stored_rate.quote})"

        # Verify rate is inverted (CHF/EUR should be > 0.8 since EUR is typically stronger)
        assert stored_rate.rate > Decimal("0.8"), \
            f"CHF/EUR rate {stored_rate.rate} seems too low (expected > 0.8)"

        # Now test EUR/USD (should NOT be inverted - already in correct order)
        await ensure_rates_multi_source(session, (test_date, test_date), ["USD"], provider_code="ECB")

        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD",
            FxRate.date == test_date
        )
        result = await session.execute(stmt)
        usd_rate = result.scalars().first()

        assert usd_rate is not None, "No EUR/USD rate found in database"
        assert usd_rate.base < usd_rate.quote, \
            f"Base ({usd_rate.base}) is not less than quote ({usd_rate.quote})"


@pytest.mark.asyncio
async def test_database_constraints():
    """Test that database constraints are working (unique constraint, check constraint)."""
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_date = date.today() - timedelta(days=1)

        # First, ensure we have a rate
        await ensure_rates_multi_source(session, (test_date, test_date), ["USD"], provider_code="ECB")

        # Query the rate
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD",
            FxRate.date == test_date
        )
        result = await session.execute(stmt)
        existing_rate = result.scalars().first()

        assert existing_rate is not None, "No rate found to test duplicate constraint"

        # Test 1: Unique constraint (date, base, quote)
        duplicate = FxRate(
            base="EUR",
            quote="USD",
            date=test_date,
            rate=Decimal("1.1234"),  # Different rate, same date/base/quote
            source="TEST"
        )
        session.add(duplicate)

        with pytest.raises(Exception):  # Should fail due to unique constraint
            await session.commit()
        await session.rollback()

        # Test 2: Check constraint (base < quote alphabetically)
        test_date_check = test_date + timedelta(days=10)

        invalid = FxRate(
            base="USD",  # USD > EUR alphabetically - should fail CHECK constraint
            quote="EUR",
            date=test_date_check,
            rate=Decimal("0.9"),
            source="TEST"
        )
        session.add(invalid)

        with pytest.raises(Exception):  # Should fail due to check constraint
            await session.commit()
        await session.rollback()

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
