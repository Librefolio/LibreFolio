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
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.common import (
    BaseBulkDeleteResponse,
    BaseBulkResponse,
    BaseDeleteResult,
    Currency,
    DateRangeModel,
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

    broker_id: int = Field(..., gt=0, description="Broker ID")
    asset_id: Optional[int] = Field(default=None, gt=0, description="Asset ID. NULL for pure cash transactions")

    type: TransactionType = Field(..., description="Transaction type")
    date: date_type = Field(..., description="Settlement date")

    quantity: Decimal = Field(default=Decimal("0"), description="Asset quantity delta (+ in, - out)")

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
    cost_basis_override: Optional[Decimal] = Field(
        default=None,
        description="Frozen cost basis for TRANSFER_IN. Overrides calculated cost basis.",
    )

    # Link to AssetEvent (realization of a global asset event in this portfolio).
    # Only valid for event-compatible types (see EVENT_COMPATIBLE_TYPES).
    # Cross-record check (asset_id must match event.asset_id) is done in service layer.
    # Omit or set to None to leave the transaction unlinked.
    asset_event_id: Optional[int] = Field(default=None, gt=0, description="Link to AssetEvent (DIVIDEND/INTEREST/ADJUSTMENT only). Omit to leave unlinked.")

    @field_validator("tags", mode="before")
    @classmethod
    def _validate_tags(cls, v):
        return validate_tags_list(v)

    @model_validator(mode="after")
    def validate_transaction_rules(self) -> TXCreateItem:
        """Validate transaction business rules based on 1.4 Constraint Analysis table."""

        # TODO(frozenset): the inline tuples below (TRANSFER/FX_CONVERSION,
        # DEPOSIT/WITHDRAWAL) and the local sets `asset_required_types` /
        # `cash_required_types` are rebuilt on every validate call. Promote to
        # module-level `frozenset[TransactionType]` constants (next to
        # EVENT_COMPATIBLE_TYPES) for O(1) membership + immutability + no
        # per-call allocation. Purely a cleanup: no behavior change.
        # Rule 1: TRANSFER and FX_CONVERSION require link_uuid
        if self.type in (TransactionType.TRANSFER, TransactionType.FX_CONVERSION):
            if not self.link_uuid:
                raise ValueError(f"{self.type.value} requires link_uuid for pairing")

        # Rule 2: TRANSFER requires asset_id and quantity != 0, no cash
        if self.type == TransactionType.TRANSFER:
            if not self.asset_id:
                raise ValueError("TRANSFER requires asset_id")
            if self.quantity == Decimal("0"):
                raise ValueError("TRANSFER requires quantity != 0")
            if self.cash is not None and not self.cash.is_zero():
                raise ValueError("TRANSFER should not have cash movement")

        # Rule 3: FX_CONVERSION requires quantity = 0 and cash with amount != 0, no asset
        if self.type == TransactionType.FX_CONVERSION:
            if self.asset_id is not None:
                raise ValueError("FX_CONVERSION should not have asset_id")
            if self.quantity != Decimal("0"):
                raise ValueError("FX_CONVERSION should have quantity = 0")
            if self.cash is None or self.cash.is_zero():
                raise ValueError("FX_CONVERSION requires cash with amount != 0")

        # Rule 4: DEPOSIT/WITHDRAWAL are pure cash - no asset allowed
        if self.type in (TransactionType.DEPOSIT, TransactionType.WITHDRAWAL):
            if self.asset_id is not None:
                raise ValueError(f"{self.type.value} should not have asset_id")

        # Rule 5: Asset REQUIRED for BUY, SELL, DIVIDEND, TRANSFER, ADJUSTMENT
        asset_required_types = {
            TransactionType.BUY,
            TransactionType.SELL,
            TransactionType.DIVIDEND,
            TransactionType.TRANSFER,
            TransactionType.ADJUSTMENT,
        }
        if self.type in asset_required_types and not self.asset_id:
            raise ValueError(f"{self.type.value} requires asset_id")

        # Rule 6: Asset OPTIONAL for INTEREST, FEE, TAX (no validation needed)
        # - INTEREST: bond interest (asset) vs deposit interest (no asset)
        # - FEE: trading commission (asset) vs annual fee (no asset)
        # - TAX: capital gain tax (asset) vs stamp duty (no asset)

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
        }
        if self.type in cash_required_types:
            if self.cash is None:
                raise ValueError(f"{self.type.value} requires cash (amount + currency)")

        # Rule 8: ADJUSTMENT should not have cash
        if self.type == TransactionType.ADJUSTMENT:
            if self.cash is not None and not self.cash.is_zero():
                raise ValueError("ADJUSTMENT should not have cash movement")

        # Rule 9: asset_event_id requires event-compatible type + asset_id present.
        # NOTE: cross-record check (asset_id == asset_event.asset_id) is in service layer.
        if self.asset_event_id is not None:
            if self.type not in EVENT_COMPATIBLE_TYPES:
                raise ValueError(f"{self.type.value} cannot be linked to an asset_event " f"(only {sorted(t.value for t in EVENT_COMPATIBLE_TYPES)} can)")
            if self.asset_id is None:
                raise ValueError("asset_event_id requires asset_id")

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

    quantity: Decimal

    # Cash as Currency object (None if amount is 0)
    cash: Optional[Currency] = None

    # DB field: bidirectional link to paired transaction (TRANSFER, FX_CONVERSION)
    # Both transactions in a pair point to each other
    related_transaction_id: Optional[int] = None

    tags: Optional[List[str]] = None
    description: Optional[str] = None

    # Frozen cost basis for TRANSFER_IN (None for normal transactions)
    cost_basis_override: Optional[Decimal] = None

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
            cost_basis_override=tx.cost_basis_override,
            asset_event_id=tx.asset_event_id,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
        )


# =============================================================================
# TRANSACTION UPDATE
# =============================================================================


class TXUpdateItem(BaseModel):
    """
    DTO for updating a transaction.

    All fields are optional except id.
    Only provided fields will be updated.

    Note: Changing type is not allowed. Create a new transaction instead.

    Note on related_transaction_id:
    This field cannot be updated directly via this DTO.
    To update linked transactions (TRANSFER, FX_CONVERSION):
    1. Delete both transactions
    2. Re-create them with new link_uuid
    Or send updates for BOTH transactions in the same bulk request.
    """

    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., gt=0, description="Transaction ID to update")

    date: Optional[date_type] = Field(default=None, description="New settlement date")
    quantity: Optional[Decimal] = Field(default=None, description="New quantity")

    # Cash update using Currency class
    cash: Optional[Currency] = Field(default=None, description="New cash (code + amount)")

    tags: Optional[List[str]] = Field(default=None, description="New tags (replaces existing)")
    description: Optional[str] = Field(default=None, max_length=500, description="New description")

    # Frozen cost basis override (for TRANSFER_IN)
    cost_basis_override: Optional[Decimal] = Field(
        default=None,
        description="Frozen cost basis for TRANSFER_IN. Set to override calculated cost basis.",
    )

    # Link/unlink to AssetEvent:
    # - None   -> leave asset_event_id unchanged
    # - 0      -> UNLINK (set to NULL) — Part 1 sentinel
    # - n > 0  -> link to the given AssetEvent (validated in service layer)
    asset_event_id: Optional[int] = Field(default=None, ge=0, description="Link/unlink to AssetEvent. 0 = unlink (Part 1 sentinel), >0 = link, None = leave unchanged.")

    @field_validator("tags", mode="before")
    @classmethod
    def _validate_tags(cls, v):
        return validate_tags_list(v)

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


class TXDeleteResult(BaseDeleteResult):
    """
    Result for a single transaction deletion attempt.

    Extends BaseDeleteResult with transaction-specific identifier and the
    atomic diagnostic status.
    """

    id: int = Field(..., description="Transaction ID")
    status: TXItemStatus = Field(default="not_attempted", description="Atomic diagnostic status")


class TXBulkDeleteResponse(BaseBulkDeleteResponse[TXDeleteResult]):
    """
    Response for bulk transaction deletion.

    `rolled_back=True` means the whole batch was rejected at the DB level,
    so every item's `status` is either `failed` or `simulated`/`not_attempted`.
    """

    rolled_back: bool = Field(default=False, description="True if the whole batch was rolled back")


# =============================================================================
# BULK CREATE RESPONSE
# =============================================================================


class TXCreateResultItem(BaseModel):
    """Result for a single transaction creation attempt."""

    model_config = ConfigDict(extra="forbid")

    success: bool
    status: TXItemStatus = Field(default="not_attempted", description="Atomic diagnostic status")
    transaction_id: Optional[int] = None
    link_uuid: Optional[str] = None  # Echo back for client correlation
    error: Optional[str] = None


class TXBulkCreateResponse(BaseBulkResponse[TXCreateResultItem]):
    """
    Response for bulk transaction creation.

    Atomic semantics: if `rolled_back=True`, no transaction was persisted.
    Use per-item `status` to distinguish the failing item from the rest.
    """

    rolled_back: bool = Field(default=False, description="True if the whole batch was rolled back")


# =============================================================================
# BULK UPDATE RESPONSE
# =============================================================================


class TXUpdateResultItem(BaseModel):
    """Result for a single transaction update attempt."""

    model_config = ConfigDict(extra="forbid")

    id: int
    success: bool
    status: TXItemStatus = Field(default="not_attempted", description="Atomic diagnostic status")
    error: Optional[str] = None


class TXBulkUpdateResponse(BaseBulkResponse[TXUpdateResultItem]):
    """
    Response for bulk transaction update.

    Atomic semantics: see `TXBulkCreateResponse`.
    """

    rolled_back: bool = Field(default=False, description="True if the whole batch was rolled back")


# =============================================================================
# VALIDATE (DRY-RUN MIXED BATCH — see Block C)
# =============================================================================


class TXValidateBatch(BaseModel):
    """
    Input for POST /transactions/validate — mixed dry-run batch.

    The three lists are applied in the order `deletes -> updates -> creates`
    inside a single session that is always rolled back at the end. Used by
    the Staging Modal to provide live feedback while the user edits drafts.
    """

    model_config = ConfigDict(extra="forbid")

    creates: List[TXCreateItem] = Field(default_factory=list, max_length=500)
    updates: List[TXUpdateItem] = Field(default_factory=list, max_length=500)
    deletes: List[int] = Field(default_factory=list, max_length=500, description="Transaction IDs to delete")


class TXValidationIssue(BaseModel):
    """Single issue produced by validate_batch."""

    model_config = ConfigDict(extra="forbid")

    operation: Literal["create", "update", "delete"]
    index: int = Field(..., ge=0, description="Index within the corresponding list")
    ref_id: Optional[int] = Field(default=None, description="Transaction ID for update/delete, None for create")
    error: str


class TXValidateResponse(BaseModel):
    """
    Result of POST /transactions/validate.

    `would_rollback` is True whenever at least one issue exists OR a balance
    violation is detected. `balance_preview` and `holdings_preview` are only
    meaningful when `would_rollback=False`.
    """

    model_config = ConfigDict(extra="forbid")

    would_rollback: bool
    issues: List[TXValidationIssue] = Field(default_factory=list)
    # Per-broker balances keyed by "{broker_id}:{currency}" for cash and
    # "{broker_id}:asset:{asset_id}" for holdings, so callers can identify
    # which broker a value belongs to when the batch spans multiple brokers.
    balance_preview: Dict[str, Decimal] = Field(default_factory=dict)
    holdings_preview: Dict[str, Decimal] = Field(default_factory=dict)


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
    value: Decimal
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
# TRANSACTION TYPE METADATA
# =============================================================================

# Sign types for validation
# + := must be positive, - := must be negative, 0 := must be zero, +/- := any non-zero value
SignType = Literal["+", "-", "0", "+/-"]

# Asset requirement modes
AssetMode = Literal["REQUIRED", "OPTIONAL", "FORBIDDEN"]


class TXTypeMetadata(BaseModel):
    """
    Metadata about a transaction type.

    Used by GET /api/v1/transactions/types endpoint.
    Frontend uses this to validate user input before submission.
    """

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Enum code (e.g., 'BUY')")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Human-readable description")
    icon: str = Field(..., description="Icon identifier or emoji")

    # Validation rules for frontend
    asset_mode: AssetMode = Field(
        ...,
        description="REQUIRED: must have asset_id, OPTIONAL: can have, FORBIDDEN: must not have",
    )
    requires_link: bool = Field(..., description="Whether link_uuid is required")
    requires_cash: bool = Field(..., description="Whether cash is required")

    # Allowed signs for validation ('+', '-', '0', '+/-')
    allowed_quantity_sign: SignType = Field(..., description="Allowed quantity sign")
    allowed_cash_sign: SignType = Field(..., description="Allowed cash amount sign")

    # Whether this type can be linked to an AssetEvent (see EVENT_COMPATIBLE_TYPES)
    event_compatible: bool = Field(..., description="Can be linked to an AssetEvent")


# TODO: aggiornare le Icone passando le immagini di icone che svilupperemo
# Precomputed metadata for all transaction types
TX_TYPE_METADATA: dict[TransactionType, TXTypeMetadata] = {
    TransactionType.BUY: TXTypeMetadata(
        code="BUY",
        name="Buy",
        description="Purchase asset with cash",
        icon="🛒",
        asset_mode="REQUIRED",
        requires_link=False,
        requires_cash=True,
        allowed_quantity_sign="+",
        allowed_cash_sign="-",
        event_compatible=False,
    ),
    TransactionType.SELL: TXTypeMetadata(
        code="SELL",
        name="Sell",
        description="Sell asset for cash",
        icon="💸",
        asset_mode="REQUIRED",
        requires_link=False,
        requires_cash=True,
        allowed_quantity_sign="-",
        allowed_cash_sign="+",
        event_compatible=False,
    ),
    TransactionType.DIVIDEND: TXTypeMetadata(
        code="DIVIDEND",
        name="Dividend",
        description="Dividend payment received",
        icon="💵",
        asset_mode="REQUIRED",
        requires_link=False,
        requires_cash=True,
        allowed_quantity_sign="0",
        allowed_cash_sign="+",
        event_compatible=True,
    ),
    TransactionType.INTEREST: TXTypeMetadata(
        code="INTEREST",
        name="Interest",
        description="Interest payment (bond or deposit)",
        icon="📈",
        asset_mode="OPTIONAL",
        requires_link=False,
        requires_cash=True,
        allowed_quantity_sign="0",
        allowed_cash_sign="+",
        event_compatible=True,
    ),
    TransactionType.DEPOSIT: TXTypeMetadata(
        code="DEPOSIT",
        name="Deposit",
        description="Add cash to broker account",
        icon="💰",
        asset_mode="FORBIDDEN",
        requires_link=False,
        requires_cash=True,
        allowed_quantity_sign="0",
        allowed_cash_sign="+",
        event_compatible=False,
    ),
    TransactionType.WITHDRAWAL: TXTypeMetadata(
        code="WITHDRAWAL",
        name="Withdrawal",
        description="Remove cash from broker account",
        icon="🏧",
        asset_mode="FORBIDDEN",
        requires_link=False,
        requires_cash=True,
        allowed_quantity_sign="0",
        allowed_cash_sign="-",
        event_compatible=False,
    ),
    TransactionType.FEE: TXTypeMetadata(
        code="FEE",
        name="Fee",
        description="Fee or commission (trading or account)",
        icon="📋",
        asset_mode="OPTIONAL",
        requires_link=False,
        requires_cash=True,
        allowed_quantity_sign="0",
        allowed_cash_sign="-",
        event_compatible=False,
    ),
    TransactionType.TAX: TXTypeMetadata(
        code="TAX",
        name="Tax",
        description="Tax payment (capital gain or stamp duty)",
        icon="🏛️",
        asset_mode="OPTIONAL",
        requires_link=False,
        requires_cash=True,
        allowed_quantity_sign="0",
        allowed_cash_sign="-",
        event_compatible=False,
    ),
    TransactionType.TRANSFER: TXTypeMetadata(
        code="TRANSFER",
        name="Transfer",
        description="Asset transfer between brokers",
        icon="🔄",
        asset_mode="REQUIRED",
        requires_link=True,
        requires_cash=False,
        allowed_quantity_sign="+/-",
        allowed_cash_sign="0",
        event_compatible=False,
    ),
    TransactionType.FX_CONVERSION: TXTypeMetadata(
        code="FX_CONVERSION",
        name="FX Conversion",
        description="Currency exchange",
        icon="💱",
        asset_mode="FORBIDDEN",
        requires_link=True,
        requires_cash=True,
        allowed_quantity_sign="0",
        allowed_cash_sign="+/-",
        event_compatible=False,
    ),
    TransactionType.ADJUSTMENT: TXTypeMetadata(
        code="ADJUSTMENT",
        name="Adjustment",
        description="Manual quantity correction (splits, gifts)",
        icon="⚙️",
        asset_mode="REQUIRED",
        requires_link=False,
        requires_cash=False,
        allowed_quantity_sign="+/-",
        allowed_cash_sign="0",
        event_compatible=True,
    ),
}
