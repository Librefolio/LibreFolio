"""
Portfolio schemas for LibreFolio.

Schemas for the /api/v1/portfolio/ endpoints:
- WAC time series (point-per-transaction where WAC changes)
- Portfolio summary (net worth, ROI, allocations, holdings)
- Portfolio history (daily cash/market_value/nav series)
- Asset history (WAC vs market price series)
- FIFO lots (open and closed lot details)
- Data quality (missing prices, stale prices, missing FX)
- Allocation history (time series by type/sector/geography)
"""

from datetime import date as date_type
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

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
# PORTFOLIO — Summary, History, Asset History, FIFO Lots
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


class DataQualityReport(BaseModel):
    """Aggregated data quality information for a portfolio calculation."""

    model_config = ConfigDict(extra="forbid")

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
    """Single asset holding in the portfolio."""

    asset_id: int
    asset_name: str
    asset_ticker: Optional[str] = None
    asset_type: str
    quantity: SafeDecimal
    wac_per_unit: Optional[SafeDecimal] = Field(None, description="None if FX rate missing")
    current_price: Optional[SafeDecimal] = Field(None, description="None if FX rate missing")
    current_value: Optional[SafeDecimal] = None
    gain_loss: Optional[SafeDecimal] = None
    gain_loss_percent: Optional[SafeDecimal] = None
    allocation_percent: Optional[SafeDecimal] = None


class BrokerBreakdown(BaseModel):
    """Per-broker mini-summary (only populated when include_breakdown=True)."""

    broker_id: int
    broker_name: str
    net_worth: Currency
    gain_loss: Currency
    gain_loss_percent: SafeDecimal
    cash_total: Currency


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
    twrr_percent: Optional[SafeDecimal] = Field(None, description="Time-Weighted Return (None if not calculable)")
    mwrr_percent: Optional[SafeDecimal] = Field(None, description="Money-Weighted Return / XIRR (None if not converged)")
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
    unrealized_gain_loss: Optional[Currency] = Field(None, description="nav_value - book_value")
    twrr: Optional[SafeDecimal] = Field(None, description="Time-Weighted Return series point")
    mwrr: Optional[SafeDecimal] = Field(None, description="Money-Weighted Return series point")
    roi: Optional[SafeDecimal] = Field(None, description="Simple ROI series point")


class AssetHistoryPoint(BaseModel):
    """Single point in the WAC vs market price time series for an asset."""

    date: date_type
    wac: SafeDecimal
    market_price: SafeDecimal
    twrr: Optional[SafeDecimal] = Field(None, description="Time-Weighted Return series point")
    mwrr: Optional[SafeDecimal] = Field(None, description="Money-Weighted Return series point")
    roi: Optional[SafeDecimal] = Field(None, description="Simple ROI series point")


class OpenLotSchema(BaseModel):
    """Serializable representation of an open FIFO lot."""

    buy_transaction_id: int
    buy_date: date_type
    buy_price: SafeDecimal
    original_quantity: SafeDecimal
    remaining_quantity: SafeDecimal
    unrealized_pnl: Optional[SafeDecimal] = Field(None, description="Unrealized P&L at current market price")


class ClosedLotSchema(BaseModel):
    """Serializable representation of a closed FIFO lot."""

    buy_transaction_id: int
    sell_transaction_id: int
    buy_date: date_type
    sell_date: date_type
    buy_price: SafeDecimal
    sell_price: SafeDecimal
    quantity: SafeDecimal
    realized_pnl: SafeDecimal


class FIFOLotsResponse(BaseModel):
    """FIFO lots response for a specific (broker, asset) pair."""

    open_lots: List[OpenLotSchema] = Field(default_factory=list)
    closed_lots: List[ClosedLotSchema] = Field(default_factory=list)
    total_realized_pnl: SafeDecimal
    total_unrealized_quantity: SafeDecimal
