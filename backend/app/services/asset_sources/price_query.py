"""Asset price queries and current quote operations."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import date as date_type
from datetime import timedelta
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetEvent,
    AssetProviderAssignment,
    PriceHistory,
)
from backend.app.schemas import (
    FAPricePoint,
    SignalCadence,
    SignalDomain,
    SignalEventPoint,
    SignalExecutionContext,
    SignalPricePoint,
    SignalSourceCapability,
    SignalVolumeKind,
)
from backend.app.schemas.common import (
    Currency,
    DateRangeModel,
    FxBackwardFillInfo,
)
from backend.app.schemas.prices import AssetBackwardFillInfo, FAAssetEventPointOut, FAPriceQueryResult
from backend.app.schemas.provider import (
    FAVolumeKind,
)
from backend.app.services.asset_sources import core
from backend.app.services.asset_sources.core import (
    AssetSourceProvider,
)
from backend.app.services.fx import convert_bulk
from backend.app.services.provider_registry import AssetProviderRegistry
from backend.app.services.series_preparation import prepare_asset_series_set
from backend.app.services.signal_service import (
    SignalPreparedSeriesBundle,
    SignalService,
)
from backend.app.utils.datetime_utils import utcnow

logger = structlog.get_logger(__name__)

RISK_WARMUP_DAY_MULTIPLIER = 2


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
        while current <= end_date:
            ph = price_map.get(current)
            if ph:
                last_known = ph
                results.append(
                    FAPricePoint(
                        date=current,
                        open=ph.open,
                        high=ph.high,
                        low=ph.low,
                        close=ph.close,
                        volume=ph.volume,
                        currency=ph.currency,
                        source_plugin_key=ph.source_plugin_key,
                        backward_fill_info=None,
                    )
                )
            elif last_known:
                days_back = (current - last_known.date).days
                results.append(
                    FAPricePoint(
                        date=current,
                        open=last_known.open,
                        high=last_known.high,
                        low=last_known.low,
                        close=last_known.close,
                        volume=last_known.volume,
                        currency=last_known.currency,
                        source_plugin_key=last_known.source_plugin_key,
                        backward_fill_info=AssetBackwardFillInfo(actual_rate_date=last_known.date, days_back=days_back),
                    )
                )
            # else: skip days before first known price
            current += timedelta(days=1)
        return results

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
        """
        if not requests:
            return []

        signal_service = SignalService()
        signal_plans = []
        request_ranges: list[tuple[date_type, date_type]] = []
        load_ranges: list[tuple[date_type, date_type]] = []
        asset_ranges: dict[int, tuple[date_type, date_type]] = {}
        for req in requests:
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
            # E1: a full-history computation (e.g. underwater drawdown, whose
            # relevant peak may predate the visible range by years) loads from
            # the beginning of the available history; the min() cap below then
            # resolves to exactly date.min. Point-derived warm-up otherwise.
            if plan.requires_full_history:
                warmup_days = (req.date_range.start - date_type.min).days
            else:
                warmup_days = max(
                    plan.max_history_points_before_visible,
                    plan.max_prepared_history_points_before_visible * RISK_WARMUP_DAY_MULTIPLIER,
                )
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

        # Compute global min/max date for single query
        global_start = min(r[0] for r in asset_ranges.values())
        global_end = max(r[1] for r in asset_ranges.values())

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
        db_result = await session.execute(stmt)
        all_prices = db_result.scalars().all()

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

        for req, (start, end) in zip(
            requests,
            load_ranges,
            strict=True,
        ):
            aid = req.asset_id
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
                    result.errors.append("Technical signal computation skipped because the price " f"series contains mixed currencies: {currencies}")
                neutral_prices = (
                    [
                        SignalPricePoint(
                            date=point.date,
                            open=point.open,
                            high=point.high,
                            low=point.low,
                            close=point.close,
                            volume=point.volume,
                            backward_fill_info=point.backward_fill_info,
                        )
                        for point in result.prices
                    ]
                    if currency_coherent
                    else []
                )
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
            result.events = [event for event in result.events if requested_start <= event.date <= requested_end] if req.include_events else []

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
        1. If a provider is assigned → call provider.get_current_value() (parallel, semaphore-limited)
        2. Fallback → read latest PriceHistory row from DB

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
            List of FACurrentPriceItem (one per requested asset_id, preserving order)
        """
        from backend.app.schemas.prices import FACurrentPriceItem  # noqa: PLC0415 — avoid circular import

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

        async def _fetch_one(asset_id: int) -> FACurrentPriceItem:
            """Fetch current price for one asset via provider or DB fallback."""
            asset = asset_map.get(asset_id)
            if not asset:
                return FACurrentPriceItem(asset_id=asset_id, error="Asset not found")

            assignment = assign_map.get(asset_id)

            # --- Try provider ---
            if assignment:
                provider = AssetProviderRegistry.get_provider_instance(assignment.provider_code)
                if provider:
                    params = core._parse_provider_params(assignment.provider_params)
                    mapped_id_type = AssetSourceProvider.map_input_type_to_identifier_type(assignment.identifier_type)

                    # Check core cache first (TTL 2min)
                    cache_key = (assignment.provider_code, assignment.identifier, str(assignment.identifier_type))
                    cached_cv, cache_ok = core._asset_current_cache.get(cache_key)
                    if cache_ok:
                        logger.debug(f"Current-price cache HIT for asset {asset_id}")
                        return FACurrentPriceItem(
                            asset_id=asset_id,
                            value=cached_cv.value,
                            currency=cached_cv.currency,
                            as_of_date=cached_cv.as_of_date,
                            source=f"provider:{assignment.provider_code}",
                        )

                    try:
                        # Capture variables for lambda (avoid late-binding)
                        _id = assignment.identifier
                        _id_type = mapped_id_type
                        _params = params
                        async with sem:
                            cv = await core._run_provider_in_thread(
                                lambda: provider.get_current_value(_id, _id_type, _params),
                                timeout=10.0,
                            )
                        core._asset_current_cache.set(cache_key, cv)
                        return FACurrentPriceItem(
                            asset_id=asset_id,
                            value=cv.value,
                            currency=cv.currency,
                            as_of_date=cv.as_of_date,
                            source=f"provider:{assignment.provider_code}",
                        )
                    except Exception as prov_err:
                        logger.debug(
                            "Provider current-price failed, falling back to DB",
                            asset_id=asset_id,
                            error=str(prov_err),
                        )

            # --- Fallback: last known price from DB ---
            last_stmt = select(PriceHistory).where(PriceHistory.asset_id == asset_id).order_by(PriceHistory.date.desc()).limit(1)
            last_res = await session.execute(last_stmt)
            last_price = last_res.scalar_one_or_none()

            if last_price:
                return FACurrentPriceItem(
                    asset_id=asset_id,
                    value=Decimal(str(last_price.close)),
                    currency=last_price.currency,
                    as_of_date=last_price.date,
                    source="db:last_known",
                )

            return FACurrentPriceItem(
                asset_id=asset_id,
                error="No price data available",
            )

        # Run all fetches in parallel
        tasks = [_fetch_one(aid) for aid in asset_ids]
        results = await asyncio.gather(*tasks)

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
                new_close = Decimal(str(item.value))
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

        return list(results)

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
