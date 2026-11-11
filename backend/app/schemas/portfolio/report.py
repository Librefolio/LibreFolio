"""Portfolio report (``GET /portfolio/report``): the query, the allocation history, the metadata and the response that gathers the sections."""

from __future__ import annotations

from datetime import date as date_type
from typing import List, Optional

from pydantic import Field

from backend.app.schemas.common import DateSpan, OpenDateRangeModel, StrictModel
from backend.app.schemas.portfolio.data_quality import DataQualityReport
from backend.app.schemas.portfolio.history import AcquisitionFundingSeries, BrokerPnlHistory, CostHistorySeries, DepositHistorySeries, IncomeHistorySeries, MwrrLinePoint, PnlCandleSeries, PortfolioHistoryPoint
from backend.app.schemas.portfolio.summary import AllocationHistoryPoint, PortfolioSummary, PositionsContribution


class AllocationHistoryDimensions(StrictModel):
    """Allocation history for all four dimensions."""

    type: List[AllocationHistoryPoint] = Field(default_factory=list)
    sector: List[AllocationHistoryPoint] = Field(default_factory=list)
    geography: List[AllocationHistoryPoint] = Field(default_factory=list)
    asset: List[AllocationHistoryPoint] = Field(default_factory=list, description="By asset (component id = asset id), plus Liquidity")


class PortfolioReportMetadata(StrictModel):
    """Metadata describing the report computation parameters."""

    broker_ids: Optional[List[int]] = None
    target_currency: str
    requested_date_from: Optional[date_type] = None
    requested_date_to: Optional[date_type] = None
    computed_date_from: Optional[date_type] = None
    computed_date_to: Optional[date_type] = None
    generated_at: date_type
    allocation_dimensions: List[str] = Field(default_factory=lambda: ["type", "sector", "geography"])
    included_features: List[str] = Field(default_factory=list)


class PortfolioReportQuery(StrictModel):
    """Request body for POST /portfolio/report.

    Runs the PortfolioCalculationEngine once and returns all requested views.
    """

    broker_ids: Optional[List[int]] = Field(None, description="Broker filter. None = all accessible brokers.")
    date_range: Optional[OpenDateRangeModel] = Field(None, description="Date range for history. None = full history.")
    target_currency: Optional[str] = Field(None, description="Override base currency (ISO 4217).")
    include_summary: bool = Field(True, description="Include portfolio summary (KPIs, holdings, allocations).")
    include_history: bool = Field(True, description="Include daily history time series.")
    include_allocation_history: bool = Field(True, description="Include allocation history by all dimensions.")
    include_breakdown: bool = Field(False, description="Include per-broker breakdown in summary.")
    include_positions_contribution: bool = Field(False, description="Include per-asset period P&L contribution.")
    include_broker_pnl_history: bool = Field(False, description="Include per-broker additive P&L history (G1a). Caller sets true only when effective scope has ≥2 brokers.")
    include_pnl_candles: bool = Field(False, description="Include the synthetic total-P&L candle series (G1b). Lazy: caller sets true only on first candle-submode activation — expensive OHLC work stays off ordinary reports.")
    include_income_history: bool = Field(False, description="Include the signed personal DIVIDEND/INTEREST income history (G1c). Caller policy: Dashboard/Broker overview set true eagerly — a sparse, cheap payload, unlike include_pnl_candles.")
    include_cost_history: bool = Field(False, description="Include the signed FEE+TAX cost history (batch 2). Same sparse/eager caller policy as include_income_history.")
    include_deposit_history: bool = Field(False, description="Include the DEPOSIT history (batch 2). Same sparse/eager caller policy as include_income_history.")
    include_acquisition_funding: bool = Field(False, description="Include the new-vs-reinvested BUY funding split (batch 2). Same sparse/eager caller policy as include_income_history.")
    apply_ownership_share: bool = Field(True, description="True (default): an owner counts its share of each broker. False: every broker counts whole, as an editor sees it — the broker page (D4).")


class PortfolioReportResponse(StrictModel):
    """Response for POST /portfolio/report.

    Contains all requested views derived from a single engine run.
    Sections are None when the corresponding include_* flag was False.
    """

    metadata: PortfolioReportMetadata
    summary: Optional[PortfolioSummary] = None
    history: Optional[List[PortfolioHistoryPoint]] = None
    allocation_history: Optional[AllocationHistoryDimensions] = None
    range: Optional[DateSpan] = Field(None, description="The days the step series cover (D-P4): the first day of the window with a state, and its end")
    mwrr_line: Optional[List[MwrrLinePoint]] = Field(None, description="The history's MWRR as true points (D-P4). Only when include_history=True.")
    data_quality: Optional[DataQualityReport] = None
    positions_contribution: Optional[PositionsContribution] = Field(None, description="Per-asset period P&L contribution. Only when include_positions_contribution=True.")
    broker_pnl_history: Optional[List[BrokerPnlHistory]] = Field(None, description="Per-broker additive P&L history (G1a). Only when include_broker_pnl_history=True.")
    pnl_candles: Optional[PnlCandleSeries] = Field(None, description="Synthetic total-P&L candle series (G1b). Only when include_pnl_candles=True.")
    income_history: Optional[IncomeHistorySeries] = Field(None, description="Signed personal DIVIDEND/INTEREST income history (G1c). Only when include_income_history=True.")
    cost_history: Optional[CostHistorySeries] = Field(None, description="Signed FEE+TAX cost history (batch 2). Only when include_cost_history=True.")
    deposit_history: Optional[DepositHistorySeries] = Field(None, description="DEPOSIT history (batch 2). Only when include_deposit_history=True.")
    acquisition_funding: Optional[AcquisitionFundingSeries] = Field(None, description="New-vs-reinvested BUY funding split (batch 2). Only when include_acquisition_funding=True.")
