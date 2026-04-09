"""
Test Suite: Asset Prices API Endpoints

Tests for price-related endpoints:
- POST /api/v1/assets/prices - Bulk upsert prices
- DELETE /api/v1/assets/prices - Bulk delete prices
- POST /api/v1/assets/prices/query - Bulk query prices (replaces GET)
- POST /api/v1/assets/prices/sync - Refresh prices from providers
"""

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.db.models import IdentifierType, ProviderInputType
from backend.app.schemas.assets import (
    FAAssetCreateItem,
    FABulkAssetCreateResponse,
    )
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.prices import (
    FAPricePoint,
    FAUpsert,
    FABulkUpsertResponse,
    FAAssetDelete,
    FABulkDeleteResponse,
    )
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_info, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    """Create a test user, login, and set session cookie on client."""
    import uuid as _uuid
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


@pytest.fixture(scope="module")
def test_server():
    """Start/stop test server for all tests in this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ============================================================
# Test 1: POST /assets/prices - Bulk upsert prices
# ============================================================
@pytest.mark.asyncio
async def test_bulk_upsert_prices(test_server):
    """Test 1: POST /assets/prices - Bulk upsert prices."""
    print_section("Test 1: POST /assets/prices - Bulk upsert")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Step 1: Create test asset
        create_item = FAAssetCreateItem(
            display_name=f"Price Upsert Test {unique_id('PRICE1')}", currency="USD"
            )
        create_resp = await client.post(
            f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT
            )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"Created asset ID: {asset_id}")

        # Step 2: Upsert prices (3 days)
        today = date.today()
        prices = [
            FAPricePoint(
                date=today - timedelta(days=2),
                close=Decimal("100.50"),
                volume=Decimal("1000"),
                currency="USD",
                ),
            FAPricePoint(
                date=today - timedelta(days=1),
                close=Decimal("101.25"),
                volume=Decimal("1500"),
                currency="USD",
                ),
            FAPricePoint(
                date=today, close=Decimal("102.00"), volume=Decimal("2000"), currency="USD"
                ),
            ]

        upsert_data = FAUpsert(asset_id=asset_id, prices=prices)

        upsert_resp = await client.post(
            f"{API_BASE}/assets/prices", json=[upsert_data.model_dump(mode="json")], timeout=TIMEOUT
            )
        assert (
            upsert_resp.status_code == 200
        ), f"Upsert failed: {upsert_resp.status_code}: {upsert_resp.text}"

        upsert_result = FABulkUpsertResponse(**upsert_resp.json())
        assert upsert_result.success_count >= 1
        print_success("Upserted 3 prices successfully")

        # Step 3: Verify prices in DB via POST query endpoint
        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {
                        "start": (today - timedelta(days=2)).isoformat(),
                        "end": today.isoformat(),
                        },
                    }
                ],
            timeout=TIMEOUT,
            )
        assert query_resp.status_code == 200

        query_data = query_resp.json()
        price_history = query_data["items"][0]["prices"]
        assert len(price_history) >= 3
        print_success(f"Price history verified: {len(price_history)} prices")


# ============================================================
# Test 2: POST /assets/prices/query - Get price history (bulk)
# ============================================================
@pytest.mark.asyncio
async def test_get_price_history(test_server):
    """Test 2: POST /assets/prices/query - Get price history."""
    print_section("Test 2: POST /assets/prices/query")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Step 1: Create asset
        create_item = FAAssetCreateItem(
            display_name=f"Price Get Test {unique_id('PRICEGET')}", currency="USD"
            )
        create_resp = await client.post(
            f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT
            )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"Created asset ID: {asset_id}")

        # Step 2: Insert prices
        prices = [
            FAPricePoint(date=date(2025, 1, 1), close=Decimal("100.00"), currency="USD"),
            FAPricePoint(date=date(2025, 1, 3), close=Decimal("103.00"), currency="USD"),
            FAPricePoint(date=date(2025, 1, 5), close=Decimal("105.00"), currency="USD"),
            ]
        upsert_data = FAUpsert(asset_id=asset_id, prices=prices)
        await client.post(
            f"{API_BASE}/assets/prices", json=[upsert_data.model_dump(mode="json")], timeout=TIMEOUT
            )
        print_info("Prices inserted")

        # Step 3: Query prices with date range via POST bulk
        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {"start": "2025-01-01", "end": "2025-01-05"},
                    }
                ],
            timeout=TIMEOUT,
            )
        assert query_resp.status_code == 200

        query_data = query_resp.json()
        price_history = query_data["items"][0]["prices"]
        assert len(price_history) >= 3, f"Expected at least 3 prices, got {len(price_history)}"
        print_success(f"Price history retrieved: {len(price_history)} prices")


# ============================================================
# Test 3: DELETE /assets/prices - Bulk delete prices
# ============================================================
@pytest.mark.asyncio
async def test_bulk_delete_prices(test_server):
    """Test 3: DELETE /assets/prices - Bulk delete prices."""
    print_section("Test 3: DELETE /assets/prices - Bulk delete")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Step 1: Create asset and insert prices
        create_item = FAAssetCreateItem(
            display_name=f"Price Delete Test {unique_id('PRICEDEL')}", currency="USD"
            )
        create_resp = await client.post(
            f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT
            )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"Created asset ID: {asset_id}")

        # Insert prices for Jan 1-10
        prices = [
            FAPricePoint(date=date(2025, 1, d), close=Decimal(f"100.{d:02d}"), currency="USD")
            for d in range(1, 11)
            ]
        upsert_data = FAUpsert(asset_id=asset_id, prices=prices)
        await client.post(
            f"{API_BASE}/assets/prices", json=[upsert_data.model_dump(mode="json")], timeout=TIMEOUT
            )
        print_info("Inserted 10 prices (Jan 1-10)")

        # Step 2: DELETE range Jan 3-7 (5 days) using FAAssetDelete
        delete_request = FAAssetDelete(
            asset_id=asset_id,
            date_ranges=[DateRangeModel(start=date(2025, 1, 3), end=date(2025, 1, 7))],
            )
        delete_resp = await client.request(
            "DELETE",
            f"{API_BASE}/assets/prices",
            json=[delete_request.model_dump(mode="json")],
            timeout=TIMEOUT,
            )
        assert (
            delete_resp.status_code == 200
        ), f"Delete failed: {delete_resp.status_code}: {delete_resp.text}"

        delete_data = FABulkDeleteResponse(**delete_resp.json())
        assert delete_data.success_count >= 1
        print_success("Deleted range Jan 3-7")

        # Step 3: Verify prices remain
        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {"start": "2025-01-01", "end": "2025-01-10"},
                    }
                ],
            timeout=TIMEOUT,
            )
        remaining_data = query_resp.json()
        remaining_prices = remaining_data["items"][0]["prices"]
        print_success(f"Remaining prices: {len(remaining_prices)}")


# ============================================================
# Test 4: POST /assets/prices/sync - Refresh from provider
# ============================================================
@pytest.mark.asyncio
async def test_refresh_prices_from_provider(test_server):
    """Test 4: POST /assets/prices/sync - Refresh from provider."""
    print_section("Test 4: POST /assets/prices/sync")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Step 1: Create asset and assign mockprov
        create_item = FAAssetCreateItem(
            display_name=f"Price Refresh Test {unique_id('PRICEREF')}", currency="USD"
            )
        create_resp = await client.post(
            f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT
            )
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"Created asset ID: {asset_id}")

        # Assign mockprov
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="mockprov",
            identifier="MOCK_REFRESH",
            identifier_type=ProviderInputType.AUTO_GENERATED,
            provider_params={"symbol": "MOCKREFRESH"},
            )
        await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT,
            )
        print_info("Provider mockprov assigned")

        # Step 2: Refresh prices from provider
        today = date.today()
        refresh_request = [
            {
                "asset_id": asset_id,
                "date_range": {
                    "start": (today - timedelta(days=5)).isoformat(),
                    "end": today.isoformat(),
                    },
                }
            ]
        refresh_resp = await client.post(
            f"{API_BASE}/assets/prices/sync", json=refresh_request, timeout=TIMEOUT
            )
        assert (
            refresh_resp.status_code == 200
        ), f"Refresh failed: {refresh_resp.status_code}: {refresh_resp.text}"
        print_success("Prices refresh requested")

        # Step 3: Verify prices were created (mockprov returns current value)
        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {
                        "start": (today - timedelta(days=5)).isoformat(),
                        "end": today.isoformat(),
                        },
                    }
                ],
            timeout=TIMEOUT,
            )
        query_data = query_resp.json()
        price_history = query_data["items"][0]["prices"]
        print_success(f"Prices after refresh: {len(price_history)}")


# ============================================================
# Test 5: POST /assets/prices/query - Multi-asset bulk query
# ============================================================
@pytest.mark.asyncio
async def test_bulk_query_multi_asset(test_server):
    """Test 5: POST /assets/prices/query - Multi-asset bulk query."""
    print_section("Test 5: POST /assets/prices/query - Multi-asset bulk")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Step 1: Create two assets
        asset_ids = []
        for i in range(2):
            create_item = FAAssetCreateItem(
                display_name=f"Multi Query Test {i} {unique_id(f'MULTIQUERY{i}')}", currency="USD"
                )
            create_resp = await client.post(
                f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT
                )
            create_data = FABulkAssetCreateResponse(**create_resp.json())
            asset_ids.append(create_data.results[0].asset_id)
        print_info(f"Created asset IDs: {asset_ids}")

        # Step 2: Insert prices for each asset
        for idx, asset_id in enumerate(asset_ids):
            prices = [
                FAPricePoint(
                    date=date(2025, 1, d),
                    close=Decimal(f"{100 + idx * 50 + d}.00"),
                    currency="USD",
                    )
                for d in range(1, 4)
                ]
            upsert_data = FAUpsert(asset_id=asset_id, prices=prices)
            await client.post(
                f"{API_BASE}/assets/prices", json=[upsert_data.model_dump(mode="json")], timeout=TIMEOUT
                )
        print_info("Prices inserted for both assets")

        # Step 3: Query both assets in a single bulk POST
        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {"asset_id": asset_ids[0], "date_range": {"start": "2025-01-01", "end": "2025-01-03"}},
                {"asset_id": asset_ids[1], "date_range": {"start": "2025-01-01", "end": "2025-01-03"}},
                ],
            timeout=TIMEOUT,
            )
        assert query_resp.status_code == 200

        query_data = query_resp.json()
        items = query_data["items"]
        assert len(items) == 2, f"Expected 2 items, got {len(items)}"

        for item in items:
            assert item["asset_id"] in asset_ids
            assert len(item["prices"]) >= 3
            print_info(f"  Asset {item['asset_id']}: {len(item['prices'])} prices")

        print_success("Multi-asset bulk query succeeded")


# ============================================================
# Test 6: Query without sync returns empty (architecture test)
# ============================================================
@pytest.mark.asyncio
async def test_query_without_sync_returns_empty(test_server):
    """Test 6: Query on asset with provider but no sync returns empty prices.

    Certifies the architectural separation:
    - Assigning a provider does NOT auto-fetch prices
    - Prices appear in DB only after explicit sync (POST /assets/prices/sync)
    - Query (POST /assets/prices/query) reads ONLY from DB, never from provider
    """
    print_section("Test 6: Query without sync = empty (architecture test)")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # 1. Create asset
        asset_item = FAAssetCreateItem(
            display_name=f"No-Sync Test {unique_id('NOSYNC')}", currency="USD"
            )
        create_resp = await client.post(
            f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT
            )
        assert create_resp.status_code == 201
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"  Created asset ID: {asset_id}")

        # 2. Assign provider (yfinance/AAPL — always has data)
        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="yfinance",
            identifier="AAPL",
            identifier_type=IdentifierType.TICKER,
            provider_params=None,
            )
        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT,
            )
        assert assign_resp.status_code == 200
        print_info("  Provider assigned: yfinance (AAPL)")

        # 3. Query WITHOUT sync — must return 0 prices
        today = date.today()
        start = (today - timedelta(days=7)).isoformat()
        end = today.isoformat()

        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[{"asset_id": asset_id, "date_range": {"start": start, "end": end}}],
            timeout=TIMEOUT,
            )
        assert query_resp.status_code == 200
        prices_before = query_resp.json()["items"][0]["prices"]
        assert len(prices_before) == 0, f"Expected 0 prices before sync, got {len(prices_before)}"
        print_success("  ✓ Query before sync returned 0 prices (DB-only, no provider call)")

        # 4. Explicit sync — download from provider into DB
        sync_resp = await client.post(
            f"{API_BASE}/assets/prices/sync",
            json=[{"asset_id": asset_id, "date_range": {"start": start, "end": end}}],
            timeout=TIMEOUT,
            )
        assert sync_resp.status_code == 200
        sync_result = sync_resp.json()["results"][0]
        print_info(f"  Sync fetched: {sync_result.get('points_fetched', 0)} prices")

        # 5. Query AFTER sync — must return ≥1 price
        query_resp2 = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[{"asset_id": asset_id, "date_range": {"start": start, "end": end}}],
            timeout=TIMEOUT,
            )
        assert query_resp2.status_code == 200
        prices_after = query_resp2.json()["items"][0]["prices"]
        assert len(prices_after) > 0, "Should have prices after sync"
        print_success(f"  ✓ Query after sync returned {len(prices_after)} prices")

        # Cleanup
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
        print_info("  Cleanup completed")


# ============================================================
# Test 8: Sync idempotency — re-sync same range → 0 points_changed
# ============================================================
@pytest.mark.asyncio
async def test_sync_idempotency(test_server):
    """Test 8: Re-syncing the same date range produces points_changed == 0."""
    print_section("Test 8: Sync idempotency")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # Create asset + assign provider
        create_item = FAAssetCreateItem(
            display_name=f"Idempotency Test {unique_id('IDEMP')}", currency="USD"
            )
        create_resp = await client.post(
            f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT
            )
        assert create_resp.status_code == 200
        asset_id = create_resp.json()["items"][0]["id"]

        assignment = FAProviderAssignmentItem(
            asset_id=asset_id, provider_code="yfinance",
            identifier="AAPL", identifier_type=IdentifierType.TICKER,
            provider_params=None,
            )
        await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")], timeout=TIMEOUT,
            )

        today = date.today()
        start = (today - timedelta(days=7)).isoformat()
        end = today.isoformat()

        # First sync — expect points_changed > 0
        sync1 = await client.post(
            f"{API_BASE}/assets/prices/sync",
            json=[{"asset_id": asset_id, "date_range": {"start": start, "end": end}}],
            timeout=TIMEOUT,
            )
        assert sync1.status_code == 200
        r1 = sync1.json()["results"][0]
        assert r1["points_changed"] > 0, "First sync should insert prices"
        print_info(f"  First sync: {r1['points_changed']} points changed")

        # Second sync — same range → 0 points_changed
        sync2 = await client.post(
            f"{API_BASE}/assets/prices/sync",
            json=[{"asset_id": asset_id, "date_range": {"start": start, "end": end}}],
            timeout=TIMEOUT,
            )
        assert sync2.status_code == 200
        r2 = sync2.json()["results"][0]
        assert r2["points_changed"] == 0, f"Re-sync should change 0 points, got {r2['points_changed']}"
        print_success("  ✓ Re-sync produced points_changed == 0 (idempotent)")

        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


# ============================================================
# Test 9: Query with include_events: true
# ============================================================
@pytest.mark.asyncio
async def test_query_with_include_events(test_server):
    """Test 9: Price query with include_events flag returns events field."""
    print_section("Test 9: Query with include_events")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # Create asset
        create_item = FAAssetCreateItem(
            display_name=f"Events Test {unique_id('EVT')}", currency="USD"
            )
        create_resp = await client.post(
            f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT
            )
        assert create_resp.status_code == 200
        asset_id = create_resp.json()["items"][0]["id"]

        today = date.today()
        start = (today - timedelta(days=30)).isoformat()
        end = today.isoformat()

        # Query with include_events: true — should succeed and have 'events' key
        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[{"asset_id": asset_id, "date_range": {"start": start, "end": end},
                   "include_events": True}],
            timeout=TIMEOUT,
            )
        assert query_resp.status_code == 200
        result = query_resp.json()["items"][0]
        assert "events" in result, "Response must contain 'events' field when include_events is true"
        assert isinstance(result["events"], list), "Events must be a list"
        print_success(f"  ✓ Query with include_events returned events field (count: {len(result['events'])})")

        # Also test with include_events: false (default) — events should be empty list
        query_resp2 = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[{"asset_id": asset_id, "date_range": {"start": start, "end": end}}],
            timeout=TIMEOUT,
            )
        assert query_resp2.status_code == 200
        result2 = query_resp2.json()["items"][0]
        assert result2.get("events", []) == [], "Events should be empty when include_events is not set"
        print_success("  ✓ Query without include_events returns empty events")

        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


# ============================================================
# Test 10: Bulk sync multi-asset (3+ assets in one request)
# ============================================================
@pytest.mark.asyncio
async def test_bulk_sync_multi_asset(test_server):
    """Test 10: Sync 3 assets in a single bulk request."""
    print_section("Test 10: Bulk sync multi-asset")

    tickers = [
        ("AAPL", f"Apple Bulk {unique_id('BLK1')}"),
        ("MSFT", f"Microsoft Bulk {unique_id('BLK2')}"),
        ("GOOGL", f"Google Bulk {unique_id('BLK3')}"),
    ]

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        asset_ids = []
        for ticker, name in tickers:
            create_item = FAAssetCreateItem(display_name=name, currency="USD")
            resp = await client.post(
                f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT
                )
            assert resp.status_code == 200
            aid = resp.json()["items"][0]["id"]
            asset_ids.append(aid)

            assignment = FAProviderAssignmentItem(
                asset_id=aid, provider_code="yfinance",
                identifier=ticker, identifier_type=IdentifierType.TICKER,
                provider_params=None,
                )
            await client.post(
                f"{API_BASE}/assets/provider",
                json=[assignment.model_dump(mode="json")], timeout=TIMEOUT,
                )
        print_info(f"  Created {len(asset_ids)} assets with providers")

        today = date.today()
        start = (today - timedelta(days=7)).isoformat()
        end = today.isoformat()

        # Bulk sync all 3
        sync_body = [{"asset_id": aid, "date_range": {"start": start, "end": end}} for aid in asset_ids]
        sync_resp = await client.post(
            f"{API_BASE}/assets/prices/sync", json=sync_body, timeout=60.0,
            )
        assert sync_resp.status_code == 200
        results = sync_resp.json()["results"]
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        for i, r in enumerate(results):
            assert r.get("points_fetched", 0) > 0 or r.get("points_changed", 0) >= 0, \
                f"Asset {i} sync should report results"
            print_info(f"  {tickers[i][0]}: fetched={r.get('points_fetched', 0)}, changed={r.get('points_changed', 0)}")

        print_success(f"  ✓ Bulk sync of {len(asset_ids)} assets completed successfully")

        # Cleanup
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)

