"""
Test Suite: the XTB plugin — ``broker_xtb`` 2.1.0, the History report workbook (lane 83, lot 83-B)

XTB exports a «History report» workbook (``.xlsx``): its *Cash Operations* sheet is the only source of transactions, its
*Open Positions* summary names the account currency, its *Closed Positions* sheet is never read. The older Cash Operations
CSV (``ID;Type;Time;Symbol;Comment;Amount``) is no longer read (developer decision, lane 83: 2.0.0 is ``.xlsx`` only).

What is pinned:

- A. the workbook sample (an anonymised real export): counts, types, signs, the account currency, the asset names from
  ``Instrument``, the partial fill and the ticker inside a comment, the sub-account transfers left out without a word,
  the open volumes equal to the net imported quantities (so no notice), the amounts of the EUR-quoted purchases and the
  values of their lots consistent to the cent, recognition by ``can_parse`` and by the registry, a workbook whose Cash
  Operations header is gone refused, the old CSV refused and ``.xlsx`` the only extension;
- B. workbooks written in ``tmp_path`` (invented values): a baseline that imports cleanly (the builder's own guard), an
  unknown type and an unreadable time or amount in the two shared notices with their sheet rows, a sub-account transfer
  without its opposite, the account currency missing or ambiguous (two ``BRIMParseError`` codes), the currency read from
  the summary, a sale, the cash taken verbatim from ``Amount`` on an instrument quoted in another currency, the
  ``xtb_positions_outside_period`` info notice (the open volume of a ticker summed over its sub-accounts) and the CFD
  positions it never compares, a workbook with no importable row;
- C. the sign of the cash (lot 83-B, 2.1.0): the cash is the ``Amount`` as written, never flipped. A tax with a positive
  amount is an INTEREST «Tax refund» (on its asset when the row has a Ticker) listed in one ``xtb_tax_refund`` info notice;
  any other sign that does not fit the type is a row not recognised; an amount of 0 is not recognised on a purchase or a
  sale and left out without a word on a cash row; a file mixing normal rows and a refund changes nothing else.

``test_brim_row_skips.py`` lists XTB in its contract with this file as its own test (its samples are read as text lines).

PURE: the sample of ``sample_reports/`` and files written in ``tmp_path``; no server, no database, no network, no clock.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import openpyxl
import pytest

from backend.app.db.models import TransactionType
from backend.app.schemas.brim import BRIMNotice, BRIMParseOutput
from backend.app.services.brim.brim_provider import BRIMParseError
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.test_scripts.brim_samples import plugin_samples_dir

# =============================================================================
# CONSTANTS
# =============================================================================

PLUGIN_CODE = "broker_xtb"
BROKER_ID = 1
SAMPLES = plugin_samples_dir(PLUGIN_CODE)
XLSX_SAMPLE = SAMPLES / "xtb-export.xlsx"

ROWS_NOT_RECOGNIZED = "rows_not_recognized"
ROWS_UNREADABLE = "rows_unreadable"
OUTSIDE_PERIOD = "xtb_positions_outside_period"
CURRENCY_MISSING = "xtb_account_currency_missing"
CURRENCY_AMBIGUOUS = "xtb_account_currency_ambiguous"
TAX_REFUND = "xtb_tax_refund"

CASH_SHEET = "Cash Operations"
OPEN_SHEET = "Open Positions"
CLOSED_SHEET = "Closed Positions"
CASH_HEADER = ["Type", "Instrument", "Ticker", "Category", "Time", "Amount", "ID", "Comment", "Product", "Position ID"]
OPEN_HEADER = ["Product", "Instrument/Position", "Ticker", "Category", "Type", "Volume", "Value", "Current price", "Open price", "Open time (UTC)"]
CLOSED_HEADER = ["Instrument", "Ticker", "Category", "Type", "Volume", "Open Price", "Open Time (UTC)", "Close Price", "Close Time (UTC)", "Product", "Profit/Loss"]

# The workbook sample, read once by hand from the file (lane 83): 41 transactions, three ETFs, every amount in EUR.
SAMPLE_XLSX_TYPES = {TransactionType.BUY: 31, TransactionType.DEPOSIT: 10}
SAMPLE_XLSX_ASSETS = {"CNDX.UK": "NASDAQ 100", "VWCE.DE": "FTSE All-World", "SXR8.DE": "Core S&P 500"}
SAMPLE_XLSX_OPEN_VOLUMES = {"SXR8.DE": Decimal("1.0652"), "VWCE.DE": Decimal("4.5483"), "CNDX.UK": Decimal("0.5267")}
# The tickers quoted in EUR, the account currency: on them the amount is money(quantity × price) exactly (CNDX.UK is quoted in USD).
SAMPLE_XLSX_EUR_QUOTED = ("SXR8.DE", "VWCE.DE")
CENT = Decimal("0.01")
SAMPLE_XLSX_SUBACCOUNT_TRANSFERS = 20

OLD_CSV_HEADER = "ID;Type;Time;Symbol;Comment;Amount"


# =============================================================================
# HELPERS
# =============================================================================


def _plugin():
    """The registered XTB plugin, reached through the registry (a missing plugin fails the test with its code)."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE}"
    return plugin


def _parse(path: Path) -> BRIMParseOutput:
    return _plugin().parse(path, broker_id=BROKER_ID)


def _notices(out: BRIMParseOutput, code: str) -> List[BRIMNotice]:
    return [notice for notice in out.warnings if notice.code == code]


def _lines_of(out: BRIMParseOutput, code: str) -> List[int]:
    """Every row number the notices of ``code`` list, sorted."""
    return sorted(number for notice in _notices(out, code) for evidence in notice.evidence for number in evidence.row_numbers)


def _reason_of(out: BRIMParseOutput, code: str, line: int) -> str:
    """The reason (last evidence column) given for row ``line`` under ``code``."""
    for notice in _notices(out, code):
        for evidence in notice.evidence:
            for number, cells in zip(evidence.row_numbers, evidence.rows, strict=False):
                if number == line:
                    return cells[-1]
    raise AssertionError(f"row {line} is not listed under {code}: {[(n.code, _lines_of(out, n.code)) for n in out.warnings]}")


def _summary(out: BRIMParseOutput) -> List[Tuple[str, str, Any]]:
    return [(notice.severity, notice.code, notice.context) for notice in out.warnings]


def _by_comment(out: BRIMParseOutput, comment: str):
    """The one transaction whose description holds ``comment`` (the plugin writes the row's comment into it)."""
    found = [tx for tx in out.transactions if comment in (tx.description or "")]
    assert len(found) == 1, f"{len(found)} transaction(s) carry the comment {comment!r}: {[tx.description for tx in out.transactions]}"
    return found[0]


def _symbol_of(out: BRIMParseOutput, asset_id: Optional[int]) -> Optional[str]:
    if asset_id is None:
        return None
    return out.extracted_assets[asset_id].extracted_symbol


# --- the workbook builder -------------------------------------------------------------------------------------------------------------------

T0 = datetime(2025, 3, 3, 9, 0, 0)


@dataclass(frozen=True)
class Cash:
    """One Cash Operations row. ``time`` and ``amount`` are written as given: a datetime / a number, or a string for the unreadable cases."""

    type: str
    time: Any
    amount: Any
    comment: str = ""
    instrument: Optional[str] = None
    ticker: Optional[str] = None
    category: Optional[str] = None
    product: str = "My Trades"
    id: str = ""


@dataclass(frozen=True)
class Position:
    """One aggregate row of Open Positions (``Category`` filled), followed by one lot row (``Category`` empty)."""

    ticker: str
    name: str
    volume: float
    category: str = "ETF"
    product: str = "Investment Plan"


@dataclass
class Built:
    path: Path
    cash_lines: List[int]
    position_lines: List[int]


def _write_workbook(
    path: Path,
    cash: Sequence[Cash],
    *,
    currencies: Sequence[Optional[str]] = ("EUR",),
    positions: Sequence[Position] = (),
    cash_header: Sequence[str] = CASH_HEADER,
    with_summary: bool = True,
) -> Built:
    """A History report as XTB writes it: three sheets, four header lines each, then the table.

    Open Positions opens with the ``Product / Metric / Amount / Currency`` summary (two lines per currency, a ``None`` currency
    leaves the cell empty), a blank row, a note, then the positions table. Returns the 1-based sheet row of every cash row and of
    every aggregate position row, so the evidence is checked against what the file holds, never against a literal.
    """
    book = openpyxl.Workbook()
    closed = book.active
    closed.title = CLOSED_SHEET
    for line in (["Account number", "90000001"], [CLOSED_SHEET], ["Date from (UTC)", datetime(2025, 1, 1)], ["Date to (UTC)", datetime(2025, 12, 31)]):
        closed.append(line)
    closed.append(CLOSED_HEADER)
    closed.append(["Profit/loss"])

    sheet = book.create_sheet(CASH_SHEET)
    for line in (["Account number", "90000001"], [CASH_SHEET], ["Date from (UTC)", datetime(2025, 1, 1)], ["Date to (UTC)", datetime(2025, 12, 31)]):
        sheet.append(line)
    sheet.append(list(cash_header))
    cash_lines: List[int] = []
    for number, row in enumerate(cash, start=1):
        sheet.append([row.type, row.instrument, row.ticker, row.category, row.time, row.amount, row.id or f"90{number:07d}", row.comment, row.product, None])
        cash_lines.append(sheet.max_row)
    sheet.append(["Total", None, None, None, None, 1.0, None, None, None, None])

    opened = book.create_sheet(OPEN_SHEET)
    opened.append(["Account number", "90000001"])
    opened.append([OPEN_SHEET])
    opened.append(["Data as of report generated", datetime(2025, 12, 31)])
    if with_summary:
        opened.append(["Product", "Metric", "Amount", "Currency"])
        for currency in currencies:
            opened.append(["My Trades", "Open position value", 0, currency])
            opened.append(["Investment Plans", "Open position value", 100.5, currency])
    opened.append([None])
    opened.append(["Note", "Summary values and open positions are shown as of the report generation time"])
    opened.append(OPEN_HEADER)
    position_lines: List[int] = []
    for position in positions:
        opened.append([position.product, position.name, position.ticker, position.category, None, position.volume, 100.0, None, 100.0, None])
        position_lines.append(opened.max_row)
        opened.append([position.product, f"#{position.ticker}-lot", position.ticker, None, "BUY", position.volume, 100.0, 100.0, 100.0, datetime(2025, 3, 3)])

    book.save(path)
    return Built(path=path, cash_lines=cash_lines, position_lines=position_lines)


# The baseline: a deposit, a pair of sub-account transfers one second apart, three purchases (one with the ticker in the
# comment, two halves of a partial fill on a fund quoted in USD) and a sale. The open volumes equal the net quantities.
BASE_CASH: Tuple[Cash, ...] = (
    Cash("Deposit", T0, 1000.0, "Invented deposit, id=1"),
    Cash("Subaccount transfer", T0 + timedelta(minutes=5), -500.0, "Transfer from 90000001 to 90000001", product="My Trades"),
    Cash("Subaccount transfer", T0 + timedelta(minutes=5, seconds=1), 500.0, "Transfer from 90000001 to 90000001", product="Investment Plans"),
    Cash("Stock purchase", T0 + timedelta(hours=1), -250.0, "OPEN BUY LFA.DE 2.5 @ 100.00", "Invented Fund A", "LFA.DE", "ETF"),
    Cash("Stock purchase", T0 + timedelta(hours=2), -183.4, "OPEN BUY 2/2.5 @ 99.10", "Invented Fund B", "LFB.UK", "ETF"),
    Cash("Stock purchase", T0 + timedelta(hours=2), -45.85, "OPEN BUY 0.5/2.5 @ 99.10", "Invented Fund B", "LFB.UK", "ETF"),
    Cash("Stock sale", T0 + timedelta(days=1), 52.0, "CLOSE BUY 0.5 @ 104.00", "Invented Fund A", "LFA.DE", "ETF"),
)
BASE_POSITIONS: Tuple[Position, ...] = (Position("LFA.DE", "Invented Fund A", 2.0), Position("LFB.UK", "Invented Fund B", 2.5))
BASE_TRANSACTIONS = 5  # the deposit, three purchases, the sale


def _base(tmp_path: Path, *extra: Cash, **kwargs: Any) -> Built:
    kwargs.setdefault("positions", BASE_POSITIONS)
    return _write_workbook(tmp_path / "xtb-history.xlsx", [*BASE_CASH, *extra], **kwargs)


# =============================================================================
# A. THE WORKBOOK SAMPLE
# =============================================================================


class TestWorkbookSample:
    """The anonymised History report of ``sample_reports/``."""

    def test_recognised_by_the_plugin_and_by_the_registry(self):
        assert _plugin().can_parse(XLSX_SAMPLE) is True
        assert BRIMProviderRegistry.auto_detect_plugin(XLSX_SAMPLE) == PLUGIN_CODE
        assert PLUGIN_CODE in BRIMProviderRegistry.get_compatible_plugins(XLSX_SAMPLE)

    def test_only_the_workbook_is_read(self, tmp_path: Path):
        """2.0.0 dropped the Cash Operations CSV: ``.xlsx`` is the only extension, and a CSV with the old header is not XTB's."""
        path = tmp_path / "xtb-old-export.csv"
        path.write_text(OLD_CSV_HEADER + "\n900000101;Deposit;03.03.2025 09:00:00;;Invented deposit;500\n", encoding="utf-8")

        assert _plugin().supported_extensions == [".xlsx"]
        assert _plugin().can_parse(path) is False
        assert BRIMProviderRegistry.auto_detect_plugin(path) != PLUGIN_CODE

    def test_counts_types_currency_and_no_notice(self):
        out = _parse(XLSX_SAMPLE)

        assert Counter(tx.type for tx in out.transactions) == SAMPLE_XLSX_TYPES
        assert {tx.cash.code for tx in out.transactions} == {"EUR"}
        assert out.warnings == [], _summary(out)
        assert out.validation_issues == []

    def test_signs_follow_the_type(self):
        out = _parse(XLSX_SAMPLE)

        buys = [tx for tx in out.transactions if tx.type == TransactionType.BUY]
        deposits = [tx for tx in out.transactions if tx.type == TransactionType.DEPOSIT]
        assert buys and deposits, "presence barrier: the sample holds purchases and deposits"
        assert all(tx.quantity > 0 and tx.cash.amount < 0 and tx.asset_id is not None for tx in buys)
        assert all(tx.quantity == 0 and tx.cash.amount > 0 and tx.asset_id is None for tx in deposits)

    def test_the_asset_names_come_from_the_instrument_column(self):
        out = _parse(XLSX_SAMPLE)

        assert {info.extracted_symbol: info.extracted_name for info in out.extracted_assets.values()} == SAMPLE_XLSX_ASSETS

    def test_a_partial_fill_imports_the_quantity_of_each_half(self):
        """``OPEN BUY 1/1.8309`` and ``OPEN BUY 0.8309/1.8309``: two rows of one order, each with its own filled quantity and amount."""
        out = _parse(XLSX_SAMPLE)

        first, second = _by_comment(out, "OPEN BUY 1/1.8309 @ 151.66"), _by_comment(out, "OPEN BUY 0.8309/1.8309 @ 151.68")

        assert (first.quantity, first.cash.amount) == (Decimal("1"), Decimal("-151.66"))
        assert (second.quantity, second.cash.amount) == (Decimal("0.8309"), Decimal("-126.03"))
        assert _symbol_of(out, first.asset_id) == _symbol_of(out, second.asset_id) == "VWCE.DE"

    def test_a_ticker_inside_the_comment_is_not_read_as_the_quantity(self):
        out = _parse(XLSX_SAMPLE)

        tx = _by_comment(out, "OPEN BUY VWCE.DE 0.1826 @ 169.86")

        assert (tx.quantity, tx.cash.amount, _symbol_of(out, tx.asset_id)) == (Decimal("0.1826"), Decimal("-31.02"), "VWCE.DE")

    def test_the_sub_account_transfers_are_left_out_without_a_word(self):
        """The sample holds 20 ``Subaccount transfer`` rows (ten +X/−X pairs): none is a transaction, none is listed."""
        book = openpyxl.load_workbook(XLSX_SAMPLE, read_only=True, data_only=True)
        try:
            transfers = sum(1 for row in book[CASH_SHEET].iter_rows(values_only=True) if row and row[0] == "Subaccount transfer")
        finally:
            book.close()
        assert transfers == SAMPLE_XLSX_SUBACCOUNT_TRANSFERS, "guard on the fixture: the sample's transfer rows"

        out = _parse(XLSX_SAMPLE)

        assert not [tx.description for tx in out.transactions if "Subaccount transfer" in (tx.description or "")]
        assert out.warnings == [], _summary(out)

    def test_the_net_imported_quantity_matches_the_open_volume(self):
        """The report covers the whole history: what it imports per instrument is what XTB shows open, hence no notice."""
        out = _parse(XLSX_SAMPLE)

        net: Dict[str, Decimal] = defaultdict(Decimal)
        for tx in out.transactions:
            if tx.type in (TransactionType.BUY, TransactionType.SELL):
                net[_symbol_of(out, tx.asset_id)] += tx.quantity

        assert dict(net) == SAMPLE_XLSX_OPEN_VOLUMES
        assert _notices(out, OUTSIDE_PERIOD) == []

    def test_on_eur_quoted_purchases_the_amount_is_quantity_times_price_in_cents(self):
        """Guard on the anonymised fixture: on an instrument quoted in the account currency the cash is money(quantity × price),
        rounded half-up to the cent, the price read from the comment; and every lot row of Open Positions is worth Volume × Current
        price to the cent. A sample whose figures do not hold together would test the plugin on a state no real export has."""
        out = _parse(XLSX_SAMPLE)

        buys = [tx for tx in out.transactions if tx.type == TransactionType.BUY and _symbol_of(out, tx.asset_id) in SAMPLE_XLSX_EUR_QUOTED]
        assert {_symbol_of(out, tx.asset_id) for tx in buys} == set(SAMPLE_XLSX_EUR_QUOTED), "presence barrier: purchases of both EUR-quoted tickers"
        wrong = []
        for tx in buys:
            price = re.search(r"@\s*([0-9]+(?:\.[0-9]+)?)", tx.description or "")
            assert price, f"no price in the comment of {tx.description!r}"
            expected = (tx.quantity * Decimal(price.group(1))).quantize(CENT, rounding=ROUND_HALF_UP)
            if -tx.cash.amount != expected:
                wrong.append((tx.description, tx.cash.amount, expected))
        assert not wrong, f"purchases whose amount is not quantity × price in cents: {wrong}"

        book = openpyxl.load_workbook(XLSX_SAMPLE, read_only=True, data_only=True)
        try:
            rows = [list(row) for row in book[OPEN_SHEET].iter_rows(values_only=True)]
        finally:
            book.close()
        start = next(index for index, row in enumerate(rows) if {"Ticker", "Category", "Volume", "Value", "Current price"} <= set(row))
        column = {label: position for position, label in enumerate(rows[start]) if label}
        lots = [row for row in rows[start + 1 :] if row[column["Ticker"]] in SAMPLE_XLSX_EUR_QUOTED and not row[column["Category"]]]
        assert {row[column["Ticker"]] for row in lots} == set(SAMPLE_XLSX_EUR_QUOTED), "presence barrier: lot rows of both EUR-quoted tickers"
        wrong_lots = [
            (row[column["Ticker"]], row[column["Volume"]], row[column["Current price"]], row[column["Value"]]) for row in lots if Decimal(repr(row[column["Value"]])) != (Decimal(repr(row[column["Volume"]])) * Decimal(repr(row[column["Current price"]]))).quantize(CENT, rounding=ROUND_HALF_UP)
        ]
        assert not wrong_lots, f"lot rows whose Value is not Volume × Current price in cents: {wrong_lots}"

    def test_a_workbook_without_the_cash_operations_header_is_refused(self, tmp_path: Path):
        """The sample with its Cash Operations header ``Type`` renamed: not an XTB report any more."""
        book = openpyxl.load_workbook(XLSX_SAMPLE)
        sheet = book[CASH_SHEET]
        renamed = 0
        for row in sheet.iter_rows():
            if [cell.value for cell in row[:1]] == ["Type"] and any(cell.value == "Amount" for cell in row):
                row[0].value = "Kind"
                renamed += 1
        assert renamed == 1, f"guard on the fixture: {renamed} Cash Operations header row(s) found"
        path = tmp_path / "xtb-no-header.xlsx"
        book.save(path)

        assert _plugin().can_parse(path) is False
        assert BRIMProviderRegistry.auto_detect_plugin(path) != PLUGIN_CODE
        with pytest.raises(BRIMParseError) as error:
            _parse(path)
        assert error.value.details.get("code") == "header_row_not_found"


# =============================================================================
# B. WORKBOOKS WRITTEN IN tmp_path
# =============================================================================


class TestWorkbookRules:
    """One rule per test, on a small History report built with openpyxl (invented values)."""

    def test_the_baseline_imports_cleanly(self, tmp_path: Path):
        """The builder's own guard: without it, a mistake in the builder would read as a plugin bug in every test below."""
        built = _base(tmp_path)

        assert _plugin().can_parse(built.path) is True
        assert BRIMProviderRegistry.auto_detect_plugin(built.path) == PLUGIN_CODE
        out = _parse(built.path)

        assert len(out.transactions) == BASE_TRANSACTIONS, [tx.description for tx in out.transactions]
        assert out.warnings == [], _summary(out)
        assert {info.extracted_symbol: info.extracted_name for info in out.extracted_assets.values()} == {"LFA.DE": "Invented Fund A", "LFB.UK": "Invented Fund B"}

    def test_a_sale_is_a_sell_with_negative_quantity_and_positive_cash(self, tmp_path: Path):
        out = _parse(_base(tmp_path).path)

        sale = _by_comment(out, "CLOSE BUY 0.5 @ 104.00")

        assert sale.type == TransactionType.SELL
        assert (sale.quantity, sale.cash.amount, sale.cash.code) == (Decimal("-0.5"), Decimal("52.0"), "EUR")
        assert _symbol_of(out, sale.asset_id) == "LFA.DE"

    def test_the_cash_is_the_amount_as_written_not_quantity_times_price(self, tmp_path: Path):
        """A fund quoted in USD: 2 × 99.10 = 198.20 USD, but the account paid 183.40 EUR, the row's ``Amount``."""
        out = _parse(_base(tmp_path).path)

        first, second = _by_comment(out, "OPEN BUY 2/2.5 @ 99.10"), _by_comment(out, "OPEN BUY 0.5/2.5 @ 99.10")

        assert (first.quantity, first.cash.amount, first.cash.code) == (Decimal("2"), Decimal("-183.4"), "EUR")
        assert first.quantity * Decimal("99.10") != -first.cash.amount
        assert (second.quantity, second.cash.amount) == (Decimal("0.5"), Decimal("-45.85"))

    def test_the_account_currency_comes_from_the_summary(self, tmp_path: Path):
        out = _parse(_base(tmp_path, currencies=("PLN",)).path)

        assert len(out.transactions) == BASE_TRANSACTIONS
        assert {tx.cash.code for tx in out.transactions} == {"PLN"}

    def test_an_unknown_type_is_listed_as_not_recognized(self, tmp_path: Path):
        built = _base(tmp_path, Cash("Zorglub bonus", T0 + timedelta(days=2), 7.5, "Invented row"))
        line = built.cash_lines[-1]

        out = _parse(built.path)

        assert len(out.transactions) == BASE_TRANSACTIONS, "the unknown row gives no transaction"
        assert _lines_of(out, ROWS_NOT_RECOGNIZED) == [line]
        assert "zorglub" in _reason_of(out, ROWS_NOT_RECOGNIZED, line).lower()
        notice = _notices(out, ROWS_NOT_RECOGNIZED)[0]
        assert notice.severity == "warning" and notice.context == {"count": 1, "report_issue": True}
        assert _notices(out, ROWS_UNREADABLE) == []

    @pytest.mark.parametrize(
        ("time", "amount", "what"),
        [("not a time", 7.5, "time"), (T0 + timedelta(days=2), "abc", "amount")],
        ids=["time", "amount"],
    )
    def test_an_unreadable_time_or_amount_is_listed_as_unreadable(self, tmp_path: Path, time: Any, amount: Any, what: str):
        built = _base(tmp_path, Cash("Deposit", time, amount, "Invented deposit, id=2"))
        line = built.cash_lines[-1]

        out = _parse(built.path)

        assert len(out.transactions) == BASE_TRANSACTIONS, "the unreadable row gives no transaction"
        assert _lines_of(out, ROWS_UNREADABLE) == [line]
        assert what in _reason_of(out, ROWS_UNREADABLE, line).lower()
        notice = _notices(out, ROWS_UNREADABLE)[0]
        assert notice.severity == "warning" and (notice.context or {}).get("report_issue") is True
        assert _notices(out, ROWS_NOT_RECOGNIZED) == []

    def test_a_sub_account_transfer_without_its_opposite_is_not_recognized(self, tmp_path: Path):
        built = _base(tmp_path, Cash("Subaccount transfer", T0 + timedelta(days=3), 75.0, "Transfer from 90000001 to 90000001"))
        line = built.cash_lines[-1]

        out = _parse(built.path)

        assert len(out.transactions) == BASE_TRANSACTIONS
        assert _lines_of(out, ROWS_NOT_RECOGNIZED) == [line], "only the lone transfer is listed: the baseline's pair stays silent"
        assert (_notices(out, ROWS_NOT_RECOGNIZED)[0].context or {}).get("report_issue") is True

    def test_two_opposite_transfers_further_apart_than_the_window_are_both_listed(self, tmp_path: Path):
        """A pair is two opposite amounts within 2 seconds; three seconds apart, neither has an opposite."""
        when = T0 + timedelta(days=3)
        built = _base(
            tmp_path,
            Cash("Subaccount transfer", when, -75.0, "Transfer from 90000001 to 90000001"),
            Cash("Subaccount transfer", when + timedelta(seconds=3), 75.0, "Transfer from 90000001 to 90000001", product="Investment Plans"),
        )

        out = _parse(built.path)

        assert _lines_of(out, ROWS_NOT_RECOGNIZED) == built.cash_lines[-2:]

    def test_an_unreadable_sub_account_transfer_is_listed_as_unreadable(self, tmp_path: Path):
        built = _base(tmp_path, Cash("Subaccount transfer", "not a time", 75.0, "Transfer from 90000001 to 90000001"))

        out = _parse(built.path)

        assert _lines_of(out, ROWS_UNREADABLE) == [built.cash_lines[-1]]
        assert _notices(out, ROWS_NOT_RECOGNIZED) == []

    @pytest.mark.parametrize(
        "kwargs",
        [{"currencies": (None,)}, {"with_summary": False}],
        ids=["empty-currency-cells", "no-summary"],
    )
    def test_a_missing_account_currency_is_refused_with_its_code(self, tmp_path: Path, kwargs: Dict[str, Any]):
        built = _base(tmp_path, **kwargs)
        assert _plugin().can_parse(built.path) is True, "presence barrier: the workbook is still an XTB report"

        with pytest.raises(BRIMParseError) as error:
            _parse(built.path)

        assert error.value.details.get("code") == CURRENCY_MISSING

    def test_two_account_currencies_are_refused_with_their_code(self, tmp_path: Path):
        built = _base(tmp_path, currencies=("EUR", "USD"))

        with pytest.raises(BRIMParseError) as error:
            _parse(built.path)

        assert error.value.details.get("code") == CURRENCY_AMBIGUOUS
        assert error.value.details.get("context") == {"currencies": "EUR, USD"}

    def test_an_open_volume_the_report_does_not_explain_gives_one_info_notice(self, tmp_path: Path):
        """LFA.DE: 3 open, 2 imported (bought before the period); LFX.DE: open, never traded in the period; LFB.UK matches."""
        positions = (Position("LFA.DE", "Invented Fund A", 3.0), BASE_POSITIONS[1], Position("LFX.DE", "Invented Fund X", 1.25))
        built = _base(tmp_path, positions=positions)

        out = _parse(built.path)

        assert len(out.transactions) == BASE_TRANSACTIONS
        assert [notice.code for notice in out.warnings] == [OUTSIDE_PERIOD], _summary(out)
        notice = out.warnings[0]
        assert notice.severity == "info" and notice.context == {"count": 2}
        evidence = notice.evidence[0]
        assert evidence.headers == ["Ticker", "Instrument", "Open volume", "Imported quantity"]
        assert evidence.rows == [["LFA.DE", "Invented Fund A", "3", "2"], ["LFX.DE", "Invented Fund X", "1.25", "0"]]
        assert evidence.row_numbers == [built.position_lines[0], built.position_lines[2]]

    def test_a_cfd_position_is_never_compared(self, tmp_path: Path):
        """CFDs are not imported: an open CFD is not a quantity the report should explain."""
        built = _base(tmp_path, positions=(*BASE_POSITIONS, Position("LFCFD", "Invented CFD", 4.0, category="CFD")))

        out = _parse(built.path)

        assert out.warnings == [], _summary(out)

    @pytest.mark.parametrize(
        ("volumes", "expected_rows"),
        [((1.0, 2.0), []), ((1.5, 2.5), [["LFA.DE", "Fund A", "4", "3"]])],
        ids=["sum-matches", "sum-differs"],
    )
    def test_the_open_volume_of_a_ticker_is_the_sum_of_its_sub_accounts(self, tmp_path: Path, volumes: Tuple[float, float], expected_rows: List[List[str]]):
        """One ticker held in two sub-accounts has one aggregate Open Positions row in each: their sum is compared with the net
        imported quantity (1 bought in My Trades + 2 in Investment Plans = 3), and a difference is one evidence row per ticker,
        numbered with the ticker's first aggregate row."""
        cash = (
            Cash("Deposit", T0, 1000.0, "Invented deposit, id=1"),
            Cash("Stock purchase", T0 + timedelta(hours=1), -100.0, "OPEN BUY 1 @ 100.00", "Fund A", "LFA.DE", "ETF", product="My Trades"),
            Cash("Stock purchase", T0 + timedelta(hours=2), -200.0, "OPEN BUY 2 @ 100.00", "Fund A", "LFA.DE", "ETF", product="Investment Plans"),
        )
        positions = (Position("LFA.DE", "Fund A", volumes[0], product="My Trades"), Position("LFA.DE", "Fund A", volumes[1], product="Investment Plan"))
        built = _write_workbook(tmp_path / "xtb-two-sub-accounts.xlsx", cash, positions=positions)

        out = _parse(built.path)

        assert len(out.transactions) == 3, [tx.description for tx in out.transactions]
        if not expected_rows:
            assert out.warnings == [], _summary(out)
            return
        assert [notice.code for notice in out.warnings] == [OUTSIDE_PERIOD], _summary(out)
        notice = out.warnings[0]
        assert notice.severity == "info" and notice.context == {"count": 1}
        assert notice.evidence[0].rows == expected_rows
        assert notice.evidence[0].row_numbers == [built.position_lines[0]]

    def test_a_workbook_with_no_importable_row_says_so(self, tmp_path: Path):
        """Only an unknown row: no transaction, the row listed, and the plain string that says nothing was imported."""
        built = _write_workbook(tmp_path / "xtb-unknown-only.xlsx", [Cash("Zorglub bonus", T0, 1.0, "Invented row")])

        out = _parse(built.path)

        assert out.transactions == []
        assert _lines_of(out, ROWS_NOT_RECOGNIZED) == built.cash_lines
        assert [notice.message for notice in _notices(out, "legacy")] == ["No valid transactions found in file"], _summary(out)

    def test_the_total_row_is_left_out_without_a_word(self, tmp_path: Path):
        """The builder always ends Cash Operations with a ``Total`` row (amount 1.0): no transaction, no notice."""
        out = _parse(_base(tmp_path).path)

        assert not [tx for tx in out.transactions if (tx.description or "").startswith("Total")]
        assert out.warnings == [], _summary(out)


# =============================================================================
# C. THE SIGN OF THE CASH (lot 83-B)
# =============================================================================

D1 = T0 + timedelta(days=10)

# The extra rows of the mixed file: each normal-signed one is imported with the Amount as written; the refund is the only notice.
MIXED_EXTRA: Tuple[Cash, ...] = (
    Cash("Dividend", D1, 3.12, "LFD.US USD 0.2630/ SHR", "Invented Dividend Co", "LFD.US", "STC"),
    Cash("Withholding tax", D1, -0.47, "LFD.US USD WHT 15%", "Invented Dividend Co", "LFD.US", "STC"),
    Cash("Withholding tax", D1 + timedelta(days=30), 0.47, "LFD.US USD WHT refund", "Invented Dividend Co", "LFD.US", "STC"),
    Cash("Free funds interests", D1, 1.1, "Free-funds Interest 2025-03"),
    Cash("Free funds interests tax", D1, -0.21, "Free-funds Interest Tax 2025-03"),
    Cash("Commission", D1, -2.0, "Invented commission"),
    Cash("Withdrawal", D1, -100.0, "Invented withdrawal"),
)


def _subfolder(tmp_path: Path, name: str) -> Path:
    """A fresh folder under ``tmp_path``: the baseline and the variant of one test each get their own workbook."""
    folder = tmp_path / name
    folder.mkdir()
    return folder


def _row_key(out: BRIMParseOutput, tx) -> Tuple[str, Any, Decimal, Decimal, str, Optional[str], str]:
    return (tx.type.value, tx.date, tx.quantity, tx.cash.amount, tx.cash.code, _symbol_of(out, tx.asset_id), tx.description or "")


class TestCashSign:
    """The cash keeps the sign of ``Amount``: a tax given back is a refund, every other wrong sign is a row to look at."""

    @pytest.mark.parametrize(
        ("row", "symbol"),
        [
            (Cash("Withholding tax", D1, 0.52, "LFD.US USD WHT refund", "Invented Dividend Co", "LFD.US", "STC"), "LFD.US"),
            (Cash("Free funds interests tax", D1, 0.3, "Free-funds Interest Tax correction"), None),
        ],
        ids=["with-ticker", "no-ticker"],
    )
    def test_a_positive_tax_is_an_interest_tax_refund_with_an_info_notice(self, tmp_path: Path, row: Cash, symbol: Optional[str]):
        built = _base(tmp_path, row)
        line = built.cash_lines[-1]

        out = _parse(built.path)

        assert len(out.transactions) == BASE_TRANSACTIONS + 1
        refund = _by_comment(out, row.comment)
        assert refund.type == TransactionType.INTEREST
        assert (refund.quantity, refund.cash.amount, refund.cash.code) == (Decimal("0"), Decimal(repr(row.amount)), "EUR")
        assert (refund.description or "").startswith("Tax refund: "), refund.description
        assert _symbol_of(out, refund.asset_id) == symbol

        assert [notice.code for notice in out.warnings] == [TAX_REFUND], _summary(out)
        notice = out.warnings[0]
        assert notice.severity == "info" and notice.context == {"count": 1}
        evidence = notice.evidence[0]
        assert evidence.headers == CASH_HEADER
        assert evidence.row_numbers == [line]
        cells = dict(zip(CASH_HEADER, evidence.rows[0], strict=True))
        assert (cells["Type"], cells["Ticker"], cells["Amount"], cells["Comment"]) == (row.type, row.ticker or "", repr(row.amount), row.comment)

    @pytest.mark.parametrize(
        ("row", "tx_type", "sign"),
        [
            (Cash("Dividend", D1, -1.5, "LFD.US USD 0.1000/ SHR", "Invented Dividend Co", "LFD.US", "STC"), TransactionType.DIVIDEND, "negative"),
            (Cash("Free funds interests", D1, -0.3, "Corr Free-funds Interest 2025-02"), TransactionType.INTEREST, "negative"),
            (Cash("Deposit", D1, -100.0, "Invented deposit reversal"), TransactionType.DEPOSIT, "negative"),
            (Cash("Commission", D1, 2.0, "Invented commission refund"), TransactionType.FEE, "positive"),
            (Cash("Withdrawal", D1, 50.0, "Invented withdrawal reversal"), TransactionType.WITHDRAWAL, "positive"),
            (Cash("Stock purchase", D1, 100.0, "OPEN BUY 1 @ 100.00", "Invented Fund A", "LFA.DE", "ETF"), TransactionType.BUY, "positive"),
            (Cash("Stock sale", D1, -100.0, "CLOSE BUY 1 @ 100.00", "Invented Fund A", "LFA.DE", "ETF"), TransactionType.SELL, "negative"),
        ],
        ids=["dividend-negative", "interest-negative", "deposit-negative", "fee-positive", "withdrawal-positive", "purchase-positive", "sale-negative"],
    )
    def test_any_other_sign_that_does_not_fit_is_not_recognized(self, tmp_path: Path, row: Cash, tx_type: TransactionType, sign: str):
        built = _base(tmp_path, row)
        line = built.cash_lines[-1]

        out = _parse(built.path)

        assert len(out.transactions) == BASE_TRANSACTIONS, "the row gives no transaction, never a flipped one"
        assert _lines_of(out, ROWS_NOT_RECOGNIZED) == [line], _summary(out)
        reason = _reason_of(out, ROWS_NOT_RECOGNIZED, line).lower()
        assert tx_type.value.lower() in reason and f"{sign} amount" in reason, reason
        assert (_notices(out, ROWS_NOT_RECOGNIZED)[0].context or {}).get("report_issue") is True
        assert [notice.code for notice in out.warnings] == [ROWS_NOT_RECOGNIZED], _summary(out)

    @pytest.mark.parametrize(
        "row",
        [
            Cash("Stock purchase", D1, 0, "OPEN BUY 1 @ 100.00", "Invented Fund A", "LFA.DE", "ETF"),
            Cash("Stock sale", D1, 0.0, "CLOSE BUY 1 @ 100.00", "Invented Fund A", "LFA.DE", "ETF"),
        ],
        ids=["purchase", "sale"],
    )
    def test_a_trade_of_amount_zero_is_not_recognized(self, tmp_path: Path, row: Cash):
        built = _base(tmp_path, row)
        line = built.cash_lines[-1]

        out = _parse(built.path)

        assert len(out.transactions) == BASE_TRANSACTIONS
        assert _lines_of(out, ROWS_NOT_RECOGNIZED) == [line], _summary(out)
        assert "amount 0" in _reason_of(out, ROWS_NOT_RECOGNIZED, line).lower()

    @pytest.mark.parametrize(
        "row",
        [
            Cash("Deposit", D1, 0, "Invented deposit of nothing"),
            Cash("Dividend", D1, 0.0, "LFD.US USD 0.0000/ SHR", "Invented Dividend Co", "LFD.US", "STC"),
            Cash("Withholding tax", D1, 0, "LFD.US USD WHT 0%", "Invented Dividend Co", "LFD.US", "STC"),
            Cash("Free funds interests", D1, 0.0, "Free-funds Interest 2025-03"),
        ],
        ids=["deposit", "dividend", "tax", "interest"],
    )
    def test_a_cash_row_of_amount_zero_is_left_out_without_a_word(self, tmp_path: Path, row: Cash):
        base = _parse(_base(_subfolder(tmp_path, "base")).path)
        out = _parse(_base(tmp_path, row).path)

        assert sorted(_row_key(out, tx) for tx in out.transactions) == sorted(_row_key(base, tx) for tx in base.transactions)
        assert out.warnings == [], _summary(out)

    def test_normal_rows_and_a_refund_together_change_nothing_else(self, tmp_path: Path):
        """A dividend, its withholding, the withholding given back a month later, an interest and its tax, a commission and a
        withdrawal on top of the baseline: the baseline's transactions are unchanged, each normal row is imported with its Amount
        as written, the refund is an INTEREST, and the only notice is the refund's."""
        base = _parse(_base(_subfolder(tmp_path, "base")).path)
        built = _base(tmp_path, *MIXED_EXTRA)
        refund_line = built.cash_lines[len(BASE_CASH) + 2]

        out = _parse(built.path)

        added = Counter(_row_key(out, tx) for tx in out.transactions) - Counter(_row_key(base, tx) for tx in base.transactions)
        assert sum(added.values()) == len(MIXED_EXTRA) == len(out.transactions) - len(base.transactions), "every baseline transaction is still there, plus one per extra row"
        assert Counter(key[0] for key in added.elements()) == Counter({"DIVIDEND": 1, "TAX": 2, "INTEREST": 2, "FEE": 1, "WITHDRAWAL": 1})

        for row in MIXED_EXTRA:
            tx = _by_comment(out, row.comment)
            assert tx.cash.amount == Decimal(repr(row.amount)), f"{row.comment}: cash {tx.cash.amount}, Amount {row.amount}"
            assert tx.cash.code == "EUR"
        assert _by_comment(out, "LFD.US USD WHT refund").type == TransactionType.INTEREST
        assert _by_comment(out, "LFD.US USD WHT 15%").type == TransactionType.TAX
        assert _symbol_of(out, _by_comment(out, "Invented commission").asset_id) is None

        assert [notice.code for notice in out.warnings] == [TAX_REFUND], _summary(out)
        assert out.warnings[0].context == {"count": 1}
        assert out.warnings[0].evidence[0].row_numbers == [refund_line]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
