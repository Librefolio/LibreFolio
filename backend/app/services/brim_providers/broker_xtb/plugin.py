"""
XTB Broker Report Import Plugin.

Reads XTB's **History report** workbook (``.xlsx``), the export XTB generates today on desktop and in the app (History →
Export → New report). Transactions come from its *Cash Operations* sheet, the account currency from *Open Positions*
(``_workbook.py``).

Every ``Amount`` is in the account currency, also on an instrument quoted in another currency: the currency written in a
comment (``SPYL.DE USD 0.6600/ SHR``) is the one of the dividend per share, never the one of the amount.

History: version 1.x of this plugin was built on the sample of the Export-To-Ghostfolio project, the «Cash Operations» CSV
of xStation 5 (``ID;Type;Time;Symbol;Comment;Amount``). XTB no longer exports that CSV (its report dialog has no format
choice since 2026: the report is the workbook), so 2.0.0 reads the workbook only (lane 83, release 1.4). The type labels
of that CSV stay in ``TYPE_MAPPINGS`` as candidates for the workbook's types not seen in a real report yet.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMEvidence, BRIMExtractedAssetInfo, BRIMNotice, BRIMParseOutput, BRIMValidationIssue
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.brim_providers import _brim_io as io
from backend.app.services.brim_providers.broker_xtb import _workbook as wb
from backend.app.services.platform.provider_registry import register_provider

logger = structlog.get_logger(__name__)

# Exact label first, then a key contained in the label. Insertion order matters for the second pass: the longer
# labels («free funds interests tax») come before the shorter ones they contain («interest»).
TYPE_MAPPINGS: Dict[str, TransactionType] = {
    "stock purchase": TransactionType.BUY,  # seen in a real History report (2026)
    "stock sale": TransactionType.SELL,
    "stocks/etf purchase": TransactionType.BUY,  # the old Cash Operations CSV (and its Portuguese labels)
    "ações/etf compra": TransactionType.BUY,
    "stocks/etf sale": TransactionType.SELL,
    "ações/etf vende": TransactionType.SELL,
    "deposit": TransactionType.DEPOSIT,
    "withdrawal": TransactionType.WITHDRAWAL,
    "dividend": TransactionType.DIVIDEND,
    "withholding tax": TransactionType.TAX,
    "commission": TransactionType.FEE,
    "fee": TransactionType.FEE,
    "free funds interests tax": TransactionType.TAX,
    "free-funds interest tax": TransactionType.TAX,
    "free funds interests": TransactionType.INTEREST,
    "free-funds interest": TransactionType.INTEREST,
    "interest": TransactionType.INTEREST,
}

# A move between two sub-accounts of the same account (My Trades → Investment Plans): a pair +X / −X at the same instant.
SUBACCOUNT_TRANSFER = "subaccount transfer"
PAIR_WINDOW_SECONDS = 2

OUTSIDE_PERIOD_CODE = "xtb_positions_outside_period"
OUTSIDE_PERIOD_MESSAGE = "For {n} instruments the quantity imported from this report differs from the quantity XTB shows open: trades made before the " "report's start (or after its end) are not in the file. Generate the report with the date range «All» to import the whole history."
OUTSIDE_PERIOD_COMMENT = "Open volume from the Open Positions sheet, next to the net quantity of the Cash Operations rows imported."

CURRENCY_MISSING_CODE = "xtb_account_currency_missing"
CURRENCY_AMBIGUOUS_CODE = "xtb_account_currency_ambiguous"

TAGS = ["import", "xtb"]


def _parse_xtb_number(value: str) -> Optional[Decimal]:
    """Parse XTB decimal number."""
    value = value.strip().replace(",", ".")
    if not value or value in {"-", "-."}:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _map_xtb_type(value: str) -> Optional[TransactionType]:
    value_lower = value.strip().lower()
    if value_lower in TYPE_MAPPINGS:
        return TYPE_MAPPINGS[value_lower]
    for key, tx_type in TYPE_MAPPINGS.items():
        if key in value_lower:
            return tx_type
    return None


def _is_decimal_token(value: str) -> bool:
    return _parse_xtb_number(value) is not None


def _parse_xtb_comment_quantity_price(comment: str) -> tuple[Decimal, Optional[Decimal]]:
    """Extract quantity and price from comments like ``OPEN BUY 34/42.5658 @ 11.7480`` or ``OPEN BUY VWCE.DE 0.19 @ 169.86``.

    ``34/42.5658`` is a partial fill: 34 units of an order of 42.5658, and the row's amount is the one of the 34.
    """
    tokens = comment.replace("/", " / ").replace("@", " @ ").split()
    quantity = Decimal("0")
    price: Optional[Decimal] = None

    for index, token in enumerate(tokens):
        if token == "@" and index + 1 < len(tokens):
            price = _parse_xtb_number(tokens[index + 1])
            break

    action_index = next((i for i, token in enumerate(tokens) if token.upper() in {"BUY", "SELL"}), None)
    search_tokens = tokens[action_index + 1 :] if action_index is not None else tokens
    for token in search_tokens:
        if _is_decimal_token(token):
            quantity = _parse_xtb_number(token) or Decimal("0")
            break

    return quantity, price


@dataclass
class _Row:
    """One row of the Cash Operations sheet, with the cells it came from (for the evidence)."""

    line: int
    cells: List[str]
    type_raw: str
    time: Optional[datetime]
    time_raw: str
    amount: Optional[Decimal]
    amount_raw: str
    symbol: str
    comment: str
    name: str = ""


@dataclass
class _Source:
    """What the workbook reader hands to the row loop."""

    rows: List[_Row]
    headers: List[str]
    currency: str
    open_positions: List[wb.OpenPosition] = field(default_factory=list)


@register_provider(BRIMProviderRegistry)
class XTBBrokerProvider(BRIMProvider):
    """XTB import plugin: the History report workbook (``.xlsx``)."""

    @property
    def provider_code(self) -> str:
        return "broker_xtb"

    @property
    def provider_name(self) -> str:
        return "XTB"

    @property
    def description(self) -> str:
        return "Import XTB's History report (Excel): purchases, sales, deposits, withdrawals, dividends, withholding taxes, fees and interest."

    @property
    def supported_extensions(self) -> List[str]:
        return [".xlsx"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://www.xtb.com/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/xtb/"

    @property
    def plugin_version(self) -> str:
        # 2.0.0 — lane 83: the History report workbook (.xlsx) only; the old Cash Operations CSV is no longer read (XTB no
        # longer exports it); unknown and unreadable rows in the two shared notices (RowSkips).
        return "2.0.0"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "xtb"

    # ------------------------------------------------------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------------------------------------------------------

    def can_parse(self, file_path: Path) -> bool:
        if file_path.suffix.lower() != ".xlsx":
            return False
        try:
            return wb.is_xtb_workbook(wb.read_workbook(file_path, limit=15))
        except Exception:  # a detection probe: any unreadable workbook is simply not ours
            return False

    # ------------------------------------------------------------------------------------------------------------------
    # Readers
    # ------------------------------------------------------------------------------------------------------------------

    def _read_xlsx(self, file_path: Path) -> _Source:
        book = wb.read_workbook(file_path)
        if not wb.is_xtb_workbook(book):
            raise BRIMParseError("Not an XTB History report: the Cash Operations table was not found", details={"code": "header_row_not_found"})

        currencies = wb.account_currencies(book)
        if not currencies:
            raise BRIMParseError("The account currency was not found in the Open Positions sheet", details={"code": CURRENCY_MISSING_CODE})
        if len(currencies) > 1:
            raise BRIMParseError(
                f"The Open Positions sheet names more than one account currency ({', '.join(currencies)})",
                details={"code": CURRENCY_AMBIGUOUS_CODE, "context": {"currencies": ", ".join(currencies)}},
            )

        sheet = book.rows(wb.CASH_SHEET)
        start = wb.find_header(sheet, wb.CASH_REQUIRED)
        assert start is not None  # is_xtb_workbook found it
        columns = wb.column_index(sheet[start])
        headers = [wb.cell_text(cell) for cell in sheet[start]]
        rows: List[_Row] = []
        for line, raw in enumerate(sheet[start + 1 :], start=start + 2):
            time_value = wb.get(raw, columns, "Time")
            amount_value = wb.get(raw, columns, "Amount")
            rows.append(
                _Row(
                    line=line,
                    cells=[wb.cell_text(cell) for cell in raw],
                    type_raw=wb.cell_text(wb.get(raw, columns, "Type")),
                    time=wb.cell_datetime(time_value),
                    time_raw=wb.cell_text(time_value),
                    amount=wb.cell_decimal(amount_value),
                    amount_raw=wb.cell_text(amount_value),
                    symbol=wb.cell_text(wb.get(raw, columns, "Ticker")),
                    comment=wb.cell_text(wb.get(raw, columns, "Comment")),
                    name=wb.cell_text(wb.get(raw, columns, "Instrument")),
                )
            )
        return _Source(rows=rows, headers=headers, currency=currencies[0], open_positions=wb.open_positions(book))

    # ------------------------------------------------------------------------------------------------------------------
    # Parse
    # ------------------------------------------------------------------------------------------------------------------

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        try:
            source = self._read_xlsx(file_path)
        except FileNotFoundError:
            raise BRIMParseError(f"File not found: {file_path}", details={"code": "file_not_found", "context": {"file": file_path.name}}) from None
        except BRIMParseError:
            raise
        except Exception as e:  # isolation boundary: any reader failure becomes the plugin's «unreadable» refusal
            logger.warning("XTB file unreadable", file=file_path.name, exc_info=e)
            raise BRIMParseError(f"Error parsing file: {e}", details={"code": "file_unreadable", "context": {"error": str(e)}}) from e
        return self._parse_rows(source, broker_id)

    def _parse_rows(self, source: _Source, broker_id: int) -> BRIMParseOutput:  # noqa: C901 — flat row loop: guards and per-type sign dispatch
        transactions: List[TXCreateItem] = []
        validation_issues: List[BRIMValidationIssue] = []
        extracted: Dict[int, BRIMExtractedAssetInfo] = {}
        asset_to_fake_id: Dict[str, int] = {}
        next_fake_id = FAKE_ASSET_ID_BASE
        skips = io.RowSkips(source.headers)
        imported_quantity: Dict[str, Decimal] = defaultdict(Decimal)
        transfers: List[_Row] = []
        quiet: Dict[str, int] = defaultdict(int)

        for row in source.rows:
            if not row.type_raw:
                if any(row.cells):
                    if row.cells and row.cells[0].strip().lower() in wb.TOTAL_LABELS:
                        quiet["total_row"] += 1
                    else:
                        skips.unreadable(row.line, row.cells, "Type is empty")
                continue
            if row.type_raw.strip().lower() in wb.TOTAL_LABELS:
                quiet["total_row"] += 1
                continue
            if row.type_raw.strip().lower() == SUBACCOUNT_TRANSFER:
                transfers.append(row)
                continue

            tx_type = _map_xtb_type(row.type_raw)
            if tx_type is None:
                skips.unknown(row.line, row.cells, f"Type «{row.type_raw}»")
                continue
            if row.time is None:
                skips.unreadable(row.line, row.cells, f"Time «{row.time_raw}»")
                continue
            if row.amount is None:
                skips.unreadable(row.line, row.cells, f"Amount «{row.amount_raw}»")
                continue

            quantity, price = _parse_xtb_comment_quantity_price(row.comment)
            amount = row.amount
            if tx_type == TransactionType.BUY:
                quantity = abs(quantity)
                amount = -abs(amount)
            elif tx_type == TransactionType.SELL:
                quantity = -abs(quantity)
                amount = abs(amount)
            elif tx_type in (TransactionType.DIVIDEND, TransactionType.INTEREST, TransactionType.DEPOSIT):
                quantity = Decimal("0")
                amount = abs(amount)
            elif tx_type in (TransactionType.WITHDRAWAL, TransactionType.FEE, TransactionType.TAX):
                quantity = Decimal("0")
                amount = -abs(amount)

            asset_required = tx_type in (TransactionType.BUY, TransactionType.SELL, TransactionType.DIVIDEND)
            asset_optional = tx_type in (TransactionType.INTEREST, TransactionType.FEE, TransactionType.TAX)
            if asset_required and not row.symbol:
                skips.unreadable(row.line, row.cells, f"{tx_type.value} without a symbol")
                continue
            if tx_type in (TransactionType.BUY, TransactionType.SELL) and quantity == 0:
                skips.unreadable(row.line, row.cells, f"Quantity in the comment «{row.comment}»")
                continue

            asset_id = None
            if asset_required or (asset_optional and row.symbol):
                asset_id = asset_to_fake_id.get(row.symbol)
                if asset_id is None:
                    asset_id = next_fake_id
                    asset_to_fake_id[row.symbol] = asset_id
                    extracted[asset_id] = BRIMExtractedAssetInfo(extracted_symbol=row.symbol, extracted_isin=None, extracted_name=row.name or row.symbol)
                    next_fake_id -= 1
            if tx_type in (TransactionType.BUY, TransactionType.SELL):
                imported_quantity[row.symbol] += quantity

            description_parts = [row.type_raw]
            if row.symbol:
                description_parts.append(row.symbol)
            if row.comment:
                description_parts.append(row.comment)
            if price is not None:
                description_parts.append(f"price={price}")
            description = " | ".join(description_parts)

            self._create_transaction(
                row_num=row.line,
                transactions=transactions,
                validation_issues=validation_issues,
                context=description,
                broker_id=broker_id,
                asset_id=asset_id,
                type=tx_type,
                date=row.time.date(),
                quantity=quantity,
                cash=Currency(code=source.currency, amount=amount),
                description=description,
                tags=list(TAGS),
            )

        paired, unpaired = _pair_transfers(transfers)
        if paired:
            quiet["subaccount_transfer"] += paired
        for row, reason in unpaired:
            if reason == "unreadable":
                skips.unreadable(row.line, row.cells, f"Time «{row.time_raw}» or Amount «{row.amount_raw}»")
            else:
                skips.unknown(row.line, row.cells, "Sub-account transfer without its opposite row")

        for reason, count in quiet.items():
            logger.info("XTB rows left out", reason=reason, count=count)

        notices: List[BRIMNotice] = []
        outside = _outside_period(source.open_positions, imported_quantity)
        if outside:
            notices.append(outside)
        if not transactions:
            notices.append(BRIMNotice.coerce("No valid transactions found in file"))

        logger.info("XTB file parsed", transaction_count=len(transactions), notice_count=len(notices) + skips.count(), asset_count=len(extracted))
        return BRIMParseOutput(
            transactions=transactions,
            warnings=[*notices, *skips.notices()],
            validation_issues=validation_issues,
            extracted_assets=extracted,
        )


def _pair_transfers(rows: List[_Row]) -> Tuple[int, List[Tuple[_Row, str]]]:
    """Match each sub-account transfer with its opposite (same size, other sign, within ``PAIR_WINDOW_SECONDS``).

    A pair moves money between two sub-accounts of the same account: nothing changes for the account, so both rows are
    left out (a known reason). A row without its opposite is returned with ``"unpaired"``; one whose time or amount
    cannot be read with ``"unreadable"``.
    """
    readable = [row for row in rows if row.time is not None and row.amount is not None and row.amount != 0]
    readable_ids = {id(row) for row in readable}
    result: List[Tuple[_Row, str]] = [(row, "unreadable") for row in rows if id(row) not in readable_ids]
    readable.sort(key=lambda row: row.time)  # type: ignore[arg-type, return-value]
    used: set[int] = set()
    pairs = 0
    for i, row in enumerate(readable):
        if i in used:
            continue
        for j in range(i + 1, len(readable)):
            other = readable[j]
            if (other.time - row.time).total_seconds() > PAIR_WINDOW_SECONDS:  # type: ignore[operator]
                break
            if j not in used and other.amount == -row.amount:  # type: ignore[operator]
                used.update({i, j})
                pairs += 2
                break
    result.extend((row, "unpaired") for i, row in enumerate(readable) if i not in used)
    result.sort(key=lambda item: item[0].line)
    return pairs, result


def _plain(value: Decimal) -> str:
    """A quantity as plain text, without exponent or trailing zeros."""
    text = format(value.normalize(), "f")
    return "0" if text in ("-0", "") else text


def _outside_period(positions: List[wb.OpenPosition], imported: Dict[str, Decimal]) -> Optional[BRIMNotice]:
    """An info note when the open volume of an instrument differs from the net quantity this report imports for it.

    The open volume of a ticker is the sum of its aggregate rows (one per sub-account that holds it). CFDs are not
    imported, so they are not compared.
    """
    by_ticker: Dict[str, List[wb.OpenPosition]] = {}
    for position in positions:
        if "CFD" not in position.category.upper():
            by_ticker.setdefault(position.ticker, []).append(position)
    differing = []
    for ticker, rows in by_ticker.items():
        volume = sum((row.volume for row in rows), Decimal("0"))
        if volume != imported.get(ticker, Decimal("0")):
            differing.append((rows[0], volume))
    if not differing:
        return None
    evidence = BRIMEvidence(
        title="",
        headers=["Ticker", "Instrument", "Open volume", "Imported quantity"],
        rows=[[p.ticker, p.name, _plain(volume), _plain(imported.get(p.ticker, Decimal("0")))] for p, volume in differing],
        row_numbers=[p.line for p, _ in differing],
        comment=OUTSIDE_PERIOD_COMMENT,
    )
    return BRIMNotice(
        severity="info",
        code=OUTSIDE_PERIOD_CODE,
        message=OUTSIDE_PERIOD_MESSAGE.format(n=len(differing)),
        evidence=[evidence],
        context={"count": len(differing)},
    )
