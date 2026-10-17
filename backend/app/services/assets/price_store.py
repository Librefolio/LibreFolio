"""Asset price persistence operations."""

from __future__ import annotations

import functools
from datetime import date
from decimal import Decimal
from typing import List, Optional

import structlog
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    PriceHistory,
)
from backend.app.db.precision import decimal_limit_issue, get_model_column_precision, integer_digits_issue, max_integer_digits, storable_price, storable_value, truncate_priceHistory
from backend.app.db.real_decimal import REAL_SIGNIFICANT_DIGITS
from backend.app.schemas import (
    FAAssetDelete,
    FABulkDeleteResponse,
    FAPriceDeleteResult,
    FAPricePoint,
    FAUpsert,
)
from backend.app.schemas.prices import FACurrentValue
from backend.app.utils.date_range_limits import DateOutOfRangeError, stored_date_bounds
from backend.app.utils.datetime_utils import utcnow
from backend.app.utils.sql_chunks import chunks

logger = structlog.get_logger(__name__)

#: The prices a user types (C-97): over the column's limit they are refused, never truncated. Volume is a count: only
#: its size is limited (W-B58), its decimals are read back rounded, as always.
_PRICE_LIMIT_FIELDS = ("open", "high", "low", "close")
_SENTINEL = Decimal("-1")


def _price_limit_issue(price: FAPricePoint, name: str) -> Optional[tuple[str, int]]:
    """What keeps the typed ``name`` of ``price`` out of its column (``decimal_limit_issue``; a volume, its size only)."""
    value = getattr(price, name)
    if value is None:
        return None
    if name == "volume":
        return integer_digits_issue(value, PriceHistory, name)
    return decimal_limit_issue(value, PriceHistory, name)


def _reject_prices_over_the_limit(data: List[FAUpsert]) -> None:
    """Refuse a manual upsert holding a price over its column's limit, before anything is written (C-97, issue #43).

    A price keeps 12 digits before the decimal point, 12 decimal places and 15 significant digits
    (``db/precision.decimal_limit_issue``; the digits before the point since W-B58); a volume, 24 digits before the
    point: a typed value over any of them is refused, naming the asset, the maxima and the dates, never truncated in
    silence. The ``-1`` sentinel has none of them. A provider's prices are not checked here: their long floats are
    truncated (``truncate_priceHistory``), and a date with a value no column can keep is skipped
    (``_unstorable_provider_point``).

    Raises:
        ValueError: the router turns it into HTTP 400, as it does a currency mismatch.
    """
    for item in data:
        offending = [f"{price.date.isoformat()} ({name})" for price in item.prices for name in (*_PRICE_LIMIT_FIELDS, "volume") if _price_limit_issue(price, name) is not None]
        if offending:
            _precision, scale = get_model_column_precision(PriceHistory, "close")
            shown = ", ".join(offending[:10]) + (f" (+{len(offending) - 10} more)" if len(offending) > 10 else "")
            raise ValueError(
                f"Too many digits in the prices of asset {item.asset_id}: at most {max_integer_digits(PriceHistory, 'close')} digits before the decimal point, {scale} decimal places and {REAL_SIGNIFICANT_DIGITS} significant digits "
                f"(a volume, {max_integer_digits(PriceHistory, 'volume')} digits before the decimal point); {len(offending)} value(s): {shown}"
            )


def _reject_dates_out_of_range(data: List[FAUpsert], earliest: date, latest: date) -> None:
    """Refuse a manual upsert holding a date outside ``stored_date_bounds()``, before anything is written (X-R65, N83).

    One entry per asset with such dates, in the request's order, with at most 10 of them; ``count`` is every one. A
    provider's points are not refused: ``bulk_upsert_prices`` skips them, as it skips the unstorable ones.

    Raises:
        DateOutOfRangeError: the router turns it into HTTP 422 ``date_out_of_range``.
    """
    items: list[dict] = []
    count = 0
    for item in data:
        dates = [price.date.isoformat() for price in item.prices if not earliest <= price.date <= latest]
        if dates:
            items.append({"asset_id": item.asset_id, "dates": dates[:10]})
            count += len(dates)
    if items:
        raise DateOutOfRangeError(items=items, count=count, earliest=earliest, latest=latest)


def _unstorable_provider_point(price: FAPricePoint) -> Optional[str]:
    """Why a provider's price point cannot be stored, as ``name=value``, or None (W-B58).

    A price that is not finite, has more digits before the decimal point than its column, or turns into 0 when truncated
    (``storable_price``); a volume past its column's digits (``integer_digits_issue``). The ``-1`` sentinel is no value.
    """
    for name in _PRICE_LIMIT_FIELDS:
        value = getattr(price, name)
        if value is None or (name != "close" and value == _SENTINEL):
            continue
        if storable_price(value, name) is None:
            return f"{name}={value}"
    volume = price.volume
    if volume is not None and volume != _SENTINEL and integer_digits_issue(volume, PriceHistory, "volume") is not None:
        return f"volume={volume}"
    return None


def _kept_price(value: Optional[Decimal], name: str) -> Optional[Decimal]:
    """A merged open, high or low as its column keeps it, or None. The incoming values are checked before; a stored one
    written by an older release may be past the column's digits, and truncating it raised in the middle of the slices
    (W-B58): it is dropped instead."""
    return storable_value(value, PriceHistory, name) if value is not None else None


def _kept_volume(value: Optional[Decimal]) -> Optional[Decimal]:
    """A merged volume, or None for one its column cannot keep (a stored value of an older release, W-B58)."""
    return value if value is None or integer_digits_issue(value, PriceHistory, "volume") is None else None


@functools.lru_cache(maxsize=1024)
def _report_unstorable_quote(asset_id: int, provider_code: str, value: str) -> None:
    """Log a live quote no price column can keep once per process for each asset, provider and value (X-R40): it is asked
    for again at every poll (the scheduler every 10 minutes, each open asset page every 30 seconds), and the same refusal
    said each time is noise. Bounded, so that a provider answering a new absurd value at every poll cannot grow it."""
    logger.warning("Live quote refused: no price column can keep it, the last stored price stands", asset_id=asset_id, provider=provider_code, value=value)


def _quote_text(value: object) -> str:
    """A quote as the log shows it, at most about 40 characters: written out, ``1E+50000000`` is 50 MB of digits."""
    text = str(value)
    return text if len(text) <= 40 else f"{text[:24]}… ({len(text)} characters)"


def storable_current_value(current: Optional[FACurrentValue], asset_id: int, provider_code: str) -> Optional[FACurrentValue]:
    """A provider's live quote as the price columns keep it, or None when they cannot (X-R40, W-B62).

    ``storable_price`` decides (W-B58): a value that is not finite, has more than 12 digits before the decimal point, or
    is not 0 and truncates to 0 (``1E-13``) is refused — never served, never cached, never written: the current price
    falls back to the last stored one, as after a provider failure — and logged once (``_report_unstorable_quote``). A
    value the truncation leaves as it is comes back as it came, its form included (``101.5`` stays ``101.5``); one it
    changes comes back truncated, as the history and today's row keep it (``65432.1234567890999`` → ``65432.123456789``).
    Never raises: a value that is no number at all, from a plugin that skips the schema, is refused too.
    """
    if current is None:
        return None
    raw = current.value
    try:
        value = raw if isinstance(raw, Decimal) else Decimal(str(raw))
        stored = storable_price(value)
    except (ArithmeticError, TypeError, ValueError):
        value = stored = None
    if stored is None:
        _report_unstorable_quote(asset_id, provider_code, _quote_text(raw))
        return None
    served = value if stored == value else stored
    return current if served is raw else current.model_copy(update={"value": served})


def unstorable_quote_reason(value: object) -> str:
    """Why a provider's current value was refused, for a refresh result (X-R51): the value, shortened, and the limits of
    a price column, read from the model."""
    _precision, scale = get_model_column_precision(PriceHistory, "close")
    return f"Current price {_quote_text(value)} not saved: a price keeps at most {max_integer_digits(PriceHistory, 'close')} digits before the decimal point, and is never 0 once cut to {scale} decimal places"


PRICE_UPSERT_CHUNK_SIZE = 1000


class PriceStoreOperations:
    """Asset price persistence operations."""

    @staticmethod
    async def bulk_upsert_prices(data: List[FAUpsert], session: AsyncSession, source_plugin_key: str = "MANUAL") -> dict:  # noqa: C901 — chunked batch upsert, per-date sentinel merge
        """
        Bulk upsert prices manually (PRIMARY bulk method).

        Args:
            data: List of FAUpsert (asset_id + prices)
            session: Database session
            source_plugin_key: Provenance tag written on every upserted row.
                Defaults to ``"MANUAL"`` (the Data Editor / manual-entry use
                case — see ``price_router`` in ``api/v1/assets/prices.py``, under
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
        earliest, latest = stored_date_bounds()
        if source_plugin_key == "MANUAL":
            _reject_prices_over_the_limit(data)
            _reject_dates_out_of_range(data, earliest, latest)

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

            # W-B58: a provider's value no column can keep loses its date, here, before any slice is written: a value
            # that failed in the truncation of a later slice left the earlier ones committed. A manual upsert never
            # gets here with one (``_reject_prices_over_the_limit`` refused it).
            unstorable_dates: list[str] = []
            out_of_range_dates: list[str] = []
            if source_plugin_key != "MANUAL":
                # X-R65 (N83): a provider's date outside stored_date_bounds() is skipped, never stored.
                for date_key in list(valid_inputs):
                    if not earliest <= date_key <= latest:
                        del valid_inputs[date_key]
                        out_of_range_dates.append(date_key.isoformat())
                if out_of_range_dates:
                    logger.warning("Provider prices skipped: date out of range", asset_id=asset_id, source=source_plugin_key, dates=out_of_range_dates[:5], count=len(out_of_range_dates), earliest=earliest.isoformat(), latest=latest.isoformat())
                for date_key, price in list(valid_inputs.items()):
                    reason = _unstorable_provider_point(price)
                    if reason is not None:
                        del valid_inputs[date_key]
                        unstorable_dates.append(f"{date_key.isoformat()} ({reason})")
                if unstorable_dates:
                    logger.warning("Provider prices skipped: no price column can keep them", asset_id=asset_id, source=source_plugin_key, dates=unstorable_dates[:5], count=len(unstorable_dates))

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
                        open=_kept_price(merged_open, "open"),
                        high=_kept_price(merged_high, "high"),
                        low=_kept_price(merged_low, "low"),
                        close=truncate_priceHistory(price.close, "close"),
                        volume=_kept_volume(merged_volume),
                        currency=price.currency or default_currency,
                        source_plugin_key=source_plugin_key,
                        # Every write stamps fetched_at, manual ones included, because it
                        # feeds the COUNT+MAX(fetched_at) cache key of
                        # PortfolioCalculationEngine._compute_price_fingerprint(). Editing an existing price by hand
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
            if out_of_range_dates:
                msg += f"; rejected {len(out_of_range_dates)} date(s) outside {earliest.isoformat()} to {latest.isoformat()}: " + ", ".join(out_of_range_dates[:5]) + (f" (+ {len(out_of_range_dates) - 5} more)" if len(out_of_range_dates) > 5 else "")
            if unstorable_dates:
                msg += f"; rejected {len(unstorable_dates)} date(s) with a value no price column can keep: " + ", ".join(unstorable_dates[:5]) + (f" (+ {len(unstorable_dates) - 5} more)" if len(unstorable_dates) > 5 else "")

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

        # One DELETE per chunk of ranges, in one transaction (MF-SEC9a): SQLite refuses an OR of a thousand terms
        deleted_count = 0
        for chunk in chunks(conditions):
            result = await session.execute(delete(PriceHistory).where(or_(*chunk)))
            deleted_count += result.rowcount
        await session.commit()

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
