"""
FX (Foreign Exchange) API endpoints.
Handles currency conversion and FX rate synchronization.
"""

from datetime import date
from datetime import timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete as sql_delete, and_, or_

from backend.app.db.models import FxCurrencyPairSource, FxRate
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
    # Pair source models
    FXPairSourceItem,
    FXPairSourcesResponse,
    FXPairSourceResult,
    FXCreatePairSourcesResponse,
    FXDeletePairSourceItem,
    FXDeletePairSourceResult,
    FXDeletePairSourcesResponse,
    # Pairs list models
    FXPairItem,
    FXPairsListResponse,
    )
from backend.app.schemas.refresh import FXSyncPairRequest, FXSyncBulkResponse
from backend.app.services.fx import (
    FXServiceError,
    convert_bulk,
    sync_pairs_bulk,
    upsert_rates_bulk,
    delete_rates_bulk,
    )
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
        providers: Optional[List[str]] = Query(None,description="Optional list of provider codes to filter. If empty, returns all providers.",),
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
    Each pair is synced independently using configured providers from
    fx_currency_pair_sources table, with automatic fallback to lower-priority providers.

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
        raise HTTPException(
            status_code=400, detail=f"All deletions failed validation: {'; '.join(errors)}"
            )

    return FXBulkDeleteResponse(
        results=results,
        success_count=len([r for r in results if r.success]),
        total_deleted=total_deleted,
        errors=errors,
        )


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
                conversion_metadata.append(
                    {"original_idx": conv_idx, "conversion": conversion, "date": current_date}
                    )
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

    # If all conversions failed, return 404
    if bulk_errors and not results:
        raise HTTPException(
            status_code=404, detail=f"All conversions failed: {'; '.join(bulk_errors)}"
            )

    return FXConvertResponse(
        results=results,
        success_count=len([r for r in results if r.to_amount is not None]),
        errors=bulk_errors,
        )


# ============================================================================
# PROVIDER CONFIGURATION ENDPOINTS
# ============================================================================


@router_providers.get("/pair-sources", response_model=FXPairSourcesResponse)
async def list_pair_sources(session: AsyncSession = Depends(get_session_generator)):
    """
    Get the list of configured currency pair sources.

    Returns all configured mappings of currency pairs to providers,
    ordered by base, quote, and priority.

    Returns:
        List of pair source configurations
    """
    try:
        stmt = select(FxCurrencyPairSource).order_by(
            FxCurrencyPairSource.base, FxCurrencyPairSource.quote, FxCurrencyPairSource.priority
            )
        result = await session.execute(stmt)
        sources = result.scalars().all()

        sources_list = [
            FXPairSourceItem(
                base=s.base, quote=s.quote, provider_code=s.provider_code, priority=s.priority
                )
            for s in sources
            ]

        return FXPairSourcesResponse(items=sources_list)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pair sources: {str(e)}")


@router_providers.post("/pair-sources", response_model=FXCreatePairSourcesResponse, status_code=201)
async def create_pair_sources_bulk(
    sources: List[FXPairSourceItem], session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Create or update multiple currency pair sources in a single atomic transaction.

    Validations:
    - base < quote (alphabetical ordering)
    - Provider code must be registered in FXProviderRegistry
    - Priority must be >= 1

    Args:
        sources: List of pair sources to create/update
        session: Database session

    Returns:
        Results for each pair source operation
    """
    results = []
    success_count = 0
    error_count = 0

    try:
        # Validate all provider codes exist
        available_providers = {p["code"] for p in FXProviderRegistry.list_providers()}

        # OPTIMIZATION: Batch query for inverse pairs conflict detection
        # Build list of all inverse pairs to check in ONE query
        inverse_checks = []
        for source in sources:
            # Inverse pair: swap base/quote
            inverse_checks.append((source.quote.upper(), source.base.upper(), source.priority))

        # Single batch query: check if ANY inverse pairs exist with SAME priority
        if inverse_checks:
            inverse_conditions = []
            for inv_base, inv_quote, inv_priority in inverse_checks:
                inverse_conditions.append(
                    and_(
                        FxCurrencyPairSource.base == inv_base,
                        FxCurrencyPairSource.quote == inv_quote,
                        FxCurrencyPairSource.priority == inv_priority,
                        )
                    )

            inverse_stmt = select(
                FxCurrencyPairSource.base, FxCurrencyPairSource.quote, FxCurrencyPairSource.priority
                ).where(or_(*inverse_conditions))

            inverse_result = await session.execute(inverse_stmt)
            existing_inverses = {
                (row.base, row.quote, row.priority) for row in inverse_result.all()
                }
        else:
            existing_inverses = set()

        # Validate each source
        for source in sources:
            # Validate provider exists
            if source.provider_code.upper() not in available_providers:
                results.append(
                    FXPairSourceResult(
                        success=False,
                        action="error",
                        base=source.base,
                        quote=source.quote,
                        provider_code=source.provider_code,
                        priority=source.priority,
                        message=f"Unknown provider: {source.provider_code}",
                        )
                    )
                error_count += 1
                continue

            # Check for inverse pair conflict (same priority)
            inverse_key = (source.quote.upper(), source.base.upper(), source.priority)
            if inverse_key in existing_inverses:
                results.append(
                    FXPairSourceResult(
                        success=False,
                        action="error",
                        base=source.base,
                        quote=source.quote,
                        provider_code=source.provider_code,
                        priority=source.priority,
                        message=f"Conflict: Inverse pair {source.quote}/{source.base} with priority={source.priority} already exists. Use different priority.",
                        )
                    )
                error_count += 1
                continue

            # Check if already exists
            stmt = select(FxCurrencyPairSource).where(
                FxCurrencyPairSource.base == source.base.upper(),
                FxCurrencyPairSource.quote == source.quote.upper(),
                FxCurrencyPairSource.priority == source.priority,
                )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update
                existing.provider_code = source.provider_code.upper()
                session.add(existing)
                action = "updated"
            else:
                # Insert
                new_source = FxCurrencyPairSource(
                    base=source.base.upper(),
                    quote=source.quote.upper(),
                    provider_code=source.provider_code.upper(),
                    priority=source.priority,
                    )
                session.add(new_source)
                action = "created"

            results.append(
                FXPairSourceResult(
                    success=True,
                    action=action,
                    base=source.base.upper(),
                    quote=source.quote.upper(),
                    provider_code=source.provider_code.upper(),
                    priority=source.priority,
                    message=None,
                    )
                )
            success_count += 1

        # Commit only if all validations passed
        if error_count > 0:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "message": f"Validation failed for {error_count} source(s). Transaction rolled back.",
                    "results": [r.model_dump() for r in results],
                    },
                )

        # Auto-remove MANUAL sentinel for pairs that now have real providers
        pairs_with_real_providers = set()
        for source in sources:
            if source.provider_code.upper() != "MANUAL":
                b, q = source.base.upper(), source.quote.upper()
                pairs_with_real_providers.add((min(b, q), max(b, q)))

        for base, quote in pairs_with_real_providers:
            manual_del = sql_delete(FxCurrencyPairSource).where(
                FxCurrencyPairSource.base == base,
                FxCurrencyPairSource.quote == quote,
                FxCurrencyPairSource.provider_code == "MANUAL",
                )
            del_result = await session.execute(manual_del)
            if del_result.rowcount > 0:
                logger.info(f"Auto-removed MANUAL sentinel for {base}/{quote} (real provider added)")

        await session.commit()

        return FXCreatePairSourcesResponse(
            results=results, success_count=success_count, error_count=error_count
            )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create pair sources: {str(e)}")


@router_providers.delete("/pair-sources", response_model=FXDeletePairSourcesResponse)
async def delete_pair_sources_bulk(
    sources: List[FXDeletePairSourceItem], session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Delete multiple currency pair sources.

    If priority is specified, deletes only that specific priority level.
    If priority is omitted, deletes ALL priorities for that pair.

    Warnings (not errors):
    - If a pair doesn't exist, logs a warning but continues

    Args:
        sources: List of FXDeletePairSourceItem to delete
        session: Database session

    Returns:
        FXDeletePairSourcesResponse with results for each deletion operation
    """
    results = []
    total_deleted = 0

    try:
        for source_item in sources:
            # Now we have a proper Pydantic model with validation
            base = source_item.base  # Already uppercase from validator
            quote = source_item.quote  # Already uppercase from validator
            priority = source_item.priority

            # Build delete query
            if priority is not None:
                # Delete specific priority
                stmt = sql_delete(FxCurrencyPairSource).where(
                    FxCurrencyPairSource.base == base,
                    FxCurrencyPairSource.quote == quote,
                    FxCurrencyPairSource.priority == priority,
                    )
            else:
                # Delete all priorities for this pair
                stmt = sql_delete(FxCurrencyPairSource).where(
                    FxCurrencyPairSource.base == base, FxCurrencyPairSource.quote == quote
                    )

            result = await session.execute(stmt)
            deleted_count = result.rowcount

            if deleted_count == 0:
                # Warning: pair not found
                priority_str = f" with priority={priority}" if priority else ""
                results.append(
                    FXDeletePairSourceResult(
                        success=True,  # Not an error, just a warning
                        base=base,
                        quote=quote,
                        priority=priority,
                        deleted_count=0,
                        message=f"Pair {base}/{quote}{priority_str} not found (nothing to delete)",
                        )
                    )
            else:
                results.append(
                    FXDeletePairSourceResult(
                        success=True,
                        base=base,
                        quote=quote,
                        priority=priority,
                        deleted_count=deleted_count,
                        message=None,
                        )
                    )
                total_deleted += deleted_count

        # Auto-reinstate MANUAL sentinel for pairs that have no real providers left
        # ONLY when deleting specific providers (with priority), NOT when deleting entire pair.
        # When priority is None, the user intentionally deletes the entire pair configuration.
        affected_pairs = set()
        for source_item in sources:
            if source_item.priority is not None:
                # Only track pairs where a specific provider was removed
                b, q = source_item.base, source_item.quote  # Already uppercase from validator
                affected_pairs.add((min(b, q), max(b, q)))

        for base, quote in affected_pairs:
            # Count remaining real providers (non-MANUAL)
            count_stmt = select(FxCurrencyPairSource).where(
                FxCurrencyPairSource.base == base,
                FxCurrencyPairSource.quote == quote,
                FxCurrencyPairSource.provider_code != "MANUAL",
                )
            remaining = await session.execute(count_stmt)
            real_count = len(remaining.scalars().all())

            if real_count == 0:
                # Check if MANUAL already exists
                manual_check = select(FxCurrencyPairSource).where(
                    FxCurrencyPairSource.base == base,
                    FxCurrencyPairSource.quote == quote,
                    FxCurrencyPairSource.provider_code == "MANUAL",
                    )
                manual_exists = (await session.execute(manual_check)).scalar_one_or_none()

                if not manual_exists:
                    from backend.app.services.fx_providers.manual import MANUAL_PRIORITY
                    manual_source = FxCurrencyPairSource(
                        base=base, quote=quote,
                        provider_code="MANUAL", priority=MANUAL_PRIORITY,
                        )
                    session.add(manual_source)
                    logger.info(f"Auto-reinstated MANUAL sentinel for {base}/{quote} (no real providers left)")

        await session.commit()

        return FXDeletePairSourcesResponse(
            results=results,
            success_count=len([r for r in results if r.success]),
            total_deleted=total_deleted,
            )

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete pair sources: {str(e)}")


# ============================================================================
# Include sub-route in main router
# ============================================================================
fx_router.include_router(router_providers)
fx_router.include_router(router_currencies)
