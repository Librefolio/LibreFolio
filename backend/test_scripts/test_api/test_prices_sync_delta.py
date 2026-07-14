"""
Test Suite: Sync Delta Payload (I-bis #24)

Covers Phase 7 Part 3 Blocco G.12 — ``FARefreshResult.changed_points``
contract on ``POST /api/v1/assets/prices/sync``.

Contract (``backend/app/services/asset_source.py`` L2727):

    changed_points = (
        changed_items_delta
        if changed_items_delta and len(changed_items_delta) <= CHANGED_POINTS_PAYLOAD_CAP
        else None
    )

i.e.:

- **empty delta** (idempotent re-sync, zero real changes) → ``None``
  (truthiness check: ``[]`` is falsy, so the ternary picks ``None``).
- **1 … CAP items** → the list is returned verbatim so the frontend
  can merge it into the chart without a full re-query.
- **> CAP items** → ``None``: the delta would be too large to ship on
  the wire; the frontend is expected to fall back to a full reload.

Additional guarantee: ``changed_items_delta`` only contains points that
are *actually* new or whose close differs from the stored value (see
``_count_actual_price_changes`` L2487). Points already stored with the
same close are NOT included in the delta even if they were fetched.

Provider under test: ``mockprov`` (deterministic 100.00 USD daily).

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G.12.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.models import ProviderInputType
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets import (
    FAAssetCreateItem,
    FABulkAssetCreateResponse,
)
from backend.app.schemas.prices import FAPricePoint, FAUpsert
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.schemas.refresh import CHANGED_POINTS_PAYLOAD_CAP
from backend.app.services.asset_source import AssetSourceManager
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 60.0


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


async def _create_asset_with_mockprov(client: httpx.AsyncClient, tag: str) -> int:
    item = FAAssetCreateItem(display_name=f"G12 {unique_id(tag)}", currency="USD")
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    asset_id = FABulkAssetCreateResponse(**resp.json()).results[0].asset_id

    # Assign mockprov via direct service (same pattern as test_current_price_persistence).
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await AssetSourceManager.bulk_assign_providers(
            [
                FAProviderAssignmentItem(
                    asset_id=asset_id,
                    provider_code="mockprov",
                    identifier=f"MOCK-G12-{asset_id}",
                    identifier_type=ProviderInputType.AUTO_GENERATED,
                    provider_params={},
                )
            ],
            session,
        )
    return asset_id


async def _sync(
    client: httpx.AsyncClient,
    asset_id: int,
    start: date,
    end: date,
) -> dict:
    resp = await client.post(
        f"{API_BASE}/assets/prices/sync",
        json=[
            {
                "asset_id": asset_id,
                "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            }
        ],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"sync failed: {resp.status_code} {resp.text}"
    body = resp.json()
    assert body["results"], body
    return body["results"][0]


async def _overwrite_close(
    client: httpx.AsyncClient,
    asset_id: int,
    target_date: date,
    new_close: Decimal,
) -> None:
    """Manually overwrite one day's price so the next sync detects a change.

    Writes a fully self-consistent flat candle (open=high=low=close=new_close)
    instead of close-only. mockprov's fixture data is itself a flat candle
    (open=high=low=close=100.00, see mockprov.py get_history_value) — merging
    a close-only update via F.4 sentinel rules would preserve the OLD
    open/high/low (100.00) while writing the NEW close (999.99), producing an
    internally-impossible row (close outside [low, high]) that
    bulk_upsert_prices' OHLC-integrity guard now rejects (added after a real
    corrupted row was found in production: close=63560.94 with high=8692.20).
    A real price change moves the whole candle, not just one field.
    """
    payload = FAUpsert(asset_id=asset_id, prices=[FAPricePoint(date=target_date, open=new_close, high=new_close, low=new_close, close=new_close)])
    resp = await client.post(
        f"{API_BASE}/assets/prices",
        json=[payload.model_dump(mode="json")],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_first_sync_returns_delta_with_all_new_points(test_server):
    """Empty DB → sync 5 days → changed_points contains 5 new points."""
    print_section("G.12.1 — first sync populates changed_points (all new)")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset_with_mockprov(client, "G12.1")
        # Use a past range so sync is deterministic (doesn't race today's bootstrap).
        start = date.today() - timedelta(days=10)
        end = start + timedelta(days=4)

        result = await _sync(client, asset_id, start, end)
        assert result["points_fetched"] == 5, result
        assert result["inserted_count"] == 5, result
        assert result["updated_count"] == 0, result

        delta = result.get("changed_points")
        assert delta is not None, f"expected populated delta, got None: {result}"
        assert len(delta) == 5, f"expected 5 items, got {len(delta)}"
        # Values match mockprov's fixed 100.00.
        for p in delta:
            assert Decimal(p["close"]) == Decimal("100.00"), p
        dates = {p["date"] for p in delta}
        assert dates == {(start + timedelta(days=i)).isoformat() for i in range(5)}
        print_success(f"changed_points populated with {len(delta)} new items")


@pytest.mark.asyncio
async def test_idempotent_resync_yields_none_delta(test_server):
    """Same sync twice → second call has changed_points = None (empty delta)."""
    print_section("G.12.2 — idempotent re-sync → changed_points = None")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset_with_mockprov(client, "G12.2")
        start = date.today() - timedelta(days=10)
        end = start + timedelta(days=2)

        first = await _sync(client, asset_id, start, end)
        assert first["points_changed"] == 3, first

        second = await _sync(client, asset_id, start, end)
        # Mockprov returns the same 100.00; every fetched point matches DB.
        assert second["points_fetched"] == 3, second
        assert second["inserted_count"] == 0, second
        assert second["updated_count"] == 0, second
        assert second["points_changed"] == 0, second
        # Contract: empty delta → None (the ternary truthiness check).
        assert second.get("changed_points") is None, f"expected None, got {second.get('changed_points')!r}"
        print_success("Re-sync idempotent: changed_points = None")


@pytest.mark.asyncio
async def test_partial_change_delta_contains_only_modified(test_server):
    """Seed 4 days, manually alter 1 close, re-sync → delta has exactly 1 item."""
    print_section("G.12.3 — delta contains only actually-changed points")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset_with_mockprov(client, "G12.3")
        start = date.today() - timedelta(days=10)
        end = start + timedelta(days=3)

        await _sync(client, asset_id, start, end)  # prime DB with 4 rows @ 100.00

        # Tamper with day+1 so the next sync detects a real change.
        target = start + timedelta(days=1)
        await _overwrite_close(client, asset_id, target, Decimal("999.99"))

        result = await _sync(client, asset_id, start, end)
        # Only the tampered date is a "change" (fetched 100.00 != stored 999.99);
        # the other 3 are fetched-but-unchanged → NOT in delta.
        assert result["updated_count"] == 1, result
        assert result["inserted_count"] == 0, result
        delta = result.get("changed_points")
        assert delta is not None and len(delta) == 1, result
        assert delta[0]["date"] == target.isoformat()
        assert Decimal(delta[0]["close"]) == Decimal("100.00")
        print_success("Delta surgical: 1 item (the tampered date only)")


@pytest.mark.asyncio
async def test_delta_above_cap_is_omitted(test_server):
    """Sync CAP+1 days on empty DB → delta omitted (None) to keep payload bounded."""
    print_section(f"G.12.4 — delta > {CHANGED_POINTS_PAYLOAD_CAP} → None")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset_with_mockprov(client, "G12.4")
        # Go CAP+1 days deep so the inserted delta exceeds the cap.
        days = CHANGED_POINTS_PAYLOAD_CAP + 1
        start = date.today() - timedelta(days=days + 2)
        end = start + timedelta(days=days - 1)

        result = await _sync(client, asset_id, start, end)
        assert result["inserted_count"] == days, result
        assert result["points_changed"] == days, result
        # Cap enforced: delta must be None even though many points changed.
        assert result.get("changed_points") is None, f"expected None above cap ({CHANGED_POINTS_PAYLOAD_CAP}), " f"got {len(result.get('changed_points') or [])} items"
        print_info(f"points_changed={result['points_changed']} ≥ cap+1 ({CHANGED_POINTS_PAYLOAD_CAP + 1})")
        print_success("Cap honoured: delta omitted above CHANGED_POINTS_PAYLOAD_CAP")


@pytest.mark.asyncio
async def test_delta_at_exact_cap_is_included(test_server):
    """Sync exactly CAP days → delta is returned (boundary = inclusive)."""
    print_section(f"G.12.5 — delta == {CHANGED_POINTS_PAYLOAD_CAP} → included")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset_with_mockprov(client, "G12.5")
        days = CHANGED_POINTS_PAYLOAD_CAP
        start = date.today() - timedelta(days=days + 2)
        end = start + timedelta(days=days - 1)

        result = await _sync(client, asset_id, start, end)
        assert result["inserted_count"] == days, result
        delta = result.get("changed_points")
        assert delta is not None, "expected delta at exact cap, got None"
        assert len(delta) == days, f"expected {days} items, got {len(delta)}"
        print_success(f"Boundary inclusive: delta returned with {len(delta)} items (= cap)")
