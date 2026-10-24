"""
Test Suite: four BRIM plugins IMPORT the rows with an economic effect they used to leave out (W-B87 block 1, lot W5-2)

Until now ``broker_etoro``, ``broker_swissquote``, ``broker_revolut`` and ``broker_trading212`` listed some rows in the shared notice
``rows_not_recognized`` (with ``report_issue``) and imported nothing from them. The developer decided (no data cleaning, the plugins stay
in beta, a plugin never creates an asset event) that these rows become real transactions:

- A. eToro: an ``Overnight fee`` is one FEE (cash negative, no asset, quantity 0); an ``SDRT`` row is one TAX on the asset of the ticker in
  ``Details`` (the same fake asset id a dividend of that ticker has); an ``Overnight refund`` STAYS a listed row (the developer's question
  on it is pending), so the notice counts only the refund;
- B. Swissquote: a ``Forex credit`` + ``Forex debit`` pair (same ``Order #`` and timestamp, nothing in ``Costs``) is two FX_CONVERSION legs
  sharing a ``link_uuid``, cash = ``Net Amount`` signed, in the row's currency; a lone leg, an order with more than two legs and a leg that
  carries ``Costs`` are still listed;
- C. Revolut Invest: a ``STOCK SPLIT`` whose ``Quantity`` is a positive number is one ADJUSTMENT of the shares ADDED, cost basis 0, with a
  ``possible_split`` field todo; a split without a readable positive quantity is still listed;
- D. Trading 212: a ``Stock split close`` + ``Stock split open`` pair of one ISIN (``Time`` within 2 seconds) whose open shares are MORE than
  the close ones is one ADJUSTMENT of the difference, cost basis 0, with the same todo; every other split row (reverse split, no partner,
  equal) is still listed; ``Stock distribution`` and ``Currency conversion`` are unchanged.

Every row is found by what it says (type, ticker or ISIN, amount, date), never by position and never by a total count. The files with
a synthetic case are built in ``tmp_path`` from the real header of the sample. The plugins' versions, the counts of the samples and the
sample listings are pinned in ``test_brim_row_skips.py`` (the old expectations of those rows were changed there).

PURE: samples and files written in ``tmp_path``, no server, no database, no network, no clock.
"""

from __future__ import annotations

import csv
import functools
import io
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import List, Mapping, Optional, Sequence, Tuple, Union

import pytest

from backend.app.config import PROJECT_ROOT
from backend.app.db.models import TransactionType
from backend.app.schemas.brim import BRIMFieldTodo, BRIMNotice, BRIMParseOutput, is_fake_asset_id
from backend.app.schemas.common import Currency
from backend.app.schemas.transactions.transactions import TXCreateItem
from backend.app.services.brim.registry import BRIMProviderRegistry
from backend.app.services.transactions.validation import TransactionValidationMixin

# =============================================================================
# CONSTANTS
# =============================================================================

SAMPLE_DIR = PROJECT_ROOT / "backend" / "app" / "services" / "brim_providers" / "sample_reports"
BROKER_ID = 1
ROWS_NOT_RECOGNIZED = "rows_not_recognized"
POSSIBLE_SPLIT = "possible_split"

ETORO = "broker_etoro"
SWISSQUOTE = "broker_swissquote"
REVOLUT = "broker_revolut"
TRADING212 = "broker_trading212"

Row = Union[Sequence[str], Mapping[str, str]]


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
def _sample(code: str, name: str) -> BRIMParseOutput:
    """The plugin's parse of an untouched sample (cached: a sample never changes inside a run)."""
    return _plugin(code).parse(SAMPLE_DIR / name, broker_id=BROKER_ID)


def _physical_lines(name: str) -> List[str]:
    """The lines of a sample as the file has them (BOM dropped), the first one being line 1."""
    return (SAMPLE_DIR / name).read_bytes().decode("utf-8-sig").splitlines()


def _header(name: str, delimiter: str) -> List[str]:
    return next(csv.reader([_physical_lines(name)[0]], delimiter=delimiter))


def _cells(header: Sequence[str], row: Row) -> List[str]:
    """A row's cells: as given, or by column name under ``header`` (a column the dict does not name is empty)."""
    if not isinstance(row, Mapping):
        return list(row)
    unknown = set(row) - set(header)
    assert not unknown, f"the case names columns the header does not have: {sorted(unknown)}"
    return [row.get(name, "") for name in header]


def _write_rows(folder: Path, sample: str, rows: Sequence[Row], delimiter: str) -> Tuple[Path, List[int]]:
    """The real header of ``sample`` plus ``rows``; returns the file and the 1-based file line of every row."""
    header = _header(sample, delimiter)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=delimiter, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(_cells(header, row))
    path = folder / sample
    path.write_text(buffer.getvalue(), encoding="utf-8")
    return path, [index + 2 for index in range(len(rows))]


def _lines_of(out: BRIMParseOutput, code: str) -> List[int]:
    """Every file line the notices of ``code`` list, sorted."""
    return sorted(number for notice in out.warnings if notice.code == code for evidence in notice.evidence for number in evidence.row_numbers)


def _notices(out: BRIMParseOutput, code: str) -> List[BRIMNotice]:
    return [notice for notice in out.warnings if notice.code == code]


def _find(out: BRIMParseOutput, tx_type: TransactionType, *, code: Optional[str] = None, amount: Optional[Decimal] = None, day: Optional[date] = None) -> List[TXCreateItem]:
    """The transactions of ``tx_type`` with this cash currency, cash amount and date (the filters that are None are not applied)."""
    found = []
    for tx in out.transactions:
        if tx.type != tx_type:
            continue
        if (code is not None or amount is not None) and tx.cash is None:
            continue
        if code is not None and tx.cash.code != code:
            continue
        if amount is not None and tx.cash.amount != amount:
            continue
        if day is not None and tx.date != day:
            continue
        found.append(tx)
    return found


def _adjustments(out: BRIMParseOutput) -> List[Tuple[int, TXCreateItem]]:
    """Every ADJUSTMENT of the output with its index in ``transactions``."""
    return [(index, tx) for index, tx in enumerate(out.transactions) if tx.type == TransactionType.ADJUSTMENT]


def _todos_of(out: BRIMParseOutput, tx_index: int) -> List[BRIMFieldTodo]:
    return [todo for todo in out.field_todos if todo.tx_index == tx_index]


def _assert_listed(out: BRIMParseOutput, lines: Sequence[int], *, reason_has: Optional[str] = None) -> None:
    """The file lines are exactly what ``rows_not_recognized`` lists: one warning that asks for a report, its count the number of rows."""
    notices = _notices(out, ROWS_NOT_RECOGNIZED)
    assert len(notices) == 1, f"expected one notice {ROWS_NOT_RECOGNIZED}; the parse gives {[(n.code, _lines_of(out, n.code)) for n in out.warnings]}"
    (notice,) = notices
    assert _lines_of(out, ROWS_NOT_RECOGNIZED) == sorted(lines), f"{ROWS_NOT_RECOGNIZED} lists {_lines_of(out, ROWS_NOT_RECOGNIZED)}, expected {sorted(lines)}"
    assert notice.severity == "warning" and (notice.context or {}).get("report_issue") is True
    assert (notice.context or {}).get("count") == len(lines)
    if reason_has:
        reasons = [row[-1].lower() for evidence in notice.evidence for row in evidence.rows]
        assert all(reason_has in reason for reason in reasons), f"the reasons {reasons} must name {reason_has!r}"


def _assert_not_listed(out: BRIMParseOutput, *lines: int) -> None:
    listed = set(_lines_of(out, ROWS_NOT_RECOGNIZED))
    assert not listed & set(lines), f"lines {sorted(listed & set(lines))} are still listed in {ROWS_NOT_RECOGNIZED}"


def _assert_evidence_holds(todo: BRIMFieldTodo, *texts: str) -> None:
    """The todo shows its working: tables with a title, a comment and rows as wide as their headers, holding the source row's cells."""
    assert todo.evidence, f"{todo.reason_code}: no evidence"
    for evidence in todo.evidence:
        assert evidence.title and evidence.title.strip(), f"{todo.reason_code}: evidence with no title"
        assert evidence.comment and evidence.comment.strip(), f"{todo.reason_code}: evidence with no comment"
        assert all(len(row) == len(evidence.headers) for row in evidence.rows), f"{todo.reason_code}: evidence row width does not match the headers"
    cells = [cell.lower() for evidence in todo.evidence for row in evidence.rows for cell in row]
    for text in texts:
        assert any(text.lower() in cell for cell in cells), f"{todo.reason_code}: no evidence cell holds {text!r}: {cells}"


def _assert_possible_split(out: BRIMParseOutput, tx_index: int, context: Mapping[str, str], *evidence_texts: str) -> None:
    """Exactly one todo for the transaction: ``asset_event_id``, a warning, ``possible_split``, the context given (as strings) and the source row."""
    todos = _todos_of(out, tx_index)
    assert len(todos) == 1, f"transaction {tx_index} has {len(todos)} field todo(s): {[(t.field, t.reason_code) for t in todos]}"
    (todo,) = todos
    assert (todo.field, todo.severity, todo.reason_code) == ("asset_event_id", "warning", POSSIBLE_SPLIT)
    assert todo.message.strip(), "an English fallback message"
    assert todo.context is not None and {key: todo.context.get(key) for key in context} == dict(context), f"context {todo.context}, expected at least {dict(context)}"
    _assert_evidence_holds(todo, *evidence_texts)


# =============================================================================
# A. eToro
# =============================================================================

ETORO_SAMPLE = "etoro-export.csv"
ETORO_FILE_CURRENCY = "USD"  # the currency a FEE row takes today (``_parse_ticker_from_details`` answers USD when the ticker has none)


def _etoro_row(day_time: str, kind: str, details: str, amount: str, **more: str) -> Mapping[str, str]:
    return {"Date": day_time, "Type": kind, "Details": details, "Amount": amount, "Units": "-", "Position ID": "1", "Asset type": "Stocks", **more}


class TestEtoroOvernightFee:
    """A — an ``Overnight fee`` is a cost the account paid: one FEE of the absolute amount, negative, in the file's currency."""

    def test_premise_a_withdrawal_conversion_fee_is_a_fee_in_the_file_currency(self):
        """Guard (green today and after): the currency and the sign of a FEE of this file are the ones the overnight fees must copy."""
        out = _sample(ETORO, ETORO_SAMPLE)

        fees = _find(out, TransactionType.FEE, code=ETORO_FILE_CURRENCY, amount=Decimal("-1.36"), day=date(2024, 1, 3))

        assert len(fees) == 1, "presence barrier: the withdrawal conversion fee of the sample is one FEE in USD"

    @pytest.mark.parametrize(("day", "amount"), [(date(2020, 4, 15), "-0.10"), (date(2020, 5, 19), "-0.31")], ids=["15-04-2020 (0,10)", "19-05-2020 (0,31)"])
    def test_an_overnight_fee_row_is_one_fee_without_an_asset(self, day: date, amount: str):
        out = _sample(ETORO, ETORO_SAMPLE)

        fees = _find(out, TransactionType.FEE, code=ETORO_FILE_CURRENCY, amount=Decimal(amount), day=day)

        assert len(fees) == 1, f"the overnight fee of {day} ({amount} {ETORO_FILE_CURRENCY}) gives {len(fees)} FEE transaction(s)"
        fee = fees[0]
        assert (fee.quantity, fee.asset_id, fee.broker_id) == (Decimal("0"), None, BROKER_ID)
        assert fee.cash == Currency(code=ETORO_FILE_CURRENCY, amount=Decimal(amount))

    def test_a_positive_overnight_fee_amount_is_still_a_cost(self, tmp_path: Path):
        """The file's brackets mean negative, but the type decides the sign: a fee written as 0,25 is also -0.25."""
        path, (line,) = _write_rows(tmp_path, ETORO_SAMPLE, [_etoro_row("15/04/2021 00:46:41", "Overnight fee", "Daily", "0,25", **{"Asset type": "CFD"})], ",")

        out = _plugin(ETORO).parse(path, broker_id=BROKER_ID)

        fees = _find(out, TransactionType.FEE, code=ETORO_FILE_CURRENCY, amount=Decimal("-0.25"), day=date(2021, 4, 15))
        assert len(fees) == 1, f"line {line} gives {len(fees)} FEE transaction(s): {[(t.type, t.cash) for t in out.transactions]}"
        _assert_not_listed(out, line)


class TestEtoroSdrt:
    """A — ``SDRT`` (UK stamp duty) is a tax paid on the asset of ``Details``: one TAX, negative."""

    def test_the_sdrt_row_is_one_tax_on_the_asset_of_its_ticker(self):
        out = _sample(ETORO, ETORO_SAMPLE)

        taxes = _find(out, TransactionType.TAX, code="USD", amount=Decimal("-6.97"), day=date(2025, 7, 10))

        assert len(taxes) == 1, f"the SDRT row gives {len(taxes)} TAX transaction(s)"
        tax = taxes[0]
        assert (tax.quantity, tax.broker_id) == (Decimal("0"), BROKER_ID)
        assert tax.asset_id is not None and is_fake_asset_id(tax.asset_id), "the TAX points at a fake asset"
        assert out.extracted_assets[tax.asset_id].extracted_symbol == "HNKE"

    def test_the_tax_takes_the_fake_asset_a_dividend_of_the_same_ticker_has(self, tmp_path: Path):
        rows = [
            _etoro_row("02/07/2025 00:10:33", "Dividend", "HNKE/USD", "0.17", **{"Position ID": "11"}),
            _etoro_row("03/07/2025 00:10:33", "Dividend", "NKE/USD", "0.16", **{"Position ID": "12"}),
            _etoro_row("10/07/2025 15:15:01", "SDRT", "HNKE/USD", "(6.97)", **{"Position ID": "13"}),
        ]
        path, (_, _, sdrt_line) = _write_rows(tmp_path, ETORO_SAMPLE, rows, ",")

        out = _plugin(ETORO).parse(path, broker_id=BROKER_ID)

        taxes = _find(out, TransactionType.TAX, code="USD", amount=Decimal("-6.97"), day=date(2025, 7, 10))
        assert len(taxes) == 1, f"the SDRT row (line {sdrt_line}) gives {len(taxes)} TAX transaction(s)"
        tax = taxes[0]
        dividends = {out.extracted_assets[t.asset_id].extracted_symbol: t.asset_id for t in out.transactions if t.type == TransactionType.DIVIDEND}
        assert tax.asset_id == dividends["HNKE"], "same ticker, same fake asset id"
        assert dividends["HNKE"] != dividends["NKE"], "another ticker, another fake asset id"
        _assert_not_listed(out, sdrt_line)


class TestEtoroOvernightRefund:
    """A — guard: the refund is not imported yet (the developer's question is pending); it is the only row the notice counts."""

    def test_the_refund_is_not_a_transaction(self):
        out = _sample(ETORO, ETORO_SAMPLE)

        refunded = [tx for tx in out.transactions if tx.date == date(2020, 5, 20) and tx.cash is not None and tx.cash.amount == Decimal("0.21")]

        assert refunded == [], f"the refund of 0,21 on 20/05/2020 is imported as {[(t.type, t.cash) for t in refunded]}"

    def test_the_refund_stays_in_the_notice(self):
        """Guard (green today and after): the refund line is listed, with a reason that names it."""
        out = _sample(ETORO, ETORO_SAMPLE)
        refund_line = next(number for number, line in enumerate(_physical_lines(ETORO_SAMPLE), start=1) if "Overnight refund" in line)

        assert refund_line in _lines_of(out, ROWS_NOT_RECOGNIZED), f"presence barrier: the refund (line {refund_line}) is in no notice"
        notice = _notices(out, ROWS_NOT_RECOGNIZED)[0]
        evidence = notice.evidence[0]
        reason = evidence.rows[evidence.row_numbers.index(refund_line)][-1].lower()
        assert "overnight refund" in reason

    def test_the_notice_counts_only_the_refund(self):
        """The fees and the SDRT row are transactions now: the notice lists the refund alone, and its count says so."""
        out = _sample(ETORO, ETORO_SAMPLE)
        refund_line = next(number for number, line in enumerate(_physical_lines(ETORO_SAMPLE), start=1) if "Overnight refund" in line)

        _assert_listed(out, [refund_line])


# =============================================================================
# B. Swissquote
# =============================================================================

SQ_SAMPLE = "swissquote-export.csv"
SQ_DAY = date(2022, 8, 23)

# The two forex orders of the sample: credit (currency, Net Amount), debit (currency, Net Amount), the day.
SQ_SAMPLE_PAIRS = {
    "order 114723639": (("EUR", "1995.39"), ("USD", "-2000.00"), date(2022, 8, 23)),
    "order 113882551": (("CHF", "100000.00"), ("USD", "-106017.30"), date(2022, 8, 9)),
}

_SQ_BUY = {
    "Date": "10-08-2022 15:30:02",
    "Order #": "113947121",
    "Transaction": "Buy",
    "Symbol": "ORFN",
    "Name": "CONSTRAINED CAPITAL ESG ORPHAN",
    "ISIN": "US8863645383",
    "Quantity": "200.0",
    "Unit price": "19.85",
    "Costs": "5.96",
    "Accrued Interest": "0.00",
    "Net Amount": "-3975.96",
    "Balance": "168660.08",
    "Currency": "USD",
}


def _sq_leg(kind: str, order: str, net: str, currency: str, *, stamp: str = "23-08-2022 12:00:25", costs: str = "0.00") -> Mapping[str, str]:
    """A ``Forex credit`` / ``Forex debit`` row; the quantity and the unit price are the ones of the sample (1.0 and the converted amount)."""
    return {
        "Date": stamp,
        "Order #": order,
        "Transaction": f"Forex {kind}",
        "Quantity": "1.0",
        "Unit price": str(abs(Decimal(net))),
        "Costs": costs,
        "Accrued Interest": "0.00",
        "Net Amount": net,
        "Balance": "1000.00",
        "Currency": currency,
    }


def _sq_parse(tmp_path: Path, legs: Sequence[Mapping[str, str]]) -> Tuple[BRIMParseOutput, List[int]]:
    """A file with a normal Buy (line 2) and the legs (lines 3 onward); returns the parse and the line of every leg."""
    path, lines = _write_rows(tmp_path, SQ_SAMPLE, [_SQ_BUY, *legs], ";")
    return _plugin(SWISSQUOTE).parse(path, broker_id=BROKER_ID), lines[1:]


def _fx_legs(out: BRIMParseOutput) -> List[TXCreateItem]:
    return [tx for tx in out.transactions if tx.type == TransactionType.FX_CONVERSION]


def _pair_of(out: BRIMParseOutput, credit: Tuple[str, str], debit: Tuple[str, str], day: date) -> Tuple[TXCreateItem, TXCreateItem]:
    """The two legs of one pair, found by currency, amount and date; fails when either is missing or ambiguous."""
    credits = _find(out, TransactionType.FX_CONVERSION, code=credit[0], amount=Decimal(credit[1]), day=day)
    debits = _find(out, TransactionType.FX_CONVERSION, code=debit[0], amount=Decimal(debit[1]), day=day)
    assert (len(credits), len(debits)) == (1, 1), f"legs {credit} / {debit} on {day}: {len(credits)} credit leg(s), {len(debits)} debit leg(s)"
    return credits[0], debits[0]


class TestSwissquoteForexPairs:
    """B — a credit leg and a debit leg of one order are one currency conversion: two linked FX_CONVERSION transactions."""

    @pytest.mark.parametrize("order", sorted(SQ_SAMPLE_PAIRS))
    def test_a_sample_pair_is_two_linked_legs_with_the_signed_net_amount(self, order: str):
        credit, debit, day = SQ_SAMPLE_PAIRS[order]
        out = _sample(SWISSQUOTE, SQ_SAMPLE)

        first, second = _pair_of(out, credit, debit, day)

        assert first.link_uuid and first.link_uuid == second.link_uuid, f"{order}: the legs must share a non-empty link_uuid ({first.link_uuid!r}, {second.link_uuid!r})"
        assert len([tx for tx in out.transactions if tx.link_uuid == first.link_uuid]) == 2, f"{order}: exactly two transactions carry the link_uuid"
        assert (first.quantity, second.quantity) == (Decimal("0"), Decimal("0"))
        assert (first.asset_id, second.asset_id) == (None, None)
        assert first.broker_id == second.broker_id == BROKER_ID
        assert first.cash.amount > 0 > second.cash.amount and first.cash.code != second.cash.code

    def test_each_pair_has_its_own_link_uuid(self):
        out = _sample(SWISSQUOTE, SQ_SAMPLE)

        links = {order: _pair_of(out, *SQ_SAMPLE_PAIRS[order])[0].link_uuid for order in SQ_SAMPLE_PAIRS}

        assert len(set(links.values())) == len(links), f"two orders share a link_uuid: {links}"

    @pytest.mark.parametrize("order", sorted(SQ_SAMPLE_PAIRS))
    def test_a_sample_pair_obeys_the_rule_of_a_linked_conversion(self, order: str):
        """The pair passes ``_validate_linked_pair``: the same type on one broker (the currencies differ and the signs are opposite, asserted above)."""
        credit, debit, day = SQ_SAMPLE_PAIRS[order]
        first, second = _pair_of(_sample(SWISSQUOTE, SQ_SAMPLE), credit, debit, day)

        legs = [SimpleNamespace(type=tx.type, broker_id=tx.broker_id, asset_id=tx.asset_id, quantity=tx.quantity) for tx in (first, second)]

        assert TransactionValidationMixin._validate_linked_pair(*legs) is None

    def test_the_sample_lists_no_forex_row_any_more(self):
        out = _sample(SWISSQUOTE, SQ_SAMPLE)

        assert _lines_of(out, ROWS_NOT_RECOGNIZED) == [], f"{ROWS_NOT_RECOGNIZED} still lists {_lines_of(out, ROWS_NOT_RECOGNIZED)}"

    @pytest.mark.parametrize("credit_first", [True, False], ids=["credit then debit", "debit then credit"])
    def test_the_order_of_the_two_lines_does_not_matter(self, credit_first: bool, tmp_path: Path):
        credit = _sq_leg("credit", "900000001", "1500.00", "EUR")
        debit = _sq_leg("debit", "900000001", "-1600.00", "USD")

        out, (first_line, second_line) = _sq_parse(tmp_path, [credit, debit] if credit_first else [debit, credit])

        first, second = _pair_of(out, ("EUR", "1500.00"), ("USD", "-1600.00"), SQ_DAY)
        assert first.link_uuid and first.link_uuid == second.link_uuid
        _assert_not_listed(out, first_line, second_line)

    def test_a_pair_is_imported_while_a_lone_leg_of_another_order_is_listed(self, tmp_path: Path):
        legs = [
            _sq_leg("credit", "900000002", "1500.00", "EUR"),
            _sq_leg("debit", "900000002", "-1600.00", "USD"),
            _sq_leg("credit", "900000003", "700.00", "CHF", stamp="24-08-2022 09:00:00"),
        ]

        out, (pair_a, pair_b, lone) = _sq_parse(tmp_path, legs)

        _pair_of(out, ("EUR", "1500.00"), ("USD", "-1600.00"), SQ_DAY)
        assert _find(out, TransactionType.FX_CONVERSION, code="CHF", amount=Decimal("700.00")) == []
        _assert_listed(out, [lone], reason_has="forex")


class TestSwissquoteForexLegsLeftOut:
    """B — a forex leg that cannot be a whole conversion is still listed, with its line, and gives no transaction."""

    @pytest.mark.parametrize("kind", ["credit", "debit"])
    def test_a_single_leg_is_listed(self, kind: str, tmp_path: Path):
        leg = _sq_leg(kind, "900000010", "250.00" if kind == "credit" else "-250.00", "EUR" if kind == "credit" else "USD")

        out, (line,) = _sq_parse(tmp_path, [leg])

        assert _fx_legs(out) == [], f"a single {kind} leg is imported"
        _assert_listed(out, [line], reason_has="forex")

    def test_an_order_with_three_legs_is_listed_whole(self, tmp_path: Path):
        legs = [
            _sq_leg("credit", "900000011", "1500.00", "EUR"),
            _sq_leg("debit", "900000011", "-1600.00", "USD"),
            _sq_leg("credit", "900000011", "10.00", "EUR"),
        ]

        out, lines = _sq_parse(tmp_path, legs)

        assert _fx_legs(out) == [], "more than two legs: none of them is a pair"
        _assert_listed(out, lines, reason_has="forex")

    @pytest.mark.parametrize("costly", ["credit", "debit"])
    def test_a_leg_with_costs_is_listed_and_so_is_its_partner(self, costly: str, tmp_path: Path):
        """``Costs`` is a charge the net amount already holds: the plugin cannot copy it, so it does not import a leg that has one (the partner is then alone)."""
        credit = _sq_leg("credit", "900000012", "1500.00", "EUR", costs="2.50" if costly == "credit" else "0.00")
        debit = _sq_leg("debit", "900000012", "-1600.00", "USD", costs="2.50" if costly == "debit" else "0.00")

        out, lines = _sq_parse(tmp_path, [credit, debit])

        assert _fx_legs(out) == [], f"a conversion with costs on its {costly} leg is imported"
        _assert_listed(out, lines, reason_has="forex")


# =============================================================================
# C. Revolut Invest
# =============================================================================

REVOLUT_SAMPLE = "revolut-invest-export.csv"
REVOLUT_SPLIT_LINE = 9  # `2022-08-25T08:27:46.419568Z,TSLA,STOCK SPLIT,0.16431924,,$0,USD,0.0947`
_REVOLUT_TOP_UP = ["2019-11-15T23:15:55.878985Z", "", "CASH TOP-UP", "", "", "$5.22", "USD", "1.1055"]


def _revolut_split(quantity: str, *, ticker: str = "AAPL", stamp: str = "2024-01-15T10:00:00.000Z") -> List[str]:
    return [stamp, ticker, "STOCK SPLIT", quantity, "", "$0", "USD", "1.0"]


def _revolut_split_adjustment(out: BRIMParseOutput) -> Tuple[int, TXCreateItem]:
    """The ADJUSTMENT that adds 0.16431924 shares on 25/08/2022, with its index; fails when there is none or more than one."""
    found = [(index, tx) for index, tx in _adjustments(out) if tx.quantity == Decimal("0.16431924") and tx.date == date(2022, 8, 25)]
    assert len(found) == 1, f"the TSLA stock split gives {len(found)} ADJUSTMENT(s); the output has {[(t.type.value, t.quantity) for t in out.transactions]}"
    return found[0]


class TestRevolutStockSplit:
    """C — ``Quantity`` of a ``STOCK SPLIT`` row is the number of shares ADDED: one ADJUSTMENT, with the cost of the new shares at zero."""

    def test_the_split_is_one_adjustment_of_the_added_shares(self):
        out = _sample(REVOLUT, REVOLUT_SAMPLE)

        _, adjustment = _revolut_split_adjustment(out)

        assert adjustment.quantity == Decimal("0.16431924")
        assert adjustment.cash is None
        assert adjustment.broker_id == BROKER_ID

    def test_the_split_points_at_the_asset_of_the_ticker(self):
        """The fake asset of TSLA, the same one the BUY of TSLA in the file has."""
        out = _sample(REVOLUT, REVOLUT_SAMPLE)
        _, adjustment = _revolut_split_adjustment(out)

        buys = [tx for tx in out.transactions if tx.type == TransactionType.BUY and tx.asset_id in out.extracted_assets and out.extracted_assets[tx.asset_id].extracted_symbol == "TSLA"]

        assert buys, "presence barrier: the sample buys TSLA"
        assert adjustment.asset_id is not None and is_fake_asset_id(adjustment.asset_id)
        assert out.extracted_assets[adjustment.asset_id].extracted_symbol == "TSLA"
        assert adjustment.asset_id == buys[0].asset_id

    def test_the_new_shares_cost_nothing_and_the_row_is_described(self):
        out = _sample(REVOLUT, REVOLUT_SAMPLE)
        _, adjustment = _revolut_split_adjustment(out)

        assert adjustment.cost_basis_override == Currency(code="USD", amount=Decimal("0"))
        assert {"import", "revolut"} <= set(adjustment.tags or [])
        assert adjustment.description and "stock split" in adjustment.description.lower() and "TSLA" in adjustment.description

    def test_the_split_has_exactly_one_possible_split_todo_with_its_source_row(self):
        out = _sample(REVOLUT, REVOLUT_SAMPLE)
        index, _ = _revolut_split_adjustment(out)

        _assert_possible_split(out, index, {"ticker": "TSLA", "added_quantity": "0.16431924"}, "STOCK SPLIT", "TSLA", "0.16431924")

    def test_the_split_row_is_not_in_the_notice_any_more(self):
        out = _sample(REVOLUT, REVOLUT_SAMPLE)

        _assert_not_listed(out, REVOLUT_SPLIT_LINE)
        assert _notices(out, ROWS_NOT_RECOGNIZED) == [], "the sample has no other row left out"

    @pytest.mark.parametrize("quantity", ["-0.5", "0", "abc", ""], ids=["negative", "zero", "unreadable", "empty"])
    def test_a_split_without_a_positive_quantity_is_listed_and_gives_nothing(self, quantity: str, tmp_path: Path):
        """Guard (green today and after): no shares added can be read, so nothing is imported and the row is listed as before."""
        path, (_, line) = _write_rows(tmp_path, REVOLUT_SAMPLE, [_REVOLUT_TOP_UP, _revolut_split(quantity)], ",")

        out = _plugin(REVOLUT).parse(path, broker_id=BROKER_ID)

        assert _adjustments(out) == [], "no ADJUSTMENT from a split that adds no readable positive number of shares"
        assert out.field_todos == []
        _assert_listed(out, [line], reason_has="stock split")

    def test_a_good_split_and_a_bad_one_in_one_file(self, tmp_path: Path):
        """Each row is judged alone: the readable split is imported (one todo), the other one is listed (no todo)."""
        path, (_, good, bad) = _write_rows(tmp_path, REVOLUT_SAMPLE, [_REVOLUT_TOP_UP, _revolut_split("0.5", ticker="AAPL"), _revolut_split("-3", ticker="MSFT")], ",")

        out = _plugin(REVOLUT).parse(path, broker_id=BROKER_ID)

        adjustments = _adjustments(out)
        assert len(adjustments) == 1, f"the readable split (line {good}) gives {len(adjustments)} ADJUSTMENT(s)"
        index, adjustment = adjustments[0]
        assert adjustment.quantity == Decimal("0.5") and out.extracted_assets[adjustment.asset_id].extracted_symbol == "AAPL"
        assert [todo.tx_index for todo in out.field_todos] == [index]
        _assert_listed(out, [bad], reason_has="stock split")
        _assert_not_listed(out, good)


# =============================================================================
# D. Trading 212
# =============================================================================

T212_SAMPLE = "trading212-export.csv"
T212_ISIN, T212_TICKER, T212_NAME = "CA46500E8678", "ISOU", "IsoEnergy"
T212_CLOSE_TIME, T212_OPEN_TIME = "2025-03-24 07:24:24.095", "2025-03-24 07:24:24.104"
T212_DAY = date(2025, 3, 24)
T212_SAMPLE_LINES = {"distribution": 11, "close": 13, "open": 14}
_T212_DEPOSIT = {"Action": "Deposit", "Time": "2023-12-18 11:45:06.326", "Total": "31.00", "Currency (Total)": "EUR", "ID": "SYNTH-DEPOSIT-1"}


def _t212_split(kind: str, shares: str, *, time: Optional[str] = None, isin: str = T212_ISIN, ticker: str = T212_TICKER, name: str = T212_NAME, row_id: str = "", total_currency: str = "EUR", price_currency: str = "") -> Mapping[str, str]:
    """A ``Stock split close`` / ``Stock split open`` row laid out under the real header (the shares in ``No. of shares``)."""
    return {
        "Action": f"Stock split {kind}",
        "Time": time or (T212_CLOSE_TIME if kind == "close" else T212_OPEN_TIME),
        "ISIN": isin,
        "Ticker": ticker,
        "Name": name,
        "No. of shares": shares,
        "Currency (Price / share)": price_currency,
        "Currency (Total)": total_currency,
        "ID": row_id or f"SYNTH-{kind.upper()}-{isin}",
    }


def _t212_parse(tmp_path: Path, rows: Sequence[Row]) -> Tuple[BRIMParseOutput, List[int]]:
    """A file with a deposit (line 2) and the rows (lines 3 onward); returns the parse and the line of every row."""
    path, lines = _write_rows(tmp_path, T212_SAMPLE, [_T212_DEPOSIT, *rows], ",")
    return _plugin(TRADING212).parse(path, broker_id=BROKER_ID), lines[1:]


def _t212_split_adjustment(out: BRIMParseOutput, isin: str = T212_ISIN) -> Tuple[int, TXCreateItem]:
    """The one ADJUSTMENT of the asset with this ISIN, with its index."""
    found = [(index, tx) for index, tx in _adjustments(out) if out.extracted_assets.get(tx.asset_id) is not None and out.extracted_assets[tx.asset_id].extracted_isin == isin]
    assert len(found) == 1, f"the split of {isin} gives {len(found)} ADJUSTMENT(s); the output has {[(t.type.value, t.quantity) for t in out.transactions]}"
    return found[0]


class TestTrading212SampleSplit:
    """D — guard: the sample's pair has MORE close shares than open ones (a reverse split): nothing is imported, both rows are listed."""

    def test_the_reverse_split_is_not_imported(self):
        out = _sample(TRADING212, T212_SAMPLE)

        assert _adjustments(out) == [] and out.field_todos == []

    def test_both_rows_stay_in_the_notice_with_the_distribution(self):
        out = _sample(TRADING212, T212_SAMPLE)
        lines = _physical_lines(T212_SAMPLE)
        assert "Stock split close" in lines[T212_SAMPLE_LINES["close"] - 1] and "Stock split open" in lines[T212_SAMPLE_LINES["open"] - 1], "fixture guard"

        _assert_listed(out, sorted(T212_SAMPLE_LINES.values()))


class TestTrading212SplitPair:
    """D — a ``close`` and an ``open`` row of one ISIN within 2 seconds, the open one with more shares, are one ADJUSTMENT of the difference."""

    def test_a_multiplicative_pair_is_one_adjustment_of_the_difference(self, tmp_path: Path):
        out, (close_line, open_line) = _t212_parse(tmp_path, [_t212_split("close", "10"), _t212_split("open", "30")])

        index, adjustment = _t212_split_adjustment(out)

        assert adjustment.quantity == Decimal("20"), "open shares minus close shares"
        assert adjustment.cash is None
        assert (adjustment.date, adjustment.broker_id) == (T212_DAY, BROKER_ID)
        assert is_fake_asset_id(adjustment.asset_id)
        info = out.extracted_assets[adjustment.asset_id]
        assert (info.extracted_isin, info.extracted_symbol) == (T212_ISIN, T212_TICKER)
        assert {"import", "trading212"} <= set(adjustment.tags or [])
        _assert_not_listed(out, close_line, open_line)

    def test_the_new_shares_cost_nothing_in_the_currency_of_the_row(self, tmp_path: Path):
        out, _ = _t212_parse(tmp_path, [_t212_split("close", "10", total_currency="GBP"), _t212_split("open", "30", total_currency="GBP")])

        _, adjustment = _t212_split_adjustment(out)

        assert adjustment.cost_basis_override == Currency(code="GBP", amount=Decimal("0"))

    def test_the_currency_of_the_price_is_the_fallback_when_the_total_has_none(self, tmp_path: Path):
        rows = [_t212_split("close", "10", total_currency="", price_currency="USD"), _t212_split("open", "30", total_currency="", price_currency="USD")]

        out, _ = _t212_parse(tmp_path, rows)

        _, adjustment = _t212_split_adjustment(out)
        assert adjustment.cost_basis_override == Currency(code="USD", amount=Decimal("0"))

    def test_the_pair_has_exactly_one_possible_split_todo_with_its_source_row(self, tmp_path: Path):
        out, _ = _t212_parse(tmp_path, [_t212_split("close", "10"), _t212_split("open", "30")])
        index, _ = _t212_split_adjustment(out)

        _assert_possible_split(out, index, {"ticker": T212_TICKER, "added_quantity": "20", "isin": T212_ISIN}, "Stock split open", T212_ISIN)

    @pytest.mark.parametrize("open_first", [False, True], ids=["close then open", "open then close"])
    def test_the_order_of_the_two_lines_does_not_matter(self, open_first: bool, tmp_path: Path):
        rows = [_t212_split("close", "10"), _t212_split("open", "30")]

        out, lines = _t212_parse(tmp_path, rows[::-1] if open_first else rows)

        _, adjustment = _t212_split_adjustment(out)
        assert adjustment.quantity == Decimal("20")
        _assert_not_listed(out, *lines)

    @pytest.mark.parametrize("open_time", ["2025-03-24 07:24:25.995", "2025-03-24 07:24:24.095"], ids=["1.9 s later", "the same instant"])
    def test_a_pair_within_two_seconds_is_matched(self, open_time: str, tmp_path: Path):
        out, lines = _t212_parse(tmp_path, [_t212_split("close", "10"), _t212_split("open", "30", time=open_time)])

        _, adjustment = _t212_split_adjustment(out)
        assert adjustment.quantity == Decimal("20")
        _assert_not_listed(out, *lines)

    def test_two_pairs_of_two_isins_are_not_mixed_up(self, tmp_path: Path):
        other = {"isin": "US0000000002", "ticker": "OTHR", "name": "Other Corp"}
        rows = [
            _t212_split("close", "10"),
            _t212_split("close", "5", **other),
            _t212_split("open", "8", **other),
            _t212_split("open", "30"),
        ]

        out, _ = _t212_parse(tmp_path, rows)

        index_a, adjustment_a = _t212_split_adjustment(out, T212_ISIN)
        index_b, adjustment_b = _t212_split_adjustment(out, "US0000000002")
        assert (adjustment_a.quantity, adjustment_b.quantity) == (Decimal("20"), Decimal("3"))
        assert adjustment_a.asset_id != adjustment_b.asset_id
        _assert_possible_split(out, index_a, {"ticker": T212_TICKER, "added_quantity": "20", "isin": T212_ISIN}, T212_ISIN)
        _assert_possible_split(out, index_b, {"ticker": "OTHR", "added_quantity": "3", "isin": "US0000000002"}, "US0000000002")

    def test_a_pair_in_the_layout_of_the_real_export_is_matched_too(self, tmp_path: Path):
        """The two split rows of the SAMPLE, as the real export writes them (the shares are not in ``No. of shares``: the first cell after the name is
        empty and the shares come after the order id), with the numbers changed to make a multiplicative split: 10 shares close, 30 open."""
        lines = _physical_lines(T212_SAMPLE)
        close, open_ = lines[T212_SAMPLE_LINES["close"] - 1], lines[T212_SAMPLE_LINES["open"] - 1]
        assert close.count("29.8047800000") == 1 and open_.count("7.4511950000") == 1, "fixture guard: the sample's numbers moved"
        deposit = io.StringIO()
        csv.writer(deposit, lineterminator="\n").writerow(_cells(_header(T212_SAMPLE, ","), _T212_DEPOSIT))
        path = tmp_path / T212_SAMPLE
        path.write_text("\n".join([lines[0], deposit.getvalue().rstrip("\n"), close.replace("29.8047800000", "10"), open_.replace("7.4511950000", "30")]) + "\n", encoding="utf-8")

        out = _plugin(TRADING212).parse(path, broker_id=BROKER_ID)

        index, adjustment = _t212_split_adjustment(out)
        assert adjustment.quantity == Decimal("20")
        assert adjustment.cost_basis_override == Currency(code="EUR", amount=Decimal("0"))
        _assert_possible_split(out, index, {"ticker": T212_TICKER, "added_quantity": "20", "isin": T212_ISIN}, "Stock split open")
        _assert_not_listed(out, 3, 4)


class TestTrading212SplitsLeftOut:
    """D — every split row that is not half of a multiplicative pair is listed, with its line, and gives no transaction and no todo."""

    @staticmethod
    def _assert_left_out(out: BRIMParseOutput, lines: Sequence[int]) -> None:
        assert _adjustments(out) == [], "no ADJUSTMENT from these rows"
        assert out.field_todos == [], "no todo from these rows"
        _assert_listed(out, lines, reason_has="stock split")

    @pytest.mark.parametrize("kind", ["close", "open"])
    def test_a_row_without_its_partner_is_listed(self, kind: str, tmp_path: Path):
        out, (line,) = _t212_parse(tmp_path, [_t212_split(kind, "10")])

        self._assert_left_out(out, [line])

    def test_both_unmatched_rows_are_listed_when_a_close_and_an_open_are_of_two_isins(self, tmp_path: Path):
        out, lines = _t212_parse(tmp_path, [_t212_split("close", "10"), _t212_split("open", "30", isin="US0000000003", ticker="THRD", name="Third Corp")])

        self._assert_left_out(out, lines)

    @pytest.mark.parametrize("open_time", ["2025-03-24 07:24:27.095", "2025-03-25 07:24:24.104"], ids=["3 s later", "a day later"])
    def test_a_pair_more_than_two_seconds_apart_is_not_a_pair(self, open_time: str, tmp_path: Path):
        out, lines = _t212_parse(tmp_path, [_t212_split("close", "10"), _t212_split("open", "30", time=open_time)])

        self._assert_left_out(out, lines)

    @pytest.mark.parametrize(("close_shares", "open_shares"), [("10", "10"), ("30", "10"), ("10", "")], ids=["equal", "reverse split", "open without shares"])
    def test_a_pair_that_adds_no_shares_is_listed(self, close_shares: str, open_shares: str, tmp_path: Path):
        out, lines = _t212_parse(tmp_path, [_t212_split("close", close_shares), _t212_split("open", open_shares)])

        self._assert_left_out(out, lines)

    def test_a_good_pair_and_a_lone_close_in_one_file(self, tmp_path: Path):
        other = {"isin": "US0000000004", "ticker": "FRTH", "name": "Fourth Corp"}
        out, (close_line, open_line, lone_line) = _t212_parse(tmp_path, [_t212_split("close", "10"), _t212_split("open", "30"), _t212_split("close", "7", **other)])

        index, _ = _t212_split_adjustment(out)
        assert [todo.tx_index for todo in out.field_todos] == [index]
        _assert_listed(out, [lone_line], reason_has="stock split")
        _assert_not_listed(out, close_line, open_line)


class TestTrading212UnchangedRows:
    """D — guard (green today and after): a share distribution and a currency conversion are still not imported."""

    def test_the_sample_stock_distribution_is_listed_and_not_imported(self):
        out = _sample(TRADING212, T212_SAMPLE)
        assert "Stock distribution" in _physical_lines(T212_SAMPLE)[T212_SAMPLE_LINES["distribution"] - 1], "fixture guard"

        assert T212_SAMPLE_LINES["distribution"] in _lines_of(out, ROWS_NOT_RECOGNIZED)
        assert not [tx for tx in out.transactions if tx.asset_id in out.extracted_assets and out.extracted_assets[tx.asset_id].extracted_isin == "US9078181081" and tx.quantity == Decimal("11.0563304000")]

    @pytest.mark.parametrize(
        ("action", "extra"),
        [
            ("Stock distribution", {"ISIN": "US9078181081", "Ticker": "PALAF", "Name": "Union Pacific", "No. of shares": "11.05"}),
            ("Currency conversion", {"Total": "10.00", "Currency (Total)": "EUR"}),
        ],
        ids=["stock distribution", "currency conversion"],
    )
    def test_the_row_is_listed_and_gives_no_transaction(self, action: str, extra: Mapping[str, str], tmp_path: Path):
        row = {"Action": action, "Time": "2025-01-24 10:00:00.000", "ID": "SYNTH-UNCHANGED-1", **extra}

        out, (line,) = _t212_parse(tmp_path, [row])

        assert _adjustments(out) == [] and out.field_todos == []
        assert [tx.type for tx in out.transactions] == [TransactionType.DEPOSIT], "only the deposit is imported"
        _assert_listed(out, [line], reason_has=action.lower())
