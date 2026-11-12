"""V7 in the SCIP model: on a Broker a currency that receives a conversion does not give one (A2 and A3, project 67).

One binary per Broker and currency that both receives and gives (``evaluation.reachability.fx_relay_groups``, the evaluator's own
list): ``side = 1`` lets only the decisions that convert INTO the currency be nonzero, ``side = 0`` only those that convert OUT of
it. Each row's coefficient is its decision's own upper bound, read back off the SCIP variable (``getUbOriginal()``), never a
constant of ours (specification P5). The exact replay checks the same rule as ``FX_NO_RELAY``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.services.pac_allocator.constraints.facts import CompiledVariables, ScenarioFacts
from backend.app.services.pac_allocator.evaluation.reachability import fx_relay_groups
from backend.app.services.pac_allocator.models import ExactPlannerScenario

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids a hard pyscipopt import for readers
    from pyscipopt import Model


def add_fx_no_relay_constraints(model: Model, scenario: ExactPlannerScenario, facts: ScenarioFacts, variables: CompiledVariables) -> None:
    """``FX_NO_RELAY``: a currency of a Broker is on the receiving side or on the giving side of its conversions, never both."""
    for group in fx_relay_groups(facts.fx_decisions):
        side = model.addVar(vtype="B", name=f"fx_side:{group.key}")
        for spec in group.receiving:
            decision = variables.quanta[spec.decision_id]
            model.addCons(decision <= decision.getUbOriginal() * side, name=f"fx_no_relay:{group.key}:in:{spec.decision_id}")
        for spec in group.giving:
            decision = variables.quanta[spec.decision_id]
            model.addCons(decision <= decision.getUbOriginal() * (1 - side), name=f"fx_no_relay:{group.key}:out:{spec.decision_id}")
