"""Provider-driven asset price refresh operations."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
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
from backend.app.db.precision import truncate_priceHistory
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
from backend.app.services.assets import core
from backend.app.services.assets.base import (
    AssetHistoryStartDate,
    AssetRateLimitedError,
    AssetSourceProvider,
)
from backend.app.services.assets.event_store import EventStoreOperations
from backend.app.services.assets.price_store import PriceStoreOperations, _unstorable_provider_point, storable_current_value, unstorable_quote_reason
from backend.app.utils.date_range_limits import range_span_floor, stored_date_bounds
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.exchange_dates import LEGACY_UTC_DATES, LEGACY_UTC_PROVIDER, exchange_zone, local_date_of_legacy_utc_date

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
    #: Z-33: the assignment still holds the mark of migration 011 and its provider is the one whose rows an older version
    #: dated by UTC: this refresh checks them once, against the provider's full history
    legacy_check: bool = False
    #: The assignment's last fetch before this refresh (UTC): the old code had fetched no bar after the day before it
    last_fetch_at: datetime | None = None


@dataclass(frozen=True)
class _FetchedRefreshData:
    prices: list[dict]
    source: str
    events: list[dict]
    #: Reasons the result reports beside its prices: a refused current value (X-R51)
    notes: tuple[str, ...] = ()
    #: The quote currency as the provider reported it with its history (Yahoo's ``GBp``), kept on the assignment (Z-32)
    reported_currency: str | None = None
    #: The exchange's IANA timezone the provider reported (its history's, else its current value's) (Z-33)
    exchange_timezone: str | None = None
    #: Z-33's one-time check only: the session dates of the provider's full history (None: no calendar fetched)
    session_dates: frozenset[date_type] | None = None
    #: Z-33's one-time check only: the (date, upper-case type) of the events of the provider's full history
    fresh_events: frozenset[tuple[date_type, str]] = frozenset()


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
        provider = await core.configured_provider(provider_code)
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
            legacy_check=assignment.exchange_timezone == LEGACY_UTC_DATES and provider_code == LEGACY_UTC_PROVIDER,
            last_fetch_at=assignment.last_fetch_at,
        )

    return prepared_items, immediate_results


async def _fetch_refresh_item(  # noqa: C901 — cache gap analysis plus independent history/current fallbacks
    asset_id: int,
    prep: _PreparedRefreshItem,
    semaphore: asyncio.Semaphore,
    semaphore_timeout: int,
) -> tuple[_FetchedRefreshData | None, str | None, AssetRateLimitedError | None]:
    """Fetch prices from provider for a single asset (no DB access).

    Returns the data (or None), the error (or None), and the refusal for too many requests met on the way, if any: a
    paused provider fails the item, or leaves it partial, and the result tells when to try again (``retry_after``).
    """
    refusal: AssetRateLimitedError | None = None
    refused_note: str | None = None  # a current value no price column keeps (X-R51)
    prov = prep.provider
    identifier = prep.identifier
    # Map ProviderInputType (stored in DB) to IdentifierType (expected by plugin methods)
    identifier_type = AssetSourceProvider.map_input_type_to_identifier_type(prep.identifier_type)
    provider_params = prep.provider_params
    provider_code = prep.provider_code
    # The part of the provider a pause after «too many requests» applies to (the host of a scraped site)
    cooldown_scope = core.cooldown_scope_for(prov, identifier, identifier_type, provider_params)
    start = prep.start
    end = prep.end

    try:
        async with asyncio.timeout(semaphore_timeout):
            async with semaphore:
                prices_data = []
                events_data = []
                reported_currency: str | None = None  # the provider's own quote currency (Z-32)
                exchange_timezone: str | None = None  # the exchange's timezone (Z-33)
                session_dates: frozenset[date_type] | None = None  # Z-33: the one-time check's calendar
                fresh_events: frozenset[tuple[date_type, str]] = frozenset()
                today = date_type.today()

                # Cache key for this provider+identifier combo.
                # #R3-4: include a hash of `provider_params` so that changing schedule /
                # maturation_frequency / annual_rate (or any other provider param) yields
                # a different key — otherwise the cache would serve stale series (e.g. DAILY
                # points after switching to WEEKLY on a scheduled_investment asset) until
                # the TTL naturally expires.
                # The provider's settings are part of the key too: other settings can give other prices. One key for
                # every reader, writer and drop of these caches (core.asset_cache_key).
                cache_key = core.asset_cache_key(provider_code, identifier, prep.identifier_type, provider_params, core.settings_cache_part(prov))

                # 0. Z-33: the one-time check of an assignment an older version dated by UTC reads the provider's full
                # history once, up to today, past the cache: the calendar of sessions and events the check needs, and the
                # data of the asked range, the only part written (the history call of step 1 is not made)
                if prep.legacy_check and prov.supports_history:
                    try:
                        calendar = await core.call_provider(prov, lambda: prov.get_history_value(identifier, identifier_type, provider_params, "min", today), timeout=55.0, scope=cooldown_scope)
                        if calendar is not None and calendar.prices:
                            session_dates = frozenset(point.date for point in calendar.prices)
                            fresh_events = frozenset((event.date, str(event.type).strip().upper()) for event in calendar.events)
                            exchange_timezone = getattr(calendar, "exchange_timezone", None) or exchange_timezone
                            reported_currency = getattr(calendar, "currency", None) or reported_currency
                            if start == "min" or start < today:
                                # The asked range, as step 1 would have fetched it: prices up to yesterday, events up to today
                                history_end = min(end, today - timedelta(days=1)) if end >= today else end
                                call_end = today if end >= today else end
                                prices_data = [point.model_dump() for point in calendar.prices if (start == "min" or point.date >= start) and point.date <= history_end]
                                events_data = [event.model_dump() for event in calendar.events if (start == "min" or event.date >= start) and event.date <= call_end]
                    except Exception as calendar_e:
                        refusal = _refusal_of(calendar_e, refusal)
                        logger.warning(f"Full-history calendar fetch failed for asset {asset_id}: {calendar_e}")

                # 1. Fetch historical data (with core cache)
                history_requested = start == "min" or start < today
                if prov.supports_history and history_requested and not prep.legacy_check:
                    try:
                        # Prices stop at yesterday: today's close is not in yet, and today's value comes from
                        # get_current_value below. Events do not: a date announced for today (a dividend, a split) is a
                        # fact, so the call asks up to today and today's prices are dropped before the cache and the
                        # write (X-R12). The same calls as before: only their end moves to today.
                        history_end = min(end, today - timedelta(days=1)) if end >= today else end
                        call_end = today if end >= today else end
                        if start == "min" or start <= history_end:
                            cached_dates = {}
                            fetch_start: AssetHistoryStartDate | None = start
                            fetch_end = call_end

                            if start != "min":
                                # Check history cache (smart range)
                                cached_entry, cache_ok = core._asset_history_cache.get(cache_key)
                                if cache_ok and cached_entry:
                                    cached_dates = cached_entry.get("dates", {})
                                    cached_events = cached_entry.get("events", [])
                                    reported_currency = cached_entry.get("currency")
                                    exchange_timezone = exchange_timezone or cached_entry.get("exchange_timezone")
                                    # Determine if we have a gap
                                    if cached_dates:
                                        # Check if requested range is fully covered
                                        needed_dates = set()
                                        # X-R55: the walk covers RANGE_SPAN_LIMIT_DAYS before history_end at most. An
                                        # older start counts as missing, with the day before the floor, so the fetch
                                        # still asks from the requested start.
                                        walk_floor = range_span_floor(history_end)
                                        if start < walk_floor:
                                            needed_dates.update((start, walk_floor - timedelta(days=1)))
                                        d = max(start, walk_floor)
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
                                            # Partial gap — fetch the missing range (up to today when it is asked, for
                                            # today's events)
                                            fetch_start = min(needed_dates)
                                            fetch_end = call_end if end >= today else max(needed_dates)

                            if fetch_start is not None:
                                hist_data = await core.call_provider(
                                    prov,
                                    lambda: prov.get_history_value(identifier, identifier_type, provider_params, fetch_start, fetch_end),
                                    timeout=55.0,
                                    scope=cooldown_scope,
                                )
                                if hist_data and hist_data.prices:
                                    fetched_points = [p.model_dump() for p in hist_data.prices]
                                    if start == "min":
                                        cached_dates = {}
                                    # Merge into cached_dates: prices up to history_end only (today's comes from the
                                    # current value; a history point dated today would not be a close yet)
                                    last_price_day = history_end.isoformat()
                                    for p in fetched_points:
                                        d_iso = p["date"].isoformat() if hasattr(p["date"], "isoformat") else str(p["date"])
                                        if d_iso > last_price_day:
                                            continue
                                        cached_dates[d_iso] = p
                                    logger.debug(f"Fetched {len(fetched_points)} historical prices for asset {asset_id}")
                                if hist_data and hist_data.events:
                                    events_data = [e.model_dump() for e in hist_data.events]
                                    logger.debug(f"Fetched {len(events_data)} events for asset {asset_id}")
                                # Z-32: the quote currency as the provider reported it (not normalized: Yahoo's GBp)
                                if hist_data and getattr(hist_data, "currency", None):
                                    reported_currency = hist_data.currency
                                # Z-33: the exchange's timezone the history was dated in (read with getattr, as the currency:
                                # a plugin may answer with any object carrying prices and events)
                                if hist_data and getattr(hist_data, "exchange_timezone", None):
                                    exchange_timezone = hist_data.exchange_timezone

                                # Update cache with merged data (the reported currency and timezone too, for a later full hit)
                                core._asset_history_cache.set(cache_key, {"dates": cached_dates, "events": events_data, "currency": reported_currency, "exchange_timezone": exchange_timezone})

                                # Build prices_data from full cached_dates for requested range
                                prices_data = list(cached_dates.values())

                    except Exception as hist_e:
                        refusal = _refusal_of(hist_e, refusal)
                        logger.warning(f"History fetch failed for asset {asset_id}: {hist_e}")

                # 2. Fetch current value (with core cache)
                if end >= today:
                    try:
                        cached_current, current_ok = core._asset_current_cache.get(cache_key)
                        if current_ok and cached_current:
                            current_data = storable_current_value(cached_current, asset_id, provider_code)
                            logger.debug(f"Current cache HIT for asset {asset_id}")
                        else:
                            fetched_current = await core.call_provider(prov, lambda: prov.get_current_value(identifier, identifier_type, provider_params), timeout=15.0, scope=cooldown_scope)
                            # As the price columns keep it: a current value they cannot keep is neither cached nor added
                            # as today's price, and the current-price path serves the cached one as stored (X-R40, W-B62)
                            current_data = storable_current_value(fetched_current, asset_id, provider_code)
                            if current_data:
                                core._asset_current_cache.set(cache_key, current_data)
                            elif fetched_current is not None:
                                # Refused: the result says why, as the upsert did when the value reached it (X-R51)
                                refused_note = unstorable_quote_reason(fetched_current.value)

                        # Z-33: the exchange's timezone from the current value when the history gave none
                        if current_data is not None and exchange_timezone is None and getattr(current_data, "exchange_timezone", None):
                            exchange_timezone = current_data.exchange_timezone
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
                        refusal = _refusal_of(curr_e, refusal)
                        logger.warning(f"Current value fetch failed for asset {asset_id}: {curr_e}")

                if not prices_data:
                    return None, (refusal.message if refusal is not None else (refused_note or "No price data available from provider")), refusal

                return (
                    _FetchedRefreshData(
                        prices=prices_data,
                        source=provider_code,
                        events=events_data,
                        notes=(refused_note,) if refused_note else (),
                        reported_currency=reported_currency,
                        exchange_timezone=exchange_timezone,
                        session_dates=session_dates,
                        fresh_events=fresh_events,
                    ),
                    None,
                    refusal,
                )

    except Exception as e:
        return None, str(e), _refusal_of(e, refusal)


async def _fetch_refresh_items(
    prepared_items: dict[int, _PreparedRefreshItem],
    concurrency: int,
    semaphore_timeout: int,
) -> tuple[dict[int, _FetchedRefreshData], dict[int, str], dict[int, AssetRateLimitedError]]:
    """Fetch every prepared item without touching the database; the third map holds the refusals for too many requests."""
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
    fetch_refusals: dict[int, AssetRateLimitedError] = {}
    for asset_id, (data, error, refusal) in zip(
        prepared_items,
        completed,
        strict=True,
    ):
        if data is not None:
            fetch_results[asset_id] = data
        if error is not None:
            fetch_errors[asset_id] = error
        if refusal is not None:
            fetch_refusals[asset_id] = refusal
    return fetch_results, fetch_errors, fetch_refusals


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


def _server_date(moment: datetime | None) -> date_type | None:
    """The server's local date of a stored UTC moment (SQLite gives it back naive), as ``date.today()`` reads dates."""
    if moment is None:
        return None
    return (moment if moment.tzinfo is not None else moment.replace(tzinfo=UTC)).astimezone().date()


async def _settle_exchange_timezone(engine: AsyncEngine, asset_id: int, prep: _PreparedRefreshItem, remote_data: _FetchedRefreshData) -> str | None:
    """Z-33: the exchange timezone of the asset's assignment, settled before the refresh writes anything.

    The one-time check (``prep.legacy_check``: the mark of migration 011 on the provider whose rows an older version
    dated by UTC) moves those dates, never their values, in one transaction with the timezone it stores (which clears
    the mark):

    - a price of the provider moves from S to S+1 when the rule says so (``local_date_of_legacy_utc_date``), the
      provider's full history has a session on S+1, and S is at most two days before the assignment's last fetch: the
      old code had fetched no bar after the day before it, so a later row is a current value, already on its day;
    - an event of the assignment moves when the rule says so and the full history has an event of its type on S+1 and
      none on S (``EventStoreOperations.redate_provider_events``: merges, and a SPLIT's ADJUSTMENT rows on S).

    Without a full history or a timezone the mark stays and the refresh writes nothing: the returned message says why.
    Otherwise a reported timezone is stored (never over the mark of another provider's assignment). Returns the
    message of a refresh that must write nothing, else None.
    """
    if prep.assignment_id is None:
        return None
    zone = exchange_zone(remote_data.exchange_timezone)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        assignment = await session.get(AssetProviderAssignment, prep.assignment_id)
        if assignment is None:
            return None
        if prep.legacy_check:
            sessions = remote_data.session_dates
            if zone is None or not sessions:
                return "Nothing written: the stored dates await their one-time check, and the provider gave no full history or exchange timezone"
            last_day = _server_date(prep.last_fetch_at)

            def price_target(stored: date_type) -> date_type | None:
                target = local_date_of_legacy_utc_date(stored, zone)
                if target == stored or target not in sessions or last_day is None or stored > last_day - timedelta(days=2):
                    return None
                return target

            def event_target(stored: date_type, kind: str) -> date_type | None:
                target = local_date_of_legacy_utc_date(stored, zone)
                if target == stored or (target, kind) not in remote_data.fresh_events or (stored, kind) in remote_data.fresh_events:
                    return None
                return target

            prices_moved, prices_dropped = await PriceStoreOperations.redate_provider_rows(session, asset_id, prep.provider_code, price_target)
            events_moved, events_merged = await EventStoreOperations.redate_provider_events(session, asset_id, assignment.id, event_target)
            first_session = min(sessions)
            before_calendar = (await session.execute(select(func.count()).select_from(PriceHistory).where(PriceHistory.asset_id == asset_id, PriceHistory.source_plugin_key == prep.provider_code, PriceHistory.date < first_session - timedelta(days=1)))).scalar_one()
            assignment.exchange_timezone = zone.key
            await session.commit()
            logger.info(
                "Stored dates checked against the exchange calendar",
                asset_id=asset_id,
                provider=prep.provider_code,
                timezone=zone.key,
                prices_moved=prices_moved,
                prices_dropped=prices_dropped,
                events_moved=events_moved,
                events_merged=events_merged,
                rows_before_calendar=before_calendar,
            )
            return None
        if zone is not None and assignment.exchange_timezone not in (zone.key, LEGACY_UTC_DATES):
            assignment.exchange_timezone = zone.key
            await session.commit()
    return None


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

    # Z-33: before anything is written, the exchange timezone; the one-time check of the dates an older version stored
    # by UTC runs here, or, without a calendar, lets nothing be written. A check that raises fails this asset only: its
    # session rolls back, the mark stays, the other assets of the call go on
    try:
        settle_error = await _settle_exchange_timezone(engine, asset_id, prep, remote_data)
    except Exception as settle_e:
        logger.warning("Exchange timezone check failed: nothing written", asset_id=asset_id, error=str(settle_e))
        settle_error = f"Nothing written: the exchange timezone check failed ({settle_e!s})"
    if settle_error is not None:
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
            message=settle_error,
            errors=[settle_error],
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
    # A refused current value is reported like a date the upsert rejects: the result is partial, and says why (X-R51)
    errors.extend(remote_data.notes)

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
                # Only the dates the upsert keeps are counted and announced: a value no column keeps loses its date in
                # the upsert (W-B58), so that date is neither a change nor in ``changed_points`` (W-B62); nor is a date
                # outside stored_date_bounds(), which the upsert skips as well (X-R65, N83)
                earliest, latest = stored_date_bounds()
                kept_items = [p for p in price_items if _unstorable_provider_point(p) is None and earliest <= p.date <= latest]
                try:
                    new_count, changed_count, changed_items_delta = await _count_actual_price_changes(persist_session, asset_id, kept_items)
                except Exception:
                    new_count, changed_count, changed_items_delta = len(kept_items), 0, list(kept_items)  # Fallback

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
                        await EventStoreOperations._upsert_asset_events(
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
                    # Z-32: the provider's own quote currency, as the column holds it (8 characters); a history that
                    # reports none leaves the last one
                    reported = (remote_data.reported_currency or "").strip()
                    if reported and len(reported) <= 8:
                        fresh_assignment.reported_currency = reported
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
    fetch_refusals: dict[int, AssetRateLimitedError] | None = None,
) -> list[FARefreshResult]:
    """Persist fetched items with one isolated session per asset.

    An item whose provider refused for too many requests carries ``error_code="RATE_LIMITED"`` and ``retry_after``,
    whether it failed or saved what it got: a caller knows when the provider may be called again.
    """
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
    results = list(await asyncio.gather(*tasks)) if tasks else []
    refusals = fetch_refusals or {}
    return [_with_refusal(result, refusals.get(result.asset_id)) for result in results]


def _with_refusal(result: FARefreshResult, refusal: AssetRateLimitedError | None) -> FARefreshResult:
    """``result`` with the refusal for too many requests its fetch met, if any."""
    if refusal is None:
        return result
    return result.model_copy(update={"error_code": refusal.error_code, "retry_after": refusal.retry_after})


def _refusal_of(error: BaseException, current: AssetRateLimitedError | None) -> AssetRateLimitedError | None:
    """The refusal to report after ``error``: the error itself when it is one, with the longest wait; else ``current``."""
    if not isinstance(error, AssetRateLimitedError):
        return current
    if current is None or (error.retry_after or 0.0) >= (current.retry_after or 0.0):
        return error
    return current


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
        fetch_results, fetch_errors, fetch_refusals = await _fetch_refresh_items(
            prepared_items,
            concurrency,
            semaphore_timeout,
        )
        persist_results = await _persist_refresh_items(
            prepared_items,
            fetch_results,
            fetch_errors,
            get_async_engine(),
            fetch_refusals,
        )

        results = immediate_results + persist_results
        return FABulkRefreshResponse(
            results=results,
            success_count=sum(1 for result in results if result.status in (SyncStatus.OK, SyncStatus.PARTIAL)),
            errors=[],
            date_range=requests[0].date_range,
            total_points_changed=sum(result.points_changed for result in results),
        )
