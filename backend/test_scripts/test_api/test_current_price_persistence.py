"""
Test Suite: F.2/F.3 current-price persistence (API integration)

Covers Phase 7 Part 3 Blocco F.2 (bootstrap new-row) and F.3 (intra-day
extend) end-to-end via the ``POST /api/v1/assets/prices/current`` endpoint.

Contract under test (documented in devWiki
``wiki/concepts/prices-current-side-effect.md``):

- ``/assets/prices/current`` is **not read-only**: for every successful
  provider fetch whose ``as_of_date == today``, the endpoint persists today's
  OHLC row in ``PriceHistory`` via:
  * F.2 bootstrap  — new row: ``open=high=low=close=new_close``, ``volume=None``.
  * F.3 extend     — existing row: ``low`` min-widens, ``high`` max-widens,
    ``open`` stays once set, ``close`` is overwritten with the latest tick.
- DB-fallback fetches (``source == "db:last_known"``) are NOT persisted —
  they are stale reads, not fresh quotes.

Provider used: ``mockprov`` (in-process test-only provider that returns a
fixed ``100.00 USD`` as of today). Deterministic, no network.

Cache reset: ``_asset_current_cache`` has a 2-min TTL; each test invalidates
the cache for the used ``(provider_code, identifier, identifier_type)``
key before calling the endpoint, so consecutive tests don't pick up each
other's results.

Related plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md``
              §G.6c (G-batch1).
Related spec: ``backend/app/services/asset_source.py::get_current_prices_bulk``
              (L2756+, F.2/F.3 persist block L2877+).
"""

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.models import PriceHistory, ProviderInputType
from backend.app.db.session import get_async_engine
from backend.app.schemas.assets import FAAssetCreateItem, FABulkAssetCreateResponse
from backend.app.schemas.prices import FAPricePoint, FAUpsert
from backend.app.schemas.provider import FAProviderAssignmentItem
from backend.app.services.asset_source import AssetSourceManager, _asset_current_cache
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    """Create a unique test user, register+login, persist session cookie."""
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
    assert resp.status_code == 201, f"register failed: {resp.status_code} {resp.text}"
    login_resp = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    assert login_resp.status_code == 200
    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


def _invalidate_current_cache(identifier: str) -> None:
    """Wipe the ``_asset_current_cache`` to guarantee a fresh provider fetch.

    The endpoint's provider branch caches ``FACurrentValue`` by
    ``(provider_code, identifier, str(identifier_type))``; a stale cache
    between tests would skip the provider call and also skip F.2/F.3
    persistence. ``NamedCache`` (theine wrapper) does not expose key
    iteration, so we clear the whole cache: safe in tests because each
    test uses a freshly-created asset/identifier.
    """
    del identifier  # currently unused — kept for API clarity
    _asset_current_cache.clear()


async def _create_asset_with_mockprov(client: httpx.AsyncClient, tag: str, identifier: str) -> int:
    """Create an asset via API + assign mockprov via helper direct session.

    Provider assignment happens through ``AssetSourceManager.bulk_assign_providers``
    (the existing helper used by ``test_asset_source_refresh.py``) since the
    API endpoint validates identifier types strictly and mockprov accepts
    AUTO_GENERATED / TICKER.
    """
    item = FAAssetCreateItem(display_name=f"F23 integ {unique_id(tag)}", currency="USD")
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), f"create asset failed: {resp.status_code} {resp.text}"
    data = FABulkAssetCreateResponse(**resp.json())
    asset_id = data.results[0].asset_id

    # Assign mockprov directly via service (bypass API to keep identifier
    # AUTO_GENERATED which mockprov supports).
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        await AssetSourceManager.bulk_assign_providers(
            [
                FAProviderAssignmentItem(
                    asset_id=asset_id,
                    provider_code="mockprov",
                    identifier=identifier,
                    identifier_type=ProviderInputType.AUTO_GENERATED,
                    provider_params={},
                )
            ],
            session,
        )
    return asset_id


async def _fetch_today_row(asset_id: int) -> PriceHistory | None:
    """Read the PriceHistory row for ``asset_id`` at today's date directly."""
    today = date.today()
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as session:
        stmt = select(PriceHistory).where(and_(PriceHistory.asset_id == asset_id, PriceHistory.date == today))
        row = (await session.execute(stmt)).scalar_one_or_none()
    return row


async def _call_current_prices(client: httpx.AsyncClient, asset_ids: list[int]) -> dict:
    resp = await client.post(f"{API_BASE}/assets/prices/current", json=asset_ids, timeout=TIMEOUT)
    assert resp.status_code == 200, f"/current failed: {resp.status_code} {resp.text}"
    return resp.json()


# ===========================================================================
# G.6c.1 — F.2 bootstrap: provider fresh quote creates today's OHLC row
# ===========================================================================
@pytest.mark.asyncio
async def test_current_price_bootstraps_today_ohlc_on_empty_db(test_server):
    """Asset w/ mockprov, no PriceHistory rows. Call /current -> F.2 bootstrap.

    Expected after call:
    - PriceHistory has exactly 1 row for today.
    - open == high == low == close == 100 (mockprov fixed value).
    - volume is None.
    - currency == USD.
    - source_plugin_key starts with "provider:".
    """
    print_section("G.6c.1 - F.2 bootstrap creates today's OHLC row")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        ident = f"G6C1_{unique_id('MOCK')}"
        asset_id = await _create_asset_with_mockprov(client, "G6C1", ident)
        _invalidate_current_cache(ident)

        body = await _call_current_prices(client, [asset_id])
        item = body["results"][0]
        assert item.get("error") is None, f"unexpected error in response: {item}"
        assert item["as_of_date"] == date.today().isoformat()

        row = await _fetch_today_row(asset_id)
        assert row is not None, "PriceHistory must have a row for today after F.2 bootstrap"
        assert row.open == Decimal("100.00"), f"open bootstrap mismatch: {row.open}"
        assert row.high == Decimal("100.00"), f"high bootstrap mismatch: {row.high}"
        assert row.low == Decimal("100.00"), f"low bootstrap mismatch: {row.low}"
        assert row.close == Decimal("100.00"), f"close bootstrap mismatch: {row.close}"
        assert row.volume is None, f"volume should be None on bootstrap, got {row.volume}"
        assert row.currency == "USD"
        assert row.source_plugin_key and row.source_plugin_key.startswith("provider:"), f"source_plugin_key should be 'provider:...', got {row.source_plugin_key}"
        print_success(f"F.2 bootstrap OK: open=high=low=close=100, volume=None, source={row.source_plugin_key}")


# ===========================================================================
# G.6c.2 — F.3 intra-day extend: tick ABOVE current high widens it
# ===========================================================================
@pytest.mark.asyncio
async def test_current_price_extends_high_when_tick_above(test_server):
    """Pre-seed today's row with high=50, low=50, close=50.

    Mockprov returns 100 -> F.3 should widen high to 100 while keeping low=50
    and setting close=100. ``open`` stays at whatever was pre-seeded.
    """
    print_section("G.6c.2 - F.3 extends high upward on intra-day tick")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        ident = f"G6C2_{unique_id('MOCK')}"
        asset_id = await _create_asset_with_mockprov(client, "G6C2", ident)
        _invalidate_current_cache(ident)

        # Pre-seed today's row via upsert API — open=48, high=50, low=50, close=50.
        today = date.today()
        upsert_payload = FAUpsert(
            asset_id=asset_id,
            prices=[FAPricePoint(date=today, open=Decimal("48"), high=Decimal("50"), low=Decimal("50"), close=Decimal("50"))],
        )
        ur = await client.post(f"{API_BASE}/assets/prices", json=[upsert_payload.model_dump(mode="json")], timeout=TIMEOUT)
        assert ur.status_code == 200

        await _call_current_prices(client, [asset_id])

        row = await _fetch_today_row(asset_id)
        assert row is not None
        assert row.low == Decimal("50"), f"low should stay at 50 (mockprov=100 > 50), got {row.low}"
        assert row.high == Decimal("100.00"), f"high should widen to 100, got {row.high}"
        assert row.close == Decimal("100.00"), f"close should be overwritten to latest tick (100), got {row.close}"
        assert row.open == Decimal("48"), f"open should stay at 48 (already set), got {row.open}"
        print_success("F.3 high widened 50->100, close overwritten 50->100, open/low preserved")


# ===========================================================================
# G.6c.3 — F.3 intra-day extend: tick BELOW current low widens it
# ===========================================================================
@pytest.mark.asyncio
async def test_current_price_extends_low_when_tick_below(test_server):
    """Pre-seed today's row with high=150, low=120, close=140.

    Mockprov returns 100 -> F.3 should widen low to 100 while keeping high=150
    and overwriting close to 100.
    """
    print_section("G.6c.3 - F.3 extends low downward on intra-day tick")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        ident = f"G6C3_{unique_id('MOCK')}"
        asset_id = await _create_asset_with_mockprov(client, "G6C3", ident)
        _invalidate_current_cache(ident)

        today = date.today()
        upsert_payload = FAUpsert(
            asset_id=asset_id,
            prices=[FAPricePoint(date=today, open=Decimal("130"), high=Decimal("150"), low=Decimal("120"), close=Decimal("140"))],
        )
        await client.post(f"{API_BASE}/assets/prices", json=[upsert_payload.model_dump(mode="json")], timeout=TIMEOUT)

        await _call_current_prices(client, [asset_id])

        row = await _fetch_today_row(asset_id)
        assert row is not None
        assert row.low == Decimal("100.00"), f"low should widen down to 100, got {row.low}"
        assert row.high == Decimal("150"), f"high should stay at 150 (mockprov=100 inside), got {row.high}"
        assert row.close == Decimal("100.00"), f"close should be overwritten to 100, got {row.close}"
        assert row.open == Decimal("130"), f"open should stay at 130, got {row.open}"
        print_success("F.3 low widened 120->100, close overwritten 140->100, open/high preserved")


# ===========================================================================
# G.6c.4 — F.3 tick INSIDE bounds only updates close (no OHLC widen)
# ===========================================================================
@pytest.mark.asyncio
async def test_current_price_inside_bounds_only_updates_close(test_server):
    """Pre-seed today with high=200, low=50, close=99.

    Mockprov returns 100 (inside [50..200]) -> F.3 should NOT widen anything.
    Only ``close`` must flip from 99 to 100.
    """
    print_section("G.6c.4 - F.3 tick inside bounds updates close only")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        ident = f"G6C4_{unique_id('MOCK')}"
        asset_id = await _create_asset_with_mockprov(client, "G6C4", ident)
        _invalidate_current_cache(ident)

        today = date.today()
        upsert_payload = FAUpsert(
            asset_id=asset_id,
            prices=[FAPricePoint(date=today, open=Decimal("75"), high=Decimal("200"), low=Decimal("50"), close=Decimal("99"))],
        )
        await client.post(f"{API_BASE}/assets/prices", json=[upsert_payload.model_dump(mode="json")], timeout=TIMEOUT)

        await _call_current_prices(client, [asset_id])

        row = await _fetch_today_row(asset_id)
        assert row is not None
        assert row.low == Decimal("50"), f"low must stay 50, got {row.low}"
        assert row.high == Decimal("200"), f"high must stay 200, got {row.high}"
        assert row.open == Decimal("75"), f"open must stay 75, got {row.open}"
        assert row.close == Decimal("100.00"), f"close must flip 99->100, got {row.close}"
        print_success("F.3 inside-bounds: only close updated, OHLC bounds untouched")


# ===========================================================================
# G.6c.5 — F.2/F.3 NOT triggered when provider fallback (db:last_known)
# ===========================================================================
@pytest.mark.asyncio
async def test_current_price_fallback_source_does_not_persist(test_server):
    """Asset w/o provider + PriceHistory pre-seeded on YESTERDAY.

    The endpoint falls back to ``db:last_known`` (yesterday's row). It must
    NOT persist a today's row (the fallback is stale data, not a fresh
    quote). Invariant documented in ``get_current_prices_bulk`` docstring.
    """
    print_section("G.6c.5 - db:last_known fallback must NOT persist today")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Create asset WITHOUT provider assignment.
        item = FAAssetCreateItem(display_name=f"F23 nofetch {unique_id('NOPROV')}", currency="USD")
        cr = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
        asset_id = FABulkAssetCreateResponse(**cr.json()).results[0].asset_id

        yesterday = date.today() - timedelta(days=1)
        upsert = FAUpsert(
            asset_id=asset_id,
            prices=[FAPricePoint(date=yesterday, open=Decimal("90"), high=Decimal("95"), low=Decimal("88"), close=Decimal("92"))],
        )
        await client.post(f"{API_BASE}/assets/prices", json=[upsert.model_dump(mode="json")], timeout=TIMEOUT)

        body = await _call_current_prices(client, [asset_id])
        item = body["results"][0]
        assert item["source"] == "db:last_known", f"expected source=db:last_known, got {item.get('source')}"
        assert item["as_of_date"] == yesterday.isoformat()

        # The key invariant: there must be NO row for today.
        today_row = await _fetch_today_row(asset_id)
        assert today_row is None, f"db:last_known fallback must not bootstrap a today's row (would fabricate data); found: {today_row}"
        print_success("fallback source=db:last_known correctly did NOT persist a today's row")
