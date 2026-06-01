"""
Analytics API endpoints for LibreFolio.

Provides read-only analytics on committed data:
- POST /analytics/wac — WAC time series per (broker, asset)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.analytics import (
    WACAnalyticsRequest,
    WACAnalyticsResponse,
    WACAnalyticsResultItem,
    WACSeriesPoint,
)
from backend.app.services.wac_service import compute_wac_iterative

logger = get_logger(__name__)

analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@analytics_router.post(
    "/wac",
    response_model=WACAnalyticsResponse,
    summary="WAC time series",
    description="Compute WAC (Weighted Average Cost) time series for committed transactions. "
    "Returns point-per-transaction data where WAC changes — useful for chart overlays and P&L.",
)
async def analytics_wac(
    body: WACAnalyticsRequest,
    session: AsyncSession = Depends(get_session_generator),
) -> WACAnalyticsResponse:
    """Compute WAC time series for each (broker, asset) query."""
    results: list[WACAnalyticsResultItem] = []

    for query in body.queries:
        # Determine as_of_date: use query end date or today
        from datetime import date as date_type

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
                    missing_pairs=[],
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

        # If FX errors, return empty series with missing_pairs
        if wac_result.wac_missing_pairs:
            results.append(
                WACAnalyticsResultItem(
                    broker_id=query.broker_id,
                    asset_id=query.asset_id,
                    currency=asset_currency,
                    series=[],
                    missing_pairs=wac_result.wac_missing_pairs,
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
                missing_pairs=[],
            )
        )

    return WACAnalyticsResponse(results=results)

