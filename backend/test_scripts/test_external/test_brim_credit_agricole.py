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

Every file is synthetic: written under ``tmp_path_factory`` by the builders of this module, with invented names, ISINs,
dossier numbers and amounts. No server, no database, no network, no clock: pure.

Plan: LibreFolio_developer_journal/Release_2/Phase_1/04_importTransactions/plan-phase01ImportTransactions.prompt.md,
section "W5-7 · Crédit Agricole sui report set — piano dettagliato".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import openpyxl
import pytest

from backend.app.schemas.brim import BRIMCoverage
from backend.app.schemas.common import DateRangeModel
from backend.app.services.brim import brim_report_set_core as core
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
    ROLE_ACCOUNT,
    ROLE_SECURITIES,
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
            notice = notice_of(analysis, "gap")
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
        assert "gap" not in codes(analysis)
        assert "balance_chain_broken" not in codes(analysis)
        assert analysis.zone(d("2025-07-15")) == ZONE_WINDOW

    def test_3_the_missing_month_in_an_xlsx_without_balances_does_the_same(self, work):
        analysis = work.analysis(acc=[file_a(work), file_b(work), work.acc(JULY_ROWS, "xlsx")])
        assert analysis.holes == []
        assert "gap" not in codes(analysis)

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
        assert sorted(codes(analysis)) == ["balance_chain_broken", "gap"]
        assert notice_of(analysis, "balance_chain_broken").context == {"date": "2025-10-31"}
        assert notice_of(analysis, "gap").context["amount"] == "700.00"
        assert notice_of(analysis, "gap").context["corrected"] is True  # a hole BEFORE a later broken interval keeps its correction
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
        assert [n.code for n in shape.notices] == ["gap"]
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
        notice = notice_of(analysis, "gap")
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
        assert notice_of(analysis, "gap").context["corrected"] is True


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
