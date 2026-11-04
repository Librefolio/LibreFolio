"""Rows of a planner result: catalogs, scenario basis, asset and exposure rows, funding, FX and conversion actions, order rows, ledger, rounding top-ups, accounting, costs and objective results."""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from backend.app.schemas.pac_allocator.base import (
    AllocationStrictModel,
    CurrencyCode,
    FundingActionReasonCode,
    PlannerCode,
    PlannerConversionMode,
    PlannerFixedDecimal,
    PlannerId,
    PlannerIssueCode,
    PlannerLabel,
    PlannerMessageKey,
    PlannerNonNegativeMoneyInput,
    PlannerPositiveDecimal,
    PlannerPositiveInteger,
    PlannerPositiveMoneyInput,
    PlannerPositiveWholeDecimal,
    PlannerSafeInteger,
    QuantityUnit,
    ReferenceDate,
    require_unique,
)
from backend.app.schemas.pac_allocator.evidence import OBJECTIVE_SIGN_DOMAINS, CanonicalKeyUnit, NumericObjectiveUnit, ObjectiveCode, ObjectiveSense, objective_unit_kind
from backend.app.schemas.pac_allocator.exact import ExactFxRate, ExactMoney, ExactNumber, ExactNumberAvailability, ExactPrice, ExactRatio, available_fraction, exact_fraction, fixed_fraction, money_fraction
from backend.app.schemas.pac_allocator.request import CurrencySpec, PlannerFundingSourceRef


class PlannerCatalogAsset(AllocationStrictModel):
    asset_id: PlannerId
    name: PlannerLabel
    ticker: PlannerLabel | None
    asset_class: PlannerCode | None


class PlannerCatalogBroker(AllocationStrictModel):
    broker_id: PlannerId
    name: PlannerLabel


class PlannerCatalogs(AllocationStrictModel):
    assets: list[PlannerCatalogAsset]
    brokers: list[PlannerCatalogBroker]
    currencies: list[CurrencySpec]

    @model_validator(mode="after")
    def validate_catalog_ids(self) -> PlannerCatalogs:
        require_unique([asset.asset_id for asset in self.assets], "Catalog Asset IDs")
        require_unique([broker.broker_id for broker in self.brokers], "Catalog Broker IDs")
        require_unique([currency.currency for currency in self.currencies], "Catalog currencies")
        if any(fixed_fraction(currency.minor_unit) <= 0 for currency in self.currencies):
            raise ValueError("Published currency minor units must be positive")
        return self


class PlannerScenarioCounts(AllocationStrictModel):
    assets: PlannerSafeInteger
    brokers: PlannerSafeInteger
    currencies: PlannerSafeInteger
    holdings: PlannerSafeInteger
    existing_cash: PlannerSafeInteger
    contributions: PlannerSafeInteger
    funding_routes: PlannerSafeInteger
    capabilities: PlannerSafeInteger
    fx_rates: PlannerSafeInteger
    order_routes: PlannerSafeInteger
    provenance: PlannerSafeInteger


class PlannerScenarioBasis(AllocationStrictModel):
    as_of: ReferenceDate
    valuation_currency: CurrencyCode
    policy: Literal["proportional", "invest_only", "invest_and_sell"]
    counts: PlannerScenarioCounts
    current_invested: ExactMoney
    selected_funding: ExactMoney
    reachable_funding: ExactMoney
    trapped_funding: ExactMoney
    fixed_reference: ExactMoney


class PacAssetPlanRow(AllocationStrictModel):
    asset_id: PlannerId
    target_weight: ExactNumber
    target_value: ExactMoney
    final_value: ExactMoney
    residual: ExactMoney
    final_weight: ExactNumberAvailability
    buy_mid_value: ExactMoney


class RebalancerAssetPlanRow(AllocationStrictModel):
    asset_id: PlannerId
    before_value: ExactMoney
    target_weight: ExactNumber
    target_value: ExactMoney
    final_value: ExactMoney
    residual: ExactMoney
    before_weight: ExactNumberAvailability
    final_weight: ExactNumberAvailability
    buy_mid_value: ExactMoney
    sell_mid_value: ExactMoney


class PlannerFundingAction(AllocationStrictModel):
    action_id: PlannerId
    sequence: PlannerPositiveInteger
    funding_route_id: PlannerId
    source: PlannerFundingSourceRef
    destination_broker_id: PlannerId
    amount: PlannerPositiveMoneyInput
    reason_code: FundingActionReasonCode
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]


class PlannerFxAction(AllocationStrictModel):
    action_id: PlannerId
    conversion_id: PlannerId = Field(description="The Broker x currency-pair conversion this engine decision belongs to; the conversion, not the action, is what gets executed.")
    order_route_id: PlannerId = Field(description="Key of the engine decision. The credit is pooled in the Broker's cash in the destination currency and funds every order of that Broker in that currency, so this is not the order the conversion pays for.")
    broker_id: PlannerId
    source_debit: PlannerPositiveMoneyInput
    destination_credit: PlannerPositiveMoneyInput
    spot_rate: ExactFxRate
    effective_rate: ExactFxRate
    spread_loss: ExactMoney
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_action_rates_and_costs(self) -> PlannerFxAction:
        if (self.spot_rate.source_currency, self.spot_rate.destination_currency) != (
            self.source_debit.currency,
            self.destination_credit.currency,
        ):
            raise ValueError("FX action rates must follow the posted source-to-destination direction")
        if (self.effective_rate.source_currency, self.effective_rate.destination_currency) != (
            self.source_debit.currency,
            self.destination_credit.currency,
        ):
            raise ValueError("Effective FX rate must follow the posted source-to-destination direction")
        if exact_fraction(self.effective_rate.value) > exact_fraction(self.spot_rate.value):
            raise ValueError("Effective FX rate cannot exceed the approved spot rate")
        if exact_fraction(self.spread_loss.value) < 0:
            raise ValueError("FX spread loss cannot be negative")
        return self


class PlannerConversion(AllocationStrictModel):
    """One currency conversion per Broker and currency pair, aggregated from the engine's FX actions.

    The engine decides FX per order route, but the credit lands in a cash pool that every
    order of that Broker in that currency shares, so only the pair total is a fact of the
    plan. ``source_debit`` and ``spread_loss`` sum the exact action figures;
    ``destination_credit`` sums the posted credits the ledger reconciles against.
    """

    conversion_id: PlannerId
    mode: PlannerConversionMode
    sequence: PlannerPositiveInteger | None = Field(description="Execution step of a manual conversion; null when the Broker converts automatically at order time.")
    broker_id: PlannerId
    source_debit: PlannerPositiveMoneyInput
    destination_credit: PlannerPositiveMoneyInput
    spot_rate: ExactFxRate
    effective_rate: ExactFxRate
    spread_loss: ExactMoney
    fx_action_ids: Annotated[list[PlannerId], Field(min_length=1)]
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_conversion(self) -> PlannerConversion:
        if (self.sequence is None) != (self.mode == "automatic"):
            raise ValueError("A conversion has an execution sequence exactly when it is manual")
        for rate in (self.spot_rate, self.effective_rate):
            if (rate.source_currency, rate.destination_currency) != (self.source_debit.currency, self.destination_credit.currency):
                raise ValueError("Conversion rates must follow the source-to-destination direction")
        if exact_fraction(self.effective_rate.value) > exact_fraction(self.spot_rate.value):
            raise ValueError("Effective conversion rate cannot exceed the approved spot rate")
        if exact_fraction(self.spread_loss.value) < 0:
            raise ValueError("Conversion spread loss cannot be negative")
        require_unique(self.fx_action_ids, "Conversion FX action IDs")
        return self


class WholeQuantityInstruction(AllocationStrictModel):
    kind: Literal["whole_quantity"]
    quantity: PlannerPositiveWholeDecimal
    quantity_step: PlannerPositiveWholeDecimal
    unit: QuantityUnit


class MonetaryAmountInstruction(AllocationStrictModel):
    kind: Literal["monetary_amount"]
    amount: PlannerPositiveMoneyInput
    order_amount_step: PlannerPositiveMoneyInput


type PlannerOrderInstruction = Annotated[
    Union[WholeQuantityInstruction, MonetaryAmountInstruction],
    Field(discriminator="kind"),
]


class ExactEconomicQuantity(AllocationStrictModel):
    kind: Literal["exact"]
    value: ExactNumber
    unit: QuantityUnit

    @model_validator(mode="after")
    def validate_positive_value(self) -> ExactEconomicQuantity:
        if exact_fraction(self.value) <= 0:
            raise ValueError("Order economic quantity must be positive")
        return self


class EstimatedExactRatioQuantity(AllocationStrictModel):
    kind: Literal["estimated_exact_ratio"]
    value: ExactRatio
    unit: QuantityUnit

    @model_validator(mode="after")
    def validate_positive_value(self) -> EstimatedExactRatioQuantity:
        if exact_fraction(self.value) <= 0:
            raise ValueError("Estimated order economic quantity must be positive")
        return self


type PlannerEconomicQuantity = Annotated[
    Union[ExactEconomicQuantity, EstimatedExactRatioQuantity],
    Field(discriminator="kind"),
]


class PlannerBuyOrderRow(AllocationStrictModel):
    kind: Literal["buy"]
    order_id: PlannerId
    sequence: PlannerPositiveInteger
    asset_id: PlannerId
    broker_id: PlannerId
    route_id: PlannerId
    instruction: PlannerOrderInstruction
    economic_quantity: PlannerEconomicQuantity
    source_price: ExactPrice
    mid_price: ExactPrice
    charge_price: ExactPrice
    mid_value: ExactMoney
    execution_margin_cost: ExactMoney
    cash_debit: PlannerPositiveMoneyInput
    fee: PlannerNonNegativeMoneyInput
    fx_cost: ExactMoney = Field(description="Always zero: a conversion funds a shared Broker x currency cash pool, so its spread is published on the conversion, not attributed to one order.")
    buffer: PlannerNonNegativeMoneyInput
    explanation_keys: list[PlannerMessageKey]
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_order_values(self) -> PlannerBuyOrderRow:
        price_currencies = {self.source_price.currency, self.mid_price.currency, self.charge_price.currency}
        if price_currencies != {self.cash_debit.currency}:
            raise ValueError("BUY prices and cash debit must use one order currency")
        if len({self.source_price.quote_base_quantity, self.mid_price.quote_base_quantity, self.charge_price.quote_base_quantity}) != 1:
            raise ValueError("BUY prices must use one quote base quantity")
        if exact_fraction(self.charge_price.value) < exact_fraction(self.mid_price.value):
            raise ValueError("BUY charge price cannot be below mid price")
        if self.fee.currency != self.cash_debit.currency or self.buffer.currency != self.cash_debit.currency:
            raise ValueError("BUY fee and buffer must use the order currency")
        if isinstance(self.instruction, MonetaryAmountInstruction):
            if {self.instruction.amount.currency, self.instruction.order_amount_step.currency} != {self.cash_debit.currency}:
                raise ValueError("Monetary BUY instruction must use the order currency")
        if exact_fraction(self.mid_value.value) <= 0:
            raise ValueError("BUY mid value must be positive")
        if exact_fraction(self.execution_margin_cost.value) < 0:
            raise ValueError("BUY execution-margin cost cannot be negative")
        if exact_fraction(self.fx_cost.value) != 0:
            raise ValueError("BUY FX cost must be zero: conversion spreads are published on the conversion")
        return self


class PlannerSellOrderRow(AllocationStrictModel):
    kind: Literal["sell"]
    order_id: PlannerId
    sequence: PlannerPositiveInteger
    asset_id: PlannerId
    broker_id: PlannerId
    route_id: PlannerId
    instruction: PlannerOrderInstruction
    economic_quantity: PlannerEconomicQuantity
    source_price: ExactPrice
    mid_price: ExactPrice
    sell_price: ExactPrice
    mid_value: ExactMoney
    execution_margin_cost: ExactMoney
    gross_credit: PlannerPositiveMoneyInput
    fee: PlannerNonNegativeMoneyInput
    cost_basis: PlannerNonNegativeMoneyInput
    taxable_gain: PlannerNonNegativeMoneyInput
    tax_reserve: PlannerNonNegativeMoneyInput
    withholding_kind: Literal["broker_withheld", "self_reserved"]
    spendable_credit: PlannerPositiveMoneyInput
    irreducibility_evidence_ref: PlannerId
    explanation_keys: list[PlannerMessageKey]
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_order_value(self) -> PlannerSellOrderRow:
        price_currencies = {self.source_price.currency, self.mid_price.currency, self.sell_price.currency}
        if price_currencies != {self.gross_credit.currency}:
            raise ValueError("SELL prices and gross credit must use one order currency")
        if len({self.source_price.quote_base_quantity, self.mid_price.quote_base_quantity, self.sell_price.quote_base_quantity}) != 1:
            raise ValueError("SELL prices must use one quote base quantity")
        if exact_fraction(self.sell_price.value) > exact_fraction(self.mid_price.value):
            raise ValueError("SELL execution price cannot exceed mid price")
        posted_currencies = {self.fee.currency, self.tax_reserve.currency, self.spendable_credit.currency}
        if posted_currencies != {self.gross_credit.currency}:
            raise ValueError("SELL fee, tax reserve, and spendable credit must use the order currency")
        if isinstance(self.instruction, MonetaryAmountInstruction):
            if {self.instruction.amount.currency, self.instruction.order_amount_step.currency} != {self.gross_credit.currency}:
                raise ValueError("Monetary SELL instruction must use the order currency")
        if fixed_fraction(self.spendable_credit.amount) != fixed_fraction(self.gross_credit.amount) - fixed_fraction(self.fee.amount) - fixed_fraction(self.tax_reserve.amount):
            raise ValueError("SELL spendable credit must equal gross credit less fee and tax reserve")
        if exact_fraction(self.mid_value.value) <= 0:
            raise ValueError("SELL mid value must be positive")
        if exact_fraction(self.execution_margin_cost.value) < 0:
            raise ValueError("SELL execution-margin cost cannot be negative")
        return self


type RebalancerOrderRow = Annotated[
    Union[PlannerBuyOrderRow, PlannerSellOrderRow],
    Field(discriminator="kind"),
]


class SellIrreducibilityCheck(AllocationStrictModel):
    kind: Literal["decrement_one_quantum", "zero_row"]
    result: Literal["closed_no_better_candidate"]
    closure_kind: Literal["deterministic_conflict", "exhaustive_oracle"]
    blocking_issue_codes: Annotated[list[PlannerIssueCode], Field(min_length=1)]


class SellIrreducibilityEvidence(AllocationStrictModel):
    evidence_id: PlannerId
    order_id: PlannerId
    checks: Annotated[list[SellIrreducibilityCheck], Field(min_length=2, max_length=2)]

    @model_validator(mode="after")
    def validate_counterfactual_order(self) -> SellIrreducibilityEvidence:
        if [check.kind for check in self.checks] != ["decrement_one_quantum", "zero_row"]:
            raise ValueError("SELL irreducibility requires decrement-one then zero-row counterfactuals")
        return self


class PlannerLedgerRow(AllocationStrictModel):
    broker_id: PlannerId
    currency: CurrencyCode
    initial_selected: PlannerFixedDecimal
    funding_in: PlannerFixedDecimal
    funding_out: PlannerFixedDecimal
    fx_debit: PlannerFixedDecimal
    fx_credit: PlannerFixedDecimal
    buy_debit: PlannerFixedDecimal
    gross_sell_credit: PlannerFixedDecimal
    buy_fees: PlannerFixedDecimal
    sell_fees: PlannerFixedDecimal
    broker_withheld_tax: PlannerFixedDecimal
    self_reserved_tax: PlannerFixedDecimal
    rounding_delta: ExactNumber = Field(description="Raw posted-exact rounding delta; credits are negated in the accounting identity.")
    final_spendable: PlannerFixedDecimal
    final_physical: PlannerFixedDecimal

    @model_validator(mode="after")
    def validate_ledger_identity(self) -> PlannerLedgerRow:
        # The final balances may be negative: a PAC pool a few minor units short
        # to rounding against the plan is published with the top-up that covers it
        # (``PacPlanSolution``); ``RebalancerPlanSolution`` still refuses them.
        nonnegative_fields = (
            "initial_selected",
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
        if any(fixed_fraction(getattr(self, name)) < 0 for name in nonnegative_fields):
            raise ValueError("Published ledger amounts cannot be negative")
        expected_spendable = (
            fixed_fraction(self.initial_selected)
            + fixed_fraction(self.funding_in)
            + fixed_fraction(self.fx_credit)
            + fixed_fraction(self.gross_sell_credit)
            - fixed_fraction(self.funding_out)
            - fixed_fraction(self.fx_debit)
            - fixed_fraction(self.buy_debit)
            - fixed_fraction(self.buy_fees)
            - fixed_fraction(self.sell_fees)
            - fixed_fraction(self.broker_withheld_tax)
            - fixed_fraction(self.self_reserved_tax)
        )
        if expected_spendable != fixed_fraction(self.final_spendable):
            raise ValueError("Ledger spendable balance does not reconcile its posted debits and credits")
        if fixed_fraction(self.final_spendable) + fixed_fraction(self.self_reserved_tax) != fixed_fraction(self.final_physical):
            raise ValueError("Ledger spendable balance does not reconcile")
        return self


class PlannerRoundingTopUp(AllocationStrictModel):
    """Cash one ledger pool lacks because the exact replay rounds every posting against the plan (QX1-b).

    ``amount`` is what to add on ``broker_id`` in ``currency`` for the plan to
    execute: the pool's negative final balance, negated. ``rounded_postings``
    counts the pool's nonzero postings that carry a quantum (BUY debit, SELL
    credit, fee, tax, FX credit), and bounds ``amount`` at that many minor units.
    ``valuation_amount`` is ``amount`` in the scenario valuation currency.
    """

    broker_id: PlannerId
    currency: CurrencyCode
    amount: PlannerPositiveDecimal
    rounded_postings: PlannerPositiveInteger
    valuation_amount: ExactMoney

    @model_validator(mode="after")
    def validate_positive_valuation(self) -> PlannerRoundingTopUp:
        if money_fraction(self.valuation_amount) <= 0:
            raise ValueError("PAC rounding top-up valuations must be positive")
        return self


class PacExposurePlanRow(AllocationStrictModel):
    dimension: Literal["asset_type", "sector", "geography"]
    category_id: PlannerId
    label: PlannerLabel
    target_weight: ExactNumber
    final_weight: ExactNumberAvailability
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_weights(self) -> PacExposurePlanRow:
        target = exact_fraction(self.target_weight)
        final = available_fraction(self.final_weight)
        if target < 0 or target > 1 or (final is not None and (final < 0 or final > 1)):
            raise ValueError("Exposure weights must be between zero and one")
        return self


class RebalancerExposurePlanRow(AllocationStrictModel):
    dimension: Literal["asset_type", "sector", "geography"]
    category_id: PlannerId
    label: PlannerLabel
    before_weight: ExactNumberAvailability
    target_weight: ExactNumber
    final_weight: ExactNumberAvailability
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_weights(self) -> RebalancerExposurePlanRow:
        target = exact_fraction(self.target_weight)
        before = available_fraction(self.before_weight)
        final = available_fraction(self.final_weight)
        if target < 0 or target > 1:
            raise ValueError("Target exposure weight must be between zero and one")
        if any(value is not None and (value < 0 or value > 1) for value in (before, final)):
            raise ValueError("Available exposure weights must be between zero and one")
        return self


class PlannerAccountingSummary(AllocationStrictModel):
    current_invested: ExactMoney
    selected_funding: ExactMoney
    reachable_funding: ExactMoney
    trapped_funding: ExactMoney
    fixed_reference: ExactMoney
    final_invested: ExactMoney
    shortfall: ExactMoney
    free_cash: ExactMoney
    physical_reserves: ExactMoney
    economic_losses: ExactMoney
    rounding_delta: ExactMoney = Field(description="Raw posted-exact aggregate rounding delta.")
    rounding_bound: ExactMoney = Field(description="One minor unit per rounded posting, in the valuation currency: each posting rounds against the plan by less than its unit.")
    identity_delta: ExactMoney


class PlannerCostTotals(AllocationStrictModel):
    buy_fees: ExactMoney
    sell_fees: ExactMoney
    fx_spread_loss: ExactMoney
    execution_margin_cost: ExactMoney
    broker_withheld_tax: ExactMoney
    self_reserved_tax: ExactMoney


class ObjectiveStageResult(AllocationStrictModel):
    objective_code: ObjectiveCode
    ordinal: PlannerPositiveInteger
    sense: ObjectiveSense
    unit: NumericObjectiveUnit
    value: ExactNumber

    @model_validator(mode="after")
    def validate_objective_unit_and_value(self) -> ObjectiveStageResult:
        sign_domain = OBJECTIVE_SIGN_DOMAINS.get(self.objective_code)
        if sign_domain is None:
            raise ValueError("Objective code must declare its sign domain")
        if self.unit.kind != objective_unit_kind(self.objective_code):
            raise ValueError("Objective unit does not match objective code")
        value = exact_fraction(self.value)
        if sign_domain == "nonnegative" and value < 0:
            raise ValueError("Objective value must be nonnegative")
        if sign_domain == "nonnegative_integer":
            if value < 0 or value.denominator != 1:
                raise ValueError("Count and ordinal objectives must be nonnegative integers")
        return self


class TieBreakResult(AllocationStrictModel):
    code: Literal["canonical_key"]
    unit: CanonicalKeyUnit
    ordered_keys: list[PlannerId]

    @model_validator(mode="after")
    def validate_keys(self) -> TieBreakResult:
        require_unique(self.ordered_keys, "Tie-break keys")
        return self


class PlannerObjectiveResults(AllocationStrictModel):
    stages: Annotated[list[ObjectiveStageResult], Field(min_length=1)]
    tie_break: TieBreakResult

    @model_validator(mode="after")
    def validate_stage_order(self) -> PlannerObjectiveResults:
        ordinals = [stage.ordinal for stage in self.stages]
        codes = [stage.objective_code for stage in self.stages]
        if ordinals != sorted(ordinals) or len(ordinals) != len(set(ordinals)) or len(codes) != len(set(codes)):
            raise ValueError("Objective stages must have unique codes and ascending ordinals")
        return self
