"""
Portfolio API endpoints for LibreFolio.

Provides read-only portfolio calculations on committed data:
- POST /portfolio/wac           — WAC time series per (broker, asset)
- POST /portfolio/summary       — Aggregated portfolio KPIs, allocations, holdings
- POST /portfolio/history       — Daily cash/invested/NAV series
- GET  /portfolio/asset-history — WAC vs market price series for one asset
- GET  /portfolio/lots          — FIFO open and closed lots for one (broker, asset)
"""

from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import Asset, User
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.portfolio import (
    AllocationHistoryQuery,
    AllocationHistoryResponse,
    AllocationItem,
    AssetHistoryPoint,
    FIFOLotsResponse,
    PortfolioHistoryPoint,
    PortfolioHistoryQuery,
    PortfolioSummary,
    PortfolioSummaryQuery,
    WACAnalyticsRequest,
    WACAnalyticsResponse,
    WACAnalyticsResultItem,
    WACSeriesPoint,
)
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
    "/summary",
    response_model=PortfolioSummary,
    summary="Portfolio summary",
    description="Aggregated portfolio KPIs: net worth, gain/loss, TWRR, MWRR, allocations, holdings.",
)
async def get_portfolio_summary(
    body: PortfolioSummaryQuery,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> PortfolioSummary:
    """Return aggregated portfolio summary for the authenticated user."""
    service = PortfolioService(session)
    return await service.get_summary(
        user_id=current_user.id,
        broker_ids=body.broker_ids,
        include_breakdown=body.include_breakdown,
        target_currency_override=body.target_currency,
    )


@portfolio_router.post(
    "/history",
    response_model=list[PortfolioHistoryPoint],
    summary="Portfolio value history",
    description="Daily time series of cash, invested capital, and NAV for the portfolio.",
)
async def get_portfolio_history(
    body: PortfolioHistoryQuery,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> list[PortfolioHistoryPoint]:
    """Return daily portfolio value series (cash, invested, NAV)."""
    service = PortfolioService(session)
    return await service.get_history(
        user_id=current_user.id,
        broker_ids=body.broker_ids,
        date_from=body.date_range.start if body.date_range else None,
        date_to=body.date_range.end if body.date_range else None,
        target_currency_override=body.target_currency,
    )


@portfolio_router.post(
    "/allocation-history",
    response_model=AllocationHistoryResponse,
    summary="Allocation history",
    description="Time series of portfolio allocation by type, sector, or geography.",
)
async def get_allocation_history(
    body: AllocationHistoryQuery,
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> AllocationHistoryResponse:
    """Return allocation history series for the given dimension."""
    from backend.app.services.portfolio_engine import (  # noqa: PLC0415
        DerivedViewsBuilder,
        PortfolioCalculationEngine,
    )

    engine = PortfolioCalculationEngine(session)
    result = await engine.calculate(
        user_id=current_user.id,
        broker_ids=body.broker_ids,
        date_from=body.date_range.start if body.date_range else None,
        date_to=body.date_range.end if body.date_range else None,
        target_currency=body.target_currency,
    )
    views = DerivedViewsBuilder(result.daily_states, result.target_currency)
    series_dicts = views.build_allocation_history(body.dimension)

    from backend.app.schemas.portfolio import AllocationHistoryPoint  # noqa: PLC0415

    series = [
        AllocationHistoryPoint(
            date=s["date"],
            components=[AllocationItem(**c) for c in s["components"]],
        )
        for s in series_dicts
    ]
    return AllocationHistoryResponse(
        dimension=body.dimension,
        series=series,
    )


@portfolio_router.get(
    "/asset-history",
    response_model=list[AssetHistoryPoint],
    summary="Asset WAC vs market price history",
    description="Time series of WAC (cost basis per unit) vs market price for a specific asset.",
)
async def get_asset_history(
    asset_id: int = Query(..., description="Asset ID"),
    broker_id: Optional[int] = Query(None, description="Optional broker filter"),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> list[AssetHistoryPoint]:
    """Return WAC vs market price series for a specific asset."""
    service = PortfolioService(session)
    return await service.get_asset_history(
        user_id=current_user.id,
        asset_id=asset_id,
        broker_id=broker_id,
    )


@portfolio_router.get(
    "/lots",
    response_model=FIFOLotsResponse,
    summary="FIFO lots for an asset",
    description="Open and closed FIFO lots for a specific asset in a specific broker.",
)
async def get_fifo_lots(
    broker_id: int = Query(..., description="Broker ID"),
    asset_id: int = Query(..., description="Asset ID"),
    session: AsyncSession = Depends(get_session_generator),
    current_user: User = Depends(get_current_user),
) -> FIFOLotsResponse:
    """Return FIFO open and closed lots for a (broker, asset) pair."""
    service = PortfolioService(session)
    return await service.get_lots(
        user_id=current_user.id,
        broker_id=broker_id,
        asset_id=asset_id,
    )
