"""Asset price and event persistence operations."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import List, Optional

import structlog
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetEvent,
    BrokerUserAccess,
    PriceHistory,
    Transaction,
    User,
)
from backend.app.schemas import (
    FAAssetDelete,
    FABulkDeleteResponse,
    FAPriceDeleteResult,
    FAUpsert,
)
from backend.app.schemas.common import (
    Currency,
    FxBackwardFillInfo,
)
from backend.app.schemas.prices import FAAssetEventPoint, FAAssetEventPointOut, FAEventBulkDeleteResponse, FAEventDeleteItemResult, FAEventQueryResult
from backend.app.services.asset_sources import core
from backend.app.services.asset_sources.core import (
    AssetSourceError,
)
from backend.app.services.fx import convert_bulk
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.decimal_utils import truncate_priceHistory

logger = structlog.get_logger(__name__)

PRICE_UPSERT_CHUNK_SIZE = 1000


class PriceStoreOperations:
    """Asset price and event persistence operations."""

    @staticmethod
    async def bulk_upsert_prices(data: List[FAUpsert], session: AsyncSession, source_plugin_key: str = "MANUAL") -> dict:  # noqa: C901 — chunked batch upsert, per-date sentinel merge
        """
        Bulk upsert prices manually (PRIMARY bulk method).

        Args:
            data: List of FAUpsert (asset_id + prices)
            session: Database session
            source_plugin_key: Provenance tag written on every upserted row.
                Defaults to ``"MANUAL"`` (the Data Editor / manual-entry use
                case — see ``price_router`` in ``api/v1/assets.py``, under
                "MANUAL PRICE MANAGEMENT ENDPOINTS"). The scheduler's
                provider-driven history sync (``bulk_refresh_prices`` →
                ``_persist_refresh_item``) passes the real ``provider_code`` (e.g.
                ``"yfinance"``) instead — previously this was always
                hardcoded to "MANUAL" regardless of caller, silently losing
                provenance for scheduler-synced rows (same root cause already
                flagged in the R4-3 comment below for a different downstream
                symptom — stale points surviving a provider-param regen wipe).

        Returns:
            {inserted_count, updated_count, results: [{asset_id, count, message}, ...]}

        Raises:
            ValueError: if any price point has a currency that doesn't match
                ``asset.currency`` (I.2 — Supersedes E.3). The router translates
                this into **HTTP 400** with the offending dates. This is the
                definitive semantics after Block I — soft-skip with ``errors[]``
                was dropped because, post-I.5/I.8, the DataEditor no longer
                sends a per-point currency. See
                ``plan-phase07-transaction-Part3_1_Closure.md`` §E.3.

        Optimized: Batch operations per asset, minimize DB roundtrips.
        """
        if not data:
            return {"inserted_count": 0, "updated_count": 0, "results": []}

        total_inserted = 0
        results = []

        for item in data:
            asset_id = item.asset_id
            prices = item.prices

            if not prices:
                results.append({"asset_id": asset_id, "count": 0, "message": "No prices to upsert"})
                continue

            # Get asset currency for prices without explicit currency
            asset_result = await session.execute(select(Asset).where(Asset.id == asset_id))
            asset = asset_result.scalar_one_or_none()
            if not asset:
                results.append({"asset_id": asset_id, "count": 0, "message": f"Asset {asset_id} not found"})
                continue

            default_currency = asset.currency

            # Build PriceHistory objects for upsert (F.4 MERGE + sentinel semantics)
            # Strategy: fetch existing rows, merge per-field, DELETE affected dates, INSERT merged rows.
            # Sentinel rules apply to open/high/low/volume only (close stays required and is written verbatim):
            #   - field == None (omitted)  → preserve existing DB value (no-op)
            #   - field == -1              → write NULL
            #   - field >= 0               → write the provided value
            # I.2 — Currency coherence validation (Supersedes E.3).
            # Hard reject (not per-item skip): if ANY point has a currency that doesn't
            # match asset.currency, raise ValueError immediately so the router returns
            # 400 with the offending dates. This is defensive — the frontend, after
            # Block I, no longer sends a per-point currency (the column was dropped
            # from the DataEditor), so reaching this branch means the client is buggy
            # or someone is hitting the API directly.
            offending_dates: list[str] = []
            for price in prices:
                effective_currency = price.currency or default_currency
                if effective_currency != default_currency:
                    offending_dates.append(f"{price.date.isoformat()} ({effective_currency})")
            if offending_dates:
                raise ValueError(
                    f"Currency mismatch for asset {asset_id}: expected {default_currency} for all prices, " f"got {len(offending_dates)} date(s) with different currency: " + ", ".join(offending_dates[:10]) + (f" (+ {len(offending_dates) - 10} more)" if len(offending_dates) > 10 else "")
                )

            # Index valid points by date (all inputs are guaranteed matching currency past this line)
            valid_inputs: dict = {}
            for price in prices:
                valid_inputs[price.date] = price

            # F.4 sentinel helper: -1 → None (SET NULL), None → preserve, else → write
            def _merge_field(new_val, existing_val):
                """F.4 sentinel merge for open/high/low/volume."""
                if new_val is None:
                    return existing_val  # no-op: preserve
                if new_val == Decimal("-1"):
                    return None  # SET NULL
                return new_val  # write

            # Integrity guard errors accumulated across all dates (surfaced via
            # the same `results[].message` the currency-mismatch check uses).
            rejected_dates: list[str] = []
            upserted_count = 0

            # SQLite has a single writer per database file, and a transaction holds
            # that writer from its first write until COMMIT. A full-history sync is
            # ~45k daily points, which in one transaction kept the lock for ~10s —
            # long past the 5s busy_timeout, so every concurrent write (another tab,
            # the scheduler, a parallel test worker) died with "database is locked".
            # Committing in bounded slices keeps each hold in the sub-second range
            # and also caps the IN(...) bind-parameter count, which SQLite limits.
            # Per-date merge semantics are unaffected: each date only ever consults
            # its own stored row, so slicing changes nothing about the outcome.
            chunk_keys = list(valid_inputs.keys())
            for chunk_start in range(0, len(chunk_keys), PRICE_UPSERT_CHUNK_SIZE):
                chunk_dates = chunk_keys[chunk_start : chunk_start + PRICE_UPSERT_CHUNK_SIZE]

                # Fetch existing rows for MERGE (F.4)
                existing_rows: dict = {}
                existing_stmt = select(PriceHistory).where(and_(PriceHistory.asset_id == asset_id, PriceHistory.date.in_(chunk_dates)))
                existing_res = await session.execute(existing_stmt)
                for row in existing_res.scalars().all():
                    existing_rows[row.date] = row

                price_objects = []
                for date_key in chunk_dates:
                    price = valid_inputs[date_key]
                    existing = existing_rows.get(date_key)
                    # Sentinel merge for auxiliary OHLC fields (open/high/low) + volume
                    merged_open = _merge_field(price.open, existing.open if existing else None)
                    merged_high = _merge_field(price.high, existing.high if existing else None)
                    merged_low = _merge_field(price.low, existing.low if existing else None)
                    merged_volume = _merge_field(price.volume, existing.volume if existing else None)

                    # Integrity policy:
                    # - Fresh provider OHLC bundles (incoming low+high present) must
                    #   be self-consistent and are still rejected if corrupted.
                    # - Close-only / partial updates must not be rejected just because
                    #   F.4 preserved stale bounds from an older flat candle — that is
                    #   the justETF/scheduled-investment case and the original
                    #   production incident alike. In that branch we widen the merged
                    #   [low, high] bounds around the new close instead.
                    if price.low is not None and price.high is not None:
                        if price.low > price.high or not (price.low <= price.close <= price.high):
                            rejected_dates.append(f"{date_key.isoformat()} (close={price.close}, low={merged_low}, high={merged_high})")
                            continue
                    elif merged_low is not None and merged_high is not None:
                        merged_low = min(merged_low, price.close)
                        merged_high = max(merged_high, price.close)

                    price_obj = PriceHistory(
                        asset_id=asset_id,
                        date=price.date,
                        open=(truncate_priceHistory(merged_open, "open") if merged_open is not None else None),
                        high=(truncate_priceHistory(merged_high, "high") if merged_high is not None else None),
                        low=(truncate_priceHistory(merged_low, "low") if merged_low is not None else None),
                        close=truncate_priceHistory(price.close, "close"),
                        volume=merged_volume,
                        currency=price.currency or default_currency,
                        source_plugin_key=source_plugin_key,
                        # Every write stamps fetched_at, manual ones included, because it
                        # feeds _compute_price_fingerprint()'s COUNT+MAX(fetched_at) cache
                        # key (portfolio_engine.py:2182). Editing an existing price by hand
                        # leaves COUNT unchanged, so fetched_at is the ONLY thing that tells
                        # the portfolio cache to recompute — without it the user's own edit
                        # would stay invisible. A previous comment here claimed manual rows
                        # kept fetched_at=None; they never did (the column is NOT NULL and
                        # the model's default_factory overwrote it at flush), and the intent
                        # it described would have been the bug above.
                        fetched_at=utcnow(),
                    )
                    price_objects.append(price_obj)

                # One native upsert instead of DELETE + INSERT. Python above has already
                # resolved every F.4 sentinel and run the integrity guard, so the merge
                # semantics stay where they can be read and SQL only decides insert vs
                # update. A date rejected by the guard is simply absent from the VALUES,
                # which preserves its stored row — the DELETE had to be filtered by hand
                # to get the same outcome. Row ids are no longer recycled on every write
                # (nothing references price_history.id, so this is free).
                if price_objects:
                    upsert_stmt = sqlite_insert(PriceHistory).values(
                        [
                            {
                                "asset_id": obj.asset_id,
                                "date": obj.date,
                                "open": obj.open,
                                "high": obj.high,
                                "low": obj.low,
                                "close": obj.close,
                                "volume": obj.volume,
                                "currency": obj.currency,
                                "source_plugin_key": obj.source_plugin_key,
                                "fetched_at": obj.fetched_at,
                            }
                            for obj in price_objects
                        ]
                    )
                    upsert_stmt = upsert_stmt.on_conflict_do_update(
                        index_elements=["asset_id", "date"],
                        set_={column: upsert_stmt.excluded[column] for column in ("open", "high", "low", "close", "volume", "currency", "source_plugin_key", "fetched_at")},
                    )
                    await session.execute(upsert_stmt)
                await session.commit()

                upserted_count += len(price_objects)

            # Count as inserted
            total_inserted += upserted_count

            # I.2 — currency-mismatch was hard-rejected earlier (whole call raises).
            # OHLC-integrity rejections (this function's own guard, soft-skip per date)
            # are reported in `msg` below instead.
            msg = f"Upserted {upserted_count} prices"
            if rejected_dates:
                msg += f"; rejected {len(rejected_dates)} date(s) with impossible OHLC (close outside [low, high]): " + ", ".join(rejected_dates[:5]) + (f" (+ {len(rejected_dates) - 5} more)" if len(rejected_dates) > 5 else "")

            results.append(
                {
                    "asset_id": asset_id,
                    "count": upserted_count,
                    "message": msg,
                }
            )
        # update_count = 0 because SQLite doesn't distinguish
        return {"inserted_count": total_inserted, "updated_count": 0, "results": results}

    @staticmethod
    async def _upsert_asset_events(
        session: AsyncSession,
        asset_id: int,
        events: list[dict | FAAssetEventPoint],
        provider_assignment_id: Optional[int],
        default_currency: str,
    ) -> int:
        """Upsert asset events into the AssetEvent table.

        Uses DELETE + INSERT strategy (same as prices) for dedup on (asset_id, date, type).

        Args:
            session: Database session
            asset_id: Asset ID
            events: List of FAAssetEventPoint or dicts (parsed via Pydantic)
            provider_assignment_id: FK to asset_provider_assignments.id (None = manual)
            default_currency: Fallback currency

        Returns:
            Number of events upserted
        """
        if not events:
            return 0

        event_objects = []
        keys_to_delete = []

        for raw_evt in events:
            # Parse through Pydantic if raw dict; if already FAAssetEventPoint, use directly
            evt: FAAssetEventPoint = raw_evt if isinstance(raw_evt, FAAssetEventPoint) else FAAssetEventPoint(**raw_evt)

            evt_date = evt.date
            evt_type = evt.type
            keys_to_delete.append((evt_date, evt_type))

            # Extract amount and currency from Currency value object
            amount = evt.value.amount
            currency = evt.value.code or default_currency

            event_objects.append(
                AssetEvent(
                    asset_id=asset_id,
                    date=evt_date,
                    type=evt_type,
                    value=amount,
                    currency=currency,
                    provider_assignment_id=provider_assignment_id,
                    notes=evt.notes,
                )
            )

        # Delete existing events for these (date, type) pairs — only for the SAME provider
        # When provider_assignment_id is None, SQLAlchemy generates IS NULL which is correct
        # Committed in bounded slices for the same reason as bulk_upsert_prices: one
        # transaction spanning every event would hold SQLite's single write lock for the
        # whole loop. keys_to_delete and event_objects are built 1:1 in the same order,
        # so slicing by index keeps each event with its own delete.
        for chunk_start in range(0, len(event_objects), PRICE_UPSERT_CHUNK_SIZE):
            chunk_end = chunk_start + PRICE_UPSERT_CHUNK_SIZE
            for evt_date, evt_type in keys_to_delete[chunk_start:chunk_end]:
                del_stmt = delete(AssetEvent).where(
                    and_(
                        AssetEvent.asset_id == asset_id,
                        AssetEvent.date == evt_date,
                        AssetEvent.type == evt_type,
                        AssetEvent.provider_assignment_id == provider_assignment_id,
                    )
                )
                await session.execute(del_stmt)

            # Insert new events
            session.add_all(event_objects[chunk_start:chunk_end])
            await session.commit()

        return len(event_objects)

    @staticmethod
    async def bulk_delete_prices(data: List[FAAssetDelete], session: AsyncSession) -> FABulkDeleteResponse:
        """
        Bulk delete price ranges (PRIMARY bulk method).

        Args:
            data: List of FAAssetDelete (asset_id + date_ranges)
            session: Database session

        Returns:
            FABulkDeleteResponse with results and deleted count

        Optimized: 1 SELECT COUNT + 1 DELETE query with complex WHERE
        Note: Cannot parallelize with gather - DB operations are sequential and interdependent
        """
        if not data:
            return FABulkDeleteResponse(deleted_count=0, results=[])

        # Build count per asset before deletion
        asset_delete_counts = {}

        for item in data:
            asset_id = item.asset_id
            ranges = item.date_ranges
            count = 0

            for date_range in ranges:
                start = date_range.start
                end = date_range.end or start  # Single day if no end

                # Count rows for this specific range
                count_stmt = (
                    select(func.count())
                    .select_from(PriceHistory)
                    .where(
                        and_(
                            PriceHistory.asset_id == asset_id,
                            PriceHistory.date >= start,
                            PriceHistory.date <= end,
                        )
                    )
                )
                result = await session.execute(count_stmt)
                count += result.scalar()

            asset_delete_counts[asset_id] = count

        # Build complex OR conditions for all ranges
        conditions = []
        for item in data:
            asset_id = item.asset_id
            ranges = item.date_ranges

            for date_range in ranges:
                start = date_range.start
                end = date_range.end or start  # Single day if no end
                conditions.append(
                    and_(
                        PriceHistory.asset_id == asset_id,
                        PriceHistory.date >= start,
                        PriceHistory.date <= end,
                    )
                )

        if not conditions:
            return FABulkDeleteResponse(deleted_count=0, results=[])

        # Execute single DELETE with OR of all conditions
        stmt = delete(PriceHistory).where(or_(*conditions))
        result = await session.execute(stmt)
        await session.commit()

        deleted_count = result.rowcount

        # Build results per asset with exact counts
        results = [
            FAPriceDeleteResult(
                asset_id=item.asset_id,
                success=True,
                deleted_count=asset_delete_counts.get(item.asset_id, 0),
                message=f"Deleted prices in {len(item.date_ranges)} range(s)",
            )
            for item in data
        ]

        return FABulkDeleteResponse(results=results, success_count=len(results), total_deleted=deleted_count, errors=[])

    @staticmethod
    async def wipe_market_data_for_currency_change(  # noqa: C901 — sequential count-then-delete steps, guard ifs
        asset_id: int,
        session: AsyncSession,
        dry_run: bool = False,
    ) -> dict:
        """Wipe **all** market data for an asset before a currency change.

        Policy D (see phase-07 closure plan §"Issue #R3-3"): when the user
        confirms a currency change, we wipe every series that was denominated
        in the old currency — prices, all events (manual + provider) — and
        disconnect any transaction still pointing at one of the deleted
        events (``transactions.asset_event_id = NULL``). Transactions
        themselves are preserved; it is the user's responsibility to decide
        whether to re-associate them to new events after re-sync.

        Rationale for the "totally symmetric" choice:
        * Prices in the old currency would mix with new-currency data after
          the change → hard-to-debug reports.
        * Events (dividends, interest, splits, …) carry a ``currency`` field
          too; a residual old-currency event is as inconsistent as a
          residual old-currency price.
        * We don't try to convert values via FX (Policy C): double-conversion
          accumulates rounding, manual events would be silently altered
          without user consent.

        Operations (inside a single transaction, in order):

        1. ``UPDATE transactions SET asset_event_id = NULL WHERE
           asset_event_id IN (SELECT id FROM asset_events WHERE asset_id=?)``
        2. ``DELETE FROM asset_events WHERE asset_id=?``
        3. ``DELETE FROM price_history WHERE asset_id=?``
        4. Invalidate per-asset history + current-price caches.

        Args:
            asset_id: target asset.
            session: active DB session (committed on success).
            dry_run: when ``True``, run only the counts and skip the
                destructive SQL. Useful for the pre-confirm summary panel
                on the frontend.

        Returns:
            Dict with keys ``prices``, ``events_manual``, ``events_provider``,
            ``linked_tx``, ``oldest``, ``newest`` (ISO strings or ``None``),
            ``dry_run``.

        Raises:
            AssetSourceError: if ``asset_id`` does not exist.
        """
        asset = (await session.execute(select(Asset).where(Asset.id == asset_id))).scalar_one_or_none()
        if not asset:
            raise AssetSourceError(f"Asset {asset_id} not found", "ASSET_NOT_FOUND")

        # --- Counters -------------------------------------------------------
        prices_res = await session.execute(select(func.count()).select_from(PriceHistory).where(PriceHistory.asset_id == asset_id))
        prices_count = int(prices_res.scalar() or 0)

        events_manual_res = await session.execute(
            select(func.count())
            .select_from(AssetEvent)
            .where(
                AssetEvent.asset_id == asset_id,
                AssetEvent.provider_assignment_id.is_(None),
            )
        )
        events_manual_count = int(events_manual_res.scalar() or 0)

        events_provider_res = await session.execute(
            select(func.count())
            .select_from(AssetEvent)
            .where(
                AssetEvent.asset_id == asset_id,
                AssetEvent.provider_assignment_id.is_not(None),
            )
        )
        events_provider_count = int(events_provider_res.scalar() or 0)

        linked_tx_res = await session.execute(select(func.count()).select_from(Transaction).where(Transaction.asset_event_id.in_(select(AssetEvent.id).where(AssetEvent.asset_id == asset_id))))
        linked_tx_count = int(linked_tx_res.scalar() or 0)

        oldest_date = None
        newest_date = None
        if prices_count > 0:
            oldest_res = await session.execute(select(func.min(PriceHistory.date)).where(PriceHistory.asset_id == asset_id))
            newest_res = await session.execute(select(func.max(PriceHistory.date)).where(PriceHistory.asset_id == asset_id))
            oldest_date = oldest_res.scalar()
            newest_date = newest_res.scalar()

        summary = {
            "prices": prices_count,
            "events_manual": events_manual_count,
            "events_provider": events_provider_count,
            "linked_tx": linked_tx_count,
            "oldest": oldest_date.isoformat() if oldest_date else None,
            "newest": newest_date.isoformat() if newest_date else None,
            "dry_run": dry_run,
        }

        if dry_run:
            return summary

        # --- Destructive SQL (single transaction) ---------------------------
        # 1. Disconnect linked transactions first (pre-DELETE to avoid FK RESTRICT).
        if linked_tx_count > 0:
            await session.execute(Transaction.__table__.update().where(Transaction.asset_event_id.in_(select(AssetEvent.id).where(AssetEvent.asset_id == asset_id))).values(asset_event_id=None))

        # 2. Delete all events.
        if events_manual_count + events_provider_count > 0:
            await session.execute(delete(AssetEvent).where(AssetEvent.asset_id == asset_id))

        # 3. Delete all prices.
        if prices_count > 0:
            await session.execute(delete(PriceHistory).where(PriceHistory.asset_id == asset_id))

        await session.commit()

        # 4. Cache invalidation — history + current. The cache key is
        # ``(provider_code, identifier, identifier_type, params_hash)`` so we
        # rebuild it from the asset's current provider config. If the asset
        # has no provider assigned the keys simply won't be in the cache;
        # ``.delete`` is a no-op in that case.
        try:
            if asset.provider_code:
                params_dict: Optional[dict] = None
                if asset.provider_params:
                    try:
                        params_dict = json.loads(asset.provider_params)
                    except Exception:  # noqa: BLE001 — params may be corrupted; just skip hashing
                        params_dict = None
                cache_key = (
                    asset.provider_code,
                    asset.identifier or "",
                    str(asset.identifier_type),
                    core._provider_params_hash(params_dict),
                )
                core._asset_history_cache.delete(cache_key)
                core._asset_current_cache.delete(cache_key)
        except Exception as cache_err:  # noqa: BLE001 — non-fatal
            logger.warning(
                "wipe_market_data: cache invalidation skipped",
                extra={"asset_id": asset_id, "error": str(cache_err)},
            )

        logger.info(
            "Market data wiped for currency change",
            extra={
                "asset_id": asset_id,
                "prices_deleted": prices_count,
                "events_manual_deleted": events_manual_count,
                "events_provider_deleted": events_provider_count,
                "transactions_disconnected": linked_tx_count,
            },
        )

        return summary

    @staticmethod
    async def bulk_upsert_events(data: list, session: AsyncSession) -> dict:
        """
        Bulk upsert manual events (provider_assignment_id = NULL).

        Uses the existing _upsert_asset_events() method with provider_assignment_id=None.

        **R3-3 Policy D — hard-400 on currency mismatch**: every event must
        carry the same currency as its parent asset. Mixing currencies in
        ``asset_events`` would create the same kind of silent inconsistency
        already rejected for ``price_history`` (see ``bulk_upsert_prices``).
        If any event in ``data`` has ``value.code`` set to a code different
        from ``asset.currency`` we raise a 400 via ``AssetSourceError`` with
        the symmetric ``EVENT_CURRENCY_MISMATCH`` code; the caller
        (endpoint handler) re-raises it as ``HTTPException`` 400.

        Args:
            data: List of FAEventUpsert objects (asset_id + events[])
            session: Database session

        Returns:
            dict with results list and success_count

        Raises:
            AssetSourceError(code="EVENT_CURRENCY_MISMATCH"): when any
                submitted event has an explicit currency code that does not
                match the asset's currency.
        """
        results = []
        total_count = 0

        for item in data:
            asset_id = item.asset_id

            # Verify asset exists
            asset_stmt = select(Asset).where(Asset.id == asset_id)
            asset_res = await session.execute(asset_stmt)
            asset = asset_res.scalar_one_or_none()
            if not asset:
                results.append(
                    {
                        "asset_id": asset_id,
                        "count": 0,
                        "message": f"Asset {asset_id} not found",
                    }
                )
                continue

            # Determine default currency from asset or 'USD'
            default_currency = asset.currency or "USD"

            # R3-3 Policy D: reject any event whose explicit currency does
            # not match the asset's currency. ``None`` / empty codes are
            # accepted (they'll inherit ``default_currency`` downstream).
            mismatches: list[tuple[int, str]] = []  # (event_index, code)
            for idx, raw_evt in enumerate(item.events or []):
                code = None
                value_obj = getattr(raw_evt, "value", None) if not isinstance(raw_evt, dict) else raw_evt.get("value")
                if isinstance(value_obj, dict):
                    code = value_obj.get("code")
                elif value_obj is not None:
                    code = getattr(value_obj, "code", None)
                if code and code != asset.currency:
                    mismatches.append((idx, code))

            if mismatches:
                mismatch_detail = ", ".join(f"#{i}={c}" for i, c in mismatches[:5])
                raise AssetSourceError(
                    f"EVENT_CURRENCY_MISMATCH: asset {asset_id} expects {asset.currency}, " f"got mismatched events [{mismatch_detail}]" + (f" (+{len(mismatches) - 5} more)" if len(mismatches) > 5 else ""),
                    "EVENT_CURRENCY_MISMATCH",
                )

            count = await PriceStoreOperations._upsert_asset_events(
                session=session,
                asset_id=asset_id,
                events=item.events,
                provider_assignment_id=None,  # manual events
                default_currency=default_currency,
            )

            total_count += count
            results.append(
                {
                    "asset_id": asset_id,
                    "count": count,
                    "message": f"Upserted {count} manual events",
                }
            )

        return {"results": results, "success_count": sum(1 for r in results if r["count"] > 0)}

    @staticmethod
    async def query_events_bulk(requests: list, session: AsyncSession) -> list:
        """
        Bulk query events for multiple assets, returning FAAssetEventPointOut with id + is_auto.

        Args:
            requests: List of FAEventQueryItem (asset_id + date_range + optional target_currency)
            session: Database session

        Returns:
            List of FAEventQueryResult

        E.8 — when ``target_currency`` is set on a request, ``event.value`` is
        converted to that currency via FX rates at the event's date. FX misses
        are surfaced as non-fatal warnings in ``FAEventQueryResult.errors``
        (the event is still returned, in its native currency).
        """
        from backend.app.schemas.prices import FAAssetEventPointOut, FAEventQueryResult  # noqa: PLC0415 — avoid circular import

        results = []

        for req in requests:
            asset_id = req.asset_id
            start = req.date_range.start
            end = req.date_range.end or start
            target_currency = getattr(req, "target_currency", None)

            stmt = (
                select(AssetEvent)
                .where(
                    and_(
                        AssetEvent.asset_id == asset_id,
                        AssetEvent.date >= start,
                        AssetEvent.date <= end,
                    )
                )
                .order_by(AssetEvent.date)
            )
            res = await session.execute(stmt)
            db_events = res.scalars().all()

            # Build native-currency event points first
            event_points: list = []
            for ev in db_events:
                event_points.append(
                    FAAssetEventPointOut(
                        date=ev.date,
                        type=ev.type.value if hasattr(ev.type, "value") else str(ev.type),
                        value=Currency(code=ev.currency, amount=ev.value),
                        notes=ev.notes,
                        id=ev.id,
                        is_auto=ev.provider_assignment_id is not None,
                    )
                )

            errors: list[str] = []

            # E.8 — optional target_currency conversion pass
            if target_currency and event_points:
                conversions = [(ep.value, target_currency, ep.date) for ep in event_points]
                conv_results, conv_errors = await convert_bulk(session, conversions, raise_on_error=False)

                for idx, (ep, conv) in enumerate(zip(event_points, conv_results, strict=True)):
                    if conv is None:
                        # FX miss — keep native currency value, surface as non-fatal warning.
                        # original_* stays None → frontend will hide the event marker (E.8.2).
                        errors.append(f"Missing FX rate {ep.value.code}->{target_currency} for event on {ep.date.isoformat()}")
                        continue
                    new_cur, rate_date, _bfill = conv
                    # Identity conversion (from == to) → no-op, don't populate original_*/fx_*
                    # so the FE can distinguish "converted" from "passthrough".
                    if ep.value.code == target_currency:
                        continue
                    # Compute days_back magnitude (0 for same-day, >0 for backward-fill).
                    days_back = (ep.date - rate_date).days if rate_date else 0
                    event_points[idx] = FAAssetEventPointOut(
                        date=ep.date,
                        type=ep.type,
                        value=new_cur,
                        notes=ep.notes,
                        id=ep.id,
                        is_auto=ep.is_auto,
                        original_value=ep.value,
                        fx_info=FxBackwardFillInfo(fx_rate_date=rate_date, fx_days_back=days_back),
                    )

                # Also include per-pair errors surfaced by convert_bulk (e.g. pair not registered)
                # (deduplicated against our per-event messages — convert_bulk errors are already
                # one per failed conversion, same index, so we skip duplicates by content).
                for err in conv_errors:
                    if err not in errors:
                        errors.append(err)

            results.append(
                FAEventQueryResult(
                    asset_id=asset_id,
                    events=event_points,
                    errors=errors,
                )
            )

        return results

    @staticmethod
    async def get_events_by_ids(event_ids: list[int], session: AsyncSession) -> list:
        """
        Fetch events by their primary-key IDs, grouped by asset_id.

        Returns the same FAEventQueryResult shape as query_events_bulk but
        with point selection instead of date-range filters.
        """
        if not event_ids:
            return []

        stmt = select(AssetEvent).where(AssetEvent.id.in_(event_ids)).order_by(AssetEvent.asset_id, AssetEvent.date)
        res = await session.execute(stmt)
        db_events = res.scalars().all()

        # Group by asset_id
        grouped: dict[int, list] = {}
        for ev in db_events:
            point = FAAssetEventPointOut(
                date=ev.date,
                type=ev.type.value if hasattr(ev.type, "value") else str(ev.type),
                value=Currency(code=ev.currency, amount=ev.value),
                notes=ev.notes,
                id=ev.id,
                is_auto=ev.provider_assignment_id is not None,
            )
            grouped.setdefault(ev.asset_id, []).append(point)

        return [FAEventQueryResult(asset_id=aid, events=evts, errors=[]) for aid, evts in grouped.items()]

    @staticmethod
    async def delete_events_bulk(
        event_ids: list[int],
        session: AsyncSession,
        current_user: User,
    ) -> FAEventBulkDeleteResponse:
        """
        Bulk delete asset events with RESTRICT-aware per-item result.

        For each requested id, returns one of:
        - ``deleted`` — event removed
        - ``not_found`` — id did not exist
        - ``in_use`` — referenced by one or more transactions; response exposes
          ``accessible_transactions`` (tx ids current user can see) and
          ``hidden_transactions_count`` (refs owned by other users).

        No partial rollback: deletable events are committed even if others are
        blocked. HTTP layer always returns 200 — inspect ``results`` for outcome.
        """
        results: list[FAEventDeleteItemResult] = []

        for event_id in event_ids:
            event = await session.get(AssetEvent, event_id)
            if event is None:
                results.append(FAEventDeleteItemResult(event_id=event_id, status="not_found"))
                continue

            # RESTRICT pre-check: enumerate transactions that reference this event.
            total_stmt = select(func.count(Transaction.id)).where(Transaction.asset_event_id == event_id)
            total_count_row = await session.execute(total_stmt)
            total_count = int(total_count_row.scalar_one() or 0)

            if total_count > 0:
                # Split by user accessibility via BrokerUserAccess join.
                accessible_stmt = (
                    select(Transaction.id)
                    .join(BrokerUserAccess, Transaction.broker_id == BrokerUserAccess.broker_id)
                    .where(
                        Transaction.asset_event_id == event_id,
                        BrokerUserAccess.user_id == current_user.id,
                    )
                )
                acc_rows = await session.execute(accessible_stmt)
                accessible_ids = [int(r[0]) for r in acc_rows.all()]
                hidden = total_count - len(accessible_ids)

                results.append(
                    FAEventDeleteItemResult(
                        event_id=event_id,
                        status="in_use",
                        accessible_transactions=accessible_ids,
                        hidden_transactions_count=hidden,
                    )
                )
                continue

            # Safe to delete
            await session.delete(event)
            results.append(FAEventDeleteItemResult(event_id=event_id, status="deleted"))

        await session.commit()

        return FAEventBulkDeleteResponse(
            results=results,
            deleted_count=sum(1 for r in results if r.status == "deleted"),
            not_found_count=sum(1 for r in results if r.status == "not_found"),
            in_use_count=sum(1 for r in results if r.status == "in_use"),
        )
