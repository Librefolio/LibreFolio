"""Synthetic PAC planner requests for the solver-robustness tests and probe.

``make``/``V``: a multi-broker grid (EUR ETFs at 20.00, 27.50, 35.00, …; every asset buyable on
every broker, or on exactly one with ``disjoint``). ``realistic_make``: cent prices, uneven
weights, three real-like fee schedules, uneven cash. ``scaled``: every money amount ×10**k.
Every builder returns a fresh wire dict; ``scenario_of`` normalizes it into ``(scenario, view)``.

Everything is rebuilt from the repository's min fixture, so a change to that fixture's shape
reaches these requests too. Not a test module (leading underscore): pytest never collects it,
and the runner catalogue does not list it.
"""

from __future__ import annotations

import copy
import json
from decimal import Decimal
from pathlib import Path

from backend.app.schemas.pac_allocator import PacPlannerRequest
from backend.app.services.pac_allocator.evaluator import build_exact_policy_view
from backend.app.services.pac_allocator.models import ExactPlannerScenario, ExactPolicyView
from backend.app.services.pac_allocator.normalize import normalize_pac_plan

# Resolved from this file, not from the working directory: parents = [test_services, test_scripts].
FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "pac_allocator" / "pac_plan_request.min.v2.json"


def _equal_weights(n_assets: int) -> list[Decimal]:
    """Equal six-decimal weights that total exactly one.

    The first weight absorbs the rounding remainder: three assets at 0.333333 total 0.999999,
    which the normalizer rejects (``allocation.target_total_not_one``). For 1, 2, 5 and 10
    assets the remainder is zero and nothing changes.
    """
    if n_assets == 10:
        return [Decimal("0.1")] * 10
    weights = [Decimal(f"{1 / n_assets:.6f}")] * n_assets
    weights[0] += Decimal(1) - sum(weights)
    return weights


def make(
    n_assets: int,
    n_brokers: int,
    *,
    disjoint: bool = False,
    fixed: tuple[str, ...] = ("0", "1.00"),
    rate: str = "0.001",
    cash: tuple[str, ...] = ("1500.00", "1500.00"),
    floor: str = "0",
    capamt: str = "10.00",
    step: str = "1",
) -> dict:
    """A grid of ``n_assets`` EUR ETFs and ``n_brokers`` brokers, equal weights, proportional policy.

    ``fixed`` and ``cash`` are per broker; ``rate``, ``floor`` and ``capamt`` (the variable-fee cap)
    are shared. Route priority is the broker's position (1, 2, …); every route is capped at 1000 units.
    """
    base = json.loads(FIXTURE.read_text())
    asset0, broker0, route0 = base["assets"][0], base["brokers"][0], base["order_routes"][0]
    assets, brokers, routes, cashes, weights = [], [], [], [], []
    for i, weight in enumerate(_equal_weights(n_assets)):
        asset = copy.deepcopy(asset0)
        asset["asset_id"] = f"asset-{i:02d}"
        asset["identity"].update(name=f"Synthetic ETF {i:02d}", ticker=f"SYN{i:02d}")
        asset["quote"]["amount"] = f"{20 + 7.5 * i:.2f}"
        assets.append(asset)
        weights.append({"asset_id": asset["asset_id"], "weight": str(weight)})
    for j in range(n_brokers):
        broker = copy.deepcopy(broker0)
        broker_id = f"broker-{j:02d}"
        broker["broker_id"] = broker_id
        broker["identity"]["name"] = f"Synthetic Broker {j:02d}"
        capability = broker["capabilities"][0]
        capability["capability_id"] = f"cap-{broker_id}-eur-whole"
        capability["quantity_step"] = step
        if step != "1":
            capability["kind"] = "fractional_quantity"
        fee = broker["fee_schedules"][0]
        fee.update(fee_schedule_id=f"fee-{broker_id}-eur-buy", capability_id=capability["capability_id"], rate=rate)
        fee["fixed_fee"]["amount"] = fixed[j]
        fee["variable_floor"]["amount"] = floor
        fee["variable_cap"]["amount"]["amount"] = capamt
        brokers.append(broker)
        cashes.append({"cash_id": f"cash-{broker_id}-eur", "broker_id": broker_id, "available": {"amount": cash[j], "currency": "EUR"}, "selected": {"amount": cash[j], "currency": "EUR"}, "provenance_id": "prov-manual"})
        for i in range(n_assets):
            if disjoint and i % n_brokers != j:
                continue
            route = copy.deepcopy(route0)
            route.update(route_id=f"route-asset-{i:02d}-{broker_id}-buy", asset_id=f"asset-{i:02d}", broker_id=broker_id, capability_id=capability["capability_id"], fee_schedule_id=fee["fee_schedule_id"], priority=j + 1)
            route["cap"]["quantity"] = "1000"
            routes.append(route)
    base.update(assets=assets, brokers=brokers, existing_cash=cashes, order_routes=routes, target_weights=weights, policy="proportional")
    base["snapshot"]["snapshot_id"] = "snapshot-pac-medium-proportional"
    return base


# The measured grid: ``make(**V[name])``.
V = {
    "5x1": {"n_assets": 5, "n_brokers": 1, "cash": ("1500.00",)},
    "5x1_3000": {"n_assets": 5, "n_brokers": 1, "cash": ("3000.00",)},
    "5x2": {"n_assets": 5, "n_brokers": 2},
    "5x2_samefee": {"n_assets": 5, "n_brokers": 2, "fixed": ("0", "0")},
    "5x2_nofee": {"n_assets": 5, "n_brokers": 2, "fixed": ("0", "0"), "rate": "0", "capamt": "0"},
    "5x2_fixedonly": {"n_assets": 5, "n_brokers": 2, "rate": "0", "capamt": "0"},
    "5x2_ratezero_fixed_both": {"n_assets": 5, "n_brokers": 2, "fixed": ("1.00", "1.00"), "rate": "0", "capamt": "0"},
    "5x2_cash1": {"n_assets": 5, "n_brokers": 2, "cash": ("3000.00", "0")},
    "5x2_disjoint": {"n_assets": 5, "n_brokers": 2, "disjoint": True},
    "10x1": {"n_assets": 10, "n_brokers": 1, "cash": ("1500.00",)},
    "10x2": {"n_assets": 10, "n_brokers": 2},
    "10x2_disjoint": {"n_assets": 10, "n_brokers": 2, "disjoint": True},
    "2x2": {"n_assets": 2, "n_brokers": 2},
    "3x2": {"n_assets": 3, "n_brokers": 2},
    "1x2": {"n_assets": 1, "n_brokers": 2},
}

PRICES = ("112.37", "87.64", "31.29", "245.80", "9.87", "64.12", "5.43", "412.55", "18.96", "53.07", "141.18", "27.35")
RAW_WEIGHTS = (35, 20, 15, 10, 8, 5, 3, 2, 1, 1, 1, 1)
# (fixed, rate, floor, cap) per broker: percentage with floor and cap, flat 0.99, flat 2.00
FEES = (("0", "0.0019", "1.50", "18.00"), ("0.99", "0", "0", "0"), ("2.00", "0", "0", "0"))
CASH = ("1200.00", "800.00", "500.00")


def realistic_make(n_assets: int, n_brokers: int) -> dict:
    """Up to 12 assets at cent prices with uneven weights, on up to 3 brokers with real-like fees and cash.

    Weights are ``RAW_WEIGHTS`` normalized to four decimals, the first absorbing the remainder;
    every asset is buyable on every broker, with the broker's position as route priority.
    """
    base = json.loads(FIXTURE.read_text())
    asset0, broker0, route0 = base["assets"][0], base["brokers"][0], base["order_routes"][0]
    raw = RAW_WEIGHTS[:n_assets]
    total = sum(raw)
    shares = [(Decimal(x) / total).quantize(Decimal("0.0001")) for x in raw]
    shares[0] += Decimal(1) - sum(shares)
    assets, brokers, routes, cashes, weights = [], [], [], [], []
    for i in range(n_assets):
        asset = copy.deepcopy(asset0)
        asset["asset_id"] = f"asset-{i:02d}"
        asset["identity"].update(name=f"Realistic ETF {i:02d}", ticker=f"RLE{i:02d}")
        asset["quote"]["amount"] = PRICES[i]
        assets.append(asset)
        weights.append({"asset_id": asset["asset_id"], "weight": str(shares[i])})
    for j in range(n_brokers):
        broker = copy.deepcopy(broker0)
        broker_id = f"broker-{j:02d}"
        broker["broker_id"] = broker_id
        broker["identity"]["name"] = f"Realistic Broker {j:02d}"
        capability = broker["capabilities"][0]
        capability["capability_id"] = f"cap-{broker_id}-eur-whole"
        fee = broker["fee_schedules"][0]
        fixed, rate, floor, cap = FEES[j]
        fee.update(fee_schedule_id=f"fee-{broker_id}-eur-buy", capability_id=capability["capability_id"], rate=rate)
        fee["fixed_fee"]["amount"] = fixed
        fee["variable_floor"]["amount"] = floor
        fee["variable_cap"]["amount"]["amount"] = cap
        brokers.append(broker)
        cashes.append({"cash_id": f"cash-{broker_id}-eur", "broker_id": broker_id, "available": {"amount": CASH[j], "currency": "EUR"}, "selected": {"amount": CASH[j], "currency": "EUR"}, "provenance_id": "prov-manual"})
        for i in range(n_assets):
            route = copy.deepcopy(route0)
            route.update(route_id=f"route-asset-{i:02d}-{broker_id}-buy", asset_id=f"asset-{i:02d}", broker_id=broker_id, capability_id=capability["capability_id"], fee_schedule_id=fee["fee_schedule_id"], priority=j + 1)
            route["cap"]["quantity"] = "1000"
            routes.append(route)
    base.update(assets=assets, brokers=brokers, existing_cash=cashes, order_routes=routes, target_weights=weights, policy="proportional")
    base["snapshot"]["snapshot_id"] = f"snapshot-realistic-{n_assets}x{n_brokers}"
    return base


def scaled(payload: dict, k: int) -> dict:
    """The same request with every money amount (quotes, cash, fee fixed/floor/cap) multiplied by 10**k."""
    result = copy.deepcopy(payload)
    factor = Decimal(10) ** k

    def mul(text: str) -> str:
        return format(Decimal(text) * factor, "f")

    for asset in result["assets"]:
        asset["quote"]["amount"] = mul(asset["quote"]["amount"])
    for cash in result["existing_cash"]:
        cash["available"]["amount"] = mul(cash["available"]["amount"])
        cash["selected"]["amount"] = mul(cash["selected"]["amount"])
    for broker in result["brokers"]:
        for fee in broker["fee_schedules"]:
            fee["fixed_fee"]["amount"] = mul(fee["fixed_fee"]["amount"])
            fee["variable_floor"]["amount"] = mul(fee["variable_floor"]["amount"])
            fee["variable_cap"]["amount"]["amount"] = mul(fee["variable_cap"]["amount"]["amount"])
    return result


def scenario_of(payload: dict) -> tuple[ExactPlannerScenario, ExactPolicyView]:
    """Normalize ``payload`` (it must be ready) and build its primary exact policy view."""
    outcome = normalize_pac_plan(PacPlannerRequest.model_validate(payload))
    assert outcome.ready, f"synthetic request must normalize: {[issue.code for issue in outcome.issues]}"
    scenario = outcome.normalized
    return scenario, build_exact_policy_view(scenario, purpose="primary")
