"""Plan solutions (PAC and Rebalancer: no-op, incumbent and deployment) and the deployment comparison, with the validators of a solution's own rows."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from backend.app.schemas.pac_allocator.base import AllocationStrictModel, DeploymentReasonCode, PlannerId, PlannerPositiveInteger, PlannerSafeInteger, require_unique
from backend.app.schemas.pac_allocator.evidence import NumericObjectiveUnit, ObjectiveCode, ObjectiveSense, objective_unit_kind
from backend.app.schemas.pac_allocator.exact import ExactNumber, exact_fraction, fixed_fraction, money_fraction
from backend.app.schemas.pac_allocator.rows import (
    PacAssetPlanRow,
    PacExposurePlanRow,
    PlannerAccountingSummary,
    PlannerBuyOrderRow,
    PlannerConversion,
    PlannerCostTotals,
    PlannerFundingAction,
    PlannerLedgerRow,
    PlannerObjectiveResults,
    PlannerRoundingTopUp,
    PlannerSellOrderRow,
    RebalancerAssetPlanRow,
    RebalancerExposurePlanRow,
    RebalancerOrderRow,
    SellIrreducibilityEvidence,
)


def _validate_action_ids_and_sequences(solution: PacPlanSolution | RebalancerPlanSolution, label: str) -> None:
    """IDs unique across every action section; sequences unique across the sequenced ones.

    A manual conversion is a step of its own; an automatic one happens inside the orders, so it has no sequence.
    """
    ids = [
        *(row.action_id for row in solution.funding_actions),
        *(row.conversion_id for row in solution.conversions),
        *(row.order_id for row in solution.order_rows),
    ]
    require_unique(ids, f"{label} action IDs")
    sections = (
        [row.sequence for row in solution.funding_actions],
        [row.sequence for row in solution.conversions if row.sequence is not None],
        [row.sequence for row in solution.order_rows],
    )
    require_unique([sequence for section in sections for sequence in section], f"{label} action sequences")
    if any(section != sorted(section) for section in sections):
        raise ValueError(f"{label} action sections must be sequence-ordered")


def _validate_conversions(solution: PacPlanSolution | RebalancerPlanSolution, label: str) -> None:
    """The conversions are the engine's decisions: unique ids, one per Broker and ordered pair, one mode per Broker, and V7.

    V7: on a Broker a currency that receives a conversion gives none. A conversion into a currency followed by one out of it
    (EUR to USD then USD to CHF, or the same pair both ways) only burns cash through a relay, and the engine never plans one.
    """
    require_unique([row.conversion_id for row in solution.conversions], f"{label} conversion IDs")
    require_unique([(row.broker_id, row.source_debit.currency, row.destination_credit.currency) for row in solution.conversions], f"{label} conversion pairs")
    modes: dict[str, str] = {}
    if any(modes.setdefault(row.broker_id, row.mode) != row.mode for row in solution.conversions):
        raise ValueError(f"{label} conversions must use one mode per Broker")
    receiving = {(row.broker_id, row.destination_credit.currency) for row in solution.conversions}
    if any((row.broker_id, row.source_debit.currency) in receiving for row in solution.conversions):
        raise ValueError(f"{label} conversions: a currency that receives a conversion cannot give one at the same Broker")


def _validate_pac_rounding_top_ups(solution: PacPlanSolution) -> None:
    """Bind the top-ups to the ledger pools they excuse.

    One top-up per negative pool, for exactly the missing amount; its rounded
    postings can be no more than the pool's own rows carry: a BUY debit and a
    fee per order paying from the pool, a credit per conversion into it. It is
    only a cap: a fee that rounds to zero is not posted, and still counts in
    the order row. The minor-unit bound needs the catalogue, so it lives in
    ``_validate_ready_solution``.
    """
    require_unique([(row.broker_id, row.currency) for row in solution.rounding_top_ups], "PAC rounding top-up scopes")
    deficits = {(row.broker_id, row.currency): -fixed_fraction(row.final_spendable) for row in solution.ledger_rows if fixed_fraction(row.final_spendable) < 0}
    if {(row.broker_id, row.currency): fixed_fraction(row.amount) for row in solution.rounding_top_ups} != deficits:
        raise ValueError("PAC rounding top-ups must cover exactly the negative ledger balances")
    for top_up in solution.rounding_top_ups:
        scope = (top_up.broker_id, top_up.currency)
        orders = sum(1 for row in solution.order_rows if (row.broker_id, row.cash_debit.currency) == scope)
        fx_credits = sum(1 for row in solution.conversions if (row.broker_id, row.destination_credit.currency) == scope)
        if top_up.rounded_postings > 2 * orders + fx_credits:
            raise ValueError("A PAC rounding top-up cannot count more rounded postings than its ledger scope carries")


class PacPlanSolution(AllocationStrictModel):
    solution_id: PlannerId
    solution_kind: Literal["primary"]
    validation: Literal["decimal_verified"]
    asset_rows: list[PacAssetPlanRow]
    funding_actions: list[PlannerFundingAction]
    conversions: list[PlannerConversion] = Field(description="One conversion per Broker x ordered currency pair, the engine's own decision; manual ones are numbered steps.")
    order_rows: list[PlannerBuyOrderRow]
    ledger_rows: list[PlannerLedgerRow]
    rounding_top_ups: list[PlannerRoundingTopUp] = Field(description="One top-up per ledger pool left short by rounding against the plan; empty when every pool balances.")
    exposure_rows: list[PacExposurePlanRow]
    accounting: PlannerAccountingSummary
    costs: PlannerCostTotals
    objectives: PlannerObjectiveResults

    @model_validator(mode="after")
    def validate_authoritative_rows(self) -> PacPlanSolution:
        require_unique([row.asset_id for row in self.asset_rows], "PAC Asset rows")
        _validate_action_ids_and_sequences(self, "PAC")
        _validate_conversions(self, "PAC")
        require_unique([(row.broker_id, row.currency) for row in self.ledger_rows], "PAC ledger scopes")
        require_unique([(row.dimension, row.category_id) for row in self.exposure_rows], "PAC exposure rows")
        _validate_pac_rounding_top_ups(self)
        return self


class RebalancerPlanSolution(AllocationStrictModel):
    solution_id: PlannerId
    solution_kind: Literal["primary"]
    validation: Literal["decimal_verified"]
    asset_rows: list[RebalancerAssetPlanRow]
    funding_actions: list[PlannerFundingAction]
    conversions: list[PlannerConversion] = Field(description="One conversion per Broker x ordered currency pair, the engine's own decision; manual ones are numbered steps.")
    order_rows: list[RebalancerOrderRow]
    sell_irreducibility: list[SellIrreducibilityEvidence]
    ledger_rows: list[PlannerLedgerRow]
    exposure_rows: list[RebalancerExposurePlanRow]
    accounting: PlannerAccountingSummary
    costs: PlannerCostTotals
    objectives: PlannerObjectiveResults

    @model_validator(mode="after")
    def validate_authoritative_rows(self) -> RebalancerPlanSolution:
        require_unique([row.asset_id for row in self.asset_rows], "Rebalancer Asset rows")
        _validate_action_ids_and_sequences(self, "Rebalancer")
        _validate_conversions(self, "Rebalancer")
        require_unique([(row.broker_id, row.currency) for row in self.ledger_rows], "Rebalancer ledger scopes")
        # The Rebalancer has no rounding top-ups, so no pool of it may end short.
        if any(fixed_fraction(row.final_spendable) < 0 or fixed_fraction(row.final_physical) < 0 for row in self.ledger_rows):
            raise ValueError("Rebalancer ledger balances cannot be negative")
        require_unique([(row.dimension, row.category_id) for row in self.exposure_rows], "Rebalancer exposure rows")
        require_unique([row.evidence_id for row in self.sell_irreducibility], "SELL evidence IDs")
        require_unique([row.order_id for row in self.sell_irreducibility], "SELL evidence order IDs")
        evidence = {row.evidence_id: row.order_id for row in self.sell_irreducibility}
        sell_orders = {row.order_id: row.irreducibility_evidence_ref for row in self.order_rows if isinstance(row, PlannerSellOrderRow)}
        if set(evidence.values()) != set(sell_orders):
            raise ValueError("SELL orders and irreducibility evidence must be one-to-one")
        if any(evidence.get(evidence_id) != order_id for order_id, evidence_id in sell_orders.items()):
            raise ValueError("SELL orders must reference their own irreducibility evidence")
        return self


def _validate_no_op_common(solution: PacPlanSolution | RebalancerPlanSolution) -> None:
    if any(money_fraction(getattr(solution.costs, name)) != 0 for name in type(solution.costs).model_fields):
        raise ValueError("No-op solutions cannot publish costs")
    accounting = solution.accounting
    if any(money_fraction(value) != 0 for value in (accounting.physical_reserves, accounting.economic_losses, accounting.rounding_delta)):
        raise ValueError("No-op solutions cannot publish new reserves, losses, or rounding")
    flow_fields = (
        "funding_in",
        "funding_out",
        "fx_debit",
        "fx_credit",
        "buy_debit",
        "gross_sell_credit",
        "buy_fees",
        "sell_fees",
        "broker_withheld_tax",
        "self_reserved_tax",
    )
    for row in solution.ledger_rows:
        if any(fixed_fraction(getattr(row, name)) != 0 for name in flow_fields) or exact_fraction(row.rounding_delta) != 0:
            raise ValueError("No-op ledger rows cannot contain action-derived postings")
        if fixed_fraction(row.final_spendable) != fixed_fraction(row.initial_selected) or fixed_fraction(row.final_physical) != fixed_fraction(row.initial_selected):
            raise ValueError("No-op ledger balances must preserve selected initial cash")


def _validate_pac_no_op(solution: PacPlanSolution) -> None:
    if money_fraction(solution.accounting.final_invested) != 0:
        raise ValueError("No-op PAC final invested value must be zero")
    if any(money_fraction(row.buy_mid_value) != 0 or money_fraction(row.final_value) != 0 for row in solution.asset_rows):
        raise ValueError("No-op PAC Asset projections cannot contain BUY value")


def _validate_rebalancer_no_op(solution: RebalancerPlanSolution) -> None:
    if money_fraction(solution.accounting.final_invested) != money_fraction(solution.accounting.current_invested):
        raise ValueError("No-op Rebalancer final invested value must equal its current value")
    if any(money_fraction(row.buy_mid_value) != 0 or money_fraction(row.sell_mid_value) != 0 or money_fraction(row.final_value) != money_fraction(row.before_value) for row in solution.asset_rows):
        raise ValueError("No-op Rebalancer Asset projections must preserve the current portfolio")


class PacNoOpSolution(PacPlanSolution):
    funding_actions: Annotated[list[PlannerFundingAction], Field(max_length=0)]
    conversions: Annotated[list[PlannerConversion], Field(max_length=0)]
    order_rows: Annotated[list[PlannerBuyOrderRow], Field(max_length=0)]
    rounding_top_ups: Annotated[list[PlannerRoundingTopUp], Field(max_length=0)]

    @model_validator(mode="after")
    def validate_no_op_projection(self) -> PacNoOpSolution:
        _validate_no_op_common(self)
        _validate_pac_no_op(self)
        return self


class RebalancerNoOpSolution(RebalancerPlanSolution):
    funding_actions: Annotated[list[PlannerFundingAction], Field(max_length=0)]
    conversions: Annotated[list[PlannerConversion], Field(max_length=0)]
    order_rows: Annotated[list[RebalancerOrderRow], Field(max_length=0)]
    sell_irreducibility: Annotated[list[SellIrreducibilityEvidence], Field(max_length=0)]

    @model_validator(mode="after")
    def validate_no_op_projection(self) -> RebalancerNoOpSolution:
        _validate_no_op_common(self)
        _validate_rebalancer_no_op(self)
        return self


class PacIncumbentSolution(PacPlanSolution):
    order_rows: Annotated[list[PlannerBuyOrderRow], Field(min_length=1)]


class RebalancerIncumbentSolution(RebalancerPlanSolution):
    order_rows: Annotated[list[RebalancerOrderRow], Field(min_length=1)]


class PacDeploymentSolution(PacPlanSolution):
    solution_kind: Literal["deployment"]


class RebalancerDeploymentSolution(RebalancerPlanSolution):
    solution_kind: Literal["deployment"]


class ObjectiveDelta(AllocationStrictModel):
    objective_code: ObjectiveCode
    ordinal: PlannerPositiveInteger
    sense: ObjectiveSense
    unit: NumericObjectiveUnit
    primary_value: ExactNumber
    deployment_value: ExactNumber
    delta: ExactNumber

    @model_validator(mode="after")
    def validate_objective_unit(self) -> ObjectiveDelta:
        if self.unit.kind != objective_unit_kind(self.objective_code):
            raise ValueError("Objective delta unit does not match objective code")
        return self


class DeploymentComparison(AllocationStrictModel):
    primary_solution_id: PlannerId
    deployment_solution_id: PlannerId
    changed_order_rows: PlannerSafeInteger
    objective_deltas: list[ObjectiveDelta]

    @model_validator(mode="after")
    def validate_objective_order(self) -> DeploymentComparison:
        ordinals = [delta.ordinal for delta in self.objective_deltas]
        codes = [delta.objective_code for delta in self.objective_deltas]
        if ordinals != sorted(ordinals) or len(ordinals) != len(set(ordinals)) or len(codes) != len(set(codes)):
            raise ValueError("Objective deltas must have unique codes and ascending ordinals")
        return self


class DeploymentUnavailable(AllocationStrictModel):
    kind: Literal["unavailable"]
    reason_code: DeploymentReasonCode


class DeploymentCoincident(AllocationStrictModel):
    kind: Literal["coincident"]
    reason_code: DeploymentReasonCode


class PacDistinctDeployment(AllocationStrictModel):
    kind: Literal["distinct"]
    solution: PacDeploymentSolution
    comparison: DeploymentComparison


class RebalancerDistinctDeployment(AllocationStrictModel):
    kind: Literal["distinct"]
    solution: RebalancerDeploymentSolution
    comparison: DeploymentComparison
