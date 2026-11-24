"""The income of a transaction: what it earns, in the currency it earns it in.

One rule for every reader of income (summary, positions, history, Yield on Cost, lots analysis), so cash income and
income in kind are never told apart by hand:

* DIVIDEND and INTEREST earn their cash ``amount``, in their ``currency``;
* REWARD (project 79, issue #90) earns the value of the units it brings in, ``cost_basis_override × quantity`` in
  ``cost_basis_currency``: it counts as a dividend of that value reinvested the same day in a buy, so no cash moves and
  the value is both the income and the cost of the lot it opens.

A REWARD without a value has unknown income (``None``), never zero: its lot starts at no known cost, which the
data-quality report names (``MISSING_COST_BASIS``).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

#: Income paid in cash: the amount is the income.
CASH_INCOME_TYPES: frozenset[str] = frozenset({"DIVIDEND", "INTEREST"})
#: Income received in units of an asset: no cash moves, the value of the units is the income.
IN_KIND_INCOME_TYPES: frozenset[str] = frozenset({"REWARD"})
#: Every type that earns income.
INCOME_TYPES: frozenset[str] = CASH_INCOME_TYPES | IN_KIND_INCOME_TYPES


@dataclass(frozen=True, slots=True)
class IncomeValue:
    """The income of one transaction in its own currency, signed as stored (a legacy negative correction stays)."""

    amount: Decimal
    currency: str


def transaction_type_code(tx: Any) -> str:
    """The type of ``tx`` as its code (``"REWARD"``), whether stored as the enum or as a string."""
    return str(getattr(tx.type, "value", tx.type))


def is_income(tx: Any) -> bool:
    """Whether ``tx`` is of a type that earns income (:data:`INCOME_TYPES`)."""
    return transaction_type_code(tx) in INCOME_TYPES


def is_in_kind_income(tx: Any) -> bool:
    """Whether ``tx`` earns income in units of an asset, with no cash (:data:`IN_KIND_INCOME_TYPES`)."""
    return transaction_type_code(tx) in IN_KIND_INCOME_TYPES


def income_value(tx: Any, *, default_currency: str | None = None) -> IncomeValue | None:
    """The income ``tx`` earns, in its own currency; None when it earns none or its value is unknown.

    A cash income reads ``amount`` and ``currency`` (``default_currency`` when the row has none, as the lots analysis
    reads an income in the asset's currency). A REWARD reads ``cost_basis_override × quantity`` in
    ``cost_basis_currency`` (``default_currency`` when the row has none); without a cost basis or a quantity its value
    is unknown: None, never zero. Any other type earns no income: None.
    """
    code = transaction_type_code(tx)
    if code in CASH_INCOME_TYPES:
        currency = tx.currency or default_currency
        if tx.amount is None or not currency:
            return None
        return IncomeValue(amount=tx.amount, currency=currency)
    if code in IN_KIND_INCOME_TYPES:
        currency = tx.cost_basis_currency or default_currency
        if tx.cost_basis_override is None or tx.quantity is None or not currency:
            return None
        return IncomeValue(amount=tx.cost_basis_override * tx.quantity, currency=currency)
    return None
