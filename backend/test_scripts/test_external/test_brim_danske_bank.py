"""
Test Suite: Danske Bank report sets, phase B — the ``broker_danske_bank`` plugin

Written red-first, before the plugin (plan step 4, §4 B0, "Specifica di dettaglio").
The plugin does not exist yet, so it is looked up in ``BRIMProviderRegistry`` inside
every test (``_danske``): the module always collects, and each test fails on its own,
saying the plugin is missing. The tests whose docstring starts with "Fixture guard"
check the writers of this file, not the product: they pass before and after phase B.

What is pinned (B0, and design v5.3 §3.4.2–§3.4.4, §3.5, §7.1):

- identity and contract: code, name, extensions, priority, version, icon, docs page,
  roles, settlement lag, pre-checkpoint policy, history tag, ``test_sample_sets``;
- recognition: ``can_parse`` (the members and its own combined files; never a foreign
  or unreadable file, and never an exception), ``detect_role``, ``describe_member``
  (coverage per axis, an account fingerprint that never serialises), ``describe_set``;
- reading: a Latin-1, cp1252 or UTF-8 cash statement; the fee header with ``<br>`` or a
  space; the currency column unnamed, named ``Valuutta`` or empty; dates as text or as
  date cells; numbers as cells or as Finnish text;
- classification (S1), rule M (D-S28), pairing (S2–S4), the zones table cell by cell,
  the truth points (C_i, border orphans, A13, proven gaps, the final verification, the
  balance chain, the proofs E1–E4 and their conflicts);
- the combined format: headers, value formats, order, privacy (no ``Säilytystili``), purity;
- the parse of the combined file: transactions, tags, descriptions, assets, todos,
  notices, evidence, and checkpoints and verifications rebuilt from the truth rows;
- lot W-B85, known rows quietly and unknown rows loudly: a «Varaus» cash row is a
  ``reservation``, left out with no notice and one backend log line; every other row not
  booked stays ``status``, and its notice asks the user to open an issue (``report_issue``);
  every other notice is left as it is;
- lot B-52, the operation date (developer's decision, 19/10/2026): a paired trade, a paired
  ``Tuotto`` and a demerger line are recorded on the custody ``Kauppapäivä``; a cash-only
  row keeps its ``Pvm``. Pairing, zones, ``not_yet_settled`` and ``deferred_rows`` stay on
  the value date. Every truth at a day D is stated in operation-date terms: it adds what is
  in flight at D, meaning the trades imported as pairs that are traded on or before D and
  settled after it. The cash truth adds their cash, a position adds their quantity, a
  verification adds their cash. The plugin is 1.1.0 (``TestOperationDateTruths`` and the
  updated pins);
- lot B-52, the A13 sets (developer's decision, 20/10/2026): a set whose cash statement
  starts after its custody export opens like any other, on the eve of the custody export,
  and the opening's cash is the statement's first balance. A trade straddling the
  statement's start is imported on its trade date, after the opening, which subtracts it
  from its positions; a trade settled before the statement stays left out
  (``outside_cash_coverage``), its cash in that balance and its shares in the opening;
- the exact facts of the two synthetic sample sets, "main" and "gap";
- project 66, wave P2c (``TestLinkedCharges``, P2 contract §6): a trade whose sum works out is recorded at
  quantity × Kurssi with its commission as a linked FEE, and one info notice lists those trades; a trade whose sum does
  not work out keeps its charges todo; a zero difference has neither; the withdrawal tax names the one withdrawal of its
  day. Compared with the snapshots of version 1.1.0 in ``brim_previous_outputs/broker_danske_bank/``.

Edge cases are built in temporary folders by two small writers: an XLSX custody export
(dates as text unless asked otherwise) and a cash statement written the way the bank
writes it (Latin-1, ``;``, LF, newest first, the running ``Saldo`` computed from the
rows). Every value is invented. No server, no shared database. The module is pure, except
for the end-to-end proofs of lot B-52: they run the gap-fix (``brim_gap_fix``) on a private
in-memory SQLite database of their own, never the lane's. The one log it reads is read with
``structlog.testing.capture_logs``, behind a barrier: a canary through the plugin module's
own logger must reach it.

Design: LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/design-phase00BrimReportSets.md (v5.3)
Plan: LibreFolio_developer_journal/Release_2/phases/26_brimDanskeBank/plan-phase00BrimDanskeBankStep4Implementation.prompt.md, §4 B0
"""

from __future__ import annotations

import csv
import importlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple

import openpyxl
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel
from structlog.testing import capture_logs

import backend.app.db.models  # noqa: F401 — registers the app tables on SQLModel.metadata (the B-52 end-to-end proofs)
from backend.app.schemas.brim import COMBINED_REQUIRED_HEADERS, BRIMCombinedTable, BRIMCoverage, BRIMGapFixRequest, BRIMParseOutput, BRIMReportRole, BRIMSetShape, is_fake_asset_id
from backend.app.schemas.common import DateRangeModel
from backend.app.services.brim import brim_report_sets
from backend.app.services.brim.brim_gap_fix import compute_gap_fix
from backend.app.services.brim.brim_provider import BRIMProvider, BRIMSetRequiredError
from backend.app.services.brim.combined_files import write_combined_csv
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.test_scripts.brim_charge_links import LINK_FIELDS, RowKey, assert_charge_link_structure, assert_expected_charge_links, load_previous_snapshot, sample_reimport_report, version_tuple
from backend.test_scripts.brim_samples import SampleDir

# =============================================================================
# CONSTANTS
# =============================================================================

PLUGIN_CODE = "broker_danske_bank"
PLUGIN_MODULE = "backend.app.services.brim_providers.broker_danske_bank.plugin"
SAMPLE_DIR = SampleDir()
BROKER_ID = 1
# The deposit account of the custody samples. It is an account number: it never leaves the members.
ACCOUNT = "SYNTH-0001"

MAIN_SET = {"custody": ["danske_bank-custody.xlsx"], "cash": ["danske_bank-cash.csv"]}
GAP_SET = {"custody": ["danske_bank-gap-custody-1.xlsx", "danske_bank-gap-custody-2.xlsx"], "cash": ["danske_bank-gap-cash.csv"]}
SAMPLE_SETS = {"main": MAIN_SET, "gap": GAP_SET}
SAMPLE_ROLES = {name: role for sample_set in SAMPLE_SETS.values() for role, names in sample_set.items() for name in names}

CUSTODY_HEADER: Tuple[Optional[str], ...] = ("Kauppapäivä", "Arvopäivä", "Sijoituskohde", "Määrä", "Kurssi", "Palkkio<br/>sis. Alv", "Summa", None, "Tila", "Toimeksiantotyyppi", "Säilytystili")
CASH_HEADER = ("Pvm", "Saaja/Maksaja", "Määrä", "Saldo", "Tila", "Tarkastus")
LF_HEADERS = ["lf_row_kind", "lf_zone", "lf_reason", "lf_checkpoint", "lf_source", "lf_match_key", "lf_value", "lf_currency", "lf_proof"]
COMBINED_HEADERS = [
    *LF_HEADERS,
    "custody:Kauppapäivä",
    "custody:Arvopäivä",
    "custody:Sijoituskohde",
    "custody:Määrä",
    "custody:Kurssi",
    "custody:Palkkio<br/>sis. Alv",
    "custody:Summa",
    "custody:H",
    "custody:Tila",
    "custody:Toimeksiantotyyppi",
    "cash:Pvm",
    "cash:Saaja/Maksaja",
    "cash:Määrä",
    "cash:Saldo",
    "cash:Tila",
    "cash:Tarkastus",
]

DATA_KINDS = {"pair", "standalone", "excluded", "summarized", "deferred"}
TRUTH_KINDS = {"truth_cash", "truth_position", "verification"}
ZONES = {"before", "window", "gap", "after"}
REASONS = {"no_counterpart", "ambiguous", "status", "unknown_type", "invalid", "not_yet_settled", "outside_cash_coverage", "superseded", "reservation"}

SOURCE_RE = re.compile(r"^(custody|cash)(?:#([1-9]\d*))?:([1-9]\d*)$")
PROOF_RE = re.compile(r"^(exact:E1|exact:E2|at_least:E3|discarded:E[1-4]:(recent_trades|window_not_covered|excluded_rows|same_day_movement|conflict))$")
MATCH_KEY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\|-?\d+\.\d{2}\|EUR$")
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CASH_VALUE_RE = re.compile(r"^-?\d+\.\d{2}$")
QUANTITY_VALUE_RE = re.compile(r"^-?\d+(\.\d*[1-9])?$")

TAGS = ["import", "danske_bank"]
DEMERGER_TAGS = ["import", "danske_bank", "demerger"]
CHARGES = "danske_trade_charges_included"
# Project 66, P2c: the info notice that lists the trades whose commission was split out as a linked FEE.
SPLIT_NOTICE = "danske_trade_charges_split"
# The opening of the old suggestion «Määrä × kurssi = … €: … erotus … € on todennäköisesti palkkio» (the plugin's own Finnish
# text, not the UI's). Project 66, P2c (the developer's decision of 21/11): a charges todo exists only for a trade quantity
# × price does not explain (a price in another currency, or 0), so it never suggests that figure nor carries «charges».
GROSS_SUGGESTION = "Määrä × kurssi"
DEMERGER = "demerger"
DEMERGER_OLD = "demerger_old_leg"
DANSKE_REASON_CODES = {CHARGES, DEMERGER, DEMERGER_OLD}
# Parse notices and their severity; every excluded reason has its own "excluded_<reason>" notice, a warning except where
# EXCLUDED_NOTICES says otherwise — but the silent reasons (SILENT_REASONS), which have none.
PARSE_NOTICES = {"deferred_rows": "info", "name_mismatch": "warning", "proof_discarded": "info", "balance_chain_broken": "warning", "deposit_assumed": "info", SPLIT_NOTICE: "info"}
# Lot N74 (Fineco, safe rows): a trade the cash statement settles after its last row is not a fault — it comes with the
# next import — so its notice is a note (info). Every other excluded reason stays a warning, excluded_status included.
EXCLUDED_NOTICES = {"excluded_not_yet_settled": "info"}
# Lot W-B85 (developer, 2026-10-19, a principle for every BRIM plugin): a row the plugin knows to be safe to drop is dropped
# in silence — no notice, at most a backend log line; a row it does not know is dropped with a warning that says so and
# asks the user to open an issue (context["report_issue"] is True: the wizard shows the link under the notice). For
# Danske a «Varaus» cash row (a reservation) is known, and every other row not booked is not. The other reasons wait for a
# decision (D-W85-1): their notices stay as they are, with no report_issue key.
SILENT_REASONS = {"reservation"}
REPORT_ISSUE_NOTICES = {"excluded_status"}
SET_NOTICES = {"gap", "overlap_mismatch", "empty_member", "balance_chain_broken", "mixed_accounts_in_file"}
# The todo context keys the wizard reads (developer guide, "context keys the frontend understands").
CHARGES_CONTEXT = ("row", "cash", "currency", "compare_nominal", "split_hint", "split_suggestions")


# =============================================================================
# HELPERS — the plugin is looked up inside each test, never at import time
# =============================================================================


def _missing(what: str) -> None:
    """Fail the current test (never the collection), naming what phase B still has to add."""
    pytest.fail(f"{what}: not implemented yet (BRIM report sets, phase B)", pytrace=False)


def _danske() -> BRIMProvider:
    """The registered Danske Bank plugin."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    if plugin is None:
        _missing(f"no BRIM plugin is registered as {PLUGIN_CODE} ({PLUGIN_MODULE})")
    return plugin


def _require_contract(name: str) -> None:
    """``BRIMProvider`` itself, not only a subclass, defines ``name``."""
    if not hasattr(BRIMProvider, name):
        _missing(f"BRIMProvider has no {name}")


def _d(text: str) -> date:
    return date.fromisoformat(text)


def _fi_date(day: date) -> str:
    return day.strftime("%d.%m.%Y")


def _from_fi_date(text: str) -> date:
    return datetime.strptime(text, "%d.%m.%Y").date()


def _fi_date_or_none(text: str) -> Optional[date]:
    try:
        return _from_fi_date(text)
    except ValueError:
        return None


def _business_days_after(day: date, count: int) -> date:
    """``day`` plus ``count`` business days: Monday to Friday, no holidays (B0)."""
    while count:
        day += timedelta(days=1)
        if day.weekday() < 5:
            count -= 1
    return day


def _fi_amount(amount: Decimal, *, thousands: str = "") -> str:
    """``amount`` as the bank writes it: comma decimal, no trailing zeros, no plus sign ("-718", "22,5", "-1181,04")."""
    digits = f"{abs(amount):.2f}".rstrip("0").rstrip(".")
    whole, _, cents = digits.partition(".")
    if thousands:
        whole = f"{int(whole):,}".replace(",", thousands)
    return ("-" if amount < 0 else "") + whole + ("," + cents if cents else "")


def _number(text: str) -> Decimal:
    """A number as a combined cell carries it: canonical ("-1181.04") or Finnish text ("−1 181,04", "22,5")."""
    return Decimal(text.replace("\u2212", "-").replace("\u00a0", "").replace(" ", "").replace(",", "."))


def _iso_or_none(text: str) -> Optional[date]:
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _decimal_or_none(text: str) -> Optional[Decimal]:
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


# =============================================================================
# WRITERS — a custody export (XLSX) and a cash statement (CSV), like the bank's
# =============================================================================


def _trade(day: str, name: str, quantity: Any, price: Any, summa: Any, *, value: Optional[str] = None, kind: str = "Rajakurssi", status: str = "Toteutettu", account: str = ACCOUNT, currency: Optional[str] = "EUR") -> List[Any]:
    """One custody trade row; the value date defaults to two business days after the trade date."""
    trade_date = _d(day)
    value_date = _d(value) if value else _business_days_after(trade_date, 2)
    return [trade_date, value_date, name, quantity, price, 0, summa, currency, status, kind, account]


def _tuotto(day: str, name: str, quantity: int, summa: Any, *, account: str = ACCOUNT) -> List[Any]:
    """A ``Tuotto`` (income) row: the shares held, no price, the cash in ``Summa``, value date = trade date."""
    return [_d(day), _d(day), name, quantity, 0, 0, summa, "EUR", "Toteutettu", "Tuotto", account]


def _demerger(day: str, name: str, quantity: int, *, old: bool, summa: Any = None, account: str = ACCOUNT) -> List[Any]:
    """A demerger line, old or new, without cash as the bank writes it (``Summa`` and currency empty)."""
    kind = "Jakautuminen, vanha" if old else "Jakautuminen, uusi"
    return [_d(day), _d(day), name, quantity, 0, 0, summa, None if summa is None else "EUR", "Toteutettu", kind, account]


def _kaamos(day: str, *, account: str = ACCOUNT) -> List[Any]:
    """A one-share purchase (30 + 8 of charges) that pins the first or the last trading day of a segment."""
    return _trade(day, "Kaamos Robotics AB", 1, 30, -38, account=account)


def _xlsx_value(value: Any, date_cells: bool) -> Any:
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day) if date_cells else _fi_date(value)
    return value


def _write_custody(path: Path, rows: Sequence[Any], *, header: Sequence[Optional[str]] = CUSTODY_HEADER, preamble: Sequence[Sequence[Any]] = (), date_cells: bool = False) -> Dict[str, int]:
    """Write a custody export: one sheet, the header, the rows (dates as text unless ``date_cells``).

    Each item of ``rows`` is a row, or ``(key, row)``. Returns ``{key: line}``, lines 1-based.
    """
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    for extra in preamble:
        sheet.append(list(extra))
    sheet.append(list(header))
    lines: Dict[str, int] = {}
    for item in rows:
        key, row = item if isinstance(item, tuple) else (None, item)
        sheet.append([_xlsx_value(value, date_cells) for value in row])
        if key is not None:
            lines[key] = sheet.max_row
    workbook.save(path)
    return lines


@dataclass(frozen=True)
class _Cash:
    """One cash-statement row, given oldest first.

    ``day`` is ISO, or any other text written as is (an invalid date); ``amount`` is a
    dot-decimal string, or any other text written as is (an invalid amount).
    """

    day: str
    label: str
    amount: str
    key: Optional[str] = None
    status: str = "Toteutunut"
    hidden: bool = False  # booked by the bank, so it moves the balance, but missing from the export


def _write_cash(path: Path, rows: Sequence[_Cash], *, opening: str = "0", encoding: str = "latin-1", thousands: str = "") -> Dict[str, int]:
    """Write a cash statement like the bank's: header, rows newest first, the running ``Saldo`` after each row.

    Only posted rows with a valid date and amount move the balance (``Tila`` =
    ``Toteutunut``, label not ``Varaus``); the others carry it unchanged. So the chain
    of the posted rows always holds, unless a ``hidden`` row breaks it.
    Returns ``{key: line}``, lines 1-based, the header being line 1.
    """
    balance = Decimal(opening)
    rendered: List[Tuple[Optional[str], str]] = []
    for row in rows:
        day = _iso_or_none(row.day)
        amount = _decimal_or_none(row.amount)
        if row.status == "Toteutunut" and not row.label.startswith("Varaus") and day is not None and amount is not None:
            balance += amount
        if row.hidden:
            continue
        cells = [_fi_date(day) if day else row.day, row.label, row.amount if amount is None else _fi_amount(amount, thousands=thousands), _fi_amount(balance, thousands=thousands), row.status, "Ei"]
        rendered.append((row.key, ";".join(cells)))
    rendered.reverse()
    text = "\n".join([";".join(CASH_HEADER), *(line for _key, line in rendered)]) + "\n"
    path.write_bytes(text.encode(encoding))
    return {key: number for number, (key, _line) in enumerate(rendered, start=2) if key is not None}


def _write_raw_custody(path: Path, header: Sequence[Any], rows: Sequence[Sequence[Any]]) -> Path:
    """Write header and rows exactly as given (cell types included)."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    for row in [header, *rows]:
        sheet.append(list(row))
    workbook.save(path)
    return path


def _sample_custody(name: str = "danske_bank-custody.xlsx") -> Tuple[List[Any], List[List[Any]]]:
    """Header and rows of a custody sample, cell values as openpyxl reads them."""
    rows = [list(row) for row in openpyxl.load_workbook(SAMPLE_DIR / name).active.iter_rows(values_only=True)]
    return rows[0], rows[1:]


def _fi_text(value: Any, *, thousands: str, minus: str) -> Any:
    """A numeric cell as Finnish text ("−1 181,04", "41,2", "300"); any other cell unchanged."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    text = str(Decimal(str(value)))
    whole, _, fraction = text.lstrip("-").partition(".")
    whole = f"{int(whole):,}".replace(",", thousands)
    return (minus if text.startswith("-") else "") + whole + ("," + fraction if fraction else "")


class _Builder:
    """The member files of one synthetic set, and where every keyed row landed: ``key -> (role, file number, line)``."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.custody: List[Path] = []
        self.cash: List[Path] = []
        self.where: Dict[str, Tuple[str, int, int]] = {}
        self.row_counts: Dict[Tuple[str, int], int] = {}

    def add_custody(self, rows: Sequence[Any], **options: Any) -> Path:
        number = len(self.custody) + 1
        path = self.folder / f"custody-{number}.xlsx"
        for key, line in _write_custody(path, rows, **options).items():
            self.where[key] = ("custody", number, line)
        self.custody.append(path)
        self.row_counts[("custody", number)] = len(rows)
        return path

    def add_cash(self, rows: Sequence[_Cash], **options: Any) -> Path:
        number = len(self.cash) + 1
        path = self.folder / f"cash-{number}.csv"
        for key, line in _write_cash(path, rows, **options).items():
            self.where[key] = ("cash", number, line)
        self.cash.append(path)
        self.row_counts[("cash", number)] = sum(1 for row in rows if not row.hidden)
        return path

    def members(self) -> Dict[str, List[Path]]:
        return {"custody": list(self.custody), "cash": list(self.cash)}

    def row(self, records: List[Dict[str, str]], key: str) -> Dict[str, str]:
        role, number, line = self.where[key]
        return _data_row(records, role, number, line)


# =============================================================================
# COMBINED TABLE — reading it back
# =============================================================================


def _records(table: BRIMCombinedTable) -> List[Dict[str, str]]:
    return [dict(zip(table.headers, row, strict=True)) for row in table.rows]


def _sources(record: Dict[str, str]) -> Set[Tuple[str, int, int]]:
    """``lf_source`` as ``{(role, file number, line)}``; a role with a single file is file 1."""
    found = set()
    for token in record["lf_source"].split(" + "):
        match = SOURCE_RE.match(token)
        assert match, f"lf_source {record['lf_source']!r} is not 'role[#n]:line' or two of them joined by ' + '"
        found.add((match.group(1), int(match.group(2) or 1), int(match.group(3))))
    return found


def _data_row(records: List[Dict[str, str]], role: str, number: int, line: int) -> Dict[str, str]:
    """The one data row (not a truth row) built from ``line`` of file ``number`` of ``role``."""
    found = [record for record in records if record["lf_row_kind"] in DATA_KINDS and (role, number, line) in _sources(record)]
    assert len(found) == 1, f"{role} file {number} line {line}: {len(found)} data rows in the combined file {[record['lf_source'] for record in found]}"
    return found[0]


def _truth(records: List[Dict[str, str]], kind: str, as_of: Optional[str] = None) -> List[Dict[str, str]]:
    return [record for record in records if record["lf_row_kind"] == kind and (as_of is None or record["lf_checkpoint"] == as_of)]


def _positions_by_title(records: List[Dict[str, str]], title: str) -> List[Dict[str, str]]:
    return [record for record in _truth(records, "truth_position") if record["custody:Sijoituskohde"] == title]


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8-sig").splitlines())


def _cash_type(label: str) -> str:
    """The transaction type of a standalone cash row, by label family (B0, S1)."""
    if label.startswith("Nosto osakesäästötililtä"):
        return "WITHDRAWAL"
    if label.startswith("Vero osakesäästötililtä"):
        return "TAX"
    if label.startswith("Palvelumaksu"):
        return "FEE"
    if label.startswith("Korko"):
        return "INTEREST"
    return "DEPOSIT"


def _owed_split(record: Dict[str, str]) -> Optional[Tuple[Decimal, Decimal]]:
    """Project 66, P2c: ``(trade cash, charges)`` of a paired purchase or sale whose sum quantity × Kurssi explains, else
    None. The gross is |quantity| × Kurssi to the cent; it explains the sum paid when it is not zero and the difference
    (paid − gross for a purchase, gross − received for a sale) is between 0 and max(15, 1 % of the gross). The trade is
    then booked at the gross (negative for a purchase), and a difference above zero is its FEE."""
    if record["lf_row_kind"] != "pair" or record["custody:Toimeksiantotyyppi"] == "Tuotto":
        return None
    quantity, paid = _number(record["custody:Määrä"]), _number(record["cash:Määrä"])
    gross = abs(quantity * _number(record["custody:Kurssi"])).quantize(Decimal("0.01"))
    if gross <= 0:
        return None
    charges = abs(paid) - gross if quantity > 0 else gross - abs(paid)
    if not Decimal(0) <= charges <= max(Decimal(15), gross / 100):
        return None
    return (-gross if quantity > 0 else gross), charges


def _owed_rows(records: List[Dict[str, str]]) -> List[Tuple[Tuple[Any, ...], List[Tuple[str, str, str]]]]:
    """What the parse owes for each pair and standalone row, in file order: the transaction
    ``(type, date, quantity, cash, title, description, tags)`` and its todos ``(reason, field, severity)``.

    Lot B-52: a pair (a trade, or a ``Tuotto``) and a demerger line are dated on the custody ``Kauppapäivä`` (the trade
    date). A cash-only row keeps its ``Pvm``, the only date it has.

    Project 66, P2c (``_owed_split``): a trade whose sum quantity × Kurssi explains is owed at the gross, followed by its
    FEE (the difference, negative, same date and title, ``Palkkio: `` + the trade's description) when the difference is
    not zero; it has no todo. A trade whose sum is not explained keeps the cash of its pair and its charges todo."""
    owed: List[Tuple[Tuple[Any, ...], List[Tuple[str, str, str]]]] = []
    for record in records:
        kind = record["lf_row_kind"]
        if kind == "pair":
            order = record["custody:Toimeksiantotyyppi"]
            quantity = _number(record["custody:Määrä"])
            tx_type = "DIVIDEND" if order == "Tuotto" else ("BUY" if quantity > 0 else "SELL")
            day, title, description = _from_fi_date(record["custody:Kauppapäivä"]), record["custody:Sijoituskohde"], f"{record['cash:Saaja/Maksaja']} ({order})"
            split = _owed_split(record)
            cash = _number(record["cash:Määrä"]) if split is None else split[0]
            todos = [(CHARGES, "cash", "warning")] if tx_type != "DIVIDEND" and split is None else []
            owed.append(((tx_type, day, Decimal(0) if tx_type == "DIVIDEND" else quantity, cash, title, description, TAGS), todos))
            if split is not None and split[1] > 0:
                owed.append((("FEE", day, Decimal(0), -split[1], title, f"Palkkio: {description}", TAGS), []))
        elif kind == "standalone" and record["cash:Pvm"]:
            label = record["cash:Saaja/Maksaja"]
            owed.append(((_cash_type(label), _from_fi_date(record["cash:Pvm"]), Decimal(0), _number(record["cash:Määrä"]), None, label, TAGS), []))
        elif kind == "standalone":
            title = record["custody:Sijoituskohde"]
            quantity = _number(record["custody:Määrä"])
            todos = [(DEMERGER, "cost_basis_override", "blocker")] if quantity > 0 else [(DEMERGER_OLD, "quantity", "warning")]
            owed.append((("ADJUSTMENT", _from_fi_date(record["custody:Kauppapäivä"]), quantity, None, title, f"{record['custody:Toimeksiantotyyppi']}: {title}", DEMERGER_TAGS), todos))
    return owed


def _owed_transactions(records: List[Dict[str, str]]) -> List[Tuple[Any, ...]]:
    """The transactions of ``_owed_rows``, in file order."""
    return [transaction for transaction, _todos in _owed_rows(records)]


def _assert_each_source_row_once(row_counts: Dict[Tuple[str, int], int], records: List[Dict[str, str]]) -> None:
    """I4, no silent loss: every row of every member lands in exactly one data row of the combined file."""
    seen = Counter(source for record in records if record["lf_row_kind"] in DATA_KINDS for source in _sources(record))
    expected = {(role, number, line) for (role, number), count in row_counts.items() for line in range(2, count + 2)}
    assert sorted(set(seen) - expected) == [], "data rows point at lines the members do not have"
    assert sorted(expected - set(seen)) == [], "member rows missing from the combined file"
    assert sorted(source for source, times in seen.items() if times > 1) == [], "member rows copied into several data rows"


def _sort_key(record: Dict[str, str]) -> Tuple[Any, ...]:
    """B0 order: value date; truth rows at their date, after that day's data rows; then custody before cash, file, line."""
    if record["lf_row_kind"] in TRUTH_KINDS:
        return (_d(record["lf_checkpoint"]), 1)
    day = record["cash:Pvm"] or record["custody:Arvopäivä"]
    role, number, line = min(_sources(record), key=lambda source: (source[0] != "custody", source[1], source[2]))
    return (_from_fi_date(day), 0, 0 if role == "custody" else 1, number, line)


def _expected_tx(tx_type: str, day: str, quantity: str, cash: Optional[str], title: Optional[str], description: str) -> Tuple[Any, ...]:
    """A transaction as ``_transactions`` shows it, from literal strings."""
    return (tx_type, _d(day), Decimal(quantity), None if cash is None else Decimal(cash), title, description, DEMERGER_TAGS if tx_type == "ADJUSTMENT" else TAGS)


# =============================================================================
# PARSE OUTPUT — reading it back
# =============================================================================


def _names(output: BRIMParseOutput) -> Dict[int, Optional[str]]:
    return {asset_id: info.extracted_name for asset_id, info in output.extracted_assets.items()}


def _asset(output: BRIMParseOutput, title: str) -> int:
    ids = [asset_id for asset_id, name in _names(output).items() if name == title]
    assert len(ids) == 1, f"{title!r}: {len(ids)} extracted assets carry this name, one expected"
    return ids[0]


def _transactions(output: BRIMParseOutput) -> List[Tuple[Any, ...]]:
    """``(type, date, quantity, cash, title, description, tags)`` of every transaction, in order."""
    names = _names(output)
    return [(tx.type.value, tx.date, tx.quantity, None if tx.cash is None else tx.cash.amount, None if tx.asset_id is None else names.get(tx.asset_id), tx.description, list(tx.tags or [])) for tx in output.transactions]


def _money(items: Sequence[Any]) -> Dict[str, Decimal]:
    return {item.currency: item.amount for item in items}


def _nonzero(money: Dict[str, Decimal]) -> Dict[str, Decimal]:
    return {code: amount for code, amount in money.items() if amount != 0}


def _checkpoint(output: BRIMParseOutput, as_of: str) -> Any:
    found = [checkpoint for checkpoint in output.checkpoints if checkpoint.as_of == _d(as_of)]
    assert len(found) == 1, f"one checkpoint expected at {as_of}, got {[item.as_of.isoformat() for item in output.checkpoints]}"
    return found[0]


def _positions(output: BRIMParseOutput, checkpoint: Any) -> Dict[str, Tuple[Decimal, str]]:
    names = _names(output)
    return {names.get(position.asset_id): (position.quantity, position.exactness) for position in checkpoint.positions}


def _codes(notices: Sequence[Any]) -> List[str]:
    return [notice.code for notice in notices]


def _essence(output: BRIMParseOutput) -> Dict[str, Any]:
    """What a parse says, without the verbatim text it quotes (evidence, messages, suggestions).

    Two readings of the same data (another encoding, another cell type) must agree on it.
    """
    names = _names(output)
    pinned_context = ("row", "cash", "currency", "compare_nominal", "split_hint", "charges")
    return {
        "transactions": _transactions(output),
        "todos": [(todo.tx_index, todo.field, todo.severity, todo.reason_code, {key: (todo.context or {}).get(key) for key in pinned_context}) for todo in output.field_todos],
        "notices": sorted((notice.code, notice.severity) for notice in output.warnings),
        "checkpoints": [
            (
                checkpoint.as_of,
                checkpoint.kind,
                _money(checkpoint.cash),
                sorted((names.get(position.asset_id), position.quantity, position.exactness) for position in checkpoint.positions),
                checkpoint.absorbed.count,
                _nonzero(_money(checkpoint.absorbed.cash)),
                sorted((row.as_of, row.currency, row.amount, row.label) for row in checkpoint.absorbed.rows),
                _money(checkpoint.absorbed.opening_cash),
            )
            for checkpoint in output.checkpoints
        ],
        "verifications": [(verification.as_of, _money(verification.cash)) for verification in output.verifications],
        "assets": sorted(name or "" for name in names.values()),
    }


# =============================================================================
# SAMPLE SETS AND SCENARIOS — combined once, parsed once
# =============================================================================


def _members(sample_set: Dict[str, List[str]]) -> Dict[str, List[Path]]:
    return {role: [SAMPLE_DIR / name for name in names] for role, names in sample_set.items()}


_SAMPLE_TABLES: Dict[str, BRIMCombinedTable] = {}
_SAMPLE_PARSES: Dict[str, Tuple[Path, BRIMParseOutput]] = {}
_BUILDERS: Dict[str, _Builder] = {}
_SCENARIO_TABLES: Dict[str, BRIMCombinedTable] = {}
_SCENARIO_PARSES: Dict[str, Tuple[Path, BRIMParseOutput]] = {}
SCENARIOS: Dict[str, Callable[[_Builder], None]] = {}


def _sample_table(name: str) -> BRIMCombinedTable:
    """The combined table of sample set ``name`` ("main" or "gap"), combined once per session."""
    plugin = _danske()
    if name not in _SAMPLE_TABLES:
        _SAMPLE_TABLES[name] = plugin.combine(_members(SAMPLE_SETS[name]))
    return _SAMPLE_TABLES[name].model_copy(deep=True)


def _sample_parse(name: str, tmp_path_factory: pytest.TempPathFactory) -> Tuple[BRIMCombinedTable, Path, BRIMParseOutput]:
    """The combined table of a sample set, its combined file (written by the core) and the parse of that file."""
    table = _sample_table(name)
    if name not in _SAMPLE_PARSES:
        path = tmp_path_factory.mktemp(f"danske-{name}") / f"danske_bank-{name}-combined.csv"
        write_combined_csv(path, table)
        _SAMPLE_PARSES[name] = (path, _danske().parse(path, broker_id=BROKER_ID))
    path, output = _SAMPLE_PARSES[name]
    return table, path, output.model_copy(deep=True)


def _scenario_files(name: str, tmp_path_factory: pytest.TempPathFactory) -> _Builder:
    """The member files of a synthetic scenario, written once per session."""
    if name not in _BUILDERS:
        builder = _Builder(tmp_path_factory.mktemp(f"danske-{name}"))
        SCENARIOS[name](builder)
        _BUILDERS[name] = builder
    return _BUILDERS[name]


def _scenario(name: str, tmp_path_factory: pytest.TempPathFactory) -> Tuple[_Builder, BRIMCombinedTable]:
    """The members and the combined table of a synthetic scenario, combined once per session."""
    plugin = _danske()
    builder = _scenario_files(name, tmp_path_factory)
    if name not in _SCENARIO_TABLES:
        _SCENARIO_TABLES[name] = plugin.combine(builder.members())
    return builder, _SCENARIO_TABLES[name].model_copy(deep=True)


def _scenario_parse(name: str, tmp_path_factory: pytest.TempPathFactory) -> Tuple[_Builder, BRIMCombinedTable, Path, BRIMParseOutput]:
    builder, table = _scenario(name, tmp_path_factory)
    if name not in _SCENARIO_PARSES:
        path = builder.folder / "combined.csv"
        write_combined_csv(path, table)
        _SCENARIO_PARSES[name] = (path, _danske().parse(path, broker_id=BROKER_ID))
    path, output = _SCENARIO_PARSES[name]
    return builder, table, path, output.model_copy(deep=True)


def _combined(source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> Tuple[BRIMCombinedTable, Path, BRIMParseOutput]:
    """``("sample", "main")`` or ``("scenario", "zones")``: the combined table, its file and its parse."""
    if source == "sample":
        return _sample_parse(name, tmp_path_factory)
    _builder, table, path, output = _scenario_parse(name, tmp_path_factory)
    return table, path, output


def scenario(name: str) -> Callable[[Callable[[_Builder], None]], Callable[[_Builder], None]]:
    """Register a scenario builder under ``name``."""

    def register(function: Callable[[_Builder], None]) -> Callable[[_Builder], None]:
        SCENARIOS[name] = function
        return function

    return register


# Every scenario starts from a cash balance of 1000 and a deposit on 2021-02-01, and trades
# from 2021-03-01 on: so C1 = 2021-02-28 (a Sunday), the border runs 03-01…03-05, and a
# segment ending 03-31 has its window up to 04-07 (five business days, no holidays).
OPENING = "1000"
DEPOSIT = _Cash("2021-02-01", "Matti Meikäläinen", "500", "deposit")


@scenario("zones")
def _zones(builder: _Builder) -> None:
    """Two segments and a proven gap; the cash statement runs from before the first window to after the last.

    Segment 1: trades 03-01…03-31, C1 = 02-28, border 03-01…03-05, window to 04-07.
    Segment 2: trades 06-01…06-30, C2 = 05-31, border 06-01…06-07, window to 07-07.
    """
    builder.add_custody(
        [
            ("a1", _trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208)),  # value 03-03
            ("a2", _trade("2021-03-10", "Lumi Holding Oyj", 5, 10, -58)),  # value 03-12, no cash row
            ("a3", _trade("2021-03-31", "Aurora Metsä Oyj", -4, 25, 92, kind="Päivän kurssi")),  # value 04-02
        ]
    )
    builder.add_custody(
        [
            ("b1", _trade("2021-06-01", "Kaamos Robotics AB", 3, 30, -98)),  # value 06-03
            ("b2", _trade("2021-06-30", "Kaamos Robotics AB", 1, 30, -38)),  # value 07-02
        ]
    )
    builder.add_cash(
        [
            _Cash("2021-01-04", "Matti Meikäläinen", "5000", "c1"),
            _Cash("2021-01-29", "Palvelumaksut 01/2021", "-3.5", "c2"),
            _Cash("2021-02-10", "Osto Revontuli Oyj", "-200", "c3"),
            _Cash("2021-02-15", "Siirto säästötilille", "-50", "c4"),
            _Cash("2021-03-02", "Osto Pohjola Tekniikka O", "-120", "c5"),
            _Cash("2021-03-03", "Osto Aurora Metsä Oyj", "-208", "c6"),
            _Cash("2021-03-17", "Osto Saimaa Energia Oyj", "-300", "c7"),
            _Cash("2021-03-31", "Palvelumaksut 03/2021", "-3.5", "c8"),
            _Cash("2021-04-02", "Myynti Aurora Metsä Oyj", "92", "c9"),
            _Cash("2021-04-06", "Myynti Lumi Palvelut Oyj", "250", "c10"),
            _Cash("2021-05-03", "Matti Meikäläinen", "500", "c11"),
            _Cash("2021-05-10", "Osto Tunturi Pankki Oyj", "-400", "c12"),
            _Cash("2021-06-02", "Osto Saimaa Energia Oyj", "-150", "c13"),
            _Cash("2021-06-03", "Osto Kaamos Robotics AB", "-98", "c14"),
            _Cash("2021-06-30", "Palvelumaksut 06/2021", "-3.5", "c15"),
            _Cash("2021-07-02", "Osto Kaamos Robotics AB", "-38", "c16"),
            _Cash("2021-07-06", "Osto Tunturi Pankki Oyj", "-90", "c17"),
            _Cash("2021-07-15", "Myynti Revontuli Oyj", "300", "c18"),
            _Cash("2021-07-30", "Palvelumaksut 07/2021", "-3.5", "c19"),
        ]
    )


@scenario("merged")
def _merged(builder: _Builder) -> None:
    """Two custody exports with a space between them that no unpaired trade row proves: one segment, 03-01…06-30."""
    builder.add_custody([("a1", _trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208)), ("a3", _trade("2021-03-31", "Aurora Metsä Oyj", -4, 25, 92, kind="Päivän kurssi"))])
    builder.add_custody([("b1", _trade("2021-06-01", "Kaamos Robotics AB", 3, 30, -98)), ("b2", _trade("2021-06-30", "Kaamos Robotics AB", 1, 30, -38))])
    builder.add_cash(
        [
            _Cash("2021-01-04", "Matti Meikäläinen", "5000"),
            _Cash("2021-03-03", "Osto Aurora Metsä Oyj", "-208"),
            _Cash("2021-04-02", "Myynti Aurora Metsä Oyj", "92"),
            _Cash("2021-05-03", "Matti Meikäläinen", "500", "deposit"),
            _Cash("2021-05-31", "Palvelumaksut 05/2021", "-3.5", "fee"),
            _Cash("2021-06-03", "Osto Kaamos Robotics AB", "-98"),
            _Cash("2021-07-02", "Osto Kaamos Robotics AB", "-38"),
        ]
    )


@scenario("late")
def _late(builder: _Builder) -> None:
    """A13: the cash statement starts on 03-10, after the custody export (03-01). C1 stays on the eve of the custody
    export, 02-28, and its cash is the statement's first balance (the developer, 20/10/2026).

    The statement opens with the income of a ``Tuotto``: the 30 days before it are all
    before the statement, so its proof cannot be checked (E1 ``window_not_covered``).
    """
    builder.add_custody(
        [
            ("k1", _trade("2021-03-01", "Kaamos Robotics AB", 2, 30, -68)),  # value 03-03, before the statement
            ("t", _tuotto("2021-03-10", "Aurora Metsä Oyj", 100, 15)),
            ("k2", _kaamos("2021-03-31")),  # value 04-02
        ]
    )
    builder.add_cash([_Cash("2021-03-10", "Aurora Metsä 1234567890", "15", "e1"), _Cash("2021-04-02", "Osto Kaamos Robotics AB", "-38", "e2")], opening=OPENING)


@scenario("early_end")
def _early_end(builder: _Builder) -> None:
    """The cash statement ends on 03-25, before the last custody trade (03-31, settled 04-02)."""
    builder.add_custody([("a", _trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208)), ("k", _kaamos("2021-03-31"))])
    builder.add_cash([DEPOSIT, _Cash("2021-03-03", "Osto Aurora Metsä Oyj", "-208", "f2"), _Cash("2021-03-25", "Palvelumaksut 03/2021", "-3.5", "f3")], opening=OPENING)


@scenario("hole")
def _hole(builder: _Builder) -> None:
    """Two cash statements that leave 03-06…03-21 uncovered; a trade settled there has no cash to meet."""
    builder.add_custody(
        [
            ("a", _trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208)),  # value 03-03
            ("k", _trade("2021-03-10", "Kaamos Robotics AB", 2, 30, -68)),  # value 03-12, in the hole
            ("l", _trade("2021-03-31", "Lumi Holding Oyj", 1, 5, -13)),  # value 04-02
        ]
    )
    builder.add_cash([DEPOSIT, _Cash("2021-03-03", "Osto Aurora Metsä Oyj", "-208", "g2"), _Cash("2021-03-05", "Palvelumaksut 03/2021", "-3.5", "g3")], opening=OPENING)
    builder.add_cash([_Cash("2021-03-22", "Matti Meikäläinen", "100", "h1"), _Cash("2021-04-02", "Osto Lumi Holding Oyj", "-13", "h2"), _Cash("2021-04-09", "Palvelumaksut 04/2021", "-3.5", "h3")], opening="1288.50")


@scenario("chain")
def _chain(builder: _Builder) -> None:
    """A row booked on 03-10 is missing from the statement: the running balance breaks on 03-15."""
    builder.add_custody([("a", _trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208)), ("k", _kaamos("2021-03-31"))])
    builder.add_cash(
        [
            DEPOSIT,
            _Cash("2021-03-03", "Osto Aurora Metsä Oyj", "-208"),
            _Cash("2021-03-10", "Palvelumaksut 02/2021", "-40", hidden=True),
            _Cash("2021-03-15", "Palvelumaksut 03/2021", "-3.5", "i3"),
            _Cash("2021-04-02", "Osto Kaamos Robotics AB", "-38"),
        ],
        opening=OPENING,
    )


def _proof_cash(*middle: _Cash, last: str = "2021-05-04") -> List[_Cash]:
    """The cash statement of the proof scenarios: the deposit, the first and the last Kaamos purchase around ``middle``."""
    return [DEPOSIT, _Cash("2021-03-03", "Osto Kaamos Robotics AB", "-38"), *middle, _Cash(last, "Osto Kaamos Robotics AB", "-38")]


@scenario("recent_trade")
def _recent_trade(builder: _Builder) -> None:
    """E1: a purchase of the same title 15 days before the ``Tuotto`` (04-20) makes its quantity no proof."""
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("a", _trade("2021-04-05", "Aurora Metsä Oyj", 10, 20, -208)), ("t", _tuotto("2021-04-20", "Aurora Metsä Oyj", 60, 9)), ("k2", _kaamos("2021-04-30"))])
    builder.add_cash(_proof_cash(_Cash("2021-04-07", "Osto Aurora Metsä Oyj", "-208"), _Cash("2021-04-20", "Aurora Metsä 1234567890", "9")), opening=OPENING)


@scenario("recent_cash")
def _recent_cash(builder: _Builder) -> None:
    """E1: an unpaired ``Osto`` of the same title 13 days before the ``Tuotto`` makes its quantity no proof."""
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("t", _tuotto("2021-04-20", "Aurora Metsä Oyj", 60, 9)), ("k2", _kaamos("2021-04-30"))])
    builder.add_cash(_proof_cash(_Cash("2021-04-07", "Osto Aurora Metsä Oyj", "-208", "osto"), _Cash("2021-04-20", "Aurora Metsä 1234567890", "9")), opening=OPENING)


@scenario("same_day")
def _same_day(builder: _Builder) -> None:
    """E2: a sale of the old title on the day of the demerger discards the exact proof; E3 still proves 110."""
    builder.add_custody(
        [
            ("k1", _kaamos("2021-03-01")),
            ("s", _trade("2021-04-01", "Lumi Holding Oyj", -10, 10, 92, kind="Päivän kurssi", value="2021-04-06")),
            ("v", _demerger("2021-04-01", "Lumi Holding Oyj", -100, old=True)),
            ("u", _demerger("2021-04-01", "Lumi Uusi Oyj", 100, old=False)),
            ("k2", _kaamos("2021-04-30")),
        ]
    )
    builder.add_cash(_proof_cash(_Cash("2021-04-06", "Myynti Lumi Holding Oyj", "92")), opening=OPENING)


@scenario("excluded_proof")
def _excluded_proof(builder: _Builder) -> None:
    """E4: a cancelled purchase of the title (03-05) between C1 and the ``Tuotto`` (04-20) discards the proof."""
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("x", _trade("2021-03-05", "Aurora Metsä Oyj", 10, 20, -208, status="Peruttu")), ("t", _tuotto("2021-04-20", "Aurora Metsä Oyj", 60, 9)), ("k2", _kaamos("2021-04-30"))])
    builder.add_cash(_proof_cash(_Cash("2021-04-20", "Aurora Metsä 1234567890", "9")), opening=OPENING)


@scenario("superseded_proof")
def _superseded_proof(builder: _Builder) -> None:
    """E4 exception: a row superseded by rule M does not discard the proof. The newer export wins 03-10."""
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("x", _trade("2021-03-10", "Aurora Metsä Oyj", 5, 20, -108))])
    builder.add_custody([("y", _trade("2021-03-10", "Saimaa Energia Oyj", 2, 10, -28)), ("t", _tuotto("2021-04-20", "Aurora Metsä Oyj", 60, 9)), ("k2", _kaamos("2021-04-30"))])
    builder.add_cash(_proof_cash(_Cash("2021-03-12", "Osto Saimaa Energia Oyj", "-28"), _Cash("2021-04-20", "Aurora Metsä 1234567890", "9")), opening=OPENING)


@scenario("conflict")
def _conflict(builder: _Builder) -> None:
    """Two exact proofs that disagree: the ``Tuotto`` says 150, the demerger 120, nothing moved in between."""
    builder.add_custody(
        [
            ("k1", _kaamos("2021-03-01")),
            ("t", _tuotto("2021-04-15", "Lumi Holding Oyj", 150, 10)),
            ("v", _demerger("2021-06-01", "Lumi Holding Oyj", -120, old=True)),
            ("u", _demerger("2021-06-01", "Lumi Uusi Oyj", 120, old=False)),
            ("k2", _kaamos("2021-06-30")),  # value 07-02
        ]
    )
    builder.add_cash(_proof_cash(_Cash("2021-04-15", "Lumi Holding 1234567890", "10"), last="2021-07-02"), opening=OPENING)


@scenario("name_mismatch")
def _name_mismatch(builder: _Builder) -> None:
    """S3: a unique key whose cash label names another title."""
    builder.add_custody([("a", _trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208)), ("k2", _kaamos("2021-03-31"))])
    builder.add_cash([DEPOSIT, _Cash("2021-03-03", "Osto Revontuli Oyj", "-208", "c"), _Cash("2021-04-02", "Osto Kaamos Robotics AB", "-38")], opening=OPENING)


@scenario("direction")
def _direction(builder: _Builder) -> None:
    """S2: same date, same amount, but an income against a sale: the direction is part of the key."""
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("t", _tuotto("2021-03-10", "Aurora Metsä Oyj", 100, 50)), ("k2", _kaamos("2021-03-31"))])
    builder.add_cash(_proof_cash(_Cash("2021-03-10", "Myynti Aurora Metsä Oyj", "50", "c"), last="2021-04-02"), opening=OPENING)


@scenario("by_name")
def _by_name(builder: _Builder) -> None:
    """S4: two titles with the same key; the names tell them apart. The file order alone would cross them."""
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("a", _trade("2021-03-10", "Aurora Metsä Oyj", 5, 20, -108)), ("s", _trade("2021-03-10", "Saimaa Energia Oyj", 8, 12.5, -108)), ("k2", _kaamos("2021-03-31"))])
    builder.add_cash(_proof_cash(_Cash("2021-03-12", "Osto Aurora Metsä Oyj", "-108", "ca"), _Cash("2021-03-12", "Osto Saimaa Energia Oyj", "-108", "cs"), last="2021-04-02"), opening=OPENING)


@scenario("ambiguous")
def _ambiguous(builder: _Builder) -> None:
    """S4: one truncated cash label compatible with two titles of the same key, and different trades: never guess."""
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("p1", _trade("2021-03-10", "Pohjola Tekniikka Oyj A", 5, 20, -108)), ("p2", _trade("2021-03-10", "Pohjola Tekniikka Oyj B", 8, 12.5, -108)), ("k2", _kaamos("2021-03-31"))])
    builder.add_cash(_proof_cash(_Cash("2021-03-12", "Osto Pohjola Tekniikka O", "-108", "cp"), last="2021-04-02"), opening=OPENING)


def _crowd(count: int) -> Callable[[_Builder], None]:
    def build(builder: _Builder) -> None:
        fills = [(f"s{index}", _trade("2021-03-10", "Saimaa Energia Oyj", 1, 5, -13)) for index in range(count)]
        builder.add_custody([("k1", _kaamos("2021-03-01")), *fills, ("k2", _kaamos("2021-03-31"))])
        builder.add_cash(_proof_cash(*(_Cash("2021-03-12", "Osto Saimaa Energia Oyj", "-13", f"c{index}") for index in range(count)), last="2021-04-02"), opening=OPENING)

    return build


SCENARIOS["crowd_8"] = _crowd(8)
SCENARIOS["crowd_9"] = _crowd(9)


@scenario("overlap_same")
def _overlap_same(builder: _Builder) -> None:
    """Rule M: two custody exports agree on 03-10, where each holds the same two identical partial fills."""
    fill = _trade("2021-03-10", "Saimaa Energia Oyj", 25, 12.4, -318)
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("a1", list(fill)), ("a2", list(fill))])
    builder.add_custody([("b1", list(fill)), ("b2", list(fill)), ("k2", _kaamos("2021-03-31"))])
    builder.add_cash(_proof_cash(_Cash("2021-03-12", "Osto Saimaa Energia Oyj", "-318", "c1"), _Cash("2021-03-12", "Osto Saimaa Energia Oyj", "-318", "c2"), last="2021-04-02"), opening=OPENING)


def _overlap_diff(newer_first: bool) -> Callable[[_Builder], None]:
    """Rule M: on 03-10 the older export (ends 03-10) says one purchase, the newer one (ends 03-31) two."""

    def build(builder: _Builder) -> None:
        older = [("k1", _kaamos("2021-03-01")), ("x", _trade("2021-03-10", "Aurora Metsä Oyj", 5, 20, -108))]
        newer = [("x2", _trade("2021-03-10", "Aurora Metsä Oyj", 5, 20, -108)), ("y", _trade("2021-03-10", "Saimaa Energia Oyj", 2, 10, -28)), ("k2", _kaamos("2021-03-31"))]
        for rows in [newer, older] if newer_first else [older, newer]:
            builder.add_custody(rows)
        builder.add_cash(_proof_cash(_Cash("2021-03-12", "Osto Aurora Metsä Oyj", "-108", "ca"), _Cash("2021-03-12", "Osto Saimaa Energia Oyj", "-28", "cs"), last="2021-04-02"), opening=OPENING)

    return build


SCENARIOS["overlap_diff"] = _overlap_diff(newer_first=False)
SCENARIOS["overlap_diff_newer_first"] = _overlap_diff(newer_first=True)


@scenario("overlap_cash")
def _overlap_cash(builder: _Builder) -> None:
    """Rule M on the cash role: two statements agree on 03-03…03-12."""
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("a", _trade("2021-03-10", "Aurora Metsä Oyj", 5, 20, -108)), ("k2", _kaamos("2021-03-31"))])
    builder.add_cash([DEPOSIT, _Cash("2021-03-03", "Osto Kaamos Robotics AB", "-38"), _Cash("2021-03-12", "Osto Aurora Metsä Oyj", "-108")], opening=OPENING)
    builder.add_cash([_Cash("2021-03-03", "Osto Kaamos Robotics AB", "-38"), _Cash("2021-03-12", "Osto Aurora Metsä Oyj", "-108"), _Cash("2021-04-02", "Osto Kaamos Robotics AB", "-38")], opening="1500")


@scenario("mixed_accounts")
def _mixed_accounts(builder: _Builder) -> None:
    """One custody export with two deposit accounts."""
    builder.add_custody([("k1", _kaamos("2021-03-01", account="FI-ACCOUNT-0001")), ("k2", _kaamos("2021-03-31", account="FI-ACCOUNT-0002"))])
    builder.add_cash(_proof_cash(last="2021-04-02"), opening=OPENING)


@scenario("empty_member")
def _empty_member(builder: _Builder) -> None:
    """A second custody export with its header only."""
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("k2", _kaamos("2021-03-31"))])
    builder.add_custody([])
    builder.add_cash(_proof_cash(last="2021-04-02"), opening=OPENING)


@scenario("classes")
def _classes(builder: _Builder) -> None:
    """One row per line of the S1 classes table (B0), in the window of one segment (03-01…03-31).

    Lot W-B85: two «Varaus» cash rows, one ``Toteutunut`` and one ``Odottaa`` — the label makes a reservation whatever
    the ``Tila``. The rows not booked that are no reservation are the custody ``Hylätty`` row and the cash ``Odottaa`` one.
    """
    no_date = _trade("2021-03-22", "Aurora Metsä Oyj", 1, 5, -13, value="2021-03-24")
    no_date[0] = ""
    builder.add_custody(
        [
            ("k0", _kaamos("2021-03-01")),
            ("status", _trade("2021-03-08", "Aurora Metsä Oyj", 5, 20, -108, status="Hylätty")),
            ("buy_positive_summa", _trade("2021-03-09", "Aurora Metsä Oyj", 5, 20, 108)),
            ("sell_negative_summa", _trade("2021-03-09", "Aurora Metsä Oyj", -5, 20, -92, kind="Päivän kurssi")),
            ("pika_buy", _trade("2021-03-11", "Lumi Holding Oyj", 4, 10, -48, kind="Pikakauppa", value="2021-03-15")),
            ("paiva_sell", _trade("2021-03-12", "Kaamos Robotics AB", -1, 33, 25, kind="Päivän kurssi", value="2021-03-16")),
            ("tuotto", _tuotto("2021-03-17", "Aurora Metsä Oyj", 10, 4.5)),
            ("vanha", _demerger("2021-03-18", "Lumi Holding Oyj", -4, old=True)),
            ("uusi", _demerger("2021-03-18", "Lumi Uusi Oyj", 4, old=False)),
            ("uusi_with_summa", _demerger("2021-03-18", "Lumi Toinen Oyj", 4, old=False, summa=-10)),
            ("unknown_type", _trade("2021-03-19", "Aurora Metsä Oyj", 5, 0, None, kind="Siirto", currency=None)),
            ("no_name", _trade("2021-03-22", "", 1, 5, -13, value="2021-03-24")),
            ("no_quantity", _trade("2021-03-22", "Aurora Metsä Oyj", None, 5, -13, value="2021-03-24")),
            ("no_trade_date", no_date),
            ("value_before_trade", _trade("2021-03-23", "Aurora Metsä Oyj", 1, 5, -13, value="2021-03-22")),
            ("k_end", _kaamos("2021-03-31")),
        ]
    )
    builder.add_cash(
        [
            _Cash("2021-02-01", "Matti Meikäläinen", "2000", "deposit_before"),
            _Cash("2021-03-03", "Osto Kaamos Robotics AB", "-38", "p_k0"),
            _Cash("2021-03-04", "Varaus", "-25", "varaus_label"),
            _Cash("2021-03-05", "Osto Revontuli Oyj", "-60", "pending", status="Odottaa"),
            _Cash("2021-03-08", "Nosto osakesäästötililtä", "-100", "nosto"),
            _Cash("2021-03-08", "Vero osakesäästötililtä", "-12.3", "vero"),
            _Cash("2021-03-09", "Palvelumaksut 03/2021", "-3.5", "fee"),
            _Cash("2021-03-10", "Korko 03/2021", "0.42", "korko"),
            _Cash("2021-03-11", "Siirto omalta tililtä", "150", "other_positive"),
            _Cash("2021-03-12", "Siirto ulkomaille", "-40", "other_negative"),
            _Cash("2021-03-12", "Osto Saimaa Energia Oyj", "30", "osto_positive"),
            _Cash("2021-03-15", "Osto Lumi Holding Oyj", "-48", "p_pika"),
            _Cash("2021-03-15", "Myynti Tunturi Pankki Oyj", "-20", "myynti_negative"),
            _Cash("2021-03-16", "Myynti Kaamos Robotics AB", "25", "p_paiva"),
            _Cash("2021-03-16", "Nosto osakesäästötililtä", "10", "nosto_positive"),
            _Cash("2021-03-16", "Palvelumaksut 02/2021", "3.5", "fee_positive"),
            _Cash("2021-03-16", "Korko 02/2021", "-0.1", "korko_negative"),
            _Cash("2021-03-16", "Vero osakesäästötililtä", "5", "vero_positive"),
            _Cash("2021-03-17", "Aurora Metsä 1234567890", "4.5", "p_tuotto"),
            _Cash("2021-03-17", "Revontuli 9876543210", "-7", "income_negative"),
            _Cash("31.02.2021", "Matti Meikäläinen", "10", "bad_date"),
            _Cash("2021-03-18", "Osto Aurora Metsä Oyj", "12,34,5", "bad_amount"),
            _Cash("2021-03-19", "Palvelumaksut 03/2021", "0", "zero_amount"),
            _Cash("2021-03-26", "Varaus", "-75", "varaus_pending", status="Odottaa"),
            _Cash("2021-03-31", "Palvelumaksut 03/2021", "-3.5", "fee_end"),
            _Cash("2021-04-02", "Osto Kaamos Robotics AB", "-38", "p_k_end"),
        ]
    )


# The expected class of every row of the "classes" scenario: (row kind, reason).
CLASS_TABLE = {
    # custody
    "k0": ("pair", ""),
    "status": ("excluded", "status"),
    "buy_positive_summa": ("excluded", "invalid"),
    "sell_negative_summa": ("excluded", "invalid"),
    "pika_buy": ("pair", ""),
    "paiva_sell": ("pair", ""),
    "tuotto": ("pair", ""),
    "vanha": ("standalone", ""),
    "uusi": ("standalone", ""),
    "uusi_with_summa": ("excluded", "invalid"),
    "unknown_type": ("excluded", "unknown_type"),
    "no_name": ("excluded", "invalid"),
    "no_quantity": ("excluded", "invalid"),
    "no_trade_date": ("excluded", "invalid"),
    "value_before_trade": ("excluded", "invalid"),
    "k_end": ("pair", ""),
    # cash
    "deposit_before": ("standalone", ""),
    # Lot W-B85: a «Varaus» row is a reservation, the label read before the Tila (red until the plugin says so).
    "varaus_label": ("excluded", "reservation"),
    "varaus_pending": ("excluded", "reservation"),
    "pending": ("excluded", "status"),
    "nosto": ("standalone", ""),
    "vero": ("standalone", ""),
    "fee": ("standalone", ""),
    "korko": ("standalone", ""),
    "other_positive": ("standalone", ""),
    "other_negative": ("excluded", "unknown_type"),
    "osto_positive": ("excluded", "unknown_type"),
    "myynti_negative": ("excluded", "unknown_type"),
    "nosto_positive": ("excluded", "unknown_type"),
    "fee_positive": ("excluded", "unknown_type"),
    "korko_negative": ("excluded", "unknown_type"),
    "vero_positive": ("excluded", "unknown_type"),
    "income_negative": ("excluded", "unknown_type"),
    "bad_date": ("excluded", "invalid"),
    "bad_amount": ("excluded", "invalid"),
    "zero_amount": ("excluded", "invalid"),
    "fee_end": ("standalone", ""),
}
CLASS_PAIRS = {"k0": "p_k0", "pika_buy": "p_pika", "paiva_sell": "p_paiva", "tuotto": "p_tuotto", "k_end": "p_k_end"}
# Lot W-B85: the «Varaus» rows of the "classes" scenario, and its rows not booked that are no reservation.
RESERVATION_KEYS = ("varaus_label", "varaus_pending")
STATUS_KEYS = ("status", "pending")

# Lot W-B85 leaves every other notice as it is (D-W85-1, pending). (source, set, codes or reasons it notes): together they
# note every excluded reason but the silent ones, and every other parse notice (fixture guard in TestKnownAndUnknownRows).
EXCLUDED_SOURCES = [
    pytest.param("scenario", "classes", ("status", "invalid", "unknown_type"), id="classes"),
    pytest.param("scenario", "direction", ("no_counterpart",), id="direction"),
    pytest.param("scenario", "ambiguous", ("ambiguous",), id="ambiguous"),
    pytest.param("scenario", "late", ("outside_cash_coverage",), id="late"),
    pytest.param("scenario", "overlap_diff", ("superseded",), id="overlap_diff"),
    pytest.param("scenario", "early_end", ("not_yet_settled",), id="early_end"),
]
NOTICE_SOURCES = [
    pytest.param("sample", "main", ("deferred_rows", "deposit_assumed", SPLIT_NOTICE), id="main"),
    pytest.param("scenario", "same_day", ("proof_discarded",), id="same_day"),
    pytest.param("scenario", "name_mismatch", ("name_mismatch",), id="name_mismatch"),
    pytest.param("scenario", "chain", ("balance_chain_broken",), id="chain"),
]
# The notices of the sample sets, (code, severity, context): every row of the samples is booked and none is a «Varaus»,
# so lot W-B85 changes nothing in them. Project 66, P2c adds the info notice of the split trades: 10 in main, 4 in gap.
SAMPLE_NOTICES = {
    "main": [(SPLIT_NOTICE, "info", {"count": 10}), ("deferred_rows", "info", {"count": 1}), ("deposit_assumed", "info", {"count": 2})],
    "gap": [(SPLIT_NOTICE, "info", {"count": 4}), ("deposit_assumed", "info", {"count": 2}), ("excluded_not_yet_settled", "info", {"count": 1, "reason": "not_yet_settled"})],
}


# =============================================================================
# 1. IDENTITY AND CONTRACT
# =============================================================================


class TestIdentity:
    """B0 "Identità": who the plugin is, the roles it combines, the parameters of its rules."""

    def test_registered_from_its_module(self) -> None:
        plugin = _danske()

        assert plugin.provider_code == PLUGIN_CODE
        assert type(plugin).__module__ == PLUGIN_MODULE

    def test_metadata(self) -> None:
        """Name, extensions, priority, version, icon and docs page. The version is 1.2.0 (project 66, P2c: the commission
        split out as a linked FEE, the withdrawal tax linked)."""
        plugin = _danske()

        # 1.2.0: project 66, P2c, linked charges (1.1.0: lot B-52, trades on Kauppapäivä; 1.0.2: lot W-B85; 1.0.1: lot N74).
        assert (plugin.provider_name, plugin.supported_extensions, plugin.detection_priority, plugin.plugin_version) == ("Danske Bank", [".xlsx", ".csv"], 100, "1.2.0")
        assert plugin.description and plugin.description.strip()
        assert (plugin.icon_url, plugin.docs_url) == ("https://danskebank.fi/favicon.ico", "/mkdocs/user/transactions/import/danske-bank/")
        assert plugin.test_file_pattern == "danske_bank"

    def test_report_set_parameters(self) -> None:
        plugin = _danske()

        assert plugin.is_report_set_plugin is True
        assert (plugin.settlement_lag_business_days, plugin.pre_checkpoint_policy, plugin.history_tag) == (5, "summarize", "danske_bank")

    def test_report_roles(self) -> None:
        """custody: XLSX, required, several files, a year deep; cash: CSV, required, several files, five years, covering custody."""
        roles = _danske().report_roles

        assert all(isinstance(role, BRIMReportRole) for role in roles)
        assert [(role.code, role.required, role.multiple, role.extensions, role.max_history, role.must_cover) for role in roles] == [("custody", True, True, [".xlsx"], "P1Y", None), ("cash", True, True, [".csv"], "P5Y", "custody")]
        assert all(role.description.strip() for role in roles)

    def test_plugin_catalogue_shows_the_roles(self) -> None:
        """The catalogue entry: identity, version 1.2.0 (project 66, P2c) and the two roles."""
        plugin = _danske()

        info = plugin.to_plugin_info()
        catalogue = {item.code: item for item in BRIMProviderRegistry.list_plugin_info()}

        # 1.2.0: project 66, P2c, linked charges (1.1.0: lot B-52, trades on Kauppapäivä; 1.0.2: lot W-B85; 1.0.1: lot N74).
        assert (info.code, info.name, info.plugin_version, info.detection_priority, info.icon_url, info.docs_url) == (PLUGIN_CODE, "Danske Bank", "1.2.0", 100, plugin.icon_url, plugin.docs_url)
        assert info.report_roles == plugin.report_roles
        assert [role.code for role in catalogue[PLUGIN_CODE].report_roles] == ["custody", "cash"]

    def test_declares_its_two_sample_sets(self) -> None:
        """The test-only contract property ``test_sample_sets``: one ``{role: [sample names]}`` per set, in this order."""
        plugin = _danske()
        _require_contract("test_sample_sets")

        assert plugin.test_sample_sets == [MAIN_SET, GAP_SET]

    @pytest.mark.parametrize("name", sorted(SAMPLE_ROLES))
    def test_fixture_guard_samples_exist(self, name: str) -> None:
        """Fixture guard: the five synthetic members are in ``sample_reports/`` and carry the test pattern."""
        assert (SAMPLE_DIR / name).is_file()
        assert "danske_bank" in name


# =============================================================================
# 2. RECOGNITION: can_parse and detect_role
# =============================================================================

FOREIGN_SAMPLES = ["credit_agricole-export.csv", "credit_agricole-export.xlsx", "credit_agricole-conti.xlsx", "intesa-lista.xlsx", "intesa-patrimonio.csv", "generic_simple.csv", "degiro-export.csv"]


def _garbage_files() -> List[Any]:
    """Files no plugin can read, and files whose bytes do not match their extension."""
    custody = (SAMPLE_DIR / "danske_bank-custody.xlsx").read_bytes()
    cash = (SAMPLE_DIR / "danske_bank-cash.csv").read_bytes()
    return [
        pytest.param("empty.csv", b"", id="empty-csv"),
        pytest.param("empty.xlsx", b"", id="empty-xlsx"),
        pytest.param("noise.csv", bytes(range(256)) * 4, id="binary-noise-csv"),
        pytest.param("noise.xlsx", bytes(range(256)) * 4, id="binary-noise-xlsx"),
        pytest.param("truncated.xlsx", custody[: len(custody) // 2], id="truncated-xlsx"),
        pytest.param("statement.xlsx", cash, id="cash-text-named-xlsx"),
        pytest.param("custody.csv", custody, id="custody-zip-named-csv"),
    ]


def _write_rows_csv(path: Path, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> Path:
    """A combined-looking file written without the core, so it may lack a column the core would require."""
    with open(path, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";", lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)
    return path


class TestCanParse:
    """B0 "Riconoscimento": the members and its own combined files — nothing else, and never an exception."""

    @pytest.mark.parametrize("name", sorted(SAMPLE_ROLES))
    def test_every_member_sample_is_its_own(self, name: str) -> None:
        plugin = _danske()
        path = SAMPLE_DIR / name

        assert plugin.can_parse(path) is True
        assert PLUGIN_CODE in BRIMProviderRegistry.get_compatible_plugins(path)
        assert BRIMProviderRegistry.auto_detect_plugin(path) == PLUGIN_CODE

    @pytest.mark.parametrize("set_name", sorted(SAMPLE_SETS))
    def test_its_combined_file_is_its_own(self, set_name: str, tmp_path: Path) -> None:
        plugin = _danske()
        path = tmp_path / f"Danske Bank — combined {set_name}.csv"
        write_combined_csv(path, _sample_table(set_name))

        assert plugin.can_parse(path) is True
        assert BRIMProviderRegistry.auto_detect_plugin(path) == PLUGIN_CODE

    @pytest.mark.parametrize("name", FOREIGN_SAMPLES)
    def test_foreign_samples_are_left_to_their_plugins(self, name: str) -> None:
        plugin = _danske()
        path = SAMPLE_DIR / name
        assert path.is_file()  # presence barrier: a missing file is refused too, for another reason

        assert plugin.can_parse(path) is False
        assert plugin.detect_role(path) is None

    @pytest.mark.parametrize(("name", "content"), _garbage_files())
    def test_unreadable_files_are_refused_without_raising(self, name: str, content: bytes, tmp_path: Path) -> None:
        plugin = _danske()
        path = tmp_path / name
        path.write_bytes(content)

        assert plugin.can_parse(path) is False
        assert plugin.detect_role(path) is None

    @pytest.mark.parametrize("name", ["gone.csv", "gone.xlsx"])
    def test_a_missing_file_is_refused_without_raising(self, name: str, tmp_path: Path) -> None:
        assert _danske().can_parse(tmp_path / name) is False

    @pytest.mark.parametrize("header", ["Kauppapäivä", "Arvopäivä", "Sijoituskohde", "Määrä", "Summa", "Toimeksiantotyyppi"])
    def test_a_custody_export_without_a_required_header_is_refused(self, header: str, tmp_path: Path) -> None:
        plugin = _danske()
        rows = [_trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208)]
        _write_custody(tmp_path / "control.xlsx", rows)
        _write_custody(tmp_path / "custody.xlsx", rows, header=["Muu sarake" if cell == header else cell for cell in CUSTODY_HEADER])

        assert plugin.can_parse(tmp_path / "control.xlsx") is True  # presence barrier: the same file with every header
        assert plugin.can_parse(tmp_path / "custody.xlsx") is False

    @pytest.mark.parametrize("header", ["Pvm", "Saaja/Maksaja", "Määrä", "Saldo", "Tila"])
    def test_a_cash_statement_without_a_required_header_is_refused(self, header: str, tmp_path: Path) -> None:
        plugin = _danske()
        _write_cash(tmp_path / "control.csv", [DEPOSIT])
        path = tmp_path / "cash.csv"
        _write_cash(path, [DEPOSIT])
        lines = path.read_bytes().decode("latin-1").split("\n")
        lines[0] = ";".join("Muu" if cell == header else cell for cell in CASH_HEADER)
        path.write_bytes("\n".join(lines).encode("latin-1"))

        assert plugin.can_parse(tmp_path / "control.csv") is True  # presence barrier
        assert plugin.can_parse(path) is False

    def test_the_custody_header_is_found_below_a_preamble(self, tmp_path: Path) -> None:
        """B0: the custody headers are looked for down to row 20; here they are on row 4."""
        plugin = _danske()
        path = tmp_path / "custody.xlsx"
        _write_custody(path, [_trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208)], preamble=[["Sijoitukset"], ["Tapahtumat 01.03.2021 - 31.03.2021"], [None]])

        assert plugin.can_parse(path) is True
        assert plugin.detect_role(path) == "custody"

    def test_another_plugins_combined_file_is_not_its_own(self, tmp_path: Path) -> None:
        """``lf_`` columns alone do not make a Danske combined file: its own role columns must be there too."""
        plugin = _danske()
        path = _write_rows_csv(tmp_path / "combined.csv", ["lf_row_kind", "lf_source", "custody:trade_date", "custody:asset", "cash:value_date", "cash:amount"], [["standalone", "custody:2", "2025-01-02", "ACME Oyj", "", ""]])

        assert plugin.can_parse(path) is False

    @pytest.mark.parametrize("dropped", ["lf_row_kind", "lf_source", "custody:Toimeksiantotyyppi", "cash:Saaja/Maksaja"])
    def test_its_combined_file_without_a_marker_column_is_refused(self, dropped: str, tmp_path: Path) -> None:
        plugin = _danske()
        table = _sample_table("main")
        keep = [index for index, header in enumerate(table.headers) if header != dropped]
        control = _write_rows_csv(tmp_path / "control.csv", table.headers, table.rows)
        path = _write_rows_csv(tmp_path / "combined.csv", [table.headers[index] for index in keep], [[row[index] for index in keep] for row in table.rows])

        assert plugin.can_parse(control) is True  # presence barrier: the very same file with the column
        assert plugin.can_parse(path) is False


class TestDetectRole:
    """B0: ``custody``, ``cash``, or None — None for its own combined file too."""

    @pytest.mark.parametrize("name", sorted(SAMPLE_ROLES))
    def test_member_samples(self, name: str) -> None:
        assert _danske().detect_role(SAMPLE_DIR / name) == SAMPLE_ROLES[name]

    @pytest.mark.parametrize("set_name", sorted(SAMPLE_SETS))
    def test_a_combined_file_has_no_role(self, set_name: str, tmp_path: Path) -> None:
        plugin = _danske()
        path = tmp_path / "combined.csv"
        write_combined_csv(path, _sample_table(set_name))

        assert plugin.can_parse(path) is True  # presence barrier: it is the plugin's file, only not a member
        assert plugin.detect_role(path) is None


# =============================================================================
# 3. DESCRIBING MEMBERS AND SETS, without combining
# =============================================================================

MEMBER_FACTS = [
    pytest.param("danske_bank-custody.xlsx", "custody", 15, "trade", "2020-02-03", "2020-06-26", id="main-custody"),
    pytest.param("danske_bank-cash.csv", "cash", 32, "value", "2019-01-07", "2020-07-03", id="main-cash"),
    pytest.param("danske_bank-gap-custody-1.xlsx", "custody", 3, "trade", "2020-09-01", "2020-10-30", id="gap-custody-1"),
    pytest.param("danske_bank-gap-custody-2.xlsx", "custody", 4, "trade", "2021-01-05", "2021-02-26", id="gap-custody-2"),
    pytest.param("danske_bank-gap-cash.csv", "cash", 14, "value", "2020-08-03", "2021-03-01", id="gap-cash"),
]


class TestDescribeMember:
    """B0: data rows, coverage on the role's axis from the valid dates, and an account fingerprint kept in memory."""

    @pytest.mark.parametrize(("name", "role", "rows", "axis", "start", "end"), MEMBER_FACTS)
    def test_samples(self, name: str, role: str, rows: int, axis: str, start: str, end: str) -> None:
        summary = _danske().describe_member(SAMPLE_DIR / name)

        assert (summary.role, summary.rows) == (role, rows)
        assert summary.coverage == [BRIMCoverage(axis=axis, start=_d(start), end=_d(end))]

    def test_the_custody_fingerprint_stays_in_memory(self) -> None:
        summary = _danske().describe_member(SAMPLE_DIR / "danske_bank-custody.xlsx")

        assert summary.account_fingerprint, "the deposit check needs a fingerprint of the custody account"
        assert ACCOUNT not in summary.account_fingerprint, "a digest of the account, not the account"
        serialised = json.dumps(summary.model_dump(mode="json")) + summary.model_dump_json()
        assert "account_fingerprint" not in serialised
        assert summary.account_fingerprint not in serialised
        assert ACCOUNT not in serialised

    def test_a_cash_statement_has_no_fingerprint(self) -> None:
        """If it had one, the framework would compare it with the custody one and always report mixed accounts."""
        assert _danske().describe_member(SAMPLE_DIR / "danske_bank-cash.csv").account_fingerprint is None

    def test_fingerprints_tell_the_accounts_apart(self, tmp_path: Path) -> None:
        plugin = _danske()
        prints = {}
        for name, account in (("first", "FI-ACCOUNT-0001"), ("second", "FI-ACCOUNT-0002"), ("first_again", "FI-ACCOUNT-0001")):
            path = tmp_path / f"{name}.xlsx"
            _write_custody(path, [_trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208, account=account)])
            prints[name] = plugin.describe_member(path).account_fingerprint

        assert all(prints.values())
        assert prints["first"] != prints["second"]
        assert prints["first"] == prints["first_again"]

    def test_coverage_counts_valid_dates_only(self, tmp_path: Path) -> None:
        plugin = _danske()
        broken = _trade("2021-03-15", "Aurora Metsä Oyj", 1, 5, -13)
        broken[0] = "31.02.2021"
        path = tmp_path / "custody.xlsx"
        _write_custody(path, [_kaamos("2021-03-01"), broken, _kaamos("2021-03-31")])

        assert plugin.describe_member(path).coverage == [BRIMCoverage(axis="trade", start=_d("2021-03-01"), end=_d("2021-03-31"))]

    @pytest.mark.parametrize("role", ["custody", "cash"])
    def test_an_export_with_its_header_only(self, role: str, tmp_path: Path) -> None:
        """Design §3.3: role recognised, zero rows, no coverage."""
        plugin = _danske()
        path = tmp_path / ("custody.xlsx" if role == "custody" else "cash.csv")
        if role == "custody":
            _write_custody(path, [])
        else:
            _write_cash(path, [])

        summary = plugin.describe_member(path)

        assert (plugin.detect_role(path), summary.role, summary.rows, summary.coverage) == (role, role, 0, [])


class TestDescribeSet:
    """B0: the final merged segments (trade axis), the proven gaps ``[E_i + 1, S_i+1 − 1]``, and notices with stable codes."""

    def test_main_set(self) -> None:
        shape = _danske().describe_set(_members(MAIN_SET))

        assert isinstance(shape, BRIMSetShape)
        assert (shape.segments, shape.gaps) == ([DateRangeModel(start=_d("2020-02-03"), end=_d("2020-06-26"))], [])
        assert _codes(shape.notices) == []

    def test_gap_set(self) -> None:
        shape = _danske().describe_set(_members(GAP_SET))

        assert shape.segments == [DateRangeModel(start=_d("2020-09-01"), end=_d("2020-10-30")), DateRangeModel(start=_d("2021-01-05"), end=_d("2021-02-26"))]
        assert shape.gaps == [DateRangeModel(start=_d("2020-10-31"), end=_d("2021-01-04"))]
        assert _codes(shape.notices) == ["gap"]
        context = shape.notices[0].context or {}
        assert {key: context.get(key) for key in ("start", "end")} == {"start": "2020-10-31", "end": "2021-01-04"}

    def test_a_proven_gap_keeps_the_segments_apart(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        shape = _danske().describe_set(_scenario_files("zones", tmp_path_factory).members())

        assert shape.segments == [DateRangeModel(start=_d("2021-03-01"), end=_d("2021-03-31")), DateRangeModel(start=_d("2021-06-01"), end=_d("2021-06-30"))]
        assert shape.gaps == [DateRangeModel(start=_d("2021-04-01"), end=_d("2021-05-31"))]
        assert _codes(shape.notices).count("gap") == 1

    def test_an_unproven_gap_merges_the_segments(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """No unpaired trade row of the cash statement falls between the two custody exports: one segment."""
        shape = _danske().describe_set(_scenario_files("merged", tmp_path_factory).members())

        assert (shape.segments, shape.gaps) == ([DateRangeModel(start=_d("2021-03-01"), end=_d("2021-06-30"))], [])
        assert "gap" not in _codes(shape.notices)

    def test_a_late_cash_statement_does_not_move_the_segment(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """A13: the segment is the custody coverage, whatever the cash statement covers."""
        shape = _danske().describe_set(_scenario_files("late", tmp_path_factory).members())

        assert shape.segments == [DateRangeModel(start=_d("2021-03-01"), end=_d("2021-03-31"))]

    @pytest.mark.parametrize(("name", "flagged"), [("overlap_diff", True), ("overlap_diff_newer_first", True), ("overlap_same", False), ("overlap_cash", False)])
    def test_overlap_mismatch(self, name: str, flagged: bool, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Rule M: files of one role that disagree on a day they both cover are reported; files that agree are not."""
        shape = _danske().describe_set(_scenario_files(name, tmp_path_factory).members())

        assert ("overlap_mismatch" in _codes(shape.notices)) is flagged
        assert shape.segments == [DateRangeModel(start=_d("2021-03-01"), end=_d("2021-03-31"))]

    def test_an_empty_member(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        plugin = _danske()
        builder = _scenario_files("empty_member", tmp_path_factory)

        shape = plugin.describe_set(builder.members())

        assert "empty_member" in _codes(shape.notices)
        assert shape.segments == [DateRangeModel(start=_d("2021-03-01"), end=_d("2021-03-31"))]
        assert plugin.describe_member(builder.custody[1]).rows == 0

    def test_a_broken_balance_chain(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        shape = _danske().describe_set(_scenario_files("chain", tmp_path_factory).members())

        assert "balance_chain_broken" in _codes(shape.notices)

    def test_two_accounts_in_one_custody_export(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        shape = _danske().describe_set(_scenario_files("mixed_accounts", tmp_path_factory).members())

        assert "mixed_accounts_in_file" in _codes(shape.notices)
        dumped = shape.model_dump_json()
        assert "FI-ACCOUNT-0001" not in dumped and "FI-ACCOUNT-0002" not in dumped

    @pytest.mark.parametrize("set_name", sorted(SAMPLE_SETS))
    def test_never_reveals_the_account(self, set_name: str) -> None:
        shape = _danske().describe_set(_members(SAMPLE_SETS[set_name]))

        assert set(_codes(shape.notices)) <= SET_NOTICES
        assert ACCOUNT not in shape.model_dump_json()


# =============================================================================
# 4. READING: encodings, header spellings, cell types
# =============================================================================


def _main_cash_text() -> str:
    return (SAMPLE_DIR / "danske_bank-cash.csv").read_bytes().decode("latin-1")


def _rename_header(position: int, name: str) -> Callable[[List[Any], List[List[Any]]], None]:
    def rewrite(header: List[Any], _rows: List[List[Any]]) -> None:
        header[position] = name

    return rewrite


def _rewrite_cells(first: int, last: int, cell: Callable[[Any], Any]) -> Callable[[List[Any], List[List[Any]]], None]:
    def rewrite(_header: List[Any], rows: List[List[Any]]) -> None:
        for row in rows:
            row[first:last] = [cell(value) for value in row[first:last]]

    return rewrite


# The ways a custody export may differ from the sample without being different data.
CUSTODY_VARIANTS: Dict[str, Callable[[List[Any], List[List[Any]]], None]] = {
    "br": _rename_header(5, "Palkkio<br>sis. Alv"),
    "space": _rename_header(5, "Palkkio sis. Alv"),
    "valuutta": _rename_header(7, "Valuutta"),
    "no_currency": _rewrite_cells(7, 8, lambda _value: None),
    "date_cells": _rewrite_cells(0, 2, lambda value: datetime.strptime(value, "%d.%m.%Y")),
    "text_numbers_nbsp": _rewrite_cells(3, 7, lambda value: _fi_text(value, thousands="\u00a0", minus="\u2212")),
    "text_numbers_space": _rewrite_cells(3, 7, lambda value: _fi_text(value, thousands=" ", minus="-")),
}


def _custody_variant(variant: str) -> Tuple[List[Any], List[List[Any]]]:
    """The main custody sample, rewritten one way: a header spelling, a missing currency, date cells, Finnish text numbers."""
    header, rows = _sample_custody()
    CUSTODY_VARIANTS[variant](header, rows)
    return header, rows


def _combine_and_parse(custody: Path, cash: Path, folder: Path) -> Tuple[BRIMCombinedTable, BRIMParseOutput]:
    plugin = _danske()
    table = plugin.combine({"custody": [custody], "cash": [cash]})
    path = folder / "combined.csv"
    write_combined_csv(path, table)
    return table, plugin.parse(path, broker_id=BROKER_ID)


def _lf_columns(table: BRIMCombinedTable) -> List[List[str]]:
    return [row[: len(LF_HEADERS)] for row in table.rows]


class TestReadingRobustness:
    """B0 "Lettura": the same data from another encoding, header spelling or cell type makes the same import."""

    @pytest.mark.parametrize("encoding", ["cp1252", "utf-8", "utf-8-sig"])
    def test_cash_statement_encodings(self, encoding: str, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Latin-1 (the sample), cp1252, UTF-8 with and without BOM: the same combined table, the same parse."""
        base_table, _path, base = _sample_parse("main", tmp_path_factory)
        cash = tmp_path / "danske_bank-cash.csv"
        cash.write_bytes(_main_cash_text().encode(encoding))

        table, output = _combine_and_parse(SAMPLE_DIR / "danske_bank-custody.xlsx", cash, tmp_path)

        assert (table.headers, table.rows) == (base_table.headers, base_table.rows)
        assert _essence(output) == _essence(base)

    @pytest.mark.parametrize("separator", [" ", "\u00a0"], ids=["space", "nbsp"])
    def test_cash_amounts_with_thousands_separators(self, separator: str, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
        """F4: Finnish amounts may group thousands with a space or a no-break space; they are the same amounts."""
        base_table, _path, base = _sample_parse("main", tmp_path_factory)
        lines = _main_cash_text().split("\n")
        rewritten = [lines[0]]
        for line in lines[1:]:
            cells = line.split(";")
            if len(cells) == len(CASH_HEADER):
                cells[2], cells[3] = _fi_amount(_number(cells[2]), thousands=separator), _fi_amount(_number(cells[3]), thousands=separator)
            rewritten.append(";".join(cells))
        cash = tmp_path / "danske_bank-cash.csv"
        cash.write_bytes("\n".join(rewritten).encode("latin-1"))
        assert f"6{separator}000" in cash.read_bytes().decode("latin-1")  # presence barrier: the grouping is really there

        table, output = _combine_and_parse(SAMPLE_DIR / "danske_bank-custody.xlsx", cash, tmp_path)

        assert _lf_columns(table) == _lf_columns(base_table)
        assert _essence(output) == _essence(base)

    @pytest.mark.parametrize("variant", ["br", "space", "valuutta", "date_cells"])
    def test_same_cells_under_another_header_or_cell_type(self, variant: str, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
        """``<br>`` or a space in the fee header, the currency column named ``Valuutta``, dates as date cells: the same rows."""
        base_table, _path, base = _sample_parse("main", tmp_path_factory)
        custody = _write_raw_custody(tmp_path / "danske_bank-custody.xlsx", *_custody_variant(variant))

        table, output = _combine_and_parse(custody, SAMPLE_DIR / "danske_bank-cash.csv", tmp_path)

        assert table.rows == base_table.rows
        assert _essence(output) == _essence(base)

    @pytest.mark.parametrize("variant", ["no_currency", "text_numbers_nbsp", "text_numbers_space"])
    def test_same_import_from_other_cell_values(self, variant: str, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
        """An empty currency column means EUR; Finnish text numbers ("−1 181,04") are numbers: the lf_ columns and the parse stay."""
        base_table, _path, base = _sample_parse("main", tmp_path_factory)
        custody = _write_raw_custody(tmp_path / "danske_bank-custody.xlsx", *_custody_variant(variant))

        table, output = _combine_and_parse(custody, SAMPLE_DIR / "danske_bank-cash.csv", tmp_path)

        assert _lf_columns(table) == _lf_columns(base_table)
        assert _essence(output) == _essence(base)

    def test_text_cells_are_copied_as_they_are(self, tmp_path: Path) -> None:
        """Verbatim: a number written as text stays that text in the combined file."""
        custody = _write_raw_custody(tmp_path / "danske_bank-custody.xlsx", *_custody_variant("text_numbers_nbsp"))

        table = _danske().combine({"custody": [custody], "cash": [SAMPLE_DIR / "danske_bank-cash.csv"]})

        kaamos = _data_row(_records(table), "custody", 1, 5)
        assert (kaamos["custody:Määrä"], kaamos["custody:Kurssi"], kaamos["custody:Summa"]) == ("300", "41,2", "\u22121\u00a0181,04")


# =============================================================================
# 5. CLASSES (S1)
# =============================================================================


class TestClassification:
    """S1: one row for every line of the B0 classes table, all in the window of one segment."""

    @pytest.mark.parametrize("key", sorted(CLASS_TABLE))
    def test_row_class(self, key: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """The row kind and reason of each row. Lot W-B85: the two «Varaus» rows (``varaus_label``, ``varaus_pending``) are
        ``("excluded", "reservation")``, the label read before the ``Tila`` — red until the plugin gives them that reason
        (today both are ``status``)."""
        builder, table = _scenario("classes", tmp_path_factory)

        row = builder.row(_records(table), key)

        assert (row["lf_row_kind"], row["lf_reason"]) == CLASS_TABLE[key]

    @pytest.mark.parametrize(("custody", "cash"), sorted(CLASS_PAIRS.items()))
    def test_pairable_rows_meet(self, custody: str, cash: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """A purchase (``Rajakurssi``, ``Pikakauppa``), a sale (``Päivän kurssi``) and an income (``Tuotto``) each meet their cash row."""
        builder, table = _scenario("classes", tmp_path_factory)
        records = _records(table)

        row = builder.row(records, custody)

        assert row["lf_row_kind"] == "pair"
        assert row is builder.row(records, cash)

    def test_every_member_row_lands_in_exactly_one_data_row(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        builder, table = _scenario("classes", tmp_path_factory)

        _assert_each_source_row_once(builder.row_counts, _records(table))

    def test_standalone_cash_rows_become_their_family_type(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """``Nosto`` → WITHDRAWAL, ``Vero`` → TAX, ``Palvelumaksu…`` → FEE, ``Korko…`` → INTEREST, any other income → DEPOSIT."""
        _builder, _table, _path, output = _scenario_parse("classes", tmp_path_factory)
        expected = {
            ("2021-02-01", "Matti Meikäläinen"): ("DEPOSIT", "2000"),
            ("2021-03-08", "Nosto osakesäästötililtä"): ("WITHDRAWAL", "-100"),
            ("2021-03-08", "Vero osakesäästötililtä"): ("TAX", "-12.3"),
            ("2021-03-09", "Palvelumaksut 03/2021"): ("FEE", "-3.5"),
            ("2021-03-10", "Korko 03/2021"): ("INTEREST", "0.42"),
            ("2021-03-11", "Siirto omalta tililtä"): ("DEPOSIT", "150"),
            ("2021-03-31", "Palvelumaksut 03/2021"): ("FEE", "-3.5"),
        }

        found = {(tx.date.isoformat(), tx.description): tx for tx in output.transactions if tx.asset_id is None}

        assert sorted(found) == sorted(expected)
        for key, (tx_type, amount) in expected.items():
            tx = found[key]
            assert (tx.type.value, tx.quantity, tx.cash.code, tx.cash.amount, tx.tags) == (tx_type, Decimal(0), "EUR", Decimal(amount), TAGS), key

    def test_an_assumed_deposit_is_explained(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """A credit with a label of no known family is booked as a deposit (only the holder pays into the account), with an info notice."""
        _builder, _table, _path, output = _scenario_parse("classes", tmp_path_factory)

        notices = [notice for notice in output.warnings if notice.code == "deposit_assumed"]

        assert notices and all(notice.severity == "info" for notice in notices)

    @pytest.mark.parametrize(("source", "name", "reasons"), EXCLUDED_SOURCES)
    def test_guard_an_excluded_row_stays_a_warning_unless_not_yet_settled(self, source: str, name: str, reasons: Tuple[str, ...], tmp_path_factory: pytest.TempPathFactory) -> None:
        """Guard (lot N74, lot W-B85): only ``excluded_not_yet_settled`` became a note; every other excluded reason the parse
        notes is still a warning, ``excluded_status`` included. And no excluded notice but ``excluded_status`` asks for an
        issue: the other reasons wait for a decision (D-W85-1) and carry no ``report_issue`` key at all — green today and
        after."""
        _table, _path, output = _combined(source, name, tmp_path_factory)

        excluded = {notice.code: notice for notice in output.warnings if notice.code.startswith("excluded_")}

        assert {f"excluded_{reason}" for reason in reasons} <= set(excluded), f"premise: the {name} set excludes rows for {reasons}, the parse noted {sorted(excluded)}"
        assert {code: notice.severity for code, notice in excluded.items()} == {code: EXCLUDED_NOTICES.get(code, "warning") for code in excluded}, "every excluded reason but not_yet_settled stays a warning"
        asking = sorted(code for code, notice in excluded.items() if "report_issue" in (notice.context or {}))
        assert set(asking) <= REPORT_ISSUE_NOTICES, f"only {sorted(REPORT_ISSUE_NOTICES)} may ask for an issue, not {asking}"


# =============================================================================
# 5b. KNOWN ROWS QUIETLY, UNKNOWN ROWS LOUDLY (lot W-B85)
# =============================================================================

LOG_CANARY = "danske-bank-test-log-canary"


def _line_of(records: List[Dict[str, str]], record: Dict[str, str]) -> int:
    """The line of ``record`` in the combined file written from ``records``: the header is line 1."""
    return next(number for number, item in enumerate(records, start=2) if item is record)


def _keyed_lines(builder: _Builder, records: List[Dict[str, str]], keys: Sequence[str]) -> Set[int]:
    """The lines of the combined file that carry the keyed member rows."""
    return {_line_of(records, builder.row(records, key)) for key in keys}


def _shown(notice: Any) -> Set[int]:
    """The lines of the combined file a notice shows as evidence."""
    return {number for evidence in notice.evidence for number in evidence.row_numbers}


def _one_notice(output: BRIMParseOutput, code: str) -> Any:
    notices = [notice for notice in output.warnings if notice.code == code]
    assert len(notices) == 1, f"premise: one {code} notice expected, the parse noted {_codes(output.warnings)}"
    return notices[0]


class TestKnownAndUnknownRows:
    """Lot W-B85 on the "classes" scenario. A «Varaus» cash row is a reservation, known and safe to drop: left out in
    silence, still counted in the set, logged once. Every other row not booked is unknown: left out with a warning that
    asks the user to open an issue. Every other notice stays as it is."""

    def test_fixture_guard_the_keys_are_the_scenarios_rows(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Fixture guard: RESERVATION_KEYS and STATUS_KEYS are exactly the rows the class table calls ``reservation`` and
        ``status``, so every count below counts rows the scenario wrote; the two reservations are cash rows labelled
        «Varaus», one booked and one not."""
        builder = _scenario_files("classes", tmp_path_factory)
        cells: Dict[str, List[str]] = {}
        for key in RESERVATION_KEYS:
            role, number, line = builder.where[key]
            assert role == "cash", key
            cells[key] = builder.cash[number - 1].read_bytes().decode("latin-1").split("\n")[line - 1].split(";")

        assert sorted(RESERVATION_KEYS) == sorted(key for key, outcome in CLASS_TABLE.items() if outcome == ("excluded", "reservation"))
        assert sorted(STATUS_KEYS) == sorted(key for key, outcome in CLASS_TABLE.items() if outcome == ("excluded", "status"))
        label, status = CASH_HEADER.index("Saaja/Maksaja"), CASH_HEADER.index("Tila")
        assert sorted((row[label], row[status]) for row in cells.values()) == [("Varaus", "Odottaa"), ("Varaus", "Toteutunut")]

    def test_a_reservation_has_its_own_reason_in_the_set(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red until W-B85: the «Varaus» rows stay in the set's accounting, as excluded rows of reason ``reservation``, and
        ``summary["reasons"]`` counts them under ``reservation`` — no longer under ``status``, which keeps the rows not
        booked only. Today both are ``status`` (4) and there is no ``reservation``."""
        _builder, table = _scenario("classes", tmp_path_factory)
        reasons = table.summary["reasons"]

        assert reasons == dict(Counter(record["lf_reason"] for record in _records(table) if record["lf_row_kind"] in DATA_KINDS and record["lf_reason"])), "premise: the summary counts the reason of every data row"
        assert {reason: reasons.get(reason) for reason in ("reservation", "status")} == {"reservation": len(RESERVATION_KEYS), "status": len(STATUS_KEYS)}

    def test_no_notice_shows_a_reservation(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red until W-B85: a reservation is known and safe to drop, so no notice tells the user about it — there is no
        ``excluded_reservation``, no notice is about the reason ``reservation``, and no notice's evidence shows a «Varaus»
        line. Today ``excluded_status`` shows both, as rows not booked."""
        builder, table, _path, output = _scenario_parse("classes", tmp_path_factory)
        lines = _keyed_lines(builder, _records(table), RESERVATION_KEYS)

        assert [notice.code for notice in output.warnings if notice.code == "excluded_reservation" or (notice.context or {}).get("reason") == "reservation"] == []
        assert {notice.code: sorted(_shown(notice) & lines) for notice in output.warnings if _shown(notice) & lines} == {}, "notices that show a «Varaus» line"

    def test_excluded_status_counts_and_shows_only_the_rows_not_booked(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red until W-B85: ``excluded_status`` is about the rows not booked that are no reservation — the custody
        ``Hylätty`` row and the cash ``Odottaa`` one — so its ``count`` and its evidence are those two rows. Today it
        counts and shows the two «Varaus» rows as well (4)."""
        builder, table, _path, output = _scenario_parse("classes", tmp_path_factory)
        status = _one_notice(output, "excluded_status")

        assert ((status.context or {}).get("count"), sorted(_shown(status))) == (len(STATUS_KEYS), sorted(_keyed_lines(builder, _records(table), STATUS_KEYS)))

    def test_excluded_status_asks_for_an_issue(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red until W-B85: a row not booked that is no reservation is a row the plugin does not know, so ``excluded_status``
        stays a warning about the reason ``status`` and carries ``context["report_issue"] is True`` — the wizard shows the
        link to open an issue under it. Today its context is ``count`` and ``reason`` only."""
        _builder, _table, _path, output = _scenario_parse("classes", tmp_path_factory)
        status = _one_notice(output, "excluded_status")
        context = status.context or {}

        assert (status.severity, context.get("reason")) == ("warning", "status")
        assert context.get("report_issue") is True, f"excluded_status context: {context}"

    def test_a_reservation_is_logged_once_with_its_count(self, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red until W-B85: the backend logs what it leaves out in silence. Across the combine and the parse of the set,
        exactly one structlog event carries ``reason="reservation"``, with ``count`` the «Varaus» rows the scenario wrote
        (2); its wording and its level are not pinned. Read behind a barrier: a canary through the plugin module's own
        logger must reach ``capture_logs``, or a missing event would prove nothing. Today no event carries the reason."""
        plugin = _danske()
        builder = _scenario_files("classes", tmp_path_factory)
        plugin_logger = importlib.import_module(PLUGIN_MODULE).logger

        with capture_logs() as events:
            plugin_logger.info(LOG_CANARY)
            assert any(event.get("event") == LOG_CANARY for event in events), f"barrier: the plugin module's logger does not reach capture_logs: {events}"
            table = plugin.combine(builder.members())
            path = tmp_path / "combined.csv"
            write_combined_csv(path, table)
            plugin.parse(path, broker_id=BROKER_ID)

        logged = [event for event in events if event.get("reason") == "reservation"]
        assert [event.get("count") for event in logged] == [len(RESERVATION_KEYS)], f"one event with reason=reservation and count={len(RESERVATION_KEYS)}; logged: {[event for event in events if event.get('event') != LOG_CANARY]}"

    def test_guard_a_reservation_stays_out_of_the_running_balance(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Guard (W-B85), green today and after: a «Varaus» row does not move the bank's balance, so whatever its reason it
        stays out of the running balance the plugin checks. The scenario's statement holds its chain in the combine, in
        the parse and in the description of the set."""
        builder, table, _path, output = _scenario_parse("classes", tmp_path_factory)

        assert [path.name for path in builder.cash if _chain_breaks(path)] == [], "premise: the statement as written holds its chain"
        assert table.summary["balance_chain"] == "ok"
        assert "balance_chain_broken" not in _codes(output.warnings)
        assert "balance_chain_broken" not in _codes(_danske().describe_set(builder.members()).notices)

    @pytest.mark.parametrize(("source", "name", "codes"), NOTICE_SOURCES)
    def test_guard_the_other_notices_are_unchanged(self, source: str, name: str, codes: Tuple[str, ...], tmp_path_factory: pytest.TempPathFactory) -> None:
        """Guard (W-B85, D-W85-1 pending), green today and after: the notes (``deferred_rows``, ``proof_discarded``,
        ``deposit_assumed``), ``name_mismatch`` and ``balance_chain_broken`` keep their severity and never ask for an
        issue — no ``report_issue`` key."""
        _table, _path, output = _combined(source, name, tmp_path_factory)
        notices = [notice for notice in output.warnings if notice.code in PARSE_NOTICES]

        assert set(codes) <= set(_codes(notices)), f"premise: the {name} set notes {codes}, the parse noted {_codes(output.warnings)}"
        assert sorted({(notice.code, notice.severity) for notice in notices}) == sorted({(notice.code, PARSE_NOTICES[notice.code]) for notice in notices})
        assert [notice.code for notice in notices if "report_issue" in (notice.context or {})] == []

    def test_fixture_guard_the_guards_see_every_other_notice(self) -> None:
        """Fixture guard: the guards on the other notices see every excluded reason but the silent ones, and every other
        parse notice."""
        assert {reason for param in EXCLUDED_SOURCES for reason in param.values[2]} == REASONS - SILENT_REASONS
        assert {code for param in NOTICE_SOURCES for code in param.values[2]} == set(PARSE_NOTICES)

    @pytest.mark.parametrize("set_name", sorted(SAMPLE_SETS))
    def test_guard_the_sample_notices_are_unchanged(self, set_name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Guard (W-B85), green today and after: the samples hold no reservation and no row not booked (fixture guard
        below), so their notices stay exactly as they are — codes, severities, context, and no ``report_issue``."""
        _table, _path, output = _sample_parse(set_name, tmp_path_factory)

        assert sorted(((notice.code, notice.severity, notice.context) for notice in output.warnings), key=lambda item: item[:2]) == SAMPLE_NOTICES[set_name]

    def test_fixture_guard_the_samples_hold_no_reservation_and_no_row_not_booked(self) -> None:
        """Fixture guard: every custody row of the samples is ``Toteutettu``, every cash row ``Toteutunut``, and no cash
        label is «Varaus»."""
        label, status = CASH_HEADER.index("Saaja/Maksaja"), CASH_HEADER.index("Tila")
        for name, role in sorted(SAMPLE_ROLES.items()):
            if role == "custody":
                header, rows = _sample_custody(name)
                assert {row[header.index("Tila")] for row in rows} == {"Toteutettu"}, name
            else:
                rows = [line.split(";") for line in (SAMPLE_DIR / name).read_bytes().decode("latin-1").split("\n")[1:] if line]
                assert {row[status] for row in rows} == {"Toteutunut"}, name
                assert [row[label] for row in rows if row[label].strip().casefold() == "varaus"] == [], name


# =============================================================================
# 6. RULE M (D-S28): several files of one role
# =============================================================================


class TestRuleM:
    """Per role, the file that ends last wins each day it covers; identical days keep one copy, differing days exclude the loser's rows."""

    def test_identical_overlap_keeps_one_copy_of_each_row(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Both custody exports hold the same two partial fills on 03-10: two pairs, not four, not one."""
        builder, table = _scenario("overlap_same", tmp_path_factory)
        records = _records(table)

        saimaa = [record for record in records if record["lf_row_kind"] in DATA_KINDS and record["custody:Sijoituskohde"] == "Saimaa Energia Oyj"]

        assert [record["lf_row_kind"] for record in saimaa] == ["pair", "pair"]
        assert {builder.row(records, "c1")["lf_source"], builder.row(records, "c2")["lf_source"]} == {record["lf_source"] for record in saimaa}
        assert [record["lf_source"] for record in records if record["lf_row_kind"] == "excluded"] == []

    @pytest.mark.parametrize(("name", "loser_file"), [("overlap_diff", 1), ("overlap_diff_newer_first", 2)])
    def test_differing_overlap_the_newer_file_wins(self, name: str, loser_file: int, tmp_path_factory: pytest.TempPathFactory) -> None:
        """The export ending 03-31 wins 03-10 over the one ending 03-10, whatever the upload order; the loser's row is ``superseded``."""
        builder, table = _scenario(name, tmp_path_factory)
        records = _records(table)
        assert builder.where["x"][1] == loser_file  # fixture guard: the older export is where the parametrization says

        loser = builder.row(records, "x")

        assert (loser["lf_row_kind"], loser["lf_reason"]) == ("excluded", "superseded")
        assert [record["lf_source"] for record in records if record["lf_reason"] == "superseded"] == [loser["lf_source"]]
        for custody, cash in (("x2", "ca"), ("y", "cs"), ("k1", None)):
            row = builder.row(records, custody)
            assert row["lf_row_kind"] == "pair", custody
            if cash is not None:
                assert row is builder.row(records, cash)

    def test_identical_overlap_of_cash_statements(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        _builder, table = _scenario("overlap_cash", tmp_path_factory)

        kinds = Counter(record["lf_row_kind"] for record in _records(table) if record["lf_row_kind"] in DATA_KINDS)

        assert kinds == Counter({"pair": 3, "standalone": 1})


# =============================================================================
# 7. PAIRING (S2–S4)
# =============================================================================


class TestPairing:
    """The key is value date, amount to the cent, currency and direction; the name is a check; one to one; never a guess."""

    def test_the_direction_is_part_of_the_key(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """An income and a sale of the same amount on the same day do not meet: each stays without counterpart."""
        builder, table = _scenario("direction", tmp_path_factory)
        records = _records(table)

        for key in ("t", "c"):
            row = builder.row(records, key)
            assert (row["lf_row_kind"], row["lf_reason"]) == ("excluded", "no_counterpart"), key

    def test_a_unique_key_pairs_despite_another_name(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """S3: the pair is made, with a ``name_mismatch`` warning; the asset comes from the custody row."""
        builder, table, _path, output = _scenario_parse("name_mismatch", tmp_path_factory)
        records = _records(table)

        pair = builder.row(records, "a")

        assert pair["lf_row_kind"] == "pair" and pair is builder.row(records, "c")
        notices = [notice for notice in output.warnings if notice.code == "name_mismatch"]
        assert notices and all(notice.severity == "warning" for notice in notices)
        # Found by its cash, not by its date: lot B-52 moves the date of a pair from the value date to the trade date. Project 66,
        # P2c: the purchase is booked at 10 × 20 and its 8 of charges are a FEE linked to it (_owed_split of the pair).
        trade_cash, charges = _owed_split(pair)
        assert (trade_cash, charges) == (Decimal("-200"), Decimal("8")), "premise: 10 × 20 explains the 208 paid"
        [buy] = [tx for tx in output.transactions if tx.type.value == "BUY" and tx.cash is not None and tx.cash.amount == trade_cash]
        assert [(tx.type.value, tx.cash.amount) for tx in output.transactions if buy.ref and tx.parent_ref == buy.ref] == [("FEE", -charges)], "its commission is a FEE linked to it"
        assert (_names(output)[buy.asset_id], buy.description) == ("Aurora Metsä Oyj", "Osto Revontuli Oyj (Rajakurssi)")

    def test_names_sort_out_two_titles_with_the_same_key(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """S4: among the matchings of maximum size, the one with most compatible names — here not the file order."""
        builder, table, _path, output = _scenario_parse("by_name", tmp_path_factory)
        records = _records(table)

        assert builder.row(records, "a") is builder.row(records, "ca")
        assert builder.row(records, "s") is builder.row(records, "cs")
        assert "name_mismatch" not in _codes(output.warnings)

    def test_candidates_that_cannot_be_told_apart_are_all_excluded(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """A truncated label compatible with two titles, and two different trades: every row of the key is ``ambiguous``."""
        builder, table = _scenario("ambiguous", tmp_path_factory)
        records = _records(table)

        for key in ("p1", "p2", "cp"):
            row = builder.row(records, key)
            assert (row["lf_row_kind"], row["lf_reason"]) == ("excluded", "ambiguous"), key

    def test_identical_partial_fills_are_two_pairs(self) -> None:
        """The main sample buys Saimaa Energia twice on 2020-03-25, 25 × 12.4 each: two pairs, one cash row each."""
        records = _records(_sample_table("main"))

        fills = [_data_row(records, "custody", 1, line) for line in (14, 15)]

        assert [record["lf_row_kind"] for record in fills] == ["pair", "pair"]
        assert fills[0] is not fills[1]
        assert sorted(line for record in fills for role, _number, line in _sources(record) if role == "cash") == [13, 14]

    @pytest.mark.parametrize("count", [8, 9])
    def test_more_than_eight_candidates_a_side_are_ambiguous(self, count: int, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Identical fills pair up to eight a side; beyond that the search stops and every row of the key is ``ambiguous``."""
        builder, table = _scenario(f"crowd_{count}", tmp_path_factory)
        records = _records(table)

        rows = [builder.row(records, f"s{index}") for index in range(count)] + [builder.row(records, f"c{index}") for index in range(count)]

        if count <= 8:
            assert all(row["lf_row_kind"] == "pair" for row in rows)
            assert len({row["lf_source"] for row in rows}) == count
        else:
            assert all((row["lf_row_kind"], row["lf_reason"]) == ("excluded", "ambiguous") for row in rows)


# =============================================================================
# 8. ZONES AND OUTCOMES (design §3.4.2, B0 table)
# =============================================================================

# key, row kind, accepted zones, reason, checkpoint. Where B0 says only that a row "follows
# the next zone" (a trade settled after the end of a custody export, inside its window),
# the outcome is pinned and the zone may be the physical one or the next one.
ZONE_CELLS = [
    pytest.param("c1", "standalone", {"before"}, "", "2021-02-28", id="before-standalone-absorbed"),
    pytest.param("c2", "standalone", {"before"}, "", "2021-02-28", id="before-fee-absorbed"),
    pytest.param("c3", "summarized", {"before"}, "", "2021-02-28", id="before-unpaired-trade-summarized"),
    pytest.param("c4", "excluded", {"before"}, "unknown_type", "2021-02-28", id="before-excluded-still-absorbed"),
    pytest.param("c5", "summarized", {"window"}, "", "2021-02-28", id="border-orphan-segment-1"),
    pytest.param("a1", "pair", {"window"}, "", "", id="window-pair"),
    pytest.param("a2", "excluded", {"window"}, "no_counterpart", "", id="window-trade-without-cash"),
    pytest.param("c7", "excluded", {"window"}, "no_counterpart", "", id="window-cash-without-trade"),
    pytest.param("c8", "standalone", {"window"}, "", "", id="window-standalone"),
    pytest.param("c10", "summarized", {"window", "gap"}, "", "2021-05-31", id="beyond-end-follows-the-gap"),
    pytest.param("c11", "standalone", {"gap"}, "", "", id="gap-standalone-imported"),
    pytest.param("c12", "summarized", {"gap"}, "", "2021-05-31", id="gap-unpaired-trade-summarized"),
    pytest.param("c13", "summarized", {"window"}, "", "2021-05-31", id="border-orphan-segment-2"),
    pytest.param("b1", "pair", {"window"}, "", "", id="segment-2-pair"),
    pytest.param("c15", "standalone", {"window"}, "", "", id="segment-2-standalone"),
    pytest.param("c17", "deferred", {"window", "after"}, "", "", id="beyond-end-of-last-segment-deferred"),
    pytest.param("c18", "deferred", {"after"}, "", "", id="after-unpaired-trade-deferred"),
    pytest.param("c19", "standalone", {"after"}, "", "", id="after-standalone"),
]


class TestZones:
    """Every cell of the zones table, on one set: two segments, a proven gap, cash rows before, between and after.

    Segment 1: trades 2021-03-01…03-31, C1 = 02-28, border 03-01…03-05, window to 04-07.
    Segment 2: trades 06-01…06-30, C2 = 05-31, border 06-01…06-07, window to 07-07.
    """

    @pytest.mark.parametrize(("key", "kind", "zones", "reason", "checkpoint"), ZONE_CELLS)
    def test_cell(self, key: str, kind: str, zones: Set[str], reason: str, checkpoint: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        builder, table = _scenario("zones", tmp_path_factory)

        row = builder.row(_records(table), key)

        assert row["lf_row_kind"] == kind
        assert row["lf_zone"] in zones
        assert (row["lf_reason"], row["lf_checkpoint"]) == (reason, checkpoint)

    @pytest.mark.parametrize(("custody", "cash", "match_key"), [("a1", "c6", "2021-03-03|-208.00|EUR"), ("a3", "c9", "2021-04-02|92.00|EUR"), ("b1", "c14", "2021-06-03|-98.00|EUR"), ("b2", "c16", "2021-07-02|-38.00|EUR")])
    def test_pairs(self, custody: str, cash: str, match_key: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        builder, table = _scenario("zones", tmp_path_factory)
        records = _records(table)

        row = builder.row(records, custody)

        assert row is builder.row(records, cash)
        assert (row["lf_row_kind"], row["lf_zone"], row["lf_match_key"]) == ("pair", "window", match_key)

    def test_every_member_row_lands_in_exactly_one_data_row(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        builder, table = _scenario("zones", tmp_path_factory)

        _assert_each_source_row_once(builder.row_counts, _records(table))

    def test_truth_points(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """C1: 4746.50 at the end of 02-28 plus the border orphan (−120); C2: 4557.00 at the end of 05-31 plus its orphan (−150).

        Nothing is in flight at either checkpoint. The verification on 06-30 is in operation-date terms (lot B-52): the
        bank's 4305.50 at the end of the day, plus the purchase b2, traded that day and settled on 07-02 (−38), gives
        4267.50. Red until the plugin counts the trades in flight."""
        _builder, table, _path, output = _scenario_parse("zones", tmp_path_factory)
        records = _records(table)

        assert [(row["lf_checkpoint"], row["lf_value"], row["lf_currency"], row["lf_zone"]) for row in _truth(records, "truth_cash")] == [("2021-02-28", "4626.50", "EUR", "before"), ("2021-05-31", "4407.00", "EUR", "gap")]
        assert [(row["lf_checkpoint"], row["lf_value"], row["lf_currency"]) for row in _truth(records, "verification")] == [("2021-06-30", "4267.50", "EUR")]
        assert _truth(records, "truth_position") == []
        opening, gap = _checkpoint(output, "2021-02-28"), _checkpoint(output, "2021-05-31")
        assert (opening.kind, _money(opening.cash), opening.absorbed.count, _money(opening.absorbed.opening_cash)) == ("opening", {"EUR": Decimal("4626.50")}, 5, {"EUR": Decimal("0")})
        assert (gap.kind, _money(gap.cash), gap.absorbed.count, _money(gap.absorbed.cash), gap.absorbed.opening_cash) == ("gap", {"EUR": Decimal("4407.00")}, 3, {"EUR": Decimal("-300")}, [])
        assert [(item.as_of, _money(item.cash)) for item in output.verifications] == [(_d("2021-06-30"), {"EUR": Decimal("4267.50")})]


# =============================================================================
# 9. TRUTH POINTS: checkpoints, verification, balance chain
# =============================================================================


class TestTruthPoints:
    """B0 "Punti di verità": where the checkpoints are, their cash, what they absorb, the final verification, the chain."""

    def test_a_late_cash_statement_opens_on_the_eve_of_the_custody_export(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red today: the opening is on the eve of the statement, 03-09, and k1 lies before it.

        A13, the developer's decision (20/10/2026). The cash statement starts on 03-10, after the custody export (03-01).
        The opening is on the eve of the custody export, 02-28, as for a normal set. Its cash is the statement's first
        balance, the balance before its first row: 1000.00. It absorbs no row. The purchase k1, settled on 03-03 before
        the statement, stays left out (``outside_cash_coverage``). It is settled after the opening, so its zone is the
        window, like a trade settled in a hole between two statements."""
        builder, table, _path, output = _scenario_parse("late", tmp_path_factory)
        records = _records(table)
        early = builder.row(records, "k1")

        assert _member_starts(builder.members()) == (_d("2021-03-01"), _d("2021-03-10")), "premise: A13, the cash statement starts after the custody export"
        assert (early["lf_row_kind"], early["lf_reason"]) == ("excluded", "outside_cash_coverage"), "premise: k1, settled before the statement, is left out"
        assert builder.row(records, "t") is builder.row(records, "e1")
        assert builder.row(records, "k2") is builder.row(records, "e2")

        assert [(row["lf_checkpoint"], row["lf_value"], row["lf_currency"]) for row in _truth(records, "truth_cash")] == [("2021-02-28", "1000.00", "EUR")], "A13 (20/10): the opening on the eve of the custody export"
        opening = _checkpoint(output, "2021-02-28")
        assert (opening.kind, _money(opening.cash), opening.absorbed.count, opening.absorbed.rows) == ("opening", {"EUR": Decimal("1000.00")}, 0, [])
        assert _money(opening.absorbed.opening_cash) == {"EUR": Decimal("1000.00")}
        assert early["lf_zone"] == "window", "k1 is settled after the opening"

    def test_a_trade_settled_in_a_hole_between_cash_statements(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        builder, table = _scenario("hole", tmp_path_factory)
        records = _records(table)

        row = builder.row(records, "k")

        assert (row["lf_row_kind"], row["lf_reason"]) == ("excluded", "outside_cash_coverage")
        assert builder.row(records, "a") is builder.row(records, "g2")
        assert builder.row(records, "l") is builder.row(records, "h2")

    def test_a_trade_settled_after_the_last_cash_row_is_not_yet_settled(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        builder, table = _scenario("early_end", tmp_path_factory)

        row = builder.row(_records(table), "k")

        assert (row["lf_row_kind"], row["lf_reason"]) == ("excluded", "not_yet_settled")

    def test_the_opening_absorbs_the_rows_before_it(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """``opening_cash`` = the checkpoint cash minus what it absorbs: here the balance the statement starts from."""
        _builder, _table, _path, output = _scenario_parse("early_end", tmp_path_factory)

        opening = _checkpoint(output, "2021-02-28")

        assert (opening.kind, _money(opening.cash), opening.absorbed.count) == ("opening", {"EUR": Decimal("1500.00")}, 1)
        assert [(row.as_of, row.currency, row.amount, row.label) for row in opening.absorbed.rows] == [(_d("2021-02-01"), "EUR", Decimal("500"), "Matti Meikäläinen")]
        assert (_money(opening.absorbed.cash), _money(opening.absorbed.opening_cash)) == ({"EUR": Decimal("500")}, {"EUR": Decimal("1000.00")})

    @pytest.mark.parametrize(
        ("source", "name", "as_of", "amount"),
        [
            # 1994.46 at the end of 2020-06-26, minus the Tunturi purchase traded that day and settled on 06-30 (−218).
            pytest.param("sample", "main", "2020-06-26", "1776.46", id="segment-ends-first"),
            # Nothing in flight: the last trade (03-31) is after V, and it is left out anyway (not_yet_settled).
            pytest.param("scenario", "early_end", "2021-03-25", "1288.50", id="cash-ends-first"),
            # 1015.00 at the end of 2021-03-31, minus the Kaamos purchase traded that day and settled on 04-02 (−38).
            pytest.param("scenario", "late", "2021-03-31", "977.00", id="late-cash-statement"),
        ],
    )
    def test_the_verification_is_at_the_earlier_end(self, source: str, name: str, as_of: str, amount: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """V = min(end of the last segment, last cash row). Its cash is in operation-date terms (lot B-52): the bank's
        balance at the end of that day plus the cash of the trades in flight on it, meaning the pairs traded on or before V
        and settled after it. Red until the plugin counts them, for main and late, whose last trade settles after V. Green
        for early_end, which has nothing in flight."""
        table, _path, output = _combined(source, name, tmp_path_factory)

        assert [(row["lf_checkpoint"], row["lf_value"], row["lf_currency"]) for row in _truth(_records(table), "verification")] == [(as_of, amount, "EUR")]
        assert [(item.as_of, _money(item.cash)) for item in output.verifications] == [(_d(as_of), {"EUR": Decimal(amount)})]

    def test_a_gap_checkpoint_needs_a_proven_gap(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        _merged_builder, merged = _scenario("merged", tmp_path_factory)
        _zones_builder, zones = _scenario("zones", tmp_path_factory)

        assert [row["lf_checkpoint"] for row in _truth(_records(merged), "truth_cash")] == ["2021-02-28"]
        assert [row["lf_checkpoint"] for row in _truth(_records(zones), "truth_cash")] == ["2021-02-28", "2021-05-31"]

    def test_the_rows_of_an_unproven_gap_stay_in_the_window(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        builder, table, _path, output = _scenario_parse("merged", tmp_path_factory)
        records = _records(table)

        for key in ("deposit", "fee"):
            row = builder.row(records, key)
            assert (row["lf_row_kind"], row["lf_zone"], row["lf_checkpoint"]) == ("standalone", "window", ""), key
        assert [(item.as_of, item.kind, _money(item.cash)) for item in output.checkpoints] == [(_d("2021-02-28"), "opening", {"EUR": Decimal("5000.00")})]

    def test_a_broken_balance_chain_turns_the_checkpoint_cash_into_a_verification(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """The truth_cash row stays, with no value; the checkpoint has no cash; a verification at its date carries the stated balance."""
        _builder, table, _path, output = _scenario_parse("chain", tmp_path_factory)
        records = _records(table)

        assert [(row["lf_checkpoint"], row["lf_value"]) for row in _truth(records, "truth_cash")] == [("2021-02-28", "")]
        assert ("2021-02-28", "1500.00") in [(row["lf_checkpoint"], row["lf_value"]) for row in _truth(records, "verification")]
        assert _checkpoint(output, "2021-02-28").cash == []
        assert (_d("2021-02-28"), {"EUR": Decimal("1500.00")}) in [(item.as_of, _money(item.cash)) for item in output.verifications]
        notices = [notice for notice in output.warnings if notice.code == "balance_chain_broken"]
        assert notices and all(notice.severity == "warning" for notice in notices)


# =============================================================================
# 10. PROOFS OF POSITION (E1–E4)
# =============================================================================


class TestProofs:
    """B0: one position per title and checkpoint, from the proofs of the segment, carried back to C_i."""

    @pytest.mark.parametrize("name", ["recent_trade", "recent_cash"])
    def test_e1_is_discarded_by_a_trade_in_the_30_days_before(self, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """A purchase of the title (custody row, or an unpaired ``Osto`` cash row) in the 30 days before the ``Tuotto``."""
        _builder, table, _path, output = _scenario_parse(name, tmp_path_factory)

        assert [row["lf_proof"] for row in _positions_by_title(_records(table), "Aurora Metsä Oyj")] == ["discarded:E1:recent_trades"]
        assert "Aurora Metsä Oyj" not in _positions(output, _checkpoint(output, "2021-02-28"))
        assert "proof_discarded" in _codes(output.warnings)

    def test_e1_is_discarded_when_the_30_days_fall_before_the_cash_statement(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """The ``Tuotto`` of "late" (03-10) is the statement's first row, so the 30 days before it are not covered. Its title
        has no position at the opening, which is on the eve of the custody export, 02-28 (A13, 20/10/2026). Red today
        only for that date: the opening is on 03-09."""
        _builder, table, _path, output = _scenario_parse("late", tmp_path_factory)

        assert [row["lf_proof"] for row in _positions_by_title(_records(table), "Aurora Metsä Oyj")] == ["discarded:E1:window_not_covered"]
        assert "proof_discarded" in _codes(output.warnings)
        assert "Aurora Metsä Oyj" not in _positions(output, _checkpoint(output, "2021-02-28"))

    def test_e2_is_discarded_by_another_movement_the_same_day(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Without an exact proof E3 applies: a sale of 10 and the old line of 100 prove at least 110."""
        _builder, table, _path, output = _scenario_parse("same_day", tmp_path_factory)
        proofs = [row["lf_proof"] for row in _positions_by_title(_records(table), "Lumi Holding Oyj")]

        assert "discarded:E2:same_day_movement" in proofs
        assert "exact:E2" not in proofs
        assert _positions(output, _checkpoint(output, "2021-02-28"))["Lumi Holding Oyj"] == (Decimal("110"), "at_least")
        assert "proof_discarded" in _codes(output.warnings)

    def test_e4_an_excluded_row_before_the_proof_discards_it(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """A cancelled purchase of the title between C1 and the ``Tuotto``: the ``Tuotto`` proves nothing."""
        _builder, table, _path, output = _scenario_parse("excluded_proof", tmp_path_factory)
        proofs = [row["lf_proof"] for row in _positions_by_title(_records(table), "Aurora Metsä Oyj")]

        assert proofs and all(re.fullmatch(r"discarded:E[1-4]:excluded_rows", proof) for proof in proofs), proofs
        assert "Aurora Metsä Oyj" not in _positions(output, _checkpoint(output, "2021-02-28"))
        assert "proof_discarded" in _codes(output.warnings)

    def test_e4_a_superseded_row_does_not_discard(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """The row rule M excluded as ``superseded`` is not an excluded row for E4: the ``Tuotto`` proves exactly 60."""
        builder, table, _path, output = _scenario_parse("superseded_proof", tmp_path_factory)
        records = _records(table)

        assert (builder.row(records, "x")["lf_row_kind"], builder.row(records, "x")["lf_reason"]) == ("excluded", "superseded")
        assert [(row["lf_proof"], row["lf_value"]) for row in _positions_by_title(records, "Aurora Metsä Oyj")] == [("exact:E1", "60")]
        assert _positions(output, _checkpoint(output, "2021-02-28"))["Aurora Metsä Oyj"] == (Decimal("60"), "exact")

    def test_exact_proofs_that_disagree_are_all_discarded(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """The ``Tuotto`` says 150, the demerger 120, nothing moved in between: both go (``conflict``); E3 still proves 120."""
        _builder, table, _path, output = _scenario_parse("conflict", tmp_path_factory)
        proofs = [row["lf_proof"] for row in _positions_by_title(_records(table), "Lumi Holding Oyj")]

        assert {"discarded:E1:conflict", "discarded:E2:conflict"} <= set(proofs)
        assert not [proof for proof in proofs if proof.startswith("exact:")]
        assert _positions(output, _checkpoint(output, "2021-02-28"))["Lumi Holding Oyj"] == (Decimal("120"), "at_least")
        assert "proof_discarded" in _codes(output.warnings)


# =============================================================================
# 10b. TRUTHS IN OPERATION-DATE TERMS (lot B-52, the condition of the lot)
# =============================================================================
#
# Lot B-52 records a paired trade on its trade date T (custody Kauppapäivä), while the bank moves its cash on the value date
# V (cash Pvm). Every truth at a day D is therefore stated in operation-date terms: it adds what is in flight at D, the
# trades imported as pairs with T <= D < V. Two scenarios have a trade straddling a truth point (the final verification, a
# gap checkpoint), and one has the normal opening, where nothing can straddle.
#
# The A13 sets, whose cash statement starts after the custody export, follow the developer's decision of 20/10/2026. They
# open on the eve of the custody export, like any other set, so nothing straddles their opening either. A trade straddling
# the statement's start is imported on its trade date, after the opening. Four scenarios pin them, two as guards.
#
# Every scenario starts from the usual 1000 (OPENING). The straddling ones and the A13 opening are proven end to end too,
# with the gap-fix of a first import (``_first_import_gap_fix``).

#: The real asset ids the B-52 end-to-end proofs give the fake ones, as the user does in the wizard (any id that is not fake).
REAL_ASSET_BASE = 101


@scenario("b52_verification")
def _b52_verification(builder: _Builder) -> None:
    """A sale and a purchase traded on the last custody day (03-31) settle on 04-02. The cash statement runs to 04-30, so
    the final verification is on 03-31, between their two dates."""
    builder.add_custody(
        [
            ("a", _trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208)),  # value 03-03
            ("s", _trade("2021-03-31", "Aurora Metsä Oyj", -4, 25, 92, kind="Päivän kurssi")),  # value 04-02
            ("k", _kaamos("2021-03-31")),  # value 04-02
        ]
    )
    builder.add_cash(
        [
            DEPOSIT,
            _Cash("2021-03-03", "Osto Aurora Metsä Oyj", "-208", "ca"),
            _Cash("2021-04-02", "Myynti Aurora Metsä Oyj", "92", "cs"),
            _Cash("2021-04-02", "Osto Kaamos Robotics AB", "-38", "ck"),
            _Cash("2021-04-30", "Palvelumaksut 04/2021", "-3.5", "fee"),
        ],
        opening=OPENING,
    )


@scenario("b52_a13")
def _b52_a13(builder: _Builder) -> None:
    """A13 with a trade straddling the start of the cash statement. The custody export starts on 03-01 and the cash
    statement on 03-10. The Aurora purchase x, traded on 03-08, settles on 03-10, the statement's first row: it pairs. The
    Tuotto of 04-20 (60 shares) proves Aurora's position. Two trades are left out: k1, settled on 03-03 before the
    statement (``outside_cash_coverage``), and n, traded on 03-08 and due on 03-10 with no cash row (``no_counterpart``)."""
    builder.add_custody(
        [
            ("k1", _trade("2021-03-01", "Kaamos Robotics AB", 2, 30, -68)),  # value 03-03, before the statement
            ("x", _trade("2021-03-08", "Aurora Metsä Oyj", 10, 20, -208)),  # value 03-10
            ("n", _trade("2021-03-08", "Lumi Holding Oyj", 5, 10, -58)),  # value 03-10, no cash row
            ("t", _tuotto("2021-04-20", "Aurora Metsä Oyj", 60, 9)),
        ]
    )
    builder.add_cash([_Cash("2021-03-10", "Osto Aurora Metsä Oyj", "-208", "cx"), _Cash("2021-04-20", "Aurora Metsä 1234567890", "9", "ct"), _Cash("2021-04-30", "Palvelumaksut 04/2021", "-3.5", "fee")], opening=OPENING)


@scenario("b52_gap")
def _b52_gap(builder: _Builder) -> None:
    """Two custody exports one business day apart: trades 03-01…03-31 and 04-02…05-03, so C2 = 04-01. The Kaamos purchase
    k, traded on 03-31, settles on 04-02: it is in flight at C2. A Saimaa purchase and a Saimaa sale on 04-01 (no custody
    row) prove the gap and cancel out, so the gap checkpoint has nothing of its own to correct. The Tuotto of 05-03 (3
    shares) proves Kaamos's position at C2."""
    builder.add_custody(
        [
            ("a", _trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208)),  # value 03-03
            ("k0", _trade("2021-03-10", "Kaamos Robotics AB", 2, 30, -68)),  # value 03-12
            ("k", _kaamos("2021-03-31")),  # value 04-02
        ]
    )
    builder.add_custody([("b", _trade("2021-04-02", "Lumi Holding Oyj", 5, 10, -58)), ("t", _tuotto("2021-05-03", "Kaamos Robotics AB", 3, 1.5))])  # b: value 04-06
    builder.add_cash(
        [
            DEPOSIT,
            _Cash("2021-03-03", "Osto Aurora Metsä Oyj", "-208", "ca"),
            _Cash("2021-03-12", "Osto Kaamos Robotics AB", "-68", "ck0"),
            _Cash("2021-04-01", "Osto Saimaa Energia Oyj", "-300", "gb"),
            _Cash("2021-04-01", "Myynti Saimaa Energia Oyj", "300", "gs"),
            _Cash("2021-04-02", "Osto Kaamos Robotics AB", "-38", "ck"),
            _Cash("2021-04-06", "Osto Lumi Holding Oyj", "-58", "cb"),
            _Cash("2021-05-03", "Kaamos Robotics 1234567890", "1.5", "ct"),
            _Cash("2021-05-31", "Palvelumaksut 05/2021", "-3.5", "fee"),
        ],
        opening=OPENING,
    )


@scenario("b52_opening")
def _b52_opening(builder: _Builder) -> None:
    """The normal opening: the cash statement starts before the custody export, so every trade is after C1 = 02-28 and
    none can be in flight there. The segment ends with a Tuotto (both dates equal), so nothing is in flight at the
    verification either."""
    builder.add_custody([("a", _trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, -208)), ("t", _tuotto("2021-04-20", "Aurora Metsä Oyj", 60, 9))])
    builder.add_cash([DEPOSIT, _Cash("2021-03-03", "Osto Aurora Metsä Oyj", "-208", "ca"), _Cash("2021-04-20", "Aurora Metsä 1234567890", "9", "ct"), _Cash("2021-04-30", "Palvelumaksut 04/2021", "-3.5", "fee")], opening=OPENING)


@scenario("b52_a13_broken")
def _b52_a13_broken(builder: _Builder) -> None:
    """An A13 set like "b52_a13", without k1 and n. The custody export starts on 03-08 with the Aurora purchase x, which
    settles on 03-10, the statement's first row. A fee booked on 04-15 is missing from the statement, so the running
    balance breaks (on 04-20) and the checkpoint's cash becomes a verification."""
    builder.add_custody([("x", _trade("2021-03-08", "Aurora Metsä Oyj", 10, 20, -208)), ("t", _tuotto("2021-04-20", "Aurora Metsä Oyj", 60, 9))])
    builder.add_cash(
        [
            _Cash("2021-03-10", "Osto Aurora Metsä Oyj", "-208", "cx"),
            _Cash("2021-04-15", "Palvelumaksut 03/2021", "-40", hidden=True),
            _Cash("2021-04-20", "Aurora Metsä 1234567890", "9", "ct"),
            _Cash("2021-04-30", "Palvelumaksut 04/2021", "-3.5", "fee"),
        ],
        opening=OPENING,
    )


@scenario("b52_a13_settled_before")
def _b52_a13_settled_before(builder: _Builder) -> None:
    """A13 with a trade settled before the cash statement starts, and a proof of its title. The custody export starts on
    03-01 with the Kaamos purchase k1 (2 shares), settled on 03-03; the cash statement starts on 03-10 with a fee. k1 is
    left out (``outside_cash_coverage``): its cash is in the statement's first balance and its shares belong to the opening.
    The Tuotto of 04-20 states those 2 Kaamos shares."""
    builder.add_custody([("k1", _trade("2021-03-01", "Kaamos Robotics AB", 2, 30, -68)), ("t", _tuotto("2021-04-20", "Kaamos Robotics AB", 2, 3))])  # k1: value 03-03
    builder.add_cash([_Cash("2021-03-10", "Palvelumaksut 02/2021", "-3.5", "fee1"), _Cash("2021-04-20", "Kaamos Robotics 1234567890", "3", "ct"), _Cash("2021-04-30", "Palvelumaksut 04/2021", "-3.5", "fee2")], opening=OPENING)


@scenario("b52_a13_sell")
def _b52_a13_sell(builder: _Builder) -> None:
    """A13 with a sale straddling the start of the cash statement, for a title with no exact proof. The custody export
    starts on 03-08 with the Saimaa sale s (5 shares), which settles on 03-10, the statement's first row, and ends with the
    Kaamos purchase k of 03-31. Saimaa has no Tuotto and no demerger, so only E3 can tell the opening that at least the 5
    shares sold were there."""
    builder.add_custody([("s", _trade("2021-03-08", "Saimaa Energia Oyj", -5, 20, 92, kind="Päivän kurssi")), ("k", _kaamos("2021-03-31"))])  # s: value 03-10; k: value 04-02
    builder.add_cash([_Cash("2021-03-10", "Myynti Saimaa Energia Oyj", "92", "cs"), _Cash("2021-04-02", "Osto Kaamos Robotics AB", "-38", "ck"), _Cash("2021-04-30", "Palvelumaksut 04/2021", "-3.5", "fee")], opening=OPENING)


@scenario("b52_events")
def _b52_events(builder: _Builder) -> None:
    """A Tuotto and a demerger whose two dates differ. In the bank's exports they are equal; here they differ only to tell
    the columns apart. The Tuotto is traded on 03-10 with value 03-12; the demerger lines are traded on 03-15 with value
    03-17."""
    tuotto = _tuotto("2021-03-10", "Aurora Metsä Oyj", 60, 9)
    tuotto[1] = _d("2021-03-12")
    old_line = _demerger("2021-03-15", "Lumi Holding Oyj", -100, old=True)
    new_line = _demerger("2021-03-15", "Lumi Uusi Oyj", 100, old=False)
    old_line[1] = new_line[1] = _d("2021-03-17")
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("t", tuotto), ("v", old_line), ("u", new_line), ("k2", _kaamos("2021-03-31"))])
    builder.add_cash(_proof_cash(_Cash("2021-03-12", "Aurora Metsä 1234567890", "9", "ct"), last="2021-04-02"), opening=OPENING)


def _in_flight(records: List[Dict[str, str]], day: str) -> Tuple[Decimal, Dict[str, Decimal]]:
    """What is in flight at the end of ``day``, read from the combined table: the cash and the quantity per title of the
    pairs that are a purchase or a sale (never a ``Tuotto``), traded on or before ``day`` (``custody:Kauppapäivä``) and
    settled after it (``cash:Pvm``). Only a pair is imported, so only a pair can be in flight."""
    cash, quantities = Decimal(0), defaultdict(Decimal)
    for record in records:
        if record["lf_row_kind"] != "pair" or record["custody:Toimeksiantotyyppi"] == "Tuotto":
            continue
        if _from_fi_date(record["custody:Kauppapäivä"]) <= _d(day) < _from_fi_date(record["cash:Pvm"]):
            cash += _number(record["cash:Määrä"])
            quantities[record["custody:Sijoituskohde"]] += _number(record["custody:Määrä"])
    return cash, dict(quantities)


async def _first_import_gap_fix(output: BRIMParseOutput) -> Tuple[Any, date, List[Any], Dict[str, int]]:
    """The gap-fix of a first import, end to end, run as the wizard runs it, on a private in-memory database (never the
    lane's).

    ``apply_history`` gives the checkpoints, the verifications and H0. On a broker without a Danske history, H0 is the day
    after the opening. The selection is every transaction dated on or after H0: the wizard hides the earlier ones, because
    the opening already brings them. Every fake asset is resolved to a real id, as the user does in the wizard. Returns
    the gap-fix response, H0, the selection and ``{title: real asset id}``.
    """
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            checkpoints, verifications, history_start = await brim_report_sets.apply_history(session, broker_id=BROKER_ID, plugin=_danske(), output=output)
            assert history_start is not None, "premise: a first import has an H0, the day after its opening"
            real = {fake: REAL_ASSET_BASE + index for index, fake in enumerate(sorted(output.extracted_assets))}
            selection = [tx.model_copy(update={"asset_id": real.get(tx.asset_id, tx.asset_id)}) for tx in output.transactions if tx.date >= history_start]
            resolved = [checkpoint.model_copy(update={"positions": [position.model_copy(update={"asset_id": real[position.asset_id]}) for position in checkpoint.positions]}) for checkpoint in checkpoints]
            request = BRIMGapFixRequest(broker_id=BROKER_ID, plugin_code=PLUGIN_CODE, checkpoints=resolved, verifications=verifications, selection=selection)
            response = await compute_gap_fix(session, request)
    finally:
        await engine.dispose()
    names = _names(output)
    return response, history_start, selection, {names[fake]: real_id for fake, real_id in real.items()}


def _gap_fix_at(response: Any, as_of: str) -> Any:
    """The gap-fix result of the checkpoint dated ``as_of``: exactly one."""
    found = [result for result in response.checkpoints if result.as_of == _d(as_of)]
    assert len(found) == 1, f"one gap-fix result expected at {as_of}, got {[result.as_of.isoformat() for result in response.checkpoints]}"
    return found[0]


def _gap_fix_verified(response: Any, as_of: str) -> Any:
    """The gap-fix result of the verification dated ``as_of``: exactly one."""
    found = [result for result in response.verifications if result.as_of == _d(as_of)]
    assert len(found) == 1, f"one verification result expected at {as_of}, got {[result.as_of.isoformat() for result in response.verifications]}"
    return found[0]


def _gap_fix_cash(result: Any) -> Dict[str, Tuple[Decimal, Decimal, Decimal]]:
    """``{currency: (bank, librefolio, difference)}`` of a gap-fix checkpoint or verification result."""
    return {row.currency: (row.bank, row.librefolio, row.difference) for row in result.cash}


def _gap_fix_positions(result: Any, titles: Dict[str, int]) -> Dict[str, Tuple[str, Decimal, Decimal, Decimal]]:
    """``{title: (exactness, bank, librefolio, difference)}`` of a gap-fix checkpoint result."""
    by_id = {real_id: title for title, real_id in titles.items()}
    return {by_id[row.asset_id]: (row.exactness, row.bank, row.librefolio, row.difference) for row in result.positions}


def _gap_fix_proposals(result: Any, titles: Dict[str, int]) -> List[Tuple[str, Optional[Decimal], Optional[str], Decimal]]:
    """``(type, cash, title, quantity)`` of the corrections a gap-fix checkpoint result proposes, sorted by type and title."""
    by_id = {real_id: title for title, real_id in titles.items()}
    proposals = [(item.type.value, None if item.cash is None else item.cash.amount, by_id.get(item.asset_id), item.quantity) for item in result.proposals]
    return sorted(proposals, key=lambda item: (item[0], item[2] or ""))


def _ledger_quantity(response: Any, selection: Sequence[Any], asset_id: int, day: date) -> Decimal:
    """The quantity of an asset LibreFolio holds at the end of ``day`` once the selection and every proposal are saved."""
    rows = [*selection, *(proposal for result in response.checkpoints for proposal in result.proposals)]
    return sum((row.quantity for row in rows if row.asset_id == asset_id and row.date <= day and row.quantity is not None), Decimal(0))


def _ledger_cash(response: Any, selection: Sequence[Any], day: date) -> Decimal:
    """The cash (EUR) LibreFolio holds at the end of ``day`` once the selection and every proposal are saved."""
    rows = [*selection, *(proposal for result in response.checkpoints for proposal in result.proposals)]
    return sum((row.cash.amount for row in rows if row.date <= day and row.cash is not None), Decimal(0))


def _cell_day(value: Any) -> Optional[date]:
    """A custody date cell as a date: text ``dd.mm.yyyy`` or a date cell; anything else is None."""
    if isinstance(value, datetime):
        return value.date()
    return _fi_date_or_none(value) if isinstance(value, str) else None


def _member_starts(members: Dict[str, List[Path]]) -> Tuple[Optional[date], Optional[date]]:
    """``(custody start, first cash day)`` of a set, read from its files as written, not through the plugin.

    The custody start is the first valid ``Kauppapäivä`` of the custody exports. The first cash day is the first day of a
    posted row of the cash statements (``Toteutunut``, no «Varaus», a valid date and amount), as the running balance reads
    them."""
    trade_days: List[date] = []
    for path in members.get("custody", []):
        header, *rows = [list(row) for row in openpyxl.load_workbook(path).active.iter_rows(values_only=True)]
        column = header.index("Kauppapäivä")
        trade_days += [day for day in (_cell_day(row[column]) for row in rows) if day is not None]
    cash_days: List[date] = []
    for path in members.get("cash", []):
        for line in path.read_bytes().decode("latin-1").split("\n")[1:]:
            cells = line.split(";")
            if len(cells) != len(CASH_HEADER) or cells[4] != "Toteutunut" or cells[1].startswith("Varaus"):
                continue
            try:
                day, _amount = _from_fi_date(cells[0]), _number(cells[2])
            except (ValueError, InvalidOperation):
                continue
            cash_days.append(day)
    return (min(trade_days) if trade_days else None, min(cash_days) if cash_days else None)


def _a13_shaped(members: Dict[str, List[Path]]) -> bool:
    """A13: the set's cash statement starts after its custody export."""
    custody_start, first_cash_day = _member_starts(members)
    return custody_start is not None and first_cash_day is not None and first_cash_day > custody_start


class TestOperationDateTruths:
    """Lot B-52, the condition of the lot: the truths in operation-date terms.

    A pair is recorded on its trade date T, while the bank moves its cash on the value date V. So every truth at a day D
    adds what is in flight at D: the trades imported as pairs with T <= D < V (``_in_flight`` reads them from the combined
    table).
    - The cash truth of a checkpoint adds their cash (a purchase negative, a sale positive).
    - A truth position adds their quantity, for its title.
    - A verification adds their cash.
    Rows that are not imported (excluded, summarized) never count. Pairing, zones, ``not_yet_settled`` and
    ``deferred_rows`` stay on the value date.

    The A13 sets follow the developer's decision of 20/10/2026. When the cash statement starts after the custody export, the
    set opens like any other, on the eve of the custody export, where nothing is in flight. H0 is the custody export's
    first day.
    - The opening's cash is the statement's first balance, the balance before its first row.
    - A trade straddling the statement's start is imported on its trade date, after the opening, and the opening's
      positions subtract it.
    - A trade settled before the statement stays left out (``outside_cash_coverage``): its cash is in that balance, its
      shares belong to the opening.

    Each straddling scenario is pinned twice:
    - on the plugin's own output: the truth lines of the combined table, and the checkpoints and verifications of the parse;
    - end to end: the gap-fix of a first import, run as the wizard runs it (``_first_import_gap_fix``). It finds nothing to
      correct beyond the opening itself, explains every cent of the opening, and the verification is ok.
    Both are red today, on the operation-date value, after premises that hold today. The end-to-end harness is consistent
    today too, in value-date terms: ``test_guard_the_normal_opening_has_nothing_in_flight`` shows it on a scenario B-52 does
    not change.
    """

    # --- 1. a trade straddling the final verification ---

    def test_a_trade_straddling_the_final_verification_is_in_its_cash(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red today: the verification is the bank's balance alone, 1292.00.

        Scenario "b52_verification". The cash statement runs beyond the last custody trade (03-31), so the final
        verification is on 03-31. The sale s (+92) and the purchase k (−38) are both traded on 03-31 and settled on 04-02,
        so they are in flight then. The verification is 1292.00 + 92 − 38 = 1346.00, on the combined table and in the
        parse. The trades are recorded on their trade dates (s and k on 03-31, the first purchase on 03-01). So the
        opening (1500.00) plus the transactions dated after it, up to 03-31, gives exactly the verification."""
        builder, table, _path, output = _scenario_parse("b52_verification", tmp_path_factory)
        records = _records(table)

        assert [builder.row(records, key)["lf_row_kind"] for key in ("a", "s", "k")] == ["pair"] * 3, "premise: the three trades pair"
        assert [(row["lf_checkpoint"], row["lf_value"]) for row in _truth(records, "truth_cash")] == [("2021-02-28", "1500.00")], "premise: the normal opening, nothing in flight"
        assert [row["lf_checkpoint"] for row in _truth(records, "verification")] == ["2021-03-31"], "premise: the verification is on the last custody day"
        assert _in_flight(records, "2021-03-31") == (Decimal("54"), {"Aurora Metsä Oyj": Decimal("-4"), "Kaamos Robotics AB": Decimal("1")}), "premise: s and k are in flight on 03-31"

        assert [(row["lf_checkpoint"], row["lf_value"], row["lf_currency"]) for row in _truth(records, "verification")] == [("2021-03-31", "1346.00", "EUR")], "B-52: the verification adds the trades in flight"
        assert [(item.as_of, _money(item.cash)) for item in output.verifications] == [(_d("2021-03-31"), {"EUR": Decimal("1346.00")})]
        assert [(tx[0], tx[1], tx[4]) for tx in _transactions(output) if tx[0] in ("BUY", "SELL")] == [
            ("BUY", _d("2021-03-01"), "Aurora Metsä Oyj"),
            ("SELL", _d("2021-03-31"), "Aurora Metsä Oyj"),
            ("BUY", _d("2021-03-31"), "Kaamos Robotics AB"),
        ], "B-52: a trade is recorded on its trade date"
        ledger = Decimal("1500.00") + sum((tx.cash.amount for tx in output.transactions if tx.cash is not None and _d("2021-02-28") < tx.date <= _d("2021-03-31")), Decimal(0))
        assert ledger == Decimal("1346.00"), "the opening plus the transactions dated up to the verification day is the verification"

    @pytest.mark.asyncio
    async def test_gap_fix_of_the_final_verification_finds_nothing_to_correct(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red today: the gap-fix finds 1292.00 on both sides, which is consistent, but in value-date terms.

        Scenario "b52_verification", through the gap-fix of a first import (H0 = 03-01). The opening proposes its cash,
        1500.00, and nothing else. Every cent is explained: the deposit it absorbs (500) and the balance the statement
        starts from (1000). The verification on 03-31 is ok, with 1346.00 on both sides: the bank's balance plus the two
        trades in flight, and LibreFolio's ledger, where they are recorded on 03-31."""
        _builder, _table, _path, output = _scenario_parse("b52_verification", tmp_path_factory)

        response, history_start, _selection, titles = await _first_import_gap_fix(output)

        assert history_start == _d("2021-03-01"), "premise: H0 is the day after the opening"
        opening = _gap_fix_at(response, "2021-02-28")
        assert (_gap_fix_proposals(opening, titles), opening.positions, opening.explanation.unexplained_cash) == ([("DEPOSIT", Decimal("1500.00"), None, Decimal(0))], [], []), "premise: the opening proposes its cash, all explained"

        verified = _gap_fix_verified(response, "2021-03-31")
        assert (verified.ok, _gap_fix_cash(verified)) == (True, {"EUR": (Decimal("1346.00"), Decimal("1346.00"), Decimal(0))}), "B-52: ok in operation-date terms"

    # --- 2. an A13 set: the opening on the eve of the custody export (the developer, 20/10/2026) ---

    def test_an_a13_set_opens_on_the_eve_of_the_custody_export(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red today: the opening is on the eve of the statement, 03-09, and x is recorded on its value date, 03-10.

        Scenario "b52_a13". The custody export starts on 03-01, the cash statement on 03-10 (A13). The developer decided
        (20/10/2026) that the opening goes back to the eve of the custody export, 02-28, as for a normal set. Nothing is in
        flight then: every trade comes after it.
        - The opening's cash is the statement's first balance, the balance before its first row: 1000.00. It absorbs no
          row.
        - Aurora's position, proven by the Tuotto (exact:E1), is the 60 shares it holds minus the moves imported between
          the opening and the Tuotto, by value date: 60 − 10 = 50.
        - The purchase x, traded on 03-08 and settled on 03-10, is imported as a BUY on 03-08 (10 shares). Project 66, P2c:
          10 × 20 explains the 208 paid, so it is booked at −200 with a linked FEE of −8 on the same day. It is not left
          out, and it brings no notice but the split one.
        - k1, settled on 03-03 before the statement, stays left out (``outside_cash_coverage``). It is settled after the
          opening, so its zone is the window. n stays left out too (``no_counterpart``).
        - The verification (04-20) has nothing in flight and stays 801.00."""
        builder, table, _path, output = _scenario_parse("b52_a13", tmp_path_factory)
        records = _records(table)

        assert _member_starts(builder.members()) == (_d("2021-03-01"), _d("2021-03-10")), "premise: A13, the cash statement starts after the custody export"
        assert (builder.row(records, "x")["lf_row_kind"], builder.row(records, "x") is builder.row(records, "cx")) == ("pair", True), "premise: x pairs with the statement's first row"
        assert [(builder.row(records, key)["lf_row_kind"], builder.row(records, key)["lf_reason"]) for key in ("k1", "n")] == [("excluded", "outside_cash_coverage"), ("excluded", "no_counterpart")], "premise: k1 and n are left out"
        assert _in_flight(records, "2021-02-28") == (Decimal(0), {}), "premise: nothing is in flight on the eve of the custody export"
        assert sorted(_codes(output.warnings)) == sorted([SPLIT_NOTICE, "excluded_no_counterpart", "excluded_outside_cash_coverage"]), "x is imported, its commission split: no other new notice"
        assert [(row["lf_checkpoint"], row["lf_value"]) for row in _truth(records, "verification")] == [("2021-04-20", "801.00")]

        assert [(row["lf_checkpoint"], row["lf_value"], row["lf_zone"]) for row in _truth(records, "truth_cash")] == [("2021-02-28", "1000.00", "before")], "A13 (20/10): the opening on the eve of the custody export, with the statement's first balance"
        assert [(row["custody:Sijoituskohde"], row["lf_value"], row["lf_proof"]) for row in _truth(records, "truth_position", "2021-02-28")] == [("Aurora Metsä Oyj", "50", "exact:E1")], "A13 (20/10): Aurora's position at the opening, x subtracted"
        opening = _checkpoint(output, "2021-02-28")
        assert (opening.kind, _money(opening.cash), _positions(output, opening), opening.absorbed.count, _money(opening.absorbed.opening_cash)) == ("opening", {"EUR": Decimal("1000.00")}, {"Aurora Metsä Oyj": (Decimal("50"), "exact")}, 0, {"EUR": Decimal("1000.00")})
        assert builder.row(records, "k1")["lf_zone"] == "window", "k1 is settled after the opening"
        trade_cash, charges = _owed_split(builder.row(records, "x"))
        assert [tx[:5] for tx in _transactions(output) if tx[0] in ("BUY", "SELL") or (tx[0] == "FEE" and tx[4] is not None)] == [
            ("BUY", _d("2021-03-08"), Decimal("10"), trade_cash, "Aurora Metsä Oyj"),
            ("FEE", _d("2021-03-08"), Decimal("0"), -charges, "Aurora Metsä Oyj"),
        ], "B-52: x is imported on its trade date; P2c: at 10 × 20, its commission a FEE of the same day"

    @pytest.mark.asyncio
    async def test_gap_fix_of_the_a13_opening_finds_nothing_to_correct(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red today: the opening is on 03-09, H0 on 03-10, and x reaches LibreFolio as a BUY dated 03-10.

        Scenario "b52_a13", through the gap-fix of a first import. The opening is on 02-28, so H0 is 03-01, the custody
        export's first day: the wizard shows every custody trade.
        - The opening proposes the statement's first balance (1000.00) and Aurora's 50 shares. Nothing is unexplained.
        - x is selected as a BUY on 03-08 (10 shares) at 10 × 20, −200, with its FEE of −8 on the same day (project 66,
          P2c): together the 208 paid. After it LibreFolio holds 792.00 and 60 Aurora shares, as the bank says: the balance
          after x, and the shares the Tuotto of 04-20 states.
        - The verification on 04-20 is ok (801.00).
        The amounts are the ones of today; the dates are not."""
        _builder, _table, _path, output = _scenario_parse("b52_a13", tmp_path_factory)

        response, history_start, selection, titles = await _first_import_gap_fix(output)

        assert [result.kind for result in response.checkpoints] == ["opening"], "premise: one checkpoint, the opening"
        opening = response.checkpoints[0]
        assert opening.explanation.unexplained_cash == [], "premise: the opening is explained to the cent"
        verified = _gap_fix_verified(response, "2021-04-20")
        assert (verified.ok, _gap_fix_cash(verified)) == (True, {"EUR": (Decimal("801.00"), Decimal("801.00"), Decimal(0))}), "premise: the verification is ok"
        assert _ledger_quantity(response, selection, titles["Aurora Metsä Oyj"], _d("2021-04-20")) == Decimal("60"), "premise: LibreFolio holds the 60 shares the Tuotto states"
        assert _gap_fix_proposals(opening, titles) == [("ADJUSTMENT", None, "Aurora Metsä Oyj", Decimal("50")), ("DEPOSIT", Decimal("1000.00"), None, Decimal(0))], "the opening proposes the statement's first balance and Aurora 50"
        assert _gap_fix_positions(opening, titles) == {"Aurora Metsä Oyj": ("exact", Decimal("50"), Decimal(0), Decimal("50"))}

        assert (opening.as_of, history_start) == (_d("2021-02-28"), _d("2021-03-01")), "A13 (20/10): the opening on the eve of the custody export, H0 its first day"
        assert [(tx.type.value, tx.date, tx.quantity, tx.cash.amount) for tx in selection if tx.type.value == "BUY" or (tx.type.value == "FEE" and tx.asset_id is not None)] == [
            ("BUY", _d("2021-03-08"), Decimal("10"), Decimal("-200")),
            ("FEE", _d("2021-03-08"), Decimal("0"), Decimal("-8")),
        ], "B-52: x is selected on its trade date; P2c: at 10 × 20, with its commission"
        after_x = (_ledger_cash(response, selection, _d("2021-03-08")), _ledger_quantity(response, selection, titles["Aurora Metsä Oyj"], _d("2021-03-08")))
        assert after_x == (Decimal("792.00"), Decimal("60")), "after x LibreFolio holds what the bank says: 792.00 and 60 Aurora shares"

    # --- 2b. A13: the rows around the statement's start (guards, green today and after) ---

    @pytest.mark.asyncio
    async def test_guard_a_trade_settled_before_the_statement_leaves_its_title_proven(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Guard, green today and after the A13 decision (20/10/2026).

        Scenario "b52_a13_settled_before". k1 is traded on 03-01 and settled on 03-03, before the cash statement (03-10…).
        - It stays left out (``outside_cash_coverage``), with the same warning as today.
        - Its cash is in the statement's first balance, the opening's 1000.00.
        - Its 2 shares belong to the opening, so it never discards the proof of its title. The Tuotto of 04-20 proves 2
          Kaamos shares at the opening (exact:E1).
        - Through the gap-fix the opening brings them: LibreFolio then holds the 2 shares the Tuotto states.
        Read whatever the opening's date. Today it is the eve of the statement (03-09), and k1 lies before it. After the
        decision it is the eve of the custody export (02-28), and k1 lies between the opening and the proof."""
        builder, table, _path, output = _scenario_parse("b52_a13_settled_before", tmp_path_factory)
        records = _records(table)
        early = builder.row(records, "k1")
        opening_days = [row["lf_checkpoint"] for row in _truth(records, "truth_cash")]
        assert len(opening_days) == 1, f"premise: one checkpoint, the opening: {opening_days}"
        opening_day = opening_days[0]

        assert _member_starts(builder.members()) == (_d("2021-03-01"), _d("2021-03-10")), "premise: A13, the cash statement starts after the custody export"
        assert builder.row(records, "t") is builder.row(records, "ct"), "premise: the Tuotto pairs"
        assert (early["lf_row_kind"], early["lf_reason"]) == ("excluded", "outside_cash_coverage")
        left_out = _one_notice(output, "excluded_outside_cash_coverage")
        assert (left_out.severity, left_out.context, sorted(_shown(left_out))) == ("warning", {"count": 1, "reason": "outside_cash_coverage"}, [_line_of(records, early)]), "the same warning as today, showing k1"

        assert [(row["lf_value"], row["lf_zone"]) for row in _truth(records, "truth_cash")] == [("1000.00", "before")], "the opening's cash is the statement's first balance, k1's cash inside it"
        assert [(row["custody:Sijoituskohde"], row["lf_value"], row["lf_proof"]) for row in _truth(records, "truth_position", opening_day)] == [("Kaamos Robotics AB", "2", "exact:E1")], "k1 does not discard the proof of its title"
        assert _positions(output, _checkpoint(output, opening_day)) == {"Kaamos Robotics AB": (Decimal("2"), "exact")}
        assert "proof_discarded" not in _codes(output.warnings)

        response, _history_start, selection, titles = await _first_import_gap_fix(output)

        assert _gap_fix_proposals(_gap_fix_at(response, opening_day), titles) == [("ADJUSTMENT", None, "Kaamos Robotics AB", Decimal("2")), ("DEPOSIT", Decimal("1000.00"), None, Decimal(0))]
        assert _ledger_quantity(response, selection, titles["Kaamos Robotics AB"], _d("2021-04-20")) == Decimal("2"), "LibreFolio holds the 2 shares the Tuotto states"

    @pytest.mark.asyncio
    async def test_guard_a_sale_straddling_the_statement_start_leaves_no_negative_position(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Guard, green today and after the A13 decision (20/10/2026).

        Scenario "b52_a13_sell". The Saimaa sale s (5 shares) is traded on 03-08 and settled on 03-10, the cash statement's
        first row, and it is imported. Saimaa has no exact proof (no Tuotto, no demerger).
        - The E3 fallback tells the opening that at least the 5 shares sold were there: Saimaa's position at the opening is
          at_least:E3, never below 5, and never missing.
        - Through the gap-fix the opening brings them, so LibreFolio never holds a negative quantity of Saimaa, the day of
          the sale included.
        Read whatever the opening's date: today 03-09, after the decision 03-07."""
        builder, table, _path, output = _scenario_parse("b52_a13_sell", tmp_path_factory)
        records = _records(table)
        sale = builder.row(records, "s")
        sold = -_number(sale["custody:Määrä"])
        opening_days = [row["lf_checkpoint"] for row in _truth(records, "truth_cash")]
        assert len(opening_days) == 1, f"premise: one checkpoint, the opening: {opening_days}"
        opening_day = opening_days[0]

        assert _member_starts(builder.members()) == (_d("2021-03-08"), _d("2021-03-10")), "premise: A13, the cash statement starts after the custody export"
        assert (sale["lf_row_kind"], sale is builder.row(records, "cs"), sold) == ("pair", True, Decimal("5")), "premise: the sale of 5 pairs with the statement's first row"
        assert [row["lf_proof"] for row in _positions_by_title(records, "Saimaa Energia Oyj") if not row["lf_proof"].startswith("at_least:")] == [], "premise: Saimaa has no exact proof"

        assert [(row["lf_checkpoint"], row["lf_proof"]) for row in _positions_by_title(records, "Saimaa Energia Oyj")] == [(opening_day, "at_least:E3")], "the E3 fallback states Saimaa at the opening"
        assert Decimal(_positions_by_title(records, "Saimaa Energia Oyj")[0]["lf_value"]) >= sold
        quantity, exactness = _positions(output, _checkpoint(output, opening_day))["Saimaa Energia Oyj"]
        assert (exactness, quantity >= sold) == ("at_least", True), f"the opening holds at least the {sold} shares sold, not {quantity}"

        response, _history_start, selection, titles = await _first_import_gap_fix(output)
        saimaa = titles["Saimaa Energia Oyj"]
        proposals = [proposal for result in response.checkpoints for proposal in result.proposals]

        # Project 66, P2c: 5 × 20 explains the 92 received, so the sale comes with its FEE (no shares).
        assert [(tx.type.value, tx.quantity) for tx in selection if tx.asset_id == saimaa] == [("SELL", -sold), ("FEE", Decimal(0))], "premise: the sale is selected"
        brought = [item for item in _gap_fix_proposals(_gap_fix_at(response, opening_day), titles) if item[2] == "Saimaa Energia Oyj"]
        assert [(item[0], item[3] >= sold) for item in brought] == [("ADJUSTMENT", True)], f"the opening brings at least the {sold} shares sold: {brought}"
        holdings = {day.isoformat(): _ledger_quantity(response, selection, saimaa, day) for day in sorted({row.date for row in [*selection, *proposals] if row.asset_id == saimaa})}
        assert min(holdings.values()) >= 0, f"LibreFolio holds a negative quantity of Saimaa: {holdings}"
        assert _ledger_quantity(response, selection, saimaa, _d("2021-03-10")) >= 0, "after the sale (recorded on or before its value date, 03-10)"

    # --- 3. a trade straddling a gap checkpoint ---

    def test_a_trade_straddling_a_gap_checkpoint_is_in_its_truths(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red today: the gap checkpoint's cash is 1224.00 and Kaamos's position 2, in value-date terms.

        Scenario "b52_gap". The two custody exports end on 03-31 and start on 04-02, closer than the settlement lag (5
        business days). A Saimaa purchase and a Saimaa sale on 04-01 prove the gap, so C2 = 04-01. The Kaamos purchase k,
        traded on 03-31 and settled on 04-02, is in flight at C2.
        - C2's cash is 1224.00 − 38 = 1186.00.
        - Kaamos's position, proven by the Tuotto of 05-03 (exact:E1), is 2 + 1 = 3, the shares the Tuotto holds.
        - k is recorded on 03-31.
        - Nothing is in flight at the opening (1500.00) or at the verification (05-03, 1129.50)."""
        builder, table, _path, output = _scenario_parse("b52_gap", tmp_path_factory)
        records = _records(table)

        assert table.summary["gaps"] == [{"start": "2021-04-01", "end": "2021-04-01"}], "premise: a proven gap of one day"
        assert [(builder.row(records, key)["lf_row_kind"], builder.row(records, key)["lf_checkpoint"]) for key in ("gb", "gs")] == [("summarized", "2021-04-01")] * 2, "premise: the gap's trades are summarized into C2"
        assert builder.row(records, "k") is builder.row(records, "ck"), "premise: k pairs"
        assert _in_flight(records, "2021-04-01") == (Decimal("-38"), {"Kaamos Robotics AB": Decimal("1")}), "premise: k alone is in flight at C2"

        assert [(row["lf_checkpoint"], row["lf_value"], row["lf_zone"]) for row in _truth(records, "truth_cash")] == [("2021-02-28", "1500.00", "before"), ("2021-04-01", "1186.00", "gap")], "B-52: C2's cash adds k"
        assert [(row["custody:Sijoituskohde"], row["lf_value"], row["lf_proof"]) for row in _truth(records, "truth_position", "2021-04-01")] == [("Kaamos Robotics AB", "3", "exact:E1")], "B-52: Kaamos's position adds k"
        gap = _checkpoint(output, "2021-04-01")
        assert (gap.kind, _money(gap.cash), _positions(output, gap)) == ("gap", {"EUR": Decimal("1186.00")}, {"Kaamos Robotics AB": (Decimal("3"), "exact")})
        assert [(tx[1], tx[2]) for tx in _transactions(output) if tx[0] == "BUY" and tx[4] == "Kaamos Robotics AB"] == [(_d("2021-03-10"), Decimal("2")), (_d("2021-03-31"), Decimal("1"))], "B-52: k0 and k on their trade dates"
        assert [(row["lf_checkpoint"], row["lf_value"]) for row in _truth(records, "verification")] == [("2021-05-03", "1129.50")]

    @pytest.mark.asyncio
    async def test_gap_fix_of_the_gap_checkpoint_finds_nothing_to_correct(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red today: at C2 the gap-fix finds 1224.00 and 2 Kaamos on both sides, which is consistent, but in value-date
        terms.

        Scenario "b52_gap", through the gap-fix of a first import (H0 = 03-01). The opening proposes its 1500.00, all
        explained. At C2 (04-01) nothing is proposed and nothing is unexplained, because the gap's two summarized trades
        cancel out. Both sides say 1186.00 and 3 Kaamos: on the bank's side k is in flight, on LibreFolio's side k is
        recorded on 03-31. The verification on 05-03 is ok (1129.50)."""
        _builder, _table, _path, output = _scenario_parse("b52_gap", tmp_path_factory)

        response, history_start, _selection, titles = await _first_import_gap_fix(output)

        assert history_start == _d("2021-03-01"), "premise: H0 is the day after the opening"
        opening, gap = _gap_fix_at(response, "2021-02-28"), _gap_fix_at(response, "2021-04-01")
        assert (_gap_fix_proposals(opening, titles), opening.explanation.unexplained_cash) == ([("DEPOSIT", Decimal("1500.00"), None, Decimal(0))], []), "premise: the opening proposes its cash, all explained"
        assert (gap.proposals, gap.explanation.unexplained_cash) == ([], []), "premise: nothing to correct at the gap checkpoint"
        verified = _gap_fix_verified(response, "2021-05-03")
        assert (verified.ok, _gap_fix_cash(verified)) == (True, {"EUR": (Decimal("1129.50"), Decimal("1129.50"), Decimal(0))}), "premise: the verification is ok"

        assert _gap_fix_cash(gap) == {"EUR": (Decimal("1186.00"), Decimal("1186.00"), Decimal(0))}, "B-52: C2 in operation-date terms"
        assert _gap_fix_positions(gap, titles) == {"Kaamos Robotics AB": ("exact", Decimal("3"), Decimal("3"), Decimal(0))}

    # --- 4. the normal opening (guard) ---

    @pytest.mark.asyncio
    async def test_guard_the_normal_opening_has_nothing_in_flight(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Guard, green today and after B-52.

        Scenario "b52_opening". The cash statement starts before the custody export, so every trade is after C1 = 02-28
        and nothing is in flight there. The segment ends with a Tuotto, so nothing is in flight at the verification
        (04-20) either. The truths stay as they are: 1500.00 and 50 Aurora at the opening, 1301.00 at the verification.
        The gap-fix of the first import proposes the opening and nothing else, all explained, and the verification is
        ok. So the end-to-end harness of this class is consistent today."""
        _builder, table, _path, output = _scenario_parse("b52_opening", tmp_path_factory)
        records = _records(table)

        assert (_in_flight(records, "2021-02-28"), _in_flight(records, "2021-04-20")) == ((Decimal(0), {}), (Decimal(0), {})), "premise: nothing in flight"
        assert [(row["lf_checkpoint"], row["lf_value"]) for row in _truth(records, "truth_cash")] == [("2021-02-28", "1500.00")]
        assert [(row["custody:Sijoituskohde"], row["lf_value"], row["lf_proof"]) for row in _truth(records, "truth_position")] == [("Aurora Metsä Oyj", "50", "exact:E1")]
        assert [(row["lf_checkpoint"], row["lf_value"]) for row in _truth(records, "verification")] == [("2021-04-20", "1301.00")]

        response, history_start, _selection, titles = await _first_import_gap_fix(output)

        assert history_start == _d("2021-03-01")
        opening = _gap_fix_at(response, "2021-02-28")
        assert _gap_fix_proposals(opening, titles) == [("ADJUSTMENT", None, "Aurora Metsä Oyj", Decimal("50")), ("DEPOSIT", Decimal("1500.00"), None, Decimal(0))]
        assert opening.explanation.unexplained_cash == []
        verified = _gap_fix_verified(response, "2021-04-20")
        assert (verified.ok, _gap_fix_cash(verified)) == (True, {"EUR": (Decimal("1301.00"), Decimal("1301.00"), Decimal(0))})

    # --- what never counts, and the other truths at a day ---

    def test_guard_a_trade_left_out_is_never_in_flight(self) -> None:
        """Guard, green today and after B-52. In the gap sample, the last Saimaa purchase is traded on 2021-02-26, the day of
        the final verification, and settles on 03-02, after the statement's last row. It is left out
        (``not_yet_settled``), so it is not in flight, and the verification stays the bank's balance, 4363.42."""
        records = _records(_sample_table("gap"))
        straddling = _data_row(records, "custody", 2, 5)

        assert (straddling["lf_row_kind"], straddling["lf_reason"], straddling["custody:Kauppapäivä"], straddling["custody:Arvopäivä"]) == ("excluded", "not_yet_settled", "26.02.2021", "02.03.2021"), "premise: a trade straddling the verification, left out"
        assert _in_flight(records, "2021-02-26") == (Decimal(0), {})
        assert [(row["lf_checkpoint"], row["lf_value"]) for row in _truth(records, "verification")] == [("2021-02-26", "4363.42")]

    def test_a_broken_chain_verification_at_the_a13_opening_is_the_statements_first_balance(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red today: the checkpoint and its verification are on the eve of the statement, 03-09.

        Scenario "b52_a13_broken". It is an A13 set whose custody export starts on 03-08 with the purchase x (settled on
        03-10, the statement's first row). A fee missing from the statement breaks the running balance. With the chain
        broken, the plugin states no cash at the opening, and a verification there instead.
        - The opening is on the eve of the custody export (A13, 20/10/2026): 03-07.
        - Nothing is in flight then, so the opening's verification is the statement's first balance, 1000.00.
        - The final verification (04-20) is the bank's balance after the break, 761.00, with nothing in flight."""
        builder, table, _path, output = _scenario_parse("b52_a13_broken", tmp_path_factory)
        records = _records(table)

        assert _member_starts(builder.members()) == (_d("2021-03-08"), _d("2021-03-10")), "premise: A13, the cash statement starts after the custody export"
        assert (builder.row(records, "x")["lf_row_kind"], builder.row(records, "x") is builder.row(records, "cx")) == ("pair", True), "premise: x pairs with the statement's first row"
        assert (table.summary["balance_chain"], [(row["lf_value"], row["lf_reason"]) for row in _truth(records, "truth_cash")]) == ("broken", [("", "balance_chain_broken")]), "premise: the chain is broken, the opening states no cash"
        assert _in_flight(records, "2021-03-07") == (Decimal(0), {}), "premise: nothing is in flight on the eve of the custody export"

        assert [row["lf_checkpoint"] for row in _truth(records, "truth_cash")] == ["2021-03-07"], "A13 (20/10): the opening on the eve of the custody export"
        assert [(row["lf_checkpoint"], row["lf_value"]) for row in _truth(records, "verification")] == [("2021-03-07", "1000.00"), ("2021-04-20", "761.00")], "the opening's verification is the statement's first balance"
        assert _checkpoint(output, "2021-03-07").cash == []
        assert [(item.as_of, _money(item.cash)) for item in output.verifications] == [(_d("2021-03-07"), {"EUR": Decimal("1000.00")}), (_d("2021-04-20"), {"EUR": Decimal("761.00")})]

    def test_a_tuotto_and_a_demerger_are_recorded_on_their_trade_date(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Red today: the DIVIDEND is dated 03-12 (the cash ``Pvm``) and the demerger lines 03-17 (``Arvopäivä``).

        Contract (B-52): a paired ``Tuotto`` and a demerger line are recorded on ``custody:Kauppapäivä``, like a trade. In
        the bank's exports their two dates are equal. Scenario "b52_events" makes them differ only to tell the columns
        apart: the DIVIDEND is recorded on 03-10 and both demerger lines on 03-15."""
        builder, table, _path, output = _scenario_parse("b52_events", tmp_path_factory)
        records = _records(table)

        assert (builder.row(records, "t")["lf_row_kind"], builder.row(records, "t") is builder.row(records, "ct")) == ("pair", True), "premise: the Tuotto pairs on its value date"
        assert [builder.row(records, key)["lf_row_kind"] for key in ("v", "u")] == ["standalone"] * 2, "premise: the demerger lines are standalone"

        events = [(tx[0], tx[1], tx[4]) for tx in _transactions(output) if tx[0] in ("DIVIDEND", "ADJUSTMENT")]
        assert events == [("DIVIDEND", _d("2021-03-10"), "Aurora Metsä Oyj"), ("ADJUSTMENT", _d("2021-03-15"), "Lumi Holding Oyj"), ("ADJUSTMENT", _d("2021-03-15"), "Lumi Uusi Oyj")], "B-52: events on Kauppapäivä"


# =============================================================================
# 11. THE COMBINED FORMAT
# =============================================================================


class TestCombinedFormat:
    """B0 "Combinato" and design §3.4.4: headers, value formats, order, verbatim cells, purity."""

    @pytest.mark.parametrize("set_name", sorted(SAMPLE_SETS))
    def test_headers(self, set_name: str) -> None:
        table = _sample_table(set_name)

        assert isinstance(table, BRIMCombinedTable)
        assert table.headers == COMBINED_HEADERS
        assert set(COMBINED_REQUIRED_HEADERS) <= set(table.headers)

    @pytest.mark.parametrize("set_name", sorted(SAMPLE_SETS))
    def test_value_formats(self, set_name: str) -> None:
        records = _records(_sample_table(set_name))
        first_checkpoint = min(row["lf_checkpoint"] for row in _truth(records, "truth_cash"))

        for number, record in enumerate(records, start=2):
            where = f"line {number} ({record['lf_row_kind']} {record['lf_source']})"
            kind = record["lf_row_kind"]
            assert kind in DATA_KINDS | TRUTH_KINDS, where
            assert kind == "verification" or record["lf_zone"] in ZONES, where
            assert record["lf_reason"] in (REASONS if kind == "excluded" else {""}), where
            assert record["lf_checkpoint"] == "" or ISO_DATE_RE.match(record["lf_checkpoint"]), where
            _sources(record)
            if kind in DATA_KINDS:
                assert (record["lf_value"], record["lf_proof"]) == ("", ""), where
                assert record["lf_match_key"] == "" or MATCH_KEY_RE.match(record["lf_match_key"]), where
            if kind == "pair":
                assert record["lf_match_key"] == f"{_from_fi_date(record['cash:Pvm']).isoformat()}|{_number(record['cash:Määrä']):.2f}|EUR", where
            if kind in TRUTH_KINDS:
                assert ISO_DATE_RE.match(record["lf_checkpoint"]), where
            if kind in ("truth_cash", "verification"):
                assert record["lf_currency"] == "EUR" and CASH_VALUE_RE.match(record["lf_value"]), where
            if kind == "truth_position":
                assert PROOF_RE.match(record["lf_proof"]), where
                assert record["lf_proof"].startswith("discarded:") or QUANTITY_VALUE_RE.match(record["lf_value"]), where
            if kind in ("truth_cash", "truth_position"):
                assert record["lf_zone"] == ("before" if record["lf_checkpoint"] == first_checkpoint else "gap"), where

    def test_source_tokens(self) -> None:
        """``custody:12``, ``cash:40``, ``custody:12 + cash:40``; ``custody#2:12`` for the files of a role that has several."""
        tokens = {name: {token.split(":")[0] for record in _records(_sample_table(name)) for token in record["lf_source"].split(" + ")} for name in sorted(SAMPLE_SETS)}

        assert tokens == {"gap": {"custody#1", "custody#2", "cash"}, "main": {"custody", "cash"}}
        assert _data_row(_records(_sample_table("main")), "custody", 1, 2)["lf_source"] == "custody:2 + cash:18"
        assert _data_row(_records(_sample_table("gap")), "custody", 2, 4)["lf_source"] == "custody#2:4 + cash:4"

    def test_member_cells_are_copied_verbatim(self) -> None:
        """XLSX text as is, XLSX numbers canonical ("50", "41.2", "-1181.04"), dates dd.mm.yyyy, CSV cells as is."""
        records = _records(_sample_table("main"))

        aurora = _data_row(records, "custody", 1, 2)
        assert {header: aurora[header] for header in COMBINED_HEADERS[len(LF_HEADERS) :]} == {
            "custody:Kauppapäivä": "10.02.2020",
            "custody:Arvopäivä": "12.02.2020",
            "custody:Sijoituskohde": "Aurora Metsä Oyj",
            "custody:Määrä": "50",
            "custody:Kurssi": "14.2",
            "custody:Palkkio<br/>sis. Alv": "0",
            "custody:Summa": "-718",
            "custody:H": "EUR",
            "custody:Tila": "Toteutettu",
            "custody:Toimeksiantotyyppi": "Rajakurssi",
            "cash:Pvm": "12.02.2020",
            "cash:Saaja/Maksaja": "Osto Aurora Metsä Oyj",
            "cash:Määrä": "-718",
            "cash:Saldo": "800,46",
            "cash:Tila": "Toteutunut",
            "cash:Tarkastus": "Ei",
        }
        kaamos = _data_row(records, "custody", 1, 5)
        assert (kaamos["custody:Määrä"], kaamos["custody:Kurssi"], kaamos["custody:Summa"], kaamos["cash:Määrä"], kaamos["cash:Saldo"]) == ("300", "41.2", "-1181.04", "-1181,04", "1518,46")
        tuotto = _data_row(records, "custody", 1, 3)
        assert (tuotto["custody:Kurssi"], tuotto["custody:Summa"], tuotto["cash:Määrä"], tuotto["cash:Saaja/Maksaja"]) == ("0", "22.5", "22,5", "Aurora Metsä 4820193756")
        vanha = _data_row(records, "custody", 1, 7)
        assert (vanha["custody:Määrä"], vanha["custody:Summa"], vanha["custody:H"], vanha["custody:Toimeksiantotyyppi"], vanha["cash:Pvm"]) == ("-100", "", "", "Jakautuminen, vanha", "")
        assert _data_row(records, "custody", 1, 16)["custody:Kurssi"] == "21"
        fee = _data_row(records, "cash", 1, 3)
        assert [fee[header] for header in COMBINED_HEADERS if header.startswith("custody:")] == [""] * 10
        assert (fee["cash:Pvm"], fee["cash:Saaja/Maksaja"], fee["cash:Määrä"], fee["cash:Saldo"]) == ("30.06.2020", "Palvelumaksut 06/2020", "-3,5", "1772,96")

    @pytest.mark.parametrize("set_name", sorted(SAMPLE_SETS))
    def test_rows_are_in_order(self, set_name: str) -> None:
        """By value date (truth rows at their date, after that day's data rows), then custody before cash, then file and line."""
        records = _records(_sample_table(set_name))
        keys = [_sort_key(record) for record in records]

        inversions = [f"line {index + 2} ({records[index]['lf_source']}) after line {index + 1} ({records[index - 1]['lf_source']})" for index in range(1, len(keys)) if keys[index] < keys[index - 1]]

        assert inversions == []

    @pytest.mark.parametrize(("set_name", "row_counts"), [("main", {("custody", 1): 15, ("cash", 1): 32}), ("gap", {("custody", 1): 3, ("custody", 2): 4, ("cash", 1): 14})])
    def test_every_member_row_lands_in_exactly_one_data_row(self, set_name: str, row_counts: Dict[Tuple[str, int], int]) -> None:
        _assert_each_source_row_once(row_counts, _records(_sample_table(set_name)))

    def test_combine_is_pure(self) -> None:
        """Same members, same table (D-S26); the members and the argument are left as they were."""
        plugin = _danske()
        members = _members(GAP_SET)
        before = {path: path.read_bytes() for paths in members.values() for path in paths}

        first, second = plugin.combine(members), plugin.combine(_members(GAP_SET))

        assert (first.headers, first.rows, first.summary) == (second.headers, second.rows, second.summary)
        assert {path: path.read_bytes() for path in before} == before
        assert members == _members(GAP_SET)

    @pytest.mark.parametrize("set_name", sorted(SAMPLE_SETS))
    def test_the_summary_can_be_stored_in_the_sidecar(self, set_name: str) -> None:
        """The core writes the summary into the combined file's JSON sidecar: plain JSON values only."""
        summary = _sample_table(set_name).summary

        assert summary
        try:
            json.dumps(summary)
        except TypeError as error:
            pytest.fail(f"the combine summary is not plain JSON: {error}")

    def test_written_by_the_core_it_reads_back_unchanged(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """No cell breaks the one-row-one-line layout the evidence line numbers rely on."""
        table, path, _output = _sample_parse("gap", tmp_path_factory)

        assert path.read_bytes().startswith(b"\xef\xbb\xbf")
        with open(path, encoding="utf-8-sig", newline="") as handle:
            assert list(csv.reader(handle, delimiter=";")) == [table.headers, *table.rows]
        assert _line_count(path) == len(table.rows) + 1


class TestPrivacy:
    """B0: ``Säilytystili`` is an account number; it serves the in-memory check and never leaves the members."""

    @pytest.mark.parametrize("set_name", sorted(SAMPLE_SETS))
    def test_samples(self, set_name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        table, path, output = _sample_parse(set_name, tmp_path_factory)

        assert [header for header in table.headers if "Säilytystili" in header] == []
        assert ACCOUNT not in path.read_text(encoding="utf-8-sig")
        assert ACCOUNT not in json.dumps(table.summary, default=str)
        assert ACCOUNT not in output.model_dump_json()

    def test_a_synthetic_set(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        _builder, table, path, output = _scenario_parse("zones", tmp_path_factory)

        assert ACCOUNT not in path.read_text(encoding="utf-8-sig") + json.dumps(table.summary, default=str) + output.model_dump_json()


# =============================================================================
# 12. THE PARSE OF THE COMBINED FILE — contract, on the samples and on synthetic sets
# =============================================================================

PARSED_SETS = [
    pytest.param("sample", "main", id="main"),
    pytest.param("sample", "gap", id="gap"),
    pytest.param("scenario", "zones", id="zones"),
    pytest.param("scenario", "classes", id="classes"),
    pytest.param("scenario", "same_day", id="same_day"),
    pytest.param("scenario", "conflict", id="conflict"),
]


class TestParseContract:
    """B0 "Parse del combinato": what the parse owes for every row, todo, notice and truth point of the file."""

    @pytest.mark.parametrize("name", sorted(SAMPLE_ROLES))
    def test_a_member_alone_is_refused(self, name: str) -> None:
        """A second guard behind the core's: a member is imported through its combined file only."""
        plugin = _danske()

        with pytest.raises(BRIMSetRequiredError):
            plugin.parse(SAMPLE_DIR / name, broker_id=BROKER_ID)

    @pytest.mark.parametrize(("source", "name"), PARSED_SETS)
    def test_no_validation_issue(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        _table, _path, output = _combined(source, name, tmp_path_factory)

        assert output.validation_issues == []
        assert all(tx.broker_id == BROKER_ID for tx in output.transactions)

    @pytest.mark.parametrize(("source", "name"), PARSED_SETS)
    def test_transactions_follow_the_combined_rows(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """One per pair and standalone row, in file order: type, date, quantity, cash, title, description and tags.

        Lot B-52: a pair and a demerger line are dated on the trade date (``custody:Kauppapäivä``), a cash-only row on its
        ``Pvm``. Red until the plugin dates the pairs that way: every set here has a pair whose two dates differ."""
        table, _path, output = _combined(source, name, tmp_path_factory)

        assert _transactions(output) == _owed_transactions(_records(table))
        assert all(tx.cash is None or tx.cash.code == "EUR" for tx in output.transactions)

    @pytest.mark.parametrize(("source", "name"), PARSED_SETS)
    def test_parse_is_idempotent(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        _table, path, output = _combined(source, name, tmp_path_factory)

        assert _danske().parse(path, broker_id=BROKER_ID).model_dump(mode="json") == output.model_dump(mode="json")

    @pytest.mark.parametrize(("source", "name"), PARSED_SETS)
    def test_one_fake_asset_per_title(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """The custody name is the extracted name; titles that only a truth position names get an id too."""
        table, _path, output = _combined(source, name, tmp_path_factory)
        records = _records(table)
        names = _names(output)

        assert all(is_fake_asset_id(asset_id) for asset_id in names)
        assert all(title and title.strip() for title in names.values())
        assert len(set(names.values())) == len(names), "one fake id per title"
        used = {tx.asset_id for tx in output.transactions if tx.asset_id is not None} | {position.asset_id for checkpoint in output.checkpoints for position in checkpoint.positions}
        assert used <= set(names)
        titles = {record["custody:Sijoituskohde"] for record in records if record["lf_row_kind"] in ("pair", "standalone") and record["custody:Sijoituskohde"]}
        titles |= {record["custody:Sijoituskohde"] for record in _truth(records, "truth_position") if not record["lf_proof"].startswith("discarded:")}
        assert titles <= set(names.values())

    @pytest.mark.parametrize(("source", "name"), PARSED_SETS)
    def test_todos_per_transaction(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """A BUY or SELL whose sum quantity × Kurssi does not explain: charges included (warning on ``cash``); one it
        explains (project 66, P2c, ``_owed_split``) and its FEE: none. A demerger: a blocking cost on the new lines, a
        warning on the old one."""
        table, _path, output = _combined(source, name, tmp_path_factory)
        owed = _owed_rows(_records(table))
        by_transaction: Dict[int, List[Tuple[str, str, str]]] = defaultdict(list)
        for todo in output.field_todos:
            by_transaction[todo.tx_index].append((todo.reason_code, todo.field, todo.severity))

        assert len(owed) == len(output.transactions), "premise: one transaction per owed row (test_transactions_follow_the_combined_rows)"
        assert set(by_transaction) <= set(range(len(output.transactions)))
        for index, (tx, (_owed_tx, expected)) in enumerate(zip(output.transactions, owed, strict=True)):
            assert sorted(by_transaction.get(index, [])) == expected, f"transaction {index}: {tx.type.value} {tx.date} {tx.description}"

    @pytest.mark.parametrize(("source", "name"), PARSED_SETS)
    def test_charges_todo_context(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """The split channel: row (a line of the combined file), cash, currency, no nominal, the hint, suggestions — and the charges when plausible in EUR.

        The row is the pair the trade comes from: same title, and (lot B-52) its trade date ``custody:Kauppapäivä`` is the
        transaction's date. Red until the plugin dates the trades that way."""
        table, _path, output = _combined(source, name, tmp_path_factory)
        records = _records(table)
        names = _names(output)
        todos = [todo for todo in output.field_todos if todo.reason_code == CHARGES]
        # Project 66, P2c: only a trade whose sum quantity × Kurssi does not explain keeps the todo.
        assert len(todos) == sum(1 for _tx, owed in _owed_rows(records) if (CHARGES, "cash", "warning") in owed)

        for todo in todos:
            tx = output.transactions[todo.tx_index]
            context = todo.context or {}
            where = f"{tx.type.value} {tx.date} {tx.description}"
            assert set(CHARGES_CONTEXT) <= set(context), where
            assert isinstance(context["row"], int) and 2 <= context["row"] <= len(records) + 1, where
            record = records[context["row"] - 2]
            assert (record["lf_row_kind"], _from_fi_date(record["custody:Kauppapäivä"]), record["custody:Sijoituskohde"]) == ("pair", tx.date, names[tx.asset_id]), where
            assert _owed_split(record) is None, f"{where}: a trade whose sum is explained is split, it has no todo"
            assert context["cash"] == f"{abs(tx.cash.amount):.2f}", f"{where}: cash is the absolute amount with two decimals"
            assert (context["currency"], context["compare_nominal"], context["split_hint"]) == ("EUR", False, "trade_charges"), where
            suggestions = context["split_suggestions"]
            assert isinstance(suggestions, list) and suggestions and all(isinstance(item, str) and item.strip() for item in suggestions), where
            # P2c (21/11): quantity × price does not explain this trade, so the todo has no amount to suggest.
            assert "charges" not in context, f"{where}: a charges todo carries no «charges»"
            assert not any(GROSS_SUGGESTION in item for item in suggestions), f"{where}: no «{GROSS_SUGGESTION}» suggestion: {suggestions}"

    @pytest.mark.parametrize(("source", "name"), PARSED_SETS)
    def test_every_todo_shows_its_source_rows(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        _table, path, output = _combined(source, name, tmp_path_factory)
        lines = _line_count(path)

        for todo in output.field_todos:
            where = f"{todo.reason_code} on transaction {todo.tx_index}"
            assert todo.message and todo.message.strip(), where
            assert todo.evidence, where
            for evidence in todo.evidence:
                assert evidence.title.strip() and evidence.comment and evidence.comment.strip(), where
                assert evidence.row_numbers and len(evidence.row_numbers) == len(evidence.rows), where
                assert all(1 <= number <= lines for number in evidence.row_numbers), where
                assert all(len(row) == len(evidence.headers) for row in evidence.rows), where

    @pytest.mark.parametrize(("source", "name"), PARSED_SETS)
    def test_notices(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Stable codes with their severity; one ``excluded_<reason>`` per reason, showing exactly those rows, but for the
        silent reasons (lot W-B85: ``reservation``), whose rows no notice shows; the others when they apply. Only a code of
        REPORT_ISSUE_NOTICES may carry ``report_issue`` (that ``excluded_status`` does is pinned in TestKnownAndUnknownRows)."""
        table, path, output = _combined(source, name, tmp_path_factory)
        records = _records(table)
        lines = _line_count(path)
        excluded: Dict[str, Set[int]] = defaultdict(set)
        for number, record in enumerate(records, start=2):
            if record["lf_row_kind"] == "excluded":
                excluded[record["lf_reason"]].add(number)
        by_code: Dict[str, List[Any]] = defaultdict(list)
        for notice in output.warnings:
            by_code[notice.code].append(notice)

        for code, notices in by_code.items():
            severity = EXCLUDED_NOTICES.get(code, "warning") if code.startswith("excluded_") else PARSE_NOTICES.get(code)
            assert severity, f"unknown parse notice code {code!r}"
            for notice in notices:
                assert notice.severity == severity, code
                assert notice.message and notice.message.strip(), code
                assert code in REPORT_ISSUE_NOTICES or "report_issue" not in (notice.context or {}), code
                for evidence in notice.evidence:
                    assert evidence.title.strip() and evidence.comment and evidence.comment.strip(), code
                    assert all(1 <= number <= lines for number in evidence.row_numbers), code
        shown = {number for notices in by_code.values() for notice in notices for evidence in notice.evidence for number in evidence.row_numbers}
        assert sorted(code for code in by_code if code.startswith("excluded_")) == sorted(f"excluded_{reason}" for reason in excluded if reason not in SILENT_REASONS)
        for reason, numbers in excluded.items():
            if reason in SILENT_REASONS:
                assert sorted(numbers & shown) == [], f"{reason}: rows left out in silence, shown by a notice"
                continue
            notices = by_code[f"excluded_{reason}"]
            assert len(notices) == 1, reason
            assert {number for evidence in notices[0].evidence for number in evidence.row_numbers} == numbers, reason
        assert ("deferred_rows" in by_code) == any(record["lf_row_kind"] == "deferred" for record in records)
        assert ("proof_discarded" in by_code) == any(record["lf_proof"].startswith("discarded:") for record in _truth(records, "truth_position"))
        assert ("deposit_assumed" in by_code) == any(tx.type.value == "DEPOSIT" for tx in output.transactions)
        assert (SPLIT_NOTICE in by_code) == any(split is not None and split[1] > 0 for split in map(_owed_split, records))

    @pytest.mark.parametrize(("source", "name"), PARSED_SETS)
    def test_checkpoints_and_verifications_are_the_truth_rows(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """The earliest checkpoint is the opening; positions carry the transactions' fake ids; the absorbed rows are the data rows of that date."""
        table, _path, output = _combined(source, name, tmp_path_factory)
        records = _records(table)
        names = _names(output)
        truth_cash = _truth(records, "truth_cash")
        dates = sorted(row["lf_checkpoint"] for row in truth_cash)

        assert sorted(checkpoint.as_of.isoformat() for checkpoint in output.checkpoints) == dates
        for checkpoint in output.checkpoints:
            day = checkpoint.as_of.isoformat()
            [row] = [item for item in truth_cash if item["lf_checkpoint"] == day]
            assert checkpoint.kind == ("opening" if day == dates[0] else "gap"), day
            assert _money(checkpoint.cash) == ({row["lf_currency"]: Decimal(row["lf_value"])} if row["lf_value"] else {}), day
            proven = sorted((item["custody:Sijoituskohde"], Decimal(item["lf_value"]), item["lf_proof"].split(":")[0]) for item in _truth(records, "truth_position", day) if not item["lf_proof"].startswith("discarded:"))
            assert sorted((names.get(position.asset_id), position.quantity, position.exactness) for position in checkpoint.positions) == proven, day
            absorbed = sorted((_from_fi_date(item["cash:Pvm"]), "EUR", _number(item["cash:Määrä"]), item["cash:Saaja/Maksaja"]) for item in records if item["lf_row_kind"] in DATA_KINDS and item["lf_checkpoint"] == day and item["cash:Määrä"])
            assert sorted((item.as_of, item.currency, item.amount, item.label) for item in checkpoint.absorbed.rows) == absorbed, day
            assert checkpoint.absorbed.count == len(absorbed), day
            total = sum((item[2] for item in absorbed), Decimal(0))
            assert _nonzero(_money(checkpoint.absorbed.cash)) == _nonzero({"EUR": total}), day
            if checkpoint.kind == "gap":
                assert checkpoint.absorbed.opening_cash == [], day
            elif checkpoint.cash:
                assert _money(checkpoint.absorbed.opening_cash) == {"EUR": _money(checkpoint.cash)["EUR"] - total}, day
        stated = sorted((row["lf_checkpoint"], row["lf_currency"], Decimal(row["lf_value"])) for row in _truth(records, "verification"))
        assert sorted((item.as_of.isoformat(), cash.currency, cash.amount) for item in output.verifications for cash in item.cash) == stated


# =============================================================================
# 13. THE MAIN SAMPLE SET
# =============================================================================


def _with_fee(trade: Tuple[Optional[str], ...], fee: str) -> List[Tuple[Optional[str], ...]]:
    """A split trade (project 66, P2c) and the FEE right after it: same date and title, no shares, ``fee`` as cash, and
    ``Palkkio: `` + the trade's description."""
    _tx_type, day, _quantity, _cash, title, description = trade
    return [trade, ("FEE", day, "0", fee, title, f"Palkkio: {description}")]


# (type, date, quantity, cash, title, description), in the order of the combined file (by value date). Lot B-52: a paired
# trade is dated on its trade date (custody Kauppapäivä), two business days before its cash row here; a Tuotto and a
# demerger have both dates equal; a cash-only row keeps its Pvm. Project 66, P2c: a trade whose sum quantity × Kurssi
# explains is booked at quantity × Kurssi, its 8 of charges a FEE right after it; Kaamos (a price in another currency:
# 300 × 41.2 is no 1181.04) keeps the sum paid.
MAIN_TRANSACTIONS = [
    ("DEPOSIT", "2019-01-07", "0", "6000", None, "Matti Meikäläinen"),
    ("FEE", "2019-03-29", "0", "-3.5", None, "Palvelumaksut 03/2019"),
    ("FEE", "2019-06-28", "0", "-3.5", None, "Palvelumaksut 06/2019"),
    ("FEE", "2019-09-30", "0", "-3.5", None, "Palvelumaksut 09/2019"),
    ("TAX", "2019-11-04", "0", "-21.3", None, "Vero osakesäästötililtä"),
    ("WITHDRAWAL", "2019-11-04", "0", "-300", None, "Nosto osakesäästötililtä"),
    ("FEE", "2019-12-31", "0", "-3.5", None, "Palvelumaksut 12/2019"),
    ("BUY", "2020-02-03", "300", "-1181.04", "Kaamos Robotics AB", "Osto Kaamos Robotics AB (Rajakurssi)"),
    *_with_fee(("BUY", "2020-02-10", "50", "-710", "Aurora Metsä Oyj", "Osto Aurora Metsä Oyj (Rajakurssi)"), "-8"),
    *_with_fee(("BUY", "2020-03-02", "40", "-394", "Lumi Holding Oyj", "Osto Lumi Holding Oyj (Pikakauppa)"), "-8"),
    *_with_fee(("SELL", "2020-03-10", "-120", "732", "Pohjola Tekniikka Oyj", "Myynti Pohjola Tekniikka (Päivän kurssi)"), "-8"),
    ("DEPOSIT", "2020-03-20", "0", "1000", None, "Matti Meikäläinen"),
    *_with_fee(("BUY", "2020-03-25", "25", "-310", "Saimaa Energia Oyj", "Osto Saimaa Energia Oyj (Rajakurssi)"), "-8"),
    *_with_fee(("BUY", "2020-03-25", "25", "-310", "Saimaa Energia Oyj", "Osto Saimaa Energia Oyj (Rajakurssi)"), "-8"),
    ("FEE", "2020-03-31", "0", "-3.5", None, "Palvelumaksut 03/2020"),
    *_with_fee(("BUY", "2020-04-01", "20", "-108", "Pohjola Tekniikka Oyj", "Osto Pohjola Tekniikka O (Rajakurssi)"), "-8"),
    ("DIVIDEND", "2020-04-15", "0", "22.5", "Aurora Metsä Oyj", "Aurora Metsä 4820193756 (Tuotto)"),
    *_with_fee(("SELL", "2020-05-05", "-80", "540", "Pohjola Tekniikka Oyj", "Myynti Pohjola Tekniikka (Päivän kurssi)"), "-8"),
    *_with_fee(("SELL", "2020-05-20", "-30", "474", "Aurora Metsä Oyj", "Myynti Aurora Metsä Oyj (Rajakurssi)"), "-8"),
    ("ADJUSTMENT", "2020-06-01", "-100", None, "Lumi Holding Oyj", "Jakautuminen, vanha: Lumi Holding Oyj"),
    ("ADJUSTMENT", "2020-06-01", "100", None, "Lumi Kiinteistöt Oyj", "Jakautuminen, uusi: Lumi Kiinteistöt Oyj"),
    ("ADJUSTMENT", "2020-06-01", "100", None, "Lumi Palvelut Oyj", "Jakautuminen, uusi: Lumi Palvelut Oyj"),
    ("TAX", "2020-06-10", "0", "-45", None, "Vero osakesäästötililtä"),
    ("WITHDRAWAL", "2020-06-10", "0", "-500", None, "Nosto osakesäästötililtä"),
    *_with_fee(("SELL", "2020-06-15", "-50", "160", "Lumi Palvelut Oyj", "Myynti Lumi Palvelut Oyj (Päivän kurssi)"), "-8"),
    *_with_fee(("BUY", "2020-06-26", "10", "-210", "Tunturi Pankki Oyj", "Osto Tunturi Pankki Oyj (Rajakurssi)"), "-8"),
    ("FEE", "2020-06-30", "0", "-3.5", None, "Palvelumaksut 06/2020"),
]
# custody line -> cash line of every pair but the two identical partial fills (custody 14 and 15, cash 13 and 14).
MAIN_PAIRS = {2: 18, 3: 10, 4: 8, 5: 19, 6: 17, 10: 5, 11: 16, 12: 11, 13: 9, 16: 4}
# cash line, row kind, accepted zones, checkpoint (C1 = 2020-02-02 absorbs every cash row up to it, and the border orphan).
MAIN_CASH_ROWS = [
    pytest.param(2, "deferred", {"window", "after"}, "", id="purchase-settled-after-the-custody-export"),
    pytest.param(3, "standalone", {"window"}, "", id="fee-06-2020"),
    pytest.param(6, "standalone", {"window"}, "", id="tax-2020"),
    pytest.param(7, "standalone", {"window"}, "", id="withdrawal-2020"),
    pytest.param(12, "standalone", {"window"}, "", id="fee-03-2020"),
    pytest.param(15, "standalone", {"window"}, "", id="deposit-2020"),
    pytest.param(20, "summarized", {"window"}, "2020-02-02", id="border-orphan"),
    pytest.param(21, "standalone", {"before"}, "2020-02-02", id="fee-12-2019"),
    pytest.param(22, "standalone", {"before"}, "2020-02-02", id="tax-2019"),
    pytest.param(23, "standalone", {"before"}, "2020-02-02", id="withdrawal-2019"),
    pytest.param(24, "summarized", {"before"}, "2020-02-02", id="sale-2019"),
    pytest.param(25, "standalone", {"before"}, "2020-02-02", id="fee-09-2019"),
    pytest.param(26, "standalone", {"before"}, "2020-02-02", id="fee-06-2019"),
    pytest.param(27, "summarized", {"before"}, "2020-02-02", id="income-2019"),
    pytest.param(28, "standalone", {"before"}, "2020-02-02", id="fee-03-2019"),
    pytest.param(29, "summarized", {"before"}, "2020-02-02", id="purchase-pohjola-2019"),
    pytest.param(30, "summarized", {"before"}, "2020-02-02", id="purchase-revontuli-2019"),
    pytest.param(31, "summarized", {"before"}, "2020-02-02", id="purchase-lumi-2019"),
    pytest.param(32, "summarized", {"before"}, "2020-02-02", id="purchase-aurora-2019"),
    pytest.param(33, "standalone", {"before"}, "2020-02-02", id="first-deposit-2019"),
]


def _pair_lines(records: List[Dict[str, str]]) -> Dict[Tuple[int, int], int]:
    """``{(custody file, custody line): cash line}`` of every pair; each pair joins one row of each role."""
    pairs = {}
    for record in records:
        if record["lf_row_kind"] != "pair":
            continue
        custody = [(number, line) for role, number, line in _sources(record) if role == "custody"]
        cash = [line for role, _number, line in _sources(record) if role == "cash"]
        assert len(custody) == len(cash) == 1, record["lf_source"]
        assert (record["lf_zone"], record["lf_reason"], record["lf_checkpoint"]) == ("window", "", ""), record["lf_source"]
        pairs[custody[0]] = cash[0]
    return pairs


def _expected_todos(transactions: Sequence[Tuple[Optional[str], ...]]) -> List[Tuple[Any, ...]]:
    """(transaction, reason, field, severity, cash, charges) of the sample todos.

    Project 66, P2c: a trade followed by its FEE (``_with_fee``) was split and has no todo. The others keep the charges
    todo, stating the trade's cash as its absolute amount with two decimals ("1181.04") and no charges: in the samples
    they are the titles priced in another currency.
    """
    todos = []
    for index, (tx_type, _day, quantity, cash, _title, description) in enumerate(transactions):
        follower = transactions[index + 1] if index + 1 < len(transactions) else None
        split = follower is not None and follower[0] == "FEE" and follower[5] == f"Palkkio: {description}"
        if tx_type in ("BUY", "SELL") and not split:
            todos.append((index, CHARGES, "cash", "warning", f"{abs(Decimal(cash)):.2f}", None))
        elif tx_type == "ADJUSTMENT":
            todos.append((index, DEMERGER, "cost_basis_override", "blocker", None, None) if Decimal(quantity) > 0 else (index, DEMERGER_OLD, "quantity", "warning", None, None))
    return todos


def _sample_todos(output: BRIMParseOutput) -> List[Tuple[Any, ...]]:
    """(transaction, reason, field, severity, cash, charges) of the parse, cash and charges read on the split todos only."""
    todos = []
    for todo in output.field_todos:
        context = (todo.context or {}) if todo.reason_code == CHARGES else {}
        todos.append((todo.tx_index, todo.reason_code, todo.field, todo.severity, context.get("cash"), context.get("charges")))
    return sorted(todos, key=lambda item: (item[0], item[1]))


class TestMainSampleFacts:
    """The main set: a custody export 2020-02-03…06-26 and a Latin-1 cash statement 2019-01-07…2020-07-03."""

    def test_row_kinds(self) -> None:
        kinds = Counter(record["lf_row_kind"] for record in _records(_sample_table("main")))

        assert kinds == Counter({"pair": 12, "standalone": 15, "summarized": 7, "deferred": 1, "truth_cash": 1, "truth_position": 3, "verification": 1})

    def test_pairs(self) -> None:
        pairs = _pair_lines(_records(_sample_table("main")))

        assert {line: cash for (_file, line), cash in pairs.items() if line not in (14, 15)} == MAIN_PAIRS
        assert sorted(pairs[(1, line)] for line in (14, 15)) == [13, 14]

    @pytest.mark.parametrize("line", [7, 8, 9], ids=["old-line", "new-line-1", "new-line-2"])
    def test_demerger_lines_are_standalone(self, line: int) -> None:
        row = _data_row(_records(_sample_table("main")), "custody", 1, line)

        assert (row["lf_row_kind"], row["lf_zone"], row["lf_reason"], row["lf_checkpoint"]) == ("standalone", "window", "", "")

    @pytest.mark.parametrize(("line", "kind", "zones", "checkpoint"), MAIN_CASH_ROWS)
    def test_cash_rows(self, line: int, kind: str, zones: Set[str], checkpoint: str) -> None:
        row = _data_row(_records(_sample_table("main")), "cash", 1, line)

        assert row["lf_row_kind"] == kind
        assert row["lf_zone"] in zones
        assert (row["lf_reason"], row["lf_checkpoint"]) == ("", checkpoint)

    def test_truth_rows(self) -> None:
        """C1 = 2020-02-02: 2819.50 at the end of the day, minus the border orphan (−120 settled 2020-02-03). Nothing is in
        flight at C1: the first trade is on 2020-02-03.

        The verification on 2020-06-26 is in operation-date terms (lot B-52): the bank's 1994.46 at the end of the day,
        plus the Tunturi purchase traded that day and settled on 06-30 (−218), gives 1776.46. Red until the plugin counts
        the trades in flight."""
        records = _records(_sample_table("main"))

        assert [(row["lf_checkpoint"], row["lf_value"], row["lf_currency"], row["lf_zone"]) for row in _truth(records, "truth_cash")] == [("2020-02-02", "2699.50", "EUR", "before")]
        assert sorted((row["custody:Sijoituskohde"], row["lf_value"], row["lf_proof"], row["lf_checkpoint"], row["lf_zone"]) for row in _truth(records, "truth_position")) == [
            ("Aurora Metsä Oyj", "100", "exact:E1", "2020-02-02", "before"),
            ("Lumi Holding Oyj", "60", "exact:E2", "2020-02-02", "before"),
            ("Pohjola Tekniikka Oyj", "180", "at_least:E3", "2020-02-02", "before"),
        ]
        assert [(row["lf_checkpoint"], row["lf_value"], row["lf_currency"]) for row in _truth(records, "verification")] == [("2020-06-26", "1776.46", "EUR")]

    def test_transactions(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Every transaction in file order. Lot B-52: each paired trade dated on its trade date. Red until the plugin does
        so."""
        _table, _path, output = _sample_parse("main", tmp_path_factory)

        assert _transactions(output) == [_expected_tx(*row) for row in MAIN_TRANSACTIONS]
        # Project 66, P2c: 6 service fees and the 10 commissions split out of the trades.
        assert Counter(tx.type.value for tx in output.transactions) == Counter({"BUY": 7, "SELL": 4, "DIVIDEND": 1, "ADJUSTMENT": 3, "FEE": 16, "TAX": 2, "WITHDRAWAL": 2, "DEPOSIT": 2})

    def test_assets(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        _table, _path, output = _sample_parse("main", tmp_path_factory)

        assert sorted(_names(output).values()) == ["Aurora Metsä Oyj", "Kaamos Robotics AB", "Lumi Holding Oyj", "Lumi Kiinteistöt Oyj", "Lumi Palvelut Oyj", "Pohjola Tekniikka Oyj", "Saimaa Energia Oyj", "Tunturi Pankki Oyj"]

    def test_todos(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Project 66, P2c: of the 11 trades only the title priced in another currency keeps its charges todo (the other
        10 are split); two blocking new lines, one old line."""
        _table, _path, output = _sample_parse("main", tmp_path_factory)

        todos = _sample_todos(output)

        assert todos == _expected_todos(MAIN_TRANSACTIONS)
        assert Counter(todo[1] for todo in todos) == Counter({CHARGES: 1, DEMERGER: 2, DEMERGER_OLD: 1})
        assert [(todo[4], todo[5]) for todo in todos if todo[1] == CHARGES] == [("1181.04", None)]

    def test_notices(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        _table, _path, output = _sample_parse("main", tmp_path_factory)

        assert sorted(set(_codes(output.warnings))) == sorted([SPLIT_NOTICE, "deferred_rows", "deposit_assumed"])

    def test_checkpoint_and_verification(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """The opening as it is (nothing in flight on 2020-02-02); the verification in operation-date terms, 1776.46 (lot
        B-52: the Tunturi purchase of 2020-06-26 is in flight). Red until the plugin counts it."""
        _table, _path, output = _sample_parse("main", tmp_path_factory)

        assert len(output.checkpoints) == 1
        opening = output.checkpoints[0]
        assert (opening.as_of, opening.kind, _money(opening.cash)) == (_d("2020-02-02"), "opening", {"EUR": Decimal("2699.50")})
        assert _positions(output, opening) == {"Aurora Metsä Oyj": (Decimal("100"), "exact"), "Lumi Holding Oyj": (Decimal("60"), "exact"), "Pohjola Tekniikka Oyj": (Decimal("180"), "at_least")}
        assert all(position.unit_cost is None for position in opening.positions)
        absorbed = opening.absorbed
        assert (absorbed.count, len(absorbed.rows), _money(absorbed.cash), _money(absorbed.opening_cash)) == (14, 14, {"EUR": Decimal("2699.50")}, {"EUR": Decimal("0")})
        assert (_d("2020-02-03"), "EUR", Decimal("-120"), "Osto Pohjola Tekniikka O") in [(row.as_of, row.currency, row.amount, row.label) for row in absorbed.rows]
        assert (min(row.as_of for row in absorbed.rows), max(row.as_of for row in absorbed.rows)) == (_d("2019-01-07"), _d("2020-02-03"))
        assert [(item.as_of, _money(item.cash)) for item in output.verifications] == [(_d("2020-06-26"), {"EUR": Decimal("1776.46")})]


# =============================================================================
# 14. THE GAP SAMPLE SET
# =============================================================================

# Lot B-52: a paired trade dated on its trade date (custody Kauppapäivä); the Tuotto has both dates equal. Project 66, P2c:
# a trade quantity × Kurssi explains is booked at it, its 8 of charges a FEE right after it; Kaamos keeps the sum received.
GAP_TRANSACTIONS = [
    ("DEPOSIT", "2020-08-03", "0", "2000", None, "Matti Meikäläinen"),
    ("FEE", "2020-08-31", "0", "-3.5", None, "Palvelumaksut 08/2020"),
    *_with_fee(("BUY", "2020-09-01", "40", "-644", "Aurora Metsä Oyj", "Osto Aurora Metsä Oyj (Rajakurssi)"), "-8"),
    *_with_fee(("SELL", "2020-09-14", "-50", "652.5", "Saimaa Energia Oyj", "Myynti Saimaa Energia Oy (Päivän kurssi)"), "-8"),
    ("FEE", "2020-09-30", "0", "-3.5", None, "Palvelumaksut 09/2020"),
    *_with_fee(("BUY", "2020-10-30", "10", "-223", "Tunturi Pankki Oyj", "Osto Tunturi Pankki Oyj (Rajakurssi)"), "-8"),
    ("DEPOSIT", "2020-12-15", "0", "500", None, "Matti Meikäläinen"),
    ("FEE", "2020-12-31", "0", "-3.5", None, "Palvelumaksut 12/2020"),
    ("SELL", "2021-01-05", "-100", "428.56", "Kaamos Robotics AB", "Myynti Kaamos Robotics A (Päivän kurssi)"),
    *_with_fee(("SELL", "2021-01-20", "-60", "432", "Pohjola Tekniikka Oyj", "Myynti Pohjola Tekniikka (Päivän kurssi)"), "-8"),
    ("DIVIDEND", "2021-02-15", "0", "28.5", "Aurora Metsä Oyj", "Aurora Metsä 5930284716 (Tuotto)"),
    ("FEE", "2021-03-01", "0", "-3.5", None, "Palvelumaksut 02/2021"),
]
# (custody file, custody line) -> cash line.
GAP_PAIRS = {(1, 2): 13, (1, 3): 12, (1, 4): 10, (2, 2): 3, (2, 3): 5, (2, 4): 4}
# cash line, row kind, zone, checkpoint: C1 = 2020-08-31 absorbs what precedes it, C2 = 2021-01-04 the trades of the gap.
GAP_CASH_ROWS = [
    pytest.param(2, "standalone", "window", "", id="fee-02-2021"),
    pytest.param(6, "standalone", "gap", "", id="gap-fee-imported"),
    pytest.param(7, "standalone", "gap", "", id="gap-deposit-imported"),
    pytest.param(8, "summarized", "gap", "2021-01-04", id="gap-sale-summarized"),
    pytest.param(9, "summarized", "gap", "2021-01-04", id="gap-purchase-summarized"),
    pytest.param(11, "standalone", "window", "", id="fee-09-2020"),
    pytest.param(14, "standalone", "before", "2020-08-31", id="fee-08-2020"),
    pytest.param(15, "standalone", "before", "2020-08-31", id="first-deposit"),
]
# The positions at C2 = 2021-01-04: E3 bounds the only movements of Kaamos (the sale of 100 on
# 2021-01-05) and of Pohjola (the sale of 60 on 2021-01-20) from below; the Tuotto of 2021-02-15 proves Aurora.
GAP_C2_POSITIONS = {"Aurora Metsä Oyj": (Decimal("190"), "exact"), "Kaamos Robotics AB": (Decimal("100"), "at_least"), "Pohjola Tekniikka Oyj": (Decimal("60"), "at_least")}


class TestGapSampleFacts:
    """The gap set: custody 2020-09-01…10-30 and 2021-01-05…02-26, one cash statement proving the trades in between."""

    def test_row_kinds(self) -> None:
        kinds = Counter(record["lf_row_kind"] for record in _records(_sample_table("gap")))

        assert kinds == Counter({"pair": 6, "standalone": 6, "summarized": 2, "excluded": 1, "truth_cash": 2, "truth_position": 4, "verification": 1})

    def test_pairs(self) -> None:
        assert _pair_lines(_records(_sample_table("gap"))) == GAP_PAIRS

    def test_a_trade_settled_after_the_statement(self) -> None:
        """The last purchase (2021-02-26) settles on 2021-03-02, after the last cash row (2021-03-01)."""
        row = _data_row(_records(_sample_table("gap")), "custody", 2, 5)

        assert (row["lf_row_kind"], row["lf_zone"], row["lf_reason"], row["lf_checkpoint"]) == ("excluded", "window", "not_yet_settled", "")

    @pytest.mark.parametrize(("line", "kind", "zone", "checkpoint"), GAP_CASH_ROWS)
    def test_cash_rows(self, line: int, kind: str, zone: str, checkpoint: str) -> None:
        row = _data_row(_records(_sample_table("gap")), "cash", 1, line)

        assert (row["lf_row_kind"], row["lf_zone"], row["lf_reason"], row["lf_checkpoint"]) == (kind, zone, "", checkpoint)

    def test_truth_rows(self) -> None:
        """Lot B-52 leaves every truth of this set as it is, green today and after. Nothing is in flight at C1 (2020-08-31)
        or C2 (2021-01-04). On the verification day (2021-02-26) the last purchase is traded but not settled, and it is
        left out (``not_yet_settled``). A trade that is not imported is never in flight."""
        records = _records(_sample_table("gap"))

        assert [(row["lf_checkpoint"], row["lf_value"], row["lf_currency"], row["lf_zone"]) for row in _truth(records, "truth_cash")] == [("2020-08-31", "3519.86", "EUR", "before"), ("2021-01-04", "3482.36", "EUR", "gap")]
        assert [(row["custody:Sijoituskohde"], row["lf_value"], row["lf_proof"], row["lf_zone"]) for row in _truth(records, "truth_position", "2020-08-31")] == [("Saimaa Energia Oyj", "50", "at_least:E3", "before")]
        at_c2 = sorted((row["custody:Sijoituskohde"], row["lf_value"], row["lf_proof"], row["lf_zone"]) for row in _truth(records, "truth_position", "2021-01-04"))
        assert at_c2 == [("Aurora Metsä Oyj", "190", "exact:E1", "gap"), ("Kaamos Robotics AB", "100", "at_least:E3", "gap"), ("Pohjola Tekniikka Oyj", "60", "at_least:E3", "gap")]
        assert [(row["lf_checkpoint"], row["lf_value"], row["lf_currency"]) for row in _truth(records, "verification")] == [("2021-02-26", "4363.42", "EUR")]

    def test_transactions(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Every transaction in file order. Lot B-52: each paired trade dated on its trade date. Red until the plugin does
        so."""
        _table, _path, output = _sample_parse("gap", tmp_path_factory)

        assert _transactions(output) == [_expected_tx(*row) for row in GAP_TRANSACTIONS]

    def test_assets(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        _table, _path, output = _sample_parse("gap", tmp_path_factory)

        assert sorted(_names(output).values()) == ["Aurora Metsä Oyj", "Kaamos Robotics AB", "Pohjola Tekniikka Oyj", "Saimaa Energia Oyj", "Tunturi Pankki Oyj"]

    def test_todos(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        _table, _path, output = _sample_parse("gap", tmp_path_factory)

        todos = _sample_todos(output)

        assert todos == _expected_todos(GAP_TRANSACTIONS)
        # Project 66, P2c: only Kaamos (100 × 44.8 is no 428.56: a price in another currency) keeps its todo.
        assert [(todo[4], todo[5]) for todo in todos if todo[1] == CHARGES] == [("428.56", None)]

    def test_notices(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Lot N74: the purchase settled after the statement is a note (info), like the assumed deposit — red until the plugin
        stops calling it a warning."""
        _table, _path, output = _sample_parse("gap", tmp_path_factory)

        assert sorted(set(_codes(output.warnings))) == sorted([SPLIT_NOTICE, "deposit_assumed", "excluded_not_yet_settled"])
        assert sorted({(notice.code, notice.severity) for notice in output.warnings}) == sorted([(SPLIT_NOTICE, "info"), ("deposit_assumed", "info"), ("excluded_not_yet_settled", "info")])

    def test_checkpoints_and_verification(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """The opening absorbs the two rows before 2020-09-01 over an opening balance of 1523.36; the gap checkpoint the two trades of the gap.

        Lot B-52 changes none of these values: nothing is in flight at either checkpoint, and the purchase that straddles
        the verification is left out (green today and after)."""
        _table, _path, output = _sample_parse("gap", tmp_path_factory)

        opening, gap = _checkpoint(output, "2020-08-31"), _checkpoint(output, "2021-01-04")
        assert (opening.kind, _money(opening.cash), _positions(output, opening)) == ("opening", {"EUR": Decimal("3519.86")}, {"Saimaa Energia Oyj": (Decimal("50"), "at_least")})
        assert sorted((row.as_of, row.currency, row.amount, row.label) for row in opening.absorbed.rows) == [(_d("2020-08-03"), "EUR", Decimal("2000"), "Matti Meikäläinen"), (_d("2020-08-31"), "EUR", Decimal("-3.5"), "Palvelumaksut 08/2020")]
        assert (opening.absorbed.count, _money(opening.absorbed.cash), _money(opening.absorbed.opening_cash)) == (2, {"EUR": Decimal("1996.50")}, {"EUR": Decimal("1523.36")})
        assert (gap.kind, _money(gap.cash)) == ("gap", {"EUR": Decimal("3482.36")})
        assert _positions(output, gap) == GAP_C2_POSITIONS
        assert sorted((row.as_of, row.currency, row.amount, row.label) for row in gap.absorbed.rows) == [(_d("2020-11-18"), "EUR", Decimal("-515"), "Osto Aurora Metsä Oyj"), (_d("2020-12-10"), "EUR", Decimal("223"), "Myynti Tunturi Pankki Oy")]
        assert (gap.absorbed.count, _money(gap.absorbed.cash), gap.absorbed.opening_cash) == (2, {"EUR": Decimal("-292")}, [])
        assert [(item.as_of, _money(item.cash)) for item in output.verifications] == [(_d("2021-02-26"), {"EUR": Decimal("4363.42")})]


# =============================================================================
# 15. FIXTURE GUARDS — the writers of this file, not the product
# =============================================================================


def _chain_breaks(path: Path) -> List[date]:
    """Days on which the running balance of a statement does not hold, read like B0 reads it (posted rows only)."""
    posted = []
    for line in reversed([line for line in path.read_bytes().decode("latin-1").split("\n")[1:] if line]):
        day_text, label, amount_text, saldo_text, status, _check = line.split(";")
        try:
            day, amount = _from_fi_date(day_text), _number(amount_text)
        except (ValueError, InvalidOperation):
            continue
        if status == "Toteutunut" and not label.startswith("Varaus"):
            posted.append((day, amount, _number(saldo_text)))
    if not posted:
        return []
    balance = posted[0][2] - posted[0][1]
    breaks = []
    for day in sorted({row[0] for row in posted}):
        todays = [row for row in posted if row[0] == day]
        balance += sum(amount for _day, amount, _saldo in todays)
        if balance not in {saldo for _day, _amount, saldo in todays}:
            breaks.append(day)
            balance = todays[-1][2]  # carry on from what the bank states, to report each break once
    return breaks


class TestFixtureGuards:
    """Fixture guards (pass before and after phase B): the writers produce what the tests say they produce."""

    @pytest.mark.parametrize("name", ["danske_bank-cash.csv", "danske_bank-gap-cash.csv"])
    def test_fixture_guard_the_cash_writer_reproduces_the_samples(self, name: str, tmp_path: Path) -> None:
        """From its own rows, the writer rebuilds a sample byte for byte: Latin-1, ``;``, LF, newest first, the running Saldo."""
        lines = [line for line in (SAMPLE_DIR / name).read_bytes().decode("latin-1").split("\n")[1:] if line]
        rows = [_Cash(_from_fi_date(cells[0]).isoformat(), cells[1], str(_number(cells[2])), status=cells[4]) for cells in (line.split(";") for line in reversed(lines))]
        oldest = lines[-1].split(";")
        path = tmp_path / name

        _write_cash(path, rows, opening=str(_number(oldest[3]) - _number(oldest[2])))

        assert path.read_bytes() == (SAMPLE_DIR / name).read_bytes()

    def test_fixture_guard_the_custody_writer_writes_the_sample_cells(self, tmp_path: Path) -> None:
        """Text dates, numbers as cells, the unnamed column H and the account, as in the main custody sample."""
        header, rows = _sample_custody()
        path = tmp_path / "custody.xlsx"

        _write_custody(path, [_trade("2020-02-10", "Aurora Metsä Oyj", 50, 14.2, -718, value="2020-02-12"), _tuotto("2020-04-15", "Aurora Metsä Oyj", 150, 22.5), _demerger("2020-06-01", "Lumi Holding Oyj", -100, old=True)])

        written = [list(row) for row in openpyxl.load_workbook(path).active.iter_rows(values_only=True)]
        assert written == [header, rows[0], rows[1], rows[5]]

    def test_fixture_guard_a_preamble_puts_the_header_on_row_four(self, tmp_path: Path) -> None:
        path = tmp_path / "custody.xlsx"

        _write_custody(path, [_kaamos("2021-03-01")], preamble=[["Sijoitukset"], ["Tapahtumat 01.03.2021 - 31.03.2021"], [None]])

        written = [list(row) for row in openpyxl.load_workbook(path).active.iter_rows(values_only=True)]
        assert written[3] == list(CUSTODY_HEADER)

    def test_fixture_guard_scenario_statements_keep_their_chain(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Every synthetic statement holds its running balance, except the two built to break it: "chain" (on 2021-03-15) and
        "b52_a13_broken" (on 2021-04-20, after its hidden fee of 04-15)."""
        breaks = {(name, path.name): _chain_breaks(path) for name in sorted(SCENARIOS) for path in _scenario_files(name, tmp_path_factory).cash}

        assert {key: days for key, days in breaks.items() if days} == {("chain", "cash-1.csv"): [_d("2021-03-15")], ("b52_a13_broken", "cash-1.csv"): [_d("2021-04-20")]}
        assert _chain_breaks(SAMPLE_DIR / "danske_bank-cash.csv") == [] and _chain_breaks(SAMPLE_DIR / "danske_bank-gap-cash.csv") == []

    def test_fixture_guard_the_a13_shaped_sets(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Fixture guard: the sets whose cash statement starts after their custody export (A13), read from the files as
        written, are exactly the five the tests read as A13 sets. They are "late" and four B-52 scenarios, and neither
        sample is one. A new A13-shaped scenario must join this list, and its tests must read its opening on the eve of the
        custody export (the developer, 20/10/2026)."""
        shaped = sorted(name for name in SCENARIOS if _a13_shaped(_scenario_files(name, tmp_path_factory).members()))

        assert shaped == ["b52_a13", "b52_a13_broken", "b52_a13_sell", "b52_a13_settled_before", "late"]
        assert [name for name in sorted(SAMPLE_SETS) if _a13_shaped(_members(SAMPLE_SETS[name]))] == []

    def test_fixture_guard_keyed_rows_land_where_the_tests_look(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Newest first: the Saimaa row written after the Aurora row lands above it, so file order alone would cross the pairs."""
        builder = _scenario_files("by_name", tmp_path_factory)

        assert (builder.where["a"], builder.where["s"]) == (("custody", 1, 3), ("custody", 1, 4))
        assert (builder.where["cs"], builder.where["ca"]) == (("cash", 1, 3), ("cash", 1, 4))
        assert builder.row_counts == {("custody", 1): 4, ("cash", 1): 5}

    def test_fixture_guard_custody_variants_change_one_thing(self) -> None:
        """Each variant of the main custody sample changes only the header cell or the columns it names."""
        header, rows = _sample_custody()
        expected = {"br": ([5], []), "space": ([5], []), "valuutta": ([7], []), "no_currency": ([], [7]), "date_cells": ([], [0, 1]), "text_numbers_nbsp": ([], [3, 4, 5, 6]), "text_numbers_space": ([], [3, 4, 5, 6])}

        changes = {}
        for variant in CUSTODY_VARIANTS:
            changed_header, changed_rows = _custody_variant(variant)
            in_header = [index for index, (old, new) in enumerate(zip(header, changed_header, strict=True)) if old != new]
            in_rows = sorted({index for old_row, new_row in zip(rows, changed_rows, strict=True) for index, (old, new) in enumerate(zip(old_row, new_row, strict=True)) if old != new})
            changes[variant] = (in_header, in_rows)

        assert changes == expected

    def test_fixture_guard_dates_and_numbers(self) -> None:
        """The calendar the scenarios reason about (five business days, no holidays) and the Finnish number formats."""
        assert _d("2021-02-28").weekday() == 6
        assert [_business_days_after(_d(day), 5) for day in ("2021-02-28", "2021-03-31", "2021-05-31", "2021-06-30", "2021-03-09", "2020-02-02", "2020-06-26", "2020-10-30", "2021-01-04")] == [
            _d(day) for day in ("2021-03-05", "2021-04-07", "2021-06-07", "2021-07-07", "2021-03-16", "2020-02-07", "2020-07-03", "2020-11-06", "2021-01-11")
        ]
        assert [_fi_amount(Decimal(value)) for value in ("-718.00", "22.50", "-1181.04", "0.42", "6000", "0")] == ["-718", "22,5", "-1181,04", "0,42", "6000", "0"]
        assert _fi_amount(Decimal("-1181.04"), thousands="\u00a0") == "-1\u00a0181,04"
        assert [_number(value) for value in ("-1181.04", "\u22121\u00a0181,04", "22,5", "1 000")] == [Decimal("-1181.04"), Decimal("-1181.04"), Decimal("22.5"), Decimal("1000")]
        assert (_fi_text(-1181.04, thousands="\u00a0", minus="\u2212"), _fi_text(41.2, thousands=" ", minus="-"), _fi_text("EUR", thousands=" ", minus="-")) == ("\u22121\u00a0181,04", "41,2", "EUR")


# =============================================================================
# 16. LINKED CHARGES — project 66, wave P2c (P2 contract §2 and §6)
# =============================================================================
#
# The developer's decisions of 16/11 (``domande-FEE.md``, «Danske: la correzione», «Prima dell'approvazione», answer b):
# - a trade whose sum works out (the test of ``_charges_todo``: 0 < paid − |quantity| × Kurssi <= max(15, gross / 100))
#   is recorded at the gross, and the difference becomes a FEE linked to it: same date, same asset, EUR, negative. Its
#   ``danske_trade_charges_included`` todo goes, and one info notice lists the split trades;
# - a trade whose sum does not work out (a price in another currency) keeps today's proposal: the todo, no FEE;
# - a zero difference: no FEE and no todo, the trade as it is;
# - the tax «Vero osakesäästötililtä» names the withdrawal «Nosto osakesäästötililtä» of its day when there is exactly
#   one; otherwise it stays free. Service fees («Palvelumaksut») stay free;
# - the cash of a trade plus its FEE is today's amount: truths and balances do not move.
#
# The snapshots of version 1.1.0 (HEAD d6e041135) are in ``brim_previous_outputs/broker_danske_bank/``. Every number below
# is worked out by hand from the samples (combined lines in the comments) and cross-checked against qty × Kurssi.

LINK_SAMPLES = {
    "main": "danske_bank-custody.xlsx+danske_bank-cash.csv",
    "gap": "danske_bank-gap-custody-1.xlsx+danske_bank-gap-custody-2.xlsx+danske_bank-gap-cash.csv",
}
WITHDRAWAL_TAX_LABEL = "Vero osakesäästötililtä"
WITHDRAWAL_LABEL = "Nosto osakesäästötililtä"


@dataclass(frozen=True)
class _Split:
    """A trade the plugin splits, named by type, trade date, title and quantity. ``paid`` is today's amount (the sum
    paid, the commission inside), ``gross`` the new one (|quantity| × Kurssi, signed by the trade), ``fee`` the FEE."""

    tx_type: str
    day: str
    title: str
    quantity: str
    paid: str
    gross: str
    fee: str


@dataclass(frozen=True)
class _Kept:
    """A trade that is not split: its amount stays ``paid``. ``todo``: the charges todo stays (the sum does not work out)
    or not (a zero difference)."""

    tx_type: str
    day: str
    title: str
    quantity: str
    paid: str
    todo: bool


@dataclass(frozen=True)
class _LinkExpectation:
    splits: Tuple[_Split, ...]
    kept: Tuple[_Kept, ...]
    tax_links: Tuple[Tuple[str, str, str], ...] = ()  # (day, tax amount, its withdrawal's amount)
    free_taxes: Tuple[Tuple[str, str], ...] = ()  # (day, amount)
    service_fees: Tuple[Tuple[str, str], ...] = ()  # (day, amount): always free
    split_keys: Tuple[str, ...] = ()  # a scenario's keys of the split pairs


SAMPLE_LINKS = {
    "main": _LinkExpectation(
        splits=(
            _Split("BUY", "2020-02-10", "Aurora Metsä Oyj", "50", "-718", "-710", "-8"),  # line 21: 50 × 14.2
            _Split("BUY", "2020-03-02", "Lumi Holding Oyj", "40", "-402", "-394", "-8"),  # line 22: 40 × 9.85
            _Split("SELL", "2020-03-10", "Pohjola Tekniikka Oyj", "-120", "724", "732", "-8"),  # line 23: 120 × 6.1
            _Split("BUY", "2020-03-25", "Saimaa Energia Oyj", "25", "-318", "-310", "-8"),  # line 25: 25 × 12.4 (partial fill)
            _Split("BUY", "2020-03-25", "Saimaa Energia Oyj", "25", "-318", "-310", "-8"),  # line 26: its identical twin
            _Split("BUY", "2020-04-01", "Pohjola Tekniikka Oyj", "20", "-116", "-108", "-8"),  # line 28: 20 × 5.4
            _Split("SELL", "2020-05-05", "Pohjola Tekniikka Oyj", "-80", "532", "540", "-8"),  # line 30: 80 × 6.75
            _Split("SELL", "2020-05-20", "Aurora Metsä Oyj", "-30", "466", "474", "-8"),  # line 31: 30 × 15.8
            _Split("SELL", "2020-06-15", "Lumi Palvelut Oyj", "-50", "152", "160", "-8"),  # line 37: 50 × 3.2
            _Split("BUY", "2020-06-26", "Tunturi Pankki Oyj", "10", "-218", "-210", "-8"),  # line 39: 10 × 21
        ),
        # line 20: 300 × 41.2 = 12 360 against 1181.04 paid, the price is in another currency.
        kept=(_Kept("BUY", "2020-02-03", "Kaamos Robotics AB", "300", "-1181.04", todo=True),),
        tax_links=(("2019-11-04", "-21.3", "-300"), ("2020-06-10", "-45", "-500")),  # lines 12/13 and 35/36: the tax first
        service_fees=(("2019-03-29", "-3.5"), ("2019-06-28", "-3.5"), ("2019-09-30", "-3.5"), ("2019-12-31", "-3.5"), ("2020-03-31", "-3.5"), ("2020-06-30", "-3.5")),
    ),
    "gap": _LinkExpectation(
        splits=(
            _Split("BUY", "2020-09-01", "Aurora Metsä Oyj", "40", "-652", "-644", "-8"),  # line 6: 40 × 16.1
            _Split("SELL", "2020-09-14", "Saimaa Energia Oyj", "-50", "644.5", "652.5", "-8"),  # line 7: 50 × 13.05
            _Split("BUY", "2020-10-30", "Tunturi Pankki Oyj", "10", "-231", "-223", "-8"),  # line 9: 10 × 22.3
            _Split("SELL", "2021-01-20", "Pohjola Tekniikka Oyj", "-60", "424", "432", "-8"),  # line 19: 60 × 7.2
        ),
        # line 18: 100 × 44.8 = 4480 against 428.56 received, the price is in another currency.
        kept=(_Kept("SELL", "2021-01-05", "Kaamos Robotics AB", "-100", "428.56", todo=True),),
        service_fees=(("2020-08-31", "-3.5"), ("2020-09-30", "-3.5"), ("2020-12-31", "-3.5"), ("2021-03-01", "-3.5")),
    ),
}
# The lines of the combined file the split notice shows: the pairs of the split trades (worked out from the samples).
SAMPLE_SPLIT_LINES = {"main": {21, 22, 23, 25, 26, 28, 30, 31, 37, 39}, "gap": {6, 7, 9, 19}}
# The other notices of the samples, as version 1.1.0 emits them (``SAMPLE_NOTICES``): the split changes none of them.
SAMPLE_OTHER_NOTICES = {"main": {"deferred_rows": 1, "deposit_assumed": 2}, "gap": {"deposit_assumed": 2, "excluded_not_yet_settled": 1}}
# The charges todos of the samples once the split is done: only the trade whose sum does not work out keeps its todo.
SAMPLE_TODOS = {"main": Counter({CHARGES: 1, DEMERGER: 2, DEMERGER_OLD: 1}), "gap": Counter({CHARGES: 1})}


def _paired_trade(day: str, name: str, quantity: Any, price: Any, summa: str, *, key: str, kind: str = "Rajakurssi") -> Tuple[Tuple[str, List[Any]], _Cash]:
    """A custody trade and its cash row, settled two business days later: ``Osto``/``Myynti`` + the name, the same amount."""
    value = _business_days_after(_d(day), 2).isoformat()
    label = ("Osto " if Decimal(summa) < 0 else "Myynti ") + name
    return (key, _trade(day, name, quantity, price, float(summa), value=value, kind=kind)), _Cash(value, label, summa, f"cash-{key}")


@scenario("p2c_charges")
def _p2c_charges(builder: _Builder) -> None:
    """Invented trades around the plausibility test (gross 1000: threshold 15; gross 2000: threshold 20, the 1 % branch).

    split: exactly 15 (``edge15``), exactly 1 % (``pct``), a sale (``ssplit``), a decimal price (``dec``), the last
    one-share purchase (``end``); not split, todo kept: 15.01 (``over``), 20.01 on 2000 (``pct_over``), a sale that got
    more than gross (``sneg``); zero difference, no todo: a purchase (``z``) and a sale (``szero``). A ``Tuotto`` (``t``)
    is no trade."""
    trades = [
        _paired_trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, "-200", key="z"),
        _paired_trade("2021-03-02", "Lumi Holding Oyj", 10, 100, "-1015", key="edge15"),
        _paired_trade("2021-03-03", "Kaamos Robotics AB", 10, 100, "-1015.01", key="over"),
        _paired_trade("2021-03-04", "Saimaa Energia Oyj", 20, 100, "-2020", key="pct"),
        _paired_trade("2021-03-05", "Tunturi Pankki Oyj", 20, 100, "-2020.01", key="pct_over"),
        _paired_trade("2021-03-08", "Aurora Metsä Oyj", -5, 20, "105", key="sneg", kind="Päivän kurssi"),
        _paired_trade("2021-03-09", "Lumi Holding Oyj", -5, 100, "500", key="szero", kind="Päivän kurssi"),
        _paired_trade("2021-03-10", "Saimaa Energia Oyj", -10, 100, "990", key="ssplit", kind="Päivän kurssi"),
        _paired_trade("2021-03-11", "Pohjola Tekniikka Oyj", 3, 21.15, "-71.45", key="dec"),
        _paired_trade("2021-03-31", "Kaamos Robotics AB", 1, 30, "-38", key="end"),
    ]
    custody = [row for row, _cash in trades]
    custody.insert(9, ("t", _tuotto("2021-03-12", "Aurora Metsä Oyj", 5, 9)))
    cash = [_Cash("2021-02-01", "Matti Meikäläinen", "10000", "deposit"), *(row for _custody, row in trades), _Cash("2021-03-12", "Aurora Metsä 1234567890", "9", "cash-t"), _Cash("2021-04-30", "Palvelumaksut 04/2021", "-3.5", "fee")]
    builder.add_custody(custody)
    builder.add_cash(sorted(cash, key=lambda row: row.day), opening=OPENING)


@scenario("p2c_tax")
def _p2c_tax(builder: _Builder) -> None:
    """Invented withdrawals and their taxes (both Kaamos purchases split, 8 of charges each).

    03-15: one withdrawal, the tax below it in the file; 03-16: one withdrawal, the tax above it; 03-17: two withdrawals
    (the tax stays free); 03-18: a tax with no withdrawal that day (the one of 03-19 is another day); 03-22: a withdrawal
    and a service fee (the fee stays free); 03-23: two taxes and one withdrawal (each tax has one withdrawal on its day:
    both name it, the literal rule, as Degiro's dividend tax does)."""
    builder.add_custody([("k1", _kaamos("2021-03-01")), ("k2", _kaamos("2021-03-31"))])
    builder.add_cash(
        [
            _Cash("2021-02-01", "Matti Meikäläinen", "5000", "deposit"),
            _Cash("2021-03-03", "Osto Kaamos Robotics AB", "-38", "cash-k1"),
            _Cash("2021-03-15", WITHDRAWAL_LABEL, "-100", "wa"),
            _Cash("2021-03-15", WITHDRAWAL_TAX_LABEL, "-10", "ta"),
            _Cash("2021-03-16", WITHDRAWAL_TAX_LABEL, "-20", "tb"),
            _Cash("2021-03-16", WITHDRAWAL_LABEL, "-200", "wb"),
            _Cash("2021-03-17", WITHDRAWAL_TAX_LABEL, "-30", "tc"),
            _Cash("2021-03-17", WITHDRAWAL_LABEL, "-300", "wc1"),
            _Cash("2021-03-17", WITHDRAWAL_LABEL, "-310", "wc2"),
            _Cash("2021-03-18", WITHDRAWAL_TAX_LABEL, "-40", "td"),
            _Cash("2021-03-19", WITHDRAWAL_LABEL, "-400", "wd"),
            _Cash("2021-03-22", WITHDRAWAL_LABEL, "-500", "we"),
            _Cash("2021-03-22", "Palvelumaksut 03/2021", "-3.5", "fe"),
            _Cash("2021-03-23", WITHDRAWAL_TAX_LABEL, "-50", "tf1"),
            _Cash("2021-03-23", WITHDRAWAL_TAX_LABEL, "-60", "tf2"),
            _Cash("2021-03-23", WITHDRAWAL_LABEL, "-600", "wf"),
            _Cash("2021-04-02", "Osto Kaamos Robotics AB", "-38", "cash-k2"),
        ],
        opening=OPENING,
    )


@scenario("p2c_nothing_to_split")
def _p2c_nothing_to_split(builder: _Builder) -> None:
    """Two trades, neither split: a zero difference (``z``) and 15.01 over a one-share gross of 30 (``o``)."""
    trades = [_paired_trade("2021-03-01", "Aurora Metsä Oyj", 10, 20, "-200", key="z"), _paired_trade("2021-03-31", "Kaamos Robotics AB", 1, 30, "-45.01", key="o")]
    builder.add_custody([row for row, _cash in trades])
    builder.add_cash([_Cash("2021-02-01", "Matti Meikäläinen", "5000", "deposit"), *(row for _custody, row in trades)], opening=OPENING)


@scenario("p2c_price_zero")
def _p2c_price_zero(builder: _Builder) -> None:
    """A purchase at Kurssi 0 (``z0``): quantity × price is 0 and explains nothing (the coordinator's choice, P2c), so it is
    not split, whatever the 8 paid. The one-share Kaamos purchase (``end``) closes the segment and is split."""
    trades = [_paired_trade("2021-03-01", "Aurora Metsä Oyj", 10, 0, "-8", key="z0"), _paired_trade("2021-03-31", "Kaamos Robotics AB", 1, 30, "-38", key="end")]
    builder.add_custody([row for row, _cash in trades])
    builder.add_cash([_Cash("2021-02-01", "Matti Meikäläinen", "5000", "deposit"), *(row for _custody, row in trades)], opening=OPENING)


SCENARIO_LINKS = {
    "p2c_charges": _LinkExpectation(
        splits=(
            _Split("BUY", "2021-03-02", "Lumi Holding Oyj", "10", "-1015", "-1000", "-15"),
            _Split("BUY", "2021-03-04", "Saimaa Energia Oyj", "20", "-2020", "-2000", "-20"),
            _Split("SELL", "2021-03-10", "Saimaa Energia Oyj", "-10", "990", "1000", "-10"),
            _Split("BUY", "2021-03-11", "Pohjola Tekniikka Oyj", "3", "-71.45", "-63.45", "-8"),
            _Split("BUY", "2021-03-31", "Kaamos Robotics AB", "1", "-38", "-30", "-8"),
        ),
        kept=(
            _Kept("BUY", "2021-03-01", "Aurora Metsä Oyj", "10", "-200", todo=False),
            _Kept("BUY", "2021-03-03", "Kaamos Robotics AB", "10", "-1015.01", todo=True),
            _Kept("BUY", "2021-03-05", "Tunturi Pankki Oyj", "20", "-2020.01", todo=True),
            _Kept("SELL", "2021-03-08", "Aurora Metsä Oyj", "-5", "105", todo=True),
            _Kept("SELL", "2021-03-09", "Lumi Holding Oyj", "-5", "500", todo=False),
        ),
        service_fees=(("2021-04-30", "-3.5"),),
        split_keys=("edge15", "pct", "ssplit", "dec", "end"),
    ),
    "p2c_tax": _LinkExpectation(
        splits=(_Split("BUY", "2021-03-01", "Kaamos Robotics AB", "1", "-38", "-30", "-8"), _Split("BUY", "2021-03-31", "Kaamos Robotics AB", "1", "-38", "-30", "-8")),
        kept=(),
        tax_links=(("2021-03-15", "-10", "-100"), ("2021-03-16", "-20", "-200"), ("2021-03-23", "-50", "-600"), ("2021-03-23", "-60", "-600")),
        free_taxes=(("2021-03-17", "-30"), ("2021-03-18", "-40")),
        service_fees=(("2021-03-22", "-3.5"),),
        split_keys=("k1", "k2"),
    ),
    "p2c_price_zero": _LinkExpectation(
        splits=(_Split("BUY", "2021-03-31", "Kaamos Robotics AB", "1", "-38", "-30", "-8"),),
        kept=(_Kept("BUY", "2021-03-01", "Aurora Metsä Oyj", "10", "-8", todo=True),),
        split_keys=("end",),
    ),
    "p2c_nothing_to_split": _LinkExpectation(
        splits=(),
        kept=(_Kept("BUY", "2021-03-01", "Aurora Metsä Oyj", "10", "-200", todo=False), _Kept("BUY", "2021-03-31", "Kaamos Robotics AB", "1", "-45.01", todo=True)),
    ),
}

LINK_SETS = [
    pytest.param("sample", "main", id="main"),
    pytest.param("sample", "gap", id="gap"),
    pytest.param("scenario", "p2c_charges", id="p2c_charges"),
    pytest.param("scenario", "p2c_tax", id="p2c_tax"),
    pytest.param("scenario", "p2c_nothing_to_split", id="p2c_nothing_to_split"),
    pytest.param("scenario", "p2c_price_zero", id="p2c_price_zero"),
]


def _link_expectation(source: str, name: str) -> _LinkExpectation:
    return SAMPLE_LINKS[name] if source == "sample" else SCENARIO_LINKS[name]


def _trade_indices(output: BRIMParseOutput, tx_type: str, day: str, title: str, quantity: str, cash: str) -> List[int]:
    """The positions of the trades of ``output`` with these values (identical partial fills give several)."""
    names = _names(output)
    wanted = (tx_type, _d(day), title, Decimal(quantity), Decimal(cash))
    return [index for index, tx in enumerate(output.transactions) if tx.cash is not None and (tx.type.value, tx.date, names.get(tx.asset_id), tx.quantity, tx.cash.amount) == wanted]


def _cash_rows(output: BRIMParseOutput, tx_type: str, day: str, amount: str) -> List[Any]:
    return [tx for tx in output.transactions if tx.type.value == tx_type and tx.date == _d(day) and tx.cash is not None and tx.cash.amount == Decimal(amount)]


def _children(output: BRIMParseOutput) -> Dict[str, List[Any]]:
    """``{ref: the rows that name it as parent}``."""
    found: Dict[str, List[Any]] = defaultdict(list)
    for tx in output.transactions:
        if tx.parent_ref:
            found[tx.parent_ref].append(tx)
    return found


def _split_fee_problem(split: _Split, trade: Any, children: Dict[str, List[Any]]) -> Optional[str]:
    """What is wrong with the FEE of a split trade: exactly one charge names it, a FEE of −charges in EUR on the trade's
    date, asset and broker, tagged like every Danske row (the report-set history is found by ``danske_bank``). None when
    it holds."""
    fees = children.get(trade.ref, []) if trade.ref else []
    if len(fees) != 1:
        return f"{split}: {len(fees)} charge(s) name the trade (ref {trade.ref!r}), one FEE expected"
    fee = fees[0]
    got = (fee.type.value, fee.date, fee.cash.amount if fee.cash else None, fee.cash.code if fee.cash else None, fee.asset_id, fee.broker_id, list(fee.tags or []))
    want = ("FEE", trade.date, Decimal(split.fee), "EUR", trade.asset_id, trade.broker_id, TAGS)
    return f"{split}: its FEE is {got}, expected {want}" if got != want else None


def _split_trade_problems(output: BRIMParseOutput, expect: _LinkExpectation, children: Dict[str, List[Any]], problems: List[str]) -> None:
    """Each split trade at its gross with exactly one FEE naming it; each kept trade at its amount, named by nothing; no
    other trade. Identical partial fills are claimed one by one, never by position."""
    names = _names(output)
    unclaimed = [index for index, tx in enumerate(output.transactions) if tx.type.value in ("BUY", "SELL")]

    def claim(tx_type: str, day: str, title: str, quantity: str, cash: str) -> Optional[Any]:
        for index in _trade_indices(output, tx_type, day, title, quantity, cash):
            if index in unclaimed:
                unclaimed.remove(index)
                return output.transactions[index]
        problems.append(f"no {tx_type} {day} {title} × {quantity} at {cash} EUR in the output")
        return None

    for split in expect.splits:
        trade = claim(split.tx_type, split.day, split.title, split.quantity, split.gross)
        problem = _split_fee_problem(split, trade, children) if trade is not None else None
        if problem:
            problems.append(problem)
    for kept in expect.kept:
        trade = claim(kept.tx_type, kept.day, kept.title, kept.quantity, kept.paid)
        if trade is not None and trade.ref and children.get(trade.ref):
            problems.append(f"{kept}: not split, yet {len(children[trade.ref])} row(s) name it")
    for index in unclaimed:
        tx = output.transactions[index]
        problems.append(f"a trade no expectation names: {tx.type.value} {tx.date} {names.get(tx.asset_id)} × {tx.quantity} at {tx.cash.amount if tx.cash else None}")


def _one_cash_row(output: BRIMParseOutput, tx_type: str, day: str, amount: str, problems: List[str]) -> Optional[Any]:
    rows = _cash_rows(output, tx_type, day, amount)
    if len(rows) != 1:
        problems.append(f"{len(rows)} {tx_type} rows on {day} at {amount}, one expected")
        return None
    return rows[0]


def _tax_and_fee_problems(output: BRIMParseOutput, expect: _LinkExpectation, problems: List[str]) -> None:
    for day, tax_amount, withdrawal_amount in expect.tax_links:
        tax = _one_cash_row(output, "TAX", day, tax_amount, problems)
        withdrawal = _one_cash_row(output, "WITHDRAWAL", day, withdrawal_amount, problems)
        if tax is None or withdrawal is None:
            continue
        if not withdrawal.ref or tax.parent_ref != withdrawal.ref:
            problems.append(f"the TAX {day} {tax_amount} should name the WITHDRAWAL {withdrawal_amount}: parent_ref={tax.parent_ref!r}, its ref={withdrawal.ref!r}")
        if (tax.asset_id, tax.broker_id) != (withdrawal.asset_id, withdrawal.broker_id):
            problems.append(f"the TAX {day} {tax_amount} should have its withdrawal's asset and broker")
    for day, amount in expect.free_taxes:
        tax = _one_cash_row(output, "TAX", day, amount, problems)
        if tax is not None and tax.parent_ref:
            problems.append(f"the TAX {day} {amount} should stay free, it names {tax.parent_ref!r}")
    for day, amount in expect.service_fees:
        fee = _one_cash_row(output, "FEE", day, amount, problems)
        if fee is not None and (fee.parent_ref or not (fee.description or "").startswith("Palvelumaksut")):
            problems.append(f"the service fee {day} {amount} should stay free: parent_ref={fee.parent_ref!r}, description {fee.description!r}")


def _charge_link_problems(output: BRIMParseOutput, expect: _LinkExpectation) -> List[str]:
    """How the links of ``output`` differ from ``expect``, exhaustively: every trade, FEE and TAX is declared."""
    problems: List[str] = []
    children = _children(output)
    _split_trade_problems(output, expect, children, problems)
    _tax_and_fee_problems(output, expect, problems)
    kinds = Counter(tx.type.value for tx in output.transactions)
    if kinds["FEE"] != len(expect.splits) + len(expect.service_fees):
        problems.append(f"{kinds['FEE']} FEE rows, expected {len(expect.splits)} split charges + {len(expect.service_fees)} service fees")
    if kinds["TAX"] != len(expect.tax_links) + len(expect.free_taxes):
        problems.append(f"{kinds['TAX']} TAX rows, expected {len(expect.tax_links)} linked + {len(expect.free_taxes)} free")
    problems += [f"a row that is not a FEE or a TAX names a parent: {tx.type.value} {tx.date} {tx.description}" for tx in output.transactions if tx.parent_ref and tx.type.value not in ("FEE", "TAX")]
    return problems


def _split_trades(output: BRIMParseOutput, expect: _LinkExpectation) -> List[int]:
    """The positions of the split trades (at their gross), each partial fill once."""
    found: List[int] = []
    for split in expect.splits:
        found += [index for index in _trade_indices(output, split.tx_type, split.day, split.title, split.quantity, split.gross) if index not in found][:1]
    return found


def _new_fees(output: BRIMParseOutput, trades: Sequence[int]) -> List[int]:
    """The positions of the FEE rows that name one of ``trades``."""
    refs = {output.transactions[index].ref for index in trades if output.transactions[index].ref}
    return [index for index, tx in enumerate(output.transactions) if tx.type.value == "FEE" and tx.parent_ref in refs]


def _link_row_key(tx_type: str, day: str, amount: str) -> RowKey:
    """A Danske row for ``assert_expected_charge_links``: no ISIN nor symbol is extracted, so the identifier is None."""
    return (tx_type, day, amount, "EUR", None)


async def _gap_fix_digest(output: BRIMParseOutput) -> Tuple[date, Dict[str, Any], Dict[str, Any]]:
    """H0, and per checkpoint and verification of the first-import gap-fix: the cash rows, the corrections, what is left
    unexplained (checkpoints), and ok (verifications)."""
    response, history_start, _selection, titles = await _first_import_gap_fix(output)
    checkpoints = {result.as_of.isoformat(): (_gap_fix_cash(result), _gap_fix_proposals(result, titles), list(result.explanation.unexplained_cash)) for result in response.checkpoints}
    verifications = {result.as_of.isoformat(): (result.ok, _gap_fix_cash(result)) for result in response.verifications}
    return history_start, checkpoints, verifications


# The gap-fix of a first import on each sample, as version 1.1.0 gives it (measured at HEAD d6e041135). The split moves
# no cent between days: a FEE is dated as its trade.
SAMPLE_GAP_FIX = {
    "main": (
        _d("2020-02-03"),
        {
            "2020-02-02": (
                {"EUR": (Decimal("2699.50"), Decimal("0"), Decimal("2699.50"))},
                [("ADJUSTMENT", None, "Aurora Metsä Oyj", Decimal("100")), ("ADJUSTMENT", None, "Lumi Holding Oyj", Decimal("60")), ("ADJUSTMENT", None, "Pohjola Tekniikka Oyj", Decimal("180")), ("DEPOSIT", Decimal("2699.50"), None, Decimal("0"))],
                [],
            )
        },
        {"2020-06-26": (True, {"EUR": (Decimal("1776.46"), Decimal("1776.46"), Decimal("0"))})},
    ),
    "gap": (
        _d("2020-09-01"),
        {
            "2020-08-31": ({"EUR": (Decimal("3519.86"), Decimal("0"), Decimal("3519.86"))}, [("ADJUSTMENT", None, "Saimaa Energia Oyj", Decimal("50")), ("DEPOSIT", Decimal("3519.86"), None, Decimal("0"))], []),
            "2021-01-04": (
                {"EUR": (Decimal("3482.36"), Decimal("3774.36"), Decimal("-292.00"))},
                [("ADJUSTMENT", None, "Aurora Metsä Oyj", Decimal("150")), ("ADJUSTMENT", None, "Kaamos Robotics AB", Decimal("100")), ("ADJUSTMENT", None, "Pohjola Tekniikka Oyj", Decimal("60")), ("WITHDRAWAL", Decimal("-292.00"), None, Decimal("0"))],
                [],
            ),
        },
        {"2021-02-26": (True, {"EUR": (Decimal("4363.42"), Decimal("4363.42"), Decimal("0"))})},
    ),
}


class TestLinkedCharges:
    """Project 66, wave P2c (P2 contract §6): the commission inside a Danske trade is split out as a linked FEE when the
    sum works out; the withdrawal tax names its withdrawal. Red before P2c unless the name says guard."""

    # -- links and free charges ---------------------------------------------------------------------------------------

    @pytest.mark.parametrize(("source", "name"), LINK_SETS)
    def test_each_charge_names_its_parent_or_stays_free(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """RED before P2c: every FEE and TAX declared. A split FEE names its trade (same date, asset, broker, EUR); the
        withdrawal tax names its one withdrawal; the tax of a day with zero or two withdrawals and every service fee stay
        free. On ``p2c_nothing_to_split`` (no trade splits, no tax) it is green today: the guard that nothing splits."""
        _table, _path, output = _combined(source, name, tmp_path_factory)

        assert output.validation_issues == [], f"{name}: {output.validation_issues}"
        problems = _charge_link_problems(output, _link_expectation(source, name))
        assert not problems, f"{name}: {len(problems)} unexpected link(s):\n  " + "\n  ".join(problems)
        assert_charge_link_structure(output, f"{PLUGIN_CODE} [{name}]")

    @pytest.mark.parametrize("name", ["gap", "p2c_tax"])
    def test_the_shared_expectation_agrees(self, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """RED before P2c. The same links through the shared checker of every plugin (``assert_expected_charge_links``),
        on the sets where each key names one row (the main sample has identical partial fills: the test above)."""
        source = "sample" if name == "gap" else "scenario"
        expect = _link_expectation(source, name)
        _table, _path, output = _combined(source, name, tmp_path_factory)

        linked = [(_link_row_key("FEE", split.day, split.fee), _link_row_key(split.tx_type, split.day, split.gross)) for split in expect.splits]
        linked += [(_link_row_key("TAX", day, tax), _link_row_key("WITHDRAWAL", day, withdrawal)) for day, tax, withdrawal in expect.tax_links]
        free = [_link_row_key("TAX", day, amount) for day, amount in expect.free_taxes] + [_link_row_key("FEE", day, amount) for day, amount in expect.service_fees]
        assert_expected_charge_links(output, f"{PLUGIN_CODE} [{name}]", linked=linked, free=free)

    def test_the_identical_partial_fills_each_get_their_own_fee(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """RED before P2c. The two Saimaa fills of 2020-03-25 (main, lines 25 and 26) are alike in every value: each is
        split, each has its own name, and their two FEEs name one each."""
        _table, _path, output = _sample_parse("main", tmp_path_factory)
        twins = [output.transactions[index] for index in _trade_indices(output, "BUY", "2020-03-25", "Saimaa Energia Oyj", "25", "-310")]
        assert len(twins) == 2, f"two fills at the gross of 310 expected, got {len(twins)}"

        refs = {tx.ref for tx in twins}
        assert None not in refs and len(refs) == 2, f"each fill has its own name: {refs}"
        fees = [tx for tx in output.transactions if tx.type.value == "FEE" and tx.parent_ref in refs]
        assert sorted(tx.parent_ref for tx in fees) == sorted(refs), "one FEE names each fill"

    # -- the split arithmetic -----------------------------------------------------------------------------------------

    @pytest.mark.parametrize("name", ["main", "gap"])
    def test_the_split_keeps_the_sum_of_each_trade(self, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """RED before P2c. Per split trade: the trade at the gross, the FEE at −charges, trade + FEE = the snapshot's amount
        (the sum paid); the gross is |quantity| × Kurssi of its pair in the combined file. The cash of the whole output
        equals the snapshot's."""
        expect = SAMPLE_LINKS[name]
        previous = load_previous_snapshot(PLUGIN_CODE, LINK_SAMPLES[name], BROKER_ID)
        table, _path, output = _sample_parse(name, tmp_path_factory)
        records = _records(table)
        previous_names = {asset_id: info.extracted_name for asset_id, info in previous.extracted_assets.items()}
        paid = Counter((tx.type.value, tx.date, previous_names.get(tx.asset_id), tx.quantity, tx.cash.amount) for tx in previous.transactions if tx.type.value in ("BUY", "SELL"))
        assert len(expect.splits) == {"main": 10, "gap": 4}[name], "presence barrier: the hand-counted splits"

        for split in expect.splits:
            key = (split.tx_type, _d(split.day), split.title, Decimal(split.quantity), Decimal(split.paid))
            assert paid[key] > 0, f"premise: the snapshot holds {key}"
            paid[key] -= 1
            pair = [record for record in records if record["lf_row_kind"] == "pair" and _from_fi_date(record["custody:Kauppapäivä"]) == _d(split.day) and record["custody:Sijoituskohde"] == split.title and _number(record["custody:Määrä"]) == Decimal(split.quantity)]
            assert pair, f"premise: {split} is a pair of the combined file"
            gross = abs(_number(pair[0]["custody:Määrä"]) * _number(pair[0]["custody:Kurssi"]))
            assert abs(Decimal(split.gross)) == gross and Decimal(split.gross) - Decimal(split.paid) == -Decimal(split.fee), f"premise: {split} is |quantity| × Kurssi and the difference"
        trades = _split_trades(output, expect)
        assert len(trades) == len(expect.splits), f"{name}: {len(trades)} trades at their gross, {len(expect.splits)} expected"
        for split, index in zip(expect.splits, trades, strict=True):
            trade = output.transactions[index]
            fees = [tx for tx in output.transactions if trade.ref and tx.parent_ref == trade.ref]
            assert [(tx.type.value, tx.cash.amount) for tx in fees] == [("FEE", Decimal(split.fee))], f"{split}: its FEE"
            assert trade.cash.amount + fees[0].cash.amount == Decimal(split.paid), f"{split}: trade + FEE is the sum paid"
        total = sum((tx.cash.amount for tx in output.transactions if tx.cash is not None), Decimal(0))
        assert total == sum((tx.cash.amount for tx in previous.transactions if tx.cash is not None), Decimal(0)), "the cash of the output is the snapshot's"

    @pytest.mark.parametrize("name", ["p2c_charges", "p2c_tax"])
    def test_the_split_keeps_the_sum_of_each_invented_trade(self, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """RED before P2c. Per split trade of the invented sets: its pair's cash in the combined file is the sum paid, the
        trade + its FEE is that sum, and the whole output's cash is the combined file's."""
        expect = SCENARIO_LINKS[name]
        builder, table, _path, output = _scenario_parse(name, tmp_path_factory)
        records = _records(table)

        for split, key in zip(expect.splits, expect.split_keys, strict=True):
            record = builder.row(records, key)
            assert (record["lf_row_kind"], _number(record["cash:Määrä"])) == ("pair", Decimal(split.paid)), f"premise: {key} is a pair at {split.paid}"
            assert abs(_number(record["custody:Määrä"]) * _number(record["custody:Kurssi"])) == abs(Decimal(split.gross)), f"premise: {key} gross"
            indices = _trade_indices(output, split.tx_type, split.day, split.title, split.quantity, split.gross)
            assert len(indices) == 1, f"{key}: the trade at the gross {split.gross}, got {len(indices)}"
            trade = output.transactions[indices[0]]
            fees = [tx for tx in output.transactions if trade.ref and tx.parent_ref == trade.ref]
            assert [tx.cash.amount for tx in fees] == [Decimal(split.fee)], f"{key}: its FEE"
            assert trade.cash.amount + fees[0].cash.amount == _number(record["cash:Määrä"]), f"{key}: trade + FEE is the sum paid"
        owed = sum((_number(record["cash:Määrä"]) for record in records if record["lf_row_kind"] in ("pair", "standalone") and record["cash:Määrä"]), Decimal(0))
        assert sum((tx.cash.amount for tx in output.transactions if tx.cash is not None), Decimal(0)) == owed, "the cash of the output is the combined file's"

    # -- the todo -----------------------------------------------------------------------------------------------------

    @pytest.mark.parametrize(("source", "name"), LINK_SETS)
    def test_only_a_trade_whose_sum_does_not_work_out_keeps_its_todo(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """RED before P2c (green on nothing but the trades kept). The charges todo stays on the trades whose sum does not
        work out, with its split hint and no amount; a split trade and a zero difference have none."""
        expect = _link_expectation(source, name)
        _table, _path, output = _combined(source, name, tmp_path_factory)
        todos = [todo for todo in output.field_todos if todo.reason_code == CHARGES]

        with_todo = sorted(index for kept in expect.kept if kept.todo for index in _trade_indices(output, kept.tx_type, kept.day, kept.title, kept.quantity, kept.paid))
        assert len(with_todo) == sum(1 for kept in expect.kept if kept.todo), "presence barrier: the trades that keep their todo are in the output"
        assert sorted(todo.tx_index for todo in todos) == with_todo, f"{name}: charges todos on {[(output.transactions[todo.tx_index].date, output.transactions[todo.tx_index].description) for todo in todos]}"
        for todo in todos:
            assert (todo.context or {}).get("split_hint") == "trade_charges", f"{name}: {todo.context}"
            # A price in another currency or of 0: quantity × price explains nothing, so there is no amount to suggest (21/11).
            assert "charges" not in (todo.context or {}), f"{name}: {todo.context}"
            assert not any(GROSS_SUGGESTION in item for item in (todo.context or {}).get("split_suggestions", [])), f"{name}: {todo.context}"

    @pytest.mark.parametrize("name", ["main", "gap"])
    def test_the_sample_todos(self, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """RED before P2c: one charges todo per sample (the Kaamos trade); the demerger todos stay, on their ADJUSTMENT rows."""
        _table, _path, output = _sample_parse(name, tmp_path_factory)

        assert Counter(todo.reason_code for todo in output.field_todos) == SAMPLE_TODOS[name]
        for todo in output.field_todos:
            expected = "ADJUSTMENT" if todo.reason_code in (DEMERGER, DEMERGER_OLD) else ("BUY", "SELL")
            assert output.transactions[todo.tx_index].type.value in expected, f"{todo.reason_code} on {output.transactions[todo.tx_index].type.value}"

    # -- the info notice ----------------------------------------------------------------------------------------------

    @pytest.mark.parametrize(("source", "name"), [param for param in LINK_SETS if _link_expectation(*param.values).splits])
    def test_one_info_notice_lists_the_split_trades(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """RED before P2c: one ``danske_trade_charges_split`` info notice, its count the split trades, its evidence their
        pairs in the combined file."""
        expect = _link_expectation(source, name)
        if source == "sample":
            table, _path, output = _sample_parse(name, tmp_path_factory)
            lines = SAMPLE_SPLIT_LINES[name]
            records = _records(table)
            assert all(records[line - 2]["lf_row_kind"] == "pair" for line in lines), "premise: the hand-counted lines are pairs"
        else:
            builder, table, _path, output = _scenario_parse(name, tmp_path_factory)
            lines = _keyed_lines(builder, _records(table), expect.split_keys)
        assert len(lines) == len(expect.splits), "premise: one line per split trade"

        notices = [notice for notice in output.warnings if notice.code == SPLIT_NOTICE]
        assert len(notices) == 1, f"{name}: one {SPLIT_NOTICE} notice expected, the parse noted {_codes(output.warnings)}"
        notice = notices[0]
        count = len(expect.splits)
        assert (notice.severity, (notice.context or {}).get("count")) == ("info", count)
        assert notice.message and notice.message.strip(), "a Finnish message, as every notice of the plugin"
        assert _shown(notice) == lines
        for evidence in notice.evidence:
            assert evidence.title.strip() and evidence.comment and evidence.comment.strip() and len(evidence.row_numbers) == len(evidence.rows)

    def test_no_notice_and_no_fee_when_nothing_splits(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Guard (green today, must stay): a set whose trades are a zero difference and a sum over the threshold has no
        split notice and no FEE."""
        _builder, _table, _path, output = _scenario_parse("p2c_nothing_to_split", tmp_path_factory)
        assert [tx.type.value for tx in output.transactions].count("BUY") == 2, "presence barrier: both trades are imported"

        assert SPLIT_NOTICE not in _codes(output.warnings)
        assert [tx for tx in output.transactions if tx.type.value == "FEE"] == []

    @pytest.mark.parametrize("name", ["main", "gap"])
    def test_guard_the_other_notices_are_unchanged(self, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Guard (green today, must stay): besides the split notice, the notices of version 1.1.0, with their counts."""
        _table, _path, output = _sample_parse(name, tmp_path_factory)

        others = {notice.code: (notice.context or {}).get("count") for notice in output.warnings if notice.code != SPLIT_NOTICE}
        assert others == SAMPLE_OTHER_NOTICES[name]

    # -- the snapshot of version 1.1.0 --------------------------------------------------------------------------------

    @pytest.mark.parametrize("name", ["main", "gap"])
    def test_the_snapshot_differs_by_the_split_trades_and_their_fees_only(self, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """RED before P2c. Not «only the names change» (P2 contract §6): take the new FEEs out, and every other row equals
        the snapshot's, in order, apart from ``ref``/``parent_ref``; a split trade differs in its cash amount alone (the
        gross); each FEE comes after its trade. The extracted assets are the snapshot's."""
        expect = SAMPLE_LINKS[name]
        previous = load_previous_snapshot(PLUGIN_CODE, LINK_SAMPLES[name], BROKER_ID)
        _table, _path, output = _sample_parse(name, tmp_path_factory)
        trades = _split_trades(output, expect)
        fees = _new_fees(output, trades)
        assert (len(trades), len(fees)) == (len(expect.splits), len(expect.splits)), f"{name}: {len(trades)} trades at their gross and {len(fees)} FEEs naming them, {len(expect.splits)} each expected"

        rest = [tx for index, tx in enumerate(output.transactions) if index not in fees]
        assert len(rest) == len(previous.transactions), f"{len(rest)} rows besides the new FEEs, the snapshot has {len(previous.transactions)}"
        assert output.extracted_assets == previous.extracted_assets
        names = _names(output)
        gross = {(split.tx_type, _d(split.day), split.title, Decimal(split.quantity), Decimal(split.paid)): Decimal(split.gross) for split in expect.splits}
        problems = []
        for index, (before, after) in enumerate(zip(previous.transactions, rest, strict=True)):
            old, new = before.model_dump(mode="json", exclude=set(LINK_FIELDS)), after.model_dump(mode="json", exclude=set(LINK_FIELDS))
            changed = sorted(field for field in old if old[field] != new[field])
            key = (before.type.value, before.date, names.get(before.asset_id), before.quantity, before.cash.amount if before.cash else None)
            if key in gross:
                if changed != ["cash"] or (after.cash.code, after.cash.amount) != (before.cash.code, gross[key]):
                    problems.append(f"#{index} {key}: should change its cash to {gross[key]} only, changed {changed}: {after.cash}")
            elif changed:
                problems.append(f"#{index} {key}: should not change, changed {changed}")
        assert not problems, f"{name}:\n  " + "\n  ".join(problems)
        positions = {output.transactions[index].ref: index for index in trades}
        assert all(positions[output.transactions[index].parent_ref] < index for index in fees), "each FEE comes after its trade"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", ["main", "gap"])
    async def test_reimport_recognises_every_row_but_the_split_trades_and_their_fees(self, name: str) -> None:
        """RED before P2c (P2 contract §2.5): over the rows 1.1.0 saved, the rows that are not split trades are found as
        duplicates; the split trades (their amount changed) and the new FEEs are not: the expected «delete and reimport»."""
        expect = SAMPLE_LINKS[name]
        report = await sample_reimport_report(_danske(), LINK_SAMPLES[name])
        output = report.output
        trades = _split_trades(output, expect)
        changed = frozenset([*trades, *_new_fees(output, trades)])
        assert len(changed) == 2 * len(expect.splits), f"{name}: {len(changed)} split trades and FEEs, {2 * len(expect.splits)} expected"

        assert sorted(report.unique) == sorted(changed), "the reimport adds exactly the split trades and their FEEs"
        assert report.duplicates == frozenset(range(len(output.transactions))) - changed, "every other row is recognised"

    # -- truths and balances ------------------------------------------------------------------------------------------

    @pytest.mark.asyncio
    @pytest.mark.parametrize("name", ["main", "gap"])
    async def test_guard_the_gap_fix_of_a_first_import_is_unchanged(self, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Guard (green today, must stay): the gap-fix of a first import, end to end, finds the same cash on both sides,
        the same corrections and the same verifications as with 1.1.0. The truths come from the combined file, and the
        ledger sums trade + FEE on the trade date: the split moves nothing."""
        _table, _path, output = _sample_parse(name, tmp_path_factory)

        assert await _gap_fix_digest(output) == SAMPLE_GAP_FIX[name]

    @pytest.mark.parametrize(("source", "name"), [param for param in LINK_SETS if param.values[0] == "scenario"])
    def test_guard_the_ledger_meets_the_verification(self, source: str, name: str, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Guard (green today, must stay): the opening plus every transaction dated after it, up to the verification day,
        is the verification: the FEEs carry what the trades lose."""
        _table, _path, output = _combined(source, name, tmp_path_factory)
        [opening] = output.checkpoints
        [verification] = output.verifications

        ledger = _money(opening.cash)["EUR"] + sum((tx.cash.amount for tx in output.transactions if tx.cash is not None and opening.as_of < tx.date <= verification.as_of), Decimal(0))
        assert ledger == _money(verification.cash)["EUR"]

    # -- the withdrawal tax keeps its place ---------------------------------------------------------------------------

    def test_a_tax_keeps_its_place_on_either_side_of_its_withdrawal(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """RED before P2c on the links (the order is green today, the guard). On 03-15 the tax is above its withdrawal in
        the combined file, on 03-16 below it: the output keeps the file order, and both taxes name their withdrawal."""
        builder, table, _path, output = _scenario_parse("p2c_tax", tmp_path_factory)
        records = _records(table)
        problems: List[str] = []

        for day, tax_key, withdrawal_key, tax_amount, withdrawal_amount in (("2021-03-15", "ta", "wa", "-10", "-100"), ("2021-03-16", "tb", "wb", "-20", "-200")):
            tax, withdrawal = _one_cash_row(output, "TAX", day, tax_amount, problems), _one_cash_row(output, "WITHDRAWAL", day, withdrawal_amount, problems)
            assert tax is not None and withdrawal is not None, problems
            file_order = _line_of(records, builder.row(records, tax_key)) < _line_of(records, builder.row(records, withdrawal_key))
            assert (output.transactions.index(tax) < output.transactions.index(withdrawal)) == file_order, f"{day}: the output keeps the file order"
            assert withdrawal.ref and tax.parent_ref == withdrawal.ref, f"{day}: the tax names its withdrawal: parent_ref={tax.parent_ref!r}, ref={withdrawal.ref!r}"
        tax_first = [_line_of(records, builder.row(records, key)) < _line_of(records, builder.row(records, other)) for key, other in (("ta", "wa"), ("tb", "wb"))]
        assert sorted(tax_first) == [False, True], "presence barrier: one tax above its withdrawal, one below"

    # -- the coordinator's choices of P2c (21/11), pinned ---------------------------------------------------------------

    def test_a_price_of_zero_explains_nothing(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """A purchase at Kurssi 0: quantity × price is 0, so the sum is not split (no FEE, the 8 paid stays the trade's
        cash) and the trade keeps its charges todo with the split hint — with no amount to suggest: no «charges», no
        «Määrä × kurssi» figure (the developer, 21/11). Red until ``_charges_todo`` drops its plausible branch."""
        builder, table, _path, output = _scenario_parse("p2c_price_zero", tmp_path_factory)
        record = builder.row(_records(table), "z0")
        assert (record["lf_row_kind"], _number(record["custody:Kurssi"])) == ("pair", Decimal(0)), "premise: the purchase at price 0 pairs"

        [index] = _trade_indices(output, "BUY", "2021-03-01", "Aurora Metsä Oyj", "10", "-8")
        trade = output.transactions[index]
        assert not trade.ref or [tx for tx in output.transactions if tx.parent_ref == trade.ref] == [], "no charge names it"
        [todo] = [todo for todo in output.field_todos if todo.tx_index == index]
        context = todo.context or {}
        assert (todo.reason_code, context.get("split_hint")) == (CHARGES, "trade_charges")
        assert context.get("split_suggestions"), "presence barrier: the todo still offers its suggestions"

        assert "charges" not in context, f"a price of 0 explains nothing: no amount to suggest, got charges={context.get('charges')!r}"
        assert not any(GROSS_SUGGESTION in item for item in context["split_suggestions"]), f"no «{GROSS_SUGGESTION}» figure: {context['split_suggestions']}"

    def test_two_taxes_with_one_withdrawal_both_name_it(self, tmp_path_factory: pytest.TempPathFactory) -> None:
        """Two taxes on a day with one withdrawal: each tax has exactly one withdrawal on its day, so both name it (the
        literal rule, as Degiro's dividend tax)."""
        _builder, _table, _path, output = _scenario_parse("p2c_tax", tmp_path_factory)
        problems: List[str] = []
        withdrawal = _one_cash_row(output, "WITHDRAWAL", "2021-03-23", "-600", problems)
        taxes = [_one_cash_row(output, "TAX", "2021-03-23", amount, problems) for amount in ("-50", "-60")]
        assert not problems, problems

        assert withdrawal.ref and [tax.parent_ref for tax in taxes] == [withdrawal.ref, withdrawal.ref]

    # -- the version --------------------------------------------------------------------------------------------------

    def test_the_version_is_above_the_snapshot(self) -> None:
        """RED before P2c: the plugin goes up a version (P2 contract §1)."""
        for name, sample in LINK_SAMPLES.items():
            previous = load_previous_snapshot(PLUGIN_CODE, sample, BROKER_ID)
            assert version_tuple(_danske().plugin_version) > version_tuple(previous.plugin_version), f"{PLUGIN_CODE} {_danske().plugin_version}: not above the snapshot's {previous.plugin_version} ({name})"
