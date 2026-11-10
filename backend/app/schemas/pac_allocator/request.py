"""Planner requests: the PAC and Rebalancer scenarios the user drafts (snapshot, currencies, provenance, assets, brokers, holdings, cash, contributions, funding and order routes, targets, sell context)."""

from __future__ import annotations

import re
from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from backend.app.schemas.common import Currency
from backend.app.schemas.pac_allocator.base import (
    PLANNER_FX_PAIR,
    AllocationStrictModel,
    CurrencyCode,
    OrderSide,
    PlannerCode,
    PlannerConversionMode,
    PlannerFixedDecimal,
    PlannerId,
    PlannerLabel,
    PlannerMoneyInput,
    PlannerRef,
    PlannerSafeInteger,
    PlannerTimestamp,
    PlannerWholeQuantityStep,
    PlannerWireInteger,
    QuantityUnit,
    ReferenceDate,
    planner_canonical_fx_pair,
)


class PlannerSnapshotInput(AllocationStrictModel):
    snapshot_id: PlannerId
    draft_revision: PlannerSafeInteger
    captured_at: PlannerTimestamp


class CurrencySpec(AllocationStrictModel):
    """Published ISO 4217 minor unit, derived by the normalizer from CLDR (babel); never a request input."""

    currency: CurrencyCode
    minor_unit: PlannerFixedDecimal


class ManualProvenance(AllocationStrictModel):
    kind: Literal["manual"]
    provenance_id: PlannerId
    label: PlannerLabel
    entered_at: PlannerTimestamp


class DomainCopyProvenance(AllocationStrictModel):
    kind: Literal["domain_copy"]
    provenance_id: PlannerId
    domain: Literal["portfolio", "market_data", "broker", "fx", "wac"]
    source_ref: PlannerRef
    source_label: PlannerLabel | None = None
    captured_at: PlannerTimestamp


type PlannerProvenance = Annotated[
    Union[ManualProvenance, DomainCopyProvenance],
    Field(discriminator="kind"),
]


class ManualAssetIdentity(AllocationStrictModel):
    kind: Literal["manual_asset"]
    name: PlannerLabel
    ticker: PlannerLabel | None
    asset_class: PlannerCode | None = None


class DomainAssetIdentity(AllocationStrictModel):
    kind: Literal["domain_asset"]
    source_asset_id: PlannerRef
    name: PlannerLabel
    ticker: PlannerLabel | None
    asset_class: PlannerCode | None = None


type PlannerAssetIdentity = Annotated[
    Union[ManualAssetIdentity, DomainAssetIdentity],
    Field(discriminator="kind"),
]


class PlannerAssetQuoteInput(AllocationStrictModel):
    amount: PlannerFixedDecimal
    currency: CurrencyCode
    quote_base_quantity: PlannerFixedDecimal
    provenance_id: PlannerId


class PlannerExposureInput(AllocationStrictModel):
    dimension: Literal["asset_type", "sector", "geography"]
    category_id: PlannerId
    label: PlannerLabel
    weight: PlannerFixedDecimal
    provenance_id: PlannerId


class PlannerAssetInput(AllocationStrictModel):
    asset_id: PlannerId
    identity: PlannerAssetIdentity = Field(description="Nested identity assembled from the authorized flat source Asset row.")
    quote: PlannerAssetQuoteInput | None = Field(description="One complete nested Price fact or explicit absence; never a partial object built from null source fields.")
    exposures: list[PlannerExposureInput] = Field(default=[], description="Complete nested Classification facts assembled by the backend; the frontend performs no financial reconstruction.")


class ManualBrokerIdentity(AllocationStrictModel):
    kind: Literal["manual_broker"]
    name: PlannerLabel


class DomainBrokerIdentity(AllocationStrictModel):
    """Minimal persisted Broker facts; executable routes still require normalizer approval."""

    kind: Literal["domain_broker"]
    source_broker_id: PlannerRef
    name: PlannerLabel
    active: bool = Field(description="Persisted activity fact used to reject submitted executable routes to an inactive Broker.")


type PlannerBrokerIdentity = Annotated[
    Union[ManualBrokerIdentity, DomainBrokerIdentity],
    Field(discriminator="kind"),
]


class WholeQuantityCapability(AllocationStrictModel):
    kind: Literal["whole_quantity"]
    capability_id: PlannerId
    quantity_unit: QuantityUnit
    quantity_step: PlannerWholeQuantityStep


class MonetaryAmountCapability(AllocationStrictModel):
    kind: Literal["monetary_amount"]
    capability_id: PlannerId
    order_amount_step: PlannerMoneyInput


type BrokerOrderCapability = Annotated[
    Union[WholeQuantityCapability, MonetaryAmountCapability],
    Field(discriminator="kind"),
]


class NoFeeCap(AllocationStrictModel):
    kind: Literal["none"]


class AmountFeeCap(AllocationStrictModel):
    kind: Literal["amount"]
    amount: PlannerMoneyInput


type FeeCap = Annotated[Union[NoFeeCap, AmountFeeCap], Field(discriminator="kind")]


class BrokerFeeScheduleInput(AllocationStrictModel):
    """An absent money field is zero. A schedule with no money field takes the quote currency of each route using it."""

    fee_schedule_id: PlannerId
    capability_id: PlannerId
    side: OrderSide
    fixed_fee: PlannerMoneyInput | None = None
    rate: PlannerFixedDecimal = "0"
    variable_floor: PlannerMoneyInput | None = None
    variable_cap: FeeCap = NoFeeCap(kind="none")


class PlannerBrokerInput(AllocationStrictModel):
    broker_id: PlannerId
    identity: PlannerBrokerIdentity
    provenance_id: PlannerId
    capabilities: list[BrokerOrderCapability] = []
    fee_schedules: list[BrokerFeeScheduleInput] = []
    conversion_mode: PlannerConversionMode = Field(description="How the plan presents this Broker's currency conversions: 'manual' as numbered steps the user performs before buying, 'automatic' as conversions the Broker performs when the orders execute. It changes no figure of the plan.")


class PlannerHoldingInput(AllocationStrictModel):
    holding_id: PlannerId
    asset_id: PlannerId
    broker_id: PlannerId
    custody_quantity: PlannerFixedDecimal = Field(description="Observed custody quantity; never recomputed from economic ownership.")
    economic_share: PlannerFixedDecimal
    planning_quantity: PlannerFixedDecimal = Field(description="Editable planning quantity proposed from source economic_quantity; it never rewrites custody_quantity.")
    quantity_unit: QuantityUnit
    provenance_id: PlannerId


class PlannerExistingCashInput(AllocationStrictModel):
    cash_id: PlannerId
    broker_id: PlannerId
    available: PlannerMoneyInput
    selected: PlannerMoneyInput
    provenance_id: PlannerId


class PlannerContributionInput(AllocationStrictModel):
    contribution_id: PlannerId
    label: PlannerLabel
    amount: PlannerMoneyInput
    provenance_id: PlannerId


class ExistingCashFundingSourceRef(AllocationStrictModel):
    kind: Literal["existing_cash"]
    cash_id: PlannerId


class ContributionFundingSourceRef(AllocationStrictModel):
    kind: Literal["contribution"]
    contribution_id: PlannerId


type PlannerFundingSourceRef = Annotated[
    Union[ExistingCashFundingSourceRef, ContributionFundingSourceRef],
    Field(discriminator="kind"),
]


class PlannerFundingRouteInput(AllocationStrictModel):
    funding_route_id: PlannerId
    source: PlannerFundingSourceRef
    broker_id: PlannerId
    currency: CurrencyCode
    priority: PlannerWireInteger = 0
    transfer_cap: PlannerMoneyInput | None = Field(default=None, description="Absent means the whole selected amount of the source.")
    provenance_id: PlannerId


class NoOrderMinimum(AllocationStrictModel):
    kind: Literal["none"]


class WholeQuantityMinimum(AllocationStrictModel):
    kind: Literal["whole_quantity"]
    quantity: PlannerFixedDecimal
    unit: QuantityUnit


class MonetaryAmountMinimum(AllocationStrictModel):
    kind: Literal["monetary_amount"]
    amount: PlannerMoneyInput


type OrderMinimum = Annotated[
    Union[NoOrderMinimum, WholeQuantityMinimum, MonetaryAmountMinimum],
    Field(discriminator="kind"),
]


class QuantityOrderCap(AllocationStrictModel):
    kind: Literal["quantity"]
    quantity: PlannerFixedDecimal
    unit: QuantityUnit


class NotionalOrderCap(AllocationStrictModel):
    kind: Literal["notional"]
    amount: PlannerMoneyInput


class NoOrderCap(AllocationStrictModel):
    """No cap of its own: a buy is still bounded by the resources, a sell by the holding."""

    kind: Literal["none"]


type OrderCap = Annotated[
    Union[QuantityOrderCap, NotionalOrderCap, NoOrderCap],
    Field(discriminator="kind"),
]


class PlannerOrderRouteInput(AllocationStrictModel):
    route_id: PlannerId
    asset_id: PlannerId
    broker_id: PlannerId
    capability_id: PlannerId
    side: OrderSide
    priority: PlannerWireInteger = 0
    minimum_if_active: OrderMinimum = NoOrderMinimum(kind="none")
    required_minimum: OrderMinimum = NoOrderMinimum(kind="none")
    cap: OrderCap = NoOrderCap(kind="none")
    execution_margin_rate: PlannerFixedDecimal = "0"
    fee_schedule_id: PlannerId
    provenance_id: PlannerId


class PlannerBuyOrderRouteInput(PlannerOrderRouteInput):
    side: Literal["buy"]
    fee_schedule_id: PlannerId | None = Field(default=None, description="Absent means a BUY without fees.")


class PlannerSellOrderRouteInput(PlannerOrderRouteInput):
    side: Literal["sell"]


type RebalancerOrderRouteInput = Annotated[
    Union[PlannerBuyOrderRouteInput, PlannerSellOrderRouteInput],
    Field(discriminator="side"),
]


class PacOrderRouteInput(PlannerBuyOrderRouteInput):
    pass


class PlannerTargetWeightInput(AllocationStrictModel):
    asset_id: PlannerId
    weight: PlannerFixedDecimal


class PlannerCostBasisInput(AllocationStrictModel):
    holding_id: PlannerId
    average_unit_cost: PlannerMoneyInput
    reference_date: ReferenceDate
    provenance_id: PlannerId


class PlannerAssetTaxInput(AllocationStrictModel):
    asset_id: PlannerId
    tax_rate: PlannerFixedDecimal
    fiscal_currency: CurrencyCode | None = Field(description="Persisted fiscal currency when known; null is explicit and must produce needs_input rather than target-currency substitution.")
    provenance_id: PlannerId


class PlannerBrokerWithholdingInput(AllocationStrictModel):
    broker_id: PlannerId
    withholding_kind: Literal["broker_withheld", "self_reserved"]
    carried_loss: PlannerMoneyInput
    reference_date: ReferenceDate
    provenance_id: PlannerId


class PlannerSellContextInput(AllocationStrictModel):
    """Complete explicit SELL facts; missing fiscal, tax, or withholding facts block assembly."""

    cost_bases: list[PlannerCostBasisInput] = []
    asset_taxes: list[PlannerAssetTaxInput] = []
    broker_withholding: list[PlannerBrokerWithholdingInput] = []


class _PlannerRequestBase(AllocationStrictModel):
    operation: Literal["plan"]
    snapshot: PlannerSnapshotInput
    as_of: ReferenceDate
    valuation_currency: CurrencyCode
    provenance: list[PlannerProvenance] = Field(description="Root provenance records referenced by every copied or manually supplied fact.")
    fx_rates: dict[str, PlannerFixedDecimal] = Field(
        default={},
        description="Canonical global FX facts; key is an alphabetically sorted uppercase currency pair naming one unit of the first currency, value is units of the second currency per one unit of the first. May be empty.",
    )
    fx_spread_rate: PlannerFixedDecimal = Field(default="0", description="Single global adverse spread applied exactly once to every actual currency conversion; valuation always uses the official rate.")
    assets: list[PlannerAssetInput]
    brokers: list[PlannerBrokerInput]
    existing_cash: list[PlannerExistingCashInput] = []
    contributions: list[PlannerContributionInput] = []
    funding_routes: list[PlannerFundingRouteInput] = []
    target_weights: list[PlannerTargetWeightInput]

    @model_validator(mode="after")
    def _validate_fx_rate_pair_keys(self) -> _PlannerRequestBase:
        # `fx_rates` is a plain `dict[str, ...]` (unconstrained key) rather than a
        # pattern-keyed dict, so the tool-schema codegen allow-list never sees a
        # `patternProperties` keyword; this validator reapplies the same pair
        # format/ordering constraint (regex + `planner_canonical_fx_pair`) at runtime.
        # Both codes are ISO-validated like every `CurrencyCode`: the normalizer
        # derives a minor unit for each referenced currency.
        for pair in self.fx_rates:
            if not re.fullmatch(PLANNER_FX_PAIR, pair):
                raise ValueError(f"FX rate key {pair!r} must be an uppercase 'AAA/BBB' currency pair")
            planner_canonical_fx_pair(pair)
            for code in pair.split("/"):
                Currency.validate_code(code)
        return self


class PacPlannerRequest(_PlannerRequestBase):
    order_routes: list[PacOrderRouteInput]
    # `min_fragmentation` is deferred (TODO_FUTURI): the exact model keeps the
    # branch, the wire does not accept it.
    policy: Literal["proportional"]


class _RebalancerPlannerRequestBase(_PlannerRequestBase):
    holdings: list[PlannerHoldingInput] = []
    order_routes: list[RebalancerOrderRouteInput]


class RebalancerInvestOnlyRequest(_RebalancerPlannerRequestBase):
    policy: Literal["invest_only"]
    order_routes: list[PacOrderRouteInput]


class RebalancerInvestAndSellRequest(_RebalancerPlannerRequestBase):
    policy: Literal["invest_and_sell"]
    sell_context: PlannerSellContextInput

    @model_validator(mode="after")
    def require_sell_route(self) -> RebalancerInvestAndSellRequest:
        if not any(route.side == "sell" for route in self.order_routes):
            raise ValueError("invest_and_sell requires at least one SELL order route")
        return self


type RebalancerPlannerRequest = Annotated[
    Union[RebalancerInvestOnlyRequest, RebalancerInvestAndSellRequest],
    Field(discriminator="policy"),
]
