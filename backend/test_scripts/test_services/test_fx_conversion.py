"""
Test 3: FX Conversion Logic
Tests currency conversion using rates from the database.
Verifies direct, inverse, cross-currency, and forward-fill conversions.
"""
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


def test_identity_conversion():
    """Test identity conversion (same currency)."""
    print_section("Test 1: Identity Conversion (Same Currency)")

    engine = get_engine()

    with Session(engine) as session:
        test_amount = Decimal("100.00")
        test_date = date.today()

        # Test EUR → EUR
        result_eur = convert(session, test_amount, "EUR", "EUR", test_date)
        if result_eur != test_amount:
            print_error(f"EUR → EUR: expected {test_amount}, got {result_eur}")
            return False
        print_success(f"EUR → EUR: {test_amount} = {result_eur} ✓")

        # Test USD → USD
        result_usd = convert(session, test_amount, "USD", "USD", test_date)
        if result_usd != test_amount:
            print_error(f"USD → USD: expected {test_amount}, got {result_usd}")
            return False
        print_success(f"USD → USD: {test_amount} = {result_usd} ✓")

        return True


def test_direct_conversion():
    """Test direct conversion using stored rate (EUR → USD)."""
    print_section("Test 2: Direct Conversion (EUR → USD)")

    engine = get_engine()

    with Session(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.desc()).limit(1)

        rate_record = session.exec(stmt).first()

        if not rate_record:
            print_error("No EUR/USD rate found in DB. Run persistence tests first.")
            return False

        print_info(f"Using rate from {rate_record.date}")
        print_info(f"EUR/USD = {rate_record.rate} (1 EUR = {rate_record.rate} USD)")

        # Convert 100 EUR to USD
        amount_eur = Decimal("100.00")
        result_usd = convert(session, amount_eur, "EUR", "USD", rate_record.date)
        expected_usd = amount_eur * rate_record.rate

        print_info(f"Conversion: {amount_eur} EUR → {result_usd} USD")
        print_info(f"Expected: {expected_usd} USD")

        if abs(result_usd - expected_usd) > Decimal("0.01"):
            print_error("Conversion result doesn't match expected value")
            return False

        print_success("Direct conversion (EUR → USD) correct")
        return True


def test_inverse_conversion():
    """Test inverse conversion (USD → EUR) using stored rate."""
    print_section("Test 3: Inverse Conversion (USD → EUR)")

    engine = get_engine()

    with Session(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.desc()).limit(1)

        rate_record = session.exec(stmt).first()

        if not rate_record:
            print_error("No EUR/USD rate found in DB. Run persistence tests first.")
            return False

        print_info(f"Using rate from {rate_record.date}")
        print_info(f"EUR/USD = {rate_record.rate} (1 EUR = {rate_record.rate} USD)")
        print_info(f"Therefore: 1 USD = {Decimal('1') / rate_record.rate} EUR")

        # Convert 100 USD to EUR (inverse operation)
        amount_usd = Decimal("100.00")
        result_eur = convert(session, amount_usd, "USD", "EUR", rate_record.date)
        expected_eur = amount_usd / rate_record.rate

        print_info(f"Conversion: {amount_usd} USD → {result_eur} EUR")
        print_info(f"Expected: {expected_eur} EUR")

        if abs(result_eur - expected_eur) > Decimal("0.01"):
            print_error("Inverse conversion result doesn't match expected value")
            return False

        print_success("Inverse conversion (USD → EUR) correct")
        return True


def test_roundtrip_conversion():
    """Test roundtrip conversion (EUR → USD → EUR) to verify rate inversion."""
    print_section("Test 4: Roundtrip Conversion (EUR → USD → EUR)")

    engine = get_engine()

    with Session(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.desc()).limit(1)

        rate_record = session.exec(stmt).first()

        if not rate_record:
            print_error("No EUR/USD rate found in DB. Run persistence tests first.")
            return False

        print_info(f"Using rate from {rate_record.date}: EUR/USD = {rate_record.rate}")

        # Roundtrip: EUR → USD → EUR
        original_amount = Decimal("100.00")

        # Step 1: EUR → USD
        usd_amount = convert(session, original_amount, "EUR", "USD", rate_record.date)
        print_info(f"Step 1: {original_amount} EUR → {usd_amount} USD")

        # Step 2: USD → EUR
        final_amount = convert(session, usd_amount, "USD", "EUR", rate_record.date)
        print_info(f"Step 2: {usd_amount} USD → {final_amount} EUR")

        # Should get back original amount (within rounding error)
        difference = abs(final_amount - original_amount)
        print_info(f"Difference: {difference} EUR")

        if difference > Decimal("0.01"):
            print_error(f"Roundtrip failed: started with {original_amount}, ended with {final_amount}")
            return False

        print_success("Roundtrip conversion successful (rate inversion works correctly)")
        return True


def test_cross_currency_conversion():
    """Test cross-currency conversion (USD → GBP via EUR)."""
    print_section("Test 5: Cross-Currency Conversion (USD → GBP)")

    engine = get_engine()

    with Session(engine) as session:
        # Find EUR/USD and EUR/GBP rates
        usd_stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.desc()).limit(1)

        gbp_stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "GBP"
            ).order_by(FxRate.date.desc()).limit(1)

        usd_rate = session.exec(usd_stmt).first()
        gbp_rate = session.exec(gbp_stmt).first()

        if not usd_rate or not gbp_rate:
            print_error("Missing EUR/USD or EUR/GBP rates. Run persistence tests first.")
            return False

        # Use the more recent date
        use_date = min(usd_rate.date, gbp_rate.date)

        print_info(f"Using rates from {use_date}")
        print_info(f"  EUR/USD: {usd_rate.rate} (1 EUR = {usd_rate.rate} USD)")
        print_info(f"  EUR/GBP: {gbp_rate.rate} (1 EUR = {gbp_rate.rate} GBP)")

        # Convert 100 USD to GBP
        amount_usd = Decimal("100.00")
        result_gbp = convert(session, amount_usd, "USD", "GBP", use_date)

        # Manual calculation: USD → EUR → GBP
        eur_amount = amount_usd / usd_rate.rate
        expected_gbp = eur_amount * gbp_rate.rate

        print_info(f"\nManual calculation:")
        print_info(f"  {amount_usd} USD ÷ {usd_rate.rate} = {eur_amount} EUR")
        print_info(f"  {eur_amount} EUR × {gbp_rate.rate} = {expected_gbp} GBP")

        print_info(f"\nActual conversion: {amount_usd} USD → {result_gbp} GBP")

        if abs(result_gbp - expected_gbp) > Decimal("0.01"):
            print_error(f"Cross-currency conversion failed: expected {expected_gbp}, got {result_gbp}")
            return False

        print_success("Cross-currency conversion (USD → GBP via EUR) correct")
        return True


def test_forward_fill():
    """Test forward-fill logic (use most recent rate when exact date not available)."""
    print_section("Test 6: Forward-Fill Logic")

    engine = get_engine()

    with Session(engine) as session:
        # Find a recent EUR/USD rate
        stmt = select(FxRate).where(
            FxRate.base == "EUR",
            FxRate.quote == "USD"
            ).order_by(FxRate.date.desc()).limit(1)

        rate_record = session.exec(stmt).first()

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
        result = convert(session, amount, "EUR", "USD", future_date)
        expected = amount * rate_record.rate

        print_info(f"Conversion: {amount} EUR → {result} USD")
        print_info(f"Expected (using rate from {rate_record.date}): {expected} USD")

        if abs(result - expected) > Decimal("0.01"):
            print_error("Forward-fill conversion failed")
            return False

        print_success("Forward-fill logic works correctly")
        print_info("Check logs above for forward-fill warning message")
        return True


def test_missing_rate_error():
    """Test that RateNotFoundError is raised when no rate exists."""
    print_section("Test 7: Missing Rate Error Handling")

    engine = get_engine()

    with Session(engine) as session:
        # Use a very old date (no rate should exist)
        old_date = date(2000, 1, 1)
        amount = Decimal("100.00")

        print_info(f"Attempting conversion for very old date: {old_date}")
        print_info("Expected behavior: RateNotFoundError")

        try:
            result = convert(session, amount, "USD", "EUR", old_date)
            print_error(f"Expected RateNotFoundError but got result: {result}")
            return False
        except RateNotFoundError as e:
            print_success(f"Correctly raised RateNotFoundError")
            print_info(f"Error message: {e}")
            return True
        except Exception as e:
            print_error(f"Unexpected error type: {type(e).__name__}: {e}")
            return False


def run_all_tests():
    """Run all FX conversion tests."""
    print_test_header(
        "LibreFolio - FX Service: Conversion Logic Tests",
        description="""These tests verify:
  • Identity conversion (same currency)
  • Direct conversion (stored rate)
  • Inverse conversion (1/rate)
  • Roundtrip conversion (verify precision)
  • Cross-currency conversion (via EUR)
  • Forward-fill logic (missing dates)
  • Error handling (missing rates)""",
        prerequisites=[
            "FX rates in database (run: python test_runner.py db fx-rates)",
            "Test database configured with recent rates"
            ]
        )

    # Ensure database exists
    print_info("Initializing test database...")
    ensure_database_exists()

    results = {
        "Identity Conversion": test_identity_conversion(),
        "Direct Conversion (EUR→USD)": test_direct_conversion(),
        "Inverse Conversion (USD→EUR)": test_inverse_conversion(),
        "Roundtrip Conversion": test_roundtrip_conversion(),
        "Cross-Currency Conversion": test_cross_currency_conversion(),
        "Forward-Fill Logic": test_forward_fill(),
        "Missing Rate Error": test_missing_rate_error(),
        }

    # Summary
    success = print_test_summary(results, "FX Conversion Logic Tests")
    return success


if __name__ == "__main__":
    success = run_all_tests()
    exit_with_result(success)
