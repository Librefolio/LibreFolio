"""
Trade Republic «Transaction export» (Profile → Account statements → Transaction export), the native CSV since April 2026.

**The file.** One row per booking, columns read **by name** (23 today: ``datetime, date, account_type, category, type, asset_class,
name, symbol, shares, price, amount, fee, tax, currency, original_amount, original_currency, fx_rate, description, transaction_id``
and either the four counterparty columns or ``value_date``). The file is recognised by a required subset of them
(``REQUIRED_COLUMNS``), never by the exact header.

**Two shapes, the same rows.** As Trade Republic writes it (``,``, every cell quoted) and as Excel saves it back after opening it in
one column: each line is a single quoted cell whose inner quotes are doubled. ``read_rows`` reads both: a row of one cell that holds
the delimiter is read again as CSV.

**The numbers, verbatim.** ``amount`` is the gross value of the booking (``shares × price`` on a trade), ``fee`` and ``tax`` are
columns of their own, already signed: the cash the account sees is ``amount + fee + tax``. So each non-zero column is one transaction,
with the value read: a BUY of ``amount``, a FEE of ``fee``, a TAX of ``tax``, all on the row's asset. Nothing is added up or
recomputed. The currency is the row's ``currency``; ``original_amount``, ``original_currency`` and ``fx_rate`` are ignored (no forex).

**Signs that do not fit (decision D2, 11/11/2026).** A positive tax is money given back from the investment's gain: an INTEREST
«Tax refund», so it counts in the P&L (a DEPOSIT would be new capital), with an info note. A negative dividend (a reversal) and a
positive fee are unknown rows, listed for a report.

**The date (decision D1).** ``date`` is the operation day as the platform states it (local time); ``datetime`` is the UTC instant,
which falls on the day before for an evening booking. A row dated after the server's today, or whose ``value_date`` is, is not
settled yet: left out whole, with an info note (D4).

**What is not imported.** Any (category, type) the table below does not hold: corporate actions, maturities, crypto transfers,
private markets, Saveback, gifts, the German tax types… They may move a position, and no real export shows their columns yet:
``RowSkips.unknown``, never «deposit or withdrawal by the sign». A row of an account other than ``DEFAULT`` (a ``JUNIOR`` depot) is
unknown too, provisionally (D3, suspended by the developer). A repeated ``transaction_id`` is the same booking: dropped quietly.
"""

from __future__ import annotations

import csv
import io as std_io
import re
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMEvidence, BRIMExtractedAssetInfo, BRIMNotice, BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim_providers import _brim_io as io
from backend.app.utils.datetime_utils import server_today

if TYPE_CHECKING:
    from backend.app.services.brim.brim_provider import BRIMProvider

logger = structlog.get_logger(__name__)

REQUIRED_COLUMNS = frozenset({"datetime", "date", "category", "type", "symbol", "shares", "amount", "fee", "tax", "currency", "transaction_id"})
DELIMITERS = (",", ";")
DEFAULT_ACCOUNT = "DEFAULT"
TAGS = ["import", "traderepublic"]
ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")

# --- (category, type) → how the row is read ---------------------------------------------------------------------------------------------
TRADE = "trade"
CASH_IN = "cash_in"  # money that reaches the account: amount > 0
CASH_OUT = "cash_out"  # money that leaves it: amount < 0
INCOME = "income"  # interest or dividend: amount > 0, tax withheld beside it
CHARGE = "charge"  # a fee or a tax as the booking itself: amount < 0
TAX_ONLY = "tax_only"  # the tax column is the booking (stamp duty, tax optimisation); amount is 0

TRADE_TYPES: Dict[str, TransactionType] = {"BUY": TransactionType.BUY, "SELL": TransactionType.SELL}
CASH_TYPES: Dict[str, Tuple[str, Optional[TransactionType]]] = {
    "INTEREST_PAYMENT": (INCOME, TransactionType.INTEREST),
    "DIVIDEND": (INCOME, TransactionType.DIVIDEND),
    "DISTRIBUTION": (INCOME, TransactionType.DIVIDEND),
    "TAX_OPTIMIZATION": (TAX_ONLY, None),
    "TRANSFER_INSTANT_INBOUND": (CASH_IN, TransactionType.DEPOSIT),
    "TRANSFER_INBOUND": (CASH_IN, TransactionType.DEPOSIT),
    "CUSTOMER_INBOUND": (CASH_IN, TransactionType.DEPOSIT),
    "CUSTOMER_INPAYMENT": (CASH_IN, TransactionType.DEPOSIT),
    "TRANSFER_OUTBOUND": (CASH_OUT, TransactionType.WITHDRAWAL),
    "TRANSFER_INSTANT_OUTBOUND": (CASH_OUT, TransactionType.WITHDRAWAL),
    "CUSTOMER_OUTBOUND_REQUEST": (CASH_OUT, TransactionType.WITHDRAWAL),
    "CARD_TRANSACTION": (CASH_OUT, TransactionType.WITHDRAWAL),
    "CARD_TRANSACTION_INTERNATIONAL": (CASH_OUT, TransactionType.WITHDRAWAL),
    "FEE": (CHARGE, TransactionType.FEE),
    "CARD_ORDERING_FEE": (CHARGE, TransactionType.FEE),
    "TAX": (CHARGE, TransactionType.TAX),
}
# The types whose transaction names a security (its symbol is required).
ASSET_REQUIRED = frozenset({TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND})

# --- the two info notes (English: the file is English) -------------------------------------------------------------------------------------
NOT_SETTLED_CODE = "traderepublic_not_yet_settled"
NOT_SETTLED_MESSAGE = "{n} rows are dated after today: they are not settled yet and were left out. They will come with the next export."
NOT_SETTLED_COMMENT = "The date (or value_date) of these rows is after the server's today."
TAX_REFUND_CODE = "traderepublic_tax_refund"
TAX_REFUND_MESSAGE = "{n} tax refunds were imported as interest («Tax refund»): money given back from the investment's gain, so it counts in the P&L."
TAX_REFUND_COMMENT = "A positive tax is money given back."


def _find_layout(first_line: str, preferred: str) -> Optional[Tuple[str, bool]]:
    """The delimiter and whether the lines are wrapped in one cell (Excel), when ``first_line`` is a Transaction export header."""
    for delimiter in dict.fromkeys((preferred, *DELIMITERS)):
        cells = next(csv.reader([first_line], delimiter=delimiter), [])
        wrapped = len(cells) == 1
        if wrapped:
            cells = next(csv.reader([cells[0]], delimiter=delimiter), [])
        if REQUIRED_COLUMNS <= {cell.strip().lower() for cell in cells}:
            return delimiter, wrapped
    return None


def is_transactions_export(provider: BRIMProvider, file_path: Path) -> bool:
    """True when the file's first line is a Transaction export header, in either shape."""
    first_line = provider._read_file_head(file_path, num_lines=1).splitlines()[:1]
    return bool(first_line) and _find_layout(first_line[0], provider.detect_csv_delimiter(file_path)) is not None


def read_rows(provider: BRIMProvider, file_path: Path) -> Tuple[List[str], List[Tuple[int, List[str]]]]:
    """The header (lowercase names) and the data rows with their 1-based line, unwrapped when Excel saved each line as one cell."""
    text = provider._open_text(file_path, newline="").read()
    first_line = text.splitlines()[:1]
    layout = _find_layout(first_line[0], provider.detect_csv_delimiter(file_path)) if first_line else None
    if layout is None:
        return [], []
    delimiter, wrapped = layout
    reader = csv.reader(std_io.StringIO(text, newline=""), delimiter=delimiter)
    rows: List[Tuple[int, List[str]]] = []
    for cells in reader:
        if wrapped and len(cells) == 1:
            cells = next(csv.reader([cells[0]], delimiter=delimiter), [])
        rows.append((reader.line_num, cells))
    header = [cell.strip().lower() for cell in rows[0][1]] if rows else []
    return header, rows[1:]


def _number(value: str) -> Optional[Decimal]:
    """A number as written: ``""`` is None; a dot decimal, or a lone comma decimal (a file re-saved with a comma locale)."""
    value = value.strip()
    if not value:
        return None
    if "," in value and "." not in value and value.count(",") == 1:
        value = value.replace(",", ".")
    try:
        return Decimal(value)
    except InvalidOperation as e:
        raise ValueError(value) from e


def _day(value: str) -> date_type:
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()


@dataclass
class _Row:
    line: int
    cells: List[str]
    get: Dict[str, str]


class TransactionsExportParser:
    """One parse of one Transaction export; ``parse`` returns the output."""

    def __init__(self, provider: BRIMProvider, broker_id: int) -> None:
        self.provider = provider
        self.broker_id = broker_id
        self.transactions: List[TXCreateItem] = []
        self.validation_issues: List[BRIMValidationIssue] = []
        self.extracted_assets: Dict[int, BRIMExtractedAssetInfo] = {}
        self.asset_ids: Dict[str, int] = {}
        self.next_fake_id = FAKE_ASSET_ID_BASE
        self.skips = io.RowSkips()
        self.header: List[str] = []
        self.not_settled: List[_Row] = []
        self.tax_refunds: List[_Row] = []
        self.quiet: Dict[str, int] = {}

    # --- entry -------------------------------------------------------------------------------------------------------------------------------
    def parse(self, file_path: Path) -> BRIMParseOutput:
        self.header, rows = read_rows(self.provider, file_path)
        self.skips.set_headers(self.header)
        seen_ids: set[str] = set()
        today = server_today()
        for line, cells in rows:
            if not any(cell.strip() for cell in cells):
                continue
            row = _Row(line, cells, {name: (cells[i].strip() if i < len(cells) else "") for i, name in enumerate(self.header)})
            tid = row.get.get("transaction_id", "")
            if tid and tid in seen_ids:
                self.quiet["duplicate_transaction_id"] = self.quiet.get("duplicate_transaction_id", 0) + 1
                continue
            if tid:
                seen_ids.add(tid)
            self._row(row, today)

        warnings: List[BRIMNotice] = []
        if not self.transactions:
            warnings.append(BRIMNotice(severity="warning", code="legacy", message="No valid transactions found in file"))
        for reason, count in self.quiet.items():
            logger.info("Trade Republic rows left out without a notice", reason=reason, count=count)
        logger.info("Trade Republic transaction export parsed", transaction_count=len(self.transactions), asset_count=len(self.extracted_assets))
        return BRIMParseOutput(
            transactions=self.transactions,
            warnings=[*warnings, *self._notes(), *self.skips.notices()],
            validation_issues=self.validation_issues,
            extracted_assets=self.extracted_assets,
        )

    # --- one row -----------------------------------------------------------------------------------------------------------------------------
    def _row(self, row: _Row, today: date_type) -> None:  # noqa: C901 — flat guard chain, one early return per reason
        get = row.get
        category, raw_type = get.get("category", "").upper(), get.get("type", "").upper()
        account = get.get("account_type", "").upper()
        if account and account != DEFAULT_ACCOUNT:
            self.skips.unknown(row.line, row.cells, f"account_type {account}: only the {DEFAULT_ACCOUNT} account is imported for now")
            return
        if category == "TRADING" and raw_type in TRADE_TYPES:
            kind, tx_type = TRADE, TRADE_TYPES[raw_type]
        elif category == "CASH" and raw_type in CASH_TYPES:
            kind, tx_type = CASH_TYPES[raw_type]
        else:
            self.skips.unknown(row.line, row.cells, f"unknown type: '{category}/{raw_type}'")
            return

        try:
            day = _day(get.get("date", ""))
        except ValueError:
            self.skips.unreadable(row.line, row.cells, "invalid date")
            return
        try:
            amount, fee, tax, shares = (_number(get.get(name, "")) for name in ("amount", "fee", "tax", "shares"))
            value_date = _day(get["value_date"]) if get.get("value_date") else None
        except ValueError as e:
            self.skips.unreadable(row.line, row.cells, f"invalid number or date: '{e}'")
            return
        currency = get.get("currency", "").upper()
        if not re.fullmatch(r"[A-Z]{3}", currency):
            self.skips.unreadable(row.line, row.cells, "invalid currency")
            return
        if day > today or (value_date is not None and value_date > today):
            self.not_settled.append(row)
            return

        amount, fee, tax = amount or Decimal("0"), fee or Decimal("0"), tax or Decimal("0")
        if fee > 0:
            self.skips.unknown(row.line, row.cells, "positive fee")
            return

        # The booking itself: (type, quantity, cash) or None when the row has none (a tax-only row)
        main: Optional[Tuple[TransactionType, Decimal, Decimal]] = None
        if kind == TRADE:
            if shares is None or amount == 0:
                self.skips.unreadable(row.line, row.cells, f"{raw_type} without shares or amount")
                return
            buy = tx_type == TransactionType.BUY
            if (shares > 0) != buy or (amount < 0) != buy:
                self.skips.unknown(row.line, row.cells, f"{raw_type} with unexpected signs")
                return
            main = (tx_type, shares, amount)
        elif kind == TAX_ONLY:
            if amount != 0:
                self.skips.unknown(row.line, row.cells, f"{raw_type} with an amount")
                return
        elif amount != 0:
            expected_positive = kind in (CASH_IN, INCOME)
            if (amount > 0) != expected_positive:
                self.skips.unknown(row.line, row.cells, f"{raw_type} with an unexpected sign")
                return
            main = (tx_type, Decimal("0"), amount)
        if main is None and fee == 0 and tax == 0:
            self.quiet["all_zero"] = self.quiet.get("all_zero", 0) + 1
            return

        asset_id = self._asset(row, required=main is not None and main[0] in ASSET_REQUIRED)
        if asset_id is False:
            return

        description = get.get("description") or raw_type
        if main is not None:
            self._emit(row, main[0], day, main[1], Currency(code=currency, amount=main[2]), asset_id, description)
        if fee < 0:
            self._emit(row, TransactionType.FEE, day, Decimal("0"), Currency(code=currency, amount=fee), asset_id, f"Fee: {description}")
        if tax < 0:
            self._emit(row, TransactionType.TAX, day, Decimal("0"), Currency(code=currency, amount=tax), asset_id, f"Tax: {description}")
        elif tax > 0:
            self.tax_refunds.append(row)
            self._emit(row, TransactionType.INTEREST, day, Decimal("0"), Currency(code=currency, amount=tax), asset_id, f"Tax refund: {description}")

    def _asset(self, row: _Row, *, required: bool):
        """The fake asset id of the row's security (None without a symbol), or False when one is required and missing."""
        symbol = row.get.get("symbol", "")
        if not symbol:
            if required:
                self.skips.unreadable(row.line, row.cells, f"{row.get.get('type', '')} without a symbol")
                return False
            return None
        if symbol in self.asset_ids:
            return self.asset_ids[symbol]
        asset_id = self.next_fake_id
        self.next_fake_id -= 1
        self.asset_ids[symbol] = asset_id
        is_isin = row.get.get("asset_class", "").upper() != "CRYPTO" and ISIN.match(symbol) is not None
        self.extracted_assets[asset_id] = BRIMExtractedAssetInfo(
            extracted_symbol=None if is_isin else symbol,
            extracted_isin=symbol if is_isin else None,
            extracted_name=row.get.get("name") or None,
        )
        return asset_id

    def _emit(self, row: _Row, tx_type: TransactionType, day: date_type, quantity: Decimal, cash: Currency, asset_id: Optional[int], description: str) -> None:
        self.provider._create_transaction(
            row_num=row.line,
            transactions=self.transactions,
            validation_issues=self.validation_issues,
            context=description,
            broker_id=self.broker_id,
            asset_id=asset_id,
            type=tx_type,
            date=day,
            quantity=quantity,
            cash=cash,
            description=description,
            tags=list(TAGS),
        )

    # --- the info notes ----------------------------------------------------------------------------------------------------------------------
    def _notes(self) -> List[BRIMNotice]:
        notes: List[BRIMNotice] = []
        for rows, code, message, comment in (
            (self.not_settled, NOT_SETTLED_CODE, NOT_SETTLED_MESSAGE, NOT_SETTLED_COMMENT),
            (self.tax_refunds, TAX_REFUND_CODE, TAX_REFUND_MESSAGE, TAX_REFUND_COMMENT),
        ):
            if rows:
                notes.append(BRIMNotice(severity="info", code=code, message=message.format(n=len(rows)), evidence=[self._evidence(rows, comment)], context={"count": len(rows)}))
        return notes

    def _evidence(self, rows: Sequence[_Row], comment: str) -> BRIMEvidence:
        width = len(self.header)
        return BRIMEvidence(title="", headers=list(self.header), rows=[(row.cells + [""] * width)[:width] for row in rows], row_numbers=[row.line for row in rows], comment=comment)


def parse(provider: BRIMProvider, file_path: Path, broker_id: int) -> BRIMParseOutput:
    """Parse a Transaction export (either shape) into transactions, notices and the extracted assets."""
    return TransactionsExportParser(provider, broker_id).parse(file_path)
