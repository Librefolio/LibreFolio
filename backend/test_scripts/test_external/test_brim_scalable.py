"""
Test Suite: the Scalable Capital plugins — ``broker_scalable`` and ``broker_scalable_deposit`` (37_brimScalable)

Written from the plan (§4, §7.1) and the coordinator's brief. The plugins are reached through the registry inside each
test, never imported at module level: the module always collects, and a missing plugin fails each test with its code.

What is pinned:

- A. identity: codes, names, icons, documentation, version, extension, priority, sample patterns;
- B. recognition by the header, never by the file name: Scalable's own CSV (PRIME, 14 columns) and the LibreFolio
  exporter's files (the 14 columns and ``lf_account``), column names in any case and any order, a UTF-8 BOM
  tolerated; the account from the ``lf_account`` values (broker, overnight account, both, none, another); each
  plugin refuses the other account's file with a code and names the plugin that reads it, both refuse a file that
  mixes the two accounts, anything else is refused without a word, and nothing raises;
- C. the three samples line by line: transactions compared as multisets (type, date, quantity, amount, currency,
  asset), descriptions with the transaction id and the reference, tags, broker, fake assets in order of first
  imported use, notices with the lines they list and their evidence; the internal transfers of the two exporter
  files mirror each other;
- D. the rules on synthetic files: statuses and reversals, trades with their FEE and TAX legs, the fee inside the
  amount of exporter 1.0.0, tax refunds, dividends and interest gross or net, cash rows by their sign, rows not
  imported or unreadable, several overnight accounts in one file, an export without rows, descriptions, assets
  without an ISIN.

Every input is a sample of ``sample_reports/`` or is written in ``tmp_path``; every value of the synthetic files is
invented (the ISINs are public securities). No server and no database: this module is pure. The endpoint that asks a
plugin about an uploaded file (``GET /import/files/{file_id}/plugin-check``) is tested in ``test_api/test_brim_api.py``,
category 17; the contract of ``cannot_parse_detail`` for every plugin, in ``test_brim_providers.py``, category 4d.

Plan: LibreFolio_developer_journal/Release_2/Phase_0/37_brimScalable/plan-phase00BrimScalable.prompt.md
"""

from __future__ import annotations

import csv
import io
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.schemas.brim import FAKE_ASSET_ID_BASE, BRIMEvidence, BRIMNotice, BRIMParseOutput, BRIMRefusal
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.provider_registry import BRIMProviderRegistry

# =============================================================================
# CONSTANTS
# =============================================================================

BROKER_CODE = "broker_scalable"
DEPOSIT_CODE = "broker_scalable_deposit"
BROKER_NAME = "Scalable Capital broker"
DEPOSIT_NAME = "Scalable Capital overnight account"
PLUGIN_CODES = (BROKER_CODE, DEPOSIT_CODE)
DOCS_URL = "/mkdocs/user/transactions/import/scalable/"
PLUGIN_VERSION = "1.0.0"
SAMPLE_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"
PRIME_SAMPLE = SAMPLE_DIR / "scalable-prime-export.csv"
BROKER_SAMPLE = SAMPLE_DIR / "scalable-broker-export.csv"
DEPOSIT_SAMPLE = SAMPLE_DIR / "scalable-deposit-export.csv"
# Not 1: every transaction must carry the broker parse was given, not a number of the plugin's own.
BROKER_ID = 7
TAGS = ["import", "scalable"]
# Between the parts of a description: U+00B7 MIDDLE DOT, one space on each side.
SEP = " \u00b7 "
# What a leg writes before the description of its row (plan §4.4).
LEG_FEE = "Order fee"
LEG_TAX = "Tax"
LEG_REFUND = "Tax refund"
BOM = b"\xef\xbb\xbf"
TRANSFER_SUBTYPES = ("CASH_TRANSFER_IN", "CASH_TRANSFER_OUT")

# The notices of the two plugins (plan §4.5) and the severity of each.
NOT_EXECUTED = "scalable_not_executed"
OPEN_PARTIAL = "scalable_open_partial"
FEES_UNKNOWN = "scalable_fees_unknown"
REVERSAL = "scalable_reversal"
NOT_IMPORTED = "scalable_not_imported"
CASH_BY_SIGN = "scalable_cash_by_sign"
TAX_REFUND = "scalable_tax_refund"
INTERNAL_TRANSFERS = "scalable_internal_transfers"
SEVERAL_ACCOUNTS = "scalable_several_overnight_accounts"
FEE_IN_AMOUNT = "scalable_fee_in_amount"
UNREADABLE_ROWS = "scalable_unreadable_rows"
DIVIDENDS_NET = "scalable_dividends_net"
SEVERITY = {
    NOT_EXECUTED: "info",
    CASH_BY_SIGN: "info",
    TAX_REFUND: "info",
    INTERNAL_TRANSFERS: "info",
    DIVIDENDS_NET: "info",
    OPEN_PARTIAL: "warning",
    FEES_UNKNOWN: "warning",
    REVERSAL: "warning",
    NOT_IMPORTED: "warning",
    SEVERAL_ACCOUNTS: "warning",
    FEE_IN_AMOUNT: "warning",
    UNREADABLE_ROWS: "warning",
}

# The 14 columns of Scalable's own CSV, as Scalable writes them; the exporter repeats them, then adds its own.
PRIME_HEADER = ("date", "time", "status", "reference", "description", "assetType", "type", "isin", "shares", "price", "amount", "fee", "tax", "currency")
BROKER_HEADER = (*PRIME_HEADER, "lf_account", "lf_id", "lf_subtype", "lf_is_cancellation", "lf_ordered_shares", "lf_transaction_fee", "lf_venue_fee", "lf_crypto_spread_fee", "lf_trading_venue")
DEPOSIT_HEADER = (*PRIME_HEADER, "lf_account", "lf_account_index", "lf_id", "lf_subtype", "lf_is_cancellation")
# The cells the exporter always writes between quotes.
QUOTED_COLUMNS = ("reference", "description")

# Securities of the samples (public identifiers; every amount, date, reference and id around them is invented).
APPLE = "US0378331005"
TELEKOM = "DE0005557508"
MSCI_WORLD = "IE00B4L5Y983"
ALL_WORLD_ACC = "IE00BK5BQT80"
ALL_WORLD_DIST = "IE00B3RBWM25"
NAMES = {
    APPLE: "Apple Inc.",
    TELEKOM: "Deutsche Telekom AG",
    MSCI_WORLD: "iShares Core MSCI World UCITS ETF USD (Acc)",
    ALL_WORLD_ACC: "Vanguard FTSE All-World UCITS ETF (USD) Accumulating",
    ALL_WORLD_DIST: "Vanguard FTSE All-World UCITS ETF (Dist)",
}


# =============================================================================
# REFUSALS — what each plugin owes for a file it does not read
# =============================================================================


@dataclass(frozen=True)
class Refusal:
    """The refusal a plugin owes for a file: its code and the plugin its context names. The message is checked as one sentence, never verbatim."""

    code: str
    plugin_code: Optional[str] = None
    plugin_name: Optional[str] = None

    @property
    def context(self) -> Dict[str, Optional[str]]:
        return {} if self.plugin_code is None else {"plugin_code": self.plugin_code, "plugin_name": self.plugin_name}


# The four refusals of plan §4.2: the other account's file, Scalable's own CSV to the overnight account, a file mixing both.
DEPOSIT_FILE = Refusal("scalable_deposit_file", DEPOSIT_CODE, DEPOSIT_NAME)
BROKER_FILE = Refusal("scalable_broker_file", BROKER_CODE, BROKER_NAME)
PRIME_FILE = Refusal("scalable_prime_file", BROKER_CODE, BROKER_NAME)
MIXED_FILE = Refusal("scalable_mixed_file")
# What a plugin answers about a file: it reads it, it refuses it without a word (no refusal, no reason), or the Refusal it owes.
ACCEPTS = "accepts"
SILENT = "silent"
Answer = Union[str, Refusal]


# =============================================================================
# HELPERS — the plugins are reached inside each test
# =============================================================================


def _plugin(code: str) -> BRIMProvider:
    """The registered plugin ``code``; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(code)
    assert plugin is not None, f"no BRIM plugin is registered as {code}: not implemented yet (37_brimScalable, plan §4)"
    return plugin


def _parse(code: str, path: Path) -> BRIMParseOutput:
    """``code``'s parse of ``path`` for broker ``BROKER_ID``; a ``BRIMParseError`` fails the test with its message."""
    try:
        return _plugin(code).parse(path, broker_id=BROKER_ID)
    except BRIMParseError as exc:
        raise AssertionError(f"{code}.parse({path.name}) raised BRIMParseError: {exc.message}") from exc


def _num(value: Any) -> Optional[str]:
    """A number as plain text without trailing zeros, so that ``86.00``, ``86`` and ``Decimal("86.0000")`` compare equal and print readably."""
    if value is None:
        return None
    number = Decimal(str(value))
    return "0" if number == 0 else format(number.normalize(), "f")


def _is_one_sentence(text: object) -> bool:
    """One short English sentence, as a refusal's message must be: a non-empty single line, no blank around it, lowercase start, no final period."""
    return isinstance(text, str) and text != "" and text == text.strip() and "\n" not in text and text[0] == text[0].lower() and not text.endswith(".")


def _raw(path: Path) -> Tuple[List[str], Dict[int, List[str]]]:
    """The header and the cells of every data line of an export, by 1-based line number (the header is line 1), as the csv module reads them."""
    rows = list(csv.reader(io.StringIO(path.read_text(encoding="utf-8-sig")), delimiter=";"))
    return rows[0], dict(enumerate(rows[1:], start=2))


def _by_name(header: Sequence[str], cells: Sequence[str]) -> Dict[str, str]:
    """A line's cells by lower-case column name."""
    return {name.strip().lower(): cell.strip() for name, cell in zip(header, cells, strict=True)}


def _description(values: Dict[str, str], *, exporter: bool, prefix: Optional[str] = None) -> str:
    """The description the plan gives a row's transaction (§4.4): a leg's prefix, the row's text (its type when the text is empty), then
    ``id <lf_id>`` in an exporter file and ``ref <reference>`` when there is one, joined by ``SEP``."""
    parts = [prefix] if prefix else []
    parts.append(values["description"] or values["type"])
    if exporter:
        parts.append(f"id {values['lf_id']}")
    if values["reference"]:
        parts.append(f"ref {values['reference']}")
    return SEP.join(parts)


# =============================================================================
# SYNTHETIC FILES — written in tmp_path the way the exporter writes them
# =============================================================================


@dataclass(frozen=True)
class Row:
    """One data row of a synthetic export, by column name; ``cells`` lays it out under any header.

    The defaults are an executed cash deposit of 100 EUR: a test writes only what its case is about. ``reference``, ``lf_id``
    and ``account`` left to None are filled by the layout (``_laid_out``).
    """

    type: str = "Deposit"
    amount: str = "100"
    status: str = "Executed"
    day: str = "2026-05-04"
    description: str = "Synthetic movement"
    asset_type: str = "Cash"
    isin: str = ""
    shares: str = ""
    price: str = ""
    fee: str = ""
    tax: str = ""
    currency: str = "EUR"
    reference: Optional[str] = None
    lf_id: Optional[str] = None
    account: Optional[str] = None
    account_index: str = "1"
    subtype: str = ""
    cancellation: str = ""
    ordered_shares: str = ""

    def by_name(self) -> Dict[str, str]:
        """The row's cells by lower-case column name."""
        return {
            "date": self.day,
            "time": "10:00:00",
            "status": self.status,
            "reference": self.reference or "",
            "description": self.description,
            "assettype": self.asset_type,
            "type": self.type,
            "isin": self.isin,
            "shares": self.shares,
            "price": self.price,
            "amount": self.amount,
            "fee": self.fee,
            "tax": self.tax,
            "currency": self.currency,
            "lf_account": self.account or "",
            "lf_account_index": self.account_index,
            "lf_id": self.lf_id or "",
            "lf_subtype": self.subtype,
            "lf_is_cancellation": self.cancellation,
            "lf_ordered_shares": self.ordered_shares,
        }

    def cells(self, header: Sequence[str]) -> List[str]:
        """The row under ``header``: each column's cell by name, empty for a column the row does not know."""
        values = self.by_name()
        return [values.get(name.strip().lower(), "") for name in header]


@dataclass(frozen=True)
class Layout:
    """A file shape: its header, whether the exporter wrote it, and the account its rows name in ``lf_account``."""

    name: str
    header: Tuple[str, ...]
    exporter: bool
    account: str = ""


PRIME = Layout("prime", PRIME_HEADER, exporter=False)
BROKER_EXPORT = Layout("broker-export", BROKER_HEADER, exporter=True, account="broker")
DEPOSIT_EXPORT = Layout("deposit-export", DEPOSIT_HEADER, exporter=True, account="deposit")
BROKER_LAYOUTS = [pytest.param(PRIME, id="prime"), pytest.param(BROKER_EXPORT, id="broker-export")]
EVERY_LAYOUT = [pytest.param(PRIME, BROKER_CODE, id="prime"), pytest.param(BROKER_EXPORT, BROKER_CODE, id="broker-export"), pytest.param(DEPOSIT_EXPORT, DEPOSIT_CODE, id="deposit-export")]


def _laid_out(rows: Sequence[Row], layout: Layout) -> List[Row]:
    """The rows as ``layout`` writes them: a distinct transaction id (exporter) or reference (PRIME), and the layout's account, wherever the test left them to None.

    Every transaction's description then names its own row.
    """
    if not layout.exporter:
        return [replace(row, reference=f"SCALTEST{index:07d}" if row.reference is None else row.reference) for index, row in enumerate(rows, start=1)]
    return [replace(row, lf_id=f"synthT{index:016d}" if row.lf_id is None else row.lf_id, account=layout.account if row.account is None else row.account) for index, row in enumerate(rows, start=1)]


def _quoted(cell: str) -> str:
    return '"' + cell.replace('"', '""') + '"'


def _line(header: Sequence[str], cells: Sequence[str]) -> str:
    """A data line as the exporter writes it: ``;`` between the cells, ``reference`` and ``description`` always between quotes."""
    return ";".join(_quoted(cell) if name.lower() in QUOTED_COLUMNS else cell for name, cell in zip(header, cells, strict=True))


def _file_bytes(header: Sequence[str], rows: Sequence[Row]) -> bytes:
    """An export: the header, then one line per row; LF, UTF-8 without a BOM."""
    lines = [";".join(header), *(_line(header, row.cells(header)) for row in rows)]
    return "".join(f"{line}\n" for line in lines).encode("utf-8")


def _write(folder: Path, layout: Layout, rows: Sequence[Row], *, name: str = "transactions.csv") -> Path:
    """Write ``rows`` (already laid out) as one ``layout`` file in ``folder``: the row of index ``i`` lands on line ``i + 2``."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(_file_bytes(layout.header, rows))
    return path


def _trade(kind: str, isin: str, shares: str, price: str, amount: str, **cells: str) -> Row:
    """An executed trade of a sample security (``Buy``, ``Savings plan``, ``Sell``…), fee and tax ``0`` unless the case says otherwise."""
    return replace(Row(type=kind, asset_type="Security", isin=isin, description=NAMES[isin], shares=shares, price=price, amount=amount, fee="0", tax="0"), **cells)


def _income(kind: str, isin: str, amount: str, **cells: str) -> Row:
    """An executed distribution of a sample security, ``assetType`` Cash as Scalable writes it."""
    return replace(Row(type=kind, isin=isin, description=NAMES[isin], amount=amount), **cells)


def _cash(kind: str, amount: str, **cells: str) -> Row:
    """An executed cash row of ``kind``."""
    return replace(Row(type=kind, amount=amount), **cells)


def _without(header: Sequence[str], column: str) -> Tuple[str, ...]:
    """``header`` without one of its columns."""
    return tuple(name for name in header if name != column)


def _reshaped(content: bytes) -> bytes:
    """The same export with its columns in reverse order and its header in upper case: read by name, in any case."""
    rows = list(csv.reader(io.StringIO(content.decode("utf-8")), delimiter=";"))
    buffer = io.StringIO()
    csv.writer(buffer, delimiter=";", lineterminator="\n").writerows([[name.upper() for name in reversed(rows[0])], *(list(reversed(row)) for row in rows[1:])])
    return buffer.getvalue().encode("utf-8")


# =============================================================================
# OUTCOMES — what became of each row
# =============================================================================

# A transaction as compared: type, date, quantity, amount, currency, asset (its ISIN, ``name:<name>`` without one, None without an asset), description.
Key = Tuple[str, str, Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]


def _asset(out: BRIMParseOutput, tx: TXCreateItem) -> Optional[str]:
    """The asset a transaction names: its ISIN, ``name:<name>`` when it has none, None without an asset; one missing from ``extracted_assets`` says so."""
    if tx.asset_id is None:
        return None
    info = out.extracted_assets.get(tx.asset_id)
    if info is None:
        return f"<asset {tx.asset_id} not extracted>"
    return info.extracted_isin or f"name:{info.extracted_name}"


def _key(out: BRIMParseOutput, tx: TXCreateItem) -> Key:
    cash = tx.cash
    return (tx.type.value, tx.date.isoformat(), _num(tx.quantity), _num(cash.amount) if cash else None, cash.code if cash else None, _asset(out, tx), tx.description)


def _money(key: Key) -> Tuple[Any, ...]:
    """Everything of a key but the description: type, date, quantity, amount, currency, asset."""
    return key[:6]


def _text(key: Key) -> Tuple[Any, ...]:
    """Type, date, amount and description of a key."""
    return (key[0], key[1], key[3], key[6])


def _diff(actual: Counter, expected: Counter) -> str:
    """What ``actual`` misses and what it has too much of, element by element."""
    missing = sorted((expected - actual).elements(), key=repr)
    extra = sorted((actual - expected).elements(), key=repr)
    return f"missing {len(missing)}: {missing}; unexpected {len(extra)}: {extra}"


@dataclass(frozen=True)
class Leg:
    """A transaction expected from a row: its type, amount and quantity, whether it names the row's asset, and its prefix (None: the row's own transaction)."""

    type: str
    amount: str
    quantity: str = "0"
    asset: bool = False
    prefix: Optional[str] = None


def _expected_key(row: Row, leg: Leg, *, exporter: bool) -> Key:
    """The key of ``leg``: the row's date and currency, its ISIN (its name without one) when the leg names its asset, the plan's description."""
    values = row.by_name()
    asset = (values["isin"] or f"name:{values['description']}") if leg.asset else None
    return (leg.type, values["date"], _num(leg.quantity), _num(leg.amount), values["currency"], asset, _description(values, exporter=exporter, prefix=leg.prefix))


def _row_numbers(notice: BRIMNotice) -> List[int]:
    """The lines a notice lists: the ``row_numbers`` of its evidence table."""
    return list(notice.evidence[0].row_numbers) if notice.evidence else []


def _listed(out: BRIMParseOutput) -> Dict[str, List[int]]:
    """The lines each notice lists, by code."""
    return {notice.code: sorted(_row_numbers(notice)) for notice in out.warnings}


def _row_notices(out: BRIMParseOutput) -> Dict[str, List[int]]:
    """``_listed`` but the overnight accounts' notice, which counts the file's accounts, not rows (``_run`` checks it apart)."""
    return {code: lines for code, lines in _listed(out).items() if code != SEVERAL_ACCOUNTS}


def _evidence_problems(evidence: BRIMEvidence, header: Sequence[str], raw: Dict[int, List[str]]) -> List[str]:
    """Where an evidence table breaks the brief: a title and a comment, the file's header, one row per line number, each row the cells of its line."""
    problems = [f"evidence without a {part}" for part, text in (("title", evidence.title), ("comment", evidence.comment)) if not (text or "").strip()]
    if [name.strip() for name in evidence.headers] != [name.strip() for name in header]:
        problems.append(f"evidence headers {evidence.headers}, not the file's {list(header)}")
    if not evidence.row_numbers or len(evidence.rows) != len(evidence.row_numbers):
        problems.append(f"{len(evidence.rows)} evidence rows for the line numbers {evidence.row_numbers}")
    mismatched = [number for number, cells in zip(evidence.row_numbers, evidence.rows, strict=False) if [cell.strip() for cell in cells] != [cell.strip() for cell in raw.get(number, [])]]
    return problems + [f"line {number}: the evidence row is not the file's {raw.get(number)}" for number in mismatched]


def _notice_problems(notice: BRIMNotice, header: Sequence[str], raw: Dict[int, List[str]]) -> List[str]:
    """Where a notice breaks the brief: the severity of its code, an English message, ``context`` ``{"count": n}`` (n: the lines it lists, or the
    accounts for the overnight accounts' notice) and one evidence table (``_evidence_problems``)."""
    severity = SEVERITY.get(notice.code, "<a code the plan does not have>")
    problems = [] if notice.severity == severity else [f"severity {notice.severity!r}, expected {severity!r}"]
    if not (notice.message or "").strip():
        problems.append("no message")
    if len(notice.evidence) != 1:
        return [*problems, f"{len(notice.evidence)} evidence tables, one expected"]
    count = (notice.context or {}).get("count") if notice.code == SEVERAL_ACCOUNTS else len(notice.evidence[0].row_numbers)
    if notice.context != {"count": count}:
        problems.append(f"context {notice.context}, expected {{'count': {count!r}}}")
    return [*problems, *_evidence_problems(notice.evidence[0], header, raw)]


def _all_notice_problems(out: BRIMParseOutput, path: Path) -> List[str]:
    """Every notice's problems against the file it comes from, and every code given by more than one notice."""
    header, raw = _raw(path)
    problems = [f"{notice.code}: {problem}" for notice in out.warnings for problem in _notice_problems(notice, header, raw)]
    return problems + [f"{code}: {count} notices, one expected" for code, count in Counter(notice.code for notice in out.warnings).items() if count > 1]


# A row of a synthetic file, the transactions it gives, and the notice that lists its line (None: no notice).
Case = Tuple[Row, Tuple[Leg, ...], Optional[str]]


def _expected_notices(cases: Sequence[Case]) -> Dict[str, List[int]]:
    """The lines each notice must list: the case of index ``i`` is written on line ``i + 2``."""
    listed: Dict[str, List[int]] = defaultdict(list)
    for line, (_, _, notice) in enumerate(cases, start=2):
        if notice is not None:
            listed[notice].append(line)
    return dict(listed)


def _run(folder: Path, layout: Layout, cases: Sequence[Case], *, code: str = BROKER_CODE, accounts: Optional[int] = None) -> BRIMParseOutput:
    """Write the cases' rows as one ``layout`` file, parse it with ``code`` and check what became of every row; the parse is returned for more checks.

    Checked: the transactions as a multiset of keys (``_expected_key``); the lines each notice lists; the contract of every notice
    (``_all_notice_problems``); no validation issue; ``scalable_several_overnight_accounts`` only when ``accounts`` is given, with that count.
    """
    rows = _laid_out([row for row, _, _ in cases], layout)
    path = _write(folder, layout, rows)
    out = _parse(code, path)
    actual = Counter(_key(out, tx) for tx in out.transactions)
    expected = Counter(_expected_key(row, leg, exporter=layout.exporter) for row, (_, legs, _) in zip(rows, cases, strict=True) for leg in legs)
    several = [(notice.context or {}).get("count") for notice in out.warnings if notice.code == SEVERAL_ACCOUNTS]

    assert actual == expected, f"{layout.name}: {len(out.transactions)} transaction(s) for {sum(expected.values())} expected — {_diff(actual, expected)}"
    assert _row_notices(out) == _expected_notices(cases), f"{layout.name}: the notices list the lines {_listed(out)}, expected {_expected_notices(cases)}"
    assert several == ([] if accounts is None else [accounts]), f"{layout.name}: scalable_several_overnight_accounts counts {several}, expected {accounts}"
    assert out.validation_issues == [], f"{layout.name}: {[(issue.row, issue.code, issue.message) for issue in out.validation_issues]}"
    problems = _all_notice_problems(out, path)
    assert not problems, f"{layout.name}: {problems}"
    return out


# =============================================================================
# THE SAMPLES, LINE BY LINE (the coordinator's brief)
# =============================================================================


@dataclass(frozen=True)
class Tx:
    """A transaction a sample line gives, as the brief lists it: type, date, amount, quantity, the ISIN of its asset (None: no asset), its prefix (None: the line's own)."""

    line: int
    type: str
    day: str
    amount: str
    quantity: str = "0"
    isin: Optional[str] = None
    prefix: Optional[str] = None


@dataclass
class SampleSpec:
    """What a sample gives: its plugin and layout, its transactions, its notices with the lines they list, its securities in order of first imported use."""

    path: Path
    code: str
    exporter: bool
    transactions: Tuple[Tx, ...]
    notices: Dict[str, Tuple[int, ...]]
    assets: Tuple[str, ...]


PRIME_SPEC = SampleSpec(
    path=PRIME_SAMPLE,
    code=BROKER_CODE,
    exporter=False,
    transactions=(
        # A sale with its fee and its tax, both legs on the sold security
        Tx(4, "SELL", "2026-06-15", "902", quantity="-5", isin=APPLE),
        Tx(4, "FEE", "2026-06-15", "-0.99", isin=APPLE, prefix=LEG_FEE),
        Tx(4, "TAX", "2026-06-15", "-24.57", isin=APPLE, prefix=LEG_TAX),
        # A dividend booked gross (63.26 + 22.74), the tax withheld on the security
        Tx(5, "DIVIDEND", "2026-06-10", "86.00", isin=TELEKOM),
        Tx(5, "TAX", "2026-06-10", "-22.74", isin=TELEKOM, prefix=LEG_TAX),
        # Purchases on their gross amount; a FEE leg only when the fee is not zero
        Tx(6, "BUY", "2026-06-02", "-750.5", quantity="5", isin=APPLE),
        Tx(6, "FEE", "2026-06-02", "-0.99", isin=APPLE, prefix=LEG_FEE),
        Tx(7, "BUY", "2026-05-20", "-1181.4", quantity="12", isin=MSCI_WORLD),
        Tx(8, "BUY", "2026-05-04", "-500", quantity="3.69249", isin=ALL_WORLD_ACC),
        # Cash: the savings plan's direct debit, interest gross with its tax (no asset), bank transfers, a fee, a tax refund, a tax
        Tx(9, "DEPOSIT", "2026-05-04", "500"),
        Tx(10, "INTEREST", "2026-04-30", "4.24"),
        Tx(10, "TAX", "2026-04-30", "-1.12", prefix=LEG_TAX),
        Tx(11, "WITHDRAWAL", "2026-04-15", "-200"),
        Tx(12, "DEPOSIT", "2026-04-01", "5000"),
        Tx(13, "FEE", "2026-03-31", "-4.99"),
        Tx(14, "DEPOSIT", "2026-03-20", "12.5"),
        Tx(15, "TAX", "2026-03-10", "-8.4"),
    ),
    # The pending and the cancelled order (2, 3), the tax refund booked as a deposit (14), the security transfer (16)
    notices={NOT_EXECUTED: (2, 3), TAX_REFUND: (14,), NOT_IMPORTED: (16,)},
    assets=(APPLE, TELEKOM, MSCI_WORLD, ALL_WORLD_ACC),
)

BROKER_SPEC = SampleSpec(
    path=BROKER_SAMPLE,
    code=BROKER_CODE,
    exporter=True,
    transactions=(
        Tx(4, "SELL", "2026-06-15", "902", quantity="-5", isin=APPLE),
        Tx(4, "FEE", "2026-06-15", "-0.99", isin=APPLE, prefix=LEG_FEE),
        Tx(4, "TAX", "2026-06-15", "-24.57", isin=APPLE, prefix=LEG_TAX),
        # The dividend without its tax: booked as credited, net
        Tx(5, "DIVIDEND", "2026-06-10", "63.26", isin=TELEKOM),
        # Line 6 reverses a purchase and is not imported; line 7 is the purchase
        Tx(7, "BUY", "2026-06-02", "-750.5", quantity="5", isin=APPLE),
        Tx(7, "FEE", "2026-06-02", "-0.99", isin=APPLE, prefix=LEG_FEE),
        Tx(8, "DEPOSIT", "2026-06-01", "300"),
        Tx(9, "BUY", "2026-05-20", "-1181.4", quantity="12", isin=MSCI_WORLD),
        Tx(9, "FEE", "2026-05-20", "-1.49", isin=MSCI_WORLD, prefix=LEG_FEE),
        Tx(10, "BUY", "2026-05-04", "-500", quantity="3.69249", isin=ALL_WORLD_ACC),
        Tx(11, "DEPOSIT", "2026-05-04", "500"),
        Tx(12, "WITHDRAWAL", "2026-04-15", "-200"),
        Tx(13, "WITHDRAWAL", "2026-04-02", "-1000"),
        Tx(14, "DEPOSIT", "2026-04-01", "5000"),
        Tx(15, "FEE", "2026-03-31", "-4.99"),
        Tx(16, "DEPOSIT", "2026-03-20", "12.5"),
        Tx(17, "TAX", "2026-03-10", "-8.4"),
        # BONUS, a cash type the plugin does not know: booked by its sign
        Tx(18, "DEPOSIT", "2026-03-05", "25"),
        # A purchase without its details (fee and tax empty): booked as it is
        Tx(20, "BUY", "2026-02-10", "-840", quantity="7", isin=ALL_WORLD_DIST),
    ),
    notices={OPEN_PARTIAL: (2,), NOT_EXECUTED: (3,), DIVIDENDS_NET: (5,), REVERSAL: (6,), INTERNAL_TRANSFERS: (8, 13), TAX_REFUND: (16,), CASH_BY_SIGN: (18,), NOT_IMPORTED: (19,), FEES_UNKNOWN: (20,)},
    assets=(APPLE, TELEKOM, MSCI_WORLD, ALL_WORLD_ACC, ALL_WORLD_DIST),
)

DEPOSIT_SPEC = SampleSpec(
    path=DEPOSIT_SAMPLE,
    code=DEPOSIT_CODE,
    exporter=True,
    transactions=(
        # Interest without its tax: booked as credited
        Tx(3, "INTEREST", "2026-06-30", "2.95"),
        Tx(4, "WITHDRAWAL", "2026-06-15", "-1500"),
        Tx(5, "WITHDRAWAL", "2026-06-01", "-300"),
        # Interest gross (2.58 + 0.92, 1.82 + 0.65), the tax withheld without an asset
        Tx(6, "INTEREST", "2026-05-31", "3.50"),
        Tx(6, "TAX", "2026-05-31", "-0.92", prefix=LEG_TAX),
        Tx(7, "INTEREST", "2026-04-30", "2.47"),
        Tx(7, "TAX", "2026-04-30", "-0.65", prefix=LEG_TAX),
        Tx(8, "DEPOSIT", "2026-04-02", "1000"),
        Tx(9, "DEPOSIT", "2026-03-02", "5000"),
    ),
    notices={NOT_EXECUTED: (2,), FEES_UNKNOWN: (3,), INTERNAL_TRANSFERS: (5, 8)},
    assets=(),
)

SAMPLE_SPECS = [pytest.param(PRIME_SPEC, id="prime"), pytest.param(BROKER_SPEC, id="broker-export"), pytest.param(DEPOSIT_SPEC, id="deposit-export")]


def _sample_keys(spec: SampleSpec) -> List[Key]:
    """The key of every transaction the brief lists for a sample; its description is built from its line's cells (``_description``)."""
    header, raw = _raw(spec.path)
    return [(tx.type, tx.day, _num(tx.quantity), _num(tx.amount), "EUR", tx.isin, _description(_by_name(header, raw[tx.line]), exporter=spec.exporter, prefix=tx.prefix)) for tx in spec.transactions]


def _tx_fixture_problems(spec: SampleSpec) -> List[str]:
    """Expected transactions whose date, currency or ISIN are not their line's cells; sample lines whose security has another name than ``NAMES`` gives."""
    header, raw = _raw(spec.path)
    problems = []
    for tx in spec.transactions:
        cells = _by_name(header, raw[tx.line])
        if (cells["date"], cells["currency"]) != (tx.day, "EUR") or (tx.isin is not None and cells["isin"] != tx.isin):
            problems.append(f"line {tx.line}: the file has {cells['date']} {cells['currency']} {cells['isin']!r}, the brief {tx.day} EUR {tx.isin!r}")
    for line, row in raw.items():
        cells = _by_name(header, row)
        if cells["isin"] and cells["description"] != NAMES.get(cells["isin"]):
            problems.append(f"line {line}: {cells['isin']} is named {cells['description']!r}, not {NAMES.get(cells['isin'])!r}")
    return problems


def _transfer_lines(path: Path) -> List[Tuple[str, str, Decimal]]:
    """(date, currency, amount) of the lines whose ``lf_subtype`` is a transfer between the two accounts, the amount read by this file (decimal comma)."""
    header, raw = _raw(path)
    lines = [_by_name(header, cells) for cells in raw.values()]
    return [(cells["date"], cells["currency"], Decimal(cells["amount"].replace(",", "."))) for cells in lines if cells["lf_subtype"] in TRANSFER_SUBTYPES]


def _named_id(description: Optional[str]) -> Optional[str]:
    """The transaction id a description names (its ``id <lf_id>`` part); None without one."""
    found = [part.removeprefix("id ") for part in (description or "").split(SEP) if part.startswith("id ")]
    return found[0] if found else None


def _transfer_moves(out: BRIMParseOutput, path: Path) -> List[Tuple[str, Optional[str], Optional[str], str]]:
    """(date, currency, amount, type) of the transactions of the transfer lines, found by the transaction id their description names."""
    header, raw = _raw(path)
    ids = {cells["lf_id"] for cells in (_by_name(header, row) for row in raw.values()) if cells["lf_subtype"] in TRANSFER_SUBTYPES}
    return [(tx.date.isoformat(), tx.cash.code if tx.cash else None, _num(tx.cash.amount) if tx.cash else None, tx.type.value) for tx in out.transactions if _named_id(tx.description) in ids]


def _essence(out: BRIMParseOutput) -> Dict[str, Any]:
    """What a parse says, without the evidence tables: transactions, assets, validation issues, and each notice's severity, context and lines."""
    return {
        "transactions": [tx.model_dump(mode="json") for tx in out.transactions],
        "assets": {fake_id: info.model_dump(mode="json") for fake_id, info in out.extracted_assets.items()},
        "issues": [issue.model_dump(mode="json") for issue in out.validation_issues],
        "notices": {notice.code: (notice.severity, notice.context, _row_numbers(notice)) for notice in out.warnings},
    }


# =============================================================================
# RECOGNITION CASES — written in tmp_path, under a name that says nothing
# =============================================================================

PRIME_BYTES = PRIME_SAMPLE.read_bytes()
BROKER_BYTES = BROKER_SAMPLE.read_bytes()
DEPOSIT_BYTES = DEPOSIT_SAMPLE.read_bytes()
# Another broker's CSV: a date and a type column, none of Scalable's other columns.
GENERIC_CSV = b"date,type,quantity,amount,currency,description\n2026-05-04,DEPOSIT,0,100.00,EUR,Top-up\n2026-05-05,BUY,2,-201.00,EUR,Two shares\n"
# One row of each account: the file mixes them.
MIXED_ROWS = (Row(account="broker", lf_id="synthT0000000000000001"), Row(account="deposit", lf_id="synthT0000000000000002"))


@dataclass
class FileCase:
    """A file, and what each plugin answers about it."""

    id: str
    content: bytes
    broker: Answer
    deposit: Answer
    name: str = "transactions.csv"

    def write(self, folder: Path) -> Path:
        path = folder / self.id / self.name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.content)
        return path

    def answer(self, code: str) -> Answer:
        return self.broker if code == BROKER_CODE else self.deposit


RECOGNITION_CASES = (
    # The samples under a name that says nothing: the header decides.
    FileCase("prime-sample", PRIME_BYTES, broker=ACCEPTS, deposit=PRIME_FILE),
    FileCase("broker-export-sample", BROKER_BYTES, broker=ACCEPTS, deposit=BROKER_FILE),
    FileCase("deposit-export-sample", DEPOSIT_BYTES, broker=DEPOSIT_FILE, deposit=ACCEPTS),
    # A UTF-8 byte order mark before the header, as Scalable's own CSV can have.
    FileCase("prime-with-bom", BOM + PRIME_BYTES, broker=ACCEPTS, deposit=PRIME_FILE),
    FileCase("broker-export-with-bom", BOM + BROKER_BYTES, broker=ACCEPTS, deposit=BROKER_FILE),
    FileCase("deposit-export-with-bom", BOM + DEPOSIT_BYTES, broker=DEPOSIT_FILE, deposit=ACCEPTS),
    # The columns in reverse order, their names in upper case.
    FileCase("prime-reshaped", _reshaped(PRIME_BYTES), broker=ACCEPTS, deposit=PRIME_FILE),
    FileCase("broker-export-reshaped", _reshaped(BROKER_BYTES), broker=ACCEPTS, deposit=BROKER_FILE),
    FileCase("deposit-export-reshaped", _reshaped(DEPOSIT_BYTES), broker=DEPOSIT_FILE, deposit=ACCEPTS),
    # The 14 columns and one more that is not lf_account: still Scalable's own CSV.
    FileCase("prime-with-another-column", _file_bytes((*PRIME_HEADER, "note"), [Row(reference="SCALTEST0000001")]), broker=ACCEPTS, deposit=PRIME_FILE),
    # An exporter file without rows could be either account's: both plugins read it.
    FileCase("broker-export-without-rows", _file_bytes(BROKER_HEADER, []), broker=ACCEPTS, deposit=ACCEPTS),
    FileCase("deposit-export-without-rows", _file_bytes(DEPOSIT_HEADER, []), broker=ACCEPTS, deposit=ACCEPTS),
    # Both accounts in one file, under either exporter header: both plugins refuse it.
    FileCase("mixed-accounts-broker-header", _file_bytes(BROKER_HEADER, MIXED_ROWS), broker=MIXED_FILE, deposit=MIXED_FILE),
    FileCase("mixed-accounts-deposit-header", _file_bytes(DEPOSIT_HEADER, MIXED_ROWS), broker=MIXED_FILE, deposit=MIXED_FILE),
    # An account neither plugin knows, alone or next to a known one.
    FileCase("unknown-account", _file_bytes(BROKER_HEADER, [Row(account="savings")]), broker=SILENT, deposit=SILENT),
    FileCase("broker-and-unknown-account", _file_bytes(BROKER_HEADER, [Row(account="broker"), Row(account="savings")]), broker=SILENT, deposit=SILENT),
    # One of the 14 columns missing: neither layout.
    FileCase("prime-without-tax", _file_bytes(_without(PRIME_HEADER, "tax"), [Row(reference="SCALTEST0000001")]), broker=SILENT, deposit=SILENT),
    FileCase("broker-export-without-currency", _file_bytes(_without(BROKER_HEADER, "currency"), [Row(account="broker")]), broker=SILENT, deposit=SILENT),
    # Another extension: the content does not matter.
    FileCase("prime-as-txt", PRIME_BYTES, broker=SILENT, deposit=SILENT, name="transactions.txt"),
    FileCase("deposit-export-as-txt", DEPOSIT_BYTES, broker=SILENT, deposit=SILENT, name="transactions.txt"),
    # Not Scalable's: another broker's CSV, even named like a Scalable export; nothing at all.
    FileCase("generic-csv-named-like-a-scalable-export", GENERIC_CSV, broker=SILENT, deposit=SILENT, name="scalable-broker-export.csv"),
    FileCase("empty-file", b"", broker=SILENT, deposit=SILENT),
    FileCase("lone-bom", BOM, broker=SILENT, deposit=SILENT),
)
RECOGNITION_PARAMS = [pytest.param(case, code, id=f"{case.id}-{code}") for case in RECOGNITION_CASES for code in PLUGIN_CODES]
# Each plugin refuses the other account's samples, naming the plugin that reads them.
REFUSED_SAMPLES = [
    pytest.param(PRIME_SAMPLE, DEPOSIT_CODE, id="prime-to-the-overnight-account-plugin"),
    pytest.param(BROKER_SAMPLE, DEPOSIT_CODE, id="broker-export-to-the-overnight-account-plugin"),
    pytest.param(DEPOSIT_SAMPLE, BROKER_CODE, id="overnight-account-export-to-the-broker-plugin"),
]


def _refusal_view(detail: Any) -> Optional[Tuple[Any, ...]]:
    """What a ``cannot_parse_detail`` answer says, as compared: a BRIMRefusal or not, its code, its context, whether its message is one sentence."""
    if detail is None:
        return None
    return (isinstance(detail, BRIMRefusal), getattr(detail, "code", None), getattr(detail, "context", None), _is_one_sentence(getattr(detail, "message", None)))


def _expected_view(answer: Answer) -> Optional[Tuple[Any, ...]]:
    """The view of the refusal ``answer`` owes; None when the plugin reads the file or has nothing to say about it."""
    return (True, answer.code, answer.context, True) if isinstance(answer, Refusal) else None


def _unreadable_problems(plugin: BRIMProvider, code: str, path: Path) -> List[str]:
    """Where a plugin breaks the contract on a path with nothing to read: an exception, an acceptance, a refusal that is not one sentence or not the reason."""
    try:
        accepted, detail, reason = plugin.can_parse(path), plugin.cannot_parse_detail(path), plugin.cannot_parse_reason(path)
    except Exception as exc:  # the contract: none of the three ever raises
        return [f"{code} on {path.name}: raised {type(exc).__name__}: {exc}"]
    problems = [f"{code} accepts {path}"] if accepted else []
    if detail is not None and not (_is_one_sentence(detail.message) and reason == detail.message):
        problems.append(f"{code} on {path.name}: refusal {detail!r}, reason {reason!r}")
    if detail is None and reason is not None:
        problems.append(f"{code} on {path.name}: no refusal, and yet the reason {reason!r}")
    return problems


# =============================================================================
# A. IDENTITY
# =============================================================================

IDENTITIES = [
    pytest.param(BROKER_CODE, BROKER_NAME, "scalable/broker.png", "scalable-broker", ["scalable-prime", "scalable-broker"], id=BROKER_CODE),
    pytest.param(DEPOSIT_CODE, DEPOSIT_NAME, "scalable/deposit.png", "scalable-deposit", ["scalable-deposit"], id=DEPOSIT_CODE),
]


class TestIdentity:
    """A — what each plugin says of itself (plan §4.1)."""

    @pytest.mark.parametrize(("code", "name", "icon", "pattern", "patterns"), IDENTITIES)
    def test_the_plugin_declares_its_identity(self, code: str, name: str, icon: str, pattern: str, patterns: List[str]):
        """Code and name; ``.csv`` only; priority 100, above the generic CSV; its composed icon among the plugins' static files; the user guide; 1.0.0; its sample patterns."""
        plugin = _plugin(code)

        declared = (plugin.provider_code, plugin.provider_name, plugin.supported_extensions, plugin.detection_priority, plugin.icon_url, plugin.docs_url, plugin.plugin_version, plugin.test_file_pattern, plugin.test_file_patterns)

        assert declared == (code, name, [".csv"], 100, f"/api/v1/uploads/plugin/brim/{icon}", DOCS_URL, PLUGIN_VERSION, pattern, patterns)

    @pytest.mark.parametrize(("code", "name", "icon", "pattern", "patterns"), IDENTITIES)
    def test_the_plugin_info_shows_the_name_and_the_icon(self, code: str, name: str, icon: str, pattern: str, patterns: List[str]):
        """What ``GET /import/plugins`` gives the import wizard and the broker icon: the same code, name, icon, guide and version."""
        info = _plugin(code).to_plugin_info()

        assert (info.code, info.name, info.icon_url, info.docs_url, info.plugin_version) == (code, name, f"/api/v1/uploads/plugin/brim/{icon}", DOCS_URL, PLUGIN_VERSION)

    def test_each_plugin_s_patterns_match_its_own_samples_only(self):
        """The generic suite parses every sample a plugin's patterns match: the broker plugin its PRIME and exporter samples, the overnight account's plugin its own."""
        matched = {code: sorted(path.name for path in SAMPLE_DIR.glob("*.csv") if any(pattern in path.name.lower() for pattern in _plugin(code).test_file_patterns)) for code in PLUGIN_CODES}

        assert matched == {BROKER_CODE: [BROKER_SAMPLE.name, PRIME_SAMPLE.name], DEPOSIT_CODE: [DEPOSIT_SAMPLE.name]}


# =============================================================================
# B. RECOGNITION AND REFUSALS (plan §4.2)
# =============================================================================


class TestRecognition:
    """B — the header decides, never the file name: the layout from the columns, the account from the ``lf_account`` values. Each plugin reads its
    account's files, refuses the other account's with a code naming the plugin that reads them, and has nothing to say about any other file."""

    @pytest.mark.parametrize(("case", "code"), RECOGNITION_PARAMS)
    def test_each_plugin_answers_each_file(self, case: FileCase, code: str, tmp_path: Path):
        """``can_parse``, ``cannot_parse_detail`` and ``cannot_parse_reason`` agree with the brief: accepted with nothing to add, refused with the code
        and the context the case owes and one English sentence, or refused without a word; the reason is always the refusal's message."""
        path = case.write(tmp_path)
        plugin = _plugin(code)
        expected = case.answer(code)

        accepted, detail, reason = plugin.can_parse(path), plugin.cannot_parse_detail(path), plugin.cannot_parse_reason(path)

        assert accepted is (expected == ACCEPTS), f"{case.id}: {code}.can_parse answers {accepted!r}"
        assert _refusal_view(detail) == _expected_view(expected), f"{case.id}: {code}.cannot_parse_detail answers {detail!r}"
        assert reason == (detail.message if detail is not None else None), f"{case.id}: cannot_parse_reason {reason!r} is not the refusal's message"

    @pytest.mark.parametrize(("sample", "code"), REFUSED_SAMPLES)
    def test_a_refusal_names_the_plugin_that_reads_the_file(self, sample: Path, code: str):
        """The plugin a refusal names exists under that code, calls itself by that name and reads the file: the import wizard can propose it."""
        detail = _plugin(code).cannot_parse_detail(sample)
        assert detail is not None and detail.context.get("plugin_code"), f"premise: {code} refuses {sample.name} naming a plugin: {detail!r}"

        named = _plugin(detail.context["plugin_code"])

        assert (named.provider_name, named.can_parse(sample)) == (detail.context.get("plugin_name"), True)

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_the_columns_are_read_by_name(self, spec: SampleSpec, tmp_path: Path):
        """The sample with its columns reversed and its header in upper case gives the same transactions, assets and notices (codes, counts, lines)."""
        path = tmp_path / "transactions.csv"
        path.write_bytes(_reshaped(spec.path.read_bytes()))

        assert _essence(_parse(spec.code, path)) == _essence(_parse(spec.code, spec.path))

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_a_byte_order_mark_changes_nothing(self, spec: SampleSpec, tmp_path: Path):
        """The sample behind a UTF-8 BOM parses exactly as the sample, evidence tables included."""
        path = tmp_path / spec.path.name
        path.write_bytes(BOM + spec.path.read_bytes())

        assert _parse(spec.code, path).model_dump(mode="json") == _parse(spec.code, spec.path).model_dump(mode="json")

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_is_detected_first_whatever_the_file_name(self, spec: SampleSpec, tmp_path: Path):
        """What the upload offers first: the plugin of the file's account, before the generic CSV (which reads any header with a date and a type); never the other account's."""
        path = tmp_path / "download.csv"
        path.write_bytes(spec.path.read_bytes())
        other = DEPOSIT_CODE if spec.code == BROKER_CODE else BROKER_CODE

        compatible = BRIMProviderRegistry.get_compatible_plugins(path)

        assert BRIMProviderRegistry.auto_detect_plugin(path) == spec.code, f"detected as {BRIMProviderRegistry.auto_detect_plugin(path)!r}, compatible {compatible}"
        assert compatible[:1] == [spec.code] and other not in compatible, f"compatible plugins {compatible}"

    def test_refuses_every_other_sample_without_a_word(self):
        """Guard: no file of ``sample_reports/`` (recursive, every extension) whose name lacks ``scalable`` is read by either plugin, and neither has anything to say about it."""
        others = sorted(path for path in SAMPLE_DIR.rglob("*") if path.is_file() and "scalable" not in path.name.lower())
        assert len(others) > 20, f"premise: the corpus holds the other brokers' samples: {[path.name for path in others]}"
        plugins = {code: _plugin(code) for code in PLUGIN_CODES}

        answered = [(code, str(path.relative_to(SAMPLE_DIR)), plugin.can_parse(path), plugin.cannot_parse_detail(path)) for code, plugin in plugins.items() for path in others]

        assert [answer for answer in answered if answer[2] or answer[3] is not None] == []

    def test_nothing_raises_on_a_path_with_nothing_to_read(self, tmp_path: Path):
        """A missing file and a folder named like a CSV: ``can_parse`` is false and no method raises; a refusal, if any, is one sentence and is the reason."""
        folder_like_a_csv = tmp_path / "folder" / "transactions.csv"
        folder_like_a_csv.mkdir(parents=True)
        paths = [tmp_path / "missing" / "transactions.csv", folder_like_a_csv]

        problems = [problem for code in PLUGIN_CODES for path in paths for problem in _unreadable_problems(_plugin(code), code, path)]

        assert not problems, problems


# =============================================================================
# FIXTURE GUARDS — this file's expectations against the samples
# =============================================================================


class TestSampleFixtures:
    """Fixture guards: this file's line-by-line expectations agree with the samples as the csv module reads them. They pass whatever the plugins do."""

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_every_data_line_is_accounted_for(self, spec: SampleSpec):
        """Each data line gives a transaction or is listed by a notice: the brief skips no line without a word."""
        _, raw = _raw(spec.path)
        claimed = {tx.line for tx in spec.transactions} | {line for lines in spec.notices.values() for line in lines}

        assert claimed == set(raw), f"{spec.path.name}: lines claimed {sorted(claimed)}, data lines {sorted(raw)}"

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_the_expected_values_are_the_line_cells(self, spec: SampleSpec):
        """Date, currency and ISIN of each expected transaction are its line's cells; each security of the sample has the name ``NAMES`` gives it."""
        assert _tx_fixture_problems(spec) == []

    def test_the_two_exporter_samples_mirror_their_transfers(self):
        """The ``CASH_TRANSFER_*`` lines of the broker file and of the overnight account's file: same dates and currencies, opposite amounts."""
        broker, deposit = _transfer_lines(BROKER_SAMPLE), _transfer_lines(DEPOSIT_SAMPLE)
        assert len(broker) == 2, f"premise: the broker sample holds two transfers: {broker}"

        assert sorted((day, currency, -amount) for day, currency, amount in broker) == sorted(deposit)


# =============================================================================
# C. THE THREE SAMPLES, LINE BY LINE (the coordinator's brief)
# =============================================================================


class TestSamples:
    """C — the three samples give exactly what the brief lists: compared as multisets, never by position."""

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_the_sample_gives_its_transactions(self, spec: SampleSpec):
        """Type, date, quantity, amount, currency and asset of every transaction (17, 19 and 9 of them); no validation issue."""
        out = _parse(spec.code, spec.path)
        actual = Counter(_money(_key(out, tx)) for tx in out.transactions)
        expected = Counter(_money(key) for key in _sample_keys(spec))

        assert actual == expected, f"{spec.path.name}: {len(out.transactions)} transaction(s) for {len(spec.transactions)} expected — {_diff(actual, expected)}"
        assert out.validation_issues == [], f"{spec.path.name}: {[(issue.row, issue.code, issue.message) for issue in out.validation_issues]}"

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_each_transaction_is_described_with_its_line(self, spec: SampleSpec):
        """The line's description (its type when empty), then ``id <lf_id>`` in an exporter file and ``ref <reference>`` when there is one; a leg's prefix first."""
        out = _parse(spec.code, spec.path)
        actual = Counter(_text(_key(out, tx)) for tx in out.transactions)
        expected = Counter(_text(key) for key in _sample_keys(spec))

        assert actual == expected, f"{spec.path.name}: {_diff(actual, expected)}"

    def test_the_descriptions_of_the_brief_are_verbatim(self):
        """The brief's examples, written out: the parts joined by U+00B7 with one space on each side."""
        prime = {tx.description for tx in _parse(BROKER_CODE, PRIME_SAMPLE).transactions}
        exporter = {tx.description for tx in _parse(BROKER_CODE, BROKER_SAMPLE).transactions}

        assert {"Apple Inc. \u00b7 ref SCALPRIME000012", "Order fee \u00b7 Apple Inc. \u00b7 ref SCALPRIME000012"} <= prime, sorted(prime)
        assert {"Apple Inc. \u00b7 id synthB0000000000000014 \u00b7 ref SCALEXPORT00012", "Interner Übertrag \u00b7 id SYNTHC0000000000000010"} <= exporter, sorted(exporter)

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_every_transaction_is_tagged_for_its_broker(self, spec: SampleSpec):
        """The broker ``parse`` was given, the tags ``["import", "scalable"]`` for both plugins, no ``link_uuid``: the transfers are merged later, in the bulk editor."""
        out = _parse(spec.code, spec.path)
        assert len(out.transactions) == len(spec.transactions), f"presence barrier: {spec.path.name} gives {len(out.transactions)} transaction(s), {len(spec.transactions)} expected"

        wrong = [(tx.type.value, tx.description, tx.broker_id, tx.tags, tx.link_uuid) for tx in out.transactions if (tx.broker_id, tx.tags, tx.link_uuid) != (BROKER_ID, TAGS, None)]

        assert not wrong, f"{spec.path.name}: (type, description, broker, tags, link_uuid) off the contract: {wrong}"

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_one_fake_asset_per_isin_in_order_of_first_imported_use(self, spec: SampleSpec):
        """Reading the file from the top, the first security a transaction names gets ``FAKE_ASSET_ID_BASE``, each new one the next id down; a security
        that only rows not imported name (the PRIME pending order comes first) uses no id and is not extracted. ISIN and name from the line."""
        out = _parse(spec.code, spec.path)
        expected = {FAKE_ASSET_ID_BASE - position: (isin, NAMES[isin]) for position, isin in enumerate(spec.assets)}

        extracted = {fake_id: (info.extracted_isin, info.extracted_name) for fake_id, info in out.extracted_assets.items()}
        used = {tx.asset_id for tx in out.transactions if tx.asset_id is not None}

        assert extracted == expected, f"{spec.path.name}: extracted assets {extracted}, expected {expected}"
        assert used == set(expected), f"{spec.path.name}: the transactions name the fake ids {sorted(used)}, the extracted ones are {sorted(expected)}"

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_the_sample_lists_its_rows_by_reason(self, spec: SampleSpec):
        """Exactly the brief's notices, one per code, each listing its lines (1-based, the header is line 1) with ``context`` ``{"count": n}``."""
        out = _parse(spec.code, spec.path)
        codes = Counter(notice.code for notice in out.warnings)

        assert codes == Counter(spec.notices.keys()), f"{spec.path.name}: notices {dict(codes)}, expected exactly one of each of {sorted(spec.notices)}"
        assert _listed(out) == {code: sorted(lines) for code, lines in spec.notices.items()}, f"{spec.path.name}: the notices list the lines {_listed(out)}"
        assert {notice.code: notice.context for notice in out.warnings} == {code: {"count": len(lines)} for code, lines in spec.notices.items()}

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_every_notice_keeps_the_contract(self, spec: SampleSpec):
        """The severity of its code, an English message, one evidence table with a title and a comment, the file's header, each listed line's cells."""
        out = _parse(spec.code, spec.path)
        assert sorted(notice.code for notice in out.warnings) == sorted(spec.notices), f"presence barrier: {spec.path.name} gives the notices {[notice.code for notice in out.warnings]}"

        problems = _all_notice_problems(out, spec.path)

        assert not problems, f"{spec.path.name}: {problems}"

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_the_parse_is_deterministic(self, spec: SampleSpec):
        """Same file, same output: the cache of parsed files and ``plugin_version`` rely on it."""
        first, second = _parse(spec.code, spec.path), _parse(spec.code, spec.path)

        assert first.model_dump(mode="json") == second.model_dump(mode="json"), f"{spec.path.name}: two parses differ"

    def test_the_internal_transfers_mirror_each_other(self):
        """Each transfer between the accounts is a WITHDRAWAL on one side and a DEPOSIT on the other, same date and currency, opposite amounts: what the
        bulk editor needs to merge them into a cash transfer (2026-04-02 -1000/+1000, 2026-06-01 +300/-300)."""
        broker = _transfer_moves(_parse(BROKER_CODE, BROKER_SAMPLE), BROKER_SAMPLE)
        deposit = _transfer_moves(_parse(DEPOSIT_CODE, DEPOSIT_SAMPLE), DEPOSIT_SAMPLE)

        assert sorted(broker) == [("2026-04-02", "EUR", "-1000", "WITHDRAWAL"), ("2026-06-01", "EUR", "300", "DEPOSIT")], f"the broker file's transfers: {broker}"
        assert sorted(deposit) == [("2026-04-02", "EUR", "1000", "DEPOSIT"), ("2026-06-01", "EUR", "-300", "WITHDRAWAL")], f"the overnight account's transfers: {deposit}"
        assert sorted((day, currency, _num(-Decimal(amount))) for day, currency, amount, _ in broker) == sorted((day, currency, amount) for day, currency, amount, _ in deposit)


# =============================================================================
# D. THE RULES, ON SYNTHETIC FILES (plan §4.3; the coordinator's brief)
# =============================================================================


class TestStatusesAndReversals:
    """D — only executed rows are imported: ``Executed`` or ``Settled``, in any case. An order filled in part and still open, every other status and
    the exporter's reversals are listed in a notice, never imported."""

    def test_the_exporter_imports_only_executed_rows(self, tmp_path: Path):
        """``Pending`` with shares executed and ``lf_ordered_shares``: ``scalable_open_partial``. Any other ``Pending``, ``Cancelled``, ``Expired``,
        ``Rejected``: ``scalable_not_executed``. ``lf_is_cancellation`` true: ``scalable_reversal``, whatever the row reverses."""
        cases = [
            (_trade("Buy", MSCI_WORLD, "2", "100,5", "-201"), (Leg("BUY", "-201", "2", asset=True),), None),
            (_trade("Buy", MSCI_WORLD, "1", "100", "-100", status="Settled"), (Leg("BUY", "-100", "1", asset=True),), None),
            (_cash("Deposit", "50", status="executed"), (Leg("DEPOSIT", "50"),), None),
            (_cash("Withdrawal", "-20", status="SETTLED"), (Leg("WITHDRAWAL", "-20"),), None),
            (_trade("Buy", ALL_WORLD_ACC, "3", "135,2", "-405,6", status="Pending", ordered_shares="10"), (), OPEN_PARTIAL),
            (_trade("Buy", ALL_WORLD_ACC, "0", "135,2", "0", status="Pending", ordered_shares="10"), (), NOT_EXECUTED),
            (_trade("Buy", ALL_WORLD_ACC, "3", "135,2", "-405,6", status="Pending"), (), NOT_EXECUTED),
            (_trade("Buy", ALL_WORLD_ACC, "0", "", "0", status="Cancelled", fee="", tax=""), (), NOT_EXECUTED),
            (_trade("Buy", ALL_WORLD_ACC, "0", "", "0", status="Expired", fee="", tax=""), (), NOT_EXECUTED),
            (_trade("Sell", APPLE, "0", "", "0", status="Rejected", fee="", tax=""), (), NOT_EXECUTED),
            (_cash("Withdrawal", "-75", status="Pending"), (), NOT_EXECUTED),
            (_trade("Buy", APPLE, "5", "150,1", "-750,5", fee="0,99", cancellation="true"), (), REVERSAL),
            (_cash("Deposit", "70", cancellation="true"), (), REVERSAL),
        ]

        _run(tmp_path, BROKER_EXPORT, cases)

    def test_scalable_s_own_csv_imports_only_executed_rows(self, tmp_path: Path):
        """PRIME writes a pending order with its shares and its amount, and has no ``lf_ordered_shares``: not executed all the same."""
        cases = [
            (_trade("Buy", MSCI_WORLD, "1", "100", "-100", status="Settled"), (Leg("BUY", "-100", "1", asset=True),), None),
            (_cash("Deposit", "50", status="EXECUTED"), (Leg("DEPOSIT", "50"),), None),
            (_trade("Buy", ALL_WORLD_ACC, "10", "135,2", "-1352", status="Pending"), (), NOT_EXECUTED),
            (_trade("Sell", APPLE, "0", "", "0", status="Expired"), (), NOT_EXECUTED),
        ]

        _run(tmp_path, PRIME, cases)


# Exporter 1.0.0 wrote the fee (and the tax) inside a trade's amount; 1.0.1 writes shares x price, as Scalable's own CSV does.
FEE_IN_AMOUNT_CASES = [
    pytest.param(BROKER_EXPORT, _trade("Buy", APPLE, "5", "150,1", "-751,49", fee="0,99"), (Leg("BUY", "-751.49", "5", asset=True),), FEE_IN_AMOUNT, id="exporter-1.0.0-buy"),
    pytest.param(BROKER_EXPORT, _trade("Sell", APPLE, "5", "180,4", "876,44", fee="0,99", tax="24,57"), (Leg("SELL", "876.44", "-5", asset=True),), FEE_IN_AMOUNT, id="exporter-1.0.0-sell"),
    pytest.param(BROKER_EXPORT, _trade("Buy", APPLE, "5", "150,1", "-760", fee="0,99"), (Leg("BUY", "-760", "5", asset=True), Leg("FEE", "-0.99", asset=True, prefix=LEG_FEE)), None, id="exporter-gap-other-than-the-charges"),
    pytest.param(PRIME, _trade("Buy", APPLE, "5", "150,1", "-751,49", fee="0,99"), (Leg("BUY", "-751.49", "5", asset=True), Leg("FEE", "-0.99", asset=True, prefix=LEG_FEE)), None, id="prime-is-never-1.0.0"),
]


class TestTrades:
    """D — a trade is booked on its gross amount, then its fee and its tax as legs on the same security; an exporter trade without details, or with the
    charges already inside its amount (exporter 1.0.0), is booked as it is."""

    @pytest.mark.parametrize("layout", BROKER_LAYOUTS)
    def test_a_trade_books_its_gross_amount_then_its_fee_and_its_tax(self, layout: Layout, tmp_path: Path):
        """``Buy`` and ``Savings plan``: BUY ``+|shares|`` for ``-|amount|``; ``Sell``: SELL ``-|shares|`` for ``+|amount|``. Then FEE ``-|fee|`` when the
        fee is not zero (whatever its sign in the file) and TAX ``-tax`` when the tax is positive, both on the trade's security and prefixed."""
        cases = [
            (_trade("Buy", APPLE, "2", "150", "-300", fee="0,99", tax="1,5"), (Leg("BUY", "-300", "2", asset=True), Leg("FEE", "-0.99", asset=True, prefix=LEG_FEE), Leg("TAX", "-1.5", asset=True, prefix=LEG_TAX)), None),
            (_trade("Savings plan", ALL_WORLD_ACC, "3,69249", "135,41", "-500"), (Leg("BUY", "-500", "3.69249", asset=True),), None),
            (_trade("Sell", APPLE, "5", "180,4", "902", fee="0,99", tax="24,57"), (Leg("SELL", "902", "-5", asset=True), Leg("FEE", "-0.99", asset=True, prefix=LEG_FEE), Leg("TAX", "-24.57", asset=True, prefix=LEG_TAX)), None),
            (_trade("Buy", MSCI_WORLD, "12", "98,45", "-1181,4", fee="-1,49"), (Leg("BUY", "-1181.4", "12", asset=True), Leg("FEE", "-1.49", asset=True, prefix=LEG_FEE)), None),
        ]

        _run(tmp_path, layout, cases)

    @pytest.mark.parametrize("layout", BROKER_LAYOUTS)
    def test_a_negative_tax_on_a_sale_is_given_back_as_a_deposit(self, layout: Layout, tmp_path: Path):
        """A tax below zero is a refund: DEPOSIT ``+|tax|`` without an asset, described ``Tax refund · …``, and ``scalable_tax_refund``; no TAX leg."""
        cases = [
            (_trade("Sell", APPLE, "5", "180,4", "902", fee="0,99", tax="-12,34"), (Leg("SELL", "902", "-5", asset=True), Leg("FEE", "-0.99", asset=True, prefix=LEG_FEE), Leg("DEPOSIT", "12.34", prefix=LEG_REFUND)), TAX_REFUND),
            (_trade("Buy", MSCI_WORLD, "2", "100,5", "-201"), (Leg("BUY", "-201", "2", asset=True),), None),
        ]

        _run(tmp_path, layout, cases)

    def test_scalable_s_own_csv_reads_an_empty_fee_or_tax_as_zero(self, tmp_path: Path):
        """PRIME: ``fee`` and ``tax`` empty mean none; no leg and nothing to say."""
        cases = [
            (_trade("Buy", MSCI_WORLD, "2", "100,5", "-201", fee="", tax=""), (Leg("BUY", "-201", "2", asset=True),), None),
            (_trade("Sell", APPLE, "1", "180,4", "180,4", fee="", tax=""), (Leg("SELL", "180.4", "-1", asset=True),), None),
        ]

        _run(tmp_path, PRIME, cases)

    def test_an_exporter_trade_without_its_details_is_booked_as_it_is(self, tmp_path: Path):
        """Exporter, ``fee`` empty: the details were not read, fee and tax are unknown. The trade on its amount as it is, no FEE or TAX leg (not even for a
        tax that is there), and ``scalable_fees_unknown``; ``0`` is a known zero and says nothing."""
        cases = [
            (_trade("Buy", ALL_WORLD_DIST, "7", "", "-840", fee="", tax=""), (Leg("BUY", "-840", "7", asset=True),), FEES_UNKNOWN),
            (_trade("Sell", APPLE, "1", "180,4", "180,4", fee="", tax="1,5"), (Leg("SELL", "180.4", "-1", asset=True),), FEES_UNKNOWN),
            (_trade("Buy", MSCI_WORLD, "2", "100,5", "-201"), (Leg("BUY", "-201", "2", asset=True),), None),
        ]

        _run(tmp_path, BROKER_EXPORT, cases)

    @pytest.mark.parametrize(("layout", "row", "legs", "notice"), FEE_IN_AMOUNT_CASES)
    def test_charges_inside_the_amount_are_left_there(self, layout: Layout, row: Row, legs: Tuple[Leg, ...], notice: Optional[str], tmp_path: Path):
        """Exporter trade whose ``|amount|`` differs from shares x price by more than a cent, and by the fee plus the positive tax within a cent: booked on
        its amount as it is, no FEE or TAX leg, ``scalable_fee_in_amount``. A gap of another size, or Scalable's own CSV: the usual trade and legs."""
        _run(tmp_path, layout, [(row, legs, notice)])


class TestIncome:
    """D — dividends and interest are booked gross, ``|amount| + |tax|``, with the tax withheld as a TAX leg; without the tax, as credited."""

    @pytest.mark.parametrize("layout", BROKER_LAYOUTS)
    def test_a_dividend_is_booked_gross_with_the_tax_withheld(self, layout: Layout, tmp_path: Path):
        """``Distribution``: DIVIDEND ``+(|amount| + |tax|)`` on the security of ``isin``, then TAX ``-|tax|`` on it when the tax is not zero, whatever its sign in the file."""
        cases = [
            (_income("Distribution", TELEKOM, "63,26", tax="22,74"), (Leg("DIVIDEND", "86", asset=True), Leg("TAX", "-22.74", asset=True, prefix=LEG_TAX)), None),
            (_income("Distribution", TELEKOM, "31,63", tax="-11,37"), (Leg("DIVIDEND", "43", asset=True), Leg("TAX", "-11.37", asset=True, prefix=LEG_TAX)), None),
            (_income("Distribution", ALL_WORLD_DIST, "4,1", tax="0"), (Leg("DIVIDEND", "4.1", asset=True),), None),
        ]

        _run(tmp_path, layout, cases)

    def test_an_exporter_dividend_without_its_tax_is_booked_net(self, tmp_path: Path):
        """``tax`` empty in an exporter file: DIVIDEND ``+|amount|`` as credited, and ``scalable_dividends_net``."""
        cases = [(_income("Distribution", TELEKOM, "63,26", tax=""), (Leg("DIVIDEND", "63.26", asset=True),), DIVIDENDS_NET)]

        _run(tmp_path, BROKER_EXPORT, cases)

    @pytest.mark.parametrize(("layout", "code"), EVERY_LAYOUT)
    def test_interest_is_booked_gross_with_the_tax_withheld(self, layout: Layout, code: str, tmp_path: Path):
        """``Interest``: INTEREST ``+(|amount| + |tax|)``, then TAX ``-|tax|`` when the tax is not zero; neither names an asset."""
        cases = [
            (_cash("Interest", "2,58", tax="0,92"), (Leg("INTEREST", "3.5"), Leg("TAX", "-0.92", prefix=LEG_TAX)), None),
            (_cash("Interest", "1,5", tax="0"), (Leg("INTEREST", "1.5"),), None),
        ]

        _run(tmp_path, layout, cases, code=code)

    @pytest.mark.parametrize(("layout", "code"), EVERY_LAYOUT)
    def test_interest_without_its_tax_is_booked_as_credited(self, layout: Layout, code: str, tmp_path: Path):
        """``tax`` empty: INTEREST ``+|amount|``. An exporter file says the details are unknown (``scalable_fees_unknown``); Scalable's own CSV says nothing."""
        cases = [(_cash("Interest", "3,12", tax=""), (Leg("INTEREST", "3.12"),), FEES_UNKNOWN if layout.exporter else None)]

        _run(tmp_path, layout, cases, code=code)


class TestCashRows:
    """D — cash rows follow the sign of their amount. The expected sign keeps the row's type; a contradicting sign, or a cash type the plugins do not
    know, gives a DEPOSIT or a WITHDRAWAL by the sign with ``scalable_cash_by_sign``; a positive tax is a refund; at zero there is nothing to book."""

    @pytest.mark.parametrize(("layout", "code"), EVERY_LAYOUT)
    def test_cash_rows_follow_the_sign_of_their_amount(self, layout: Layout, code: str, tmp_path: Path):
        cases = [
            (_cash("Deposit", "500"), (Leg("DEPOSIT", "500"),), None),
            (_cash("Withdrawal", "-200"), (Leg("WITHDRAWAL", "-200"),), None),
            (_cash("Fee", "-4,99"), (Leg("FEE", "-4.99"),), None),
            (_cash("Taxes", "-8,4"), (Leg("TAX", "-8.4"),), None),
            (_cash("Taxes", "12,5"), (Leg("DEPOSIT", "12.5"),), TAX_REFUND),
            (_cash("Deposit", "-50"), (Leg("WITHDRAWAL", "-50"),), CASH_BY_SIGN),
            (_cash("Withdrawal", "60"), (Leg("DEPOSIT", "60"),), CASH_BY_SIGN),
            (_cash("Fee", "2,5"), (Leg("DEPOSIT", "2.5"),), CASH_BY_SIGN),
            (_cash("Interest", "-0,5", tax="0"), (Leg("WITHDRAWAL", "-0.5"),), CASH_BY_SIGN),
            (_cash("Reward", "25"), (Leg("DEPOSIT", "25"),), CASH_BY_SIGN),
            (_cash("Reward", "-3"), (Leg("WITHDRAWAL", "-3"),), CASH_BY_SIGN),
            (_cash("Deposit", "0"), (), NOT_IMPORTED),
        ]

        _run(tmp_path, layout, cases, code=code)

    def test_transfers_between_the_accounts_are_listed(self, tmp_path: Path):
        """``lf_subtype`` ``CASH_TRANSFER_IN`` and ``CASH_TRANSFER_OUT``: a DEPOSIT and a WITHDRAWAL like any other, listed in ``scalable_internal_transfers``."""
        cases = [
            (_cash("Deposit", "1000", subtype="CASH_TRANSFER_IN", description="Interner Übertrag"), (Leg("DEPOSIT", "1000"),), INTERNAL_TRANSFERS),
            (_cash("Withdrawal", "-300", subtype="CASH_TRANSFER_OUT", description="Interner Übertrag"), (Leg("WITHDRAWAL", "-300"),), INTERNAL_TRANSFERS),
            (_cash("Deposit", "5000", subtype="DEPOSIT"), (Leg("DEPOSIT", "5000"),), None),
        ]

        _run(tmp_path, DEPOSIT_EXPORT, cases, code=DEPOSIT_CODE)


class TestRowsNotImported:
    """D — what the plugins do not book is listed, never dropped in silence."""

    @pytest.mark.parametrize("layout", BROKER_LAYOUTS)
    def test_security_transfers_corporate_actions_and_unknown_types_are_listed(self, layout: Layout, tmp_path: Path):
        """``Security transfer``, ``Corporate action`` and a type the plugins do not know on a security: ``scalable_not_imported``."""
        cases = [
            (_trade("Security transfer", ALL_WORLD_DIST, "7", "", "0"), (), NOT_IMPORTED),
            (_trade("Corporate action", TELEKOM, "10", "", "0"), (), NOT_IMPORTED),
            (_trade("Zorglub", APPLE, "1", "150,1", "-150,1"), (), NOT_IMPORTED),
            (_cash("Deposit", "20"), (Leg("DEPOSIT", "20"),), None),
        ]

        _run(tmp_path, layout, cases)

    @pytest.mark.parametrize("layout", BROKER_LAYOUTS)
    def test_rows_that_cannot_be_read_are_listed(self, layout: Layout, tmp_path: Path):
        """No date, no amount, no currency, a trade without shares, a trade or a dividend without ISIN and description: ``scalable_unreadable_rows``."""
        cases = [
            (_cash("Deposit", "10", day=""), (), UNREADABLE_ROWS),
            (_cash("Deposit", ""), (), UNREADABLE_ROWS),
            (_cash("Deposit", "12", currency=""), (), UNREADABLE_ROWS),
            (_trade("Buy", APPLE, "", "150,1", "-750,5"), (), UNREADABLE_ROWS),
            (replace(_trade("Buy", APPLE, "5", "150,1", "-750,5"), isin="", description=""), (), UNREADABLE_ROWS),
            (replace(_income("Distribution", TELEKOM, "5"), isin="", description=""), (), UNREADABLE_ROWS),
            (_cash("Deposit", "11"), (Leg("DEPOSIT", "11"),), None),
        ]

        _run(tmp_path, layout, cases)


class TestTheFileAsAWhole:
    """D — what is said of a file rather than of a row: several overnight accounts, an export without rows."""

    def test_several_overnight_accounts_are_named_and_all_their_rows_imported(self, tmp_path: Path):
        """``lf_account_index`` 1 and 2: ``scalable_several_overnight_accounts``, a warning with ``count`` 2; every row imported all the same."""
        cases = [
            (_cash("Interest", "1,5", tax="0,4"), (Leg("INTEREST", "1.9"), Leg("TAX", "-0.4", prefix=LEG_TAX)), None),
            (_cash("Deposit", "100", account_index="2"), (Leg("DEPOSIT", "100"),), None),
            (_cash("Withdrawal", "-30", account_index="2"), (Leg("WITHDRAWAL", "-30"),), None),
        ]

        _run(tmp_path, DEPOSIT_EXPORT, cases, code=DEPOSIT_CODE, accounts=2)

    @pytest.mark.parametrize("layout", [pytest.param(BROKER_EXPORT, id="broker-header"), pytest.param(DEPOSIT_EXPORT, id="deposit-header")])
    @pytest.mark.parametrize("code", PLUGIN_CODES)
    def test_an_export_without_rows_parses_to_nothing(self, layout: Layout, code: str, tmp_path: Path):
        """The exporter's header and no row: both plugins read it, and the parse gives no transaction, no asset and no issue, without an error."""
        path = _write(tmp_path, layout, [])
        assert _plugin(code).can_parse(path) is True, f"premise: {code} reads an exporter file without rows"

        out = _parse(code, path)

        assert (out.transactions, out.extracted_assets, out.validation_issues) == ([], {}, [])


# The descriptions test_a_description_names_its_row expects, written out, by amount.
DESCRIBED = {
    "prime": {
        "40": f"Deposit{SEP}ref SCALTEST0000001",
        "41": "Einzahlung",
        "42": f"Einzahlung{SEP}ref REF0042",
        "-0.99": f"Order fee{SEP}Apple Inc.{SEP}ref SCALTEST9999999",
        "-1.5": f"Tax{SEP}Apple Inc.{SEP}ref SCALTEST9999999",
    },
    "broker-export": {
        "40": f"Deposit{SEP}id synthT0000000000000001",
        "41": f"Einzahlung{SEP}id synthT0000000000000002",
        "42": f"Einzahlung{SEP}id synthT0000000000000003{SEP}ref REF0042",
        "-0.99": f"Order fee{SEP}Apple Inc.{SEP}id synthT0000000000000004{SEP}ref SCALTEST9999999",
        "-1.5": f"Tax{SEP}Apple Inc.{SEP}id synthT0000000000000004{SEP}ref SCALTEST9999999",
    },
}


class TestDescriptionsAndAssets:
    """D — the description names its row, so two identical movements stay distinct; one fake asset per security, by ISIN or else by name."""

    @pytest.mark.parametrize("layout", BROKER_LAYOUTS)
    def test_a_description_names_its_row(self, layout: Layout, tmp_path: Path):
        """The row's text, its type when the text is empty; ``id <lf_id>`` in an exporter file; ``ref <reference>`` only when there is one; the legs'
        ``Order fee`` and ``Tax`` before it."""
        cases = [
            (_cash("Deposit", "40", description=""), (Leg("DEPOSIT", "40"),), None),
            (_cash("Deposit", "41", description="Einzahlung", reference=""), (Leg("DEPOSIT", "41"),), None),
            (_cash("Deposit", "42", description="Einzahlung", reference="REF0042"), (Leg("DEPOSIT", "42"),), None),
            (_trade("Buy", APPLE, "2", "150", "-300", fee="0,99", tax="1,5", reference="SCALTEST9999999"), (Leg("BUY", "-300", "2", asset=True), Leg("FEE", "-0.99", asset=True, prefix=LEG_FEE), Leg("TAX", "-1.5", asset=True, prefix=LEG_TAX)), None),
        ]

        out = _run(tmp_path, layout, cases)

        assert {_num(tx.cash.amount): tx.description for tx in out.transactions if tx.type.value != "BUY"} == DESCRIBED[layout.name]

    def test_a_security_without_isin_is_one_asset_by_its_name(self, tmp_path: Path):
        """Without an ISIN the description keys the asset: two purchases of one fund share a fake id, another fund has its own; the name is extracted, no ISIN."""
        cases = [
            (Row(type="Buy", asset_type="Security", description="Private Fund A", shares="1", price="100", amount="-100", fee="0", tax="0"), (Leg("BUY", "-100", "1", asset=True),), None),
            (Row(type="Buy", asset_type="Security", description="Private Fund B", shares="2", price="100", amount="-200", fee="0", tax="0"), (Leg("BUY", "-200", "2", asset=True),), None),
            (Row(type="Buy", asset_type="Security", description="Private Fund A", shares="3", price="100", amount="-300", fee="0", tax="0"), (Leg("BUY", "-300", "3", asset=True),), None),
        ]

        out = _run(tmp_path, PRIME, cases)

        extracted = {fake_id: (info.extracted_isin or None, info.extracted_name) for fake_id, info in out.extracted_assets.items()}
        assert extracted == {FAKE_ASSET_ID_BASE: (None, "Private Fund A"), FAKE_ASSET_ID_BASE - 1: (None, "Private Fund B")}

    def test_only_the_rows_imported_use_a_fake_id(self, tmp_path: Path):
        """From the top, the first security a transaction names gets ``FAKE_ASSET_ID_BASE``: a pending order, a reversal or a security transfer before it
        uses no id, and a security only they name is not extracted."""
        cases = [
            (_trade("Buy", ALL_WORLD_ACC, "3", "135,2", "-405,6", status="Pending"), (), NOT_EXECUTED),
            (_trade("Buy", TELEKOM, "4", "25", "-100", cancellation="true"), (), REVERSAL),
            (_trade("Security transfer", ALL_WORLD_DIST, "7", "", "0"), (), NOT_IMPORTED),
            (_trade("Buy", MSCI_WORLD, "2", "100,5", "-201"), (Leg("BUY", "-201", "2", asset=True),), None),
            (_trade("Buy", ALL_WORLD_ACC, "1", "135,2", "-135,2"), (Leg("BUY", "-135.2", "1", asset=True),), None),
        ]

        out = _run(tmp_path, BROKER_EXPORT, cases)

        assert {fake_id: info.extracted_isin for fake_id, info in out.extracted_assets.items()} == {FAKE_ASSET_ID_BASE: MSCI_WORLD, FAKE_ASSET_ID_BASE - 1: ALL_WORLD_ACC}
