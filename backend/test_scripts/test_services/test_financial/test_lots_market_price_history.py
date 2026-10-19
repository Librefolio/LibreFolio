"""Y-30 (decision N89) — the lots analysis' market price line, independent of the lots: ``MARKET_PRICE_HISTORY``.

Workstream Y, release 1.3: the service-level reds of the series, through ``lots_analysis_service.get_lots_analysis``. The
FAILED half (the series stays when the replay fails, its rate gaps stay in the data quality) is beside J-12's contract in
``test_lots_failed_analysis_withholding.py``; the pure builder and the 1900 floor in ``test_lots_analysis_pure.py``; the
endpoint in ``test_api/test_portfolio_api.py``.

WHY. The price/WAC chart drew its price line from ``PRICE_HISTORY``, which is per lot: a point for each day of each
selected lot's life. With ``calculation_status == "FAILED"`` (J-12, N81) every lot section is None, ``price_history``
included, and the chart lost its price line; on a day with no lot open the line had a hole even when nothing failed.

THE CONTRACT.

- ``LotAnalysisType.MARKET_PRICE_HISTORY`` asks for ``LotsAnalysisResponse.market_price_history``, a list of
  ``MarketPriceHistoryPoint`` (``date``, ``market_price``, ``currency`` = the target currency, ``estimated``): the
  per-lot point without ``lot_id``. None unless requested.
- One point per day of the computed window — from the first transaction of the scope (never before 1900-01-01) to
  ``date_to`` — trimmed to ``[date_from or that first day, date_to]`` like the other histories, on each day that has a
  mark convertible to the target currency. The mark is the unified price resolver's (``financial_math/price_marks.py``):
  a market quote, exact or carried forward, is not estimated; else the last BUY or SELL, estimated. A day with no
  observation on or before it has no point, and so has a day whose rate is missing: that pair and day go to
  ``data_quality.missing_fx_pairs`` with their FX issue (``MISSING_FX_MARKET`` for a pair with no route), and a COMPLETE
  replay with such a gap is DEGRADED.
- Independent of the lots: a day with no lot open has its point, and ``selected_lot_ids`` does not change the series.
- It values nothing at cost, so asking for it never raises ``CURRENT_PRICE_ASSUMED_AT_COST``; its rates are asked for
  every day even when it is requested alone. ``PRICE_HISTORY`` (per lot) is unchanged.

TODAY (base ``7dbd46aa6``): the service normalizes the requested analyses first, and ``'MARKET_PRICE_HISTORY' is not a
valid LotAnalysisType`` (ValueError); the response has no ``market_price_history`` (AttributeError). The analysis is
asked for by its string and the field read inside the tests, so only these tests fail and the file still collects. Each
red says what it reads today in its docstring; GUARD marks a test green today and after.

Every test owns its rows: users, brokers and assets carry a uuid4 (``_scope_boundary_books.py``), written into the test's
session and rolled back by the ``session`` fixture. Everything is in EUR but the VND ledger, whose absent rate is owned
the same way (``_own_vnd_rates``). Dates in March 2025.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import Asset, AssetType, Broker, FxConversionRoute, FxRate, PriceHistory, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import LotAnalysisType, LotsAnalysisResponse
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.test_scripts.test_services._scope_boundary_books import add_prices, asset_row, new_asset, new_broker, new_user

D = Decimal
MARKET_PRICE_HISTORY = "MARKET_PRICE_HISTORY"  # asked for by its string: the LotAnalysisType member is new (Y-30)
# The lot sections and the average-cost lines: none of them is filled when only the series is asked for.
OTHER_SECTIONS = (
    "lots",
    "gantt_segments",
    "custody_history",
    "lot_events",
    "value_history",
    "return_history",
    "price_history",
    "performance_history",
    "income_events",
    "economic_allocation_groups",
    "broker_wac_history",
    "cumulative_wac_history",
)


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


# --------------------------------------------------------------------------- #
# Ledger LIFE — two lots, each sold whole, and the days between and after them
# --------------------------------------------------------------------------- #
#
# An EUR asset (quote_base_quantity 1), one broker. Lot 1: BUY 10 for 1000 EUR on 3 Mar, SELL 10 for 1040 EUR on 6 Mar.
# No lot open 7–9 Mar. Lot 2: BUY 5 for 530 EUR on 10 Mar, SELL 5 for 545 EUR on 13 Mar. No lot open 14–16 Mar, the
# reading day 16 Mar. Quoted 102 on 4 Mar, 105 on 7 Mar and 108 on 12 Mar: no quote on a trade day, so a trade marks it.

LIFE_FIRST_BUY = date(2025, 3, 3)
LIFE_FIRST_SALE = date(2025, 3, 6)
LIFE_SECOND_BUY = date(2025, 3, 10)
LIFE_SECOND_SALE = date(2025, 3, 13)
LIFE_DATE_TO = date(2025, 3, 16)
LIFE_QUOTES = {date(2025, 3, 4): "102", date(2025, 3, 7): "105", date(2025, 3, 12): "108"}
# Each day's mark, 3–16 Mar: (day, price, estimated). A quote, exact or carried, is not estimated; a trade is.
LIFE_LINE = [
    (date(2025, 3, 3), "100", True),  # the first BUY, 1000 / 10
    (date(2025, 3, 4), "102", False),  # quoted
    (date(2025, 3, 5), "102", False),  # carried
    (date(2025, 3, 6), "104", True),  # the first SELL, 1040 / 10
    (date(2025, 3, 7), "105", False),  # quoted — no lot open
    (date(2025, 3, 8), "105", False),  # carried — no lot open
    (date(2025, 3, 9), "105", False),  # carried — no lot open
    (date(2025, 3, 10), "106", True),  # the second BUY, 530 / 5
    (date(2025, 3, 11), "106", True),  # the trade carried
    (date(2025, 3, 12), "108", False),  # quoted
    (date(2025, 3, 13), "109", True),  # the second SELL, 545 / 5
    (date(2025, 3, 14), "109", True),  # carried — no lot open
    (date(2025, 3, 15), "109", True),  # carried — no lot open
    (date(2025, 3, 16), "109", True),  # carried — no lot open, the reading day
]
LOT_1_DAYS = _days(LIFE_FIRST_BUY, LIFE_FIRST_SALE)  # 3–6 Mar: the first lot's life, its sale day included
LOT_2_DAYS = _days(LIFE_SECOND_BUY, LIFE_SECOND_SALE)  # 10–13 Mar
NO_LOT_DAYS = [*_days(date(2025, 3, 7), date(2025, 3, 9)), *_days(date(2025, 3, 14), LIFE_DATE_TO)]

# --------------------------------------------------------------------------- #
# Ledger ESTIMATED — a lot opened before any observation
# --------------------------------------------------------------------------- #
#
# An EUR asset, one broker. On 3 Mar an ADJUSTMENT +10 at a cost of 100 EUR a unit (an inherited position: a cost, never
# a price); on 5 Mar a BUY of 2 for 220 EUR, the first observation; the first quote, 112, on 7 Mar; read on 10 Mar. So
# 3–4 Mar have no observation on or before them, and the lots are valued at cost there (J-17).

EST_ADJUSTMENT_DAY = date(2025, 3, 3)
EST_BUY_DAY = date(2025, 3, 5)
EST_QUOTE_DAY = date(2025, 3, 7)
EST_DATE_TO = date(2025, 3, 10)
EST_LINE = [
    (date(2025, 3, 5), "110", True),  # the BUY, 220 / 2: before the first quote, a trade mark
    (date(2025, 3, 6), "110", True),  # the trade carried
    (date(2025, 3, 7), "112", False),  # the first quote
    (date(2025, 3, 8), "112", False),  # the quote carried
    (date(2025, 3, 9), "112", False),
    (date(2025, 3, 10), "112", False),
]

# --------------------------------------------------------------------------- #
# Ledger VND — an asset quoted and bought in VND, read in EUR
# --------------------------------------------------------------------------- #
#
# A VND asset, one broker: BUY 100 for 2 500 000 VND on 3 Mar (25 000 a unit), quoted 26 000 VND on 5 Mar, read on 8 Mar
# in EUR. Every mark is in VND. VND/EUR has no rate and no route, owned: both are emptied for the pair inside the test's
# transaction (a neighbour's committed rate, however old, would backward-fill without limit). Optionally the test owns
# one rate, 1 EUR = 20 000 VND, on 6 Mar: from that day on 26 000 VND is 1.3 EUR.

VND_BUY_DAY = date(2025, 3, 3)
VND_QUOTE_DAY = date(2025, 3, 5)
VND_RATE_DAY = date(2025, 3, 6)
VND_DATE_TO = date(2025, 3, 8)


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


@dataclass(frozen=True)
class Book:
    owner: User
    broker: Broker
    asset: Asset
    rows: dict[str, Transaction] = field(default_factory=dict)


async def _add(session: AsyncSession, **rows: Transaction) -> dict[str, Transaction]:
    session.add_all(rows.values())
    await session.flush()
    return rows


async def seed_life(session: AsyncSession) -> Book:
    """Ledger LIFE (above): two lots, each sold whole, no lot open 7–9 and 14–16 Mar."""
    owner = await new_user(session, "y30_life")
    broker = await new_broker(session, "Y30 life", owner)
    asset = await new_asset(session, "Y30 life")
    add_prices(session, asset, LIFE_QUOTES)
    rows = await _add(
        session,
        buy=asset_row(broker, asset, TransactionType.BUY, LIFE_FIRST_BUY, "10", amount="-1000"),
        sell=asset_row(broker, asset, TransactionType.SELL, LIFE_FIRST_SALE, "-10", amount="1040"),
        rebuy=asset_row(broker, asset, TransactionType.BUY, LIFE_SECOND_BUY, "5", amount="-530"),
        resell=asset_row(broker, asset, TransactionType.SELL, LIFE_SECOND_SALE, "-5", amount="545"),
    )
    return Book(owner, broker, asset, rows)


async def seed_estimated(session: AsyncSession) -> Book:
    """Ledger ESTIMATED (above): an ADJUSTMENT's lot from 3 Mar, the first observation a BUY on 5 Mar, the first quote on 7 Mar."""
    owner = await new_user(session, "y30_est")
    broker = await new_broker(session, "Y30 est", owner)
    asset = await new_asset(session, "Y30 est")
    add_prices(session, asset, {EST_QUOTE_DAY: "112"})
    rows = await _add(
        session,
        adjustment=asset_row(broker, asset, TransactionType.ADJUSTMENT, EST_ADJUSTMENT_DAY, "10", cost="100"),
        buy=asset_row(broker, asset, TransactionType.BUY, EST_BUY_DAY, "2", amount="-220"),
    )
    return Book(owner, broker, asset, rows)


async def _own_vnd_rates(session: AsyncSession, *, rate_from: date | None) -> None:
    """VND/EUR as this test needs it: no rate and no route, but the one rate it writes from ``rate_from`` (None: none).

    The ``_own_fx_rate`` contract (``test_lots_analysis_service.py``) applied to an absence: ``fx_rates`` and
    ``fx_conversion_routes`` are global and store a pair alphabetically (EUR/VND), so both are emptied for it inside this
    test's transaction, which the ``session`` fixture rolls back — a neighbour's rows come back intact. With no route the
    pair is not configured, so its gap is ``MISSING_FX_MARKET``; a rate is read from ``fx_rates`` whatever the routes.
    """
    base, quote = sorted(("VND", "EUR"))
    await session.execute(delete(FxRate).where(FxRate.base == base, FxRate.quote == quote))
    await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == base, FxConversionRoute.quote == quote))
    if rate_from is not None:
        session.add(FxRate(date=rate_from, base=base, quote=quote, rate=D("20000"), source="TEST"))
    await session.flush()


async def seed_vnd(session: AsyncSession, *, rate_from: date | None) -> Book:
    """Ledger VND (above), VND/EUR owned: no rate before ``rate_from``, 20 000 VND a euro from it."""
    owner = await new_user(session, "y30_vnd")
    broker = await new_broker(session, "Y30 vnd", owner)
    tag = uuid4().hex[:16]
    asset = Asset(display_name=f"Y30 vnd {tag}", identifier_ticker=f"Y30V{tag[:8].upper()}", currency="VND", asset_type=AssetType.STOCK)
    session.add(asset)
    await session.flush()
    session.add(PriceHistory(asset_id=asset.id, date=VND_QUOTE_DAY, close=D("26000"), currency="VND", source_plugin_key="TEST"))
    await _own_vnd_rates(session, rate_from=rate_from)
    rows = await _add(session, buy=asset_row(broker, asset, TransactionType.BUY, VND_BUY_DAY, "100", amount="-2500000", currency="VND"))
    return Book(owner, broker, asset, rows)


# --------------------------------------------------------------------------- #
# Readings
# --------------------------------------------------------------------------- #


async def _analysis(
    session: AsyncSession,
    book: Book,
    analyses: list[LotAnalysisType | str],
    *,
    date_to: date,
    date_from: date | None = None,
    selected_lot_ids: list[int] | None = None,
) -> LotsAnalysisResponse:
    """The analysis of the book's asset over every broker its owner sees (the book's own), in EUR."""
    return await get_lots_analysis(
        session=session,
        user_id=book.owner.id,
        asset_id=book.asset.id,
        broker_ids=None,
        date_from=date_from,
        date_to=date_to,
        target_currency="EUR",
        selected_lot_ids=selected_lot_ids,
        requested_analyses=analyses,
    )


def _points(points) -> list[tuple]:
    """A price line, readably: (day, price, currency, estimated) in the answer's order."""
    return [(point.date, point.market_price, point.currency, point.estimated) for point in points]


def _expected(line, *, currency: str = "EUR") -> list[tuple]:
    return [(day, D(price), currency, estimated) for day, price, estimated in line]


def _issue_codes(result: LotsAnalysisResponse) -> list[str]:
    return sorted({str(issue.code) for issue in result.data_quality.issues})


def _missing_fx(result: LotsAnalysisResponse) -> dict[str, list[date]]:
    return {item.pair: list(item.dates) for item in result.data_quality.missing_fx_pairs}


def _market_issue_pairs(result: LotsAnalysisResponse) -> list[list[str]]:
    return [list(issue.affected_fx_pairs) for issue in result.data_quality.issues if str(issue.code) == "MISSING_FX_MARKET"]


# --------------------------------------------------------------------------- #
# A1 — a point on every marked day, whatever lot is open
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_market_price_guard_the_per_lot_price_history_stops_with_its_lots(session):
    """GUARD (green today and after): ``PRICE_HISTORY`` is per lot and unchanged by Y-30. On ledger LIFE the first lot has
    the marks of 3–6 Mar, the second those of 10–13 Mar — the same marks as the market line on those days (``LIFE_LINE``)
    — and no lot has a point on the days no lot is open, 7–9 and 14–16 Mar."""
    book = await seed_life(session)

    result = await _analysis(session, book, [LotAnalysisType.LOT_SUMMARY, LotAnalysisType.PRICE_HISTORY], date_to=LIFE_DATE_TO)

    assert result.calculation_status == "COMPLETE", _issue_codes(result)
    first_lot, second_lot = book.rows["buy"].id, book.rows["rebuy"].id
    assert sorted(lot.lot_id for lot in result.lots) == [first_lot, second_lot]
    by_lot = {lot_id: [(point.date, point.market_price, point.estimated) for point in result.price_history if point.lot_id == lot_id] for lot_id in (first_lot, second_lot)}
    marks = {day: (day, D(price), estimated) for day, price, estimated in LIFE_LINE}
    assert by_lot == {first_lot: [marks[day] for day in LOT_1_DAYS], second_lot: [marks[day] for day in LOT_2_DAYS]}
    assert {point.date for point in result.price_history} & set(NO_LOT_DAYS) == set()


@pytest.mark.asyncio
async def test_market_price_history_has_a_point_on_every_marked_day_whatever_lot_is_open(session):
    """A1: ledger LIFE, the per-lot line and the market line in one answer. The market line has one point for each day from
    the first transaction (3 Mar) to ``date_to`` (16 Mar), the quotes carried and the trades marking their days: on the
    days with no lot open too, between the first sale and the second purchase (7–9 Mar) and after the last sale (14–16
    Mar). The per-lot line of the same answer has none there: the control that the two differ.

    Today: ValueError — 'MARKET_PRICE_HISTORY' is not a valid LotAnalysisType.
    """
    book = await seed_life(session)

    result = await _analysis(session, book, [LotAnalysisType.PRICE_HISTORY, MARKET_PRICE_HISTORY], date_to=LIFE_DATE_TO)

    assert result.calculation_status == "COMPLETE", _issue_codes(result)
    assert _points(result.market_price_history) == _expected(LIFE_LINE)
    # The control, in the same answer: the per-lot line stops with its lots; the market line covers the days between.
    assert sorted({point.date for point in result.price_history}) == [*LOT_1_DAYS, *LOT_2_DAYS]
    assert set(NO_LOT_DAYS) <= {point.date for point in result.market_price_history}


# --------------------------------------------------------------------------- #
# A2 — selected_lot_ids does not change the series
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_market_price_history_ignores_selected_lot_ids(session):
    """A2: ledger LIFE, the first lot alone selected (its life is 3–6 Mar). The per-lot line follows the selection — the
    control that it took effect —, the market line does not: the same 14 points as with no selection, 3–16 Mar.

    Today: the precondition passes (the ledger has its two lots, each with the id of the BUY that opened it); then
    ValueError — 'MARKET_PRICE_HISTORY' is not a valid LotAnalysisType.
    """
    book = await seed_life(session)
    first_lot = book.rows["buy"].id
    # Precondition: two lots, the first opened by the first BUY (lot_id = opening_transaction_id).
    summary = await _analysis(session, book, [LotAnalysisType.LOT_SUMMARY], date_to=LIFE_DATE_TO)
    assert sorted(lot.lot_id for lot in summary.lots) == sorted([first_lot, book.rows["rebuy"].id])

    whole = await _analysis(session, book, [LotAnalysisType.PRICE_HISTORY, MARKET_PRICE_HISTORY], date_to=LIFE_DATE_TO)
    narrowed = await _analysis(session, book, [LotAnalysisType.PRICE_HISTORY, MARKET_PRICE_HISTORY], date_to=LIFE_DATE_TO, selected_lot_ids=[first_lot])

    assert ({point.lot_id for point in narrowed.price_history}, sorted({point.date for point in narrowed.price_history})) == ({first_lot}, LOT_1_DAYS)
    assert _points(narrowed.market_price_history) == _points(whole.market_price_history) == _expected(LIFE_LINE)


# --------------------------------------------------------------------------- #
# A3 — estimated only on a trade's mark; no point before any observation
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_market_price_history_estimated_only_on_a_trade_mark_and_no_point_before_any_observation(session):
    """A3: ledger ESTIMATED, the series alone. 3–4 Mar have no observation on or before them (the ADJUSTMENT's cost is
    no price): no point. 5–6 Mar the BUY's 110, estimated (a trade's mark, before the first quote). From 7 Mar the quote,
    112, exact then carried: not estimated. The ADJUSTMENT's lot is open every day, so its per-lot line reads the same
    points — the precondition, which checks this ledger's marks today.

    Today: the precondition passes (the lot's per-lot line is ``EST_LINE``); then ValueError — 'MARKET_PRICE_HISTORY' is
    not a valid LotAnalysisType.
    """
    book = await seed_estimated(session)
    adjustment_lot = book.rows["adjustment"].id
    # Precondition: the lot open all along has exactly these marks, and none on 3–4 Mar.
    per_lot = await _analysis(session, book, [LotAnalysisType.PRICE_HISTORY], date_to=EST_DATE_TO)
    assert _points(point for point in per_lot.price_history if point.lot_id == adjustment_lot) == _expected(EST_LINE)

    result = await _analysis(session, book, [MARKET_PRICE_HISTORY], date_to=EST_DATE_TO)

    assert _points(result.market_price_history) == _expected(EST_LINE)
    assert min(point.date for point in result.market_price_history) == EST_BUY_DAY


# --------------------------------------------------------------------------- #
# A4 — trimmed to [date_from, date_to]
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_market_price_history_is_trimmed_to_date_from_and_date_to(session):
    """A4: ledger LIFE read from 8 Mar (a day with no lot open, after the first transaction) to 15 Mar. The window is still
    computed from the first transaction (3 Mar) — 8 Mar carries 7 Mar's quote — but the series is trimmed like the other
    histories: its first point on ``date_from``, its last on ``date_to``.

    Today: ValueError — 'MARKET_PRICE_HISTORY' is not a valid LotAnalysisType.
    """
    book = await seed_life(session)
    date_from, date_to = date(2025, 3, 8), date(2025, 3, 15)

    result = await _analysis(session, book, [MARKET_PRICE_HISTORY], date_from=date_from, date_to=date_to)

    assert result.calculation_metadata.computed_date_from == LIFE_FIRST_BUY
    assert _points(result.market_price_history) == _expected([(day, price, estimated) for day, price, estimated in LIFE_LINE if date_from <= day <= date_to])
    dates = [point.date for point in result.market_price_history]
    assert (min(dates), max(dates)) == (date_from, date_to)


# --------------------------------------------------------------------------- #
# A5 — a day without a rate has no point, and the gap is reported
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rate_from", "points", "missing_days"),
    [
        pytest.param(None, [], _days(VND_BUY_DAY, VND_DATE_TO), id="no-rate"),
        pytest.param(VND_RATE_DAY, [(day, "1.3", False) for day in _days(VND_RATE_DAY, VND_DATE_TO)], _days(VND_BUY_DAY, date(2025, 3, 5)), id="a-rate-from-6-Mar"),
    ],
)
async def test_market_price_history_has_no_point_on_a_day_without_a_rate_and_reports_the_gap(session, rate_from, points, missing_days):
    """A5: ledger VND, read in EUR, the series alone. Every day from the BUY (3 Mar) has a mark in VND; a day without a
    VND/EUR rate has no point — never the VND price read as euros —, and the gap is reported: VND/EUR in
    ``missing_fx_pairs`` with exactly those days, ``MISSING_FX_MARKET`` for the pair (no route: not configured), and the
    COMPLETE replay DEGRADED. With no rate at all: no point, 3–8 Mar missing. With a rate owned from 6 Mar (20 000 VND a
    euro): 26 000 VND is 1.3 EUR on 6–8 Mar (the quote carried, not estimated), 3–5 Mar missing — which also proves the
    series asks for its rates when it is requested alone. The per-lot line of the lot open all along reads the same points
    and reports the same gap: the precondition, which checks the rates this test owns today.

    Today: the precondition passes; then ValueError — 'MARKET_PRICE_HISTORY' is not a valid LotAnalysisType.
    """
    book = await seed_vnd(session, rate_from=rate_from)
    expected_points = _expected(points)
    # Precondition: the per-lot line on the same rates — the same points, the same gap, reported the same way.
    per_lot = await _analysis(session, book, [LotAnalysisType.PRICE_HISTORY], date_to=VND_DATE_TO)
    assert (per_lot.calculation_status, _points(per_lot.price_history), _missing_fx(per_lot), _market_issue_pairs(per_lot)) == ("DEGRADED", expected_points, {"VND/EUR": missing_days}, [["EUR-VND"]])

    result = await _analysis(session, book, [MARKET_PRICE_HISTORY], date_to=VND_DATE_TO)

    assert _points(result.market_price_history) == expected_points
    assert _missing_fx(result) == {"VND/EUR": missing_days}
    assert _market_issue_pairs(result) == [["EUR-VND"]]
    assert result.calculation_status == "DEGRADED"


# --------------------------------------------------------------------------- #
# A6 — asked alone: only the series, never a price at cost
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_market_price_history_alone_fills_only_the_series_and_never_assumes_the_price_at_cost(session):
    """A6: ledger ESTIMATED, whose first two days (3–4 Mar) have no observation, the series alone. Only
    ``market_price_history`` is filled: the lot sections and the average-cost lines are None. The series values nothing
    at cost, so no ``CURRENT_PRICE_ASSUMED_AT_COST``: that issue stays with the analyses that value the lots — the
    precondition shows the value history raising it on this ledger, for 3–4 Mar.

    Today: the precondition passes; then ValueError — 'MARKET_PRICE_HISTORY' is not a valid LotAnalysisType.
    """
    book = await seed_estimated(session)
    # Precondition: valuing the lots, this ledger has days at cost — 3 and 4 Mar.
    valued = await _analysis(session, book, [LotAnalysisType.VALUE_HISTORY], date_to=EST_DATE_TO)
    at_cost = [issue.message_params for issue in valued.data_quality.issues if str(issue.code) == "CURRENT_PRICE_ASSUMED_AT_COST"]
    assert [(params["date_from"], params["date_to"]) for params in at_cost] == [(EST_ADJUSTMENT_DAY.isoformat(), date(2025, 3, 4).isoformat())]

    result = await _analysis(session, book, [MARKET_PRICE_HISTORY], date_to=EST_DATE_TO)

    assert _points(result.market_price_history) == _expected(EST_LINE)
    assert {name: getattr(result, name) for name in OTHER_SECTIONS} == dict.fromkeys(OTHER_SECTIONS)
    assert "CURRENT_PRICE_ASSUMED_AT_COST" not in _issue_codes(result)


# --------------------------------------------------------------------------- #
# A7 — None unless requested
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_market_price_history_is_none_unless_requested(session):
    """A7: ledger LIFE, every other analysis requested — the lot sections, the per-lot price line, the average-cost lines,
    the performance, the income markers: ``market_price_history`` is None, like every section nobody asked for.

    Today: the analysis answers, and AttributeError — the response has no ``market_price_history``.
    """
    book = await seed_life(session)
    every_other = [analysis for analysis in LotAnalysisType if analysis != MARKET_PRICE_HISTORY]

    result = await _analysis(session, book, every_other, date_to=LIFE_DATE_TO)

    assert result.price_history, "precondition: the per-lot price line was computed"
    assert result.market_price_history is None
