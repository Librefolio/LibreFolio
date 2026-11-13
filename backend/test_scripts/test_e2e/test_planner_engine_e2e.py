"""E2E of the planner engine (lot T0 of project 67): a portfolio built through the API, a request composed from
``POST /portfolio/allocation-source``, a plan from ``POST /tools/compute``.

Every test registers its own user, creates its own Broker, Assets, prices and transactions through the public endpoints,
reads them back through the planner source, composes the request the way the planner page does
(``frontend/src/lib/features/tools/pac-allocator/planner/request.ts``, ``copies.ts``) and sends it to the served Tool.
The Tool identity and the engine window are read from ``GET /tools/catalog``, never hard-coded.

What no endpoint gives yet is written by hand, as the user writes it in the page today, under one ``manual`` provenance
(``HAND_PROVENANCE_ID``): the Broker's order modes (capabilities) and fee schedules (until P1–P3), the order routes and
which Assets a Broker may buy, the targets, the contributions, the strategy and the target fidelity. Each such field is
marked ``# HAND (P3)`` below, so P3 knows what to move to an endpoint.

Isolation: each test owns its user and every row it writes (Broker, Assets with uuid names, their prices, the Broker's
transactions), addresses them by id, and deletes them before returning. FX is only read: the one FX case reads a rate
that ``./dev.py test db populate`` saved and never writes one (D13 = a). No external network, no clock waits.

The engine already exists (B3, B4): these tests were written against it, so none of them was red before it.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from typing import Any
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.db.session import get_async_engine
from backend.app.schemas.pac_allocator.results import PAC_PLAN_INPUT_ADAPTER, PAC_PLAN_OUTPUT_ADAPTER, REBALANCER_PLAN_INPUT_ADAPTER, REBALANCER_PLAN_OUTPUT_ADAPTER
from backend.app.services.accounts import user_service
from backend.app.services.pac_allocator.planner import plan_pac_allocation, plan_rebalancing
from backend.test_scripts.test_db_config import verify_test_database
from backend.test_scripts.test_server_helper import _TestingServerManager

settings = get_settings()
API_BASE = f"http://localhost:{settings.TEST_PORT}/api/v1"
TIMEOUT = 30.0
# The plan operation's client deadline is 65 s (tool_plugins/pac_allocator/plugin.py): the transport must outwait it.
COMPUTE_TIMEOUT = 70.0
PASSWORD = "PlannerE2ePass123!"
SOLE_ADMIN_DELETE_DETAIL = {"error_code": "LAST_ADMIN", "message": "Cannot delete account: you are the last active administrator"}

PAC = "pac_allocator"
REBALANCER = "portfolio_rebalancer"
IDENTITY_KEYS = ("tool_code", "contract_version", "implementation_version", "schema_fingerprint")

# A fixed past day: the prices are saved on it, the transactions before it.
AS_OF = date(2026, 1, 15)
TRADE_DAY = AS_OF - timedelta(days=5)
ALL_SECTIONS = ["assets", "brokers", "holdings", "cash_balances", "prices", "classifications", "fx_quotes"]

HAND_PROVENANCE_ID = "manual:t0-hand-written"
BALANCED = {"kind": "level", "level": "balanced"}

# The source issues every copied Asset and Broker carries today: no sector, no geography (the test saves none), and
# no execution profile for the Broker (test 3 pins that one).
ASSET_SOURCE_WARNINGS = ("allocation.classification_sector_missing", "allocation.classification_geography_missing")
BROKER_PROFILE_ISSUE = "allocation.broker_execution_profile_unsupported"


@pytest.fixture(scope="module")
def test_server():
    """Attach to the runner-owned backend, or start its in-process test server."""
    with _TestingServerManager() as server_manager:
        if not server_manager.start_server():
            pytest.fail("Failed to start test server")
        yield server_manager


# ---------------------------------------------------------------------------
# A user of our own, and everything it creates, for the length of one test
# ---------------------------------------------------------------------------


class _Owned:
    """What a test created through the API, dropped in FK-safe order: Brokers force-deleted with their transactions, then
    the Assets with their prices."""

    def __init__(self) -> None:
        self.broker_ids: list[int] = []
        self.asset_ids: list[int] = []

    async def drop(self, client: httpx.AsyncClient) -> list[str]:
        """Never raises: what could not be removed is returned."""
        problems: list[str] = []
        for broker_id in self.broker_ids:
            try:
                resp = await client.delete(f"{API_BASE}/brokers", params={"ids": [broker_id], "force": True}, timeout=TIMEOUT)
                done = resp.status_code == 200 and any(r.get("id") == broker_id and r.get("success") for r in resp.json().get("results", []))
                if not done:
                    problems.append(f"broker {broker_id}: HTTP {resp.status_code} {resp.text}")
            except Exception as exc:  # noqa: BLE001 — cleanup reports instead of masking the test's own outcome
                problems.append(f"broker {broker_id}: {exc!r}")
        if self.asset_ids:
            try:
                resp = await client.delete(f"{API_BASE}/assets", params={"asset_ids": self.asset_ids}, timeout=TIMEOUT)
                deleted = {r["asset_id"] for r in resp.json().get("results", []) if r.get("success")} if resp.status_code == 200 else set()
                problems += [f"asset {asset_id}: HTTP {resp.status_code} {resp.text}" for asset_id in self.asset_ids if asset_id not in deleted]
            except Exception as exc:  # noqa: BLE001
                problems.append(f"assets {self.asset_ids}: {exc!r}")
        return problems


async def _register_and_login(client: httpx.AsyncClient) -> int:
    username = f"planner_e2e_{uuid4().hex[:16]}"
    registered = await client.post(f"{API_BASE}/auth/register", json={"username": username, "email": f"{username}@example.com", "password": PASSWORD}, timeout=TIMEOUT)
    assert registered.status_code == 201, registered.text
    login = await client.post(f"{API_BASE}/auth/login", json={"username": username, "password": PASSWORD}, timeout=TIMEOUT)
    assert login.status_code == 200, login.text
    session = login.cookies.get("session")
    assert session is not None
    client.cookies.set("session", session)
    me = await client.get(f"{API_BASE}/auth/me", timeout=TIMEOUT)
    assert me.status_code == 200, me.text
    return me.json()["user"]["id"]


async def _delete_own_user(client: httpx.AsyncClient, user_id: int) -> None:
    """Delete only this test's account, with the exact sole-admin fallback."""
    response = await client.delete(f"{API_BASE}/auth/users/me", timeout=TIMEOUT)
    if response.status_code == 400 and response.json().get("detail") == SOLE_ADMIN_DELETE_DETAIL:
        is_test_db, _ = verify_test_database()
        assert is_test_db, "Refusing sole-admin cleanup outside the test database"
        async with AsyncSession(get_async_engine()) as session:
            assert await user_service.delete_user(session, user_id)
        return
    assert response.status_code == 200, response.text


@asynccontextmanager
async def _owner() -> AsyncIterator[tuple[httpx.AsyncClient, _Owned]]:
    async with httpx.AsyncClient() as client:
        user_id = await _register_and_login(client)
        owned = _Owned()
        try:
            yield client, owned
        finally:
            problems = await owned.drop(client)
            if problems:
                print(f"cleanup problems: {problems}")  # also on a red body, whose own error the assert below never reaches
            await _delete_own_user(client, user_id)
        assert not problems, problems


# ---------------------------------------------------------------------------
# Building the portfolio through the API
# ---------------------------------------------------------------------------


async def _create_broker(client: httpx.AsyncClient, owned: _Owned) -> int:
    name = f"T0 Broker {uuid4().hex[:12]}"
    resp = await client.post(f"{API_BASE}/brokers", json=[{"name": name}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    row = next(r for r in resp.json()["results"] if r["name"] == name)
    assert row["success"] is True, row
    owned.broker_ids.append(row["broker_id"])
    return row["broker_id"]


async def _create_asset(client: httpx.AsyncClient, owned: _Owned, currency: str = "EUR") -> int:
    name = f"T0 Asset {uuid4().hex[:12]}"
    resp = await client.post(f"{API_BASE}/assets", json=[{"display_name": name, "currency": currency, "asset_type": "ETF"}], timeout=TIMEOUT)
    assert resp.status_code in (200, 201), resp.text
    (result,) = resp.json()["results"]
    assert result["success"], resp.text
    owned.asset_ids.append(result["asset_id"])
    return result["asset_id"]


async def _save_price(client: httpx.AsyncClient, asset_id: int, day: date, close: str) -> None:
    resp = await client.post(f"{API_BASE}/assets/prices", json=[{"asset_id": asset_id, "prices": [{"date": day.isoformat(), "close": close}]}], timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    (result,) = (r for r in resp.json()["results"] if r["asset_id"] == asset_id)
    assert result["count"] == 1, result


async def _commit(client: httpx.AsyncClient, creates: list[dict]) -> None:
    resp = await client.post(f"{API_BASE}/transactions/commit", json={"creates": creates}, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["committed"] is True, body["issues"]


def _deposit(broker_id: int, amount: str, currency: str = "EUR", day: date = TRADE_DAY) -> dict:
    return {"broker_id": broker_id, "type": "DEPOSIT", "date": day.isoformat(), "cash": {"code": currency, "amount": amount}}


def _buy(broker_id: int, asset_id: int, quantity: str, cost: str, currency: str = "EUR", day: date = TRADE_DAY) -> dict:
    return {"broker_id": broker_id, "asset_id": asset_id, "type": "BUY", "date": day.isoformat(), "quantity": quantity, "cash": {"code": currency, "amount": f"-{cost}"}}


async def _source(client: httpx.AsyncClient, *, broker_id: int, asset_ids: list[int] | None, sections: list[str] = ALL_SECTIONS, fx_pairs: list[str] | None = None, as_of: date = AS_OF) -> dict:
    body = {"as_of": as_of.isoformat(), "target_currency": "EUR", "requested_sections": sections, "broker_ids": [broker_id], "asset_ids": asset_ids, "fx_pairs": fx_pairs or []}
    resp = await client.post(f"{API_BASE}/portfolio/allocation-source", json=body, timeout=TIMEOUT)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _asset_key(source: dict, asset_id: int) -> str:
    """The source's key of the Asset with database id ``asset_id``, read from its Asset rows, never built here."""
    keys = [row["asset_id"] for row in source["assets"] if row["source_asset_id"] == asset_id]
    assert len(keys) == 1, f"Asset {asset_id} in the source's assets: {keys}"
    return keys[0]


def _assert_source_issues(source: dict, expected: set[tuple[str, str]]) -> None:
    """The source's issues are exactly ``expected`` (code, entity): a missing price or rate fails here, by its name."""
    found = {(issue["code"], issue["path"].get("entity_id", "")) for issue in source["issues"]}
    assert found == expected, f"planner source issues: unexpected {sorted(found - expected)}, missing {sorted(expected - found)}"


def _expected_issues(source: dict, *, more: set[tuple[str, str]] = frozenset()) -> set[tuple[str, str]]:
    assets = {(code, row["asset_id"]) for row in source["assets"] for code in ASSET_SOURCE_WARNINGS}
    brokers = {(BROKER_PROFILE_ISSUE, row["broker_id"]) for row in source["brokers"]}
    return assets | brokers | set(more)


# ---------------------------------------------------------------------------
# Source → request, as the planner page composes it
# ---------------------------------------------------------------------------


_PLANNER_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:@/-]*")
_PLANNER_ID_KEPT = re.compile(r"[A-Za-z0-9.:@/-]")


def _planner_id(raw: str, max_length: int = 128) -> str:
    """A domain identifier in the planner's alphabet, as ``toPlannerId`` maps it in the page: a valid one unchanged, any
    other (a source reference with ``+``) as ``enc:`` plus its UTF-8 bytes escaped with ``_``."""
    if _PLANNER_ID.fullmatch(raw) and not raw.startswith("enc:") and len(raw) <= max_length:
        return raw
    encoded = "enc:" + "".join(char if _PLANNER_ID_KEPT.fullmatch(char) else "".join(f"_{byte:02x}" for byte in char.encode("utf-8")) for char in raw)
    assert len(encoded) <= max_length, f"identifier too long for the planner: {raw!r}"
    return encoded


def _planner_timestamp(text: str) -> str:
    """The source's timezone-aware timestamp as the planner's UTC ``…Z`` form (``toPlannerTimestamp`` in the page)."""
    return datetime.fromisoformat(text).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass
class _HandWritten:
    """HAND (P3): what the user writes in the page because no endpoint gives it yet."""

    # Order modes and fees of the Broker (until P1–P3): one mode in EUR, by amount in ``amount_step`` or by whole units.
    whole_units: bool = False
    amount_step: str = "1"
    fixed_fee: str | None = None
    # The Assets the Broker may buy (an unlisted Asset is excluded on the Broker), and the targets by Asset id.
    routed: list[int] = field(default_factory=list)
    targets: dict[int, str] = field(default_factory=dict)
    # Strategy and target fidelity (Rebalancer); the PAC's strategy is ``proportional``.
    target_fidelity: dict = field(default_factory=lambda: dict(BALANCED))


def _compose(source: dict, hand: _HandWritten, *, product: str) -> dict:
    """The request of ``product`` from the source's fields and the hand-written part; no constant of a portfolio here."""
    snapshot = source["snapshot"]
    captured_at = _planner_timestamp(snapshot["generated_at"])
    provenance: list[dict] = [
        {"kind": "domain_copy", "provenance_id": row["provenance_id"], "domain": row["domain"], "source_ref": _planner_id(row["source_ref"], 256), **({"source_label": row["source_label"]} if row["source_label"] else {}), "captured_at": _planner_timestamp(row["captured_at"])}
        for row in source["provenance"]
    ]
    provenance.append({"kind": "manual", "provenance_id": HAND_PROVENANCE_ID, "label": "Written by hand (no endpoint until P1-P3)", "entered_at": captured_at})

    prices = {row["asset_id"]: row for row in source["prices"]}
    assets = []
    for row in source["assets"]:
        price = prices[row["asset_id"]]
        assert None not in (price["amount"], price["currency"], price["quote_base_quantity"]), f"no saved price for {row['asset_id']}: {price}"
        exposures = [
            {"dimension": c["dimension"], "category_id": _planner_id(c["category_id"]), "label": c["label"], "weight": c["weight"], "provenance_id": c["provenance_id"]} for c in source["classifications"] if c["asset_id"] == row["asset_id"] and None not in (c["category_id"], c["label"], c["weight"])
        ]
        assets.append(
            {
                "asset_id": row["asset_id"],
                "identity": {"kind": "domain_asset", "source_asset_id": str(row["source_asset_id"]), "name": row["name"], "ticker": row["ticker"], "asset_class": row["asset_class"].lower()},
                "quote": {"amount": price["amount"], "currency": price["currency"], "quote_base_quantity": price["quote_base_quantity"], "provenance_id": price["provenance_id"]},
                "exposures": exposures,
            }
        )

    brokers, routes = [], []
    for row in source["brokers"]:
        broker_id = row["broker_id"]
        capability_id, fee_id = f"{broker_id}/mode:EUR", f"{broker_id}/fee:EUR:buy"
        # HAND (P3): the Broker's order mode and its fee schedule.
        capability = {"kind": "whole_quantity", "capability_id": capability_id, "quantity_unit": "asset_unit", "quantity_step": "1"} if hand.whole_units else {"kind": "monetary_amount", "capability_id": capability_id, "order_amount_step": {"amount": hand.amount_step, "currency": "EUR"}}
        fees = [] if hand.fixed_fee is None else [{"fee_schedule_id": fee_id, "capability_id": capability_id, "side": "buy", "fixed_fee": {"amount": hand.fixed_fee, "currency": "EUR"}}]
        brokers.append(
            {
                "broker_id": broker_id,
                "identity": {"kind": "domain_broker", "source_broker_id": str(row["source_broker_id"]), "name": row["name"], "active": row["active"]},
                "provenance_id": row["provenance_id"],
                "capabilities": [capability],
                "fee_schedules": fees,
                "conversion_mode": "manual",  # HAND (P3)
            }
        )
        # HAND (P3): one BUY route per Asset the Broker may buy.
        for asset_id in hand.routed:
            route = {"route_id": f"route:{_asset_key(source, asset_id)}:{broker_id}", "asset_id": _asset_key(source, asset_id), "broker_id": broker_id, "capability_id": capability_id, "side": "buy", "provenance_id": HAND_PROVENANCE_ID}
            routes.append(route | ({"fee_schedule_id": fee_id} if fees else {}))

    # Every cash row is copied with all of it selected, as the page does («whole available»).
    cash = [{"cash_id": row["cash_id"], "broker_id": row["broker_id"], "available": {"amount": row["custody_amount"], "currency": row["currency"]}, "selected": {"amount": row["custody_amount"], "currency": row["currency"]}, "provenance_id": row["provenance_id"]} for row in source["cash_balances"]]

    request: dict[str, Any] = {
        "operation": "plan",
        "snapshot": {"snapshot_id": f"t0-{uuid4().hex[:12]}", "draft_revision": 1, "captured_at": captured_at},
        "as_of": snapshot["as_of"],
        "valuation_currency": snapshot["target_currency"],
        "provenance": provenance,
        "fx_rates": {row["pair"]: row["rate"] for row in source["fx_quotes"] if row["rate"] is not None},
        "assets": assets,
        "brokers": brokers,
        "existing_cash": cash,
        "contributions": [],  # HAND (P3): none in these cases.
        "order_routes": routes,
        "target_weights": [{"kind": "asset", "asset_id": _asset_key(source, asset_id), "weight": weight} for asset_id, weight in hand.targets.items()],  # HAND (P3)
    }
    if product == PAC:
        return request | {"funding_routes": [], "policy": "proportional"}  # HAND (P3): strategy.
    holdings = [
        {
            "holding_id": row["holding_id"],
            "asset_id": row["asset_id"],
            "broker_id": row["broker_id"],
            "custody_quantity": row["custody_quantity"],
            "economic_share": row["ownership_share"],
            "planning_quantity": row["economic_quantity"],
            "quantity_unit": row["quantity_unit"],
            "provenance_id": row["provenance_id"],
        }
        for row in source["holdings"]
    ]
    return request | {"holdings": holdings, "policy": "invest_only", "target_fidelity": hand.target_fidelity}  # HAND (P3): strategy, fidelity.


# ---------------------------------------------------------------------------
# The served Tool
# ---------------------------------------------------------------------------


async def _descriptor(client: httpx.AsyncClient, tool_code: str) -> dict:
    response = await client.get(f"{API_BASE}/tools/catalog", timeout=TIMEOUT)
    assert response.status_code == 200, response.text
    descriptor = next((item for item in response.json()["items"] if item["tool_code"] == tool_code), None)
    assert descriptor is not None, f"{tool_code} is not served by the catalog"
    return descriptor


async def _plan(client: httpx.AsyncClient, tool_code: str, parameters: dict) -> tuple[dict, float]:
    """One ``plan`` item through ``POST /tools/compute``: the plan, and the engine window the worker claimed (seconds)."""
    descriptor = await _descriptor(client, tool_code)
    identity = {key: descriptor[key] for key in IDENTITY_KEYS}
    policy = next((p for p in descriptor["operations"] if p["operation"] == "plan"), None)
    assert policy is not None, f"{tool_code} serves no 'plan' operation"
    item = {"correlation_id": f"t0-{uuid4().hex}", **identity, "parameters": parameters}
    envelope = {"request_id": f"t0-request-{uuid4().hex}", "items": [item]}
    response = await client.post(f"{API_BASE}/tools/compute", json=envelope, timeout=COMPUTE_TIMEOUT)
    assert response.status_code == 200, response.text
    (result,) = (r for r in response.json()["results"] if r["correlation_id"] == item["correlation_id"])
    assert result["status"] == "success", f"{tool_code}: {result.get('error')}"
    assert {key: result[key] for key in IDENTITY_KEYS} == identity
    return result["result"], policy["engine_timeout_ms"] / 1000


def _in_process(product: str, request: dict, budget_seconds: float) -> dict:
    """The same request planned in this process, in the same engine window, dumped as the wire dumps it."""
    if product == PAC:
        return PAC_PLAN_OUTPUT_ADAPTER.dump_python(plan_pac_allocation(PAC_PLAN_INPUT_ADAPTER.validate_python(request), solver_time_budget_seconds=budget_seconds), mode="json", by_alias=True)
    return REBALANCER_PLAN_OUTPUT_ADAPTER.dump_python(plan_rebalancing(REBALANCER_PLAN_INPUT_ADAPTER.validate_python(request), solver_time_budget_seconds=budget_seconds), mode="json", by_alias=True)


def _exact(number: dict) -> Fraction:
    """An exact number of the wire (``finite_decimal`` or ``exact_ratio``) as a Fraction."""
    if number["kind"] == "finite_decimal":
        return Fraction(Decimal(number["value"]))
    assert number["kind"] == "exact_ratio", number
    return Fraction(int(number["numerator"]), int(number["denominator"]))


def _money(money: dict) -> Fraction:
    return _exact(money["value"])


def _orders(plan: dict) -> dict[str, dict]:
    rows = plan["primary_solution"]["order_rows"]
    by_asset = {row["asset_id"]: row for row in rows}
    assert len(by_asset) == len(rows), rows
    return by_asset


def _holding(source: dict, asset_id: int) -> dict:
    return next(row for row in source["holdings"] if row["asset_id"] == _asset_key(source, asset_id))


def _cash(source: dict, currency: str) -> dict:
    return next(row for row in source["cash_balances"] if row["currency"] == currency)


# ---------------------------------------------------------------------------
# T0-a: the PAC
# ---------------------------------------------------------------------------


async def _pac_portfolio(client: httpx.AsyncClient, owned: _Owned, *, prices: tuple[str, str], deposit: str) -> tuple[int, int, int, dict]:
    """A Broker with one deposit and two priced Assets, nothing held; its source."""
    broker_id = await _create_broker(client, owned)
    asset_a, asset_b = await _create_asset(client, owned), await _create_asset(client, owned)
    await _save_price(client, asset_a, AS_OF, prices[0])
    await _save_price(client, asset_b, AS_OF, prices[1])
    await _commit(client, [_deposit(broker_id, deposit)])
    source = await _source(client, broker_id=broker_id, asset_ids=[asset_a, asset_b])
    _assert_source_issues(source, _expected_issues(source))
    assert source["holdings"] == [], "precondition: the PAC case holds nothing"
    assert Decimal(_cash(source, "EUR")["custody_amount"]) == Decimal(deposit)
    return broker_id, asset_a, asset_b, source


@pytest.mark.asyncio
async def test_pac_plan_composed_from_the_endpoints_matches_the_hand_plan(test_server):
    """Test 1: a deposit of 1 000 EUR, A at 10 EUR and B at 20 EUR, whole units, no fee, targets 50/50 → buy 50 A
    (500 EUR) and 25 B (500 EUR): the only plan that lands both targets exactly, so the proven optimum."""
    async with _owner() as (client, owned):
        _broker_id, asset_a, asset_b, source = await _pac_portfolio(client, owned, prices=("10", "20"), deposit="1000")
        hand = _HandWritten(whole_units=True, routed=[asset_a, asset_b], targets={asset_a: "0.5", asset_b: "0.5"})
        plan, _budget = await _plan(client, PAC, _compose(source, hand, product=PAC))

    assert (plan["result_state"], plan["proof"]["kind"]) == ("ready_incumbent", "optimal_proven"), plan.get("issues")
    orders = _orders(plan)
    assert set(orders) == {_asset_key(source, asset_a), _asset_key(source, asset_b)}
    for asset_id, quantity, debit in ((asset_a, 50, 500), (asset_b, 25, 500)):
        order = orders[_asset_key(source, asset_id)]
        assert (order["instruction"]["kind"], Decimal(order["instruction"]["quantity"])) == ("whole_quantity", quantity), order
        assert (order["cash_debit"]["currency"], Decimal(order["cash_debit"]["amount"]), Decimal(order["fee"]["amount"])) == ("EUR", debit, 0), order


@pytest.mark.asyncio
async def test_pac_plan_over_http_equals_the_in_process_plan(test_server):
    """Test 2: a request composed from the endpoints (amounts in 1 EUR steps, 1 EUR a order) is planned over HTTP
    exactly as ``plan_pac_allocation`` plans it in process, in the engine window the catalog serves."""
    async with _owner() as (client, owned):
        _broker_id, asset_a, asset_b, source = await _pac_portfolio(client, owned, prices=("12.5", "40"), deposit="777")
        hand = _HandWritten(fixed_fee="1", routed=[asset_a, asset_b], targets={asset_a: "0.6", asset_b: "0.4"})
        request = _compose(source, hand, product=PAC)
        plan, budget = await _plan(client, PAC, request)

    assert (plan["result_state"], plan["proof"]["kind"]) == ("ready_incumbent", "optimal_proven"), plan.get("issues")
    assert plan["primary_solution"]["order_rows"], "positive control: the case must buy something"
    assert plan == _in_process(PAC, request, budget)


@pytest.mark.asyncio
async def test_source_reports_the_missing_broker_profile(test_server):
    """Test 3: until P3 the source has no execution profile of a Broker: it says ``not_available`` and raises
    ``allocation.broker_execution_profile_unsupported`` on it. When P3 brings the profile, this test turns red on purpose:
    the order modes and fees written by hand in this file (``# HAND (P3)``) then move to the source."""
    async with _owner() as (client, owned):
        broker_id = await _create_broker(client, owned)
        source = await _source(client, broker_id=broker_id, asset_ids=[], sections=["brokers"])

    (broker,) = source["brokers"]
    assert (broker["source_broker_id"], broker["execution_profile_status"]) == (broker_id, "not_available")
    profile = [issue for issue in source["issues"] if issue["code"] == BROKER_PROFILE_ISSUE]
    assert [(i["kind"], i["severity"], i["path"]["entity_id"], i["path"]["field"]) for i in profile] == [("unsupported", "error", broker["broker_id"], "execution_profile_status")]


# ---------------------------------------------------------------------------
# T0-b: the Rebalancer, «Invest only»
# ---------------------------------------------------------------------------


async def _rebalancer_portfolio(client: httpx.AsyncClient, owned: _Owned, *, held_b: str) -> tuple[int, int, dict]:
    """Specifica-REB §11 on the ledger: A and B at 1 EUR a unit, 5 000 of A and ``held_b`` of B bought from a deposit of
    10 000 EUR; the cash left is 10 000 − 5 000 − ``held_b``."""
    broker_id = await _create_broker(client, owned)
    asset_a, asset_b = await _create_asset(client, owned), await _create_asset(client, owned)
    await _save_price(client, asset_a, AS_OF, "1")
    await _save_price(client, asset_b, AS_OF, "1")
    await _commit(client, [_deposit(broker_id, "10000"), _buy(broker_id, asset_a, "5000", "5000"), _buy(broker_id, asset_b, held_b, held_b)])
    source = await _source(client, broker_id=broker_id, asset_ids=[asset_a, asset_b])
    _assert_source_issues(source, _expected_issues(source))
    for asset_id, quantity in ((asset_a, "5000"), (asset_b, held_b)):
        holding = _holding(source, asset_id)
        assert (Decimal(holding["custody_quantity"]), Decimal(holding["ownership_share"]), Decimal(holding["economic_quantity"])) == (Decimal(quantity), 1, Decimal(quantity)), holding
    assert Decimal(_cash(source, "EUR")["custody_amount"]) == 10_000 - 5_000 - Decimal(held_b)
    return asset_a, asset_b, source


def _t4_hand(asset_a: int, asset_b: int) -> _HandWritten:
    """HAND (P3): purchases by amount in 1 EUR steps, 5 EUR a order, targets 50/50, «Balanced»."""
    return _HandWritten(amount_step="1", fixed_fee="5", routed=[asset_a, asset_b], targets={asset_a: "0.5", asset_b: "0.5"})


@pytest.mark.asyncio
async def test_rebalancer_invest_only_from_the_portfolio_buys_the_gap(test_server):
    """Test 4 (T4): 5 000 of A, 4 800 of B and 200 EUR of cash, built with transactions and prices → one purchase of 195 of
    B (5 EUR of fee), proven optimal, J = λ·D/F + money lost = 1 × 50/10 000 + 5 = 1 001/200; the same plan in process."""
    async with _owner() as (client, owned):
        asset_a, asset_b, source = await _rebalancer_portfolio(client, owned, held_b="4800")
        request = _compose(source, _t4_hand(asset_a, asset_b), product=REBALANCER)
        plan, budget = await _plan(client, REBALANCER, request)

    assert (plan["result_state"], plan["proof"]["kind"]) == ("ready_incumbent", "optimal_proven"), plan.get("issues")
    (order,) = plan["primary_solution"]["order_rows"]
    assert (order["asset_id"], order["instruction"]["kind"]) == (_asset_key(source, asset_b), "monetary_amount")
    assert (Decimal(order["instruction"]["amount"]["amount"]), order["instruction"]["amount"]["currency"], Decimal(order["fee"]["amount"])) == (195, "EUR", 5)
    assert _money(plan["primary_solution"]["score"]["plan_score"]) == Fraction(1_001, 200)
    assert plan == _in_process(REBALANCER, request, budget)


@pytest.mark.asyncio
async def test_rebalancer_leaves_small_cash_idle(test_server):
    """Test 5 (T5): 5 000 of A, 4 900 of B and 100 EUR of cash → no operation at «Balanced»: D = 20 000, nothing lost,
    J = 1 × 20 000/10 000 = 2 (a purchase of 95 of B would score 1 001/200)."""
    async with _owner() as (client, owned):
        asset_a, asset_b, source = await _rebalancer_portfolio(client, owned, held_b="4900")
        request = _compose(source, _t4_hand(asset_a, asset_b), product=REBALANCER)
        plan, budget = await _plan(client, REBALANCER, request)

    assert (plan["result_state"], plan["proof"]["kind"]) == ("ready_no_op", "optimal_proven"), plan.get("issues")
    assert plan["primary_solution"]["order_rows"] == []
    score = plan["primary_solution"]["score"]
    assert (_exact(score["distance_weight"]), _exact(score["target_distance"]), _money(score["wealth_loss"]), _money(score["plan_score"])) == (1, 20_000, 0, 2)
    assert plan == _in_process(REBALANCER, request, budget)


@pytest.mark.asyncio
async def test_rebalancer_without_holdings_points_to_the_pac(test_server):
    """Test 6 (V9): an account with cash only (a deposit, a priced Asset never bought) → ``needs_input`` with
    ``portfolio_rebalancer.holdings_missing``: with nothing held there is nothing to rebalance, the PAC is the tool."""
    async with _owner() as (client, owned):
        broker_id = await _create_broker(client, owned)
        asset_id = await _create_asset(client, owned)
        await _save_price(client, asset_id, AS_OF, "1")
        await _commit(client, [_deposit(broker_id, "1000")])
        source = await _source(client, broker_id=broker_id, asset_ids=[asset_id])
        _assert_source_issues(source, _expected_issues(source))
        assert source["holdings"] == [], "precondition: nothing is held"
        assert [(row["currency"], Decimal(row["custody_amount"])) for row in source["cash_balances"]] == [("EUR", 1000)], "precondition: one cash row"
        hand = _HandWritten(fixed_fee="5", routed=[asset_id], targets={asset_id: "1"})
        plan, _budget = await _plan(client, REBALANCER, _compose(source, hand, product=REBALANCER))

    assert (plan["result_state"], plan["availability"]) == ("needs_input", "needs_input")
    assert "primary_solution" not in plan
    assert "portfolio_rebalancer.holdings_missing" in {issue["code"] for issue in plan["issues"]}


@pytest.mark.asyncio
async def test_plan_with_a_saved_fx_rate_read_from_the_source(test_server):
    """Test 7 (T4 with a USD Asset, D13 = a): the EUR/USD rate is the one ``db populate`` saved, read from the source and
    never written. A is quoted in USD at that rate r: 5 000 units are worth 5 000·r/r = 5 000 EUR, so the case is T4
    again (buy 195 of B, J = 1 001/200) and A's value before the plan is computed from the rate read. A has no buy route
    on the Broker (excluded by hand), so the plan needs no conversion."""
    async with _owner() as (client, owned):
        broker_id = await _create_broker(client, owned)
        # The rate first: the latest saved EUR/USD at or before today, and its day becomes the plan's day.
        probe = await _source(client, broker_id=broker_id, asset_ids=[], sections=["fx_quotes"], fx_pairs=["EUR/USD"], as_of=date.today())
        (quote,) = probe["fx_quotes"]
        assert quote["rate"] is not None, f"no saved EUR/USD rate (run ./dev.py test db populate): source issues {[i['code'] for i in probe['issues']]}"
        rate, as_of = Decimal(quote["rate"]), date.fromisoformat(quote["reference_date"])

        asset_a, asset_b = await _create_asset(client, owned, currency="USD"), await _create_asset(client, owned)
        await _save_price(client, asset_a, as_of, quote["rate"])
        await _save_price(client, asset_b, as_of, "1")
        await _commit(
            client,
            [
                _deposit(broker_id, "5000", day=as_of),
                _buy(broker_id, asset_b, "4800", "4800", day=as_of),
                _deposit(broker_id, "6000", currency="USD", day=as_of),
                _buy(broker_id, asset_a, "5000", "6000", currency="USD", day=as_of),
            ],
        )
        source = await _source(client, broker_id=broker_id, asset_ids=[asset_a, asset_b], fx_pairs=["EUR/USD"], as_of=as_of)
        _assert_source_issues(source, _expected_issues(source))
        (read,) = source["fx_quotes"]
        assert (read["pair"], Decimal(read["rate"]), read["reference_date"]) == ("EUR/USD", rate, as_of.isoformat()), read
        price_a = next(row for row in source["prices"] if row["asset_id"] == _asset_key(source, asset_a))
        assert (price_a["currency"], Decimal(price_a["amount"])) == ("USD", rate), price_a
        quantity_a = Decimal(_holding(source, asset_a)["economic_quantity"])
        value_a = Fraction(quantity_a) * Fraction(Decimal(price_a["amount"])) / Fraction(Decimal(read["rate"]))
        assert value_a == 5_000, "A is worth 5 000 EUR at the rate read: the expectations below are T4's"
        assert Decimal(_cash(source, "EUR")["custody_amount"]) == 200

        hand = _t4_hand(asset_a, asset_b)
        hand.routed = [asset_b]  # HAND (P3): A excluded on this Broker, so no EUR → USD conversion enters the plan.
        request = _compose(source, hand, product=REBALANCER)
        assert request["fx_rates"] == {"EUR/USD": read["rate"]}, "the request carries the rate the source read"
        plan, budget = await _plan(client, REBALANCER, request)

    assert (plan["result_state"], plan["proof"]["kind"]) == ("ready_incumbent", "optimal_proven"), plan.get("issues")
    row_a = next(row for row in plan["primary_solution"]["asset_rows"] if row["asset_id"] == _asset_key(source, asset_a))
    assert (_money(row_a["before_value"]), row_a["before_value"]["currency"]) == (value_a, "EUR")
    (order,) = plan["primary_solution"]["order_rows"]
    assert (order["asset_id"], Decimal(order["instruction"]["amount"]["amount"]), Decimal(order["fee"]["amount"])) == (_asset_key(source, asset_b), 195, 5)
    assert _money(plan["primary_solution"]["score"]["plan_score"]) == Fraction(1_001, 200)
    assert plan == _in_process(REBALANCER, request, budget)
