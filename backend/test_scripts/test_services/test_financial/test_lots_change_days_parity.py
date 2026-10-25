"""L1a — the lots analysis computed on its change days, through the service: the cost reds and the parity battery.

Workstream J «Numeri e analisi», lot L1a. The pure contract (``lot_change_days``, ``expand_to_days``, the bisected
``last_day_without_observation``) is pinned in ``test_financial_math/test_lot_change_days.py``; here the service on the
lane's database, through ``lots_analysis_service.get_lots_analysis``.

WHY. ``get_lots_analysis`` builds ``history_dates`` — every calendar day from the scope's first transaction (floored at
1900-01-01) to ``date_to`` — and hands them to the per-day builders (``financial_math/lots/histories.py``,
``lots/average_cost_lines.py``), then trims to the window. A lot bought on 2 Jan 1900 and read on 15 Feb 2021 is valued on
44 240 days, whatever the window: ``_lot_snapshot_on_date`` twice a day (value and return histories) and
``_open_value_on_date`` three times (once inside each snapshot, once in the performance NAV) — about 221 000 calls to
answer 31 days.

THE CURE (J, L1a). The builders, unchanged, receive only the change days — ``lot_change_days``, new home
``financial_math/lots/change_days.py``, called by the service through its own namespace
(``lots_analysis_service.lot_change_days``) — and ``expand_to_days`` fills every day of the window from the last change
day on or before it. The answer must not move by one byte: one point per day of the window, the same figures in the same
representation.

THE REDS (RED until L1a), on the 1900 book read over its last 30 days: (1) ``_lot_snapshot_on_date`` and
``_open_value_on_date`` together are called at most 400 times (today about 221 000); (2) ``lot_change_days`` is called
exactly once (today the name does not exist: never called).

THE PARITY BATTERY (PARITY: green today and after the cure — the guarantee). Each case runs the analysis twice in the
same session, every ``LotAnalysisType`` requested: A as it is; B with ``lots_analysis_service.lot_change_days`` replaced
by «every day is a change day» (``raising=False``, undone before the comparison). Today the name does not exist and the
patch changes nothing, so A == B trivially; after the cure B is today's computation. The two answers must dump to the
same JSON (``model_dump(mode="json")``) but for ``calculation_metadata.generated_at``, the wall clock's date, which is
never compared; a difference is reported by its first path. Before comparing, the case checks it is not comparing
nothing: a window that ends before it starts has no daily point, any other its market price line; and, on its whole
window in its first scope, each book proves it is what it says (its ``check``).

THE BOOKS (``SCENARIOS``; days of the week matter: a close, a trade or an event that changes nothing in the prices is the
day only the event dates can name).

- ``fx-daily`` — a HUF asset read in EUR; U owns A and B. HUF closes every Monday, 4 Jan 1937 – 26 Dec 1938 (a seeded
  walk from 5 000). EUR/HUF on every calendar day, 28 Dec 1936 – 31 Dec 1938 (a seeded walk around 390), but none on
  6–10 Dec 1937: 5 Dec's rate is carried over them. EUR/ISK on 28 Dec 1936, 10 Nov 1937 and 1 Jun 1938. A: BUY 10 (Mon
  4 Jan 1937), BUY 6 (Wed 3 Mar), SELL 4 (Wed 16 Jun), BUY 3 in ISK — a third currency — (Wed 10 Nov), a DIVIDEND and a
  TAX inside the rate gap (Wed 8 Dec), a FEE and the SELL 6 that closes the first lot (Wed 2 Feb 1938), SELL 2 (Wed 7
  Sep). B: BUY 5 (Wed 5 May 1937), SELL 5 — the whole lot — (Wed 4 May 1938). Read to Fri 30 Dec 1938.
- ``at-cost`` — EUR. An ADJUSTMENT-in of 10 at a cost of 100 on Mon 5 Feb 2024, before any observation; closes every
  Wednesday, 6 Mar – 26 Jun; BUY 5 at 112 on Thu 21 Mar (a trade's mark until the next close), SELL 4 at 117 on Thu 16
  May. Read to Fri 28 Jun. Valued at cost on 5 Feb – 5 Mar.
- ``representation`` — EUR. BUY 15 for 1 650 on Wed 3 Apr 2024, before any close: its mark, 1 650 / 15, reads ``110``
  (estimated) on 3 Apr and is carried to Sun 7 Apr; closes 110 (Mon 8 Apr), 115 (Mon 15 and Mon 22 Apr), 116 (Mon 6 May);
  a DIVIDEND of 15 on Wed 8 May. Read to Fri 17 May. On 8 Apr, a day without any transaction, the price keeps its value
  and changes its representation, ``110`` → ``110.000000`` (and its flag, estimated → not): the figures built on it
  change their digits that day, so it must be a change day though no row falls on it. Through the DB equal closes read
  back alike (``RealDecimal`` pads them to six decimals: 115 and 115.0 both read ``115.000000``); the representation
  contract of ``lot_change_days`` (prices written 1.1 and 1.10, and the like) is pinned by the unit file.
- ``at-cost-then-no-rate`` — EUR, VND without a rate or a route to EUR (owned). An ADJUSTMENT-in of 10 at 100 on Mon
  5 Feb 2024; the first observation a close in VND on Wed 14 Feb; EUR closes every Monday from 4 Mar; BUY 4 at 106 on
  Wed 13 Mar. Read to Fri 29 Mar. At cost 5–13 Feb, no value 14 Feb – 3 Mar: on 14 Feb no price changes (None before,
  None after), only the end of the days at cost does.
- ``transfer-in-transit`` — EUR; U owns A and B, V owns B. Mondays closed, 8 Jan – 25 Mar 2024. A buys 10 at 100 on Mon
  8 Jan and sends them on Wed 7 Feb; B receives them on Tue 13 Feb at a cost basis of 100 (in transit 7–12 Feb), sells
  4 at 115 on Wed 6 Mar, cashes a DIVIDEND of 12 on Wed 20 Mar. Read to Fri 29 Mar. U filtering A or B: the
  performance re-runs over A and B (the brokers U can see); V reads B at its edge.
- ``l1-boundary``, ``l2-in-transit-at-date-to`` — ledgers L1 (read 16 Jan 2025) and L2 (in transit on 14 Jan 2025) of
  ``_scope_boundary_books.py``, read by U over each broker alone; L1 also by V, an owner of B only. L2 is not read with
  B alone: B has no row by 14 Jan (its leg is dated the 16th), so that answer is empty.
- ``split`` — EUR. BUY 10 at 100 on Wed 10 Jan 2024; a 2:1 SPLIT event on Thu 1 Feb with its ADJUSTMENT +10 (no close
  that day: 1 Feb changes no price); closes halve from Mon 5 Feb; SELL 6 at 55 on Thu 7 Mar, DIVIDEND 8 on Thu 14 Mar.
  Read to Fri 29 Mar.
- ``short`` — EUR; A allows shorting. SELL 5 at 120 on Wed 10 Jan 2024 (short), BUY 5 at 105 on Wed 14 Feb (bought
  back), SELL 3 at 106 on Wed 28 Feb (short again, still open). Mondays closed. Read to Fri 29 Mar.
- ``unknown-pools`` — EUR, VND without a rate or a route (owned). BUY 10 at 100 on Mon 8 Jan 2024; a DIVIDEND of 80 VND
  on Wed 24 Jan (the lot's income withheld from that day); BUY 5 for 2 600 000 VND on Wed 7 Feb (its cost and its mark
  have no rate: the performance is invalid from that day, no market price until Monday's close); SELL 2 for 230 000 VND
  on Wed 6 Mar (proceeds without a rate: the first lot's values stop the day before); a DIVIDEND of 20 EUR on Wed 13 Mar.
  Mondays closed. Read to Fri 29 Mar.
- ``failed`` — EUR; U owns A (no shorting) and B. A buys 5 (Mon 8 Jan 2024), cashes 10 (Wed 10 Jan) and sells 8 (Wed 17
  Jan): FAILED. B buys 4 (Wed 24 Jan) and sells 1 on Mon 11 Mar, closed 108 as on 4 Mar: a sale that moves no price.
  Read over every broker (FAILED), A (FAILED) and B (COMPLETE), to Fri 29 Mar.
- ``selected-lots`` — EUR. BUY 10 (Mon 8 Jan 2024, closed 100), BUY 4 (Mon 15 Jan, closed 100 again: a purchase that
  moves no price), BUY 6 (Mon 22 Jan, 102), SELL 12 (Wed 14 Feb), DIVIDEND 20 (Wed 21 Feb). Read to Fri 29 Mar with
  ``selected_lot_ids`` = the second and the third lot.
- ``1900`` — the reds' book. EUR. BUY 10 at 100 on 2 Jan 1900; closes 101 (2 Mar 2020), 103 (1 Jun), 99 (1 Sep), 105
  (1 Dec); SELL 4 at 105 on 15 Oct 2020. Read over 16 Jan – 15 Feb 2021 only: in the battery once, B costing what
  today's computation costs.

THE WINDOWS (``_windows``): the whole book (``date_from`` None); from a week before its first transaction; its second
half; its last month and its last year, when it is longer; a window in its middle, ``date_to`` moved to two thirds of
it; and one that ends before it starts (``date_from`` the day after ``date_to``; the service accepts it and trims every
history to nothing). The scopes: ``reader-brokers``, the reader by label and a broker by label, ``all`` for
``broker_ids`` None.

ISOLATION. Every row is written into the test's session and flushed, never committed: the ``session`` fixture rolls it
back. Users, brokers and assets carry a uuid4 (``_scope_boundary_books.py``). FX rates are global rows: EUR/HUF and EUR/ISK
over 1 Dec 1936 – 31 Jan 1939 are this file's own — a row a neighbour committed there is deleted inside the test's
transaction and comes back with the rollback —, and VND's absence is owned the same way (``_own_no_rate``), as
``test_lots_market_price_history.py`` owns it.

TODAY (HEAD ``b675ada54``): both reds fail on their assertion; every PARITY case is green.

J5-5 (steps, contract MF-P4b §1.3, §8): the seven histories become STEPS (``date`` .. ``through``) and the answer carries
``range``. The reds at the end of the file (RED until the cure): ``test_red_every_history_is_a_list_of_steps`` (shape,
maximality, A == B once expanded, over every PARITY case), ``test_red_the_1900_lot_is_a_few_steps``,
``test_red_a_price_representation_change_is_a_step_boundary`` (8 Apr 2024 of book ``representation``) and
``test_red_a_year_one_typo_costs_steps_not_days`` (floor lowered in this process, measured on HEAD: 737 854 calls of
``AssetPriceSeries.resolve``, 613 s, 3.9 GB). The ``test_guard_the_step_checker_*`` tests prove the checker itself on
pure cases and on the real books. The answer is read as ``model_dump(mode="json")`` dicts: no new class is imported.
"""

import random
import sys
import time
import tracemalloc
from collections import Counter
from collections.abc import Awaitable, Callable, Mapping, Sequence
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

from backend.app.db.models import Asset, AssetEvent, AssetEventType, AssetType, Broker, FxConversionRoute, FxRate, PriceHistory, Transaction, TransactionType, User
from backend.app.db.session import get_async_engine
from backend.app.schemas.portfolio import LotAnalysisType, LotsAnalysisResponse
from backend.app.services import lots_analysis_service
from backend.app.services.financial_math.lots import histories
from backend.app.services.financial_math.price_marks import AssetPriceSeries
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.test_scripts.test_services._lots_steps import as_daily_rows, compress_days, expand_steps, order_by_key, rows_by_key, step_values
from backend.test_scripts.test_services._scope_boundary_books import (
    L1_BUY_DAY,
    L1_DATE_TO,
    L2_BUY_DAY,
    L2_DATE_TO,
    add_prices,
    asset_row,
    grant_owner,
    link,
    new_asset,
    new_broker,
    new_user,
    seed_l1,
    seed_l2,
)

EUR = "EUR"
ALL_ANALYSES = list(LotAnalysisType)
# The seven history sections, each with the field that keys its rows (None: one line for the whole scope). Since J5-5 a
# row is a STEP (``date`` .. ``through``), not a day; the change days fill them.
STEP_KEYS: dict[str, str | None] = {
    "value_history": "lot_id",
    "return_history": "lot_id",
    "price_history": "lot_id",
    "market_price_history": None,
    "broker_wac_history": "broker_id",
    "cumulative_wac_history": None,
    "performance_history": None,
}
DAILY_SECTIONS = tuple(STEP_KEYS)
# The per-day steps the reds count, on the module that calls them (histories.py reads both through its globals).
COUNTED_STEPS = ("_lot_snapshot_on_date", "_open_value_on_date")
CALL_BUDGET = 400

Q1_FIRST_MONDAY = date(2024, 1, 8)
Q1_DATE_TO = date(2024, 3, 29)  # a Friday
AT_COST_DAY = date(2024, 2, 5)  # a Monday: the ADJUSTMENT-in at a cost, before any observation
FX_FIRST_DAY = date(1937, 1, 4)  # a Monday
FX_DATE_TO = date(1938, 12, 30)  # a Friday
FX_RATE_SPAN = (date(1936, 12, 1), date(1939, 1, 31))  # the EUR/HUF and EUR/ISK rows this file owns
FX_GAP = (date(1937, 12, 6), date(1937, 12, 10))  # Monday to Friday without an EUR/HUF rate
FX_ISK_RATES = {date(1936, 12, 28): Decimal("150.25"), date(1937, 11, 10): Decimal("152.5"), date(1938, 6, 1): Decimal("149.75")}
REPRESENTATION_FIRST_DAY = date(2024, 4, 3)  # a Wednesday: the BUY, before any close
REPRESENTATION_CLOSE_DAY = date(2024, 4, 8)  # a Monday without a transaction: the first close, equal to the BUY's price
REPRESENTATION_DATE_TO = date(2024, 5, 17)  # a Friday
BOOK_1900_BUY_DAY = date(1900, 1, 2)
BOOK_1900_DATE_TO = date(2021, 2, 15)
BOOK_1900_DATE_FROM = BOOK_1900_DATE_TO - timedelta(days=30)


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


# --------------------------------------------------------------------------- #
# Readings
# --------------------------------------------------------------------------- #


async def _analysis(
    session: AsyncSession,
    *,
    user: User,
    asset: Asset,
    broker_ids: list[int] | None,
    date_from: date | None,
    date_to: date,
    selected_lot_ids: list[int] | None = None,
) -> LotsAnalysisResponse:
    """Every analysis of ``asset`` for ``user`` over ``broker_ids``, in EUR."""
    return await get_lots_analysis(
        session=session,
        user_id=user.id,
        asset_id=asset.id,
        broker_ids=broker_ids,
        date_from=date_from,
        date_to=date_to,
        target_currency=EUR,
        selected_lot_ids=selected_lot_ids,
        requested_analyses=ALL_ANALYSES,
    )


def _every_day_is_a_change_day(**arguments) -> list[date]:
    """``lot_change_days`` as today's computation reads it: every day of ``days`` is a change day. If the cure of J5-5
    changes the signature (no ``days`` list any more), this stand-in must follow it: it fails loudly, never silently
    patches nothing."""
    assert "days" in arguments, f"lot_change_days has no `days` argument any more ({sorted(arguments)}): adapt _every_day_is_a_change_day to the new signature"
    return list(arguments["days"])


async def _as_is_and_every_day(session: AsyncSession, monkeypatch: pytest.MonkeyPatch, **request) -> tuple[LotsAnalysisResponse, LotsAnalysisResponse]:
    """A, the analysis as it is; then B, the same with ``lots_analysis_service.lot_change_days`` answering every day —
    today's computation —, the patch undone when B returns. ``raising=False``: before L1a the name does not exist, the
    patch only adds it, and nothing reads it."""
    as_is = await _analysis(session, **request)
    with monkeypatch.context() as patch:
        patch.setattr(lots_analysis_service, "lot_change_days", _every_day_is_a_change_day, raising=False)
        every_day = await _analysis(session, **request)
    return as_is, every_day


def _dump(result: LotsAnalysisResponse) -> dict:
    """The answer as its JSON, but the day it was generated on: the wall clock's date, never compared."""
    payload = result.model_dump(mode="json")
    del payload["calculation_metadata"]["generated_at"]
    return payload


def _first_difference(left: object, right: object, path: str = "$") -> str | None:
    """The first path where two JSON trees differ, with both values; None when they are equal."""
    if isinstance(left, dict) and isinstance(right, dict):
        return _first_key_difference(left, right, path)
    if isinstance(left, list) and isinstance(right, list):
        return _first_item_difference(left, right, path)
    if type(left) is type(right) and left == right:
        return None
    return f"{path}: A={left!r} B={right!r}"


def _first_key_difference(left: dict, right: dict, path: str) -> str | None:
    for key in sorted(left.keys() | right.keys()):
        if key not in left or key not in right:
            return f"{path}.{key}: only in {'A' if key in left else 'B'}"
        found = _first_difference(left[key], right[key], f"{path}.{key}")
        if found is not None:
            return found
    return None


def _first_item_difference(left: list, right: list, path: str) -> str | None:
    for index, (one, other) in enumerate(zip(left, right, strict=False)):
        found = _first_difference(one, other, f"{path}[{index}]{_point_label(one)}")
        if found is not None:
            return found
    if len(left) != len(right):
        return f"{path}: A has {len(left)} items, B has {len(right)}"
    return None


def _point_label(item: object) -> str:
    """A history point named by what identifies it, ``(lot_id=…, broker_id=…, date=…)``; nothing for anything else."""
    if not isinstance(item, dict):
        return ""
    named = [f"{key}={item[key]}" for key in ("lot_id", "broker_id", "date") if key in item]
    return f"({', '.join(named)})" if named else ""


def _point_counts(as_is: LotsAnalysisResponse, every_day: LotsAnalysisResponse) -> dict[str, tuple[int, int]]:
    """Points of each daily section, A and B."""
    return {name: (len(getattr(as_is, name) or []), len(getattr(every_day, name) or [])) for name in DAILY_SECTIONS}


def _assert_not_vacuous(result: LotsAnalysisResponse, *, empty_window: bool) -> None:
    """Precondition: the comparison is never between two empty answers by accident. A window that ends before it starts
    has no point in any daily section; any other window of these books has its market price line."""
    points = {name: len(getattr(result, name) or []) for name in DAILY_SECTIONS}
    if empty_window:
        assert set(points.values()) == {0}, f"precondition: an empty window has no daily point, {points}"
    else:
        assert points["market_price_history"] > 0, f"precondition: the window has its market price line, {points}"


def _calendar(first: date, last: date) -> list[date]:
    """Every calendar day from ``first`` to ``last``."""
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _issues(result: LotsAnalysisResponse) -> list:
    return list(result.data_quality.issues) if result.data_quality else []


def _counting(calls: Counter, name: str, original: Callable) -> Callable:
    """``original``, counting its calls in ``calls[name]``."""

    def counted(*args, **kwargs):
        calls[name] += 1
        return original(*args, **kwargs)

    return counted


# --------------------------------------------------------------------------- #
# Books
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Book:
    """What a scenario wrote: its asset, its readers by label (``owner``, ``coowner``), its brokers by label (``A``,
    ``B``) and its asset's transactions by name."""

    asset: Asset
    users: Mapping[str, User]
    brokers: Mapping[str, Broker]
    rows: Mapping[str, Transaction] = field(default_factory=dict)


async def _add(session: AsyncSession, **rows: Transaction) -> dict[str, Transaction]:
    """The rows, written in the order given (their ids ascend in it), and flushed."""
    session.add_all(rows.values())
    await session.flush()
    return rows


def _weekly(first: date, closes: Sequence[str]) -> dict[date, str]:
    """``closes`` on ``first`` and on the same weekday of each following week."""
    return {first + timedelta(weeks=week): close for week, close in enumerate(closes)}


async def _eur_book(session: AsyncSession, label: str, *broker_labels: str) -> tuple[User, dict[str, Broker], Asset]:
    """An owner, its brokers (``A`` unless named) and an EUR asset, every name the test's own (a uuid4)."""
    owner = await new_user(session, f"l1a_{label}")
    brokers = {name: await new_broker(session, f"L1a {label} {name}", owner) for name in broker_labels or ("A",)}
    return owner, brokers, await new_asset(session, f"L1a {label}")


async def _own_no_rate(session: AsyncSession, currency: str) -> None:
    """``currency`` has no rate and no route to EUR while the test runs. Both tables are global and store a pair
    alphabetically, so both are emptied for it inside the test's transaction — the rollback brings a neighbour's rows
    back. A neighbour's rate would matter however old it is: the FX service backward-fills without limit."""
    base, quote = sorted((currency, EUR))
    await session.execute(delete(FxRate).where(FxRate.base == base, FxRate.quote == quote))
    await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == base, FxConversionRoute.quote == quote))
    await session.flush()


async def _own_rates(session: AsyncSession, quote: str, rates: Mapping[date, Decimal]) -> None:
    """EUR/``quote`` over ``FX_RATE_SPAN`` is this test's own: a row a neighbour committed there is deleted inside the
    test's transaction (the rollback brings it back), then ``rates`` are written — 1 EUR = rate ``quote``, the pair in
    the table's alphabetical order (EUR < HUF < ISK)."""
    await session.execute(delete(FxRate).where(FxRate.base == EUR, FxRate.quote == quote, FxRate.date >= FX_RATE_SPAN[0], FxRate.date <= FX_RATE_SPAN[1]))
    session.add_all([FxRate(date=day, base=EUR, quote=quote, rate=rate, source="TEST") for day, rate in rates.items()])
    await session.flush()


def _daily_huf_rates() -> dict[date, Decimal]:
    """EUR/HUF on every calendar day from 28 Dec 1936 to 31 Dec 1938, a seeded walk around 390, but on ``FX_GAP``."""
    rng = random.Random(1937)
    rates: dict[date, Decimal] = {}
    rate = 390.0
    for day in _calendar(date(1936, 12, 28), date(1938, 12, 31)):
        rate += rng.uniform(-0.8, 0.8)
        if not FX_GAP[0] <= day <= FX_GAP[1]:
            rates[day] = Decimal(f"{rate:.4f}")
    return rates


def _weekly_huf_closes() -> dict[date, Decimal]:
    """The HUF closes of the 104 Mondays from 4 Jan 1937, a seeded walk from 5 000."""
    rng = random.Random(5000)
    closes: dict[date, Decimal] = {}
    close = 5000
    for week in range(104):
        closes[FX_FIRST_DAY + timedelta(weeks=week)] = Decimal(close)
        close += rng.randint(-120, 150)
    return closes


async def seed_fx_daily(session: AsyncSession) -> Book:
    """Book ``fx-daily`` (module docstring): a HUF asset, a rate a day, a five-day rate gap, a trade in ISK."""
    owner = await new_user(session, "l1a_fx")
    brokers = {"A": await new_broker(session, "L1a fx A", owner), "B": await new_broker(session, "L1a fx B", owner)}
    tag = uuid4().hex[:16]
    asset = Asset(display_name=f"L1a fx {tag}", identifier_ticker=f"L1AF{tag[:8].upper()}", currency="HUF", asset_type=AssetType.STOCK)
    session.add(asset)
    await session.flush()
    session.add_all([PriceHistory(asset_id=asset.id, date=day, close=close, currency="HUF", source_plugin_key="TEST") for day, close in _weekly_huf_closes().items()])
    await _own_rates(session, "HUF", _daily_huf_rates())
    await _own_rates(session, "ISK", FX_ISK_RATES)
    a, b = brokers["A"], brokers["B"]
    rows = await _add(
        session,
        buy_1=asset_row(a, asset, TransactionType.BUY, FX_FIRST_DAY, "10", amount="-50000", currency="HUF"),
        buy_2=asset_row(a, asset, TransactionType.BUY, date(1937, 3, 3), "6", amount="-31200", currency="HUF"),
        buy_b=asset_row(b, asset, TransactionType.BUY, date(1937, 5, 5), "5", amount="-26000", currency="HUF"),
        sell_1=asset_row(a, asset, TransactionType.SELL, date(1937, 6, 16), "-4", amount="22000", currency="HUF"),
        buy_isk=asset_row(a, asset, TransactionType.BUY, date(1937, 11, 10), "3", amount="-5865", currency="ISK"),
        dividend=asset_row(a, asset, TransactionType.DIVIDEND, date(1937, 12, 8), "0", amount="1600", currency="HUF"),
        tax=asset_row(a, asset, TransactionType.TAX, date(1937, 12, 8), "0", amount="-240", currency="HUF"),
        fee=asset_row(a, asset, TransactionType.FEE, date(1938, 2, 2), "0", amount="-500", currency="HUF"),
        sell_2=asset_row(a, asset, TransactionType.SELL, date(1938, 2, 2), "-6", amount="33600", currency="HUF"),
        sell_b=asset_row(b, asset, TransactionType.SELL, date(1938, 5, 4), "-5", amount="28500", currency="HUF"),
        sell_3=asset_row(a, asset, TransactionType.SELL, date(1938, 9, 7), "-2", amount="11800", currency="HUF"),
    )
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


async def seed_at_cost(session: AsyncSession) -> Book:
    """Book ``at-cost`` (module docstring): an ADJUSTMENT-in at a cost a month before the first close."""
    owner, brokers, asset = await _eur_book(session, "at_cost")
    a = brokers["A"]
    add_prices(session, asset, _weekly(date(2024, 3, 6), ["110", "112", "109", "111", "111", "114", "116", "115", "117", "117", "119", "118", "120", "121", "119", "122", "123"]))
    rows = await _add(
        session,
        adjustment=asset_row(a, asset, TransactionType.ADJUSTMENT, AT_COST_DAY, "10", currency=None, cost="100"),
        buy=asset_row(a, asset, TransactionType.BUY, date(2024, 3, 21), "5", amount="-560"),
        sell=asset_row(a, asset, TransactionType.SELL, date(2024, 5, 16), "-4", amount="468"),
    )
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


async def seed_representation(session: AsyncSession) -> Book:
    """Book ``representation`` (module docstring): the BUY's mark, ``110``, carried into an equal close on a day without
    a transaction, which reads back ``110.000000`` — the same price in another representation, on a day only a price
    change can name."""
    owner, brokers, asset = await _eur_book(session, "representation")
    a = brokers["A"]
    add_prices(session, asset, {REPRESENTATION_CLOSE_DAY: "110", date(2024, 4, 15): "115", date(2024, 4, 22): "115", date(2024, 5, 6): "116"})
    rows = await _add(
        session,
        buy=asset_row(a, asset, TransactionType.BUY, REPRESENTATION_FIRST_DAY, "15", amount="-1650"),
        dividend=asset_row(a, asset, TransactionType.DIVIDEND, date(2024, 5, 8), "0", amount="15"),
    )
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


async def seed_at_cost_then_no_rate(session: AsyncSession) -> Book:
    """Book ``at-cost-then-no-rate`` (module docstring): the days at cost end on a close nobody can convert."""
    await _own_no_rate(session, "VND")
    owner, brokers, asset = await _eur_book(session, "at_cost_no_rate")
    a = brokers["A"]
    session.add(PriceHistory(asset_id=asset.id, date=date(2024, 2, 14), close=Decimal("2600000"), currency="VND", source_plugin_key="TEST"))
    add_prices(session, asset, _weekly(date(2024, 3, 4), ["104", "106", "105", "108"]))
    rows = await _add(
        session,
        adjustment=asset_row(a, asset, TransactionType.ADJUSTMENT, AT_COST_DAY, "10", currency=None, cost="100"),
        buy=asset_row(a, asset, TransactionType.BUY, date(2024, 3, 13), "4", amount="-424"),
    )
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


async def seed_transfer_in_transit(session: AsyncSession) -> Book:
    """Book ``transfer-in-transit`` (module docstring): A sends 10 to B, six days in transit; V owns B only."""
    owner, brokers, asset = await _eur_book(session, "transfer", "A", "B")
    a, b = brokers["A"], brokers["B"]
    coowner = await new_user(session, "l1a_transfer_coowner")
    await grant_owner(session, b, coowner)
    add_prices(session, asset, _weekly(Q1_FIRST_MONDAY, ["100", "103", "101", "104", "107", "110", "108", "112", "115", "113", "117", "116"]))
    rows = await _add(
        session,
        buy=asset_row(a, asset, TransactionType.BUY, Q1_FIRST_MONDAY, "10", amount="-1000"),
        out_leg=asset_row(a, asset, TransactionType.TRANSFER, date(2024, 2, 7), "-10"),
        in_leg=asset_row(b, asset, TransactionType.TRANSFER, date(2024, 2, 13), "10", cost="100"),
        sell=asset_row(b, asset, TransactionType.SELL, date(2024, 3, 6), "-4", amount="460"),
        dividend=asset_row(b, asset, TransactionType.DIVIDEND, date(2024, 3, 20), "0", amount="12"),
    )
    await link(session, rows["out_leg"], rows["in_leg"])
    return Book(asset=asset, users={"owner": owner, "coowner": coowner}, brokers=brokers, rows=rows)


async def seed_l1_read_by_two(session: AsyncSession) -> Book:
    """Ledger L1 (``_scope_boundary_books.py``), and V, an owner of B only."""
    ledger = await seed_l1(session)
    coowner = await new_user(session, "l1a_l1_coowner")
    await grant_owner(session, ledger.broker_b, coowner)
    rows = {"buy": ledger.buy, "out_leg": ledger.out_leg, "in_leg": ledger.in_leg, "sell": ledger.sell}
    return Book(asset=ledger.asset, users={"owner": ledger.owner, "coowner": coowner}, brokers={"A": ledger.broker_a, "B": ledger.broker_b}, rows=rows)


async def seed_l2_in_transit(session: AsyncSession) -> Book:
    """Ledger L2 (``_scope_boundary_books.py``): read on 14 Jan 2025, its 10 units are in transit."""
    ledger = await seed_l2(session)
    rows = {"buy": ledger.buy, "out_leg": ledger.out_leg, "in_leg": ledger.in_leg}
    return Book(asset=ledger.asset, users={"owner": ledger.owner}, brokers={"A": ledger.broker_a, "B": ledger.broker_b}, rows=rows)


async def seed_split(session: AsyncSession) -> Book:
    """Book ``split`` (module docstring): a 2:1 SPLIT event and its ADJUSTMENT on a day without a close."""
    owner, brokers, asset = await _eur_book(session, "split")
    a = brokers["A"]
    add_prices(session, asset, _weekly(Q1_FIRST_MONDAY, ["100", "101", "99", "102", "51", "52", "50", "53", "54", "55", "54", "56"]))
    split = AssetEvent(asset_id=asset.id, date=date(2024, 2, 1), type=AssetEventType.SPLIT, value=Decimal("2"), currency=EUR)
    session.add(split)
    await session.flush()
    split_in = asset_row(a, asset, TransactionType.ADJUSTMENT, date(2024, 2, 1), "10")
    split_in.asset_event_id = split.id
    rows = await _add(
        session,
        buy=asset_row(a, asset, TransactionType.BUY, date(2024, 1, 10), "10", amount="-1000"),
        split_in=split_in,
        sell=asset_row(a, asset, TransactionType.SELL, date(2024, 3, 7), "-6", amount="330"),
        dividend=asset_row(a, asset, TransactionType.DIVIDEND, date(2024, 3, 14), "0", amount="8"),
    )
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


async def seed_short(session: AsyncSession) -> Book:
    """Book ``short`` (module docstring): a short sold, bought back, and sold again on a broker that allows it."""
    owner, brokers, asset = await _eur_book(session, "short")
    a = brokers["A"]
    a.allow_asset_shorting = True
    add_prices(session, asset, _weekly(Q1_FIRST_MONDAY, ["120", "118", "112", "109", "111", "105", "103", "106", "104", "101", "99", "100"]))
    rows = await _add(
        session,
        short=asset_row(a, asset, TransactionType.SELL, date(2024, 1, 10), "-5", amount="600"),
        bought_back=asset_row(a, asset, TransactionType.BUY, date(2024, 2, 14), "5", amount="-525"),
        short_again=asset_row(a, asset, TransactionType.SELL, date(2024, 2, 28), "-3", amount="318"),
    )
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


async def seed_unknown_pools(session: AsyncSession) -> Book:
    """Book ``unknown-pools`` (module docstring): an income, a purchase and a sale in VND, which has no rate."""
    await _own_no_rate(session, "VND")
    owner, brokers, asset = await _eur_book(session, "unknown_pools")
    a = brokers["A"]
    add_prices(session, asset, _weekly(Q1_FIRST_MONDAY, ["100", "101", "103", "102", "104", "106", "105", "107", "108", "110", "109", "111"]))
    rows = await _add(
        session,
        buy=asset_row(a, asset, TransactionType.BUY, Q1_FIRST_MONDAY, "10", amount="-1000"),
        vnd_dividend=asset_row(a, asset, TransactionType.DIVIDEND, date(2024, 1, 24), "0", amount="80", currency="VND"),
        vnd_buy=asset_row(a, asset, TransactionType.BUY, date(2024, 2, 7), "5", amount="-2600000", currency="VND"),
        vnd_sell=asset_row(a, asset, TransactionType.SELL, date(2024, 3, 6), "-2", amount="230000", currency="VND"),
        eur_dividend=asset_row(a, asset, TransactionType.DIVIDEND, date(2024, 3, 13), "0", amount="20"),
    )
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


async def seed_failed(session: AsyncSession) -> Book:
    """Book ``failed`` (module docstring): A sells more than it holds; B trades normally."""
    owner, brokers, asset = await _eur_book(session, "failed", "A", "B")
    a, b = brokers["A"], brokers["B"]
    add_prices(session, asset, _weekly(Q1_FIRST_MONDAY, ["100", "102", "104", "103", "105", "107", "106", "108", "108", "108", "110", "111"]))
    rows = await _add(
        session,
        buy=asset_row(a, asset, TransactionType.BUY, Q1_FIRST_MONDAY, "5", amount="-500"),
        dividend=asset_row(a, asset, TransactionType.DIVIDEND, date(2024, 1, 10), "0", amount="10"),
        oversell=asset_row(a, asset, TransactionType.SELL, date(2024, 1, 17), "-8", amount="880"),
        buy_b=asset_row(b, asset, TransactionType.BUY, date(2024, 1, 24), "4", amount="-412"),
        sell_b=asset_row(b, asset, TransactionType.SELL, date(2024, 3, 11), "-1", amount="108"),
    )
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


async def seed_selected_lots(session: AsyncSession) -> Book:
    """Book ``selected-lots`` (module docstring): three lots, the second bought on a day whose close repeats."""
    owner, brokers, asset = await _eur_book(session, "selected")
    a = brokers["A"]
    add_prices(session, asset, _weekly(Q1_FIRST_MONDAY, ["100", "100", "102", "102", "104", "105", "107", "107", "108", "108", "110", "109"]))
    rows = await _add(
        session,
        buy_1=asset_row(a, asset, TransactionType.BUY, Q1_FIRST_MONDAY, "10", amount="-1000"),
        buy_2=asset_row(a, asset, TransactionType.BUY, date(2024, 1, 15), "4", amount="-400"),
        buy_3=asset_row(a, asset, TransactionType.BUY, date(2024, 1, 22), "6", amount="-612"),
        sell=asset_row(a, asset, TransactionType.SELL, date(2024, 2, 14), "-12", amount="1272"),
        dividend=asset_row(a, asset, TransactionType.DIVIDEND, date(2024, 2, 21), "0", amount="20"),
    )
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


async def seed_1900(session: AsyncSession) -> Book:
    """Book ``1900`` (module docstring): a lot bought in 1900, priced in 2020, read in 2021."""
    owner, brokers, asset = await _eur_book(session, "1900")
    a = brokers["A"]
    add_prices(session, asset, {date(2020, 3, 2): "101", date(2020, 6, 1): "103", date(2020, 9, 1): "99", date(2020, 12, 1): "105"})
    rows = await _add(
        session,
        buy=asset_row(a, asset, TransactionType.BUY, BOOK_1900_BUY_DAY, "10", amount="-1000"),
        sell=asset_row(a, asset, TransactionType.SELL, date(2020, 10, 15), "-4", amount="420"),
    )
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


# --------------------------------------------------------------------------- #
# What each book proves it is (read on its whole window, in its first scope)
# --------------------------------------------------------------------------- #

BookCheck = Callable[[Book, LotsAnalysisResponse], None]


def _market_price_days(result: LotsAnalysisResponse) -> list[Mapping]:
    """The asset's market price line as one row per day, read in whichever form the answer has it (days before J5-5,
    steps after): the books prove what they are on days, not on rows."""
    return as_daily_rows(result.model_dump(mode="json")["market_price_history"] or [], None)


def _check_every_day_marked(_book: Book, result: LotsAnalysisResponse) -> None:
    """The HUF and ISK rates are in place: the market price line has a point on every day from the first transaction to
    ``date_to``, the five days of ``FX_GAP`` included (5 Dec 1937's rate carried over them)."""
    marked = [date.fromisoformat(row["date"]) for row in _market_price_days(result)]
    assert marked == _calendar(FX_FIRST_DAY, FX_DATE_TO), f"precondition: {len(marked)} marked days, from {marked[:1]} to {marked[-1:]}"


def _check_at_cost(first_day: date, last_day_at_cost: date) -> BookCheck:
    """The lots are valued at cost from ``first_day`` to ``last_day_at_cost`` (J-17's warning names that range)."""

    def check(_book: Book, result: LotsAnalysisResponse) -> None:
        ranges = [(issue.message_params.get("date_from"), issue.message_params.get("date_to")) for issue in _issues(result) if str(issue.code) == "CURRENT_PRICE_ASSUMED_AT_COST"]
        assert (first_day.isoformat(), last_day_at_cost.isoformat()) in ranges, f"precondition: the days at cost {ranges}"

    return check


def _check_representations(_book: Book, result: LotsAnalysisResponse) -> None:
    """The line from the BUY to the first close: the trade's mark, 1 650 / 15 = ``110``, estimated, on 3 Apr and carried
    to 7 Apr; on 8 Apr the close of 110, read back from the DB padded to six decimals, ``110.000000``, not estimated."""
    line = {date.fromisoformat(row["date"]): (row["market_price"], row["estimated"]) for row in _market_price_days(result)}
    observed = {day: line.get(day) for day in _calendar(REPRESENTATION_FIRST_DAY, REPRESENTATION_CLOSE_DAY)}
    expected = dict.fromkeys(_calendar(REPRESENTATION_FIRST_DAY, REPRESENTATION_CLOSE_DAY - timedelta(days=1)), ("110", True))
    expected[REPRESENTATION_CLOSE_DAY] = ("110.000000", False)
    assert observed == expected, f"precondition: the line from the trade to the close {observed}"


def _check_event_kinds(*, present: Sequence[str], absent: Sequence[str] = ()) -> BookCheck:
    """The event history has every kind of ``present`` and none of ``absent``."""

    def check(_book: Book, result: LotsAnalysisResponse) -> None:
        kinds = {str(event.kind) for event in result.lot_events or []}
        assert set(present) <= kinds and not kinds & set(absent), f"precondition: the event kinds {sorted(kinds)}"

    return check


def _check_short_lot(_book: Book, result: LotsAnalysisResponse) -> None:
    """A lot is SHORT."""
    directions = sorted(str(lot.direction) for lot in result.lots or [])
    assert "SHORT" in directions, f"precondition: the lots' directions {directions}"


def _check_missing_pair(pair: str) -> BookCheck:
    """The data quality reports ``pair`` missing."""

    def check(_book: Book, result: LotsAnalysisResponse) -> None:
        pairs = sorted(item.pair for item in result.data_quality.missing_fx_pairs) if result.data_quality else []
        assert pair in pairs, f"precondition: the missing pairs {pairs}"

    return check


def _check_status(status: str) -> BookCheck:
    """The analysis is ``status``."""

    def check(_book: Book, result: LotsAnalysisResponse) -> None:
        assert result.calculation_status == status, f"precondition: {result.calculation_status}, issues {sorted({str(issue.code) for issue in _issues(result)})}"

    return check


def _check_selected_lots(*names: str) -> BookCheck:
    """The value history holds the lots of the rows ``names`` and no other."""

    def check(book: Book, result: LotsAnalysisResponse) -> None:
        valued = {point.lot_id for point in result.value_history or []}
        assert valued == {book.rows[name].id for name in names}, f"precondition: the lots valued {sorted(valued)}"

    return check


# --------------------------------------------------------------------------- #
# Scenarios, windows, scopes
# --------------------------------------------------------------------------- #


def _windows(first_day: date, date_to: date) -> dict[str, tuple[date | None, date]]:
    """``(date_from, date_to)`` of each window a book is read over (module docstring, THE WINDOWS)."""
    span = (date_to - first_day).days
    windows: dict[str, tuple[date | None, date]] = {
        "whole": (None, date_to),
        "before-first-transaction": (first_day - timedelta(days=7), date_to),
        "second-half": (first_day + timedelta(days=span // 2), date_to),
        "middle": (first_day + timedelta(days=span // 3), first_day + timedelta(days=2 * span // 3)),
        "empty": (date_to + timedelta(days=1), date_to),
    }
    if span > 30:
        windows["last-month"] = (date_to - timedelta(days=30), date_to)
    if span > 365:
        windows["last-year"] = (date_to - timedelta(days=365), date_to)
    return windows


@dataclass(frozen=True)
class Scenario:
    """A book (``seed``), the day of its first transaction and its reading day, the scopes it is read in (``_reader``),
    the rows whose lots are selected (none: every lot), what it proves on its whole window in its first scope
    (``check``), and its windows (``_windows`` unless given)."""

    seed: Callable[[AsyncSession], Awaitable[Book]]
    first_day: date
    date_to: date
    scopes: tuple[str, ...]
    selected: tuple[str, ...] = ()
    check: BookCheck | None = None
    windows: Mapping[str, tuple[date | None, date]] | None = None

    def readings(self) -> Mapping[str, tuple[date | None, date]]:
        return self.windows if self.windows is not None else _windows(self.first_day, self.date_to)


SCENARIOS: dict[str, Scenario] = {
    "fx-daily": Scenario(seed_fx_daily, FX_FIRST_DAY, FX_DATE_TO, ("owner-all", "owner-A", "owner-B"), check=_check_every_day_marked),
    "at-cost": Scenario(seed_at_cost, AT_COST_DAY, date(2024, 6, 28), ("owner-all", "owner-A"), check=_check_at_cost(AT_COST_DAY, date(2024, 3, 5))),
    "representation": Scenario(seed_representation, REPRESENTATION_FIRST_DAY, REPRESENTATION_DATE_TO, ("owner-all", "owner-A"), check=_check_representations),
    "at-cost-then-no-rate": Scenario(seed_at_cost_then_no_rate, AT_COST_DAY, Q1_DATE_TO, ("owner-all", "owner-A"), check=_check_at_cost(AT_COST_DAY, date(2024, 2, 13))),
    "transfer-in-transit": Scenario(seed_transfer_in_transit, Q1_FIRST_MONDAY, Q1_DATE_TO, ("owner-all", "owner-A", "owner-B", "coowner-all"), check=_check_event_kinds(present=("TRANSFER_DEPART", "TRANSFER_ARRIVE"))),
    "l1-boundary": Scenario(seed_l1_read_by_two, L1_BUY_DAY, L1_DATE_TO, ("owner-all", "owner-A", "owner-B", "coowner-all"), check=_check_event_kinds(present=("TRANSFER_DEPART", "TRANSFER_ARRIVE"))),
    "l2-in-transit-at-date-to": Scenario(seed_l2_in_transit, L2_BUY_DAY, L2_DATE_TO, ("owner-all", "owner-A"), check=_check_event_kinds(present=("TRANSFER_DEPART",), absent=("TRANSFER_ARRIVE",))),
    "split": Scenario(seed_split, date(2024, 1, 10), Q1_DATE_TO, ("owner-all", "owner-A"), check=_check_event_kinds(present=("SPLIT",))),
    "short": Scenario(seed_short, date(2024, 1, 10), Q1_DATE_TO, ("owner-all", "owner-A"), check=_check_short_lot),
    "unknown-pools": Scenario(seed_unknown_pools, Q1_FIRST_MONDAY, Q1_DATE_TO, ("owner-all", "owner-A"), check=_check_missing_pair("VND/EUR")),
    "failed": Scenario(seed_failed, Q1_FIRST_MONDAY, Q1_DATE_TO, ("owner-all", "owner-A", "owner-B"), check=_check_status("FAILED")),
    "selected-lots": Scenario(seed_selected_lots, Q1_FIRST_MONDAY, Q1_DATE_TO, ("owner-all", "owner-A"), selected=("buy_2", "buy_3"), check=_check_selected_lots("buy_2", "buy_3")),
    "1900": Scenario(seed_1900, BOOK_1900_BUY_DAY, BOOK_1900_DATE_TO, ("owner-all",), windows={"last-30-days": (BOOK_1900_DATE_FROM, BOOK_1900_DATE_TO)}),
}

PARITY_CASES = [pytest.param(name, window, scope, id=f"{name}/{window}/{scope}") for name, scenario in SCENARIOS.items() for window in scenario.readings() for scope in scenario.scopes]


def _reader(book: Book, scope: str) -> tuple[User, list[int] | None]:
    """``reader-brokers``: the reader by label, and the broker it asks for by label (``all``: broker_ids None)."""
    reader, brokers = scope.split("-", 1)
    return book.users[reader], None if brokers == "all" else [book.brokers[brokers].id]


# --------------------------------------------------------------------------- #
# The reds
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_red_the_1900_book_is_valued_on_its_change_days_alone(session, monkeypatch):
    """GUARD (red until L1a, green since, to stay green after J5-5). The 1900 book read over its last 30 days, every analysis: ``_lot_snapshot_on_date`` and
    ``_open_value_on_date`` (``financial_math/lots/histories.py``, counted on the module whose globals call them) are
    called at most 400 times together. The lot changes on six days — the BUY, four closes, the SELL —: with the first
    day, the last and each change's next day, 13 change days by the contract, five calls each (65); the budget leaves
    room for more event dates.

    Precondition, green today and after: the lot of the BUY has value rows, and the builders reach both counted steps.
    (That these rows are a few STEPS covering the 31 days is ``test_red_the_1900_lot_is_a_few_steps``.)

    Today: about 221 000 calls — 44 240 days from 2 Jan 1900, five calls a day.
    """
    book = await seed_1900(session)
    calls: Counter[str] = Counter()
    for name in COUNTED_STEPS:
        monkeypatch.setattr(histories, name, _counting(calls, name, getattr(histories, name)))

    result = await _analysis(session, user=book.users["owner"], asset=book.asset, broker_ids=None, date_from=BOOK_1900_DATE_FROM, date_to=BOOK_1900_DATE_TO)

    lot_rows = [point for point in result.value_history or [] if point.lot_id == book.rows["buy"].id]
    assert lot_rows, "precondition: the lot of the BUY has value rows"
    assert all(calls[name] > 0 for name in COUNTED_STEPS), f"precondition: the builders value the lot through the counted steps, {dict(calls)}"
    assert sum(calls.values()) <= CALL_BUDGET, f"{sum(calls.values())} calls of {' + '.join(COUNTED_STEPS)} {dict(calls)} to answer a {BOOK_1900_DATE_TO - BOOK_1900_DATE_FROM} window; the budget is {CALL_BUDGET}"


@pytest.mark.asyncio
async def test_red_the_1900_lot_is_a_few_steps(session):
    """RED until J5-5 (steps). The 1900 book read over its last 30 days, every analysis: nothing changes in the window
    (the closes and the SELL are in 2020), so the lot of the BUY has ONE value step — rows are maximal — and its
    expansion is exactly the window's 31 calendar days, ``range`` being the window.

    Today: the rows carry no ``through`` (one row per day) — «row has no through».
    """
    book = await seed_1900(session)

    result = await _analysis(session, user=book.users["owner"], asset=book.asset, broker_ids=None, date_from=BOOK_1900_DATE_FROM, date_to=BOOK_1900_DATE_TO)

    payload = result.model_dump(mode="json")
    assert payload.get("range") == {"start": BOOK_1900_DATE_FROM.isoformat(), "end": BOOK_1900_DATE_TO.isoformat()}, f"range: {payload.get('range')!r}"
    lot_rows = [row for row in payload["value_history"] if row["lot_id"] == book.rows["buy"].id]
    days = [row["date"] for row in expand_steps(lot_rows, "lot_id")]
    assert days == [day.isoformat() for day in _calendar(BOOK_1900_DATE_FROM, BOOK_1900_DATE_TO)], f"the steps of the lot expand to {len(days)} days"
    assert len(lot_rows) == 1, f"nothing changes in the window: one maximal step, got {len(lot_rows)} rows"


@pytest.mark.asyncio
async def test_red_the_service_asks_for_the_change_days_once(session, monkeypatch):
    """RED until L1a. The 1900 book read over its last 30 days, every analysis, over every broker (no performance
    re-run): ``lots_analysis_service.lot_change_days`` is called exactly once — one set of change days for every
    builder. It is wrapped where the service reads it (``raising=False``), the wrapper answering what the original
    answers.

    Today: the name does not exist in the service's namespace and nothing calls it — «lot_change_days was not called».
    """
    book = await seed_1900(session)
    asked: list[dict] = []
    original = getattr(lots_analysis_service, "lot_change_days", None)

    def recording(*args, **kwargs):
        asked.append(kwargs)
        return list(kwargs["days"]) if original is None else original(*args, **kwargs)

    monkeypatch.setattr(lots_analysis_service, "lot_change_days", recording, raising=False)

    await _analysis(session, user=book.users["owner"], asset=book.asset, broker_ids=None, date_from=BOOK_1900_DATE_FROM, date_to=BOOK_1900_DATE_TO)

    assert len(asked) == 1, "lot_change_days was not called" if not asked else f"lot_change_days was called {len(asked)} times"


# --------------------------------------------------------------------------- #
# The parity battery
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
@pytest.mark.parametrize(("scenario_name", "window", "scope"), PARITY_CASES)
async def test_parity_the_change_days_answer_what_every_day_answers(session, monkeypatch, scenario_name, window, scope):
    """PARITY (green today and after L1a). A book (``SCENARIOS``) read over a window (``_windows``) in a scope
    (``_reader``), every analysis: the answer computed on its change days (A, as it is) dumps to the same JSON as the
    answer computed on every day (B, ``lot_change_days`` answering every day: today's computation), the generation day
    aside. Not between two empty answers (``_assert_not_vacuous``), and on its whole window in its first scope the book
    proves what it is (``Scenario.check``).

    Today: green — ``lot_change_days`` does not exist, the patch changes nothing and A is B.
    """
    scenario = SCENARIOS[scenario_name]
    book = await scenario.seed(session)
    date_from, date_to = scenario.readings()[window]
    user, broker_ids = _reader(book, scope)
    selected = [book.rows[name].id for name in scenario.selected] or None

    as_is, every_day = await _as_is_and_every_day(session, monkeypatch, user=user, asset=book.asset, broker_ids=broker_ids, date_from=date_from, date_to=date_to, selected_lot_ids=selected)

    _assert_not_vacuous(as_is, empty_window=date_from is not None and date_from > date_to)
    if scenario.check is not None and window == "whole" and scope == scenario.scopes[0]:
        scenario.check(book, as_is)
    difference = _first_difference(_dump(as_is), _dump(every_day))
    assert difference is None, f"{scenario_name} / {window} / {scope}: on its change days the answer differs from every day's at {difference} — points A/B {_point_counts(as_is, every_day)}"


# --------------------------------------------------------------------------- #
# J5-5 — the seven histories as STEPS (contract MF-P4b §1.1, §1.3, §8): the shape reds
# --------------------------------------------------------------------------- #
#
# A row of a history is no longer a day but a STEP: ``date`` (the first day it holds) and ``through`` (the last day,
# inclusive); the response carries ``range = {start, end}``, ``start = max(display_from, computed_from)``, ``end =
# date_to``. The rows of one key (``lot_id``; ``broker_id`` for the broker WAC; none for the others) are in order, do not
# overlap and lie inside ``range``; a gap is only where today's daily answer has no row. Steps are MAXIMAL: two rows of
# one key that touch (the second starts the day after the first ends) never carry identical values — compared as JSON
# text, so ``1.10`` and ``1.1`` differ — and expanding every row from ``date`` to ``through`` gives today's daily answer,
# field for field.
#
# These tests read the answer as ``model_dump(mode="json")`` dicts and name no new class (``StepSpan``, ``DateSpan``
# come from another workstream): until the schema carries ``range`` and ``through`` they fail on an assertion.
# An empty window (``date_from`` after ``date_to``) has no step in any section; its ``range`` would start after it ends,
# which the contract does not say, so it is not asserted.


def assert_step_shape(payload: Mapping, *, expected_range: Mapping[str, str], label: str) -> None:
    """``payload`` (a dumped ``LotsAnalysisResponse``) has its ``range`` and, in each of the seven sections, rows that are
    steps: ``through`` >= ``date``, ordered, not overlapping, inside ``range``, maximal where they touch."""
    assert payload.get("range") == dict(expected_range), f"{label}: range is {payload.get('range')!r}, expected {dict(expected_range)}"
    range_start, range_end = date.fromisoformat(expected_range["start"]), date.fromisoformat(expected_range["end"])
    for section, key_name in STEP_KEYS.items():
        for key, group in rows_by_key(payload.get(section) or [], key_name).items():
            where = f"{label}: {section}[{key_name}={key}]"
            previous: Mapping | None = None
            for row in group:
                assert "through" in row, f"{where}: row has no `through` (the series is still one row per day): {dict(row)}"
                first, last = date.fromisoformat(row["date"]), date.fromisoformat(row["through"])
                assert first <= last, f"{where}: through {last} before date {first}"
                assert range_start <= first and last <= range_end, f"{where}: step {first}..{last} outside the range {range_start}..{range_end}"
                if previous is not None:
                    previous_last = date.fromisoformat(previous["through"])
                    assert first > previous_last, f"{where}: step {first}..{last} starts inside or before the previous one, which ends {previous_last}"
                    if first == previous_last + timedelta(days=1):
                        assert step_values(row) != step_values(previous), f"{where}: steps ending {previous_last} and starting {first} hold identical values: one step, not two"
                previous = row


def _expected_range(date_from: date | None, result: LotsAnalysisResponse, date_to: date) -> dict[str, str]:
    """``{start, end}`` the contract gives: ``start = max(display_from, computed_from)``, the first day with data in the
    window; ``end = date_to``."""
    computed_from = result.calculation_metadata.computed_date_from
    assert computed_from is not None, "precondition: the book has a first computed day"
    return {"start": (computed_from if date_from is None else max(date_from, computed_from)).isoformat(), "end": date_to.isoformat()}


@pytest.mark.asyncio
@pytest.mark.parametrize(("scenario_name", "window", "scope"), PARITY_CASES)
async def test_red_every_history_is_a_list_of_steps(session, monkeypatch, scenario_name, window, scope):
    """RED until J5-5. A book read over a window in a scope, every analysis: the answer has its ``range`` and the seven
    histories are steps (``assert_step_shape``); and the steps computed on the change days (A) expand to the same daily
    rows as the steps computed on every day (B, ``lot_change_days`` answering every day): the canonical form's proof.
    An empty window has no row in any section.

    Today: ``range`` is missing from the answer — «range is None».
    """
    scenario = SCENARIOS[scenario_name]
    book = await scenario.seed(session)
    date_from, date_to = scenario.readings()[window]
    user, broker_ids = _reader(book, scope)
    selected = [book.rows[name].id for name in scenario.selected] or None
    empty_window = date_from is not None and date_from > date_to

    as_is, every_day = await _as_is_and_every_day(session, monkeypatch, user=user, asset=book.asset, broker_ids=broker_ids, date_from=date_from, date_to=date_to, selected_lot_ids=selected)

    _assert_not_vacuous(as_is, empty_window=empty_window)
    label = f"{scenario_name} / {window} / {scope}"
    payload_a, payload_b = as_is.model_dump(mode="json"), every_day.model_dump(mode="json")
    if empty_window:
        return
    assert_step_shape(payload_a, expected_range=_expected_range(date_from, as_is, date_to), label=label)
    for section, key_name in STEP_KEYS.items():
        expanded_a = expand_steps(payload_a.get(section) or [], key_name)
        expanded_b = expand_steps(payload_b.get(section) or [], key_name)
        assert expanded_a == expanded_b, f"{label}: {section}: the steps on the change days expand to {len(expanded_a)} daily rows, on every day to {len(expanded_b)}: first difference {_first_difference(expanded_a, expanded_b, section)}"
        canonical = compress_days(expanded_a, key_name)
        assert order_by_key(payload_a.get(section) or [], key_name) == canonical, f"{label}: {section}: the steps are not the maximal ones of their own expansion ({len(payload_a.get(section) or [])} rows, {len(canonical)} maximal steps)"


# The checker itself, so that a red is red for the answer and never for the checker: pure cases, then the real books.

_RANGE = {"start": "2024-01-01", "end": "2024-01-10"}


def _price_step(first: str, last: str, price: str = "1.10", **extra: object) -> dict:
    return {"date": first, "through": last, "market_price": price, "currency": "EUR", "estimated": False, **extra}


def test_guard_the_step_checker_accepts_canonical_steps():
    """GUARD. Steps with a gap between them, and touching steps whose prices ``1.10`` and ``1.1`` differ as text, are valid;
    ``expand_steps`` repeats each on its days and ``compress_days`` gives the steps back."""
    steps = [_price_step("2024-01-01", "2024-01-03"), _price_step("2024-01-04", "2024-01-05", "1.1"), _price_step("2024-01-08", "2024-01-10", "1.1")]
    assert_step_shape({"range": _RANGE, "market_price_history": steps}, expected_range=_RANGE, label="canonical")
    days = expand_steps(steps, None)
    assert [row["date"] for row in days] == ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08", "2024-01-09", "2024-01-10"]
    assert all("through" not in row for row in days)
    assert compress_days(days, None) == steps


@pytest.mark.parametrize(
    ("steps", "range_", "expected"),
    [
        pytest.param([_price_step("2024-01-01", "2024-01-03"), _price_step("2024-01-04", "2024-01-05")], _RANGE, "identical values", id="touching-and-equal"),
        pytest.param([_price_step("2024-01-01", "2024-01-04"), _price_step("2024-01-04", "2024-01-05", "1.2")], _RANGE, "starts inside or before", id="overlapping"),
        pytest.param([_price_step("2024-01-04", "2024-01-05"), _price_step("2024-01-01", "2024-01-02", "1.2")], _RANGE, "starts inside or before", id="out-of-order"),
        pytest.param([_price_step("2023-12-31", "2024-01-03")], _RANGE, "outside the range", id="before-the-range"),
        pytest.param([_price_step("2024-01-08", "2024-01-11")], _RANGE, "outside the range", id="after-the-range"),
        pytest.param([_price_step("2024-01-05", "2024-01-04")], _RANGE, "before date", id="through-before-date"),
        pytest.param([{"date": "2024-01-01", "market_price": "1.10"}], _RANGE, "no `through`", id="a-day-not-a-step"),
        pytest.param([_price_step("2024-01-01", "2024-01-03")], {"start": "2024-01-02", "end": "2024-01-10"}, "range is", id="wrong-range"),
    ],
)
def test_guard_the_step_checker_rejects_what_is_not_a_step_list(steps, range_, expected):
    """GUARD. Each defect of the contract is caught, and named."""
    with pytest.raises(AssertionError, match=expected):
        assert_step_shape({"range": range_, "market_price_history": steps}, expected_range=_RANGE, label="mutant")


def test_guard_a_key_is_checked_on_its_own_rows():
    """GUARD. Two lots whose steps touch in time but not in key are not compared; one lot's two equal touching steps are."""
    lot_1, lot_2 = {"lot_id": 1, "market_price": "1", "currency": "EUR", "estimated": False}, {"lot_id": 2, "market_price": "1", "currency": "EUR", "estimated": False}
    fine = [{**lot_1, "date": "2024-01-01", "through": "2024-01-05"}, {**lot_2, "date": "2024-01-06", "through": "2024-01-07"}]
    assert_step_shape({"range": _RANGE, "price_history": fine}, expected_range=_RANGE, label="two lots")
    split = [{**lot_1, "date": "2024-01-01", "through": "2024-01-05"}, {**lot_1, "date": "2024-01-06", "through": "2024-01-07"}]
    with pytest.raises(AssertionError, match="identical values"):
        assert_step_shape({"range": _RANGE, "price_history": split}, expected_range=_RANGE, label="one lot")


STEP_CHECK_CASES = [case for case in PARITY_CASES if case.values[1] != "empty"]


@pytest.mark.asyncio
@pytest.mark.parametrize(("scenario_name", "window", "scope"), STEP_CHECK_CASES)
async def test_guard_the_step_checker_accepts_the_real_books_as_steps(session, scenario_name, window, scope):
    """GUARD (green today, and after J5-5). The answer of a book, its seven histories read in whichever form they come
    (daily rows today, steps after) and compressed to maximal steps, is a valid step list inside the expected ``range``,
    and expands back to the same daily rows: the checker and the expected range hold on the real books, so a red of
    ``test_red_every_history_is_a_list_of_steps`` is red for the answer.
    """
    scenario = SCENARIOS[scenario_name]
    book = await scenario.seed(session)
    date_from, date_to = scenario.readings()[window]
    user, broker_ids = _reader(book, scope)
    selected = [book.rows[name].id for name in scenario.selected] or None

    result = await _analysis(session, user=user, asset=book.asset, broker_ids=broker_ids, date_from=date_from, date_to=date_to, selected_lot_ids=selected)

    payload = result.model_dump(mode="json")
    for section, key_name in STEP_KEYS.items():
        daily = as_daily_rows(payload.get(section) or [], key_name)
        steps = compress_days(daily, key_name)
        payload[section] = steps
        assert expand_steps(steps, key_name) == list(daily), f"{scenario_name} / {window} / {scope}: {section} does not expand back to its daily rows"
    expected_range = _expected_range(date_from, result, date_to)
    assert_step_shape(payload, expected_range=expected_range, label=f"{scenario_name} / {window} / {scope}")


# --------------------------------------------------------------------------- #
# A boundary the candidate days could miss: a price that changes its representation on a day without a transaction
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_red_a_price_representation_change_is_a_step_boundary(session):
    """RED until J5-5. Book ``representation`` over its whole life: the lot's mark reads ``110`` (estimated) until Sun 7
    Apr 2024 and ``110.000000`` (a close, not estimated) from Mon 8 Apr, a day with no transaction and a price of the
    same value. The price lines of the lot and of the asset have a step ending 7 Apr and another starting 8 Apr, and the
    lot's value line a step starting 8 Apr: the day only the price's representation can name must stay a boundary after
    the cure, however it chooses its candidate days.

    Today: the rows carry no ``through`` — «row has no through».
    """
    book = await seed_representation(session)
    lot_id = book.rows["buy"].id

    result = await _analysis(session, user=book.users["owner"], asset=book.asset, broker_ids=None, date_from=None, date_to=REPRESENTATION_DATE_TO)

    payload = result.model_dump(mode="json")
    last_estimated, first_close = (REPRESENTATION_CLOSE_DAY - timedelta(days=1)).isoformat(), REPRESENTATION_CLOSE_DAY.isoformat()
    for section, key_name in (("price_history", "lot_id"), ("market_price_history", None), ("value_history", "lot_id")):
        rows = [row for row in payload[section] if key_name is None or row[key_name] == lot_id]
        assert all("through" in row for row in rows), f"{section}: row has no `through` (the series is still one row per day)"
        ending = [row for row in rows if row["through"] == last_estimated]
        starting = [row for row in rows if row["date"] == first_close]
        assert len(ending) == 1 and len(starting) == 1, f"{section}: {len(ending)} steps end {last_estimated}, {len(starting)} start {first_close}"
        assert step_values(ending[0]) != step_values(starting[0]), f"{section}: the steps around {first_close} hold identical values"
        if section != "value_history":
            assert (ending[0]["market_price"], ending[0]["estimated"]) == ("110", True), f"{section}: {ending[0]}"
            assert (starting[0]["market_price"], starting[0]["estimated"]) == ("110.000000", False), f"{section}: {starting[0]}"


# --------------------------------------------------------------------------- #
# The typo: a first transaction in year 1 costs steps, not days
# --------------------------------------------------------------------------- #

YEAR_ONE_BUY_DAY = date(1, 1, 3)
YEAR_ONE_DATE_TO = date(2021, 2, 15)
RESOLVE_BUDGET = 2_000  # the price series is asked at most this often in the whole analysis (today once per calendar day: 737 854)
RESOLVE_ABORT = 5_000  # the spy stops the analysis here, so that today the red fails fast instead of walking 740 000 days
STEP_ROWS_PER_SECTION = 40  # bounded by the true changes of the book (a BUY, four closes, a SELL), not by its 737 834 days
PEAK_BYTES = 150 * 1024 * 1024
WALL_SECONDS = 20


async def seed_year_one(session: AsyncSession) -> Book:
    """Book ``year-one``: EUR. BUY 10 at 100 on 3 Jan of year 1 (a typo), closes 101 (2 Mar 2020), 103 (1 Jun), 99 (1 Sep),
    105 (1 Dec); SELL 4 at 105 on 15 Oct 2020. One lot, one broker."""
    owner, brokers, asset = await _eur_book(session, "year_one")
    a = brokers["A"]
    add_prices(session, asset, {date(2020, 3, 2): "101", date(2020, 6, 1): "103", date(2020, 9, 1): "99", date(2020, 12, 1): "105"})
    rows = await _add(
        session,
        buy=asset_row(a, asset, TransactionType.BUY, YEAR_ONE_BUY_DAY, "10", amount="-1000"),
        sell=asset_row(a, asset, TransactionType.SELL, date(2020, 10, 15), "-4", amount="420"),
    )
    return Book(asset=asset, users={"owner": owner}, brokers=brokers, rows=rows)


def _lower_the_floor(monkeypatch: pytest.MonkeyPatch, floor: date) -> list[str]:
    """``EARLIEST_RANGE_START`` is ``floor`` in this process only: in the module that defines it and in every backend module
    that imported it by value. The names of the modules patched are returned."""
    patched = []
    for name, module in list(sys.modules.items()):
        if name.startswith("backend.app") and module is not None and "EARLIEST_RANGE_START" in vars(module):
            monkeypatch.setattr(module, "EARLIEST_RANGE_START", floor)
            patched.append(name)
    return patched


@pytest.mark.asyncio
async def test_red_a_year_one_typo_costs_steps_not_days(session, monkeypatch):
    """RED until J5-5. A lot bought on 3 Jan of year 1 and read over its whole life (``date_from`` None), every analysis,
    with the product's floor lowered to 1 Jan of year 1 in this process only: the 737 834 days since the BUY are never
    walked.
    (a) every section has at most ``STEP_ROWS_PER_SECTION`` rows, and the lot's value steps and the price line cover every
        day from the first to ``date_to`` (summed lengths, no day built);
    (b) ``AssetPriceSeries.resolve`` is called at most ``RESOLVE_BUDGET`` times (a spy raises at ``RESOLVE_ABORT``);
    (c) the peak of ``tracemalloc`` is under 150 MB;
    (d) the answer comes in under 20 s (and no list of every day is built: (b) bounds the price loop, the peak the lists).

    Today: the price loop asks the series once per calendar day — the spy raises at 5 000 calls.
    """
    book = await seed_year_one(session)
    patched = _lower_the_floor(monkeypatch, date(1, 1, 1))
    assert "backend.app.utils.datetime_utils" in patched and "backend.app.services.lots_analysis_service" in patched, f"precondition: the floor is lowered where it is defined and where the service reads it, {patched}"

    resolved = Counter[str]()
    original_resolve = AssetPriceSeries.resolve

    def counted_resolve(self, query_date):
        resolved["calls"] += 1
        if resolved["calls"] > RESOLVE_ABORT:
            raise AssertionError(f"AssetPriceSeries.resolve called more than {RESOLVE_ABORT} times: the price loop is still per day")
        return original_resolve(self, query_date)

    monkeypatch.setattr(AssetPriceSeries, "resolve", counted_resolve)

    tracemalloc.start()
    started = time.monotonic()
    try:
        result = await _analysis(session, user=book.users["owner"], asset=book.asset, broker_ids=None, date_from=None, date_to=YEAR_ONE_DATE_TO)
        elapsed = time.monotonic() - started
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    assert result.calculation_status != "FAILED", f"precondition: the year-one book is analysed, {result.calculation_status}"
    assert resolved["calls"] <= RESOLVE_BUDGET, f"AssetPriceSeries.resolve called {resolved['calls']} times; the budget is {RESOLVE_BUDGET}"
    payload = result.model_dump(mode="json")
    assert payload.get("range") == {"start": YEAR_ONE_BUY_DAY.isoformat(), "end": YEAR_ONE_DATE_TO.isoformat()}, f"range: {payload.get('range')!r}"
    for section in STEP_KEYS:
        rows = payload.get(section) or []
        assert 0 < len(rows) <= STEP_ROWS_PER_SECTION, f"{section}: {len(rows)} rows; at most {STEP_ROWS_PER_SECTION}, one per true change"
    whole_life = (YEAR_ONE_DATE_TO - YEAR_ONE_BUY_DAY).days + 1
    for section, selector in (("value_history", lambda row: row["lot_id"] == book.rows["buy"].id), ("market_price_history", lambda row: True)):
        covered = sum((date.fromisoformat(row["through"]) - date.fromisoformat(row["date"])).days + 1 for row in payload[section] if selector(row))
        assert covered == whole_life, f"{section}: the steps cover {covered} days, the life since the BUY is {whole_life}"
    assert peak < PEAK_BYTES, f"tracemalloc peak {peak / 1024 / 1024:.0f} MB; the budget is {PEAK_BYTES // 1024 // 1024} MB"
    assert elapsed < WALL_SECONDS, f"the answer took {elapsed:.1f} s; the budget is {WALL_SECONDS} s"
