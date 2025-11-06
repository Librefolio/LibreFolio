"""
Asset pricing source service.

This module provides:
- AssetSourceProvider: Abstract base class for pricing providers
- AssetSourceManager: Manager for provider operations and price data
- Synthetic yield calculation for SCHEDULED_YIELD assets
- Backward-fill logic for missing price data
- Helper functions for decimal precision

Similar to fx.py but for price_history table (asset prices vs FX rates).

Key differences from FX:
- Table: price_history (not fx_rates)
- Fields: OHLC (open/high/low/close) + volume (not single rate)
- Lookup: (asset_id, date) not (base, quote, date)
- Synthetic yield: Calculated on-demand for SCHEDULED_YIELD assets

Design principles:
- Bulk-first: All operations have bulk version as PRIMARY
- Singles call bulk with 1 element
- DB optimization: Minimize queries (typically 1-3 max)
- Parallel provider calls where possible
"""
from abc import ABC, abstractmethod
from datetime import date as date_type, timedelta
from decimal import Decimal, ROUND_DOWN
from typing import TypedDict, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Asset,
    AssetProviderAssignment,
    ValuationModel,
)


# ============================================================================
# TYPE DEFINITIONS
# ============================================================================


class CurrentValue(TypedDict):
    """Current value of an asset."""
    value: Decimal
    currency: str
    as_of_date: date_type
    source: str


class PricePoint(TypedDict):
    """Single price data point (OHLC)."""
    date: date_type
    open: Optional[Decimal]
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Decimal  # Required
    volume: Optional[Decimal]
    currency: str


class HistoricalData(TypedDict):
    """Historical price data."""
    prices: list[PricePoint]
    currency: str
    source: str


class AssetSourceError(Exception):
    """Base exception for asset source errors."""
    def __init__(self, message: str, error_code: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================


class AssetSourceProvider(ABC):
    """
    Abstract base class for asset pricing providers.

    All providers must implement:
    - get_current_value(): Fetch current price
    - get_history_value(): Fetch historical prices
    - search(): Search for assets (if supported)
    - validate_params(): Validate provider_params

    Providers auto-register via @register_provider(AssetProviderRegistry) decorator.
    """

    @property
    @abstractmethod
    def provider_code(self) -> str:
        """Unique provider code (e.g., 'yfinance', 'cssscraper')."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass

    @abstractmethod
    async def get_current_value(
        self,
        provider_params: dict,
        session: AsyncSession,
    ) -> CurrentValue:
        """
        Fetch current price for asset.

        Args:
            provider_params: Provider-specific configuration (JSON)
            session: Database session

        Returns:
            CurrentValue with latest price

        Raises:
            AssetSourceError: On fetch failure
        """
        pass

    @abstractmethod
    async def get_history_value(
        self,
        provider_params: dict,
        start_date: date_type,
        end_date: date_type,
        session: AsyncSession,
    ) -> HistoricalData:
        """
        Fetch historical prices for date range.

        Args:
            provider_params: Provider-specific configuration (JSON)
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            session: Database session

        Returns:
            HistoricalData with price series

        Raises:
            AssetSourceError: On fetch failure
        """
        pass

    async def search(self, query: str) -> list[dict]:
        """
        Search for assets via provider (if supported).

        Args:
            query: Search query string

        Returns:
            List of {identifier, display_name, currency, type}

        Raises:
            AssetSourceError: If search not supported or fails
        """
        raise AssetSourceError(
            f"Search not supported by {self.provider_name}",
            "NOT_SUPPORTED",
            {"provider": self.provider_code}
        )

    def validate_params(self, params: dict) -> None:
        """
        Validate provider_params structure.

        Args:
            params: Provider parameters to validate

        Raises:
            AssetSourceError: If params invalid
        """
        pass  # Default: no validation


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_price_column_precision(column_name: str) -> tuple[int, int]:
    """
    Get (precision, scale) for price_history numeric columns.

    Args:
        column_name: Column name (open, high, low, close, adjusted_close)

    Returns:
        (precision, scale) tuple - e.g., (18, 6) means 18 total digits, 6 decimals
    """
    # All price columns use NUMERIC(18, 6)
    if column_name in ("open", "high", "low", "close", "adjusted_close"):
        return (18, 6)
    raise ValueError(f"Unknown price column: {column_name}")


def truncate_price_to_db_precision(value: Decimal, column_name: str = "close") -> Decimal:
    """
    Truncate price to match database column precision.

    Prevents false update detection when re-syncing identical values.
    Database truncates on write, so we truncate before comparing.

    Args:
        value: Price value to truncate
        column_name: Target column (default: close)

    Returns:
        Truncated Decimal matching DB precision

    Example:
        >>> truncate_price_to_db_precision(Decimal("175.123456789"), "close")
        Decimal("175.123456")  # Truncated to 6 decimals
    """
    precision, scale = get_price_column_precision(column_name)
    quantizer = Decimal(10) ** -scale
    return value.quantize(quantizer, rounding=ROUND_DOWN)


def calculate_days_between_act365(start: date_type, end: date_type) -> Decimal:
    """
    Calculate day fraction using ACT/365 convention.

    Args:
        start: Start date
        end: End date

    Returns:
        Decimal fraction (actual_days / 365)

    Example:
        >>> calculate_days_between_act365(date(2025, 1, 1), date(2025, 1, 31))
        Decimal("0.082191780821917808")  # 30/365
    """
    actual_days = (end - start).days
    return Decimal(actual_days) / Decimal(365)


# ============================================================================
# SYNTHETIC YIELD CALCULATION (Internal Module)
# ============================================================================


def find_active_rate(
    schedule: list[dict],
    target_date: date_type,
    maturity_date: date_type,
    late_interest: Optional[dict],
) -> Decimal:
    """
    Find applicable interest rate for target date.

    Logic:
    1. Search schedule for rate covering target_date
    2. If past maturity + grace period: use late_interest.rate
    3. If no match: return 0%

    Args:
        schedule: List of {start_date, end_date, rate}
        target_date: Date to find rate for
        maturity_date: Asset maturity date
        late_interest: {rate, grace_period_days} or None

    Returns:
        Applicable annual interest rate (as Decimal, e.g., 0.05 for 5%)
    """
    # Check if within schedule
    for period in schedule:
        start = period["start_date"]
        end = period["end_date"]
        if start <= target_date <= end:
            return Decimal(str(period["rate"]))

    # Check if past maturity with late interest
    if late_interest and target_date > maturity_date:
        grace_days = late_interest.get("grace_period_days", 0)
        grace_end = maturity_date + timedelta(days=grace_days)

        if target_date > grace_end:
            return Decimal(str(late_interest["rate"]))

    # No applicable rate
    return Decimal("0")


def calculate_accrued_interest(
    face_value: Decimal,
    start_date: date_type,
    end_date: date_type,
    schedule: list[dict],
    maturity_date: date_type,
    late_interest: Optional[dict],
) -> Decimal:
    """
    Calculate accrued SIMPLE interest from start to end.

    Formula (SIMPLE interest):
        interest = principal * sum(rate_i * time_fraction_i)

    Where:
        - rate_i: Annual interest rate for period i
        - time_fraction_i: Days in period i / 365 (ACT/365)

    Args:
        face_value: Principal amount
        start_date: Calculation start date
        end_date: Calculation end date (inclusive)
        schedule: Interest rate schedule
        maturity_date: Asset maturity date
        late_interest: Late interest configuration

    Returns:
        Total accrued interest (Decimal)
    """
    total_interest = Decimal("0")
    current_date = start_date

    while current_date <= end_date:
        # Find rate for this day
        rate = find_active_rate(schedule, current_date, maturity_date, late_interest)

        # Calculate daily interest: principal * (rate / 365)
        daily_interest = face_value * rate / Decimal(365)
        total_interest += daily_interest

        current_date += timedelta(days=1)

    return total_interest


async def calculate_synthetic_value(
    asset: Asset,
    target_date: date_type,
    session: AsyncSession,
) -> PricePoint:
    """
    Calculate synthetic valuation for SCHEDULED_YIELD asset.

    Formula:
        value = face_value + accrued_interest - dividends_paid

    Args:
        asset: Asset with valuation_model = SCHEDULED_YIELD
        target_date: Date to calculate value for
        session: Database session

    Returns:
        PricePoint with calculated value

    Raises:
        ValueError: If asset not SCHEDULED_YIELD or missing required fields

    TODO (Step 03):
        - Check if loan repaid via transactions
        - Subtract dividend payments from value
    """
    if asset.valuation_model != ValuationModel.SCHEDULED_YIELD:
        raise ValueError(f"Asset {asset.id} is not SCHEDULED_YIELD type")

    if not asset.face_value or not asset.interest_schedule or not asset.maturity_date:
        raise ValueError(f"Asset {asset.id} missing required fields for synthetic yield")

    # Parse schedules (stored as JSON strings in DB)
    import json
    interest_schedule = json.loads(asset.interest_schedule)
    late_interest = json.loads(asset.late_interest) if asset.late_interest else None

    # TODO: Parse dividend_schedule when implemented
    # dividend_schedule = json.loads(asset.dividend_schedule) if asset.dividend_schedule else []

    # Calculate accrued interest from asset creation to target date
    # Note: Assuming asset.created_at as start date (TODO: Use first transaction date in Step 03)
    start_date = asset.created_at.date()

    accrued_interest = calculate_accrued_interest(
        face_value=asset.face_value,
        start_date=start_date,
        end_date=target_date,
        schedule=interest_schedule,
        maturity_date=asset.maturity_date,
        late_interest=late_interest,
    )

    # Calculate value (TODO: Subtract dividends in Step 03)
    synthetic_value = asset.face_value + accrued_interest

    return PricePoint(
        date=target_date,
        open=None,
        high=None,
        low=None,
        close=truncate_price_to_db_precision(synthetic_value),
        volume=None,
        currency=asset.currency,
    )


# ============================================================================
# ASSET SOURCE MANAGER
# ============================================================================


class AssetSourceManager:
    """
    Manager for asset pricing operations.

    Responsibilities:
    - Provider assignment CRUD
    - Price data refresh (via providers)
    - Manual price CRUD
    - Price queries with backward-fill
    - Synthetic yield integration

    All methods follow bulk-first design:
    - Bulk operations are PRIMARY
    - Single operations call bulk with 1 element
    - DB queries optimized (typically 1-3 max)
    """

    # ========================================================================
    # PROVIDER ASSIGNMENT METHODS
    # ========================================================================

    @staticmethod
    async def bulk_assign_providers(
        assignments: list[dict],
        session: AsyncSession,
    ) -> list[dict]:
        """
        Bulk assign/update providers to assets (PRIMARY bulk method).

        Args:
            assignments: List of {asset_id, provider_code, provider_params}
            session: Database session

        Returns:
            List of results: [{asset_id, success, message}, ...]

        Optimized: 1 delete + 1 insert query
        """
        if not assignments:
            return []

        results = []
        asset_ids = [a["asset_id"] for a in assignments]

        # Delete existing assignments (upsert pattern)
        await session.execute(
            delete(AssetProviderAssignment).where(
                AssetProviderAssignment.asset_id.in_(asset_ids)
            )
        )

        # Bulk insert new assignments
        new_assignments = [
            AssetProviderAssignment(
                asset_id=a["asset_id"],
                provider_code=a["provider_code"],
                provider_params=a.get("provider_params"),
                last_fetch_at=None,  # Never fetched yet
            )
            for a in assignments
        ]

        session.add_all(new_assignments)
        await session.commit()

        # Build results
        for assignment in assignments:
            results.append({
                "asset_id": assignment["asset_id"],
                "success": True,
                "message": f"Provider {assignment['provider_code']} assigned"
            })

        return results

    @staticmethod
    async def assign_provider(
        asset_id: int,
        provider_code: str,
        provider_params: Optional[str],
        session: AsyncSession,
    ) -> dict:
        """
        Assign provider to single asset (calls bulk with 1 element).

        Args:
            asset_id: Asset ID
            provider_code: Provider code
            provider_params: Provider parameters (JSON string)
            session: Database session

        Returns:
            Single result dict
        """
        results = await AssetSourceManager.bulk_assign_providers(
            [{"asset_id": asset_id, "provider_code": provider_code, "provider_params": provider_params}],
            session
        )
        return results[0]

    @staticmethod
    async def bulk_remove_providers(
        asset_ids: list[int],
        session: AsyncSession,
    ) -> list[dict]:
        """
        Bulk remove provider assignments (PRIMARY bulk method).

        Args:
            asset_ids: List of asset IDs
            session: Database session

        Returns:
            List of results: [{asset_id, success, message}, ...]

        Optimized: 1 DELETE query with WHERE IN
        """
        if not asset_ids:
            return []

        await session.execute(
            delete(AssetProviderAssignment).where(
                AssetProviderAssignment.asset_id.in_(asset_ids)
            )
        )
        await session.commit()

        return [
            {"asset_id": aid, "success": True, "message": "Provider removed"}
            for aid in asset_ids
        ]

    @staticmethod
    async def remove_provider(
        asset_id: int,
        session: AsyncSession,
    ) -> dict:
        """
        Remove provider from single asset (calls bulk with 1 element).

        Args:
            asset_id: Asset ID
            session: Database session

        Returns:
            Single result dict
        """
        results = await AssetSourceManager.bulk_remove_providers([asset_id], session)
        return results[0]

    @staticmethod
    async def get_asset_provider(
        asset_id: int,
        session: AsyncSession,
    ) -> Optional[AssetProviderAssignment]:
        """
        Fetch provider assignment for asset.

        Args:
            asset_id: Asset ID
            session: Database session

        Returns:
            AssetProviderAssignment or None if not assigned
        """
        result = await session.execute(
            select(AssetProviderAssignment).where(
                AssetProviderAssignment.asset_id == asset_id
            )
        )
        return result.scalar_one_or_none()

    # TODO: Implement remaining methods in next iteration
    # - bulk_refresh_prices()
    # - refresh_price()
    # - bulk_upsert_prices()
    # - upsert_prices()
    # - bulk_delete_prices()
    # - delete_prices()
    # - get_prices() with backward-fill + synthetic yield

