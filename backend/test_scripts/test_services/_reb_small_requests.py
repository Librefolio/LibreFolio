"""The small Rebalancer cases (specifica-REB §11) as wire requests: T1, T4, T5, T6 for ``plan_rebalancing``, the Tool and its API.

Not collected by pytest (leading underscore). The same conventions as ``_reb_small_cases.py``, which builds them as exact
scenarios: valuation currency EUR, one Broker ``broker-x``, Assets priced 1 EUR a unit (T6: 4 000), purchases by amount in
steps of ``amount_step`` EUR (T6: whole units), a fixed fee of 5 EUR an order. «Invest only», the fidelity «Balanced»
unless a case says otherwise. Lot B3 of project 67 brings them in.
"""

from __future__ import annotations

from typing import Any

JsonObject = dict[str, Any]
BROKER = "broker-x"
PROVENANCE = "prov-reb-small"
_AT = "2026-11-13T20:00:00Z"
BALANCED = {"kind": "level", "level": "balanced"}
FAITHFUL = {"kind": "level", "level": "faithful"}


def _money(amount: str) -> JsonObject:
    return {"amount": amount, "currency": "EUR"}


def request(
    name: str,
    *,
    holdings: dict[str, str],
    cash: str | None,
    weights: dict[str, str],
    prices: dict[str, str] | None = None,
    whole_units: frozenset[str] = frozenset(),
    amount_step: str = "1",
    fidelity: JsonObject | None = None,
) -> JsonObject:
    """A Rebalancer «Invest only» request on one Broker. ``cash`` is the selected cash of the Broker's EUR cell; ``None``
    omits the cash row altogether (no cash at all, which «Invest only» refuses)."""
    price_by_asset = dict.fromkeys(weights, "1") | (prices or {})
    capabilities = [{"kind": "monetary_amount", "capability_id": "cap-eur-amount", "order_amount_step": _money(amount_step)}]
    if whole_units:
        capabilities.append({"kind": "whole_quantity", "capability_id": "cap-eur-units", "quantity_unit": "asset_unit", "quantity_step": "1"})
    fees = [{"fee_schedule_id": f"fee-{capability['capability_id']}", "capability_id": capability["capability_id"], "side": "buy", "fixed_fee": _money("5"), "rate": "0"} for capability in capabilities]
    return {
        "operation": "plan",
        "snapshot": {"snapshot_id": f"snapshot-reb-small-{name}", "draft_revision": 1, "captured_at": _AT},
        "as_of": "2026-11-13",
        "valuation_currency": "EUR",
        "provenance": [{"kind": "manual", "provenance_id": PROVENANCE, "label": "Rebalancer small cases", "entered_at": _AT}],
        "assets": [
            {
                "asset_id": asset_id,
                "identity": {"kind": "manual_asset", "name": f"Asset {asset_id}", "ticker": None, "asset_class": "etf"},
                "quote": {"amount": price_by_asset[asset_id], "currency": "EUR", "quote_base_quantity": "1", "provenance_id": PROVENANCE},
                "exposures": [{"dimension": "asset_type", "category_id": "equity", "label": "Equity", "weight": "1", "provenance_id": PROVENANCE}],
            }
            for asset_id in weights
        ],
        "brokers": [{"broker_id": BROKER, "identity": {"kind": "manual_broker", "name": "Broker X"}, "provenance_id": PROVENANCE, "capabilities": capabilities, "fee_schedules": fees, "conversion_mode": "manual"}],
        "holdings": [
            {"holding_id": f"holding-{asset_id}", "asset_id": asset_id, "broker_id": BROKER, "custody_quantity": quantity, "economic_share": "1", "planning_quantity": quantity, "quantity_unit": "asset_unit", "provenance_id": PROVENANCE} for asset_id, quantity in holdings.items() if quantity != "0"
        ],
        "existing_cash": [] if cash is None else [{"cash_id": "cash-x-eur", "broker_id": BROKER, "available": _money(cash), "selected": _money(cash), "provenance_id": PROVENANCE}],
        "order_routes": [
            {
                "route_id": f"route-buy-{asset_id}",
                "asset_id": asset_id,
                "broker_id": BROKER,
                "capability_id": "cap-eur-units" if asset_id in whole_units else "cap-eur-amount",
                "side": "buy",
                "fee_schedule_id": "fee-cap-eur-units" if asset_id in whole_units else "fee-cap-eur-amount",
                "provenance_id": PROVENANCE,
            }
            for asset_id in weights
        ],
        "target_weights": [{"kind": "asset", "asset_id": asset_id, "weight": weight, "minimum": None, "maximum": None} for asset_id, weight in weights.items()],
        "policy": "invest_only",
        "target_fidelity": fidelity or BALANCED,
    }


def buy_route(asset_id: str) -> str:
    return f"route-buy-{asset_id}"


def t1(**fields) -> JsonObject:
    """T1: A 5 040, B 4 960, a cash row selected at zero (with no cash row at all «Invest only» answers
    ``allocation.no_selected_funding``); the best plan is no operation."""
    return request("t1", holdings={"asset-a": "5040", "asset-b": "4960"}, cash=fields.pop("cash", "0"), weights={"asset-a": "0.5", "asset-b": "0.5"}, **fields)


def t4(**fields) -> JsonObject:
    """T4: A 5 000, B 4 800, cash 200; the best plan buys 195 of B (5 EUR of fee)."""
    return request("t4", holdings={"asset-a": "5000", "asset-b": "4800"}, cash="200", weights={"asset-a": "0.5", "asset-b": "0.5"}, **fields)


def t5(**fields) -> JsonObject:
    """T5: A 5 000, B 4 900, cash 100; at «Balanced» the best plan is no operation."""
    return request("t5", holdings={"asset-a": "5000", "asset-b": "4900"}, cash="100", weights={"asset-a": "0.5", "asset-b": "0.5"}, **fields)


def t6(**fields) -> JsonObject:
    """T6: one Asset at 4 000 EUR a unit, one unit held, cash 6 000, «Faithful» (``λ = 4``); the best plan buys one unit."""
    return request("t6", holdings={"asset-a": "1"}, cash="6000", weights={"asset-a": "1"}, prices={"asset-a": "4000"}, whole_units=frozenset({"asset-a"}), **({"fidelity": FAITHFUL} | fields))


HELD_BROKER = "broker-held"


def with_positions_only_broker(payload: JsonObject, *, asset_id: str = "asset-a", quantity: str = "1000") -> JsonObject:
    """``payload`` plus a «positions only» Broker (Q-F3a-5b of project 67): it holds ``quantity`` of ``asset_id`` and has no
    order mode, no fee, no cash and no route — what the planner sends for a Broker outside the scenario that holds a position.
    """
    payload = {**payload}
    payload["brokers"] = [*payload["brokers"], {"broker_id": HELD_BROKER, "identity": {"kind": "domain_broker", "source_broker_id": "9", "name": "Held Broker", "active": True}, "provenance_id": PROVENANCE, "conversion_mode": "manual"}]
    payload["holdings"] = [
        *payload["holdings"],
        {"holding_id": f"holding-held-{asset_id}", "asset_id": asset_id, "broker_id": HELD_BROKER, "custody_quantity": quantity, "economic_share": "1", "planning_quantity": quantity, "quantity_unit": "asset_unit", "provenance_id": PROVENANCE},
    ]
    return payload
