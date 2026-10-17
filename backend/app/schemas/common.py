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

from collections.abc import Sequence
from datetime import date as date_type
from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Any, List, Literal, Optional, Union

import pycountry
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, ValidationInfo, field_validator, model_validator
from pydantic.functional_serializers import PlainSerializer

from backend.app.utils.date_range_limits import MAX_BULK_ITEMS, bulk_too_many_items_detail
from backend.app.utils.datetime_utils import EARLIEST_RANGE_START, parse_ISO_date

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
# DECIMAL EXPONENT BOUND — an input never expanded (R13-SEC7-3)
# =============================================================================

MAX_DECIMAL_EXPONENT = 100
"""The largest power of ten, either way, an input amount or quantity may carry (R13-SEC7-3).

No column comes near it — 24 digits before the decimal point at most, 12 after — and the columns' own limits still
decide (``db/precision.decimal_limit_issue``). The bound only keeps a finite value such as ``1E+999999999``, which
pydantic accepts, from reaching a fixed-point format (a billion digits on the event loop) or the context's arithmetic.
"""


def check_decimal_exponent(value: Decimal) -> Decimal:
    """``value``, or a ``ValueError`` (a 422 at the boundary) when its exponent is past ±``MAX_DECIMAL_EXPONENT``.

    ``adjusted()`` is the exponent of the leading digit — the exponent itself for a zero, so ``0E-999999999`` is refused
    too — and costs nothing whatever the value. NaN and the infinities are left to pydantic, which refuses them.
    """
    if value.is_finite() and abs(value.adjusted()) > MAX_DECIMAL_EXPONENT:
        raise ValueError(f"Value out of range: its exponent must be within ±{MAX_DECIMAL_EXPONENT}")
    return value


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

    # Invalid currency
    raise ValueError(f"Invalid currency code: '{code}'. Must be ISO 4217 currency.")


# =============================================================================
# STRICT MODEL BASE
# =============================================================================


class StrictModel(BaseModel):
    """A `BaseModel` that refuses fields it does not declare.

    ``ConfigDict(extra="forbid")`` was repeated **316 times** across the schema
    layer and the AI Export payloads — the single most duplicated line in the
    backend. It is not decoration: forbidding unknown fields is what turns a
    renamed or misspelled key into a loud 422 instead of a value that silently
    goes nowhere, and every one of those 316 classes wanted it.

    Repeating it is how it eventually gets forgotten on the one model where it
    mattered most, and nothing says so. Inheriting it means a new model is strict
    by default and has to *opt out* on purpose, which is the right way round.

    Pydantic merges `model_config` down the inheritance chain, so a subclass that
    genuinely needs something else can still declare its own — the handful that
    do (``from_attributes``, ``frozen``, ``str_strip_whitespace``) keep working
    unchanged.
    """

    model_config = ConfigDict(extra="forbid")


# =============================================================================
# CURRENCY CLASS
# =============================================================================


class Currency(BaseModel):
    """
    Currency amount with validation and arithmetic operations.

    Validates currency codes against ISO 4217 (via pycountry).
    Supports addition/subtraction only between same currencies.
    Amount can be negative.

    Attributes:
        code: ISO 4217 currency code (USD, EUR)
        amount: Decimal amount (can be negative)

    Examples:
        >>> usd = Currency(code="USD", amount=Decimal("100.50"))
        >>> fee = Currency(code="USD", amount=Decimal("2.50"))
        >>> total = usd + fee  # Currency(code="USD", amount=Decimal("103.00"))

        >>> eur = Currency(code="EUR", amount=Decimal("50"))
        >>> usd + eur  # ValueError: Cannot add USD and EUR

        >>> negative = -usd  # Currency(code="USD", amount=Decimal("-100.50"))

    Raises:
        ValueError: If currency code is not valid ISO 4217
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="ISO 4217 currency code")
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
        """Convert amount to Decimal if needed; refuse an exponent past ±100 (``check_decimal_exponent``, R13-SEC7-3)."""
        if isinstance(v, Decimal):
            return check_decimal_exponent(v)
        if isinstance(v, (int, float, str)):
            try:
                amount = Decimal(str(v))
            except Exception:
                raise ValueError(f"Cannot convert '{v}' to Decimal") from None
            return check_decimal_exponent(amount)
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


def is_fiat_currency(value: Any) -> bool:
    """Return True when ``value`` is a valid ISO 4217 currency code.

    Non-raising twin of :meth:`Currency.validate_code`, which already normalises
    (``upper().strip()``) and rejects the empty string. Anything that is not a
    valid code -- a crypto ticker like ``BTC``, an empty cell, ``None``, a number
    a CSV parser failed to coerce -- answers ``False`` instead of raising,
    because callers use this to *classify* a symbol, not to validate input.

    Single source of truth for the "is this fiat?" question. It lives beside
    ``Currency`` because that class already owns ISO 4217 validation and its LRU
    cache; a second normalisation elsewhere is exactly how the four BRIM copies
    of this helper started to drift apart.
    """
    if not isinstance(value, str):
        return False
    try:
        Currency.validate_code(value)
    except ValueError:
        return False
    return True


CurrencyCode = Annotated[str, BeforeValidator(Currency.validate_code)]
"""Use instead of a bare ``str`` for a currency-**code** field that a model **reads back** — a stored value, a
computed payload. A field a request **stores** uses ``IsoCurrencyCode`` instead (E-18, below).

``Currency.validate_code`` normalises (``upper().strip()``) and checks the code against the ISO 4217 registry (via
pycountry), raising ``ValueError`` on a crypto ticker like ``BTC``, an internal placeholder, an empty string. It is
lenient on purpose: ``pycountry.currencies.lookup`` also takes a currency name or a numeric code (``"Euro"``,
``"978"``) and they come back as given, so a value stored before E-18 still loads. This annotated type carries that one
rule so a field opts in *by type* instead of every class repeating its own ``@field_validator`` (nineteen payloads
did, fifteen forgot).

It does **not** change the wire shape: the field stays a JSON string. A value that
is already a valid uppercase code (``"EUR"``) is returned byte-for-byte unchanged,
so ``model_dump()`` of any existing payload is identical; only an *invalid* code --
which no correct payload should ever carry -- is now rejected at construction
instead of leaking out to the model that reads it.

Mirrors ``SafeDecimal`` just above: one rule, written once, inherited by type. Uses
``BeforeValidator`` (not ``AfterValidator``) so it sees the raw input and matches the
definition already used across ``ai_export_runtime`` verbatim, which now imports this
one instead of keeping a divergent copy.

Import::

    from backend.app.schemas.common import CurrencyCode

Usage::

    class MyPayload(StrictModel):
        target_currency: CurrencyCode
        currency: CurrencyCode | None = None  # None passes through; only real codes are checked
"""


# =============================================================================
# STRICT CURRENCY CODES FOR THE WRITE PATHS (E-18, MF-SEC9b)
# =============================================================================

#: How many characters of a refused currency text the error quotes (E-18): enough to recognise it, never a long input.
_REFUSED_CURRENCY_SHOWN = 16


def iso_currency_code(value: Any) -> str:
    """The currency code a write path stores (E-18, MF-SEC9b): an ISO 4217 alphabetic code, in upper case.

    ``Currency.validate_code`` asks ``pycountry.currencies.lookup``, which also takes a currency name or a numeric code
    (``"Euro"``, ``"978"``) and returns it as given: a request could store ``"EURO"`` or ``"978"`` as a currency. Here
    the whitespace around the text is stripped (NBSP included) and the case is free — ``" eur "`` and ``"GBp"`` give
    ``"EUR"`` and ``"GBP"`` —, and what is left must be three ASCII letters ISO 4217 lists as an alphabetic code
    (``XXX``, ``XTS`` and the metals included). Anything else raises ``ValueError``, quoting at most 16 characters of
    the text. The read paths keep ``Currency.validate_code``: a value stored before stays readable and deletable.
    """
    if not isinstance(value, str):
        raise ValueError(f"Currency code must be a string, got {type(value).__name__}")
    code = value.strip().upper()
    if len(code) == 3 and code.isascii() and code.isalpha() and pycountry.currencies.get(alpha_3=code) is not None:
        return code
    shown = code if len(code) <= _REFUSED_CURRENCY_SHOWN else code[:_REFUSED_CURRENCY_SHOWN] + "…"
    raise ValueError(f"Invalid currency code {shown!r}: expected an ISO 4217 alphabetic code, such as EUR")


IsoCurrencyCode = Annotated[str, BeforeValidator(iso_currency_code)]
"""``CurrencyCode`` for a field a write path stores (E-18): an ISO 4217 alphabetic code only, never a name or a number.

A read model keeps ``CurrencyCode``: what was stored before E-18 must still load.
"""


def _iso_currency_amount(value: Currency) -> Currency:
    """An amount a write path stores: its code must pass ``iso_currency_code`` (E-18). The object is unchanged."""
    iso_currency_code(value.code)
    return value


IsoCurrencyAmount = Annotated[Currency, AfterValidator(_iso_currency_amount)]
"""A ``Currency`` a write path stores (E-18): the same class and wire shape, its code an ISO 4217 alphabetic code.

An after-validator, not a subclass: the services and the BRIM plugins build these fields with ``Currency`` objects, which
a subclass would refuse. ``Currency`` itself stays lenient, for the amounts read back from what was stored.
"""


class BackwardFillInfo(BaseModel):
    """
    Backward-fill information when requested date has no data.

    Used by both FX (services/fx/conversion.py) and Asset pricing
    (services/assets/price_query.py) systems to indicate when historical data
    was used instead of exact date match.

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
            raise ValueError(f"end date ({self.end}) must be >= start date ({self.start})")
        return self


# Sentinel type: allows literal "min"/"max" alongside real dates.
DateOrSentinel = Union[date_type, Literal["min", "max"]]


class OpenDateRangeModel(BaseModel):
    """
    Open-ended date range — both start and end are optional.

    Unlike DateRangeModel (which requires start), this model allows
    either or both bounds to be unset:
    - start=None → from the beginning of time
    - end=None → up to today / unbounded future
    - Both None → entire history
    - start="min" → resolved server-side to earliest accessible date
    - end="max" → resolved server-side to latest accessible date / today

    The validator still enforces end >= start when both are concrete dates.

    Use cases: /portfolio/wac date_range, flexible query filters.
    """

    model_config = ConfigDict(extra="forbid")

    start: Optional[DateOrSentinel] = Field(None, description="Start date (inclusive), None = from beginning, 'min' = earliest accessible")
    end: Optional[DateOrSentinel] = Field(None, description="End date (inclusive), None = unbounded / today, 'max' = latest accessible")

    @model_validator(mode="after")
    def validate_end_after_start(self) -> OpenDateRangeModel:
        """Ensure end >= start when both are concrete dates (skip if sentinels)."""
        if self.start is not None and self.end is not None and isinstance(self.start, date_type) and isinstance(self.end, date_type) and self.end < self.start:
            raise ValueError(f"end date ({self.end}) must be >= start date ({self.start})")
        return self

    def has_sentinels(self) -> bool:
        """Return True if either bound is a sentinel string."""
        return self.start in ("min", "max") or self.end in ("min", "max")

    def resolved_start(self) -> Optional[date_type]:
        """Return start as a concrete date, or None if sentinel/None."""
        if self.start is None or isinstance(self.start, str):
            return None
        return self.start

    def resolved_end(self) -> Optional[date_type]:
        """Return end as a concrete date, or None if sentinel/None."""
        if self.end is None or isinstance(self.end, str):
            return None
        return self.end


class PeriodBoundedModel(StrictModel):
    """A `StrictModel` mixin for payloads with a flat inclusive ``[period_start, period_end]``.

    Fourteen AI Export payloads declare ``period_start`` and ``period_end`` as two
    flat ``date`` fields, and not one of them checked that the end is not before
    the start -- so a payload could be exported with an *inverted* period and the
    only thing that could notice would be the model reading it.

    ``DateRangeModel`` has enforced ``end >= start`` forever, but it nests the two
    bounds under ``{"start": ..., "end": ...}``. These payloads are versioned and
    the two flat keys are part of their wire shape, so swapping them for a nested
    range would not be a refactor -- it would break the contract. This mixin keeps
    the two fields **flat** and adds the one validator, so a payload opts in by
    inheriting instead of repeating the rule fourteen times.

    Inheriting the fields moves them to the front of the serialised key order
    (Pydantic emits base-class fields first), which is invisible to every JSON
    consumer -- the object is byte-for-byte the same *set* of keys and values, as
    ``model_dump()`` (order-insensitive) confirms.
    """

    period_start: date_type
    period_end: date_type

    @model_validator(mode="after")
    def validate_period_end_after_start(self) -> PeriodBoundedModel:
        """Ensure ``period_end`` is not before ``period_start``."""
        if self.period_end < self.period_start:
            raise ValueError(f"period_end ({self.period_end}) must be >= period_start ({self.period_start})")
        return self


# =============================================================================
# FIXED-PERIOD CHANGES REQUESTS (MF-P2b, R13-SEC8)
# =============================================================================

#: The distinct ``as_of`` days one fixed-period changes request may value, and as many distinct ``range_start`` days. Each
#: ``as_of`` costs ten valued days — the anchor and one reference per period, a grouped price query each for the assets —,
#: each ``range_start`` one more, so the cost of a request follows its distinct days, not its length. The Assets and FX
#: tables send one of each.
PERIOD_CHANGES_MAX_AS_OF_DAYS = 5


def period_changes_request_refusal(items: Sequence[Any]) -> dict | None:
    """The 422 ``detail`` that refuses a fixed-period changes request, or None when it is within the limits (MF-P2b).

    The limits of the bulk requests the same pages send (Z-25, ``utils/date_range_limits.py``): at most
    ``MAX_BULK_ITEMS`` items (``bulk_too_many_items``); and at most ``PERIOD_CHANGES_MAX_AS_OF_DAYS`` distinct ``as_of``
    days, and as many distinct ``range_start`` days (``period_changes_too_many_days``), in the same shape: a code, a
    message and the numbers. Both checked before any read.
    """
    if len(items) > MAX_BULK_ITEMS:
        return bulk_too_many_items_detail(len(items), MAX_BULK_ITEMS)
    for field in ("as_of", "range_start"):
        days = len({day for item in items if (day := getattr(item, field, None)) is not None})
        if days > PERIOD_CHANGES_MAX_AS_OF_DAYS:
            return {
                "code": "period_changes_too_many_days",
                "message": f"A fixed-period changes request may value at most {PERIOD_CHANGES_MAX_AS_OF_DAYS} distinct {field} days, not {days}",
                "field": field,
                "max_days": PERIOD_CHANGES_MAX_AS_OF_DAYS,
                "days": days,
            }
    return None


def period_changes_as_of(value: date_type, info: ValidationInfo) -> date_type:
    """A day of a fixed-period changes item (``as_of``, ``range_start``): on or after ``EARLIEST_RANGE_START`` (1900-01-01).

    Nothing is valued before it, and up to 0005-12-30 the five-year reference day (1 825 days back) would fall before
    year 1: ``date`` would overflow, a 500.
    """
    if value < EARLIEST_RANGE_START:
        raise ValueError(f"{info.field_name or 'as_of'} ({value}) must be on or after {EARLIEST_RANGE_START}")
    return value


#: The ``as_of`` field of a fixed-period changes item (see :func:`period_changes_as_of`).
PeriodChangesAsOf = Annotated[date_type, AfterValidator(period_changes_as_of)]


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
    - errors: Optional list of error messages (operation-level errors, not per-item)

    Design Notes:
    - Generic class parameterized by TResult (the result item type)
    - Subclasses inherit this structure and specify their result type
    - errors field is for operation-level errors (e.g., "timeout", "provider unavailable")
    - Per-item errors should be in the result items themselves

    Examples:
        ```python
        class FABulkAssetCreateResponse(BaseBulkResponse[FAAssetCreateResult]):
            # Inherits: results, success_count, errors
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
