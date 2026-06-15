"""
Financial valuation helpers.

Pure math helpers shared across portfolio, broker, and other valuation paths.
"""

from __future__ import annotations

from decimal import Decimal


def normalize_quote_base_quantity(quote_base_quantity: int | None) -> int:
    """Return a safe positive quote base quantity."""
    if quote_base_quantity is None or quote_base_quantity <= 0:
        return 1
    return quote_base_quantity


def compute_holding_value(
    qty: Decimal,
    raw_price: Decimal,
    quote_base_quantity: int | None,
) -> Decimal:
    """Compute market value from raw market quote and quote base quantity."""
    base = Decimal(normalize_quote_base_quantity(quote_base_quantity))
    return (qty / base) * raw_price
