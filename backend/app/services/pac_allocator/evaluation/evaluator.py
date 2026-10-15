"""Exact evaluator for the PAC/Rebalancer planner v2.

Every quantity here is computed on ``ExactRatio``, never on floats: the planner
must be able to *prove* a result, and a proof cannot rest on a representation
that rounds. The evaluator is deliberately independent of the solver — it scores
a candidate without knowing how that candidate was produced, which is what makes
it usable as the formula the SCIP objectives mirror, as the referee that replays
every SCIP incumbent (``rounding_top_ups`` then tells a cash deficit left by
rounding against the plan, which the user can top up, from a rejection), and —
in the test tree — as the scorer behind the exhaustive oracle.

The P1 ``analyze`` arithmetic that used to open this file was removed on
2026-09-21 (`b82e59ffa` and its follow-up): it was a Decimal prototype for
budgets and target gaps, never released, superseded by the exact domain of this package.
"""

from __future__ import annotations

from collections import Counter

from backend.app.services.pac_allocator.evaluation.bounds import decision_upper_bounds, expected_decision_rows, validated_baseline_quanta
from backend.app.services.pac_allocator.evaluation.candidates import candidate_contract_conflicts
from backend.app.services.pac_allocator.evaluation.economics import EconomicState, evaluate_economic_state
from backend.app.services.pac_allocator.evaluation.errors import ExactPolicyContractError, ExactReplayRejectedError
from backend.app.services.pac_allocator.evaluation.facts import constraint_facts, objective_value_map
from backend.app.services.pac_allocator.evaluation.keys import candidate_quanta
from backend.app.services.pac_allocator.evaluation.policy import baseline_state_for_purpose, build_decision_accesses, canonical_tie_breaks, default_exact_view_id, sell_gate_refs, validate_invest_only_baseline, validate_policy_purpose
from backend.app.services.pac_allocator.evaluation.references import build_constraint_refs, build_objective_refs
from backend.app.services.pac_allocator.evaluation.scenario import ScenarioIndex, build_scenario_index, exact_scenario_fingerprint, to_valuation
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    CandidateDecision,
    Checkpoint,
    DecisionAccess,
    ExactConflict,
    ExactConstraintEvaluation,
    ExactEvaluation,
    ExactObjectiveEvaluation,
    ExactPlannerScenario,
    ExactPolicyPurpose,
    ExactPolicyView,
    ExactRoundingTopUp,
    check_budget,
)
from backend.app.services.pac_allocator.numeric import (
    ExactRatio,
)

_EXACT_ZERO = ExactRatio(0)


def _require_feasible_invest_only_baseline(
    scenario: ExactPlannerScenario,
    *,
    purpose: ExactPolicyPurpose,
    baseline: CandidateActionVector | None,
    checkpoint: Checkpoint | None,
) -> None:
    if purpose != "sell_extension":
        return
    if baseline is None:
        raise ExactPolicyContractError("SELL extension requires an invest-only baseline candidate")
    baseline_view = build_exact_policy_view(
        scenario,
        purpose="invest_only_baseline",
        view_id=baseline.view_id,
        checkpoint=checkpoint,
    )
    evaluation = evaluate_exact_candidate(
        scenario,
        baseline_view,
        baseline,
        checkpoint=checkpoint,
    )
    if not evaluation.feasible:
        codes = ", ".join(evaluation.conflict_codes)
        raise ExactPolicyContractError("SELL extension baseline is not exact-feasible" + (f": {codes}" if codes else ""))


def build_exact_policy_view(
    scenario: ExactPlannerScenario,
    *,
    purpose: ExactPolicyPurpose = "primary",
    baseline: CandidateActionVector | None = None,
    view_id: str | None = None,
    checkpoint: Checkpoint | None = None,
) -> ExactPolicyView:
    """Build the canonical solver-neutral exact view for one policy phase.

    ``invest_and_sell`` is deliberately two-stage: callers first request
    ``invest_only_baseline`` and then pass that complete candidate to
    ``sell_extension``. ``deployment`` freezes all primary funding, FX and
    SELL decisions and exposes BUY decisions as additive-only; its caller
    supplies the already exact-verified primary candidate.
    """
    check_budget(checkpoint)
    index = build_scenario_index(scenario)
    validate_policy_purpose(scenario, purpose, baseline)
    rows = expected_decision_rows(scenario, index, checkpoint)
    expected_ids = tuple(item[0] for item in rows)
    upper_bounds = decision_upper_bounds(
        scenario,
        index,
        checkpoint,
    )
    baseline_quanta = validated_baseline_quanta(
        baseline=baseline,
        expected_ids=expected_ids,
        upper_bounds=upper_bounds,
        required=purpose in {"sell_extension", "deployment"},
    )
    _require_feasible_invest_only_baseline(
        scenario,
        purpose=purpose,
        baseline=baseline,
        checkpoint=checkpoint,
    )
    validate_invest_only_baseline(
        purpose=purpose,
        rows=rows,
        baseline_quanta=baseline_quanta,
    )
    baseline_state = baseline_state_for_purpose(
        scenario=scenario,
        index=index,
        purpose=purpose,
        baseline_quanta=baseline_quanta,
        checkpoint=checkpoint,
    )
    decision_tuple = build_decision_accesses(
        scenario=scenario,
        purpose=purpose,
        rows=rows,
        upper_bounds=upper_bounds,
        baseline_quanta=baseline_quanta,
        baseline_state=baseline_state,
        checkpoint=checkpoint,
    )
    objectives = build_objective_refs(scenario, purpose)
    sell_gates, proof_requirements = sell_gate_refs(
        purpose=purpose,
        decisions=decision_tuple,
    )
    fingerprint = exact_scenario_fingerprint(scenario)
    result = ExactPolicyView(
        view_id=(
            view_id
            if view_id is not None
            else default_exact_view_id(
                scenario=scenario,
                purpose=purpose,
                baseline_quanta=baseline_quanta,
            )
        ),
        scenario_fingerprint=fingerprint,
        product=scenario.product,
        policy=scenario.policy,
        purpose=purpose,
        phase="exact",
        decisions=decision_tuple,
        constraints=build_constraint_refs(
            scenario,
            index,
            purpose,
            checkpoint,
        ),
        objectives=objectives,
        tie_breaks=canonical_tie_breaks(
            scenario=scenario,
            index=index,
            checkpoint=checkpoint,
        ),
        sell_gates=sell_gates,
        proof_requirements=proof_requirements,
    )
    check_budget(checkpoint)
    return result


def _validated_policy_decisions(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    view: ExactPolicyView,
    checkpoint: Checkpoint | None,
) -> tuple[tuple[DecisionAccess, ...], EconomicState | None]:
    expected_rows = expected_decision_rows(scenario, index, checkpoint)
    expected_ids = tuple(item[0] for item in expected_rows)
    if tuple(item.decision_id for item in view.decisions) != expected_ids:
        raise ExactPolicyContractError("policy view must expose every scenario decision exactly once")
    upper_bounds = decision_upper_bounds(
        scenario,
        index,
        checkpoint,
    )
    baseline_quanta = {item.decision_id: item.baseline_quanta for item in view.decisions}
    if any(value < 0 or value > upper_bounds[decision_id] for decision_id, value in baseline_quanta.items()):
        raise ExactPolicyContractError("policy view baseline lies outside the canonical finite domain")
    validate_invest_only_baseline(
        purpose=view.purpose,
        rows=expected_rows,
        baseline_quanta=baseline_quanta,
    )
    if view.purpose == "sell_extension":
        embedded_baseline = CandidateActionVector(
            view_id=f"{view.view_id}:embedded-invest-only",
            candidate_id=f"{view.view_id}:embedded-invest-only",
            decisions=tuple(
                CandidateDecision(
                    decision_id=decision_id,
                    quanta=baseline_quanta[decision_id],
                )
                for decision_id in expected_ids
            ),
        )
        _require_feasible_invest_only_baseline(
            scenario,
            purpose=view.purpose,
            baseline=embedded_baseline,
            checkpoint=checkpoint,
        )
    baseline_state = baseline_state_for_purpose(
        scenario=scenario,
        index=index,
        purpose=view.purpose,
        baseline_quanta=baseline_quanta,
        checkpoint=checkpoint,
    )
    expected_decisions = build_decision_accesses(
        scenario=scenario,
        purpose=view.purpose,
        rows=expected_rows,
        upper_bounds=upper_bounds,
        baseline_quanta=baseline_quanta,
        baseline_state=baseline_state,
        checkpoint=checkpoint,
    )
    if view.decisions != expected_decisions:
        raise ExactPolicyContractError("policy view decision access differs from the canonical phase")
    return expected_decisions, baseline_state


def _validate_policy_view(
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    view: ExactPolicyView,
    checkpoint: Checkpoint | None,
) -> tuple[ExactPolicyPurpose, EconomicState | None]:
    if view.product != scenario.product or view.policy != scenario.policy:
        raise ExactPolicyContractError("policy view product/policy does not match the scenario")
    if view.phase != "exact":
        raise ExactPolicyContractError("exact evaluator requires an exact-phase policy view")
    validate_policy_purpose(scenario, view.purpose, None)
    if view.scenario_fingerprint != exact_scenario_fingerprint(scenario):
        raise ExactPolicyContractError("policy view scenario fingerprint does not match")
    expected_decisions, baseline_state = _validated_policy_decisions(
        scenario,
        index,
        view,
        checkpoint,
    )
    expected_constraints = build_constraint_refs(
        scenario,
        index,
        view.purpose,
        checkpoint,
    )
    if view.constraints != expected_constraints:
        raise ExactPolicyContractError("policy view constraint refs do not match the exact catalogue")
    expected_objectives = build_objective_refs(
        scenario,
        view.purpose,
    )
    if view.objectives != expected_objectives:
        raise ExactPolicyContractError("policy view objective refs do not match its policy phase")
    if view.tie_breaks != canonical_tie_breaks(
        scenario=scenario,
        index=index,
        checkpoint=checkpoint,
    ):
        raise ExactPolicyContractError("policy view tie break differs from the canonical vector")
    expected_gates, expected_requirements = sell_gate_refs(
        purpose=view.purpose,
        decisions=expected_decisions,
    )
    if view.sell_gates != expected_gates or view.proof_requirements != expected_requirements:
        raise ExactPolicyContractError("policy view SELL proof metadata differs from the canonical phase")
    return view.purpose, baseline_state


def evaluate_exact_candidate(
    scenario: ExactPlannerScenario,
    view: ExactPolicyView,
    candidate: CandidateActionVector,
    *,
    checkpoint: Checkpoint | None = None,
) -> ExactEvaluation:
    """Replay one complete discrete candidate with exact native accounting."""
    check_budget(checkpoint)
    index = build_scenario_index(scenario)
    _purpose, baseline_state = _validate_policy_view(
        scenario,
        index,
        view,
        checkpoint,
    )
    contract_conflicts = candidate_contract_conflicts(
        view=view,
        candidate=candidate,
        checkpoint=checkpoint,
    )
    if contract_conflicts:
        conflict_codes = tuple(sorted({item.code for item in contract_conflicts}))
        return ExactEvaluation(
            view_id=view.view_id,
            candidate_id=candidate.candidate_id,
            feasible=False,
            constraints=(),
            objectives=(),
            conflict_codes=conflict_codes,
            candidate_valid=False,
            conflicts=contract_conflicts,
        )

    quanta = candidate_quanta(candidate)
    state = evaluate_economic_state(
        scenario,
        index,
        quanta,
        checkpoint,
    )
    facts = constraint_facts(
        scenario=scenario,
        index=index,
        view=view,
        quanta=quanta,
        state=state,
        baseline_state=baseline_state,
        checkpoint=checkpoint,
    )
    constraints = []
    conflicts = []
    for ref in view.constraints:
        check_budget(checkpoint)
        fact = facts.get(ref.ref_id)
        if fact is None:
            raise ExactPolicyContractError(f"exact evaluator has no predicate for {ref.ref_id}")
        constraints.append(
            ExactConstraintEvaluation(
                ref_id=ref.ref_id,
                satisfied=fact.satisfied,
                value=fact.value,
                lower_bound=fact.lower_bound,
                upper_bound=fact.upper_bound,
            )
        )
        if not fact.satisfied:
            conflicts.append(
                ExactConflict(
                    code=ref.code,
                    entity_refs=ref.entity_refs,
                )
            )

    objective_values = objective_value_map(
        scenario=scenario,
        index=index,
        view=view,
        quanta=quanta,
        state=state,
        baseline_state=baseline_state,
        checkpoint=checkpoint,
    )
    objectives = tuple(
        ExactObjectiveEvaluation(
            ref_id=ref.ref_id,
            value=objective_values[ref.code],
        )
        for ref in view.objectives
    )
    conflicts_tuple = tuple(
        sorted(
            set(conflicts),
            key=lambda item: (
                item.code,
                tuple((entity.kind, entity.entity_id) for entity in item.entity_refs),
            ),
        )
    )
    conflict_codes = tuple(sorted({item.code for item in conflicts_tuple}))
    canonical_tie_decision_ids = view.tie_breaks[0].decision_ids
    result = ExactEvaluation(
        view_id=view.view_id,
        candidate_id=candidate.candidate_id,
        feasible=not conflicts_tuple,
        constraints=tuple(sorted(constraints, key=lambda item: item.ref_id)),
        objectives=objectives,
        conflict_codes=conflict_codes,
        candidate_valid=True,
        conflicts=conflicts_tuple,
        postings=state.postings,
        funding_transfers=state.funding_transfers,
        funding_sources=state.funding_sources,
        fx=state.fx,
        orders=state.orders,
        ledgers=state.ledgers,
        holdings=state.holdings,
        assets=state.assets,
        accounting=state.accounting,
        costs=state.costs,
        canonical_tie_decision_ids=canonical_tie_decision_ids,
        canonical_tie_quanta=tuple(quanta[decision_id] for decision_id in canonical_tie_decision_ids),
    )
    check_budget(checkpoint)
    return result


# The rules a pure rounding deficit breaks: the pool's own cash rule, the FX
# source cash rule (the same balance, seen from its FX debit), the global
# no-leverage rule, and the rounding bound. A top-up repairs all four. Every
# posting rounds against the plan and SCIP models the same rule, so no natural
# plan reaches a top-up any more: it stays as a safety net.
_ROUNDING_DEFICIT_CODES = frozenset(
    {
        "FX_SOURCE_CASH",
        "NO_SHORT_OR_LEVERAGE",
        "ROUNDING_BOUND",
        "SPENDABLE_CASH_NONNEGATIVE",
    }
)


def _require_rounding_only_rejection(evaluation: ExactEvaluation) -> frozenset[str]:
    """Return the replay's conflict codes once they can only be cash a rounding left short."""
    if not evaluation.candidate_valid or evaluation.accounting is None:
        raise ExactReplayRejectedError(f"the exact replay rejected a candidate outside the policy contract: {', '.join(evaluation.conflict_codes)}")
    codes = frozenset(evaluation.conflict_codes)
    if "SPENDABLE_CASH_NONNEGATIVE" not in codes or not codes <= _ROUNDING_DEFICIT_CODES:
        raise ExactReplayRejectedError(f"the exact replay rejected rules no rounding explains: {', '.join(evaluation.conflict_codes)}")
    if any(row.final_quantity < _EXACT_ZERO for row in evaluation.holdings):
        raise ExactReplayRejectedError("the exact replay rejected a negative final holding")
    return codes


def rounding_top_ups(
    scenario: ExactPlannerScenario,
    evaluation: ExactEvaluation,
) -> tuple[ExactRoundingTopUp, ...]:
    """Classify an exact replay: the cash each pool lacks to rounding, or a rejection.

    The replay stays authoritative. A feasible replay needs nothing. A replay
    whose only violation is negative final spendable cash, each pool short by
    ``D <= N x minor unit`` (``N`` = the pool's postings that carry a quantum:
    the buy debit of every order, a nonzero fee, the FX credit), is a plan the
    user can execute by adding ``D`` to each such pool: one top-up per negative
    pool, in ledger order. A failed ``ROUNDING_BOUND`` is accepted only as the
    top-ups repair it: the adjustment within the bound, and the shortfall within
    the bound once the top-ups are reachable cash. Anything else raises
    ``ExactReplayRejectedError``; the messages name rules and pools, never amounts.
    """
    if evaluation.feasible:
        return ()
    codes = _require_rounding_only_rejection(evaluation)
    index = build_scenario_index(scenario)
    rounded_postings = Counter((posting.broker_id, posting.currency) for posting in evaluation.postings if posting.quantum is not None)
    top_ups = []
    for ledger in evaluation.ledgers:
        if ledger.final_spendable >= _EXACT_ZERO:
            continue
        pool = (ledger.broker_id, ledger.currency)
        deficit = -ledger.final_spendable
        count = rounded_postings[pool]
        if count == 0 or deficit > count * index.currency_quantum[ledger.currency]:
            raise ExactReplayRejectedError(f"the exact replay left {ledger.broker_id}/{ledger.currency} short beyond its rounded postings")
        top_ups.append(
            ExactRoundingTopUp(
                broker_id=ledger.broker_id,
                currency=ledger.currency,
                amount=deficit,
                rounded_postings=count,
                valuation_amount=to_valuation(index, deficit, ledger.currency),
            )
        )
    if not top_ups:
        raise ExactReplayRejectedError("the exact replay rejected spendable cash without a negative pool")
    if "ROUNDING_BOUND" in codes:
        accounting = evaluation.accounting
        topped_up = sum((item.valuation_amount for item in top_ups), _EXACT_ZERO)
        if abs(accounting.rounding_adjustment) > accounting.rounding_bound or accounting.shortfall + topped_up < -accounting.rounding_bound:
            raise ExactReplayRejectedError("the exact replay rejected a rounding bound the top-ups do not repair")
    return tuple(top_ups)
