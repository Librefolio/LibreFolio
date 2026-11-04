"""
Test Suite: Prices Currency Coherence (I.2 Hard-Reject; X-R71 all or nothing)

Covers Phase 7 Part 3 Blocco G.5 + I.2 (Supersedes E.3), and X-R71.

Contract under test — ``POST /api/v1/assets/prices`` (bulk upsert, manual):

- If any ``FAPricePoint.currency`` differs from its ``asset.currency`` the
  **whole request** fails -- every asset of it, not only the one at fault --
  with HTTP 422 and a coded detail, before anything is written (no
  soft-skip, no partial success)::

      {"code": "price_currency_mismatch", "message": "...",
       "items": [{"asset_id", "expected", "found", "dates"}, ...],
       "count": n}

  ``items``: one entry per asset at fault, in request order (ten at most);
  ``expected`` the asset's currency; ``found`` the other currencies given,
  first seen first; ``dates`` its offending dates, in request order, ten at
  most. ``count``: every offending date of the request.
- When ``FAPricePoint.currency`` is omitted or matches ``asset.currency``
  the upsert proceeds normally.
- An item naming an asset that does not exist is not checked: when nothing
  is at fault its result says ``Asset N not found`` (count 0) and the other
  assets are stored, as before X-R71 (decision D3).

Before X-R71 (I.2): the service checked the currency asset by asset, in
request order, after writing and committing the assets before the one at
fault, and raised ``ValueError``, which the router answered with 400 and a
string detail: a clean asset listed before the offending one stayed stored.
The service side (the refusal after reading the assets only, the numbers, a
provider's ``ValueError``) is pinned by ``services asset-source-guards``.

See ``backend/app/services/assets/price_store.py::bulk_upsert_prices`` and
``backend/app/api/v1/assets/prices.py::upsert_prices_bulk``.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G.5.
"""

from __future__ import annotations

import contextlib
import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets.assets import FAAssetCreateItem, FABulkAssetCreateResponse
from backend.app.schemas.prices import FAPricePoint, FAUpsert
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    """Register + login + persist session cookie on the client."""
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


async def _create_asset(client: httpx.AsyncClient, tag: str, currency: str = "USD", owned: list[int] | None = None) -> int:
    """An asset of the calling test, its name unique across workers; its id added to ``owned`` when given (the list of
    ``_owned_assets``, which deletes them)."""
    item = FAAssetCreateItem(display_name=f"G5 {unique_id(tag)} {uuid.uuid4().hex[:8]}", currency=currency)
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    asset_id = FABulkAssetCreateResponse(**resp.json()).results[0].asset_id
    if owned is not None:
        owned.append(asset_id)
    return asset_id


@contextlib.asynccontextmanager
async def _owned_assets(client: httpx.AsyncClient) -> AsyncIterator[list[int]]:
    """The assets a test creates (``_create_asset(..., owned=…)``), deleted with their prices when it ends, whatever its
    outcome: ``Asset`` and ``PriceHistory`` carry no ``user_id``, every concurrent test sees them."""
    owned: list[int] = []
    try:
        yield owned
    finally:
        if owned:
            await client.delete(f"{API_BASE}/assets", params={"asset_ids": owned}, timeout=TIMEOUT)


def _point(d: date, close: Decimal = Decimal("100.00"), currency: str | None = None) -> FAPricePoint:
    kwargs = {"date": d, "close": close}
    if currency is not None:
        kwargs["currency"] = currency
    return FAPricePoint(**kwargs)


async def _upsert(client: httpx.AsyncClient, asset_id: int, prices: list[FAPricePoint]) -> httpx.Response:
    payload = FAUpsert(asset_id=asset_id, prices=prices)
    return await client.post(
        f"{API_BASE}/assets/prices",
        json=[payload.model_dump(mode="json")],
        timeout=TIMEOUT,
    )


async def _upsert_many(client: httpx.AsyncClient, items: list[FAUpsert]) -> httpx.Response:
    """``POST /assets/prices`` with several assets in ONE request (``_upsert`` posts one)."""
    return await client.post(f"{API_BASE}/assets/prices", json=[item.model_dump(mode="json") for item in items], timeout=TIMEOUT)


async def _query_prices(client: httpx.AsyncClient, asset_id: int, start: date, end: date) -> list[dict]:
    resp = await client.post(
        f"{API_BASE}/assets/prices/query",
        json=[{"asset_id": asset_id, "date_range": {"start": start.isoformat(), "end": end.isoformat()}}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text
    items = resp.json().get("items", [])
    return items[0].get("prices", []) if items else []


async def _stored_days(client: httpx.AsyncClient, asset_id: int) -> list[str]:
    """Every day the asset has a price on, whatever its date: the backup export reads the table, no range and no fill."""
    resp = await client.get(f"{API_BASE}/backup/asset/{asset_id}/prices", params={"format": "json"}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return [row["date"] for row in resp.json()["rows"]]


async def _absent_asset_id(client: httpx.AsyncClient) -> int:
    """An asset id no asset has: far above the lane database's ids (``test_assets_crud``'s sentinel), checked absent."""
    missing_id = 1_000_000_000 + (uuid.uuid4().int % 1_000_000_000)
    probe = await client.get(f"{API_BASE}/assets", params={"asset_ids": [missing_id]}, timeout=TIMEOUT)
    assert probe.status_code == 200 and probe.json() == [], f"precondition: asset {missing_id} must not exist, got {probe.status_code} {probe.text}"
    return missing_id


def _entry(asset_id: int, found: list[str], dates: list[date], expected: str = "USD") -> dict:
    """One ``items`` entry of a ``price_currency_mismatch`` refusal: the asset, its currency, the others given (first seen
    first) and its offending dates (request order)."""
    return {"asset_id": asset_id, "expected": expected, "found": found, "dates": [day.isoformat() for day in dates]}


def _mismatch_detail(resp: httpx.Response, context: str = "") -> dict:
    """The detail of a 422 ``price_currency_mismatch``, its shape checked: the code, a message, ``items`` and ``count``.
    Any other answer fails the test, naming the answer (and ``context``, what the caller saw besides)."""
    assert resp.status_code == 422, f"expected 422 price_currency_mismatch, got {resp.status_code}: {resp.text[:400]}{context}"
    detail = resp.json().get("detail")
    assert isinstance(detail, dict) and set(detail) == {"code", "message", "items", "count"}, detail
    assert detail["code"] == "price_currency_mismatch", detail
    assert isinstance(detail["message"], str) and detail["message"].strip(), detail
    return detail


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_upsert_rejects_single_mismatched_currency(test_server):
    """Single EUR point against USD asset → 422 ``price_currency_mismatch`` naming the asset, both currencies and the date.

    Red before X-R71: 400 with a string detail («Currency mismatch for asset …»).
    """
    print_section("G.5.1 — single mismatch → 422 price_currency_mismatch")
    async with httpx.AsyncClient() as client, _owned_assets(client) as owned:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G5.1", currency="USD", owned=owned)
        d0 = date.today() - timedelta(days=1)

        resp = await _upsert(client, asset_id, [_point(d0, currency="EUR")])
        detail = _mismatch_detail(resp)
        assert detail["items"] == [_entry(asset_id, ["EUR"], [d0])], detail
        assert detail["count"] == 1, detail
        print_success(f"Rejected with 422 {detail['code']}: {detail['items']}")


@pytest.mark.asyncio
async def test_upsert_rejects_mixed_batch_atomically(test_server):
    """One bad point in a batch of 3 → whole batch rejected with 422 ``price_currency_mismatch``, DB stays empty.

    Red before X-R71: 400 with a string detail.
    """
    print_section("G.5.2 — atomic reject on mixed batch")
    async with httpx.AsyncClient() as client, _owned_assets(client) as owned:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G5.2", currency="USD", owned=owned)
        d0 = date.today() - timedelta(days=3)
        points = [
            _point(d0 + timedelta(days=0), currency="USD"),
            _point(d0 + timedelta(days=1), currency="GBP"),  # offender
            _point(d0 + timedelta(days=2), currency="USD"),
        ]

        resp = await _upsert(client, asset_id, points)
        detail = _mismatch_detail(resp)
        assert detail["items"] == [_entry(asset_id, ["GBP"], [d0 + timedelta(days=1)])], detail
        assert detail["count"] == 1, detail

        # No row persisted — atomicity.
        stored = await _query_prices(client, asset_id, d0, d0 + timedelta(days=2))
        assert stored == [], f"expected zero rows after reject, got {len(stored)}"
        print_success("Mixed batch atomically rejected — DB unchanged")


@pytest.mark.asyncio
async def test_upsert_accepts_matching_currency(test_server):
    """Explicit matching ``currency`` (USD) is accepted."""
    print_section("G.5.3 — matching currency accepted")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G5.3", currency="USD")
        d0 = date.today() - timedelta(days=2)

        resp = await _upsert(client, asset_id, [_point(d0, currency="USD")])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["inserted_count"] == 1, body
        print_success("Explicit matching currency accepted (inserted=1)")


@pytest.mark.asyncio
async def test_upsert_accepts_omitted_currency(test_server):
    """``currency=None`` on the payload is accepted and defaults to asset currency."""
    print_section("G.5.4 — omitted currency defaults to asset currency")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G5.4", currency="EUR")
        d0 = date.today() - timedelta(days=2)

        # No currency field — should be inferred as EUR from asset.
        resp = await _upsert(client, asset_id, [_point(d0)])
        assert resp.status_code == 200, resp.text
        assert resp.json()["inserted_count"] == 1
        print_success("Omitted currency accepted (inferred from asset)")


@pytest.mark.asyncio
async def test_upsert_reports_ten_offending_dates_at_most_and_counts_them_all(test_server):
    """G.5.5: 12 bad dates → the asset's entry lists the first 10, in request order; ``count`` says 12.

    Red before X-R71: 400 with a string detail, its date list truncated with «(+ 2 more)».
    """
    print_section("G.5.5 — many offending dates: ten listed, every one counted")
    async with httpx.AsyncClient() as client, _owned_assets(client) as owned:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G5.5", currency="USD", owned=owned)
        d0 = date.today() - timedelta(days=15)
        points = [_point(d0 + timedelta(days=i), currency="CHF") for i in range(12)]

        resp = await _upsert(client, asset_id, points)
        detail = _mismatch_detail(resp)
        assert detail["items"] == [_entry(asset_id, ["CHF"], [point.date for point in points[:10]])], detail
        assert detail["count"] == 12, detail
        print_success("Large mismatch batch: 10 dates listed, 12 counted")


# ============================================================================
# X-R71: a mismatch in any asset refuses the whole upload, before any write
# ============================================================================


@pytest.mark.asyncio
async def test_a_mismatch_in_one_asset_refuses_the_whole_upload_and_writes_no_asset(test_server):
    """X-R71: A clean, B with a price in EUR, C clean, in ONE request: 422 naming B, and no asset written.

    Contract: 422 ``{"code": "price_currency_mismatch", "message", "items": [{"asset_id": B, "expected": "USD", "found":
    ["EUR"], "dates": [B's EUR day]}], "count": 1}``; no row for A, B or C.
    Red before X-R71: 400 with a string detail, and A's two prices stored: the upsert committed A before reaching B.
    """
    print_section("X-R71 — one asset at fault refuses the whole upload")
    async with httpx.AsyncClient() as client, _owned_assets(client) as owned:
        await create_user_and_login(client)
        a, b, c = [await _create_asset(client, f"XR71.{name}", currency="USD", owned=owned) for name in "ABC"]
        assert [await _stored_days(client, asset_id) for asset_id in (a, b, c)] == [[], [], []], "barrier: a new asset holds prices"
        d0 = date.today() - timedelta(days=5)
        eur_day = d0 + timedelta(days=1)

        resp = await _upsert_many(
            client,
            [
                FAUpsert(asset_id=a, prices=[_point(d0, currency="USD"), _point(d0 + timedelta(days=1))]),
                FAUpsert(asset_id=b, prices=[_point(d0), _point(eur_day, currency="EUR")]),
                FAUpsert(asset_id=c, prices=[_point(d0, currency="USD")]),
            ],
        )
        stored = {name: await _stored_days(client, asset_id) for name, asset_id in (("A", a), ("B", b), ("C", c))}

        detail = _mismatch_detail(resp, f"; stored after the answer: {stored}")
        assert detail["items"] == [_entry(b, ["EUR"], [eur_day])], detail
        assert detail["count"] == 1, detail
        assert stored == {"A": [], "B": [], "C": []}, f"the refused upload wrote prices: {stored}"
        print_success(f"422 {detail['code']} naming asset {b}; nothing stored for A, B or C")


@pytest.mark.asyncio
async def test_every_asset_at_fault_is_named_in_request_order(test_server):
    """X-R71: A at fault (EUR), B clean, C at fault (GBP, then CHF): one refusal names A then C; nothing is written.

    Contract: 422 ``price_currency_mismatch``; ``items`` A then C, in request order; C's ``found`` ``["GBP", "CHF"]``,
    first seen first (sorted would be CHF, GBP); each ``dates`` the asset's offending days in request order; ``count`` 3;
    no row for A, B or C.
    Red before X-R71: 400 with a string detail naming A alone: the first asset at fault stops the upsert.
    """
    print_section("X-R71 — every asset at fault named, in request order")
    async with httpx.AsyncClient() as client, _owned_assets(client) as owned:
        await create_user_and_login(client)
        a, b, c = [await _create_asset(client, f"XR71.{name}", currency="USD", owned=owned) for name in "ABC"]
        days = [date.today() - timedelta(days=5) + timedelta(days=n) for n in range(3)]

        resp = await _upsert_many(
            client,
            [
                FAUpsert(asset_id=a, prices=[_point(days[0]), _point(days[1], currency="EUR")]),
                FAUpsert(asset_id=b, prices=[_point(days[0], currency="USD"), _point(days[1])]),
                FAUpsert(asset_id=c, prices=[_point(days[0], currency="GBP"), _point(days[1], currency="USD"), _point(days[2], currency="CHF")]),
            ],
        )
        stored = {name: await _stored_days(client, asset_id) for name, asset_id in (("A", a), ("B", b), ("C", c))}

        detail = _mismatch_detail(resp, f"; stored after the answer: {stored}")
        assert detail["items"] == [_entry(a, ["EUR"], [days[1]]), _entry(c, ["GBP", "CHF"], [days[0], days[2]])], detail
        assert detail["count"] == 3, detail
        assert stored == {"A": [], "B": [], "C": []}, f"the refused upload wrote prices: {stored}"
        print_success(f"422 {detail['code']}: assets {a} and {c} named in request order, {detail['count']} dates")


@pytest.mark.asyncio
async def test_an_unknown_asset_between_two_clean_ones_is_reported_and_the_others_stored(test_server):
    """X-R71 guard (decision D3), green before the fix and after: nothing at fault, an asset id no asset has between two
    clean assets.

    Contract: 200; the results in request order, the unknown asset's ``count`` 0 and «Asset N not found»; the two clean
    assets stored, every day of theirs.
    """
    print_section("X-R71 guard — an unknown asset among clean ones")
    async with httpx.AsyncClient() as client, _owned_assets(client) as owned:
        await create_user_and_login(client)
        a = await _create_asset(client, "XR71.A", currency="USD", owned=owned)
        c = await _create_asset(client, "XR71.C", currency="USD", owned=owned)
        missing_id = await _absent_asset_id(client)
        d0 = date.today() - timedelta(days=5)

        resp = await _upsert_many(
            client,
            [
                FAUpsert(asset_id=a, prices=[_point(d0, currency="USD"), _point(d0 + timedelta(days=1))]),
                FAUpsert(asset_id=missing_id, prices=[_point(d0)]),
                FAUpsert(asset_id=c, prices=[_point(d0)]),
            ],
        )
        assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:400]}"
        results = resp.json()["results"]
        assert [row["asset_id"] for row in results] == [a, missing_id, c], results
        by_asset = {row["asset_id"]: row for row in results}
        assert (by_asset[missing_id]["count"], by_asset[missing_id]["message"]) == (0, f"Asset {missing_id} not found"), results
        assert (by_asset[a]["count"], by_asset[c]["count"]) == (2, 1), results
        assert await _stored_days(client, a) == [d0.isoformat(), (d0 + timedelta(days=1)).isoformat()]
        assert await _stored_days(client, c) == [d0.isoformat()]
        print_success(f"200: asset {missing_id} not found, assets {a} and {c} stored")
