"""
Test 2: FX Rates Persistence
Tests fetching FX rates from ECB and persisting them to the database.
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
from backend.test_scripts.test_db_config import setup_test_database
setup_test_database()

from sqlmodel import Session, select

from backend.app.db.models import FxRate
from backend.app.db.session import get_engine
from backend.app.main import ensure_database_exists
from backend.app.services.fx import FXServiceError, ensure_rates
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

    engine = get_engine()

    with Session(engine) as session:
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
        existing_count = len(session.exec(existing_stmt).all())
        print_info(f"Existing rates in DB: {existing_count}")

        try:
            # Fetch rates from ECB
            synced_count = await ensure_rates(session, (start_date, end_date), ["USD"])
            print_success(f"Synced {synced_count} new rates")

            # Verify rates were persisted
            all_stmt = select(FxRate).where(
                FxRate.base == "EUR",
                FxRate.quote == "USD",
                FxRate.date >= start_date,
                FxRate.date <= end_date
            )
            all_rates = session.exec(all_stmt).all()

            if not all_rates:
                print_error("No rates found in database after sync")
                return False

            print_success(f"Total rates in DB: {len(all_rates)}")

            # Show sample rates
            print_info("Sample rates:")
            for rate in sorted(all_rates, key=lambda r: r.date)[:3]:
                print_info(f"  {rate.date}: 1 EUR = {rate.rate} USD")

            # Verify rate values are reasonable (EUR/USD typically between 1.0 and 1.2)
            for rate in all_rates:
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

    engine = get_engine()

    with Session(engine) as session:
        # Use recent date range
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=7)
        test_currencies = ["USD", "GBP", "CHF", "JPY"]

        print_info(f"Date range: {start_date} to {end_date}")
        print_info(f"Currencies: {', '.join(test_currencies)}")

        try:
            # Fetch rates
            synced_count = await ensure_rates(session, (start_date, end_date), test_currencies)
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
                rates = session.exec(stmt).all()

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

    engine = get_engine()

    with Session(engine) as session:
        test_date = date.today() - timedelta(days=1)

        print_info(f"Testing data overwrite for {test_date}")

        try:
            # Step 1: Insert initial fake rate manually
            print_step(1, "Insert fake rate manually")
            fake_rate = FxRate(
                base="EUR",
                quote="USD",
                date=test_date,
                rate=Decimal("9.9999"),  # Obviously fake
                source="TEST"
            )
            session.add(fake_rate)
            session.commit()
            print_success(f"Inserted fake rate: EUR/USD = 9.9999 on {test_date}")

            # Step 2: Fetch real rate from ECB (should overwrite)
            print_step(2, "Fetch real rate from ECB")
            await ensure_rates(session, (test_date, test_date), ["USD"])

            # Step 3: Verify rate was updated
            print_step(3, "Verify rate was updated")
            stmt = select(FxRate).where(
                FxRate.base == "EUR",
                FxRate.quote == "USD",
                FxRate.date == test_date
            )
            updated_rate = session.exec(stmt).first()

            if not updated_rate:
                print_error("Rate not found after update")
                return False

            # Check that rate was updated (should NOT be fake value)
            if updated_rate.rate == Decimal("9.9999"):
                print_error(f"Rate was NOT updated: still {updated_rate.rate}")
                return False

            # Check that source was updated
            if updated_rate.source != "ECB":
                print_error(f"Source was NOT updated: still {updated_rate.source}")
                return False

            print_success(f"Rate successfully updated: EUR/USD = {updated_rate.rate}")
            print_success(f"Source updated: {updated_rate.source}")

            # Verify rate is realistic (should be between 0.9 and 1.3 for EUR/USD)
            if not (Decimal("0.9") <= updated_rate.rate <= Decimal("1.3")):
                print_warning(f"Updated rate seems unrealistic: {updated_rate.rate}")

            return True

        except Exception as e:
            print_error(f"Data overwrite test failed: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
            return False


async def test_idempotent_sync():
    """Test that syncing the same period twice doesn't create duplicates."""
    print_section("Test 4: Idempotent Sync (No Duplicates)")

    engine = get_engine()

    with Session(engine) as session:
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=3)

        print_info(f"Date range: {start_date} to {end_date}")
        print_info("Syncing USD twice...")

        try:
            # First sync
            synced_1 = await ensure_rates(session, (start_date, end_date), ["USD"])
            print_info(f"First sync: {synced_1} new rates")

            # Count rates after first sync
            stmt = select(FxRate).where(
                FxRate.base == "EUR",
                FxRate.quote == "USD",
                FxRate.date >= start_date,
                FxRate.date <= end_date
            )
            count_1 = len(session.exec(stmt).all())

            # Second sync (should insert 0 new rates)
            synced_2 = await ensure_rates(session, (start_date, end_date), ["USD"])
            print_info(f"Second sync: {synced_2} new rates")

            # Count rates after second sync
            count_2 = len(session.exec(stmt).all())

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


async def test_database_constraints():
    """Test that database constraints are working (unique constraint, check constraint)."""
    print_section("Test 5: Database Constraints")

    engine = get_engine()

    with Session(engine) as session:
        test_date = date.today() - timedelta(days=1)

        print_info("Testing unique constraint (date, base, quote)...")

        try:
            # First, ensure we have a rate
            await ensure_rates(session, (test_date, test_date), ["USD"])

            # Query the rate
            stmt = select(FxRate).where(
                FxRate.base == "EUR",
                FxRate.quote == "USD",
                FxRate.date == test_date
            )
            existing_rate = session.exec(stmt).first()

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
                session.commit()
                print_error("Duplicate insertion succeeded (unique constraint not working!)")
                session.rollback()
                return False
            except Exception as e:
                print_success("Duplicate insertion correctly rejected by unique constraint")
                session.rollback()

            # Test check constraint (base < quote alphabetically)
            print_info("\nTesting check constraint (base < quote)...")

            invalid = FxRate(
                base="USD",  # USD > EUR alphabetically - should fail
                quote="EUR",
                date=test_date,
                rate=Decimal("0.9"),
                source="TEST"
            )
            session.add(invalid)

            try:
                session.commit()
                print_error("Invalid base/quote order accepted (check constraint not working!)")
                session.rollback()
                return False
            except Exception as e:
                print_success("Invalid base/quote order correctly rejected by check constraint")
                session.rollback()

            return True

        except Exception as e:
            print_error(f"Constraint test failed: {e}")
            import traceback
            traceback.print_exc()
            session.rollback()
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
  • Database constraints (unique, check)""",
        prerequisites=[
            "ECB API accessible and working (run: python test_runner.py external ecb)",
            "Test database configured",
            "Internet connection"
        ]
    )

    # Ensure database exists
    print_info("Initializing test database...")
    ensure_database_exists()

    results = {
        "Fetch & Persist Single Currency": await test_fetch_and_persist_single_currency(),
        "Fetch & Persist Multiple Currencies": await test_fetch_multiple_currencies(),
        "Data Overwrite (Update Existing)": await test_data_overwrite(),
        "Idempotent Sync": await test_idempotent_sync(),
        "Database Constraints": await test_database_constraints(),
    }

    # Summary
    success = print_test_summary(results, "FX Rates Persistence Tests")
    return success


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit_with_result(success)

