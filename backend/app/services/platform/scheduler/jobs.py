"""Scheduler jobs — current-price refresh and history sync.

An item a provider's pause refused (``error_code == "RATE_LIMITED"``, whatever its status or value) is deferred:
neither ok nor failed. The job's state counts it apart and records ``retry_at``, the end of the shortest pause, when
the scheduler retries the job before its regular round (``scheduler.py``, release 1.3, Z7b).

The history sync covers the lookback horizon, and reaches further back for an asset or a pair whose last saved value
is older, at most ``HISTORY_CATCH_UP_MAX_DAYS``: a server that was off, asleep or blocked for longer than the horizon
fills its gap (release 1.3, Z-5).
"""

import json
import time as time_module
from datetime import UTC, date, datetime, timedelta

import structlog
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetProviderAssignment, FxConversionRoute, FxRate, PriceHistory
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import DateRangeModel
from backend.app.schemas.refresh import FARefreshItem, SyncStatus
from backend.app.services.assets.manager import AssetSourceManager
from backend.app.services.fx.sync import sync_pairs_bulk
from backend.app.services.platform.scheduler.joblog import (
    append_entry,
    build_current_price_entry,
    build_history_sync_entry,
)
from backend.app.services.platform.scheduler.state import JobState, SchedulerState

logger = structlog.get_logger(__name__)


#: The ``error_code`` of an item a provider's pause refused: the item is deferred, neither ok nor failed.
RATE_LIMITED = "RATE_LIMITED"

#: The furthest back, in days, a history sync reaches to fill the gap of an asset or a pair behind the horizon: the
#: lookback horizon's own maximum (``scheduler_history_sync_horizon_days``, 1–365).
HISTORY_CATCH_UP_MAX_DAYS = 365


def _classify_job_status(ok_count: int, total_count: int, deferred_count: int = 0) -> str:
    """Classify a job's status from its item counts: ``ok`` when every item succeeded, ``error`` when none did and none
    was deferred, ``partial`` otherwise. Deferred items (a provider's pause) are neither ok nor failed."""
    if total_count == 0 or ok_count == total_count:
        return "ok"
    if ok_count == 0 and deferred_count == 0:
        return "error"
    return "partial"


def _is_deferred(item: object) -> bool:
    return getattr(item, "error_code", None) == RATE_LIMITED


def _retry_at(deferred: list, now: datetime) -> str | None:
    """When the deferred items may be retried: now plus the shortest pause among those that know theirs."""
    waits = [wait for wait in (getattr(item, "retry_after", None) for item in deferred) if wait is not None]
    if not waits:
        return None
    return (now + timedelta(seconds=min(waits))).isoformat()


def _history_sync_start(today: date, horizon_days: int, last_saved: date | None) -> date:
    """Where the history sync of an asset or a pair starts (release 1.3, Z-5).

    The lookback horizon, or the day after the last saved value when that is older: never more than
    ``HISTORY_CATCH_UP_MAX_DAYS`` back, and never after the horizon. Without a saved value the horizon stays: fetching
    a whole history remains a manual sync.
    """
    horizon_start = today - timedelta(days=horizon_days)
    if last_saved is None:
        return horizon_start
    resume = last_saved + timedelta(days=1)
    if resume >= horizon_start:
        return horizon_start
    return max(resume, min(horizon_start, today - timedelta(days=HISTORY_CATCH_UP_MAX_DAYS)))


async def _last_price_dates(session: AsyncSession, asset_ids: list[int]) -> dict[int, date]:
    """The date of each asset's last saved price, for the assets that have one."""
    if not asset_ids:
        return {}
    statement = select(PriceHistory.asset_id, func.max(PriceHistory.date)).where(PriceHistory.asset_id.in_(asset_ids)).group_by(PriceHistory.asset_id)
    rows = (await session.execute(statement)).all()
    return {asset_id: last for asset_id, last in rows if last is not None}


async def _last_fx_dates(session: AsyncSession, pairs: list[str]) -> dict[str, date]:
    """The date of each pair's last saved rate, keyed by the slug as given.

    ``FxRate`` keeps a pair in alphabetical order (``base < quote``), so ``USD-EUR`` reads the rows of ``EUR-USD``.
    """
    keys = {pair: tuple(sorted(parts)) for pair in pairs if len(parts := pair.split("-")) == 2}
    if not keys:
        return {}
    conditions = [and_(FxRate.base == base, FxRate.quote == quote) for base, quote in sorted(set(keys.values()))]
    statement = select(FxRate.base, FxRate.quote, func.max(FxRate.date)).where(or_(*conditions)).group_by(FxRate.base, FxRate.quote)
    rows = (await session.execute(statement)).all()
    last_by_key = {(base, quote): last for base, quote, last in rows if last is not None}
    return {pair: last_by_key[key] for pair, key in keys.items() if key in last_by_key}


async def run_current_price_refresh(state: SchedulerState) -> None:
    """Fetch current prices for all active assets with assigned providers."""
    t_start = time_module.monotonic()
    engine = get_async_engine()

    async with AsyncSession(engine) as session:
        stmt = select(Asset.id, Asset.display_name, Asset.icon_url).join(AssetProviderAssignment, Asset.id == AssetProviderAssignment.asset_id).where(Asset.active == True)  # noqa: E712 — SQLAlchemy expression
        result = await session.execute(stmt)
        rows = result.all()
        asset_ids = [r[0] for r in rows]
        asset_names: dict[int, str] = {r[0]: r[1] for r in rows}
        asset_icons: dict[int, str | None] = {r[0]: r[2] for r in rows}

        if not asset_ids:
            # An empty asset list is not a reason to stay silent. Returning here left
            # neither the state nor a log entry behind, so the scheduler panel kept
            # showing the *previous* run: "it ran and found nothing to do" was
            # indistinguishable from "it stopped running". run_history_sync has always
            # written its entry in this same situation — the two jobs now agree.
            logger.debug("Scheduler: no active assets to refresh")
            results: list = []
        else:
            # Call service layer (includes F.2/F.3 OHLC upsert)
            results = await AssetSourceManager.get_current_prices_bulk(asset_ids, session, concurrency=3)

    duration = time_module.monotonic() - t_start
    deferred = [r for r in results if _is_deferred(r)]
    ok_count = sum(1 for r in results if not _is_deferred(r) and r.value is not None)
    err_count = len(results) - ok_count - len(deferred)
    status = _classify_job_status(ok_count, len(results), len(deferred))
    retry_at = _retry_at(deferred, datetime.now(UTC))

    state.current_price = JobState(
        last_run_at=datetime.now().astimezone().isoformat(),
        last_duration_s=round(duration, 2),
        last_status=status,
        last_items_ok=ok_count,
        last_items_err=err_count,
        last_error=None,
        last_items_deferred=len(deferred),
        retry_at=retry_at,
    )

    # Write detailed job log entry
    entry = build_current_price_entry(results, asset_names, round(duration, 2), status, asset_icons=asset_icons, retry_at=retry_at)
    append_entry(entry)

    logger.info(
        "Scheduler: current-price refresh",
        ok=ok_count,
        errors=err_count,
        deferred=len(deferred),
        retry_at=retry_at,
        duration_s=round(duration, 1),
    )


async def run_history_sync(state: SchedulerState, horizon_days: int = 14) -> None:
    """Sync historical prices for active assets + all FX routes.

    Each asset, and the FX pairs together, start at the horizon, or further back when their last saved value is older
    (``_history_sync_start``): a server that was off, asleep or blocked for longer than the horizon fills its gap.
    """
    t_start = time_module.monotonic()
    engine = get_async_engine()
    today = date.today()
    horizon_start = today - timedelta(days=horizon_days)

    asset_results_list: list = []
    fx_results_list: list = []
    asset_names: dict[int, str] = {}
    last_price_dates: dict[int, date] = {}
    fx_starts: list[date] = []

    # --- Asset history sync ---
    async with AsyncSession(engine) as session:
        stmt = select(Asset.id, Asset.display_name, Asset.icon_url).join(AssetProviderAssignment, Asset.id == AssetProviderAssignment.asset_id).where(Asset.active == True)  # noqa: E712
        result = await session.execute(stmt)
        rows = result.all()
        asset_ids = [r[0] for r in rows]
        asset_names = {r[0]: r[1] for r in rows}
        asset_icons: dict[int, str | None] = {r[0]: r[2] for r in rows}
        if asset_ids:
            last_price_dates = await _last_price_dates(session, asset_ids)

    asset_starts = {aid: _history_sync_start(today, horizon_days, last_price_dates.get(aid)) for aid in asset_ids}
    if asset_ids:
        refresh_items = [
            FARefreshItem(
                asset_id=aid,
                date_range=DateRangeModel(start=asset_starts[aid], end=today),
            )
            for aid in asset_ids
        ]

        async with AsyncSession(engine) as session:
            response = await AssetSourceManager.bulk_refresh_prices(refresh_items, session, concurrency=3)
            asset_results_list = list(response.results)

    # --- FX history sync ---
    async with AsyncSession(engine) as session:
        route_stmt = select(FxConversionRoute)
        route_result = await session.execute(route_stmt)
        routes = route_result.scalars().all()

        pairs_set: set[str] = set()
        for route in routes:
            # Skip MANUAL routes — they are user-managed, not auto-synced
            try:
                steps = json.loads(route.chain_steps)
                if any(s.get("provider", "").upper() == "MANUAL" for s in steps):
                    continue
            except (json.JSONDecodeError, TypeError):
                pass
            slug = f"{route.base}-{route.quote}"
            pairs_set.add(slug)

        if pairs_set:
            pairs_list = sorted(pairs_set)
            last_fx_dates = await _last_fx_dates(session, pairs_list)
            fx_starts = [_history_sync_start(today, horizon_days, last_fx_dates.get(pair)) for pair in pairs_list]
            # One call for every pair: the providers fetch by currency, so a pair behind widens the days, not the requests.
            fx_response = await sync_pairs_bulk(session, pairs_list, (min(fx_starts), today))
            fx_results_list = list(fx_response.results)

    assets_behind = sum(1 for start in asset_starts.values() if start < horizon_start)
    fx_pairs_behind = sum(1 for start in fx_starts if start < horizon_start)
    if assets_behind or fx_pairs_behind:
        logger.info(
            "Scheduler: history sync reaches back",
            assets_behind=assets_behind,
            fx_pairs_behind=fx_pairs_behind,
            earliest_start=min([*asset_starts.values(), *fx_starts]).isoformat(),
        )

    duration = time_module.monotonic() - t_start
    asset_deferred = [r for r in asset_results_list if _is_deferred(r)]
    fx_deferred = [r for r in fx_results_list if _is_deferred(r)]
    asset_ok = sum(1 for r in asset_results_list if not _is_deferred(r) and r.status == SyncStatus.OK)
    fx_ok = sum(1 for r in fx_results_list if not _is_deferred(r) and r.status == SyncStatus.OK)
    asset_err = len(asset_results_list) - asset_ok - len(asset_deferred)
    fx_err = len(fx_results_list) - fx_ok - len(fx_deferred)
    total_ok = asset_ok + fx_ok
    total_items = len(asset_results_list) + len(fx_results_list)
    deferred_count = len(asset_deferred) + len(fx_deferred)
    status = _classify_job_status(total_ok, total_items, deferred_count)
    retry_at = _retry_at(asset_deferred + fx_deferred, datetime.now(UTC))

    state.history_sync = JobState(
        last_run_at=datetime.now().astimezone().isoformat(),
        last_duration_s=round(duration, 2),
        last_status=status,
        last_items_ok=total_ok,
        last_items_err=total_items - total_ok - deferred_count,
        last_error=None,
        last_items_deferred=deferred_count,
        retry_at=retry_at,
    )

    # Write detailed job log entry
    entry = build_history_sync_entry(
        asset_results_list,
        fx_results_list,
        asset_names,
        round(duration, 2),
        status,
        asset_icons=asset_icons,
        retry_at=retry_at,
    )
    append_entry(entry)

    logger.info(
        "Scheduler: history sync",
        assets_ok=asset_ok,
        assets_err=asset_err,
        fx_ok=fx_ok,
        fx_err=fx_err,
        deferred=deferred_count,
        retry_at=retry_at,
        duration_s=round(duration, 1),
    )
