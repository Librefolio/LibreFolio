"""
Portfolio API endpoints for LibreFolio.

Provides read-only portfolio calculations on committed data:
- POST /portfolio/report        — UNIFIED: summary+history+allocation+contribution+data_quality
- POST /portfolio/positions-series — the daily P&L / value series of the chosen positions (#48)
- POST /portfolio/lots/analysis — FifoLotEngine bulk multi-analysis (lots, Gantt, histories, WAC)

Legacy standalone endpoints (/summary, /history, /allocation-history) removed —
all data is available via /report with include_* flags.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.portfolio import (
    LotsAnalysisQuery,
    LotsAnalysisResponse,
    PortfolioPlannerSourceRequest,
    PortfolioPlannerSourceResponse,
    PortfolioReportQuery,
    PortfolioReportResponse,
    PositionsSeriesQuery,
    PositionsSeriesResponse,
)
from backend.app.services.lots_analysis_service import LotsAnalysisService
from backend.app.services.pac_allocator.source.portfolio_allocation_source import (
    PortfolioPlannerSourceAccessError,
    PortfolioPlannerSourceAssetNotFoundError,
    build_portfolio_planner_source,
)
from backend.app.services.portfolio_service import PortfolioService

logger = get_logger(__name__)

portfolio_router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


async def _get_allocation_source_user(
    request: Request,
    session: AsyncSession = Depends(get_session_generator),
) -> User:
    """Reuse standard authentication while marking only its 401 responses no-store."""
    try:
        return await get_current_user(request, session)
    except HTTPException as exc:
        if exc.status_code == 401:
            exc.headers = {
                **(exc.headers or {}),
                "Cache-Control": "no-store",
            }
        raise


# =============================================================================
# PORTFOLIO ENDPOINTS
# =============================================================================


@portfolio_router.post(
    "/allocation-source",
    response_model=PortfolioPlannerSourceResponse,
    summary="Planner domain-copy source",
    description=("Return an authenticated, uncached, read-only snapshot of selected Portfolio, Broker, Asset, saved-price, WAC, and saved-FX facts. The response contains no targets, recommendations, or provider refreshes."),
)
async def get_portfolio_allocation_source(
    body: PortfolioPlannerSourceRequest,
    response: Response,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(_get_allocation_source_user),
) -> PortfolioPlannerSourceResponse:
    """Return explicit domain facts for user-confirmed planner copy actions."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return await build_portfolio_planner_source(
            session,
            user_id=current_user.id,
            request=body,
        )
    except PortfolioPlannerSourceAccessError as exc:
        raise HTTPException(
            status_code=403,
            detail={"code": "portfolio_planner_source_broker_forbidden"},
            headers={"Cache-Control": "no-store"},
        ) from exc
    except PortfolioPlannerSourceAssetNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "portfolio_planner_source_asset_not_found"},
            headers={"Cache-Control": "no-store"},
        ) from exc


@portfolio_router.post(
    "/report",
    response_model=PortfolioReportResponse,
    summary="Unified portfolio report",
    description=("Run the PortfolioCalculationEngine once and return all requested views (summary, history, allocation history, data quality) in a single response. Use this instead of separate summary/history/allocation-history calls to avoid multiple engine runs."),
)
async def get_portfolio_report(
    body: PortfolioReportQuery,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> PortfolioReportResponse:
    """Return a complete portfolio report from a single engine run."""
    from backend.app.services.platform.date_sentinel import resolve_date_sentinels  # noqa: PLC0415

    # Resolve min/max sentinels before passing to service
    if body.date_range and body.date_range.has_sentinels():
        body.date_range = await resolve_date_sentinels(body.date_range, current_user.id, session, broker_ids=body.broker_ids)

    service = PortfolioService(session)
    return await service.get_report(user_id=current_user.id, query=body)


@portfolio_router.post(
    "/positions-series",
    response_model=PositionsSeriesResponse,
    summary="Daily series of the chosen positions",
    description=(
        "The daily series of the positions asked for, and only those: for each calendar day its quantity, market value, cost, "
        "result since the window's start (the Performance table's period P&L at that day) and the percent on the capital deployed, "
        "in the report currency and at the owner's share. A position of a broker the user cannot read comes back empty. The "
        "frontend draws the lines of the positions chart from it and computes nothing."
    ),
)
async def get_positions_series(
    body: PositionsSeriesQuery,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> PositionsSeriesResponse:
    """Return the daily series of the chosen positions from one engine run with the position frames."""
    from backend.app.services.platform.date_sentinel import resolve_date_sentinels  # noqa: PLC0415

    if body.date_range and body.date_range.has_sentinels():
        body.date_range = await resolve_date_sentinels(body.date_range, current_user.id, session, broker_ids=body.broker_ids)

    return await PortfolioService(session).get_positions_series(user_id=current_user.id, query=body)


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
    from backend.app.services.platform.date_sentinel import resolve_date_sentinels  # noqa: PLC0415

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
