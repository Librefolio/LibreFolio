"""Plan solutions (PAC and Rebalancer: no-op, incumbent and deployment) and the deployment comparison, with the validators of a solution's own rows."""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from typing import Annotated, Literal

from pydantic import Field, model_validator

from backend.app.schemas.pac_allocator.base import AllocationStrictModel, DeploymentReasonCode, PlannerId, PlannerPositiveInteger, PlannerSafeInteger, require_unique
from backend.app.schemas.pac_allocator.evidence import NumericObjectiveUnit, ObjectiveCode, ObjectiveSense, objective_unit_kind
from backend.app.schemas.pac_allocator.exact import ExactNumber, exact_fraction, fixed_fraction, money_fraction
from backend.app.schemas.pac_allocator.rows import (
    PacAssetPlanRow,
    PacCashEntryRow,
    PacExposurePlanRow,
    PlannerAccountingSummary,
    PlannerBuyOrderRow,
    PlannerConversion,
    PlannerCostTotals,
    PlannerFundingAction,
    PlannerLedgerRow,
    PlannerObjectiveResults,
    PlannerPlanAccounts,
    PlannerRoundingTopUp,
    PlannerSellOrderRow,
    PlannerTransfer,
    RebalancerAssetPlanRow,
    RebalancerAssetTypeTaxRow,
    RebalancerCashItemRow,
    RebalancerExposurePlanRow,
    RebalancerOrderRow,
    RebalancerScoreSummary,
    RebalancerTaxBasketRow,
    RebalancerTaxReserveRow,
    RebalancerTaxScopeRow,
    RebalancerUninvestedRow,
)


def _validate_action_ids_and_sequences(solution: PacPlanSolution | RebalancerPlanSolution, label: str) -> None:
    """IDs unique across every action section; sequences unique across the sequenced ones.

    A manual conversion is a step of its own; an automatic one happens inside the orders, so it has no sequence.
    """
    # The PAC has no transfers (specification §15 n. 2); the Rebalancer's are numbered steps like its deposits.
    transfers = solution.transfers if isinstance(solution, RebalancerPlanSolution) else []
    ids = [
        *(row.action_id for row in solution.funding_actions),
        *(row.conversion_id for row in solution.conversions),
        *(row.transfer_id for row in transfers),
        *(row.order_id for row in solution.order_rows),
    ]
    require_unique(ids, f"{label} action IDs")
    sections = (
        [row.sequence for row in solution.funding_actions],
        [row.sequence for row in solution.conversions if row.sequence is not None],
        [row.sequence for row in transfers],
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


# The rounded postings an order can carry in its own pool: a BUY its debit and its fee; a SELL its credit, its fee, the
# foreign withholding and the tax.
_ROUNDED_POSTINGS_PER_ORDER = {"buy": 2, "sell": 4}


def _order_currency(row: PlannerBuyOrderRow | PlannerSellOrderRow) -> str:
    return row.cash_debit.currency if isinstance(row, PlannerBuyOrderRow) else row.gross_credit.currency


def _validate_rounding_top_ups(solution: PacPlanSolution | RebalancerPlanSolution, label: str) -> None:
    """Bind the top-ups to the ledger pools they excuse (both Tools, contract §6.5).

    One top-up per negative pool, for exactly the missing amount; its rounded
    postings can be no more than the pool's own rows carry: per order paying
    from the pool its postings (``_ROUNDED_POSTINGS_PER_ORDER``), a credit per
    conversion into it. It is only a cap: a fee that rounds to zero is not
    posted, and still counts in the order row. The minor-unit bound needs the
    catalogue, so it lives in ``_validate_ready_solution``.
    """
    require_unique([(row.broker_id, row.currency) for row in solution.rounding_top_ups], f"{label} rounding top-up scopes")
    deficits = {(row.broker_id, row.currency): -fixed_fraction(row.final_spendable) for row in solution.ledger_rows if fixed_fraction(row.final_spendable) < 0}
    if {(row.broker_id, row.currency): fixed_fraction(row.amount) for row in solution.rounding_top_ups} != deficits:
        raise ValueError(f"{label} rounding top-ups must cover exactly the negative ledger balances")
    for top_up in solution.rounding_top_ups:
        scope = (top_up.broker_id, top_up.currency)
        postings = sum(_ROUNDED_POSTINGS_PER_ORDER[row.kind] for row in solution.order_rows if (row.broker_id, _order_currency(row)) == scope)
        fx_credits = sum(1 for row in solution.conversions if (row.broker_id, row.destination_credit.currency) == scope)
        if top_up.rounded_postings > postings + fx_credits:
            raise ValueError(f"A {label} rounding top-up cannot count more rounded postings than its ledger scope carries")


def _validate_cash_by_currency(solution: PacPlanSolution | RebalancerPlanSolution, label: str) -> None:
    """Bind the cash at the end, currency by currency (TL-5 of project 67), to the ledger it reads: the spendable balances of
    a currency, every Broker summed, plus its contributions not deposited; a currency with no row ends with nothing."""
    spendable: dict[str, Fraction] = defaultdict(Fraction)
    for row in solution.ledger_rows:
        spendable[row.currency] += fixed_fraction(row.final_spendable)
    rows = {row.currency: row for row in solution.plan_accounts.cash_by_currency}
    for currency in {*spendable, *rows}:
        row = rows.get(currency)
        expected = spendable[currency] + (money_fraction(row.unused_contributions) if row is not None else Fraction())
        if expected != (money_fraction(row.final) if row is not None else Fraction()):
            raise ValueError(f"{label} cash at the end of a currency must be its ledger's spendable balance plus the contributions not deposited")
    accounts = solution.plan_accounts
    if money_fraction(accounts.final_cash) != money_fraction(accounts.final_wealth) - money_fraction(solution.accounting.final_invested):
        raise ValueError(f"{label} cash at the end must be the final wealth less the Assets after the plan")


class PacPlanSolution(AllocationStrictModel):
    solution_id: PlannerId
    solution_kind: Literal["primary"]
    validation: Literal["decimal_verified"]
    asset_rows: list[PacAssetPlanRow]
    cash_rows: list[PacCashEntryRow] = Field(description="One row per cash entry that carries a limit; empty when the request set none.")
    funding_actions: list[PlannerFundingAction]
    conversions: list[PlannerConversion] = Field(description="One conversion per Broker x ordered currency pair, the engine's own decision; manual ones are numbered steps.")
    order_rows: list[PlannerBuyOrderRow]
    ledger_rows: list[PlannerLedgerRow]
    rounding_top_ups: list[PlannerRoundingTopUp] = Field(description="One top-up per ledger pool left short by rounding against the plan; empty when every pool balances.")
    exposure_rows: list[PacExposurePlanRow]
    accounting: PlannerAccountingSummary
    costs: PlannerCostTotals
    plan_accounts: PlannerPlanAccounts = Field(description="The plan's accounts, the same for both Tools: the wealth before and after, the money lost by entry and what is left uninvested (contract §6.1).")
    objectives: PlannerObjectiveResults

    @model_validator(mode="after")
    def validate_authoritative_rows(self) -> PacPlanSolution:
        require_unique([row.asset_id for row in self.asset_rows], "PAC Asset rows")
        require_unique([(row.broker_id, row.currency) for row in self.cash_rows], "PAC cash entry rows")
        for row in [*self.asset_rows, *self.cash_rows]:
            if row.minimum is not None and row.maximum is not None and money_fraction(row.minimum) > money_fraction(row.maximum):
                raise ValueError("A row's minimum cannot exceed its maximum")
        _validate_action_ids_and_sequences(self, "PAC")
        _validate_conversions(self, "PAC")
        require_unique([(row.broker_id, row.currency) for row in self.ledger_rows], "PAC ledger scopes")
        require_unique([(row.dimension, row.category_id) for row in self.exposure_rows], "PAC exposure rows")
        _validate_rounding_top_ups(self, "PAC")
        _validate_cash_by_currency(self, "PAC")
        return self


class RebalancerPlanSolution(AllocationStrictModel):
    """A Rebalancer plan (contract §6): the items before, at their target and after (Asset rows, cash items, uninvested),
    the steps in one executable order (deposits, conversions, transfers, orders), the ledger with its rounding top-ups, the
    plan's accounts, the score and the tax parts. In «Invest only» the tax parts are empty."""

    solution_id: PlannerId
    solution_kind: Literal["primary"]
    validation: Literal["decimal_verified"]
    asset_rows: list[RebalancerAssetPlanRow]
    cash_rows: list[RebalancerCashItemRow] = Field(description="One row per cash item of the request (a weight or a limit on a Broker's cash in one currency).")
    uninvested_row: RebalancerUninvestedRow
    funding_actions: list[PlannerFundingAction]
    conversions: list[PlannerConversion] = Field(description="One conversion per Broker x ordered currency pair, the engine's own decision; manual ones are numbered steps.")
    transfers: list[PlannerTransfer] = Field(description="One transfer per lane the plan uses: from a Broker to another, in one currency.")
    order_rows: list[RebalancerOrderRow]
    ledger_rows: list[PlannerLedgerRow]
    rounding_top_ups: list[PlannerRoundingTopUp] = Field(description="One top-up per ledger pool left short by rounding against the plan; empty when every pool balances.")
    exposure_rows: list[RebalancerExposurePlanRow]
    accounting: PlannerAccountingSummary
    costs: PlannerCostTotals
    plan_accounts: PlannerPlanAccounts
    score: RebalancerScoreSummary
    tax_basket_rows: list[RebalancerTaxBasketRow] = Field(description="Per tax scope and basket; empty when the plan sells nothing.")
    tax_scope_rows: list[RebalancerTaxScopeRow] = Field(description="Per tax scope with a sale; empty when the plan sells nothing.")
    tax_reserves: list[RebalancerTaxReserveRow] = Field(description="Per Broker and currency where the plan sets tax aside; empty when nothing is set aside.")
    asset_type_tax_rows: list[RebalancerAssetTypeTaxRow] = Field(description="Per asset type with a sale; empty when the plan sells nothing.")
    objectives: PlannerObjectiveResults

    @model_validator(mode="after")
    def validate_authoritative_rows(self) -> RebalancerPlanSolution:
        require_unique([row.asset_id for row in self.asset_rows], "Rebalancer Asset rows")
        require_unique([(row.broker_id, row.currency) for row in self.cash_rows], "Rebalancer cash item rows")
        for row in [*self.asset_rows, *self.cash_rows]:
            if row.minimum is not None and row.maximum is not None and money_fraction(row.minimum) > money_fraction(row.maximum):
                raise ValueError("A row's minimum cannot exceed its maximum")
        _validate_action_ids_and_sequences(self, "Rebalancer")
        _validate_conversions(self, "Rebalancer")
        require_unique([(row.source_broker_id, row.destination_broker_id, row.amount.currency) for row in self.transfers], "Rebalancer transfer lanes")
        require_unique([(row.broker_id, row.currency) for row in self.ledger_rows], "Rebalancer ledger scopes")
        _validate_rounding_top_ups(self, "Rebalancer")
        _validate_cash_by_currency(self, "Rebalancer")
        require_unique([(row.dimension, row.kind, getattr(row, "category_id", "")) for row in self.exposure_rows], "Rebalancer exposure rows")
        require_unique([(row.scope.model_dump_json(), row.basket_id) for row in self.tax_basket_rows], "Rebalancer tax basket rows")
        require_unique([row.scope.model_dump_json() for row in self.tax_scope_rows], "Rebalancer tax scope rows")
        require_unique([(row.broker_id, row.amount.currency) for row in self.tax_reserves], "Rebalancer tax reserves")
        require_unique([row.asset_class or "" for row in self.asset_type_tax_rows], "Rebalancer asset type tax rows")
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
        "transfer_in",
        "transfer_out",
        "fx_debit",
        "fx_credit",
        "buy_debit",
        "gross_sell_credit",
        "buy_fees",
        "sell_fees",
        "broker_withheld_tax",
        "foreign_withholding_tax",
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
    if solution.rounding_top_ups:
        raise ValueError("No-op Rebalancer solutions have nothing to top up")
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
    # A plan of conversions or transfers alone is not «no operation» (contract §6.3).
    funding_actions: Annotated[list[PlannerFundingAction], Field(max_length=0)]
    conversions: Annotated[list[PlannerConversion], Field(max_length=0)]
    transfers: Annotated[list[PlannerTransfer], Field(max_length=0)]
    order_rows: Annotated[list[RebalancerOrderRow], Field(max_length=0)]

    @model_validator(mode="after")
    def validate_no_op_projection(self) -> RebalancerNoOpSolution:
        _validate_no_op_common(self)
        _validate_rebalancer_no_op(self)
        return self


class PacIncumbentSolution(PacPlanSolution):
    """A plan with at least one step: an order, a deposit or a conversion (contract §6.3 and §6.8). A plan that moves cash
    and buys nothing is a plan (the developer, 20/11/2026); none of the lists is required alone."""

    @model_validator(mode="after")
    def validate_has_a_step(self) -> PacIncumbentSolution:
        if not (self.order_rows or self.funding_actions or self.conversions):
            raise ValueError("A PAC plan with no step is a no-op solution")
        return self


class RebalancerIncumbentSolution(RebalancerPlanSolution):
    """A plan with at least one step: an order, a deposit, a conversion or a transfer (contract §6.3)."""

    @model_validator(mode="after")
    def validate_has_a_step(self) -> RebalancerIncumbentSolution:
        if not (self.order_rows or self.funding_actions or self.conversions or self.transfers):
            raise ValueError("A Rebalancer plan with no step is a no-op solution")
        return self


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
