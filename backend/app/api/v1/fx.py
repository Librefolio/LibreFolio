"""
FX (Foreign Exchange) API endpoints.
Handles currency conversion and FX rate synchronization.
"""
from datetime import date
from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, delete as sql_delete

from backend.app.db.models import FxCurrencyPairSource
from backend.app.db.session import get_session
from backend.app.services.fx import (
    FXServiceError,
    FXProviderFactory,
    convert_bulk,
    ensure_rates_multi_source,
    upsert_rates_bulk,
    )

router = APIRouter(prefix="/fx", tags=["FX"])


class SyncResponse(BaseModel):
    """Response model for FX rate sync operation."""
    synced: int = Field(..., description="Number of new rates inserted")
    date_range: tuple[str, str] = Field(..., description="Date range synced (ISO format)")
    currencies: list[str] = Field(..., description="Currencies synced")


class BackwardFillInfo(BaseModel):
    """Information about backward-fill applied during conversion."""
    actual_rate_date: str = Field(..., description="Date of the rate actually used")
    days_back: int = Field(..., description="Number of days back from requested date")


class ConversionRequest(BaseModel):
    """Single conversion request with optional date range."""
    amount: Decimal = Field(..., gt=0, description="Amount to convert (must be positive)")
    from_currency: str = Field(..., alias="from", min_length=3, max_length=3, description="Source currency (ISO 4217)")
    to_currency: str = Field(..., alias="to", min_length=3, max_length=3, description="Target currency (ISO 4217)")
    start_date: date = Field(..., description="Start date (required). If end_date is not provided, only this date is used")
    end_date: date | None = Field(None, description="End date (optional). If provided, converts for all dates from start_date to end_date (inclusive)")

    class Config:
        populate_by_name = True


class ConvertRequest(BaseModel):
    """Request model for bulk currency conversion."""
    conversions: list[ConversionRequest] = Field(..., min_length=1, description="List of conversions to perform")


class ConversionResult(BaseModel):
    """Single conversion result."""
    amount: Decimal = Field(..., description="Original amount")
    from_currency: str = Field(..., description="Source currency code")
    to_currency: str = Field(..., description="Target currency code")
    conversion_date: str = Field(..., description="Date requested for conversion (ISO format)")
    converted_amount: Decimal = Field(..., description="Converted amount")
    rate: Decimal | None = Field(None, description="Exchange rate used (if not identity)")
    backward_fill_info: BackwardFillInfo | None = Field(
        None,
        description="Backward-fill info (only present if rate from a different date was used). "
                    "If null, rate_date = conversion_date"
    )


class ConvertResponse(BaseModel):
    """Response model for bulk currency conversion."""
    results: list[ConversionResult] = Field(..., description="Conversion results in order")
    errors: list[str] = Field(default_factory=list, description="Errors encountered (if any)")


class RateUpsertItem(BaseModel):
    """Single rate to upsert."""
    rate_date: date = Field(..., description="Date of the rate (ISO format)", alias="date")
    base: str = Field(..., min_length=3, max_length=3, description="Base currency (ISO 4217)")
    quote: str = Field(..., min_length=3, max_length=3, description="Quote currency (ISO 4217)")
    rate: Decimal = Field(..., gt=0, description="Exchange rate (must be positive)")
    source: str = Field(default="MANUAL", description="Source of the rate")

    class Config:
        populate_by_name = True


class UpsertRatesRequest(BaseModel):
    """Request model for bulk rate upsert."""
    rates: list[RateUpsertItem] = Field(..., min_length=1, description="List of rates to insert/update")


class RateUpsertResult(BaseModel):
    """Single rate upsert result."""
    success: bool = Field(..., description="Whether the operation was successful")
    action: str = Field(..., description="Action taken: 'inserted' or 'updated'")
    rate: Decimal = Field(..., description="The rate value stored")
    date: str = Field(..., description="Date of the rate (ISO format)")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")


# ============================================================================
# PROVIDER CONFIGURATION MODELS
# ============================================================================

class ProviderInfo(BaseModel):
    """Information about a single FX rate provider."""
    code: str = Field(..., description="Provider code (e.g., ECB, FED, BOE, SNB)")
    name: str = Field(..., description="Provider full name")
    base_currency: str = Field(..., description="Default base currency")
    base_currencies: list[str] = Field(..., description="All supported base currencies")
    description: str = Field(..., description="Provider description")


class ProvidersResponse(BaseModel):
    """Response model for GET /providers."""
    providers: list[ProviderInfo] = Field(..., description="List of available providers")
    count: int = Field(..., description="Number of providers")


class PairSourceItem(BaseModel):
    """Currency pair source configuration."""
    base: str = Field(..., min_length=3, max_length=3, description="Base currency (ISO 4217, alphabetically first)")
    quote: str = Field(..., min_length=3, max_length=3, description="Quote currency (ISO 4217, alphabetically second)")
    provider_code: str = Field(..., description="Provider to use for this pair (ECB, FED, BOE, SNB)")
    priority: int = Field(default=1, ge=1, description="Priority level (1=primary, 2+=fallback)")


class PairSourcesResponse(BaseModel):
    """Response model for GET /pair-sources."""
    sources: list[PairSourceItem] = Field(..., description="Configured currency pair sources")
    count: int = Field(..., description="Number of configured pairs")


class CreatePairSourcesRequest(BaseModel):
    """Request model for POST /pair-sources/bulk."""
    sources: list[PairSourceItem] = Field(..., min_length=1, description="Pair sources to create/update")


class PairSourceResult(BaseModel):
    """Result of a single pair source operation."""
    success: bool = Field(..., description="Whether the operation succeeded")
    action: str = Field(..., description="Action taken: 'created', 'updated', or 'error'")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    provider_code: str = Field(..., description="Provider code")
    priority: int = Field(..., description="Priority level")
    message: str | None = Field(None, description="Error message if action='error'")


class CreatePairSourcesResponse(BaseModel):
    """Response model for POST /pair-sources/bulk."""
    results: list[PairSourceResult] = Field(..., description="Results for each pair source")
    success_count: int = Field(..., description="Number of successful operations")
    error_count: int = Field(..., description="Number of failed operations")


class DeletePairSourcesRequest(BaseModel):
    """Request model for DELETE /pair-sources/bulk."""
    sources: list[dict] = Field(
        ...,
        min_length=1,
        description="Pair sources to delete: [{base, quote, priority?}, ...]"
    )


class DeletePairSourceResult(BaseModel):
    """Result of a single pair source deletion."""
    success: bool = Field(..., description="Whether the operation succeeded")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")
    priority: int | None = Field(None, description="Priority level (if specified)")
    deleted_count: int = Field(..., description="Number of records deleted")
    message: str | None = Field(None, description="Warning/error message if any")


class DeletePairSourcesResponse(BaseModel):
    """Response model for DELETE /pair-sources/bulk."""
    results: list[DeletePairSourceResult] = Field(..., description="Results for each deletion")
    total_deleted: int = Field(..., description="Total number of records deleted")


class UpsertRatesResponse(BaseModel):
    """Response model for bulk rate upsert."""
    results: list[RateUpsertResult] = Field(..., description="Upsert results in order")
    success_count: int = Field(..., description="Number of successful operations")
    errors: list[str] = Field(default_factory=list, description="Errors encountered (if any)")


class CurrenciesResponse(BaseModel):
    """Response model for available currencies list."""
    currencies: list[str] = Field(..., description="List of available currency codes")
    count: int = Field(..., description="Number of available currencies")


@router.get("/providers", response_model=ProvidersResponse)
async def list_providers():
    """
    Get the list of all available FX rate providers.

    Returns information about each provider including:
    - Provider code and name
    - Default base currency
    - All supported base currencies (for multi-base providers)
    - Description

    Returns:
        List of provider information
    """
    try:
        providers_data = FXProviderFactory.get_all_providers()
        providers = [ProviderInfo(**p) for p in providers_data]
        return ProvidersResponse(providers=providers, count=len(providers))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch providers: {str(e)}")


@router.get("/currencies", response_model=CurrenciesResponse)
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
        provider_instance = FXProviderFactory.get_provider(provider)
        currencies = await provider_instance.get_supported_currencies()
        return CurrenciesResponse(currencies=currencies, count=len(currencies))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FXServiceError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch currencies: {str(e)}")


@router.post("/sync", response_model=SyncResponse)
async def sync_rates(
    start: date = Query(..., description="Start date (inclusive)"),
    end: date = Query(..., description="End date (inclusive)"),
    currencies: str = Query("USD,GBP,CHF,JPY", description="Comma-separated currency codes"),
    provider: str | None = Query(None, description="Provider code (ECB, FED, BOE, SNB). If NULL, uses fx_currency_pair_sources configuration."),
    base_currency: str | None = Query(None, description="Base currency (for multi-base providers)"),
    session: AsyncSession = Depends(get_session)
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
            return SyncResponse(
                synced=result['total_changed'],
                date_range=(start.isoformat(), end.isoformat()),
                currencies=result['currencies_synced']
            )

        else:
            # AUTO-CONFIGURATION MODE: Use fx_currency_pair_sources
            # TODO: Implement in next step
            # For now, return error asking for explicit provider
            raise HTTPException(
                status_code=400,
                detail="Auto-configuration mode not yet implemented. Please specify 'provider' parameter explicitly."
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except FXServiceError as e:
        raise HTTPException(status_code=502, detail=f"Failed to sync rates: {str(e)}")


@router.post("/rate-set", response_model=UpsertRatesResponse, status_code=200)
async def upsert_rates_endpoint(
    request: UpsertRatesRequest,
    session: AsyncSession = Depends(get_session)
    ):
    """
    Manually insert or update one or more FX rates (bulk operation).

    This endpoint accepts a list of rates to insert/update. Even single rate
    should be sent as a list with one element.

    Uses UPSERT logic: if a rate for the same date/base/quote exists, it will be updated.
    Automatic alphabetical ordering and rate inversion is applied.

    Args:
        request: List of rates to insert/update
        session: Database session

    Returns:
        Operation results with action taken (inserted/updated) for each rate
    """
    results = []
    errors = []

    for idx, rate_item in enumerate(request.rates):
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

            results.append(RateUpsertResult(
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

    return UpsertRatesResponse(
        results=results,
        success_count=len(results),
        errors=errors
        )


@router.post("/convert", response_model=ConvertResponse)
async def convert_currency_bulk(
    request: ConvertRequest,
    session: AsyncSession = Depends(get_session)
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

    for conv_idx, conversion in enumerate(request.conversions):
        from_cur = conversion.from_currency.upper()
        to_cur = conversion.to_currency.upper()

        # Validate date range
        if conversion.end_date and conversion.start_date > conversion.end_date:
            raise HTTPException(
                status_code=400,
                detail=f"Conversion {conv_idx}: start_date must be before or equal to end_date"
                )

        # Expand date range into individual days
        if conversion.end_date:
            # Multi-day conversion: process each day in range
            current_date = conversion.start_date
            while current_date <= conversion.end_date:
                bulk_conversions.append((conversion.amount, from_cur, to_cur, current_date))
                conversion_metadata.append({
                    'original_idx': conv_idx,
                    'conversion': conversion,
                    'date': current_date
                    })
                current_date += timedelta(days=1)
        else:
            # Single-day conversion
            bulk_conversions.append((conversion.amount, from_cur, to_cur, conversion.start_date))
            conversion_metadata.append({
                'original_idx': conv_idx,
                'conversion': conversion,
                'date': conversion.start_date
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
            backward_fill_info = BackwardFillInfo(
                actual_rate_date=actual_rate_date.isoformat(),
                days_back=days_back
            )

        results.append(ConversionResult(
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

    return ConvertResponse(
        results=results,
        errors=bulk_errors
        )


# ============================================================================
# PROVIDER CONFIGURATION ENDPOINTS
# ============================================================================

@router.get("/pair-sources", response_model=PairSourcesResponse)
async def list_pair_sources(session: AsyncSession = Depends(get_session)):
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
            PairSourceItem(
                base=s.base,
                quote=s.quote,
                provider_code=s.provider_code,
                priority=s.priority
            )
            for s in sources
        ]

        return PairSourcesResponse(sources=sources_list, count=len(sources_list))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch pair sources: {str(e)}")


@router.post("/pair-sources/bulk", response_model=CreatePairSourcesResponse, status_code=201)
async def create_pair_sources_bulk(
    request: CreatePairSourcesRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Create or update multiple currency pair sources in a single atomic transaction.

    All operations succeed or all fail together. If any validation error occurs,
    the entire transaction is rolled back.

    Validations:
    - base < quote (alphabetical ordering)
    - Provider code must be registered in FXProviderFactory
    - Priority must be >= 1

    Args:
        request: List of pair sources to create/update
        session: Database session

    Returns:
        Results for each pair source operation
    """
    results = []
    success_count = 0
    error_count = 0

    try:
        # Validate all providers exist
        available_providers = {p['code'] for p in FXProviderFactory.get_all_providers()}

        for source in request.sources:
            # Validate base < quote
            if source.base >= source.quote:
                results.append(PairSourceResult(
                    success=False,
                    action="error",
                    base=source.base,
                    quote=source.quote,
                    provider_code=source.provider_code,
                    priority=source.priority,
                    message=f"Invalid pair: base ({source.base}) must be < quote ({source.quote}) alphabetically"
                ))
                error_count += 1
                continue

            # Validate provider exists
            if source.provider_code.upper() not in available_providers:
                results.append(PairSourceResult(
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

            results.append(PairSourceResult(
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
                    "results": [r.dict() for r in results]
                }
            )

        await session.commit()

        return CreatePairSourcesResponse(
            results=results,
            success_count=success_count,
            error_count=error_count
        )

    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create pair sources: {str(e)}")


@router.delete("/pair-sources/bulk", response_model=DeletePairSourcesResponse)
async def delete_pair_sources_bulk(
    request: DeletePairSourcesRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    Delete multiple currency pair sources.

    If priority is specified, deletes only that specific priority level.
    If priority is omitted, deletes ALL priorities for that pair.

    Warnings (not errors):
    - If a pair doesn't exist, logs a warning but continues

    Args:
        request: List of pair sources to delete: [{base, quote, priority?}, ...]
        session: Database session

    Returns:
        Results for each deletion operation
    """
    results = []
    total_deleted = 0

    try:
        for source_dict in request.sources:
            base = source_dict.get("base", "").upper()
            quote = source_dict.get("quote", "").upper()
            priority = source_dict.get("priority")

            if not base or not quote:
                results.append(DeletePairSourceResult(
                    success=False,
                    base=base or "MISSING",
                    quote=quote or "MISSING",
                    priority=priority,
                    deleted_count=0,
                    message="Missing base or quote currency"
                ))
                continue

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
                results.append(DeletePairSourceResult(
                    success=True,  # Not an error, just a warning
                    base=base,
                    quote=quote,
                    priority=priority,
                    deleted_count=0,
                    message=f"Pair {base}/{quote}{priority_str} not found (nothing to delete)"
                ))
            else:
                results.append(DeletePairSourceResult(
                    success=True,
                    base=base,
                    quote=quote,
                    priority=priority,
                    deleted_count=deleted_count,
                    message=None
                ))
                total_deleted += deleted_count

        await session.commit()

        return DeletePairSourcesResponse(
            results=results,
            total_deleted=total_deleted
        )

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete pair sources: {str(e)}")


