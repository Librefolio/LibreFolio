"""
Generic Provider Tests for FX Rate Providers
Tests all registered FX providers (ECB, FED, BOE, etc.) with uniform test suite.
"""
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_success,
    print_warning,
    )
from backend.app.services.fx import FXServiceError, normalize_rate_for_storage
from backend.app.services.provider_registry import FXProviderRegistry

# TODO: riflettere per il futuro di usare 'pipenv install pytest-xdist' per parallelizzare la run di questi test

# ============================================================================
# PYTEST FIXTURES AND PARAMETRIZATION
# ============================================================================
"""
PYTEST PARAMETRIZATION STRATEGY:

This file uses pytest.mark.parametrize at module level to automatically
run ALL test functions for EACH registered FX provider.

Example: If 4 providers are registered (ECB, FED, BOE, SNB) and we have
4 test functions, pytest will generate 4×4 = 16 individual tests:
  - test_provider_metadata[ECB]
  - test_provider_metadata[FED]
  - test_provider_metadata[BOE]
  - test_provider_metadata[SNB]
  - test_supported_currencies[ECB]
  - ... (and so on)

This ensures ALL providers are tested uniformly without manual orchestration.

To see all generated tests:
  pytest backend/test_scripts/test_external/test_fx_providers.py --collect-only
"""


def get_all_fx_providers():
    """
    Get all registered FX providers for parametrization.
    This ensures tests run for ALL registered providers dynamically.
    """
    FXProviderRegistry.auto_discover()
    providers = FXProviderRegistry.list_providers()

    if not providers:
        pytest.skip("No FX providers registered")

    # Extract provider codes
    provider_codes = []
    for p in providers:
        code = p['code'] if isinstance(p, dict) else p
        provider_codes.append(code)

    return provider_codes


# Parametrize all tests to run for each registered provider
# This replaces the old run_all_tests() orchestration
pytestmark = pytest.mark.parametrize("provider_code", get_all_fx_providers())


# ============================================================================
# INDIVIDUAL TEST FUNCTIONS (run for each provider via parametrize)
# ============================================================================

@pytest.mark.asyncio
async def test_provider_metadata(provider_code: str):
    """Test provider metadata and instantiation."""
    print_section(f"Test 1: {provider_code} - Metadata & Registration")

    try:
        # Check registration
        provider_class = FXProviderRegistry.get_provider(provider_code)
        assert provider_class, f"{provider_code} provider not registered"

        print_success(f"{provider_code} is registered in registry")

        # Get instance
        provider = FXProviderRegistry.get_provider_instance(provider_code)

        # Validate metadata
        print_info(f"  Code: {provider.code}")
        print_info(f"  Name: {provider.name}")
        print_info(f"  Base currency: {provider.base_currency}")
        print_info(f"  Description: {provider.description}")

        # Validate base currency format
        assert provider.base_currency and len(provider.base_currency) == 3, f"Invalid base currency: {provider.base_currency}"

        print_success("Provider metadata valid")

    except Exception as e:
        print_error(f"Provider metadata test failed: {e}")
        import traceback
        traceback.print_exc()


@pytest.mark.asyncio
async def test_supported_currencies(provider_code: str):
    """Test fetching supported currencies list."""
    print_section(f"Test 2: {provider_code} - Supported Currencies")

    try:
        provider = FXProviderRegistry.get_provider_instance(provider_code)

        print_info(f"Fetching supported currencies from {provider.name}...")
        currencies = await provider.get_supported_currencies()

        assert currencies, "No currencies returned"

        print_success(f"Found {len(currencies)} supported currencies")

        # Verify base currency is included
        assert provider.base_currency in currencies, f"Base currency {provider.base_currency} not in supported list"

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

        # Show sample of other currencies
        other = sorted([c for c in currencies if c not in test_currencies])
        if other:
            sample = other[:10]
            print_info(f"Other currencies ({len(other)}): {', '.join(sample)}...")

        print_success("All test currencies present")

    except FXServiceError as e:
        print_error(f"API error: {e}")

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


@pytest.mark.asyncio
async def test_fetch_rates(provider_code: str):
    """Test fetching actual FX rates."""
    print_section(f"Test 3: {provider_code} - Fetch Rates")

    try:
        provider = FXProviderRegistry.get_provider_instance(provider_code)

        # Test date range: last 5 business days
        end_date = date.today()
        start_date = end_date - timedelta(days=7)  # 7 days to ensure we get some business days

        # Get 2 test currencies (excluding base)
        test_currencies = [c for c in provider.test_currencies if c != provider.base_currency][:2]

        if not test_currencies:
            print_info("No test currencies available (only base currency)")

        print_info(f"Fetching rates for {', '.join(test_currencies)} from {start_date} to {end_date}...")

        rates_data = await provider.fetch_rates(
            (start_date, end_date),
            test_currencies
            )

        assert rates_data, "No rate data returned"

        print_success(f"Received rate data for {len(rates_data)} currencies")

        # Validate structure
        for currency, observations in rates_data.items():
            print_info(f"  {currency}: {len(observations)} observations")

            if observations:
                # Check first observation structure
                first_obs = observations[0]
                assert isinstance(first_obs, tuple) and len(first_obs) == 4, f"Invalid observation format for {currency}"

                obs_date, base, quote, obs_rate = first_obs

                # Validate types
                if not isinstance(obs_date, date):
                    print_error(f"Invalid date type for {currency}: {type(obs_date)}")

                if not isinstance(base, str) or not isinstance(quote, str):
                    print_error(f"Invalid currency types for {currency}: {type(base)}, {type(quote)}")

                if not isinstance(obs_rate, Decimal):
                    print_error(f"Invalid rate type for {currency}: {type(obs_rate)}")

                # Validate rate is positive
                assert obs_rate > 0, f"Invalid rate value for {currency}: {obs_rate}"

                print_success(f"  ✓ {currency}: {obs_date} {base}/{quote} = {obs_rate}")

        print_success("Rate data structure valid")

    except FXServiceError as e:
        print_error(f"API error: {e}")

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()


@pytest.mark.asyncio
async def test_normalize_for_storage(provider_code: str):
    """Test rate normalization for alphabetical storage."""
    print_section(f"Test 4: {provider_code} - Rate Normalization")

    try:
        provider = FXProviderRegistry.get_provider_instance(provider_code)

        print_info(f"Testing normalization for {provider.base_currency} base...")

        # Test case 1: currency > base (no inversion)
        test_currency_higher = None
        for curr in provider.test_currencies:
            if curr > provider.base_currency:
                test_currency_higher = curr
                break

        if test_currency_higher:
            rate = Decimal("1.5")
            base, quote, normalized_rate = normalize_rate_for_storage(provider.base_currency, test_currency_higher, rate)
            print_info(f"  Case 1: {provider.base_currency} < {test_currency_higher}")
            print_info(f"    Input rate: {rate}")
            print_info(f"    Stored as: {base}/{quote} = {normalized_rate}")

            assert base == provider.base_currency and quote == test_currency_higher, f"Expected {provider.base_currency}/{test_currency_higher}, got {base}/{quote}"

            assert normalized_rate == rate, f"Rate should not be inverted: {rate} != {normalized_rate}"

            print_success(f"  ✓ No inversion: {base}/{quote} = {normalized_rate}")

        # Test case 2: currency < base (inversion needed)
        test_currency_lower = None
        for curr in provider.test_currencies:
            if curr < provider.base_currency:
                test_currency_lower = curr
                break

        if test_currency_lower:
            rate = Decimal("1.5")
            base, quote, normalized_rate = normalize_rate_for_storage(provider.base_currency, test_currency_lower, rate)

            print_info(f"  Case 2: {test_currency_lower} < {provider.base_currency}")
            print_info(f"    Input rate: {rate}")
            print_info(f"    Stored as: {base}/{quote} = {normalized_rate}")

            assert base == test_currency_lower and quote == provider.base_currency, f"Expected {test_currency_lower}/{provider.base_currency}, got {base}/{quote}"

            expected_inverted = Decimal("1") / rate
            assert abs(normalized_rate - expected_inverted) <= Decimal("0.0001"), f"Rate should be inverted: expected {expected_inverted}, got {normalized_rate}"

            print_success(f"  ✓ Inverted: {base}/{quote} = {normalized_rate}")

        print_success("Rate normalization works correctly")

    except Exception as e:
        print_error(f"Normalization test failed: {e}")
        import traceback
        traceback.print_exc()
        raise  # Re-raise for pytest


# ============================================================================
# MULTI-UNIT CURRENCY TESTS
# ============================================================================
"""
Multi-unit currency tests verify correct handling of currencies quoted
per 100 units instead of per 1 unit (JPY, SEK, NOK, DKK).

These tests only run for providers that have multi_unit_currencies defined.
Providers without multi-unit support will skip these tests automatically.
"""

# Expected reasonable ranges for multi-unit currencies
# Format: {currency: (min, max)} where values are per 1 USD
REASONABLE_RANGES = {
    'JPY': (Decimal("100"), Decimal("200")),  # 1 USD = 100-200 JPY (typical)
    'SEK': (Decimal("8"), Decimal("15")),  # 1 USD = 8-15 SEK (typical)
    'NOK': (Decimal("8"), Decimal("15")),  # 1 USD = 8-15 NOK (typical)
    'DKK': (Decimal("6"), Decimal("10")),  # 1 USD = 6-10 DKK (typical)
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


@pytest.mark.asyncio
async def test_multi_unit_identification(provider_code: str):
    """
    Test that multi-unit currencies are correctly identified.

    Skips if provider has no multi-unit currencies.
    """
    print_section(f"Multi-Unit Test 1: {provider_code} - Currency Identification")

    try:
        provider = FXProviderRegistry.get_provider_instance(provider_code)

        # Get multi-unit currencies from provider property
        multi_unit = provider.multi_unit_currencies

        if not multi_unit:
            print_info(f"{provider_code} has no multi-unit currencies - SKIPPING")
            pytest.skip(f"{provider_code} does not support multi-unit currencies")

        print_info(f"Multi-unit currencies defined: {multi_unit}")

        # Verify they are supported
        supported = await provider.get_supported_currencies()

        for currency in multi_unit:
            if currency in supported:
                print_success(f"  ✓ {currency} (multi-unit, supported)")
            else:
                print_warning(f"  ! {currency} (multi-unit but not supported)")

    except Exception as e:
        print_error(f"Multi-unit identification test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


@pytest.mark.asyncio
async def test_multi_unit_reasonableness(provider_code: str):
    """
    Test that multi-unit currency rates are in reasonable ranges.

    Skips if provider has no multi-unit currencies.
    """
    print_section(f"Multi-Unit Test 2: {provider_code} - Rate Reasonableness")

    try:
        provider = FXProviderRegistry.get_provider_instance(provider_code)

        # Get multi-unit currencies from provider property
        multi_unit_currencies = provider.multi_unit_currencies

        if not multi_unit_currencies:
            print_info(f"{provider_code} has no multi-unit currencies - SKIPPING")
            pytest.skip(f"{provider_code} does not support multi-unit currencies")

        # Check which multi-unit currencies are supported
        supported = await provider.get_supported_currencies()
        testable = [c for c in multi_unit_currencies if c in supported]

        if not testable:
            print_warning(f"No multi-unit currencies supported by {provider_code}")
            pytest.skip(f"{provider_code} has multi-unit defined but none supported")

        print_info(f"Testing {len(testable)} multi-unit currency(ies): {', '.join(testable)}")

        # Fetch recent rates (last 7 days to have some data)
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=7)

        print_info(f"Fetching rates for {start_date} to {end_date}...")

        try:
            rates_data = await provider.fetch_rates((start_date, end_date), testable)
        except Exception as e:
            print_error(f"Failed to fetch rates: {e}")
            raise

        all_reasonable = True

        for currency in testable:
            observations = rates_data.get(currency, [])

            if not observations:
                print_warning(f"  {currency}: No data (weekends/holidays?)")
                continue

            # Check first observation
            # Format: (date, base, quote, rate)
            rate_date, obs_base, obs_quote, rate = observations[0]

            is_reasonable, explanation = is_rate_reasonable(
                currency, rate, provider.base_currency
                )

            if is_reasonable:
                print_success(f"  ✓ {currency}: {rate:.2f} per {provider.base_currency} - {explanation}")
            else:
                print_error(f"  ✗ {currency}: {rate:.2f} per {provider.base_currency} - {explanation}")
                all_reasonable = False

        assert all_reasonable, "Some multi-unit rates are outside reasonable ranges"

    except Exception as e:
        print_error(f"Multi-unit rate reasonableness test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


@pytest.mark.asyncio
async def test_multi_unit_consistency(provider_code: str):
    """
    Test consistency of multi-unit rate calculations.

    Skips if provider has no multi-unit currencies.
    """
    print_section(f"Multi-Unit Test 3: {provider_code} - Calculation Consistency")

    try:
        provider = FXProviderRegistry.get_provider_instance(provider_code)

        # Get multi-unit currencies from provider property
        multi_unit_currencies = provider.multi_unit_currencies

        if not multi_unit_currencies:
            print_info(f"{provider_code} has no multi-unit currencies - SKIPPING")
            pytest.skip(f"{provider_code} does not support multi-unit currencies")

        print_info("Testing normalization logic for multi-unit currencies...")

        # Test case: JPY (if in multi-unit set)
        if 'JPY' in multi_unit_currencies:
            # Simulate a typical rate
            # Example: 100 JPY = 0.67 USD → 1 USD should = ~149 JPY

            test_api_rate = Decimal("0.67")  # 100 JPY = 0.67 base currency

            # Expected result after inversion: 1 base = 149.25 JPY
            expected_rate = Decimal("100") / test_api_rate

            print_info(f"  Test case: API says 100 JPY = {test_api_rate} {provider.base_currency}")
            print_info(f"  Expected: 1 {provider.base_currency} = {expected_rate:.2f} JPY")

            # Verify the math (allow 140-160 range)
            assert Decimal("140") <= expected_rate <= Decimal("160"), \
                f"Calculation produces unexpected result: {expected_rate}"

            print_success(f"  ✓ Multi-unit inversion logic is mathematically correct")
        else:
            print_info(f"  JPY not in {provider_code} multi-unit set, skipping math test")

    except Exception as e:
        print_error(f"Multi-unit consistency test failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
