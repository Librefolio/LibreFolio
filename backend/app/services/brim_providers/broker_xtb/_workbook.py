"""Reader of XTB's «History report» workbook (``.xlsx``), the export XTB generates today.

The workbook has three sheets, each opening with four header lines (``Account number``, the sheet's name, the period) and
then its table:

- **Cash Operations** — every cash movement: purchases, sales, deposits, withdrawals, dividends, taxes, interest, the
  transfers between the account's sub-accounts (*My Trades*, *Investment Plans*); a last ``Total`` row. The only source
  of transactions.
- **Open Positions** — a snapshot at the report's generation: a summary per sub-account (``Product / Metric / Amount /
  Currency``: the only place that names the **account currency**), then one aggregate row per instrument (``Category``
  filled) followed by one row per lot.
- **Closed Positions** — the positions closed in the period: the same trades Cash Operations already holds, so it is
  never imported (reading it too would count every sale twice).

Cash Operations has no currency column: every ``Amount`` is in the account currency, also on an instrument quoted in
another currency (the price in the comment is in the instrument's currency). This module only reads and normalises
cells; the plugin decides what each row becomes.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import openpyxl

CASH_SHEET = "Cash Operations"
OPEN_SHEET = "Open Positions"
CLOSED_SHEET = "Closed Positions"

# The columns that identify the Cash Operations table (its header row is found by them, never by position).
CASH_REQUIRED = ("Type", "Time", "Amount", "Comment")
# Rows that close a table: a sum, never a movement.
TOTAL_LABELS = {"total", "profit/loss"}

TIME_FORMATS = ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y %H:%M:%S", "%d.%m.%Y")


def cell_text(value: Any) -> str:
    """A cell as text: ``None`` is empty, a number keeps its shortest form, a datetime its ISO second."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, float):
        return repr(value)
    return str(value).strip()


def cell_decimal(value: Any) -> Optional[Decimal]:
    """A number cell as read: a native number keeps its shortest decimal form; text accepts ``,`` as decimal mark."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(repr(value))
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def cell_datetime(value: Any) -> Optional[datetime]:
    """A time cell: a native datetime, or text in one of XTB's formats."""
    if isinstance(value, datetime):
        return value
    text = cell_text(value)
    if not text:
        return None
    for fmt in TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


@dataclass
class Workbook:
    """The sheets of one XTB report, as lists of raw rows (cells keep their openpyxl type)."""

    sheets: Dict[str, List[List[Any]]] = field(default_factory=dict)

    def rows(self, name: str) -> List[List[Any]]:
        return self.sheets.get(name, [])


def read_workbook(file_path: Path, *, limit: Optional[int] = None) -> Workbook:
    """Read every sheet of the workbook (``limit`` rows each, for detection)."""
    with warnings.catch_warnings():
        # openpyxl warns about harmless things in exported workbooks (default styles).
        warnings.simplefilter("ignore")
        book = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        try:
            sheets: Dict[str, List[List[Any]]] = {}
            for sheet in book.worksheets:
                rows: List[List[Any]] = []
                for row in sheet.iter_rows(values_only=True):
                    rows.append(list(row))
                    if limit is not None and len(rows) >= limit:
                        break
                sheets[sheet.title.strip()] = rows
            return Workbook(sheets=sheets)
        finally:
            book.close()


def find_header(rows: Sequence[Sequence[Any]], required: Sequence[str]) -> Optional[int]:
    """Index of the first row holding every ``required`` label (exact, trimmed), or ``None``."""
    wanted = set(required)
    for index, row in enumerate(rows):
        labels = {cell_text(cell) for cell in row}
        if wanted <= labels:
            return index
    return None


def column_index(header: Sequence[Any]) -> Dict[str, int]:
    """Label → column, first occurrence wins."""
    index: Dict[str, int] = {}
    for position, cell in enumerate(header):
        label = cell_text(cell)
        if label and label not in index:
            index[label] = position
    return index


def get(row: Sequence[Any], columns: Dict[str, int], label: str) -> Any:
    position = columns.get(label)
    if position is None or position >= len(row):
        return None
    return row[position]


def is_xtb_workbook(book: Workbook) -> bool:
    """The three sheets' names, and a Cash Operations table whose header carries the identifying columns."""
    if CASH_SHEET not in book.sheets or OPEN_SHEET not in book.sheets:
        return False
    return find_header(book.rows(CASH_SHEET), CASH_REQUIRED) is not None


def account_currencies(book: Workbook) -> List[str]:
    """The distinct currencies of the Open Positions summary (``Product / Metric / Amount / Currency``), in order."""
    rows = book.rows(OPEN_SHEET)
    start = find_header(rows, ("Product", "Metric", "Amount", "Currency"))
    if start is None:
        return []
    columns = column_index(rows[start])
    found: List[str] = []
    for row in rows[start + 1 :]:
        if not any(cell not in (None, "") for cell in row):
            break  # the summary ends at the first blank row
        code = cell_text(get(row, columns, "Currency")).upper()
        if code and code not in found:
            found.append(code)
    return found


@dataclass
class OpenPosition:
    """One aggregate row of Open Positions: an instrument and its open volume."""

    line: int
    ticker: str
    name: str
    category: str
    volume: Decimal
    cells: List[str]
    headers: List[str]


def open_positions(book: Workbook) -> List[OpenPosition]:
    """The aggregate rows of Open Positions (``Category`` filled: one per instrument; lot rows leave it empty)."""
    rows = book.rows(OPEN_SHEET)
    start = find_header(rows, ("Ticker", "Category", "Volume"))
    if start is None:
        return []
    columns = column_index(rows[start])
    headers = [cell_text(cell) for cell in rows[start]]
    result: List[OpenPosition] = []
    for offset, row in enumerate(rows[start + 1 :], start=start + 2):
        category = cell_text(get(row, columns, "Category"))
        ticker = cell_text(get(row, columns, "Ticker"))
        volume = cell_decimal(get(row, columns, "Volume"))
        if not category or not ticker or volume is None:
            continue
        name = cell_text(get(row, columns, "Instrument/Position")) or cell_text(get(row, columns, "Instrument")) or ticker
        result.append(OpenPosition(line=offset, ticker=ticker, name=name, category=category, volume=volume, cells=[cell_text(c) for c in row], headers=headers))
    return result
