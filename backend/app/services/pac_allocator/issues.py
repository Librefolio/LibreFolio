"""Closed Planner v2 issue taxonomy and deterministic normalization precedence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, get_args

from backend.app.schemas.pac_allocator.base import PlannerIssueCode, PlannerMoneyInput
from backend.app.schemas.pac_allocator.issues import EntityIssuePath, FieldIssuePath, MoneyIssueParam, PlannerIssue, PlannerIssueEntityKind, PlannerIssueParam, PlannerIssuePath, PlannerIssueSection, SectionIssuePath

type IssueKind = Literal["missing", "invalid", "unsupported", "constraint", "proof", "info"]
type IssueSeverity = Literal["info", "warning", "error"]
type PlannerAvailability = Literal["ready", "needs_input", "invalid", "unsupported"]
type NormalizerIssueKind = Literal["missing", "invalid", "unsupported"]


@dataclass(frozen=True, slots=True)
class IssueDefinition:
    code: PlannerIssueCode
    kind: NormalizerIssueKind
    severity: Literal["error"]
    producer: Literal["w1_normalizer"]

    def __post_init__(self) -> None:
        if self.code not in get_args(PlannerIssueCode):
            raise ValueError(f"Unknown PlannerIssueCode: {self.code}")
        if self.kind not in {"missing", "invalid", "unsupported"}:
            raise ValueError(f"Unsupported W1 normalizer issue kind: {self.kind}")
        if self.severity != "error" or self.producer != "w1_normalizer":
            raise ValueError("W1 normalizer definitions must be controlling errors from w1_normalizer")


def _normalizer_definition(code: PlannerIssueCode, kind: NormalizerIssueKind) -> IssueDefinition:
    return IssueDefinition(code=code, kind=kind, severity="error", producer="w1_normalizer")


# Canonical public universe.  It intentionally carries no inferred
# kind/severity policy for codes that this normalizer does not produce.
CANONICAL_ISSUE_CODES: tuple[PlannerIssueCode, ...] = get_args(PlannerIssueCode)
# Lot SE of project 67 added allocation.solver_numerical_error (77 → 78), by the coordinator's decision of 16/11; lot ZB added
# allocation.cash_limit_exceeded_by_rounding (78 → 79), by the developer's decision of 17/11 (specification §16.16).
if len(CANONICAL_ISSUE_CODES) != 79 or len(set(CANONICAL_ISSUE_CODES)) != 79:
    raise RuntimeError("PlannerIssueCode must remain the frozen 79-value universe (A4 closed it at 77, step 4; lots SE and ZB added one each)")


# Explicit W1 producer map.  Adding `self.issue(code, ...)` without first
# defining that code here fails closed rather than inventing a universal
# default for source, evaluator, solver, proof, or publication issues.
W1_NORMALIZER_ISSUE_DEFINITIONS: dict[PlannerIssueCode, IssueDefinition] = {
    "allocation.bound_max_below_current": _normalizer_definition("allocation.bound_max_below_current", "invalid"),
    "allocation.bound_min_above_max": _normalizer_definition("allocation.bound_min_above_max", "invalid"),
    "allocation.bounds_min_sum_exceeds_reference": _normalizer_definition("allocation.bounds_min_sum_exceeds_reference", "invalid"),
    "allocation.broker_inactive": _normalizer_definition("allocation.broker_inactive", "unsupported"),
    "allocation.capacity_unsupported": _normalizer_definition("allocation.capacity_unsupported", "unsupported"),
    "allocation.cash_selection_invalid": _normalizer_definition("allocation.cash_selection_invalid", "invalid"),
    "allocation.coefficient_envelope_unsupported": _normalizer_definition("allocation.coefficient_envelope_unsupported", "unsupported"),
    "allocation.currency_mismatch": _normalizer_definition("allocation.currency_mismatch", "invalid"),
    "allocation.duplicate_id": _normalizer_definition("allocation.duplicate_id", "invalid"),
    "allocation.economic_share_out_of_range": _normalizer_definition("allocation.economic_share_out_of_range", "invalid"),
    "allocation.execution_margin_rate_out_of_range": _normalizer_definition("allocation.execution_margin_rate_out_of_range", "invalid"),
    "allocation.exposure_total_exceeds_one": _normalizer_definition("allocation.exposure_total_exceeds_one", "invalid"),
    "allocation.exposure_weight_out_of_range": _normalizer_definition("allocation.exposure_weight_out_of_range", "invalid"),
    "allocation.fee_floor_exceeds_cap": _normalizer_definition("allocation.fee_floor_exceeds_cap", "invalid"),
    "allocation.fee_rate_out_of_range": _normalizer_definition("allocation.fee_rate_out_of_range", "invalid"),
    "allocation.fee_schedule_missing": _normalizer_definition("allocation.fee_schedule_missing", "missing"),
    "allocation.funding_cap_negative": _normalizer_definition("allocation.funding_cap_negative", "invalid"),
    "allocation.fx_rate_inconsistent": _normalizer_definition("allocation.fx_rate_inconsistent", "invalid"),
    "allocation.fx_rate_missing": _normalizer_definition("allocation.fx_rate_missing", "missing"),
    "allocation.fx_spread_rate_out_of_range": _normalizer_definition("allocation.fx_spread_rate_out_of_range", "invalid"),
    "allocation.identity_fx_rate_not_allowed": _normalizer_definition("allocation.identity_fx_rate_not_allowed", "invalid"),
    "allocation.invalid_quote_basis": _normalizer_definition("allocation.invalid_quote_basis", "invalid"),
    "allocation.negative_cash_unsupported": _normalizer_definition("allocation.negative_cash_unsupported", "unsupported"),
    "allocation.negative_contribution": _normalizer_definition("allocation.negative_contribution", "invalid"),
    "allocation.negative_fee_amount": _normalizer_definition("allocation.negative_fee_amount", "invalid"),
    "allocation.negative_inventory_unsupported": _normalizer_definition("allocation.negative_inventory_unsupported", "unsupported"),
    "allocation.no_selected_funding": _normalizer_definition("allocation.no_selected_funding", "missing"),
    "allocation.nonpositive_fx_rate": _normalizer_definition("allocation.nonpositive_fx_rate", "invalid"),
    "allocation.nonpositive_order_amount_step": _normalizer_definition("allocation.nonpositive_order_amount_step", "invalid"),
    "allocation.nonpositive_price": _normalizer_definition("allocation.nonpositive_price", "invalid"),
    "allocation.nonpositive_quantity_step": _normalizer_definition("allocation.nonpositive_quantity_step", "invalid"),
    "allocation.order_amount_step_missing": _normalizer_definition("allocation.order_amount_step_missing", "missing"),
    "allocation.order_cap_nonpositive": _normalizer_definition("allocation.order_cap_nonpositive", "invalid"),
    "allocation.order_minimum_exceeds_cap": _normalizer_definition("allocation.order_minimum_exceeds_cap", "invalid"),
    "allocation.order_minimum_negative": _normalizer_definition("allocation.order_minimum_negative", "invalid"),
    "allocation.planning_quantity_negative": _normalizer_definition("allocation.planning_quantity_negative", "invalid"),
    "allocation.price_missing": _normalizer_definition("allocation.price_missing", "missing"),
    "allocation.provenance_not_found": _normalizer_definition("allocation.provenance_not_found", "invalid"),
    "allocation.quote_base_quantity_missing": _normalizer_definition("allocation.quote_base_quantity_missing", "missing"),
    "allocation.reference_not_found": _normalizer_definition("allocation.reference_not_found", "invalid"),
    "allocation.route_priority_negative": _normalizer_definition("allocation.route_priority_negative", "invalid"),
    "allocation.target_total_not_one": _normalizer_definition("allocation.target_total_not_one", "invalid"),
    "allocation.target_weight_missing": _normalizer_definition("allocation.target_weight_missing", "missing"),
    "allocation.target_weight_out_of_range": _normalizer_definition("allocation.target_weight_out_of_range", "invalid"),
    "allocation.wac_missing": _normalizer_definition("allocation.wac_missing", "missing"),
    "pac_allocator.cash_weight_unsupported": _normalizer_definition("pac_allocator.cash_weight_unsupported", "unsupported"),
    "portfolio_rebalancer.carried_loss_negative": _normalizer_definition("portfolio_rebalancer.carried_loss_negative", "invalid"),
    "portfolio_rebalancer.cost_basis_negative": _normalizer_definition("portfolio_rebalancer.cost_basis_negative", "invalid"),
    "portfolio_rebalancer.holdings_missing": _normalizer_definition("portfolio_rebalancer.holdings_missing", "missing"),
    "portfolio_rebalancer.nonpositive_current_portfolio": _normalizer_definition("portfolio_rebalancer.nonpositive_current_portfolio", "missing"),
    "portfolio_rebalancer.sell_fee_missing": _normalizer_definition("portfolio_rebalancer.sell_fee_missing", "missing"),
    "portfolio_rebalancer.tax_rate_missing": _normalizer_definition("portfolio_rebalancer.tax_rate_missing", "missing"),
    "portfolio_rebalancer.tax_rate_out_of_range": _normalizer_definition("portfolio_rebalancer.tax_rate_out_of_range", "invalid"),
    "portfolio_rebalancer.withholding_missing": _normalizer_definition("portfolio_rebalancer.withholding_missing", "missing"),
}

if any(code not in CANONICAL_ISSUE_CODES or definition.code != code for code, definition in W1_NORMALIZER_ISSUE_DEFINITIONS.items()):
    raise RuntimeError("W1 normalizer issue definitions must use canonical public codes")


def section_path(section: PlannerIssueSection) -> SectionIssuePath:
    return SectionIssuePath(kind="section", section=section)


def entity_path(section: PlannerIssueSection, entity_kind: PlannerIssueEntityKind, entity_id: str) -> EntityIssuePath:
    return EntityIssuePath(kind="entity", section=section, entity_kind=entity_kind, entity_id=entity_id)


def field_path(section: PlannerIssueSection, entity_kind: PlannerIssueEntityKind, entity_id: str, field: str) -> FieldIssuePath:
    return FieldIssuePath(kind="field", section=section, entity_kind=entity_kind, entity_id=entity_id, field=field)


def make_issue(
    definition: IssueDefinition,
    path: PlannerIssuePath,
    *,
    params: tuple[PlannerIssueParam, ...] = (),
) -> PlannerIssue:
    ordered_params = sorted(params, key=lambda param: param.name)
    return PlannerIssue(code=definition.code, severity=definition.severity, kind=definition.kind, path=path, message_key=definition.code, params=ordered_params)


def bounds_unsatisfiable_issue(entity_kind: Literal["asset", "cash"], entity_id: str) -> PlannerIssue:
    """``allocation.bounds_unsatisfiable`` for one entry that carries a limit (M20, decisioni §10.2).

    A ready result cannot carry an ``error``, so the problem is a ``warning`` of kind ``constraint``, its path on the entry; the
    interface gathers the listed entries into one banner.
    """
    return PlannerIssue(code="allocation.bounds_unsatisfiable", severity="warning", kind="constraint", path=entity_path("targets", entity_kind, entity_id), message_key="allocation.bounds_unsatisfiable", params=[])


def solver_numerical_error_issue() -> PlannerIssue:
    """``allocation.solver_numerical_error``: SCIP failed inside a stage after the search already held a plan (lot SE of
    project 67). The plan is published, not proven, and the run's stop reads ``time_limit``, the wire's only stop for an
    unfinished stage: this warning names the real cause, so the user does not read it as the clock and raise a budget
    that would not help. A ``warning`` of kind ``proof`` on the ``proof`` section; no parameter, nothing personal."""
    return PlannerIssue(code="allocation.solver_numerical_error", severity="warning", kind="proof", path=section_path("proof"), message_key="allocation.solver_numerical_error", params=[])


def normalizer_issue_definition(code: PlannerIssueCode) -> IssueDefinition:
    try:
        return W1_NORMALIZER_ISSUE_DEFINITIONS[code]
    except KeyError as error:
        raise KeyError(f"No explicit W1 normalizer IssueDefinition for {code}") from error


_SECTION_ORDER = {
    "input": 0,
    "assets": 1,
    "brokers": 2,
    "holdings": 3,
    "cash": 4,
    "contributions": 5,
    "funding": 6,
    "routing": 7,
    "fx": 8,
    "targets": 9,
    "policy": 10,
    "proof": 11,
    "liquidity": 12,
    "result": 13,
}
_KIND_ORDER = {"missing": 0, "invalid": 1, "unsupported": 2, "constraint": 3, "proof": 4, "info": 5}
_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}
_PATH_ORDER = {"section": 0, "entity": 1, "field": 2}


def _path_key(path: PlannerIssuePath) -> tuple[object, ...]:
    if isinstance(path, SectionIssuePath):
        return (_SECTION_ORDER[path.section], _PATH_ORDER[path.kind], "", "", "")
    if isinstance(path, EntityIssuePath):
        return (_SECTION_ORDER[path.section], _PATH_ORDER[path.kind], path.entity_kind, path.entity_id, "")
    return (_SECTION_ORDER[path.section], _PATH_ORDER[path.kind], path.entity_kind, path.entity_id, path.field)


def _param_key(param: PlannerIssueParam) -> tuple[object, ...]:
    return (param.name, param.kind, repr(param.model_dump(mode="python")))


def issue_sort_key(issue: PlannerIssue) -> tuple[object, ...]:
    return (*_path_key(issue.path), _SEVERITY_ORDER[issue.severity], _KIND_ORDER[issue.kind], issue.code, tuple(_param_key(param) for param in issue.params))


def canonicalize_issues(issues: list[PlannerIssue] | tuple[PlannerIssue, ...]) -> tuple[PlannerIssue, ...]:
    ordered = sorted(issues, key=issue_sort_key)
    unique: list[PlannerIssue] = []
    seen: set[str] = set()
    for issue in ordered:
        identity = issue.model_dump_json()
        if identity in seen:
            continue
        seen.add(identity)
        unique.append(issue)
    return tuple(unique)


def normalization_availability(issues: list[PlannerIssue] | tuple[PlannerIssue, ...]) -> PlannerAvailability:
    error_kinds = {issue.kind for issue in issues if issue.severity == "error"}
    if "missing" in error_kinds:
        return "needs_input"
    if "invalid" in error_kinds:
        return "invalid"
    if "unsupported" in error_kinds:
        return "unsupported"
    unexpected = error_kinds - {"constraint", "proof", "info"}
    if unexpected:
        raise ValueError(f"Unknown normalization issue kinds: {sorted(unexpected)!r}")
    if error_kinds & {"constraint", "proof"}:
        raise ValueError("Constraint/proof errors cannot determine input normalization availability")
    return "ready"


def cash_limit_exceeded_by_rounding_issue(broker_id: str, currency: str, exceeded_by: str) -> PlannerIssue:
    """``allocation.cash_limit_exceeded_by_rounding`` (lot ZB of project 67, specification §16.16): the prudent model held
    no plan, the wide one did, and its plan ends this cash cell beyond its limit by the rounding of its postings, at most
    the reserves of those that happened (one minor unit each). The plan is published, not proven, with this note:
    ``exceeded_by`` is the miss in the cell's own ``currency``, whole minor units (``PlannerFixedDecimal``). A ``warning``
    of kind ``constraint`` on the cell, like the rounding top-up's note."""
    return PlannerIssue(
        code="allocation.cash_limit_exceeded_by_rounding",
        severity="warning",
        kind="constraint",
        path=entity_path("targets", "cash", f"{broker_id}:{currency}"),
        message_key="allocation.cash_limit_exceeded_by_rounding",
        params=[MoneyIssueParam(kind="money", name="exceeded_by", value=PlannerMoneyInput(amount=exceeded_by, currency=currency))],
    )
