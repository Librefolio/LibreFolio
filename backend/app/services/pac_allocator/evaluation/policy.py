"""Building blocks of an exact-phase policy view: purpose checks, baseline state, decision access per phase, canonical tie breaks and SELL proof gates."""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256

from backend.app.services.pac_allocator.evaluation.economics import EconomicState, evaluate_economic_state
from backend.app.services.pac_allocator.evaluation.errors import ExactPolicyContractError
from backend.app.services.pac_allocator.evaluation.keys import exact_decision_id, fx_debit_key
from backend.app.services.pac_allocator.evaluation.reachability import buy_pool_currencies
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
    ProofRequirement,
    SellIrreducibilityGateRef,
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
    if purpose not in {
        "primary",
        "invest_only_baseline",
        "sell_extension",
        "deployment",
    }:
        raise ExactPolicyContractError(f"unknown exact policy purpose: {purpose}")
    if purpose == "primary" and scenario.policy == "invest_and_sell":
        raise ExactPolicyContractError("invest_and_sell requires invest_only_baseline then sell_extension")
    if purpose in {"invest_only_baseline", "sell_extension"} and scenario.policy != "invest_and_sell":
        raise ExactPolicyContractError(f"{purpose} requires an invest_and_sell scenario")
    if purpose in {"primary", "invest_only_baseline"} and baseline is not None:
        raise ExactPolicyContractError(f"{purpose} cannot receive a baseline candidate")


def validate_invest_only_baseline(
    *,
    purpose: ExactPolicyPurpose,
    rows: tuple[
        tuple[str, DecisionFamily, tuple[EntityRef, ...]],
        ...,
    ],
    baseline_quanta: Mapping[str, int],
) -> None:
    if purpose in {"primary", "invest_only_baseline"}:
        if any(baseline_quanta.values()):
            raise ExactPolicyContractError(f"{purpose} must start from the zero action vector")
        return
    if purpose != "sell_extension":
        return
    sell_baseline_ids = {decision_id for decision_id, family, _refs in rows if family == "sell_quantum"}
    if any(baseline_quanta[decision_id] != 0 for decision_id in sell_baseline_ids):
        raise ExactPolicyContractError("invest-only baseline cannot contain SELL decisions")


def baseline_state_for_purpose(
    *,
    scenario: ExactPlannerScenario,
    index: ScenarioIndex,
    purpose: ExactPolicyPurpose,
    baseline_quanta: Mapping[str, int],
    checkpoint: Checkpoint | None,
) -> EconomicState | None:
    if purpose not in {"sell_extension", "deployment"}:
        return None
    return evaluate_economic_state(
        scenario,
        index,
        baseline_quanta,
        checkpoint,
    )


def _sell_eligible_route_ids(
    *,
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
    baseline_state: EconomicState | None,
) -> set[str]:
    if purpose != "sell_extension" or baseline_state is None:
        return set()
    baseline_assets = {item.asset_id: item for item in baseline_state.assets}
    baseline_buy_assets = {order.asset_id for order in baseline_state.orders if order.side == "buy"}
    return {route.route_id for route in scenario.order_routes if route.side == "sell" and baseline_assets[route.asset_id].residual > _EXACT_ZERO and route.asset_id not in baseline_buy_assets}


def _decision_mode_for_purpose(
    *,
    purpose: ExactPolicyPurpose,
    family: DecisionFamily,
    route_id: str,
    sell_eligible: set[str],
) -> DecisionMode:
    if purpose in {"primary", "invest_only_baseline"}:
        return "disabled" if family == "sell_quantum" else "mutable"
    if purpose == "sell_extension":
        if family in {"funding_transfer", "fx_debit"}:
            return "frozen_exact"
        if family == "buy_quantum":
            return "additive_only"
        return "mutable" if route_id in sell_eligible else "disabled"
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
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
    rows: tuple[
        tuple[str, DecisionFamily, tuple[EntityRef, ...]],
        ...,
    ],
    upper_bounds: Mapping[str, int],
    baseline_quanta: Mapping[str, int],
    baseline_state: EconomicState | None,
    checkpoint: Checkpoint | None,
) -> tuple[DecisionAccess, ...]:
    sell_eligible = _sell_eligible_route_ids(
        scenario=scenario,
        purpose=purpose,
        baseline_state=baseline_state,
    )
    decisions = []
    for decision_id, family, entity_refs in rows:
        check_budget(checkpoint)
        route_id = decision_id.split(":", 1)[1]
        decisions.append(
            _decision_access(
                decision_id=decision_id,
                family=family,
                entity_refs=entity_refs,
                mode=_decision_mode_for_purpose(
                    purpose=purpose,
                    family=family,
                    route_id=route_id,
                    sell_eligible=sell_eligible,
                ),
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
    for route in scenario.order_routes:
        check_budget(checkpoint)
        if route.side != "buy":
            continue
        quote_currency = index.assets[route.asset_id].quote.price.currency
        for currency in buy_pool_currencies(
            scenario,
            index,
            broker_id=route.broker_id,
            quote_currency=quote_currency,
            checkpoint=checkpoint,
        ):
            decision_id = exact_decision_id("fx_debit", fx_debit_key(route.route_id, currency))
            rows.append(
                (
                    (
                        "",
                        route.broker_id,
                        currency,
                        "fx",
                        quote_currency,
                        route.route_id,
                        decision_id,
                    ),
                    decision_id,
                )
            )
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


def sell_gate_refs(
    *,
    purpose: ExactPolicyPurpose,
    decisions: tuple[DecisionAccess, ...],
) -> tuple[
    tuple[SellIrreducibilityGateRef, ...],
    tuple[ProofRequirement, ...],
]:
    if purpose != "sell_extension":
        return (), ()
    additive_buys = tuple(item.decision_id for item in decisions if item.family == "buy_quantum" and item.mode == "additive_only")
    reopened = tuple(item.decision_id for item in decisions if item.family in {"funding_transfer", "fx_debit"})
    gates = tuple(
        SellIrreducibilityGateRef(
            gate_id=f"sell-irreducibility:{item.decision_id}",
            sell_decision_id=item.decision_id,
            fixed_incremental_buy_decision_ids=additive_buys,
            reopened_decision_ids=reopened,
        )
        for item in decisions
        if (item.family == "sell_quantum" and item.mode != "disabled" and item.upper_quanta > 0)
    )
    requirements = (
        (
            ProofRequirement(
                requirement_id="proof:sell-irreducibility",
                code="portfolio_rebalancer.sell_irreducibility",
                allowed_sources=(
                    "deterministic_conflict",
                    "exhaustive_oracle",
                ),
            ),
        )
        if gates
        else ()
    )
    return gates, requirements


def default_exact_view_id(
    *,
    scenario: ExactPlannerScenario,
    purpose: ExactPolicyPurpose,
    baseline_quanta: Mapping[str, int],
) -> str:
    prefix = f"exact:{scenario.snapshot.snapshot_id}:" f"{scenario.snapshot.draft_revision}:{purpose}"
    if purpose not in {"sell_extension", "deployment"}:
        return prefix
    baseline_fingerprint = sha256(repr(tuple(sorted(baseline_quanta.items()))).encode("utf-8")).hexdigest()
    return f"{prefix}:{baseline_fingerprint}"
