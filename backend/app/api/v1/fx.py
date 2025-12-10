"""
FX (Foreign Exchange) API endpoints.
Handles currency conversion and FX rate synchronization.
"""
from datetime import date
from datetime import timedelta
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete as sql_delete, and_, or_

from backend.app.db.models import FxCurrencyPairSource
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
    FXCurrenciesResponse,
    )
from backend.app.schemas.refresh import FXSyncResponse
from backend.app.services.fx import (
    FXServiceError,
    convert_bulk,
    ensure_rates_multi_source,
    upsert_rates_bulk,
    delete_rates_bulk,
    )
from backend.app.services.provider_registry import FXProviderRegistry

logger = get_logger(__name__)
fx_router = APIRouter(prefix="/fx", tags=["FX"])
router_providers = APIRouter(prefix="/providers", tags=["FX Providers"])
router_currencies = APIRouter(prefix="/currencies", tags=["FX Currencies"])

# ============================================================================
# ENDPOINTS
# ============================================================================

@router_providers.get("", response_model=List[FXProviderInfo])
async def list_providers():
    """
    Get the list of all available FX rate providers.

    Returns information about each provider including:
    - Provider code and name
    - Default base currency
    - All supported base currencies (for multi-base providers)
    - Description
    - Icon URL

    Returns:
        List of provider information
    """
    try:
        # Get all providers from registry
        providers_list = FXProviderRegistry.list_providers()

        # Build provider info from instances
        providers = []
        for provider_dict in providers_list:
            code = provider_dict['code']
            instance = FXProviderRegistry.get_provider_instance(code)

            # Get base currencies (all supported or just default)
            if hasattr(instance, 'base_currencies') and instance.base_currencies:
                base_currencies = instance.base_currencies
            else:
                base_currencies = [instance.base_currency]

            providers.append(FXProviderInfo(
                code=code,
                name=provider_dict['name'],
                base_currency=instance.base_currency,
                base_currencies=base_currencies,
                description=getattr(instance, 'description', f'{provider_dict["name"]} FX rate provider'),
                icon_url=instance.get_icon()
                ))

        return providers  # Return list directly, no wrapper
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch providers: {str(e)}")


@router_currencies.get("", response_model=FXCurrenciesResponse)
async def list_currencies(
    provider: str = Query("ECB", description="Provider code (ECB, FED, BOE, SNB)")
    ):
    """
    Get the list of available currencies from specified provider.

    Args:
        provider: Provider code (default: ECB)

    Returns:
        List of ISO 4217 currency codes
    """
    try:
        provider_instance = FXProviderRegistry.get_provider_instance(provider)
        if not provider_instance:
            available = [p['code'] for p in FXProviderRegistry.list_providers()]
            raise HTTPException(
                status_code=400,
                detail=f"Unknown FX provider: {provider}. Available providers: {', '.join(available) if available else 'none registered'}"
                )

        currencies = await provider_instance.get_supported_currencies()
        return FXCurrenciesResponse(currencies=currencies, count=len(currencies))
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FXServiceError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch currencies: {str(e)}")


@router_currencies.get("/sync", response_model=FXSyncResponse)
async def sync_rates(
    start: date = Query(..., description="Start date (inclusive)"),
    end: date = Query(..., description="End date (inclusive)"),
    currencies: str = Query("USD,GBP,CHF,JPY", description="Comma-separated currency codes"),
    provider: str | None = Query(None, description="Provider code (ECB, FED, BOE, SNB). If NULL, uses fx_currency_pair_sources configuration."),
    base_currency: str | None = Query(None, description="Base currency (for multi-base providers)"),
    session: AsyncSession = Depends(get_session_generator)
    ):
    """
    Synchronize FX rates for the specified date range and currencies.

    **Two modes of operation**:

    1. **Explicit Provider Mode** (provider parameter specified):
       - Forces the specified provider for all currencies
       - Ignores fx_currency_pair_sources configuration
       - Backward compatible with previous API

    2. **Auto-Configuration Mode** (provider=NULL):
       - Consults fx_currency_pair_sources table
       - Uses priority=1 provider for each currency pair
       - Fails with explicit error if configuration missing

    Args:
        start: Start date (inclusive)
        end: End date (inclusive)
        currencies: Comma-separated currency codes (e.g., "USD,GBP,CHF")
        provider: (Optional) Force specific provider. If NULL, uses configuration.
        base_currency: (Optional) Base currency for multi-base providers
        session: Database session

    Returns:
        Sync statistics
    """
    # Validate date range
    if start > end:
        raise HTTPException(status_code=400, detail="Start date must be before or equal to end date")
    if end > date.today():
        raise HTTPException(status_code=400, detail="End date cannot be in the future")

    # Parse currencies
    currency_list = [c.strip().upper() for c in currencies.split(",") if c.strip()]
    if not currency_list:
        raise HTTPException(status_code=400, detail="At least one currency must be specified")

    try:
        if provider:
            # EXPLICIT PROVIDER MODE: Force specified provider
            result = await ensure_rates_multi_source(
                session,
                (start, end),
                currency_list,
                provider_code=provider,
                base_currency=base_currency
                )
            return FXSyncResponse(
                synced=result['total_changed'],
                date_range=DateRangeModel(start=start, end=end),
                currencies=result['currencies_synced']
                )

        else:
            # AUTO-CONFIGURATION MODE: Use fx_currency_pair_sources with fallback logic
            # Query ALL configured pair sources (all priorities), ordered by priority ASC
            stmt = select(FxCurrencyPairSource).order_by(
                FxCurrencyPairSource.base,
                FxCurrencyPairSource.quote,
                FxCurrencyPairSource.priority
                )
            result = await session.execute(stmt)
            all_pair_sources = result.scalars().all()

            if not all_pair_sources:
                raise HTTPException(
                    status_code=400,
                    detail="No currency pair sources configured. Please either: "
                           "(1) specify 'provider' parameter explicitly, or "
                           "(2) configure pair sources via POST /fx/pair-sources/bulk"
                    )

            # Build lookup: (base, quote) -> list of (provider_code, priority) ordered by priority
            config_lookup = {}
            for ps in all_pair_sources:
                key = (ps.base, ps.quote)
                if key not in config_lookup:
                    config_lookup[key] = []
                config_lookup[key].append((ps.provider_code, ps.priority))

            # For each configured pair, assign to its primary provider
            # This handles inverse pairs correctly (EUR/USD → ECB, USD/EUR → FED)
            provider_pairs = {}  # provider_code -> set of (base, quote) tuples

            for (base, quote), providers_list in config_lookup.items():
                # Use primary provider (priority=1 or lowest)
                primary_provider = providers_list[0][0]

                if primary_provider not in provider_pairs:
                    provider_pairs[primary_provider] = set()

                provider_pairs[primary_provider].add((base, quote))

            # Convert pairs to currencies for each provider
            provider_currencies = {}
            for provider_code, pairs in provider_pairs.items():
                currencies = set()
                for base, quote in pairs:
                    currencies.add(base)
                    currencies.add(quote)
                provider_currencies[provider_code] = currencies

            # Check if ALL requested currencies are covered
            all_configured_currencies = set()
            for currencies in provider_currencies.values():
                all_configured_currencies.update(currencies)

            missing_pairs = []
            for curr in currency_list:
                if curr not in all_configured_currencies:
                    missing_pairs.append(curr)

            if missing_pairs:
                raise HTTPException(
                    status_code=400,
                    detail=f"No configuration found for currencies: {', '.join(missing_pairs)}. "
                           f"Please configure pair sources via POST /fx/pair-sources/bulk "
                           f"or use explicit 'provider' parameter."
                    )

            # Execute sync with fallback logic
            total_changed = 0
            total_fetched = 0
            all_currencies_synced = set()
            final_errors = []

            # Group by provider and try each one (with fallbacks if configured)
            for provider_code, currencies_set in provider_currencies.items():
                currencies_list = list(currencies_set)

                # Try primary provider first
                try:
                    result = await ensure_rates_multi_source(
                        session,
                        (start, end),
                        currencies_list,
                        provider_code=provider_code,
                        base_currency=None
                        )
                    total_changed += result['total_changed']
                    total_fetched += result['total_fetched']
                    all_currencies_synced.update(result['currencies_synced'])

                except FXServiceError as e:
                    # Provider failed - try fallback providers if configured
                    logger.warning(f"Provider {provider_code} (priority=1) failed: {str(e)}")

                    # Find fallback providers for any pair in this currency set
                    fallback_attempted = False
                    for base, quote in [(c1, c2) for c1 in currencies_list for c2 in currencies_list if c1 < c2]:
                        pair_key = (base, quote)
                        if pair_key in config_lookup and len(config_lookup[pair_key]) > 1:
                            # Has fallback providers (priority > 1)
                            for fallback_provider, fallback_priority in config_lookup[pair_key][1:]:
                                logger.info(f"Trying fallback provider {fallback_provider} (priority={fallback_priority}) for {base}/{quote}")
                                fallback_attempted = True

                                try:
                                    result = await ensure_rates_multi_source(
                                        session,
                                        (start, end),
                                        [base, quote],
                                        provider_code=fallback_provider,
                                        base_currency=None
                                        )
                                    total_changed += result['total_changed']
                                    total_fetched += result['total_fetched']
                                    all_currencies_synced.update(result['currencies_synced'])
                                    logger.info(f"Fallback successful: {fallback_provider} provided {base}/{quote}")
                                    break  # Success, no need to try more fallbacks for this pair

                                except FXServiceError as fallback_e:
                                    logger.warning(f"Fallback provider {fallback_provider} (priority={fallback_priority}) also failed: {str(fallback_e)}")
                                    continue  # Try next fallback

                    if not fallback_attempted:
                        # No fallbacks configured, record error
                        final_errors.append(f"Provider {provider_code} failed: {str(e)}")

            # If all providers failed and no currencies synced, raise error
            if final_errors and not all_currencies_synced:
                raise HTTPException(
                    status_code=502,
                    detail=f"All providers failed: {'; '.join(final_errors)}"
                    )

            return FXSyncResponse(
                synced=total_changed,
                date_range=DateRangeModel(start=start, end=end),
                currencies=sorted(list(all_currencies_synced))
                )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FXServiceError as e:
        raise HTTPException(status_code=502, detail=f"Failed to sync rates: {str(e)}")


@router_currencies.post("/rate", response_model=FXBulkUpsertResponse, status_code=200)
async def upsert_rates_endpoint(
    rates: List[FXUpsertItem],
    session: AsyncSession = Depends(get_session_generator)
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
                session,
                [(rate_item.rate_date, base, quote, rate_value, rate_item.source)]
                )

            success, action = rate_results[0]

            results.append(FXUpsertResult(
                success=success,
                action=action,
                rate=rate_value,
                date=rate_item.rate_date.isoformat(),
                base=base,
                quote=quote
                ))

        except ValueError as e:
            error_msg = f"Rate {idx}: Validation error: {str(e)}"
            errors.append(error_msg)
        except Exception as e:
            error_msg = f"Rate {idx}: Failed: {str(e)}"
            errors.append(error_msg)

    # If all rates failed, return 400
    if errors and not results:
        raise HTTPException(
            status_code=400,
            detail=f"All rates failed: {'; '.join(errors)}"
            )

    return FXBulkUpsertResponse(
        results=results,
        success_count=len(results),
        errors=errors
        )


@router_currencies.delete("/rate", response_model=FXBulkDeleteResponse)
async def delete_rates_endpoint(
    deletions: List[FXDeleteItem],
    session: AsyncSession = Depends(get_session_generator)
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

    # Prepare deletions for bulk service call
    bulk_deletions = []
    deletion_metadata = []  # Track original request info for response

    for idx, delete_req in enumerate(deletions):
        from_cur = delete_req.from_currency.upper()
        to_cur = delete_req.to_currency.upper()

        # Validate currencies are different
        if from_cur == to_cur:
            error_msg = f"Deletion {idx}: from and to currencies must be different (got {from_cur})"
            errors.append(error_msg)
            continue

        # Extract dates from DateRangeModel
        start_date = delete_req.date_range.start
        end_date = delete_req.date_range.end

        # Add to bulk deletions (backend will normalize)
        bulk_deletions.append((
            from_cur,
            to_cur,
            start_date,
            end_date
            ))

        deletion_metadata.append({
            'original_idx': idx,
            'from_currency': from_cur,
            'to_currency': to_cur,
            'start_date': start_date,
            'end_date': end_date
            })

    # Execute bulk deletions if any valid
    if bulk_deletions:
        try:
            # Call backend service (normalizes and executes)
            delete_results = await delete_rates_bulk(session, bulk_deletions)

            # Process results
            for metadata, (success, existing_count, deleted_count, message) in zip(deletion_metadata, delete_results):
                # Backend normalized the pair, we need to figure out what it became
                # For display, we'll show the normalized version
                from_cur = metadata['from_currency']
                to_cur = metadata['to_currency']

                # Normalize for display (same logic as backend)
                if from_cur > to_cur:
                    base, quote = to_cur, from_cur
                else:
                    base, quote = from_cur, to_cur

                results.append(FXDeleteResult(
                    success=success,
                    base=base,
                    quote=quote,
                    date_range=DateRangeModel(
                        start=metadata['start_date'],
                        end=metadata['end_date'] if metadata['end_date'] else None
                        ),
                    existing_count=existing_count,
                    deleted_count=deleted_count,
                    message=message
                    ))

                total_deleted += deleted_count

        except Exception as e:
            error_msg = f"Bulk deletion failed: {str(e)}"
            errors.append(error_msg)
            # If entire bulk operation failed, return 500
            raise HTTPException(status_code=500, detail=error_msg)

    # If all deletions failed validation, return 400
    if errors and not results:
        raise HTTPException(
            status_code=400,
            detail=f"All deletions failed validation: {'; '.join(errors)}"
            )

    return FXBulkDeleteResponse(
        results=results,
        success_count=len([r for r in results if r.success]),
        total_deleted=total_deleted,
        errors=errors
        )


@router_currencies.post("/convert", response_model=FXConvertResponse)
async def convert_currency_bulk(
    request: List[FXConversionRequest],
    session: AsyncSession = Depends(get_session_generator)
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
        from_cur = conversion.from_currency.upper()
        to_cur = conversion.to_currency.upper()

        # Validate date range
        if conversion.date_range.end and conversion.date_range.start > conversion.date_range.end:
            raise HTTPException(
                status_code=400,
                detail=f"Conversion {conv_idx}: start date must be before or equal to end date"
                )

        # Expand date range into individual days
        if conversion.date_range.end:
            # Multi-day conversion: process each day in range
            current_date = conversion.date_range.start
            while current_date <= conversion.date_range.end:
                bulk_conversions.append((conversion.amount, from_cur, to_cur, current_date))
                conversion_metadata.append({
                    'original_idx': conv_idx,
                    'conversion': conversion,
                    'date': current_date
                    })
                current_date += timedelta(days=1)
        else:
            # Single-day conversion
            bulk_conversions.append((conversion.amount, from_cur, to_cur, conversion.date_range.start))
            conversion_metadata.append({
                'original_idx': conv_idx,
                'conversion': conversion,
                'date': conversion.date_range.start
                })


    # Call convert_bulk with raise_on_error=False to get partial results
    bulk_results, bulk_errors = await convert_bulk(session, bulk_conversions, raise_on_error=False)

    results = []

    # Process results
    for idx, (metadata, bulk_result) in enumerate(zip(conversion_metadata, bulk_results)):
        if bulk_result is None:
            # This conversion failed (error already in bulk_errors)
            continue

        converted_amount, actual_rate_date, backward_fill_applied = bulk_result
        conversion = metadata['conversion']
        on_date = metadata['date']
        # TODO: portare questi upper dentro la classe che astrae la valuta, ancora da fare
        from_cur = conversion.from_currency.upper()
        to_cur = conversion.to_currency.upper()

        # Calculate effective rate (for display purposes)
        rate = None
        if from_cur != to_cur:
            rate = converted_amount / conversion.amount

        # Build backward-fill info if applicable
        backward_fill_info = None
        if backward_fill_applied:
            days_back = (on_date - actual_rate_date).days
            backward_fill_info = BackwardFillInfo(actual_rate_date=actual_rate_date, days_back=days_back)

        results.append(FXConversionResult(
            amount=conversion.amount,
            from_currency=from_cur,
            to_currency=to_cur,
            conversion_date=on_date.isoformat(),
            converted_amount=converted_amount,
            rate=rate,
            backward_fill_info=backward_fill_info
            ))

    # If all conversions failed, return 404
    if bulk_errors and not results:
        raise HTTPException(
            status_code=404,
            detail=f"All conversions failed: {'; '.join(bulk_errors)}"
            )

    return FXConvertResponse(
        results=results,
        success_count=len([r for r in results if r.converted_amount is not None]),
        errors=bulk_errors
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
            FxCurrencyPairSource.base,
            FxCurrencyPairSource.quote,
            FxCurrencyPairSource.priority
            )
        result = await session.execute(stmt)
        sources = result.scalars().all()

        sources_list = [
            FXPairSourceItem(
                base=s.base,
                quote=s.quote,
                provider_code=s.provider_code,
                priority=s.priority
                )
            for s in sources
            ]

        return FXPairSourcesResponse(sources=sources_list, count=len(sources_list))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pair sources: {str(e)}")


@router_providers.post("/pair-sources", response_model=FXCreatePairSourcesResponse, status_code=201)
async def create_pair_sources_bulk(
    sources: List[FXPairSourceItem],
    session: AsyncSession = Depends(get_session_generator)
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
        available_providers = {p['code'] for p in FXProviderRegistry.list_providers()}

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
                        FxCurrencyPairSource.priority == inv_priority
                        )
                    )

            inverse_stmt = select(
                FxCurrencyPairSource.base,
                FxCurrencyPairSource.quote,
                FxCurrencyPairSource.priority
                ).where(or_(*inverse_conditions))

            inverse_result = await session.execute(inverse_stmt)
            existing_inverses = {
                (row.base, row.quote, row.priority)
                for row in inverse_result.all()
                }
        else:
            existing_inverses = set()

        # Validate each source
        for source in sources:
            # Validate provider exists
            if source.provider_code.upper() not in available_providers:
                results.append(FXPairSourceResult(
                    success=False,
                    action="error",
                    base=source.base,
                    quote=source.quote,
                    provider_code=source.provider_code,
                    priority=source.priority,
                    message=f"Unknown provider: {source.provider_code}"
                    ))
                error_count += 1
                continue

            # Check for inverse pair conflict (same priority)
            inverse_key = (source.quote.upper(), source.base.upper(), source.priority)
            if inverse_key in existing_inverses:
                results.append(FXPairSourceResult(
                    success=False,
                    action="error",
                    base=source.base,
                    quote=source.quote,
                    provider_code=source.provider_code,
                    priority=source.priority,
                    message=f"Conflict: Inverse pair {source.quote}/{source.base} with priority={source.priority} already exists. Use different priority."
                    ))
                error_count += 1
                continue

            # Check if already exists
            stmt = select(FxCurrencyPairSource).where(
                FxCurrencyPairSource.base == source.base.upper(),
                FxCurrencyPairSource.quote == source.quote.upper(),
                FxCurrencyPairSource.priority == source.priority
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
                    priority=source.priority
                    )
                session.add(new_source)
                action = "created"

            results.append(FXPairSourceResult(
                success=True,
                action=action,
                base=source.base.upper(),
                quote=source.quote.upper(),
                provider_code=source.provider_code.upper(),
                priority=source.priority,
                message=None
                ))
            success_count += 1

        # Commit only if all validations passed
        if error_count > 0:
            await session.rollback()
            raise HTTPException(
                status_code=400,
                detail={
                    "message": f"Validation failed for {error_count} source(s). Transaction rolled back.",
                    "results": [r.model_dump() for r in results]
                    }
                )

        await session.commit()

        return FXCreatePairSourcesResponse(
            results=results,
            success_count=success_count,
            error_count=error_count
            )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create pair sources: {str(e)}")


@router_providers.delete("/pair-sources", response_model=FXDeletePairSourcesResponse)
async def delete_pair_sources_bulk(
    sources: List[FXDeletePairSourceItem],
    session: AsyncSession = Depends(get_session_generator)
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
                    FxCurrencyPairSource.priority == priority
                    )
            else:
                # Delete all priorities for this pair
                stmt = sql_delete(FxCurrencyPairSource).where(
                    FxCurrencyPairSource.base == base,
                    FxCurrencyPairSource.quote == quote
                    )

            result = await session.execute(stmt)
            deleted_count = result.rowcount

            if deleted_count == 0:
                # Warning: pair not found
                priority_str = f" with priority={priority}" if priority else ""
                results.append(FXDeletePairSourceResult(
                    success=True,  # Not an error, just a warning
                    base=base,
                    quote=quote,
                    priority=priority,
                    deleted_count=0,
                    message=f"Pair {base}/{quote}{priority_str} not found (nothing to delete)"
                    ))
            else:
                results.append(FXDeletePairSourceResult(
                    success=True,
                    base=base,
                    quote=quote,
                    priority=priority,
                    deleted_count=deleted_count,
                    message=None
                    ))
                total_deleted += deleted_count

        await session.commit()

        return FXDeletePairSourcesResponse(
            results=results,
            success_count=len([r for r in results if r.success]),
            total_deleted=total_deleted
            )

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete pair sources: {str(e)}")

# ============================================================================
# Include sub-route in main router
# ============================================================================
fx_router.include_router(router_providers)
fx_router.include_router(router_currencies)
