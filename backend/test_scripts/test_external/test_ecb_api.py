"""
Test 1: ECB API Connection and Currency List
Tests the connection to ECB API and fetching available currencies.
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.fx import FXServiceError, get_available_currencies
from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_success,
    print_test_header,
    print_test_summary,
    exit_with_result,
)


async def test_ecb_connection():
    """Test basic connection to ECB API."""
    print_section("Test 1: ECB API Connection")

    try:
        print_info("Connecting to ECB API...")
        currencies = await get_available_currencies()

        if not currencies:
            print_error("No currencies returned from ECB API")
            return False

        print_success(f"Successfully connected to ECB API")
        print_info(f"Found {len(currencies)} available currencies")
        return True

    except FXServiceError as e:
        print_error(f"ECB API error: {e}")
        return False
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_currency_list():
    """Test fetching and validating currency list."""
    print_section("Test 2: Currency List Validation")

    try:
        currencies = await get_available_currencies()

        # Verify common currencies are present
        expected_currencies = {
            "USD": "US Dollar",
            "GBP": "British Pound",
            "CHF": "Swiss Franc",
            "JPY": "Japanese Yen",
            "CAD": "Canadian Dollar",
            "AUD": "Australian Dollar",
            "EUR": "Euro (base currency)",
        }

        print_info("Checking for expected currencies...")
        missing = []
        for code, name in expected_currencies.items():
            if code in currencies:
                print_success(f"  {code} - {name}")
            else:
                print_error(f"  {code} - {name} (MISSING)")
                missing.append(code)

        if missing:
            print_error(f"Missing expected currencies: {', '.join(missing)}")
            return False

        # Show sample of other currencies
        other_currencies = sorted([c for c in currencies if c not in expected_currencies])
        if other_currencies:
            print_info(f"\nOther available currencies ({len(other_currencies)}):")
            print_info(f"  {', '.join(other_currencies[:20])}...")

        print_success(f"All expected currencies found")
        return True

    except Exception as e:
        print_error(f"Failed to validate currency list: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all ECB connection tests."""
    print_test_header(
        "LibreFolio - FX Service: ECB API Connection Tests",
        description="""These tests verify:
  • Connection to ECB (European Central Bank) API
  • Availability of currency data
  • Presence of common currencies""",
        prerequisites=[
            "Internet connection",
            "ECB API accessible (https://data-api.ecb.europa.eu)"
        ]
    )

    results = {
        "ECB API Connection": await test_ecb_connection(),
        "Currency List Validation": await test_currency_list(),
    }

    # Summary
    success = print_test_summary(results, "ECB API Connection Tests")

    if success:
        print_success("ECB API is accessible and working correctly! 🎉")
    else:
        print_error("Some tests failed. Check your internet connection or ECB API status.")

    return success


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit_with_result(success)
