"""
Test Suite: Crédit Agricole report sets — the rows, the classes, rule M, the pairs and the balances (W5-7, steps 2-5)

The modules under test are not wired to the plugin yet, so they are tested directly:

- ``broker_credit_agricole._rows``: the two exports read as rows (``read_securities``, ``read_account``), what the XLSX
  header (the testata) states, ``account_fingerprint``, ``detect_role``;
- ``broker_credit_agricole._report_set``: rule M with the Crédit Agricole policy, the classes of a row, the pairs of a
  securities row and an account row, the statements, intervals and holes of the account balances, the truth points
  (``Analysis``), ``describe_member`` and ``describe_set``;
- ``broker_credit_agricole._classify``: the causale registry (its tiers).

What is pinned, by area (letters follow the plan, W5-7):

- A reading: what is not a row (blank rows, rows without a date or a causale, the recap footer), a zero amount dropped,
  an unreadable amount kept as ``invalid``; ``cells`` keep the file's text; the testata in its two spellings (label and
  value in one cell, or the value in the next filled cell) and the five-digit year ``02026`` only there;
  ``chain_closes``; ``account_fingerprint``;
- B ``detect_role`` for CSV and XLSX; ``None`` for anything else;
- C ``describe_member``: role, rows and coverage on the ``trade`` and ``value`` axes;
- D rule M: identical rows once, a download cut mid-day loses the day without a mismatch, two downloads that contradict
  are a mismatch, multiplicity inside one file is kept;
- E classes of a securities row and of an account row;
- F pairing: the key is the kind of fact, the amount to the cent and the VALUE date; operation dates may differ; no
  guess on ambiguity; the outcome of every row;
- G balances: ``explained_by_rows`` cell by cell and the six scenarios of the plan (closed chain, the real-world hole,
  the key test that the hole disappears once the rows are there, a broken chain, a CSV-only set, a broken interval
  after a good opening);
- H in-flight cash; I opening positions; J zones; K dates (the operation date is never replaced by the value date);
- L ``describe_set``.

From the section "W5-7 STEP 6" on, the subject is the plugin ``broker_credit_agricole`` 2.0.0 wired to that analysis: its
contract, ``combine`` (the combined table), ``parse`` (the combined file), the standalone account rows (parity with 1.5.0, as
literals) and the end-to-end proofs (``apply_history`` and ``compute_gap_fix`` on a private in-memory database).

Every file is synthetic: written under ``tmp_path_factory`` by the builders of this module, with invented names, ISINs,
dossier numbers and amounts. No server, no database, no network, no clock: pure.

Plan: LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md,
section "W5-7 · Crédit Agricole sui report set — piano dettagliato".
"""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import openpyxl
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlmodel import SQLModel

import backend.app.db.models  # noqa: F401 — registers the app tables on SQLModel.metadata (the end-to-end proofs of step 6)
from backend.app.db.models import TransactionType
from backend.app.schemas.brim import BRIMCheckpoint, BRIMCombinedTable, BRIMCoverage, BRIMGapFixRequest, BRIMParseOutput, BRIMTruthCash, is_fake_asset_id
from backend.app.schemas.common import Currency, DateRangeModel
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim import brim_report_set_core as core
from backend.app.services.brim import brim_report_sets
from backend.app.services.brim.brim_gap_fix import compute_gap_fix
from backend.app.services.brim.brim_provider import BRIMParseError, BRIMProvider, BRIMSetRequiredError
from backend.app.services.brim.combined_files import write_combined_csv
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.brim_providers.broker_credit_agricole import _classify as classify_module
from backend.app.services.brim_providers.broker_credit_agricole._report_set import (
    ZONE_BEFORE,
    ZONE_GAP,
    ZONE_WINDOW,
    Analysis,
    Statement,
    classify_account,
    classify_securities,
    describe_member,
    describe_set,
    explained_by_rows,
    pair_rows,
)
from backend.app.services.brim_providers.broker_credit_agricole._rows import (
    ACCOUNT_COLUMNS,
    ROLE_ACCOUNT,
    ROLE_SECURITIES,
    SECURITIES_COLUMNS,
    AccountRow,
    SecuritiesRow,
    account_fingerprint,
    detect_role,
    parse_testata_date,
    read_account,
    read_securities,
)
from backend.app.services.brim_providers.broker_credit_agricole._rows import (
    Testata as Header,
)
from backend.test_scripts.brim_samples import SampleDir

# =============================================================================
# CONSTANTS
# =============================================================================

SECURITIES_CSV_HEADER = "Data operazione;Nome;Divisa;Causale;Prezzo;Divisa;Cambio;Quantità;Controvalore in Euro;Data valuta"
ACCOUNT_CSV_HEADER = "Data Op.;Data Val.;Causale;Descrizione;Importo;Divisa"

INCOME_CAUSALE = "CEDOLE, DIVIDENDI, PREMI ESTRATTI"
TRADE_CAUSALE = "COMPRAVENDITA TITOLI/FONDI/OPZIONI"
SCT_CAUSALE = "GIROCONTO/BONIFICO"
MATURITY_CAUSALE = "TITOLI SCADUTI O ESTRATTI"

# Invented securities. The securities export prints the name in full, the account export truncates it (a prefix).
BOND_A, BOND_A_ACC, ISIN_A = "BTP SAMPLE 1/12/2026 1.25%", "BTP SAMPLE 1/12/2026", "IT0000000001"
BOND_B, BOND_B_ACC, ISIN_B = "BTP DEMO 15/03/2033 3.35%", "BTP DEMO 15/03/2033", "IT0000000002"
FUND_X = "SAMPLE GLOB EQ FUND"
FUND_R_SEC, FUND_R_ACC = "SAMPLE FUND SICAV CL B", "SAMPLE FUND SICAV"

SAME = "="  # a value date equal to the operation date


# =============================================================================
# BUILDERS — the two exports as the bank writes them, from invented rows
# =============================================================================


def d(text: str) -> date:
    return date.fromisoformat(text)


def dmy(text: str) -> str:
    return d(text).strftime("%d/%m/%Y")


def it(amount: Any, *, thousands: bool = True) -> str:
    """A number as the bank writes it: comma decimal, dot thousands (``1.234,56``)."""
    places = max(2, -Decimal(str(amount)).as_tuple().exponent)  # an amount written with three decimals (1000,005) keeps them
    text = f"{abs(Decimal(str(amount))):,.{places}f}".replace(",", "\x00").replace(".", ",").replace("\x00", "." if thousands else "")
    return ("-" if Decimal(str(amount)) < 0 else "") + text


@dataclass(frozen=True)
class Sec:
    """One securities row. Dates are ISO; ``value`` is ``"="`` (the operation date), a date, or ``""`` (empty cell)."""

    op: str
    name: str
    causale: str
    qty: str = "0"
    ctv: str = "0"
    value: str = SAME
    currency: str = "EUR"

    def value_text(self) -> str:
        return dmy(self.op) if self.value == SAME else (dmy(self.value) if self.value else "")


@dataclass(frozen=True)
class Acc:
    """One account row. ``amount`` is a plain decimal text, or any text written as is (an unreadable amount)."""

    op: str
    causale: str
    desc: str
    amount: str
    value: str = SAME
    currency: str = "EUR"

    def value_text(self) -> str:
        return dmy(self.op) if self.value == SAME else (dmy(self.value) if self.value else "")

    def amount_text(self, *, apostrophe: bool = True) -> str:
        try:
            number = Decimal(self.amount)
        except Exception:  # noqa: BLE001 — a test amount that is not a number is written as is, on purpose
            return self.amount
        return ("'-" if apostrophe else "-") + it(abs(number)) if number < 0 else it(number)


def _sec_cells(row: Sec) -> List[str]:
    return [dmy(row.op), row.name, row.currency, row.causale, "0,00", row.currency, "1", row.qty, it(row.ctv) if row.ctv != "" else "", row.value_text()]


def _acc_cells(row: Acc) -> List[str]:
    return [dmy(row.op), row.value_text(), row.causale, row.desc, row.amount_text(), row.currency]


def _write_text(path: Path, lines: Sequence[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    return path


def write_securities_csv(path: Path, rows: Sequence[Sec], *, extra: Sequence[str] = ()) -> Path:
    return _write_text(path, [SECURITIES_CSV_HEADER, *(";".join(_sec_cells(row)) for row in rows), *extra])


def write_securities_xlsx(
    path: Path,
    rows: Sequence[Sec],
    *,
    dossier: str = "1234500001",
    support: str = "9876500002",
    liquidity: Optional[str] = "7.250,00 EUR",
    updated: Optional[str] = "25/07/02026",
) -> Path:
    """The securities XLSX: a preamble, two empty leading columns, the ``Divisa`` cell holding the causale (a real quirk),
    and recap rows without a date at the end."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append([])
    sheet.append([])
    sheet.append([None] * 11 + ["Lista Movimenti Deposito Titoli"])
    sheet.append([])
    sheet.append([])
    sheet.append([None, None, "Dossier n.", dossier] if dossier else [])
    sheet.append([None, None, "C/C di appoggio", support, None, None, None, None, None, None, "Data Aggiornamento", updated] if support else [None] * 10 + ["Data Aggiornamento", updated])
    sheet.append([None, None, "Liquidità", liquidity, None, None, None, None, None, None, "Intestatari", "ROSSI MARIO"] if liquidity else [])
    sheet.append([])
    sheet.append([None, None, "Data operazione", "Nome", "Divisa", "Causale", "Prezzo", "Divisa prezzo", "Cambio", "Quantità", "Ctv in Eur", "Data Valuta"])
    for row in rows:
        sheet.append([None, None, dmy(row.op), row.name, row.causale, row.causale, "0,00", row.currency, "1", row.qty, it(row.ctv) if row.ctv != "" else "", row.value_text()])
    sheet.append([None, None, None, "Totale operazioni", None, None, None, None, None, None, "0,00"])
    sheet.append([None, None, "Riepilogo cedole", None, None, None, None, None, None, None, "0,00"])
    workbook.save(path)
    return path


def write_account_csv(path: Path, rows: Sequence[Acc], *, extra: Sequence[str] = ()) -> Path:
    return _write_text(path, [ACCOUNT_CSV_HEADER, *(";".join(_acc_cells(row)) for row in rows), *extra])


def write_account_xlsx(
    path: Path,
    rows: Sequence[Acc],
    *,
    opening: Optional[str] = None,
    closing: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    form: str = "one_cell",
    thousands: bool = False,
) -> Path:
    """The account XLSX with its testata above the table.

    ``form``: ``one_cell`` (``Saldo Iniziale 1000,00 EUR`` in one cell), ``next_cell`` (the label in a cell, the value in
    the next filled cell, as text) or ``typed`` (the same, but numbers and dates are real cells).
    """
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["Lista Movimenti Conto"])
    balances: List[Any] = []
    periods: List[Any] = []
    for label, column, amount, day_text in (("Saldo Iniziale", 0, opening, None), ("Saldo Finale", 3, closing, None), ("Data dal", 0, None, date_from), ("Data al", 3, None, date_to)):
        value: Any = None
        if amount is not None:
            value = f"{it(amount, thousands=thousands)} EUR" if form != "typed" else float(Decimal(amount))
        elif day_text is not None:
            value = dmy(day_text) if form != "typed" else datetime.combine(d(day_text), datetime.min.time())
        if value is None:
            continue
        target = balances if amount is not None else periods
        while len(target) < column + 3:
            target.append(None)
        if form == "one_cell":
            target[column] = f"{label} {value}"
        else:
            target[column] = label
            target[column + 2] = value
    if balances:
        sheet.append(balances)
    if periods:
        sheet.append(periods)
    sheet.append([])
    sheet.append(["Data Op.", "Data Val.", "Causale", "Descrizione", "Importo", "Divisa"])
    for row in rows:
        sheet.append(_acc_cells(row))
    sheet.append(["Totale Entrate/Uscite/Movimenti €", None, None, None, "0,00"])
    sheet.append([None, None, None, "Totale Entrate/Uscite/Movimenti €", "0,00"])
    workbook.save(path)
    return path


class Work:
    """A folder of synthetic files, and the analysis of a set of them."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.count = 0

    def _path(self, stem: str, extension: str) -> Path:
        self.count += 1
        return self.folder / f"{stem}-{self.count}.{extension}"

    def sec(self, rows: Sequence[Sec], kind: str = "csv", **options: Any) -> Path:
        if kind == "csv":
            return write_securities_csv(self._path("securities", "csv"), rows, **options)
        return write_securities_xlsx(self._path("securities", "xlsx"), rows, **options)

    def acc(self, rows: Sequence[Acc], kind: str = "csv", **options: Any) -> Path:
        if kind == "csv":
            return write_account_csv(self._path("account", "csv"), rows, **options)
        return write_account_xlsx(self._path("account", "xlsx"), rows, **options)

    def text(self, name: str, lines: Sequence[str]) -> Path:
        return _write_text(self.folder / name, lines)

    @staticmethod
    def analysis(sec: Sequence[Path] = (), acc: Sequence[Path] = ()) -> Analysis:
        return Analysis({ROLE_SECURITIES: list(sec), ROLE_ACCOUNT: list(acc)})


@pytest.fixture
def work(tmp_path_factory: pytest.TempPathFactory) -> Work:
    return Work(tmp_path_factory.mktemp("ca"))


# --- row factories: the facts of the plan (a coupon, a purchase, a fund redemption, a maturity) --------------------


def coupon_sec(op: str, amount: str, *, name: str = BOND_A, value: str = SAME, qty: str = "40000", currency: str = "EUR") -> Sec:
    return Sec(op, name, "CEDOLA", qty, amount, value, currency)


def coupon_acc(op: str, amount: str, *, name: str = BOND_A_ACC, isin: str = ISIN_A, ritenuta: str = "31,25", value: str = SAME, currency: str = "EUR") -> Acc:
    desc = f"CEDOLA:{name} {isin} DOS:00000/00000000 NOMINALE: 40.000,00 TASSO: 1,25 ALIQ: 12,50 RITENUTA: {ritenuta} DATA : 01/06/2026 N.MOVIM: 1"
    return Acc(op, INCOME_CAUSALE, desc, amount, value, currency)


def buy_sec(op: str, amount: str, *, name: str = BOND_B, qty: str = "5000", value: str = SAME) -> Sec:
    return Sec(op, name, "ACQ.CONT.SU MERC.", qty, amount, value)


def buy_acc(op: str, amount: str, *, name: str = BOND_B_ACC, value: str = SAME) -> Acc:
    return Acc(op, TRADE_CAUSALE, f"NOTA INF. ACQ. TIT:{name} DOSS:00000/00000000", f"-{amount}", value)


def fund_buy_sec(op: str, amount: str, *, value: str = SAME) -> Sec:
    return Sec(op, FUND_X, "SICAV: SOTTOSCR", "1867.178", amount, value)


def fund_buy_acc(op: str, amount: str, *, value: str = SAME) -> Acc:
    return Acc(op, TRADE_CAUSALE, f"SOTTOSC SICAV ORD.:2026/000000001 {FUND_X}", f"-{amount}", value)


def redeem_sec(op: str, amount: str, *, name: str = FUND_R_SEC, value: str = SAME) -> Sec:
    return Sec(op, name, "FONDI: RIMBORSO", "100", amount, value)


def redeem_acc(op: str, amount: str, *, name: str = FUND_R_ACC, value: str = SAME) -> Acc:
    return Acc(op, SCT_CAUSALE, f"ORD:{name} DT.ORD:000000 DESCR.OPERAZIONE SCT::RIMBORSI: : :SU {name} CL B", amount, value)


def matured_sec(op: str, amount: str, *, name: str = BOND_A, value: str = SAME) -> Sec:
    return Sec(op, name, "TITOLI SCADUTI", "40000", amount, value)


def matured_acc(op: str, amount: str, *, name: str = BOND_A_ACC, value: str = SAME) -> Acc:
    return Acc(op, MATURITY_CAUSALE, f"RIMB.TIT. {name} (0000000 ) DOS:00000/00000000", amount, value)


def transfer_sec(op: str, name: str, qty: str, *, causale: str = "GIRO ALTRO DOSSIER", value: str = SAME) -> Sec:
    return Sec(op, name, causale, qty, "0", value)


def pos_acc(op: str, amount: str, tag: str = "a") -> Acc:
    return Acc(op, "PAGAMENTO TRAMITE POS", f"POS CARTA 00000000 {tag}", amount)


def salary_acc(op: str, amount: str, tag: str = "a") -> Acc:
    return Acc(op, "ACCREDITO EMOLUMENTI", f"STIPENDIO SAMPLE {tag}", amount)


FACTORIES: Dict[str, Tuple[Callable[..., Sec], Callable[..., Acc]]] = {
    "coupon": (coupon_sec, coupon_acc),
    "buy": (buy_sec, buy_acc),
    "redeem": (redeem_sec, redeem_acc),
    "matured": (matured_sec, matured_acc),
}


# --- helpers to read results ---------------------------------------------------------------------------------------


def pick(rows: Sequence[Any], **attrs: Any) -> Any:
    """The one row whose attributes equal ``attrs`` (a row is found by what it is, never by its position)."""
    found = [row for row in rows if all(getattr(row, key) == value for key, value in attrs.items())]
    assert len(found) == 1, f"{len(found)} rows match {attrs}"
    return found[0]


def codes(analysis: Analysis) -> List[str]:
    return [notice.code for notice in analysis.set_notices()]


def notice_of(analysis: Analysis, code: str) -> Any:
    return pick(analysis.set_notices(), code=code)


def outcome_of(row: Any) -> Tuple[str, str]:
    return row.outcome.kind, row.outcome.reason


@dataclass
class Paired:
    securities: List[SecuritiesRow]
    account: List[AccountRow]
    pairs: List[Tuple[SecuritiesRow, AccountRow]]
    ambiguous: List[Any]

    def indexes(self) -> set:
        return {(self.securities.index(sec), self.account.index(acc)) for sec, acc in self.pairs}


def pair(work: Work, secs: Sequence[Sec], accs: Sequence[Acc]) -> Paired:
    """Read two files and run ``pair_rows`` on their rows, with no rule M and no balances in between."""
    securities = read_securities(work.sec(secs)).rows
    account = read_account(work.acc(accs)).rows
    for sec in securities:
        sec.klass = classify_securities(sec)
    for acc in account:
        acc.klass, acc.tier = classify_account(acc)
    pairs, ambiguous = pair_rows(securities, account)
    return Paired(securities, account, pairs, ambiguous)


def acc_row(op: str, amount: str, *, causale: str = "X", description: str = "", value: Optional[str] = None) -> AccountRow:
    day = d(op)
    return AccountRow(1, 1, 2, day, d(value) if value else day, causale, description, None if amount == "?" else Decimal(amount), "EUR", {})


def sec_row(causale: str, *, name: str = "N", op: str = "2026-01-02") -> SecuritiesRow:
    return SecuritiesRow(1, 1, 2, d(op), d(op), name, causale, None, None, None, "EUR", {})


# =============================================================================
# A. READING
# =============================================================================


class TestReadingSecurities:
    def test_what_is_a_row_and_what_is_not(self, work):
        path = work.text(
            "securities-mixed.csv",
            [
                SECURITIES_CSV_HEADER,
                f"01/06/2026;{BOND_A};EUR;CEDOLA;0,00;EUR;1;40000;187,50;01/06/2026",
                "",
                ";;;;;;;;;",
                ";NO DATE;EUR;CEDOLA;0,00;EUR;1;100;10,00;01/06/2026",
                "02/06/2026;NO CAUSALE;EUR;;0,00;EUR;1;100;10,00;02/06/2026",
                f"03/06/2026;{FUND_X};EUR;SICAV: SOTTOSCR;25,10;EUR;1;1867.178;46.870,00;05/06/2026",
                ";Totale operazioni;;;;;;;;",
            ],
        )
        rows = read_securities(path).rows
        assert [row.causale for row in rows] == ["CEDOLA", "SICAV: SOTTOSCR"]
        coupon, fund = rows
        assert (coupon.op, coupon.value, coupon.name, coupon.currency) == (d("2026-06-01"), d("2026-06-01"), BOND_A, "EUR")
        assert (coupon.qty, coupon.ctv) == (Decimal("40000"), Decimal("187.50"))
        assert (fund.op, fund.value) == (d("2026-06-03"), d("2026-06-05"))
        assert (fund.qty, fund.ctv, fund.price) == (Decimal("1867.178"), Decimal("46870.00"), Decimal("25.10"))
        # The file's own text is kept next to the parsed value.
        assert coupon.cells["Controvalore"] == "187,50"
        assert fund.cells["Quantità"] == "1867.178"
        assert fund.cells["Data valuta"] == "05/06/2026"
        # The row number is the physical line (header = 1), so the blank lines count.
        assert (coupon.row, fund.row) == (2, 7)
        assert fund.source == "securities:7"

    def test_the_causale_is_upper_cased_and_a_value_date_may_be_empty(self, work):
        path = work.text("securities-lower.csv", [SECURITIES_CSV_HEADER, f"01/06/2026;{BOND_A};EUR;cedola;0,00;EUR;1;40000;187,50;"])
        (row,) = read_securities(path).rows
        assert row.causale == "CEDOLA"
        assert row.value is None
        assert row.cells["Data valuta"] == ""

    def test_a_five_digit_year_is_only_read_in_the_testata_never_in_a_row(self, work):
        path = work.text("securities-year.csv", [SECURITIES_CSV_HEADER, f"01/06/02026;{BOND_A};EUR;CEDOLA;0,00;EUR;1;40000;187,50;01/06/2026"])
        assert read_securities(path).rows == []

    def test_xlsx_reads_like_the_csv_and_takes_the_currency_from_the_price_currency(self, work):
        rows = [coupon_sec("2026-06-01", "187.50"), fund_buy_sec("2026-06-03", "46870.00", value="2026-06-05"), buy_sec("2026-06-10", "5000.00", value="2026-06-12")]
        usd = Sec("2026-06-11", "SAMPLE US ETF", "ACQ.CONT.SU MERC.", "10", "900.00", SAME, "USD")
        as_tuple = lambda row: (row.op, row.value, row.name, row.causale, row.qty, row.ctv, row.currency)  # noqa: E731
        from_csv = read_securities(work.sec([*rows, usd], "csv")).rows
        from_xlsx = read_securities(work.sec([*rows, usd], "xlsx")).rows
        assert [as_tuple(row) for row in from_xlsx] == [as_tuple(row) for row in from_csv]
        assert pick(from_xlsx, name="SAMPLE US ETF").currency == "USD"
        # The recap rows at the foot are not rows.
        assert len(from_xlsx) == 4

    def test_the_securities_testata(self, work):
        testata = read_securities(work.sec([coupon_sec("2026-06-01", "187.50")], "xlsx")).testata
        assert testata.dossier == "1234500001"
        assert testata.support_account == "9876500002"
        assert testata.liquidity == Decimal("7250.00")
        assert testata.liquidity_currency == "EUR"
        assert testata.updated == date(2026, 7, 25)  # written 25/07/02026
        assert not testata.has_balances

    def test_a_csv_has_no_testata(self, work):
        testata = read_securities(work.sec([coupon_sec("2026-06-01", "187.50")])).testata
        assert testata == Header()
        assert account_fingerprint(testata) is None

    def test_a_file_without_the_header_has_no_rows(self, work):
        path = work.text("securities-nothing.csv", ["Colonna A;Colonna B", "1;2"])
        file = read_securities(path)
        assert file.rows == []
        assert file.testata == Header()


class TestReadingAccount:
    def test_what_is_a_row_and_what_is_not(self, work):
        path = work.text(
            "account-mixed.csv",
            [
                ACCOUNT_CSV_HEADER,
                "30/07/2026;30/07/2026;PAGAMENTO UTENZE;SDD A : UTILITY PROVIDER ADDEBITO SDD NUMERO 0000000001;'-61,20;EUR",
                "29/07/2026;29/07/2026;ACCREDITO EMOLUMENTI;PENSIONE SAMPLE;2.879,70;EUR",
                "28/07/2026;28/07/2026;COMMISSIONI/SPESE;STORNO AZZERATO;0,00;EUR",
                "27/07/2026;27/07/2026;COMMISSIONI/SPESE;STORNO AZZERATO CON APICE;'0,00;EUR",
                "26/07/2026;26/07/2026;PAGAMENTO TRAMITE POS;POS ILLEGGIBILE;n/d;EUR",
                "",
                ";;;;;",
                ";;PAGAMENTO UTENZE;SENZA DATA;'-5,00;EUR",
                "25/07/2026;25/07/2026;;SENZA CAUSALE;'-5,00;EUR",
                "Totale Entrate/Uscite/Movimenti €;;;;;",
                ";;;Totale Entrate;1234,00;",
            ],
        )
        rows = read_account(path).rows
        assert [row.description for row in rows] == ["SDD A : UTILITY PROVIDER ADDEBITO SDD NUMERO 0000000001", "PENSIONE SAMPLE", "POS ILLEGGIBILE"]
        utility, pension, unreadable = rows
        assert utility.amount == Decimal("-61.20")
        assert utility.cells["Importo"] == "'-61,20"  # the apostrophe is the file's text
        assert pension.amount == Decimal("2879.70")
        assert unreadable.amount is None
        assert unreadable.cells["Importo"] == "n/d"
        assert (utility.op, utility.value, utility.currency) == (d("2026-07-30"), d("2026-07-30"), "EUR")

    def test_an_unreadable_amount_is_an_invalid_row_that_is_excluded(self, work):
        analysis = work.analysis(acc=[work.acc([pos_acc("2026-07-26", "n/d"), pos_acc("2026-07-27", "-10.00", "b")])])
        invalid = pick(analysis.account, description="POS CARTA 00000000 a")
        assert invalid.klass == "invalid"
        assert outcome_of(invalid) == ("excluded", "invalid")
        assert outcome_of(pick(analysis.account, description="POS CARTA 00000000 b")) == ("standalone", "")

    def test_the_currency_defaults_to_eur_and_is_read_when_given(self, work):
        path = work.text("account-ccy.csv", [ACCOUNT_CSV_HEADER, "01/06/2026;01/06/2026;PAGAMENTO TRAMITE POS;POS A;'-1,00;", "02/06/2026;02/06/2026;PAGAMENTO TRAMITE POS;POS B;'-1,00;USD"])
        assert [row.currency for row in read_account(path).rows] == ["EUR", "USD"]

    def test_the_cells_keep_the_files_text(self, work):
        rows = read_account(work.acc([Acc("2026-06-01", "PAGAMENTO TRAMITE POS", "POS X", "-1234.50", "2026-06-03")])).rows
        (row,) = rows
        assert row.cells == {
            "Data Op.": "01/06/2026",
            "Data Val.": "03/06/2026",
            "Causale": "PAGAMENTO TRAMITE POS",
            "Descrizione": "POS X",
            "Importo": "'-1.234,50",
            "Divisa": "EUR",
        }


class TestTestata:
    @pytest.mark.parametrize("form", ["one_cell", "next_cell", "typed"])
    def test_the_testata_in_its_three_spellings(self, work, form):
        path = work.acc([pos_acc("2025-08-05", "-10.00")], "xlsx", opening="1000.00", closing="1500.00", date_from="2025-08-01", date_to="2025-12-31", form=form)
        testata = read_account(path).testata
        assert (testata.opening, testata.closing) == (Decimal("1000.00"), Decimal("1500.00"))
        assert (testata.date_from, testata.date_to) == (d("2025-08-01"), d("2025-12-31"))
        assert testata.currency == ("EUR" if form != "typed" else None)
        assert testata.has_balances
        assert testata.declared == (d("2025-08-01"), d("2025-12-31"))

    def test_thousands_separators_in_a_balance(self, work):
        path = work.acc([], "xlsx", opening="12345.60", closing="1000000.00", date_from="2025-08-01", date_to="2025-08-31", thousands=True)
        testata = read_account(path).testata
        assert (testata.opening, testata.closing) == (Decimal("12345.60"), Decimal("1000000.00"))

    def test_a_negative_balance(self, work):
        path = work.acc([], "xlsx", opening="-250.00", closing="40.00", date_from="2025-08-01", date_to="2025-08-31")
        assert read_account(path).testata.opening == Decimal("-250.00")

    def test_an_xlsx_without_a_testata_states_nothing(self, work):
        file = read_account(work.acc([pos_acc("2025-08-05", "-10.00")], "xlsx"))
        assert file.testata == Header()
        assert not file.testata.has_balances
        assert file.testata.declared is None
        assert file.chain_closes is None
        assert len(file.rows) == 1

    def test_a_partial_testata_has_no_balances(self, work):
        testata = read_account(work.acc([], "xlsx", opening="1000.00", date_from="2025-08-01", date_to="2025-08-31")).testata
        assert testata.opening == Decimal("1000.00")
        assert testata.closing is None
        assert not testata.has_balances

    def test_a_period_written_backwards_is_not_declared(self):
        assert Header(date_from=d("2025-09-01"), date_to=d("2025-08-01")).declared is None

    def test_a_csv_has_no_testata(self, work):
        file = read_account(work.acc([pos_acc("2025-08-05", "-10.00")]))
        assert file.testata == Header()
        assert file.chain_closes is None

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("25/07/02026", date(2026, 7, 25)),
            ("25/07/2026", date(2026, 7, 25)),
            ("Data Aggiornamento 25/07/02026", date(2026, 7, 25)),
            ("1/2/2026", date(2026, 2, 1)),
            ("31/02/2026", None),
            ("not a date", None),
            ("", None),
            (None, None),
            (date(2026, 7, 25), date(2026, 7, 25)),
            (datetime(2026, 7, 25, 10, 30), date(2026, 7, 25)),
        ],
    )
    def test_parse_testata_date(self, text, expected):
        assert parse_testata_date(text) == expected


class TestChainCloses:
    OPENING_ROWS = [salary_acc("2025-08-05", "500.00")]

    @pytest.mark.parametrize(
        ("closing", "expected"),
        [("1500.00", True), ("1500.01", True), ("1499.99", True), ("1500.02", False), ("1499.98", False), ("0.00", False)],
    )
    def test_the_chain_closes_to_the_cent(self, work, closing, expected):
        path = work.acc(self.OPENING_ROWS, "xlsx", opening="1000.00", closing=closing, date_from="2025-08-01", date_to="2025-08-31")
        assert read_account(path).chain_closes is expected

    def test_the_sum_is_over_every_row_of_the_file(self, work):
        rows = [salary_acc("2025-08-05", "500.00"), pos_acc("2025-08-06", "-120.40"), pos_acc("2025-08-07", "-79.60", "b")]
        path = work.acc(rows, "xlsx", opening="1000.00", closing="1300.00", date_from="2025-08-01", date_to="2025-08-31")
        assert read_account(path).chain_closes is True

    def test_an_unreadable_row_means_the_chain_is_not_checked(self, work):
        path = work.acc([*self.OPENING_ROWS, pos_acc("2025-08-06", "n/d")], "xlsx", opening="1000.00", closing="1500.00", date_from="2025-08-01", date_to="2025-08-31")
        assert read_account(path).chain_closes is None

    def test_a_zero_row_is_dropped_before_the_sum(self, work):
        path = work.acc([*self.OPENING_ROWS, pos_acc("2025-08-06", "0.00")], "xlsx", opening="1000.00", closing="1500.00", date_from="2025-08-01", date_to="2025-08-31")
        file = read_account(path)
        assert len(file.rows) == 1
        assert file.chain_closes is True

    def test_row_span(self, work):
        file = read_account(work.acc([salary_acc("2025-08-20", "1.00"), pos_acc("2025-08-05", "-1.00"), pos_acc("2025-08-12", "-1.00", "b")]))
        assert file.row_span == (d("2025-08-05"), d("2025-08-20"))
        assert read_account(work.acc([])).row_span is None


class TestAccountFingerprint:
    def _fingerprint(self, work, **options):
        return read_securities(work.sec([coupon_sec("2026-06-01", "187.50")], "xlsx", **options)).testata

    def test_it_is_a_sha256_hex_and_never_contains_the_numbers(self, work):
        testata = self._fingerprint(work)
        fingerprint = account_fingerprint(testata)
        assert fingerprint is not None
        assert re.fullmatch(r"[0-9a-f]{64}", fingerprint)
        assert testata.dossier not in fingerprint
        assert testata.support_account not in fingerprint

    def test_the_same_dossier_and_support_account_give_the_same_key(self, work):
        assert account_fingerprint(self._fingerprint(work)) == account_fingerprint(self._fingerprint(work, liquidity="1,00 EUR"))

    def test_another_dossier_gives_another_key(self, work):
        assert account_fingerprint(self._fingerprint(work)) != account_fingerprint(self._fingerprint(work, dossier="1234500099"))

    def test_another_support_account_gives_another_key(self, work):
        assert account_fingerprint(self._fingerprint(work)) != account_fingerprint(self._fingerprint(work, support="9876500099"))

    def test_a_testata_that_names_neither_gives_none(self, work):
        assert account_fingerprint(Header()) is None
        assert account_fingerprint(Header(opening=Decimal("1"), closing=Decimal("2"))) is None
        assert account_fingerprint(self._fingerprint(work, dossier="", support="")) is None


# =============================================================================
# B. ROLES
# =============================================================================


class TestDetectRole:
    @pytest.mark.parametrize("kind", ["csv", "xlsx"])
    def test_a_securities_export(self, work, kind):
        assert detect_role(work.sec([coupon_sec("2026-06-01", "187.50")], kind)) == ROLE_SECURITIES

    @pytest.mark.parametrize("kind", ["csv", "xlsx"])
    def test_an_account_export(self, work, kind):
        assert detect_role(work.acc([pos_acc("2026-06-01", "-1.00")], kind)) == ROLE_ACCOUNT

    def test_an_export_without_rows_still_has_its_role(self, work):
        assert detect_role(work.sec([])) == ROLE_SECURITIES
        assert detect_role(work.acc([], "xlsx", opening="1.00", closing="1.00", date_from="2025-08-01", date_to="2025-08-31")) == ROLE_ACCOUNT

    def test_an_unrelated_csv_has_no_role(self, work):
        assert detect_role(work.text("other.csv", ["Date;Description;Amount", "2026-06-01;Coffee;-1.20"])) is None

    def test_an_unreadable_file_has_no_role(self, work):
        broken = work.folder / "broken.xlsx"
        broken.write_bytes(b"this is not a zip archive")
        assert detect_role(broken) is None
        assert detect_role(work.folder / "missing.csv") is None

    def test_another_extension_has_no_role(self, work):
        text = work.sec([coupon_sec("2026-06-01", "187.50")]).read_text(encoding="utf-8-sig")
        for extension in ("txt", "pdf", "xls"):
            path = work.folder / f"securities.{extension}"
            path.write_text(text, encoding="utf-8")
            assert detect_role(path) is None

    def test_a_combined_file_is_not_an_original(self, work):
        combined = work.text("combined.csv", ["lf_row_kind;Data operazione;Nome;Causale;Quantità;Data Op.;Descrizione;Importo", "pair;01/06/2026;X;CEDOLA;1;01/06/2026;Y;1,00"])
        assert detect_role(combined) is None


# =============================================================================
# C. DESCRIBE A MEMBER
# =============================================================================


class TestDescribeMember:
    SECURITIES = [coupon_sec("2026-06-01", "10.00", value="2026-06-03"), coupon_sec("2026-06-20", "20.00", value="2026-06-24"), coupon_sec("2026-07-10", "30.00", value="2026-07-14")]

    def test_securities_csv(self, work):
        summary = describe_member(work.sec(self.SECURITIES))
        assert summary.role == ROLE_SECURITIES
        assert summary.rows == 3
        assert summary.coverage == [BRIMCoverage(axis="trade", start=d("2026-06-01"), end=d("2026-07-10")), BRIMCoverage(axis="value", start=d("2026-06-03"), end=d("2026-07-14"))]
        assert summary.account_fingerprint is None

    def test_securities_xlsx_has_a_fingerprint(self, work):
        summary = describe_member(work.sec(self.SECURITIES, "xlsx"))
        assert summary.rows == 3
        assert summary.account_fingerprint is not None
        assert re.fullmatch(r"[0-9a-f]{64}", summary.account_fingerprint)

    def test_the_fingerprint_is_the_one_of_the_testata(self, work):
        path = work.sec(self.SECURITIES, "xlsx")
        assert describe_member(path).account_fingerprint == account_fingerprint(read_securities(path).testata)

    def test_account_csv_has_the_axes_of_its_rows(self, work):
        rows = [pos_acc("2025-09-10", "-1.00"), Acc("2025-11-20", "PAGAMENTO TRAMITE POS", "POS B", "-2.00", "2025-11-24")]
        summary = describe_member(work.acc(rows))
        assert summary.role == ROLE_ACCOUNT
        assert summary.account_fingerprint is None
        assert summary.coverage == [BRIMCoverage(axis="trade", start=d("2025-09-10"), end=d("2025-11-20")), BRIMCoverage(axis="value", start=d("2025-09-10"), end=d("2025-11-24"))]

    def test_account_xlsx_adds_the_declared_period_when_it_differs_from_the_rows(self, work):
        rows = [pos_acc("2025-09-10", "-1.00"), pos_acc("2025-11-20", "-2.00", "b")]
        path = work.acc(rows, "xlsx", opening="1000.00", closing="997.00", date_from="2025-08-01", date_to="2025-12-31")
        summary = describe_member(path)
        assert summary.coverage == [
            BRIMCoverage(axis="trade", start=d("2025-09-10"), end=d("2025-11-20")),
            BRIMCoverage(axis="trade", start=d("2025-08-01"), end=d("2025-12-31")),
            BRIMCoverage(axis="value", start=d("2025-09-10"), end=d("2025-11-20")),
        ]
        assert summary.account_fingerprint is None

    def test_account_xlsx_with_a_declared_period_equal_to_its_rows_has_one_trade_entry(self, work):
        rows = [pos_acc("2025-09-10", "-1.00"), pos_acc("2025-09-20", "-2.00", "b")]
        path = work.acc(rows, "xlsx", opening="1000.00", closing="997.00", date_from="2025-09-10", date_to="2025-09-20")
        assert [c.axis for c in describe_member(path).coverage] == ["trade", "value"]

    def test_a_file_without_value_dates_has_no_value_axis(self, work):
        summary = describe_member(work.sec([coupon_sec("2026-06-01", "10.00", value="")]))
        assert [c.axis for c in summary.coverage] == ["trade"]

    def test_an_export_without_rows_has_no_coverage(self, work):
        summary = describe_member(work.sec([]))
        assert (summary.role, summary.rows, summary.coverage) == (ROLE_SECURITIES, 0, [])

    def test_an_unrelated_file_has_no_role(self, work):
        summary = describe_member(work.text("other.csv", ["A;B", "1;2"]))
        assert (summary.role, summary.rows, summary.coverage) == (None, 0, [])


# =============================================================================
# D. RULE M, THE CRÉDIT AGRICOLE POLICY
# =============================================================================


class TestRuleM:
    def test_the_csv_and_the_xlsx_of_one_export_count_once(self, work):
        rows = [coupon_sec("2026-06-01", "187.50"), buy_sec("2026-06-10", "5000.00"), redeem_sec("2026-06-15", "900.00")]
        analysis = work.analysis(sec=[work.sec(rows, "csv"), work.sec(rows, "xlsx")])
        assert sorted((row.op, row.name, row.causale, row.ctv) for row in analysis.securities) == sorted((d(r.op), r.name, r.causale, Decimal(r.ctv)) for r in rows)
        assert analysis.superseded == []
        assert analysis.mismatch == {ROLE_SECURITIES: [], ROLE_ACCOUNT: []}
        assert "overlap_mismatch" not in codes(analysis)

    def test_the_csv_and_the_xlsx_of_one_account_export_count_once(self, work):
        rows = [pos_acc("2025-09-10", "-10.00"), salary_acc("2025-09-12", "1500.00")]
        analysis = work.analysis(acc=[work.acc(rows, "csv"), work.acc(rows, "xlsx")])
        assert sorted(row.description for row in analysis.account) == sorted(r.desc for r in rows)
        assert analysis.superseded == []
        assert analysis.mismatch[ROLE_ACCOUNT] == []

    def _full_and_cut(self):
        """A full download (10-01..10-03, four rows on the 3rd) and one cut mid-day (only one of those four rows on the 3rd, then 4th and 5th)."""
        day3 = [pos_acc("2025-10-03", "-3.00", tag) for tag in ("g1", "g2", "g3", "g4")]
        full = [pos_acc("2025-10-01", "-1.00", "f1"), pos_acc("2025-10-01", "-1.10", "f2"), pos_acc("2025-10-02", "-2.00", "f3"), *day3]
        cut = [day3[0], pos_acc("2025-10-04", "-4.00", "h1"), pos_acc("2025-10-05", "-5.00", "h2")]
        return full, cut

    @pytest.mark.parametrize("cut_first", [False, True])
    def test_a_download_cut_mid_day_loses_that_day_without_a_mismatch(self, work, cut_first):
        full, cut = self._full_and_cut()
        paths = [work.acc(full), work.acc(cut)]
        analysis = work.analysis(acc=paths[::-1] if cut_first else paths)
        descriptions = sorted(row.description for row in analysis.account)
        assert descriptions == sorted(r.desc for r in [*full, cut[1], cut[2]])
        assert analysis.mismatch[ROLE_ACCOUNT] == []
        assert "overlap_mismatch" not in codes(analysis)
        (lost,) = analysis.superseded
        assert lost.description == "POS CARTA 00000000 g1"
        assert outcome_of(lost) == ("excluded", "superseded")
        assert lost.file_index == (2 if not cut_first else 1)

    def test_a_download_that_ends_on_the_cut_day_loses_it_too(self, work):
        day3 = [pos_acc("2025-10-03", "-3.00", tag) for tag in ("g1", "g2", "g3")]
        cut = [pos_acc("2025-10-01", "-1.00", "f1"), day3[0]]
        full = [*day3, pos_acc("2025-10-04", "-4.00", "h1"), pos_acc("2025-10-06", "-6.00", "h2")]
        analysis = work.analysis(acc=[work.acc(cut), work.acc(full)])
        assert sorted(row.description for row in analysis.account) == sorted(r.desc for r in [cut[0], *full])
        assert analysis.mismatch[ROLE_ACCOUNT] == []
        assert [outcome_of(row) for row in analysis.superseded] == [("excluded", "superseded")]

    def test_two_downloads_that_each_hold_a_row_the_other_lacks_are_a_mismatch(self, work):
        shared = pos_acc("2025-10-02", "-2.00", "x")
        first = [pos_acc("2025-10-01", "-1.00", "a1"), shared, pos_acc("2025-10-02", "-2.20", "only_first")]
        second = [shared, pos_acc("2025-10-02", "-2.30", "only_second"), pos_acc("2025-10-05", "-5.00", "z")]
        analysis = work.analysis(acc=[work.acc(first), work.acc(second)])
        assert analysis.mismatch[ROLE_ACCOUNT] == [d("2025-10-02")]
        assert analysis.mismatch[ROLE_SECURITIES] == []
        notice = notice_of(analysis, "overlap_mismatch")
        assert notice.severity == "warning"
        assert notice.context == {"role": ROLE_ACCOUNT, "days": 1, "first": "2025-10-02", "last": "2025-10-02"}
        # The file with the later end owns the tied day; the other one's rows of that day are not counted twice.
        assert {row.description for row in analysis.superseded} == {"POS CARTA 00000000 x", "POS CARTA 00000000 only_first"}
        assert {outcome_of(row) for row in analysis.superseded} == {("excluded", "superseded")}
        assert "POS CARTA 00000000 only_second" in {row.description for row in analysis.account}

    def test_the_same_for_securities(self, work):
        shared = coupon_sec("2026-06-02", "20.00", name=BOND_A)
        first = [coupon_sec("2026-06-01", "10.00"), shared, coupon_sec("2026-06-02", "21.00", name="ONLY FIRST BOND")]
        second = [shared, coupon_sec("2026-06-02", "22.00", name="ONLY SECOND BOND"), coupon_sec("2026-06-09", "90.00")]
        analysis = work.analysis(sec=[work.sec(first), work.sec(second)])
        assert analysis.mismatch[ROLE_SECURITIES] == [d("2026-06-02")]
        assert notice_of(analysis, "overlap_mismatch").context["role"] == ROLE_SECURITIES

    def test_multiplicity_inside_the_winning_file_is_kept(self, work):
        twice = [pos_acc("2025-10-02", "-9.00", "same"), pos_acc("2025-10-02", "-9.00", "same")]
        winner = [pos_acc("2025-10-01", "-1.00", "a"), *twice, pos_acc("2025-10-03", "-3.00", "c")]
        loser = [twice[0], pos_acc("2025-10-05", "-5.00", "e")]
        analysis = work.analysis(acc=[work.acc(winner), work.acc(loser)])
        assert [row.description for row in analysis.account].count("POS CARTA 00000000 same") == 2
        assert analysis.mismatch[ROLE_ACCOUNT] == []

    def test_the_same_two_rows_in_two_downloads_stay_two_not_four(self, work):
        twice = [pos_acc("2025-10-02", "-9.00", "same"), pos_acc("2025-10-02", "-9.00", "same")]
        analysis = work.analysis(acc=[work.acc(twice), work.acc(twice)])
        assert [row.description for row in analysis.account] == ["POS CARTA 00000000 same"] * 2
        assert analysis.superseded == []

    def test_an_older_securities_download_that_is_a_subset_of_the_bigger_one_adds_nothing(self, work):
        everything = [coupon_sec("2026-06-01", "10.00"), buy_sec("2026-06-20", "500.00"), redeem_sec("2026-07-10", "30.00"), matured_sec("2026-08-15", "40.00")]
        older = everything[:2]
        analysis = work.analysis(sec=[work.sec(older), work.sec(everything)])
        assert sorted(row.causale for row in analysis.securities) == sorted(r.causale for r in everything)
        assert analysis.superseded == []
        assert analysis.mismatch[ROLE_SECURITIES] == []

    def test_a_securities_download_cut_mid_day_loses_that_day(self, work):
        day = [coupon_sec("2026-06-05", f"{n}.00", name=f"BOND {n}") for n in (1, 2, 3, 4)]
        full = [coupon_sec("2026-06-01", "9.00", name="BOND 0"), *day]
        cut = [day[0], coupon_sec("2026-06-09", "8.00", name="BOND 9")]
        analysis = work.analysis(sec=[work.sec(full), work.sec(cut)])
        assert analysis.mismatch[ROLE_SECURITIES] == []
        assert [row.name for row in analysis.superseded] == ["BOND 1"]
        assert outcome_of(analysis.superseded[0]) == ("excluded", "superseded")
        assert sorted(row.name for row in analysis.securities) == sorted(["BOND 0", "BOND 1", "BOND 2", "BOND 3", "BOND 4", "BOND 9"])

    def test_the_two_roles_are_merged_apart(self, work):
        sec_rows = [coupon_sec("2026-06-01", "10.00")]
        acc_rows = [coupon_acc("2026-06-01", "10.00")]
        analysis = work.analysis(sec=[work.sec(sec_rows), work.sec(sec_rows)], acc=[work.acc(acc_rows)])
        assert len(analysis.securities) == 1
        assert len(analysis.account) == 1
        assert len(analysis.pairs) == 1

    def test_the_source_of_a_row_names_its_file_only_when_there_are_several(self, work):
        one = work.analysis(acc=[work.acc([pos_acc("2025-10-01", "-1.00")])])
        assert one.account[0].source == "account:2"
        two = work.analysis(acc=[work.acc([pos_acc("2025-10-01", "-1.00")]), work.acc([pos_acc("2025-10-09", "-1.00")])])
        assert sorted(row.source for row in two.account) == ["account#1:2", "account#2:2"]


# =============================================================================
# E. CLASSES
# =============================================================================


class TestClassesOfSecurities:
    @pytest.mark.parametrize(
        ("causale", "klass"),
        [
            ("CEDOLA", "coupon"),
            ("ACQ.CONT.SU MERC.", "buy"),
            ("SICAV: SOTTOSCR", "buy"),
            ("FONDI: RIMBORSO", "redeem"),
            ("TITOLI SCADUTI", "matured"),
            ("GIRO ALTRO DOSSIER", "transfer_in"),
            ("VERS.TITOLI", "transfer_in"),
            ("QUALCOSA DI NUOVO", "unknown"),
            ("", "unknown"),
        ],
    )
    def test_the_class_of_a_causale(self, causale, klass):
        assert classify_securities(sec_row(causale)) == klass

    def test_analysis_classifies_every_row_read(self, work):
        rows = [
            coupon_sec("2026-06-01", "1.00"),
            buy_sec("2026-06-02", "2.00"),
            fund_buy_sec("2026-06-03", "3.00"),
            redeem_sec("2026-06-04", "4.00"),
            matured_sec("2026-06-05", "5.00"),
            transfer_sec("2026-06-06", "T1", "10"),
            transfer_sec("2026-06-07", "T2", "10", causale="VERS.TITOLI"),
            Sec("2026-06-08", "ODD", "FOO BAR", "1", "6.00"),
        ]
        analysis = work.analysis(sec=[work.sec(rows)])
        assert {row.causale: row.klass for row in analysis.securities} == {
            "CEDOLA": "coupon",
            "ACQ.CONT.SU MERC.": "buy",
            "SICAV: SOTTOSCR": "buy",
            "FONDI: RIMBORSO": "redeem",
            "TITOLI SCADUTI": "matured",
            "GIRO ALTRO DOSSIER": "transfer_in",
            "VERS.TITOLI": "transfer_in",
            "FOO BAR": "unknown",
        }


COUPON_DESC = coupon_acc("2026-06-01", "1.00").desc
BUY_DESC = buy_acc("2026-06-01", "1.00").desc
SELL_DESC = f"NOTA INF. VEND. TIT:{BOND_B_ACC} DOSS:00000/00000000"
FUND_BUY_DESC = fund_buy_acc("2026-06-01", "1.00").desc
REDEEM_DESC = redeem_acc("2026-06-01", "1.00").desc
SALARY_TRANSFER_DESC = "ORD:IMPRESA DEMO SRL DT.ORD:000000 DESCR.OPERAZIONE SCT::STIPENDIO DI MAGGIO"
MATURITY_DESC = matured_acc("2026-06-01", "1.00").desc
DIVIDEND_ISIN = "IT0000000003"
DIVIDEND_DESC = f"DIVIDENDO AZIONE SAMPLE CORP {DIVIDEND_ISIN} DOS:00000/00000000 N.MOVIM: 1"


class TestClassesOfAccount:
    @pytest.mark.parametrize(
        ("causale", "description", "amount", "klass"),
        [
            (INCOME_CAUSALE, COUPON_DESC, "187.50", "coupon"),
            (INCOME_CAUSALE, "DIVIDENDO AZIONE SAMPLE", "12.00", "coupon"),
            (INCOME_CAUSALE, DIVIDEND_DESC, "95.40", "dividend"),  # the word DIVIDEND and an ISIN: a dividend, not a coupon
            (INCOME_CAUSALE, "DIVIDENDO CONGUAGLIO SENZA TITOLO IDENTIFICATO", "12.00", "coupon"),  # the keyword but no ISIN
            (INCOME_CAUSALE, DIVIDEND_DESC, "-95.40", "standalone"),  # a clawback is never a dividend
            (INCOME_CAUSALE, "STORNO CEDOLA ERRATA", "-50.00", "standalone"),
            (TRADE_CAUSALE, BUY_DESC, "-5000.00", "trade_buy"),
            (TRADE_CAUSALE, FUND_BUY_DESC, "-100.00", "trade_buy"),
            (TRADE_CAUSALE, SELL_DESC, "5000.00", "trade_sell"),
            (TRADE_CAUSALE, "OPERAZIONE SENZA PAROLA CHIAVE", "-5000.00", "trade_unknown"),
            (TRADE_CAUSALE, BUY_DESC, "5000.00", "trade_unknown"),  # the word says buy, the sign says money in
            (TRADE_CAUSALE, SELL_DESC, "-5000.00", "trade_unknown"),  # the word says sell, the sign says money out
            (SCT_CAUSALE, REDEEM_DESC, "900.00", "redemption"),
            (SCT_CAUSALE, SALARY_TRANSFER_DESC, "900.00", "standalone"),
            (SCT_CAUSALE, REDEEM_DESC, "-900.00", "standalone"),
            (MATURITY_CAUSALE, MATURITY_DESC, "30000.00", "maturity"),
            (MATURITY_CAUSALE, MATURITY_DESC, "-30000.00", "standalone"),
            ("PAGAMENTO TRAMITE POS", "POS CARTA 00000000", "-42.10", "standalone"),
            ("ACCREDITO EMOLUMENTI", "STIPENDIO", "2000.00", "standalone"),
            ("COMMISSIONI/SPESE", "SPESE DI GESTIONE", "-10.00", "standalone"),
            ("INTERESSI/COMPETENZE", "CANONE MENSILE", "-4.00", "standalone"),
            ("INTERESSI/COMPETENZE", "INTERESSI ATTIVI", "0.80", "standalone"),
            ("QUALCOSA DI NUOVO", "NON LO CONOSCO", "-1.00", "standalone"),
        ],
    )
    def test_the_class_of_a_row(self, causale, description, amount, klass):
        assert classify_account(acc_row("2026-06-01", amount, causale=causale, description=description))[0] == klass

    def test_an_unreadable_amount_is_invalid(self):
        assert classify_account(acc_row("2026-06-01", "?", causale=INCOME_CAUSALE, description=COUPON_DESC)) == ("invalid", "")

    @pytest.mark.parametrize(
        ("causale", "description", "amount", "tier"),
        [
            (INCOME_CAUSALE, COUPON_DESC, "187.50", classify_module.TIER_TYPED),
            ("COMMISSIONI/SPESE", "SPESE", "-10.00", classify_module.TIER_TYPED),
            (TRADE_CAUSALE, BUY_DESC, "-5000.00", classify_module.TIER_UNRESOLVED),
            (SCT_CAUSALE, REDEEM_DESC, "900.00", classify_module.TIER_UNRESOLVED),
            (SCT_CAUSALE, SALARY_TRANSFER_DESC, "900.00", classify_module.TIER_DECLARED_CASH),
            ("PAGAMENTO TRAMITE POS", "POS", "-1.00", classify_module.TIER_DECLARED_CASH),
            ("QUALCOSA DI NUOVO", "NON LO CONOSCO", "-1.00", classify_module.TIER_UNKNOWN),
        ],
    )
    def test_the_tier_of_a_row(self, causale, description, amount, tier):
        assert classify_account(acc_row("2026-06-01", amount, causale=causale, description=description))[1] == tier

    def test_an_unknown_causale_has_the_unknown_tier_through_the_analysis(self, work):
        rows = [Acc("2026-06-01", "QUALCOSA DI NUOVO", "NON LO CONOSCO", "-1.00"), pos_acc("2026-06-02", "-1.00")]
        analysis = work.analysis(acc=[work.acc(rows)])
        assert pick(analysis.account, causale="QUALCOSA DI NUOVO").tier == classify_module.TIER_UNKNOWN
        assert pick(analysis.account, causale="PAGAMENTO TRAMITE POS").tier == classify_module.TIER_DECLARED_CASH

    def test_superseded_rows_are_classified_too(self, work):
        full = [pos_acc("2025-10-01", "-1.00", "a"), pos_acc("2025-10-01", "-2.00", "b")]
        cut = [full[0], pos_acc("2025-10-09", "-9.00", "z")]
        analysis = work.analysis(acc=[work.acc(full), work.acc(cut)])
        (lost,) = analysis.superseded
        assert lost.klass == "standalone"
        assert lost.tier == classify_module.TIER_DECLARED_CASH


# =============================================================================
# F. PAIRING
# =============================================================================


class TestPairing:
    DAY = "2026-04-10"

    @pytest.mark.parametrize("kind", sorted(FACTORIES))
    def test_each_kind_of_fact_pairs_with_its_other_half(self, work, kind):
        make_sec, make_acc = FACTORIES[kind]
        result = pair(work, [make_sec(self.DAY, "250.00")], [make_acc(self.DAY, "250.00")])
        assert result.indexes() == {(0, 0)}
        assert result.ambiguous == []

    def test_a_fund_subscription_pairs_with_its_account_row(self, work):
        result = pair(work, [fund_buy_sec(self.DAY, "46870.00")], [fund_buy_acc(self.DAY, "46870.00")])
        assert result.indexes() == {(0, 0)}

    @pytest.mark.parametrize(("sec_kind", "acc_kind"), [(a, b) for a in sorted(FACTORIES) for b in sorted(FACTORIES) if a != b])
    def test_a_different_kind_of_fact_never_pairs_even_with_the_same_amount_and_value_date(self, work, sec_kind, acc_kind):
        result = pair(work, [FACTORIES[sec_kind][0](self.DAY, "250.00")], [FACTORIES[acc_kind][1](self.DAY, "250.00")])
        assert result.pairs == []
        assert result.ambiguous == []

    def test_an_account_dividend_never_pairs_with_a_securities_coupon(self, work):
        sec = Sec(self.DAY, BOND_A, "CEDOLA", "40000", "95.40")
        acc = Acc(self.DAY, INCOME_CAUSALE, DIVIDEND_DESC, "95.40")
        result = pair(work, [sec], [acc])
        assert result.account[0].klass == "dividend"
        assert result.pairs == []
        assert result.ambiguous == []

    def test_an_account_dividend_and_a_securities_coupon_are_left_as_they_are(self, work):
        account = work.acc([Acc("2025-08-10", INCOME_CAUSALE, DIVIDEND_DESC, "95.40"), pos_acc("2025-08-01", "-1.00"), pos_acc("2025-08-31", "-2.00", "b")])
        analysis = work.analysis(sec=[work.sec([Sec("2025-08-10", BOND_A, "CEDOLA", "40000", "95.40")])], acc=[account])
        assert analysis.pairs == []
        assert outcome_of(analysis.securities[0]) == ("excluded", "no_counterpart")
        assert outcome_of(pick(analysis.account, klass="dividend")) == ("standalone", "")

    def test_an_unpaired_account_dividend_is_standalone(self, work):
        analysis = work.analysis(acc=[work.acc([Acc("2025-08-10", INCOME_CAUSALE, DIVIDEND_DESC, "95.40")])])
        assert outcome_of(analysis.account[0]) == ("standalone", "")

    def test_a_cash_row_is_not_the_half_of_anything(self, work):
        result = pair(work, [coupon_sec(self.DAY, "250.00")], [pos_acc(self.DAY, "250.00")])
        assert result.pairs == []

    @pytest.mark.parametrize(
        ("sec_op", "acc_op", "value"),
        [
            ("2026-03-17", "2026-03-25", "2026-03-25"),  # an order on the 17th, debited on the 25th
            ("2026-03-27", "2026-03-25", "2026-03-29"),  # the account row two days BEFORE the securities row
            ("2026-03-25", "2026-03-25", "2026-03-25"),
            ("2026-03-01", "2026-03-31", "2026-04-02"),
        ],
    )
    def test_the_operation_dates_may_differ_in_either_direction(self, work, sec_op, acc_op, value):
        result = pair(work, [buy_sec(sec_op, "5000.00", value=value)], [buy_acc(acc_op, "5000.00", value=value)])
        assert result.indexes() == {(0, 0)}

    @pytest.mark.parametrize("acc_value", ["2026-03-24", "2026-03-26", "2026-04-25"])
    def test_a_value_date_that_differs_does_not_pair(self, work, acc_value):
        result = pair(work, [buy_sec("2026-03-25", "5000.00")], [buy_acc("2026-03-25", "5000.00", value=acc_value)])
        assert result.pairs == []
        assert result.ambiguous == []

    def test_a_missing_value_date_pairs_nothing(self, work):
        assert pair(work, [coupon_sec(self.DAY, "250.00", value="")], [coupon_acc(self.DAY, "250.00")]).pairs == []
        assert pair(work, [coupon_sec(self.DAY, "250.00")], [coupon_acc(self.DAY, "250.00", value="")]).pairs == []
        assert pair(work, [coupon_sec(self.DAY, "250.00", value="")], [coupon_acc(self.DAY, "250.00", value="")]).pairs == []

    @pytest.mark.parametrize("acc_amount", ["250.01", "249.99", "25.00", "2500.00"])
    def test_an_amount_that_differs_by_a_cent_does_not_pair(self, work, acc_amount):
        assert pair(work, [coupon_sec(self.DAY, "250.00")], [coupon_acc(self.DAY, acc_amount)]).pairs == []

    def test_a_different_currency_does_not_pair(self, work):
        assert pair(work, [coupon_sec(self.DAY, "250.00", currency="USD")], [coupon_acc(self.DAY, "250.00")]).pairs == []
        assert pair(work, [coupon_sec(self.DAY, "250.00", currency="USD")], [coupon_acc(self.DAY, "250.00", currency="USD")]).indexes() == {(0, 0)}

    def test_the_amount_is_compared_in_absolute_value(self, work):
        # The securities export may write a purchase negative or positive; the account always writes it negative.
        assert pair(work, [Sec(self.DAY, BOND_B, "ACQ.CONT.SU MERC.", "5000", "-5000.00")], [buy_acc(self.DAY, "5000.00")]).indexes() == {(0, 0)}

    def test_a_row_without_an_amount_pairs_nothing(self, work):
        assert pair(work, [Sec(self.DAY, BOND_B, "ACQ.CONT.SU MERC.", "5000", "")], [buy_acc(self.DAY, "5000.00")]).pairs == []
        assert pair(work, [buy_sec(self.DAY, "5000.00")], [Acc(self.DAY, TRADE_CAUSALE, BUY_DESC, "n/d")]).pairs == []

    def test_a_row_pairs_at_most_once(self, work):
        twins = [coupon_sec(self.DAY, "100.00"), coupon_sec(self.DAY, "100.00")]
        result = pair(work, twins, [coupon_acc(self.DAY, "100.00")])
        assert len(result.pairs) == 1
        assert result.ambiguous == []
        assert len({id(sec) for sec, _ in result.pairs}) == 1
        # The reverse: two identical account rows and one securities row.
        result = pair(work, [coupon_sec(self.DAY, "100.00")], [coupon_acc(self.DAY, "100.00"), coupon_acc(self.DAY, "100.00")])
        assert len(result.pairs) == 1
        assert result.ambiguous == []

    def test_interchangeable_twins_pair_without_ambiguity(self, work):
        result = pair(work, [coupon_sec(self.DAY, "100.00"), coupon_sec(self.DAY, "100.00")], [coupon_acc(self.DAY, "100.00"), coupon_acc(self.DAY, "100.00")])
        assert result.indexes() == {(0, 0), (1, 1)} or result.indexes() == {(0, 1), (1, 0)}
        assert len(result.pairs) == 2
        assert result.ambiguous == []

    def test_candidates_with_a_different_isin_and_no_compatible_name_are_all_left_out(self, work):
        accs = [coupon_acc(self.DAY, "100.00", name="ZZZ ALPHA 2030", isin=ISIN_A), coupon_acc(self.DAY, "100.00", name="ZZZ BETA 2031", isin=ISIN_B)]
        result = pair(work, [coupon_sec(self.DAY, "100.00")], accs)
        assert result.pairs == []
        assert len(result.ambiguous) == 3

    def test_two_candidates_with_the_same_name_but_a_different_isin_are_ambiguous(self, work):
        accs = [coupon_acc(self.DAY, "100.00", isin=ISIN_A), coupon_acc(self.DAY, "100.00", isin=ISIN_B)]
        result = pair(work, [coupon_sec(self.DAY, "100.00")], accs)
        assert result.pairs == []
        assert len(result.ambiguous) == 3

    def test_two_candidates_with_a_different_withholding_are_ambiguous(self, work):
        accs = [coupon_acc(self.DAY, "100.00", ritenuta="31,25"), coupon_acc(self.DAY, "100.00", ritenuta="10,00")]
        result = pair(work, [coupon_sec(self.DAY, "100.00")], accs)
        assert result.pairs == []
        assert len(result.ambiguous) == 3

    def test_candidates_with_a_different_name_and_no_compatible_one_are_ambiguous(self, work):
        accs = [buy_acc(self.DAY, "100.00", name="ALPHA BOND 2030"), buy_acc(self.DAY, "100.00", name="BETA BOND 2031")]
        result = pair(work, [buy_sec(self.DAY, "100.00", name="GAMMA BOND 2040 1%")], accs)
        assert result.pairs == []
        assert len(result.ambiguous) == 3

    def test_a_compatible_name_breaks_the_tie_and_the_other_row_stays_unpaired(self, work):
        accs = [buy_acc(self.DAY, "100.00", name="ALPHA BOND 2030"), buy_acc(self.DAY, "100.00", name="BETA BOND 2031")]
        for ordered in (accs, accs[::-1]):
            result = pair(work, [buy_sec(self.DAY, "100.00", name="ALPHA BOND 2030 1%")], ordered)
            (matched,) = result.pairs
            assert "ALPHA BOND 2030" in matched[1].description
            assert result.ambiguous == []

    def test_the_name_may_be_the_longer_one_or_the_shorter_one(self, work):
        accs = [buy_acc(self.DAY, "100.00", name="ALPHA BOND 2030 1% CUM"), buy_acc(self.DAY, "100.00", name="BETA BOND 2031")]
        result = pair(work, [buy_sec(self.DAY, "100.00", name="ALPHA BOND 2030")], accs)
        (matched,) = result.pairs
        assert "ALPHA" in matched[1].description

    def test_two_securities_rows_and_a_name_that_fits_one(self, work):
        secs = [coupon_sec(self.DAY, "100.00", name="ALPHA BOND 2030 1%"), coupon_sec(self.DAY, "100.00", name="BETA BOND 2031 2%")]
        result = pair(work, secs, [coupon_acc(self.DAY, "100.00", name="ALPHA BOND 2030", isin=ISIN_A)])
        assert result.indexes() == {(0, 0)}
        assert result.ambiguous == []

    def test_two_securities_rows_and_a_name_that_fits_none_are_ambiguous(self, work):
        secs = [coupon_sec(self.DAY, "100.00", name="ALPHA BOND 2030 1%"), coupon_sec(self.DAY, "100.00", name="BETA BOND 2031 2%")]
        result = pair(work, secs, [coupon_acc(self.DAY, "100.00", name="GAMMA BOND 2040", isin=ISIN_A)])
        assert result.pairs == []
        assert len(result.ambiguous) == 3

    def test_an_ambiguous_key_does_not_block_the_others(self, work):
        accs = [coupon_acc(self.DAY, "100.00", isin=ISIN_A), coupon_acc(self.DAY, "100.00", isin=ISIN_B), buy_acc(self.DAY, "7000.00")]
        result = pair(work, [coupon_sec(self.DAY, "100.00"), buy_sec(self.DAY, "7000.00")], accs)
        assert result.indexes() == {(1, 2)}
        assert len(result.ambiguous) == 3

    def test_up_to_eight_candidates_are_tried(self, work):
        result = pair(work, [coupon_sec(self.DAY, "100.00")], [coupon_acc(self.DAY, "100.00") for _ in range(8)])
        assert len(result.pairs) == 1
        assert result.ambiguous == []

    def test_over_eight_candidates_are_ambiguous(self, work):
        result = pair(work, [coupon_sec(self.DAY, "100.00")], [coupon_acc(self.DAY, "100.00") for _ in range(9)])
        assert result.pairs == []
        assert len(result.ambiguous) == 10
        result = pair(work, [coupon_sec(self.DAY, "100.00") for _ in range(9)], [coupon_acc(self.DAY, "100.00")])
        assert result.pairs == []
        assert len(result.ambiguous) == 10


class TestDatesAreNeverReplaced:
    """K: the value date only pairs the rows; the transaction keeps the operation date (decision of 28/10)."""

    def test_the_rows_keep_their_operation_date(self, work):
        sec = buy_sec("2026-03-17", "5000.00", value="2026-03-25")
        acc = buy_acc("2026-03-24", "5000.00", value="2026-03-25")
        analysis = work.analysis(sec=[work.sec([sec])], acc=[work.acc([acc])])
        ((paired_sec, paired_acc),) = analysis.pairs
        assert paired_sec.op == d("2026-03-17")
        assert paired_acc.op == d("2026-03-24")
        assert paired_sec.value == paired_acc.value == d("2026-03-25")
        assert paired_sec.op != paired_sec.value
        assert paired_acc.op != paired_acc.value
        assert paired_sec.cells["Data operazione"] == "17/03/2026"
        assert paired_acc.cells["Data Op."] == "24/03/2026"
        assert paired_sec.day == d("2026-03-17")

    def test_rule_m_and_the_coverage_run_on_the_operation_date(self, work):
        sec = work.sec([buy_sec("2026-03-17", "5000.00", value="2026-03-25")])
        summary = describe_member(sec)
        assert summary.coverage[0] == BRIMCoverage(axis="trade", start=d("2026-03-17"), end=d("2026-03-17"))
        assert summary.coverage[1] == BRIMCoverage(axis="value", start=d("2026-03-25"), end=d("2026-03-25"))
        assert work.analysis(sec=[sec]).segments() == [DateRangeModel(start=d("2026-03-17"), end=d("2026-03-17"))]


class TestOutcomes:
    """F: one outcome per row, and the reason when it is left out."""

    def test_a_pair_is_a_pair_on_both_sides(self, work):
        analysis = work.analysis(sec=[work.sec([coupon_sec("2025-08-10", "100.00")])], acc=[work.acc([coupon_acc("2025-08-10", "100.00")])])
        assert outcome_of(analysis.securities[0]) == ("pair", "")
        assert outcome_of(analysis.account[0]) == ("pair", "")

    def test_a_transfer_in_is_standalone_always(self, work):
        for acc in ([], [work.acc([pos_acc("2025-08-01", "-1.00")])]):
            analysis = work.analysis(sec=[work.sec([transfer_sec("2025-08-10", "T1", "100"), transfer_sec("2030-01-01", "T2", "100", causale="VERS.TITOLI")])], acc=acc)
            assert {outcome_of(row) for row in analysis.securities} == {("standalone", "")}

    def test_an_unknown_causale_is_excluded_as_unknown_type(self, work):
        analysis = work.analysis(sec=[work.sec([Sec("2025-08-10", "ODD", "FOO BAR", "1", "6.00")])], acc=[work.acc([pos_acc("2025-08-01", "-1.00")])])
        assert outcome_of(analysis.securities[0]) == ("excluded", "unknown_type")

    def test_without_an_account_export_an_unpaired_row_is_outside_the_cash_coverage(self, work):
        rows = [coupon_sec("2025-08-10", "1.00", name="C"), buy_sec("2025-08-10", "2.00", name="B"), redeem_sec("2025-08-10", "3.00", name="R"), matured_sec("2025-08-10", "4.00", name="M")]
        analysis = work.analysis(sec=[work.sec(rows)])
        assert {outcome_of(row) for row in analysis.securities} == {("excluded", "outside_cash_coverage")}

    def test_the_reason_follows_the_days_the_account_covers(self, work):
        # The account covers 2025-08-01 .. 2025-08-31 (its first and last row) and 2025-10-01 .. 2025-10-31.
        account = [work.acc([pos_acc("2025-08-01", "-1.00"), pos_acc("2025-08-31", "-2.00", "b")]), work.acc([pos_acc("2025-10-01", "-1.00", "c"), pos_acc("2025-10-31", "-2.00", "d")])]
        rows = {
            "BEFORE": coupon_sec("2025-07-10", "10.00", name="BEFORE"),
            "INSIDE": coupon_sec("2025-08-15", "11.00", name="INSIDE"),
            "IN THE HOLE": coupon_sec("2025-09-15", "12.00", name="IN THE HOLE"),
            "SECOND": coupon_sec("2025-10-15", "13.00", name="SECOND"),
            "AFTER": coupon_sec("2025-11-05", "14.00", name="AFTER"),
            "LAST DAY": coupon_sec("2025-10-31", "15.00", name="LAST DAY"),
        }
        analysis = work.analysis(sec=[work.sec(list(rows.values()))], acc=account)
        expected = {
            "BEFORE": "outside_cash_coverage",
            "INSIDE": "no_counterpart",
            "IN THE HOLE": "outside_cash_coverage",
            "SECOND": "no_counterpart",
            "AFTER": "not_yet_settled",
            "LAST DAY": "no_counterpart",
        }
        assert {name: outcome_of(pick(analysis.securities, name=name)) for name in rows} == {name: ("excluded", reason) for name, reason in expected.items()}

    def test_the_reason_reads_the_value_date_not_the_operation_date(self, work):
        account = work.acc([pos_acc("2025-08-01", "-1.00"), pos_acc("2025-08-31", "-2.00", "b")])
        sec = coupon_sec("2025-08-29", "10.00", value="2025-09-02")
        analysis = work.analysis(sec=[work.sec([sec])], acc=[account])
        assert outcome_of(analysis.securities[0]) == ("excluded", "not_yet_settled")

    def test_an_ambiguous_securities_row_says_so(self, work):
        accs = [coupon_acc("2025-08-10", "100.00", isin=ISIN_A), coupon_acc("2025-08-10", "100.00", isin=ISIN_B), pos_acc("2025-08-01", "-1.00")]
        analysis = work.analysis(sec=[work.sec([coupon_sec("2025-08-10", "100.00")])], acc=[work.acc(accs)])
        assert outcome_of(analysis.securities[0]) == ("excluded", "ambiguous")
        # An account row is cash the bank really moved: ambiguous, it is still imported (standalone).
        assert [outcome_of(row) for row in analysis.account if row.klass == "coupon"] == [("standalone", "ambiguous")] * 2
        assert analysis.pairs == []

    def test_the_account_rows_that_are_real_cash_stay_standalone_unpaired(self, work):
        rows = [
            coupon_acc("2025-08-10", "11.00"),
            redeem_acc("2025-08-11", "12.00"),
            matured_acc("2025-08-12", "13.00"),
            pos_acc("2025-08-13", "-14.00"),
            Acc("2025-08-14", "QUALCOSA DI NUOVO", "NON LO CONOSCO", "-15.00"),
        ]
        analysis = work.analysis(acc=[work.acc(rows)])
        assert [outcome_of(row) for row in analysis.account] == [("standalone", "")] * 5

    def test_an_unpaired_trade_on_the_account_is_still_cash_the_bank_moved(self, work):
        rows = [
            buy_acc("2025-08-10", "11.00"),
            Acc("2025-08-11", TRADE_CAUSALE, SELL_DESC, "12.00"),
            Acc("2025-08-12", TRADE_CAUSALE, "OPERAZIONE SENZA PAROLA CHIAVE", "-13.00"),
        ]
        analysis = work.analysis(acc=[work.acc(rows)])
        assert [row.klass for row in analysis.account] == ["trade_buy", "trade_sell", "trade_unknown"]
        assert [outcome_of(row) for row in analysis.account] == [("standalone", "no_counterpart")] * 3

    def test_the_counts_follow_the_outcomes(self, work):
        sec = [coupon_sec("2025-08-10", "100.00"), coupon_sec("2025-08-20", "50.00", name="LONELY BOND")]
        acc = [coupon_acc("2025-08-10", "100.00"), pos_acc("2025-08-01", "-1.00"), pos_acc("2025-08-31", "-1.00", "b")]
        counts = work.analysis(sec=[work.sec(sec)], acc=[work.acc(acc)]).counts()
        assert counts[("pair", "")] == 2
        assert counts[("standalone", "")] == 2
        assert counts[("excluded", "no_counterpart")] == 1


# =============================================================================
# G. BALANCES
# =============================================================================


def statement(day: str, amount: str, kind: str = "start") -> Statement:
    return Statement(as_of=d(day), amount=Decimal(amount), kind=kind, file_index=1, currency="EUR")


class TestExplainedByRows:
    START, END = statement("2025-06-30", "1000.00"), statement("2025-07-31", "1300.00", "end")

    def _explain(self, *rows: AccountRow):
        return explained_by_rows(self.START, self.END, list(rows))

    @pytest.mark.parametrize(
        ("rows_sum", "kind", "residual"),
        [
            ("300.00", "closed", "0.00"),
            ("299.99", "closed", "0.01"),
            ("300.01", "closed", "-0.01"),
            ("299.98", "broken", "0.02"),
            ("300.02", "broken", "-0.02"),
            ("100.00", "broken", "200.00"),
            ("-300.00", "broken", "600.00"),
        ],
    )
    def test_the_residual_and_its_kind(self, rows_sum, kind, residual):
        interval = self._explain(acc_row("2025-07-15", rows_sum))
        assert interval.kind == kind
        assert interval.residual == Decimal(residual)
        assert interval.rows == 1

    def test_several_rows_are_summed(self):
        interval = self._explain(acc_row("2025-07-10", "500.00"), acc_row("2025-07-20", "-250.00"), acc_row("2025-07-25", "50.00"))
        assert (interval.kind, interval.residual, interval.rows) == ("closed", Decimal("0.00"), 3)

    def test_no_row_at_all_is_a_hole(self):
        interval = self._explain()
        assert (interval.kind, interval.residual, interval.rows) == ("hole", Decimal("300.00"), 0)

    def test_no_row_and_nothing_to_explain_is_closed(self):
        interval = explained_by_rows(self.START, statement("2025-07-31", "1000.00", "end"), [])
        assert (interval.kind, interval.residual) == ("closed", Decimal("0.00"))

    def test_the_start_day_is_excluded(self):
        # A row dated on the start day is already in the opening balance.
        interval = self._explain(acc_row("2025-06-30", "300.00"))
        assert (interval.kind, interval.rows) == ("hole", 0)
        interval = self._explain(acc_row("2025-06-30", "999.00"), acc_row("2025-07-10", "300.00"))
        assert (interval.kind, interval.rows) == ("closed", 1)

    def test_the_end_day_is_included(self):
        interval = self._explain(acc_row("2025-07-31", "300.00"))
        assert (interval.kind, interval.rows) == ("closed", 1)

    def test_a_row_after_the_end_is_not_in_the_stretch(self):
        interval = self._explain(acc_row("2025-08-01", "300.00"))
        assert (interval.kind, interval.rows) == ("hole", 0)

    def test_a_row_before_the_start_is_not_in_the_stretch(self):
        interval = self._explain(acc_row("2025-06-29", "300.00"))
        assert (interval.kind, interval.rows) == ("hole", 0)

    def test_an_unreadable_row_inside_is_broken(self):
        interval = self._explain(acc_row("2025-07-10", "300.00"), acc_row("2025-07-12", "?"))
        assert interval.kind == "broken"

    def test_an_unreadable_row_inside_is_broken_even_when_the_rest_would_close(self):
        assert self._explain(acc_row("2025-07-12", "?")).kind == "broken"

    def test_an_unreadable_row_outside_is_ignored(self):
        assert self._explain(acc_row("2025-08-12", "?")).kind == "hole"

    def test_the_days_of_the_stretch(self):
        interval = self._explain()
        assert interval.days == DateRangeModel(start=d("2025-07-01"), end=d("2025-07-31"))

    def test_two_statements_of_one_day_that_disagree_are_not_a_hole(self):
        # An empty stretch of zero days cannot hide money: the disagreement is broken, never a correction.
        interval = explained_by_rows(statement("2025-07-31", "1000.00"), statement("2025-07-31", "1005.00", "end"), [])
        assert interval.kind == "broken"
        assert interval.residual == Decimal("5.00")


# The shared story of the scenarios (all numbers invented, deliberately tiny):
#   balance on 2025-06-30: 5000.00; July (unseen by file A and B): +1500.00 on the 10th, -200.00 on the 20th -> 6300.00 on 07-31;
#   August to December (file B): +1500, -400, -150, +1500, -20 -> 8730.00 on 12-31.
JULY_ROWS = [salary_acc("2025-07-10", "1500.00", "luglio"), pos_acc("2025-07-20", "-200.00", "luglio")]
B_ROWS = [
    salary_acc("2025-08-05", "1500.00", "agosto"),
    pos_acc("2025-09-12", "-400.00", "settembre"),
    pos_acc("2025-10-15", "-150.00", "ottobre"),
    salary_acc("2025-11-03", "1500.00", "novembre"),
    Acc("2025-12-10", "COMMISSIONI/SPESE", "SPESE DI GESTIONE DICEMBRE", "-20.00"),
]
A_ROWS = B_ROWS[2:]  # the bank cut the old rows: only October to December are left


def file_b(work: Work) -> Path:
    return work.acc(B_ROWS, "xlsx", opening="6300.00", closing="8730.00", date_from="2025-08-01", date_to="2025-12-31")


def file_a(work: Work) -> Path:
    return work.acc(A_ROWS, "xlsx", opening="5000.00", closing="8730.00", date_from="2025-07-01", date_to="2025-12-31")


class TestBalanceScenarios:
    def test_1_one_file_whose_chain_closes(self, work):
        rows = [salary_acc("2025-08-05", "2000.00"), pos_acc("2025-09-10", "-300.00"), Acc("2025-11-20", "COMMISSIONI/SPESE", "SPESE", "-25.50")]
        path = work.acc(rows, "xlsx", opening="1000.00", closing="2674.50", date_from="2025-08-01", date_to="2025-12-31")
        assert read_account(path).chain_closes is True
        analysis = work.analysis(acc=[path])
        assert [(s.kind, s.as_of, s.amount) for s in analysis.statements] == [("start", d("2025-07-31"), Decimal("1000.00")), ("end", d("2025-12-31"), Decimal("2674.50"))]
        assert [i.kind for i in analysis.intervals] == ["closed"]
        (checkpoint,) = analysis.checkpoints
        assert checkpoint.kind == "opening"
        assert (checkpoint.cash.as_of, checkpoint.cash.stated, checkpoint.cash.amount, checkpoint.cash.in_flight) == (d("2025-07-31"), Decimal("1000.00"), Decimal("1000.00"), Decimal("0"))
        assert checkpoint.cash.currency == "EUR"
        assert checkpoint.cash.source == "account#1:start"
        (verification,) = analysis.verifications
        assert (verification.kind, verification.as_of, verification.stated) == ("verification", d("2025-12-31"), Decimal("2674.50"))
        assert analysis.holes == []
        assert analysis.gaps() == []
        assert analysis.set_notices() == []

    def test_2_the_real_world_shape_has_one_hole(self, work):
        for a_first in (True, False):
            paths = [file_a(work), file_b(work)]
            analysis = work.analysis(acc=paths if a_first else paths[::-1])
            a_index = 1 if a_first else 2
            assert read_account(paths[0]).chain_closes is False  # A: rows are missing against its balances
            assert read_account(paths[1]).chain_closes is True
            opening = analysis.opening_statement
            assert (opening.as_of, opening.amount, opening.kind, opening.file_index) == (d("2025-06-30"), Decimal("5000.00"), "start", a_index)
            (hole,) = analysis.holes
            assert hole.kind == "hole"
            assert hole.days == DateRangeModel(start=d("2025-07-01"), end=d("2025-07-31"))
            assert hole.residual == Decimal("1300.00")
            assert [c.kind for c in analysis.checkpoints] == ["opening", "gap"]
            opening_cp, gap_cp = analysis.checkpoints
            assert (opening_cp.cash.as_of, opening_cp.cash.stated) == (d("2025-06-30"), Decimal("5000.00"))
            assert (gap_cp.cash.as_of, gap_cp.cash.stated, gap_cp.cash.kind) == (d("2025-07-31"), Decimal("6300.00"), "gap")
            assert analysis.gaps() == [DateRangeModel(start=d("2025-07-01"), end=d("2025-07-31"))]
            notice = notice_of(analysis, "account_gap")
            assert notice.severity == "warning"
            assert notice.context == {"start": "2025-07-01", "end": "2025-07-31", "amount": "1300.00", "corrected": True}
            assert "balance_chain_broken" not in codes(analysis)
            # B's rows are in the set once, A's identical rows are not counted twice.
            assert sorted(row.description for row in analysis.account) == sorted(r.desc for r in B_ROWS)
            assert analysis.superseded == []
            # Both files state the same closing balance on the last day: one verification, no conflict.
            assert [(v.kind, v.as_of) for v in analysis.verifications] == [("verification", d("2025-12-31"))]
            assert analysis.conflicting_days == []

    def test_2_the_days_the_account_covers(self, work):
        analysis = work.analysis(acc=[file_a(work), file_b(work)])
        assert analysis.cash_spans == [(d("2025-08-01"), d("2025-12-31"))]  # B declares its whole period; A adds nothing outside it

    def test_3_the_rows_of_the_missing_month_make_the_hole_disappear(self, work):
        july = work.acc(JULY_ROWS)
        analysis = work.analysis(acc=[file_a(work), file_b(work), july])
        assert [i.kind for i in analysis.intervals] == ["closed", "closed"]
        assert analysis.opening_statement.as_of == d("2025-06-30")
        assert analysis.holes == []
        assert analysis.gaps() == []
        assert [c.kind for c in analysis.checkpoints] == ["opening"]
        assert "account_gap" not in codes(analysis)
        assert "balance_chain_broken" not in codes(analysis)
        assert analysis.zone(d("2025-07-15")) == ZONE_WINDOW

    def test_3_the_missing_month_in_an_xlsx_without_balances_does_the_same(self, work):
        analysis = work.analysis(acc=[file_a(work), file_b(work), work.acc(JULY_ROWS, "xlsx")])
        assert analysis.holes == []
        assert "account_gap" not in codes(analysis)

    def test_4_a_file_that_does_not_add_up_is_only_a_verification(self, work):
        analysis = work.analysis(acc=[file_a(work)])
        (interval,) = analysis.intervals
        assert interval.kind == "broken"
        assert interval.residual == Decimal("2400.00")
        assert analysis.opening_statement is None
        assert analysis.checkpoints == []
        assert analysis.holes == []
        assert analysis.gaps() == []
        assert [(v.kind, v.as_of) for v in analysis.verifications] == [("verification", d("2025-06-30")), ("verification", d("2025-12-31"))]
        assert list(codes(analysis)) == ["balance_chain_broken"]
        assert notice_of(analysis, "balance_chain_broken").context == {"date": "2025-12-31"}
        assert notice_of(analysis, "balance_chain_broken").severity == "warning"
        # It covers only the days of its rows.
        assert analysis.cash_spans == [(d("2025-10-15"), d("2025-12-10"))]

    def test_5_a_set_of_csv_files_states_no_balance_but_still_pairs(self, work):
        analysis = work.analysis(sec=[work.sec([coupon_sec("2025-08-10", "100.00")])], acc=[work.acc([coupon_acc("2025-08-10", "100.00")])])
        assert analysis.statements == []
        assert analysis.checkpoints == []
        assert analysis.verifications == []
        assert analysis.opening_statement is None
        assert codes(analysis) == ["no_balance"]
        notice = notice_of(analysis, "no_balance")
        assert (notice.severity, notice.context) == ("info", None)
        assert len(analysis.pairs) == 1
        assert analysis.zone(d("2025-08-10")) == ""
        assert analysis.securities[0].outcome.zone == ""

    def test_6_a_broken_interval_after_a_good_opening_keeps_the_opening_and_the_gaps(self, work):
        f1 = work.acc([salary_acc("2025-07-05", "800.00"), pos_acc("2025-07-20", "-300.00")], "xlsx", opening="1000.00", closing="1500.00", date_from="2025-07-01", date_to="2025-07-31")
        f2 = work.acc([salary_acc("2025-09-05", "500.00"), pos_acc("2025-09-18", "-200.00")], "xlsx", opening="2200.00", closing="2500.00", date_from="2025-09-01", date_to="2025-09-30")
        f3 = work.acc([salary_acc("2025-10-08", "300.00"), pos_acc("2025-10-22", "-200.00")], "xlsx", opening="2500.00", closing="2900.00", date_from="2025-10-01", date_to="2025-10-31")
        analysis = work.analysis(acc=[f1, f2, f3])
        assert [i.kind for i in analysis.intervals] == ["closed", "hole", "closed", "broken"]
        assert analysis.opening_statement.as_of == d("2025-06-30")
        # The earlier gap is kept, with its correction point; the broken stretch adds a notice and no correction.
        assert [c.kind for c in analysis.checkpoints] == ["opening", "gap"]
        assert analysis.checkpoints[1].cash.as_of == d("2025-08-31")
        assert analysis.checkpoints[1].cash.stated == Decimal("2200.00")
        assert analysis.gaps() == [DateRangeModel(start=d("2025-08-01"), end=d("2025-08-31"))]
        assert sorted(codes(analysis)) == ["account_gap", "balance_chain_broken"]
        assert notice_of(analysis, "balance_chain_broken").context == {"date": "2025-10-31"}
        assert notice_of(analysis, "account_gap").context["amount"] == "700.00"
        assert notice_of(analysis, "account_gap").context["corrected"] is True  # a hole BEFORE a later broken interval keeps its correction
        # The balances of the broken stretch are compared, never used.
        assert [v.as_of for v in analysis.verifications] == [d("2025-07-31"), d("2025-09-30"), d("2025-10-31")]
        assert {v.kind for v in analysis.verifications} == {"verification"}

    def test_two_statements_of_one_day_that_disagree_are_reported(self, work):
        f1 = work.acc([salary_acc("2025-07-05", "500.00")], "xlsx", opening="1000.00", closing="1500.00", date_from="2025-07-01", date_to="2025-07-31")
        f2 = work.acc([salary_acc("2025-08-05", "200.00")], "xlsx", opening="1600.00", closing="1800.00", date_from="2025-08-01", date_to="2025-08-31")
        analysis = work.analysis(acc=[f1, f2])
        assert analysis.conflicting_days == [d("2025-07-31")]
        assert "balance_chain_broken" in codes(analysis)

    def test_a_statement_is_the_eve_of_the_first_day_and_the_last_day(self, work):
        path = work.acc([], "xlsx", opening="1.00", closing="1.00", date_from="2025-08-01", date_to="2025-08-31")
        analysis = work.analysis(acc=[path])
        assert [(s.kind, s.as_of) for s in analysis.statements] == [("start", d("2025-07-31")), ("end", d("2025-08-31"))]

    def test_a_file_without_all_four_header_fields_gives_no_statement(self, work):
        for options in ({"opening": "1.00", "closing": "1.00", "date_from": "2025-08-01"}, {"opening": "1.00", "date_from": "2025-08-01", "date_to": "2025-08-31"}, {}):
            analysis = work.analysis(acc=[work.acc([pos_acc("2025-08-05", "-1.00")], "xlsx", **options)])
            assert analysis.statements == []
            assert "no_balance" in codes(analysis)

    def test_the_liquidity_of_the_securities_header_is_a_verification_inside_the_covered_days(self, work):
        account = work.acc([salary_acc("2026-07-01", "1.00"), pos_acc("2026-07-31", "-1.00")])
        securities = work.sec([coupon_sec("2026-07-10", "5.00")], "xlsx", liquidity="7.250,00 EUR", updated="25/07/02026")
        analysis = work.analysis(sec=[securities], acc=[account])
        (verification,) = analysis.verifications
        assert (verification.as_of, verification.stated, verification.source) == (d("2026-07-25"), Decimal("7250.00"), "securities:liquidity")

    def test_the_liquidity_outside_the_covered_days_is_not_used(self, work):
        account = work.acc([salary_acc("2026-07-01", "1.00"), pos_acc("2026-07-20", "-1.00")])
        securities = work.sec([coupon_sec("2026-07-10", "5.00")], "xlsx", liquidity="7.250,00 EUR", updated="25/07/02026")
        assert work.analysis(sec=[securities], acc=[account]).verifications == []


# =============================================================================
# H. IN-FLIGHT CASH
# =============================================================================


class TestInFlight:
    def test_an_order_recorded_before_the_bank_books_it(self, work):
        analysis = work.analysis(sec=[work.sec([buy_sec("2025-09-17", "5000.00", value="2025-09-25")])], acc=[work.acc([buy_acc("2025-09-25", "5000.00")])])
        assert len(analysis.pairs) == 1
        expected = {"2025-09-16": "0", "2025-09-17": "-5000.00", "2025-09-20": "-5000.00", "2025-09-24": "-5000.00", "2025-09-25": "0", "2025-09-30": "0"}
        assert {day: analysis.in_flight(d(day)) for day in expected} == {day: Decimal(amount) for day, amount in expected.items()}

    def test_the_bank_books_it_before_the_securities_row(self, work):
        analysis = work.analysis(sec=[work.sec([buy_sec("2025-09-25", "5000.00", value="2025-09-26")])], acc=[work.acc([buy_acc("2025-09-23", "5000.00", value="2025-09-26")])])
        assert len(analysis.pairs) == 1
        expected = {"2025-09-22": "0", "2025-09-23": "5000.00", "2025-09-24": "5000.00", "2025-09-25": "0", "2025-09-30": "0"}
        assert {day: analysis.in_flight(d(day)) for day in expected} == {day: Decimal(amount) for day, amount in expected.items()}

    def test_an_unpaired_row_is_never_in_flight(self, work):
        analysis = work.analysis(sec=[work.sec([buy_sec("2025-09-17", "5000.00", value="2025-09-25")])], acc=[work.acc([buy_acc("2025-09-26", "5000.00")])])
        assert analysis.pairs == []
        assert analysis.in_flight(d("2025-09-20")) == Decimal("0")

    def test_the_opening_balance_between_the_two_dates(self, work):
        # Order on the 17th (value 25th), debited on the 25th; the statement is dated the 20th.
        account = work.acc([buy_acc("2025-09-25", "5000.00"), salary_acc("2025-09-26", "4000.00")], "xlsx", opening="3000.00", closing="2000.00", date_from="2025-09-21", date_to="2025-09-30")
        analysis = work.analysis(sec=[work.sec([buy_sec("2025-09-17", "5000.00", value="2025-09-25")])], acc=[account])
        (opening,) = [c for c in analysis.checkpoints if c.kind == "opening"]
        assert opening.cash.as_of == d("2025-09-20")
        assert opening.cash.stated == Decimal("3000.00")
        assert opening.cash.in_flight == Decimal("-5000.00")
        assert opening.cash.amount == Decimal("-2000.00")  # stated + in_flight: the ledger already spent it
        (verification,) = analysis.verifications
        assert (verification.as_of, verification.in_flight, verification.amount) == (d("2025-09-30"), Decimal("0"), Decimal("2000.00"))

    def test_the_opening_balance_when_the_bank_booked_first(self, work):
        # Debited on the 23rd, recorded on the 25th; the statement is dated the 24th.
        account = work.acc([salary_acc("2025-09-28", "100.00")], "xlsx", opening="8000.00", closing="8100.00", date_from="2025-09-25", date_to="2025-09-30")
        bank_first = work.acc([buy_acc("2025-09-23", "5000.00", value="2025-09-26")])
        sec = work.sec([buy_sec("2025-09-25", "5000.00", value="2025-09-26")])
        analysis = work.analysis(sec=[sec], acc=[account, bank_first])
        (opening,) = [c for c in analysis.checkpoints if c.kind == "opening"]
        assert opening.cash.as_of == d("2025-09-24")
        assert opening.cash.in_flight == Decimal("5000.00")
        assert opening.cash.amount == Decimal("13000.00")

    def test_a_verification_between_the_two_dates(self, work):
        first = work.acc([salary_acc("2025-09-10", "1000.00")], "xlsx", opening="7000.00", closing="8000.00", date_from="2025-09-01", date_to="2025-09-20")
        debit = work.acc([buy_acc("2025-09-25", "5000.00")])
        analysis = work.analysis(sec=[work.sec([buy_sec("2025-09-17", "5000.00", value="2025-09-25")])], acc=[first, debit])
        (verification,) = [v for v in analysis.verifications if v.as_of == d("2025-09-20")]
        assert (verification.stated, verification.in_flight, verification.amount) == (Decimal("8000.00"), Decimal("-5000.00"), Decimal("3000.00"))
        (opening,) = [c for c in analysis.checkpoints if c.kind == "opening"]
        assert opening.cash.in_flight == Decimal("0")

    def test_a_verification_when_the_bank_booked_first(self, work):
        first = work.acc([salary_acc("2025-09-10", "1000.00"), buy_acc("2025-09-23", "5000.00", value="2025-09-26")], "xlsx", opening="7000.00", closing="3000.00", date_from="2025-09-01", date_to="2025-09-24")
        analysis = work.analysis(sec=[work.sec([buy_sec("2025-09-25", "5000.00", value="2025-09-26")])], acc=[first])
        assert len(analysis.pairs) == 1
        (verification,) = [v for v in analysis.verifications if v.as_of == d("2025-09-24")]
        assert (verification.stated, verification.in_flight, verification.amount) == (Decimal("3000.00"), Decimal("5000.00"), Decimal("8000.00"))


# =============================================================================
# I. OPENING POSITIONS
# =============================================================================


class TestOpeningPositions:
    ACCOUNT = staticmethod(lambda work: work.acc([salary_acc("2025-08-05", "100.00")], "xlsx", opening="1000.00", closing="1100.00", date_from="2025-08-01", date_to="2025-08-31"))

    def test_the_transfers_up_to_the_opening_give_one_position_per_title(self, work):
        rows = [
            transfer_sec("2025-07-15", "BTP SAMPLE 1/12/2026 1.25%", "1000"),
            transfer_sec("2025-07-31", "btp  sample 1/12/2026 1.25%", "500", causale="VERS.TITOLI"),
            transfer_sec("2025-07-16", "SAMPLE GLOB EQ FUND", "-20"),
        ]
        analysis = work.analysis(sec=[work.sec(rows)], acc=[self.ACCOUNT(work)])
        (opening,) = analysis.checkpoints
        positions = {position.name.lower().replace("  ", " "): position for position in opening.positions}
        assert set(positions) == {"btp sample 1/12/2026 1.25%", "sample glob eq fund"}
        bond = positions["btp sample 1/12/2026 1.25%"]
        assert bond.quantity == Decimal("1500")
        assert bond.proof == "exact:transfer_in"
        assert bond.as_of == d("2025-07-31")
        assert len(bond.rows) == 2
        fund = positions["sample glob eq fund"]
        assert fund.quantity == Decimal("20")  # the sum of the absolute quantities

    def test_a_transfer_after_the_opening_gives_no_position(self, work):
        rows = [transfer_sec("2025-08-01", "BTP SAMPLE 1/12/2026 1.25%", "1000"), transfer_sec("2025-09-10", "OTHER BOND", "5")]
        analysis = work.analysis(sec=[work.sec(rows)], acc=[self.ACCOUNT(work)])
        (opening,) = analysis.checkpoints
        assert opening.positions == []
        assert {outcome_of(row) for row in analysis.securities} == {("standalone", "")}

    def test_only_a_transfer_gives_a_position(self, work):
        rows = [coupon_sec("2025-07-15", "10.00"), buy_sec("2025-07-16", "20.00")]
        analysis = work.analysis(sec=[work.sec(rows)], acc=[self.ACCOUNT(work)])
        assert analysis.checkpoints[0].positions == []

    def test_without_an_opening_there_is_no_checkpoint_at_all(self, work):
        analysis = work.analysis(sec=[work.sec([transfer_sec("2025-07-15", "BTP SAMPLE 1/12/2026 1.25%", "1000")])], acc=[work.acc([pos_acc("2025-08-05", "-1.00")])])
        assert analysis.checkpoints == []
        assert work.analysis(sec=[work.sec([transfer_sec("2025-07-15", "BTP SAMPLE 1/12/2026 1.25%", "1000")])]).checkpoints == []

    def test_a_gap_checkpoint_carries_no_position(self, work):
        analysis = work.analysis(sec=[work.sec([transfer_sec("2025-06-01", "BTP SAMPLE 1/12/2026 1.25%", "1000")])], acc=[file_a(work), file_b(work)])
        opening, gap = analysis.checkpoints
        assert [p.quantity for p in opening.positions] == [Decimal("1000")]
        assert gap.positions == []


# =============================================================================
# J. ZONES
# =============================================================================


class TestZones:
    @pytest.mark.parametrize(
        ("day", "zone"),
        [
            ("2025-06-01", ZONE_BEFORE),
            ("2025-06-29", ZONE_BEFORE),
            ("2025-06-30", ZONE_BEFORE),  # the opening day itself is still "before"
            ("2025-07-01", ZONE_GAP),
            ("2025-07-15", ZONE_GAP),
            ("2025-07-31", ZONE_GAP),  # the last day of the hole
            ("2025-08-01", ZONE_WINDOW),
            ("2025-12-31", ZONE_WINDOW),
            ("2026-03-01", ZONE_WINDOW),
        ],
    )
    def test_the_zone_of_a_day(self, work, day, zone):
        analysis = work.analysis(acc=[file_a(work), file_b(work)])
        assert analysis.zone(d(day)) == zone

    def test_a_day_without_a_date_has_no_zone(self, work):
        analysis = work.analysis(acc=[file_a(work), file_b(work)])
        assert analysis.zone(None) == ""

    def test_without_an_opening_the_zone_is_empty(self, work):
        for acc in ([], [work.acc([pos_acc("2025-08-05", "-1.00")])], [file_a(work)]):
            assert work.analysis(acc=acc).zone(d("2025-08-05")) == ""

    def test_without_a_hole_every_day_after_the_opening_is_a_window(self, work):
        path = work.acc([salary_acc("2025-08-05", "100.00")], "xlsx", opening="1000.00", closing="1100.00", date_from="2025-08-01", date_to="2025-08-31")
        analysis = work.analysis(acc=[path])
        assert [analysis.zone(d(day)) for day in ("2025-07-31", "2025-08-01", "2025-09-15")] == [ZONE_BEFORE, ZONE_WINDOW, ZONE_WINDOW]

    def test_rows_carry_the_zone_of_their_account_date(self, work):
        account = work.acc([salary_acc("2025-08-05", "100.00"), buy_acc("2025-08-10", "50.00")], "xlsx", opening="1000.00", closing="1050.00", date_from="2025-08-01", date_to="2025-08-31")
        sec = work.sec([buy_sec("2025-08-10", "50.00"), transfer_sec("2025-07-15", "T1", "10")])
        analysis = work.analysis(sec=[sec], acc=[account])
        assert pick(analysis.securities, causale="ACQ.CONT.SU MERC.").outcome.zone == ZONE_WINDOW
        assert pick(analysis.securities, causale="GIRO ALTRO DOSSIER").outcome.zone == ZONE_BEFORE
        assert pick(analysis.account, causale="ACCREDITO EMOLUMENTI").outcome.zone == ZONE_WINDOW
        assert pick(analysis.account, causale=TRADE_CAUSALE).outcome.zone == ZONE_WINDOW


# =============================================================================
# L. THE SHAPE OF A SET
# =============================================================================


class TestDescribeSet:
    def test_the_segments_are_the_merged_securities_coverage(self, work):
        august = work.sec([coupon_sec("2025-08-01", "1.00"), coupon_sec("2025-08-31", "1.00", name="B")])
        september = work.sec([coupon_sec("2025-09-01", "1.00", name="C"), coupon_sec("2025-09-30", "1.00", name="D")])
        november = work.sec([coupon_sec("2025-11-05", "1.00", name="E"), coupon_sec("2025-11-20", "1.00", name="F")])
        shape = describe_set({ROLE_SECURITIES: [august, september, november]})
        assert [(s.start, s.end) for s in shape.segments] == [(d("2025-08-01"), d("2025-09-30")), (d("2025-11-05"), d("2025-11-20"))]
        assert shape.gaps == []

    def test_the_gaps_are_the_holes(self, work):
        shape = describe_set({ROLE_ACCOUNT: [file_a(work), file_b(work)]})
        assert [(g.start, g.end) for g in shape.gaps] == [(d("2025-07-01"), d("2025-07-31"))]
        assert [n.code for n in shape.notices] == ["account_gap"]
        assert shape.segments == []

    def test_a_clean_set_has_no_notice(self, work):
        path = work.acc([salary_acc("2025-08-05", "100.00"), coupon_acc("2025-08-10", "1.00")], "xlsx", opening="1000.00", closing="1101.00", date_from="2025-08-01", date_to="2025-08-31")
        shape = describe_set({ROLE_ACCOUNT: [path], ROLE_SECURITIES: [work.sec([coupon_sec("2025-08-10", "1.00")])]})
        assert shape.notices == []
        assert shape.gaps == []

    def test_an_export_without_rows_is_an_empty_member(self, work):
        shape = describe_set({ROLE_SECURITIES: [work.sec([]), work.sec([coupon_sec("2025-08-10", "1.00")])]})
        (notice,) = [n for n in shape.notices if n.code == "empty_member"]
        assert (notice.severity, notice.context) == ("warning", {"role": ROLE_SECURITIES, "file": 1})

    def test_an_account_file_without_the_header_is_an_empty_member(self, work):
        shape = describe_set({ROLE_ACCOUNT: [work.text("not-an-account.csv", ["A;B", "1;2"])]})
        (notice,) = [n for n in shape.notices if n.code == "empty_member"]
        assert notice.context == {"role": ROLE_ACCOUNT, "file": 1}

    def test_a_mismatch_between_two_downloads(self, work):
        first = work.acc([pos_acc("2025-10-01", "-1.00", "a"), pos_acc("2025-10-02", "-2.00", "only_first")])
        second = work.acc([pos_acc("2025-10-02", "-2.30", "only_second"), pos_acc("2025-10-05", "-5.00", "z")])
        shape = describe_set({ROLE_ACCOUNT: [first, second]})
        assert "overlap_mismatch" in [n.code for n in shape.notices]

    def test_a_broken_chain(self, work):
        shape = describe_set({ROLE_ACCOUNT: [file_a(work)]})
        assert [n.code for n in shape.notices] == ["balance_chain_broken"]

    def test_csv_only_account_files_say_no_balance(self, work):
        shape = describe_set({ROLE_ACCOUNT: [work.acc([pos_acc("2025-08-05", "-1.00")])]})
        (notice,) = shape.notices
        assert (notice.code, notice.severity) == ("no_balance", "info")

    def test_a_set_without_an_account_says_nothing_about_balances(self, work):
        shape = describe_set({ROLE_SECURITIES: [work.sec([coupon_sec("2025-08-10", "1.00")])]})
        assert shape.notices == []

    def test_an_empty_set(self):
        shape = describe_set({})
        assert (shape.segments, shape.gaps, shape.notices) == ([], [], [])


# =============================================================================
# N. THE MONEY FINDINGS OF THE REVIEW (decisions of 28/10)
# =============================================================================


def balanced_xlsx(work: Work, rows: Sequence[Acc], *, opening: str, date_from: str, date_to: str) -> Path:
    """An account XLSX whose chain closes: the closing balance is the opening plus the rows."""
    closing = Decimal(opening) + sum((Decimal(row.amount) for row in rows), Decimal("0"))
    return work.acc(rows, "xlsx", opening=opening, closing=f"{closing:.2f}", date_from=date_from, date_to=date_to)


SELL_BOND_A_DESC = f"NOTA INF. VEND. TIT:{BOND_A_ACC} DOSS:00000/00000000"


class TestAccountRowsAreNeverDroppedForLackOfAPair:
    """Rule 1: an account row is cash the bank really moved."""

    @pytest.mark.parametrize(
        ("row", "klass"),
        [
            (Acc("2025-08-10", TRADE_CAUSALE, SELL_BOND_A_DESC, "5000.00"), "trade_sell"),
            (buy_acc("2025-08-10", "5000.00", name=BOND_A_ACC), "trade_buy"),
            (fund_buy_acc("2025-08-10", "5000.00"), "trade_buy"),
            (Acc("2025-08-10", TRADE_CAUSALE, "OPERAZIONE SENZA PAROLA CHIAVE", "-5000.00"), "trade_unknown"),
            (Acc("2025-08-10", TRADE_CAUSALE, BUY_DESC, "5000.00"), "trade_unknown"),  # the word says buy, the sign says money in
        ],
    )
    def test_an_unpaired_trade_is_standalone_with_its_reason(self, work, row, klass):
        analysis = work.analysis(acc=[work.acc([row])])
        assert analysis.account[0].klass == klass
        assert outcome_of(analysis.account[0]) == ("standalone", "no_counterpart")

    def test_an_unpaired_trade_is_standalone_even_next_to_a_securities_export(self, work):
        analysis = work.analysis(sec=[work.sec([coupon_sec("2025-08-20", "9.00", name="LONELY BOND")])], acc=[work.acc([Acc("2025-08-10", TRADE_CAUSALE, SELL_BOND_A_DESC, "5000.00")])])
        assert outcome_of(analysis.account[0]) == ("standalone", "no_counterpart")

    def test_an_invalid_and_a_superseded_account_row_stay_excluded(self, work):
        invalid = work.analysis(acc=[work.acc([pos_acc("2025-08-10", "n/d")])])
        assert outcome_of(invalid.account[0]) == ("excluded", "invalid")
        full = [pos_acc("2025-10-01", "-1.00", "a"), pos_acc("2025-10-01", "-2.00", "b")]
        cut = [full[0], pos_acc("2025-10-09", "-9.00", "z")]
        superseded = work.analysis(acc=[work.acc(full), work.acc(cut)])
        assert [outcome_of(row) for row in superseded.superseded] == [("excluded", "superseded")]

    def test_one_securities_row_against_two_account_rows(self, work):
        accs = [coupon_acc("2025-08-10", "100.00", name="ZZZ ALPHA 2030", isin=ISIN_A), coupon_acc("2025-08-10", "100.00", name="ZZZ BETA 2031", isin=ISIN_B)]
        analysis = work.analysis(sec=[work.sec([coupon_sec("2025-08-10", "100.00")])], acc=[work.acc(accs)])
        assert analysis.pairs == []
        assert [outcome_of(row) for row in analysis.securities] == [("excluded", "ambiguous")]
        assert [outcome_of(row) for row in analysis.account] == [("standalone", "ambiguous")] * 2

    def test_two_securities_rows_against_one_account_row(self, work):
        secs = [coupon_sec("2025-08-10", "100.00", name="ALPHA BOND 2030 1%"), coupon_sec("2025-08-10", "100.00", name="BETA BOND 2031 2%")]
        analysis = work.analysis(sec=[work.sec(secs)], acc=[work.acc([coupon_acc("2025-08-10", "100.00", name="GAMMA BOND 2040", isin=ISIN_A)])])
        assert analysis.pairs == []
        assert [outcome_of(row) for row in analysis.securities] == [("excluded", "ambiguous")] * 2
        assert [outcome_of(row) for row in analysis.account] == [("standalone", "ambiguous")]

    def test_two_securities_rows_against_two_account_rows(self, work):
        secs = [coupon_sec("2025-08-10", "100.00", name="ALPHA BOND 2030 1%"), coupon_sec("2025-08-10", "100.00", name="BETA BOND 2031 2%")]
        accs = [coupon_acc("2025-08-10", "100.00", name="GAMMA BOND 2040", isin=ISIN_A), coupon_acc("2025-08-10", "100.00", name="DELTA BOND 2041", isin=ISIN_B)]
        analysis = work.analysis(sec=[work.sec(secs)], acc=[work.acc(accs)])
        assert analysis.pairs == []
        assert [outcome_of(row) for row in analysis.securities] == [("excluded", "ambiguous")] * 2
        assert [outcome_of(row) for row in analysis.account] == [("standalone", "ambiguous")] * 2


# --- rule 2: a hole after a broken interval is not corrected ---------------------------------------------------------


def hole_after_broken_files(work: Work) -> List[Path]:
    """July closes, August is broken by -100 (its rows add 200, its balances 100), September has no file (a hole of +300), October closes."""
    f1 = work.acc([salary_acc("2025-07-05", "800.00"), pos_acc("2025-07-20", "-300.00")], "xlsx", opening="1000.00", closing="1500.00", date_from="2025-07-01", date_to="2025-07-31")
    f2 = work.acc([salary_acc("2025-08-05", "500.00"), pos_acc("2025-08-18", "-300.00")], "xlsx", opening="1500.00", closing="1600.00", date_from="2025-08-01", date_to="2025-08-31")
    f3 = work.acc([salary_acc("2025-10-08", "300.00"), pos_acc("2025-10-22", "-200.00")], "xlsx", opening="1900.00", closing="2000.00", date_from="2025-10-01", date_to="2025-10-31")
    return [f1, f2, f3]


def hole_after_broken(work: Work) -> Analysis:
    return work.analysis(acc=hole_after_broken_files(work))


class TestHoleAfterABrokenInterval:
    def test_the_intervals_of_the_scenario(self, work):
        analysis = hole_after_broken(work)
        assert [i.kind for i in analysis.intervals] == ["closed", "broken", "hole", "closed"]
        assert analysis.intervals[1].residual == Decimal("-100.00")
        assert analysis.intervals[2].residual == Decimal("300.00")
        assert analysis.opening_statement.as_of == d("2025-06-30")

    def test_no_gap_checkpoint_after_a_broken_interval(self, work):
        analysis = hole_after_broken(work)
        assert [c.kind for c in analysis.checkpoints] == ["opening"]

    def test_the_hole_is_still_reported_but_not_corrected(self, work):
        analysis = hole_after_broken(work)
        assert analysis.gaps() == [DateRangeModel(start=d("2025-09-01"), end=d("2025-09-30"))]
        notice = notice_of(analysis, "account_gap")
        assert notice.severity == "warning"
        assert notice.context == {"start": "2025-09-01", "end": "2025-09-30", "amount": "300.00", "corrected": False}
        assert notice_of(analysis, "balance_chain_broken").context == {"date": "2025-08-31"}

    def test_the_end_of_the_hole_is_only_compared(self, work):
        analysis = hole_after_broken(work)
        (verification,) = [v for v in analysis.verifications if v.as_of == d("2025-09-30")]
        assert (verification.kind, verification.stated) == ("verification", Decimal("1900.00"))
        assert {v.kind for v in analysis.verifications} == {"verification"}

    def test_a_hole_before_a_later_broken_interval_keeps_its_checkpoint(self, work):
        f1 = work.acc([salary_acc("2025-07-05", "800.00"), pos_acc("2025-07-20", "-300.00")], "xlsx", opening="1000.00", closing="1500.00", date_from="2025-07-01", date_to="2025-07-31")
        f2 = work.acc([salary_acc("2025-09-05", "500.00"), pos_acc("2025-09-18", "-200.00")], "xlsx", opening="2200.00", closing="2500.00", date_from="2025-09-01", date_to="2025-09-30")
        f3 = work.acc([salary_acc("2025-10-08", "300.00")], "xlsx", opening="2500.00", closing="2900.00", date_from="2025-10-01", date_to="2025-10-31")
        analysis = work.analysis(acc=[f1, f2, f3])
        assert [i.kind for i in analysis.intervals] == ["closed", "hole", "closed", "broken"]
        assert [c.kind for c in analysis.checkpoints] == ["opening", "gap"]
        assert notice_of(analysis, "account_gap").context["corrected"] is True


# --- rule 3: opening positions include what is in flight -------------------------------------------------------------


def opening_positions(analysis: Analysis) -> Dict[str, Decimal]:
    """The positions of the opening checkpoint by normalised title."""
    (opening,) = [c for c in analysis.checkpoints if c.kind == "opening"]
    return {core.norm(position.name): position.quantity for position in opening.positions}


PERIOD = {"opening": "10000.00", "date_from": "2025-08-01", "date_to": "2025-08-31"}  # the opening statement is the eve of it: 2025-07-31


class TestOpeningPositionsInFlight:
    def test_a_purchase_recorded_before_the_opening_and_booked_after_it_adds_its_quantity(self, work):
        sec = work.sec([transfer_sec("2025-07-15", BOND_B, "1000"), buy_sec("2025-07-29", "5000.00", name="btp demo  15/03/2033 3.35%", qty="500", value="2025-08-01")])
        account = balanced_xlsx(work, [buy_acc("2025-08-01", "5000.00")], **PERIOD)
        analysis = work.analysis(sec=[sec], acc=[account])
        assert len(analysis.pairs) == 1
        assert analysis.opening_statement.as_of == d("2025-07-31")
        assert opening_positions(analysis) == {core.norm(BOND_B): Decimal("1500")}

    def test_a_purchase_booked_by_the_bank_before_the_opening_but_recorded_after_it_changes_nothing(self, work):
        # The ledger holds what is recorded by the opening day; the account date does not matter.
        sec = work.sec([transfer_sec("2025-07-15", BOND_B, "1000"), buy_sec("2025-08-01", "5000.00", qty="500", value="2025-08-02")])
        account = balanced_xlsx(work, [], **PERIOD)
        bank_first = work.acc([buy_acc("2025-07-30", "5000.00", value="2025-08-02")])
        analysis = work.analysis(sec=[sec], acc=[account, bank_first])
        assert len(analysis.pairs) == 1
        assert opening_positions(analysis) == {core.norm(BOND_B): Decimal("1000")}

    def test_a_purchase_recorded_and_booked_before_the_opening_is_added(self, work):
        # An old account file (a CSV) that precedes the first XLSX: the purchase is in the ledger at the opening.
        sec = work.sec([transfer_sec("2025-07-15", BOND_B, "1000"), buy_sec("2025-07-20", "3000.00", qty="300", value="2025-07-21")])
        account = balanced_xlsx(work, [], **PERIOD)
        old_csv = work.acc([buy_acc("2025-07-21", "3000.00")])
        analysis = work.analysis(sec=[sec], acc=[account, old_csv])
        assert len(analysis.pairs) == 1
        assert opening_positions(analysis) == {core.norm(BOND_B): Decimal("1300")}

    def test_a_redemption_in_flight_is_negative(self, work):
        sec = work.sec([transfer_sec("2025-07-15", FUND_R_SEC, "300"), redeem_sec("2025-07-29", "900.00", value="2025-08-01")])
        account = balanced_xlsx(work, [redeem_acc("2025-08-01", "900.00")], **PERIOD)
        analysis = work.analysis(sec=[sec], acc=[account])
        assert len(analysis.pairs) == 1
        assert opening_positions(analysis) == {core.norm(FUND_R_SEC): Decimal("200")}

    def test_a_redemption_booked_first_but_recorded_after_the_opening_changes_nothing(self, work):
        sec = work.sec([transfer_sec("2025-07-15", FUND_R_SEC, "300"), redeem_sec("2025-08-01", "900.00", value="2025-08-02")])
        bank_first = work.acc([redeem_acc("2025-07-30", "900.00", value="2025-08-02")])
        analysis = work.analysis(sec=[sec], acc=[balanced_xlsx(work, [], **PERIOD), bank_first])
        assert len(analysis.pairs) == 1
        assert opening_positions(analysis) == {core.norm(FUND_R_SEC): Decimal("300")}

    def test_a_redemption_recorded_and_booked_before_the_opening_is_subtracted(self, work):
        sec = work.sec([transfer_sec("2025-07-15", FUND_R_SEC, "300"), redeem_sec("2025-07-20", "900.00", value="2025-07-21")])
        old_csv = work.acc([redeem_acc("2025-07-21", "900.00")])
        analysis = work.analysis(sec=[sec], acc=[balanced_xlsx(work, [], **PERIOD), old_csv])
        assert len(analysis.pairs) == 1
        assert opening_positions(analysis) == {core.norm(FUND_R_SEC): Decimal("200")}

    def test_a_maturity_in_flight_leaves_the_title_without_a_position(self, work):
        matured = Sec("2025-07-29", BOND_A, "TITOLI SCADUTI", "0", "40000.00", "2025-08-01")  # the quantity is 0 in the file: the number is unknown
        sec = work.sec([transfer_sec("2025-07-15", BOND_A, "40000"), transfer_sec("2025-07-16", BOND_B, "10"), matured])
        account = balanced_xlsx(work, [matured_acc("2025-08-01", "40000.00")], **PERIOD)
        analysis = work.analysis(sec=[sec], acc=[account])
        assert len(analysis.pairs) == 1
        assert opening_positions(analysis) == {core.norm(BOND_B): Decimal("10")}

    def test_pairs_wholly_after_the_opening_change_nothing(self, work):
        # The ledger does not hold them at the opening day, whichever the account date.
        sec = work.sec([transfer_sec("2025-07-15", BOND_B, "1000"), buy_sec("2025-08-05", "2000.00", qty="200", value="2025-08-06"), Sec("2025-08-10", BOND_B, "TITOLI SCADUTI", "0", "700.00", "2025-08-11")])
        account = balanced_xlsx(work, [buy_acc("2025-08-06", "2000.00"), matured_acc("2025-08-11", "700.00", name=BOND_B_ACC)], **PERIOD)
        analysis = work.analysis(sec=[sec], acc=[account])
        assert len(analysis.pairs) == 2
        assert opening_positions(analysis) == {core.norm(BOND_B): Decimal("1000")}

    def test_a_maturity_recorded_before_the_opening_leaves_the_title_without_a_position(self, work):
        sec = work.sec([transfer_sec("2025-07-05", BOND_B, "1000"), Sec("2025-07-10", BOND_B, "TITOLI SCADUTI", "0", "700.00", "2025-07-11")])
        old_csv = work.acc([matured_acc("2025-07-11", "700.00", name=BOND_B_ACC)])
        analysis = work.analysis(sec=[sec], acc=[balanced_xlsx(work, [], **PERIOD), old_csv])
        assert len(analysis.pairs) == 1
        assert opening_positions(analysis) == {}

    def test_a_title_without_a_transfer_gets_no_position_from_a_pair_in_flight(self, work):
        sec = work.sec([buy_sec("2025-07-29", "5000.00", qty="500", value="2025-08-01")])
        account = balanced_xlsx(work, [buy_acc("2025-08-01", "5000.00")], **PERIOD)
        analysis = work.analysis(sec=[sec], acc=[account])
        assert len(analysis.pairs) == 1
        assert opening_positions(analysis) == {}


# --- rule 4: a row inside a hole is imported -------------------------------------------------------------------------


class TestRowsInsideAHoleAreImported:
    def _july_hole(self, work: Work, rows: Sequence[Sec]) -> Analysis:
        return work.analysis(sec=[work.sec(rows)], acc=[file_a(work), file_b(work)])  # the hole is 2025-07-01 .. 2025-07-31

    def test_coupon_buy_and_maturity_inside_the_hole_are_standalone(self, work):
        rows = [
            coupon_sec("2025-07-15", "10.00", name="IN COUPON"),
            buy_sec("2025-07-31", "20.00", name="IN BUY"),  # the last day of the hole is inside
            matured_sec("2025-07-01", "30.00", name="IN MATURITY"),  # so is the first
            redeem_sec("2025-07-20", "40.00", name="IN REDEMPTION"),
        ]
        analysis = self._july_hole(work, rows)
        assert len(analysis.holes) == 1
        for row in analysis.securities:
            assert outcome_of(row) == ("standalone", "in_gap"), row.name
            assert row.outcome.zone == ZONE_GAP

    def test_a_row_just_outside_the_hole_keeps_its_outcome(self, work):
        rows = [
            coupon_sec("2025-06-30", "10.00", name="OPENING DAY"),  # the opening day itself is not in the hole
            coupon_sec("2025-08-01", "20.00", name="NEXT DAY"),  # the account covers it: no counterpart
            Sec("2025-07-30", "OP INSIDE VALUE OUTSIDE", "CEDOLA", "1", "30.00", "2025-08-02"),  # the value date decides
        ]
        analysis = self._july_hole(work, rows)
        assert outcome_of(pick(analysis.securities, name="OPENING DAY")) == ("excluded", "outside_cash_coverage")
        assert outcome_of(pick(analysis.securities, name="NEXT DAY")) == ("excluded", "no_counterpart")
        assert outcome_of(pick(analysis.securities, name="OP INSIDE VALUE OUTSIDE")) == ("excluded", "no_counterpart")

    def test_both_dates_must_lie_inside_the_hole_and_the_operation_date_is_the_fallback(self, work):
        rows = [
            Sec("2025-07-10", "BOTH INSIDE", "CEDOLA", "1", "10.00", "2025-07-12"),
            Sec("2025-07-10", "NO VALUE DATE", "CEDOLA", "1", "20.00", ""),
            Sec("2025-06-20", "NO VALUE DATE OUTSIDE", "CEDOLA", "1", "30.00", ""),
            Sec("2025-06-20", "OP OUTSIDE VALUE INSIDE", "CEDOLA", "1", "40.00", "2025-07-05"),
        ]
        analysis = self._july_hole(work, rows)
        assert outcome_of(pick(analysis.securities, name="BOTH INSIDE")) == ("standalone", "in_gap")
        assert outcome_of(pick(analysis.securities, name="NO VALUE DATE")) == ("standalone", "in_gap")
        assert outcome_of(pick(analysis.securities, name="NO VALUE DATE OUTSIDE")) == ("excluded", "outside_cash_coverage")
        # The operation date is outside the hole: the cash may already be in the balance the hole is corrected to (single count).
        assert outcome_of(pick(analysis.securities, name="OP OUTSIDE VALUE INSIDE")) == ("excluded", "outside_cash_coverage")

    def test_an_operation_date_inside_and_a_value_date_after_the_hole_is_not_imported(self, work):
        rows = [Sec("2025-07-20", "OP INSIDE VALUE AFTER", "CEDOLA", "1", "10.00", "2025-08-03"), buy_sec("2025-07-31", "20.00", name="LAST DAY VALUE NEXT", value="2025-08-01")]
        analysis = self._july_hole(work, rows)
        assert outcome_of(pick(analysis.securities, name="OP INSIDE VALUE AFTER")) == ("excluded", "no_counterpart")
        assert outcome_of(pick(analysis.securities, name="LAST DAY VALUE NEXT")) == ("excluded", "no_counterpart")

    def test_the_two_dates_must_lie_in_the_same_hole(self, work):
        # July closes, August is a hole, September closes, October is a hole, November closes.
        f1 = work.acc([salary_acc("2025-07-05", "1000.00"), pos_acc("2025-07-20", "-600.00")], "xlsx", opening="5000.00", closing="5400.00", date_from="2025-07-01", date_to="2025-07-31")
        f2 = work.acc([salary_acc("2025-09-10", "500.00")], "xlsx", opening="5200.00", closing="5700.00", date_from="2025-09-01", date_to="2025-09-30")
        f3 = work.acc([salary_acc("2025-11-10", "100.00")], "xlsx", opening="5500.00", closing="5600.00", date_from="2025-11-01", date_to="2025-11-30")
        rows = [
            Sec("2025-08-20", "SAME HOLE", "CEDOLA", "1", "10.00", "2025-08-25"),
            Sec("2025-08-20", "OTHER HOLE", "CEDOLA", "1", "20.00", "2025-10-05"),
        ]
        analysis = work.analysis(sec=[work.sec(rows)], acc=[f1, f2, f3])
        assert len(analysis.holes) == 2
        assert outcome_of(pick(analysis.securities, name="SAME HOLE")) == ("standalone", "in_gap")
        assert outcome_of(pick(analysis.securities, name="OTHER HOLE")) == ("excluded", "outside_cash_coverage")

    def test_a_fund_booked_by_the_bank_before_the_securities_date_is_counted_once(self, work):
        # The SICAV case: operation 1 September, value 31 August; the bank debited 30 August, a day no file covers.
        # B's opening balance (eve of 1 September) already holds the debit, so the correction of the hole takes it: the row must not take it again.
        f1 = balanced_xlsx(work, [salary_acc("2025-07-05", "1000.00"), pos_acc("2025-07-20", "-600.00")], opening="5000.00", date_from="2025-07-01", date_to="2025-07-31")  # 5400.00 on 07-31
        f2 = balanced_xlsx(work, [salary_acc("2025-09-10", "500.00")], opening="4400.00", date_from="2025-09-01", date_to="2025-09-30")  # 5400 - 1000 for the fund on 08-30
        sec = work.sec([fund_buy_sec("2025-09-01", "1000.00", value="2025-08-31")])
        analysis = work.analysis(sec=[sec], acc=[f1, f2])
        (hole,) = analysis.holes
        assert (hole.days, hole.residual) == (DateRangeModel(start=d("2025-08-01"), end=d("2025-08-31")), Decimal("-1000.00"))
        assert [c.kind for c in analysis.checkpoints] == ["opening", "gap"]  # the correction holds the -1000.00 ...
        assert analysis.checkpoints[1].cash.stated == Decimal("4400.00")
        (row,) = analysis.securities
        assert row.outcome.kind == "excluded"  # ... so the row, dated 1 September, must not take it again
        assert outcome_of(row) == ("excluded", "outside_cash_coverage")
        assert not any(outcome_of(r) == ("standalone", "in_gap") for r in analysis.securities)

    @pytest.mark.parametrize("account_amount", ["1000.01", "1010.00"])  # a cent off, or the amount with a fee
    def test_an_account_row_that_fails_to_pair_is_the_single_count_of_its_cash(self, work, account_amount):
        # File B holds the debit (op 1 September, value 31 August) but its amount differs from the securities row's: no pair.
        # The securities row has its value date inside the hole and its operation date outside: it must stay out; the account row is the cash.
        f1 = balanced_xlsx(work, [salary_acc("2025-07-05", "1000.00"), pos_acc("2025-07-20", "-600.00")], opening="5000.00", date_from="2025-07-01", date_to="2025-07-31")  # 5400.00 on 07-31
        f2 = balanced_xlsx(work, [buy_acc("2025-09-01", account_amount, name=BOND_B_ACC, value="2025-08-31"), salary_acc("2025-09-10", "500.00")], opening="5200.00", date_from="2025-09-01", date_to="2025-09-30")
        sec = work.sec([buy_sec("2025-09-01", "1000.00", name=BOND_B, qty="5000", value="2025-08-31")])
        analysis = work.analysis(sec=[sec], acc=[f1, f2])
        assert len(analysis.holes) == 1
        assert analysis.pairs == []
        (row,) = analysis.securities
        assert row.outcome.kind == "excluded"
        assert outcome_of(pick(analysis.account, causale=TRADE_CAUSALE)) == ("standalone", "no_counterpart")
        assert not any(outcome_of(r) == ("standalone", "in_gap") for r in analysis.securities)

    def test_a_transfer_and_an_unknown_type_are_not_changed_by_the_hole(self, work):
        rows = [transfer_sec("2025-07-15", "T1", "10"), Sec("2025-07-16", "ODD", "FOO BAR", "1", "6.00")]
        analysis = self._july_hole(work, rows)
        assert outcome_of(pick(analysis.securities, name="T1")) == ("standalone", "")
        assert outcome_of(pick(analysis.securities, name="ODD")) == ("excluded", "unknown_type")

    def test_a_hole_that_is_not_corrected_still_imports_its_rows(self, work):
        sec = work.sec([coupon_sec("2025-09-15", "10.00", name="IN THE HOLE"), coupon_sec("2025-08-15", "20.00", name="IN THE BROKEN STRETCH")])
        analysis = work.analysis(sec=[sec], acc=hole_after_broken_files(work))
        assert [c.kind for c in analysis.checkpoints] == ["opening"]
        assert len(analysis.holes) == 1
        assert outcome_of(pick(analysis.securities, name="IN THE HOLE")) == ("standalone", "in_gap")
        assert outcome_of(pick(analysis.securities, name="IN THE BROKEN STRETCH")) == ("excluded", "no_counterpart")


# --- rule 5: the notices that count what was left unpaired -----------------------------------------------------------


def unpaired_set(work: Work) -> Tuple[List[Path], List[Path]]:
    """Three rows ambiguous, four with no counterpart (and one outside the cash coverage, which is counted in neither)."""
    accs = [
        coupon_acc("2025-08-10", "100.00", isin=ISIN_A),
        coupon_acc("2025-08-10", "100.00", isin=ISIN_B),
        buy_acc("2025-08-12", "50.00"),
        Acc("2025-08-13", TRADE_CAUSALE, SELL_BOND_A_DESC, "60.00"),
        Acc("2025-08-14", TRADE_CAUSALE, "OPERAZIONE SENZA PAROLA CHIAVE", "-70.00"),
        pos_acc("2025-08-01", "-1.00"),
        pos_acc("2025-08-31", "-2.00", "b"),
    ]
    secs = [coupon_sec("2025-08-10", "100.00"), coupon_sec("2025-08-20", "7.00", name="LONELY BOND"), coupon_sec("2025-07-01", "8.00", name="OUTSIDE BOND")]
    return [work.sec(secs)], [work.acc(accs)]


class TestPairingNotices:
    def test_the_ambiguous_notice_counts_securities_and_account_rows(self, work):
        sec, acc = unpaired_set(work)
        notice = notice_of(work.analysis(sec=sec, acc=acc), "ambiguous")
        assert notice.severity == "warning"
        assert notice.context == {"rows": 3}

    def test_the_no_counterpart_notice_counts_unpaired_securities_and_account_rows(self, work):
        sec, acc = unpaired_set(work)
        analysis = work.analysis(sec=sec, acc=acc)
        notice = notice_of(analysis, "no_counterpart")
        assert notice.severity == "warning"
        assert notice.context == {"rows": 4}  # LONELY BOND, plus the three trades of the account

    def test_describe_set_returns_them(self, work):
        sec, acc = unpaired_set(work)
        shape = describe_set({ROLE_SECURITIES: sec, ROLE_ACCOUNT: acc})
        assert pick(shape.notices, code="ambiguous").context == {"rows": 3}
        assert pick(shape.notices, code="no_counterpart").context == {"rows": 4}

    def test_no_notice_when_nothing_is_left_unpaired(self, work):
        analysis = work.analysis(sec=[work.sec([coupon_sec("2025-08-10", "100.00")])], acc=[work.acc([coupon_acc("2025-08-10", "100.00")])])
        assert "ambiguous" not in codes(analysis)
        assert "no_counterpart" not in codes(analysis)
        shape = describe_set({ROLE_SECURITIES: [work.sec([coupon_sec("2025-08-10", "100.00")])], ROLE_ACCOUNT: [work.acc([coupon_acc("2025-08-10", "100.00")])]})
        assert {notice.code for notice in shape.notices} == {"no_balance"}

    def test_only_the_ambiguous_notice_when_nothing_else_is_left_over(self, work):
        accs = [coupon_acc("2025-08-10", "100.00", isin=ISIN_A), coupon_acc("2025-08-10", "100.00", isin=ISIN_B)]
        analysis = work.analysis(sec=[work.sec([coupon_sec("2025-08-10", "100.00")])], acc=[work.acc(accs)])
        assert notice_of(analysis, "ambiguous").context == {"rows": 3}
        assert "no_counterpart" not in codes(analysis)

    def test_a_row_outside_the_cash_coverage_or_not_yet_settled_is_not_counted(self, work):
        account = work.acc([pos_acc("2025-08-01", "-1.00"), pos_acc("2025-08-31", "-2.00", "b")])
        secs = [coupon_sec("2025-07-01", "8.00", name="BEFORE"), coupon_sec("2025-09-15", "9.00", name="AFTER")]
        analysis = work.analysis(sec=[work.sec(secs)], acc=[account])
        assert "no_counterpart" not in codes(analysis)

    def test_a_paired_trade_is_never_counted(self, work):
        analysis = work.analysis(sec=[work.sec([buy_sec("2025-08-10", "50.00")])], acc=[work.acc([buy_acc("2025-08-10", "50.00")])])
        assert "no_counterpart" not in codes(analysis)


# --- rule 7: the pairing key rounds half up to the cent ---------------------------------------------------------------


class TestPairingKeyRoundsHalfUp:
    DAY = "2026-04-10"

    @pytest.mark.parametrize(
        ("sec_amount", "acc_amount", "pairs"),
        [
            ("1000.005", "1000.01", True),  # half up: 1000.005 -> 1000.01 (half-even would give 1000.00)
            ("1000.004", "1000.00", True),
            ("1000.006", "1000.01", True),
            ("1000.00", "1000.005", False),  # 1000.005 -> 1000.01 on the account side too: it differs from 1000.00
            ("1000.01", "1000.005", True),
            ("2000.015", "2000.02", True),
            ("1000.015", "1000.01", False),  # the known limit: 1000.015 rounds up to 1000.02, one cent from the account's 1000.01
        ],
    )
    def test_the_amount_is_rounded_half_up_to_the_cent_on_both_sides(self, work, sec_amount, acc_amount, pairs):
        result = pair(work, [coupon_sec(self.DAY, sec_amount)], [coupon_acc(self.DAY, acc_amount)])
        assert (len(result.pairs) == 1) is pairs

    def test_a_securities_amount_of_1000_015_does_not_pair_with_1000_01_known_limit(self, work):
        assert pair(work, [coupon_sec(self.DAY, "1000.015")], [coupon_acc(self.DAY, "1000.01")]).pairs == []

    def test_the_same_rule_holds_for_a_purchase(self, work):
        result = pair(work, [buy_sec(self.DAY, "5000.005")], [buy_acc(self.DAY, "5000.01")])
        assert len(result.pairs) == 1


# =============================================================================
# W5-7 STEP 6 — THE PLUGIN ON THE REPORT SET (written red first, before the wiring)
# =============================================================================
#
# Everything above reads the exports (rows, rule M, pairs, balances). From here the plugin ``broker_credit_agricole`` 2.0.0
# is the subject: its contract (roles, ``can_parse``, ``parse`` of an original), ``combine`` (the combined table) and
# ``parse`` (the combined file). The contract is the sheet "W-CP3 · contratto di combine / parse" of the plan W5-7.
#
# Every set is synthetic and built by the builders above. Each scenario is combined once, written with the core's
# ``write_combined_csv`` and parsed once; the end-to-end proofs run ``apply_history`` and ``compute_gap_fix`` on a private
# in-memory SQLite database (never the lane's), as the wizard does for a first import.
#
# What is NOT here: the optional ``portfolio`` role (step 7).

PLUGIN_CODE = "broker_credit_agricole"
SAMPLE_DIR = SampleDir()
BROKER_ID = 1
REAL_ASSET_BASE = 101

NEW_BOND, NEW_BOND_ACC = "BTP NUOVO 1/2/2036 3.00%", "BTP NUOVO 1/2/2036"
LONELY_BOND = "BTP LONELY 1/1/2030 2%"

LF_HEADERS = ["lf_row_kind", "lf_zone", "lf_reason", "lf_checkpoint", "lf_source", "lf_match_key", "lf_value", "lf_currency", "lf_proof"]
COMBINED_HEADERS = [*LF_HEADERS, *(f"securities:{column}" for column in SECURITIES_COLUMNS), *(f"account:{column}" for column in ACCOUNT_COLUMNS)]
DATA_KINDS = {"pair", "standalone", "excluded"}
TRUTH_KINDS = {"truth_cash", "truth_position", "verification"}
ITALIAN_DATE_RE = re.compile(r"^\d{2}/\d{2}/\d{4}$")
ITALIAN_MONEY_RE = re.compile(r"^-?\d+,\d{2}$")
PLAIN_QUANTITY_RE = re.compile(r"^\d+(\.\d+)?$")
SOURCE_TOKEN_RE = re.compile(r"^(securities|account)(?:#([1-9]\d*))?:([1-9]\d*)$")


def ca_plugin() -> BRIMProvider:
    """The registered Crédit Agricole plugin (looked up inside every test, never at import time)."""
    BRIMProviderRegistry.auto_discover()
    found = BRIMProviderRegistry.get_provider_instance(PLUGIN_CODE)
    if found is None:
        pytest.fail(f"no BRIM plugin is registered as {PLUGIN_CODE}", pytrace=False)
    return found


# --- the scenarios: member files built once, combined once, parsed once -------------------------------------------------


@dataclass
class Run:
    """A scenario after the plugin: its member files, the combined table, the combined file and its parse."""

    members: Dict[str, List[Path]]
    folder: Path
    table: BRIMCombinedTable
    path: Path
    output: BRIMParseOutput

    @property
    def records(self) -> List[Dict[str, str]]:
        return records_of(self.table)


BUILDERS: Dict[str, Callable[[Work], Dict[str, List[Path]]]] = {}
_RUNS: Dict[str, Run] = {}


def builder(name: str) -> Callable[[Callable[[Work], Dict[str, List[Path]]]], Callable[[Work], Dict[str, List[Path]]]]:
    def register(function: Callable[[Work], Dict[str, List[Path]]]) -> Callable[[Work], Dict[str, List[Path]]]:
        BUILDERS[name] = function
        return function

    return register


def records_of(table: BRIMCombinedTable) -> List[Dict[str, str]]:
    return [dict(zip(table.headers, row, strict=True)) for row in table.rows]


def run_of(name: str, tmp_path_factory: pytest.TempPathFactory) -> Run:
    """The scenario ``name`` combined and parsed through the plugin, once per session."""
    if name not in _RUNS:
        work = Work(tmp_path_factory.mktemp(f"ca-{name}"))
        members = BUILDERS[name](work)
        plugin = ca_plugin()
        table = plugin.combine(members)
        path = work.folder / "combined.csv"
        write_combined_csv(path, table)
        _RUNS[name] = Run(members, work.folder, table, path, plugin.parse(path, broker_id=BROKER_ID))
    return _RUNS[name]


def account_xlsx(work: Work, rows: Sequence[Acc], *, opening: str, date_from: str, date_to: str) -> Path:
    """An account XLSX whose balances add up: the closing balance is the opening one plus its rows."""
    closing = Decimal(opening) + sum((Decimal(row.amount) for row in rows), Decimal(0))
    return work.acc(rows, "xlsx", opening=opening, closing=f"{closing:.2f}", date_from=date_from, date_to=date_to)


def set_of(securities: Sequence[Path], account: Sequence[Path]) -> Dict[str, List[Path]]:
    return {ROLE_SECURITIES: list(securities), ROLE_ACCOUNT: list(account)}


# --- the sets ---------------------------------------------------------------------------------------------------------


@builder("full")
def _full(work: Work) -> Dict[str, List[Path]]:
    """A month of every kind of fact. The account opens at 0 on 2026-01-31; the securities export states 4.443,75 on 2026-02-15.

    - a transfer from another dossier before the opening (40000 BOND_A), a coupon with its withholding, a purchase, a
      *collocamento* (the order is on 02-10, the bank books it on 02-18), a fund subscription, a fund redemption, a maturity
      with a premium (40500 for 40000 held), a payment whose value date is two days after its operation date, and a coupon
      that only the account export shows;
    - a securities coupon with no row in the account (excluded).
    """
    secs = [
        transfer_sec("2026-01-25", BOND_A, "40000"),
        coupon_sec("2026-02-05", "93.75"),
        buy_sec("2026-02-09", "250.00"),
        Sec("2026-02-10", NEW_BOND, "ACQ.CONT.SU MERC.", "2000", "2000.00", "2026-02-18"),
        fund_buy_sec("2026-02-12", "400.00"),
        coupon_sec("2026-02-15", "77.00", name=LONELY_BOND),
        redeem_sec("2026-02-20", "150.00"),
        matured_sec("2026-02-25", "40500.00"),
    ]
    accs = [
        salary_acc("2026-02-01", "5000.00"),
        coupon_acc("2026-02-05", "93.75"),
        buy_acc("2026-02-09", "250.00"),
        fund_buy_acc("2026-02-12", "400.00"),
        buy_acc("2026-02-18", "2000.00", name=NEW_BOND_ACC),
        redeem_acc("2026-02-20", "150.00"),
        Acc("2026-02-22", "PAGAMENTO TRAMITE POS", "POS CARTA 00000000 a", "-25.50", "2026-02-24"),
        matured_acc("2026-02-25", "40500.00"),
        coupon_acc("2026-02-27", "46.88", ritenuta="15,62"),
    ]
    return set_of([work.sec(secs, "xlsx", liquidity="4.443,75 EUR", updated="15/02/02026")], [account_xlsx(work, accs, opening="0", date_from="2026-02-01", date_to="2026-02-28")])


@builder("five_days")
def _five_days(work: Work) -> Dict[str, List[Path]]:
    """The account opens at 0 on 2026-01-31 and its first row is five days later (02-05). No transfer."""
    accs = [salary_acc("2026-02-05", "1000.00"), coupon_acc("2026-02-10", "93.75")]
    return set_of([work.sec([coupon_sec("2026-02-10", "93.75")])], [account_xlsx(work, accs, opening="0", date_from="2026-02-01", date_to="2026-02-28")])


@builder("straddle")
def _straddle(work: Work) -> Dict[str, List[Path]]:
    """A purchase ordered on 01-29 and booked on 02-02 straddles the opening (2026-01-31, balance 0)."""
    secs = [buy_sec("2026-01-29", "250.00", value="2026-02-02")]
    accs = [buy_acc("2026-02-02", "250.00"), salary_acc("2026-02-03", "1000.00")]
    return set_of([work.sec(secs)], [account_xlsx(work, accs, opening="0", date_from="2026-02-01", date_to="2026-02-28")])


def _january(work: Work) -> Path:
    accs = [salary_acc("2026-01-01", "1000.00"), coupon_acc("2026-01-10", "93.75")]
    return account_xlsx(work, accs, opening="0", date_from="2026-01-01", date_to="2026-01-31")


def _march(work: Work) -> Path:
    return account_xlsx(work, [pos_acc("2026-03-05", "-50.00")], opening="1500.00", date_from="2026-03-01", date_to="2026-03-31")


@builder("hole")
def _hole(work: Work) -> Dict[str, List[Path]]:
    """Two account exports with February missing: January closes at 1093.75, March opens at 1500.00."""
    secs = [coupon_sec("2026-01-10", "93.75")]
    return set_of([work.sec(secs)], [_january(work), _march(work)])


@builder("hole_filled")
def _hole_filled(work: Work) -> Dict[str, List[Path]]:
    """The same two exports and the February one between them (it opens at 1093.75 and closes at 1500.00)."""
    secs = [coupon_sec("2026-01-10", "93.75")]
    february = account_xlsx(work, [Acc("2026-02-10", "ACCREDITO EMOLUMENTI", "STIPENDIO SAMPLE b", "700.00"), pos_acc("2026-02-20", "-293.75")], opening="1093.75", date_from="2026-02-01", date_to="2026-02-28")
    return set_of([work.sec(secs)], [_january(work), february, _march(work)])


@builder("hole_securities")
def _hole_securities(work: Work) -> Dict[str, List[Path]]:
    """The hole of February, but the securities export has two rows in it: a coupon (+62.50) and a purchase (-100.00)."""
    secs = [coupon_sec("2026-01-10", "93.75"), coupon_sec("2026-02-10", "62.50"), buy_sec("2026-02-12", "100.00")]
    return set_of([work.sec(secs)], [_january(work), _march(work)])


@builder("coupons")
def _coupons(work: Work) -> Dict[str, List[Path]]:
    """Three coupons in both exports (two titles) and one that only the account shows: four coupons, no balance."""
    secs = [coupon_sec("2026-02-03", "93.75"), coupon_sec("2026-02-10", "50.00"), coupon_sec("2026-02-17", "12.50", name=BOND_B, qty="5000"), coupon_sec("2026-02-18", "7.00", name=LONELY_BOND)]
    accs = [
        coupon_acc("2026-02-03", "93.75"),
        coupon_acc("2026-02-10", "50.00", ritenuta="16,67"),
        coupon_acc("2026-02-17", "12.50", name=BOND_B_ACC, isin=ISIN_B, ritenuta="4,17"),
        coupon_acc("2026-02-24", "20.00", ritenuta="6,67"),
    ]
    return set_of([work.sec(secs)], [work.acc(accs)])


@builder("excluded")
def _excluded(work: Work) -> Dict[str, List[Path]]:
    """One row of every reason a row is left out, around two valid account payments (02-10, 02-20)."""
    secs = [
        coupon_sec("2026-01-05", "8.00", name="EARLY BOND 1/1/2030"),  # before the account export: outside_cash_coverage
        coupon_sec("2026-03-05", "9.00", name="LATE BOND 1/1/2030"),  # after it: not_yet_settled
        coupon_sec("2026-02-12", "7.00", name="MIDDLE BOND 1/1/2030"),  # inside it, no row in the account: no_counterpart
        Sec("2026-02-12", "ODD ROW SAMPLE", "OPERAZIONE STRANA", "0", "0"),  # a causale nobody knows: unknown_type
    ]
    accs = [pos_acc("2026-02-10", "-1.00"), pos_acc("2026-02-15", "n/d", "b"), pos_acc("2026-02-20", "-2.00", "c")]  # the middle one is unreadable: invalid
    return set_of([work.sec(secs)], [work.acc(accs)])


#: The standalone account rows and what the 1.5.0 plugin made of them (captured from the 1.5.0 plugin on exactly these rows).
PARITY_ACCOUNT_ROWS: List[Acc] = [
    salary_acc("2026-03-02", "1500.00"),
    Acc("2026-03-03", "PAGAMENTO TRAMITE POS", "POS CARTA 00000000 a", "-25.50"),
    Acc("2026-03-04", "INTERESSI/COMPETENZE", "CANONE MENSILE SAMPLE", "-4.00"),
    Acc("2026-03-05", "INTERESSI/COMPETENZE", "INTERESSI CREDITORI SAMPLE", "0.35"),
    Acc("2026-03-06", "COMMISSIONI/SPESE", "COMMISSIONE BONIFICO SAMPLE", "-2.00"),
    Acc("2026-03-07", "COMMISSIONI/SPESE", "IMPOSTA DI BOLLO SAMPLE", "-34.20"),
    coupon_acc("2026-03-10", "93.75"),
    Acc("2026-03-11", INCOME_CAUSALE, f"DIVIDENDO SAMPLE CORP {ISIN_B} DOS:00000/00000000", "12.00"),
    buy_acc("2026-03-12", "250.00"),
    Acc("2026-03-13", "CAUSALE NUOVA SAMPLE", "MOVIMENTO SAMPLE", "-9.00"),
    redeem_acc("2026-03-14", "150.00"),
    matured_acc("2026-03-15", "1000.00", name="BTP ALTRO 1/3/2026"),
    Acc("2026-03-16", "COMMISS./SPESE SU OPERAZ. TITOLI", "SPESE SAMPLE OPERAZIONE DOSSIER: 00000", "-3.00"),
]


@builder("parity")
def _parity(work: Work) -> Dict[str, List[Path]]:
    """Account rows with no securities counterpart at all: each is a standalone row. One unrelated securities row completes the set."""
    return set_of([work.sec([coupon_sec("2026-03-01", "8.00", name="UNRELATED SAMPLE BOND")])], [work.acc(PARITY_ACCOUNT_ROWS)])


@builder("maturity_derived")
def _maturity_derived(work: Work) -> Dict[str, List[Path]]:
    """A maturity with no position held by the other securities rows: 40160 at price 100.40, the nominal is derived (40000)."""
    row = Sec("2026-02-10", BOND_A, "TITOLI SCADUTI", "0", "40160.00")
    cells = _sec_cells(row)
    cells[4] = "100,40"  # the price column
    securities = _write_text(work.folder / "securities-priced.csv", [SECURITIES_CSV_HEADER, ";".join(cells)])
    return set_of([securities], [work.acc([matured_acc("2026-02-10", "40160.00")])])


# --- typed cells (point e): the XLSX as Excel writes it, numbers and dates are real cells ---------------------------------


TYPED_SECS = [coupon_sec("2026-02-05", "1234.56"), fund_buy_sec("2026-02-10", "2500.75")]
TYPED_ACCS = [salary_acc("2026-02-01", "4000.55"), coupon_acc("2026-02-05", "1234.56"), fund_buy_acc("2026-02-10", "2500.75")]


def _as_day(text: str) -> datetime:
    return datetime.combine(d(text), datetime.min.time())


def _typed_value(row_value: str, op: str) -> Optional[datetime]:
    return _as_day(op if row_value == SAME else row_value) if row_value else None


def write_securities_xlsx_typed(path: Path, rows: Sequence[Sec]) -> Path:
    """The securities XLSX with real date and number cells (the layout of ``write_securities_xlsx``)."""
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append([])
    sheet.append([])
    sheet.append([None] * 11 + ["Lista Movimenti Deposito Titoli"])
    sheet.append([])
    sheet.append([None, None, "Data operazione", "Nome", "Divisa", "Causale", "Prezzo", "Divisa prezzo", "Cambio", "Quantità", "Ctv in Eur", "Data Valuta"])
    for row in rows:
        sheet.append([None, None, _as_day(row.op), row.name, row.causale, row.causale, 0.0, row.currency, 1.0, float(Decimal(row.qty)), float(Decimal(row.ctv)), _typed_value(row.value, row.op)])
    sheet.append([None, None, None, "Totale operazioni", None, None, None, None, None, None, 0.0])
    workbook.save(path)
    return path


def write_account_xlsx_typed(path: Path, rows: Sequence[Acc], *, opening: str, date_from: str, date_to: str) -> Path:
    """The account XLSX with real cells, the testata included (the layout of ``write_account_xlsx``)."""
    closing = Decimal(opening) + sum((Decimal(row.amount) for row in rows), Decimal(0))
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.append(["Lista Movimenti Conto"])
    sheet.append(["Saldo Iniziale", None, float(Decimal(opening)), "Saldo Finale", None, float(closing)])
    sheet.append(["Data dal", None, _as_day(date_from), "Data al", None, _as_day(date_to)])
    sheet.append([])
    sheet.append(["Data Op.", "Data Val.", "Causale", "Descrizione", "Importo", "Divisa"])
    for row in rows:
        sheet.append([_as_day(row.op), _typed_value(row.value, row.op), row.causale, row.desc, float(Decimal(row.amount)), row.currency])
    sheet.append(["Totale Entrate/Uscite/Movimenti €", None, None, None, 0.0])
    workbook.save(path)
    return path


@builder("typed")
def _typed(work: Work) -> Dict[str, List[Path]]:
    securities = write_securities_xlsx_typed(work.folder / "securities-typed.xlsx", TYPED_SECS)
    account = write_account_xlsx_typed(work.folder / "account-typed.xlsx", TYPED_ACCS, opening="0", date_from="2026-02-01", date_to="2026-02-28")
    return set_of([securities], [account])


@builder("typed_twin")
def _typed_twin(work: Work) -> Dict[str, List[Path]]:
    """The same facts as the typed set, in CSV: the cells are text, written with the bank's thousands separators."""
    return set_of([work.sec(TYPED_SECS)], [work.acc(TYPED_ACCS)])


# --- reading a parse -----------------------------------------------------------------------------------------------------


def names_of(output: BRIMParseOutput) -> Dict[int, Optional[str]]:
    return {asset_id: info.extracted_name for asset_id, info in output.extracted_assets.items()}


def tx_tuples(output: BRIMParseOutput) -> List[Tuple[Any, ...]]:
    """``(type, date, quantity, cash, title)`` of every transaction, sorted (order is not what is pinned)."""
    names = names_of(output)
    found = [(tx.type.value, tx.date, tx.quantity, None if tx.cash is None else tx.cash.amount, None if tx.asset_id is None else names.get(tx.asset_id)) for tx in output.transactions]
    return sorted(found, key=lambda item: (item[1], item[0], item[4] or "", item[3] if item[3] is not None else Decimal(0)))


def expected(*items: Tuple[Any, ...]) -> List[Tuple[Any, ...]]:
    """Expected ``tx_tuples`` from ``(type, "YYYY-MM-DD", quantity, cash, title)``, sorted the same way."""
    found = [(kind, d(day), Decimal(quantity), None if cash is None else Decimal(cash), title) for kind, day, quantity, cash, title in items]
    return sorted(found, key=lambda item: (item[1], item[0], item[4] or "", item[3] if item[3] is not None else Decimal(0)))


def txs_of(output: BRIMParseOutput, **attrs: Any) -> List[Any]:
    """The transactions of a parse that match ``attrs``: ``type`` (its value text), ``date`` (ISO text) and ``title``."""
    names = names_of(output)
    found = []
    for tx in output.transactions:
        view = {"type": tx.type.value, "date": tx.date.isoformat(), "title": names.get(tx.asset_id)}
        if all(view[key] == value for key, value in attrs.items()):
            found.append(tx)
    return found


def one_tx(output: BRIMParseOutput, **attrs: Any) -> Any:
    found = txs_of(output, **attrs)
    assert len(found) == 1, f"{len(found)} transactions match {attrs}"
    return found[0]


def notice_codes(output: BRIMParseOutput) -> List[str]:
    return [notice.code for notice in output.warnings]


def checkpoint_at(output: BRIMParseOutput, as_of: str) -> Any:
    found = [checkpoint for checkpoint in output.checkpoints if checkpoint.as_of == d(as_of)]
    assert len(found) == 1, f"one checkpoint expected at {as_of}, got {[item.as_of.isoformat() for item in output.checkpoints]}"
    return found[0]


def cash_of(items: Sequence[Any]) -> Dict[str, Decimal]:
    return {item.currency: item.amount for item in items}


# --- reading a combined table ----------------------------------------------------------------------------------------------


def by_kind(records: Sequence[Dict[str, str]], *kinds: str) -> List[Dict[str, str]]:
    return [record for record in records if record["lf_row_kind"] in kinds]


def record_of(records: Sequence[Dict[str, str]], role: str, row: int) -> Dict[str, str]:
    """The one data row of the table that comes from line ``row`` of the (single) file of ``role``."""
    token = f"{role}:{row}"
    found = [record for record in by_kind(records, *DATA_KINDS) if token in record["lf_source"].split(" + ")]
    assert len(found) == 1, f"{len(found)} data rows come from {token}"
    return found[0]


def day_text(text: str) -> date:
    return datetime.strptime(text, "%d/%m/%Y").date()


def row_day(record: Dict[str, str]) -> Tuple[date, int]:
    """The day a table row is placed at, and 0 for a fact / 1 for a truth point of that day."""
    if record["lf_row_kind"] in TRUTH_KINDS:
        return d(record["lf_checkpoint"]), 1
    return day_text(record["securities:Data operazione"] or record["account:Data Op."]), 0


def truths(records: Sequence[Dict[str, str]], kind: str) -> List[Dict[str, str]]:
    return [record for record in records if record["lf_row_kind"] == kind]


# =============================================================================
# 1. THE PLUGIN'S CONTRACT: identity, roles, recognition, the refusal of an original
# =============================================================================


class TestPluginContract:
    """The plugin is a report-set plugin: 2.0.0, history tag, ``import`` policy, the two required roles, sample sets."""

    def test_version_history_tag_and_policy(self):
        plugin = ca_plugin()
        assert plugin.plugin_version == "2.0.0"
        assert plugin.history_tag == "credit_agricole"
        assert plugin.pre_checkpoint_policy == "import"  # every row is imported, nothing is summarised before a checkpoint
        assert plugin.is_report_set_plugin is True

    def test_the_two_required_roles(self):
        roles = {role.code: role for role in ca_plugin().report_roles}
        assert [role.code for role in ca_plugin().report_roles][:2] == [ROLE_SECURITIES, ROLE_ACCOUNT]
        securities, account = roles[ROLE_SECURITIES], roles[ROLE_ACCOUNT]
        assert (securities.required, securities.multiple, sorted(securities.extensions)) == (True, True, [".csv", ".xlsx"])
        assert (account.required, account.multiple, sorted(account.extensions)) == (True, True, [".csv", ".xlsx"])
        assert (securities.must_cover, account.must_cover, account.max_history) == (None, ROLE_SECURITIES, "P2Y")

    def test_the_sample_sets_are_synthetic_sets_of_both_roles(self):
        sample_sets = ca_plugin().test_sample_sets
        assert sample_sets, "a report-set plugin declares its sample sets"
        for sample_set in sample_sets:
            assert set(sample_set) == {ROLE_SECURITIES, ROLE_ACCOUNT}
            for role, names in sample_set.items():
                assert names, f"a sample set has no {role} file"
                for name in names:
                    assert (SAMPLE_DIR / name).is_file(), f"{name} is not in sample_reports/"
                    assert ca_plugin().detect_role(SAMPLE_DIR / name) == role


class TestRecognition:
    """``detect_role``, ``can_parse``, ``describe_member`` and ``describe_set`` are the analysis of the set, exposed by the plugin."""

    @pytest.mark.parametrize("kind", ["csv", "xlsx"])
    def test_detect_role_of_the_two_exports(self, work, kind):
        plugin = ca_plugin()
        assert plugin.detect_role(work.sec([coupon_sec("2026-02-05", "93.75")], kind)) == ROLE_SECURITIES
        assert plugin.detect_role(work.acc([pos_acc("2026-02-05", "-1.00")], kind)) == ROLE_ACCOUNT

    def test_a_combined_file_an_unrelated_file_and_a_binary_file_have_no_role(self, work, tmp_path_factory):
        plugin = ca_plugin()
        combined = run_of("full", tmp_path_factory).path
        assert plugin.detect_role(combined) is None
        assert plugin.detect_role(work.text("other.csv", ["a;b;c", "1;2;3"])) is None
        binary = work.folder / "garbage.xlsx"
        binary.write_bytes(b"\x00\x01\x02 not a workbook")
        assert plugin.detect_role(binary) is None

    def test_can_parse_the_exports_and_the_combined_file_and_nothing_else(self, work, tmp_path_factory):
        plugin = ca_plugin()
        binary = work.folder / "garbage.xlsx"
        binary.write_bytes(b"\x00\x01\x02 not a workbook")
        for kind in ("csv", "xlsx"):
            assert plugin.can_parse(work.sec([coupon_sec("2026-02-05", "93.75")], kind)) is True
            assert plugin.can_parse(work.acc([pos_acc("2026-02-05", "-1.00")], kind)) is True  # so that the wizard can say "the set is needed"
        assert plugin.can_parse(run_of("full", tmp_path_factory).path) is True
        assert plugin.can_parse(work.text("other.csv", ["a;b;c", "1;2;3"])) is False
        assert plugin.can_parse(work.text("notes.txt", [SECURITIES_CSV_HEADER])) is False
        assert plugin.can_parse(binary) is False
        assert plugin.can_parse(work.folder / "missing.csv") is False

    def test_describe_member_is_the_analysis_of_the_member(self, work):
        plugin = ca_plugin()
        securities = work.sec([coupon_sec("2026-02-05", "93.75"), buy_sec("2026-02-09", "250.00")], "xlsx")
        account = account_xlsx(work, [salary_acc("2026-02-01", "100.00")], opening="0", date_from="2026-02-01", date_to="2026-02-28")
        for path, role, rows in ((securities, ROLE_SECURITIES, 2), (account, ROLE_ACCOUNT, 1)):
            summary = plugin.describe_member(path)
            assert (summary.role, summary.rows) == (role, rows)
            assert summary == describe_member(path)

    def test_describe_set_is_the_analysis_of_the_set(self, tmp_path_factory):
        members = run_of("hole", tmp_path_factory).members
        shape = ca_plugin().describe_set(members)
        assert shape == describe_set(members)
        assert [(gap.start, gap.end) for gap in shape.gaps] == [(d("2026-02-01"), d("2026-02-28"))]


class TestAnOriginalIsNeverImportedAlone:
    """An export is imported through the combined file only: the original is refused with the role that is missing."""

    @pytest.mark.parametrize("kind", ["csv", "xlsx"])
    def test_a_securities_export_asks_for_the_account(self, work, kind):
        with pytest.raises(BRIMSetRequiredError) as raised:
            ca_plugin().parse(work.sec([coupon_sec("2026-02-05", "93.75")], kind), broker_id=BROKER_ID)
        assert raised.value.missing_roles == [ROLE_ACCOUNT]

    @pytest.mark.parametrize("kind", ["csv", "xlsx"])
    def test_an_account_export_asks_for_the_securities(self, work, kind):
        with pytest.raises(BRIMSetRequiredError) as raised:
            ca_plugin().parse(work.acc([pos_acc("2026-02-05", "-1.00")], kind), broker_id=BROKER_ID)
        assert raised.value.missing_roles == [ROLE_SECURITIES]

    def test_guard_a_csv_that_is_neither_an_original_nor_a_combined_file_is_a_parse_error(self, work):
        """Guard: green with the 1.5.0 plugin too (it refused an unknown header), and it must stay so."""
        with pytest.raises(BRIMParseError) as raised:
            ca_plugin().parse(work.text("other.csv", ["a;b;c", "1;2;3"]), broker_id=BROKER_ID)
        assert not isinstance(raised.value, BRIMSetRequiredError)


# =============================================================================
# 2. THE COMBINED TABLE (``combine``)
# =============================================================================


class TestCombinedTable:
    """Columns, one row per fact, kinds, reasons, order, privacy, purity."""

    def test_the_columns_and_their_order(self, tmp_path_factory):
        assert run_of("full", tmp_path_factory).table.headers == COMBINED_HEADERS

    def test_one_row_per_fact_and_the_kind_of_each(self, tmp_path_factory):
        records = run_of("full", tmp_path_factory).records
        assert Counter(record["lf_row_kind"] for record in records) == {"pair": 6, "standalone": 4, "excluded": 1, "truth_cash": 1, "truth_position": 1, "verification": 2}

    def test_each_row_of_each_file_is_in_the_table_exactly_once(self, tmp_path_factory):
        run = run_of("full", tmp_path_factory)
        wanted = [f"{ROLE_SECURITIES}:{row.row}" for row in read_securities(run.members[ROLE_SECURITIES][0]).rows]
        wanted += [f"{ROLE_ACCOUNT}:{row.row}" for row in read_account(run.members[ROLE_ACCOUNT][0]).rows]
        seen: List[str] = []
        for record in by_kind(run.records, *DATA_KINDS):
            tokens = record["lf_source"].split(" + ")
            assert all(SOURCE_TOKEN_RE.match(token) for token in tokens), record["lf_source"]
            seen += tokens
        assert sorted(seen) == sorted(wanted)

    def test_a_pair_is_one_row_with_both_halves(self, tmp_path_factory):
        run = run_of("full", tmp_path_factory)
        pairs = by_kind(run.records, "pair")
        coupon = next(record for record in pairs if record["securities:Data operazione"] == "05/02/2026")
        assert len(coupon["lf_source"].split(" + ")) == 2
        assert coupon["securities:Nome"] == BOND_A
        assert coupon["account:Descrizione"].startswith("CEDOLA:")
        assert (coupon["securities:Controvalore"], coupon["account:Importo"]) == ("93,75", "93,75")
        assert coupon["lf_zone"] == "window"
        assert all(record["securities:Nome"] and record["account:Descrizione"] for record in pairs)

    def test_the_collocamento_pair_keeps_its_two_dates(self, tmp_path_factory):
        """The order is on 02-10 (securities), the bank books it on 02-18 (account): both are in the row."""
        record = next(record for record in by_kind(run_of("full", tmp_path_factory).records, "pair") if record["securities:Nome"] == NEW_BOND)
        assert (record["securities:Data operazione"], record["securities:Data valuta"], record["account:Data Op."]) == ("10/02/2026", "18/02/2026", "18/02/2026")

    def test_a_row_of_one_export_only_has_empty_cells_for_the_other(self, tmp_path_factory):
        records = run_of("full", tmp_path_factory).records
        for record in by_kind(records, "standalone", "excluded"):
            halves = [bool(record[f"securities:{SECURITIES_COLUMNS[0]}"]), bool(record[f"account:{ACCOUNT_COLUMNS[0]}"])]
            assert sorted(halves) == [False, True], record["lf_source"]

    def test_the_standalone_and_excluded_rows_and_their_reason(self, tmp_path_factory):
        run = run_of("full", tmp_path_factory)
        by_day = {record["securities:Data operazione"] or record["account:Data Op."]: record for record in by_kind(run.records, "standalone", "excluded")}
        assert by_day["25/01/2026"]["lf_row_kind"] == "standalone"  # the transfer from another dossier
        assert (by_day["25/01/2026"]["lf_zone"], by_day["25/01/2026"]["lf_reason"]) == ("before", "")
        assert (by_day["01/02/2026"]["lf_row_kind"], by_day["01/02/2026"]["lf_reason"]) == ("standalone", "")  # the salary
        assert (by_day["15/02/2026"]["lf_row_kind"], by_day["15/02/2026"]["lf_reason"]) == ("excluded", "no_counterpart")  # the lonely coupon
        assert (by_day["27/02/2026"]["lf_row_kind"], by_day["27/02/2026"]["lf_reason"]) == ("standalone", "")  # the coupon of the account alone

    def test_every_reason_a_row_is_left_out(self, tmp_path_factory):
        run = run_of("excluded", tmp_path_factory)
        securities = {row.name: row for row in read_securities(run.members[ROLE_SECURITIES][0]).rows}
        account = {row.description: row for row in read_account(run.members[ROLE_ACCOUNT][0]).rows}
        got = {
            "EARLY BOND 1/1/2030": record_of(run.records, ROLE_SECURITIES, securities["EARLY BOND 1/1/2030"].row),
            "LATE BOND 1/1/2030": record_of(run.records, ROLE_SECURITIES, securities["LATE BOND 1/1/2030"].row),
            "MIDDLE BOND 1/1/2030": record_of(run.records, ROLE_SECURITIES, securities["MIDDLE BOND 1/1/2030"].row),
            "ODD ROW SAMPLE": record_of(run.records, ROLE_SECURITIES, securities["ODD ROW SAMPLE"].row),
            "POS CARTA 00000000 b": record_of(run.records, ROLE_ACCOUNT, account["POS CARTA 00000000 b"].row),
        }
        assert {name: (record["lf_row_kind"], record["lf_reason"]) for name, record in got.items()} == {
            "EARLY BOND 1/1/2030": ("excluded", "outside_cash_coverage"),
            "LATE BOND 1/1/2030": ("excluded", "not_yet_settled"),
            "MIDDLE BOND 1/1/2030": ("excluded", "no_counterpart"),
            "ODD ROW SAMPLE": ("excluded", "unknown_type"),
            "POS CARTA 00000000 b": ("excluded", "invalid"),
        }

    def test_a_securities_row_inside_a_hole_is_standalone_in_gap(self, tmp_path_factory):
        run = run_of("hole_securities", tmp_path_factory)
        rows = {row.op: row for row in read_securities(run.members[ROLE_SECURITIES][0]).rows}
        for day in ("2026-02-10", "2026-02-12"):
            record = record_of(run.records, ROLE_SECURITIES, rows[d(day)].row)
            assert (record["lf_row_kind"], record["lf_reason"], record["lf_zone"]) == ("standalone", "in_gap", "gap"), day

    def test_the_table_is_ordered_by_operation_date_and_a_days_truth_points_come_after_its_facts(self, tmp_path_factory):
        keys = [row_day(record) for record in run_of("full", tmp_path_factory).records]
        assert keys == sorted(keys)

    def test_the_cash_truth_points(self, tmp_path_factory):
        records = run_of("full", tmp_path_factory).records
        (opening,) = truths(records, "truth_cash")
        assert (opening["lf_checkpoint"], opening["lf_zone"], opening["lf_currency"], Decimal(opening["lf_value"])) == ("2026-01-31", "before", "EUR", Decimal("0"))
        # the securities export states 4.443,75 on 02-15; the 2000.00 purchase ordered on 02-10 is booked on 02-18: it is in flight
        assert {record["lf_checkpoint"]: Decimal(record["lf_value"]) for record in truths(records, "verification")} == {"2026-02-15": Decimal("2443.75"), "2026-02-28": Decimal("43115.13")}

    def test_the_opening_position_is_what_the_transfer_proves(self, tmp_path_factory):
        (position,) = truths(run_of("full", tmp_path_factory).records, "truth_position")
        assert (position["lf_checkpoint"], position["lf_proof"], Decimal(position["lf_value"])) == ("2026-01-31", "exact:transfer_in", Decimal("40000"))

    def test_a_pair_that_straddles_the_opening_is_in_flight_at_the_opening(self, tmp_path_factory):
        """Ordered on 01-29, booked on 02-02: at the end of 01-31 the ledger holds it and the bank does not."""
        (opening,) = truths(run_of("straddle", tmp_path_factory).records, "truth_cash")
        assert (opening["lf_checkpoint"], Decimal(opening["lf_value"])) == ("2026-01-31", Decimal("-250.00"))

    def test_a_hole_is_closed_by_a_cash_truth_at_its_end_and_a_covered_stretch_is_not(self, tmp_path_factory):
        hole = truths(run_of("hole", tmp_path_factory).records, "truth_cash")
        assert [(record["lf_checkpoint"], record["lf_zone"], Decimal(record["lf_value"])) for record in hole] == [("2025-12-31", "before", Decimal("0")), ("2026-02-28", "gap", Decimal("1500.00"))]
        filled = truths(run_of("hole_filled", tmp_path_factory).records, "truth_cash")
        assert [record["lf_checkpoint"] for record in filled] == ["2025-12-31"]

    def test_the_summary_is_json_and_states_the_balance_chain(self, tmp_path_factory):
        summary = run_of("full", tmp_path_factory).table.summary
        assert "balance_chain" in summary
        assert isinstance(json.dumps(summary), str)

    def test_combine_is_a_pure_function_of_the_members(self, tmp_path_factory):
        run = run_of("full", tmp_path_factory)
        again = ca_plugin().combine(run.members)
        assert (again.headers, again.rows, again.summary) == (run.table.headers, run.table.rows, run.table.summary)

    def test_the_combined_file_never_holds_a_dossier_a_support_account_or_an_owner(self, tmp_path_factory):
        text = run_of("full", tmp_path_factory).path.read_text(encoding="utf-8-sig")
        for secret in ("1234500001", "9876500002", "ROSSI MARIO"):  # the testata of the securities XLSX
            assert secret not in text


# =============================================================================
# 3. THE CELLS ARE REWRITABLE (point e)
# =============================================================================


class TestRewritableCells:
    """An XLSX with real number and date cells gives a combined file that reads back to the same figures."""

    def test_the_cells_of_a_typed_xlsx_are_written_the_way_the_combined_file_reads_them(self, tmp_path_factory):
        records = by_kind(run_of("typed", tmp_path_factory).records, *DATA_KINDS)
        assert len(records) == 3  # the coupon pair, the fund pair and the salary
        for record in records:
            for column in ("securities:Data operazione", "securities:Data valuta", "account:Data Op.", "account:Data Val."):
                assert record[column] == "" or ITALIAN_DATE_RE.match(record[column]), (column, record[column])
            for column in ("securities:Controvalore", "account:Importo"):
                assert record[column] == "" or ITALIAN_MONEY_RE.match(record[column]), (column, record[column])
            assert record["securities:Quantità"] == "" or PLAIN_QUANTITY_RE.match(record["securities:Quantità"]), record["securities:Quantità"]

    def test_the_figures_are_the_ones_of_the_cells(self, tmp_path_factory):
        pairs = {record["securities:Nome"]: record for record in by_kind(run_of("typed", tmp_path_factory).records, "pair")}
        coupon, fund = pairs[BOND_A], pairs[FUND_X]
        assert (coupon["securities:Data operazione"], coupon["securities:Controvalore"], coupon["account:Importo"]) == ("05/02/2026", "1234,56", "1234,56")
        assert (fund["securities:Data operazione"], fund["securities:Quantità"], fund["securities:Controvalore"], fund["account:Importo"]) == ("10/02/2026", "1867.178", "2500,75", "-2500,75")

    def test_the_combined_file_of_a_typed_xlsx_is_parsed_to_the_same_transactions(self, tmp_path_factory):
        output = run_of("typed", tmp_path_factory).output
        assert tx_tuples(output) == expected(
            ("DEPOSIT", "2026-02-01", "0", "4000.55", None),
            ("INTEREST", "2026-02-05", "0", "1265.81", BOND_A),
            ("TAX", "2026-02-05", "0", "-31.25", BOND_A),
            ("BUY", "2026-02-10", "1867.178", "-2500.75", FUND_X),
        )
        assert cash_of(checkpoint_at(output, "2026-01-31").cash) == {"EUR": Decimal("0")}
        assert [(item.as_of, cash_of(item.cash)) for item in output.verifications] == [(d("2026-02-28"), {"EUR": Decimal("2734.36")})]

    def test_the_same_facts_in_csv_make_the_same_transactions(self, tmp_path_factory):
        assert tx_tuples(run_of("typed_twin", tmp_path_factory).output) == tx_tuples(run_of("typed", tmp_path_factory).output)

    def test_the_combined_file_reads_back_to_the_table_it_was_written_from(self, tmp_path_factory):
        run = run_of("typed", tmp_path_factory)
        with run.path.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle, delimiter=";"))
        assert rows == [run.table.headers, *run.table.rows]


# =============================================================================
# 4. THE PARSE OF THE COMBINED FILE (``parse``)
# =============================================================================


class TestParseOfTheCombinedFile:
    """What each row of the full set becomes."""

    def test_the_transactions(self, tmp_path_factory):
        assert tx_tuples(run_of("full", tmp_path_factory).output) == expected(
            ("ADJUSTMENT", "2026-01-25", "40000", None, BOND_A),
            ("DEPOSIT", "2026-02-01", "0", "5000.00", None),
            ("INTEREST", "2026-02-05", "0", "125.00", BOND_A),
            ("TAX", "2026-02-05", "0", "-31.25", BOND_A),
            ("BUY", "2026-02-09", "5000", "-250.00", BOND_B),
            ("BUY", "2026-02-10", "2000", "-2000.00", NEW_BOND),
            ("BUY", "2026-02-12", "1867.178", "-400.00", FUND_X),
            ("SELL", "2026-02-20", "-100", "150.00", FUND_R_SEC),
            ("WITHDRAWAL", "2026-02-22", "0", "-25.50", None),
            ("SELL", "2026-02-25", "-40000", "40000.00", BOND_A),
            ("INTEREST", "2026-02-25", "0", "500.00", BOND_A),
            ("INTEREST", "2026-02-27", "0", "62.50", BOND_A),
            ("TAX", "2026-02-27", "0", "-15.62", BOND_A),
        )

    def test_a_coupon_pair_is_the_gross_interest_and_its_withholding(self, tmp_path_factory):
        output = run_of("full", tmp_path_factory).output
        interest = one_tx(output, type="INTEREST", date="2026-02-05")
        tax = one_tx(output, type="TAX", date="2026-02-05")
        assert (interest.tags, interest.description, interest.quantity) == (["import", "credit_agricole"], f"CEDOLA: {BOND_A}", 0)
        assert "withholding_tax" in tax.tags
        assert interest.cash.amount + tax.cash.amount == Decimal("93.75")  # what the bank credited

    def test_a_purchase_has_no_deposit_before_it(self, tmp_path_factory):
        output = run_of("full", tmp_path_factory).output
        deposits = txs_of(output, type="DEPOSIT")
        assert [(tx.date, tx.cash.amount) for tx in deposits] == [(d("2026-02-01"), Decimal("5000.00"))]  # the salary and nothing else

    def test_a_maturity_with_a_premium_is_a_par_sale_and_the_premium(self, tmp_path_factory):
        output = run_of("full", tmp_path_factory).output
        assert "maturity_premium" in one_tx(output, type="INTEREST", date="2026-02-25").tags
        assert "maturity_premium" not in one_tx(output, type="SELL", date="2026-02-25").tags

    def test_a_maturity_with_no_position_derives_its_nominal_and_asks_to_verify(self, tmp_path_factory):
        output = run_of("maturity_derived", tmp_path_factory).output
        assert tx_tuples(output) == expected(("SELL", "2026-02-10", "-40000", "40000.00", BOND_A), ("INTEREST", "2026-02-10", "0", "160.00", BOND_A))
        sale = one_tx(output, type="SELL")
        todos = [todo for todo in output.field_todos if output.transactions[todo.tx_index] is sale]
        assert [(todo.reason_code, todo.field, todo.severity) for todo in todos] == [("derived_quantity", "quantity", "warning")]

    def test_a_transfer_from_another_dossier_is_an_adjustment_and_a_notice(self, tmp_path_factory):
        output = run_of("full", tmp_path_factory).output
        transfer = one_tx(output, type="ADJUSTMENT")
        assert transfer.cash is None
        assert transfer.description.startswith("[GIRO ALTRO DOSSIER — successione / transfer-in]")
        notice = next(notice for notice in output.warnings if notice.code == "ca_succession_transfer_in")
        assert notice.severity == "info"

    def test_one_title_is_one_asset_and_the_isin_of_a_pair_links_the_coupon_of_the_account_alone(self, tmp_path_factory):
        output = run_of("full", tmp_path_factory).output
        names = names_of(output)
        bond_a = {tx.asset_id for tx in output.transactions if names.get(tx.asset_id) == BOND_A}
        assert len(bond_a) == 1 and None not in bond_a
        assert one_tx(output, type="INTEREST", date="2026-02-27").asset_id in bond_a  # the account coupon, written with the short name
        assert sorted(name for name in names.values() if name in (BOND_A, BOND_B, NEW_BOND, FUND_X, FUND_R_SEC)) == sorted([BOND_A, BOND_B, NEW_BOND, FUND_X, FUND_R_SEC])
        assert all(asset_id is None or is_fake_asset_id(asset_id) for asset_id in (tx.asset_id for tx in output.transactions))

    def test_nothing_is_invented_and_nothing_is_rejected(self, tmp_path_factory):
        output = run_of("full", tmp_path_factory).output
        assert output.validation_issues == []
        assert all(tx.broker_id == BROKER_ID for tx in output.transactions)

    def test_the_excluded_row_imports_nothing_and_has_a_notice(self, tmp_path_factory):
        output = run_of("full", tmp_path_factory).output
        assert not [tx for tx in output.transactions if tx.cash is not None and tx.cash.amount == Decimal("77.00")]
        assert any("no_counterpart" in code for code in notice_codes(output))

    def test_every_reason_a_row_is_left_out_has_a_notice_and_no_transaction(self, tmp_path_factory):
        output = run_of("excluded", tmp_path_factory).output
        assert tx_tuples(output) == expected(("WITHDRAWAL", "2026-02-10", "0", "-1.00", None), ("WITHDRAWAL", "2026-02-20", "0", "-2.00", None))
        codes = " ".join(notice_codes(output))
        # a notice per reason; its code is the plugin's choice (``excluded_<reason>``, or its own name for an unknown causale and an unreadable amount)
        for reason in ("outside_cash_coverage", "not_yet_settled", "no_counterpart", "unknown", "invalid"):
            assert reason in codes, reason

    def test_the_opening_checkpoint_and_the_verifications(self, tmp_path_factory):
        output = run_of("full", tmp_path_factory).output
        opening = checkpoint_at(output, "2026-01-31")
        assert [checkpoint.as_of for checkpoint in output.checkpoints] == [d("2026-01-31")]
        assert (opening.kind, cash_of(opening.cash)) == ("opening", {"EUR": Decimal("0")})
        names = names_of(output)
        assert {names[position.asset_id]: (position.quantity, position.exactness) for position in opening.positions} == {BOND_A: (Decimal("40000"), "exact")}
        assert opening.absorbed.count == 0  # with the policy import nothing is summarised
        assert opening.absorbed.opening_cash == []
        assert [(item.as_of, cash_of(item.cash)) for item in output.verifications] == [(d("2026-02-15"), {"EUR": Decimal("2443.75")}), (d("2026-02-28"), {"EUR": Decimal("43115.13")})]

    def test_a_hole_is_a_gap_checkpoint_at_its_end(self, tmp_path_factory):
        output = run_of("hole", tmp_path_factory).output
        assert [(checkpoint.as_of, checkpoint.kind, cash_of(checkpoint.cash)) for checkpoint in output.checkpoints] == [
            (d("2025-12-31"), "opening", {"EUR": Decimal("0")}),
            (d("2026-02-28"), "gap", {"EUR": Decimal("1500.00")}),
        ]
        assert [(item.as_of, cash_of(item.cash)) for item in output.verifications] == [(d("2026-01-31"), {"EUR": Decimal("1093.75")}), (d("2026-03-31"), {"EUR": Decimal("1450.00")})]

    def test_a_securities_row_inside_a_hole_brings_its_cash_and_no_counter_leg(self, tmp_path_factory):
        output = run_of("hole_securities", tmp_path_factory).output
        assert tx_tuples(output) == expected(
            ("DEPOSIT", "2026-01-01", "0", "1000.00", None),
            ("INTEREST", "2026-01-10", "0", "125.00", BOND_A),
            ("TAX", "2026-01-10", "0", "-31.25", BOND_A),
            ("INTEREST", "2026-02-10", "0", "62.50", BOND_A),
            ("BUY", "2026-02-12", "5000", "-100.00", BOND_B),
            ("WITHDRAWAL", "2026-03-05", "0", "-50.00", None),
        )

    def test_a_combined_file_keeps_its_parse_after_a_rewrite_of_its_cells(self, tmp_path_factory):
        """The parse reads the file, not the table: the file written by the core and read back gives the same transactions."""
        run = run_of("full", tmp_path_factory)
        assert tx_tuples(ca_plugin().parse(run.path, broker_id=BROKER_ID)) == tx_tuples(run.output)


class TestNoAutoCash:
    """Point d: the cash of a fact is the account's, so the securities side never adds a counter leg."""

    def test_a_coupon_is_one_interest_whatever_the_number_of_its_rows(self, tmp_path_factory):
        output = run_of("coupons", tmp_path_factory).output
        assert len(txs_of(output, type="INTEREST")) == 4  # three coupons in both exports and one in the account alone
        assert len(txs_of(output, type="TAX")) == 4
        assert len(output.transactions) == 8

    def test_no_transaction_is_an_auto_cash_leg(self, tmp_path_factory):
        for name in ("coupons", "full", "hole_securities"):
            output = run_of(name, tmp_path_factory).output
            assert not [tx for tx in output.transactions if "auto_cash" in (tx.tags or [])], name
            assert not [tx for tx in output.transactions if (tx.description or "").startswith("Auto cash")], name

    def test_the_coupons_cash_and_titles(self, tmp_path_factory):
        output = run_of("coupons", tmp_path_factory).output
        assert tx_tuples(output) == expected(
            ("INTEREST", "2026-02-03", "0", "125.00", BOND_A),
            ("TAX", "2026-02-03", "0", "-31.25", BOND_A),
            ("INTEREST", "2026-02-10", "0", "66.67", BOND_A),
            ("TAX", "2026-02-10", "0", "-16.67", BOND_A),
            ("INTEREST", "2026-02-17", "0", "16.67", BOND_B),
            ("TAX", "2026-02-17", "0", "-4.17", BOND_B),
            ("INTEREST", "2026-02-24", "0", "26.67", BOND_A),
            ("TAX", "2026-02-24", "0", "-6.67", BOND_A),
        )

    def test_the_two_titles_are_two_assets(self, tmp_path_factory):
        output = run_of("coupons", tmp_path_factory).output
        names = names_of(output)
        ids = {title: {tx.asset_id for tx in output.transactions if names.get(tx.asset_id) == title} for title in (BOND_A, BOND_B)}
        assert all(len(found) == 1 for found in ids.values())
        assert ids[BOND_A] != ids[BOND_B]
        assert one_tx(output, type="INTEREST", date="2026-02-24").asset_id in ids[BOND_A]  # the account-only coupon, by its ISIN


class TestOperationDates:
    """Point c: a transaction is recorded on the day it was made (the operation date), never on the value date."""

    def test_the_collocamento_is_on_the_day_of_the_order_not_the_value_date(self, tmp_path_factory):
        output = run_of("full", tmp_path_factory).output
        order = one_tx(output, type="BUY", title=NEW_BOND)
        assert order.date == d("2026-02-10")  # ordered eight days before the value date

    def test_a_payment_is_on_its_operation_date_not_on_its_value_date(self, tmp_path_factory):
        assert one_tx(run_of("full", tmp_path_factory).output, type="WITHDRAWAL").date == d("2026-02-22")  # the value date is 02-24

    def test_no_transaction_of_the_set_is_dated_on_a_value_date_that_is_not_an_operation_date(self, tmp_path_factory):
        run = run_of("full", tmp_path_factory)
        securities = read_securities(run.members[ROLE_SECURITIES][0]).rows
        account = read_account(run.members[ROLE_ACCOUNT][0]).rows
        operation_days = {row.op for row in [*securities, *account]}
        value_only = {row.value for row in [*securities, *account] if row.value is not None} - operation_days
        assert value_only, "premise: the set has value dates that are nobody's operation date"
        tx_days = {tx.date for tx in run.output.transactions}
        assert not (tx_days & value_only)
        assert tx_days <= operation_days

    def test_a_table_row_is_placed_on_its_operation_date(self, tmp_path_factory):
        """The table is ordered by operation date, a pair by the securities one: the collocamento is between 02-09 and 02-12."""
        pairs = [record["securities:Data operazione"] for record in by_kind(run_of("full", tmp_path_factory).records, "pair")]
        assert [day_text(day) for day in pairs] == sorted(day_text(day) for day in pairs)
        assert pairs.index("10/02/2026") == pairs.index("09/02/2026") + 1


# =============================================================================
# 5. THE STANDALONE ACCOUNT ROWS ARE THE 1.5.0 ONES (proof 6)
# =============================================================================

#: ``(type, date, quantity, cash, title)`` of the standalone account rows of ``PARITY_ACCOUNT_ROWS``, as the 1.5.0 plugin made them.
PARITY_TRANSACTIONS = [
    ("DEPOSIT", "2026-03-02", "0", "1500.00", None),
    ("WITHDRAWAL", "2026-03-03", "0", "-25.50", None),
    ("FEE", "2026-03-04", "0", "-4.00", None),
    ("INTEREST", "2026-03-05", "0", "0.35", None),
    ("FEE", "2026-03-06", "0", "-2.00", None),
    ("TAX", "2026-03-07", "0", "-34.20", None),
    ("INTEREST", "2026-03-10", "0", "125.00", "BTP SAMPLE 1/12/2026"),
    ("TAX", "2026-03-10", "0", "-31.25", "BTP SAMPLE 1/12/2026"),
    ("DIVIDEND", "2026-03-11", "0", "12.00", "SAMPLE CORP"),
    ("WITHDRAWAL", "2026-03-12", "0", "-250.00", None),
    ("WITHDRAWAL", "2026-03-13", "0", "-9.00", None),
    ("DEPOSIT", "2026-03-14", "0", "150.00", None),
    ("FEE", "2026-03-16", "0", "-3.00", None),
]
PARITY_TAGS = {
    ("2026-03-02", "DEPOSIT"): ["import", "credit_agricole", "accredito_emolumenti"],
    ("2026-03-03", "WITHDRAWAL"): ["import", "credit_agricole", "pagamento_tramite_pos"],
    ("2026-03-04", "FEE"): ["import", "credit_agricole", "interessi_competenze"],
    ("2026-03-05", "INTEREST"): ["import", "credit_agricole", "interessi_competenze"],
    ("2026-03-06", "FEE"): ["import", "credit_agricole", "commissioni_spese"],
    ("2026-03-07", "TAX"): ["import", "credit_agricole", "commissioni_spese"],
    ("2026-03-10", "INTEREST"): ["import", "credit_agricole", "cedole_dividendi_premi_estratti"],
    ("2026-03-10", "TAX"): ["import", "credit_agricole", "cedole_dividendi_premi_estratti", "withholding_tax"],
    ("2026-03-11", "DIVIDEND"): ["import", "credit_agricole", "cedole_dividendi_premi_estratti"],
    ("2026-03-12", "WITHDRAWAL"): ["import", "credit_agricole", "compravendita_titoli_fondi_opzioni"],
    ("2026-03-13", "WITHDRAWAL"): ["import", "credit_agricole", "causale_nuova_sample"],
    ("2026-03-14", "DEPOSIT"): ["import", "credit_agricole", "giroconto_bonifico"],
    ("2026-03-16", "FEE"): ["import", "credit_agricole", "commiss_spese_su_operaz_titoli"],
}


class TestStandaloneAccountRowsKeepTheirTransactions:
    """Proof 6. The literals above are what the 1.5.0 plugin returned for the same rows (captured before the rewrite)."""

    def test_types_dates_cash_and_titles(self, tmp_path_factory):
        output = run_of("parity", tmp_path_factory).output
        rest = [item for item in tx_tuples(output) if item[0] != "SELL"]
        assert rest == expected(*PARITY_TRANSACTIONS)

    def test_tags_and_the_description_of_the_account_row(self, tmp_path_factory):
        output = run_of("parity", tmp_path_factory).output
        rows = {acc.op: acc for acc in PARITY_ACCOUNT_ROWS}
        for (day, kind), tags in PARITY_TAGS.items():
            tx = one_tx(output, type=kind, date=day)
            assert tx.tags == tags, (day, kind)
            if (day, kind) != ("2026-03-10", "TAX"):  # the withholding leg of a coupon prefixes its label
                assert tx.description == rows[day].desc, (day, kind)

    def test_a_coupon_without_a_pair_is_gross_interest_plus_tax_like_before(self, tmp_path_factory):
        output = run_of("parity", tmp_path_factory).output
        interest, tax = one_tx(output, type="INTEREST", date="2026-03-10"), one_tx(output, type="TAX", date="2026-03-10")
        assert interest.asset_id == tax.asset_id
        assert interest.description.startswith("CEDOLA:BTP SAMPLE 1/12/2026 IT0000000001")
        assert tax.description.startswith("[CEDOLE, DIVIDENDI, PREMI ESTRATTI — ritenuta]")

    def test_a_standalone_maturity_sells_the_nominal_it_derives(self, tmp_path_factory):
        output = run_of("parity", tmp_path_factory).output
        assert [item for item in tx_tuples(output) if item[0] == "SELL"] == expected(("SELL", "2026-03-15", "-1000", "1000.00", "BTP ALTRO 1/3/2026"))
        assert "account_maturity" in one_tx(output, type="SELL").tags

    def test_the_unresolved_trades_are_blockers_and_the_unallocated_charge_a_todo(self, tmp_path_factory):
        output = run_of("parity", tmp_path_factory).output
        found = {}
        for todo in output.field_todos:
            tx = output.transactions[todo.tx_index]
            found[(tx.date.isoformat(), tx.type.value)] = (todo.severity, todo.reason_code, todo.field, (todo.context or {}).get("reason"))
        assert found == {
            ("2026-03-12", "WITHDRAWAL"): ("blocker", "ca_account_trade_unresolved", "asset_id", "no_quantity"),
            ("2026-03-14", "DEPOSIT"): ("blocker", "ca_account_trade_unresolved", "asset_id", "fund_redemption"),
            ("2026-03-16", "FEE"): ("warning", "ca_account_charge_unallocated", "asset_id", None),
        }

    def test_an_unknown_causale_is_a_notice_that_names_it(self, tmp_path_factory):
        output = run_of("parity", tmp_path_factory).output
        notice = next(notice for notice in output.warnings if notice.code == "ca_unknown_causale")
        assert notice.severity == "info"
        assert notice.context["causali"] == ["CAUSALE NUOVA SAMPLE"]
        assert notice.context["row_count"] == 1


# =============================================================================
# 6. END TO END: combine -> parse -> apply_history -> compute_gap_fix (proofs 1-4)
# =============================================================================


@dataclass
class FirstImport:
    """A first import of a parse, run as the wizard runs it: the history, then the gap-fix, on a private in-memory database."""

    response: Any
    history_start: date
    kept: List[BRIMCheckpoint]
    selection: List[TXCreateItem]
    titles: Dict[str, int]


async def first_import(output: BRIMParseOutput) -> FirstImport:
    """``apply_history`` on an empty history, then ``compute_gap_fix`` with every transaction dated on or after H0.

    The wizard hides what precedes H0 (the opening brings it) and resolves every fake asset to a real one: here the real ids
    are ``REAL_ASSET_BASE`` + the rank of the fake one. The database is private to the call and closed before it returns.
    """
    plugin = ca_plugin()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    try:
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine, expire_on_commit=False) as session:
            checkpoints, verifications, history_start = await brim_report_sets.apply_history(session, broker_id=BROKER_ID, plugin=plugin, output=output)
            assert history_start is not None, "premise: a first import has an H0"
            real = {fake: REAL_ASSET_BASE + index for index, fake in enumerate(sorted(output.extracted_assets))}
            selection = [tx.model_copy(update={"asset_id": real.get(tx.asset_id, tx.asset_id)}) for tx in output.transactions if tx.date >= history_start]
            resolved = [checkpoint.model_copy(update={"positions": [position.model_copy(update={"asset_id": real[position.asset_id]}) for position in checkpoint.positions]}) for checkpoint in checkpoints]
            request = BRIMGapFixRequest(broker_id=BROKER_ID, plugin_code=PLUGIN_CODE, checkpoints=resolved, verifications=verifications, selection=selection)
            response = await compute_gap_fix(session, request)
    finally:
        await engine.dispose()
    names = names_of(output)
    return FirstImport(response, history_start, list(checkpoints), selection, {names[fake]: real_id for fake, real_id in real.items()})


def gf_checkpoint(response: Any, as_of: str) -> Any:
    found = [result for result in response.checkpoints if result.as_of == d(as_of)]
    assert len(found) == 1, f"one gap-fix result expected at {as_of}, got {[result.as_of.isoformat() for result in response.checkpoints]}"
    return found[0]


def gf_verification(response: Any, as_of: str) -> Any:
    found = [result for result in response.verifications if result.as_of == d(as_of)]
    assert len(found) == 1, f"one verification expected at {as_of}, got {[result.as_of.isoformat() for result in response.verifications]}"
    return found[0]


def gf_cash(result: Any) -> Dict[str, Tuple[Decimal, Decimal, Decimal]]:
    """``{currency: (bank, librefolio, difference)}``."""
    return {row.currency: (row.bank, row.librefolio, row.difference) for row in result.cash}


def gf_positions(result: Any, titles: Dict[str, int]) -> Dict[str, Tuple[str, Decimal, Decimal, Decimal]]:
    by_id = {real_id: title for title, real_id in titles.items()}
    return {by_id[row.asset_id]: (row.exactness, row.bank, row.librefolio, row.difference) for row in result.positions}


def gf_proposals(result: Any) -> List[Tuple[str, Optional[Decimal], date]]:
    return sorted((item.type.value, None if item.cash is None else item.cash.amount, item.date) for item in result.proposals)


def money(value: str) -> Tuple[Decimal, Decimal, Decimal]:
    """A cash row that agrees: the bank's figure on both sides, no difference."""
    return Decimal(value), Decimal(value), Decimal(0)


class TestFirstImportEndToEnd:
    """The truth points of the plugin, against the ledger a first import builds from its transactions."""

    @pytest.mark.asyncio
    async def test_the_full_set_agrees_with_the_bank_at_the_opening_and_at_both_verifications(self, tmp_path_factory):
        """Proof 1, with the cash in flight of a collocamento between the opening and the end of the month.

        The account opens at 0 and the opening position (the transfer) is held by the ledger from its own date: nothing to
        correct. The securities export states 4.443,75 on 02-15, with 2000.00 ordered and not yet booked: the ledger, which
        records the order on 02-10, holds 2443.75, and so does the truth. The last balance closes the month to the cent."""
        flow = await first_import(run_of("full", tmp_path_factory).output)
        assert flow.history_start == d("2026-01-25")
        assert [checkpoint.as_of for checkpoint in flow.kept] == [d("2026-01-31")], "the opening is kept by apply_history"
        opening = gf_checkpoint(flow.response, "2026-01-31")
        assert (opening.kind, gf_cash(opening), gf_proposals(opening)) == ("opening", {"EUR": money("0")}, [])
        assert gf_positions(opening, flow.titles) == {BOND_A: ("exact", Decimal("40000"), Decimal("40000"), Decimal(0))}
        for day, value in (("2026-02-15", "2443.75"), ("2026-02-28", "43115.13")):
            verified = gf_verification(flow.response, day)
            assert (verified.ok, gf_cash(verified)) == (True, {"EUR": money(value)}), day

    @pytest.mark.asyncio
    async def test_the_opening_survives_apply_history_when_the_first_row_is_five_days_later(self, tmp_path_factory):
        """Proof 2. The account opens on 01-31 and its first row is 02-05: with the policy ``import`` H0 is the first
        transaction, and the opening must still be a checkpoint of the import (it compares the bank with the ledger on the eve
        of the history, and the ledger is empty then, as the bank's balance is 0)."""
        run = run_of("five_days", tmp_path_factory)
        assert [checkpoint.as_of for checkpoint in run.output.checkpoints] == [d("2026-01-31")], "premise: the plugin states the opening"
        assert min(tx.date for tx in run.output.transactions) == d("2026-02-05"), "premise: the first transaction is five days after it"
        flow = await first_import(run.output)
        assert [checkpoint.as_of for checkpoint in flow.kept] == [d("2026-01-31")], "CORE: apply_history dropped the opening that precedes H0 by more than a day; the plugin does state it"
        opening = gf_checkpoint(flow.response, "2026-01-31")
        assert (gf_cash(opening), gf_proposals(opening)) == ({"EUR": money("0")}, [])
        verified = gf_verification(flow.response, "2026-02-28")
        assert (verified.ok, gf_cash(verified)) == (True, {"EUR": money("1093.75")})

    @pytest.mark.asyncio
    async def test_a_pair_that_straddles_the_opening_leaves_no_difference(self, tmp_path_factory):
        """Proof 3. Ordered on 01-29 (securities), booked on 02-02 (account): on 01-31 the ledger holds the purchase and the
        bank does not, so the opening states the bank's balance plus the cash in flight, and the difference is 0."""
        run = run_of("straddle", tmp_path_factory)
        flow = await first_import(run.output)
        assert one_tx(run.output, type="BUY").date == d("2026-01-29"), "premise: the purchase is recorded on the day of the order"
        assert flow.history_start == d("2026-01-29")
        opening = gf_checkpoint(flow.response, "2026-01-31")
        assert (gf_cash(opening), gf_proposals(opening)) == ({"EUR": money("-250.00")}, [])
        verified = gf_verification(flow.response, "2026-02-28")
        assert (verified.ok, gf_cash(verified)) == (True, {"EUR": money("750.00")})

    @pytest.mark.asyncio
    async def test_a_month_without_rows_is_one_cash_correction(self, tmp_path_factory):
        """Proof 4. January closes at 1093.75 and March opens at 1500.00, and no export covers February: 406.25 of cash the
        files do not show, proposed once, at the end of the hole. Everything else agrees with the bank."""
        flow = await first_import(run_of("hole", tmp_path_factory).output)
        gaps = [result for result in flow.response.checkpoints if result.kind == "gap"]
        assert [result.as_of for result in gaps] == [d("2026-02-28")]
        assert gf_cash(gaps[0]) == {"EUR": (Decimal("1500.00"), Decimal("1093.75"), Decimal("406.25"))}
        assert gf_proposals(gaps[0]) == [("DEPOSIT", Decimal("406.25"), d("2026-02-28"))]
        assert gf_proposals(gf_checkpoint(flow.response, "2025-12-31")) == []
        assert {verified.as_of: verified.ok for verified in flow.response.verifications} == {d("2026-01-31"): True, d("2026-03-31"): True}

    @pytest.mark.asyncio
    async def test_the_same_months_with_the_february_rows_need_no_correction(self, tmp_path_factory):
        flow = await first_import(run_of("hole_filled", tmp_path_factory).output)
        assert [result.as_of for result in flow.response.checkpoints if result.kind == "gap"] == []
        assert all(not result.proposals for result in flow.response.checkpoints)
        assert flow.response.verifications and all(verified.ok for verified in flow.response.verifications)
        assert d("2026-03-31") in {verified.as_of for verified in flow.response.verifications}

    @pytest.mark.asyncio
    async def test_securities_rows_inside_the_hole_leave_only_what_is_left_of_it(self, tmp_path_factory):
        """The coupon (+62.50) and the purchase (-100.00) of February are in the ledger, which holds 1093.75 + 62.50 - 100.00 =
        1056.25 at the end of the hole while the bank states 1500.00: the correction is 443.75, not the 406.25 of the bare hole."""
        flow = await first_import(run_of("hole_securities", tmp_path_factory).output)
        (gap,) = [result for result in flow.response.checkpoints if result.kind == "gap"]
        assert gf_cash(gap) == {"EUR": (Decimal("1500.00"), Decimal("1056.25"), Decimal("443.75"))}
        assert gf_proposals(gap) == [("DEPOSIT", Decimal("443.75"), d("2026-02-28"))]
        assert all(verified.ok for verified in flow.response.verifications)


class TestApplyHistoryKeepsTheOpening:
    """The core alone, with the policy ``import`` and no plugin of ours: does the opening survive a first row that is not the next day?

    Proof 2 asks it of the plugin's own output; this isolates the core, so that a red there is read as the core's."""

    @staticmethod
    def _output(first_row: str) -> BRIMParseOutput:
        return BRIMParseOutput(
            transactions=[TXCreateItem(broker_id=BROKER_ID, type=TransactionType.DEPOSIT, date=d(first_row), cash=Currency(code="EUR", amount=Decimal("1000.00")), tags=["import", "credit_agricole"])],
            checkpoints=[BRIMCheckpoint(as_of=d("2026-01-31"), kind="opening", cash=[BRIMTruthCash(currency="EUR", amount=Decimal("0"))])],
        )

    @staticmethod
    async def _kept(first_row: str) -> List[date]:
        plugin = SimpleNamespace(history_tag="credit_agricole", pre_checkpoint_policy="import")
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        try:
            async with engine.begin() as connection:
                await connection.run_sync(SQLModel.metadata.create_all)
            async with AsyncSession(engine, expire_on_commit=False) as session:
                kept, _verifications, _start = await brim_report_sets.apply_history(session, broker_id=BROKER_ID, plugin=plugin, output=TestApplyHistoryKeepsTheOpening._output(first_row))
        finally:
            await engine.dispose()
        return [checkpoint.as_of for checkpoint in kept]

    @pytest.mark.asyncio
    async def test_guard_an_opening_the_day_before_the_first_row_is_kept(self):
        """Guard, green today: the premise of the next test (the stub plugin is read as a plugin with the policy import)."""
        assert await self._kept("2026-02-01") == [d("2026-01-31")]

    @pytest.mark.asyncio
    async def test_an_opening_five_days_before_the_first_row_is_kept(self):
        assert await self._kept("2026-02-05") == [d("2026-01-31")]
