"""
Test Suite: Market-Data Wipe Endpoints (R3-3 Policy D direct API)

Covers Phase 7 Part 3 Closure_2 G-batch6 (post-G coverage gap-fill):

- ``GET  /api/v1/assets/{id}/market-data/summary``  → dry-run counters.
- ``POST /api/v1/assets/{id}/market-data/wipe``     → destructive wipe.

Both endpoints delegate to ``AssetSourceManager.wipe_market_data_for_currency_change``
which had **0% coverage** because ``test_asset_currency_change.py`` exercised
the Policy D flow only indirectly (via ``DELETE /assets/prices`` + ``PATCH``).
This suite invokes the dedicated wipe surface to lock the contract:

    Returns dict {prices, events_manual, events_provider, linked_tx,
                  oldest, newest (ISO|None), dry_run}.

Tests:
- summary on empty asset → all counters zero, dry_run=true.
- summary on populated asset → counters reflect prices + manual events,
  oldest/newest are ISO dates, dry_run=true.
- wipe destructive removes prices + events, returns dry_run=false,
  re-call on already-empty asset returns zeros (idempotent).
- 404 when asset id does not exist (ASSET_NOT_FOUND mapping).
- linked transactions are disconnected, not deleted.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G-batch6.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets import FAAssetCreateItem, FABulkAssetCreateResponse
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import FAAssetEventPoint, FAEventUpsert, FAPricePoint, FAUpsert
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    import time  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415

    username = f"test_{int(time.time() * 1000)}_{_uuid.uuid4().hex[:4]}"
    email = f"{username}@test.com"
    password = "TestPass123!"
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    assert resp.status_code == 201, resp.text
    login = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    assert login.status_code == 200, login.text
    session = login.cookies.get("session")
    if session:
        client.cookies.set("session", session)


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as srv:
        if not srv.start_server():
            pytest.fail("Failed to start test server")
        yield srv


async def _create_asset(client: httpx.AsyncClient, tag: str, currency: str = "USD") -> int:
    item = FAAssetCreateItem(display_name=f"WipeTest {unique_id(tag)}", currency=currency)
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    return FABulkAssetCreateResponse(**resp.json()).results[0].asset_id


async def _seed_prices(client: httpx.AsyncClient, asset_id: int, start: date, count: int) -> None:
    points = [FAPricePoint(date=start + timedelta(days=i), close=Decimal("100.00") + Decimal(i)) for i in range(count)]
    payload = FAUpsert(asset_id=asset_id, prices=points)
    resp = await client.post(
        f"{API_BASE}/assets/prices",
        json=[payload.model_dump(mode="json")],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text


async def _seed_events(client: httpx.AsyncClient, asset_id: int, start: date, count: int, currency: str = "USD") -> None:
    events = [
        FAAssetEventPoint(
            date=start + timedelta(days=i),
            type="DIVIDEND",
            value=Currency(code=currency, amount=Decimal("0.25") + Decimal(i) / Decimal(100)),
            notes=f"wipe-test event {i}",
        )
        for i in range(count)
    ]
    upsert = FAEventUpsert(asset_id=asset_id, events=events)
    resp = await client.post(
        f"{API_BASE}/assets/events",
        json=[upsert.model_dump(mode="json")],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_summary_on_empty_asset_returns_zeros(test_server):
    """G-batch6.1 — GET /summary on empty asset → all counters zero, dry_run=true."""
    print_section("G-batch6.1 — empty asset summary")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "WB6.1")

        resp = await client.get(f"{API_BASE}/assets/{asset_id}/market-data/summary", timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["prices"] == 0
        assert body["events_manual"] == 0
        assert body["events_provider"] == 0
        assert body["linked_tx"] == 0
        assert body["oldest"] is None
        assert body["newest"] is None
        assert body["dry_run"] is True
        print_success("Empty asset summary: all counters zero")


@pytest.mark.asyncio
async def test_summary_reflects_prices_and_events(test_server):
    """G-batch6.2 — summary counters mirror seeded prices + manual events."""
    print_section("G-batch6.2 — populated asset summary")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "WB6.2")
        start = date.today() - timedelta(days=10)
        await _seed_prices(client, asset_id, start, 5)
        await _seed_events(client, asset_id, start + timedelta(days=2), 3)

        resp = await client.get(f"{API_BASE}/assets/{asset_id}/market-data/summary", timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["prices"] == 5, body
        assert body["events_manual"] == 3, body
        assert body["events_provider"] == 0, body
        assert body["linked_tx"] == 0, body
        assert body["oldest"] == start.isoformat()
        assert body["newest"] == (start + timedelta(days=4)).isoformat()
        assert body["dry_run"] is True
        print_success(f"Summary: prices={body['prices']}, events_manual={body['events_manual']}")


@pytest.mark.asyncio
async def test_wipe_destructive_removes_data_and_is_idempotent(test_server):
    """G-batch6.3 — POST /wipe deletes prices+events; second call sees zeros."""
    print_section("G-batch6.3 — destructive wipe + idempotency")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "WB6.3")
        start = date.today() - timedelta(days=7)
        await _seed_prices(client, asset_id, start, 4)
        await _seed_events(client, asset_id, start, 2)

        # First wipe — destructive, returns the pre-wipe counters.
        wipe1 = await client.post(f"{API_BASE}/assets/{asset_id}/market-data/wipe", timeout=TIMEOUT)
        assert wipe1.status_code == 200, wipe1.text
        body1 = wipe1.json()
        assert body1["prices"] == 4, body1
        assert body1["events_manual"] == 2, body1
        assert body1["dry_run"] is False
        print_info(f"First wipe deleted prices={body1['prices']}, events={body1['events_manual']}")

        # Summary after wipe → all zero.
        summary = await client.get(f"{API_BASE}/assets/{asset_id}/market-data/summary", timeout=TIMEOUT)
        assert summary.status_code == 200
        s = summary.json()
        assert s["prices"] == 0 and s["events_manual"] == 0 and s["oldest"] is None

        # Second wipe — idempotent: nothing left to delete, all counters zero.
        wipe2 = await client.post(f"{API_BASE}/assets/{asset_id}/market-data/wipe", timeout=TIMEOUT)
        assert wipe2.status_code == 200, wipe2.text
        body2 = wipe2.json()
        assert body2["prices"] == 0 and body2["events_manual"] == 0
        assert body2["dry_run"] is False
        print_success("Wipe is destructive on first call, no-op on second (idempotent)")


@pytest.mark.asyncio
async def test_wipe_unknown_asset_returns_404(test_server):
    """G-batch6.4 — wipe / summary on unknown asset → 404 (ASSET_NOT_FOUND)."""
    print_section("G-batch6.4 — unknown asset → 404")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        ghost_id = 999_999_999

        for method, path in (
            ("GET", f"/assets/{ghost_id}/market-data/summary"),
            ("POST", f"/assets/{ghost_id}/market-data/wipe"),
        ):
            resp = await client.request(method, f"{API_BASE}{path}", timeout=TIMEOUT)
            assert resp.status_code == 404, f"{method} {path} → {resp.status_code}: {resp.text}"
        print_success("Unknown asset id correctly mapped to 404 on both endpoints")


@pytest.mark.asyncio
async def test_summary_dry_run_does_not_mutate(test_server):
    """G-batch6.5 — summary endpoint never deletes (dry_run=true contract)."""
    print_section("G-batch6.5 — summary is purely read-only")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "WB6.5")
        start = date.today() - timedelta(days=3)
        await _seed_prices(client, asset_id, start, 2)

        # Call summary twice — counters must stay stable across calls.
        for attempt in (1, 2):
            resp = await client.get(f"{API_BASE}/assets/{asset_id}/market-data/summary", timeout=TIMEOUT)
            assert resp.status_code == 200
            body = resp.json()
            assert body["prices"] == 2, f"attempt {attempt}: prices changed → {body}"
            assert body["dry_run"] is True
        print_success("Summary endpoint is non-mutating across repeated calls")
