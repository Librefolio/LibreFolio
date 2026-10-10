"""Scalable Capital: the reader shared by the two plugins, broker and overnight account.

Not a provider: the leading underscore keeps ``BRIMProviderRegistry.auto_discover`` away
from it (see ``provider_registry.py``). ``broker_scalable`` and ``broker_scalable_deposit``
import it.

**Three files, one shape.** Every file starts with the 14 columns of Scalable's own CSV
export (PRIME, broker account only)::

    date;time;status;reference;description;assetType;type;isin;shares;price;amount;fee;tax;currency

The LibreFolio exporter (``Librefolio/librefolio-exporter``) writes one file per account and
adds ``lf_*`` columns: ``lf_account`` says which account (``broker`` or ``deposit``),
``lf_id`` is the transaction id, ``lf_subtype`` the exact type, ``lf_is_cancellation`` marks
a reversal. The layout is told by the header and the account by the ``lf_account`` values,
never by the file name, whose prefix the user can change.

**Rules** (BRIM: verbatim amounts, no forex, currency per row):

- only executed rows are imported; the others are counted in notices;
- a trade is booked on its gross ``amount`` (shares x price, as in PRIME and in exporter
  1.0.1), with the fee and the tax as FEE and TAX transactions of the same security;
- dividends and interest are booked gross (``amount`` + ``tax``, the tax withheld), with a
  TAX transaction;
- cash rows follow the sign of ``amount``; an unknown cash type is booked by its sign;
- the transaction id goes into the description, so two identical movements stay distinct
  and a movement exported again is recognised as a duplicate.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog
from pydantic import ValidationError

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMEvidence, BRIMExtractedAssetInfo, BRIMNotice, BRIMParseOutput, BRIMRefusal, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim_providers._brim_io import read_rows, to_date, to_decimal_it

logger = structlog.get_logger(__name__)

# The two accounts, and the plugin that reads each (code, name): the refusals name the other one.
BROKER = "broker"
DEPOSIT = "deposit"
BROKER_PLUGIN = ("broker_scalable", "Scalable Capital broker")
DEPOSIT_PLUGIN = ("broker_scalable_deposit", "Scalable Capital overnight account")

# Scalable's own export, compared lowercase: names are read by name, never by position.
PRIME_COLUMNS = ("date", "time", "status", "reference", "description", "assettype", "type", "isin", "shares", "price", "amount", "fee", "tax", "currency")

_TAGS = ("import", "scalable")
_SEP = " · "
_TEXT_LIMIT = 350  # the description column holds 500 characters; the id, the reference and a leg prefix follow the text
_TOLERANCE = Decimal("0.01")
_DATE_FORMATS = ("%Y-%m-%d",)
_EXECUTED = {"executed", "settled"}
_BUY_TYPES = {"buy", "savings plan"}
_TAX_TYPES = {"taxes", "tax"}
_TRANSFER_SUBTYPES = {"CASH_TRANSFER_IN", "CASH_TRANSFER_OUT"}

# Notices in display order: severity, English message ({n}: how many rows) and the comment of the evidence table.
_NOTICES: Dict[str, Tuple[str, str, str]] = {
    "scalable_unreadable_rows": (
        "warning",
        "{n} rows could not be read and were not imported: a date, an amount, a currency, the shares or the security is missing.",
        "A date, an amount, a currency, the shares or the security of these rows is missing or unreadable.",
    ),
    "scalable_fee_in_amount": (
        "warning",
        "{n} trades carry the fee inside their amount, as LibreFolio exporter 1.0.0 wrote it: they were imported as they are, without a separate fee. Export them again with exporter 1.0.1 or later to see the fees apart.",
        "Here amount is shares × price with the fee and the tax already added (or taken away, for a sale).",
    ),
    "scalable_fees_unknown": (
        "warning",
        "{n} rows came without their fee and tax details: they were imported with the amount Scalable shows, without separate fees or taxes. Export again with the option to include fees and taxes to get them.",
        "fee and tax are empty on these rows: unknown, not zero.",
    ),
    "scalable_open_partial": (
        "warning",
        "{n} orders are filled in part and still open: not imported yet. They come executed with a later export.",
        "shares is what was executed so far, lf_ordered_shares what was ordered.",
    ),
    "scalable_reversal": (
        "warning",
        "{n} rows reverse a transaction already booked: they were not imported. Check the reversed transaction and correct it by hand.",
        "lf_is_cancellation is true on these rows.",
    ),
    "scalable_not_imported": (
        "warning",
        "{n} rows were not imported: security transfers, corporate actions and types LibreFolio does not read yet. Add them by hand if they move shares or cash.",
        "The type column says what these rows are.",
    ),
    "scalable_several_overnight_accounts": (
        "warning",
        "The file holds {n} overnight accounts: all their rows go into this broker, whose balance is their sum.",
        "The first row of each overnight account, told apart by lf_account_index.",
    ),
    "scalable_not_executed": (
        "info",
        "{n} rows were not executed (pending, cancelled, expired or rejected) and were not imported. An order executed later comes with the next export.",
        "The status column says why these rows were not executed.",
    ),
    "scalable_internal_transfers": (
        "info",
        "{n} transfers between the broker and the overnight account: import the other account's file into its own broker, then merge each pair into a cash transfer in the bulk editor.",
        "lf_subtype is CASH_TRANSFER_IN or CASH_TRANSFER_OUT on these rows.",
    ),
    "scalable_dividends_net": (
        "info",
        "{n} dividends were imported as credited, net of the tax withheld: the file does not give the tax.",
        "tax is empty on these rows: the amount is what reached the account.",
    ),
    "scalable_tax_refund": (
        "info",
        "{n} tax refunds were imported as deposits: in LibreFolio a tax always takes money out.",
        "A positive tax amount is money given back.",
    ),
    "scalable_cash_by_sign": (
        "info",
        "{n} cash rows have a type LibreFolio does not know, or an unexpected sign: they were imported as deposits or withdrawals, by the sign of their amount.",
        "The sign of amount decided between deposit and withdrawal.",
    ),
}
# No caption of our own: an empty title lets the import wizard show its translated default one.
_EVIDENCE_TITLE = ""


# =============================================================================
# READING AND RECOGNITION
# =============================================================================


@dataclass
class ScalableFile:
    """A Scalable export as read: its layout, its header and its data rows with their line numbers."""

    kind: str  # "prime" or "exporter"
    account: str  # BROKER, DEPOSIT, "mixed", "empty" (no data rows) or "unknown"
    header: List[str]
    index: Dict[str, int]
    rows: List[Tuple[int, List[str]]] = field(default_factory=list)


def _index(header: List[str]) -> Dict[str, int]:
    index: Dict[str, int] = {}
    for position, name in enumerate(header):
        index.setdefault(name.strip().lower(), position)
    return index


def _account(index: Dict[str, int], rows: List[Tuple[int, List[str]]]) -> str:
    if not rows:
        return "empty"
    column = index["lf_account"]
    values = {cells[column].strip().lower() for _, cells in rows if column < len(cells)} - {""}
    if values == {BROKER}:
        return BROKER
    if values == {DEPOSIT}:
        return DEPOSIT
    if values == {BROKER, DEPOSIT}:
        return "mixed"
    return "unknown"


def read_file(provider: BRIMProvider, file_path: Path) -> Optional[ScalableFile]:
    """The file as a Scalable export, or None when it is not one. Raises when the file cannot be read."""
    if file_path.suffix.lower() != ".csv":
        return None
    delimiter = provider.detect_csv_delimiter(file_path)
    first = next(csv.reader(io.StringIO(provider._read_file_head(file_path, num_lines=1)), delimiter=delimiter), None)
    if not first or not set(PRIME_COLUMNS) <= {cell.strip().lower() for cell in first}:
        return None
    raw = read_rows(file_path, delimiter=delimiter)
    header = [str(cell).strip() for cell in raw[0]] if raw else [cell.strip() for cell in first]
    index = _index(header)
    rows = [(line, [str(cell) for cell in cells]) for line, cells in enumerate(raw[1:], start=2) if any(str(cell).strip() for cell in cells)]
    if "lf_account" not in index:
        return ScalableFile(kind="prime", account=BROKER, header=header, index=index, rows=rows)
    return ScalableFile(kind="exporter", account=_account(index, rows), header=header, index=index, rows=rows)


def _safe_read(provider: BRIMProvider, file_path: Path) -> Optional[ScalableFile]:
    """``read_file`` for recognition: a file that cannot be read is simply not a Scalable export."""
    try:
        return read_file(provider, file_path)
    except Exception:  # noqa: BLE001 — can_parse and the refusals never raise: an unreadable file is just not ours
        return None


def _reads(scalable: ScalableFile, account: str) -> bool:
    if scalable.kind == "prime":
        return account == BROKER
    return scalable.account in (account, "empty")


def accepts(provider: BRIMProvider, file_path: Path, account: str) -> bool:
    """True when the plugin of ``account`` reads this file: its own account, or an export with no rows."""
    scalable = _safe_read(provider, file_path)
    return scalable is not None and _reads(scalable, account)


def _plugin_context(plugin: Tuple[str, str]) -> Dict[str, str]:
    return {"plugin_code": plugin[0], "plugin_name": plugin[1]}


def refusal(provider: BRIMProvider, file_path: Path, account: str) -> Optional[BRIMRefusal]:
    """Why the plugin of ``account`` refuses a Scalable export, and which plugin reads it; None for any other file."""
    scalable = _safe_read(provider, file_path)
    if scalable is None or _reads(scalable, account):
        return None
    if scalable.account == "mixed":
        return BRIMRefusal(code="scalable_mixed_file", message="the file mixes the broker and the overnight account: export the two accounts separately")
    if account == BROKER and scalable.account == DEPOSIT:
        return BRIMRefusal(
            code="scalable_deposit_file",
            message="this is the export of the Scalable overnight account: read it with the Scalable Capital overnight account plugin",
            context=_plugin_context(DEPOSIT_PLUGIN),
        )
    if account == DEPOSIT and scalable.kind == "prime":
        return BRIMRefusal(
            code="scalable_prime_file",
            message="this is Scalable's own export of the broker account: read it with the Scalable Capital broker plugin",
            context=_plugin_context(BROKER_PLUGIN),
        )
    if account == DEPOSIT and scalable.account == BROKER:
        return BRIMRefusal(
            code="scalable_broker_file",
            message="this is the export of the Scalable broker account: read it with the Scalable Capital broker plugin",
            context=_plugin_context(BROKER_PLUGIN),
        )
    return None


def parse(provider: BRIMProvider, file_path: Path, broker_id: int, account: str) -> BRIMParseOutput:
    """Parse the export of ``account`` into transactions, notices and extracted assets."""
    try:
        scalable = read_file(provider, file_path)
    except FileNotFoundError:
        raise BRIMParseError(f"File not found: {file_path}") from None
    except Exception as e:
        raise BRIMParseError(f"Error reading file: {e}") from e
    if scalable is None or not _reads(scalable, account):
        refused = refusal(provider, file_path, account)
        raise BRIMParseError(refused.message if refused else "Not a Scalable Capital export", details={"file": file_path.name})
    output = _Reader(provider, broker_id, scalable).run()
    logger.info("Scalable Capital file parsed", plugin_code=provider.provider_code, layout=scalable.kind, transaction_count=len(output.transactions), notice_count=len(output.warnings), asset_count=len(output.extracted_assets))
    return output


# =============================================================================
# CLASSIFICATION
# =============================================================================


@dataclass
class _Row:
    line: int
    cells: List[str]
    index: Dict[str, int]

    def get(self, name: str) -> str:
        column = self.index.get(name)
        if column is None or column >= len(self.cells):
            return ""
        return self.cells[column].strip()

    def number(self, name: str) -> Optional[Decimal]:
        """A PRIME column (decimal comma); None when empty or unreadable."""
        return to_decimal_it(self.get(name))


class _Reader:
    """Classifies the rows of one export and builds the parse output."""

    def __init__(self, provider: BRIMProvider, broker_id: int, scalable: ScalableFile):
        self.provider = provider
        self.broker_id = broker_id
        self.file = scalable
        self.exporter = scalable.kind == "exporter"
        self.transactions: List[TXCreateItem] = []
        self.validation_issues: List[BRIMValidationIssue] = []
        self.flagged: Dict[str, List[_Row]] = {code: [] for code in _NOTICES}
        self.assets: Dict[int, BRIMExtractedAssetInfo] = {}
        self.asset_ids: Dict[str, int] = {}
        self.next_fake_id = FAKE_ASSET_ID_BASE

    # -- output -----------------------------------------------------------------

    def run(self) -> BRIMParseOutput:
        rows = [_Row(line, cells, self.file.index) for line, cells in self.file.rows]
        for row in rows:
            self._row(row)
        self._several_accounts(rows)
        used = {tx.asset_id for tx in self.transactions if tx.asset_id is not None}
        assets = {fake_id: info for fake_id, info in self.assets.items() if fake_id in used}
        return BRIMParseOutput(transactions=self.transactions, warnings=self._notices(), validation_issues=self.validation_issues, extracted_assets=assets)

    def _notices(self) -> List[BRIMNotice]:
        width = len(self.file.header)
        notices = []
        for code, (severity, message, comment) in _NOTICES.items():
            rows = self.flagged[code]
            if not rows:
                continue
            evidence = BRIMEvidence(
                title=_EVIDENCE_TITLE,
                headers=list(self.file.header),
                rows=[(row.cells + [""] * width)[:width] for row in rows],
                row_numbers=[row.line for row in rows],
                comment=comment,
            )
            notices.append(BRIMNotice(severity=severity, code=code, message=message.format(n=len(rows)), evidence=[evidence], context={"count": len(rows)}))
        return notices

    def _flag(self, code: str, row: _Row) -> None:
        self.flagged[code].append(row)

    def _several_accounts(self, rows: List[_Row]) -> None:
        if "lf_account_index" not in self.file.index:
            return
        first: Dict[str, _Row] = {}
        for row in rows:
            first.setdefault(row.get("lf_account_index"), row)
        first.pop("", None)
        if len(first) > 1:
            self.flagged["scalable_several_overnight_accounts"] = list(first.values())

    # -- rows -------------------------------------------------------------------

    def _row(self, row: _Row) -> None:
        if self.exporter and row.get("lf_is_cancellation").lower() == "true":
            self._flag("scalable_reversal", row)
            return
        status = row.get("status").lower()
        if status not in _EXECUTED:
            shares = row.number("shares")
            partial = status == "pending" and row.get("lf_ordered_shares") and shares is not None and shares > 0
            self._flag("scalable_open_partial" if partial else "scalable_not_executed", row)
            return
        if to_date(row.get("date"), _DATE_FORMATS) is None or row.number("amount") is None or not row.get("currency"):
            self._flag("scalable_unreadable_rows", row)
            return
        kind = row.get("type").lower()
        if kind in _BUY_TYPES or kind == "sell":
            self._trade(row, sell=kind == "sell")
        elif "distribution" in kind:
            self._income(row, TransactionType.DIVIDEND)
        elif kind == "interest":
            self._income(row, TransactionType.INTEREST)
        elif kind in ("deposit", "withdrawal", "fee") or kind in _TAX_TYPES or row.get("assettype").lower() == "cash":
            self._cash(row, kind)
        else:
            self._flag("scalable_not_imported", row)

    def _trade(self, row: _Row, sell: bool) -> None:
        shares = row.number("shares")
        amount = abs(row.number("amount"))
        if not shares or not self._asset_key(row):
            self._flag("scalable_unreadable_rows", row)
            return
        fee, tax = row.number("fee"), row.number("tax")
        if self.exporter and not row.get("fee"):
            # Exporter: the details were not read, so fee and tax are unknown and the amount is the net one.
            self._flag("scalable_fees_unknown", row)
            self._create(row, TransactionType.SELL if sell else TransactionType.BUY, -abs(shares) if sell else abs(shares), amount if sell else -amount, asset=True)
            return
        fee = abs(fee or Decimal("0"))
        tax = tax or Decimal("0")
        charges = fee + max(tax, Decimal("0"))
        if self.exporter and charges > _TOLERANCE and self._charges_inside(row, abs(shares), amount, charges):
            self._flag("scalable_fee_in_amount", row)
            self._create(row, TransactionType.SELL if sell else TransactionType.BUY, -abs(shares) if sell else abs(shares), amount if sell else -amount, asset=True)
            return
        if not self._create(row, TransactionType.SELL if sell else TransactionType.BUY, -abs(shares) if sell else abs(shares), amount if sell else -amount, asset=True):
            return
        if fee > 0:
            self._create(row, TransactionType.FEE, Decimal("0"), -fee, asset=True, prefix="Order fee")
        self._tax_leg(row, tax)

    def _tax_leg(self, row: _Row, tax: Decimal) -> None:
        """The tax of a trade: paid (> 0) is a TAX of the security; given back (< 0) is a deposit."""
        if tax > 0:
            self._create(row, TransactionType.TAX, Decimal("0"), -tax, asset=True, prefix="Tax")
        elif tax < 0:
            self._flag("scalable_tax_refund", row)
            self._create(row, TransactionType.DEPOSIT, Decimal("0"), -tax, asset=False, prefix="Tax refund")

    @staticmethod
    def _charges_inside(row: _Row, shares: Decimal, amount: Decimal, charges: Decimal) -> bool:
        """True when the amount already holds the fee and the tax: shares × price differs from it by exactly those."""
        price = row.number("price")
        if price is None:
            return False
        gap = abs(amount - shares * price)
        return gap > _TOLERANCE and abs(gap - charges) <= _TOLERANCE

    def _income(self, row: _Row, tx_type: TransactionType) -> None:
        amount = row.number("amount")
        if amount <= 0:
            self._by_sign(row)
            return
        dividend = tx_type == TransactionType.DIVIDEND
        if dividend and not self._asset_key(row):
            self._flag("scalable_unreadable_rows", row)
            return
        tax = row.number("tax")
        withheld = abs(tax) if tax is not None else Decimal("0")
        if not row.get("tax"):
            if dividend:
                self._flag("scalable_dividends_net", row)
            elif self.exporter:
                self._flag("scalable_fees_unknown", row)
        if self._create(row, tx_type, Decimal("0"), amount + withheld, asset=dividend) and withheld > 0:
            self._create(row, TransactionType.TAX, Decimal("0"), -withheld, asset=dividend, prefix="Tax")

    def _cash(self, row: _Row, kind: str) -> None:
        amount = row.number("amount")
        if amount == 0:
            self._flag("scalable_not_imported", row)
            return
        if row.get("lf_subtype").upper() in _TRANSFER_SUBTYPES:
            self._flag("scalable_internal_transfers", row)
        if kind == "deposit" and amount > 0:
            self._create(row, TransactionType.DEPOSIT, Decimal("0"), amount, asset=False)
        elif kind == "withdrawal" and amount < 0:
            self._create(row, TransactionType.WITHDRAWAL, Decimal("0"), amount, asset=False)
        elif kind == "fee" and amount < 0:
            self._create(row, TransactionType.FEE, Decimal("0"), amount, asset=False)
        elif kind in _TAX_TYPES and amount < 0:
            self._create(row, TransactionType.TAX, Decimal("0"), amount, asset=False)
        elif kind in _TAX_TYPES:
            self._flag("scalable_tax_refund", row)
            self._create(row, TransactionType.DEPOSIT, Decimal("0"), amount, asset=False)
        else:
            self._by_sign(row)

    def _by_sign(self, row: _Row) -> None:
        """A cash row whose type is unknown, or whose sign contradicts it: a deposit or a withdrawal by its sign."""
        amount = row.number("amount")
        if amount == 0:
            self._flag("scalable_not_imported", row)
            return
        self._flag("scalable_cash_by_sign", row)
        self._create(row, TransactionType.DEPOSIT if amount > 0 else TransactionType.WITHDRAWAL, Decimal("0"), amount, asset=False)

    # -- transactions -------------------------------------------------------------

    def _description(self, row: _Row, prefix: Optional[str]) -> str:
        parts = [prefix] if prefix else []
        parts.append((row.get("description") or row.get("type") or "Scalable Capital")[:_TEXT_LIMIT])
        if self.exporter and row.get("lf_id"):
            parts.append(f"id {row.get('lf_id')}")
        if row.get("reference"):
            parts.append(f"ref {row.get('reference')}")
        return _SEP.join(parts)

    def _create(self, row: _Row, tx_type: TransactionType, quantity: Decimal, amount: Decimal, *, asset: bool, prefix: Optional[str] = None) -> bool:
        try:
            cash = Currency(code=row.get("currency").upper(), amount=amount)
        except (ValueError, ValidationError):
            self._flag("scalable_unreadable_rows", row)  # not an ISO 4217 currency
            return False
        created = self.provider._create_transaction(
            row_num=row.line,
            transactions=self.transactions,
            validation_issues=self.validation_issues,
            context=row.get("description") or None,
            broker_id=self.broker_id,
            asset_id=self._asset_id(row) if asset else None,
            type=tx_type,
            date=to_date(row.get("date"), _DATE_FORMATS),
            quantity=quantity,
            cash=cash,
            description=self._description(row, prefix),
            tags=list(_TAGS),
        )
        return created is not None

    @staticmethod
    def _asset_key(row: _Row) -> str:
        return row.get("isin") or row.get("description")

    def _asset_id(self, row: _Row) -> int:
        """One fake asset id per ISIN (the name when there is none), in order of first use."""
        key = self._asset_key(row)
        if key not in self.asset_ids:
            self.asset_ids[key] = self.next_fake_id
            self.assets[self.next_fake_id] = BRIMExtractedAssetInfo(extracted_symbol=None, extracted_isin=row.get("isin") or None, extracted_name=row.get("description") or None)
            self.next_fake_id -= 1
        return self.asset_ids[key]
