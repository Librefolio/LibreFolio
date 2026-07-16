"""
Portfolio schemas for LibreFolio.

Schemas for the /api/v1/portfolio/ endpoints:
- WAC time series (point-per-transaction where WAC changes)
- Portfolio summary (net worth, ROI, allocations, holdings)
- Portfolio history (daily cash/market_value/nav series)
- Bulk lots analysis (FifoLotEngine-based multi-analysis endpoint)
- Data quality (missing prices, stale prices, missing FX)
- Allocation history (time series by type/sector/geography)
"""

from datetime import date as date_type
from enum import StrEnum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.common import Currency, OpenDateRangeModel, SafeDecimal
from backend.app.schemas.wac import WACMissingPairInfo

# =============================================================================
# WAC ANALYTICS — Time series request/response
# =============================================================================


class WACAnalyticsQuery(BaseModel):
    """Single query for WAC time series."""

    model_config = ConfigDict(extra="forbid")

    broker_id: int = Field(..., description="Broker to compute WAC for")
    asset_id: int = Field(..., description="Asset to compute WAC for")
    date_range: Optional[OpenDateRangeModel] = Field(None, description="Date range filter. None = entire history.")


class WACAnalyticsRequest(BaseModel):
    """Request body for POST /portfolio/wac."""

    model_config = ConfigDict(extra="forbid")

    queries: List[WACAnalyticsQuery] = Field(..., min_length=1, max_length=20, description="WAC queries (max 20)")


class WACSeriesPoint(BaseModel):
    """Single point in WAC time series (where WAC changes)."""

    model_config = ConfigDict(extra="forbid")

    date: date_type
    wac: SafeDecimal = Field(..., description="WAC per unit after this transaction")
    pool_qty: SafeDecimal = Field(..., description="Pool quantity after this transaction")
    effect: str = Field(..., description="Effect on pool: add, reduce, add_zero_cost, add_at_wac")


class WACAnalyticsResultItem(BaseModel):
    """WAC series result for a single (broker, asset) query."""

    model_config = ConfigDict(extra="forbid")

    broker_id: int
    asset_id: int
    currency: str = Field(..., description="Target currency of WAC values")
    series: List[WACSeriesPoint] = Field(default_factory=list)
    missing_fx_pairs: List[WACMissingPairInfo] = Field(default_factory=list, description="FX pairs that could not be resolved, with dates")


class WACAnalyticsResponse(BaseModel):
    """Response for POST /portfolio/wac."""

    model_config = ConfigDict(extra="forbid")

    results: List[WACAnalyticsResultItem]


# =============================================================================
# PORTFOLIO — Summary, History
# =============================================================================


class PortfolioSummaryQuery(BaseModel):
    """Request body for POST /portfolio/summary."""

    model_config = ConfigDict(extra="forbid")

    broker_ids: Optional[List[int]] = Field(None, description="Optional broker filter")
    include_breakdown: bool = Field(False, description="Include per-broker breakdown in by_broker")
    target_currency: Optional[str] = Field(None, description="Override base currency (ISO 4217, e.g. USD)")


class PortfolioHistoryQuery(BaseModel):
    """Request body for POST /portfolio/history."""

    model_config = ConfigDict(extra="forbid")

    broker_ids: Optional[List[int]] = Field(None, description="Optional broker filter")
    date_range: Optional[OpenDateRangeModel] = Field(None, description="Inclusive date range. None = full history.")
    target_currency: Optional[str] = Field(None, description="Override base currency (ISO 4217, e.g. USD)")


class AllocationItem(BaseModel):
    """Single allocation slice (by type, sector, or geography)."""

    name: str = Field(..., description="Category name, e.g. 'ETF', 'Technology', 'US', 'Unknown'")
    value: SafeDecimal = Field(..., description="Percentage share (0-100)")
    amount: SafeDecimal = Field(..., description="Absolute value in base currency")
    emoji: Optional[str] = Field(None, description="Display emoji for the category (sector/type/geo)")


# =============================================================================
# DATA QUALITY — Missing prices, stale prices, quality report
# =============================================================================


class MissingPriceAsset(BaseModel):
    """Asset excluded from NAV because no PriceHistory was available."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    symbol: Optional[str] = None
    name: str
    broker_id: int
    broker_name: str
    first_position_date: Optional[date_type] = Field(None, description="Date of first qualifying transaction for this holding")
    quantity: SafeDecimal
    open_cost_basis: Optional[SafeDecimal] = Field(None, description="WAC × qty in base currency, None if FX missing")
    currency: str


class StalePriceAsset(BaseModel):
    """Asset whose latest price is older than the staleness threshold."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    name: str
    last_price_date: date_type
    stale_days: int


# =============================================================================
# DATA QUALITY ENUMS + ISSUE DTO
# =============================================================================


class IssueSeverity(StrEnum):
    """Severity levels for data quality issues."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueDomain(StrEnum):
    """Domain of a data quality issue."""

    PORTFOLIO = "portfolio"
    ASSET = "asset"
    FOREX = "forex"


class IssueCode(StrEnum):
    """Unique code identifying a data quality issue type.

    Only codes that are actively generated (backend engine or frontend page) are listed.
    Do not add future-proof codes — add them only when they are generated in the same step.
    """

    # Portfolio (generated by DerivedViewsBuilder.build_data_quality_report)
    MISSING_PRICE = "MISSING_PRICE"
    TRANSACTION_IMPLIED = "TRANSACTION_IMPLIED"
    STALE_PRICE = "STALE_PRICE"
    MISSING_FX_MARKET = "MISSING_FX_MARKET"
    NAV_INCOMPLETE = "NAV_INCOMPLETE"
    MWRR_NOT_CALCULABLE = "MWRR_NOT_CALCULABLE"
    MWRR_SERIES_UNRELIABLE = "MWRR_SERIES_UNRELIABLE"

    # Asset detail (constructed client-side in assets/[id]/+page.svelte)
    ASSET_ARCHIVED = "ASSET_ARCHIVED"
    RANGE_BEFORE_FIRST_DATA = "RANGE_BEFORE_FIRST_DATA"
    FX_PAIR_MISSING = "FX_PAIR_MISSING"
    FX_PAIR_NO_DATA = "FX_PAIR_NO_DATA"
    FX_PAIR_PARTIAL_GAP = "FX_PAIR_PARTIAL_GAP"

    # FIFO lots analysis (generated by FifoLotEngine / POST /portfolio/lots/analysis)
    REFERENCE_PRICE_FALLBACK = "REFERENCE_PRICE_FALLBACK"
    REFERENCE_PRICE_UNAVAILABLE = "REFERENCE_PRICE_UNAVAILABLE"
    SHORT_TRANSFER_NOT_SUPPORTED = "SHORT_TRANSFER_NOT_SUPPORTED"
    SHORT_ADJUSTMENT_NOT_SUPPORTED = "SHORT_ADJUSTMENT_NOT_SUPPORTED"
    FIFO_SOURCE_QUANTITY_MISSING = "FIFO_SOURCE_QUANTITY_MISSING"
    TRANSFER_PAIR_MISSING = "TRANSFER_PAIR_MISSING"


class DataQualityIssue(BaseModel):
    """A single data quality issue rendered in the UI as a banner item.

    Fields populated depend on the issue type:
    - Portfolio issues: affected_asset_ids/names (MISSING_PRICE, STALE_PRICE),
      affected_fx_pairs (MISSING_FX_MARKET), count + dates in message_params (NAV_INCOMPLETE).
    - Asset/FX issues: affected_fx_pairs (FX_PAIR_*), affected_asset_names (context).
    """

    model_config = ConfigDict(extra="forbid")

    domain: IssueDomain
    code: IssueCode
    severity: IssueSeverity
    message_i18n_key: str
    message_params: Dict[str, Any] = Field(default_factory=dict)
    count: Optional[int] = None
    affected_asset_ids: List[int] = Field(default_factory=list)
    affected_asset_names: List[str] = Field(default_factory=list)
    affected_fx_pairs: List[str] = Field(default_factory=list)
    cta_action: Optional[str] = None
    cta_target: Optional[str] = None
    group_key: Optional[str] = None


class DataQualityReport(BaseModel):
    """Aggregated data quality information for a portfolio calculation."""

    model_config = ConfigDict(extra="forbid")

    issues: List[DataQualityIssue] = Field(default_factory=list)
    missing_price_assets: List[MissingPriceAsset] = Field(default_factory=list)
    missing_fx_pairs: List[WACMissingPairInfo] = Field(default_factory=list)
    stale_prices: List[StalePriceAsset] = Field(default_factory=list)
    incomplete_nav_dates: List[date_type] = Field(default_factory=list)
    incomplete_book_value_dates: List[date_type] = Field(default_factory=list)
    incomplete_allocation_dates: List[date_type] = Field(default_factory=list)
    in_transit_cost_basis_warnings: List[str] = Field(default_factory=list)
    share_mismatch_warnings: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


# =============================================================================
# ALLOCATION HISTORY — Time series by dimension
# =============================================================================


class AllocationHistoryPoint(BaseModel):
    """Single point in the allocation history time series."""

    model_config = ConfigDict(extra="forbid")

    date: date_type
    components: List[AllocationItem]


class AllocationHistoryQuery(BaseModel):
    """Request body for POST /portfolio/allocation-history."""

    model_config = ConfigDict(extra="forbid")

    broker_ids: Optional[List[int]] = Field(None, description="Optional broker filter")
    date_range: Optional[OpenDateRangeModel] = Field(None, description="Date range filter. None = full history.")
    target_currency: Optional[str] = Field(None, description="Override base currency (ISO 4217)")
    dimension: str = Field("type", pattern="^(type|sector|geography)$", description="Allocation dimension")


class AllocationHistoryResponse(BaseModel):
    """Response for POST /portfolio/allocation-history."""

    model_config = ConfigDict(extra="forbid")

    dimension: str
    series: List[AllocationHistoryPoint]
    data_quality: Optional[DataQualityReport] = None


class PortfolioHolding(BaseModel):
    """Single open holding snapshot at report end date."""

    asset_id: int
    asset_name: str
    asset_ticker: Optional[str] = None
    asset_type: str
    broker_id: Optional[int] = Field(None, description="Broker that holds this position")
    broker_name: Optional[str] = Field(None, description="Broker display name")
    quantity: SafeDecimal
    wac_per_unit: Optional[SafeDecimal] = Field(None, description="None if FX rate missing")
    current_price: Optional[SafeDecimal] = Field(None, description="Snapshot price at report end date. None if FX rate missing")
    current_value: Optional[SafeDecimal] = Field(None, description="Snapshot position value at report end date")
    gain_loss: Optional[SafeDecimal] = Field(None, description="Unrealized P&L at report end date: current_value - cost_basis")
    gain_loss_percent: Optional[SafeDecimal] = None
    price_change_1d: Optional[SafeDecimal] = Field(None, description="Percentage price change vs previous day relative to report end date")
    gain_loss_change_1d: Optional[SafeDecimal] = Field(None, description="Change in unrealized P&L vs previous day using current quantity and base-currency prices")
    gain_loss_change_1d_percent: Optional[SafeDecimal] = Field(None, description="gain_loss_change_1d as percentage of previous day's unrealized P&L; None if prior unrealized P&L is ~0")
    allocation_percent: Optional[SafeDecimal] = Field(None, description="Weight vs total market value (excludes cash)")
    nav_weight_percent: Optional[SafeDecimal] = Field(None, description="Weight vs NAV at report end date (includes cash): current_value / NAV * 100")


class AssetPeriodContribution(BaseModel):
    """Per-asset period P&L contribution for dashboard Performance view."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    asset_name: str
    asset_ticker: Optional[str] = None
    asset_type: str
    broker_id: int
    broker_name: str
    period_unrealized_delta: Optional[SafeDecimal] = Field(None, description="Change in unrealized P&L over the period")
    period_realized_gain_loss: Optional[SafeDecimal] = Field(None, description="Realized gain/loss from SELLs in period")
    period_income: Optional[SafeDecimal] = Field(None, description="DIVIDEND/INTEREST attributed to this asset in period")
    period_fees_taxes: Optional[SafeDecimal] = Field(None, description="FEE/TAX attributed to this asset in period (positive value)")
    period_pnl: Optional[SafeDecimal] = Field(None, description="Total period P&L: unrealized_delta + realized + income - fees_taxes")
    period_pnl_percent: Optional[SafeDecimal] = Field(None, description="Period return %: period_pnl / |start_value|. None if start_value=0")
    start_value: Optional[SafeDecimal] = Field(None, description="Position value at period start (0 if there was no opening position)")
    end_value: Optional[SafeDecimal] = Field(None, description="Position value at period end (0 if the position was closed by period end)")
    is_fully_sold: bool = Field(False, description="True if position quantity is 0 at period end")


class UnallocatedContribution(BaseModel):
    """Broker-level fees/income not attributed to a specific asset."""

    model_config = ConfigDict(extra="forbid")

    broker_id: int
    broker_name: str
    unallocated_income: Optional[SafeDecimal] = Field(None, description="DIVIDEND/INTEREST without asset_id in period")
    unallocated_fees_taxes: Optional[SafeDecimal] = Field(None, description="FEE/TAX without asset_id in period (positive value)")


class OtherPeriodEffect(BaseModel):
    """Period P&L row not linked to a specific asset position."""

    model_config = ConfigDict(extra="forbid")

    description: str
    category: str = Field(..., pattern="^(Income|Cost|Other)$")
    period_pnl: SafeDecimal
    broker_id: Optional[int] = Field(None, description="Nullable when effect is not broker-specific")
    broker_name: Optional[str] = Field(None, description="Nullable when effect is not broker-specific")


class PositionsContribution(BaseModel):
    """Complete per-asset contribution breakdown for a period."""

    model_config = ConfigDict(extra="forbid")

    positions: List[AssetPeriodContribution] = Field(default_factory=list)
    unallocated: List[UnallocatedContribution] = Field(default_factory=list)
    other_effects: List[OtherPeriodEffect] = Field(default_factory=list, description="Non-position period effects for income, costs, and reconciliation residuals")
    gross_gains: SafeDecimal = Field(default=0, description="Sum of max(period_pnl, 0) across all positions")
    gross_losses: SafeDecimal = Field(default=0, description="Sum of |min(period_pnl, 0)| across all positions")


class BrokerBreakdown(BaseModel):
    """Per-broker mini-summary (only populated when include_breakdown=True)."""

    model_config = ConfigDict(extra="forbid")

    broker_id: int
    broker_name: str
    net_worth: Currency
    gain_loss: Currency
    gain_loss_percent: SafeDecimal
    cash_total: Currency
    cash_balances: List[Currency] = Field(default_factory=list, description="Cash balance per currency, native (unconverted)")


class PortfolioSummary(BaseModel):
    """Full portfolio summary response."""

    net_worth: Currency
    total_invested: Currency
    total_gain_loss: Currency
    total_gain_loss_percent: SafeDecimal
    cash_total: Currency
    cash_balances: List[Currency] = Field(default_factory=list)
    market_value: Optional[Currency] = Field(None, description="Total mark-to-market value of held assets")
    broker_nav_value: Optional[Currency] = Field(None, description="market_value + cash_value (before in-transit)")
    in_transit_market_value: Optional[Currency] = Field(None, description="Market value of assets/cash in transit")
    open_cost_basis: Optional[Currency] = Field(None, description="WAC × quantity for all held assets")
    in_transit_book_value: Optional[Currency] = Field(None, description="Cost basis of assets/cash in transit")
    book_value: Optional[Currency] = Field(None, description="open_cost_basis + cash + in_transit_book_value")
    unrealized_gain_loss: Optional[Currency] = Field(None, description="nav_value - book_value")
    total_deposited: Optional[Currency] = Field(None, description="Sum of all DEPOSIT amounts (positive) in target currency")
    total_withdrawn: Optional[Currency] = Field(None, description="Sum of all WITHDRAWAL amounts (positive) in target currency")
    net_deposited_capital: Optional[Currency] = Field(None, description="total_deposited - total_withdrawn")
    period_nav_start: Optional[Currency] = Field(None, description="NAV at start of selected period")
    period_market_value_start: Optional[Currency] = Field(None, description="Market value of held assets at start of selected period")
    period_book_value_start: Optional[Currency] = Field(None, description="Book value at start of selected period")
    period_net_flows: Optional[Currency] = Field(None, description="Sum of external cash flows in selected period")
    period_pnl: Optional[Currency] = Field(None, description="Period P&L = nav_end - nav_start - net_flows")
    period_unrealized_gain_loss_start: Optional[Currency] = Field(None, description="Unrealized G/L at start of period")
    period_unrealized_gain_loss_end: Optional[Currency] = Field(None, description="Unrealized G/L at end of period (snapshot)")
    period_unrealized_gain_loss_delta: Optional[Currency] = Field(None, description="Change in unrealized G/L over the period")
    period_realized_gain_loss: Optional[Currency] = Field(None, description="Realized G/L from sales in period (WAC-based)")
    period_income: Optional[Currency] = Field(None, description="DIVIDEND + INTEREST in period (positive)")
    period_fees_taxes: Optional[Currency] = Field(None, description="FEE + TAX in period (positive value, shown negative in UI)")
    period_fees: Optional[Currency] = Field(None, description="FEE only in period (commissions)")
    period_taxes: Optional[Currency] = Field(None, description="TAX only in period")
    period_other_result: Optional[Currency] = Field(None, description="pnl - unrealized_delta - realized - income + fees_taxes")
    twrr_percent: Optional[SafeDecimal] = Field(None, description="Time-Weighted Return (None if not calculable)")
    mwrr_annualized_percent: Optional[SafeDecimal] = Field(None, description="Annualized MWRR / XIRR (None if not converged)")
    mwrr_cumulative_percent: Optional[SafeDecimal] = Field(None, description="Cumulative MWRR for the period: (1+r_ann)^(days/365)-1")
    mwrr_period_days: Optional[int] = Field(None, description="Number of days in the MWRR calculation period")
    simple_roi_percent: SafeDecimal
    allocation_by_type: List[AllocationItem] = Field(default_factory=list)
    allocation_by_sector: List[AllocationItem] = Field(default_factory=list)
    allocation_by_geography: List[AllocationItem] = Field(default_factory=list)
    holdings: List[PortfolioHolding] = Field(default_factory=list)
    by_broker: Optional[List[BrokerBreakdown]] = Field(None, description="Only populated when include_breakdown=True")
    missing_fx_pairs: List[WACMissingPairInfo] = Field(
        default_factory=list,
        description="FX pairs with missing rates (aggregated by range for compact payload)",
    )
    missing_price_assets: List[MissingPriceAsset] = Field(
        default_factory=list,
        description="Assets excluded from NAV because no PriceHistory was available",
    )
    data_quality: Optional[DataQualityReport] = Field(None, description="Aggregated data quality report")


class PortfolioHistoryPoint(BaseModel):
    """Single point in the portfolio value time series."""

    date: date_type
    cash_value: Currency
    market_value: Currency = Field(..., description="Total mark-to-market value of held assets")
    broker_nav_value: Optional[Currency] = Field(None, description="market_value + cash_value (before in-transit)")
    in_transit_cash_value: Optional[Currency] = Field(None, description="Cash in transit between brokers")
    in_transit_asset_market_value: Optional[Currency] = Field(None, description="Market value of assets in transit")
    in_transit_market_value: Optional[Currency] = Field(None, description="Total in-transit market value")
    nav_value: Currency
    open_cost_basis: Optional[Currency] = Field(None, description="WAC × quantity for all held assets")
    in_transit_asset_cost_basis: Optional[Currency] = Field(None, description="Cost basis of assets in transit")
    in_transit_book_value: Optional[Currency] = Field(None, description="Cost basis of all in-transit items")
    book_value: Optional[Currency] = Field(None, description="open_cost_basis + cash + in_transit_book_value")
    capital_baseline: Currency = Field(..., description="Net external capital contributed to scope (deposits − withdrawals + linked-external flows)")
    book_asset_like: Currency = Field(..., description="open_cost_basis + in_transit_asset_cost_basis (asset-like book value)")
    cash_from_contributed_capital: Currency = Field(..., description="Portion of cash attributable to undeployed external capital")
    cash_from_generated_returns: Currency = Field(..., description="Portion of cash from returns (interest, dividends, realized gains)")
    total_pnl: Currency = Field(..., description="NAV - Capital Baseline (total P&L vs external capital)")
    unrealized_gain_loss: Optional[Currency] = Field(None, description="nav_value - book_value")
    twrr: Optional[SafeDecimal] = Field(None, description="Time-Weighted Return series point")
    mwrr_annualized: Optional[SafeDecimal] = Field(None, description="Annualized MWRR at this point")
    mwrr_cumulative: Optional[SafeDecimal] = Field(None, description="Cumulative MWRR at this point: (1+r_ann)^(days/365)-1")
    roi: Optional[SafeDecimal] = Field(None, description="Simple ROI series point")


# =============================================================================
# LOTS ANALYSIS — Bulk FifoLotEngine contract
# =============================================================================

LotDirection = Literal["LONG", "SHORT"]
LotCustodyType = Literal["BROKER", "IN_TRANSIT"]
ReferencePriceSource = Literal["exact", "fallback", "unavailable"]
LotCalculationStatus = Literal["COMPLETE", "DEGRADED", "UNAVAILABLE"]


class LotAnalysisType(StrEnum):
    """Selectable sections for POST /portfolio/lots/analysis."""

    LOT_SUMMARY = "LOT_SUMMARY"
    GANTT_TOPOLOGY = "GANTT_TOPOLOGY"
    CUSTODY_HISTORY = "CUSTODY_HISTORY"
    EVENT_HISTORY = "EVENT_HISTORY"
    VALUE_HISTORY = "VALUE_HISTORY"
    RETURN_HISTORY = "RETURN_HISTORY"
    PRICE_HISTORY = "PRICE_HISTORY"
    BROKER_WAC_HISTORY = "BROKER_WAC_HISTORY"
    CUMULATIVE_WAC_HISTORY = "CUMULATIVE_WAC_HISTORY"


class LotsAnalysisQuery(BaseModel):
    """Request body for POST /portfolio/lots/analysis."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., description="Asset to analyze.")
    broker_ids: Optional[List[int]] = Field(None, description="Optional broker filter. None = all accessible brokers.")
    date_range: Optional[OpenDateRangeModel] = Field(None, description="Optional date range filter for histories and visible intervals.")
    target_currency: Optional[str] = Field(None, description="Override base currency (ISO 4217 or supported crypto).")
    selected_lot_ids: Optional[List[int]] = Field(None, description="Optional subset of lot_ids to project in lot-scoped analyses.")
    requested_analyses: List[LotAnalysisType] = Field(..., description="Non-empty list of analyses to compute.")

    @field_validator("target_currency")
    @classmethod
    def validate_target_currency(cls, v: Optional[str]) -> Optional[str]:
        return Currency.validate_code(v) if v else None

    @field_validator("requested_analyses")
    @classmethod
    def validate_requested_analyses(cls, v: List[LotAnalysisType]) -> List[LotAnalysisType]:
        if not v:
            raise ValueError("requested_analyses must contain at least one analysis type")
        deduped = list(dict.fromkeys(v))
        if len(deduped) != len(v):
            raise ValueError("requested_analyses must not contain duplicates")
        return v


class LotCustodySummarySchema(BaseModel):
    """Current custody slice for a lot."""

    model_config = ConfigDict(extra="forbid")

    broker_id: Optional[int] = Field(None, description="Broker currently holding this fragment. None for in-transit slices.")
    custody_type: LotCustodyType
    quantity: SafeDecimal


class LotSummarySchema(BaseModel):
    """Direction-neutral lot row used by table, selection sync, and custody modal."""

    model_config = ConfigDict(extra="forbid")

    lot_id: int = Field(..., description="Stable lot identifier. Equals opening_transaction_id.")
    opening_transaction_id: int = Field(..., description="Transaction that opened the lot. Equals lot_id.")
    asset_id: int
    direction: LotDirection
    opening_broker_id: int
    opening_date: date_type
    opening_unit_price: SafeDecimal = Field(..., description="Opening unit price converted to response target_currency.")
    original_quantity: SafeDecimal
    original_cost: SafeDecimal = Field(..., description="Original lot cost in response target_currency.")
    currency: Optional[str] = Field(None, description="Original transaction currency preserved from FifoLot.currency.")
    open_quantity: SafeDecimal
    realized_quantity: SafeDecimal
    realized_pnl: SafeDecimal = Field(..., description="Realized FIFO P&L in response target_currency.")
    cumulative_proceeds: SafeDecimal = Field(..., description="Cumulative proceeds in response target_currency.")
    reference_unit_price: Optional[SafeDecimal] = Field(None, description="Reference unit price used for relative return, in target_currency.")
    reference_price_source: Optional[ReferencePriceSource] = None
    states: List[str] = Field(default_factory=list, description="Combinable derived state tags from FifoEngineResult.get_lot_states().")
    current_custody: List[LotCustodySummarySchema] = Field(default_factory=list, description="Active custody slices for unified table and modal summary.")
    open_value: Optional[SafeDecimal] = Field(None, description="Current open mark-to-market value in response target_currency.")
    total_value: Optional[SafeDecimal] = Field(None, description="Current total lot value (open_value + realized cash logic) in response target_currency.")
    pnl: Optional[SafeDecimal] = Field(None, description="Current total lot P&L in response target_currency.")
    relative_return: Optional[SafeDecimal] = Field(None, description="Relative return vs reference_unit_price, when computable.")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        return Currency.validate_code(v) if v else None


class GanttSegmentSchema(BaseModel):
    """Serializable projection of one FragmentInterval."""

    model_config = ConfigDict(extra="forbid")

    fragment_id: str
    lot_id: int
    direction: LotDirection
    custody_type: LotCustodyType
    broker_id: Optional[int] = None
    source_broker_id: Optional[int] = None
    destination_broker_id: Optional[int] = None
    quantity: SafeDecimal
    unit_price: SafeDecimal = Field(..., description="Fragment unit price converted to response target_currency.")
    start_date: date_type
    end_date: Optional[date_type] = Field(None, description="None when fragment is still active.")


class LotTimelineEventKind(StrEnum):
    """Presentation-level lot chronology events derived from engine events/closures."""

    BUY = "BUY"
    SELL = "SELL"
    ADJUSTMENT_IN = "ADJUSTMENT_IN"
    ADJUSTMENT_OUT = "ADJUSTMENT_OUT"
    SPLIT = "SPLIT"
    TRANSFER_DEPART = "TRANSFER_DEPART"
    TRANSFER_ARRIVE = "TRANSFER_ARRIVE"


class LotTimelineEventSchema(BaseModel):
    """Flat lot timeline row.

    Shared by both custody_history and lot_events. Flat list + lot_id keeps response
    shape consistent with existing point-based history DTOs and simplifies multi-select UI.
    """

    model_config = ConfigDict(extra="forbid")

    lot_id: int
    date: date_type
    kind: LotTimelineEventKind
    transaction_id: int
    related_transaction_id: Optional[int] = Field(None, description="Paired transaction id for transfer events, when available.")
    broker_id: Optional[int] = Field(None, description="Broker directly associated with this event, when singular.")
    source_broker_id: Optional[int] = None
    destination_broker_id: Optional[int] = None
    fragment_id: Optional[str] = Field(None, description="Affected custody fragment, when event is fragment-specific.")
    quantity: SafeDecimal
    unit_price: Optional[SafeDecimal] = Field(None, description="Event unit price in response target_currency.")
    open_unit_price: Optional[SafeDecimal] = Field(None, description="Opening unit price for closure rows, in target_currency.")
    close_unit_price: Optional[SafeDecimal] = Field(None, description="Closing unit price for closure rows, in target_currency.")
    realized_pnl: Optional[SafeDecimal] = Field(None, description="Closure realized P&L in target_currency.")
    proceeds: Optional[SafeDecimal] = Field(None, description="Closure proceeds in target_currency.")
    ratio: Optional[SafeDecimal] = Field(None, description="Split ratio for SPLIT events.")


class LotValueHistoryPoint(BaseModel):
    """Per-lot value history point."""

    model_config = ConfigDict(extra="forbid")

    lot_id: int
    date: date_type
    open_value: SafeDecimal
    proceeds: SafeDecimal
    total_value: SafeDecimal
    original_cost: SafeDecimal
    pnl: SafeDecimal


class LotReturnHistoryPoint(BaseModel):
    """Per-lot relative return point."""

    model_config = ConfigDict(extra="forbid")

    lot_id: int
    date: date_type
    relative_return: Optional[SafeDecimal] = Field(None, description="None when reference price is unavailable or zero.")
    reference_price_source: Optional[ReferencePriceSource] = Field(None, description="Reference price resolution echoed for chart/tooltips.")


class LotPriceHistoryPoint(BaseModel):
    """Per-lot market price point."""

    model_config = ConfigDict(extra="forbid")

    lot_id: int
    date: date_type
    market_price: SafeDecimal
    currency: str = Field(..., description="Currency of market_price, normally equal to response target_currency.")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return Currency.validate_code(v)


class BrokerWACHistoryPoint(BaseModel):
    """Broker-scoped WAC time-series point for selected asset."""

    model_config = ConfigDict(extra="forbid")

    date: date_type
    broker_id: int
    wac: SafeDecimal
    pool_qty: SafeDecimal


class CumulativeWACHistoryPoint(BaseModel):
    """Combined WAC time-series point across requested brokers."""

    model_config = ConfigDict(extra="forbid")

    date: date_type
    wac: SafeDecimal
    pool_qty: SafeDecimal


class LotsAnalysisMetadata(BaseModel):
    """Metadata describing bulk lots-analysis computation."""

    model_config = ConfigDict(extra="forbid")

    broker_ids: Optional[List[int]] = None
    selected_lot_ids: Optional[List[int]] = None
    requested_analyses: List[LotAnalysisType]
    requested_date_from: Optional[date_type] = None
    requested_date_to: Optional[date_type] = None
    computed_date_from: Optional[date_type] = None
    computed_date_to: Optional[date_type] = None
    generated_at: date_type


class LotsAnalysisResponse(BaseModel):
    """Response for POST /portfolio/lots/analysis.

    Sections are None unless explicitly requested via requested_analyses.
    """

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    target_currency: str
    calculation_status: LotCalculationStatus
    calculation_metadata: LotsAnalysisMetadata
    data_quality: Optional[DataQualityReport] = None
    lots: Optional[List[LotSummarySchema]] = Field(None, description="LOT_SUMMARY payload.")
    gantt_segments: Optional[List[GanttSegmentSchema]] = Field(None, description="GANTT_TOPOLOGY payload.")
    custody_history: Optional[List[LotTimelineEventSchema]] = Field(None, description="CUSTODY_HISTORY payload.")
    lot_events: Optional[List[LotTimelineEventSchema]] = Field(None, description="EVENT_HISTORY payload.")
    value_history: Optional[List[LotValueHistoryPoint]] = Field(None, description="Flat per-lot VALUE_HISTORY points.")
    return_history: Optional[List[LotReturnHistoryPoint]] = Field(None, description="Flat per-lot RETURN_HISTORY points.")
    price_history: Optional[List[LotPriceHistoryPoint]] = Field(None, description="Flat per-lot PRICE_HISTORY points.")
    broker_wac_history: Optional[List[BrokerWACHistoryPoint]] = Field(None, description="BROKER_WAC_HISTORY payload.")
    cumulative_wac_history: Optional[List[CumulativeWACHistoryPoint]] = Field(None, description="CUMULATIVE_WAC_HISTORY payload.")

    @field_validator("target_currency")
    @classmethod
    def validate_target_currency(cls, v: str) -> str:
        return Currency.validate_code(v)


# =============================================================================
# PORTFOLIO REPORT — Unified single-engine-run endpoint
# =============================================================================


class AllocationHistoryDimensions(BaseModel):
    """Allocation history for all three dimensions."""

    model_config = ConfigDict(extra="forbid")

    type: List[AllocationHistoryPoint] = Field(default_factory=list)
    sector: List[AllocationHistoryPoint] = Field(default_factory=list)
    geography: List[AllocationHistoryPoint] = Field(default_factory=list)


class PortfolioReportMetadata(BaseModel):
    """Metadata describing the report computation parameters."""

    model_config = ConfigDict(extra="forbid")

    broker_ids: Optional[List[int]] = None
    target_currency: str
    requested_date_from: Optional[date_type] = None
    requested_date_to: Optional[date_type] = None
    computed_date_from: Optional[date_type] = None
    computed_date_to: Optional[date_type] = None
    generated_at: date_type
    allocation_dimensions: List[str] = Field(default_factory=lambda: ["type", "sector", "geography"])
    included_features: List[str] = Field(default_factory=list)


class PortfolioReportQuery(BaseModel):
    """Request body for POST /portfolio/report.

    Runs the PortfolioCalculationEngine once and returns all requested views.
    """

    model_config = ConfigDict(extra="forbid")

    broker_ids: Optional[List[int]] = Field(None, description="Broker filter. None = all accessible brokers.")
    date_range: Optional[OpenDateRangeModel] = Field(None, description="Date range for history. None = full history.")
    target_currency: Optional[str] = Field(None, description="Override base currency (ISO 4217).")
    include_summary: bool = Field(True, description="Include portfolio summary (KPIs, holdings, allocations).")
    include_history: bool = Field(True, description="Include daily history time series.")
    include_allocation_history: bool = Field(True, description="Include allocation history by all dimensions.")
    include_breakdown: bool = Field(False, description="Include per-broker breakdown in summary.")
    include_positions_contribution: bool = Field(False, description="Include per-asset period P&L contribution.")


class PortfolioReportResponse(BaseModel):
    """Response for POST /portfolio/report.

    Contains all requested views derived from a single engine run.
    Sections are None when the corresponding include_* flag was False.
    """

    model_config = ConfigDict(extra="forbid")

    metadata: PortfolioReportMetadata
    summary: Optional[PortfolioSummary] = None
    history: Optional[List[PortfolioHistoryPoint]] = None
    allocation_history: Optional[AllocationHistoryDimensions] = None
    data_quality: Optional[DataQualityReport] = None
    positions_contribution: Optional[PositionsContribution] = Field(None, description="Per-asset period P&L contribution. Only when include_positions_contribution=True.")
