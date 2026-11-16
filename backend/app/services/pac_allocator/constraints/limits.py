"""V5 in the SCIP model (A3, project 67): limits on the final value of Assets and of cash cells.

Every row reads what the replay reads, resolved to amounts against the same reference (``evaluation.limits``):

* ``entry_limit_min/max:<entry>``: the final value of an Asset or of a cash cell (the sums ``add_ledger_balance_constraints``
  returns, valued in the valuation currency) between its resolved bounds. They are written on integers with exact bounds
  wherever the entry allows it, so SCIP's relative tolerance cannot accept a plan the replay refuses (see ``add_limit_constraints``).

Without limits nothing is added, so the model is the one of a scenario without them. A cell that carries a limit but no flow has
the constant value zero; a zero variable stands for it so a violated bound stays an infeasible row, not a Python boolean.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import TYPE_CHECKING

from backend.app.services.pac_allocator.constraints.facts import CompiledVariables, ScenarioFacts, as_float, asset_final_value_exprs
from backend.app.services.pac_allocator.evaluation.bounds import current_value_by_asset
from backend.app.services.pac_allocator.evaluation.keys import exact_decision_id
from backend.app.services.pac_allocator.evaluation.limits import LimitEntry, ResolvedBounds, ResolvedLimits, buy_value_per_quantum
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index, to_valuation
from backend.app.services.pac_allocator.models import ExactOrderRoute, ExactPlannerScenario
from backend.app.services.pac_allocator.numeric import ExactRatio

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Model

    from backend.app.services.pac_allocator.constraints.facts import LinearTerm


# SCIP checks a linear row with a tolerance relative to its bound (~1e-6): on a row near EUR1000 a value a thousandth over is
# accepted, and the exact replay then refuses the plan. So a limit is written, where it can be, on integers with an exact bound.
_FLOAT_TIGHTENING = 2e-6
_UNITS_WITH_RELATIVE_SLACK = 10**6


def _floor(value: ExactRatio) -> int:
    return value.numerator // value.denominator


def _ceil(value: ExactRatio) -> int:
    return -((-value.numerator) // value.denominator)


def add_limit_constraints(
    model: Model,
    scenario: ExactPlannerScenario,
    facts: ScenarioFacts,
    variables: CompiledVariables,
    cells: dict[tuple[str, str], list[LinearTerm]],
    limits: ResolvedLimits | None,
    reserves_by_cell: dict[tuple[str, str], list[LinearTerm]] | None = None,
) -> None:
    """``ENTRY_VALUE_WITHIN_LIMITS`` for every limited entry, written so that SCIP cannot accept what the replay refuses.

    * An Asset bought on one route depends on one decision: its limits become an integer bound on that variable, computed
      exactly (floor of the maximum, ceil of the minimum). No float, and a plan exactly on the limit stays allowed.
    * A cash cell is a sum of integer quanta of its currency: its row is written in those units with an exact floor or ceil
      bound; above 10^6 units a margin of ``ceil(1e-6 * N)`` units covers SCIP's relative tolerance.
    * An Asset on several routes stays a float row, tightened inward by ``2e-6 * max(1, |limit|)``. This has a cost: a plan
      closer to the limit than that, which the replay would accept, is excluded. It is the price of never accepting one the
      replay refuses, and it only touches Assets with several routes.
    """
    if limits is None or not limits.by_entry:
        return
    index = build_scenario_index(scenario)
    zero = model.addVar(vtype="C", lb=0.0, ub=0.0, name="limit_zero")
    buy_routes: dict[str, list[ExactOrderRoute]] = defaultdict(list)
    for route in scenario.order_routes:
        if route.side == "buy":
            buy_routes[route.asset_id].append(route)
    final_value = asset_final_value_exprs(scenario, facts, variables)
    current = current_value_by_asset(scenario, index)
    for entry, bounds in limits.by_entry.items():
        if entry.kind == "cash":
            _cash_rows(model, index, facts, cells, zero, entry, bounds, (reserves_by_cell or {}).get((entry.broker_id, entry.currency), []))
        elif len(buy_routes[entry.asset_id]) == 1:
            _single_route_bounds(model, index, variables, zero, entry, bounds, buy_routes[entry.asset_id][0], current.get(entry.asset_id, ExactRatio(0)))
        else:
            _float_rows(model, final_value[entry.asset_id], entry, bounds)


def _single_route_bounds(model: Model, index, variables: CompiledVariables, zero, entry: LimitEntry, bounds: ResolvedBounds, route: ExactOrderRoute, current: ExactRatio) -> None:
    """One route, one decision: the limits, less what the Asset is already worth (``current``, zero in the PAC), as integer
    bounds on its quanta; an empty range is an infeasible row."""
    variable = variables.quanta[exact_decision_id("buy_quantum", route.route_id)]
    unit = buy_value_per_quantum(index, route)
    lower = max(int(variable.getLbOriginal()), 0 if bounds.minimum is None else _ceil((bounds.minimum - current) / unit))
    upper = int(variable.getUbOriginal()) if bounds.maximum is None else min(int(variable.getUbOriginal()), _floor((bounds.maximum - current) / unit))
    if lower > upper:
        model.addCons(zero >= 1, name=f"entry_limit_empty:{entry.key}")
        return
    model.chgVarUb(variable, upper)
    model.chgVarLb(variable, lower)


def _cash_rows(model: Model, index, facts: ScenarioFacts, cells, zero, entry: LimitEntry, bounds: ResolvedBounds, reserves: list | None = None) -> None:
    """A cash cell in whole quanta of its currency, bounds floored or ceiled exactly in those units.

    SCIP accepts a row within a tolerance relative to the side it sees, and the cell's constant (its own cash) moves to that
    side: a cell holding 17 350 € with a maximum of 2 000 € is the row «decisions ≤ −1 535 000 units», and a violation of
    1.5 units passes (the consultant's «cashmax», lot CR of project 67: a cell a cent above its maximum in the replay). So
    the margin of ``ceil(1e-6 · N)`` units is taken on the side SCIP holds once the row is written, not on the bound alone.

    The Rebalancer's cell is continuous, each posting less the reserve it keeps for its rounding (row 6): its value is the
    lowest cash the replay can post. A minimum reads it as it is. A maximum reads the highest cash the replay can post, the
    cell with its ``reserves`` back in, since a rounding never adds cash. The replay's cash is a whole number of quanta, so
    a row held within SCIP's tolerance of a whole bound still holds the bound."""
    quantum = facts.currency_quantum[entry.currency]
    units = sum(cells.get((entry.broker_id, entry.currency), []), zero) / quantum
    per_unit = to_valuation(index, index.currency_quantum[entry.currency], entry.currency)  # valuation currency of one quantum
    if bounds.maximum is not None:
        highest = units + sum(reserves, 0.0) / quantum if reserves else units
        row = model.addCons(highest <= _floor(bounds.maximum / per_unit), name=f"entry_limit_max:{entry.key}")
        side = model.getRhs(row)
        model.chgRhs(row, side - _tolerance_margin(side))
    if bounds.minimum is not None:
        row = model.addCons(units >= _ceil(bounds.minimum / per_unit), name=f"entry_limit_min:{entry.key}")
        side = model.getLhs(row)
        model.chgLhs(row, side + _tolerance_margin(side))


def _tolerance_margin(side: float) -> int:
    """The whole units SCIP's relative tolerance can let through on a row whose side is ``side`` units: none up to 10^6,
    ``ceil(|side| / 10^6)`` above."""
    magnitude = abs(side)
    return -(-math.ceil(magnitude) // _UNITS_WITH_RELATIVE_SLACK) if magnitude > _UNITS_WITH_RELATIVE_SLACK else 0


def _float_rows(model: Model, value: LinearTerm, entry: LimitEntry, bounds: ResolvedBounds) -> None:
    """An Asset on several routes: a float row tightened inward, see ``add_limit_constraints``."""
    if bounds.maximum is not None:
        limit = as_float(bounds.maximum)
        model.addCons(value <= limit - _FLOAT_TIGHTENING * max(1.0, abs(limit)), name=f"entry_limit_max:{entry.key}")
    if bounds.minimum is not None:
        limit = as_float(bounds.minimum)
        model.addCons(value >= limit + _FLOAT_TIGHTENING * max(1.0, abs(limit)), name=f"entry_limit_min:{entry.key}")
