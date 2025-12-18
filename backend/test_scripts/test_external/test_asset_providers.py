"""
Generic test suite for ALL asset pricing providers.

Tests all registered asset providers (yfinance, cssscraper, etc.) with uniform test suite.
Similar pattern to test_fx_providers.py.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from backend.app.db import IdentifierType

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
            # TODO: modificare i provider affichè forniscano nella test list anche l'expected_symbol
            expected_symbol = test_case.get('expected_symbol', identifier)
            # Get provider_params and identifier_type if specified in test_case
            provider_params = test_case.get('provider_params')
            if isinstance(provider_params, dict) and '_transaction_override' in test_case:
                provider_params['_transaction_override'] = test_case.get('_transaction_override')
            identifier_type = test_case.get('identifier_type', IdentifierType.TICKER)  # Default to TICKER

            print_info(f"  Testing: {identifier} (expects: {expected_symbol})")

            # Import IdentifierType if not already imported
            # Convert string to enum if needed
            if isinstance(identifier_type, str):
                identifier_type = IdentifierType[identifier_type]

            # Call with all required parameters
            try:
                if provider_params:
                    result = await provider.get_current_value(identifier, identifier_type, provider_params)
                else:
                    result = await provider.get_current_value(identifier, identifier_type)
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
    """Test get_history_value method (if supported)."""
    print_section(f"Test 3: {provider_code} - Historical Data Fetching")

    try:
        provider = AssetProviderRegistry.get_provider_instance(provider_code)

        # Check if historical data is supported via supports_history property
        supports_history = provider.supports_history

        if not supports_history:
            print_info(f"{provider_code} does not support historical data - SKIPPING")
            pytest.skip(f"{provider_code} does not support historical data")

        # Get first test case
        if not provider.test_cases:
            pytest.skip("No test_cases defined")

        test_case = provider.test_cases[0]
        identifier = test_case['identifier']
        identifier_type = test_case.get('identifier_type', IdentifierType.ISIN)
        provider_params = test_case.get('provider_params')
        if isinstance(provider_params, dict) and '_transaction_override' in test_case:
            provider_params['_transaction_override'] = test_case.get('_transaction_override')

        print_info(f"Testing historical data for: {identifier}")

        # Fetch last 7 days
        end_date = date.today()
        start_date = end_date - timedelta(days=7)

        print_info(f"  Date range: {start_date} to {end_date}")

        result = await provider.get_history_value(identifier, identifier_type, provider_params, start_date, end_date)

        # Validate result structure - FAHistoricalData has .prices attribute
        assert hasattr(result, 'prices'), f"Result missing 'prices' attribute: {type(result)}"

        prices = result.prices
        assert isinstance(prices, list), f"prices is not a list: {type(prices)}"

        if not prices:
            print_warning("  No price data returned (weekends/holidays?)")
        else:
            print_info(f"  Received {len(prices)} price points")

            # Check first price structure - FAPricePoint object
            first_price = prices[0]
            assert hasattr(first_price, 'date'), "Price point missing 'date'"
            assert hasattr(first_price, 'close'), "Price point missing 'close'"

            print_success(f"  ✓ First price: {first_price.date} close={first_price.close}")

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


def test_validate_params(provider_code: str):
    """Test provider_params validation using test_cases."""
    print_section(f"Test 5: {provider_code} - Provider Params Validation")

    try:
        provider = AssetProviderRegistry.get_provider_instance(provider_code)

        # Test 1: Validate with None (should work for providers that don't require params)
        print_info("Testing with None params...")
        try:
            provider.validate_params(None)
            print_success(f"  ✓ {provider_code} accepts None params")
            none_accepted = True
        except Exception as e:
            print_info(f"  {provider_code} rejects None params: {str(e)[:80]}")
            none_accepted = False

        # Test 2: Validate with empty dict (should work for providers that don't require params)
        print_info("Testing with empty dict params...")
        try:
            provider.validate_params({})
            print_success(f"  ✓ {provider_code} accepts empty dict params")
            empty_accepted = True
        except Exception as e:
            print_info(f"  {provider_code} rejects empty dict: {str(e)[:80]}")
            empty_accepted = False

        # Test 3: Validate all provider_params from test_cases
        if provider.test_cases:
            print_info(f"Testing {len(provider.test_cases)} test case(s) with provider_params...")

            for idx, test_case in enumerate(provider.test_cases, 1):
                provider_params = test_case.get('provider_params')
                identifier = test_case.get('identifier', 'N/A')

                print_info(f"  Test case {idx}/{len(provider.test_cases)}: {identifier[:50]}...")

                if provider_params is not None:
                    # Test case has params - should validate successfully
                    try:
                        provider.validate_params(provider_params)
                        print_success(f"    ✓ Params validated: {list(provider_params.keys())}")
                    except Exception as e:
                        print_error(f"    ✗ Validation failed: {e}")
                        raise
                else:
                    # Test case has no params - provider should accept None
                    print_info(f"    Test case has no provider_params (None)")
                    if not none_accepted:
                        print_warning(f"    Provider requires params but test_case has None!")

            # If any test_case has params, ensure None/empty were rejected (provider requires params)
            any_test_case_has_params = any(tc.get('provider_params') is not None for tc in provider.test_cases)
            if any_test_case_has_params and none_accepted:
                print_warning(f"  Provider has test_cases with params but also accepts None - may be intentional")
        else:
            print_info(f"  {provider_code} has no test_cases - skipping params validation from test_cases")

        print_success("Provider params validation test passed")

    except Exception as e:
        print_error(f"Validation test failed: {e}")
        traceback.print_exc()
        raise


@pytest.mark.asyncio
async def test_error_handling(provider_code: str):
    """Test error handling with invalid identifier."""
    print_section(f"Test 6: {provider_code} - Error Handling")

    try:
        provider = AssetProviderRegistry.get_provider_instance(provider_code)

        # Try with invalid identifier
        invalid_identifier = "INVALID_NONEXISTENT_SYMBOL_12345"
        print_info(f"Testing with invalid identifier: {invalid_identifier}")

        from backend.app.db.models import IdentifierType

        error_raised = False
        try:
            result = await provider.get_current_value(invalid_identifier, IdentifierType.TICKER)

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
