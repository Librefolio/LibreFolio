"""Wire projection of a Rebalancer plan (B3 of project 67): what the Rebalancer publishes beyond the PAC's rows.

Like ``planner_report``, this module **computes no economics**: every figure is on the exact evaluation already, or is read
through the one function that computes it (``evaluation.facts.rebalancer_score`` for ``D`` and ``J``,
``financial_math.weights.largest_weight_deviation`` for the largest deviation, ``evaluation.economics`` for the value of a
cash cell). What it adds is the shape of contract §6: the items on ``F`` (Assets, cash items, the uninvested row), the
transfers between Brokers, the plan accounts, the score and its tie-breaks, the exposure before and after. The rows the PAC
shares (deposits, conversions, buys, ledger, top-ups, accounting, costs, objectives) come from ``planner_report``.
"""

from __future__ import annotations

from backend.app.schemas.pac_allocator.exact import UnavailableExactNumber
from backend.app.schemas.pac_allocator.request import RebalancerCustomFidelityInput, RebalancerFidelityInput, RebalancerLevelFidelityInput, RebalancerTargetFirstFidelityInput
from backend.app.schemas.pac_allocator.results import RebalancerScenarioBasis
from backend.app.schemas.pac_allocator.rows import (
    PlannerTransfer,
    RebalancerAssetPlanRow,
    RebalancerCashItemRow,
    RebalancerExposurePlanRow,
    RebalancerScoreSummary,
    RebalancerTieBreakStage,
    RebalancerUninvestedRow,
)
from backend.app.services.financial_math.weights import largest_weight_deviation
from backend.app.services.pac_allocator import planner_report as report
from backend.app.services.pac_allocator.evaluation.economics import final_cash_by_cell, initial_cash_by_cell
from backend.app.services.pac_allocator.evaluation.facts import rebalancer_score
from backend.app.services.pac_allocator.evaluation.limits import limit_reference, resolve_scenario_limits
from backend.app.services.pac_allocator.evaluation.scenario import build_scenario_index
from backend.app.services.pac_allocator.models import FIDELITY_LEVEL_WEIGHTS, ExactEvaluation, ExactPlannerScenario, ExactPolicyView
from backend.app.services.pac_allocator.numeric import ExactRatio
from backend.app.services.pac_allocator.solver import SolverRunResult
from backend.app.services.pac_allocator.wire_numbers import ratio_to_exact_number, ratio_to_fixed_decimal, ratio_to_money

__all__ = [
    "build_cash_item_rows",
    "build_rebalancer_asset_rows",
    "build_rebalancer_exposure_rows",
    "build_rebalancer_scenario_basis",
    "build_score",
    "build_transfers",
    "build_uninvested_row",
    "wire_fidelity",
]

_ZERO = ExactRatio(0)
_TIE_STAGE_PREFIX = "tie:"
# The Rebalancer's main stages: the score, or the «Target first» chain. Every later stage of the view is a named tie-break.
_PRINCIPAL_CODES = frozenset({"plan_score", "target_distance", "wealth_loss"})


def _accounting(evaluation: ExactEvaluation):
    if evaluation.accounting is None or evaluation.costs is None:
        raise ValueError("the Rebalancer's report requires an evaluation that produced accounting and costs")
    return evaluation.accounting


def wire_fidelity(fidelity) -> RebalancerFidelityInput:
    """An exact fidelity in the request's form, for a scenario built without a request: a level whose ``λ`` is in
    ``FIDELITY_LEVEL_WEIGHTS``, else a custom ``λ``; «Target first» as it is. A request's own form is always preferred."""
    if fidelity is None or fidelity.kind == "target_first":
        return RebalancerTargetFirstFidelityInput(kind="target_first")
    level = next((name for name, weight in FIDELITY_LEVEL_WEIGHTS.items() if weight == fidelity.distance_weight), None)
    if level is not None:
        return RebalancerLevelFidelityInput(kind="level", level=level)
    return RebalancerCustomFidelityInput.model_validate({"kind": "custom", "lambda": ratio_to_fixed_decimal(fidelity.distance_weight)})


def build_rebalancer_scenario_basis(scenario: ExactPlannerScenario, evaluation: ExactEvaluation, fidelity: RebalancerFidelityInput) -> RebalancerScenarioBasis:
    """The shared basis plus the request's fidelity, as the request wrote it, and ``F``."""
    accounting = _accounting(evaluation)
    return RebalancerScenarioBasis(**report.scenario_basis_fields(scenario, evaluation), target_fidelity=fidelity, initial_wealth=ratio_to_money(accounting.initial_wealth, scenario.valuation_currency))


def _share(value: ExactRatio, wealth: ExactRatio):
    return ratio_to_exact_number(value / wealth)


def build_rebalancer_asset_rows(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> list[RebalancerAssetPlanRow]:
    """One row per Asset, before / target / after, every weight a share of ``F`` (contract §6.2)."""
    accounting = _accounting(evaluation)
    currency = scenario.valuation_currency
    wealth = accounting.initial_wealth
    bounds = resolve_scenario_limits(scenario, limit_reference(scenario, accounting)).assets()
    rows = []
    for row in evaluation.assets:
        limit = bounds.get(row.asset_id)
        rows.append(
            RebalancerAssetPlanRow(
                asset_id=row.asset_id,
                before_value=ratio_to_money(row.current_value, currency),
                before_weight=_share(row.current_value, wealth),
                target_weight=ratio_to_exact_number(row.target_weight),
                target_value=ratio_to_money(row.target_value, currency),
                final_value=ratio_to_money(row.final_value, currency),
                final_weight=_share(row.final_value, wealth),
                residual=ratio_to_money(row.residual, currency),
                buy_mid_value=ratio_to_money(row.buy_mid_value, currency),
                sell_mid_value=ratio_to_money(row.sell_mid_value, currency),
                minimum=ratio_to_money(limit.minimum, currency) if limit is not None and limit.minimum is not None else None,
                maximum=ratio_to_money(limit.maximum, currency) if limit is not None and limit.maximum is not None else None,
            )
        )
    return rows


def _cash_values(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> tuple[dict[tuple[str, str], ExactRatio], dict[tuple[str, str], ExactRatio]]:
    index = build_scenario_index(scenario)
    return initial_cash_by_cell(index, evaluation.ledgers), final_cash_by_cell(index, evaluation.ledgers)


def build_cash_item_rows(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> list[RebalancerCashItemRow]:
    """One row per cash entry of the scenario (a weight or a limit), before / target / after on ``F``. The values are the
    cells' spendable cash as ``evaluation.economics`` reads it, the one reading the replay's distance and limits use."""
    accounting = _accounting(evaluation)
    currency = scenario.valuation_currency
    wealth = accounting.initial_wealth
    before, final = _cash_values(scenario, evaluation)
    bounds = resolve_scenario_limits(scenario, limit_reference(scenario, accounting)).cash()
    rows = []
    for entry in scenario.cash_entries:
        cell = (entry.broker_id, entry.currency)
        before_value, final_value, target_value = before.get(cell, _ZERO), final.get(cell, _ZERO), entry.weight * wealth
        limit = bounds.get(cell)
        rows.append(
            RebalancerCashItemRow(
                broker_id=entry.broker_id,
                currency=entry.currency,
                before_value=ratio_to_money(before_value, currency),
                before_weight=_share(before_value, wealth),
                target_weight=ratio_to_exact_number(entry.weight),
                target_value=ratio_to_money(target_value, currency),
                final_value=ratio_to_money(final_value, currency),
                final_weight=_share(final_value, wealth),
                residual=ratio_to_money(final_value - target_value, currency),
                minimum=ratio_to_money(limit.minimum, currency) if limit is not None and limit.minimum is not None else None,
                maximum=ratio_to_money(limit.maximum, currency) if limit is not None and limit.maximum is not None else None,
            )
        )
    return rows


def build_uninvested_row(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> RebalancerUninvestedRow:
    """``N`` before and after: ``F`` less the Assets and the cash items with a target. After the plan it is the exact
    accounting's ``uninvested``; before, the same reading on the starting values."""
    accounting = _accounting(evaluation)
    currency = scenario.valuation_currency
    wealth = accounting.initial_wealth
    before, _final = _cash_values(scenario, evaluation)
    before_items = sum((before.get((entry.broker_id, entry.currency), _ZERO) for entry in scenario.cash_entries if entry.weight != _ZERO), _ZERO)
    before_value = wealth - accounting.current_invested - before_items
    return RebalancerUninvestedRow(
        before_value=ratio_to_money(before_value, currency),
        before_weight=_share(before_value, wealth),
        final_value=ratio_to_money(accounting.uninvested, currency),
        final_weight=_share(accounting.uninvested, wealth),
    )


def build_transfers(evaluation: ExactEvaluation, sequence) -> list[PlannerTransfer]:
    """One row per transfer the plan makes, read off its ``transfer_out`` postings (the replay posts only nonzero ones), in
    their canonical order; each takes the next step of the shared counter."""
    rows = []
    for posting in evaluation.postings:
        if posting.family != "transfer_out" or posting.exact_amount == _ZERO:
            continue
        destination = next(ref.entity_id for ref in posting.entity_refs if ref.kind == "destination_broker")
        rows.append(
            PlannerTransfer(
                transfer_id=posting.posting_id.replace("transfer-out:", "transfer:", 1),
                sequence=sequence.next(),
                source_broker_id=posting.broker_id,
                destination_broker_id=destination,
                amount=report._positive_money(posting.posted_amount, posting.currency),
            )
        )
    return rows


def build_rebalancer_exposure_rows(scenario: ExactPlannerScenario, evaluation: ExactEvaluation) -> list[RebalancerExposurePlanRow]:
    """The exposure before and after, on the invested part (decision 3 of the B3 checkpoint): the targets are the Assets'
    target weights over their sum, the cash being no exposure; before over the current invested value, after over the final.
    With no weight on any Asset there is no exposure target to close, and no row."""
    accounting = _accounting(evaluation)
    asset_total = sum((row.target_weight for row in evaluation.assets), _ZERO)
    if asset_total == _ZERO:
        return []
    targets = {row.asset_id: row.target_weight / asset_total for row in evaluation.assets}
    current = {row.asset_id: row.current_value for row in evaluation.assets}
    final = {row.asset_id: row.final_value for row in evaluation.assets}
    rows = []
    for dimension in report._EXPOSURE_DIMENSIONS:
        before_rows = report._exposure_rows_for_dimension(scenario, dimension, targets, current, accounting.current_invested)
        after_rows = report._exposure_rows_for_dimension(scenario, dimension, targets, final, accounting.final_invested)
        for before_row, after_row in zip(before_rows, after_rows, strict=True):
            before_weight = before_row.final_weight
            if isinstance(before_weight, UnavailableExactNumber):
                before_weight = UnavailableExactNumber(kind="unavailable", reason="zero_current_invested")
            rows.append(
                RebalancerExposurePlanRow(
                    dimension=after_row.dimension,
                    category_id=after_row.category_id,
                    label=after_row.label,
                    before_weight=before_weight,
                    target_weight=after_row.target_weight,
                    final_weight=after_row.final_weight,
                    provenance_ids=after_row.provenance_ids,
                )
            )
    return rows


def _tie_break_status(view: ExactPolicyView, solver: SolverRunResult) -> list[RebalancerTieBreakStage]:
    """How SCIP left each tie-break: the named ones in cascade order, then ``canonical``, the fixed-order vector (specifica
    §6.4: one level). ``closed`` at its optimum, ``unfinished`` at a limit, ``rejected`` when the exact comparison kept the
    plan before it (D4). The canonical vector is ``closed`` when all its stages are, ``rejected`` when every open one was
    rejected, ``unfinished`` otherwise."""
    named = [ref.code for ref in sorted(view.objectives, key=lambda ref: ref.ordinal) if ref.code not in _PRINCIPAL_CODES]
    by_code = {stage.objective_code: stage for stage in solver.stages}

    def status_of(stages) -> str:
        open_stages = [stage for stage in stages if stage is None or stage.status != "finished"]
        if not open_stages:
            return "closed"
        return "rejected" if all(stage is not None and stage.rejected for stage in open_stages) else "unfinished"

    canonical = [stage for stage in solver.stages if stage.objective_code.startswith(_TIE_STAGE_PREFIX)]
    rows = [RebalancerTieBreakStage(objective_code=code, status=status_of([by_code.get(code)])) for code in named]
    return [*rows, RebalancerTieBreakStage(objective_code="canonical", status=status_of(canonical))]


def build_score(scenario: ExactPlannerScenario, view: ExactPolicyView, evaluation: ExactEvaluation, solver: SolverRunResult) -> RebalancerScoreSummary:
    """The score (specifica §6) from ``evaluation.facts.rebalancer_score``, the largest deviations from
    ``financial_math.weights``, and the tie-breaks from the solver run."""
    accounting = _accounting(evaluation)
    currency = scenario.valuation_currency
    wealth = accounting.initial_wealth
    fidelity = scenario.target_fidelity
    score = rebalancer_score(fidelity, evaluation.assets, evaluation.cash_targets, accounting)
    weighted = fidelity is not None and fidelity.kind == "weighted"
    before, _final = _cash_values(scenario, evaluation)
    before_items = [(row.current_value, row.target_weight) for row in evaluation.assets]
    before_items += [(before.get((row.broker_id, row.currency), _ZERO), row.target_weight) for row in evaluation.cash_targets]
    after_items = [(row.final_value, row.target_weight) for row in evaluation.assets] + [(row.final_value, row.target_weight) for row in evaluation.cash_targets]
    return RebalancerScoreSummary(
        distance_weight=ratio_to_exact_number(fidelity.distance_weight) if weighted else None,
        target_distance=ratio_to_exact_number(score["target_distance"]),
        distance_per_wealth=ratio_to_money(score["target_distance"] / wealth, currency),
        wealth_loss=ratio_to_money(score["wealth_loss"], currency),
        plan_score=ratio_to_money(score["plan_score"], currency) if weighted else None,
        largest_deviation_before=ratio_to_exact_number(largest_weight_deviation(before_items, wealth)),
        largest_deviation_after=ratio_to_exact_number(largest_weight_deviation(after_items, wealth)),
        tie_breaks=_tie_break_status(view, solver),
    )
