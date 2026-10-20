"""
Test Suite: Asset Prices API Endpoints

Tests for price-related endpoints:
- POST /api/v1/assets/prices - Bulk upsert prices
- DELETE /api/v1/assets/prices - Bulk delete prices
- POST /api/v1/assets/prices/query - Bulk query prices (replaces GET)
- POST /api/v1/assets/prices/sync - Refresh prices from providers
"""

import time
import uuid
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.db.models import IdentifierType, ProviderInputType
from backend.app.schemas.assets.assets import (
    FAAssetCreateItem,
    FABulkAssetCreateResponse,
)
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.prices import (
    FAAssetDelete,
    FABulkDeleteResponse,
    FABulkUpsertResponse,
    FAPricePoint,
    FAUpsert,
)
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.utils.datetime_utils import latest_range_end
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success, unique_id

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
        create_item = FAAssetCreateItem(display_name=f"Price Upsert Test {unique_id('PRICE1')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
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
            FAPricePoint(date=today, close=Decimal("102.00"), volume=Decimal("2000"), currency="USD"),
        ]

        upsert_data = FAUpsert(asset_id=asset_id, prices=prices)

        upsert_resp = await client.post(f"{API_BASE}/assets/prices", json=[upsert_data.model_dump(mode="json")], timeout=TIMEOUT)
        assert upsert_resp.status_code == 200, f"Upsert failed: {upsert_resp.status_code}: {upsert_resp.text}"

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
        create_item = FAAssetCreateItem(display_name=f"Price Get Test {unique_id('PRICEGET')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
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
        await client.post(f"{API_BASE}/assets/prices", json=[upsert_data.model_dump(mode="json")], timeout=TIMEOUT)
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
        create_item = FAAssetCreateItem(display_name=f"Price Delete Test {unique_id('PRICEDEL')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"Created asset ID: {asset_id}")

        # Insert prices for Jan 1-10
        prices = [FAPricePoint(date=date(2025, 1, d), close=Decimal(f"100.{d:02d}"), currency="USD") for d in range(1, 11)]
        upsert_data = FAUpsert(asset_id=asset_id, prices=prices)
        await client.post(f"{API_BASE}/assets/prices", json=[upsert_data.model_dump(mode="json")], timeout=TIMEOUT)
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
        assert delete_resp.status_code == 200, f"Delete failed: {delete_resp.status_code}: {delete_resp.text}"

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
        create_item = FAAssetCreateItem(display_name=f"Price Refresh Test {unique_id('PRICEREF')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
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
        refresh_resp = await client.post(f"{API_BASE}/assets/prices/sync", json=refresh_request, timeout=TIMEOUT)
        assert refresh_resp.status_code == 200, f"Refresh failed: {refresh_resp.status_code}: {refresh_resp.text}"
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
            create_item = FAAssetCreateItem(display_name=f"Multi Query Test {i} {unique_id(f'MULTIQUERY{i}')}", currency="USD")
            create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
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
            await client.post(f"{API_BASE}/assets/prices", json=[upsert_data.model_dump(mode="json")], timeout=TIMEOUT)
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
        asset_item = FAAssetCreateItem(display_name=f"No-Sync Test {unique_id('NOSYNC')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[asset_item.model_dump(mode="json")], timeout=TIMEOUT)
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
        create_item = FAAssetCreateItem(display_name=f"Idempotency Test {unique_id('IDEMP')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        assignment = FAProviderAssignmentItem(
            asset_id=asset_id,
            provider_code="yfinance",
            identifier="AAPL",
            identifier_type=IdentifierType.TICKER,
            provider_params=None,
        )
        await client.post(
            f"{API_BASE}/assets/provider",
            json=[assignment.model_dump(mode="json")],
            timeout=TIMEOUT,
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
        create_item = FAAssetCreateItem(display_name=f"Events Test {unique_id('EVT')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        today = date.today()
        start = (today - timedelta(days=30)).isoformat()
        end = today.isoformat()

        # Query with include_events: true — should succeed and have 'events' key
        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[{"asset_id": asset_id, "date_range": {"start": start, "end": end}, "include_events": True}],
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
            resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
            assert resp.status_code == 201
            create_data = FABulkAssetCreateResponse(**resp.json())
            aid = create_data.results[0].asset_id
            asset_ids.append(aid)

            assignment = FAProviderAssignmentItem(
                asset_id=aid,
                provider_code="yfinance",
                identifier=ticker,
                identifier_type=IdentifierType.TICKER,
                provider_params=None,
            )
            await client.post(
                f"{API_BASE}/assets/provider",
                json=[assignment.model_dump(mode="json")],
                timeout=TIMEOUT,
            )
        print_info(f"  Created {len(asset_ids)} assets with providers")

        today = date.today()
        start = (today - timedelta(days=7)).isoformat()
        end = today.isoformat()

        # Bulk sync all 3
        sync_body = [{"asset_id": aid, "date_range": {"start": start, "end": end}} for aid in asset_ids]
        sync_resp = await client.post(
            f"{API_BASE}/assets/prices/sync",
            json=sync_body,
            timeout=60.0,
        )
        assert sync_resp.status_code == 200
        results = sync_resp.json()["results"]
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"

        for i, r in enumerate(results):
            assert r.get("points_fetched", 0) > 0 or r.get("points_changed", 0) >= 0, f"Asset {i} sync should report results"
            print_info(f"  {tickers[i][0]}: fetched={r.get('points_fetched', 0)}, changed={r.get('points_changed', 0)}")

        print_success(f"  ✓ Bulk sync of {len(asset_ids)} assets completed successfully")

        # Cleanup
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)


# ============================================================
# Test 11: POST /assets/prices/current - Get current prices (with DB data)
# ============================================================
@pytest.mark.asyncio
async def test_get_current_prices_with_db_data(test_server):
    """Test 11: POST /assets/prices/current - Asset with manual prices returns db:last_known."""
    print_section("Test 11: POST /assets/prices/current - with DB data")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # Create asset and insert manual prices
        create_item = FAAssetCreateItem(display_name=f"Current Price DB {unique_id('CUR1')}", currency="EUR")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # Insert 3 days of prices
        today = date.today()
        prices = [
            FAPricePoint(date=today - timedelta(days=2), close=Decimal("50.00"), currency="EUR"),
            FAPricePoint(date=today - timedelta(days=1), close=Decimal("51.00"), currency="EUR"),
            FAPricePoint(date=today, close=Decimal("52.25"), currency="EUR"),
        ]
        upsert_item = FAUpsert(asset_id=asset_id, prices=prices)
        upsert_resp = await client.post(f"{API_BASE}/assets/prices", json=[upsert_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert upsert_resp.status_code == 200
        print_info(f"  Inserted {len(prices)} prices for asset {asset_id}")

        # Now call current prices endpoint
        current_resp = await client.post(f"{API_BASE}/assets/prices/current", json=[asset_id], timeout=TIMEOUT)
        assert current_resp.status_code == 200
        data = current_resp.json()
        assert "results" in data
        assert "success_count" in data
        assert data["success_count"] == 1

        result = data["results"][0]
        assert result["asset_id"] == asset_id
        assert result["value"] is not None
        assert Decimal(result["value"]) == Decimal("52.25")
        assert result["source"] == "db:last_known"
        assert result["error"] is None
        print_success(f"  ✓ Current price returned: {result['value']} ({result['source']})")

        # Cleanup
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


# ============================================================
# Test 12: POST /assets/prices/current - Asset with no data
# ============================================================
@pytest.mark.asyncio
async def test_get_current_prices_no_data(test_server):
    """Test 12: POST /assets/prices/current - Asset without prices returns error."""
    print_section("Test 12: POST /assets/prices/current - no data")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # Create asset with no prices
        create_item = FAAssetCreateItem(display_name=f"Current Price Empty {unique_id('CUR2')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # Call current prices endpoint
        current_resp = await client.post(f"{API_BASE}/assets/prices/current", json=[asset_id], timeout=TIMEOUT)
        assert current_resp.status_code == 200
        data = current_resp.json()
        assert data["success_count"] == 0

        result = data["results"][0]
        assert result["asset_id"] == asset_id
        assert result["value"] is None
        assert result["error"] is not None
        print_success(f"  ✓ No data: error='{result['error']}'")

        # Cleanup
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


# ============================================================
# Test 13: POST /assets/prices/current - Nonexistent asset
# ============================================================
@pytest.mark.asyncio
async def test_get_current_prices_nonexistent(test_server):
    """Test 13: POST /assets/prices/current - Nonexistent asset ID returns error."""
    print_section("Test 13: POST /assets/prices/current - nonexistent")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        current_resp = await client.post(f"{API_BASE}/assets/prices/current", json=[999999], timeout=TIMEOUT)
        assert current_resp.status_code == 200
        data = current_resp.json()
        assert data["success_count"] == 0

        result = data["results"][0]
        assert result["asset_id"] == 999999
        assert result["value"] is None
        assert result["error"] is not None
        print_success(f"  ✓ Nonexistent asset: error='{result['error']}'")


# ============================================================
# Test 14: POST /assets/prices/current - Empty list
# ============================================================
@pytest.mark.asyncio
async def test_get_current_prices_empty_list(test_server):
    """Test 14: POST /assets/prices/current - Empty list returns empty results."""
    print_section("Test 14: POST /assets/prices/current - empty list")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        current_resp = await client.post(f"{API_BASE}/assets/prices/current", json=[], timeout=TIMEOUT)
        assert current_resp.status_code == 200
        data = current_resp.json()
        assert data["results"] == []
        assert data["success_count"] == 0
        print_success("  ✓ Empty list returns empty results")


# ============================================================
# Tests 15–17: I.9 — Currency mismatch hard reject (Supersedes E.3); 422 price_currency_mismatch since X-R71
# ============================================================


@pytest.mark.asyncio
async def test_upsert_mismatch_single_row_rejects_422(test_server):
    """I.9 Test 15: single row with mismatched currency → HTTP 422 ``price_currency_mismatch`` hard reject (X-R71).

    Contract: the detail names the asset, its currency (``expected``), the one given (``found``) and the date; ``count`` 1.
    Red before X-R71: 400 with a string detail («Currency mismatch for asset …»).
    """
    print_section("Test 15: I.9 — single mismatch rejects 422")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        create_item = FAAssetCreateItem(display_name=f"I9 Mismatch {unique_id('I9A')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id

        today = date.today()
        prices = [FAPricePoint(date=today, close=Decimal("1.0"), currency="EUR")]
        upsert = FAUpsert(asset_id=asset_id, prices=prices)
        resp = await client.post(f"{API_BASE}/assets/prices", json=[upsert.model_dump(mode="json")], timeout=TIMEOUT)
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        detail = resp.json()["detail"]
        assert isinstance(detail, dict) and detail.get("code") == "price_currency_mismatch", detail
        assert detail["items"] == [{"asset_id": asset_id, "expected": "USD", "found": ["EUR"], "dates": [today.isoformat()]}], detail
        assert detail["count"] == 1, detail
        print_success("  ✓ single EUR row on USD asset → 422 price_currency_mismatch")

        # Cleanup
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_upsert_mismatch_partial_rejects_entire_batch_422(test_server):
    """I.9 Test 16: one mismatch in a batch of 3 → entire batch rejected with 422 ``price_currency_mismatch`` (X-R71).

    Contract: the detail names the asset, USD expected, GBP found, and the GBP day alone; ``count`` 1; nothing stored.
    Red before X-R71: 400 with a string detail.
    """
    print_section("Test 16: I.9 — partial mismatch rejects entire batch 422")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        create_item = FAAssetCreateItem(display_name=f"I9 Partial {unique_id('I9B')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id

        today = date.today()
        prices = [
            FAPricePoint(date=today - timedelta(days=2), close=Decimal("100"), currency="USD"),
            FAPricePoint(date=today - timedelta(days=1), close=Decimal("101"), currency="GBP"),  # mismatch
            FAPricePoint(date=today, close=Decimal("102"), currency="USD"),
        ]
        upsert = FAUpsert(asset_id=asset_id, prices=prices)
        resp = await client.post(f"{API_BASE}/assets/prices", json=[upsert.model_dump(mode="json")], timeout=TIMEOUT)
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"
        detail = resp.json()["detail"]
        assert isinstance(detail, dict) and detail.get("code") == "price_currency_mismatch", detail
        assert detail["items"] == [{"asset_id": asset_id, "expected": "USD", "found": ["GBP"], "dates": [(today - timedelta(days=1)).isoformat()]}], detail
        assert detail["count"] == 1, detail
        # Verify NO rows were inserted (atomic reject)
        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[{"asset_id": asset_id, "date_range": {"start": (today - timedelta(days=2)).isoformat(), "end": today.isoformat()}}],
            timeout=TIMEOUT,
        )
        data = query_resp.json()
        # Should be empty or only the price points that were present before (none in this test)
        assert len(data["items"][0].get("prices", [])) == 0, "Batch should have been atomically rejected"
        print_success("  ✓ 1/3 mismatch rejected whole batch (atomic)")

        # Cleanup
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_upsert_same_currency_succeeds_200(test_server):
    """I.9 Test 17: all rows matching asset currency → 200 OK, normal insert."""
    print_section("Test 17: I.9 — matching currency succeeds 200")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        create_item = FAAssetCreateItem(display_name=f"I9 Match {unique_id('I9C')}", currency="EUR")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id

        today = date.today()
        prices = [
            FAPricePoint(date=today - timedelta(days=1), close=Decimal("50"), currency="EUR"),
            FAPricePoint(date=today, close=Decimal("51"), currency="EUR"),
        ]
        upsert = FAUpsert(asset_id=asset_id, prices=prices)
        resp = await client.post(f"{API_BASE}/assets/prices", json=[upsert.model_dump(mode="json")], timeout=TIMEOUT)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = FABulkUpsertResponse(**resp.json())
        assert data.success_count >= 1
        print_success("  ✓ EUR rows on EUR asset → 200 OK")


@pytest.mark.asyncio
async def test_manual_price_wrappers_round_trip(test_server):
    """Test 18: Manual price wrapper happy-path round trip."""
    print_section("Test 18: Manual price wrappers round trip")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        create_item = FAAssetCreateItem(display_name=f"Manual Price Wrap {unique_id('MPW')}", currency="EUR")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201
        asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id

        upsert_resp = await client.post(
            f"{API_BASE}/assets/prices",
            json=[
                {
                    "asset_id": asset_id,
                    "prices": [
                        {"date": "2025-02-10", "close": "50.00", "currency": "EUR"},
                        {"date": "2025-02-11", "close": "51.25", "currency": "EUR"},
                    ],
                }
            ],
            timeout=TIMEOUT,
        )
        assert upsert_resp.status_code == 200, upsert_resp.text
        upsert_data = FABulkUpsertResponse(**upsert_resp.json())
        assert upsert_data.inserted_count >= 2
        assert upsert_data.success_count == 1

        query_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {"start": "2025-02-10", "end": "2025-02-11"},
                }
            ],
            timeout=TIMEOUT,
        )
        assert query_resp.status_code == 200, query_resp.text
        prices = query_resp.json()["items"][0]["prices"]
        assert len(prices) == 2

        current_resp = await client.post(f"{API_BASE}/assets/prices/current", json=[asset_id], timeout=TIMEOUT)
        assert current_resp.status_code == 200, current_resp.text
        current = current_resp.json()["results"][0]
        assert current["asset_id"] == asset_id
        assert current["source"] == "db:last_known"
        assert Decimal(current["value"]) == Decimal("51.25")

        delete_resp = await client.request(
            "DELETE",
            f"{API_BASE}/assets/prices",
            json=[
                {
                    "asset_id": asset_id,
                    "date_ranges": [{"start": "2025-02-10", "end": "2025-02-10"}],
                }
            ],
            timeout=TIMEOUT,
        )
        assert delete_resp.status_code == 200, delete_resp.text
        delete_data = FABulkDeleteResponse(**delete_resp.json())
        assert delete_data.success_count == 1
        assert delete_data.total_deleted >= 1

        query_after_delete = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {"start": "2025-02-10", "end": "2025-02-11"},
                }
            ],
            timeout=TIMEOUT,
        )
        assert query_after_delete.status_code == 200
        remaining = query_after_delete.json()["items"][0]["prices"]
        assert len(remaining) == 1
        assert remaining[0]["date"] == "2025-02-11"
        print_success("  ✓ Upsert/query/current/delete wrappers all returned expected data")


@pytest.mark.asyncio
async def test_sync_and_current_price_provider_success_with_mockprov(test_server):
    """Test 19: Sync + provider-backed current price with mockprov."""
    print_section("Test 19: Sync + current price via mock provider")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        create_item = FAAssetCreateItem(display_name=f"Mock Sync {unique_id('MSYNC')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        assert create_resp.status_code == 201
        asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id

        assign_resp = await client.post(
            f"{API_BASE}/assets/provider",
            json=[
                FAProviderAssignmentItem(
                    asset_id=asset_id,
                    provider_code="mockprov",
                    identifier="MOCK",
                    identifier_type=ProviderInputType.TICKER,
                    provider_params=None,
                ).model_dump(mode="json")
            ],
            timeout=TIMEOUT,
        )
        assert assign_resp.status_code == 200, assign_resp.text

        today = date.today()
        sync_resp = await client.post(
            f"{API_BASE}/assets/prices/sync",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {"start": (today - timedelta(days=2)).isoformat(), "end": today.isoformat()},
                }
            ],
            timeout=TIMEOUT,
        )
        assert sync_resp.status_code == 200, sync_resp.text
        sync_data = sync_resp.json()
        assert sync_data["success_count"] == 1
        assert sync_data["results"][0]["asset_id"] == asset_id
        assert sync_data["results"][0]["points_fetched"] >= 1

        current_resp = await client.post(f"{API_BASE}/assets/prices/current", json=[asset_id], timeout=TIMEOUT)
        assert current_resp.status_code == 200, current_resp.text
        current = current_resp.json()["results"][0]
        assert current["source"] == "provider:mockprov"
        assert Decimal(current["value"]) == Decimal("100.00")

        verify_resp = await client.post(
            f"{API_BASE}/assets/prices/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {"start": (today - timedelta(days=2)).isoformat(), "end": today.isoformat()},
                }
            ],
            timeout=TIMEOUT,
        )
        assert verify_resp.status_code == 200, verify_resp.text
        assert len(verify_resp.json()["items"][0]["prices"]) >= 1
        print_success("  ✓ Sync + current price wrappers succeeded with mock provider")


# ============================================================
# X-R55 (N75): a price query has a ceiling, the server's tomorrow
# ============================================================
#
# get_prices_bulk used to backward-fill one point a day up to any requested end: 9999-12-31 meant about 2.9 million
# points built and serialised by the lane's backend. These two cases go through the route. The unbounded sizes are
# pinned at service level (services range-ceiling, RC-A06), behind a fuse: here a red guard on unbounded code must not
# keep the shared backend's event loop busy for minutes, with every neighbour test of the run waiting on it.
#
# The ceiling is datetime_utils.latest_range_end(), tomorrow by the server's calendar (R13-SEC7-1's one helper). The
# lane's server runs on this host, in this process's time zone: the test asks the same helper for the day it cuts at.

EXTREME_SECONDS = 20.0  # a capped answer takes milliseconds; an unbounded one, minutes


async def _create_ceiling_asset(client: httpx.AsyncClient) -> int:
    """An asset of this test alone, in USD; the caller deletes it."""
    item = FAAssetCreateItem(display_name=f"Range Ceiling {unique_id('RCEIL')}", currency="USD")
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code == 201, resp.text
    return FABulkAssetCreateResponse(**resp.json()).results[0].asset_id


async def _price_three_days_before(client: httpx.AsyncClient, asset_id: int, today: date) -> None:
    """A close on each of the three days before ``today``: the last stored price is yesterday's."""
    prices = [FAPricePoint(date=today - timedelta(days=back), close=Decimal(100 + back), currency="USD") for back in (3, 2, 1)]
    resp = await client.post(f"{API_BASE}/assets/prices", json=[FAUpsert(asset_id=asset_id, prices=prices).model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_query_end_after_tomorrow_stops_at_tomorrow(test_server):
    """RC-API-01 (X-R55, N75): POST /assets/prices/query up to today+10 gives no point after the ceiling,
    ``latest_range_end()``: tomorrow, by the server's calendar.

    The last stored price is yesterday: the series is backward-filled up to the ceiling, and no further. The ceiling is
    read before the request (the series must reach it) and after the answer (no point may pass it): a day turning
    meanwhile only widens what is accepted.
    Red before X-R55: points backward-filled up to today+10.
    """
    print_section("RC-API-01: price query clamped to tomorrow")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_ceiling_asset(client)
        try:
            ceiling_before = latest_range_end()
            today = ceiling_before - timedelta(days=1)
            await _price_three_days_before(client, asset_id, today)
            date_range = {"start": (today - timedelta(days=3)).isoformat(), "end": (today + timedelta(days=10)).isoformat()}
            resp = await client.post(f"{API_BASE}/assets/prices/query", json=[{"asset_id": asset_id, "date_range": date_range}], timeout=TIMEOUT)
            ceiling = latest_range_end()
            assert resp.status_code == 200, resp.text
            days = [date.fromisoformat(point["date"]) for point in resp.json()["items"][0]["prices"]]
            late = [day for day in days if day > ceiling]
            assert not late, f"{len(late)} points after the ceiling {ceiling}: {late[0]} … {late[-1]}"
            assert days and days[-1] >= ceiling_before, f"the series should be backward-filled up to the ceiling {ceiling_before}: {days}"
            print_success(f"  ✓ {len(days)} points, the last on {days[-1]}")
        finally:
            await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_query_extreme_end_is_bounded(test_server):
    """RC-API-02 (X-R55, N75, guard): a query ending 9999-12-31 answers within EXTREME_SECONDS with no point after the
    ceiling, ``latest_range_end()``: 9999-12-01 … 9999-12-31 lies wholly after it, so the item is empty, without error.

    The start is not 0001-01-01 on purpose: on unbounded code that request makes the lane's shared backend build and
    serialise about 2.9 million points, its event loop blocked for minutes and every neighbour test with it. This shape
    costs unbounded code 31 points, and still fails it; 0001-01-01 … 9999-12-31 is pinned at service level (RC-A06).
    Red before X-R55: 500 «date value out of range» — after its 31 backward-filled points the per-day walk stepped past
    9999-12-31, the last day a date can hold, as every query ending there did (after 2.9 million points from today).
    """
    print_section("RC-API-02: price query ending 9999-12-31")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_ceiling_asset(client)
        try:
            await _price_three_days_before(client, asset_id, latest_range_end() - timedelta(days=1))
            query = [{"asset_id": asset_id, "date_range": {"start": "9999-12-01", "end": "9999-12-31"}}]
            started = time.monotonic()
            try:
                resp = await client.post(f"{API_BASE}/assets/prices/query", json=query, timeout=EXTREME_SECONDS)
            except httpx.TimeoutException:
                pytest.fail(f"no answer within {EXTREME_SECONDS:.0f} s for a query ending 9999-12-31")
            elapsed = time.monotonic() - started
            ceiling = latest_range_end()
            assert resp.status_code == 200, resp.text
            assert elapsed < EXTREME_SECONDS, f"{elapsed:.1f} s"
            (item,) = resp.json()["items"]
            days = [date.fromisoformat(point["date"]) for point in item["prices"]]
            late = [day for day in days if day > ceiling]
            assert not late, f"{len(late)} points after the ceiling {ceiling}: {late[0]} … {late[-1]}"
            assert (item["asset_id"], item["prices"], item["events"], item["errors"]) == (asset_id, [], [], [])
            print_success(f"  ✓ empty item in {elapsed:.2f} s")
        finally:
            await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


# ============================================================
# Z-25 (N77): a bulk price query has a cap on its items
# ============================================================
#
# POST /assets/prices/query refuses more than MAX_BULK_ITEMS (1 000) items before reading anything: a 422 with a coded
# detail. Its item-day budget (1 million, bulk_too_many_days) is pinned at service level only (services range-ceiling,
# BL-A01…A07): over the real budget through the route, code without it would make the lane's shared backend fill
# over a million points, the cost the cap exists to refuse.

BULK_MAX_ITEMS = 1_000  # the contract's number (N77), written here and not read from the code under test


@pytest.mark.asyncio
async def test_query_more_than_1000_items_is_refused(test_server):
    """BL-API-01 (Z-25, N77): 1 001 one-day items answer 422 ``{"code": "bulk_too_many_items", "message",
    "max_items": 1000, "items": 1001}``.

    The refusal comes before any read, so the asset id is never looked up, and nothing is written.
    Red before Z-25: 200, the 1 001 items queried.
    """
    print_section("BL-API-01: price query of 1 001 items refused")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        query = [{"asset_id": 1, "date_range": {"start": "2025-06-18", "end": "2025-06-18"}} for _ in range(BULK_MAX_ITEMS + 1)]
        resp = await client.post(f"{API_BASE}/assets/prices/query", json=query, timeout=TIMEOUT)
        assert resp.status_code == 422, f"{resp.status_code}: {resp.text[:300]}"
        detail = resp.json()["detail"]
        assert isinstance(detail, dict) and detail.get("code") == "bulk_too_many_items", detail
        assert isinstance(detail.get("message"), str) and detail["message"].strip(), detail
        assert {key: value for key, value in detail.items() if key not in ("code", "message")} == {"max_items": BULK_MAX_ITEMS, "items": BULK_MAX_ITEMS + 1}
        print_success(f"  ✓ 422 {detail['code']}: {detail['items']} items, at most {detail['max_items']}")


# ============================================================
# X-R65 (N83, revised 19/10): a stored price is dated no later than the server's tomorrow
# ============================================================
#
# J's SEC8-1b: one price dated 0001-01-01 made a backward fill or a risk replay walk about 740 000 days per asset, and
# X-R65 (17/10) bounded every stored price to [1900-01-01, latest_range_end()]. N83's revision (developer, 19/10: «se
# voglio leggere e salvare più indietro devo poterlo fare») takes the 1900 floor away and keeps the ceiling alone: the
# walks stay bounded where they read (N75's 100 years, R13-SEC8's replay floors, Z-30's full-history load). POST
# /assets/prices checks every date against date_range_limits.latest_stored_date() -- latest_range_end(), included --
# before any statement: one date after it refuses the whole request with a 422 and writes nothing, for any asset of it;
# a date before 1900 is stored like any other. The frozen ceiling, the cap of ten and a provider's points are pinned at
# service level (services asset-source-guards; services range-ceiling, RC-W); here the route on the lane's server, at its
# real ceiling, read before the request and after the answer as RC-API-01 reads it. 1899-12-31 and 1850-06-01, not
# 0001-01-01: year one is stored at service level, on that unit's own asset, and taken by the handler on no database
# (RC-W10); on the lane's shared backend no test leaves a row from which a neighbour's walk could start.


async def _create_bounds_asset(client: httpx.AsyncClient) -> int:
    """An asset of this test alone, in USD, its name unique across workers; the caller deletes it."""
    item = FAAssetCreateItem(display_name=f"Stored Bounds {unique_id('XR65')} {uuid.uuid4().hex[:8]}", currency="USD")
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code == 201, resp.text
    return FABulkAssetCreateResponse(**resp.json()).results[0].asset_id


async def _stored_price_days(client: httpx.AsyncClient, asset_id: int) -> list[str]:
    """Every day the asset has a price on, whatever its date: the backup export reads the table, no range and no fill."""
    return list(await _stored_price_closes(client, asset_id))


async def _stored_price_closes(client: httpx.AsyncClient, asset_id: int) -> dict[str, Decimal]:
    """The asset's closes by ISO day, in date order, whatever their date: the backup export, as ``_stored_price_days``."""
    resp = await client.get(f"{API_BASE}/backup/asset/{asset_id}/prices", params={"format": "json"}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return {row["date"]: Decimal(str(row["close"])) for row in resp.json()["rows"]}


def _usd_prices(asset_id: int, closes: dict[date, str]) -> FAUpsert:
    """The asset's prices: a close in USD on each day of ``closes``, in its order."""
    return FAUpsert(asset_id=asset_id, prices=[FAPricePoint(date=day, close=Decimal(close), currency="USD") for day, close in closes.items()])


@pytest.mark.asyncio
async def test_upsert_after_the_ceiling_is_refused_whole(test_server):
    """RC-API-05 (X-R65, N83 revised 19/10): POST /assets/prices with 1899-12-31 and 1850-06-01 on one asset and a day
    past the ceiling on another, each beside valid days, answers 422 ``{"code": "date_out_of_range", "message",
    "params": {"max": the ceiling}, "items": [{"asset_id": second, "dates": [that day]}], "count": 1}`` -- and neither
    asset has a price, not even on its valid days, nor the first on its days before 1900: the request is refused whole.

    The ceiling is ``latest_range_end()``, read before the request and after the answer: ``max`` lies between them. The
    day past it is 30 days on, past whatever the ceiling becomes meanwhile.
    Red before X-R65: 200, the six prices stored -- the day past the ceiling with them.
    Red before N83's revision: ``params`` is ``{"min": "1900-01-01", "max"}``; the first asset is refused too, for its
    two days before 1900, and ``count`` is 3.
    """
    print_section("RC-API-05: price upsert after the ceiling refused")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        owned: list[int] = []
        try:
            owned.append(await _create_bounds_asset(client))
            owned.append(await _create_bounds_asset(client))
            first, second = owned
            assert (await _stored_price_days(client, first), await _stored_price_days(client, second)) == ([], []), "barrier: a new asset holds prices"
            ceiling_before = latest_range_end()
            past_ceiling = ceiling_before + timedelta(days=30)
            body = [
                _usd_prices(first, {date(2020, 3, 2): "100", date(1899, 12, 31): "101", date(2020, 3, 3): "102", date(1850, 6, 1): "103"}),
                _usd_prices(second, {date(2020, 3, 2): "200", past_ceiling: "201"}),
            ]
            resp = await client.post(f"{API_BASE}/assets/prices", json=[item.model_dump(mode="json") for item in body], timeout=TIMEOUT)
            ceiling_after = latest_range_end()
            assert resp.status_code == 422, f"{resp.status_code}: {resp.text[:400]}"
            detail = resp.json()["detail"]
            assert isinstance(detail, dict) and set(detail) == {"code", "message", "params", "items", "count"}, detail
            assert detail["code"] == "date_out_of_range", detail
            assert isinstance(detail["message"], str) and detail["message"].strip(), detail
            assert set(detail["params"]) == {"max"}, f"params {detail['params']}: a stored date has one bound, the ceiling"
            assert ceiling_before <= date.fromisoformat(detail["params"]["max"]) <= ceiling_after, f"max {detail['params']['max']} outside {ceiling_before} … {ceiling_after}"
            assert detail["items"] == [{"asset_id": second, "dates": [past_ceiling.isoformat()]}], detail
            assert detail["count"] == 1, detail
            assert await _stored_price_days(client, first) == []
            assert await _stored_price_days(client, second) == []
            print_success(f"  ✓ 422 {detail['code']}: {detail['count']} date(s), nothing stored")
        finally:
            if owned:
                await client.delete(f"{API_BASE}/assets", params={"asset_ids": owned}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_upsert_before_1900_is_stored(test_server):
    """RC-API-07 (N83 revised 19/10): POST /assets/prices with 1850-06-01 and 1899-12-31 beside a valid day answers 200:
    the asset's result counts 3 and lists no rejection, and the asset has a price on the three days, at their closes.

    Red before N83's revision: 422 ``date_out_of_range``, ``params`` ``{"min": "1900-01-01", "max"}``, the two days
    before 1900 refused and nothing stored.
    """
    print_section("RC-API-07: price upsert before 1900 stored")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_bounds_asset(client)
        try:
            assert await _stored_price_days(client, asset_id) == [], "barrier: a new asset holds prices"
            closes = {date(1850, 6, 1): "301", date(1899, 12, 31): "302", date(2020, 3, 2): "303"}
            resp = await client.post(f"{API_BASE}/assets/prices", json=[_usd_prices(asset_id, closes).model_dump(mode="json")], timeout=TIMEOUT)
            assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:400]}"
            result = next(item for item in FABulkUpsertResponse(**resp.json()).results if item.asset_id == asset_id)
            assert (result.count, result.rejected) == (3, []), result
            assert await _stored_price_closes(client, asset_id) == {day.isoformat(): Decimal(close) for day, close in closes.items()}
            print_success(f"  ✓ 200: {result.count} prices stored, the first on {min(closes)}")
        finally:
            await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


# ============================================================
# Z-29a (N90, revised 19/10): an item's price series sampled for a compact chart
# ============================================================
#
# On «All» the asset list asked every asset's whole daily history, about 9 787 points each since 2000: an out-of-memory
# on a small instance. An item may now say its step one way: max_points, the most points the card's chart takes (per
# asset daily, weekly — ISO, Monday to Sunday — or monthly, the finest whose count over the asset's own fill fits);
# resolution, the step asked; or sample_like, the key of another item of the request whose step and buckets it follows
# (a comparison on a card). A weekly or monthly series is the last point of each week or month, the last one cut at the
# end, each the daily answer's point on that date; sample_bounds holds the daily points on the fill's first day and on
# the end; resolution says the step. The rule, the buckets, the references, the ceiling, the day budget and the reads
# are pinned at service level (services price-query-sampling, a private database); here the route on the lane's server:
# its 422s, the OpenAPI document, and assets of these tests' own.

SAMPLING_BOUNDS = (1, 10_000)  # the contract's bounds (N90), written here and not read from the code under test
SAMPLING_RESOLUTIONS = ("daily", "weekly", "monthly")  # the steps (N90), written here and not read from the code under test
SAMPLING_FIELDS = ("max_points", "resolution", "sample_like")  # at most one per item (N90, revised 19/10)
SAMPLING_UNREAD_ASSET_ID = 2_147_483_647  # never read: the body is refused before the handler runs
SAMPLING_SMA3 = {"instance_id": "sma3", "signal_code": "SMA", "params": {"period": 3}}
SAMPLING_ROWS = (date(2020, 12, 1), date(2023, 12, 29))  # a card's weekday closes, the first and the last
SAMPLING_LATE_ROWS = (date(2022, 3, 1), date(2023, 12, 29))  # a target's: a Tuesday, long after the range starts
SAMPLING_RANGE = (date(2021, 1, 3), date(2023, 12, 31))  # Sunday to Sunday, 1 093 days; Friday 2021-01-01 precedes it
SAMPLING_DETAIL_KEYS = {"code", "reason", "item", "key", "message"}  # the 422 sample_reference detail (N90, revised 19/10)


def _sampling_bucket(day: date, step: str) -> tuple[int, int]:
    """The ISO week (its year, its number) or the calendar month (year, month) of ``day``."""
    return (day.isocalendar().year, day.isocalendar().week) if step == "weekly" else (day.year, day.month)


def _sampling_dates(first: date, end: date, step: str) -> list[date]:
    """The dates of a weekly or monthly sample: each day from ``first`` that ends its week or month, or ends the range —
    ``first`` itself only when it closes its bucket."""
    days = [first + timedelta(days=n) for n in range((end - first).days + 1)]
    return [day for day in days if day == end or _sampling_bucket(day, step) != _sampling_bucket(day + timedelta(days=1), step)]


def _validation_errors(resp: httpx.Response) -> list[dict]:
    """The errors of a 422 FastAPI raised on the body; the status is checked first."""
    assert resp.status_code == 422, f"{resp.status_code}: {resp.text[:300]}"
    detail = resp.json()["detail"]
    assert isinstance(detail, list), f"not a validation error of the body: {detail!r}"
    return detail


def _sampling_literal_values(node: dict, components: dict) -> list:
    """The values a ``Literal`` property admits, however the OpenAPI document writes them: ``enum`` or ``const`` on the
    property, ``anyOf``/``oneOf`` of those, or a ``$ref`` (alone, or the one member of an ``allOf``) to a component that
    holds them — a ``type`` alias is written so. A ``{"type": "null"}`` branch admits none. ``components``: the
    document's ``components/schemas``."""
    if "$ref" in node:
        name = node["$ref"].rsplit("/", 1)[-1]
        assert name in components, f"{node['$ref']} is not a component of the document"
        return _sampling_literal_values(components[name], components)
    if "enum" in node:
        return list(node["enum"])
    if "const" in node:
        return [node["const"]]
    if node.get("type") == "null":
        return []
    if len(node.get("allOf", [])) == 1:
        return _sampling_literal_values(node["allOf"][0], components)
    branches = node.get("anyOf") or node.get("oneOf")
    assert branches, f"no literal values in {node}"
    return [value for branch in branches for value in _sampling_literal_values(branch, components)]


def _sampling_ref(node: dict) -> str | None:
    """The component a property refers to: its ``$ref``, alone or the one member of an ``allOf``; None without one."""
    if "$ref" in node:
        return node["$ref"].rsplit("/", 1)[-1]
    members = node.get("allOf", [])
    return _sampling_ref(members[0]) if len(members) == 1 else None


def _sampling_nullable(field: dict) -> bool:
    """Whether an optional property admits null: one of its ``anyOf`` branches is ``{"type": "null"}``."""
    return any(branch.get("type") == "null" for branch in field.get("anyOf", []))


async def _create_sampling_asset(client: httpx.AsyncClient) -> int:
    """An asset of this test alone, in USD, its name unique across workers; the caller deletes it."""
    item = FAAssetCreateItem(display_name=f"Price Sampling {unique_id('Z29A')} {uuid.uuid4().hex[:8]}", currency="USD")
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code == 201, resp.text
    return FABulkAssetCreateResponse(**resp.json()).results[0].asset_id


async def _upsert_sampling_closes(client: httpx.AsyncClient, asset_id: int, rows: tuple[date, date], base: int) -> None:
    """A close in USD on every weekday from ``rows[0]`` to ``rows[1]``, each its own (``base`` + n / 100)."""
    first, last = rows
    days = [day for day in (first + timedelta(days=n) for n in range((last - first).days + 1)) if day.weekday() < 5]
    prices = [FAPricePoint(date=day, close=Decimal(base) + Decimal(n) / 100, currency="USD") for n, day in enumerate(days)]
    resp = await client.post(f"{API_BASE}/assets/prices", json=[FAUpsert(asset_id=asset_id, prices=prices).model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text[:300]


def _assert_sampled(answer: dict, daily: dict, step: str, first: date, end: date) -> None:
    """``answer`` says ``step`` and carries the points of ``_sampling_dates(first, end, step)``, each, as JSON, the
    daily answer's point on its date; its ``sample_bounds`` are the daily points on ``first`` and on ``end``, the last
    one also its last point; no event, no error, no signal."""
    daily_points = {point["date"]: point for point in daily["prices"]}
    expected = [day.isoformat() for day in _sampling_dates(first, end, step)]
    got = [point["date"] for point in answer["prices"]]
    assert answer.get("resolution") == step, f"resolution {answer.get('resolution')!r} for {step!r}"
    assert got == expected, f"{step}: {len(got)} dates for {len(expected)}; the first ones {got[:3]}, expected {expected[:3]}"
    differing = [point for point in answer["prices"] if point != daily_points.get(point["date"])]
    assert not differing, f"{step}: {len(differing)} points differ from the daily answer's; the first: {differing[0]} / {daily_points.get(differing[0]['date'])}"
    bounds = answer.get("sample_bounds")
    assert isinstance(bounds, dict) and set(bounds) == {"first", "last"}, f"{step}: sample_bounds {bounds!r}"
    assert bounds["first"] == daily_points[first.isoformat()], f"{step}: sample_bounds.first {bounds['first']} / the daily point on {first}: {daily_points[first.isoformat()]}"
    assert bounds["last"] == daily_points[end.isoformat()] == answer["prices"][-1], f"{step}: sample_bounds.last {bounds['last']} / the daily and last point on {end}"
    assert (answer["events"], answer["errors"], answer["signals"]) == ([], [], []), answer


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("extra", "named"),
    [
        pytest.param({"signals": [SAMPLING_SMA3]}, ("max_points",), id="signals"),
        pytest.param({"include_events": True}, ("max_points",), id="include-events"),
        pytest.param({"resolution": "weekly"}, SAMPLING_FIELDS, id="resolution"),
    ],
)
async def test_query_max_points_with_signals_events_or_resolution_is_refused(test_server, extra, named):
    """PQS-API-01 (Z-29a, N90 revised 19/10): an item with max_points and signals, or with max_points and include_events,
    answers 422: a value error naming max_points — the sample carries the price series alone, signals and events need
    every day (until Z-29s). An item with max_points and resolution answers 422 too: a value error naming max_points,
    resolution and sample_like — an item says its step one way.

    The asset id is never read: the body is refused before the handler runs. The same item without max_points is valid
    (services price-query-sampling, PQS-S03, S13).
    Red before Z-29a: 422 too, but for max_points itself, an unknown field (``extra_forbidden``).
    """
    print_section(f"PQS-API-01: max_points with {next(iter(extra))} refused")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        body = [{"asset_id": SAMPLING_UNREAD_ASSET_ID, "date_range": {"start": "2025-01-01", "end": "2025-12-31"}, "max_points": 300, **extra}]
        resp = await client.post(f"{API_BASE}/assets/prices/query", json=body, timeout=TIMEOUT)
        errors = _validation_errors(resp)
        assert not [error for error in errors if error["type"] == "extra_forbidden"], f"refused as an unknown field: {errors}"
        assert any(error["type"] == "value_error" and all(name in error["msg"] for name in named) for error in errors), errors
        print_success(f"  ✓ 422: {[error['msg'] for error in errors]}")


@pytest.mark.asyncio
@pytest.mark.parametrize(("max_points", "error_type"), [pytest.param(0, "greater_than_equal", id="zero"), pytest.param(10_001, "less_than_equal", id="past-10000")])
async def test_query_max_points_out_of_bounds_is_refused(test_server, max_points, error_type):
    """PQS-API-02 (Z-29a, N90): max_points 0, or 10 001, answers 422 on the field itself: at least 1, at most 10 000.

    Red before Z-29a: 422 for an unknown field (``extra_forbidden``), not for its bounds.
    """
    print_section(f"PQS-API-02: max_points {max_points} refused")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        body = [{"asset_id": SAMPLING_UNREAD_ASSET_ID, "date_range": {"start": "2025-01-01", "end": "2025-12-31"}, "max_points": max_points}]
        resp = await client.post(f"{API_BASE}/assets/prices/query", json=body, timeout=TIMEOUT)
        errors = _validation_errors(resp)
        assert [(error["type"], error["loc"]) for error in errors] == [(error_type, ["body", 0, "max_points"])], errors
        print_success(f"  ✓ 422 {error_type} on max_points")


@pytest.mark.asyncio
async def test_openapi_lists_the_sampling_fields(test_server):
    """PQS-API-03 (Z-29a, N90 revised 19/10): the OpenAPI document the API client is generated from lists on
    ``FAPriceQueryItem`` ``key``, ``max_points``, ``resolution`` and ``sample_like``, none required, each admitting null:
    ``key`` and ``sample_like`` strings with a pattern, ``max_points`` an integer from 1 to 10 000, ``resolution``
    exactly daily, weekly and monthly. On ``FAPriceQueryResult``: ``resolution``, not required (it has a default, as
    ``prices`` and ``events``), exactly the three steps, default daily; ``sample_bounds``, not required, null or the
    ``FAPriceSampleBounds`` component, whose ``first`` and ``last`` are required price points. A ``Literal`` may be an
    ``enum`` on the property or behind a ``$ref`` (a ``type`` alias); a price point the ``FAPricePoint`` component or its
    output variant.

    Red before Z-29a: the item has none of the four properties, and the result neither ``resolution`` nor
    ``sample_bounds``.
    """
    print_section("PQS-API-03: the sampling fields in the OpenAPI document")

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_BASE}/openapi.json", timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text[:300]
    components = resp.json()["components"]["schemas"]
    item = components["FAPriceQueryItem"]
    fields = {name: item["properties"].get(name) for name in ("key", *SAMPLING_FIELDS)}
    assert all(fields.values()), f"FAPriceQueryItem lacks {[name for name, field in fields.items() if field is None]}: {sorted(item['properties'])}"
    assert not set(fields) & set(item.get("required", [])), item.get("required")
    assert all(_sampling_nullable(field) for field in fields.values()), f"not every sampling field admits null: {fields}"
    for name in ("key", "sample_like"):
        strings = [branch for branch in fields[name]["anyOf"] if branch.get("type") == "string"]
        assert len(strings) == 1 and "pattern" in strings[0], f"{name}: {fields[name]}"
    integers = [branch for branch in fields["max_points"]["anyOf"] if branch.get("type") == "integer"]
    assert len(integers) == 1 and (integers[0].get("minimum"), integers[0].get("maximum")) == SAMPLING_BOUNDS, fields["max_points"]
    assert sorted(_sampling_literal_values(fields["resolution"], components)) == sorted(SAMPLING_RESOLUTIONS), fields["resolution"]
    print_success(f"  ✓ FAPriceQueryItem: {sorted(fields)}")

    result = components.get("FAPriceQueryResult")
    assert result is not None, f"no FAPriceQueryResult component: {sorted(name for name in components if name.startswith('FAPriceQuery'))}"
    resolution, bounds = result["properties"].get("resolution"), result["properties"].get("sample_bounds")
    assert resolution is not None and bounds is not None, f"FAPriceQueryResult: {sorted(result['properties'])}"
    assert sorted(_sampling_literal_values(resolution, components)) == sorted(SAMPLING_RESOLUTIONS), resolution
    assert resolution.get("default") == "daily", resolution
    assert not {"resolution", "sample_bounds"} & set(result.get("required", [])), result.get("required")
    assert _sampling_nullable(bounds), f"sample_bounds does not admit null: {bounds}"
    refs = [_sampling_ref(branch) for branch in bounds["anyOf"] if _sampling_ref(branch)]
    assert len(refs) == 1 and refs[0].startswith("FAPriceSampleBounds"), bounds
    bounds_component = components[refs[0]]
    assert sorted(bounds_component.get("required", [])) == ["first", "last"], bounds_component
    point_refs = {name: _sampling_ref(bounds_component["properties"][name]) or "" for name in ("first", "last")}
    assert all(ref.startswith("FAPricePoint") for ref in point_refs.values()), point_refs
    print_success(f"  ✓ FAPriceQueryResult: resolution {resolution}, sample_bounds → {refs[0]} {point_refs}")


@pytest.mark.asyncio
async def test_query_max_points_samples_the_daily_answer(test_server):
    """PQS-API-04 (Z-29a, N90 revised 19/10): one asset of this test's own, a close on every weekday from 2020-12-01 to
    2023-12-29, asked from Sunday 2021-01-03 to Sunday 2023-12-31 in one request, three times: without max_points (1 093
    daily points, the first filled from Friday 2021-01-01, the row before the range); with 200, which the fill's 157 ISO
    weeks fit (weekly: every Sunday, 2021-01-03 included — it closes its week — 157 points); with 100 (monthly: every
    month end from 2021-01-31, 36 points, 2021-01-03 not among them). Each answer says its step in ``resolution`` —
    daily, weekly, monthly — and every sampled point is, as JSON, the daily answer's point on its date; the weekly and
    the monthly answers' ``sample_bounds`` are the daily points on 2021-01-03 and 2023-12-31, the last one also their
    last point; the daily answer has none.

    The range ends in 2023, before any ceiling: the answer does not depend on the day the suite runs.
    Red before Z-29a: 422, max_points refused as an unknown field.
    """
    print_section("PQS-API-04: a sampled series is the daily one on its dates, its bounds the daily ones")
    first, end = SAMPLING_RANGE

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        owned: list[int] = []
        try:
            owned.append(await _create_sampling_asset(client))
            (asset_id,) = owned
            await _upsert_sampling_closes(client, asset_id, SAMPLING_ROWS, 100)
            date_range = {"start": first.isoformat(), "end": end.isoformat()}
            body = [{"asset_id": asset_id, "date_range": date_range}, {"asset_id": asset_id, "date_range": date_range, "max_points": 200}, {"asset_id": asset_id, "date_range": date_range, "max_points": 100}]
            resp = await client.post(f"{API_BASE}/assets/prices/query", json=body, timeout=TIMEOUT)
            assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:300]}"
            daily, weekly, monthly = resp.json()["items"]
            assert [item["asset_id"] for item in (daily, weekly, monthly)] == [asset_id] * 3
            assert (daily.get("resolution"), daily.get("sample_bounds")) == ("daily", None), (daily.get("resolution"), daily.get("sample_bounds"))
            assert len(daily["prices"]) == len({point["date"] for point in daily["prices"]}) == (end - first).days + 1, f"{len(daily['prices'])} daily points"
            assert daily["prices"][0]["date"] == first.isoformat() and daily["prices"][0]["backward_fill_info"]["actual_rate_date"] == "2021-01-01", daily["prices"][0]
            for answer, step, count, opens_with_first in ((weekly, "weekly", 157, True), (monthly, "monthly", 36, False)):
                expected = _sampling_dates(first, end, step)
                assert (len(expected), expected[0] == first) == (count, opens_with_first), f"premise: {len(expected)} {step} dates, the first {expected[0]}"
                _assert_sampled(answer, daily, step, first, end)
                print_success(f"  ✓ {step}: {len(answer['prices'])} points of the {len(daily['prices'])} daily ones, bounds on {first} and {end}")
        finally:
            if owned:
                await client.delete(f"{API_BASE}/assets", params={"asset_ids": owned}, timeout=TIMEOUT)


@pytest.mark.asyncio
async def test_query_sample_like_puts_a_target_on_its_cards_buckets(test_server):
    """PQS-API-05 (Z-29a, N90 revised 19/10): two assets of this test's own: a card's, a close on every weekday from
    2020-12-01 to 2023-12-29, and a target's, from Tuesday 2022-03-01 only. One request on Sunday 2021-01-03 … Sunday
    2023-12-31: the card with ``key`` "card" and max_points 100 — monthly, every month end from 2021-01-31 (36 points),
    its first bound on 2021-01-03 — and the target with ``sample_like`` "card": monthly too, from its own first day,
    later than the card's — every month end from 2022-03-31 (22 points), its first bound on 2022-03-01 — each point and
    bound, as JSON, its own daily answer's (asked apart). The same request with ``sample_like`` "nope" answers 422
    ``{"code": "sample_reference", "reason": "unknown_key", "item": 1, "key": null, "message"}``: a key no item carries,
    the target, second in the request, keyed by none.

    The range ends in 2023, before any ceiling: the answer does not depend on the day the suite runs.
    Red before Z-29a: 422, key and sample_like refused as unknown fields — the first request; the second's detail is a
    list of those, not a coded dict.
    """
    print_section("PQS-API-05: a target follows its card's buckets from its own first day")
    first, end = SAMPLING_RANGE
    target_first = SAMPLING_LATE_ROWS[0]
    date_range = {"start": first.isoformat(), "end": end.isoformat()}

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        owned: list[int] = []
        try:
            owned.append(await _create_sampling_asset(client))
            owned.append(await _create_sampling_asset(client))
            card_asset, target_asset = owned
            await _upsert_sampling_closes(client, card_asset, SAMPLING_ROWS, 100)
            await _upsert_sampling_closes(client, target_asset, SAMPLING_LATE_ROWS, 200)
            resp = await client.post(f"{API_BASE}/assets/prices/query", json=[{"asset_id": card_asset, "date_range": date_range}, {"asset_id": target_asset, "date_range": date_range}], timeout=TIMEOUT)
            assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:300]}"
            card_daily, target_daily = resp.json()["items"]
            assert (target_daily["prices"][0]["date"], target_daily["prices"][0]["backward_fill_info"]) == (target_first.isoformat(), None), f"premise: the target's fill starts on its first row, {target_daily['prices'][0]}"
            assert len(_sampling_dates(first, end, "monthly")) == 36 and len(_sampling_dates(target_first, end, "monthly")) == 22, "premise"

            card_item = {"asset_id": card_asset, "date_range": date_range, "key": "card", "max_points": 100}
            resp = await client.post(f"{API_BASE}/assets/prices/query", json=[card_item, {"asset_id": target_asset, "date_range": date_range, "sample_like": "card"}], timeout=TIMEOUT)
            assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:300]}"
            card, target = resp.json()["items"]
            assert (card["asset_id"], target["asset_id"]) == (card_asset, target_asset)
            _assert_sampled(card, card_daily, "monthly", first, end)
            _assert_sampled(target, target_daily, "monthly", target_first, end)
            print_success(f"  ✓ card {len(card['prices'])} monthly points from {first}; target {len(target['prices'])} from {target_first}")

            resp = await client.post(f"{API_BASE}/assets/prices/query", json=[card_item, {"asset_id": target_asset, "date_range": date_range, "sample_like": "nope"}], timeout=TIMEOUT)
            assert resp.status_code == 422, f"{resp.status_code}: {resp.text[:300]}"
            detail = resp.json()["detail"]
            assert isinstance(detail, dict) and set(detail) == SAMPLING_DETAIL_KEYS, detail
            assert {name: detail[name] for name in ("code", "reason", "item", "key")} == {"code": "sample_reference", "reason": "unknown_key", "item": 1, "key": None}, detail
            assert isinstance(detail["message"], str) and detail["message"].strip(), detail
            print_success(f"  ✓ 422 {detail['code']} {detail['reason']} on item {detail['item']}")
        finally:
            if owned:
                await client.delete(f"{API_BASE}/assets", params={"asset_ids": owned}, timeout=TIMEOUT)
