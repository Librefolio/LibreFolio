"""
Transaction type metadata: the field modes and pair-form rules of each transaction type (``TX_TYPE_METADATA``),
the type swap groups, the rules read from the table (``cost_basis_required``, ``cost_basis_allowed``, and for rules
5-11 ``get_tx_type_metadata``, ``event_compatible``, ``event_compatible_types``), the event type metadata, and the ``GET /transactions/types``
response.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field

from backend.app.db.models import TransactionType
from backend.app.schemas.common import (
    StrictModel,
)
from backend.app.schemas.transactions.batch import VALIDATION_CODE_METADATA, TXValidationCodeInfo

# =============================================================================
# TRANSACTION TYPE METADATA
# =============================================================================

# Sign types for validation — semantic enum used by both quantity and cash fields.
# All values lowercase so the frontend can use them as-is without mapping.
SignType = Literal["positive", "negative", "zero", "nonzero", "free"]

# Field mode — controls whether a field is shown / required / hidden.
# Shared by asset_mode, cash_mode, quantity_mode.
FieldMode = Literal["required", "optional", "forbidden"]

# Cost basis field mode — specific to cost_basis_override applicability.
# "forbidden": field not used for this type/side.
# "optional": can have cost_basis but not mandatory.
# "required_qty_pos": required when quantity > 0 (receiver side of TRANSFER, positive ADJUSTMENT).
CostBasisFieldMode = Literal["forbidden", "optional", "required_qty_pos"]

# Pair form layout — controls the dual-transaction form layout in the frontend.
# None = standard single form, otherwise specifies which dual form to show.
PairFormLayout = Literal["fx", "transfer_asset", "transfer_cash"]

# Field constraint relation — how a field relates between the two halves of a pair.
PairFieldRelation = Literal["equal", "opposite", "different"]


class PairFieldConstraint(StrictModel):
    """How a field relates between the two halves of a pair."""

    field: Literal["broker_id", "asset_id", "cash_currency", "cash_amount", "quantity"] = Field(..., description="Transaction field name")
    relation: PairFieldRelation = Field(
        ...,
        description="Constraint: equal (same value), opposite (negated), different (must differ)",
    )


class SplitMeta(StrictModel):
    """How a paired type splits into 2 standalone types."""

    from_type: str = Field(..., description="Type for 'from' half (negative/source side)")
    to_type: str = Field(..., description="Type for 'to' half (positive/destination side)")


class PromoteRule(StrictModel):
    """How 2 standalone types can be promoted to this paired type."""

    type_a: str = Field(..., description="First standalone type")
    type_b: str = Field(..., description="Second standalone type")
    field_constraints: list[PairFieldConstraint] = Field(..., description="Validation rules for the pair")


class TXTypeMetadata(StrictModel):
    """
    Metadata about a transaction type.

    Used by GET /api/v1/transactions/types endpoint.
    Frontend uses these values directly (all lowercase, no mapping needed).
    """

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

    # Whether this type can be linked to an AssetEvent (rule 9 of validate_transaction_business_rules)
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

    # Cost basis override applicability — tells frontend whether to show/require the field.
    cost_basis_mode: CostBasisFieldMode = Field(
        "forbidden",
        description="Whether cost_basis_override is applicable. " "'forbidden': field not used; " "'required_qty_pos': required when quantity > 0; " "'optional': can have cost_basis but not mandatory.",
    )

    # For paired types: per-side cost_basis rule. Index 0 = 'from' (sender, qty<0), index 1 = 'to' (receiver, qty>0).
    # Overrides cost_basis_mode when present. None for standalone types.
    cost_basis_pair: list[CostBasisFieldMode] | None = Field(
        None,
        description="[from_side, to_side] cost_basis rules for paired types. " "Index 0 = 'Da' (sender, qty<0), index 1 = 'A' (receiver, qty>0). " "Overrides cost_basis_mode when present. None for standalone types.",
    )


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


# Precomputed metadata for all transaction types.
# swap_group is auto-populated from SWAP_GROUPS via _swap_group_codes().
def _build_tx_type_metadata() -> dict[TransactionType, TXTypeMetadata]:
    """Build metadata dict with auto-populated swap_group field."""
    raw: dict[TransactionType, dict] = {
        TransactionType.BUY: {
            "code": "BUY",
            "name": "Buy",
            "description": "Purchase asset with cash",
            "icon_slug": "buy",
            "doc_slug": "buy-sell",
            "asset_mode": "required",
            "cash_mode": "required",
            "quantity_mode": "required",
            "requires_link": False,
            "quantity_sign": "positive",
            "cash_sign": "negative",
            "event_compatible": False,
        },
        TransactionType.SELL: {
            "code": "SELL",
            "name": "Sell",
            "description": "Sell asset for cash",
            "icon_slug": "sell",
            "doc_slug": "buy-sell",
            "asset_mode": "required",
            "cash_mode": "required",
            "quantity_mode": "required",
            "requires_link": False,
            "quantity_sign": "negative",
            "cash_sign": "positive",
            "event_compatible": False,
        },
        TransactionType.DIVIDEND: {
            "code": "DIVIDEND",
            "name": "Dividend",
            "description": "Dividend payment received",
            "icon_slug": "dividend",
            "doc_slug": "dividend",
            "asset_mode": "required",
            "cash_mode": "required",
            "quantity_mode": "forbidden",
            "requires_link": False,
            "quantity_sign": "zero",
            "cash_sign": "positive",
            "event_compatible": True,
        },
        TransactionType.INTEREST: {
            "code": "INTEREST",
            "name": "Interest",
            "description": "Interest payment (bond or deposit)",
            "icon_slug": "interest",
            "doc_slug": "interest",
            "asset_mode": "optional",
            "cash_mode": "required",
            "quantity_mode": "forbidden",
            "requires_link": False,
            "quantity_sign": "zero",
            "cash_sign": "positive",
            "event_compatible": True,
        },
        TransactionType.DEPOSIT: {
            "code": "DEPOSIT",
            "name": "Deposit",
            "description": "Add cash to broker account",
            "icon_slug": "deposit",
            "doc_slug": "deposit-withdrawal",
            "asset_mode": "forbidden",
            "cash_mode": "required",
            "quantity_mode": "forbidden",
            "requires_link": False,
            "quantity_sign": "zero",
            "cash_sign": "positive",
            "event_compatible": False,
        },
        TransactionType.WITHDRAWAL: {
            "code": "WITHDRAWAL",
            "name": "Withdrawal",
            "description": "Remove cash from broker account",
            "icon_slug": "withdrawal",
            "doc_slug": "deposit-withdrawal",
            "asset_mode": "forbidden",
            "cash_mode": "required",
            "quantity_mode": "forbidden",
            "requires_link": False,
            "quantity_sign": "zero",
            "cash_sign": "negative",
            "event_compatible": False,
        },
        TransactionType.FEE: {
            "code": "FEE",
            "name": "Fee",
            "description": "Fee or commission (trading or account)",
            "icon_slug": "fee",
            "doc_slug": "fee",
            "asset_mode": "optional",
            "cash_mode": "required",
            "quantity_mode": "forbidden",
            "requires_link": False,
            "quantity_sign": "zero",
            "cash_sign": "negative",
            "event_compatible": False,
        },
        TransactionType.TAX: {
            "code": "TAX",
            "name": "Tax",
            "description": "Tax payment (capital gain or stamp duty)",
            "icon_slug": "tax",
            "doc_slug": "fee",
            "asset_mode": "optional",
            "cash_mode": "required",
            "quantity_mode": "forbidden",
            "requires_link": False,
            "quantity_sign": "zero",
            "cash_sign": "negative",
            "event_compatible": False,
        },
        TransactionType.TRANSFER: {
            "code": "TRANSFER",
            "name": "Asset Transfer",
            "description": "Asset transfer between brokers",
            "icon_slug": "transfer",
            "doc_slug": "transfer",
            "asset_mode": "required",
            "cash_mode": "forbidden",
            "quantity_mode": "required",
            "requires_link": True,
            "quantity_sign": "nonzero",
            "cash_sign": "zero",
            "event_compatible": False,
            "pair_form_layout": "transfer_asset",
            "split_into": SplitMeta(from_type="ADJUSTMENT", to_type="ADJUSTMENT"),
            "promote_from": [
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
            "pair_field_constraints": [
                PairFieldConstraint(field="asset_id", relation="equal"),
                PairFieldConstraint(field="broker_id", relation="different"),
                PairFieldConstraint(field="quantity", relation="opposite"),
            ],
            "cost_basis_pair": ["forbidden", "required_qty_pos"],
        },
        TransactionType.FX_CONVERSION: {
            "code": "FX_CONVERSION",
            "name": "FX Conversion",
            "description": "Currency exchange",
            "icon_slug": "fx-conversion",
            "doc_slug": "fx-conversion",
            "asset_mode": "forbidden",
            "cash_mode": "required",
            "quantity_mode": "forbidden",
            "requires_link": True,
            "quantity_sign": "zero",
            "cash_sign": "nonzero",
            "event_compatible": False,
            "pair_form_layout": "fx",
            "split_into": SplitMeta(from_type="WITHDRAWAL", to_type="DEPOSIT"),
            "promote_from": [
                PromoteRule(
                    type_a="WITHDRAWAL",
                    type_b="DEPOSIT",
                    field_constraints=[
                        PairFieldConstraint(field="cash_currency", relation="different"),
                        PairFieldConstraint(field="broker_id", relation="equal"),
                    ],
                ),
            ],
            "pair_field_constraints": [
                PairFieldConstraint(field="cash_currency", relation="different"),
                PairFieldConstraint(field="broker_id", relation="equal"),
            ],
        },
        TransactionType.ADJUSTMENT: {
            "code": "ADJUSTMENT",
            "name": "Adjustment",
            "description": "Manual quantity correction (splits, gifts)",
            "icon_slug": "adjustment",
            "doc_slug": "adjustment",
            "asset_mode": "required",
            "cash_mode": "forbidden",
            "quantity_mode": "required",
            "requires_link": False,
            "quantity_sign": "nonzero",
            "cash_sign": "zero",
            "event_compatible": True,
            "cost_basis_mode": "required_qty_pos",
        },
        TransactionType.CASH_TRANSFER: {
            "code": "CASH_TRANSFER",
            "name": "Cash Transfer",
            "description": "Wire transfer / bonifico between brokers",
            "icon_slug": "cash-transfer",
            "doc_slug": "cash-transfer",
            "asset_mode": "forbidden",
            "cash_mode": "required",
            "quantity_mode": "forbidden",
            "requires_link": True,
            "quantity_sign": "zero",
            "cash_sign": "nonzero",
            "event_compatible": False,
            "pair_form_layout": "transfer_cash",
            "split_into": SplitMeta(from_type="WITHDRAWAL", to_type="DEPOSIT"),
            "promote_from": [
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
            "pair_field_constraints": [
                PairFieldConstraint(field="cash_currency", relation="equal"),
                PairFieldConstraint(field="broker_id", relation="different"),
                PairFieldConstraint(field="cash_amount", relation="opposite"),
            ],
        },
    }
    # Auto-populate swap_group for every type
    result: dict[TransactionType, TXTypeMetadata] = {}
    for tx_type, kwargs in raw.items():
        kwargs["swap_group"] = _swap_group_codes(tx_type)
        result[tx_type] = TXTypeMetadata(**kwargs)
    return result


TX_TYPE_METADATA: dict[TransactionType, TXTypeMetadata] = _build_tx_type_metadata()


def _cost_basis_rule(tx_type: TransactionType, quantity: Decimal) -> CostBasisFieldMode | None:
    """The cost-basis rule ``TX_TYPE_METADATA`` gives ``tx_type`` on the side ``quantity`` puts it; ``None`` for an
    unknown type.

    A paired type reads the rule of its side — ``cost_basis_pair[0]`` for the sending one (quantity not above zero),
    ``[1]`` for the receiving one — and any other type its ``cost_basis_mode``. The table is read at call time.
    """
    meta = TX_TYPE_METADATA.get(tx_type)
    if meta is None:
        return None
    return meta.cost_basis_pair[1 if quantity > 0 else 0] if meta.cost_basis_pair else meta.cost_basis_mode


def cost_basis_required(tx_type: TransactionType, quantity: Decimal | None) -> bool:
    """Whether a transaction of ``tx_type`` with ``quantity`` needs a cost basis, as ``TX_TYPE_METADATA`` says.

    ``required_qty_pos``, the rule of its side (``_cost_basis_rule``), asks for a cost basis when the quantity is above
    zero. The frontend reads the same table (``GET /transactions/types``) to decide where a cost basis may be sent.
    """
    if quantity is None:
        return False
    return _cost_basis_rule(tx_type, quantity) == "required_qty_pos" and quantity > 0


def cost_basis_allowed(tx_type: TransactionType, quantity: Decimal) -> bool:
    """Whether a transaction of ``tx_type`` with ``quantity`` may carry a cost basis, so a ``cost_basis_mode`` (rule 12).

    Allowed when the rule of its side (``_cost_basis_rule``) is not ``forbidden``, a ``required_qty_pos`` one only with
    a quantity above zero: the test the frontend makes as ``cbAllowed`` (``features/transactions/txPayloadHelpers.ts``).
    """
    rule = _cost_basis_rule(tx_type, quantity)
    return rule is not None and rule != "forbidden" and not (rule == "required_qty_pos" and quantity <= 0)


def get_tx_type_metadata(tx_type: TransactionType) -> TXTypeMetadata | None:
    """The ``TX_TYPE_METADATA`` row of ``tx_type``, read at call time; ``None`` for a type the table lacks.

    Rules 5-11 of ``validate_transaction_business_rules`` read it (W-B36).
    """
    return TX_TYPE_METADATA.get(tx_type)


def event_compatible(tx_type: TransactionType) -> bool:
    """Whether ``TX_TYPE_METADATA`` lets a transaction of ``tx_type`` link an asset event (rule 9, event suggestions)."""
    meta = TX_TYPE_METADATA.get(tx_type)
    return meta is not None and meta.event_compatible


def event_compatible_types() -> list[str]:
    """The codes of the types ``TX_TYPE_METADATA`` lets link an asset event, sorted: rule 9's ``allowed``."""
    return sorted(tx_type.value for tx_type, meta in TX_TYPE_METADATA.items() if meta.event_compatible)


class EventTypeMetadata(StrictModel):
    """Metadata about an asset event type for frontend rendering."""

    code: str = Field(..., description="Enum code (e.g., 'DIVIDEND')")
    name: str = Field(..., description="Display name")
    emoji: str = Field(..., description="Emoji icon for rendering")
    compatible_tx_types: list[str] = Field(..., description="Transaction types that can link to this event type")


class TXTypesResponse(StrictModel):
    """Combined response for GET /transactions/types."""

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
