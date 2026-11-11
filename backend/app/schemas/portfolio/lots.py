"""Bulk lots analysis (``POST /portfolio/lots``): the query, the lots, their timelines and histories, and the economic allocation of a position."""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from enum import StrEnum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from backend.app.schemas.common import Currency, DateSpan, OpenDateRangeModel, SafeDecimal, StepSpan, StrictModel
from backend.app.schemas.portfolio.data_quality import DataQualityReport

LotDirection = Literal["LONG", "SHORT"]


LotCustodyType = Literal["BROKER", "IN_TRANSIT"]


ReferencePriceSource = Literal["exact", "fallback", "unavailable"]


# Global analysis status (1:1 with FifoEngineResult.analysis_status). COMPLETE = fully reliable;
# DEGRADED = isolable economic issue (orphan income/cost, FX gap, local pool failure) with gross
# metrics intact; FAILED = non-isolable quantitative failure (unreliable replay).
LotAnalysisStatus = Literal["COMPLETE", "DEGRADED", "FAILED"]


# Per-lot net-metrics reliability, orthogonal to the global status.
LotNetMetricsStatus = Literal["AVAILABLE", "UNAVAILABLE"]


LotValueSource = Literal["MARKET_PRICE", "ESTIMATED_AT_COST"]


class LotAnalysisType(StrEnum):
    """Selectable sections for POST /portfolio/lots/analysis."""

    LOT_SUMMARY = "LOT_SUMMARY"
    GANTT_TOPOLOGY = "GANTT_TOPOLOGY"
    CUSTODY_HISTORY = "CUSTODY_HISTORY"
    EVENT_HISTORY = "EVENT_HISTORY"
    VALUE_HISTORY = "VALUE_HISTORY"
    RETURN_HISTORY = "RETURN_HISTORY"
    PRICE_HISTORY = "PRICE_HISTORY"
    MARKET_PRICE_HISTORY = "MARKET_PRICE_HISTORY"
    BROKER_WAC_HISTORY = "BROKER_WAC_HISTORY"
    CUMULATIVE_WAC_HISTORY = "CUMULATIVE_WAC_HISTORY"
    PERFORMANCE_HISTORY = "PERFORMANCE_HISTORY"
    INCOME_EVENTS = "INCOME_EVENTS"


class LotsAnalysisQuery(BaseModel):
    """Request body for POST /portfolio/lots/analysis."""

    asset_id: int = Field(..., description="Asset to analyze.")
    broker_ids: Optional[List[int]] = Field(None, description="Optional broker filter. None = all accessible brokers.")
    date_range: Optional[OpenDateRangeModel] = Field(None, description="Optional date range filter for histories and visible intervals.")
    target_currency: Optional[str] = Field(None, description="Override base currency (ISO 4217).")
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


class LotCustodySummarySchema(StrictModel):
    """Current custody slice for a lot."""

    broker_id: Optional[int] = Field(None, description="Broker currently holding this fragment. None for in-transit slices.")
    custody_type: LotCustodyType
    quantity: SafeDecimal


class LotSummarySchema(StrictModel):
    """Direction-neutral lot row used by table, selection sync, and custody modal."""

    lot_id: int = Field(..., description="Stable lot identifier. Equals opening_transaction_id.")
    opening_transaction_id: int = Field(..., description="Transaction that opened the lot. Equals lot_id.")
    asset_id: int
    direction: LotDirection
    opening_broker_id: int
    opening_date: date_type
    closing_date: Optional[date_type] = Field(None, description="Authoritative closing date (max LotClosure.close_date) when fully closed (open_quantity == 0). None otherwise.")
    opening_unit_price: Optional[SafeDecimal] = Field(None, description="Opening unit price converted to response target_currency; None when the rate at the opening date is missing.")
    original_quantity: SafeDecimal
    original_cost: Optional[SafeDecimal] = Field(None, description="Original lot cost in response target_currency; None when the rate at the opening date is missing.")
    currency: Optional[str] = Field(None, description="Original transaction currency preserved from FifoLot.currency.")
    open_quantity: SafeDecimal
    realized_quantity: SafeDecimal
    realized_pnl: Optional[SafeDecimal] = Field(None, description="Realized FIFO P&L in response target_currency; None when the rate of one of its closures is missing.")
    cumulative_proceeds: Optional[SafeDecimal] = Field(None, description="Cumulative proceeds in response target_currency; None when a rate they need is missing.")
    reference_unit_price: Optional[SafeDecimal] = Field(None, description="Reference unit price used for relative return, in target_currency.")
    reference_price_source: Optional[ReferencePriceSource] = None
    states: List[str] = Field(default_factory=list, description="Combinable derived state tags from FifoEngineResult.get_lot_states().")
    current_custody: List[LotCustodySummarySchema] = Field(default_factory=list, description="Active custody slices for unified table and modal summary.")
    open_value: Optional[SafeDecimal] = Field(None, description="Current open mark-to-market value in response target_currency.")
    total_value: Optional[SafeDecimal] = Field(None, description="Current total lot value (open_value + realized cash logic) in response target_currency.")
    pnl: Optional[SafeDecimal] = Field(None, description="Market+realized lot P&L in target_currency (excludes asset income). = market_pnl + realized_pnl.")
    relative_return: Optional[SafeDecimal] = Field(None, description="Open Return: relative return vs reference_unit_price, when computable.")
    asset_income: Optional[SafeDecimal] = Field(default=Decimal("0"), description="Cumulative asset-linked dividends+interest allocated to this lot, in target_currency; None when an income pool reaching the lot has no rate.")
    market_pnl: Optional[SafeDecimal] = Field(None, description="Price-only P&L: OpenValue - open cost basis. 0 when value_source=ESTIMATED_AT_COST. = pnl - realized_pnl.")
    total_pnl: Optional[SafeDecimal] = Field(None, description="market_pnl + realized_pnl + asset_income, in target_currency.")
    cash_yield: Optional[SafeDecimal] = Field(None, description="asset_income / opening_value, when opening_value > 0.")
    total_return: Optional[SafeDecimal] = Field(None, description="total_pnl / opening_value (opening_value = original_cost), when > 0.")
    annualized_return: Optional[SafeDecimal] = Field(None, description="Net annualized return (CAGR) of net_total_return over the lot holding window (opening_date -> closing_date if closed, else analysis end): (1+net_total_return)^(365/days)-1. Fraction. None if net metrics unavailable / <30 days.")
    value_source: Optional[LotValueSource] = Field(
        None, description="MARKET_PRICE when the asset has a current price — a market quote or a BUY/SELL price, carried forward; ESTIMATED_AT_COST when it has no observation at all (open value assumed at cost, market_pnl=0); null when the current price cannot be converted."
    )
    allocated_fees: Optional[SafeDecimal] = Field(default=Decimal("0"), description="Cumulative FEE allocated to this lot, target_currency (positive magnitude); None when a FEE pool reaching the lot cannot be valued in target_currency.")
    allocated_taxes: Optional[SafeDecimal] = Field(default=Decimal("0"), description="Cumulative TAX allocated to this lot, target_currency (positive magnitude); None when a TAX pool reaching the lot cannot be valued in target_currency.")
    net_total_pnl: Optional[SafeDecimal] = Field(None, description="total_pnl - allocated_fees - allocated_taxes, in target_currency.")
    net_total_return: Optional[SafeDecimal] = Field(None, description="net_total_pnl / opening_value, when opening_value > 0.")
    net_metrics_status: LotNetMetricsStatus = Field("AVAILABLE", description="AVAILABLE when net metrics are reliable; UNAVAILABLE when the lot belongs to a degraded economic pool.")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        return Currency.validate_code(v) if v else None


class GanttSegmentSchema(StrictModel):
    """Serializable projection of one FragmentInterval."""

    fragment_id: str
    lot_id: int
    direction: LotDirection
    custody_type: LotCustodyType
    broker_id: Optional[int] = None
    source_broker_id: Optional[int] = None
    destination_broker_id: Optional[int] = None
    quantity: SafeDecimal
    unit_price: Optional[SafeDecimal] = Field(None, description="Fragment unit price converted to response target_currency; None when the rate at the fragment start is missing.")
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


class LotTimelineEventSchema(StrictModel):
    """Flat lot timeline row.

    Shared by both custody_history and lot_events. Flat list + lot_id keeps response
    shape consistent with existing point-based history DTOs and simplifies multi-select UI.
    """

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
    opening_value: Optional[SafeDecimal] = Field(
        None,
        description="For the event that opens a lot (BUY, ADJUSTMENT_IN): the lot's original cost in target_currency, converted at the opening date — the lot summary's original_cost, in the currency of unit_price. None on every other kind and when the conversion is missing.",
    )
    scope_boundary: Optional[Literal["IN", "OUT"]] = Field(
        None,
        description="For a row of a TRANSFER leg whose partner sits at a broker outside the scope, read as an adjustment: IN when its units came into the scope, OUT when they left it. A label only, the economics follow kind; the partner broker is never named. None on every other row.",
    )


class LotValueHistoryPoint(StepSpan):
    """Per-lot value history point."""

    lot_id: int
    open_value: SafeDecimal
    proceeds: SafeDecimal
    total_value: SafeDecimal
    original_cost: SafeDecimal
    pnl: SafeDecimal
    income: Optional[SafeDecimal] = Field(default=Decimal("0"), description="Cumulative asset-linked income (dividends+interest) allocated to this lot up to date, in target_currency; None from the date of an income pool without a rate.")
    allocated_fees: Optional[SafeDecimal] = Field(default=Decimal("0"), description="Cumulative FEE allocated to this lot up to date, in target_currency (positive magnitude); None from the date of a FEE pool that cannot be valued.")
    allocated_taxes: Optional[SafeDecimal] = Field(default=Decimal("0"), description="Cumulative TAX allocated to this lot up to date, in target_currency (positive magnitude); None from the date of a TAX pool that cannot be valued.")
    net_pnl: Optional[SafeDecimal] = Field(default=Decimal("0"), description="pnl - allocated_fees - allocated_taxes up to date, in target_currency; None when fees or taxes are unknown.")


class LotReturnHistoryPoint(StepSpan):
    """Per-lot relative return point."""

    lot_id: int
    total_return: Optional[SafeDecimal] = Field(
        None,
        description="(OpenValue(t)+Proceeds(t)+Income(t))/OriginalCost - 1. Includes asset-linked income. Computable when original_cost != 0.",
    )
    relative_return: Optional[SafeDecimal] = Field(None, description="None when reference price is unavailable or zero.")
    reference_price_source: Optional[ReferencePriceSource] = Field(None, description="Reference price resolution echoed for chart/tooltips.")
    income: Optional[SafeDecimal] = Field(default=Decimal("0"), description="Cumulative asset-linked income allocated to this lot up to date, in target_currency; None from the date of an income pool without a rate.")
    net_total_return: Optional[SafeDecimal] = Field(None, description="(total_value + income - allocated_fees - allocated_taxes)/original_cost - 1, when original_cost != 0.")


class LotPriceHistoryPoint(StepSpan):
    """Per-lot market price point."""

    lot_id: int
    market_price: SafeDecimal
    currency: str = Field(..., description="Currency of market_price, normally equal to response target_currency.")
    estimated: bool = Field(default=False, description="True when market_price is estimated from the last-known trade (no real market quote on/before this date), False for an actual price-history quote.")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return Currency.validate_code(v)


class MarketPriceHistoryPoint(StepSpan):
    """The asset's market price on one day, whatever lots are open (Y-30): a LotPriceHistoryPoint without lot_id."""

    market_price: SafeDecimal
    currency: str = Field(..., description="Currency of market_price: the response target_currency.")
    estimated: bool = Field(default=False, description="True when market_price is estimated from the last-known trade (no real market quote on/before this date), False for an actual price-history quote, exact or carried forward.")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return Currency.validate_code(v)


class BrokerWACHistoryPoint(StepSpan):
    """Broker-scoped WAC time-series point for selected asset."""

    broker_id: int
    wac: SafeDecimal
    pool_qty: SafeDecimal


class CumulativeWACHistoryPoint(StepSpan):
    """Combined WAC time-series point across requested brokers."""

    wac: SafeDecimal
    pool_qty: SafeDecimal


class PerformanceHistoryPoint(StepSpan):
    """Asset-level ROI/TWRR time-series point (whole asset in filtered broker scope, independent of selected_lot_ids)."""

    roi: Optional[SafeDecimal] = Field(None, description="Simple ROI at this date, None if not computable (e.g. no cash flow yet).")
    twrr: Optional[SafeDecimal] = Field(None, description="Cumulative TWRR at this date, None if not computable.")


class LotIncomeEventKind(StrEnum):
    """Asset-linked income transaction kinds allocated to LONG lots (plan v3 §11 markers)."""

    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"


class LotIncomeEventSchema(StrictModel):
    """A single asset-linked DIVIDEND/INTEREST transaction allocated pro-rata across open LONG lots.

    Powers the dashed income markers on the WAC/Value/Return charts (plan v3 §11): one entry per
    income transaction that had at least one open LONG lot on its date. ``amount`` is the whole
    transaction total in target_currency (pre-split); ``lot_ids`` are the lots it was allocated to.
    """

    type: LotIncomeEventKind
    date: date_type
    broker_id: Optional[int] = Field(None, description="Broker of the income transaction.")
    transaction_id: Optional[int] = Field(None, description="Source transaction id.")
    amount: Optional[SafeDecimal] = Field(None, description="Total income in target_currency (before pro-rata allocation); None when its rate is missing.")
    lot_ids: List[int] = Field(default_factory=list, description="LONG lots the income was allocated to at transaction.date.")


EconomicTypeLiteral = Literal["FEE", "TAX", "DIVIDEND", "INTEREST"]


AllocationContextLiteral = Literal["OPENING", "CLOSURE", "INCOME", "HOLDING"]


AllocationRuleLiteral = Literal[
    "ASSET_INCOME_HOLDINGS",
    "SAME_DAY_MIXED_TRADES",
    "SAME_DAY_TRADES",
    "SAME_DAY_INCOME",
    "PREVIOUS_DAY_TRADES",
    "PREVIOUS_DAY_INCOME",
    "OPEN_LOTS_FALLBACK",
]


class EconomicLotAllocationSchema(StrictModel):
    """Audit leaf: share of a target operation assigned to a single lot."""

    lot_id: int
    weight: SafeDecimal
    native_amount: Optional[SafeDecimal] = Field(None, description="Native share of the pool; None when the split of the pool is unknown (weighting trades in different currencies, one without a rate).")
    target_amount: Optional[SafeDecimal] = Field(None, description="Target-currency share; None when the pool or its split cannot be valued in target_currency.")


class TargetOperationAllocationSchema(StrictModel):
    """Audit mid-level: one target operation (opening/closure/income/holding).

    The allocation context lives on the operation, not the group, so the same lot
    can appear under multiple contexts (e.g. OPENING and CLOSURE) with its
    breakdown preserved.
    """

    context: AllocationContextLiteral
    operation_transaction_id: Optional[int] = Field(None, description="Trade/income transaction the pool was matched against; None for HOLDING fallback.")
    weight: Optional[SafeDecimal] = Field(None, description="Share of the pool assigned to this operation; None when the weighting trades are in different currencies and one has no rate.")
    lot_allocations: List[EconomicLotAllocationSchema] = Field(default_factory=list)


class EconomicAllocationGroupSchema(StrictModel):
    """Audit top-level: a pooled economic group (FEE/TAX/income) and its allocations."""

    economic_type: EconomicTypeLiteral
    asset_id: int
    broker_id: int
    date: date_type
    native_currency: Optional[str] = None
    target_currency: str
    rule: AllocationRuleLiteral
    source_transaction_ids: List[int] = Field(default_factory=list)
    native_pool_total: SafeDecimal
    target_pool_total: Optional[SafeDecimal] = Field(None, description="Pool total in target_currency; None when one of its events has no rate.")
    operation_allocations: List[TargetOperationAllocationSchema] = Field(default_factory=list)
    native_orphan: SafeDecimal = Field(default=0, description="Unallocated native residual (orphan pool).")
    target_orphan: Optional[SafeDecimal] = Field(default=Decimal("0"), description="Unallocated target residual (orphan pool); None when one of its events has no rate.")


class LotsAnalysisMetadata(StrictModel):
    """Metadata describing bulk lots-analysis computation."""

    broker_ids: Optional[List[int]] = None
    selected_lot_ids: Optional[List[int]] = None
    requested_analyses: List[LotAnalysisType]
    requested_date_from: Optional[date_type] = None
    requested_date_to: Optional[date_type] = None
    computed_date_from: Optional[date_type] = None
    computed_date_to: Optional[date_type] = None
    generated_at: date_type


class LotsAnalysisResponse(StrictModel):
    """Response for POST /portfolio/lots/analysis.

    Sections are None unless explicitly requested via requested_analyses.
    """

    asset_id: int
    target_currency: str
    quote_base_quantity: int = Field(
        1,
        description="Asset quote_base_quantity (e.g. 100 for bonds priced per 100 nominal). Lets the frontend rescale per-quote unit prices (opening_unit_price) to the per-unit axis used by WAC/value lines.",
    )
    calculation_status: LotAnalysisStatus
    calculation_metadata: LotsAnalysisMetadata
    range: Optional[DateSpan] = Field(
        None,
        description="The days the histories cover: the first day of the window with data (the later of the requested start and the scope's first transaction) to its last day. None when the window holds no day. Every history point holds from its `date` to its `through`, both inside it.",
    )
    data_quality: Optional[DataQualityReport] = None
    lots: Optional[List[LotSummarySchema]] = Field(None, description="LOT_SUMMARY payload.")
    gantt_segments: Optional[List[GanttSegmentSchema]] = Field(None, description="GANTT_TOPOLOGY payload.")
    custody_history: Optional[List[LotTimelineEventSchema]] = Field(None, description="CUSTODY_HISTORY payload.")
    lot_events: Optional[List[LotTimelineEventSchema]] = Field(None, description="EVENT_HISTORY payload.")
    value_history: Optional[List[LotValueHistoryPoint]] = Field(None, description="Flat per-lot VALUE_HISTORY points.")
    return_history: Optional[List[LotReturnHistoryPoint]] = Field(None, description="Flat per-lot RETURN_HISTORY points.")
    price_history: Optional[List[LotPriceHistoryPoint]] = Field(None, description="Flat per-lot PRICE_HISTORY points.")
    market_price_history: Optional[List[MarketPriceHistoryPoint]] = Field(
        None,
        description="MARKET_PRICE_HISTORY payload — the asset's market price on each day of the window that has a mark convertible to target_currency, independent of the lots and of selected_lot_ids; kept with FAILED.",
    )
    broker_wac_history: Optional[List[BrokerWACHistoryPoint]] = Field(None, description="BROKER_WAC_HISTORY payload.")
    cumulative_wac_history: Optional[List[CumulativeWACHistoryPoint]] = Field(None, description="CUMULATIVE_WAC_HISTORY payload.")
    performance_history: Optional[List[PerformanceHistoryPoint]] = Field(
        None,
        description="PERFORMANCE_HISTORY payload — asset-wide ROI/TWRR, ignores selected_lot_ids.",
    )
    income_events: Optional[List[LotIncomeEventSchema]] = Field(
        None,
        description="INCOME_EVENTS payload — asset-linked DIVIDEND/INTEREST allocated to LONG lots, for chart markers.",
    )
    economic_allocation_groups: Optional[List[EconomicAllocationGroupSchema]] = Field(
        None,
        description="Inline one-shot economic audit (FEE/TAX/income pooling + allocations). Present with LOT_SUMMARY.",
    )
    asset_orphan_income: Optional[SafeDecimal] = Field(default=Decimal("0"), description="Income with no eligible lot, in target_currency; None when an orphan income pool has no rate.")
    asset_orphan_fees: Optional[SafeDecimal] = Field(default=Decimal("0"), description="FEE with no eligible lot, in target_currency; None when an orphan FEE pool has no rate.")
    asset_orphan_taxes: Optional[SafeDecimal] = Field(default=Decimal("0"), description="TAX with no eligible lot, in target_currency; None when an orphan TAX pool has no rate.")

    @field_validator("target_currency")
    @classmethod
    def validate_target_currency(cls, v: str) -> str:
        return Currency.validate_code(v)
