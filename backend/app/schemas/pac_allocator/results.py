"""Planner results (failure and ready, with their deployments), the cross-row validators of a ready result, and the input and output adapters of both Tools."""

from __future__ import annotations

from fractions import Fraction
from typing import Annotated, Literal, Union

from pydantic import Field, TypeAdapter, model_validator

from backend.app.schemas.pac_allocator.base import AllocationStrictModel, CurrencyCode, PlannerId, PlannerRef, collect_currency_codes, require_unique
from backend.app.schemas.pac_allocator.evidence import InfeasibilityProvenProof, NotProvenProof, OptimalProvenProof, ReadyPlanProof, ReportedFloatingSolverEvidence
from backend.app.schemas.pac_allocator.exact import ExactMoney, ExactNumberAvailability, available_fraction, exact_fraction, fixed_fraction, money_fraction, validate_weight_availability
from backend.app.schemas.pac_allocator.issues import PlannerIssue
from backend.app.schemas.pac_allocator.request import PacPlannerRequest, PlannerProvenance, RebalancerPlannerRequest
from backend.app.schemas.pac_allocator.rows import PacAssetPlanRow, PacExposurePlanRow, PlannerAccountingSummary, PlannerBuyOrderRow, PlannerCatalogs, PlannerScenarioBasis, PlannerSellOrderRow, RebalancerAssetPlanRow, RebalancerExposurePlanRow
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


def _validate_asset_row(row: PacAssetPlanRow | RebalancerAssetPlanRow) -> None:
    nonnegative_values = [row.target_value, row.final_value, row.buy_mid_value]
    if isinstance(row, RebalancerAssetPlanRow):
        nonnegative_values.extend([row.before_value, row.sell_mid_value])
    if any(money_fraction(value) < 0 for value in nonnegative_values):
        raise ValueError("Asset before, target, final, BUY, and SELL values cannot be negative")
    if money_fraction(row.residual) != money_fraction(row.final_value) - money_fraction(row.target_value):
        raise ValueError("Asset residual must equal final minus target value")
    if isinstance(row, RebalancerAssetPlanRow):
        expected_final = money_fraction(row.before_value) + money_fraction(row.buy_mid_value) - money_fraction(row.sell_mid_value)
    else:
        expected_final = money_fraction(row.buy_mid_value)
    if money_fraction(row.final_value) != expected_final:
        raise ValueError("Asset final value must reconcile before, BUY, and SELL values")


def _validate_target_weight_identities(
    rows: list[PacAssetPlanRow] | list[RebalancerAssetPlanRow],
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
    if isinstance(solution, RebalancerPlanSolution):
        if sum((money_fraction(row.before_value) for row in solution.asset_rows), Fraction()) != current_invested:
            raise ValueError("Rebalancer before values must sum to current invested value")
    elif current_invested != 0:
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
    if isinstance(solution, RebalancerPlanSolution):
        _validate_available_weight_identities(
            [row.before_weight for row in solution.asset_rows],
            [row.before_value for row in solution.asset_rows],
            current_invested,
            "zero_current_invested",
            "Before",
        )


def _validate_exposure_projection(solution: PacPlanSolution | RebalancerPlanSolution) -> None:
    dimensions: dict[str, list[PacExposurePlanRow | RebalancerExposurePlanRow]] = {}
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
        if isinstance(solution, RebalancerPlanSolution):
            validate_weight_availability(
                [row.before_weight for row in rows],
                money_fraction(solution.accounting.current_invested),
                "zero_current_invested",
                f"{dimension} before exposure",
            )


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
    valuation_money.extend(row.spread_loss for row in solution.fx_actions)
    valuation_money.extend(row.spread_loss for row in solution.conversions)
    valuation_money.extend(row.execution_margin_cost for row in solution.order_rows)
    valuation_money.extend(row.fx_cost for row in solution.order_rows if isinstance(row, PlannerBuyOrderRow))
    top_ups = solution.rounding_top_ups if isinstance(solution, PacPlanSolution) else []
    valuation_money.extend(row.valuation_amount for row in top_ups)
    if any(money.currency != valuation_currency for money in valuation_money):
        raise ValueError("Asset, accounting, and cost projections must use the valuation currency")
    if any(row.currency == valuation_currency and money_fraction(row.valuation_amount) != fixed_fraction(row.amount) for row in top_ups):
        raise ValueError("A PAC rounding top-up in the valuation currency must be valued at its own amount")
    if any(exact_fraction(getattr(solution.costs, name).value) < 0 for name in type(solution.costs).model_fields):
        raise ValueError("Cost totals cannot be negative")
    _validate_accounting_summary(solution.accounting, top_up_value=sum((money_fraction(row.valuation_amount) for row in top_ups), Fraction()))
    if isinstance(solution, RebalancerPlanSolution) and money_fraction(solution.accounting.final_invested) <= 0:
        raise ValueError("Ready Rebalancer solutions require positive final invested value")
    _validate_asset_projection(solution)
    _validate_exposure_projection(solution)
    if any(stage.unit.kind in {"valuation_money", "valuation_money_squared"} and stage.unit.currency_code != valuation_currency for stage in solution.objectives.stages):
        raise ValueError("Valuation objective units must use the scenario valuation currency")
    if any(stage.objective_code == "shortfall" and exact_fraction(stage.value) != money_fraction(solution.accounting.shortfall) for stage in solution.objectives.stages):
        raise ValueError("The shortfall objective must equal the authoritative accounting shortfall")


def _validate_pac_top_up_minor_units(
    catalogs: PlannerCatalogs,
    solution: PacPlanSolution | RebalancerPlanSolution,
) -> None:
    """``amount <= rounded_postings x minor unit``: the one top-up bound that needs the catalogue."""
    if not isinstance(solution, PacPlanSolution):
        return
    minor_units = {row.currency: fixed_fraction(row.minor_unit) for row in catalogs.currencies}
    if any(fixed_fraction(row.amount) > row.rounded_postings * minor_units[row.currency] for row in solution.rounding_top_ups):
        raise ValueError("A PAC rounding top-up cannot exceed its rounded postings times the currency minor unit")


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
    if any(row.destination_broker_id not in broker_ids for row in solution.funding_actions):
        raise ValueError("Funding rows must reference catalog Broker IDs")
    if any(row.broker_id not in broker_ids for row in solution.fx_actions):
        raise ValueError("FX rows must reference catalog Broker IDs")
    if any(row.asset_id not in asset_ids or row.broker_id not in broker_ids for row in solution.order_rows):
        raise ValueError("Order rows must reference catalog Asset and Broker IDs")
    if not collect_currency_codes(solution.model_dump(mode="python")) <= currencies:
        raise ValueError("Solution rows must reference catalog currencies")
    _validate_pac_top_up_minor_units(catalogs, solution)
    referenced_provenance = {provenance_id for row in [*solution.funding_actions, *solution.fx_actions, *solution.conversions, *solution.order_rows, *solution.exposure_rows] for provenance_id in row.provenance_ids}
    if not referenced_provenance <= provenance_ids:
        raise ValueError("Solution rows must reference top-level provenance IDs")
    for row in [*solution.funding_actions, *solution.fx_actions, *solution.conversions, *solution.order_rows, *solution.exposure_rows]:
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


def _validate_optimal_proof_objectives(
    proof: ReadyPlanProof | InfeasibilityProvenProof | None,
    solution: PacPlanSolution | RebalancerPlanSolution | None,
) -> None:
    if not isinstance(proof, OptimalProvenProof):
        return
    if solution is None:
        raise ValueError("optimal_proven requires a published primary solution")
    witness_codes = proof.witness.objective_codes
    published_codes = [stage.objective_code for stage in solution.objectives.stages]
    if witness_codes != published_codes:
        raise ValueError("Optimal proof witness must cover every published objective stage in order")
    if not proof.tie_break_closed:
        raise ValueError("Optimal proof witness must close the published canonical tie-break")


def _validate_not_proven_issue_binding(
    product: str,
    policy: str,
    proof: ReadyPlanProof | InfeasibilityProvenProof | None,
    issues: list[PlannerIssue],
) -> None:
    if not isinstance(proof, NotProvenProof) or proof.reason_code != "portfolio_rebalancer.sell_irreducibility_unresolved":
        return
    if product != "Rebalancer" or policy != "invest_and_sell":
        raise ValueError("SELL irreducibility reason is only valid for invest_and_sell")
    if not any(issue.code == proof.reason_code and issue.kind == "proof" and issue.severity == "warning" for issue in issues):
        raise ValueError("SELL irreducibility reason requires a matching warning proof issue")


def _validate_solver_status_proof(
    proof: ReadyPlanProof | InfeasibilityProvenProof | None,
    solver_evidence: ReportedFloatingSolverEvidence,
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
    if isinstance(proof, OptimalProvenProof):
        if any(stage.status != "finished" for stage in solver_evidence.stages):
            raise ValueError("optimal_proven requires every solver stage finished")
        if codes != proof.witness.objective_codes:
            raise ValueError("Optimal proof witness must name exactly the finished solver stages in order")
    elif isinstance(proof, InfeasibilityProvenProof):
        if not infeasible:
            raise ValueError("infeasibility_proven requires an infeasible first solver stage")
        if codes != proof.witness.objective_codes:
            raise ValueError("Infeasibility proof witness must name the infeasible solver stage")
    elif infeasible:
        raise ValueError("An infeasible solver stage requires an infeasibility proof")


def _validate_rebalancer_policy_solution(
    policy: str,
    solution: RebalancerPlanSolution,
) -> None:
    if policy != "invest_only":
        return
    if any(isinstance(row, PlannerSellOrderRow) for row in solution.order_rows):
        raise ValueError("invest_only results cannot contain SELL orders")
    if solution.sell_irreducibility:
        raise ValueError("invest_only results cannot contain SELL irreducibility evidence")


def _validate_solver_units(
    solver_evidence: ReportedFloatingSolverEvidence,
    valuation_currency: CurrencyCode,
) -> None:
    if any(stage.unit.kind in {"valuation_money", "valuation_money_squared"} and stage.unit.currency_code != valuation_currency for stage in solver_evidence.stages):
        raise ValueError("Solver valuation units must use the scenario valuation currency")


def _validate_stop_evidence(
    stop_reason: str,
    solver_evidence: ReportedFloatingSolverEvidence,
) -> None:
    # An infeasible stage is a verdict, not an interruption: it ends a completed search.
    unfinished = any(stage.status == "unfinished" for stage in solver_evidence.stages)
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
    request_fingerprint: PlannerRef = Field(description="External request correlation emitted only after internal view and scenario-fingerprint verification.")


class PacScenarioBasis(PlannerScenarioBasis):
    policy: Literal["proportional"]


class RebalancerScenarioBasis(PlannerScenarioBasis):
    policy: Literal["invest_only", "invest_and_sell"]


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
        _validate_stop_evidence(self.stop_reason, self.solver_evidence)
        _validate_solver_units(self.solver_evidence, self.scenario_basis.valuation_currency)
        _validate_not_proven_issue_binding("PAC", self.scenario_basis.policy, proof, self.issues)
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
        _validate_stop_evidence(self.stop_reason, self.solver_evidence)
        _validate_solver_units(self.solver_evidence, self.scenario_basis.valuation_currency)
        _validate_not_proven_issue_binding("Rebalancer", self.scenario_basis.policy, proof, self.issues)
        _validate_optimal_proof_objectives(proof, solution)
        _validate_solver_status_proof(proof, self.solver_evidence)
        if solution is not None:
            _validate_basis_solution(self.scenario_basis, solution)
            _validate_ready_solution(self.catalogs, self.provenance, self.scenario_basis.valuation_currency, solution)
            _validate_rebalancer_policy_solution(self.scenario_basis.policy, solution)
        if isinstance(deployment, RebalancerDistinctDeployment) and solution is not None:
            _validate_basis_solution(self.scenario_basis, deployment.solution)
            _validate_ready_solution(self.catalogs, self.provenance, self.scenario_basis.valuation_currency, deployment.solution)
            _validate_rebalancer_policy_solution(self.scenario_basis.policy, deployment.solution)
            _validate_distinct_deployment(solution, deployment)
        return self


class RebalancerPlannerReadyNoOpResult(_RebalancerReadyResultBase):
    result_state: Literal["ready_no_op"]
    outcome: Literal["no_op"]
    proof: ReadyPlanProof
    primary_solution: RebalancerNoOpSolution
    deployment: RebalancerDeployment


class RebalancerPlannerReadyIncumbentResult(_RebalancerReadyResultBase):
    result_state: Literal["ready_incumbent"]
    outcome: Literal["incumbent_found"]
    proof: ReadyPlanProof
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
