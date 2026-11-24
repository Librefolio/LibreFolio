"""
Investimental Broker Report Import Plugin.

Parses Investimental CSV order-update logs on a best-effort basis.

This is an ORDER-UPDATE log, not a clean execution ledger.  The parser groups
rows by ``Order ID`` and emits at most one transaction per order.  It drops the
deleted/rejected requests, requires an execution marker (``Update Type`` = ``Fil``
or a non-zero ``Last Trade ID``), and skips orders whose final state is
cancelled/rejected/expired or never executed.

Each row says how much of the order is still OPEN, not how much was executed.
Since 1.2.0 (project 66, INV-1) the transaction is the sum of the fills: for
each executed row, against the row before it, the executed quantity is the
open ``Volume`` before minus the open ``Volume`` after (on the row that closes
the order, ``Status`` = ``Inactive``, its own ``Volume``) and the executed amount
is ``Value`` before minus ``Value`` after.  The date is the last fill's.  Before,
the last row alone was read, so an order filled in several parts kept only its
last part.

Known limits:
- The file contains tickers only, no ISIN.
- A fill whose quantity times the price before it does not give its amount is
  kept, with a warning to check it; fills on several days make one transaction,
  with a warning naming the days.
- An executed order without its ``New`` row (the export starts with the order
  under way) is skipped: its whole quantity cannot be read.  A warning notice
  (``investimental_order_start_missing``) gives what the file shows (date,
  side, symbol, price, the visible quantity and amount) and the order's rows,
  for entering it by hand.

The fee (1.3.0, INV-2): each row's ``Fee`` is the commission still due on the
OPEN part of the order, so a fill's commission is the ``Fee`` of the row before
it minus its own.  The order's commission is the sum over the fills that count
for the quantity, and becomes one FEE linked to the trade, on its date.  The
row of an expiry is not a fill: its ``Fee`` is the commission of the part not
executed, and is not read.  A sum of 0 (bonds, sells: the export writes 0)
gives no FEE.  One warning notice per file (``investimental_fee_from_order_log``)
lists the fees read, since the order log's figure may differ slightly from the
statement.  A fill on which ``Fee`` rises breaks the rule: that order gets no
FEE and a warning to check its fee on the statement.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMEvidence, BRIMExtractedAssetInfo, BRIMNotice, BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency, iso_currency_code
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.platform.provider_registry import register_provider

logger = structlog.get_logger(__name__)

COL_ORDER_ID = "Order ID"
COL_SIDE = "Side"
COL_EXCHANGE = "Exchange"
COL_SYMBOL = "Symbol"
COL_PRICE = "Price"
COL_VOLUME = "Volume"
COL_VALUE = "Value"
COL_FEE = "Fee"
COL_ACCOUNT_NAME = "Account Name"
COL_LAST_TRADE_ID = "Last Trade ID"
COL_STATUS = "Status"
COL_UPDATE_TYPE = "Update Type"
COL_UPDATE_TIME = "Update Time"
COL_REQUEST_STATUS = "Request Status"

REQUIRED_COLUMNS = [
    COL_ORDER_ID,
    "Order Number",
    COL_SIDE,
    COL_EXCHANGE,
    COL_SYMBOL,
    "Market",
    COL_PRICE,
    COL_VOLUME,
    COL_VALUE,
    COL_FEE,
    COL_ACCOUNT_NAME,
    COL_LAST_TRADE_ID,
    COL_STATUS,
    COL_UPDATE_TYPE,
    COL_UPDATE_TIME,
    COL_REQUEST_STATUS,
]


def _parse_investimental_date(value: str) -> Optional[date_type]:
    """Parse Investimental update date/time."""
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_investimental_datetime(value: str) -> Optional[datetime]:
    value = value.strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _parse_investimental_number(value: str) -> Optional[Decimal]:
    """Parse Investimental decimal numbers."""
    value = value.strip()
    if not value:
        return None
    try:
        return Decimal(value.replace(",", ""))
    except InvalidOperation:
        return None


def _extract_currency_from_account(value: str) -> Optional[str]:
    """Extract currency code from account name like 'JOHN DOE [RON]'."""
    value = value.strip()
    if "[" not in value or "]" not in value:
        return None
    code = value.rsplit("[", 1)[1].split("]", 1)[0].strip().upper()
    if not code:
        return None
    try:
        # An ISO 4217 alphabetic code only: a name or a number in the brackets is no currency (E-18)
        return iso_currency_code(code)
    except ValueError:
        return None


def _row_is_deleted_or_rejected(row: Dict[str, str]) -> bool:
    request_status = (row.get(COL_REQUEST_STATUS) or "").strip().lower()
    return request_status in {"deleted", "rejected"}


def _row_has_execution_marker(row: Dict[str, str]) -> bool:
    update_type = (row.get(COL_UPDATE_TYPE) or "").strip().lower()
    last_trade_id = (row.get(COL_LAST_TRADE_ID) or "").strip()
    return update_type == "fil" or last_trade_id not in {"", "0"}


#: Quantity times price may differ from the amount by this much before a fill is flagged (a cent, the file's rounding).
_FILL_TOLERANCE = Decimal("0.01")


def _number_or_zero(row: Dict[str, str], column: str) -> Decimal:
    return _parse_investimental_number(row.get(column, "")) or Decimal("0")


@dataclass
class _Fill:
    """One executed row of an order: what it executed, read against the row before it."""

    row: Dict[str, str]
    quantity: Decimal
    amount: Decimal
    #: The amount is ``Price * Volume``: the row had no row before it and no ``Value``.
    estimated: bool = False
    #: Quantity times the price before it does not give the amount.
    mismatched: bool = False
    #: The commission it executed: the ``Fee`` before it minus its own (INV-2); 0 without a row before it.
    fee: Decimal = Decimal("0")


def _fill_of(before: Optional[Dict[str, str]], row: Dict[str, str]) -> _Fill:
    """What an executed row executed (INV-1). The open ``Volume`` and ``Value`` fall by the executed part; the row
    that closes the order (``Inactive``) shows its own last part. Without a row before it (the file starts with the
    order under way), only a closing row says what it executed; a fill still open says what is left, and counts 0."""
    volume = _number_or_zero(row, COL_VOLUME)
    value = _number_or_zero(row, COL_VALUE)
    closing = (row.get(COL_STATUS) or "").strip().lower() == "inactive"
    if before is None:
        if not closing:
            return _Fill(row=row, quantity=Decimal("0"), amount=Decimal("0"))
        if value == 0:
            price = _number_or_zero(row, COL_PRICE)
            return _Fill(row=row, quantity=volume, amount=price * volume, estimated=price > 0)
        return _Fill(row=row, quantity=volume, amount=value)
    quantity = volume if closing else _number_or_zero(before, COL_VOLUME) - volume
    amount = _number_or_zero(before, COL_VALUE) - value
    mismatched = abs(quantity * _number_or_zero(before, COL_PRICE) - amount) > _FILL_TOLERANCE
    fee = _number_or_zero(before, COL_FEE) - _number_or_zero(row, COL_FEE)
    return _Fill(row=row, quantity=quantity, amount=amount, mismatched=mismatched, fee=fee)


def _order_start_shown(rows: List[Dict[str, str]]) -> bool:
    """The file shows the order from its start: a ``New`` row among the ones that count (not a deleted request)."""
    return any((row.get(COL_UPDATE_TYPE) or "").strip().lower() == "new" for row in rows)


#: The columns of the evidence of the fee notice: one row per FEE read from the order log.
_FEE_EVIDENCE_COLUMNS = ["Order", "Symbol", "Date", "Amount", "Currency"]


def _fee_notice(entries: List[tuple[List[str], int]]) -> BRIMNotice:
    """One notice per file for the fees read from the order log (INV-2, FEE consultant 24/11): the order log's figure
    may differ slightly from the statement. One evidence row per FEE, on the line of the order's last fill."""
    count = len(entries)
    return BRIMNotice(
        severity="warning",
        code="investimental_fee_from_order_log",
        message=f"{count} fee{'s were' if count != 1 else ' was'} read from the order log: check {'them' if count != 1 else 'it'} against your statement.",
        context={"count": count},
        evidence=[
            BRIMEvidence(
                title="",
                headers=list(_FEE_EVIDENCE_COLUMNS),
                rows=[cells for cells, _ in entries],
                row_numbers=[line for _, line in entries],
                comment="Each fee is the drop, at each fill, of the commission still due on the open part of the order.",
            )
        ],
    )


#: The columns of an order's rows shown as evidence beside the notice of a skipped order.
_EVIDENCE_COLUMNS = [COL_UPDATE_TIME, COL_SIDE, COL_PRICE, COL_VOLUME, COL_VALUE, COL_FEE, COL_STATUS, COL_UPDATE_TYPE, COL_LAST_TRADE_ID]


def _plain(number: Decimal) -> str:
    """A decimal as people write it: no trailing zeros, no exponent (``15114.050000`` → ``15114.05``, ``200`` → ``200``)."""
    return format(number.normalize(), "f")


def _start_missing_notice(order_id: str, lines: List[tuple[int, Dict[str, str]]], last_fill: Dict[str, str], visible: tuple[Decimal, Decimal], currency: str) -> BRIMNotice:
    """The order is executed but the file starts after its ``New`` row: its whole quantity cannot be read, so it is
    skipped (INV-1, FEE consultant 24/11, choice a) and the notice gives what the file shows, for entering it by hand.
    A partial trade with a blocker was tried first: the correction step cannot fix an amount, so a wrong amount would
    have reached the Bulk unmarked."""
    quantity, amount = visible
    shown = quantity > 0
    day = _parse_investimental_date(last_fill.get(COL_UPDATE_TIME, ""))
    price = _number_or_zero(last_fill, COL_PRICE)
    side = (last_fill.get(COL_SIDE) or "").strip().lower()
    symbol = (last_fill.get(COL_SYMBOL) or "").strip().upper()
    return BRIMNotice(
        severity="warning",
        code="investimental_order_start_missing",
        message=(
            f"Order {order_id} ({side} {symbol}, last fill on {day.isoformat() if day else '?'} at {_plain(price)}): the file starts with this order "
            f"already under way, so its whole quantity cannot be read from the file " + (f"(the file shows {_plain(quantity)} for {_plain(amount)} {currency}). " if shown else "(none of the fills it shows can be counted). ") + "The order was not imported: enter it by hand from your statement."
        ),
        context={
            "order": order_id,
            "date": day.isoformat() if day else "",
            "side": side,
            "symbol": symbol,
            "price": _plain(price),
            "quantity": _plain(quantity),
            "amount": _plain(amount),
            "currency": currency,
            "visible": "yes" if shown else "no",
        },
        evidence=[
            BRIMEvidence(
                title=f"Order {order_id}",
                headers=list(_EVIDENCE_COLUMNS),
                rows=[[(row.get(column) or "").strip() for column in _EVIDENCE_COLUMNS] for _, row in lines],
                row_numbers=[line for line, _ in lines],
                comment="Each row gives the volume still open. The first rows of the order, with the first fills, are not in the file.",
            )
        ],
    )


def _executed_fills(rows: List[Dict[str, str]]) -> List[_Fill]:
    """The fills of an order, its rows in time order without the deleted/rejected requests; a fill that executed
    nothing (the open volume did not fall) is left out."""
    fills: List[_Fill] = []
    before: Optional[Dict[str, str]] = None
    for row in rows:
        if _row_has_execution_marker(row):
            fill = _fill_of(before, row)
            if fill.quantity > 0:
                fills.append(fill)
        before = row
    return fills


@register_provider(BRIMProviderRegistry)
class InvestimentalBrokerProvider(BRIMProvider):
    """Investimental order-update CSV import plugin."""

    @property
    def provider_code(self) -> str:
        return "broker_investimental"

    @property
    def provider_name(self) -> str:
        return "Investimental"

    @property
    def description(self) -> str:
        return "Import final executed transactions from Investimental CSV order-update logs. Cancellations, rejected requests, and unexecuted orders are skipped."

    @property
    def supported_extensions(self) -> List[str]:
        return [".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://www.investimental.ro/wp-content/themes/investimental/img/favicon/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/investimental/"

    @property
    def plugin_version(self) -> str:
        # 1.1.0 — project 66, P4: a fee or a tax is linked to the booking of its own row.
        # 1.2.0 — project 66, INV-1: an order filled in several parts is the sum of its fills, not its last part.
        # 1.3.0 — project 66, INV-2: the commission of the fills, one FEE per order linked to its trade.
        return "1.3.0"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "investimental"

    @staticmethod
    def _fill_warnings(order_id: str, fills: List[_Fill]) -> List[str]:
        """What the user should check on an order's fills: an estimated amount, a fill whose numbers disagree, fills
        on several days (one transaction, on the last fill's date)."""
        notes: List[str] = []
        if any(fill.estimated for fill in fills):
            notes.append(f"Order {order_id}: zero Value on final fill; estimated cash as Price * Volume")
        if any(fill.mismatched for fill in fills):
            notes.append(f"Order {order_id}: executed quantity times price does not give the executed amount; check this trade against your statement")
        days = sorted({day.isoformat() for day in (_parse_investimental_date(fill.row.get(COL_UPDATE_TIME, "")) for fill in fills) if day})
        if len(days) > 1:
            notes.append(f"Order {order_id}: filled on several days ({', '.join(days)}); imported as one trade on {days[-1]}")
        return notes

    def can_parse(self, file_path: Path) -> bool:
        """Detect Investimental format by distinctive order-log headers."""
        if file_path.suffix.lower() != ".csv":
            return False
        try:
            content = self._read_file_head(file_path, num_lines=2)
            first_line = content.splitlines()[0] if content else ""
            header = next(csv.reader([first_line]))
            return all(col in header for col in REQUIRED_COLUMNS)
        except Exception:
            return False

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat order-state filter chain and field mapping, no nested decisions
        """Parse Investimental CSV export file."""
        transactions: List[TXCreateItem] = []
        warnings: List[str | BRIMNotice] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted_assets_raw: Dict[int, Dict[str, Optional[str]]] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE
        orders: Dict[str, List[Dict[str, str]]] = {}
        row_numbers: Dict[str, List[int]] = {}
        skipped_cancelled = 0
        skipped_unexecuted = 0
        skipped_invalid = 0
        skipped_start = 0
        fee_entries: List[tuple[List[str], int]] = []

        def get_asset_id(symbol: str) -> int:
            nonlocal next_fake_id
            symbol = symbol.strip().upper()
            if symbol in asset_to_fake_id:
                return asset_to_fake_id[symbol]
            asset_id = next_fake_id
            asset_to_fake_id[symbol] = asset_id
            extracted_assets_raw[asset_id] = {
                "extracted_symbol": symbol,
                "extracted_isin": None,
                "extracted_name": symbol,
            }
            next_fake_id -= 1
            return asset_id

        detected_delim = self.detect_csv_delimiter(file_path)

        try:
            with self._open_text(file_path, newline="") as f:
                reader = csv.DictReader(f, delimiter=detected_delim)
                if not reader.fieldnames or not all(col in reader.fieldnames for col in REQUIRED_COLUMNS):
                    raise BRIMParseError("Unexpected Investimental header", details={"code": "header_mismatch"})

                row_num = 1
                for row in reader:
                    row_num += 1
                    order_id = (row.get(COL_ORDER_ID) or "").strip()
                    if not order_id:
                        skipped_invalid += 1
                        warnings.append(f"Row {row_num}: missing Order ID, skipping")
                        continue
                    orders.setdefault(order_id, []).append(row)
                    row_numbers.setdefault(order_id, []).append(row_num)

            for order_id, rows in orders.items():
                sorted_rows = sorted(rows, key=lambda r: _parse_investimental_datetime(r.get(COL_UPDATE_TIME, "")) or datetime.min)
                final_row = sorted_rows[-1]
                candidate_rows = [row for row in sorted_rows if not _row_is_deleted_or_rejected(row)]

                if not candidate_rows:
                    skipped_cancelled += 1
                    warnings.append(f"Order {order_id}: final state deleted/rejected, skipping")
                    continue

                has_execution = any(_row_has_execution_marker(row) for row in sorted_rows)
                final_request_status = (final_row.get(COL_REQUEST_STATUS) or "").strip().lower()
                final_update_type = (final_row.get(COL_UPDATE_TYPE) or "").strip().lower()
                if final_request_status in {"deleted", "rejected"} and not has_execution:
                    skipped_cancelled += 1
                    warnings.append(f"Order {order_id}: final state {final_request_status}, skipping")
                    continue
                if final_update_type in {"oot", "exp", "can"} and not has_execution:
                    skipped_cancelled += 1
                    warnings.append(f"Order {order_id}: final state {final_update_type}, skipping")
                    continue
                if not has_execution:
                    skipped_unexecuted += 1
                    warnings.append(f"Order {order_id}: no executed fill marker, skipping")
                    continue

                fills = _executed_fills(candidate_rows)
                if not _order_start_shown(candidate_rows):
                    # Executed, but the file starts after the order's New row: its whole quantity cannot be read, even when
                    # none of the fills it shows can be counted (INV-1, choice a).
                    skipped_start += 1
                    executed = [row for row in candidate_rows if _row_has_execution_marker(row)]
                    last_executed = fills[-1].row if fills else (executed or candidate_rows)[-1]
                    shown_part = (sum((fill.quantity for fill in fills), Decimal("0")), sum((fill.amount for fill in fills), Decimal("0")))
                    currency_shown = _extract_currency_from_account(last_executed.get(COL_ACCOUNT_NAME, "")) or ""
                    lines = sorted(zip(row_numbers[order_id], rows, strict=True), key=lambda line: line[0])
                    warnings.append(_start_missing_notice(order_id, lines, last_executed, shown_part, currency_shown))
                    continue
                if not fills:
                    skipped_unexecuted += 1
                    warnings.append(f"Order {order_id}: no executed fill, skipping")
                    continue

                selected = candidate_rows[-1]
                last_fill = fills[-1].row
                selected_row_num = row_numbers[order_id][rows.index(last_fill)]
                tx_date = _parse_investimental_date(last_fill.get(COL_UPDATE_TIME, ""))
                side = (selected.get(COL_SIDE) or "").strip().lower()
                symbol = (selected.get(COL_SYMBOL) or "").strip().upper()
                currency = _extract_currency_from_account(selected.get(COL_ACCOUNT_NAME, ""))
                volume = sum((fill.quantity for fill in fills), Decimal("0"))
                value = sum((fill.amount for fill in fills), Decimal("0"))

                if not tx_date or side not in {"buy", "sell"} or not symbol or not currency:
                    skipped_invalid += 1
                    warnings.append(f"Order {order_id}: missing date/side/symbol/currency, skipping")
                    continue
                if value <= 0:
                    skipped_invalid += 1
                    warnings.append(f"Order {order_id}: zero Value and no valid price, skipping")
                    continue
                warnings.extend(self._fill_warnings(order_id, fills))

                asset_id = get_asset_id(symbol)
                tx_type = TransactionType.BUY if side == "buy" else TransactionType.SELL
                quantity = abs(volume) if tx_type == TransactionType.BUY else -abs(volume)
                cash_amount = -abs(value) if tx_type == TransactionType.BUY else abs(value)
                exchange = (selected.get(COL_EXCHANGE) or "").strip()
                description = f"Investimental {side} {symbol}"
                if exchange:
                    description = f"{description} on {exchange}"

                booking = self._create_transaction(
                    row_num=selected_row_num,
                    transactions=transactions,
                    validation_issues=validation_issues,
                    context=description,
                    broker_id=broker_id,
                    asset_id=asset_id,
                    type=tx_type,
                    date=tx_date,
                    quantity=quantity,
                    cash=Currency(code=currency, amount=cash_amount),
                    description=description,
                    tags=["import", "investimental"],
                )

                # INV-2: the commission of the counted fills. A rise of Fee on a fill breaks the rule: no FEE for the order.
                fee = sum((fill.fee for fill in fills), Decimal("0"))
                if any(fill.fee < 0 for fill in fills):
                    warnings.append(f"Order {order_id}: the fee cannot be read from the order log (it rises on a fill); no fee imported, check it against your statement")
                elif fee > 0:
                    charge = self._create_charge_of(
                        booking,  # project 66 P4: linked to the booking of its own row; free when that booking was refused
                        row_num=selected_row_num,
                        transactions=transactions,
                        validation_issues=validation_issues,
                        context=f"Fee: {description}",
                        broker_id=broker_id,
                        asset_id=asset_id,
                        type=TransactionType.FEE,
                        date=tx_date,
                        quantity=Decimal("0"),
                        cash=Currency(code=currency, amount=-abs(fee)),
                        description=f"Investimental fee: {symbol}",
                        tags=["import", "investimental", "fee"],
                    )
                    if charge is not None:
                        fee_entries.append(([order_id, symbol, tx_date.isoformat(), _plain(fee), currency], selected_row_num))

        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}", details={"code": "file_not_found", "context": {"file": file_path.name}}) from None
        except BRIMParseError:
            raise
        except Exception as e:
            raise BRIMParseError(f"Error parsing file: {e}", details={"code": "file_unreadable", "context": {"error": str(e)}}) from e

        if fee_entries:
            warnings.append(_fee_notice(fee_entries))
        if skipped_cancelled:
            warnings.append(f"Summary: skipped {skipped_cancelled} cancelled/rejected/expired orders")
        if skipped_unexecuted:
            warnings.append(f"Summary: skipped {skipped_unexecuted} orders without executed fills")
        if skipped_start:
            warnings.append(f"Summary: skipped {skipped_start} orders without their start (the file begins with them under way)")
        if skipped_invalid:
            warnings.append(f"Summary: skipped {skipped_invalid} invalid rows/orders")
        if not transactions:
            warnings.append("No valid transactions found in file")

        extracted_assets_typed: Dict[int, BRIMExtractedAssetInfo] = {
            fake_id: BRIMExtractedAssetInfo(
                extracted_symbol=info.get("extracted_symbol"),
                extracted_isin=info.get("extracted_isin"),
                extracted_name=info.get("extracted_name"),
            )
            for fake_id, info in extracted_assets_raw.items()
        }

        logger.info(
            "Investimental file parsed",
            transaction_count=len(transactions),
            warning_count=len(warnings),
            asset_count=len(extracted_assets_typed),
        )

        return BRIMParseOutput(transactions=transactions, warnings=warnings, validation_issues=validation_issues, extracted_assets=extracted_assets_typed)
