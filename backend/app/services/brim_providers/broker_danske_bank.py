"""
Danske Bank (Finland) report-set import plugin.

An equity savings account (osakesäästötili) at Danske Bank is exported as two files, and
neither is enough on its own:

- the custody transactions (XLSX, at most one year): trades with quantity and price,
  income (``Tuotto``) and demergers (``Jakautuminen``), but no deposit and no balance;
- the cash statement (CSV, at most five years): every cash movement with the running
  balance, but no quantity.

This is a report-set plugin: the exports uploaded together are combined into one derived
file (``combine``), and that file is what ``parse`` imports. The combined file pairs each
trade with its cash movement, states where every row goes and why (the ``lf_*`` columns),
and carries the truth points the bank's files prove: the balance on the eve of each
custody period, the positions some rows reveal, and a final balance to compare.

Design: ``LibreFolio_developer_journal/Release_2/Phase_0/26_brimDanskeBank/design-phase00BrimReportSets.md``
(sections 3.4 and 7.1); implementation choices in
``plan-phase00BrimDanskeBankStep4Implementation.prompt.md`` (section 4, B0).
"""

from __future__ import annotations

import csv
import hashlib
import io
import re
import warnings
from bisect import bisect_right
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from itertools import groupby, permutations
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import openpyxl
import structlog

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import (
    FAKE_ASSET_ID_BASE,
    BRIMAbsorbed,
    BRIMAbsorbedRow,
    BRIMCheckpoint,
    BRIMCombinedTable,
    BRIMCoverage,
    BRIMEvidence,
    BRIMExtractedAssetInfo,
    BRIMFieldTodo,
    BRIMMemberSummary,
    BRIMNotice,
    BRIMParseOutput,
    BRIMReportRole,
    BRIMSetShape,
    BRIMTruthCash,
    BRIMTruthPosition,
    BRIMValidationIssue,
    BRIMVerification,
)
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider, BRIMSetRequiredError
from backend.app.services.provider_registry import BRIMProviderRegistry, register_provider

logger = structlog.get_logger(__name__)

PROVIDER_CODE = "broker_danske_bank"
HISTORY_TAG = "danske_bank"
# The equity savings cash account is in euro, and the cash statement has no currency column.
CURRENCY = "EUR"
LAG_BUSINESS_DAYS = 5
PROOF_WINDOW_DAYS = 30
MAX_MATCH_CANDIDATES = 8
CENT = Decimal("0.01")
ZERO = Decimal("0")

CUSTODY_COLUMNS = ("Kauppapäivä", "Arvopäivä", "Sijoituskohde", "Määrä", "Kurssi", "Palkkio<br/>sis. Alv", "Summa", "H", "Tila", "Toimeksiantotyyppi")
CASH_COLUMNS = ("Pvm", "Saaja/Maksaja", "Määrä", "Saldo", "Tila", "Tarkastus")
LF_COLUMNS = ("lf_row_kind", "lf_zone", "lf_reason", "lf_checkpoint", "lf_source", "lf_match_key", "lf_value", "lf_currency", "lf_proof")
COMBINED_HEADERS = [*LF_COLUMNS, *(f"custody:{column}" for column in CUSTODY_COLUMNS), *(f"cash:{column}" for column in CASH_COLUMNS)]
_COMBINED_MARKERS = ("lf_row_kind", "lf_source", "custody:Toimeksiantotyyppi", "cash:Saaja/Maksaja")

# Normalised header -> column name in the combined file. The account column is read for
# the account check only and is never copied (it is an account number).
_ACCOUNT = "Säilytystili"
_CUSTODY_HEADERS = {
    "kauppapäivä": "Kauppapäivä",
    "arvopäivä": "Arvopäivä",
    "sijoituskohde": "Sijoituskohde",
    "määrä": "Määrä",
    "kurssi": "Kurssi",
    "palkkio sis. alv": "Palkkio<br/>sis. Alv",
    "summa": "Summa",
    "valuutta": "H",
    "tila": "Tila",
    "toimeksiantotyyppi": "Toimeksiantotyyppi",
    "säilytystili": _ACCOUNT,
}
_CUSTODY_REQUIRED = {"Kauppapäivä", "Arvopäivä", "Sijoituskohde", "Määrä", "Kurssi", "Summa", "Tila", "Toimeksiantotyyppi"}
_CASH_HEADERS = {"pvm": "Pvm", "saaja/maksaja": "Saaja/Maksaja", "määrä": "Määrä", "saldo": "Saldo", "tila": "Tila", "tarkastus": "Tarkastus"}
_CASH_REQUIRED = {"Pvm", "Saaja/Maksaja", "Määrä", "Saldo", "Tila"}
_HEADER_SCAN_ROWS = 20

_CUSTODY_BOOKED = "toteutettu"
_CASH_BOOKED = "toteutunut"
_RESERVATION = "varaus"
_ORDER_TYPES = {"rajakurssi", "päivän kurssi", "pikakauppa"}
_INCOME = "tuotto"
_DEMERGER_OLD = "jakautuminen, vanha"
_DEMERGER_NEW = "jakautuminen, uusi"

# First word of a standalone cash label -> (class, sign the amount must have).
_CASH_FAMILIES = {"nosto": ("withdrawal", -1), "vero": ("tax", -1), "korko": ("interest", 1), "hyvityskorko": ("interest", 1)}
_FEE_PREFIX = "palvelumaksu"
_STANDALONE_TYPES = {
    "deposit": TransactionType.DEPOSIT,
    "withdrawal": TransactionType.WITHDRAWAL,
    "tax": TransactionType.TAX,
    "fee": TransactionType.FEE,
    "interest": TransactionType.INTEREST,
}
_PAIRED = ("buy", "sell", "income")
_MOVEMENTS = ("buy", "sell", "demerger_old", "demerger_new")
_TRUTH_KINDS = ("truth_cash", "truth_position", "verification")
_EXCLUDED_ORDER = ("no_counterpart", "ambiguous", "not_yet_settled", "outside_cash_coverage", "status", "unknown_type", "invalid", "superseded")

_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_SPACES_RE = re.compile(r"\s+")
_DATE_RE = re.compile(r"^(\d{1,2})\.(\d{1,2})\.(\d{4})$")
_REFERENCE_RE = re.compile(r"^(?P<name>.*\S)\s+(?P<ref>\d{10})$")


# =============================================================================
# TEXT, NUMBERS AND DATES
# =============================================================================


def _norm(value: Any) -> str:
    """Case- and space-insensitive form of a header or a name (``<br/>`` counts as a space)."""
    if value is None:
        return ""
    return _SPACES_RE.sub(" ", _BR_RE.sub(" ", str(value))).strip().casefold()


def _plain(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return "0" if text in ("", "-0") else text


def _cell_text(value: Any) -> str:
    """A spreadsheet cell as text: dates as ``dd.mm.yyyy``, numbers in their shortest decimal form."""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.strftime("%d.%m.%Y")
    if isinstance(value, float):
        return _plain(Decimal(repr(value)))
    if isinstance(value, Decimal):
        return _plain(value)
    return str(value).strip()


def _to_date(text: str) -> Optional[date]:
    match = _DATE_RE.match(text.strip())
    if match is None:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _to_decimal(text: str) -> Optional[Decimal]:
    """A Finnish or plain number: spaces (also NBSP) as thousands, comma or dot as decimal, Unicode minus."""
    cleaned = text.strip().replace("\u2212", "-")
    for space in (" ", "\u00a0", "\u202f"):
        cleaned = cleaned.replace(space, "")
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    if not cleaned:
        return None
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def _money(value: Decimal) -> str:
    return format(value.quantize(CENT), "f")


def _fi_money(value: Decimal) -> str:
    return _money(value).replace(".", ",")


def _add_business_days(start: date, days: int) -> date:
    """``start`` plus ``days`` weekdays (holidays are not known and not skipped)."""
    current, added = start, 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def _compatible(first: str, second: str) -> bool:
    """Two names of the same security: the cash statement truncates its labels, so one is a prefix of the other."""
    a, b = _norm(first), _norm(second)
    return bool(a) and bool(b) and (a.startswith(b) or b.startswith(a))


def _source(role: str, file_index: int, file_count: int, row: int) -> str:
    return f"{role}:{row}" if file_count == 1 else f"{role}#{file_index}:{row}"


# =============================================================================
# SOURCE ROWS
# =============================================================================


@dataclass(eq=False)
class _Outcome:
    kind: str = ""
    zone: str = ""
    reason: str = ""
    checkpoint: Optional[date] = None


@dataclass(eq=False)
class _CustodyRow:
    file_index: int
    file_count: int
    row: int
    cells: Dict[str, str]
    account: str
    trade: Optional[date]
    value: Optional[date]
    name: str
    qty: Optional[Decimal]
    price: Optional[Decimal]
    summa: Optional[Decimal]
    currency: str
    klass: str = ""
    outcome: _Outcome = field(default_factory=_Outcome)

    @property
    def source(self) -> str:
        return _source("custody", self.file_index, self.file_count, self.row)

    @property
    def signature(self) -> Tuple[str, ...]:
        return tuple(self.cells[column] for column in CUSTODY_COLUMNS)

    @property
    def title(self) -> str:
        return _norm(self.name)

    @property
    def order_type(self) -> str:
        return self.cells["Toimeksiantotyyppi"]

    @property
    def trade_signature(self) -> Tuple[Any, ...]:
        return (self.title, self.qty, self.price, self.trade, _norm(self.order_type))

    @property
    def day(self) -> Optional[date]:
        return self.value or self.trade


@dataclass(eq=False)
class _CashRow:
    file_index: int
    file_count: int
    row: int
    cells: Dict[str, str]
    value: Optional[date]
    label: str
    amount: Optional[Decimal]
    saldo: Optional[Decimal]
    status: str
    klass: str = ""
    name: str = ""
    outcome: _Outcome = field(default_factory=_Outcome)

    @property
    def source(self) -> str:
        return _source("cash", self.file_index, self.file_count, self.row)

    @property
    def signature(self) -> Tuple[str, ...]:
        return tuple(self.cells[column] for column in CASH_COLUMNS)

    @property
    def day(self) -> Optional[date]:
        return self.value


def _xlsx_rows(path: Path, limit: Optional[int] = None) -> List[List[Any]]:
    """Rows of the first worksheet with data, from row 1 (values only)."""
    with warnings.catch_warnings():
        # openpyxl warns about harmless things in bank exports (default styles, print areas).
        warnings.simplefilter("ignore")
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        for sheet in workbook.worksheets:
            rows = _sheet_rows(sheet, limit)
            if any(cell not in (None, "") for row in rows for cell in row):
                return rows
        return []
    finally:
        workbook.close()


def _sheet_rows(sheet: Any, limit: Optional[int]) -> List[List[Any]]:
    rows: List[List[Any]] = []
    for row in sheet.iter_rows(min_row=1, values_only=True):
        rows.append(list(row))
        if limit is not None and len(rows) >= limit:
            break
    return rows


def _csv_rows(path: Path) -> List[List[str]]:
    with BRIMProvider._open_text(path, newline="") as handle:
        return [list(row) for row in csv.reader(handle, delimiter=";")]


def _layout(header: Sequence[Any], names: Dict[str, str], required: Set[str]) -> Optional[Dict[str, int]]:
    columns: Dict[str, int] = {}
    for index, cell in enumerate(header):
        name = names.get(_norm(cell))
        if name is not None and name not in columns:
            columns[name] = index
    return columns if required <= columns.keys() else None


def _custody_layout(header: Sequence[Any]) -> Optional[Dict[str, int]]:
    columns = _layout(header, _CUSTODY_HEADERS, _CUSTODY_REQUIRED)
    if columns is None:
        return None
    # The currency of Summa sits in the column right after it, with no header.
    after = columns["Summa"] + 1
    if "H" not in columns and after < len(header) and _norm(header[after]) == "":
        columns["H"] = after
    return columns


def _cash_layout(header: Sequence[Any]) -> Optional[Dict[str, int]]:
    return _layout(header, _CASH_HEADERS, _CASH_REQUIRED)


def _find_layout(rows: Sequence[Sequence[Any]], layout: Callable[[Sequence[Any]], Optional[Dict[str, int]]]) -> Optional[Tuple[int, Dict[str, int]]]:
    for index, row in enumerate(rows[:_HEADER_SCAN_ROWS]):
        columns = layout(row)
        if columns is not None:
            return index, columns
    return None


def _read_custody(path: Path, file_index: int, file_count: int) -> List[_CustodyRow]:
    rows = _xlsx_rows(path)
    found = _find_layout(rows, _custody_layout)
    if found is None:
        raise BRIMParseError("Not a Danske Bank custody export: the transaction columns are missing")
    header_index, columns = found
    result = []
    for index in range(header_index + 1, len(rows)):
        raw = rows[index]
        if all(_cell_text(cell) == "" for cell in raw):
            continue
        cells = {name: _cell_text(raw[position]) if position < len(raw) else "" for name, position in columns.items()}
        result.append(_custody_row(cells, file_index, file_count, index + 1))
    return result


def _custody_row(cells: Dict[str, str], file_index: int, file_count: int, row: int) -> _CustodyRow:
    account = cells.pop(_ACCOUNT, "")
    for column in CUSTODY_COLUMNS:
        cells.setdefault(column, "")
    return _CustodyRow(
        file_index=file_index,
        file_count=file_count,
        row=row,
        cells=cells,
        account=account,
        trade=_to_date(cells["Kauppapäivä"]),
        value=_to_date(cells["Arvopäivä"]),
        name=cells["Sijoituskohde"],
        qty=_to_decimal(cells["Määrä"]),
        price=_to_decimal(cells["Kurssi"]),
        summa=_to_decimal(cells["Summa"]),
        currency=(cells["H"] or CURRENCY).upper(),
    )


def _read_cash(path: Path, file_index: int, file_count: int) -> List[_CashRow]:
    rows = _csv_rows(path)
    found = _find_layout(rows, _cash_layout)
    if found is None:
        raise BRIMParseError("Not a Danske Bank cash statement: the account columns are missing")
    header_index, columns = found
    result = []
    for index in range(header_index + 1, len(rows)):
        raw = rows[index]
        if all(cell.strip() == "" for cell in raw):
            continue
        cells = {name: raw[position].strip() if position < len(raw) else "" for name, position in columns.items()}
        for column in CASH_COLUMNS:
            cells.setdefault(column, "")
        result.append(
            _CashRow(
                file_index=file_index,
                file_count=file_count,
                row=index + 1,
                cells=cells,
                value=_to_date(cells["Pvm"]),
                label=cells["Saaja/Maksaja"],
                amount=_to_decimal(cells["Määrä"]),
                saldo=_to_decimal(cells["Saldo"]),
                status=cells["Tila"],
            )
        )
    return result


def _csv_kind(path: Path) -> Optional[str]:
    head = BRIMProvider._read_file_head(path, num_lines=_HEADER_SCAN_ROWS)
    rows = list(csv.reader(io.StringIO(head), delimiter=";"))
    if rows and all(marker in [cell.strip().lstrip("\ufeff") for cell in rows[0]] for marker in _COMBINED_MARKERS):
        return "combined"
    return "cash" if _find_layout(rows, _cash_layout) is not None else None


def _file_kind(path: Path) -> Optional[str]:
    """``custody``, ``cash``, ``combined`` or None; an unreadable file is simply not ours."""
    suffix = path.suffix.lower()
    try:
        if suffix in (".xlsx", ".xlsm"):
            return "custody" if _find_layout(_xlsx_rows(path, limit=_HEADER_SCAN_ROWS), _custody_layout) is not None else None
        if suffix == ".csv":
            return _csv_kind(path)
    except Exception as exc:  # any read error means "not a Danske export"
        logger.debug("Danske Bank detection failed", error=type(exc).__name__)
        return None
    return None


# =============================================================================
# CLASSES (S1)
# =============================================================================


def _trade_class(row: _CustodyRow) -> str:
    if row.summa is None or row.price is None:
        return "invalid"
    if row.qty > 0 and row.summa < 0:
        return "buy"
    if row.qty < 0 and row.summa > 0:
        return "sell"
    return "invalid"


def _income_class(row: _CustodyRow) -> str:
    return "income" if row.qty > 0 and row.summa is not None and row.summa > 0 else "invalid"


def _old_line_class(row: _CustodyRow) -> str:
    return "demerger_old" if row.qty < 0 and row.summa is None else "invalid"


def _new_line_class(row: _CustodyRow) -> str:
    return "demerger_new" if row.qty > 0 and row.summa is None else "invalid"


_EVENT_CLASSES: Dict[str, Callable[[_CustodyRow], str]] = {_INCOME: _income_class, _DEMERGER_OLD: _old_line_class, _DEMERGER_NEW: _new_line_class}


def _classify_custody(row: _CustodyRow) -> str:
    if _norm(row.cells["Tila"]) != _CUSTODY_BOOKED:
        return "status"
    if row.trade is None or row.value is None or not row.name or not row.qty or row.value < row.trade:
        return "invalid"
    order_type = _norm(row.order_type)
    if order_type in _ORDER_TYPES:
        return _trade_class(row)
    classify = _EVENT_CLASSES.get(order_type)
    return classify(row) if classify is not None else "unknown_type"


def _standalone_class(word: str, amount: Decimal) -> Tuple[str, str]:
    family = _CASH_FAMILIES.get(word)
    if family is None and word.startswith(_FEE_PREFIX):
        family = ("fee", -1)
    if family is not None:
        klass, sign = family
        return (klass, "") if (amount > 0) == (sign > 0) else ("unknown_type", "")
    # Only the holder can pay money into an equity savings account.
    return ("deposit", "") if amount > 0 else ("unknown_type", "")


def _cash_label_class(label: str, amount: Decimal) -> Tuple[str, str]:
    """Class and security name of a booked cash row, from its label and its sign."""
    text = _SPACES_RE.sub(" ", label).strip()
    first, _, rest = text.partition(" ")
    word = first.casefold()
    if word == "osto" and rest:
        return ("buy", rest) if amount < 0 else ("unknown_type", "")
    if word == "myynti" and rest:
        return ("sell", rest) if amount > 0 else ("unknown_type", "")
    match = _REFERENCE_RE.match(text)
    if match is not None and amount > 0:
        return "income", match.group("name")
    return _standalone_class(word, amount)


def _classify_cash(row: _CashRow) -> Tuple[str, str]:
    if _norm(row.status) != _CASH_BOOKED or _norm(row.label) == _RESERVATION:
        return "status", ""
    if row.value is None or not row.amount:
        return "invalid", ""
    return _cash_label_class(row.label, row.amount)


# =============================================================================
# RULE M: SEVERAL FILES OF ONE ROLE
# =============================================================================


def _coverage(rows: Iterable[Any], day_of: Callable[[Any], Optional[date]]) -> Optional[Tuple[date, date]]:
    days = [day for day in (day_of(row) for row in rows) if day is not None]
    return (min(days), max(days)) if days else None


def _by_day(rows: Iterable[Any], day_of: Callable[[Any], Optional[date]]) -> Dict[date, List[Any]]:
    groups: Dict[date, List[Any]] = defaultdict(list)
    for row in rows:
        day = day_of(row)
        if day is not None:
            groups[day].append(row)
    return groups


def _same_rows(first: Sequence[Any], second: Sequence[Any]) -> bool:
    return Counter(row.signature for row in first) == Counter(row.signature for row in second)


class _RoleMerge:
    """Rule M (design D-S28): for each day, the rows of the latest file covering it."""

    def __init__(self, files: List[List[Any]], day_of: Callable[[Any], Optional[date]]):
        self.files = files
        self.day_of = day_of
        self.spans = [_coverage(rows, day_of) for rows in files]
        self.order = sorted((index for index, span in enumerate(self.spans) if span), key=lambda index: (self.spans[index][1], self.spans[index][0], index))
        self.groups = [_by_day(rows, day_of) for rows in files]
        self.kept: List[Any] = []
        self.superseded: List[Any] = []
        for index, rows in enumerate(files):
            for row in rows:
                self._place(index, row)
        self.mismatch_days = sorted(self._mismatch_days())

    def _owner(self, day: date) -> int:
        return next(index for index in reversed(self.order) if self.spans[index][0] <= day <= self.spans[index][1])

    def _place(self, index: int, row: Any) -> None:
        day = self.day_of(row)
        owner = index if day is None else self._owner(day)
        if owner == index:
            self.kept.append(row)
        elif not _same_rows(self.groups[index].get(day, []), self.groups[owner].get(day, [])):
            self.superseded.append(row)

    def _mismatch_days(self) -> Set[date]:
        days: Set[date] = set()
        for index, span in enumerate(self.spans):
            if span is None:
                continue
            candidates = {day for groups in self.groups for day in groups if span[0] <= day <= span[1]}
            for day in candidates:
                owner = self._owner(day)
                if owner != index and not _same_rows(self.groups[index].get(day, []), self.groups[owner].get(day, [])):
                    days.add(day)
        return days


# =============================================================================
# PAIRING (S2-S4)
# =============================================================================


def _custody_key(row: _CustodyRow) -> Tuple[Any, ...]:
    return (row.value, row.summa.quantize(CENT), row.currency, row.klass)


def _cash_key(row: _CashRow) -> Tuple[Any, ...]:
    return (row.value, row.amount.quantize(CENT), CURRENCY, row.klass)


def _match_key_text(day: Optional[date], amount: Optional[Decimal], currency: str) -> str:
    if day is None or amount is None:
        return ""
    return f"{day.isoformat()}|{_money(amount)}|{currency}"


def _assignments(custody_count: int, cash_count: int) -> Iterable[List[Tuple[int, int]]]:
    if custody_count <= cash_count:
        for chosen in permutations(range(cash_count), custody_count):
            yield list(zip(range(custody_count), chosen, strict=True))
    else:
        for chosen in permutations(range(custody_count), cash_count):
            yield list(zip(chosen, range(cash_count), strict=True))


def _best_assignment(custody: List[_CustodyRow], cash: List[_CashRow]) -> Optional[List[Tuple[_CustodyRow, _CashRow]]]:
    """The assignment with the most compatible names, if every such assignment imports the same trades."""
    best_weight, outcomes, best = -1, set(), None
    for pairs in _assignments(len(custody), len(cash)):
        weight = sum(_compatible(custody[i].name, cash[j].name) for i, j in pairs)
        outcome = tuple(sorted((custody[i].trade_signature for i, _ in pairs), key=repr))
        if weight > best_weight:
            best_weight, outcomes, best = weight, {outcome}, pairs
        elif weight == best_weight:
            outcomes.add(outcome)
    if best is None or len(outcomes) != 1:
        return None
    return [(custody[i], cash[j]) for i, j in best]


def _assign(custody: List[_CustodyRow], cash: List[_CashRow]) -> Optional[List[Tuple[_CustodyRow, _CashRow]]]:
    """Pairs for one key (value date, amount, currency, direction); None when ambiguous."""
    if len(custody) == 1 and len(cash) == 1:
        return [(custody[0], cash[0])]
    if max(len(custody), len(cash)) > MAX_MATCH_CANDIDATES:
        return None
    if len({row.trade_signature for row in custody}) == 1 and len({_norm(row.label) for row in cash}) == 1:
        return list(zip(custody, cash, strict=False))
    return _best_assignment(custody, cash)


def _pair_rows(custody_rows: List[_CustodyRow], cash_rows: List[_CashRow]) -> Tuple[List[Tuple[_CustodyRow, _CashRow]], List[Any]]:
    custody_by_key: Dict[Tuple[Any, ...], List[_CustodyRow]] = defaultdict(list)
    cash_by_key: Dict[Tuple[Any, ...], List[_CashRow]] = defaultdict(list)
    for row in custody_rows:
        if row.klass in _PAIRED:
            custody_by_key[_custody_key(row)].append(row)
    for row in cash_rows:
        if row.klass in _PAIRED:
            cash_by_key[_cash_key(row)].append(row)
    pairs: List[Tuple[_CustodyRow, _CashRow]] = []
    ambiguous: List[Any] = []
    for key in sorted(custody_by_key.keys() & cash_by_key.keys(), key=repr):
        chosen = _assign(custody_by_key[key], cash_by_key[key])
        if chosen is None:
            ambiguous.extend([*custody_by_key[key], *cash_by_key[key]])
        else:
            pairs.extend(chosen)
    return pairs, ambiguous


# =============================================================================
# SEGMENTS, ZONES AND THE BALANCE CHAIN
# =============================================================================


@dataclass
class _Segment:
    start: date
    end: date
    checkpoint: date
    kind: str
    window_end: date = date.min
    border_end: date = date.min

    @property
    def zone(self) -> str:
        return "before" if self.kind == "opening" else "gap"


def _raw_segments(custody_files: List[List[_CustodyRow]]) -> List[Tuple[date, date]]:
    spans = sorted(span for span in (_coverage(rows, lambda row: row.trade) for rows in custody_files) if span)
    merged: List[Tuple[date, date]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1] + timedelta(days=1):
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _proven_segments(raw: List[Tuple[date, date]], unpaired_cash: List[_CashRow]) -> List[Tuple[date, date]]:
    """Merge two custody periods unless a cash trade without counterpart proves trades in between."""
    segments = raw[:1]
    for start, end in raw[1:]:
        previous_end = segments[-1][1]
        limit = _add_business_days(start - timedelta(days=1), LAG_BUSINESS_DAYS)
        if any(previous_end < row.value <= limit for row in unpaired_cash):
            segments.append((start, end))
        else:
            segments[-1] = (segments[-1][0], end)
    return segments


def _timeline(segments: List[Tuple[date, date]], first_cash: Optional[date]) -> List[_Segment]:
    timeline: List[_Segment] = []
    for index, (start, end) in enumerate(segments):
        checkpoint = start - timedelta(days=1)
        if index == 0 and first_cash is not None and first_cash > start:
            # The cash statement starts after the custody export: the balance is known from the eve of its first row (A13).
            checkpoint = first_cash - timedelta(days=1)
        timeline.append(_Segment(start=start, end=end, checkpoint=checkpoint, kind="opening" if index == 0 else "gap"))
    for index, segment in enumerate(timeline):
        settled = _add_business_days(segment.end, LAG_BUSINESS_DAYS)
        segment.window_end = min(settled, timeline[index + 1].checkpoint) if index + 1 < len(timeline) else settled
        segment.border_end = _add_business_days(segment.checkpoint, LAG_BUSINESS_DAYS)
    return timeline


def _zone(timeline: List[_Segment], day: Optional[date]) -> Tuple[str, int]:
    """Zone of a value date and the segment it belongs to (for a gap: the segment after it)."""
    if day is None or not timeline:
        return "", -1
    if day <= timeline[0].checkpoint:
        return "before", 0
    for index, segment in enumerate(timeline):
        if day <= segment.window_end:
            return "window", index
        if index + 1 < len(timeline) and day <= timeline[index + 1].checkpoint:
            return "gap", index + 1
    return "after", len(timeline) - 1


@dataclass
class _Chain:
    """The running balance of the cash statement, checked day by day."""

    opening: Optional[Decimal] = None
    days: List[date] = field(default_factory=list)
    day_end: Dict[date, Decimal] = field(default_factory=dict)
    last_row: Dict[date, _CashRow] = field(default_factory=dict)
    first_row: Optional[_CashRow] = None
    breaks: List[date] = field(default_factory=list)

    def balance_at(self, day: date) -> Optional[Decimal]:
        index = bisect_right(self.days, day)
        return self.opening if index == 0 else self.day_end[self.days[index - 1]]

    def source_at(self, day: date) -> Optional[_CashRow]:
        index = bisect_right(self.days, day)
        return self.first_row if index == 0 else self.last_row[self.days[index - 1]]

    def covers(self, day: date) -> bool:
        return bool(self.days) and self.days[0] - timedelta(days=1) <= day <= self.days[-1]


def _day_consistent(balance: Decimal, group: List[_CashRow], total: Decimal) -> bool:
    """The rows of one day add up, in file order or at least as a day total."""
    running = balance
    for row in group:
        running += row.amount
        if row.saldo is None or row.saldo != running:
            return total in {row.saldo for row in group}
    return True


def _chain(rows: List[_CashRow]) -> _Chain:
    booked = sorted((row for row in rows if row.klass not in ("status", "invalid")), key=lambda row: (row.value, row.file_index, -row.row))
    if not booked:
        return _Chain()
    first = booked[0]
    chain = _Chain(opening=first.saldo - first.amount if first.saldo is not None else None, first_row=first)
    balance = chain.opening
    for day, grouped in groupby(booked, key=lambda row: row.value):
        group = list(grouped)
        total = (balance if balance is not None else ZERO) + sum((row.amount for row in group), ZERO)
        if balance is None or not _day_consistent(balance, group, total):
            chain.breaks.append(day)
            total = group[-1].saldo if group[-1].saldo is not None else total
        chain.days.append(day)
        chain.day_end[day] = total
        chain.last_row[day] = group[-1]
        balance = total
    return chain


def _cash_spans(cash_files: List[List[_CashRow]]) -> List[Tuple[date, date]]:
    spans = sorted(span for span in (_coverage(rows, lambda row: row.value) for rows in cash_files) if span)
    merged: List[Tuple[date, date]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1] + timedelta(days=1):
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


# =============================================================================
# POSITION PROOFS (E1-E4)
# =============================================================================


@dataclass
class _Proof:
    row: _CustodyRow
    rule: str
    quantity: Optional[Decimal] = None
    exactness: str = "exact"
    reason: str = ""

    @property
    def proof_text(self) -> str:
        if self.reason:
            return f"discarded:{self.rule}:{self.reason}"
        return f"{self.exactness}:{self.rule}"


@dataclass
class _Movement:
    day: date
    trade: date
    order: Tuple[int, int]
    qty: Decimal
    row: _CustodyRow


# =============================================================================
# THE ANALYSIS
# =============================================================================


class _Analysis:
    """Everything the plugin knows about a set: classes, pairs, zones, truth points."""

    def __init__(self, members: Dict[str, List[Path]]):
        custody_paths = list(members.get("custody", []))
        cash_paths = list(members.get("cash", []))
        self.custody_files = [_read_custody(path, index + 1, len(custody_paths)) for index, path in enumerate(custody_paths)]
        self.cash_files = [_read_cash(path, index + 1, len(cash_paths)) for index, path in enumerate(cash_paths)]
        custody_merge = _RoleMerge(self.custody_files, lambda row: row.trade)
        cash_merge = _RoleMerge(self.cash_files, lambda row: row.value)
        self.custody: List[_CustodyRow] = custody_merge.kept
        self.cash: List[_CashRow] = cash_merge.kept
        self.superseded: List[Any] = [*custody_merge.superseded, *cash_merge.superseded]
        self.mismatch = {"custody": custody_merge.mismatch_days, "cash": cash_merge.mismatch_days}
        for row in [*self.custody, *custody_merge.superseded]:
            row.klass = _classify_custody(row)
        for row in [*self.cash, *cash_merge.superseded]:
            row.klass, row.name = _classify_cash(row)
        self.pairs, ambiguous = _pair_rows(self.custody, self.cash)
        self.ambiguous = {id(row) for row in ambiguous}
        paired = {id(row) for pair in self.pairs for row in pair}
        unpaired_cash = [row for row in self.cash if row.klass in _PAIRED and id(row) not in paired and id(row) not in self.ambiguous]
        self.segments = _proven_segments(_raw_segments(self.custody_files), unpaired_cash)
        self.chain = _chain(self.cash)
        self.first_cash = self.chain.days[0] if self.chain.days else None
        self.cash_spans = _cash_spans(self.cash_files)
        self.timeline = _timeline(self.segments, self.first_cash)
        if self.timeline:
            self._settle()

    # ----------------------------------------------------------------- outcomes

    def _absorbing(self, zone: str) -> Optional[date]:
        return self.timeline[0].checkpoint if zone == "before" else None

    def _settle(self) -> None:
        for custody, cash in self.pairs:
            zone, _ = _zone(self.timeline, cash.value)
            custody.outcome = _Outcome("pair", zone)
            cash.outcome = _Outcome("pair", zone)
        for row in self.custody:
            if not row.outcome.kind:
                self._settle_custody(row)
        for row in self.cash:
            if not row.outcome.kind:
                self._settle_cash(row)
        for row in self.superseded:
            row.outcome = _Outcome("excluded", _zone(self.timeline, row.day)[0], "superseded")

    def _settle_custody(self, row: _CustodyRow) -> None:
        zone, _ = _zone(self.timeline, row.day)
        if id(row) in self.ambiguous:
            row.outcome = _Outcome("excluded", zone, "ambiguous")
        elif row.klass in _PAIRED:
            row.outcome = _Outcome("excluded", zone, self._unpaired_custody_reason(row))
        elif row.klass in ("demerger_old", "demerger_new"):
            row.outcome = _Outcome("standalone", zone)
        else:
            row.outcome = _Outcome("excluded", zone, row.klass)

    def _unpaired_custody_reason(self, row: _CustodyRow) -> str:
        if not self.cash_spans:
            return "outside_cash_coverage"
        if row.value > self.cash_spans[-1][1]:
            return "not_yet_settled"
        if not any(start <= row.value <= end for start, end in self.cash_spans):
            return "outside_cash_coverage"
        return "no_counterpart"

    def _settle_cash(self, row: _CashRow) -> None:
        zone, index = _zone(self.timeline, row.value)
        if id(row) in self.ambiguous:
            row.outcome = _Outcome("excluded", zone, "ambiguous", self._absorbing(zone))
        elif row.klass in _PAIRED:
            row.outcome = self._unpaired_cash_outcome(row, zone, index)
        elif row.klass in _STANDALONE_TYPES:
            row.outcome = _Outcome("standalone", zone, checkpoint=self._absorbing(zone))
        elif row.klass == "unknown_type":
            row.outcome = _Outcome("excluded", zone, "unknown_type", self._absorbing(zone))
        else:
            row.outcome = _Outcome("excluded", zone, row.klass)

    def _unpaired_cash_outcome(self, row: _CashRow, zone: str, index: int) -> _Outcome:
        """Design 3.4.2, row "cash that pairs, without counterpart"."""
        segment = self.timeline[index]
        if zone in ("before", "gap"):
            return _Outcome("summarized", zone, checkpoint=segment.checkpoint)
        if zone == "after":
            return _Outcome("deferred", "after")
        if row.value <= segment.border_end:
            return _Outcome("summarized", "window", checkpoint=segment.checkpoint)
        if row.value > segment.end:
            # A trade made after the custody export ends: it belongs to the next zone.
            if index + 1 < len(self.timeline):
                return _Outcome("summarized", "gap", checkpoint=self.timeline[index + 1].checkpoint)
            return _Outcome("deferred", "after")
        return _Outcome("excluded", "window", "no_counterpart")

    # ----------------------------------------------------------------- movements and proofs

    def _custody_rows_of(self, title: str) -> List[_CustodyRow]:
        return [row for row in self.custody if row.title == title]

    def _movements(self, title: str) -> List[_Movement]:
        moves = []
        for row in self._custody_rows_of(title):
            imported = row.outcome.kind == "pair" or row.outcome.kind == "standalone"
            if imported and row.klass in _MOVEMENTS:
                moves.append(_Movement(day=row.value, trade=row.trade, order=(row.file_index, row.row), qty=row.qty, row=row))
        return sorted(moves, key=lambda move: (move.day, move.trade, move.order))

    def _moved(self, title: str, after: date, until: date, inclusive: bool) -> Decimal:
        return sum((move.qty for move in self._movements(title) if after < move.day and (move.day <= until if inclusive else move.day < until)), ZERO)

    def _excluded_between(self, title: str, after: date, until: date, proof_row: Optional[_CustodyRow]) -> bool:
        for row in self._custody_rows_of(title):
            if row is proof_row or row.outcome.kind != "excluded":
                continue
            if any(day is not None and after < day <= until for day in (row.trade, row.value)):
                return True
        return False

    def _recent_trades(self, title: str, start: date, end: date, proof_row: _CustodyRow) -> bool:
        for row in self._custody_rows_of(title):
            if row is not proof_row and row.klass in _MOVEMENTS and row.trade is not None and start <= row.trade <= end:
                return True
        for row in self.cash:
            if row.klass in ("buy", "sell") and row.outcome.kind != "pair" and _compatible(row.name, title) and start <= row.value <= end:
                return True
        return False

    def _proof_e1(self, segment: _Segment, row: _CustodyRow) -> _Proof:
        day = row.trade
        start = day - timedelta(days=PROOF_WINDOW_DAYS)
        if self._recent_trades(row.title, start, day, row):
            return _Proof(row, "E1", reason="recent_trades")
        if start < segment.start and (self.first_cash is None or self.first_cash > start):
            return _Proof(row, "E1", reason="window_not_covered")
        if self._excluded_between(row.title, segment.checkpoint, day, row):
            return _Proof(row, "E1", reason="excluded_rows")
        return _Proof(row, "E1", quantity=row.qty - self._moved(row.title, segment.checkpoint, day, inclusive=True))

    def _proof_e2(self, segment: _Segment, row: _CustodyRow) -> _Proof:
        day = row.value
        same_day = [other for other in self._custody_rows_of(row.title) if other is not row and other.klass in _MOVEMENTS and day in (other.trade, other.value)]
        if same_day:
            return _Proof(row, "E2", reason="same_day_movement")
        if self._excluded_between(row.title, segment.checkpoint, day, row):
            return _Proof(row, "E2", reason="excluded_rows")
        return _Proof(row, "E2", quantity=-row.qty - self._moved(row.title, segment.checkpoint, day, inclusive=False))

    def _proof_e3(self, segment: _Segment, title: str) -> Optional[_Proof]:
        running, lowest, at = ZERO, ZERO, None
        for move in self._movements(title):
            if not segment.checkpoint < move.day <= segment.window_end:
                continue
            running += move.qty
            if running < lowest:
                lowest, at = running, move
        if at is None:
            return None
        if self._excluded_between(title, segment.checkpoint, at.day, None):
            return _Proof(at.row, "E3", exactness="at_least", reason="excluded_rows")
        return _Proof(at.row, "E3", quantity=-lowest, exactness="at_least")

    def _exact_proofs(self, segment: _Segment, title: str) -> List[_Proof]:
        proofs = []
        for row in self._custody_rows_of(title):
            if row.value is None or not segment.checkpoint < row.value <= segment.window_end:
                continue
            if row.klass == "income":
                proofs.append(self._proof_e1(segment, row))
            elif row.klass == "demerger_old":
                proofs.append(self._proof_e2(segment, row))
        return proofs

    def _title_proofs(self, segment: _Segment, title: str) -> List[_Proof]:
        """The accepted proof first (at most one), then the discarded ones."""
        proofs = self._exact_proofs(segment, title)
        discarded = [proof for proof in proofs if proof.reason]
        accepted = [proof for proof in proofs if not proof.reason]
        if len({proof.quantity for proof in accepted}) > 1 or any(proof.quantity < 0 for proof in accepted):
            discarded += [replace(proof, reason="conflict") for proof in accepted]
            accepted = []
        if accepted:
            return [accepted[0], *discarded]
        fallback = self._proof_e3(segment, title)
        return ([fallback] if fallback else []) + discarded

    def proofs(self, segment: _Segment) -> List[_Proof]:
        titles = sorted({row.title for row in self.custody if row.value is not None and segment.checkpoint < row.value <= segment.window_end})
        return [proof for title in titles for proof in self._title_proofs(segment, title)]

    # ----------------------------------------------------------------- cash truth

    def border_cash(self, segment: _Segment) -> Decimal:
        rows = [row for row in self.cash if row.outcome.kind == "summarized" and row.outcome.checkpoint == segment.checkpoint and row.value > segment.checkpoint]
        return sum((row.amount for row in rows), ZERO)

    def verification_day(self) -> Optional[date]:
        if not self.chain.days:
            return None
        day = min(self.timeline[-1].end, self.chain.days[-1])
        return day if self.chain.covers(day) else None

    # ----------------------------------------------------------------- notices for the preview

    def set_notices(self) -> List[BRIMNotice]:
        notices = []
        for role, files in (("custody", self.custody_files), ("cash", self.cash_files)):
            for index, rows in enumerate(files, start=1):
                if not rows:
                    notices.append(BRIMNotice(severity="warning", code="empty_member", message=f"A {role} export has no rows", context={"role": role, "file": index}))
        for index, rows in enumerate(self.custody_files, start=1):
            if len({row.account for row in rows if row.account}) > 1:
                notices.append(BRIMNotice(severity="warning", code="mixed_accounts_in_file", message="A custody export contains several custody accounts", context={"file": index}))
        for role, days in self.mismatch.items():
            if days:
                message = f"Two {role} exports disagree on {len(days)} day(s) they both cover: the newer export is used for those days"
                notices.append(BRIMNotice(severity="warning", code="overlap_mismatch", message=message, context={"role": role, "days": len(days), "first": days[0].isoformat(), "last": days[-1].isoformat()}))
        for gap in self.gaps():
            message = f"No custody export covers {gap.start.isoformat()} to {gap.end.isoformat()}: the trades of that period are summarised. Export the custody transactions for it if the bank still has them"
            notices.append(BRIMNotice(severity="warning", code="gap", message=message, context={"start": gap.start.isoformat(), "end": gap.end.isoformat()}))
        if self.chain.breaks:
            message = f"The running balance of the cash statement does not add up from {self.chain.breaks[0].isoformat()}: the balances are only compared, not used for corrections"
            notices.append(BRIMNotice(severity="warning", code="balance_chain_broken", message=message, context={"date": self.chain.breaks[0].isoformat()}))
        return notices

    def gaps(self) -> List[DateRangeModel]:
        return [DateRangeModel(start=before.end + timedelta(days=1), end=after.start - timedelta(days=1)) for before, after in zip(self.timeline, self.timeline[1:], strict=False)]


# =============================================================================
# THE COMBINED TABLE
# =============================================================================


def _line(kind: str, *, zone: str = "", reason: str = "", checkpoint: Optional[date] = None, source: str = "", match_key: str = "", value: str = "", currency: str = "", proof: str = "", custody: Optional[_CustodyRow] = None, cash: Optional[_CashRow] = None) -> List[str]:
    values = {
        "lf_row_kind": kind,
        "lf_zone": zone,
        "lf_reason": reason,
        "lf_checkpoint": checkpoint.isoformat() if checkpoint else "",
        "lf_source": source,
        "lf_match_key": match_key,
        "lf_value": value,
        "lf_currency": currency,
        "lf_proof": proof,
    }
    for column in CUSTODY_COLUMNS:
        values[f"custody:{column}"] = custody.cells.get(column, "") if custody else ""
    for column in CASH_COLUMNS:
        values[f"cash:{column}"] = cash.cells.get(column, "") if cash else ""
    return [values[header] for header in COMBINED_HEADERS]


def _data_key(day: Optional[date], role_rank: int, file_index: int, row: int) -> Tuple[Any, ...]:
    return (day or date.min, 0, role_rank, file_index, row, "")


def _truth_key(day: date, rank: int, detail: str) -> Tuple[Any, ...]:
    return (day, 1, rank, 0, 0, detail)


class _TableBuilder:
    """Writes the analysis as the combined table: one line per source row, plus the truth rows."""

    def __init__(self, analysis: _Analysis):
        self.analysis = analysis
        self.lines: List[Tuple[Tuple[Any, ...], List[str]]] = []
        self.summary_checkpoints: List[Dict[str, Any]] = []
        self.summary_verifications: List[Dict[str, Any]] = []

    def build(self) -> BRIMCombinedTable:
        self._data_lines()
        for segment in self.analysis.timeline:
            self._checkpoint_lines(segment)
        self._final_verification()
        rows = [line for _, line in sorted(self.lines, key=lambda item: item[0])]
        return BRIMCombinedTable(headers=list(COMBINED_HEADERS), rows=rows, summary=self._summary())

    def _add(self, key: Tuple[Any, ...], line: List[str]) -> None:
        self.lines.append((key, line))

    def _data_lines(self) -> None:
        analysis = self.analysis
        for custody, cash in analysis.pairs:
            key = _data_key(cash.value, 0, custody.file_index, custody.row)
            match = _match_key_text(cash.value, cash.amount, CURRENCY)
            self._add(key, _line("pair", zone=cash.outcome.zone, source=f"{custody.source} + {cash.source}", match_key=match, custody=custody, cash=cash))
        paired = {id(row) for pair in analysis.pairs for row in pair}
        for row in [*analysis.custody, *(item for item in analysis.superseded if isinstance(item, _CustodyRow))]:
            if id(row) not in paired:
                self._add(_data_key(row.day, 0, row.file_index, row.row), self._custody_line(row))
        for row in [*analysis.cash, *(item for item in analysis.superseded if isinstance(item, _CashRow))]:
            if id(row) not in paired:
                self._add(_data_key(row.value, 1, row.file_index, row.row), self._cash_line(row))

    @staticmethod
    def _custody_line(row: _CustodyRow) -> List[str]:
        outcome = row.outcome
        match = _match_key_text(row.value, row.summa, row.currency) if row.klass in _PAIRED else ""
        return _line(outcome.kind, zone=outcome.zone, reason=outcome.reason, checkpoint=outcome.checkpoint, source=row.source, match_key=match, custody=row)

    @staticmethod
    def _cash_line(row: _CashRow) -> List[str]:
        outcome = row.outcome
        match = _match_key_text(row.value, row.amount, CURRENCY) if row.klass in _PAIRED else ""
        return _line(outcome.kind, zone=outcome.zone, reason=outcome.reason, checkpoint=outcome.checkpoint, source=row.source, match_key=match, cash=row)

    def _checkpoint_lines(self, segment: _Segment) -> None:
        analysis = self.analysis
        chain = analysis.chain
        balance = chain.balance_at(segment.checkpoint) if chain.covers(segment.checkpoint) else None
        source = chain.source_at(segment.checkpoint) if balance is not None else None
        amount, reason = None, ""
        if balance is None:
            reason = "not_covered"
        elif chain.breaks:
            reason = "balance_chain_broken"
            self._verification_line(segment.checkpoint, segment.zone, balance, source)
        else:
            amount = balance + analysis.border_cash(segment)
        self._add(
            _truth_key(segment.checkpoint, 0, ""),
            _line("truth_cash", zone=segment.zone, reason=reason, checkpoint=segment.checkpoint, source=source.source if source else "", value=_money(amount) if amount is not None else "", currency=CURRENCY if amount is not None else "", cash=source),
        )
        proofs = analysis.proofs(segment)
        for proof in proofs:
            quantity = _plain(proof.quantity) if proof.quantity is not None and not proof.reason else ""
            self._add(_truth_key(segment.checkpoint, 1, proof.row.title), _line("truth_position", zone=segment.zone, checkpoint=segment.checkpoint, source=proof.row.source, value=quantity, proof=proof.proof_text, custody=proof.row))
        self.summary_checkpoints.append(
            {
                "as_of": segment.checkpoint.isoformat(),
                "kind": segment.kind,
                "cash": _money(amount) if amount is not None else None,
                "positions": sum(1 for proof in proofs if not proof.reason),
                "absorbed": self._absorbed_count(segment.checkpoint),
            }
        )

    def _absorbed_count(self, checkpoint: date) -> int:
        return sum(1 for row in self.analysis.cash if row.outcome.checkpoint == checkpoint and row.amount is not None and row.value is not None)

    def _verification_line(self, day: date, zone: str, balance: Decimal, source: Optional[_CashRow]) -> None:
        self._add(
            _truth_key(day, 2, ""),
            _line("verification", zone=zone, checkpoint=day, source=source.source if source else "", value=_money(balance), currency=CURRENCY, cash=source),
        )
        self.summary_verifications.append({"as_of": day.isoformat(), "cash": _money(balance)})

    def _final_verification(self) -> None:
        day = self.analysis.verification_day()
        if day is None:
            return
        chain = self.analysis.chain
        self._verification_line(day, _zone(self.analysis.timeline, day)[0], chain.balance_at(day), chain.source_at(day))

    def _summary(self) -> Dict[str, Any]:
        analysis = self.analysis
        kinds: Counter = Counter()
        zones: Counter = Counter()
        reasons: Counter = Counter()
        for _, line in self.lines:
            kind = line[0]
            if kind in _TRUTH_KINDS:
                continue
            kinds[kind] += 1
            zones[line[1] or "none"] += 1
            if line[2]:
                reasons[line[2]] += 1
        return {
            "rows": {"custody": sum(len(rows) for rows in analysis.custody_files), "cash": sum(len(rows) for rows in analysis.cash_files)},
            "outcomes": dict(sorted(kinds.items())),
            "zones": dict(sorted(zones.items())),
            "reasons": dict(sorted(reasons.items())),
            "segments": [{"start": segment.start.isoformat(), "end": segment.end.isoformat()} for segment in analysis.timeline],
            "gaps": [{"start": gap.start.isoformat(), "end": gap.end.isoformat()} for gap in analysis.gaps()],
            "checkpoints": self.summary_checkpoints,
            "verifications": self.summary_verifications,
            "balance_chain": "broken" if analysis.chain.breaks else "ok",
            "overlap_mismatch_days": sum(len(days) for days in analysis.mismatch.values()),
        }


# =============================================================================
# PARSE OF THE COMBINED FILE
# =============================================================================

_CUSTODY_EVIDENCE = (
    ("Kauppapäivä", "custody:Kauppapäivä"),
    ("Arvopäivä", "custody:Arvopäivä"),
    ("Sijoituskohde", "custody:Sijoituskohde"),
    ("Määrä", "custody:Määrä"),
    ("Kurssi", "custody:Kurssi"),
    ("Summa", "custody:Summa"),
    ("Valuutta", "custody:H"),
    ("Toimeksiantotyyppi", "custody:Toimeksiantotyyppi"),
)
_CASH_EVIDENCE = (("Pvm", "cash:Pvm"), ("Saaja/Maksaja", "cash:Saaja/Maksaja"), ("Määrä", "cash:Määrä"), ("Saldo", "cash:Saldo"))

Row = Dict[str, str]
Line = Tuple[int, Row]

_EXCLUDED_MESSAGES = {
    "no_counterpart": "{n} riviä ilman vastinetta toisessa tiedostossa: niitä ei tuoda.",
    "ambiguous": "{n} riviä, joita ei voitu yhdistää yksiselitteisesti: niitä ei tuoda.",
    "not_yet_settled": "{n} kauppaa maksetaan tilitiedoston viimeisen päivän jälkeen: ne tulevat seuraavassa tuonnissa.",
    "outside_cash_coverage": "{n} kauppaa maksettiin ennen tilitiedoston ensimmäistä päivää: niitä ei tuoda.",
    "status": "{n} riviä ei ole toteutunut tai kirjattu: niitä ei tuoda.",
    "unknown_type": "{n} riviä on tuntematonta tyyppiä: niitä ei tuoda.",
    "invalid": "{n} riviä on virheellisiä: niitä ei tuoda.",
    "superseded": "{n} riviä korvattiin uudemmalla tiedostolla, joka kattaa samat päivät.",
}
_EXCLUDED_COMMENT = "Nämä rivit eivät tule tuontiin. Jos jokin niistä pitää paikkansa, lisää se käsin."


def _evidence(title: str, comment: str, lines: Sequence[Line], columns: Sequence[Tuple[str, str]]) -> BRIMEvidence:
    return BRIMEvidence(
        title=title,
        headers=[header for header, _ in columns],
        rows=[[row.get(column, "") for _, column in columns] for _, row in lines],
        row_numbers=[number for number, _ in lines],
        comment=comment,
    )


def _row_evidence(lines: Sequence[Line], comment: str) -> List[BRIMEvidence]:
    """One table for the custody side and one for the cash side, as far as the rows have them."""
    custody = [line for line in lines if line[1].get("custody:Toimeksiantotyyppi")]
    cash = [line for line in lines if line[1].get("cash:Saaja/Maksaja")]
    tables = []
    if custody:
        tables.append(_evidence("Arvopaperitapahtumat", comment, custody, _CUSTODY_EVIDENCE))
    if cash:
        tables.append(_evidence("Tilitapahtumat", comment, cash, _CASH_EVIDENCE))
    return tables


def _read_combined(path: Path) -> List[Line]:
    with BRIMProvider._open_text(path, newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        header = [cell.strip().lstrip("\ufeff") for cell in next(reader, [])]
        missing = [name for name in COMBINED_HEADERS if name not in header]
        if missing:
            raise BRIMParseError("Not a Danske Bank combined file: columns are missing", details={"missing": missing})
        positions = {name: header.index(name) for name in COMBINED_HEADERS}
        lines: List[Line] = []
        for cells in reader:
            if not any(cell.strip() for cell in cells):
                continue
            lines.append((reader.line_num, {name: cells[position] if position < len(cells) else "" for name, position in positions.items()}))
        return lines


@dataclass
class _TruthCash:
    zone: str
    amount: Optional[Decimal]
    reason: str
    evidence: List[BRIMEvidence]


class _CombinedParser:
    """Rebuilds transactions, todos, notices and truth points from the combined file."""

    def __init__(self, provider: BRIMProvider, broker_id: int):
        self.provider = provider
        self.broker_id = broker_id
        self.transactions: List[TXCreateItem] = []
        self.issues: List[BRIMValidationIssue] = []
        self.todos: List[BRIMFieldTodo] = []
        self.assets: Dict[int, BRIMExtractedAssetInfo] = {}
        self.fake_ids: Dict[str, int] = {}
        self.excluded: Dict[str, List[Line]] = defaultdict(list)
        self.deferred: List[Line] = []
        self.deposits: List[Line] = []
        self.mismatched: List[Line] = []
        self.discarded: List[Line] = []
        self.absorbed: Dict[date, List[BRIMAbsorbedRow]] = defaultdict(list)
        self.truth_cash: Dict[date, _TruthCash] = {}
        self.positions: Dict[date, List[BRIMTruthPosition]] = defaultdict(list)
        self.verifications: List[BRIMVerification] = []
        self.handlers: Dict[str, Callable[[int, Row], None]] = {
            "pair": self._pair,
            "standalone": self._standalone,
            "excluded": self._excluded,
            "summarized": self._nothing,
            "deferred": self._deferred,
            "truth_cash": self._truth_cash,
            "truth_position": self._truth_position,
            "verification": self._verification,
        }

    # ----------------------------------------------------------------- dispatch

    def add(self, line: int, row: Row) -> None:
        handler = self.handlers.get(row["lf_row_kind"])
        if handler is None:
            raise BRIMParseError(f"Line {line} of the combined file has an unknown kind", details={"line": line, "kind": row["lf_row_kind"]})
        if row["lf_checkpoint"] and row["lf_row_kind"] not in _TRUTH_KINDS:
            self._absorb(line, row)
        handler(line, row)

    def _absorb(self, line: int, row: Row) -> None:
        amount = _to_decimal(row["cash:Määrä"])
        day = _to_date(row["cash:Pvm"])
        if amount is None or day is None:
            return
        self.absorbed[date.fromisoformat(row["lf_checkpoint"])].append(BRIMAbsorbedRow(as_of=day, currency=CURRENCY, amount=amount, label=row["cash:Saaja/Maksaja"] or None))

    def _nothing(self, line: int, row: Row) -> None:
        return None

    def _fake_id(self, name: str) -> int:
        key = _norm(name)
        if key not in self.fake_ids:
            fake_id = FAKE_ASSET_ID_BASE - len(self.fake_ids)
            self.fake_ids[key] = fake_id
            self.assets[fake_id] = BRIMExtractedAssetInfo(extracted_name=name.strip())
        return self.fake_ids[key]

    def _create(self, line: int, context: str, **fields: Any) -> Optional[TXCreateItem]:
        return self.provider._create_transaction(row_num=line, transactions=self.transactions, validation_issues=self.issues, context=context, broker_id=self.broker_id, **fields)

    @staticmethod
    def _required(line: int, *values: Any) -> None:
        if any(value is None for value in values):
            raise BRIMParseError(f"Line {line} of the combined file is incomplete", details={"line": line})

    # ----------------------------------------------------------------- rows

    def _pair(self, line: int, row: Row) -> None:
        quantity = _to_decimal(row["custody:Määrä"])
        amount = _to_decimal(row["cash:Määrä"])
        day = _to_date(row["cash:Pvm"])
        self._required(line, quantity, amount, day)
        name = row["custody:Sijoituskohde"]
        label = row["cash:Saaja/Maksaja"]
        order_type = row["custody:Toimeksiantotyyppi"]
        if _norm(order_type) == _INCOME:
            tx_type, delta = TransactionType.DIVIDEND, ZERO
        else:
            tx_type, delta = (TransactionType.BUY if quantity > 0 else TransactionType.SELL), quantity
        created = self._create(
            line,
            label,
            asset_id=self._fake_id(name),
            type=tx_type,
            date=day,
            quantity=delta,
            cash=Currency(code=CURRENCY, amount=amount),
            description=f"{label} ({order_type})"[:500],
            tags=["import", HISTORY_TAG],
        )
        if created is None:
            return
        if tx_type != TransactionType.DIVIDEND:
            self.todos.append(_charges_todo(len(self.transactions) - 1, line, row, tx_type, quantity, amount))
        if not _compatible(name, _cash_label_class(label, amount)[1]):
            self.mismatched.append((line, row))

    def _standalone(self, line: int, row: Row) -> None:
        if row["custody:Toimeksiantotyyppi"]:
            self._demerger(line, row)
        else:
            self._cash_row(line, row)

    def _demerger(self, line: int, row: Row) -> None:
        quantity = _to_decimal(row["custody:Määrä"])
        day = _to_date(row["custody:Arvopäivä"])
        self._required(line, quantity, day)
        name = row["custody:Sijoituskohde"]
        order_type = row["custody:Toimeksiantotyyppi"]
        created = self._create(
            line,
            order_type,
            asset_id=self._fake_id(name),
            type=TransactionType.ADJUSTMENT,
            date=day,
            quantity=quantity,
            description=f"{order_type}: {name}"[:500],
            tags=["import", HISTORY_TAG, "demerger"],
        )
        if created is not None:
            self.todos.append(_demerger_todo(len(self.transactions) - 1, line, row, new_line=_norm(order_type) == _DEMERGER_NEW))

    def _cash_row(self, line: int, row: Row) -> None:
        amount = _to_decimal(row["cash:Määrä"])
        day = _to_date(row["cash:Pvm"])
        self._required(line, amount, day)
        label = row["cash:Saaja/Maksaja"]
        klass, _ = _cash_label_class(label, amount)
        tx_type = _STANDALONE_TYPES.get(klass)
        if tx_type is None:
            raise BRIMParseError(f"Line {line} of the combined file is not a standalone cash row", details={"line": line})
        self._create(line, label, type=tx_type, date=day, cash=Currency(code=CURRENCY, amount=amount), description=label[:500], tags=["import", HISTORY_TAG])
        if klass == "deposit":
            self.deposits.append((line, row))

    def _excluded(self, line: int, row: Row) -> None:
        self.excluded[row["lf_reason"] or "invalid"].append((line, row))

    def _deferred(self, line: int, row: Row) -> None:
        self.deferred.append((line, row))

    # ----------------------------------------------------------------- truth rows

    def _truth_cash(self, line: int, row: Row) -> None:
        amount = _to_decimal(row["lf_value"]) if row["lf_value"] else None
        comment = "Pankin ilmoittama saldo päivän lopussa, ennen arvopaperitiedoston jaksoa."
        evidence = _row_evidence([(line, row)], comment) if row["cash:Saaja/Maksaja"] else []
        self.truth_cash[date.fromisoformat(row["lf_checkpoint"])] = _TruthCash(zone=row["lf_zone"], amount=amount, reason=row["lf_reason"], evidence=evidence)

    def _truth_position(self, line: int, row: Row) -> None:
        proof = row["lf_proof"]
        if proof.startswith("discarded:") or not row["lf_value"]:
            self.discarded.append((line, row))
            return
        exactness = proof.split(":", 1)[0]
        quantity = _to_decimal(row["lf_value"])
        self._required(line, quantity)
        position = BRIMTruthPosition(asset_id=self._fake_id(row["custody:Sijoituskohde"]), quantity=quantity, exactness=exactness)
        self.positions[date.fromisoformat(row["lf_checkpoint"])].append(position)

    def _verification(self, line: int, row: Row) -> None:
        amount = _to_decimal(row["lf_value"])
        self._required(line, amount)
        comment = "Pankin ilmoittama saldo päivän lopussa: sitä verrataan LibreFolioon, mutta sen perusteella ei korjata."
        evidence = _row_evidence([(line, row)], comment) if row["cash:Saaja/Maksaja"] else []
        self.verifications.append(BRIMVerification(as_of=date.fromisoformat(row["lf_checkpoint"]), cash=[BRIMTruthCash(currency=row["lf_currency"] or CURRENCY, amount=amount)], evidence=evidence))

    # ----------------------------------------------------------------- output

    def _checkpoint(self, day: date) -> BRIMCheckpoint:
        truth = self.truth_cash[day]
        kind = "opening" if truth.zone == "before" else "gap"
        rows = self.absorbed.get(day, [])
        sums: Dict[str, Decimal] = defaultdict(lambda: ZERO)
        for item in rows:
            sums[item.currency] += item.amount
        cash = [BRIMTruthCash(currency=CURRENCY, amount=truth.amount)] if truth.amount is not None else []
        opening = [BRIMTruthCash(currency=CURRENCY, amount=truth.amount - sums[CURRENCY])] if kind == "opening" and truth.amount is not None else []
        absorbed = BRIMAbsorbed(count=len(rows), cash=[BRIMTruthCash(currency=code, amount=amount) for code, amount in sorted(sums.items())], rows=rows, opening_cash=opening)
        return BRIMCheckpoint(as_of=day, kind=kind, cash=cash, positions=self.positions.get(day, []), absorbed=absorbed, evidence=truth.evidence)

    def output(self) -> BRIMParseOutput:
        return BRIMParseOutput(
            transactions=self.transactions,
            warnings=self._notices(),
            validation_issues=self.issues,
            field_todos=self.todos,
            extracted_assets=self.assets,
            checkpoints=[self._checkpoint(day) for day in sorted(self.truth_cash)],
            verifications=sorted(self.verifications, key=lambda item: item.as_of),
        )

    def _notices(self) -> List[BRIMNotice]:
        notices = []
        for reason in sorted(self.excluded, key=lambda item: (_EXCLUDED_ORDER.index(item) if item in _EXCLUDED_ORDER else len(_EXCLUDED_ORDER), item)):
            lines = self.excluded[reason]
            message = _EXCLUDED_MESSAGES.get(reason, "{n} riviä jätettiin pois.").format(n=len(lines))
            notices.append(BRIMNotice(severity="warning", code=f"excluded_{reason}", message=message, evidence=_row_evidence(lines, _EXCLUDED_COMMENT), context={"count": len(lines), "reason": reason}))
        notices.extend(self._info_notices())
        return notices

    def _info_notices(self) -> List[BRIMNotice]:
        notices = []
        if self.deferred:
            message = f"{len(self.deferred)} tilitapahtumaa on arvopaperitiedoston viimeisen päivän jälkeen: ne tulevat seuraavassa tuonnissa."
            notices.append(BRIMNotice(severity="info", code="deferred_rows", message=message, evidence=_row_evidence(self.deferred, "Näiden kauppojen arvopaperirivit ovat seuraavassa arvopaperitiedostossa."), context={"count": len(self.deferred)}))
        if self.mismatched:
            message = f"{len(self.mismatched)} yhdistetyssä kaupassa nimi ei täsmää tilitapahtuman nimeen: tarkista ne."
            comment = "Päivä, summa ja suunta täsmäävät, joten rivit yhdistettiin. Nimi on kuitenkin eri, joten tarkista, että kyse on samasta kaupasta."
            notices.append(BRIMNotice(severity="warning", code="name_mismatch", message=message, evidence=_row_evidence(self.mismatched, comment), context={"count": len(self.mismatched)}))
        if self.discarded:
            message = f"{len(self.discarded)} omistusmäärää ei voitu päätellä luotettavasti tiedostoista: niitä ei käytetä täsmäytyksessä."
            comment = "Rivi olisi kertonut omistuksen määrän, mutta lähellä on muita kauppoja tai pois jätettyjä rivejä samalla arvopaperilla."
            proofs = sorted({row["lf_proof"] for _, row in self.discarded})
            notices.append(BRIMNotice(severity="info", code="proof_discarded", message=message, evidence=_row_evidence(self.discarded, comment), context={"count": len(self.discarded), "proofs": proofs}))
        broken = sorted(day for day, truth in self.truth_cash.items() if truth.reason == "balance_chain_broken")
        if broken:
            message = "Tilitiedoston saldot eivät täsmää tapahtumien kanssa: saldoja käytetään vain vertailuun, ei korjauksiin."
            notices.append(BRIMNotice(severity="warning", code="balance_chain_broken", message=message, context={"dates": [day.isoformat() for day in broken]}))
        if self.deposits:
            message = f"{len(self.deposits)} hyvitystä kirjattiin talletuksiksi, koska osakesäästötilille voi tallettaa vain rahaa: tarkista ne."
            notices.append(BRIMNotice(severity="info", code="deposit_assumed", message=message, evidence=_row_evidence(self.deposits, "Maksajan nimi ei ole tunnettu tapahtumatyyppi, joten rivi on tulkittu talletukseksi."), context={"count": len(self.deposits)}))
        return notices


def _charges_todo(tx_index: int, line: int, row: Row, tx_type: TransactionType, quantity: Decimal, amount: Decimal) -> BRIMFieldTodo:
    """Every trade: Summa includes the commission (the fee column is always 0); the split is optional (D-S17)."""
    name = row["custody:Sijoituskohde"]
    price = _to_decimal(row["custody:Kurssi"]) or ZERO
    gross = (abs(quantity) * price).quantize(CENT)
    charges = abs(amount) - gross if tx_type == TransactionType.BUY else gross - abs(amount)
    plausible = ZERO <= charges <= max(Decimal("15"), gross / 100)
    suggestions = []
    if plausible:
        suggestions.append(f"Määrä × kurssi = {_fi_money(gross)} €: jos kurssi on euroissa, erotus {_fi_money(charges)} € on todennäköisesti palkkio.")
    else:
        suggestions.append("Kurssi voi olla muussa valuutassa kuin euroissa, joten palkkiota ei voi laskea tiedostosta.")
    suggestions.append("Tarkat luvut ovat kauppavahvistuksessa: avaa tapahtuma verkkopankissa.")
    context: Dict[str, Any] = {
        "row": line,
        "cash": _money(abs(amount)),
        "currency": CURRENCY,
        "compare_nominal": False,
        "split_hint": "trade_charges",
        "split_suggestions": suggestions,
    }
    if plausible:
        context["charges"] = _money(charges)
    verb = "osto" if tx_type == TransactionType.BUY else "myynti"
    comment = "Pankki ilmoittaa vain kokonaissumman: palkkiosarake on aina 0, joten palkkio sisältyy summaan. Kassa on oikein; jos haluat seurata palkkioita erikseen, jaa rivi."
    return BRIMFieldTodo(
        tx_index=tx_index,
        field="cash",
        severity="warning",
        reason_code="danske_trade_charges_included",
        message=f"Rivi {line}: {verb} {name} — summa sisältää palkkion.",
        context=context,
        evidence=_row_evidence([(line, row)], comment),
    )


def _demerger_todo(tx_index: int, line: int, row: Row, *, new_line: bool) -> BRIMFieldTodo:
    name = row["custody:Sijoituskohde"]
    if new_line:
        comment = "Jakautuminen on verotuksessa neutraali: vanhan osakkeen hankintameno jaetaan uusille osakkeille Verohallinnon ilmoittamassa suhteessa. Tiedosto ei kerro hankintamenoa."
        return BRIMFieldTodo(
            tx_index=tx_index,
            field="cost_basis_override",
            severity="blocker",
            reason_code="demerger",
            message=f"Rivi {line}: jakautumisessa saatu {name} — anna hankintameno kappaletta kohden.",
            context={"row": line},
            evidence=_row_evidence([(line, row)], comment),
        )
    comment = "Vanha rivi poistaa koko omistuksen. LibreFolio ei siirrä sen hankintamenoa uusille riveille: anna uusien rivien hankintameno."
    return BRIMFieldTodo(
        tx_index=tx_index,
        field="quantity",
        severity="warning",
        reason_code="demerger_old_leg",
        message=f"Rivi {line}: {name} poistuu jakautumisessa — sijoitettu pääoma ei pienene automaattisesti.",
        context={"row": line},
        evidence=_row_evidence([(line, row)], comment),
    )


# =============================================================================
# THE PLUGIN
# =============================================================================


@register_provider(BRIMProviderRegistry)
class DanskeBankBrokerProvider(BRIMProvider):
    """Danske Bank Finland equity savings account: custody XLSX + cash CSV, combined into one import."""

    @property
    def provider_code(self) -> str:
        return PROVIDER_CODE

    @property
    def provider_name(self) -> str:
        return "Danske Bank"

    @property
    def description(self) -> str:
        return "Import a Danske Bank (Finland) equity savings account: the custody transactions (XLSX) and the cash statement (CSV), uploaded together and combined into one import."

    @property
    def supported_extensions(self) -> List[str]:
        return [".xlsx", ".csv"]

    @property
    def detection_priority(self) -> int:
        return 100

    @property
    def icon_url(self) -> Optional[str]:
        return "https://danskebank.fi/favicon.ico"

    @property
    def docs_url(self) -> Optional[str]:
        return "/mkdocs/user/transactions/import/danske-bank/"

    @property
    def plugin_version(self) -> str:
        return "1.0.0"

    @property
    def test_file_pattern(self) -> Optional[str]:
        return "danske_bank"

    @property
    def test_sample_sets(self) -> List[Dict[str, List[str]]]:
        return [
            {"custody": ["danske_bank-custody.xlsx"], "cash": ["danske_bank-cash.csv"]},
            {"custody": ["danske_bank-gap-custody-1.xlsx", "danske_bank-gap-custody-2.xlsx"], "cash": ["danske_bank-gap-cash.csv"]},
        ]

    # ----------------------------------------------------------------- report set contract

    @property
    def report_roles(self) -> List[BRIMReportRole]:
        return [
            BRIMReportRole(
                code="custody",
                required=True,
                multiple=True,
                extensions=[".xlsx"],
                description="Custody transactions (Sijoitukset → Tapahtumat), exported as Excel: trades, income and demergers, dated by trade date",
                max_history="P1Y",
            ),
            BRIMReportRole(
                code="cash",
                required=True,
                multiple=True,
                extensions=[".csv"],
                description="Cash account statement of the equity savings account, exported as CSV: every cash movement with the running balance",
                max_history="P5Y",
                must_cover="custody",
            ),
        ]

    @property
    def settlement_lag_business_days(self) -> int:
        return LAG_BUSINESS_DAYS

    @property
    def pre_checkpoint_policy(self) -> str:
        return "summarize"

    def can_parse(self, file_path: Path) -> bool:
        return _file_kind(file_path) is not None

    def detect_role(self, file_path: Path) -> Optional[str]:
        kind = _file_kind(file_path)
        return kind if kind in ("custody", "cash") else None

    def describe_member(self, file_path: Path) -> BRIMMemberSummary:
        role = self.detect_role(file_path)
        if role == "custody":
            rows = _read_custody(file_path, 1, 1)
            span = _coverage(rows, lambda row: row.trade)
            accounts = sorted({row.account for row in rows if row.account})
            fingerprint = hashlib.sha256("\n".join(accounts).encode("utf-8")).hexdigest() if accounts else None
            coverage = [BRIMCoverage(axis="trade", start=span[0], end=span[1])] if span else []
            return BRIMMemberSummary(role=role, rows=len(rows), coverage=coverage, account_fingerprint=fingerprint)
        if role == "cash":
            rows = _read_cash(file_path, 1, 1)
            span = _coverage(rows, lambda row: row.value)
            coverage = [BRIMCoverage(axis="value", start=span[0], end=span[1])] if span else []
            return BRIMMemberSummary(role=role, rows=len(rows), coverage=coverage)
        return BRIMMemberSummary(role=None, rows=0)

    def describe_set(self, members: Dict[str, List[Path]]) -> BRIMSetShape:
        analysis = _Analysis(members)
        segments = [DateRangeModel(start=segment.start, end=segment.end) for segment in analysis.timeline]
        return BRIMSetShape(segments=segments, gaps=analysis.gaps(), notices=analysis.set_notices())

    def combine(self, members: Dict[str, List[Path]]) -> BRIMCombinedTable:
        analysis = _Analysis(members)
        if not analysis.timeline:
            raise BRIMParseError("The custody exports have no dated rows: there is nothing to combine")
        return _TableBuilder(analysis).build()

    def parse(self, file_path: Path, broker_id: int) -> BRIMParseOutput:
        kind = _file_kind(file_path)
        if kind in ("custody", "cash"):
            raise BRIMSetRequiredError(
                "This Danske Bank export is one file of a report set: upload the custody transactions (XLSX) and the cash statement (CSV) together, and import the set",
                missing_roles=[role.code for role in self.report_roles if role.code != kind],
            )
        if kind != "combined":
            raise BRIMParseError("Not a Danske Bank combined file")
        parser = _CombinedParser(self, broker_id)
        for line, row in _read_combined(file_path):
            parser.add(line, row)
        return parser.output()
