"""
Pair promotion: the request and response of ``POST /transactions/transfers/promote``, and the promote-suggest
input, candidate and response.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Dict, List, Literal, Optional

from pydantic import Field, field_validator

from backend.app.db.models import TransactionType
from backend.app.schemas.common import (
    IsoCurrencyAmount,
    SafeDecimal,
    StrictModel,
    check_decimal_exponent,
)

# =============================================================================
# TRANSFER PROMOTION (Block H.4)
# =============================================================================


class TXTransferPromoteRequest(StrictModel):
    """
    Atomically promote a DEPOSIT/WITHDRAWAL pair into a TRANSFER (with asset)
    or FX_CONVERSION (cross-currency, same broker).

    Cannot be done via PATCH because `type` is immutable on existing rows —
    the endpoint deletes the original pair and creates a new one within a
    single session.
    """

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
    # destination item; if None the service will not set it. Refused on an
    # FX_CONVERSION, whose cash legs take none (N78, W-B72).
    # Object {code, amount} — e.g. {"code": "EUR", "amount": "42.50"}
    cost_basis_override: Optional[IsoCurrencyAmount] = None

    @field_validator("quantity")
    @classmethod
    def _quantity_exponent(cls, v: Optional[SafeDecimal]) -> Optional[SafeDecimal]:
        """Refuse a quantity whose exponent is past ±100 (R13-SEC7-3): a 422 before the promotion does any work."""
        return None if v is None else check_decimal_exponent(v)


class TXTransferPromoteResponse(StrictModel):
    """Outcome of /transactions/transfers/promote."""

    rolled_back: bool
    new_from_tx_id: Optional[int] = None
    new_to_tx_id: Optional[int] = None
    errors: List[str] = Field(default_factory=list)


# =============================================================================
# PROMOTE-SUGGEST (bulk candidate search)
# =============================================================================


class TXPromoteSuggestInput(StrictModel):
    """Single TX to find promote candidates for. id < 0 = fake (unsaved)."""

    id: int = Field(..., description="Real ID (>0) or fake ID (<0) for unsaved TX")
    type: TransactionType
    broker_id: int = Field(..., gt=0)
    date: date_type
    currency: Optional[str] = None
    asset_id: Optional[int] = None
    amount: Optional[SafeDecimal] = None
    quantity: Optional[SafeDecimal] = None
    asset_event_id: Optional[int] = Field(
        default=None,
        ge=0,
        description="Asset event the row is linked to; None or 0 = not linked. A linked row gets no candidate from a rule whose target type does not accept an event link.",
    )


class TXPromoteSuggestCandidate(StrictModel):
    """A DB transaction that could be promoted with the input TX."""

    id: int = Field(..., gt=0)
    broker_id: int
    date: date_type
    type: str
    currency: Optional[str] = None
    asset_id: Optional[int] = None


class TXPromoteSuggestResponse(StrictModel):
    """Map of input id/fakeId → list of DB candidates."""

    results: Dict[int, List[TXPromoteSuggestCandidate]]
