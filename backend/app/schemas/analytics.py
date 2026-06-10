"""
Analytics schemas for LibreFolio.

Schemas for the /api/v1/analytics/ endpoints:
- WAC time series (point-per-transaction where WAC changes)

Schemas for the /api/v1/portfolio/ endpoints:
- Portfolio summary (net worth, ROI, allocations, holdings)
- Portfolio history (daily cash/invested/nav series)
- Asset history (WAC vs market price series)
- FIFO lots (open and closed lot details)
"""

from __future__ import annotations

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
    date_range: Optional[OpenDateRangeModel] = Field(
        None, description="Date range filter. None = entire history."
    )


class WACAnalyticsRequest(BaseModel):
    """Request body for POST /analytics/wac."""

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
    missing_pairs: List["WACMissingPairInfo"] = Field(default_factory=list, description="FX pairs that could not be resolved, with dates")


class WACAnalyticsResponse(BaseModel):
    """Response for POST /analytics/wac."""

    model_config = ConfigDict(extra="forbid")

    results: List[WACAnalyticsResultItem]


# =============================================================================
# PORTFOLIO — Summary, History, Asset History, FIFO Lots
# =============================================================================


class AllocationItem(BaseModel):
    """Single allocation slice (by type, sector, or geography)."""

    name: str = Field(..., description="Category name, e.g. 'ETF', 'Technology', 'US', 'Unknown'")
    value: SafeDecimal = Field(..., description="Percentage share (0-100)")
    amount: SafeDecimal = Field(..., description="Absolute value in base currency")


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
    net_worth: SafeDecimal
    gain_loss: SafeDecimal
    gain_loss_percent: SafeDecimal
    cash_total: SafeDecimal


class PortfolioSummary(BaseModel):
    """Full portfolio summary response."""

    net_worth: SafeDecimal
    total_invested: SafeDecimal
    total_gain_loss: SafeDecimal
    total_gain_loss_percent: SafeDecimal
    cash_total: SafeDecimal
    cash_balances: List[Currency] = Field(default_factory=list)
    twrr_percent: Optional[SafeDecimal] = Field(None, description="Time-Weighted Return (None if not calculable)")
    mwrr_percent: Optional[SafeDecimal] = Field(None, description="Money-Weighted Return / XIRR (None if not converged)")
    simple_roi_percent: SafeDecimal
    allocation_by_type: List[AllocationItem] = Field(default_factory=list)
    allocation_by_sector: List[AllocationItem] = Field(default_factory=list)
    allocation_by_geography: List[AllocationItem] = Field(default_factory=list)
    holdings: List[PortfolioHolding] = Field(default_factory=list)
    by_broker: Optional[List[BrokerBreakdown]] = Field(None, description="Only populated when include_breakdown=True")
    wac_missing_pairs: List[WACMissingPairInfo] = Field(
        default_factory=list,
        description="FX pairs with missing rates (aggregated by range for compact payload)",
    )


class PortfolioHistoryPoint(BaseModel):
    """Single point in the portfolio value time series."""

    date: date_type
    cash_value: SafeDecimal
    invested_value: SafeDecimal
    nav_value: SafeDecimal
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

