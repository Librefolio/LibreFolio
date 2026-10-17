"""FX rate endpoints (``/fx/currencies``): provider sync, manual upsert and delete, signal catalog, bulk conversion."""

import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, List

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete as sql_delete
from sqlmodel import select

from backend.app.api.v1.auth import get_current_user
from backend.app.db.models import FxRate, User
from backend.app.db.session import get_session_generator
from backend.app.schemas.common import PERIOD_CHANGES_MAX_AS_OF_DAYS, BackwardFillInfo, Currency, DateRangeModel
from backend.app.schemas.fx import (
    PERIOD_CHANGES_MAX_PAIRS,
    FXBulkDeleteResponse,
    FXBulkUpsertResponse,
    FXConversionRequest,
    FXConversionResult,
    FXConvertResponse,
    FXDeleteItem,
    FXDeleteResult,
    FXPeriodChangesRequest,
    FXPeriodChangesResponse,
    FXSignalQueryResult,
    FXUpsertItem,
    FXUpsertResult,
)
from backend.app.schemas.refresh import FXSyncBulkResponse, FXSyncPairRequest
from backend.app.schemas.signals import SignalCadence, SignalCatalogResponse, SignalDomain, SignalExecutionContext, SignalPricePoint
from backend.app.services.fx.base import FXServiceError
from backend.app.services.fx.conversion import convert_bulk
from backend.app.services.fx.period_changes import get_fx_period_changes_bulk
from backend.app.services.fx.storage import delete_rates_bulk, fx_rate_refusal, normalize_storable_rate, upsert_rates_bulk
from backend.app.services.fx.sync import sync_pairs_bulk
from backend.app.services.signals.planning import SignalExecutionPlan, SignalRequestValidationError
from backend.app.services.signals.registry import SignalPluginRegistry
from backend.app.services.signals.service import SignalService
from backend.app.utils.date_range_limits import range_span_floor
from backend.app.utils.datetime_utils import latest_range_end

router_currencies = APIRouter(prefix="/currencies", tags=["FX Currencies"])


@router_currencies.post("/sync", response_model=FXSyncBulkResponse)
async def sync_rates(
    body: FXSyncPairRequest,
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """
    Synchronize FX rates for specified currency pairs and date range.

    **Pair-based sync** — accepts explicit pair slugs (e.g. ['EUR-USD', 'CHF-CNY']).
    Each pair is synced independently using configured routes from
    fx_conversion_routes table, supporting both direct and chain conversions.

    Pairs are normalized to alphabetical order (USD-EUR → EUR-USD).

    **Status per pair:**
    - `ok` — provider returned data, inserted/updated in DB
    - `partial` — provider returned empty or incomplete data
    - `failed` — all providers for this pair failed
    - `skipped` — pair is MANUAL-only, nothing to sync

    Args:
        body: FXSyncPairRequest with pairs list and date range

    Returns:
        FXSyncBulkResponse with per-pair results and summary
    """
    # Validate date range
    if isinstance(body.start, date) and body.start > body.end:
        raise HTTPException(status_code=400, detail="Start date must be before or equal to end date")
    if body.end > date.today():
        raise HTTPException(status_code=400, detail="End date cannot be in the future")

    try:
        result = await sync_pairs_bulk(
            session,
            pairs=body.pairs,
            date_range=(body.start, body.end),
        )
        return result

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except FXServiceError as e:
        raise HTTPException(status_code=502, detail=f"Failed to sync rates: {e!s}") from e
    except Exception as e:
        # Catch-all to prevent hanging — always return a response
        raise HTTPException(status_code=500, detail=f"Unexpected sync error: {e!s}") from e


@router_currencies.post("/rate", response_model=FXBulkUpsertResponse, status_code=200)
async def upsert_rates_endpoint(
    rates: List[FXUpsertItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """
    Manually insert or update one or more FX rates (bulk operation).

    This endpoint accepts a list of rates to insert/update.

    Uses UPSERT logic: if a rate for the same date/base/quote exists, it will be updated.
    Automatic alphabetical ordering and rate inversion is applied.

    Args:
        rates: List of rates to insert/update
        session: Database session

    Returns:
        Operation results with action taken (inserted/updated) for each rate
    """
    results = []
    errors = []

    for idx, rate_item in enumerate(rates):
        base = rate_item.base.upper()
        quote = rate_item.quote.upper()

        # Validate currencies are different
        if base == quote:
            error_msg = f"Rate {idx}: Base and quote must be different (got {base})"
            errors.append(error_msg)
            continue

        try:
            # Alphabetical ordering (base < quote), the rate inverted: inside the item's try, since the inverse of a tiny
            # rate overflows (1 / 1E-1000000) and a rate fx_rates.rate cannot keep is the item's error, never a 500 (X-R38)
            normalized = normalize_storable_rate(base, quote, rate_item.rate)
            if normalized is None:
                raise ValueError(fx_rate_refusal(base, quote, rate_item.rate_date))
            base, quote, rate_value = normalized

            # Use bulk service function
            rate_results = await upsert_rates_bulk(session, [(rate_item.rate_date, base, quote, rate_value, rate_item.source)])

            success, action = rate_results[0]

            results.append(
                FXUpsertResult(
                    success=success,
                    action=action,
                    rate=rate_value,
                    date=rate_item.rate_date.isoformat(),
                    base=base,
                    quote=quote,
                )
            )

        except ValueError as e:
            error_msg = f"Rate {idx}: Validation error: {e!s}"
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Rate {idx}: Failed: {e!s}"
            errors.append(error_msg)

    # If all rates failed, return 400
    if errors and not results:
        raise HTTPException(status_code=400, detail=f"All rates failed: {'; '.join(errors)}")

    return FXBulkUpsertResponse(results=results, success_count=len(results), errors=errors)


@router_currencies.delete("/rate", response_model=FXBulkDeleteResponse)
async def delete_rates_endpoint(  # noqa: C901 — flat bulk loop, per-item validation/dispatch
    deletions: List[FXDeleteItem],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """
    Delete one or more FX rates (bulk operation).

    This endpoint accepts a list of deletion requests. Each request can specify a date range
    to delete rates (using DateRangeModel).

    Currency pairs are automatically normalized to alphabetical order in the backend,
    so deleting USD/EUR will delete the stored EUR/USD rate.

    Args:
        deletions: List of deletion requests with date ranges
        session: Database session

    Returns:
        Deletion results with counts (existing vs deleted) for each request

    Example:
        DELETE /fx/rate-set/bulk
        {
            "deletions": [
                {
                    "from": "EUR",
                    "to": "USD",
                    "start_date": "2025-01-01"
                },
                {
                    "from": "GBP",
                    "to": "USD",
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-05"
                }
            ]
        }
    """
    results = []
    errors = []
    total_deleted = 0

    # Separate "delete_all" requests from date-range requests
    bulk_deletions = []
    deletion_metadata = []

    for idx, delete_req in enumerate(deletions):
        from_cur = delete_req.from_currency.upper()
        to_cur = delete_req.to_currency.upper()

        # Validate currencies are different
        if from_cur == to_cur:
            error_msg = f"Deletion {idx}: from and to currencies must be different (got {from_cur})"
            errors.append(error_msg)
            continue

        # Normalize to alphabetical order
        if from_cur > to_cur:
            base, quote = to_cur, from_cur
        else:
            base, quote = from_cur, to_cur

        if delete_req.delete_all:
            # Delete ALL rates for this pair (no date filter)
            try:
                # Count existing
                count_stmt = select(FxRate).where(FxRate.base == base, FxRate.quote == quote)
                count_result = await session.execute(count_stmt)
                existing_count = len(count_result.scalars().all())

                # Delete all
                del_stmt = sql_delete(FxRate).where(FxRate.base == base, FxRate.quote == quote)
                del_result = await session.execute(del_stmt)
                deleted_count = del_result.rowcount
                await session.commit()

                message = None if deleted_count > 0 else f"No rates found for {base}/{quote}"

                results.append(
                    FXDeleteResult(
                        success=True,
                        base=base,
                        quote=quote,
                        date_range=DateRangeModel(start=date.today()),  # placeholder
                        existing_count=existing_count,
                        deleted_count=deleted_count,
                        message=message,
                    )
                )
                total_deleted += deleted_count
            except Exception as e:
                errors.append(f"Delete all for {base}/{quote} failed: {e!s}")
        else:
            # Date-range deletion — collect for bulk service call
            start_date = delete_req.date_range.start
            end_date = delete_req.date_range.end

            bulk_deletions.append((from_cur, to_cur, start_date, end_date))
            deletion_metadata.append(
                {
                    "original_idx": idx,
                    "from_currency": from_cur,
                    "to_currency": to_cur,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )

    # Execute bulk deletions if any valid
    if bulk_deletions:
        try:
            # Call backend service (normalizes and executes)
            delete_results = await delete_rates_bulk(session, bulk_deletions)

            # Process results
            for metadata, (success, existing_count, deleted_count, message) in zip(deletion_metadata, delete_results, strict=True):
                # Backend normalized the pair, we need to figure out what it became
                # For display, we'll show the normalized version
                from_cur = metadata["from_currency"]
                to_cur = metadata["to_currency"]

                # Normalize for display (same logic as backend)
                if from_cur > to_cur:
                    base, quote = to_cur, from_cur
                else:
                    base, quote = from_cur, to_cur

                results.append(
                    FXDeleteResult(
                        success=success,
                        base=base,
                        quote=quote,
                        date_range=DateRangeModel(
                            start=metadata["start_date"],
                            end=metadata["end_date"] if metadata["end_date"] else None,
                        ),
                        existing_count=existing_count,
                        deleted_count=deleted_count,
                        message=message,
                    )
                )

                total_deleted += deleted_count

        except Exception as e:
            error_msg = f"Bulk deletion failed: {e!s}"
            errors.append(error_msg)
            # If entire bulk operation failed, return 500
            raise HTTPException(status_code=500, detail=error_msg) from e

    # If all deletions failed validation, return 400
    if errors and not results:
        raise HTTPException(status_code=400, detail=f"All deletions failed validation: {'; '.join(errors)}")

    return FXBulkDeleteResponse(
        results=results,
        success_count=len([r for r in results if r.success]),
        total_deleted=total_deleted,
        errors=errors,
    )


_RATE_NOT_FOUND_RE = re.compile(r"^Conversion \d+: No FX rate found for (\S+) on or before (\S+)\. (.+)$")
_CONVERSION_ERROR_INDEX_RE = re.compile(r"^Conversion (\d+)(?::| failed:)")


def _compress_convert_errors(errors: list[str]) -> list[str]:
    """Compress repeated 'No FX rate found' errors into date-range summaries.

    Example: 13 identical messages for CHF/JPY on different dates →
    'No FX rate found for CHF/JPY (13 dates: 2026-03-01 … 2026-03-13). Please sync ...'
    Non-matching errors are kept as-is.
    """
    pair_dates: dict[str, list[str]] = {}  # pair → [date_str, ...]
    pair_suffix: dict[str, str] = {}  # pair → trailing message
    other_errors: list[str] = []

    for err in errors:
        m = _RATE_NOT_FOUND_RE.match(err)
        if m:
            pair, date_str, suffix = m.group(1), m.group(2), m.group(3)
            pair_dates.setdefault(pair, []).append(date_str)
            pair_suffix[pair] = suffix
        else:
            other_errors.append(err)

    compressed: list[str] = []
    for pair, dates in pair_dates.items():
        dates.sort()
        n = len(dates)
        if n == 1:
            compressed.append(f"No FX rate found for {pair} on or before {dates[0]}. {pair_suffix[pair]}")
        else:
            compressed.append(f"No FX rate found for {pair} ({n} dates: {dates[0]} … {dates[-1]}). {pair_suffix[pair]}")

    return compressed + other_errors


def _convert_errors_for_kind(
    errors: list[str],
    metadata: list[dict],
    kind: str,
) -> list[str]:
    selected: list[str] = []
    for error in errors:
        match = _CONVERSION_ERROR_INDEX_RE.match(error)
        if not match:
            if kind == "daily":
                selected.append(error)
            continue
        index = int(match.group(1))
        if index < len(metadata) and metadata[index]["kind"] == kind:
            selected.append(error)
    return selected


@router_currencies.get("/signals", response_model=SignalCatalogResponse)
async def list_fx_signal_catalog(
    _current_user: User = Depends(get_current_user),
) -> SignalCatalogResponse:
    """Return static signal definitions compatible with FX close rates."""
    return SignalCatalogResponse(items=[definition for definition in SignalPluginRegistry.list_definitions() if SignalDomain.FX in definition.compatible_domains])


@router_currencies.post("/convert", response_model=FXConvertResponse)
async def convert_currency_bulk(  # noqa: C901 — sequential bulk pipeline: expand, convert, map results
    request: List[FXConversionRequest],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """
    Convert one or more amounts between currencies (bulk operation).

    This endpoint accepts a list of conversions to perform. Each conversion can specify:
    - A single date (start_date only) for single-day conversion
    - A date range (start_date + end_date) for multi-day conversion

    When a date range is specified, the conversion is automatically expanded to process
    each day in the range individually (both start_date and end_date are inclusive).

    Uses unlimited backward-fill logic: if rate for exact date is not available,
    uses the most recent rate before the requested date.

    Args:
        request: List of conversions to perform
        session: Database session

    Returns:
        Conversion results with rate information for each conversion (one result per day)
    """

    signal_service = SignalService()
    signal_plans: dict[int, SignalExecutionPlan] = {}
    bulk_conversions = []
    conversion_metadata: list[dict] = []

    latest_end = latest_range_end()
    served_ranges: dict[int, DateRangeModel] = {}
    for conv_idx, conversion in enumerate(request):
        to_cur = conversion.to_currency
        # X-R55: the range ends at latest_range_end() and spans RANGE_SPAN_LIMIT_DAYS at most; a conversion entirely
        # after that end asks nothing, and its signals run on an empty series.
        requested_end = min(conversion.date_range.end or conversion.date_range.start, latest_end)
        visible_start = max(conversion.date_range.start, range_span_floor(requested_end))
        in_range = visible_start <= requested_end
        if in_range and (visible_start, requested_end) != (conversion.date_range.start, conversion.date_range.end or conversion.date_range.start):
            conversion = conversion.model_copy(update={"date_range": DateRangeModel(start=visible_start, end=requested_end)})
        served_ranges[conv_idx] = conversion.date_range

        current_date = visible_start
        while current_date <= requested_end:
            bulk_conversions.append(
                (
                    conversion.from_amount,
                    to_cur,
                    current_date,
                )
            )
            conversion_metadata.append(
                {
                    "kind": "daily",
                    "original_idx": conv_idx,
                    "conversion": conversion,
                    "date": current_date,
                }
            )
            current_date += timedelta(days=1)

        if conversion.signals:
            context = SignalExecutionContext(
                domain=SignalDomain.FX,
                requested_range=conversion.date_range,
                cadence=SignalCadence.DAILY,
                source_reference=(f"fx:{conversion.from_amount.code}/" f"{conversion.to_currency}"),
            )
            try:
                plan = signal_service.prepare_plan(
                    conversion.signals,
                    context,
                    conversion.annotation_requests,
                )
            except SignalRequestValidationError as e:
                raise HTTPException(status_code=422, detail=str(e)) from e
            warmup_days = min(
                plan.max_history_days_before_visible,
                (conversion.date_range.start - date.min).days,
            )
            signal_start = max(conversion.date_range.start - timedelta(days=warmup_days), range_span_floor(requested_end))
            signal_plans[conv_idx] = plan
            signal_amount = Currency(
                code=conversion.from_amount.code,
                amount=Decimal("1"),
            )
            current_date = signal_start
            while in_range and current_date <= requested_end:
                bulk_conversions.append(
                    (
                        signal_amount,
                        to_cur,
                        current_date,
                    )
                )
                conversion_metadata.append(
                    {
                        "kind": "signal",
                        "original_idx": conv_idx,
                        "conversion": conversion,
                        "date": current_date,
                    }
                )
                current_date += timedelta(days=1)

    bulk_results, bulk_errors = await convert_bulk(
        session,
        bulk_conversions,
        raise_on_error=False,
    )

    results = []
    signal_points: dict[int, list[SignalPricePoint]] = {index: [] for index in signal_plans}

    for metadata, bulk_result in zip(
        conversion_metadata,
        bulk_results,
        strict=True,
    ):
        if bulk_result is None:
            continue

        converted_currency, actual_rate_date, backward_fill_applied = bulk_result
        conversion = metadata["conversion"]
        on_date = metadata["date"]
        from_cur = conversion.from_amount.code
        to_cur = conversion.to_currency

        backward_fill_info = None
        if backward_fill_applied:
            backward_fill_info = BackwardFillInfo(
                actual_rate_date=actual_rate_date,
                days_back=(on_date - actual_rate_date).days,
            )

        if metadata["kind"] == "signal":
            close = Decimal("1") if from_cur == to_cur else converted_currency.amount
            signal_points[metadata["original_idx"]].append(
                SignalPricePoint(
                    date=on_date,
                    close=close,
                    backward_fill_info=backward_fill_info,
                )
            )
            continue

        rate = None
        if from_cur != to_cur:
            rate = converted_currency.amount / conversion.from_amount.amount
        results.append(
            FXConversionResult(
                from_amount=conversion.from_amount,
                to_amount=converted_currency,
                conversion_date=on_date.isoformat(),
                rate=rate,
                backward_fill_info=backward_fill_info,
            )
        )

    signal_results = []
    for request_index, plan in signal_plans.items():
        conversion = request[request_index]
        signal_results.append(
            FXSignalQueryResult(
                request_index=request_index,
                from_currency=conversion.from_amount.code,
                to_currency=conversion.to_currency,
                date_range=served_ranges[request_index],
                signals=await signal_service.execute(
                    plan,
                    signal_points[request_index],
                    events_loaded=False,
                ),
            )
        )

    daily_errors = _convert_errors_for_kind(
        bulk_errors,
        conversion_metadata,
        "daily",
    )
    compressed_errors = _compress_convert_errors(daily_errors) if daily_errors else []

    if daily_errors and not results and not signal_results:
        raise HTTPException(
            status_code=404,
            detail=("All conversions failed: " f"{'; '.join(compressed_errors)}"),
        )

    return FXConvertResponse(
        results=results,
        success_count=len([result for result in results if result.to_amount is not None]),
        errors=compressed_errors,
        signal_results=signal_results,
    )


@router_currencies.post("/period-changes", response_model=FXPeriodChangesResponse)
async def query_fx_period_changes_bulk(
    requests: Annotated[List[FXPeriodChangesRequest], Body(max_length=PERIOD_CHANGES_MAX_PAIRS)],
    session: AsyncSession = Depends(get_session_generator),
    _current_user: User = Depends(get_current_user),
):
    """The FX table's fixed-period changes (1D … 5Y) of several pairs, up to each one's ``as_of``, in both orientations.

    The rate on a day is the conversion of 1 base on that day, as ``POST /currencies/convert`` gives it. Each change is a
    fraction, null without a rate on either day. At most ``PERIOD_CHANGES_MAX_PAIRS`` pairs and
    ``PERIOD_CHANGES_MAX_AS_OF_DAYS`` distinct ``as_of`` days, each from 1900-01-01 (MF-P2b): 422 otherwise.
    """
    if len({item.as_of for item in requests}) > PERIOD_CHANGES_MAX_AS_OF_DAYS:
        raise HTTPException(status_code=422, detail=f"At most {PERIOD_CHANGES_MAX_AS_OF_DAYS} distinct as_of days per request")
    return FXPeriodChangesResponse(items=await get_fx_period_changes_bulk(requests, session))
