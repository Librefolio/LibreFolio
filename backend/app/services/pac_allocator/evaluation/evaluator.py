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
2026-09-21 (`a538ee94d` and its follow-up): it was a Decimal prototype for
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
from backend.app.services.pac_allocator.evaluation.limits import plan_reference, resolve_scenario_limits
from backend.app.services.pac_allocator.evaluation.policy import baseline_state_for_purpose, build_decision_accesses, canonical_tie_breaks, default_exact_view_id, validate_policy_purpose, validate_primary_baseline
from backend.app.services.pac_allocator.evaluation.references import build_constraint_refs, build_objective_refs
from backend.app.services.pac_allocator.evaluation.scenario import ScenarioIndex, build_scenario_index, exact_scenario_fingerprint, to_valuation
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    CandidateDecision,
    Checkpoint,
    DecisionAccess,
    ExactCashLimitOvershoot,
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
from backend.app.services.pac_allocator.posting_reserve import RESERVED_FAMILIES, posting_reserves

_EXACT_ZERO = ExactRatio(0)


def build_exact_policy_view(
    scenario: ExactPlannerScenario,
    *,
    purpose: ExactPolicyPurpose = "primary",
    baseline: CandidateActionVector | None = None,
    view_id: str | None = None,
    checkpoint: Checkpoint | None = None,
) -> ExactPolicyView:
    """Build the canonical solver-neutral exact view for one purpose.

    ``primary`` serves every policy and starts from the zero vector; its sells stay disabled until the sale lot (C1 of
    project 67) opens them. ``deployment`` freezes all primary funding, FX, transfer and SELL decisions and exposes BUY
    decisions as additive-only; its caller supplies the already exact-verified primary candidate.
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
        required=purpose == "deployment",
    )
    validate_primary_baseline(purpose=purpose, baseline_quanta=baseline_quanta)
    decision_tuple = build_decision_accesses(
        purpose=purpose,
        rows=rows,
        upper_bounds=upper_bounds,
        baseline_quanta=baseline_quanta,
        checkpoint=checkpoint,
    )
    objectives = build_objective_refs(scenario, purpose)
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
    validate_primary_baseline(purpose=view.purpose, baseline_quanta=baseline_quanta)
    baseline_state = baseline_state_for_purpose(
        scenario=scenario,
        index=index,
        purpose=view.purpose,
        baseline_quanta=baseline_quanta,
        checkpoint=checkpoint,
    )
    expected_decisions = build_decision_accesses(
        purpose=view.purpose,
        rows=expected_rows,
        upper_bounds=upper_bounds,
        baseline_quanta=baseline_quanta,
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
        quanta=quanta,
        state=state,
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
        cash_targets=state.cash_targets,
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


_LIMIT_REF_PREFIX = "constraint:entry_value_within_limits:"


def cash_limit_overshoots(scenario: ExactPlannerScenario, evaluation: ExactEvaluation, top_ups: tuple[ExactRoundingTopUp, ...] = ()) -> tuple[ExactCashLimitOvershoot, ...]:
    """Classify the limits a plan of the wide model misses (lot ZB of project 67, specification §16.16).

    The wide model holds the cell's exact cash inside the limit, its reserves on the side that admits; the replay rounds
    the postings against the plan, so the posted cash can end beyond the limit by at most ``R``, the reserves of the
    cell's postings that happened (``posting_reserve``, one minor unit where a posting can round). Such a miss is a note
    the plan carries, in the order of the limits. A miss beyond ``R`` (SCIP's tolerance on a row with no margin), or an
    Asset limit missed, raises ``ExactReplayRejectedError``. The messages name rules and cells, never amounts.

    A limit is read on the cell's cash once its rounding ``top_ups`` are added (lot ZB-c, contract §6.2, specification
    §16.16 p. 3): a cell the top-up brings back inside its band carries the top-up alone, one line for one cent; one still
    outside keeps the note, with what is still missing. The allowance is unchanged.

    Only the wide model's plans reach it (the planner's path, and the cascade on that model): the prudent model's meet
    every limit to the cent.
    """
    if evaluation.accounting is None or "ENTRY_VALUE_WITHIN_LIMITS" not in evaluation.conflict_codes:
        return ()
    index = build_scenario_index(scenario)
    entries = {f"{_LIMIT_REF_PREFIX}{entry.key}": entry for entry in resolve_scenario_limits(scenario, plan_reference(scenario, evaluation.accounting)).by_entry}
    reserves = posting_reserves(scenario)
    kept: dict[tuple[str, str], list[ExactRatio]] = {}
    for posting in evaluation.postings:
        reserve = reserves.get(posting.posting_id, _EXACT_ZERO)
        if posting.family in RESERVED_FAMILIES and posting.exact_amount > _EXACT_ZERO and reserve > _EXACT_ZERO:
            kept.setdefault((posting.broker_id, posting.currency), []).append(reserve)
    added = {(top_up.broker_id, top_up.currency): top_up.valuation_amount for top_up in top_ups}
    overshoots = []
    for constraint in evaluation.constraints:
        entry = entries.get(constraint.ref_id)
        if entry is None or constraint.satisfied:
            continue
        if entry.kind != "cash":
            raise ExactReplayRejectedError("the exact replay rejected an Asset limit")
        value = constraint.value + added.get((entry.broker_id, entry.currency), _EXACT_ZERO)
        above = constraint.upper_bound is not None and value > constraint.upper_bound
        below = constraint.lower_bound is not None and value < constraint.lower_bound
        if not above and not below:
            continue  # the top-up brings the cell back inside its band
        miss = value - constraint.upper_bound if above else constraint.lower_bound - value
        cell_reserves = kept.get((entry.broker_id, entry.currency), [])
        allowance = sum(cell_reserves, _EXACT_ZERO)
        if miss <= _EXACT_ZERO or miss > to_valuation(index, allowance, entry.currency):
            raise ExactReplayRejectedError(f"the exact replay missed the cash limit of {entry.broker_id}/{entry.currency} beyond its postings' reserves")
        quantum = index.currency_quantum[entry.currency]
        units = miss / to_valuation(index, quantum, entry.currency)
        whole = units.numerator // units.denominator + (1 if units.numerator % units.denominator else 0)
        overshoots.append(ExactCashLimitOvershoot(broker_id=entry.broker_id, currency=entry.currency, side="maximum" if above else "minimum", amount=whole * quantum, reserved_postings=len(cell_reserves)))
    return tuple(overshoots)


def evaluate_do_nothing(scenario: ExactPlannerScenario, view: ExactPolicyView, *, checkpoint: Checkpoint | None = None) -> ExactEvaluation:
    """Evaluate the do-nothing plan: every decision at its frozen or baseline quanta.

    The planner needs it even when no plan is publishable, because every ready result still carries a scenario basis; the
    scenario preview (B4 of project 67) reads today's values and ``F`` from it, with no optimizer. A blind ``0`` is *not*
    always valid: a ``frozen_exact`` decision with a nonzero ``frozen_quanta``, or any decision whose ``lower_quanta``
    exceeds zero, would be rejected by the candidate contract; the decision's own frozen or baseline value is valid for any
    well-formed view, and for the all-mutable primary shape it is exactly zero anyway.
    """
    candidate = CandidateActionVector(
        view_id=view.view_id,
        candidate_id="plan:zero",
        decisions=tuple(CandidateDecision(decision_id=access.decision_id, quanta=access.frozen_quanta if access.mode == "frozen_exact" else access.baseline_quanta) for access in view.decisions),
    )
    return evaluate_exact_candidate(scenario, view, candidate, checkpoint=checkpoint)


def _require_rounding_only_rejection(evaluation: ExactEvaluation, tolerated: frozenset[str] = frozenset()) -> frozenset[str]:
    """Return the replay's conflict codes, less the ``tolerated`` ones, once they can only be cash a rounding left short."""
    if not evaluation.candidate_valid or evaluation.accounting is None:
        raise ExactReplayRejectedError(f"the exact replay rejected a candidate outside the policy contract: {', '.join(evaluation.conflict_codes)}")
    codes = frozenset(evaluation.conflict_codes) - tolerated
    if "SPENDABLE_CASH_NONNEGATIVE" not in codes or not codes <= _ROUNDING_DEFICIT_CODES:
        raise ExactReplayRejectedError(f"the exact replay rejected rules no rounding explains: {', '.join(evaluation.conflict_codes)}")
    if any(row.final_quantity < _EXACT_ZERO for row in evaluation.holdings):
        raise ExactReplayRejectedError("the exact replay rejected a negative final holding")
    return codes


def rounding_top_ups(
    scenario: ExactPlannerScenario,
    evaluation: ExactEvaluation,
    *,
    tolerated: frozenset[str] = frozenset(),
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

    ``tolerated`` rules are classified apart (``cash_limit_overshoots``, lots ZB and ZB-c, after these top-ups): they
    neither need nor refuse a top-up.
    """
    if evaluation.feasible:
        return ()
    if tolerated and evaluation.candidate_valid and evaluation.accounting is not None and not frozenset(evaluation.conflict_codes) - tolerated:
        return ()
    codes = _require_rounding_only_rejection(evaluation, tolerated)
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
