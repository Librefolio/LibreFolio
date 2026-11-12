"""Decision-independent scenario facts for the constraint builders: the floating-point projection of the exact scenario
(``ScenarioFacts``), the FX and price lookups over it, and the variable container every builder shares.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.app.services.financial_math.fx_rates import oriented_rate
from backend.app.services.pac_allocator.models import ExactFeeSchedule, ExactOrderCapability, ExactOrderRoute, ExactPlannerScenario
from backend.app.services.pac_allocator.numeric import ExactRatio

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Expr, Variable

    LinearTerm = float | Expr


def as_float(value: ExactRatio) -> float:
    """Project one exact rational to a float for the floating SCIP model.

    Only ever used to *search*; every candidate the solver proposes is
    replayed through ``evaluate_exact_candidate`` (pure ``ExactRatio``) before
    it is trusted, so this projection cannot leak into a reported number.
    """
    return value.numerator / value.denominator


@dataclass(frozen=True, slots=True)
class ScenarioFacts:
    """Pure, decision-independent scenario facts, derived only from public
    ``ExactPlannerScenario`` fields (deliberately not the evaluator's internal
    ``evaluation/scenario.py`` ``ScenarioIndex`` — see Step3 §16.9 for why: this module must
    stay buildable without reaching into another module's internals).
    """

    valuation_currency: str
    currency_quantum: dict[str, float]
    fx_rate_by_pair: dict[str, float]
    fx_spread_rate: float
    assets_by_id: dict[str, str]  # asset_id -> quote currency (all this module needs of an Asset)
    mid_native_by_asset: dict[str, float]
    capability_by_key: dict[tuple[str, str], ExactOrderCapability]
    fee_by_key: dict[tuple[str, str], ExactFeeSchedule]


def _fx_pair_key(first: str, second: str) -> str:
    return "/".join(sorted((first, second)))


def fx_rate(facts: ScenarioFacts, source_currency: str, destination_currency: str) -> float:
    """Return units of ``destination_currency`` per unit of ``source_currency``.

    Mirrors ``evaluation.scenario.fx_rate`` (same direct-pair lookup over the same alphabetically-ordered pair keys)
    but is re-derived here from the public ``ScenarioFacts.fx_rate_by_pair`` rather than imported, since the
    evaluator's version is a private helper. The orientation of the stored rate is the house's ``oriented_rate``.
    """
    if source_currency == destination_currency:
        return 1.0
    rate = facts.fx_rate_by_pair.get(_fx_pair_key(source_currency, destination_currency))
    if rate is None:
        raise KeyError(f"missing direct FX rate for {source_currency}/{destination_currency}")
    return oriented_rate(rate, source_currency, destination_currency)


def valuation_rate(facts: ScenarioFacts, currency: str) -> float:
    """Units of the scenario's valuation currency per unit of ``currency``."""
    return fx_rate(facts, currency, facts.valuation_currency)


def planning_fx_rate(facts: ScenarioFacts, source_currency: str, destination_currency: str) -> float:
    """Mirror ``numeric.calculate_planning_fx_rate``: the spread rate, capped
    at the triangle through the valuation currency.
    """
    effective_rate = fx_rate(facts, source_currency, destination_currency) * (1.0 - facts.fx_spread_rate)
    return min(effective_rate, valuation_rate(facts, source_currency) / valuation_rate(facts, destination_currency))


def order_prices(facts: ScenarioFacts, route: ExactOrderRoute) -> tuple[float, float]:
    """Return ``(mid_native, execution_native)`` for one order route.

    Mirrors ``evaluation.scenario.order_prices``: the execution side applies the
    route's own margin against the Asset's scenario-constant mid price.
    """
    mid_native = facts.mid_native_by_asset[route.asset_id]
    margin = as_float(route.execution_margin_rate)
    execution_native = mid_native * (1.0 + margin) if route.side == "buy" else mid_native * (1.0 - margin)
    return mid_native, execution_native


def order_notional(facts: ScenarioFacts, route: ExactOrderRoute, capability: ExactOrderCapability, measure: LinearTerm) -> LinearTerm:
    """Return the fee-schedule ``notional`` (always quote-currency cash) for
    ``measure = order_step * decision_quanta``, mirroring the ``exact_cash``
    branch evaluator.py's ``_evaluate_orders`` computes per capability kind.
    """
    if capability.kind == "whole_quantity":
        _, execution_native = order_prices(facts, route)
        return measure * execution_native
    return measure


def build_scenario_facts(scenario: ExactPlannerScenario) -> ScenarioFacts:
    fx_rate_by_pair = {item.pair_key: as_float(item.rate) for item in scenario.fx_rates}
    currency_quantum = {item.currency: as_float(item.minor_unit) for item in scenario.currency_specs}
    assets_by_id = {asset.asset_id: asset.quote.price.currency for asset in scenario.assets}
    mid_native_by_asset = {asset.asset_id: as_float(asset.quote.price.amount) / as_float(asset.quote.quote_base_quantity) for asset in scenario.assets}
    capability_by_key: dict[tuple[str, str], ExactOrderCapability] = {}
    fee_by_key: dict[tuple[str, str], ExactFeeSchedule] = {}
    for broker in scenario.brokers:
        for capability in broker.capabilities:
            capability_by_key[(broker.broker_id, capability.capability_id)] = capability
        for fee in broker.fee_schedules:
            fee_by_key[(broker.broker_id, fee.fee_schedule_id)] = fee
    return ScenarioFacts(
        valuation_currency=scenario.valuation_currency,
        currency_quantum=currency_quantum,
        fx_rate_by_pair=fx_rate_by_pair,
        fx_spread_rate=as_float(scenario.fx_spread_rate),
        assets_by_id=assets_by_id,
        mid_native_by_asset=mid_native_by_asset,
        capability_by_key=capability_by_key,
        fee_by_key=fee_by_key,
    )


def buy_pool_currencies(scenario: ExactPlannerScenario, facts: ScenarioFacts, *, broker_id: str, quote_currency: str) -> tuple[str, ...]:
    """Mirror ``evaluation.reachability.buy_pool_currencies`` exactly: currencies that hold
    (or can hold) cash at ``broker_id`` and have a direct FX pair to
    ``quote_currency`` — anti-cascade, one hop only.
    """
    candidates: set[str] = set()
    for cash in scenario.existing_cash:
        if cash.broker_id == broker_id:
            candidates.add(cash.selected.currency)
    for route in scenario.funding_routes:
        if route.broker_id == broker_id:
            candidates.add(route.currency)
    for other in scenario.order_routes:
        if other.broker_id == broker_id and other.side == "sell":
            candidates.add(facts.assets_by_id[other.asset_id])
    candidates.discard(quote_currency)
    return tuple(sorted(currency for currency in candidates if _fx_pair_key(currency, quote_currency) in facts.fx_rate_by_pair))


@dataclass(frozen=True, slots=True)
class CompiledVariables:
    """All SCIP decision variables, keyed for both constraint and objective builders."""

    quanta: dict[str, Variable]  # decision_id -> integer var, every DecisionAccess row
    buy_active: dict[str, Variable]  # buy order_route_id -> binary var
    funding_active: dict[str, Variable]  # funding route_id -> binary var
    buy_fee: dict[str, Variable]  # buy order_route_id -> continuous fee var (quote currency), every buy route


def _minimum_value(route: ExactOrderRoute, field: str) -> float:
    # ``ExactOrderMinimum.__post_init__`` already forces ``value == 0`` when
    # ``kind == "none"``, so the raw value is always the right magnitude to
    # compare against ``measure`` directly, exactly as evaluator.py does.
    return as_float(getattr(route, field).value)
