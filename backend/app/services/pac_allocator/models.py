"""Immutable numeric state shared by allocation normalization and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Callable, Literal

from backend.app.schemas.pac_allocator import AllocationIssue, FactReason, GridMode
from backend.app.services.pac_allocator.numeric import ExactRatio

Checkpoint = Callable[[], None]


@dataclass(frozen=True, slots=True)
class ParsedValue[T]:
    value: T | None
    reason: FactReason | None = None

    @property
    def available(self) -> bool:
        return self.reason is None and self.value is not None

    def require(self) -> T:
        if not self.available or self.value is None:
            raise RuntimeError("Required normalized value is unavailable")
        return self.value


@dataclass(frozen=True, slots=True)
class ParsedGrid:
    mode: GridMode | None
    step: ParsedValue[Decimal]


@dataclass(frozen=True, slots=True)
class ParsedAsset:
    instrument_key: str
    name: str | None
    grid: ParsedGrid | None


@dataclass(frozen=True, slots=True)
class ParsedQuote:
    price: ParsedValue[Decimal]
    currency: ParsedValue[str]
    basis: ParsedValue[int]
    reference_date: date | None
    date_valid: bool


@dataclass(frozen=True, slots=True)
class ParsedHolding:
    row_key: str
    instrument_key: str
    name: str | None
    quantity: ParsedValue[Decimal]
    quote: ParsedQuote
    grid: ParsedGrid | None


@dataclass(frozen=True, slots=True)
class ParsedTarget:
    instrument_key: str
    percent: ParsedValue[Decimal]


@dataclass(frozen=True, slots=True)
class ParsedMoneyVector:
    entries: tuple[tuple[str, Decimal], ...]
    reason: FactReason | None

    def amount_entries(self) -> tuple[tuple[str, Decimal], ...]:
        return self.entries

    def amounts(self) -> dict[str, Decimal]:
        return dict(self.entries)


@dataclass(frozen=True, slots=True)
class ParsedContributionVector:
    entries: tuple[tuple[str, Decimal, Decimal], ...]
    reason: FactReason | None

    def amount_entries(self) -> tuple[tuple[str, Decimal], ...]:
        return tuple((currency, amount) for currency, amount, _monetary_step in self.entries)

    def amounts(self) -> dict[str, Decimal]:
        totals: dict[str, Decimal] = {}
        for currency, amount in self.amount_entries():
            totals[currency] = totals.get(currency, Decimal(0)) + amount
        return totals


@dataclass(frozen=True, slots=True)
class ParsedRate:
    currency: str
    rate: ParsedValue[Decimal]
    reference_date: date | None


@dataclass(frozen=True, slots=True)
class PacAsset:
    instrument_key: str
    name: str
    grid_mode: GridMode | None
    quantity_step: Decimal | None


@dataclass(frozen=True, slots=True)
class Holding:
    row_key: str
    instrument_key: str
    name: str
    quantity: Decimal
    raw_price: Decimal
    currency: str
    quote_base_quantity: int
    reference_date: date | None
    grid_mode: GridMode | None
    quantity_step: Decimal | None


@dataclass(frozen=True, slots=True)
class Target:
    instrument_key: str
    percent: Decimal


@dataclass(frozen=True, slots=True)
class PacScenario:
    report_currency: str
    as_of_date: date | None
    assets: tuple[PacAsset, ...]
    targets: tuple[Target, ...]
    cash_balances: tuple[tuple[str, Decimal], ...]
    contributions: tuple[tuple[str, Decimal, Decimal], ...]
    valuation_rates: tuple[ParsedRate, ...]


@dataclass(frozen=True, slots=True)
class RebalanceScenario:
    report_currency: str
    as_of_date: date | None
    holdings: tuple[Holding, ...]
    targets: tuple[Target, ...]
    cash_balances: tuple[tuple[str, Decimal], ...]
    contributions: tuple[tuple[str, Decimal, Decimal], ...]
    valuation_rates: tuple[ParsedRate, ...]


@dataclass(frozen=True, slots=True)
class PacNormalizationResult:
    report_currency: ParsedValue[str]
    as_of_date: date | None
    assets: tuple[ParsedAsset, ...]
    targets: tuple[ParsedTarget, ...]
    cash: ParsedMoneyVector
    contributions: ParsedContributionVector
    rates: tuple[ParsedRate, ...]
    currencies: tuple[str, ...]
    currency_domain_valid: bool
    asset_identity_valid: bool
    target_identity_valid: bool
    target_total: ParsedValue[Decimal]
    targets_valid: bool
    issues: tuple[AllocationIssue, ...]
    normalized: PacScenario | None

    def rate_map(self) -> dict[str, ParsedValue[Decimal]]:
        return {item.currency: item.rate for item in self.rates}

    def target_map(self) -> dict[str, ParsedValue[Decimal]]:
        return {item.instrument_key: item.percent for item in self.targets}


@dataclass(frozen=True, slots=True)
class RebalanceNormalizationResult:
    report_currency: ParsedValue[str]
    as_of_date: date | None
    holdings: tuple[ParsedHolding, ...]
    targets: tuple[ParsedTarget, ...]
    cash: ParsedMoneyVector
    contributions: ParsedContributionVector
    rates: tuple[ParsedRate, ...]
    currencies: tuple[str, ...]
    currency_domain_valid: bool
    row_identity_valid: bool
    target_identity_valid: bool
    target_total: ParsedValue[Decimal]
    targets_valid: bool
    issues: tuple[AllocationIssue, ...]
    normalized: RebalanceScenario | None

    def rate_map(self) -> dict[str, ParsedValue[Decimal]]:
        return {item.currency: item.rate for item in self.rates}

    def target_map(self) -> dict[str, ParsedValue[Decimal]]:
        return {item.instrument_key: item.percent for item in self.targets}


type NormalizationResult = PacNormalizationResult | RebalanceNormalizationResult


@dataclass(frozen=True, slots=True)
class MoneyEvaluation:
    existing_cash: ParsedValue[Decimal]
    contributions: ParsedValue[Decimal]
    combined_cash: ParsedValue[Decimal]


@dataclass(frozen=True, slots=True)
class PacEvaluation:
    money: MoneyEvaluation
    allocations: tuple[ParsedValue[Decimal], ...]


@dataclass(frozen=True, slots=True)
class HoldingEvaluation:
    native_value: ParsedValue[Decimal]
    reporting_value: ParsedValue[Decimal]


@dataclass(frozen=True, slots=True)
class InstrumentEvaluation:
    instrument_key: str
    current_reporting: ParsedValue[Decimal]
    target_value_reporting: ParsedValue[Decimal]
    value_gap_reporting: ParsedValue[Decimal]
    gap_numerator: Decimal | None


@dataclass(frozen=True, slots=True)
class RebalanceEvaluation:
    holdings: tuple[HoldingEvaluation, ...]
    instruments: tuple[InstrumentEvaluation, ...]
    invested: ParsedValue[Decimal]
    money: MoneyEvaluation
    max_gap_numerator: Decimal | None
    squared_gap_numerator: Decimal | None


def check_budget(checkpoint: Checkpoint | None) -> None:
    if checkpoint is not None:
        checkpoint()


def unavailable_reason(values: list[ParsedValue] | tuple[ParsedValue, ...]) -> FactReason | None:
    reasons = {item.reason for item in values if not item.available}
    for reason in ("input_invalid", "outside_p1_domain", "input_missing", "dependency_unavailable"):
        if reason in reasons:
            return reason
    return "dependency_unavailable" if reasons else None


# Planner v2 exact domain ----------------------------------------------------
#
# These data-only records deliberately do not depend on a solver.  The public
# request is normalized into these records once; the evaluator, exhaustive
# oracle, and future solver adapter consume the same exact state.

type PlannerProduct = Literal["pac", "rebalancer"]
type RebalancerPolicy = Literal["invest_only", "invest_and_sell"]
type PlannerPolicy = Literal["proportional", "min_fragmentation", "invest_only", "invest_and_sell"]
type IdentityKind = Literal["domain", "manual"]
type FreshnessKind = Literal["fresh", "stale"]
type ProvenanceKind = Literal["manual", "domain_copy"]
type CapabilityKind = Literal["whole_quantity", "monetary_amount"]
type OrderSide = Literal["buy", "sell"]
type FxMode = Literal["native_currency_required", "conversion_allowed"]
type OrderMinimumKind = Literal["none", "whole_quantity", "monetary_amount"]
type OrderCapKind = Literal["quantity", "notional"]
type ConstraintPhase = Literal["normalization", "exact", "solver", "publication"]
type ConstraintEnforcement = Literal["normalizer", "exact_only", "solver_and_exact", "publication_gate"]
type ObjectiveSense = Literal["min"]
type DecisionFamily = Literal["funding_transfer", "fx_debit", "buy_quantum", "sell_quantum"]
type DecisionMode = Literal["disabled", "mutable", "frozen_exact", "additive_only"]
type ExactUnitKind = Literal["boolean", "count", "ratio", "asset_quantity", "native_money", "valuation_money", "valuation_money_squared", "ordinal_penalty", "canonical_key"]


def _require_text(value: str, field: str) -> None:
    if not value:
        raise ValueError(f"{field} must not be empty")


def _require_currency(value: str, field: str = "currency") -> None:
    if len(value) != 3 or value != value.upper() or not value.isalpha():
        raise ValueError(f"{field} must be an uppercase ISO-like three-letter code")


def _require_canonical_tuple[T](values: tuple[T, ...], key: Callable[[T], object], field: str) -> None:
    keys = tuple(key(value) for value in values)
    if keys != tuple(sorted(keys)):
        raise ValueError(f"{field} must use canonical sorted order")
    if len(keys) != len(set(keys)):
        raise ValueError(f"{field} must not contain duplicate keys")


def _require_unique_values(values: tuple[object, ...], field: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{field} must not contain duplicate values")


def _require_nonnegative(value: ExactRatio, field: str) -> None:
    if value < ExactRatio(0):
        raise ValueError(f"{field} must be nonnegative")


def _require_positive(value: ExactRatio, field: str) -> None:
    if value <= ExactRatio(0):
        raise ValueError(f"{field} must be positive")


def _require_unit_interval(value: ExactRatio, field: str) -> None:
    if not ExactRatio(0) <= value <= ExactRatio(1):
        raise ValueError(f"{field} must lie in the closed unit interval")


@dataclass(frozen=True, slots=True)
class ExactMoney:
    amount: ExactRatio
    currency: str

    def __post_init__(self) -> None:
        _require_currency(self.currency)


@dataclass(frozen=True, slots=True)
class ExactFreshness:
    kind: FreshnessKind
    age_days: int | None
    accepted: bool

    def __post_init__(self) -> None:
        if self.kind == "fresh":
            if self.age_days is not None or self.accepted:
                raise ValueError("fresh observations cannot carry stale acceptance")
            return
        if self.age_days is None or self.age_days < 0 or not self.accepted:
            raise ValueError("stale observations require nonnegative age and explicit acceptance")


@dataclass(frozen=True, slots=True)
class ExactSnapshot:
    snapshot_id: str
    draft_revision: int
    captured_at: datetime

    def __post_init__(self) -> None:
        _require_text(self.snapshot_id, "snapshot_id")
        if self.draft_revision < 0:
            raise ValueError("draft_revision must be nonnegative")
        if self.captured_at.tzinfo is None or self.captured_at.utcoffset() is None:
            raise ValueError("captured_at must include a timezone")


@dataclass(frozen=True, slots=True)
class ExactCurrencySpec:
    currency: str
    minor_unit: ExactRatio

    def __post_init__(self) -> None:
        _require_currency(self.currency)
        if self.minor_unit <= ExactRatio(0):
            raise ValueError("minor_unit must be positive")


@dataclass(frozen=True, slots=True)
class ExactProvenance:
    provenance_id: str
    kind: ProvenanceKind
    label: str | None
    entered_at: datetime | None
    domain: str | None
    source_ref: str | None
    source_label: str | None
    captured_at: datetime | None

    def __post_init__(self) -> None:
        _require_text(self.provenance_id, "provenance_id")


@dataclass(frozen=True, slots=True)
class ExactValuationRate:
    rate_id: str
    source_currency: str
    destination_currency: str
    rate: ExactRatio
    reference_date: date
    freshness: ExactFreshness
    provenance_id: str

    def __post_init__(self) -> None:
        _require_currency(self.source_currency, "source_currency")
        _require_currency(self.destination_currency, "destination_currency")
        if self.source_currency == self.destination_currency:
            raise ValueError("valuation rates must be nonidentity")
        _require_positive(self.rate, "valuation rate")


@dataclass(frozen=True, slots=True)
class ExactExposure:
    dimension: Literal["asset_type", "sector", "geography"]
    category: str
    label: str
    weight: ExactRatio
    provenance_id: str

    def __post_init__(self) -> None:
        _require_unit_interval(self.weight, "exposure weight")


@dataclass(frozen=True, slots=True)
class ExactAssetQuote:
    price: ExactMoney
    quote_base_quantity: ExactRatio
    reference_date: date
    freshness: ExactFreshness
    provenance_id: str

    def __post_init__(self) -> None:
        _require_positive(self.price.amount, "asset price")
        _require_positive(self.quote_base_quantity, "quote_base_quantity")


@dataclass(frozen=True, slots=True)
class ExactAsset:
    asset_id: str
    identity_kind: IdentityKind
    source_asset_id: str | None
    name: str
    ticker: str | None
    asset_class: str
    quote: ExactAssetQuote
    exposures: tuple[ExactExposure, ...]

    def __post_init__(self) -> None:
        if (self.identity_kind == "domain") != (self.source_asset_id is not None):
            raise ValueError("domain Asset identity requires source_asset_id and manual identity forbids it")
        _require_canonical_tuple(self.exposures, lambda exposure: (exposure.dimension, exposure.category), "asset exposures")


@dataclass(frozen=True, slots=True)
class ExactOrderCapability:
    capability_id: str
    kind: CapabilityKind
    currency: str
    fx_mode: FxMode
    order_step: ExactRatio

    def __post_init__(self) -> None:
        _require_currency(self.currency)
        _require_positive(self.order_step, "order_step")


@dataclass(frozen=True, slots=True)
class ExactFeeSchedule:
    fee_schedule_id: str
    capability_id: str
    side: OrderSide
    fixed_fee: ExactMoney
    proportional_rate: ExactRatio
    minimum_fee: ExactMoney
    maximum_fee: ExactMoney | None

    def __post_init__(self) -> None:
        _require_nonnegative(self.fixed_fee.amount, "fixed_fee")
        _require_unit_interval(self.proportional_rate, "proportional_rate")
        _require_nonnegative(self.minimum_fee.amount, "minimum_fee")
        currencies = {self.fixed_fee.currency, self.minimum_fee.currency}
        if self.maximum_fee is not None:
            _require_nonnegative(self.maximum_fee.amount, "maximum_fee")
            if self.minimum_fee.amount > self.maximum_fee.amount:
                raise ValueError("minimum_fee cannot exceed maximum_fee")
            currencies.add(self.maximum_fee.currency)
        if len(currencies) != 1:
            raise ValueError("fee amounts must use one currency")


@dataclass(frozen=True, slots=True)
class ExactBroker:
    broker_id: str
    identity_kind: IdentityKind
    source_broker_id: str | None
    name: str
    active: bool | None
    provenance_id: str
    capabilities: tuple[ExactOrderCapability, ...]
    fee_schedules: tuple[ExactFeeSchedule, ...]

    def __post_init__(self) -> None:
        if (self.identity_kind == "domain") != (self.source_broker_id is not None):
            raise ValueError("domain Broker identity requires source_broker_id and manual identity forbids it")
        _require_canonical_tuple(self.capabilities, lambda capability: capability.capability_id, "broker capabilities")
        _require_canonical_tuple(self.fee_schedules, lambda schedule: (schedule.capability_id, schedule.side, schedule.fee_schedule_id), "broker fee schedules")


@dataclass(frozen=True, slots=True)
class ExactHolding:
    holding_id: str
    asset_id: str
    broker_id: str
    custody_quantity: ExactRatio
    economic_share: ExactRatio
    economic_quantity: ExactRatio
    planning_quantity: ExactRatio
    provenance_id: str

    def __post_init__(self) -> None:
        _require_nonnegative(self.custody_quantity, "custody_quantity")
        _require_unit_interval(self.economic_share, "economic_share")
        if self.economic_quantity != self.custody_quantity * self.economic_share:
            raise ValueError("economic_quantity must equal custody_quantity times economic_share")
        _require_nonnegative(self.planning_quantity, "planning_quantity")


@dataclass(frozen=True, slots=True)
class ExactExistingCash:
    source_kind: Literal["local_broker_cash", "manual_cash"]
    cash_id: str
    broker_id: str
    available: ExactMoney
    selected: ExactMoney
    provenance_id: str

    def __post_init__(self) -> None:
        if self.available.currency != self.selected.currency:
            raise ValueError("available and selected cash currencies must match")
        _require_nonnegative(self.available.amount, "available cash")
        _require_nonnegative(self.selected.amount, "selected cash")
        if self.selected.amount > self.available.amount:
            raise ValueError("selected cash cannot exceed available cash")


@dataclass(frozen=True, slots=True)
class ExactContribution:
    contribution_id: str
    label: str
    amount: ExactMoney
    provenance_id: str

    def __post_init__(self) -> None:
        _require_nonnegative(self.amount.amount, "contribution")


@dataclass(frozen=True, slots=True)
class ExactFundingRoute:
    route_id: str
    broker_id: str
    source_kind: Literal["existing_cash", "contribution"]
    source_id: str
    currency: str
    transfer_cap: ExactMoney
    priority: int
    provenance_id: str

    def __post_init__(self) -> None:
        _require_currency(self.currency)
        if self.transfer_cap.currency != self.currency:
            raise ValueError("transfer cap currency must match funding route")
        _require_nonnegative(self.transfer_cap.amount, "transfer_cap")
        if self.priority < 0:
            raise ValueError("funding route priority must be nonnegative")


@dataclass(frozen=True, slots=True)
class ExactOrderMinimum:
    kind: OrderMinimumKind
    value: ExactRatio
    currency: str | None

    def __post_init__(self) -> None:
        _require_nonnegative(self.value, "order minimum")
        if self.kind == "none":
            if self.value != ExactRatio(0) or self.currency is not None:
                raise ValueError("none order minimum must be zero and currencyless")
        elif self.kind == "whole_quantity":
            if self.currency is not None:
                raise ValueError("whole-quantity minimum cannot carry currency")
        elif self.currency is None:
            raise ValueError("monetary minimum requires currency")
        else:
            _require_currency(self.currency)


@dataclass(frozen=True, slots=True)
class ExactOrderCap:
    kind: OrderCapKind
    value: ExactRatio
    currency: str | None

    def __post_init__(self) -> None:
        _require_positive(self.value, "order cap")
        if self.kind == "quantity":
            if self.currency is not None:
                raise ValueError("quantity cap cannot carry currency")
        elif self.currency is None:
            raise ValueError("notional cap requires currency")
        else:
            _require_currency(self.currency)


@dataclass(frozen=True, slots=True)
class ExactOrderRoute:
    route_id: str
    broker_id: str
    asset_id: str
    capability_id: str
    fee_schedule_id: str
    side: OrderSide
    minimum_if_active: ExactOrderMinimum
    required_minimum: ExactOrderMinimum
    cap: ExactOrderCap
    execution_margin_rate: ExactRatio
    priority: int
    gross_amount_requested: ExactMoney | None
    provenance_id: str

    def __post_init__(self) -> None:
        if not ExactRatio(0) <= self.execution_margin_rate < ExactRatio(1):
            raise ValueError("execution margin must lie in the half-open unit interval")
        if self.priority < 0:
            raise ValueError("order route priority must be nonnegative")
        if self.gross_amount_requested is not None:
            _require_nonnegative(self.gross_amount_requested.amount, "gross_amount_requested")


@dataclass(frozen=True, slots=True)
class ExactFxQuote:
    quote_id: str
    source_currency: str
    destination_currency: str
    rate: ExactRatio
    reference_date: date
    freshness: ExactFreshness
    provenance_id: str

    def __post_init__(self) -> None:
        _require_currency(self.source_currency, "source_currency")
        _require_currency(self.destination_currency, "destination_currency")
        if self.source_currency == self.destination_currency:
            raise ValueError("FX quotes must be nonidentity")
        _require_positive(self.rate, "FX rate")


@dataclass(frozen=True, slots=True)
class ExactFxRoute:
    route_id: str
    broker_id: str
    quote_id: str
    source_currency: str
    destination_currency: str
    source_amount_step: ExactMoney
    fixed_fee: ExactMoney
    spread_rate: ExactRatio
    buffer_rate: ExactRatio
    priority: int
    provenance_id: str

    def __post_init__(self) -> None:
        _require_currency(self.source_currency, "source_currency")
        _require_currency(self.destination_currency, "destination_currency")
        if self.source_currency == self.destination_currency:
            raise ValueError("FX routes must be nonidentity")
        if self.source_amount_step.currency != self.source_currency or self.fixed_fee.currency != self.source_currency:
            raise ValueError("FX debit step and fee must use source currency")
        _require_positive(self.source_amount_step.amount, "source_amount_step")
        _require_nonnegative(self.fixed_fee.amount, "FX fixed fee")
        if not ExactRatio(0) <= self.spread_rate < ExactRatio(1):
            raise ValueError("FX spread must lie in the half-open unit interval")
        if not ExactRatio(0) <= self.buffer_rate < ExactRatio(1):
            raise ValueError("FX buffer must lie in the half-open unit interval")
        if self.priority < 0:
            raise ValueError("FX route priority must be nonnegative")


@dataclass(frozen=True, slots=True)
class ExactTargetWeight:
    asset_id: str
    weight: ExactRatio

    def __post_init__(self) -> None:
        _require_unit_interval(self.weight, "target weight")


@dataclass(frozen=True, slots=True)
class ExactCostBasis:
    holding_id: str
    average_unit_cost: ExactMoney
    reference_date: date
    provenance_id: str

    def __post_init__(self) -> None:
        _require_nonnegative(self.average_unit_cost.amount, "average_unit_cost")


@dataclass(frozen=True, slots=True)
class ExactAssetTax:
    asset_id: str
    fiscal_currency: str
    gain_tax_rate: ExactRatio
    provenance_id: str

    def __post_init__(self) -> None:
        _require_currency(self.fiscal_currency, "fiscal_currency")
        _require_unit_interval(self.gain_tax_rate, "gain_tax_rate")


@dataclass(frozen=True, slots=True)
class ExactWithholding:
    broker_id: str
    fiscal_currency: str
    carried_loss_available: ExactMoney
    withholding_kind: Literal["broker_withheld", "self_reserved"]
    reference_date: date
    provenance_id: str

    def __post_init__(self) -> None:
        _require_currency(self.fiscal_currency, "fiscal_currency")
        if self.carried_loss_available.currency != self.fiscal_currency:
            raise ValueError("carried loss currency must match fiscal currency")
        _require_nonnegative(self.carried_loss_available.amount, "carried_loss_available")


@dataclass(frozen=True, slots=True)
class ExactSellContext:
    cost_basis: tuple[ExactCostBasis, ...]
    asset_tax: tuple[ExactAssetTax, ...]
    withholding: tuple[ExactWithholding, ...]

    def __post_init__(self) -> None:
        _require_canonical_tuple(self.cost_basis, lambda item: item.holding_id, "cost basis")
        _require_canonical_tuple(self.asset_tax, lambda item: item.asset_id, "asset tax")
        _require_canonical_tuple(self.withholding, lambda item: item.broker_id, "withholding")


@dataclass(frozen=True, slots=True)
class ExactPlannerScenario:
    snapshot: ExactSnapshot
    product: PlannerProduct
    policy: PlannerPolicy
    as_of_date: date
    valuation_currency: str
    currency_specs: tuple[ExactCurrencySpec, ...]
    provenance: tuple[ExactProvenance, ...]
    valuation_rates: tuple[ExactValuationRate, ...]
    assets: tuple[ExactAsset, ...]
    brokers: tuple[ExactBroker, ...]
    holdings: tuple[ExactHolding, ...]
    existing_cash: tuple[ExactExistingCash, ...]
    contributions: tuple[ExactContribution, ...]
    funding_routes: tuple[ExactFundingRoute, ...]
    order_routes: tuple[ExactOrderRoute, ...]
    fx_quotes: tuple[ExactFxQuote, ...]
    fx_routes: tuple[ExactFxRoute, ...]
    target_weights: tuple[ExactTargetWeight, ...]
    sell_context: ExactSellContext | None

    def __post_init__(self) -> None:
        if (self.product == "pac") != (self.policy in {"proportional", "min_fragmentation"}):
            raise ValueError("PAC product requires a PAC policy and vice versa")
        if self.product == "pac" and (self.holdings or self.sell_context is not None):
            raise ValueError("PAC scenarios cannot contain holdings or SELL context")
        if self.policy == "invest_only" and self.sell_context is not None:
            raise ValueError("invest-only scenarios cannot contain SELL context")
        if self.policy == "invest_and_sell" and self.sell_context is None:
            raise ValueError("invest-and-sell scenarios require SELL context")
        _require_currency(self.valuation_currency, "valuation_currency")
        _require_canonical_tuple(self.currency_specs, lambda item: item.currency, "currency_specs")
        _require_canonical_tuple(self.provenance, lambda item: item.provenance_id, "provenance")
        _require_canonical_tuple(self.valuation_rates, lambda item: item.rate_id, "valuation_rates")
        _require_canonical_tuple(self.assets, lambda item: item.asset_id, "assets")
        _require_canonical_tuple(self.brokers, lambda item: item.broker_id, "brokers")
        _require_canonical_tuple(self.holdings, lambda item: item.holding_id, "holdings")
        _require_unique_values(tuple(item.source_asset_id for item in self.assets if item.identity_kind == "domain"), "domain asset source identities")
        _require_unique_values(tuple(item.source_broker_id for item in self.brokers if item.identity_kind == "domain"), "domain broker source identities")
        _require_unique_values(tuple((item.asset_id, item.broker_id) for item in self.holdings), "holding Asset×Broker identities")
        _require_canonical_tuple(self.existing_cash, lambda item: item.cash_id, "existing_cash")
        _require_canonical_tuple(self.contributions, lambda item: item.contribution_id, "contributions")
        _require_canonical_tuple(self.funding_routes, lambda item: item.route_id, "funding_routes")
        _require_canonical_tuple(self.order_routes, lambda item: item.route_id, "order_routes")
        _require_canonical_tuple(self.fx_quotes, lambda item: item.quote_id, "fx_quotes")
        _require_canonical_tuple(self.fx_routes, lambda item: item.route_id, "fx_routes")
        _require_canonical_tuple(self.target_weights, lambda item: item.asset_id, "target_weights")
        if self.valuation_currency not in {item.currency for item in self.currency_specs}:
            raise ValueError("valuation currency requires a currency spec")
        if sum((item.weight for item in self.target_weights), ExactRatio(0)) != ExactRatio(1):
            raise ValueError("target weights must total exactly one")
        if not {item.asset_id for item in self.target_weights}.issubset({item.asset_id for item in self.assets}):
            raise ValueError("target weights must reference normalized assets")


# Solver-neutral policy/evaluation boundary ---------------------------------


@dataclass(frozen=True, slots=True)
class ExactUnit:
    kind: ExactUnitKind
    currency_code: str | None = None
    asset_id: str | None = None

    def __post_init__(self) -> None:
        currency_kinds = {"native_money", "valuation_money", "valuation_money_squared"}
        if self.kind in currency_kinds:
            if self.currency_code is None:
                raise ValueError(f"{self.kind} requires currency_code")
            _require_currency(self.currency_code, "currency_code")
        elif self.currency_code is not None:
            raise ValueError(f"{self.kind} cannot carry currency_code")
        if self.kind == "asset_quantity":
            if self.asset_id is None:
                raise ValueError("asset_quantity requires asset_id")
        elif self.asset_id is not None:
            raise ValueError(f"{self.kind} cannot carry asset_id")


@dataclass(frozen=True, slots=True)
class EntityRef:
    kind: str
    entity_id: str

    def __post_init__(self) -> None:
        _require_text(self.kind, "entity kind")
        _require_text(self.entity_id, "entity_id")


@dataclass(frozen=True, slots=True)
class DecisionAccess:
    decision_id: str
    family: DecisionFamily
    mode: DecisionMode
    entity_refs: tuple[EntityRef, ...]
    lower_quanta: int
    upper_quanta: int
    baseline_quanta: int
    frozen_quanta: int | None

    def __post_init__(self) -> None:
        _require_text(self.decision_id, "decision_id")
        if self.lower_quanta < 0 or self.upper_quanta < self.lower_quanta:
            raise ValueError("decision bounds must be finite, ordered, and nonnegative")
        if not self.lower_quanta <= self.baseline_quanta <= self.upper_quanta:
            raise ValueError("baseline_quanta must lie within decision bounds")
        if self.mode == "frozen_exact":
            if self.frozen_quanta is None or not self.lower_quanta <= self.frozen_quanta <= self.upper_quanta:
                raise ValueError("frozen_exact decisions require an in-bounds frozen value")
        elif self.frozen_quanta is not None:
            raise ValueError("only frozen_exact decisions can carry frozen_quanta")
        if self.mode == "additive_only" and self.lower_quanta < self.baseline_quanta:
            raise ValueError("additive_only lower bound cannot precede baseline")


@dataclass(frozen=True, slots=True)
class ConstraintRef:
    ref_id: str
    code: str
    phase: ConstraintPhase
    scope: str
    entity_refs: tuple[EntityRef, ...]
    units: tuple[ExactUnit, ...]
    enforcement: ConstraintEnforcement
    bound_source: str
    public_issue_code: str | None
    explanation_key: str


@dataclass(frozen=True, slots=True)
class ObjectiveRef:
    ref_id: str
    code: str
    ordinal: int
    sense: ObjectiveSense
    unit: ExactUnit
    freeze_rule: str
    report_field: str
    closure_rule: str

    def __post_init__(self) -> None:
        if self.ordinal < 0:
            raise ValueError("objective ordinal must be nonnegative")


@dataclass(frozen=True, slots=True)
class TieBreakRef:
    ref_id: str
    code: str
    ordinal: int
    unit: ExactUnit
    sense: ObjectiveSense = "min"

    def __post_init__(self) -> None:
        if self.ordinal < 0:
            raise ValueError("tie-break ordinal must be nonnegative")


@dataclass(frozen=True, slots=True)
class ProofRequirement:
    requirement_id: str
    code: str
    allowed_sources: tuple[Literal["deterministic_conflict", "exhaustive_oracle"], ...]

    def __post_init__(self) -> None:
        if not self.allowed_sources:
            raise ValueError("proof requirements need at least one exact source")
        if len(self.allowed_sources) != len(set(self.allowed_sources)):
            raise ValueError("proof sources must be unique")


@dataclass(frozen=True, slots=True)
class SellIrreducibilityGateRef:
    gate_id: str
    sell_decision_id: str
    fixed_incremental_buy_decision_ids: tuple[str, ...]
    reopened_decision_ids: tuple[str, ...]
    counterfactuals: tuple[Literal["decrement_one_quantum", "zero_row"], ...] = ("decrement_one_quantum", "zero_row")

    def __post_init__(self) -> None:
        if self.counterfactuals != ("decrement_one_quantum", "zero_row"):
            raise ValueError("SELL irreducibility uses the frozen decrement-then-zero order")


@dataclass(frozen=True, slots=True)
class ExactPolicyView:
    view_id: str
    scenario_fingerprint: str
    product: PlannerProduct
    policy: PlannerPolicy
    phase: ConstraintPhase
    decisions: tuple[DecisionAccess, ...]
    constraints: tuple[ConstraintRef, ...]
    objectives: tuple[ObjectiveRef, ...]
    tie_breaks: tuple[TieBreakRef, ...]
    sell_gates: tuple[SellIrreducibilityGateRef, ...]
    proof_requirements: tuple[ProofRequirement, ...]

    def __post_init__(self) -> None:
        _require_text(self.view_id, "view_id")
        _require_text(self.scenario_fingerprint, "scenario_fingerprint")
        _require_canonical_tuple(self.decisions, lambda item: item.decision_id, "decisions")
        _require_canonical_tuple(self.constraints, lambda item: item.ref_id, "constraints")
        if tuple(item.ordinal for item in self.objectives) != tuple(sorted(item.ordinal for item in self.objectives)):
            raise ValueError("objectives must use ordinal order")
        if tuple(item.ordinal for item in self.tie_breaks) != tuple(sorted(item.ordinal for item in self.tie_breaks)):
            raise ValueError("tie_breaks must use ordinal order")
        _require_canonical_tuple(self.sell_gates, lambda item: item.gate_id, "sell_gates")
        _require_canonical_tuple(self.proof_requirements, lambda item: item.requirement_id, "proof_requirements")


@dataclass(frozen=True, slots=True)
class CandidateDecision:
    decision_id: str
    quanta: int

    def __post_init__(self) -> None:
        if self.quanta < 0:
            raise ValueError("candidate decision quanta must be nonnegative")


@dataclass(frozen=True, slots=True)
class CandidateActionVector:
    view_id: str
    candidate_id: str
    decisions: tuple[CandidateDecision, ...]

    def __post_init__(self) -> None:
        _require_canonical_tuple(self.decisions, lambda item: item.decision_id, "candidate decisions")


@dataclass(frozen=True, slots=True)
class ExactConstraintEvaluation:
    ref_id: str
    satisfied: bool
    value: ExactRatio
    lower_bound: ExactRatio | None
    upper_bound: ExactRatio | None


@dataclass(frozen=True, slots=True)
class ExactObjectiveEvaluation:
    ref_id: str
    value: ExactRatio


@dataclass(frozen=True, slots=True)
class ExactEvaluation:
    view_id: str
    candidate_id: str
    feasible: bool
    constraints: tuple[ExactConstraintEvaluation, ...]
    objectives: tuple[ExactObjectiveEvaluation, ...]
    conflict_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_canonical_tuple(self.constraints, lambda item: item.ref_id, "constraint evaluations")
        _require_canonical_tuple(self.objectives, lambda item: item.ref_id, "objective evaluations")
        if self.conflict_codes != tuple(sorted(set(self.conflict_codes))):
            raise ValueError("conflict_codes must be unique and sorted")
