"""Contract tests for the PAC/Rebalancer SCIP policy compiler (Step 3, Stage 2).

Covers the three new production modules that turn one `ExactPolicyView` into
one SCIP `pyscipopt.Model`, ready for `solver.py`'s (Stage 3, not yet built)
lexicographic re-optimization loop:

  * `constraints.py` -- `ScenarioFacts`, `CompiledVariables`, the pure
    lookup helpers (`fx_rate`, `valuation_rate`, `order_prices`,
    `order_notional`, `buy_pool_currencies`, `as_float`), and every hard
    constraint builder.
  * `objectives.py` -- the five named objective-cascade stages plus the
    canonical tie-break stages.
  * `compiler.py` -- `compile_policy_program`, the single top-level entry
    point, and its scope guard (`PolicyProgramScopeError`).

Scope for this build (and therefore for every fixture below): PAC
`proportional` policy, `primary` purpose only -- no other product/policy/
purpose combination is implemented, and `solver.py` does not exist yet.
Nothing here searches or optimizes in the ordinary MIP sense: every model
built below has its `quanta` decisions pinned to one concrete candidate
before `model.optimize()` is ever called, so SCIP is only ever asked to
certify one already-fully-determined point (or, for the objective-stage
checks, to resolve the handful of continuous epigraph/activation variables
that pinning the integer decisions does not by itself fix) -- a
single-point-feasible-region MIP, which SCIP solves instantly.

Three ready-made scenario fixtures come from the sibling oracle suite
(`_two_asset_pac_scenario`, `_coarse_funding_fx_scenario`,
`_credit_tie_fx_scenario` -- `test_pac_planner_oracle.py`), and every
scenario-construction primitive comes from `test_pac_planner_evaluator.py`
-- both already-established, precedented cross-test-file imports in this
package. The handful of scenarios that are genuinely new to this file exist
because they exercise something no sibling fixture does: two BUY routes
sharing one cash pool (a real ledger overspend reachable through nothing but
each route's own already-tightened box bound, never a hand-widened one), two
funding routes sharing one source, a single isolated funding route, and a
multi-broker scenario where two brokers reuse the same raw capability/
fee-schedule id string (proving the compiled lookup keys them by
`(broker_id, id)`, never by `id` alone).

Pattern used throughout: never call `model.optimize()` more than once on
the same `Model` (chaining raw `optimize()` calls after presolve has run
can hit deleted-vars/inconsistent-bound errors) -- every check below builds
a fresh `compile_policy_program(scenario, view)` first, via `_fresh_program`.
SCIP's own floating solve introduces a small numerical error (a part in
1e9-1e12 was observed while writing this suite), so stage-value comparisons
against the Decimal-exact `evaluate_exact_candidate` use `pytest.approx`;
feasibility comparisons (`model.getStatus()` vs. `evaluation.feasible`) are
exact string/bool comparisons, since SCIP's status is not a continuous
quantity.

Not covered here: `PolicyProgramContractError`. Its docstring already
states it should be unreachable for any view `evaluator.build_exact_policy_view`
actually produces, and forcing it would require hand-corrupting a
`DecisionAccess`/`ExactPolicyView` past its own `__post_init__` invariants
(the same kind of bypass the sibling suites use for their own analogous
dead branches) purely to prove a "should never happen" guard rail exists --
out of scope for this build's required coverage.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from backend.app.services.pac_allocator import numeric as NUM
from backend.app.services.pac_allocator.compiler import (
    CompiledProgram,
    PolicyProgramScopeError,
    compile_policy_program,
)
from backend.app.services.pac_allocator.constraints import (
    _MODELLED_ROUNDED_FAMILIES,
    _ROUNDED_FAMILY_DETECTORS,
    CompiledVariables,
    LedgerPostingScopeError,
    ScenarioFacts,
    _require_modelled_rounded_families,
    as_float,
    build_scenario_facts,
    buy_pool_currencies,
    fx_rate,
    order_notional,
    order_prices,
    valuation_rate,
)
from backend.app.services.pac_allocator.evaluator import (
    build_exact_policy_view,
    evaluate_exact_candidate,
    exact_decision_id,
)
from backend.app.services.pac_allocator.ledger import _ROUNDED_FAMILIES
from backend.app.services.pac_allocator.models import ExactPlannerScenario, ExactPolicyView
from backend.app.services.pac_allocator.objectives import build_canonical_tie_stages
from backend.test_scripts.test_services.test_pac_planner_evaluator import (
    CENT,
    ONE,
    ZERO,
    R,
    _asset,
    _broker,
    _candidate,
    _capability,
    _cash,
    _fee,
    _funding_route,
    _fx_rate,
    _invest_and_sell_scenario,
    _invest_only_baseline,
    _invest_only_scenario,
    _min_fragmentation_scenario,
    _objective_map,
    _order_route,
    _pac_scenario,
    _scenario,
)
from backend.test_scripts.test_services.test_pac_planner_oracle import (
    _coarse_funding_fx_scenario,
    _credit_tie_fx_scenario,
    _two_asset_pac_scenario,
)

STAGE_CODES_IN_ORDER = ("fixed_l2", "shortfall", "route_priority", "explicit_cost", "active_order_rows")

# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------


def _fresh_program(scenario: ExactPlannerScenario, view: ExactPolicyView) -> CompiledProgram:
    """A distinct compiled program per call -- never reused across multiple
    `model.optimize()` calls (see the module docstring).
    """
    return compile_policy_program(scenario, view)


def _pin(model, variable, value: int | float) -> None:
    """Pin one SCIP variable to an exact value (both bounds at once)."""
    model.chgVarLb(variable, value)
    model.chgVarUb(variable, value)


def _quanta_map(candidate) -> dict[str, int]:
    """All of one `CandidateActionVector`'s decisions as a plain dict, for
    pinning the equivalent SCIP variables to the exact same values used for
    the Decimal-exact replay.
    """
    return {decision.decision_id: decision.quanta for decision in candidate.decisions}


def _pinned_status(
    scenario: ExactPlannerScenario,
    view: ExactPolicyView,
    *,
    quanta: dict[str, int] | None = None,
    buy_active: dict[str, int] | None = None,
    funding_active: dict[str, int] | None = None,
    buy_fee: dict[str, float] | None = None,
) -> str:
    """Build a fresh compiled program, pin the given variables, and return
    `model.getStatus()` for a zero objective -- a pure feasibility probe.
    """
    program = _fresh_program(scenario, view)
    for decision_id, value in (quanta or {}).items():
        _pin(program.model, program.variables.quanta[decision_id], value)
    for route_id, value in (buy_active or {}).items():
        _pin(program.model, program.variables.buy_active[route_id], value)
    for route_id, value in (funding_active or {}).items():
        _pin(program.model, program.variables.funding_active[route_id], value)
    for route_id, value in (buy_fee or {}).items():
        _pin(program.model, program.variables.buy_fee[route_id], value)
    program.model.setObjective(0)
    program.model.optimize()
    return program.model.getStatus()


def _stage_value(scenario: ExactPlannerScenario, view: ExactPolicyView, quanta: dict[str, int], stage_code: str) -> float:
    """Build a fresh compiled program, pin every `quanta` decision to one
    fully-specified candidate, minimize exactly one named cascade stage, and
    return its optimal value. `buy_active`/`funding_active`/`buy_fee` are
    left free: the hard constraints force each to the value that `quanta`
    (already covering every decision) uniquely determines.
    """
    program = _fresh_program(scenario, view)
    for decision_id, value in quanta.items():
        _pin(program.model, program.variables.quanta[decision_id], value)
    stage = next(candidate_stage for candidate_stage in program.objective_stages if candidate_stage.code == stage_code)
    program.model.setObjective(stage.expression, sense="minimize")
    program.model.optimize()
    assert program.model.getStatus() == "optimal", f"stage {stage_code!r} did not solve to optimality"
    return program.model.getObjVal()


def _objective_value(view: ExactPolicyView, evaluation: Any, code: str) -> float:
    return as_float(_objective_map(view, evaluation)[code])


# --------------------------------------------------------------------------
# Local scenario fixtures
# --------------------------------------------------------------------------


def _multi_broker_shared_ids_scenario() -> ExactPlannerScenario:
    """Two brokers that each define a capability/fee schedule under the
    *same* raw id string (`capability:shared` / `fee:shared`), plus a third
    currency (GBP) with no direct FX pair to the route's own quote currency
    (USD). Proves `build_scenario_facts` keys its capability/fee dicts by
    `(broker_id, id)` rather than by `id` alone, and gives `buy_pool_currencies`
    a real anti-cascade candidate to exclude: GBP is real, fundable cash at
    this broker, but reaching USD from it would need two FX hops, which this
    module deliberately never attempts (one hop only).
    """
    cap_a = _capability("capability:shared", kind="whole_quantity", step=R(1))
    cap_b = _capability("capability:shared", kind="monetary_amount", step=R(1, 100))
    fee_a = _fee("fee:shared", cap_a.capability_id, "buy", currency="USD", fixed=R(1), rate=R(1, 50), floor=R(2), cap=R(9))
    fee_b = _fee("fee:shared", cap_b.capability_id, "buy", currency="USD", fixed=R(3), rate=R(1, 20), floor=R(4), cap=None)
    broker_a = _broker("broker:a", (cap_a,), (fee_a,))
    broker_b = _broker("broker:b", (cap_b,), (fee_b,))
    return _scenario(
        "scenario:multi-broker-shared-ids",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a", price=R(10), currency="USD"),),
        brokers=(broker_a, broker_b),
        existing_cash=(
            _cash("cash:eur", "broker:a", R(50), currency="EUR"),
            _cash("cash:gbp", "broker:a", R(30), currency="GBP"),
        ),
        order_routes=(
            _order_route(
                "route:buy:a",
                broker_id="broker:a",
                asset_id="asset:a",
                capability=cap_a,
                fee_id=fee_a.fee_schedule_id,
                side="buy",
                cap=R(5),
                currency="USD",
            ),
        ),
        fx_rates=(_fx_rate("EUR", "USD", R(6, 5)), _fx_rate("EUR", "GBP", R(9, 10))),
        currency_quantums=(("EUR", CENT), ("USD", CENT), ("GBP", CENT)),
    )


def _shared_cash_two_route_scenario() -> ExactPlannerScenario:
    """Two independent BUY routes on the *same* broker/currency cash pool
    (EUR100 at `broker:a`), each individually capped high enough (20 units)
    that its own box bound alone would allow spending the entire pool on
    that route alone -- `add_ledger_balance_constraints` is the only thing
    stopping both from being pinned to values that jointly overspend it.
    """
    capability = _capability("capability:a", kind="whole_quantity", step=R(1))
    fee = _fee("fee:buy:a", capability.capability_id, "buy", currency="EUR")
    broker = _broker("broker:a", (capability,), (fee,))
    return _scenario(
        "scenario:shared-cash",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a", price=R(10)), _asset("asset:b", price=R(20))),
        brokers=(broker,),
        existing_cash=(_cash("cash:a", "broker:a", R(100)),),
        order_routes=(
            _order_route("route:buy:a", broker_id="broker:a", asset_id="asset:a", capability=capability, fee_id=fee.fee_schedule_id, side="buy", cap=R(20), priority=1),
            _order_route("route:buy:b", broker_id="broker:a", asset_id="asset:b", capability=capability, fee_id=fee.fee_schedule_id, side="buy", cap=R(20), priority=2),
        ),
    )


def _shared_source_two_funding_routes_scenario() -> ExactPlannerScenario:
    """Two funding routes at two different destination brokers, both
    drawing on the *same* `existing_cash` source (USD100 at `broker:source`)
    -- `add_funding_pool_constraints` is the only thing stopping both from
    being pinned to the source's full amount at once.
    """
    capability = _capability("capability:usd", kind="whole_quantity", step=R(1))
    fee = _fee("fee:buy:usd", capability.capability_id, "buy", currency="USD")
    dest1 = _broker("broker:dest1", (capability,), (fee,))
    dest2 = _broker("broker:dest2", (capability,), (fee,))
    source = _broker("broker:source")
    return _scenario(
        "scenario:shared-source",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a", price=R(10), currency="USD"),),
        brokers=(dest1, dest2, source),
        existing_cash=(_cash("cash:source", source.broker_id, R(100), currency="USD"),),
        funding_routes=(
            _funding_route("route:funding:1", broker_id=dest1.broker_id, source_kind="existing_cash", source_id="cash:source", amount=R(100), currency="USD", priority=1),
            _funding_route("route:funding:2", broker_id=dest2.broker_id, source_kind="existing_cash", source_id="cash:source", amount=R(100), currency="USD", priority=2),
        ),
        order_routes=(_order_route("route:buy:a", broker_id=dest1.broker_id, asset_id="asset:a", capability=capability, fee_id=fee.fee_schedule_id, side="buy", cap=R(1), currency="USD", priority=5),),
        fx_rates=(_fx_rate("EUR", "USD", R(11, 10)),),
        currency_quantums=(("EUR", CENT), ("USD", ONE)),
    )


def _single_funding_route_scenario() -> ExactPlannerScenario:
    """One isolated funding route, so `add_funding_activation_constraints`
    can be pinned down without any other constraint family in play.
    """
    capability = _capability("capability:a", kind="whole_quantity", step=R(1))
    fee = _fee("fee:buy:a", capability.capability_id, "buy")
    dest = _broker("broker:dest", (capability,), (fee,))
    source = _broker("broker:source")
    return _scenario(
        "scenario:single-funding",
        product="pac",
        policy="proportional",
        assets=(_asset("asset:a", price=R(10)),),
        brokers=(dest, source),
        existing_cash=(_cash("cash:source", source.broker_id, R(50)),),
        funding_routes=(_funding_route("route:funding:a", broker_id=dest.broker_id, source_kind="existing_cash", source_id="cash:source", amount=R(50), priority=1),),
        order_routes=(_order_route("route:buy:a", broker_id=dest.broker_id, asset_id="asset:a", capability=capability, fee_id=fee.fee_schedule_id, side="buy", cap=R(1), priority=5),),
    )


def _sub_quantum_fx_credit_scenario() -> ExactPlannerScenario:
    """`_coarse_funding_fx_scenario` (sibling oracle suite) re-rated so one
    euro converts into less than one whole-USD quantum: EUR/USD 2/5 with no
    spread. 1 EUR is an exact 0.4 USD credit and 2 EUR an exact 0.8 USD, both
    of which floor to 0 USD; 3 EUR (an exact 1.2 USD) is the first conversion
    whose floor reaches 1 USD. EUR is both the valuation and the source
    currency, so the planning rate is the approved rate itself.
    """
    return replace(_coarse_funding_fx_scenario(), fx_rates=(_fx_rate("EUR", "USD", R(2, 5)),), fx_spread_rate=ZERO)


# --------------------------------------------------------------------------
# Item 1 + 2: `build_scenario_facts` and the pure lookup helpers
# --------------------------------------------------------------------------


def test_build_scenario_facts_multi_broker_multi_currency() -> None:
    scenario = _multi_broker_shared_ids_scenario()
    facts = build_scenario_facts(scenario)

    assert facts.valuation_currency == "EUR"
    assert facts.currency_quantum == {"EUR": 0.01, "USD": 0.01, "GBP": 0.01}
    assert facts.fx_rate_by_pair == {"EUR/USD": 1.2, "EUR/GBP": 0.9}
    assert facts.assets_by_id == {"asset:a": "USD"}
    assert facts.mid_native_by_asset == {"asset:a": 10.0}

    # Same raw id string, two different brokers: the composite key must not collide.
    assert set(facts.capability_by_key) == {("broker:a", "capability:shared"), ("broker:b", "capability:shared")}
    assert facts.capability_by_key[("broker:a", "capability:shared")].kind == "whole_quantity"
    assert facts.capability_by_key[("broker:b", "capability:shared")].kind == "monetary_amount"
    assert set(facts.fee_by_key) == {("broker:a", "fee:shared"), ("broker:b", "fee:shared")}
    assert facts.fee_by_key[("broker:a", "fee:shared")].fixed_fee.amount == R(1)
    assert facts.fee_by_key[("broker:b", "fee:shared")].fixed_fee.amount == R(3)


def test_fx_rate_direct_and_inverse_pair_direction() -> None:
    scenario = _multi_broker_shared_ids_scenario()
    facts = build_scenario_facts(scenario)
    assert fx_rate(facts, "EUR", "USD") == pytest.approx(1.2)
    assert fx_rate(facts, "USD", "EUR") == pytest.approx(1.0 / 1.2)
    assert fx_rate(facts, "USD", "USD") == 1.0  # identity, no lookup needed


def test_valuation_rate_uses_scenario_valuation_currency() -> None:
    scenario = _multi_broker_shared_ids_scenario()
    facts = build_scenario_facts(scenario)
    assert facts.valuation_currency == "EUR"
    assert valuation_rate(facts, "EUR") == 1.0
    assert valuation_rate(facts, "USD") == pytest.approx(1.0 / 1.2)


def test_order_prices_applies_execution_margin_for_buy() -> None:
    scenario = _pac_scenario(price=R(10), margin=R(1, 20))  # 5% margin
    facts = build_scenario_facts(scenario)
    route = scenario.order_routes[0]
    mid_native, execution_native = order_prices(facts, route)
    assert mid_native == pytest.approx(10.0)
    assert execution_native == pytest.approx(10.5)  # buy side: mid * (1 + margin)


def test_order_notional_whole_quantity_uses_execution_price() -> None:
    scenario = _pac_scenario(price=R(10), margin=R(1, 20))
    facts = build_scenario_facts(scenario)
    route = scenario.order_routes[0]
    capability = facts.capability_by_key[(route.broker_id, route.capability_id)]
    assert capability.kind == "whole_quantity"
    assert order_notional(facts, route, capability, 3.0) == pytest.approx(3.0 * 10.5)


def test_order_notional_monetary_amount_returns_measure_unchanged() -> None:
    scenario = _multi_broker_shared_ids_scenario()
    facts = build_scenario_facts(scenario)
    monetary_capability = facts.capability_by_key[("broker:b", "capability:shared")]
    assert monetary_capability.kind == "monetary_amount"
    # `route` is only consulted by the whole_quantity branch (for its own
    # asset/side); the monetary_amount branch returns `measure` untouched,
    # so any route from the scenario is a legitimate probe here.
    route = scenario.order_routes[0]
    assert order_notional(facts, route, monetary_capability, 42.0) == 42.0


def test_buy_pool_currencies_excludes_quote_and_no_direct_pair_currency() -> None:
    scenario = _multi_broker_shared_ids_scenario()
    facts = build_scenario_facts(scenario)
    pools = buy_pool_currencies(scenario, facts, broker_id="broker:a", quote_currency="USD")
    # EUR: real cash at broker:a with a direct EUR/USD pair -> included.
    # GBP: also real cash at broker:a, but only a direct EUR/GBP pair exists
    #      (no direct GBP/USD pair) -> excluded, one hop only (anti-cascade).
    # USD: the route's own quote currency -> excluded.
    assert pools == ("EUR",)


def test_as_float_projects_exact_ratio() -> None:
    assert as_float(R(6, 5)) == pytest.approx(1.2)
    assert as_float(ZERO) == 0.0
    assert as_float(ONE) == 1.0


# --------------------------------------------------------------------------
# Item 3 (+ Item 8 for the ledger case): hard-constraint feasibility boundaries
# --------------------------------------------------------------------------


def test_funding_pool_constraint_boundary() -> None:
    """`FUNDING_WITHIN_SELECTED`: two funding routes at two different
    destination brokers share one `existing_cash` source; each route's own
    box bound alone allows the full 100, but the pool constraint caps their
    *sum*.
    """
    scenario = _shared_source_two_funding_routes_scenario()
    view = build_exact_policy_view(scenario)
    route_1 = exact_decision_id("funding_transfer", "route:funding:1")
    route_2 = exact_decision_id("funding_transfer", "route:funding:2")

    assert _pinned_status(scenario, view, quanta={route_1: 60, route_2: 40}) == "optimal"  # sum == 100, boundary
    assert _pinned_status(scenario, view, quanta={route_1: 60, route_2: 41}) == "infeasible"  # sum == 101


def test_ledger_balance_constraint_boundary_matches_evaluator() -> None:
    """`NO_SHORT_OR_LEVERAGE`: two BUY routes on the same broker/currency
    cash pool, each individually capped well above what the shared EUR100
    pool can support -- also this suite's Item 8 evaluator-agreement case:
    both the SCIP status and `evaluate_exact_candidate`'s own feasibility
    must agree, on the feasible boundary and on the infeasible candidate one
    unit past it.
    """
    scenario = _shared_cash_two_route_scenario()
    view = build_exact_policy_view(scenario)
    decision_a = exact_decision_id("buy_quantum", "route:buy:a")
    decision_b = exact_decision_id("buy_quantum", "route:buy:b")

    # Each route's own box bound individually allows the whole pool (10 @ EUR10, 5 @ EUR20).
    access_a = next(d for d in view.decisions if d.decision_id == decision_a)
    access_b = next(d for d in view.decisions if d.decision_id == decision_b)
    assert access_a.upper_quanta == 10
    assert access_b.upper_quanta == 5

    # Boundary: 8*EUR10 + 1*EUR20 = EUR100 == the whole pool.
    feasible_candidate = _candidate(view, {decision_a: 8, decision_b: 1}, candidate_id="candidate:boundary")
    feasible_evaluation = evaluate_exact_candidate(scenario, view, feasible_candidate)
    assert feasible_evaluation.feasible is True
    assert _pinned_status(scenario, view, quanta=_quanta_map(feasible_candidate)) == "optimal"

    # One unit past it: 8*EUR10 + 2*EUR20 = EUR120 > the pool -- a genuine
    # shared-pool overspend, not merely an out-of-box-bounds pin (both
    # individual pins, 8 <= 10 and 2 <= 5, are within each route's own box bound).
    infeasible_candidate = _candidate(view, {decision_a: 8, decision_b: 2}, candidate_id="candidate:overspend")
    infeasible_evaluation = evaluate_exact_candidate(scenario, view, infeasible_candidate)
    assert infeasible_evaluation.feasible is False
    assert "NO_SHORT_OR_LEVERAGE" in infeasible_evaluation.conflict_codes
    assert _pinned_status(scenario, view, quanta=_quanta_map(infeasible_candidate)) == "infeasible"


def test_order_required_minimum_constraint_boundary() -> None:
    """`ORDER_REQUIRED_MIN`: an unconditional floor -- below it is
    infeasible, exactly at it is feasible, and (unlike `ORDER_MIN_IF_ACTIVE`)
    zero is *also* infeasible, since this floor is never gated by "active".
    """
    scenario = _pac_scenario(required=R(5), route_cap=R(10))
    view = build_exact_policy_view(scenario)
    decision_id = exact_decision_id("buy_quantum", "route:buy:a")

    assert _pinned_status(scenario, view, quanta={decision_id: 4}) == "infeasible"
    assert _pinned_status(scenario, view, quanta={decision_id: 5}) == "optimal"  # boundary
    assert _pinned_status(scenario, view, quanta={decision_id: 0}) == "infeasible"  # unconditional, not "if active"


def test_order_activation_constraint_boundary_both_disjunction_directions() -> None:
    """`ORDER_MIN_IF_ACTIVE`: the measure is either exactly zero or at least
    the active floor. A value strictly between the two is infeasible no
    matter which way `buy_active` is pinned (or left free) -- both
    directions of the disjunction fail at once.
    """
    scenario = _pac_scenario(minimum=R(3), route_cap=R(10))
    view = build_exact_policy_view(scenario)
    decision_id = exact_decision_id("buy_quantum", "route:buy:a")

    assert _pinned_status(scenario, view, quanta={decision_id: 0}) == "optimal"  # active free, solver picks 0
    assert _pinned_status(scenario, view, quanta={decision_id: 3}) == "optimal"  # boundary, active free, solver picks 1
    assert _pinned_status(scenario, view, quanta={decision_id: 2}) == "infeasible"  # strictly between, active free
    assert _pinned_status(scenario, view, quanta={decision_id: 2}, buy_active={"route:buy:a": 0}) == "infeasible"  # order_active_upper violated
    assert _pinned_status(scenario, view, quanta={decision_id: 2}, buy_active={"route:buy:a": 1}) == "infeasible"  # order_active_floor violated


def test_funding_activation_constraint_boundary() -> None:
    """Links `funding_active` to its transfer decision the same way: a
    nonzero transfer forced inactive is infeasible; the same transfer with
    `funding_active` pinned to 1 (or left free, since nothing else prefers
    0 over 1 here) is feasible.
    """
    scenario = _single_funding_route_scenario()
    view = build_exact_policy_view(scenario)
    decision_id = exact_decision_id("funding_transfer", "route:funding:a")

    assert _pinned_status(scenario, view, quanta={decision_id: 0}, funding_active={"route:funding:a": 0}) == "optimal"
    assert _pinned_status(scenario, view, quanta={decision_id: 5}, funding_active={"route:funding:a": 0}) == "infeasible"
    assert _pinned_status(scenario, view, quanta={decision_id: 5}, funding_active={"route:funding:a": 1}) == "optimal"
    assert _pinned_status(scenario, view, quanta={decision_id: 5}) == "optimal"  # active left free, solver picks 1


def test_fee_epigraph_floor_and_linear_boundary() -> None:
    """The floor/linear part of the fee epigraph (no cap in play here -- the
    cap has its own tests below, `test_fee_epigraph_cap_boundary` and
    `test_fee_epigraph_cap_exact`): at a quantity where the floor binds, the
    fee variable cannot go below the floor; at a quantity where the linear
    term exceeds the floor, it cannot go below the linear value either. Both
    boundaries also match the Decimal-exact replay.
    """
    scenario = _pac_scenario(price=R(10), fee_rate=R(1, 10), fee_floor=R(5), fee_cap=None, route_cap=R(10), cash=R(1000))
    view = build_exact_policy_view(scenario)
    decision_id = exact_decision_id("buy_quantum", "route:buy:a")
    route_id = "route:buy:a"

    # q=1: notional=EUR10, rate*notional=EUR1 < floor(EUR5) -> the floor binds.
    assert _pinned_status(scenario, view, quanta={decision_id: 1}, buy_fee={route_id: 5.0}) == "optimal"
    assert _pinned_status(scenario, view, quanta={decision_id: 1}, buy_fee={route_id: 4.99}) == "infeasible"

    # q=6: notional=EUR60, rate*notional=EUR6 > floor(EUR5) -> the linear term binds.
    assert _pinned_status(scenario, view, quanta={decision_id: 6}, buy_fee={route_id: 6.0}) == "optimal"
    assert _pinned_status(scenario, view, quanta={decision_id: 6}, buy_fee={route_id: 5.99}) == "infeasible"

    # q=0 (inactive): the fee must be exactly zero.
    assert _pinned_status(scenario, view, quanta={decision_id: 0}, buy_fee={route_id: 0.0}) == "optimal"
    assert _pinned_status(scenario, view, quanta={decision_id: 0}, buy_fee={route_id: 0.01}) == "infeasible"

    # Cross-check against the Decimal-exact replay: floor and linear both
    # match `evaluate_exact_candidate`'s own `exact_fee` (no cap in this scenario).
    for quanta, expected_fee in ((1, 5), (6, 6)):
        candidate = _candidate(view, {decision_id: quanta}, candidate_id=f"candidate:fee-linear-{quanta}")
        evaluation = evaluate_exact_candidate(scenario, view, candidate)
        order_evaluation = next(o for o in evaluation.orders if o.route_id == route_id)
        assert order_evaluation.exact_fee == R(expected_fee)


@pytest.mark.parametrize(
    ("fixed_fee", "fee_rate", "fee_floor"),
    [
        pytest.param(ZERO, R(19, 10000), R(3, 2), id="rate-0.19pct-min-1.50"),
        pytest.param(ZERO, ZERO, R(2), id="flat-min-2"),
        pytest.param(ONE, R(19, 10000), R(3, 2), id="fixed-1-rate-0.19pct-min-1.50"),
    ],
)
def test_fee_epigraph_floor_above_linear_upper_boundary(fixed_fee, fee_rate, fee_floor) -> None:
    """X2 regression (found 2026-09-24): a fee minimum above the linear fee at
    the route's own notional upper bound, `floor > rate * notional_upper`.
    The epigraph took its upper bound and its Big-M from `rate *
    notional_upper` alone, so the floor row could not be switched off: with
    the order OFF it demanded `fee >= floor - rate * notional_upper > 0`
    against `fee <= 0`, with it ON `fee >= fixed + floor` above the upper
    bound -- the whole model was infeasible whatever the order did. And
    `_fee_variable_upper` hands the same bound to the posted-fee units, so a
    fee of `fixed + floor` could not be posted either: the order-off check
    catches the epigraph, the q=9 check needs both sites.

    EUR100 of cash at EUR10 a unit is the X2 probe: 10 units at most, 9 once
    the minimum is paid. Shapes: the probe's 0.19% with a EUR1.50 minimum; a
    flat EUR2 minimum on a zero rate, where any minimum at all sits above the
    linear part; and the probe plus a EUR1 fixed fee, so the Big-M must still
    carry `fixed`. Every boundary is cross-checked against the exact replay.
    """
    scenario = _pac_scenario(price=R(10), cash=R(100), fixed_fee=fixed_fee, fee_rate=fee_rate, fee_floor=fee_floor, fee_cap=None, route_cap=R(100))
    view = build_exact_policy_view(scenario)
    route_id = "route:buy:a"
    decision_id = exact_decision_id("buy_quantum", route_id)
    minimum_fee = fixed_fee + fee_floor  # the fee of every order this route can place

    # Precondition, verified rather than assumed: at the route's own upper
    # bound (10 units, EUR100) the linear fee is still below the minimum.
    access = next(d for d in view.decisions if d.decision_id == decision_id)
    assert access.upper_quanta == 10
    assert fee_rate * R(10) * access.upper_quanta < fee_floor

    # Order off: the fee sits at zero. The core of X2 -- this was infeasible.
    assert _pinned_status(scenario, view, quanta={decision_id: 0}, buy_fee={route_id: 0.0}) == "optimal"

    # q=9 (EUR90): the minimum binds; the fee reaches `fixed + floor` ...
    assert _pinned_status(scenario, view, quanta={decision_id: 9}, buy_fee={route_id: as_float(minimum_fee)}) == "optimal"
    # ... and not one cent less: the floor still binds.
    assert _pinned_status(scenario, view, quanta={decision_id: 9}, buy_fee={route_id: as_float(minimum_fee - CENT)}) == "infeasible"
    # q=10 spends the whole EUR100 on the notional, leaving nothing for the minimum.
    assert _pinned_status(scenario, view, quanta={decision_id: 10}) == "infeasible"

    # Decimal-exact replay: 9 units are feasible at exactly the minimum fee, 10 are not.
    candidate = _candidate(view, {decision_id: 9}, candidate_id="candidate:fee-floor-above-linear-upper")
    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    assert evaluation.feasible is True
    order_evaluation = next(o for o in evaluation.orders if o.route_id == route_id)
    assert order_evaluation.exact_fee == minimum_fee

    over_budget = _candidate(view, {decision_id: 10}, candidate_id="candidate:fee-floor-over-budget")
    over_budget_evaluation = evaluate_exact_candidate(scenario, view, over_budget)
    assert over_budget_evaluation.feasible is False
    assert "NO_SHORT_OR_LEVERAGE" in over_budget_evaluation.conflict_codes


@pytest.mark.parametrize(
    ("fixed_fee", "fee_rate", "fee_floor", "fee_cap"),
    [
        pytest.param(ZERO, R(1, 10), ZERO, R(3, 2), id="rate-10pct-cap-1.50"),
        pytest.param(ZERO, R(1, 10), R(6, 5), R(3, 2), id="floor-1.20-rate-10pct-cap-1.50"),
        pytest.param(R(1, 2), R(1, 10), ZERO, R(3, 2), id="fixed-0.50-rate-10pct-cap-1.50"),
    ],
)
def test_fee_epigraph_cap_boundary(fixed_fee, fee_rate, fee_floor, fee_cap) -> None:
    """QX1-a regression (found 2026-09-24): a fee cap that binds inside the
    route's own range, `rate * notional_upper > cap`. The epigraph ignored
    `maximum_fee`: its linear row `fee >= fixed + rate * notional - big_m *
    (1 - active)` was always on, so past the cap it demanded more than
    `calculate_fee` charges -- at 9 units `fixed + EUR9` instead of `fixed +
    cap`. The posted fee is debited in the ledger, so the model also excluded
    plans the replay accepts. Since QX1-a the cap is modelled exactly (a
    binary per capped route, linear branch or flat cap branch): the minimal
    fee the model admits is `calculate_fee` at every notional, minimum and
    cap included.

    EUR100 of cash at EUR10 a unit, 10% (EUR1 of linear fee a unit) capped at
    EUR1.50. Shapes: the cap alone; a EUR1.20 minimum under it, so the floor
    binds at 1 unit and the cap from 2; and a EUR0.50 fixed fee, so the Big-M
    of the cap branch must still carry `fixed`. The exact replay is checked
    first, as ground truth; then each boundary is pinned both ways (the fee
    reaches `calculate_fee`, and not one cent less). The red core is the q=9
    pin at `fixed + cap`: infeasible while the cap was ignored.
    """
    scenario = _pac_scenario(price=R(10), cash=R(100), fixed_fee=fixed_fee, fee_rate=fee_rate, fee_floor=fee_floor, fee_cap=fee_cap, route_cap=R(100))
    view = build_exact_policy_view(scenario)
    route_id = "route:buy:a"
    decision_id = exact_decision_id("buy_quantum", route_id)
    # `calculate_fee` by hand, in exact ratios, for a nonzero order: `fixed + clamp(rate * notional, floor, cap)`.
    expected_fee = {quanta: fixed_fee + min(max(fee_rate * R(10) * quanta, fee_floor), fee_cap) for quanta in (1, 9)}

    # Preconditions, verified rather than assumed: at the route's own upper
    # bound (10 units, EUR100) the linear fee is above the cap, so the cap can
    # bind in this route; at 1 unit the fee is below `fixed + cap`, at 9 it is
    # exactly `fixed + cap`.
    access = next(d for d in view.decisions if d.decision_id == decision_id)
    assert access.upper_quanta == 10
    assert fee_rate * R(10) * access.upper_quanta > fee_cap
    assert expected_fee[1] < fixed_fee + fee_cap
    assert expected_fee[9] == fixed_fee + fee_cap

    # Ground truth first: the exact replay charges `expected_fee` on both orders, and both fit the EUR100.
    for quanta, fee in expected_fee.items():
        candidate = _candidate(view, {decision_id: quanta}, candidate_id=f"candidate:fee-cap-boundary-{quanta}")
        evaluation = evaluate_exact_candidate(scenario, view, candidate)
        assert evaluation.feasible is True
        order_evaluation = next(o for o in evaluation.orders if o.route_id == route_id)
        assert order_evaluation.exact_fee == fee

    # Order off: the fee sits at zero -- whatever the cap adds switches off with the order.
    assert _pinned_status(scenario, view, quanta={decision_id: 0}, buy_fee={route_id: 0.0}) == "optimal"

    # q=1 (EUR10): below the cap; the fee reaches `calculate_fee` and not one cent less.
    assert _pinned_status(scenario, view, quanta={decision_id: 1}, buy_fee={route_id: as_float(expected_fee[1])}) == "optimal"
    assert _pinned_status(scenario, view, quanta={decision_id: 1}, buy_fee={route_id: as_float(expected_fee[1] - CENT)}) == "infeasible"

    # q=9 (EUR90): the cap binds; the fee reaches `fixed + cap`. The core of
    # QX1-a -- this was infeasible, the linear row demanded `fixed + EUR9`.
    assert _pinned_status(scenario, view, quanta={decision_id: 9}, buy_fee={route_id: as_float(expected_fee[9])}) == "optimal"
    # ... and not one cent less: the cap branch is still a floor at `fixed + cap`.
    assert _pinned_status(scenario, view, quanta={decision_id: 9}, buy_fee={route_id: as_float(expected_fee[9] - CENT)}) == "infeasible"


def test_fee_epigraph_cap_exact() -> None:
    """QX1-a regression (found 2026-09-24): the fee epigraph used to ignore
    the cap (`maximum_fee`). With one order of EUR100 at 10% capped at EUR2,
    minimizing that route's fee alone, SCIP said EUR10 -- the linear fee --
    while the Decimal-exact replay charges EUR2. Now the cap is modelled
    exactly: SCIP's minimal fee is the replay's own capped EUR2.
    """
    scenario = _pac_scenario(price=R(10), cash=R(1000), fee_rate=R(1, 10), fee_cap=R(2), route_cap=R(10))
    view = build_exact_policy_view(scenario)
    route_id = "route:buy:a"
    decision_id = exact_decision_id("buy_quantum", route_id)

    program = _fresh_program(scenario, view)
    decision_var = program.variables.quanta[decision_id]
    fee_var = program.variables.buy_fee[route_id]
    _pin(program.model, decision_var, 10)  # notional = 10 * EUR10 = EUR100
    program.model.setObjective(fee_var, sense="minimize")
    program.model.optimize()
    assert program.model.getStatus() == "optimal"

    # Capped: rate * notional = 0.1 * 100 = EUR10 clamps to the EUR2 cap (SCIP said EUR10 before QX1-a).
    assert program.model.getVal(fee_var) == pytest.approx(2.0)

    # The Decimal-exact replay is the source of truth, and it charges the same capped EUR2.
    candidate = _candidate(view, {decision_id: 10}, candidate_id="candidate:fee-cap")
    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    assert evaluation.feasible is True
    order_evaluation = next(o for o in evaluation.orders if o.route_id == route_id)
    assert order_evaluation.exact_fee == R(2)


# --------------------------------------------------------------------------
# Item 4: every objective stage's SCIP value vs. the Decimal-exact replay
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({}, id="all-zero"),
        pytest.param({"a": 2, "b": 1}, id="mid"),
        pytest.param({"a": 3, "b": 3}, id="all-max"),
    ],
)
def test_objective_stage_values_match_evaluator_two_asset(overrides: dict[str, int]) -> None:
    scenario = _two_asset_pac_scenario()
    view = build_exact_policy_view(scenario)
    decision_a = exact_decision_id("buy_quantum", "route:buy:a")
    decision_b = exact_decision_id("buy_quantum", "route:buy:b")

    candidate = _candidate(view, {decision_a: overrides.get("a", 0), decision_b: overrides.get("b", 0)}, candidate_id="candidate:stage-check")
    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    assert evaluation.feasible is True  # every hand-picked candidate here is within bounds

    resolved_quanta = _quanta_map(candidate)
    for code in STAGE_CODES_IN_ORDER:
        scip_value = _stage_value(scenario, view, resolved_quanta, code)
        expected_value = _objective_value(view, evaluation, code)
        assert scip_value == pytest.approx(expected_value, abs=1e-6), f"stage {code!r}: scip={scip_value} evaluator={expected_value}"


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param({}, id="all-zero"),
        pytest.param({"funding": 10, "fx": 8, "buy": 1}, id="mid"),
        pytest.param({"funding": 12, "fx": 10, "buy": 2}, id="near-max"),
    ],
)
def test_objective_stage_values_match_evaluator_coarse_funding_fx(overrides: dict[str, int]) -> None:
    scenario = _coarse_funding_fx_scenario()
    view = build_exact_policy_view(scenario)
    funding_decision = exact_decision_id("funding_transfer", "route:funding:eur")
    fx_decision = exact_decision_id("fx_debit", "route:buy:usd:EUR")
    buy_decision = exact_decision_id("buy_quantum", "route:buy:usd")

    candidate = _candidate(
        view,
        {
            funding_decision: overrides.get("funding", 0),
            fx_decision: overrides.get("fx", 0),
            buy_decision: overrides.get("buy", 0),
        },
        candidate_id="candidate:stage-check",
    )
    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    assert evaluation.feasible is True

    resolved_quanta = _quanta_map(candidate)
    for code in STAGE_CODES_IN_ORDER:
        scip_value = _stage_value(scenario, view, resolved_quanta, code)
        expected_value = _objective_value(view, evaluation, code)
        assert scip_value == pytest.approx(expected_value, abs=1e-6), f"stage {code!r}: scip={scip_value} evaluator={expected_value}"


# --------------------------------------------------------------------------
# Item 5: `build_objective_cascade` / `build_canonical_tie_stages` order
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build_scenario",
    [pytest.param(_two_asset_pac_scenario, id="two-asset"), pytest.param(_coarse_funding_fx_scenario, id="coarse-funding-fx")],
)
def test_objective_cascade_stage_order(build_scenario) -> None:
    scenario = build_scenario()
    view = build_exact_policy_view(scenario)
    program = _fresh_program(scenario, view)

    assert len(view.tie_breaks) == 1
    codes = [stage.code for stage in program.objective_stages]
    expected = list(STAGE_CODES_IN_ORDER) + [f"tie:{decision_id}" for decision_id in view.tie_breaks[0].decision_ids]
    assert codes == expected

    # `build_canonical_tie_stages` also stands on its own, not only through
    # the orchestrator: each tie stage's expression is literally the same
    # `Variable` object as `variables.quanta[decision_id]`.
    tie_stages = build_canonical_tie_stages(program.variables, view)
    assert [stage.code for stage in tie_stages] == [f"tie:{decision_id}" for decision_id in view.tie_breaks[0].decision_ids]
    for stage, decision_id in zip(tie_stages, view.tie_breaks[0].decision_ids, strict=True):
        assert stage.expression is program.variables.quanta[decision_id]


# --------------------------------------------------------------------------
# Item 6: `compile_policy_program`'s scope guard
# --------------------------------------------------------------------------


def test_scope_error_for_non_primary_purpose() -> None:
    """A `pac`/`proportional` scenario is otherwise perfectly in-scope, but
    a `deployment`-purpose view isn't -- isolates the *second* `if` in
    `_require_supported_scope` from the product/policy check (which this
    scenario passes).
    """
    scenario = _pac_scenario()
    primary_view = build_exact_policy_view(scenario)
    baseline_candidate = _candidate(primary_view, {}, candidate_id="baseline:zero")
    deployment_view = build_exact_policy_view(scenario, purpose="deployment", baseline=baseline_candidate, view_id="view:deployment-probe")

    assert deployment_view.product == "pac"
    assert deployment_view.policy == "proportional"
    assert deployment_view.purpose == "deployment"
    with pytest.raises(PolicyProgramScopeError, match="primary purpose"):
        compile_policy_program(scenario, deployment_view)


def test_scope_error_for_non_proportional_policy() -> None:
    scenario = _min_fragmentation_scenario()
    view = build_exact_policy_view(scenario)
    assert scenario.product == "pac"
    assert scenario.policy == "min_fragmentation"
    with pytest.raises(PolicyProgramScopeError, match="PAC proportional"):
        compile_policy_program(scenario, view)


def test_scope_error_for_non_pac_product() -> None:
    scenario = _invest_only_scenario()
    view = build_exact_policy_view(scenario)
    assert scenario.product == "rebalancer"
    with pytest.raises(PolicyProgramScopeError, match="PAC proportional"):
        compile_policy_program(scenario, view)


def test_scope_error_for_non_pac_product_and_non_primary_purpose() -> None:
    """`invest_and_sell` + `invest_only_baseline` fails *both* checks at
    once; the product/policy check runs first, so that message is the one
    that surfaces.
    """
    scenario = _invest_and_sell_scenario()
    view, _baseline = _invest_only_baseline(scenario)
    assert scenario.product == "rebalancer"
    assert view.purpose != "primary"
    with pytest.raises(PolicyProgramScopeError, match="PAC proportional"):
        compile_policy_program(scenario, view)


# --------------------------------------------------------------------------
# Item 7: `CompiledVariables` / box-bound correctness
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "build_scenario",
    [pytest.param(_two_asset_pac_scenario, id="two-asset"), pytest.param(_coarse_funding_fx_scenario, id="coarse-funding-fx")],
)
def test_compiled_variables_match_view_and_routes(build_scenario) -> None:
    scenario = build_scenario()
    view = build_exact_policy_view(scenario)
    program = _fresh_program(scenario, view)

    assert isinstance(program.variables, CompiledVariables)
    assert isinstance(program.facts, ScenarioFacts)

    assert set(program.variables.quanta) == {access.decision_id for access in view.decisions}
    for access in view.decisions:
        variable = program.variables.quanta[access.decision_id]
        assert variable.getLbOriginal() == access.lower_quanta
        assert variable.getUbOriginal() == access.upper_quanta

    buy_route_ids = {route.route_id for route in scenario.order_routes if route.side == "buy"}
    funding_route_ids = {route.route_id for route in scenario.funding_routes}
    assert set(program.variables.buy_active) == buy_route_ids
    assert set(program.variables.buy_fee) == buy_route_ids
    assert set(program.variables.funding_active) == funding_route_ids


# --------------------------------------------------------------------------
# Item A1: a fractional FX credit is posted AGAINST THE PLAN -- it floors at
# its currency quantum (README row 16). SCIP and the Decimal-exact replay sum
# the same POSTED amounts (Step3 §16.11) and must AGREE on feasibility, on the
# point the floor can no longer finance and on the one it still can.
# --------------------------------------------------------------------------


def test_fractional_fx_credit_floors_and_the_buy_it_cannot_cover_is_infeasible() -> None:
    """A genuinely *fractional* FX credit. In `_coarse_funding_fx_scenario`
    the effective rate is `6/5 * (1 - 1/100) = 297/250 = 1.188`, so
    converting 8 EUR (fx quanta 8) yields an exact credit of
    `8 * 297/250 = 1188/125 = 9.504` USD -- not a whole-USD multiple. A
    credit is rounded against the plan: it posts `floor(9.504) = 9` USD, a
    rounding delta of `-63/125` that the accounting charges to the plan as a
    `+63/125` adjustment -- never the 10 USD a round-half-up gives. A 2-unit
    BUY at 5 USD debits exactly 10 USD, so the destination USD cell closes at
    `9 - 10 = -1`: the point is infeasible.

    Under HALF_UP the credit posted 10 USD and this very point was the coarse
    fixture's optimum, financed by 0.496 USD the conversion never delivers.
    Both sides must now reject it: the Decimal-exact replay AND the pinned
    SCIP model, whose ledger rows sum the same posted amounts (Step3 §16.11:
    never the exact ones).
    """
    scenario = _coarse_funding_fx_scenario()
    view = build_exact_policy_view(scenario)
    funding = exact_decision_id("funding_transfer", "route:funding:eur")
    fx = exact_decision_id("fx_debit", "route:buy:usd:EUR")
    buy = exact_decision_id("buy_quantum", "route:buy:usd")
    quanta = {funding: 8, fx: 8, buy: 2}

    candidate = _candidate(view, quanta, candidate_id="candidate:fx-credit-floor")
    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    assert evaluation.candidate_valid is True  # inside every box: only the cash rules can decide

    # The fractional FX credit: exact 9.504, posted at its floor, 9.
    fx_evaluation = next(item for item in evaluation.fx if item.order_route_id == "route:buy:usd" and item.source_currency == "EUR")
    assert fx_evaluation.exact_destination_credit == R(1188, 125)  # 9.504, NOT a quantum multiple
    assert fx_evaluation.posted_destination_credit == R(9)
    fx_posting = next(posting for posting in evaluation.postings if posting.family == "fx_credit" and posting.broker_id == "broker:destination" and posting.currency == "USD")
    assert fx_posting.rounding_delta == R(-63, 125)  # posted - exact, signed: a credit only ever rounds down
    assert fx_posting.accounting_rounding_adjustment == R(63, 125)  # debit-positive: a cost to the plan

    order_evaluation = next(item for item in evaluation.orders if item.route_id == "route:buy:usd")
    assert order_evaluation.posted_cash_amount == R(10)  # the 2-unit BUY posts a 10 USD debit

    usd_cell = next(ledger for ledger in evaluation.ledgers if ledger.broker_id == "broker:destination" and ledger.currency == "USD")
    assert (usd_cell.fx_credit, usd_cell.buy_debit) == (R(9), R(10))  # POSTED amounts on both sides
    assert usd_cell.final_spendable == R(-1)

    assert evaluation.feasible is False
    assert {"NO_SHORT_OR_LEVERAGE", "SPENDABLE_CASH_NONNEGATIVE"} <= set(evaluation.conflict_codes)
    assert _pinned_status(scenario, view, quanta=quanta) == "infeasible"


def test_fractional_fx_credit_whose_floor_covers_the_buy_stays_feasible() -> None:
    """Green control for the test above, one euro further: 9 EUR convert
    into an exact `9 * 297/250 = 2673/250 = 10.692` USD. Its floor, 10 USD,
    still covers the same 10 USD debit -- as every rounding of 10.692 at the
    whole-USD quantum does -- so the point is feasible in the exact replay
    and in the pinned SCIP model alike, whether the credit posts 10 against
    the plan or 11 under HALF_UP. Funding 9 EUR fits the fixture's 12 EUR
    funding cap and source cash, and the destination EUR cell closes at
    `9 - 9 = 0`.
    """
    scenario = _coarse_funding_fx_scenario()
    view = build_exact_policy_view(scenario)
    funding = exact_decision_id("funding_transfer", "route:funding:eur")
    fx = exact_decision_id("fx_debit", "route:buy:usd:EUR")
    buy = exact_decision_id("buy_quantum", "route:buy:usd")
    quanta = {funding: 9, fx: 9, buy: 2}

    candidate = _candidate(view, quanta, candidate_id="candidate:fx-credit-floor-covers")
    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    assert evaluation.candidate_valid is True

    fx_evaluation = next(item for item in evaluation.fx if item.order_route_id == "route:buy:usd" and item.source_currency == "EUR")
    assert fx_evaluation.exact_destination_credit == R(2673, 250)  # 10.692, NOT a quantum multiple
    assert fx_evaluation.posted_destination_credit >= R(10)  # at least its floor, whatever the rounding

    usd_cell = next(ledger for ledger in evaluation.ledgers if ledger.broker_id == "broker:destination" and ledger.currency == "USD")
    assert usd_cell.buy_debit == R(10)
    assert usd_cell.fx_credit >= usd_cell.buy_debit
    assert usd_cell.final_spendable >= ZERO

    assert evaluation.feasible is True
    assert _pinned_status(scenario, view, quanta=quanta) == "optimal"


# --------------------------------------------------------------------------
# Item A2: an exact FX-credit tie posts its FLOOR, and the BUY may spend that
# floor and not one quantum more -- SCIP and the Decimal-exact replay agree on
# both sides of it, with no guard in between (option A).
# --------------------------------------------------------------------------


def test_exact_fx_credit_tie_posts_its_floor_and_not_one_quantum_more() -> None:
    """`_credit_tie_fx_scenario` converts 5 EUR at 3/2 with no spread into an
    exact 7.5 USD -- a tie of the whole-USD quantum. A credit is rounded
    against the plan, so even at a tie it posts its floor: 7 USD, a rounding
    delta of -1/2 -- never the 8 a round-half-up gives. With a 1 USD
    whole-unit asset and a zero fee every BUY debit is a whole USD, so no
    debit is ever rounded at all: 7 units (exactly the posted credit) are
    feasible, 8 units (one quantum more) are not, in the exact replay and in
    the pinned SCIP model alike.

    `_posted_units_term` encodes a credit as `quantum * units` under
    `q*u <= exact <= q*u + q`. Off a quantum multiple -- 7.5 here -- that pins
    `units` to the floor itself; only at an exact multiple does it also admit
    one quantum less, and a smaller credit never helps a ledger `>= 0` row. So
    the model's feasible set equals the exact one, with no neighbour left to
    choose at the tie. Before option A the compiler refused this very scenario
    with `LedgerPostingScopeError` (the credit-tie guard, now removed) before
    a model existed; `_pinned_status` compiling it at all is the first half of
    this regression.
    """
    scenario = _credit_tie_fx_scenario(price=R(1), cap=R(10))
    view = build_exact_policy_view(scenario)
    funding = exact_decision_id("funding_transfer", "route:funding:eur")
    fx = exact_decision_id("fx_debit", "route:buy:usd:EUR")
    buy = exact_decision_id("buy_quantum", "route:buy:usd")

    # The rounding function itself, independently of the ledger: 7.5 sits
    # exactly on the .5 boundary of quantum ONE and still floors to 7.
    floored = NUM.post_floor(R(15, 2), ONE)
    assert floored.posted == R(7)
    assert floored.rounding_delta == R(-1, 2)

    for units, expected_feasible, expected_status, expected_usd_balance in (
        (7, True, "optimal", ZERO),  # 7 posted credit - 7 posted debit
        (8, False, "infeasible", R(-1)),  # one quantum more than the posted credit
    ):
        quanta = {funding: 5, fx: 5, buy: units}
        candidate = _candidate(view, quanta, candidate_id=f"candidate:credit-tie:{units}")
        evaluation = evaluate_exact_candidate(scenario, view, candidate)
        assert evaluation.candidate_valid is True, units  # inside every box: only the cash rules can decide

        # Precondition, verified rather than assumed: the conversion really is
        # an exact tie, posted at its floor.
        fx_evaluation = next(item for item in evaluation.fx if item.order_route_id == "route:buy:usd" and item.source_currency == "EUR")
        assert fx_evaluation.exact_destination_credit == R(15, 2), units  # 7.5 USD, an exact tie
        assert fx_evaluation.posted_destination_credit == R(7), units

        usd_cell = next(ledger for ledger in evaluation.ledgers if ledger.broker_id == "broker:destination" and ledger.currency == "USD")
        assert (usd_cell.fx_credit, usd_cell.buy_debit) == (R(7), R(units)), units
        assert usd_cell.final_spendable == expected_usd_balance, units

        assert evaluation.feasible is expected_feasible, units
        assert _pinned_status(scenario, view, quanta=quanta) == expected_status, units


# --------------------------------------------------------------------------
# Item A3: fail-closed rounded-family guard (never a silent exact fallback).
# --------------------------------------------------------------------------


def test_rounded_family_guard_fails_closed_on_unmodelled_sell_families() -> None:
    """The guard exists so that an unmodelled rounded family ERRORs rather
    than silently falling back to its exact expression -- the exact
    degradation that caused the Step3 §16.11 defect.

    Three properties: (1) every rounded family in `ledger.py` has a detector
    here, so a family added there without one trips immediately; (2) the
    baseline PAC scenario, which posts only modelled BUY/FX families, passes;
    (3) adding a SELL route makes the four SELL/tax families reachable, and
    since this build does not model them the guard raises.
    """
    # (1) fail-closed on an undetectable family.
    assert set(_ROUNDED_FAMILIES) <= set(_ROUNDED_FAMILY_DETECTORS)
    assert _MODELLED_ROUNDED_FAMILIES == frozenset({"fx_credit", "buy_debit", "buy_fee"})

    # (2) the baseline PAC scenario posts only modelled families -> no error.
    baseline = _pac_scenario()
    baseline_facts = build_scenario_facts(baseline)
    _require_modelled_rounded_families(baseline, baseline_facts)  # must not raise

    # (3) a SELL route makes the four unmodelled SELL/tax families reachable.
    buy_route = baseline.order_routes[0]
    sell_route = replace(buy_route, route_id="route:sell:usd", side="sell")
    sell_scenario = replace(baseline, order_routes=tuple(sorted((buy_route, sell_route), key=lambda route: route.route_id)))
    sell_facts = build_scenario_facts(sell_scenario)

    with pytest.raises(LedgerPostingScopeError) as excinfo:
        _require_modelled_rounded_families(sell_scenario, sell_facts)
    message = str(excinfo.value)
    for unmodelled_family in ("gross_sell_credit", "sell_fee", "broker_withheld_tax", "self_reserved_tax"):
        assert unmodelled_family in message
    # ... and it never blames a family this build actually models.
    for modelled_family in _MODELLED_ROUNDED_FAMILIES:
        assert modelled_family not in message


# --------------------------------------------------------------------------
# Item A4: non-negativity is ENFORCED (a `:nonneg` row per rounded flow), not
# assumed -- a non-negative `units` floored (credit) or ceiled (debit) at the
# quantum only matches the ledger's posting against the plan for x >= 0.
# --------------------------------------------------------------------------


def test_posted_units_terms_add_nonneg_row_per_rounded_flow() -> None:
    """`_posted_units_term` encodes a posting as `quantum * units` for a
    non-negative integer `units`, rounded against the plan: a credit at
    `floor(exact/quantum)`, a debit at `ceil(exact/quantum)`. That matches the
    ledger's posting of a non-negative magnitude (`numeric.post_floor` /
    `numeric.post_ceiling`) only for a non-negative amount. Each rounded flow
    therefore gets an explicit `:nonneg` row that *enforces* non-negativity
    rather than assuming it, so a future negative-capable flow fails loudly
    instead of rounding the wrong way. This asserts those rows are actually
    in the compiled model.
    """
    scenario = _coarse_funding_fx_scenario()
    view = build_exact_policy_view(scenario)
    program = _fresh_program(scenario, view)
    constraint_names = {constraint.name for constraint in program.model.getConss()}

    assert "posted_buy_debit:route:buy:usd:nonneg" in constraint_names
    assert "posted_buy_fee:route:buy:usd:nonneg" in constraint_names
    assert "posted_fx_credit:route:buy:usd:EUR:nonneg" in constraint_names


# --------------------------------------------------------------------------
# Item A5: the exact-flow families stay UNROUNDED -- they never pass through
# `_posted_units_term`, so no `posted_*` variable is ever created for them.
# --------------------------------------------------------------------------


def test_exact_flow_families_are_not_posted_through_units_terms() -> None:
    """`ledger.py`'s `_EXACT_FLOW_FAMILIES` (`initial_selected`, `funding_in`,
    `funding_out`, `fx_debit`) are summed unrounded, so none of them may reach
    `_posted_units_term`. Only `buy_debit`, `buy_fee` and `fx_credit` are
    posted -- proven here by the exact set of `posted_*` variables: it
    contains no funding transfer and no `fx_debit`, even though this scenario
    genuinely has both.
    """
    scenario = _coarse_funding_fx_scenario()
    view = build_exact_policy_view(scenario)
    program = _fresh_program(scenario, view)
    variable_names = {variable.name for variable in program.model.getVars()}
    posted_variable_names = {name for name in variable_names if name.startswith("posted_")}

    # This scenario really does carry a funding transfer and an fx_debit ...
    assert "funding:route:funding:eur" in variable_names
    assert "fx:route:buy:usd:EUR" in variable_names

    # ... yet the only posted variables are the three rounded flows -- never a
    # funding transfer, never the fx_debit leg.
    assert posted_variable_names == {
        "posted_buy_debit:route:buy:usd",
        "posted_buy_fee:route:buy:usd",
        "posted_fx_credit:route:buy:usd:EUR",
    }
    assert not any("funding" in name for name in posted_variable_names)
    assert not any(name.startswith("posted_fx_debit") for name in posted_variable_names)


# --------------------------------------------------------------------------
# Item A6 (C-FXPOS): an active FX conversion must post a nonzero credit. The
# Decimal-exact replay checks it (`FX_CREDIT_POSITIVE`); the compiled model
# must carry it too, as a live `posted_fx_credit:{route}:{currency}:active`
# row -- the rounding rows alone happily post a zero credit.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "suffix",
    [
        pytest.param("nonneg", id="nonneg-rounding-row"),
        pytest.param("lo", id="lo-rounding-row"),
        pytest.param("hi", id="hi-rounding-row"),
        pytest.param("active", id="active-fx-credit-positive-row"),
    ],
)
def test_fx_credit_positive_has_a_compiled_row_per_fx_conversion(suffix: str) -> None:
    """The exact replay rejects an FX action whose credit posts zero
    (`FX_CREDIT_POSITIVE`: no action, or a posted credit `> 0`). The compiled
    model mirrors that rule with one `:active` row per FX conversion, next
    to the rounding rows of the same posted credit -- `:nonneg`, `:lo`,
    `:hi`, which keep their names (the controls of this parametrization).
    The coarse fixture has exactly one conversion, EUR into the USD route.
    """
    scenario = _coarse_funding_fx_scenario()
    view = build_exact_policy_view(scenario)
    program = _fresh_program(scenario, view)
    constraint_names = {constraint.name for constraint in program.model.getConss()}

    assert f"posted_fx_credit:route:buy:usd:EUR:{suffix}" in constraint_names


_ZERO_POSTED_FX_CREDIT_CASES = [
    pytest.param(1, R(2, 5), id="0.4-usd-posts-zero-under-any-rounding"),
    pytest.param(2, R(4, 5), id="0.8-usd-floors-to-zero"),
]


@pytest.mark.parametrize(("source_eur", "exact_credit"), _ZERO_POSTED_FX_CREDIT_CASES)
def test_fx_credit_that_posts_zero_is_rejected_by_the_exact_replay(source_eur: int, exact_credit: Any) -> None:
    """On `_sub_quantum_fx_credit_scenario`, converting 1 or 2 EUR yields an
    exact 0.4 or 0.8 USD, whose floor at the whole-USD quantum is 0. Spending
    euros to receive nothing is not a conversion: the exact replay rejects
    the point on `FX_CREDIT_POSITIVE` alone -- nothing is bought, so every
    cash cell stays `>= 0`.

    The 0.4 USD case posts 0 under a round-half-up too, so it holds already
    (a control); the 0.8 USD case posted 1 under HALF_UP and needs the credit
    to floor.
    """
    scenario = _sub_quantum_fx_credit_scenario()
    view = build_exact_policy_view(scenario)
    funding = exact_decision_id("funding_transfer", "route:funding:eur")
    fx = exact_decision_id("fx_debit", "route:buy:usd:EUR")
    buy = exact_decision_id("buy_quantum", "route:buy:usd")
    quanta = {funding: source_eur, fx: source_eur, buy: 0}

    candidate = _candidate(view, quanta, candidate_id=f"candidate:fx-credit-zero:{source_eur}")
    evaluation = evaluate_exact_candidate(scenario, view, candidate)
    assert evaluation.candidate_valid is True  # inside every box: only the posting rules can decide

    fx_evaluation = next(item for item in evaluation.fx if item.order_route_id == "route:buy:usd" and item.source_currency == "EUR")
    assert fx_evaluation.exact_destination_credit == exact_credit
    assert fx_evaluation.posted_destination_credit == ZERO

    positive = next(item for item in evaluation.constraints if item.ref_id == "constraint:fx_credit_positive:route:buy:usd:EUR")
    assert (positive.satisfied, positive.value) == (False, ZERO)
    assert evaluation.feasible is False
    assert evaluation.conflict_codes == ("FX_CREDIT_POSITIVE",)


@pytest.mark.parametrize(("source_eur", "exact_credit"), _ZERO_POSTED_FX_CREDIT_CASES)
def test_active_fx_conversion_whose_credit_posts_zero_is_infeasible_in_the_compiled_model(source_eur: int, exact_credit: Any) -> None:
    """The compiled half of the test above, on the very same points: the
    pinned SCIP model must reject them as the exact replay does. Its rounding
    rows admit the zero credit (`q*u <= exact <= q*u + q` holds at `u = 0`
    for any exact credit below one quantum) and nothing is bought with it,
    so only the `:active` row can object.
    """
    scenario = _sub_quantum_fx_credit_scenario()
    view = build_exact_policy_view(scenario)
    funding = exact_decision_id("funding_transfer", "route:funding:eur")
    fx = exact_decision_id("fx_debit", "route:buy:usd:EUR")
    buy = exact_decision_id("buy_quantum", "route:buy:usd")
    quanta = {funding: source_eur, fx: source_eur, buy: 0}

    # Precondition, verified rather than assumed: the exact credit (which no
    # rounding rule moves) is below one whole-USD quantum, so its floor is 0.
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, quanta, candidate_id=f"candidate:fx-credit-zero-compiled:{source_eur}"))
    fx_evaluation = next(item for item in evaluation.fx if item.order_route_id == "route:buy:usd" and item.source_currency == "EUR")
    assert fx_evaluation.exact_destination_credit == exact_credit
    assert ZERO < exact_credit < ONE

    assert _pinned_status(scenario, view, quanta=quanta) == "infeasible"


def test_fx_credit_positive_admits_a_nonzero_floored_credit_and_no_conversion() -> None:
    """Green controls on the same fixture: the `:active` row may never prune
    a point the exact replay accepts. 3 EUR convert into an exact 1.2 USD
    that posts 1 USD (floor and round-half-up agree), a nonzero credit; and
    no conversion at all leaves the rule nothing to check. Both points are
    feasible in the exact replay and in the pinned SCIP model.
    """
    scenario = _sub_quantum_fx_credit_scenario()
    view = build_exact_policy_view(scenario)
    funding = exact_decision_id("funding_transfer", "route:funding:eur")
    fx = exact_decision_id("fx_debit", "route:buy:usd:EUR")
    buy = exact_decision_id("buy_quantum", "route:buy:usd")
    constraint_id = "constraint:fx_credit_positive:route:buy:usd:EUR"

    converting = {funding: 3, fx: 3, buy: 0}
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, converting, candidate_id="candidate:fx-credit-one"))
    fx_evaluation = next(item for item in evaluation.fx if item.order_route_id == "route:buy:usd" and item.source_currency == "EUR")
    assert (fx_evaluation.exact_destination_credit, fx_evaluation.posted_destination_credit) == (R(6, 5), R(1))
    positive = next(item for item in evaluation.constraints if item.ref_id == constraint_id)
    assert (positive.satisfied, positive.value) == (True, R(1))
    assert evaluation.feasible is True
    assert _pinned_status(scenario, view, quanta=converting) == "optimal"

    idle = {funding: 0, fx: 0, buy: 0}
    evaluation = evaluate_exact_candidate(scenario, view, _candidate(view, idle, candidate_id="candidate:fx-idle"))
    assert not evaluation.fx  # no FX action at all
    positive = next(item for item in evaluation.constraints if item.ref_id == constraint_id)
    assert positive.satisfied is True
    assert evaluation.feasible is True
    assert _pinned_status(scenario, view, quanta=idle) == "optimal"
