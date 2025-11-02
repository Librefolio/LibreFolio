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

    # Test conversion: 100 USD to EUR (single item in bulk request)
    print_info("\nTesting conversion: 100 USD → EUR")

    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "USD",
                        "to": "EUR",
                        "date": end_date.isoformat()
                    }
                ]
            },
            timeout=TIMEOUT
            )

        print_info(f"Status code: {response.status_code}")

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()

        # Validate bulk response structure
        if "results" not in data or "errors" not in data:
            print_error("Invalid response structure (missing results or errors)")
            return False

        if len(data["results"]) != 1:
            print_error(f"Expected 1 result, got {len(data['results'])}")
            return False

        result = data["results"][0]

        # Validate result structure
        required_fields = ["amount", "from_currency", "to_currency", "converted_amount", "rate", "rate_date"]
        for field in required_fields:
            if field not in result:
                print_error(f"Missing field in result: {field}")
                return False

        print_success(f"Conversion successful")
        print_info(f"  {result['amount']} {result['from_currency']} = {result['converted_amount']} {result['to_currency']}")
        print_info(f"  Rate: {result['rate']}")
        print_info(f"  Rate date: {result['rate_date']}")

        # Test identity conversion (EUR → EUR)
        print_info("\nTesting identity conversion: 100 EUR → EUR")

        response2 = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "EUR",
                        "to": "EUR",
                        "date": end_date.isoformat()
                    }
                ]
            },
            timeout=TIMEOUT
            )

        if response2.status_code != 200:
            print_error("Identity conversion request failed")
            return False

        data2 = response2.json()
        result2 = data2["results"][0]

        if Decimal(str(result2["converted_amount"])) != Decimal("100.00"):
            print_error(f"Identity conversion failed: expected 100.00, got {result2['converted_amount']}")
            return False

        if result2["rate"] is not None:
            print_error(f"Identity conversion should have null rate, got {result2['rate']}")
            return False

        print_success("Identity conversion correct (rate=null, amount unchanged)")

        # Test roundtrip (USD → EUR → USD) - using bulk with 2 conversions
        print_info("\nTesting roundtrip: 100 USD → EUR → USD")

        # First get EUR amount
        response3 = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "USD",
                        "to": "EUR",
                        "date": end_date.isoformat()
                    }
                ]
            },
            timeout=TIMEOUT
            )

        if response3.status_code != 200:
            print_error("First conversion failed")
            return False

        eur_amount = response3.json()["results"][0]["converted_amount"]

        # Then convert back
        response4 = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "amount": str(eur_amount),
                        "from": "EUR",
                        "to": "USD",
                        "date": end_date.isoformat()
                    }
                ]
            },
            timeout=TIMEOUT
            )

        if response4.status_code != 200:
            print_error("Second conversion failed")
            return False

        final_usd = Decimal(str(response4.json()["results"][0]["converted_amount"]))
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
    """Test backward-fill behavior and warning for old dates."""
    print_section("Test 4: Backward-Fill Warning")

    # First, insert a rate for a date in the past (before requested date)
    old_rate_date = date(1999, 12, 15)
    requested_date = date(2000, 3, 20)  # 3 months after the rate

    print_info(f"Step 1: Insert rate for past date ({old_rate_date})")

    try:
        # Insert a manual rate (using bulk with single item)
        insert_response = httpx.post(
            f"{API_BASE_URL}/fx/rate",
            json={
                "rates": [
                    {
                        "date": old_rate_date.isoformat(),
                        "base": "EUR",
                        "quote": "USD",
                        "rate": "1.05000",
                        "source": "TEST"
                    }
                ]
            },
            timeout=TIMEOUT
        )

        if insert_response.status_code != 200:
            print_error(f"Failed to insert test rate: {insert_response.status_code}")
            return False

        print_success(f"Test rate inserted for {old_rate_date}")

        # Now request conversion for a later date (should use backward-fill)
        print_info(f"\nStep 2: Request conversion for later date ({requested_date})")
        print_info(f"Expected: 200 OK with backward_fill_info (using rate from {old_rate_date})")

        response = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "USD",
                        "to": "EUR",
                        "date": requested_date.isoformat()
                    }
                ]
            },
            timeout=TIMEOUT
            )

        print_info(f"Status code: {response.status_code}")

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()

        # Validate bulk response and extract first result
        if "results" not in data or len(data["results"]) == 0:
            print_error("Response missing results")
            return False

        result = data["results"][0]

        # Verify backward_fill_info is present
        if "backward_fill_info" not in result:
            print_error("Response missing backward_fill_info field")
            return False

        fill_info = result["backward_fill_info"]

        if fill_info is None:
            print_error("backward_fill_info should not be null for old date")
            return False

        # Verify structure
        required_fields = ["applied", "requested_date", "actual_rate_date", "days_back"]
        for field in required_fields:
            if field not in fill_info:
                print_error(f"backward_fill_info missing field: {field}")
                return False

        if not fill_info["applied"]:
            print_error("backward_fill_info.applied should be true")
            return False

        # Verify requested_date matches what we sent
        if fill_info["requested_date"] != requested_date.isoformat():
            print_error(f"requested_date mismatch: expected {requested_date.isoformat()}, got {fill_info['requested_date']}")
            return False

        # Verify actual_rate_date is <= requested_date
        from datetime import date as date_type
        actual_date = date_type.fromisoformat(fill_info["actual_rate_date"])
        requested_date_parsed = date_type.fromisoformat(fill_info["requested_date"])

        if actual_date > requested_date_parsed:
            print_error(f"actual_rate_date ({actual_date}) should be <= requested_date ({requested_date_parsed})")
            return False

        # Verify days_back calculation is correct
        expected_days_back = (requested_date_parsed - actual_date).days
        if fill_info["days_back"] != expected_days_back:
            print_error(f"days_back incorrect: expected {expected_days_back}, got {fill_info['days_back']}")
            return False

        print_success(f"✓ Backward-fill applied: {fill_info['days_back']} days back")
        print_info(f"  Requested: {fill_info['requested_date']} ✓")
        print_info(f"  Actual rate from: {fill_info['actual_rate_date']} ✓")
        print_info(f"  Days back calculation: correct ✓")
        print_success("Backward-fill warning works correctly with all validations passing")
        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_manual_rate_upsert():
    """Test POST /fx/rate endpoint for manual rate entry."""
    print_section("Test 4: Manual Rate Upsert")

    # Use a date far in the past to avoid interference from other rates
    test_date = date(2020, 1, 15)

    # Test 1: Insert new rate
    print_info("Test 4.1: Insert new manual rate")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/rate",
            json={
                "rates": [
                    {
                        "date": test_date.isoformat(),
                        "base": "EUR",
                        "quote": "USD",
                        "rate": "1.12345",
                        "source": "MANUAL"
                    }
                ]
            },
            timeout=TIMEOUT
        )

        print_info(f"Status code: {response.status_code}")

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()

        # Verify bulk response structure
        required_fields = ["results", "success_count", "errors"]
        for field in required_fields:
            if field not in data:
                print_error(f"Missing field in response: {field}")
                return False

        if len(data["results"]) != 1:
            print_error(f"Expected 1 result, got {len(data['results'])}")
            return False

        result = data["results"][0]

        # Verify result structure
        result_fields = ["success", "action", "rate", "date", "base", "quote"]
        for field in result_fields:
            if field not in result:
                print_error(f"Missing field in result: {field}")
                return False

        if not result["success"]:
            print_error("Operation reported as unsuccessful")
            return False

        if result["action"] not in ["inserted", "updated"]:
            print_error(f"Invalid action: {result['action']}")
            return False

        print_success(f"Rate {result['action']}: {result['base']}/{result['quote']} = {result['rate']} on {result['date']}")

        # Test 2: Update existing rate (upsert)
        print_info("\nTest 4.2: Update existing rate (upsert)")
        response2 = httpx.post(
            f"{API_BASE_URL}/fx/rate",
            json={
                "rates": [
                    {
                        "date": test_date.isoformat(),
                        "base": "EUR",
                        "quote": "USD",
                        "rate": "1.23456",  # Different rate
                        "source": "MANUAL_CORRECTED"
                    }
                ]
            },
            timeout=TIMEOUT
        )

        if response2.status_code != 200:
            print_error("Update request failed")
            return False

        data2 = response2.json()
        result2 = data2["results"][0]

        if result2["action"] != "updated":
            print_error(f"Expected action 'updated', got {result2['action']}")
            return False

        print_success(f"Rate updated: new value = {result2['rate']}")

        # Test 3: Verify rate is usable in conversion
        print_info("\nTest 4.3: Verify manual rate is used in conversion")
        response3 = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "EUR",
                        "to": "USD",
                        "date": test_date.isoformat()
                    }
                ]
            },
            timeout=TIMEOUT
        )

        if response3.status_code != 200:
            print_error("Conversion using manual rate failed")
            return False

        data3 = response3.json()
        result3 = data3["results"][0]
        expected_amount = Decimal("100.00") * Decimal(result2["rate"])
        actual_amount = Decimal(str(result3["converted_amount"]))

        if abs(actual_amount - expected_amount) > Decimal("0.01"):
            print_error(f"Conversion incorrect: expected {expected_amount}, got {actual_amount}")
            return False

        print_success("Manual rate correctly used in conversion")

        # Test 4: Invalid request (same base and quote)
        print_info("\nTest 4.4: Invalid request (base == quote)")
        response4 = httpx.post(
            f"{API_BASE_URL}/fx/rate",
            json={
                "rates": [
                    {
                        "date": test_date.isoformat(),
                        "base": "EUR",
                        "quote": "EUR",  # Same as base
                        "rate": "1.0",
                        "source": "MANUAL"
                    }
                ]
            },
            timeout=TIMEOUT
        )

        # Should return 200 with errors in response
        if response4.status_code == 200:
            data4 = response4.json()
            if len(data4["errors"]) == 0 or len(data4["results"]) > 0:
                print_error("Same base/quote was accepted (should have errors)")
                return False
            print_success(f"Same base/quote rejected with errors: {data4['errors'][0][:50]}...")
        else:
            print_success(f"Same base/quote rejected (status {response4.status_code})")

        # Test 5: Automatic alphabetical ordering and rate inversion
        print_info("\nTest 4.5: Automatic ordering (USD/EUR → EUR/USD with rate inversion)")
        response5 = httpx.post(
            f"{API_BASE_URL}/fx/rate",
            json={
                "rates": [
                    {
                        "date": test_date.isoformat(),
                        "base": "USD",  # Will be reordered to EUR/USD
                        "quote": "EUR",
                        "rate": "0.90000",  # 1 USD = 0.9 EUR
                        "source": "MANUAL"
                    }
                ]
            },
            timeout=TIMEOUT
        )

        if response5.status_code != 200:
            print_error("Rate with reverse ordering failed")
            return False

        data5 = response5.json()
        result5 = data5["results"][0]

        # Should be stored as EUR/USD
        if result5["base"] != "EUR" or result5["quote"] != "USD":
            print_error(f"Expected EUR/USD, got {result5['base']}/{result5['quote']}")
            return False

        # Rate should be inverted: 1/0.9 = 1.111...
        expected_rate = Decimal("1") / Decimal("0.90000")
        actual_rate = Decimal(str(result5["rate"]))

        if abs(actual_rate - expected_rate) > Decimal("0.001"):
            print_error(f"Rate not inverted correctly: expected ~{expected_rate}, got {actual_rate}")
            return False

        print_success(f"✓ Ordered as {result5['base']}/{result5['quote']}")
        print_success(f"✓ Rate inverted: {result5['rate']}")

        print_success("Manual rate upsert endpoint works correctly")
        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bulk_conversions():
    """Test bulk conversion with multiple items in single request."""
    print_section("Test 5: Bulk Conversions (Multiple Items)")

    # Ensure rates exist
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=7)

    try:
        httpx.post(
            f"{API_BASE_URL}/fx/sync",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": "USD,GBP,CHF"
            },
            timeout=TIMEOUT
        )
    except:
        pass

    # Test bulk conversion with 3 different conversions
    print_info("Test 5.1: Bulk convert 3 amounts in single request")

    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {"amount": "100.00", "from": "USD", "to": "EUR", "date": end_date.isoformat()},
                    {"amount": "200.00", "from": "GBP", "to": "EUR", "date": end_date.isoformat()},
                    {"amount": "300.00", "from": "CHF", "to": "EUR", "date": end_date.isoformat()},
                ]
            },
            timeout=TIMEOUT
        )

        print_info(f"Status code: {response.status_code}")

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            return False

        data = response.json()

        if len(data["results"]) != 3:
            print_error(f"Expected 3 results, got {len(data['results'])}")
            return False

        print_success(f"✓ Bulk conversion successful: {len(data['results'])} conversions")

        # Verify all conversions have correct source currencies
        expected_from = ["USD", "GBP", "CHF"]
        for idx, result in enumerate(data["results"]):
            if result["from_currency"] != expected_from[idx]:
                print_error(f"Result {idx}: Expected from={expected_from[idx]}, got {result['from_currency']}")
                return False

        print_success("✓ All conversions have correct currencies")
        print_info(f"  100 USD = {data['results'][0]['converted_amount']} EUR")
        print_info(f"  200 GBP = {data['results'][1]['converted_amount']} EUR")
        print_info(f"  300 CHF = {data['results'][2]['converted_amount']} EUR")

        # Test bulk with mixed success/failure
        print_info("\nTest 5.2: Bulk with one invalid currency (partial failure)")

        response2 = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {"amount": "100.00", "from": "USD", "to": "EUR", "date": end_date.isoformat()},
                    {"amount": "200.00", "from": "XXX", "to": "EUR", "date": end_date.isoformat()},  # Invalid
                ]
            },
            timeout=TIMEOUT
        )

        if response2.status_code != 200:
            print_error(f"Expected status 200 (partial success), got {response2.status_code}")
            return False

        data2 = response2.json()

        # Should have 1 result and 1 error
        if len(data2["results"]) != 1:
            print_error(f"Expected 1 successful result, got {len(data2['results'])}")
            return False

        if len(data2["errors"]) != 1:
            print_error(f"Expected 1 error, got {len(data2['errors'])}")
            return False

        print_success("✓ Partial failure handled correctly")
        print_info(f"  Successful: {data2['results'][0]['from_currency']} → {data2['results'][0]['to_currency']}")
        print_info(f"  Failed: {data2['errors'][0][:60]}...")

        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bulk_rate_upserts():
    """Test bulk rate upsert with multiple items in single request."""
    print_section("Test 6: Bulk Rate Upserts (Multiple Items)")

    test_date = date(2019, 6, 15)

    print_info("Test 6.1: Bulk upsert 3 rates in single request")

    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/rate",
            json={
                "rates": [
                    {"date": test_date.isoformat(), "base": "EUR", "quote": "USD", "rate": "1.12", "source": "TEST"},
                    {"date": test_date.isoformat(), "base": "EUR", "quote": "GBP", "rate": "0.88", "source": "TEST"},
                    {"date": test_date.isoformat(), "base": "CHF", "quote": "USD", "rate": "1.15", "source": "TEST"},
                ]
            },
            timeout=TIMEOUT
        )

        print_info(f"Status code: {response.status_code}")

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            return False

        data = response.json()

        if data["success_count"] != 3:
            print_error(f"Expected 3 successful upserts, got {data['success_count']}")
            return False

        if len(data["results"]) != 3:
            print_error(f"Expected 3 results, got {len(data['results'])}")
            return False

        print_success(f"✓ Bulk upsert successful: {data['success_count']} rates inserted/updated")

        for result in data["results"]:
            print_info(f"  {result['action']}: {result['base']}/{result['quote']} = {result['rate']}")

        # Test bulk with one invalid (base==quote)
        print_info("\nTest 6.2: Bulk with one invalid rate (partial failure)")

        response2 = httpx.post(
            f"{API_BASE_URL}/fx/rate",
            json={
                "rates": [
                    {"date": test_date.isoformat(), "base": "EUR", "quote": "JPY", "rate": "130.0", "source": "TEST"},
                    {"date": test_date.isoformat(), "base": "EUR", "quote": "EUR", "rate": "1.0", "source": "TEST"},  # Invalid
                ]
            },
            timeout=TIMEOUT
        )

        if response2.status_code != 200:
            print_error(f"Expected status 200 (partial success), got {response2.status_code}")
            return False

        data2 = response2.json()

        # Should have 1 success and 1 error
        if data2["success_count"] != 1:
            print_error(f"Expected 1 successful upsert, got {data2['success_count']}")
            return False

        if len(data2["errors"]) != 1:
            print_error(f"Expected 1 error, got {len(data2['errors'])}")
            return False

        print_success("✓ Partial failure handled correctly")
        print_info(f"  Successful: {data2['results'][0]['base']}/{data2['results'][0]['quote']}")
        print_info(f"  Failed: {data2['errors'][0][:60]}...")

        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_invalid_requests():
    """Test comprehensive validation and error handling for invalid requests."""
    print_section("Test 5: Invalid Request Handling")

    all_ok = True

    # Test 1: Invalid date range (start > end) with error detail check
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
            data = response.json()
            if "detail" in data:
                print_success(f"Invalid date range rejected (status {response.status_code})")
                print_info(f"  Error message: {data['detail']}")
            else:
                print_error("Response missing 'detail' field")
                all_ok = False
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    # Test 2: Negative amount (POST bulk)
    print_info("\nTest 5.2: Negative amount")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "amount": "-100.00",
                        "from": "USD",
                        "to": "EUR",
                        "date": date.today().isoformat()
                    }
                ]
            },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Negative amount was accepted (should return 422)")
            all_ok = False
        else:
            print_success(f"Negative amount rejected (status {response.status_code})")
            data = response.json()
            if "detail" in data:
                print_info(f"  Error message: {str(data['detail'])[:80]}...")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    # Test 3: Zero amount
    print_info("\nTest 5.3: Zero amount")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "amount": "0",
                        "from": "USD",
                        "to": "EUR",
                        "date": date.today().isoformat()
                    }
                ]
            },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Zero amount was accepted (should return 422)")
            all_ok = False
        else:
            print_success(f"Zero amount rejected (status {response.status_code})")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    # Test 4: Non-numeric amount
    print_info("\nTest 5.4: Non-numeric amount (abc)")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "amount": "abc",
                        "from": "USD",
                        "to": "EUR",
                        "date": date.today().isoformat()
                    }
                ]
            },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Non-numeric amount was accepted (should return 422)")
            all_ok = False
        else:
            print_success(f"Non-numeric amount rejected (status {response.status_code})")
            data = response.json()
            if "detail" in data:
                print_info(f"  Error message: validation error detected")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    # Test 5: Invalid currency code format (too long)
    print_info("\nTest 5.5: Invalid currency code format (INVALID)")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "INVALID",
                        "to": "EUR",
                        "date": date.today().isoformat()
                    }
                ]
            },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            data = response.json()
            # Check if errors in response
            if len(data.get("errors", [])) == 0:
                print_error("Invalid currency code was accepted")
                all_ok = False
            else:
                print_success(f"Invalid currency code rejected with errors")
        else:
            print_success(f"Invalid currency code rejected (status {response.status_code})")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    # Test 6: Valid but unsupported currency code
    print_info("\nTest 5.6: Valid format but unsupported currency (XXX)")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "XXX",
                        "to": "EUR",
                        "date": date.today().isoformat()
                    }
                ]
            },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            data = response.json()
            # Check if errors in response
            if len(data.get("errors", [])) == 0:
                print_error("Unsupported currency XXX was accepted")
                all_ok = False
            else:
                print_success(f"Unsupported currency rejected with errors")
        else:
            print_success(f"Unsupported currency rejected (status {response.status_code})")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    # Test 7: Empty conversions array
    print_info("\nTest 5.7: Empty conversions array")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": []  # Empty array
            },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Empty conversions was accepted (should return 422)")
            all_ok = False
        else:
            print_success(f"Empty conversions rejected (status {response.status_code})")
            data = response.json()
            if "detail" in data:
                print_info(f"  Error indicates validation failure")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    # Test 8: Missing required field in conversion (amount)
    print_info("\nTest 5.8: Missing required field in conversion (amount)")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert",
            json={
                "conversions": [
                    {
                        "from": "USD",
                        "to": "EUR",
                        # amount is missing
                    }
                ]
            },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Request with missing amount was accepted (should return 422)")
            all_ok = False
        else:
            print_success(f"Missing required field rejected (status {response.status_code})")
    except Exception as e:
        print_error(f"Request failed: {e}")
        all_ok = False

    # Test 9: Empty currency string
    print_info("\nTest 5.9: Empty currency string in sync")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/sync",
            params={
                "start": date.today().isoformat(),
                "end": date.today().isoformat(),
                "currencies": ""  # Empty string
                },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Empty currencies was accepted (should return 400)")
            all_ok = False
        else:
            print_success(f"Empty currencies rejected (status {response.status_code})")
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
  • POST /fx/convert - Convert currencies (bulk-only, single = 1 item array)
  • POST /fx/rate - Manually insert/update rates (bulk-only, single = 1 item array)
  • Backward-fill warnings for old dates
  • Bulk operations with multiple items
  • Partial failure handling
  • Comprehensive error handling and validation""",
        prerequisites=[
            "Services FX conversion subsystem (run: python test_runner.py services fx)",
            "Test server will be started automatically on TEST_PORT",
            "Test server will be stopped automatically at end"
            ]
        )

    # Use context manager for server - will start and stop automatically
    with TestServerManager() as server_manager:
        print_section("Backend Server Management")

        # Show database and port info
        from backend.app.config import get_settings
        settings = get_settings()
        test_port = settings.TEST_PORT

        print_info(f"Database: {settings.DATABASE_URL}")
        print_info(f"Test server port: {test_port}")
        print_info(f"API base URL: {API_BASE_URL}")

        print_info(f"\nStarting test server...")

        if not server_manager.start_server():
            print_error("Failed to start backend server")
            print_info(f"Check if port {test_port} is available")
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
        "POST /fx/convert (Single)": test_convert_currency(),
        "POST /fx/rate (Single)": test_manual_rate_upsert(),
        "Backward-Fill Warning": test_convert_missing_rate(),
        "POST /fx/convert (Bulk)": test_bulk_conversions(),
        "POST /fx/rate (Bulk)": test_bulk_rate_upserts(),
        "Invalid Request Handling": test_invalid_requests(),
        }

    # Summary
    success = print_test_summary(results, "FX API Endpoint Tests")
    return success


if __name__ == "__main__":
    success = run_all_tests()
    exit_with_result(success)
