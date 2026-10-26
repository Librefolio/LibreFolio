"""
Test Suite: Asset Currency Change Flow (N68, lot X5-3, "policy A")

Contract under test — ``PATCH /api/v1/assets`` with the ``currency`` field.

**Before N68** (Policy D, R3-3 / I-bis #7): changing the currency of an asset that owned any price or event was refused
with the token ``CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|prices=N|...`` (HTTP 409 when the whole batch was blocked), and
the front end then called ``POST /assets/{id}/market-data/wipe`` and PATCHed again. That wipe deleted the SPLITs too and
was itself refused while a SPLIT had costless incoming adjustments (X-R48).

**N68** (decided by the developer on 19/10, defaults confirmed on 24/10):

1. **No block.** The currency PATCH always succeeds, HTTP 200, ``success`` true, whatever the asset owns. The token is
   never produced and the all-blocked 409 does not exist.
2. In the SAME call it deletes the asset's prices and every NON-SPLIT event, sets ``transactions.asset_event_id`` to NULL
   on the transactions linked to those events (the transactions stay), and keeps every SPLIT event with the transactions
   linked to it: an ADJUSTMENT without a cost stays linked to its SPLIT, so the position math is unchanged and no
   MISSING_COST_BASIS appears.
3. The same currency, or an asset with nothing to lose, behaves as before. A mixed batch (an asset with market data, one
   without, one not found) keeps 200 with partial success.

Tests:

- N68.1 prices + events + PATCH → 200, success, no token, currency changed, prices and events gone (provider-less asset).
- N68.2 SPLIT + costless ADJUSTMENT + dividend + price → SPLIT and ADJUSTMENT stay linked, position math unchanged.
- N68.3 dividend- and interest-linked transactions are unlinked, not deleted, every other field as before.
- N68.4 an asset that has only events (no price) changes currency too.
- N68.5 same-currency PATCH leaves prices and events alone.
- N68.6 mixed batch → 200, partial success, nothing blocked.
- N68.7 an asset nobody patched keeps its market data.
- N68.8 an asset with nothing to lose changes currency (as before).

Isolation: each test creates its own user, broker(s) and asset(s) under a unique name and addresses them by id; whatever
it creates through the API is dropped at the end (brokers with their transactions, then assets with their events).
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
import pytest_asyncio

from backend.app.config import get_settings
from backend.app.schemas.assets.assets import (
    FAAssetCreateItem,
    FAAssetPatchItem,
    FABulkAssetCreateResponse,
)
from backend.app.schemas.prices import FAPricePoint, FAUpsert
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
OLD_TOKEN = "CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA"
WIDE_RANGE = {"start": "2000-01-01", "end": (date.today() + timedelta(days=365)).isoformat()}


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


class _Owned:
    """What a test created through the API, dropped in FK-safe order at the end (brokers force-deleted with their
    transactions first, then the assets with their events)."""

    def __init__(self) -> None:
        self.asset_ids: list[int] = []
        self.broker_ids: list[int] = []

    async def drop(self, client: httpx.AsyncClient) -> list[str]:
        """Never raises: what could not be removed is returned."""
        problems: list[str] = []
        for broker_id in self.broker_ids:
            try:
                resp = await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
                done = resp.status_code == 200 and any(r.get("id") == broker_id and r.get("success") for r in resp.json().get("results", []))
                if not done:
                    problems.append(f"broker {broker_id}: HTTP {resp.status_code} {resp.text}")
            except Exception as exc:  # noqa: BLE001 — cleanup reports instead of masking the test's own outcome
                problems.append(f"broker {broker_id}: {exc!r}")
        if self.asset_ids:
            try:
                resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": self.asset_ids}, timeout=TIMEOUT)
                deleted = {r["asset_id"] for r in resp.json().get("results", []) if r.get("success")} if resp.status_code == 200 else set()
                problems += [f"asset {asset_id}: HTTP {resp.status_code} {resp.text}" for asset_id in self.asset_ids if asset_id not in deleted]
            except Exception as exc:  # noqa: BLE001
                problems.append(f"assets {self.asset_ids}: {exc!r}")
        return problems


@pytest_asyncio.fixture
async def env(test_server):
    """A logged-in client and the collector of what the test creates; dropped after the test."""
    owned = _Owned()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        yield client, owned
        problems = await owned.drop(client)
    assert not problems, problems


async def _create_asset(client: httpx.AsyncClient, owned: _Owned, tag: str, currency: str = "USD") -> int:
    item = FAAssetCreateItem(display_name=f"N68 {unique_id(tag)}", currency=currency)
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    asset_id = FABulkAssetCreateResponse(**resp.json()).results[0].asset_id
    owned.asset_ids.append(asset_id)
    return asset_id


async def _create_broker(client: httpx.AsyncClient, owned: _Owned) -> int:
    name = f"N68 Broker {unique_id('B')}"
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": name, "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["results"] if r["name"] == name)
    assert row["success"] is True, row
    owned.broker_ids.append(row["broker_id"])
    return row["broker_id"]


async def _seed_prices(client: httpx.AsyncClient, asset_id: int, start: date, count: int) -> None:
    points = [FAPricePoint(date=start + timedelta(days=i), close=Decimal("100.00") + Decimal(i)) for i in range(count)]
    payload = FAUpsert(asset_id=asset_id, prices=points)
    resp = await client.post(f"{API_BASE}/assets/prices", json=[payload.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text


async def _seed_event(client: httpx.AsyncClient, asset_id: int, day: date, kind: str, amount: str, currency: str) -> int:
    """One manual event on ``day``; its id, read back from the API."""
    resp = await client.post(
        f"{API_BASE}/assets/events",
        json=[{"asset_id": asset_id, "events": [{"date": day.isoformat(), "type": kind, "value": {"code": currency, "amount": amount}}]}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text
    matches = [e["id"] for e in await _events_of(client, asset_id) if e["date"] == day.isoformat() and e["type"] == kind]
    assert len(matches) == 1, f"expected exactly one {kind} on {day} for asset {asset_id}, got {matches}"
    return matches[0]


async def _events_of(client: httpx.AsyncClient, asset_id: int) -> list[dict[str, Any]]:
    resp = await client.post(f"{API_BASE}/assets/events/query", json=[{"asset_id": asset_id, "date_range": WIDE_RANGE}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return next(item for item in resp.json()["items"] if item["asset_id"] == asset_id)["events"]


async def _prices_of(client: httpx.AsyncClient, asset_id: int, start: date, count: int) -> list[dict[str, Any]]:
    """The prices stored on the ``count`` days from ``start``: exactly the seeded range, since a wider query is filled
    forward by the API and would count days that hold no stored price."""
    date_range = {"start": start.isoformat(), "end": (start + timedelta(days=count - 1)).isoformat()}
    resp = await client.post(f"{API_BASE}/assets/prices/query", json=[{"asset_id": asset_id, "date_range": date_range}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return next(item for item in resp.json()["items"] if item["asset_id"] == asset_id)["prices"]


async def _commit(client: httpx.AsyncClient, creates: list[dict]) -> list[int]:
    """Commit ``creates``; the new ids in request order."""
    resp = await client.post(f"{API_BASE}/transactions/commit", json={"creates": creates}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["committed"] is True, body["issues"]
    ids = {r["index"]: r["ids"][0] for r in body["results"] if r["operation"] == "create"}
    return [ids[i] for i in range(len(creates))]


async def _tx_rows(client: httpx.AsyncClient, ids: list[int]) -> dict[int, dict[str, Any]]:
    resp = await client.get(f"{API_BASE}/transactions", params={"ids": ids}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    rows = {tx["id"]: tx for tx in resp.json()}
    assert set(rows) == set(ids), f"transactions {sorted(set(ids) - set(rows))} not found among {sorted(rows)}"
    return rows


async def _wac_pool(client: httpx.AsyncClient, broker_id: int, asset_id: int) -> str:
    """The pool quantities of the position's WAC series as text (nothing else: the cash is in another currency), and
    the whole answer must not mention a missing cost basis."""
    resp = await client.post(f"{API_BASE}/portfolio/wac", json={"queries": [{"broker_id": broker_id, "asset_id": asset_id}]}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    assert "MISSING_COST_BASIS" not in resp.text, resp.text
    series = resp.json()["results"][0]["series"]
    return ",".join(str(Decimal(point["pool_qty"])) for point in series)


async def _patch_currency(client: httpx.AsyncClient, items: list[FAAssetPatchItem]) -> httpx.Response:
    return await client.patch(
        f"{API_BASE}/assets",
        json=[it.model_dump(mode="json", exclude_none=True) for it in items],
        timeout=TIMEOUT,
    )


async def _currency(client: httpx.AsyncClient, asset_id: int) -> str:
    resp = await client.get(f"{API_BASE}/assets/all", timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    for a in resp.json():
        if a["id"] == asset_id:
            return a["currency"]
    raise AssertionError(f"asset {asset_id} not in /assets/all")


def _assert_all_patched(resp: httpx.Response, asset_ids: list[int]) -> dict[int, dict]:
    """200, every asset of ``asset_ids`` succeeded and no result carries the block's token."""
    assert resp.status_code == 200, f"expected 200, got {resp.status_code}: {resp.text}. Red today (N68): 409 when every item is blocked by its market data"
    assert OLD_TOKEN not in resp.text, f"the block's token is never produced any more: {resp.text}"
    per_asset = {r["asset_id"]: r for r in resp.json()["results"]}
    for asset_id in asset_ids:
        assert per_asset[asset_id]["success"] is True, f"asset {asset_id}: {per_asset[asset_id]}. Red today (N68): refused with the token when the asset owns market data"
    return per_asset


def _without_updated_at(row: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in row.items() if k != "updated_at"}


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_currency_change_passes_with_prices_and_events(env):
    """N68.1 — a provider-less asset with prices and events: PATCH currency → 200, success, no token; currency changed,
    prices and events gone (no SPLIT here: nothing is kept)."""
    print_section("N68.1 — currency change with prices + events passes")
    client, owned = env
    asset_id = await _create_asset(client, owned, "N68.1", currency="USD")
    start = date.today() - timedelta(days=10)
    await _seed_prices(client, asset_id, start, 3)
    await _seed_event(client, asset_id, start, "DIVIDEND", "0.25", "USD")
    await _seed_event(client, asset_id, start + timedelta(days=1), "INTEREST", "0.50", "USD")
    assert len(await _prices_of(client, asset_id, start, 3)) == 3, "precondition: three prices"
    assert len(await _events_of(client, asset_id)) == 2, "precondition: two events"

    resp = await _patch_currency(client, [FAAssetPatchItem(asset_id=asset_id, currency="EUR")])

    body = resp.json() if resp.status_code == 200 else {}
    per_asset = _assert_all_patched(resp, [asset_id])
    assert body["success_count"] == 1, body
    assert any(f["info"] == "currency" for f in per_asset[asset_id]["updated_fields"]), per_asset[asset_id]
    assert await _currency(client, asset_id) == "EUR"
    assert await _prices_of(client, asset_id, start, 3) == [], "the prices are gone, in the same call"
    assert await _events_of(client, asset_id) == [], "the non-split events are gone, in the same call"
    print_success("PATCH with prices and events: 200, success, market data removed, currency EUR")


@pytest.mark.asyncio
async def test_currency_change_keeps_the_split_and_its_costless_adjustment_linked(env):
    """N68.2 — BUY + SPLIT + costless ADJUSTMENT linked to it + dividend (with its transaction) + price: after the PATCH the
    SPLIT is still there, the ADJUSTMENT is untouched and still linked, the dividend event is gone, and the position's
    pool quantities are the same as before (no MISSING_COST_BASIS)."""
    print_section("N68.2 — SPLIT and its costless adjustment survive")
    client, owned = env
    asset_id = await _create_asset(client, owned, "N68.2", currency="EUR")
    broker_id = await _create_broker(client, owned)
    await _seed_prices(client, asset_id, date(2026, 1, 10), 2)
    split_id = await _seed_event(client, asset_id, date(2026, 2, 1), "SPLIT", "2", "EUR")
    dividend_id = await _seed_event(client, asset_id, date(2026, 2, 10), "DIVIDEND", "1", "EUR")
    buy_id, adjustment_id, dividend_tx_id = await _commit(
        client,
        [
            {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-15", "quantity": "15", "cash": {"code": "EUR", "amount": "-1500"}},
            {"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": "2026-02-01", "quantity": "15", "asset_event_id": split_id, "cost_basis_mode": "auto"},
            {"broker_id": broker_id, "asset_id": asset_id, "type": "DIVIDEND", "date": "2026-02-10", "cash": {"code": "EUR", "amount": "15"}, "asset_event_id": dividend_id},
        ],
    )
    rows_before = await _tx_rows(client, [buy_id, adjustment_id, dividend_tx_id])
    assert rows_before[adjustment_id]["asset_event_id"] == split_id and rows_before[dividend_tx_id]["asset_event_id"] == dividend_id, "precondition: the links"
    pool_before = await _wac_pool(client, broker_id, asset_id)
    split_before = next(e for e in await _events_of(client, asset_id) if e["id"] == split_id)

    resp = await _patch_currency(client, [FAAssetPatchItem(asset_id=asset_id, currency="USD")])

    _assert_all_patched(resp, [asset_id])
    assert await _currency(client, asset_id) == "USD"
    events_after = await _events_of(client, asset_id)
    assert [e["id"] for e in events_after] == [split_id], f"only the SPLIT stays: {events_after}"
    assert next(e for e in events_after if e["id"] == split_id) == split_before, "the SPLIT is untouched"
    assert await _prices_of(client, asset_id, date(2026, 1, 10), 2) == [], "the prices are gone"
    rows_after = await _tx_rows(client, [buy_id, adjustment_id, dividend_tx_id])
    assert rows_after[adjustment_id] == rows_before[adjustment_id], "the SPLIT's ADJUSTMENT is untouched, link included"
    assert rows_after[buy_id] == rows_before[buy_id], "the BUY is untouched"
    assert rows_after[dividend_tx_id]["asset_event_id"] is None, "the dividend's transaction is unlinked"
    assert _without_updated_at({**rows_after[dividend_tx_id], "asset_event_id": dividend_id}) == _without_updated_at(rows_before[dividend_tx_id]), "...and nothing else of it changed"
    assert await _wac_pool(client, broker_id, asset_id) == pool_before, "the position math is unchanged"
    print_success("SPLIT and costless ADJUSTMENT kept and linked, dividend unlinked, position unchanged")


@pytest.mark.asyncio
async def test_currency_change_unlinks_dividend_and_interest_transactions(env):
    """N68.3 — transactions linked to a DIVIDEND and to an INTEREST event survive the PATCH, unlinked, every other field as
    before; they are still found by the broker's listing."""
    print_section("N68.3 — event-linked transactions are unlinked, not deleted")
    client, owned = env
    asset_id = await _create_asset(client, owned, "N68.3", currency="USD")
    broker_id = await _create_broker(client, owned)
    dividend_id = await _seed_event(client, asset_id, date(2026, 3, 1), "DIVIDEND", "1", "USD")
    interest_id = await _seed_event(client, asset_id, date(2026, 3, 2), "INTEREST", "2", "USD")
    dividend_tx, interest_tx = await _commit(
        client,
        [
            {"broker_id": broker_id, "asset_id": asset_id, "type": "DIVIDEND", "date": "2026-03-01", "cash": {"code": "USD", "amount": "10"}, "asset_event_id": dividend_id},
            {"broker_id": broker_id, "asset_id": asset_id, "type": "INTEREST", "date": "2026-03-02", "cash": {"code": "USD", "amount": "20"}, "asset_event_id": interest_id},
        ],
    )
    before = await _tx_rows(client, [dividend_tx, interest_tx])
    assert (before[dividend_tx]["asset_event_id"], before[interest_tx]["asset_event_id"]) == (dividend_id, interest_id), "precondition: the links"

    resp = await _patch_currency(client, [FAAssetPatchItem(asset_id=asset_id, currency="EUR")])

    _assert_all_patched(resp, [asset_id])
    after = await _tx_rows(client, [dividend_tx, interest_tx])
    for tx_id, event_id in ((dividend_tx, dividend_id), (interest_tx, interest_id)):
        assert after[tx_id]["asset_event_id"] is None, f"transaction {tx_id} must be unlinked: {after[tx_id]}"
        assert _without_updated_at({**after[tx_id], "asset_event_id": event_id}) == _without_updated_at(before[tx_id]), f"transaction {tx_id} changed beyond its link"
    assert await _events_of(client, asset_id) == [], "both events are gone"
    print_success("dividend and interest transactions kept, unlinked")


@pytest.mark.asyncio
async def test_currency_change_with_events_only_passes(env):
    """N68.4 — an asset that owns only events (no price) is not blocked either."""
    print_section("N68.4 — events only")
    client, owned = env
    asset_id = await _create_asset(client, owned, "N68.4", currency="USD")
    await _seed_event(client, asset_id, date(2026, 4, 1), "DIVIDEND", "1", "USD")

    resp = await _patch_currency(client, [FAAssetPatchItem(asset_id=asset_id, currency="EUR")])

    _assert_all_patched(resp, [asset_id])
    assert await _currency(client, asset_id) == "EUR"
    assert await _events_of(client, asset_id) == []
    print_success("events-only asset changed currency")


@pytest.mark.asyncio
async def test_same_currency_patch_leaves_market_data_untouched(env):
    """N68.5 — PATCH currency == existing currency is a no-op for the market data: prices and events are still there."""
    print_section("N68.5 — same-currency PATCH untouched")
    client, owned = env
    asset_id = await _create_asset(client, owned, "N68.5", currency="USD")
    start = date.today() - timedelta(days=6)
    await _seed_prices(client, asset_id, start, 2)
    event_id = await _seed_event(client, asset_id, start, "DIVIDEND", "1", "USD")

    resp = await _patch_currency(client, [FAAssetPatchItem(asset_id=asset_id, currency="USD")])

    assert resp.status_code == 200, resp.text
    assert resp.json()["results"][0]["success"] is True, resp.text
    assert len(await _prices_of(client, asset_id, start, 2)) == 2, "the prices are still there"
    assert [e["id"] for e in await _events_of(client, asset_id)] == [event_id], "the event is still there"
    assert await _currency(client, asset_id) == "USD"
    print_success("same currency: nothing removed")


@pytest.mark.asyncio
async def test_mixed_batch_keeps_200_with_partial_success(env):
    """N68.6 — one asset with market data, one without, one that does not exist → 200; the two real assets succeed, the
    missing one fails by itself (a message, no token)."""
    print_section("N68.6 — mixed batch stays 200, partial success")
    client, owned = env
    with_data = await _create_asset(client, owned, "N68.6-A", currency="USD")
    start = date.today() - timedelta(days=3)
    await _seed_prices(client, with_data, start, 2)
    await _seed_event(client, with_data, start, "DIVIDEND", "1", "USD")
    empty = await _create_asset(client, owned, "N68.6-B", currency="USD")
    ghost = 999_999_999

    resp = await _patch_currency(
        client,
        [
            FAAssetPatchItem(asset_id=with_data, currency="EUR"),
            FAAssetPatchItem(asset_id=empty, currency="EUR"),
            FAAssetPatchItem(asset_id=ghost, currency="EUR"),
        ],
    )

    assert resp.status_code == 200, f"expected 200 (partial), got {resp.status_code}: {resp.text}"
    assert OLD_TOKEN not in resp.text, resp.text
    body = resp.json()
    per_asset = {r["asset_id"]: r for r in body["results"]}
    assert per_asset[with_data]["success"] is True, f"{per_asset[with_data]}. Red today (N68): refused with the token"
    assert per_asset[empty]["success"] is True, per_asset[empty]
    assert per_asset[ghost]["success"] is False and "not found" in per_asset[ghost]["message"], per_asset[ghost]
    assert body["success_count"] == 2, body
    assert await _currency(client, with_data) == "EUR" and await _currency(client, empty) == "EUR"
    assert await _prices_of(client, with_data, start, 2) == []
    print_success("partial success 200: two patched, one not found")


@pytest.mark.asyncio
async def test_currency_change_touches_no_other_asset(env):
    """N68.7 — an asset nobody patched keeps its prices, events and linked transaction, while its neighbour changes."""
    print_section("N68.7 — other assets untouched")
    client, owned = env
    patched = await _create_asset(client, owned, "N68.7-A", currency="USD")
    bystander = await _create_asset(client, owned, "N68.7-B", currency="USD")
    broker_id = await _create_broker(client, owned)
    start = date.today() - timedelta(days=5)
    for asset_id in (patched, bystander):
        await _seed_prices(client, asset_id, start, 2)
    patched_event = await _seed_event(client, patched, start, "DIVIDEND", "1", "USD")
    bystander_event = await _seed_event(client, bystander, start, "DIVIDEND", "1", "USD")
    (bystander_tx,) = await _commit(client, [{"broker_id": broker_id, "asset_id": bystander, "type": "DIVIDEND", "date": start.isoformat(), "cash": {"code": "USD", "amount": "5"}, "asset_event_id": bystander_event}])
    before = await _tx_rows(client, [bystander_tx])

    resp = await _patch_currency(client, [FAAssetPatchItem(asset_id=patched, currency="EUR")])

    _assert_all_patched(resp, [patched])
    assert patched_event not in [e["id"] for e in await _events_of(client, patched)]
    assert len(await _prices_of(client, bystander, start, 2)) == 2, "the bystander keeps its prices"
    assert [e["id"] for e in await _events_of(client, bystander)] == [bystander_event], "...and its event"
    assert (await _tx_rows(client, [bystander_tx])) == before, "...and its linked transaction, untouched"
    assert await _currency(client, bystander) == "USD"
    print_success("the neighbour's market data is intact")


@pytest.mark.asyncio
async def test_currency_change_with_nothing_to_lose_passes(env):
    """N68.8 — an asset with no price and no event changes currency, as before."""
    print_section("N68.8 — nothing to lose")
    client, owned = env
    asset_id = await _create_asset(client, owned, "N68.8", currency="USD")

    resp = await _patch_currency(client, [FAAssetPatchItem(asset_id=asset_id, currency="EUR")])

    assert resp.status_code == 200, resp.text
    assert resp.json()["results"][0]["success"] is True, resp.text
    assert await _currency(client, asset_id) == "EUR"
    print_success("empty asset changed currency")
