"""Project 74 — POST /portfolio/report with ``group_by``: an asset held at several brokers as one row («Globale»).

The developer's rule (16/11/2026): the row is the sum of its brokers, never a replay as if they were one broker. These
tests own their user, brokers, assets, transactions and prices, and delete them (brokers first, then assets, then the
user). Rows are found by their own ids, never by position or count of a shared list.

* L2 — the Portfolio: ``summary.holdings`` and ``summary.holding_groups``.
* L3 — the Period: ``positions_contribution`` (rows, closures, other effects) and the identity with the series of the
  asset summed over its brokers (``positions-series`` with ``broker_id: null``).
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import httpx
import pytest

from backend.app.config import get_settings
from backend.test_scripts.test_server_helper import _TestingServerManager
from backend.test_scripts.test_utils import print_section

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30
WINDOW = {"start": "2025-01-01", "end": "2025-06-30"}


@pytest.fixture(scope="module")
def test_server():
    with _TestingServerManager() as manager:
        if not manager.start_server():
            pytest.fail("Failed to start test server")
        yield manager


async def _login_new_user(client: httpx.AsyncClient) -> None:
    username = f"grp74_{uuid.uuid4().hex[:8]}"
    created = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@test.com", "password": "TestPass123!"}, timeout=TIMEOUT)
    assert created.status_code == 201, created.text
    login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": "TestPass123!"}, timeout=TIMEOUT)
    assert login.status_code == 200, login.text
    if session := login.cookies.get("session"):
        client.cookies.set("session", session)


async def _broker(client: httpx.AsyncClient) -> int:
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": f"G74_{uuid.uuid4().hex[:6]}", "allow_cash_overdraft": True}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return resp.json()["results"][0]["broker_id"]


async def _asset(client: httpx.AsyncClient) -> int:
    resp = await client.post(f"{API_BASE}/assets", json=[{"display_name": f"G74_{uuid.uuid4().hex[:6]}", "currency": "EUR", "asset_type": "STOCK"}], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["results"][0]["asset_id"]


async def _commit(client: httpx.AsyncClient, creates: list[dict]) -> None:
    resp = await client.post(f"{API_BASE}/transactions/commit", json={"creates": creates}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    assert resp.json().get("committed") is True, resp.text


async def _prices(client: httpx.AsyncClient, asset_id: int, closes: dict[str, str]) -> None:
    resp = await client.post(f"{API_BASE}/assets/prices", json=[{"asset_id": asset_id, "prices": [{"date": day, "close": close, "currency": "EUR"} for day, close in closes.items()]}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text


async def _report(client: httpx.AsyncClient, broker_ids: list[int], group_by: str | None, **extra) -> httpx.Response:
    body = {"broker_ids": broker_ids, "date_range": WINDOW, "include_summary": True, "include_history": False, "include_allocation_history": False, "include_positions_contribution": True, **extra}
    if group_by is not None:
        body["group_by"] = group_by
    return await client.post(f"{API_BASE}/portfolio/report", json=body, timeout=TIMEOUT)


async def _cleanup(client: httpx.AsyncClient, broker_ids: list[int], asset_ids: list[int]) -> None:
    if broker_ids:
        resp = await client.delete(f"{API_BASE}/brokers", params={"ids": broker_ids, "force": True}, timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text
    if asset_ids:
        resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": asset_ids}, timeout=TIMEOUT)
        assert resp.status_code == 200, resp.text
    resp = await client.delete(f"{API_BASE}/auth/users/me", timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text


def _rows(items: list[dict], asset_id: int) -> list[dict]:
    return [item for item in items if item["asset_id"] == asset_id]


async def _brief_book(client: httpx.AsyncClient) -> tuple[int, int, int, int]:
    """The brief's example: buy 10 @100 on A and 10 @200 on B, sell 5 on B @250; one more asset held on A only. The asset
    is worth 220 at the window's end."""
    broker_a, broker_b = await _broker(client), await _broker(client)
    shared, single = await _asset(client), await _asset(client)
    await _commit(
        client,
        [
            {"broker_id": broker_a, "type": "DEPOSIT", "date": "2025-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "5000"}},
            {"broker_id": broker_b, "type": "DEPOSIT", "date": "2025-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "5000"}},
            {"broker_id": broker_a, "asset_id": shared, "type": "BUY", "date": "2025-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
            {"broker_id": broker_b, "asset_id": shared, "type": "BUY", "date": "2025-01-03", "quantity": "10", "cash": {"code": "EUR", "amount": "-2000"}},
            {"broker_id": broker_b, "asset_id": shared, "type": "SELL", "date": "2025-03-03", "quantity": "-5", "cash": {"code": "EUR", "amount": "1250"}},
            {"broker_id": broker_a, "asset_id": single, "type": "BUY", "date": "2025-01-02", "quantity": "4", "cash": {"code": "EUR", "amount": "-400"}},
        ],
    )
    await _prices(client, shared, {"2025-06-30": "220.00"})
    await _prices(client, single, {"2025-06-30": "110.00"})
    return broker_a, broker_b, shared, single


@pytest.mark.asyncio
class TestGroupByPortfolio:
    """L2 — the holdings and their groups."""

    async def test_holdings_one_row_per_asset_summed_over_its_brokers(self, test_server):
        print_section("group_by=asset: holdings")
        async with httpx.AsyncClient() as client:
            await _login_new_user(client)
            brokers: list[int] = []
            assets: list[int] = []
            try:
                broker_a, broker_b, shared, single = await _brief_book(client)
                brokers, assets = [broker_a, broker_b], [shared, single]
                by_broker = await _report(client, brokers, None)
                by_asset = await _report(client, brokers, "asset")
            finally:
                await _cleanup(client, brokers, assets)

        assert by_broker.status_code == 200, by_broker.text
        assert by_asset.status_code == 200, by_asset.text
        broker_summary, asset_summary = by_broker.json()["summary"], by_asset.json()["summary"]
        assert by_broker.json()["metadata"]["group_by"] == "broker"
        assert by_asset.json()["metadata"]["group_by"] == "asset"

        # broker (default): today's rows, each naming its broker
        rows = _rows(broker_summary["holdings"], shared)
        assert sorted(row["broker_id"] for row in rows) == sorted([broker_a, broker_b])
        assert all(row["broker_ids"] == [row["broker_id"]] for row in rows)

        # asset: one row, the sum of the two
        [group] = _rows(asset_summary["holdings"], shared)
        assert group["broker_id"] is None and group["broker_name"] is None
        assert sorted(group["broker_ids"]) == sorted([broker_a, broker_b])
        assert Decimal(group["quantity"]) == Decimal("15")
        assert Decimal(group["current_value"]) == Decimal("3300")
        # A: 10 × (220 − 100) = 1 200; B: 5 × (220 − 200) = 100 — B's own cost, never one FIFO over the two
        assert Decimal(group["gain_loss"]) == Decimal("1300")
        assert Decimal(group["gain_loss"]) == sum(Decimal(row["gain_loss"]) for row in rows)
        # on the summed cost, 2 000: 65 %, not the average of 120 % and 10 %
        assert Decimal(group["gain_loss_percent"]) == Decimal("0.65")
        # total cost over total quantity: 2 000 / 15
        assert round(Decimal(group["wac_per_unit"]), 4) == round(Decimal("2000") / Decimal("15"), 4)
        assert Decimal(group["current_price"]) == Decimal("220")
        assert Decimal(group["nav_weight_percent"]) == sum(Decimal(row["nav_weight_percent"]) for row in rows)

        # an asset held at one broker keeps its figures, keyed by the asset alone as every Globale row
        [alone_broker] = _rows(broker_summary["holdings"], single)
        [alone_asset] = _rows(asset_summary["holdings"], single)
        assert (alone_asset["broker_id"], alone_asset["broker_name"], alone_asset["broker_ids"]) == (None, None, [broker_a])
        assert {key: value for key, value in alone_asset.items() if key not in ("broker_id", "broker_name")} == {key: value for key, value in alone_broker.items() if key not in ("broker_id", "broker_name")}

        # nothing else of the summary changes
        assert asset_summary["net_worth"] == broker_summary["net_worth"]
        assert asset_summary["allocation_by_asset"] == broker_summary["allocation_by_asset"]

    async def test_holding_groups_by_asset_type_over_every_broker(self, test_server):
        print_section("group_by=asset: holding groups")
        async with httpx.AsyncClient() as client:
            await _login_new_user(client)
            brokers: list[int] = []
            assets: list[int] = []
            try:
                broker_a, broker_b, shared, single = await _brief_book(client)
                brokers, assets = [broker_a, broker_b], [shared, single]
                by_asset = await _report(client, brokers, "asset")
            finally:
                await _cleanup(client, brokers, assets)

        groups = by_asset.json()["summary"]["holding_groups"]
        assert {(group["broker_id"], group["asset_type"]) for group in groups} == {(None, "STOCK")}
        [stock] = groups
        # 1 300 on the shared asset + 4 × (110 − 100) = 40 on the other
        assert Decimal(stock["gain_loss"]["amount"]) == Decimal("1340")

    async def test_an_unknown_grouping_is_refused(self, test_server):
        async with httpx.AsyncClient() as client:
            await _login_new_user(client)
            try:
                resp = await _report(client, [], "currency")
            finally:
                await _cleanup(client, [], [])
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestGroupByPeriod:
    """L3 — the Performance rows of the period."""

    async def test_rows_summed_realized_is_the_brokers_own(self, test_server):
        print_section("group_by=asset: contribution")
        async with httpx.AsyncClient() as client:
            await _login_new_user(client)
            brokers: list[int] = []
            assets: list[int] = []
            try:
                broker_a, broker_b, shared, single = await _brief_book(client)
                brokers, assets = [broker_a, broker_b], [shared, single]
                by_broker = await _report(client, brokers, None)
                by_asset = await _report(client, brokers, "asset")
                series = await client.post(
                    f"{API_BASE}/portfolio/positions-series",
                    json={"broker_ids": brokers, "date_range": WINDOW, "positions": [{"asset_id": shared, "broker_id": None}]},
                    timeout=TIMEOUT,
                )
            finally:
                await _cleanup(client, brokers, assets)

        rows = _rows(by_broker.json()["positions_contribution"]["positions"], shared)
        [group] = _rows(by_asset.json()["positions_contribution"]["positions"], shared)
        assert group["broker_id"] is None
        assert sorted(group["broker_ids"]) == sorted([broker_a, broker_b])
        # The brief: B sold 5 bought at 200 for 250 → +250. One FIFO over the two brokers would say +750.
        assert Decimal(group["period_realized_gain_loss"]) == Decimal("250")
        assert Decimal(group["period_pnl"]) == sum(Decimal(row["period_pnl"]) for row in rows)
        assert group["is_fully_sold"] is False
        # The identity: the row is the last point of the series of the asset summed over its brokers
        assert series.status_code == 200, series.text
        [line] = series.json()["series"]
        assert Decimal(line["points"][-1]["pnl"]) == Decimal(group["period_pnl"])
        # The other asset keeps its figures, keyed by the asset alone; the totals of the period do not move
        [alone_broker] = _rows(by_broker.json()["positions_contribution"]["positions"], single)
        [alone_asset] = _rows(by_asset.json()["positions_contribution"]["positions"], single)
        assert (alone_asset["broker_id"], alone_asset["broker_ids"]) == (None, [broker_a])
        assert Decimal(alone_asset["period_pnl"]) == Decimal(alone_broker["period_pnl"])
        for total in ("gross_gains", "gross_losses"):
            assert by_asset.json()["positions_contribution"][total] is not None

    async def test_a_move_between_two_brokers_of_the_scope_does_not_close_the_asset(self, test_server):
        print_section("group_by=asset: internal transfer")
        async with httpx.AsyncClient() as client:
            await _login_new_user(client)
            brokers: list[int] = []
            assets: list[int] = []
            try:
                broker_a, broker_b = await _broker(client), await _broker(client)
                moved = await _asset(client)
                brokers, assets = [broker_a, broker_b], [moved]
                link = f"g74-{uuid.uuid4().hex[:8]}"
                await _commit(
                    client,
                    [
                        {"broker_id": broker_a, "type": "DEPOSIT", "date": "2025-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
                        {"broker_id": broker_a, "asset_id": moved, "type": "BUY", "date": "2025-01-02", "quantity": "10", "cash": {"code": "EUR", "amount": "-1000"}},
                        {"broker_id": broker_a, "asset_id": moved, "type": "TRANSFER", "date": "2025-03-03", "quantity": "-10", "link_uuid": link},
                        {"broker_id": broker_b, "asset_id": moved, "type": "TRANSFER", "date": "2025-03-03", "quantity": "10", "link_uuid": link, "cost_basis_override": {"code": "EUR", "amount": "100"}},
                    ],
                )
                await _prices(client, moved, {"2025-02-28": "110.00", "2025-06-30": "130.00"})
                by_broker = await _report(client, brokers, None)
                by_asset = await _report(client, brokers, "asset")
            finally:
                await _cleanup(client, brokers, assets)

        rows = _rows(by_broker.json()["positions_contribution"]["positions"], moved)
        sender = next(row for row in rows if row["broker_id"] == broker_a)
        assert sender["is_fully_sold"] is True and sender["closed_by"] == "TRANSFER"
        [group] = _rows(by_asset.json()["positions_contribution"]["positions"], moved)
        assert group["is_fully_sold"] is False
        assert group["closed_by"] is None
        assert Decimal(group["period_pnl"]) == sum(Decimal(row["period_pnl"]) for row in rows)
        # 10 × (130 − 100): what the asset did, whatever broker held it
        assert Decimal(group["period_pnl"]) == Decimal("300")
        # One identity for the asset across the views: the holding (held at B alone now) and the Period row (A and B) are
        # both keyed by the asset alone, so a tick and the chart's series are the same in Portfolio and in Period
        [holding] = _rows(by_asset.json()["summary"]["holdings"], moved)
        assert (holding["broker_id"], holding["broker_ids"]) == (None, [broker_b])
        assert group["broker_id"] is None and sorted(group["broker_ids"]) == sorted(brokers)

    async def test_other_effects_summed_by_kind_with_their_brokers(self, test_server):
        print_section("group_by=asset: other effects")
        async with httpx.AsyncClient() as client:
            await _login_new_user(client)
            brokers: list[int] = []
            try:
                broker_a, broker_b = await _broker(client), await _broker(client)
                brokers = [broker_a, broker_b]
                await _commit(
                    client,
                    [
                        {"broker_id": broker_a, "type": "DEPOSIT", "date": "2025-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "100"}},
                        {"broker_id": broker_b, "type": "DEPOSIT", "date": "2025-01-01", "quantity": "0", "cash": {"code": "EUR", "amount": "100"}},
                        {"broker_id": broker_a, "type": "FEE", "date": "2025-02-01", "quantity": "0", "cash": {"code": "EUR", "amount": "-3"}},
                        {"broker_id": broker_b, "type": "FEE", "date": "2025-02-01", "quantity": "0", "cash": {"code": "EUR", "amount": "-4"}},
                    ],
                )
                by_broker = await _report(client, brokers, None)
                by_asset = await _report(client, brokers, "asset")
            finally:
                await _cleanup(client, brokers, [])

        per_broker = [effect for effect in by_broker.json()["positions_contribution"]["other_effects"] if effect["description"] == "Unallocated costs"]
        assert sorted(effect["broker_id"] for effect in per_broker) == sorted(brokers)
        merged = [effect for effect in by_asset.json()["positions_contribution"]["other_effects"] if effect["description"] == "Unallocated costs"]
        [row] = merged
        assert Decimal(row["period_pnl"]) == Decimal("-7")
        assert sorted(row["broker_ids"]) == sorted(brokers)
        assert row["broker_id"] is None and row["broker_name"] is None
