"""Portfolio summary: allocation items, holdings, the contribution of each position, the brokers and the summary that holds them."""

from __future__ import annotations

from datetime import date as date_type
from enum import StrEnum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from backend.app.schemas.common import Currency, SafeDecimal, StepSpan, StrictModel
from backend.app.schemas.portfolio.data_quality import DataQualityReport, MissingPriceAsset
from backend.app.schemas.portfolio.yield_on_cost import YieldOnCostResult
from backend.app.schemas.wac import WACMissingPairInfo


class AllocationItem(StrictModel):
    """Single allocation slice (by type, sector, geography, or asset)."""

    name: str = Field(..., description="Category name, e.g. 'ETF', 'Technology', 'US', 'Unknown'")
    value: Optional[SafeDecimal] = Field(
        ...,
        description="Percentage share of the total, rounded to 0.01: amount / sum of all slices × 100. The shares add up to 100; with negative cash the cash slice is below zero and the others can exceed 100. None for every slice when the sum of the slices is zero or negative (no meaningful share); the amounts stay.",
    )
    amount: SafeDecimal = Field(..., description="Absolute value in base currency")
    emoji: Optional[str] = Field(None, description="Display emoji for the category (sector/type/geo)")
    id: Optional[int] = Field(None, description="Asset id of a slice of the asset dimension (the colour key); None for its Liquidity slice and in the other dimensions")


class AssetAllocationItem(AllocationItem):
    """A slice of the asset dimension: the allocation item, plus what the pie needs to draw the asset's icon."""

    asset_type: Optional[str] = Field(None, description="Type of the asset (its icon when it has no icon of its own); None for the Liquidity slice")
    icon_url: Optional[str] = Field(None, description="The asset's own icon; None when it has none and for the Liquidity slice")


class AllocationHistoryPoint(StepSpan):
    """One step of the allocation history (D-P4): the components hold from ``date`` to ``through``."""

    components: List[AllocationItem]


class PortfolioHolding(StrictModel):
    """Single open holding snapshot at report end date."""

    asset_id: int
    asset_name: str
    asset_ticker: Optional[str] = None
    asset_type: str
    broker_id: Optional[int] = Field(None, description="Broker that holds this position")
    broker_name: Optional[str] = Field(None, description="Broker display name")
    quantity: SafeDecimal
    wac_per_unit: Optional[SafeDecimal] = Field(None, description="None if FX rate missing")
    current_price: Optional[SafeDecimal] = Field(None, description="Effective current-unit price converted to report currency. None if FX rate missing")
    current_value: Optional[SafeDecimal] = Field(None, description="Snapshot position value at report end date")
    valuation_source: Optional[Literal["MARKET_PRICE", "LAST_TRADE_PRICE", "ESTIMATED_AT_COST", "MISSING"]] = Field(
        None,
        description="Source selected by the valuation hierarchy: MARKET_PRICE (a market quote), LAST_TRADE_PRICE (the last BUY or SELL price), ESTIMATED_AT_COST (no price at all: the book cost, an estimate, with no current_price), MISSING (no price and no known cost: not valued)",
    )
    valuation_effective_unit_price: Optional[SafeDecimal] = Field(None, description="Native-currency unit price actually used for current_value")
    valuation_effective_currency: Optional[str] = Field(None, description="Native currency of valuation_effective_unit_price")
    valuation_reference_date: Optional[date_type] = Field(None, description="Original date of the selected market or transaction reference")
    valuation_reference_unit_price: Optional[SafeDecimal] = Field(None, description="Original source unit price before split adjustment or target-currency conversion")
    valuation_reference_currency: Optional[str] = Field(None, description="Native currency of valuation_reference_unit_price")
    valuation_split_adjusted: bool = Field(False, description="Whether intervening split events restated the transaction reference for current units")
    missing_fx_pair: Optional[str] = Field(None, description="Required source/target FX pair when valuation conversion is unavailable")
    gain_loss: Optional[SafeDecimal] = Field(None, description="Unrealized P&L at report end date: current_value - cost_basis")
    gain_loss_percent: Optional[SafeDecimal] = None
    annualized_return: Optional[SafeDecimal] = Field(
        None, description="Net annualized return (CAGR) of the still-open position over first-transaction -> report-end window: (1 + (unrealized + income - fees)/cost_basis)^(365/days)-1. Value-at-cost when market price missing (income-only). Fraction. None if <30 days / no cost basis."
    )
    price_change_1d: Optional[SafeDecimal] = Field(None, description="Percentage price change vs previous day relative to report end date")
    gain_loss_change_1d: Optional[SafeDecimal] = Field(None, description="Change in unrealized P&L vs previous day using current quantity and base-currency prices")
    gain_loss_change_1d_percent: Optional[SafeDecimal] = Field(None, description="Daily unrealized P&L change as percentage of the previous day's absolute position market value; None if prior value is ~0")
    allocation_percent: Optional[SafeDecimal] = Field(None, description="Weight vs total market value of the holdings (excludes cash), rounded to 0.01; None when the holding has no value or that total is zero or negative")
    nav_weight_percent: Optional[SafeDecimal] = Field(None, description="Weight vs NAV at report end date (includes cash): current_value / NAV * 100, rounded to 0.01; None when the holding has no value or the NAV is zero or negative")
    oldest_open_lot_date: Optional[date_type] = Field(None, description="Opening date of the oldest FIFO lot still open at report end for this (asset, broker); None if fully closed")
    yield_on_cost: YieldOnCostResult = Field(
        description="Trailing-365-day gross recorded income per eligible unit divided by residual unit WAC.",
    )


class AssetPeriodContribution(BaseModel):
    """Per-asset period P&L contribution for dashboard Performance view."""

    asset_id: int
    asset_name: str
    asset_ticker: Optional[str] = None
    asset_type: str
    broker_id: int
    broker_name: str
    period_unrealized_delta: Optional[SafeDecimal] = Field(
        None,
        description="Change in unrealized P&L over the period, from the portfolio's own valuation at the two boundaries; an internal transfer that leaves and arrives inside the period splits it between the two brokers at the value on arrival (P22). None when a boundary the position is held at has an unknown unrealized (no rate, incomplete cost)",
    )
    period_realized_gain_loss: Optional[SafeDecimal] = Field(None, description="Realized gain/loss in period: SELLs, and outgoing ADJUSTMENTs with a cost basis (the value handed over, at the rate of its date, against the average cost)")
    period_income: Optional[SafeDecimal] = Field(None, description="DIVIDEND/INTEREST attributed to this asset in period")
    period_fees_taxes: Optional[SafeDecimal] = Field(None, description="FEE/TAX attributed to this asset in period (positive value)")
    period_pnl: Optional[SafeDecimal] = Field(None, description="Total period P&L: unrealized_delta + realized + income - fees_taxes")
    period_pnl_percent: Optional[SafeDecimal] = Field(None, description="Period return %: period_pnl / |start_value|. None if start_value=0")
    period_unrealized_delta_percent: Optional[SafeDecimal] = Field(None, description="period_unrealized_delta / |start_value|, a fraction rounded to 4 decimals like period_pnl_percent; None without a start value or without the component")
    period_realized_gain_loss_percent: Optional[SafeDecimal] = Field(None, description="period_realized_gain_loss / |start_value|, a fraction rounded to 4 decimals; None without a start value or without the component")
    period_income_percent: Optional[SafeDecimal] = Field(None, description="period_income / |start_value|, a fraction rounded to 4 decimals; None without a start value or without the component")
    period_fees_taxes_percent: Optional[SafeDecimal] = Field(
        None, description="period_fees_taxes / |start_value|, a fraction rounded to 4 decimals and positive like period_fees_taxes (a cost); None without a start value or without the component. Each component is rounded on its own: their sum may differ from period_pnl_percent in the last digit"
    )
    annualized_return: Optional[SafeDecimal] = Field(
        None, description="Net annualized return (CAGR) over the position's holding window inside the period (oldest lot opening in period -> period end), base = |start_value| or end cost basis when opened mid-period: (1+period_pnl_pct)^(365/days)-1. Fraction. None if <30 days / no base."
    )
    start_value: Optional[SafeDecimal] = Field(
        None,
        description="Position value at the end of the period's start day, as the portfolio values it (market quote, trade price, split adjustment, estimate at cost) at that day's rate; 0 if there was no opening position, None if it cannot be valued",
    )
    end_value: Optional[SafeDecimal] = Field(
        None,
        description="Position value at period end, as the portfolio values it (the holding's current_value) at that day's rate; 0 if the position was closed by period end, None if it cannot be valued",
    )
    is_fully_sold: bool = Field(False, description="True if position quantity is 0 at period end")
    closed_by: Optional[Literal["SELL", "TRANSFER", "ADJUSTMENT"]] = Field(
        None,
        description="For a position closed at period end: the type of the movement that closed it (the last one that took its quantity to the dust threshold or below; a split never closes). None while held, for an income-only row, or a position that never opened (MF-CB)",
    )
    closed_to_broker_id: Optional[int] = Field(
        None,
        description="With closed_by TRANSFER: the broker the units went to (the paired leg's), when the user can read it, in the requested brokers or not; None otherwise (MF-CB)",
    )
    oldest_open_lot_date: Optional[date_type] = Field(None, description="Opening date of the oldest FIFO lot still open at period end for this (asset, broker); None if fully closed")


class UnallocatedContribution(StrictModel):
    """Broker-level fees/income not attributed to a specific asset."""

    broker_id: int
    broker_name: str
    unallocated_income: Optional[SafeDecimal] = Field(None, description="DIVIDEND/INTEREST without asset_id in period")
    unallocated_fees_taxes: Optional[SafeDecimal] = Field(None, description="FEE/TAX without asset_id in period (positive value)")


class OtherPeriodEffectCode(StrEnum):
    """Fixed code of an `OtherPeriodEffect` row a reader must recognize without parsing its English description."""

    FX_ON_CASH = "fx_on_cash"


class OtherPeriodEffect(StrictModel):
    """Period P&L row not linked to a specific asset position."""

    description: str
    code: Optional[OtherPeriodEffectCode] = Field(None, description="Fixed code of the rows a reader recognizes by it, never by `description`: `fx_on_cash` is a broker's exchange result on foreign cash. None for every other row")
    category: str = Field(..., pattern="^(Income|Cost|Other)$")
    period_pnl: SafeDecimal
    broker_id: Optional[int] = Field(None, description="Nullable when effect is not broker-specific")
    broker_name: Optional[str] = Field(None, description="Nullable when effect is not broker-specific")


class PositionsContribution(StrictModel):
    """Complete per-asset contribution breakdown for a period."""

    positions: List[AssetPeriodContribution] = Field(default_factory=list)
    unallocated: List[UnallocatedContribution] = Field(default_factory=list)
    other_effects: List[OtherPeriodEffect] = Field(default_factory=list, description="Non-position period effects for income, costs, and reconciliation residuals")
    gross_gains: SafeDecimal = Field(default=0, description="Sum of max(period_pnl, 0) across all positions")
    gross_losses: SafeDecimal = Field(default=0, description="Sum of |min(period_pnl, 0)| across all positions")


class BrokerBreakdown(StrictModel):
    """Per-broker mini-summary (only populated when include_breakdown=True)."""

    broker_id: int
    broker_name: str
    net_worth: Currency
    gain_loss: Currency
    gain_loss_percent: SafeDecimal
    cash_total: Currency
    cash_balances: List[Currency] = Field(default_factory=list, description="Cash balance per currency, native (unconverted)")


class HoldingGroupGainLoss(StrictModel):
    """Unrealized gain or loss of a group of holdings: one broker's, or one asset type's at one broker."""

    broker_id: int
    asset_type: Optional[str] = Field(None, description="Asset type of the group, as the holdings report it; None for the broker's whole group")
    gain_loss: Optional[Currency] = Field(None, description="Sum of gain_loss over the group's holdings whose current_value and gain_loss are both known; None when none is")
    gain_loss_percent: Optional[SafeDecimal] = Field(
        None,
        description="gain_loss / the cost of the same holdings (current_value − gain_loss), a fraction (0.05 = 5 %), unrounded; None when no holding counts or the cost is 0",
    )


class UnrealizedBreakdownRow(StrictModel):
    """One row of the period's unrealized change, split by cause (Dashboard tooltip).

    For the assets priced in ``asset_currency`` (A), valued in the report currency (T), with r
    the A→T rate of the day, C_A and C_T their historical cost in A and in T:

    * ``asset`` — change of MV − C_A × r: what the assets did in their own currency;
    * ``fx`` — change of C_A × r − C_T: what the exchange rate did to their cost (A ≠ T only);
    * ``unsplit`` — change of MV − C_T for positions that could not be split on a boundary day
      (no market value, no rate, or a cost incomplete in either currency).
    """

    kind: Literal["asset", "fx", "unsplit"]
    asset_currency: str = Field(..., description="Currency the assets of this row are priced in")
    period_delta: Currency = Field(..., description="Change over the period, in the report currency")


class PortfolioSummary(StrictModel):
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
    period_unrealized_gain_loss_start: Optional[Currency] = Field(None, description="Unrealized G/L at start of period: market value − open cost basis of the positions held then, securities in transit left out (not NAV − book value)")
    period_unrealized_gain_loss_end: Optional[Currency] = Field(None, description="Unrealized G/L at end of period (snapshot): market value − open cost basis of the positions held then, securities in transit left out")
    period_unrealized_gain_loss_delta: Optional[Currency] = Field(None, description="Change in unrealized G/L over the period: end − start of market value − open cost basis")
    period_unrealized_breakdown: List[UnrealizedBreakdownRow] = Field(
        default_factory=list,
        description="period_unrealized_gain_loss_delta split by asset currency into the assets' own change and the exchange-rate effect on their historical cost; the rows add up to it exactly",
    )
    period_realized_gain_loss: Optional[Currency] = Field(None, description="Realized G/L in period (WAC-based): sales, and outgoing adjustments with a cost basis at the value they hand over")
    period_income: Optional[Currency] = Field(None, description="DIVIDEND + INTEREST in period, signed — a legacy negative correction reduces this value rather than being folded into the reconciliation residual")
    period_fees_taxes: Optional[Currency] = Field(None, description="FEE + TAX in period (positive value, shown negative in UI)")
    period_fees: Optional[Currency] = Field(None, description="FEE only in period (commissions)")
    period_taxes: Optional[Currency] = Field(None, description="TAX only in period")
    period_other_result: Optional[Currency] = Field(None, description="pnl - unrealized_delta - realized - income + fees_taxes")
    twrr_percent: Optional[SafeDecimal] = Field(None, description="Time-Weighted Return (None if not calculable)")
    mwrr_annualized_percent: Optional[SafeDecimal] = Field(None, description="Annualized MWRR / XIRR (None if not converged)")
    mwrr_cumulative_percent: Optional[SafeDecimal] = Field(None, description="Cumulative MWRR for the period: (1+r_ann)^(days/365)-1")
    mwrr_period_days: Optional[int] = Field(None, description="Number of days in the MWRR calculation period")
    timing_effect_percent: Optional[SafeDecimal] = Field(
        None,
        description="mwrr_cumulative_percent − twrr_percent, a fraction: what the timing of deposits and withdrawals added to the period's return; None when either is missing",
    )
    pnl_change_1d: Optional[Currency] = Field(
        None,
        description="Change of the total P&L from the calendar day before the valuation date to it, from the engine's daily states; None for a portfolio born on the valuation date",
    )
    pnl_change_1d_vs_nav_percent: Optional[SafeDecimal] = Field(
        None,
        description="pnl_change_1d / |NAV of the day before|, a fraction with the change's sign, unrounded; None on a zero base",
    )
    simple_roi_percent: SafeDecimal
    allocation_by_type: List[AllocationItem] = Field(default_factory=list)
    allocation_by_sector: List[AllocationItem] = Field(default_factory=list)
    allocation_by_geography: List[AllocationItem] = Field(default_factory=list)
    allocation_by_asset: List[AssetAllocationItem] = Field(default_factory=list, description="Held market value by asset (id = asset id), plus the Liquidity slice")
    holdings: List[PortfolioHolding] = Field(default_factory=list)
    holding_groups: List[HoldingGroupGainLoss] = Field(
        default_factory=list,
        description="Unrealized G/L of the holdings grouped by broker (asset_type None) and by asset type at each broker, ordered by broker_id then asset_type (the broker's group first)",
    )
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
