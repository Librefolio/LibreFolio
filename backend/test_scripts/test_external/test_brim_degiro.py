"""
Test Suite: the DEGIRO plugin rewritten — ``broker_degiro`` (issue #35, workstream L)

Written red-first, before the rewrite (plan §7 step 2, §8). The plugin exists today, but it
reads the Dutch header only, takes the amount of a row from its balance, books every amount in
euros, drops the currency conversions and reads ``1,1734`` as eleven thousand. Each test pins
the approved design (plan §2, decisions D1–D10 as recommended, §0.1) and fails on its own
assertion until the rewrite lands. What the rewrite adds to the module (``_detect_language``,
``_MESSAGES``, the ``decimal_hint`` of ``_parse_degiro_number``) is reached with ``getattr``
inside the tests, never at import time: the module always collects. A test whose docstring
starts with "Guard" passes before and after the rewrite (what must not change); one that starts
with "Fixture guard" checks this file's own expectations against the samples, never the plugin.

What is pinned:

- A. recognition by structure, in any language: the Account Statement (12 columns, the 9th and
  11th unnamed, ``isin`` in the 5th, a first row dated ``DD-MM-YYYY`` at ``HH:MM``, ``,`` or
  ``;``) and the orders list (at least 16 columns, ``isin`` in the 4th); the other samples and
  the near misses refused; DEGIRO detected over the generic CSV; ``cannot_parse_reason``
  agreeing with ``can_parse`` (D8);
- B. the two samples line by line: the Dutch collage (57 transactions, two notices) and the
  synthetic English statement (17 transactions, one notice), compared as multisets, never by
  position; dates, descriptions, tags, assets, notices and their evidence;
- C. the classification, in its order: no amount, currency legs, trades by their form (any
  verb), charges of an order, the multilingual word table (taxes before dividends, case,
  accents and mojibake ignored), the rows known but not importable (D5), the sign rule, the
  unknown rows; continuation lines merged;
- D. the currency conversions (D2): two ``FX_CONVERSION`` per conversion with one
  ``link_uuid``, one description and the plugin's tags; paired by Order Id, or by date and
  time, the adjacent candidate first and a fee never; unpaired or ambiguous legs listed; a
  ``link_uuid`` that is the same on every parse and on a Windows-1252 copy;
- E. the numbers (D1): value by value when certain, the file's decimal mark for the ambiguous;
- F. the languages and the messages (D4): the header decides, English by default; the
  catalogue ``_MESSAGES``; no i18n key that would override it; the orders list (D9);
- G. identity: version 2.0.0, code, priority, and the two helpers kept.

Every input is a sample of ``sample_reports/`` or is written in ``tmp_path``; every value of the
synthetic files is invented. No server, no database: this module is pure. How the pairs go
through the batch (validate, commit, reciprocal links) is in ``test_api/test_brim_api.py``,
category 16.

Plan: LibreFolio_developer_journal/Release_2/phases/31_brimDegiro/plan-phase00BrimDegiro.prompt.md
"""

from __future__ import annotations

import csv
import importlib
import inspect
import io
import json
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.schemas.brim import BRIMNotice, BRIMParseOutput, is_fake_asset_id
from backend.app.schemas.transactions import TXCreateItem
from backend.app.services.brim_provider import BRIMParseError, BRIMProvider
from backend.app.services.provider_registry import BRIMProviderRegistry

# =============================================================================
# CONSTANTS
# =============================================================================

PLUGIN_CODE = "broker_degiro"
PLUGIN_MODULE = "backend.app.services.brim_providers.broker_degiro"
PLUGIN_VERSION = "2.0.0"
SAMPLE_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"
NL_SAMPLE = SAMPLE_DIR / "degiro-export.csv"
EN_SAMPLE = SAMPLE_DIR / "degiro-account-en.csv"
I18N_DIR = PROJECT_ROOT / "frontend" / "src" / "lib" / "i18n"
BROKER_ID = 1
TAGS = ["import", "degiro"]

# The notice codes of the design (§2.4, §2.7, D5, D7, D9): one notice per code, its rows grouped.
UNKNOWN_ROWS = "degiro_unknown_rows"
NOT_IMPORTED = "degiro_not_imported"
FLATEX_WITHDRAWAL = "degiro_flatex_withdrawal"
UNPAIRED_FX = "degiro_unpaired_fx"
UNEXPECTED_SIGN = "degiro_unexpected_sign"
QUANTITY_UNREADABLE = "degiro_quantity_unreadable"
ORDERS_LIST = "degiro_orders_list"
NOTICE_CODES = (UNKNOWN_ROWS, NOT_IMPORTED, FLATEX_WITHDRAWAL, UNPAIRED_FX, UNEXPECTED_SIGN, QUANTITY_UNREADABLE, ORDERS_LIST)
# The languages of the message catalogue (D4, resolved by the research of §1.8); any other header speaks English.
CATALOGUE_LANGUAGES = ("en", "nl", "de", "fr", "es")
# The outcome of a row that left no transaction and no notice.
SKIPPED = "skipped"

# The Account Statement headers, verified in the sources of §1.8: 12 columns, the 9th and 11th unnamed.
EN_HEADER = ("Date", "Time", "Value date", "Product", "ISIN", "Description", "FX", "Change", "", "Balance", "", "Order Id")
NL_HEADER = ("Datum", "Tijd", "Valutadatum", "Product", "ISIN", "Omschrijving", "FX", "Mutatie", "", "Saldo", "", "Order Id")
DE_HEADER = ("Datum", "Uhrzeit", "Valutadatum", "Produkt", "ISIN", "Beschreibung", "FX", "Änderung", "", "Saldo", "", "Order-ID")
FR_HEADER = ("Date", "Heure", "Date de", "Produit", "Code ISIN", "Description", "FX", "Mouvements", "", "Solde", "", "ID Ordre")
ES_HEADER = ("Fecha", "Hora", "Fecha valor", "Producto", "ISIN", "Descripción", "Tipo", "Variación", "", "Saldo", "", "ID Orden")
PT_HEADER = ("Data", "Hora", "Data Valor", "Produto", "ISIN", "Descrição", "T.", "Mudança", "", "Saldo", "", "ID da Ordem")
IT_HEADER = ("Data", "Ora", "Data Valore", "Prodotto", "ISIN", "Descrizione", "Borsa", "Variazioni", "", "Saldo", "", "ID Ordine")
STATEMENT_HEADERS = {"en": EN_HEADER, "nl": NL_HEADER, "de": DE_HEADER, "fr": FR_HEADER, "es": ES_HEADER, "pt": PT_HEADER, "it": IT_HEADER}
# The language the notices of a file with that header speak: PT and IT have no catalogue, they speak English.
MESSAGE_LANGUAGE = {"en": "en", "nl": "nl", "de": "de", "fr": "fr", "es": "es", "pt": "en", "it": "en"}

# The orders list ("Transactions" export): the two layouts of the brief, header as written (the Dutch one ends with a comma).
ORDERS_EN = "Date;Time;Product;ISIN;Reference exchange;Venue;Quantity;Price;;Local value;;Value EUR;Exchange rate;AutoFX Fee;Transaction and/or third party fees EUR;Total EUR;Order ID"
ORDERS_EN_ROWS = (
    "08-09-2025;15:31;APPLE INC;US0378331005;NDQ;XNAS;5;180,25;USD;-901,25;USD;-770,16;1,1702;-1,93;-1,00;-773,09;5e1f0c2a-0101-4b7d-9c3e-1a2b3c4d5e6f",
    "25-08-2025;11:04;VANGUARD FTSE ALL-WORLD UCITS ETF;IE00BK5BQT80;EAM;XAMS;-3;118,75;EUR;356,25;EUR;356,25;;0,00;-1,00;355,25;5e1f0c2a-0102-4b7d-9c3e-1a2b3c4d5e6f",
)
ORDERS_NL = "Datum,Tijd,Product,ISIN,Beurs,Uitvoeringsplaats,Aantal,Koers,,Lokale waarde,,Waarde EUR,Wisselkoers,AutoFX Kosten,Transactiekosten en/of kosten van derden EUR,Totaal EUR,Order ID,"
ORDERS_NL_ROWS = (
    '03-04-2025,09:04,VANGUARD FTSE AW,IE00B3RBWM25,EAM,XAMS,1,"97,93",EUR,"-97,93",EUR,"-97,93",,"0,00","-2,00","-99,93",5e1f0c2a-0103-4b7d-9c3e-1a2b3c4d5e6f,',
    '25-07-2025,14:31,ISHARES KOREA,IE00B0M63391,EAM,XAMS,1,"42,53",EUR,"-42,53",EUR,"-42,53",,"0,00","-1,00","-43,53",5e1f0c2a-0104-4b7d-9c3e-1a2b3c4d5e6f,',
)

# Instruments of the synthetic files (public identifiers; every amount, date and Order Id around them is invented).
APPLE, APPLE_NAME = "US0378331005", "APPLE INC"
SP500, SP500_NAME = "IE00B5BMR087", "ISHARES CORE S&P 500 UCITS ETF"
SAP, SAP_NAME = "DE0007164600", "SAP SE"
KBC, KBC_NAME = "BE0003565737", "KBC GROEP"
VODAFONE, VODAFONE_NAME = "GB00BH4HKS39", "VODAFONE GROUP"
CASH_FUND, CASH_FUND_NAME = "NL0010661914", "EUR CASH FUND FUNDSHARE"


def _order(number: int) -> str:
    """An invented Order Id, one per ``number``."""
    return f"5e1f0c2a-{number:04d}-4b7d-9c3e-1a2b3c4d5e6f"


# =============================================================================
# HELPERS — the plugin and the new module attributes are reached inside each test
# =============================================================================


def _plugin() -> BRIMProvider:
    """The registered DEGIRO plugin."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    assert plugin is not None, f"no BRIM plugin is registered as {PLUGIN_CODE} ({PLUGIN_MODULE})"
    return plugin


def _module_attribute(name: str) -> Any:
    """``name`` of the plugin module, read when the test runs: a missing attribute fails the test, never the collection."""
    value = getattr(importlib.import_module(PLUGIN_MODULE), name, None)
    assert value is not None, f"{PLUGIN_MODULE} has no {name}: not implemented yet (DEGIRO rewrite, issue #35)"
    return value


def _messages() -> Dict[str, Dict[str, str]]:
    """The message catalogue, ``_MESSAGES[language][code]``."""
    messages = _module_attribute("_MESSAGES")
    assert isinstance(messages, dict), f"_MESSAGES is a {type(messages).__name__}, not a dict of languages"
    return messages


def _parse(path: Path) -> BRIMParseOutput:
    """The plugin's ``parse`` of ``path`` on broker 1; a ``BRIMParseError`` fails the test with its message."""
    try:
        return _plugin().parse(path, broker_id=BROKER_ID)
    except BRIMParseError as exc:
        raise AssertionError(f"parse({path.name}) raised BRIMParseError: {exc.message}") from exc


def _num(value: Any) -> Optional[str]:
    """A number as plain text without trailing zeros, so that ``27.80``, ``27.8`` and ``Decimal("27.80")`` compare equal and print readably."""
    if value is None:
        return None
    number = Decimal(str(value))
    return "0" if number == 0 else format(number.normalize(), "f")


def _plain_number(text: str) -> Decimal:
    """This file's own reading of an amount it wrote or found in a sample (never the plugin's): with ``.`` and ``,`` the last one is the decimal mark, a lone ``,`` is decimal."""
    text = text.strip()
    if "," in text and "." in text:
        text = text.replace(".", "") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    return Decimal(text.replace(",", "."))


def _day(text: str) -> date:
    """A ``DD-MM-YYYY`` cell as a date."""
    return datetime.strptime(text, "%d-%m-%Y").date()


def _raw_lines(path: Path, delimiter: str) -> Dict[int, List[str]]:
    """The cells of every physical line of a sample, by 1-based line number (the header is line 1), read by the csv module."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return {number: next(csv.reader([line], delimiter=delimiter)) for number, line in enumerate(lines, start=1)}


def _cash_key(currency: Optional[str], amount: Any) -> Tuple[Optional[str], Optional[str]]:
    """``(currency, amount)`` of a movement, the amount as ``_num`` writes it."""
    return currency, _num(amount)


def _tx_cash(tx: TXCreateItem) -> Tuple[Optional[str], Optional[str]]:
    return _cash_key(tx.cash.code, tx.cash.amount) if tx.cash is not None else (None, None)


def _isin(out: BRIMParseOutput, tx: TXCreateItem) -> Optional[str]:
    """The ISIN of the asset a transaction names (``None``: no asset); an asset missing from ``extracted_assets`` reads ``<missing asset N>``."""
    if tx.asset_id is None:
        return None
    info = out.extracted_assets.get(tx.asset_id)
    return info.extracted_isin if info is not None else f"<missing asset {tx.asset_id}>"


def _asset_ids_by_isin(out: BRIMParseOutput) -> Dict[Optional[str], set]:
    """The fake asset ids the transactions name, by the ISIN of their extracted asset."""
    ids: Dict[Optional[str], set] = defaultdict(set)
    for tx in out.transactions:
        if tx.asset_id is not None:
            ids[_isin(out, tx)].add(tx.asset_id)
    return dict(ids)


def _diff(actual: Counter, expected: Counter) -> str:
    """What ``actual`` misses and what it has too much of, element by element."""
    missing = sorted((expected - actual).elements(), key=repr)
    extra = sorted((actual - expected).elements(), key=repr)
    return f"missing {len(missing)}: {missing}; unexpected {len(extra)}: {extra}"


def _is_one_sentence(reason: object) -> bool:
    """One short English sentence, as ``cannot_parse_reason`` answers: a non-empty single line, no blank around it, lowercase start, no final period."""
    return isinstance(reason, str) and reason != "" and reason == reason.strip() and "\n" not in reason and reason[0] == reason[0].lower() and not reason.endswith(".")


# =============================================================================
# SYNTHETIC ACCOUNT STATEMENTS — written in tmp_path the way the user downloads them
# =============================================================================


@dataclass(frozen=True)
class Row:
    """One data row of a synthetic Account Statement, by position: the 12 columns DEGIRO writes.

    Without an amount the currency of the change stays empty too, as on DEGIRO's informative rows.
    """

    description: str
    amount: str = ""
    currency: str = "EUR"
    isin: str = ""
    product: str = ""
    order_id: str = ""
    fx: str = ""
    day: str = "22-09-2025"
    time: str = "10:00"
    balance: str = "100,00"

    def cells(self) -> List[str]:
        change_currency = self.currency if self.amount else ""
        return [self.day, self.time, self.day, self.product, self.isin, self.description, self.fx, change_currency, self.amount, self.currency, self.balance, self.order_id]


# A data row is a ``Row`` or raw cells (a continuation line, a malformed row).
Cells = Union[Row, Sequence[str]]


def _continuation(*, description: str = "", order_id: str = "") -> List[str]:
    """A continuation line: date and time empty, the rest of a cell DEGIRO wrapped (a description, an Order Id)."""
    return ["", "", "", "", "", description, "", "", "", "", "", order_id]


def _cells(row: Cells) -> List[str]:
    return row.cells() if isinstance(row, Row) else list(row)


def _csv_text(rows: Sequence[Sequence[str]], delimiter: str, newline: str) -> str:
    """Rows as a spreadsheet writes them: a cell is quoted only when it holds the delimiter or a quote."""
    buffer = io.StringIO()
    csv.writer(buffer, delimiter=delimiter, lineterminator=newline).writerows(rows)
    return buffer.getvalue()


def _statement_bytes(header: Sequence[str], rows: Sequence[Cells], *, delimiter: str = ";", newline: str = "\r\n", encoding: str = "utf-8") -> bytes:
    """An Account Statement as the user downloads it by default: ``;``, CRLF, decimal comma."""
    return _csv_text([list(header), *(_cells(row) for row in rows)], delimiter, newline).encode(encoding)


def _write(folder: Path, rows: Sequence[Cells], *, header: Sequence[str] = EN_HEADER, name: str = "Account.csv", **shape: str) -> Path:
    """Write a synthetic Account Statement in ``folder``: data row ``i`` lands on physical line ``i + 2``."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(_statement_bytes(header, rows, **shape))
    return path


def _orders_bytes(header: str, rows: Sequence[str], newline: str) -> bytes:
    """An orders list, its lines written as given."""
    return newline.join([header, *rows]).encode("utf-8") + newline.encode("utf-8")


def _scenario(cases: Sequence[Tuple[Cells, Optional[str]]]) -> Tuple[List[Cells], Dict[int, str]]:
    """``(row, expected outcome)`` cases split into the rows to write and the outcome expected on each ``Row``'s line."""
    rows = [row for row, _ in cases]
    expected = {index + 2: outcome for index, (row, outcome) in enumerate(cases) if isinstance(row, Row)}
    return rows, expected


def _word_rows(words: Sequence[str], sign: str, *, currency: str = "EUR", isin: str = "", product: str = "") -> List[Row]:
    """One row per description, each with its own amount and minute, so that every transaction maps back to its row."""
    return [Row(word, amount=f"{sign}{index},{index:02d}", currency=currency, isin=isin, product=product, time=f"10:{index:02d}") for index, word in enumerate(words, start=1)]


def _every_line(rows: Sequence[Cells], outcome: str) -> Dict[int, str]:
    """The same expected outcome for every ``Row``."""
    return {index + 2: outcome for index, row in enumerate(rows) if isinstance(row, Row)}


# =============================================================================
# OUTCOMES — what became of each written row
# =============================================================================


def _row_numbers(notice: BRIMNotice) -> List[int]:
    """The source lines a notice lists: the ``row_numbers`` of its first evidence table."""
    return list(notice.evidence[0].row_numbers) if notice.evidence else []


def _noticed_lines(out: BRIMParseOutput) -> Dict[int, List[str]]:
    """The codes of the notices that list each line."""
    noticed: Dict[int, List[str]] = defaultdict(list)
    for notice in out.warnings:
        for line in _row_numbers(notice):
            noticed[line].append(notice.code)
    return noticed


def _written_rows(rows: Sequence[Cells]) -> Dict[int, Row]:
    """The ``Row`` of every physical line that has one (not the continuation lines)."""
    written = {index + 2: row for index, row in enumerate(rows) if isinstance(row, Row)}
    keys = [_cash_key(row.currency, _plain_number(row.amount)) for row in written.values() if row.amount and _plain_number(row.amount) != 0]
    assert len(keys) == len(set(keys)), f"fixture: two written rows share a currency and an amount, their transactions cannot be told apart: {sorted(keys)}"
    return written


def _types_by_cash(out: BRIMParseOutput) -> Dict[Tuple[Optional[str], Optional[str]], List[str]]:
    """The types of the transactions, by currency and amount."""
    found: Dict[Tuple[Optional[str], Optional[str]], List[str]] = defaultdict(list)
    for tx in out.transactions:
        found[_tx_cash(tx)].append(tx.type.value)
    return found


def _outcomes(out: BRIMParseOutput, rows: Sequence[Cells]) -> Tuple[Dict[int, str], List[str]]:
    """What became of each written ``Row``, by physical line, and the transactions no written row accounts for.

    A row's outcome is the type of the transaction that carries its currency and amount, the code of the notice
    that lists its line, both joined by ``+`` when both happen (a defect), or ``skipped``.
    """
    by_cash = _types_by_cash(out)
    noticed = _noticed_lines(out)
    outcomes = {}
    for line, row in _written_rows(rows).items():
        found = by_cash.pop(_cash_key(row.currency, _plain_number(row.amount)), []) if row.amount else []
        outcomes[line] = "+".join([*found, *noticed.get(line, [])]) or SKIPPED
    unaccounted = [f"{kind} {currency} {amount}" for (currency, amount), kinds in by_cash.items() for kind in kinds]
    return outcomes, unaccounted


def _assert_outcomes(out: BRIMParseOutput, rows: Sequence[Cells], expected: Dict[int, str]) -> None:
    """Every written row has its expected outcome, every transaction comes from a written row, and every line a notice lists holds one."""
    outcomes, unaccounted = _outcomes(out, rows)
    wrong = [f"line {line} {rows[line - 2].description!r}: expected {outcome}, got {outcomes[line]}" for line, outcome in expected.items() if outcomes[line] != outcome]
    stray = sorted(set(_noticed_lines(out)) - set(expected))
    assert not wrong and not unaccounted and not stray, f"{len(wrong)} of {len(expected)} row(s) classified wrong: {wrong}; transactions that no written row accounts for: {unaccounted}; notices listing lines without a written row: {stray}"


def _of_type(out: BRIMParseOutput, kind: str) -> List[TXCreateItem]:
    return [tx for tx in out.transactions if tx.type.value == kind]


# =============================================================================
# NOTICES
# =============================================================================


def _notices(out: BRIMParseOutput) -> Dict[str, List[BRIMNotice]]:
    """The notices of a parse, by code."""
    found: Dict[str, List[BRIMNotice]] = defaultdict(list)
    for notice in out.warnings:
        found[notice.code].append(notice)
    return dict(found)


def _the_notice(out: BRIMParseOutput, code: str) -> BRIMNotice:
    """The one notice of ``code``: the rows of one reason are grouped in one notice."""
    found = _notices(out).get(code, [])
    assert len(found) == 1, f"{len(found)} notice(s) {code}, one expected; the parse gave {[(notice.code, notice.message) for notice in out.warnings]}"
    return found[0]


def _context(notice: BRIMNotice) -> Dict[str, Any]:
    """The two context keys the contract names, ``language`` and ``count``."""
    context = notice.context or {}
    return {key: context.get(key) for key in ("language", "count")}


def _notice_context_problems(notice: BRIMNotice, language: str) -> List[str]:
    """Where a notice breaks the contract outside its evidence: severity ``warning``, ``context`` with the file's language and the count of its rows."""
    problems = [] if notice.severity == "warning" else [f"severity {notice.severity!r}, not 'warning'"]
    expected = {"language": language, "count": len(_row_numbers(notice))}
    if _context(notice) != expected:
        problems.append(f"context {_context(notice)}, expected {expected}")
    return problems


def _notice_evidence_problems(notice: BRIMNotice, raw: Dict[int, List[str]]) -> List[str]:
    """Where the first evidence table breaks the contract: 12 headers, one row of the 12 file cells per listed line."""
    if not notice.evidence:
        return ["no evidence table"]
    evidence = notice.evidence[0]
    problems = [] if len(evidence.headers) == 12 else [f"{len(evidence.headers)} evidence headers, not 12"]
    if len(evidence.rows) != len(evidence.row_numbers):
        problems.append(f"{len(evidence.rows)} evidence rows for {len(evidence.row_numbers)} row numbers")
    for number, cells in zip(evidence.row_numbers, evidence.rows, strict=False):
        if [cell.strip() for cell in cells] != [cell.strip() for cell in raw.get(number, [])]:
            problems.append(f"line {number}: the evidence row {cells} is not the file's {raw.get(number)}")
    return problems


def _message_problems(notice: BRIMNotice, language: str) -> List[str]:
    """Where the message is not ``_MESSAGES[language][code].format(n=count)``."""
    template = _messages().get(language, {}).get(notice.code)
    if template is None:
        return [f"_MESSAGES[{language!r}] has no {notice.code!r}"]
    expected = template.format(n=(notice.context or {}).get("count"))
    return [] if notice.message == expected else [f"message {notice.message!r}, not _MESSAGES[{language!r}][{notice.code!r}] = {expected!r}"]


# =============================================================================
# CURRENCY PAIRS
# =============================================================================


def _fx_groups(out: BRIMParseOutput) -> Dict[Optional[str], List[TXCreateItem]]:
    """The FX_CONVERSION transactions, grouped by ``link_uuid``."""
    groups: Dict[Optional[str], List[TXCreateItem]] = defaultdict(list)
    for tx in _of_type(out, "FX_CONVERSION"):
        groups[tx.link_uuid].append(tx)
    return dict(groups)


def _pair_cash(group: Sequence[TXCreateItem]) -> frozenset:
    """The currencies and amounts of a group of legs, in no order."""
    return frozenset(_tx_cash(tx) for tx in group)


def _links(out: BRIMParseOutput) -> Dict[Tuple[Optional[str], Optional[str]], Optional[str]]:
    """The ``link_uuid`` of every FX_CONVERSION leg, by currency and amount."""
    return {_tx_cash(tx): tx.link_uuid for tx in _of_type(out, "FX_CONVERSION")}


def _is_uuid(value: Any) -> bool:
    """A UUID string that fits ``TXCreateItem.link_uuid`` (36 characters at most)."""
    if not isinstance(value, str) or len(value) > 36:
        return False
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _legs_problems(group: Sequence[TXCreateItem]) -> List[str]:
    """Two legs move two currencies in opposite directions."""
    cash = [tx.cash for tx in group]
    if len(group) != 2 or None in cash:
        return []
    if cash[0].code == cash[1].code or (cash[0].amount > 0) == (cash[1].amount > 0):
        return [f"legs {sorted(_pair_cash(group), key=repr)}: two currencies and opposite signs expected"]
    return []


def _pair_problems(link: Optional[str], group: Sequence[TXCreateItem]) -> List[str]:
    """Where a group of linked legs breaks the pair contract (§2.5, and the batch rules of §1.4)."""
    problems = [] if len(group) == 2 else [f"{len(group)} leg(s) share it, not 2"]
    if not _is_uuid(link):
        problems.append(f"link_uuid {link!r} is not a UUID string of at most 36 characters")
    if any(tx.quantity != 0 or tx.asset_id is not None or tx.cash is None or tx.cash.amount == 0 for tx in group):
        problems.append("a leg has a quantity, an asset, or no cash")
    if len({tx.description for tx in group}) != 1 or any(tx.tags != TAGS for tx in group):
        problems.append(f"descriptions {[tx.description for tx in group]} and tags {[tx.tags for tx in group]}: one description, and {TAGS} on both legs")
    return [*problems, *_legs_problems(group)]


def _all_pair_problems(out: BRIMParseOutput) -> List[str]:
    return [f"{link}: {problem}" for link, group in _fx_groups(out).items() for problem in _pair_problems(link, group)]


# =============================================================================
# THE SAMPLES, LINE BY LINE (plan §2.9; the brief of the test-author)
# =============================================================================


@dataclass(frozen=True)
class Tx:
    """A transaction expected from one line of a sample: type, amount, currency, the ISIN of its asset (``None``: no asset), quantity."""

    line: int
    type: str
    amount: str
    currency: str
    isin: Optional[str] = None
    quantity: str = "0"


@dataclass(frozen=True)
class FxPair:
    """A currency conversion expected from two lines of a sample, in file order, with each line's currency and amount."""

    first: int
    second: int
    first_cash: Tuple[str, str]
    second_cash: Tuple[str, str]


@dataclass
class SampleSpec:
    """Everything a sample gives: transactions, conversions, notices by code with their lines, the lines skipped without a word, the continuation lines."""

    path: Path
    delimiter: str
    language: str
    transactions: Tuple[Tx, ...]
    fx_pairs: Tuple[FxPair, ...]
    notices: Dict[str, Tuple[int, ...]]
    skipped: Tuple[int, ...]
    continuations: Tuple[int, ...]
    count: int


# The Dutch collage: lines 2-30 write a decimal comma between quotes, lines 31-74 a decimal point; descriptions in
# Dutch, Portuguese, French, Spanish and English; line 19 holds the tail of line 18's Order Id.
NL_SPEC = SampleSpec(
    path=NL_SAMPLE,
    delimiter=",",
    language="nl",
    transactions=(
        # Deposits: iDEAL, and the Spanish «Ingreso»
        Tx(4, "DEPOSIT", "27.80", "EUR"),
        Tx(55, "DEPOSIT", "25.00", "EUR"),
        # Dividends, «Dividend» and the French «Dividende»
        Tx(10, "DIVIDEND", "0.44", "USD", "US1912161007"),
        Tx(12, "DIVIDEND", "0.44", "USD", "US56035L1044"),
        Tx(14, "DIVIDEND", "0.73", "USD", "US18539C2044"),
        Tx(33, "DIVIDEND", "11.82", "USD", "IE0031442068"),
        Tx(48, "DIVIDEND", "1.39", "USD", "US00206R1023"),
        Tx(51, "DIVIDEND", "0.51", "USD", "US7561091049"),
        Tx(61, "DIVIDEND", "3.50", "USD", "US69181V1070"),
        Tx(66, "DIVIDEND", "9999.99", "JPY", "JP3633400001"),
        Tx(74, "DIVIDEND", "0.23", "USD", "IE00BYPC1H27"),
        # Dividend taxes, the Dutch «Dividendbelasting» and the French «Impôts sur dividende»: taxes, not dividends
        Tx(11, "TAX", "-0.07", "USD", "US1912161007"),
        Tx(13, "TAX", "-0.07", "USD", "US56035L1044"),
        Tx(15, "TAX", "-0.11", "USD", "US18539C2044"),
        Tx(52, "TAX", "-0.15", "USD", "US7561091049"),
        Tx(60, "TAX", "-0.53", "USD", "US69181V1070"),
        Tx(67, "TAX", "-9999.99", "JPY", "JP3633400001"),
        # Charges of an order (Dutch, Portuguese, French words): the order's asset
        Tx(21, "FEE", "-1.00", "EUR", "US9256521090"),
        Tx(28, "FEE", "-0.50", "EUR", "CA0641491075"),
        Tx(36, "FEE", "-1.00", "EUR", "US00165C1045"),
        Tx(38, "FEE", "-1.00", "EUR", "IE00BYXG2H39"),
        Tx(40, "FEE", "-1.00", "EUR", "IE00B0M63391"),
        Tx(43, "FEE", "-1.00", "EUR", "IE00B4L5Y983"),
        Tx(49, "FEE", "-4.90", "EUR", "FI4000198031"),
        Tx(68, "FEE", "-9999.99", "EUR", "JP3633400001"),
        # Charges without an order: exchange connection (Dutch, English) and corporate action, no asset (D6)
        Tx(45, "FEE", "-2.50", "EUR"),
        Tx(46, "FEE", "-2.50", "EUR"),
        Tx(47, "FEE", "-2.50", "EUR"),
        Tx(62, "FEE", "-2.50", "EUR"),
        Tx(57, "FEE", "-0.01", "USD"),
        # Purchases, any verb (Koop, Compra, Achat); line 37 is «-1.2108» between quotes
        Tx(22, "BUY", "-33.90", "USD", "US9256521090", quantity="1"),
        Tx(30, "BUY", "-79.35", "EUR", "IE00B3RBWM25", quantity="1"),
        Tx(31, "BUY", "-97.93", "EUR", "IE00B3RBWM25", quantity="1"),
        Tx(32, "BUY", "-19.5", "EUR", "AU000000FBR4", quantity="500"),
        Tx(37, "BUY", "-1.2108", "USD", "US00165C1045", quantity="1"),
        Tx(41, "BUY", "-42.53", "EUR", "IE00B0M63391", quantity="1"),
        Tx(42, "BUY", "-298.71", "EUR", "IE00B4L5Y983", quantity="6"),
        Tx(44, "BUY", "-82.06", "EUR", "IE00B4L5Y983", quantity="1"),
        Tx(50, "BUY", "-479.76", "EUR", "FI4000198031", quantity="6"),
        Tx(69, "BUY", "-9999.99", "EUR", "JP3633400001", quantity="30"),
        # Sales (Verkoop, Sell): a negative quantity
        Tx(29, "SELL", "63.97", "USD", "CA0641491075", quantity="-1"),
        Tx(39, "SELL", "5.42", "EUR", "IE00BYXG2H39", quantity="-1"),
        Tx(56, "SELL", "19.84", "GBP", "GB00BPQY8M80", quantity="-4"),
        # Courtesy credits: interest, with their own description (decision 5)
        Tx(63, "INTEREST", "0.24", "EUR"),
        Tx(64, "INTEREST", "0.61", "EUR"),
    ),
    fx_pairs=(
        FxPair(6, 7, ("EUR", "1.28"), ("USD", "-1.36")),  # no Order Id: one date and time
        FxPair(18, 20, ("USD", "33.90"), ("EUR", "-31.91")),  # Order Id rebuilt from line 19; line 21's fee is not the partner
        FxPair(26, 27, ("USD", "-63.97"), ("EUR", "54.57")),
        FxPair(53, 54, ("EUR", "0.79"), ("USD", "-0.85")),  # Spanish «Cambio de Divisa»
        FxPair(58, 59, ("USD", "-457.52"), ("EUR", "408.83")),  # line 59 is the mojibake «CrÃ©dito de divisa»
        FxPair(72, 73, ("EUR", "12.28"), ("USD", "-12.75")),
    ),
    notices={NOT_IMPORTED: (34, 35, 65, 70, 71), FLATEX_WITHDRAWAL: (24, 25)},
    # Transfers without an amount (2, 8, 16, 75), cash sweeps (3, 9, 17), reservations (5, 23)
    skipped=(2, 3, 5, 8, 9, 16, 17, 23, 75),
    continuations=(19,),
    count=57,
)

# The synthetic English statement: ``;``, decimal comma, thousands dot; line 13 holds the tail of line 12's Order Id.
# It is stored with LF (git normalises its line endings); CRLF, the way the user downloads the file, is exercised by ``_statement_bytes``.
EN_SPEC = SampleSpec(
    path=EN_SAMPLE,
    delimiter=";",
    language="en",
    transactions=(
        Tx(3, "INTEREST", "3.47", "CZK"),
        Tx(4, "INTEREST", "3.00", "EUR"),  # «DEGIRO rabat propagace», its description kept
        Tx(5, "INTEREST", "0.75", "EUR"),
        Tx(10, "TAX", "-0.72", "USD", "US0378331005"),
        Tx(11, "DIVIDEND", "4.80", "USD", "US0378331005"),
        Tx(15, "FEE", "-1.00", "EUR", "US0378331005"),
        Tx(16, "BUY", "-901.25", "USD", "US0378331005", quantity="5"),
        Tx(17, "FEE", "-1.00", "EUR", "IE00BK5BQT80"),
        Tx(18, "SELL", "356.25", "EUR", "IE00BK5BQT80", quantity="-3"),
        Tx(19, "FEE", "-1.00", "EUR", "IE00BK5BQT80"),
        Tx(20, "BUY", "-1124.00", "EUR", "IE00BK5BQT80", quantity="10"),
        Tx(21, "FEE", "-2.50", "EUR"),
        Tx(23, "DEPOSIT", "2500.00", "EUR"),
    ),
    fx_pairs=(
        FxPair(8, 9, ("EUR", "3.49"), ("USD", "-4.08")),  # no Order Id
        FxPair(12, 14, ("USD", "901.25"), ("EUR", "-770.16")),  # Order Id rebuilt from line 13
    ),
    notices={FLATEX_WITHDRAWAL: (22,)},
    # Interest at zero (2), the transfer without an amount (6), the sweep (7), the two reservations (24, 25)
    skipped=(2, 6, 7, 24, 25),
    continuations=(13,),
    count=17,
)

SAMPLE_SPECS = [pytest.param(NL_SPEC, id="dutch-sample"), pytest.param(EN_SPEC, id="english-sample")]


def _spec_raw(spec: SampleSpec) -> Dict[int, List[str]]:
    return _raw_lines(spec.path, spec.delimiter)


def _expected_keys(spec: SampleSpec) -> Counter:
    """``(type, quantity, amount, currency, ISIN)`` of every expected transaction."""
    keys = Counter((tx.type, _num(tx.quantity), _num(tx.amount), tx.currency, tx.isin) for tx in spec.transactions)
    for pair in spec.fx_pairs:
        for currency, amount in (pair.first_cash, pair.second_cash):
            keys[("FX_CONVERSION", "0", _num(amount), currency, None)] += 1
    return keys


def _actual_keys(out: BRIMParseOutput) -> Counter:
    return Counter((tx.type.value, _num(tx.quantity), _tx_cash(tx)[1], _tx_cash(tx)[0], _isin(out, tx)) for tx in out.transactions)


def _pair_description(raw: Dict[int, List[str]], pair: FxPair) -> str:
    """``<first line's description> / <second line's description>``, in file order; one description when both are the same."""
    first, second = raw[pair.first][5], raw[pair.second][5]
    return first if first == second else f"{first} / {second}"


def _expected_dated(spec: SampleSpec, raw: Dict[int, List[str]]) -> Counter:
    """``(type, amount, currency, date, description)`` of every expected transaction: the date of column 1 and the description of column 6, verbatim."""
    rows = Counter((tx.type, _num(tx.amount), tx.currency, _day(raw[tx.line][0]), raw[tx.line][5]) for tx in spec.transactions)
    for pair in spec.fx_pairs:
        description = _pair_description(raw, pair)
        for line, (currency, amount) in ((pair.first, pair.first_cash), (pair.second, pair.second_cash)):
            rows[("FX_CONVERSION", _num(amount), currency, _day(raw[line][0]), description)] += 1
    return rows


def _tx_fixture_problems(spec: SampleSpec, raw: Dict[int, List[str]]) -> List[str]:
    """Expected transactions whose currency, amount or ISIN are not the cells of their line (columns 8, 9 and 5)."""
    problems = []
    for tx in spec.transactions:
        cells = raw[tx.line]
        if (cells[7], _plain_number(cells[8]), cells[4] or None) != (tx.currency, Decimal(tx.amount), tx.isin):
            problems.append(f"line {tx.line}: the file has {cells[7]} {cells[8]} {cells[4] or None}, the spec {tx.currency} {tx.amount} {tx.isin}")
    return problems


def _pair_fixture_problems(spec: SampleSpec, raw: Dict[int, List[str]]) -> List[str]:
    """Expected conversions whose cash is not the cells of their lines, or whose FX rate is not on exactly one leg."""
    problems = []
    for pair in spec.fx_pairs:
        for line, (currency, amount) in ((pair.first, pair.first_cash), (pair.second, pair.second_cash)):
            if (raw[line][7], _plain_number(raw[line][8])) != (currency, Decimal(amount)):
                problems.append(f"line {line}: the file has {raw[line][7]} {raw[line][8]}, the spec {currency} {amount}")
        if [bool(raw[line][6].strip()) for line in (pair.first, pair.second)].count(True) != 1:
            problems.append(f"lines {pair.first} and {pair.second}: the FX rate is not on exactly one of them")
    return problems


def _product_names(spec: SampleSpec, raw: Dict[int, List[str]]) -> Dict[str, set]:
    """The product names (column 4) the expected transactions show for each ISIN."""
    names: Dict[str, set] = defaultdict(set)
    for tx in spec.transactions:
        if tx.isin:
            names[tx.isin].add(raw[tx.line][3])
    return names


# =============================================================================
# RECOGNITION CASES — written in tmp_path, accepted or refused by structure
# =============================================================================


@dataclass(frozen=True)
class FileCase:
    """A synthetic file ``can_parse`` must accept or refuse."""

    id: str
    name: str
    content: bytes
    accepted: bool

    def write(self, folder: Path) -> Path:
        path = folder / self.id / self.name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.content)
        return path


def _swap(cells: Sequence[str], first: int, second: int) -> List[str]:
    swapped = list(cells)
    swapped[first], swapped[second] = swapped[second], swapped[first]
    return swapped


def _first_columns(line: str, delimiter: str, count: int) -> str:
    return delimiter.join(line.split(delimiter)[:count])


# One data row, as the user's own export has them (a courtesy credit).
ONE_ROW = Row("DEGIRO courtesy", amount="0,75", time="10:01", balance="9,60")
EN_STATEMENT = _statement_bytes(EN_HEADER, [ONE_ROW])

RECOGNITION_CASES = (
    # Accepted: the Account Statement under every verified header, as the user downloads it (``;``, CRLF, one data row)
    *(FileCase(f"{language}-statement", "Account.csv", _statement_bytes(header, [ONE_ROW]), True) for language, header in STATEMENT_HEADERS.items()),
    FileCase("en-statement-comma-lf", "Account.csv", _statement_bytes(EN_HEADER, [ONE_ROW], delimiter=",", newline="\n"), True),
    FileCase("en-statement-utf8-bom", "Account.csv", b"\xef\xbb\xbf" + EN_STATEMENT, True),
    FileCase("en-statement-empty-13th-column", "Account.csv", _statement_bytes([*EN_HEADER, ""], [[*ONE_ROW.cells(), ""]]), True),
    FileCase("en-orders-list", "Transactions.csv", _orders_bytes(ORDERS_EN, ORDERS_EN_ROWS, "\r\n"), True),
    FileCase("nl-orders-list", "Transactions.csv", _orders_bytes(ORDERS_NL, ORDERS_NL_ROWS, "\n"), True),
    # Refused: near misses of the structure
    FileCase("en-statement-11-columns", "Account.csv", _statement_bytes(EN_HEADER[:11], [ONE_ROW.cells()[:11]]), False),
    FileCase("nl-statement-11-columns", "Account.csv", _statement_bytes(NL_HEADER[:11], [ONE_ROW.cells()[:11]], delimiter=","), False),
    FileCase("en-statement-named-13th-column", "Account.csv", _statement_bytes([*EN_HEADER, "Extra"], [[*ONE_ROW.cells(), ""]]), False),
    FileCase("en-statement-named-9th-column", "Account.csv", _statement_bytes([*EN_HEADER[:8], "Amount", *EN_HEADER[9:]], [ONE_ROW]), False),
    FileCase("en-statement-isin-in-4th-column", "Account.csv", _statement_bytes(_swap(EN_HEADER, 3, 4), [_swap(ONE_ROW.cells(), 3, 4)]), False),
    FileCase("en-statement-iso-date", "Account.csv", _statement_bytes(EN_HEADER, [Row("DEGIRO courtesy", amount="0,75", day="2025-09-22", time="10:01")]), False),
    FileCase("en-statement-slash-date", "Account.csv", _statement_bytes(EN_HEADER, [Row("DEGIRO courtesy", amount="0,75", day="22/09/2025", time="10:01")]), False),
    FileCase("en-statement-time-without-colon", "Account.csv", _statement_bytes(EN_HEADER, [Row("DEGIRO courtesy", amount="0,75", time="10h01")]), False),
    FileCase("en-orders-list-15-columns", "Transactions.csv", _orders_bytes(_first_columns(ORDERS_EN, ";", 15), [_first_columns(row, ";", 15) for row in ORDERS_EN_ROWS], "\r\n"), False),
    FileCase("en-statement-as-txt", "Account.txt", EN_STATEMENT, False),
    FileCase("empty-file", "Account.csv", b"", False),
)
ACCEPTED_CASES = [pytest.param(case, id=case.id) for case in RECOGNITION_CASES if case.accepted]
REFUSED_CASES = [pytest.param(case, id=case.id) for case in RECOGNITION_CASES if not case.accepted]


def _unreadable_paths(folder: Path) -> List[Path]:
    """Paths with nothing to read: a missing file, a folder named like a CSV."""
    folder_like_a_csv = folder / "folder" / "Account.csv"
    folder_like_a_csv.mkdir(parents=True)
    return [folder / "missing" / "Account.csv", folder_like_a_csv]


def _reason_problem(plugin: BRIMProvider, path: Path, accepted: bool, label: str) -> Optional[str]:
    """Where ``cannot_parse_reason`` breaks its contract on one path, or ``None``."""
    try:
        reason = plugin.cannot_parse_reason(path)
    except Exception as exc:  # the contract: it never raises
        return f"{label}: raised {type(exc).__name__}: {exc}"
    if accepted:
        return None if reason is None else f"{label}: accepted, and yet the reason {reason!r}"
    if reason is None:
        return f"{label}: refused without a reason"
    return None if _is_one_sentence(reason) else f"{label}: {reason!r} is not one sentence (one line, lowercase start, no final period)"


# =============================================================================
# G. IDENTITY, AND THE TWO HELPERS KEPT
# =============================================================================


class TestIdentity:
    """G — the plugin's identity: the version is bumped (§1.7, the files already parsed show a re-parse); the rest stays."""

    def test_the_version_is_2_0_0(self):
        """The parse changes for the same input (amounts, currencies, types, pairs, notices): ``plugin_version`` 2.0.0, so the files already parsed offer a new parse."""
        assert _plugin().plugin_version == PLUGIN_VERSION, f"plugin_version is {_plugin().plugin_version!r}: the rewrite bumps it to {PLUGIN_VERSION}"

    def test_code_class_and_priority_are_unchanged(self):
        """Guard: the code the brokers and the files already name, the class, priority 100 (above the generic CSV)."""
        plugin = _plugin()

        assert (plugin.provider_code, type(plugin).__name__, plugin.detection_priority) == (PLUGIN_CODE, "DegiroBrokerProvider", 100)

    @pytest.mark.parametrize(("text", "expected"), [pytest.param("17-12-2022", date(2022, 12, 17), id="dd-mm-yyyy"), pytest.param("01-01-2025", date(2025, 1, 1), id="new-year"), pytest.param("", None, id="blank"), pytest.param("2022-12-17", None, id="iso-is-not-degiro")])
    def test_the_date_helper_is_kept(self, text: str, expected: Optional[date]):
        """Guard: ``_parse_degiro_date`` reads ``DD-MM-YYYY`` and nothing else (``test_brim_providers.py`` imports it)."""
        assert _module_attribute("_parse_degiro_date")(text) == expected

    @pytest.mark.parametrize(
        ("description", "expected"),
        [
            pytest.param("Compra 6 ISHARES MSCI WOR A@49,785 EUR", "6", id="compra-guard"),
            pytest.param("Koop 1 @ 33,9 USD", "1", id="koop-guard"),
            pytest.param("Verkoop 1 @ 63,97 USD", "1", id="verkoop-guard"),
            pytest.param("Sell 4 AVIVA@496 GBX (GB00BPQY8M80)", "4", id="sell-guard"),
            pytest.param("Achat 6 QT GROUP OYJ@79,96 EUR (FI4000198031)", "6", id="achat-guard"),
            pytest.param("Nákup 3 ISHARES CORE S&P 500 UCITS ETF@10,5 EUR (IE00B5BMR087)", "3", id="czech-buy"),
            pytest.param("Prodej 2 ISHARES CORE S&P 500 UCITS ETF@11 EUR (IE00B5BMR087)", "2", id="czech-sell"),
            pytest.param("Kauf 4 zu je 12,5 EUR", "4", id="old-german-form"),
            pytest.param("Dividend", "0", id="no-trade-guard"),
            pytest.param("iDEAL Deposit", "0", id="no-quantity-guard"),
        ],
    )
    def test_the_quantity_helper_reads_any_verb(self, description: str, expected: str):
        """``_extract_quantity_from_description`` reads the quantity right after the first word of a trade form, whatever the verb (``@`` or the old German ``zu je``); 0 without one. The ``-guard`` cases pass today."""
        assert _module_attribute("_extract_quantity_from_description")(description) == Decimal(expected)


# =============================================================================
# A. RECOGNITION BY STRUCTURE (plan §2.2, D7, D8)
# =============================================================================


class TestRecognition:
    """A — ``can_parse`` reads the structure, never the words: the Account Statement and the orders list, in any language, on ``,`` or ``;``.

    The user's own exports (§1.2) are English, ``;``, CRLF: today no plugin takes them. The accepted cases are red
    until the rewrite (but the Dutch header); the refused ones are guards, apart from the Dutch statement without its
    Order Id column, which today's name check still takes.
    """

    @pytest.mark.parametrize("sample", [NL_SAMPLE, EN_SAMPLE], ids=lambda path: path.name)
    def test_recognises_both_samples(self, sample: Path):
        assert _plugin().can_parse(sample) is True, f"DEGIRO refuses its own sample {sample.name}"

    @pytest.mark.parametrize("case", ACCEPTED_CASES)
    def test_recognises_the_structure_in_any_language(self, case: FileCase, tmp_path: Path):
        """12 columns (a 13th only if empty), the 9th and 11th unnamed, ``isin`` in the 5th, a first row dated ``DD-MM-YYYY`` at ``HH:MM``; or the orders list."""
        path = case.write(tmp_path)

        assert _plugin().can_parse(path) is True, f"{case.id}: DEGIRO refuses a file with its structure"

    @pytest.mark.parametrize("case", REFUSED_CASES)
    def test_refuses_a_near_miss(self, case: FileCase, tmp_path: Path):
        """11 columns, a named 13th or 9th column, ``isin`` elsewhere, a first row not dated ``DD-MM-YYYY`` at ``HH:MM``, 15 columns of an orders list, another extension, nothing."""
        path = case.write(tmp_path)

        assert _plugin().can_parse(path) is False, f"{case.id}: DEGIRO claims a file without its structure"

    def test_refuses_every_other_sample(self):
        """Guard: no file of ``sample_reports/`` (recursive, every extension) whose name lacks ``degiro`` is DEGIRO's."""
        others = sorted(path for path in SAMPLE_DIR.rglob("*") if path.is_file() and "degiro" not in path.name.lower())
        assert len(others) > 20, f"premise: the corpus holds the other brokers' samples: {[path.name for path in others]}"
        plugin = _plugin()

        claimed = [str(path.relative_to(SAMPLE_DIR)) for path in others if plugin.can_parse(path)]

        assert not claimed, f"DEGIRO claims {len(claimed)} other sample(s): {claimed}"

    @pytest.mark.parametrize("case", [pytest.param(FileCase("dutch-sample", NL_SAMPLE.name, NL_SAMPLE.read_bytes(), True), id="dutch-sample"), pytest.param(FileCase("english-sample", EN_SAMPLE.name, EN_SAMPLE.read_bytes(), True), id="english-sample"), *ACCEPTED_CASES])
    def test_is_detected_before_the_generic_csv(self, case: FileCase, tmp_path: Path):
        """What the upload offers first: ``auto_detect_plugin`` answers DEGIRO, never the generic CSV (priority 0) nor another broker."""
        path = case.write(tmp_path)

        assert BRIMProviderRegistry.auto_detect_plugin(path) == PLUGIN_CODE, f"{case.id}: detected as {BRIMProviderRegistry.auto_detect_plugin(path)!r}, compatible {BRIMProviderRegistry.get_compatible_plugins(path)}"

    def test_says_why_exactly_when_it_refuses(self, tmp_path: Path):
        """D8: ``cannot_parse_reason(p)`` is ``None`` exactly when ``can_parse(p)``, otherwise one English sentence, and it never raises —
        on every file of ``sample_reports/`` (recursive, every extension), every synthetic case above, a missing path and a folder named like a CSV."""
        corpus = sorted(path for path in SAMPLE_DIR.rglob("*") if path.is_file())
        synthetic = [case.write(tmp_path / "cases") for case in RECOGNITION_CASES]
        paths = [*corpus, *synthetic, *_unreadable_paths(tmp_path / "unreadable")]
        plugin = _plugin()
        accepted = {path: plugin.can_parse(path) for path in paths}
        assert set(accepted.values()) == {True, False}, "premise: DEGIRO accepts some of these files and refuses the others"

        labels = {path: str(path.relative_to(SAMPLE_DIR) if path.is_relative_to(SAMPLE_DIR) else path.relative_to(tmp_path)) for path in paths}
        broken = [problem for path in paths if (problem := _reason_problem(plugin, path, accepted[path], labels[path]))]

        assert not broken, f"cannot_parse_reason breaks its contract on {len(broken)} of {len(paths)} path(s): {broken}"


# =============================================================================
# FIXTURE GUARDS — this file's expectations against the samples
# =============================================================================


class TestSampleFixtures:
    """Fixture guards: the line-by-line expectations below agree with the samples as the csv module reads them. They pass before and after the rewrite."""

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_every_line_is_expected_exactly_once(self, spec: SampleSpec):
        """Each data line is a transaction, a leg, a notice row, a silent skip or a continuation, once; the counts add up."""
        raw = _spec_raw(spec)
        claimed = [
            *(tx.line for tx in spec.transactions),
            *(line for pair in spec.fx_pairs for line in (pair.first, pair.second)),
            *(line for lines in spec.notices.values() for line in lines),
            *spec.skipped,
            *spec.continuations,
        ]

        assert sorted(claimed) == sorted(number for number in raw if number > 1), f"{spec.path.name}: {Counter(claimed) - Counter(raw)} claimed twice or beyond the file"
        assert len(spec.transactions) + 2 * len(spec.fx_pairs) == spec.count

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_the_expected_values_are_the_file_cells(self, spec: SampleSpec):
        """Currency, amount and ISIN of each expected transaction are its line's cells; each pair has its rate on one leg; a continuation line has no date and no time; one product name per ISIN."""
        raw = _spec_raw(spec)
        problems = [*_tx_fixture_problems(spec, raw), *_pair_fixture_problems(spec, raw)]
        problems += [f"line {line} is not a continuation" for line in spec.continuations if raw[line][:2] != ["", ""]]
        problems += [f"{isin} has several product names {names}" for isin, names in _product_names(spec, raw).items() if len(names) != 1]

        assert not problems, problems


# =============================================================================
# B. THE TWO SAMPLES, LINE BY LINE (plan §2.9)
# =============================================================================


class TestSamples:
    """B — the Dutch collage and the synthetic English statement give exactly what §2.9 and the brief list: compared as multisets, never by position."""

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_the_sample_gives_its_transactions(self, spec: SampleSpec):
        """``(type, quantity, amount, currency, ISIN)`` of every transaction: the amount and the currency of each row (columns 9 and 8), not of its balance; no validation issue."""
        out = _parse(spec.path)
        actual, expected = _actual_keys(out), _expected_keys(spec)

        assert actual == expected, f"{spec.path.name}: {len(out.transactions)} transaction(s) for {spec.count} expected — {_diff(actual, expected)}"
        assert out.validation_issues == [], f"{spec.path.name}: {[(issue.row, issue.code, issue.message) for issue in out.validation_issues]}"

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_each_transaction_has_the_date_and_the_description_of_its_line(self, spec: SampleSpec):
        """The date of column 1, the description of column 6 verbatim (mojibake included); a pair's legs share «<first> / <second>»."""
        out = _parse(spec.path)
        actual = Counter((tx.type.value, _tx_cash(tx)[1], _tx_cash(tx)[0], tx.date, tx.description) for tx in out.transactions)
        expected = _expected_dated(spec, _spec_raw(spec))

        assert actual == expected, f"{spec.path.name}: {_diff(actual, expected)}"

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_each_transaction_is_tagged_and_only_the_legs_are_linked(self, spec: SampleSpec):
        """Broker 1, the tags ``["import", "degiro"]`` on every row, a ``link_uuid`` on the FX_CONVERSION legs only."""
        out = _parse(spec.path)
        assert len(out.transactions) == spec.count, f"presence barrier: {spec.path.name} gives {len(out.transactions)} transaction(s), {spec.count} expected"

        wrong = [(tx.type.value, _tx_cash(tx), tx.broker_id, tx.tags, tx.link_uuid) for tx in out.transactions if tx.broker_id != BROKER_ID or tx.tags != TAGS or (tx.link_uuid is None) == (tx.type.value == "FX_CONVERSION")]

        assert not wrong, f"{spec.path.name}: (type, cash, broker, tags, link_uuid) off the contract: {wrong}"

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_one_fake_asset_per_isin_named_after_its_product(self, spec: SampleSpec):
        """Every ISIN the expected rows name has one fake asset id of its own, with ``extracted_isin`` and ``extracted_name`` (column 4) filled."""
        out = _parse(spec.path)
        names = {isin: found.pop() for isin, found in _product_names(spec, _spec_raw(spec)).items()}
        ids = _asset_ids_by_isin(out)
        assert set(ids) == set(names), f"{spec.path.name}: assets for {sorted(ids, key=str)}, expected {sorted(names)}"
        assert [isin for isin, found in ids.items() if len(found) != 1] == [], f"{spec.path.name}: several fake ids for one ISIN: {ids}"

        extracted = {isin: (out.extracted_assets[asset_id].extracted_isin, out.extracted_assets[asset_id].extracted_name, is_fake_asset_id(asset_id)) for isin, (asset_id,) in ids.items()}

        assert extracted == {isin: (isin, name, True) for isin, name in names.items()}, f"{spec.path.name}: (extracted ISIN, extracted name, fake id) per ISIN"
        assert len({min(found) for found in ids.values()}) == len(ids), f"{spec.path.name}: two ISINs share a fake asset id: {ids}"

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_the_sample_lists_its_rows_by_reason(self, spec: SampleSpec):
        """One notice per code, its rows grouped by physical line number, and nothing else: no unknown row in either sample."""
        out = _parse(spec.path)
        codes = Counter(notice.code for notice in out.warnings)

        assert codes == Counter(list(spec.notices)), f"{spec.path.name}: notices {dict(codes)} ({[notice.message for notice in out.warnings]}), expected one of each {sorted(spec.notices)}"
        assert {notice.code: sorted(_row_numbers(notice)) for notice in out.warnings} == {code: sorted(lines) for code, lines in spec.notices.items()}

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_every_notice_keeps_the_contract(self, spec: SampleSpec):
        """Severity ``warning``; ``context`` with the file's language and the count; evidence of 12 headers and each listed line's 12 cells; the message from ``_MESSAGES``."""
        out = _parse(spec.path)
        raw = _spec_raw(spec)
        assert sorted(notice.code for notice in out.warnings) == sorted(spec.notices), f"presence barrier: {spec.path.name} gives the notices {[notice.code for notice in out.warnings]}"

        problems = [f"{notice.code}: {problem}" for notice in out.warnings for problem in [*_notice_context_problems(notice, spec.language), *_notice_evidence_problems(notice, raw), *_message_problems(notice, spec.language)]]

        assert not problems, f"{spec.path.name}: {problems}"

    @pytest.mark.parametrize("spec", SAMPLE_SPECS)
    def test_the_conversions_are_linked_pairs(self, spec: SampleSpec):
        """Each conversion: its two lines' legs under one ``link_uuid``, one description, the plugin's tags, no asset, quantity 0; one UUID per conversion."""
        out = _parse(spec.path)
        raw = _spec_raw(spec)
        expected = {frozenset({_cash_key(*pair.first_cash), _cash_key(*pair.second_cash)}): _pair_description(raw, pair) for pair in spec.fx_pairs}

        actual = {_pair_cash(group): group[0].description for group in _fx_groups(out).values()}

        assert actual == expected, f"{spec.path.name}: the legs grouped by link_uuid, with a description each, are {actual}"
        assert _all_pair_problems(out) == []


# =============================================================================
# C. CLASSIFICATION, IN ITS ORDER (plan §2.4)
# =============================================================================


class TestClassification:
    """C — trades and charges by structure, transaction taxes, the sign rule, the rows known but not importable, the unknown rows, continuation lines.

    Small statements written in ``tmp_path`` with the English header, ``;`` and CRLF, as the user downloads them; each
    row has its own currency and amount, so every transaction maps back to its row (``_outcomes``).
    """

    def test_a_trade_is_read_by_its_form_whatever_the_verb(self, tmp_path: Path):
        """``<word> <quantity> …@<price> <CCY>`` with an ISIN and an Order Id: Czech ``Nákup`` with a negative amount is a BUY of 3, ``Prodej`` with a positive one a SELL of -2, on one fake asset."""
        rows, expected = _scenario(
            [
                (Row(f"Nákup 3 {SP500_NAME}@10,5 EUR ({SP500})", amount="-31,50", isin=SP500, product=SP500_NAME, order_id=_order(1), day="05-09-2025", time="14:02"), "BUY"),
                (Row(f"Prodej 2 {SP500_NAME}@11 EUR ({SP500})", amount="22,00", isin=SP500, product=SP500_NAME, order_id=_order(2), day="12-09-2025", time="10:15"), "SELL"),
            ]
        )
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert {(tx.type.value, _num(tx.quantity), _isin(out, tx)) for tx in out.transactions} == {("BUY", "3", SP500), ("SELL", "-2", SP500)}
        assert len({tx.asset_id for tx in out.transactions}) == 1, "one fake asset per ISIN"

    def test_the_old_german_form_is_a_trade_too(self, tmp_path: Path):
        """``Kauf 4 zu je 12,5 EUR`` (``zu je`` instead of ``@``) is a BUY of 4; ``Verkauf 4 zu je 13 EUR`` a SELL of -4."""
        rows, expected = _scenario(
            [
                (Row("Kauf 4 zu je 12,5 EUR", amount="-50,00", isin=SAP, product=SAP_NAME, order_id=_order(3), day="03-02-2020", time="09:05"), "BUY"),
                (Row("Verkauf 4 zu je 13 EUR", amount="52,00", isin=SAP, product=SAP_NAME, order_id=_order(4), day="04-03-2020", time="11:40"), "SELL"),
            ]
        )
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert {(tx.type.value, _num(tx.quantity)) for tx in out.transactions} == {("BUY", "4"), ("SELL", "-4")}

    def test_a_charge_of_an_order_is_a_fee_in_any_language(self, tmp_path: Path):
        """An Order Id, a negative amount, neither a leg nor a trade: a FEE whatever its words — on the order's asset when the row names its ISIN, without an asset otherwise."""
        rows, expected = _scenario(
            [
                (Row(f"Nákup 3 {SP500_NAME}@10,5 EUR ({SP500})", amount="-31,50", isin=SP500, product=SP500_NAME, order_id=_order(5), time="14:02"), "BUY"),
                (Row("Opłata transakcyjna DEGIRO", amount="-2,00", isin=SP500, product=SP500_NAME, order_id=_order(5), time="14:02"), "FEE"),
                (Row("Opłata za przewalutowanie", amount="-0,25", order_id=_order(5), time="14:02"), "FEE"),
            ]
        )
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert {_num(tx.cash.amount): _isin(out, tx) for tx in _of_type(out, "FEE")} == {"-2": SP500, "-0.25": None}
        assert len({tx.asset_id for tx in out.transactions if tx.asset_id is not None}) == 1, "the fee and the purchase name one fake asset"

    def test_a_transaction_tax_of_an_order_is_a_tax(self, tmp_path: Path):
        """``Transactiebelasting <country>`` and ``Stamp Duty`` carry their trade's Order Id: TAX on the order's asset, never FEE."""
        rows, expected = _scenario(
            [
                (Row("Koop 10 @ 25 EUR", amount="-250,00", isin=KBC, product=KBC_NAME, order_id=_order(6), time="11:00"), "BUY"),
                (Row("Transactiebelasting Belgie", amount="-0,88", isin=KBC, product=KBC_NAME, order_id=_order(6), time="11:00"), "TAX"),
                (Row(f"Buy 100 {VODAFONE_NAME}@70 GBX ({VODAFONE})", amount="-70,00", currency="GBP", isin=VODAFONE, product=VODAFONE_NAME, order_id=_order(7), time="12:00"), "BUY"),
                (Row("London/Dublin Stamp Duty", amount="-0,35", currency="GBP", isin=VODAFONE, product=VODAFONE_NAME, order_id=_order(7), time="12:00"), "TAX"),
            ]
        )
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert sorted((_isin(out, tx), tx.description) for tx in _of_type(out, "TAX")) == [(KBC, "Transactiebelasting Belgie"), (VODAFONE, "London/Dublin Stamp Duty")]

    def test_a_sign_against_the_type_is_listed_not_imported(self, tmp_path: Path):
        """A negative dividend, a dividend tax refunded, a withdrawal or a deposit the wrong way, a connection fee refunded: ``degiro_unexpected_sign``, nothing imported; the same words with the right sign are imported."""
        rows, expected = _scenario(
            [
                (Row("Dividend", amount="-0,44", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:01"), UNEXPECTED_SIGN),
                (Row("Dividend Tax", amount="0,07", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:02"), UNEXPECTED_SIGN),
                (Row("Withdrawal", amount="100,00", time="09:03"), UNEXPECTED_SIGN),
                (Row("iDEAL Deposit", amount="-27,80", time="09:04"), UNEXPECTED_SIGN),
                (Row("DEGIRO Exchange Connection Fee 2025 (Nasdaq - NDQ)", amount="2,50", time="09:05"), UNEXPECTED_SIGN),
                (Row("Dividend", amount="0,45", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:06"), "DIVIDEND"),
                (Row("Dividend Tax", amount="-0,06", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:07"), "TAX"),
                (Row("Withdrawal", amount="-50,00", time="09:08"), "WITHDRAWAL"),
            ]
        )
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert sorted(_row_numbers(_the_notice(out, UNEXPECTED_SIGN))) == [2, 3, 4, 5, 6]

    def test_an_unknown_row_is_listed_with_its_cells(self, tmp_path: Path):
        """A description nothing recognises, with an amount: one ``degiro_unknown_rows`` notice whose evidence row holds the row's 12 cells, its description among them; nothing imported."""
        rows, expected = _scenario([(Row("Zorglub bonification", amount="5,00", time="09:30"), UNKNOWN_ROWS), (Row("iDEAL Deposit", amount="20,00", time="09:31"), "DEPOSIT")])
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        notice = _the_notice(out, UNKNOWN_ROWS)
        evidence = notice.evidence[0]
        assert (evidence.row_numbers, [cells[5] for cells in evidence.rows], len(evidence.headers)) == ([2], ["Zorglub bonification"], 12)
        assert [[cell.strip() for cell in cells] for cells in evidence.rows] == [rows[0].cells()]
        assert (_context(notice), notice.severity, notice.message) == ({"language": "en", "count": 1}, "warning", _messages()["en"][UNKNOWN_ROWS].format(n=1))

    def test_rows_known_but_not_importable_are_listed(self, tmp_path: Path):
        """D5: a trade form after a ``PREFIX:`` (corporate actions, with an Order Id, either sign), money-market fund rows, capital returns, any other
        zero amount with an ISIN: one ``degiro_not_imported`` notice, nothing imported. A plain trade next to them stays a trade."""
        prefixed = [
            ("AANDELENSPLIT: Koop 20 @ 2,5 EUR", "-50,00"),
            ("AANDELENSPLIT: Verkoop 10 @ 5 EUR", "50,01"),
            ("ISIN-WIJZIGING: Koop 10 @ 15,4 EUR", "-154,00"),
            ("FUSIE: Verkoop 5 @ 20 EUR", "100,00"),
            ("DELISTING: Verkoop 7 @ 0,01 EUR", "0,07"),
            ("STOCK DIVIDEND: Koop 3 @ 0 EUR", "0,00"),
            ("PRODUCTWIJZIGING : Koop 500 @ 0,039 EUR", "0"),
        ]
        others = [
            ("Conversion Fonds Monétaires finalisée: Vente 1 046,3825 @ 0,9854 EUR", "-4,81", CASH_FUND, CASH_FUND_NAME),
            ("Variation Fonds Monétaires (EUR)", "-0,25", CASH_FUND, CASH_FUND_NAME),
            ("Geldmarktfonds Preisänderung (EUR)", "-0,26", CASH_FUND, CASH_FUND_NAME),
            ("Money Market fund price change (EUR)", "-0,27", CASH_FUND, CASH_FUND_NAME),
            ("Změna ceny Peněžního Fondu (EUR)", "-0,28", CASH_FUND, CASH_FUND_NAME),
            ("Capital Return", "1,50", APPLE, APPLE_NAME),
            ("Kapitaalsuitkering", "1,51", APPLE, APPLE_NAME),
            ("Kapitaaluitkering", "1,52", APPLE, APPLE_NAME),
            ("Kapitalrückzahlung", "1,53", APPLE, APPLE_NAME),
            ("Remboursement de capital", "1,54", APPLE, APPLE_NAME),
            ("Zorglub corporate notice", "0,00", APPLE, APPLE_NAME),
        ]
        cases: List[Tuple[Cells, Optional[str]]] = [(Row(text, amount=amount, isin=KBC, product=KBC_NAME, order_id=_order(10 + index), time=f"08:{index:02d}"), NOT_IMPORTED) for index, (text, amount) in enumerate(prefixed)]
        cases += [(Row(text, amount=amount, currency="EUR" if isin == CASH_FUND else "USD", isin=isin, product=name, time=f"09:{index:02d}"), NOT_IMPORTED) for index, (text, amount, isin, name) in enumerate(others)]
        cases.append((Row("Koop 10 @ 5 EUR", amount="-50,02", isin=KBC, product=KBC_NAME, order_id=_order(30), time="10:00"), "BUY"))
        rows, expected = _scenario(cases)
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert sorted(_row_numbers(_the_notice(out, NOT_IMPORTED))) == sorted(line for line, outcome in expected.items() if outcome == NOT_IMPORTED)

    def test_a_file_mixing_languages_is_read_row_by_row_and_speaks_its_header(self, tmp_path: Path):
        """The word table holds every language on every row (an English header, Dutch, French, Spanish, German, Portuguese words), and the notices speak English, the header's language."""
        rows, expected = _scenario(
            [
                (Row("Dividendbelasting", amount="-0,15", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:01"), "TAX"),
                (Row("Dividende", amount="1,05", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:02"), "DIVIDEND"),
                (Row("Retención del dividendo", amount="-0,16", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:03"), "TAX"),
                (Row("Ausschüttung", amount="1,10", isin=SP500, product=SP500_NAME, time="09:04"), "DIVIDEND"),
                (Row("Ingreso", amount="50,00", time="09:05"), "DEPOSIT"),
                (Row("Einzahlung", amount="60,00", time="09:06"), "DEPOSIT"),
                (Row("Retrait de fonds", amount="-70,00", time="09:07"), "WITHDRAWAL"),
                (Row("Zinsen", amount="0,30", time="09:08"), "INTEREST"),
                (Row("Custo de Conectividade DEGIRO 2024 (NYSE - NSY)", amount="-2,50", time="09:09"), "FEE"),
                (Row("Reservierung SOFORT Einzahlung", amount="80,00", time="09:10"), SKIPPED),
                (Row("Quatsch mit Soße", amount="9,99", time="09:11"), UNKNOWN_ROWS),
            ]
        )
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        notice = _the_notice(out, UNKNOWN_ROWS)
        assert (_context(notice)["language"], notice.message) == ("en", _messages()["en"][UNKNOWN_ROWS].format(n=1))

    def test_a_wrapped_description_is_merged_into_its_row(self, tmp_path: Path):
        """A line without date and time continues the row above: its cells are appended verbatim. The merged row keeps its first line number in the evidence."""
        rows = [
            Row("DEGIRO Rebate Prom", amount="3,00", time="10:02"),
            _continuation(description="otion"),
            Row("Zorglub bonif", amount="5,00", time="10:05"),
            _continuation(description="ication"),
            Row("iDEAL Deposit", amount="20,00", time="10:07"),
        ]
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, {2: "INTEREST", 4: UNKNOWN_ROWS, 6: "DEPOSIT"})
        assert [tx.description for tx in _of_type(out, "INTEREST")] == ["DEGIRO Rebate Promotion"]
        evidence = _the_notice(out, UNKNOWN_ROWS).evidence[0]
        assert (evidence.row_numbers, [cells[5] for cells in evidence.rows]) == ([4], ["Zorglub bonification"])


# =============================================================================
# C. THE WORD TABLE (plan §2.4 step 5; strings of §1.8)
# =============================================================================

DIVIDEND_TAX_WORDS = ("Dividendbelasting", "Dividend Tax", "Dividendensteuer", "Quellensteuer", "Impôts sur dividende", "Impôt sur les dividendes", "Retención del dividendo", "Ritenuta sul dividendo", "Imposta sui dividendi", "Imposto sobre dividendo")
DIVIDEND_WORDS = ("Dividend", "Dividende", "Dividendo", "Dividenda", "Fund Distribution", "Ausschüttung")
DEPOSIT_WORDS = ("iDEAL Deposit", "SOFORT Deposit", "flatex Deposit", "Deposit", "storting", "Einzahlung", "Dépôt", "Versement de fonds", "Ingreso", "Deposito", "Vklad")
WITHDRAWAL_WORDS = ("Withdrawal", "Auszahlung", "Retrait de fonds")
FLATEX_WITHDRAWALS = (("Processed Flatex Withdrawal", "15,10"), ("flatex Withdrawal", "-100,00"), ("flatex terugstorting", "-15,11"), ("Prelievo flatex", "-15,12"))
INTEREST_WORDS = ("Flatex Interest Income", "Interest", "Rente", "Zinsen", "Intérêts", "Intereses", "Interessi", "Juros")
PROMOTION_WORDS = ("DEGIRO courtesy", "DEGIRO Rebate Promotion", "DEGIRO Verrekening Promotie", "DEGIRO rabat propagace", "Neukundenaktion")
FEE_WITHOUT_ORDER = (
    "DEGIRO Aansluitingskosten 2024 (Euronext Amsterdam - EAM)",
    "DEGIRO Exchange Connection Fee 2025 (Nasdaq - NDQ)",
    "Giro Exchange Connection Fee 2024",
    "DEGIRO Anschlussgebühren für Handelsplatz 2024 (Xetra - XET)",
    "Frais de connexion aux places boursières 2024 (Euronext Paris - EPA)",
    "Costi di connessione alla borsa 2024 (Borsa Italiana - MIL)",
    "Custo de Conectividade DEGIRO 2024 (NYSE - NSY)",
    "DEGIRO poplatek za Obchodování 2025 (Xetra - XET)",
    "DEGIRO Corporate Action Kosten",
    "ADR/GDR Pass-Through Fee",
)
INTERNAL_ROWS = (
    ("Degiro Cash Sweep Transfer", "26,45"),
    ("Transfer from your Cash Account at flatexDEGIRO Bank: 12,00 EUR", "12,00"),
    ("Overboeking naar uw geldrekening bij flatexDEGIRO Bank: 0,92 EUR", "-0,92"),
    ("Reservation iDEAL / Sofort Deposit", "27,80"),
    ("Reservering iDEAL / Sofort storting", "-27,81"),
    ("Reservierung SOFORT Einzahlung", "27,82"),
    ("Reserva Ingreso SOFORT", "27,83"),
    ("Prenotazione deposito iDEAL", "-27,84"),
)
# The words of a currency leg, without the FX rate that makes a row a leg: alternately a credit in EUR and a debit in USD.
FX_WORDS = (
    "Valuta Creditering",
    "Valuta Debitering",
    "FX Credit",
    "FX Debit",
    "Währungswechsel (Gutschrift)",
    "Währungswechsel (Ausbuchung)",
    "Opération de change - Crédit",
    "Opération de change - Débit",
    "Ingreso Cambio de Divisa",
    "Retirada Cambio de Divisa",
    "Credito FX",
    "Prelievo FX",
    "Crédito de divisa",
    "Levantamento de divisa",
    "FX vyúčtování konverze měny",
)


class TestWordTable:
    """C, step 5 — the multilingual word table, every language on every row: taxes before dividends, flatex withdrawals before withdrawals, internal rows before deposits.

    Each category is one statement, one row per string, the outcome of every row asserted (``_outcomes``).
    """

    def test_dividend_taxes_are_taxes(self, tmp_path: Path):
        rows = _word_rows(DIVIDEND_TAX_WORDS, "-", currency="USD", isin=APPLE, product=APPLE_NAME)
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, _every_line(rows, "TAX"))
        assert {_isin(out, tx) for tx in out.transactions} == {APPLE}

    def test_dividends_are_dividends(self, tmp_path: Path):
        rows = _word_rows(DIVIDEND_WORDS, "", currency="USD", isin=APPLE, product=APPLE_NAME)
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, _every_line(rows, "DIVIDEND"))
        assert {_isin(out, tx) for tx in out.transactions} == {APPLE}

    def test_deposits_are_deposits(self, tmp_path: Path):
        rows = _word_rows(DEPOSIT_WORDS, "")
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, _every_line(rows, "DEPOSIT"))
        assert all(tx.asset_id is None for tx in out.transactions)

    def test_withdrawals_are_withdrawals(self, tmp_path: Path):
        rows = _word_rows(WITHDRAWAL_WORDS, "-")
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, _every_line(rows, "WITHDRAWAL"))

    def test_flatex_era_withdrawals_are_listed_not_imported(self, tmp_path: Path):
        """D7: which of the two flatex rows is the real withdrawal is not proven, so neither is imported: one ``degiro_flatex_withdrawal`` notice, whatever the sign."""
        rows = [Row(text, amount=amount, time=f"13:{index:02d}") for index, (text, amount) in enumerate(FLATEX_WITHDRAWALS, start=30)]
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, _every_line(rows, FLATEX_WITHDRAWAL))

    def test_interest_above_zero_is_interest_below_a_fee_and_at_zero_nothing(self, tmp_path: Path):
        """«Flatex Interest Income» and the interest of every language: INTEREST when positive, FEE when negative, skipped without a word at zero; the description kept."""
        cases: List[Tuple[Cells, Optional[str]]] = [(row, "INTEREST") for row in _word_rows(INTEREST_WORDS, "")]
        cases += [(Row(word, amount=f"-0,{index:02d}", time=f"11:{index:02d}"), "FEE") for index, word in enumerate(INTEREST_WORDS, start=1)]
        cases += [(Row("Flatex Interest Income", amount="0,00", currency="CZK", time="12:01"), SKIPPED), (Row("Zinsen", amount="0,00", time="12:02"), SKIPPED)]
        rows, expected = _scenario(cases)
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert sorted(tx.description for tx in out.transactions) == sorted([*INTEREST_WORDS, *INTEREST_WORDS])
        assert out.warnings == [], f"zero interest is skipped without a notice: {[(notice.code, notice.message) for notice in out.warnings]}"

    def test_promotional_credits_are_interest_with_their_own_words(self, tmp_path: Path):
        """Decision 5: courtesy and promotional credits, in every language, are INTEREST with the original description."""
        rows = _word_rows(PROMOTION_WORDS, "")
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, _every_line(rows, "INTEREST"))
        assert sorted(tx.description for tx in out.transactions) == sorted(PROMOTION_WORDS)

    def test_charges_without_an_order_are_fees(self, tmp_path: Path):
        """Exchange connection fees in every language, corporate action costs, ADR/GDR fees: FEE without an asset (D6)."""
        rows = _word_rows(FEE_WITHOUT_ORDER, "-")
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, _every_line(rows, "FEE"))
        assert all(tx.asset_id is None for tx in out.transactions)

    def test_internal_rows_are_skipped_without_a_word(self, tmp_path: Path):
        """Decision 6: cash sweeps, transfers with flatexDEGIRO Bank, reservations (even when they name a deposit) leave no transaction and no notice."""
        rows = [Row(text, amount=amount, time=f"18:{index:02d}") for index, (text, amount) in enumerate(INTERNAL_ROWS, start=1)]
        rows.append(Row("iDEAL Deposit", amount="27,85", time="18:30"))
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, {**_every_line(rows, SKIPPED), len(rows) + 1: "DEPOSIT"})
        assert out.warnings == [], f"internal rows are skipped without a notice: {[(notice.code, notice.message) for notice in out.warnings]}"

    def test_leg_words_without_a_leg_are_listed_as_unpaired(self, tmp_path: Path):
        """The words of a currency leg on a row without an FX rate and without a pair, in every language: ``degiro_unpaired_fx``, nothing imported."""
        rows = [Row(word, amount=f"{'' if index % 2 else '-'}1,{index:02d}", currency="EUR" if index % 2 else "USD", time=f"07:{index:02d}") for index, word in enumerate(FX_WORDS, start=1)]
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, _every_line(rows, UNPAIRED_FX))

    def test_words_match_whatever_their_case_their_accents_or_their_mojibake(self, tmp_path: Path):
        """Case and accents are ignored, and the text broken by a wrong encoding is repaired before matching («CrÃ©dito» reads «Crédito»)."""
        rows, expected = _scenario(
            [
                (Row("DIVIDEND TAX", amount="-0,21", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:21"), "TAX"),
                (Row("dividendensteuer", amount="-0,22", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:22"), "TAX"),
                (Row("Impot sur les dividendes", amount="-0,23", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:23"), "TAX"),
                (Row("ImpÃ´ts sur dividende", amount="-0,24", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:24"), "TAX"),
                (Row("RetenciÃ³n del dividendo", amount="-0,25", currency="USD", isin=APPLE, product=APPLE_NAME, time="09:25"), "TAX"),
                (Row("AUSSCHUTTUNG", amount="1,26", isin=SP500, product=SP500_NAME, time="09:26"), "DIVIDEND"),
                (Row("Depot", amount="30,00", time="09:27"), "DEPOSIT"),
                (Row("DÃ©pÃ´t", amount="31,00", time="09:28"), "DEPOSIT"),
                (Row("INTERESES", amount="0,29", time="09:29"), "INTEREST"),
                (Row("CrÃ©dito de divisa", amount="4,00", time="09:30"), UNPAIRED_FX),
            ]
        )
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert "DÃ©pÃ´t" in {tx.description for tx in out.transactions}, "the description stays the file's, verbatim"


# =============================================================================
# D. CURRENCY CONVERSIONS AS LINKED PAIRS (plan §2.5, D2)
# =============================================================================


def _apple_order_rows(order_id: str) -> Dict[str, Row]:
    """The four rows of a purchase in dollars paid from euros, as DEGIRO writes them under one Order Id: the leg carrying the rate, its partner, the fee, the trade."""
    shared = {"isin": APPLE, "product": APPLE_NAME, "order_id": order_id, "day": "08-09-2025", "time": "15:31"}
    return {
        "leg": Row("FX Credit", amount="901,25", currency="USD", fx="1,1702", **shared),
        "partner": Row("FX Debit", amount="-770,16", **shared),
        "fee": Row("DEGIRO Transaction and/or third party fees", amount="-1,00", **shared),
        "trade": Row(f"Buy 5 {APPLE_NAME}@180,25 USD ({APPLE})", amount="-901,25", currency="USD", **shared),
    }


# Two orders of the same file, in the two orders DEGIRO writes a group: the leg first, or the trade first.
FEE_ARRANGEMENTS = {"leg-first": ("leg", "partner", "fee", "trade"), "trade-first": ("trade", "fee", "partner", "leg")}
OUTCOME_OF_ROLE = {"leg": "FX_CONVERSION", "partner": "FX_CONVERSION", "fee": "FEE", "trade": "BUY"}


def _conversion_rows() -> List[Row]:
    """A conversion without an Order Id (the rate on the debit, one date and time), then a deposit on another day."""
    return [
        Row("FX Credit", amount="3,49", day="16-09-2025", time="06:45"),
        Row("FX Debit", amount="-4,08", currency="USD", fx="1,1690", day="16-09-2025", time="06:45"),
        Row("iDEAL Deposit", amount="100,00", day="17-09-2025", time="09:00"),
    ]


class TestFxPairs:
    """D — a conversion is two FX_CONVERSION transactions the batch accepts as a pair: one ``link_uuid`` (a UUID string), quantity 0, no asset,
    one description, one set of tags. The leg is the row with an FX rate; its partner is in its group (its Order Id, or else its date and time),
    in another currency, with the opposite sign, not a trade; among several candidates the adjacent row. The rate itself is never used."""

    def test_a_conversion_is_two_linked_legs_with_one_description(self, tmp_path: Path):
        """«FX Credit» and «FX Debit» at one date and time, no Order Id: two legs, one valid UUID, «FX Credit / FX Debit» on both, in file order."""
        rows = _conversion_rows()
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, {2: "FX_CONVERSION", 3: "FX_CONVERSION", 4: "DEPOSIT"})
        groups = _fx_groups(out)
        assert len(groups) == 1 and _all_pair_problems(out) == [], f"one pair expected: {groups}; {_all_pair_problems(out)}"
        assert [(tx.description, tx.date) for tx in next(iter(groups.values()))] == [("FX Credit / FX Debit", date(2025, 9, 16))] * 2

    def test_legs_pair_within_their_own_order(self, tmp_path: Path):
        """Two orders at the same date and time, their rows interleaved: each leg pairs with the row of its own Order Id, the only candidate there."""
        orders = {"a": _order(41), "b": _order(42)}
        shared = {"isin": APPLE, "product": APPLE_NAME, "day": "08-09-2025", "time": "15:31"}
        rows, expected = _scenario(
            [
                (Row("FX Credit", amount="100,00", currency="USD", fx="1,1700", order_id=orders["a"], **shared), "FX_CONVERSION"),
                (Row("FX Credit", amount="50,00", currency="USD", fx="1,1700", order_id=orders["b"], **shared), "FX_CONVERSION"),
                (Row("FX Debit", amount="-85,47", order_id=orders["a"], **shared), "FX_CONVERSION"),
                (Row("FX Debit", amount="-42,74", order_id=orders["b"], **shared), "FX_CONVERSION"),
                (Row(f"Buy 1 {APPLE_NAME}@100 USD ({APPLE})", amount="-100,00", currency="USD", order_id=orders["a"], **shared), "BUY"),
                (Row(f"Buy 1 {APPLE_NAME}@50 USD ({APPLE})", amount="-50,00", currency="USD", order_id=orders["b"], **shared), "BUY"),
            ]
        )
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert {_pair_cash(group) for group in _fx_groups(out).values()} == {frozenset({("USD", "100"), ("EUR", "-85.47")}), frozenset({("USD", "50"), ("EUR", "-42.74")})}
        assert len(_fx_groups(out)) == 2 and _all_pair_problems(out) == []

    def test_without_an_order_legs_pair_by_date_and_time(self, tmp_path: Path):
        """No Order Id: the group is the date and the time. A leg one minute away from the other row has no partner."""
        rows, expected = _scenario(
            [
                (Row("FX Credit", amount="3,49", day="16-09-2025", time="06:45"), "FX_CONVERSION"),
                (Row("FX Debit", amount="-4,08", currency="USD", fx="1,1690", day="16-09-2025", time="06:45"), "FX_CONVERSION"),
                (Row("FX Credit", amount="5,00", day="17-09-2025", time="06:45"), UNPAIRED_FX),
                (Row("FX Debit", amount="-5,85", currency="USD", fx="1,1700", day="17-09-2025", time="06:46"), UNPAIRED_FX),
            ]
        )
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert {_pair_cash(group) for group in _fx_groups(out).values()} == {frozenset({("EUR", "3.49"), ("USD", "-4.08")})}

    @pytest.mark.parametrize("arrangement", list(FEE_ARRANGEMENTS))
    def test_the_fee_of_the_order_is_never_the_partner(self, arrangement: str, tmp_path: Path):
        """In euros and negative, the fee qualifies as a candidate for the dollar leg: the adjacent row wins, and the fee stays a FEE on the order's asset (lines 18-22 of the Dutch sample, lines 12-16 of the English one)."""
        roles = FEE_ARRANGEMENTS[arrangement]
        by_role = _apple_order_rows(_order(43))
        rows, expected = _scenario([(by_role[role], OUTCOME_OF_ROLE[role]) for role in roles])
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert {_pair_cash(group) for group in _fx_groups(out).values()} == {frozenset({("USD", "901.25"), ("EUR", "-770.16")})}
        assert [(_num(tx.cash.amount), _isin(out, tx)) for tx in _of_type(out, "FEE")] == [("-1", APPLE)]

    def test_legs_with_the_same_words_share_them_once(self, tmp_path: Path):
        """In Czech both legs read «FX vyúčtování konverze měny», the direction is in the sign alone: the pair's description is that text, not «X / X»."""
        text = "FX vyúčtování konverze měny"
        rows = [Row(text, amount="3,49", day="16-09-2025", time="06:45"), Row(text, amount="-4,08", currency="USD", fx="1,1690", day="16-09-2025", time="06:45")]
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, _every_line(rows, "FX_CONVERSION"))
        assert [tx.description for tx in out.transactions] == [text, text]

    def test_a_leg_without_a_partner_is_listed_not_imported(self, tmp_path: Path):
        """No row in the group, a candidate with the same sign, a candidate in the same currency: ``degiro_unpaired_fx`` for the leg and for the leg words left alone, no FX_CONVERSION."""
        rows, expected = _scenario(
            [
                (Row("FX Debit", amount="-1,36", currency="USD", fx="1,0613", day="17-12-2022", time="08:37"), UNPAIRED_FX),
                (Row("FX Debit", amount="-2,00", currency="USD", fx="1,1700", day="18-12-2022", time="08:00"), UNPAIRED_FX),
                (Row("FX Credit", amount="-1,71", day="18-12-2022", time="08:00"), UNPAIRED_FX),
                (Row("FX Debit", amount="-3,00", currency="USD", fx="1,1700", day="19-12-2022", time="08:00"), UNPAIRED_FX),
                (Row("FX Credit", amount="3,00", currency="USD", day="19-12-2022", time="08:00"), UNPAIRED_FX),
                (Row("iDEAL Deposit", amount="27,80", day="20-12-2022", time="09:51"), "DEPOSIT"),
            ]
        )
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, expected)
        assert sorted(_row_numbers(_the_notice(out, UNPAIRED_FX))) == [2, 3, 4, 5, 6]

    def test_a_leg_between_two_candidates_is_ambiguous(self, tmp_path: Path):
        """Two qualifying rows, both adjacent to the leg: no pair is guessed, the three rows are listed as ``degiro_unpaired_fx``."""
        rows = [
            Row("FX Credit", amount="1,00", day="16-09-2025", time="06:45"),
            Row("FX Debit", amount="-1,17", currency="USD", fx="1,1700", day="16-09-2025", time="06:45"),
            Row("FX Credit", amount="1,01", day="16-09-2025", time="06:45"),
        ]
        out = _parse(_write(tmp_path, rows))

        _assert_outcomes(out, rows, _every_line(rows, UNPAIRED_FX))

    @pytest.mark.parametrize("sample", [EN_SAMPLE, NL_SAMPLE], ids=lambda path: path.name)
    def test_the_link_uuid_is_the_same_on_every_parse(self, sample: Path):
        """``parse`` is idempotent (``plugin_version`` caching): the same file gives the same ``link_uuid`` to the same legs."""
        first = _links(_parse(sample))
        assert first, f"presence barrier: {sample.name} gives no FX_CONVERSION"

        assert _links(_parse(sample)) == first

    def test_the_link_uuid_survives_a_windows_1252_copy(self, tmp_path: Path):
        """The UUID comes from the decoded text, never from the bytes: the same French statement saved as UTF-8 and as Windows-1252 gives the same pair."""
        rows = [
            Row("Opération de change - Crédit", amount="3,49", day="16-09-2025", time="06:45"),
            Row("Opération de change - Débit", amount="-4,08", currency="USD", fx="1,1690", day="16-09-2025", time="06:45"),
            Row("Dépôt", amount="100,00", day="17-09-2025", time="09:00"),
        ]
        utf8 = _write(tmp_path / "utf8", rows, header=FR_HEADER)
        windows = _write(tmp_path / "cp1252", rows, header=FR_HEADER, encoding="cp1252")
        with pytest.raises(UnicodeDecodeError):
            windows.read_bytes().decode("utf-8")  # premise: only the encoding fallback reads the copy

        original, copy = _parse(utf8), _parse(windows)

        assert len(_links(original)) == 2 and _all_pair_problems(original) == [], f"presence barrier: one pair in the French statement: {_links(original)}"
        assert (_links(copy), [tx.description for tx in copy.transactions]) == (_links(original), [tx.description for tx in original.transactions])

    def test_another_file_gives_another_link_uuid(self, tmp_path: Path):
        """The same conversion on the same lines of two files whose other rows differ: two ``link_uuid``, so that two imports never collide in one batch."""
        rows = _conversion_rows()
        other = [*rows[:2], Row("iDEAL Deposit", amount="200,00", day="17-09-2025", time="09:00")]

        first, second = _links(_parse(_write(tmp_path / "first", rows))), _links(_parse(_write(tmp_path / "second", other)))

        assert len(set(first.values())) == 1 and set(first) == set(second), f"presence barrier: one pair in each file: {first}, {second}"
        assert set(first.values()).isdisjoint(second.values()), f"two different files give the same link_uuid {first}"


# =============================================================================
# E. NUMBERS (plan §2.3, D1)
# =============================================================================

# Values whose reading is certain: both marks (the last is decimal), a repeated mark (thousands), one mark followed
# by 1, 2 or at least 4 digits (decimal), spaces and no-break spaces (thousands), a zero integer part (decimal).
CERTAIN_NUMBERS = [
    pytest.param("1,1734", "1.1734", id="comma-then-four-digits"),
    pytest.param("-1,2108", "-1.2108", id="negative-comma-then-four-digits"),
    pytest.param("-1.2108", "-1.2108", id="point-then-four-digits"),
    pytest.param("1.234,56", "1234.56", id="point-thousands-comma-decimal"),
    pytest.param("1,234.56", "1234.56", id="comma-thousands-point-decimal"),
    pytest.param("-1.124,00", "-1124.00", id="negative-thousands"),
    pytest.param("1.234.567", "1234567", id="repeated-point"),
    pytest.param("1,234,567", "1234567", id="repeated-comma"),
    pytest.param("1 046,3825", "1046.3825", id="space-thousands"),
    pytest.param("1\u00a0046,3825", "1046.3825", id="no-break-space-thousands"),
    pytest.param("27,80", "27.80", id="comma-then-two-digits"),
    pytest.param("-97.93", "-97.93", id="point-then-two-digits"),
    pytest.param("-19.5", "-19.5", id="point-then-one-digit"),
    pytest.param("0,039", "0.039", id="zero-integer-part"),
    pytest.param("0", "0", id="zero"),
]
# Values a single mark followed by exactly three digits leaves ambiguous: the file's decimal mark decides; without one, decimal.
AMBIGUOUS_NUMBERS = [
    pytest.param("1.000", ",", "1000", id="point-in-a-comma-file"),
    pytest.param("1.000", ".", "1.000", id="point-in-a-point-file"),
    pytest.param("49,785", ",", "49.785", id="comma-in-a-comma-file"),
    pytest.param("49,785", ".", "49785", id="comma-in-a-point-file"),
    pytest.param("1.000", None, "1.000", id="point-without-a-file-mark"),
    pytest.param("49,785", None, "49.785", id="comma-without-a-file-mark"),
]


def _number_parser() -> Any:
    """``_parse_degiro_number(value, decimal_hint=None)``."""
    parse = _module_attribute("_parse_degiro_number")
    assert "decimal_hint" in inspect.signature(parse).parameters, "_parse_degiro_number has no decimal_hint parameter: the file's decimal mark cannot decide the ambiguous values (D1)"
    return parse


class TestNumbers:
    """E — D1: a value is read on its own when its form is certain, and the file's decimal mark decides only the ambiguous ones.

    The Dutch collage mixes both marks (§1.3): one mark for the whole file would read ``-97.93`` as ``-9793``. Some
    certain cases pass today too: they guard what the rewrite keeps.
    """

    @pytest.mark.parametrize(("text", "expected"), CERTAIN_NUMBERS)
    def test_a_certain_value_is_read_on_its_own(self, text: str, expected: str):
        value = _module_attribute("_parse_degiro_number")(text)

        assert value == Decimal(expected) and isinstance(value, Decimal), f"{text!r} reads {value!r}, expected {expected}"

    @pytest.mark.parametrize(("text", "expected"), CERTAIN_NUMBERS)
    def test_a_certain_value_ignores_the_file_mark(self, text: str, expected: str):
        parse = _number_parser()

        assert (parse(text, decimal_hint=","), parse(text, decimal_hint=".")) == (Decimal(expected), Decimal(expected))

    @pytest.mark.parametrize(("text", "hint", "expected"), AMBIGUOUS_NUMBERS)
    def test_an_ambiguous_value_follows_the_file_mark(self, text: str, hint: Optional[str], expected: str):
        assert _number_parser()(text, decimal_hint=hint) == Decimal(expected)

    @pytest.mark.parametrize("text", ["", "   "])
    def test_a_blank_value_is_none(self, text: str):
        """Guard: a blank cell is no number."""
        assert _module_attribute("_parse_degiro_number")(text) is None

    @pytest.mark.parametrize(
        ("rows", "shape", "currency"),
        [
            pytest.param(
                [Row(f"Koop 1.000 @ 0,05 EUR ({SAP})", amount="-50,00", isin=SAP, product=SAP_NAME, order_id=_order(51), balance="1.950,00"), Row("iDEAL Deposit", amount="2.000,00", time="09:00", balance="2.000,00")],
                {"delimiter": ";", "newline": "\r\n"},
                "EUR",
                id="comma-file",
            ),
            pytest.param(
                [Row(f"Buy 1,000 {APPLE_NAME}@0.05 USD ({APPLE})", amount="-50.00", currency="USD", isin=APPLE, product=APPLE_NAME, order_id=_order(52), balance="1950.00"), Row("iDEAL Deposit", amount="2000.00", time="09:00", balance="2000.00")],
                {"delimiter": ",", "newline": "\n"},
                "USD",
                id="point-file",
            ),
        ],
    )
    def test_the_quantity_of_a_trade_follows_the_file_mark(self, rows: List[Row], shape: Dict[str, str], currency: str, tmp_path: Path):
        """``1.000`` in a file whose amounts write a decimal comma (``-50,00``, ``1.950,00``) is a thousand shares; ``1,000`` in a file of decimal points, too."""
        out = _parse(_write(tmp_path, rows, **shape))

        _assert_outcomes(out, rows, {2: "BUY", 3: "DEPOSIT"})
        assert [(_num(tx.quantity), _tx_cash(tx)) for tx in _of_type(out, "BUY")] == [("1000", (currency, "-50"))]


# =============================================================================
# F. LANGUAGES AND MESSAGES (plan §2.7, D4)
# =============================================================================

LANGUAGE_CASES = [
    *(pytest.param(header, MESSAGE_LANGUAGE[language], id=f"{language}-header") for language, header in STATEMENT_HEADERS.items()),
    pytest.param(("Datum", "Col 2", "Col 3", "Col 4", "ISIN", "Col 6", "FX", "Col 8", "", "Col 10", "", "Col 12"), "en", id="only-datum"),
    pytest.param(("Datum", "Tijd", "Col 3", "Col 4", "ISIN", "Col 6", "FX", "Col 8", "", "Col 10", "", "Col 12"), "en", id="two-dutch-columns"),
    pytest.param(("Col 1", "Tijd", "Col 3", "Col 4", "ISIN", "Omschrijving", "FX", "Mutatie", "", "Col 10", "", "Col 12"), "nl", id="three-dutch-columns"),
    pytest.param(("Datum", "Col 2", "Valutadatum", "Col 4", "ISIN", "Col 6", "FX", "Col 8", "", "Saldo", "", "Col 12"), "en", id="dutch-german-tie"),
]


class TestLanguagesAndMessages:
    """F — the header decides the language of the messages, scored on its named columns (``ISIN`` and ``FX`` do not count): the best language wins
    with at least three matches and alone; anything else is English. Wrong language touches the messages only, never the reading."""

    @pytest.mark.parametrize(("header", "expected"), LANGUAGE_CASES)
    def test_the_header_decides_the_language(self, header: Tuple[str, ...], expected: str):
        """«Datum» is Dutch and German: alone it decides nothing. PT and IT have no catalogue yet (unverified headers): English."""
        assert _module_attribute("_detect_language")(list(header)) == expected

    def test_the_catalogue_has_every_code_in_five_languages(self):
        """``_MESSAGES[language][code]`` for EN, NL, DE, FR, ES and every code; each template takes ``n``; Dutch is not English."""
        messages = _messages()
        assert set(messages) == set(CATALOGUE_LANGUAGES), f"_MESSAGES languages {sorted(messages)}, expected {sorted(CATALOGUE_LANGUAGES)}"

        missing = [f"{language}/{code}" for language in CATALOGUE_LANGUAGES for code in NOTICE_CODES if not str(messages[language].get(code) or "").strip()]
        assert not missing, f"templates missing: {missing}"
        unformattable = []
        for language in CATALOGUE_LANGUAGES:
            for code in NOTICE_CODES:
                try:
                    messages[language][code].format(n=3)
                except (KeyError, IndexError, ValueError) as exc:
                    unformattable.append(f"{language}/{code}: {exc!r}")
        assert not unformattable, f"templates that do not format with n alone: {unformattable}"
        assert [code for code in NOTICE_CODES if messages["nl"][code] == messages["en"][code]] == [], "a Dutch message is the English one"

    @pytest.mark.parametrize("language", list(STATEMENT_HEADERS))
    def test_a_notice_speaks_the_language_of_the_header(self, language: str, tmp_path: Path):
        """One unknown row under each verified header: the notice's ``context.language`` and message come from the header; PT and IT speak English."""
        expected = MESSAGE_LANGUAGE[language]
        out = _parse(_write(tmp_path, [Row("Zorglub bonification", amount="5,00")], header=STATEMENT_HEADERS[language]))

        notice = _the_notice(out, UNKNOWN_ROWS)

        assert (_context(notice), notice.message) == ({"language": expected, "count": 1}, _messages()[expected][UNKNOWN_ROWS].format(n=1))

    def test_no_i18n_key_overrides_the_language_of_the_file(self):
        """Guard: the wizard translates ``importWizard.brimNotice.<code>`` into the UI language when the key exists, and falls back to the plugin's message
        otherwise (``resolveBrimNotice.ts``). A ``degiro_*`` key would replace the message in the file's language: none may exist."""
        catalogues = sorted(I18N_DIR.glob("*.json"))
        notices = {path.name: json.loads(path.read_text(encoding="utf-8")).get("importWizard", {}).get("brimNotice", {}) for path in catalogues}
        assert notices.get("en.json"), f"premise: en.json has the importWizard.brimNotice namespace the wizard reads: {sorted(notices)}"

        overriding = [f"{name}: importWizard.brimNotice.{key}" for name, keys in notices.items() for key in keys if key.startswith("degiro_")]

        assert not overriding, f"i18n keys override the DEGIRO messages: {overriding}"


# =============================================================================
# THE ORDERS LIST (decision 7, D9)
# =============================================================================


class TestOrdersList:
    """D9: the «Transactions» export is the list of the orders, not of the cash movements. DEGIRO recognises it (above the generic CSV), imports nothing
    and says so in the language of its header: the file goes to ``parsed`` with the notice (§1.7), no ``BRIMParseError``."""

    @pytest.mark.parametrize(("header", "rows", "newline", "language"), [pytest.param(ORDERS_EN, ORDERS_EN_ROWS, "\r\n", "en", id="english-17-columns"), pytest.param(ORDERS_NL, ORDERS_NL_ROWS, "\n", "nl", id="dutch")])
    def test_the_orders_list_imports_nothing_and_says_so(self, header: str, rows: Tuple[str, ...], newline: str, language: str, tmp_path: Path):
        path = tmp_path / "Transactions.csv"
        path.write_bytes(_orders_bytes(header, rows, newline))

        out = _parse(path)

        assert (out.transactions, [notice.code for notice in out.warnings]) == ([], [ORDERS_LIST]), f"the orders list gives {len(out.transactions)} transaction(s) and the notices {[(notice.code, notice.message) for notice in out.warnings]}"
        notice = out.warnings[0]
        context = notice.context or {}
        assert (notice.severity, context.get("language"), isinstance(context.get("count"), int)) == ("warning", language, True), f"severity {notice.severity!r}, context {context}"
        assert notice.message == _messages()[language][ORDERS_LIST].format(n=context["count"])
