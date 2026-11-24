"""
Test Suite: POST /api/v1/assets/prices/reward-values (project 79, STK-4b)

The value on receipt of rewards in kind, read from the stored price history through the real server: what the
transaction form's suggestion (STK-2a) and the bulk workspace's «fill from price history» (STK-4b) ask.

The contract, per item, in the order asked:

- ``FILLED`` with ``value`` = the asset's close of THAT very day divided by its quote base quantity, in the price's own
  currency;
- ``NO_PRICE_THAT_DAY`` when the asset has a stored history but no close on that day — never the day before or after:
  the gap day used here has a close on the day before AND the day after, so a backward or forward fill would answer;
- ``NO_HISTORY`` when the asset has no stored price at all, or does not exist;
- more than 1 000 items → 422 ``bulk_too_many_items`` before any read; no session → 401.

The service itself, its rounding and the rows the upsert route refuses (a close of 0, a currency other than the asset's)
are pinned without a server by ``test_services/test_reward_values.py``.

Isolation: WRITE_SCOPED — each test registers its own user and creates its own assets (unique names) and their prices,
and deletes the assets (their prices go with them) in ``finally``. The unknown asset is an id far above any a lane holds.
"""

import time
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import httpx
import pytest

from backend.app.config import get_settings
from backend.app.schemas.assets.assets import FAAssetCreateItem, FABulkAssetCreateResponse
from backend.app.schemas.prices import FAPricePoint, FAUpsert
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
REWARD_VALUES = f"{API_BASE}/assets/prices/reward-values"
TIMEOUT = 30.0

BULK_MAX_ITEMS = 1_000  # the contract's number (N77), written here and not read from the code under test
FAR_AWAY_ASSET_ID = 987_654_321  # an id far above any a lane's database holds

D1 = date(2024, 3, 4)  # a close
D2 = date(2024, 3, 5)  # no close: between D1 and D3
D3 = date(2024, 3, 6)  # a close


async def create_user_and_login(client: httpx.AsyncClient) -> None:
    """Create a test user, login, and set session cookie on client."""
    username = f"test_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"
    resp = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"}, timeout=TIMEOUT)
    assert resp.status_code == 201, f"register: {resp.status_code} {resp.text}"
    login_resp = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": "TestPass123!"}, timeout=TIMEOUT)
    assert login_resp.status_code == 200, f"login: {login_resp.status_code} {login_resp.text}"
    session = login_resp.cookies.get("session")
    if session:
        client.cookies.set("session", session)


@pytest.fixture(scope="module")
def test_server():
    """Attach to (or start) the test server for the tests of this module."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


async def _create_asset(client: httpx.AsyncClient, owned: list[int], label: str, quote_base: int = 1, currency: str = "EUR") -> int:
    """An asset of this test alone; its id is recorded for cleanup before anything about it is checked."""
    item = FAAssetCreateItem(display_name=f"Reward value {label} {unique_id('RV')}", currency=currency, quote_base_quantity=quote_base)
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code == 201, resp.text
    (result,) = FABulkAssetCreateResponse(**resp.json()).results
    if result.asset_id is not None:
        owned.append(result.asset_id)
    assert result.success and result.asset_id is not None, f"the asset was not created: {result}"
    return result.asset_id


async def _store_closes(client: httpx.AsyncClient, asset_id: int, closes: dict[date, str], currency: str = "EUR") -> None:
    prices = [FAPricePoint(date=day, close=Decimal(close), currency=currency) for day, close in closes.items()]
    resp = await client.post(f"{API_BASE}/assets/prices", json=[FAUpsert(asset_id=asset_id, prices=prices).model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text


async def _stored_days(client: httpx.AsyncClient, asset_id: int, start: date, end: date) -> dict[str, Decimal]:
    """The closes STORED for the asset in [start, end] (no backward fill: only the rows the history holds)."""
    resp = await client.post(f"{API_BASE}/assets/prices/query", json=[{"asset_id": asset_id, "date_range": {"start": start.isoformat(), "end": end.isoformat()}}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    item = next(i for i in resp.json()["items"] if i["asset_id"] == asset_id)
    return {point["date"]: Decimal(str(point["close"])) for point in item["prices"] if not point.get("backward_fill_info")}


async def _delete_assets(client: httpx.AsyncClient, owned: list[int]) -> None:
    for asset_id in owned:
        await client.delete(f"{API_BASE}/assets", params={"asset_ids": [asset_id]}, timeout=TIMEOUT)


async def _ask(client: httpx.AsyncClient, pairs: list[tuple[int, date]]) -> list[dict]:
    resp = await client.post(REWARD_VALUES, json=[{"asset_id": asset_id, "date": day.isoformat()} for asset_id, day in pairs], timeout=TIMEOUT)
    assert resp.status_code == 200, f"{resp.status_code}: {resp.text[:300]}"
    items = resp.json()["items"]
    assert len(items) == len(pairs), f"one result per item asked: {len(items)} for {len(pairs)}"
    return items


def _shape(item: dict) -> tuple[int, str, str, Optional[str], Optional[Decimal]]:
    value = item.get("value")
    return (item["asset_id"], item["date"], item["status"], value["code"] if value else None, Decimal(str(value["amount"])) if value else None)


@pytest.mark.asyncio
async def test_the_close_of_that_very_day_is_filled(test_server):
    """D1 has a close: FILLED, its value the close itself (quote base 1), in the price's currency."""
    print_section("STK-4b: reward value on a day with a close")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        owned: list[int] = []
        try:
            asset_id = await _create_asset(client, owned, "filled")
            await _store_closes(client, asset_id, {D1: "61.25", D3: "70"})

            (item,) = await _ask(client, [(asset_id, D1)])

            assert _shape(item) == (asset_id, D1.isoformat(), "FILLED", "EUR", Decimal("61.25")), item
            print_success(f"  ✓ {item['status']} {item['value']}")
        finally:
            await _delete_assets(client, owned)


@pytest.mark.asyncio
async def test_a_gap_day_is_no_price_never_a_fill(test_server):
    """D2 has no close, but D1 before it and D3 after it do (proved by reading the stored rows back): a backward or forward
    fill would answer 61.25 or 70. The answer is NO_PRICE_THAT_DAY, with no value."""
    print_section("STK-4b: reward value on a gap day")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        owned: list[int] = []
        try:
            asset_id = await _create_asset(client, owned, "gap")
            await _store_closes(client, asset_id, {D1: "61.25", D3: "70"})
            stored = await _stored_days(client, asset_id, D1, D3)
            assert stored == {D1.isoformat(): Decimal("61.25"), D3.isoformat(): Decimal("70")}, f"precondition: closes on D1 and D3 only, none on D2: {stored}"

            (item,) = await _ask(client, [(asset_id, D2)])

            assert _shape(item) == (asset_id, D2.isoformat(), "NO_PRICE_THAT_DAY", None, None), item
            print_success("  ✓ NO_PRICE_THAT_DAY between two closes")
        finally:
            await _delete_assets(client, owned)


@pytest.mark.asyncio
async def test_an_asset_without_any_price_is_no_history(test_server):
    print_section("STK-4b: reward value of an asset with no stored price")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        owned: list[int] = []
        try:
            asset_id = await _create_asset(client, owned, "no history")

            (item,) = await _ask(client, [(asset_id, D1)])

            assert _shape(item) == (asset_id, D1.isoformat(), "NO_HISTORY", None, None), item
        finally:
            await _delete_assets(client, owned)


@pytest.mark.asyncio
async def test_an_unknown_asset_is_no_history(test_server):
    print_section("STK-4b: reward value of an unknown asset")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)

        (item,) = await _ask(client, [(FAR_AWAY_ASSET_ID, D1)])

        assert _shape(item) == (FAR_AWAY_ASSET_ID, D1.isoformat(), "NO_HISTORY", None, None), item


@pytest.mark.asyncio
async def test_a_quote_base_of_100_divides_the_close(test_server):
    """A bond quoted per 100: a close of 98.5 is 0.985 per unit."""
    print_section("STK-4b: reward value of an asset quoted per 100")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        owned: list[int] = []
        try:
            bond_id = await _create_asset(client, owned, "bond", quote_base=100)
            await _store_closes(client, bond_id, {D1: "98.5"})

            (item,) = await _ask(client, [(bond_id, D1)])

            assert _shape(item) == (bond_id, D1.isoformat(), "FILLED", "EUR", Decimal("0.985")), item
        finally:
            await _delete_assets(client, owned)


@pytest.mark.asyncio
async def test_results_come_in_the_order_asked(test_server):
    """Mixed statuses and assets, a repeated item answered twice, each result at the position of its item."""
    print_section("STK-4b: reward values in the order asked")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        owned: list[int] = []
        try:
            priced = await _create_asset(client, owned, "order priced", currency="USD")
            bond = await _create_asset(client, owned, "order bond", quote_base=100)
            empty = await _create_asset(client, owned, "order empty")
            await _store_closes(client, priced, {D1: "10", D3: "30"}, currency="USD")
            await _store_closes(client, bond, {D2: "99"})

            items = await _ask(client, [(empty, D1), (priced, D3), (FAR_AWAY_ASSET_ID, D2), (bond, D2), (priced, D2), (priced, D3), (bond, D1)])

            assert [_shape(item) for item in items] == [
                (empty, D1.isoformat(), "NO_HISTORY", None, None),
                (priced, D3.isoformat(), "FILLED", "USD", Decimal("30")),
                (FAR_AWAY_ASSET_ID, D2.isoformat(), "NO_HISTORY", None, None),
                (bond, D2.isoformat(), "FILLED", "EUR", Decimal("0.99")),
                (priced, D2.isoformat(), "NO_PRICE_THAT_DAY", None, None),
                (priced, D3.isoformat(), "FILLED", "USD", Decimal("30")),
                (bond, D1.isoformat(), "NO_PRICE_THAT_DAY", None, None),
            ]
        finally:
            await _delete_assets(client, owned)


@pytest.mark.asyncio
async def test_more_than_1000_items_is_refused(test_server):
    """1 001 items answer 422 ``{"code": "bulk_too_many_items", "message", "max_items": 1000, "items": 1001}``, before any read."""
    print_section("STK-4b: 1 001 reward values refused")
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        body = [{"asset_id": FAR_AWAY_ASSET_ID, "date": D1.isoformat()} for _ in range(BULK_MAX_ITEMS + 1)]
        resp = await client.post(REWARD_VALUES, json=body, timeout=TIMEOUT)

        assert resp.status_code == 422, f"{resp.status_code}: {resp.text[:300]}"
        detail = resp.json()["detail"]
        assert isinstance(detail, dict) and detail.get("code") == "bulk_too_many_items", detail
        assert isinstance(detail.get("message"), str) and detail["message"].strip(), detail
        assert {key: value for key, value in detail.items() if key not in ("code", "message")} == {"max_items": BULK_MAX_ITEMS, "items": BULK_MAX_ITEMS + 1}


@pytest.mark.asyncio
async def test_without_a_session_is_refused(test_server):
    async with httpx.AsyncClient() as client:
        resp = await client.post(REWARD_VALUES, json=[{"asset_id": FAR_AWAY_ASSET_ID, "date": (D1 + timedelta(days=1)).isoformat()}], timeout=TIMEOUT)

        assert resp.status_code == 401, f"{resp.status_code}: {resp.text[:300]}"
