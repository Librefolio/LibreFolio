"""Contract checks of a candidate against its policy view, before any replay: decision domain and decision access."""

from __future__ import annotations

from backend.app.services.pac_allocator.evaluation.keys import candidate_quanta, entity_refs
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    Checkpoint,
    DecisionAccess,
    ExactConflict,
    ExactPolicyView,
    check_budget,
)


def _conflict(
    code: str,
    *refs: tuple[str, str],
) -> ExactConflict:
    return ExactConflict(code=code, entity_refs=entity_refs(*refs))


def _decision_access_conflicts(
    access: DecisionAccess,
    value: int,
) -> tuple[ExactConflict, ...]:
    ref = ("decision", access.decision_id)
    conflicts = []
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return (_conflict("CANDIDATE_DECISION_OFF_GRID", ref),)
    if not access.lower_quanta <= value <= access.upper_quanta:
        conflicts.append(_conflict("CANDIDATE_DECISION_OUT_OF_BOUNDS", ref))
    if access.mode == "disabled" and value != 0:
        conflicts.append(_conflict("CANDIDATE_DECISION_DISABLED", ref))
    if access.mode == "frozen_exact" and value != access.frozen_quanta:
        conflicts.append(_conflict("CANDIDATE_DECISION_NOT_FROZEN", ref))
    if access.mode == "additive_only" and value < access.baseline_quanta:
        conflicts.append(_conflict("CANDIDATE_DECISION_NOT_ADDITIVE", ref))
    return tuple(conflicts)


def candidate_contract_conflicts(
    *,
    view: ExactPolicyView,
    candidate: CandidateActionVector,
    checkpoint: Checkpoint | None,
) -> tuple[ExactConflict, ...]:
    conflicts = []
    if candidate.view_id != view.view_id:
        conflicts.append(
            _conflict(
                "CANDIDATE_VIEW_MISMATCH",
                ("policy_view", view.view_id),
                ("candidate", candidate.candidate_id),
            )
        )
    candidate_ids = tuple(item.decision_id for item in candidate.decisions)
    if len(candidate_ids) != len(set(candidate_ids)):
        conflicts.append(
            _conflict(
                "CANDIDATE_DECISION_DUPLICATE",
                ("candidate", candidate.candidate_id),
            )
        )
    candidate_values = candidate_quanta(candidate)
    expected_ids = {item.decision_id for item in view.decisions}
    actual_ids = set(candidate_values)
    for decision_id in sorted(expected_ids - actual_ids):
        conflicts.append(
            _conflict(
                "CANDIDATE_DECISION_MISSING",
                ("decision", decision_id),
            )
        )
    for decision_id in sorted(actual_ids - expected_ids):
        conflicts.append(
            _conflict(
                "CANDIDATE_DECISION_EXTRA",
                ("decision", decision_id),
            )
        )
    for access in view.decisions:
        check_budget(checkpoint)
        value = candidate_values.get(access.decision_id)
        if value is None:
            continue
        conflicts.extend(_decision_access_conflicts(access, value))
    return tuple(
        sorted(
            set(conflicts),
            key=lambda item: (
                item.code,
                tuple((ref.kind, ref.entity_id) for ref in item.entity_refs),
            ),
        )
    )
