"""
Test Suite: Market-Data Wipe Endpoints (R3-3 Policy D direct API, N68 "policy A")

- ``GET  /api/v1/assets/{id}/market-data/summary``  -> dry-run counters.
- ``POST /api/v1/assets/{id}/market-data/wipe``     -> destructive wipe.

Both delegate to ``AssetSourceManager.wipe_market_data_for_currency_change``.

Contract after N68 (lot X5-3): SPLIT events survive the wipe. The answer, and the summary's, are exactly
``{prices, events_manual, events_provider, splits_kept, linked_tx, oldest, newest, dry_run}``:

- ``events_manual`` / ``events_provider`` count the NON-SPLIT events that go;
- ``splits_kept`` counts the SPLIT events that stay;
- ``linked_tx`` counts the transactions linked to the events that go (not those linked to a SPLIT);
- the wipe never answers 409 ``MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST`` any more: a SPLIT with a costless
  incoming ADJUSTMENT is kept, and the ADJUSTMENT stays linked to it.

Tests:
- summary on empty asset -> all counters zero (``splits_kept`` included), dry_run=true.
- summary on populated asset -> counters reflect prices + manual events, oldest/newest are ISO dates.
- summary counts a SPLIT as kept, not as an event that goes; exact key set.
- wipe removes prices + non-split events, returns dry_run=false, re-call is idempotent.
- wipe keeps a SPLIT and its costless ADJUSTMENT linked (200, not 409); the dividend's transaction is unlinked, not deleted.
- 404 when asset id does not exist (ASSET_NOT_FOUND mapping).
- summary never mutates.

Isolation: each test creates its own user, broker and asset(s) and addresses them by id.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets.assets import FAAssetCreateItem, FABulkAssetCreateResponse
from backend.app.schemas.assets.events import FAAssetEventPoint, FAEventUpsert
from backend.app.schemas.common import Currency
from backend.app.schemas.prices import FAPricePoint, FAUpsert
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
        assert body["splits_kept"] == 0, body
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
        assert body["splits_kept"] == 0, body
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
        assert body1["splits_kept"] == 0, body1
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


# ============================================================================
# N68 — SPLIT events survive the wipe
# ============================================================================


async def _events_of(client: httpx.AsyncClient, asset_id: int) -> list[dict]:
    resp = await client.post(
        f"{API_BASE}/assets/events/query",
        json=[{"asset_id": asset_id, "date_range": {"start": "2000-01-01", "end": (date.today() + timedelta(days=365)).isoformat()}}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text
    return next(item for item in resp.json()["items"] if item["asset_id"] == asset_id)["events"]


async def _prices_of(client: httpx.AsyncClient, asset_id: int, start: date, count: int) -> list[dict]:
    """The prices stored on the ``count`` days from ``start`` (exactly the seeded range: a wider query is filled forward)."""
    date_range = {"start": start.isoformat(), "end": (start + timedelta(days=count - 1)).isoformat()}
    resp = await client.post(f"{API_BASE}/assets/prices/query", json=[{"asset_id": asset_id, "date_range": date_range}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return next(item for item in resp.json()["items"] if item["asset_id"] == asset_id)["prices"]


async def _event_id(client: httpx.AsyncClient, asset_id: int, day: date, kind: str) -> int:
    ids = [e["id"] for e in await _events_of(client, asset_id) if e["date"] == day.isoformat() and e["type"] == kind]
    assert len(ids) == 1, f"expected one {kind} on {day} for asset {asset_id}, got {ids}"
    return ids[0]


async def _create_split_event(client: httpx.AsyncClient, asset_id: int, day: date, currency: str = "USD") -> int:
    resp = await client.post(
        f"{API_BASE}/assets/events",
        json=[{"asset_id": asset_id, "events": [{"date": day.isoformat(), "type": "SPLIT", "value": {"code": currency, "amount": "2"}}]}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text
    return await _event_id(client, asset_id, day, "SPLIT")


async def _create_broker(client: httpx.AsyncClient) -> int:
    name = f"Wipe Broker {unique_id('WB')}"
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": name, "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["results"] if r["name"] == name)
    assert row["success"] is True, row
    return row["broker_id"]


async def _commit_creates(client: httpx.AsyncClient, creates: list[dict]) -> list[int]:
    resp = await client.post(f"{API_BASE}/transactions/commit", json={"creates": creates}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["committed"] is True, body["issues"]
    ids = {r["index"]: r["ids"][0] for r in body["results"] if r["operation"] == "create"}
    return [ids[i] for i in range(len(creates))]


async def _tx_rows(client: httpx.AsyncClient, ids: list[int]) -> dict[int, dict]:
    resp = await client.get(f"{API_BASE}/transactions", params={"ids": ids}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    rows = {tx["id"]: tx for tx in resp.json()}
    assert set(rows) == set(ids), f"transactions {sorted(set(ids) - set(rows))} missing"
    return rows


async def _drop(client: httpx.AsyncClient, broker_ids: list[int], asset_ids: list[int]) -> None:
    """Brokers (force: their transactions go with them), then assets. Reports a failure, never hides the test's own."""
    problems: list[str] = []
    for broker_id in broker_ids:
        resp = await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
        if resp.status_code != 200:
            problems.append(f"broker {broker_id}: {resp.status_code} {resp.text}")
    if asset_ids:
        resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)
        if resp.status_code != 200:
            problems.append(f"assets {asset_ids}: {resp.status_code} {resp.text}")
    assert not problems, problems


async def _split_case(client: httpx.AsyncClient) -> dict:
    """An asset with 2 prices, a manual DIVIDEND event linked to a DIVIDEND transaction, a manual SPLIT of 2 with a
    costless ADJUSTMENT linked to it, and the BUY that gives the position its units; on one broker."""
    asset_id = await _create_asset(client, "WN68", currency="USD")
    broker_id = await _create_broker(client)
    start = date(2026, 1, 10)
    await _seed_prices(client, asset_id, start, 2)
    await _seed_events(client, asset_id, date(2026, 2, 10), 1)
    dividend_event = await _event_id(client, asset_id, date(2026, 2, 10), "DIVIDEND")
    split_event = await _create_split_event(client, asset_id, date(2026, 2, 1))
    buy_tx, adjustment_tx, dividend_tx = await _commit_creates(
        client,
        [
            {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": "2026-01-15", "quantity": "15", "cash": {"code": "USD", "amount": "-1500"}},
            {"broker_id": broker_id, "asset_id": asset_id, "type": "ADJUSTMENT", "date": "2026-02-01", "quantity": "15", "asset_event_id": split_event, "cost_basis_mode": "auto"},
            {"broker_id": broker_id, "asset_id": asset_id, "type": "DIVIDEND", "date": "2026-02-10", "cash": {"code": "USD", "amount": "5"}, "asset_event_id": dividend_event},
        ],
    )
    return {"asset_id": asset_id, "broker_id": broker_id, "start": start, "dividend_event": dividend_event, "split_event": split_event, "buy_tx": buy_tx, "adjustment_tx": adjustment_tx, "dividend_tx": dividend_tx}


@pytest.mark.asyncio
async def test_summary_counts_a_split_as_kept_not_as_an_event_that_goes(test_server):
    """N68.1 — summary of an asset with a SPLIT: ``splits_kept`` 1, the SPLIT is not in ``events_manual``, ``linked_tx``
    counts the dividend's transaction only (not the SPLIT's adjustment); the keys are exactly the contract's."""
    print_section("N68.1 — summary: splits_kept")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        case = await _split_case(client)
        try:
            resp = await client.get(f"{API_BASE}/assets/{case['asset_id']}/market-data/summary", timeout=TIMEOUT)
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert sorted(body) == ["dry_run", "events_manual", "events_provider", "linked_tx", "newest", "oldest", "prices", "splits_kept"], body
            assert body["prices"] == 2, body
            assert body["events_manual"] == 1, f"only the dividend goes; the SPLIT is not counted as an event that goes: {body}"
            assert body["events_provider"] == 0, body
            assert body["splits_kept"] == 1, body
            assert body["linked_tx"] == 1, f"only the dividend's transaction is linked to an event that goes: {body}"
            assert body["oldest"] == case["start"].isoformat() and body["newest"] == (case["start"] + timedelta(days=1)).isoformat(), body
            assert body["dry_run"] is True
            assert len(await _prices_of(client, case["asset_id"], case["start"], 2)) == 2, "the summary wrote nothing"
            print_success(f"Summary: {body}")
        finally:
            await _drop(client, [case["broker_id"]], [case["asset_id"]])


@pytest.mark.asyncio
async def test_wipe_keeps_the_split_and_its_costless_adjustment_and_unlinks_the_dividend(test_server):
    """N68.2 — POST /wipe on an asset whose SPLIT has a costless incoming ADJUSTMENT: 200 (never the old 409), prices and
    the dividend gone, the SPLIT kept, the ADJUSTMENT untouched and still linked, the dividend's transaction kept and
    unlinked; a second wipe is idempotent (nothing to delete, ``splits_kept`` still 1)."""
    print_section("N68.2 — wipe keeps the split")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        case = await _split_case(client)
        try:
            tx_ids = [case["buy_tx"], case["adjustment_tx"], case["dividend_tx"]]
            before = await _tx_rows(client, tx_ids)
            assert before[case["adjustment_tx"]]["asset_event_id"] == case["split_event"], "precondition: the adjustment is linked to its SPLIT"

            wipe = await client.post(f"{API_BASE}/assets/{case['asset_id']}/market-data/wipe", timeout=TIMEOUT)

            assert wipe.status_code == 200, f"{wipe.status_code} {wipe.text}. Red today (X-R48): 409 MARKET_DATA_SPLIT_ADJUSTMENTS_WITHOUT_COST"
            body = wipe.json()
            assert (body["prices"], body["events_manual"], body["events_provider"], body["splits_kept"], body["linked_tx"], body["dry_run"]) == (2, 1, 0, 1, 1, False), body
            assert [e["id"] for e in await _events_of(client, case["asset_id"])] == [case["split_event"]], "only the SPLIT stays"
            assert await _prices_of(client, case["asset_id"], case["start"], 2) == []
            after = await _tx_rows(client, tx_ids)
            assert after[case["adjustment_tx"]] == before[case["adjustment_tx"]], "the SPLIT's adjustment is untouched, link included"
            assert after[case["buy_tx"]] == before[case["buy_tx"]]
            assert after[case["dividend_tx"]]["asset_event_id"] is None, "the dividend's transaction is unlinked, not deleted"

            again = await client.post(f"{API_BASE}/assets/{case['asset_id']}/market-data/wipe", timeout=TIMEOUT)
            assert again.status_code == 200, again.text
            second = again.json()
            assert (second["prices"], second["events_manual"], second["events_provider"], second["splits_kept"], second["linked_tx"]) == (0, 0, 0, 1, 0), second
            print_success("Wipe: 200, SPLIT and its adjustment kept, dividend tx unlinked, second wipe idempotent")
        finally:
            await _drop(client, [case["broker_id"]], [case["asset_id"]])
