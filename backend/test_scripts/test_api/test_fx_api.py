"""
Test FX API Endpoints
Tests REST API endpoints for FX functionality.
Auto-starts backend server if not running and stops it after tests.
"""
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import httpx

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from backend.test_scripts.test_server_helper import TestServerManager, TEST_API_BASE_URL
from backend.test_scripts.test_utils import (
    print_error,
    print_info,
    print_section,
    print_success,
    print_test_header,
    print_test_summary,
    exit_with_result,
    )

# Configuration - use test server port
API_BASE_URL = TEST_API_BASE_URL  # http://localhost:8001/api/v1 (test port)
TIMEOUT = 30.0


def test_get_currencies():
    """Test GET /fx/currencies endpoint."""
    print_section("Test 1: GET /fx/currencies")

    try:
        response = httpx.get(f"{API_BASE_URL}/fx/currencies", timeout=TIMEOUT)

        print_info(f"Status code: {response.status_code}")

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()

        # Validate response structure
        if "currencies" not in data or "count" not in data:
            print_error("Invalid response structure")
            print_error(f"Response: {data}")
            return False

        currencies = data["currencies"]
        count = data["count"]

        print_success(f"Found {count} currencies")
        print_info(f"Sample: {', '.join(currencies[:10])}...")

        # Verify expected currencies
        expected = {"EUR", "USD", "GBP", "CHF", "JPY"}
        missing = expected - set(currencies)

        if missing:
            print_error(f"Missing expected currencies: {missing}")
            return False

        print_success("All expected currencies present")
        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sync_rates():
    """Test POST /fx/sync endpoint."""
    print_section("Test 2: POST /fx/sync")

    # Sync last 7 days for USD and GBP
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=7)
    currencies = "USD,GBP"

    print_info(f"Date range: {start_date} to {end_date}")
    print_info(f"Currencies: {currencies}")

    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/sync",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": currencies
                },
            timeout=TIMEOUT
            )

        print_info(f"Status code: {response.status_code}")

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()

        # Validate response structure
        required_fields = ["synced", "date_range", "currencies"]
        for field in required_fields:
            if field not in data:
                print_error(f"Missing field in response: {field}")
                return False

        print_success(f"Synced {data['synced']} rates")
        print_info(f"Date range: {data['date_range']}")
        print_info(f"Currencies: {data['currencies']}")

        # Sync again (should return 0 new rates - idempotency)
        print_info("\nTesting idempotency (sync again)...")
        response2 = httpx.post(
            f"{API_BASE_URL}/fx/sync",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": currencies
                },
            timeout=TIMEOUT
            )

        if response2.status_code != 200:
            print_error("Second sync request failed")
            return False

        data2 = response2.json()

        if data2["synced"] != 0:
            print_error(f"Second sync returned {data2['synced']} rates (expected 0)")
            return False

        print_success("Idempotency verified (second sync returned 0 new rates)")
        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_convert_currency():
    """Test GET /fx/convert endpoint."""
    print_section("Test 3: GET /fx/convert")

    # First, ensure we have rates
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=7)

    print_info("Ensuring rates exist...")
    try:
        httpx.post(
            f"{API_BASE_URL}/fx/sync",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": "USD,GBP"
                },
            timeout=TIMEOUT
            )
    except:
        pass  # Ignore errors, may already exist

    # Test conversion: 100 USD to EUR
    print_info("\nTesting conversion: 100 USD → EUR")

    try:
        response = httpx.get(
            f"{API_BASE_URL}/fx/convert",
            params={
                "amount": "100.00",
                "from": "USD",
                "to": "EUR",
                "date": end_date.isoformat()
                },
            timeout=TIMEOUT
            )

        print_info(f"Status code: {response.status_code}")

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()

        # Validate response structure
        required_fields = ["amount", "from_currency", "to_currency", "converted_amount", "rate", "rate_date"]
        for field in required_fields:
            if field not in data:
                print_error(f"Missing field in response: {field}")
                return False

        print_success(f"Conversion successful")
        print_info(f"  {data['amount']} {data['from_currency']} = {data['converted_amount']} {data['to_currency']}")
        print_info(f"  Rate: {data['rate']}")
        print_info(f"  Rate date: {data['rate_date']}")

        # Test identity conversion (EUR → EUR)
        print_info("\nTesting identity conversion: 100 EUR → EUR")

        response2 = httpx.get(
            f"{API_BASE_URL}/fx/convert",
            params={
                "amount": "100.00",
                "from": "EUR",
                "to": "EUR",
                "date": end_date.isoformat()
                },
            timeout=TIMEOUT
            )

        if response2.status_code != 200:
            print_error("Identity conversion request failed")
            return False

        data2 = response2.json()

        if Decimal(str(data2["converted_amount"])) != Decimal("100.00"):
            print_error(f"Identity conversion failed: expected 100.00, got {data2['converted_amount']}")
            return False

        if data2["rate"] is not None:
            print_error(f"Identity conversion should have null rate, got {data2['rate']}")
            return False

        print_success("Identity conversion correct (rate=null, amount unchanged)")

        # Test roundtrip (USD → EUR → USD)
        print_info("\nTesting roundtrip: 100 USD → EUR → USD")

        # USD → EUR
        response3 = httpx.get(
            f"{API_BASE_URL}/fx/convert",
            params={
                "amount": "100.00",
                "from": "USD",
                "to": "EUR",
                "date": end_date.isoformat()
                },
            timeout=TIMEOUT
            )

        if response3.status_code != 200:
            print_error("First conversion failed")
            return False

        eur_amount = response3.json()["converted_amount"]

        # EUR → USD
        response4 = httpx.get(
            f"{API_BASE_URL}/fx/convert",
            params={
                "amount": str(eur_amount),
                "from": "EUR",
                "to": "USD",
                "date": end_date.isoformat()
                },
            timeout=TIMEOUT
            )

        if response4.status_code != 200:
            print_error("Second conversion failed")
            return False

        final_usd = Decimal(str(response4.json()["converted_amount"]))
        difference = abs(final_usd - Decimal("100.00"))

        print_info(f"  100 USD → {eur_amount} EUR → {final_usd} USD")
        print_info(f"  Difference: {difference} USD")

        if difference > Decimal("0.01"):
            print_error(f"Roundtrip failed: difference {difference} > 0.01")
            return False

        print_success("Roundtrip conversion successful")
        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_convert_missing_rate():
    """Test error handling when rate is not available."""
    print_section("Test 4: Missing Rate Error Handling")

    # Try to convert with a very old date (no rate should exist)
    old_date = date(2000, 1, 1)

    print_info(f"Attempting conversion for old date: {old_date}")
    print_info("Expected: 404 error")

    try:
        response = httpx.get(
            f"{API_BASE_URL}/fx/convert",
            params={
                "amount": "100.00",
                "from": "USD",
                "to": "EUR",
                "date": old_date.isoformat()
                },
            timeout=TIMEOUT
            )

        print_info(f"Status code: {response.status_code}")

        if response.status_code != 404:
            print_error(f"Expected status 404, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()
        print_info(f"Error message: {data.get('detail', 'No detail')}")

        print_success("Missing rate correctly returns 404 error")
        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_invalid_requests():
    """Test validation and error handling for invalid requests."""
    print_section("Test 5: Invalid Request Handling")

    all_ok = True

    # Test 1: Invalid date range (start > end)
    print_info("Test 5.1: Invalid date range (start > end)")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/sync",
            params={
                "start": "2025-01-10",
                "end": "2025-01-01",
                "currencies": "USD"
                },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Invalid date range was accepted (should return 400)")
            all_ok = False
        else:
            print_success(f"Invalid date range rejected (status {response.status_code})")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    # Test 2: Negative amount
    print_info("\nTest 5.2: Negative amount")
    try:
        response = httpx.get(
            f"{API_BASE_URL}/fx/convert",
            params={
                "amount": "-100.00",
                "from": "USD",
                "to": "EUR",
                "date": date.today().isoformat()
                },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Negative amount was accepted (should return 422)")
            all_ok = False
        else:
            print_success(f"Negative amount rejected (status {response.status_code})")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    # Test 3: Invalid currency code
    print_info("\nTest 5.3: Invalid currency code")
    try:
        response = httpx.get(
            f"{API_BASE_URL}/fx/convert",
            params={
                "amount": "100.00",
                "from": "INVALID",
                "to": "EUR",
                "date": date.today().isoformat()
                },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Invalid currency code was accepted")
            all_ok = False
        else:
            print_success(f"Invalid currency code rejected (status {response.status_code})")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    return all_ok


def run_all_tests():
    """Run all FX API tests."""
    print_test_header(
        "LibreFolio - FX API Endpoint Tests",
        description="""These tests verify:
  • GET /fx/currencies - List available currencies
  • POST /fx/sync - Sync FX rates from ECB
  • GET /fx/convert - Convert between currencies
  • Error handling and validation""",
        prerequisites=[
            "Services FX conversion subsystem (run: python test_runner.py services fx)",
            "Test server will be started automatically on TEST_PORT",
            "Test server will be stopped automatically at end"
            ]
        )

    # Use context manager for server - will start and stop automatically
    with TestServerManager() as server_manager:
        print_section("Backend Server Management")

        print_info(f"Starting test server on port {server_manager.health_url.split(':')[2].split('/')[0]}...")

        if not server_manager.start_server():
            print_error("Failed to start backend server")
            print_info(f"Check if port {TEST_API_BASE_URL.split(':')[2].split('/')[0]} is available")
            return False

        print_success("Test server started successfully")

        # Run tests
        result = _run_tests()

        print_info("Stopping test server...")
        return result


def _run_tests():
    """Internal function to run actual tests."""
    results = {
        "GET /fx/currencies": test_get_currencies(),
        "POST /fx/sync": test_sync_rates(),
        "GET /fx/convert": test_convert_currency(),
        "Missing Rate Error": test_convert_missing_rate(),
        "Invalid Request Handling": test_invalid_requests(),
        }

    # Summary
    success = print_test_summary(results, "FX API Endpoint Tests")
    return success


if __name__ == "__main__":
    success = run_all_tests()
    exit_with_result(success)
