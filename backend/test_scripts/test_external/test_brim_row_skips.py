"""
Test Suite: the rows a BRIM plugin leaves out — «known rows quietly, unknown rows loudly» (W-B86, D-W85-4)

The developer's principle (19/10/2026, skill ``brim-plugin`` rule 10): a row the plugin knows it can drop is dropped without a
word (at most a log line). A row it does not recognise, cannot read, or whose economic effect it does not import is left out
WITH a ``severity="warning"`` notice whose ``context["report_issue"]`` is True: the wizard then shows «open an issue on GitHub»,
so the users become the canaries of a broker whose export changes.

What is pinned:

- A. the shared helper ``_brim_io.RowSkips`` (already written, so these are guards): grouping, order, context, evidence shape,
  short rows padded, nothing collected → no notice;
- B. the rows each in-scope plugin leaves out, one small file per case (a sample of ``sample_reports/`` with one row appended, found
  by its file LINE NUMBER, never by position or wording): the code of the notice, ``report_issue``, no transaction from the row;
  the rows that stay silent; the version bumps; the samples (which rows each lists, and that a normal row still imports); a plain
  string warning that is not one of the rows above is unchanged;
- C. the contract, over EVERY registered plugin: it is either in ``ROW_SKIPS_BY_PLUGIN`` (and obeys it) or in ``ROW_SKIPS_PENDING``
  (the beta decision of 19/10/2026: W-B86 covers only the stable plugins), never both, never neither;
- D. the four catalogue keys the two shared codes need, in EN/IT/FR/ES.

DEGIRO and Scalable also have their own files (``test_brim_degiro.py``, ``test_brim_scalable.py``) for the cases that need their
synthetic writers; Danske Bank has its own cure and test (``test_brim_danske_bank.py``).

PURE: samples and files written in ``tmp_path``, no server, no database, no network, no clock.
"""

from __future__ import annotations

import csv
import functools
import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.schemas.brim import BRIMNotice, BRIMParseOutput
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.brim_providers import _brim_io as brim_io
from scripts.i18n_catalog import load_catalog

# =============================================================================
# CONSTANTS
# =============================================================================

SAMPLE_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"
BROKER_ID = 1
ROWS_NOT_RECOGNIZED = "rows_not_recognized"
ROWS_UNREADABLE = "rows_unreadable"
SHARED_CODES = (ROWS_NOT_RECOGNIZED, ROWS_UNREADABLE)
UI_LANGUAGES = ("en", "it", "fr", "es")

# The plugins W-B86 and D-W85-4 cover, and the plugin that has its own cure and test.
OWN_CODE_DANSKE = "broker_danske_bank"

# The plugins the beta decision of 19/10/2026 leaves out («only the stable plugins»): their rows left out are not classified yet.
ROW_SKIPS_PENDING = frozenset(
    {
        "broker_avanza",
        "broker_bitvavo",
        "broker_bux",
        "broker_coinbase",
        "broker_cointracking",
        "broker_cryptocom",
        "broker_delta",
        "broker_disnat",
        "broker_fineco",
        "broker_finpension",
        "broker_freetrade",
        "broker_generic_csv",
        "broker_intesa",
        "broker_investengine",
        "broker_investimental",
        "broker_parqet",
        "broker_rabobank",
        "broker_relai",
        "broker_saxo",
        "broker_schwab",
        "broker_xtb",
    }
)

# The version each plugin bumps to (the output for the same file changes: its notices). DEGIRO and Scalable pin theirs in their own files.
NEW_VERSIONS = {
    "broker_credit_agricole": "1.5.0",
    "broker_directa": "1.1.0",
    "broker_revolut": "1.2.0",
    "broker_trading212": "1.1.0",
    "broker_etoro": "1.2.0",
    "broker_traderepublic": "1.1.0",
    "broker_swissquote": "1.1.0",
    "broker_ibkr": "1.1.0",
}


# =============================================================================
# HELPERS
# =============================================================================


def _plugin(code: str):
    """The registered plugin ``code``; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(code)
    assert plugin is not None, f"no BRIM plugin is registered as {code}"
    return plugin


def _registered() -> List[str]:
    BRIMProviderRegistry.auto_discover()
    return sorted(BRIMProviderRegistry._providers)


@functools.cache
def _parse_sample(code: str, name: str) -> BRIMParseOutput:
    """The plugin's parse of an untouched sample (cached: a sample never changes inside a run)."""
    return _plugin(code).parse(SAMPLE_DIR / name, broker_id=BROKER_ID)


def _physical_lines(name: str) -> List[str]:
    """The lines of a sample as the file has them (BOM dropped), the first one being line 1."""
    return (SAMPLE_DIR / name).read_bytes().decode("utf-8-sig").splitlines()


def _listing(out: BRIMParseOutput, code: str, line: int) -> List[Tuple[BRIMNotice, List[str]]]:
    """The notices of ``code`` whose evidence lists file line ``line``, each with the evidence row of that line."""
    found = []
    for notice in out.warnings:
        if notice.code != code:
            continue
        for evidence in notice.evidence:
            for number, cells in zip(evidence.row_numbers, evidence.rows, strict=False):
                if number == line:
                    found.append((notice, list(cells)))
    return found


def _lines_of(out: BRIMParseOutput, code: str) -> List[int]:
    """Every file line the notices of ``code`` list, sorted."""
    return sorted(number for notice in out.warnings if notice.code == code for evidence in notice.evidence for number in evidence.row_numbers)


# =============================================================================
# A. THE SHARED HELPER — guards, GREEN today
# =============================================================================

HEADERS = ["Date", "Type", "Amount"]


class TestRowSkipsHelper:
    """A — ``RowSkips`` groups the rows a plugin leaves out into at most two notices, ``rows_not_recognized`` first, each a warning that asks for a report."""

    def test_the_two_codes_are_the_shared_ones(self):
        assert (brim_io.ROWS_NOT_RECOGNIZED, brim_io.ROWS_UNREADABLE) == (ROWS_NOT_RECOGNIZED, ROWS_UNREADABLE)

    def test_nothing_collected_gives_no_notice(self):
        skips = brim_io.RowSkips(HEADERS)

        assert (bool(skips), skips.count(), skips.count(ROWS_NOT_RECOGNIZED), skips.count(ROWS_UNREADABLE), skips.notices()) == (False, 0, 0, 0, [])

    def test_a_collected_row_is_counted_by_code_and_in_total(self):
        skips = brim_io.RowSkips(HEADERS)
        skips.unreadable(9, ["x", "y", "z"], "a date")
        skips.unknown(4, ["a", "b", "c"], "b")
        skips.unknown(6, ["a", "b2", "c"], "b2")

        assert (bool(skips), skips.count(), skips.count(ROWS_NOT_RECOGNIZED), skips.count(ROWS_UNREADABLE)) == (True, 3, 2, 1)

    def test_the_notices_are_grouped_by_code_unknown_first_whatever_the_order_of_collection(self):
        skips = brim_io.RowSkips(HEADERS)
        skips.unreadable(9, ["09/01", "Buy", "abc"], "amount")
        skips.unknown(4, ["04/01", "Zorglub", "1"], "Zorglub")
        skips.unreadable(7, ["07/01", "Buy", ""], "amount")

        notices = skips.notices()

        assert [notice.code for notice in notices] == [ROWS_NOT_RECOGNIZED, ROWS_UNREADABLE]
        assert [[number for evidence in notice.evidence for number in evidence.row_numbers] for notice in notices] == [[4], [9, 7]], "the rows keep the order they were collected in"

    def test_each_notice_is_a_warning_that_asks_for_a_report_with_its_count(self):
        skips = brim_io.RowSkips(HEADERS)
        skips.unknown(4, ["04/01", "Zorglub", "1"], "Zorglub")
        skips.unknown(5, ["05/01", "Zorglub", "2"], "Zorglub")
        skips.unreadable(9, ["09/01", "Buy", "abc"], "amount")

        by_code = {notice.code: notice for notice in skips.notices()}

        assert {code: (notice.severity, notice.context) for code, notice in by_code.items()} == {
            ROWS_NOT_RECOGNIZED: ("warning", {"count": 2, "report_issue": True}),
            ROWS_UNREADABLE: ("warning", {"count": 1, "report_issue": True}),
        }
        assert all(notice.message.strip() for notice in by_code.values()), "an English fallback message"

    def test_the_evidence_is_one_table_with_the_header_a_reason_column_and_the_cells_as_text(self):
        skips = brim_io.RowSkips(HEADERS)
        skips.unknown(4, ["04/01", None, 12], "the type")

        (notice,) = skips.notices()

        assert len(notice.evidence) == 1
        evidence = notice.evidence[0]
        assert (evidence.title, evidence.headers, evidence.rows, evidence.row_numbers) == ("", [*HEADERS, "Reason"], [["04/01", "", "12", "the type"]], [4])
        assert evidence.comment and evidence.comment.strip(), "a table without a comment is a grid of numbers"

    def test_a_row_shorter_than_the_header_is_padded_with_empty_cells(self):
        skips = brim_io.RowSkips(HEADERS)
        skips.unreadable(3, ["only"], "fewer columns than the header")

        (notice,) = skips.notices()

        assert notice.evidence[0].headers == [*HEADERS, "Reason"]
        assert notice.evidence[0].rows == [["only", "", "", "fewer columns than the header"]]

    def test_a_row_longer_than_the_header_gets_numbered_headers_and_the_others_are_padded(self):
        skips = brim_io.RowSkips(HEADERS)
        skips.unknown(3, ["a", "b", "c", "d", "e"], "wide")
        skips.unknown(4, ["a"], "narrow")

        (notice,) = skips.notices()
        evidence = notice.evidence[0]

        assert evidence.headers == [*HEADERS, "#4", "#5", "Reason"]
        assert evidence.rows == [["a", "b", "c", "d", "e", "wide"], ["a", "", "", "", "", "narrow"]]
        assert all(len(row) == len(evidence.headers) for row in evidence.rows), "every row is as wide as its headers"

    def test_a_helper_without_headers_numbers_every_column(self):
        skips = brim_io.RowSkips()
        skips.unknown(2, ["a", "b"], "no header")

        (notice,) = skips.notices()

        assert notice.evidence[0].headers == ["#1", "#2", "Reason"]


# =============================================================================
# B. THE ROWS EACH PLUGIN LEAVES OUT
# =============================================================================

Row = Union[Sequence[str], Mapping[str, str]]


@dataclass(frozen=True)
class SkipCase:
    """One row appended to a sample, and what the plugin owes for it.

    ``row`` is the cells of the new line, or a ``{column name: value}`` dict laid out under the sample's first line (the names are
    compared lowercase, a column the dict does not name is empty). ``code`` is the notice the row must be listed under, with
    ``severity``; ``extra_transactions`` is how many transactions the row gives (0: left out; 1: imported, but a part of it is not);
    ``reason_has`` is a lowercase text the reason of the evidence row must hold (the shared codes only).
    """

    id: str
    plugin: str
    sample: str
    row: Row
    code: str
    kind: str = "unknown"
    delimiter: str = ";"
    severity: str = "warning"
    extra_transactions: int = 0
    reason_has: Optional[str] = None


@dataclass(frozen=True)
class SilentCase:
    """A row the plugin knows it can drop: no transaction, and not a word in any notice."""

    id: str
    plugin: str
    sample: str
    row: Row
    delimiter: str = ","


@dataclass(frozen=True)
class OnlyRowCase:
    """A file with the sample's first ``keep_lines`` lines and one row: no transaction at all, so a plain string warning is left that is none of the rows' business."""

    id: str
    plugin: str
    sample: str
    row: Row
    keep_lines: int
    delimiter: str
    message_has: str


def _first_line_cells(sample: str, delimiter: str) -> List[str]:
    return next(csv.reader([_physical_lines(sample)[0]], delimiter=delimiter))


def _row_cells(sample: str, row: Row, delimiter: str) -> List[str]:
    """The cells of a case's row: as given, or by column name under the first line of the sample."""
    if not isinstance(row, Mapping):
        return list(row)
    values = {name.strip().lower(): value for name, value in row.items()}
    return [values.get(name.strip().lower(), "") for name in _first_line_cells(sample, delimiter)]


def _write_with_row(folder: Path, sample: str, row: Row, delimiter: str, *, keep_lines: Optional[int] = None) -> Tuple[Path, int]:
    """The sample, or its first ``keep_lines`` lines, plus one row; returns the file and the 1-based line of the new row."""
    raw = (SAMPLE_DIR / sample).read_bytes()
    if keep_lines is not None:
        raw = b"".join(raw.splitlines(keepends=True)[:keep_lines])
    if not raw.endswith(b"\n"):
        raw += b"\n"
    buffer = io.StringIO()
    csv.writer(buffer, delimiter=delimiter, lineterminator="\n").writerow(_row_cells(sample, row, delimiter))
    path = folder / sample
    path.write_bytes(raw + buffer.getvalue().encode("utf-8"))
    return path, raw.count(b"\n") + 1


# --- the rows -----------------------------------------------------------------------------------------------------------------------------------


def _degiro_row(description: str, day: str = "22-09-2025") -> List[str]:
    """A 12-column Account Statement row: date, time, value date, product, ISIN, description, FX, change currency, amount, balance currency, balance, Order Id."""
    return [day, "10:00", day, "", "", description, "", "EUR", "5,00", "EUR", "100,00", ""]


_DIRECTA_ROW = ["27-12-2024", "27-12-2024", "Provento etf", "IEMB", "IE00B2NPKV68", "YYYYYYY", "ISHARES JPMORGAN", "0", "20.95", "0", "EUR", ""]
_SWISSQUOTE_ROW = ["10-08-2022 15:30:02", "113947121", "Buy", "ORFN", "CONSTRAINED CAPITAL", "US8863645383", "200.0", "19.85", "5.96", "0.00", "-3975.96", "168660.08", "USD"]
_IBKR_ROW = ["BUY", "20240130", "US0378331005", "5", "190", "950", "USD", "-1", "USD"]
_TR_ROW = ["2025-02-03", "Aankoop", "-10", "Test fund", "IE00BKX55T58", "1", "", ""]


def _with(cells: Sequence[str], **positions: str) -> List[str]:
    """``cells`` with the cells at the given 0-based positions replaced (``c3="x"`` is position 3)."""
    changed = list(cells)
    for key, value in positions.items():
        changed[int(key[1:])] = value
    return changed


_SCALABLE_ROW = {"date": "2026-05-04", "time": "10:00:00", "reference": "SCALROWSKIP1", "description": "Synthetic movement", "assetType": "Cash", "type": "Deposit", "amount": "100", "currency": "EUR", "lf_id": "synthSKIP000000001", "lf_account_index": "1"}

SKIP_CASES: Tuple[SkipCase, ...] = (
    # --- DEGIRO: six codes of its own, all with report_issue; one small statement per code is in test_brim_degiro.py
    SkipCase("degiro-unknown-description", "broker_degiro", "degiro-account-en.csv", _degiro_row("Zorglub bonification"), "degiro_unknown_rows"),
    SkipCase("degiro-unreadable-date", "broker_degiro", "degiro-account-en.csv", _degiro_row("iDEAL Deposit", day="99-99-2025"), "degiro_unknown_rows", kind="unreadable"),
    # --- Crédit Agricole: three codes of its own get report_issue
    SkipCase("ca-securities-unknown-causale", "broker_credit_agricole", "credit_agricole-export.csv", ["12/07/2026", "FONDO PROVA", "EUR", "CAUSALE MAI VISTA", "10,00", "EUR", "1", "5", "50,00", "12/07/2026"], "ca_securities_unknown_causale"),
    SkipCase("ca-account-invalid-amount", "broker_credit_agricole", "credit_agricole-conti.csv", ["12/07/2026", "12/07/2026", "ACCREDITO EMOLUMENTI", "PROVA", "'abc", "EUR"], "ca_account_invalid_amount", kind="unreadable"),
    SkipCase("ca-account-unknown-causale", "broker_credit_agricole", "credit_agricole-conti.csv", ["12/07/2026", "12/07/2026", "OPERAZIONE MAI VISTA", "QUALCOSA DI NUOVO", "'-250,00", "EUR"], "ca_unknown_causale", severity="info", extra_transactions=1),
    # --- Scalable: a status nobody knows is unknown, an empty one is unreadable (the known not-executed ones are silent: test_brim_scalable.py)
    SkipCase("scalable-unknown-status", "broker_scalable", "scalable-prime-export.csv", {**_SCALABLE_ROW, "status": "On hold"}, ROWS_NOT_RECOGNIZED, reason_has="on hold"),
    SkipCase("scalable-empty-status", "broker_scalable", "scalable-prime-export.csv", {**_SCALABLE_ROW, "status": ""}, ROWS_UNREADABLE, kind="unreadable"),
    SkipCase("scalable-unreadable-date", "broker_scalable", "scalable-prime-export.csv", {**_SCALABLE_ROW, "status": "Executed", "date": ""}, "scalable_unreadable_rows", kind="unreadable"),
    SkipCase("scalable-security-transfer", "broker_scalable", "scalable-prime-export.csv", {**_SCALABLE_ROW, "status": "Executed", "type": "Security transfer", "assetType": "Security", "isin": "IE00B4L5Y983", "shares": "7", "amount": "0"}, "scalable_not_imported"),
    SkipCase("scalable-deposit-unknown-status", "broker_scalable_deposit", "scalable-deposit-export.csv", {**_SCALABLE_ROW, "status": "On hold", "lf_account": "deposit"}, ROWS_NOT_RECOGNIZED, reason_has="on hold"),
    SkipCase("scalable-deposit-empty-status", "broker_scalable_deposit", "scalable-deposit-export.csv", {**_SCALABLE_ROW, "status": "", "lf_account": "deposit"}, ROWS_UNREADABLE, kind="unreadable"),
    # --- Directa: four string warnings become two codes
    SkipCase("directa-unknown-type", "broker_directa", "directa-export.csv", _with(_DIRECTA_ROW, c2="Zorglub"), ROWS_NOT_RECOGNIZED, delimiter=",", reason_has="zorglub"),
    SkipCase("directa-unreadable-date", "broker_directa", "directa-export.csv", _with(_DIRECTA_ROW, c0="99-99-2024"), ROWS_UNREADABLE, kind="unreadable", delimiter=","),
    SkipCase("directa-missing-type", "broker_directa", "directa-export.csv", _with(_DIRECTA_ROW, c2=""), ROWS_UNREADABLE, kind="unreadable", delimiter=","),
    SkipCase("directa-insufficient-columns", "broker_directa", "directa-export.csv", _DIRECTA_ROW[:3], ROWS_UNREADABLE, kind="unreadable", delimiter=","),
    # --- Revolut: a stock split is no longer silent
    SkipCase("revolut-stock-split", "broker_revolut", "revolut-invest-export.csv", ["2024-01-15T10:00:00.000Z", "AAPL", "STOCK SPLIT", "1", "", "$0", "USD", "1.0"], ROWS_NOT_RECOGNIZED, delimiter=",", reason_has="stock split"),
    # --- Trading 212: a stock split, a stock distribution and a currency conversion are no longer silent
    SkipCase(
        "trading212-stock-split", "broker_trading212", "trading212-export.csv", {"Action": "Stock split open", "Time": "2025-03-24 07:24:24.104", "ISIN": "CA46500E8678", "Ticker": "ISOU", "Name": "IsoEnergy", "No. of shares": "7.45"}, ROWS_NOT_RECOGNIZED, delimiter=",", reason_has="stock split"
    ),
    SkipCase(
        "trading212-stock-distribution",
        "broker_trading212",
        "trading212-export.csv",
        {"Action": "Stock distribution", "Time": "2025-01-23 14:46:06.327", "ISIN": "US9078181081", "Ticker": "PALAF", "Name": "Union Pacific", "No. of shares": "11.05"},
        ROWS_NOT_RECOGNIZED,
        delimiter=",",
        reason_has="stock distribution",
    ),
    SkipCase("trading212-currency-conversion", "broker_trading212", "trading212-export.csv", {"Action": "Currency conversion", "Time": "2025-01-24 10:00:00", "Total": "10.00", "Currency (Total)": "EUR"}, ROWS_NOT_RECOGNIZED, delimiter=",", reason_has="currency conversion"),
    # --- eToro: overnight fees, overnight refunds and stamp duty are no longer silent
    SkipCase("etoro-overnight-fee", "broker_etoro", "etoro-export.csv", {"Date": "15/04/2025 00:46:41", "Type": "Overnight fee", "Details": "Daily", "Amount": "(0,10)", "Units": "-", "Position ID": "1074146905", "Asset type": "CFD"}, ROWS_NOT_RECOGNIZED, delimiter=",", reason_has="overnight fee"),
    SkipCase(
        "etoro-overnight-refund", "broker_etoro", "etoro-export.csv", {"Date": "20/05/2025 01:31:04", "Type": "Overnight refund", "Details": "Daily", "Amount": "0,21", "Units": "-", "Position ID": "624957573", "Asset type": "CFD"}, ROWS_NOT_RECOGNIZED, delimiter=",", reason_has="overnight refund"
    ),
    SkipCase("etoro-sdrt", "broker_etoro", "etoro-export.csv", {"Date": "10/07/2025 15:15:01", "Type": "SDRT", "Details": "HNKE/USD", "Amount": "(6.97)", "Units": "-", "Position ID": "1", "Asset type": "Stocks"}, ROWS_NOT_RECOGNIZED, delimiter=",", reason_has="sdrt"),
    # --- Trade Republic: a fee or a tax column is not imported (the row is); the strings become two codes
    SkipCase("traderepublic-fee-column", "broker_traderepublic", "traderepublic-export.csv", _with(_TR_ROW, c6="-1.0"), ROWS_NOT_RECOGNIZED, extra_transactions=1),
    SkipCase("traderepublic-tax-column", "broker_traderepublic", "traderepublic-export.csv", _with(_TR_ROW, c7="-0.5"), ROWS_NOT_RECOGNIZED, extra_transactions=1),
    SkipCase("traderepublic-unknown-type", "broker_traderepublic", "traderepublic-export.csv", _with(_TR_ROW, c1="Zorglub"), ROWS_NOT_RECOGNIZED, reason_has="zorglub"),
    SkipCase("traderepublic-invalid-date", "broker_traderepublic", "traderepublic-export.csv", _with(_TR_ROW, c0="03/02/xx"), ROWS_UNREADABLE, kind="unreadable"),
    SkipCase("traderepublic-invalid-amount", "broker_traderepublic", "traderepublic-export.csv", _with(_TR_ROW, c2="abc"), ROWS_UNREADABLE, kind="unreadable"),
    SkipCase("traderepublic-missing-isin", "broker_traderepublic", "traderepublic-export.csv", _with(_TR_ROW, c4=""), ROWS_UNREADABLE, kind="unreadable"),
    # --- Swissquote: a forex leg and an unknown transaction are unknown; the values a row needs are unreadable
    SkipCase("swissquote-forex-credit", "broker_swissquote", "swissquote-export.csv", _with(_SWISSQUOTE_ROW, c2="Forex Credit"), ROWS_NOT_RECOGNIZED, reason_has="forex credit"),
    SkipCase("swissquote-forex-debit", "broker_swissquote", "swissquote-export.csv", _with(_SWISSQUOTE_ROW, c2="Forex Debit"), ROWS_NOT_RECOGNIZED, reason_has="forex debit"),
    SkipCase("swissquote-unknown-transaction", "broker_swissquote", "swissquote-export.csv", _with(_SWISSQUOTE_ROW, c2="Zorglub"), ROWS_NOT_RECOGNIZED, reason_has="zorglub"),
    SkipCase("swissquote-invalid-date", "broker_swissquote", "swissquote-export.csv", _with(_SWISSQUOTE_ROW, c0="99-99-2022 15:30:02"), ROWS_UNREADABLE, kind="unreadable"),
    SkipCase("swissquote-missing-net-amount", "broker_swissquote", "swissquote-export.csv", _with(_SWISSQUOTE_ROW, c10=""), ROWS_UNREADABLE, kind="unreadable"),
    SkipCase("swissquote-zero-net-amount", "broker_swissquote", "swissquote-export.csv", _with(_SWISSQUOTE_ROW, c10="0.00"), ROWS_UNREADABLE, kind="unreadable"),
    SkipCase("swissquote-missing-currency", "broker_swissquote", "swissquote-export.csv", _with(_SWISSQUOTE_ROW, c12=""), ROWS_UNREADABLE, kind="unreadable"),
    SkipCase("swissquote-missing-isin-and-symbol", "broker_swissquote", "swissquote-export.csv", _with(_SWISSQUOTE_ROW, c3="", c5=""), ROWS_UNREADABLE, kind="unreadable"),
    SkipCase("swissquote-non-positive-quantity", "broker_swissquote", "swissquote-export.csv", _with(_SWISSQUOTE_ROW, c6="0"), ROWS_UNREADABLE, kind="unreadable"),
    # --- IBKR: an unknown direction and a trade without an ISIN (an FX trade) are unknown; a date that cannot be read is unreadable
    SkipCase("ibkr-unknown-direction", "broker_ibkr", "ibkr-trades-export.csv", _with(_IBKR_ROW, c0="TRANSFER"), ROWS_NOT_RECOGNIZED, delimiter=",", reason_has="transfer"),
    SkipCase("ibkr-no-isin", "broker_ibkr", "ibkr-trades-export.csv", _with(_IBKR_ROW, c2=""), ROWS_NOT_RECOGNIZED, delimiter=","),
    SkipCase("ibkr-invalid-date", "broker_ibkr", "ibkr-trades-export.csv", _with(_IBKR_ROW, c1="99999999"), ROWS_UNREADABLE, kind="unreadable", delimiter=","),
)
CASES_BY_ID: Dict[str, SkipCase] = {case.id: case for case in SKIP_CASES}

SILENT_CASES: Tuple[SilentCase, ...] = (
    SilentCase("revolut-transfer", "broker_revolut", "revolut-invest-export.csv", ["2024-01-15T10:00:00.000Z", "AAPL", "TRANSFER FROM REVOLUT TRADING LTD TO REVOLUT SECURITIES EUROPE UAB", "1", "", "$0", "USD", "1.0"]),
    SilentCase("trading212-transfer", "broker_trading212", "trading212-export.csv", {"Action": "Transfer out", "Time": "2025-02-28 08:25:01.076", "ISIN": "DE000A3GK2N1", "Ticker": "XBTI", "Name": "DDA Funds Physical Bitcoin", "No. of shares": "595"}),
)

# A plain string warning that is none of the rows above stays a string (code ``legacy``, no ``report_issue``): the sample or the one-row file that gives it, and a text of its message.
ONLY_ROW_CASES: Tuple[OnlyRowCase, ...] = (
    OnlyRowCase("directa-no-valid-transactions", "broker_directa", "directa-export.csv", _with(_DIRECTA_ROW, c2="Zorglub"), 10, ",", "Nessuna transazione valida"),
    OnlyRowCase("traderepublic-no-valid-transactions", "broker_traderepublic", "traderepublic-export.csv", _with(_TR_ROW, c1="Zorglub"), 1, ";", "No valid transactions found"),
    OnlyRowCase("swissquote-no-valid-transactions", "broker_swissquote", "swissquote-export.csv", _with(_SWISSQUOTE_ROW, c2="Zorglub"), 1, ";", "No valid transactions found"),
    OnlyRowCase("ibkr-no-valid-transactions", "broker_ibkr", "ibkr-trades-export.csv", _with(_IBKR_ROW, c2=""), 1, ",", "No valid transactions found"),
)


def _case_ids(cases: Sequence[Any]) -> List[str]:
    return [case.id for case in cases]


def _parse_case(case: Union[SkipCase, SilentCase], folder: Path) -> Tuple[BRIMParseOutput, BRIMParseOutput, int]:
    """The untouched sample's parse, the parse of the sample with the case's row, and the line of that row."""
    path, line = _write_with_row(folder, case.sample, case.row, case.delimiter)
    return _parse_sample(case.plugin, case.sample), _plugin(case.plugin).parse(path, broker_id=BROKER_ID), line


class TestRowsLeftOut:
    """B — a row a plugin does not recognise, cannot read, or does not fully import is listed under its code with ``report_issue``, and its line."""

    @pytest.mark.parametrize("case", SKIP_CASES, ids=_case_ids(SKIP_CASES))
    def test_the_row_is_listed_under_its_code_with_its_line_and_asks_for_a_report(self, case: SkipCase, tmp_path: Path):
        """The new line is in the evidence of exactly one notice of ``case.code``: its severity, ``context.report_issue`` True; the row gives
        ``extra_transactions`` transaction(s); and no plain string warning names the line any more."""
        base, out, line = _parse_case(case, tmp_path)

        listed = _listing(out, case.code, line)
        assert len(listed) == 1, f"{case.id}: line {line} is listed by {len(listed)} notice(s) {case.code}; the parse gives {[(n.code, n.severity, _lines_of(out, n.code)) for n in out.warnings]}"
        notice, cells = listed[0]
        assert notice.severity == case.severity, f"{case.id}: severity {notice.severity!r}, expected {case.severity!r}"
        assert (notice.context or {}).get("report_issue") is True, f"{case.id}: context {notice.context}, report_issue must be True"
        assert len(out.transactions) - len(base.transactions) == case.extra_transactions, f"{case.id}: the row gives {len(out.transactions) - len(base.transactions)} transaction(s), expected {case.extra_transactions}"
        assert not [n.message for n in out.warnings if n.code == "legacy" and re.search(rf"\b(Row|Riga) {line}\b", n.message)], f"{case.id}: a plain string warning still names line {line}"
        if case.reason_has:
            assert case.reason_has in cells[-1].lower(), f"{case.id}: the reason {cells[-1]!r} must name {case.reason_has!r}"

    @pytest.mark.parametrize("case", [case for case in SKIP_CASES if case.code in SHARED_CODES], ids=lambda case: case.id)
    def test_a_shared_notice_counts_its_rows_and_shows_the_header_and_a_reason(self, case: SkipCase, tmp_path: Path):
        """``context.count`` is the number of rows the table lists; every row has a non-empty reason in its last column, one more than the headers' file columns."""
        _, out, line = _parse_case(case, tmp_path)
        listed = _listing(out, case.code, line)
        assert listed, f"{case.id}: presence barrier: line {line} is in no notice {case.code}; the parse gives {[(n.code, _lines_of(out, n.code)) for n in out.warnings]}"
        notice = listed[0][0]
        evidence = notice.evidence[0]

        assert (notice.context or {}).get("count") == len(evidence.row_numbers) == len(evidence.rows)
        assert all(len(row) == len(evidence.headers) for row in evidence.rows), f"{case.id}: a row is not as wide as its headers"
        assert all(row[-1].strip() for row in evidence.rows), f"{case.id}: a row without a reason"
        assert evidence.comment and evidence.comment.strip()

    @pytest.mark.parametrize("case", SILENT_CASES, ids=_case_ids(SILENT_CASES))
    def test_a_row_the_plugin_knows_it_may_drop_is_dropped_without_a_word(self, case: SilentCase, tmp_path: Path):
        """Guard (green today and after): a transfer has no economic effect in the file's own words: no transaction, and the notices are those of the sample."""
        base, out, _ = _parse_case(case, tmp_path)

        assert len(out.transactions) == len(base.transactions), f"{case.id}: the row gives a transaction"
        assert [notice.model_dump() for notice in out.warnings] == [notice.model_dump() for notice in base.warnings], f"{case.id}: the row changed the notices"

    @pytest.mark.parametrize("case", ONLY_ROW_CASES, ids=_case_ids(ONLY_ROW_CASES))
    def test_a_plain_string_warning_that_is_not_one_of_the_rows_is_unchanged(self, case: OnlyRowCase, tmp_path: Path):
        """Guard (green today and after): a file with no valid row still says so in a plain string (code ``legacy``, no ``report_issue``)."""
        path, _ = _write_with_row(tmp_path, case.sample, case.row, case.delimiter, keep_lines=case.keep_lines)

        out = _plugin(case.plugin).parse(path, broker_id=BROKER_ID)

        legacy = [notice for notice in out.warnings if notice.code == "legacy" and case.message_has in notice.message]
        assert out.transactions == [] and len(legacy) == 1, f"{case.id}: {[(n.code, n.message) for n in out.warnings]}"
        assert not (legacy[0].context or {}).get("report_issue")

    def test_the_revolut_crypto_layout_keeps_its_plain_string_warnings(self):
        """Guard (green today and after): the crypto sample's unsupported types (Send, Receive, Stake, Staking reward) stay six plain strings, none of them a shared code."""
        out = _parse_sample("broker_revolut", "revolut-crypto-export.csv")

        assert sorted(notice.code for notice in out.warnings) == ["legacy"] * 6, [(notice.code, notice.message) for notice in out.warnings]
        assert all("unsupported crypto type" in notice.message for notice in out.warnings)
        assert len(out.transactions) == 10

    def test_the_swissquote_dividend_quantity_note_stays_a_plain_string(self):
        """Guard (green today and after): «DIVIDEND source quantity … discarded» describes a row that is imported: three plain strings in the sample."""
        out = _parse_sample("broker_swissquote", "swissquote-export.csv")

        notes = [notice for notice in out.warnings if notice.code == "legacy" and "DIVIDEND source quantity" in notice.message]
        assert len(notes) == 3, [(notice.code, notice.message) for notice in out.warnings]


# --- the samples ----------------------------------------------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class SampleListing:
    """What a sample lists under the shared codes after the cure: ``{line: text the line holds}`` for each code; nothing else is listed."""

    plugin: str
    sample: str
    not_recognized: Mapping[int, str] = field(default_factory=dict)
    unreadable: Mapping[int, str] = field(default_factory=dict)


SAMPLE_LISTINGS: Tuple[SampleListing, ...] = (
    SampleListing("broker_degiro", "degiro-export.csv"),
    SampleListing("broker_degiro", "degiro-account-en.csv"),
    SampleListing("broker_credit_agricole", "credit_agricole-export.csv"),
    SampleListing("broker_credit_agricole", "credit_agricole-conti.csv"),
    SampleListing("broker_scalable", "scalable-prime-export.csv"),
    SampleListing("broker_scalable", "scalable-broker-export.csv"),
    SampleListing("broker_scalable_deposit", "scalable-deposit-export.csv"),
    # Directa's sample holds a type nobody knows (line 34) and a row without a type (line 35)
    SampleListing("broker_directa", "directa-export.csv", not_recognized={34: "Pippo"}, unreadable={35: "31-05-2024,,"}),
    # The stock split of the Invest layout; the crypto layout has none of the rows
    SampleListing("broker_revolut", "revolut-invest-export.csv", not_recognized={9: "STOCK SPLIT"}),
    SampleListing("broker_revolut", "revolut-crypto-export.csv"),
    # A stock distribution (11) and a stock split (13, 14); the transfer (12) is silent
    SampleListing("broker_trading212", "trading212-export.csv", not_recognized={11: "Stock distribution", 13: "Stock split close", 14: "Stock split open"}),
    SampleListing("broker_etoro", "etoro-export.csv", not_recognized={24: "Overnight fee", 26: "Overnight fee", 27: "Overnight refund", 29: "SDRT"}),
    # The two rows with a fee: they are imported, their fee is not
    SampleListing("broker_traderepublic", "traderepublic-export.csv", not_recognized={9: "Sell", 10: "Buy"}),
    SampleListing("broker_swissquote", "swissquote-export.csv", not_recognized={3: "Forex credit", 4: "Forex debit", 10: "Forex credit", 11: "Forex debit"}),
    # The three FX trades of the trades sample (no ISIN)
    SampleListing("broker_ibkr", "ibkr-trades-export.csv", not_recognized={10: "SELL", 11: "SELL", 12: "SELL"}),
    SampleListing("broker_ibkr", "ibkr-default-currency-export.csv"),
)

# What each sample imported before the cure and must keep importing: a normal row of the sample still gives its transaction.
SAMPLE_TRANSACTIONS = {
    ("broker_degiro", "degiro-export.csv"): 57,
    ("broker_degiro", "degiro-account-en.csv"): 17,
    ("broker_credit_agricole", "credit_agricole-export.csv"): 156,
    ("broker_credit_agricole", "credit_agricole-conti.csv"): 24,
    ("broker_scalable", "scalable-prime-export.csv"): 17,
    ("broker_scalable", "scalable-broker-export.csv"): 19,
    ("broker_scalable_deposit", "scalable-deposit-export.csv"): 9,
    ("broker_directa", "directa-export.csv"): 23,
    ("broker_revolut", "revolut-invest-export.csv"): 8,
    ("broker_revolut", "revolut-crypto-export.csv"): 10,
    ("broker_trading212", "trading212-export.csv"): 12,
    ("broker_etoro", "etoro-export.csv"): 23,
    ("broker_traderepublic", "traderepublic-export.csv"): 9,
    ("broker_swissquote", "swissquote-export.csv"): 17,
    ("broker_ibkr", "ibkr-trades-export.csv"): 16,
    ("broker_ibkr", "ibkr-default-currency-export.csv"): 2,
}
CA_CODES = ("ca_securities_unknown_causale", "ca_unknown_causale", "ca_account_invalid_amount")


def _listing_id(listing: SampleListing) -> str:
    return f"{listing.plugin}-{listing.sample}"


class TestSamples:
    """B — what each sample lists under the shared codes (the rows it holds that the plugin does not recognise or does not import), and that a normal row still imports."""

    @pytest.mark.parametrize("listing", SAMPLE_LISTINGS, ids=[_listing_id(listing) for listing in SAMPLE_LISTINGS])
    def test_the_expected_lines_hold_the_text_the_listing_names(self, listing: SampleListing):
        """Guard on the fixture (green today): each line the listing expects is in the file and holds the text it names."""
        lines = _physical_lines(listing.sample)

        wrong = {line: text for line, text in {**listing.not_recognized, **listing.unreadable}.items() if line > len(lines) or text.lower() not in lines[line - 1].lower()}

        assert not wrong, f"{listing.sample}: these lines do not hold the text the listing names: {wrong}"

    @pytest.mark.parametrize("listing", SAMPLE_LISTINGS, ids=[_listing_id(listing) for listing in SAMPLE_LISTINGS])
    def test_the_sample_lists_exactly_the_rows_it_holds_that_are_left_out(self, listing: SampleListing):
        """``rows_not_recognized`` lists exactly the lines expected and ``rows_unreadable`` exactly its own; a sample with none lists neither code."""
        out = _parse_sample(listing.plugin, listing.sample)
        assert out.transactions, f"presence barrier: {listing.sample} gives no transaction"

        assert (_lines_of(out, ROWS_NOT_RECOGNIZED), _lines_of(out, ROWS_UNREADABLE)) == (sorted(listing.not_recognized), sorted(listing.unreadable))

    @pytest.mark.parametrize("listing", SAMPLE_LISTINGS, ids=[_listing_id(listing) for listing in SAMPLE_LISTINGS])
    def test_every_shared_notice_of_the_sample_is_a_warning_that_asks_for_a_report(self, listing: SampleListing):
        out = _parse_sample(listing.plugin, listing.sample)

        shared = [notice for notice in out.warnings if notice.code in SHARED_CODES]

        assert sorted(notice.code for notice in shared) == sorted(code for code, rows in ((ROWS_NOT_RECOGNIZED, listing.not_recognized), (ROWS_UNREADABLE, listing.unreadable)) if rows), f"{listing.sample}: {[(n.code, _lines_of(out, n.code)) for n in shared]}"
        assert [notice.code for notice in shared if notice.severity != "warning" or (notice.context or {}).get("report_issue") is not True] == []

    @pytest.mark.parametrize(("plugin", "sample"), sorted(SAMPLE_TRANSACTIONS), ids=[f"{plugin}-{sample}" for plugin, sample in sorted(SAMPLE_TRANSACTIONS)])
    def test_a_normal_row_of_the_sample_still_imports(self, plugin: str, sample: str):
        """Guard (green today and after): the sample gives the transactions it gave before the cure."""
        assert len(_parse_sample(plugin, sample).transactions) == SAMPLE_TRANSACTIONS[(plugin, sample)]

    def test_the_directa_sample_has_no_plain_string_warning_left(self):
        """The two string warnings of the sample (an unknown type, a missing type) are the two shared codes now."""
        out = _parse_sample("broker_directa", "directa-export.csv")

        assert [(notice.code, notice.message) for notice in out.warnings if notice.code == "legacy"] == []

    @pytest.mark.parametrize("sample", ["traderepublic-export.csv"])
    def test_the_traderepublic_sample_has_no_plain_string_warning_left(self, sample: str):
        out = _parse_sample("broker_traderepublic", sample)

        assert [(notice.code, notice.message) for notice in out.warnings if notice.code == "legacy"] == []

    def test_the_ca_samples_give_none_of_the_three_codes_that_ask_for_a_report(self):
        """Guard (green today and after): the two Crédit Agricole samples hold no unknown causale and no invalid amount."""
        found = {(sample, notice.code) for sample in ("credit_agricole-export.csv", "credit_agricole-conti.csv") for notice in _parse_sample("broker_credit_agricole", sample).warnings if notice.code in CA_CODES}

        assert found == set()


class TestVersions:
    """B — the output for the same file changes (its notices), so every plugin bumps its version and the files already parsed offer a new parse."""

    @pytest.mark.parametrize(("code", "version"), sorted(NEW_VERSIONS.items()), ids=sorted(NEW_VERSIONS))
    def test_the_plugin_version_is_bumped(self, code: str, version: str):
        assert _plugin(code).plugin_version == version, f"{code}: plugin_version is {_plugin(code).plugin_version!r}, expected {version}"


# =============================================================================
# C. THE CONTRACT — over every registered plugin
# =============================================================================


@dataclass(frozen=True)
class PluginSkips:
    """How a plugin is held to «known rows quietly, unknown rows loudly».

    ``unknown`` and ``unreadable`` are the ids of the ``SKIP_CASES`` that build a file with such a row (None: the plugin has no such row
    to report, and ``note`` says why). ``own_test`` names the file that tests a plugin with its own cure.
    """

    unknown: Optional[str]
    unreadable: Optional[str]
    note: str = ""
    own_test: Optional[str] = None


_ONLY_SKIPPED_TYPES = "its other warnings stay plain strings (D-W85-4 adds only a minimal aggregated notice for the rows it used to skip in silence)"

ROW_SKIPS_BY_PLUGIN: Dict[str, PluginSkips] = {
    "broker_degiro": PluginSkips("degiro-unknown-description", "degiro-unreadable-date", "both are degiro_unknown_rows, with report_issue"),
    "broker_credit_agricole": PluginSkips("ca-securities-unknown-causale", "ca-account-invalid-amount"),
    "broker_scalable": PluginSkips("scalable-unknown-status", "scalable-empty-status"),
    "broker_scalable_deposit": PluginSkips("scalable-deposit-unknown-status", "scalable-deposit-empty-status"),
    "broker_directa": PluginSkips("directa-unknown-type", "directa-unreadable-date"),
    "broker_revolut": PluginSkips("revolut-stock-split", None, f"no unreadable row is reported: {_ONLY_SKIPPED_TYPES}"),
    "broker_trading212": PluginSkips("trading212-stock-split", None, f"no unreadable row is reported: {_ONLY_SKIPPED_TYPES}"),
    "broker_etoro": PluginSkips("etoro-overnight-fee", None, f"no unreadable row is reported: {_ONLY_SKIPPED_TYPES}"),
    "broker_traderepublic": PluginSkips("traderepublic-unknown-type", "traderepublic-invalid-date"),
    "broker_swissquote": PluginSkips("swissquote-unknown-transaction", "swissquote-invalid-date"),
    "broker_ibkr": PluginSkips("ibkr-unknown-direction", "ibkr-invalid-date"),
    OWN_CODE_DANSKE: PluginSkips(None, None, "own code, tested in test_brim_danske_bank.py (W-B85)", own_test="test_brim_danske_bank.py"),
}

CONTRACT_PARAMS = [pytest.param(plugin, kind, getattr(skips, kind), id=f"{plugin}-{kind}") for plugin, skips in sorted(ROW_SKIPS_BY_PLUGIN.items()) for kind in ("unknown", "unreadable") if getattr(skips, kind) is not None]


class TestTheContract:
    """C — every registered plugin is classified, and each in-scope plugin leaves no row out silently."""

    def test_every_registered_plugin_is_in_exactly_one_set(self):
        registered = set(_registered())
        in_scope, pending = set(ROW_SKIPS_BY_PLUGIN), set(ROW_SKIPS_PENDING)

        assert not in_scope & pending, f"in both ROW_SKIPS_BY_PLUGIN and ROW_SKIPS_PENDING: {sorted(in_scope & pending)}"
        unclassified = sorted(registered - in_scope - pending)
        assert not unclassified, (
            f"new plugin(s) {unclassified}: classify each. A stable plugin goes in ROW_SKIPS_BY_PLUGIN with how to build a file with an unknown row and an unreadable one "
            f"(skill brim-plugin rule 10: known rows quietly, unknown rows loudly, report_issue); a beta plugin goes in ROW_SKIPS_PENDING with the reason written here "
            f"(beta decision of 19/10/2026, W-B86: only the stable plugins)."
        )
        stale = sorted((in_scope | pending) - registered)
        assert not stale, f"classified but not registered (renamed or removed?): {stale}"

    def test_a_plugin_with_a_case_names_the_cases_of_its_own_plugin(self):
        problems = []
        for plugin, skips in ROW_SKIPS_BY_PLUGIN.items():
            for kind in ("unknown", "unreadable"):
                case_id = getattr(skips, kind)
                if case_id is None:
                    continue
                case = CASES_BY_ID.get(case_id)
                if case is None:
                    problems.append(f"{plugin}: {kind} names the case {case_id!r}, which does not exist")
                elif case.plugin != plugin or case.kind != kind:
                    problems.append(f"{plugin}: {kind} names {case_id!r}, a {case.kind} case of {case.plugin}")
            if skips.own_test is None and skips.unknown is None:
                problems.append(f"{plugin}: no unknown-row case and no own test")
            if (skips.unknown is None or skips.unreadable is None) and not skips.note.strip():
                problems.append(f"{plugin}: a missing case needs a note saying why")
        assert not problems, problems

    def test_the_plugin_with_its_own_cure_has_its_test_file(self):
        folder = Path(__file__).parent
        missing = [skips.own_test for skips in ROW_SKIPS_BY_PLUGIN.values() if skips.own_test and not (folder / skips.own_test).is_file()]

        assert not missing, f"the tests of the plugins with their own cure are not here: {missing}"

    @pytest.mark.parametrize(("plugin", "kind", "case_id"), CONTRACT_PARAMS)
    def test_a_row_left_out_is_never_lost_in_silence(self, plugin: str, kind: str, case_id: str, tmp_path: Path):
        """The contract: the row is listed in a ``warning`` notice that asks for a report and names its line (a row that is imported in part, as the unknown causale of
        Crédit Agricole, is listed too), and an unreadable row gives no transaction — no row is lost without a word."""
        case = CASES_BY_ID[case_id]
        base, out, line = _parse_case(case, tmp_path)

        imported = len(out.transactions) > len(base.transactions)
        listed = [notice for notice in out.warnings if notice.severity == "warning" and (notice.context or {}).get("report_issue") is True and line in {number for evidence in notice.evidence for number in evidence.row_numbers}]
        assert listed, f"{plugin}: the {kind} row on line {line} is in no warning notice with report_issue: {[(n.code, n.severity, n.context) for n in out.warnings]}"
        assert not (kind == "unreadable" and imported), f"{plugin}: the unreadable row on line {line} is imported"
        assert not [n.message for n in out.warnings if n.code == "legacy" and re.search(rf"\b(Row|Riga) {line}\b", n.message)], f"{plugin}: a plain string warning still names line {line}"


# =============================================================================
# D. THE CATALOGUE — the keys the two shared codes need
# =============================================================================

SHARED_KEYS = [f"importWizard.{family}.{code}" for family in ("brimNotice", "brimEvidence") for code in SHARED_CODES]


def _entry(catalogue: Dict[str, Any], key: str) -> Any:
    """The entry at a dotted i18n key, or None when a part of the path is missing."""
    node: Any = catalogue
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


class TestTheCatalogue:
    """D — the wizard words the two shared notices (``importWizard.brimNotice.<code>``) and the comment under their table (``importWizard.brimEvidence.<code>``)
    in the UI language; the notice takes the row count as the ICU variable ``count``."""

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    def test_the_four_keys_have_a_wording(self, language: str):
        catalogue = load_catalog(language, fallback=False)

        missing = [key for key in SHARED_KEYS if not isinstance(_entry(catalogue, key), str) or not _entry(catalogue, key).strip()]

        assert not missing, f"{language}.json: {len(missing)} of {len(SHARED_KEYS)} key(s) missing or empty: {missing}"

    @pytest.mark.parametrize("language", UI_LANGUAGES)
    @pytest.mark.parametrize("code", SHARED_CODES)
    def test_the_notice_takes_the_row_count_as_an_icu_variable(self, language: str, code: str):
        text = _entry(load_catalog(language, fallback=False), f"importWizard.brimNotice.{code}")

        assert isinstance(text, str) and "{count" in text, f"{language}.json importWizard.brimNotice.{code} must use the ICU variable {{count}} (the notice context has it): {text!r}"
