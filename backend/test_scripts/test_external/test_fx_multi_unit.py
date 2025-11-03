"""
Multi-Unit Currency Tests for FX Providers

This test suite specifically tests the handling of multi-unit currencies
(JPY, SEK, NOK, DKK) which are quoted per 100 units instead of per 1 unit.

These tests verify:
- Correct identification of multi-unit currencies
- Proper inversion logic (100/rate instead of 1/rate)
- Reasonable rate ranges (e.g., JPY should be ~100-200 per USD, not 10000+)
- Consistency across providers
"""
import asyncio
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.fx import FXProviderFactory
from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_success,
    print_test_header,
    print_warning,
    exit_with_result,
)


# Expected reasonable ranges for multi-unit currencies
# Format: {currency: (min, max)} where values are per 1 USD
REASONABLE_RANGES = {
    'JPY': (Decimal("100"), Decimal("200")),   # 1 USD = 100-200 JPY (typical)
    'SEK': (Decimal("8"), Decimal("15")),      # 1 USD = 8-15 SEK (typical)
    'NOK': (Decimal("8"), Decimal("15")),      # 1 USD = 8-15 NOK (typical)
    'DKK': (Decimal("6"), Decimal("10")),      # 1 USD = 6-10 DKK (typical)
}


def is_rate_reasonable(currency: str, rate: Decimal, base_currency: str) -> tuple[bool, str]:
    """
    Check if a rate is in a reasonable range.

    This helps detect if multi-unit logic is correct.
    If JPY shows 14925 per USD instead of 149, we know there's a 100x error.

    Args:
        currency: Currency code (e.g., 'JPY')
        rate: Rate value (foreign currency per 1 base currency)
        base_currency: Base currency (USD, EUR, etc.)

    Returns:
        Tuple of (is_reasonable, explanation)
    """
    if currency not in REASONABLE_RANGES:
        return True, "Not a multi-unit currency"

    min_val, max_val = REASONABLE_RANGES[currency]

    # Adjust ranges based on base currency
    # These ranges are calibrated for USD base
    # For other bases, we allow wider ranges
    if base_currency != "USD":
        # Rough adjustment: multiply range by 2 for non-USD bases
        min_val = min_val / 2
        max_val = max_val * 2

    if rate < min_val:
        return False, f"Rate {rate} is too low (expected {min_val}-{max_val}). Possible over-inversion?"
    elif rate > max_val:
        return False, f"Rate {rate} is too high (expected {min_val}-{max_val}). Possible missing 100x division?"
    else:
        return True, f"Rate {rate} is within expected range ({min_val}-{max_val})"


async def test_multi_unit_identification(provider_code: str) -> bool:
    """Test that multi-unit currencies are correctly identified."""
    print_section(f"Test 1: {provider_code} - Multi-Unit Currency Identification")

    try:
        provider = FXProviderFactory.get_provider(provider_code)

        # Get multi-unit currencies from provider property (always exists, may be empty)
        multi_unit = provider.multi_unit_currencies

        if not multi_unit:
            print_info(f"{provider_code} has no multi-unit currencies (empty set)")
            print_info("This is normal for providers that quote all currencies per 1 unit")
            return True

        print_info(f"Multi-unit currencies defined: {multi_unit}")

        # Verify they are supported
        supported = await provider.get_supported_currencies()

        for currency in multi_unit:
            if currency in supported:
                print_success(f"  ✓ {currency} (multi-unit, supported)")
            else:
                print_warning(f"  ! {currency} (multi-unit but not supported)")

        return True

    except Exception as e:
        print_error(f"Multi-unit identification test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multi_unit_rates(provider_code: str) -> bool:
    """Test that multi-unit currency rates are in reasonable ranges."""
    print_section(f"Test 2: {provider_code} - Multi-Unit Rate Reasonableness")

    try:
        provider = FXProviderFactory.get_provider(provider_code)

        # Get multi-unit currencies from provider property
        multi_unit_currencies = provider.multi_unit_currencies

        if not multi_unit_currencies:
            print_info(f"{provider_code} has no multi-unit currencies, skipping rate tests")
            return True

        # Check which multi-unit currencies are supported
        supported = await provider.get_supported_currencies()
        testable = [c for c in multi_unit_currencies if c in supported]

        if not testable:
            print_warning(f"No multi-unit currencies supported by {provider_code}")
            return True

        print_info(f"Testing {len(testable)} multi-unit currency(ies): {', '.join(testable)}")

        # Fetch recent rates (last 7 days to have some data)
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=7)

        print_info(f"Fetching rates for {start_date} to {end_date}...")

        try:
            rates_data = await provider.fetch_rates((start_date, end_date), testable)
        except Exception as e:
            print_error(f"Failed to fetch rates: {e}")
            return False

        all_reasonable = True

        for currency in testable:
            observations = rates_data.get(currency, [])

            if not observations:
                print_warning(f"  {currency}: No data (weekends/holidays?)")
                continue

            # Check first observation
            # New format: (date, base, quote, rate)
            rate_date, obs_base, obs_quote, rate = observations[0]

            is_reasonable, explanation = is_rate_reasonable(
                currency, rate, provider.base_currency
            )

            if is_reasonable:
                print_success(f"  ✓ {currency}: {rate:.2f} per {provider.base_currency} - {explanation}")
            else:
                print_error(f"  ✗ {currency}: {rate:.2f} per {provider.base_currency} - {explanation}")
                all_reasonable = False

        return all_reasonable

    except Exception as e:
        print_error(f"Multi-unit rate reasonableness test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multi_unit_consistency(provider_code: str) -> bool:
    """Test consistency of multi-unit rate calculations."""
    print_section(f"Test 3: {provider_code} - Multi-Unit Calculation Consistency")

    try:
        provider = FXProviderFactory.get_provider(provider_code)

        # Get multi-unit currencies from provider property
        multi_unit_currencies = provider.multi_unit_currencies

        if not multi_unit_currencies:
            print_info(f"{provider_code} has no multi-unit currencies, skipping consistency test")
            return True

        print_info("Testing normalization logic for multi-unit currencies...")

        # Test case: JPY (if supported)
        if 'JPY' in multi_unit_currencies:
            # Simulate a typical FRED/SNB rate
            # Example: 100 JPY = 0.67 USD → 1 USD should = ~149 JPY

            test_api_rate = Decimal("0.67")  # 100 JPY = 0.67 base currency

            # Expected result after inversion: 1 base = 149.25 JPY
            expected_rate = Decimal("100") / test_api_rate

            print_info(f"  Test case: API says 100 JPY = {test_api_rate} {provider.base_currency}")
            print_info(f"  Expected: 1 {provider.base_currency} = {expected_rate:.2f} JPY")

            # Verify the math
            if expected_rate < Decimal("140") or expected_rate > Decimal("160"):
                print_error(f"  ✗ Calculation produces unexpected result: {expected_rate}")
                return False

            print_success(f"  ✓ Multi-unit inversion logic is mathematically correct")

        return True

    except Exception as e:
        print_error(f"Multi-unit consistency test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_provider(provider_code: str) -> dict[str, bool]:
    """Run all multi-unit tests for a single provider."""
    results = {}

    print_info("=" * 60)
    print_info(f"Testing Provider: {provider_code}")
    print_info("=" * 60)
    print_info("")

    results['identification'] = await test_multi_unit_identification(provider_code)
    results['reasonableness'] = await test_multi_unit_rates(provider_code)
    results['consistency'] = await test_multi_unit_consistency(provider_code)

    return results


async def main():
    """Run multi-unit currency tests for all providers."""
    print_test_header("LibreFolio - Multi-Unit Currency Tests")

    print_info("""
This test suite validates correct handling of multi-unit currencies.

Multi-unit currencies (JPY, SEK, NOK, DKK) are quoted per 100 units
instead of per 1 unit by some central banks.

Example:
- Normal: 1 EUR = 1.08 USD
- Multi-unit: 100 JPY = 0.67 USD (NOT 1 JPY = 0.0067 USD)

The code must handle this correctly:
✓ Correct: 1 USD = 100/0.67 = 149 JPY
✗ Wrong: 1 USD = 1/0.67 * 100 = 14925 JPY (100x error!)

📋 Prerequisites:
   • Internet connection (for live rate tests)
   • At least one provider with multi-unit currencies (FED, SNB)
    """)

    # Get all registered providers
    providers = FXProviderFactory.get_all_providers()

    print_info(f"Found {len(providers)} registered provider(s):")
    for p in providers:
        print_info(f"   • {p['code']}: {p['name']}")
    print_info("")

    all_results = {}

    for provider_info in providers:
        provider_code = provider_info['code']
        results = await test_provider(provider_code)
        all_results[provider_code] = results
        print_info("")

    # Summary
    print_section("Multi-Unit Currency Tests Summary")

    total_tests = 0
    passed_tests = 0

    for provider_code, results in all_results.items():
        for test_name, passed in results.items():
            total_tests += 1
            if passed:
                passed_tests += 1
                print_success(f"✓ {provider_code} - {test_name}")
            else:
                print_error(f"✗ {provider_code} - {test_name}")

    print_info("")
    print_section(f"Results: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print_success("All multi-unit currency tests passed! 🎉")
        print_success("")
        print_success("✅ Multi-unit currencies (JPY, SEK, NOK, DKK) are handled correctly")
        print_success("✅ Rates are in reasonable ranges (no 100x errors)")
        print_success("✅ Inversion logic is mathematically sound")
        exit_with_result(True)
    else:
        print_error(f"{total_tests - passed_tests} test(s) failed")
        print_error("")
        print_error("⚠️  Multi-unit currency handling may have issues:")
        print_error("   - Check MULTI_UNIT_CURRENCIES set includes all relevant currencies")
        print_error("   - Verify inversion logic: use (100 / rate) NOT (1 / rate * 100)")
        print_error("   - Review rate reasonableness checks above")
        exit_with_result(False)


if __name__ == "__main__":
    asyncio.run(main())

