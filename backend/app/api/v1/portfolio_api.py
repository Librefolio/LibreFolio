"""
Portfolio API endpoints for LibreFolio.

Provides read-only portfolio calculations on committed data:
- POST /portfolio/wac           — WAC time series per (broker, asset)
- POST /portfolio/report        — UNIFIED: summary+history+allocation+contribution+data_quality
- POST /portfolio/lots/analysis — FifoLotEngine bulk multi-analysis (lots, Gantt, histories, WAC)

Legacy standalone endpoints (/summary, /history, /allocation-history) removed —
all data is available via /report with include_* flags.
"""

from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import Asset, User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.portfolio import LotsAnalysisQuery, LotsAnalysisResponse, PortfolioReportQuery, PortfolioReportResponse, WACAnalyticsRequest, WACAnalyticsResponse, WACAnalyticsResultItem, WACSeriesPoint
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.portfolio_service import PortfolioService, compute_wac_iterative

logger = get_logger(__name__)

portfolio_router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@portfolio_router.post(
    "/wac",
    response_model=WACAnalyticsResponse,
    summary="WAC time series",
    description="Compute WAC (Weighted Average Cost) time series for committed transactions. " "Returns point-per-transaction data where WAC changes — useful for chart overlays and P&L.",
)
async def get_portfolio_wac(
    body: WACAnalyticsRequest,
    session: AsyncSession = Depends(get_session_generator),
) -> WACAnalyticsResponse:
    """Compute WAC time series for each (broker, asset) query."""
    results: list[WACAnalyticsResultItem] = []

    for query in body.queries:
        # Determine as_of_date: use query end date or today
        as_of_date = query.date_range.end if query.date_range and query.date_range.end else date_type.today()

        # Get asset currency
        asset = await session.get(Asset, query.asset_id)
        if asset is None:
            results.append(
                WACAnalyticsResultItem(
                    broker_id=query.broker_id,
                    asset_id=query.asset_id,
                    currency="USD",
                    series=[],
                    missing_fx_pairs=[],
                )
            )
            continue

        asset_currency = asset.currency or "USD"

        # Compute full WAC with qualifying_txs
        wac_result = await compute_wac_iterative(
            session=session,
            broker_id=query.broker_id,
            asset_id=query.asset_id,
            as_of_date=as_of_date,
            asset_currency=asset_currency,
        )

        # If FX errors, return empty series with missing_fx_pairs
        if wac_result.wac_missing_pairs:
            results.append(
                WACAnalyticsResultItem(
                    broker_id=query.broker_id,
                    asset_id=query.asset_id,
                    currency=asset_currency,
                    series=[],
                    missing_fx_pairs=wac_result.wac_missing_pairs,
                )
            )
            continue

        # Build series from qualifying_txs (each has running_wac)
        # Apply start date filter if provided
        start_date = query.date_range.start if query.date_range and query.date_range.start else None
        target_currency = wac_result.wac.code if wac_result.wac else asset_currency

        series: list[WACSeriesPoint] = []
        # Track running pool_qty from qualifying txs
        pool_qty_running = 0
        for qtx in wac_result.wac_qualifying_txs:
            pool_qty_running += qtx.quantity
            # Apply date filter
            if start_date and qtx.date < start_date:
                continue
            if qtx.running_wac is not None:
                series.append(
                    WACSeriesPoint(
                        date=qtx.date,
                        wac=qtx.running_wac,
                        pool_qty=pool_qty_running,
                        effect=qtx.effect,
                    )
                )

        results.append(
            WACAnalyticsResultItem(
                broker_id=query.broker_id,
                asset_id=query.asset_id,
                currency=target_currency,
                series=series,
                missing_fx_pairs=[],
            )
        )

    return WACAnalyticsResponse(results=results)


# =============================================================================
# PORTFOLIO ENDPOINTS
# =============================================================================


@portfolio_router.post(
    "/report",
    response_model=PortfolioReportResponse,
    summary="Unified portfolio report",
    description=("Run the PortfolioCalculationEngine once and return all requested views " "(summary, history, allocation history, data quality) in a single response. " "Use this instead of separate summary/history/allocation-history calls to avoid " "multiple engine runs."),
)
async def get_portfolio_report(
    body: PortfolioReportQuery,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> PortfolioReportResponse:
    """Return a complete portfolio report from a single engine run."""
    from backend.app.services.date_sentinel import resolve_date_sentinels  # noqa: PLC0415

    # Resolve min/max sentinels before passing to service
    if body.date_range and body.date_range.has_sentinels():
        body.date_range = await resolve_date_sentinels(body.date_range, current_user.id, session, broker_ids=body.broker_ids)

    service = PortfolioService(session)
    return await service.get_report(user_id=current_user.id, query=body)


@portfolio_router.post(
    "/lots/analysis",
    response_model=LotsAnalysisResponse,
    summary="Bulk FIFO lots analysis",
    description=(
        "Run the FifoLotEngine once for one asset and return all requested analyses "
        "(lot summary, Gantt topology, custody/event history, value/return/price history, "
        "broker and cumulative WAC history) in a single response, converted to target_currency. "
        "Supersedes GET /portfolio/lots for the new lots UI (Gantt, unified table, custody modal, "
        "comparison chart) — the frontend performs no FX conversion, FIFO attribution, or WAC math."
    ),
)
async def get_lots_analysis(
    body: LotsAnalysisQuery,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> LotsAnalysisResponse:
    """Return a bulk FIFO lots analysis from a single FifoLotEngine run."""
    from backend.app.services.date_sentinel import resolve_date_sentinels  # noqa: PLC0415

    # Resolve min/max sentinels before passing to service
    if body.date_range and body.date_range.has_sentinels():
        body.date_range = await resolve_date_sentinels(body.date_range, current_user.id, session, broker_ids=body.broker_ids)

    date_from = body.date_range.start if body.date_range else None
    date_to = body.date_range.end if body.date_range else None

    service = LotsAnalysisService(session)
    try:
        return await service.get_lots_analysis(
            user_id=current_user.id,
            asset_id=body.asset_id,
            broker_ids=body.broker_ids,
            date_from=date_from,
            date_to=date_to,
            target_currency=body.target_currency,
            selected_lot_ids=body.selected_lot_ids,
            requested_analyses=body.requested_analyses,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
