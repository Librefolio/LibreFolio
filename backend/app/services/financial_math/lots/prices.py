"""Price lookups of the lots analysis: the daily market prices of an asset, and the reference price of a lot at its opening."""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal
from typing import Sequence

from backend.app.db.models import PriceHistory
from backend.app.schemas.portfolio import (
    ReferencePriceSource,
)
from backend.app.services.financial_math.fifo.models import FifoLot


@dataclass(frozen=True, slots=True)
class PricePoint:
    price: Decimal
    currency: str
    resolved_date: date_type
    source: ReferencePriceSource


class PriceHistoryLookup:
    def __init__(self, prices: Sequence[PriceHistory]) -> None:
        self._rows = sorted((row for row in prices if row.close is not None), key=lambda row: row.date)
        self._dates = [row.date for row in self._rows]

    def resolve(self, query_date: date_type) -> PricePoint | None:
        if not self._rows:
            return None
        idx = bisect.bisect_right(self._dates, query_date) - 1
        if idx < 0:
            return None
        row = self._rows[idx]
        return PricePoint(
            price=row.close if row.close is not None else Decimal("0"),
            currency=row.currency,
            resolved_date=row.date,
            source="exact" if row.date == query_date else "fallback",
        )

    def latest(self) -> PricePoint | None:
        if not self._rows:
            return None
        last = self._rows[-1]
        return PricePoint(price=last.close if last.close is not None else Decimal("0"), currency=last.currency, resolved_date=last.date, source="exact")


def opening_reference_price(
    lot: FifoLot,
    price_lookup: PriceHistoryLookup,
    quote_base_quantity: int = 1,
) -> tuple[Decimal | None, str | None, date_type, ReferencePriceSource | None]:
    if lot.reference_unit_price is not None:
        resolved_reference = price_lookup.resolve(lot.opening_date)
        if resolved_reference is None:
            return None, None, lot.opening_date, lot.reference_price_source
        return lot.reference_unit_price, resolved_reference.currency, resolved_reference.resolved_date, lot.reference_price_source
    # No market quote at the opening date (e.g. a bond bought at emission, before it started
    # trading) → fall back to the lot's own buy price. opening_unit_price is per-single-unit
    # (cost / raw quantity), whereas market_price is quoted per quote_base_quantity units, so
    # scale it up to keep relative_return (= market_price / reference − 1) on one axis; otherwise
    # a qbq=100 bond reports ~9687% instead of ~−2%. No-op for qbq=1 (stocks). The resolved
    # branches above already return a per-quote market reference, so they need no scaling.
    scale = quote_base_quantity if quote_base_quantity > 0 else 1
    return lot.opening_unit_price * scale, lot.currency, lot.opening_date, "exact"
