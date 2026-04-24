"""
Test Suite: Prices Currency Coherence (I.2 Hard-Reject)

Covers Phase 7 Part 3 Blocco G.5 + I.2 (Supersedes E.3).

Contract under test — ``POST /api/v1/assets/prices`` (bulk upsert):

- If any ``FAPricePoint.currency`` differs from ``asset.currency`` the
  whole upsert for that asset **must** fail with HTTP 400 (no soft-skip,
  no partial success). The service raises ``ValueError`` which the
  router translates; the 400 body includes the offending date(s) so
  the frontend can surface them.
- When ``FAPricePoint.currency`` is omitted or matches ``asset.currency``
  the upsert proceeds normally.
- Behaviour is atomic per-asset: a single bad point blocks all points
  of the same ``FAUpsert`` item — DB must show zero rows inserted.

See ``backend/app/services/asset_source.py::bulk_upsert_prices`` L1336+
("I.2 — Currency coherence validation").

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G.5.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets import FAAssetCreateItem, FABulkAssetCreateResponse
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


async def _create_asset(client: httpx.AsyncClient, tag: str, currency: str = "USD") -> int:
    item = FAAssetCreateItem(display_name=f"G5 {unique_id(tag)}", currency=currency)
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    return FABulkAssetCreateResponse(**resp.json()).results[0].asset_id


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


async def _query_prices(client: httpx.AsyncClient, asset_id: int, start: date, end: date) -> list[dict]:
    resp = await client.post(
        f"{API_BASE}/assets/prices/query",
        json=[{"asset_id": asset_id, "date_range": {"start": start.isoformat(), "end": end.isoformat()}}],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text
    items = resp.json().get("items", [])
    return items[0].get("prices", []) if items else []


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_upsert_rejects_single_mismatched_currency(test_server):
    """Single EUR point against USD asset → 400 with the offending date."""
    print_section("G.5.1 — single mismatch → 400")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G5.1", currency="USD")
        d0 = date.today() - timedelta(days=1)

        resp = await _upsert(client, asset_id, [_point(d0, currency="EUR")])
        assert resp.status_code == 400, f"expected 400, got {resp.status_code}: {resp.text}"
        detail = resp.json().get("detail", "")
        assert "Currency mismatch" in detail, detail
        assert "USD" in detail and "EUR" in detail, detail
        assert d0.isoformat() in detail, detail
        print_success(f"Rejected with 400: {detail[:120]}")


@pytest.mark.asyncio
async def test_upsert_rejects_mixed_batch_atomically(test_server):
    """One bad point in a batch of 3 → whole batch rejected, DB stays empty."""
    print_section("G.5.2 — atomic reject on mixed batch")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G5.2", currency="USD")
        d0 = date.today() - timedelta(days=3)
        points = [
            _point(d0 + timedelta(days=0), currency="USD"),
            _point(d0 + timedelta(days=1), currency="GBP"),  # offender
            _point(d0 + timedelta(days=2), currency="USD"),
        ]

        resp = await _upsert(client, asset_id, points)
        assert resp.status_code == 400, resp.text
        detail = resp.json().get("detail", "")
        assert "GBP" in detail, detail

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
async def test_upsert_reports_many_offending_dates_with_ellipsis(test_server):
    """>10 bad dates → error message truncates with ``+ N more`` suffix."""
    print_section("G.5.5 — many offending dates truncated in message")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G5.5", currency="USD")
        d0 = date.today() - timedelta(days=15)
        points = [_point(d0 + timedelta(days=i), currency="CHF") for i in range(12)]

        resp = await _upsert(client, asset_id, points)
        assert resp.status_code == 400, resp.text
        detail = resp.json().get("detail", "")
        assert "CHF" in detail
        assert "more" in detail or "+ 2 more" in detail, f"expected truncation hint, got: {detail}"
        print_success("Large mismatch batch truncated with ellipsis")

