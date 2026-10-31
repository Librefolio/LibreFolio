"""Crédit Agricole: reading the two exports as rows, and what the XLSX header (the testata) says.

Two exports, each in CSV or XLSX, each possibly downloaded several times:

- the securities movements, "Lista Movimenti Deposito Titoli" (role ``securities``): one row per coupon, purchase,
  redemption, maturity or transfer, dated by ``Data operazione`` and settled on ``Data valuta``;
- the account movements, "Lista Movimenti Conto" (role ``account``): every cash movement, dated by ``Data Op.`` and settled
  on ``Data Val.``.

Only the XLSX carries a header above the table (the testata): for the account the opening and closing balance and the
period they refer to, for the securities the dossier, the supporting account and the cash. The CSV has none.

Nothing here classifies a row into a transaction, pairs rows of the two exports or builds a truth point: that is
``_report_set.py``. This module reads, and keeps every figure as the file wrote it (``cells``) next to the parsed value.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from backend.app.services.brim import brim_report_set_core as core
from backend.app.services.brim_providers import _brim_io as io
from backend.app.services.brim_providers.broker_credit_agricole._classify import is_recap_footer, resolve_currency

ROLE_SECURITIES = "securities"
ROLE_ACCOUNT = "account"

SECURITIES_HEADER = ("Data operazione", "Causale", "Quantità")
ACCOUNT_HEADER = ("Data Op.", "Descrizione", "Importo")

#: Columns kept verbatim for each row, in the order the combined file writes them (the file's own spelling).
SECURITIES_COLUMNS = ("Data operazione", "Data valuta", "Nome", "Causale", "Prezzo", "Quantità", "Controvalore", "Divisa")
ACCOUNT_COLUMNS = ("Data Op.", "Data Val.", "Causale", "Descrizione", "Importo", "Divisa")

_SECURITIES_COLUMN_LABELS = {
    "date": ["Data operazione"],
    "value": ["Data valuta"],
    "name": ["Nome"],
    "causale": ["Causale"],
    "price": ["Prezzo"],
    "qty": ["Quantità"],
    "ctv": ["Controvalore in Euro", "Ctv in Eur"],
}
_ACCOUNT_COLUMN_LABELS = {
    "date": ["Data Op."],
    "value": ["Data Val."],
    "causale": ["Causale"],
    "descrizione": ["Descrizione"],
    "importo": ["Importo"],
    "divisa": ["Divisa"],
}

_CENT = core.CENT
_HEADER_SCAN_ROWS = 60

#: Account row classes that are not a booked movement: the row is read, shown, and never imported.
KLASS_INVALID = "invalid"


# =============================================================================
# THE ROWS
# =============================================================================


@dataclass
class Outcome:
    """What the set does with a row: ``pair``, ``standalone`` or ``excluded`` (with the reason), and in which zone."""

    kind: str = ""
    zone: str = ""
    reason: str = ""


@dataclass(eq=False)
class SecuritiesRow:
    file_index: int
    file_count: int
    row: int
    op: date
    value: Optional[date]
    name: str
    causale: str
    price: Optional[Decimal]
    qty: Optional[Decimal]
    ctv: Optional[Decimal]
    currency: str
    cells: Dict[str, str]
    klass: str = ""
    outcome: Outcome = field(default_factory=Outcome)

    @property
    def day(self) -> date:
        return self.op

    @property
    def source(self) -> str:
        return core.source(ROLE_SECURITIES, self.file_index, self.file_count, self.row)

    @property
    def signature(self) -> Tuple[Any, ...]:
        """Two downloads of the same bank row have the same signature (the CSV and the XLSX of one export included)."""
        return (self.op, self.value, core.norm(self.name), self.causale, self.price, self.qty, self.ctv, self.currency)

    @property
    def trade_signature(self) -> Tuple[Any, ...]:
        """What the row imports, whichever account row it is paired with."""
        return (self.klass, core.norm(self.name), self.op, self.qty, self.ctv, self.currency)


@dataclass(eq=False)
class AccountRow:
    file_index: int
    file_count: int
    row: int
    op: date
    value: Optional[date]
    causale: str
    description: str
    amount: Optional[Decimal]
    currency: str
    cells: Dict[str, str]
    klass: str = ""
    tier: str = ""
    outcome: Outcome = field(default_factory=Outcome)

    @property
    def day(self) -> date:
        return self.op

    @property
    def source(self) -> str:
        return core.source(ROLE_ACCOUNT, self.file_index, self.file_count, self.row)

    @property
    def signature(self) -> Tuple[Any, ...]:
        return (self.op, self.value, self.causale, core.norm(self.description), self.amount, self.currency)


# =============================================================================
# THE TESTATA (the header above the table of an XLSX)
# =============================================================================

_DATE_TEXT_RE = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{1,5})")
_MONEY_TEXT_RE = re.compile(r"^(?P<number>[-+]?\s*[\d.,]+)\s*(?P<currency>[A-Za-z]{3})?$")


def parse_testata_date(value: Any) -> Optional[date]:
    """A date of the testata. It also reads the five-digit year the securities header writes (``25/07/02026``): only here, never in a row."""
    if isinstance(value, (date,)) or value is None:
        return io.to_date(value)
    match = _DATE_TEXT_RE.search(str(value))
    if match is None:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_testata_money(value: Any) -> Tuple[Optional[Decimal], Optional[str]]:
    """``(amount, currency code)`` of ``2984,99 EUR`` or of a number in a cell of its own."""
    if value is None:
        return None, None
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return io.to_decimal_it(value), None
    match = _MONEY_TEXT_RE.match(str(value).strip())
    if match is None:
        return None, None
    currency = match.group("currency")
    return io.to_decimal_it(match.group("number")), currency.upper() if currency else None


def _label_value(rows: Sequence[Sequence[Any]], label: str) -> Any:
    """What the testata says after ``label``: the rest of its own cell (``Saldo Iniziale 2984,99 EUR``), or else the next filled cell of the row.

    ``None`` when the label is not there or has nothing after it.
    """
    # A word boundary closes a label that ends in a letter; a label that ends in a dot ("Dossier n.") has none to close it.
    boundary = r"\b" if label[-1].isalnum() else ""
    pattern = re.compile(r"^\s*" + re.escape(label) + boundary + r"\s*:?\s*(?P<rest>.*)$", re.IGNORECASE | re.DOTALL)
    for row in rows:
        for index, cell in enumerate(row):
            match = pattern.match(io.cell_str(cell))
            if match is None:
                continue
            rest = match.group("rest").strip()
            if rest:
                return rest
            for after in row[index + 1 :]:
                if io.cell_str(after):
                    return after
    return None


@dataclass(frozen=True)
class Testata:
    """What the header of an XLSX states; every field is ``None`` (or empty) when the file does not say it."""

    opening: Optional[Decimal] = None
    closing: Optional[Decimal] = None
    currency: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    dossier: str = ""
    support_account: str = ""
    liquidity: Optional[Decimal] = None
    liquidity_currency: Optional[str] = None
    updated: Optional[date] = None

    @property
    def has_balances(self) -> bool:
        return self.opening is not None and self.closing is not None and self.date_from is not None and self.date_to is not None

    @property
    def declared(self) -> Optional[Tuple[date, date]]:
        if self.date_from is not None and self.date_to is not None and self.date_from <= self.date_to:
            return self.date_from, self.date_to
        return None


def read_testata(rows: Sequence[Sequence[Any]], header_idx: int) -> Testata:
    """The testata of the rows above the table's header row."""
    above = rows[:header_idx]
    opening, opening_currency = _parse_testata_money(_label_value(above, "Saldo Iniziale"))
    closing, closing_currency = _parse_testata_money(_label_value(above, "Saldo Finale"))
    liquidity, liquidity_currency = _parse_testata_money(_label_value(above, "Liquidità"))
    return Testata(
        opening=opening,
        closing=closing,
        currency=opening_currency or closing_currency,
        date_from=parse_testata_date(_label_value(above, "Data dal")),
        date_to=parse_testata_date(_label_value(above, "Data al")),
        dossier=io.cell_str(_label_value(above, "Dossier n.")),
        support_account=io.cell_str(_label_value(above, "C/C di appoggio")),
        liquidity=liquidity,
        liquidity_currency=liquidity_currency,
        updated=parse_testata_date(_label_value(above, "Data Aggiornamento")),
    )


def account_fingerprint(testata: Testata) -> Optional[str]:
    """An opaque key of the dossier and supporting account the header names; ``None`` when it names none.

    Compared in memory only (two securities exports of different dossiers do not combine); the numbers themselves are
    never copied anywhere.
    """
    if not testata.dossier and not testata.support_account:
        return None
    return hashlib.sha256(f"{testata.dossier}|{testata.support_account}".encode()).hexdigest()


# =============================================================================
# THE FILES
# =============================================================================


@dataclass
class SecuritiesFile:
    path: Path
    rows: List[SecuritiesRow]
    testata: Testata


@dataclass
class AccountFile:
    path: Path
    rows: List[AccountRow]
    testata: Testata

    @property
    def row_span(self) -> Optional[Tuple[date, date]]:
        return core.coverage(self.rows, lambda row: row.op)

    @property
    def chain_closes(self) -> Optional[bool]:
        """Whether ``opening + the sum of the file's rows = closing``, to the cent; ``None`` when the file states no balances.

        A row whose amount cannot be read is no sum: the chain of a file that has one is not checked.
        """
        testata = self.testata
        if testata.opening is None or testata.closing is None or any(row.amount is None for row in self.rows):
            return None
        total = sum((row.amount for row in self.rows if row.amount is not None), Decimal("0"))
        return abs(testata.opening + total - testata.closing) <= _CENT


def _read_table(path: Path) -> List[List[Any]]:
    return io.read_rows(path)


def _date_text(value: Any, parsed: Optional[date]) -> str:
    """A date cell as ``dd/mm/yyyy``: an XLSX date cell would print as ``2024-07-01 00:00:00``, which the combined file could not read back."""
    return parsed.strftime("%d/%m/%Y") if parsed is not None else io.cell_str(value)


def _number_text(value: Any, *, italian: bool) -> str:
    """A number cell the way the file's own convention writes it, so that the combined file reads back the same figure.

    A numeric XLSX cell prints with a dot (``1234.56``), which an Italian column (``Prezzo``, ``Controvalore``, ``Importo``) would
    read as a thousands separator; a text cell is the file's own and stays as it is.
    """
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        text = format(Decimal(str(value)), "f")
        return text.replace(".", ",") if italian else text
    return io.cell_str(value)


def read_securities(path: Path, file_index: int = 1, file_count: int = 1) -> SecuritiesFile:
    """The securities rows of one export. A row without a date or a causale, a blank row and the recap footer are not rows."""
    rows = _read_table(path)
    header_idx = io.find_header_row(rows, SECURITIES_HEADER, max_scan=_HEADER_SCAN_ROWS)
    if header_idx is None:
        return SecuritiesFile(path=path, rows=[], testata=Testata())
    col = io.build_col_index(rows[header_idx], _SECURITIES_COLUMN_LABELS)
    divisa_cols = [index for index, cell in enumerate(rows[header_idx]) if "divisa" in io.cell_str(cell).lower()]
    parsed: List[SecuritiesRow] = []
    for offset, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
        if io.is_blank_row(row):
            continue
        day = io.to_date(io.row_get(row, col, "date"))
        causale = io.cell_str(io.row_get(row, col, "causale")).upper()
        name = io.cell_str(io.row_get(row, col, "name"))
        if day is None and is_recap_footer(name):
            continue
        if day is None or not causale:
            continue
        currency = resolve_currency(row, divisa_cols)
        cells = {
            "Data operazione": _date_text(io.row_get(row, col, "date"), day),
            "Data valuta": _date_text(io.row_get(row, col, "value"), io.to_date(io.row_get(row, col, "value"))),
            "Nome": name,
            "Causale": causale,
            "Prezzo": _number_text(io.row_get(row, col, "price"), italian=True),
            "Quantità": _number_text(io.row_get(row, col, "qty"), italian=False),
            "Controvalore": _number_text(io.row_get(row, col, "ctv"), italian=True),
            "Divisa": currency,
        }
        parsed.append(
            SecuritiesRow(
                file_index=file_index,
                file_count=file_count,
                row=offset,
                op=day,
                value=io.to_date(io.row_get(row, col, "value")),
                name=name,
                causale=causale,
                price=io.to_decimal_it(io.row_get(row, col, "price")),
                qty=io.to_decimal_plain(io.row_get(row, col, "qty")),
                ctv=io.to_decimal_it(io.row_get(row, col, "ctv")),
                currency=currency,
                cells=cells,
            )
        )
    return SecuritiesFile(path=path, rows=parsed, testata=read_testata(rows, header_idx))


def read_account(path: Path, file_index: int = 1, file_count: int = 1) -> AccountFile:
    """The account rows of one export. A zero amount is no movement and is left out, as the plugin has always done."""
    rows = _read_table(path)
    header_idx = io.find_header_row(rows, ACCOUNT_HEADER, max_scan=_HEADER_SCAN_ROWS)
    if header_idx is None:
        return AccountFile(path=path, rows=[], testata=Testata())
    col = io.build_col_index(rows[header_idx], _ACCOUNT_COLUMN_LABELS)
    parsed: List[AccountRow] = []
    for offset, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):
        if io.is_blank_row(row):
            continue
        day = io.to_date(io.row_get(row, col, "date"))
        causale = io.cell_str(io.row_get(row, col, "causale")).upper()
        description = io.cell_str(io.row_get(row, col, "descrizione"))
        if day is None and is_recap_footer(description):
            continue
        if day is None or not causale:
            continue
        amount = io.to_decimal_it(io.row_get(row, col, "importo"))
        if amount == 0:
            continue
        currency = io.cell_str(io.row_get(row, col, "divisa")) or "EUR"
        cells = {
            "Data Op.": _date_text(io.row_get(row, col, "date"), day),
            "Data Val.": _date_text(io.row_get(row, col, "value"), io.to_date(io.row_get(row, col, "value"))),
            "Causale": causale,
            "Descrizione": description,
            "Importo": _number_text(io.row_get(row, col, "importo"), italian=True),
            "Divisa": currency,
        }
        parsed.append(
            AccountRow(
                file_index=file_index,
                file_count=file_count,
                row=offset,
                op=day,
                value=io.to_date(io.row_get(row, col, "value")),
                causale=causale,
                description=description,
                amount=amount,
                currency=currency,
                cells=cells,
            )
        )
    return AccountFile(path=path, rows=parsed, testata=read_testata(rows, header_idx))


def securities_from_cells(cells: Dict[str, str], line: int) -> Optional[SecuritiesRow]:
    """A securities row read back from the cells the combined file keeps (``None`` when it has no date or no causale)."""
    day = io.to_date(cells.get("Data operazione"))
    causale = cells.get("Causale", "").strip().upper()
    if day is None or not causale:
        return None
    return SecuritiesRow(
        file_index=1,
        file_count=1,
        row=line,
        op=day,
        value=io.to_date(cells.get("Data valuta")),
        name=cells.get("Nome", "").strip(),
        causale=causale,
        price=io.to_decimal_it(cells.get("Prezzo")),
        qty=io.to_decimal_plain(cells.get("Quantità")),
        ctv=io.to_decimal_it(cells.get("Controvalore")),
        currency=cells.get("Divisa", "").strip() or "EUR",
        cells=dict(cells),
    )


def account_from_cells(cells: Dict[str, str], line: int) -> Optional[AccountRow]:
    """An account row read back from the cells the combined file keeps (``None`` when it has no date or no causale)."""
    day = io.to_date(cells.get("Data Op."))
    causale = cells.get("Causale", "").strip().upper()
    if day is None or not causale:
        return None
    return AccountRow(
        file_index=1,
        file_count=1,
        row=line,
        op=day,
        value=io.to_date(cells.get("Data Val.")),
        causale=causale,
        description=cells.get("Descrizione", "").strip(),
        amount=io.to_decimal_it(cells.get("Importo")),
        currency=cells.get("Divisa", "").strip() or "EUR",
        cells=dict(cells),
    )


# =============================================================================
# ROLES AND MEMBERS
# =============================================================================


def detect_role(path: Path) -> Optional[str]:
    """``securities`` or ``account`` for an export this plugin combines, else ``None``.

    A combined file this plugin wrote (it carries the ``lf_row_kind`` column) is not an original and has no role.
    """
    if path.suffix.lower() not in (".csv", ".xlsx"):
        return None
    try:
        rows = _read_table(path)
    except Exception:  # noqa: BLE001 — a file that cannot be read is no export of ours: the answer is "no role"
        return None
    head = rows[:_HEADER_SCAN_ROWS]
    if any(io.cell_str(cell).lower() == "lf_row_kind" for row in head for cell in row):
        return None
    if io.find_header_row(head, SECURITIES_HEADER, max_scan=_HEADER_SCAN_ROWS) is not None:
        return ROLE_SECURITIES
    if io.find_header_row(head, ACCOUNT_HEADER, max_scan=_HEADER_SCAN_ROWS) is not None:
        return ROLE_ACCOUNT
    return None
