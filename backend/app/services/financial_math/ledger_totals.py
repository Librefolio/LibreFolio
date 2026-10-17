"""Control totals of the transaction ledger: the cash of every broker in each currency and the quantity of every
position, read from the rows alone — no price, rate, cost, date or setting.

A backup writes them into its manifest; the check of a restore recomputes them on the archive's copy, once upgraded to
the app's schema, and compares them before the restore is confirmed. A difference means rows lost, added or altered in
broker, asset, currency, amount or quantity; it is reported, never a refusal, since a migration may correct data. So
that two readings of the same ledger always agree, they are:

* cash: every row's amount in the currency it was recorded in, per broker — the native balances of ``native_cash``;
* quantity: every row's quantity per broker and asset, by the portfolio engine's rule — every row with an asset and a
  quantity, whatever its type: a split and a transfer are rows too;
* the whole instance, every broker at 100 %: no user, share, date, setting or cache;
* independent of the row type: reclassifying rows (a TRANSFER half into an ADJUSTMENT, a CASH_TRANSFER half into a
  DEPOSIT or a WITHDRAWAL) changes nothing. The cost basis is left out: it depends on rates and on the average-cost
  and FIFO rules;
* exact: summed in Python, never with ``SUM`` in SQL (a Numeric on SQLite goes through a float), in a decimal context
  that raises instead of rounding; quantities below the Dashboard's dust threshold are kept;
* canonical: a line that sums to zero is left out (an absent line is zero), the others are sorted, and every amount is
  written in plain decimal notation without trailing zeros, never «-0». ``from_json`` reads back only that text: an
  optional «-», at most 60 digits before the point and 60 after it, the precision of the exact context. A manifest
  written by hand therefore cannot make it expand an exponent or an unbounded number (J-27). The round trip holds for
  every total within that bound, and every ledger the database can hold stays within it: amounts are RealDecimal(18, 6),
  quantities RealDecimal(22, 10).

``CONTROL_TOTALS_VERSION`` names the method: totals written by another version are not comparable.
"""

from __future__ import annotations

import decimal
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date as date_type
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from backend.app.db.models import Transaction
from backend.app.services.financial_math.native_cash import cash_movement_from_transaction, native_balances

CONTROL_TOTALS_VERSION = 1

# Rows per query: keyset blocks on the primary key keep the read linear and its memory bounded.
_BLOCK_SIZE = 5000

# Sums of RealDecimal(18, 6) amounts never need this many digits; a total that would is an error, not a rounding.
_EXACT = decimal.Context(prec=60, traps=[decimal.InvalidOperation, decimal.DivisionByZero, decimal.Overflow, decimal.Inexact])

# An amount as ``to_json`` writes it, the only text ``from_json`` reads: an optional minus, then ASCII digits — at most
# the exact context's precision before the point and as many after it. ``Decimal`` would also take an exponent («1E+9»),
# a «+», spaces, «_» and other scripts' digits; an exponent would then be written out in full (J-27).
_PLAIN_AMOUNT = re.compile(rf"-?[0-9]{{1,{_EXACT.prec}}}(?:\.[0-9]{{1,{_EXACT.prec}}})?")

_ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class ControlTotals:
    """The control totals of a ledger: cash per (broker, currency) and quantity per (broker, asset), without zero lines."""

    version: int
    cash: tuple[tuple[int, str, Decimal], ...]
    quantities: tuple[tuple[int, int, Decimal], ...]

    def to_json(self) -> dict[str, Any]:
        """A JSON-ready dict: the version, then the lines in order, every amount as canonical decimal text."""
        return {
            "version": self.version,
            "cash": [{"broker_id": broker_id, "currency": currency, "balance": _canonical_text(balance)} for broker_id, currency, balance in self.cash],
            "quantities": [{"broker_id": broker_id, "asset_id": asset_id, "quantity": _canonical_text(quantity)} for broker_id, asset_id, quantity in self.quantities],
        }

    @classmethod
    def from_json(cls, data: Any) -> ControlTotals:
        """The totals ``to_json`` wrote. ValueError for another version or a malformed document."""
        if not isinstance(data, Mapping):
            raise ValueError("Control totals must be a JSON object.")
        version = data.get("version")
        if type(version) is not int or version != CONTROL_TOTALS_VERSION:
            raise ValueError(f"Control totals of version {version!r} are not comparable with version {CONTROL_TOTALS_VERSION}.")
        try:
            cash = tuple((_as_id(row["broker_id"]), _as_currency(row["currency"]), _as_amount(row["balance"])) for row in data["cash"])
            quantities = tuple((_as_id(row["broker_id"]), _as_id(row["asset_id"]), _as_amount(row["quantity"])) for row in data["quantities"])
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Malformed control totals: {exc!r}") from exc
        return cls(version=CONTROL_TOTALS_VERSION, cash=cash, quantities=quantities)


def position_quantities(transactions: Iterable[Any], as_of: date_type | None = None) -> dict[int, dict[int, Decimal]]:
    """The quantity of every position, per broker and asset, on ``as_of`` (every row when None).

    The portfolio engine's rule: every row with an asset and a non-zero quantity counts, whatever its type. The whole
    broker, no share. Like ``native_balances``, a position whose rows cancel out keeps its line at zero.
    """
    result: dict[int, dict[int, Decimal]] = {}
    for tx in transactions:
        quantity = tx.quantity
        if tx.asset_id is None or not quantity:
            continue
        if as_of is not None and tx.date > as_of:
            continue
        by_asset = result.setdefault(tx.broker_id, {})
        by_asset[tx.asset_id] = by_asset.get(tx.asset_id, _ZERO) + quantity
    return result


def control_totals(transactions: Iterable[Any]) -> ControlTotals:
    """The control totals of ``transactions``: native cash per (broker, currency), quantity per (broker, asset)."""
    accumulator = _LedgerAccumulator()
    accumulator.add(transactions)
    return accumulator.totals()


async def compute_control_totals(session: Any) -> ControlTotals:
    """The control totals of the whole ledger ``session`` reads: a named read point of the layer.

    Only the columns the totals need, one query per block of ``_BLOCK_SIZE`` rows by primary key, never an SQL sum.
    """
    columns = (
        Transaction.id,
        Transaction.type,
        Transaction.date,
        Transaction.broker_id,
        Transaction.asset_id,
        Transaction.currency,
        Transaction.amount,
        Transaction.quantity,
    )
    accumulator = _LedgerAccumulator()
    last_id: int | None = None
    while True:
        statement = select(*columns).order_by(Transaction.id).limit(_BLOCK_SIZE)
        if last_id is not None:
            statement = statement.where(Transaction.id > last_id)
        rows = (await session.execute(statement)).all()
        if not rows:
            break
        accumulator.add(rows)
        if len(rows) < _BLOCK_SIZE:
            break
        last_id = rows[-1].id
    return accumulator.totals()


class _LedgerAccumulator:
    """Exact running sums of a ledger read in blocks."""

    __slots__ = ("_cash", "_quantities")

    def __init__(self) -> None:
        self._cash: dict[tuple[int, str], Decimal] = {}
        self._quantities: dict[tuple[int, int], Decimal] = {}

    def add(self, rows: Iterable[Any]) -> None:
        rows = list(rows)
        with decimal.localcontext(_EXACT):
            movements = [movement for movement in (cash_movement_from_transaction(row) for row in rows) if movement is not None]
            for broker_id, by_currency in native_balances(movements).items():
                for currency, balance in by_currency.items():
                    self._cash[(broker_id, currency)] = self._cash.get((broker_id, currency), _ZERO) + balance
            for broker_id, by_asset in position_quantities(rows).items():
                for asset_id, quantity in by_asset.items():
                    self._quantities[(broker_id, asset_id)] = self._quantities.get((broker_id, asset_id), _ZERO) + quantity

    def totals(self) -> ControlTotals:
        return ControlTotals(
            version=CONTROL_TOTALS_VERSION,
            cash=tuple((broker_id, currency, _canonical(balance)) for (broker_id, currency), balance in sorted(self._cash.items()) if balance != _ZERO),
            quantities=tuple((broker_id, asset_id, _canonical(quantity)) for (broker_id, asset_id), quantity in sorted(self._quantities.items()) if quantity != _ZERO),
        )


def _canonical_text(value: Decimal) -> str:
    """Plain decimal notation without trailing zeros («10», «0.5», «-12.25», «0.000001»); zero is «0», never «-0»."""
    if value == _ZERO:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _canonical(value: Decimal) -> Decimal:
    return Decimal(_canonical_text(value))


def _as_id(value: Any) -> int:
    if type(value) is not int:
        raise ValueError(f"Malformed control totals: {value!r} is not an id.")
    return value


def _as_currency(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"Malformed control totals: {value!r} is not a currency.")
    return value


def _as_amount(value: Any) -> Decimal:
    if not isinstance(value, str) or _PLAIN_AMOUNT.fullmatch(value) is None:
        preview = repr(value[:40]) + ("…" if len(value) > 40 else "") if isinstance(value, str) else repr(value)
        raise ValueError(f"Malformed control totals: {preview} is not plain decimal text.")
    return _canonical(Decimal(value))
