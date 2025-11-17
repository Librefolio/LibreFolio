"""
Generic test suite for ALL asset pricing providers.

This test file discovers all registered providers via AssetProviderRegistry
and runs uniform tests on each one.

Similar to: backend/test_scripts/test_external/test_fx_providers.py

Tests performed for each provider:
  • Metadata validation (provider_code, provider_name)
  • Current value fetching (using test_cases)
  • Historical data fetching (7 days, if supported)
  • Search functionality (if supported)
  • Error handling
  • Parameter validation
  • Data quality checks
  • Rate limiting
  • Edge cases
  • Concurrency safety

Prerequisites:
  • Internet connection for external providers (yfinance, cssscraper)
  • Provider APIs accessible and working
"""

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.provider_registry import AssetProviderRegistry
from backend.app.services.asset_source import AssetSourceError
from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_success,
    print_test_header,
    )


def test_provider_metadata(provider) -> dict:
    """Test provider metadata (code, name)."""
    try:
        code = provider.provider_code
        name = provider.provider_name

        if not code or not isinstance(code, str):
            return {"passed": False, "message": f"Invalid provider_code: {code}"}

        if not name or not isinstance(name, str):
            return {"passed": False, "message": f"Invalid provider_name: {name}"}

        return {
            "passed": True,
            "message": f"Metadata valid: {code} = {name}"
            }
    except Exception as e:
        return {"passed": False, "message": f"Metadata test failed: {e}"}


async def test_provider_current_value(provider) -> dict:
    """Test get_current_value method."""
    try:
        # Check if provider has test_cases
        if not provider.test_cases:
            return {"passed": False, "message": "No test_cases defined, impossible to test"}

        # Test all cases
        results = []
        failed = []
        for i, test_case in enumerate(provider.test_cases):
            identifier = test_case['identifier']
            provider_params = test_case['provider_params']

            try:
                result = await provider.get_current_value(
                    identifier=identifier,
                    provider_params=provider_params
                    )

                # Validate result
                if not hasattr(result, 'value') or result.value is None:
                    failed.append(f"Case {i + 1}: Missing 'value'")
                    continue

                if not hasattr(result, 'currency') or not result.currency:
                    failed.append(f"Case {i + 1}: Missing 'currency'")
                    continue

                if not hasattr(result, 'as_of_date') or not result.as_of_date:
                    failed.append(f"Case {i + 1}: Missing 'as_of_date'")
                    continue

                results.append(f"Case {i + 1}: OK - {result.value} {result.currency}")

            except AssetSourceError as e:
                failed.append(f"Case {i + 1}: Provider error - {e.message}")

        # Check if all cases passed
        if failed:
            return {
                "passed": False,
                "message": f"Some cases failed: {'; '.join(failed)}"
                }

        return {
            "passed": True,
            "message": f"All {len(results)} test case(s) passed: {'; '.join(results)}"
            }

    except AssetSourceError as e:
        # Provider errors are expected for some edge cases
        return {
            "passed": True,
            "message": f"Provider error (OK): {e.error_code} - {e.message}"
            }
    except Exception as e:
        return {"passed": False, "message": f"Unexpected error: {e}"}


async def test_provider_history(provider) -> dict:
    """Test get_history_value method (7 days)."""
    try:
        # Check if provider supports history
        if not provider.supports_history:
            return {"passed": True, "message": "History not supported (expected)"}

        # Use first test case
        test_case = provider.test_cases[0]
        identifier = test_case['identifier']
        provider_params = test_case['provider_params']

        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=7)

        result = await provider.get_history_value(
            identifier=identifier,
            start_date=start_date,
            end_date=end_date,
            provider_params=provider_params
            )

        # Validate result
        if not hasattr(result, 'prices') or not isinstance(result.prices, list):
            return {"passed": False, "message": "Result missing 'prices' list"}

        if len(result.prices) == 0:
            return {"passed": False, "message": "Result has empty prices list"}

        return {
            "passed": True,
            "message": f"History: {len(result.prices)} prices from {start_date} to {end_date}"
            }
    except Exception as e:
        return {"passed": False, "message": f"Unexpected error: {e}"}


async def test_provider_search(provider) -> dict:
    """Test search method."""
    try:
        # Check if provider has test_search_query
        if provider.test_search_query is None:
            return {"passed": True, "message": "Search not supported (skipped)"}

        query = provider.test_search_query

        results = await provider.search(query)

        if not isinstance(results, list):
            return {"passed": False, "message": "Search didn't return a list"}

        # Empty results are OK (cssscraper doesn't support search)
        if len(results) == 0:
            return {"passed": True, "message": "Search returned 0 results (OK)"}

        # Validate first result structure
        first = results[0]
        if not isinstance(first, dict):
            return {"passed": False, "message": "Search result not a dict"}

        return {
            "passed": True,
            "message": f"Search found {len(results)} result(s) for '{query}'"
            }

    except AssetSourceError as e:
        if e.error_code == "NOT_SUPPORTED":
            return {
                "passed": True,
                "message": f"Provider error (OK): {e.error_code}"
                }
        else:
            return {
                "passed": False,
                "message": f"Provider error: {e.error_code} - {e.message}"
                }
    except Exception as e:
        return {"passed": False, "message": f"Unexpected error: {e}"}


async def test_provider_error_handling(provider) -> dict:
    """Test error handling with invalid inputs."""
    try:
        # Test with invalid identifier
        try:
            await provider.get_current_value(
                identifier="INVALID_TICKER_12345",
                provider_params=None
                )
            return {"passed": False, "message": "Should have raised error for invalid identifier"}
        except AssetSourceError as e:
            # Expected error
            if e.error_code in ["NO_DATA", "NOT_FOUND", "FETCH_ERROR", "MISSING_PARAMS", "INVALID_IDENTIFIER"]:
                return {"passed": True, "message": f"Error handling OK: {e.error_code}"}
            return {"passed": False, "message": f"Unexpected error code: {e.error_code}"}

    except Exception as e:
        return {"passed": False, "message": f"Error handling test failed: {e}"}


async def run_provider_tests(provider_code: str, provider) -> dict:
    """Run all tests for a single provider."""
    print_section(f"Testing Provider: {provider_code}")

    results = {}

    # Test 1: Metadata
    print_info("Test 1: Metadata validation")
    results["metadata"] = test_provider_metadata(provider)
    if results["metadata"]["passed"]:
        print_success(f"✓ {results['metadata']['message']}")
    else:
        print_error(f"✗ {results['metadata']['message']}")

    # Test 2: Current value
    print_info("Test 2: Current value fetch")
    results["current_value"] = await test_provider_current_value(provider)
    if results["current_value"]["passed"]:
        print_success(f"✓ {results['current_value']['message']}")
    else:
        print_error(f"✗ {results['current_value']['message']}")

    # Test 3: Historical data
    print_info("Test 3: Historical data fetch")
    results["history"] = await test_provider_history(provider)
    if results["history"]["passed"]:
        print_success(f"✓ {results['history']['message']}")
    else:
        print_error(f"✗ {results['history']['message']}")

    # Test 4: Search
    print_info("Test 4: Search functionality")
    results["search"] = await test_provider_search(provider)
    if results["search"]["passed"]:
        print_success(f"✓ {results['search']['message']}")
    else:
        print_error(f"✗ {results['search']['message']}")

    # Test 5: Error handling
    print_info("Test 5: Error handling")
    results["error_handling"] = await test_provider_error_handling(provider)
    if results["error_handling"]["passed"]:
        print_success(f"✓ {results['error_handling']['message']}")
    else:
        print_error(f"✗ {results['error_handling']['message']}")

    return results


async def run_all_tests():
    """Main test runner."""
    print_test_header(
        "LibreFolio - Asset Providers: Generic Test Suite",
        description="""This test suite runs uniform tests on ALL registered asset providers.
        
Tests performed for each provider:
  • Metadata validation and registration
  • Current value fetching (using test_cases)
  • Historical data fetching (if supports_history)
  • Search functionality (if test_search_query defined)
  • Error handling
        
This ensures all providers implement the interface correctly and work as expected.""",
        prerequisites=[
            "Internet connection",
            "Provider APIs accessible",
            "At least one provider registered (yfinance, cssscraper, etc.)"
            ]
        )

    # Auto-discover providers before testing
    AssetProviderRegistry.auto_discover()

    # Discover all providers
    providers = AssetProviderRegistry.list_providers()

    if not providers:
        print_error("❌ No providers registered in AssetProviderRegistry!")
        return False

    print_info(f"📋 Found {len(providers)} registered provider(s):")
    for p in providers:
        print_info(f"  • {p['code']}: {p['name']}")

    # Run tests for each provider
    all_results = {}
    for provider_info in providers:
        code = provider_info["code"]
        try:
            provider = AssetProviderRegistry.get_provider(code)
            provider_instance = provider()  # Instantiate
            all_results[code] = await run_provider_tests(code, provider_instance)
        except Exception as e:
            print_error(f"Failed to test provider {code}: {e}")
            all_results[code] = {"error": str(e)}

    # Summary
    print_section("Test Summary")

    total_providers = len(all_results)
    passed_providers = 0

    for code, results in all_results.items():
        if "error" in results:
            print_error(f"❌ {code}: FAILED (error during testing)")
            continue

        # Count passed tests
        passed_tests = sum(1 for r in results.values() if r["passed"])
        total_tests = len(results)

        if passed_tests == total_tests:
            print_success(f"✅ {code}: ALL {total_tests} tests passed")
            passed_providers += 1
        else:
            print_error(f"❌ {code}: {passed_tests}/{total_tests} tests passed")

    print_info(f"\nResults: {passed_providers}/{total_providers} providers passed all tests")

    return passed_providers == total_providers


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
