"""POST /portfolio/allocation — the «Allocazione» tab's filtered allocation (lane 80, lot ALF-B2, issue #89).

The route wires ``PortfolioService.get_allocation`` (``services/portfolio/allocation.py``) to the pure view
``financial_math.portfolio.allocation_view`` on the page's engine run. The view's own rules are tested purely in
``test_financial_math/test_allocation_view.py``; here what the wiring adds:

- ``TestValidation`` — 401 without a session; 422 on an unknown dimension, on «Liquidity» as an excluded bucket (only a
  class), on an unknown field;
- ``TestTheView`` — one broker holding an equity ETF and a bond ETF bought at known prices, and cash: «solo azioni»
  takes the equity ETF, the bond and the cash are outside, base + outside + excluded = the report's net worth; the
  amounts travel (privacy is the frontend's); the scope lists the assets with their names; the matrix and the history;
- ``TestTheScope`` — ``broker_ids`` leaves the other broker's asset out; a broker the user cannot read gives an empty
  view, as the report's; an owner at 50 % sees half, and ``apply_ownership_share=False`` the whole broker.

Each test owns its users, brokers, assets and transactions and deletes them (brokers first). No count of rows it did
not create, no position, no clock: every figure is the test's own book. Amounts are short decimals, so identities are
exact. Runs in ``./dev.py test api portfolio-allocation`` (the lane's shared backend).
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from decimal import Decimal

import httpx
import pytest

from backend.test_scripts.test_api.test_portfolio_api import (
    API_BASE,
    TIMEOUT,
    commit_batch,
    create_broker,
    create_test_user,
    delete_current_test_user,
    get_current_user_id,
    post_portfolio_report,
    test_server,  # noqa: F401 — the module fixture, re-used
)
from backend.test_scripts.test_utils import print_section

WINDOW = {"start": "2025-01-01", "end": "2025-03-31"}


async def post_allocation(client: httpx.AsyncClient, body: dict) -> httpx.Response:
    return await client.post(f"{API_BASE}/portfolio/allocation", json=body, timeout=TIMEOUT)


async def _create_asset(client: httpx.AsyncClient, asset_type: str) -> int:
    resp = await client.post(f"{API_BASE}/assets", json=[{"display_name": f"Alloc_{asset_type}_{uuid.uuid4().hex[:6]}", "currency": "EUR", "asset_type": asset_type}], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    return resp.json()["results"][0]["asset_id"]


@asynccontextmanager
async def _user(client: httpx.AsyncClient):
    """A fresh user, its brokers and assets deleted after (brokers first)."""
    await create_test_user(client)
    user_id = await get_current_user_id(client)
    owned: dict[str, list[int]] = {"brokers": [], "assets": []}
    try:
        yield owned
    finally:
        if owned["brokers"]:
            resp = await client.delete(f"{API_BASE}/brokers", params={"ids": owned["brokers"], "force": True}, timeout=TIMEOUT)
            assert resp.status_code == 200, resp.text
        if owned["assets"]:
            resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": owned["assets"]}, timeout=TIMEOUT)
            assert resp.status_code == 200, resp.text
        await delete_current_test_user(client, user_id)


async def _book(client: httpx.AsyncClient, owned: dict) -> tuple[int, int, int]:
    """One broker: DEPOSIT 1000, BUY 10 of an ETF_STOCK for 500 and 2 of an ETF_BOND for 200: NAV 1000, cash 300."""
    broker_id = await create_broker(client)
    owned["brokers"].append(broker_id)
    equity, bond = await _create_asset(client, "ETF_STOCK"), await _create_asset(client, "ETF_BOND")
    owned["assets"] += [equity, bond]
    await commit_batch(
        client,
        creates=[
            {"broker_id": broker_id, "type": "DEPOSIT", "date": "2025-01-02", "quantity": "0", "cash": {"code": "EUR", "amount": "1000"}},
            {"broker_id": broker_id, "asset_id": equity, "type": "BUY", "date": "2025-01-03", "quantity": "10", "cash": {"code": "EUR", "amount": "-500"}},
            {"broker_id": broker_id, "asset_id": bond, "type": "BUY", "date": "2025-01-03", "quantity": "2", "cash": {"code": "EUR", "amount": "-200"}},
        ],
    )
    return broker_id, equity, bond


def _d(value) -> Decimal:
    return Decimal(str(value))


def _identity(body: dict) -> Decimal:
    return _d(body["base"]) + _d(body["outside"]["amount"]) + _d(body["excluded"]["amount"])


@pytest.mark.asyncio
class TestValidation:
    async def test_unauthenticated(self, test_server):  # noqa: F811
        print_section("Allocation: unauthenticated")
        async with httpx.AsyncClient() as client:
            resp = await post_allocation(client, {})
        assert resp.status_code == 401

    async def test_invalid_filters_are_refused(self, test_server):  # noqa: F811
        print_section("Allocation: invalid filters")
        async with httpx.AsyncClient() as client, _user(client):
            bad_dimension = await post_allocation(client, {"dimension": "country"})
            liquidity_bucket = await post_allocation(client, {"exclude_buckets": ["Liquidity"]})
            unknown_field = await post_allocation(client, {"include_everything": True})
            empty_class = await post_allocation(client, {"classes": [""]})
            empty_type = await post_allocation(client, {"types": [""]})
            fine = await post_allocation(client, {"dimension": "asset", "exclude_buckets": ["Unknown", "Other"], "classes": [], "types": ["ETF_STOCK"]})
        assert (bad_dimension.status_code, liquidity_bucket.status_code, unknown_field.status_code, empty_class.status_code, empty_type.status_code) == (422, 422, 422, 422, 422)
        assert fine.status_code == 200, fine.text
        assert fine.json()["applicable_buckets"] == [], "the asset dimension has no excludable bucket"


@pytest.mark.asyncio
class TestTheView:
    async def test_only_stocks_and_the_identity(self, test_server):  # noqa: F811
        print_section("Allocation: only stocks, the identity, the amounts")
        async with httpx.AsyncClient() as client, _user(client) as owned:
            broker_id, equity, bond = await _book(client, owned)
            resp = await post_allocation(client, {"date_range": WINDOW, "dimension": "type", "classes": ["STOCK"], "include_history": True})
            report = await post_portfolio_report(client, {"date_range": WINDOW, "include_history": False, "include_allocation_history": False})
        assert resp.status_code == 200, resp.text
        assert report.status_code == 200, report.text
        body = resp.json()
        assert (body["currency"], body["as_of"], body["date_from"], body["dimension"]) == ("EUR", WINDOW["end"], WINDOW["start"], "type")
        assert _d(body["portfolio_total"]) == _d(report.json()["summary"]["net_worth"]["amount"]) == Decimal("1000"), "the total is the KPI «Patrimonio netto»"
        assert [(row["key"], _d(row["amount"]), _d(row["share_of_selection"])) for row in body["slices"]] == [("ETF_STOCK", Decimal("500"), Decimal("100"))]
        assert [(row["asset_id"], _d(row["amount"])) for row in body["slices"][0]["assets"]] == [(equity, Decimal("500"))]
        assert {row["asset_class"]: _d(row["amount"]) for row in body["outside"]["by_class"]} == {"BOND": Decimal("200"), "Liquidity": Decimal("300")}
        assert _identity(body) == _d(body["portfolio_total"])
        assert _d(body["base_share_of_portfolio"]) == Decimal("50")
        assert body["applicable_buckets"] == ["Unknown"]
        assert {(row["asset_id"], row["asset_class"], row["asset_type"]) for row in body["assets"]} == {(equity, "STOCK", "ETF_STOCK"), (bond, "BOND", "ETF_BOND")}
        assert all(row["name"].startswith("Alloc_") for row in body["assets"]), "the assets carry their names"
        assert [(row["asset_class"], _d(row["amount"])) for row in body["classes"]] == [("STOCK", Decimal("500")), ("Liquidity", Decimal("300")), ("BOND", Decimal("200"))], "largest first"
        assert {row["asset_class"]: [(item["asset_type"], _d(item["amount"])) for item in row["types"]] for row in body["classes"]} == {"STOCK": [("ETF_STOCK", Decimal("500"))], "BOND": [("ETF_BOND", Decimal("200"))], "Liquidity": []}
        assert body["matrix"] is None, "the type dimension has no matrix (86, D-15)"
        history = body["history"]
        assert history and history[-1]["through"] == WINDOW["end"]
        assert all(_d(step["base"]) == sum((_d(c["amount"]) for c in step["components"]), Decimal("0")) for step in history)
        assert _d(history[-1]["base"]) == Decimal("500")

    async def test_a_type_kept_on_its_own(self, test_server):  # noqa: F811
        print_section("Allocation: a type kept beside the classes, and the matrix of the sectors")
        async with httpx.AsyncClient() as client, _user(client) as owned:
            _broker_id, equity, _bond = await _book(client, owned)
            resp = await post_allocation(client, {"date_range": WINDOW, "dimension": "type", "classes": ["Liquidity"], "types": ["ETF_STOCK"]})
            sector = await post_allocation(client, {"date_range": WINDOW, "dimension": "sector", "classes": [], "types": ["ETF_STOCK"]})
        assert resp.status_code == sector.status_code == 200, resp.text
        body = resp.json()
        assert {row["key"]: _d(row["amount"]) for row in body["slices"]} == {"ETF_STOCK": Decimal("500"), "Liquidity": Decimal("300")}
        assert {row["asset_class"]: _d(row["amount"]) for row in body["outside"]["by_class"]} == {"BOND": Decimal("200")}
        assert _identity(body) == _d(body["portfolio_total"])
        assert _d(sector.json()["base"]) == Decimal("500")
        assert {cell["asset_class"] for cell in sector.json()["matrix"]["cells"]} == {"STOCK", "BOND", "Liquidity"}, "the matrix is the whole portfolio"
        assert equity

    async def test_the_geography_and_no_history_by_default(self, test_server):  # noqa: F811
        print_section("Allocation: geography, the cash has no country")
        async with httpx.AsyncClient() as client, _user(client) as owned:
            await _book(client, owned)
            resp = await post_allocation(client, {"date_range": WINDOW, "dimension": "geography", "exclude_buckets": ["Other"]})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["history"] is None
        assert [(row["key"], _d(row["amount"])) for row in body["slices"]] == [("Unknown", Decimal("700"))], "no profile: Unknown; Other has no effect in the geography"
        assert {row["reason"]: _d(row["amount"]) for row in body["excluded"]["unattributable"]} == {"no_country": Decimal("300")}
        assert body["excluded"]["by_bucket"] == []
        assert _identity(body) == Decimal("1000")


@pytest.mark.asyncio
class TestTheScope:
    async def test_the_broker_filter_and_an_unreadable_broker(self, test_server):  # noqa: F811
        print_section("Allocation: broker scope, a broker the user cannot read")
        async with httpx.AsyncClient() as stranger, _user(stranger) as stranger_owned:
            foreign_broker = await create_broker(stranger)
            stranger_owned["brokers"].append(foreign_broker)
            async with httpx.AsyncClient() as client, _user(client) as owned:
                broker_id, equity, bond = await _book(client, owned)
                other_broker = await create_broker(client)
                owned["brokers"].append(other_broker)
                crypto = await _create_asset(client, "CRYPTO")
                owned["assets"].append(crypto)
                await commit_batch(
                    client,
                    creates=[
                        {"broker_id": other_broker, "type": "DEPOSIT", "date": "2025-01-02", "quantity": "0", "cash": {"code": "EUR", "amount": "80"}},
                        {"broker_id": other_broker, "asset_id": crypto, "type": "BUY", "date": "2025-01-04", "quantity": "1", "cash": {"code": "EUR", "amount": "-80"}},
                    ],
                )
                both = await post_allocation(client, {"date_range": WINDOW, "dimension": "asset"})
                first_only = await post_allocation(client, {"date_range": WINDOW, "dimension": "asset", "broker_ids": [broker_id]})
                unreadable = await post_allocation(client, {"date_range": WINDOW, "dimension": "asset", "broker_ids": [foreign_broker]})
        for resp in (both, first_only, unreadable):
            assert resp.status_code == 200, resp.text
        assert {row["asset_id"] for row in both.json()["assets"]} == {equity, bond, crypto}
        assert _d(both.json()["portfolio_total"]) == Decimal("1080")
        assert {row["asset_id"] for row in first_only.json()["assets"]} == {equity, bond}, "the other broker's asset is out of the scope"
        assert _d(first_only.json()["portfolio_total"]) == Decimal("1000")
        empty = unreadable.json()
        assert (empty["as_of"], _d(empty["portfolio_total"]), empty["slices"], empty["assets"]) == (None, Decimal("0"), [], []), "nothing of another user's broker"

    async def test_the_owners_share_and_the_whole_broker(self, test_server):  # noqa: F811
        print_section("Allocation: ownership share")
        async with httpx.AsyncClient() as client, _user(client) as owned:
            broker_id, _equity, _bond = await _book(client, owned)
            me = await get_current_user_id(client)
            share = await client.put(f"{API_BASE}/brokers/{broker_id}/access", json=[{"user_id": me, "role": "OWNER", "share_percentage": 0.5}], timeout=TIMEOUT)
            assert share.status_code == 200, share.text
            mine = await post_allocation(client, {"date_range": WINDOW, "dimension": "type"})
            whole = await post_allocation(client, {"date_range": WINDOW, "dimension": "type", "broker_ids": [broker_id], "apply_ownership_share": False})
        assert mine.status_code == 200 and whole.status_code == 200, (mine.text, whole.text)
        assert _d(mine.json()["portfolio_total"]) == Decimal("500"), "an owner at 50 % sees half"
        assert _d(whole.json()["portfolio_total"]) == Decimal("1000"), "the broker page counts the broker whole"
        assert {row["key"]: _d(row["amount"]) for row in mine.json()["slices"]} == {"ETF_STOCK": Decimal("250"), "ETF_BOND": Decimal("100"), "Liquidity": Decimal("150")}
