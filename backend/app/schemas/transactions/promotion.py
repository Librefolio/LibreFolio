"""
Pair promotion: the promote-suggest input, candidate and response.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import Dict, List, Optional

from pydantic import Field

from backend.app.db.models import TransactionType
from backend.app.schemas.common import (
    SafeDecimal,
    StrictModel,
)

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
