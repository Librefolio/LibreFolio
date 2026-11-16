"""
Test Suite: POST /assets/validate (lane 65, lot B4)

The dry run of the asset PATCH: same payload, same service (``patch_assets_bulk``), but it never writes.

- the validate answer says what would happen, and a read after it finds every asset unchanged;
- a currency change under validate leaves the prices and the events intact (the wipe of N68 runs inside the dry run and
  is rolled back);
- validate returns the same issues and warnings as the PATCH of the same payload.

Isolation: each test creates its own user and its own assets (and broker) under unique names, addresses them by id, and
drops them at the end.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
import pytest_asyncio

from backend.app.config import get_settings
from backend.app.db.models import AssetType
from backend.app.schemas.assets.assets import (
    FAAssetCreateItem,
    FAAssetPatchItem,
    FABulkAssetCreateResponse,
    FABulkAssetPatchResponse,
)
from backend.app.schemas.prices import FAPricePoint, FAUpsert
from backend.test_scripts.test_api.test_asset_currency_change import _Owned, create_user_and_login
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section, print_success, unique_id

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
WIDE_RANGE = {"start": "2000-01-01", "end": (date.today() + timedelta(days=365)).isoformat()}


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as srv:
        if not srv.start_server():
            pytest.fail("Failed to start test server")
        yield srv


@pytest_asyncio.fixture
async def env(test_server):
    """A logged-in client and the collector of what the test creates; dropped after the test."""
    owned = _Owned()
    async with httpx.AsyncClient() as client:
        await create_user_and_login(client)
        yield client, owned
        problems = await owned.drop(client)
    assert not problems, problems


async def _create_asset(client: httpx.AsyncClient, owned: _Owned, tag: str, asset_type: AssetType = AssetType.STOCK, currency: str = "USD") -> tuple[int, str]:
    """One asset under a unique name; (id, name)."""
    name = f"B4 {tag} {unique_id(tag)}"
    item = FAAssetCreateItem(display_name=name, currency=currency, asset_type=asset_type)
    resp = await client.post(f"{API_BASE}/assets", json=[item.model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    asset_id = FABulkAssetCreateResponse(**resp.json()).results[0].asset_id
    owned.asset_ids.append(asset_id)
    return asset_id, name


async def _row_of(client: httpx.AsyncClient, asset_id: int) -> dict[str, Any]:
    """The asset as ``GET /assets/query`` lists it, whole (``updated_at`` included), found by id."""
    resp = await client.get(f"{API_BASE}/assets/query", timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    found = next((row for row in resp.json() if row["id"] == asset_id), None)
    assert found is not None, f"asset {asset_id} not listed by /assets/query"
    return found


def _payload(items: list[FAAssetPatchItem]) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json", exclude_unset=True) for item in items]


async def _validate(client: httpx.AsyncClient, items: list[FAAssetPatchItem]) -> FABulkAssetPatchResponse:
    resp = await client.post(f"{API_BASE}/assets/validate", json=_payload(items), timeout=TIMEOUT)
    assert resp.status_code == 200, f"validate: {resp.status_code}: {resp.text}"
    return FABulkAssetPatchResponse(**resp.json())


async def _patch(client: httpx.AsyncClient, items: list[FAAssetPatchItem]) -> FABulkAssetPatchResponse:
    resp = await client.patch(f"{API_BASE}/assets", json=_payload(items), timeout=TIMEOUT)
    assert resp.status_code == 200, f"patch: {resp.status_code}: {resp.text}"
    return FABulkAssetPatchResponse(**resp.json())


async def _seed_prices(client: httpx.AsyncClient, asset_id: int, start: date, count: int) -> None:
    points = [FAPricePoint(date=start + timedelta(days=i), close=Decimal("100.00") + Decimal(i)) for i in range(count)]
    resp = await client.post(f"{API_BASE}/assets/prices", json=[FAUpsert(asset_id=asset_id, prices=points).model_dump(mode="json")], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text


async def _seed_event(client: httpx.AsyncClient, asset_id: int, day: date, kind: str, amount: str, currency: str) -> None:
    resp = await client.post(f"{API_BASE}/assets/events", json=[{"asset_id": asset_id, "events": [{"date": day.isoformat(), "type": kind, "value": {"code": currency, "amount": amount}}]}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text


async def _events_of(client: httpx.AsyncClient, asset_id: int) -> list[dict[str, Any]]:
    resp = await client.post(f"{API_BASE}/assets/events/query", json=[{"asset_id": asset_id, "date_range": WIDE_RANGE}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return next(item for item in resp.json()["items"] if item["asset_id"] == asset_id)["events"]


async def _prices_of(client: httpx.AsyncClient, asset_id: int, start: date, count: int) -> list[dict[str, Any]]:
    """The stored prices of exactly the seeded range (a wider query is filled forward by the API)."""
    date_range = {"start": start.isoformat(), "end": (start + timedelta(days=count - 1)).isoformat()}
    resp = await client.post(f"{API_BASE}/assets/prices/query", json=[{"asset_id": asset_id, "date_range": date_range}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return next(item for item in resp.json()["items"] if item["asset_id"] == asset_id)["prices"]


def _issue_keys(data: FABulkAssetPatchResponse) -> tuple[list[tuple], list[tuple]]:
    """What a caller reads from the answer, without the message text: (issues, warnings)."""
    key = lambda i: (i.code.value, i.asset_id, i.index, i.field, i.params)  # noqa: E731 — local projection
    return [key(i) for i in data.issues], [key(w) for w in data.warnings]


@pytest.mark.asyncio
async def test_validate_never_writes(env):
    """B4.1 — red today: ``POST /assets/validate`` does not exist (405/404). Contract: a batch that PATCH would save is
    answered 200 with ``committed`` false, no issue, a success per item and the family warning; a read after it finds both
    assets exactly as they were (``updated_at`` included)."""
    print_section("B4.1 — validate never writes")
    client, owned = env
    id_a, _ = await _create_asset(client, owned, "WR-A", AssetType.CROWDFUND_REAL_ESTATE)
    id_b, _ = await _create_asset(client, owned, "WR-B", AssetType.STOCK)
    before = {id_a: await _row_of(client, id_a), id_b: await _row_of(client, id_b)}

    data = await _validate(
        client,
        [
            FAAssetPatchItem(asset_id=id_a, asset_type=AssetType.ETF_STOCK, is_benchmark=True),
            FAAssetPatchItem(asset_id=id_b, active=False, quote_base_quantity=100, user_url="https://example.com/v"),
        ],
    )

    assert data.committed is False
    assert data.issues == []
    assert [w.code.value for w in data.warnings] == ["assetFamilyChange"] and data.warnings[0].asset_id == id_a
    assert [r.asset_id for r in data.results] == [id_a, id_b] and all(r.success for r in data.results), data.results
    assert {f.info for f in data.results[1].updated_fields} == {"active", "quote_base_quantity", "user_url"}, "validate says what would be written"
    assert await _row_of(client, id_a) == before[id_a], "validate wrote on asset A"
    assert await _row_of(client, id_b) == before[id_b], "validate wrote on asset B"

    saved = await _patch(client, [FAAssetPatchItem(asset_id=id_a, asset_type=AssetType.ETF_STOCK, is_benchmark=True)])
    assert saved.committed is True, "control: the same payload really saves through PATCH"
    assert (await _row_of(client, id_a))["asset_type"] == AssetType.ETF_STOCK.value
    print_success("validate: committed=false, would-be results, family warning, both assets untouched")


@pytest.mark.asyncio
async def test_validate_currency_change_keeps_prices_and_events(env):
    """B4.2 — red today: no route. Contract: the currency change of an asset with prices and events is judged, not
    executed: prices and events are exactly the same after validate (the N68 wipe is rolled back), and the control PATCH
    of the same payload does remove them, so the dry run really took the wipe path."""
    print_section("B4.2 — validate of a currency change keeps prices and events")
    client, owned = env
    asset_id, _ = await _create_asset(client, owned, "CUR", currency="USD")
    start = date.today() - timedelta(days=10)
    await _seed_prices(client, asset_id, start, 3)
    await _seed_event(client, asset_id, start, "DIVIDEND", "0.25", "USD")
    await _seed_event(client, asset_id, start + timedelta(days=1), "INTEREST", "0.50", "USD")
    await _seed_event(client, asset_id, start + timedelta(days=2), "SPLIT", "2", "USD")
    prices_before = await _prices_of(client, asset_id, start, 3)
    events_before = await _events_of(client, asset_id)
    row_before = await _row_of(client, asset_id)
    assert len(prices_before) == 3 and len(events_before) == 3, "precondition"

    data = await _validate(client, [FAAssetPatchItem(asset_id=asset_id, currency="EUR")])

    assert data.committed is False and data.issues == []
    assert data.results[0].success is True and any(f.info == "currency" for f in data.results[0].updated_fields), data.results
    assert await _prices_of(client, asset_id, start, 3) == prices_before, "validate must not wipe the prices"
    assert await _events_of(client, asset_id) == events_before, "validate must not wipe the events"
    assert await _row_of(client, asset_id) == row_before, "the currency is unchanged after validate"

    saved = await _patch(client, [FAAssetPatchItem(asset_id=asset_id, currency="EUR")])
    assert saved.committed is True
    assert await _prices_of(client, asset_id, start, 3) == [], "control: PATCH wipes the prices"
    assert [e["type"] for e in await _events_of(client, asset_id)] == ["SPLIT"], "control: PATCH keeps only the SPLIT"
    print_success("validate: prices, events and currency intact; PATCH control wipes them")


@pytest.mark.asyncio
async def test_validate_returns_the_same_issues_and_warnings_as_patch(env):
    """B4.3 — red today: no route. Contract: one batch with a missing asset, an INDEX with transactions, a name taken by
    another asset and a family change gets the same issues and the same warnings from validate and from PATCH; both
    answer 200, ``committed`` false and every result failed, and nothing is written."""
    print_section("B4.3 — validate and PATCH report the same issues and warnings")
    client, owned = env
    ghost = 999_999_999
    stock_id, stock_name = await _create_asset(client, owned, "PAR-S", AssetType.STOCK)
    renamed_id, renamed_name = await _create_asset(client, owned, "PAR-R", AssetType.STOCK)
    _holder_id, holder_name = await _create_asset(client, owned, "PAR-H", AssetType.STOCK)
    crowd_id, _ = await _create_asset(client, owned, "PAR-C", AssetType.CROWDFUND_REAL_ESTATE)

    broker_name = f"B4 Broker {unique_id('B')}"
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": broker_name, "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["results"] if r["name"] == broker_name)
    owned.broker_ids.append(row["broker_id"])
    buy = {"broker_id": row["broker_id"], "asset_id": stock_id, "type": "BUY", "date": "2026-01-15", "quantity": "10", "cash": {"code": "USD", "amount": "-100"}}
    resp = await client.post(f"{API_BASE}/transactions/commit", json={"creates": [buy]}, timeout=TIMEOUT)
    assert resp.status_code == 200 and resp.json()["committed"] is True, resp.text

    items = [
        FAAssetPatchItem(asset_id=ghost, active=False),
        FAAssetPatchItem(asset_id=stock_id, asset_type=AssetType.INDEX),
        FAAssetPatchItem(asset_id=renamed_id, display_name=holder_name),
        FAAssetPatchItem(asset_id=crowd_id, asset_type=AssetType.ETF_STOCK),
    ]
    rows_before = {asset_id: await _row_of(client, asset_id) for asset_id in (stock_id, renamed_id, crowd_id)}

    via_validate = await _validate(client, items)
    via_patch = await _patch(client, items)

    issues_v, warnings_v = _issue_keys(via_validate)
    issues_p, warnings_p = _issue_keys(via_patch)
    assert issues_v == issues_p and warnings_v == warnings_p, (issues_v, issues_p, warnings_v, warnings_p)
    assert [i[0] for i in issues_v] == ["assetNotFound", "indexWithTransactions", "assetNameTaken"], issues_v
    assert [w[0] for w in warnings_v] == ["assetFamilyChange"], warnings_v
    for data in (via_validate, via_patch):
        assert data.committed is False and data.success_count == 0
        assert len(data.results) == 4 and all(r.success is False for r in data.results), data.results
    for asset_id, before in rows_before.items():
        assert await _row_of(client, asset_id) == before, f"asset {asset_id} changed"
    assert (await _row_of(client, renamed_id))["display_name"] == renamed_name and (await _row_of(client, stock_id))["display_name"] == stock_name
    print_success("validate and PATCH: identical issues and warnings, nothing written")
