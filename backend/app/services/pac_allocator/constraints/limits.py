"""V5 and V10 in the SCIP model (A3, project 67): limits on the final value of Assets and of cash cells, and the uninvested cap.

Every row reads what the replay reads, resolved to amounts against the same reference (``evaluation.limits``):

* ``entry_limit_min/max:<entry>``: the final value of an Asset (``asset_final_value_exprs``) or of a cash cell (the sums
  ``add_ledger_balance_constraints`` returns, valued in the valuation currency) between its resolved bounds;
* ``uninvested_max``: ``reference - sum(final asset values) <= sum of the cash maxima``, only where V10 applies (D8).

Rows are written on the integer quantities of the model (order steps and registered units), never on exact amounts. Without
limits nothing is added, so the model is the one of a scenario without them. A cell that carries a limit but no flow has the
constant value zero; a zero variable stands for it so a violated bound stays an infeasible row, not a Python boolean.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.services.pac_allocator.constraints.facts import CompiledVariables, ScenarioFacts, as_float, asset_final_value_exprs, valuation_rate
from backend.app.services.pac_allocator.evaluation.limits import ResolvedLimits, uninvested_maximum
from backend.app.services.pac_allocator.models import ExactPlannerScenario

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Model

    from backend.app.services.pac_allocator.constraints.facts import LinearTerm


def add_limit_constraints(
    model: Model,
    scenario: ExactPlannerScenario,
    facts: ScenarioFacts,
    variables: CompiledVariables,
    cells: dict[tuple[str, str], list[LinearTerm]],
    limits: ResolvedLimits | None,
) -> None:
    """``ENTRY_VALUE_WITHIN_LIMITS`` for every limited entry, and ``UNINVESTED_WITHIN_CASH_MAXIMA`` where it applies."""
    if limits is None or not limits.by_entry:
        return
    zero = model.addVar(vtype="C", lb=0.0, ub=0.0, name="limit_zero")
    final_value = asset_final_value_exprs(scenario, facts, variables)
    for entry, bounds in limits.by_entry.items():
        if entry.kind == "asset":
            value: LinearTerm = final_value[entry.asset_id]
        else:
            rate = valuation_rate(facts, entry.currency)
            value = sum(cells.get((entry.broker_id, entry.currency), []), zero) * rate
        if bounds.minimum is not None:
            model.addCons(value >= as_float(bounds.minimum), name=f"entry_limit_min:{entry.key}")
        if bounds.maximum is not None:
            model.addCons(value <= as_float(bounds.maximum), name=f"entry_limit_max:{entry.key}")
    maximum = uninvested_maximum(scenario, facts.ledger_cells, limits)
    if maximum is not None:
        invested = sum(final_value.values(), zero)
        model.addCons(as_float(limits.reference) - invested <= as_float(maximum), name="uninvested_max")
