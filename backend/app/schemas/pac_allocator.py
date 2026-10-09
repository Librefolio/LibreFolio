"""Strict P1 analysis and additive v2 planning contracts for PAC/Rebalancer."""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from fractions import Fraction
from math import gcd
from typing import Annotated, Literal, Union

from pydantic import AfterValidator, ConfigDict, Field, StringConstraints, TypeAdapter, model_validator

from backend.app.schemas.common import Currency, StrictModel

_NONNEGATIVE = r"^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$"
_POSITIVE = r"^(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*)$"
_ISO_DATE = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$"


def _unicode_scalar_text(value: str) -> str:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("Text must contain Unicode scalar values")
    return value


def _calendar_date(value: str) -> str:
    date.fromisoformat(value)
    return value


class AllocationStrictModel(StrictModel):
    # Input defaults let a caller omit neutral values; the serialization schema still lists
    # every field as required, because results are dumped in full.
    model_config = ConfigDict(strict=True, frozen=True, revalidate_instances="always", json_schema_serialization_defaults_required=True)


CurrencyCode = Annotated[str, StringConstraints(strict=True, min_length=3, max_length=3, pattern=r"^[A-Z]{3}$"), AfterValidator(Currency.validate_code)]
ReferenceDate = Annotated[str, StringConstraints(strict=True, min_length=10, max_length=10, pattern=_ISO_DATE), AfterValidator(_calendar_date)]


# =============================================================================
# V2 PLANNER CONTRACTS — additive until the CP5 P1 migration
# =============================================================================


_PLANNER_FIXED_DECIMAL = r"^(?:0(?:\.[0-9]+)?|[1-9][0-9]*(?:\.[0-9]+)?|-(?:[1-9][0-9]*(?:\.[0-9]+)?|0\.[0-9]*[1-9][0-9]*))$"
_PLANNER_INTEGER = r"^(?:0|[1-9][0-9]*|-[1-9][0-9]*)$"
_PLANNER_POSITIVE_INTEGER = r"^[1-9][0-9]*$"
_PLANNER_ID = r"^[A-Za-z0-9][A-Za-z0-9._:@/-]*$"
_PLANNER_CODE = r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*$"
_PLANNER_MESSAGE_KEY = r"^[A-Za-z0-9][A-Za-z0-9_.-]*$"
_UTC_TIMESTAMP = r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?Z$"
_JS_SAFE_INTEGER = 9_007_199_254_740_991
_PLANNER_FX_PAIR = r"^[A-Z]{3}/[A-Z]{3}$"


def _planner_fixed_decimal(value: str) -> str:
    parsed = Decimal(value)
    if not parsed.is_finite():
        raise ValueError("Decimal text must be finite")
    if parsed.is_zero() and value.startswith("-"):
        raise ValueError("Decimal text must not encode negative zero")
    return value


def _planner_nonnegative_decimal(value: str) -> str:
    if Decimal(value) < 0:
        raise ValueError("Decimal text must be nonnegative")
    return value


def _planner_positive_decimal(value: str) -> str:
    if Decimal(value) <= 0:
        raise ValueError("Decimal text must be positive")
    return value


def _planner_positive_whole_decimal(value: str) -> str:
    parsed = Decimal(value)
    if parsed <= 0 or parsed != parsed.to_integral_value():
        raise ValueError("Quantity step must be a positive whole number")
    return value


def _planner_integer_text(value: str) -> str:
    if Decimal(value).is_zero() and value.startswith("-"):
        raise ValueError("Integer text must not encode negative zero")
    return value


def _planner_utc_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("Timestamp must be UTC")
    return value


def _planner_canonical_fx_pair(value: str) -> str:
    first, _, second = value.partition("/")
    if first >= second:
        raise ValueError("Canonical FX pair must name two distinct currencies in ascending alphabetical order")
    return value


def _require_unique(values: list[object], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _collect_currency_codes(value: object) -> set[str]:
    currencies: set[str] = set()

    def visit(node: object) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if key in {"currency", "currency_code", "source_currency", "destination_currency"} and isinstance(child, str):
                    currencies.add(child)
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return currencies


PlannerId = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128, pattern=_PLANNER_ID)]
PlannerRef = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=256, pattern=_PLANNER_ID)]
PlannerCode = Annotated[str, StringConstraints(strict=True, min_length=3, max_length=96, pattern=_PLANNER_CODE)]
PlannerIssueCode = Literal[
    "allocation.asset_inactive_not_buyable",
    "allocation.asset_type_missing",
    "allocation.broker_execution_profile_unsupported",
    "allocation.broker_inactive",
    "allocation.capacity_unsupported",
    "allocation.cash_selection_invalid",
    "allocation.classification_geography_missing",
    "allocation.classification_invalid",
    "allocation.classification_sector_missing",
    "allocation.coefficient_envelope_unsupported",
    "allocation.currency_mismatch",
    "allocation.deployment_omitted",
    "allocation.duplicate_id",
    "allocation.dynamic_fee_unsupported",
    "allocation.economic_share_out_of_range",
    "allocation.execution_margin_missing",
    "allocation.execution_margin_rate_out_of_range",
    "allocation.exposure_total_exceeds_one",
    "allocation.exposure_weight_out_of_range",
    "allocation.fee_floor_exceeds_cap",
    "allocation.fee_rate_out_of_range",
    "allocation.fee_schedule_missing",
    "allocation.fiscal_currency_missing",
    "allocation.funding_cap_negative",
    "allocation.fx_rate_inconsistent",
    "allocation.fx_rate_missing",
    "allocation.fx_spread_rate_out_of_range",
    "allocation.identity_fx_rate_not_allowed",
    "allocation.invalid_quote_basis",
    "allocation.negative_cash_unsupported",
    "allocation.negative_contribution",
    "allocation.negative_fee_amount",
    "allocation.negative_inventory_unsupported",
    "allocation.no_additional_buy_feasible",
    "allocation.no_positive_order_fundable",
    "allocation.no_selected_funding",
    "allocation.nonpositive_fx_rate",
    "allocation.nonpositive_order_amount_step",
    "allocation.nonpositive_price",
    "allocation.nonpositive_quantity_step",
    "allocation.order_amount_step_missing",
    "allocation.order_cap_nonpositive",
    "allocation.order_minimum_exceeds_cap",
    "allocation.order_minimum_negative",
    "allocation.planning_quantity_negative",
    "allocation.price_missing",
    "allocation.price_order_invalid",
    "allocation.provenance_not_found",
    "allocation.provenance_stale_confirmed",
    "allocation.quote_base_quantity_missing",
    "allocation.reference_not_found",
    "allocation.required_buy_sell_conflict",
    "allocation.required_min_notional_unfunded",
    "allocation.route_priority_negative",
    "allocation.saved_fx_invalid",
    "allocation.solver_limit_no_incumbent",
    "allocation.target_total_not_one",
    "allocation.target_weight_missing",
    "allocation.target_weight_out_of_range",
    "allocation.tax_netting_unsupported",
    "allocation.valuation_currency_missing",
    "allocation.wac_missing",
    "allocation.zero_selected_funding",
    "pac_allocator.initial_holding_forbidden",
    "pac_allocator.sell_forbidden",
    "portfolio_rebalancer.baseline_incumbent_missing",
    "portfolio_rebalancer.carried_loss_negative",
    "portfolio_rebalancer.cost_basis_negative",
    "portfolio_rebalancer.holdings_missing",
    "portfolio_rebalancer.nonpositive_current_portfolio",
    "portfolio_rebalancer.sell_fee_missing",
    "portfolio_rebalancer.sell_inventory_exceeded",
    "portfolio_rebalancer.sell_irreducibility_unresolved",
    "portfolio_rebalancer.sell_to_idle_forbidden",
    "portfolio_rebalancer.tax_rate_missing",
    "portfolio_rebalancer.tax_rate_out_of_range",
    "portfolio_rebalancer.withholding_missing",
]
FundingActionReasonCode = Literal["allocation.fund_declared_orders"]
DeploymentReasonCode = Literal[
    "allocation.deployment_omitted",
    "allocation.no_actions_selected",
    "allocation.no_additional_buy_feasible",
    "allocation.primary_is_deployment",
]
NotProvenReasonCode = Literal[
    "allocation.exact_proof_not_established",
    "portfolio_rebalancer.sell_irreducibility_unresolved",
]
PlannerMessageKey = Annotated[str, StringConstraints(strict=True, min_length=3, max_length=160, pattern=_PLANNER_MESSAGE_KEY)]
PlannerLabel = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128), AfterValidator(_unicode_scalar_text)]
PlannerLongLabel = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=256), AfterValidator(_unicode_scalar_text)]
PlannerTimestamp = Annotated[
    str,
    StringConstraints(strict=True, min_length=20, max_length=27, pattern=_UTC_TIMESTAMP),
    AfterValidator(_planner_utc_timestamp),
]
PlannerFixedDecimal = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=96, pattern=_PLANNER_FIXED_DECIMAL),
    AfterValidator(_planner_fixed_decimal),
]
PlannerWholeQuantityStep = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=96, pattern=_PLANNER_INTEGER),
]
PlannerNonNegativeDecimal = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=96, pattern=_NONNEGATIVE),
    AfterValidator(_planner_nonnegative_decimal),
]
PlannerPositiveDecimal = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=96, pattern=_POSITIVE),
    AfterValidator(_planner_positive_decimal),
]
PlannerPositiveWholeDecimal = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=96, pattern=_PLANNER_POSITIVE_INTEGER),
    AfterValidator(_planner_positive_whole_decimal),
]
PlannerIntegerText = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=192, pattern=_PLANNER_INTEGER),
    AfterValidator(_planner_integer_text),
]
PlannerPositiveIntegerText = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=192, pattern=_PLANNER_POSITIVE_INTEGER),
]
PlannerSafeInteger = Annotated[int, Field(strict=True, ge=0, le=_JS_SAFE_INTEGER)]
PlannerPositiveInteger = Annotated[int, Field(strict=True, gt=0, le=_JS_SAFE_INTEGER)]
PlannerWireInteger = Annotated[int, Field(strict=True, ge=-_JS_SAFE_INTEGER, le=_JS_SAFE_INTEGER)]
QuantityUnit = Literal["asset_unit"]
OrderSide = Literal["buy", "sell"]
PlannerConversionMode = Literal["manual", "automatic"]


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


class PlannerMoneyInput(AllocationStrictModel):
    amount: PlannerFixedDecimal
    currency: CurrencyCode


class PlannerNonNegativeMoneyInput(AllocationStrictModel):
    amount: PlannerNonNegativeDecimal
    currency: CurrencyCode


class PlannerPositiveMoneyInput(AllocationStrictModel):
    amount: PlannerPositiveDecimal
    currency: CurrencyCode


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
        # format/ordering constraint (regex + `_planner_canonical_fx_pair`) at runtime.
        # Both codes are ISO-validated like every `CurrencyCode`: the normalizer
        # derives a minor unit for each referenced currency.
        for pair in self.fx_rates:
            if not re.fullmatch(_PLANNER_FX_PAIR, pair):
                raise ValueError(f"FX rate key {pair!r} must be an uppercase 'AAA/BBB' currency pair")
            _planner_canonical_fx_pair(pair)
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


# -----------------------------------------------------------------------------
# V2 exact output scalars, issues, evidence, and authoritative result rows
# -----------------------------------------------------------------------------


class FiniteDecimal(AllocationStrictModel):
    """Exact branch used only for a terminating base-10 value inside the bounded wire envelope."""

    kind: Literal["finite_decimal"]
    value: PlannerFixedDecimal


class ExactRatio(AllocationStrictModel):
    """Reduced exact branch used when the value has no bounded terminating representation."""

    kind: Literal["exact_ratio"]
    numerator: PlannerIntegerText
    denominator: PlannerPositiveIntegerText
    display_decimal: PlannerFixedDecimal = Field(description="Backend-authored display projection; never authoritative.")
    display_scale: Annotated[int, Field(strict=True, ge=0, le=18)]
    display_authority: Literal["non_authoritative"]

    @model_validator(mode="after")
    def validate_canonical_ratio(self) -> ExactRatio:
        if gcd(abs(int(self.numerator)), int(self.denominator)) != 1:
            raise ValueError("Exact ratio must be reduced to canonical terms")
        return self


type ExactNumber = Annotated[Union[FiniteDecimal, ExactRatio], Field(discriminator="kind")]


def _fixed_fraction(value: str) -> Fraction:
    """Convert canonical fixed-point text without applying Decimal context precision."""

    return Fraction(Decimal(value))


def _exact_fraction(value: FiniteDecimal | ExactRatio) -> Fraction:
    if isinstance(value, FiniteDecimal):
        return _fixed_fraction(value.value)
    return Fraction(int(value.numerator), int(value.denominator))


def _money_fraction(value: ExactMoney) -> Fraction:
    return _exact_fraction(value.value)


class ExactMoney(AllocationStrictModel):
    value: ExactNumber
    currency: CurrencyCode


class ExactPrice(AllocationStrictModel):
    value: ExactNumber
    currency: CurrencyCode
    quote_base_quantity: PlannerPositiveDecimal
    quantity_unit: QuantityUnit

    @model_validator(mode="after")
    def validate_positive_value(self) -> ExactPrice:
        if _exact_fraction(self.value) <= 0:
            raise ValueError("Exact price must be positive")
        return self


class ExactFxRate(AllocationStrictModel):
    source_currency: CurrencyCode
    destination_currency: CurrencyCode = Field(description="Currency units received per one source-currency unit.")
    value: ExactNumber

    @model_validator(mode="after")
    def validate_rate(self) -> ExactFxRate:
        if self.source_currency == self.destination_currency:
            raise ValueError("Published FX action rates must be non-identity")
        if _exact_fraction(self.value) <= 0:
            raise ValueError("Exact FX rate must be positive")
        return self


class AvailableExactNumber(AllocationStrictModel):
    kind: Literal["available"]
    value: ExactNumber


class UnavailableExactNumber(AllocationStrictModel):
    kind: Literal["unavailable"]
    reason: Literal["zero_current_invested", "zero_final_invested", "not_applicable", "dependency_unavailable"]


type ExactNumberAvailability = Annotated[
    Union[AvailableExactNumber, UnavailableExactNumber],
    Field(discriminator="kind"),
]


def _available_fraction(value: AvailableExactNumber | UnavailableExactNumber) -> Fraction | None:
    if isinstance(value, AvailableExactNumber):
        return _exact_fraction(value.value)
    return None


def _validate_weight_availability(
    values: list[AvailableExactNumber | UnavailableExactNumber],
    total: Fraction,
    zero_reason: str,
    label: str,
) -> None:
    fractions = [_available_fraction(value) for value in values]
    if total == 0:
        if any(value is not None for value in fractions):
            raise ValueError(f"{label} weights must be unavailable at zero invested value")
        if any(value.reason != zero_reason for value in values if isinstance(value, UnavailableExactNumber)):
            raise ValueError(f"{label} weights must use the explicit zero-invested reason")
        return
    if any(value is None or value < 0 or value > 1 for value in fractions):
        raise ValueError(f"{label} weights must all be available unit-interval values")
    if sum((value for value in fractions if value is not None), Fraction()) != 1:
        raise ValueError(f"{label} weights must form a complete unit vector")


PlannerIssueSection = Literal[
    "input",
    "assets",
    "brokers",
    "holdings",
    "cash",
    "contributions",
    "funding",
    "routing",
    "fx",
    "targets",
    "policy",
    "proof",
    "liquidity",
    "result",
]
PlannerIssueEntityKind = Literal[
    "scenario",
    "asset",
    "broker",
    "holding",
    "currency",
    "cash",
    "contribution",
    "funding_route",
    "fx_rate",
    "order_route",
    "order",
    "solution",
]


class SectionIssuePath(AllocationStrictModel):
    kind: Literal["section"]
    section: PlannerIssueSection


class EntityIssuePath(AllocationStrictModel):
    kind: Literal["entity"]
    section: PlannerIssueSection
    entity_kind: PlannerIssueEntityKind
    entity_id: PlannerId


class FieldIssuePath(AllocationStrictModel):
    kind: Literal["field"]
    section: PlannerIssueSection
    entity_kind: PlannerIssueEntityKind
    entity_id: PlannerId
    field: PlannerCode


type PlannerIssuePath = Annotated[
    Union[SectionIssuePath, EntityIssuePath, FieldIssuePath],
    Field(discriminator="kind"),
]


class TextIssueParam(AllocationStrictModel):
    kind: Literal["text"]
    name: PlannerId
    value: PlannerLongLabel


class IdIssueParam(AllocationStrictModel):
    kind: Literal["id"]
    name: PlannerId
    value: PlannerId


class CountIssueParam(AllocationStrictModel):
    kind: Literal["count"]
    name: PlannerId
    value: PlannerSafeInteger


class DecimalIssueParam(AllocationStrictModel):
    kind: Literal["decimal"]
    name: PlannerId
    value: PlannerFixedDecimal


class CurrencyIssueParam(AllocationStrictModel):
    kind: Literal["currency"]
    name: PlannerId
    value: CurrencyCode


class MoneyIssueParam(AllocationStrictModel):
    kind: Literal["money"]
    name: PlannerId
    value: PlannerMoneyInput


type PlannerIssueParam = Annotated[
    Union[TextIssueParam, IdIssueParam, CountIssueParam, DecimalIssueParam, CurrencyIssueParam, MoneyIssueParam],
    Field(discriminator="kind"),
]


class PlannerIssue(AllocationStrictModel):
    code: PlannerIssueCode
    severity: Literal["info", "warning", "error"]
    kind: Literal["missing", "invalid", "unsupported", "constraint", "proof", "info"]
    path: PlannerIssuePath
    message_key: PlannerMessageKey
    params: list[PlannerIssueParam]

    @model_validator(mode="after")
    def validate_param_names(self) -> PlannerIssue:
        _require_unique([param.name for param in self.params], "Issue parameter names")
        return self


class CountUnit(AllocationStrictModel):
    kind: Literal["count"]


class ValuationMoneyUnit(AllocationStrictModel):
    kind: Literal["valuation_money"]
    currency_code: CurrencyCode


class ValuationMoneySquaredUnit(AllocationStrictModel):
    kind: Literal["valuation_money_squared"]
    currency_code: CurrencyCode


class OrdinalPenaltyUnit(AllocationStrictModel):
    kind: Literal["ordinal_penalty"]


class CanonicalKeyUnit(AllocationStrictModel):
    kind: Literal["canonical_key"]


type NumericObjectiveUnit = Annotated[
    Union[CountUnit, ValuationMoneyUnit, ValuationMoneySquaredUnit, OrdinalPenaltyUnit],
    Field(discriminator="kind"),
]

ObjectiveCode = Literal[
    "fixed_l2",
    "shortfall",
    "turnover",
    "explicit_cost",
    "incremental_cost",
    "split_asset_count",
    "active_order_rows",
    "incremental_order_rows",
    "route_priority",
]
ObjectiveSense = Literal["min", "max"]

_ObjectiveSignDomain = Literal["signed", "nonnegative", "nonnegative_integer"]
# Keep this exhaustive: every future ObjectiveCode must choose its sign domain.
_OBJECTIVE_SIGN_DOMAINS: dict[ObjectiveCode, _ObjectiveSignDomain] = {
    "fixed_l2": "nonnegative",
    "shortfall": "signed",
    "turnover": "nonnegative",
    "explicit_cost": "nonnegative",
    "incremental_cost": "nonnegative",
    "split_asset_count": "nonnegative_integer",
    "active_order_rows": "nonnegative_integer",
    "incremental_order_rows": "nonnegative_integer",
    "route_priority": "nonnegative_integer",
}


def _objective_unit_kind(code: ObjectiveCode) -> str:
    if code == "fixed_l2":
        return "valuation_money_squared"
    if code in {"shortfall", "turnover", "explicit_cost", "incremental_cost"}:
        return "valuation_money"
    if code in {"split_asset_count", "active_order_rows", "incremental_order_rows"}:
        return "count"
    return "ordinal_penalty"


class SolverSettingEvidence(AllocationStrictModel):
    name: PlannerId
    value: PlannerLongLabel


class SolverToleranceEvidence(AllocationStrictModel):
    feasibility: PlannerNonNegativeDecimal
    integrality: PlannerNonNegativeDecimal
    absolute_gap: PlannerNonNegativeDecimal
    relative_gap: PlannerNonNegativeDecimal


class SolverStageEvidence(AllocationStrictModel):
    """Non-authoritative floating solver report; never an exact objective value.

    ``infeasible`` is SCIP's own verdict on the first, still-global stage, and
    it carries no observation: an infeasible solve has no primal, no dual and
    no gap. No later stage can carry it — a face emptied by earlier pins is an
    anomaly of the pins, not a statement about the scenario — so such a stage
    is reported ``unfinished``.
    """

    kind: Literal["reported_floating"]
    stage: PlannerId
    objective_code: ObjectiveCode
    ordinal: PlannerPositiveInteger
    status: Literal["finished", "unfinished", "infeasible"]
    scope: Literal["global", "incumbent_face"]
    sense: ObjectiveSense
    unit: NumericObjectiveUnit
    primal: PlannerFixedDecimal | None
    dual: PlannerFixedDecimal | None
    absolute_gap: PlannerNonNegativeDecimal | None
    relative_gap: PlannerNonNegativeDecimal | None
    tolerances: SolverToleranceEvidence
    engine: PlannerLabel
    version: PlannerLabel
    settings: list[SolverSettingEvidence]

    @model_validator(mode="after")
    def validate_objective_unit(self) -> SolverStageEvidence:
        if self.unit.kind != _objective_unit_kind(self.objective_code):
            raise ValueError("Solver stage unit does not match objective code")
        observations = (self.primal, self.dual, self.absolute_gap, self.relative_gap)
        if self.status == "finished" and any(value is None for value in observations):
            raise ValueError("Finished solver stage evidence requires finite primal, dual, and gaps")
        if self.status == "infeasible":
            if self.ordinal != 1 or self.scope != "global":
                raise ValueError("Only the first, global solver stage can report infeasibility")
            if any(value is not None for value in observations):
                raise ValueError("An infeasible solver stage has no primal, dual, or gap")
        if self.primal is not None and self.dual is not None:
            primal = _fixed_fraction(self.primal)
            dual = _fixed_fraction(self.dual)
            if (self.sense == "min" and dual > primal) or (self.sense == "max" and primal > dual):
                raise ValueError("Reported bound ordering must match the objective sense")
            if self.absolute_gap is not None and _fixed_fraction(self.absolute_gap) < abs(primal - dual):
                raise ValueError("Reported absolute gap must bound the primal-dual difference")
        return self


class ReportedFloatingSolverEvidence(AllocationStrictModel):
    """What SCIP did, stage by stage; every ready result carries it (D-X1)."""

    kind: Literal["reported_floating"]
    stages: Annotated[list[SolverStageEvidence], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_stage_order(self) -> ReportedFloatingSolverEvidence:
        ordinals = [stage.ordinal for stage in self.stages]
        codes = [stage.objective_code for stage in self.stages]
        if ordinals != sorted(ordinals) or len(ordinals) != len(set(ordinals)) or len(codes) != len(set(codes)):
            raise ValueError("Solver stages must have unique codes and ascending ordinals")
        statuses = [stage.status for stage in self.stages]
        if "infeasible" in statuses:
            # Nothing runs after an infeasible first stage, so nothing is reported after it.
            if len(statuses) != 1:
                raise ValueError("An infeasible solver stage must be the only reported stage")
            return self
        if statuses != sorted(statuses, key={"finished": 0, "unfinished": 1}.__getitem__):
            raise ValueError("Finished solver stages must precede unfinished stages")
        return self


class SolverStatusWitness(AllocationStrictModel):
    """SCIP's own status, which is the proof (D-X1).

    Names the objective stages the solver closed — at the optimum for
    ``optimal_proven``, as infeasible for ``infeasibility_proven``. Engine,
    version, tolerances and gaps already live on the solver evidence, which
    the ready result binds to this witness stage by stage.
    """

    kind: Literal["solver_status"]
    objective_codes: Annotated[list[ObjectiveCode], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_objective_codes(self) -> SolverStatusWitness:
        if len(self.objective_codes) != len(set(self.objective_codes)):
            raise ValueError("Solver-status witness objective codes must be unique")
        return self


class OptimalProvenProof(AllocationStrictModel):
    kind: Literal["optimal_proven"]
    proof_source: Literal["solver_status"]
    witness: SolverStatusWitness
    tie_break_closed: Literal[True]


class NotProvenProof(AllocationStrictModel):
    kind: Literal["not_proven"]
    reason_code: NotProvenReasonCode


class InfeasibilityProvenProof(AllocationStrictModel):
    kind: Literal["infeasibility_proven"]
    proof_source: Literal["solver_status"]
    witness: SolverStatusWitness

    @model_validator(mode="after")
    def validate_first_stage_only(self) -> InfeasibilityProvenProof:
        if len(self.witness.objective_codes) != 1:
            raise ValueError("An infeasibility proof names exactly the first objective stage")
        return self


type ReadyPlanProof = Annotated[
    Union[OptimalProvenProof, NotProvenProof],
    Field(discriminator="kind"),
]


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
        _require_unique([asset.asset_id for asset in self.assets], "Catalog Asset IDs")
        _require_unique([broker.broker_id for broker in self.brokers], "Catalog Broker IDs")
        _require_unique([currency.currency for currency in self.currencies], "Catalog currencies")
        if any(_fixed_fraction(currency.minor_unit) <= 0 for currency in self.currencies):
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
        if _exact_fraction(self.effective_rate.value) > _exact_fraction(self.spot_rate.value):
            raise ValueError("Effective FX rate cannot exceed the approved spot rate")
        if _exact_fraction(self.spread_loss.value) < 0:
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
        if _exact_fraction(self.effective_rate.value) > _exact_fraction(self.spot_rate.value):
            raise ValueError("Effective conversion rate cannot exceed the approved spot rate")
        if _exact_fraction(self.spread_loss.value) < 0:
            raise ValueError("Conversion spread loss cannot be negative")
        _require_unique(self.fx_action_ids, "Conversion FX action IDs")
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
        if _exact_fraction(self.value) <= 0:
            raise ValueError("Order economic quantity must be positive")
        return self


class EstimatedExactRatioQuantity(AllocationStrictModel):
    kind: Literal["estimated_exact_ratio"]
    value: ExactRatio
    unit: QuantityUnit

    @model_validator(mode="after")
    def validate_positive_value(self) -> EstimatedExactRatioQuantity:
        if _exact_fraction(self.value) <= 0:
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
        if _exact_fraction(self.charge_price.value) < _exact_fraction(self.mid_price.value):
            raise ValueError("BUY charge price cannot be below mid price")
        if self.fee.currency != self.cash_debit.currency or self.buffer.currency != self.cash_debit.currency:
            raise ValueError("BUY fee and buffer must use the order currency")
        if isinstance(self.instruction, MonetaryAmountInstruction):
            if {self.instruction.amount.currency, self.instruction.order_amount_step.currency} != {self.cash_debit.currency}:
                raise ValueError("Monetary BUY instruction must use the order currency")
        if _exact_fraction(self.mid_value.value) <= 0:
            raise ValueError("BUY mid value must be positive")
        if _exact_fraction(self.execution_margin_cost.value) < 0:
            raise ValueError("BUY execution-margin cost cannot be negative")
        if _exact_fraction(self.fx_cost.value) != 0:
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
        if _exact_fraction(self.sell_price.value) > _exact_fraction(self.mid_price.value):
            raise ValueError("SELL execution price cannot exceed mid price")
        posted_currencies = {self.fee.currency, self.tax_reserve.currency, self.spendable_credit.currency}
        if posted_currencies != {self.gross_credit.currency}:
            raise ValueError("SELL fee, tax reserve, and spendable credit must use the order currency")
        if isinstance(self.instruction, MonetaryAmountInstruction):
            if {self.instruction.amount.currency, self.instruction.order_amount_step.currency} != {self.gross_credit.currency}:
                raise ValueError("Monetary SELL instruction must use the order currency")
        if _fixed_fraction(self.spendable_credit.amount) != _fixed_fraction(self.gross_credit.amount) - _fixed_fraction(self.fee.amount) - _fixed_fraction(self.tax_reserve.amount):
            raise ValueError("SELL spendable credit must equal gross credit less fee and tax reserve")
        if _exact_fraction(self.mid_value.value) <= 0:
            raise ValueError("SELL mid value must be positive")
        if _exact_fraction(self.execution_margin_cost.value) < 0:
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
        # to HALF_UP rounding is published with the top-up that covers it
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
        if any(_fixed_fraction(getattr(self, name)) < 0 for name in nonnegative_fields):
            raise ValueError("Published ledger amounts cannot be negative")
        expected_spendable = (
            _fixed_fraction(self.initial_selected)
            + _fixed_fraction(self.funding_in)
            + _fixed_fraction(self.fx_credit)
            + _fixed_fraction(self.gross_sell_credit)
            - _fixed_fraction(self.funding_out)
            - _fixed_fraction(self.fx_debit)
            - _fixed_fraction(self.buy_debit)
            - _fixed_fraction(self.buy_fees)
            - _fixed_fraction(self.sell_fees)
            - _fixed_fraction(self.broker_withheld_tax)
            - _fixed_fraction(self.self_reserved_tax)
        )
        if expected_spendable != _fixed_fraction(self.final_spendable):
            raise ValueError("Ledger spendable balance does not reconcile its posted debits and credits")
        if _fixed_fraction(self.final_spendable) + _fixed_fraction(self.self_reserved_tax) != _fixed_fraction(self.final_physical):
            raise ValueError("Ledger spendable balance does not reconcile")
        return self


class PlannerRoundingTopUp(AllocationStrictModel):
    """Cash one ledger pool lacks because the exact replay rounds HALF_UP (QX1-b).

    ``amount`` is what to add on ``broker_id`` in ``currency`` for the plan to
    execute: the pool's negative final balance, negated. ``rounded_postings``
    counts the pool's postings that carry a quantum (BUY debit, nonzero fee, FX
    credit), and bounds ``amount`` at that many minor units. ``valuation_amount``
    is ``amount`` in the scenario valuation currency.
    """

    broker_id: PlannerId
    currency: CurrencyCode
    amount: PlannerPositiveDecimal
    rounded_postings: PlannerPositiveInteger
    valuation_amount: ExactMoney

    @model_validator(mode="after")
    def validate_positive_valuation(self) -> PlannerRoundingTopUp:
        if _money_fraction(self.valuation_amount) <= 0:
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
        target = _exact_fraction(self.target_weight)
        final = _available_fraction(self.final_weight)
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
        target = _exact_fraction(self.target_weight)
        before = _available_fraction(self.before_weight)
        final = _available_fraction(self.final_weight)
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
    rounding_bound: ExactMoney
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
        sign_domain = _OBJECTIVE_SIGN_DOMAINS.get(self.objective_code)
        if sign_domain is None:
            raise ValueError("Objective code must declare its sign domain")
        if self.unit.kind != _objective_unit_kind(self.objective_code):
            raise ValueError("Objective unit does not match objective code")
        value = _exact_fraction(self.value)
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
        _require_unique(self.ordered_keys, "Tie-break keys")
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


def _validate_action_ids_and_sequences(solution: PacPlanSolution | RebalancerPlanSolution, label: str) -> None:
    """IDs unique across every action section; sequences unique across the sequenced ones.

    FX actions carry no sequence: they are engine decisions, executed through their
    conversion. A manual conversion is a step of its own; an automatic one happens
    inside the orders, so it has no sequence either.
    """
    ids = [
        *(row.action_id for row in solution.funding_actions),
        *(row.action_id for row in solution.fx_actions),
        *(row.conversion_id for row in solution.conversions),
        *(row.order_id for row in solution.order_rows),
    ]
    _require_unique(ids, f"{label} action IDs")
    sections = (
        [row.sequence for row in solution.funding_actions],
        [row.sequence for row in solution.conversions if row.sequence is not None],
        [row.sequence for row in solution.order_rows],
    )
    _require_unique([sequence for section in sections for sequence in section], f"{label} action sequences")
    if any(section != sorted(section) for section in sections):
        raise ValueError(f"{label} action sections must be sequence-ordered")


def _validate_conversions(solution: PacPlanSolution | RebalancerPlanSolution, label: str) -> None:
    """Bind every FX action to its Broker x currency-pair conversion.

    A conversion is a pure aggregate: it covers exactly the actions that reference it,
    repeats their Broker, currency pair and rates, and carries their exact sums. One
    conversion per pair, and one mode per Broker, because the mode is a Broker input.
    """
    _require_unique([row.conversion_id for row in solution.conversions], f"{label} conversion IDs")
    _require_unique([(row.broker_id, row.source_debit.currency, row.destination_credit.currency) for row in solution.conversions], f"{label} conversion pairs")
    modes: dict[str, str] = {}
    if any(modes.setdefault(row.broker_id, row.mode) != row.mode for row in solution.conversions):
        raise ValueError(f"{label} conversions must use one mode per Broker")
    conversions = {row.conversion_id: row for row in solution.conversions}
    members: dict[str, list[PlannerFxAction]] = {conversion_id: [] for conversion_id in conversions}
    for action in solution.fx_actions:
        conversion = conversions.get(action.conversion_id)
        if conversion is None:
            raise ValueError(f"{label} FX actions must reference a published conversion")
        if (action.broker_id, action.source_debit.currency, action.destination_credit.currency) != (conversion.broker_id, conversion.source_debit.currency, conversion.destination_credit.currency):
            raise ValueError(f"{label} FX actions must match their conversion's Broker and currency pair")
        if _exact_fraction(action.spot_rate.value) != _exact_fraction(conversion.spot_rate.value) or _exact_fraction(action.effective_rate.value) != _exact_fraction(conversion.effective_rate.value):
            raise ValueError(f"{label} FX actions must use their conversion's rates")
        members[action.conversion_id].append(action)
    for conversion_id, conversion in conversions.items():
        actions = members[conversion_id]
        if set(conversion.fx_action_ids) != {action.action_id for action in actions}:
            raise ValueError(f"{label} conversions must list exactly the FX actions that reference them")
        if (
            _fixed_fraction(conversion.source_debit.amount) != sum((_fixed_fraction(action.source_debit.amount) for action in actions), Fraction())
            or _fixed_fraction(conversion.destination_credit.amount) != sum((_fixed_fraction(action.destination_credit.amount) for action in actions), Fraction())
            or _money_fraction(conversion.spread_loss) != sum((_money_fraction(action.spread_loss) for action in actions), Fraction())
        ):
            raise ValueError(f"{label} conversion totals must equal the exact sums of their FX actions")
        if set(conversion.provenance_ids) != {provenance_id for action in actions for provenance_id in action.provenance_ids}:
            raise ValueError(f"{label} conversion provenance must be the union of its FX actions' provenance")


def _validate_pac_rounding_top_ups(solution: PacPlanSolution) -> None:
    """Bind the top-ups to the ledger pools they excuse.

    One top-up per negative pool, for exactly the missing amount; its rounded
    postings can be no more than the pool's own rows carry: a BUY debit and a
    fee per order paying from the pool, a credit per FX action into it. It is
    only a cap: a fee that rounds to zero is not posted, and still counts in
    the order row. The minor-unit bound needs the catalogue, so it lives in
    ``_validate_ready_solution``.
    """
    _require_unique([(row.broker_id, row.currency) for row in solution.rounding_top_ups], "PAC rounding top-up scopes")
    deficits = {(row.broker_id, row.currency): -_fixed_fraction(row.final_spendable) for row in solution.ledger_rows if _fixed_fraction(row.final_spendable) < 0}
    if {(row.broker_id, row.currency): _fixed_fraction(row.amount) for row in solution.rounding_top_ups} != deficits:
        raise ValueError("PAC rounding top-ups must cover exactly the negative ledger balances")
    for top_up in solution.rounding_top_ups:
        scope = (top_up.broker_id, top_up.currency)
        orders = sum(1 for row in solution.order_rows if (row.broker_id, row.cash_debit.currency) == scope)
        fx_credits = sum(1 for row in solution.fx_actions if (row.broker_id, row.destination_credit.currency) == scope)
        if top_up.rounded_postings > 2 * orders + fx_credits:
            raise ValueError("A PAC rounding top-up cannot count more rounded postings than its ledger scope carries")


class PacPlanSolution(AllocationStrictModel):
    solution_id: PlannerId
    solution_kind: Literal["primary"]
    validation: Literal["decimal_verified"]
    asset_rows: list[PacAssetPlanRow]
    funding_actions: list[PlannerFundingAction]
    fx_actions: list[PlannerFxAction]
    conversions: list[PlannerConversion] = Field(description="One conversion per Broker x currency pair, aggregating the FX actions; manual ones are numbered steps.")
    order_rows: list[PlannerBuyOrderRow]
    ledger_rows: list[PlannerLedgerRow]
    rounding_top_ups: list[PlannerRoundingTopUp] = Field(description="One top-up per ledger pool left short by HALF_UP rounding; empty when every pool balances.")
    exposure_rows: list[PacExposurePlanRow]
    accounting: PlannerAccountingSummary
    costs: PlannerCostTotals
    objectives: PlannerObjectiveResults

    @model_validator(mode="after")
    def validate_authoritative_rows(self) -> PacPlanSolution:
        _require_unique([row.asset_id for row in self.asset_rows], "PAC Asset rows")
        _validate_action_ids_and_sequences(self, "PAC")
        _validate_conversions(self, "PAC")
        _require_unique([(row.broker_id, row.currency) for row in self.ledger_rows], "PAC ledger scopes")
        _require_unique([(row.dimension, row.category_id) for row in self.exposure_rows], "PAC exposure rows")
        _validate_pac_rounding_top_ups(self)
        return self


class RebalancerPlanSolution(AllocationStrictModel):
    solution_id: PlannerId
    solution_kind: Literal["primary"]
    validation: Literal["decimal_verified"]
    asset_rows: list[RebalancerAssetPlanRow]
    funding_actions: list[PlannerFundingAction]
    fx_actions: list[PlannerFxAction]
    conversions: list[PlannerConversion] = Field(description="One conversion per Broker x currency pair, aggregating the FX actions; manual ones are numbered steps.")
    order_rows: list[RebalancerOrderRow]
    sell_irreducibility: list[SellIrreducibilityEvidence]
    ledger_rows: list[PlannerLedgerRow]
    exposure_rows: list[RebalancerExposurePlanRow]
    accounting: PlannerAccountingSummary
    costs: PlannerCostTotals
    objectives: PlannerObjectiveResults

    @model_validator(mode="after")
    def validate_authoritative_rows(self) -> RebalancerPlanSolution:
        _require_unique([row.asset_id for row in self.asset_rows], "Rebalancer Asset rows")
        _validate_action_ids_and_sequences(self, "Rebalancer")
        _validate_conversions(self, "Rebalancer")
        _require_unique([(row.broker_id, row.currency) for row in self.ledger_rows], "Rebalancer ledger scopes")
        # The Rebalancer has no rounding top-ups, so no pool of it may end short.
        if any(_fixed_fraction(row.final_spendable) < 0 or _fixed_fraction(row.final_physical) < 0 for row in self.ledger_rows):
            raise ValueError("Rebalancer ledger balances cannot be negative")
        _require_unique([(row.dimension, row.category_id) for row in self.exposure_rows], "Rebalancer exposure rows")
        _require_unique([row.evidence_id for row in self.sell_irreducibility], "SELL evidence IDs")
        _require_unique([row.order_id for row in self.sell_irreducibility], "SELL evidence order IDs")
        evidence = {row.evidence_id: row.order_id for row in self.sell_irreducibility}
        sell_orders = {row.order_id: row.irreducibility_evidence_ref for row in self.order_rows if isinstance(row, PlannerSellOrderRow)}
        if set(evidence.values()) != set(sell_orders):
            raise ValueError("SELL orders and irreducibility evidence must be one-to-one")
        if any(evidence.get(evidence_id) != order_id for order_id, evidence_id in sell_orders.items()):
            raise ValueError("SELL orders must reference their own irreducibility evidence")
        return self


def _validate_no_op_common(solution: PacPlanSolution | RebalancerPlanSolution) -> None:
    if any(_money_fraction(getattr(solution.costs, name)) != 0 for name in type(solution.costs).model_fields):
        raise ValueError("No-op solutions cannot publish costs")
    accounting = solution.accounting
    if any(_money_fraction(value) != 0 for value in (accounting.physical_reserves, accounting.economic_losses, accounting.rounding_delta)):
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
        if any(_fixed_fraction(getattr(row, name)) != 0 for name in flow_fields) or _exact_fraction(row.rounding_delta) != 0:
            raise ValueError("No-op ledger rows cannot contain action-derived postings")
        if _fixed_fraction(row.final_spendable) != _fixed_fraction(row.initial_selected) or _fixed_fraction(row.final_physical) != _fixed_fraction(row.initial_selected):
            raise ValueError("No-op ledger balances must preserve selected initial cash")


def _validate_pac_no_op(solution: PacPlanSolution) -> None:
    if _money_fraction(solution.accounting.final_invested) != 0:
        raise ValueError("No-op PAC final invested value must be zero")
    if any(_money_fraction(row.buy_mid_value) != 0 or _money_fraction(row.final_value) != 0 for row in solution.asset_rows):
        raise ValueError("No-op PAC Asset projections cannot contain BUY value")


def _validate_rebalancer_no_op(solution: RebalancerPlanSolution) -> None:
    if _money_fraction(solution.accounting.final_invested) != _money_fraction(solution.accounting.current_invested):
        raise ValueError("No-op Rebalancer final invested value must equal its current value")
    if any(_money_fraction(row.buy_mid_value) != 0 or _money_fraction(row.sell_mid_value) != 0 or _money_fraction(row.final_value) != _money_fraction(row.before_value) for row in solution.asset_rows):
        raise ValueError("No-op Rebalancer Asset projections must preserve the current portfolio")


class PacNoOpSolution(PacPlanSolution):
    funding_actions: Annotated[list[PlannerFundingAction], Field(max_length=0)]
    fx_actions: Annotated[list[PlannerFxAction], Field(max_length=0)]
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
    fx_actions: Annotated[list[PlannerFxAction], Field(max_length=0)]
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
        if self.unit.kind != _objective_unit_kind(self.objective_code):
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
        if _exact_fraction(delta.delta) != _exact_fraction(delta.deployment_value) - _exact_fraction(delta.primary_value):
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
    if any(_money_fraction(money) < 0 for money in nonnegative):
        raise ValueError("Nonnegative accounting totals cannot be negative")
    if _money_fraction(accounting.free_cash) + top_up_value < 0:
        raise ValueError("Free cash cannot be negative beyond the rounding top-ups")
    if _money_fraction(accounting.selected_funding) != _money_fraction(accounting.reachable_funding) + _money_fraction(accounting.trapped_funding):
        raise ValueError("Selected funding must equal reachable plus trapped funding")
    if _money_fraction(accounting.fixed_reference) != _money_fraction(accounting.current_invested) + _money_fraction(accounting.reachable_funding):
        raise ValueError("Fixed reference must equal current invested plus reachable funding")
    if abs(_money_fraction(accounting.rounding_delta)) > _money_fraction(accounting.rounding_bound):
        raise ValueError("Rounding delta must remain inside its exact bound")
    if _money_fraction(accounting.shortfall) + top_up_value < -_money_fraction(accounting.rounding_bound):
        raise ValueError("Shortfall cannot exceed the favorable rounding bound")
    decomposition = _money_fraction(accounting.free_cash) + _money_fraction(accounting.physical_reserves) + _money_fraction(accounting.economic_losses) + _money_fraction(accounting.rounding_delta)
    if _money_fraction(accounting.shortfall) != decomposition:
        raise ValueError("Shortfall must equal free cash, physical reserves, economic losses, and rounding")
    if _money_fraction(accounting.identity_delta) != 0:
        raise ValueError("Published accounting identity delta must be zero")


def _validate_asset_row(row: PacAssetPlanRow | RebalancerAssetPlanRow) -> None:
    nonnegative_values = [row.target_value, row.final_value, row.buy_mid_value]
    if isinstance(row, RebalancerAssetPlanRow):
        nonnegative_values.extend([row.before_value, row.sell_mid_value])
    if any(_money_fraction(value) < 0 for value in nonnegative_values):
        raise ValueError("Asset before, target, final, BUY, and SELL values cannot be negative")
    if _money_fraction(row.residual) != _money_fraction(row.final_value) - _money_fraction(row.target_value):
        raise ValueError("Asset residual must equal final minus target value")
    if isinstance(row, RebalancerAssetPlanRow):
        expected_final = _money_fraction(row.before_value) + _money_fraction(row.buy_mid_value) - _money_fraction(row.sell_mid_value)
    else:
        expected_final = _money_fraction(row.buy_mid_value)
    if _money_fraction(row.final_value) != expected_final:
        raise ValueError("Asset final value must reconcile before, BUY, and SELL values")


def _validate_target_weight_identities(
    rows: list[PacAssetPlanRow] | list[RebalancerAssetPlanRow],
    fixed_reference: Fraction,
) -> None:
    weights = [_exact_fraction(row.target_weight) for row in rows]
    if any(weight < 0 or weight > 1 for weight in weights) or sum(weights, Fraction()) != 1:
        raise ValueError("Asset target weights must form a complete unit vector")
    if any(weight * fixed_reference != _money_fraction(row.target_value) for row, weight in zip(rows, weights, strict=True)):
        raise ValueError("Each Asset target weight must match its fixed-reference target value")


def _validate_available_weight_identities(
    weights: list[ExactNumberAvailability],
    values: list[ExactMoney],
    total: Fraction,
    zero_reason: str,
    label: str,
) -> None:
    _validate_weight_availability(weights, total, zero_reason, label)
    if total == 0:
        return
    for weight, value in zip(weights, values, strict=True):
        available = _available_fraction(weight)
        if available is None or available * total != _money_fraction(value):
            raise ValueError(f"Each available Asset {label.lower()} weight must match its value")


def _validate_asset_projection(solution: PacPlanSolution | RebalancerPlanSolution) -> None:
    accounting = solution.accounting
    fixed_reference = _money_fraction(accounting.fixed_reference)
    current_invested = _money_fraction(accounting.current_invested)
    final_invested = _money_fraction(accounting.final_invested)
    if sum((_money_fraction(row.target_value) for row in solution.asset_rows), Fraction()) != fixed_reference:
        raise ValueError("Asset target values must sum to the fixed reference")
    if sum((_money_fraction(row.final_value) for row in solution.asset_rows), Fraction()) != final_invested:
        raise ValueError("Asset final values must sum to final invested value")
    for row in solution.asset_rows:
        _validate_asset_row(row)
    if isinstance(solution, RebalancerPlanSolution):
        if sum((_money_fraction(row.before_value) for row in solution.asset_rows), Fraction()) != current_invested:
            raise ValueError("Rebalancer before values must sum to current invested value")
    elif current_invested != 0:
        raise ValueError("PAC current invested value must be zero")
    if sum((_money_fraction(row.residual) for row in solution.asset_rows), Fraction()) != -_money_fraction(accounting.shortfall):
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
        if sum((_exact_fraction(row.target_weight) for row in rows), Fraction()) != 1:
            raise ValueError(f"{dimension} exposure targets must form a complete unit vector")
        _validate_weight_availability(
            [row.final_weight for row in rows],
            _money_fraction(solution.accounting.final_invested),
            "zero_final_invested",
            f"{dimension} final exposure",
        )
        if isinstance(solution, RebalancerPlanSolution):
            _validate_weight_availability(
                [row.before_weight for row in rows],
                _money_fraction(solution.accounting.current_invested),
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
    if any(row.currency == valuation_currency and _money_fraction(row.valuation_amount) != _fixed_fraction(row.amount) for row in top_ups):
        raise ValueError("A PAC rounding top-up in the valuation currency must be valued at its own amount")
    if any(_exact_fraction(getattr(solution.costs, name).value) < 0 for name in type(solution.costs).model_fields):
        raise ValueError("Cost totals cannot be negative")
    _validate_accounting_summary(solution.accounting, top_up_value=sum((_money_fraction(row.valuation_amount) for row in top_ups), Fraction()))
    if isinstance(solution, RebalancerPlanSolution) and _money_fraction(solution.accounting.final_invested) <= 0:
        raise ValueError("Ready Rebalancer solutions require positive final invested value")
    _validate_asset_projection(solution)
    _validate_exposure_projection(solution)
    if any(stage.unit.kind in {"valuation_money", "valuation_money_squared"} and stage.unit.currency_code != valuation_currency for stage in solution.objectives.stages):
        raise ValueError("Valuation objective units must use the scenario valuation currency")
    if any(stage.objective_code == "shortfall" and _exact_fraction(stage.value) != _money_fraction(solution.accounting.shortfall) for stage in solution.objectives.stages):
        raise ValueError("The shortfall objective must equal the authoritative accounting shortfall")


def _validate_pac_top_up_minor_units(
    catalogs: PlannerCatalogs,
    solution: PacPlanSolution | RebalancerPlanSolution,
) -> None:
    """``amount <= rounded_postings x minor unit``: the one top-up bound that needs the catalogue."""
    if not isinstance(solution, PacPlanSolution):
        return
    minor_units = {row.currency: _fixed_fraction(row.minor_unit) for row in catalogs.currencies}
    if any(_fixed_fraction(row.amount) > row.rounded_postings * minor_units[row.currency] for row in solution.rounding_top_ups):
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
    if not _collect_currency_codes(solution.model_dump(mode="python")) <= currencies:
        raise ValueError("Solution rows must reference catalog currencies")
    _validate_pac_top_up_minor_units(catalogs, solution)
    referenced_provenance = {provenance_id for row in [*solution.funding_actions, *solution.fx_actions, *solution.conversions, *solution.order_rows, *solution.exposure_rows] for provenance_id in row.provenance_ids}
    if not referenced_provenance <= provenance_ids:
        raise ValueError("Solution rows must reference top-level provenance IDs")
    for row in [*solution.funding_actions, *solution.fx_actions, *solution.conversions, *solution.order_rows, *solution.exposure_rows]:
        _require_unique(row.provenance_ids, "Result-row provenance IDs")
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
    if any(_exact_fraction(money.value) < 0 for money in basis_money):
        raise ValueError(f"{product} scenario totals cannot be negative")
    if product == "PAC" and _money_fraction(scenario_basis.current_invested) != 0:
        raise ValueError("PAC scenario current invested value must be zero")
    if product == "Rebalancer" and _money_fraction(scenario_basis.current_invested) <= 0:
        raise ValueError("Ready Rebalancer scenarios require positive current invested value")
    if _exact_fraction(scenario_basis.selected_funding.value) != _exact_fraction(scenario_basis.reachable_funding.value) + _exact_fraction(scenario_basis.trapped_funding.value):
        raise ValueError(f"{product} selected funding must equal reachable plus trapped funding")
    if _exact_fraction(scenario_basis.fixed_reference.value) != _exact_fraction(scenario_basis.current_invested.value) + _exact_fraction(scenario_basis.reachable_funding.value):
        raise ValueError(f"{product} fixed reference must equal current invested plus reachable funding")


def _validate_result_catalogs(
    product: str,
    catalogs: PlannerCatalogs,
    provenance: list[PlannerProvenance],
    scenario_basis: PlannerScenarioBasis,
) -> None:
    _require_unique([row.provenance_id for row in provenance], f"{product} provenance IDs")
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
