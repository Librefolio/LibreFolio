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
from typing import List, Literal, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

from backend.app.db.models import Transaction, TransactionType
from backend.app.schemas.common import (
    Currency,
    DateRangeModel,
    SafeDecimal,
    StrictModel,
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


def validate_transaction_business_rules(  # noqa: C901 — flat per-rule error collection
    *,
    tx_type: TransactionType,
    asset_id: Optional[int],
    quantity: Decimal,
    cash: Optional[Currency],
    asset_event_id: Optional[int],
    cost_basis_mode: Optional[str],
) -> List[PydanticCustomError]:
    """Per-type business rules (Rules 5-12) evaluated on the FINAL normalized
    transaction state (type + asset_id + cash + quantity + asset_event_id +
    cost_basis_mode).

    Pure function: it *returns* the list of violations instead of raising, so
    both the CREATE path (``TXCreateItem.validate_transaction_rules``) and the
    UPDATE merge path (``TransactionService`` bulk-update loop) can enforce
    identical semantics on the resulting transaction. It deliberately receives
    the already-normalized final state (primitives + ``Currency``) rather than a
    DTO, so CREATE and UPDATE stay decoupled.

    Create-only concerns are NOT part of this shared function and remain in
    ``TXCreateItem``: field-level positivity (broker_id / id) and the pairing
    rules 1-4 (link_uuid, TRANSFER/FX_CONVERSION/CASH_TRANSFER shape).
    """
    t = tx_type.value  # shorthand for error params
    errors: List[PydanticCustomError] = []
    zero = Decimal("0")

    # Rule 5: Asset REQUIRED for BUY, SELL, DIVIDEND, TRANSFER, ADJUSTMENT
    asset_required_types = {
        TransactionType.BUY,
        TransactionType.SELL,
        TransactionType.DIVIDEND,
        TransactionType.TRANSFER,
        TransactionType.ADJUSTMENT,
    }
    if tx_type in asset_required_types and not asset_id:
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
    if tx_type in cash_required_types:
        if cash is None:
            errors.append(PydanticCustomError("cashRequired", "{type} requires cash (amount + currency)", {"type": t}))

    # Rule 8: ADJUSTMENT should not have cash
    if tx_type == TransactionType.ADJUSTMENT:
        if cash is not None and not cash.is_zero():
            errors.append(PydanticCustomError("cashForbidden", "ADJUSTMENT should not have cash movement", {"type": t}))

    # Rule 9: asset_event_id requires event-compatible type + asset_id present.
    if asset_event_id is not None:
        if tx_type not in EVENT_COMPATIBLE_TYPES:
            allowed = sorted(tt.value for tt in EVENT_COMPATIBLE_TYPES)
            errors.append(
                PydanticCustomError(
                    "eventTypeIncompatible",
                    "{type} cannot be linked to an asset_event (only {allowed} can)",
                    {"type": t, "allowed": ", ".join(allowed)},
                )
            )
        if asset_id is None:
            errors.append(PydanticCustomError("eventRequiresAsset", "asset_event_id requires asset_id", {"type": t}))

    # Rule 10: Per-type quantity sign enforcement
    if tx_type == TransactionType.BUY and quantity <= zero:
        errors.append(PydanticCustomError("qtyPositive", "BUY requires quantity > 0", {"type": t}))
    if tx_type == TransactionType.SELL and quantity >= zero:
        errors.append(PydanticCustomError("qtyNegative", "SELL requires quantity < 0", {"type": t}))
    if (
        tx_type
        in (
            TransactionType.DIVIDEND,
            TransactionType.INTEREST,
            TransactionType.DEPOSIT,
            TransactionType.WITHDRAWAL,
            TransactionType.FEE,
            TransactionType.TAX,
            TransactionType.CASH_TRANSFER,
        )
        and quantity != zero
    ):
        errors.append(PydanticCustomError("qtyZero", "{type} requires quantity = 0", {"type": t}))
    if tx_type == TransactionType.ADJUSTMENT and quantity == zero:
        errors.append(PydanticCustomError("qtyNonzero", "ADJUSTMENT requires quantity != 0", {"type": t}))

    # Rule 11: Per-type cash sign enforcement
    if cash is not None and not cash.is_zero():
        amt = cash.amount
        if tx_type in (TransactionType.BUY, TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.TAX) and amt >= zero:
            errors.append(PydanticCustomError("cashSignNegative", "{type} requires cash.amount < 0", {"type": t}))
        if tx_type in (TransactionType.SELL, TransactionType.DIVIDEND, TransactionType.INTEREST, TransactionType.DEPOSIT) and amt <= zero:
            errors.append(PydanticCustomError("cashSignPositive", "{type} requires cash.amount > 0", {"type": t}))

    # Rule 12: cost_basis_mode is only valid for:
    #   - TRANSFER with quantity > 0 (receiver side)
    #   - ADJUSTMENT with quantity > 0
    if cost_basis_mode is not None:
        cbm_valid = False
        if tx_type == TransactionType.TRANSFER and quantity > zero:
            cbm_valid = True
        elif tx_type == TransactionType.ADJUSTMENT and quantity > zero:
            cbm_valid = True
        if not cbm_valid:
            errors.append(
                PydanticCustomError(
                    "costBasisModeIncompatible",
                    "cost_basis_mode is only valid for TRANSFER receiver (qty>0) or ADJUSTMENT (qty>0), got {type} qty={qty}",
                    {"type": t, "qty": str(quantity)},
                )
            )

    return errors


# =============================================================================
# TRANSACTION CREATE
# =============================================================================


class TXCreateItem(StrictModel):
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

    # Frozen cost basis for TRANSFER_IN - snapshot of PMC at transfer time.
    # IMPORTANT: amount is PER-UNIT (weighted-average cost per single unit), NOT a total.
    # The engine multiplies it by quantity. Divide any TOTAL countervalue by quantity first.
    # Object {code, amount} — e.g. {"code": "EUR", "amount": "42.50"}
    cost_basis_override: Optional[Currency] = Field(
        default=None,
        description="Frozen PER-UNIT cost basis (WAC per single unit) for TRANSFER_IN. Multiplied by quantity to get the total. Object {code, amount}.",
    )

    # WAC computation mode — session-only instruction (not persisted in DB).
    # "auto": backend computes WAC and writes cost_basis_override at commit.
    # "auto-detail": same + returns qualifying_txs, asset_price in validate response.
    # "manual": use cost_basis_override as-is.
    # None: not applicable (BUY, SELL, etc.)
    cost_basis_mode: Literal["auto", "auto-detail", "manual"] | None = Field(
        default=None,
        description="'auto': backend computes WAC; 'auto-detail': + qualifying details; " "'manual': use cost_basis_override; None: not applicable.",
    )

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
    def validate_transaction_rules(self) -> TXCreateItem:  # noqa: C901 — flat per-rule error collection
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

        # Rules 5-12 (per-type business rules on the final state) are shared with
        # the UPDATE merge path via a module-level pure function, so CREATE and
        # UPDATE enforce identical semantics. Rules 1-4 (pairing) and field-level
        # positivity above remain create-only concerns.
        errors.extend(
            validate_transaction_business_rules(
                tx_type=self.type,
                asset_id=self.asset_id,
                quantity=self.quantity,
                cash=self.cash,
                asset_event_id=self.asset_event_id,
                cost_basis_mode=self.cost_basis_mode,
            )
        )

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


class TXReadItem(StrictModel):
    """
    DTO for reading a transaction from the API.

    This is the response format for GET operations.
    Uses Currency for cash representation.

    Note on linked transactions:
    With bidirectional DEFERRABLE FK, related_transaction_id is populated
    on BOTH transactions in a pair (A->B and B->A), so no separate
    linked_transaction_id field is needed.
    """

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


class TXUpdateItem(StrictModel):
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
    cost_basis_override: Optional[Currency] = Field(
        default=None,
        description="Frozen cost basis for TRANSFER_IN. Object {code, amount}.",
    )

    # WAC computation mode — session-only instruction (not persisted in DB).
    cost_basis_mode: Literal["auto", "auto-detail", "manual"] | None = Field(
        default=None,
        description="'auto': backend computes WAC at commit; 'auto-detail': + qualifying details; " "'manual': use cost_basis_override; None: leave unchanged.",
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

    @model_validator(mode="after")
    def _business_rules(self) -> TXUpdateItem:
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


class TXQueryParams(StrictModel):
    """
    Query parameters for filtering transactions.

    Used by GET /api/v1/transactions endpoint.
    """

    broker_id: Optional[int] = Field(default=None, gt=0, description="Filter by broker")
    asset_id: Optional[int] = Field(default=None, gt=0, description="Filter by asset")
    asset_event_id: Optional[int] = Field(default=None, gt=0, description="Only transactions linked to this asset event (reverse lookup)")
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

    limit: Optional[int] = Field(default=None, ge=1, le=10000, description="Max results (None = no limit)")
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


class TXDeleteItem(StrictModel):
    """Single transaction ID to delete."""

    id: int = Field(..., gt=0, description="Transaction ID to delete")
