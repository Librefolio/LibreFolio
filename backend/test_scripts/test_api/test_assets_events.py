"""
Test Suite: Asset Events API Endpoints

Tests for event-related endpoints:
- POST /api/v1/assets/events - Bulk upsert manual events
- DELETE /api/v1/assets/events/{event_id} - Delete event by ID
- POST /api/v1/assets/events/query - Bulk query events
"""

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets import (
    FAAssetCreateItem,
    FABulkAssetCreateResponse,
)
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.prices import (
    FAAssetEventPoint,
    FABulkEventUpsertResponse,
    FAEventDeleteResult,
    FAEventQueryItem,
    FAEventQueryResponse,
    FAEventUpsert,
)
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success, unique_id

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
# Test 1: POST /assets/events - Bulk upsert manual events
# ============================================================
@pytest.mark.asyncio
async def test_bulk_upsert_events(test_server):
    """Test 1: POST /assets/events - Bulk upsert manual events."""
    print_section("Test 1: POST /assets/events - Bulk upsert")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # Step 1: Create test asset
        create_item = FAAssetCreateItem(display_name=f"Event Upsert Test {unique_id('EVT1')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id
        print_info(f"Created asset ID: {asset_id}")

        # Step 2: Upsert 2 manual events (DIVIDEND + SPLIT)
        today = date.today()
        events = [
            FAAssetEventPoint(
                date=today - timedelta(days=30),
                type="DIVIDEND",
                value=Currency(code="USD", amount=Decimal("1.25")),
                notes="Q1 dividend",
            ),
            FAAssetEventPoint(
                date=today - timedelta(days=10),
                type="SPLIT",
                value=Currency(code="USD", amount=Decimal("2")),
                notes="2:1 stock split",
            ),
        ]

        upsert_data = FAEventUpsert(asset_id=asset_id, events=events)

        upsert_resp = await client.post(
            f"{API_BASE}/assets/events",
            json=[upsert_data.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        assert upsert_resp.status_code == 200, f"Expected 200, got {upsert_resp.status_code}: {upsert_resp.text}"
        result = FABulkEventUpsertResponse(**upsert_resp.json())
        assert result.success_count >= 1
        assert result.results[0].count == 2
        print_success(f"Upserted {result.results[0].count} events for asset {asset_id}")


# ============================================================
# Test 2: POST /assets/events/query - Query events
# ============================================================
@pytest.mark.asyncio
async def test_query_events(test_server):
    """Test 2: POST /assets/events/query - Query events for an asset."""
    print_section("Test 2: POST /assets/events/query")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # Create asset + insert events
        create_item = FAAssetCreateItem(display_name=f"Event Query Test {unique_id('EVT2')}", currency="EUR")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        today = date.today()
        event_date = today - timedelta(days=5)
        events = [
            FAAssetEventPoint(
                date=event_date,
                type="INTEREST",
                value=Currency(code="EUR", amount=Decimal("0.50")),
                notes="Monthly interest",
            ),
        ]
        upsert_data = FAEventUpsert(asset_id=asset_id, events=events)
        await client.post(
            f"{API_BASE}/assets/events",
            json=[upsert_data.model_dump(mode="json")],
            timeout=TIMEOUT,
        )

        # Query events
        query_item = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(
                start=today - timedelta(days=30),
                end=today,
            ),
        )
        query_resp = await client.post(
            f"{API_BASE}/assets/events/query",
            json=[query_item.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        assert query_resp.status_code == 200, f"Expected 200, got {query_resp.status_code}: {query_resp.text}"
        result = FAEventQueryResponse(**query_resp.json())
        assert len(result.items) == 1
        assert len(result.items[0].events) == 1

        evt = result.items[0].events[0]
        assert evt.type == "INTEREST"
        assert evt.id is not None  # DB primary key
        assert evt.is_auto is False  # manual event
        assert evt.value.code == "EUR"
        assert float(evt.value.amount) == 0.50
        print_success(f"Queried event: id={evt.id}, type={evt.type}, is_auto={evt.is_auto}")


# ============================================================
# Test 3: DELETE /assets/events/{id} - Delete event by ID
# ============================================================
@pytest.mark.asyncio
async def test_delete_event_by_id(test_server):
    """Test 3: DELETE /assets/events/{id} - Delete a single event."""
    print_section("Test 3: DELETE /assets/events/{id}")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # Create asset + insert event
        create_item = FAAssetCreateItem(display_name=f"Event Delete Test {unique_id('EVT3')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        today = date.today()
        events = [
            FAAssetEventPoint(
                date=today - timedelta(days=3),
                type="DIVIDEND",
                value=Currency(code="USD", amount=Decimal("2.00")),
            ),
        ]
        upsert_data = FAEventUpsert(asset_id=asset_id, events=events)
        await client.post(
            f"{API_BASE}/assets/events",
            json=[upsert_data.model_dump(mode="json")],
            timeout=TIMEOUT,
        )

        # Query to get event ID
        query_item = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=today - timedelta(days=30), end=today),
        )
        query_resp = await client.post(
            f"{API_BASE}/assets/events/query",
            json=[query_item.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        result = FAEventQueryResponse(**query_resp.json())
        assert len(result.items[0].events) == 1
        event_id = result.items[0].events[0].id
        print_info(f"Event to delete: id={event_id}")

        # Delete event
        del_resp = await client.delete(
            f"{API_BASE}/assets/events/{event_id}",
            timeout=TIMEOUT,
        )
        assert del_resp.status_code == 200, f"Expected 200, got {del_resp.status_code}: {del_resp.text}"
        del_result = FAEventDeleteResult(**del_resp.json())
        assert del_result.success is True
        assert del_result.deleted_count == 1
        assert del_result.event_id == event_id
        print_success(f"Deleted event {event_id}")

        # Verify deletion: query again
        verify_resp = await client.post(
            f"{API_BASE}/assets/events/query",
            json=[query_item.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        verify_result = FAEventQueryResponse(**verify_resp.json())
        assert len(verify_result.items[0].events) == 0
        print_success("Verified: event no longer returned by query")


# ============================================================
# Test 4: DELETE non-existent event returns success=False
# ============================================================
@pytest.mark.asyncio
async def test_delete_nonexistent_event(test_server):
    """Test 4: DELETE /assets/events/{id} with non-existent ID."""
    print_section("Test 4: DELETE non-existent event")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        del_resp = await client.delete(
            f"{API_BASE}/assets/events/999999",
            timeout=TIMEOUT,
        )
        assert del_resp.status_code == 200, f"Expected 200, got {del_resp.status_code}: {del_resp.text}"
        del_result = FAEventDeleteResult(**del_resp.json())
        assert del_result.success is False
        assert del_result.deleted_count == 0
        print_success("Non-existent event correctly returns success=False")


# ============================================================
# Test 5: Upsert same date+type replaces manual event
# ============================================================
@pytest.mark.asyncio
async def test_upsert_replaces_same_date_type(test_server):
    """Test 5: Upserting same (date, type) for manual events replaces old one."""
    print_section("Test 5: Upsert replaces same date+type")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        create_item = FAAssetCreateItem(display_name=f"Event Replace Test {unique_id('EVT5')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        today = date.today()
        event_date = today - timedelta(days=7)

        # Insert first dividend
        events_v1 = [
            FAAssetEventPoint(
                date=event_date,
                type="DIVIDEND",
                value=Currency(code="USD", amount=Decimal("1.00")),
                notes="Original",
            ),
        ]
        upsert_v1 = FAEventUpsert(asset_id=asset_id, events=events_v1)
        await client.post(
            f"{API_BASE}/assets/events",
            json=[upsert_v1.model_dump(mode="json")],
            timeout=TIMEOUT,
        )

        # Upsert again with different value (same date, same type)
        events_v2 = [
            FAAssetEventPoint(
                date=event_date,
                type="DIVIDEND",
                value=Currency(code="USD", amount=Decimal("1.50")),
                notes="Updated",
            ),
        ]
        upsert_v2 = FAEventUpsert(asset_id=asset_id, events=events_v2)
        await client.post(
            f"{API_BASE}/assets/events",
            json=[upsert_v2.model_dump(mode="json")],
            timeout=TIMEOUT,
        )

        # Query — should have exactly 1 event with updated value
        query_item = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=today - timedelta(days=30), end=today),
        )
        query_resp = await client.post(
            f"{API_BASE}/assets/events/query",
            json=[query_item.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        result = FAEventQueryResponse(**query_resp.json())
        assert len(result.items[0].events) == 1, f"Expected 1 event, got {len(result.items[0].events)}"
        evt = result.items[0].events[0]
        assert float(evt.value.amount) == 1.50
        assert evt.notes == "Updated"
        print_success(f"Upsert correctly replaced event: value={evt.value.amount}, notes={evt.notes}")


# ============================================================
# Test 6: Query with empty date range returns no events
# ============================================================
@pytest.mark.asyncio
async def test_query_empty_range(test_server):
    """Test 6: Query events for a date range with no events."""
    print_section("Test 6: Query empty date range")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        create_item = FAAssetCreateItem(display_name=f"Event Empty Query {unique_id('EVT6')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # Query for a range with no events
        query_item = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=date(2020, 1, 1), end=date(2020, 12, 31)),
        )
        query_resp = await client.post(
            f"{API_BASE}/assets/events/query",
            json=[query_item.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        assert query_resp.status_code == 200
        result = FAEventQueryResponse(**query_resp.json())
        assert len(result.items[0].events) == 0
        print_success("Empty query correctly returns 0 events")


# ============================================================
# Test 7: Upsert for non-existent asset returns count=0
# ============================================================
@pytest.mark.asyncio
async def test_upsert_nonexistent_asset(test_server):
    """Test 7: Upsert events for a non-existent asset_id."""
    print_section("Test 7: Upsert for non-existent asset")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        events = [
            FAAssetEventPoint(
                date=date.today(),
                type="DIVIDEND",
                value=Currency(code="USD", amount=Decimal("1.00")),
            ),
        ]
        upsert_data = FAEventUpsert(asset_id=999999, events=events)

        resp = await client.post(
            f"{API_BASE}/assets/events",
            json=[upsert_data.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200
        result = FABulkEventUpsertResponse(**resp.json())
        assert result.results[0].count == 0
        assert "not found" in result.results[0].message.lower()
        print_success("Non-existent asset correctly returns count=0 with message")


# ============================================================
# Test 8: Multiple event types on same date
# ============================================================
@pytest.mark.asyncio
async def test_multiple_types_same_date(test_server):
    """Test 8: Multiple event types on the same date coexist."""
    print_section("Test 8: Multiple event types on same date")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        create_item = FAAssetCreateItem(display_name=f"Event Multi Type {unique_id('EVT8')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        today = date.today()
        event_date = today - timedelta(days=5)

        # Insert DIVIDEND and INTEREST on same date
        events = [
            FAAssetEventPoint(
                date=event_date,
                type="DIVIDEND",
                value=Currency(code="USD", amount=Decimal("1.00")),
            ),
            FAAssetEventPoint(
                date=event_date,
                type="INTEREST",
                value=Currency(code="USD", amount=Decimal("0.50")),
            ),
        ]
        upsert_data = FAEventUpsert(asset_id=asset_id, events=events)
        await client.post(
            f"{API_BASE}/assets/events",
            json=[upsert_data.model_dump(mode="json")],
            timeout=TIMEOUT,
        )

        # Query — should have both events
        query_item = FAEventQueryItem(
            asset_id=asset_id,
            date_range=DateRangeModel(start=today - timedelta(days=30), end=today),
        )
        query_resp = await client.post(
            f"{API_BASE}/assets/events/query",
            json=[query_item.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        result = FAEventQueryResponse(**query_resp.json())
        events_found = result.items[0].events
        assert len(events_found) == 2, f"Expected 2 events, got {len(events_found)}"
        types_found = {e.type for e in events_found}
        assert types_found == {"DIVIDEND", "INTEREST"}
        print_success(f"Both event types coexist on same date: {types_found}")
