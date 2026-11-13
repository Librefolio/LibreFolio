"""The scenario preview of both Tools (contract §11, decisioni-REB §11.2; B4 of project 67).

``preview_pac_allocation`` and ``preview_rebalancing`` read the request of ``plan`` with the engine's own normalizer and
exact arithmetic, and return the numbers the screen shows before the calculation (N1: the frontend computes none of them):

* the total of the plan: ``F`` for the Rebalancer, the cash the PAC invests (its fixed reference);
* the Rebalancer's target entries today, value and weight on ``F``;
* the Rebalancer's table «maximum acceptable cost», from ``financial_math.acceptable_cost``, with the λ of the three levels
  (``FIDELITY_LEVEL_WEIGHTS``, the normalizer's table) and the «custom» fidelity both ways.

The numbers come from the replay of the do-nothing plan (``evaluation.evaluator.evaluate_do_nothing``), the same exact
reading the planner publishes in a scenario basis. **No optimizer**: this module never imports the compiler, the solver or
SCIP, so it answers in milliseconds and stays importable where SCIP is not. A request that cannot be counted answers like
``plan`` does, with the normalizer's issues.
"""

from __future__ import annotations

from decimal import Decimal

from backend.app.schemas.pac_allocator.exact import ExactMoney
from backend.app.schemas.pac_allocator.issues import PlannerIssue
from backend.app.schemas.pac_allocator.preview import (
    AcceptableCostRow,
    AcceptableCostTable,
    CustomFidelityPreview,
    FidelityLevelWeights,
    PacPreviewReadyResult,
    PlannerPreviewInvalidResult,
    PlannerPreviewNeedsInputResult,
    PlannerPreviewUnsupportedResult,
    PreviewAssetItem,
    PreviewCashItem,
    RebalancerPreviewReadyResult,
)
from backend.app.schemas.pac_allocator.request import PacPlannerRequest, RebalancerPlannerRequest
from backend.app.schemas.pac_allocator.results import PlannerResultSnapshot
from backend.app.services.financial_math.acceptable_cost import REFERENCE_ROW_INDEX, acceptable_cost_rows, lambda_from_reference_amount, max_acceptable_cost
from backend.app.services.pac_allocator.evaluation.economics import initial_cash_by_cell
from backend.app.services.pac_allocator.evaluation.evaluator import build_exact_policy_view, evaluate_do_nothing
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index, exact_scenario_fingerprint
from backend.app.services.pac_allocator.models import FIDELITY_LEVEL_WEIGHTS, Checkpoint, ExactEvaluation, ExactPlannerScenario, check_budget
from backend.app.services.pac_allocator.normalize import normalize_pac_plan, normalize_rebalancer_plan
from backend.app.services.pac_allocator.numeric import ExactRatio
from backend.app.services.pac_allocator.wire_numbers import ratio_to_exact_number, ratio_to_money

__all__ = ["preview_pac_allocation", "preview_rebalancing"]

_ZERO = ExactRatio(0)


def preview_pac_allocation(request: PacPlannerRequest, *, checkpoint: Checkpoint | None = None):
    """The PAC's preview: the cash the plan invests, or the issues that keep it from being counted."""
    check_budget(checkpoint)
    normalized = normalize_pac_plan(request)
    if not normalized.ready or normalized.normalized is None:
        return _failure(normalized.availability, request.snapshot.snapshot_id, list(normalized.issues))
    scenario = normalized.normalized
    accounting = _do_nothing(scenario, checkpoint).accounting
    return PacPreviewReadyResult(**_ready_fields(scenario, list(normalized.issues)), total=ratio_to_money(accounting.fixed_reference, scenario.valuation_currency))


def preview_rebalancing(request: RebalancerPlannerRequest, *, checkpoint: Checkpoint | None = None):
    """The Rebalancer's preview: ``F``, today's target entries on it, the table «maximum acceptable cost» and the «custom»
    fidelity both ways (the euros typed win over a custom λ in the request); or the issues that keep it from being counted."""
    check_budget(checkpoint)
    normalized = normalize_rebalancer_plan(request)
    if not normalized.ready or normalized.normalized is None:
        return _failure(normalized.availability, request.snapshot.snapshot_id, list(normalized.issues))
    scenario = normalized.normalized
    evaluation = _do_nothing(scenario, checkpoint)
    wealth = evaluation.accounting.initial_wealth
    currency = scenario.valuation_currency
    rows = acceptable_cost_rows(wealth)
    custom_weight = _custom_weight(request, wealth, rows[REFERENCE_ROW_INDEX])
    table = AcceptableCostTable(
        level_weights=FidelityLevelWeights(**{level: ratio_to_exact_number(weight) for level, weight in FIDELITY_LEVEL_WEIGHTS.items()}),
        rows=[
            AcceptableCostRow(
                misplaced=ratio_to_money(misplaced, currency),
                reference=index == REFERENCE_ROW_INDEX,
                **{level: _cost(weight, misplaced, wealth, currency) for level, weight in FIDELITY_LEVEL_WEIGHTS.items()},
                custom=_cost(custom_weight, misplaced, wealth, currency) if custom_weight is not None else None,
            )
            for index, misplaced in enumerate(rows)
        ],
    )
    custom = None
    if custom_weight is not None:
        custom = CustomFidelityPreview(distance_weight=ratio_to_exact_number(custom_weight), reference_amount=_cost(custom_weight, rows[REFERENCE_ROW_INDEX], wealth, currency))
    return RebalancerPreviewReadyResult(**_ready_fields(scenario, list(normalized.issues)), total=ratio_to_money(wealth, currency), items=_items(scenario, evaluation), table=table, custom=custom)


def _do_nothing(scenario: ExactPlannerScenario, checkpoint: Checkpoint | None) -> ExactEvaluation:
    evaluation = evaluate_do_nothing(scenario, build_exact_policy_view(scenario, purpose="primary"), checkpoint=checkpoint)
    if evaluation.accounting is None:
        raise ValueError("the preview requires a do-nothing replay that produced accounting")
    return evaluation


def _custom_weight(request: RebalancerPlannerRequest, wealth: ExactRatio, reference: ExactRatio) -> ExactRatio | None:
    """The «custom» λ: from the euros typed on the reference row when the request has them, else the request's custom λ;
    none for a level or «Target first» (M33: it has no maximum)."""
    if request.custom_reference_amount is not None:
        return lambda_from_reference_amount(ExactRatio.from_decimal(Decimal(request.custom_reference_amount.amount)), wealth, reference)
    if request.target_fidelity.kind == "custom":
        return ExactRatio.from_decimal(Decimal(request.target_fidelity.lambda_))
    return None


def _cost(weight: ExactRatio, misplaced: ExactRatio, wealth: ExactRatio, currency: str) -> ExactMoney:
    return ratio_to_money(max_acceptable_cost(weight, misplaced, wealth), currency)


def _items(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> list:
    """Every target entry today: the Assets' current values and the cash entries' selected cash, each on ``F``."""
    wealth = evaluation.accounting.initial_wealth
    currency = scenario.valuation_currency
    before = initial_cash_by_cell(build_scenario_index(scenario), evaluation.ledgers)
    items: list = [PreviewAssetItem(kind="asset", asset_id=row.asset_id, value=ratio_to_money(row.current_value, currency), weight=ratio_to_exact_number(row.current_value / wealth)) for row in evaluation.assets]
    for entry in scenario.cash_entries:
        value = before.get((entry.broker_id, entry.currency), _ZERO)
        items.append(PreviewCashItem(kind="cash", broker_id=entry.broker_id, currency=entry.currency, value=ratio_to_money(value, currency), weight=ratio_to_exact_number(value / wealth)))
    return items


def _ready_fields(scenario: ExactPlannerScenario, issues: list[PlannerIssue]) -> dict:
    return {
        "operation": "preview",
        "result_state": "preview_ready",
        "availability": "ready",
        "snapshot": PlannerResultSnapshot(snapshot_id=scenario.snapshot.snapshot_id, request_fingerprint=exact_scenario_fingerprint(scenario)),
        "valuation_currency": scenario.valuation_currency,
        "issues": issues,
    }


def _failure(availability: str, snapshot_id: str, issues: list[PlannerIssue]):
    """The preview's failure result, like ``plan``'s: no exact scenario, so no fingerprint."""
    snapshot = PlannerResultSnapshot(snapshot_id=snapshot_id, request_fingerprint="")
    if availability == "needs_input":
        return PlannerPreviewNeedsInputResult(operation="preview", result_state="preview_needs_input", availability="needs_input", snapshot=snapshot, issues=issues)
    if availability == "unsupported":
        return PlannerPreviewUnsupportedResult(operation="preview", result_state="preview_unsupported", availability="unsupported", snapshot=snapshot, issues=issues)
    return PlannerPreviewInvalidResult(operation="preview", result_state="preview_invalid", availability="invalid", snapshot=snapshot, issues=issues)
