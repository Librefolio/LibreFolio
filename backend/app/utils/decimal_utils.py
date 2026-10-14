"""
Decimal parsing for LibreFolio.

A leaf helper: the truncation to the database precision lives in ``backend.app.db.precision``.
"""

from decimal import Decimal
from typing import Optional


def parse_decimal_value(value) -> Optional[Decimal]:
    """
    Convert input to Decimal safely.

    Args:
        value: Input value (Decimal, int, float, str, or None)

    Returns:
        Decimal or None
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except Exception:
        return None
