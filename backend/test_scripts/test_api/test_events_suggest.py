"""
Test Suite: POST /transactions/events/suggest (Blocco C.2)

Covers Phase 7 Part 3 Blocco C.2 + Blocco G.4.

Contract under test (see ``transaction_service.suggest_events_bulk``
L838 + ``transactions.py`` L260):

For each ``(asset_id, date, type, tolerance_days)`` return candidate
``AssetEvent`` rows whose ``type`` maps to the tx ``type`` and whose
``date`` is within ±``tolerance_days``.

**Type mapping**:

- DIVIDEND  → {DIVIDEND}
- INTEREST  → {INTEREST}
- ADJUSTMENT → {PRICE_ADJUSTMENT, SPLIT}
- any other tx type → ``skipped_reason="type_not_event_compatible"``,
  empty ``candidates[]`` (no DB query is issued).

**Result invariants**:

- Output order preserves input order (one result per request).
- Each result's ``candidates`` is sorted by ascending ``distance_days``.
- ``is_auto = provider_assignment_id IS NOT NULL``.
- Asset events are global (no broker access check) — only authentication
  is required.
- ``tolerance_days=0`` matches only the exact date.
- ``tolerance_days`` is capped at 7 by the schema (422 beyond).
- The window is cut at the calendar's edge: an item dated 0001-01-01 or
  9999-12-31 is answered like any other, not with a 500 (W-B71).
- Large batches (>500 requests) are delegated without a cap.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G.4.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import httpx
import pytest

import backend.app.api.v1.transactions as transactions_api
from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


# ============================================================================
# Fixtures & helpers
# ============================================================================


def _uname() -> str:
    return f"g4_{int(date.today().toordinal())}_{uuid.uuid4().hex[:8]}"


async def create_test_user(client: httpx.AsyncClient) -> None:
    username = _uname()
    password = "TestPass123!"
    resp = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": f"{username}@test.com", "password": password},
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


async def _create_asset(client: httpx.AsyncClient, currency: str = "EUR") -> int:
    payload = [{"display_name": f"G4 Asset {uuid.uuid4().hex[:6]}", "currency": currency, "asset_type": "STOCK"}]
    resp = await client.post(f"{API_BASE}/assets", json=payload, timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["results"][0]["asset_id"]


async def _upsert_events(
    client: httpx.AsyncClient,
    asset_id: int,
    events: list[dict],
) -> None:
    """Upsert manual events for an asset via ``POST /assets/events``."""
    payload = [{"asset_id": asset_id, "events": events}]
    resp = await client.post(f"{API_BASE}/assets/events", json=payload, timeout=TIMEOUT)
    assert resp.status_code == 200, f"upsert events failed: {resp.status_code} {resp.text}"


async def _suggest(client: httpx.AsyncClient, items: list[dict]) -> list[dict]:
    resp = await client.post(f"{API_BASE}/transactions/events/suggest", json=items, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return resp.json()


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_suggest_matches_dividend_within_tolerance_sorted_by_distance(test_server):
    """DIVIDEND @ D with tolerance=3 returns candidates sorted by |Δdays|."""
    print_section("G.4.1 — DIVIDEND candidates sorted by distance")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        asset_id = await _create_asset(client)
        d = date.today() - timedelta(days=30)

        # Three DIVIDEND events: d+0, d+2, d-3 → distances 0, 2, 3 from d.
        await _upsert_events(
            client,
            asset_id,
            [
                {"date": d.isoformat(), "type": "DIVIDEND", "value": {"code": "EUR", "amount": "1.00"}},
                {"date": (d + timedelta(days=2)).isoformat(), "type": "DIVIDEND", "value": {"code": "EUR", "amount": "1.20"}},
                {"date": (d - timedelta(days=3)).isoformat(), "type": "DIVIDEND", "value": {"code": "EUR", "amount": "0.90"}},
                # Out-of-window event (distance 5) — must be excluded with tolerance=3.
                {"date": (d + timedelta(days=5)).isoformat(), "type": "DIVIDEND", "value": {"code": "EUR", "amount": "1.10"}},
            ],
        )

        results = await _suggest(
            client,
            [{"asset_id": asset_id, "date": d.isoformat(), "type": "DIVIDEND", "tolerance_days": 3}],
        )
        assert len(results) == 1
        r = results[0]
        assert r["asset_id"] == asset_id
        assert r["skipped_reason"] is None
        distances = [c["distance_days"] for c in r["candidates"]]
        assert distances == sorted(distances), f"not sorted: {distances}"
        assert distances[0] == 0  # exact match first
        assert 5 not in distances, "out-of-window event leaked in"
        assert len(r["candidates"]) == 3
        for c in r["candidates"]:
            assert c["type"] == "DIVIDEND"
            assert c["is_auto"] is False  # all manually inserted
        print_success(f"Sorted distances {distances} — out-of-window excluded")


@pytest.mark.asyncio
async def test_suggest_zero_tolerance_matches_exact_date_only(test_server):
    """tolerance_days=0 returns only the candidate whose date == request.date."""
    print_section("G.4.2 — tolerance_days=0 exact-date only")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        asset_id = await _create_asset(client)
        d = date.today() - timedelta(days=20)

        await _upsert_events(
            client,
            asset_id,
            [
                {"date": d.isoformat(), "type": "INTEREST", "value": {"code": "EUR", "amount": "5"}},
                {"date": (d + timedelta(days=1)).isoformat(), "type": "INTEREST", "value": {"code": "EUR", "amount": "5"}},
            ],
        )

        results = await _suggest(
            client,
            [{"asset_id": asset_id, "date": d.isoformat(), "type": "INTEREST", "tolerance_days": 0}],
        )
        cands = results[0]["candidates"]
        assert len(cands) == 1, cands
        assert cands[0]["distance_days"] == 0
        assert cands[0]["date"] == d.isoformat()
        print_success("Exact-date match isolated (tolerance=0)")


@pytest.mark.asyncio
async def test_suggest_adjustment_maps_to_split_and_price_adjustment(test_server):
    """ADJUSTMENT tx type → pulls both SPLIT and PRICE_ADJUSTMENT events."""
    print_section("G.4.3 — ADJUSTMENT → {SPLIT, PRICE_ADJUSTMENT}")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        asset_id = await _create_asset(client)
        d = date.today() - timedelta(days=40)

        await _upsert_events(
            client,
            asset_id,
            [
                {"date": d.isoformat(), "type": "SPLIT", "value": {"code": "EUR", "amount": "2"}},
                {
                    "date": (d + timedelta(days=1)).isoformat(),
                    "type": "PRICE_ADJUSTMENT",
                    "value": {"code": "EUR", "amount": "0.5"},
                },
                # DIVIDEND must NOT surface for ADJUSTMENT requests.
                {"date": d.isoformat(), "type": "DIVIDEND", "value": {"code": "EUR", "amount": "1.0"}},
            ],
        )

        results = await _suggest(
            client,
            [{"asset_id": asset_id, "date": d.isoformat(), "type": "ADJUSTMENT", "tolerance_days": 2}],
        )
        types = sorted({c["type"] for c in results[0]["candidates"]})
        assert types == ["PRICE_ADJUSTMENT", "SPLIT"], types
        assert "DIVIDEND" not in {c["type"] for c in results[0]["candidates"]}
        print_success(f"ADJUSTMENT pulled {types}, DIVIDEND excluded")


@pytest.mark.asyncio
async def test_suggest_incompatible_type_is_skipped(test_server):
    """BUY is not an event-compatible type → skipped_reason emitted."""
    print_section("G.4.4 — incompatible tx type → skipped")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        asset_id = await _create_asset(client)
        d = date.today() - timedelta(days=5)

        results = await _suggest(
            client,
            [{"asset_id": asset_id, "date": d.isoformat(), "type": "BUY", "tolerance_days": 1}],
        )
        r = results[0]
        assert r["skipped_reason"] == "type_not_event_compatible", r
        assert r["candidates"] == []
        print_success("BUY correctly skipped with type_not_event_compatible")


@pytest.mark.asyncio
async def test_suggest_preserves_input_order(test_server):
    """Output results are in the same order as the input requests."""
    print_section("G.4.5 — result order mirrors input order")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        a1 = await _create_asset(client)
        a2 = await _create_asset(client)
        d = date.today() - timedelta(days=10)

        requests = [
            {"asset_id": a2, "date": d.isoformat(), "type": "DIVIDEND", "tolerance_days": 0},
            {"asset_id": a1, "date": d.isoformat(), "type": "INTEREST", "tolerance_days": 0},
            # Skipped entry in the middle to ensure the shape doesn't shift.
            {"asset_id": a1, "date": d.isoformat(), "type": "BUY", "tolerance_days": 0},
        ]
        results = await _suggest(client, requests)
        assert [r["asset_id"] for r in results] == [a2, a1, a1]
        assert [r["type"] for r in results] == ["DIVIDEND", "INTEREST", "BUY"]
        assert results[2]["skipped_reason"] == "type_not_event_compatible"
        print_success("Input order preserved across matched and skipped entries")


@pytest.mark.asyncio
async def test_suggest_no_matches_returns_empty_candidates(test_server):
    """No events in DB → candidates=[] but skipped_reason stays None."""
    print_section("G.4.6 — empty candidates for compatible-but-unmatched type")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        asset_id = await _create_asset(client)
        d = date.today() - timedelta(days=50)

        results = await _suggest(
            client,
            [{"asset_id": asset_id, "date": d.isoformat(), "type": "DIVIDEND", "tolerance_days": 7}],
        )
        r = results[0]
        assert r["skipped_reason"] is None
        assert r["candidates"] == []
        print_success("Compatible-type empty-match returns [] with no skipped_reason")


@pytest.mark.asyncio
async def test_suggest_rejects_tolerance_over_max(test_server):
    """tolerance_days > 7 → schema validation → 422."""
    print_section("G.4.7 — tolerance > 7 rejected by schema")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        asset_id = await _create_asset(client)
        resp = await client.post(
            f"{API_BASE}/transactions/events/suggest",
            json=[{"asset_id": asset_id, "date": date.today().isoformat(), "type": "DIVIDEND", "tolerance_days": 8}],
            timeout=TIMEOUT,
        )
        assert resp.status_code == 422, f"expected 422, got {resp.status_code}: {resp.text}"
        print_success("tolerance_days=8 rejected with 422")


@pytest.mark.asyncio
async def test_suggest_direct_calls_service(monkeypatch: pytest.MonkeyPatch):
    """Happy path: route delegates to TransactionService.suggest_events_bulk."""
    print_section("G.4.8a — direct suggest happy path")

    captured: dict = {}

    async def fake_suggest_events_bulk(self, requests):
        captured["requests"] = requests
        return ["ok"]

    monkeypatch.setattr(
        transactions_api,
        "TransactionService",
        type("FakeTransactionService", (), {"__init__": lambda self, session: None, "suggest_events_bulk": fake_suggest_events_bulk}),
    )

    result = await transactions_api.suggest_events(requests=["req"], session=object(), _current_user=object())

    assert result == ["ok"]
    assert captured["requests"] == ["req"]
    print_success("Direct suggest happy path delegated to service")


@pytest.mark.asyncio
async def test_suggest_accepts_more_than_500_requests(monkeypatch: pytest.MonkeyPatch):
    """The 500-item cap was removed: large raw list bodies are delegated as-is."""
    print_section("G.4.8 — more than 500 requests accepted (no cap)")

    captured: dict = {}

    async def fake_suggest_events_bulk(self, requests):
        captured["count"] = len(requests)
        return ["ok"] * len(requests)

    monkeypatch.setattr(
        transactions_api,
        "TransactionService",
        type("FakeTransactionService", (), {"__init__": lambda self, session: None, "suggest_events_bulk": fake_suggest_events_bulk}),
    )

    result = await transactions_api.suggest_events(requests=[object()] * 501, session=object(), _current_user=object())

    assert captured["count"] == 501
    assert len(result) == 501
    print_success(">500 requests accepted and delegated (no cap)")


# ============================================================================
# W-B71 — the window at the calendar's edges
# ============================================================================
#
# suggest_events_bulk searches date ± tolerance_days. From 0001-01-01 back and from 9999-12-31 on, any tolerance above
# 0 leaves the calendar: OverflowError, a 500 for the whole batch. The guard (G.4.9) and the red (G.4.10) send the same
# batch — an ordinary DIVIDEND at tolerance_days=3, then one dated 0001-01-01 and one dated 9999-12-31 — except for
# the edge items' tolerance: 0 in the guard (the day itself, answered today), 3 in the red.

#: The calendar's edge days, where a window around the date leaves the calendar.
CALENDAR_EDGES = (date.min, date.max)
#: At tolerance_days=3 the events 3 days either side of the day are inside the window, those 4 days away just outside.
WINDOW_TOLERANCE = 3
WINDOW_INSIDE = (-3, 3)
WINDOW_OUTSIDE = (-4, 4)


async def _drop_asset(client: httpx.AsyncClient, asset_id: int) -> list[str]:
    """Delete an asset the test created; its events cascade. Returns the problems instead of raising, so that a failed cleanup never hides the test's own failure."""
    try:
        resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        return [f"asset {asset_id}: cleanup request failed: {exc!r}"]
    done = resp.status_code == 200 and any(item.get("asset_id") == asset_id and item.get("success") for item in resp.json().get("results", []))
    return [] if done else [f"asset {asset_id} not deleted: HTTP {resp.status_code} {resp.text}"]


async def _upsert_window_events(client: httpx.AsyncClient, asset_id: int, day: date) -> None:
    """A manual DIVIDEND of the asset at each offset of WINDOW_INSIDE and WINDOW_OUTSIDE from ``day``."""
    await _upsert_events(client, asset_id, [{"date": (day + timedelta(days=offset)).isoformat(), "type": "DIVIDEND", "value": {"code": "EUR", "amount": "1.00"}} for offset in (*WINDOW_INSIDE, *WINDOW_OUTSIDE)])


def _dividend(asset_id: int, day: date, tolerance_days: int) -> dict:
    """One suggest request item: a DIVIDEND of the asset dated ``day``."""
    return {"asset_id": asset_id, "date": day.isoformat(), "type": "DIVIDEND", "tolerance_days": tolerance_days}


async def _post_on_its_own_connection(client: httpx.AsyncClient, url: str, **kwargs) -> httpx.Response:
    """POST with ``client``'s session on a connection of its own, for a request that may end in an unhandled exception.

    After such a 500 the server closes the connection; sent on the client's own, the next request (the cleanup) could be
    written to it and fail with a ReadError, leaving the test's asset behind.
    """
    async with httpx.AsyncClient(cookies=client.cookies) as own:
        return await own.post(url, **kwargs)


def _assert_edge_batch_answer(results: list[dict], asset_id: int, day: date) -> None:
    """The answer to [ordinary DIVIDEND dated ``day`` at tolerance 3, DIVIDEND dated 0001-01-01, DIVIDEND dated 9999-12-31].

    One result per item, in input order; the ordinary item is offered the events 3 days either side of ``day``, never
    those 4 days away; the edge items have no candidate (the asset has no event near either edge) and no skipped_reason.
    """
    expected_items = [(asset_id, day.isoformat(), "DIVIDEND"), *((asset_id, edge.isoformat(), "DIVIDEND") for edge in CALENDAR_EDGES)]
    assert [(r["asset_id"], r["date"], r["type"]) for r in results] == expected_items, f"One result per item, in input order: {results}"
    ordinary, *edges = results
    inside = sorted((day + timedelta(days=offset)).isoformat() for offset in WINDOW_INSIDE)
    outside = sorted((day + timedelta(days=offset)).isoformat() for offset in WINDOW_OUTSIDE)
    found = sorted(candidate["date"] for candidate in ordinary["candidates"])
    assert (ordinary["skipped_reason"], found) == (None, inside), f"At tolerance_days={WINDOW_TOLERANCE} the DIVIDEND dated {day} must be offered the events of {inside}, never those of {outside}: {ordinary}"
    for edge, result in zip(CALENDAR_EDGES, edges, strict=True):
        assert (result["skipped_reason"], result["candidates"]) == (None, []), f"The asset has no event near {edge}: the DIVIDEND dated {edge} gets no candidate and no skipped_reason: {result}"


@pytest.mark.asyncio
async def test_suggest_window_guard_inside_the_calendar(test_server):
    """G.4.9 — W-B71 guard (passes before and after the cure): the edge days at tolerance_days=0, next to an ordinary window.

    The batch: a DIVIDEND dated ``d`` at tolerance_days=3, then DIVIDENDs dated 0001-01-01 and 9999-12-31 at
    tolerance_days=0 (the schema's default), whose window is the day itself, which moves nothing past the calendar.
    Answered in input order: the ordinary item is offered the events 3 days either side and not those 4 days away, the
    edge items nothing. So the edge dates are accepted as such: what G.4.10 adds is a window around them.
    """
    print_section("G.4.9 — the window inside the calendar (W-B71 guard)")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        asset_id = await _create_asset(client)
        cleanup_problems: list[str] = []
        try:
            d = date.today() - timedelta(days=30)
            await _upsert_window_events(client, asset_id, d)

            results = await _suggest(client, [_dividend(asset_id, d, WINDOW_TOLERANCE), *(_dividend(asset_id, edge, 0) for edge in CALENDAR_EDGES)])

            _assert_edge_batch_answer(results, asset_id, d)
            print_success("Edge days answered at tolerance 0; the ordinary window reaches 3 days and no further")
        finally:
            cleanup_problems = await _drop_asset(client, asset_id)
        assert cleanup_problems == [], f"Cleanup of the test's asset: {cleanup_problems}"


@pytest.mark.asyncio
async def test_suggest_cuts_the_window_at_the_calendar_edges(test_server):
    """G.4.10 — RED until W-B71: DIVIDENDs dated 0001-01-01 and 9999-12-31 at tolerance_days=3 are answered with no candidate, and the ordinary item of the same batch keeps its events.

    suggest_events_bulk searches date ± tolerance_days: 3 days before 0001-01-01 or after 9999-12-31 is outside the
    calendar, OverflowError, a 500 for the whole batch: every draft of the bulk editor loses its event suggestions for
    one row with a mistyped year. The window must be cut at the calendar's edge (shift_date, saturating at date.min /
    date.max); not a 422, since the save refuses such a date already (N74). The batch is G.4.9's, with the edge items
    at tolerance_days=3 instead of 0, and the answer must be the same.
    """
    print_section("G.4.10 — the window cut at the calendar's edges (W-B71)")
    async with httpx.AsyncClient() as client:
        await create_test_user(client)
        asset_id = await _create_asset(client)
        cleanup_problems: list[str] = []
        try:
            d = date.today() - timedelta(days=30)
            await _upsert_window_events(client, asset_id, d)
            batch = [_dividend(asset_id, d, WINDOW_TOLERANCE), *(_dividend(asset_id, edge, WINDOW_TOLERANCE) for edge in CALENDAR_EDGES)]

            resp = await _post_on_its_own_connection(client, f"{API_BASE}/transactions/events/suggest", json=batch, timeout=TIMEOUT)
            if resp.status_code != 200:
                alone: dict[str, int] = {}
                for edge in CALENDAR_EDGES:
                    probe = await _post_on_its_own_connection(client, f"{API_BASE}/transactions/events/suggest", json=[_dividend(asset_id, edge, WINDOW_TOLERANCE)], timeout=TIMEOUT)
                    alone[edge.isoformat()] = probe.status_code
                pytest.fail(
                    f"W-B71: events/suggest answered HTTP {resp.status_code} ({resp.text[:200]}) to a batch with a DIVIDEND dated 0001-01-01 and one dated 9999-12-31 at tolerance_days={WINDOW_TOLERANCE}, next to an ordinary DIVIDEND dated {d}; each edge item alone: {alone}. suggest_events_bulk computes date ∓ timedelta(days={WINDOW_TOLERANCE}), which raises OverflowError (a 500) past the calendar, so the whole batch loses its suggestions; a window at the calendar's edge must be cut there (shift_date, saturating at date.min / date.max)",
                    pytrace=False,
                )

            _assert_edge_batch_answer(resp.json(), asset_id, d)
            print_success("Window cut at the calendar's edges; the batch keeps its suggestions")
        finally:
            cleanup_problems = await _drop_asset(client, asset_id)
        assert cleanup_problems == [], f"Cleanup of the test's asset: {cleanup_problems}"
