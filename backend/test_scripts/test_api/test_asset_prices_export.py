"""
Test Suite: Asset Prices Export (I.4) + CSV Round-Trip (I-bis #5)

Covers Phase 7 Part 3 Blocco G.11:

- ``GET /api/v1/backup/asset/{asset_id}/prices?format=csv|json`` contract:
  * CSV: ``text/csv``, semicolon delimiter, fixed column order
    (``date, open, high, low, close, volume, currency, source_plugin_key,
    fetched_at``), ``Content-Disposition`` attachment filename
    ``prices_<slug>_<YYYY-MM-DD>.csv``.
  * JSON: ``application/json`` envelope
    ``{scope, entity, exported_at, row_count, rows[]}`` with
    ``scope="prices"`` and ``entity.currency`` matching the asset.
- 404 when the asset does not exist.
- Empty price history → header-only CSV / envelope with ``row_count=0``.
- **I-bis #5 round-trip**: the CSV exported by ``/backup/...`` can be
  parsed back (semicolon delimiter + extra columns tolerated) and
  re-upserted via ``POST /api/v1/assets/prices`` producing the same
  OHLC rows — this is the primary justification for the semicolon
  delimiter switch in ``backup_service.stream_rows_as_csv``.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G.11.
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
from backend.app.schemas.prices import FAPricePoint, FAUpsert
from backend.app.services.backup_service import PRICE_COLUMNS
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_info, print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0


# ============================================================================
# Fixtures & helpers
# ============================================================================


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
    assert login_resp.status_code == 200, f"login failed: {login_resp.status_code} {login_resp.text}"
    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)


@pytest.fixture(scope="module")
def test_server():
    """Start/stop the test server for the module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _create_asset(client: httpx.AsyncClient, tag: str, currency: str = "USD") -> tuple[int, str]:
    """Create an asset; return ``(asset_id, display_name)``."""
    display_name = f"Export Test {unique_id(tag)}"
    item = FAAssetCreateItem(display_name=display_name, currency=currency)
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), f"create asset failed: {resp.status_code} {resp.text}"
    data = FABulkAssetCreateResponse(**resp.json())
    return data.results[0].asset_id, display_name


async def _upsert_prices(client: httpx.AsyncClient, asset_id: int, points: list[FAPricePoint]) -> None:
    payload = FAUpsert(asset_id=asset_id, prices=points)
    resp = await client.post(
        f"{API_BASE}/assets/prices",
        json=[payload.model_dump(mode="json")],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"upsert failed: {resp.status_code} {resp.text}"


async def _query_prices(client: httpx.AsyncClient, asset_id: int, start: date, end: date) -> list[dict]:
    resp = await client.post(
        f"{API_BASE}/assets/prices/query",
        json=[{"asset_id": asset_id, "date_range": {"start": start.isoformat(), "end": end.isoformat()}}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"query failed: {resp.status_code} {resp.text}"
    items = resp.json().get("items", [])
    assert items, "query returned no items"
    return items[0].get("prices", [])


def _sample_points(start: date, count: int, *, base: Decimal = Decimal("100.00")) -> list[FAPricePoint]:
    """Build ``count`` FAPricePoints with deterministic OHLC."""
    out: list[FAPricePoint] = []
    for i in range(count):
        d = start + timedelta(days=i)
        close = base + Decimal(i)
        out.append(
            FAPricePoint(
                date=d,
                open=close - Decimal("0.50"),
                high=close + Decimal("0.75"),
                low=close - Decimal("1.00"),
                close=close,
                volume=Decimal(1000 + i * 10),
            )
        )
    return out


# ============================================================================
# Tests — G.11
# ============================================================================


@pytest.mark.asyncio
async def test_export_csv_shape_and_headers(test_server):
    """CSV export: text/csv, ``;`` delimiter, fixed columns, attachment filename."""
    print_section("G.11.1 — CSV export shape + headers")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id, _ = await _create_asset(client, "G11.1")
        start = date.today() - timedelta(days=5)
        await _upsert_prices(client, asset_id, _sample_points(start, 3))

        resp = await client.get(
            f"{API_BASE}/backup/asset/{asset_id}/prices",
            params={"format": "csv"},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("text/csv"), resp.headers["content-type"]
        disp = resp.headers.get("content-disposition", "")
        assert "attachment" in disp and "prices_" in disp and disp.endswith('.csv"'), disp

        body = resp.text
        reader = csv.reader(io.StringIO(body), delimiter=";")
        rows = list(reader)
        assert rows, "CSV body is empty"
        assert rows[0] == PRICE_COLUMNS, f"header mismatch: {rows[0]} != {PRICE_COLUMNS}"
        # 3 data rows (header excluded)
        data_rows = rows[1:]
        assert len(data_rows) == 3, f"expected 3 data rows, got {len(data_rows)}"
        # Dates are ISO-8601 in column 0, close values coincide with the seed.
        assert data_rows[0][0] == start.isoformat()
        assert Decimal(data_rows[0][4]) == Decimal("100.00")
        print_success(f"CSV export: {len(data_rows)} rows, delimiter ';', columns ok")


@pytest.mark.asyncio
async def test_export_json_envelope(test_server):
    """JSON export: uniform envelope + ``row_count`` + ``entity.currency``."""
    print_section("G.11.2 — JSON export envelope")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id, _ = await _create_asset(client, "G11.2", currency="EUR")
        start = date.today() - timedelta(days=3)
        await _upsert_prices(client, asset_id, _sample_points(start, 2))

        resp = await client.get(
            f"{API_BASE}/backup/asset/{asset_id}/prices",
            params={"format": "json"},
            timeout=TIMEOUT,
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("application/json")
        payload = json.loads(resp.text)
        assert payload["scope"] == "prices"
        assert payload["entity"]["type"] == "asset"
        assert payload["entity"]["id"] == asset_id
        assert payload["entity"]["currency"] == "EUR"
        assert payload["row_count"] == 2
        assert "exported_at" in payload
        assert len(payload["rows"]) == 2
        # Decimal values are serialised as strings.
        first = payload["rows"][0]
        assert first["date"] == start.isoformat()
        # Decimals are rendered as strings at full DB scale; compare by value.
        assert Decimal(first["close"]) == Decimal("100.00")
        print_success("JSON envelope complete: scope/entity/row_count/rows")


@pytest.mark.asyncio
async def test_export_unknown_asset_returns_404(test_server):
    """404 Not Found for a non-existent asset id."""
    print_section("G.11.3 — unknown asset → 404")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        resp = await client.get(f"{API_BASE}/backup/asset/999999999/prices", timeout=TIMEOUT)
        assert resp.status_code == 404, resp.text
        print_success("Unknown asset correctly returns 404")


@pytest.mark.asyncio
async def test_export_empty_history(test_server):
    """Asset with zero prices → CSV has header only, JSON has ``row_count=0``."""
    print_section("G.11.4 — empty price history")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id, _ = await _create_asset(client, "G11.4")

        csv_resp = await client.get(
            f"{API_BASE}/backup/asset/{asset_id}/prices",
            params={"format": "csv"},
            timeout=TIMEOUT,
        )
        assert csv_resp.status_code == 200
        rows = list(csv.reader(io.StringIO(csv_resp.text), delimiter=";"))
        assert rows[0] == PRICE_COLUMNS
        assert len(rows) == 1, f"expected header-only CSV, got {len(rows)} rows"

        json_resp = await client.get(
            f"{API_BASE}/backup/asset/{asset_id}/prices",
            params={"format": "json"},
            timeout=TIMEOUT,
        )
        assert json_resp.status_code == 200
        payload = json.loads(json_resp.text)
        assert payload["row_count"] == 0
        assert payload["rows"] == []
        print_success("Empty history: CSV header-only + JSON row_count=0")


@pytest.mark.asyncio
async def test_export_csv_round_trip(test_server):
    """I-bis #5 round-trip: export CSV → parse → re-upsert → prices match."""
    print_section("G.11.5 — CSV export → import round-trip (I-bis #5)")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        src_id, _ = await _create_asset(client, "G11.5-src")
        start = date.today() - timedelta(days=10)
        original = _sample_points(start, 4)
        await _upsert_prices(client, src_id, original)

        export_resp = await client.get(
            f"{API_BASE}/backup/asset/{src_id}/prices",
            params={"format": "csv"},
            timeout=TIMEOUT,
        )
        assert export_resp.status_code == 200
        csv_body = export_resp.text

        # Parse the exported CSV, ignoring the extra canary columns
        # (``currency``, ``source_plugin_key``, ``fetched_at``) — mirrors
        # the frontend CsvEditor tolerance introduced in I-bis #5.
        reader = csv.DictReader(io.StringIO(csv_body), delimiter=";")
        reimported_points: list[FAPricePoint] = []
        for row in reader:
            reimported_points.append(
                FAPricePoint(
                    date=date.fromisoformat(row["date"]),
                    open=Decimal(row["open"]) if row.get("open") else None,
                    high=Decimal(row["high"]) if row.get("high") else None,
                    low=Decimal(row["low"]) if row.get("low") else None,
                    close=Decimal(row["close"]),
                    volume=Decimal(row["volume"]) if row.get("volume") else None,
                )
            )
        assert len(reimported_points) == 4, "expected 4 rows from round-trip"

        # Re-upsert on a DIFFERENT asset (same currency so no I.2 mismatch).
        dst_id, _ = await _create_asset(client, "G11.5-dst")
        await _upsert_prices(client, dst_id, reimported_points)

        # Query both and compare OHLC tuples.
        src_prices = await _query_prices(client, src_id, start, start + timedelta(days=3))
        dst_prices = await _query_prices(client, dst_id, start, start + timedelta(days=3))
        assert len(src_prices) == len(dst_prices) == 4

        def _key(p: dict) -> tuple:
            return (p["date"], Decimal(p["open"]), Decimal(p["high"]), Decimal(p["low"]), Decimal(p["close"]))

        src_sorted = sorted(src_prices, key=lambda p: p["date"])
        dst_sorted = sorted(dst_prices, key=lambda p: p["date"])
        for s, d in zip(src_sorted, dst_sorted, strict=True):
            assert _key(s) == _key(d), f"round-trip mismatch: {s} vs {d}"
        print_info(f"Round-trip verified for {len(src_sorted)} price rows")
        print_success("CSV export → re-import → OHLC integrity preserved")


