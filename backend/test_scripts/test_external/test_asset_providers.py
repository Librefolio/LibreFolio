"""
Generic test suite for ALL asset pricing providers.

Tests all registered asset providers (yfinance, cssscraper, etc.) with uniform test suite.
Similar pattern to test_fx_providers.py.
"""
import sys
import traceback
from datetime import date, timedelta
from pathlib import Path

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.provider_registry import AssetProviderRegistry
from backend.app.services.asset_source import AssetSourceError
from backend.app.schemas.prices import FACurrentValue
from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_success,
    print_warning,
)
import traceback


# ============================================================================
# PYTEST FIXTURES AND PARAMETRIZATION
# ============================================================================
"""
PYTEST PARAMETRIZATION STRATEGY:

This file uses pytest.mark.parametrize at module level to automatically
run ALL test functions for EACH registered asset provider.

Example: If 2 providers are registered (yfinance, cssscraper) and we have
5 test functions, pytest will generate 2×5 = 10 individual tests.

To see all generated tests:
  pytest backend/test_scripts/test_external/test_asset_providers.py --collect-only
"""


def get_all_asset_providers():
    """
    Get all registered asset providers for parametrization.
    This ensures tests run for ALL registered providers dynamically.
    """
    AssetProviderRegistry.auto_discover()
    providers = AssetProviderRegistry.list_providers()

    if not providers:
        pytest.skip("No asset providers registered")

    # Extract provider codes
    provider_codes = []
    for p in providers:
        code = p['code'] if isinstance(p, dict) else p
        provider_codes.append(code)

    return provider_codes


# Parametrize all tests to run for each registered provider
pytestmark = pytest.mark.parametrize("provider_code", get_all_asset_providers())


# ============================================================================
# INDIVIDUAL TEST FUNCTIONS (run for each provider via parametrize)
# ============================================================================

def test_provider_metadata(provider_code: str):
    """Test provider metadata (code, name, registration)."""
    print_section(f"Test 1: {provider_code} - Metadata & Registration")

    try:
        # Check registration
        provider_class = AssetProviderRegistry.get_provider(provider_code)
        assert provider_class, f"{provider_code} provider not registered"

        print_success(f"{provider_code} is registered in registry")

        # Get provider instance
        provider = AssetProviderRegistry.get_provider_instance(provider_code)

        code = provider.provider_code
        name = provider.provider_name

        print_info(f"  Provider code: {code}")
        print_info(f"  Provider name: {name}")

        assert code, "Provider code is empty"
        assert name, "Provider name is empty"
        assert code == provider_code, f"Provider code mismatch: {code} != {provider_code}"

        print_success("Provider metadata valid")

    except Exception as e:
        print_error(f"Metadata test failed: {e}")
        traceback.print_exc()
        raise


@pytest.mark.asyncio
async def test_current_value(provider_code: str):
    """Test get_current_value method."""
    print_section(f"Test 2: {provider_code} - Current Value Fetching")

    try:
        provider = AssetProviderRegistry.get_provider_instance(provider_code)

        # Check if provider has test_cases
        if not provider.test_cases:
            print_warning("No test_cases defined for provider")
            pytest.skip(f"{provider_code} has no test_cases defined")

        print_info(f"Testing {len(provider.test_cases)} test case(s)...")

        for test_case in provider.test_cases:
            identifier = test_case['identifier']
            expected_symbol = test_case.get('expected_symbol', identifier)
            # Get provider_params if specified in test_case (for cssscraper, scheduled_investment, etc.)
            provider_params = test_case.get('provider_params')

            print_info(f"  Testing: {identifier} (expects: {expected_symbol})")

            # Call with provider_params if available, otherwise without
            try:
                if provider_params:
                    result = await provider.get_current_value(identifier, provider_params)
                else:
                    result = await provider.get_current_value(identifier)
            except TypeError as e:
                # Provider requires provider_params but test_case doesn't have it
                if "provider_params" in str(e):
                    print_warning(f"{provider_code} requires provider_params but none in test_case - SKIPPING")
                    pytest.skip(f"{provider_code} test_case missing provider_params")
                raise

            # Validate result is FACurrentValue Pydantic model
            assert isinstance(result, FACurrentValue), f"Result is not FACurrentValue: {type(result)}"

            # Access Pydantic model attributes directly (FACurrentValue has: value, currency, as_of_date, source)
            current_price = result.value
            currency = result.currency
            as_of_date = result.as_of_date

            # Validate values
            assert current_price is not None, f"value is None for {identifier}"
            assert current_price > 0, f"value not positive: {current_price}"
            assert currency, f"currency is empty for {identifier}"
            assert len(currency) == 3, f"currency not 3-letter code: {currency}"
            assert as_of_date, f"as_of_date is empty for {identifier}"

            print_success(f"  ✓ {identifier}: {current_price} {currency} (as_of: {as_of_date})")

        print_success(f"All {len(provider.test_cases)} test cases passed")

    except AssetSourceError as e:
        # Check if it's a "requires provider_params" or "not supported" error
        if "requires provider_params" in str(e).lower() or "not supported" in str(e).lower():
            print_warning(f"{provider_code}: {e} - SKIPPING")
            pytest.skip(str(e))
        print_error(f"Provider error: {e}")
        raise

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        traceback.print_exc()
        raise


@pytest.mark.asyncio
async def test_historical_data(provider_code: str):
    """Test get_historical_data method (if supported)."""
    print_section(f"Test 3: {provider_code} - Historical Data Fetching")

    try:
        provider = AssetProviderRegistry.get_provider_instance(provider_code)

        # Check if historical data is supported
        supports_history = hasattr(provider, 'get_historical_data') and callable(provider.get_historical_data)

        if not supports_history:
            print_info(f"{provider_code} does not support historical data - SKIPPING")
            pytest.skip(f"{provider_code} does not support historical data")

        # Get first test case
        if not provider.test_cases:
            pytest.skip("No test_cases defined")

        test_case = provider.test_cases[0]
        identifier = test_case['identifier']

        print_info(f"Testing historical data for: {identifier}")

        # Fetch last 7 days
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        print_info(f"  Date range: {start_date} to {end_date}")

        result = await provider.get_historical_data(identifier, start_date, end_date)

        # Validate result structure
        assert isinstance(result, dict), f"Result is not a dict: {type(result)}"
        assert 'prices' in result, "Result missing 'prices' list"

        prices = result['prices']
        assert isinstance(prices, list), f"prices is not a list: {type(prices)}"

        if not prices:
            print_warning("  No price data returned (weekends/holidays?)")
        else:
            print_info(f"  Received {len(prices)} price points")

            # Check first price structure
            first_price = prices[0]
            assert isinstance(first_price, dict), "Price point is not a dict"
            assert 'date' in first_price, "Price point missing 'date'"
            assert 'close' in first_price, "Price point missing 'close'"

            print_success(f"  ✓ First price: {first_price['date']} close={first_price['close']}")

        print_success("Historical data fetch successful")

    except AssetSourceError as e:
        print_error(f"Provider error: {e}")
        raise

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        traceback.print_exc()
        raise


@pytest.mark.asyncio
async def test_search(provider_code: str):
    """Test search method (if supported)."""
    print_section(f"Test 4: {provider_code} - Search Functionality")

    try:
        provider = AssetProviderRegistry.get_provider_instance(provider_code)

        # Check if search is supported
        supports_search = hasattr(provider, 'search') and callable(provider.search)

        if not supports_search:
            print_info(f"{provider_code} does not support search - SKIPPING")
            pytest.skip(f"{provider_code} does not support search")

        # Test with a common search term
        search_term = "Apple"
        print_info(f"Searching for: '{search_term}'")

        try:
            results = await provider.search(search_term)
        except AssetSourceError as e:
            # Provider has search method but doesn't support it or raises error
            if "not supported" in str(e).lower():
                print_info(f"{provider_code} search not supported - SKIPPING")
                pytest.skip(f"{provider_code}: {e}")
            raise

        # Validate result structure
        assert isinstance(results, list), f"Results is not a list: {type(results)}"

        if not results:
            print_warning(f"  No results for '{search_term}' (OK)")
        else:
            print_info(f"  Found {len(results)} result(s)")

            # Check first result structure
            first_result = results[0]
            assert isinstance(first_result, dict), "Search result is not a dict"

            # Different providers may return different keys (symbol/identifier, name/description/display_name)
            has_symbol = 'symbol' in first_result or 'identifier' in first_result
            has_name = 'name' in first_result or 'description' in first_result or 'display_name' in first_result

            assert has_symbol, f"Search result missing 'symbol' or 'identifier': {first_result.keys()}"
            assert has_name, f"Search result missing 'name', 'description', or 'display_name': {first_result.keys()}"

            symbol = first_result.get('symbol') or first_result.get('identifier')
            name = first_result.get('name') or first_result.get('description') or first_result.get('display_name')
            print_success(f"  ✓ First result: {symbol} - {name}")

        print_success("Search functionality OK")

    except AssetSourceError as e:
        # Already handled above, but catch again for safety
        if "not supported" in str(e).lower():
            print_info(f"{provider_code} search not supported - SKIPPING")
            pytest.skip(f"{provider_code}: {e}")
        print_error(f"Provider error: {e}")
        raise

    except Exception as e:
        print_error(f"Unexpected error: {e}")
        traceback.print_exc()
        raise


@pytest.mark.asyncio
async def test_error_handling(provider_code: str):
    """Test error handling with invalid identifier."""
    print_section(f"Test 5: {provider_code} - Error Handling")

    try:
        provider = AssetProviderRegistry.get_provider_instance(provider_code)

        # Try with invalid identifier
        invalid_identifier = "INVALID_NONEXISTENT_SYMBOL_12345"
        print_info(f"Testing with invalid identifier: {invalid_identifier}")

        error_raised = False
        try:
            result = await provider.get_current_value(invalid_identifier)

            # If we got a result, check what it is
            if result is None:
                # Provider returned None - acceptable
                print_success(f"  ✓ Provider returned None for invalid identifier")
                error_raised = True
            elif isinstance(result, FACurrentValue):
                # Got a valid result - provider may have returned mock/default data
                print_warning(f"  Provider returned result for invalid identifier: {result.symbol}")
                print_info(f"  This may be acceptable for test/mock providers")
                # Don't fail for mock providers
                if 'mock' in provider_code.lower() or 'test' in provider_code.lower():
                    error_raised = True
                else:
                    print_error("  Real provider should have raised AssetSourceError")

        except AssetSourceError as e:
            # Expected behavior
            print_success(f"  ✓ Correctly raised AssetSourceError: {e.error_code}")
            assert e.error_code, "Error code is empty"
            error_raised = True

        except Exception as e:
            # Other exceptions are also acceptable (404, connection errors, etc.)
            print_success(f"  ✓ Correctly raised exception: {type(e).__name__}")
            error_raised = True

        if not error_raised:
            print_error("  Provider should have raised error or returned None")
            pytest.fail("Expected error handling for invalid identifier")

        print_success("Error handling works correctly")

    except Exception as e:
        print_error(f"Error handling test failed: {e}")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
