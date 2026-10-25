"""L1b — the lots analysis reads its FX rates as steps: the cost reds and the parity battery.

Workstream J «Numeri e analisi», lot L1b. The pure contract of the resolver (``need_days``, the reader stubbed) is pinned in
``test_lots_analysis_pure.py``; here the resolver and the service on the lane's database, through
``lots_analysis_service.get_lots_analysis``.

WHY. ``collect_fx_needs`` (``financial_math/lots/conversions.py``) asks the market price series' currencies one ``need()``
per calendar day from ``computed_from`` to ``actual_to``, and ``FxRateResolver.load`` hands ``convert_bulk`` one ``Currency``
per need. A lot bought on 2 Jan 1900 and read on 15 Feb 2021 is 44 240 needs and a 44 240-conversion ``convert_bulk`` call
(44 240 pydantic objects, one dict entry each), to answer 31 days.

THE CURE (J, L1b). ``FxRateResolver`` keeps ``need``, ``load``, ``convert``, ``missing_pairs`` and ``target_currency`` as
they are and gains ``need_days(currency, first, last)`` (every day of the window asked; nothing for a blank code, the target
or a window that ends before it starts). ``load`` asks ``unit_rate_steps`` (P3: one unit's rate as steps over the windows
asked, the same digits and exponent as ``convert_bulk`` on every asked day) once per load for every pending currency's
windows, a single-day need being a one-day window, and no longer calls ``convert_bulk``; each pending currency is still
normalised through ``Currency(code=currency, amount=1)`` once. ``collect_fx_needs`` asks the market currencies with one
``need_days(currency, computed_from, actual_to)`` each.

THE REDS (RED until L1b), on the ``1900-usd`` book — an EUR asset read in USD over 16 Jan – 15 Feb 2021, every analysis:
(r1) the conversions handed to ``conversions.convert_bulk`` total at most 400 (today about 44 000);
(r2) ``conversions.unit_rate_steps`` is called once or twice (today never: the name does not exist in ``conversions``).
Both wrap the name where ``conversions`` reads it (``raising=False``, delegating to the real function). The precondition,
green today and after: the BUY's lot has a value point worth something on each of the window's 31 days.

THE PARITY BATTERY (PARITY: green today and after the cure — the guarantee). Each case runs the analysis twice in one
session, every ``LotAnalysisType`` requested: A as it is; B with ``lots_analysis_service.FxRateResolver`` and
``lots_analysis_service.collect_fx_needs`` replaced by the LEGACY copies below (today's code, copied verbatim from HEAD
2879ae3e4, asking ``convert_bulk`` for one unit per need), undone before the comparison. Today A is B; after the cure B is
today's computation. The two answers dump to the same JSON (``model_dump(mode="json")``) but for
``calculation_metadata.generated_at``; a difference is reported by its first path. Not vacuous: ``_assert_not_vacuous``, the
book's own ``check`` on its whole window in its first scope, and — for every book with a foreign currency — B must have
asked ``convert_bulk`` for something there.

THE CASES. Every book of ``test_lots_change_days_parity.SCENARIOS`` (its windows × its scopes) read in EUR — the books with a
foreign currency are the ones that matter: ``fx-daily`` (HUF and ISK), ``at-cost-then-no-rate`` and ``unknown-pools`` (VND,
no rate) —, plus ``fx-daily`` read in HUF (the ISK purchase has no rate to HUF: a missing pair; the HUF asset is the
target) and ``1900-usd`` read in USD over its whole window, its last 30 days and an empty window. Trimmed: the 1900 EUR book
of L1a stays in its one 30-day window; ``1900-usd`` is read in its first scope only.

THE RESOLVER, ALONE (``test_the_resolver_*``): today's resolver and the product's, fed the same asks in the same order over
seeded rates, answer alike for every asked key and for the unasked days around — ``Decimal.as_tuple()`` equality, so the digits
and the exponent as well as the value —, and report the same ``missing_pairs()``. The legacy resolver has no ``need_days``:
a window is one ``need()`` per day on it; the product's resolver is asked ``need_days`` when it has it, and the same per-day
needs while it has not (today: so the cases are green today and exercise ``need_days`` after the cure — its absence is the pure
file's red). The rates (1 Jan – 31 Mar 1960, EUR/USD daily with a gap of six days, CHF/EUR direct, EUR/HUF, nothing for EUR/GBP):
EUR/USD stored with the house rule (base < quote), so USD→EUR reads it inverted (``amount / rate``) and EUR→USD direct; legacy
rows outside ``usable_fx_rate_bounds()`` (0, ``1E-19``, ``1E+19``, infinity) planted with raw SQL past the model inside the test's
transaction — the table accepts them (no CHECK on the rate), so that case is run.

ISOLATION. Every row is written into the test's session and flushed, never committed: the ``session`` fixture rolls it back.
Users, brokers and assets carry a uuid4 (``_scope_boundary_books.py``). FX pairs are global rows: each pair a test reads
(EUR/USD, CHF/EUR, EUR/HUF, EUR/GBP, HUF/ISK, CHF/USD, GBP/USD) is this test's own — every row of it, and its route, is deleted inside the
test's transaction and comes back with the rollback — then the test's rates are written. No sleep, no wall clock, no fixed
position in a collection.

TODAY (HEAD ``2879ae3e4``): the two reds fail on their assertion; every PARITY and resolver case is green.

J5-5 (D-P4 cure B, contract MF-P4b §1.3): the seven histories are STEPS (``date`` .. ``through``) and the service reads the market
price only on the days it can change on (``price_candidate_days``: an observation, a rate step — ``FxRateResolver.rate_change_days``
—, an event, with the day after each), converting a stretch with ``convert_through``. What this battery protects is unchanged: the
rates read as steps give the answer the per-day conversions gave. Three things follow. (1) The legacy copy gains the two methods the
service now calls, written so that it stays the reader of EVERY day: ``rate_change_days`` is every day it was asked for (so B reads
the price on every calendar day of a market currency's window, as HEAD did) and ``convert_through`` asks each day of the stretch
one by one. (2) A and B both end in steps, built by the same ``history_steps`` and both maximal, so their JSON is equal as it
stands (no expansion needed: equal days AND equal grouping); B is the day-by-day reading, A the one on candidates. (3) Whatever a
test says of "a point on each day" reads the steps through ``_lots_steps.daily_points``; the cost budgets (r1, r2) count what the
resolver is asked, which the days never changed.
"""

import random
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from datetime import date as date_type
from decimal import Decimal

import pytest
import pytest_asyncio

from backend.test_scripts.test_db_config import setup_test_database

setup_test_database()

from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import FxConversionRoute, FxRate, PriceHistory, Transaction
from backend.app.db.precision import usable_fx_rate_bounds
from backend.app.db.session import get_async_engine
from backend.app.schemas.common import Currency
from backend.app.schemas.portfolio import (
    LotAnalysisType,
    LotsAnalysisResponse,
)
from backend.app.schemas.wac import WACMissingPairInfo
from backend.app.services import lots_analysis_service
from backend.app.services.financial_math.fifo.models import FifoEvent, FifoInputTransaction, FifoLot, FragmentInterval, LotClosure
from backend.app.services.financial_math.lots import conversions as conversions_module
from backend.app.services.financial_math.lots.conversions import FxRateResolver, need_closure_rates, needs_market_series
from backend.app.services.financial_math.lots.prices import opening_reference_price
from backend.app.services.financial_math.price_marks import AssetPriceSeries
from backend.app.services.fx import conversion as fx_conversion
from backend.app.services.fx.conversion import convert_bulk
from backend.app.services.lots_analysis_service import get_lots_analysis
from backend.test_scripts.test_services._lots_steps import daily_points

# Non-test names of the L1a battery: its books, readings and comparison helpers. Never its ``test_*`` functions.
from backend.test_scripts.test_services.test_financial.test_lots_change_days_parity import (
    ALL_ANALYSES,
    BOOK_1900_BUY_DAY,
    BOOK_1900_DATE_FROM,
    BOOK_1900_DATE_TO,
    FX_DATE_TO,
    FX_FIRST_DAY,
    SCENARIOS,
    Book,
    Scenario,
    _assert_not_vacuous,
    _calendar,
    _check_missing_pair,
    _dump,
    _first_difference,
    _point_counts,
    _reader,
    seed_1900,
    seed_fx_daily,
)

EUR = "EUR"
USD = "USD"
HUF = "HUF"
THIS_MODULE = sys.modules[__name__]  # the legacy resolver reads ``convert_bulk`` from here: a case counts it by patching this name
CONVERSION_BUDGET = 400  # r1: today 44 000 and more
LEGACY_FLOOR = 44_000  # the 1900-usd book's legacy run hands convert_bulk at least this many conversions (44 240 days of EUR)

# Books with a foreign currency in EUR: B must ask convert_bulk for something on their whole window.
FOREIGN_IN_EUR = frozenset({"fx-daily", "at-cost-then-no-rate", "unknown-pools"})
BOOK_1900_USD_RATES_SPAN = (date(2019, 12, 1), date(2021, 2, 28))


@pytest_asyncio.fixture
async def session():
    async with AsyncSession(get_async_engine(), expire_on_commit=False) as s:
        yield s
        await s.rollback()


# --------------------------------------------------------------------------- #
# LEGACY — today's FxRateResolver and collect_fx_needs, verbatim from HEAD 2879ae3e4
# (backend/app/services/financial_math/lots/conversions.py). The reference of the parity battery.
# --------------------------------------------------------------------------- #


class LegacyFxRateResolver:
    def __init__(self, target_currency: str) -> None:
        self.target_currency = target_currency
        self._needs: list[tuple[str, date_type]] = []
        self._seen: set[tuple[str, date_type]] = set()
        self._loaded: set[tuple[str, date_type]] = set()
        self._rates: dict[tuple[str, date_type], Decimal] = {}
        self._missing: dict[str, set[date_type]] = defaultdict(set)

    def need(self, currency: str | None, as_of_date: date_type) -> None:
        if not currency or currency == self.target_currency:
            return
        key = (currency, as_of_date)
        if key in self._seen:
            return
        self._seen.add(key)
        self._needs.append(key)

    async def load(self, session: AsyncSession) -> None:
        pending = [key for key in self._needs if key not in self._loaded]
        if not pending:
            return
        conversions = [(Currency(code=currency, amount=Decimal("1")), self.target_currency, as_of_date) for currency, as_of_date in pending]
        results, _errors = await convert_bulk(session, conversions, raise_on_error=False)
        for idx, key in enumerate(pending):
            self._loaded.add(key)
            result = results[idx] if idx < len(results) else None
            if result is None:
                continue
            converted, _rate_date, _backfilled = result
            self._rates[key] = converted.amount

    def convert(self, amount: Decimal | None, currency: str | None, as_of_date: date_type) -> Decimal | None:
        if amount is None:
            return None
        if not currency or currency == self.target_currency:
            return amount
        rate = self._rates.get((currency, as_of_date))
        if rate is None:
            self._missing[f"{currency}/{self.target_currency}"].add(as_of_date)
            return None
        return amount * rate

    def missing_pairs(self) -> list[WACMissingPairInfo]:
        """Every conversion asked for and not made, one entry per pair, as the data-quality report lists them."""
        return [WACMissingPairInfo(pair=pair, dates=sorted(dates)) for pair, dates in sorted(self._missing.items())]

    # The two methods the service has called since J5-5 (D-P4 cure B: the market price is read on the days a rate can change,
    # not on every day). They are not copies of HEAD: they make this resolver what it was, the reader of EVERY day.

    def rate_change_days(self) -> tuple[date_type, ...]:
        """Every day a rate was asked for. The legacy resolver reads the rate of each day on its own, one ``convert_bulk`` unit
        a need: for it every asked day is a day the rate can change on, so the service reads the market price on all of them —
        today's day-by-day computation, the reference of the battery."""
        return tuple(sorted({day for _currency, day in self._needs}))

    def convert_through(self, amount: Decimal | None, currency: str | None, first: date_type, last: date_type) -> Decimal | None:
        """``convert`` for the stretch ``first``..``last``, each of its days asked one by one, as the days did. The answer is
        the first day's; a day with no rate is a gap of the pair, whatever the day before it said."""
        converted = self.convert(amount, currency, first)
        for offset in range(1, (last - first).days + 1):
            self.convert(amount, currency, first + timedelta(days=offset))
        return converted


def legacy_collect_fx_needs(  # noqa: C901 — independent per-analysis fx-need collection blocks, no decision tree
    *,
    fx_resolver: LegacyFxRateResolver,
    analyses: Sequence[LotAnalysisType],
    lots_by_id: dict[int, FifoLot],
    selected_ids: Sequence[int],
    transactions: Sequence[Transaction | FifoInputTransaction],
    price_series: AssetPriceSeries,
    prices: Sequence[PriceHistory],
    fragments: Sequence[FragmentInterval],
    events: Sequence[FifoEvent],
    closures: Sequence[LotClosure],
    split_ratios_by_tx_id: dict[int, Decimal],
    actual_to: date_type,
    computed_from: date_type,
    asset_currency: str,
) -> None:
    tx_by_id = {tx.id: tx for tx in transactions if tx.id is not None}
    if LotAnalysisType.LOT_SUMMARY in analyses or LotAnalysisType.RETURN_HISTORY in analyses:
        for lot_id in selected_ids:
            lot = lots_by_id[lot_id]
            fx_resolver.need(lot.currency, lot.opening_date)
            raw_reference_price, raw_reference_currency, reference_date, _reference_source = opening_reference_price(lot, price_series)
            if raw_reference_price is not None and raw_reference_currency is not None:
                fx_resolver.need(raw_reference_currency, reference_date)
            for closure in [c for c in closures if c.lot_id == lot_id]:
                need_closure_rates(fx_resolver, closure, lot)

    if LotAnalysisType.GANTT_TOPOLOGY in analyses:
        for fragment in fragments:
            if fragment.lot_id in selected_ids:
                lot = lots_by_id[fragment.lot_id]
                fx_resolver.need(lot.currency, fragment.start_date)

    if LotAnalysisType.CUSTODY_HISTORY in analyses or LotAnalysisType.EVENT_HISTORY in analyses:
        for event in events:
            tx = tx_by_id.get(event.transaction_id)
            if tx is not None:
                fx_resolver.need(tx.currency, event.date)
            # An opening row's price is in its lot's currency (for a priced ADJUSTMENT, its cost basis's).
            if event.kind in ("BUY", "ADJUSTMENT_IN") and event.transaction_id in lots_by_id:
                fx_resolver.need(lots_by_id[event.transaction_id].currency, event.date)
        for closure in closures:
            if closure.lot_id in selected_ids:
                need_closure_rates(fx_resolver, closure, lots_by_id[closure.lot_id])

    # The market price line (Y-30) reads the same marks every day, though it values no lot: it needs their rates too.
    if needs_market_series(analyses) or LotAnalysisType.MARKET_PRICE_HISTORY in analyses:
        current = computed_from
        # The unified resolver marks each day from asset-system prices AND observed trades
        # (BUY/SELL; never an ADJUSTMENT), each in its native currency; both the valuation and
        # chart lines convert those marks to target at the *valuation* date. Register the fx
        # needs for every price- and trade-currency across the whole window so a foreign mark
        # carried forward still translates on the day it is read (mirrors build_asset_price_series).
        currencies = {price.currency for price in prices}
        for tx in transactions:
            if tx.id in split_ratios_by_tx_id:
                continue
            tx_type = str(getattr(tx.type, "value", tx.type))
            # The series' observations: BUY/SELL trades, never an ADJUSTMENT (J-17).
            if tx_type in ("BUY", "SELL") and tx.amount:
                currencies.add(tx.currency or asset_currency)
        currencies.discard(None)
        while current <= actual_to:
            for currency in currencies:
                fx_resolver.need(currency, current)
            current += timedelta(days=1)


# --------------------------------------------------------------------------- #
# Rows this file owns, and the readings
# --------------------------------------------------------------------------- #


async def _own_pair(session: AsyncSession, one: str, other: str, rates: Mapping[date, Decimal] | None = None) -> None:
    """The pair ``one``/``other`` is this test's own while it runs: every FxRate row and every route of it (the table keeps a
    pair alphabetically, base < quote) is deleted inside the test's transaction — the rollback brings a neighbour's rows back —,
    then ``rates`` are written as stored: 1 base = rate quote. A neighbour's older rate would matter however old it is: the FX
    service backward-fills without limit."""
    base, quote = sorted((one, other))
    await session.execute(delete(FxRate).where(FxRate.base == base, FxRate.quote == quote))
    await session.execute(delete(FxConversionRoute).where(FxConversionRoute.base == base, FxConversionRoute.quote == quote))
    session.add_all([FxRate(date=day, base=base, quote=quote, rate=rate, source="TEST") for day, rate in (rates or {}).items()])
    await session.flush()


def _book_1900_usd_rates() -> dict[date, Decimal]:
    """EUR/USD (1 EUR = rate USD): one rate on Fri 29 Dec 1899 — the 1900 purchase and every day after it read it, backward-filled,
    up to the first daily rate; without it the purchase's cost has no rate and the lot is not valued at all —, then the business
    days of 1 Dec 2019 – 28 Feb 2021, a seeded walk around 1.10: weekends carry the Friday's rate."""
    rng = random.Random(2021)
    rates: dict[date, Decimal] = {date(1899, 12, 29): Decimal("1.3000")}
    rate = 1.10
    for day in _calendar(*BOOK_1900_USD_RATES_SPAN):
        if day.weekday() >= 5:
            continue
        rate += rng.uniform(-0.004, 0.004)
        rates[day] = Decimal(f"{rate:.4f}")
    return rates


async def seed_1900_usd(session: AsyncSession) -> Book:
    """Book ``1900-usd``: L1a's 1900 book — an EUR asset, BUY 10 at 100 on 2 Jan 1900, closes 101, 103, 99, 105 in 2020, SELL 4
    at 105 on 15 Oct 2020 — with EUR/USD owned (``_book_1900_usd_rates``)."""
    book = await seed_1900(session)
    await _own_pair(session, EUR, USD, _book_1900_usd_rates())
    return book


async def seed_fx_daily_in_huf(session: AsyncSession) -> Book:
    """Book ``fx-daily`` read in HUF: the asset is the target, the ISK purchase (10 Nov 1937) has no HUF/ISK rate — the pair is
    owned and empty, a missing pair."""
    book = await seed_fx_daily(session)
    await _own_pair(session, HUF, "ISK")
    return book


async def _read(
    session: AsyncSession,
    *,
    target: str,
    user,
    asset,
    broker_ids: list[int] | None,
    date_from: date | None,
    date_to: date,
    selected_lot_ids: list[int] | None = None,
) -> LotsAnalysisResponse:
    """Every analysis of ``asset`` for ``user`` over ``broker_ids``, in ``target``."""
    return await get_lots_analysis(
        session=session,
        user_id=user.id,
        asset_id=asset.id,
        broker_ids=broker_ids,
        date_from=date_from,
        date_to=date_to,
        target_currency=target,
        selected_lot_ids=selected_lot_ids,
        requested_analyses=ALL_ANALYSES,
    )


def _assert_1900_is_valued(book: Book, result: LotsAnalysisResponse) -> None:
    """Precondition of the reds, green today and after: the BUY's lot has a value point, worth something in USD, on each of
    the 31 days of the window."""
    lot_days = [point.date for point in daily_points(result.value_history) if point.lot_id == book.rows["buy"].id and point.open_value > 0]
    assert lot_days == _calendar(BOOK_1900_DATE_FROM, BOOK_1900_DATE_TO), f"precondition: {len(lot_days)} value points worth something for the lot of the BUY"


# --------------------------------------------------------------------------- #
# The reds
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_red_the_1900_book_is_converted_in_steps_not_one_item_a_day(session, monkeypatch):
    """RED until L1b. The 1900-usd book read over 16 Jan – 15 Feb 2021, every analysis: the conversions handed to
    ``conversions.convert_bulk`` (wrapped where ``conversions`` reads it, ``raising=False``, counting ``len(conversions)``
    across its calls) total at most 400. The cure hands it nothing: the lot's rates are steps.

    Precondition, green today and after: the lot of the BUY is valued on each of the 31 days.

    Today: about 44 000 — one EUR→USD conversion per calendar day from 2 Jan 1900 to 15 Feb 2021, in one call.
    """
    book = await seed_1900_usd(session)
    handed: list[int] = []
    wrapped = getattr(conversions_module, "convert_bulk", None) or fx_conversion.convert_bulk

    async def counting(session_, conversions, *args, **kwargs):
        handed.append(len(conversions))
        return await wrapped(session_, conversions, *args, **kwargs)

    monkeypatch.setattr(conversions_module, "convert_bulk", counting, raising=False)

    result = await _read(session, target=USD, user=book.users["owner"], asset=book.asset, broker_ids=None, date_from=BOOK_1900_DATE_FROM, date_to=BOOK_1900_DATE_TO)

    _assert_1900_is_valued(book, result)
    assert sum(handed) <= CONVERSION_BUDGET, f"{sum(handed)} conversions handed to convert_bulk in {len(handed)} call(s) to read {len(_calendar(BOOK_1900_DATE_FROM, BOOK_1900_DATE_TO))} days; the budget is {CONVERSION_BUDGET}"


@pytest.mark.asyncio
async def test_red_the_resolver_asks_unit_rate_steps_once_or_twice(session, monkeypatch):
    """RED until L1b. The 1900-usd book read over 16 Jan – 15 Feb 2021, every analysis: ``conversions.unit_rate_steps`` (wrapped
    where ``conversions`` reads it, ``raising=False``, delegating to the real one when the name does not exist) is called at
    least once and at most twice: one ``load`` for the income and cost rates, one for the rest.

    Precondition, green today and after: the lot of the BUY is valued on each of the 31 days.

    Today: never called — the name does not exist in ``conversions``.
    """
    book = await seed_1900_usd(session)
    requests: list[dict] = []
    wrapped = getattr(conversions_module, "unit_rate_steps", None) or fx_conversion.unit_rate_steps

    async def recording(session_, asked):
        requests.append({pair: list(windows) for pair, windows in asked.items()})
        return await wrapped(session_, asked)

    monkeypatch.setattr(conversions_module, "unit_rate_steps", recording, raising=False)

    result = await _read(session, target=USD, user=book.users["owner"], asset=book.asset, broker_ids=None, date_from=BOOK_1900_DATE_FROM, date_to=BOOK_1900_DATE_TO)

    _assert_1900_is_valued(book, result)
    assert 1 <= len(requests) <= 2, "unit_rate_steps was never called" if not requests else f"unit_rate_steps was called {len(requests)} times"


# --------------------------------------------------------------------------- #
# The parity battery
# --------------------------------------------------------------------------- #

_HUF_FX_DAILY = Scenario(seed_fx_daily_in_huf, FX_FIRST_DAY, FX_DATE_TO, ("owner-all", "owner-A", "owner-B"), check=_check_missing_pair("ISK/HUF"))


def _check_1900_in_usd(_book: Book, result: LotsAnalysisResponse) -> None:
    """The 1900-usd book is what it says: the market price line has a USD point on every day from the BUY (2 Jan 1900, converted
    at the rate of 29 Dec 1899, backward-filled) to ``date_to``, and the BUY's lot is valued on the last day."""
    marked = [point.date for point in daily_points(result.market_price_history)]
    assert marked == _calendar(BOOK_1900_BUY_DAY, BOOK_1900_DATE_TO), f"precondition: {len(marked)} marked days, from {marked[:1]} to {marked[-1:]}"
    assert any(point.date == BOOK_1900_DATE_TO and point.open_value > 0 for point in daily_points(result.value_history)), "precondition: the lot is valued on the reading day"


_1900_IN_USD = Scenario(
    seed_1900_usd,
    BOOK_1900_BUY_DAY,
    BOOK_1900_DATE_TO,
    ("owner-all",),
    check=_check_1900_in_usd,
    windows={"whole": (None, BOOK_1900_DATE_TO), "last-30-days": (BOOK_1900_DATE_FROM, BOOK_1900_DATE_TO), "empty": (BOOK_1900_DATE_TO + timedelta(days=1), BOOK_1900_DATE_TO)},
)

#: ``(target, book name)`` → its scenario, each book of L1a in EUR and the two new readings.
READINGS: dict[tuple[str, str], Scenario] = {(EUR, name): scenario for name, scenario in SCENARIOS.items()}
READINGS[(HUF, "fx-daily")] = _HUF_FX_DAILY
READINGS[(USD, "1900-usd")] = _1900_IN_USD

PARITY_CASES = [pytest.param(target, name, window, scope, id=f"{target}/{name}/{window}/{scope}") for (target, name), scenario in READINGS.items() for window in scenario.readings() for scope in scenario.scopes]


def _is_foreign(target: str, name: str) -> bool:
    """The book has a currency other than its target to convert: B must have asked ``convert_bulk`` for it."""
    return (target, name) in {(HUF, "fx-daily"), (USD, "1900-usd")} or (target == EUR and name in FOREIGN_IN_EUR)


async def _as_is_and_legacy(session: AsyncSession, monkeypatch: pytest.MonkeyPatch, **request) -> tuple[LotsAnalysisResponse, LotsAnalysisResponse, int]:
    """A, the analysis as it is; then B, the same with ``lots_analysis_service.FxRateResolver`` and ``.collect_fx_needs``
    replaced by the legacy copies — today's computation —, the patch undone when B returns, and the number of conversions B
    handed ``convert_bulk``."""
    as_is = await _read(session, **request)
    handed: list[int] = []

    async def counting(session_, conversions, *args, **kwargs):
        handed.append(len(conversions))
        return await fx_conversion.convert_bulk(session_, conversions, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(lots_analysis_service, "FxRateResolver", LegacyFxRateResolver)
        patch.setattr(lots_analysis_service, "collect_fx_needs", legacy_collect_fx_needs)
        patch.setattr(THIS_MODULE, "convert_bulk", counting)
        legacy = await _read(session, **request)
    return as_is, legacy, sum(handed)


@pytest.mark.asyncio
@pytest.mark.parametrize(("target", "scenario_name", "window", "scope"), PARITY_CASES)
async def test_parity_the_steps_answer_what_the_days_answered(session, monkeypatch, target, scenario_name, window, scope):
    """PARITY (green today and after L1b). A book read over a window in a scope, every analysis, in ``target``: the answer
    with the FX rates read as steps (A, as it is) dumps to the same JSON as the answer with today's resolver and needs (B, the
    legacy copies: one ``convert_bulk`` unit per need), the generation day aside. Not between two empty answers
    (``_assert_not_vacuous``); on its whole window in its first scope the book proves what it is (``Scenario.check``) and, with
    a foreign currency, B asked ``convert_bulk`` for something (and, for 1900-usd, for 44 000 conversions and more).

    Today: green — A is B.
    """
    scenario = READINGS[(target, scenario_name)]
    book = await scenario.seed(session)
    date_from, date_to = scenario.readings()[window]
    user, broker_ids = _reader(book, scope)
    selected = [book.rows[name].id for name in scenario.selected] or None
    empty_window = date_from is not None and date_from > date_to

    as_is, legacy, handed = await _as_is_and_legacy(session, monkeypatch, target=target, user=user, asset=book.asset, broker_ids=broker_ids, date_from=date_from, date_to=date_to, selected_lot_ids=selected)

    _assert_not_vacuous(as_is, empty_window=empty_window)
    if window == "whole" and scope == scenario.scopes[0]:
        if scenario.check is not None:
            scenario.check(book, as_is)
        if _is_foreign(target, scenario_name):
            assert handed > 0, f"precondition: today's resolver handed convert_bulk {handed} conversions on a book with a foreign currency"
    if (target, scenario_name) == (USD, "1900-usd") and not empty_window:
        assert handed >= LEGACY_FLOOR, f"precondition: the legacy copy handed convert_bulk {handed} conversions, the 44 240 days of today's computation are missing"
    difference = _first_difference(_dump(as_is), _dump(legacy))
    assert difference is None, f"{target} / {scenario_name} / {window} / {scope}: the steps' answer differs from the days' at {difference} — points A/B {_point_counts(as_is, legacy)}"


# --------------------------------------------------------------------------- #
# The resolver, alone: today's and the product's over seeded rates
# --------------------------------------------------------------------------- #

CHF = "CHF"
GBP = "GBP"
R_FIRST = date(1960, 1, 4)  # a Monday
R_LAST = date(1960, 3, 31)
USD_GAP = (date(1960, 2, 10), date(1960, 2, 15))  # no EUR/USD row (a legacy one on 12 Feb, when planted)
CHF_ROWS = {date(1960, 1, 15): "1.0234567891", date(1960, 2, 20): "1.05", date(1960, 3, 10): "0.9876543210"}
HUF_DAYS = [R_FIRST + timedelta(days=offset) for offset in range(0, 88, 3)]  # a EUR/HUF row every third day
AMOUNTS = (Decimal("1"), Decimal("123.456789"), Decimal("-5000"))


def _daily_usd_rates() -> dict[date, Decimal]:
    """EUR/USD every calendar day of ``R_FIRST`` – ``R_LAST``, a seeded walk around 1.0837, but on ``USD_GAP``. Four decimals:
    the inverse of one (USD→EUR) has a long tail, so another arithmetic shows in the digits."""
    rng = random.Random(1960)
    rates: dict[date, Decimal] = {}
    rate = 1.0837
    for day in _calendar(R_FIRST, R_LAST):
        rate += rng.uniform(-0.004, 0.004)
        if not USD_GAP[0] <= day <= USD_GAP[1]:
            rates[day] = Decimal(f"{rate:.4f}")
    return rates


def _huf_rates() -> dict[date, Decimal]:
    rng = random.Random(390)
    rate = 390.0
    rates: dict[date, Decimal] = {}
    for day in HUF_DAYS:
        rate += rng.uniform(-3, 3)
        rates[day] = Decimal(f"{rate:.4f}")
    return rates


#: Legacy rows an older release could leave, outside ``usable_fx_rate_bounds()``: planted with raw SQL, past the model.
LEGACY_ROWS: tuple[tuple[str, str, date, float], ...] = (
    (CHF, EUR, date(1960, 1, 10), float("inf")),  # before CHF's first usable row
    (CHF, EUR, date(1960, 2, 5), 1e19),  # in the gap between two usable rows
    (CHF, EUR, date(1960, 3, 20), 0.0),  # after the last usable row
    (EUR, USD, date(1960, 2, 12), 1e-19),  # inside the gap, on a would-be anchor
)


async def _seed_resolver_rates(session: AsyncSession) -> None:
    """The pairs of the resolver cases: EUR/USD daily with a gap, CHF/EUR direct, EUR/HUF, nothing for EUR/GBP."""
    await _own_pair(session, EUR, USD, _daily_usd_rates())
    await _own_pair(session, CHF, EUR, {day: Decimal(rate) for day, rate in CHF_ROWS.items()})
    await _own_pair(session, EUR, HUF, _huf_rates())
    await _own_pair(session, EUR, GBP)


async def _plant_legacy_rows(session: AsyncSession) -> None:
    """``LEGACY_ROWS`` with raw SQL past the model, inside the test's transaction, read back: each is outside
    ``usable_fx_rate_bounds()`` and is the row the SQL says it is."""
    smallest, first_refused = usable_fx_rate_bounds()
    for base, quote, day, rate in LEGACY_ROWS:
        assert not (smallest <= Decimal(str(rate)) < first_refused), f"the fixture itself is wrong: the legacy rate {rate} is usable"
        await session.execute(
            text("INSERT INTO fx_rates (date, base, quote, rate, source, fetched_at) VALUES (:day, :base, :quote, :rate, 'L1B-LEGACY', CURRENT_TIMESTAMP)"),
            {"day": day.isoformat(), "base": base, "quote": quote, "rate": rate},
        )
    stored = sorted((row[0], row[1], row[2], float(row[3])) for row in (await session.execute(text("SELECT base, quote, date, rate FROM fx_rates WHERE source = 'L1B-LEGACY'"))).all())
    planted = sorted((base, quote, day.isoformat(), rate) for base, quote, day, rate in LEGACY_ROWS)
    assert stored == planted, f"the fixture itself is wrong: raw SQL reads back {stored}, not the legacy rows planted {planted}"


def _bits(value: object) -> object:
    """None, or a Decimal's type, sign, digits and exponent: ``==`` alone takes 1.0837 for 1.0837000000."""
    if value is None:
        return None
    return (type(value).__name__, value.as_tuple() if isinstance(value, Decimal) else value)


class _Twins:
    """Today's resolver and the product's, fed the same asks in the same order. ``window`` is one ``need()`` per day on the
    legacy resolver, which has no ``need_days``; on the product's, ``need_days`` when it has it and the same per-day needs
    while it has not (before L1b)."""

    def __init__(self, target: str) -> None:
        self.target = target
        self.legacy = LegacyFxRateResolver(target)
        self.product = FxRateResolver(target)
        self.asked: set[tuple[str, date]] = set()

    def need(self, currency: str, day: date) -> None:
        self.legacy.need(currency, day)
        self.product.need(currency, day)
        self.asked.add((currency, day))

    def window(self, currency: str, first: date, last: date) -> None:
        days = _calendar(first, last)
        for day in days:
            self.legacy.need(currency, day)
        need_days = getattr(self.product, "need_days", None)
        if need_days is not None:
            need_days(currency, first, last)
        else:
            for day in days:
                self.product.need(currency, day)
        self.asked.update((currency, day) for day in days)

    async def load(self, session: AsyncSession) -> None:
        await self.legacy.load(session)
        await self.product.load(session)

    def read(self, currency: str, day: date) -> Decimal | None:
        """One unit's conversion on ``day``, asked of both resolvers — a conversion with no rate is recorded in each one's missing
        pairs — and the legacy one's answer returned, for a precondition."""
        self.product.convert(Decimal("1"), currency, day)
        return self.legacy.convert(Decimal("1"), currency, day)

    def answers(self, currency: str, first: date, last: date) -> dict[date, Decimal | None]:
        """``read`` on each day of ``first`` – ``last``."""
        return {day: self.read(currency, day) for day in _calendar(first, last)}

    def assert_alike(self, label: str, currencies: Sequence[str], first: date, last: date) -> None:
        """Both resolvers answer alike (``as_tuple()``) three amounts on every key asked and on every day of ``currencies``
        from five days before ``first`` to five days after ``last`` — asked or not —, and report the same missing pairs."""
        around = {(currency, day) for currency in currencies for day in _calendar(first - timedelta(days=5), last + timedelta(days=5))}
        differences = []
        for currency, day in sorted(self.asked | around):
            for amount in AMOUNTS:
                legacy, product = self.legacy.convert(amount, currency, day), self.product.convert(amount, currency, day)
                if _bits(legacy) != _bits(product):
                    differences.append(f"{currency} {day} amount {amount}: legacy {legacy!r} product {product!r}")
        assert not differences, f"{label}: {len(differences)} answers differ, first {differences[:3]}"
        legacy_missing, product_missing = self.legacy.missing_pairs(), self.product.missing_pairs()
        assert legacy_missing == product_missing, f"{label}: missing pairs differ — legacy {legacy_missing} product {product_missing}"


def _answered(answers: Mapping[date, object]) -> list[date]:
    return [day for day, value in answers.items() if value is not None]


@pytest.mark.asyncio
async def test_the_resolver_a_daily_pair_with_a_gap_read_inverted(session):
    """PARITY (green today and after). USD→EUR over EUR/USD, a rate a day but six days of gap (10–15 Feb 1960): the window of
    the whole span, a few single days around it and a day before the first rate, answered alike by both resolvers — the
    inverse of 1.08xx to the digit, the gap backward-filled from 9 Feb.

    Precondition: today's resolver answers the gap days with 9 Feb's rate.
    """
    await _seed_resolver_rates(session)
    twins = _Twins(EUR)
    twins.window(USD, R_FIRST, R_LAST)
    twins.need(USD, R_FIRST - timedelta(days=3))
    twins.need(USD, R_LAST + timedelta(days=4))
    await twins.load(session)

    gap = twins.answers(USD, USD_GAP[0], USD_GAP[1])
    before_gap = twins.read(USD, USD_GAP[0] - timedelta(days=1))
    assert before_gap is not None and set(map(_bits, gap.values())) == {_bits(before_gap)}, f"precondition: the gap {gap} carries 9 Feb's rate {before_gap}"
    twins.assert_alike("USD->EUR over the span", [USD], R_FIRST, R_LAST)


@pytest.mark.asyncio
async def test_the_resolver_a_pair_read_direct_and_a_pair_with_no_rows(session):
    """PARITY (green today and after). Target USD: EUR→USD reads EUR/USD as it is (a direct pair), CHF→USD has no row at all
    (CHF/USD: nothing, a missing conversion), GBP→USD none either. Both resolvers answer alike.

    Precondition: EUR answers on every day of its window; CHF and GBP on none.
    """
    await _seed_resolver_rates(session)
    await _own_pair(session, CHF, USD)
    await _own_pair(session, GBP, USD)
    twins = _Twins(USD)
    twins.window(EUR, R_FIRST, R_LAST)
    twins.window(CHF, date(1960, 2, 1), date(1960, 2, 10))
    twins.need(GBP, date(1960, 2, 2))
    await twins.load(session)

    assert _answered(twins.answers(EUR, R_FIRST, R_LAST)) == _calendar(R_FIRST, R_LAST), "precondition: EUR→USD answers on every day of the window, the gap carried"
    assert _answered(twins.answers(CHF, date(1960, 2, 1), date(1960, 2, 10))) == [] and _answered(twins.answers(GBP, date(1960, 2, 2), date(1960, 2, 2))) == [], "precondition: CHF→USD and GBP→USD have no rate"
    twins.assert_alike("EUR->USD direct, CHF->USD and GBP->USD without a pair", [EUR, CHF, GBP], R_FIRST, R_LAST)


@pytest.mark.asyncio
async def test_the_resolver_a_window_that_straddles_the_first_rate(session):
    """PARITY (green today and after). CHF→EUR (stored direct, base CHF) has its first row on 15 Jan 1960: a window of 5–25 Jan
    answers None before it and the rate from it on; a single day on 5 Jan (before it) is no rate, a single day on 1 Feb is
    carried from 15 Jan. Both resolvers answer alike.

    Precondition: the reference answers from 15 Jan and not before.
    """
    await _seed_resolver_rates(session)
    twins = _Twins(EUR)
    twins.window(CHF, date(1960, 1, 5), date(1960, 1, 25))
    twins.need(CHF, date(1960, 1, 5))
    twins.need(CHF, date(1960, 2, 1))
    await twins.load(session)

    answered = _answered(twins.answers(CHF, date(1960, 1, 5), date(1960, 1, 25)))
    assert answered == _calendar(date(1960, 1, 15), date(1960, 1, 25)), f"precondition: CHF answers from its first row, {answered[:1]}"
    assert twins.read(CHF, date(1960, 2, 1)) is not None, "precondition: 1 Feb is carried from 15 Jan"
    twins.assert_alike("a window across the first rate", [CHF], date(1960, 1, 5), date(1960, 2, 1))


@pytest.mark.asyncio
async def test_the_resolver_a_currency_with_no_rows_a_numeric_code_and_a_missing_pair(session):
    """PARITY (green today and after). GBP→EUR (EUR/GBP has no row, no route) as a window and a single day, the numeric ISO
    code '978' (valid for pycountry, base '978' of a pair that cannot have a row) and the target's own code in lower case
    ('eur', which normalises to the target and so converts at exactly Decimal('1'), convert_bulk's identity): both resolvers
    answer alike and report the same missing pairs.

    Precondition: GBP and '978' answer on no day; 'eur' answers 1 on each of its days, the digits of Decimal('1').
    """
    await _seed_resolver_rates(session)
    twins = _Twins(EUR)
    twins.window(GBP, date(1960, 3, 1), date(1960, 3, 7))
    twins.need(GBP, date(1960, 2, 1))
    twins.need("978", date(1960, 2, 2))
    twins.window("eur", date(1960, 2, 3), date(1960, 2, 5))
    await twins.load(session)

    assert _answered(twins.answers(GBP, date(1960, 3, 1), date(1960, 3, 7))) == [] and _answered(twins.answers("978", date(1960, 2, 2), date(1960, 2, 2))) == [], "precondition: GBP and 978 have no rate"
    eur = twins.answers("eur", date(1960, 2, 3), date(1960, 2, 5))
    assert {_bits(value) for value in eur.values()} == {_bits(Decimal("1"))}, f"precondition: the target's lower-case code converts at exactly 1, {eur}"
    twins.assert_alike("no rows, a numeric code, the target in lower case", [GBP, "978", "eur"], date(1960, 2, 1), date(1960, 3, 7))


@pytest.mark.asyncio
async def test_the_resolver_a_code_is_normalised_through_currency(session):
    """PARITY (green today and after). Raw lower-case codes: 'usd' and 'huf' read the USD and HUF rows (a window each, and a
    single day of 'usd' outside its window), as the upper-case 'USD' does. Both resolvers answer alike for the codes as asked.

    Precondition: 'usd' answers on its window with USD's rate and 'huf' with a HUF rate.
    """
    await _seed_resolver_rates(session)
    twins = _Twins(EUR)
    twins.window("usd", date(1960, 1, 20), date(1960, 2, 20))
    twins.need("usd", date(1960, 3, 25))
    twins.window("huf", date(1960, 2, 1), date(1960, 2, 28))
    await twins.load(session)

    upper = _Twins(EUR)
    upper.window(USD, date(1960, 1, 20), date(1960, 2, 20))
    await upper.load(session)
    assert [_bits(value) for value in twins.answers("usd", date(1960, 1, 20), date(1960, 2, 20)).values()] == [_bits(value) for value in upper.answers(USD, date(1960, 1, 20), date(1960, 2, 20)).values()], "precondition: 'usd' reads USD's rows"
    assert len(_answered(twins.answers("huf", date(1960, 2, 1), date(1960, 2, 28)))) == 28, "precondition: 'huf' reads the HUF rows"
    twins.assert_alike("lower-case codes", ["usd", "huf"], date(1960, 1, 20), date(1960, 3, 25))


@pytest.mark.asyncio
async def test_the_resolver_two_loads_accumulate_and_a_need_asked_again_is_not_reloaded(session):
    """PARITY (green today and after). Several loads accumulate: needs (a single USD day, a CHF window), ``load``, answers
    compared; then more needs — a USD window, a CHF day outside the first window, a CHF day inside it, the first USD day
    asked again —, ``load``, compared again with the first needs still answered; a third ``load`` with nothing new and the
    same needs repeated changes nothing.

    Precondition: the second load's windows answer, and the first load's keys still do.
    """
    await _seed_resolver_rates(session)
    twins = _Twins(EUR)
    twins.need(USD, date(1960, 1, 12))
    twins.window(CHF, date(1960, 1, 10), date(1960, 1, 31))
    await twins.load(session)
    twins.assert_alike("after the first load", [USD, CHF], R_FIRST, R_LAST)

    twins.window(USD, date(1960, 2, 1), date(1960, 2, 28))
    twins.need(CHF, date(1960, 3, 15))
    twins.need(CHF, date(1960, 1, 20))
    twins.need(USD, date(1960, 1, 12))
    await twins.load(session)
    assert twins.read(USD, date(1960, 1, 12)) is not None and len(_answered(twins.answers(USD, date(1960, 2, 1), date(1960, 2, 28)))) == 28, "precondition: both loads answer"
    assert twins.read(CHF, date(1960, 3, 15)) is not None, "precondition: the CHF day of the second load answers"
    twins.assert_alike("after the second load", [USD, CHF], R_FIRST, R_LAST)

    twins.need(USD, date(1960, 2, 10))
    twins.need(CHF, date(1960, 3, 15))
    await twins.load(session)
    twins.assert_alike("after a third load with nothing new", [USD, CHF], R_FIRST, R_LAST)


@pytest.mark.asyncio
async def test_the_resolver_a_legacy_unusable_rate_is_a_missing_rate(session):
    """PARITY (green today and after). Rows an older release left outside ``usable_fx_rate_bounds()`` — an infinite CHF rate
    before CHF's first usable row (10 Jan), 1E+19 in its gap (5 Feb), 0 after its last (20 Mar), 1E-19 inside EUR/USD's gap on
    12 Feb —, planted with raw SQL in the test's transaction (the table has no CHECK on the rate: it accepts them): windows
    and single days across each, USD→EUR and CHF→EUR, a window starting on the unusable row's day (its anchor is the usable row
    before it). Both resolvers skip them alike.

    Precondition: the rows are in the table (read back) and the reference skips them — 12 Feb carries 9 Feb's USD rate, 5 Feb
    15 Jan's CHF rate, nothing answers on 10 Jan.
    """
    await _seed_resolver_rates(session)
    await _plant_legacy_rows(session)
    twins = _Twins(EUR)
    twins.window(USD, date(1960, 2, 8), date(1960, 2, 18))
    twins.window(USD, date(1960, 2, 12), date(1960, 2, 14))
    twins.window(CHF, date(1960, 1, 8), date(1960, 3, 31))
    twins.need(CHF, date(1960, 2, 5))
    twins.need(CHF, date(1960, 1, 10))
    twins.need(CHF, date(1960, 3, 20))
    await twins.load(session)

    assert twins.read(USD, date(1960, 2, 12)) == twins.read(USD, date(1960, 2, 9)) is not None, "precondition: 12 Feb carries 9 Feb's rate"
    assert twins.read(CHF, date(1960, 2, 5)) == twins.read(CHF, date(1960, 1, 15)) is not None, "precondition: 5 Feb carries 15 Jan's CHF rate"
    assert twins.read(CHF, date(1960, 1, 10)) is None, "precondition: 10 Jan has no usable CHF row"
    assert twins.read(CHF, date(1960, 3, 20)) == twins.read(CHF, date(1960, 3, 10)) is not None, "precondition: 20 Mar carries 10 Mar's CHF rate"
    twins.assert_alike("legacy unusable rows", [USD, CHF], date(1960, 1, 5), R_LAST)


@pytest.mark.asyncio
async def test_the_resolver_an_invalid_code_raises_at_load(session):
    """PARITY (green today and after). A code pycountry rejects ('Z1') raises at ``load`` on both resolvers, the same exception
    type, a ``ValueError``: ``Currency(code=…, amount=1)`` validates each pending currency before anything is asked.

    Today: ``pydantic_core.ValidationError`` from today's list of ``Currency``.
    """
    await _seed_resolver_rates(session)
    twins = _Twins(EUR)
    twins.need("Z1", date(1960, 2, 1))
    twins.need(USD, date(1960, 2, 1))

    with pytest.raises(ValueError) as legacy_error:
        await twins.legacy.load(session)
    with pytest.raises(ValueError) as product_error:
        await twins.product.load(session)

    assert type(legacy_error.value) is type(product_error.value), f"legacy raised {type(legacy_error.value).__name__}, the product {type(product_error.value).__name__}"


@pytest.mark.asyncio
async def test_the_resolver_nothing_to_ask_is_not_asked():
    """PARITY (green today and after). Needs that ask nothing — the target's code, a blank or missing one — leave both
    resolvers with nothing to load: ``load`` answers on no session at all (``None`` is never read from), the amounts convert as
    themselves and there is no missing pair.

    Precondition: the reference has no pending need.
    """
    twins = _Twins(EUR)
    for currency in (EUR, None, ""):
        twins.legacy.need(currency, date(1960, 2, 1))
        twins.product.need(currency, date(1960, 2, 1))
    await twins.load(None)

    assert twins.legacy._needs == [], "precondition: nothing pending"
    for resolver in (twins.legacy, twins.product):
        assert [resolver.convert(Decimal("7"), currency, date(1960, 2, 1)) for currency in (EUR, None, "")] == [Decimal("7")] * 3
        assert resolver.missing_pairs() == []


def test_the_battery_patches_names_that_exist():
    """GUARD. The parity battery replaces the service's two names and counts the legacy resolver's ``convert_bulk`` through this
    module's global: they must exist where it patches them (a rename would turn the battery into two copies of one run), and the
    two new readings must be in it."""
    assert hasattr(lots_analysis_service, "FxRateResolver") and hasattr(lots_analysis_service, "collect_fx_needs")
    assert THIS_MODULE.convert_bulk is fx_conversion.convert_bulk
    assert {(HUF, "fx-daily"), (USD, "1900-usd")} <= set(READINGS)
