"""
Test Suite: Asset Events API Endpoints

Tests for event-related endpoints:
- POST /api/v1/assets/events - Bulk upsert manual events
- DELETE /api/v1/assets/events?ids=... - Bulk delete events (RESTRICT-aware)
- POST /api/v1/assets/events/query - Bulk query events
- POST /api/v1/assets/events - editing a manual event in place (by key or by id)
"""

import uuid
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
    FAEventBulkDeleteResponse,
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
# Test 3: DELETE /assets/events?ids=... - Bulk delete (happy path)
# ============================================================


async def _create_asset_with_events(client: httpx.AsyncClient, event_count: int, prefix: str) -> tuple[int, list[int]]:
    """Helper: create an asset with N manual events and return (asset_id, [event_ids])."""
    create_item = FAAssetCreateItem(display_name=f"Bulk Delete {prefix} {unique_id(prefix)}", currency="USD")
    create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
    asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id

    today = date.today()
    events = [
        FAAssetEventPoint(
            date=today - timedelta(days=i + 1),
            type="DIVIDEND",
            value=Currency(code="USD", amount=Decimal("1.00")),
            notes=f"Evt {i}",
        )
        for i in range(event_count)
    ]
    upsert_data = FAEventUpsert(asset_id=asset_id, events=events)
    await client.post(f"{API_BASE}/assets/events", json=[upsert_data.model_dump(mode="json")], timeout=TIMEOUT)

    query_resp = await client.post(
        f"{API_BASE}/assets/events/query",
        json=[FAEventQueryItem(asset_id=asset_id, date_range=DateRangeModel(start=today - timedelta(days=60), end=today)).model_dump(mode="json")],
        timeout=TIMEOUT,
    )
    result = FAEventQueryResponse(**query_resp.json())
    ids = [e.id for e in result.items[0].events]
    assert len(ids) == event_count
    return asset_id, ids


@pytest.mark.asyncio
async def test_delete_event_bulk_happy_path(test_server):
    """Bulk delete 3 events — all should be deleted."""
    print_section("Bulk delete: happy path (3 ids, 3 deleted)")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        _asset_id, ids = await _create_asset_with_events(client, 3, "HAPPY")

        del_resp = await client.delete(
            f"{API_BASE}/assets/events",
            params=[("ids", str(i)) for i in ids],
            timeout=TIMEOUT,
        )
        assert del_resp.status_code == 200, del_resp.text
        payload = FAEventBulkDeleteResponse(**del_resp.json())
        assert payload.deleted_count == 3
        assert payload.not_found_count == 0
        assert payload.in_use_count == 0
        assert {r.status for r in payload.results} == {"deleted"}
        print_success(f"Deleted {payload.deleted_count} events in bulk")


# ============================================================
# Test 4: Bulk delete with non-existent IDs
# ============================================================
@pytest.mark.asyncio
async def test_delete_event_bulk_not_found_marked_correctly(test_server):
    """Non-existent IDs must be reported as status='not_found'."""
    print_section("Bulk delete: not_found marking")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        _asset_id, ids = await _create_asset_with_events(client, 1, "NF")
        missing_id = 9_999_999

        del_resp = await client.delete(
            f"{API_BASE}/assets/events",
            params=[("ids", str(ids[0])), ("ids", str(missing_id))],
            timeout=TIMEOUT,
        )
        assert del_resp.status_code == 200
        payload = FAEventBulkDeleteResponse(**del_resp.json())
        assert payload.deleted_count == 1
        assert payload.not_found_count == 1
        by_id = {r.event_id: r for r in payload.results}
        assert by_id[ids[0]].status == "deleted"
        assert by_id[missing_id].status == "not_found"
        print_success("not_found correctly reported; deletable event still removed")


# ============================================================
# Test 5: Bulk delete with in_use (RESTRICT) breakdown
# ============================================================
@pytest.mark.asyncio
async def test_delete_event_bulk_in_use_returns_breakdown(test_server):
    """Event referenced by a transaction → status='in_use' with breakdown."""
    print_section("Bulk delete: in_use breakdown")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        _asset_id, ids = await _create_asset_with_events(client, 1, "INUSE")
        event_id = ids[0]

        # Create a broker owned by this user and a DIVIDEND tx linked to the event.
        import uuid as _uuid  # noqa: PLC0415

        broker_name = f"BulkDel Broker {_uuid.uuid4().hex[:6]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": broker_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        broker_id = br_resp.json()["results"][0]["broker_id"]

        tx_payload = {
            "creates": [
                {
                    "broker_id": broker_id,
                    "asset_id": _asset_id,
                    "type": "DIVIDEND",
                    "date": date.today().isoformat(),
                    "cash": {"code": "USD", "amount": "1.25"},
                    "asset_event_id": event_id,
                }
            ]
        }
        tx_resp = await client.post(f"{API_BASE}/transactions/commit", json=tx_payload, timeout=TIMEOUT)
        assert tx_resp.status_code == 200, tx_resp.text
        tx_body = tx_resp.json()
        assert tx_body["committed"] is True, tx_body
        tx_id = tx_body["results"][0]["ids"][0]

        # Delete: event should now be in_use.
        del_resp = await client.delete(
            f"{API_BASE}/assets/events",
            params=[("ids", str(event_id))],
            timeout=TIMEOUT,
        )
        assert del_resp.status_code == 200
        payload = FAEventBulkDeleteResponse(**del_resp.json())
        assert payload.deleted_count == 0
        assert payload.in_use_count == 1
        item = payload.results[0]
        assert item.status == "in_use"
        assert tx_id in item.accessible_transactions
        assert item.hidden_transactions_count == 0
        print_success(f"in_use reported with accessible_transactions={item.accessible_transactions}")


# ============================================================
# Test 6: Bulk delete — partial success (mix deleted + not_found + in_use)
# ============================================================
@pytest.mark.asyncio
async def test_delete_event_bulk_partial_success(test_server):
    """Mix of deleted / not_found / in_use should be committed per-item."""
    print_section("Bulk delete: partial success (mix)")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id, ids = await _create_asset_with_events(client, 2, "MIX")
        deletable_id, blocked_id = ids[0], ids[1]
        missing_id = 9_000_001

        # Create a tx referencing blocked_id.
        import uuid as _uuid  # noqa: PLC0415

        broker_name = f"BulkDel Mix {_uuid.uuid4().hex[:6]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": broker_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        broker_id = br_resp.json()["results"][0]["broker_id"]
        await client.post(
            f"{API_BASE}/transactions/commit",
            json={
                "creates": [
                    {
                        "broker_id": broker_id,
                        "asset_id": asset_id,
                        "type": "DIVIDEND",
                        "date": date.today().isoformat(),
                        "cash": {"code": "USD", "amount": "1.00"},
                        "asset_event_id": blocked_id,
                    }
                ]
            },
            timeout=TIMEOUT,
        )

        del_resp = await client.delete(
            f"{API_BASE}/assets/events",
            params=[("ids", str(deletable_id)), ("ids", str(blocked_id)), ("ids", str(missing_id))],
            timeout=TIMEOUT,
        )
        payload = FAEventBulkDeleteResponse(**del_resp.json())
        assert payload.deleted_count == 1
        assert payload.not_found_count == 1
        assert payload.in_use_count == 1
        by_id = {r.event_id: r for r in payload.results}
        assert by_id[deletable_id].status == "deleted"
        assert by_id[blocked_id].status == "in_use"
        assert by_id[missing_id].status == "not_found"
        print_success("Mixed statuses all present; deletable committed, others reported")


# ============================================================
# Test 7: Bulk delete — no partial rollback (blocked doesn't cancel deletable)
# ============================================================
@pytest.mark.asyncio
async def test_delete_event_bulk_no_partial_rollback(test_server):
    """A single in_use id must not roll back successfully-deleted events."""
    print_section("Bulk delete: no partial rollback")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id, ids = await _create_asset_with_events(client, 2, "NOROLL")
        deletable_id, blocked_id = ids[0], ids[1]

        import uuid as _uuid  # noqa: PLC0415

        broker_name = f"BulkDel NoRoll {_uuid.uuid4().hex[:6]}"
        br_resp = await client.post(
            f"{API_BASE}/brokers",
            json=[{"name": broker_name, "allow_cash_overdraft": True}],
            timeout=TIMEOUT,
        )
        broker_id = br_resp.json()["results"][0]["broker_id"]
        await client.post(
            f"{API_BASE}/transactions/commit",
            json={
                "creates": [
                    {
                        "broker_id": broker_id,
                        "asset_id": asset_id,
                        "type": "INTEREST",
                        "date": date.today().isoformat(),
                        "cash": {"code": "USD", "amount": "1.00"},
                        "asset_event_id": blocked_id,
                    }
                ]
            },
            timeout=TIMEOUT,
        )

        del_resp = await client.delete(
            f"{API_BASE}/assets/events",
            params=[("ids", str(deletable_id)), ("ids", str(blocked_id))],
            timeout=TIMEOUT,
        )
        payload = FAEventBulkDeleteResponse(**del_resp.json())
        assert payload.deleted_count == 1
        assert payload.in_use_count == 1

        # Verify deletable_id is actually gone.
        q_resp = await client.post(
            f"{API_BASE}/assets/events/query",
            json=[FAEventQueryItem(asset_id=asset_id, date_range=DateRangeModel(start=date.today() - timedelta(days=60), end=date.today())).model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        q_result = FAEventQueryResponse(**q_resp.json())
        remaining_ids = {e.id for e in q_result.items[0].events}
        assert deletable_id not in remaining_ids, "Deletable event was rolled back"
        assert blocked_id in remaining_ids, "Blocked event was unexpectedly removed"
        print_info(f"After bulk delete, remaining ids: {remaining_ids}")
        print_success("Deletable event committed; blocked event preserved")


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


# ============================================================
# Test 9: EVENT_CURRENCY_MISMATCH → HTTP 400 (Policy D regression)
# ============================================================
@pytest.mark.asyncio
async def test_bulk_upsert_events_currency_mismatch_returns_400(test_server):
    """Test 9: Hard-400 when an event currency differs from its parent asset.

    Regression for the residual ``e.code`` → ``e.error_code`` bug discovered
    by wiki-lint pass #5 on `assets.py::bulk_upsert_events` (the third
    occurrence beyond G-batch6's market_data fixes). Before the fix the
    branch raised AttributeError, which the bare ``except Exception`` mapped
    to HTTP 500 instead of the documented HTTP 400.
    """
    print_section("Test 9: EVENT_CURRENCY_MISMATCH → HTTP 400")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        # Asset declared in USD…
        create_item = FAAssetCreateItem(display_name=f"Event Cur Mismatch {unique_id('EVT9')}", currency="USD")
        create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
        create_data = FABulkAssetCreateResponse(**create_resp.json())
        asset_id = create_data.results[0].asset_id

        # …event submitted with EUR value → must be rejected.
        events = [
            FAAssetEventPoint(
                date=date.today() - timedelta(days=1),
                type="DIVIDEND",
                value=Currency(code="EUR", amount=Decimal("1.00")),
            ),
        ]
        upsert_data = FAEventUpsert(asset_id=asset_id, events=events)

        resp = await client.post(
            f"{API_BASE}/assets/events",
            json=[upsert_data.model_dump(mode="json")],
            timeout=TIMEOUT,
        )
        assert resp.status_code == 400, f"Expected 400 for EVENT_CURRENCY_MISMATCH, got {resp.status_code}: {resp.text}"
        # The error message must mention the mismatch (asset USD vs event EUR).
        body = resp.text.upper()
        assert "EUR" in body or "USD" in body or "MISMATCH" in body or "CURRENCY" in body, f"Error body should mention the currency mismatch: {resp.text}"
        print_success("Currency-mismatched event correctly rejected with HTTP 400")


@pytest.mark.asyncio
async def test_get_events_by_ids_groups_multiple_assets(test_server):
    """Test 10: GET /assets/events groups queried IDs by asset."""
    print_section("Test 10: GET /assets/events by ids")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        created_asset_ids = []
        for prefix, amount in (("GE1", "1.10"), ("GE2", "2.20")):
            create_item = FAAssetCreateItem(display_name=f"Events By Id {unique_id(prefix)}", currency="USD")
            create_resp = await client.post(f"{API_BASE}/assets", json=[create_item.model_dump(mode="json")], timeout=TIMEOUT)
            assert create_resp.status_code == 201, create_resp.text
            asset_id = FABulkAssetCreateResponse(**create_resp.json()).results[0].asset_id
            created_asset_ids.append((asset_id, Decimal(amount)))

            upsert_resp = await client.post(
                f"{API_BASE}/assets/events",
                json=[
                    {
                        "asset_id": asset_id,
                        "events": [
                            {
                                "date": date.today().isoformat(),
                                "type": "DIVIDEND",
                                "value": {"code": "USD", "amount": amount},
                                "notes": f"event-{prefix}",
                            }
                        ],
                    }
                ],
                timeout=TIMEOUT,
            )
            assert upsert_resp.status_code == 200, upsert_resp.text

        query_resp = await client.post(
            f"{API_BASE}/assets/events/query",
            json=[
                {
                    "asset_id": asset_id,
                    "date_range": {"start": date.today().isoformat(), "end": date.today().isoformat()},
                }
                for asset_id, _amount in created_asset_ids
            ],
            timeout=TIMEOUT,
        )
        assert query_resp.status_code == 200, query_resp.text
        query_items = query_resp.json()["items"]
        event_ids = [item["events"][0]["id"] for item in query_items]
        expected_by_asset = dict(created_asset_ids)

        by_ids_resp = await client.get(
            f"{API_BASE}/assets/events",
            params=[("ids", str(event_id)) for event_id in event_ids],
            timeout=TIMEOUT,
        )
        assert by_ids_resp.status_code == 200, by_ids_resp.text
        body = by_ids_resp.json()
        assert len(body["items"]) == 2

        grouped = {item["asset_id"]: item["events"][0] for item in body["items"]}
        assert set(grouped) == set(expected_by_asset)
        for asset_id, amount in expected_by_asset.items():
            event = grouped[asset_id]
            assert event["id"] in event_ids
            assert event["is_auto"] is False
            assert Decimal(event["value"]["amount"]) == amount
        print_success("✓ GET /assets/events returned grouped manual events")


# ============================================================
# Editing a manual event in place (workstream I: F1, F2)
# ============================================================
#
# The event editor edits a row the user can see, so the edit must land on THAT
# row: same id, links kept. Before the fix (108a2adf5) ``_upsert_asset_events``
# was DELETE + INSERT on (asset_id, date, type, provider_assignment_id):
#
# * F2 — a manual event that a transaction links to could not be edited at all.
#   The DELETE hit ``transactions.asset_event_id ON DELETE RESTRICT`` and the
#   IntegrityError surfaced as HTTP 500. An unlinked event silently got a new id
#   on every edit.
# * F1 — an upsert point had no ``id`` (``extra="forbid"`` -> 422), so the editor
#   could not change the type or the date of an event: it could only add a second one.
#
# Intended contract: each point may carry an optional ``id``. Without an id, a
# (date, type) matching a manual row updates that row in place. With an id, the
# row with that id is updated in place (date, type, value and notes may change).
# The whole item is validated before anything is written:
#   - an id that is unknown, of another asset or of a provider row -> 400 EVENT_NOT_EDITABLE
#   - an edit landing on a key held by another row               -> 400 EVENT_KEY_CONFLICT
#   - the same id twice in one item                              -> 422 ("duplicate")
#
# The payloads are plain JSON on purpose. Importing the new point schema would
# have broken this whole module before the fix, instead of failing only the tests below.
#
# Every test owns a fresh USD asset. Events are scoped by asset, so the fixed
# dates below cannot meet another test's rows. At the end each test drops what it
# created: brokers first (force, which takes the transactions pinning the events),
# then the asset, which cascades its events. Users are left in place, as in the
# rest of this module.

EDIT_DAY = date(2024, 3, 15)
EDIT_OTHER_DAY = date(2024, 4, 15)
EDIT_WINDOW = {"start": "2024-01-01", "end": "2024-12-31"}
UNKNOWN_EVENT_ID = 9_999_999


class _OwnedRows:
    """What one test created through the API, dropped in FK-safe order at the end."""

    def __init__(self) -> None:
        self.asset_ids: list[int] = []
        self.broker_ids: list[int] = []

    async def drop(self, client: httpx.AsyncClient) -> list[str]:
        """Drop brokers, then assets. Never raises: what could not be removed is returned."""
        return await self._drop_brokers(client) + await self._drop_assets(client)

    async def _drop_brokers(self, client: httpx.AsyncClient) -> list[str]:
        problems: list[str] = []
        for broker_id in self.broker_ids:
            try:
                resp = await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
                done = resp.status_code == 200 and any(r.get("id") == broker_id and r.get("success") for r in resp.json().get("results", []))
                if not done:
                    problems.append(f"broker {broker_id}: HTTP {resp.status_code} {resp.text}")
            except Exception as exc:
                problems.append(f"broker {broker_id}: {exc!r}")
        return problems

    async def _drop_assets(self, client: httpx.AsyncClient) -> list[str]:
        if not self.asset_ids:
            return []
        try:
            resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": self.asset_ids}, timeout=TIMEOUT)
            deleted = {r["asset_id"] for r in resp.json().get("results", []) if r.get("success")} if resp.status_code == 200 else set()
        except Exception as exc:
            return [f"assets {self.asset_ids}: {exc!r}"]
        return [f"asset {asset_id}: HTTP {resp.status_code} {resp.text}" for asset_id in self.asset_ids if asset_id not in deleted]


def _point(day: date, kind: str, amount: str, *, event_id: int | None = None, notes: str | None = None) -> dict:
    """One point of the upsert body, as the editor sends it."""
    point: dict = {"date": day.isoformat(), "type": kind, "value": {"code": "USD", "amount": amount}}
    if event_id is not None:
        point["id"] = event_id
    if notes is not None:
        point["notes"] = notes
    return point


async def _new_asset(client: httpx.AsyncClient, owned: _OwnedRows, prefix: str) -> int:
    name = f"Event Edit {prefix} {uuid.uuid4().hex}"
    resp = await client.post(f"{API_BASE}/assets", json=[{"display_name": name, "currency": "USD"}], timeout=TIMEOUT)
    assert resp.status_code == 201, resp.text
    row = next(r for r in resp.json()["results"] if r["display_name"] == name)
    assert row["success"] is True, row
    owned.asset_ids.append(row["asset_id"])
    return row["asset_id"]


async def _upsert(client: httpx.AsyncClient, asset_id: int, points: list[dict]) -> httpx.Response:
    return await client.post(f"{API_BASE}/assets/events", json=[{"asset_id": asset_id, "events": points}], timeout=TIMEOUT)


async def _seed(client: httpx.AsyncClient, asset_id: int, points: list[dict]) -> None:
    """Create events with a plain no-id upsert, the way they exist today."""
    resp = await _upsert(client, asset_id, points)
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["results"] if r["asset_id"] == asset_id)
    assert row["count"] == len(points), row


async def _events(client: httpx.AsyncClient, asset_id: int) -> list[dict]:
    """Every event of this asset in the window the tests below write in."""
    resp = await client.post(f"{API_BASE}/assets/events/query", json=[{"asset_id": asset_id, "date_range": EDIT_WINDOW}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return next(item for item in resp.json()["items"] if item["asset_id"] == asset_id)["events"]


async def _events_on(client: httpx.AsyncClient, asset_id: int, day: date) -> list[dict]:
    return [e for e in await _events(client, asset_id) if e["date"] == day.isoformat()]


async def _the_event(client: httpx.AsyncClient, asset_id: int, day: date, kind: str) -> dict:
    """The one event of ``kind`` on ``day``: fails if there is none or more than one."""
    matches = [e for e in await _events_on(client, asset_id, day) if e["type"] == kind]
    assert len(matches) == 1, f"expected exactly one {kind} on {day} for asset {asset_id}, got {matches}"
    return matches[0]


def _amount(event: dict) -> Decimal:
    return Decimal(str(event["value"]["amount"]))


async def _snapshot(client: httpx.AsyncClient, asset_id: int) -> dict[int, tuple]:
    """id -> (date, type, amount, notes) of every event of the asset: the "nothing written" check."""
    return {e["id"]: (e["date"], e["type"], _amount(e), e.get("notes")) for e in await _events(client, asset_id)}


async def _tx_event_id(client: httpx.AsyncClient, tx_id: int) -> int | None:
    resp = await client.get(f"{API_BASE}/transactions", params={"ids": [tx_id]}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return next(t for t in resp.json() if t["id"] == tx_id)["asset_event_id"]


async def _link_dividend_tx(client: httpx.AsyncClient, owned: _OwnedRows, asset_id: int, event_id: int, day: date) -> int:
    """Commit a DIVIDEND, on a broker of this test's own, linked to ``event_id``."""
    broker_name = f"Event Edit Broker {uuid.uuid4().hex}"
    br_resp = await client.post(f"{API_BASE}/brokers", json=[{"name": broker_name, "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert br_resp.status_code == 200, br_resp.text
    broker_row = next(r for r in br_resp.json()["results"] if r["name"] == broker_name)
    assert broker_row["success"] is True, broker_row
    owned.broker_ids.append(broker_row["broker_id"])

    tx_resp = await client.post(
        f"{API_BASE}/transactions/commit",
        json={
            "creates": [
                {
                    "broker_id": broker_row["broker_id"],
                    "asset_id": asset_id,
                    "type": "DIVIDEND",
                    "date": day.isoformat(),
                    "cash": {"code": "USD", "amount": "1.25"},
                    "asset_event_id": event_id,
                }
            ]
        },
        timeout=TIMEOUT,
    )
    assert tx_resp.status_code == 200, tx_resp.text
    tx_body = tx_resp.json()
    assert tx_body["committed"] is True, tx_body
    tx_id = next(r for r in tx_body["results"] if r["operation"] == "create" and r["index"] == 0)["ids"][0]
    # Precondition: without the link the edits below would prove nothing about F2.
    assert await _tx_event_id(client, tx_id) == event_id
    return tx_id


def _assert_rejected(resp: httpx.Response, code: str) -> None:
    assert resp.status_code == 400, f"expected HTTP 400 {code}, got {resp.status_code}: {resp.text}"
    assert code in str(resp.json()["detail"]), resp.text


@pytest.mark.asyncio
async def test_upsert_without_id_updates_a_linked_event_in_place(test_server):
    """F2: re-upserting the (date, type) of a manual event a transaction links to edits that row.

    Before the fix: the DELETE half of DELETE + INSERT violates ``ON DELETE RESTRICT`` -> HTTP 500.
    Contract: 200. The same row (same id) carries the new amount and notes, it is the
    only DIVIDEND of that day, and the transaction still points at it.
    """
    print_section("Event edit: no-id upsert of a linked event updates it in place")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "LINKED")
            await _seed(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00", notes="original")])
            event_id = (await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND"))["id"]
            tx_id = await _link_dividend_tx(client, owned, asset_id, event_id, EDIT_DAY)

            resp = await _upsert(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.75", notes="edited")])

            assert resp.status_code == 200, f"editing a linked event must not fail: {resp.status_code} {resp.text}"
            edited = await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND")
            assert edited["id"] == event_id, f"the edit replaced row {event_id} with row {edited['id']}"
            assert _amount(edited) == Decimal("1.75")
            assert edited["notes"] == "edited"
            assert await _tx_event_id(client, tx_id) == event_id
            print_success(f"Linked event {event_id} edited in place; transaction {tx_id} still linked")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_upsert_without_id_keeps_the_event_id(test_server):
    """F2, unlinked half: an edit by (date, type) keeps the id of the row it edits.

    Before the fix: DELETE + INSERT -> 200, but the event comes back under a NEW id, so whatever
    held the old id (the editor's selection, a link made a moment later) points at nothing.
    Contract: same id, new amount.
    """
    print_section("Event edit: no-id upsert keeps the event id")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "KEEPID")
            await _seed(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00")])
            event_id = (await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND"))["id"]

            resp = await _upsert(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "2.50")])

            assert resp.status_code == 200, resp.text
            edited = await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND")
            assert edited["id"] == event_id, f"the edit replaced row {event_id} with row {edited['id']}"
            assert _amount(edited) == Decimal("2.50")
            print_success(f"Event {event_id} kept its id across an edit")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_upsert_with_id_changes_the_type_in_place(test_server):
    """F1: a point carrying an id retypes its own row instead of adding a second event.

    Before the fix: ``id`` was not a field of the strict upsert point -> 422.
    Contract: 200. On that day the asset has exactly one event: same id, type INTEREST.
    """
    print_section("Event edit: id-bearing upsert changes the type in place")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "RETYPE")
            await _seed(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00")])
            event_id = (await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND"))["id"]

            resp = await _upsert(client, asset_id, [_point(EDIT_DAY, "INTEREST", "1.00", event_id=event_id)])

            assert resp.status_code == 200, resp.text
            on_day = await _events_on(client, asset_id, EDIT_DAY)
            assert [(e["id"], e["type"]) for e in on_day] == [(event_id, "INTEREST")], on_day
            print_success(f"Event {event_id} retyped DIVIDEND -> INTEREST in place")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_upsert_with_id_moves_the_date_in_place(test_server):
    """F1: a point carrying an id can move its row to another date.

    Before the fix: 422 (``id`` was an unknown field).
    Contract: 200. The row is on the new date under the same id and the old date is empty.
    """
    print_section("Event edit: id-bearing upsert moves the date in place")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "MOVE")
            await _seed(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00")])
            event_id = (await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND"))["id"]
            assert await _events_on(client, asset_id, EDIT_OTHER_DAY) == []

            resp = await _upsert(client, asset_id, [_point(EDIT_OTHER_DAY, "DIVIDEND", "1.00", event_id=event_id)])

            assert resp.status_code == 200, resp.text
            assert await _events_on(client, asset_id, EDIT_DAY) == []
            moved = await _the_event(client, asset_id, EDIT_OTHER_DAY, "DIVIDEND")
            assert moved["id"] == event_id
            assert _amount(moved) == Decimal("1.00")
            print_success(f"Event {event_id} moved {EDIT_DAY} -> {EDIT_OTHER_DAY} in place")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_upsert_with_id_retypes_a_linked_event(test_server):
    """Retyping an event a transaction links to is allowed, and the link survives.

    Developer decision: the type of a linked event may change. The DIVIDEND transaction
    keeps its ``asset_event_id``, even though the event is now an INTEREST.

    Before the fix: 422 (``id`` was an unknown field).
    Contract: 200. The row is INTEREST under the same id, no DIVIDEND is left on that
    day, and the transaction still points at the row.
    """
    print_section("Event edit: retyping a linked event keeps the link")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "RETYPELINK")
            await _seed(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00")])
            event_id = (await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND"))["id"]
            tx_id = await _link_dividend_tx(client, owned, asset_id, event_id, EDIT_DAY)

            resp = await _upsert(client, asset_id, [_point(EDIT_DAY, "INTEREST", "1.00", event_id=event_id)])

            assert resp.status_code == 200, resp.text
            on_day = await _events_on(client, asset_id, EDIT_DAY)
            assert [(e["id"], e["type"]) for e in on_day] == [(event_id, "INTEREST")], on_day
            assert await _tx_event_id(client, tx_id) == event_id
            print_success(f"Linked event {event_id} retyped; transaction {tx_id} still linked")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_upsert_with_an_id_of_another_asset_is_rejected(test_server):
    """An id belonging to another asset is not editable through this asset's item.

    Before the fix: 422 (``id`` was an unknown field), not the 400 the editor can explain.
    Contract: 400 EVENT_NOT_EDITABLE. Nothing is written: the other asset's event is
    unchanged and no event appears on the asset the item names.
    """
    print_section("Event edit: an id of another asset is rejected")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "OWNER")
            other_asset_id = await _new_asset(client, owned, "OTHER")
            await _seed(client, other_asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00", notes="not yours")])
            foreign_id = (await _the_event(client, other_asset_id, EDIT_DAY, "DIVIDEND"))["id"]
            other_before = await _snapshot(client, other_asset_id)

            resp = await _upsert(client, asset_id, [_point(EDIT_OTHER_DAY, "DIVIDEND", "9.99", event_id=foreign_id)])

            _assert_rejected(resp, "EVENT_NOT_EDITABLE")
            assert await _snapshot(client, other_asset_id) == other_before
            assert await _snapshot(client, asset_id) == {}
            print_success(f"Event {foreign_id} of asset {other_asset_id} rejected for asset {asset_id}")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_upsert_with_an_unknown_id_is_rejected(test_server):
    """An id that matches no event is rejected, not silently turned into a new event.

    Before the fix: 422 (``id`` was an unknown field).
    Contract: 400 EVENT_NOT_EDITABLE, nothing written.
    """
    print_section("Event edit: an unknown id is rejected")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            by_id = await client.get(f"{API_BASE}/assets/events", params={"ids": [UNKNOWN_EVENT_ID]}, timeout=TIMEOUT)
            assert by_id.status_code == 200, by_id.text
            assert by_id.json()["items"] == [], f"precondition: event {UNKNOWN_EVENT_ID} must not exist, got {by_id.text}"
            asset_id = await _new_asset(client, owned, "UNKNOWN")
            await _seed(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00")])
            before = await _snapshot(client, asset_id)

            resp = await _upsert(client, asset_id, [_point(EDIT_OTHER_DAY, "DIVIDEND", "5.00", event_id=UNKNOWN_EVENT_ID)])

            _assert_rejected(resp, "EVENT_NOT_EDITABLE")
            assert await _snapshot(client, asset_id) == before
            print_success(f"Unknown event id {UNKNOWN_EVENT_ID} rejected")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_upsert_with_id_onto_an_existing_key_is_a_conflict(test_server):
    """Retyping E1 onto the (date, type) another manual row already holds is a conflict.

    E1 = (D, DIVIDEND) and E2 = (D, INTEREST); the item retypes E1 to INTEREST alone.
    Before the fix: 422 (``id`` was an unknown field).
    Contract: 400 EVENT_KEY_CONFLICT; both rows unchanged.
    """
    print_section("Event edit: an id-update onto a held key is a conflict")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "CONFLICT")
            await _seed(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00"), _point(EDIT_DAY, "INTEREST", "0.50")])
            e1 = await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND")
            await _the_event(client, asset_id, EDIT_DAY, "INTEREST")
            before = await _snapshot(client, asset_id)

            resp = await _upsert(client, asset_id, [_point(EDIT_DAY, "INTEREST", "1.00", event_id=e1["id"])])

            _assert_rejected(resp, "EVENT_KEY_CONFLICT")
            assert await _snapshot(client, asset_id) == before
            print_success("Retype onto a held key rejected; both rows unchanged")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_key_conflict_rejects_the_whole_item_before_writing(test_server):
    """Validation covers the whole item before any write: a valid edit listed first is not applied.

    E1 = (D, DIVIDEND), E2 = (D, INTEREST), E3 = (D', DIVIDEND). The item first changes
    E3's amount (valid on its own), then retypes E1 onto E2's key (conflict).
    Before the fix: 422 (``id`` was an unknown field).
    Contract: 400 EVENT_KEY_CONFLICT and E3 keeps its old amount: nothing was written.
    """
    print_section("Event edit: a conflict rejects the whole item before writing")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "ATOMIC")
            await _seed(
                client,
                asset_id,
                [_point(EDIT_DAY, "DIVIDEND", "1.00"), _point(EDIT_DAY, "INTEREST", "0.50"), _point(EDIT_OTHER_DAY, "DIVIDEND", "2.00")],
            )
            e1 = await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND")
            e3 = await _the_event(client, asset_id, EDIT_OTHER_DAY, "DIVIDEND")
            before = await _snapshot(client, asset_id)

            resp = await _upsert(
                client,
                asset_id,
                [
                    _point(EDIT_OTHER_DAY, "DIVIDEND", "2.75", event_id=e3["id"]),
                    _point(EDIT_DAY, "INTEREST", "1.00", event_id=e1["id"]),
                ],
            )

            _assert_rejected(resp, "EVENT_KEY_CONFLICT")
            assert _amount(await _the_event(client, asset_id, EDIT_OTHER_DAY, "DIVIDEND")) == Decimal("2.00")
            assert await _snapshot(client, asset_id) == before
            print_success("Conflicting item rejected as a whole; the valid edit was not applied")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_upsert_with_ids_can_swap_two_types(test_server):
    """Two rows of one item may swap their keys: each lands on the key the other leaves.

    Before the fix: 422 (``id`` was an unknown field).
    Contract: 200. Both ids are kept and their types are swapped, amounts as sent.
    """
    print_section("Event edit: two id-updates swap their types")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "SWAP")
            await _seed(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00"), _point(EDIT_DAY, "INTEREST", "0.50")])
            e1_id = (await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND"))["id"]
            e2_id = (await _the_event(client, asset_id, EDIT_DAY, "INTEREST"))["id"]

            resp = await _upsert(
                client,
                asset_id,
                [_point(EDIT_DAY, "INTEREST", "1.00", event_id=e1_id), _point(EDIT_DAY, "DIVIDEND", "0.50", event_id=e2_id)],
            )

            assert resp.status_code == 200, resp.text
            on_day = {e["id"]: (e["type"], _amount(e)) for e in await _events_on(client, asset_id, EDIT_DAY)}
            assert on_day == {e1_id: ("INTEREST", Decimal("1.00")), e2_id: ("DIVIDEND", Decimal("0.50"))}
            print_success(f"Events {e1_id} and {e2_id} swapped types in place")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_new_event_on_the_final_key_of_an_id_update_is_a_conflict(test_server):
    """A no-id event may not take the key an id-update of the same item moves onto.

    E1 = (D, DIVIDEND); D has no INTEREST beforehand. The item retypes E1 to INTEREST
    and also sends a new (D, INTEREST) without id.
    Before the fix: 422 (``id`` was an unknown field).
    Contract: 400 EVENT_KEY_CONFLICT, nothing written.
    """
    print_section("Event edit: a new event on an id-update's final key is a conflict")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "NEWONKEY")
            await _seed(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00")])
            e1_id = (await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND"))["id"]
            assert [e for e in await _events_on(client, asset_id, EDIT_DAY) if e["type"] == "INTEREST"] == []
            before = await _snapshot(client, asset_id)

            resp = await _upsert(client, asset_id, [_point(EDIT_DAY, "INTEREST", "1.00", event_id=e1_id), _point(EDIT_DAY, "INTEREST", "0.40")])

            _assert_rejected(resp, "EVENT_KEY_CONFLICT")
            assert await _snapshot(client, asset_id) == before
            print_success("New event on an id-update's final key rejected")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_duplicate_event_id_in_one_item_is_rejected(test_server):
    """The same id twice in one item is a malformed request.

    Before the fix: 422 too, but for the wrong reason (``id`` was an unknown field), so the body
    never mentions a duplicate.
    Contract: 422 whose text names the duplicate id ("Duplicate event id"), nothing written.
    """
    print_section("Event edit: a duplicate id in one item is rejected")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "DUPID")
            await _seed(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00")])
            e1_id = (await _the_event(client, asset_id, EDIT_DAY, "DIVIDEND"))["id"]
            before = await _snapshot(client, asset_id)

            resp = await _upsert(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.10", event_id=e1_id), _point(EDIT_OTHER_DAY, "DIVIDEND", "1.20", event_id=e1_id)])

            assert resp.status_code == 422, resp.text
            assert "duplicate" in resp.text.lower(), f"the 422 must name the duplicate id: {resp.text}"
            assert await _snapshot(client, asset_id) == before
            print_success("Duplicate id rejected with 422")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers


@pytest.mark.asyncio
async def test_upsert_with_ids_edits_two_events_sharing_a_key(test_server):
    """Rows that keep their key may share it: legacy same-key duplicates stay editable by id.

    Precondition: one no-id upsert carrying the same (date, type) twice stores two rows
    (the code before the fix did; the contract does not say whether it still will). If it does not, the
    test skips: the service-level twin
    ``test_asset_source_upsert_guards.py::test_two_manual_events_sharing_a_key_are_edited_by_id``
    builds the duplicates directly in the database instead.

    Before the fix: 422 (``id`` was an unknown field).
    Contract: 200. Both ids are kept, each with its own new amount.
    """
    print_section("Event edit: two rows sharing a key are edited by id")
    owned = _OwnedRows()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        try:
            asset_id = await _new_asset(client, owned, "STAYERS")
            seed = await _upsert(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.00", notes="first"), _point(EDIT_DAY, "DIVIDEND", "1.00", notes="second")])
            dividends = [e for e in await _events_on(client, asset_id, EDIT_DAY) if e["type"] == "DIVIDEND"]
            if seed.status_code != 200 or len(dividends) != 2:
                reason = f"precondition not met: a no-id upsert no longer stores two DIVIDEND rows on one day (HTTP {seed.status_code}, {len(dividends)} rows)"
                pytest.skip(f"{reason}; covered by test_asset_source_upsert_guards.py::test_two_manual_events_sharing_a_key_are_edited_by_id")
            first_id, second_id = sorted(e["id"] for e in dividends)

            resp = await _upsert(client, asset_id, [_point(EDIT_DAY, "DIVIDEND", "1.11", event_id=first_id), _point(EDIT_DAY, "DIVIDEND", "2.22", event_id=second_id)])

            assert resp.status_code == 200, resp.text
            after = {e["id"]: _amount(e) for e in await _events_on(client, asset_id, EDIT_DAY) if e["type"] == "DIVIDEND"}
            assert after == {first_id: Decimal("1.11"), second_id: Decimal("2.22")}
            print_success(f"Same-key rows {first_id} and {second_id} edited independently")
        finally:
            leftovers = await owned.drop(client)
    assert not leftovers, leftovers
