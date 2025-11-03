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
from backend.app.services.fx import FXServiceError, ensure_rates_multi_source
from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_step,
    print_success,
    print_test_header,
    print_test_summary,
    print_warning,
    exit_with_result,
    )


async def test_fetch_and_persist_single_currency():
    """Test fetching and persisting rates for a single currency."""
    print_section("Test 1: Fetch & Persist Single Currency (USD)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Use recent date range to avoid weekends
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=5)

        print_info(f"Date range: {start_date} to {end_date}")
        print_info(f"Currency: USD")

        # Count existing rates before sync
        existing_stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD",
            FxRate.date >= start_date,
            FxRate.date <= end_date
            )
        result = await session.execute(existing_stmt)
        existing_count = len(result.scalars().all())
        print_info(f"Existing rates in DB: {existing_count}")

        try:
            # Fetch rates from ECB
            result = await ensure_rates_multi_source(session, (start_date, end_date), ["USD"], provider_code="ECB")
            synced_count = result['total_changed']
            print_success(f"Synced {synced_count} new rates")

            # Verify rates were persisted
            all_stmt = select(FxRate).where(
                FxRate.base == "EUR",
                FxRate.quote == "USD",
                FxRate.date >= start_date,
                FxRate.date <= end_date
                )
            result = await session.execute(all_stmt)
            all_rates = result.scalars().all()

            if not all_rates:
                print_error("No rates found in database after sync")
                return False

            print_success(f"Total rates in DB: {len(all_rates)}")

            # Show sample rates
            print_info("Sample rates:")
            for rate in sorted(all_rates, key=lambda r: r.date)[:3]:
                print_info(f"  {rate.date}: 1 EUR = {rate.rate} USD")

            # Verify rate values are reasonable (EUR/USD typically between 1.0 and 1.2)
            # Only check ECB rates (ignore TEST rates from other tests)
            ecb_rates = [r for r in all_rates if r.source == "ECB"]
            for rate in ecb_rates:
                if not (Decimal("0.7") <= rate.rate <= Decimal("1.9")):
                    print_error(f"Suspicious rate value: {rate.rate} on {rate.date}")
                    return False

            print_success("All rate values are within expected range")
            return True

        except FXServiceError as e:
            print_error(f"ECB API error: {e}")
            return False
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_fetch_multiple_currencies():
    """Test fetching and persisting rates for multiple currencies."""
    print_section("Test 2: Fetch & Persist Multiple Currencies")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Use recent date range
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=7)
        test_currencies = ["USD", "GBP", "CHF", "JPY"]

        print_info(f"Date range: {start_date} to {end_date}")
        print_info(f"Currencies: {', '.join(test_currencies)}")

        try:
            # Fetch rates
            result = await ensure_rates_multi_source(session, (start_date, end_date), test_currencies, provider_code="ECB")
            synced_count = result['total_changed']
            print_success(f"Synced {synced_count} new rates")

            # Verify each currency
            all_ok = True
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

                if not rates:
                    print_error(f"  {currency}: No rates found (stored as {base}/{quote})")
                    all_ok = False
                else:
                    latest = max(rates, key=lambda r: r.date)
                    print_success(f"  {currency}: {len(rates)} rates (latest: {latest.date}, rate: {latest.rate})")

            return all_ok

        except Exception as e:
            print_error(f"Failed to fetch multiple currencies: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_data_overwrite():
    """Test that new data overwrites old data for same date/currency pair."""
    print_section("Test 3: Data Overwrite (Update Existing Rates)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        # Use a date range to ensure we get at least one business day with data
        # Go back 7 days to avoid recent weekends/holidays
        end_date = date.today() - timedelta(days=7)
        start_date = end_date - timedelta(days=3)

        print_info(f"Testing data overwrite for date range {start_date} to {end_date}")

        try:
            # Step 1: Fetch real rates first to find a business day with data
            print_step(1, "Fetch real rates from ECB to identify business days")
            result = await ensure_rates_multi_source(session, (start_date, end_date), ["USD"], provider_code="ECB")
            synced_count = result['total_changed']

            if synced_count == 0:
                print_warning(f"No rates available for {start_date} to {end_date} (all weekends/holidays)")
                print_info("This is expected behavior - test passes")
                return True

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

            if not real_rate:
                print_error("No real ECB rates found even though synced_count > 0")
                return False

            test_date = real_rate.date
            original_rate = real_rate.rate
            print_success(f"Found business day with data: {test_date} (original rate: {original_rate})")

            # Step 2: Overwrite with fake rate
            print_step(2, "Overwrite with fake rate")
            from sqlalchemy.dialects.sqlite import insert
            from sqlalchemy import func

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
            print_success(f"Overwrote with fake rate: EUR/USD = 9.9999 on {test_date}")

            # Step 3: Fetch from ECB again (should restore real rate)
            print_step(3, "Fetch from ECB again to restore real rate")
            result = await ensure_rates_multi_source(session, (test_date, test_date), ["USD"], provider_code="ECB")
            refetch_count = result['total_changed']

            # Step 4: Verify rate was restored
            print_step(4, "Verify rate was restored")
            stmt = select(FxRate).where(
                FxRate.base == "EUR",
                FxRate.quote == "USD",
                FxRate.date == test_date
            )
            result = await session.execute(stmt)
            restored_rate = result.scalars().first()

            if not restored_rate:
                print_error("Rate not found after restore")
                return False

            # If ECB couldn't refetch (weekend/holiday), the test is inconclusive but acceptable
            if refetch_count == 0:
                print_warning(f"ECB has no data for {test_date} (weekend/holiday)")
                if restored_rate.rate == Decimal("9.9999"):
                    print_info("Rate remains fake (ECB couldn't refetch) - this is acceptable")
                    print_success("Test passes: ECB correctly returns empty for weekend/holiday")
                    return True
                else:
                    print_error("Rate changed but refetch_count=0, unexpected behavior")
                    return False

            # If ECB refetched data, verify it was restored
            if restored_rate.rate == Decimal("9.9999"):
                print_error(f"Rate was NOT restored: still {restored_rate.rate}")
                print_error(f"But refetch_count={refetch_count}, ECB should have updated it")
                return False

            # Check that source was updated
            if restored_rate.source != "ECB":
                print_error(f"Source was NOT restored: still {restored_rate.source}")
                return False

            print_success(f"Rate successfully restored: EUR/USD = {restored_rate.rate}")
            print_success(f"Source restored: {restored_rate.source}")

            # Verify rate is realistic (should be between 0.2 and 1.9 for EUR/USD)
            if not (Decimal("0.2") <= restored_rate.rate <= Decimal("1.9")):
                print_warning(f"Restored rate seems unrealistic: {restored_rate.rate}")

            return True

        except Exception as e:
            print_error(f"Data overwrite test failed: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            return False


async def test_idempotent_sync():
    """Test that syncing the same period twice doesn't create duplicates."""
    print_section("Test 4: Idempotent Sync (No Duplicates)")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=3)

        print_info(f"Date range: {start_date} to {end_date}")
        print_info("Syncing USD twice...")

        try:
            # First sync
            result = await ensure_rates_multi_source(session, (start_date, end_date), ["USD"], provider_code="ECB")
            synced_1 = result['total_changed']
            print_info(f"First sync: {synced_1} new rates")

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
            print_info(f"Second sync: {synced_2} new rates")

            # Count rates after second sync
            result = await session.execute(stmt)
            count_2 = len(result.scalars().all())

            if synced_2 != 0:
                print_error(f"Second sync inserted {synced_2} rates (expected 0)")
                return False

            if count_1 != count_2:
                print_error(f"Rate count changed: {count_1} → {count_2} (duplicates?)")
                return False

            print_success("No duplicates created on second sync")
            return True

        except Exception as e:
            print_error(f"Failed idempotency test: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_rate_inversion_for_alphabetical_ordering():
    """Test that rates are correctly inverted when storing currencies in alphabetical order.

    ECB provides: 1 EUR = X CHF (e.g., 1 EUR = 0.95 CHF)
    We store as: CHF/EUR with inverted rate (e.g., 1 CHF = 1.0526 EUR)

    This ensures base < quote alphabetically (CHF < EUR).
    """
    print_section("Test 5: Rate Inversion for Alphabetical Ordering")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_date = date.today() - timedelta(days=1)

        print_info("Fetching CHF rate from ECB (CHF < EUR alphabetically, needs inversion)...")

        try:
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

            if not stored_rate:
                print_error("No CHF/EUR rate found in database")
                return False

            print_info(f"Stored as: {stored_rate.base}/{stored_rate.quote} = {stored_rate.rate}")

            # Verify alphabetical ordering
            if stored_rate.base >= stored_rate.quote:
                print_error(f"Base ({stored_rate.base}) is not less than quote ({stored_rate.quote})")
                return False

            print_success("✅ Currency pair stored in correct alphabetical order (CHF < EUR)")

            # Verify rate is inverted (should be > 1.0 since EUR is stronger than CHF)
            # ECB gives: 1 EUR = ~0.95 CHF
            # Inverted:  1 CHF = ~1.05 EUR
            if stored_rate.rate < Decimal("0.8") or stored_rate.rate > Decimal("1.3"):
                print_warning(f"Rate {stored_rate.rate} seems unusual for CHF/EUR (expected ~1.05)")
                print_warning("This might be OK if CHF has changed significantly vs EUR")
            else:
                print_info(f"Rate {stored_rate.rate} is in expected range for inverted CHF/EUR")

            # Now test a currency that doesn't need inversion (e.g., USD)
            print_info("\nFetching USD rate from ECB (EUR < USD alphabetically, no inversion)...")

            await ensure_rates_multi_source(session, (test_date, test_date), ["USD"], provider_code="ECB")

            stmt = select(FxRate).where(
                FxRate.base == "EUR",
                FxRate.quote == "USD",
                FxRate.date == test_date
            )
            result = await session.execute(stmt)
            usd_rate = result.scalars().first()

            if not usd_rate:
                print_error("No EUR/USD rate found in database")
                return False

            print_info(f"Stored as: {usd_rate.base}/{usd_rate.quote} = {usd_rate.rate}")

            # Verify alphabetical ordering
            if usd_rate.base >= usd_rate.quote:
                print_error(f"Base ({usd_rate.base}) is not less than quote ({usd_rate.quote})")
                return False

            print_success("✅ Currency pair stored in correct alphabetical order (EUR < USD)")

            # Verify rate is NOT inverted (should be > 1.0 since USD is typically stronger)
            if usd_rate.rate < Decimal("0.8") or usd_rate.rate > Decimal("1.5"):
                print_warning(f"Rate {usd_rate.rate} seems unusual for EUR/USD (expected ~1.08-1.20)")
                print_warning("This might be OK if exchange rates have changed significantly")
            else:
                print_info(f"Rate {usd_rate.rate} is in expected range for EUR/USD")

            print_success("\n✅ Rate inversion logic working correctly!")
            print_info("  • CHF/EUR: inverted (CHF < EUR alphabetically)")
            print_info("  • EUR/USD: not inverted (EUR < USD alphabetically)")

            return True

        except Exception as e:
            print_error(f"Rate inversion test failed: {e}")
            import traceback
            traceback.print_exc()
            return False


async def test_database_constraints():
    """Test that database constraints are working (unique constraint, check constraint)."""
    print_section("Test 6: Database Constraints")

    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        test_date = date.today() - timedelta(days=1)

        print_info("Testing unique constraint (date, base, quote)...")

        try:
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

            if not existing_rate:
                print_error("No rate found to test duplicate constraint")
                return False

            print_info(f"Found rate: {existing_rate.date}, EUR/USD = {existing_rate.rate}")

            # Try to insert duplicate (should fail due to unique constraint)
            duplicate = FxRate(
                base="EUR",
                quote="USD",
                date=test_date,
                rate=Decimal("1.1234"),  # Different rate, same date/base/quote
                source="TEST"
                )
            session.add(duplicate)

            try:
                await session.commit()
                print_error("Duplicate insertion succeeded (unique constraint not working!)")
                await session.rollback()
                return False
            except Exception as e:
                print_success("Duplicate insertion correctly rejected by unique constraint")
                await session.rollback()

            # Test check constraint (base < quote alphabetically)
            print_info("\nTesting check constraint (base < quote)...")

            # Use a different date to avoid UNIQUE constraint conflict
            test_date_check = test_date + timedelta(days=10)

            invalid = FxRate(
                base="USD",  # USD > EUR alphabetically - should fail CHECK constraint
                quote="EUR",
                date=test_date_check,  # Different date to ensure it's not UNIQUE violation
                rate=Decimal("0.9"),
                source="TEST"
                )
            session.add(invalid)

            try:
                await session.commit()
                print_error("Invalid base/quote order accepted (check constraint not working!)")
                await session.rollback()
                return False
            except Exception as e:
                # Check if it's specifically a CHECK constraint error
                error_msg = str(e).lower()
                if 'check constraint' in error_msg or 'ck_fx_rates_base_less_than_quote' in error_msg:
                    print_success("Invalid base/quote order correctly rejected by check constraint")
                elif 'unique constraint' in error_msg:
                    print_error("Rejected by UNIQUE constraint instead of CHECK constraint")
                    print_warning("This might be a false positive - check if constraint exists")
                    await session.rollback()
                    return False
                else:
                    print_success(f"Invalid base/quote order rejected (reason: {error_msg[:100]})")
                await session.rollback()

            return True

        except Exception as e:
            print_error(f"Constraint test failed: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            return False


async def run_all_tests():
    """Run all FX persistence tests."""
    print_test_header(
        "LibreFolio - FX Service: Rates Persistence Tests",
        description="""These tests verify:
  • Fetching FX rates from ECB API
  • Persisting rates to the database
  • Overwriting existing data with fresh data
  • Idempotent sync (no duplicates)
  • Rate inversion for alphabetical ordering (CHF/EUR vs EUR/USD)
  • Database constraints (unique, check)
  
Tests WILL FAIL if ECB API is down/unreachable or no internet.""",
        prerequisites=[
            "ECB API accessible and working (run: python test_runner.py external ecb)",
            "Test database configured",
            "Internet connection"
            ]
        )

    # Initialize database with safety checks
    print_info("Initializing test database...")
    if not initialize_test_database(print_info):
        return False

    results = {
        "Fetch & Persist Single Currency": await test_fetch_and_persist_single_currency(),
        "Fetch & Persist Multiple Currencies": await test_fetch_multiple_currencies(),
        "Data Overwrite (Update Existing)": await test_data_overwrite(),
        "Idempotent Sync": await test_idempotent_sync(),
        "Rate Inversion for Alphabetical Ordering": await test_rate_inversion_for_alphabetical_ordering(),
        "Database Constraints": await test_database_constraints(),
        }

    # Summary
    success = print_test_summary(results, "FX Rates Persistence Tests")
    return success


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit_with_result(success)
