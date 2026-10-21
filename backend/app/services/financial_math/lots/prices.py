"""Price lookups of the lots analysis, from the home's daily price series: the reference price of a lot at its opening, and the days valued at cost."""

from __future__ import annotations

import bisect
from datetime import date as date_type
from decimal import Decimal
from typing import Sequence

from backend.app.schemas.portfolio import (
    ReferencePriceSource,
)
from backend.app.services.financial_math.fifo.models import FifoLot
from backend.app.services.financial_math.price_marks import AssetPriceSeries


def opening_reference_price(
    lot: FifoLot,
    price_series: AssetPriceSeries,
    quote_base_quantity: int = 1,
) -> tuple[Decimal | None, str | None, date_type, ReferencePriceSource | None]:
    """The reference price of ``lot`` at its opening: ``(price, currency, opening date, source)``.

    A lot the FIFO engine gave a market reference (one opened by an ADJUSTMENT, from the home's daily mark on its
    opening day: a market quote, or a BUY/SELL price, carried forward) keeps that price, in the currency of that mark.
    The date is always the opening date, so the reference converts at the rate of the day it stands for (P21), never
    at the date of an older observation it was carried from.
    """
    if lot.reference_unit_price is not None:
        mark = price_series.resolve(lot.opening_date)
        if mark.is_missing:
            return None, None, lot.opening_date, lot.reference_price_source
        return lot.reference_unit_price, mark.currency, lot.opening_date, lot.reference_price_source
    # No market reference — a lot opened by a BUY, or by an ADJUSTMENT with no mark on or before its
    # opening (e.g. a bond received before it started trading) → fall back to the lot's own price.
    # opening_unit_price is per-single-unit (cost / raw quantity), whereas market_price is quoted per
    # quote_base_quantity units, so scale it up to keep relative_return (= market_price / reference − 1)
    # on one axis; otherwise a qbq=100 bond reports ~9687% instead of ~−2%. No-op for qbq=1 (stocks).
    # The resolved branch above already returns a per-quote market reference, so it needs no scaling.
    scale = quote_base_quantity if quote_base_quantity > 0 else 1
    return lot.opening_unit_price * scale, lot.currency, lot.opening_date, "exact"


def last_day_without_observation(price_series: AssetPriceSeries, days: Sequence[date_type]) -> date_type | None:
    """The last of the ascending ``days`` with no observation on or before it; None when the first already has one.

    Such a day has no price at all — no quote and no BUY or SELL, on it or before it — so the lots value an open lot
    at its cost there, as the Dashboard values a holding (J-17). They are always the days before the asset's first
    observation: a later day resolves to that observation, carried forward. So the days with an observation are a tail
    of ``days``, found by bisection (L1a): a few lookups, whatever the length of the history.
    """
    first_observed = bisect.bisect_left(days, True, key=lambda day: not price_series.resolve(day).is_missing)
    return days[first_observed - 1] if first_observed else None
