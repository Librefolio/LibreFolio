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

import httpx
import pytest

from backend.app.config import get_settings

# Import Pydantic schemas
from backend.app.db.models import AssetType
from backend.app.schemas.assets.assets import (
    FAAssetCreateItem,
    FAAssetPatchItem,
    FABulkAssetCreateResponse,
    FABulkAssetPatchResponse,
    FAinfoResponse,
)
from backend.app.schemas.assets.metadata import FAAssetMetadataResponse

# Test server fixture
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success, unique_id

# Constants
settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    """Create a test user, login, and set session cookie on client."""
    import uuid as _uuid  # noqa: PLC0415 — test setup — imports after sys.path/db config

    username = f"test_{int(__import__('time').time() * 1000)}_{_uuid.uuid4().hex[:4]}"
    email = f"{username}@test.com"
    password = "TestPass123!"
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    if resp.status_code != 201:
        raise Exception(f"Failed to create user: {resp.text}")
    login_resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    if login_resp.status_code != 200:
        raise Exception(f"Failed to login: {login_resp.text}")
    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)


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
        await create_user_and_login(client)
        # Step 1: Create test asset
        create_item = FAAssetCreateItem(
            display_name=f"Original Name {unique_id('PATCH1')}",
            currency="USD",
            asset_type=AssetType.STOCK,
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: PATCH display_name
        new_name = f"Updated Name {unique_id('UPD1')}"
        patch_item = FAAssetPatchItem(asset_id=asset_id, display_name=new_name)
        patch_resp = await client.patch(f"{API_BASE}/assets", json=[patch_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert patch_resp.status_code == 200, f"PATCH failed: {patch_resp.status_code}: {patch_resp.text}"

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1
        assert any(item.info == "display_name" for item in patch_data.results[0].updated_fields)
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
        await create_user_and_login(client)
        # Step 1: Create asset with USD currency
        create_item = FAAssetCreateItem(
            display_name=f"Currency Test {unique_id('PATCH2')}",
            currency="USD",
            asset_type=AssetType.STOCK,
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id} with currency=USD")

        # Step 2: PATCH to EUR
        patch_item = FAAssetPatchItem(asset_id=asset_id, currency="EUR")
        patch_resp = await client.patch(f"{API_BASE}/assets", json=[patch_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert patch_resp.status_code == 200

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1
        assert any(item.info == "currency" for item in patch_data.results[0].updated_fields)
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
        await create_user_and_login(client)
        # Step 1: Create asset with STOCK type
        create_item = FAAssetCreateItem(
            display_name=f"Type Test {unique_id('PATCH3')}",
            currency="USD",
            asset_type=AssetType.STOCK,
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id} with asset_type=STOCK")

        # Step 2: PATCH to ETF
        patch_item = FAAssetPatchItem(asset_id=asset_id, asset_type=AssetType.ETF)
        patch_resp = await client.patch(f"{API_BASE}/assets", json=[patch_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert patch_resp.status_code == 200

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1
        assert any(item.info == "asset_type" for item in patch_data.results[0].updated_fields)
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
        await create_user_and_login(client)
        # Step 1: Create asset without icon_url
        create_item = FAAssetCreateItem(display_name=f"Icon Test {unique_id('PATCH4')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id} without icon_url")

        # Step 2: PATCH icon_url
        new_icon_url = "https://example.com/icon.png"
        patch_item = FAAssetPatchItem(asset_id=asset_id, icon_url=new_icon_url)
        patch_resp = await client.patch(f"{API_BASE}/assets", json=[patch_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert patch_resp.status_code == 200

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1
        assert any(item.info == "icon_url" for item in patch_data.results[0].updated_fields)
        print_success("✓ icon_url patched successfully")

        # Step 3: Verify in DB
        read_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets = [FAAssetMetadataResponse(**a) for a in read_resp.json()]
        assert assets[0].icon_url == new_icon_url
        print_success("✓ DB verification passed (icon_url set)")

        # Step 4: Clear icon_url with empty string
        patch_clear = FAAssetPatchItem(asset_id=asset_id, icon_url="")
        patch_clear_resp = await client.patch(f"{API_BASE}/assets", json=[patch_clear.model_dump(mode="json")], timeout=TIMEOUT)
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

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Step 1: Create asset with icon_url
        create_item = FAAssetCreateItem(
            display_name=f"Icon Clear Test {unique_id('ICONCLR')}",
            currency="USD",
            asset_type=AssetType.STOCK,
            icon_url="http://example.com/icon.png",
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Create failed: {create_resp.status_code}"
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset {asset_id} with icon_url")

        # Step 2: Verify icon_url is set
        read_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assert read_resp.status_code == 200
        asset_data = [FAAssetMetadataResponse(**a) for a in read_resp.json()][0]
        assert asset_data.icon_url == "http://example.com/icon.png"
        print_info(f"  ✓ icon_url verified: {asset_data.icon_url}")

        # Step 3: PATCH icon_url to clear (empty string → backend converts to None)
        patch_item = FAAssetPatchItem(asset_id=asset_id, icon_url="")
        patch_resp = await client.patch(f"{API_BASE}/assets", json=[patch_item.model_dump(mode="json", exclude_unset=True)], timeout=TIMEOUT)
        assert patch_resp.status_code == 200, f"PATCH failed: {patch_resp.status_code}"
        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1
        print_success("✓ PATCH request succeeded")

        # Step 4: Verify icon_url is cleared (None)
        read_after = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assert read_after.status_code == 200
        asset_after = [FAAssetMetadataResponse(**a) for a in read_after.json()][0]
        assert asset_after.icon_url is None, f"Expected None, got {asset_after.icon_url}"
        print_success("✓ icon_url cleared successfully (None)")


async def _info_of(client: httpx.AsyncClient, asset_id: int) -> FAinfoResponse:
    """The asset as ``GET /assets/query`` lists it (it carries the user URL and the identifiers), found by id."""
    resp = await client.get(f"{API_BASE}/assets/query", timeout=TIMEOUT)
    assert resp.status_code == 200, f"query failed: {resp.status_code}"
    found = next((FAinfoResponse(**row) for row in resp.json() if row["id"] == asset_id), None)
    assert found is not None, f"asset {asset_id} not listed by /assets/query"
    return found


# ============================================================
# Test 5b: an explicit null clears the nullable columns (T-2)
# ============================================================
@pytest.mark.asyncio
async def test_patch_explicit_null_clears_icon_url_user_url_and_identifier(test_server):
    """T-2 — the edit modal removes an icon by sending ``"icon_url": null``: the server must clear it, not answer success and
    keep the old address. The same holds for the user URL and a single identifier; a null on the name changes nothing, and a
    field left out of the patch keeps its value."""
    print_section("Test 5b: PATCH /assets - explicit null clears")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        name = f"Null Clear Test {unique_id('NULLCLR')}"
        create_item = FAAssetCreateItem(
            display_name=name,
            currency="USD",
            asset_type=AssetType.STOCK,
            icon_url="https://example.com/own-icon.png",
            user_url="https://example.com/notes",
            identifier_isin="US0378331005",
            identifier_ticker=unique_id("TK")[:20],
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Create failed: {create_resp.status_code}: {create_resp.text}"
        asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id
        before = await _info_of(client, asset_id)
        assert before.icon_url and before.user_url and before.identifier_isin and before.identifier_ticker

        # The wire shape the frontend sends: raw JSON with explicit nulls, no Pydantic dump in between.
        patch_json = [{"asset_id": asset_id, "icon_url": None, "user_url": None, "identifier_isin": None, "display_name": None}]
        patch_resp = await client.patch(f"{API_BASE}/assets", json=patch_json, timeout=TIMEOUT)
        assert patch_resp.status_code == 200, f"PATCH failed: {patch_resp.status_code}: {patch_resp.text}"
        result = FABulkAssetPatchResponse(**patch_resp.json()).results[0]
        assert result.success, result.message
        assert {item.info for item in result.updated_fields} == {"icon_url", "user_url", "identifier_isin"}

        after = await _info_of(client, asset_id)
        assert after.icon_url is None, f"icon_url kept: {after.icon_url}"
        assert after.user_url is None, f"user_url kept: {after.user_url}"
        assert after.identifier_isin is None, f"identifier_isin kept: {after.identifier_isin}"
        assert after.display_name == name, "a null on the name must not change it"
        assert after.identifier_ticker == before.identifier_ticker, "a field left out of the patch keeps its value"
        print_success("✓ explicit null cleared icon_url, user_url and identifier_isin; name and ticker kept")


# ============================================================
# Test 5c: an explicit empty list clears identifier_other
# ============================================================
@pytest.mark.asyncio
async def test_patch_explicit_empty_list_clears_identifier_other(test_server):
    """The edit modal sends ``"identifier_other": []`` when the user removes the last OTHER identifier: the server must clear
    the list. ``null`` keeps it (the schema reads it as "leave unchanged"), and the single identifiers are not touched."""
    print_section("Test 5c: PATCH /assets - identifier_other [] clears, null keeps")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        others = [unique_id("OTHER-A"), unique_id("OTHER-B")]
        create_item = FAAssetCreateItem(
            display_name=f"Other Clear Test {unique_id('OTHCLR')}",
            currency="EUR",
            asset_type=AssetType.BOND,
            identifier_isin="IT0005634800",
            identifier_ticker=unique_id("TK")[:20],
            identifier_other=others,
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201, f"Create failed: {create_resp.status_code}: {create_resp.text}"
        asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id
        before = await _info_of(client, asset_id)
        assert before.identifier_other == others

        # null: the list stays as it is, and nothing is reported as updated.
        null_resp = await client.patch(f"{API_BASE}/assets", json=[{"asset_id": asset_id, "identifier_other": None}], timeout=TIMEOUT)
        assert null_resp.status_code == 200, f"PATCH failed: {null_resp.status_code}: {null_resp.text}"
        null_result = FABulkAssetPatchResponse(**null_resp.json()).results[0]
        assert null_result.success, null_result.message
        assert not null_result.updated_fields, f"null must change nothing: {null_result.updated_fields}"
        assert (await _info_of(client, asset_id)).identifier_other == others, "null must keep identifier_other"

        # []: the list is cleared, and only that field is reported.
        empty_resp = await client.patch(f"{API_BASE}/assets", json=[{"asset_id": asset_id, "identifier_other": []}], timeout=TIMEOUT)
        assert empty_resp.status_code == 200, f"PATCH failed: {empty_resp.status_code}: {empty_resp.text}"
        empty_result = FABulkAssetPatchResponse(**empty_resp.json()).results[0]
        assert empty_result.success, empty_result.message
        assert [item.info for item in empty_result.updated_fields] == ["identifier_other"]

        after = await _info_of(client, asset_id)
        assert not after.identifier_other, f"identifier_other kept: {after.identifier_other}"
        assert after.identifier_isin == before.identifier_isin, "the ISIN must not change"
        assert after.identifier_ticker == before.identifier_ticker, "the ticker must not change"
        print_success("✓ identifier_other: null kept it, [] cleared it; ISIN and ticker kept")


# ============================================================
# Test 6: PATCH active
# ============================================================
@pytest.mark.asyncio
async def test_patch_active(test_server):
    """Test 6: PATCH active field."""
    print_section("Test 6: PATCH /assets - active")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Step 1: Create asset (active=True by default)
        create_item = FAAssetCreateItem(
            display_name=f"Active Test {unique_id('PATCH6')}",
            currency="USD",
            asset_type=AssetType.STOCK,
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id} (active=True)")

        # Step 2: PATCH active to False
        patch_item = FAAssetPatchItem(asset_id=asset_id, active=False)
        patch_resp = await client.patch(f"{API_BASE}/assets", json=[patch_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert patch_resp.status_code == 200

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1
        assert any(item.info == "active" for item in patch_data.results[0].updated_fields)
        print_success("✓ active patched to False")

        # Step 3: Verify via /assets/query (active=true should NOT include this asset)
        list_resp = await client.get(f"{API_BASE}/assets/query", params={"active": "true"}, timeout=TIMEOUT)
        assert list_resp.status_code == 200
        # FAinfoResponse uses 'id' (not 'asset_id')
        active_ids = [item["id"] for item in list_resp.json()]
        assert asset_id not in active_ids, "Deactivated asset should NOT appear in active=true query"
        print_success("✓ Asset correctly filtered out when active=false")


# ============================================================
# Test 7: PATCH multiple base fields
# ============================================================
@pytest.mark.asyncio
async def test_patch_multiple_base_fields(test_server):
    """Test 7: PATCH multiple base fields simultaneously."""
    print_section("Test 7: PATCH /assets - Multiple Base Fields")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Step 1: Create asset
        create_item = FAAssetCreateItem(
            display_name=f"Multi Patch {unique_id('PATCH7')}",
            currency="USD",
            asset_type=AssetType.STOCK,
        )
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # Step 2: PATCH multiple fields at once
        new_name = f"Multi Patched Name {unique_id('UPD7')}"
        patch_item = FAAssetPatchItem(
            asset_id=asset_id,
            display_name=new_name,
            currency="EUR",
            asset_type=AssetType.ETF,
            icon_url="https://multi.test/icon.png",
        )
        patch_resp = await client.patch(f"{API_BASE}/assets", json=[patch_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert patch_resp.status_code == 200

        patch_data = FABulkAssetPatchResponse(**patch_resp.json())
        assert patch_data.success_count == 1

        # Verify all fields in updated_fields
        updated = patch_data.results[0].updated_fields
        assert any(item.info == "display_name" for item in updated)
        assert any(item.info == "currency" for item in updated)
        assert any(item.info == "asset_type" for item in updated)
        assert any(item.info == "icon_url" for item in updated)
        print_success(f"✓ All fields patched: {updated}")
        # Step 3: Verify in DB
        read_resp = await client.get(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        assets = [FAAssetMetadataResponse(**a) for a in read_resp.json()]
        asset = assets[0]
        assert asset.display_name == new_name
        assert asset.currency == "EUR"
        assert asset.asset_type == AssetType.ETF
        assert asset.icon_url == "https://multi.test/icon.png"
        print_success("✓ DB verification passed (all fields updated)")
