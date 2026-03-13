"""
FX (Foreign Exchange) API endpoints.
Handles currency conversion and FX rate synchronization.
"""

import json
from datetime import date
from datetime import timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete as sql_delete

from backend.app.db.models import FxConversionRoute, FxRate
from backend.app.db.session import get_session_generator
from backend.app.logging_config import get_logger
from backend.app.schemas.common import BackwardFillInfo, DateRangeModel
from backend.app.schemas.fx import (
    # Provider models
    FXProviderInfo,
    # Conversion models
    FXConversionRequest,
    FXConversionResult,
    FXConvertResponse,
    # Rate upsert models
    FXUpsertItem,
    FXUpsertResult,
    FXBulkUpsertResponse,
    # Rate delete models
    FXDeleteItem,
    FXDeleteResult,
    FXBulkDeleteResponse,
    # Route models (replaces pair-source models)
    FXRouteStep,
    FXConversionRouteItem,
    FXConversionRoutesResponse,
    FXConversionRouteResult,
    FXCreateRoutesResponse,
    FXDeleteRouteItem,
    FXDeleteRouteResult,
    FXDeleteRoutesResponse,
    # Pairs list models
    )
from backend.app.schemas.refresh import FXSyncPairRequest, FXSyncBulkResponse
from backend.app.services.fx import (
    FXServiceError,
    convert_bulk,
    sync_pairs_bulk,
    upsert_rates_bulk,
    delete_rates_bulk,
    )
from backend.app.services.fx_providers.manual import MANUAL_PRIORITY
from backend.app.services.provider_registry import FXProviderRegistry

logger = get_logger(__name__)
fx_router = APIRouter(prefix="/fx", tags=["FX (Forex)"])
router_providers = APIRouter(prefix="/providers", tags=["FX Providers"])
router_currencies = APIRouter(prefix="/currencies", tags=["FX Currencies"])


# ============================================================================
# ENDPOINTS
# ============================================================================


def _build_providers_description() -> str:
    """Build dynamic description listing all installed FX providers."""
    try:
        installed = FXProviderRegistry.list_providers()
        codes = ", ".join(p["code"] for p in installed)
    except Exception:
        codes = "(auto-discovered at runtime)"
    return (
        "Get the list of available FX rate providers.\n\n"
        "Returns information about each provider including:\n"
        "- Provider code and name\n"
        "- Default base currency\n"
        "- All supported base currencies (for multi-base providers)\n"
        "- All target currencies (from get_supported_currencies)\n"
        "- Description and icon URL\n\n"
        "Note: This endpoint absorbed the former GET /fx/currencies endpoint.\n"
        "Target currencies are now returned per-provider instead of a separate call.\n\n"
        f"Installed providers: {codes}\n\n"
        "Use the `providers` query parameter to filter by specific provider codes."
    )


@router_providers.get("", response_model=List[FXProviderInfo], description=_build_providers_description())
async def list_providers(
    providers: Optional[List[str]] = Query(None, description="Optional list of provider codes to filter. If empty, returns all providers.", ),
    ):
    """Get the list of available FX rate providers, optionally filtered."""
    try:
        # Get all providers from registry
        providers_list = FXProviderRegistry.list_providers()

        # Always filter out MANUAL provider — it's an internal sentinel
        providers_list = [p for p in providers_list if p["code"] != "MANUAL"]

        # Filter by requested provider codes (case-insensitive)
        if providers:
            requested = {p.upper() for p in providers}
            providers_list = [p for p in providers_list if p["code"].upper() in requested]

        # Build provider info from instances
        result = []
        for provider_dict in providers_list:
            code = provider_dict["code"]
            instance = FXProviderRegistry.get_provider_instance(code)

            # Get base currencies (property always available in base class)
            base_currencies = instance.base_currencies

            # Get target currencies via async call
            try:
                target_currencies = await instance.get_supported_currencies()
            except Exception as e:
                logger.warning(f"Failed to fetch target currencies for {code}: {e}")
                target_currencies = []

            result.append(
                FXProviderInfo(
                    code=code,
                    name=provider_dict["name"],
                    base_currency=instance.base_currency,
                    base_currencies=base_currencies,
                    target_currencies=sorted(target_currencies),
                    description=getattr(
                        instance, "description", f'{provider_dict["name"]} FX rate provider'
                        ),
                    icon_url=instance.icon,
                    )
                )

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch providers: {str(e)}")


@router_currencies.post("/sync", response_model=FXSyncBulkResponse)
async def sync_rates(
    body: FXSyncPairRequest,
    session: AsyncSession = Depends(get_session_generator),
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
    if body.start > body.end:
        raise HTTPException(
            status_code=400, detail="Start date must be before or equal to end date"
            )
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
        raise HTTPException(status_code=400, detail=str(e))
    except FXServiceError as e:
        raise HTTPException(status_code=502, detail=f"Failed to sync rates: {str(e)}")


@router_currencies.post("/rate", response_model=FXBulkUpsertResponse, status_code=200)
async def upsert_rates_endpoint(
    rates: List[FXUpsertItem], session: AsyncSession = Depends(get_session_generator)
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

        # Ensure alphabetical ordering (base < quote)
        if base > quote:
            base, quote = quote, base
            # Invert rate
            rate_value = Decimal("1") / rate_item.rate
        else:
            rate_value = rate_item.rate

        try:
            # Use bulk service function
            rate_results = await upsert_rates_bulk(
                session, [(rate_item.rate_date, base, quote, rate_value, rate_item.source)]
                )

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
            error_msg = f"Rate {idx}: Validation error: {str(e)}"
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Rate {idx}: Failed: {str(e)}"
            errors.append(error_msg)

    # If all rates failed, return 400
    if errors and not results:
        raise HTTPException(status_code=400, detail=f"All rates failed: {'; '.join(errors)}")

    return FXBulkUpsertResponse(results=results, success_count=len(results), errors=errors)


@router_currencies.delete("/rate", response_model=FXBulkDeleteResponse)
async def delete_rates_endpoint(
    deletions: List[FXDeleteItem], session: AsyncSession = Depends(get_session_generator)
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
                count_stmt = select(FxRate).where(
                    FxRate.base == base, FxRate.quote == quote
                    )
                count_result = await session.execute(count_stmt)
                existing_count = len(count_result.scalars().all())

                # Delete all
                del_stmt = sql_delete(FxRate).where(
                    FxRate.base == base, FxRate.quote == quote
                    )
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
                errors.append(f"Delete all for {base}/{quote} failed: {str(e)}")
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
            for metadata, (success, existing_count, deleted_count, message) in zip(
                deletion_metadata, delete_results
                ):
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
            error_msg = f"Bulk deletion failed: {str(e)}"
            errors.append(error_msg)
            # If entire bulk operation failed, return 500
            raise HTTPException(status_code=500, detail=error_msg)

    # If all deletions failed validation, return 400
    if errors and not results:
        raise HTTPException(status_code=400, detail=f"All deletions failed validation: {'; '.join(errors)}")

    return FXBulkDeleteResponse(
        results=results,
        success_count=len([r for r in results if r.success]),
        total_deleted=total_deleted,
        errors=errors,
        )


import re

_RATE_NOT_FOUND_RE = re.compile(r"^Conversion \d+: No FX rate found for (\S+) on or before (\S+)\. (.+)$")


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


@router_currencies.post("/convert", response_model=FXConvertResponse)
async def convert_currency_bulk(
    request: List[FXConversionRequest], session: AsyncSession = Depends(get_session_generator)
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

    # Prepare bulk conversions, expanding date ranges
    bulk_conversions = []
    conversion_metadata = []  # Track which original conversion each bulk conversion belongs to

    for conv_idx, conversion in enumerate(request):
        to_cur = conversion.to_currency

        # Validate date range
        if conversion.date_range.end and conversion.date_range.start > conversion.date_range.end:
            raise HTTPException(
                status_code=400,
                detail=f"Conversion {conv_idx}: start date must be before or equal to end date",
                )

        # Expand date range into individual days
        # Now using new signature: (Currency, to_currency, date)
        if conversion.date_range.end:
            # Multi-day conversion: process each day in range
            current_date = conversion.date_range.start
            while current_date <= conversion.date_range.end:
                bulk_conversions.append((conversion.from_amount, to_cur, current_date))
                conversion_metadata.append({"original_idx": conv_idx, "conversion": conversion, "date": current_date})
                current_date += timedelta(days=1)
        else:
            # Single-day conversion
            bulk_conversions.append((conversion.from_amount, to_cur, conversion.date_range.start))
            conversion_metadata.append(
                {
                    "original_idx": conv_idx,
                    "conversion": conversion,
                    "date": conversion.date_range.start,
                    }
                )

    # Call convert_bulk with raise_on_error=False to get partial results
    bulk_results, bulk_errors = await convert_bulk(session, bulk_conversions, raise_on_error=False)

    results = []

    # Process results
    for idx, (metadata, bulk_result) in enumerate(zip(conversion_metadata, bulk_results)):
        if bulk_result is None:
            # This conversion failed (error already in bulk_errors)
            continue

        # bulk_result is now (Currency, rate_date, backward_fill_applied)
        converted_currency, actual_rate_date, backward_fill_applied = bulk_result
        conversion = metadata["conversion"]
        on_date = metadata["date"]
        from_cur = conversion.from_amount.code
        to_cur = conversion.to_currency

        # Calculate effective rate (for display purposes)
        rate = None
        if from_cur != to_cur:
            rate = converted_currency.amount / conversion.from_amount.amount

        # Build backward-fill info if applicable
        backward_fill_info = None
        if backward_fill_applied:
            days_back = (on_date - actual_rate_date).days
            backward_fill_info = BackwardFillInfo(
                actual_rate_date=actual_rate_date, days_back=days_back
                )

        results.append(
            FXConversionResult(
                from_amount=conversion.from_amount,
                to_amount=converted_currency,  # Already a Currency object
                conversion_date=on_date.isoformat(),
                rate=rate,
                backward_fill_info=backward_fill_info,
                )
            )

    # Compress repeated errors (e.g. same pair missing for N dates → single message)
    compressed_errors = _compress_convert_errors(bulk_errors) if bulk_errors else []

    # If all conversions failed, return 404
    if bulk_errors and not results:
        raise HTTPException(status_code=404, detail=f"All conversions failed: {'; '.join(compressed_errors)}")

    return FXConvertResponse(
        results=results,
        success_count=len([r for r in results if r.to_amount is not None]),
        errors=compressed_errors,
        )


# ============================================================================
# PROVIDER CONFIGURATION ENDPOINTS
# ============================================================================


@router_providers.get("/routes", response_model=FXConversionRoutesResponse)
async def list_routes(session: AsyncSession = Depends(get_session_generator)):
    """
    Get the list of configured conversion routes.

    Returns all configured routes ordered by base, quote, and priority.
    Each route contains chain_steps describing how to compute the rate.

    Returns:
        List of conversion route configurations
    """
    try:
        stmt = select(FxConversionRoute).order_by(FxConversionRoute.base, FxConversionRoute.quote, FxConversionRoute.priority)
        result = await session.execute(stmt)
        routes = result.scalars().all()

        routes_list = [
            FXConversionRouteItem(
                base=r.base, quote=r.quote, priority=r.priority,
                chain_steps=[FXRouteStep(**s) for s in json.loads(r.chain_steps)],
                )
            for r in routes
            ]

        return FXConversionRoutesResponse(items=routes_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch routes: {str(e)}")


@router_providers.post("/routes", response_model=FXCreateRoutesResponse, status_code=201)
async def create_routes_bulk(
    routes: List[FXConversionRouteItem], session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Create or update multiple conversion routes in a single atomic transaction.

    Validations:
    - base < quote (alphabetical ordering)
    - Provider codes must be registered in FXProviderRegistry
    - Chain steps must be valid (continuity, no repeated edges, matching endpoints)

    Args:
        routes: List of routes to create/update
        session: Database session

    Returns:
        Results for each route operation
    """
    results = []
    success_count = 0
    error_count = 0

    try:
        available_providers = {p["code"] for p in FXProviderRegistry.list_providers()}

        for route_item in routes:
            # Validate all provider codes in chain_steps
            invalid_providers = []
            for step in route_item.chain_steps:
                if step.provider.upper() not in available_providers:
                    invalid_providers.append(step.provider)

            if invalid_providers:
                results.append(
                    FXConversionRouteResult(
                        success=False,
                        action="error",
                        base=route_item.base,
                        quote=route_item.quote,
                        priority=route_item.priority,
                        chain_steps=route_item.chain_steps,
                        message=f"Unknown provider(s): {', '.join(invalid_providers)}",
                        )
                    )
                error_count += 1
                continue

            # Normalize base/quote to alphabetical order
            base = min(route_item.base.upper(), route_item.quote.upper())
            quote = max(route_item.base.upper(), route_item.quote.upper())

            # Serialize chain_steps to JSON
            chain_steps_json = json.dumps([
                {"from": s.from_currency, "to": s.to_currency, "provider": s.provider}
                for s in route_item.chain_steps
                ])

            # Check if already exists
            stmt = select(FxConversionRoute).where(
                FxConversionRoute.base == base,
                FxConversionRoute.quote == quote,
                FxConversionRoute.priority == route_item.priority,
                )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.chain_steps = chain_steps_json
                session.add(existing)
                action = "updated"
            else:
                new_route = FxConversionRoute(
                    base=base,
                    quote=quote,
                    priority=route_item.priority,
                    chain_steps=chain_steps_json,
                    )
                session.add(new_route)
                action = "created"

            results.append(
                FXConversionRouteResult(
                    success=True,
                    action=action,
                    base=base,
                    quote=quote,
                    priority=route_item.priority,
                    chain_steps=route_item.chain_steps,
                    message=None,
                    )
                )
            success_count += 1

        if error_count > 0:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "message": f"Validation failed for {error_count} route(s). Transaction rolled back.",
                    "results": [r.model_dump() for r in results],
                    },
                )

        # Auto-remove MANUAL sentinel for pairs that now have real providers
        pairs_with_real_providers = set()
        for route_item in routes:
            has_real = any(s.provider.upper() != "MANUAL" for s in route_item.chain_steps)
            if has_real:
                b = min(route_item.base.upper(), route_item.quote.upper())
                q = max(route_item.base.upper(), route_item.quote.upper())
                pairs_with_real_providers.add((b, q))

        for base, quote in pairs_with_real_providers:
            # Delete MANUAL routes for this pair
            manual_del = sql_delete(FxConversionRoute).where(
                FxConversionRoute.base == base,
                FxConversionRoute.quote == quote,
                # A route is MANUAL if chain_steps contains only MANUAL provider
                # We check by looking for routes where chain_steps has MANUAL
                )
            # More targeted: find MANUAL routes
            manual_stmt = select(FxConversionRoute).where(
                FxConversionRoute.base == base,
                FxConversionRoute.quote == quote,
                )
            manual_result = await session.execute(manual_stmt)
            manual_routes = manual_result.scalars().all()
            for mr in manual_routes:
                steps = mr.parsed_steps
                if all(s["provider"].upper() == "MANUAL" for s in steps):
                    await session.delete(mr)
                    logger.info(f"Auto-removed MANUAL sentinel for {base}/{quote} (real provider added)")

        await session.commit()

        return FXCreateRoutesResponse(results=results, success_count=success_count, error_count=error_count)

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create routes: {str(e)}")


@router_providers.delete("/routes", response_model=FXDeleteRoutesResponse)
async def delete_routes_bulk(
    routes: List[FXDeleteRouteItem], session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Delete multiple conversion routes.

    If priority is specified, deletes only that specific priority level.
    If priority is omitted, deletes ALL priorities for that pair.

    Args:
        routes: List of FXDeleteRouteItem to delete
        session: Database session

    Returns:
        FXDeleteRoutesResponse with results for each deletion operation
    """
    results = []
    total_deleted = 0

    try:
        for route_item in routes:
            base = route_item.base
            quote = route_item.quote
            priority = route_item.priority

            # Normalize to alphabetical
            norm_base = min(base, quote)
            norm_quote = max(base, quote)

            if priority is not None:
                stmt = sql_delete(FxConversionRoute).where(
                    FxConversionRoute.base == norm_base,
                    FxConversionRoute.quote == norm_quote,
                    FxConversionRoute.priority == priority,
                    )
            else:
                stmt = sql_delete(FxConversionRoute).where(
                    FxConversionRoute.base == norm_base,
                    FxConversionRoute.quote == norm_quote,
                    )

            result = await session.execute(stmt)
            deleted_count = result.rowcount

            if deleted_count == 0:
                priority_str = f" with priority={priority}" if priority else ""
                results.append(
                    FXDeleteRouteResult(
                        success=True,
                        base=norm_base,
                        quote=norm_quote,
                        priority=priority,
                        deleted_count=0,
                        message=f"Route {norm_base}/{norm_quote}{priority_str} not found (nothing to delete)",
                        )
                    )
            else:
                results.append(
                    FXDeleteRouteResult(
                        success=True,
                        base=norm_base,
                        quote=norm_quote,
                        priority=priority,
                        deleted_count=deleted_count,
                        message=None,
                        )
                    )
                total_deleted += deleted_count

        # Auto-reinstate MANUAL sentinel for pairs that have no routes left
        affected_pairs = set()
        for route_item in routes:
            if route_item.priority is not None:
                b = min(route_item.base, route_item.quote)
                q = max(route_item.base, route_item.quote)
                affected_pairs.add((b, q))

        for base, quote in affected_pairs:
            count_stmt = select(FxConversionRoute).where(
                FxConversionRoute.base == base,
                FxConversionRoute.quote == quote,
                )
            remaining = await session.execute(count_stmt)
            remaining_routes = remaining.scalars().all()

            # Check if any non-MANUAL route exists
            has_real = False
            for r in remaining_routes:
                steps = r.parsed_steps
                if not all(s["provider"].upper() == "MANUAL" for s in steps):
                    has_real = True
                    break

            if not has_real and not any(
                all(s["provider"].upper() == "MANUAL" for s in r.parsed_steps)
                for r in remaining_routes
                ):
                manual_route = FxConversionRoute(
                    base=base, quote=quote,
                    priority=MANUAL_PRIORITY,
                    chain_steps=json.dumps([{"from": base, "to": quote, "provider": "MANUAL"}]),
                    )
                session.add(manual_route)
                logger.info(f"Auto-reinstated MANUAL sentinel for {base}/{quote} (no real providers left)")

        await session.commit()

        return FXDeleteRoutesResponse(
            results=results,
            success_count=len([r for r in results if r.success]),
            total_deleted=total_deleted,
            )

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete routes: {str(e)}")


# ============================================================================
# Include sub-route in main router
# ============================================================================
fx_router.include_router(router_providers)
fx_router.include_router(router_currencies)
