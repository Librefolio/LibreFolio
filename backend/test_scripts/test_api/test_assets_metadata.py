"""
Asset bulk read API tests: GET /api/v1/assets (several assets, in request order).

Plan 68, D7a: the description, countries and sectors of an asset live in its profile. The tests that pinned the old
``classification_params`` written through ``PATCH /assets`` went with it; the profile's own are in
``test_assets_profile.py`` and ``test_assets_profile_read.py``.
"""

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.db import AssetType
from backend.app.schemas import (
    FAAssetCreateItem,
    FAAssetMetadataResponse,
    FABulkAssetCreateResponse,
)
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30


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


# ============================================================================
# PYTEST FIXTURES
# ============================================================================


@pytest.fixture(scope="module")
def test_server():
    """
    Start test server once for all tests in this module.

    The server will be automatically started before tests run and stopped after.
    """
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager
        # Server automatically stopped by context manager


async def create_test_asset(name_prefix: str = "META") -> int:
    """
    Helper function to create a test asset for metadata tests.

    Returns the asset ID.
    """
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        item = FAAssetCreateItem(
            display_name=f"{name_prefix} Test Asset {unique_id(name_prefix)}",
            currency="USD",
            asset_type=AssetType.STOCK,
        )

        response = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
        assert response.status_code == 201, f"Failed to create test asset: {response.text}"

        data = FABulkAssetCreateResponse(**response.json())
        assert data.success_count == 1, "Asset creation failed"
        return data.results[0].asset_id


# ============================================================================
# TEST FUNCTIONS
# ============================================================================


@pytest.mark.asyncio
async def test_bulk_read_assets(test_server):
    """Test 1: GET /assets (bulk read)."""
    print_section("Test 1: GET /assets - Bulk Read")

    test_asset = await create_test_asset("READ1")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        response = await client.get(f"{API_BASE}/assets", params={"asset_ids": [test_asset]}, timeout=TIMEOUT)

        assert response.status_code == 200, f"Bulk read failed: {response.status_code}: {response.text}"

        assets = [FAAssetMetadataResponse(**a) for a in response.json()]
        assert len(assets) > 0, "Should return at least one asset"

        asset = assets[0]
        assert asset.asset_id == test_asset, "Asset ID mismatch"
        assert asset.display_name, "Asset should have display_name"
        assert asset.currency, "Asset should have currency"

        print_success("✓ Bulk read returned the asset")


@pytest.mark.asyncio
async def test_bulk_read_multiple_assets(test_server):
    """Test 2: GET /assets (bulk read of several assets, in request order)."""
    print_section("Test 2: GET /assets - Bulk Read Multiple Assets")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Create multiple test assets
        items = [
            FAAssetCreateItem(
                display_name=f"Test Asset {i} {unique_id(f'BULK{i}')}",
                currency="USD",
                asset_type=AssetType.STOCK,
            )
            for i in range(3)
        ]

        create_response = await client.post(f"{API_BASE}/assets", json=[a.model_dump(mode="json") for a in items], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_response.json())
        asset_ids = [r.asset_id for r in create_data.results if r.success]

        assert len(asset_ids) == 3, "Should have created 3 assets"

        # Bulk read
        response = await client.get(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)

        assert response.status_code == 200, f"Bulk read failed: {response.status_code}"

        assets = [FAAssetMetadataResponse(**a) for a in response.json()]
        assert len(assets) == 3, f"Expected 3 assets, got {len(assets)}"

        # Verify order preserved (request order)
        for i, asset_id in enumerate(asset_ids):
            assert assets[i].asset_id == asset_id, f"Order not preserved at index {i}"

        print_success("✓ Bulk read multiple assets OK (order preserved)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
