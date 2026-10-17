"""J-12 (decision N81, option A) — a FAILED lots analysis withholds every lot figure: only the failure and what to fix.

Workstream J «Numeri e analisi», release 1.3: the service-level reds and guards S1–S6 of the lot, through
``lots_analysis_service.get_lots_analysis``. The engine half of S4 is in
``test_financial_math/test_fifo_transfer_issue_names_the_giving_leg.py``; the AI Export half of the lot beside the FIFO
component tests (``test_ai_export_fifo_failed_reconstruction.py``).

THE RULE. A replay that hits a code of ``_QUANTITATIVE_FAILURE_CODES`` (``financial_math/fifo/models.py``: a sale beyond
what is held, ``FIFO_SOURCE_QUANTITY_MISSING``; a lone or broken TRANSFER leg, ``TRANSFER_PAIR_MISSING``; the two
``SHORT_*_NOT_SUPPORTED``) cannot be trusted as a whole: FAILED. Its lots, and every figure drawn from them, are wrong,
so none is given — as Yield on Cost already withholds its number when the same replay fails
(``yield_on_cost._component_replay_failure``). The contract (journal of J, «J-12: contratto con Y», 17/10 11:30):

- FAILED: ``lots``, ``gantt_segments``, ``custody_history``, ``lot_events``, ``value_history``, ``return_history``,
  ``price_history`` (per lot), ``performance_history``, ``income_events`` and ``economic_allocation_groups`` are None —
  the default, as ``_empty_response`` —, and so are the orphans ``asset_orphan_income/fees/taxes`` (unknown, not 0).
  What does not come from the lots stays: the average-cost lines (``broker_wac_history``, ``cumulative_wac_history``),
  ``quote_base_quantity``, ``calculation_metadata`` and ``data_quality`` with every issue (S1, S2).
- On an issue of those codes ``message_params`` gains ``transaction_date`` (ISO date of the row ``transaction_id``
  names) and ``fails_analysis: True``; its other params stay. No other issue carries either key (S3).
- With FAILED, ``data_quality.issues`` keeps only the blocking issues and the gaps of the average-cost lines that
  ``_report_gaps`` adds (their missing rates, ``MISSING_COST_BASIS``). The issues of the sections no longer computed go:
  ``REFERENCE_PRICE_FALLBACK``, ``REFERENCE_PRICE_UNAVAILABLE``, ``ASSET_INCOME_NO_ELIGIBLE_LOTS``,
  ``ASSET_COST_NO_ELIGIBLE_LOTS``, ``CURRENT_PRICE_ASSUMED_AT_COST`` and the rates missing for the lot figures (rule
  agreed with Y, the panel's owner; S7). A DEGRADED analysis keeps every issue it has today.
- ``transaction_id`` is always a real row of the scope: a transfer departing with more than its broker holds, or a
  short one, names the GIVING leg, never the lower id of the pair (S4).
- DEGRADED and COMPLETE analyses are unchanged (S5, S6).

TODAY (base ``2f4ef68e6``) a FAILED analysis returns every section, filled with the figures of a replay it calls
unreliable, and every issue of those sections; its failure issues carry ``transaction_id``, ``lot_id``, ``broker_id``,
``related_transaction_id`` (and ``missing_quantity``) only; a transfer issue names the departure event's
``transaction_id`` — the lower id of a same-day pair, or the earlier-dated leg. Each red says what it read today in its
docstring.

Every test owns its rows: users, brokers and assets carry a uuid4 (``_scope_boundary_books.py``), written into the test's
session and rolled back. No FX: everything is in EUR. Dates in 2025.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, Broker, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import LotAnalysisType, LotsAnalysisResponse
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.test_scripts.test_services._scope_boundary_books import add_prices, asset_row, link, new_asset, new_broker, new_user

D = Decimal
ORPHAN_DAY = date(2025, 2, 1)  # a dividend and a fee before any lot: no eligible lot, no trade to match
BUY_DAY = date(2025, 2, 3)
INCOME_DAY = date(2025, 2, 5)
FIRST_TRADE_DAY = date(2025, 2, 6)  # DEGRADED ledger: the first observation
FAILURE_DAY = date(2025, 2, 10)  # the oversell, the lone leg, the transfer pair
LATE_ADJUSTMENT_DAY = date(2025, 2, 12)
DATE_TO = date(2025, 2, 14)
PRICES: Mapping[date, str] = {date(2025, 2, 3): "100", date(2025, 2, 6): "105", date(2025, 2, 10): "110", date(2025, 2, 13): "112"}

ALL_ANALYSES = list(LotAnalysisType)
WAC_LINES = (LotAnalysisType.BROKER_WAC_HISTORY, LotAnalysisType.CUMULATIVE_WAC_HISTORY)
# S7: every analysis; every analysis but the two average-cost lines; the broker's average-cost line alone.
ANALYSIS_SETS = {
    "every-analysis": ALL_ANALYSES,
    "every-analysis-but-the-wac-lines": [analysis for analysis in LotAnalysisType if analysis not in WAC_LINES],
    "broker-wac-history-alone": [LotAnalysisType.BROKER_WAC_HISTORY],
}
# The sections drawn from the lots: None with FAILED (the default, as ``_empty_response``)...
LOT_SECTIONS = ("lots", "gantt_segments", "custody_history", "lot_events", "value_history", "return_history", "price_history", "performance_history", "income_events", "economic_allocation_groups")
# ...and the orphans, unknown with FAILED: None, never 0.
ORPHANS = ("asset_orphan_income", "asset_orphan_fees", "asset_orphan_taxes")
QUANTITATIVE_FAILURES = {"FIFO_SOURCE_QUANTITY_MISSING", "TRANSFER_PAIR_MISSING", "SHORT_TRANSFER_NOT_SUPPORTED", "SHORT_ADJUSTMENT_NOT_SUPPORTED"}
NEW_KEYS = ("transaction_date", "fails_analysis")


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


# --------------------------------------------------------------------------- #
# Books
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Book:
    owner: User
    broker_a: Broker
    asset: Asset
    rows: dict[str, Transaction] = field(default_factory=dict)
    broker_b: Broker | None = None


async def _add(session: AsyncSession, **rows: Transaction) -> dict[str, Transaction]:
    session.add_all(rows.values())
    await session.flush()
    return rows


async def _book(session: AsyncSession, label: str, *, prices: bool = True) -> tuple[User, Broker, Asset]:
    owner = await new_user(session, f"j12_{label}")
    broker_a = await new_broker(session, f"J12 {label} A", owner)
    asset = await new_asset(session, f"J12 {label}")
    if prices:
        add_prices(session, asset, PRICES)
    return owner, broker_a, asset


async def seed_oversell(session: AsyncSession) -> Book:
    """A (no shorting) buys 5 at 100 on 3 Feb, cashes a 10 EUR dividend on 5 Feb, sells 8 at 110 on 10 Feb: 3 beyond what it holds."""
    owner, a, asset = await _book(session, "oversell")
    rows = await _add(
        session,
        buy=asset_row(a, asset, TransactionType.BUY, BUY_DAY, "5", amount="-500"),
        dividend=asset_row(a, asset, TransactionType.DIVIDEND, INCOME_DAY, "0", amount="10"),
        sell=asset_row(a, asset, TransactionType.SELL, FAILURE_DAY, "-8", amount="880"),
    )
    return Book(owner, a, asset, rows)


async def seed_lone_transfer_leg(session: AsyncSession) -> Book:
    """A buys 10 at 100 on 3 Feb, cashes a 10 EUR dividend on 5 Feb, and has a TRANSFER −4 on 10 Feb with no partner at all."""
    owner, a, asset = await _book(session, "lone")
    rows = await _add(
        session,
        buy=asset_row(a, asset, TransactionType.BUY, BUY_DAY, "10", amount="-1000"),
        dividend=asset_row(a, asset, TransactionType.DIVIDEND, INCOME_DAY, "0", amount="10"),
        leg=asset_row(a, asset, TransactionType.TRANSFER, FAILURE_DAY, "-4"),
    )
    return Book(owner, a, asset, rows)


async def seed_mixed_failed(session: AsyncSession) -> Book:
    """FAILED, with every issue the rule drops beside the failure. No quote at all. On 1 Feb A cashes a 10 EUR dividend and
    pays a 2 EUR fee before holding anything (an orphan income, an orphan cost); on 3 Feb it receives 5 with a cost of 100
    (no reference price that day); on 10 Feb it sells 8 at 110 — 3 beyond what it holds, and the first observation, so
    3–9 Feb is valued at cost —; on 12 Feb it receives 2 without a cost (a reference price carried from the sale, a cost
    basis missing in the average-cost lines)."""
    owner, a, asset = await _book(session, "mixed", prices=False)
    rows = await _add(
        session,
        orphan_dividend=asset_row(a, asset, TransactionType.DIVIDEND, ORPHAN_DAY, "0", amount="10"),
        orphan_fee=asset_row(a, asset, TransactionType.FEE, ORPHAN_DAY, "0", amount="-2"),
        adjustment=asset_row(a, asset, TransactionType.ADJUSTMENT, BUY_DAY, "5", cost="100"),
        sell=asset_row(a, asset, TransactionType.SELL, FAILURE_DAY, "-8", amount="880"),
        costless=asset_row(a, asset, TransactionType.ADJUSTMENT, LATE_ADJUSTMENT_DAY, "2"),
    )
    return Book(owner, a, asset, rows)


async def seed_degraded(session: AsyncSession) -> Book:
    """DEGRADED, never FAILED, with the same issues as the FAILED ledger above, the failure aside. No quote at all. On 1 Feb
    an orphan 10 EUR dividend and an orphan 2 EUR fee; on 3 Feb A receives 5 with a cost of 100 (no reference price); on
    6 Feb it buys 1 at 104 — the first observation, so 3–5 Feb is valued at cost —; on 10 Feb it receives 2 without a
    cost (a reference price carried from the purchase, a cost basis missing); on 12 Feb it cashes a 10 EUR dividend."""
    owner, a, asset = await _book(session, "degraded", prices=False)
    rows = await _add(
        session,
        orphan_dividend=asset_row(a, asset, TransactionType.DIVIDEND, ORPHAN_DAY, "0", amount="10"),
        orphan_fee=asset_row(a, asset, TransactionType.FEE, ORPHAN_DAY, "0", amount="-2"),
        adjustment=asset_row(a, asset, TransactionType.ADJUSTMENT, BUY_DAY, "5", cost="100"),
        buy=asset_row(a, asset, TransactionType.BUY, FIRST_TRADE_DAY, "1", amount="-104"),
        costless=asset_row(a, asset, TransactionType.ADJUSTMENT, FAILURE_DAY, "2"),
        dividend=asset_row(a, asset, TransactionType.DIVIDEND, LATE_ADJUSTMENT_DAY, "0", amount="10"),
    )
    return Book(owner, a, asset, rows)


async def seed_complete(session: AsyncSession) -> Book:
    """COMPLETE: A buys 10 at 100 on 3 Feb and cashes a 10 EUR dividend on 5 Feb; quoted every few days."""
    owner, a, asset = await _book(session, "complete")
    rows = await _add(
        session,
        buy=asset_row(a, asset, TransactionType.BUY, BUY_DAY, "10", amount="-1000"),
        dividend=asset_row(a, asset, TransactionType.DIVIDEND, INCOME_DAY, "0", amount="10"),
    )
    return Book(owner, a, asset, rows)


async def seed_same_day_pair(session: AsyncSession, *, giving: str, short: bool = False) -> Book:
    """S4: U owns A and B. A buys 5 at 100 on 3 Feb — or, ``short`` (A allows shorting), sells 3 at 100 and holds −3. On
    10 Feb A gives ``giving`` units to B, both legs that day. B's receiving leg (with its Auto cost, 100 a unit) is written
    FIRST, so it has the LOWER id of the pair."""
    owner, a, asset = await _book(session, "pair")
    b = await new_broker(session, "J12 pair B", owner)
    if short:
        a.allow_asset_shorting = True
        opening = asset_row(a, asset, TransactionType.SELL, BUY_DAY, "-3", amount="300")
    else:
        opening = asset_row(a, asset, TransactionType.BUY, BUY_DAY, "5", amount="-500")
    rows = await _add(session, opening=opening)
    rows |= await _add(session, in_leg=asset_row(b, asset, TransactionType.TRANSFER, FAILURE_DAY, giving, cost="100"))
    rows |= await _add(session, out_leg=asset_row(a, asset, TransactionType.TRANSFER, FAILURE_DAY, f"-{giving}"))
    await link(session, rows["out_leg"], rows["in_leg"])
    return Book(owner, a, asset, rows, broker_b=b)


# --------------------------------------------------------------------------- #
# Readings
# --------------------------------------------------------------------------- #


async def _analysis(session: AsyncSession, book: Book, analyses: list[LotAnalysisType] = ALL_ANALYSES) -> LotsAnalysisResponse:
    return await get_lots_analysis(
        session=session,
        user_id=book.owner.id,
        asset_id=book.asset.id,
        broker_ids=None,
        date_from=None,
        date_to=DATE_TO,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=analyses,
    )


def _issue_codes(result: LotsAnalysisResponse) -> list[str]:
    """The distinct issue codes of the analysis, sorted."""
    return sorted({str(issue.code) for issue in result.data_quality.issues})


def _issues(result: LotsAnalysisResponse, code: str) -> list:
    return [issue for issue in result.data_quality.issues if str(issue.code) == code]


def _shape(value: object) -> object:
    """What a section holds, readably: None, ``list[n]``, or the orphan amount itself."""
    if value is None or isinstance(value, Decimal):
        return value
    return f"list[{len(value)}]"


async def _seeded(session: AsyncSession, name: str) -> Book:
    return await {"oversell": seed_oversell, "lone-transfer-leg": seed_lone_transfer_leg}[name](session)


FAILED_BOOKS = ["oversell", "lone-transfer-leg"]


# --------------------------------------------------------------------------- #
# S1, S2 — a FAILED analysis withholds every lot section, and keeps the rest
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize("book_name", FAILED_BOOKS)
async def test_s1_s2_failed_analysis_withholds_every_lot_section(session, book_name):
    """S1 (oversell: A holds 5 and sells 8) and S2 (a lone TRANSFER leg, no partner), every analysis requested: the replay is
    FAILED, so every section drawn from the lots is None, and the orphans too (unknown, never 0).

    Today: FAILED, and every section filled from the replay it calls unreliable. Oversell: 1 lot, 1 Gantt segment, 1 custody
    row, 2 events, 12 value / return / performance points, 8 price points (the lot's life, 3–10 Feb), 1 income event, 1
    economic allocation group, the three orphans Decimal 0. Lone leg: the same but 1 event and 12 price points — its lot of
    10 still open at A, as if the 4 units had never left.
    """
    book = await _seeded(session, book_name)

    result = await _analysis(session, book)

    # Precondition, green today and after: the replay failed on the code this book is about — the red is the sections.
    assert (result.calculation_status, _issue_codes(result)) == ("FAILED", ["FIFO_SOURCE_QUANTITY_MISSING" if book_name == "oversell" else "TRANSFER_PAIR_MISSING"])
    observed = {name: _shape(getattr(result, name)) for name in (*LOT_SECTIONS, *ORPHANS)}
    assert observed == dict.fromkeys((*LOT_SECTIONS, *ORPHANS))


@pytest.mark.asyncio
@pytest.mark.parametrize("book_name", FAILED_BOOKS)
async def test_s1_s2_guard_failed_analysis_keeps_the_wac_lines_the_metadata_and_the_issues(session, book_name):
    """GUARD (green today and after): what does not come from the lots stays with FAILED — the two average-cost lines (one
    point a day at least), ``quote_base_quantity``, the metadata up to ``date_to`` and the failure issue in the data quality."""
    book = await _seeded(session, book_name)

    result = await _analysis(session, book)

    observed = {
        "status": result.calculation_status,
        "broker WAC points": bool(result.broker_wac_history),
        "cumulative WAC points": bool(result.cumulative_wac_history),
        "quote_base_quantity": result.quote_base_quantity,
        "computed until": result.calculation_metadata.computed_date_to,
        "issues": _issue_codes(result),
    }
    assert observed == {
        "status": "FAILED",
        "broker WAC points": True,
        "cumulative WAC points": True,
        "quote_base_quantity": 1,
        "computed until": DATE_TO,
        "issues": ["FIFO_SOURCE_QUANTITY_MISSING" if book_name == "oversell" else "TRANSFER_PAIR_MISSING"],
    }


# --------------------------------------------------------------------------- #
# S3 — the failure issue says when, and that it fails the analysis
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize("book_name", FAILED_BOOKS)
async def test_s3_failure_issue_gains_transaction_date_and_fails_analysis(session, book_name):
    """S3: the failure issue's ``message_params`` gain ``transaction_date`` (ISO date of the row ``transaction_id`` names)
    and ``fails_analysis: True``; the other params stay, and nothing else is added.

    Today: the params stop at ``transaction_id`` (the SELL / the lone leg), ``lot_id`` None, ``broker_id`` A,
    ``related_transaction_id`` None — and ``missing_quantity`` 3 for the oversell: no ``transaction_date``, no
    ``fails_analysis``.
    """
    book = await _seeded(session, book_name)

    result = await _analysis(session, book, [LotAnalysisType.LOT_SUMMARY])

    if book_name == "oversell":
        code, row, extra = "FIFO_SOURCE_QUANTITY_MISSING", book.rows["sell"], {"missing_quantity": D("3")}
    else:
        code, row, extra = "TRANSFER_PAIR_MISSING", book.rows["leg"], {}
    issues = _issues(result, code)
    assert len(issues) == 1, [issue.message_params for issue in result.data_quality.issues]
    assert issues[0].message_params == {
        "transaction_id": row.id,
        "lot_id": None,
        "broker_id": book.broker_a.id,
        "related_transaction_id": None,
        **extra,
        "transaction_date": FAILURE_DAY.isoformat(),
        "fails_analysis": True,
    }


@pytest.mark.asyncio
async def test_s3_guard_other_issues_of_a_failed_analysis_carry_neither_key(session):
    """GUARD (green today and after): beside a failure, an issue that does not fail the analysis carries neither
    ``transaction_date`` nor ``fails_analysis``. After S7 the only such issues a FAILED analysis keeps are the gaps of the
    average-cost lines — here ``MISSING_COST_BASIS``, the one this guard requires; today the dropped ones are checked too."""
    book = await seed_mixed_failed(session)

    result = await _analysis(session, book)

    codes = _issue_codes(result)
    # Precondition: FAILED, with the cost basis gap of the average-cost lines beside the failure (kept by S7).
    assert result.calculation_status == "FAILED"
    assert {"FIFO_SOURCE_QUANTITY_MISSING", "MISSING_COST_BASIS"} <= set(codes), codes
    carrying = {str(issue.code): sorted(key for key in NEW_KEYS if key in issue.message_params) for issue in result.data_quality.issues if str(issue.code) not in QUANTITATIVE_FAILURES}
    assert carrying == {code: [] for code in codes if code not in QUANTITATIVE_FAILURES}


@pytest.mark.asyncio
async def test_s3_guard_issues_of_a_degraded_analysis_carry_neither_key(session):
    """GUARD (green today and after): a DEGRADED analysis — a reference price unavailable, the price assumed at cost, a cost
    basis missing — has no issue with ``transaction_date`` or ``fails_analysis``."""
    book = await seed_degraded(session)

    result = await _analysis(session, book)

    codes = _issue_codes(result)
    assert result.calculation_status == "DEGRADED"
    assert {"REFERENCE_PRICE_UNAVAILABLE", "CURRENT_PRICE_ASSUMED_AT_COST", "MISSING_COST_BASIS"} <= set(codes), codes
    carrying = {str(issue.code): sorted(key for key in NEW_KEYS if key in issue.message_params) for issue in result.data_quality.issues}
    assert carrying == {code: [] for code in codes}


# --------------------------------------------------------------------------- #
# S7 — a FAILED analysis keeps only the blocking issues and the gaps of the average-cost lines
# --------------------------------------------------------------------------- #


def _codes_one_per_issue(result: LotsAnalysisResponse) -> list[str]:
    """The issue codes, one entry per issue, sorted: a duplicate shows."""
    return sorted(str(issue.code) for issue in result.data_quality.issues)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("analyses", "kept"),
    [
        ("every-analysis", ["FIFO_SOURCE_QUANTITY_MISSING", "MISSING_COST_BASIS"]),
        ("every-analysis-but-the-wac-lines", ["FIFO_SOURCE_QUANTITY_MISSING"]),
        ("broker-wac-history-alone", ["FIFO_SOURCE_QUANTITY_MISSING", "MISSING_COST_BASIS"]),
    ],
)
async def test_s7_failed_analysis_keeps_only_the_blocking_issues_and_the_gaps_of_the_wac_lines(session, analyses, kept):
    """S7, the FAILED ledger with every droppable issue beside the failure: the data quality keeps the blocking issue and,
    when an average-cost line is computed (a WAC analysis requested), the cost basis gap of the costless acquisition.
    Everything else — the issues of the sections no longer computed — goes.

    Today every issue stays. Every analysis: ASSET_COST_NO_ELIGIBLE_LOTS, ASSET_INCOME_NO_ELIGIBLE_LOTS,
    CURRENT_PRICE_ASSUMED_AT_COST, FIFO_SOURCE_QUANTITY_MISSING, MISSING_COST_BASIS, REFERENCE_PRICE_FALLBACK,
    REFERENCE_PRICE_UNAVAILABLE. Without the average-cost lines: the same but MISSING_COST_BASIS. The broker's line alone
    (no economic stage, no market series): FIFO_SOURCE_QUANTITY_MISSING, MISSING_COST_BASIS, REFERENCE_PRICE_FALLBACK,
    REFERENCE_PRICE_UNAVAILABLE.
    """
    book = await seed_mixed_failed(session)

    result = await _analysis(session, book, ANALYSIS_SETS[analyses])

    assert result.calculation_status == "FAILED"
    assert _codes_one_per_issue(result) == kept


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("analyses", "today"),
    [
        ("every-analysis", ["ASSET_COST_NO_ELIGIBLE_LOTS", "ASSET_INCOME_NO_ELIGIBLE_LOTS", "CURRENT_PRICE_ASSUMED_AT_COST", "MISSING_COST_BASIS", "REFERENCE_PRICE_FALLBACK", "REFERENCE_PRICE_UNAVAILABLE"]),
        ("every-analysis-but-the-wac-lines", ["ASSET_COST_NO_ELIGIBLE_LOTS", "ASSET_INCOME_NO_ELIGIBLE_LOTS", "CURRENT_PRICE_ASSUMED_AT_COST", "REFERENCE_PRICE_FALLBACK", "REFERENCE_PRICE_UNAVAILABLE"]),
        ("broker-wac-history-alone", ["MISSING_COST_BASIS", "REFERENCE_PRICE_FALLBACK", "REFERENCE_PRICE_UNAVAILABLE"]),
    ],
)
async def test_s7_guard_degraded_analysis_keeps_every_issue_it_has_today(session, analyses, today):
    """GUARD (green today and after): the DEGRADED ledger, the same issues as the FAILED one but the failure, keeps every
    issue it has today — the rule of S7 is about FAILED only."""
    book = await seed_degraded(session)

    result = await _analysis(session, book, ANALYSIS_SETS[analyses])

    assert result.calculation_status == "DEGRADED"
    assert _codes_one_per_issue(result) == today


# --------------------------------------------------------------------------- #
# S4 — a transfer that cannot depart names the giving leg
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(("short", "giving", "code"), [(False, "8", "FIFO_SOURCE_QUANTITY_MISSING"), (True, "2", "SHORT_TRANSFER_NOT_SUPPORTED")], ids=["beyond-holdings", "short"])
async def test_s4_transfer_issue_names_the_giving_leg(session, short, giving, code):
    """S4: A holds 5 and gives 8 to B (or holds −3, short, and gives 2), both legs on 10 Feb, B's receiving leg written first
    (the lower id). The issue names A's giving leg: ``transaction_id`` its id, ``broker_id`` A, ``transaction_date`` its date.

    Today: ``transaction_id`` is B's receiving leg (the lower id of the pair), ``broker_id`` A, no ``transaction_date`` —
    for both codes.
    """
    book = await seed_same_day_pair(session, giving=giving, short=short)
    out_leg, in_leg = book.rows["out_leg"], book.rows["in_leg"]

    result = await _analysis(session, book, [LotAnalysisType.LOT_SUMMARY])

    # Precondition: the receiving leg has the lower id, and the replay failed on this code alone.
    assert in_leg.id < out_leg.id
    assert (result.calculation_status, _issue_codes(result)) == ("FAILED", [code])
    issues = _issues(result, code)
    assert len(issues) == 1, [issue.message_params for issue in issues]
    params = issues[0].message_params
    observed = {"transaction_id": params.get("transaction_id"), "broker_id": params.get("broker_id"), "transaction_date": params.get("transaction_date")}
    assert observed == {"transaction_id": out_leg.id, "broker_id": book.broker_a.id, "transaction_date": FAILURE_DAY.isoformat()}


# --------------------------------------------------------------------------- #
# S5, S6 — DEGRADED and COMPLETE are unchanged
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(("seed", "status"), [(seed_degraded, "DEGRADED"), (seed_complete, "COMPLETE")], ids=["S5-degraded", "S6-complete"])
async def test_s5_s6_guard_degraded_and_complete_analyses_keep_every_section(session, seed, status):
    """GUARD (green today and after): S5, a DEGRADED analysis (lots opened by ADJUSTMENTs, no reference price, a cost basis
    missing), and S6, a COMPLETE one, keep every section and the orphans as numbers — a dividend makes the income events
    and the economic allocation groups non-empty."""
    book = await seed(session)

    result = await _analysis(session, book)

    assert result.calculation_status == status, _issue_codes(result)
    observed = {name: getattr(result, name) is not None for name in (*LOT_SECTIONS, *ORPHANS, "broker_wac_history", "cumulative_wac_history")}
    assert observed == dict.fromkeys(observed, True)
    assert result.lots and result.income_events and result.economic_allocation_groups, (result.lots, result.income_events, result.economic_allocation_groups)
