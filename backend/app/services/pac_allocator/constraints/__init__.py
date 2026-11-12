"""Hard-constraint builders for the PAC/Rebalancer SCIP compiler (Step 3).

Scope for this build: PAC ``proportional`` policy, ``primary`` purpose only
(see ``plan-phase00Step3PacRebalancerSolverPolicies.prompt.md`` §16.6/§16.9).
SELL is always off for this policy, so every SELL-only ``ExactConstraintCode``
(``SELL_WITHIN_INVENTORY``, ``NO_ASSET_BUY_AND_SELL``, ``SELL_ELIGIBLE``, ...)
is out of scope by construction, not merely deferred.

Every ``ExactConstraintCode`` that ``evaluator.py`` enforces at replay time
falls into exactly one of three buckets here:

1. Already a ``DecisionAccess`` box bound (``lower_quanta``/``upper_quanta``)
   — ``compiler.py`` sets it directly on the SCIP variable; nothing to add
   here (``ORDER_CAP``, most of ``ORDER_QUANTIZED``'s effect, ``SELECTED_
   WITHIN_AVAILABLE``'s upstream precondition, disabled/frozen decisions).
2. A scenario-level precondition or accounting tautology, true by
   construction of the linear expressions this module and ``objectives.py``
   build — never a live SCIP row (``FUNDING_SOURCE_CONSERVATION``,
   ``NO_SELF_TRANSFER``, ``NO_DOUBLE_COUNT``, ``ORDER_QUANTIZED``,
   ``ORDER_SIDE_ALLOWED``, ``NO_IMPLICIT_ROUTE``, ``FX_RATE_ORDER_SAFE``,
   ``FX_NATIVE_QUANTUM``, ``ROUTE_DECLARED``,
   ``COST_NOT_INVESTMENT``, ``SELL_POSTED_ONCE``, ``ROUNDING_BOUND``,
   ``ACCOUNTING_IDENTITY``, ``REBALANCER_NONEMPTY`` — this last one is also
   simply inapplicable, ``scenario.product == "pac"`` here).
3. A genuine cross-decision or semi-continuous constraint a plain box bound
   cannot express — one ``model.addCons(...)`` call per instance:
   ``FUNDING_WITHIN_SELECTED`` (funding-source pooling),
   ``NO_SHORT_OR_LEVERAGE`` (Broker×currency ledger balance, folding in
   ``FX_SOURCE_CASH``'s spendable-cash floor), ``FX_CREDIT_POSITIVE`` (an
   active conversion posts a nonzero credit: the ``:active`` row of its
   posted credit, ``_posted_units_term``), ``ORDER_MIN_IF_ACTIVE`` (semi-continuous:
   measure is either exactly zero or at least the active floor), and the
   fee epigraph (linearizes ``financial_math.fees.calculate_fee``'s ``fixed +
   clamp(rate * notional, floor, cap)`` for the ``explicit_cost`` objective).

The Decimal-exact replay via ``evaluate_exact_candidate`` is the only source
of truth for feasibility and for every reported number; this module's job is
only to keep the solver's search space close enough to the truth that a
floating incumbent survives replay. Every Big-M coefficient below is derived
from a route's own known finite bounds (``order_step * upper_quanta``) —
never an arbitrary constant, per Step3 §4's "Nessun Big-M arbitrario" rule.

Fee (``add_fee_epigraph_constraints``): for a nonzero order
``financial_math.fees.calculate_fee`` is ``fixed + clamp(rate * notional, floor, cap)``, three
pieces of the notional: flat at the floor, linear, flat at the cap. Under a
minimization, plain lower-bound rows represent the convex floor+linear part
exactly. The cap makes the function concave, so where it can bind within
the route's range (``_fee_cap_excess``: ``rate * notional_upper > cap``) a
``fee_capped`` binary picks the branch: the linear one, where the fee's
upper bound implies ``rate * notional <= cap``, or the flat one, where the
fee is exactly ``fixed + cap``. The minimal fee the model admits is then
``financial_math.fees.calculate_fee`` at every notional. The posted fee is debited in the cash
ledger, so this is also what lets the model reach the plans the exact
replay accepts.

Fee bound (``_fee_clamp_upper``): the fee variable of an active BUY route is
bounded by ``fixed + max(floor, min(rate * notional_upper, cap))``, in the
epigraph's Big-M and in the posted-fee units alike. Two defects found on
2026-09-24 shaped it:

- X2: the minimum belongs in the bound. With ``rate * notional_upper``
  alone, a minimum above it (a flat minimum on a zero rate, or a small
  route) left the floor row unsatisfiable, order on or off, and the whole
  model infeasible.
- QX1-a: the cap used to be ignored. The linear row priced a capped order
  at the uncapped fee and excluded plans the exact replay accepts (EUR50 050
  at EUR100 a unit, 0.19% capped at EUR18: the replay buys 500 units, the
  model stopped at 499). The cap enters the bound only together with its
  binary: with the linear row always on, a capped bound would make every
  order past the cap infeasible (at most 94 units in that example).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.services.pac_allocator.constraints.cells import (
    _MODELLED_ROUNDED_FAMILIES,  # noqa: F401 -- private, but the policy tests import it from this path
    _ROUNDED_FAMILY_DETECTORS,  # noqa: F401 -- same
    LedgerPostingScopeError,
    _require_modelled_rounded_families,  # noqa: F401 -- same
    add_ledger_balance_constraints,
)
from backend.app.services.pac_allocator.constraints.facts import (
    CompiledVariables,
    ScenarioFacts,
    as_float,  # noqa: F401 -- private use by the policy tests, from this path
    build_scenario_facts,
    fx_rate,
    order_notional,
    order_prices,
    planning_fx_rate,
    valuation_rate,
)
from backend.app.services.pac_allocator.constraints.fees import add_fee_epigraph_constraints
from backend.app.services.pac_allocator.constraints.funding import add_funding_activation_constraints, add_funding_pool_constraints
from backend.app.services.pac_allocator.constraints.fx import add_fx_no_relay_constraints
from backend.app.services.pac_allocator.constraints.limits import add_limit_constraints
from backend.app.services.pac_allocator.constraints.orders import add_order_activation_constraints
from backend.app.services.pac_allocator.evaluation.limits import ResolvedLimits
from backend.app.services.pac_allocator.models import ExactPlannerScenario

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Model

__all__ = [
    "CompiledVariables",
    "LedgerPostingScopeError",
    "ScenarioFacts",
    "add_fee_epigraph_constraints",
    "add_funding_activation_constraints",
    "add_funding_pool_constraints",
    "add_ledger_balance_constraints",
    "add_order_activation_constraints",
    "build_scenario_facts",
    "compile_hard_constraints",
    "fx_rate",
    "order_notional",
    "order_prices",
    "planning_fx_rate",
    "valuation_rate",
]


def compile_hard_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables, limits: ResolvedLimits | None = None) -> None:
    """Add every real cross-decision / semi-continuous constraint for one
    PAC ``proportional`` ``primary`` scenario. Box bounds are set on the
    variables themselves by ``compiler.py`` before this is called.

    ``limits`` are the scenario's V5 limits resolved to amounts (``evaluation.limits.resolve_scenario_limits``): without
    them, or without any limit, the model has no limit row (A3).
    """
    add_funding_pool_constraints(model, scenario, facts, variables)
    cells = add_ledger_balance_constraints(model, scenario, facts, variables)
    add_order_activation_constraints(model, scenario, facts, variables)
    add_funding_activation_constraints(model, scenario, facts, variables)
    add_fee_epigraph_constraints(model, scenario, facts, variables)
    add_fx_no_relay_constraints(model, scenario, facts, variables)
    add_limit_constraints(model, scenario, facts, variables, cells, limits)
