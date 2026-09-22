"""Immutable numeric state shared by allocation normalization and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Literal

from backend.app.services.pac_allocator.numeric import ExactRatio

Checkpoint = Callable[[], None]














































def check_budget(checkpoint: Checkpoint | None) -> None:
    if checkpoint is not None:
        checkpoint()




# Planner v2 exact domain ----------------------------------------------------
#
# These data-only records deliberately do not depend on a solver.  The public
# request is normalized into these records once; the evaluator, exhaustive
# oracle, and future solver adapter consume the same exact state.

type PlannerProduct = Literal["pac", "rebalancer"]
type PlannerPolicy = Literal["proportional", "min_fragmentation", "invest_only", "invest_and_sell"]
type IdentityKind = Literal["domain", "manual"]
type FreshnessKind = Literal["fresh", "stale"]
type ProvenanceKind = Literal["manual", "domain_copy"]
type CapabilityKind = Literal["whole_quantity", "monetary_amount"]
type OrderSide = Literal["buy", "sell"]
type OrderMinimumKind = Literal["none", "whole_quantity", "monetary_amount"]
type OrderCapKind = Literal["quantity", "notional"]
type ConstraintPhase = Literal["normalization", "exact", "solver", "publication"]
type ConstraintEnforcement = Literal["normalizer", "exact_only", "solver_and_exact", "publication_gate"]
type ObjectiveSense = Literal["min"]
type DecisionFamily = Literal["funding_transfer", "fx_debit", "buy_quantum", "sell_quantum"]
type DecisionMode = Literal["disabled", "mutable", "frozen_exact", "additive_only"]
type ExactPolicyPurpose = Literal["primary", "invest_only_baseline", "sell_extension", "deployment"]
type ExactUnitKind = Literal["boolean", "count", "ratio", "asset_quantity", "native_money", "valuation_money", "valuation_money_squared", "ordinal_penalty", "canonical_key"]
type ExactObjectiveCode = Literal[
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
type ExactConstraintCode = Literal[
    "SELECTED_WITHIN_AVAILABLE",
    "FUNDING_WITHIN_SELECTED",
    "FUNDING_SOURCE_CONSERVATION",
    "NO_SELF_TRANSFER",
    "ROUTE_DECLARED",
    "NO_DOUBLE_COUNT",
    "FX_DEBIT_CREDIT_COUPLED",
    "FX_CREDIT_POSITIVE",
    "FX_RATE_ORDER_SAFE",
    "FX_SOURCE_CASH",
    "FX_NATIVE_QUANTUM",
    "ORDER_QUANTIZED",
    "ORDER_MIN_IF_ACTIVE",
    "ORDER_REQUIRED_MIN",
    "ORDER_CAP",
    "ORDER_SIDE_ALLOWED",
    "NO_IMPLICIT_ROUTE",
    "SPENDABLE_CASH_NONNEGATIVE",
    "PHYSICAL_CASH_RECONCILED",
    "COST_NOT_INVESTMENT",
    "SELL_POSTED_ONCE",
    "ROUNDING_BOUND",
    "ACCOUNTING_IDENTITY",
    "FINAL_QUANTITY_NONNEGATIVE",
    "FINAL_VALUE_NONNEGATIVE",
    "SELL_WITHIN_INVENTORY",
    "BUY_DEBIT_POSITIVE",
    "SELL_NET_POSITIVE",
    "NO_ASSET_BUY_AND_SELL",
    "NO_SHORT_OR_LEVERAGE",
    "REBALANCER_NONEMPTY",
    "SELL_ELIGIBLE",
    "SELL_FUNDS_INCREMENTAL_BUY",
]
type LedgerPostingDirection = Literal["credit", "debit"]
type LedgerPostingFamily = Literal[
    "initial_selected",
    "funding_in",
    "funding_out",
    "fx_debit",
    "fx_credit",
    "buy_debit",
    "gross_sell_credit",
    "buy_fee",
    "sell_fee",
    "broker_withheld_tax",
    "self_reserved_tax",
]


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
class ExactFxRate:
    """One canonical global FX fact: 1 unit of pair_first equals `rate` units of pair_second."""

    pair_first: str
    pair_second: str
    rate: ExactRatio

    def __post_init__(self) -> None:
        _require_currency(self.pair_first, "pair_first")
        _require_currency(self.pair_second, "pair_second")
        if self.pair_first >= self.pair_second:
            raise ValueError("FX rate pair must name two distinct currencies in ascending alphabetical order")
        _require_positive(self.rate, "FX rate")

    @property
    def pair_key(self) -> str:
        return f"{self.pair_first}/{self.pair_second}"


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
    order_step: ExactRatio

    def __post_init__(self) -> None:
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
        _require_unique_values(
            tuple(schedule.fee_schedule_id for schedule in self.fee_schedules),
            "broker fee schedule IDs",
        )


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
    provenance_id: str

    def __post_init__(self) -> None:
        if not ExactRatio(0) <= self.execution_margin_rate < ExactRatio(1):
            raise ValueError("execution margin must lie in the half-open unit interval")
        if self.priority < 0:
            raise ValueError("order route priority must be nonnegative")


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
    fx_rates: tuple[ExactFxRate, ...]
    fx_spread_rate: ExactRatio
    assets: tuple[ExactAsset, ...]
    brokers: tuple[ExactBroker, ...]
    holdings: tuple[ExactHolding, ...]
    existing_cash: tuple[ExactExistingCash, ...]
    contributions: tuple[ExactContribution, ...]
    funding_routes: tuple[ExactFundingRoute, ...]
    order_routes: tuple[ExactOrderRoute, ...]
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
        _require_canonical_tuple(self.fx_rates, lambda item: (item.pair_first, item.pair_second), "fx_rates")
        if not ExactRatio(0) <= self.fx_spread_rate < ExactRatio(1):
            raise ValueError("FX spread must lie in the half-open unit interval")
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
        _require_canonical_tuple(self.target_weights, lambda item: item.asset_id, "target_weights")
        if self.valuation_currency not in {item.currency for item in self.currency_specs}:
            raise ValueError("valuation currency requires a currency spec")
        if sum((item.weight for item in self.target_weights), ExactRatio(0)) != ExactRatio(1):
            raise ValueError("target weights must total exactly one")
        if {item.asset_id for item in self.target_weights} != {item.asset_id for item in self.assets}:
            raise ValueError("target weights must cover every normalized Asset exactly once")


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


def _validate_decision_mode(
    *,
    mode: DecisionMode,
    lower_quanta: int,
    upper_quanta: int,
    baseline_quanta: int,
    frozen_quanta: int | None,
) -> None:
    if mode == "disabled":
        if (
            lower_quanta,
            upper_quanta,
            baseline_quanta,
            frozen_quanta,
        ) != (0, 0, 0, None):
            raise ValueError("disabled decisions must be fixed to zero")
    elif mode == "frozen_exact":
        if frozen_quanta is None or not lower_quanta <= frozen_quanta <= upper_quanta:
            raise ValueError("frozen_exact decisions require an in-bounds frozen value")
    elif frozen_quanta is not None:
        raise ValueError("only frozen_exact decisions can carry frozen_quanta")
    if mode == "additive_only" and lower_quanta != baseline_quanta:
        raise ValueError("additive_only lower bound must equal the frozen baseline")


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
        _require_canonical_tuple(
            self.entity_refs,
            lambda item: (item.kind, item.entity_id),
            "decision entity_refs",
        )
        integer_fields = (
            ("lower_quanta", self.lower_quanta),
            ("upper_quanta", self.upper_quanta),
            ("baseline_quanta", self.baseline_quanta),
        )
        if any(isinstance(value, bool) or not isinstance(value, int) for _name, value in integer_fields):
            raise ValueError("decision quanta bounds and baseline must be integers")
        if self.frozen_quanta is not None and (isinstance(self.frozen_quanta, bool) or not isinstance(self.frozen_quanta, int)):
            raise ValueError("frozen_quanta must be an integer")
        if self.lower_quanta < 0 or self.upper_quanta < self.lower_quanta:
            raise ValueError("decision bounds must be finite, ordered, and nonnegative")
        if not self.lower_quanta <= self.baseline_quanta <= self.upper_quanta:
            raise ValueError("baseline_quanta must lie within decision bounds")
        _validate_decision_mode(
            mode=self.mode,
            lower_quanta=self.lower_quanta,
            upper_quanta=self.upper_quanta,
            baseline_quanta=self.baseline_quanta,
            frozen_quanta=self.frozen_quanta,
        )


@dataclass(frozen=True, slots=True)
class ConstraintRef:
    ref_id: str
    code: ExactConstraintCode
    phase: ConstraintPhase
    scope: str
    entity_refs: tuple[EntityRef, ...]
    units: tuple[ExactUnit, ...]
    enforcement: ConstraintEnforcement
    bound_source: str
    public_issue_code: str | None
    explanation_key: str

    def __post_init__(self) -> None:
        _require_text(self.ref_id, "constraint ref_id")
        _require_text(self.code, "constraint code")
        _require_text(self.scope, "constraint scope")
        _require_canonical_tuple(
            self.entity_refs,
            lambda item: (item.kind, item.entity_id),
            "constraint entity_refs",
        )
        if len(self.units) != len(set(self.units)):
            raise ValueError("constraint units must not contain duplicates")
        _require_text(self.bound_source, "constraint bound_source")
        _require_text(self.explanation_key, "constraint explanation_key")


@dataclass(frozen=True, slots=True)
class ObjectiveRef:
    ref_id: str
    code: ExactObjectiveCode
    ordinal: int
    sense: ObjectiveSense
    unit: ExactUnit
    freeze_rule: str
    report_field: str
    closure_rule: str

    def __post_init__(self) -> None:
        _require_text(self.ref_id, "objective ref_id")
        _require_text(self.code, "objective code")
        if self.ordinal < 0:
            raise ValueError("objective ordinal must be nonnegative")
        _require_text(self.freeze_rule, "objective freeze_rule")
        _require_text(self.report_field, "objective report_field")
        _require_text(self.closure_rule, "objective closure_rule")


@dataclass(frozen=True, slots=True)
class TieBreakRef:
    ref_id: str
    code: str
    ordinal: int
    unit: ExactUnit
    decision_ids: tuple[str, ...]
    sense: ObjectiveSense = "min"

    def __post_init__(self) -> None:
        _require_text(self.ref_id, "tie-break ref_id")
        _require_text(self.code, "tie-break code")
        if self.ordinal < 0:
            raise ValueError("tie-break ordinal must be nonnegative")
        _require_unique_values(
            self.decision_ids,
            "tie-break decision IDs",
        )
        for decision_id in self.decision_ids:
            _require_text(decision_id, "tie-break decision ID")


@dataclass(frozen=True, slots=True)
class ProofRequirement:
    requirement_id: str
    code: str
    allowed_sources: tuple[Literal["deterministic_conflict", "exhaustive_oracle"], ...]

    def __post_init__(self) -> None:
        _require_text(self.requirement_id, "proof requirement_id")
        _require_text(self.code, "proof code")
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
        _require_text(self.gate_id, "SELL gate_id")
        _require_text(self.sell_decision_id, "SELL decision_id")
        for values, field in (
            (
                self.fixed_incremental_buy_decision_ids,
                "fixed incremental BUY decision IDs",
            ),
            (self.reopened_decision_ids, "reopened decision IDs"),
        ):
            if values != tuple(sorted(set(values))):
                raise ValueError(f"{field} must be unique and sorted")
        if self.counterfactuals != ("decrement_one_quantum", "zero_row"):
            raise ValueError("SELL irreducibility uses the frozen decrement-then-zero order")


def _validate_tie_break_coverage(
    tie_breaks: tuple[TieBreakRef, ...],
    decision_by_id: dict[str, DecisionAccess],
) -> None:
    expected_decision_ids = set(decision_by_id)
    for tie_break in tie_breaks:
        if set(tie_break.decision_ids) != expected_decision_ids:
            raise ValueError("every tie-break must cover the complete decision vector")


def _validate_sell_gate_references(
    sell_gates: tuple[SellIrreducibilityGateRef, ...],
    decision_by_id: dict[str, DecisionAccess],
) -> None:
    for gate in sell_gates:
        sell_decision = decision_by_id.get(gate.sell_decision_id)
        if sell_decision is None or sell_decision.family != "sell_quantum":
            raise ValueError("SELL gates must reference one SELL decision")
        if any(decision_by_id.get(decision_id) is None or decision_by_id[decision_id].family != "buy_quantum" for decision_id in gate.fixed_incremental_buy_decision_ids):
            raise ValueError("SELL gates can freeze only declared BUY decisions")
        if any(decision_by_id.get(decision_id) is None or decision_by_id[decision_id].family not in {"funding_transfer", "fx_debit"} for decision_id in gate.reopened_decision_ids):
            raise ValueError("SELL gates can reopen only funding and FX decisions")


@dataclass(frozen=True, slots=True)
class ExactPolicyView:
    view_id: str
    scenario_fingerprint: str
    product: PlannerProduct
    policy: PlannerPolicy
    purpose: ExactPolicyPurpose
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
        if self.purpose not in {
            "primary",
            "invest_only_baseline",
            "sell_extension",
            "deployment",
        }:
            raise ValueError("unknown exact policy purpose")
        if self.phase != "exact":
            raise ValueError("ExactPolicyView must use the exact phase")
        if (self.product == "pac") != (self.policy in {"proportional", "min_fragmentation"}):
            raise ValueError("ExactPolicyView product and policy must be compatible")
        if self.purpose == "primary" and self.policy == "invest_and_sell":
            raise ValueError("invest_and_sell requires an invest-only baseline view")
        if self.purpose in {"invest_only_baseline", "sell_extension"} and self.policy != "invest_and_sell":
            raise ValueError(f"{self.purpose} requires invest_and_sell policy")
        if self.purpose != "sell_extension" and (self.sell_gates or self.proof_requirements):
            raise ValueError("only sell_extension views can carry SELL proof metadata")
        _require_canonical_tuple(self.decisions, lambda item: item.decision_id, "decisions")
        decision_by_id = {item.decision_id: item for item in self.decisions}
        _require_canonical_tuple(self.constraints, lambda item: item.ref_id, "constraints")
        objective_ordinals = tuple(item.ordinal for item in self.objectives)
        if objective_ordinals != tuple(range(1, len(self.objectives) + 1)):
            raise ValueError("objectives must use unique contiguous ordinals from one")
        _require_unique_values(
            tuple(item.ref_id for item in self.objectives),
            "objective ref_ids",
        )
        _require_unique_values(
            tuple(item.code for item in self.objectives),
            "objective codes",
        )
        tie_ordinals = tuple(item.ordinal for item in self.tie_breaks)
        if tie_ordinals != tuple(sorted(set(tie_ordinals))):
            raise ValueError("tie_breaks must use unique ordinal order")
        _require_unique_values(
            tuple(item.ref_id for item in self.tie_breaks),
            "tie-break ref_ids",
        )
        _validate_tie_break_coverage(
            self.tie_breaks,
            decision_by_id,
        )
        _require_canonical_tuple(self.sell_gates, lambda item: item.gate_id, "sell_gates")
        _require_canonical_tuple(self.proof_requirements, lambda item: item.requirement_id, "proof_requirements")
        _validate_sell_gate_references(
            self.sell_gates,
            decision_by_id,
        )


@dataclass(frozen=True, slots=True)
class CandidateDecision:
    decision_id: str
    quanta: int

    def __post_init__(self) -> None:
        _require_text(self.decision_id, "candidate decision_id")
        if isinstance(self.quanta, bool) or not isinstance(self.quanta, int):
            raise ValueError("candidate decision quanta must be an integer")
        if self.quanta < 0:
            raise ValueError("candidate decision quanta must be nonnegative")


@dataclass(frozen=True, slots=True)
class CandidateActionVector:
    view_id: str
    candidate_id: str
    decisions: tuple[CandidateDecision, ...]

    def __post_init__(self) -> None:
        _require_text(self.view_id, "candidate view_id")
        _require_text(self.candidate_id, "candidate_id")
        _require_canonical_tuple(self.decisions, lambda item: item.decision_id, "candidate decisions")


@dataclass(frozen=True, slots=True)
class ExactConflict:
    code: str
    entity_refs: tuple[EntityRef, ...]

    def __post_init__(self) -> None:
        _require_text(self.code, "conflict code")
        _require_canonical_tuple(
            self.entity_refs,
            lambda item: (item.kind, item.entity_id),
            "conflict entity_refs",
        )


@dataclass(frozen=True, slots=True)
class ExactLedgerPosting:
    posting_id: str
    family: LedgerPostingFamily
    direction: LedgerPostingDirection
    broker_id: str
    currency: str
    entity_refs: tuple[EntityRef, ...]
    exact_amount: ExactRatio
    posted_amount: ExactRatio
    quantum: ExactRatio | None
    rounding_delta: ExactRatio

    def __post_init__(self) -> None:
        _require_text(self.posting_id, "posting_id")
        _require_text(self.broker_id, "posting broker_id")
        _require_currency(self.currency, "posting currency")
        _require_canonical_tuple(
            self.entity_refs,
            lambda item: (item.kind, item.entity_id),
            "posting entity_refs",
        )
        _require_nonnegative(self.exact_amount, "posting exact_amount")
        _require_nonnegative(self.posted_amount, "posting posted_amount")
        if self.rounding_delta != self.posted_amount - self.exact_amount:
            raise ValueError("posting rounding_delta must equal posted minus exact")
        if self.quantum is None:
            if self.rounding_delta != ExactRatio(0):
                raise ValueError("unrounded postings must have zero rounding delta")
        else:
            _require_positive(self.quantum, "posting quantum")

    @property
    def accounting_rounding_adjustment(self) -> ExactRatio:
        """Return the debit-positive contribution used by ``A_round``."""
        if self.direction == "debit":
            return self.rounding_delta
        return -self.rounding_delta


@dataclass(frozen=True, slots=True)
class ExactFundingTransferEvaluation:
    decision_id: str
    route_id: str
    source_kind: Literal["existing_cash", "contribution"]
    source_id: str
    destination_broker_id: str
    currency: str
    quanta: int
    amount: ExactRatio

    def __post_init__(self) -> None:
        _require_text(self.decision_id, "funding decision_id")
        _require_text(self.route_id, "funding route_id")
        _require_text(self.source_id, "funding source_id")
        _require_text(self.destination_broker_id, "funding destination_broker_id")
        _require_currency(self.currency, "funding currency")
        if isinstance(self.quanta, bool) or not isinstance(self.quanta, int) or self.quanta < 0:
            raise ValueError("funding quanta must be a nonnegative integer")
        _require_nonnegative(self.amount, "funding amount")


@dataclass(frozen=True, slots=True)
class ExactFundingSourceEvaluation:
    source_kind: Literal["existing_cash", "contribution"]
    source_id: str
    source_broker_id: str | None
    currency: str
    selected: ExactRatio
    transferred: ExactRatio
    remaining: ExactRatio
    structurally_reachable_amount: ExactRatio
    structurally_trapped_amount: ExactRatio

    def __post_init__(self) -> None:
        _require_text(self.source_id, "funding source_id")
        _require_currency(self.currency, "funding source currency")
        _require_nonnegative(self.selected, "selected funding")
        _require_nonnegative(self.transferred, "transferred funding")
        if self.remaining != self.selected - self.transferred:
            raise ValueError("funding remaining must reconcile selected and transferred")
        _require_nonnegative(self.structurally_reachable_amount, "structurally_reachable_amount")
        _require_nonnegative(self.structurally_trapped_amount, "structurally_trapped_amount")
        # `remaining` may go negative on an overcommitted source (transferred >
        # selected, flagged separately by FUNDING_WITHIN_SELECTED); the reachable/
        # trapped split is always nonnegative, so it reconciles against the
        # nonnegative floor of `remaining`, not `remaining` itself.
        if self.structurally_reachable_amount + self.structurally_trapped_amount != max(self.remaining, ExactRatio(0)):
            raise ValueError("structurally reachable and trapped amounts must reconcile with remaining funding")


@dataclass(frozen=True, slots=True)
class ExactFxEvaluation:
    decision_id: str
    order_route_id: str
    broker_id: str
    source_currency: str
    destination_currency: str
    quanta: int
    source_debit: ExactRatio
    approved_rate: ExactRatio
    effective_rate: ExactRatio
    exact_destination_credit: ExactRatio
    posted_destination_credit: ExactRatio
    spread_loss: ExactRatio

    def __post_init__(self) -> None:
        _require_text(self.decision_id, "FX decision_id")
        _require_text(self.order_route_id, "FX order_route_id")
        _require_text(self.broker_id, "FX broker_id")
        _require_currency(self.source_currency, "FX source_currency")
        _require_currency(self.destination_currency, "FX destination_currency")
        if self.source_currency == self.destination_currency:
            raise ValueError("FX evaluation must be nonidentity")
        if isinstance(self.quanta, bool) or not isinstance(self.quanta, int) or self.quanta < 0:
            raise ValueError("FX quanta must be a nonnegative integer")
        for field, value in (
            ("source_debit", self.source_debit),
            ("exact_destination_credit", self.exact_destination_credit),
            ("posted_destination_credit", self.posted_destination_credit),
            ("spread_loss", self.spread_loss),
        ):
            _require_nonnegative(value, field)
        _require_positive(self.approved_rate, "approved_rate")
        _require_positive(self.effective_rate, "effective_rate")
        if self.effective_rate > self.approved_rate:
            raise ValueError("effective FX rate cannot exceed approved rate")


@dataclass(frozen=True, slots=True)
class ExactOrderEvaluation:
    decision_id: str
    route_id: str
    side: OrderSide
    broker_id: str
    asset_id: str
    capability_kind: CapabilityKind
    native_currency: str
    source_currency: str
    source_quote_base_quantity: ExactRatio
    quanta: int
    order_measure: ExactRatio
    economic_quantity: ExactRatio
    source_unit_price: ExactRatio
    mid_unit_price: ExactRatio
    execution_unit_price: ExactRatio
    exact_cash_amount: ExactRatio
    posted_cash_amount: ExactRatio
    exact_fee: ExactRatio
    posted_fee: ExactRatio
    mid_value: ExactRatio
    execution_margin_loss: ExactRatio
    cost_basis: ExactRatio
    taxable_gain: ExactRatio
    exact_tax_reserve: ExactRatio
    posted_tax_reserve: ExactRatio
    withholding_kind: Literal["broker_withheld", "self_reserved"] | None

    def __post_init__(self) -> None:
        _require_text(self.decision_id, "order decision_id")
        _require_text(self.route_id, "order route_id")
        _require_text(self.broker_id, "order broker_id")
        _require_text(self.asset_id, "order asset_id")
        _require_currency(self.native_currency, "order native_currency")
        _require_currency(self.source_currency, "order source_currency")
        if isinstance(self.quanta, bool) or not isinstance(self.quanta, int) or self.quanta <= 0:
            raise ValueError("active order quanta must be a positive integer")
        for field, value in (
            ("order_measure", self.order_measure),
            ("economic_quantity", self.economic_quantity),
            (
                "source_quote_base_quantity",
                self.source_quote_base_quantity,
            ),
            ("source_unit_price", self.source_unit_price),
            ("mid_unit_price", self.mid_unit_price),
            ("execution_unit_price", self.execution_unit_price),
            ("exact_cash_amount", self.exact_cash_amount),
            ("posted_cash_amount", self.posted_cash_amount),
            ("exact_fee", self.exact_fee),
            ("posted_fee", self.posted_fee),
            ("mid_value", self.mid_value),
            ("execution_margin_loss", self.execution_margin_loss),
            ("cost_basis", self.cost_basis),
            ("taxable_gain", self.taxable_gain),
            ("exact_tax_reserve", self.exact_tax_reserve),
            ("posted_tax_reserve", self.posted_tax_reserve),
        ):
            _require_nonnegative(value, field)
        _require_positive(
            self.source_quote_base_quantity,
            "source_quote_base_quantity",
        )
        if self.side == "buy":
            if self.mid_unit_price > self.execution_unit_price:
                raise ValueError("BUY execution price cannot be below mid")
            if any(
                value != ExactRatio(0)
                for value in (
                    self.cost_basis,
                    self.taxable_gain,
                    self.exact_tax_reserve,
                    self.posted_tax_reserve,
                )
            ):
                raise ValueError("BUY evaluations cannot carry SELL tax values")
            if self.withholding_kind is not None:
                raise ValueError("BUY evaluations cannot carry withholding")
        elif self.execution_unit_price > self.mid_unit_price:
            raise ValueError("SELL execution price cannot exceed mid")
        elif self.withholding_kind is None:
            raise ValueError("SELL evaluations require withholding kind")


@dataclass(frozen=True, slots=True)
class ExactBrokerLedgerEvaluation:
    broker_id: str
    currency: str
    initial_selected: ExactRatio
    funding_in: ExactRatio
    funding_out: ExactRatio
    fx_debit: ExactRatio
    fx_credit: ExactRatio
    buy_debit: ExactRatio
    gross_sell_credit: ExactRatio
    buy_fees: ExactRatio
    sell_fees: ExactRatio
    broker_withheld_tax: ExactRatio
    self_reserved_tax: ExactRatio
    raw_rounding_delta: ExactRatio
    accounting_rounding_adjustment: ExactRatio
    final_spendable: ExactRatio
    final_physical: ExactRatio

    def __post_init__(self) -> None:
        _require_text(self.broker_id, "ledger broker_id")
        _require_currency(self.currency, "ledger currency")
        for field in (
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
        ):
            _require_nonnegative(getattr(self, field), field)
        expected_spendable = self.initial_selected + self.funding_in + self.fx_credit + self.gross_sell_credit - self.funding_out - self.fx_debit - self.buy_debit - self.buy_fees - self.sell_fees - self.broker_withheld_tax - self.self_reserved_tax
        if self.final_spendable != expected_spendable:
            raise ValueError("ledger final_spendable does not reconcile")
        if self.final_physical != self.final_spendable + self.self_reserved_tax:
            raise ValueError("ledger final_physical does not reconcile")


@dataclass(frozen=True, slots=True)
class ExactHoldingEvaluation:
    asset_id: str
    broker_id: str
    initial_quantity: ExactRatio
    buy_quantity: ExactRatio
    sell_quantity: ExactRatio
    final_quantity: ExactRatio

    def __post_init__(self) -> None:
        _require_text(self.asset_id, "holding asset_id")
        _require_text(self.broker_id, "holding broker_id")
        _require_nonnegative(self.initial_quantity, "initial_quantity")
        _require_nonnegative(self.buy_quantity, "buy_quantity")
        _require_nonnegative(self.sell_quantity, "sell_quantity")
        if self.final_quantity != self.initial_quantity + self.buy_quantity - self.sell_quantity:
            raise ValueError("holding final_quantity does not reconcile")


@dataclass(frozen=True, slots=True)
class ExactAssetEvaluation:
    asset_id: str
    target_weight: ExactRatio
    current_value: ExactRatio
    target_value: ExactRatio
    buy_mid_value: ExactRatio
    sell_mid_value: ExactRatio
    final_value: ExactRatio
    residual: ExactRatio

    def __post_init__(self) -> None:
        _require_text(self.asset_id, "Asset evaluation asset_id")
        _require_unit_interval(self.target_weight, "target_weight")
        for field in (
            "current_value",
            "target_value",
            "buy_mid_value",
            "sell_mid_value",
        ):
            _require_nonnegative(getattr(self, field), field)
        if self.final_value != self.current_value + self.buy_mid_value - self.sell_mid_value:
            raise ValueError("Asset final_value does not reconcile")
        if self.residual != self.final_value - self.target_value:
            raise ValueError("Asset residual does not reconcile")


@dataclass(frozen=True, slots=True)
class ExactAccountingEvaluation:
    current_invested: ExactRatio
    selected_funding: ExactRatio
    reachable_funding: ExactRatio
    trapped_funding: ExactRatio
    fixed_reference: ExactRatio
    final_invested: ExactRatio
    shortfall: ExactRatio
    free_cash: ExactRatio
    physical_reserves: ExactRatio
    economic_losses: ExactRatio
    rounding_adjustment: ExactRatio
    rounding_bound: ExactRatio
    identity_delta: ExactRatio

    def __post_init__(self) -> None:
        for field in (
            "current_invested",
            "selected_funding",
            "reachable_funding",
            "trapped_funding",
            "fixed_reference",
            "physical_reserves",
            "rounding_bound",
        ):
            _require_nonnegative(getattr(self, field), field)
        if self.trapped_funding != self.selected_funding - self.reachable_funding:
            raise ValueError("trapped funding must equal selected less reachable")
        if self.fixed_reference != self.current_invested + self.reachable_funding:
            raise ValueError("fixed reference must equal current invested plus reachable funding")
        if self.shortfall != self.fixed_reference - self.final_invested:
            raise ValueError("shortfall must equal fixed reference less final invested")
        expected_delta = self.shortfall - (self.free_cash + self.physical_reserves + self.economic_losses + self.rounding_adjustment)
        if self.identity_delta != expected_delta:
            raise ValueError("accounting identity_delta does not reconcile")


@dataclass(frozen=True, slots=True)
class ExactCostEvaluation:
    buy_fees: ExactRatio
    sell_fees: ExactRatio
    fx_spread_loss: ExactRatio
    execution_margin_loss: ExactRatio
    broker_withheld_tax: ExactRatio
    self_reserved_tax: ExactRatio
    explicit_cost: ExactRatio

    def __post_init__(self) -> None:
        for field in (
            "buy_fees",
            "sell_fees",
            "execution_margin_loss",
            "broker_withheld_tax",
            "self_reserved_tax",
        ):
            _require_nonnegative(getattr(self, field), field)
        expected = self.buy_fees + self.sell_fees + self.fx_spread_loss + self.execution_margin_loss + self.broker_withheld_tax + self.self_reserved_tax
        if self.explicit_cost != expected:
            raise ValueError("explicit cost does not reconcile")


@dataclass(frozen=True, slots=True)
class ExactConstraintEvaluation:
    ref_id: str
    satisfied: bool
    value: ExactRatio
    lower_bound: ExactRatio | None
    upper_bound: ExactRatio | None

    def __post_init__(self) -> None:
        _require_text(self.ref_id, "constraint evaluation ref_id")
        if self.lower_bound is not None and self.upper_bound is not None and self.lower_bound > self.upper_bound:
            raise ValueError("constraint evaluation bounds must be ordered")


@dataclass(frozen=True, slots=True)
class ExactObjectiveEvaluation:
    ref_id: str
    value: ExactRatio

    def __post_init__(self) -> None:
        _require_text(self.ref_id, "objective evaluation ref_id")


@dataclass(frozen=True, slots=True)
class ExactEvaluation:
    view_id: str
    candidate_id: str
    feasible: bool
    constraints: tuple[ExactConstraintEvaluation, ...]
    objectives: tuple[ExactObjectiveEvaluation, ...]
    conflict_codes: tuple[str, ...]
    candidate_valid: bool = True
    conflicts: tuple[ExactConflict, ...] = ()
    postings: tuple[ExactLedgerPosting, ...] = ()
    funding_transfers: tuple[ExactFundingTransferEvaluation, ...] = ()
    funding_sources: tuple[ExactFundingSourceEvaluation, ...] = ()
    fx: tuple[ExactFxEvaluation, ...] = ()
    orders: tuple[ExactOrderEvaluation, ...] = ()
    ledgers: tuple[ExactBrokerLedgerEvaluation, ...] = ()
    holdings: tuple[ExactHoldingEvaluation, ...] = ()
    assets: tuple[ExactAssetEvaluation, ...] = ()
    accounting: ExactAccountingEvaluation | None = None
    costs: ExactCostEvaluation | None = None
    canonical_tie_decision_ids: tuple[str, ...] = ()
    canonical_tie_quanta: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        _require_canonical_tuple(self.constraints, lambda item: item.ref_id, "constraint evaluations")
        _require_canonical_tuple(self.objectives, lambda item: item.ref_id, "objective evaluations")
        if self.conflict_codes != tuple(sorted(set(self.conflict_codes))):
            raise ValueError("conflict_codes must be unique and sorted")
        _require_canonical_tuple(
            self.conflicts,
            lambda item: (
                item.code,
                tuple((ref.kind, ref.entity_id) for ref in item.entity_refs),
            ),
            "conflicts",
        )
        _require_canonical_tuple(self.postings, lambda item: item.posting_id, "postings")
        _require_canonical_tuple(
            self.funding_transfers,
            lambda item: item.route_id,
            "funding transfers",
        )
        _require_canonical_tuple(
            self.funding_sources,
            lambda item: (item.source_kind, item.source_id),
            "funding sources",
        )
        _require_canonical_tuple(self.fx, lambda item: (item.order_route_id, item.source_currency), "FX evaluations")
        _require_canonical_tuple(self.orders, lambda item: item.route_id, "order evaluations")
        _require_canonical_tuple(
            self.ledgers,
            lambda item: (item.broker_id, item.currency),
            "ledger evaluations",
        )
        _require_canonical_tuple(
            self.holdings,
            lambda item: (item.asset_id, item.broker_id),
            "holding evaluations",
        )
        _require_canonical_tuple(self.assets, lambda item: item.asset_id, "Asset evaluations")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in self.canonical_tie_quanta):
            raise ValueError("canonical tie quanta must be nonnegative integers")
        _require_unique_values(
            self.canonical_tie_decision_ids,
            "canonical tie decision IDs",
        )
        if len(self.canonical_tie_decision_ids) != len(self.canonical_tie_quanta):
            raise ValueError("canonical tie decision IDs and quanta must align")
        if self.feasible and (not self.candidate_valid or self.accounting is None or self.costs is None):
            raise ValueError("feasible exact evaluations require a valid complete economic evaluation")
        expected_conflict_codes = tuple(sorted({item.code for item in self.conflicts}))
        if self.conflict_codes != expected_conflict_codes:
            raise ValueError("conflict_codes must equal the canonical conflict catalogue")
        expected_feasible = self.candidate_valid and all(item.satisfied for item in self.constraints) and not self.conflicts
        if self.feasible != expected_feasible:
            raise ValueError("feasible must match candidate, constraint, and conflict state")
        if self.candidate_valid and (self.accounting is None or self.costs is None):
            raise ValueError("valid candidates require complete accounting and costs")
        if not self.candidate_valid and any(
            (
                self.constraints,
                self.objectives,
                self.postings,
                self.funding_transfers,
                self.funding_sources,
                self.fx,
                self.orders,
                self.ledgers,
                self.holdings,
                self.assets,
                self.accounting is not None,
                self.costs is not None,
                self.canonical_tie_decision_ids,
                self.canonical_tie_quanta,
            )
        ):
            raise ValueError("invalid candidate contracts cannot carry economic results")
