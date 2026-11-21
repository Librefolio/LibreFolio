"""Building blocks of an exact-phase policy view: purpose checks, baseline state, decision access per purpose and canonical tie breaks."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256

from backend.app.services.pac_allocator.evaluation.bounds import transfer_decision_id
from backend.app.services.pac_allocator.evaluation.economics import EconomicState, evaluate_economic_state
from backend.app.services.pac_allocator.evaluation.errors import ExactPolicyContractError
from backend.app.services.pac_allocator.evaluation.keys import exact_decision_id
from backend.app.services.pac_allocator.evaluation.reachability import fx_decision_specs
from backend.app.services.pac_allocator.evaluation.scenario import ScenarioIndex
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    Checkpoint,
    DecisionAccess,
    DecisionFamily,
    DecisionMode,
    EntityRef,
    ExactPlannerScenario,
    ExactPolicyPurpose,
    ExactUnit,
    TieBreakRef,
    check_budget,
)
from backend.app.services.pac_allocator.numeric import (
    ExactRatio,
)

_EXACT_ZERO = ExactRatio(0)


def validate_policy_purpose(
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
    baseline: CandidateActionVector | None,
) -> None:
    if purpose not in {"primary", "deployment"}:
        raise ExactPolicyContractError(f"unknown exact policy purpose: {purpose}")
    if purpose == "primary" and baseline is not None:
        raise ExactPolicyContractError(f"{purpose} cannot receive a baseline candidate")


def validate_primary_baseline(
    *,
    purpose: ExactPolicyPurpose,
    baseline_quanta: Mapping[str, int],
) -> None:
    """``primary`` starts from the zero action vector; only ``deployment`` has a baseline."""
    if purpose == "primary" and any(baseline_quanta.values()):
        raise ExactPolicyContractError(f"{purpose} must start from the zero action vector")


def baseline_state_for_purpose(
    *,
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    purpose: ExactPolicyPurpose,
    baseline_quanta: Mapping[str, int],
    checkpoint: Checkpoint | None,
) -> EconomicState | None:
    if purpose != "deployment":
        return None
    return evaluate_economic_state(
        scenario,
        index,
        baseline_quanta,
        checkpoint,
    )


def _decision_mode_for_purpose(
    *,
    purpose: ExactPolicyPurpose,
    family: DecisionFamily,
) -> DecisionMode:
    """``primary``: every decision is open but the sells, ``disabled`` until C1 (project 67) opens them. ``deployment``: the
    buys grow from the verified primary candidate, everything else is frozen at it."""
    if purpose == "primary":
        return "disabled" if family == "sell_quantum" else "mutable"
    return "additive_only" if family == "buy_quantum" else "frozen_exact"


def _decision_access(
    *,
    decision_id: str,
    family: DecisionFamily,
    entity_refs: tuple[EntityRef, ...],
    mode: DecisionMode,
    upper_bound: int,
    baseline_value: int,
) -> DecisionAccess:
    if mode == "disabled":
        return DecisionAccess(
            decision_id=decision_id,
            family=family,
            mode=mode,
            entity_refs=entity_refs,
            lower_quanta=0,
            upper_quanta=0,
            baseline_quanta=0,
            frozen_quanta=None,
        )
    lower = baseline_value if mode == "additive_only" else 0
    frozen = baseline_value if mode == "frozen_exact" else None
    return DecisionAccess(
        decision_id=decision_id,
        family=family,
        mode=mode,
        entity_refs=entity_refs,
        lower_quanta=lower,
        upper_quanta=upper_bound,
        baseline_quanta=baseline_value,
        frozen_quanta=frozen,
    )


def build_decision_accesses(
    *,
    purpose: ExactPolicyPurpose,
    rows: tuple[
        tuple[str, DecisionFamily, tuple[EntityRef, ...]],
        ...,
    ],
    upper_bounds: Mapping[str, int],
    baseline_quanta: Mapping[str, int],
    checkpoint: Checkpoint | None,
) -> tuple[DecisionAccess, ...]:
    decisions = []
    for decision_id, family, entity_refs in rows:
        check_budget(checkpoint)
        decisions.append(
            _decision_access(
                decision_id=decision_id,
                family=family,
                entity_refs=entity_refs,
                mode=_decision_mode_for_purpose(purpose=purpose, family=family),
                upper_bound=upper_bounds[decision_id],
                baseline_value=baseline_quanta[decision_id],
            )
        )
    return tuple(sorted(decisions, key=lambda item: item.decision_id))


def _canonical_tie_decision_ids(
    *,
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> tuple[str, ...]:
    rows: list[tuple[tuple[str, ...], str]] = []
    for route in scenario.funding_routes:
        check_budget(checkpoint)
        decision_id = exact_decision_id("funding_transfer", route.route_id)
        rows.append(
            (
                (
                    "",
                    route.broker_id,
                    route.currency,
                    "funding",
                    "",
                    route.route_id,
                    decision_id,
                ),
                decision_id,
            )
        )
    for spec in fx_decision_specs(scenario, index, checkpoint):
        check_budget(checkpoint)
        rows.append((spec.tie_break, spec.decision_id))
    for lane in scenario.transfer_lanes:
        check_budget(checkpoint)
        decision_id = transfer_decision_id(lane)
        rows.append((("", lane.source_broker_id, lane.currency, "transfer", lane.destination_broker_id, "", decision_id), decision_id))
    for route in scenario.order_routes:
        check_budget(checkpoint)
        quote_currency = index.assets[route.asset_id].quote.price.currency
        family: DecisionFamily = "buy_quantum" if route.side == "buy" else "sell_quantum"
        decision_id = exact_decision_id(family, route.route_id)
        rows.append(
            (
                (
                    route.asset_id,
                    route.broker_id,
                    quote_currency,
                    route.side,
                    "",
                    route.route_id,
                    decision_id,
                ),
                decision_id,
            )
        )
    return tuple(decision_id for _, decision_id in sorted(rows))


def canonical_tie_breaks(
    *,
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    checkpoint: Checkpoint | None,
) -> tuple[TieBreakRef, ...]:
    return (
        TieBreakRef(
            ref_id="tie:canonical-decision-vector",
            code="canonical_key",
            ordinal=1,
            unit=ExactUnit(kind="canonical_key"),
            decision_ids=_canonical_tie_decision_ids(
                scenario=scenario,
                index=index,
                checkpoint=checkpoint,
            ),
        ),
    )


def default_exact_view_id(
    *,
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
    baseline_quanta: Mapping[str, int],
) -> str:
    prefix = f"exact:{scenario.snapshot.snapshot_id}:" f"{scenario.snapshot.draft_revision}:{purpose}"
    if purpose != "deployment":
        return prefix
    baseline_fingerprint = sha256(repr(tuple(sorted(baseline_quanta.items()))).encode("utf-8")).hexdigest()
    return f"{prefix}:{baseline_fingerprint}"
