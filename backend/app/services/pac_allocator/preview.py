"""The scenario preview of both Tools (contract §11, decisioni-REB §11.2; B4 of project 67).

``preview_pac_allocation`` and ``preview_rebalancing`` read the request of ``plan`` with the engine's own normalizer and
exact arithmetic, and return the numbers the screen shows before the calculation (N1: the frontend computes none of them):

* the total of the plan: ``F`` for the Rebalancer, the cash the PAC invests (its fixed reference);
* the Rebalancer's target entries today, value and weight on ``F``;
* the λ of the Rebalancer's three fidelity levels (``FIDELITY_LEVEL_WEIGHTS``, the normalizer's table). The page computes
  the table «maximum acceptable cost» from them and ``F`` (R1-F (b) of project 67): no number here depends on the request's
  target fidelity, so the page asks no preview when only the fidelity changes.

The numbers come from the replay of the do-nothing plan (``evaluation.evaluator.evaluate_do_nothing``), the same exact
reading the planner publishes in a scenario basis. **No optimizer**: this module never imports the compiler, the solver or
SCIP, so it answers in milliseconds and stays importable where SCIP is not. A request that cannot be counted answers like
``plan`` does, with the normalizer's issues. Limits that contradict each other or the portfolio (the normalizer's three
cross checks) do not stop it: they make the plan ``invalid``, while the preview counts and names them in ``limit_problems``.
"""

from __future__ import annotations

from backend.app.schemas.pac_allocator.issues import PlannerIssue
from backend.app.schemas.pac_allocator.preview import (
    FidelityLevelWeights,
    PacPreviewReadyResult,
    PlannerPreviewInvalidResult,
    PlannerPreviewNeedsInputResult,
    PlannerPreviewUnsupportedResult,
    PreviewAssetItem,
    PreviewCashItem,
    PreviewOtherCashItem,
    RebalancerPreviewReadyResult,
)
from backend.app.schemas.pac_allocator.request import PacPlannerRequest, RebalancerPlannerRequest
from backend.app.schemas.pac_allocator.results import PlannerResultSnapshot
from backend.app.services.pac_allocator.evaluation.economics import initial_cash_by_cell
from backend.app.services.pac_allocator.evaluation.evaluator import build_exact_policy_view, evaluate_do_nothing
from backend.app.services.pac_allocator.evaluation.limits import plan_reference
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index, exact_scenario_fingerprint
from backend.app.services.pac_allocator.models import FIDELITY_LEVEL_WEIGHTS, Checkpoint, ExactEvaluation, ExactPlannerScenario, check_budget
from backend.app.services.pac_allocator.normalize import COUNTED_ANYWAY, PlannerV2NormalizationResult, normalize_pac_plan, normalize_rebalancer_plan
from backend.app.services.pac_allocator.numeric import ExactRatio
from backend.app.services.pac_allocator.wire_numbers import ratio_to_exact_number, ratio_to_money

__all__ = ["preview_pac_allocation", "preview_rebalancing"]

_ZERO = ExactRatio(0)


def preview_pac_allocation(request: PacPlannerRequest, *, checkpoint: Checkpoint | None = None):
    """The PAC's preview: the cash the plan invests, or the issues that keep it from being counted."""
    check_budget(checkpoint)
    normalized = normalize_pac_plan(request)
    scenario = _counted(normalized)
    if scenario is None:
        return _failure(normalized.availability, request.snapshot.snapshot_id, list(normalized.issues))
    accounting = _do_nothing(scenario, checkpoint).accounting
    return PacPreviewReadyResult(**_ready_fields(scenario, normalized), total=ratio_to_money(accounting.fixed_reference, scenario.valuation_currency))


def preview_rebalancing(request: RebalancerPlannerRequest, *, checkpoint: Checkpoint | None = None):
    """The Rebalancer's preview: ``F``, today's target entries on it and the λ of the three fidelity levels; or the issues
    that keep it from being counted."""
    check_budget(checkpoint)
    normalized = normalize_rebalancer_plan(request)
    scenario = _counted(normalized)
    if scenario is None:
        return _failure(normalized.availability, request.snapshot.snapshot_id, list(normalized.issues))
    evaluation = _do_nothing(scenario, checkpoint)
    wealth = plan_reference(scenario, evaluation.accounting)
    levels = FidelityLevelWeights(**{level: ratio_to_exact_number(weight) for level, weight in FIDELITY_LEVEL_WEIGHTS.items()})
    return RebalancerPreviewReadyResult(**_ready_fields(scenario, normalized), total=ratio_to_money(wealth, scenario.valuation_currency), items=_items(scenario, evaluation, request), fidelity_level_weights=levels)


def _counted(normalized: PlannerV2NormalizationResult) -> ExactPlannerScenario | None:
    """The scenario the preview counts on: the normalized one, or the one the limits' cross checks were found on (Q2: the
    plan refuses it, the preview counts and names them); none when the request cannot be counted."""
    if normalized.ready and normalized.normalized is not None:
        return normalized.normalized
    return normalized.counted


def _do_nothing(scenario: ExactPlannerScenario, checkpoint: Checkpoint | None) -> ExactEvaluation:
    evaluation = evaluate_do_nothing(scenario, build_exact_policy_view(scenario, purpose="primary"), checkpoint=checkpoint)
    if evaluation.accounting is None:
        raise ValueError("the preview requires a do-nothing replay that produced accounting")
    return evaluation


def _items(scenario: ExactPlannerScenario, evaluation: ExactEvaluation, request: RebalancerPlannerRequest) -> list:
    """Every target entry today, each on ``F``: the Assets' current values and the cash entries' selected cash, every cash
    entry of the request (one still at 0 % with no limit, which the scenario leaves out, included); and «other cash» (G5-2 of
    project 67): what of ``F`` no entry holds, the cash outside the entries and the contributions, zero when none is left.
    The items cover ``F`` whole."""
    wealth = plan_reference(scenario, evaluation.accounting)
    currency = scenario.valuation_currency
    before = initial_cash_by_cell(build_scenario_index(scenario), evaluation.ledgers)
    items: list = [PreviewAssetItem(kind="asset", asset_id=row.asset_id, value=ratio_to_money(row.current_value, currency), weight=ratio_to_exact_number(row.current_value / wealth)) for row in evaluation.assets]
    held = sum((row.current_value for row in evaluation.assets), _ZERO)
    for entry in (item for item in request.target_weights if item.kind == "cash"):
        value = before.get((entry.broker_id, entry.currency), _ZERO)
        held += value
        items.append(PreviewCashItem(kind="cash", broker_id=entry.broker_id, currency=entry.currency, value=ratio_to_money(value, currency), weight=ratio_to_exact_number(value / wealth)))
    other = wealth - held
    items.append(PreviewOtherCashItem(kind="other_cash", value=ratio_to_money(other, currency), weight=ratio_to_exact_number(other / wealth)))
    return items


def _ready_fields(scenario: ExactPlannerScenario, normalized: PlannerV2NormalizationResult) -> dict:
    """The fields of every ready preview; the limits' cross checks move from ``issues`` to ``limit_problems``."""
    limit_problems = list(normalized.limit_problems)
    return {
        "operation": "preview",
        "result_state": "preview_ready",
        "availability": "ready",
        "snapshot": PlannerResultSnapshot(snapshot_id=scenario.snapshot.snapshot_id, request_fingerprint=exact_scenario_fingerprint(scenario)),
        "valuation_currency": scenario.valuation_currency,
        # A target total not yet one (F3a step 8 of project 67) is the plan's refusal, not the preview's: the screen shows it.
        "issues": [issue for issue in normalized.issues if issue not in limit_problems and issue.code not in COUNTED_ANYWAY],
        "limit_problems": limit_problems,
    }


def _failure(availability: str, snapshot_id: str, issues: list[PlannerIssue]):
    """The preview's failure result, like ``plan``'s: no exact scenario, so no fingerprint."""
    snapshot = PlannerResultSnapshot(snapshot_id=snapshot_id, request_fingerprint="")
    if availability == "needs_input":
        return PlannerPreviewNeedsInputResult(operation="preview", result_state="preview_needs_input", availability="needs_input", snapshot=snapshot, issues=issues)
    if availability == "unsupported":
        return PlannerPreviewUnsupportedResult(operation="preview", result_state="preview_unsupported", availability="unsupported", snapshot=snapshot, issues=issues)
    return PlannerPreviewInvalidResult(operation="preview", result_state="preview_invalid", availability="invalid", snapshot=snapshot, issues=issues)
