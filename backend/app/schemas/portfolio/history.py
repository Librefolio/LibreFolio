"""Portfolio history series: value, MWRR line, broker P&L, P&L candles, income, cost, deposits and acquisition funding."""

from __future__ import annotations

from datetime import date as date_type
from typing import List, Optional

from pydantic import BaseModel, Field

from backend.app.schemas.common import Currency, SafeDecimal, StepSpan, StrictModel


class PortfolioHistoryPoint(StepSpan):
    """One step of the portfolio value series (D-P4): the values hold from ``date`` to ``through``, during which nothing
    changes. The MWRR, which moves every day, is in ``PortfolioReportResponse.mwrr_line``."""

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
    roi: Optional[SafeDecimal] = Field(None, description="Simple ROI series point")


class MwrrLinePoint(StrictModel):
    """A true point of the history's MWRR line (D-P4): the MWRR of the period up to ``date``, solved on that day. The line
    has a point at the start and the end of every history step, and one a month inside the steps longer than 62 days."""

    date: date_type
    annualized: Optional[SafeDecimal] = Field(None, description="Annualized MWRR on this day; None where there is no rate")
    cumulative: Optional[SafeDecimal] = Field(None, description="Cumulative MWRR on this day: (1+r_ann)^(days/365)-1")


class BrokerPnlHistoryPoint(StepSpan):
    """One step of a broker's additive P&L contribution (G1a, D-P4)."""

    total_pnl: Currency = Field(..., description="This broker's slice of the scope total_pnl for this day")


class BrokerPnlHistory(StrictModel):
    """One broker's full additive P&L history (G1a — GrowthChart P&L broker overlay).

    Points are built from the same Decimal components as the scope-aggregate
    PortfolioHistoryPoint.total_pnl at each date, so for every date, summing
    total_pnl across all BrokerPnlHistory entries reproduces the aggregate
    PortfolioHistoryPoint.total_pnl exactly (see DailyStateBuilder §4.2).
    """

    broker_id: int
    broker_name: str
    points: List[BrokerPnlHistoryPoint] = Field(default_factory=list)


class PnlCandlePoint(StepSpan):
    """One day's synthetic total-P&L candle (G1b, plan §4.3).

    ``close`` always equals the canonical ``PortfolioHistoryPoint.total_pnl`` for the
    same date exactly (built by construction from the same Decimal components, not a
    residual check). Days whose candle is unavailable (a held asset's valuation was
    MISSING that day) are omitted from the series entirely — a genuine gap, never a
    guessed or zeroed candle. A step (D-P4): a quiet day carries the candle of the last computed day.
    """

    open: Currency
    high: Currency
    low: Currency
    close: Currency


class PnlCandleSeries(StrictModel):
    """The full synthetic P&L candle series (G1b — GrowthChart P&L candles submode).

    Cross-asset high/low are explicitly synthetic and potentially non-simultaneous
    (plan §3.3) — ``hypothetical`` is always ``True`` at this series-metadata level so
    the frontend can render the required always-visible label; there is no per-point
    variant since every point in this series carries the same caveat. No volume field
    by design (plan §3.3).
    """

    hypothetical: bool = Field(True, description="Always true: cross-asset high/low are synthetic/non-simultaneous, never a real intraday series")
    points: List[PnlCandlePoint] = Field(default_factory=list)


class IncomeHistoryPoint(BaseModel):
    """One day's signed personal income (G1c, plan §3.4/§4.4).

    Source is every scoped, committed DIVIDEND/INTEREST Transaction — asset-linked
    and broker-level (``asset_id=None``) rows alike, never a global AssetEvent
    declaration. Signed: a legacy negative correction reduces the bucket, it is
    never abs()'d away. Days with no DIVIDEND/INTEREST activity are omitted from
    the series entirely (a sparse economic-flow series, not a dense one with
    false zeros) — this point type itself never carries a "no data" sentinel.
    """

    date: date_type
    dividend: Currency = Field(..., description="Signed sum of DIVIDEND transactions for this date")
    interest: Currency = Field(..., description="Signed sum of INTEREST transactions for this date")


class IncomeHistorySeries(StrictModel):
    """The full signed personal income history (G1c — GrowthChart P&L income submode).

    ``sum(dividend) + sum(interest)`` across every point reproduces the canonical
    signed ``PortfolioSummary.period_income`` exactly for the same scope/date
    range (plan §3.4) — same signed-conversion pattern as the summary's own
    income accumulator, not a residual reconciliation. ``missing_fx_pairs``
    reuses the existing portfolio data-quality contract: a day whose income
    transaction could not be converted is omitted from the sums (never a
    silently-wrong zero) and its currency pair is reported here instead.
    """

    points: List[IncomeHistoryPoint] = Field(default_factory=list)
    missing_fx_pairs: List[str] = Field(default_factory=list, description="'FROM/TO' pairs that could not be converted — affected days are excluded from the sums, not zeroed")


class CostHistoryPoint(BaseModel):
    """One day's signed cost total (batch 2 — FEE + TAX combined, matching the
    dashboard's existing "Fees & taxes" KPI grouping).

    Source is every scoped, committed FEE/TAX Transaction — asset-linked and
    broker-level (``asset_id=None``) rows alike. Signed: preserves the raw
    Transaction.amount sign (negative, per the FEE/TAX convention) rather than
    flipping to a positive "magnitude" — same signed-fidelity policy as
    IncomeHistoryPoint. Days with no FEE/TAX activity are omitted entirely
    (sparse, not a dense zero-filled series).
    """

    date: date_type
    cost: Currency = Field(..., description="Signed sum of FEE+TAX transactions for this date (negative, per the DB convention)")


class CostHistorySeries(StrictModel):
    """The full signed cost history (batch 2 — GrowthChart Income submode's costs dimension)."""

    points: List[CostHistoryPoint] = Field(default_factory=list)
    missing_fx_pairs: List[str] = Field(default_factory=list, description="'FROM/TO' pairs that could not be converted — affected days are excluded from the sums, not zeroed")


class DepositHistoryPoint(BaseModel):
    """One day's deposit total (batch 2 — fresh external cash contributed).

    Source is every scoped, committed DEPOSIT Transaction. Always non-negative
    per the DEPOSIT type's own sign convention (Transaction.amount > 0). Days
    with no DEPOSIT activity are omitted entirely (sparse, not a dense
    zero-filled series).
    """

    date: date_type
    deposit: Currency = Field(..., description="Sum of DEPOSIT transactions for this date")


class DepositHistorySeries(StrictModel):
    """The full deposit history (batch 2 — GrowthChart Income submode's deposit-size dimension)."""

    points: List[DepositHistoryPoint] = Field(default_factory=list)
    missing_fx_pairs: List[str] = Field(default_factory=list, description="'FROM/TO' pairs that could not be converted — affected days are excluded from the sums, not zeroed")


class AcquisitionFundingPoint(BaseModel):
    """One day's BUY funding split between fresh capital and reinvested returns
    (batch 2 — "new vs reinvested liquidity", plan §5.2).

    Not independently computed: surfaces the engine's own existing per-BUY K/R
    pool draw (see AcquisitionFundingContribution) — the same value already
    used internally to update the running capital/returns pool balances, now
    also exposed as an output. ``from_new_capital + from_reinvested`` equals
    that day's total BUY cash outflow exactly, by construction (not a
    residual). Days with no BUY activity are omitted entirely (a genuine gap,
    not a zeroed row).
    """

    date: date_type
    from_new_capital: Currency = Field(..., description="Portion of that day's BUY(s) funded from fresh external capital (K pool)")
    from_reinvested: Currency = Field(..., description="Portion of that day's BUY(s) funded from reinvested prior returns (R pool)")


class AcquisitionFundingSeries(StrictModel):
    """The full new-vs-reinvested BUY funding history (batch 2 — GrowthChart Income
    submode's acquisition-size dimension, rendered as a 2-zone stacked bar).

    No ``missing_fx_pairs`` field of its own, unlike its co-rendered Income-submode
    siblings (income/cost/deposit). A BUY whose currency has no FX rate on its date is
    skipped by the engine's ``amount_target is None -> continue`` guard before it reaches
    the funding split, so it contributes nothing here; the engine records that failed
    conversion in its movement-level ``missing_fx`` channel, which reaches the report's
    ``data_quality`` (pair and date) whenever the summary is built. Same as
    PnlCandleSeries, which shipped with it.
    """

    points: List[AcquisitionFundingPoint] = Field(default_factory=list)
