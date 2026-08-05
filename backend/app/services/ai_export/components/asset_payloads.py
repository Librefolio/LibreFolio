"""Pydantic payload models for the Asset-core `ComponentSpec` builders.

Deliberately independent from the public wire schemas and from
`backend.app.services.ai_export.components.catalog` (the fail-closed foundation
metadata this module implements). Every model here is `extra="forbid"`,
Decimal-safe (via
`backend.app.schemas.common.SafeDecimal`, which always serializes in plain
decimal notation - never scientific notation - see that module) and
JSON-safe, so `backend.app.services.ai_export.components.envelope.
build_envelope` can validate/serialize it deterministically.

Covers the eight non-technical Asset components (workstream E2, "Asset
core" wave): `asset.identity`, `asset.market_snapshot`,
`asset.position_scope`, `asset.provenance`, `asset.positions_by_broker`,
`asset.cost_value_pl`, `asset.performance`, `asset.lot_detail`. The three
technical Asset components (`asset.ohlc_returns`, `asset.indicators`,
`asset.states_events`) belong to the sibling technical-shared wave and are
not defined here.

Money fields fall into two categories:
- `Currency` (code + amount) is used only where the amount's currency can
  differ from `target_currency` at the row level - i.e. the native-currency
  price observation in `asset.market_snapshot`.
- Plain `SafeDecimal` is used everywhere else, because those values come
  straight from `PortfolioHolding`/`AssetPeriodContribution`/
  `LotSummarySchema` (all already expressed in the report/analysis's single
  `target_currency`) - the payload's own `target_currency` field is the one
  and only currency code for every such amount, so wrapping each row value
  in a redundant `Currency` would duplicate that code without adding
  information.
"""

from __future__ import annotations

from datetime import date as Date
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from backend.app.schemas.common import Currency, DateRangeModel, SafeDecimal


class AssetComponentModel(BaseModel):
    """Shared strict-shape base for every Asset-core component payload."""

    model_config = ConfigDict(extra="forbid")


# =============================================================================
# asset.identity
# =============================================================================


class AssetGeographicWeight(AssetComponentModel):
    """One geographic-area weight, verbatim from `Asset.classification_params`."""

    area: str
    weight: SafeDecimal


class AssetSectorWeight(AssetComponentModel):
    """One sector weight, verbatim from `Asset.classification_params`."""

    sector: str
    weight: SafeDecimal


class AssetIdentifiers(AssetComponentModel):
    """Every identifier column recorded for this asset - factual data, never a link-out."""

    isin: str | None = None
    ticker: str | None = None
    cusip: str | None = None
    sedol: str | None = None
    figi: str | None = None
    other: tuple[str, ...] = ()


class AssetClassification(AssetComponentModel):
    """Structured classification plus the free-text provider/user description, kept as data only.

    `short_description` is never interpreted, templated or used for control
    flow anywhere in this runtime - it is carried through verbatim, exactly
    like every other field here, even if it contains adversarial content
    (e.g. markup or script-like text): this component only ever describes
    data, it does not render or execute it.
    """

    short_description: str | None = None
    geographic_area: tuple[AssetGeographicWeight, ...] = ()
    sector_area: tuple[AssetSectorWeight, ...] = ()


class AssetIdentityPayload(AssetComponentModel):
    """`asset.identity` payload: point-in-time identity/classification/currency facts."""

    asset_id: int
    display_name: str
    currency: str
    asset_type: str
    quote_base_quantity: int
    active: bool
    identifiers: AssetIdentifiers
    classification: AssetClassification


# =============================================================================
# asset.market_snapshot
# =============================================================================


class AssetFxConversionDirection(StrEnum):
    """How the observed native price was converted to the target currency."""

    IDENTITY = "identity"  # native currency == target currency, no conversion
    DIRECT = "direct"  # native currency is the alphabetically-first (base) leg
    INVERSE = "inverse"  # native currency is the alphabetically-second (quote) leg


class AssetPriceObservation(AssetComponentModel):
    """One observed daily close, in its native currency, with source provenance."""

    date: Date
    native_price: Currency
    source_plugin_key: str


class AssetFxConversionProvenance(AssetComponentModel):
    """Provenance of the native -> target currency conversion applied to `AssetPriceObservation`."""

    rate_date: Date
    direction: AssetFxConversionDirection
    backward_fill_applied: bool


class AssetMarketSnapshotPayload(AssetComponentModel):
    """`asset.market_snapshot` payload: current observed market price, never WAC/cost-derived.

    `observed`/`converted_price`/`conversion` are all `None` together when no
    priced observation exists at or before `as_of_date` - a valid, empty
    snapshot (e.g. a newly-added asset with no price history yet), never a
    build failure by itself. This is deliberately the *observed* market
    price with FX provenance, never the Portfolio Engine's WAC/cost basis
    masquerading as a market price - see `asset.cost_value_pl` for WAC.
    """

    asset_id: int
    as_of_date: Date
    target_currency: str
    observed: AssetPriceObservation | None = None
    converted_price: Currency | None = None
    conversion: AssetFxConversionProvenance | None = None


# =============================================================================
# asset.position_scope
# =============================================================================


class AssetPositionScopeBroker(AssetComponentModel):
    """One broker currently holding this asset."""

    broker_id: int
    broker_name: str
    quantity: SafeDecimal


class AssetPortfolioRoleUnavailable(AssetComponentModel):
    """One factual reason a `portfolio_role` numerator/denominator/ratio is `None`.

    Deterministic, machine-stable `field` code plus a human-readable
    `reason`. Present only when the corresponding value could not be
    computed from valued open-position legs - never a stand-in for a
    silent `0` (requirement 2: missing valuation yields an explicit
    unavailable field/reason, not a zero).
    """

    field: str
    reason: str


class AssetPortfolioRoleBasis(AssetComponentModel):
    """Deterministic, purely quantitative portfolio-weight/role basis for this asset.

    Data-backs the `asset.position_review` contract's "FIFO and Portfolio
    Role" section WITHOUT interpreting core/satellite: it exposes only the
    factual denominators/counts an interpreting model needs, never a
    subjective role label.

    Valuation basis (both numerator and denominator): current mark-to-market
    open-position value at `as_of_date`, expressed in `target_currency` (the
    same single currency as every other value in this payload - see the
    module docstring). The portfolio denominator is *gross absolute*: the sum
    of `abs(current_value)` across every accessible open-position leg, so a
    short/negative leg contributes its magnitude (never a partial or negative
    cancellation) - this is what makes `portfolio_weight_ratio` a stable
    concentration weight even with short positions.

    `broker_scope_mode` records whether the denominator spans the whole
    accessible portfolio (`WHOLE_ACCESSIBLE_PORTFOLIO`, no `BuildScope.
    broker_scope`) or only the requested broker subset (`SCOPED_BROKERS`).

    Every value is `None`-with-reason (see `unavailable`) rather than a
    silent `0` whenever a contributing leg lacks a valuation, so a partial
    price/FX gap can never masquerade as a real concentration figure.
    """

    target_currency: str
    valuation_basis: Literal["current_market_value"] = "current_market_value"
    denominator_basis: Literal["gross_absolute_open_position_value"] = "gross_absolute_open_position_value"
    broker_scope_mode: Literal["WHOLE_ACCESSIBLE_PORTFOLIO", "SCOPED_BROKERS"]
    asset_market_value: SafeDecimal | None = None
    asset_gross_absolute_value: SafeDecimal | None = None
    portfolio_gross_absolute_value: SafeDecimal | None = None
    portfolio_weight_ratio: SafeDecimal | None = None
    position_leg_count: int = 0
    broker_count: int = 0
    unavailable: tuple[AssetPortfolioRoleUnavailable, ...] = ()


class AssetPositionScopePayload(AssetComponentModel):
    """`asset.position_scope` payload: which brokers hold this asset, plus aggregate context.

    Retains one row per broker at every detail level (compact/standard/
    full never truncate this list) in deterministic `broker_id` order. An
    asset with no current holdings in scope is a valid, empty result
    (`brokers=()`, `broker_count=0`), never a build failure.

    `portfolio_role` adds a deterministic, non-interpretive portfolio-weight
    basis (this asset's aggregate value vs the scoped portfolio's gross
    absolute open-position value) for the `asset.position_review` contract -
    see `AssetPortfolioRoleBasis`.
    """

    asset_id: int
    as_of_date: Date
    target_currency: str
    brokers: tuple[AssetPositionScopeBroker, ...] = ()
    total_quantity: SafeDecimal = Decimal("0")
    broker_count: int = 0
    portfolio_role: AssetPortfolioRoleBasis | None = None


# =============================================================================
# asset.provenance
# =============================================================================


class AssetProviderAssignmentInfo(AssetComponentModel):
    """Factual pricing-provider assignment for this asset, when one exists."""

    provider_code: str
    identifier_type: str
    identifier: str | None = None
    last_fetch_date: Date | None = None


class AssetValuationSourceSemantic(AssetComponentModel):
    """One stable code -> description pair documenting a `valuation_source` value.

    `code`/`description` are static runtime methodology text (not user/
    provider content): they describe what the Portfolio Engine's
    `valuation_source` values mean, never data about a specific asset.
    """

    code: str
    description: str


class AssetProvenancePayload(AssetComponentModel):
    """`asset.provenance` payload: semantics/methodology, independent of the AI Export period."""

    asset_id: int
    provider: AssetProviderAssignmentInfo | None = None
    valuation_source_semantics: tuple[AssetValuationSourceSemantic, ...]
    price_provenance_note: str


# =============================================================================
# asset.positions_by_broker
# =============================================================================


class AssetPositionValuationSource(StrEnum):
    """Mirrors `backend.app.schemas.portfolio.PortfolioHolding.valuation_source`."""

    MARKET_PRICE = "MARKET_PRICE"
    LAST_TRADE_PRICE = "LAST_TRADE_PRICE"
    MISSING = "MISSING"


class AssetBrokerPosition(AssetComponentModel):
    """One broker's current position in this asset - engine-derived, never recomputed here."""

    broker_id: int
    broker_name: str
    quantity: SafeDecimal
    valuation_source: AssetPositionValuationSource | None = None
    wac_per_unit: SafeDecimal | None = None
    unit_price: SafeDecimal | None = None
    current_value: SafeDecimal | None = None
    unrealized_gain_loss: SafeDecimal | None = None
    unrealized_gain_loss_percent: SafeDecimal | None = None


class AssetPositionsByBrokerPayload(AssetComponentModel):
    """`asset.positions_by_broker` payload: per-broker position rows for this asset.

    Retains one row per broker at every detail level, same `broker_id`
    universe/order as `asset.position_scope` (both are derived from the
    same memoized `PortfolioReportResponse.summary` resource).
    """

    asset_id: int
    as_of_date: Date
    target_currency: str
    positions: tuple[AssetBrokerPosition, ...] = ()


# =============================================================================
# Shared aggregate-coverage metadata (asset.cost_value_pl, asset.performance)
# =============================================================================


class AssetCoverageOmission(AssetComponentModel):
    """One broker row excluded from an aggregate total, and which required field(s) were missing."""

    broker_id: int
    missing_fields: tuple[str, ...]


class AssetAggregateCoverage(AssetComponentModel):
    """Coverage/completeness metadata for an aggregate total computed over a subset of broker rows.

    Aggregate totals are only ever summed over the "valued" subset - broker
    rows carrying every field required for reconciliation. `is_complete` is
    `True` only when `valued_broker_count == total_broker_count`; otherwise
    the aggregate is a partial figure and must never be presented as a
    complete portfolio total. `omitted` lists exactly which broker(s) were
    excluded from the aggregate and why, never silently dropped.
    """

    total_broker_count: int
    valued_broker_count: int
    omitted: tuple[AssetCoverageOmission, ...] = ()
    is_complete: bool


# =============================================================================
# asset.cost_value_pl
# =============================================================================


class AssetBrokerCostValuePl(AssetComponentModel):
    """One broker's cost/value/P&L breakdown for this asset - engine-derived."""

    broker_id: int
    broker_name: str
    quantity: SafeDecimal
    wac_per_unit: SafeDecimal | None = None
    cost_basis: SafeDecimal | None = None
    current_value: SafeDecimal | None = None
    unrealized_gain_loss: SafeDecimal | None = None
    unrealized_gain_loss_percent: SafeDecimal | None = None


class AssetCostValuePlPayload(AssetComponentModel):
    """`asset.cost_value_pl` payload: WAC vs current valuation, per broker and aggregated.

    `cost_basis = wac_per_unit * quantity`, a plain multiplication - not a
    duplicate of any engine-owned formula (`PortfolioHolding` has no direct
    `cost_basis` field, only `wac_per_unit`). Every per-broker row is always
    retained (see `coverage.total_broker_count`); aggregate totals sum only
    the "valued" subset - rows carrying `cost_basis`, `current_value` AND
    `unrealized_gain_loss` (the engine's own `gain_loss`, never recomputed
    as `current_value - cost_basis`, which could silently reconcile
    incoherent subsets) - see `coverage`. When no broker row is fully
    valued, totals are `None` rather than a misleading `0`.
    """

    asset_id: int
    as_of_date: Date
    target_currency: str
    brokers: tuple[AssetBrokerCostValuePl, ...] = ()
    coverage: AssetAggregateCoverage
    total_cost_basis: SafeDecimal | None = None
    total_current_value: SafeDecimal | None = None
    total_unrealized_gain_loss: SafeDecimal | None = None


# =============================================================================
# asset.performance
# =============================================================================


class AssetBrokerPeriodPerformance(AssetComponentModel):
    """One broker's period performance contribution for this asset - engine-derived passthrough."""

    broker_id: int
    broker_name: str
    start_value: SafeDecimal | None = None
    end_value: SafeDecimal | None = None
    period_pnl: SafeDecimal | None = None
    period_pnl_percent: SafeDecimal | None = None
    period_realized_gain_loss: SafeDecimal | None = None
    period_unrealized_delta: SafeDecimal | None = None
    period_income: SafeDecimal | None = None
    period_fees_taxes: SafeDecimal | None = None
    is_fully_sold: bool = False


class AssetPerformancePayload(AssetComponentModel):
    """`asset.performance` payload: engine period-contribution outputs over the unified scope period.

    Every per-broker row is always retained (see
    `coverage.total_broker_count`). No return formula is recomputed here
    beyond simple aggregation over the "valued" subset - rows carrying
    `start_value`, `end_value` AND `period_pnl` together, so the aggregate
    percent's numerator (`total_period_pnl`) and denominator
    (`total_start_value`) subsets always match exactly by construction (see
    `coverage`). `total_period_pnl_percent = total_period_pnl /
    abs(total_start_value)`, computed only when `total_start_value` is not
    `None` and not `0` - the same ratio the engine already applies
    per-broker, applied once more at the asset-aggregate level, which the
    engine itself does not expose. When no broker row is fully valued,
    totals (and the percent) are `None` rather than a misleading `0`.
    """

    asset_id: int
    period: DateRangeModel
    target_currency: str
    zero_semantics: str
    brokers: tuple[AssetBrokerPeriodPerformance, ...] = ()
    coverage: AssetAggregateCoverage
    total_start_value: SafeDecimal | None = None
    total_end_value: SafeDecimal | None = None
    total_period_pnl: SafeDecimal | None = None
    total_period_pnl_percent: SafeDecimal | None = None


# =============================================================================
# asset.lot_detail
# =============================================================================


class AssetLotCustodyRow(AssetComponentModel):
    """One current custody slice of a lot's still-open quantity. No transaction/lot identifiers.

    `broker_id` is `None` for in-transit slices (mirrors
    `LotCustodySummarySchema.broker_id`), never omitted/defaulted to a
    sentinel broker.
    """

    broker_id: int | None = None
    custody_type: Literal["BROKER", "IN_TRANSIT"]
    quantity: SafeDecimal


class AssetLotDetailRow(AssetComponentModel):
    """One lot with a prompt-local audit reference, never a database identifier."""

    lot_ref: str
    opening_broker_id: int
    opening_date: Date
    opening_unit_price: SafeDecimal
    original_quantity: SafeDecimal
    original_cost: SafeDecimal
    open_quantity: SafeDecimal
    realized_quantity: SafeDecimal
    cumulative_proceeds: SafeDecimal
    realized_pnl: SafeDecimal
    open_value: SafeDecimal | None = None
    unrealized_pnl: SafeDecimal | None = None
    total_pnl: SafeDecimal | None = None
    net_total_pnl: SafeDecimal | None = None
    income: SafeDecimal
    allocated_fees: SafeDecimal
    allocated_taxes: SafeDecimal
    value_source: str | None = None
    net_metrics_status: str
    states: tuple[str, ...] = ()
    closing_date: Date | None = None
    current_custody: tuple[AssetLotCustodyRow, ...] = ()


class AssetLotDetailPayload(AssetComponentModel):
    """`asset.lot_detail` payload: open/partial lots, plus lots closed within the period.

    Includes every lot with `open_quantity != 0` (open or partially closed -
    mirrors `FifoEngineResult.get_lot_states()`'s OPEN/PARTIALLY_CLOSED
    semantics, never `closing_date` alone) or with `open_quantity == 0` AND
    an authoritative `closing_date >= period_start`; never a top-N/7+3 style
    truncation, and never a standalone full-FIFO export. `lots=()` is a
    valid, empty result (e.g. an asset with no lots at all in scope), never
    a build failure by itself.

    A lot reported as fully closed (`open_quantity == 0`) but missing its
    authoritative `closing_date` is a data-quality problem, not an open lot:
    it is omitted from `lots` rather than silently treated as open, and
    counted in `omitted_degraded_lot_count` (no lot/transaction identifiers
    are ever exposed, per this component's no-ID contract).
    """

    asset_id: int
    period: DateRangeModel
    target_currency: str
    cost_allocation_semantics: str
    lots: tuple[AssetLotDetailRow, ...] = ()
    omitted_degraded_lot_count: int = 0


__all__ = [
    "AssetAggregateCoverage",
    "AssetBrokerCostValuePl",
    "AssetBrokerPeriodPerformance",
    "AssetBrokerPosition",
    "AssetClassification",
    "AssetComponentModel",
    "AssetCostValuePlPayload",
    "AssetCoverageOmission",
    "AssetFxConversionDirection",
    "AssetFxConversionProvenance",
    "AssetGeographicWeight",
    "AssetIdentifiers",
    "AssetIdentityPayload",
    "AssetLotCustodyRow",
    "AssetLotDetailPayload",
    "AssetLotDetailRow",
    "AssetMarketSnapshotPayload",
    "AssetPerformancePayload",
    "AssetPositionScopeBroker",
    "AssetPositionScopePayload",
    "AssetPositionValuationSource",
    "AssetPositionsByBrokerPayload",
    "AssetPriceObservation",
    "AssetProviderAssignmentInfo",
    "AssetProvenancePayload",
    "AssetSectorWeight",
    "AssetValuationSourceSemantic",
]
