"""Asset price queries and current quote operations."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetProviderAssignment,
    PriceHistory,
)
from backend.app.db.precision import storable_price
from backend.app.schemas import (
    FAPricePoint,
    SignalCadence,
    SignalDomain,
    SignalEventPoint,
    SignalExecutionContext,
    SignalPricePoint,
    SignalResult,
    SignalSourceCapability,
    SignalVolumeKind,
)
from backend.app.schemas.assets.events import FAAssetEventPointOut
from backend.app.schemas.common import (
    Currency,
    DateRangeModel,
    FxBackwardFillInfo,
)
from backend.app.schemas.prices import AssetBackwardFillInfo, FACurrentPriceItem, FACurrentValue, FAPriceQueryResult, FAPriceSampleBounds
from backend.app.schemas.provider import (
    FAVolumeKind,
)
from backend.app.services.assets import core
from backend.app.services.assets.base import AssetRateLimitedError, AssetSourceProvider
from backend.app.services.assets.market_calendar import ensure_market_holidays
from backend.app.services.assets.price_sampling import SampleResolution, choose_resolution, resolve_sample_references, sample_dates
from backend.app.services.assets.price_store import storable_current_value
from backend.app.services.assets.registry import AssetProviderRegistry
from backend.app.services.fx.conversion import convert_bulk
from backend.app.services.market_series import mark_market_closed_carries, prepare_asset_series_set
from backend.app.services.signals.aggregation import align_signal_series, sample_signal_series
from backend.app.services.signals.execution import SignalPreparedSeriesBundle
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.services.signals.service import SignalService
from backend.app.utils.date_range_limits import MAX_BULK_ITEM_DAYS, BulkTooManyDaysError
from backend.app.utils.datetime_utils import EARLIEST_RANGE_START, latest_range_end, utcnow

logger = structlog.get_logger(__name__)

RISK_WARMUP_DAY_MULTIPLIER = 2

#: Rows read per page, after the latest one, while looking for the last close that reads a number (W-B62).
_FALLBACK_PAGE = 32


@dataclass(frozen=True)
class _SamplePlan:
    """Z-29: an item sampled weekly or monthly, before its bucket rows are read: its step, the fill's first day, the
    buckets' dates (none: nothing to fill) and the rows already read (the seed, the first row in the range, and with
    sample_like the last row on or before the first day)."""

    resolution: SampleResolution
    first: date_type | None
    dates: tuple[date_type, ...]
    edges: tuple[PriceHistory, ...]


async def _last_readable_price(session: AsyncSession, asset_id: int) -> Optional[PriceHistory]:
    """The asset's most recent price row whose close reads a number, or None (W-B62).

    ``RealDecimal`` reads ``None`` for a close the file holds as ±inf, or as no number at all, written by an older release
    or by another tool (W-B58); ``Decimal(str(None))`` raised, and the gather failed the whole bulk call. Such a row is
    passed over. The latest row is read alone, then older ones a page at a time: the first one almost always reads.
    """
    stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_id).order_by(PriceHistory.date.desc())
    offset, page = 0, 1
    while True:
        rows = (await session.execute(stmt.offset(offset).limit(page))).scalars().all()
        for row in rows:
            if row.close is not None:
                return row
        if len(rows) < page:
            return None
        offset += page
        page = _FALLBACK_PAGE


async def _last_readable_prices(session: AsyncSession, asset_ids: list[int]) -> dict[int, PriceHistory]:
    """Each asset's most recent price row whose close reads a number (``_last_readable_price``), for many assets at once.

    One grouped query for the latest row of every asset (MF-SEC9c), run once the live quotes are in: the fallbacks used
    to read the session from the parallel quote tasks, which one ``AsyncSession`` does not allow. An asset whose latest
    close does not read (W-B62) is looked up alone, older rows a page at a time, one after the other. An asset without a
    readable price is absent.
    """
    if not asset_ids:
        return {}
    latest = select(PriceHistory.asset_id, func.max(PriceHistory.date).label("latest")).where(PriceHistory.asset_id.in_(asset_ids)).group_by(PriceHistory.asset_id).subquery()
    rows = (await session.execute(select(PriceHistory).join(latest, and_(PriceHistory.asset_id == latest.c.asset_id, PriceHistory.date == latest.c.latest)))).scalars().all()
    found: dict[int, PriceHistory] = {}
    unreadable: list[int] = []
    for row in rows:
        if row.close is not None:
            found[row.asset_id] = row
        else:
            unreadable.append(row.asset_id)
    for asset_id in sorted(unreadable):
        row = await _last_readable_price(session, asset_id)
        if row is not None:
            found[asset_id] = row
    return found


def _quote_item(asset_id: int, quote: FACurrentValue, source: str) -> FACurrentPriceItem:
    """The item of a live quote."""
    return FACurrentPriceItem(asset_id=asset_id, value=quote.value, currency=quote.currency, as_of_date=quote.as_of_date, source=source)


async def _live_quote_item(asset_id: int, assignment: AssetProviderAssignment, semaphore: asyncio.Semaphore) -> tuple[Optional[FACurrentPriceItem], Optional[AssetRateLimitedError]]:
    """The asset's live quote from its provider as an item, and the «too many requests» refusal met, if any.

    ``(None, None)`` without a configured provider, after a failure, or for a quote no price column keeps: the caller
    then falls back to the last stored price. The quote is served as the price columns keep it
    (``storable_current_value``: truncated like the history, or refused and logged once; X-R40, W-B62), and a quote is
    cached only once its item is built: the current-value cache (2 minutes, shared with the refresh) never holds one
    that cannot be served.
    """
    provider = await core.configured_provider(assignment.provider_code)
    if not provider:
        return None, None
    params = core._parse_provider_params(assignment.provider_params)
    mapped_id_type = AssetSourceProvider.map_input_type_to_identifier_type(assignment.identifier_type)
    source = f"provider:{assignment.provider_code}"

    # Check core cache first (TTL 2min), under the key a refresh uses too: with the provider's parameters
    # and settings (core.asset_cache_key), so that assets with other parameters never share a value (X-R28)
    cache_key = core.asset_cache_key(assignment.provider_code, assignment.identifier, assignment.identifier_type, params, core.settings_cache_part(provider))
    cached_cv, cache_ok = core._asset_current_cache.get(cache_key)
    if cache_ok:
        logger.debug(f"Current-price cache HIT for asset {asset_id}")
        # Only a quote that passed is ever cached; checked again all the same, it costs nothing
        quote = storable_current_value(cached_cv, asset_id, assignment.provider_code)
        return (_quote_item(asset_id, quote, source) if quote is not None else None), None

    try:
        # Capture variables for lambda (avoid late-binding)
        _id = assignment.identifier
        _id_type = mapped_id_type
        _params = params
        async with semaphore:
            # R13-SEC9-1: checked again once the slot is ours: a call for the same key that held the slot may have
            # cached the quote meanwhile, and N waiters must not become N provider calls (and a cooldown for everyone).
            cached_cv, cache_ok = core._asset_current_cache.get(cache_key)
            if cache_ok:
                quote = storable_current_value(cached_cv, asset_id, assignment.provider_code)
                return (_quote_item(asset_id, quote, source) if quote is not None else None), None
            fetched = await core.call_provider(provider, lambda: provider.get_current_value(_id, _id_type, _params), timeout=10.0, scope=core.cooldown_scope_for(provider, _id, _id_type, _params))
            # Cached before the slot is released, so the next waiter's re-check above always finds it
            quote = storable_current_value(fetched, asset_id, assignment.provider_code)
            if quote is None:
                return None, None
            item = _quote_item(asset_id, quote, source)
            core._asset_current_cache.set(cache_key, quote)
            return item, None
    except AssetRateLimitedError as refused:
        # Paused after «too many requests»: no call was made, or the provider refused this one. The
        # last stored price stands, and the item says why and for how long (decision 34, D-Z7-2).
        logger.debug("Provider paused, falling back to DB", asset_id=asset_id, retry_after=refused.retry_after)
        return None, refused
    except Exception as prov_err:
        logger.debug("Provider current-price failed, falling back to DB", asset_id=asset_id, error=str(prov_err))
        return None, None


class PriceQueryOperations:
    """Asset price queries and current quote operations."""

    @staticmethod
    def _build_backward_filled_series(
        price_map: dict[date_type, PriceHistory],
        start_date: date_type,
        end_date: date_type,
        seed_price: Optional[PriceHistory] = None,
    ) -> list[FAPricePoint]:
        results: list[FAPricePoint] = []
        last_known: Optional[PriceHistory] = seed_price
        current = start_date
        if seed_price is None:
            # Nothing is emitted before the first known price: start the walk there (X-R55).
            if not price_map:
                return results
            current = max(start_date, min(price_map))
        while current <= end_date:
            ph = price_map.get(current)
            if ph:
                last_known = ph
            if last_known:
                results.append(PriceQueryOperations._fill_point(last_known, current))
            # else: skip days before first known price
            current += timedelta(days=1)
        return results

    @staticmethod
    def _fill_point(row: PriceHistory, day: date_type) -> FAPricePoint:
        """The fill's point on ``day``, from ``row``, the last stored row on or before it: the row itself when it is stored
        on that day, else its values filled backward, with how far. One rule for the daily fill and the sample (Z-29)."""
        return FAPricePoint(
            date=day,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            currency=row.currency,
            source_plugin_key=row.source_plugin_key,
            backward_fill_info=None if row.date == day else AssetBackwardFillInfo(actual_rate_date=row.date, days_back=(day - row.date).days),
        )

    @staticmethod
    def _sample_series(known: list[PriceHistory], dates: list[date_type]) -> list[FAPricePoint]:
        """The fill's point on each of ``dates`` (oldest first), from ``known`` (oldest first): the last row on or before
        the date (Z-29)."""
        points: list[FAPricePoint] = []
        cursor = -1
        for day in dates:
            while cursor + 1 < len(known) and known[cursor + 1].date <= day:
                cursor += 1
            if cursor >= 0:
                points.append(PriceQueryOperations._fill_point(known[cursor], day))
        return points

    @staticmethod
    def _sampled_points(known: list[PriceHistory], plan: _SamplePlan) -> tuple[list[FAPricePoint], bool]:
        """The points of ``plan``'s dates, the fill's first day in front when it is not one of them (it travels apart, in
        ``sample_bounds``): the second value says it is (Z-29)."""
        first_apart = plan.first != plan.dates[0]
        return PriceQueryOperations._sample_series(known, [plan.first, *plan.dates] if first_apart else list(plan.dates)), first_apart

    @staticmethod
    async def _bucket_last_rows(session: AsyncSession, asset_ids: list[int], start: date_type, end: date_type, resolution: SampleResolution) -> dict[int, list[PriceHistory]]:
        """The last row of each ISO week or calendar month of ``asset_ids`` from ``start`` to ``end``, by asset, oldest first
        (Z-29). One statement: SQLite groups the rows and only the chosen ones are read."""
        bucket = func.strftime("%Y-%m", PriceHistory.date) if resolution == "monthly" else func.date(PriceHistory.date, "-6 days", "weekday 1")
        # SQLite takes a bare column from the row that holds its group's max() (lang_select.html, «bare columns in an
        # aggregate query»): the id of each bucket's last row
        last_ids = select(PriceHistory.id, func.max(PriceHistory.date)).where(PriceHistory.asset_id.in_(asset_ids), PriceHistory.date >= start, PriceHistory.date <= end).group_by(PriceHistory.asset_id, bucket).subquery()
        rows = (await session.execute(select(PriceHistory).where(PriceHistory.id.in_(select(last_ids.c.id))).order_by(PriceHistory.asset_id, PriceHistory.date))).scalars().all()
        by_asset: dict[int, list[PriceHistory]] = {}
        for row in rows:
            by_asset.setdefault(row.asset_id, []).append(row)
        return by_asset

    @staticmethod
    async def _plan_samples(requests: list, session: AsyncSession) -> tuple[dict[int, _SamplePlan], dict[int, date_type]]:  # noqa: C901 — three ways to ask a step, one table
        """Z-29: by item index, the plan of each item with ``max_points``, ``resolution`` or ``sample_like`` that is sampled
        weekly or monthly, or has nothing to fill.

        The fill's first day F: the range's start when a row of the asset precedes it (the fill's seed), else its first row
        in the range. ``max_points``: the step ``choose_resolution`` gives on F … end; ``resolution``: that step;
        ``sample_like``: the step of the item named (daily for an item without these fields) from the later of its F and
        this item's own — or, when the item named has nothing to fill, the step its ``max_points`` or ``resolution`` gives
        on this item's own fill. Only the seed and the first row in the range are read here (one index probe each, one
        statement per range), plus, for a ``sample_like`` whose first day is later than its own F, the last row on or
        before that day: the sample's dates are known, and counted against the day budget, before any bucket row is read.
        A daily step is left out, to be read and filled day by day as without these fields — a ``sample_like`` from the
        later first day, given back as the second mapping (by item index, the day its range now starts); nothing to fill
        gives an empty series, as the fill does.
        """
        references = resolve_sample_references(requests)
        asked = {index for index, req in enumerate(requests) if req.max_points is not None or req.resolution is not None or req.sample_like is not None}
        if not asked:
            return {}, {}
        by_range: dict[tuple[date_type, date_type], set[int]] = {}
        for index in asked | {references[index] for index in asked if index in references}:
            req = requests[index]
            by_range.setdefault((req.date_range.start, req.date_range.end or req.date_range.start), set()).add(index)
        edges: dict[int, tuple[PriceHistory | None, PriceHistory | None]] = {}
        for (start, end), indexes in by_range.items():
            asset_ids = sorted({requests[index].asset_id for index in indexes})
            # Each asset's first row in the range and its last one before it, the fill's seed: one index probe each
            first_row_id = select(PriceHistory.id).where(PriceHistory.asset_id == Asset.id, PriceHistory.date >= start, PriceHistory.date <= end).order_by(PriceHistory.date).limit(1).scalar_subquery()
            seed_row_id = select(PriceHistory.id).where(PriceHistory.asset_id == Asset.id, PriceHistory.date < start).order_by(PriceHistory.date.desc()).limit(1).scalar_subquery()
            edge_ids = {asset_id: (first_id, seed_id) for asset_id, first_id, seed_id in (await session.execute(select(Asset.id, first_row_id, seed_row_id).where(Asset.id.in_(asset_ids)))).all()}
            wanted = sorted({row_id for pair in edge_ids.values() for row_id in pair if row_id is not None})
            rows = {row.id: row for row in (await session.execute(select(PriceHistory).where(PriceHistory.id.in_(wanted)))).scalars().all()} if wanted else {}
            for index in indexes:
                first_id, seed_id = edge_ids.get(requests[index].asset_id, (None, None))
                edges[index] = (rows.get(seed_id), rows.get(first_id))

        def own_first(index: int) -> date_type | None:
            seed, first_row = edges[index]
            return requests[index].date_range.start if seed is not None else (first_row.date if first_row is not None else None)

        def asked_step(req: object, first: date_type, end: date_type) -> SampleResolution:
            if req.resolution is not None:
                return req.resolution
            if req.max_points is not None:
                return choose_resolution(first, end, req.max_points)
            return "daily"

        plans: dict[int, _SamplePlan] = {}
        daily_starts: dict[int, date_type] = {}
        anchored: list[int] = []
        for index in sorted(asked):
            req = requests[index]
            end = req.date_range.end or req.date_range.start
            first = own_first(index)
            if first is None:
                plans[index] = _SamplePlan(resolution="daily", first=None, dates=(), edges=())
                continue
            if index in references:
                named = requests[references[index]]
                named_first = own_first(references[index])
                if named_first is None:
                    resolution = asked_step(named, first, end)
                else:
                    resolution = asked_step(named, named_first, end)
                    if named_first > first:
                        first = named_first
                        anchored.append(index)
            else:
                resolution = asked_step(req, first, end)
            if resolution != "daily":
                seed, first_row = edges[index]
                plans[index] = _SamplePlan(resolution=resolution, first=first, dates=tuple(sample_dates(first, end, resolution)), edges=tuple(row for row in (seed, first_row) if row is not None))
            elif index in anchored:
                # A daily card: its follower is daily too, from the day the comparison starts
                daily_starts[index] = first
        for index in anchored:
            plan = plans.get(index)
            if plan is None:
                continue
            # The point on the later first day: the last row on or before it
            row = (await session.execute(select(PriceHistory).where(PriceHistory.asset_id == requests[index].asset_id, PriceHistory.date <= plan.first).order_by(PriceHistory.date.desc()).limit(1))).scalars().first()
            if row is not None:
                plans[index] = _SamplePlan(resolution=plan.resolution, first=plan.first, dates=plan.dates, edges=(*plan.edges, row))
        return plans, daily_starts

    @staticmethod
    async def _read_samples(
        requests: list,
        plans: dict[int, _SamplePlan],
        session: AsyncSession,
        price_maps: dict[int, dict[date_type, PriceHistory]],
        seed_prices: dict[int, PriceHistory],
        asset_ranges: dict[int, tuple[date_type, date_type]],
    ) -> dict[int, tuple[list[FAPricePoint], bool]]:
        """Z-29: the points of each planned item once the day budget has passed them, and whether its first one travels
        apart (``_sampled_points``). Every asset is read once: one the request reads whole (a daily item, a signal's
        comparison) on a range that holds the item's is sampled from those rows; the others with one statement per range
        and step (``_bucket_last_rows``) for all of them. Each date gets the point the daily fill has there."""
        sampled: dict[int, tuple[list[FAPricePoint], bool]] = {index: ([], False) for index, plan in plans.items() if not plan.dates}
        groups: dict[tuple[date_type, date_type, SampleResolution], list[int]] = {}
        for index, plan in plans.items():
            if not plan.dates:
                continue
            req = requests[index]
            start, end = req.date_range.start, req.date_range.end or req.date_range.start
            loaded = asset_ranges.get(req.asset_id)
            if loaded is not None and loaded[0] <= start and loaded[1] >= end:
                seed = seed_prices.get(req.asset_id)
                known = sorted({row.date: row for row in (*((seed,) if seed is not None else ()), *price_maps.get(req.asset_id, {}).values())}.values(), key=lambda row: row.date)
                sampled[index] = PriceQueryOperations._sampled_points(known, plan)
                continue
            groups.setdefault((start, end, plan.resolution), []).append(index)
        for (start, end, resolution), indexes in groups.items():
            last_rows = await PriceQueryOperations._bucket_last_rows(session, sorted({requests[index].asset_id for index in indexes}), start, end, resolution)
            for index in indexes:
                plan = plans[index]
                known = sorted({row.date: row for row in (*plan.edges, *last_rows.get(requests[index].asset_id, []))}.values(), key=lambda row: row.date)
                sampled[index] = PriceQueryOperations._sampled_points(known, plan)
        return sampled

    @staticmethod
    def _reduce_signal_sample(result: FAPriceQueryResult, plan: _SamplePlan) -> None:
        """Z-29s: the answer of an item with signals sampled weekly or monthly, computed day by day and cut to its range,
        reduced to ``plan``'s dates: its prices and bounds as a bucket read gives them (each the daily answer's point, the
        first day's in ``sample_bounds``), its step, and each signal series as the compact chart reduces it
        (``_sample_signal_result``). Without prices (``include_price=False``): the step and the signals."""
        if result.prices:
            first = next((point for point in result.prices if point.date == plan.first), None)
            dates = set(plan.dates)
            result.prices = [point for point in result.prices if point.date in dates]
            result.sample_bounds = FAPriceSampleBounds(first=first, last=result.prices[-1]) if first is not None and result.prices else None
        result.resolution = plan.resolution
        result.signals = [PriceQueryOperations._sample_signal_result(signal, plan) for signal in result.signals]

    @staticmethod
    def _sample_signal_result(signal: SignalResult, plan: _SamplePlan) -> SignalResult:
        """``signal`` with each series reduced to ``plan``'s dates by its output's ``aggregation_profile``, read from the
        plugin as AI Export reads it (Z-29s, ``sample_signal_series``), then all on the same dates (O1,
        ``align_signal_series``). A series no output spec describes stays as it is, logged: none today."""
        if not signal.series:
            return signal
        plugin_class = SignalPluginRegistry.get_plugin(signal.signal_code)
        profiles = {output.key: output.aggregation_profile for output in plugin_class.output_specs} if plugin_class is not None else {}
        reduced = []
        for series in signal.series:
            profile = profiles.get(series.key)
            if profile is None:
                logger.warning("Signal series left daily on a sampled item: no output spec", signal_code=signal.signal_code, series_key=series.key)
                reduced.append(series)
                continue
            reduced.append(sample_signal_series(series, profile, plan.resolution, plan.dates))
        return signal.model_copy(update={"series": PriceQueryOperations._align_reduced(signal.series, reduced)})

    @staticmethod
    def _align_reduced(daily: list, reduced: list) -> list:
        """``reduced`` (``daily``'s series each reduced alone) on identical dates, as ``SignalResult`` wants them (O1,
        ``align_signal_series``). A series left as it was (no output spec, or a reduction that kept no value) keeps its
        daily dates and is not aligned with the others: Z-29b does not read the step from the density of a signal."""
        done = [index for index, (before, after) in enumerate(zip(daily, reduced, strict=True)) if after is not before]
        for index, series in zip(done, align_signal_series([reduced[index] for index in done]), strict=True):
            reduced[index] = series
        return reduced

    @staticmethod
    def _fill_span(
        price_map: dict[date_type, PriceHistory],
        start_date: date_type,
        end_date: date_type,
        stored_seed: Optional[PriceHistory],
    ) -> int:
        """How many points ``_build_backward_filled_series`` would emit for these arguments, without building them (Z-25).

        With a seed (``stored_seed``, or a price of the map before ``start_date``, the one the caller hands the fill), one
        per day of the range; without one, one per day from the first price; none with neither.
        """
        if end_date < start_date:
            return 0
        if stored_seed is not None or any(point_date < start_date for point_date in price_map):
            return (end_date - start_date).days + 1
        first = min(price_map, default=None)
        if first is None or first > end_date:
            return 0
        return (end_date - first).days + 1

    @staticmethod
    def derive_signal_source_capability(prices: Sequence[FAPricePoint]) -> SignalSourceCapability:
        """Derive the semantic volume capability of a neutral price series
        from the source plugin(s) that directly observed it.

        Fails closed (unknown/false) whenever:
        - no point was directly observed (all backward-filled, or empty series),
        - any observed source_plugin_key does not resolve to a registered
          provider (e.g. "MANUAL" upserts, test/legacy sentinel keys), or
        - observed sources disagree (mixed providers with different capability).

        Only points with ``backward_fill_info is None`` count as evidence:
        backward-filled rows copy the seed price's ``source_plugin_key`` onto
        dates that source never actually reported, so counting them would let
        a stale source's capability leak onto data it didn't produce.
        """
        observed_keys = {point.source_plugin_key for point in prices if point.backward_fill_info is None and point.source_plugin_key}
        if not observed_keys:
            return SignalSourceCapability()

        capabilities: set[tuple[bool, FAVolumeKind]] = set()
        for key in observed_keys:
            provider = AssetProviderRegistry.get_provider_instance(key)
            if provider is None:
                # Unknown/manual source (e.g. "MANUAL") — fail closed.
                return SignalSourceCapability()
            capabilities.add((provider.supports_meaningful_volume, provider.volume_kind))

        if len(capabilities) != 1:
            # Mixed sources with disagreeing capability — fail closed.
            return SignalSourceCapability()

        supports_meaningful_volume, volume_kind = next(iter(capabilities))
        if not supports_meaningful_volume:
            return SignalSourceCapability()
        return SignalSourceCapability(
            supports_meaningful_volume=True,
            volume_kind=SignalVolumeKind(volume_kind.value),
        )

    @staticmethod
    async def get_prices_bulk(  # noqa: C901 — TODO(P2-refactor): multi-pass query/FX/signal pipeline, extract passes
        requests: list,
        session: AsyncSession,
    ) -> list:
        """Bulk query prices for multiple assets with a single DB read.

        Fetches all prices in one query and partitions the result by asset_id.
        Each asset then gets its own backward-filled series.

        This method reads ONLY from DB — it does not delegate to providers.
        Provider fetch is a separate operation (POST /assets/prices/sync).

        Every item's range ends at ``latest_range_end()`` at the latest (X-R55): the series, the signals and the events
        see the cut range. An item that starts after it gets an empty result, in its place.

        An item with ``max_points``, ``resolution`` or ``sample_like`` is sampled weekly or monthly when its step says so
        (Z-29): planned on two rows per asset (``_plan_samples``), its points counted against the day budget, then read
        once — from the day-by-day rows when the request reads its asset whole, else one statement per range and step
        for every such asset (``_read_samples``). Each result says its step (``resolution``); a sampled one carries its
        first and last points apart (``sample_bounds``). A ``sample_like`` that cannot be followed raises
        ``SampleReferenceError`` before any read. Such an item sent with ``include_price=False`` only gives its step
        (Z-29a-f): its plan stays, but no price row is read for it past the plan and it counts nothing against the
        budget, whatever its step. With signals, such an item is read, computed and counted day by day as without these
        fields (Z-29s); once its signals are computed and its answer cut, a weekly or monthly plan reduces it: its prices
        and bounds as a bucket read gives them, each signal series by its output's ``aggregation_profile``
        (``sample_signal_series``).
        """
        if not requests:
            return []
        # Z-29: every sample_like names an item of the request, before anything is read
        resolve_sample_references(requests)

        latest_end = latest_range_end()
        clamped: list = []
        future_positions: set[int] = set()
        for index, req in enumerate(requests):
            if req.date_range.start > latest_end:
                future_positions.add(index)
            elif (req.date_range.end or req.date_range.start) > latest_end:
                req = req.model_copy(update={"date_range": DateRangeModel(start=req.date_range.start, end=latest_end)})
            clamped.append(req)
        if future_positions:
            present = [req for index, req in enumerate(clamped) if index not in future_positions]
            present_results = iter(await PriceQueryOperations.get_prices_bulk(present, session) if present else [])
            return [FAPriceQueryResult(asset_id=req.asset_id) if index in future_positions else next(present_results) for index, req in enumerate(clamped)]
        requests = clamped
        # Z-29: the items sampled weekly or monthly, planned on two rows per asset and kept out of the day-by-day read
        # below; their points count against the day budget, their rows are read once it has passed. A follower of a
        # daily card is read day by day from the day the comparison starts
        sample_plans, daily_starts = await PriceQueryOperations._plan_samples(requests, session)
        for index, start in daily_starts.items():
            requests[index] = requests[index].model_copy(update={"date_range": DateRangeModel(start=start, end=requests[index].date_range.end or requests[index].date_range.start)})
        # Z-29s: an item with signals is read, computed and counted day by day, as without a sampling field; its plan
        # reduces its answer once the signals are computed (_reduce_signal_sample)
        signal_samples = {index: plan for index, plan in sample_plans.items() if requests[index].signals}
        sample_plans = {index: plan for index, plan in sample_plans.items() if index not in signal_samples}
        # Z-29a-f: an item that asks a sampling and no prices only gives its step (a comparison's card, beside its target):
        # its plan stays, but it reads no price row past it and counts nothing against the day budget, whatever its step;
        # one with signals needs its rows (Z-29s)
        placeholders = {index for index, req in enumerate(requests) if not req.include_price and not req.signals and (req.max_points is not None or req.resolution is not None or req.sample_like is not None)}

        signal_service = SignalService()
        signal_plans = []
        request_ranges: list[tuple[date_type, date_type]] = []
        load_ranges: list[tuple[date_type, date_type]] = []
        asset_ranges: dict[int, tuple[date_type, date_type]] = {}
        for index, req in enumerate(requests):
            end = req.date_range.end or req.date_range.start
            requested_range = (req.date_range.start, end)
            context = SignalExecutionContext(
                domain=SignalDomain.ASSET,
                requested_range=req.date_range,
                cadence=SignalCadence.DAILY,
                source_reference=f"asset:{req.asset_id}",
                target_currency=req.target_currency,
            )
            plan = signal_service.prepare_plan(
                req.signals,
                context,
                req.annotation_requests,
            )
            # Point-derived warm-up, for every signal of the plan.
            warmup_days = max(
                plan.max_history_days_before_visible,
                plan.max_prepared_history_points_before_visible * RISK_WARMUP_DAY_MULTIPLIER,
            )
            # E1: a full-history computation (e.g. underwater drawdown, whose
            # relevant peak may predate the visible range by years) loads from
            # the beginning of the available history, which Z-30 sets at
            # EARLIEST_RANGE_START (1900-01-01, the floor of every full-history
            # load): the load starts at the earlier of that floor and the warm-up's
            # start above. A row stored before 1900 (writes have no floor since
            # N83) is at most the fill's seed, so a price at 0001-01-01 no longer
            # makes one visible day walk ~740,000 days.
            if plan.requires_full_history:
                warmup_days = max(warmup_days, (req.date_range.start - EARLIEST_RANGE_START).days)
            warmup_days = min(
                warmup_days,
                (req.date_range.start - date_type.min).days,
            )
            load_range = (
                req.date_range.start - timedelta(days=warmup_days),
                end,
            )
            request_ranges.append(requested_range)
            load_ranges.append(load_range)
            signal_plans.append(plan)
            if index in sample_plans or index in placeholders:
                continue
            for asset_id in (
                req.asset_id,
                *sorted(plan.comparison_asset_ids),
            ):
                existing = asset_ranges.get(asset_id)
                asset_ranges[asset_id] = (
                    min(existing[0], load_range[0]) if existing else load_range[0],
                    max(existing[1], load_range[1]) if existing else load_range[1],
                )

        asset_ids = list(asset_ranges.keys())

        # Compute global min/max date for single query (none when every item is sampled, Z-29)
        global_start = min((r[0] for r in asset_ranges.values()), default=date_type.max)
        global_end = max((r[1] for r in asset_ranges.values()), default=date_type.min)

        # Single DB query for ALL assets in the date range
        stmt = (
            select(PriceHistory)
            .where(
                and_(
                    PriceHistory.asset_id.in_(asset_ids),
                    PriceHistory.date >= global_start,
                    PriceHistory.date <= global_end,
                )
            )
            .order_by(PriceHistory.asset_id, PriceHistory.date)
        )
        all_prices = (await session.execute(stmt)).scalars().all() if asset_ids else []

        # Partition by asset_id
        price_maps: dict[int, dict[date_type, PriceHistory]] = {aid: {} for aid in asset_ids}
        for p in all_prices:
            if p.asset_id in price_maps:
                price_maps[p.asset_id][p.date] = p

        # Query seed prices for assets that may need backward-fill from before the range.
        # For each asset, find the most recent price BEFORE global_start to use as seed.
        seed_prices: dict[int, PriceHistory] = {}
        assets_needing_seed = [aid for aid in asset_ids if not price_maps[aid].get(asset_ranges[aid][0])]
        if assets_needing_seed:
            for aid in assets_needing_seed:
                seed_stmt = (
                    select(PriceHistory)
                    .where(
                        and_(
                            PriceHistory.asset_id == aid,
                            PriceHistory.date < asset_ranges[aid][0],
                        )
                    )
                    .order_by(PriceHistory.date.desc())
                    .limit(1)
                )
                seed_result = await session.execute(seed_stmt)
                seed_row = seed_result.scalars().first()
                if seed_row:
                    seed_prices[aid] = seed_row

        # Z-25: the per-day points the fills will build, comparison series included, against the request's budget. The
        # count follows the fill, not the request: a full-history signal loads from 1900-01-01 at the latest (Z-30), and
        # its fill emits from the first stored price, or from the load start when an older row seeds it, even when the
        # visible range is one day. A sampled item counts its points and its two bounds (Z-29); an item without prices
        # that only gives its step, nothing (Z-29a-f); a sampled item with signals, its fill, as any item with signals
        # (Z-29s).
        item_days = 0
        for index, (req, plan, (start, end)) in enumerate(zip(requests, signal_plans, load_ranges, strict=True)):
            if index in placeholders:
                continue
            if index in sample_plans:
                item_days += len(sample_plans[index].dates) + 2 if sample_plans[index].dates else 0
                continue
            item_days += PriceQueryOperations._fill_span(price_maps.get(req.asset_id, {}), start, end, seed_prices.get(req.asset_id))
            if plan.requires_prepared_asset_series:
                for comparison_asset_id in plan.comparison_asset_ids:
                    if comparison_asset_id != req.asset_id:
                        item_days += PriceQueryOperations._fill_span(price_maps.get(comparison_asset_id, {}), start, end, seed_prices.get(comparison_asset_id))
        if item_days > MAX_BULK_ITEM_DAYS:
            raise BulkTooManyDaysError(item_days=item_days, max_item_days=MAX_BULK_ITEM_DAYS)
        sampled = await PriceQueryOperations._read_samples(requests, {index: plan for index, plan in sample_plans.items() if index not in placeholders}, session, price_maps, seed_prices, asset_ranges)
        sampled.update({index: ([], False) for index in placeholders})

        # Build backward-filled series per asset (preserving request order)
        results = []

        # Check if any request wants events
        event_requests = {
            req.asset_id
            for req, plan in zip(
                requests,
                signal_plans,
                strict=True,
            )
            if getattr(req, "include_events", False) or plan.requires_events
        }

        # Query events if needed
        event_maps: dict[int, list[FAAssetEventPointOut]] = {}
        if event_requests:
            evt_stmt = (
                select(AssetEvent)
                .where(
                    and_(
                        AssetEvent.asset_id.in_(list(event_requests)),
                        AssetEvent.date >= global_start,
                        AssetEvent.date <= global_end,
                    )
                )
                .order_by(AssetEvent.asset_id, AssetEvent.date)
            )
            evt_result = await session.execute(evt_stmt)
            for evt in evt_result.scalars().all():
                if evt.asset_id not in event_maps:
                    event_maps[evt.asset_id] = []
                event_maps[evt.asset_id].append(
                    FAAssetEventPointOut(
                        date=evt.date,
                        type=evt.type.value if hasattr(evt.type, "value") else str(evt.type),
                        value=Currency(code=evt.currency, amount=evt.value),
                        notes=evt.notes,
                        id=evt.id,
                        is_auto=evt.provider_assignment_id is not None,
                    )
                )

        for index, (req, (start, end)) in enumerate(zip(requests, load_ranges, strict=True)):
            aid = req.asset_id
            if index in sampled:
                results.append(FAPriceQueryResult(asset_id=aid, prices=sampled[index][0], resolution=sample_plans[index].resolution if index in sample_plans else "daily"))
                continue
            price_map = price_maps.get(aid, {})
            in_memory_seed = max(
                (price for point_date, price in price_map.items() if point_date < start),
                key=lambda price: price.date,
                default=None,
            )
            seed = in_memory_seed or seed_prices.get(aid)
            series = PriceQueryOperations._build_backward_filled_series(price_map, start, end, seed_price=seed)
            events = [event for event in event_maps.get(aid, []) if start <= event.date <= end] if aid in event_requests else []
            results.append(FAPriceQueryResult(asset_id=aid, prices=series, events=events))

        dependency_results: dict[
            tuple[int, int],
            FAPriceQueryResult,
        ] = {}
        effective_risk_targets: dict[int, str] = {}
        for request_index, (
            req,
            result,
            plan,
            (start, end),
        ) in enumerate(
            zip(
                requests,
                results,
                signal_plans,
                load_ranges,
                strict=True,
            )
        ):
            if not plan.requires_prepared_asset_series:
                continue
            target = req.target_currency or next(
                (point.currency for point in result.prices if point.currency is not None),
                None,
            )
            if target is not None:
                effective_risk_targets[request_index] = target
            for comparison_asset_id in plan.comparison_asset_ids:
                if comparison_asset_id == req.asset_id:
                    continue
                comparison_price_map = price_maps.get(
                    comparison_asset_id,
                    {},
                )
                in_memory_seed = max(
                    (price for point_date, price in comparison_price_map.items() if point_date < start),
                    key=lambda price: price.date,
                    default=None,
                )
                comparison_seed = in_memory_seed or seed_prices.get(comparison_asset_id)
                dependency_results[(request_index, comparison_asset_id)] = FAPriceQueryResult(
                    asset_id=comparison_asset_id,
                    prices=PriceQueryOperations._build_backward_filled_series(
                        comparison_price_map,
                        start,
                        end,
                        seed_price=comparison_seed,
                    ),
                )

        # ── Currency conversion pass ──────────────────────────────────────
        # For each result whose request has target_currency, convert OHLC
        # values via FX rates in a single batch call per asset.
        # E.1 closure (2026-04-22) — the `fx_error` discriminator was removed
        # from the response: the frontend surfaces the remediation via the
        # `requiredFxPairs` derived in `routes/(app)/assets/[id]/+page.svelte`,
        # which already distinguishes 4 states (`ok`/`missing`/`no-data`/`partial-gap`)
        # with dedicated banners + CTA. Auto-registration is NOT performed:
        # pair registration is an explicit user action (E.4 cancelled).

        conversion_jobs = [(getattr(req, "target_currency", None), result) for req, result in zip(requests, results, strict=True)]
        conversion_jobs.extend(
            (
                effective_risk_targets.get(request_index),
                dependency_result,
            )
            for (
                request_index,
                _comparison_asset_id,
            ), dependency_result in dependency_results.items()
        )
        for target, result in conversion_jobs:
            if not target or not result.prices:
                continue

            # Collect conversion requests for close (required) prices
            # We'll convert close first, then proportionally scale OHLC
            conversions = []
            price_indices = []  # track which prices need conversion
            for i, p in enumerate(result.prices):
                if p.currency == target:
                    continue  # already in target currency
                conversions.append((Currency(code=p.currency, amount=p.close), target, p.date))
                price_indices.append(i)

            if not conversions:
                continue

            converted, conv_errors = await convert_bulk(session, conversions, raise_on_error=False)

            # Dedup conversion errors ONCE per job. The old per-point loop ran
            # `err not in result.errors` for every failed point × every error —
            # quadratic in the number of failures, and with a full-history load
            # (E1) tens of thousands of distinct per-date errors made the pass
            # spin the event loop for minutes (2026-09-02 live wedge).
            # The list is also CAPPED: errors embed the failing date, so a
            # long uncovered FX range would otherwise produce a multi-MB
            # payload nobody reads (the frontend only ever surfaces [0]).
            if conv_errors:
                seen = set(result.errors)
                deduped = []
                for err in conv_errors:
                    if err not in seen:
                        seen.add(err)
                        deduped.append(err)
                MAX_CONV_ERRORS = 10
                if len(deduped) > MAX_CONV_ERRORS:
                    deduped = deduped[:MAX_CONV_ERRORS] + [f"… and {len(deduped) - MAX_CONV_ERRORS} more FX conversion failures"]
                result.errors.extend(deduped)

            # Apply conversion results
            conv_idx = 0
            for pi in price_indices:
                conv_result = converted[conv_idx]
                original_point = result.prices[pi]

                if conv_result is None:
                    # Conversion failed — keep native price. The FE will hide
                    # the point from converted chart (same policy as events,
                    # E.8.2) and surface the FX pair issue via `requiredFxPairs`.
                    old_bfi = original_point.backward_fill_info
                    failed_bfi = AssetBackwardFillInfo(
                        actual_rate_date=old_bfi.actual_rate_date if old_bfi else original_point.date,
                        days_back=old_bfi.days_back if old_bfi else 0,
                        fx_rate_date=None,
                        fx_days_back=None,
                    )
                    # Keep the same currency/values, only attach the bfi.
                    result.prices[pi] = FAPricePoint(
                        date=original_point.date,
                        open=original_point.open,
                        high=original_point.high,
                        low=original_point.low,
                        close=original_point.close,
                        volume=original_point.volume,
                        currency=original_point.currency,
                        original_currency=original_point.original_currency,
                        original_close=original_point.original_close,
                        original_open=original_point.original_open,
                        original_high=original_point.original_high,
                        original_low=original_point.original_low,
                        source_plugin_key=original_point.source_plugin_key,
                        backward_fill_info=failed_bfi,
                    )
                    conv_idx += 1
                    continue

                converted_currency, rate_date, _bfill_applied = conv_result
                original_point = result.prices[pi]
                original_close = original_point.close
                original_currency = original_point.currency

                # Compute conversion factor from close conversion
                if original_close and original_close != 0:
                    fx_factor = converted_currency.amount / original_close
                else:
                    conv_idx += 1
                    continue

                # Scale all OHLC values by the same factor
                new_open = original_point.open * fx_factor if original_point.open is not None else None
                new_high = original_point.high * fx_factor if original_point.high is not None else None
                new_low = original_point.low * fx_factor if original_point.low is not None else None
                new_close = converted_currency.amount

                # Compute FX staleness
                fx_days_back_val = (original_point.date - rate_date).days if rate_date < original_point.date else 0

                # Build new backward_fill_info preserving price staleness
                old_bfi = original_point.backward_fill_info
                if old_bfi:
                    new_bfi = AssetBackwardFillInfo(
                        actual_rate_date=old_bfi.actual_rate_date,
                        days_back=old_bfi.days_back,
                        fx_rate_date=rate_date,
                        fx_days_back=fx_days_back_val,
                    )
                elif fx_days_back_val > 0:
                    new_bfi = AssetBackwardFillInfo(
                        actual_rate_date=original_point.date,
                        days_back=0,
                        fx_rate_date=rate_date,
                        fx_days_back=fx_days_back_val,
                    )
                else:
                    new_bfi = None

                # Replace price point with converted version
                result.prices[pi] = FAPricePoint(
                    date=original_point.date,
                    open=new_open,
                    high=new_high,
                    low=new_low,
                    close=new_close,
                    volume=original_point.volume,
                    currency=target,
                    original_currency=original_currency,
                    original_close=original_close,
                    original_open=original_point.open,
                    original_high=original_point.high,
                    original_low=original_point.low,
                    source_plugin_key=original_point.source_plugin_key,
                    backward_fill_info=new_bfi,
                )
                conv_idx += 1

        # Z-29: a sampled series' first point travels apart, beside its last; prices keep the buckets' points, the ones
        # the compact chart draws. Here, once every point is converted.
        for index, (_points, first_apart) in sampled.items():
            result = results[index]
            first = result.prices.pop(0) if first_apart and result.prices else (result.prices[0] if result.prices else None)
            result.sample_bounds = FAPriceSampleBounds(first=first, last=result.prices[-1]) if first is not None and result.prices else None

        # One table for the whole call, and only when something is computed from the prices: the
        # signals read it to tell a stored weekend or holiday repeat from a quote.
        market_holidays = await ensure_market_holidays() if any(req.signals for req in requests) else frozenset()
        prepared_series_bundles: list[Optional[SignalPreparedSeriesBundle]] = []
        for request_index, (
            req,
            result,
            plan,
            (start, end),
        ) in enumerate(
            zip(
                requests,
                results,
                signal_plans,
                load_ranges,
                strict=True,
            )
        ):
            target = effective_risk_targets.get(request_index)
            if not plan.requires_prepared_asset_series or target is None:
                prepared_series_bundles.append(None)
                continue

            prepared_range = DateRangeModel(start=start, end=end)
            primary_set = prepare_asset_series_set(
                [result],
                requested_range=prepared_range,
                target_currency=target,
                market_holidays=market_holidays,
            )
            series_sets = {None: primary_set}
            for comparison_asset_id in plan.comparison_asset_ids:
                if comparison_asset_id == req.asset_id:
                    series_sets[comparison_asset_id] = primary_set
                    continue
                dependency_result = dependency_results[(request_index, comparison_asset_id)]
                series_sets[comparison_asset_id] = prepare_asset_series_set(
                    [result, dependency_result],
                    requested_range=prepared_range,
                    target_currency=target,
                    market_holidays=market_holidays,
                )
            prepared_series_bundles.append(
                SignalPreparedSeriesBundle(
                    primary_asset_id=req.asset_id,
                    series_sets=series_sets,
                )
            )

        # ── Event conversion pass (E.8) ───────────────────────────────────
        # Mirror of the price conversion above, applied to ``result.events``
        # when the request has ``target_currency`` and ``include_events=True``.
        # On success: populate ``original_value``/``fx_rate_date``/``fx_days_back``.
        # On failure: keep the event in its native currency, all ``*_value``/
        # ``fx_*`` stay ``None`` — the FE uses this to hide the marker from
        # the converted chart (see plan closure §E.8.2).
        for req, result in zip(requests, results, strict=True):
            target = getattr(req, "target_currency", None)
            if not target or not result.events:
                continue

            conversions = []
            event_indices = []
            for i, ep in enumerate(result.events):
                if ep.value.code == target:
                    continue  # identity passthrough
                conversions.append((ep.value, target, ep.date))
                event_indices.append(i)

            if not conversions:
                continue

            conv_results, conv_errors = await convert_bulk(session, conversions, raise_on_error=False)

            for idx, ei in enumerate(event_indices):
                conv = conv_results[idx]
                original_ep = result.events[ei]
                if conv is None:
                    # FX miss — surface non-fatal warning, leave event untouched.
                    result.errors.append(f"Missing FX rate {original_ep.value.code}->{target} for event on {original_ep.date.isoformat()}")
                    continue
                new_cur, rate_date, _bfill = conv
                days_back = (original_ep.date - rate_date).days if rate_date else 0
                result.events[ei] = FAAssetEventPointOut(
                    date=original_ep.date,
                    type=original_ep.type,
                    value=new_cur,
                    notes=original_ep.notes,
                    id=original_ep.id,
                    is_auto=original_ep.is_auto,
                    original_value=original_ep.value,
                    fx_info=FxBackwardFillInfo(fx_rate_date=rate_date, fx_days_back=days_back),
                )
            # Include any extra convert_bulk errors (dedup against per-event ones)
            for err in conv_errors:
                if err not in result.errors:
                    result.errors.append(err)

        # ── Signal computation and response slicing ────────────────────────
        for (
            req,
            result,
            plan,
            requested_range,
            prepared_series_bundle,
        ) in zip(
            requests,
            results,
            signal_plans,
            request_ranges,
            prepared_series_bundles,
            strict=True,
        ):
            if req.signals:
                target = req.target_currency
                price_currencies = {point.currency for point in result.prices if point.currency}
                currency_coherent = len(price_currencies) <= 1 and (not target or not price_currencies or price_currencies == {target})
                event_conversion_complete = not target or all(event.value.code == target for event in result.events)
                if not currency_coherent:
                    currencies = ", ".join(sorted(price_currencies))
                    result.errors.append("Technical signal computation excluded unconverted price dates because the series contains mixed currencies: " f"{currencies}")
                signal_price_points = result.prices if currency_coherent else [point for point in result.prices if target and point.currency == target]
                # A stored weekend or holiday row repeating the close before it is a carry, not a quote: marked as
                # carried, it leaves the sessions the indicators compute on, exactly as it leaves the risk series.
                signal_price_points = list(mark_market_closed_carries({point.date: point for point in signal_price_points}, market_holidays).values())
                neutral_prices = [
                    SignalPricePoint(
                        date=point.date,
                        open=point.open,
                        high=point.high,
                        low=point.low,
                        close=point.close,
                        volume=point.volume,
                        backward_fill_info=point.backward_fill_info,
                    )
                    for point in signal_price_points
                ]
                neutral_events = (
                    [
                        SignalEventPoint(
                            date=event.date,
                            type=event.type,
                            value=event.value.amount,
                            metadata={
                                "currency": event.value.code,
                                "notes": event.notes,
                                "id": event.id,
                                "is_auto": event.is_auto,
                            },
                        )
                        for event in result.events
                    ]
                    if event_conversion_complete
                    else []
                )
                result.signals = await signal_service.execute(
                    plan,
                    neutral_prices,
                    neutral_events,
                    events_loaded=(plan.requires_events and event_conversion_complete),
                    prepared_series_bundle=prepared_series_bundle,
                    source_capability=PriceQueryOperations.derive_signal_source_capability(result.prices),
                )

            requested_start, requested_end = requested_range
            result.prices = [point for point in result.prices if requested_start <= point.date <= requested_end] if req.include_price else []
            if not req.include_price:
                result.sample_bounds = None
            result.events = [event for event in result.events if requested_start <= event.date <= requested_end] if req.include_events else []

        # Z-29s: an item with signals sampled weekly or monthly, read and computed day by day, reduced to its plan's dates
        for index, plan in signal_samples.items():
            if plan.resolution != "daily" and plan.dates:
                PriceQueryOperations._reduce_signal_sample(results[index], plan)

        return results

    @staticmethod
    async def get_current_prices_bulk(  # noqa: C901 — per-asset provider→cache→DB fallback chain
        asset_ids: list[int],
        session: AsyncSession,
        concurrency: int = 5,
    ) -> list:
        """
        Fetch current/live prices for multiple assets.

        For each asset:
        1. If a provider is assigned → call provider.get_current_value() (parallel, semaphore-limited), served as the
           price columns keep it: a quote they cannot keep is neither served nor cached (X-R40, W-B62)
        2. Fallback → the latest PriceHistory row whose close reads a number (W-B62)

        **Side effect (F.2 + F.3)**: for every successful provider fetch whose
        ``as_of_date`` is today, the OHLC row for today is either created
        (``open=high=low=close=value``, ``volume=None``) or its intra-day
        range is extended (``low``/``high`` widened, ``open`` set if missing,
        ``close`` overwritten with the latest tick). DB-fallback results are
        not persisted (they are stale data, not fresh quotes). A commit
        failure on the OHLC persist is logged + rolled back without failing
        the fetch (the FACurrentPriceItem list is still returned).

        Args:
            asset_ids: Asset IDs to fetch prices for
            session: Database session (used for both read and the F.2/F.3 write-back)
            concurrency: Max parallel provider calls

        Returns:
            List of FACurrentPriceItem (one per requested asset_id, preserving order); a repeated id is fetched and
            written back once (R13-SEC9-1)
        """
        if not asset_ids:
            return []

        sem = asyncio.Semaphore(concurrency)

        # Batch query: assets + assignments
        asset_stmt = select(Asset).where(Asset.id.in_(asset_ids))
        asset_res = await session.execute(asset_stmt)
        asset_map = {a.id: a for a in asset_res.scalars().all()}

        assign_stmt = select(AssetProviderAssignment).where(AssetProviderAssignment.asset_id.in_(asset_ids))
        assign_res = await session.execute(assign_stmt)
        assign_map = {a.asset_id: a for a in assign_res.scalars().all()}

        async def _live_one(asset_id: int) -> tuple[Optional[FACurrentPriceItem], Optional[AssetRateLimitedError]]:
            """One asset's live quote from its provider, or why there is none. It never reads the session: the quotes
            run in parallel, and one ``AsyncSession`` cannot serve concurrent tasks (MF-SEC9c)."""
            assignment = assign_map.get(asset_id)
            if asset_id not in asset_map or assignment is None:
                return None, None
            return await _live_quote_item(asset_id, assignment, sem)

        # The live quotes in parallel, one per distinct id (R13-SEC9-1: a repeated id is fetched, and written back, once)
        distinct_ids = list(dict.fromkeys(asset_ids))
        live = dict(zip(distinct_ids, await asyncio.gather(*(_live_one(aid) for aid in distinct_ids)), strict=True))

        # Fallback: the last known price from the DB, for the assets without a live quote, in one grouped read once the
        # quotes are in (MF-SEC9c). The latest close that reads a number: one the file holds as ±inf reads None, and is
        # passed over (W-B62)
        stored = await _last_readable_prices(session, [aid for aid in distinct_ids if aid in asset_map and live[aid][0] is None])
        fetched: dict[int, FACurrentPriceItem] = {}
        for aid in distinct_ids:
            item, refusal = live[aid]
            if aid not in asset_map:
                fetched[aid] = FACurrentPriceItem(asset_id=aid, error="Asset not found")
                continue
            if item is not None:
                fetched[aid] = item
                continue
            refusal_fields = {"error_code": refusal.error_code, "retry_after": refusal.retry_after} if refusal is not None else {}
            last_price = stored.get(aid)
            if last_price is not None:
                fetched[aid] = FACurrentPriceItem(
                    asset_id=aid,
                    value=Decimal(str(last_price.close)),
                    currency=last_price.currency,
                    as_of_date=last_price.date,
                    source="db:last_known",
                    **refusal_fields,
                )
            else:
                fetched[aid] = FACurrentPriceItem(asset_id=aid, error="No price data available", **refusal_fields)
        # The answer in request order
        results = [fetched[aid] for aid in distinct_ids]

        # F.2 + F.3 — persist current-price snapshots to PriceHistory.
        # ----------------------------------------------------------------
        # This call is NOT read-only anymore (docstring updated): for every
        # successful **provider** fetch whose ``as_of_date`` equals today we
        # either bootstrap a new row (F.2) or extend the existing intra-day
        # range (F.3). Results sourced from the DB fallback
        # (``source == "db:last_known"``) are **skipped**: they are not fresh
        # quotes, they are stale rows we just read — writing them back as
        # "today" would fabricate data.
        #
        # Concurrency note: multiple callers hitting this in parallel produce
        # last-write-wins semantics. Acceptable because fresh data flows from
        # the same provider (plus its cache), the value is the same, and the
        # realistic concurrency upper bound is (connected users + 1 scheduler).
        today = date_type.today()
        items_to_persist = [r for r in results if r.value is not None and r.currency and r.as_of_date == today and r.source and r.source.startswith("provider:")]

        if items_to_persist:
            existing_stmt = select(PriceHistory).where(and_(PriceHistory.asset_id.in_([r.asset_id for r in items_to_persist]), PriceHistory.date == today))
            existing_res = await session.execute(existing_stmt)
            existing_by_asset = {row.asset_id: row for row in existing_res.scalars().all()}

            logger.debug(
                "Current-price persist: processing %d fresh provider quote(s) for %s (existing rows today: %d)",
                len(items_to_persist),
                today,
                len(existing_by_asset),
            )

            for item in items_to_persist:
                # Truncated like the history (W-B58): 12 decimal places, 15 significant digits. A quote no price column
                # can keep never gets here: it is neither served nor cached (``storable_current_value``; X-R40, W-B62).
                new_close = storable_price(Decimal(str(item.value)))
                if new_close is None:
                    continue
                existing = existing_by_asset.get(item.asset_id)
                if existing is None:
                    # F.2 bootstrap — open=high=low=close=new, volume=None
                    session.add(
                        PriceHistory(
                            asset_id=item.asset_id,
                            date=today,
                            open=new_close,
                            high=new_close,
                            low=new_close,
                            close=new_close,
                            volume=None,
                            currency=item.currency,
                            source_plugin_key=item.source or "provider:unknown",
                            fetched_at=utcnow(),
                        )
                    )
                    logger.debug(
                        "  [F.2 bootstrap] asset=%s date=%s close=%s currency=%s source=%s",
                        item.asset_id,
                        today,
                        new_close,
                        item.currency,
                        item.source,
                    )
                else:
                    # F.3 intra-day extend
                    patch = PriceQueryOperations._extend_ohlc_bounds(existing, new_close)
                    # Always overwrite close with the latest quote (per user spec)
                    patch["close"] = new_close
                    for field_name, new_val in patch.items():
                        setattr(existing, field_name, new_val)
                    existing.fetched_at = utcnow()
                    logger.debug(
                        "  [Intra-day price extend] asset=%s date=%s new_close=%s patch_fields=%s",
                        item.asset_id,
                        today,
                        new_close,
                        list(patch.keys()),
                    )

            try:
                await session.commit()
                logger.debug("Current-price persist: commit OK (%d row(s) written/updated)", len(items_to_persist))
            except Exception as commit_err:
                logger.warning("Current-price OHLC persist failed, rolling back: %s", commit_err)
                await session.rollback()
        else:
            # Only log when something was expected but filtered out (db:last_known or today mismatch)
            skipped_count = sum(1 for r in results if r.source == "db:last_known")
            if skipped_count > 0:
                logger.debug(
                    "Current-price persist: skipped %d item(s) with source=db:last_known (stale fallback, not persisted)",
                    skipped_count,
                )

        # One item per requested id, in request order: a repeated id gets its distinct fetch's item again
        return [fetched[aid] for aid in asset_ids]

    @staticmethod
    def _extend_ohlc_bounds(existing: PriceHistory, new_close: Decimal) -> dict:
        """Compute the patch to apply to ``existing`` so the intra-day OHLC
        bounds cover ``new_close`` (F.3).

        Rules (per plan):
        - ``low``  = min(existing.low,  new_close) when existing.low is set, else new_close
        - ``high`` = max(existing.high, new_close) when existing.high is set, else new_close
        - ``open`` = new_close only when existing.open is None (first tick of the day)
        - ``volume`` untouched

        Close is intentionally NOT touched here: the caller decides whether to
        overwrite close with the latest tick (the current-price path does,
        see ``get_current_prices_bulk``).

        Returns a dict of only the fields that need to change, so the caller
        can SETATTR them directly on the ORM row (no over-write on stable
        fields, easier to log/inspect).
        """
        patch: dict = {}
        if existing.low is None or new_close < existing.low:
            patch["low"] = new_close
        if existing.high is None or new_close > existing.high:
            patch["high"] = new_close
        if existing.open is None:
            patch["open"] = new_close
        return patch
