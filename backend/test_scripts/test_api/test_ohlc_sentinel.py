"""
Test Suite: OHLC Sentinel Semantics (F.4) + Close Required

Covers Phase 7 Part 3 Blocco F.4 — upsert sentinel rules on PriceHistory:

- ``None`` / omitted → no-op: existing DB value is preserved (partial merge).
- ``-1``             → SET NULL on the DB column.
- ``>= 0``           → write the provided value.

``close`` is always required and is NOT affected by the sentinel (use the
DELETE endpoint to clear a row; ``-1`` on close is meaningless).

Endpoint under test: ``POST /api/v1/assets/prices`` (bulk upsert).

Spec: ``backend/app/schemas/prices.py::FAPricePoint`` docstring +
      ``backend/app/services/asset_source.py::_merge_field`` (L1367+).

Related plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md``
              §G.6 (G-batch1).
"""

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets import FAAssetCreateItem, FABulkAssetCreateResponse
from backend.app.schemas.prices import FABulkUpsertResponse, FAPricePoint, FAUpsert
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
    """Start/stop test server for the whole module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _create_asset(client: httpx.AsyncClient, tag: str, currency: str = "USD") -> int:
    """Create a test asset and return its id."""
    item = FAAssetCreateItem(display_name=f"Sentinel Test {unique_id(tag)}", currency=currency)
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), f"create asset failed: {resp.status_code} {resp.text}"
    data = FABulkAssetCreateResponse(**resp.json())
    return data.results[0].asset_id


async def _upsert_prices(client: httpx.AsyncClient, asset_id: int, points: list[FAPricePoint]) -> FABulkUpsertResponse:
    """Call POST /assets/prices with a single FAUpsert payload."""
    payload = FAUpsert(asset_id=asset_id, prices=points)
    resp = await client.post(
        f"{API_BASE}/assets/prices",
        json=[payload.model_dump(mode="json")],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"upsert failed: {resp.status_code} {resp.text}"
    return FABulkUpsertResponse(**resp.json())


async def _query_prices(client: httpx.AsyncClient, asset_id: int, start: date, end: date) -> list[dict]:
    """Query price history and return the raw ``prices`` list from items[0]."""
    resp = await client.post(
        f"{API_BASE}/assets/prices/query",
        json=[
            {
                "asset_id": asset_id,
                "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            }
        ],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"query failed: {resp.status_code} {resp.text}"
    items = resp.json().get("items", [])
    assert items, "query returned no items"
    return items[0].get("prices", [])


def _get_point_by_date(points: list[dict], target: date) -> dict:
    iso = target.isoformat()
    for p in points:
        if p.get("date") == iso:
            return p
    raise AssertionError(f"date {iso} not found in {[p.get('date') for p in points]}")


# ============================================================================
# G.6.1 — sentinel -1 sets NULL on open
# ============================================================================
@pytest.mark.asyncio
async def test_sentinel_minus_one_sets_null_on_open(test_server):
    """-1 on ``open`` for an existing row → DB stores NULL (None in response)."""
    print_section("G.6.1 — sentinel -1 clears open to NULL")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G61")
        d = date.today() - timedelta(days=5)

        # Seed: write open=50, close=100
        await _upsert_prices(
            client,
            asset_id,
            [FAPricePoint(date=d, open=Decimal("50"), close=Decimal("100"))],
        )
        points = await _query_prices(client, asset_id, d, d)
        seed = _get_point_by_date(points, d)
        assert Decimal(str(seed["open"])) == Decimal("50"), f"seed open should be 50, got {seed['open']}"
        print_info(f"seeded open={seed['open']}")

        # Sentinel: open=-1 → SET NULL
        await _upsert_prices(
            client,
            asset_id,
            [FAPricePoint(date=d, open=Decimal("-1"), close=Decimal("100"))],
        )
        points = await _query_prices(client, asset_id, d, d)
        after = _get_point_by_date(points, d)
        assert after["open"] is None, f"open should be NULL after -1 sentinel, got {after['open']}"
        # Close not touched by sentinel rules
        assert Decimal(str(after["close"])) == Decimal("100"), "close must stay 100"
        print_success("open cleared to NULL via -1 sentinel; close preserved")


# ============================================================================
# G.6.2 — None preserves existing value (no-op)
# ============================================================================
@pytest.mark.asyncio
async def test_none_preserves_existing_open(test_server):
    """``open`` omitted on a subsequent upsert → existing DB value preserved."""
    print_section("G.6.2 — None/omitted field is a no-op (preserves existing)")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G62")
        d = date.today() - timedelta(days=4)

        # Seed: open=42.5, close=99
        await _upsert_prices(
            client,
            asset_id,
            [FAPricePoint(date=d, open=Decimal("42.5"), close=Decimal("99"))],
        )

        # Second upsert: same date, only close changes, open omitted (None)
        await _upsert_prices(
            client,
            asset_id,
            [FAPricePoint(date=d, close=Decimal("123"))],
        )

        points = await _query_prices(client, asset_id, d, d)
        after = _get_point_by_date(points, d)
        assert Decimal(str(after["open"])) == Decimal("42.5"), f"open should be preserved at 42.5 (None=no-op), got {after['open']}"
        assert Decimal(str(after["close"])) == Decimal("123"), f"close should be updated to 123, got {after['close']}"
        print_success("open preserved across upsert with omitted field; close updated")


# ============================================================================
# G.6.3 — explicit value overwrites existing
# ============================================================================
@pytest.mark.asyncio
async def test_value_overwrites_existing_high(test_server):
    """Explicit non-negative value on ``high`` overwrites the existing one."""
    print_section("G.6.3 — explicit value overwrites existing")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G63")
        d = date.today() - timedelta(days=3)

        await _upsert_prices(
            client,
            asset_id,
            [FAPricePoint(date=d, high=Decimal("100"), close=Decimal("95"))],
        )
        await _upsert_prices(
            client,
            asset_id,
            [FAPricePoint(date=d, high=Decimal("200"), close=Decimal("95"))],
        )

        points = await _query_prices(client, asset_id, d, d)
        after = _get_point_by_date(points, d)
        assert Decimal(str(after["high"])) == Decimal("200"), f"high should be overwritten to 200, got {after['high']}"
        print_success("high overwritten to 200")


# ============================================================================
# G.6.4 — close is required (Pydantic validation)
# ============================================================================
@pytest.mark.asyncio
async def test_close_is_required(test_server):
    """Omitting ``close`` yields 422 from Pydantic (not 200, not 400)."""
    print_section("G.6.4 — close is required, not affected by sentinel")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G64")

        # Build raw payload with close missing — Pydantic must reject.
        bad_payload = [
            {
                "asset_id": asset_id,
                "prices": [{"date": date.today().isoformat(), "open": "10"}],
            }
        ]
        resp = await client.post(f"{API_BASE}/assets/prices", json=bad_payload, timeout=TIMEOUT)
        assert resp.status_code == 422, f"missing close should raise 422 (Pydantic validation), got {resp.status_code}: {resp.text}"
        print_success(f"missing close rejected with 422 (Pydantic); body: {resp.text[:120]}")


# ============================================================================
# G.6.5 — new row with only close keeps OHLC auxiliary fields NULL
# ============================================================================
@pytest.mark.asyncio
async def test_new_row_without_ohlc_keeps_null(test_server):
    """A brand-new date upsert with only ``close`` → open/high/low/volume stay NULL."""
    print_section("G.6.5 — new row with only close keeps auxiliary fields NULL")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G65")
        d = date.today() - timedelta(days=2)

        await _upsert_prices(client, asset_id, [FAPricePoint(date=d, close=Decimal("77"))])

        points = await _query_prices(client, asset_id, d, d)
        p = _get_point_by_date(points, d)
        assert p["open"] is None, f"open should be NULL, got {p['open']}"
        assert p["high"] is None, f"high should be NULL, got {p['high']}"
        assert p["low"] is None, f"low should be NULL, got {p['low']}"
        assert p["volume"] is None, f"volume should be NULL, got {p['volume']}"
        assert Decimal(str(p["close"])) == Decimal("77"), f"close should be 77, got {p['close']}"
        print_success("auxiliary OHLC fields NULL when only close is sent on a new date")


# ============================================================================
# G.6.6 — sentinel semantics on volume
# ============================================================================
@pytest.mark.asyncio
async def test_sentinel_minus_one_clears_volume(test_server):
    """Sentinel -1 also works on ``volume``."""
    print_section("G.6.6 — sentinel -1 clears volume to NULL")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G66")
        d = date.today() - timedelta(days=1)

        await _upsert_prices(
            client,
            asset_id,
            [FAPricePoint(date=d, close=Decimal("50"), volume=Decimal("1234"))],
        )
        points = await _query_prices(client, asset_id, d, d)
        assert Decimal(str(_get_point_by_date(points, d)["volume"])) == Decimal("1234")

        await _upsert_prices(
            client,
            asset_id,
            [FAPricePoint(date=d, close=Decimal("50"), volume=Decimal("-1"))],
        )
        points = await _query_prices(client, asset_id, d, d)
        p = _get_point_by_date(points, d)
        assert p["volume"] is None, f"volume should be NULL after -1, got {p['volume']}"
        print_success("volume cleared to NULL via -1 sentinel")


# ============================================================================
# G.6.7 — mixed sentinel / preserve / value in a single batch
# ============================================================================
@pytest.mark.asyncio
async def test_mixed_sentinel_in_batch(test_server):
    """A single batch with 3 points exercising all 3 branches on ``low``:

    - day1: low=-1  → SET NULL (was 10)
    - day2: low=None → preserve (stays 20)
    - day3: low=99  → overwrite (was 30)
    """
    print_section("G.6.7 — mixed sentinel/preserve/value in same batch")

    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G67")
        d1 = date.today() - timedelta(days=10)
        d2 = date.today() - timedelta(days=9)
        d3 = date.today() - timedelta(days=8)

        # Seed: low values 10/20/30 on three consecutive days.
        await _upsert_prices(
            client,
            asset_id,
            [
                FAPricePoint(date=d1, close=Decimal("100"), low=Decimal("10")),
                FAPricePoint(date=d2, close=Decimal("100"), low=Decimal("20")),
                FAPricePoint(date=d3, close=Decimal("100"), low=Decimal("30")),
            ],
        )

        # Batch: sentinel / omit / value (close unchanged, just to satisfy required).
        await _upsert_prices(
            client,
            asset_id,
            [
                FAPricePoint(date=d1, close=Decimal("100"), low=Decimal("-1")),
                FAPricePoint(date=d2, close=Decimal("100")),  # low omitted → preserve
                FAPricePoint(date=d3, close=Decimal("100"), low=Decimal("99")),
            ],
        )

        points = await _query_prices(client, asset_id, d1, d3)
        p1 = _get_point_by_date(points, d1)
        p2 = _get_point_by_date(points, d2)
        p3 = _get_point_by_date(points, d3)

        assert p1["low"] is None, f"day1 low should be NULL (-1 sentinel), got {p1['low']}"
        assert Decimal(str(p2["low"])) == Decimal("20"), f"day2 low should be preserved at 20 (None=no-op), got {p2['low']}"
        assert Decimal(str(p3["low"])) == Decimal("99"), f"day3 low should be overwritten to 99, got {p3['low']}"
        print_success("all three sentinel branches behave correctly in a single batch")
