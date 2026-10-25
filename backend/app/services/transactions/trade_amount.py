"""
The form's «Total amount / Unit price» (``POST /transactions/trade-amount``): reads the asset's quote base and asks
``financial_math/trade_amount.py`` for the other value. No financial arithmetic of its own.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, PriceHistory, Transaction
from backend.app.db.precision import get_model_column_precision
from backend.app.schemas.transactions.trade_amount import TXTradeAmountRequest, TXTradeAmountResponse
from backend.app.services.financial_math.trade_amount import amount_from_unit_price, unit_price_from_amount
from backend.app.services.financial_math.valuation import normalize_quote_base_quantity


def _plain(value: Decimal) -> str:
    """A decimal as plain text, with no exponent and no trailing zeros in the fraction (``1000``, ``83.4``)."""
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


async def convert_trade_amount(session: AsyncSession, request: TXTradeAmountRequest) -> Optional[TXTradeAmountResponse]:
    """The other value of the pair, or ``None`` when the asset does not exist.

    The result is rounded half-even to the scale of the column that keeps it: the amount's (``Transaction.amount``) or
    the price's (``PriceHistory.close``), so what the form shows is what would be stored.
    """
    asset = await session.get(Asset, request.asset_id)
    if asset is None:
        return None
    base = normalize_quote_base_quantity(asset.quote_base_quantity)
    if request.mode == "price_to_amount":
        scale = get_model_column_precision(Transaction, "amount")[1]
        result = amount_from_unit_price(request.quantity, request.value, base, scale=scale)
    else:
        scale = get_model_column_precision(PriceHistory, "close")[1]
        result = unit_price_from_amount(request.quantity, request.value, base, scale=scale)
    return TXTradeAmountResponse(mode=request.mode, result=_plain(result), quote_base_quantity=base)
