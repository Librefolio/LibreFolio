"""Scheduler jobs — current-price refresh and history sync."""

import time as time_module
from datetime import date, datetime, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetProviderAssignment, FxConversionRoute
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.refresh import FARefreshItem
from backend.app.services.asset_source import AssetSourceManager
from backend.app.services.fx import sync_pairs_bulk
from backend.app.services.scheduler.joblog import (
    append_entry,
    build_current_price_entry,
    build_history_sync_entry,
)
from backend.app.services.scheduler.state import JobState, SchedulerState

logger = structlog.get_logger(__name__)


async def run_current_price_refresh(state: SchedulerState) -> None:
    """Fetch current prices for all active assets with assigned providers."""
    t_start = time_module.monotonic()
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        stmt = (
            select(Asset.id, Asset.display_name)
            .join(AssetProviderAssignment, Asset.id == AssetProviderAssignment.asset_id)
            .where(Asset.active == True)  # noqa: E712 — SQLAlchemy expression
        )
        result = await session.execute(stmt)
        rows = result.all()
        asset_ids = [r[0] for r in rows]
        asset_names: dict[int, str] = {r[0]: r[1] for r in rows}

        if not asset_ids:
            logger.debug("Scheduler: no active assets to refresh")
            return

        # Call service layer (includes F.2/F.3 OHLC upsert)
        results = await AssetSourceManager.get_current_prices_bulk(
            asset_ids, session, concurrency=3
        )

    duration = time_module.monotonic() - t_start
    ok_count = sum(1 for r in results if r.value is not None)
    err_count = len(results) - ok_count
    status = "ok" if err_count == 0 else "partial"

    state.current_price = JobState(
        last_run_at=datetime.now().astimezone().isoformat(),
        last_duration_s=round(duration, 2),
        last_status=status,
        last_items_ok=ok_count,
        last_items_err=err_count,
        last_error=None,
    )

    # Write detailed job log entry
    entry = build_current_price_entry(results, asset_names, round(duration, 2), status)
    append_entry(entry)

    logger.info(
        "Scheduler: current-price refresh",
        ok=ok_count,
        errors=err_count,
        duration_s=round(duration, 1),
    )


async def run_history_sync(state: SchedulerState, horizon_days: int = 14) -> None:
    """Sync historical prices for active assets + all FX routes."""
    t_start = time_module.monotonic()
    engine = get_async_engine()
    today = date.today()
    start_date = today - timedelta(days=horizon_days)

    asset_ok = 0
    asset_err = 0
    fx_ok = 0
    fx_err = 0
    asset_results_list: list = []
    fx_results_list: list = []
    asset_names: dict[int, str] = {}

    # --- Asset history sync ---
    async with AsyncSession(engine) as session:
        stmt = (
            select(Asset.id, Asset.display_name)
            .join(AssetProviderAssignment, Asset.id == AssetProviderAssignment.asset_id)
            .where(Asset.active == True)  # noqa: E712
        )
        result = await session.execute(stmt)
        rows = result.all()
        asset_ids = [r[0] for r in rows]
        asset_names = {r[0]: r[1] for r in rows}

    if asset_ids:
        refresh_items = [
            FARefreshItem(
                asset_id=aid,
                date_range=DateRangeModel(start=start_date, end=today),
            )
            for aid in asset_ids
        ]

        async with AsyncSession(engine) as session:
            response = await AssetSourceManager.bulk_refresh_prices(
                refresh_items, session, concurrency=3
            )
            asset_ok = response.success_count
            asset_err = len(response.results) - response.success_count
            asset_results_list = list(response.results)

    # --- FX history sync ---
    async with AsyncSession(engine) as session:
        route_stmt = select(FxConversionRoute)
        route_result = await session.execute(route_stmt)
        routes = route_result.scalars().all()

        pairs_set: set[str] = set()
        for route in routes:
            slug = f"{route.base}-{route.quote}"
            pairs_set.add(slug)

        if pairs_set:
            pairs_list = sorted(pairs_set)
            fx_response = await sync_pairs_bulk(
                session, pairs_list, (start_date, today)
            )
            fx_ok = sum(1 for r in fx_response.results if r.status == "ok")
            fx_err = len(fx_response.results) - fx_ok
            fx_results_list = list(fx_response.results)

    duration = time_module.monotonic() - t_start
    status = "ok" if (asset_err + fx_err) == 0 else "partial"

    state.history_sync = JobState(
        last_run_at=datetime.now().astimezone().isoformat(),
        last_duration_s=round(duration, 2),
        last_status=status,
        last_items_ok=asset_ok + fx_ok,
        last_items_err=asset_err + fx_err,
        last_error=None,
    )

    # Write detailed job log entry
    entry = build_history_sync_entry(
        asset_results_list, fx_results_list, asset_names, round(duration, 2), status
    )
    append_entry(entry)

    logger.info(
        "Scheduler: history sync",
        assets_ok=asset_ok,
        assets_err=asset_err,
        fx_ok=fx_ok,
        fx_err=fx_err,
        duration_s=round(duration, 1),
    )
