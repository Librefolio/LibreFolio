"""MF5-1 «P4» — ``DailyStateBuilder.build()`` keeps only its computed days, and every reader reads the segments.

Today ``build()`` appends one ``DailyPortfolioState`` per calendar day from ``date_from`` to ``date_to``: a quiet day is
``replace(previous_state, …)`` with its ten containers copied. A scope with one DEPOSIT on 1900-01-02 and a handful of
2025 movements makes ~46 000 states, of which ~10 are computed; every reader (``period``, ``DerivedViewsBuilder``, the
data-quality report, ``portfolio_service._engine_missing_fx_pairs``) then walks the whole list.

The cure (contract in ``test_daily_states_segments.py``): ``PortfolioCalculationResult.daily_states`` is a
``DailyStates`` holding one ``StateSegment`` per day the engine computes from ``date_from`` on (a movement, a market quote,
a rate change it reads, an in-transit boundary, a stale turn, a split, ``date_from``, ``period_start``), each holding until
the next; the engine's early returns give ``DailyStates()``. A quiet day is built only when a reader asks for it, through
``StateSegment.state_on``.

What is tested (pure: no database, no server, no network; the builder is fed by hand as in
``test_portfolio_engine/test_replay_floor.py``, whose helpers are copied below):

1. ``TestTheEngineKeepsTheComputedDays`` — on two books whose computed days are listed by hand (EUR movements, quotes,
   stale turns and a ``period_start``; cash and securities in transit with USD rate changes and foreign cash): the result
   is a ``DailyStates`` over every calendar day of the frame, and the segments start exactly on the computed days.
2. ``TestQuietDaysMaterializedAsToday`` — on three books (the in-transit/foreign-cash book, the EUR book, candles and
   acquisition funding on): every materialized day is its segment's state but for date, external flow 0 and acquisition
   funding None; a non-zero external flow and an acquisition funding appear only on segment starts.
3. ``TestTheCenturyBook`` — the cost red: one DEPOSIT on 1900-01-02 and seven 2025 rows, ``date_from`` on the floor
   (1900-01-01, ``EARLIEST_RANGE_START``): 46 021 days, fewer than 100 segments, and ``build()`` builds no quiet day
   (``StateSegment.state_on`` never called; ``DailyPortfolioState`` constructed at most twice per segment, HEAD: 46 021).
4. ``TestReadersOnSegments`` — on the century book, each reader gives on the ``DailyStates`` exactly what it gives on its
   dense ``list(...)``, and builds at most a number bounded by the segments (data quality, missing FX pairs), or one or two
   days (period boundaries, allocation now). Since D-P4 («cure B») the step views (history, broker P&L, allocation) build no
   quiet day at all — they read each segment's own state — and give steps equal to the dense list's, expanded to days the
   dense states' values; ``build_performance_inputs`` is sparse on the engine's states, and the TWRR, ROI and MWRR it gives on
   every snapshot day equal the dense inputs' on that day. The stale-price turn is the refined one (only the last observation
   before a gap longer than the threshold), and a missing pair's valuation days are in ``ranges``, its ``dates`` the movements.
5. ``TestEarlyReturns`` — ``PortfolioCalculationEngine.calculate`` without an access or without a transaction returns an
   empty ``DailyStates`` (the session is an ``AsyncMock``: no database).

Counting. ``StateSegment.state_on`` is replaced on the class through ``monkeypatch`` (it is patchable on the slotted
dataclass: slots restrict instances, not the class), and ``DailyPortfolioState.__init__`` is wrapped too
(``dataclasses.replace`` constructs through it), so a quiet day built by any other path is still counted. No clock.

RED on HEAD 1fd80c481, by absence: ``StateSegment`` and ``DailyStates`` do not exist, the module fails at collection with
``ImportError``. After a cure that adds the types but keeps a reader walking every day, that reader's cost test is red.

Runs in ``./dev.py test services financial-math`` (the runner collects the whole ``test_financial_math/`` directory).
"""

from __future__ import annotations

import dataclasses
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

from backend.app.db.models import BrokerUserAccess, TransactionType, UserRole
from backend.app.services.financial_math.portfolio import period
from backend.app.services.financial_math.portfolio.classifier import ScopeAwareTransactionClassifier
from backend.app.services.financial_math.portfolio.daily_state import DailyStateBuilder
from backend.app.services.financial_math.portfolio.data_quality import build_data_quality_report
from backend.app.services.financial_math.portfolio.derived_views import DerivedViewsBuilder
from backend.app.services.financial_math.portfolio.engine import PortfolioCalculationEngine
from backend.app.services.financial_math.portfolio.models import DailyPortfolioState, DailyStates, PortfolioCalculationResult, StateSegment
from backend.app.services.financial_math.price_marks import build_asset_price_series
from backend.app.services.financial_math.returns import (
    calculate_simple_roi_series,
    calculate_twrr_series,
    period_mwrr_series,
    rebase_to_period,
)
from backend.app.services.portfolio_service import _engine_missing_fx_pairs
from backend.test_scripts.test_services._engine_average_costs import engine_average_costs
from backend.test_scripts.test_services._engine_native_cash import engine_native_cash

A, B = 10, 20
X, Y, Z = 100, 200, 300

#: EARLIEST_RANGE_START (utils/datetime_utils.py), as test_replay_floor.py writes it.
FLOOR = date(1900, 1, 1)
QUIET_FIELDS = {"date", "external_cash_flow", "acquisition_funding"}

# =============================================================================
# HELPERS — copies of test_portfolio_engine/test_replay_floor.py (plus OHLC for the candles)
# =============================================================================


def _tx(
    *,
    id: int,
    broker_id: int = A,
    type: str = "DEPOSIT",
    dt: date,
    amount: str = "0",
    currency: str | None = "EUR",
    quantity: str = "0",
    asset_id: int | None = None,
    related_id: int | None = None,
) -> MagicMock:
    tx = MagicMock()
    tx.id = id
    tx.broker_id = broker_id
    tx.type = TransactionType(type)
    tx.date = dt
    tx.amount = Decimal(amount)
    tx.currency = currency
    tx.quantity = Decimal(quantity)
    tx.asset_id = asset_id
    tx.related_transaction_id = related_id
    tx.cost_basis_override = None
    tx.cost_basis_currency = None
    return tx


def _mark_series_from(classified_txs, price_map, asset_currencies, ohlc_by_date=None):
    """Mirror PortfolioCalculationEngine: one AssetPriceSeries per asset from prices + trades."""
    txs_by_asset: dict[int, list] = {}
    for ctxn in classified_txs:
        tx = ctxn.tx
        if tx.asset_id is not None:
            txs_by_asset.setdefault(tx.asset_id, []).append(tx)
    mark_series = {}
    for aid in set(txs_by_asset) | set(price_map or {}):
        series = build_asset_price_series(
            price_rows=(price_map or {}).get(aid, []),
            transactions=txs_by_asset.get(aid, []),
            split_linked_tx_ids=set(),
            asset_currency=(asset_currencies or {}).get(aid, "EUR"),
            quote_base_quantity=1,
            ohlc_by_date=(ohlc_by_date or {}).get(aid),
        )
        if series.has_observations:
            mark_series[aid] = series
    return mark_series


def _builder_kwargs(ohlc_by_date=None, **overrides) -> dict:
    kwargs = {
        "classified_txs": [],
        "in_transit_intervals": [],
        "external_cash_flows": [],
        "price_map": {},
        "quote_base_map": {},
        "asset_currencies": {},
        "fx_rate_map": {},
        "asset_classifications": {},
        "asset_types": {},
        "target_currency": "EUR",
    }
    kwargs.update(overrides)
    kwargs.setdefault("mark_series", _mark_series_from(kwargs["classified_txs"], kwargs["price_map"], kwargs["asset_currencies"], ohlc_by_date))
    kwargs.setdefault(
        "average_costs",
        engine_average_costs(kwargs["classified_txs"], asset_currencies=kwargs["asset_currencies"], target_currency="EUR", fx_rate_map=kwargs["fx_rate_map"], date_to=kwargs["date_to"]),
    )
    kwargs.setdefault("native_cash", engine_native_cash(kwargs["classified_txs"], target_currency="EUR", fx_rate_map=kwargs["fx_rate_map"], date_to=kwargs["date_to"]))
    return kwargs


def _ledger(txs, scope, *, date_to, price_map=None, fx_rate_map=None, asset_currencies=None) -> dict:
    """Builder overrides of a classified ledger (the real classifier, loading order (date, id), share 1)."""
    classification = ScopeAwareTransactionClassifier(
        scope_broker_ids=set(scope),
        all_transactions=sorted(txs, key=lambda tx: (tx.date, tx.id)),
        broker_shares=dict.fromkeys(scope, Decimal("1")),
    ).classify()
    price_map = price_map or {}
    asset_ids = {ctxn.tx.asset_id for ctxn in classification.classified if ctxn.tx.asset_id is not None} | set(price_map)
    return {
        "classified_txs": classification.classified,
        "in_transit_intervals": classification.in_transit_intervals,
        "external_cash_flows": classification.external_cash_flows,
        "price_map": price_map,
        "fx_rate_map": fx_rate_map or {},
        "asset_currencies": dict.fromkeys(asset_ids, "EUR") | (asset_currencies or {}),
        "asset_types": dict.fromkeys(asset_ids, "Stock"),
        "asset_classifications": dict.fromkeys(asset_ids),
        "date_to": date_to,
    }


def _prices(asset_id: int, currency: str, closes: dict[date, str]) -> dict[int, list[tuple[date, Decimal, str]]]:
    return {asset_id: [(day, Decimal(close), currency) for day, close in sorted(closes.items())]}


def _days(first: date, last: date) -> list[date]:
    return [first + timedelta(days=offset) for offset in range((last - first).days + 1)]


def _build(ledger: dict, *, date_from: date, **overrides) -> PortfolioCalculationResult:
    return DailyStateBuilder(**_builder_kwargs(**ledger, date_from=date_from, **overrides)).build()


def _field_values(state: DailyPortfolioState, *, skip: set[str] = frozenset()) -> dict:
    return {f.name: getattr(state, f.name) for f in dataclasses.fields(DailyPortfolioState) if f.name not in skip}


def _exact(value):
    """``value`` made of plain comparables with every Decimal as its digits and exponent (``Decimal("1.10")`` is not
    ``Decimal("1.1")``), through pydantic models, dicts, lists and tuples."""
    if isinstance(value, Decimal):
        return ("Decimal", value.as_tuple())
    if isinstance(value, BaseModel):
        return _exact(value.model_dump())
    if isinstance(value, dict):
        return {key: _exact(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_exact(item) for item in value]
    return value


def _by_day(steps: list[dict]) -> dict[date, dict]:
    """A series of steps (D-P4: each holds from ``date`` to ``through``, both included) as one entry per day, asserting its
    invariant: ``date <= through``, in order, no overlap; and two touching steps never hold the same values (maximal)."""
    days: dict[date, dict] = {}
    previous: dict | None = None
    for step in steps:
        assert step["date"] <= step["through"], f"step {step['date']}..{step['through']} ends before it starts"
        values = {key: value for key, value in step.items() if key not in ("date", "through")}
        if previous is not None:
            assert previous["through"] < step["date"], f"steps overlap or are out of order at {step['date']}"
            if previous["through"] + timedelta(days=1) == step["date"]:
                assert _exact({k: v for k, v in previous.items() if k not in ("date", "through")}) != _exact(values), f"the steps ending {previous['through']} and starting {step['date']} hold the same values"
        for day in _days(step["date"], step["through"]):
            days[day] = values
        previous = step
    return days


def _period_returns(snapshots: list, flows: list, date_from: date | None) -> tuple[dict, dict, dict]:
    """TWRR, simple ROI and MWRR of the period rebased on ``date_from``, each by snapshot day, Decimals with their exponent
    (the MWRR None where the card of that period has none)."""
    period = rebase_to_period(snapshots, flows, date_from)
    navs, cash_flows = list(period.nav_snapshots), list(period.cash_flows)
    twrr = {point.date: _exact(point.twrr) for point in calculate_twrr_series(navs, cash_flows)}
    roi = {point.date: _exact(point.roi) for point in calculate_simple_roi_series(navs, cash_flows)}
    mwrr = {point.date: _exact(point.mwrr) for point in period_mwrr_series(navs, cash_flows)}
    return twrr, roi, mwrr


@pytest.fixture
def materializations(monkeypatch) -> list[date]:
    """Every day ``StateSegment.state_on`` is asked for, in order."""
    calls: list[date] = []
    real_state_on = StateSegment.state_on

    def counting_state_on(self, day):
        calls.append(day)
        return real_state_on(self, day)

    monkeypatch.setattr(StateSegment, "state_on", counting_state_on)
    return calls


@pytest.fixture
def constructions(monkeypatch) -> list[date]:
    """Every ``DailyPortfolioState`` constructed (``dataclasses.replace`` constructs through ``__init__``), by its date."""
    built: list[date] = []
    real_init = DailyPortfolioState.__init__

    def counting_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        built.append(self.date)

    monkeypatch.setattr(DailyPortfolioState, "__init__", counting_init)
    return built


# =============================================================================
# BOOKS
# =============================================================================

# The EUR book: January 2025, period_start 01-25.
EUR_FROM, EUR_TO, EUR_PERIOD_START = date(2025, 1, 1), date(2025, 1, 31), date(2025, 1, 25)


def _eur_book() -> dict:
    """A deposits 1000 on 01-03 and buys 5 X for 500 on 01-06; X closes 101 on 01-08 and 102 on 01-13; a dividend of 10
    on 01-20 (no quantity: no position day)."""
    txs = [
        _tx(id=1, dt=date(2025, 1, 3), amount="1000"),
        _tx(id=2, type="BUY", dt=date(2025, 1, 6), amount="-500", quantity="5", asset_id=X),
        _tx(id=3, type="DIVIDEND", dt=date(2025, 1, 20), amount="10", asset_id=X),
    ]
    return _ledger(txs, {A}, date_to=EUR_TO, price_map=_prices(X, "EUR", {date(2025, 1, 8): "101", date(2025, 1, 13): "102"}))


#: The EUR book's computed days: date_from (the replay's first day) 01-01; movements 01-03, 01-06, 01-20; quotes 01-08,
#: 01-13; stale turns (D-P4): a price turns stale on an observation + STALE_PRICE_THRESHOLD_DAYS 7 + 1 only for the last
#: observation before a gap longer than the threshold — X is observed on 01-06 (BUY), 01-08 and 01-13, each followed by a
#: newer one within 8 days but the last, so only 01-21 (01-13 + 8); no 01-14 (BUY + 8) nor 01-16 (01-08 + 8);
#: period_start 01-25.
EUR_COMPUTED_DAYS = [date(2025, 1, d) for d in (1, 3, 6, 8, 13, 20, 21, 25)]

# The transit book: February 2025, one EUR deposit before date_from.
TRANSIT_FROM, TRANSIT_TO = date(2025, 2, 1), date(2025, 2, 28)


def _usd_rate(day: date) -> str:
    if day < date(2025, 2, 7):
        return "0.90"
    return "0.92" if day < date(2025, 2, 20) else "0.91"


def _transit_book() -> dict:
    """A deposits 2000 EUR on 01-15 (before date_from) and 1000 USD on 02-02, buys 5 Y (a USD stock) for 500 USD on
    02-03; 200 EUR leave A on 02-05 and reach B on 02-09; 2 Y leave A on 02-10 and reach B on 02-14. Y closes 105 USD on
    02-11 and 107 on 02-25. USD->EUR on every day from 01-14: 0.90, 0.92 from 02-07, 0.91 from 02-20."""
    txs = [
        _tx(id=1, dt=date(2025, 1, 15), amount="2000"),
        _tx(id=2, dt=date(2025, 2, 2), amount="1000", currency="USD"),
        _tx(id=3, type="BUY", dt=date(2025, 2, 3), amount="-500", currency="USD", quantity="5", asset_id=Y),
        _tx(id=4, type="CASH_TRANSFER", dt=date(2025, 2, 5), amount="-200", related_id=5),
        _tx(id=5, broker_id=B, type="CASH_TRANSFER", dt=date(2025, 2, 9), amount="200", related_id=4),
        _tx(id=6, type="TRANSFER", dt=date(2025, 2, 10), quantity="-2", asset_id=Y, currency=None, related_id=7),
        _tx(id=7, broker_id=B, type="TRANSFER", dt=date(2025, 2, 14), quantity="2", asset_id=Y, currency=None, related_id=6),
    ]
    rates = {("USD", "EUR", day): Decimal(_usd_rate(day)) for day in _days(date(2025, 1, 14), TRANSIT_TO)}
    return _ledger(txs, {A, B}, date_to=TRANSIT_TO, price_map=_prices(Y, "USD", {date(2025, 2, 11): "105", date(2025, 2, 25): "107"}), fx_rate_map=rates, asset_currencies={Y: "USD"})


#: The transit book's computed days from date_from: 02-01 (date_from); movements 02-02, 02-03, 02-05, 02-09, 02-10, 02-14;
#: in-transit boundaries 02-05/02-08/02-09 (cash) and 02-10/02-13/02-14 (securities); USD rate changes 02-07, 02-20;
#: quotes 02-11, 02-25; stale turns (D-P4): Y's observations (``AssetPriceSeries.observation_dates``: its quotes and its
#: BUY) are 02-03, 02-11 and 02-25 — a transfer is none —, and a price turns stale on an observation + 8 only for the last
#: one before a gap longer than the threshold: 02-11 + 8 = 02-19 (the next observation is 14 days on); not 02-03 + 8 = 02-11,
#: which a newer observation precedes. The USD rate is stored every day: no stale rate.
TRANSIT_COMPUTED_DAYS = [date(2025, 2, d) for d in (1, 2, 3, 5, 7, 8, 9, 10, 11, 13, 14, 19, 20, 25)]

# The funding book: candles and acquisition funding on.
FUNDING_FROM, FUNDING_TO = date(2025, 1, 1), date(2025, 1, 20)


def _funding_book() -> dict:
    txs = [
        _tx(id=1, dt=date(2025, 1, 2), amount="1000"),
        _tx(id=2, type="BUY", dt=date(2025, 1, 3), amount="-400", quantity="4", asset_id=X),
        _tx(id=3, type="BUY", dt=date(2025, 1, 8), amount="-220", quantity="2", asset_id=X),
        _tx(id=4, type="DIVIDEND", dt=date(2025, 1, 12), amount="5", asset_id=X),
        _tx(id=5, type="SELL", dt=date(2025, 1, 15), amount="109", quantity="-1", asset_id=X),
        _tx(id=6, type="BUY", dt=date(2025, 1, 16), amount="-100", quantity="1", asset_id=X),
    ]
    return _ledger(txs, {A}, date_to=FUNDING_TO, price_map=_prices(X, "EUR", {date(2025, 1, 3): "100", date(2025, 1, 6): "110", date(2025, 1, 10): "108"}))


FUNDING_OHLC = {X: {date(2025, 1, 3): (Decimal("98"), Decimal("103"), Decimal("97")), date(2025, 1, 6): (Decimal("104"), Decimal("112"), Decimal("101"))}}

# The century book: one DEPOSIT on 1900-01-02, seven rows in 2025, date_from on the floor.
CENTURY_TO = date(2025, 12, 31)


def _century_book() -> dict:
    """A deposits 10 000 EUR on 1900-01-02. In 2025: buys 10 X for 1000 (03-03); deposits 600 USD (03-10); buys 5 Y (a
    USD stock) for 500 USD (03-11); receives 3 Z by an ADJUSTMENT with no cost and no price (04-01: Z is MISSING, the NAV
    incomplete from then on); a dividend of 20 on X (09-01); sells 4 X for 440 (11-03). X closes 101 (03-05) and 105
    (06-02), Y 110 USD (03-12). USD->EUR only from 03-10 to 03-20 (0.90, 0.92 from 03-15): from 03-21 the pair is
    missing on every day."""
    txs = [
        _tx(id=1, dt=date(1900, 1, 2), amount="10000"),
        _tx(id=2, type="BUY", dt=date(2025, 3, 3), amount="-1000", quantity="10", asset_id=X),
        _tx(id=3, dt=date(2025, 3, 10), amount="600", currency="USD"),
        _tx(id=4, type="BUY", dt=date(2025, 3, 11), amount="-500", currency="USD", quantity="5", asset_id=Y),
        _tx(id=5, type="ADJUSTMENT", dt=date(2025, 4, 1), quantity="3", asset_id=Z),
        _tx(id=6, type="DIVIDEND", dt=date(2025, 9, 1), amount="20", asset_id=X),
        _tx(id=7, type="SELL", dt=date(2025, 11, 3), amount="440", quantity="-4", asset_id=X),
    ]
    rates = {("USD", "EUR", day): Decimal("0.90" if day < date(2025, 3, 15) else "0.92") for day in _days(date(2025, 3, 10), date(2025, 3, 20))}
    prices = _prices(X, "EUR", {date(2025, 3, 5): "101", date(2025, 6, 2): "105"}) | _prices(Y, "USD", {date(2025, 3, 12): "110"})
    return _ledger(txs, {A}, date_to=CENTURY_TO, price_map=prices, fx_rate_map=rates, asset_currencies={Y: "USD"})


CENTURY_DAYS = (CENTURY_TO - FLOOR).days + 1  # 46 021


@pytest.fixture(scope="module")
def century() -> PortfolioCalculationResult:
    return _build(_century_book(), date_from=FLOOR)


@pytest.fixture(scope="module")
def century_dense(century) -> list[DailyPortfolioState]:
    """The century book's every day, materialized once: the oracle every reader is compared with."""
    return list(century.daily_states)


# =============================================================================
# 1. THE ENGINE KEEPS THE COMPUTED DAYS
# =============================================================================


class TestTheEngineKeepsTheComputedDays:
    @pytest.mark.parametrize(
        ("book", "date_from", "date_to", "overrides", "computed_days"),
        [
            pytest.param(_eur_book, EUR_FROM, EUR_TO, {"period_start": EUR_PERIOD_START}, EUR_COMPUTED_DAYS, id="eur-quotes-stale-period_start"),
            pytest.param(_transit_book, TRANSIT_FROM, TRANSIT_TO, {}, TRANSIT_COMPUTED_DAYS, id="transit-usd-rates"),
        ],
    )
    def test_one_segment_per_computed_day(self, book, date_from, date_to, overrides, computed_days):
        result = _build(book(), date_from=date_from, **overrides)
        ds = result.daily_states

        assert isinstance(ds, DailyStates), f"daily_states is a {type(ds).__name__}"
        assert len(ds) == len(_days(date_from, date_to))
        assert (ds.first_date, ds.last_date) == (date_from, date_to)
        assert [seg.start for seg in ds.segments] == computed_days
        assert ds.segments[-1].end == date_to
        for seg in ds.segments:
            assert seg.state.date == seg.start

    def test_without_period_start_its_day_is_quiet(self):
        """The EUR book without ``period_start``: 01-25 is no longer computed (the guard that the hand list is exact)."""
        ds = _build(_eur_book(), date_from=EUR_FROM).daily_states
        assert [seg.start for seg in ds.segments] == [day for day in EUR_COMPUTED_DAYS if day != EUR_PERIOD_START]

    def test_a_date_from_after_the_first_movement_starts_the_first_segment(self):
        """The EUR book from 01-10 (a quiet day): the first segment starts on date_from and holds the replay's numbers."""
        date_from = date(2025, 1, 10)
        full = _build(_eur_book(), date_from=EUR_FROM).daily_states
        ds = _build(_eur_book(), date_from=date_from).daily_states
        assert [seg.start for seg in ds.segments] == [date_from] + [day for day in EUR_COMPUTED_DAYS if date_from < day != EUR_PERIOD_START]
        assert ds == full[(date_from - EUR_FROM).days :]


# =============================================================================
# 2. QUIET DAYS MATERIALIZED AS TODAY
# =============================================================================


def _funding_result() -> PortfolioCalculationResult:
    return _build(_funding_book(), date_from=FUNDING_FROM, ohlc_by_date=FUNDING_OHLC, compute_candles=True, compute_acquisition_funding=True)


class TestQuietDaysMaterializedAsToday:
    @pytest.mark.parametrize(
        ("make", "date_from", "date_to"),
        [
            pytest.param(lambda: _build(_transit_book(), date_from=TRANSIT_FROM), TRANSIT_FROM, TRANSIT_TO, id="transit-foreign-cash"),
            pytest.param(lambda: _build(_eur_book(), date_from=EUR_FROM, period_start=EUR_PERIOD_START), EUR_FROM, EUR_TO, id="eur"),
            pytest.param(_funding_result, FUNDING_FROM, FUNDING_TO, id="candles-acquisition-funding"),
        ],
    )
    def test_every_day_is_its_segments_state_but_for_the_three_quiet_fields(self, make, date_from, date_to):
        ds = make().daily_states
        states = list(ds)
        starts = {seg.start for seg in ds.segments}

        assert [state.date for state in states] == _days(date_from, date_to)
        assert any(seg.end > seg.start for seg in ds.segments), "precondition: the book has quiet days"
        for state in states:
            seg = ds.segment_at(state.date)
            assert seg is not None and seg.start <= state.date <= seg.end
            if state.date == seg.start:
                assert state is seg.state, f"{state.date}: a computed day is the stored state"
                continue
            assert state.external_cash_flow == Decimal(0), state.date
            assert state.acquisition_funding is None, state.date
            assert _field_values(state, skip=QUIET_FIELDS) == _field_values(seg.state, skip=QUIET_FIELDS), state.date
        assert {state.date for state in states if state.acquisition_funding is not None} <= starts
        assert {state.date for state in states if state.external_cash_flow != 0} <= starts

    def test_the_transit_book_carries_value_in_transit_on_quiet_days(self):
        """Precondition of the transit case: the cash and the securities in transit are on quiet days too."""
        ds = _build(_transit_book(), date_from=TRANSIT_FROM).daily_states
        assert ds.state_on(date(2025, 2, 6)).in_transit_cash_value != 0
        assert ds.state_on(date(2025, 2, 12)).in_transit_asset_market_value != 0
        assert ds.segment_at(date(2025, 2, 6)).start == date(2025, 2, 5)

    def test_the_funding_book_has_candles_and_funding(self):
        """Precondition of the funding case: candles carried on quiet days, funding only on BUY days."""
        ds = _funding_result().daily_states
        assert ds.state_on(date(2025, 1, 4)).pnl_candle is not None
        assert ds.state_on(date(2025, 1, 4)).pnl_candle == ds.state_on(date(2025, 1, 3)).pnl_candle
        funded = [state.date for state in ds if state.acquisition_funding is not None]
        assert funded == [date(2025, 1, 3), date(2025, 1, 8), date(2025, 1, 16)]
        assert [state.date for state in ds if state.external_cash_flow != 0] == [date(2025, 1, 2)]


# =============================================================================
# 3. THE CENTURY BOOK — THE COST OF build()
# =============================================================================


class TestTheCenturyBook:
    def test_build_keeps_few_segments_and_builds_no_quiet_day(self, materializations, constructions):
        result = _build(_century_book(), date_from=FLOOR)
        ds = result.daily_states
        during_build_state_on, during_build_constructed = len(materializations), len(constructions)

        assert isinstance(ds, DailyStates)
        assert len(ds) == CENTURY_DAYS
        assert len(ds.segments) < 100, f"{len(ds.segments)} segments"
        assert during_build_state_on == 0, f"build() materialized {during_build_state_on} quiet days"
        assert during_build_constructed <= 2 * len(ds.segments), f"build() constructed {during_build_constructed} states for {len(ds.segments)} segments"

    def test_the_century_book_spans_the_frame(self, century):
        ds = century.daily_states
        assert (ds.first_date, ds.last_date) == (FLOOR, CENTURY_TO)
        assert ds.segments[0].start == FLOOR and ds.segments[-1].end == CENTURY_TO
        # 1900-01-02 holds until the first 2025 movement: one segment of ~45 000 days.
        assert ds.segment_at(date(1950, 6, 15)).start == date(1900, 1, 2)
        assert ds.segment_at(date(1950, 6, 15)).end >= date(2025, 3, 2)

    def test_the_century_book_has_what_the_readers_need(self, century, century_dense):
        """Preconditions of the reader tests: a long run of incomplete NAV and of a missing pair (each a few segments
        across ~280 days), external flows, a by_type allocation."""
        assert sum(1 for state in century_dense if not state.nav_complete) > 200
        assert sum(1 for state in century_dense if "USD/EUR" in state.missing_fx_pairs) > 200
        assert [state.date for state in century_dense if state.external_cash_flow != 0] == [date(1900, 1, 2), date(2025, 3, 10)]
        assert century_dense[-1].by_type


# =============================================================================
# 4. READERS ON SEGMENTS
# =============================================================================

AS_OF = CENTURY_TO
WINDOW_FROM = date(2025, 12, 1)  # a one-month window: 31 days
WINDOW_DAYS = (AS_OF - WINDOW_FROM).days + 1


class TestPeriodReaders:
    @pytest.mark.parametrize(
        "day",
        [
            pytest.param(date(1950, 6, 15), id="quiet-in-the-long-segment"),
            pytest.param(date(2025, 3, 3), id="computed-day"),
            pytest.param(AS_OF, id="last-day"),
            pytest.param(date(2026, 1, 5), id="after-the-last-day"),
            pytest.param(FLOOR, id="first-day"),
            pytest.param(date(1899, 12, 31), id="before-the-first-day"),
        ],
    )
    def test_state_as_of(self, century, century_dense, materializations, day):
        got = period.state_as_of(century.daily_states, day)
        assert len(materializations) <= 2, f"{len(materializations)} days built"
        assert got == period.state_as_of(century_dense, day)

    @pytest.mark.parametrize(
        "as_of",
        [
            pytest.param(AS_OF, id="quiet-last-day"),
            pytest.param(date(2025, 3, 4), id="the-day-after-a-movement"),
            pytest.param(date(2025, 3, 3), id="a-movement-day"),
            pytest.param(date(1900, 1, 2), id="the-deposit-day"),
            pytest.param(FLOOR, id="no-day-before"),
        ],
    )
    def test_day_change(self, century, century_dense, materializations, as_of):
        got = period.day_change(century.daily_states, as_of)
        assert len(materializations) <= 4, f"{len(materializations)} days built"
        assert got == period.day_change(century_dense, as_of)

    @pytest.mark.parametrize(
        ("date_from", "as_of"),
        [
            pytest.param(None, AS_OF, id="since-inception"),
            pytest.param(date(2025, 6, 30), AS_OF, id="half-year"),
            pytest.param(date(1899, 6, 1), AS_OF, id="before-the-first-day"),
            pytest.param(date(1950, 1, 1), date(1960, 1, 1), id="inside-the-long-segment"),
            pytest.param(date(2025, 3, 3), date(2025, 3, 11), id="across-movements"),
        ],
    )
    def test_period_boundaries_and_pnl(self, century, century_dense, materializations, date_from, as_of):
        boundaries = period.period_boundaries(century.daily_states, date_from, as_of)
        assert len(materializations) <= 4, f"period_boundaries built {len(materializations)} days"
        materializations.clear()
        pnl = period.period_pnl(century.daily_states, date_from, as_of)
        assert len(materializations) <= 4, f"period_pnl built {len(materializations)} days"

        assert boundaries == period.period_boundaries(century_dense, date_from, as_of)
        assert pnl == period.period_pnl(century_dense, date_from, as_of)


class TestDerivedViewsReaders:
    """D-P4: the step views read each segment's own state (never a quiet day built), give steps — one per run of identical
    values, clipped to the window — and, expanded to days, the daily series of the dense list of states. The performance
    inputs are sparse on the engine's states: the returns they give on a snapshot's day are the dense inputs' on that day."""

    def test_build_history_of_a_window(self, century, century_dense, materializations):
        """A one-month window: the steps are the dense list's steps (same days, same values with their exponent), expanded to
        days they cover the window once, and on every day the NAV and the P&L are the dense state's."""
        got = DerivedViewsBuilder(century.daily_states, "EUR").build_history(WINDOW_FROM, AS_OF)
        assert len(materializations) == 0, f"{len(materializations)} quiet days built: the steps read the segments' own states"
        by_day = _by_day(got)
        assert list(by_day) == _days(WINDOW_FROM, AS_OF)
        assert len(got) < WINDOW_DAYS, "the quiet days are inside steps"
        assert _exact(got) == _exact(DerivedViewsBuilder(century_dense, "EUR").build_history(WINDOW_FROM, AS_OF))
        for state in century_dense[-WINDOW_DAYS:]:
            assert by_day[state.date]["nav_value"].amount.as_tuple() == state.nav_value.as_tuple(), state.date
            assert by_day[state.date]["total_pnl"].amount.as_tuple() == state.total_pnl.as_tuple(), state.date

    def test_build_history_of_a_window_inside_the_long_segment(self, century, century_dense, materializations):
        """Inside the 1900-2025 segment the window is one step, its days the window's, as the dense list gives it."""
        window_from, window_to = date(1950, 1, 1), date(1950, 1, 31)
        got = DerivedViewsBuilder(century.daily_states, "EUR").build_history(window_from, window_to)
        assert len(materializations) == 0
        assert [(step["date"], step["through"]) for step in got] == [(window_from, window_to)]
        assert _exact(got) == _exact(DerivedViewsBuilder(century_dense, "EUR").build_history(window_from, window_to))

    def test_build_history_with_extra_days_splits_the_step_there(self, century, century_dense, materializations):
        """``extra_days`` are change days the service adds (its TWRR/ROI days): a day inside a quiet run starts a step only
        where the values it reads from the segment differ — with no ``metrics``, never: the step stays whole."""
        quiet_day = date(2025, 12, 15)
        views = DerivedViewsBuilder(century.daily_states, "EUR")
        assert views.change_days(WINDOW_FROM, AS_OF, [quiet_day]) == sorted({WINDOW_FROM, quiet_day, *(seg.start for seg in century.daily_states.segments if WINDOW_FROM < seg.start <= AS_OF)})
        assert [(step["date"], step["through"]) for step in views.build_history(WINDOW_FROM, AS_OF, extra_days=[quiet_day])] == [(step["date"], step["through"]) for step in views.build_history(WINDOW_FROM, AS_OF)]
        pinned = views.build_history(WINDOW_FROM, AS_OF, metrics=lambda day: {"marker": day >= quiet_day}, extra_days=[quiet_day])
        assert [(step["date"], step["through"]) for step in pinned if step["date"] <= quiet_day <= step["through"]] == [(quiet_day, AS_OF)], "a metric that changes on the extra day starts a step there"
        assert len(materializations) == 0

    def test_build_broker_pnl_history_of_a_window(self, century, century_dense, materializations):
        got = DerivedViewsBuilder(century.daily_states, "EUR").build_broker_pnl_history(WINDOW_FROM, AS_OF)
        assert len(materializations) == 0, f"{len(materializations)} quiet days built"
        dense = DerivedViewsBuilder(century_dense, "EUR").build_broker_pnl_history(WINDOW_FROM, AS_OF)
        assert got and _exact(got) == _exact(dense)
        for broker_id, steps in got.items():
            by_day = _by_day(steps)
            assert list(by_day) == _days(WINDOW_FROM, AS_OF), f"broker {broker_id}: a step every day of the window it is in the state"
            for state in century_dense[-WINDOW_DAYS:]:
                assert by_day[state.date]["total_pnl"].amount.as_tuple() == state.broker_contributions[broker_id].pnl_contribution.as_tuple(), (broker_id, state.date)

    @pytest.mark.parametrize("dimension", ["type", "sector", "geography"])
    def test_build_allocation_history_from_a_date(self, century, century_dense, materializations, dimension):
        got = DerivedViewsBuilder(century.daily_states, "EUR").build_allocation_history(dimension, WINDOW_FROM)
        assert len(materializations) == 0, f"{len(materializations)} quiet days built from {WINDOW_FROM}"
        by_day = _by_day(got)
        assert list(by_day) == _days(WINDOW_FROM, AS_OF), "steps expanded to days: every day from the window's start to the end"
        assert _exact(got) == _exact(DerivedViewsBuilder(century_dense, "EUR").build_allocation_history(dimension, WINDOW_FROM))

    @pytest.mark.parametrize(
        "date_from",
        [
            pytest.param(WINDOW_FROM, id="one-month"),
            pytest.param(date(2025, 3, 1), id="since-march-with-a-flow"),
        ],
    )
    def test_build_performance_inputs_of_a_window(self, century, century_dense, materializations, date_from):
        """The engine's inputs are sparse (D-P4): the opening day, every segment start after it and the last day; the flows
        are the dense ones'. On every snapshot day TWRR, ROI and MWRR (after ``rebase_to_period``) are, Decimal for Decimal
        with its exponent, the dense inputs' value on that day: a quiet stretch's factor is exactly 1."""
        window_days = (AS_OF - date_from).days + 1
        sparse_snapshots, sparse_flows = DerivedViewsBuilder(century.daily_states, "EUR").build_performance_inputs(date_from)
        assert len(materializations) == 0, f"{len(materializations)} quiet days built"
        dense_snapshots, dense_flows = DerivedViewsBuilder(century_dense, "EUR").build_performance_inputs(date_from)

        assert [(flow.date, _exact(flow.amount)) for flow in sparse_flows] == [(flow.date, _exact(flow.amount)) for flow in dense_flows], "the flows are identical"
        starts_after_opening = [seg.start for seg in century.daily_states.segments if dense_snapshots[0].date < seg.start]
        assert [snapshot.date for snapshot in sparse_snapshots] == sorted({dense_snapshots[0].date, *starts_after_opening, AS_OF}), "the opening day, every segment start after it, the last day"
        assert len(sparse_snapshots) < window_days, "sparse: not one snapshot a day"
        dense_by_day = {snapshot.date: snapshot for snapshot in dense_snapshots}
        assert all(_exact(snapshot.nav) == _exact(dense_by_day[snapshot.date].nav) for snapshot in sparse_snapshots), "a snapshot's NAV is the dense day's"

        sparse_returns = _period_returns(sparse_snapshots, sparse_flows, date_from)
        dense_returns = _period_returns(dense_snapshots, dense_flows, date_from)
        for name, sparse_values, dense_values in zip(("twrr", "roi", "mwrr"), sparse_returns, dense_returns, strict=True):
            assert sparse_values and set(sparse_values) <= set(dense_values), name
            assert {day: dense_values[day] for day in sparse_values} == sparse_values, f"{name} on a snapshot day is the dense series' value"

    def test_build_performance_inputs_on_the_days_asked(self, century, century_dense, materializations):
        """``days`` adds snapshots after the opening (D-P4): the service asks every change day of its window plus the
        quiet days it wants a point on. On each of them, quiet days included, TWRR, ROI and MWRR are the dense series'
        value of that day; a day outside the window or before the opening is ignored."""
        date_from = date(2025, 3, 1)
        quiet_days = [date(2025, 5, 15), date(2025, 8, 20), date(2025, 12, 15)]
        views = DerivedViewsBuilder(century.daily_states, "EUR")
        days = [*views.change_days(date_from, AS_OF), *quiet_days, date(2025, 2, 1), date(2026, 3, 1)]
        sparse_snapshots, sparse_flows = views.build_performance_inputs(date_from, days=days)
        assert len(materializations) == 0
        dense_snapshots, dense_flows = DerivedViewsBuilder(century_dense, "EUR").build_performance_inputs(date_from)
        expected_days = sorted({date_from, *views.change_days(date_from, AS_OF), *quiet_days})
        assert [snapshot.date for snapshot in sparse_snapshots] == expected_days, "the opening, the days asked inside the window, nothing else"
        assert [(flow.date, _exact(flow.amount)) for flow in sparse_flows] == [(flow.date, _exact(flow.amount)) for flow in dense_flows]
        for name, sparse_values, dense_values in zip(("twrr", "roi", "mwrr"), _period_returns(sparse_snapshots, sparse_flows, date_from), _period_returns(dense_snapshots, dense_flows, date_from), strict=True):
            assert set(quiet_days) <= set(sparse_values), name
            assert {day: dense_values[day] for day in sparse_values} == sparse_values, f"{name} on a snapshot day, a quiet one included, is the dense series' value"

    def test_the_mwrr_of_a_quiet_day_needs_no_snapshot_between(self, century, century_dense):
        """The MWRR solves every point alone, so snapshots on a few quiet days only (the MWRR line's days, D-P4) give the
        dense series' MWRR on each of them: the flows are the same and the NAV of a day is its segment's."""
        date_from = date(2025, 3, 1)
        quiet_days = [date(2025, 5, 15), date(2025, 8, 20), date(2025, 12, 15)]
        snapshots, flows = DerivedViewsBuilder(century.daily_states, "EUR").build_performance_inputs(date_from, days=quiet_days)
        dense_snapshots, dense_flows = DerivedViewsBuilder(century_dense, "EUR").build_performance_inputs(date_from)
        assert [snapshot.date for snapshot in snapshots] == [date_from, *quiet_days]
        sparse_mwrr, dense_mwrr = _period_returns(snapshots, flows, date_from)[2], _period_returns(dense_snapshots, dense_flows, date_from)[2]
        assert set(sparse_mwrr) == set(quiet_days)
        assert {day: dense_mwrr[day] for day in quiet_days} == sparse_mwrr

    def test_build_performance_inputs_since_march_holds_the_usd_deposit(self, century):
        """Precondition: the March window's flows are not empty (the 600 USD deposit of 03-10)."""
        _snapshots, flows = DerivedViewsBuilder(century.daily_states, "EUR").build_performance_inputs(date(2025, 3, 1))
        assert [flow.date for flow in flows] == [date(2025, 3, 10)]

    def test_build_allocation_current(self, century, century_dense, materializations):
        got = DerivedViewsBuilder(century.daily_states, "EUR").build_allocation_current()
        assert len(materializations) <= 2, f"{len(materializations)} days built"
        assert got == DerivedViewsBuilder(century_dense, "EUR").build_allocation_current()
        assert got[0], "precondition: a by_type allocation"


class TestSegmentBoundedReaders:
    @pytest.mark.parametrize(
        ("period_from", "period_to"),
        [
            pytest.param(None, None, id="whole-history"),
            pytest.param(date(2025, 3, 1), AS_OF, id="since-march"),
            pytest.param(date(2025, 6, 10), date(2025, 6, 20), id="inside-the-incomplete-run"),
            pytest.param(date(1950, 1, 1), date(1950, 12, 31), id="inside-the-long-segment"),
        ],
    )
    def test_build_data_quality_report(self, century, century_dense, materializations, period_from, period_to):
        bound = len(century.daily_states.segments) + 2
        got = build_data_quality_report(century.daily_states, period_from=period_from, period_to=period_to)
        assert len(materializations) <= bound, f"{len(materializations)} days built, bound {bound} (the segments)"
        assert got == build_data_quality_report(century_dense, period_from=period_from, period_to=period_to)

    def test_the_data_quality_report_lists_the_incomplete_days(self, century):
        """Precondition: the whole-history report counts ~275 incomplete NAV days, while the segments are few."""
        report = build_data_quality_report(century.daily_states)
        assert sum((span.end - span.start).days + 1 for span in report.incomplete_nav_ranges) > 200
        assert len(century.daily_states.segments) < 100

    @pytest.mark.parametrize(
        ("period_from", "period_to"),
        [
            pytest.param(None, None, id="whole-history"),
            pytest.param(date(2025, 6, 1), AS_OF, id="second-half"),
            pytest.param(date(2025, 3, 15), date(2025, 3, 25), id="where-the-rate-stops"),
            pytest.param(date(1950, 1, 1), date(1950, 12, 31), id="inside-the-long-segment"),
        ],
    )
    def test_engine_missing_fx_pairs(self, century, century_dense, materializations, period_from, period_to):
        bound = len(century.daily_states.segments) + 2
        got = _engine_missing_fx_pairs(century, period_from, period_to)
        assert len(materializations) <= bound, f"{len(materializations)} days built, bound {bound} (the segments)"
        dense_result = SimpleNamespace(missing_fx=century.missing_fx, daily_states=century_dense)
        assert got == _engine_missing_fx_pairs(dense_result, period_from, period_to)

    def test_the_missing_pair_spans_many_days(self, century):
        """Precondition (D-P4): USD/EUR is missing on more than 200 valuation days, which are in ``ranges`` (merged
        ``DateSpan`` list: a handful for a handful of segments), while ``dates`` lists the movements only — here none: the
        USD deposit and BUY of 03-10 and 03-11 have their rate."""
        info = {info.pair: info for info in _engine_missing_fx_pairs(century, None, None)}["USD/EUR"]
        assert sum((span.end - span.start).days + 1 for span in info.ranges) > 200
        assert len(info.ranges) < 10, "a few merged ranges, not a span a day"
        assert info.dates == [], "dates are the movements' only"


# =============================================================================
# 5. THE ENGINE'S EARLY RETURNS
# =============================================================================


def _rows(items: list) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    return result


class TestEarlyReturns:
    @pytest.mark.asyncio
    async def test_no_access_gives_an_empty_daily_states(self):
        db = MagicMock()
        db.execute = AsyncMock(return_value=_rows([]))
        result = await PortfolioCalculationEngine(db).calculate(user_id=1, target_currency="EUR")
        assert isinstance(result.daily_states, DailyStates)
        assert len(result.daily_states) == 0

    @pytest.mark.asyncio
    async def test_no_transaction_gives_an_empty_daily_states(self):
        access = BrokerUserAccess(broker_id=A, user_id=1, role=UserRole.OWNER, share_percentage=Decimal("1"))
        db = MagicMock()
        db.execute = AsyncMock(side_effect=[_rows([access]), _rows([])])
        result = await PortfolioCalculationEngine(db).calculate(user_id=1, target_currency="EUR")
        assert result.scope_broker_ids == [A], "precondition: the second early return (an access, no transaction)"
        assert isinstance(result.daily_states, DailyStates)
        assert len(result.daily_states) == 0
