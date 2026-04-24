"""
Test Suite: Asset Currency Change Flow (I.3 + I-bis #7)

Covers Phase 7 Part 3 Blocco G.10.

Contract under test — ``PATCH /api/v1/assets`` with ``currency`` field:

**Policy D (R3-3)**: changing the currency of an asset that still owns any
price/event row is destructive — the stored values are in the *old*
currency and cannot be silently reinterpreted. The backend therefore
refuses the patch and emits a structured error token
``CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|prices=N|...|from=X|to=Y``
inside the per-item ``message``.

**I-bis #7** — when *every* item in the batch is blocked for this same
reason (``success_count == 0`` AND each failure carries the token), the
endpoint elevates the HTTP status from the default bulk 200 to **HTTP
409 Conflict** so clients can distinguish "nothing happened (conflict)"
from a normal partial-success 200. Body:

    {
      "detail": {
        "error_code": "CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA",
        "message": "All assets in the batch are blocked …",
        "results": [ ... per-item FAAssetPatchResult ... ]
      }
    }

Happy path (Policy D flow):

1. ``DELETE /assets/prices`` (bulk) to wipe all prices for the asset.
2. ``PATCH /assets`` with the new currency → 200.
3. Optionally re-sync from the provider.

This test does not exercise the re-sync leg (mockprov-based sync is
already covered by ``test_prices_sync_delta.py``). We verify:

- G.10.1 PATCH with prices → 409 + token parsable.
- G.10.2 wipe + PATCH → 200 + asset has the new currency.
- G.10.3 mixed batch (one blocked, one free) → 200 with one success,
  one failure, **no** 409 promotion.
- G.10.4 idempotent same-currency PATCH is never blocked.

Plan: ``plan-phase07-transaction-Part3_1_Closure_2-BlockG.prompt.md`` §G.10.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets import (
    FAAssetCreateItem,
    FAAssetPatchItem,
    FABulkAssetCreateResponse,
)
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
    item = FAAssetCreateItem(display_name=f"G10 {unique_id(tag)}", currency=currency)
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    return FABulkAssetCreateResponse(**resp.json()).results[0].asset_id


async def _seed_prices(client: httpx.AsyncClient, asset_id: int, start: date, count: int) -> None:
    points = [
        FAPricePoint(date=start + timedelta(days=i), close=Decimal("100.00") + Decimal(i))
        for i in range(count)
    ]
    payload = FAUpsert(asset_id=asset_id, prices=points)
    resp = await client.post(
        f"{API_BASE}/assets/prices",
        json=[payload.model_dump(mode="json")],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, resp.text


async def _wipe_prices(client: httpx.AsyncClient, asset_id: int, start: date, end: date) -> None:
    resp = await client.request(
        "DELETE",
        f"{API_BASE}/assets/prices",
        json=[
            {
                "asset_id": asset_id,
                "date_ranges": [{"start": start.isoformat(), "end": end.isoformat()}],
            }
        ],
        timeout=TIMEOUT,
    )
    assert resp.status_code == 200, f"wipe failed: {resp.status_code} {resp.text}"


async def _patch_currency(client: httpx.AsyncClient, items: list[FAAssetPatchItem]) -> httpx.Response:
    return await client.patch(
        f"{API_BASE}/assets",
        json=[it.model_dump(mode="json", exclude_none=True) for it in items],
        timeout=TIMEOUT,
    )


async def _get_asset(client: httpx.AsyncClient, asset_id: int) -> dict:
    resp = await client.get(f"{API_BASE}/assets/all", timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    for a in resp.json():
        if a["id"] == asset_id:
            return a
    raise AssertionError(f"asset {asset_id} not in /assets/all")


def _parse_blocker_token(message: str) -> dict[str, str]:
    """Parse ``CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA|k=v|...`` token."""
    parts = message.split("|")
    assert parts[0] == "CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA", message
    kv: dict[str, str] = {}
    for part in parts[1:]:
        if "=" in part:
            k, v = part.split("=", 1)
            kv[k] = v
    return kv


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_currency_change_blocked_returns_409_with_token(test_server):
    """Asset with prices → PATCH currency → 409 + parsable token."""
    print_section("G.10.1 — blocked currency change → 409 + token")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G10.1", currency="USD")
        start = date.today() - timedelta(days=4)
        await _seed_prices(client, asset_id, start, 3)

        resp = await _patch_currency(client, [FAAssetPatchItem(asset_id=asset_id, currency="EUR")])
        assert resp.status_code == 409, f"expected 409, got {resp.status_code}: {resp.text}"
        body = resp.json()
        detail = body.get("detail") or {}
        assert detail.get("error_code") == "CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA", body
        results = detail.get("results", [])
        assert len(results) == 1
        kv = _parse_blocker_token(results[0]["message"])
        assert kv["prices"] == "3", kv
        assert kv["from"] == "USD"
        assert kv["to"] == "EUR"
        assert kv["oldest"] == start.isoformat()
        assert kv["newest"] == (start + timedelta(days=2)).isoformat()
        print_success(f"409 with token parsed: prices={kv['prices']} from={kv['from']} to={kv['to']}")


@pytest.mark.asyncio
async def test_currency_change_succeeds_after_wipe(test_server):
    """Wipe prices → PATCH currency → 200 + asset currency updated."""
    print_section("G.10.2 — wipe + PATCH → 200 (Policy D happy path)")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G10.2", currency="USD")
        start = date.today() - timedelta(days=4)
        await _seed_prices(client, asset_id, start, 3)

        # Step 1 — confirm blocked before wipe (sanity).
        blocked = await _patch_currency(client, [FAAssetPatchItem(asset_id=asset_id, currency="EUR")])
        assert blocked.status_code == 409

        # Step 2 — wipe all prices.
        await _wipe_prices(client, asset_id, start, start + timedelta(days=10))
        print_info("Prices wiped")

        # Step 3 — PATCH currency → 200.
        ok = await _patch_currency(client, [FAAssetPatchItem(asset_id=asset_id, currency="EUR")])
        assert ok.status_code == 200, ok.text
        body = ok.json()
        assert body["success_count"] == 1, body
        assert body["results"][0]["success"] is True

        # Step 4 — verify asset.currency actually changed.
        asset = await _get_asset(client, asset_id)
        assert asset["currency"] == "EUR", asset
        print_success("Currency change succeeded after wipe: USD → EUR")


@pytest.mark.asyncio
async def test_mixed_batch_keeps_200_with_partial_success(test_server):
    """One asset blocked + one free → 200 (no 409 promotion), partial success."""
    print_section("G.10.3 — mixed batch stays 200 (I-bis #7 only when ALL fail)")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        # Asset A: has prices → will be blocked.
        a = await _create_asset(client, "G10.3-A", currency="USD")
        start = date.today() - timedelta(days=3)
        await _seed_prices(client, a, start, 2)
        # Asset B: no prices → PATCH should succeed.
        b = await _create_asset(client, "G10.3-B", currency="USD")

        resp = await _patch_currency(
            client,
            [
                FAAssetPatchItem(asset_id=a, currency="EUR"),
                FAAssetPatchItem(asset_id=b, currency="EUR"),
            ],
        )
        assert resp.status_code == 200, f"expected 200 (partial), got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["success_count"] == 1, body
        per_asset = {r["asset_id"]: r for r in body["results"]}
        assert per_asset[a]["success"] is False
        assert "CURRENCY_CHANGE_BLOCKED_BY_MARKET_DATA" in per_asset[a]["message"]
        assert per_asset[b]["success"] is True
        print_success("Partial-success 200: A blocked, B patched (no 409)")


@pytest.mark.asyncio
async def test_same_currency_patch_is_not_blocked(test_server):
    """PATCH currency == existing currency → not blocked (no-op change)."""
    print_section("G.10.4 — no-op same-currency PATCH passes")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        asset_id = await _create_asset(client, "G10.4", currency="USD")
        start = date.today() - timedelta(days=2)
        await _seed_prices(client, asset_id, start, 2)

        resp = await _patch_currency(client, [FAAssetPatchItem(asset_id=asset_id, currency="USD")])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success_count"] == 1, body
        assert body["results"][0]["success"] is True
        print_success("Same-currency PATCH accepted (no block)")

