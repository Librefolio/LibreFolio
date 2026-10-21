"""MF-E2 — a short position in the lots' performance history, through the service: the developer's worked example, and L1a's
parity on a book with a short.

Workstream MF, lot E2: the service-level red, through ``lots_analysis_service.get_lots_analysis`` with
``PERFORMANCE_HISTORY`` alone. The builder's contract is pinned purely in
``test_lots_analysis_pure.py::TestShortPositionsInThePerformanceHistory`` (its section header states it).

THE DEFECT. ``build_performance_history`` reads a short as if owned: its fragment, stored with a positive quantity, counts
+q·p; the sale that opens it is no flow, so the line starts on the buy-back, a deposit. A short that gained 200 on 1 000
reads ROI −100% and TWRR −180%.

THE RULE (developer, option (b), convention (1) «gross exposure», E2-Q1). An open short counts −q·p; its opening proceeds
are a flow out of the position on its opening date; TWRR compounds each day's change over the previous day's gross
exposure (Σ |value|); ROI reads the gain over the capital, the long leg's net deposits plus the short sales' cumulative
proceeds.

THE BOOK. U owns broker S, which allows shorting, and broker L. An EUR asset, its own rows: S sells 10 short at 100 on
Sunday 5 Jan 2025 (proceeds 1 000) and buys them back at 80 on Wednesday 8 Jan (pays 800); L buys 3 at 100 on 5 Jan;
quotes 100, 90, 80 and 80 from 5 to 8 Jan. Read on 8 Jan with ``broker_ids=[S]``: U can see L too, so the performance
history is replayed over both brokers and read for S alone — the path a filtered page takes. L's lot is in the replay,
out of the scope: the series is S's short alone.

Rows written into the test's session with uuid4 names (``_scope_boundary_books.py``) and rolled back. EUR only: no rate is
asked.

L1a PARITY WITH A SHORT (``test_l1a_parity_…``; PARITY: green before and after L1a, MF-E2b included). J's battery,
``test_lots_change_days_parity.py``, compares the analysis computed on its change days (A, as it is) with the one computed
on every day (B, ``lots_analysis_service.lot_change_days`` answering every day), every ``LotAnalysisType`` requested. Its
``short`` book is EUR-only and buys its short back whole. The book here adds what that one has not: a short bought back in
part, the opening sale and the buy-back on days whose close repeats the previous one (only the event dates name them),
closes with gaps, and days whose price has no rate — a flow among them. J's helpers are imported, not copied; J's file is
untouched.

THE BOOK (``seed_short_partial_no_rate``). EUR; U owns A (shorting) and B. Closes on Mondays, Wednesdays and Fridays, 8 Jan –
27 Mar 2024, none on 11–15 Mar; on Wed 21 and Fri 23 Feb the close is in VND, which has no rate or route to EUR (owned, as
J's ``unknown-pools``): no price from 21 to 25 Feb, a close winning over the trades of its day. B buys 6 at 100 on Mon
8 Jan; A sells 10 short at 102 on Wed 17 Jan (closed 102, as on Mon 15 Jan) and buys 4 back at 95 on Wed 7 Feb (closed 95,
as on Mon 5 Feb); B buys 2 at 95 on Fri 23 Feb, a day without a price. Read to Fri 29 Mar, in J's windows (``_windows``),
over every broker, A (the performance re-run over A and B) and B.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import PriceHistory, TransactionType
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import LotAnalysisType, LotsAnalysisResponse
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.test_scripts.test_services._scope_boundary_books import add_prices, asset_row, new_asset, new_broker, new_user
from backend.test_scripts.test_services.test_financial.test_lots_change_days_parity import Book, _as_is_and_every_day, _assert_not_vacuous, _dump, _first_difference, _own_no_rate, _point_counts, _windows

SHORT_SALE_DAY = date(2025, 1, 5)
BUY_BACK_DAY = date(2025, 1, 8)
PRICES = {date(2025, 1, 5): "100", date(2025, 1, 6): "90", date(2025, 1, 7): "80", date(2025, 1, 8): "80"}


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


@pytest.mark.asyncio
async def test_the_worked_example_shows_the_shorts_gain(session):
    """(date, ROI, TWRR) from 5 to 8 Jan: (0, —), (10%, 10%), (20%, 22.2222%), (20%, 22.2222%) — the approved figures. NAV
    −1 000, −900, −800, 0; flows +1 000 on 5 Jan and −800 on 8 Jan; capital 1 000; TWRR 1.1 × (1 + 100 / 900) − 1.

    Today (read 20/10/2026): no point on 5–7 Jan, and on 8 Jan ROI −1 and TWRR −1.8.
    """
    owner = await new_user(session, "e2")
    short_broker = await new_broker(session, "E2 S", owner)
    short_broker.allow_asset_shorting = True
    long_broker = await new_broker(session, "E2 L", owner)
    asset = await new_asset(session, "E2 short")
    add_prices(session, asset, PRICES)
    session.add_all(
        [
            asset_row(short_broker, asset, TransactionType.SELL, SHORT_SALE_DAY, "-10", amount="1000"),
            asset_row(short_broker, asset, TransactionType.BUY, BUY_BACK_DAY, "10", amount="-800"),
            asset_row(long_broker, asset, TransactionType.BUY, SHORT_SALE_DAY, "3", amount="-300"),
        ]
    )
    await session.flush()

    result = await get_lots_analysis(
        session=session,
        user_id=owner.id,
        asset_id=asset.id,
        broker_ids=[short_broker.id],
        date_from=None,
        date_to=BUY_BACK_DAY,
        target_currency="EUR",
        selected_lot_ids=None,
        requested_analyses=[LotAnalysisType.PERFORMANCE_HISTORY],
    )

    # Precondition, green today and after: the replay is not FAILED, so the performance history is given (J-12).
    assert result.performance_history is not None, (result.calculation_status, result.data_quality)
    observed = [(point.date, point.roi, point.twrr) for point in result.performance_history]
    assert observed == [
        (date(2025, 1, 5), Decimal("0"), None),
        (date(2025, 1, 6), Decimal("0.1"), Decimal("0.1")),
        (date(2025, 1, 7), Decimal("0.2"), Decimal("0.222222")),
        (date(2025, 1, 8), Decimal("0.2"), Decimal("0.222222")),
    ]


# --------------------------------------------------------------------------- #
# L1a parity with a short (module docstring, L1a PARITY WITH A SHORT)
# --------------------------------------------------------------------------- #

PARITY_FIRST_DAY = date(2024, 1, 8)  # Mon: B's purchase, the first transaction
PARITY_SHORT_DAY = date(2024, 1, 17)  # Wed: A's short sale, closed as on Mon 15 Jan
PARITY_BUY_BACK_DAY = date(2024, 2, 7)  # Wed: A's partial buy-back, closed as on Mon 5 Feb
PARITY_NO_RATE = (date(2024, 2, 21), date(2024, 2, 25))  # Wed – Sun: the last observation is a VND close
PARITY_GAP_BUY_DAY = date(2024, 2, 23)  # Fri: B's purchase, a day without a price
PARITY_DATE_TO = date(2024, 3, 29)  # Fri
PARITY_CLOSES = {
    **{date(2024, 1, 8) + timedelta(days=offset): close for offset, close in ((0, "100"), (2, "101"), (4, "103"), (7, "102"), (9, "102"), (11, "104"), (14, "99"), (16, "98"), (18, "97"))},
    **{date(2024, 1, 29) + timedelta(days=offset): close for offset, close in ((0, "96"), (2, "98"), (4, "97"), (7, "95"), (9, "95"), (11, "94"), (14, "96"), (16, "97"), (18, "95"), (21, "94"))},
    **{date(2024, 2, 26) + timedelta(days=offset): close for offset, close in ((0, "93"), (2, "92"), (4, "94"), (7, "95"), (9, "93"), (11, "92"), (21, "90"), (23, "91"), (25, "89"), (28, "88"), (30, "90"))},
}
PARITY_VND_CLOSES = {date(2024, 2, 21): "2500000", date(2024, 2, 23): "2500000"}
PARITY_SCOPES = ("owner-all", "owner-A", "owner-B")
PARITY_WINDOWS = _windows(PARITY_FIRST_DAY, PARITY_DATE_TO)


async def seed_short_partial_no_rate(session: AsyncSession) -> Book:
    """The book of the module docstring (L1a PARITY WITH A SHORT), every row the test's own."""
    await _own_no_rate(session, "VND")
    owner = await new_user(session, "e2_l1a")
    brokers = {"A": await new_broker(session, "E2 L1a A", owner), "B": await new_broker(session, "E2 L1a B", owner)}
    brokers["A"].allow_asset_shorting = True
    asset = await new_asset(session, "E2 L1a short")
    add_prices(session, asset, PARITY_CLOSES)
    session.add_all([PriceHistory(asset_id=asset.id, date=day, close=Decimal(close), currency="VND", source_plugin_key="TEST") for day, close in PARITY_VND_CLOSES.items()])
    a, b = brokers["A"], brokers["B"]
    rows = {
        "long": asset_row(b, asset, TransactionType.BUY, PARITY_FIRST_DAY, "6", amount="-600"),
        "short": asset_row(a, asset, TransactionType.SELL, PARITY_SHORT_DAY, "-10", amount="1020"),
        "bought_back": asset_row(a, asset, TransactionType.BUY, PARITY_BUY_BACK_DAY, "4", amount="-380"),
        "gap_buy": asset_row(b, asset, TransactionType.BUY, PARITY_GAP_BUY_DAY, "2", amount="-190"),
    }
    session.add_all(rows.values())
    await session.flush()
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


def _check_short_partial_no_rate(book: Book, result: LotsAnalysisResponse) -> None:
    """Precondition, on the whole window over every broker: the book is what it says. The replay is not FAILED; the short is
    a lot of 10 with 6 still open; VND/EUR is reported missing; the market price line and the performance have no point
    on 21–25 Feb and have one on 19 and 26 Feb; the opening sale's and the buy-back's days change no price."""
    short = next((lot for lot in result.lots or [] if lot.lot_id == book.rows["short"].id), None)
    pairs = sorted(item.pair for item in result.data_quality.missing_fx_pairs) if result.data_quality else []
    priced = {point.date: point.market_price for point in result.market_price_history or []}
    performance = {point.date: point.roi for point in result.performance_history or []}
    no_rate_days = [PARITY_NO_RATE[0] + timedelta(days=offset) for offset in range((PARITY_NO_RATE[1] - PARITY_NO_RATE[0]).days + 1)]
    observed = {
        "status": result.calculation_status != "FAILED",
        "short (direction, original, open)": None if short is None else (str(short.direction), short.original_quantity, short.open_quantity),
        "VND/EUR missing": "VND/EUR" in pairs,
        "no price, no performance on 21–25 Feb": all(day not in priced and performance.get(day) is None for day in no_rate_days),
        "a price and a performance on 19 and 26 Feb": all(day in priced and performance.get(day) is not None for day in (date(2024, 2, 19), date(2024, 2, 26))),
        "the short's and the buy-back's days repeat the close before": (priced[PARITY_SHORT_DAY] == priced[PARITY_SHORT_DAY - timedelta(days=2)], priced[PARITY_BUY_BACK_DAY] == priced[PARITY_BUY_BACK_DAY - timedelta(days=2)]),
    }
    assert observed == {
        "status": True,
        "short (direction, original, open)": ("SHORT", Decimal("10"), Decimal("6")),
        "VND/EUR missing": True,
        "no price, no performance on 21–25 Feb": True,
        "a price and a performance on 19 and 26 Feb": True,
        "the short's and the buy-back's days repeat the close before": (True, True),
    }, f"precondition: the book is not what it says, {observed}"


async def short_book_parity(session: AsyncSession, monkeypatch: pytest.MonkeyPatch, window: str, scope: str) -> str | None:
    """Seed the book, read it in ``window`` over ``scope`` as it is (A) and on every day (B); the first JSON path where they
    differ, None when they agree. On the whole window over every broker it first proves the book is what it says."""
    book = await seed_short_partial_no_rate(session)
    date_from, date_to = PARITY_WINDOWS[window]
    broker_ids = None if scope == "owner-all" else [book.brokers[scope.split("-", 1)[1]].id]
    as_is, every_day = await _as_is_and_every_day(session, monkeypatch, user=book.users["owner"], asset=book.asset, broker_ids=broker_ids, date_from=date_from, date_to=date_to)
    _assert_not_vacuous(as_is, empty_window=date_from is not None and date_from > date_to)
    if window == "whole" and scope == "owner-all":
        _check_short_partial_no_rate(book, as_is)
    difference = _first_difference(_dump(as_is), _dump(every_day))
    return None if difference is None else f"{difference} — points A/B {_point_counts(as_is, every_day)}"


@pytest.mark.asyncio
@pytest.mark.parametrize(("window", "scope"), [pytest.param(window, scope, id=f"{window}/{scope}") for window in PARITY_WINDOWS for scope in PARITY_SCOPES])
async def test_l1a_parity_a_short_bought_back_in_part_across_days_without_a_rate(session, monkeypatch, window, scope):
    """PARITY (green today, and after MF-E2b). The book of the module docstring read in ``window`` over ``scope``, every
    analysis: computed on its change days, the answer dumps to the same JSON as computed on every day (J's battery, its
    helpers), the generation day aside; not between two empty answers, and on the whole window over every broker the book
    proves what it is (``_check_short_partial_no_rate``)."""
    difference = await short_book_parity(session, monkeypatch, window, scope)

    assert difference is None, f"{window} / {scope}: on its change days the answer differs from every day's at {difference}"
