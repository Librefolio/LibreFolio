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


class ConvertResponse(BaseModel):
    """Response model for currency conversion."""
    amount: Decimal = Field(..., description="Original amount")
    from_currency: str = Field(..., description="Source currency code")
    to_currency: str = Field(..., description="Target currency code")
    converted_amount: Decimal = Field(..., description="Converted amount")
    rate: Decimal | None = Field(None, description="Exchange rate used (if not identity)")
    rate_date: str = Field(..., description="Date of the rate used (ISO format)")


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


@router.get("/convert", response_model=ConvertResponse)
async def convert_currency(
    amount: Decimal = Query(..., description="Amount to convert"),
    from_currency: str = Query(..., alias="from", description="Source currency (ISO 4217)"),
    to_currency: str = Query(..., alias="to", description="Target currency (ISO 4217)"),
    on_date: date = Query(default_factory=date.today, description="Conversion date"),
    session: AsyncSession = Depends(get_session)
    ):
    """
    Convert an amount from one currency to another.
    Uses forward-fill logic if exact date rate is not available.

    Args:
        amount: Amount to convert
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
        converted_amount = await convert(session, amount, from_cur, to_cur, on_date)

        # Calculate effective rate (for display purposes)
        rate = None
        if from_cur != to_cur:
            rate = converted_amount / amount

        return ConvertResponse(
            amount=amount,
            from_currency=from_cur,
            to_currency=to_cur,
            converted_amount=converted_amount,
            rate=rate,
            rate_date=on_date.isoformat()
            )
    except RateNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail=f"FX rate not found: {str(e)}. Try syncing rates first using POST /api/v1/fx/sync"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")
