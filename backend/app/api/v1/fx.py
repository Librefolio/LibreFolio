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


class UpsertRatesResponse(BaseModel):
    """Response model for bulk rate upsert."""
    results: list[RateUpsertResult] = Field(..., description="Upsert results in order")
    success_count: int = Field(..., description="Number of successful operations")
    errors: list[str] = Field(default_factory=list, description="Errors encountered (if any)")


class CurrenciesResponse(BaseModel):
    """Response model for available currencies list."""
    currencies: list[str] = Field(..., description="List of available currency codes")
    count: int = Field(..., description="Number of available currencies")


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
    provider: str = Query("ECB", description="Provider code (ECB, FED, BOE, SNB)"),
    base_currency: str | None = Query(None, description="Base currency (for multi-base providers)"),
    session: AsyncSession = Depends(get_session)
    ):
    """
    Synchronize FX rates from specified provider for the specified date range and currencies.

    Args:
        start: Start date
        end: End date
        currencies: Comma-separated list of currency codes (e.g., "USD,GBP,CHF")
        provider: Provider code (default: ECB)
        base_currency: Base currency to use (for multi-base providers). If not specified, uses provider's default.
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
