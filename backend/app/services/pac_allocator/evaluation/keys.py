"""Stable identifiers and quanta of the exact evaluator: decision ids, FX pair, source, FX-debit and asset-broker keys, entity references and whole-quantum checks."""

from __future__ import annotations

from backend.app.services.pac_allocator.evaluation.errors import ExactPolicyContractError
from backend.app.services.pac_allocator.models import (
    CandidateActionVector,
    DecisionFamily,
    EntityRef,
)
from backend.app.services.pac_allocator.numeric import (
    ExactRatio,
)

_EXACT_ZERO = ExactRatio(0)

_DECISION_PREFIX: dict[DecisionFamily, str] = {
    "funding_transfer": "funding",
    "fx_debit": "fx",
    "buy_quantum": "buy",
    "sell_quantum": "sell",
}


def exact_decision_id(family: DecisionFamily, entity_id: str) -> str:
    """Return the stable W1 decision identifier shared by views and candidates."""
    if family not in _DECISION_PREFIX:
        raise ExactPolicyContractError(f"unknown decision family: {family}")
    if not entity_id:
        raise ExactPolicyContractError("decision entity ID must not be empty")
    return f"{_DECISION_PREFIX[family]}:{entity_id}"


def fx_pair_key(first: str, second: str) -> str:
    return "/".join(sorted((first, second)))


def source_key(kind: str, source_id: str) -> tuple[str, str]:
    return kind, source_id


def fx_debit_key(route_id: str, currency: str) -> str:
    return f"{route_id}:{currency}"


def asset_broker_key(asset_id: str, broker_id: str) -> str:
    """Collision-free composite key: both components are arbitrary-length
    free-form identifiers that may themselves contain ``:`` or ``/``, so a
    plain ``f"{asset_id}:{broker_id}"`` join is ambiguous (e.g. ``("a", "b:c")``
    vs ``("a:b", "c")``). Length-prefixing each component removes the
    ambiguity regardless of its contents.
    """
    return f"{len(asset_id)}:{asset_id}{len(broker_id)}:{broker_id}"


def floor_units(value: ExactRatio, quantum: ExactRatio) -> int:
    if value < _EXACT_ZERO or quantum <= _EXACT_ZERO:
        raise ExactPolicyContractError("finite decision bounds require nonnegative value and positive quantum")
    ratio = value / quantum
    return ratio.numerator // ratio.denominator


def is_quantum_multiple(value: ExactRatio, quantum: ExactRatio) -> bool:
    if quantum <= _EXACT_ZERO:
        return False
    return (value / quantum).denominator == 1


def entity_refs(*items: tuple[str, str]) -> tuple[EntityRef, ...]:
    return tuple(EntityRef(kind=kind, entity_id=entity_id) for kind, entity_id in sorted(items))


def candidate_quanta(
    candidate: CandidateActionVector,
) -> dict[str, int]:
    return {item.decision_id: item.quanta for item in candidate.decisions}
