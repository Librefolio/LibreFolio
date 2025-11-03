"""
Generic Provider Tests for FX Rate Providers
Tests all registered FX providers (ECB, FED, BOE, etc.) with uniform test suite.
"""
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.fx import FXServiceError, FXProviderFactory
from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_success,
    print_test_header,
    print_test_summary,
    exit_with_result,
    )


async def test_provider_metadata(provider_code: str) -> bool:
    """Test provider metadata and instantiation."""
    print_section(f"Test 1: {provider_code} - Metadata & Registration")

    try:
        # Check registration
        if not FXProviderFactory.is_registered(provider_code):
            print_error(f"{provider_code} provider not registered")
            return False

        print_success(f"{provider_code} is registered in factory")

        # Get instance
        provider = FXProviderFactory.get_provider(provider_code)

        # Validate metadata
        print_info(f"  Code: {provider.code}")
        print_info(f"  Name: {provider.name}")
        print_info(f"  Base currency: {provider.base_currency}")
        print_info(f"  Description: {provider.description}")

        # Validate base currency format
        if not provider.base_currency or len(provider.base_currency) != 3:
            print_error(f"Invalid base currency: {provider.base_currency}")
            return False

        print_success("Provider metadata valid")
        return True

    except Exception as e:
        print_error(f"Provider metadata test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_supported_currencies(provider_code: str) -> bool:
    """Test fetching supported currencies list."""
    print_section(f"Test 2: {provider_code} - Supported Currencies")

    try:
        provider = FXProviderFactory.get_provider(provider_code)

        print_info(f"Fetching supported currencies from {provider.name}...")
        currencies = await provider.get_supported_currencies()

        if not currencies:
            print_error("No currencies returned")
            return False

        print_success(f"Found {len(currencies)} supported currencies")

        # Verify base currency is included
        if provider.base_currency not in currencies:
            print_error(f"Base currency {provider.base_currency} not in supported list")
            return False

        print_success(f"Base currency {provider.base_currency} is present")

        # Check test currencies (provider-specific expected currencies)
        test_currencies = provider.test_currencies
        print_info(f"Checking {len(test_currencies)} test currencies...")

        missing = []
        for curr in test_currencies:
            if curr in currencies:
                print_success(f"  ✓ {curr}")
            else:
                print_error(f"  ✗ {curr} (MISSING)")
                missing.append(curr)

        if missing:
            print_error(f"Missing test currencies: {', '.join(missing)}")
            return False

        # Show sample of other currencies
        other = sorted([c for c in currencies if c not in test_currencies])
        if other:
            sample = other[:10]
            print_info(f"Other currencies ({len(other)}): {', '.join(sample)}...")

        print_success("All test currencies present")
        return True

    except FXServiceError as e:
        print_error(f"API error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fetch_rates(provider_code: str) -> bool:
    """Test fetching actual FX rates."""
    print_section(f"Test 3: {provider_code} - Fetch Rates")

    try:
        provider = FXProviderFactory.get_provider(provider_code)

        # Test date range: last 5 business days
        end_date = date.today()
        start_date = end_date - timedelta(days=7)  # 7 days to ensure we get some business days

        # Get 2 test currencies (excluding base)
        test_currencies = [c for c in provider.test_currencies if c != provider.base_currency][:2]

        if not test_currencies:
            print_info("No test currencies available (only base currency)")
            return True

        print_info(f"Fetching rates for {', '.join(test_currencies)} from {start_date} to {end_date}...")

        rates_data = await provider.fetch_rates(
            (start_date, end_date),
            test_currencies
        )

        if not rates_data:
            print_error("No rate data returned")
            return False

        print_success(f"Received rate data for {len(rates_data)} currencies")

        # Validate structure
        for currency, observations in rates_data.items():
            print_info(f"  {currency}: {len(observations)} observations")

            if observations:
                # Check first observation structure
                first_obs = observations[0]
                if not isinstance(first_obs, tuple) or len(first_obs) != 2:
                    print_error(f"Invalid observation format for {currency}")
                    return False

                obs_date, obs_rate = first_obs

                # Validate types
                if not isinstance(obs_date, date):
                    print_error(f"Invalid date type for {currency}: {type(obs_date)}")
                    return False

                from decimal import Decimal
                if not isinstance(obs_rate, Decimal):
                    print_error(f"Invalid rate type for {currency}: {type(obs_rate)}")
                    return False

                # Validate rate is positive
                if obs_rate <= 0:
                    print_error(f"Invalid rate value for {currency}: {obs_rate}")
                    return False

                print_success(f"  ✓ {currency}: {obs_date} = {obs_rate}")

        print_success("Rate data structure valid")
        return True

    except FXServiceError as e:
        print_error(f"API error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_normalize_for_storage(provider_code: str) -> bool:
    """Test rate normalization for alphabetical storage."""
    print_section(f"Test 4: {provider_code} - Rate Normalization")

    try:
        from decimal import Decimal
        provider = FXProviderFactory.get_provider(provider_code)

        print_info(f"Testing normalization for {provider.base_currency} base...")

        # Test case 1: currency > base (no inversion)
        test_currency_higher = None
        for curr in provider.test_currencies:
            if curr > provider.base_currency:
                test_currency_higher = curr
                break

        if test_currency_higher:
            rate = Decimal("1.5")
            base, quote, normalized_rate = provider.normalize_for_storage(test_currency_higher, rate)

            print_info(f"  Case 1: {provider.base_currency} < {test_currency_higher}")
            print_info(f"    Input rate: {rate}")
            print_info(f"    Stored as: {base}/{quote} = {normalized_rate}")

            if base != provider.base_currency or quote != test_currency_higher:
                print_error(f"Expected {provider.base_currency}/{test_currency_higher}, got {base}/{quote}")
                return False

            if normalized_rate != rate:
                print_error(f"Rate should not be inverted: {rate} != {normalized_rate}")
                return False

            print_success(f"  ✓ No inversion: {base}/{quote} = {normalized_rate}")

        # Test case 2: currency < base (inversion needed)
        test_currency_lower = None
        for curr in provider.test_currencies:
            if curr < provider.base_currency:
                test_currency_lower = curr
                break

        if test_currency_lower:
            rate = Decimal("1.5")
            base, quote, normalized_rate = provider.normalize_for_storage(test_currency_lower, rate)

            print_info(f"  Case 2: {test_currency_lower} < {provider.base_currency}")
            print_info(f"    Input rate: {rate}")
            print_info(f"    Stored as: {base}/{quote} = {normalized_rate}")

            if base != test_currency_lower or quote != provider.base_currency:
                print_error(f"Expected {test_currency_lower}/{provider.base_currency}, got {base}/{quote}")
                return False

            expected_inverted = Decimal("1") / rate
            if abs(normalized_rate - expected_inverted) > Decimal("0.0001"):
                print_error(f"Rate should be inverted: expected {expected_inverted}, got {normalized_rate}")
                return False

            print_success(f"  ✓ Inverted: {base}/{quote} = {normalized_rate}")

        print_success("Rate normalization works correctly")
        return True

    except Exception as e:
        print_error(f"Normalization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_single_provider(provider_code: str) -> dict[str, bool]:
    """Run all tests for a single provider."""
    results = {}

    print_info(f"\n{'='*60}")
    print_info(f"Testing Provider: {provider_code}")
    print_info(f"{'='*60}\n")

    # Run all tests
    results[f"{provider_code} - Metadata"] = await test_provider_metadata(provider_code)
    results[f"{provider_code} - Supported Currencies"] = await test_supported_currencies(provider_code)
    results[f"{provider_code} - Fetch Rates"] = await test_fetch_rates(provider_code)
    results[f"{provider_code} - Normalization"] = await test_normalize_for_storage(provider_code)

    return results


async def run_all_tests():
    """Run tests for all registered providers."""
    print_test_header(
        "LibreFolio - FX Providers: Generic Test Suite",
        description="""This test suite runs uniform tests on ALL registered FX providers.
        
Tests performed for each provider:
  • Metadata validation and registration
  • Supported currencies retrieval
  • Actual rate fetching (last 7 days)
  • Rate normalization for storage
  
This ensures all providers implement the interface correctly and work as expected.""",
        prerequisites=[
            "Internet connection",
            "Provider APIs accessible",
            "At least one provider registered (ECB, FED, BOE, etc.)"
            ]
        )

    # Get all registered providers
    all_providers = FXProviderFactory.get_all_providers()

    if not all_providers:
        print_error("No providers registered in factory!")
        return False

    print_info(f"\nFound {len(all_providers)} registered provider(s):")
    for p in all_providers:
        print_info(f"  • {p['code']}: {p['name']} (base: {p['base_currency']})")

    # Run tests for each provider
    all_results = {}

    for provider_info in all_providers:
        provider_code = provider_info['code']
        provider_results = await test_single_provider(provider_code)
        all_results.update(provider_results)

    # Summary
    print_info(f"\n{'='*60}")
    print_info("OVERALL SUMMARY")
    print_info(f"{'='*60}\n")

    success = print_test_summary(all_results, "All FX Providers Tests")

    if success:
        print_success(f"\n🎉 All {len(all_providers)} provider(s) passed all tests! 🎉")
        for p in all_providers:
            print_info(f"  ✓ {p['code']}: {p['name']}")
    else:
        print_error("\n❌ Some tests failed. Check:")
        print_error("  - Internet connection")
        print_error("  - Provider API status")
        print_error("  - Provider implementation")

    return success


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit_with_result(success)
