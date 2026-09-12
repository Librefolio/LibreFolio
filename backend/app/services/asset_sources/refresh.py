"""Provider-driven asset price refresh operations."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Any, List

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.app.db.models import (
    Asset,
    AssetProviderAssignment,
    PriceHistory,
)
from backend.app.db.session import get_async_engine
from backend.app.schemas import (
    CHANGED_POINTS_PAYLOAD_CAP,
    FABulkRefreshResponse,
    FAPricePoint,
    FARefreshItem,
    FARefreshResult,
    FAUpsert,
    SyncStatus,
)
from backend.app.services.asset_sources import core
from backend.app.services.asset_sources.core import (
    AssetHistoryStartDate,
    AssetSourceProvider,
)
from backend.app.services.asset_sources.price_store import PriceStoreOperations
from backend.app.services.provider_registry import AssetProviderRegistry
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.decimal_utils import truncate_priceHistory

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class _PreparedRefreshItem:
    assignment_id: int | None
    asset_currency: str
    provider: AssetSourceProvider
    provider_code: str
    provider_params: Any
    identifier: str | None
    identifier_type: str
    start: AssetHistoryStartDate
    end: date_type


@dataclass(frozen=True)
class _FetchedRefreshData:
    prices: list[dict]
    source: str
    events: list[dict]


async def _prepare_refresh_items(  # noqa: C901 — per-item validation maps each rejection to a typed result
    requests: List[FARefreshItem],
    session: AsyncSession,
    bulk_started_ns: int,
) -> tuple[dict[int, _PreparedRefreshItem], list[FARefreshResult]]:
    """Resolve DB-backed refresh inputs without performing writes."""
    asset_ids = [request.asset_id for request in requests]
    request_map = {request.asset_id: request for request in requests}

    assignment_rows = await session.execute(select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(asset_ids)))
    assignment_map = {assignment.asset_id: assignment for assignment in assignment_rows.scalars().all()}

    asset_rows = await session.execute(select(Asset).where(Asset.id.in_(asset_ids)))
    asset_map = {asset.id: asset for asset in asset_rows.scalars().all()}

    resume_ids = [request.asset_id for request in requests if request.date_range.start == "resume"]
    last_price_map: dict[int, date_type] = {}
    if resume_ids:
        last_rows = await session.execute(select(PriceHistory.asset_id, func.max(PriceHistory.date)).where(PriceHistory.asset_id.in_(resume_ids)).group_by(PriceHistory.asset_id))
        last_price_map = {row[0]: row[1] for row in last_rows.all() if row[1] is not None}

    prepared_items: dict[int, _PreparedRefreshItem] = {}
    immediate_results: list[FARefreshResult] = []

    for asset_id in asset_ids:
        request = request_map[asset_id]
        assignment = assignment_map.get(asset_id)
        asset = asset_map.get(asset_id)

        if not asset:
            immediate_results.append(
                FARefreshResult(
                    asset_id=asset_id,
                    status=SyncStatus.FAILED,
                    errors=[f"Asset {asset_id} not found"],
                    elapsed_ms=(time.monotonic_ns() - bulk_started_ns) // 1_000_000,
                )
            )
            continue

        if not assignment:
            immediate_results.append(
                FARefreshResult(
                    asset_id=asset_id,
                    status=SyncStatus.SKIPPED,
                    message="No provider assigned",
                    errors=["No provider assigned for asset"],
                    elapsed_ms=(time.monotonic_ns() - bulk_started_ns) // 1_000_000,
                )
            )
            continue

        provider_code = assignment.provider_code
        provider = AssetProviderRegistry.get_provider_instance(provider_code)
        if not provider:
            immediate_results.append(
                FARefreshResult(
                    asset_id=asset_id,
                    status=SyncStatus.FAILED,
                    provider_used=provider_code,
                    errors=[f"Provider not found: {provider_code}"],
                    elapsed_ms=(time.monotonic_ns() - bulk_started_ns) // 1_000_000,
                )
            )
            continue

        provider_params = assignment.provider_params or {}
        try:
            if isinstance(provider_params, str):
                provider_params = json.loads(provider_params)
        except Exception as exc:
            logger.debug(
                "Failed to decode provider params JSON",
                asset_id=asset_id,
                provider_code=provider_code,
                error=str(exc),
            )

        try:
            provider.validate_params(provider_params)
        except Exception as exc:
            immediate_results.append(
                FARefreshResult(
                    asset_id=asset_id,
                    status=SyncStatus.FAILED,
                    provider_used=provider_code,
                    errors=[f"Invalid provider params: {exc!s}"],
                    elapsed_ms=(time.monotonic_ns() - bulk_started_ns) // 1_000_000,
                )
            )
            continue

        resolved_start = request.date_range.start
        if resolved_start == "resume":
            last_date = last_price_map.get(asset_id)
            resolved_start = last_date + timedelta(days=1) if last_date else "min"

        if isinstance(resolved_start, date_type) and resolved_start > request.date_range.end:
            immediate_results.append(
                FARefreshResult(
                    asset_id=asset_id,
                    status=SyncStatus.SKIPPED,
                    provider_used=provider_code,
                    message="Already up to date",
                    elapsed_ms=(time.monotonic_ns() - bulk_started_ns) // 1_000_000,
                )
            )
            continue

        prepared_items[asset_id] = _PreparedRefreshItem(
            assignment_id=assignment.id,
            asset_currency=asset.currency,
            provider=provider,
            provider_code=provider_code,
            provider_params=provider_params,
            identifier=assignment.identifier,
            identifier_type=assignment.identifier_type,
            start=resolved_start,
            end=request.date_range.end,
        )

    return prepared_items, immediate_results


async def _fetch_refresh_item(  # noqa: C901 — cache gap analysis plus independent history/current fallbacks
    asset_id: int,
    prep: _PreparedRefreshItem,
    semaphore: asyncio.Semaphore,
    semaphore_timeout: int,
) -> tuple[_FetchedRefreshData | None, str | None]:
    """Fetch prices from provider for a single asset (no DB access)."""
    prov = prep.provider
    identifier = prep.identifier
    # Map ProviderInputType (stored in DB) to IdentifierType (expected by plugin methods)
    identifier_type = AssetSourceProvider.map_input_type_to_identifier_type(prep.identifier_type)
    provider_params = prep.provider_params
    provider_code = prep.provider_code
    start = prep.start
    end = prep.end

    try:
        async with asyncio.timeout(semaphore_timeout):
            async with semaphore:
                prices_data = []
                events_data = []
                today = date_type.today()

                # Cache key for this provider+identifier combo.
                # #R3-4: include a hash of `provider_params` so that changing schedule /
                # maturation_frequency / annual_rate (or any other provider param) yields
                # a different key — otherwise the cache would serve stale series (e.g. DAILY
                # points after switching to WEEKLY on a scheduled_investment asset) until
                # the TTL naturally expires.
                params_hash = core._provider_params_hash(provider_params)
                cache_key = (provider_code, identifier, str(prep.identifier_type), params_hash)

                # 1. Fetch historical data (with core cache)
                history_requested = start == "min" or start < today
                if prov.supports_history and history_requested:
                    try:
                        history_end = min(end, today - timedelta(days=1)) if end >= today else end
                        if start == "min" or start <= history_end:
                            cached_dates = {}
                            fetch_start: AssetHistoryStartDate | None = start
                            fetch_end = history_end

                            if start != "min":
                                # Check history cache (smart range)
                                cached_entry, cache_ok = core._asset_history_cache.get(cache_key)
                                if cache_ok and cached_entry:
                                    cached_dates = cached_entry.get("dates", {})
                                    cached_events = cached_entry.get("events", [])
                                    # Determine if we have a gap
                                    if cached_dates:
                                        # Check if requested range is fully covered
                                        needed_dates = set()
                                        d = start
                                        while d <= history_end:
                                            d_iso = d.isoformat()
                                            if d_iso not in cached_dates:
                                                needed_dates.add(d)
                                            d += timedelta(days=1)
                                        if not needed_dates:
                                            # Full cache hit — use cached data
                                            prices_data = list(cached_dates.values())
                                            events_data = cached_events
                                            logger.debug(f"History cache HIT for asset {asset_id} ({len(prices_data)} points)")
                                            fetch_start = None  # skip fetch
                                        else:
                                            # Partial gap — fetch the missing range
                                            fetch_start = min(needed_dates)
                                            fetch_end = max(needed_dates)

                            if fetch_start is not None:
                                hist_data = await core._run_provider_in_thread(
                                    lambda: prov.get_history_value(identifier, identifier_type, provider_params, fetch_start, fetch_end),
                                    timeout=55.0,
                                )
                                if hist_data and hist_data.prices:
                                    fetched_points = [p.model_dump() for p in hist_data.prices]
                                    if start == "min":
                                        cached_dates = {}
                                    # Merge into cached_dates
                                    for p in fetched_points:
                                        d_iso = p["date"].isoformat() if hasattr(p["date"], "isoformat") else str(p["date"])
                                        cached_dates[d_iso] = p
                                    logger.debug(f"Fetched {len(fetched_points)} historical prices for asset {asset_id}")
                                if hist_data and hist_data.events:
                                    events_data = [e.model_dump() for e in hist_data.events]
                                    logger.debug(f"Fetched {len(events_data)} events for asset {asset_id}")

                                # Update cache with merged data
                                core._asset_history_cache.set(cache_key, {"dates": cached_dates, "events": events_data})

                                # Build prices_data from full cached_dates for requested range
                                prices_data = list(cached_dates.values())

                    except Exception as hist_e:
                        logger.warning(f"History fetch failed for asset {asset_id}: {hist_e}")

                # 2. Fetch current value (with core cache)
                if end >= today:
                    try:
                        cached_current, current_ok = core._asset_current_cache.get(cache_key)
                        if current_ok and cached_current:
                            current_data = cached_current
                            logger.debug(f"Current cache HIT for asset {asset_id}")
                        else:
                            current_data = await core._run_provider_in_thread(
                                lambda: prov.get_current_value(identifier, identifier_type, provider_params),
                                timeout=15.0,
                            )
                            if current_data:
                                core._asset_current_cache.set(cache_key, current_data)

                        if current_data and current_data.value:
                            current_price = {
                                "date": current_data.as_of_date or today,
                                "close": current_data.value,
                                "currency": current_data.currency,
                            }
                            prices_data = [p for p in prices_data if p.get("date") != current_price["date"]]
                            prices_data.append(current_price)
                            logger.debug(f"Added current price for asset {asset_id}: {current_data.value}")
                    except Exception as curr_e:
                        logger.warning(f"Current value fetch failed for asset {asset_id}: {curr_e}")

                if not prices_data:
                    return None, "No price data available from provider"

                return (
                    _FetchedRefreshData(
                        prices=prices_data,
                        source=provider_code,
                        events=events_data,
                    ),
                    None,
                )

    except Exception as e:
        return None, str(e)


async def _fetch_refresh_items(
    prepared_items: dict[int, _PreparedRefreshItem],
    concurrency: int,
    semaphore_timeout: int,
) -> tuple[dict[int, _FetchedRefreshData], dict[int, str]]:
    """Fetch every prepared item without touching the database."""
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        _fetch_refresh_item(
            asset_id,
            prepared,
            semaphore,
            semaphore_timeout,
        )
        for asset_id, prepared in prepared_items.items()
    ]
    completed = await asyncio.gather(*tasks) if tasks else []

    fetch_results: dict[int, _FetchedRefreshData] = {}
    fetch_errors: dict[int, str] = {}
    for asset_id, (data, error) in zip(
        prepared_items,
        completed,
        strict=True,
    ):
        if data is not None:
            fetch_results[asset_id] = data
        if error is not None:
            fetch_errors[asset_id] = error
    return fetch_results, fetch_errors


async def _count_actual_price_changes(
    session: AsyncSession,
    asset_id: int,
    price_items: list,
) -> tuple[int, int, list]:
    """
    Compare fetched prices with existing DB prices.

    Returns
    -------
    tuple
        ``(new_count, changed_count, changed_items)`` where
        ``changed_items`` is the subset of ``price_items`` whose dates
        correspond to true inserts or true updates (value changed vs
        the stored row). Used by I-bis #24 to produce the
        ``changed_points`` delta in ``FARefreshResult`` so the
        frontend can refresh the chart without a full re-query.
    """
    if not price_items:
        return 0, 0, []

    dates = [p.date for p in price_items]

    # Load existing prices for these dates
    stmt = select(PriceHistory.date, PriceHistory.close).where(and_(PriceHistory.asset_id == asset_id, PriceHistory.date.in_(dates)))
    result = await session.execute(stmt)
    existing: dict = {row[0]: row[1] for row in result.all()}

    new_count = 0
    changed_count = 0
    changed_items: list = []
    for p in price_items:
        old_close = existing.get(p.date)
        if old_close is None:
            new_count += 1
            changed_items.append(p)
        else:
            # Truncate fetched value to DB precision before comparing
            truncated_new = truncate_priceHistory(Decimal(str(p.close)), "close")
            if float(old_close) != float(truncated_new):
                changed_count += 1
                changed_items.append(p)

    return new_count, changed_count, changed_items


async def _persist_refresh_item(  # noqa: C901 — sequential guarded persist steps, per-step error mapping
    asset_id: int,
    prep: _PreparedRefreshItem,
    remote_data: _FetchedRefreshData | None,
    fetch_error: str | None,
    engine: AsyncEngine,
) -> FARefreshResult:
    """Upsert fetched prices and update assignment in an isolated session."""
    t_start_ns = time.monotonic_ns()
    provider_code = prep.provider_code
    provider = prep.provider
    start = prep.start

    # Check if fetch failed
    if fetch_error is not None:
        elapsed_ms = (time.monotonic_ns() - t_start_ns) // 1_000_000
        return FARefreshResult(
            asset_id=asset_id,
            status=SyncStatus.FAILED,
            provider_used=provider_code,
            errors=[fetch_error],
            elapsed_ms=elapsed_ms,
        )

    if not remote_data:
        elapsed_ms = (time.monotonic_ns() - t_start_ns) // 1_000_000
        return FARefreshResult(
            asset_id=asset_id,
            status=SyncStatus.FAILED,
            provider_used=provider_code,
            errors=["No data available from provider"],
            elapsed_ms=elapsed_ms,
        )

    prices = remote_data.prices
    if not prices:
        elapsed_ms = (time.monotonic_ns() - t_start_ns) // 1_000_000
        return FARefreshResult(
            asset_id=asset_id,
            status=SyncStatus.FAILED,
            provider_used=provider_code,
            errors=["No prices returned from provider"],
            elapsed_ms=elapsed_ms,
        )

    # Convert to FAPricePoint objects — fallback to asset's own currency
    asset_currency = prep.asset_currency

    # #R3-2: Filter out points with currency mismatch BEFORE counting as fetched.
    # A point whose currency differs from the asset's currency is, from the asset's
    # point of view, indistinguishable from "no data available" — the bulk_upsert
    # would reject the whole batch with HTTPException(400) and fetched_count would
    # remain inflated, producing a misleading PARTIAL status ("20↓ 0Δ") instead of
    # a clear FAILED with the real reason.
    errors: list[str] = []
    accepted_prices: list[dict] = []
    mismatch_buckets: dict[str, int] = {}
    for p in prices:
        p_currency = p.get("currency") or asset_currency
        if p_currency != asset_currency:
            mismatch_buckets[p_currency] = mismatch_buckets.get(p_currency, 0) + 1
            continue
        accepted_prices.append(p)
    if mismatch_buckets:
        detail = ", ".join(f"{cnt} {code}" for code, cnt in sorted(mismatch_buckets.items()))
        errors.append(f"{sum(mismatch_buckets.values())} points discarded: currency mismatch " f"(got {detail}, expected {asset_currency})")

    # #R4-1: short-circuit when every fetched point was filtered out for currency mismatch.
    # Building ``FAUpsert(prices=[])`` would raise a raw Pydantic ``min_length`` validation
    # error that ends up surfaced to the user ("List should have at least 1 item after
    # validation, not 0"), instead of the meaningful "N points discarded: currency mismatch …"
    # message we just collected in ``errors``. Returning FAILED here with that message
    # mirrors the "No prices returned from provider" short-circuit above.
    if not accepted_prices and mismatch_buckets:
        elapsed_ms = (time.monotonic_ns() - t_start_ns) // 1_000_000
        return FARefreshResult(
            asset_id=asset_id,
            status=SyncStatus.FAILED,
            provider_used=provider_code,
            points_fetched=0,
            points_changed=0,
            inserted_count=0,
            updated_count=0,
            events_fetched=len(remote_data.events),
            events_changed=0,
            message=errors[0],
            errors=errors,
            elapsed_ms=elapsed_ms,
        )

    price_items = [
        FAPricePoint(
            date=p["date"],
            open=p.get("open"),
            high=p.get("high"),
            low=p.get("low"),
            close=p["close"],
            volume=p.get("volume"),
            currency=p.get("currency") or asset_currency,
        )
        for p in accepted_prices
    ]
    upsert_obj = FAUpsert(asset_id=asset_id, prices=price_items)

    fetched_count = len(accepted_prices)
    inserted_count = 0
    updated_count = 0
    events_fetched_count = len(remote_data.events)
    events_changed_count = 0
    # I-bis #24 — accumulate the actual delta here; None if above cap.
    changed_items_delta: list = []

    # Isolated session for this asset's DB writes
    try:
        async with AsyncSession(engine, expire_on_commit=False) as persist_session:
            # Count actual changes BEFORE upserting (compare with DB)
            if price_items:
                try:
                    new_count, changed_count, changed_items_delta = await _count_actual_price_changes(persist_session, asset_id, price_items)
                except Exception:
                    new_count, changed_count, changed_items_delta = fetched_count, 0, list(price_items)  # Fallback

                try:
                    # Pass the real provider_code so upserted rows are correctly
                    # tagged (see bulk_upsert_prices docstring) instead of the
                    # previous hardcoded "MANUAL", which mislabeled every
                    # scheduler-synced row and left fetched_at always NULL —
                    # silently defeating the portfolio engine's cache-invalidation
                    # fingerprint (COUNT + MAX(fetched_at)) for same-date revisions.
                    upsert_result = await PriceStoreOperations.bulk_upsert_prices([upsert_obj], persist_session, source_plugin_key=provider_code)
                    inserted_count = new_count
                    updated_count = changed_count
                    # Surface OHLC-integrity rejections (bad provider data,
                    # e.g. close outside [low, high]) as a visible warning
                    # instead of a silent undercount in inserted/updated.
                    for r in upsert_result.get("results", []):
                        if "rejected" in (r.get("message") or ""):
                            errors.append(r["message"])
                except Exception as e:
                    errors.append(f"DB upsert failed: {e!s}")
                    # If the upsert failed, no delta is reliable.
                    changed_items_delta = []

            # Upsert asset events (if any)
            events_list = remote_data.events
            if events_list:
                try:
                    assignment_id = prep.assignment_id
                    events_changed_count = (
                        await PriceStoreOperations._upsert_asset_events(
                            persist_session,
                            asset_id,
                            events_list,
                            assignment_id,
                            prep.asset_currency,
                        )
                        or 0
                    )
                except Exception as e:
                    errors.append(f"Event upsert failed: {e!s}")

            # Update last_fetch_at on assignment
            try:
                assign_stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id == asset_id)
                assign_res = await persist_session.execute(assign_stmt)
                fresh_assignment = assign_res.scalar_one_or_none()
                if fresh_assignment:
                    fresh_assignment.last_fetch_at = utcnow()
                    persist_session.add(fresh_assignment)
                    await persist_session.commit()
            except Exception as e:
                # Not critical: price/event persistence result is already committed separately.
                logger.debug("Failed to update provider assignment fetch timestamp", asset_id=asset_id, error=str(e))
    except Exception as e:
        errors.append(f"Persist session error: {e!s}")

    points_changed = inserted_count + updated_count
    elapsed_ms = (time.monotonic_ns() - t_start_ns) // 1_000_000

    # Determine status
    message = None
    if errors:
        status = SyncStatus.FAILED if fetched_count == 0 else SyncStatus.PARTIAL
        # #R3-2: surface the first error as the user-facing message so the FE toast
        # shows a meaningful reason (e.g. "20 points discarded: currency mismatch …")
        # instead of a vague "Sync (partial): 20↓ 0Δ".
        message = errors[0]
    elif fetched_count > 0:
        has_history = provider.supports_history and (start == "min" or start < date_type.today())
        if has_history and fetched_count == 1:
            status = SyncStatus.PARTIAL
            message = "Current value only, history unavailable"
        else:
            status = SyncStatus.OK
    else:
        status = SyncStatus.FAILED
        message = "No data available from provider"

    return FARefreshResult(
        asset_id=asset_id,
        status=status,
        provider_used=provider_code,
        points_fetched=fetched_count,
        points_changed=points_changed,
        inserted_count=inserted_count,
        updated_count=updated_count,
        events_fetched=events_fetched_count,
        events_changed=events_changed_count,
        message=message,
        errors=errors,
        elapsed_ms=elapsed_ms,
        # I-bis #24 — delta payload (None when empty OR above cap).
        changed_points=(changed_items_delta if changed_items_delta and len(changed_items_delta) <= CHANGED_POINTS_PAYLOAD_CAP else None),
    )


async def _persist_refresh_items(
    prepared_items: dict[int, _PreparedRefreshItem],
    fetch_results: dict[int, _FetchedRefreshData],
    fetch_errors: dict[int, str],
    engine: AsyncEngine,
) -> list[FARefreshResult]:
    """Persist fetched items with one isolated session per asset."""
    asset_ids = [asset_id for asset_id in prepared_items if asset_id in fetch_results or asset_id in fetch_errors]
    tasks = [
        _persist_refresh_item(
            asset_id,
            prepared_items[asset_id],
            fetch_results.get(asset_id),
            fetch_errors.get(asset_id),
            engine,
        )
        for asset_id in asset_ids
    ]
    return list(await asyncio.gather(*tasks)) if tasks else []


class RefreshOperations:
    """Provider-driven asset price refresh operations."""

    @staticmethod
    async def bulk_refresh_prices(
        requests: List[FARefreshItem],
        session: AsyncSession,
        concurrency: int = 5,
        semaphore_timeout: int = 60,
    ) -> FABulkRefreshResponse:
        """Refresh prices through explicit prepare, fetch and persist phases."""
        if not requests:
            return FABulkRefreshResponse(
                results=[],
                success_count=0,
                date_range=None,
                total_points_changed=0,
            )

        bulk_started_ns = time.monotonic_ns()
        prepared_items, immediate_results = await _prepare_refresh_items(
            requests,
            session,
            bulk_started_ns,
        )
        fetch_results, fetch_errors = await _fetch_refresh_items(
            prepared_items,
            concurrency,
            semaphore_timeout,
        )
        persist_results = await _persist_refresh_items(
            prepared_items,
            fetch_results,
            fetch_errors,
            get_async_engine(),
        )

        results = immediate_results + persist_results
        return FABulkRefreshResponse(
            results=results,
            success_count=sum(1 for result in results if result.status in (SyncStatus.OK, SyncStatus.PARTIAL)),
            errors=[],
            date_range=requests[0].date_range,
            total_points_changed=sum(result.points_changed for result in results),
        )
