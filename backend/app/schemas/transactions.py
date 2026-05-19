"""
Transaction schemas for LibreFolio.

DTOs for Transaction CRUD operations.
These schemas provide strict validation for API input/output.

**Naming Convention**:
- TX prefix: Transaction-related schemas
- Item suffix: Single item in a list (e.g., TXCreateItem)

**Design Notes**:
- Tags are List[str] in schemas, stored as comma-separated string in DB
- Uses Currency from common.py for amount+currency validation
- Uses DateRangeModel from common.py for date filtering
- link_uuid is used during bulk creation to link paired transactions (TRANSFER, FX_CONVERSION)
"""

from __future__ import annotations

from datetime import date as date_type
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.common import (
    BackwardFillInfo,
    BaseDeleteResult,
    BaseListResponse,
    Currency,
    DateRangeModel,
    FxBackwardFillInfo,
    SafeDecimal,
)
from backend.app.utils.datetime_utils import UTCDateTime

# =============================================================================
# SHARED VALIDATORS (DRY)
# =============================================================================


# Transaction types that can be linked to an AssetEvent.
# Rationale:
# - DIVIDEND / INTEREST: direct cash realization of a global payout event
# - ADJUSTMENT: captures SPLIT / PRICE_ADJUSTMENT asset-level effects
EVENT_COMPATIBLE_TYPES: frozenset[TransactionType] = frozenset(
    {
        TransactionType.DIVIDEND,
        TransactionType.INTEREST,
        TransactionType.ADJUSTMENT,
    }
)


def validate_tags_list(v) -> Optional[List[str]]:
    """
    Shared validator for tags field.

    Accepts:
    - None -> None
    - List[str] -> List[str] (stripped, non-empty)
    - str (comma-separated) -> List[str]

    Returns list of non-empty stripped strings, or None if empty.
    """
    if v is None:
        return None
    if isinstance(v, str):
        tags = [t.strip() for t in v.split(",") if t.strip()]
        return tags if tags else None
    if isinstance(v, list):
        tags = [str(t).strip() for t in v if str(t).strip()]
        return tags if tags else None
    raise ValueError("tags must be a list of strings or comma-separated string")


def tags_to_csv(tags: Optional[List[str]]) -> Optional[str]:
    """Convert tags list to comma-separated string for DB storage."""
    if not tags:
        return None
    return ",".join(tags)


# =============================================================================
# TRANSACTION CREATE
# =============================================================================


class TXCreateItem(BaseModel):
    """
    DTO for creating a single transaction.

    Used by POST /api/v1/transactions endpoint.

    Field semantics:
    - quantity: Asset delta (+ buy/in, - sell/out). Default 0.
    - cash: Currency object with code + amount. None if no cash movement.
    - link_uuid: Temporary UUID to link paired transactions in bulk create

    Sign rules per type:
    - BUY: quantity > 0, cash.amount < 0
    - SELL: quantity < 0, cash.amount > 0
    - DIVIDEND/INTEREST: quantity = 0, cash.amount > 0
    - DEPOSIT: quantity = 0, cash.amount > 0
    - WITHDRAWAL: quantity = 0, cash.amount < 0
    - FEE/TAX: quantity = 0, cash.amount < 0
    - TRANSFER: quantity +/-, cash = None, link_uuid REQUIRED
    - FX_CONVERSION: quantity = 0, cash.amount +/-, link_uuid REQUIRED
    - ADJUSTMENT: quantity +/-, cash = None
    """

    model_config = ConfigDict(extra="forbid")

    broker_id: int = Field(..., description="Broker ID")
    asset_id: Optional[int] = Field(default=None, description="Asset ID. NULL for pure cash transactions")

    type: TransactionType = Field(..., description="Transaction type")
    date: date_type = Field(..., description="Settlement date")

    quantity: SafeDecimal = Field(default=Decimal("0"), description="Asset quantity delta (+ in, - out)")

    # Cash movement using Currency class from common.py
    cash: Optional[Currency] = Field(default=None, description="Cash movement (code + amount). Required for cash operations.")

    # Temporary linking for bulk create (not persisted)
    link_uuid: Optional[str] = Field(
        default=None,
        max_length=36,
        description="Temporary UUID to link paired transactions (TRANSFER, FX_CONVERSION)",
    )

    tags: Optional[List[str]] = Field(default=None, description="List of tags for filtering/grouping")
    description: Optional[str] = Field(default=None, max_length=500, description="Transaction notes")

    # Frozen cost basis for TRANSFER_IN - snapshot of PMC at transfer time
    # Object {code, amount} — e.g. {"code": "EUR", "amount": "42.50"}
    cost_basis_override: Optional[Currency] = Field(default=None,description="Frozen cost basis for TRANSFER_IN. Object {code, amount}.",)

    # Link to AssetEvent (realization of a global asset event in this portfolio).
    # Only valid for event-compatible types (see EVENT_COMPATIBLE_TYPES).
    # Cross-record check (asset_id must match event.asset_id) is done in service layer.
    # Omit or set to None to leave the transaction unlinked.
    asset_event_id: Optional[int] = Field(default=None, description="Link to AssetEvent (DIVIDEND/INTEREST/ADJUSTMENT only). Omit to leave unlinked.")

    @field_validator("tags", mode="before")
    @classmethod
    def _validate_tags(cls, v):
        return validate_tags_list(v)

    @model_validator(mode="after")
    def validate_transaction_rules(self) -> TXCreateItem:
        """Validate transaction business rules based on 1.4 Constraint Analysis table.

        Collects ALL violations instead of raising at the first one, so the
        frontend can display a full error list in a single validate round-trip.
        """
        t = self.type.value  # shorthand for error params
        errors: list[PydanticCustomError] = []

        # Field-level positivity checks (moved from Field(gt=0) so they are
        # collected alongside business-rule errors instead of blocking them).
        if self.broker_id <= 0:
            errors.append(PydanticCustomError("brokerRequired", "Please select a broker (broker_id must be > 0)", {"broker_id": self.broker_id}))
        if self.asset_id is not None and self.asset_id <= 0:
            errors.append(PydanticCustomError("assetIdInvalid", "asset_id must be > 0 when provided", {"asset_id": self.asset_id}))
        if self.asset_event_id is not None and self.asset_event_id <= 0:
            errors.append(PydanticCustomError("assetEventIdInvalid", "asset_event_id must be > 0 when provided", {"asset_event_id": self.asset_event_id}))

        # Rule 1: TRANSFER, FX_CONVERSION, and CASH_TRANSFER require link_uuid
        if self.type in (TransactionType.TRANSFER, TransactionType.FX_CONVERSION, TransactionType.CASH_TRANSFER):
            if not self.link_uuid:
                errors.append(PydanticCustomError("linkUuidRequired", "{type} requires link_uuid for pairing", {"type": t}))

        # Rule 2: TRANSFER requires asset_id and quantity != 0, no cash
        if self.type == TransactionType.TRANSFER:
            if not self.asset_id:
                errors.append(PydanticCustomError("assetRequired", "TRANSFER requires asset_id", {"type": t}))
            if self.quantity == Decimal("0"):
                errors.append(PydanticCustomError("qtyNonzero", "TRANSFER requires quantity != 0", {"type": t}))
            if self.cash is not None and not self.cash.is_zero():
                errors.append(PydanticCustomError("cashForbidden", "TRANSFER should not have cash movement", {"type": t}))

        # Rule 3: FX_CONVERSION requires quantity = 0 and cash with amount != 0, no asset
        if self.type == TransactionType.FX_CONVERSION:
            if self.asset_id is not None:
                errors.append(PydanticCustomError("assetForbidden", "FX_CONVERSION should not have asset_id", {"type": t}))
            if self.quantity != Decimal("0"):
                errors.append(PydanticCustomError("fxConversionQtyZero", "FX_CONVERSION should have quantity = 0", {"type": t}))
            if self.cash is None or self.cash.is_zero():
                errors.append(PydanticCustomError("fxConversionCashRequired", "FX_CONVERSION requires cash with amount != 0", {"type": t}))

        # Rule 3b: CASH_TRANSFER requires quantity = 0 and cash with amount != 0, no asset
        if self.type == TransactionType.CASH_TRANSFER:
            if self.asset_id is not None:
                errors.append(PydanticCustomError("assetForbidden", "CASH_TRANSFER should not have asset_id", {"type": t}))
            if self.quantity != Decimal("0"):
                errors.append(PydanticCustomError("qtyZero", "CASH_TRANSFER should have quantity = 0", {"type": t}))
            if self.cash is None or self.cash.is_zero():
                errors.append(PydanticCustomError("cashRequired", "CASH_TRANSFER requires cash with amount != 0", {"type": t}))

        # Rule 4: DEPOSIT/WITHDRAWAL/CASH_TRANSFER are pure cash - no asset allowed
        if self.type in (TransactionType.DEPOSIT, TransactionType.WITHDRAWAL, TransactionType.CASH_TRANSFER):
            if self.asset_id is not None:
                errors.append(PydanticCustomError("assetForbidden", "{type} should not have asset_id", {"type": t}))

        # Rule 5: Asset REQUIRED for BUY, SELL, DIVIDEND, TRANSFER, ADJUSTMENT
        asset_required_types = {
            TransactionType.BUY,
            TransactionType.SELL,
            TransactionType.DIVIDEND,
            TransactionType.TRANSFER,
            TransactionType.ADJUSTMENT,
        }
        if self.type in asset_required_types and not self.asset_id:
            errors.append(PydanticCustomError("assetRequired", "{type} requires asset_id", {"type": t}))

        # Rule 6: Asset OPTIONAL for INTEREST, FEE, TAX (no validation needed)

        # Rule 7: Cash REQUIRED for all types except TRANSFER, ADJUSTMENT
        cash_required_types = {
            TransactionType.BUY,
            TransactionType.SELL,
            TransactionType.DIVIDEND,
            TransactionType.INTEREST,
            TransactionType.DEPOSIT,
            TransactionType.WITHDRAWAL,
            TransactionType.FEE,
            TransactionType.TAX,
            TransactionType.FX_CONVERSION,
            TransactionType.CASH_TRANSFER,
        }
        if self.type in cash_required_types:
            if self.cash is None:
                errors.append(PydanticCustomError("cashRequired", "{type} requires cash (amount + currency)", {"type": t}))

        # Rule 8: ADJUSTMENT should not have cash
        if self.type == TransactionType.ADJUSTMENT:
            if self.cash is not None and not self.cash.is_zero():
                errors.append(PydanticCustomError("cashForbidden", "ADJUSTMENT should not have cash movement", {"type": t}))

        # Rule 9: asset_event_id requires event-compatible type + asset_id present.
        if self.asset_event_id is not None:
            if self.type not in EVENT_COMPATIBLE_TYPES:
                allowed = sorted(tt.value for tt in EVENT_COMPATIBLE_TYPES)
                errors.append(
                    PydanticCustomError(
                        "eventTypeIncompatible",
                        "{type} cannot be linked to an asset_event (only {allowed} can)",
                        {"type": t, "allowed": ", ".join(allowed)},
                    )
                )
            if self.asset_id is None:
                errors.append(PydanticCustomError("eventRequiresAsset", "asset_event_id requires asset_id", {"type": t}))

        # Rule 10: Per-type quantity sign enforcement
        zero = Decimal("0")
        if self.type == TransactionType.BUY and self.quantity <= zero:
            errors.append(PydanticCustomError("qtyPositive", "BUY requires quantity > 0", {"type": t}))
        if self.type == TransactionType.SELL and self.quantity >= zero:
            errors.append(PydanticCustomError("qtyNegative", "SELL requires quantity < 0", {"type": t}))
        if (
            self.type
            in (
                TransactionType.DIVIDEND,
                TransactionType.INTEREST,
                TransactionType.DEPOSIT,
                TransactionType.WITHDRAWAL,
                TransactionType.FEE,
                TransactionType.TAX,
                TransactionType.CASH_TRANSFER,
            )
            and self.quantity != zero
        ):
            errors.append(PydanticCustomError("qtyZero", "{type} requires quantity = 0", {"type": t}))
        if self.type == TransactionType.ADJUSTMENT and self.quantity == zero:
            errors.append(PydanticCustomError("qtyNonzero", "ADJUSTMENT requires quantity != 0", {"type": t}))

        # Rule 11: Per-type cash sign enforcement
        if self.cash is not None and not self.cash.is_zero():
            amt = self.cash.amount
            if self.type in (TransactionType.BUY, TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.TAX) and amt >= zero:
                errors.append(PydanticCustomError("cashSignNegative", "{type} requires cash.amount < 0", {"type": t}))
            if self.type in (TransactionType.SELL, TransactionType.DIVIDEND, TransactionType.INTEREST, TransactionType.DEPOSIT) and amt <= zero:
                errors.append(PydanticCustomError("cashSignPositive", "{type} requires cash.amount > 0", {"type": t}))

        # Pydantic v2 model_validator can only raise a single exception.
        # When there are multiple business-rule errors, we pack them ALL into
        # one PydanticCustomError with type "multipleBusinessRuleErrors" and
        # the full list serialised in ctx.errors.  The frontend unpacks this
        # special type back into separate per-issue messages.
        if errors:
            if len(errors) == 1:
                raise errors[0]
            raise PydanticCustomError(
                "multipleBusinessRuleErrors",
                "{error_count} business-rule validation errors",
                {
                    "error_count": len(errors),
                    "errors": [
                        {
                            "code": e.type,
                            "msg": e.message_template,
                            "ctx": e.context or {},
                        }
                        for e in errors
                    ],
                },
            )

        return self

    def get_amount(self) -> Decimal:
        """Get cash amount or 0 if no cash."""
        return self.cash.amount if self.cash else Decimal("0")

    def get_currency(self) -> Optional[str]:
        """Get currency code or None if no cash."""
        return self.cash.code if self.cash else None

    def get_tags_csv(self) -> Optional[str]:
        """Convert tags list to comma-separated string for DB storage."""
        return tags_to_csv(self.tags)


# =============================================================================
# TRANSACTION READ
# =============================================================================


class TXReadItem(BaseModel):
    """
    DTO for reading a transaction from the API.

    This is the response format for GET operations.
    Uses Currency for cash representation.

    Note on linked transactions:
    With bidirectional DEFERRABLE FK, related_transaction_id is populated
    on BOTH transactions in a pair (A->B and B->A), so no separate
    linked_transaction_id field is needed.
    """

    model_config = ConfigDict(extra="forbid")

    id: int
    broker_id: int
    asset_id: Optional[int] = None

    type: TransactionType
    date: date_type

    quantity: SafeDecimal

    # Cash as Currency object (None if amount is 0)
    cash: Optional[Currency] = None

    # DB field: bidirectional link to paired transaction (TRANSFER, FX_CONVERSION)
    # Both transactions in a pair point to each other
    related_transaction_id: Optional[int] = None

    # Broker of the partner transaction (populated by service layer).
    # Allows the frontend to show the partner broker name/icon even when
    # the user has no access to the partner transaction itself.
    partner_broker_id: Optional[int] = None

    tags: Optional[List[str]] = None
    description: Optional[str] = None

    # Frozen cost basis for TRANSFER_IN (None for normal transactions)
    # Object {code, amount} when set.
    cost_basis_override: Optional[Currency] = None

    # Link to the AssetEvent realized by this transaction (None = stand-alone)
    asset_event_id: Optional[int] = None

    created_at: UTCDateTime
    updated_at: UTCDateTime

    @classmethod
    def from_db_model(cls, tx: Transaction) -> TXReadItem:
        """
        Create TXReadItem from database Transaction model.

        With bidirectional FK (DEFERRABLE), related_transaction_id is always
        populated correctly in both directions. No need for external lookup.

        Args:
            tx: Transaction SQLModel instance from database

        Returns:
            TXReadItem DTO ready for API response
        """
        # Convert DB amount+currency to Currency object
        cash = None
        if tx.amount != Decimal("0") and tx.currency:
            cash = Currency(code=tx.currency, amount=tx.amount)

        # Convert CSV tags to list
        tags = None
        if tx.tags:
            tags = [t.strip() for t in tx.tags.split(",") if t.strip()]

        # Build Currency from cost_basis DB fields
        cost_basis = None
        if tx.cost_basis_override is not None and tx.cost_basis_currency is not None:
            cost_basis = Currency(code=tx.cost_basis_currency, amount=tx.cost_basis_override)

        return cls(
            id=tx.id,
            broker_id=tx.broker_id,
            asset_id=tx.asset_id,
            type=tx.type,
            date=tx.date,
            quantity=tx.quantity,
            cash=cash,
            related_transaction_id=tx.related_transaction_id,
            tags=tags,
            description=tx.description,
            cost_basis_override=cost_basis,
            asset_event_id=tx.asset_event_id,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
        )


# =============================================================================
# TRANSACTION UPDATE
# =============================================================================

# Sign-flip swap groups: types with identical field structure that can be
# swapped.  Types not listed here are singletons (swap group = [self]).
# Paired types are currently singletons but this may evolve.
SWAP_GROUPS: list[frozenset[TransactionType]] = [
    frozenset({TransactionType.BUY, TransactionType.SELL}),
    frozenset({TransactionType.DEPOSIT, TransactionType.WITHDRAWAL}),
    frozenset({TransactionType.DIVIDEND, TransactionType.INTEREST}),
    frozenset({TransactionType.TAX, TransactionType.FEE}),
]


def get_swap_group(tx_type: TransactionType) -> frozenset[TransactionType]:
    """Return the swap group containing *tx_type*, or a singleton frozenset."""
    for group in SWAP_GROUPS:
        if tx_type in group:
            return group
    return frozenset({tx_type})


def _swap_group_codes(tx_type: TransactionType) -> list[str]:
    """Return swap partners as a sorted list of code strings (EXCLUDING self).
    Empty list = no swap possible (singleton or paired type)."""
    group = get_swap_group(tx_type)
    return sorted(t.value for t in group if t != tx_type)


class TXUpdateItem(BaseModel):
    """
    DTO for updating a transaction.

    All fields are optional except id.
    Only provided fields will be updated.

    Type change is limited to "sign-flip" swaps within the same swap group
    (e.g. BUY↔SELL, DEPOSIT↔WITHDRAWAL).  Paired types cannot be swapped.

    Note on related_transaction_id:
    This field cannot be updated directly via this DTO.
    To update linked transactions (TRANSFER, FX_CONVERSION):
    1. Delete both transactions
    2. Re-create them with new link_uuid
    Or send updates for BOTH transactions in the same bulk request.
    """

    model_config = ConfigDict(extra="forbid")

    # NOTE: gt=0 removed from Field — enforced in model_validator so that
    # Pydantic doesn't short-circuit and the full error set is returned.
    id: int = Field(..., description="Transaction ID to update")

    # Sign-flip: only within the same swap group (BUY↔SELL, DEPOSIT↔WITHDRAWAL, etc.)
    type: Optional[TransactionType] = Field(default=None, description="New type (sign-flip swap only)")

    date: Optional[date_type] = Field(default=None, description="New settlement date")
    quantity: Optional[SafeDecimal] = Field(default=None, description="New quantity")

    # Cash update using Currency class
    cash: Optional[Currency] = Field(default=None, description="New cash (code + amount)")

    tags: Optional[List[str]] = Field(default=None, description="New tags (replaces existing)")
    description: Optional[str] = Field(default=None, max_length=500, description="New description")

    # Frozen cost basis override (for TRANSFER_IN) — object {code, amount}
    cost_basis_override: Optional[Currency] = Field(default=None,description="Frozen cost basis for TRANSFER_IN. Object {code, amount}.",)

    # Link/unlink to AssetEvent:
    # - None   -> leave asset_event_id unchanged
    # - 0      -> UNLINK (set to NULL) — Part 1 sentinel
    # - n > 0  -> link to the given AssetEvent (validated in service layer)
    asset_event_id: Optional[int] = Field(default=None, ge=0, description="Link/unlink to AssetEvent. 0 = unlink (Part 1 sentinel), >0 = link, None = leave unchanged.")

    @field_validator("tags", mode="before")
    @classmethod
    def _validate_tags(cls, v):
        return validate_tags_list(v)

    @model_validator(mode="after")
    def _business_rules(self) -> "TXUpdateItem":
        """Validate id > 0 in the model_validator so Pydantic doesn't
        short-circuit and the full error set is always returned."""
        if self.id is not None and self.id <= 0:
            raise PydanticCustomError(
                "idRequired",
                "Transaction id must be > 0",
                {"id": self.id},
            )
        return self

    def get_tags_csv(self) -> Optional[str]:
        """Convert tags list to comma-separated string for DB storage."""
        return tags_to_csv(self.tags)


# =============================================================================
# TRANSACTION QUERY
# =============================================================================


class TXQueryParams(BaseModel):
    """
    Query parameters for filtering transactions.

    Used by GET /api/v1/transactions endpoint.
    """

    model_config = ConfigDict(extra="forbid")

    broker_id: Optional[int] = Field(default=None, gt=0, description="Filter by broker")
    asset_id: Optional[int] = Field(default=None, gt=0, description="Filter by asset")
    types: Optional[List[TransactionType]] = Field(default=None, description="Filter by types")

    # When set, other filters are ignored and the service returns the requested
    # transactions in the exact order specified (preserving client-side ordering).
    ids: Optional[List[int]] = Field(default=None, description="Fetch specific IDs preserving input order")

    # Date range using DateRangeModel from common.py
    date_range: Optional[DateRangeModel] = Field(default=None, description="Filter by date range")

    tags: Optional[List[str]] = Field(default=None, description="Filter by tags (any match)")
    currency: Optional[str] = Field(default=None, max_length=3, description="Filter by currency")

    # H.3: transfer-match helpers. Composable with the other filters. When `ids`
    # is set, these filters (including exclude_ids) are ignored.
    amount_abs_min: Optional[SafeDecimal] = Field(default=None, description="ABS(amount) >= N")
    amount_abs_max: Optional[SafeDecimal] = Field(default=None, description="ABS(amount) <= N")
    only_unlinked: bool = Field(default=False, description="related_transaction_id IS NULL")
    exclude_ids: Optional[List[int]] = Field(default=None, description="Transaction.id NOT IN (...)")

    limit: int = Field(default=100, ge=1, le=1000, description="Max results")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")

    @field_validator("tags", mode="before")
    @classmethod
    def _validate_tags(cls, v):
        return validate_tags_list(v)

    @field_validator("currency", mode="before")
    @classmethod
    def _validate_currency(cls, v):
        if v is None:
            return v
        return Currency.validate_code(v)


# =============================================================================
# TRANSACTION DELETE
# =============================================================================


class TXDeleteItem(BaseModel):
    """Single transaction ID to delete."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., gt=0, description="Transaction ID to delete")


# Per-item diagnostic status for atomic bulk operations.
# - "success":       item applied AND the whole batch committed.
# - "simulated":     item applied in-session but batch was rolled back (another
#                    item failed or balance validation triggered).
# - "failed":        the item itself raised the error that caused the rollback.
# - "not_attempted": processing stopped before this item was considered.
TXItemStatus = Literal["success", "simulated", "failed", "not_attempted"]

# Batch operation types — single source of truth for all operation Literals.
TXBatchOperation = Literal["create", "update", "delete", "split", "promote"]


class TXDeleteResult(BaseDeleteResult):
    """
    Result for a single transaction deletion attempt.

    Extends BaseDeleteResult with transaction-specific identifier and the
    atomic diagnostic status.
    """

    id: int = Field(..., description="Transaction ID")
    status: TXItemStatus = Field(default="not_attempted", description="Atomic diagnostic status")


# =============================================================================
# UNIFIED BATCH (Unified Batch Pipeline — replaces POST/PATCH/DELETE /bulk)
# =============================================================================


class TXMixedBatch(BaseModel):
    """Unified batch body for /validate and /commit.

    `creates` and `updates` are List[dict] (not List[TXCreateItem]) so that
    FastAPI does NOT pre-validate individual rows. The service does per-row
    model_validate() in try/except, collecting schema errors alongside
    business-rule and balance violations in one response.
    """

    model_config = ConfigDict(extra="forbid")

    creates: List[dict] = Field(default_factory=list, max_length=500)
    updates: List[dict] = Field(default_factory=list, max_length=500)
    deletes: List[int] = Field(default_factory=list, max_length=500)
    splits: List[dict] = Field(default_factory=list, max_length=100)
    promotes: List[dict] = Field(default_factory=list, max_length=100)


# =============================================================================
# WAC (WEIGHTED AVERAGE COST) — FX-aware calculation results
# =============================================================================


class WACConversionInfo(BaseModel):
    """Single FX conversion applied during WAC calculation."""

    model_config = ConfigDict(extra="forbid")

    tx_id: int = Field(..., description="Transaction ID that needed conversion")
    from_currency: str = Field(..., description="Original currency of the transaction")
    to_currency: str = Field(..., description="Target currency for WAC")
    rate: SafeDecimal = Field(..., description="FX rate applied")
    rate_date: date_type = Field(..., description="Actual date of the FX rate used")
    stale_days: int = Field(0, ge=0, description="Days between TX date and rate date (0 = fresh)")


class WACResult(BaseModel):
    """Result of weighted average cost calculation with FX details.

    - wac is None when at least one FX conversion failed (see missing_pairs).
    - wac is Currency(code=target, amount="0") when total_qty == 0 without FX errors.
    """

    model_config = ConfigDict(extra="forbid")

    wac: Optional[Currency] = Field(None, description="Calculated WAC. None if FX conversion failed.")
    conversions: List[WACConversionInfo] = Field(default_factory=list, description="FX conversions applied")
    missing_pairs: List[str] = Field(default_factory=list, description="FX pairs that could not be resolved (e.g. 'CHF/EUR')")


# =============================================================================
# WAC PREVIEW — Explicit preview endpoint (replaces auto-calc at commit)
# =============================================================================


class WACPreviewItem(BaseModel):
    """Single WAC preview request within a bulk call.

    Uses DateRangeModel to define the computation period:
    - start: beginning of the range (TXs from this date onward are considered)
    - end: effective end date for WAC computation (if None → today)
    """

    model_config = ConfigDict(extra="forbid")

    sender_broker_id: int = Field(..., description="Broker ID of the source (sender) side")
    asset_id: int = Field(..., description="Asset ID to calculate WAC for")
    date_range: DateRangeModel = Field(..., description="Date range for WAC computation. end=None means today.")

    @property
    def end_date(self) -> date_type:
        """The effective end date for WAC computation."""
        return self.date_range.end or date_type.today()


class WACPendingTXItem(TXCreateItem):
    """A pending TX from workspace for WAC calculation.

    Extends TXCreateItem to inherit full semantic validation.
    Overrides: asset_id is required (WAC always needs an asset).
    Added: id field to identify DB rows to override.
    """

    id: Optional[int] = Field(None, description="DB id to override, or None for new pending TX")
    asset_id: int = Field(..., description="Asset ID (required for WAC calculation)")


class WACPreviewRequest(BaseModel):
    """Bulk WAC preview request."""

    model_config = ConfigDict(extra="forbid")

    items: List[WACPreviewItem] = Field(..., min_length=1, max_length=50)
    pending_txs: List[WACPendingTXItem] = Field(default_factory=list, max_length=500)
    excluded_tx_ids: List[int] = Field(default_factory=list, max_length=500, description="DB TX ids to exclude (deleted in workspace)")


class WACQualifyingTX(BaseModel):
    """A TX that participated in WAC calculation."""

    model_config = ConfigDict(extra="forbid")

    tx_id: Optional[int] = Field(None, description="DB id, or None if pending without id")
    type: str
    date: date_type
    quantity: SafeDecimal
    unit_cost: Optional[SafeDecimal] = None
    currency: Optional[str] = None
    effect: str = Field(..., description="add | reduce | add_zero_cost | skip_no_override")
    fx_info: Optional[FxBackwardFillInfo] = None


class WACPreviewResultItem(BaseModel):
    """Result for a single WAC preview item."""

    model_config = ConfigDict(extra="forbid")

    # WAC inventory-aware
    wac: Optional[Currency] = Field(None, description="Calculated WAC per unit. None if FX conversion failed.")
    wac_qualifying_txs: List[WACQualifyingTX] = Field(default_factory=list)
    wac_missing_pairs: List[str] = Field(default_factory=list)
    # Asset price at date (useful for ADJUSTMENT scenario)
    asset_price: Optional[Currency] = Field(None, description="Asset close price at as_of_date (backward-filled)")
    asset_price_stale: Optional[BackwardFillInfo] = Field(None, description="Staleness of asset price")
    asset_price_missing: bool = Field(False, description="True if no price data available at all")


class WACPreviewResponse(BaseListResponse[WACPreviewResultItem]):
    """Response for POST /transactions/wac-preview. items[i] ↔ request.items[i]."""

    pass



class TXBatchResultItem(BaseModel):
    """Per-item result for committed rows."""

    model_config = ConfigDict(extra="forbid")

    operation: TXBatchOperation
    index: int
    ids: List[int] = Field(default_factory=list, description="IDs of affected transactions. Split/promote return both IDs.")
    link_uuid: Optional[str] = None
    status: TXItemStatus


class TXBatchResponse(BaseModel):
    """Unified response for /validate and /commit."""

    model_config = ConfigDict(extra="forbid")

    committed: bool
    issues: List[TXValidationIssue] = Field(default_factory=list)
    results: Optional[List[TXBatchResultItem]] = None


# =============================================================================
# VALIDATION CODES (F13 — centralized enum)
# =============================================================================


class TXValidationCode(str, Enum):
    """Centralized validation error codes for transaction operations.

    Frontend maps these to i18n keys via `transactions.errors.{code}`.
    Exposed in GET /transactions/types → validation_codes.
    """

    BALANCE_ASSET_NEGATIVE = "balanceAssetNegative"
    BALANCE_CASH_NEGATIVE = "balanceCashNegative"
    TX_NOT_FOUND = "txNotFound"
    TYPE_CANNOT_SPLIT = "typeCannotSplit"
    SPLIT_IDS_MISMATCH = "splitIdsMismatch"
    PROMOTE_REF_NOT_FOUND = "promoteRefNotFound"
    ALREADY_PAIRED = "alreadyPaired"
    NO_PROMOTE_RULE = "noPromoteRule"
    ACCESS_DENIED = "accessDenied"
    LINK_UUID_PAIR_COUNT = "linkUuidPairCount"


class TXValidationCodeInfo(BaseModel):
    """Metadata for a validation code — exposed in GET /transactions/types."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Validation code identifier")
    description: str = Field(..., description="Human-readable description")
    severity: Literal["error", "warning"] = Field("error", description="Issue severity")


# Precomputed list of all validation codes for the types endpoint.
VALIDATION_CODE_METADATA: list[TXValidationCodeInfo] = [TXValidationCodeInfo(code=c.value, description=c.name.replace("_", " ").title(), severity="error") for c in TXValidationCode]


# =============================================================================
# VALIDATION ISSUE
# =============================================================================


class TXValidationIssue(BaseModel):
    """Single issue produced by validate_batch."""

    model_config = ConfigDict(extra="forbid")

    operation: TXBatchOperation
    index: int = Field(..., ge=-1, description="Index within the corresponding list (-1 = broker-level, not row-specific)")
    ref_id: Optional[int] = Field(default=None, description="Transaction ID for update/delete, None for create")
    error: str
    code: Optional[str] = Field(default=None, description="i18n error code from the catalog (e.g. 'assetRequired')")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Structured params for frontend i18n resolver (IDs, dates, amounts)")
    field: Optional[str] = Field(default=None, description="Draft field that caused the error (e.g. 'asset_id', 'quantity')")


# =============================================================================
# EVENTS SUGGEST (Block C.2)
# =============================================================================


class TXEventSuggestRequestItem(BaseModel):
    """
    Single suggest request: given (asset_id, date, type), find candidate
    AssetEvent rows within +/- tolerance_days whose type maps to the tx type.
    """

    model_config = ConfigDict(extra="forbid")

    asset_id: int = Field(..., gt=0)
    date: date_type
    type: TransactionType
    tolerance_days: int = Field(0, ge=0, le=7, description="Days window (+/-) around date")


class TXEventSuggestCandidate(BaseModel):
    """Lean AssetEvent projection returned as a candidate."""

    model_config = ConfigDict(extra="forbid")

    id: int
    asset_id: int
    date: date_type
    type: str
    value: SafeDecimal
    currency: str
    is_auto: bool
    distance_days: int = Field(..., ge=0, description="abs(event.date - request.date)")


class TXEventSuggestResultItem(BaseModel):
    """Result for one request — candidates sorted by ascending distance."""

    model_config = ConfigDict(extra="forbid")

    asset_id: int
    date: date_type
    type: TransactionType
    candidates: List[TXEventSuggestCandidate] = Field(default_factory=list)
    skipped_reason: Optional[Literal["type_not_event_compatible"]] = None


# =============================================================================
# TRANSFER PROMOTION (Block H.4)
# =============================================================================


class TXTransferPromoteRequest(BaseModel):
    """
    Atomically promote a DEPOSIT/WITHDRAWAL pair into a TRANSFER (with asset)
    or FX_CONVERSION (cross-currency, same broker).

    Cannot be done via PATCH because `type` is immutable on existing rows —
    the endpoint deletes the original pair and creates a new one within a
    single session.
    """

    model_config = ConfigDict(extra="forbid")

    from_tx_id: int = Field(..., gt=0, description="Source transaction (e.g. original WITHDRAWAL)")
    to_tx_id: int = Field(..., gt=0, description="Destination transaction (e.g. original DEPOSIT)")
    new_type: Literal[TransactionType.TRANSFER, TransactionType.FX_CONVERSION] = Field(
        ...,
        description="Target type after promotion",
    )
    # Required when new_type == TRANSFER (cash -> asset transfer).
    asset_id: Optional[int] = Field(default=None, gt=0)
    quantity: Optional[SafeDecimal] = Field(default=None, description="Asset quantity for TRANSFER")
    # Optional override for cost_basis_override propagated on the TRANSFER
    # destination item; if None the service will not set it.
    # Object {code, amount} — e.g. {"code": "EUR", "amount": "42.50"}
    cost_basis_override: Optional[Currency] = None


class TXTransferPromoteResponse(BaseModel):
    """Outcome of /transactions/transfers/promote."""

    model_config = ConfigDict(extra="forbid")

    rolled_back: bool
    new_from_tx_id: Optional[int] = None
    new_to_tx_id: Optional[int] = None
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# BATCH SPLIT / PROMOTE ITEMS (pipeline-only, no standalone endpoints)
# =============================================================================


class TXSplitBatchItem(BaseModel):
    """Single split within a batch. Both IDs of the pair must be provided."""

    model_config = ConfigDict(extra="forbid")

    id_a: int = Field(..., gt=0, description="ID of one half of the pair")
    id_b: int = Field(..., gt=0, description="ID of the other half of the pair")

    @model_validator(mode="after")
    def ids_must_differ(self) -> "TXSplitBatchItem":
        if self.id_a == self.id_b:
            raise ValueError("id_a and id_b must be different transactions")
        return self


class TXPromoteBatchItem(BaseModel):
    """Single promote within a batch. Supports saved+saved, new+new, saved+new."""

    model_config = ConfigDict(extra="forbid")

    id_a: Optional[int] = Field(None, gt=0, description="Real ID for saved TX A")
    id_b: Optional[int] = Field(None, gt=0, description="Real ID for saved TX B")
    link_uuid_a: Optional[str] = Field(None, max_length=36, description="link_uuid to resolve TX A from creates in same batch")
    link_uuid_b: Optional[str] = Field(None, max_length=36, description="link_uuid to resolve TX B from creates in same batch")
    resolved_fields: Optional[Dict[str, Any]] = Field(None, description="Merged field values from PromoteMergeModal: description, tags, date, cost_basis_override")

    @model_validator(mode="after")
    def _validate_refs(self) -> "TXPromoteBatchItem":
        """At least one of id_a/link_uuid_a and id_b/link_uuid_b must be set."""
        if self.id_a is None and self.link_uuid_a is None:
            raise ValueError("Either id_a or link_uuid_a must be provided for TX A")
        if self.id_b is None and self.link_uuid_b is None:
            raise ValueError("Either id_b or link_uuid_b must be provided for TX B")
        if self.id_a is not None and self.link_uuid_a is not None:
            raise ValueError("Provide either id_a or link_uuid_a for TX A, not both")
        if self.id_b is not None and self.link_uuid_b is not None:
            raise ValueError("Provide either id_b or link_uuid_b for TX B, not both")
        return self


# =============================================================================
# PROMOTE-SUGGEST (bulk candidate search)
# =============================================================================


class TXPromoteSuggestInput(BaseModel):
    """Single TX to find promote candidates for. id < 0 = fake (unsaved)."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="Real ID (>0) or fake ID (<0) for unsaved TX")
    type: TransactionType
    broker_id: int = Field(..., gt=0)
    date: date_type
    currency: Optional[str] = None
    asset_id: Optional[int] = None
    amount: Optional[SafeDecimal] = None
    quantity: Optional[SafeDecimal] = None


class TXPromoteSuggestCandidate(BaseModel):
    """A DB transaction that could be promoted with the input TX."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., gt=0)
    broker_id: int
    date: date_type
    type: str
    currency: Optional[str] = None
    asset_id: Optional[int] = None


class TXPromoteSuggestResponse(BaseModel):
    """Map of input id/fakeId → list of DB candidates."""

    model_config = ConfigDict(extra="forbid")

    results: Dict[int, List[TXPromoteSuggestCandidate]]


# =============================================================================
# TRANSACTION TYPE METADATA
# =============================================================================

# Sign types for validation — semantic enum used by both quantity and cash fields.
# All values lowercase so the frontend can use them as-is without mapping.
SignType = Literal["positive", "negative", "zero", "nonzero", "free"]

# Field mode — controls whether a field is shown / required / hidden.
# Shared by asset_mode, cash_mode, quantity_mode.
FieldMode = Literal["required", "optional", "forbidden"]

# Pair form layout — controls the dual-transaction form layout in the frontend.
# None = standard single form, otherwise specifies which dual form to show.
PairFormLayout = Literal["fx", "transfer_asset", "transfer_cash"]

# Field constraint relation — how a field relates between the two halves of a pair.
PairFieldRelation = Literal["equal", "opposite", "different"]


class PairFieldConstraint(BaseModel):
    """How a field relates between the two halves of a pair."""

    model_config = ConfigDict(extra="forbid")

    field: Literal["broker_id", "asset_id", "cash_currency", "cash_amount", "quantity"] = Field(..., description="Transaction field name")
    relation: PairFieldRelation = Field(
        ...,
        description="Constraint: equal (same value), opposite (negated), different (must differ)",
    )


class SplitMeta(BaseModel):
    """How a paired type splits into 2 standalone types."""

    model_config = ConfigDict(extra="forbid")

    from_type: str = Field(..., description="Type for 'from' half (negative/source side)")
    to_type: str = Field(..., description="Type for 'to' half (positive/destination side)")


class PromoteRule(BaseModel):
    """How 2 standalone types can be promoted to this paired type."""

    model_config = ConfigDict(extra="forbid")

    type_a: str = Field(..., description="First standalone type")
    type_b: str = Field(..., description="Second standalone type")
    field_constraints: list[PairFieldConstraint] = Field(..., description="Validation rules for the pair")


class TXTypeMetadata(BaseModel):
    """
    Metadata about a transaction type.

    Used by GET /api/v1/transactions/types endpoint.
    Frontend uses these values directly (all lowercase, no mapping needed).
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Enum code (e.g., 'BUY')")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Human-readable description")
    icon_slug: str = Field(..., description="Slug for icon path (e.g. 'buy' → /icons/transactions/buy.png)")
    doc_slug: str | None = Field(None, description="Slug for docs page (e.g. 'buy-sell' → mkdocs path). None if no dedicated page.")

    # Field modes — frontend uses these directly for show/hide/required gating
    asset_mode: FieldMode = Field(..., description="required: must have asset_id, optional: can have, forbidden: must not have")
    cash_mode: FieldMode = Field(..., description="required: must have cash, optional: can have, forbidden: must not have")
    quantity_mode: FieldMode = Field(..., description="required: must have quantity ≠ 0, optional: can have, forbidden: must be 0")

    # Whether link_uuid is required (paired transactions: TRANSFER, FX_CONVERSION)
    requires_link: bool = Field(..., description="Whether link_uuid is required")

    # Sign constraints (lowercase, frontend uses as-is)
    quantity_sign: SignType = Field(..., description="Allowed quantity sign constraint")
    cash_sign: SignType = Field(..., description="Allowed cash amount sign constraint")

    # Whether this type can be linked to an AssetEvent (see EVENT_COMPATIBLE_TYPES)
    event_compatible: bool = Field(..., description="Can be linked to an AssetEvent")

    # Pair form layout — tells frontend which dual-transaction form to use.
    # None = standard single form. Set for types that are inherently paired.
    pair_form_layout: PairFormLayout | None = Field(
        None,
        description="Dual-form layout: 'fx' (2 currencies, 1 broker), " "'transfer_asset' (2 brokers, 1 asset), 'transfer_cash' (2 brokers, 1 currency). " "None = standard single form.",
    )

    # Split/Promote server-driven metadata (only for paired types, None for standalone)
    split_into: SplitMeta | None = Field(
        None,
        description="How this paired type splits into 2 standalone types. None for standalone types.",
    )
    promote_from: list[PromoteRule] | None = Field(
        None,
        description="Rules for promoting 2 standalone types into this paired type. None for standalone types.",
    )
    pair_field_constraints: list[PairFieldConstraint] | None = Field(
        None,
        description="Field equivalence constraints between the two halves of a pair. None for standalone types.",
    )

    # Swap group — types this type can be "flipped" to (including itself).
    # Singleton = [self] (no swap partners). Frontend uses this directly.
    swap_group: list[str] = Field(default_factory=list, description="Other type codes this type can be swapped with (sign-flip). Empty = no swap.")


# Precomputed metadata for all transaction types.
# swap_group is auto-populated from SWAP_GROUPS via _swap_group_codes().
def _build_tx_type_metadata() -> dict[TransactionType, TXTypeMetadata]:
    """Build metadata dict with auto-populated swap_group field."""
    raw: dict[TransactionType, dict] = {
        TransactionType.BUY: dict(
            code="BUY",
            name="Buy",
            description="Purchase asset with cash",
            icon_slug="buy",
            doc_slug="buy-sell",
            asset_mode="required",
            cash_mode="required",
            quantity_mode="required",
            requires_link=False,
            quantity_sign="positive",
            cash_sign="negative",
            event_compatible=False,
        ),
        TransactionType.SELL: dict(
            code="SELL",
            name="Sell",
            description="Sell asset for cash",
            icon_slug="sell",
            doc_slug="buy-sell",
            asset_mode="required",
            cash_mode="required",
            quantity_mode="required",
            requires_link=False,
            quantity_sign="negative",
            cash_sign="positive",
            event_compatible=False,
        ),
        TransactionType.DIVIDEND: dict(
            code="DIVIDEND",
            name="Dividend",
            description="Dividend payment received",
            icon_slug="dividend",
            doc_slug="dividend",
            asset_mode="required",
            cash_mode="required",
            quantity_mode="forbidden",
            requires_link=False,
            quantity_sign="zero",
            cash_sign="positive",
            event_compatible=True,
        ),
        TransactionType.INTEREST: dict(
            code="INTEREST",
            name="Interest",
            description="Interest payment (bond or deposit)",
            icon_slug="interest",
            doc_slug="interest",
            asset_mode="optional",
            cash_mode="required",
            quantity_mode="forbidden",
            requires_link=False,
            quantity_sign="zero",
            cash_sign="positive",
            event_compatible=True,
        ),
        TransactionType.DEPOSIT: dict(
            code="DEPOSIT",
            name="Deposit",
            description="Add cash to broker account",
            icon_slug="deposit",
            doc_slug="deposit-withdrawal",
            asset_mode="forbidden",
            cash_mode="required",
            quantity_mode="forbidden",
            requires_link=False,
            quantity_sign="zero",
            cash_sign="positive",
            event_compatible=False,
        ),
        TransactionType.WITHDRAWAL: dict(
            code="WITHDRAWAL",
            name="Withdrawal",
            description="Remove cash from broker account",
            icon_slug="withdrawal",
            doc_slug="deposit-withdrawal",
            asset_mode="forbidden",
            cash_mode="required",
            quantity_mode="forbidden",
            requires_link=False,
            quantity_sign="zero",
            cash_sign="negative",
            event_compatible=False,
        ),
        TransactionType.FEE: dict(
            code="FEE",
            name="Fee",
            description="Fee or commission (trading or account)",
            icon_slug="fee",
            doc_slug="fee",
            asset_mode="optional",
            cash_mode="required",
            quantity_mode="forbidden",
            requires_link=False,
            quantity_sign="zero",
            cash_sign="negative",
            event_compatible=False,
        ),
        TransactionType.TAX: dict(
            code="TAX",
            name="Tax",
            description="Tax payment (capital gain or stamp duty)",
            icon_slug="tax",
            doc_slug="fee",
            asset_mode="optional",
            cash_mode="required",
            quantity_mode="forbidden",
            requires_link=False,
            quantity_sign="zero",
            cash_sign="negative",
            event_compatible=False,
        ),
        TransactionType.TRANSFER: dict(
            code="TRANSFER",
            name="Asset Transfer",
            description="Asset transfer between brokers",
            icon_slug="transfer",
            doc_slug="transfer",
            asset_mode="required",
            cash_mode="forbidden",
            quantity_mode="required",
            requires_link=True,
            quantity_sign="nonzero",
            cash_sign="zero",
            event_compatible=False,
            pair_form_layout="transfer_asset",
            split_into=SplitMeta(from_type="ADJUSTMENT", to_type="ADJUSTMENT"),
            promote_from=[
                PromoteRule(
                    type_a="ADJUSTMENT",
                    type_b="ADJUSTMENT",
                    field_constraints=[
                        PairFieldConstraint(field="asset_id", relation="equal"),
                        PairFieldConstraint(field="broker_id", relation="different"),
                        PairFieldConstraint(field="quantity", relation="opposite"),
                    ],
                ),
            ],
            pair_field_constraints=[
                PairFieldConstraint(field="asset_id", relation="equal"),
                PairFieldConstraint(field="broker_id", relation="different"),
                PairFieldConstraint(field="quantity", relation="opposite"),
            ],
        ),
        TransactionType.FX_CONVERSION: dict(
            code="FX_CONVERSION",
            name="FX Conversion",
            description="Currency exchange",
            icon_slug="fx-conversion",
            doc_slug="fx-conversion",
            asset_mode="forbidden",
            cash_mode="required",
            quantity_mode="forbidden",
            requires_link=True,
            quantity_sign="zero",
            cash_sign="nonzero",
            event_compatible=False,
            pair_form_layout="fx",
            split_into=SplitMeta(from_type="WITHDRAWAL", to_type="DEPOSIT"),
            promote_from=[
                PromoteRule(
                    type_a="WITHDRAWAL",
                    type_b="DEPOSIT",
                    field_constraints=[
                        PairFieldConstraint(field="cash_currency", relation="different"),
                        PairFieldConstraint(field="broker_id", relation="equal"),
                    ],
                ),
            ],
            pair_field_constraints=[
                PairFieldConstraint(field="cash_currency", relation="different"),
                PairFieldConstraint(field="broker_id", relation="equal"),
            ],
        ),
        TransactionType.ADJUSTMENT: dict(
            code="ADJUSTMENT",
            name="Adjustment",
            description="Manual quantity correction (splits, gifts)",
            icon_slug="adjustment",
            doc_slug="adjustment",
            asset_mode="required",
            cash_mode="forbidden",
            quantity_mode="required",
            requires_link=False,
            quantity_sign="nonzero",
            cash_sign="zero",
            event_compatible=True,
        ),
        TransactionType.CASH_TRANSFER: dict(
            code="CASH_TRANSFER",
            name="Cash Transfer",
            description="Wire transfer / bonifico between brokers",
            icon_slug="cash-transfer",
            doc_slug="cash-transfer",
            asset_mode="forbidden",
            cash_mode="required",
            quantity_mode="forbidden",
            requires_link=True,
            quantity_sign="zero",
            cash_sign="nonzero",
            event_compatible=False,
            pair_form_layout="transfer_cash",
            split_into=SplitMeta(from_type="WITHDRAWAL", to_type="DEPOSIT"),
            promote_from=[
                PromoteRule(
                    type_a="WITHDRAWAL",
                    type_b="DEPOSIT",
                    field_constraints=[
                        PairFieldConstraint(field="cash_currency", relation="equal"),
                        PairFieldConstraint(field="broker_id", relation="different"),
                        PairFieldConstraint(field="cash_amount", relation="opposite"),
                    ],
                ),
            ],
            pair_field_constraints=[
                PairFieldConstraint(field="cash_currency", relation="equal"),
                PairFieldConstraint(field="broker_id", relation="different"),
                PairFieldConstraint(field="cash_amount", relation="opposite"),
            ],
        ),
    }
    # Auto-populate swap_group for every type
    result: dict[TransactionType, TXTypeMetadata] = {}
    for tx_type, kwargs in raw.items():
        kwargs["swap_group"] = _swap_group_codes(tx_type)
        result[tx_type] = TXTypeMetadata(**kwargs)
    return result


TX_TYPE_METADATA: dict[TransactionType, TXTypeMetadata] = _build_tx_type_metadata()


class EventTypeMetadata(BaseModel):
    """Metadata about an asset event type for frontend rendering."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Enum code (e.g., 'DIVIDEND')")
    name: str = Field(..., description="Display name")
    emoji: str = Field(..., description="Emoji icon for rendering")
    compatible_tx_types: list[str] = Field(..., description="Transaction types that can link to this event type")


class TXTypesResponse(BaseModel):
    """Combined response for GET /transactions/types."""

    model_config = ConfigDict(extra="forbid")

    transaction_types: list[TXTypeMetadata]
    event_types: list[EventTypeMetadata]
    validation_codes: list[TXValidationCodeInfo] = Field(
        default_factory=lambda: VALIDATION_CODE_METADATA,
        description="All known validation error codes with descriptions",
    )


# Precomputed metadata for all event types
EVENT_TYPE_METADATA: list[EventTypeMetadata] = [
    EventTypeMetadata(
        code="DIVIDEND",
        name="Dividend",
        emoji="💰",
        compatible_tx_types=["DIVIDEND"],
    ),
    EventTypeMetadata(
        code="INTEREST",
        name="Interest",
        emoji="📈",
        compatible_tx_types=["INTEREST"],
    ),
    EventTypeMetadata(
        code="SPLIT",
        name="Split",
        emoji="✂️",
        compatible_tx_types=["ADJUSTMENT"],
    ),
    EventTypeMetadata(
        code="PRICE_ADJUSTMENT",
        name="Price Adjustment",
        emoji="📊",
        compatible_tx_types=["ADJUSTMENT"],
    ),
    EventTypeMetadata(
        code="MATURITY_SETTLEMENT",
        name="Maturity Settlement",
        emoji="🏁",
        compatible_tx_types=["INTEREST"],
    ),
]
