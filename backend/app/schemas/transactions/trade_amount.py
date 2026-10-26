"""
Trade amount (``POST /transactions/trade-amount``): the request and the answer of the form's «Total amount / Unit price».

A BUY or SELL stores a quantity and an amount; the unit price is only a way of typing the amount. The form sends the
value the user typed and gets the other one back, calculated in ``financial_math/trade_amount.py``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator
from pydantic_core import PydanticCustomError

from backend.app.db.models import PriceHistory, Transaction
from backend.app.db.precision import decimal_limit_issue
from backend.app.schemas.common import StrictModel

TradeAmountMode = Literal["price_to_amount", "amount_to_price"]


class TXTradeAmountRequest(StrictModel):
    """What the user typed (``value``) for ``quantity`` units of ``asset_id``; ``mode`` says which value it is.

    ``price_to_amount``: ``value`` is the unit price, the answer is the amount. ``amount_to_price``: ``value`` is the
    amount, the answer is the unit price. Both are held to the input limits of the column that keeps them (quantity
    10 decimals, amount 6, price 12, 15 significant digits): a typed value past them is refused, never rounded.
    """

    asset_id: int = Field(..., gt=0)
    quantity: Decimal
    mode: TradeAmountMode
    value: Decimal

    @model_validator(mode="after")
    def _check_limits(self) -> TXTradeAmountRequest:
        if self.quantity == 0:
            raise PydanticCustomError("qtyNonzero", "quantity must not be zero")
        checked = [("quantity", self.quantity, Transaction, "quantity")]
        checked.append(("value", self.value, PriceHistory if self.mode == "price_to_amount" else Transaction, "close" if self.mode == "price_to_amount" else "amount"))
        for field, number, model, column in checked:
            issue = decimal_limit_issue(number, model, column)
            if issue is not None:
                code, limit = issue
                raise PydanticCustomError(code, "{field} is past the limits of its column", {"field": field, "limit": limit})
        return self


class TXTradeAmountResponse(StrictModel):
    """The calculated value as a plain decimal (no exponent, no trailing zeros), and the quote base the asset uses."""

    mode: TradeAmountMode
    result: str
    quote_base_quantity: int
