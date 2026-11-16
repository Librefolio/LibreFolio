"""Planner results (failure and ready, with their deployments), the cross-row validators of a ready result, and the input and output adapters of both Tools."""

from __future__ import annotations

from fractions import Fraction
from typing import Annotated, Literal, Union

from pydantic import Field, TypeAdapter, model_validator

from backend.app.schemas.pac_allocator.base import AllocationStrictModel, CurrencyCode, PlannerId, PlannerRef, collect_currency_codes, require_unique
from backend.app.schemas.pac_allocator.evidence import (
    InfeasibilityProvenProof,
    NotProvenProof,
    OptimalProvenProof,
    ReadyPlanProof,
    RebalancerOptimalProvenProof,
    RebalancerReadyPlanProof,
    ReportedFloatingSolverEvidence,
)
from backend.app.schemas.pac_allocator.exact import ExactMoney, ExactNumberAvailability, available_fraction, exact_fraction, fixed_fraction, money_fraction, validate_weight_availability
from backend.app.schemas.pac_allocator.issues import PlannerIssue
from backend.app.schemas.pac_allocator.request import PacPlannerRequest, PlannerProvenance, RebalancerFidelityInput, RebalancerPlannerRequest
from backend.app.schemas.pac_allocator.rows import PacAssetPlanRow, PacExposurePlanRow, PlannerAccountingSummary, PlannerCatalogs, PlannerScenarioBasis, PlannerSellOrderRow, RebalancerAssetPlanRow, RebalancerCashItemRow, RebalancerExposurePlanRow, RebalancerUnavailableWeight
from backend.app.schemas.pac_allocator.solutions import DeploymentCoincident, DeploymentUnavailable, PacDistinctDeployment, PacIncumbentSolution, PacNoOpSolution, PacPlanSolution, RebalancerDistinctDeployment, RebalancerIncumbentSolution, RebalancerNoOpSolution, RebalancerPlanSolution


def _validate_distinct_deployment(
    primary: PacPlanSolution | RebalancerPlanSolution,
    deployment: PacDistinctDeployment | RebalancerDistinctDeployment,
) -> None:
    comparison = deployment.comparison
    if primary.solution_id == deployment.solution.solution_id:
        raise ValueError("A distinct deployment must use a distinct solution ID")
    if comparison.primary_solution_id != primary.solution_id:
        raise ValueError("Deployment comparison must reference the primary solution")
    if comparison.deployment_solution_id != deployment.solution.solution_id:
        raise ValueError("Deployment comparison must reference the deployment solution")
    primary_orders = {row.order_id: row.model_dump(mode="json") for row in primary.order_rows}
    deployment_orders = {row.order_id: row.model_dump(mode="json") for row in deployment.solution.order_rows}
    changed_order_rows = sum(primary_orders.get(order_id) != deployment_orders.get(order_id) for order_id in primary_orders.keys() | deployment_orders.keys())
    if changed_order_rows == 0 or comparison.changed_order_rows != changed_order_rows:
        raise ValueError("A distinct deployment must report its exact nonzero changed-order-row count")
    primary_stages = primary.objectives.stages
    deployment_stages = deployment.solution.objectives.stages
    deltas = comparison.objective_deltas
    if len(primary_stages) != len(deployment_stages) or len(deltas) != len(primary_stages):
        raise ValueError("Deployment comparison must cover every objective stage")
    for primary_stage, deployment_stage, delta in zip(primary_stages, deployment_stages, deltas, strict=True):
        primary_key = (primary_stage.objective_code, primary_stage.ordinal, primary_stage.sense, primary_stage.unit)
        deployment_key = (deployment_stage.objective_code, deployment_stage.ordinal, deployment_stage.sense, deployment_stage.unit)
        delta_key = (delta.objective_code, delta.ordinal, delta.sense, delta.unit)
        if primary_key != deployment_key or delta_key != primary_key:
            raise ValueError("Deployment objective stages must have identical ordered identities")
        if delta.primary_value != primary_stage.value or delta.deployment_value != deployment_stage.value:
            raise ValueError("Deployment comparison values must match the authoritative solutions")
        if exact_fraction(delta.delta) != exact_fraction(delta.deployment_value) - exact_fraction(delta.primary_value):
            raise ValueError("Deployment objective delta must equal deployment minus primary")


def _validate_accounting_summary(accounting: PlannerAccountingSummary, *, top_up_value: Fraction = Fraction(0)) -> None:
    """Check the accounting identities; ``top_up_value`` is the PAC rounding top-ups' total value.

    A top-up is cash the user adds before executing: reachable funding the
    plan relies on, which the published accounting does not include. So it
    relaxes the two rules that read the balance — free cash and the favorable
    shortfall bound — by exactly its value, and nothing else. The Rebalancer
    has no top-up and passes zero.
    """
    nonnegative = (
        accounting.current_invested,
        accounting.selected_funding,
        accounting.reachable_funding,
        accounting.trapped_funding,
        accounting.fixed_reference,
        accounting.final_invested,
        accounting.physical_reserves,
        accounting.economic_losses,
        accounting.rounding_bound,
    )
    if any(money_fraction(money) < 0 for money in nonnegative):
        raise ValueError("Nonnegative accounting totals cannot be negative")
    if money_fraction(accounting.free_cash) + top_up_value < 0:
        raise ValueError("Free cash cannot be negative beyond the rounding top-ups")
    if money_fraction(accounting.selected_funding) != money_fraction(accounting.reachable_funding) + money_fraction(accounting.trapped_funding):
        raise ValueError("Selected funding must equal reachable plus trapped funding")
    if money_fraction(accounting.fixed_reference) != money_fraction(accounting.current_invested) + money_fraction(accounting.reachable_funding):
        raise ValueError("Fixed reference must equal current invested plus reachable funding")
    if abs(money_fraction(accounting.rounding_delta)) > money_fraction(accounting.rounding_bound):
        raise ValueError("Rounding delta must remain inside its exact bound")
    if money_fraction(accounting.shortfall) + top_up_value < -money_fraction(accounting.rounding_bound):
        raise ValueError("Shortfall cannot exceed the favorable rounding bound")
    decomposition = money_fraction(accounting.free_cash) + money_fraction(accounting.physical_reserves) + money_fraction(accounting.economic_losses) + money_fraction(accounting.rounding_delta)
    if money_fraction(accounting.shortfall) != decomposition:
        raise ValueError("Shortfall must equal free cash, physical reserves, economic losses, and rounding")
    if money_fraction(accounting.identity_delta) != 0:
        raise ValueError("Published accounting identity delta must be zero")


def _validate_asset_row(row: PacAssetPlanRow) -> None:
    if any(money_fraction(value) < 0 for value in (row.target_value, row.final_value, row.buy_mid_value)):
        raise ValueError("Asset target, final, and BUY values cannot be negative")
    if money_fraction(row.residual) != money_fraction(row.final_value) - money_fraction(row.target_value):
        raise ValueError("Asset residual must equal final minus target value")
    if money_fraction(row.final_value) != money_fraction(row.buy_mid_value):
        raise ValueError("Asset final value must reconcile before, BUY, and SELL values")


def _validate_target_weight_identities(
    rows: list[PacAssetPlanRow],
    fixed_reference: Fraction,
) -> None:
    weights = [exact_fraction(row.target_weight) for row in rows]
    if any(weight < 0 or weight > 1 for weight in weights) or sum(weights, Fraction()) != 1:
        raise ValueError("Asset target weights must form a complete unit vector")
    if any(weight * fixed_reference != money_fraction(row.target_value) for row, weight in zip(rows, weights, strict=True)):
        raise ValueError("Each Asset target weight must match its fixed-reference target value")


def _validate_available_weight_identities(
    weights: list[ExactNumberAvailability],
    values: list[ExactMoney],
    total: Fraction,
    zero_reason: str,
    label: str,
) -> None:
    validate_weight_availability(weights, total, zero_reason, label)
    if total == 0:
        return
    for weight, value in zip(weights, values, strict=True):
        available = available_fraction(weight)
        if available is None or available * total != money_fraction(value):
            raise ValueError(f"Each available Asset {label.lower()} weight must match its value")


def _validate_asset_projection(solution: PacPlanSolution | RebalancerPlanSolution) -> None:
    if isinstance(solution, RebalancerPlanSolution):
        _validate_rebalancer_items(solution)
        return
    accounting = solution.accounting
    fixed_reference = money_fraction(accounting.fixed_reference)
    current_invested = money_fraction(accounting.current_invested)
    final_invested = money_fraction(accounting.final_invested)
    if sum((money_fraction(row.target_value) for row in solution.asset_rows), Fraction()) != fixed_reference:
        raise ValueError("Asset target values must sum to the fixed reference")
    if sum((money_fraction(row.final_value) for row in solution.asset_rows), Fraction()) != final_invested:
        raise ValueError("Asset final values must sum to final invested value")
    for row in solution.asset_rows:
        _validate_asset_row(row)
    if current_invested != 0:
        raise ValueError("PAC current invested value must be zero")
    if sum((money_fraction(row.residual) for row in solution.asset_rows), Fraction()) != -money_fraction(accounting.shortfall):
        raise ValueError("Asset residuals must sum to negative shortfall")
    _validate_target_weight_identities(solution.asset_rows, fixed_reference)
    _validate_available_weight_identities(
        [row.final_weight for row in solution.asset_rows],
        [row.final_value for row in solution.asset_rows],
        final_invested,
        "zero_final_invested",
        "Final",
    )


def _validate_rebalancer_item_row(row: RebalancerAssetPlanRow | RebalancerCashItemRow, wealth: Fraction) -> None:
    """One item, on ``F``: its target is its weight of ``F``, its weights its values over ``F``, its residual final less target."""
    target_weight = exact_fraction(row.target_weight)
    if not 0 <= target_weight <= 1:
        raise ValueError("An item's target weight must be between zero and one")
    if money_fraction(row.before_value) < 0 or money_fraction(row.target_value) < 0:
        raise ValueError("An item's before and target values cannot be negative")
    if target_weight * wealth != money_fraction(row.target_value):
        raise ValueError("An item's target value must be its target weight of the initial wealth")
    if exact_fraction(row.before_weight) * wealth != money_fraction(row.before_value) or exact_fraction(row.final_weight) * wealth != money_fraction(row.final_value):
        raise ValueError("An item's weights must be its values over the initial wealth")
    if money_fraction(row.residual) != money_fraction(row.final_value) - money_fraction(row.target_value):
        raise ValueError("An item's residual must equal final minus target value")
    if isinstance(row, RebalancerAssetPlanRow):
        if any(money_fraction(value) < 0 for value in (row.final_value, row.buy_mid_value, row.sell_mid_value)):
            raise ValueError("Asset final, BUY, and SELL values cannot be negative")
        if money_fraction(row.final_value) != money_fraction(row.before_value) + money_fraction(row.buy_mid_value) - money_fraction(row.sell_mid_value):
            raise ValueError("Asset final value must reconcile before, BUY, and SELL values")


def _largest_deviation(rows: list, weight: str) -> Fraction:
    return max((abs(exact_fraction(getattr(row, weight)) - exact_fraction(row.target_weight)) for row in rows), default=Fraction())


def _validate_rebalancer_items(solution: RebalancerPlanSolution) -> None:
    """The items of a Rebalancer plan on ``F`` (contract §6.2) and the score read off them (specifica §6).

    The items of the distance are the Asset rows and the cash rows with a target weight; a cash row with only a limit sits
    inside the uninvested row, as in the exact replay. The items and the uninvested row add up to ``F`` before and after the
    plan; the target weights of the items sum to one. ``D`` is the sum of the squared residuals of the items plus ``N²``; the
    largest deviation is read off the same items (X14: the cash rows with a target). Final invested may be zero (contract §3).
    """
    accounting = solution.accounting
    accounts = solution.plan_accounts
    wealth = money_fraction(accounts.initial_wealth)
    if wealth <= 0:
        raise ValueError("A ready Rebalancer plan starts from a positive wealth")
    for row in [*solution.asset_rows, *solution.cash_rows]:
        _validate_rebalancer_item_row(row, wealth)
    items: list[RebalancerAssetPlanRow | RebalancerCashItemRow] = [*solution.asset_rows, *_distance_cash_rows(solution)]
    if sum((exact_fraction(row.target_weight) for row in items), Fraction()) != 1:
        raise ValueError("The target weights of the Assets and the cash items must sum to one")
    if sum((money_fraction(row.before_value) for row in solution.asset_rows), Fraction()) != money_fraction(accounting.current_invested):
        raise ValueError("Rebalancer before values must sum to current invested value")
    if sum((money_fraction(row.final_value) for row in solution.asset_rows), Fraction()) != money_fraction(accounting.final_invested):
        raise ValueError("Asset final values must sum to final invested value")
    _validate_rebalancer_uninvested(solution, items, wealth)
    _validate_rebalancer_score(solution, items, wealth)


def _distance_cash_rows(solution: RebalancerPlanSolution) -> list[RebalancerCashItemRow]:
    """The cash rows that are items of the distance: those with a target weight."""
    return [row for row in solution.cash_rows if exact_fraction(row.target_weight) != 0]


def _validate_rebalancer_uninvested(solution: RebalancerPlanSolution, items: list, wealth: Fraction) -> None:
    """The uninvested row closes the items to ``F`` before and after, and is the plan accounts' ``N``."""
    accounts = solution.plan_accounts
    uninvested = solution.uninvested_row
    for value, weight in ((uninvested.before_value, uninvested.before_weight), (uninvested.final_value, uninvested.final_weight)):
        if exact_fraction(weight) * wealth != money_fraction(value):
            raise ValueError("The uninvested weights must be its values over the initial wealth")
    for field in ("before_value", "final_value"):
        if sum((money_fraction(getattr(row, field)) for row in items), Fraction()) + money_fraction(getattr(uninvested, field)) != wealth:
            raise ValueError("The items and the uninvested row must add up to the initial wealth")
    if money_fraction(uninvested.final_value) != money_fraction(accounts.uninvested):
        raise ValueError("The uninvested row must match the plan accounts")


def _validate_rebalancer_score(solution: RebalancerPlanSolution, items: list, wealth: Fraction) -> None:
    """``D``, ``D/F``, the money lost, the largest deviations and the published stages, all read off the items."""
    accounts = solution.plan_accounts
    uninvested = solution.uninvested_row
    score = solution.score
    distance = sum((money_fraction(row.residual) ** 2 for row in items), Fraction()) + money_fraction(uninvested.final_value) ** 2
    if exact_fraction(score.target_distance) != distance or money_fraction(score.distance_per_wealth) != distance / wealth:
        raise ValueError("The target distance must be the squared residuals of the items plus the uninvested squared")
    if money_fraction(score.wealth_loss) != wealth - money_fraction(accounts.final_wealth):
        raise ValueError("The score's money lost must equal the initial less the final wealth")
    if (exact_fraction(score.largest_deviation_before), exact_fraction(score.largest_deviation_after)) != (_largest_deviation(items, "before_weight"), _largest_deviation(items, "final_weight")):
        raise ValueError("The largest deviation must be read off the items' weights")
    published = {stage.objective_code: exact_fraction(stage.value) for stage in solution.objectives.stages}
    expected = {"target_distance": distance, "wealth_loss": money_fraction(score.wealth_loss)}
    if score.plan_score is not None:
        expected["plan_score"] = money_fraction(score.plan_score)
    if any(code in published and published[code] != value for code, value in expected.items()):
        raise ValueError("The published objective stages must match the score")


def _validate_exposure_projection(solution: PacPlanSolution | RebalancerPlanSolution) -> None:
    if isinstance(solution, RebalancerPlanSolution):
        _validate_rebalancer_exposure(solution)
        return
    dimensions: dict[str, list[PacExposurePlanRow]] = {}
    for row in solution.exposure_rows:
        dimensions.setdefault(row.dimension, []).append(row)
    for dimension, rows in dimensions.items():
        if sum((exact_fraction(row.target_weight) for row in rows), Fraction()) != 1:
            raise ValueError(f"{dimension} exposure targets must form a complete unit vector")
        validate_weight_availability(
            [row.final_weight for row in rows],
            money_fraction(solution.accounting.final_invested),
            "zero_final_invested",
            f"{dimension} final exposure",
        )


def _validate_rebalancer_weights(values: list, base: Fraction, zero_reason: str, label: str) -> None:
    """One base of a Rebalancer dimension: every weight available and summing to one on a positive base; every weight
    unavailable for ``zero_reason`` on a zero base."""
    if base == 0:
        if any(not isinstance(value, RebalancerUnavailableWeight) or value.reason != zero_reason for value in values):
            raise ValueError(f"{label} weights must be unavailable for {zero_reason} on a zero base")
        return
    fractions = [available_fraction(value) for value in values]
    if any(value is None for value in fractions):
        raise ValueError(f"{label} weights must all be available on a positive base")
    if sum((value for value in fractions if value is not None), Fraction()) != 1:
        raise ValueError(f"{label} weights must sum to one")


_REBALANCER_EXPOSURE_DIMENSIONS = ("asset_type", "sector", "geography")


def _validate_rebalancer_exposure(solution: RebalancerPlanSolution) -> None:
    """The whole portfolio, in each of the three dimensions (developer's decision of 13/11, project 67): exactly one cash
    row, whose target is the cash items' weights and whose before and after are the cash of the accounts (``F`` less the
    invested value, ``W`` less the final invested value); the targets sum to one; before sums to one on ``F``, after on
    ``W``, each unavailable with its own reason at a zero base."""
    dimensions: dict[str, list[RebalancerExposurePlanRow]] = {dimension: [] for dimension in _REBALANCER_EXPOSURE_DIMENSIONS}
    for row in solution.exposure_rows:
        dimensions[row.dimension].append(row)
    initial = money_fraction(solution.plan_accounts.initial_wealth)
    final = money_fraction(solution.plan_accounts.final_wealth)
    cash_target = sum((exact_fraction(row.target_weight) for row in solution.cash_rows), Fraction())
    cash_before = None if initial == 0 else (initial - money_fraction(solution.accounting.current_invested)) / initial
    cash_after = None if final == 0 else (final - money_fraction(solution.accounting.final_invested)) / final
    for dimension, rows in dimensions.items():
        cash_rows = [row for row in rows if row.kind == "cash"]
        if len(cash_rows) != 1:
            raise ValueError(f"{dimension} exposure must have exactly one cash row")
        (cash,) = cash_rows
        if exact_fraction(cash.target_weight) != cash_target:
            raise ValueError(f"{dimension} exposure cash target must be the cash items' weights, not renormalised")
        if (available_fraction(cash.before_weight), available_fraction(cash.final_weight)) != (cash_before, cash_after):
            raise ValueError(f"{dimension} exposure cash must be the cash of the accounts, before on F and after on W")
        if sum((exact_fraction(row.target_weight) for row in rows), Fraction()) != 1:
            raise ValueError(f"{dimension} exposure targets must sum to one with the cash row")
        _validate_rebalancer_weights([row.before_weight for row in rows], initial, "zero_initial_wealth", f"{dimension} before exposure")
        _validate_rebalancer_weights([row.final_weight for row in rows], final, "zero_final_wealth", f"{dimension} final exposure")


def _limit_row_money(solution: PacPlanSolution | RebalancerPlanSolution) -> list:
    """The amounts of a solution's limit rows (Asset minimum and maximum, cash entry or item values and limits): all in the valuation currency."""
    amounts = [money for row in solution.asset_rows for money in (row.minimum, row.maximum)]
    cash_fields = ("final_value", "minimum", "maximum") if isinstance(solution, PacPlanSolution) else ("before_value", "target_value", "final_value", "residual", "minimum", "maximum")
    amounts += [getattr(row, name) for row in solution.cash_rows for name in cash_fields]
    return [money for money in amounts if money is not None]


def _validate_plan_accounts(solution: PacPlanSolution | RebalancerPlanSolution) -> None:
    """The plan accounts against the accounting (both Tools, contract §6.1): ``F`` is the current invested value plus the
    selected funding; the money lost, by entry, is the reserves plus the economic losses plus the rounding; ``N`` is ``F``
    less the final invested value and the cash items with a target (the PAC has none: its ``N`` is the shortfall plus the
    trapped cash)."""
    accounting = solution.accounting
    accounts = solution.plan_accounts
    wealth = money_fraction(accounts.initial_wealth)
    if wealth != money_fraction(accounting.current_invested) + money_fraction(accounting.selected_funding):
        raise ValueError("The initial wealth must equal current invested plus selected funding")
    if accounts.money_lost.total() != money_fraction(accounting.physical_reserves) + money_fraction(accounting.economic_losses) + money_fraction(accounting.rounding_delta):
        raise ValueError("The money lost must equal the reserves, the economic losses and the rounding of the accounting")
    targeted_cash = sum((money_fraction(row.final_value) for row in solution.cash_rows if isinstance(row, RebalancerCashItemRow) and exact_fraction(row.target_weight) != 0), Fraction())
    if money_fraction(accounts.uninvested) != wealth - money_fraction(accounting.final_invested) - targeted_cash:
        raise ValueError("The uninvested value must be the initial wealth less the final invested value and the cash items with a target")


def _rebalancer_valuation_money(solution: PacPlanSolution | RebalancerPlanSolution) -> list:
    """The Rebalancer's amounts in the valuation currency: the uninvested row, the score, the cost basis and gain of every
    sale, the tax parts."""
    if not isinstance(solution, RebalancerPlanSolution):
        return []
    amounts = [solution.uninvested_row.before_value, solution.uninvested_row.final_value]
    amounts += [solution.score.distance_per_wealth, solution.score.wealth_loss, *([solution.score.plan_score] if solution.score.plan_score is not None else [])]
    amounts += [money for row in solution.order_rows if isinstance(row, PlannerSellOrderRow) for money in (row.cost_basis, row.realized_gain)]
    amounts += [getattr(row, name) for row in solution.tax_basket_rows for name in ("weighted_gains", "weighted_losses", "carried_losses_used", "taxable", "tax", "loss_left")]
    amounts += [getattr(row, name) for row in solution.asset_type_tax_rows for name in ("realized_gain", "realized_loss", "tax")]
    return amounts


def _validate_solution_financials(
    solution: PacPlanSolution | RebalancerPlanSolution,
    valuation_currency: CurrencyCode,
) -> None:
    valuation_money = [
        *(getattr(solution.accounting, name) for name in type(solution.accounting).model_fields),
        *(getattr(solution.costs, name) for name in type(solution.costs).model_fields),
    ]
    for row in solution.asset_rows:
        fields = ("target_value", "final_value", "residual", "buy_mid_value")
        if isinstance(row, RebalancerAssetPlanRow):
            fields = ("before_value", *fields, "sell_mid_value")
        valuation_money.extend(getattr(row, name) for name in fields)
    valuation_money.extend(_limit_row_money(solution))
    valuation_money.extend(row.spread_loss for row in solution.conversions)
    valuation_money.extend(row.execution_margin_cost for row in solution.order_rows)
    valuation_money.extend(_rebalancer_valuation_money(solution))
    accounts = solution.plan_accounts
    valuation_money.extend([accounts.initial_wealth, accounts.final_wealth, accounts.uninvested, *(getattr(accounts.money_lost, name) for name in type(accounts.money_lost).model_fields)])
    top_ups = solution.rounding_top_ups
    valuation_money.extend(row.valuation_amount for row in top_ups)
    if any(money.currency != valuation_currency for money in valuation_money):
        raise ValueError("Asset, accounting, and cost projections must use the valuation currency")
    if any(row.currency == valuation_currency and money_fraction(row.valuation_amount) != fixed_fraction(row.amount) for row in top_ups):
        raise ValueError("A rounding top-up in the valuation currency must be valued at its own amount")
    if any(exact_fraction(getattr(solution.costs, name).value) < 0 for name in type(solution.costs).model_fields):
        raise ValueError("Cost totals cannot be negative")
    # Final invested may be zero in the Rebalancer too (contract §3): a plan may end fully in cash.
    _validate_accounting_summary(solution.accounting, top_up_value=sum((money_fraction(row.valuation_amount) for row in top_ups), Fraction()))
    _validate_plan_accounts(solution)
    _validate_asset_projection(solution)
    _validate_exposure_projection(solution)
    if any(stage.unit.kind in {"valuation_money", "valuation_money_squared"} and stage.unit.currency_code != valuation_currency for stage in solution.objectives.stages):
        raise ValueError("Valuation objective units must use the scenario valuation currency")
    if any(stage.objective_code == "shortfall" and exact_fraction(stage.value) != money_fraction(solution.accounting.shortfall) for stage in solution.objectives.stages):
        raise ValueError("The shortfall objective must equal the authoritative accounting shortfall")


def _validate_top_up_minor_units(
    catalogs: PlannerCatalogs,
    solution: PacPlanSolution | RebalancerPlanSolution,
) -> None:
    """``amount <= rounded_postings x minor unit``: the one top-up bound that needs the catalogue."""
    minor_units = {row.currency: fixed_fraction(row.minor_unit) for row in catalogs.currencies}
    if any(fixed_fraction(row.amount) > row.rounded_postings * minor_units[row.currency] for row in solution.rounding_top_ups):
        raise ValueError("A rounding top-up cannot exceed its rounded postings times the currency minor unit")


def _validate_rebalancer_references(broker_ids: set[str], solution: PacPlanSolution | RebalancerPlanSolution) -> None:
    if not isinstance(solution, RebalancerPlanSolution):
        return
    if any(row.source_broker_id not in broker_ids or row.destination_broker_id not in broker_ids for row in solution.transfers):
        raise ValueError("Transfer rows must reference catalog Broker IDs")
    if any(row.broker_id not in broker_ids for row in solution.tax_reserves):
        raise ValueError("Tax reserve rows must reference catalog Broker IDs")


def _validate_ready_solution(
    catalogs: PlannerCatalogs,
    provenance: list[PlannerProvenance],
    valuation_currency: CurrencyCode,
    solution: PacPlanSolution | RebalancerPlanSolution,
) -> None:
    asset_ids = {row.asset_id for row in catalogs.assets}
    broker_ids = {row.broker_id for row in catalogs.brokers}
    currencies = {row.currency for row in catalogs.currencies}
    provenance_ids = {row.provenance_id for row in provenance}
    if {row.asset_id for row in solution.asset_rows} != asset_ids:
        raise ValueError("Solution must carry exactly one authoritative row per catalog Asset")
    if any(row.broker_id not in broker_ids or row.currency not in currencies for row in solution.ledger_rows):
        raise ValueError("Ledger rows must reference catalog Broker and currency IDs")
    if any(row.broker_id not in broker_ids or row.currency not in currencies for row in solution.cash_rows):
        raise ValueError("Cash entry rows must reference catalog Broker and currency IDs")
    if any(row.destination_broker_id not in broker_ids for row in solution.funding_actions):
        raise ValueError("Funding rows must reference catalog Broker IDs")
    if any(row.broker_id not in broker_ids for row in solution.conversions):
        raise ValueError("Conversion rows must reference catalog Broker IDs")
    if any(row.asset_id not in asset_ids or row.broker_id not in broker_ids for row in solution.order_rows):
        raise ValueError("Order rows must reference catalog Asset and Broker IDs")
    _validate_rebalancer_references(broker_ids, solution)
    if not collect_currency_codes(solution.model_dump(mode="python")) <= currencies:
        raise ValueError("Solution rows must reference catalog currencies")
    _validate_top_up_minor_units(catalogs, solution)
    referenced_provenance = {provenance_id for row in [*solution.funding_actions, *solution.conversions, *solution.order_rows, *solution.exposure_rows] for provenance_id in row.provenance_ids}
    if not referenced_provenance <= provenance_ids:
        raise ValueError("Solution rows must reference top-level provenance IDs")
    for row in [*solution.funding_actions, *solution.conversions, *solution.order_rows, *solution.exposure_rows]:
        require_unique(row.provenance_ids, "Result-row provenance IDs")
    _validate_solution_financials(solution, valuation_currency)


def _validate_scenario_basis_financials(
    product: str,
    scenario_basis: PlannerScenarioBasis,
) -> None:
    basis_money = [
        scenario_basis.current_invested,
        scenario_basis.selected_funding,
        scenario_basis.reachable_funding,
        scenario_basis.trapped_funding,
        scenario_basis.fixed_reference,
    ]
    if any(money.currency != scenario_basis.valuation_currency for money in basis_money):
        raise ValueError(f"{product} scenario totals must use the valuation currency")
    if any(exact_fraction(money.value) < 0 for money in basis_money):
        raise ValueError(f"{product} scenario totals cannot be negative")
    if product == "PAC" and money_fraction(scenario_basis.current_invested) != 0:
        raise ValueError("PAC scenario current invested value must be zero")
    if product == "Rebalancer" and money_fraction(scenario_basis.current_invested) <= 0:
        raise ValueError("Ready Rebalancer scenarios require positive current invested value")
    if isinstance(scenario_basis, RebalancerScenarioBasis):
        if scenario_basis.initial_wealth.currency != scenario_basis.valuation_currency:
            raise ValueError("Rebalancer initial wealth must use the valuation currency")
        if money_fraction(scenario_basis.initial_wealth) != money_fraction(scenario_basis.current_invested) + money_fraction(scenario_basis.selected_funding):
            raise ValueError("Rebalancer initial wealth must equal current invested plus selected funding")
    if exact_fraction(scenario_basis.selected_funding.value) != exact_fraction(scenario_basis.reachable_funding.value) + exact_fraction(scenario_basis.trapped_funding.value):
        raise ValueError(f"{product} selected funding must equal reachable plus trapped funding")
    if exact_fraction(scenario_basis.fixed_reference.value) != exact_fraction(scenario_basis.current_invested.value) + exact_fraction(scenario_basis.reachable_funding.value):
        raise ValueError(f"{product} fixed reference must equal current invested plus reachable funding")


def _validate_result_catalogs(
    product: str,
    catalogs: PlannerCatalogs,
    provenance: list[PlannerProvenance],
    scenario_basis: PlannerScenarioBasis,
) -> None:
    require_unique([row.provenance_id for row in provenance], f"{product} provenance IDs")
    expected_counts = (len(catalogs.assets), len(catalogs.brokers), len(catalogs.currencies), len(provenance))
    actual_counts = (
        scenario_basis.counts.assets,
        scenario_basis.counts.brokers,
        scenario_basis.counts.currencies,
        scenario_basis.counts.provenance,
    )
    if actual_counts != expected_counts:
        raise ValueError(f"{product} catalog and provenance counts must match the result rows")
    if scenario_basis.valuation_currency not in {row.currency for row in catalogs.currencies}:
        raise ValueError(f"{product} valuation currency must appear in the result catalog")
    _validate_scenario_basis_financials(product, scenario_basis)


def _validate_basis_solution(
    scenario_basis: PlannerScenarioBasis,
    solution: PacPlanSolution | RebalancerPlanSolution,
) -> None:
    accounting = solution.accounting
    for field in ("current_invested", "selected_funding", "reachable_funding", "trapped_funding", "fixed_reference"):
        if getattr(scenario_basis, field) != getattr(accounting, field):
            raise ValueError(f"Scenario basis and solution accounting disagree on {field}")
    if isinstance(scenario_basis, RebalancerScenarioBasis) and isinstance(solution, RebalancerPlanSolution) and scenario_basis.initial_wealth != solution.plan_accounts.initial_wealth:
        raise ValueError("Scenario basis and plan accounts disagree on the initial wealth")


def _named_tie_breaks(solution: PacPlanSolution | RebalancerPlanSolution | None) -> dict[str, str]:
    """The Rebalancer's named tie-breaks and how SCIP left them (``score.tie_breaks``); none for the PAC or without a plan."""
    if not isinstance(solution, RebalancerPlanSolution):
        return {}
    return {stage.objective_code: stage.status for stage in solution.score.tie_breaks}


def _validate_optimal_proof_objectives(
    proof: ReadyPlanProof | InfeasibilityProvenProof | None,
    solution: PacPlanSolution | RebalancerPlanSolution | None,
) -> None:
    """The witness covers every published stage in order; for the Rebalancer, the tie-breaks it left open are out of it (they
    do not downgrade the proof, specifica §15 n. 10)."""
    if not isinstance(proof, (OptimalProvenProof, RebalancerOptimalProvenProof)):
        return
    if solution is None:
        raise ValueError("optimal_proven requires a published primary solution")
    witness_codes = proof.witness.objective_codes
    named = _named_tie_breaks(solution)
    published_codes = [stage.objective_code for stage in solution.objectives.stages if named.get(stage.objective_code, "closed") == "closed"]
    if witness_codes != published_codes:
        raise ValueError("Optimal proof witness must cover every published objective stage in order")
    if isinstance(proof, OptimalProvenProof) and not proof.tie_break_closed:
        raise ValueError("Optimal proof witness must close the published canonical tie-break")


def _validate_solver_status_proof(
    proof: ReadyPlanProof | RebalancerReadyPlanProof | InfeasibilityProvenProof | None,
    solver_evidence: ReportedFloatingSolverEvidence,
    named_tie_breaks: dict[str, str] | None = None,
) -> None:
    """Bind a ``solver_status`` proof to the evidence of the solve it rests on.

    The proof is SCIP's own status (D-X1), so the evidence must show that
    status: an optimum needs every reported stage finished, on exactly the
    witness's objectives in order; an infeasibility needs the single first
    stage infeasible, on the witness's one objective. And conversely, an
    infeasible stage backs nothing but an infeasibility proof.
    """
    codes = [stage.objective_code for stage in solver_evidence.stages]
    infeasible = any(stage.status == "infeasible" for stage in solver_evidence.stages)
    if isinstance(proof, (OptimalProvenProof, RebalancerOptimalProvenProof)):
        # The Rebalancer: a tie-break may be left open; every other stage closed, and the witness names the closed ones.
        named = named_tie_breaks or {}
        if any(stage.status != "finished" and stage.objective_code not in named for stage in solver_evidence.stages):
            raise ValueError("optimal_proven requires every solver stage finished")
        if named:
            codes = [stage.objective_code for stage in solver_evidence.stages if stage.status == "finished"]
        if codes != proof.witness.objective_codes:
            raise ValueError("Optimal proof witness must name exactly the finished solver stages in order")
    elif isinstance(proof, InfeasibilityProvenProof):
        if not infeasible:
            raise ValueError("infeasibility_proven requires an infeasible first solver stage")
        if codes != proof.witness.objective_codes:
            raise ValueError("Infeasibility proof witness must name the infeasible solver stage")
    elif infeasible:
        raise ValueError("An infeasible solver stage requires an infeasibility proof")


def _validate_tie_break_statuses(solution: RebalancerPlanSolution, solver_evidence: ReportedFloatingSolverEvidence) -> None:
    """``score.tie_breaks`` names the published stages after the score (or the chain), each once, then ``canonical``; a named
    one is ``closed`` exactly when its solver stage finished, so a «rejected» one matches an unfinished stage, never a finished
    stage carrying the bounds of a plan that is not published."""
    principal = {"plan_score", "target_distance", "wealth_loss"}
    published = [stage.objective_code for stage in solution.objectives.stages if stage.objective_code not in principal] + ["canonical"]
    if [stage.objective_code for stage in solution.score.tie_breaks] != published:
        raise ValueError("The score's tie-breaks must name the published tie-break stages in order")
    evidence = {stage.objective_code: stage.status for stage in solver_evidence.stages}
    for stage in solution.score.tie_breaks:
        if stage.objective_code in evidence and (stage.status == "closed") != (evidence[stage.objective_code] == "finished"):
            raise ValueError("A tie-break is closed exactly when its solver stage finished")


def _validate_rebalancer_policy_solution(
    policy: str,
    solution: RebalancerPlanSolution,
) -> None:
    sells = [row for row in solution.order_rows if isinstance(row, PlannerSellOrderRow)]
    if policy == "invest_only" and sells:
        raise ValueError("invest_only results cannot contain SELL orders")
    if not sells and (solution.tax_basket_rows or solution.tax_scope_rows or solution.tax_reserves or solution.asset_type_tax_rows):
        raise ValueError("A plan that sells nothing publishes empty tax parts")


def _validate_solver_units(
    solver_evidence: ReportedFloatingSolverEvidence,
    valuation_currency: CurrencyCode,
) -> None:
    if any(stage.unit.kind in {"valuation_money", "valuation_money_squared"} and stage.unit.currency_code != valuation_currency for stage in solver_evidence.stages):
        raise ValueError("Solver valuation units must use the scenario valuation currency")


def _validate_stage_order(solver_evidence: ReportedFloatingSolverEvidence, named_tie_breaks: dict[str, str] | None = None) -> None:
    """Finished solver stages precede unfinished ones, except a Rebalancer tie-break whose plan the exact comparison
    rejected (D4; lot CR of project 67). SCIP closed that stage, the solver reports it unfinished, and the cascade goes on, so
    a later stage may finish after it: a legitimate state, which ``score.tie_breaks`` names (``rejected``). Every other
    unfinished stage before a finished one is still refused. A rejection cannot happen in the tail, so a rejected row never
    follows an unfinished row that is not itself rejected (the consultant's invariant). An infeasible stage is alone (the
    evidence's own rule)."""
    rejected = {code for code, status in (named_tie_breaks or {}).items() if status == "rejected"}
    # D4 rejects only outside the tail: a rejected tie-break never follows a stage a limit left unfinished.
    left_open = False
    for stage in solver_evidence.stages:
        if stage.objective_code in rejected and left_open:
            raise ValueError("A rejected tie-break cannot follow a stage a limit left unfinished")
        left_open = left_open or (stage.status == "unfinished" and stage.objective_code not in rejected)
    statuses = [stage.status for stage in solver_evidence.stages if stage.objective_code not in rejected]
    if "infeasible" in statuses:
        return
    if statuses != sorted(statuses, key={"finished": 0, "unfinished": 1}.__getitem__):
        raise ValueError("Finished solver stages must precede unfinished stages")


def _validate_stop_evidence(
    stop_reason: str,
    solver_evidence: ReportedFloatingSolverEvidence,
    named_tie_breaks: dict[str, str] | None = None,
) -> None:
    # An infeasible stage is a verdict, not an interruption: it ends a completed search. So is a Rebalancer tie-break whose
    # plan the exact comparison rejected (D4): SCIP closed it, no limit stopped the search there.
    named = named_tie_breaks or {}
    rejected = {code for code, status in named.items() if status == "rejected"}
    # The canonical vector has no evidence row: when a limit left it open, its entry in the score says so.
    unfinished = any(stage.status == "unfinished" and stage.objective_code not in rejected for stage in solver_evidence.stages) or named.get("canonical") == "unfinished"
    if (stop_reason == "completed") == unfinished:
        raise ValueError("Completed stops require no unfinished stage; limit stops require an unfinished stage")


type PacDeployment = Annotated[
    Union[DeploymentUnavailable, DeploymentCoincident, PacDistinctDeployment],
    Field(discriminator="kind"),
]
type RebalancerDeployment = Annotated[
    Union[DeploymentUnavailable, DeploymentCoincident, RebalancerDistinctDeployment],
    Field(discriminator="kind"),
]


class PlannerResultSnapshot(AllocationStrictModel):
    snapshot_id: PlannerId
    request_fingerprint: PlannerRef | Literal[""] = Field(
        description="External request correlation: on a ready result the scenario fingerprint, emitted only after internal view and scenario-fingerprint verification; empty on needs_input, invalid and unsupported, which have no exact scenario and never carry the snapshot identifier in its place."
    )


class PacScenarioBasis(PlannerScenarioBasis):
    policy: Literal["proportional"]


class RebalancerScenarioBasis(PlannerScenarioBasis):
    """The PAC's basis plus what the Rebalancer adds (contract §6.1): the target fidelity of the request and ``F``."""

    policy: Literal["invest_only", "invest_and_sell"]
    target_fidelity: RebalancerFidelityInput
    initial_wealth: ExactMoney = Field(description="F: the current invested value plus every selected cash and contribution, in the valuation currency; the reference of every weight.")


class _PlannerFailureResultBase(AllocationStrictModel):
    operation: Literal["plan"]
    snapshot: PlannerResultSnapshot
    issues: Annotated[list[PlannerIssue], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_controlling_issue(self) -> _PlannerFailureResultBase:
        availability = getattr(self, "availability", None)
        if availability not in {"needs_input", "invalid", "unsupported"}:
            raise ValueError("Failure result must declare a failure availability")
        required_kind = "missing" if availability == "needs_input" else availability
        if not any(issue.kind == required_kind and issue.severity == "error" for issue in self.issues):
            raise ValueError("Failure result must include an error issue matching its availability")
        return self


class PacPlannerNeedsInputResult(_PlannerFailureResultBase):
    result_state: Literal["needs_input"]
    availability: Literal["needs_input"]


class PacPlannerInvalidResult(_PlannerFailureResultBase):
    result_state: Literal["invalid"]
    availability: Literal["invalid"]


class PacPlannerUnsupportedResult(_PlannerFailureResultBase):
    result_state: Literal["unsupported"]
    availability: Literal["unsupported"]


class RebalancerPlannerNeedsInputResult(_PlannerFailureResultBase):
    result_state: Literal["needs_input"]
    availability: Literal["needs_input"]


class RebalancerPlannerInvalidResult(_PlannerFailureResultBase):
    result_state: Literal["invalid"]
    availability: Literal["invalid"]


class RebalancerPlannerUnsupportedResult(_PlannerFailureResultBase):
    result_state: Literal["unsupported"]
    availability: Literal["unsupported"]


class _PacReadyResultBase(AllocationStrictModel):
    operation: Literal["plan"]
    availability: Literal["ready"]
    snapshot: PlannerResultSnapshot
    catalogs: PlannerCatalogs
    provenance: Annotated[list[PlannerProvenance], Field(min_length=1)]
    scenario_basis: PacScenarioBasis
    stop_reason: Literal["completed", "time_limit", "node_limit"]
    solver_evidence: ReportedFloatingSolverEvidence
    issues: list[PlannerIssue]

    @model_validator(mode="after")
    def validate_gap_evidence(self) -> _PacReadyResultBase:
        if any(issue.severity == "error" for issue in self.issues):
            raise ValueError("Ready results cannot contain error-severity issues")
        _validate_result_catalogs("PAC", self.catalogs, self.provenance, self.scenario_basis)
        proof = getattr(self, "proof", None)
        deployment = getattr(self, "deployment", None)
        solution = getattr(self, "primary_solution", None)
        _validate_stage_order(self.solver_evidence)
        _validate_stop_evidence(self.stop_reason, self.solver_evidence)
        _validate_solver_units(self.solver_evidence, self.scenario_basis.valuation_currency)
        _validate_optimal_proof_objectives(proof, solution)
        _validate_solver_status_proof(proof, self.solver_evidence)
        if solution is not None:
            _validate_basis_solution(self.scenario_basis, solution)
            _validate_ready_solution(self.catalogs, self.provenance, self.scenario_basis.valuation_currency, solution)
        if isinstance(deployment, PacDistinctDeployment) and solution is not None:
            _validate_basis_solution(self.scenario_basis, deployment.solution)
            _validate_ready_solution(self.catalogs, self.provenance, self.scenario_basis.valuation_currency, deployment.solution)
            _validate_distinct_deployment(solution, deployment)
        return self


class PacPlannerReadyNoOpResult(_PacReadyResultBase):
    result_state: Literal["ready_no_op"]
    outcome: Literal["no_op"]
    proof: ReadyPlanProof
    primary_solution: PacNoOpSolution
    deployment: PacDeployment


class PacPlannerReadyIncumbentResult(_PacReadyResultBase):
    result_state: Literal["ready_incumbent"]
    outcome: Literal["incumbent_found"]
    proof: ReadyPlanProof
    primary_solution: PacIncumbentSolution
    deployment: PacDeployment


class PacPlannerReadyInfeasibleResult(_PacReadyResultBase):
    result_state: Literal["ready_infeasible"]
    outcome: Literal["infeasible_proven"]
    proof: InfeasibilityProvenProof
    stop_reason: Literal["completed"]


class PacPlannerReadyNoIncumbentResult(_PacReadyResultBase):
    result_state: Literal["ready_no_incumbent"]
    outcome: Literal["no_incumbent"]
    proof: NotProvenProof
    # A completed search always holds a plan: the replay publishes it with its
    # rounding top-ups or raises. "No plan" is only a limit stop (QX1-b).
    stop_reason: Literal["time_limit", "node_limit"]


class _RebalancerReadyResultBase(AllocationStrictModel):
    operation: Literal["plan"]
    availability: Literal["ready"]
    snapshot: PlannerResultSnapshot
    catalogs: PlannerCatalogs
    provenance: Annotated[list[PlannerProvenance], Field(min_length=1)]
    scenario_basis: RebalancerScenarioBasis
    stop_reason: Literal["completed", "time_limit", "node_limit"]
    solver_evidence: ReportedFloatingSolverEvidence
    issues: list[PlannerIssue]

    @model_validator(mode="after")
    def validate_gap_evidence(self) -> _RebalancerReadyResultBase:
        if any(issue.severity == "error" for issue in self.issues):
            raise ValueError("Ready results cannot contain error-severity issues")
        _validate_result_catalogs("Rebalancer", self.catalogs, self.provenance, self.scenario_basis)
        proof = getattr(self, "proof", None)
        deployment = getattr(self, "deployment", None)
        solution = getattr(self, "primary_solution", None)
        named = _named_tie_breaks(solution)
        _validate_stage_order(self.solver_evidence, named)
        _validate_stop_evidence(self.stop_reason, self.solver_evidence, named)
        _validate_solver_units(self.solver_evidence, self.scenario_basis.valuation_currency)
        _validate_optimal_proof_objectives(proof, solution)
        _validate_solver_status_proof(proof, self.solver_evidence, named)
        if solution is not None:
            _validate_basis_solution(self.scenario_basis, solution)
            _validate_ready_solution(self.catalogs, self.provenance, self.scenario_basis.valuation_currency, solution)
            _validate_rebalancer_policy_solution(self.scenario_basis.policy, solution)
            _validate_tie_break_statuses(solution, self.solver_evidence)
        if isinstance(deployment, RebalancerDistinctDeployment) and solution is not None:
            _validate_basis_solution(self.scenario_basis, deployment.solution)
            _validate_ready_solution(self.catalogs, self.provenance, self.scenario_basis.valuation_currency, deployment.solution)
            _validate_rebalancer_policy_solution(self.scenario_basis.policy, deployment.solution)
            _validate_distinct_deployment(solution, deployment)
        return self


class RebalancerPlannerReadyNoOpResult(_RebalancerReadyResultBase):
    result_state: Literal["ready_no_op"]
    outcome: Literal["no_op"]
    proof: RebalancerReadyPlanProof
    primary_solution: RebalancerNoOpSolution
    deployment: RebalancerDeployment


class RebalancerPlannerReadyIncumbentResult(_RebalancerReadyResultBase):
    result_state: Literal["ready_incumbent"]
    outcome: Literal["incumbent_found"]
    proof: RebalancerReadyPlanProof
    primary_solution: RebalancerIncumbentSolution
    deployment: RebalancerDeployment


class RebalancerPlannerReadyInfeasibleResult(_RebalancerReadyResultBase):
    result_state: Literal["ready_infeasible"]
    outcome: Literal["infeasible_proven"]
    proof: InfeasibilityProvenProof
    stop_reason: Literal["completed"]


class RebalancerPlannerReadyNoIncumbentResult(_RebalancerReadyResultBase):
    result_state: Literal["ready_no_incumbent"]
    outcome: Literal["no_incumbent"]
    proof: NotProvenProof
    stop_reason: Literal["time_limit", "node_limit"]


type PacPlannerResult = Annotated[
    Union[
        PacPlannerNeedsInputResult,
        PacPlannerInvalidResult,
        PacPlannerUnsupportedResult,
        PacPlannerReadyNoOpResult,
        PacPlannerReadyIncumbentResult,
        PacPlannerReadyInfeasibleResult,
        PacPlannerReadyNoIncumbentResult,
    ],
    Field(discriminator="result_state"),
]
type RebalancerPlannerResult = Annotated[
    Union[
        RebalancerPlannerNeedsInputResult,
        RebalancerPlannerInvalidResult,
        RebalancerPlannerUnsupportedResult,
        RebalancerPlannerReadyNoOpResult,
        RebalancerPlannerReadyIncumbentResult,
        RebalancerPlannerReadyInfeasibleResult,
        RebalancerPlannerReadyNoIncumbentResult,
    ],
    Field(discriminator="result_state"),
]

PAC_PLAN_INPUT_ADAPTER = TypeAdapter(PacPlannerRequest)
PAC_PLAN_OUTPUT_ADAPTER = TypeAdapter(PacPlannerResult)
REBALANCER_PLAN_INPUT_ADAPTER = TypeAdapter(RebalancerPlannerRequest)
REBALANCER_PLAN_OUTPUT_ADAPTER = TypeAdapter(RebalancerPlannerResult)
