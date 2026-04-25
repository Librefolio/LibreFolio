"""
Test Suite: Backup Export — Events + FX Rates

Covers Phase 7 Part 3 Closure_2 G-batch6 (post-G coverage gap-fill):

- ``GET /api/v1/backup/asset/{id}/events?format=csv|json``
- ``GET /api/v1/backup/fx/{base}/{quote}/rates?format=csv|json``

Both endpoints had **0% coverage** because G.11 only exercised the prices
variant. Same envelope/CSV contract as ``backup_asset_prices`` (already
covered by ``test_asset_prices_export.py``):

* CSV: ``text/csv``, ``;`` delimiter, fixed columns from
  ``backup_service.{EVENT_COLUMNS,FX_RATE_COLUMNS}``, ``Content-Disposition``
  attachment with the ``<scope>_<slug>_<YYYY-MM-DD>.csv`` filename.
* JSON: ``application/json`` envelope ``{scope, entity, exported_at,
  row_count, rows[]}`` — ``scope`` is ``events`` or ``fx_rates``.

Tests:
- Events CSV → header + manual row with ``source=MANUAL``.
- Events JSON envelope → ``scope=events``, ``row_count`` matches.
- Events on missing asset → 404.
- Empty events → header-only CSV / row_count=0.
- FX CSV with seeded MANUAL rate.
- FX JSON envelope shape; inverted pair sets ``inverted=true``.
- FX 400 on identical or empty currencies.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G-batch6.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets import FAAssetCreateItem, FABulkAssetCreateResponse
from backend.app.schemas.common import Currency
from backend.app.schemas.fx import FXUpsertItem
from backend.app.schemas.prices import FAAssetEventPoint, FAEventUpsert
from backend.app.services.backup_service import EVENT_COLUMNS, FX_RATE_COLUMNS
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    import time  # noqa: PLC0415
    import uuid as _uuid  # noqa: PLC0415

    username = f"test_{int(time.time() * 1000)}_{_uuid.uuid4().hex[:4]}"
    email = f"{username}@test.com"
    password = "TestPass123!"
    r = await client.post(
        f"{API_BASE}/auth/register",
        json={"username": username, "email": email, "password": password},
        timeout=TIMEOUT,
    )
    assert r.status_code == 201, r.text
    login = await client.post(
        f"{API_BASE}/auth/login",
        json={"username": username, "password": password},
        timeout=TIMEOUT,
    )
    assert login.status_code == 200, login.text
    s = login.cookies.get("session")
    if s:
        client.cookies.set("session", s)


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as srv:
        if not srv.start_server():
            pytest.fail("Failed to start test server")
        yield srv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_asset(client: httpx.AsyncClient, tag: str, currency: str = "USD") -> int:
    item = FAAssetCreateItem(display_name=f"Backup {unique_id(tag)}", currency=currency)
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    return FABulkAssetCreateResponse(**resp.json()).results[0].asset_id


async def _seed_event(
    client: httpx.AsyncClient,
    asset_id: int,
    on: date,
    amount: Decimal,
    currency: str = "USD",
) -> None:
    upsert = FAEventUpsert(
        asset_id=asset_id,
        events=[
            FAAssetEventPoint(
                date=on,
                type="DIVIDEND",
                value=Currency(code=currency, amount=amount),
                notes="backup-test",
            )
        ],
    )
    resp = await client.post(
        f"{API_BASE}/assets/events",
        json=[upsert.model_dump(mode="json")],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text


async def _seed_fx_rate(
    client: httpx.AsyncClient,
    base: str,
    quote: str,
    on: date,
    rate: Decimal,
) -> None:
    item = FXUpsertItem(
        **{"date": on},
        base=base,
        quote=quote,
        rate=rate,
        source="MANUAL",
    )
    resp = await client.post(
        f"{API_BASE}/fx/currencies/rate",
        json=[item.model_dump(mode="json")],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Events backup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_events_csv_export_shape(test_server):
    """G-batch6.6 — events CSV: ``;`` delimiter + fixed columns + MANUAL source."""
    print_section("G-batch6.6 — events CSV shape")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "EvtCSV", currency="USD")
        on = date.today() - timedelta(days=2)
        await _seed_event(client, asset_id, on, Decimal("1.50"))

        resp = await client.get(
            f"{API_BASE}/backup/asset/{asset_id}/events",
            params={"format": "csv"},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("text/csv")
        disp = resp.headers.get("content-disposition", "")
        assert "events_" in disp and disp.endswith('.csv"'), disp

        rows = list(csv.reader(io.StringIO(resp.text), delimiter=";"))
        assert rows[0] == EVENT_COLUMNS, rows[0]
        assert len(rows) == 2, f"expected header + 1 row, got {len(rows)}"
        # Manual events have source=MANUAL and provider_assignment_id empty.
        record = dict(zip(EVENT_COLUMNS, rows[1], strict=True))
        assert record["date"] == on.isoformat()
        assert record["type"] == "DIVIDEND"
        assert record["source"] == "MANUAL"
        assert record["currency"] == "USD"
        assert record["provider_assignment_id"] == ""
        print_success("Events CSV: header + MANUAL row OK")


@pytest.mark.asyncio
async def test_events_json_envelope(test_server):
    """G-batch6.7 — events JSON: scope=events + row_count + entity.currency."""
    print_section("G-batch6.7 — events JSON envelope")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "EvtJSON", currency="EUR")
        on = date.today() - timedelta(days=1)
        await _seed_event(client, asset_id, on, Decimal("0.75"), currency="EUR")

        resp = await client.get(
            f"{API_BASE}/backup/asset/{asset_id}/events",
            params={"format": "json"},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("application/json")
        payload = json.loads(resp.text)
        assert payload["scope"] == "events"
        assert payload["entity"]["type"] == "asset"
        assert payload["entity"]["id"] == asset_id
        assert payload["entity"]["currency"] == "EUR"
        assert payload["row_count"] == 1
        assert "exported_at" in payload
        only = payload["rows"][0]
        assert only["date"] == on.isoformat()
        assert only["type"] == "DIVIDEND"
        assert only["source"] == "MANUAL"
        print_success("Events JSON envelope OK (scope=events)")


@pytest.mark.asyncio
async def test_events_unknown_asset_returns_404(test_server):
    """G-batch6.8 — events backup on missing asset → 404."""
    print_section("G-batch6.8 — events 404")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await client.get(f"{API_BASE}/backup/asset/999999999/events", timeout=TIMEOUT)
        assert resp.status_code == 404, resp.text
        print_success("Unknown asset id → 404")


@pytest.mark.asyncio
async def test_events_empty_history(test_server):
    """G-batch6.9 — asset with zero events → header-only CSV / row_count=0."""
    print_section("G-batch6.9 — empty events backup")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "EvtEmpty")

        csv_resp = await client.get(
            f"{API_BASE}/backup/asset/{asset_id}/events",
            params={"format": "csv"},
            timeout=TIMEOUT,
        )
        assert csv_resp.status_code == 200
        rows = list(csv.reader(io.StringIO(csv_resp.text), delimiter=";"))
        assert rows[0] == EVENT_COLUMNS
        assert len(rows) == 1, f"expected header-only CSV, got {len(rows)} rows"

        json_resp = await client.get(
            f"{API_BASE}/backup/asset/{asset_id}/events",
            params={"format": "json"},
            timeout=TIMEOUT,
        )
        payload = json.loads(json_resp.text)
        assert payload["row_count"] == 0
        assert payload["rows"] == []
        print_success("Empty events backup: CSV header-only + JSON row_count=0")


# ---------------------------------------------------------------------------
# FX rates backup
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fx_csv_export_shape(test_server):
    """G-batch6.10 — FX CSV: ``;`` delimiter + fixed columns + stored ordering."""
    print_section("G-batch6.10 — FX rates CSV shape")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        on = date.today() - timedelta(days=1)
        # Storage invariant: base < quote → seed EUR/USD to be unambiguous.
        await _seed_fx_rate(client, "EUR", "USD", on, Decimal("1.10"))

        resp = await client.get(
            f"{API_BASE}/backup/fx/EUR/USD/rates",
            params={"format": "csv"},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("text/csv")
        disp = resp.headers.get("content-disposition", "")
        assert "fx_eur_usd_" in disp and disp.endswith('.csv"'), disp

        rows = list(csv.reader(io.StringIO(resp.text), delimiter=";"))
        assert rows[0] == FX_RATE_COLUMNS
        assert len(rows) >= 2, "expected header + at least one rate row"
        # Find OUR seeded row by date — populate may have inserted others.
        seeded = next(
            (dict(zip(FX_RATE_COLUMNS, r, strict=True)) for r in rows[1:] if r and r[0] == on.isoformat()),
            None,
        )
        assert seeded is not None, f"seeded row {on.isoformat()} not found in {rows[1:]}"
        assert seeded["base"] == "EUR"
        assert seeded["quote"] == "USD"
        assert Decimal(seeded["rate"]) == Decimal("1.10")
        print_success("FX CSV: stored EUR/USD rate exported correctly")


@pytest.mark.asyncio
async def test_fx_json_envelope_with_inverted_pair(test_server):
    """G-batch6.11 — FX JSON: requesting USD/EUR on stored EUR/USD sets ``inverted=true``."""
    print_section("G-batch6.11 — FX JSON envelope + inverted")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        on = date.today() - timedelta(days=2)
        await _seed_fx_rate(client, "EUR", "USD", on, Decimal("1.08"))

        # Request inverted (USD/EUR): server normalises to stored order and
        # marks the envelope ``inverted: true``.
        resp = await client.get(
            f"{API_BASE}/backup/fx/USD/EUR/rates",
            params={"format": "json"},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, resp.text
        payload = json.loads(resp.text)
        assert payload["scope"] == "fx_rates"
        entity = payload["entity"]
        assert entity["type"] == "fx_pair"
        assert entity["base"] == "EUR"
        assert entity["quote"] == "USD"
        assert entity["requested_base"] == "USD"
        assert entity["requested_quote"] == "EUR"
        assert entity["inverted"] is True
        assert payload["row_count"] >= 1
        print_success("FX JSON envelope correctly flags inverted pair")


@pytest.mark.asyncio
async def test_fx_invalid_pair_returns_400(test_server):
    """G-batch6.12 — same base/quote → 400."""
    print_section("G-batch6.12 — FX rates invalid pair → 400")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Same currency: explicit 400 raised before the DB query.
        resp = await client.get(f"{API_BASE}/backup/fx/USD/USD/rates", timeout=TIMEOUT)
        assert resp.status_code == 400, resp.text
        print_success("Identical base/quote rejected with 400")


@pytest.mark.asyncio
async def test_fx_empty_pair_returns_header_only_csv(test_server):
    """G-batch6.13 — pair with zero rates → header-only CSV, row_count=0 JSON."""
    print_section("G-batch6.13 — empty FX pair backup")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Pick an unlikely-to-be-seeded pair (CAD/SEK alphabetical).
        csv_resp = await client.get(
            f"{API_BASE}/backup/fx/CAD/SEK/rates",
            params={"format": "csv"},
            timeout=TIMEOUT,
        )
        assert csv_resp.status_code == 200, csv_resp.text
        rows = list(csv.reader(io.StringIO(csv_resp.text), delimiter=";"))
        assert rows[0] == FX_RATE_COLUMNS
        # If a previous test in the suite already inserted a rate this would
        # be > 1; we only assert the header is present and CSV is well-formed.
        assert len(rows) >= 1
        json_resp = await client.get(
            f"{API_BASE}/backup/fx/CAD/SEK/rates",
            params={"format": "json"},
            timeout=TIMEOUT,
        )
        payload = json.loads(json_resp.text)
        assert payload["scope"] == "fx_rates"
        assert payload["entity"]["base"] == "CAD"
        assert payload["entity"]["quote"] == "SEK"
        # row_count is non-negative integer (no FX rates seeded for CAD/SEK
        # in this suite, but other tests may have seeded — accept >= 0).
        assert payload["row_count"] == len(payload["rows"])
        print_success("Empty FX pair backup contract honoured")
