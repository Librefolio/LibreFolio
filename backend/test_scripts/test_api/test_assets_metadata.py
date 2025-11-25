"""
Test Assets Metadata API Endpoints.

Tests REST API endpoints for asset metadata management:
- PATCH /api/v1/assets/metadata (bulk)
- POST /api/v1/assets (bulk read)
- POST /api/v1/assets/{asset_id}/metadata/refresh
- POST /api/v1/assets/metadata/refresh/bulk
- POST /api/v1/assets/scraper (provider assignments read)

Auto-starts backend server if not running and stops it after tests.
"""
import json
import sys
from pathlib import Path

import httpx

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup test database BEFORE importing app modules
from backend.test_scripts.test_db_config import setup_test_database, initialize_test_database

setup_test_database()

from backend.test_scripts.test_server_helper import _TestingServerManager, TEST_API_BASE_URL
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


def setup_test_assets(base_url: str) -> dict:
    """Create test assets for metadata tests.

    Returns dict with asset IDs: {'stock_id': int, 'etf_id': int}
    """
    print_section("Setup: Creating Test Assets")

    # Create a stock asset
    stock_payload = {
        "display_name": "Test Stock Asset",
        "identifier": "TEST_STOCK_META",
        "identifier_type": "TICKER",
        "currency": "USD",
        "asset_type": "STOCK",
        "valuation_model": "MARKET_PRICE",
        "active": True
        }

    try:
        # Note: Assuming there's a POST /assets endpoint for creation
        # If not, we'll need to use direct DB insertion
        resp = httpx.post(
            f"{base_url}/assets",
            json=stock_payload,
            timeout=TIMEOUT
            )

        if resp.status_code == 201 or resp.status_code == 200:
            stock_data = resp.json()
            stock_id = stock_data.get('id') or stock_data.get('asset_id')
            print_success(f"✓ Created stock asset: ID={stock_id}")
        else:
            # Fallback: use asset ID 1 (should exist from populate)
            print_info(f"⚠️  Could not create asset via API (status {resp.status_code}), using ID=1")
            stock_id = 1

    except Exception as e:
        print_info(f"⚠️  Could not create asset via API ({e}), using ID=1")
        stock_id = 1

    return {'stock_id': stock_id}


def test_patch_metadata_bulk(base_url: str, asset_id: int) -> bool:
    """Test PATCH /assets/metadata (bulk partial update)."""
    print_section("Test 1: PATCH /assets/metadata (bulk)")

    try:
        # Test 1a: Valid geographic_area with changes verification
        print_info("Test 1a: PATCH with valid geographic_area")
        payload = {
            "assets": [
                {
                    "asset_id": asset_id,
                    "patch": {
                        "short_description": "Updated via API test",
                        "geographic_area": {"USA": "0.7", "FRA": "0.3"},
                        "investment_type": "stock"
                        }
                    }
                ]
            }

        resp = httpx.patch(
            f"{base_url}/assets/metadata",
            json=payload,
            timeout=TIMEOUT
            )

        if resp.status_code != 200:
            print_error(f"❌ PATCH failed: {resp.status_code} {resp.text}")
            return False

        data = resp.json()
        print_info(f"Response: {json.dumps(data, indent=2)}")

        # Verify structure
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Response should contain at least one result"
        assert data[0].get('asset_id') == asset_id, "asset_id mismatch"
        assert data[0].get('success') == True, "success should be True"

        # **NEW: Verify changes are returned**
        changes = data[0].get('changes')
        assert changes is not None, "changes should not be None"
        assert isinstance(changes, list), "changes should be a list"
        assert len(changes) > 0, "changes should contain at least one field change"
        print_success(f"✓ Changes returned: {len(changes)} field(s) updated")

        # **NEW: Verify database was actually updated by reading back**
        read_resp = httpx.post(
            f"{base_url}/assets",
            json={"asset_ids": [asset_id]},
            timeout=TIMEOUT
            )

        if read_resp.status_code != 200:
            print_error(f"❌ Failed to read back asset: {read_resp.status_code}")
            return False

        read_data = read_resp.json()
        assert len(read_data) > 0, "Should return at least one asset"

        updated_params = read_data[0].get('classification_params', {})
        assert updated_params.get('short_description') == "Updated via API test", \
            f"short_description not updated: {updated_params.get('short_description')}"
        assert updated_params.get('investment_type') == "stock", \
            f"investment_type not updated: {updated_params.get('investment_type')}"

        geo_area = updated_params.get('geographic_area', {})
        assert "USA" in geo_area, "USA not in geographic_area"
        assert "FRA" in geo_area, "FRA not in geographic_area"
        # Check values (as strings due to Decimal serialization)
        assert geo_area["USA"] == "0.7000", f"USA value mismatch: {geo_area['USA']}"
        assert geo_area["FRA"] == "0.3000", f"FRA value mismatch: {geo_area['FRA']}"

        print_success("✓ Test 1a: Database verified - all fields updated correctly")

        # Test 1b: Invalid geographic_area (should return 422 or per-item error)
        print_info("\nTest 1b: PATCH with invalid geographic_area")
        invalid_payload = {
            "assets": [
                {
                    "asset_id": asset_id,
                    "patch": {
                        "geographic_area": {"INVALID_COUNTRY": "1.0"}
                        }
                    }
                ]
            }

        resp = httpx.patch(
            f"{base_url}/assets/metadata",
            json=invalid_payload,
            timeout=TIMEOUT
            )

        # Should either return 422 or 200 with success=false in result
        if resp.status_code == 422:
            print_success("✓ Test 1b: Invalid geographic_area rejected with 422")
        elif resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                if not data[0].get('success'):
                    print_success("✓ Test 1b: Invalid geographic_area rejected (per-item error)")
                else:
                    print_error("❌ Test 1b: Invalid geographic_area should have been rejected")
                    return False
        else:
            print_error(f"❌ Test 1b: Unexpected status {resp.status_code}")
            return False

        # Test 1c: PATCH with absent fields (should be ignored - verify DB unchanged)
        print_info("\nTest 1c: PATCH with absent fields (PATCH semantics)")

        # Read current state
        read_resp = httpx.post(
            f"{base_url}/assets",
            json={"asset_ids": [asset_id]},
            timeout=TIMEOUT
            )
        before_params = read_resp.json()[0]['classification_params']

        patch_sector_only = {
            "assets": [
                {
                    "asset_id": asset_id,
                    "patch": {
                        "sector": "Technology"
                        }
                    }
                ]
            }

        resp = httpx.patch(
            f"{base_url}/assets/metadata",
            json=patch_sector_only,
            timeout=TIMEOUT
            )

        if resp.status_code != 200:
            print_error(f"❌ PATCH failed: {resp.status_code}")
            return False

        # Verify only sector changed, other fields intact
        read_resp = httpx.post(
            f"{base_url}/assets",
            json={"asset_ids": [asset_id]},
            timeout=TIMEOUT
            )
        after_params = read_resp.json()[0]['classification_params']

        assert after_params.get('sector') == "Technology", "sector not updated"
        assert after_params.get('short_description') == before_params.get('short_description'), \
            "short_description should not change"
        assert after_params.get('geographic_area') == before_params.get('geographic_area'), \
            "geographic_area should not change"

        print_success("✓ Test 1c: Absent fields ignored (PATCH semantics verified)")

        # Test 1d: PATCH with null (should clear field - verify DB cleared)
        print_info("\nTest 1d: PATCH with null (clear field)")
        patch_null = {
            "assets": [
                {
                    "asset_id": asset_id,
                    "patch": {
                        "sector": None
                        }
                    }
                ]
            }

        resp = httpx.patch(
            f"{base_url}/assets/metadata",
            json=patch_null,
            timeout=TIMEOUT
            )

        if resp.status_code != 200:
            print_error(f"❌ PATCH null failed: {resp.status_code}")
            return False

        # Verify changes show field cleared
        data = resp.json()
        changes = data[0].get('changes', [])
        sector_change = next((c for c in changes if c['field'] == 'sector'), None)
        assert sector_change is not None, "sector change not in changes list"
        assert sector_change['new'] == 'null', f"sector should be cleared (null), got: {sector_change['new']}"

        # Verify DB actually cleared
        read_resp = httpx.post(
            f"{base_url}/assets",
            json={"asset_ids": [asset_id]},
            timeout=TIMEOUT
            )
        after_params = read_resp.json()[0]['classification_params']
        assert after_params.get('sector') is None, "sector should be None in DB"

        print_success("✓ Test 1d: Null clears field (DB verified)")

        return True

    except Exception as e:
        print_error(f"❌ Exception in PATCH tests: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bulk_read_assets(base_url: str, asset_id: int) -> bool:
    """Test POST /assets (bulk read with metadata)."""
    print_section("Test 2: POST /assets (bulk read)")

    try:
        payload = {"asset_ids": [asset_id]}

        resp = httpx.post(
            f"{base_url}/assets",
            json=payload,
            timeout=TIMEOUT
            )

        if resp.status_code != 200:
            print_error(f"❌ Bulk read failed: {resp.status_code} {resp.text}")
            return False

        data = resp.json()
        print_info(f"Response: {json.dumps(data, indent=2)[:200]}...")

        # Verify structure
        assert isinstance(data, list), "Response should be a list"
        assert len(data) > 0, "Response should contain at least one asset"

        asset = data[0]
        assert 'asset_id' in asset or 'id' in asset, "Asset should have ID"
        assert 'display_name' in asset, "Asset should have display_name"

        # classification_params may be null or a dict
        if 'classification_params' in asset:
            print_success(f"✓ Asset returned with classification_params: {asset.get('classification_params') is not None}")

        print_success("✓ Bulk read assets returned metadata")
        return True

    except Exception as e:
        print_error(f"❌ Exception in bulk read: {e}")
        return False


def test_metadata_refresh_single(base_url: str, asset_id: int) -> bool:
    """Test POST /assets/{asset_id}/metadata/refresh."""
    print_section("Test 3: POST /assets/{asset_id}/metadata/refresh")

    try:
        resp = httpx.post(
            f"{base_url}/assets/{asset_id}/metadata/refresh",
            timeout=TIMEOUT
            )

        # May return 200 with success=true/false depending on provider
        if resp.status_code != 200:
            print_error(f"❌ Single refresh failed: {resp.status_code} {resp.text}")
            return False

        data = resp.json()
        print_info(f"Response: {json.dumps(data, indent=2)}")

        # Verify structure (FAMetadataRefreshResult)
        assert 'asset_id' in data, "Response should have asset_id"
        assert 'success' in data, "Response should have success"
        assert 'message' in data, "Response should have message"

        if data.get('success'):
            print_success(f"✓ Metadata refresh successful: {data.get('message')}")
            if data.get('changes'):
                print_info(f"  Changes: {len(data['changes'])} fields updated")
        else:
            print_info(f"ℹ️  Metadata refresh returned success=false: {data.get('message')}")
            print_info("  (This is normal if no provider assigned or provider doesn't support metadata)")

        print_success("✓ Single metadata refresh endpoint OK")
        return True

    except Exception as e:
        print_error(f"❌ Exception in single refresh: {e}")
        return False


def test_metadata_refresh_bulk(base_url: str, asset_id: int) -> bool:
    """Test POST /assets/metadata/refresh/bulk."""
    print_section("Test 4: POST /assets/metadata/refresh/bulk")

    try:
        payload = {"asset_ids": [asset_id]}

        resp = httpx.post(
            f"{base_url}/assets/metadata/refresh/bulk",
            json=payload,
            timeout=TIMEOUT
            )

        if resp.status_code != 200:
            print_error(f"❌ Bulk refresh failed: {resp.status_code} {resp.text}")
            return False

        data = resp.json()
        print_info(f"Response: {json.dumps(data, indent=2)}")

        # Verify structure (FABulkMetadataRefreshResponse)
        assert 'results' in data, "Response should have results"
        assert 'success_count' in data, "Response should have success_count"
        assert 'failed_count' in data, "Response should have failed_count"

        print_info(f"  Success: {data['success_count']}, Failed: {data['failed_count']}")
        print_success("✓ Bulk metadata refresh endpoint OK")
        return True

    except Exception as e:
        print_error(f"❌ Exception in bulk refresh: {e}")
        return False


def test_provider_assignments_read(base_url: str, asset_id: int) -> bool:
    """Test POST /assets/scraper (read provider assignments).

    NOTE: This endpoint is not yet implemented (Phase 5.2).
    Test will pass if endpoint returns 404 (not implemented yet).
    """
    print_section("Test 5: POST /assets/scraper (read provider assignments)")

    try:
        payload = {"asset_ids": [asset_id]}

        resp = httpx.post(
            f"{base_url}/assets/scraper",
            json=payload,
            timeout=TIMEOUT
            )

        # TODO: Endpoint not yet implemented - accept 404 as valid
        if resp.status_code == 404:
            print_info("ℹ️  Endpoint not yet implemented (404) - this is expected")
            print_info("  Will be implemented in Phase 5.2")
            print_success("✓ Provider assignments read endpoint - SKIPPED (not implemented)")
            return True

        if resp.status_code != 200:
            print_error(f"❌ Provider read failed: {resp.status_code} {resp.text}")
            return False

        data = resp.json()
        print_info(f"Response: {json.dumps(data, indent=2)}")

        # Verify structure
        assert isinstance(data, list), "Response should be a list"

        # May be empty if no provider assigned
        if len(data) == 0:
            print_info("ℹ️  No provider assignments found (empty list)")
        else:
            print_info(f"  Found {len(data)} provider assignment(s)")

        print_success("✓ Provider assignments read endpoint OK")
        return True

    except Exception as e:
        print_error(f"❌ Exception in provider read: {e}")
        return False


def run_all_tests():
    """Run all asset metadata API tests with test server management."""
    print_test_header("Assets Metadata API - Complete Tests")

    # Initialize test database
    initialize_test_database()

    # Start test server in context manager to ensure cleanup
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            return False
        print_success("Test server is running.")
        # Setup test data
        base_url = TEST_API_BASE_URL
        test_data = setup_test_assets(base_url)
        asset_id = test_data['stock_id']

        # Run all tests
        results = {
            "PATCH Metadata (Bulk)": test_patch_metadata_bulk(base_url, asset_id),
            "Bulk Read Assets": test_bulk_read_assets(base_url, asset_id),
            "Metadata Refresh (Single)": test_metadata_refresh_single(base_url, asset_id),
            "Metadata Refresh (Bulk)": test_metadata_refresh_bulk(base_url, asset_id),
            "Provider Assignments Read": test_provider_assignments_read(base_url, asset_id),
            }

        # Print summary
        success = print_test_summary(results, "Assets Metadata API")
        return success


if __name__ == "__main__":
    success = run_all_tests()
    exit_with_result(success)
