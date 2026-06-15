"""
Common schemas shared across subsystems.

This module contains Pydantic models used by multiple services
(e.g., both FX and Asset pricing systems).

**Domain Coverage**:
- BackwardFillInfo: Shared by FA and FX for gap-filling logic
- DateRangeModel: Reusable date range representation
- BaseListResponse: Standardized base class for list/collection responses
- BaseBulkResponse: Standardized base class for bulk operation responses

**Design Notes**:
- No backward compatibility maintained during refactoring
- Models designed for maximum reusability across FA/FX systems
- Future: Consider adding validation (end >= start) via Pydantic validator
"""

# Postpones evaluation of type hints to improve imports and performance. Also avoid circular import issues.
from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Any, List, Optional

import pycountry
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic.functional_serializers import PlainSerializer

from backend.app.utils.datetime_utils import parse_ISO_date

# =============================================================================
# SAFE DECIMAL — no scientific notation in JSON output
# =============================================================================


def _decimal_fixed_point(v: Decimal) -> str:
    """Serialize Decimal to fixed-point string (never scientific notation).

    Python's ``str(Decimal)`` may emit ``"1.29E+5"`` or ``"0E+6"`` which
    frontend Zod regex validators reject.  ``format(v, 'f')`` always
    produces plain decimal notation: ``"129000"`` / ``"0"``.
    """
    if not isinstance(v, Decimal):
        return str(v)
    return format(v, "f")


SafeDecimal = Annotated[
    Decimal,
    PlainSerializer(_decimal_fixed_point, return_type=str, when_used="json"),
]
"""Use instead of ``Decimal`` in **response** schemas to guarantee
no scientific notation reaches the frontend.

Import::

    from backend.app.schemas.common import SafeDecimal

Usage::

    class MyResponse(BaseModel):
        amount: SafeDecimal
        quantity: Optional[SafeDecimal] = None
"""

# =============================================================================
# CRYPTOCURRENCY SUPPORT
# =============================================================================

# Cryptocurrencies not in pycountry ISO 4217 database
CRYPTO_CURRENCIES = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "USDT": "Tether",
    "USDC": "USD Coin",
    "BNB": "Binance Coin",
    "XRP": "Ripple",
    "ADA": "Cardano",
    "SOL": "Solana",
    "DOT": "Polkadot",
    "DOGE": "Dogecoin",
    "MATIC": "Polygon",
    "AVAX": "Avalanche",
    "LINK": "Chainlink",
    "UNI": "Uniswap",
    "ATOM": "Cosmos",
    "LTC": "Litecoin",
    "XLM": "Stellar",
    "ALGO": "Algorand",
    "VET": "VeChain",
    "FIL": "Filecoin",
}


# =============================================================================
# CACHED CURRENCY VALIDATION
# =============================================================================


@lru_cache(maxsize=256)
def _validate_currency_code_cached(code: str) -> str:
    """
    Cached currency code validation.

    This function is cached to avoid repeated pycountry lookups.
    The cache stores up to 256 validated currency codes.

    Args:
        code: Normalized (uppercase, stripped) currency code

    Returns:
        The validated currency code

    Raises:
        ValueError: If currency code is invalid
    """
    # Check ISO 4217 via pycountry
    try:
        pycountry.currencies.lookup(code)
        return code
    except LookupError:
        pass

    # Check crypto currencies
    if code in CRYPTO_CURRENCIES:
        return code

    # Invalid currency
    raise ValueError(f"Invalid currency code: '{code}'. " f"Must be ISO 4217 currency or supported crypto.")


# =============================================================================
# CURRENCY CLASS
# =============================================================================


class Currency(BaseModel):
    """
    Currency amount with validation and arithmetic operations.

    Validates currency codes against ISO 4217 (via pycountry) + crypto dict.
    Supports addition/subtraction only between same currencies.
    Amount can be negative.

    Attributes:
        code: ISO 4217 currency code (USD, EUR) or crypto symbol (BTC, ETH)
        amount: Decimal amount (can be negative)

    Examples:
        >>> usd = Currency(code="USD", amount=Decimal("100.50"))
        >>> fee = Currency(code="USD", amount=Decimal("2.50"))
        >>> total = usd + fee  # Currency(code="USD", amount=Decimal("103.00"))

        >>> eur = Currency(code="EUR", amount=Decimal("50"))
        >>> usd + eur  # ValueError: Cannot add USD and EUR

        >>> btc = Currency(code="BTC", amount=Decimal("0.5"))  # Valid crypto

        >>> negative = -usd  # Currency(code="USD", amount=Decimal("-100.50"))

    Raises:
        ValueError: If currency code is not valid ISO 4217 or supported crypto
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="ISO 4217 currency code or crypto symbol")
    amount: SafeDecimal = Field(..., description="Amount (can be negative)")

    @staticmethod
    def validate_code(v: Any) -> str:
        """
        Validate and normalize a currency code (static method).

        Use this method in Pydantic @field_validator for currency code fields
        that don't need a full Currency object.

        This method uses an LRU cache internally to avoid repeated pycountry lookups.

        Args:
            v: Currency code to validate

        Returns:
            Uppercase validated currency code

        Raises:
            ValueError: If currency code is invalid

        Example:
            @field_validator('currency')
            @classmethod
            def validate_currency(cls, v):
                return Currency.validate_code(v)
        """
        if not isinstance(v, str):
            raise ValueError(f"Currency code must be a string, got {type(v)}")

        # Normalize: uppercase and strip whitespace
        code = v.upper().strip()

        if not code:
            raise ValueError("Currency code cannot be empty")

        # Use cached validation
        return _validate_currency_code_cached(code)

    @field_validator("code", mode="before")
    @classmethod
    def validate_currency_code(cls, v: Any) -> str:
        """Validate and normalize currency code."""
        return cls.validate_code(v)

    @field_validator("amount", mode="before")
    @classmethod
    def validate_amount(cls, v: Any) -> Decimal:
        """Convert amount to Decimal if needed."""
        if isinstance(v, Decimal):
            return v
        if isinstance(v, (int, float, str)):
            try:
                return Decimal(str(v))
            except Exception:
                raise ValueError(f"Cannot convert '{v}' to Decimal") from None
        raise ValueError(f"Amount must be numeric, got {type(v)}")

    def __add__(self, other: Currency) -> Currency:
        """Add two Currency objects (same currency only)."""
        if not isinstance(other, Currency):
            raise TypeError(f"Cannot add Currency and {type(other).__name__}")
        if self.code != other.code:
            raise ValueError(f"Cannot add {self.code} and {other.code}")
        return Currency(code=self.code, amount=self.amount + other.amount)

    def __sub__(self, other: Currency) -> Currency:
        """Subtract two Currency objects (same currency only)."""
        if not isinstance(other, Currency):
            raise TypeError(f"Cannot subtract {type(other).__name__} from Currency")
        if self.code != other.code:
            raise ValueError(f"Cannot subtract {other.code} from {self.code}")
        return Currency(code=self.code, amount=self.amount - other.amount)

    def __neg__(self) -> Currency:
        """Negate currency amount."""
        return Currency(code=self.code, amount=-self.amount)

    def __abs__(self) -> Currency:
        """Absolute value of currency amount."""
        return Currency(code=self.code, amount=abs(self.amount))

    def __eq__(self, other: object) -> bool:
        """Check equality (same code and amount)."""
        if not isinstance(other, Currency):
            return False
        return self.code == other.code and self.amount == other.amount

    def __ne__(self, other: object) -> bool:
        """Check inequality."""
        return not self.__eq__(other)

    def __lt__(self, other: Currency) -> bool:
        """Less than comparison (same currency only)."""
        if not isinstance(other, Currency):
            raise TypeError(f"Cannot compare Currency and {type(other).__name__}")
        if self.code != other.code:
            raise ValueError(f"Cannot compare {self.code} and {other.code}")
        return self.amount < other.amount

    def __le__(self, other: Currency) -> bool:
        """Less than or equal comparison (same currency only)."""
        return self == other or self < other

    def __gt__(self, other: Currency) -> bool:
        """Greater than comparison (same currency only)."""
        if not isinstance(other, Currency):
            raise TypeError(f"Cannot compare Currency and {type(other).__name__}")
        if self.code != other.code:
            raise ValueError(f"Cannot compare {self.code} and {other.code}")
        return self.amount > other.amount

    def __ge__(self, other: Currency) -> bool:
        """Greater than or equal comparison (same currency only)."""
        return self == other or self > other

    def __str__(self) -> str:
        """String representation: '100.50 USD'."""
        return f"{self.amount} {self.code}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Currency(code='{self.code}', amount=Decimal('{self.amount}'))"

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash((self.code, self.amount))

    def to_dict(self) -> dict:
        """Serialize to dict for JSON responses."""
        return {"currency": self.code, "amount": format(self.amount, "f")}  # Decimal → fixed-point string

    @classmethod
    def zero(cls, code: str) -> Currency:
        """Create a zero-valued Currency."""
        return cls(code=code, amount=Decimal("0"))

    def is_zero(self) -> bool:
        """Check if amount is zero."""
        return self.amount == Decimal("0")

    def is_positive(self) -> bool:
        """Check if amount is positive."""
        return self.amount > Decimal("0")

    def is_negative(self) -> bool:
        """Check if amount is negative."""
        return self.amount < Decimal("0")


class BackwardFillInfo(BaseModel):
    """
    Backward-fill information when requested date has no data.

    Used by both FX (fx.py) and Asset pricing (asset_source.py) systems
    to indicate when historical data was used instead of exact date match.

    Attributes:
        actual_rate_date: stored as a `date` (accepts ISO string, `date` or `datetime` on input)
        days_back: Number of days back from requested date

    Examples:
        # Exact match - backward_fill_info is None
        {
            "date": "2025-11-05",
            "value": 1.234,
            "backward_fill_info": None
        }

        # Backfilled - used data from 3 days earlier
        {
            "date": "2025-11-05",
            "value": 1.234,
            "backward_fill_info": {
                "actual_rate_date": "2025-11-02",
                "days_back": 3
            }
        }
    """

    model_config = ConfigDict()

    actual_rate_date: date_type = Field(..., description="ISO date of actual data used (YYYY-MM-DD)")
    days_back: int = Field(..., description="Number of days back from requested date")

    @field_validator("actual_rate_date", mode="before")
    @classmethod
    def _parse_actual_rate_date(cls, v):
        return parse_ISO_date(v)

    def actual_rate_date_str(self) -> str:
        """Return the actual_rate_date as ISO string (YYYY-MM-DD)."""
        return self.actual_rate_date.isoformat()


class FxBackwardFillInfo(BaseModel):
    """
    FX-specific backward-fill staleness, decoupled from price backward-fill.

    Used on **any** entity whose value was converted to a target currency
    via an FX rate lookup, when that lookup may have fallen back to an
    older date than the requested one. Semantics are identical to the
    price staleness in ``BackwardFillInfo``, but apply only to FX.

    Decoupled from price-staleness because:
    - Prices have both dimensions (price backward-fill + FX backward-fill)
      → use the composed ``AssetBackwardFillInfo``.
    - Events (dividends, interest, splits, etc.) exist on discrete real
      dates and are NEVER backward-filled themselves — only their value's
      FX conversion can be stale → use ``FxBackwardFillInfo`` directly.
    - Future aggregates (dashboard, portfolio breakdown) may need FX
      staleness without any price-staleness concept.

    Both fields are typically ``None`` when no currency conversion was
    performed (identity / passthrough).

    Attributes:
        fx_rate_date: Actual date of the FX rate used for the conversion.
        fx_days_back: Days between the requested date and ``fx_rate_date``
            (0 = same-day match, >0 = backward-fill applied).
    """

    model_config = ConfigDict()

    fx_rate_date: Optional[date_type] = Field(None, description="Actual date of the FX rate used for conversion")
    fx_days_back: Optional[int] = Field(None, description="Days back for the FX rate (0 = same-day, None = no conversion)")

    @field_validator("fx_rate_date", mode="before")
    @classmethod
    def _parse_fx_rate_date(cls, v):
        return parse_ISO_date(v) if v is not None else v


class DateRangeModel(BaseModel):
    """
    Reusable date range model for FA and FX operations.

    Used across multiple operations: price deletion, FX rate queries, etc.
    Represents an inclusive date range [start, end].

    Attributes:
        start: Start date (inclusive, required)
        end: End date (inclusive, optional - defaults to start for single day)

    Design Notes:
        - If end is None, represents a single day (start only)
        - If end is provided, represents a range [start, end] inclusive
        - Validator ensures end >= start when provided

    Examples:
        # Single day
        {"start": "2025-11-05", "end": null}  # Just 2025-11-05

        # Range
        {"start": "2025-11-01", "end": "2025-11-30"}  # Entire November
    """

    model_config = ConfigDict(extra="forbid")

    start: date_type = Field(..., description="Start date (inclusive)")
    end: Optional[date_type] = Field(None, description="End date (inclusive, optional = single day)")

    @model_validator(mode="after")
    def validate_end_after_start(self) -> DateRangeModel:
        """Ensure end >= start when end is provided."""
        if self.end is not None and self.end < self.start:
            raise ValueError(f"end date ({self.end}) must be >= start date ({self.end})")
        return self


class OpenDateRangeModel(BaseModel):
    """
    Open-ended date range — both start and end are optional.

    Unlike DateRangeModel (which requires start), this model allows
    either or both bounds to be unset:
    - start=None → from the beginning of time
    - end=None → up to today / unbounded future
    - Both None → entire history

    The validator still enforces end >= start when both are provided.

    Use cases: /portfolio/wac date_range, flexible query filters.
    """

    model_config = ConfigDict(extra="forbid")

    start: Optional[date_type] = Field(None, description="Start date (inclusive, None = from beginning)")
    end: Optional[date_type] = Field(None, description="End date (inclusive, None = unbounded / today)")

    @model_validator(mode="after")
    def validate_end_after_start(self) -> OpenDateRangeModel:
        """Ensure end >= start when both are provided."""
        if self.start is not None and self.end is not None and self.end < self.start:
            raise ValueError(f"end date ({self.end}) must be >= start date ({self.start})")
        return self


class BaseDeleteResult(BaseModel):
    """
    Standardized base class for all delete/removal operation results.

    Provides consistent structure across FA and FX systems for deletion operations.
    All delete/removal result classes should inherit from this base.

    Standard fields:
    - success: bool - Whether the deletion operation succeeded
    - deleted_count: int - Number of items actually deleted (always >= 0)
    - message: Optional[str] - Info/warning/error message

    Identifier fields:
    - Subclasses add their own identifier fields (asset_id, base/quote, etc.)

    Design Notes:
    - Simple inheritance model (no Generic complexity)
    - Consistent naming: always use 'deleted_count' (not 'deleted')
    - message is optional (None if operation successful with no warnings)
    - Subclasses can add operation-specific fields (existing_count, etc.)

    Examples:
        ```python
        class FAAssetDeleteResult(BaseDeleteResult):
            asset_id: int
            # Inherits: success, deleted_count, message

        class FXDeleteResult(BaseDeleteResult):
            base: str
            quote: str
            date_range: DateRangeModel
            existing_count: int  # Operation-specific field
            # Inherits: success, deleted_count, message
        ```

    Benefits:
    - Consistent API across all deletion operations
    - Guaranteed validation (deleted_count >= 0)
    - Single source of truth for deletion result structure
    - Easy to extend with operation-specific fields
    """

    model_config = ConfigDict(extra="forbid")

    success: bool = Field(..., description="Whether the deletion succeeded")
    deleted_count: int = Field(..., ge=0, description="Number of items deleted")
    message: Optional[str] = Field(None, description="Info/warning/error message")


# CustomType specified by subclass


class OldNew[CType](BaseModel):
    """
    Represents a field change with old and new values.

    Used to communicate changes in metadata refresh operations.
    Generic type CType allows flexible typing (str, str|None, etc.)

    Examples:
        >>> change = OldNew(info="sector", old="Technology", new="Industrials")
        >>> change = OldNew(info="sector", old=None, new="Technology")  # First time set
        >>>
        >>> # With optional types
        >>> change: OldNew[str | None] = OldNew(info="sector", old="Tech", new=None)  # Cleared
    """

    model_config = ConfigDict(extra="forbid")
    info: Optional[str] = Field(None, description="Info message/Field name")
    old: CType = Field(..., description="Old value")
    new: CType = Field(..., description="New value")


# Generic type for result items in bulk responses, must be child of BaseModel


class BaseListResponse[TResult: BaseModel](BaseModel):
    """
    Standardized base class for all list/collection responses.

    Provides consistent structure for any endpoint that returns a list of items.
    Subclasses specify the concrete item type via Generic.

    Standard fields:
    - items: List of result items

    Design Notes:
    - Generic class parameterized by TResult (the item type)
    - count was removed: len(items) in Python / .length in JS is sufficient
    - Will be reintroduced if server-side pagination is needed (total != len(items))

    Examples:
        ```python
        class UploadListResponse(BaseListResponse[UploadFileInfo]):
            pass  # Inherits: items

        class CountryListResponse(BaseListResponse[CountryListItem]):
            language: str  # Additional fields allowed
        ```
    """

    model_config = ConfigDict(extra="forbid")

    items: List[TResult] = Field(default_factory=list, description="List of items")


class BaseBulkResponse[TResult: BaseModel](BaseModel):
    """
    Standardized base class for all bulk operation responses.

    Provides consistent structure across FA and FX systems for bulk operations.
    Subclasses should specify the concrete result type.

    Standard fields:
    - results: List of per-item operation results
    - success_count: Number of successful operations
    - failed_count: Number of failed operations (derived from len(results) - success_count)
    - errors: Optional list of error messages (operation-level errors, not per-item)

    Design Notes:
    - Generic class parameterized by TResult (the result item type)
    - Subclasses inherit this structure and specify their result type
    - failed_count is NOT stored, computed from results length
    - errors field is for operation-level errors (e.g., "timeout", "provider unavailable")
    - Per-item errors should be in the result items themselves

    Examples:
        ```python
        class FABulkAssetCreateResponse(BaseBulkResponse[FAAssetCreateResult]):
            # Inherits: results, success_count, errors
            # failed_count is computed property
            pass

        class FXBulkUpsertResponse(BaseBulkResponse[FXUpsertResult]):
            # Can add specific fields if needed
            inserted_count: int
            updated_count: int
        ```
    """

    model_config = ConfigDict(extra="forbid")

    results: List[TResult] = Field(..., description="Per-item operation results")
    success_count: int = Field(..., ge=0, description="Number of successful operations")
    errors: List[str] = Field(default_factory=list, description="Operation-level errors (not per-item)")

    @property
    def failed_count(self) -> int:
        """Computed property: number of failed operations."""
        return len(self.results) - self.success_count

    @property
    def total_count(self) -> int:
        """Computed property: total number of items processed."""
        return len(self.results)


class BaseBulkDeleteResponse[TResult: BaseModel](BaseBulkResponse[TResult]):
    """
    Specialized base class for bulk delete/removal operations.

    Combines BaseBulkResponse structure with delete-specific aggregate field.
    Inherits list of results and success tracking from BaseBulkResponse,
    adds total deletion count across all items.

    Standard fields (from BaseBulkResponse):
    - results: List[TResult] - Per-item deletion results
    - success_count: int - Number of successful deletions
    - errors: List[str] - Operation-level errors

    Delete-specific field:
    - total_deleted: int - Total number of records deleted across all items

    Computed properties (from BaseBulkResponse):
    - failed_count: int - Number of failed deletions
    - total_count: int - Total number of items processed

    Design Notes:
    - Extends BaseBulkResponse with delete-specific aggregate
    - total_deleted is the sum of all deleted_count from individual results
    - Generic class parameterized by TResult (the result item type)
    - Use when bulk operation deletes multiple records per item

    Examples:
        ```python
        # For price deletion (deletes multiple price records per asset)
        class FABulkDeleteResponse(BaseBulkDeleteResponse[FAPriceDeleteResult]):
            pass

        # For FX rate deletion (deletes multiple rates per pair)
        class FXBulkDeleteResponse(BaseBulkDeleteResponse[FXDeleteResult]):
            pass
        ```

    Benefits:
    - Consistent pattern for bulk deletion operations
    - Clear separation: success_count (items) vs total_deleted (records)
    - Inherits all BaseBulkResponse benefits
    - Delete-specific semantics explicit in class name
    """

    # Delete-specific aggregate field
    total_deleted: int = Field(..., ge=0, description="Total number of records deleted across all items")
