"""
Test Suite: Asset PATCH - Base Fields (non-metadata)

Tests for PATCH /api/v1/assets endpoint covering base fields:
- display_name
- currency
- asset_type
- icon_url
- active

Metadata fields (classification_params) are tested in test_assets_metadata.py
"""

import pytest
import httpx

from backend.app.config import get_settings
# Import Pydantic schemas
from backend.app.schemas.assets import (
    FAAssetCreateItem,
    FAAssetPatchItem,
    FABulkAssetCreateResponse,
    FABulkAssetPatchResponse,
    FAAssetMetadataResponse,
    AssetType, FAinfoResponse
    )

# Test server fixture
from backend.test_scripts.test_server_helper import _TestingServerManager

# Constants
settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0

def unique_id(prefix: str = "TEST") -> str:
    """Generate unique ID for test data."""
    import time
    return f"{prefix}_{int(time.time() * 1000)}_{id(prefix) % 100}"

def print_section(title: str):
    """Print test section header."""
    print(f"\n{'=' * 60}\n  {title}\n{'=' * 60}")

def print_info(msg: str):
    """Print info message."""
    print(f"ℹ️  {msg}")

def print_success(msg: str):
    """Print success message."""
    print(f"✅ ✓ {msg}")


# Fixture: test server
@pytest.fixture(scope="module")
def test_server():
    """Start/stop test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager
        # Server automatically stopped by context manager


# ============================================================
# Test 1: PATCH display_name
# ============================================================
@pytest.mark.asyncio
async def test_patch_display_name(test_server):
    """Test 1: PATCH display_name field."""
    print_section("Test 1: PATCH /assets - display_name")

    async with httpx.AsyncClient() as client:
        # Step 1: Create test asset
        create_item = FAAssetCreateItem(
            display_name=f"Original Name {unique_id('PATCH1')}",
            currency="USD",
            asset_type=AssetType.STOCK
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[create_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        assert create_resp.status_code == 201
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: PATCH display_name
        new_name = f"Updated Name {unique_id('UPD1')}"
        patch_item = FAAssetPatchItem(
            asset_id=asset_id,
            display_name=new_name
        )
        patch_resp = await client.patch(
            f"{API_BASE}/assets",
            json=[patch_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        assert patch_resp.status_code == 200, f"PATCH failed: {patch_resp.status_code}: {patch_resp.text}"

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1
        assert "display_name" in patch_data.results[0].updated_fields
        print_success("✓ display_name patched successfully")

        # Step 3: Verify in DB
        read_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets = [FAAssetMetadataResponse(**a) for a in read_resp.json()]
        assert assets[0].display_name == new_name
        print_success("✓ DB verification passed")


# ============================================================
# Test 2: PATCH currency
# ============================================================
@pytest.mark.asyncio
async def test_patch_currency(test_server):
    """Test 2: PATCH currency field."""
    print_section("Test 2: PATCH /assets - currency")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset with USD currency
        create_item = FAAssetCreateItem(
            display_name=f"Currency Test {unique_id('PATCH2')}",
            currency="USD",
            asset_type=AssetType.STOCK
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[create_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id} with currency=USD")

        # Step 2: PATCH to EUR
        patch_item = FAAssetPatchItem(
            asset_id=asset_id,
            currency="EUR"
        )
        patch_resp = await client.patch(
            f"{API_BASE}/assets",
            json=[patch_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        assert patch_resp.status_code == 200

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1
        assert "currency" in patch_data.results[0].updated_fields
        print_success("✓ currency patched successfully")

        # Step 3: Verify in DB
        read_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets = [FAAssetMetadataResponse(**a) for a in read_resp.json()]
        assert assets[0].currency == "EUR"
        print_success("✓ DB verification passed (currency=EUR)")


# ============================================================
# Test 3: PATCH asset_type
# ============================================================
@pytest.mark.asyncio
async def test_patch_asset_type(test_server):
    """Test 3: PATCH asset_type field."""
    print_section("Test 3: PATCH /assets - asset_type")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset with STOCK type
        create_item = FAAssetCreateItem(
            display_name=f"Type Test {unique_id('PATCH3')}",
            currency="USD",
            asset_type=AssetType.STOCK
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[create_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id} with asset_type=STOCK")

        # Step 2: PATCH to ETF
        patch_item = FAAssetPatchItem(
            asset_id=asset_id,
            asset_type=AssetType.ETF
        )
        patch_resp = await client.patch(
            f"{API_BASE}/assets",
            json=[patch_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        assert patch_resp.status_code == 200

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1
        assert "asset_type" in patch_data.results[0].updated_fields
        print_success("✓ asset_type patched successfully")

        # Step 3: Verify in DB
        read_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets = [FAAssetMetadataResponse(**a) for a in read_resp.json()]
        assert assets[0].asset_type == AssetType.ETF
        print_success("✓ DB verification passed (asset_type=ETF)")


# ============================================================
# Test 4: PATCH icon_url
# ============================================================
@pytest.mark.asyncio
async def test_patch_icon_url(test_server):
    """Test 4: PATCH icon_url field."""
    print_section("Test 4: PATCH /assets - icon_url")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset without icon_url
        create_item = FAAssetCreateItem(
            display_name=f"Icon Test {unique_id('PATCH4')}",
            currency="USD"
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[create_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id} without icon_url")

        # Step 2: PATCH icon_url
        new_icon_url = "https://example.com/icon.png"
        patch_item = FAAssetPatchItem(
            asset_id=asset_id,
            icon_url=new_icon_url
        )
        patch_resp = await client.patch(
            f"{API_BASE}/assets",
            json=[patch_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        assert patch_resp.status_code == 200

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1
        assert "icon_url" in patch_data.results[0].updated_fields
        print_success("✓ icon_url patched successfully")

        # Step 3: Verify in DB
        read_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets = [FAAssetMetadataResponse(**a) for a in read_resp.json()]
        assert assets[0].icon_url == new_icon_url
        print_success("✓ DB verification passed (icon_url set)")

        # Step 4: Clear icon_url with empty string
        patch_clear = FAAssetPatchItem(
            asset_id=asset_id,
            icon_url=""
        )
        patch_clear_resp = await client.patch(
            f"{API_BASE}/assets",
            json=[patch_clear.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        assert patch_clear_resp.status_code == 200
        print_success("✓ icon_url cleared successfully")

        # Step 5: Verify icon_url is None in DB
        read_cleared = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets_cleared = [FAAssetMetadataResponse(**a) for a in read_cleared.json()]
        assert assets_cleared[0].icon_url is None
        print_success("✓ DB verification passed (icon_url=None)")


# ============================================================
# Test 5: PATCH icon_url clear (None)
# ============================================================
@pytest.mark.asyncio
async def test_patch_icon_url_clear(test_server):
    """Test 5: PATCH icon_url=None to clear field."""
    print_section("Test 5: PATCH /assets - icon_url clear")
    # TODO: Implementare test


# ============================================================
# Test 6: PATCH active
# ============================================================
@pytest.mark.asyncio
async def test_patch_active(test_server):
    """Test 6: PATCH active field."""
    print_section("Test 6: PATCH /assets - active")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset (active=True by default)
        create_item = FAAssetCreateItem(
            display_name=f"Active Test {unique_id('PATCH6')}",
            currency="USD",
            asset_type=AssetType.STOCK
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[create_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id} (active=True)")

        # Step 2: PATCH active to False
        patch_item = FAAssetPatchItem(
            asset_id=asset_id,
            active=False
        )
        patch_resp = await client.patch(
            f"{API_BASE}/assets",
            json=[patch_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        assert patch_resp.status_code == 200

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1
        assert "active" in patch_data.results[0].updated_fields
        print_success("✓ active patched to False")

        # Step 3: Verify: asset NOT in active=true filter
        list_resp = await client.get(f"{API_BASE}/assets/query", params={"active": True}, timeout=TIMEOUT)
        list_data = [FAinfoResponse(**item) for item in list_resp.json()]
        asset_ids_active = [a.asset_id for a in list_data]
        assert asset_id not in asset_ids_active, "Asset should NOT appear in active=true filter"
        print_success("✓ Asset correctly filtered out when active=false")


# ============================================================
# Test 7: PATCH multiple base fields
# ============================================================
@pytest.mark.asyncio
async def test_patch_multiple_base_fields(test_server):
    """Test 7: PATCH multiple base fields simultaneously."""
    print_section("Test 7: PATCH /assets - Multiple Base Fields")

    async with httpx.AsyncClient() as client:
        # Step 1: Create asset
        create_item = FAAssetCreateItem(
            display_name=f"Multi Patch {unique_id('PATCH7')}",
            currency="USD",
            asset_type=AssetType.STOCK
        )
        create_resp = await client.post(
            f"{API_BASE}/assets",
            json=[create_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: PATCH multiple fields at once
        patch_item = FAAssetPatchItem(
            asset_id=asset_id,
            display_name="Multi Patched Name",
            currency="EUR",
            asset_type=AssetType.ETF,
            icon_url="https://multi.test/icon.png"
        )
        patch_resp = await client.patch(
            f"{API_BASE}/assets",
            json=[patch_item.model_dump(mode="json")],
            timeout=TIMEOUT
        )
        assert patch_resp.status_code == 200

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1

        # Verify all fields in updated_fields
        updated = patch_data.results[0].updated_fields
        assert "display_name" in updated
        assert "currency" in updated
        assert "asset_type" in updated
        assert "icon_url" in updated
        print_success(f"✓ All fields patched: {updated}")

        # Step 3: Verify in DB
        read_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets = [FAAssetMetadataResponse(**a) for a in read_resp.json()]
        asset = assets[0]
        assert asset.display_name == "Multi Patched Name"
        assert asset.currency == "EUR"
        assert asset.asset_type == AssetType.ETF
        assert asset.icon_url == "https://multi.test/icon.png"
        print_success("✓ DB verification passed (all fields updated)")

