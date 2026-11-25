"""Rows of a planner result: catalogs, scenario basis, asset and exposure rows, funding, FX and conversion actions, order rows, ledger, rounding top-ups, accounting, costs and objective results."""

from __future__ import annotations

from fractions import Fraction
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
    PlannerLabel,
    PlannerMessageKey,
    PlannerMoneyInput,
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
from backend.app.schemas.pac_allocator.exact import AvailableExactNumber, ExactFxRate, ExactMoney, ExactNumber, ExactNumberAvailability, ExactPrice, ExactRatio, available_fraction, exact_fraction, fixed_fraction, money_fraction
from backend.app.schemas.pac_allocator.request import CurrencySpec, PlannerFundingSourceRef, RebalancerLossScopeInput


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
    minimum: ExactMoney | None = Field(description="The Asset's minimum final value as an amount in the valuation currency, whichever form the request gave it; null when not set.")
    maximum: ExactMoney | None = Field(description="The Asset's maximum final value as an amount in the valuation currency, whichever form the request gave it; null when not set.")


class PacCashEntryRow(AllocationStrictModel):
    """A cash entry with a limit: the final spendable cash of one Broker in one currency, valued in the valuation currency, and its limits."""

    broker_id: PlannerId
    currency: CurrencyCode
    final_value: ExactMoney
    minimum: ExactMoney | None = Field(description="The cell's minimum final cash as an amount in the valuation currency; null when not set.")
    maximum: ExactMoney | None = Field(description="The cell's maximum final cash as an amount in the valuation currency; null when not set.")


class RebalancerAssetPlanRow(AllocationStrictModel):
    """An Asset before, at its target and after the plan (contract §6.2). Every weight is a share of ``F``, the wealth the
    plan starts from, so the Asset rows, the cash item rows and the uninvested row sum to one before and after."""

    asset_id: PlannerId
    before_value: ExactMoney
    before_weight: ExactNumber
    target_weight: ExactNumber
    target_value: ExactMoney
    final_value: ExactMoney
    final_weight: ExactNumber
    residual: ExactMoney
    buy_mid_value: ExactMoney
    sell_mid_value: ExactMoney
    minimum: ExactMoney | None = Field(description="The Asset's minimum final value as an amount in the valuation currency, whichever form the request gave it; null when not set.")
    maximum: ExactMoney | None = Field(description="The Asset's maximum final value as an amount in the valuation currency, whichever form the request gave it; null when not set.")


class RebalancerCashItemRow(AllocationStrictModel):
    """A cash item of the request (a Broker's cash in one currency, with a weight or a limit), before, at its target and
    after the plan; its spendable cash valued in the valuation currency, every weight a share of ``F``. Only an item with a
    target weight is an item of the distance; the cash of one with only a limit is part of the uninvested row."""

    broker_id: PlannerId
    currency: CurrencyCode
    before_value: ExactMoney
    before_weight: ExactNumber
    target_weight: ExactNumber
    target_value: ExactMoney
    final_value: ExactMoney
    final_weight: ExactNumber
    residual: ExactMoney
    minimum: ExactMoney | None = Field(description="The item's minimum final cash as an amount in the valuation currency; null when not set.")
    maximum: ExactMoney | None = Field(description="The item's maximum final cash as an amount in the valuation currency; null when not set.")


class RebalancerUninvestedPart(AllocationStrictModel):
    """One of the two parts of the uninvested row (TL-5 of project 67), before and after the plan, on ``F``."""

    before_value: ExactMoney
    before_weight: ExactNumber
    final_value: ExactMoney
    final_weight: ExactNumber


class RebalancerUninvestedRow(AllocationStrictModel):
    """What is neither in an Asset nor in a cash item with a target, before and after the plan: ``N = F − Assets − cash
    items with a target``. Its target is zero. After the plan it includes the money the plan lost.

    Its two parts (TL-5 of project 67, the developer's answer of 24/11): ``untargeted_cash``, the cash with no target and the
    contributions not deposited — all of ``N`` before the plan, ``N`` less the money lost after it — and ``costs``, the money
    the plan lost: zero before the plan, ``F − W`` after it. Together they are the row."""

    before_value: ExactMoney
    before_weight: ExactNumber
    final_value: ExactMoney
    final_weight: ExactNumber
    untargeted_cash: RebalancerUninvestedPart
    costs: RebalancerUninvestedPart

    @model_validator(mode="after")
    def validate_parts(self) -> RebalancerUninvestedRow:
        parts = (self.untargeted_cash, self.costs)
        for field in ("before_value", "final_value"):
            if len({getattr(part, field).currency for part in parts} | {getattr(self, field).currency}) != 1:
                raise ValueError("The uninvested row and its parts must use one currency")
            if sum((money_fraction(getattr(part, field)) for part in parts), Fraction()) != money_fraction(getattr(self, field)):
                raise ValueError(f"The uninvested row's parts must sum to its {field}")
        for field in ("before_weight", "final_weight"):
            if sum((exact_fraction(getattr(part, field)) for part in parts), Fraction()) != exact_fraction(getattr(self, field)):
                raise ValueError(f"The uninvested row's parts must sum to its {field}")
        if money_fraction(self.costs.before_value) != 0:
            raise ValueError("Nothing is lost before the plan")
        return self


class PlannerFundingAction(AllocationStrictModel):
    action_id: PlannerId
    sequence: PlannerPositiveInteger
    funding_route_id: PlannerId
    source: PlannerFundingSourceRef
    destination_broker_id: PlannerId
    amount: PlannerPositiveMoneyInput
    reason_code: FundingActionReasonCode
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]


class PlannerConversion(AllocationStrictModel):
    """One currency conversion per Broker and ordered currency pair: the engine's own decision.

    The credit lands in a cash pool that every order of that Broker in that currency shares, so the pair is what the plan
    executes. ``source_debit`` is the exact amount converted, ``destination_credit`` the posted credit the ledger reconciles
    against, ``spread_loss`` the exact cost in the valuation currency.
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
        return self


class PlannerTransfer(AllocationStrictModel):
    """Cash moved from one Broker to another, in one currency, free and instant (contract §6.3, Rebalancer)."""

    transfer_id: PlannerId
    sequence: PlannerPositiveInteger
    source_broker_id: PlannerId
    destination_broker_id: PlannerId
    amount: PlannerPositiveMoneyInput

    @model_validator(mode="after")
    def validate_transfer(self) -> PlannerTransfer:
        if self.source_broker_id == self.destination_broker_id:
            raise ValueError("A transfer moves cash between two different Brokers")
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
        return self


def _validate_sell_currencies(row: PlannerSellOrderRow) -> None:
    """A sale's prices, fee, taxes and net credit are in the order currency; its cost basis and gain in one other, the valuation currency."""
    if {row.source_price.currency, row.mid_price.currency, row.sell_price.currency} != {row.gross_credit.currency}:
        raise ValueError("SELL prices and gross credit must use one order currency")
    if len({row.source_price.quote_base_quantity, row.mid_price.quote_base_quantity, row.sell_price.quote_base_quantity}) != 1:
        raise ValueError("SELL prices must use one quote base quantity")
    if {row.fee.currency, row.foreign_withholding_tax.currency, row.tax.currency, row.net_credit.currency} != {row.gross_credit.currency}:
        raise ValueError("SELL fee, taxes and net credit must use the order currency")
    if row.cost_basis.currency != row.realized_gain.currency:
        raise ValueError("SELL cost basis and realized gain must use one currency, the valuation currency")
    if isinstance(row.instruction, MonetaryAmountInstruction) and {row.instruction.amount.currency, row.instruction.order_amount_step.currency} != {row.gross_credit.currency}:
        raise ValueError("Monetary SELL instruction must use the order currency")


class PlannerSellOrderRow(AllocationStrictModel):
    """A sale (contract §6.3): the gross credit, the fee, the foreign withholding and the tax, all in the order currency, and
    what is left, ``net_credit``, which may be zero or negative. ``cost_basis`` and ``realized_gain`` are in the valuation
    currency, where the tax is computed; a loss is a negative gain. ``tax_handling`` says whether the Broker withholds the tax
    (an administered regime) or the plan sets it aside (a declarative one). ``reason`` is a label the report computes:
    ``loss_offset`` is a sale at a loss of an Asset that was not above its target before the plan."""

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
    cost_basis: ExactMoney
    realized_gain: ExactMoney
    foreign_withholding_tax: PlannerNonNegativeMoneyInput
    tax: PlannerNonNegativeMoneyInput
    tax_handling: Literal["withheld", "reserved"]
    net_credit: PlannerMoneyInput
    reason: Literal["rebalancing", "loss_offset"]
    explanation_keys: list[PlannerMessageKey]
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_order_value(self) -> PlannerSellOrderRow:
        _validate_sell_currencies(self)
        if exact_fraction(self.sell_price.value) > exact_fraction(self.mid_price.value):
            raise ValueError("SELL execution price cannot exceed mid price")
        expected_net = fixed_fraction(self.gross_credit.amount) - fixed_fraction(self.fee.amount) - fixed_fraction(self.foreign_withholding_tax.amount) - fixed_fraction(self.tax.amount)
        if fixed_fraction(self.net_credit.amount) != expected_net:
            raise ValueError("SELL net credit must equal gross credit less fee, foreign withholding and tax")
        if money_fraction(self.cost_basis) < 0:
            raise ValueError("SELL cost basis cannot be negative")
        if exact_fraction(self.mid_value.value) <= 0:
            raise ValueError("SELL mid value must be positive")
        if exact_fraction(self.execution_margin_cost.value) < 0:
            raise ValueError("SELL execution-margin cost cannot be negative")
        return self


type RebalancerOrderRow = Annotated[
    Union[PlannerBuyOrderRow, PlannerSellOrderRow],
    Field(discriminator="kind"),
]


class PlannerLedgerRow(AllocationStrictModel):
    broker_id: PlannerId
    currency: CurrencyCode
    initial_selected: PlannerFixedDecimal
    funding_in: PlannerFixedDecimal
    funding_out: PlannerFixedDecimal
    transfer_in: PlannerFixedDecimal = Field(description="Cash that arrives from another Broker of the plan in this currency.")
    transfer_out: PlannerFixedDecimal = Field(description="Cash that leaves for another Broker of the plan in this currency.")
    fx_debit: PlannerFixedDecimal
    fx_credit: PlannerFixedDecimal
    buy_debit: PlannerFixedDecimal
    gross_sell_credit: PlannerFixedDecimal
    buy_fees: PlannerFixedDecimal
    sell_fees: PlannerFixedDecimal
    broker_withheld_tax: PlannerFixedDecimal = Field(description="Tax withheld by a Broker whose tax_regime is administered.")
    foreign_withholding_tax: PlannerFixedDecimal = Field(description="Tax a foreign source withheld before the cash reached the cell.")
    self_reserved_tax: PlannerFixedDecimal = Field(description="Tax the plan sets aside for a Broker whose tax_regime is declarative: the Broker withholds nothing.")
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
        if any(fixed_fraction(getattr(self, name)) < 0 for name in nonnegative_fields):
            raise ValueError("Published ledger amounts cannot be negative")
        expected_spendable = (
            fixed_fraction(self.initial_selected)
            + fixed_fraction(self.funding_in)
            + fixed_fraction(self.fx_credit)
            + fixed_fraction(self.gross_sell_credit)
            + fixed_fraction(self.transfer_in)
            - fixed_fraction(self.funding_out)
            - fixed_fraction(self.transfer_out)
            - fixed_fraction(self.fx_debit)
            - fixed_fraction(self.buy_debit)
            - fixed_fraction(self.buy_fees)
            - fixed_fraction(self.sell_fees)
            - fixed_fraction(self.broker_withheld_tax)
            - fixed_fraction(self.foreign_withholding_tax)
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


class RebalancerUnavailableWeight(AllocationStrictModel):
    """A Rebalancer exposure weight with no base: the wealth it is measured on is zero (before on ``F``, after on ``W``).
    Its own reasons, so that the PAC's ``UnavailableExactNumber`` (and its fingerprint) stays as it is."""

    kind: Literal["unavailable"]
    reason: Literal["zero_initial_wealth", "zero_final_wealth"]


type RebalancerWeightAvailability = Annotated[Union[AvailableExactNumber, RebalancerUnavailableWeight], Field(discriminator="kind")]


class _RebalancerExposureWeights(AllocationStrictModel):
    """The exposure of the whole portfolio in one dimension (developer's decision of 13/11, project 67): before on the
    plan's total ``F``, the target on the items' weights as they are (not renormalised), after on the final wealth ``W``."""

    dimension: Literal["asset_type", "sector", "geography"]
    before_weight: RebalancerWeightAvailability
    target_weight: ExactNumber
    final_weight: RebalancerWeightAvailability

    @model_validator(mode="after")
    def validate_weights(self) -> _RebalancerExposureWeights:
        target = exact_fraction(self.target_weight)
        if target < 0 or target > 1:
            raise ValueError("Target exposure weight must be between zero and one")
        if any(value is not None and (value < 0 or value > 1) for value in (available_fraction(self.before_weight), available_fraction(self.final_weight))):
            raise ValueError("Available exposure weights must be between zero and one")
        return self


class RebalancerExposureCategoryRow(_RebalancerExposureWeights):
    """A category of the dimension (or the uncategorised rest), as the Assets declare it."""

    kind: Literal["category"]
    category_id: PlannerId
    label: PlannerLabel
    provenance_ids: Annotated[list[PlannerId], Field(min_length=1)]


class RebalancerExposureCashRow(_RebalancerExposureWeights):
    """The cash of the portfolio in this dimension: one row, always there, even at zero. Before: the selected cash and the
    contributions; target: the cash items' weights; after: the final spendable cash and the contributions not deposited.
    The tax set aside is not here (it is money lost). No category and no label: the screen names it."""

    kind: Literal["cash"]
    provenance_ids: list[PlannerId]


type RebalancerExposurePlanRow = Annotated[Union[RebalancerExposureCategoryRow, RebalancerExposureCashRow], Field(discriminator="kind")]


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
    broker_withheld_tax: ExactMoney = Field(description="Tax withheld by a Broker whose tax_regime is administered.")
    self_reserved_tax: ExactMoney = Field(description="Tax the plan sets aside for a Broker whose tax_regime is declarative: the Broker withholds nothing.")
    foreign_withholding_tax: ExactMoney


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


class PlannerMoneyLost(AllocationStrictModel):
    """The money the plan loses, by entry (contract §6.1), in the valuation currency: its sum is ``F − W``."""

    buy_fees: ExactMoney
    sell_fees: ExactMoney
    fx_spread_loss: ExactMoney
    execution_margin_cost: ExactMoney
    broker_withheld_tax: ExactMoney
    self_reserved_tax: ExactMoney
    foreign_withholding_tax: ExactMoney
    rounding: ExactMoney = Field(description="What the postings, each rounded against the plan to its currency's minor unit, lose against the exact amounts.")

    def total(self) -> Fraction:
        return sum((money_fraction(getattr(self, name)) for name in type(self).model_fields), Fraction())


class PlannerCurrencyCash(AllocationStrictModel):
    """The plan's cash in one currency, in that currency, every Broker summed (TL-5 of project 67, contract §6.1): ``initial``
    the cash chosen for the plan plus the contributions declared in it; ``final`` the spendable cash the Brokers end with
    plus the contributions not deposited, which ``unused_contributions`` repeats. The tax the plan sets aside is not
    spendable: it is among the money lost. ``final`` may be a few minor units below zero, where a rounding top-up covers it."""

    currency: CurrencyCode
    initial: ExactMoney
    final: ExactMoney
    unused_contributions: ExactMoney

    @model_validator(mode="after")
    def validate_cash(self) -> PlannerCurrencyCash:
        if {self.initial.currency, self.final.currency, self.unused_contributions.currency} != {self.currency}:
            raise ValueError("A currency's cash is written in that currency")
        if money_fraction(self.initial) < 0 or money_fraction(self.unused_contributions) < 0:
            raise ValueError("The cash at the start and the unused contributions cannot be negative")
        return self


class PlannerPlanAccounts(AllocationStrictModel):
    """The accounts of the plan (contract §6.1, specifica §5-§6), the same for both Tools: the wealth before (``F``: the
    invested value plus every selected cash and contribution) and after (``W``: Assets plus spendable cash), the money lost
    on the way, by entry, and what is left uninvested (``N``: neither in an Asset nor in a cash item)."""

    initial_wealth: ExactMoney
    final_wealth: ExactMoney
    money_lost: PlannerMoneyLost
    uninvested: ExactMoney
    final_cash: ExactMoney = Field(description="All the cash at the end of the plan, in the valuation currency: ``W`` less the Assets after it — the cash items with and without a target and the contributions not deposited (TL-5 of project 67).")
    cash_by_currency: list[PlannerCurrencyCash] = Field(description="The cash at the start and at the end, one row per currency the plan holds cash in, the valuation currency first, then by code (TL-5 of project 67).")

    @model_validator(mode="after")
    def validate_accounts(self) -> PlannerPlanAccounts:
        values = [self.initial_wealth, self.final_wealth, self.uninvested, self.final_cash, *(getattr(self.money_lost, name) for name in type(self.money_lost).model_fields)]
        if len({money.currency for money in values}) != 1:
            raise ValueError("Plan accounts must use one currency, the valuation currency")
        if money_fraction(self.initial_wealth) < 0:
            raise ValueError("Initial wealth cannot be negative")
        if any(money_fraction(getattr(self.money_lost, name)) < 0 for name in type(self.money_lost).model_fields if name != "rounding"):
            raise ValueError("Money lost on fees, spread, margins and taxes cannot be negative")
        if self.money_lost.total() != money_fraction(self.initial_wealth) - money_fraction(self.final_wealth):
            raise ValueError("The money lost, by entry, must sum to the initial less the final wealth")
        currencies = [row.currency for row in self.cash_by_currency]
        valuation = self.initial_wealth.currency
        if currencies != sorted(currencies, key=lambda code: (code != valuation, code)) or len(set(currencies)) != len(currencies):
            raise ValueError("The cash by currency lists each currency once, the valuation currency first, then by code")
        return self


class RebalancerTieBreakStage(AllocationStrictModel):
    """A tie-break of the Rebalancer, by name, and how SCIP left it: ``closed`` at its optimum, ``unfinished`` at a limit, or
    ``rejected``: its plan failed the exact check and the plan of the stage before is published (D4). ``canonical`` is the
    fixed-order tie-break vector, last, on the same level as the named ones (specifica §6.4)."""

    objective_code: ObjectiveCode | Literal["canonical"]
    status: Literal["closed", "unfinished", "rejected"]


class RebalancerAssetItemRef(AllocationStrictModel):
    """An Asset item of the Rebalancer's distance (an Asset row of the plan)."""

    kind: Literal["asset"]
    asset_id: PlannerId


class RebalancerCashItemRef(AllocationStrictModel):
    """A cash item of the Rebalancer's distance: a Broker's cash in one currency with a target weight (a cash row of the
    plan that has a target)."""

    kind: Literal["cash"]
    broker_id: PlannerId
    currency: CurrencyCode


type RebalancerItemRef = Annotated[Union[RebalancerAssetItemRef, RebalancerCashItemRef], Field(discriminator="kind")]


class RebalancerScoreSummary(AllocationStrictModel):
    """The Rebalancer's score (specifica §6, contract §6.1, §6.6), from the exact values of the published plan.

    ``target_distance`` is ``D``: the squared residuals of the Asset rows and the cash items with a target plus ``N²``, in
    the valuation currency squared. ``distance_per_wealth`` is ``D / F``. ``wealth_loss`` is ``F − W``. ``distance_weight`` is ``λ`` and
    ``plan_score`` is ``J = λ·D/F + (F − W)``, both null under «Target first». The largest deviation is the largest
    ``|weight − target weight|`` over the Asset rows and the cash items with a target, as a share of one, before and after the
    plan; ``largest_deviation_before_item`` and ``…_after_item`` name the item that reaches it (X14, «which entry»): the
    first one in the published order (the Asset rows, then the cash rows with a target) on a tie, null when no item is off
    its target."""

    distance_weight: ExactNumber | None
    target_distance: ExactNumber
    distance_per_wealth: ExactMoney
    wealth_loss: ExactMoney
    plan_score: ExactMoney | None
    largest_deviation_before: ExactNumber
    largest_deviation_after: ExactNumber
    largest_deviation_before_item: RebalancerItemRef | None
    largest_deviation_after_item: RebalancerItemRef | None
    tie_breaks: list[RebalancerTieBreakStage]

    @model_validator(mode="after")
    def validate_score(self) -> RebalancerScoreSummary:
        if (self.distance_weight is None) != (self.plan_score is None):
            raise ValueError("The distance weight and the plan score are both present (a weighted fidelity) or both absent («Target first»)")
        if self.distance_weight is not None and exact_fraction(self.distance_weight) <= 0:
            raise ValueError("The distance weight must be positive")
        if exact_fraction(self.target_distance) < 0 or money_fraction(self.distance_per_wealth) < 0:
            raise ValueError("The target distance cannot be negative")
        if any(not 0 <= exact_fraction(value) <= 1 for value in (self.largest_deviation_before, self.largest_deviation_after)):
            raise ValueError("A deviation of weights is between zero and one")
        for value, item in ((self.largest_deviation_before, self.largest_deviation_before_item), (self.largest_deviation_after, self.largest_deviation_after_item)):
            if (item is None) != (exact_fraction(value) == 0):
                raise ValueError("The largest deviation names its item exactly when some item is off its target")
        if self.plan_score is not None and self.distance_weight is not None:
            expected = exact_fraction(self.distance_weight) * money_fraction(self.distance_per_wealth) + money_fraction(self.wealth_loss)
            if money_fraction(self.plan_score) != expected:
                raise ValueError("The plan score must equal λ·D/F plus the money lost")
        require_unique([stage.objective_code for stage in self.tie_breaks], "Rebalancer tie-break stages")
        return self


class RebalancerTaxBasketRow(AllocationStrictModel):
    """One tax scope (a Broker that withholds, or the declared income) and one basket: gains and losses weighted by the
    basket's rules, the carried losses used, the taxable base, the tax and the loss left for later (contract §6.4)."""

    scope: RebalancerLossScopeInput
    basket_id: PlannerId
    weighted_gains: ExactMoney
    weighted_losses: ExactMoney
    carried_losses_used: ExactMoney
    taxable: ExactMoney
    tax: ExactMoney
    loss_left: ExactMoney

    @model_validator(mode="after")
    def validate_basket(self) -> RebalancerTaxBasketRow:
        if any(money_fraction(getattr(self, name)) < 0 for name in ("weighted_gains", "weighted_losses", "carried_losses_used", "taxable", "tax", "loss_left")):
            raise ValueError("Tax basket amounts are magnitudes and cannot be negative")
        return self


class RebalancerTaxScopeRow(AllocationStrictModel):
    """Whether a tax scope nets sales settled in more than one currency (the note K1 of the interface)."""

    scope: RebalancerLossScopeInput
    nets_across_currencies: bool


class RebalancerTaxReserveRow(AllocationStrictModel):
    """The tax to set aside on a Broker that withholds nothing, in one currency."""

    broker_id: PlannerId
    amount: PlannerPositiveMoneyInput


class RebalancerAssetTypeTaxRow(AllocationStrictModel):
    """Gains, losses and tax of the sales, by asset type (the card «gains and losses by type»); ``asset_class`` is the
    catalog's, null for Assets without one."""

    asset_class: PlannerCode | None
    realized_gain: ExactMoney
    realized_loss: ExactMoney
    tax: ExactMoney

    @model_validator(mode="after")
    def validate_amounts(self) -> RebalancerAssetTypeTaxRow:
        if any(money_fraction(getattr(self, name)) < 0 for name in ("realized_gain", "realized_loss", "tax")):
            raise ValueError("Gains, losses and tax by asset type are magnitudes and cannot be negative")
        return self
