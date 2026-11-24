"""Planner requests: the PAC and Rebalancer scenarios the user drafts (snapshot, currencies, provenance, assets, brokers, holdings, cash, contributions, funding and order routes, targets, sell context)."""

from __future__ import annotations

import re
from typing import Annotated, Literal, Union

from pydantic import ConfigDict, Field, model_validator

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
    PlannerPositiveDecimal,
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


class PlannerAmountLimitInput(AllocationStrictModel):
    """A limit as an amount in the valuation currency (the normalizer checks the currency)."""

    kind: Literal["amount"]
    amount: PlannerMoneyInput


class PlannerShareLimitInput(AllocationStrictModel):
    """A limit as a share of the Tool's reference, a fraction from 0 to 1 (the normalizer checks the range).

    The reference is the money the plan works with: in the PAC the funding it can reach, which the plan page shows as its total.
    """

    kind: Literal["share"]
    share: PlannerFixedDecimal


type PlannerEntryLimitInput = Annotated[Union[PlannerAmountLimitInput, PlannerShareLimitInput], Field(discriminator="kind")]


class PlannerAssetTargetInput(AllocationStrictModel):
    """The target of an Asset: its weight and, each optional, a minimum and a maximum on its final value."""

    kind: Literal["asset"]
    asset_id: PlannerId
    weight: PlannerFixedDecimal
    minimum: PlannerEntryLimitInput | None = None
    maximum: PlannerEntryLimitInput | None = None


class PlannerCashTargetInput(AllocationStrictModel):
    """The target of a Broker's cash in one currency: a weight and optional limits on its final spendable cash.

    The PAC accepts limits only; a weight other than zero is «unsupported» there (contract §5.2).
    """

    kind: Literal["cash"]
    broker_id: PlannerId
    currency: CurrencyCode
    weight: PlannerFixedDecimal
    minimum: PlannerEntryLimitInput | None = None
    maximum: PlannerEntryLimitInput | None = None


type PlannerTargetEntryInput = Annotated[Union[PlannerAssetTargetInput, PlannerCashTargetInput], Field(discriminator="kind")]


# ---------------------------------------------------------------------------
# The Rebalancer's request, in its final form (contract 2.0.0 §5.4, S1 of project 67)
# ---------------------------------------------------------------------------


class RebalancerLevelFidelityInput(AllocationStrictModel):
    """A fidelity level: «cost-aware», «balanced» or «faithful». The normalizer maps it to its ``λ`` (specifica §6.3)."""

    kind: Literal["level"]
    level: Literal["cost_aware", "balanced", "faithful"]


class RebalancerCustomFidelityInput(AllocationStrictModel):
    """A custom fidelity: the distance weight ``λ`` itself, greater than zero. The interface converts the user's figure in money
    into it (the ``preview`` operation); the plan receives only ``λ``.

    ``lambda`` is a Python keyword, so the field is ``lambda_`` with the wire name as its alias, read and written by it."""

    # An instance is not validated again where another model receives it (``revalidate_instances``): a strict model re-reads
    # an instance by its field names, which the alias-only field refuses, so a plan with this fidelity could not publish its
    # basis (F3a step 10b of project 67). It is frozen and was validated once. Kept out of the docstring: the docstring is the
    # JSON schema's description, and the contract's fingerprint must not move.
    model_config = AllocationStrictModel.model_config | ConfigDict(serialize_by_alias=True, revalidate_instances="never")

    kind: Literal["custom"]
    lambda_: PlannerPositiveDecimal = Field(alias="lambda", description="The distance weight λ of the score J = λ·D/F + (F − W); greater than zero.")


class RebalancerTargetFirstFidelityInput(AllocationStrictModel):
    """«Target first»: the distance first, then the money lost; no ``λ``."""

    kind: Literal["target_first"]


type RebalancerFidelityInput = Annotated[
    Union[RebalancerLevelFidelityInput, RebalancerCustomFidelityInput, RebalancerTargetFirstFidelityInput],
    Field(discriminator="kind"),
]


class RebalancerTaxBasketInput(AllocationStrictModel):
    """A basket of gains and losses that offset each other, with its reference rate. No basket = no offsetting."""

    basket_id: PlannerId
    name: PlannerLabel
    reference_rate: PlannerFixedDecimal


class RebalancerAssetTaxInput(AllocationStrictModel):
    """How a sale of one Asset is taxed: the basket its gains and its losses go to (or none), the rate, the foreign withholding
    on gains. One row per Asset a plan may sell."""

    asset_id: PlannerId
    gain_basket_id: PlannerId | None = Field(description="The basket a realized gain of this Asset goes to; null = none.")
    loss_basket_id: PlannerId | None = Field(description="The basket a realized loss of this Asset goes to; null = none.")
    tax_rate: PlannerFixedDecimal
    foreign_withholding_rate: PlannerFixedDecimal = Field(default="0", description="Tax a foreign source withholds on a realized gain, before the domestic tax.")
    provenance_id: PlannerId


class RebalancerBrokerTaxInput(AllocationStrictModel):
    """Who pays the tax of a Broker's sales: ``administered``, the Broker withholds it; ``declarative``, the plan sets it aside.
    One row per Broker with sale routes; the interface writes the default, ``declarative``."""

    broker_id: PlannerId
    tax_regime: Literal["administered", "declarative"]
    provenance_id: PlannerId


class RebalancerBrokerLossScopeInput(AllocationStrictModel):
    kind: Literal["broker"]
    broker_id: PlannerId


class RebalancerDeclaredLossScopeInput(AllocationStrictModel):
    kind: Literal["declared"]


type RebalancerLossScopeInput = Annotated[Union[RebalancerBrokerLossScopeInput, RebalancerDeclaredLossScopeInput], Field(discriminator="kind")]


class RebalancerCarriedLossInput(AllocationStrictModel):
    """Losses carried from earlier years, in one scope (a Broker that withholds, or the declared income) and one basket."""

    scope: RebalancerLossScopeInput
    basket_id: PlannerId
    amount: PlannerMoneyInput
    provenance_id: PlannerId


class RebalancerCostBasisInput(AllocationStrictModel):
    """The average unit cost of one holding, in the valuation currency (the source gives it so)."""

    holding_id: PlannerId
    average_unit_cost: PlannerMoneyInput
    provenance_id: PlannerId


class RebalancerTaxInput(AllocationStrictModel):
    """The tax facts of the Rebalancer's sales (contract §5.4). Required only with sale routes under «Invest and sell», which
    the schema admits from C1 on; under «Invest only» it is empty."""

    baskets: list[RebalancerTaxBasketInput] = []
    assets: list[RebalancerAssetTaxInput] = []
    brokers: list[RebalancerBrokerTaxInput] = []
    carried_losses: list[RebalancerCarriedLossInput] = []
    cost_bases: list[RebalancerCostBasisInput] = []


class _PlannerScenarioInputBase(AllocationStrictModel):
    # ``plan`` computes the plan; ``preview`` (B4 of project 67, contract §11) reads the same request for the numbers the
    # screen shows before the calculation, with no optimizer. One model per service, so every validation path is the same
    # for both operations.
    operation: Literal["plan", "preview"]
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
    target_weights: list[PlannerTargetEntryInput]

    @model_validator(mode="after")
    def _validate_fx_rate_pair_keys(self) -> _PlannerScenarioInputBase:
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


class PacPlannerRequest(_PlannerScenarioInputBase):
    # The PAC declares its funding routes (specification §15 n. 2); the Rebalancer's are generated by the normalizer.
    funding_routes: list[PlannerFundingRouteInput] = []
    order_routes: list[PacOrderRouteInput]
    # `min_fragmentation` is deferred (TODO_FUTURI): the exact model keeps the
    # branch, the wire does not accept it.
    policy: Literal["proportional"]


class RebalancerPlannerRequest(_PlannerScenarioInputBase):
    """One request for both strategies (contract 2.0.0 §5.4): the strategy is a field, with the target fidelity beside it.

    No funding routes: the normalizer generates the deposits of the contributions and the transfers between Brokers. Until
    C1 the strategy admits only ``invest_only`` and no sale route: the schema refuses the rest, so a sale never reaches the
    engine before the engine models it (S1, D10 of project 67).
    """

    policy: Literal["invest_only"]
    target_fidelity: RebalancerFidelityInput
    holdings: list[PlannerHoldingInput] = []
    order_routes: list[RebalancerOrderRouteInput]
    tax: RebalancerTaxInput = RebalancerTaxInput()

    @model_validator(mode="after")
    def _invest_only_has_no_sale_route(self) -> RebalancerPlannerRequest:
        # «Invest only» sells nothing; C1 lifts this with the strategy field. A validator, so the fingerprint does not move then.
        if any(route.side == "sell" for route in self.order_routes):
            raise ValueError("invest_only takes no SELL order route")
        return self
