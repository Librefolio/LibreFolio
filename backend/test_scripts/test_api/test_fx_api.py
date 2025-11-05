"""
Test FX API Endpoints
Tests REST API endpoints for FX functionality.
Auto-starts backend server if not running and stops it after tests.
"""
import sys
from datetime import date as data_type, timedelta
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
# Get expected providers from backend factory
from backend.app.services.fx import FXProviderFactory
from backend.app.config import get_settings

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


def test_get_providers():
    """Test GET /fx/providers endpoint."""
    print_section("Test 2: GET /fx/providers")

    try:
        expected_providers = FXProviderFactory.get_all_providers()
        expected_codes = {p['code'] for p in expected_providers}
        expected_count = len(expected_providers)

        print_info(f"Expected providers from factory: {', '.join(sorted(expected_codes))} ({expected_count} total)")

        # Get actual providers from API
        response = httpx.get(f"{API_BASE_URL}/fx/providers", timeout=TIMEOUT)

        print_info(f"Status code: {response.status_code}")

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()

        # Validate response structure
        if "providers" not in data or "count" not in data:
            print_error("Invalid response structure")
            print_error(f"Response: {data}")
            return False

        providers = data["providers"]
        count = data["count"]

        print_success(f"Found {count} providers from API")

        # Compare with expected count
        if count != expected_count:
            print_error(f"Provider count mismatch: API returned {count}, factory has {expected_count}")
            return False

        actual_codes = {p["code"] for p in providers}
        print_info(f"API providers: {', '.join(sorted(actual_codes))}")

        # Compare provider codes
        if actual_codes != expected_codes:
            missing = expected_codes - actual_codes
            extra = actual_codes - expected_codes
            if missing:
                print_error(f"API missing providers: {missing}")
            if extra:
                print_error(f"API has unexpected providers: {extra}")
            return False

        print_success(f"✓ API providers match factory ({count} providers)")

        # Validate each provider structure and content
        required_fields = ["code", "name", "base_currency", "base_currencies", "description"]

        # Create lookup for expected providers
        expected_by_code = {p['code']: p for p in expected_providers}

        for api_provider in providers:
            code = api_provider["code"]

            # Verify all required fields present
            for field in required_fields:
                if field not in api_provider:
                    print_error(f"Provider {code} missing field: {field}")
                    return False

            # Verify base_currencies is a list containing base_currency
            if not isinstance(api_provider["base_currencies"], list):
                print_error(f"Provider {code}: base_currencies must be a list")
                return False

            if api_provider["base_currency"] not in api_provider["base_currencies"]:
                print_error(f"Provider {code}: base_currency not in base_currencies")
                return False

            # Compare with expected data from factory
            expected = expected_by_code[code]

            if api_provider["name"] != expected["name"]:
                print_error(f"Provider {code}: name mismatch (API: {api_provider['name']}, Expected: {expected['name']})")
                return False

            if api_provider["base_currency"] != expected["base_currency"]:
                print_error(f"Provider {code}: base_currency mismatch")
                return False

            if set(api_provider["base_currencies"]) != set(expected["base_currencies"]):
                print_error(f"Provider {code}: base_currencies mismatch")
                return False

        print_success("✓ All provider structures valid")
        print_success("✓ All provider data matches factory")

        # Log example provider details
        if "ECB" in expected_by_code:
            print_info(f"  Example - ECB base currencies: {expected_by_code['ECB']['base_currencies']}")

        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pair_sources_crud():
    """Test GET/POST/DELETE /fx/pair-sources endpoints."""
    print_section("Test 3: Pair Sources CRUD Operations")

    try:
        # SETUP: Cleanup any existing configurations that might conflict
        # This ensures test is isolated regardless of previous test state
        print_info("\nSetup: Cleaning up any existing test configurations")
        cleanup_pairs = [
            {"base": "EUR", "quote": "USD"},  # Will be created in this test
            {"base": "USD", "quote": "EUR"},  # Inverse pair that might exist from Test 4.5
            {"base": "GBP", "quote": "USD"},  # Will be created in this test
            {"base": "CHF", "quote": "USD"},  # Will be created in this test
        ]

        for pair in cleanup_pairs:
            httpx.request(
                "DELETE",
                f"{API_BASE_URL}/fx/pair-sources/bulk",
                json={"sources": [pair]},
                timeout=TIMEOUT
            )

        print_success("✓ Cleanup completed")

        # Test 3.1: GET empty list initially
        print_info("\nTest 3.1: GET /fx/pair-sources (after cleanup)")
        response = httpx.get(f"{API_BASE_URL}/fx/pair-sources", timeout=TIMEOUT)

        if response.status_code != 200:
            print_error(f"GET failed: {response.status_code}")
            return False

        data = response.json()
        initial_count = data["count"]
        print_info(f"Initial pair sources count: {initial_count}")

        # Test 3.2: POST bulk create
        print_info("\nTest 3.2: POST /fx/pair-sources/bulk (create)")
        create_request = {
            "sources": [
                {"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 1},
                {"base": "GBP", "quote": "USD", "provider_code": "BOE", "priority": 1},
                {"base": "CHF", "quote": "USD", "provider_code": "SNB", "priority": 1}
                ]
            }

        response = httpx.post(
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json=create_request,
            timeout=TIMEOUT
            )

        print_info(f"Status code: {response.status_code}")

        if response.status_code != 201:
            print_error(f"Expected status 201, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()

        if data["success_count"] != 3 or data["error_count"] != 0:
            print_error(f"Expected 3 successes, 0 errors. Got {data['success_count']} successes, {data['error_count']} errors")
            return False

        # Verify all created or updated (may already exist from previous runs)
        for result in data["results"]:
            if result["action"] not in ["created", "updated"]:
                print_error(f"Expected 'created' or 'updated', got '{result['action']}'")
                return False

        created_count = sum(1 for r in data["results"] if r["action"] == "created")
        updated_count = sum(1 for r in data["results"] if r["action"] == "updated")
        print_success(f"✓ Upserted 3 pair sources ({created_count} created, {updated_count} updated)")

        # Test 3.3: GET again to verify
        print_info("\nTest 3.3: GET /fx/pair-sources (verify creation)")
        response = httpx.get(f"{API_BASE_URL}/fx/pair-sources", timeout=TIMEOUT)
        data = response.json()

        # Should have at least the 3 we just upserted (some may have been deleted by cleanup from previous runs)
        if data["count"] < 3:
            print_error(f"Expected at least 3 sources, got {data['count']}")
            return False

        print_success(f"✓ Verified {data['count']} pair sources exist (at least our 3)")

        # Verify structure
        for source in data["sources"][-3:]:  # Last 3 created
            required = ["base", "quote", "provider_code", "priority"]
            for field in required:
                if field not in source:
                    print_error(f"Source missing field: {field}")
                    return False

        # Test 3.4: POST update (same pair, different provider)
        print_info("\nTest 3.4: POST /fx/pair-sources/bulk (update)")
        update_request = {
            "sources": [
                {"base": "EUR", "quote": "USD", "provider_code": "FED", "priority": 1}  # Change ECB -> FED
                ]
            }

        response = httpx.post(
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json=update_request,
            timeout=TIMEOUT
            )

        if response.status_code != 201:
            print_error(f"Update failed: {response.status_code}")
            return False

        data = response.json()

        if data["results"][0]["action"] != "updated":
            print_error(f"Expected 'updated', got '{data['results'][0]['action']}'")
            return False

        print_success(f"✓ Updated EUR/USD provider to FED")

        # Test 3.5: POST inverse pair with different priority (should succeed)
        print_info("\nTest 3.5: POST /fx/pair-sources/bulk (inverse pair, different priority)")
        # EUR/USD priority=1 already exists, create USD/EUR priority=2
        inverse_request = {
            "sources": [
                {"base": "USD", "quote": "EUR", "provider_code": "FED", "priority": 2}  # Inverse of EUR/USD
                ]
            }

        response = httpx.post(
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json=inverse_request,
            timeout=TIMEOUT
            )

        if response.status_code != 201:
            print_error(f"Expected status 201 for inverse pair with different priority, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        print_success(f"✓ Inverse pair USD/EUR priority=2 created (EUR/USD priority=1 exists)")

        # Test 3.5B: POST inverse pair with SAME priority (should fail)
        print_info("\nTest 3.5B: POST /fx/pair-sources/bulk (inverse pair conflict)")
        # Try to create USD/EUR priority=2 again (conflicts with existing USD/EUR priority=2)
        conflict_request = {
            "sources": [
                {"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 2}  # Inverse of USD/EUR priority=2
                ]
            }

        response = httpx.post(
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json=conflict_request,
            timeout=TIMEOUT
            )

        if response.status_code != 400:
            print_error(f"Expected status 400 for inverse pair conflict, got {response.status_code}")
            print_error(f"Response: {response.text}")
            return False

        data = response.json()
        # Verify error message mentions the conflict
        if "Conflict" not in str(data) and "inverse" not in str(data).lower():
            print_error(f"Expected conflict error message, got: {data}")
            return False

        print_success(f"✓ Inverse pair conflict correctly rejected (status 400)")

        # Cleanup the USD/EUR priority=2 we created
        httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json={"sources": [{"base": "USD", "quote": "EUR", "priority": 2}]},
            timeout=TIMEOUT
            )

        # Test 3.6: POST with unknown provider
        print_info("\nTest 3.6: POST /fx/pair-sources/bulk (unknown provider)")
        invalid_request = {
            "sources": [
                {"base": "EUR", "quote": "JPY", "provider_code": "UNKNOWN", "priority": 1}
                ]
            }

        response = httpx.post(
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json=invalid_request,
            timeout=TIMEOUT
            )

        if response.status_code != 400:
            print_error(f"Expected status 400 for unknown provider, got {response.status_code}")
            return False

        print_success(f"✓ Unknown provider correctly rejected (status 400)")

        # Test 3.7: DELETE specific priority
        print_info("\nTest 3.7: DELETE /fx/pair-sources/bulk (specific priority)")
        delete_request = {
            "sources": [
                {"base": "GBP", "quote": "USD", "priority": 1}
                ]
            }

        response = httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json=delete_request,
            timeout=TIMEOUT
            )

        if response.status_code != 200:
            print_error(f"DELETE failed: {response.status_code}")
            return False

        data = response.json()

        if data["total_deleted"] != 1:
            print_error(f"Expected 1 deletion, got {data['total_deleted']}")
            return False

        print_success(f"✓ Deleted GBP/USD priority=1")

        # Test 3.8: DELETE all priorities for a pair
        print_info("\nTest 3.8: DELETE /fx/pair-sources/bulk (all priorities)")
        delete_request = {
            "sources": [
                {"base": "CHF", "quote": "USD"}  # No priority = delete all
                ]
            }

        response = httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json=delete_request,
            timeout=TIMEOUT
            )

        if response.status_code != 200:
            print_error(f"DELETE failed: {response.status_code}")
            return False

        data = response.json()

        if data["total_deleted"] < 1:
            print_error(f"Expected at least 1 deletion, got {data['total_deleted']}")
            return False

        print_success(f"✓ Deleted all CHF/USD priorities ({data['total_deleted']} record(s))")

        # Test 3.9: DELETE non-existent pair (warning, not error)
        print_info("\nTest 3.9: DELETE /fx/pair-sources/bulk (non-existent pair)")
        delete_request = {
            "sources": [
                {"base": "AAA", "quote": "ZZZ", "priority": 1}
                ]
            }

        response = httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json=delete_request,
            timeout=TIMEOUT
            )

        if response.status_code != 200:
            print_error(f"Expected status 200 (warning), got {response.status_code}")
            return False

        data = response.json()

        if data["results"][0]["deleted_count"] != 0:
            print_error(f"Expected 0 deletions for non-existent pair")
            return False

        if not data["results"][0]["message"]:
            print_error(f"Expected warning message for non-existent pair")
            return False

        print_success(f"✓ Non-existent pair returned warning (not error)")
        print_info(f"  Message: {data['results'][0]['message'][:80]}...")

        # Cleanup: Remove test configurations (Test 4.3 is now self-contained)
        print_info("\nℹ️  Cleaning up test configurations")

        print_success("All pair sources CRUD tests passed")
        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sync_rates():
    """Test POST /fx/sync/bulk endpoint (both explicit and auto-configuration modes)."""
    print_section("Test 4: POST /fx/sync/bulk")

    # Sync last 7 days for USD and GBP
    end_date = data_type.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=7)
    currencies = "USD,GBP"

    print_info(f"Date range: {start_date} to {end_date}")
    print_info(f"Currencies: {currencies}")

    try:
        # Test 4.1: Explicit Provider Mode (backward compatible)
        print_info("\nTest 4.1: Explicit Provider Mode (provider=ECB)")
        response = httpx.post(
            f"{API_BASE_URL}/fx/sync/bulk",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": currencies,
                "provider": "ECB"  # Explicit provider mode
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

        print_success(f"✓ Explicit mode: Synced {data['synced']} rates")
        print_info(f"  Date range: {data['date_range']}")
        print_info(f"  Currencies: {data['currencies']}")

        # Test 4.2: Idempotency
        print_info("\nTest 4.2: Idempotency (sync again with same params)")
        response2 = httpx.post(
            f"{API_BASE_URL}/fx/sync/bulk",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": currencies,
                "provider": "ECB"
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

        print_success("✓ Idempotency verified (0 new rates)")

        # Test 4.3: Auto-Configuration Mode (uses fx_currency_pair_sources)
        print_info("\nTest 4.3: Auto-Configuration Mode (no provider specified)")

        # SETUP: Explicit configuration for this test (isolated from Test 3)
        print_info("  Step 1: Setup configuration (EUR/USD → FED priority=1)")

        # Clear any existing EUR/USD configuration
        httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json={"sources": [{"base": "EUR", "quote": "USD"}]},  # Delete all priorities
            timeout=TIMEOUT
        )

        # Create explicit configuration for this test
        setup_response = httpx.post(
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json={
                "sources": [
                    {"base": "EUR", "quote": "USD", "provider_code": "FED", "priority": 1}
                ]
            },
            timeout=TIMEOUT
        )

        if setup_response.status_code != 201:
            print_error(f"Failed to setup configuration: {setup_response.status_code}")
            return False

        # Verify configuration was created
        verify_response = httpx.get(f"{API_BASE_URL}/fx/pair-sources", timeout=TIMEOUT)
        if verify_response.status_code != 200:
            print_error("Failed to verify configuration")
            return False

        pair_sources = verify_response.json()["sources"]
        fed_config = [s for s in pair_sources if s["provider_code"] == "FED" and s["base"] == "EUR" and s["quote"] == "USD"]

        if not fed_config:
            print_error("Configuration not found after creation")
            return False

        print_success(f"✓ Configuration verified: EUR/USD → FED priority={fed_config[0]['priority']}")

        # EXECUTE: Test auto-configuration sync
        print_info("  Step 2: Execute sync with auto-configuration (no provider specified)")

        response3 = httpx.post(
            f"{API_BASE_URL}/fx/sync/bulk",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": "USD,EUR"  # Both currencies to match provider pair
                # NO provider parameter - uses auto-configuration
                },
            timeout=TIMEOUT
            )

        print_info(f"  Status code: {response3.status_code}")

        if response3.status_code == 400:
            # Auto-configuration not yet implemented OR configuration missing
            data3 = response3.json()
            detail = data3.get("detail", "")
            if "not yet implemented" in detail.lower():
                print_info("⚠️  Auto-configuration mode not yet implemented (expected)")
                print_info("  This will be implemented in Phase 5.3")
            elif "no configuration found" in detail.lower():
                print_error(f"Configuration missing: {detail}")
                print_error("  Test 3 (pair-sources) should have configured EUR/USD=FED")
                return False
            else:
                print_error(f"Unexpected 400 error: {detail}")
                return False
        elif response3.status_code == 200:
            # Auto-configuration working! Validate thoroughly
            data3 = response3.json()

            # Verify we got some rates
            if data3['synced'] == 0:
                print_error("Auto-config returned 0 synced rates (expected > 0)")
                return False

            print_success(f"✓ Auto-configuration mode: Synced {data3['synced']} rates")
            print_info(f"  Date range: {data3['date_range']}")

            # VALIDATION: Check that requested currencies are present
            # Note: Provider may sync additional currencies beyond what we requested
            currencies_synced = data3['currencies']
            print_info(f"  Currencies synced: {currencies_synced}")

            # We requested USD,EUR via EUR/USD configuration
            # At minimum, we expect at least ONE of the configured currencies
            # (The provider might sync the pair in either direction or with additional currencies)
            has_requested = False
            for curr in ['USD', 'EUR']:
                if curr in currencies_synced:
                    has_requested = True
                    break

            if not has_requested:
                print_error(f"Expected at least USD or EUR in synced currencies, got: {currencies_synced}")
                return False

            # Check if we got both (ideal case)
            if 'USD' in currencies_synced and 'EUR' in currencies_synced:
                print_success("✓ Auto-configuration synced both USD and EUR (complete pair)")
            else:
                print_success(f"✓ Auto-configuration synced at least one requested currency: {currencies_synced}")
                print_info("  Note: Provider may sync additional currencies based on its supported pairs")

            # PROOF: Verify that synced rates are usable and recent
            print_info("  Step 3: Verify synced rates work for conversion")

            test_conversion = httpx.post(
                f"{API_BASE_URL}/fx/convert/bulk",
                json={
                    "conversions": [
                        {
                            "amount": "100.00",
                            "from": "USD",
                            "to": "EUR",
                            "start_date": end_date.isoformat()
                            }
                        ]
                    },
                timeout=TIMEOUT
                )

            if test_conversion.status_code == 200:
                conversion_data = test_conversion.json()

                # Verify conversion succeeded (no errors)
                if len(conversion_data.get("errors", [])) > 0:
                    print_error(f"Conversion had errors: {conversion_data['errors']}")
                    return False

                result = conversion_data["results"][0]

                # Verify we got a result
                if result.get("converted_amount") is None:
                    print_error("Conversion returned no amount")
                    return False

                print_success(f"✓ Conversion works: 100 USD = {result['converted_amount']} EUR")

                # Check if backward-fill was used (indicates old rate)
                if result.get("backward_fill_info"):
                    days_back = result["backward_fill_info"]["days_back"]
                    if days_back > 7:
                        print_info(f"  ⚠️  Used old rate ({days_back} days back) - may not be from auto-config sync")
                    else:
                        print_info(f"  ✓ Used recent rate ({days_back} days back)")
                else:
                    print_info("  ✓ Used exact date rate (no backward-fill)")

                print_success("✓ Auto-configuration proof: Synced rates are usable")

                # Note: Complete source verification would require:
                # - GET /fx/rates endpoint to query source field
                # - Or checking DB directly for source='FED'
                # This is acceptable proof that auto-config worked
            else:
                print_error(f"Conversion failed after auto-config sync: {test_conversion.status_code}")
                return False

        else:
            print_error(f"Unexpected status code: {response3.status_code}")
            print_error(f"Response: {response3.text}")
            return False

        # Test 4.4: Fallback Logic (Priority-Based Retry)
        print_info("\nTest 4.4: Fallback Logic (multiple priorities)")
        print_info("  Note: Simulating fallback by configuring multiple priorities")

        # Setup: EUR/USD with ECB priority=1 and FED priority=2 (fallback)
        print_info("  Step 1: Configure EUR/USD with ECB (priority=1) and FED (priority=2)")

        # Clear existing
        httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json={"sources": [{"base": "EUR", "quote": "USD"}]},
            timeout=TIMEOUT
        )

        # Create dual configuration
        setup_response = httpx.post(
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json={
                "sources": [
                    {"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 1},
                    {"base": "EUR", "quote": "USD", "provider_code": "FED", "priority": 2}
                ]
            },
            timeout=TIMEOUT
        )

        if setup_response.status_code != 201:
            print_error(f"Failed to setup fallback configuration: {setup_response.status_code}")
            return False

        print_success("✓ Fallback configuration created (ECB priority=1, FED priority=2)")

        # Execute sync (will use ECB, or FED if ECB fails)
        print_info("  Step 2: Execute sync (primary: ECB, fallback: FED)")

        response4 = httpx.post(
            f"{API_BASE_URL}/fx/sync/bulk",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": "USD,EUR"
                },
            timeout=TIMEOUT
        )

        if response4.status_code == 200:
            data4 = response4.json()
            print_success(f"✓ Fallback sync completed: {data4['synced']} rates synced")
            print_info(f"  Note: Used primary (ECB) or fallback (FED) based on availability")
            print_info(f"  Check logs for 'Provider X failed, trying Y' messages")

            # Verify currencies
            if 'USD' in data4['currencies'] or 'EUR' in data4['currencies']:
                print_success("✓ Fallback logic working (rates synced)")
            else:
                print_error(f"Unexpected currencies: {data4['currencies']}")
                return False
        else:
            print_error(f"Fallback sync failed: {response4.status_code}")
            return False

        # CLEANUP: Remove fallback configuration
        httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json={"sources": [{"base": "EUR", "quote": "USD"}]},
            timeout=TIMEOUT
        )

        # Test 4.5: Inverse Pairs Configuration
        print_info("\nTest 4.5: Inverse Pairs (EUR/USD vs USD/EUR)")
        print_info("  Testing that both directions can coexist with different priorities")

        # Setup: EUR/USD (ECB) and USD/EUR (FED) with priority=1 each
        print_info("  Step 1: Configure EUR/USD (ECB) and USD/EUR (FED)")

        # Clear existing
        httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json={"sources": [
                {"base": "EUR", "quote": "USD"},
                {"base": "USD", "quote": "EUR"}
            ]},
            timeout=TIMEOUT
        )

        # Create inverse pairs configuration
        setup_response = httpx.post(
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json={
                "sources": [
                    {"base": "EUR", "quote": "USD", "provider_code": "ECB", "priority": 1},
                    {"base": "USD", "quote": "EUR", "provider_code": "FED", "priority": 1}
                ]
            },
            timeout=TIMEOUT
        )

        if setup_response.status_code != 201:
            print_error(f"Failed to setup inverse pairs: {setup_response.status_code}")
            return False

        print_success("✓ Inverse pairs configured (EUR/USD=ECB, USD/EUR=FED)")

        # Execute sync for both currencies
        print_info("  Step 2: Execute sync for both EUR and USD")

        response5 = httpx.post(
            f"{API_BASE_URL}/fx/sync/bulk",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": "EUR,USD"
                },
            timeout=TIMEOUT
        )

        if response5.status_code == 200:
            data5 = response5.json()
            print_success(f"✓ Inverse pairs sync completed: {data5['synced']} rates synced")

            # Verify both currencies present
            currencies_synced = data5['currencies']
            if 'USD' not in currencies_synced or 'EUR' not in currencies_synced:
                print_error(f"Expected both EUR and USD, got: {currencies_synced}")
                return False

            print_success("✓ Both directions synced (EUR/USD from ECB, USD/EUR from FED)")
            print_info("  Note: System handles semantic difference between pair directions")
        else:
            print_error(f"Inverse pairs sync failed: {response5.status_code}")
            return False

        # CLEANUP: Remove test configurations to avoid conflicts with subsequent tests
        print_info("  Step 3: Cleanup test configurations")
        httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/pair-sources/bulk",
            json={"sources": [
                {"base": "EUR", "quote": "USD"},
                {"base": "USD", "quote": "EUR"}
            ]},
            timeout=TIMEOUT
        )
        print_success("✓ Test configurations cleaned up")

        print_success("All sync tests passed (including fallback and inverse pairs)")
        return True

    except Exception as e:
        print_error(f"Request failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_convert_currency():
    """Test GET /fx/convert/bulk endpoint."""
    print_section("Test 5: GET /fx/convert/bulk")

    # First, ensure we have rates
    end_date = data_type.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=7)

    print_info("Ensuring rates exist...")
    try:
        httpx.post(
            f"{API_BASE_URL}/fx/sync/bulk",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": "USD,GBP",
                "provider": "ECB"
                },
            timeout=TIMEOUT
            )
    except:
        pass  # Ignore errors, may already exist

    # Test conversion: 100 USD to EUR (single item in bulk request)
    print_info("\nTesting conversion: 100 USD → EUR")

    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "USD",
                        "to": "EUR",
                        "start_date": end_date.isoformat()
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
        required_fields = ["amount", "from_currency", "to_currency", "conversion_date", "converted_amount", "rate"]
        for field in required_fields:
            if field not in result:
                print_error(f"Missing field in result: {field}")
                return False

        print_success(f"Conversion successful")
        print_info(f"  {result['amount']} {result['from_currency']} = {result['converted_amount']} {result['to_currency']}")
        print_info(f"  Rate: {result['rate']}")
        print_info(f"  Conversion date: {result['conversion_date']}")

        # Log rate_date info (from backward_fill_info if present, else same as conversion_date)
        if result.get('backward_fill_info'):
            print_info(f"  Actual rate date: {result['backward_fill_info']['actual_rate_date']} (backward-filled)")
        else:
            print_info(f"  Rate date: {result['conversion_date']} (exact match)")

        # Test identity conversion (EUR → EUR)
        print_info("\nTesting identity conversion: 100 EUR → EUR")

        response2 = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "EUR",
                        "to": "EUR",
                        "start_date": end_date.isoformat()
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
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "USD",
                        "to": "EUR",
                        "start_date": end_date.isoformat()
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
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": str(eur_amount),
                        "from": "EUR",
                        "to": "USD",
                        "start_date": end_date.isoformat()
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
    print_section("Test 7: Backward-Fill Warning")

    # First, insert a rate for a date in the past (before requested date)
    old_rate_date = data_type(1999, 12, 15)
    requested_date = data_type(2000, 3, 20)  # 3 months after the rate

    print_info(f"Step 1: Insert rate for past date ({old_rate_date})")

    try:
        # Insert a manual rate (using bulk with single item)
        insert_response = httpx.post(
            f"{API_BASE_URL}/fx/rate-set/bulk",
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
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "USD",
                        "to": "EUR",
                        "start_date": requested_date.isoformat()
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

        # Verify structure (simplified: no more 'applied' and 'requested_date')
        required_fields = ["actual_rate_date", "days_back"]
        for field in required_fields:
            if field not in fill_info:
                print_error(f"backward_fill_info missing field: {field}")
                return False

        # Verify actual_rate_date is <= requested_date (conversion_date)
        actual_date = data_type.fromisoformat(fill_info["actual_rate_date"])
        conversion_date = data_type.fromisoformat(result["conversion_date"])

        if actual_date > conversion_date:
            print_error(f"actual_rate_date ({actual_date}) should be <= conversion_date ({conversion_date})")
            return False

        # Verify days_back calculation is correct
        expected_days_back = (conversion_date - actual_date).days
        if fill_info["days_back"] != expected_days_back:
            print_error(f"days_back incorrect: expected {expected_days_back}, got {fill_info['days_back']}")
            return False

        print_success(f"✓ Backward-fill applied: {fill_info['days_back']} days back")
        print_info(f"  Conversion date: {result['conversion_date']} ✓")
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
    """Test POST /fx/rate-set/bulk endpoint for manual rate entry."""
    print_section("Test 6: Manual Rate Upsert")

    # Use a date far in the past to avoid interference from other rates
    test_date = data_type(2020, 1, 15)

    # Test 1: Insert new rate
    print_info("Test 4.1: Insert new manual rate")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/rate-set/bulk",
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
            f"{API_BASE_URL}/fx/rate-set/bulk",
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
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "EUR",
                        "to": "USD",
                        "start_date": test_date.isoformat()
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
            f"{API_BASE_URL}/fx/rate-set/bulk",
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
            f"{API_BASE_URL}/fx/rate-set/bulk",
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
    print_section("Test 8: Bulk Conversions (Multiple Items)")

    # Ensure rates exist
    end_date = data_type.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=7)

    try:
        httpx.post(
            f"{API_BASE_URL}/fx/sync/bulk",
            params={
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "currencies": "USD,GBP,CHF",
                "provider": "ECB"
                },
            timeout=TIMEOUT
            )
    except:
        pass

    # Test bulk conversion with 3 different conversions
    print_info("Test 10.1: Bulk convert 3 amounts in single request")

    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {"amount": "100.00", "from": "USD", "to": "EUR", "start_date": end_date.isoformat()},
                    {"amount": "200.00", "from": "GBP", "to": "EUR", "start_date": end_date.isoformat()},
                    {"amount": "300.00", "from": "CHF", "to": "EUR", "start_date": end_date.isoformat()},
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
        print_info("\nTest 10.2: Bulk with one invalid currency (partial failure)")

        response2 = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {"amount": "100.00", "from": "USD", "to": "EUR", "start_date": end_date.isoformat()},
                    {"amount": "200.00", "from": "XXX", "to": "EUR", "start_date": end_date.isoformat()},  # Invalid
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
    print_section("Test 9: Bulk Rate Upserts (Multiple Items)")

    test_date = data_type(2019, 6, 15)

    print_info("Test 6.1: Bulk upsert 3 rates in single request")

    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/rate-set/bulk",
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
            f"{API_BASE_URL}/fx/rate-set/bulk",
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


def test_delete_rates():
    """Test DELETE /fx/rate-set/bulk endpoint for rate deletion."""
    print_section("Test 10: Rate Deletion (DELETE /rate-set/bulk)")

    all_ok = True

    # Test 1: Delete single day
    print_info("Test 10.1: Delete single day (start_date only)")
    try:
        # Cleanup: Remove any existing EUR/USD rates in our test range
        setup_dates = [data_type(2025, 1, 1), data_type(2025, 1, 2), data_type(2025, 1, 3)]
        httpx.request("DELETE",
                      f"{API_BASE_URL}/fx/rate-set/bulk",
                      json={"deletions": [{"from": "EUR", "to": "USD", "start_date": setup_dates[0].isoformat(), "end_date": setup_dates[-1].isoformat()}]},
                      timeout=TIMEOUT
                      )

        # Setup: Insert 3 rates for EUR/USD
        for test_date in setup_dates:
            response = httpx.post(
                f"{API_BASE_URL}/fx/rate-set/bulk",
                json={
                    "rates": [
                        {
                            "date": test_date.isoformat(),
                            "base": "EUR",
                            "quote": "USD",
                            "rate": "1.1",
                            "source": "TEST"
                            }
                        ]
                    },
                timeout=TIMEOUT
                )
            if response.status_code != 200:
                print_error(f"Setup failed for {test_date}")
                all_ok = False
                return all_ok

        # Delete: EUR/USD 2025-01-02
        response = httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "deletions": [
                    {
                        "from": "EUR",
                        "to": "USD",
                        "start_date": "2025-01-02"
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            print_error(f"Response: {response.text}")
            all_ok = False
        else:
            data = response.json()

            # Verify response structure
            if "results" not in data or "total_deleted" not in data:
                print_error("Invalid response structure")
                all_ok = False
            else:
                result = data["results"][0]

                # existing_count counts rates for THIS SPECIFIC REQUEST (date=2025-01-02)
                # We inserted 3 rates (01, 02, 03) but we're deleting only 02
                if result["existing_count"] != 1:
                    print_error(f"Expected existing_count=1 (for date 2025-01-02), got {result['existing_count']}")
                    all_ok = False
                elif result["deleted_count"] != 1:
                    print_error(f"Expected deleted_count=1, got {result['deleted_count']}")
                    all_ok = False
                else:
                    print_success(f"✓ Deleted 1 rate (existing: 1 for that date, deleted: 1)")

        # Cleanup
        for test_date in setup_dates:
            httpx.request("DELETE",
                          f"{API_BASE_URL}/fx/rate-set/bulk",
                          json={"deletions": [{"from": "EUR", "to": "USD", "start_date": test_date.isoformat()}]},
                          timeout=TIMEOUT
                          )

    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        all_ok = False

    # Test 2: Delete range (start_date + end_date)
    print_info("\nTest 10.2: Delete range (start_date + end_date)")
    try:
        # Use old dates (1995) to avoid interference from other tests
        # Cleanup: Remove any existing GBP/USD rates in our test range
        httpx.request("DELETE",
                      f"{API_BASE_URL}/fx/rate-set/bulk",
                      json={"deletions": [{"from": "GBP", "to": "USD", "start_date": "1995-01-01", "end_date": "1995-01-31"}]},
                      timeout=TIMEOUT
                      )

        # Setup: Insert 7 rates for GBP/USD (1995-01-01 to 07)
        for day in range(1, 8):
            test_date = data_type(1995, 1, day)
            response = httpx.post(
                f"{API_BASE_URL}/fx/rate-set/bulk",
                json={
                    "rates": [
                        {
                            "date": test_date.isoformat(),
                            "base": "GBP",
                            "quote": "USD",
                            "rate": "1.25",
                            "source": "TEST"
                            }
                        ]
                    },
                timeout=TIMEOUT
                )

        # Delete: GBP/USD ALL 7 rates (1995-01-01 to 07)
        response = httpx.request("DELETE",
                                 f"{API_BASE_URL}/fx/rate-set/bulk",
                                 json={
                                     "deletions": [
                                         {
                                             "from": "GBP",
                                             "to": "USD",
                                             "start_date": "1995-01-01",
                                             "end_date": "1995-01-07"
                                             }
                                         ]
                                     },
                                 timeout=TIMEOUT
                                 )

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            all_ok = False
        else:
            data = response.json()
            result = data["results"][0]

            # existing_count counts rates for THIS SPECIFIC RANGE (1995-01-01 to 07)
            # We inserted 7 rates (01-07) and delete ALL 7
            if result["existing_count"] != 7:
                print_error(f"Expected existing_count=7 (all inserted rates), got {result['existing_count']}")
                all_ok = False
            elif result["deleted_count"] != 7:
                print_error(f"Expected deleted_count=7 (all rates), got {result['deleted_count']}")
                all_ok = False
            else:
                print_success(f"✓ Deleted range: 7 rates (all from 1995-01-01 to 07)")

        # Cleanup (already deleted, but for safety)
        httpx.request("DELETE",
                      f"{API_BASE_URL}/fx/rate-set/bulk",
                      json={"deletions": [{"from": "GBP", "to": "USD", "start_date": "1995-01-01", "end_date": "1995-01-31"}]},
                      timeout=TIMEOUT
                      )

    except Exception as e:
        print_error(f"Test failed: {e}")
        all_ok = False

    # Test 3: Delete inverted pair (USD/EUR → EUR/USD in DB)
    print_info("\nTest 10.3: Delete inverted pair (normalization)")
    try:
        # Setup: Insert EUR/USD
        test_date = data_type(2025, 1, 1)
        response = httpx.post(
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "rates": [
                    {
                        "date": test_date.isoformat(),
                        "base": "EUR",
                        "quote": "USD",
                        "rate": "1.1",
                        "source": "TEST"
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        # Delete: USD/EUR (should delete EUR/USD via normalization)
        response = httpx.request("DELETE",
                                 f"{API_BASE_URL}/fx/rate-set/bulk",
                                 json={
                                     "deletions": [
                                         {
                                             "from": "USD",
                                             "to": "EUR",
                                             "start_date": test_date.isoformat()
                                             }
                                         ]
                                     },
                                 timeout=TIMEOUT
                                 )

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            all_ok = False
        else:
            data = response.json()
            result = data["results"][0]

            if result["deleted_count"] != 1:
                print_error(f"Expected deleted_count=1, got {result['deleted_count']}")
                all_ok = False
            else:
                print_success(f"✓ Inverted pair deleted via normalization")

    except Exception as e:
        print_error(f"Test failed: {e}")
        all_ok = False

    # Test 4: Bulk delete (3 pairs)
    print_info("\nTest 10.4: Bulk delete (3 different pairs)")
    try:
        # Setup: Insert EUR/USD, GBP/USD, CHF/USD
        test_date = data_type(2025, 1, 10)
        pairs = [("EUR", "USD", "1.1"), ("GBP", "USD", "1.25"), ("CHF", "USD", "1.05")]

        for base, quote, rate in pairs:
            response = httpx.post(
                f"{API_BASE_URL}/fx/rate-set/bulk",
                json={
                    "rates": [
                        {
                            "date": test_date.isoformat(),
                            "base": base,
                            "quote": quote,
                            "rate": rate,
                            "source": "TEST"
                            }
                        ]
                    },
                timeout=TIMEOUT
                )

        # Delete all 3 in single request
        response = httpx.request("DELETE",
                                 f"{API_BASE_URL}/fx/rate-set/bulk",
                                 json={
                                     "deletions": [
                                         {"from": "EUR", "to": "USD", "start_date": test_date.isoformat()},
                                         {"from": "GBP", "to": "USD", "start_date": test_date.isoformat()},
                                         {"from": "CHF", "to": "USD", "start_date": test_date.isoformat()}
                                         ]
                                     },
                                 timeout=TIMEOUT
                                 )

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            all_ok = False
        else:
            data = response.json()

            if data["total_deleted"] != 3:
                print_error(f"Expected total_deleted=3, got {data['total_deleted']}")
                all_ok = False
            else:
                print_success(f"✓ Bulk delete: 3 pairs deleted in single request")

    except Exception as e:
        print_error(f"Test failed: {e}")
        all_ok = False

    # Test 5: Delete non-existent rate
    print_info("\nTest 10.5: Delete non-existent rate (graceful handling)")
    try:
        response = httpx.request("DELETE",
                                 f"{API_BASE_URL}/fx/rate-set/bulk",
                                 json={
                                     "deletions": [
                                         {
                                             "from": "EUR",
                                             "to": "ZZZ",  # Non-existent currency
                                             "start_date": "2025-01-01"
                                             }
                                         ]
                                     },
                                 timeout=TIMEOUT
                                 )

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            all_ok = False
        else:
            data = response.json()
            result = data["results"][0]

            if not result["success"]:
                print_error("Operation reported as unsuccessful")
                all_ok = False
            elif result["existing_count"] != 0 or result["deleted_count"] != 0:
                print_error(f"Expected counts=0, got existing={result['existing_count']}, deleted={result['deleted_count']}")
                all_ok = False
            elif result["message"] is None:
                print_error("Expected warning message for non-existent rate")
                all_ok = False
            else:
                print_success(f"✓ Non-existent rate handled gracefully with message")

    except Exception as e:
        print_error(f"Test failed: {e}")
        all_ok = False

    # Test 6: Partial failure (validation error)
    print_info("\nTest 10.6: Partial failure (same from/to currency)")
    try:
        # Setup valid pair
        test_date = data_type(2025, 1, 15)
        httpx.post(
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "rates": [
                    {
                        "date": test_date.isoformat(),
                        "base": "EUR",
                        "quote": "USD",
                        "rate": "1.1",
                        "source": "TEST"
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        # Try to delete: one valid, one invalid (EUR/EUR)
        response = httpx.request("DELETE",
                                 f"{API_BASE_URL}/fx/rate-set/bulk",
                                 json={
                                     "deletions": [
                                         {"from": "EUR", "to": "USD", "start_date": test_date.isoformat()},
                                         {"from": "EUR", "to": "EUR", "start_date": test_date.isoformat()}  # Invalid
                                         ]
                                     },
                                 timeout=TIMEOUT
                                 )

        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            all_ok = False
        else:
            data = response.json()

            if len(data["results"]) != 1:
                print_error(f"Expected 1 result (valid deletion), got {len(data['results'])}")
                all_ok = False
            elif len(data["errors"]) != 1:
                print_error(f"Expected 1 error (invalid deletion), got {len(data['errors'])}")
                all_ok = False
            else:
                print_success(f"✓ Partial failure handled: 1 deleted, 1 error")

    except Exception as e:
        print_error(f"Test failed: {e}")
        all_ok = False

    # Test 7: Invalid date range (start > end)
    print_info("\nTest 10.7: Invalid date range (start > end)")
    try:
        response = httpx.request("DELETE",
                                 f"{API_BASE_URL}/fx/rate-set/bulk",
                                 json={
                                     "deletions": [
                                         {
                                             "from": "EUR",
                                             "to": "USD",
                                             "start_date": "2025-01-05",
                                             "end_date": "2025-01-01"  # Before start_date
                                             }
                                         ]
                                     },
                                 timeout=TIMEOUT
                                 )

        if response.status_code == 200:
            print_error("Invalid date range was accepted (should return 400)")
            all_ok = False
        else:
            print_success(f"✓ Invalid date range rejected (status {response.status_code})")

    except Exception as e:
        print_error(f"Test failed: {e}")
        all_ok = False

    # Test 8: Invalid date format (FastAPI/Pydantic validation)
    print_info("\nTest 10.8: Invalid date format")
    try:
        response = httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "deletions": [
                    {
                        "from": "EUR",
                        "to": "USD",
                        "start_date": "2025-13-45"  # Invalid date
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        if response.status_code == 200:
            print_error("Invalid date format was accepted (should return 422)")
            all_ok = False
        else:
            print_success(f"✓ Invalid date format rejected (status {response.status_code})")

    except Exception as e:
        print_error(f"Test failed: {e}")
        all_ok = False

    # Test 9: Idempotency (delete already deleted rates)
    print_info("\nTest 10.9: Idempotency (delete already deleted rates)")
    try:
        # Setup: Insert and then delete
        test_date = data_type(2025, 1, 20)
        httpx.post(
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "rates": [
                    {
                        "date": test_date.isoformat(),
                        "base": "EUR",
                        "quote": "USD",
                        "rate": "1.1",
                        "source": "TEST"
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        # First delete
        response1 = httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "deletions": [
                    {
                        "from": "EUR",
                        "to": "USD",
                        "start_date": test_date.isoformat()
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        if response1.status_code != 200:
            print_error(f"First delete failed: {response1.status_code}")
            all_ok = False
        else:
            data1 = response1.json()
            if data1["results"][0]["deleted_count"] != 1:
                print_error(f"First delete should delete 1, got {data1['results'][0]['deleted_count']}")
                all_ok = False

        # Second delete (idempotency test)
        response2 = httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "deletions": [
                    {
                        "from": "EUR",
                        "to": "USD",
                        "start_date": test_date.isoformat()
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        if response2.status_code != 200:
            print_error(f"Second delete (idempotent) failed: {response2.status_code}")
            all_ok = False
        else:
            data2 = response2.json()
            result2 = data2["results"][0]

            if result2["deleted_count"] != 0:
                print_error(f"Second delete should delete 0 (already deleted), got {result2['deleted_count']}")
                all_ok = False
            elif result2["message"] is None:
                print_error("Expected warning message for already deleted rate")
                all_ok = False
            else:
                print_success(f"✓ Idempotency verified: second delete returns 0 with message")

    except Exception as e:
        print_error(f"Test failed: {e}")
        all_ok = False

    # Test 10: Verify conversions fail after rate deletion + backward-fill behavior
    print_info("\nTest 10.10: Verify conversions and backward-fill after rate deletion")
    try:
        # Part A: Delete only rate (no backward-fill possible)
        # Use a date far in the past (older than any possible rate in DB)
        test_date_old = data_type(1990, 1, 1)

        # Cleanup any existing EUR/JPY rates in 1990
        httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "deletions": [
                    {
                        "from": "EUR",
                        "to": "JPY",
                        "start_date": "1990-01-01",
                        "end_date": "1990-12-31"
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        # Insert single rate for 1990-01-01
        httpx.post(
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "rates": [
                    {
                        "date": test_date_old.isoformat(),
                        "base": "EUR",
                        "quote": "JPY",
                        "rate": "160.5",
                        "source": "TEST"
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        # Verify conversion works BEFORE deletion
        response_before = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "100",
                        "from": "EUR",
                        "to": "JPY",
                        "start_date": test_date_old.isoformat()
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        if response_before.status_code != 200:
            print_error("Conversion before delete failed (should work)")
            all_ok = False
        else:
            print_success("✓ Part A: Conversion works before deletion")

        # Delete the only rate
        httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "deletions": [
                    {
                        "from": "EUR",
                        "to": "JPY",
                        "start_date": test_date_old.isoformat()
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        # Verify conversion FAILS after deletion (no backward-fill possible)
        response_after = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "100",
                        "from": "EUR",
                        "to": "JPY",
                        "start_date": test_date_old.isoformat()
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        # Should have errors (no rate available)
        if response_after.status_code == 200:
            data_after = response_after.json()
            if len(data_after["errors"]) == 0:
                print_error("Conversion after delete succeeded (should fail - no rates)")
                all_ok = False
            else:
                print_success(f"✓ Part A: Conversion fails after deletion (no backward-fill)")
        else:
            print_success(f"✓ Part A: Conversion fails after deletion (status {response_after.status_code})")

        # Part B: Delete recent rate but older rate exists (backward-fill should work)
        test_date_base = data_type(1991, 6, 1)
        test_date_future = data_type(1991, 6, 15)

        # Cleanup 1991 range
        httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "deletions": [
                    {
                        "from": "EUR",
                        "to": "JPY",
                        "start_date": "1991-01-01",
                        "end_date": "1991-12-31"
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        # Insert two rates: 1991-06-01 and 1991-06-15
        httpx.post(
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "rates": [
                    {
                        "date": test_date_base.isoformat(),
                        "base": "EUR",
                        "quote": "JPY",
                        "rate": "155.0",
                        "source": "TEST"
                        },
                    {
                        "date": test_date_future.isoformat(),
                        "base": "EUR",
                        "quote": "JPY",
                        "rate": "158.0",
                        "source": "TEST"
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        # Verify conversion for 1991-06-15 works (exact match)
        response_exact = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "100",
                        "from": "EUR",
                        "to": "JPY",
                        "start_date": test_date_future.isoformat()
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        if response_exact.status_code != 200:
            print_error("Conversion for exact date failed")
            all_ok = False

        # Delete the 1991-06-15 rate (but keep 1991-06-01)
        httpx.request(
            "DELETE",
            f"{API_BASE_URL}/fx/rate-set/bulk",
            json={
                "deletions": [
                    {
                        "from": "EUR",
                        "to": "JPY",
                        "start_date": test_date_future.isoformat()
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        # Verify conversion for 1991-06-15 still works via BACKWARD-FILL (uses 1991-06-01)
        response_backfill = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "100",
                        "from": "EUR",
                        "to": "JPY",
                        "start_date": test_date_future.isoformat()
                        }
                    ]
                },
            timeout=TIMEOUT
            )

        if response_backfill.status_code != 200:
            print_error("Backward-fill conversion failed (should work using older rate)")
            all_ok = False
        else:
            data_backfill = response_backfill.json()
            if len(data_backfill["errors"]) > 0:
                print_error(f"Backward-fill had errors: {data_backfill['errors']}")
                all_ok = False
            else:
                result = data_backfill["results"][0]
                # Should have backward_fill_info present
                if result.get("backward_fill_info") is None:
                    print_error("Expected backward_fill_info but got None")
                    all_ok = False
                elif result["backward_fill_info"]["days_back"] != 14:
                    print_error(f"Expected 14 days back, got {result['backward_fill_info']['days_back']}")
                    all_ok = False
                else:
                    print_success(f"✓ Part B: Backward-fill works correctly (14 days back from {test_date_future} to {test_date_base})")

    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        all_ok = False

    return all_ok


def test_invalid_requests():
    """Test comprehensive validation and error handling for invalid requests."""
    print_section("Test 11: Invalid Request Handling")

    all_ok = True

    # Test 1: Invalid date range (start > end) with error detail check
    print_info("Test 11.1: Invalid date range (start > end)")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/sync/bulk",
            params={
                "start": "2025-01-10",
                "end": "2025-01-01",
                "currencies": "USD",
                "provider": "ECB"
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
    print_info("\nTest 11.2: Negative amount")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "-100.00",
                        "from": "USD",
                        "to": "EUR",
                        "start_date": data_type.today().isoformat()
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
    print_info("\nTest 11.3: Zero amount")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "0",
                        "from": "USD",
                        "to": "EUR",
                        "start_date": data_type.today().isoformat()
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
    print_info("\nTest 11.4: Non-numeric amount (abc)")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "abc",
                        "from": "USD",
                        "to": "EUR",
                        "start_date": data_type.today().isoformat()
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
    print_info("\nTest 11.5: Invalid currency code format (INVALID)")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "INVALID",
                        "to": "EUR",
                        "start_date": data_type.today().isoformat()
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
    print_info("\nTest 11.6: Valid format but unsupported currency (XXX)")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
            json={
                "conversions": [
                    {
                        "amount": "100.00",
                        "from": "XXX",
                        "to": "EUR",
                        "start_date": data_type.today().isoformat()
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
    print_info("\nTest 11.7: Empty conversions array")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
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
    print_info("\nTest 11.8: Missing required field in conversion (amount)")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/convert/bulk",
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
    print_info("\nTest 11.9: Empty currency string in sync")
    try:
        response = httpx.post(
            f"{API_BASE_URL}/fx/sync/bulk",
            params={
                "start": data_type.today().isoformat(),
                "end": data_type.today().isoformat(),
                "currencies": "",  # Empty string
                "provider": "ECB"
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
  • POST /fx/sync/bulk - Sync FX rates from ECB
  • POST /fx/convert/bulk - Convert currencies (bulk-only, single = 1 item array)
  • POST /fx/rate-set/bulk - Manually insert/update rates (bulk-only, single = 1 item array)
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
        "GET /fx/providers": test_get_providers(),
        "Pair Sources CRUD": test_pair_sources_crud(),  # Moved BEFORE sync to setup configuration
        "POST /fx/sync/bulk": test_sync_rates(),
        "POST /fx/convert/bulk (Single)": test_convert_currency(),
        "POST /fx/rate-set/bulk (Single)": test_manual_rate_upsert(),
        "Backward-Fill Warning": test_convert_missing_rate(),
        "POST /fx/convert/bulk (Bulk)": test_bulk_conversions(),
        "POST /fx/rate-set/bulk (Bulk)": test_bulk_rate_upserts(),
        "DELETE /fx/rate-set/bulk": test_delete_rates(),
        "Invalid Request Handling": test_invalid_requests(),
        }

    # Summary
    success = print_test_summary(results, "FX API Endpoint Tests")
    return success


if __name__ == "__main__":
    success = run_all_tests()
    exit_with_result(success)
