"""Positions series (``GET /portfolio/positions-series``): the position key, the query, the points and the response."""

from __future__ import annotations

from datetime import date as date_type
from typing import List, Literal, Optional

from pydantic import Field

from backend.app.schemas.common import DateSpan, OpenDateRangeModel, SafeDecimal, StepSpan, StrictModel


class PositionKey(StrictModel):
    """A position asked for: an asset at one broker, or at all the brokers of the scope."""

    asset_id: int
    broker_id: Optional[int] = Field(None, description="Broker that holds the position. None = the asset summed over the brokers of the scope.")


class PositionsSeriesQuery(StrictModel):
    """Request body for POST /portfolio/positions-series: the daily series of the chosen positions, and only those."""

    broker_ids: Optional[List[int]] = Field(None, description="Broker filter, as the report's. None = all accessible brokers.")
    date_range: Optional[OpenDateRangeModel] = Field(None, description="The window of the chart: its start is the period's start (every figure is the result since it). None = full history.")
    target_currency: Optional[str] = Field(None, description="Override base currency (ISO 4217).")
    positions: List[PositionKey] = Field(..., min_length=1, max_length=50, description="The positions to draw (max 50), as the rows of the Portfolio table: (asset, broker).")
    apply_ownership_share: bool = Field(True, description="As the report's: False counts every broker whole (the broker page, D4).")


class PositionSeriesPoint(StepSpan):
    """One step of a position's series, in the report currency and at the owner's share: the figures hold from `date` to `through`, both included."""

    quantity: SafeDecimal = Field(..., description="Units held; 0 on the day the position closes")
    market_value: Optional[SafeDecimal] = Field(None, description="Value as the portfolio values it that day; 0 once closed; None when it cannot be valued (missing price or rate)")
    cost_basis: Optional[SafeDecimal] = Field(None, description="Historical cost of the open quantity; None when it is incomplete")
    pnl: Optional[SafeDecimal] = Field(
        None, description="The position's result since the window's start, the Performance table's period P&L at this day: the change of the unrealized result + realized + income - fees and taxes. A sum of the parts that are known when `complete` is False; None when none is."
    )
    base: Optional[SafeDecimal] = Field(None, description="The capital the percent is on: |value at the window's start| + the cost of what is bought after it + what an internal transfer brings in, at its value on arrival. A sale never lowers it. None when the start value is unknown.")
    pnl_percent: Optional[SafeDecimal] = Field(None, description="pnl / base, a fraction (0.12 = 12 %), unrounded; None when the base is 0 or unknown. «Base 100» is 1 + pnl_percent.")
    valuation_source: Optional[Literal["MARKET_PRICE", "LAST_TRADE_PRICE", "ESTIMATED_AT_COST", "MISSING"]] = Field(None, description="How the value was found, as the holdings report it; None when the position is not held that day")
    complete: bool = Field(True, description="False when a boundary value of the unrealized result is unknown that day, so `pnl` leaves that part out")


class PositionSeries(StrictModel):
    """The series of one asked position."""

    key: PositionKey
    asset_name: str
    asset_ticker: Optional[str] = None
    broker_name: Optional[str] = Field(None, description="None for an asset summed over the brokers")
    first_date: Optional[date_type] = Field(None, description="First day with a point: the window's start if the position is held then, else the first day held; None if never held in the window")
    last_date: Optional[date_type] = Field(None, description="The window's end while the position is held, else the day it went to 0")
    held_at_start: bool = False
    held_at_end: bool = False
    closed_on: Optional[date_type] = Field(None, description="The day the position went to 0 for good; None while it is held")
    complete: bool = Field(True, description="False when any point is not complete")
    points: List[PositionSeriesPoint] = Field(default_factory=list, description="Steps, contiguous from first_date to last_date: each holds from its `date` to its `through` while nothing changes")


class PositionsSeriesResponse(StrictModel):
    """Response for POST /portfolio/positions-series."""

    currency: str
    date_from: date_type
    date_to: date_type
    range: DateSpan = Field(..., description="The window of the chart: `date_from` to `date_to`. Every point of every series holds inside it, from its `date` to its `through`.")
    series: List[PositionSeries] = Field(default_factory=list, description="In the order asked; a position never held in the window has points = []")
    missing_fx_pairs: List[str] = Field(default_factory=list, description="Pairs the engine could not convert in the window: the values that depend on them are None")
