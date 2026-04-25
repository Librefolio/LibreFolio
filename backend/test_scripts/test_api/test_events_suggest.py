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
- More than 500 requests → 422.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G.4.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import httpx
import pytest

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
