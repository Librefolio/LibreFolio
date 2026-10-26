"""
Test Suite: a BRIM plugin records the DATE OF THE OPERATION, never the value / settlement date (W-B88)

The developer's principle: the date a plugin gives a transaction is the day the user made the operation (trade or booking date). The
value date — «Data valuta», «Valutadatum», «Value Date», «Settlement Date», «Date de règlement» — may only decide whether a row is
settled; it is never the date of the transaction.

These are GUARDS, green from the start: each plugin below already reads the operation date. Each one is built to be able to fail: it
asserts on a row whose two dates DIFFER (in both directions, across month and year boundaries, so a plugin that switched to the value
date — or that took the wrong one of two dates — would land on another day), found by what the row says (type, quantity, amount,
currency, description), never by position and never by a count.

What is pinned:

- A. fixture guards: every row the tests lean on really exists in its sample, with the two dates side by side, and they differ;
- B. the operation date, per plugin: ``broker_directa`` («Data operazione» vs «Data valuta»), ``broker_degiro`` («Datum» / «Date» vs
  «Valutadatum» / «Value date», Dutch and English statements), ``broker_investengine`` («Trade Date/Time» vs «Settlement Date»),
  ``broker_saxo`` («Trade Date» vs «Value Date»), ``broker_credit_agricole`` (securities «Data operazione» vs «Data valuta»; cash
  «Data Op.» vs «Data Val.»), ``broker_schwab`` («Date» with the « as of MM/DD/YYYY» suffix: the first date wins), ``broker_disnat``
  («Date de transaction» vs «Date de règlement»);
- C. the one documented exception, ``broker_disnat``: a row with no trade date (``-``, as the dividends and the fees have) falls back
  to the settlement date, because the file offers no other day for it.

Not covered here, on purpose: Avanza, Intesa and Rabobank mention «Valuta» but it means the CURRENCY (they have no value-date column);
Fineco and Danske Bank have their own date tests; ``broker_generic_csv`` is another lot.

PURE: untouched samples of ``sample_reports/``, no server, no database, no network, no clock.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.schemas.brim import BRIMParseOutput
from backend.app.services.brim.registry import BRIMProviderRegistry

# =============================================================================
# CONSTANTS
# =============================================================================

SAMPLE_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"
BROKER_ID = 1


# =============================================================================
# HELPERS
# =============================================================================


def _plugin(code: str):
    """The registered plugin ``code``; a missing one fails the test with its code."""
    BRIMProviderRegistry.auto_discover()
    plugin = BRIMProviderRegistry.get_provider_instance(code)
    assert plugin is not None, f"no BRIM plugin is registered as {code}"
    return plugin


@functools.cache
def _parse_sample(code: str, name: str) -> BRIMParseOutput:
    """The plugin's parse of an untouched sample (cached: a sample never changes inside a run)."""
    return _plugin(code).parse(SAMPLE_DIR / name, broker_id=BROKER_ID)


@functools.cache
def _physical_lines(name: str) -> Tuple[str, ...]:
    """The lines of a sample as the file has them (BOM dropped)."""
    return tuple((SAMPLE_DIR / name).read_bytes().decode("utf-8-sig").splitlines())


@dataclass(frozen=True)
class DateCase:
    """One row of a sample whose operation date and value date differ.

    ``needles`` are texts that must all sit on ONE physical line of the sample: together they identify the row and show both dates as
    the file writes them. ``tx_type`` / ``quantity`` / ``cash`` / ``currency`` / ``description_has`` identify the transaction(s) the
    plugin makes of it (``cash=None``: no cash leg). ``operation`` is the date the transaction must carry; ``other`` is the value /
    settlement date it must NOT carry.
    """

    id: str
    plugin: str
    sample: str
    needles: Tuple[str, ...]
    tx_type: str
    quantity: str
    cash: Optional[str]
    currency: Optional[str]
    operation: date
    other: date
    description_has: Optional[str] = None


def _matches(out: BRIMParseOutput, case: DateCase):
    """The transactions of ``out`` that the case identifies by content (never by position)."""
    found = []
    for tx in out.transactions:
        if tx.type.value != case.tx_type or tx.quantity != Decimal(case.quantity):
            continue
        if case.cash is None:
            if tx.cash is not None:
                continue
        elif tx.cash is None or tx.cash.amount != Decimal(case.cash) or tx.cash.code != case.currency:
            continue
        if case.description_has is not None and case.description_has not in (tx.description or ""):
            continue
        found.append(tx)
    return found


def _line_with(sample: str, needles: Tuple[str, ...]) -> Optional[str]:
    return next((line for line in _physical_lines(sample) if all(needle in line for needle in needles)), None)


# =============================================================================
# THE CASES — every row below has an operation date and a value date that differ
# =============================================================================

CASES: List[DateCase] = [
    # --- Directa: «Data operazione» (1st column) vs «Data valuta» (2nd) -------------------------------------------------------
    DateCase(
        "directa-buy-value-two-days-later",
        "broker_directa",
        "directa-export.csv",
        ("02-12-2024,04-12-2024,Acquisto,ICOV,IE00B3B8Q275",),
        "BUY",
        "3",
        "-431.04",
        "EUR",
        date(2024, 12, 2),
        date(2024, 12, 4),
    ),
    DateCase(
        "directa-sell-value-two-days-later",
        "broker_directa",
        "directa-export.csv",
        ("29-05-2024,31-05-2024,Vendita,AV,IT0005366601",),
        "SELL",
        "-200",
        "666",
        "EUR",
        date(2024, 5, 29),
        date(2024, 5, 31),
    ),
    DateCase(
        "directa-coupon-value-three-days-later",
        "broker_directa",
        "directa-export.csv",
        ("02-12-2024,05-12-2024,Cedola obb.,M.510999",),
        "INTEREST",
        "0",
        "24.38",
        "EUR",
        date(2024, 12, 2),
        date(2024, 12, 5),
        "BTP VALORE",
    ),
    DateCase(
        "directa-coupon-value-one-day-EARLIER",
        "broker_directa",
        "directa-export.csv",
        ("06-12-2024,05-12-2024,Cedola obb.,M.511185",),
        "INTEREST",
        "0",
        "71.25",
        "EUR",
        date(2024, 12, 6),
        date(2024, 12, 5),
        "ALPER FX",
    ),
    # --- DEGIRO, Dutch statement: «Datum» vs «Valutadatum» -----------------------------------------------------------------
    DateCase(
        "degiro-nl-dividend-value-one-day-earlier",
        "broker_degiro",
        "degiro-export.csv",
        ("16-12-2022,07:27,15-12-2022,CLEARWAY ENERGY INC.,US18539C2044,Dividend",),
        "DIVIDEND",
        "0",
        "0.73",
        "USD",
        date(2022, 12, 16),
        date(2022, 12, 15),
    ),
    DateCase(
        "degiro-nl-deposit-value-one-day-earlier",
        "broker_degiro",
        "degiro-export.csv",
        ("17-12-2022,09:51,16-12-2022,,,iDEAL Deposit",),
        "DEPOSIT",
        "0",
        "27.80",
        "EUR",
        date(2022, 12, 17),
        date(2022, 12, 16),
    ),
    DateCase(
        "degiro-nl-fx-leg-value-one-day-earlier",
        "broker_degiro",
        "degiro-export.csv",
        ("17-12-2022,08:37,16-12-2022,,,Valuta Creditering",),
        "FX_CONVERSION",
        "0",
        "1.28",
        "EUR",
        date(2022, 12, 17),
        date(2022, 12, 16),
    ),
    # --- DEGIRO, English statement: «Date» vs «Value date» -----------------------------------------------------------------
    DateCase(
        "degiro-en-dividend-value-three-days-earlier",
        "broker_degiro",
        "degiro-account-en.csv",
        ("15-09-2025;09:12;12-09-2025;APPLE INC;US0378331005;Dividend;",),
        "DIVIDEND",
        "0",
        "4.80",
        "USD",
        date(2025, 9, 15),
        date(2025, 9, 12),
    ),
    DateCase(
        "degiro-en-interest-value-across-the-month",
        "broker_degiro",
        "degiro-account-en.csv",
        ("03-10-2025;07:15;30-09-2025;;;Flatex Interest Income",),
        "INTEREST",
        "0",
        "3.47",
        "CZK",
        date(2025, 10, 3),
        date(2025, 9, 30),
    ),
    DateCase(
        "degiro-en-fee-value-across-the-month",
        "broker_degiro",
        "degiro-account-en.csv",
        ("02-07-2025;07:16;30-06-2025;;;DEGIRO Exchange Connection Fee",),
        "FEE",
        "0",
        "-2.50",
        "EUR",
        date(2025, 7, 2),
        date(2025, 6, 30),
    ),
    # --- InvestEngine: «Trade Date/Time» vs «Settlement Date» --------------------------------------------------------------
    DateCase(
        "investengine-buy-settles-four-days-later",
        "broker_investengine",
        "investengine-export.csv",
        ("2.594594,£116.00,£300.96,23/01/25 15:00:08,27/01/25",),
        "BUY",
        "2.594594",
        "-300.96",
        "GBP",
        date(2025, 1, 23),
        date(2025, 1, 27),
    ),
    DateCase(
        "investengine-buy-settles-across-the-year",
        "broker_investengine",
        "investengine-export.csv",
        ("2.699055,£110.79,£299.04,23/12/24 15:18:12,27/12/24",),
        "BUY",
        "2.699055",
        "-299.04",
        "GBP",
        date(2024, 12, 23),
        date(2024, 12, 27),
    ),
    DateCase(
        "investengine-sell-settles-across-the-month",
        "broker_investengine",
        "investengine-export.csv",
        ("10.696127,£102.22,£1093.41,30/04/25 14:13:11,02/05/25",),
        "SELL",
        "-10.696127",
        "1093.41",
        "GBP",
        date(2025, 4, 30),
        date(2025, 5, 2),
    ),
    # --- Saxo: «Trade Date» vs «Value Date» --------------------------------------------------------------------------------
    DateCase(
        "saxo-buy-value-next-day",
        "broker_saxo",
        "saxo-export.csv",
        ("30-Dec-2024,31-Dec-2024,Trade,NVIDIA Corp.",),
        "BUY",
        "3",
        "-405.55",
        "USD",
        date(2024, 12, 30),
        date(2024, 12, 31),
    ),
    DateCase(
        "saxo-buy-value-across-the-year",
        "broker_saxo",
        "saxo-export.csv",
        ("30-Dec-2024,02-Jan-2025,Trade,Vanguard FTSE All-World UCITS ETF", "Buy 17 @ 139.74 USD"),
        "BUY",
        "17",
        "-2379.35",
        "USD",
        date(2024, 12, 30),
        date(2025, 1, 2),
    ),
    DateCase(
        "saxo-dutch-trade-value-four-days-later",
        "broker_saxo",
        "saxo-export.csv",
        ("16-jan-2025,20-jan-2025,Transactie,Vanguard S&P 500 Dist UCITS ETF",),
        "BUY",
        "1.5",
        "-110",
        "EUR",
        date(2025, 1, 16),
        date(2025, 1, 20),
    ),
    # --- Crédit Agricole, securities export: «Data operazione» vs «Data valuta» (last column) --------------------------------
    DateCase(
        "credit-agricole-securities-buy-value-four-days-later",
        "broker_credit_agricole",
        "credit_agricole-export.csv",
        ("24/07/2025;BTP 01/03/35 3,35%;EUR;ACQ.CONT.SU MERC.", ";28/07/2025"),
        "BUY",
        "50000",
        "-50683.13",
        "EUR",
        date(2025, 7, 24),
        date(2025, 7, 28),
        "ACQ.CONT.SU MERC.",
    ),
    DateCase(
        "credit-agricole-securities-buy-auto-cash-leg-has-the-same-day",
        "broker_credit_agricole",
        "credit_agricole-export.csv",
        ("24/07/2025;BTP 01/03/35 3,35%;EUR;ACQ.CONT.SU MERC.", ";28/07/2025"),
        "DEPOSIT",
        "0",
        "50683.13",
        "EUR",
        date(2025, 7, 24),
        date(2025, 7, 28),
        "Auto cash for BUY BTP 01/03/35",
    ),
    DateCase(
        "credit-agricole-securities-subscription-value-one-day-EARLIER",
        "broker_credit_agricole",
        "credit_agricole-export.csv",
        ("07/11/2025;AMUNDI PIO GLOB EQ G;EUR;SICAV: SOTTOSCR", ";06/11/2025"),
        "BUY",
        "1843.575",
        "-20129.44",
        "EUR",
        date(2025, 11, 7),
        date(2025, 11, 6),
    ),
    DateCase(
        "credit-agricole-securities-redemption-value-next-day",
        "broker_credit_agricole",
        "credit_agricole-export.csv",
        ("10/11/2025;AMUNDI PRIMO INV LC;EUR;FONDI: RIMBORSO", ";11/11/2025"),
        "SELL",
        "-1867.178",
        "9984.47",
        "EUR",
        date(2025, 11, 10),
        date(2025, 11, 11),
    ),
    DateCase(
        "credit-agricole-securities-transfer-in-value-six-days-EARLIER",
        "broker_credit_agricole",
        "credit_agricole-export.csv",
        ("13/06/2024;AMUNDI PRIMO INV LC;EUR;VERS.TITOLI", ";618.458;", ";07/06/2024"),
        "ADJUSTMENT",
        "618.458",
        None,
        None,
        date(2024, 6, 13),
        date(2024, 6, 7),
    ),
    # --- Crédit Agricole, cash account: «Data Op.» (1st column) vs «Data Val.» (2nd) -------------------------------------------
    DateCase(
        "credit-agricole-cash-tax-value-two-weeks-EARLIER",
        "broker_credit_agricole",
        "credit_agricole-conti.csv",
        ("14/07/2026;30/06/2026;COMMISS./SPESE SU OPERAZ. TITOLI;ADDEBITO CAPITAL GAIN",),
        "TAX",
        "0",
        "-21.42",
        "EUR",
        date(2026, 7, 14),
        date(2026, 6, 30),
        "ADDEBITO CAPITAL GAIN",
    ),
    # --- Schwab: «Date» = «MM/DD/YYYY as of MM/DD/YYYY», the FIRST date wins ------------------------------------------------
    DateCase(
        "schwab-stock-split-as-of-three-days-EARLIER",
        "broker_schwab",
        "schwab-export.csv",
        ('"07/15/2024 as of 07/12/2024","Stock Split","AVGO"',),
        "ADJUSTMENT",
        "9",
        None,
        None,
        date(2024, 7, 15),
        date(2024, 7, 12),
        "BROADCOM",
    ),
    DateCase(
        "schwab-spin-off-as-of-three-days-EARLIER",
        "broker_schwab",
        "schwab-export.csv",
        ('"08/22/2022 as of 08/19/2022","Spin-off","APE"',),
        "ADJUSTMENT",
        "344",
        None,
        None,
        date(2022, 8, 22),
        date(2022, 8, 19),
        "AMC ENTERTAINMENT",
    ),
    # --- Disnat: «Date de transaction» vs «Date de règlement» -----------------------------------------------------------------
    DateCase(
        "disnat-buy-settles-next-day",
        "broker_disnat",
        "disnat-export.csv",
        ("2025-07-31,2025-08-01,ACHAT,Actions,VEQT-C",),
        "BUY",
        "10",
        "-493.8",
        "CAD",
        date(2025, 7, 31),
        date(2025, 8, 1),
    ),
    DateCase(
        "disnat-sell-settles-four-days-later",
        "broker_disnat",
        "disnat-export.csv",
        ("2025-08-01,2025-08-05,VENTE,Actions,CASH-C",),
        "SELL",
        "-10",
        "500",
        "CAD",
        date(2025, 8, 1),
        date(2025, 8, 5),
    ),
    DateCase(
        "disnat-buy-settles-across-the-month",
        "broker_disnat",
        "disnat-export.csv",
        ("2024-11-29,2024-12-02,ACHAT,Actions,CASH-C",),
        "BUY",
        "2",
        "-100",
        "CAD",
        date(2024, 11, 29),
        date(2024, 12, 2),
    ),
]

# Disnat rows with NO trade date («-»): the settlement date is the only day the file gives, so it is the transaction's date.
# ``operation`` is the settlement date here and ``other`` repeats it: the fallback has no second day to be told apart from.
FALLBACK_CASES: List[DateCase] = [
    DateCase(
        "disnat-dividend-without-trade-date",
        "broker_disnat",
        "disnat-export.csv",
        ("-,2025-09-29,DIVIDENDE SOCIÉTÉ FIDUCIE,Actions,XIC",),
        "DIVIDEND",
        "0",
        "2.53",
        "CAD",
        date(2025, 9, 29),
        date(2025, 9, 29),
        "ISHRS CORE S&P/TSX CAPPED",
    ),
    DateCase(
        "disnat-fee-without-trade-date",
        "broker_disnat",
        "disnat-export.csv",
        ("-,2025-09-04,FRAIS,-,-,FRAIS REER 2025",),
        "FEE",
        "0",
        "-100",
        "CAD",
        date(2025, 9, 4),
        date(2025, 9, 4),
        "FRAIS REER 2025",
    ),
    DateCase(
        "disnat-late-payment-interest-without-trade-date",
        "broker_disnat",
        "disnat-export.csv",
        ("-,2025-07-30,INTÉRÊTS VERSEMENT TARDIF",),
        "INTEREST",
        "0",
        "0.17",
        "CAD",
        date(2025, 7, 30),
        date(2025, 7, 30),
        "00101 IQEINT",
    ),
]


# =============================================================================
# A. FIXTURE GUARDS — they check this file's expectations against the samples, never the plugin
# =============================================================================


class TestFixtureGuards:
    """A — the rows the tests lean on exist in the samples, and their two dates really differ."""

    @pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
    def test_the_row_is_in_the_sample_and_its_dates_differ(self, case: DateCase):
        assert case.operation != case.other, "a guard on a row whose two dates agree could never fail"
        assert _line_with(case.sample, case.needles) is not None, f"{case.sample}: no line holds {case.needles}"

    @pytest.mark.parametrize("case", FALLBACK_CASES, ids=lambda c: c.id)
    def test_the_fallback_row_is_in_the_sample_with_no_trade_date(self, case: DateCase):
        line = _line_with(case.sample, case.needles)
        assert line is not None, f"{case.sample}: no line holds {case.needles}"
        assert line.startswith("-,"), "the trade date of this row is the placeholder '-'"


# =============================================================================
# B. THE OPERATION DATE, PER PLUGIN
# =============================================================================


class TestOperationDate:
    """B — the transaction carries the day of the operation, not the value / settlement day of the same row."""

    @pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
    def test_the_transaction_date_is_the_operation_date(self, case: DateCase):
        found = _matches(_parse_sample(case.plugin, case.sample), case)

        assert found, f"{case.plugin} gave no {case.tx_type} for {case.needles} (quantity {case.quantity}, cash {case.cash} {case.currency})"
        assert {tx.date for tx in found} == {case.operation}, f"{case.id}: the operation date is {case.operation}, the value / settlement date {case.other}; got {sorted({tx.date for tx in found})}"

    @pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
    def test_the_value_date_is_never_used(self, case: DateCase):
        found = _matches(_parse_sample(case.plugin, case.sample), case)

        assert found, f"{case.plugin} gave no {case.tx_type} for {case.needles}"
        assert all(tx.date != case.other for tx in found), f"{case.id}: a transaction took the value / settlement date {case.other}"


# =============================================================================
# C. THE ONE DOCUMENTED EXCEPTION — DISNAT, a row with no trade date
# =============================================================================


class TestDisnatSettlementFallback:
    """C — Disnat leaves the trade date at ``-`` for dividends, fees, taxes and interest: the settlement date then dates the row, and ONLY then (B pins the dated rows)."""

    @pytest.mark.parametrize("case", FALLBACK_CASES, ids=lambda c: c.id)
    def test_a_row_with_no_trade_date_takes_the_settlement_date(self, case: DateCase):
        found = _matches(_parse_sample(case.plugin, case.sample), case)

        assert found, f"{case.plugin} gave no {case.tx_type} for {case.needles}"
        assert {tx.date for tx in found} == {case.operation}
