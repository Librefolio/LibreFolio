"""SCIP compiler orchestrator for the PAC/Rebalancer solver (Step 3, Stage 2).

Builds one ``CompiledProgram`` per ``(scenario, view)`` pair: the SCIP
``Model``, every decision/activation/fee ``Variable`` (``CompiledVariables``),
every hard constraint (``constraints.compile_hard_constraints``), and the
ordered objective cascade (``objectives.build_objective_cascade``), ready for
``solver.py``'s lexicographic re-optimization loop (Step3 Stage 3, not yet
built). This module never calls ``model.optimize()`` itself — building and
solving are deliberately separate responsibilities.

Scope: PAC ``proportional`` policy, ``primary`` purpose only (see
``constraints.py``/``objectives.py`` module docstrings and Step3 §16.6/
§16.9). ``compile_policy_program`` raises ``PolicyProgramScopeError`` for any
other ``(product, policy, purpose)`` combination rather than silently
building an incomplete or wrong model — this build only implements PAC
proportional.

``ObjectiveInputs`` (``fixed_reference``/per-Asset ``target_value``) are
obtained by one probe call to the public ``evaluate_exact_candidate`` rather
than re-deriving evaluator.py's private reachability algorithms (see
``objectives.py``'s ``ObjectiveInputs`` docstring). The probe candidate uses
each decision's own ``frozen_quanta`` (when ``mode == "frozen_exact"``) or
``baseline_quanta`` otherwise — guaranteed contract-valid for *any*
well-formed ``ExactPolicyView`` by ``DecisionAccess``'s own invariants
(``_validate_decision_mode``/``__post_init__``), not merely for this build's
expected all-``mutable``, all-zero-baseline PAC-proportional-primary shape.
This is also semantically inert: reading evaluator.py confirms
``fixed_reference``/``target_value`` never depend on the probed quanta at
all (only decision *contract* validity matters — see
``_candidate_contract_conflicts``/``_decision_access_conflicts``), so any
guaranteed-valid probe candidate returns the identical constants.

Known search-quality limitation, stated here (not only in the plan and the
regression test) so a reader meets it where the code is: the fee epigraph
``constraints.add_fee_epigraph_constraints`` builds is **cap-oblivious** —
its internal upper-bound estimate is ``rate * notional_upper``, ignoring the
route's ``maximum_fee``. A compiled model can therefore believe a heavily
capped BUY route costs more in fees than it truly does, which can only bias
which candidate the solver *prefers*. It can never cause false infeasibility
(the estimate is pessimistic, never optimistic) and never corrupts any
reported number: every fee published or replayed comes from
``evaluate_exact_candidate``'s exact ``calculate_fee``, never from the SCIP
variable. Locked by ``test_fee_epigraph_cap_oblivious_regression``. If a
solve ever produces an incumbent whose SCIP-internal objective disagrees
with the exact replay in a way that changes the *lexicographic ranking*,
that is out of tolerance by definition and must be escalated — not absorbed
by widening an epsilon.
"""

from __future__ import annotations

from dataclasses import dataclass

from pyscipopt import Model

from backend.app.services.pac_allocator.constraints import (
    CompiledVariables,
    ScenarioFacts,
    as_float,
    build_scenario_facts,
    compile_hard_constraints,
)
from backend.app.services.pac_allocator.evaluator import evaluate_exact_candidate
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    CandidateDecision,
    DecisionAccess,
    ExactPlannerScenario,
    ExactPolicyView,
)
from backend.app.services.pac_allocator.objectives import (
    ObjectiveInputs,
    ObjectiveStage,
    build_objective_cascade,
    compute_objective_inputs,
)

__all__ = [
    "CompiledProgram",
    "PolicyProgramContractError",
    "PolicyProgramScopeError",
    "compile_policy_program",
]


class PolicyProgramScopeError(ValueError):
    """Raised when ``compile_policy_program`` is asked to build a model for a
    ``(product, policy, purpose)`` combination this Stage 2 build does not
    implement (only PAC ``proportional``/``primary`` is in scope).
    """


class PolicyProgramContractError(ValueError):
    """Raised only if the internal all-decisions probe candidate is somehow
    rejected by ``evaluate_exact_candidate`` — meaning ``view`` itself is not
    well-formed against its own ``DecisionAccess`` invariants. Should never
    trigger for a policy view ``normalize.py`` actually produced; kept as a
    defensive, explicit failure rather than a silent wrong answer.
    """


@dataclass(frozen=True, slots=True)
class CompiledProgram:
    """Everything ``solver.py`` needs to run the lexicographic
    re-optimization loop, plus the scenario-derived context useful for
    reporting/debugging.
    """

    model: Model
    scenario: ExactPlannerScenario
    view: ExactPolicyView
    facts: ScenarioFacts
    variables: CompiledVariables
    objective_stages: tuple[ObjectiveStage, ...]
    objective_inputs: ObjectiveInputs


def _require_supported_scope(scenario: ExactPlannerScenario, view: ExactPolicyView) -> None:
    if scenario.product != "pac" or scenario.policy != "proportional":
        raise PolicyProgramScopeError(f"compiler.py only supports PAC proportional for now; got product={scenario.product!r} policy={scenario.policy!r}")
    if view.purpose != "primary":
        raise PolicyProgramScopeError(f"compiler.py only supports the primary purpose for now; got purpose={view.purpose!r}")


def _probe_quanta(access: DecisionAccess) -> int:
    """A guaranteed contract-valid quanta value for one decision — see the
    module docstring for why this (not a blind ``0``) is the correct probe.
    """
    return access.frozen_quanta if access.mode == "frozen_exact" else access.baseline_quanta


def _probe_objective_inputs(scenario: ExactPlannerScenario, view: ExactPolicyView) -> ObjectiveInputs:
    probe_candidate = CandidateActionVector(
        view_id=view.view_id,
        candidate_id="__stage2_compiler_probe__",
        decisions=tuple(CandidateDecision(decision_id=access.decision_id, quanta=_probe_quanta(access)) for access in view.decisions),
    )
    evaluation = evaluate_exact_candidate(scenario, view, probe_candidate)
    if evaluation.accounting is None:
        raise PolicyProgramContractError("compiler.py's internal probe candidate was rejected; the policy view is not well-formed")
    target_value_by_asset = {asset.asset_id: as_float(asset.target_value) for asset in evaluation.assets}
    return compute_objective_inputs(target_value_by_asset, as_float(evaluation.accounting.fixed_reference))


def _create_variables(model: Model, scenario: ExactPlannerScenario, view: ExactPolicyView) -> CompiledVariables:
    quanta = {access.decision_id: model.addVar(vtype="I", lb=access.lower_quanta, ub=access.upper_quanta, name=access.decision_id) for access in view.decisions}
    buy_active = {}
    buy_fee = {}
    for route in scenario.order_routes:
        if route.side != "buy":
            continue
        buy_active[route.route_id] = model.addVar(vtype="B", name=f"active_buy:{route.route_id}")
        buy_fee[route.route_id] = model.addVar(vtype="C", lb=0.0, name=f"fee:{route.route_id}")
    funding_active = {route.route_id: model.addVar(vtype="B", name=f"active_funding:{route.route_id}") for route in scenario.funding_routes}
    return CompiledVariables(quanta=quanta, buy_active=buy_active, funding_active=funding_active, buy_fee=buy_fee)


def compile_policy_program(scenario: ExactPlannerScenario, view: ExactPolicyView) -> CompiledProgram:
    """Build one complete SCIP model for ``scenario``/``view``: variables,
    hard constraints, and the ordered objective cascade. Never solves.
    """
    _require_supported_scope(scenario, view)
    facts = build_scenario_facts(scenario)
    model = Model(f"pac_allocator:{view.view_id}")
    model.hideOutput()
    variables = _create_variables(model, scenario, view)
    compile_hard_constraints(model, scenario, facts, variables)
    objective_inputs = _probe_objective_inputs(scenario, view)
    objective_stages = tuple(build_objective_cascade(model, scenario, facts, variables, objective_inputs, view))
    return CompiledProgram(
        model=model,
        scenario=scenario,
        view=view,
        facts=facts,
        variables=variables,
        objective_stages=objective_stages,
        objective_inputs=objective_inputs,
    )
