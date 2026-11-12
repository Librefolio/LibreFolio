"""V7 in the SCIP model: a Broker converts a currency pair in one direction at most (A2, project 67).

One binary per Broker and pair that has an FX decision in each direction (``evaluation.reachability.fx_two_way_pairs``,
the evaluator's own list): ``direction = 1`` lets only the low-to-high debit be nonzero, ``direction = 0`` only the
high-to-low one. Each row's coefficient is its decision's own upper bound, read back off the SCIP variable
(``getUbOriginal()``), never a constant of ours (specification P5). The exact replay checks the same rule as
``FX_SINGLE_DIRECTION``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.services.pac_allocator.constraints.facts import CompiledVariables, ScenarioFacts
from backend.app.services.pac_allocator.evaluation.reachability import fx_two_way_pairs
from backend.app.services.pac_allocator.models import ExactPlannerScenario

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Model


def add_fx_single_direction_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables) -> None:
    """``FX_SINGLE_DIRECTION``: at most one direction of each two-way pair carries a debit."""
    for pair in fx_two_way_pairs(facts.fx_decisions):
        low_to_high = variables.quanta[pair.low_to_high.decision_id]
        high_to_low = variables.quanta[pair.high_to_low.decision_id]
        direction = model.addVar(vtype="B", name=f"fx_direction:{pair.key}")
        model.addCons(low_to_high <= low_to_high.getUbOriginal() * direction, name=f"fx_single_direction:{pair.key}:low_to_high")
        model.addCons(high_to_low <= high_to_low.getUbOriginal() * (1 - direction), name=f"fx_single_direction:{pair.key}:high_to_low")
