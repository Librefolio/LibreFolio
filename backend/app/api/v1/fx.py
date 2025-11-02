"""
FX (Foreign Exchange) API endpoints.
Handles currency conversion and FX rate synchronization.
"""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.session import get_session
from backend.app.services.fx import (
    FXServiceError,
    RateNotFoundError,
    convert,
    ensure_rates,
    get_available_currencies,
    )

router = APIRouter(prefix="/fx", tags=["FX"])


class SyncResponse(BaseModel):
    """Response model for FX rate sync operation."""
    synced: int = Field(..., description="Number of new rates inserted")
    date_range: tuple[str, str] = Field(..., description="Date range synced (ISO format)")
    currencies: list[str] = Field(..., description="Currencies synced")


class BackwardFillInfo(BaseModel):
    """Information about backward-fill applied during conversion."""
    applied: bool = Field(..., description="Whether backward-fill was applied")
    requested_date: str = Field(..., description="Date requested for conversion")
    actual_rate_date: str = Field(..., description="Date of the rate actually used")
    days_back: int = Field(..., description="Number of days back from requested date")


class ConvertResponse(BaseModel):
    """Response model for currency conversion."""
    amount: Decimal = Field(..., description="Original amount")
    from_currency: str = Field(..., description="Source currency code")
    to_currency: str = Field(..., description="Target currency code")
    converted_amount: Decimal = Field(..., description="Converted amount")
    rate: Decimal | None = Field(None, description="Exchange rate used (if not identity)")
    rate_date: str = Field(..., description="Date of the rate used (ISO format)")
    backward_fill_info: BackwardFillInfo | None = Field(None, description="Info about backward-fill if applied")


class UpsertRateRequest(BaseModel):
    """Request model for manual rate upsert."""
    rate_date: date = Field(..., description="Date of the rate (ISO format)", alias="date")
    base: str = Field(..., min_length=3, max_length=3, description="Base currency (ISO 4217)")
    quote: str = Field(..., min_length=3, max_length=3, description="Quote currency (ISO 4217)")
    rate: Decimal = Field(..., gt=0, description="Exchange rate (must be positive)")
    source: str = Field(default="MANUAL", description="Source of the rate")

    class Config:
        populate_by_name = True  # Allow using both 'date' and 'rate_date'


class UpsertRateResponse(BaseModel):
    """Response model for manual rate upsert."""
    success: bool = Field(..., description="Whether the operation was successful")
    action: str = Field(..., description="Action taken: 'inserted' or 'updated'")
    rate: Decimal = Field(..., description="The rate value stored")
    date: str = Field(..., description="Date of the rate (ISO format)")
    base: str = Field(..., description="Base currency")
    quote: str = Field(..., description="Quote currency")


class CurrenciesResponse(BaseModel):
    """Response model for available currencies list."""
    currencies: list[str] = Field(..., description="List of available currency codes")
    count: int = Field(..., description="Number of available currencies")


@router.get("/currencies", response_model=CurrenciesResponse)
async def list_currencies():
    """
    Get the list of available currencies from ECB.

    Returns:
        List of ISO 4217 currency codes
    """
    try:
        currencies = await get_available_currencies()
        return CurrenciesResponse(currencies=currencies, count=len(currencies))
    except FXServiceError as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch currencies: {str(e)}")


@router.post("/sync", response_model=SyncResponse)
async def sync_rates(
    start: date = Query(..., description="Start date (inclusive)"),
    end: date = Query(..., description="End date (inclusive)"),
    currencies: str = Query("USD,GBP,CHF,JPY", description="Comma-separated currency codes"),
    session: AsyncSession = Depends(get_session)
    ):
    """
    Synchronize FX rates from ECB for the specified date range and currencies.

    Args:
        start: Start date
        end: End date
        currencies: Comma-separated list of currency codes (e.g., "USD,GBP,CHF")
        session: Database session

    Returns:
        Sync statistics
    """
    # Validate date range
    if start > end:
        raise HTTPException(status_code=400, detail="Start date must be before or equal to end date")

    # Parse currencies
    currency_list = [c.strip().upper() for c in currencies.split(",") if c.strip()]
    if not currency_list:
        raise HTTPException(status_code=400, detail="At least one currency must be specified")

    try:
        synced_count = await ensure_rates(session, (start, end), currency_list)
        return SyncResponse(
            synced=synced_count,
            date_range=(start.isoformat(), end.isoformat()),
            currencies=currency_list
            )
    except FXServiceError as e:
        raise HTTPException(status_code=502, detail=f"Failed to sync rates: {str(e)}")


@router.post("/rate", response_model=UpsertRateResponse, status_code=200)
async def upsert_rate(
    request: UpsertRateRequest,
    session: AsyncSession = Depends(get_session)
    ):
    """
    Manually insert or update a single FX rate.

    This endpoint allows manual data entry or correction of FX rates.
    Uses UPSERT logic: if a rate for the same date/base/quote exists, it will be updated.

    Args:
        request: Rate data to insert/update
        session: Database session

    Returns:
        Operation result with action taken (inserted/updated)
    """
    from backend.app.db.models import FxRate
    from sqlalchemy.dialects.sqlite import insert
    from sqlalchemy import func, select

    base = request.base.upper()
    quote = request.quote.upper()

    # Validate currencies are different
    if base == quote:
        raise HTTPException(
            status_code=400,
            detail="Base and quote currencies must be different"
        )

    # Ensure alphabetical ordering (base < quote)
    if base > quote:
        base, quote = quote, base
        # Invert rate
        rate_value = Decimal("1") / request.rate
    else:
        rate_value = request.rate

    try:
        # Check if rate already exists
        stmt = select(FxRate).where(
            FxRate.date == request.rate_date,
            FxRate.base == base,
            FxRate.quote == quote
        )
        result = await session.execute(stmt)
        existing = result.scalars().first()

        action = "updated" if existing else "inserted"

        # UPSERT
        upsert_stmt = insert(FxRate).values(
            date=request.rate_date,
            base=base,
            quote=quote,
            rate=rate_value,
            source=request.source,
            fetched_at=func.current_timestamp()
        )

        upsert_stmt = upsert_stmt.on_conflict_do_update(
            index_elements=['date', 'base', 'quote'],
            set_={
                'rate': upsert_stmt.excluded.rate,
                'source': upsert_stmt.excluded.source,
                'fetched_at': func.current_timestamp()
            }
        )

        await session.execute(upsert_stmt)
        await session.commit()

        return UpsertRateResponse(
            success=True,
            action=action,
            rate=rate_value,
            date=request.rate_date.isoformat(),
            base=base,
            quote=quote
        )

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to upsert rate: {str(e)}")


@router.get("/convert", response_model=ConvertResponse)
async def convert_currency(
    amount: Decimal = Query(..., gt=0, description="Amount to convert (must be positive)"),
    from_currency: str = Query(..., alias="from", description="Source currency (ISO 4217)"),
    to_currency: str = Query(..., alias="to", description="Target currency (ISO 4217)"),
    on_date: date = Query(default_factory=date.today, alias="date", description="Conversion date"),
    session: AsyncSession = Depends(get_session)
    ):
    """
    Convert an amount from one currency to another.
    Uses backward-fill logic with unlimit time range if exact date rate is not available.

    Args:
        amount: Amount to convert (must be positive)
        from_currency: Source currency (ISO 4217 code)
        to_currency: Target currency (ISO 4217 code)
        on_date: Date for which to use the rate (defaults to today)
        session: Database session

    Returns:
        Conversion result with rate information
    """
    from_cur = from_currency.upper()
    to_cur = to_currency.upper()

    try:
        # Get conversion with rate info
        converted_amount, actual_rate_date, backward_fill_applied = await convert(
            session, amount, from_cur, to_cur, on_date, return_rate_info=True
        )

        # Calculate effective rate (for display purposes)
        rate = None
        if from_cur != to_cur:
            rate = converted_amount / amount

        # Build backward-fill info if applicable
        backward_fill_info = None
        if backward_fill_applied:
            days_back = (on_date - actual_rate_date).days
            backward_fill_info = BackwardFillInfo(
                applied=True,
                requested_date=on_date.isoformat(),
                actual_rate_date=actual_rate_date.isoformat(),
                days_back=days_back
            )

        return ConvertResponse(
            amount=amount,
            from_currency=from_cur,
            to_currency=to_cur,
            converted_amount=converted_amount,
            rate=rate,
            rate_date=actual_rate_date.isoformat(),
            backward_fill_info=backward_fill_info
            )
    except RateNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"FX rate not found: {str(e)}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
